# 开发者指南

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.8+ | 核心编程语言 |
| PyQt6 6.6.1 | GUI 框架 |
| OpenAI API (兼容) | LLM 对话 API 调用 |
| PaddlePaddle 2.6.1 | 深度学习框架（OCR 引擎后端，延迟加载） |
| PaddleOCR 2.9.1 | 光学字符识别 |
| Pillow | 图像处理 |
| mss | 跨平台截图 |
| requests | HTTP 客户端（翻译 API） |
| tencentcloud-sdk-python | 腾讯云机器翻译 SDK |
| pytest 7+ | 单元测试 |
| PyInstaller | 打包为可执行文件 |

## 项目结构

```
├── main.py                  # 应用入口（含全局异常捕获 → 报错日志.md）
├── requirements.txt         # Python 依赖
├── requirements-dev.txt     # 开发依赖（pytest 等）
├── pyproject.toml           # 项目元数据 + pytest 配置
├── build_final.spec         # PyInstaller 打包配置
├── hook_paddleocr.py        # PyInstaller PaddleOCR 运行时钩子
├── src/
│   ├── main_window.py       # 主窗口（QTabWidget 组织各面板）
│   ├── settings.py          # 配置管理（加密存储到 %APPDATA%/RedList/）
│   ├── settings_panel.py    # 设置面板 UI
│   ├── theme.py             # 主题颜色和样式管理
│   ├── screenshot_translate.py  # 向后兼容 re-export 模块
│   ├── task_panel.py        # 任务面板
│   ├── timer.py             # 定时器
│   ├── screenshot/          # 截图模块（包）
│   │   ├── __init__.py      # 统一导出（含老旧 screenshot_legacy 类）
│   │   ├── region_selector.py   # 屏幕区域选择器
│   │   ├── translate_panel.py   # 截图翻译面板（核心逻辑）
│   │   └── translation_thread.py # 异步翻译线程
│   ├── sticky_note/         # 便签模块（包）
│   │   ├── __init__.py
│   │   ├── manager.py       # 便签管理器
│   │   ├── window.py        # 便签窗口
│   │   └── panel.py         # 便签设置面板
│   ├── screenshot_legacy.py # 旧截图模块（ScreenshotManager/ConfirmDialog/ScreenshotPanel）
│   ├── translation/
│   │   ├── __init__.py
│   │   └── translation_service.py  # 翻译服务抽象（百度/腾讯）
│   ├── llm_chat/           # LLM 对话模块（包）
│   │   ├── __init__.py
│   │   ├── chat_panel.py       # 对话主面板（QSplitter 左右分栏）
│   │   ├── chat_display.py     # 气泡消息展示区（Markdown + 代码块 + 工具栏）
│   │   ├── conversation_list.py # 左侧会话列表
│   │   ├── input_bar.py        # 输入栏（多行 QTextEdit + 模型/专家选择）
│   │   ├── llm_service.py      # QThread 流式调用 OpenAI 兼容 API
│   │   ├── conversation_manager.py # 会话 JSON 持久化
│   │   ├── model_dialog.py     # 自定义模型弹窗
│   │   ├── prompt_expert_dialog.py # 自定义提示词专家弹窗
│   │   └── chinese_menu.py     # 中文右击菜单工具函数
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── ocr_service.py   # OCR 服务（PaddleOCR，延迟加载）
│   ├── overlay/
│   │   ├── __init__.py
│   │   ├── overlay_window.py   # 通用覆盖窗口
│   │   ├── mask_overlay.py     # 文字遮罩覆盖层
│   │   └── mask_translation_overlay.py  # 翻译结果遮罩
│   └── utils/
│       ├── __init__.py
│       ├── cache.py         # LRU + TTL 缓存
│       ├── color.py         # 颜色工具（lighten_color/darken_color）
│       ├── debounce.py      # 防抖执行器
│       ├── geometry.py      # 矩形碰撞检测
│       ├── logger.py        # 日志配置
│       └── sound.py         # 提示音播放
├── tests/                   # 单元测试
│   ├── test_color.py
│   ├── test_geometry.py
│   ├── test_screenshot_translate.py
│   └── conftest.py
├── resources/
│   └── sounds/              # 提示音文件
├── app-icons/               # 应用图标
├── docs/                    # 文档
└── dist/                    # 构建输出
```

## 从源码运行

```bash
pip install -r requirements-dev.txt
pytest          # 运行测试
python main.py  # 启动应用
```

## 运行测试

```bash
pytest -v               # 全部测试
pytest -m "not heavy"   # 跳过重量级测试（CI 默认）
pytest --coverage       # 含覆盖率报告
```

## 构建应用

### 一键构建（含安全护栏）

```bash
python scripts/pre_build_check.py    # 预构建检查
pyinstaller build_final.spec         # 构建
python scripts/post_build_verify.py  # 构建后验证
```

