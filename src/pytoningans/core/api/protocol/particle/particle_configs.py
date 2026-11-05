from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field

from ...types import Pos2D

if TYPE_CHECKING:
    from ...types import (
        ITexture, IGraphicsItem,
        OptionalOnHitEntityCallback, OptionalOnHitWindowCallback, OptionalOnExpireCallback,
        OptionalOnParticleSpawnEmitterCallback, OptionalOnParticleExpireEmitterCallback
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticleEmitterConfigDTO:
    """
    Data Transfer Object (DTO) for the ParticleEmitterConfig.\n
    Single source of truth for emitted particles' visual, physical, and collision properties.
    """
    
    pixmap: ITexture
    pos: Pos2D = field(default_factory=lambda: Pos2D(0.0, 0.0))
    """Initial position."""
    target: Optional[IGraphicsItem] = None
    """Optional object to attach emitted particles."""
    offset: Pos2D = field(default_factory=lambda: Pos2D(0.0, 0.0))
    """Offset based from the `target`."""
    local_space: bool = False
    """Emitted particles stay within the local space (inherited position) of the `target`."""

    # Emission Rate & Duration
    rate: float = 0.0
    """Emission rate."""
    duration: Optional[float] = None
    """Emittor duration."""

    # Randomization Ranges
    velocity_x_range: tuple[float, float] = (-50.0, 50.0)
    velocity_y_range: tuple[float, float] = (-50.0, 50.0)
    gravity_range: tuple[float, float] = (0.0, 0.0)
    lifetime_range: tuple[float, float] = (1.0, 2.5)
    rotation_speed_range: tuple[float, float] = (0.0, 0.0)
    scale_over_time_range: tuple[float, float] = (1.0, 1.0)
    initial_rotation_range: tuple[float, float] = (0.0, 0.0)

    # Shape & Radius
    spawn_radius: float = 0.0

    # Motion & Steering & Tags
    tags: Optional[set[str]] = None
    orient_to_velocity: bool = False
    """Force look at velocity's direction."""
    homing_target: Optional[IGraphicsItem] = None
    """Optional target to home into."""
    homing_speed: float = 0.0

    # Particle Flags
    fade_out: bool = True
    """Emitted particles fade out on expiration."""
    bounce_bounds: bool = True
    """Emitted particles bounce upon collision with boundaries."""
    passthrough_mouse: bool = True
    """Allow emitted particles to be interacted with the OS mouse."""
    collide_windows: bool = False
    """Allow emitted particles to collide with OS window."""
    collide_entities: bool = False
    """Allow emitted particles to collide with entities."""

    # Particle Callbacks & Hooks
    on_hit_window: OptionalOnHitWindowCallback = None
    """Called on emitted particles hitting an OS window."""
    on_hit_entity: OptionalOnHitEntityCallback = None
    """Called on emitted particles hitting an entity."""
    on_expire: OptionalOnExpireCallback = None
    """Called on emitted particles' expiration."""
    on_particle_spawn_emitter: OptionalOnParticleSpawnEmitterCallback = None
    """Called on spawn."""
    on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None
    """Called on expiration."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticleConfigDTO:
    """
    Data Transfer Object (DTO) for the ParticleConfig.\n
    Single source of truth for particle visual, physical, and collision properties."""

    # Physics & Lifetime
    gravity: float = 0.0
    """Applied vertical velocity."""
    lifetime: float = 3.0
    """Duration in seconds."""

    # Visual FX Toggles
    fade_out: bool = True
    """Fade out on expire."""
    scale_over_time: float = 1.0
    """Scale multiplier over time."""
    rotation_speed: float = 0.0
    """Rotation speed in degrees clockwise."""

    # Motion & Steering & Tags
    tags: set[str] = field(default_factory=set)
    initial_rotation_range: tuple[float, float] = (0.0, 0.0)
    orient_to_velocity: bool = False
    """Force look at velocity's direction."""
    homing_target: Optional[IGraphicsItem] = None
    """Optional target to home into."""
    homing_speed: float = 0.0

    # Collision & Hierarchy Toggles
    local_space: bool = False
    """Force local space transformation (inherit parent's location)."""
    bounce_bounds: bool = True
    """Bounce back upon hitting boundaries."""
    passthrough_mouse: bool = True
    """Ignore OS mouse interactions."""
    collide_windows: bool = False
    """Allow collision with OS windows."""
    collide_entities: bool = False
    """Allow collision with entities."""

    # Callbacks & Sub-Emitters
    on_hit_window: OptionalOnHitWindowCallback = None
    """Called upon hitting an OS window."""
    on_hit_entity: OptionalOnHitEntityCallback = None
    """Called upon hitting an entity."""
    on_expire: OptionalOnExpireCallback = None
    """Called upon duration expiration."""
    on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None
    """Called upon particle emitter expiration."""
    
    @classmethod
    def from_emitter_config(
        cls,
        emitter_cfg: ParticleEmitterConfigDTO,
        *,
        gravity: float,
        lifetime: float,
        scale_target: float,
        rotation_speed: float,
    ) -> ParticleConfigDTO:
        """Constructs a resolved ParticleConfig from a ParticleEmitterConfig template."""
        return cls(
            gravity=gravity,
            lifetime=lifetime,
            fade_out=emitter_cfg.fade_out,
            scale_over_time=scale_target,
            rotation_speed=rotation_speed,
            tags=emitter_cfg.tags or set(),
            initial_rotation_range=emitter_cfg.initial_rotation_range,
            orient_to_velocity=emitter_cfg.orient_to_velocity,
            homing_target=emitter_cfg.homing_target,
            homing_speed=emitter_cfg.homing_speed,
            local_space=emitter_cfg.local_space,
            bounce_bounds=emitter_cfg.bounce_bounds,
            passthrough_mouse=emitter_cfg.passthrough_mouse,
            collide_windows=emitter_cfg.collide_windows,
            collide_entities=emitter_cfg.collide_entities,
            on_hit_window=emitter_cfg.on_hit_window,
            on_hit_entity=emitter_cfg.on_hit_entity,
            on_expire=emitter_cfg.on_expire,
            on_particle_expire_emitter=emitter_cfg.on_particle_expire_emitter,
        )
