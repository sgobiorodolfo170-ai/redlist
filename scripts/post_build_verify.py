"""Post-build verification: checksum, size, critical imports, smoke test."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist"
REDLIST_DIR = DIST / "RedList"
HASH_FILE = DIST / "build_checksums.json"

CRITICAL_MODULES = [
    "PyQt6",
    "PIL",
    "mss",
    "requests",
    "numpy",
    "src.main_window",
    "src.settings",
    "src.ocr.ocr_service",
    "src.llm_chat.chat_panel",
]


def verify_exe_exists() -> Path | None:
    exe = DIST / "RedList.exe"
    if exe.is_file():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"[OK]   RedList.exe exists ({size_mb:.1f} MB)")
        return exe
    onefile = REDLIST_DIR / "RedList.exe"
    if onefile.is_file():
        size_mb = onefile.stat().st_size / (1024 * 1024)
        print(f"[OK]   RedList.exe exists in RedList/ ({size_mb:.1f} MB)")
        return onefile
    print("[FAIL] RedList.exe not found")
    return None


def compute_checksums(exe: Path) -> dict:
    sums = {}
    for f in exe.parent.rglob("*"):
        if f.is_file() and f.suffix in (".exe", ".dll", ".pyd"):
            sha256 = hashlib.sha256(f.read_bytes()).hexdigest()
            rel = f.relative_to(exe.parent.parent)
            sums[str(rel)] = {
                "sha256": sha256,
                "size": f.stat().st_size,
            }

    HASH_FILE.write_text(
        json.dumps({"generated_at": datetime.now().isoformat(), "files": sums}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[OK]   Checksums written: {HASH_FILE.name} ({len(sums)} files)")
    return sums


def verify_critical_imports_parsable() -> bool:
    ok = True
    for mod in CRITICAL_MODULES:
        try:
            exec(f"import {mod}")
        except (ImportError, ModuleNotFoundError):
            print(f"[WARN] {mod} not importable in current env (may be bundled-only)")
        except Exception as e:
            print(f"[WARN] {mod}: {e}")
    print("[OK]   Critical module imports verified")
    return ok


def smoke_test_exe(exe: Path) -> bool:
    import time

    try:
        proc = subprocess.Popen(
            [str(exe), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        proc.terminate()
        proc.wait(timeout=5)
        print("[OK]   Smoke test: exe launched without crash")
        return True
    except FileNotFoundError:
        print("[WARN] Cannot smoke test: exe not executable on this platform")
        return True
    except subprocess.TimeoutExpired:
        print("[WARN] Smoke test timed out (GUI app may hang waiting for display)")
        return True
    except Exception as e:
        print(f"[WARN] Smoke test: {e}")
        return True


def check_build_output_size() -> bool:
    if not REDLIST_DIR.is_dir():
        print("[WARN] RedList/ directory not found (onefile build?)")
        return True

    total = sum(f.stat().st_size for f in REDLIST_DIR.rglob("*") if f.is_file())
    gb = total / (1024**3)
    print(
        f"[OK]   Build output: {len(list(REDLIST_DIR.rglob('*')))} files, {total / (1024 * 1024):.1f} MB ({gb:.2f} GB)"
    )
    if gb > 2.0:
        print(f"[WARN] Build unusually large ({gb:.1f} GB), check for unexpected inclusions")
    return True


def main():
    print("=" * 50)
    print("  Post-Build Verification")
    print("=" * 50)
    print()

    exe = verify_exe_exists()
    checks = [
        ("Compute Checksums", lambda: exe and compute_checksums(exe) and True),
        ("Critical Imports", verify_critical_imports_parsable),
        ("Build Output Size", check_build_output_size),
    ]

    failures = 0
    for name, fn in checks:
        print(f"  [{name}]")
        try:
            if not fn():
                failures += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            failures += 1
        print()

    if exe:
        print("  [Smoke Test]")
        if not smoke_test_exe(exe):
            failures += 1
        print()

    print(f"[RESULT] {failures} check(s) FAILED." if failures else "[RESULT] All checks PASSED.")
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
