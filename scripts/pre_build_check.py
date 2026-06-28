"""Pre-build validation: version consistency, git state, dependency checks."""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def check_version_consistency() -> bool:
    ok = True
    pyproject = REPO / "pyproject.toml"
    release_notes = REPO / "docs" / "release-notes.md"

    pyproject_ver = None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if m := re.match(r'^version\s*=\s*"(.+)"', line):
            pyproject_ver = m.group(1)
            break

    if not pyproject_ver:
        print("[FAIL] pyproject.toml: version not found")
        return False

    rn_versions = re.findall(r"^## v(\S+)", release_notes.read_text(encoding="utf-8"), re.MULTILINE)
    latest_rn = max(rn_versions, key=lambda v: [int(x) for x in v.split(".")]) if rn_versions else None

    if not latest_rn:
        print("[FAIL] release-notes.md: no versions found")
        return False

    def normalize(v: str) -> tuple:
        parts = v.split(".")
        return tuple(int(p) for p in parts + ["0"] * (3 - len(parts)))

    if normalize(pyproject_ver) != normalize(latest_rn):
        print(f"[FAIL] Version mismatch: pyproject.toml={pyproject_ver}, release-notes.md={latest_rn}")
        ok = False
    else:
        print(f"[OK]   Version consistent: {pyproject_ver}")

    return ok


def check_clean_git() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO, check=True, timeout=15
        )
        if result.stdout.strip():
            print("[WARN] Uncommitted changes detected:")
            for line in result.stdout.strip().splitlines()[:10]:
                print(f"       {line}")
            return True
        print("[OK]   Working tree clean")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[WARN] git not available, skipping dirty check")
        return True


def check_builtin_tests() -> bool:
    ok = True
    tests_dir = REPO / "tests"
    if not tests_dir.is_dir():
        print("[FAIL] tests/ directory missing")
        return False

    test_files = list(tests_dir.glob("test_*.py"))
    if not test_files:
        print("[FAIL] No test files found in tests/")
        return False

    print(f"[OK]   {len(test_files)} test files found")
    return ok


def check_build_spec() -> bool:
    spec = REPO / "build_final.spec"
    if not spec.is_file():
        print("[FAIL] build_final.spec not found")
        return False

    content = spec.read_text(encoding="utf-8")
    if "hiddenimports" not in content:
        print("[FAIL] build_final.spec missing hiddenimports")
        return False

    print("[OK]   build_final.spec present")
    return True


def main():
    print("=" * 50)
    print("  Pre-Build Safety Checks")
    print("=" * 50)
    print()

    checks = [
        ("Version Consistency", check_version_consistency),
        ("Clean Git Status", check_clean_git),
        ("Test Files", check_builtin_tests),
        ("Build Spec", check_build_spec),
    ]

    failures = 0
    for name, fn in checks:
        print(f"  [{name}]")
        if not fn():
            failures += 1
        print()

    if failures:
        print(f"[RESULT] {failures} check(s) FAILED. Fix before building.")
        sys.exit(1)
    else:
        print("[RESULT] All checks PASSED. Ready to build.")


if __name__ == "__main__":
    main()
