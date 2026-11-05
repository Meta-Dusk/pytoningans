"""
PyToNingans Mod and Modpack Archive Utilities
===========================================
Safe export and extraction of .zip packages for mods and modpacks,
including directory normalization, zip-slip security guards, and manifest detection.
"""
from __future__ import annotations

import json, os, shutil, zipfile, re
from pathlib import Path
from typing import Optional

IGNORED_ARCHIVE_PATTERNS: set[str] = {
    "__pycache__",
    ".git",
    ".vscode",
    ".idea",
    ".DS_Store",
    "Thumbs.db",
}


def is_ignored_file(path: Path) -> bool:
    """Returns True if the file or any parent directory matches ignored archive patterns."""
    for part in path.parts:
        if part in IGNORED_ARCHIVE_PATTERNS or part.endswith((".pyc", ".pyo")):
            return True
    return False


def export_mod_or_pack_to_zip(
    source_dir: Path, output_zip_path: Path
) -> tuple[bool, str, Optional[Path]]:
    """
    Compresses a standalone mod folder or modpack directory into a clean .zip package.
    Excludes cached files, bytecode, and IDE folders.
    Returns (success, message, output_zip_path).
    """
    try:
        source_dir = source_dir.resolve()
        output_zip_path = output_zip_path.resolve()
        if not source_dir.exists():
            return False, f"Source directory does not exist: {source_dir}", None

        output_zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                root_path = Path(root)
                # Prune ignored directories in-place
                dirs[:] = [d for d in dirs if d not in IGNORED_ARCHIVE_PATTERNS]

                for file in files:
                    file_path: Path = root_path / file
                    rel_path: Path = file_path.relative_to(source_dir)
                    if not is_ignored_file(rel_path):
                        zf.write(file_path, arcname=str(rel_path).replace("\\", "/"))

        return True, f"Successfully exported to {output_zip_path.name}", output_zip_path
    except Exception as e:
        return False, f"Failed to export archive: {str(e)}", None


def extract_mod_or_pack_from_zip(
    zip_path: Path, target_mods_dir: Path
) -> tuple[bool, str, Optional[Path]]:
    """
    Safely extracts a mod or modpack .zip archive into target_mods_dir.
    Performs zip-slip path validation, manifest ID detection, and duplicate avoidance.
    Returns (success, message, extracted_folder_path).
    """
    zip_path = zip_path.resolve()
    target_mods_dir = target_mods_dir.resolve()

    if not zip_path.exists():
        return False, f"File not found: {zip_path}", None

    if not zipfile.is_zipfile(zip_path):
        return False, "Selected file is not a valid ZIP archive.", None

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist: list[str] = zf.namelist()
            if not namelist:
                return False, "Archive is empty.", None

            # Zip-slip security validation
            for name in namelist:
                dest: Path = (target_mods_dir / name).resolve()
                if not str(dest).startswith(str(target_mods_dir)):
                    return False, f"Security violation: path traversal detected in '{name}'.", None

            # Check for single top-level directory wrapper
            top_level_dirs: set[str] = set()
            for name in namelist:
                parts: list[str] = name.strip("/").split("/")
                if len(parts) > 1:
                    top_level_dirs.add(parts[0])

            has_single_wrapper: bool = len(top_level_dirs) == 1

            # Detect manifest file (mod.json, modpack.json, config.json, pack.json)
            manifest_candidates: list[str] = ["mod.json", "modpack.json", "config.json", "pack.json"]
            target_manifest: Optional[str] = None

            # Check root level
            for candidate in manifest_candidates:
                if candidate in namelist:
                    target_manifest = candidate
                    break

            # Check inside single top-level wrapper
            if not target_manifest and has_single_wrapper:
                wrapper_prefix: str = next(iter(top_level_dirs))
                for candidate in manifest_candidates:
                    wrapper_candidate: str = f"{wrapper_prefix}/{candidate}"
                    if wrapper_candidate in namelist:
                        target_manifest = wrapper_candidate
                        break

            dest_folder_name: Optional[str] = None

            # Primary: Extract 'id' from manifest file
            if target_manifest:
                try:
                    manifest_bytes = zf.read(target_manifest)
                    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
                    dest_folder_name = manifest_data.get("id")
                except Exception:
                    pass

            # Secondary: Fall back to top-level wrapper directory name
            if not dest_folder_name and has_single_wrapper:
                dest_folder_name = next(iter(top_level_dirs))

            # Fallback: Derive from zip stem (strip cloud version suffix like '_v1.0.0')
            if not dest_folder_name:
                stem = zip_path.stem
                dest_folder_name = re.sub(r"_v\d+(\.\d+)*$", "", stem)

            # Clean destination folder name for filesystem safety
            safe_folder_name: str = "".join(
                c if c.isalnum() or c in ("-", "_") else "_" for c in dest_folder_name
            ).strip() or "imported_mod"

            dest_dir: Path = target_mods_dir / safe_folder_name
            if dest_dir.exists():
                # Avoid accidental overwrite via numeric indexing
                counter: int = 1
                while (target_mods_dir / f"{safe_folder_name}_{counter}").exists():
                    counter += 1
                dest_dir = target_mods_dir / f"{safe_folder_name}_{counter}"

            dest_dir.mkdir(parents=True, exist_ok=True)

            # Extract files
            for member in zf.infolist():
                if has_single_wrapper:
                    # Strip wrapper prefix
                    relative_parts: list[str] = member.filename.strip("/").split("/")[1:]
                    if not relative_parts:
                        continue
                    relative_name: str = "/".join(relative_parts)
                    target_path: Path = (dest_dir / relative_name).resolve()
                else:
                    target_path: Path = (dest_dir / member.filename).resolve()

                # Verify target_path remains inside dest_dir
                if not str(target_path).startswith(str(dest_dir)):
                    continue

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src_file, open(target_path, "wb") as dst_file:
                        shutil.copyfileobj(src_file, dst_file)

            return True, f"Successfully imported into '{dest_dir.name}'.", dest_dir

    except Exception as e:
        return False, f"Failed to extract archive: {e}", None
