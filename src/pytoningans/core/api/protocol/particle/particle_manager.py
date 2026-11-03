from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol, Union, runtime_checkable

from ...types import Pos2D

if TYPE_CHECKING:
    from .particle import IParticle
    from .particle_emitter import IParticleEmitter
    from ..entity import IBaseEntity
    from ...types import (
        OptionalOnHitWindowCallback, OptionalOnHitEntityCallback, OptionalOnExpireCallback,
        OptionalOnParticleExpireEmitterCallback, OptionalOnParticleSpawnEmitterCallback
    )


# TODO: Avoid using **kwargs for the IParticleAPI Protocol's parameters
@runtime_checkable
class IParticleAPI(Protocol):
    """Public interface for spawning particles, creating emitters, and triggering presets."""

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
        """Spawns a single particle or projectile into the current world overlay."""
        ...

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
        """Spawns an interactive projectile pre-configured with default collision and 'projectile' tag."""
        ...

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
        """Spawns an animated sprite sheet particle without entity FSM overhead."""
        ...

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
        """Creates a continuous stream or timed duration particle emitter."""
        ...

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
        ...

    def spawn_square(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        size: int = 10,
        color: str = "white",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated square particle."""
        ...

    def spawn_ring(
        self,
        pos: Pos2D,
        velocity: Pos2D,
        radius: int = 10,
        thickness: int = 2,
        color: str = "white",
        **kwargs: Any,
    ) -> IParticle:
        """Spawns a procedurally generated ring particle."""
        ...

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
        ...

    # --- Preset Helpers ---

    def trigger_explosion(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D,
        count: int = 30,
        speed_min: float = 100.0,
        speed_max: float = 300.0,
        gravity: float = 200.0,
        lifetime: float = 1.2,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_entity: OptionalOnHitEntityCallback = None,
    ) -> list[IParticle]:
        """Triggers a radial burst explosion particle preset."""
        ...

    def attach_dust_trail(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D = Pos2D(0.0, 0.0),
        target: Optional[IBaseEntity] = None,
        offset: Pos2D = Pos2D(0.0, 0.0),
        rate: float = 15.0,
        duration: Optional[float] = None,
    ) -> IParticleEmitter:
        """Spawns a rising footstep dust trail emitter attached to a target entity or position."""
        ...

    def trigger_spark_impact(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D,
        count: int = 12,
    ) -> list[IParticle]:
        """Triggers a short-lived spark burst preset."""
        ...

    def attach_ambient_aura(
        self,
        texture: Union[str, tuple, Any],
        pos: Pos2D = Pos2D(0.0, 0.0),
        target: Optional[IBaseEntity] = None,
        offset: Pos2D = Pos2D(0.0, 0.0),
        radius: float = 25.0,
        rate: float = 10.0,
        local_space: bool = True,
    ) -> IParticleEmitter:
        """Spawns an ambient aura levitation emitter surrounding a target entity or position."""
        ...

