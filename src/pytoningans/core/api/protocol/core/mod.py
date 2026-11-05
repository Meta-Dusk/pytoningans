from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...types import AttackType, BehaviorType, DeathAnimation


@runtime_checkable
class IModInfo(Protocol):
    """Metadata and runtime configuration for a loaded mod."""
    current_mod_name: str
    current_mod_folder: str
    entity_type: str
    max_health: int
    attack_damage: int
    attack_range: int
    jump_height: int
    move_speed: float
    regen_rate: float
    can_fly: bool
    can_climb_walls: bool
    can_move_windows: bool
    window_move_mode: str
    ignore_window_physics: bool
    behavior_type: BehaviorType
    attack_type: AttackType
    plain_dialogue: list[str]
    death_dialogue: list[str]
    death_animation: DeathAnimation
    auto_close_on_death: bool
    fade_in_on_spawn: bool
    instance_names: list[str]

