import json
import time
from urllib.parse import urlparse

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from src.llm_chat.exceptions import (
    AuthError,
    ConnectionError_,
    InvalidConfigError,
    LLMError,
    ModelNotFoundError,
    TimeoutError,
    format_error_signal,
)
from src.utils.encoding import force_utf8_response, safe_decode, validate_utf8_response
from src.utils.logger import get_logger

logger = get_logger("LLMService")


def _extract_host(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


class LLMService(QThread):
    STREAM_TIMEOUT = 300

    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, messages, model_config):
        super().__init__()
        self.messages = messages
        self.model_config = model_config
        self._cancelled = False
        self._response = None
        self._start_time = 0.0
        self._model_name = ""
        self._api_host = ""

    def run(self):
        api_url = self.model_config.get("api_url", "").rstrip("/")
        api_key = self.model_config.get("api_key", "")
        model_name = self.model_config.get("model_name", "")
        self._model_name = model_name
        self._api_host = _extract_host(api_url)
        self._start_time = time.time()

        if not api_url or not api_key or not model_name:
            logger.warning("Invalid config | model=%s api=%s", model_name, self._api_host,
                           extra={"model": model_name, "host": self._api_host, "event": "invalid_config"})
            self.error.emit(format_error_signal(InvalidConfigError("模型配置不完整，请检查 API 地址、Key 和模型名称")))
            return

        url = f"{api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {
            "model": model_name,
            "messages": self.messages,
            "stream": True,
        }

        try:
            self._response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
            self._response.raise_for_status()

            # Force UTF-8 decoding regardless of server-declared encoding
            force_utf8_response(self._response)

            # Validate response encoding - warn if not UTF-8
            validate_utf8_response(self._response, log_prefix="LLM ")

            chunks = []
            # Use explicit UTF-8 decoding with fallback instead of decode_unicode=True
            # decode_unicode=True relies on server-declared encoding which may be wrong on Windows (GBK)
            for raw_line in self._response.iter_lines(decode_unicode=False):
                if self._cancelled:
                    break
                if time.time() - self._start_time > self.STREAM_TIMEOUT:
                    self.error.emit(format_error_signal(TimeoutError("流式响应超时，请重试")))
                    return
                if not raw_line:
                    continue
                # Safely decode each line as UTF-8 with replacement fallback
                line = safe_decode(raw_line, encoding="utf-8")
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunks.append(content)
                            self.chunk_received.emit(content)
                    except json.JSONDecodeError:
                        continue

            if not self._cancelled:
                self.finished.emit("".join(chunks))

        except requests.exceptions.Timeout:
            elapsed = time.time() - self._start_time
            logger.warning("LLM request timed out | model=%s api=%s elapsed=%.1fs",
                           self._model_name, self._api_host, elapsed,
                           extra={"model": self._model_name, "host": self._api_host,
                                  "elapsed": elapsed, "event": "timeout"})
            self.error.emit(format_error_signal(TimeoutError("请求超时，请检查网络连接或 API 地址")))
        except requests.exceptions.ConnectionError:
            elapsed = time.time() - self._start_time
            logger.warning("LLM connection failed | model=%s api=%s elapsed=%.1fs",
                           self._model_name, self._api_host, elapsed,
                           extra={"model": self._model_name, "host": self._api_host,
                                  "elapsed": elapsed, "event": "connection_error"})
            self.error.emit(format_error_signal(ConnectionError_("无法连接到 API 服务器，请检查接口地址")))
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            detail = ""
            if e.response is not None:
                try:
                    detail = e.response.text[:200]
                except Exception:
                    pass
            ct = e.response.headers.get("Content-Type", "") if e.response is not None else ""
            logger.warning("LLM HTTP error | model=%s api=%s status=%s content_type=%s detail=%s",
                           self._model_name, self._api_host, status, ct, detail,
                           extra={"model": self._model_name, "host": self._api_host,
                                  "status": status, "content_type": ct, "event": "http_error"})
            if status == 401:
                self.error.emit(format_error_signal(AuthError(f"API Key 认证失败，请检查密钥 ({detail})")))
            elif status == 404:
                self.error.emit(format_error_signal(ModelNotFoundError(detail or str(e))))
            else:
                msg = f"HTTP 错误 {status}: {detail or str(e)}"
                self.error.emit(format_error_signal(LLMError(msg, code="HTTP_ERROR")))
        except Exception as e:
            elapsed = time.time() - self._start_time
            logger.exception("LLM request failed | model=%s api=%s elapsed=%.1fs",
                             self._model_name, self._api_host, elapsed,
                             extra={"model": self._model_name, "host": self._api_host,
                                    "elapsed": elapsed, "event": "unknown_error"})
            self.error.emit(format_error_signal(LLMError(f"请求失败: {str(e)}")))
        finally:
            if self._response is not None:
                self._response.close()
                self._response = None

    def cancel(self):
        self._cancelled = True
        if self._response is not None:
            self._response.close()
            self._response = None
