from __future__ import annotations

import math

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRect, QPointF

from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from pytoningans.core.entity.base import BaseEntity

class PhysicsSystem:
    def __init__(self, entity: Optional[BaseEntity] = None) -> None:
        self.entity = entity
        self.gravity: float = 0.8
        self.move_speed: float = 2.0

    def update(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        """Processes physics calculations based on elapsed time."""
        if self.entity is None or self.entity.world is None: return
        if not self.entity.locks.physics:
            self.entity.velocity_y = 0
            return

        ground_y: float = self.entity.world.scene.sceneRect().bottom()
        
        time_scale: float = dt / 16.0
        current_gravity: float = self.gravity * time_scale
        current_move_speed: float = self.move_speed * time_scale

        self._tick_gravity_and_collisions(ground_y, current_gravity)

        # Structures don't die, so they default to False
        is_dead: bool = getattr(self.entity, 'is_dead', False)
        if is_dead: return

        self._tick_soft_collision(current_move_speed, centers)
        self._tick_movement(current_move_speed)

    def _tick_soft_collision(
        self, current_move_speed: float, centers: Optional[dict['BaseEntity', QPointF]]= None
    ) -> None:
        """Gently repels overlapping entities to prevent dense clustering."""
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.world is None
        ):
            return
        if self.entity.state in (EntityState.DRAG, EntityState.MOVING):
            return

        hitbox: QRect = self.entity.current_hitbox
        
        fallback_center = QPointF(
            self.entity.x() + hitbox.center().x(),
            self.entity.y() + hitbox.center().y()
        )
        my_center: Optional[QPointF] = centers.get(self.entity) if centers else fallback_center
        
        repel_x, repel_y = 0.0, 0.0
        min_dist: float = hitbox.width() * 0.6
        
        # Combine both lists so pets and structures can repel each other
        all_entities: list[BaseEntity] = self.entity.world.active_entities + self.entity.world.active_structures
        
        for other in all_entities:
            is_other_dead: bool = getattr(other, 'is_dead', False)
            if other is self.entity or is_other_dead: continue
            
            other_fallback = QPointF(
                other.x() + other.current_hitbox.center().x(),
                other.y() + other.current_hitbox.center().y()
            )
            other_center: Optional[QPointF] = centers.get(other) if centers else other_fallback
            if other_center is None or my_center is None: continue
            
            dx: float = my_center.x() - other_center.x()
            dy: float = my_center.y() - other_center.y()
            dist: float = math.hypot(dx, dy)
            
            if 0 < dist < min_dist:
                force: float = (min_dist - dist) / min_dist
                repel_x += (dx / dist) * force * (current_move_speed * 1.5)
                
                if self.entity.mod_manager.can_fly:
                    repel_y += (dy / dist) * force * (current_move_speed * 1.5)
                    
        if repel_x != 0 or repel_y != 0:
            new_x: float = self.entity.x() + repel_x
            new_y: float = self.entity.y() + repel_y if self.entity.mod_manager.can_fly else self.entity.y()
            self.entity.setPos(new_x, new_y)

    def _tick_movement(self, current_move_speed: float) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.anim_sys is None
        ):
            return
            
        target_pos: Optional[QPointF] = getattr(self.entity, '_target_pos', None)
        if self.entity.state is not EntityState.MOVING or target_pos is None: return
        
        curr_x, curr_y = self.entity.x(), self.entity.y()
        target_x: float = float(target_pos.x())
        target_y: float = float(target_pos.y()) if self.entity.mod_manager.can_fly else curr_y

        dx, dy = target_x - curr_x, target_y - curr_y
        dist: float = math.hypot(dx, dy)

        if dist < max(current_move_speed, 5.0):
            self.entity.setPos(target_x, target_y)
            
            if hasattr(self.entity, 'target_pos'):
                setattr(self.entity, 'target_pos', None)
            else:
                setattr(self.entity, '_target_pos', None)
                
            self.entity.sprite_rotation = 0.0
            self.entity.anim_sys.set_state(EntityState.IDLE)
        else:
            step_x: float = curr_x + (dx / dist) * current_move_speed
            step_y: float = curr_y + (dy / dist) * current_move_speed if self.entity.mod_manager.can_fly else curr_y
            
            if abs(dx) > 1: self.entity.facing_left = (dx < 0)
            
            if self.entity.mod_manager.can_fly and dist > 5.0:
                self.entity.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            
            self.entity.setPos(step_x, step_y)

    def _tick_gravity_and_collisions(self, ground_y: float, current_gravity: float) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.anim_sys is None
        ):
            return
            
        is_dead: bool = getattr(self.entity, 'is_dead', False)
        if self.entity.mod_manager.can_fly and not is_dead: return
        
        hitbox: QRect = self.entity.current_hitbox
        hitbox_bottom_offset: int = hitbox.y() + hitbox.height()
        pet_bottom: float = self.entity.y() + hitbox_bottom_offset
        
        if pet_bottom < ground_y or self.entity.velocity_y < 0:
            self.entity.velocity_y += current_gravity
            new_y: float = self.entity.y() + self.entity.velocity_y
            
            if new_y + hitbox_bottom_offset > ground_y:
                new_y = ground_y - hitbox_bottom_offset
                self.entity.velocity_y = 0
                if self.entity.state is EntityState.JUMPING and not is_dead:
                    self.entity.anim_sys.set_state(EntityState.IDLE)
                    
            self.entity.setPos(self.entity.x(), new_y)
        else:
            self.entity.velocity_y = 0
            if self.entity.state is EntityState.JUMPING and not is_dead:
                self.entity.anim_sys.set_state(EntityState.IDLE)