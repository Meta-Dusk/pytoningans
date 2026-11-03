from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

from ...types import Pos2D

if TYPE_CHECKING:
    from .particle import IParticle
    from .particle_emitter import IParticleEmitter
    from ..entity import IBaseEntity
    from ...types import (
        OptionalOnHitWindowCallback, OptionalOnHitEntityCallback,
        OptionalOnParticleSpawnEmitterCallback, OptionalOnParticleExpireEmitterCallback,
        OptionalOnExpireCallback
    )


# TODO: Avoid using **kwargs for the ParticleAPI's parameters
class ParticleAPI:
    """
    Concrete adapter wrapping a ParticleManager to expose decoupled Particle API operations
    for modders and engine behaviors without requiring direct PySide6 dependency.
    """

    def __init__(self, manager: Any) -> None:
        self._manager: Any = manager

    @staticmethod
    def _to_point(pos: Union[Pos2D, Any]) -> Any:
        if isinstance(pos, Pos2D):
            from PySide6.QtCore import QPointF
            return QPointF(pos.x, pos.y)
        return pos

    def spawn_particle(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D,
        velocity: Pos2D,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = False,
        homing_target: Optional[Any] = None,
        homing_speed: float = 0.0,
        tags: Optional[set[str]] = None,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
        target: Optional[IBaseEntity] = None,
    ) -> IParticle:
        return self._manager.spawn(
            pixmap=texture,
            pos=self._to_point(pos),
            velocity=self._to_point(velocity),
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            initial_rotation_range=initial_rotation_range,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            tags=tags,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_expire_emitter=on_particle_expire_emitter,
            parent=target,
        )

    def spawn_projectile(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D,
        velocity: Pos2D,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        tags: Optional[set[str]] = None,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = True,
        homing_target: Optional[Any] = None,
        homing_speed: float = 0.0,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = True,
        collide_entities: bool = True,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
    ) -> IParticle:
        return self._manager.spawn_projectile(
            pixmap=texture,
            pos=self._to_point(pos),
            velocity=self._to_point(velocity),
            gravity=gravity,
            lifetime=lifetime,
            tags=tags,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
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
        )

    def spawn_animated_particle(
        self,
        sprite_sheet: Union[str, tuple, Any],
        pos: Pos2D,
        velocity: Pos2D,
        frame_width: int,
        frame_height: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        tags: Optional[set[str]] = None,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = False,
        homing_target: Optional[Any] = None,
        homing_speed: float = 0.0,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
    ) -> IParticle:
        return self._manager.spawn_animated_particle(
            sprite_sheet=sprite_sheet,
            pos=self._to_point(pos),
            velocity=self._to_point(velocity),
            frame_width=frame_width,
            frame_height=frame_height,
            frame_count=frame_count,
            fps=fps,
            loop=loop,
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
        )

    def create_emitter(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D = Pos2D(0.0, 0.0),
        target: Optional[IBaseEntity] = None,
        offset: Pos2D = Pos2D(0.0, 0.0),
        local_space: bool = False,
        rate: float = 0.0,
        duration: Optional[float] = None,
        velocity_x_range: tuple[float, float] = (-50.0, 50.0),
        velocity_y_range: tuple[float, float] = (-50.0, 50.0),
        gravity_range: tuple[float, float] = (0.0, 0.0),
        lifetime_range: tuple[float, float] = (1.0, 2.5),
        rotation_speed_range: tuple[float, float] = (0.0, 0.0),
        scale_over_time_range: tuple[float, float] = (1.0, 1.0),
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        spawn_radius: float = 0.0,
        tags: Optional[set[str]] = None,
        orient_to_velocity: bool = False,
        homing_target: Optional[Any] = None,
        homing_speed: float = 0.0,
        fade_out: bool = True,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_spawn_emitter: OptionalOnParticleSpawnEmitterCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
    ) -> IParticleEmitter:
        return self._manager.create_emitter(
            pixmap=texture,
            pos=self._to_point(pos),
            target=target,
            offset=self._to_point(offset),
            local_space=local_space,
            rate=rate,
            duration=duration,
            velocity_x_range=velocity_x_range,
            velocity_y_range=velocity_y_range,
            gravity_range=gravity_range,
            lifetime_range=lifetime_range,
            rotation_speed_range=rotation_speed_range,
            scale_over_time_range=scale_over_time_range,
            initial_rotation_range=initial_rotation_range,
            spawn_radius=spawn_radius,
            tags=tags,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            fade_out=fade_out,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_spawn_emitter=on_particle_spawn_emitter,
            on_particle_expire_emitter=on_particle_expire_emitter,
        )

    # --- Procedural Shape Helpers ---

    def spawn_dot(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        radius: int = 5,
        color: str = "white",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated solid circle particle."""
        return self.spawn_particle(("dot", radius, color), pos, velocity, **kwargs)

    def spawn_square(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        size: int = 10,
        color: str = "white",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated square particle."""
        return self.spawn_particle(("square", size, color), pos, velocity, **kwargs)

    def spawn_ring(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        radius: int = 10,
        thickness: int = 2,
        color: str = "white",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated hollow ring particle."""
        return self.spawn_particle(("ring", radius, thickness, color), pos, velocity, **kwargs)

    def spawn_glow_circle(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        radius: int = 15,
        core_color: str = "white",
        outer_color: str = "transparent",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated glowing radial circle particle."""
        return self.spawn_particle(("glow_circle", radius, core_color, outer_color), pos, velocity, **kwargs)
    
    # --- Preset Helpers ---
    # TODO: Fix ParticleAPI methods
    # def trigger_explosion(
    #     self,
    #     texture: Union[str, tuple, Any],
    #     pos: Pos2D,
    #     count: int = 30,
    #     speed_min: float = 100.0,
    #     speed_max: float = 300.0,
    #     gravity: float = 200.0,
    #     lifetime: float = 1.2,
    #     collide_windows: bool = False,
    #     collide_entities: bool = False,
    #     on_hit_entity: OptionalOnHitEntityCallback = None,
    # ) -> list[IParticle]:
    #     from pytoningans.core.particle.particle_presets import ParticlePresets
    #     from pytoningans.core.particle.procedural_graphics import ProceduralGraphics
    #     pix = ProceduralGraphics.resolve_texture(texture)
    #     return ParticlePresets.explode(
    #         manager=self._manager,
    #         pixmap=pix,
    #         pos=self._to_point(pos),
    #         count=count,
    #         speed_min=speed_min,
    #         speed_max=speed_max,
    #         gravity=gravity,
    #         lifetime=lifetime,
    #         collide_windows=collide_windows,
    #         collide_entities=collide_entities,
    #         on_hit_entity=on_hit_entity,
    #     )

    # def attach_dust_trail(
    #     self,
    #     texture: Union[str, tuple, Any],
    #     pos: Pos2D = Pos2D(0.0, 0.0),
    #     target: Optional[IBaseEntity] = None,
    #     offset: Pos2D = Pos2D(0.0, 0.0),
    #     rate: float = 15.0,
    #     duration: Optional[float] = None,
    # ) -> IParticleEmitter:
    #     from pytoningans.core.particle.particle_presets import ParticlePresets
    #     from pytoningans.core.particle.procedural_graphics import ProceduralGraphics
    #     pix = ProceduralGraphics.resolve_texture(texture)
    #     return ParticlePresets.dust_trail(
    #         manager=self._manager,
    #         pixmap=pix,
    #         pos=self._to_point(pos),
    #         target=target,
    #         offset=self._to_point(offset),
    #         rate=rate,
    #         duration=duration,
    #     )

    # def trigger_spark_impact(
    #     self,
    #     texture: Union[str, tuple, Any],
    #     pos: Pos2D,
    #     count: int = 12,
    # ) -> list[IParticle]:
    #     from pytoningans.core.particle.particle_presets import ParticlePresets
    #     from pytoningans.core.particle.procedural_graphics import ProceduralGraphics
    #     pix = ProceduralGraphics.resolve_texture(texture)
    #     return ParticlePresets.spark_impact(
    #         manager=self._manager,
    #         pixmap=pix,
    #         pos=self._to_point(pos),
    #         count=count,
    #     )

    # def attach_ambient_aura(
    #     self,
    #     texture: Union[str, tuple, Any],
    #     pos: Pos2D = Pos2D(0.0, 0.0),
    #     target: Optional[IBaseEntity] = None,
    #     offset: Pos2D = Pos2D(0.0, 0.0),
    #     radius: float = 25.0,
    #     rate: float = 10.0,
    #     local_space: bool = True,
    # ) -> IParticleEmitter:
    #     from pytoningans.core.particle.particle_presets import ParticlePresets
    #     from pytoningans.core.particle.procedural_graphics import ProceduralGraphics
    #     pix = ProceduralGraphics.resolve_texture(texture)
    #     return ParticlePresets.ambient_aura(
    #         manager=self._manager,
    #         pixmap=pix,
    #         pos=self._to_point(pos),
    #         target=target,
    #         offset=self._to_point(offset),
    #         radius=radius,
    #         rate=rate,
    #         local_space=local_space,
    #     )

