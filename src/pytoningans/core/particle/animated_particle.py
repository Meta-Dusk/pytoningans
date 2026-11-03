from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF, QRect

from .particle import Particle

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem
    from PySide6.QtGui import QPixmap
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker
    from .particle_manager import ParticleManager
    from .types import (
        OptionalOnHitWindowCallback, OptionalOnHitEntityCallback,
        OptionalOnParticleExpireEmitterCallback, OptionalOnExpireCallback
    )


class AnimatedParticle(Particle):
    """Lightweight particle subclass handling sprite sheet playback without entity FSM overhead."""

    def __init__(
        self,
        sprite_sheet: QPixmap,
        frame_width: int,
        frame_height: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        # Standard Particle Physics & Transform Parameters
        x: float = 0.0, y: float = 0.0,
        vx: float = 0.0, vy: float = 0.0,
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
        self.frame_width: int = max(1, int(frame_width))
        self.frame_height: int = max(1, int(frame_height))
        self.frame_count: int = max(1, int(frame_count))
        self.fps: float = fps
        self.loop: bool = loop

        self.frames: list[QPixmap] = []
        cols: int = max(1, sprite_sheet.width() // self.frame_width)
        for i in range(self.frame_count):
            col = i % cols
            row = i // cols
            frame_rect = QRect(
                col * self.frame_width,
                row * self.frame_height,
                self.frame_width,
                self.frame_height,
            )
            frame = sprite_sheet.copy(frame_rect)
            self.frames.append(frame)

        initial_pixmap: QPixmap = self.frames[0] if self.frames else sprite_sheet

        super().__init__(
            pixmap=initial_pixmap,
            x=x, y=y,
            vx=vx, vy=vy,
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            tags=tags,
            initial_rotation_range=initial_rotation_range,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_expire_emitter=on_particle_expire_emitter,
            particle_manager=particle_manager,
            parent=parent,
        )

        # Center transform origin point on the specific frame dimensions
        self.setTransformOriginPoint(self.frame_width / 2.0, self.frame_height / 2.0)

        self.anim_time: float = 0.0
        self.current_frame_index: int = 0

    def update_systems(
        self, dt_sec: float,
        bounds_w: float, bounds_h: float,
        window_tracker: Optional[WindowTracker] = None,
        active_entities: Optional[list[BaseEntity]] = None,
    ) -> None:
        if self.is_dead:
            return

        # Advance frame accumulation timer if animation is playable
        if self.fps > 0 and len(self.frames) > 1:
            self.anim_time += dt_sec
            frame_duration: float = 1.0 / self.fps
            raw_index = int(self.anim_time / frame_duration)

            if not self.loop and raw_index >= self.frame_count:
                # Finished one-shot animation playback
                impact_point = (
                    self.sceneBoundingRect().center()
                    if self.scene() is not None
                    else QPointF(self.x() + self.frame_width / 2, self.y() + self.frame_height / 2)
                )
                if self.on_particle_expire_emitter is not None and self.particle_manager is not None:
                    self.on_particle_expire_emitter(self.particle_manager, impact_point)
                if self.on_expire:
                    self.on_expire(self)
                self.destroy()
                return

            if self.loop:
                target_frame = raw_index % self.frame_count
            else:
                target_frame = min(raw_index, self.frame_count - 1)

            if target_frame != self.current_frame_index and target_frame < len(self.frames):
                self.current_frame_index = target_frame
                self.setPixmap(self.frames[self.current_frame_index])

        super().update_systems(
            dt_sec=dt_sec,
            bounds_w=bounds_w,
            bounds_h=bounds_h,
            window_tracker=window_tracker,
            active_entities=active_entities,
        )
