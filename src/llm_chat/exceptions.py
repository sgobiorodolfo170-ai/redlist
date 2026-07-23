

class LLMError(Exception):
    """Base exception for all LLM-related errors."""
    def __init__(self, message: str, code: str = "LLM_ERROR"):
        self.code = code
        super().__init__(message)


class AuthError(LLMError):
    def __init__(self, message: str = "API Key 认证失败，请检查密钥"):
        super().__init__(message, code="AUTH_ERROR")


class RateLimitError(LLMError):
    def __init__(self, message: str = "请求过于频繁", retry_after: int = 60):
        super().__init__(message, code="RATE_LIMIT_ERROR")


class StreamDecodeError(LLMError):
    def __init__(self, message: str = "流式响应编码异常，已尝试修复"):
        super().__init__(message, code="STREAM_DECODE_ERROR")


class TimeoutError(LLMError):
    def __init__(self, message: str = "请求超时，请检查网络连接"):
        super().__init__(message, code="TIMEOUT")


class ModelNotFoundError(LLMError):
    def __init__(self, model: str = ""):
        message = f"模型不存在: {model}" if model else "模型不存在或接口地址错误"
        super().__init__(message, code="MODEL_NOT_FOUND")


class InvalidConfigError(LLMError):
    def __init__(self, message: str = "模型配置无效"):
        super().__init__(message, code="INVALID_CONFIG")


class ConnectionError_(LLMError):
    def __init__(self, message: str = "无法连接到 API 服务器，请检查接口地址"):
        super().__init__(message, code="CONNECTION_ERROR")


_SIGNAL_FORMAT = "[{code}] {message}"


def format_error_signal(exc: LLMError) -> str:
    """Format exception into signal string: [CODE] message"""
    return _SIGNAL_FORMAT.format(code=exc.code, message=str(exc))


def parse_error_signal(signal: str) -> tuple[str, str]:
    """Parse signal string back into (code, message)"""
    if signal.startswith("[") and "] " in signal:
        code = signal[1:signal.index("]")]
        message = signal[signal.index("]") + 2:]
        return code, message
    return "LLM_ERROR", signal
