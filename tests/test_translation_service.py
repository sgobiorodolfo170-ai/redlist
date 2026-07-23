from unittest.mock import MagicMock, patch

from src.translation.translation_service import (
    BaiduProvider,
    TencentProvider,
    TranslationResult,
    TranslationService,
)


class TestTranslationResult:
    def test_fields(self):
        tr = TranslationResult(
            original_text="hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            provider="baidu_nmt",
        )
        assert tr.original_text == "hello"
        assert tr.translated_text == "你好"
        assert tr.source_lang == "en"
        assert tr.target_lang == "zh"
        assert tr.provider == "baidu_nmt"


class TestBaiduProvider:
    def test_nmt_default(self):
        p = BaiduProvider()
        assert p.name == "baidu_nmt"
        assert p._label == "百度通用翻译"
        assert p._url == "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def test_llm_mode(self):
        p = BaiduProvider(model_type="llm")
        assert p.name == "baidu_llm"
        assert p._label == "百度大模型翻译"
        assert p._url == "https://fanyi-api.baidu.com/ait/api/aiTextTranslate"

    def test_translate_missing_credentials(self):
        settings = MagicMock()
        settings.get.return_value = ""
        p = BaiduProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is None
        assert settings.get.call_count >= 2

    @patch("src.translation.translation_service.BaiduProvider._get_session")
    def test_nmt_success(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "trans_result": [{"src": "hello", "dst": "你好"}]
        }

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "baidu_nmt_app_id": "test_id",
            "baidu_nmt_app_key": "test_key",
        }.get(k, d)

        p = BaiduProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is not None
        assert result.translated_text == "你好"
        assert result.provider == "baidu_nmt"
        mock_session.get.assert_called_once()

    @patch("src.translation.translation_service.BaiduProvider._get_session")
    def test_llm_success(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.post.return_value.json.return_value = {
            "trans_result": [{"src": "hello", "dst": "你好"}]
        }

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "baidu_llm_app_id": "test_id",
            "baidu_llm_app_key": "test_key",
        }.get(k, d)

        p = BaiduProvider(model_type="llm")
        result = p.translate("hello", "en", "zh", settings)
        assert result is not None
        assert result.translated_text == "你好"
        mock_session.post.assert_called_once()

    @patch("src.translation.translation_service.BaiduProvider._get_session")
    def test_api_error(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "error_code": "54001",
            "error_msg": "Invalid Sign",
        }

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": "key" if "key" in k else "id"

        p = BaiduProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is None

    @patch("src.translation.translation_service.BaiduProvider._get_session")
    def test_timeout(self, mock_get_session):
        import requests
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.get.side_effect = requests.exceptions.Timeout("timeout")

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": "key" if "key" in k else "id"

        p = BaiduProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is None

    @patch("src.translation.translation_service.BaiduProvider._get_session")
    def test_request_exception(self, mock_get_session):
        import requests
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.get.side_effect = requests.exceptions.ConnectionError("connection failed")

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": "key" if "key" in k else "id"

        p = BaiduProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is None

    def test_get_session_retry_config(self):
        session = BaiduProvider._get_session()
        assert session is not None
        retry_adapter = session.get_adapter("https://example.com")
        assert retry_adapter is not None
        session.close()


class TestTencentProvider:
    def test_translate_missing_credentials(self):
        settings = MagicMock()
        settings.get.return_value = ""
        p = TencentProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is None

    @patch("tencentcloud.common.credential.Credential")
    @patch("tencentcloud.tmt.v20180321.tmt_client.TmtClient")
    def test_translate_success(self, mock_client_cls, mock_cred):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.TargetText = "你好"
        mock_client.TextTranslate.return_value = mock_resp

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "tencent_secret_id": "test_id",
            "tencent_secret_key": "test_key",
        }.get(k, d)

        p = TencentProvider()
        result = p.translate("hello", "en", "zh", settings)
        assert result is not None
        assert result.translated_text == "你好"

    def test_translate_import_error(self):
        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "tencent_secret_id": "test_id",
            "tencent_secret_key": "test_key",
        }.get(k, d)

        with patch("tencentcloud.common.credential.Credential", side_effect=ImportError("no sdk")):
            p = TencentProvider()
            result = p.translate("hello", "en", "zh", settings)
            assert result is None

    def test_name(self):
        p = TencentProvider()
        assert p.name == "tencent"


