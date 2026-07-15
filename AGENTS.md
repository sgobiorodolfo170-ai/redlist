# Agent Rules

## Commit Discipline
- Every modification session must end with a git commit.
- Stage only the files that were changed during the session.
- Use a descriptive Chinese commit message (e.g., "fix: 粒子颜色改为粉红").
- If user requests changes but no explicit commit command, commit automatically at the end.

## Build
- After editing `src/timer.py` or `resources/heartbeat3d/heartbeat3d.js`, run `pyinstaller build_final.spec` and confirm the build succeeds.
