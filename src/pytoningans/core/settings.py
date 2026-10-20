from __future__ import annotations

import json
from enum import StrEnum, unique
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import QObject, Signal

from pytoningans.utils.paths import get_settings_path


@unique
class HealthBarMode(StrEnum):
    ON_DAMAGE = "on_damage"
    ALWAYS = "always"
    HIDDEN = "hidden"


@dataclass
class AppSettings:
    """Global user preferences and application configuration settings."""
    health_bar_mode: str = HealthBarMode.ON_DAMAGE
    show_damage_numbers: bool = True
    show_health_numbers: bool = True
    enable_health_shake: bool = True
    auto_hide_delay_ms: int = 3000
    enable_window_physics: bool = True
    avoid_window_spawn: bool = True
    spawn_area_mode: str = "screen"
    enable_debug_mode: bool = False
    creator_name: str = "Modder"
    creator_bio: str = ""


# Backward compatibility alias
CombatVisualSettings = AppSettings


class SettingsManager(QObject):
    settings_changed = Signal()
    _instance: Optional[SettingsManager] = None

    def __init__(self) -> None:
        super().__init__()
        self.settings: AppSettings = AppSettings()
        self.load()

    @classmethod
    def get(cls) -> SettingsManager:
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def load(self) -> None:
        path: Path = get_settings_path()
        if path.exists():
            try:
                data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
                self.settings = AppSettings(
                    health_bar_mode=data.get("health_bar_mode", HealthBarMode.ON_DAMAGE),
                    show_damage_numbers=data.get("show_damage_numbers", True),
                    show_health_numbers=data.get("show_health_numbers", True),
                    enable_health_shake=data.get("enable_health_shake", True),
                    auto_hide_delay_ms=data.get("auto_hide_delay_ms", 3000),
                    enable_window_physics=data.get("enable_window_physics", True),
                    avoid_window_spawn=data.get("avoid_window_spawn", True),
                    spawn_area_mode=data.get("spawn_area_mode", "screen"),
                    enable_debug_mode=data.get("enable_debug_mode", False),
                    creator_name=data.get("creator_name", "Modder"),
                    creator_bio=data.get("creator_bio", ""),
                )
            except Exception as e:
                print(f"Warning: Failed to load settings from {path}: {e}")
                self.settings = AppSettings()
        else:
            self.settings = AppSettings()

    def save(self) -> None:
        path: Path = get_settings_path()
        try:
            path.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to save settings to {path}: {e}")

    def update_settings(
        self,
        health_bar_mode: Optional[str] = None,
        show_damage_numbers: Optional[bool] = None,
        show_health_numbers: Optional[bool] = None,
        enable_health_shake: Optional[bool] = None,
        auto_hide_delay_ms: Optional[int] = None,
        enable_window_physics: Optional[bool] = None,
        avoid_window_spawn: Optional[bool] = None,
        spawn_area_mode: Optional[str] = None,
        enable_debug_mode: Optional[bool] = None,
        creator_name: Optional[str] = None,
        creator_bio: Optional[str] = None,
    ) -> None:
        changed = False
        if health_bar_mode is not None and self.settings.health_bar_mode != health_bar_mode:
            self.settings.health_bar_mode = health_bar_mode
            changed = True
        if show_damage_numbers is not None and self.settings.show_damage_numbers != show_damage_numbers:
            self.settings.show_damage_numbers = show_damage_numbers
            changed = True
        if show_health_numbers is not None and self.settings.show_health_numbers != show_health_numbers:
            self.settings.show_health_numbers = show_health_numbers
            changed = True
        if enable_health_shake is not None and self.settings.enable_health_shake != enable_health_shake:
            self.settings.enable_health_shake = enable_health_shake
            changed = True
        if auto_hide_delay_ms is not None and self.settings.auto_hide_delay_ms != auto_hide_delay_ms:
            self.settings.auto_hide_delay_ms = auto_hide_delay_ms
            changed = True
        if enable_window_physics is not None and self.settings.enable_window_physics != enable_window_physics:
            self.settings.enable_window_physics = enable_window_physics
            changed = True
        if avoid_window_spawn is not None and self.settings.avoid_window_spawn != avoid_window_spawn:
            self.settings.avoid_window_spawn = avoid_window_spawn
            changed = True
        if spawn_area_mode is not None and self.settings.spawn_area_mode != spawn_area_mode:
            self.settings.spawn_area_mode = spawn_area_mode
            changed = True
        if enable_debug_mode is not None and self.settings.enable_debug_mode != enable_debug_mode:
            self.settings.enable_debug_mode = enable_debug_mode
            changed = True
        if creator_name is not None and self.settings.creator_name != creator_name.strip():
            self.settings.creator_name = creator_name.strip()
            changed = True
        if creator_bio is not None and self.settings.creator_bio != creator_bio.strip():
            self.settings.creator_bio = creator_bio.strip()
            changed = True

        if changed:
            self.save()
            self.settings_changed.emit()

    def reset_to_defaults(self) -> None:
        self.settings = AppSettings()
        self.save()
        self.settings_changed.emit()

