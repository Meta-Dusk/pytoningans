from __future__ import annotations

import random, math

from typing import TYPE_CHECKING, cast, Optional, List
from PySide6.QtCore import QPointF, QRectF

from pytoningans.core.constants import EntityState, BehaviorType, AttackType
from pytoningans.core.api import BaseEntityBehavior, IEntity
from pytoningans.core.entity.speech_bubble import SpeechBubble

if TYPE_CHECKING:
    from pytoningans.core.entity.base import Entity
    from pytoningans.core.entity_manager import EntityManager

class AISystem:
    def __init__(self, entity: Optional[Entity] = None) -> None:
        self.entity: Optional[Entity] = entity
        
        self.decision_accumulator: int = 0
        
        self.interact_time_left: int = 0
        self.interaction_cooldown: int = 0
        
        self.attack_time_left: int = 0
        self.attack_cooldown: int = 0
    
    def update(self, dt: int) -> None:
        if self.entity is None or self.entity.anim_sys is None: return
        self.decision_accumulator += dt
        
        if self.interaction_cooldown > 0: self.interaction_cooldown -= dt
        if self.attack_cooldown > 0: self.attack_cooldown -= dt
        
        if self.entity.state is EntityState.INTERACT:
            self.interact_time_left -= dt
            if self.interact_time_left <= 0:
                self.entity.anim_sys.set_state(EntityState.IDLE)
            return
            
        if self.entity.state is EntityState.ATTACK:
            self.attack_time_left -= dt
            if self.attack_time_left <= 0:
                self.entity.anim_sys.set_state(EntityState.IDLE)
            return

        if self.decision_accumulator >= 2500:
            self.decision_accumulator = 0
            if self._check_environment(): return
            self._ai_decision_tick()
            
        self.check_combat()
        
        if self.entity.state is not EntityState.ATTACK:
            self.check_interactions()
    
    def _ai_decision_tick(self) -> None:
        if self.entity is None: return
        if self.entity.state in (EntityState.DRAG, EntityState.INTERACT): return
        if self._on_ai_decision_tick(): return
        self._default_ai_decision()

    def _default_ai_decision(self) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.anim_sys is None or
            self.entity.world is None
        ):
            return
        
        if not self.entity.mod_manager.can_fly and random.random() < 0.15:
            self.entity.jump()
            return
        
        geom: QRectF = self.entity.world.scene.sceneRect()

        if random.random() < 0.60:
            dest_x: float = random.uniform(
                geom.left() + 50,
                geom.right() - self.entity.boundingRect().width() - 50
            )
            dest_y: float = 0.0
            if self.entity.mod_manager.can_fly:
                dest_y = random.uniform(
                    geom.top() + 50,
                    geom.bottom() - self.entity.boundingRect().height() - 50
                )
            else:
                dest_y = self.entity.y()

            self.entity._target_pos = QPointF(dest_x, dest_y)
            self.entity.anim_sys.set_state(EntityState.MOVING)
        else:
            self.entity._target_pos = None
            self.entity.anim_sys.set_state(EntityState.IDLE)
    
    def _on_ai_decision_tick(self) -> bool:
        if self.entity is None or self.entity.mod_manager is None: return False
        
        behavior: Optional[BaseEntityBehavior] = self.entity.mod_manager.custom_behavior
        if behavior is None: return False
        try:
            pet_api: IEntity = cast(IEntity, self.entity)
            if behavior.on_decision_tick(pet_api): return True
        except Exception as e:
            print(f"Custom AI Error (Decision): {e}")
            
        return False
    
    def check_combat(self) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.entity_manager is None
        ):
            return
        
        if self.entity.mod_manager.behavior_type is not BehaviorType.HOSTILE:
            return
        
        if self.attack_cooldown > 0 or not self.entity.is_interactable:
            return

        my_center: QPointF = self.entity.pos() + self.entity.current_hitbox.center()

        for other_entity in self.entity.entity_manager.active_entities:
            if (
                other_entity is self.entity or
                not other_entity.is_interactable or
                other_entity is None or
                other_entity.mod_manager is None or
                other_entity.entity_manager is None
            ):
                continue
            
            if other_entity.mod_manager.current_mod_name == self.entity.mod_manager.current_mod_name:
                continue
            
            other_center: QPointF = other_entity.pos() + other_entity.current_hitbox.center()
            distance: float = self._get_distance(my_center, other_center)

            if distance > self.entity.mod_manager.attack_range: continue
            
            override_default: bool = self._on_combat_check(other_entity)

            if not override_default:
                self._default_combat_logic(my_center, other_center)
                    
            break 

    def _get_distance(self, my_center: QPointF, other_center: QPointF) -> float:
        return math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())

    def _default_combat_logic(
        self, my_center: QPointF, other_center: QPointF
    ) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.anim_sys is None
        ):
            return
        
        dx: float = other_center.x() - my_center.x()
        dy: float = other_center.y() - my_center.y()
                
        self.entity.facing_left = (dx < 0)
                
        if self.entity.mod_manager.can_fly:
            self.entity.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
                
        self.entity._target_pos = None
        self.attack_time_left = 800 
        self.attack_cooldown = 2000 
        self.entity.anim_sys.set_state(EntityState.ATTACK)

    def _on_combat_check(self, other_pet: Entity) -> bool:
        if self.entity is None or self.entity.mod_manager is None: return False
        if not self.entity.mod_manager.custom_behavior: return False
        try:
            entity_api: IEntity = cast(IEntity, self.entity)
            other_entity_api: IEntity = cast(IEntity, other_pet)
            return self.entity.mod_manager.custom_behavior.on_attack(entity_api, other_entity_api)
        except Exception as e:
            print(f"Custom AI Error (Attack): {e}")
        return False
    
    def check_interactions(self, centers: Optional[dict[Entity, QPointF]] = None) -> None:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.mod_manager.behavior_type is BehaviorType.PASSIVE or
            self.entity.entity_manager is None
        ):
            return
        
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            return

        if not self.entity.is_interactable: return

        fallback_center: QPointF = self.entity.pos() + self.entity.current_hitbox.center()
        my_center: Optional[QPointF] = centers.get(self.entity) if centers else fallback_center

        for other_entity in self.entity.entity_manager.active_entities:
            if (
                other_entity.ai_sys is None or
                other_entity is self.entity or
                not other_entity.is_interactable
            ):
                continue

            other_fallback: QPointF = other_entity.pos() + other_entity.current_hitbox.center()
            other_center: Optional[QPointF] = centers.get(other_entity) if centers else other_fallback
            if other_center is None or my_center is None: continue
            distance: float = self._get_distance(my_center, other_center)

            if distance >= 120: return
            override_default: bool = self._on_check_interactions(other_entity)
            
            if not override_default:
                self.entity.facing_left = other_center.x() < my_center.x()
                other_entity.facing_left = my_center.x() < other_center.x()
                self.start_interaction()
                other_entity.ai_sys.start_interaction()
                
            break

    def _on_check_interactions(self, other_pet: Entity) -> bool:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.mod_manager.custom_behavior is None
        ):
            return False
        try:
            entity_api: IEntity = cast(IEntity, self.entity)
            other_entity_api: IEntity = cast(IEntity, other_pet)
            return self.entity.mod_manager.custom_behavior.on_interact(entity_api, other_entity_api)
        except Exception as e:
            print(f"Custom AI Error (Interact): {e}")
        return False

    def start_interaction(self) -> None:
        if self.entity is None or self.entity.anim_sys is None: return
        self.entity._target_pos = None
        self.interact_time_left = 3000 
        self.interaction_cooldown = 6000
        self.entity.anim_sys.set_state(EntityState.INTERACT)
    
    def _check_environment(self) -> bool:
        if (
            self.entity is None or
            self.entity.mod_manager is None or
            self.entity.entity_manager is None
        ):
            return False
        
        if self.entity.bubble is not None and self.entity.bubble.isVisible():
            return False
        
        if random.random() < 0.5: return False
            
        windows: List[str] = self.entity.entity_manager.active_window_titles
        
        for trigger in self.entity.mod_manager.window_triggers:
            matches: List[str] = trigger.get("title_matches", [])
            chance: float = trigger.get("chance", 1.0)
            
            if any(m.lower() in w.lower() for m in matches for w in windows):
                if random.random() < chance:
                    text: str = trigger.get("text", "...")
                    duration: int = trigger.get("duration", 4000)
                    self._trigger_dialogue(text, duration)
                    return True

        if random.random() < 0.05 and self.entity.mod_manager.plain_dialogue:
            text: str = random.choice(self.entity.mod_manager.plain_dialogue)
            self._trigger_dialogue(text, 3000)
            return True
            
        return False
        
    def _trigger_dialogue(self, text: str, duration_ms: int) -> None:
        if self.entity is None or self.entity.anim_sys is None: return
        if self.entity.bubble is None:
            self.entity.bubble = SpeechBubble(self.entity)
            
        self.entity.bubble.speak(text, duration_ms)
        self.entity.anim_sys.set_state(EntityState.IDLE)
        self.entity._target_pos = None
        self.entity.toFront()
    
    def process_combat(self) -> None:
        if (
            self.entity is None or
            self.entity.entity_manager is None or
            self.entity.mod_manager is None or
            self.entity.is_dead or
            self.entity.current_attack_hitbox.isEmpty()
        ):
            return

        # Translate using QRectF for floating-point precision
        global_attack_rect: QRectF = QRectF(self.entity.current_attack_hitbox).translated(self.entity.pos())
        targets: list[tuple[float, Entity]] = []
        
        for other_entity in self.entity.entity_manager.active_entities:
            if other_entity is self.entity or other_entity.is_dead: continue
                
            other_global_hitbox: QRectF = QRectF(other_entity.current_hitbox).translated(other_entity.pos())
            
            if global_attack_rect.intersects(other_global_hitbox):
                my_center: QPointF = global_attack_rect.center()
                other_center: QPointF = other_global_hitbox.center()
                dist: float = math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())
                targets.append((dist, other_entity))

        if not targets: return

        targets.sort(key=lambda t: t[0])
        valid_targets: list[Entity] = []
        attack_type: AttackType = self.entity.mod_manager.attack_type
        
        match attack_type:
            case AttackType.SINGLE:
                valid_targets.append(targets[0][1])
            case AttackType.AOE:
                valid_targets: list[Entity] = [t[1] for t in targets]
            case AttackType.MULTI:
                max_t: int = self.entity.mod_manager.max_targets
                valid_targets = [t[1] for t in targets[:max_t]]

        damage: int = self.entity.mod_manager.attack_damage
        for target in valid_targets:
            target.take_damage(damage)