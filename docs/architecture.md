# 架构说明

## 整体架构

RedList 采用模块化单体架构，各功能模块通过主窗口协调工作。

```
┌───────────────────────────────────────────────────────┐
│                     MainWindow                         │
│  ┌──────────┬────────────┬──────────┬──────────────┬──────────────┐  │
│  │ TaskPanel │  StickyNote │  Timer   │ Screenshot  │  LLM Chat   │  │
│  │           │  (package)  │          │  (package)  │  (package)  │  │
│  └──────────┴────────────┴──────────┴──────────────┴──────────────┘  │
│  ┌───────────────────────────────────────────────────┐ │
│  │              SettingsPanel                         │ │
│  └───────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
  ┌────────────┐     ┌──────────────────┐
  │ OCR Service│     │TranslationService │
  │ (PaddleOCR)│     │(Baidu/Tencent)   │
  └────────────┘     └──────────────────┘
```

## 模块说明

### main_window.py
应用主窗口，通过 QTabWidget 组织各功能面板，管理全局状态和应用生命周期。

### task_panel.py
待办事项管理面板，支持创建、编辑、删除、标记完成。数据本地持久化。

### sticky_note/ (package)
桌面便签模块。包含 `manager.py`（管理器）、`window.py`（窗口）、`panel.py`（设置面板）。支持磁吸到屏幕边缘和自定义样式。

### timer.py
定时器模块，支持倒计时和到期提醒播放提示音。

### llm_chat/ (package)
LLM 对话模块。包含 `chat_panel.py`（主面板，QSplitter 左右分栏）、`chat_display.py`（气泡消息展示，Markdown/代码块渲染、工具栏）、`conversation_list.py`（左侧会话列表）、`input_bar.py`（多行输入栏 + 模型/专家选择）、`llm_service.py`（QThread 流式调用 OpenAI 兼容 API）、`conversation_manager.py`（会话 JSON 持久化）、`model_dialog.py` / `prompt_expert_dialog.py`（自定义弹窗）、`chinese_menu.py`（中文右击菜单）。

### screenshot/ (package)
截图模块。包含 `screenshot_manager.py`（原 `screenshot_legacy.py` 中的 `ScreenshotManager`）、`translate_panel.py`（截图翻译面板）、`region_selector.py`（区域选择器）、`translation_thread.py`（翻译线程）。

### screenshot_translate.py -> screenshot/translate_panel.py
`src/screenshot_translate.py` 现为向后兼容的 re-export 模块。截图翻译的核心逻辑已迁移到 `src/screenshot/translate_panel.py`。

### ocr/
OCR 服务层，封装 PaddleOCR（延迟加载，首次使用时初始化），提供统一的文字识别接口。

### translation/
翻译服务抽象层，统一接口支持多服务商切换（百度大模型、百度通用、腾讯翻译）。通过 `TranslationService` 单例管理。

### overlay/
屏幕覆盖层窗口，用于截图区域的遮罩和交互选取。包含 `mask_overlay.py`（文字遮罩）和 `overlay_window.py`（通用覆盖窗口）。

### utils/
通用工具模块：
- `geometry.py` — 矩形重叠检测（`is_horizontal_overlap` / `is_vertical_overlap`），提取自 sticky_note
- `color.py` — 颜色处理（`lighten_color` / `darken_color`），提取自 translate_panel
- `cache.py` — LRU 缓存 + TTL，用于 OCR 和翻译结果缓存
- `debounce.py` — 防抖执行器，用于配置自动保存
- `logger.py` — 日志配置，统一的日志输出格式
- `sound.py` — 系统提示音播放（基于 MCI，已优化资源释放）

### theme.py
统一主题颜色和样式管理，提供界面配色方案。

### settings.py
配置管理。使用 `%APPDATA%/RedList/settings.json` 持久化，含防抖自动保存。

## 数据流

### LLM 对话流程

```
用户输入文本 + 可选截图 → ChatPanel 构建 API messages
    → LLMService (QThread) 流式调用 OpenAI 兼容 API
    → ChatDisplay.update_temp_bubble 逐字渲染
    → 完成后 finalize_temp_bubble 显示工具栏（复制/导出/重新生成）
    → ConversationManager 持久化到 JSON
```

### 截图翻译流程

```
用户触发截图 → RegionSelector 区域选择
    → mss 截图 → OCR 识别文字 → TranslationThread 异步翻译
    → MaskTranslationOverlay 显示结果
```

### 配置存储流程

```
设置界面修改 → Debouncer (500ms) 防抖 → settings.json
    → 应用启动时自动加载
```

### 运行模式

```
源码运行: main.py → QApplication → MainWindow → 各 Panel
打包运行: RedList.exe → sys._MEIPASS 资源路径 → 同上
          崩溃时自动生成 报错日志.md
```
