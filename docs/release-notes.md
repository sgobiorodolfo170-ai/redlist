# Release Notes

## v3.2 (2026-06-15)

LLM 对话模块发布版本，同时包含 ORM 生命周期管理与内存优化。

### 新增功能
- **LLM 对话面板**：截图+大模型对话选项卡，支持自定义模型提供商（URL + API Key + 模型名称）
- **自定义提示词专家**：用户自定义 system prompt，选中后自动注入
- **流式输出**：逐字显示模型回复，支持 Markdown + 代码块渲染
- **会话管理**：左侧会话列表，支持新建/重命名/删除，本地 JSON 持久化
- **助手气泡工具栏**：复制、导出为 Markdown、重新生成（仅对最后一条消息有效）
- **中文右击菜单**：QTextEdit/QLineEdit 原生中文菜单（撤销/重做/剪切/复制/粘贴/删除/全选）
- **输入框自动聚焦**：发送后自动回到输入框，按 Enter 发送 / Shift+Enter 换行

### 架构变更
- 新建 `src/llm_chat/` 包，包含 10 个模块
- 主窗口新增 🤖 工具按钮，注册 ChatPanel

### 内存管理
- OCR 服务生命周期管理：延迟加载 + 主动释放资源，避免内存泄漏
- 便签数量限制：单实例模式，防止多窗口内存溢出
- 提示音 MCI 资源释放：确保播放后正确释放

### 模块重构
- 提取 `theme.py`：统一主题颜色和样式管理
- 提取 `sound.py`：统一提示音播放（MCI 接口封装）
- 提取 `_BaseMaskOverlay`：消除 overlay 模块中的重复类
- 合并百度翻译方法：统一翻译服务调用逻辑

### 代码质量
- 修复潜在死代码崩溃漏洞
- 统一日志格式化（% 格式化）
- 新增 pre-commit 配置（代码质量检查）

### 问题修复
- 修复 main_window.py 中 settings_btn 未注册导致的 KeyError
- 修复 sticky_note/manager.py 中 MAX_NOTES 循环导入
- 修复 input_bar.py `reload_providers()` blockSignals 永不释放
- 修复 model_combo/expert_combo 选择 "✚ 自定义..." 无响应
- 修复 chat_display.py 切换会话时 `update_temp_bubble` RuntimeError
- 修复 settings 不保存（list() 拷贝避免同引用比较提前 return）
- 修复流式响应空数组 `IndexError`
- 修复 `llm_service.py` 四个 bug：会话切换污染、response 泄漏、错误体暴露、流式超时
- 修复流式气泡 `_raw_text` 未初始化导致的 AttributeError

## v3.1 (2026-06-11)

代码重构与工程化改进版本。

### 模块重构
- `screenshot.py` 拆分为 `screenshot/` 包（region_selector / translate_panel / translation_thread）
- `sticky_note.py` 拆分为 `sticky_note/` 包（manager / window / panel）
- 公共工具提取到 `src/utils/`：`color.py`（颜色处理）、`geometry.py`（矩形碰撞检测）、`sound.py`（提示音）、`theme.py`（主题）

### 打包与工程化
- 优化 `build_final.spec`：`console=False`，排除大型可选依赖，exe 约 150MB
- 新增 `报错日志.md` 崩溃错误日志机制（写入 exe 所在目录）
- 新增 `pyproject.toml` 项目元数据 + pytest 配置
- 新增 `requirements-dev.txt` 开发依赖分离
- CI 增强：`PYTHONUTF8` 编码、pip 缓存、覆盖率报告

### 新增测试
- `test_color.py` — 颜色工具函数测试
- `test_geometry.py` — 矩形碰撞检测测试
- `test_screenshot_translate.py` — 截图翻译模块测试

### 问题修复
- 修复 `screenshot.py` 与 `screenshot/` 包同名冲突导致的导入错误
- 修复死代码崩溃漏洞（deep_merge/remove_none_values）
- 修复 logger 模式不一致（f-string vs % 格式化）
- 移除已废弃的 DeepL 翻译服务

## v3.0 (2026-04-03)

正式版稳定发布。

### 核心功能
- 任务管理：创建、编辑、删除待办事项
- 便签功能：桌面便签，支持磁吸和自定义
- 定时器：灵活的计时和提醒功能
- 截图工具：快速截图并保存
- 截图翻译：OCR 识别 + 多语言翻译

### 翻译服务
- 百度大模型文本翻译
- 百度通用文本翻译
- 腾讯翻译君

### 界面特性
- 简洁现代的用户界面
- 选项卡式布局
- 自定义设置
- 开机自启动选项

### 安全性
- API 密钥本地加密存储，无硬编码
- 所有数据本地存储，不上传用户数据

---

## v2.1 (2026-04-03)

### 新增功能
- 百度大模型文本翻译支持
- 百度通用文本翻译支持
- 优化的翻译配置界面

### 改进优化
- 截图翻译功能优化
- 界面布局优化
- 代码结构优化

### 问题修复
- 修复 OCR 相关问题
- 修复配置保存问题
- 修复界面显示问题

### 移除功能
- 快捷键功能（避免冲突）

### 代码清理
- 删除 115 个冗余文件
- 移除所有测试代码
- 清理技术文档
- 优化项目结构
