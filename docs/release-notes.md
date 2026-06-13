# Release Notes

## v3.1 (2026-06-11)

代码重构与工程化改进版本。

### 模块重构
- `screenshot.py` 拆分为 `screenshot/` 包（region_selector / translate_panel / translation_thread）
- `sticky_note.py` 拆分为 `sticky_note/` 包（manager / window / panel）
- 公共工具提取到 `src/utils/`：`color.py`（颜色处理）、`geometry.py`（矩形碰撞检测）

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
