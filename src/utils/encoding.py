"""
Encoding safety utilities for defending against UTF-8/GBK mojibake.

Provides defensive encoding validation and repair for text flowing through
the LLM chat pipeline (streaming response -> display -> storage).
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)


def ensure_utf8(text: Union[str, bytes, None]) -> str:
    """
    Ensure text is valid UTF-8 string.

    Handles the common "锟斤拷" mojibake caused by UTF-8 bytes misdecoded as GBK.
    If input is already valid UTF-8 str, returns as-is.
    If input is bytes, decodes as UTF-8 with replacement fallback.
    If input is str with replacement chars (�), attempts to repair by
    re-encoding to bytes and re-decoding (recovers some mojibake cases).

    Args:
        text: Input text (str, bytes, or None)

    Returns:
        Valid UTF-8 string (never raises)
    """
    if text is None:
        return ""

    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")

    if not isinstance(text, str):
        text = str(text)

    # Fast path: already valid UTF-8
    try:
        text.encode("utf-8").decode("utf-8")
        return text
    except UnicodeError:
        pass

    # Contains replacement chars or other encoding issues - attempt repair
    repaired = _repair_mojibake(text)
    if repaired != text:
        logger.debug("Repaired encoding issue in text (len=%d)", len(text))
        return repaired

    # Last resort: force clean via replace
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _repair_mojibake(text: str) -> str:
    """
    Attempt to repair common UTF-8/GBK mojibake patterns.

    Common pattern: UTF-8 bytes misdecoded as GBK produce "锟斤拷" (U+951F U+65A4 U+62B7)
    This happens when:
    1. UTF-8 Chinese text (e.g., "测试" = E6 B5 8B E8 AF 95)
    2. Interpreted as GBK -> "娴嬭瘯" or "锟斤拷" depending on byte alignment

    Repair strategy: encode as latin-1 (1:1 byte mapping) then decode as utf-8
    This works when the mojibake text was produced by GBK-decoding UTF-8 bytes.
    """
    # Check for common mojibake indicators
    if "锟斤拷" in text or "烫烫烫" in text or "屯屯屯" in text:
        try:
            # latin-1 preserves raw byte values 0-255
            raw_bytes = text.encode("latin-1")
            # Try decoding as UTF-8
            return raw_bytes.decode("utf-8")
        except UnicodeError:
            pass

    # Also try the reverse: text that was UTF-8 decoded as latin-1
    # (less common but possible)
    try:
        raw_bytes = text.encode("utf-8")
        return raw_bytes.decode("utf-8", errors="replace")
    except UnicodeError:
        pass

    return text


def safe_decode(data: bytes, encoding: str = "utf-8", errors: str = "replace") -> str:
    """
    Safely decode bytes to string with explicit encoding and error handling.

    Unlike str(data) or data.decode() with default encoding, this:
    - Requires explicit encoding (no locale-dependent default)
    - Uses 'replace' error handler by default (never raises)
    - Logs warnings on decode errors for observability

    Args:
        data: Bytes to decode
        encoding: Target encoding (default utf-8)
        errors: Error handling scheme (default replace)

    Returns:
        Decoded string
    """
    if not isinstance(data, bytes):
        return str(data)

    try:
        return data.decode(encoding, errors=errors)
    except (UnicodeError, LookupError) as e:
        logger.warning("Failed to decode %d bytes as %s: %s", len(data), encoding, e)
        return data.decode("utf-8", errors="replace")


def validate_utf8_response(response, log_prefix: str = "") -> bool:
    """
    Validate that HTTP response declares UTF-8 encoding.

    Logs warning if response.encoding is not UTF-8 compatible.
    Does not modify response - callers should use safe_decode() on response.content
    or set response.encoding = 'utf-8' before using response.text.

    Args:
        response: requests.Response object
        log_prefix: Prefix for log messages (e.g., "LLM ", "API ")

    Returns:
        True if encoding is UTF-8 compatible, False otherwise
    """
    declared = (response.encoding or "").lower()
    is_utf8 = declared in ("utf-8", "utf8", "utf_8", "unicode-1-1-utf-8")

    if not is_utf8 and declared:
        logger.warning(
            "%sResponse encoding is '%s' (not UTF-8). "
            "Streaming decode may produce mojibake. "
            "Consider setting response.encoding = 'utf-8' before reading.",
            log_prefix, declared
        )

    return is_utf8


def force_utf8_response(response) -> None:
    """
    Force response to use UTF-8 decoding for .text and .iter_lines(decode_unicode=True).

    Call this after receiving response but before reading content.
    This overrides any server-declared encoding.

    Args:
        response: requests.Response object
    """
    response.encoding = "utf-8"


def rewrite_file_as_utf8(path: Path, content: str) -> bool:
    """
    Rewrite file content as UTF-8.

    Args:
        path: File path
        content: Decoded content string

    Returns:
        True if rewrite succeeded, False otherwise
    """
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        logger.info("Rewrote %s as UTF-8 (was non-UTF-8 encoding)", path.name)
        return True
    except (PermissionError, OSError) as e:
        logger.warning("Failed to rewrite %s as UTF-8: %s", path.name, e)
        return False


def read_file_with_fallback_encoding(
    path: Path,
    encodings: Tuple[str, ...] = ("utf-8", "gbk", "gb18030"),
    rewrite_utf8: bool = True,
) -> Tuple[str, str, Optional[Exception]]:
    """
    Read file trying multiple encodings.

    Tries each encoding in order. First success wins.
    If rewrite_utf8=True and the winning encoding is not utf-8,
    rewrites file as UTF-8 to prevent recurrence.

    Args:
        path: File path
        encodings: Encoding priority list (default: utf-8, gbk, gb18030)
        rewrite_utf8: If True, rewrite non-UTF-8 files as UTF-8

    Returns:
        (content, encoding_used, error)
        error is the last exception if all encodings failed, None on success
    """
    if not path.exists():
        return "", "", FileNotFoundError(f"File not found: {path}")

    last_error: Optional[Exception] = None
    for enc in encodings:
        try:
            with open(path, "rb") as f:
                raw = f.read()
            content = raw.decode(enc)
            logger.debug("Read %s as %s", path.name, enc)
            if rewrite_utf8 and enc != "utf-8":
                rewrite_file_as_utf8(path, content)
            return content, enc, None
        except (UnicodeError, LookupError) as e:
            logger.debug("Failed to decode %s as %s: %s", path.name, enc, e)
            last_error = e
        except (PermissionError, OSError) as e:
            return "", "", e

    return "", "", last_error or UnicodeError(f"Failed to decode {path.name}")
