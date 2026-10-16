from __future__ import annotations

import json
from enum import StrEnum, unique
from dataclasses import dataclass, asdict
from typing import Optional

from PySide6.QtCore import QObject, Signal

from pytoningans.utils.paths import get_settings_path


@unique
class HealthBarMode(StrEnum):
    ON_DAMAGE = "on_damage"
    ALWAYS = "always"
    HIDDEN = "hidden"


@dataclass
class CombatVisualSettings:
    health_bar_mode: str = HealthBarMode.ON_DAMAGE
    show_damage_numbers: bool = True
    show_health_numbers: bool = True
    enable_health_shake: bool = True
    auto_hide_delay_ms: int = 3000
    enable_window_physics: bool = True


class SettingsManager(QObject):
    settings_changed = Signal()
    _instance: Optional[SettingsManager] = None

    def __init__(self) -> None:
        super().__init__()
        self.settings: CombatVisualSettings = CombatVisualSettings()
        self.load()

    @classmethod
    def get(cls) -> SettingsManager:
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def load(self) -> None:
        path = get_settings_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.settings = CombatVisualSettings(
                    health_bar_mode=data.get("health_bar_mode", HealthBarMode.ON_DAMAGE),
                    show_damage_numbers=data.get("show_damage_numbers", True),
                    show_health_numbers=data.get("show_health_numbers", True),
                    enable_health_shake=data.get("enable_health_shake", True),
                    auto_hide_delay_ms=data.get("auto_hide_delay_ms", 3000),
                    enable_window_physics=data.get("enable_window_physics", True),
                )
            except Exception as e:
                print(f"Warning: Failed to load settings from {path}: {e}")
                self.settings = CombatVisualSettings()
        else:
            self.settings = CombatVisualSettings()

    def save(self) -> None:
        path = get_settings_path()
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

        if changed:
            self.save()
            self.settings_changed.emit()

    def reset_to_defaults(self) -> None:
        self.settings = CombatVisualSettings()
        self.save()
        self.settings_changed.emit()

