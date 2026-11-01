from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem

if TYPE_CHECKING:
    from ..entity.living_entity import Entity


class Projectile(QGraphicsPixmapItem):
    """Lightweight graphics item representing a moving projectile or particle effect."""

    def __init__(
        self,
        pixmap: QPixmap,
        x: float,
        y: float,
        vx: float,
        vy: float,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: Optional[Callable[[Projectile, QPointF], None]] = None,
        on_hit_entity: Optional[Callable[[Projectile, Entity], None]] = None,
        on_expire: Optional[Callable[[Projectile], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(pixmap, parent)
        self.setPos(x, y)
        
        self.vx: float = vx
        self.vy: float = vy
        self.gravity: float = gravity
        self.lifetime: float = lifetime
        self.time_alive: float = 0.0
        self.is_dead: bool = False

        # Collision & Mouse behavior toggles
        self.passthrough_mouse: bool = passthrough_mouse
        self.collide_windows: bool = collide_windows
        self.collide_entities: bool = collide_entities

        # Event Callbacks
        self.on_hit_window = on_hit_window
        self.on_hit_entity = on_hit_entity
        self.on_expire = on_expire

        # Optimize C++ layer mouse processing
        if self.passthrough_mouse:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)

    def update_systems(
        self,
        dt_sec: float,
        bounds_w: float,
        bounds_h: float,
        window_tracker=None,
        active_entities: Optional[list[Entity]] = None,
    ) -> None:
        if self.is_dead:
            return

        # Lifetime expiration
        self.time_alive += dt_sec
        if self.time_alive >= self.lifetime:
            if self.on_expire:
                self.on_expire(self)
            self.destroy()
            return

        # Velocity & Gravity
        if self.gravity != 0.0:
            self.vy += self.gravity * dt_sec

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        # Screen border boundary check / bouncing
        pix_w: int = self.pixmap().width()
        pix_h: int = self.pixmap().height()

        if new_x <= 0 or new_x + pix_w >= bounds_w:
            self.vx *= -1
            new_x = max(0.0, min(new_x, bounds_w - pix_w))

        if new_y <= 0 or new_y + pix_h >= bounds_h:
            self.vy *= -1
            new_y = max(0.0, min(new_y, bounds_h - pix_h))

        self.setPos(new_x, new_y)

        # Optional Win32 Window Collisions (Stubbed for integration)
        if self.collide_windows and window_tracker is not None:
            impact_point = QPointF(new_x + pix_w / 2, new_y + pix_h / 2)
            if hasattr(window_tracker, "check_point_collision") and window_tracker.check_point_collision(impact_point):
                if self.on_hit_window:
                    self.on_hit_window(self, impact_point)
                self.destroy()
                return

        # Optional Entity Collisions
        if self.collide_entities and active_entities:
            hitbox: QRectF = self.sceneBoundingRect()
            for entity in active_entities:
                if entity.sceneBoundingRect().intersects(hitbox):
                    if self.on_hit_entity:
                        self.on_hit_entity(self, entity)
                    self.destroy()
                    return

    def destroy(self) -> None:
        self.is_dead = True
        if self.scene():
            self.scene().removeItem(self)
