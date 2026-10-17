from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import QPointF, QRectF, QRect

from pytoningans.core.api import BaseBehavior, BaseEntityBehavior, IEntity
from pytoningans.core.constants import AttackType, BehaviorType, EntityState

if TYPE_CHECKING:
    from pytoningans.core.entity.living_entity import Entity
    from .system import AISystem


def get_distance(p1: QPointF, p2: QPointF) -> float:
    """Calculates Euclidean distance between two 2D points."""
    return math.hypot(p1.x() - p2.x(), p1.y() - p2.y())


def check_combat(ai: AISystem) -> None:
    """Checks if any hostile target is in attack range and initiates attack."""
    if (
        ai.entity is None or
        ai.entity.mod_manager is None or
        ai.entity.entity_manager is None
    ):
        return
    
    if ai.entity.mod_manager.behavior_type is not BehaviorType.HOSTILE:
        return
    
    if ai.attack_cooldown > 0 or not ai.entity.is_interactable:
        return

    my_center: QPointF = ai.entity.pos() + ai.entity.current_hitbox.center()

    for other_entity in ai.entity.entity_manager.active_entities:
        if (
            other_entity is ai.entity or
            not other_entity.is_interactable or
            other_entity is None or
            other_entity.mod_manager is None or
            other_entity.entity_manager is None
        ):
            continue
        
        if other_entity.mod_manager.current_mod_name == ai.entity.mod_manager.current_mod_name:
            continue
        
        other_center: QPointF = other_entity.pos() + other_entity.current_hitbox.center()
        dist: float = get_distance(my_center, other_center)

        if dist > ai.entity.mod_manager.attack_range:
            continue
        
        override_default: bool = on_combat_check(ai, other_entity)

        if not override_default:
            default_combat_logic(ai, my_center, other_center)
                
        break


def default_combat_logic(ai: AISystem, my_center: QPointF, other_center: QPointF) -> None:
    """Standard attack initiation: faces target, sets rotation (if flying), and enters ATTACK state."""
    if (
        ai.entity is None or
        ai.entity.mod_manager is None or
        ai.entity.anim_sys is None
    ):
        return
    
    dx: float = other_center.x() - my_center.x()
    dy: float = other_center.y() - my_center.y()
            
    ai.entity.facing_left = (dx < 0)
            
    if ai.entity.mod_manager.can_fly:
        ai.entity.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            
    ai.entity.target_pos = None
    ai.attack_time_left = 800 
    ai.attack_cooldown = 2000 
    ai.entity.anim_sys.set_state(EntityState.ATTACK)


def on_combat_check(ai: AISystem, other_entity: Entity) -> bool:
    """Invokes custom modder on_attack hook if defined."""
    if ai.entity is None:
        return False
    behavior: Optional[BaseBehavior] = ai.entity.behavior
    if not isinstance(behavior, BaseEntityBehavior):
        return False
    try:
        entity_api: IEntity = cast(IEntity, ai.entity)
        other_entity_api: IEntity = cast(IEntity, other_entity)
        return behavior.on_attack(entity_api, other_entity_api)
    except Exception as e:
        print(f"Custom AI Error (Attack): {e}")
    return False


def process_combat(ai: AISystem) -> None:
    """Processes attack frame impact, detecting targets in attack hitbox and dealing damage."""
    if (
        ai.entity is None or
        ai.entity.entity_manager is None or
        ai.entity.mod_manager is None or
        ai.entity.is_dead
    ):
        return

    atk_hitbox: QRect = ai.entity.current_attack_hitbox
    if atk_hitbox.isEmpty():
        base_hitbox = ai.entity.current_hitbox
        if not base_hitbox.isEmpty():
            range_px: int = ai.entity.mod_manager.attack_range
            if ai.entity.facing_left:
                atk_hitbox = QRect(base_hitbox.x() - range_px, base_hitbox.y(), range_px, base_hitbox.height())
            else:
                atk_hitbox = QRect(base_hitbox.x() + base_hitbox.width(), base_hitbox.y(), range_px, base_hitbox.height())
        else:
            return

    # Translate using QRectF for floating-point precision
    global_attack_rect: QRectF = QRectF(atk_hitbox).translated(ai.entity.pos())

    # Check desktop window hits if entity is configured to move windows
    if (
        ai.entity.world is not None and
        ai.entity.mod_manager.can_move_windows and
        ai.entity.mod_manager.window_move_mode in ("attack", "both")
    ):
        knockback: int = max(20, min(60, ai.entity.mod_manager.attack_damage * 2))
        knock_dir: int = -knockback if ai.entity.facing_left else knockback

        for win in list(ai.entity.world.active_window_rects):
            if not global_attack_rect.intersects(QRectF(win)): continue
            if not ai.entity.world.move_window(win, knock_dir, 0): continue
            
            damage: int = ai.entity.mod_manager.attack_damage or 10
            hit_x: float = global_attack_rect.center().x()
            hit_y: float = max(float(win.top()), min(global_attack_rect.center().y(), float(win.bottom())))
            ai.entity.world.spawn_damage_number(damage, QPointF(hit_x, hit_y))

    targets: list[tuple[float, Entity]] = []
    
    for other_entity in ai.entity.entity_manager.active_entities:
        if other_entity is ai.entity or other_entity.is_dead:
            continue
            
        other_global_hitbox: QRectF = QRectF(other_entity.current_hitbox).translated(other_entity.pos())
        
        if global_attack_rect.intersects(other_global_hitbox):
            my_center: QPointF = global_attack_rect.center()
            other_center: QPointF = other_global_hitbox.center()
            dist: float = math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())
            targets.append((dist, other_entity))

    if not targets:
        return

    targets.sort(key=lambda t: t[0])
    valid_targets: list[Entity] = []
    attack_type: AttackType = ai.entity.mod_manager.attack_type
    
    match attack_type:
        case AttackType.SINGLE:
            valid_targets.append(targets[0][1])
        case AttackType.AOE:
            valid_targets = [t[1] for t in targets]
        case AttackType.MULTI:
            max_t: int = ai.entity.mod_manager.max_targets
            valid_targets = [t[1] for t in targets[:max_t]]

    damage: int = ai.entity.mod_manager.attack_damage
    for target in valid_targets:
        target.take_damage(damage)

