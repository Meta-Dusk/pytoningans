"""
PyToNingans - Export Cloud Configuration Tool
=============================================
Reads credentials from local .env or environment variables and generates
cloud_config.json for bundling into the release installer.
Does NOT commit secrets to git (cloud_config.json is in .gitignore).
"""
import json
import os
import sys
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent.parent


def parse_env_file(path: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    if not path.is_file():
        return results
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        results[k.strip()] = v.strip().strip("'\"")
    return results


def main() -> None:
    env_file = ROOT_DIR / ".env"
    env_vars = parse_env_file(env_file)

    url = os.environ.get("SUPABASE_URL") or env_vars.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY") or env_vars.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        print("[WARN]  SUPABASE_URL or SUPABASE_ANON_KEY not found in .env or environment variables.")
        print("[INFO]  To configure:")
        print("        1. Copy .env.example to .env")
        print("        2. Fill in your project URL and public anon key")
        print("        3. Re-run this script before compiling the installer.")
        sys.exit(1)

    target = ROOT_DIR / "cloud_config.json"
    payload = {
        "supabase_url": url,
        "supabase_anon_key": key,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[OK]    Successfully generated {target.name} from .env!")
    print(f"[INFO]  Project URL: {url}")
    print("[INFO]  The installer will now bundle this configuration automatically.")


if __name__ == "__main__":
    main()

