from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRect, QPointF, QRectF

from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.entity.living_entity import Entity

class PhysicsSystem:
    def __init__(self, entity: Optional[BaseEntity] = None) -> None:
        self.entity = entity
        self.gravity: float = 0.8
        self.move_speed: float = 2.0
        self.current_platform_rect: Optional[QRect] = None

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
        self, current_move_speed: float, centers: Optional[dict[BaseEntity, QPointF]]= None
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
        
        # Combine both lists so entities and structures can repel each other
        all_entities: list[BaseStructure | Entity] = (
            self.entity.world.active_entities + self.entity.world.active_structures
        )
        
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
        if self.entity.state != EntityState.MOVING or target_pos is None: return
        
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

            # Check side wall collisions against desktop windows for ground entities
            collided_side: bool = False
            if not self.entity.mod_manager.can_fly and self.entity.world is not None:
                window_rects: list[QRect] = getattr(self.entity.world, "active_window_rects", [])
                hitbox: QRect = self.entity.current_hitbox
                if hitbox.width() <= 0 or hitbox.height() <= 0:
                    b_rect: QRectF = self.entity.boundingRect()
                    bw: int = int(b_rect.width()) if b_rect.width() > 0 else 50
                    bh: int = int(b_rect.height()) if b_rect.height() > 0 else 50
                    hitbox = QRect(0, 0, bw, bh)

                curr_left: float = curr_x + hitbox.x()
                curr_right: float = curr_left + hitbox.width()
                feet_y: float = self.entity.y() + hitbox.y() + hitbox.height()
                top_y: float = self.entity.y() + hitbox.y()

                for win in window_rects:
                    # Only collide if entity is vertically overlapping the window body
                    if feet_y > win.top() + 8 and top_y < win.bottom() - 4:
                        step_left: float = step_x + hitbox.x()
                        step_right: float = step_left + hitbox.width()

                        # Moving RIGHT: only trigger if entity was to the left of the window (entering from outside)
                        if dx > 0 and curr_right <= win.left() + 6:
                            if step_right >= win.left():
                                step_x = float(win.left() - hitbox.x() - hitbox.width() - 1)
                                self.entity.facing_left = True
                                self.entity._target_pos = None
                                self.entity.anim_sys.set_state(EntityState.IDLE)
                                collided_side = True
                                break
                        # Moving LEFT: only trigger if entity was to the right of the window (entering from outside)
                        elif dx < 0 and curr_left >= win.right() - 6:
                            if step_left <= win.right():
                                step_x = float(win.right() - hitbox.x() + 1)
                                self.entity.facing_left = False
                                self.entity._target_pos = None
                                self.entity.anim_sys.set_state(EntityState.IDLE)
                                collided_side = True
                                break
            
            if not collided_side and abs(dx) > 1:
                self.entity.facing_left = (dx < 0)
            
            if self.entity.mod_manager.can_fly and dist > 5.0:
                self.entity.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            
            # Keep ground entities within world monitor horizontal boundaries
            if self.entity.world:
                hitbox: QRect = self.entity.current_hitbox
                world_bounds: QRectF = self.entity.world.scene.sceneRect()
                min_step_x: float = float(world_bounds.left() - hitbox.x())
                max_step_x: float = float(world_bounds.right() - hitbox.x() - hitbox.width())
                if step_x <= min_step_x:
                    step_x = min_step_x
                    self.entity.facing_left = False
                    self.entity._target_pos = None
                    self.entity.anim_sys.set_state(EntityState.IDLE)
                elif step_x >= max_step_x:
                    step_x = max_step_x
                    self.entity.facing_left = True
                    self.entity._target_pos = None
                    self.entity.anim_sys.set_state(EntityState.IDLE)

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
        if hitbox.width() <= 0 or hitbox.height() <= 0:
            b_rect: QRectF = self.entity.boundingRect()
            bw: int = int(b_rect.width()) if b_rect.width() > 0 else 50
            bh: int = int(b_rect.height()) if b_rect.height() > 0 else 50
            hitbox = QRect(0, 0, bw, bh)

        hitbox_bottom_offset: int = hitbox.y() + hitbox.height()
        entity_bottom: float = self.entity.y() + hitbox_bottom_offset
        entity_top: float = self.entity.y() + hitbox.y()

        entity_x: float = self.entity.x()
        entity_left: float = entity_x + hitbox.x()
        entity_right: float = entity_left + hitbox.width()

        window_rects: list[QRect] = getattr(self.entity.world, "active_window_rects", []) if self.entity.world else []

        # Depenetration & auto-scoop for entities caught inside a window body (e.g. window moved over them)
        for win in window_rects:
            if entity_right > win.left() + 4 and entity_left < win.right() - 4:
                if entity_bottom > win.top() + 6 and entity_top < win.bottom() - 4:
                    # If entity is in upper portion (within 80px of top), scoop onto the title bar ledge!
                    if entity_top < win.top() + 80:
                        scoop_y: float = float(win.top() - hitbox_bottom_offset)
                        scoop_x: float = self.entity.x()
                        if self.entity.world:
                            wb: QRectF = self.entity.world.scene.sceneRect()
                            scoop_x = (
                                max(
                                    float(wb.left() - hitbox.x()),
                                    min(scoop_x, float(wb.right() - hitbox.x() - hitbox.width()))
                                )
                            )
                        self.entity.setPos(scoop_x, scoop_y)
                        self.entity.velocity_y = 0.0
                        self.current_platform_rect = win
                        if self.entity.state == EntityState.JUMPING and not is_dead:
                            self.entity.anim_sys.set_state(EntityState.IDLE)
                        return
                    else:
                        # Deep inside window: check lateral push to nearest exterior boundary
                        dist_left: float = abs(entity_right - win.left())
                        dist_right: float = abs(win.right() - entity_left)
                        if dist_left < dist_right:
                            eject_x: float = float(win.left() - hitbox.x() - hitbox.width() - 2)
                            self.entity.facing_left = True
                        else:
                            eject_x: float = float(win.right() - hitbox.x() + 2)
                            self.entity.facing_left = False

                        # Check if being pushed to the side would place entity outside the world bounds
                        if self.entity.world:
                            world_bounds: QRectF = self.entity.world.scene.sceneRect()
                            min_x: float = float(world_bounds.left() - hitbox.x())
                            max_x: float = float(world_bounds.right() - hitbox.x() - hitbox.width())

                            # If pushed out of bounds of the monitor by the window:
                            if eject_x < min_x or eject_x > max_x:
                                eject_x = max(min_x, min(eject_x, max_x))
                                self.entity.setPos(eject_x, self.entity.y())
                                self.entity._target_pos = None
                                from .living_entity import Entity
                                if not is_dead and isinstance(self.entity, Entity):
                                    death_lines: list[str] = self.entity.mod_manager.death_dialogue
                                    if not death_lines:
                                        self.entity.say("Squished!", duration_ms=3000, is_death=True)
                                    self.entity.die()
                                elif not is_dead and self.entity.anim_sys is not None:
                                    self.entity.anim_sys.set_state(EntityState.IDLE)
                                return

                        self.entity.setPos(eject_x, self.entity.y())
                        self.entity._target_pos = None
                        if not is_dead and self.entity.anim_sys is not None:
                            self.entity.anim_sys.set_state(EntityState.IDLE)
                        return

        candidate_floors: list[float] = [ground_y]
        floor_to_win: dict[float, QRect] = {}
        # Maximum vertical step this frame (anti-tunneling tolerance)
        fall_step: float = max(8.0, self.entity.velocity_y + current_gravity + 4.0)

        for win in window_rects:
            if entity_right > win.left() + 4 and entity_left < win.right() - 4:
                win_top: float = float(win.top())
                # Platform must be at or below current feet or crossed during this frame's fall
                if entity_bottom <= win_top + fall_step and win_top < ground_y:
                    if win_top >= entity_bottom - 12.0:
                        candidate_floors.append(win_top)
                        floor_to_win[win_top] = win

        effective_ground_y: float = min(candidate_floors)
        self.current_platform_rect = floor_to_win.get(effective_ground_y, None)

        if entity_bottom < effective_ground_y or self.entity.velocity_y < 0:
            self.entity.velocity_y += current_gravity
            new_y: float = self.entity.y() + self.entity.velocity_y

            # Ceiling collision when jumping upwards into a window bottom
            if self.entity.velocity_y < 0:
                for win in window_rects:
                    if entity_right > win.left() + 4 and entity_left < win.right() - 4:
                        win_bottom: float = float(win.bottom())
                        if entity_top >= win_bottom - 6 and (entity_top + self.entity.velocity_y) <= win_bottom:
                            new_y = win_bottom - hitbox.y()
                            self.entity.velocity_y = 0.0
                            break

            if new_y + hitbox_bottom_offset >= effective_ground_y:
                new_y = effective_ground_y - hitbox_bottom_offset
                self.entity.velocity_y = 0.0
                if self.entity.state == EntityState.JUMPING and not is_dead:
                    self.entity.anim_sys.set_state(EntityState.IDLE)
                    
            self.entity.setPos(self.entity.x(), new_y)
        else:
            self.entity.velocity_y = 0.0
            if self.entity.state == EntityState.JUMPING and not is_dead:
                self.entity.anim_sys.set_state(EntityState.IDLE)