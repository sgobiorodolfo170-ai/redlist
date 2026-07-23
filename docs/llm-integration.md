# LLM 集成指南

## 编码规范

所有 LLM API 交互必须遵循以下编码约定以防止乱码（mojibake）：

### 输出端（API 调用 → 应用）

```python
from utils.encoding import safe_decode, validate_utf8_response, force_utf8_response

# 1. 强制响应使用 UTF-8 解码
force_utf8_response(response)

# 2. 验证响应编码声明
validate_utf8_response(response, log_prefix="LLM ")

# 3. 逐行解码时使用 safe_decode（而非 decode_unicode=True）
for raw_line in response.iter_lines(decode_unicode=False):
    line = safe_decode(raw_line, "utf-8")
```

### 输入端（用户内容 → 显示/存储）

```python
from utils.encoding import ensure_utf8

# 确保渲染和拷贝内容为有效 UTF-8
safe_display_text = ensure_utf8(raw_content)
```

### 文件持久化

```python
from utils.encoding import read_file_with_fallback_encoding

# 自动尝试 utf-8 → gbk → gb18030，自动重写非 UTF-8 文件
content, encoding, err = read_file_with_fallback_encoding(filepath)
```

## 错误码表

所有 LLM 错误信号使用 `[CODE] message` 格式。`chat_panel.on_llm_error` 根据 CODE 分发中文提示。

| CODE | 含义 | 中文提示 | 触发位置 |
|------|------|---------|---------|
| `AUTH_ERROR` | API Key 认证失败 | API Key 认证失败 | `llm_service.py` status=401 |
| `MODEL_NOT_FOUND` | 模型不存在 | 模型不存在或已下线，请检查模型名称 | `llm_service.py` status=404 |
| `RATE_LIMIT` | 请求频率超限 | 请求频率超限，请稍后重试 | `llm_service.py` status=429 |
| `STREAM_DECODE` | 流式响应解码失败 | 服务器返回编码异常 | `llm_service.py` decode 异常 |
| `TIMEOUT` | 请求超时 | 连接超时，请检查网络或代理设置 | `llm_service.py` timeout / `STREAM_TIMEOUT` |
| `CONNECTION_ERROR` | 网络连接失败 | 无法连接服务器，请检查网络和 API 地址 | `llm_service.py` ConnectionError |
| `HTTP_ERROR` | HTTP 错误（其他状态码） | HTTP 错误 {status_code} | `llm_service.py` 其他 status |
| `INVALID_CONFIG` | 模型配置无效 | 配置参数不符合要求，请检查对话框 | `model_dialog.py` 验证失败 |
| `LLM_ERROR` | 未分类错误 | 发生了未知错误，请重试 | 兜底分支 |

### 添加新错误码

1. 在 `exceptions.py` 定义新异常类（继承 `LLMError`）
2. 在 `llm_service.py` 对应位置 `emit(format_error_signal(NewException(...)))`
3. 在 `chat_panel.py` `on_llm_error` 添加 `if code == "NEW_CODE":` 分支

## 添加新模型

### 步骤

1. 运行应用 → LLM Chat → 模型管理 → 添加模型
2. 填写：
   - **显示名称**：任意标识名
   - **API 地址**：必须 http:// 或 https:// 开头，格式 `https://api.example.com/v1/chat/completions`
   - **API Key**：至少 8 字符
   - **模型名**：服务商实际模型 ID（如 `gpt-4o`）
3. 可选参数（留空使用 API 默认值）：
   - Temperature：0.0–2.0
   - Max Tokens：1–32768
   - Top P：0.0–1.0

### 验证

模型配置保存时通过 `config.py` 的 `ModelConfig`（Pydantic v2）校验：

- `api_url`：有效 http/https URL
- `api_key`：最小长度 8
- `temperature`：0–2 范围
- `max_tokens`：1–32768 范围
- `top_p`：0–1 范围

### API 兼容性要求

本工具通过 OpenAI 兼容 API（`POST /v1/chat/completions`）调用 LLM。要求服务商支持：

- SSE 流式响应（`stream: true`）
- 标准 `choices[].delta.content` 格式
- 以 `data: [DONE]` 结束流

## 编码修复历史

### 问题
GBK 编码下读写包含 UTF-8 中文的 JSON 文件导致永久性乱码（"锟斤拷"），LLM 流式响应因 `decode_unicode=True` 的隐式编码推断触发解码异常。

### 修复（2026-07）

| 文件 | 修改内容 |
|------|---------|
| `utils/encoding.py` | 新建：ensure_utf8、safe_decode、read_file_with_fallback_encoding、rewrite_file_as_utf8、validate_utf8_response、force_utf8_response |
| `llm_service.py` | 请求头声明 UTF-8；iter_lines 改为 decode_unicode=False + safe_decode；调用 force_utf8_response + validate_utf8_response |
| `chat_display.py` | append_message 和 update_temp_bubble 入口调用 ensure_utf8；_raw_text 存储净化文本 |
| `settings.py` | load_settings 使用 read_file_with_fallback_encoding + rewrite_file_as_utf8 |
| `conversation_manager.py` | list_conversations 和 get_conversation 使用 read_file_with_fallback_encoding |
