import hashlib
import random
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.cache import get_cache
from src.utils.logger import get_logger

logger = get_logger("Translation")


@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    provider: str


class TranslationService:
    _session: Optional[requests.Session] = None
    _deepl_translator = None

    CACHE_NAME = "translation_cache"
    CACHE_MAX_SIZE = 500
    CACHE_TTL = 7200

    def __init__(self, settings):
        self.settings = settings
        self.provider = settings.get('translate_provider', 'baidu_llm')

        self.baidu_app_id = settings.get('baidu_app_id', '').strip()
        self.baidu_app_key = settings.get('baidu_app_key', '').strip()

        self.tencent_secret_id = settings.get('tencent_secret_id', '').strip()
        self.tencent_secret_key = settings.get('tencent_secret_key', '').strip()

        self.deepl_api_key = settings.get('deepl_api_key', '').strip()

        self._init_session()

    def _init_session(self) -> None:
        if TranslationService._session is None:
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=10)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            TranslationService._session = session

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._session is None:
            cls._session = requests.Session()
        return cls._session

    def update_config(self, provider, baidu_id='', baidu_key='',
                     tencent_id='', tencent_key='', deepl_key=''):
        self.provider = provider
        self.baidu_app_id = baidu_id.strip() if baidu_id else ''
        self.baidu_app_key = baidu_key.strip() if baidu_key else ''
        self.tencent_secret_id = tencent_id.strip() if tencent_id else ''
        self.tencent_secret_key = tencent_key.strip() if tencent_key else ''
        self.deepl_api_key = deepl_key.strip() if deepl_key else ''
        self._clear_cache()

    def set_baidu_config(self, app_id: str, app_key: str):
        self.baidu_app_id = app_id
        self.baidu_app_key = app_key
        self._clear_cache()

    def _clear_cache(self) -> None:
        cache = get_cache(self.CACHE_NAME, self.CACHE_MAX_SIZE, self.CACHE_TTL)
        cache.clear()

    def get_target_lang(self) -> str:
        return self.settings.get('translate_target_lang', 'zh')

    def _make_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        key_str = f"{self.provider}:{text}:{source_lang}:{target_lang}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def translate(self, text: str, source_lang: str = "auto",
                  target_lang: str = None) -> Optional[TranslationResult]:
        if not text.strip():
            return None

        if target_lang is None:
            target_lang = self.get_target_lang()

        cache_key = self._make_cache_key(text, source_lang, target_lang)
        cache = get_cache(self.CACHE_NAME, self.CACHE_MAX_SIZE, self.CACHE_TTL)

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for: {text[:30]}...")
            return cached_result

        result = self._do_translate(text, source_lang, target_lang)

        if result is not None:
            cache.set(cache_key, result)

        return result

    def _do_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[TranslationResult]:
        if self.provider in ('baidu_llm', 'baidu_nmt') and self.baidu_app_id and self.baidu_app_key:
            model_type = "llm" if self.provider == "baidu_llm" else None
            return self._translate_baidu(text, source_lang, target_lang, model_type)
        elif self.provider == 'tencent' and self.tencent_secret_id and self.tencent_secret_key:
            return self._translate_tencent(text, source_lang, target_lang)
        elif self.provider == 'deepl' and self.deepl_api_key:
            return self._translate_deepl(text, source_lang, target_lang)

        return None

    def _translate_baidu(self, text: str, source_lang: str,
                        target_lang: str, model_type: Optional[str] = None) -> Optional[TranslationResult]:
        if model_type == "llm":
            url = "https://fanyi-api.baidu.com/ait/api/aiTextTranslate"
            label = "百度大模型翻译"
            provider = "baidu_llm"
        else:
            url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
            label = "百度通用翻译"
            provider = "baidu_nmt"

        salt = random.randint(32768, 65536)
        sign_str = f"{self.baidu_app_id}{text}{salt}{self.baidu_app_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()

        params = {
            "q": text,
            "from": source_lang,
            "to": target_lang,
            "appid": self.baidu_app_id,
            "salt": salt,
            "sign": sign
        }
        if model_type == "llm":
            params["model_type"] = "llm"

        try:
            session = self._get_session()
            if model_type == "llm":
                response = session.post(url, json=params, timeout=10)
            else:
                response = session.get(url, params=params, timeout=10)
            result = response.json()

            if "error_code" in result:
                logger.error(f"[{label}] 错误: {result.get('error_code')} - {result.get('error_msg')}")
                return None

            if "trans_result" in result and result["trans_result"]:
                translated = "".join([r["dst"] for r in result["trans_result"]])
                return TranslationResult(
                    original_text=text,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    provider=provider
                )
        except requests.exceptions.Timeout:
            logger.error(f"[{label}] 请求超时")
        except requests.exceptions.RequestException as e:
            logger.error(f"[{label}] 网络错误: {e}")
        except Exception as e:
            logger.exception(f"[{label}] 未知错误: {e}")

        return None

    def _translate_tencent(self, text: str, source_lang: str,
                           target_lang: str) -> Optional[TranslationResult]:
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.tmt.v20180321 import models, tmt_client

            cred = credential.Credential(self.tencent_secret_id, self.tencent_secret_key)
            httpProfile = HttpProfile()
            httpProfile.endpoint = "tmt.tencentcloudapi.com"

            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile

            client = tmt_client.TmtClient(cred, "ap-guangzhou", clientProfile)

            req = models.TextTranslateRequest()
            req.SourceText = text

            lang_map = {
                "zh": "zh",
                "en": "en",
                "jp": "ja",
                "kor": "ko"
            }

            req.Source = lang_map.get(source_lang, "auto")
            req.Target = lang_map.get(target_lang, "zh")
            req.ProjectId = 0

            resp = client.TextTranslate(req)

            return TranslationResult(
                original_text=text,
                translated_text=resp.TargetText,
                source_lang=source_lang,
                target_lang=target_lang,
                provider="tencent"
            )
        except ImportError:
            logger.error("[腾讯翻译] SDK未安装")
        except Exception as e:
            logger.exception(f"[腾讯翻译] 错误: {e}")
        return None

    def _translate_deepl(self, text: str, source_lang: str,
                        target_lang: str) -> Optional[TranslationResult]:
        try:
            import deepl

            if TranslationService._deepl_translator is None:
                TranslationService._deepl_translator = deepl.Translator(self.deepl_api_key)

            translator = TranslationService._deepl_translator

            lang_map = {
                "zh": "ZH",
                "en": "EN-US",
                "jp": "JA",
                "kor": "KO"
            }

            result = translator.translate_text(
                text,
                source_lang=lang_map.get(source_lang),
                target_lang=lang_map.get(target_lang, "ZH")
            )

            return TranslationResult(
                original_text=text,
                translated_text=result.text,
                source_lang=source_lang,
                target_lang=target_lang,
                provider="deepl"
            )
        except ImportError:
            logger.error("[DeepL] SDK未安装")
        except Exception as e:
            logger.exception(f"[DeepL] 错误: {e}")
        return None

    def detect_language(self, text: str) -> str:
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return "zh"
        return "en"

    @classmethod
    def cleanup(cls) -> None:
        if cls._session is not None:
            cls._session.close()
            cls._session = None
        cls._deepl_translator = None
