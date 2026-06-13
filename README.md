# RedList 3.0

简洁高效的待办事项和截图翻译工具。

## 功能

任务管理 · 桌面便签 · 定时器 · 截图 · 截图翻译（OCR + 多语言翻译）

## 快速开始

**运行构建版本**：进入 `dist/RedList/` 双击 `RedList.exe`

> 如启动失败，查看同目录的 `报错日志.md` 了解错误详情。

**从源码运行**：

```bash
pip install -r requirements-dev.txt
pytest           # 运行测试（可选）
python main.py
```

## 文档

| 文档 | 说明 |
|------|------|
| [用户指南](docs/user-guide.md) | 完整用法、配置翻译服务、设置说明 |
| [开发者指南](docs/developer-guide.md) | 技术栈、项目结构、构建和扩展 |
| [架构说明](docs/architecture.md) | 模块关系、数据流 |
| [发布说明](docs/release-notes.md) | 版本历史和更新日志 |

## 许可证

MIT License。详见 [LICENSE.txt](LICENSE.txt)。
