from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPixmap

from .projectile import Projectile

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsScene
    from ..entity.living_entity import Entity


class ProjectileManager:
    """
    Manages active projectiles, handling creation, tick updates, and scene cleanup.
    """

    def __init__(self, scene: QGraphicsScene):
        self.scene: QGraphicsScene = scene
        self.active_projectiles: list[Projectile] = []

    def spawn(
        self,
        pixmap: QPixmap,
        pos: QPointF,
        velocity: QPointF,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        **kwargs,
    ) -> Projectile:
        proj = Projectile(
            pixmap=pixmap,
            x=pos.x(),
            y=pos.y(),
            vx=velocity.x(),
            vy=velocity.y(),
            gravity=gravity,
            lifetime=lifetime,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            **kwargs,
        )
        self.scene.addItem(proj)
        self.active_projectiles.append(proj)
        return proj

    def update(
        self,
        dt_sec: float,
        bounds_w: float,
        bounds_h: float,
        window_tracker=None,
        active_entities: Optional[list[Entity]] = None,
    ) -> None:
        surviving_projectiles: list[Projectile] = []

        for proj in self.active_projectiles:
            proj.update_systems(
                dt_sec,
                bounds_w,
                bounds_h,
                window_tracker=window_tracker,
                active_entities=active_entities,
            )
            if proj.is_dead:
                # Ensures scene removal if destroy() wasn't directly called
                if proj.scene():
                    self.scene.removeItem(proj)
            else:
                surviving_projectiles.append(proj)

        self.active_projectiles = surviving_projectiles

    def clear_all(self) -> None:
        for proj in self.active_projectiles:
            if proj.scene():
                self.scene.removeItem(proj)
        self.active_projectiles.clear()
