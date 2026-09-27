from dataclasses import dataclass, field
from typing import Dict
from enum import StrEnum, unique

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

@dataclass(frozen=True)
class WindowConfig:
    default_width: int = 150
    default_height: int = 150
    placeholder_text: str = "🐾"
    placeholder_style: str = "font-size: 50px; color: black;"

@dataclass(frozen=True)
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

@dataclass(frozen=True)
class ModConfig:
    animations: Dict[PetState, AnimationMeta] = field(default_factory=lambda: {
        PetState.IDLE: AnimationMeta(row=0, start_frame=0, end_frame=3),
        PetState.DRAG: AnimationMeta(row=1, start_frame=0, end_frame=3),
        PetState.INTERACT: AnimationMeta(row=2, start_frame=0, end_frame=3),
    })

@dataclass(frozen=True)
class AppConfig:
    app_name: str = "PyToNingans"

WINDOW_CFG = WindowConfig()
MOD_CFG = ModConfig()
APP_CFG = AppConfig()