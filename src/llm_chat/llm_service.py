import json
import time

import requests

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.logger import get_logger

logger = get_logger("LLMService")

_STREAM_TIMEOUT = 300


class LLMService(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, messages, model_config):
        super().__init__()
        self.messages = messages
        self.model_config = model_config
        self._cancelled = False
        self._response = None

    def run(self):
        api_url = self.model_config.get('api_url', '').rstrip('/')
        api_key = self.model_config.get('api_key', '')
        model_name = self.model_config.get('model_name', '')

        if not api_url or not api_key or not model_name:
            self.error.emit("模型配置不完整，请检查 API 地址、Key 和模型名称")
            return

        url = f"{api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": self.messages,
            "stream": True,
        }

        try:
            self._response = requests.post(
                url, headers=headers, json=payload, stream=True, timeout=120
            )
            self._response.raise_for_status()

            full_text = ""
            start_time = time.time()
            for line in self._response.iter_lines(decode_unicode=True):
                if self._cancelled:
                    break
                if time.time() - start_time > _STREAM_TIMEOUT:
                    self.error.emit("流式响应超时，请重试")
                    return
                if not line:
                    continue
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
                            full_text += content
                            self.chunk_received.emit(content)
                    except json.JSONDecodeError:
                        continue

            if not self._cancelled:
                self.finished.emit(full_text)

        except requests.exceptions.Timeout:
            self.error.emit("请求超时，请检查网络连接或 API 地址")
        except requests.exceptions.ConnectionError:
            self.error.emit("无法连接到 API 服务器，请检查接口地址")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            detail = ""
            if e.response is not None:
                try:
                    detail = e.response.text[:200]
                except Exception:
                    pass
            if status == 401:
                self.error.emit(f"API Key 认证失败，请检查密钥 ({detail})")
            elif status == 404:
                self.error.emit(f"模型不存在或接口地址错误 ({detail})")
            else:
                self.error.emit(f"HTTP 错误 {status}: {detail or str(e)}")
        except Exception as e:
            self.error.emit(f"请求失败: {str(e)}")
            logger.exception("LLM request failed")
        finally:
            if self._response is not None:
                self._response.close()
                self._response = None

    def cancel(self):
        self._cancelled = True
        if self._response is not None:
            self._response.close()
            self._response = None
