import re, shutil, subprocess, sys, time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .style_service import Style
from .logger import Log, PrintBadge

# Resolve paths
ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent
SPEC_FILE: Path = ROOT_DIR / "pysidedeploy.spec"
INSTALLER_SCRIPT: Path = ROOT_DIR / "installer" / "installer.iss"

# Locates Inno Setup Compiler
ISCC_PATH: str = shutil.which("iscc") or r"F:\Program Files (x86)\Inno Setup 7\ISCC.exe"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, rem_seconds = divmod(seconds, 60)
    hours, rem_minutes = divmod(int(minutes), 60)
    if hours > 0:
        return f"{hours}h {rem_minutes}m {rem_seconds:.2f}s"
    return f"{int(minutes)}m {rem_seconds:.2f}s"


@contextmanager
def track_step(
    label: str, timings: list[tuple[str, float]]
) -> Generator[None]:
    print(f"\n{Style.CYAN}{'=' * 48}")
    print(f"{Style.BOLD}{label}{Style.RESET}")
    print(f"{Style.CYAN}{'=' * 48}{Style.RESET}")

    start: float = time.perf_counter()
    try:
        yield
    finally:
        elapsed: float = time.perf_counter() - start
        timings.append((label, elapsed))
        print(f"{Style.DIM}⏱\t{label} finished in {format_duration(elapsed)}{Style.RESET}")


def print_summary(
    timings: list[tuple[str, float]], total_elapsed: float
) -> None:
    print(f"\n{Style.CYAN}{'=' * 48}")
    print(f"{Style.BOLD}📊 BUILD TIMING SUMMARY{Style.RESET}")
    print(f"{Style.CYAN}{'=' * 48}{Style.RESET}")
    
    for label, elapsed in timings:
        elapsed_dur: str = format_duration(elapsed)
        print(f"\t{label:<34} {Style.YELLOW}{elapsed_dur:>10}{Style.RESET}")
        
    print(f"{Style.DIM}{'-' * 48}{Style.RESET}")
    
    total_elapsed_dur: str = format_duration(total_elapsed)
    print(
        f"\t{Style.BOLD}{'Total Elapsed':<34} "
        f"{Style.GREEN}{total_elapsed_dur:>10}{Style.RESET}"
    )


def clean_build_artifacts() -> None:
    artifact_dirs: list[Path] = [
        ROOT_DIR / "build",
        ROOT_DIR / "deployment",
    ]
    artifact_files: list[Path] = [
        ROOT_DIR / "PyToNingans.exe",
    ]

    removed_any: bool = False
    try:
        for directory in artifact_dirs:
            if not directory.exists(): continue
            shutil.rmtree(directory)
            PrintBadge.info()
            old_build_dir: Path = directory.relative_to(ROOT_DIR)
            print(f"Removed old build directory: {old_build_dir}")
            removed_any = True

        for file_path in artifact_files:
            if not file_path.is_file(): continue
            file_path.unlink()
            old_exec_path: Path = file_path.relative_to(ROOT_DIR)
            PrintBadge.info()
            print(f"Removed old executable: {old_exec_path}")
            removed_any = True
    except OSError as exc:
        Log.error(f"\nFailed to clean old build artifacts: {exc}")
        print(
            f"{Style.YELLOW}Close any running instances of "
            f"PyToNingans.exe and try again.{Style.RESET}"
        )
        sys.exit(1)

    if not removed_any:
        Log.info("No previous build artifacts to clean.")


def set_console_mode(mode: str) -> None:
    if not SPEC_FILE.is_file():
        Log.error(f"Spec file not found at {SPEC_FILE}.")
        sys.exit(1)

    content: str = SPEC_FILE.read_text(encoding="utf-8")
    content = re.sub(r"\s*--windows-console-mode=(disable|force|attach|hide)", "", content)

    console_mode: str = "disable" if mode == "release" else "force"
    content = re.sub(
        r"^(extra_args\s*=.*)$",
        rf"\g<1> --windows-console-mode={console_mode}",
        content,
        flags=re.MULTILINE,
    )
    SPEC_FILE.write_text(content, encoding="utf-8")
    PrintBadge.info()
    print(f"Set --windows-console-mode={console_mode}")