### 快速构建

```bash
pyinstaller build_final.spec
```

构建后的可执行文件位于 `dist/RedList/RedList.exe`，约 150MB（不含 PaddleOCR 模型，首次运行时自动下载）。

> 注意：`build_final.spec` 中 `hiddenimports` 需包含 `src.llm_chat` 及其子模块。构建超时建议 ≥ 600s。

## LLM 对话模块

### 自定义模型提供商

模型信息存储在 `settings.json` 的 `llm_providers` 字段，支持任意 OpenAI 兼容 API：
- URL（API 端点）
- API Key
- 模型名称（如 gpt-4o、deepseek-chat）

通过 🤖 面板的「模型选择」→「✚ 自定义」添加。

### 提示词专家

`prompt_experts` 字段存储自定义 system prompt，选中后自动注入 messages。

### 会话持久化

```
%APPDATA%/RedList/conversations/
├── <conv_id>.json     # 单条会话（messages 列表）
```

### 关键约定

- 流式输出: QThread + SSE 逐行解析，`accumulated_text` 追踪全文
- 气泡高度: `document().setTextWidth(text_width)` → `size().height() + padding`
- 助手气泡底部工具栏: 复制/导出 Markdown/重新生成（仅最后一条）
- 回车发送 / Shift+Enter 换行，发送后自动聚焦输入框
- 中文右击菜单: `createStandardContextMenu()` + `chinese_menu.py` 翻译

## 构建安全护栏

### 预构建检查 (`scripts/pre_build_check.py`)

构建前自动执行以下验证，确保构建质量：
- **版本一致性**：`pyproject.toml` 版本号与 `docs/release-notes.md` 最新版本一致
- **Git 状态**：检测未提交的变更（警告，不阻塞）
- **测试完整性**：确认 `tests/` 目录存在且有测试文件
- **构建配置**：确认 `build_final.spec` 存在且包含 `hiddenimports`

在构建前手动运行：
```bash
python scripts/pre_build_check.py
```

### 构建后验证 (`scripts/post_build_verify.py`)

构建完成后自动执行：
- **产物存在性**：确认 `RedList.exe` 已生成，检查文件大小
- **SHA-256 校验和**：为所有 `.exe/.dll/.pyd` 文件生成哈希清单到 `dist/build_checksums.json`
- **构建体积审计**：输出文件总数和总大小，异常大时警告
- **关键模块可解析性**：验证 PyQt6/PIL/numpy 等核心依赖可导入

```bash
python scripts/post_build_verify.py
```

### CI 流水线 (`quality.yml`)

GitHub Actions 包含 4 个并行 job：

| Job | 工具 | 作用 |
|---|---|---|
| `lint` | ruff | 代码风格 + 格式检查 |
| `test` | pytest + pytest-cov | 单元测试 + 覆盖率 |
| `security` | bandit | 安全漏洞扫描 |
| `pre-build` | pre_build_check.py | 版本一致性 + 构建前置条件 |

### Pre-commit 钩子

| 钩子 | 作用 |
|---|---|
| `trailing-whitespace` | 去除行尾多余空格 |
| `end-of-file-fixer` | 确保文件以空行结尾 |
| `check-yaml` / `check-json` | YAML/JSON 语法校验 |
| `check-added-large-files` | 阻止 >500KB 文件提交 |
| `check-case-conflict` | 检查文件名大小写冲突 |
| `check-merge-conflict` | 检测残留的合并冲突标记 |
| `detect-private-key` | 防止私钥泄露 |
| `ruff check --fix` | 代码问题自动修复 |
| `ruff-format` | 代码格式化 |
| `mypy` | 静态类型检查 |
| `bandit` | Python 安全扫描 |

## 配置与调试

### 用户数据位置

```
%APPDATA%/RedList/
├── settings.json    # 加密配置
├── tasks/           # 任务数据
└── notes/           # 便签数据
```

### 错误日志

应用在启动和运行时的未捕获异常会自动写入 exe 所在目录的 `报错日志.md`，格式为 Markdown 表格。

## 扩展指南

### 添加新的翻译服务

1. 在 `src/translation/translation_service.py` 中添加新的翻译器类，继承 `BaseTranslator`
2. 实现 `translate(text, source, target)` 方法
3. 在 `TranslationService.create_translator()` 中注册新服务商

### 更换 OCR 引擎

1. 在 `src/ocr/ocr_service.py` 中替换或扩展 OCR 实现
2. 保持 `ocr_image(image) -> list[OCRResult]` 接口签名

### 模块拆分规范

- 当一个 .py 文件超过 300 行或有明显可分离的职责时，应拆分为包（package）
- 公共工具函数提取到 `src/utils/` 对应的模块
- 包内的 `__init__.py` 作为统一导出入口，不要包含业务逻辑
