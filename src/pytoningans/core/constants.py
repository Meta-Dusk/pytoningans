from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Any

@unique
class VerificationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@unique
class EntityType(StrEnum):
    ENTITY = "entity"
    STRUCTURE = "structure"
    ITEM = "item"

@unique
class DeathAnimation(StrEnum):
    SPRITE = "sprite"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    ROTATE_LEFT_OR_RIGHT = "rotate_left_or_right"

@unique
class AttackType(StrEnum):
    SINGLE = "single"
    AOE = "aoe"
    MULTI = "multi"

@unique
class EntityState(StrEnum):
    IDLE = "idle"
    DRAG = "drag"
    CLICKED = "clicked"
    INTERACT = "interact"
    MOVING = "moving"
    JUMPING = "jumping"
    CLIMBING = "climbing"
    DYING = "dying"
    REVIVING = "reviving"
    ATTACK = "attack"

@unique
class StructureState(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    OPEN = "open"

@unique
class ItemState(StrEnum):
    IDLE = "idle"
    HELD = "held"
    DROPPED = "dropped"
    USED = "used"

@unique
class BehaviorType(StrEnum):
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"

@dataclass(slots=True, kw_only=True)
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

    # Item Hold Anchor (2nd anchor for held items)
    has_hold_point: bool = False
    hold_x: int = 0
    hold_y: int = 0
    
    frame_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Dictionary mapping string frame indices (for JSON) to override data dicts"""

@dataclass(slots=True, kw_only=True, frozen=True)
class AppConfig:
    name: str = "PyToNingans"

@dataclass(slots=True, kw_only=True)
class SystemLocks:
    ai: bool = True
    physics: bool = True
    animation: bool = True

APP_CONFIG = AppConfig()