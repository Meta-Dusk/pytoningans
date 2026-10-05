from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Any

@unique
class AttackType(StrEnum):
    SINGLE = "single"
    AOE = "aoe"
    MULTI = "multi"

@unique
class PetState(StrEnum):
    DRAG = "drag"
    IDLE = "idle"
    CLICKED = "clicked"
    INTERACT = "interact"
    MOVING = "moving"
    JUMPING = "jumping"
    DYING = "dying"
    CLIMBING = "climbing"
    REVIVING = "reviving"
    ATTACK = "attack"

@unique
class BehaviorType(StrEnum):
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"

@dataclass(frozen=True)
class WindowConfig:
    default_width: int = 150
    default_height: int = 150
    placeholder_text: str = "🐾"
    placeholder_style: str = "font-size: 50px; color: black;"

@dataclass()
class AnimationMeta:
    row: int
    start_frame: int = 0
    end_frame: int = 0
    loop: bool = True
    reverse: bool = False
    
    override_width: int = 0
    """0 means \"use global grid width\""""
    
    override_height: int = 0
    """0 means \"use global grid width\""""
    
    offset_x: int = 0
    offset_y: int = 0
    fps: int = 10
    
    # Engine runtime cache
    base_h: int = 0
    computed_w: int = 0
    computed_h: int = 0
    
    # Physics and Alignment
    anchor_x: int = 0
    anchor_y: int = 0
    hitbox_x: int = 0
    hitbox_y: int = 0
    hitbox_w: int = 0
    hitbox_h: int = 0
    
    frame_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Dictionary mapping string frame indices (for JSON) to override data dicts"""

@dataclass(frozen=True)
class ModConfig:
    animations: dict[PetState, AnimationMeta] = field(default_factory=lambda: {
        PetState.IDLE: AnimationMeta(row=0, start_frame=0, end_frame=3),
        PetState.DRAG: AnimationMeta(row=1, start_frame=0, end_frame=3),
        PetState.INTERACT: AnimationMeta(row=2, start_frame=0, end_frame=3),
    })

@dataclass(frozen=True)
class AppConfig:
    app_name: str = "PyToNingans"

@dataclass
class SystemLocks:
    ai: bool = True
    physics: bool = True
    animation: bool = True

WINDOW_CFG = WindowConfig()
MOD_CFG = ModConfig()
APP_CFG = AppConfig()