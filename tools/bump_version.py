import sys, re
from pathlib import Path

# Resolve project root (<root>/tools/bump_version.py -> <root>)
ROOT_DIR = Path(__file__).resolve().parent.parent

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

def log_info(msg: str) -> None:
    print(f"[INFO]  {msg}")

def log_success(msg: str) -> None:
    print(f"[OK]    {msg}")

def log_warn(msg: str) -> None:
    print(f"[WARN]  {msg}")

def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}")

def bump_pyproject_toml(new_version: str) -> bool:
    target: Path = ROOT_DIR / "pyproject.toml"
    log_info(f"Targeting {target}...")
    if not target.is_file():
        log_error(f"File not found: {target}")
        return False

    content: str = target.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'^(version\s*=\s*")[^"]+(")',
        rf'\g<1>{new_version}\g<2>',
        content,
        flags=re.MULTILINE
    )

    if count == 0:
        log_warn("Pattern 'version = \"...\"' not found in pyproject.toml. No changes made.")
        return False

    target.write_text(updated, encoding="utf-8")
    log_success(f"Updated pyproject.toml -> {new_version} ({count} occurrence)")
    return True

def bump_installer_iss(new_version: str) -> bool:
    target: Path = ROOT_DIR / "installer" / "installer.iss"
    log_info(f"Targeting {target}...")
    if not target.is_file():
        log_error(f"File not found: {target}")
        return False

    content: str = target.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'^(#define MyAppVersion\s+")[^"]+(")',
        rf'\g<1>{new_version}\g<2>',
        content,
        flags=re.MULTILINE
    )

    if count == 0:
        log_warn("Pattern '#define MyAppVersion \"...\"' not found in installer.iss. No changes made.")
        return False

    target.write_text(updated, encoding="utf-8")
    log_success(f"Updated installer.iss -> {new_version} ({count} occurrence)")
    return True

def bump_pysidedeploy_spec(new_version: str) -> bool:
    target: Path = ROOT_DIR / "pysidedeploy.spec"
    log_info(f"Targeting {target}...")
    if not target.is_file():
        log_error(f"File not found: {target}")
        return False

    # Windows PE version strings require 4 digits (e.g., 0.7.0.0)
    win_version: str = new_version if len(new_version.split(".")) == 4 else f"{new_version}.0"

    content: str = target.read_text(encoding="utf-8")
    updated, count_file = re.subn(
        r'(--windows-file-version=)[^\s"]+',
        rf'\g<1>{win_version}',
        content
    )
    updated, count_prod = re.subn(
        r'(--windows-product-version=)[^\s"]+',
        rf'\g<1>{win_version}',
        updated
    )

    if count_file == 0 and count_prod == 0:
        log_warn("Version flags '--windows-*-version=' not found in pysidedeploy.spec. No changes made.")
        return False

    target.write_text(updated, encoding="utf-8")
    log_success(
        f"Updated pysidedeploy.spec -> {win_version} "
        f"(--windows-file-version: {count_file}, --windows-product-version: {count_prod})"
    )
    return True

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:   uv run tools/bump_version.py <version>")
        print("Example: uv run tools/bump_version.py 0.7.0")
        sys.exit(1)

    target_version: str = sys.argv[1].strip()
    log_info(f"Project root resolved to: {ROOT_DIR}")

    if not SEMVER_PATTERN.match(target_version):
        log_warn(f"'{target_version}' does not match standard 3-digit semver (X.Y.Z). Proceeding anyway.")

    results: list[bool] = [
        bump_pyproject_toml(target_version),
        bump_installer_iss(target_version),
        bump_pysidedeploy_spec(target_version),
    ]

    if all(results):
        log_success(f"All target configurations successfully updated to v{target_version}.")
    else:
        failed = sum(1 for r in results if not r)
        log_error(f"{failed} file(s) failed or had no matching patterns. Review logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()