class TestTranslationService:
    def test_constructor(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.settings is settings
        assert service.last_error == ""

    def test_get_target_lang(self):
        settings = MagicMock()
        settings.get.return_value = "en"
        service = TranslationService(settings)
        assert service.get_target_lang() == "en"

    def test_translate_empty_text(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.translate("") is None
        assert service.translate("   ") is None

    def test_make_cache_key(self):
        settings = MagicMock()
        settings.get.return_value = "baidu_nmt"
        service = TranslationService(settings)
        key = service._make_cache_key("hello", "en", "zh")
        assert isinstance(key, str)
        assert len(key) == 32

    @patch("src.translation.translation_service.get_cache")
    def test_translate_cache_hit(self, mock_get_cache):
        cached_result = TranslationResult("hello", "你好", "en", "zh", "baidu_nmt")
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_result
        mock_get_cache.return_value = mock_cache

        settings = MagicMock()
        settings.get.return_value = "baidu_nmt"
        service = TranslationService(settings)

        result = service.translate("hello", "en", "zh")
        assert result is cached_result

    @patch("src.translation.translation_service.get_cache")
    def test_translate_success(self, mock_get_cache):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "translate_provider": "baidu_nmt",
            "baidu_nmt_app_id": "id",
            "baidu_nmt_app_key": "key",
            "translate_target_lang": "zh",
        }.get(k, d)

        with patch.object(BaiduProvider, "translate") as mock_provider_translate:
            mock_provider_translate.return_value = TranslationResult(
                "hello", "你好", "en", "zh", "baidu_nmt"
            )
            service = TranslationService(settings)
            result = service.translate("hello", "en", "zh")

        assert result is not None
        assert result.translated_text == "你好"
        mock_cache.set.assert_called_once()

    def test_detect_language_chinese(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.detect_language("你好世界") == "zh"

    def test_detect_language_english(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.detect_language("hello world") == "en"

    def test_cleanup(self):
        TranslationService._session = MagicMock()
        TranslationService.cleanup()
        assert TranslationService._session is None

    def test_get_session_fallback(self):
        TranslationService._session = None
        session = TranslationService._get_session()
        assert session is not None
        TranslationService._session = None

    @patch("src.translation.translation_service.get_cache")
    def test_clear_cache(self, mock_get_cache):
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        settings = MagicMock()
        service = TranslationService(settings)
        service._clear_cache()
        mock_cache.clear.assert_called_once()

    @patch("src.translation.translation_service.get_cache")
    def test_translate_without_target_lang(self, mock_get_cache):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "translate_provider": "baidu_nmt",
            "baidu_nmt_app_id": "id",
            "baidu_nmt_app_key": "key",
            "translate_target_lang": "zh",
        }.get(k, d)

        with patch.object(BaiduProvider, "translate") as mock_provider_translate:
            mock_provider_translate.return_value = TranslationResult("hi", "你好", "en", "zh", "baidu_nmt")
            service = TranslationService(settings)
            result = service.translate("hi", "auto")
            assert result is not None

    def test_translate_unknown_provider(self):
        settings = MagicMock()
        settings.get.return_value = "nonexistent_provider"
        service = TranslationService(settings)
        result = service.translate("hello", "en", "zh")
        assert result is None

    @patch("src.translation.translation_service.get_cache")
    def test_translate_provider_failure_sets_last_error(self, mock_get_cache):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "translate_provider": "baidu_nmt",
            "baidu_nmt_app_id": "",
            "baidu_nmt_app_key": "",
        }.get(k, d)

        service = TranslationService(settings)
        result = service.translate("hello", "en", "zh")
        assert result is None
        assert service.last_error != ""


class TestTranslationServiceEdgeCases:
    def test_detect_language_mixed_alphanumeric(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.detect_language("hello123") == "en"

    def test_detect_language_numbers_only(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.detect_language("12345") == "en"

    def test_detect_language_emoji_only(self):
        settings = MagicMock()
        service = TranslationService(settings)
        assert service.detect_language("😀🎉🚀") == "en"

    def test_make_cache_key_format(self):
        settings = MagicMock()
        settings.get.return_value = "baidu_llm"
        service = TranslationService(settings)
        key = service._make_cache_key("hello world", "en", "zh")
        assert isinstance(key, str)
        assert len(key) == 32
        # MD5 hex digest is always lowercase hex
        int(key, 16)