def run_deploy(mode: str) -> None:
    set_console_mode(mode)
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        ["pyside6-deploy", "-c", "pysidedeploy.spec"], cwd=ROOT_DIR
    )

    if result.returncode != 0:
        Log.error(f"\npyside6-deploy failed for {mode} mode.")
        sys.exit(1)

    # Ensure cloud_config.json is present in the build distribution folder if available in root
    src_config: Path = ROOT_DIR / "cloud_config.json"
    dist_dir: Path = ROOT_DIR / "build" / "PyToNingans.dist"
    if src_config.is_file() and dist_dir.is_dir():
        dest_config: Path = dist_dir / "cloud_config.json"
        shutil.copy2(src_config, dest_config)
        PrintBadge.info()
        print(f"Copied {src_config.name} to {dest_config}")


def run_inno_setup(suffix: str) -> None:
    if not Path(ISCC_PATH).exists():
        Log.error(f"Inno Setup Compiler not found at {ISCC_PATH}.")
        print(
            f"{Style.YELLOW}Please add ISCC.exe to your system PATH or "
            f"update ISCC_PATH in this script.{Style.RESET}"
        )
        sys.exit(1)

    # Extract version for a clean installer name
    content: str = INSTALLER_SCRIPT.read_text(encoding="utf-8")
    match: Optional[re.Match[str]] = re.search(
        r'^#define MyAppVersion\s+"([^"]+)"', content, re.MULTILINE
    )
    version: str = match.group(1) if match else "Unknown"

    # The /F flag forces Inno Setup to override the OutputBaseFilename
    output_name: str = f"PyToNingans-v{version}{suffix}-Win64-Installer"
    
    PrintBadge.info()
    print("Running Inno Setup Compiler...")
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        [ISCC_PATH, f"/F{output_name}", str(INSTALLER_SCRIPT)], cwd=ROOT_DIR
    )

    if result.returncode != 0:
        print("\n")
        Log.error(f"Inno Setup compilation failed.")
        sys.exit(1)
    
    PrintBadge.success()
    print(f"Installer created: {Style.BOLD}{output_name}.exe{Style.RESET}")


def main() -> None:
    args: list[str] = [arg.lower() for arg in sys.argv[1:]]
    clean: bool = "--clean" in args
    positional: list[str] = [arg for arg in args if arg != "--clean"]

    if len(positional) != 1 or positional[0] not in ["release", "debug", "both"]:
        print(
            f"{Style.YELLOW}Usage:{Style.RESET} "
            "uv run tools/build.py [release|debug|both] [--clean]"
        )
        sys.exit(1)

    target: str = positional[0]
    total_start: float = time.perf_counter()
    timings: list[tuple[str, float]] = []

    try:
        if clean:
            with track_step("🧹 CLEANING BUILD ARTIFACTS", timings):
                clean_build_artifacts()

        if target == "both":
            with track_step("🚀 BUILDING APP (RELEASE)", timings):
                run_deploy("release")
            with track_step("📦 PACKAGING INSTALLER (RELEASE)", timings):
                run_inno_setup("")

            with track_step("🚀 BUILDING APP (DEBUG)", timings):
                run_deploy("debug")
            with track_step("📦 PACKAGING INSTALLER (DEBUG)", timings):
                run_inno_setup("-with-console")
        else:
            with track_step(f"🚀 BUILDING APP ({target.upper()})", timings):
                run_deploy(target)
            suffix: str = "" if target == "release" else "-with-console"
            with track_step(f"📦 PACKAGING INSTALLER ({target.upper()})", timings):
                run_inno_setup(suffix)
    finally:
        if timings:
            print_summary(timings, time.perf_counter() - total_start)

    msg: str = "both versions" if target == "both" else f"{target} version"
    print("\n")
    Log.success(f"{Style.BOLD}[OK] Successfully built and packaged {msg}!")


if __name__ == "__main__":
    main()