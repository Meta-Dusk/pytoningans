from __future__ import annotations

import random
from typing import Optional, cast, TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPointF, QVariantAnimation
from PySide6.QtWidgets import QGraphicsSceneContextMenuEvent, QMenu

from pytoningans.core.api import BaseBehavior, BaseEntityBehavior, IEntity, Pos2D
from pytoningans.core.constants import AnimationMeta, DeathAnimation, EntityState
from pytoningans.core.entity.ai_brain import AISystem
from pytoningans.core.entity.base_entity import BaseEntity
from pytoningans.core.entity.indicators import HealthBarItem
from pytoningans.core.entity.speech_bubble import SpeechBubble
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.world import WorldOverlay
from pytoningans.core.settings import SettingsManager

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager
    from pytoningans.core.entity.base_item import BaseItem


class Entity(BaseEntity):
    """Living entities with AI, health, dialogue, and combat."""
    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: ModManager, world: WorldOverlay, entity_manager: EntityManager
    ) -> None:
        super().__init__(start_x, start_y, mod_manager, world)
        self.entity_manager = entity_manager

        self.is_dead: bool = False
        self.current_health: int = mod_manager.max_health if mod_manager else 100
        self.damage_tint_time_left: int = 0
        self.revive_time_left: int = 0
        self._target_pos: Optional[QPointF] = None
        self.held_item: Optional[BaseItem] = None

        self._fade_anim: Optional[QVariantAnimation] = None
        self._rot_anim: Optional[QVariantAnimation] = None

        self.ai_sys: Optional[AISystem] = AISystem(self)
        self.bubble: Optional[SpeechBubble] = None
        self.health_bar: Optional[HealthBarItem] = HealthBarItem(self)

        if self.anim_sys is not None:
            self.anim_sys.attack_frame_hit.connect(self.ai_sys.process_combat)

    def on_hover_enter(self) -> None:
        super().on_hover_enter()
        if self.health_bar is not None and not self.is_dead:
            self.health_bar.set_hovered(True)

    def on_hover_leave(self) -> None:
        super().on_hover_leave()
        if self.health_bar is not None:
            self.health_bar.set_hovered(False)

    @property
    def is_interactable(self) -> bool:
        return (
            super().is_interactable and
            self.state not in (EntityState.DRAG, EntityState.INTERACT) and
            not self.is_dead
        )

    @property
    def target_pos(self) -> Optional[QPointF]:
        return self._target_pos

    @target_pos.setter
    def target_pos(self, pos: Optional[Pos2D]) -> None:
        if pos is None:
            self._target_pos = None
        else:
            self._target_pos = QPointF(pos.x, pos.y)

    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        if self.is_paused: return

        if self.bubble is not None: self.bubble.tick(dt)
        if self.health_bar is not None: self.health_bar.tick(dt)

        if self.revive_time_left > 0:
            self.revive_time_left -= dt
            if self.revive_time_left <= 0:
                if self.anim_sys is not None: self.anim_sys.set_state(EntityState.IDLE)
                self.locks.ai = True
                self.locks.physics = self.is_physics_enabled

        if (
            self.damage_tint_time_left > 0 and
            self.tint_effect is not None
        ):
            self.damage_tint_time_left -= dt
            if self.damage_tint_time_left <= 0:
                self.tint_effect.setEnabled(False)
            else:
                fade_strength: float = 0.7 * (self.damage_tint_time_left / 300.0)
                self.tint_effect.setStrength(fade_strength)

        if self.is_dead:
            super().update_systems(dt, centers)
            return

        if (
            not self.is_force_idle and
            self.locks.ai and
            self.ai_sys is not None
        ):
            self.ai_sys.update(dt)
        super().update_systems(dt, centers)

        if not self.is_force_idle:
            behavior: Optional[BaseBehavior] = self.get_behavior
            if behavior is None: return
            if isinstance(behavior, BaseEntityBehavior):
                try:
                    behavior.on_update(cast(IEntity, self), dt)
                except Exception as e:
                    print(f"Custom Entity on_update Error: {e}")

    def on_moved(self) -> None:
        if self.health_bar is not None: self.health_bar.update_position()
        if self.bubble is not None: self.bubble.update_position()
        if self.held_item is not None: self.held_item._update_held_position()

    def pick_up(self, item: BaseItem) -> bool:
        """Picks up the specified item if possible."""
        return item.pick_up(self)

    def drop_item(self) -> Optional[BaseItem]:
        """Drops the currently held item onto the ground."""
        if self.held_item is not None:
            item: BaseItem = self.held_item
            item.drop(self)
            return item
        return None

    def use_item(self) -> bool:
        """Uses the currently held item."""
        if self.held_item is not None:
            return self.held_item.use(self)
        return False

    def on_instance_name_changed(self) -> None:
        super().on_instance_name_changed()
        if self.health_bar is not None:
            self.health_bar.update_position()
            self.health_bar.update()

    def take_damage(self, amount: int) -> None:
        if self.is_dead: return
        old_hp: int = self.current_health
        self.current_health = max(0, self.current_health - amount)
        actual_damage: int = old_hp - self.current_health

        self.damage_tint_time_left = 300
        if self.tint_effect is not None:
            self.tint_effect.setEnabled(True)
            self.tint_effect.setStrength(0.85)

        if self.health_bar is not None:
            self.health_bar.on_damage_taken(actual_damage, self.current_health, old_hp)

        if self.bubble is not None and self.bubble.isVisible():
            max_hp: int = self.mod_manager.max_health if self.mod_manager else 100
            ratio: float = min(1.0, max(0.1, actual_damage / max(1, max_hp)))
            amp: float = 3.0 + (ratio * 6.0)
            self.bubble.shake(amplitude=amp, duration_ms=250)

        if self.world is not None and SettingsManager.get().settings.show_damage_numbers:
            head_pos: QPointF = self.pos() + QPointF(self.width() / 2.0, -10.0)
            self.world.spawn_damage_number(actual_damage, head_pos, is_heal=False)

        self._on_damage(amount)

        if self.current_health <= 0:
            self.die()

    def heal(self, amount: int) -> None:
        if self.is_dead or amount <= 0: return
        old_hp: int = self.current_health
        max_hp: int = self.mod_manager.max_health if self.mod_manager else 100
        self.current_health = min(max_hp, self.current_health + amount)
        actual_heal: int = self.current_health - old_hp
        if actual_heal <= 0: return

        if self.health_bar:
            self.health_bar.on_heal(actual_heal, self.current_health, old_hp)

        if self.world and SettingsManager.get().settings.show_damage_numbers:
            head_pos: QPointF = self.pos() + QPointF(self.width() / 2.0, -10.0)
            self.world.spawn_damage_number(actual_heal, head_pos, is_heal=True)

    def jump(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or self.mod_manager.can_fly: return
        if self.velocity_y != 0: return

        self.velocity_y = -self.mod_manager.jump_height
        if self.anim_sys: self.anim_sys.set_state(EntityState.JUMPING)

    def die(self) -> None:
        if self.is_dead or self.mod_manager is None: return
        self.current_health = 0
        self.is_dead = True
        
        if self.held_item is not None:
            self.held_item.drop(self)
            
        self.sprite_rotation = 0.0
        if self.anim_sys: self.anim_sys.set_state(EntityState.DYING)
        self._target_pos = None

        if self.health_bar is not None:
            self.health_bar.on_die()

        # Trigger death dialogue, overriding or interrupting any active speech bubble
        death_lines: list[str] = getattr(self.mod_manager, "death_dialogue", [])
        if death_lines:
            death_text: str = random.choice(death_lines)
            if self.bubble is not None and self.bubble.isVisible():
                self.bubble.interrupt_with(death_text, duration_ms=3500)
            else:
                self.say(death_text, duration_ms=3500, is_death=True)
        elif self.bubble is not None and self.bubble.isVisible():
            self.bubble.interrupt_with(None)

        death_type: DeathAnimation = self.mod_manager.death_animation
        target_rot: float = 0.0

        match death_type:
            case DeathAnimation.ROTATE_LEFT:
                target_rot = -90.0
            case DeathAnimation.ROTATE_RIGHT:
                target_rot = 90.0
            case DeathAnimation.ROTATE_LEFT_OR_RIGHT:
                target_rot = -90.0 if random.random() > 0.5 else 90.0

        if target_rot != 0.0:
            self._rot_anim = QVariantAnimation(self.world)
            self._rot_anim.setDuration(600)
            self._rot_anim.setStartValue(self.sprite_rotation)
            self._rot_anim.setEndValue(target_rot)
            self._rot_anim.setEasingCurve(QEasingCurve.Type.OutBounce)

            def _on_rot_change(val: float):
                self.sprite_rotation = val
                if self.anim_sys: self.anim_sys._update_frame()

            self._rot_anim.valueChanged.connect(_on_rot_change)
            self._rot_anim.start()

        self._on_die()

        if self.mod_manager.auto_close_on_death:
            fade_duration: int = 3500 if death_lines else 3000
            self._fade_anim = QVariantAnimation(self.world)
            self._fade_anim.setDuration(fade_duration)
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)

            self._fade_anim.valueChanged.connect(self.setOpacity)
            self._fade_anim.finished.connect(self.destroy)
            self._fade_anim.start()

    def revive(self) -> None:
        if self.mod_manager is None or not self.is_dead: return

        self.current_health = self.mod_manager.max_health
        self.is_dead = False

        if self.health_bar is not None:
            self.health_bar.on_revive()

        if self.bubble is not None:
            self.bubble.reset()
            self.bubble.hide()

        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        if self._rot_anim is not None:
            self._rot_anim.stop()
            self._rot_anim = None

        self.setOpacity(1.0)
        self.sprite_rotation = 0.0

        anim_meta: Optional[AnimationMeta] = self.mod_manager.animations.get(EntityState.REVIVING)

        if anim_meta is not None:
            total_frames: int = (anim_meta.end_frame - anim_meta.start_frame) + 1
            ms_per_frame: int = 1000 // max(1, anim_meta.fps)

            self.revive_time_left = total_frames * ms_per_frame
            if self.anim_sys: self.anim_sys.set_state(EntityState.REVIVING)

            self.locks.ai = False
            self.locks.physics = False
        else:
            if self.anim_sys: self.anim_sys.set_state(EntityState.IDLE)
        self._on_revive()

    def say(self, text: str, duration_ms: int = 4000, is_death: bool = False) -> None:
        """Displays a speech bubble with the given text and notifies custom behavior."""
        if self.is_dead and not is_death: return
        if self.bubble is None:
            self.bubble = SpeechBubble(self)

        self.bubble.speak(text, duration_ms)
        self._on_speak(text)

    def force_talk(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or not self.mod_manager.plain_dialogue: return

        text: str = random.choice(self.mod_manager.plain_dialogue)
        self.say(text, 4000)

        if self.anim_sys: self.anim_sys.set_state(EntityState.IDLE)
        self._target_pos = None

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.sprite_rotation = 0.0

        if self.is_dead:
            if (
                self._fade_anim is not None and
                self._fade_anim.state() == QVariantAnimation.State.Running
            ):
                self._fade_anim.pause()
            if (
                self._rot_anim is not None and
                self._rot_anim.state() == QVariantAnimation.State.Running
            ):
                self._rot_anim.pause()

        super().contextMenuEvent(event)

        if not self.is_dead: return
        if (
            self._fade_anim is not None and
            self._fade_anim.state() == QVariantAnimation.State.Paused
        ):
            self._fade_anim.resume()
        if (
            self._rot_anim is not None and
            self._rot_anim.state() == QVariantAnimation.State.Paused
        ):
            self._rot_anim.resume()

    def _on_die(self) -> None:
        behavior: Optional[BaseBehavior] = self.get_behavior
        if not isinstance(behavior, BaseEntityBehavior): return

        entity_api: IEntity = cast(IEntity, self)
        behavior.on_death(entity_api)

    def _on_revive(self) -> None:
        behavior: Optional[BaseBehavior] = self.get_behavior
        if not isinstance(behavior, BaseEntityBehavior): return

        entity_api: IEntity = cast(IEntity, self)
        behavior.on_revive(entity_api)

    def _on_speak(self, text: str) -> None:
        behavior: Optional[BaseBehavior] = self.get_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        try:
            behavior.on_speak(cast(IEntity, self), text)
        except Exception as e:
            print(f"Custom Entity on_speak Error: {e}")

    def _on_damage(self, amount: int) -> None:
        behavior: Optional[BaseBehavior] = self.get_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        try:
            behavior.on_damage(cast(IEntity, self), amount)
        except Exception as e:
            print(f"Custom Entity on_damage Error: {e}")

    def destroy(self) -> None:
        if self.held_item is not None:
            self.held_item.drop(self)

        if self.health_bar is not None:
            self.health_bar.detach()
            self.health_bar = None
            
        if self.bubble is not None:
            self.bubble.detach()
            self.bubble = None
            
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
            
        if self._rot_anim is not None:
            self._rot_anim.stop()
            self._rot_anim = None
            
        if self.ai_sys is not None:
            if self.anim_sys is not None:
                try:
                    self.anim_sys.attack_frame_hit.disconnect(self.ai_sys.process_combat)
                except Exception:
                    pass
            self.ai_sys.entity = None
            self.ai_sys = None
            
        if (
            self.entity_manager is not None and
            self in self.entity_manager.active_entities
        ):
            self.entity_manager.remove_entity(self)
            
        super().destroy()
        self.entity_manager = None