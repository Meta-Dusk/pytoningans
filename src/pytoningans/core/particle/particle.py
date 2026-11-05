from __future__ import annotations

import math, random
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QGraphicsPixmapItem
from .types import ParticleConfig

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker
    from .particle_emitter import ParticleEmitter
    from .particle_manager import ParticleManager


class Particle(QGraphicsPixmapItem):
    """Universal item handling visual FX, physics particles, and gameplay projectiles."""

    def __init__(
        self,
        pixmap: QPixmap,
        pos: QPointF,
        velocity: QPointF,
        config: Optional[ParticleConfig] = None,
        particle_manager: Optional[ParticleManager] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(pixmap, parent)
        self.config: ParticleConfig = config or ParticleConfig()

        self.setPos(pos)
        self.setTransformOriginPoint(pixmap.width() / 2.0, pixmap.height() / 2.0)

        self.vx: float = velocity.x()
        self.vy: float = velocity.y()
        self.time_alive: float = 0.0
        self.is_dead: bool = False

        # Mutable instance copies for runtime state
        self.tags: set[str] = set(self.config.tags)
        self.particle_manager: Optional[ParticleManager] = particle_manager
        self.attached_emitters: list[ParticleEmitter] = []

        if self.config.initial_rotation_range != (0.0, 0.0):
            self.setRotation(random.uniform(*self.config.initial_rotation_range))

        if self.config.passthrough_mouse:
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

        cfg: ParticleConfig = self.config

        # Lifetime & Expiration
        self.time_alive += dt_sec
        progress: float = self.time_alive / cfg.lifetime
        if progress >= 1.0:
            impact_point: QPointF = (
                self.sceneBoundingRect().center()
                if self.scene() is not None
                else QPointF(self.x() + self.pixmap().width() / 2, self.y() + self.pixmap().height() / 2)
            )
            if cfg.on_particle_expire_emitter is not None and self.particle_manager is not None:
                cfg.on_particle_expire_emitter(self.particle_manager, impact_point)
            if cfg.on_expire:
                cfg.on_expire(self)
            self.destroy()
            return

        # Visual Effects
        if cfg.fade_out:
            self.setOpacity(max(0.0, 1.0 - progress))

        if cfg.scale_over_time != 1.0:
            current_scale = 1.0 + (cfg.scale_over_time - 1.0) * progress
            self.setScale(max(0.0, current_scale))

        self._homing_steering(dt_sec)

        # Physics
        if cfg.gravity != 0.0:
            self.vy += cfg.gravity * dt_sec

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        # Rotation
        if cfg.orient_to_velocity:
            speed: float = math.hypot(self.vx, self.vy)
            if speed > 1e-4:
                self.setRotation(math.degrees(math.atan2(self.vy, self.vx)))
        elif cfg.rotation_speed != 0.0:
            self.setRotation(self.rotation() + cfg.rotation_speed * dt_sec)

        # World Bounds
        bounce = cfg.bounce_bounds if not cfg.local_space else False
        if bounce:
            pix_w: int = self.pixmap().width()
            pix_h: int = self.pixmap().height()
            if new_x <= 0 or new_x + pix_w >= bounds_w:
                self.vx *= -1
                new_x = max(0.0, min(new_x, bounds_w - pix_w))
            if new_y <= 0 or new_y + pix_h >= bounds_h:
                self.vy *= -1
                new_y = max(0.0, min(new_y, bounds_h - pix_h))

        self.setPos(new_x, new_y)

        if not cfg.collide_windows and not cfg.collide_entities:
            return

        # Collisions
        if cfg.collide_windows and window_tracker is not None:
            scene_point: QPointF = (
                self.mapToScene(QPointF(new_x, new_y)) if cfg.local_space else QPointF(new_x, new_y)
            )
            if window_tracker.check_point_collision(scene_point):
                if cfg.on_particle_expire_emitter is not None and self.particle_manager is not None:
                    cfg.on_particle_expire_emitter(self.particle_manager, scene_point)
                if cfg.on_hit_window:
                    cfg.on_hit_window(self, scene_point)
                self.destroy()
                return

        if cfg.collide_entities and active_entities:
            hitbox: QRectF = self.sceneBoundingRect()
            for entity in active_entities:
                if entity is self.parentItem() or not entity.sceneBoundingRect().intersects(hitbox):
                    continue
                impact_point: QPointF = hitbox.center()
                if cfg.on_particle_expire_emitter is not None and self.particle_manager is not None:
                    cfg.on_particle_expire_emitter(self.particle_manager, impact_point)
                if cfg.on_hit_entity:
                    cfg.on_hit_entity(self, entity)
                self.destroy()
                return

    def _homing_steering(self, dt_sec: float) -> None:
        cfg: ParticleConfig = self.config
        if cfg.homing_target is None or cfg.homing_speed <= 0.0:
            return
        if cfg.homing_target.scene() is None or getattr(cfg.homing_target, "is_dead", False):
            return

        target_center: QPointF = cfg.homing_target.sceneBoundingRect().center()
        my_center: QPointF = (
            self.sceneBoundingRect().center()
            if self.scene() is not None
            else QPointF(self.x() + self.pixmap().width() / 2, self.y() + self.pixmap().height() / 2)
        )
        dx: float = target_center.x() - my_center.x()
        dy: float = target_center.y() - my_center.y()
        dist: float = math.hypot(dx, dy)
        if dist <= 1e-3:
            return

        current_speed: float = math.hypot(self.vx, self.vy)
        if current_speed <= 1e-4:
            return

        cur_angle: float = math.atan2(self.vy, self.vx)
        target_angle: float = math.atan2(dy, dx)
        angle_diff: float = (target_angle - cur_angle + math.pi) % (2.0 * math.pi) - math.pi

        turn_rate: float = (
            math.radians(cfg.homing_speed)
            if cfg.homing_speed > 2.0 * math.pi
            else cfg.homing_speed
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
