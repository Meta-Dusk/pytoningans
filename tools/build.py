import sys, re, subprocess, shutil
from pathlib import Path

# Resolve project root (<root>/tools/build.py -> <root>)
ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT_DIR / "pysidedeploy.spec"
DIST_DIR = ROOT_DIR / "PyToNingans.dist"

def set_console_mode(mode: str) -> None:
    if not SPEC_FILE.is_file():
        print(f"[ERROR] Could not find {SPEC_FILE}")
        sys.exit(1)

    content = SPEC_FILE.read_text(encoding="utf-8")
    
    # Strip any existing console mode flags from extra_args to prevent duplicates
    content = re.sub(r'\s*--windows-console-mode=(disable|force|attach|hide)', '', content)
    
    # Add the correct flag for the chosen mode
    flag = " --windows-console-mode=disable" if mode == "release" else " --windows-console-mode=force"
    
    # Inject the flag into the extra_args line
    content = re.sub(
        r'^(extra_args\s*=.*)$',
        rf'\g<1>{flag}',
        content,
        flags=re.MULTILINE
    )
    
    SPEC_FILE.write_text(content, encoding="utf-8")
    print(f"[INFO] Set {mode} mode ({flag.strip()}) in pysidedeploy.spec")

def run_deploy(mode: str) -> None:
    print(f"\n{'='*40}")
    print(f"🚀 STARTING {mode.upper()} BUILD")
    print(f"{'='*40}")
    
    set_console_mode(mode)
    
    print(f"[INFO] Running pyside6-deploy...")
    result = subprocess.run(["pyside6-deploy", "-c", "pysidedeploy.spec"], cwd=ROOT_DIR)
    
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed for {mode} mode.")
        sys.exit(1)
        
    print(f"[OK] {mode.capitalize()} build completed successfully!")

def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1].lower() not in ["release", "debug", "both"]:
        print("Usage:   uv run tools/build.py [release|debug|both]")
        print("Example: uv run tools/build.py release")
        sys.exit(1)

    target = sys.argv[1].lower()
    print(f"[INFO] Project root resolved to: {ROOT_DIR}")

    if target in ["release", "debug"]:
        run_deploy(target)
    
    elif target == "both":
        # Build Release First
        run_deploy("release")
        
        # Move the release build out of the way so the debug build doesn't overwrite it
        release_backup = ROOT_DIR / "PyToNingans_Release.dist"
        if release_backup.exists():
            shutil.rmtree(release_backup)
        if DIST_DIR.exists():
            DIST_DIR.rename(release_backup)
            print(f"[INFO] Moved Release build to: {release_backup.name}")
            
        # Build Debug Second (leaves PyToNingans.dist as the active debug folder)
        run_deploy("debug")
        
        print("\n[OK] Both builds finished successfully!")
        print(f"  -> Release version is in: {release_backup.name}")
        print(f"  -> Debug version is in:   {DIST_DIR.name}")

if __name__ == "__main__":
    main()