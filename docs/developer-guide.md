# 开发者指南

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.8+ | 核心编程语言 |
| PyQt6 6.6.1 | GUI 框架 |
| PaddlePaddle 2.6.1 | 深度学习框架（OCR 引擎后端） |
| PaddleOCR 2.9.1 | 光学字符识别 |
| Pillow | 图像处理 |
| mss | 跨平台截图 |
| requests | HTTP 客户端（翻译 API） |
| tencentcloud-sdk-python | 腾讯云机器翻译 SDK |
| PyInstaller | 打包为可执行文件 |
| NSIS | Windows 安装程序 |

## 项目结构

```
├── main.py                  # 应用入口
├── requirements.txt         # Python 依赖
├── build_final.spec         # PyInstaller 打包配置
├── installer.nsi            # NSIS 安装程序脚本
├── hook_paddleocr.py        # PyInstaller PaddleOCR 钩子
├── src/
│   ├── main_window.py       # 主窗口
│   ├── settings.py          # 配置管理
│   ├── settings_panel.py    # 设置面板
│   ├── screenshot.py        # 截图功能
│   ├── screenshot_translate.py  # 截图翻译
│   ├── task_panel.py        # 任务面板
│   ├── sticky_note.py       # 便签功能
│   ├── timer.py             # 定时器
│   ├── translation/
│   │   ├── __init__.py
│   │   └── translation_service.py  # 翻译服务抽象
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── ocr_service.py   # OCR 服务封装
│   └── overlay/
│       ├── __init__.py
│       ├── overlay_window.py
│       └── mask_overlay.py
├── resources/
│   └── sounds/              # 提示音文件
├── app-icons/               # 应用图标
├── docs/                    # 文档
└── dist/                    # 构建输出
```

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

## 构建应用

### 简单构建

```bash
简单构建.bat
```

### 完整构建（含安装程序）

```bash
一键构建.bat
```

### 构建输出

构建后的可执行文件位于 `dist/RedList/RedList.exe`，大小约 726MB（含所有依赖和 OCR 模型）。

## 扩展指南

### 添加新的翻译服务

1. 在 `src/translation/translation_service.py` 中添加新的翻译器类，继承现有抽象基类
2. 实现翻译接口方法
3. 在设置面板中注册新的服务商选项

### 更换 OCR 引擎

1. 在 `src/ocr/ocr_service.py` 中替换或扩展 OCR 实现
2. 确保保持相同的接口签名
