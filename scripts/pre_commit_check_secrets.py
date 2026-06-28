"""Pre-commit hook: detect API keys and secrets before they reach the remote."""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

BANNED_PATTERNS = [
    (r"(?i)(sk-[A-Za-z0-9_-]{20,})", "OpenAI/LLM API key (sk-...)"),
    (r"(?i)(api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,})", "Generic API key assignment"),
    (r"(?i)(secret[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,})", "Secret key assignment"),
    (r"(?i)(AKID[A-Za-z0-9_-]{16,})", "Tencent Cloud Secret ID (AKID...)"),
    (r"(?i)(app[_-]?id\s*[=:]\s*['\"]?\d{10,})", "App ID (10+ digits)"),
    (r"(?i)(app[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,})", "App Key"),
]

EXCLUDE_FILES = [".pre-commit-config.yaml", "scripts/pre_commit_check_secrets.py"]


def find_sensitive_files() -> list[tuple[Path, str, str]]:
    findings = []
    for path in REPO.rglob("*"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.is_dir() or path.suffix in (".pyc", ".exe", ".dll", ".pyd", ".ico"):
            continue
        relative = path.relative_to(REPO)
        if str(relative) in EXCLUDE_FILES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, desc in BANNED_PATTERNS:
            if re.search(pattern, content):
                findings.append((relative, desc, content))
    return findings


def main():
    findings = find_sensitive_files()
    if not findings:
        print("[OK] No API keys or secrets detected.")
        sys.exit(0)

    print("[FAIL] Potential API keys/secrets found in tracked files:")
    for path, desc, _ in findings:
        print(f"       {path} — {desc}")
    print()
    print("If these are false positives, add the file to EXCLUDE_FILES in this script.")
    print("If these contain real credentials, remove them from the repo immediately.")
    sys.exit(1)


if __name__ == "__main__":
    main()
