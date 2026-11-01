from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
    from PySide6.QtWidgets import QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker


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
        # Collision & Hierarchy Toggles
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        # Callbacks
        on_hit_window: Optional[Callable[[Particle, QPointF], None]] = None,
        on_hit_entity: Optional[Callable[[Particle, BaseEntity], None]] = None,
        on_expire: Optional[Callable[[Particle], None]] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        # Super init handles setParentItem if parent is provided
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

        # Hierarchy & Physics
        self.local_space: bool = local_space
        self.bounce_bounds: bool = bounce_bounds if not local_space else False
        self.passthrough_mouse: bool = passthrough_mouse
        self.collide_windows: bool = collide_windows
        self.collide_entities: bool = collide_entities

        # Callbacks
        self.on_hit_window = on_hit_window
        self.on_hit_entity = on_hit_entity
        self.on_expire = on_expire

        if self.passthrough_mouse:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)

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

        if self.rotation_speed != 0.0:
            self.setRotation(self.rotation() + self.rotation_speed * dt_sec)

        # Movement & Gravity (Applies in local coordinate space if parented)
        if self.gravity != 0.0:
            self.vy += self.gravity * dt_sec

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

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
                if self.on_hit_entity:
                    self.on_hit_entity(self, entity)
                self.destroy()
                return

    def destroy(self) -> None:
        self.is_dead = True
        if self.scene():
            self.scene().removeItem(self)
