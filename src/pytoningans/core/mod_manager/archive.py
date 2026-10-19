"""
PyToNingans Mod & Modpack Archive Utilities
===========================================
Safe export and extraction of .zip packages for mods and modpacks,
including directory normalization, zip-slip security guards, and manifest detection.
"""
from __future__ import annotations

import json, os, shutil, zipfile
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
    Performs zip-slip path validation and manifest detection.
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

            # Analyze root structure
            has_root_pack: bool = "pack.json" in namelist
            has_root_config: bool = "config.json" in namelist

            # Check for single top-level directory wrapper
            top_level_dirs: set[str] = set()
            for name in namelist:
                parts: list[str] = name.strip("/").split("/")
                if len(parts) > 1:
                    top_level_dirs.add(parts[0])

            has_single_wrapper: bool = (
                not has_root_pack and not has_root_config and len(top_level_dirs) == 1
            )

            # Determine destination folder name
            dest_folder_name: str = zip_path.stem
            if has_root_pack:
                try:
                    pack_data = json.loads(zf.read("pack.json").decode("utf-8"))
                    dest_folder_name = pack_data.get("id", dest_folder_name)
                except Exception:
                    pass
            elif has_root_config:
                try:
                    cfg_data = json.loads(zf.read("config.json").decode("utf-8"))
                    dest_folder_name = cfg_data.get("name", dest_folder_name)
                except Exception:
                    pass
            elif has_single_wrapper:
                dest_folder_name = next(iter(top_level_dirs))

            # Clean destination folder name for filesystem safety
            safe_folder_name: str = "".join(
                c if c.isalnum() or c in ("-", "_") else "_" for c in dest_folder_name
            ).strip() or "imported_mod"

            dest_dir: Path = target_mods_dir / safe_folder_name
            if dest_dir.exists():
                # Avoid accidental overwrite
                counter = 1
                while (target_mods_dir / f"{safe_folder_name}_{counter}").exists():
                    counter += 1
                dest_dir = target_mods_dir / f"{safe_folder_name}_{counter}"

            dest_dir.mkdir(parents=True, exist_ok=True)

            # Extract files
            for member in zf.infolist():
                target_path: Path
                if has_single_wrapper:
                    # Strip wrapper prefix
                    relative_parts: list[str] = member.filename.strip("/").split("/")[1:]
                    if not relative_parts:
                        continue
                    relative_name: str = "/".join(relative_parts)
                    target_path = (dest_dir / relative_name).resolve()
                else:
                    target_path = (dest_dir / member.filename).resolve()

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
