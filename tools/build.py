import sys, re, subprocess, shutil

from pathlib import Path
from typing import Optional

# Resolve paths
ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT_DIR / "pysidedeploy.spec"
INSTALLER_SCRIPT = ROOT_DIR / "installer" / "installer.iss"

# Locates Inno Setup Compiler.
ISCC_PATH = shutil.which("iscc") or r"F:\Program Files (x86)\Inno Setup 7\ISCC.exe"

def set_console_mode(mode: str) -> None:
    content: str = SPEC_FILE.read_text(encoding="utf-8")
    content = re.sub(r'\s*--windows-console-mode=(disable|force|attach|hide)', '', content)
    
    flag: str = f" --windows-console-mode={'disable' if mode == 'release' else 'force'}"
    
    content = re.sub(
        r'^(extra_args\s*=.*)$',
        rf'\g<1>{flag}',
        content,
        flags=re.MULTILINE
    )
    SPEC_FILE.write_text(content, encoding="utf-8")

def run_deploy(mode: str) -> None:
    print(f"\n{'='*40}")
    print(f"🚀 BUILDING APP: {mode.upper()}")
    print(f"{'='*40}")
    
    set_console_mode(mode)
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        ["pyside6-deploy", "-c", "pysidedeploy.spec"], cwd=ROOT_DIR
    )
    
    if result.returncode != 0:
        print(f"\n[ERROR] pyside6-deploy failed for {mode} mode.")
        sys.exit(1)

def run_inno_setup(suffix: str) -> None:
    print(f"\n{'='*40}")
    print(f"📦 PACKAGING INSTALLER {suffix.upper()}")
    print(f"{'='*40}")
    
    if not Path(ISCC_PATH).exists():
        print(f"[ERROR] Inno Setup Compiler not found at {ISCC_PATH}.")
        print("Please add ISCC.exe to your system PATH or update ISCC_PATH in this script.")
        sys.exit(1)
        
    # Extract version for a clean installer name
    content: str = INSTALLER_SCRIPT.read_text(encoding="utf-8")
    match: Optional[re.Match[str]] = re.search(r'^#define MyAppVersion\s+"([^"]+)"', content, re.MULTILINE)
    version: str = match.group(1) if match else "Unknown"
    
    # The /F flag forces Inno Setup to override the OutputBaseFilename
    output_name: str = f"PyToNingans_v{version}{suffix}"
    
    print(f"[INFO] Running Inno Setup Compiler...")
    result = subprocess.run([ISCC_PATH, f'/F{output_name}', str(INSTALLER_SCRIPT)], cwd=ROOT_DIR)
    
    if result.returncode != 0:
        print(f"\n[ERROR] Inno Setup compilation failed.")
        sys.exit(1)
        
    print(f"[OK] Installer created: {output_name}.exe")

def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1].lower() not in ["release", "debug", "both"]:
        print("Usage:   uv run tools/build.py [release|debug|both]")
        sys.exit(1)

    target: str = sys.argv[1].lower()
    
    if target == "both":
        run_deploy("release")
        run_inno_setup("")
        
        run_deploy("debug")
        run_inno_setup("-with-console")
        
        print("\n[OK] Successfully built and packaged both versions!")
    else:
        run_deploy(target)
        suffix = "" if target == "release" else "-with-console"
        run_inno_setup(suffix)
        print(f"\n[OK] Successfully built and packaged {target} version!")

if __name__ == "__main__":
    main()