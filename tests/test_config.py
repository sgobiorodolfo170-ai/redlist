import unittest

from pydantic import ValidationError

from src.llm_chat.config import ModelConfig


class TestModelConfigValid(unittest.TestCase):
    def test_minimal_valid_config(self):
        cfg = ModelConfig(
            name="test",
            api_url="https://api.openai.com/v1",
            api_key="sk-test12345678",
            model_name="gpt-4o",
        )
        self.assertEqual(cfg.name, "test")
        self.assertEqual(cfg.model_name, "gpt-4o")
        self.assertEqual(cfg.temperature, None)

    def test_full_config(self):
        cfg = ModelConfig(
            name="deepseek",
            api_url="https://api.deepseek.com",
            api_key="sk-abcdefghijklmnop",
            model_name="deepseek-chat",
            temperature=0.3,
            max_tokens=4096,
            top_p=0.9,
        )
        self.assertEqual(cfg.temperature, 0.3)
        self.assertEqual(cfg.max_tokens, 4096)

    def test_api_url_trailing_slash(self):
        cfg = ModelConfig(
            name="test",
            api_url="https://api.openai.com/v1/",
            api_key="sk-test12345678",
            model_name="gpt-4o",
        )
        self.assertFalse(cfg.api_url.endswith("/"))

    def test_to_dict_excludes_none(self):
        cfg = ModelConfig(
            name="test",
            api_url="https://api.test.com",
            api_key="sk-test12345678",
            model_name="gpt-4",
        )
        d = cfg.to_dict()
        self.assertIn("name", d)
        self.assertIn("api_url", d)
        self.assertIn("api_key", d)
        self.assertIn("model_name", d)
        self.assertNotIn("temperature", d)
        self.assertNotIn("max_tokens", d)

    def test_to_dict_includes_set_fields(self):
        cfg = ModelConfig(
            name="test",
            api_url="https://api.test.com",
            api_key="sk-test12345678",
            model_name="gpt-4",
            temperature=0.5,
        )
        d = cfg.to_dict()
        self.assertEqual(d["temperature"], 0.5)
        self.assertNotIn("max_tokens", d)


class TestModelConfigInvalid(unittest.TestCase):
    def test_empty_name_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="",
                api_url="https://api.openai.com/v1",
                api_key="sk-test12345678",
                model_name="gpt-4o",
            )

    def test_empty_model_name_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="https://api.openai.com/v1",
                api_key="sk-test12345678",
                model_name="",
            )

    def test_short_api_key_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="https://api.openai.com/v1",
                api_key="sk-ab",
                model_name="gpt-4o",
            )

    def test_invalid_url_scheme_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="ftp://api.openai.com/v1",
                api_key="sk-test12345678",
                model_name="gpt-4o",
            )

    def test_missing_url_netloc_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="not-a-url",
                api_key="sk-test12345678",
                model_name="gpt-4o",
            )

    def test_temperature_out_of_range_high_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="https://api.openai.com/v1",
                api_key="sk-test12345678",
                model_name="gpt-4o",
                temperature=3.0,
            )

    def test_max_tokens_zero_raises(self):
        with self.assertRaises(ValidationError):
            ModelConfig(
                name="test",
                api_url="https://api.openai.com/v1",
                api_key="sk-test12345678",
                model_name="gpt-4o",
                max_tokens=0,
            )


if __name__ == "__main__":
    unittest.main()
