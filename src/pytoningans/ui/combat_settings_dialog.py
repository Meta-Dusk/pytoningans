"""
PyToNingans - Legacy Combat Settings Dialog Alias
=================================================
Maintains backward compatibility by aliasing SettingsDialog to CombatSettingsDialog.
"""
from __future__ import annotations

from .settings_dialog import SettingsDialog as CombatSettingsDialog

__all__ = ["CombatSettingsDialog"]

