import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.utils.encoding import (
    ensure_utf8,
    force_utf8_response,
    read_file_with_fallback_encoding,
    rewrite_file_as_utf8,
    safe_decode,
    validate_utf8_response,
)


class TestEnsureUtf8(unittest.TestCase):
    def test_clean_utf8_string(self):
        self.assertEqual(ensure_utf8("测试正常"), "测试正常")

    def test_ascii_string(self):
        self.assertEqual(ensure_utf8("hello world"), "hello world")

    def test_empty_string(self):
        self.assertEqual(ensure_utf8(""), "")

    def test_none_input(self):
        self.assertEqual(ensure_utf8(None), "")

    def test_bytes_input(self):
        result = ensure_utf8(b"\xe6\xb5\x8b\xe8\xaf\x95")
        self.assertEqual(result, "测试")

    def test_bytes_with_invalid_sequence(self):
        result = ensure_utf8(b"\xff\xfe\x00\x00")
        self.assertIsInstance(result, str)
        self.assertIn("\ufffd", result)

    def test_int_input(self):
        self.assertEqual(ensure_utf8(42), "42")

    def test_mojibake_repair(self):
        text = "锟斤拷"
        result = ensure_utf8(text)
        self.assertIsInstance(result, str)


class TestSafeDecode(unittest.TestCase):
    def test_decode_utf8_bytes(self):
        self.assertEqual(safe_decode(b"hello"), "hello")

    def test_decode_non_bytes(self):
        self.assertEqual(safe_decode("already_string"), "already_string")

    def test_decode_with_invalid_bytes(self):
        result = safe_decode(b"\xff\xfe\x00\x00")
        self.assertIsInstance(result, str)


class TestValidateUtf8Response(unittest.TestCase):
    def test_utf8_encoding_returns_true(self):
        r = Mock()
        r.encoding = "utf-8"
        r.headers = {"Content-Type": "application/json; charset=utf-8"}
        self.assertTrue(validate_utf8_response(r))

    def test_gbk_encoding_returns_false(self):
        r = Mock()
        r.encoding = "gbk"
        r.headers = {"Content-Type": "application/json; charset=gbk"}
        self.assertFalse(validate_utf8_response(r))

    def test_none_encoding(self):
        r = Mock()
        r.encoding = None
        r.headers = {"Content-Type": "application/json"}
        self.assertFalse(validate_utf8_response(r))


class TestForceUtf8Response(unittest.TestCase):
    def test_force_utf8_overrides_encoding(self):
        r = Mock()
        r.encoding = "gbk"
        force_utf8_response(r)
        self.assertEqual(r.encoding, "utf-8")


class TestReadFileWithFallbackEncoding(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_bytes(self, name: str, data: bytes) -> Path:
        p = self.tmpdir / name
        p.write_bytes(data)
        return p

    def test_read_utf8_file(self):
        p = self._write_bytes("utf8.json", json.dumps({"a": 1}).encode("utf-8"))
        content, enc, err = read_file_with_fallback_encoding(p)
        self.assertEqual(enc, "utf-8")
        self.assertIsNone(err)
        self.assertEqual(json.loads(content), {"a": 1})

    def test_read_gbk_file(self):
        text = '{"name": "测试"}'
        gbk_data = text.encode("gbk")
        p = self._write_bytes("gbk.json", gbk_data)
        content, enc, err = read_file_with_fallback_encoding(p)
        self.assertIsNone(err)
        self.assertEqual(enc, "gbk")
        data = json.loads(content)
        self.assertEqual(data["name"], "测试")

    def test_read_gb18030_file(self):
        text = '{"name": "测试"}'
        gb_data = text.encode("gb18030")
        p = self._write_bytes("gb18030.json", gb_data)
        content, enc, err = read_file_with_fallback_encoding(p)
        self.assertIsNone(err)
        self.assertIn(enc, ("gbk", "gb18030"))

    def test_nonexistent_file(self):
        p = self.tmpdir / "nope.json"
        content, enc, err = read_file_with_fallback_encoding(p)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, FileNotFoundError)

    def test_binary_data_all_encodings_fail(self):
        p = self._write_bytes("binary.bin", b"\x00\x01\x02\xff\xfe")
        content, enc, err = read_file_with_fallback_encoding(p)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, UnicodeError)

    def test_rewrite_non_utf8_to_utf8(self):
        text = '{"name": "测试"}'.encode("gbk")
        p = self._write_bytes("rewrite.json", text)
        content, enc, err = read_file_with_fallback_encoding(p, rewrite_utf8=True)
        self.assertIsNone(err)
        self.assertEqual(enc, "gbk")
        content2, enc2, err2 = read_file_with_fallback_encoding(p)
        self.assertEqual(enc2, "utf-8")
        self.assertEqual(json.loads(content2)["name"], "测试")


class TestRewriteFileAsUtf8(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_rewrite_content(self):
        p = self.tmpdir / "test.txt"
        p.write_text("测试", encoding="gbk")
        result = rewrite_file_as_utf8(p, "测试")
        self.assertTrue(result)
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), "测试")

    def test_rewrite_nonexistent_path(self):
        p = self.tmpdir / "subdir" / "nope.txt"
        result = rewrite_file_as_utf8(p, "test")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
