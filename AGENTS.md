# Agent 规则

## 提交规范
- 每次修改结束后必须提交 git。
- 只暂存当前会话中修改过的文件。
- 使用描述性的中文提交信息（例如 "fix: 粒子颜色改为粉红"）。
- 如果用户要求修改但没有明确要求提交，则在结束时自动提交。

## 构建
- 编辑 `src/timer.py` 或 `resources/heartbeat3d/heartbeat3d.js` 后，运行 `pyinstaller build_final.spec` 并确认构建成功。
