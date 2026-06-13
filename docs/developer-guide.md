# 开发者指南

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.8+ | 核心编程语言 |
| PyQt6 6.6.1 | GUI 框架 |
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

```bash
pyinstaller build_final.spec
```

构建后的可执行文件位于 `dist/RedList/RedList.exe`，约 150MB（不含 PaddleOCR 模型，首次运行时自动下载）。

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
