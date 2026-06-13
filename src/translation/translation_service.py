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

    CACHE_NAME = "translation_cache"
    CACHE_MAX_SIZE = 500
    CACHE_TTL = 7200

    def __init__(self, settings):
        self.settings = settings
        self.last_error = ""
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

    def _clear_cache(self) -> None:
        cache = get_cache(self.CACHE_NAME, self.CACHE_MAX_SIZE, self.CACHE_TTL)
        cache.clear()

    def get_target_lang(self) -> str:
        return self.settings.get('translate_target_lang', 'zh')

    def _make_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        provider = self.settings.get('translate_provider', 'baidu_llm')
        key_str = f"{provider}:{text}:{source_lang}:{target_lang}"
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
        provider = self.settings.get('translate_provider', 'baidu_llm')
        if provider in ('baidu_llm', 'baidu_nmt'):
            if provider == 'baidu_llm':
                baidu_id = self.settings.get('baidu_llm_app_id', '').strip()
                baidu_key = self.settings.get('baidu_llm_app_key', '').strip()
            else:
                baidu_id = self.settings.get('baidu_nmt_app_id', '').strip()
                baidu_key = self.settings.get('baidu_nmt_app_key', '').strip()
            if baidu_id and baidu_key:
                model_type = "llm" if provider == "baidu_llm" else None
                return self._translate_baidu(text, source_lang, target_lang, baidu_id, baidu_key, model_type)
        elif provider == 'tencent':
            tencent_id = self.settings.get('tencent_secret_id', '').strip()
            tencent_key = self.settings.get('tencent_secret_key', '').strip()
            if tencent_id and tencent_key:
                return self._translate_tencent(text, source_lang, target_lang, tencent_id, tencent_key)

        return None

    def _translate_baidu(self, text: str, source_lang: str,
                        target_lang: str, baidu_app_id: str, baidu_app_key: str,
                        model_type: Optional[str] = None) -> Optional[TranslationResult]:
        if model_type == "llm":
            url = "https://fanyi-api.baidu.com/ait/api/aiTextTranslate"
            label = "百度大模型翻译"
            provider = "baidu_llm"
        else:
            url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
            label = "百度通用翻译"
            provider = "baidu_nmt"

        salt = random.randint(32768, 65536)
        sign_str = f"{baidu_app_id}{text}{salt}{baidu_app_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()

        params = {
            "q": text,
            "from": source_lang,
            "to": target_lang,
            "appid": baidu_app_id,
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
                err_msg = f"{result.get('error_code')} - {result.get('error_msg')}"
                logger.error(f"[{label}] 错误: {err_msg}")
                self.last_error = f"[{label}] {err_msg}"
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
            self.last_error = f"[{label}] 请求超时"
            logger.error(self.last_error)
        except requests.exceptions.RequestException as e:
            self.last_error = f"[{label}] 网络错误: {e}"
            logger.error(self.last_error)
        except Exception as e:
            self.last_error = f"[{label}] 未知错误: {e}"
            logger.exception(self.last_error)

        return None

    def _translate_tencent(self, text: str, source_lang: str,
                           target_lang: str,
                           tencent_secret_id: str, tencent_secret_key: str) -> Optional[TranslationResult]:
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.tmt.v20180321 import models, tmt_client

            cred = credential.Credential(tencent_secret_id, tencent_secret_key)
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
            self.last_error = "[腾讯翻译] SDK未安装"
            logger.error(self.last_error)
        except Exception as e:
            self.last_error = f"[腾讯翻译] 错误: {e}"
            logger.exception(self.last_error)
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
