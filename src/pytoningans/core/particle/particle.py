from __future__ import annotations

import math, random
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QGraphicsPixmapItem

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker
    from .particle_emitter import ParticleEmitter
    from .particle_manager import ParticleManager
    from .types import (
        OptionalOnHitEntityCallback, OptionalOnHitWindowCallback,
        OptionalOnParticleExpireEmitterCallback, OptionalOnExpireCallback
    )


class Particle(QGraphicsPixmapItem):
    """Universal item handling visual FX, physics particles, and gameplay projectiles."""

    def __init__(
        self,
        pixmap: QPixmap,
        x: float,
        y: float,
        vx: float,
        vy: float,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        # Visual FX Toggles
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        # Tags, Motion & Steering
        tags: Optional[set[str]] = None,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = False,
        homing_target: Optional[QGraphicsItem] = None,
        homing_speed: float = 0.0,
        # Collision & Hierarchy Toggles
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        # Callbacks & Sub-Emitters
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
        particle_manager: Optional[ParticleManager] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(pixmap, parent)
        self.setPos(x, y)
        self.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)

        self.vx: float = vx
        self.vy: float = vy
        self.gravity: float = gravity
        self.lifetime: float = lifetime
        self.time_alive: float = 0.0
        self.is_dead: bool = False

        # Visuals
        self.fade_out: bool = fade_out
        self.scale_over_time: float = scale_over_time
        self.rotation_speed: float = rotation_speed

        # Tags
        self.tags: set[str] = set(tags) if tags else set()

        # Motion & Steering
        self.initial_rotation_range: tuple[float, float] = initial_rotation_range
        self.orient_to_velocity: bool = orient_to_velocity
        self.homing_target: Optional[QGraphicsItem] = homing_target
        self.homing_speed: float = homing_speed

        # Apply initial rotation range if specified
        if self.initial_rotation_range != (0.0, 0.0):
            self.setRotation(random.uniform(*self.initial_rotation_range))

        # Hierarchy & Physics
        self.local_space: bool = local_space
        self.bounce_bounds: bool = bounce_bounds if not local_space else False
        self.passthrough_mouse: bool = passthrough_mouse
        self.collide_windows: bool = collide_windows
        self.collide_entities: bool = collide_entities

        # Callbacks & Sub-Emitter Triggers
        self.on_hit_window = on_hit_window
        self.on_hit_entity = on_hit_entity
        self.on_expire = on_expire
        self.on_particle_expire_emitter = on_particle_expire_emitter
        self.particle_manager: Optional[ParticleManager] = particle_manager
        self.attached_emitters: list[ParticleEmitter] = []

        if self.passthrough_mouse:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)

    # --- Tagging System Helper Methods ---

    def has_tag(self, tag: str) -> bool:
        """Returns True if the particle possesses the specified tag."""
        return tag in self.tags

    def add_tag(self, tag: str) -> None:
        """Assigns a tag to the particle."""
        self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the particle."""
        self.tags.discard(tag)

    # --- Systems & Tick Updates ---

    def update_systems(
        self,
        dt_sec: float,
        bounds_w: float,
        bounds_h: float,
        window_tracker: Optional[WindowTracker] = None,
        active_entities: Optional[list[BaseEntity]] = None,
    ) -> None:
        if self.is_dead:
            return

        # Lifetime & Expiration
        self.time_alive += dt_sec
        progress: float = self.time_alive / self.lifetime
        if progress >= 1.0:
            impact_point = (
                self.sceneBoundingRect().center()
                if self.scene() is not None
                else QPointF(self.x() + self.pixmap().width() / 2, self.y() + self.pixmap().height() / 2)
            )
            if self.on_particle_expire_emitter is not None and self.particle_manager is not None:
                self.on_particle_expire_emitter(self.particle_manager, impact_point)
            if self.on_expire:
                self.on_expire(self)
            self.destroy()
            return

        # Visual Effects Updating
        if self.fade_out:
            self.setOpacity(max(0.0, 1.0 - progress))

        if self.scale_over_time != 1.0:
            current_scale = 1.0 + (self.scale_over_time - 1.0) * progress
            self.setScale(max(0.0, current_scale))

        self._homing_steering(dt_sec)

        # Movement & Gravity (Applies in local coordinate space if parented)
        if self.gravity != 0.0:
            self.vy += self.gravity * dt_sec

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        # Rotation and Orientation
        if self.orient_to_velocity:
            speed = math.hypot(self.vx, self.vy)
            if speed > 1e-4:
                self.setRotation(math.degrees(math.atan2(self.vy, self.vx)))
        elif self.rotation_speed != 0.0:
            self.setRotation(self.rotation() + self.rotation_speed * dt_sec)

        # World-space bounds check (skipped when local_space=True)
        if self.bounce_bounds:
            pix_w: int = self.pixmap().width()
            pix_h: int = self.pixmap().height()
            if new_x <= 0 or new_x + pix_w >= bounds_w:
                self.vx *= -1
                new_x = max(0.0, min(new_x, bounds_w - pix_w))
            if new_y <= 0 or new_y + pix_h >= bounds_h:
                self.vy *= -1
                new_y = max(0.0, min(new_y, bounds_h - pix_h))

        self.setPos(new_x, new_y)

        # Fast Bypass Guard Clause for Visual-Only Particles
        if not self.collide_windows and not self.collide_entities:
            return

        # Interactive Collision Processing
        if self.collide_windows and window_tracker is not None:
            # Map local position to scene coordinates if parented
            scene_point: QPointF = (
                self.mapToScene(QPointF(new_x, new_y))
                if self.local_space
                else QPointF(new_x, new_y)
            )
            if window_tracker.check_point_collision(scene_point):
                if self.on_particle_expire_emitter is not None and self.particle_manager is not None:
                    self.on_particle_expire_emitter(self.particle_manager, scene_point)
                if self.on_hit_window:
                    self.on_hit_window(self, scene_point)
                self.destroy()
                return

        if self.collide_entities and active_entities:
            hitbox: QRectF = self.sceneBoundingRect()
            for entity in active_entities:
                if (
                    entity is self.parentItem() or
                    not entity.sceneBoundingRect().intersects(hitbox)
                ):
                    continue
                impact_point: QPointF = hitbox.center()
                if self.on_particle_expire_emitter is not None and self.particle_manager is not None:
                    self.on_particle_expire_emitter(self.particle_manager, impact_point)
                if self.on_hit_entity:
                    self.on_hit_entity(self, entity)
                self.destroy()
                return

    def _homing_steering(self, dt_sec: float) -> None:
        # Homing Steering Logic: Steer velocity vector towards homing target
        if self.homing_target is None or self.homing_speed <= 0.0:
            return
        
        if (
            self.homing_target.scene() is None or
            getattr(self.homing_target, "is_dead", False)
        ):
            return
        
        target_center: QPointF = self.homing_target.sceneBoundingRect().center()
        my_center: QPointF = (
            self.sceneBoundingRect().center()
            if self.scene() is not None
            else QPointF(self.x() + self.pixmap().width() / 2, self.y() + self.pixmap().height() / 2)
        )
        dx: float = target_center.x() - my_center.x()
        dy: float = target_center.y() - my_center.y()
        dist: float = math.hypot(dx, dy)
        if dist <= 1e-3: return
        
        current_speed: float = math.hypot(self.vx, self.vy)
        if current_speed <= 1e-4: return
        
        cur_angle: float = math.atan2(self.vy, self.vx)
        target_angle: float = math.atan2(dy, dx)
        angle_diff: float = (target_angle - cur_angle + math.pi) % (2.0 * math.pi) - math.pi

        turn_rate: float = (
            math.radians(self.homing_speed)
            if self.homing_speed > 2.0 * math.pi
            else self.homing_speed
        )
        max_turn: float = turn_rate * dt_sec
        turn: float = math.copysign(min(abs(angle_diff), max_turn), angle_diff)
        new_angle: float = cur_angle + turn
        self.vx = math.cos(new_angle) * current_speed
        self.vy = math.sin(new_angle) * current_speed

    def destroy(self) -> None:
        if self.is_dead:
            return
        self.is_dead = True
        for emitter in self.attached_emitters:
            emitter.destroy()
        self.attached_emitters.clear()
        if self.scene():
            self.scene().removeItem(self)
