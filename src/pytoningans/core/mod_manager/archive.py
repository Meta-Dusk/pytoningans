"""
PyToNingans Mod and Modpack Archive Utilities
===========================================
Safe export and extraction of .zip packages for mods and modpacks,
including directory normalization, zip-slip security guards, and manifest detection.
"""
from __future__ import annotations

import json, os, shutil, zipfile, re, stat, tempfile
from pathlib import Path
from typing import Optional, Any, Callable

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
    zip_path: Path,
    target_mods_dir: Path,
    *,
    overwrite: bool = False,
    dest_folder_name: Optional[str] = None,
) -> tuple[bool, str, Optional[Path]]:
    """
    Safely extracts a mod or modpack .zip archive into target_mods_dir.
    Performs zip-slip path validation, manifest ID detection, and duplicate avoidance.
    Supports atomic extraction and overwriting existing installations in-place.
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
                if str(dest).startswith(str(target_mods_dir)): continue
                err_msg: str = f"Security violation: path traversal detected in '{name}'."
                return False, err_msg, None

            # Check for single top-level directory wrapper.
            #? A true wrapper means ALL non-empty items in the archive reside
            #? inside the exact same root directory.
            root_items: set[str] = {
                name.strip("/").split("/")[0] for name
                in namelist if name.strip("/")
            }
            has_single_wrapper: bool = (
                len(root_items) == 1 and
                any("/" in name.strip("/") for name in namelist)
            )

            resolved_folder_name: Optional[str] = dest_folder_name

            if not resolved_folder_name:
                # Detect manifest file
                manifest_candidates: list[str] = [
                    "mod.json", "modpack.json", "config.json", "pack.json"
                ]
                target_manifest: Optional[str] = None

                # Check root level
                for candidate in manifest_candidates:
                    if not candidate in namelist: continue
                    target_manifest = candidate
                    break

                # Check inside single top-level wrapper
                if not target_manifest and has_single_wrapper:
                    wrapper_prefix: str = next(iter(root_items))
                    for candidate in manifest_candidates:
                        wrapper_candidate: str = f"{wrapper_prefix}/{candidate}"
                        if not wrapper_candidate in namelist: continue
                        target_manifest = wrapper_candidate
                        break

                # Primary: Extract 'id' from manifest file
                if target_manifest is not None:
                    try:
                        manifest_bytes: bytes = zf.read(target_manifest)
                        manifest_data: dict[str, Any] = json.loads(manifest_bytes.decode("utf-8"))
                        resolved_folder_name = manifest_data.get("id")
                    except Exception:
                        pass

                # Secondary: Fall back to top-level wrapper directory name
                if resolved_folder_name is None and has_single_wrapper:
                    resolved_folder_name = next(iter(root_items))

                # Fallback: Derive from zip stem (strip cloud version suffix like '_v1.0.0')
                if resolved_folder_name is None:
                    stem: str = zip_path.stem
                    resolved_folder_name = re.sub(r"_v\d+(\.\d+)*$", "", stem)

            # Clean destination folder name for filesystem safety
            safe_folder_name: str = "".join(
                c if c.isalnum() or c in ("-", "_") else "_" for
                c in (resolved_folder_name or "imported_mod")
            ).strip() or "imported_mod"

            dest_dir: Path = target_mods_dir / safe_folder_name
            if dest_dir.exists() and not overwrite:
                # Avoid accidental overwrite via numeric indexing
                counter: int = 1
                while (target_mods_dir / f"{safe_folder_name}_{counter}").exists():
                    counter += 1
                dest_dir = target_mods_dir / f"{safe_folder_name}_{counter}"

            # Stage extraction in a temporary directory for safety and atomicity
            with tempfile.TemporaryDirectory() as stage_temp_dir:
                stage_dir: Path = Path(stage_temp_dir) / safe_folder_name
                stage_dir.mkdir(parents=True, exist_ok=True)

                for member in zf.infolist():
                    if has_single_wrapper:
                        # Strip wrapper prefix
                        relative_parts: list[str] = member.filename.strip("/").split("/")[1:]
                        if not relative_parts:
                            continue
                        relative_name: str = "/".join(relative_parts)
                        target_path: Path = (stage_dir / relative_name).resolve()
                    else:
                        target_path: Path = (stage_dir / member.filename).resolve()

                    # Verify target_path remains inside stage_dir
                    if not str(target_path).startswith(str(stage_dir)):
                        continue

                    if member.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src_file, open(target_path, "wb") as dst_file:
                            shutil.copyfileobj(src_file, dst_file)

                # Staging succeeded. Deploy to dest_dir.
                if dest_dir.exists() and overwrite:
                    def _handle_remove_readonly(
                        func: Callable[..., Any],
                        path: str,
                        _: BaseException
                    ) -> None:
                        try:
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        except Exception:
                            pass

                    try:
                        shutil.rmtree(dest_dir, onexc=_handle_remove_readonly)
                        shutil.copytree(stage_dir, dest_dir)
                    except Exception:
                        # Fallback in-place copy if directory deletion is restricted
                        shutil.copytree(stage_dir, dest_dir, dirs_exist_ok=True)
                else:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(stage_dir, dest_dir, dirs_exist_ok=True)
            
            err_msg: str = f"Successfully imported into '{dest_dir.name}'."
            return True, err_msg, dest_dir

    except Exception as e:
        err_msg: str = f"Failed to extract archive: {e}"
        return False, err_msg, None
