from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF

from pytoningans.core.constants import EntityState
from .combat import check_combat as _do_check_combat
from .combat import default_combat_logic as _do_default_combat_logic
from .combat import get_distance as _do_get_distance
from .combat import on_combat_check as _do_on_combat_check
from .combat import process_combat as _do_process_combat
from .decision import ai_decision_tick as _do_ai_decision_tick
from .decision import default_ai_decision as _do_default_ai_decision
from .decision import on_ai_decision_tick as _do_on_ai_decision_tick
from .environment import check_environment as _do_check_environment
from .environment import trigger_dialogue as _do_trigger_dialogue
from .interaction import check_interactions as _do_check_interactions
from .interaction import on_check_interactions as _do_on_check_interactions
from .interaction import start_interaction as _do_start_interaction
from .item_seeking import check_item_seeking as _do_check_item_seeking
from .item_seeking import default_survival_seeking as _do_default_survival_seeking
from .item_seeking import navigate_towards_item as _do_navigate_towards_item

if TYPE_CHECKING:
    from pytoningans.core.api import IItem
    from pytoningans.core.entity.living_entity import Entity


class AISystem:
    """Core AI decision and behavior coordinator for living entities."""

    def __init__(self, entity: Optional[Entity] = None) -> None:
        self.entity: Optional[Entity] = entity

        self.decision_accumulator: int = 0

        self.interact_time_left: int = 0
        self.interaction_cooldown: int = 0

        self.attack_time_left: int = 0
        self.attack_cooldown: int = 0

    def update(self, dt: int) -> None:
        """Main update tick called every frame by the entity."""
        if self.entity is None or self.entity.anim_sys is None:
            return
        self.decision_accumulator += dt

        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        if self.entity.state == EntityState.INTERACT:
            self.interact_time_left -= dt
            if self.interact_time_left <= 0:
                self.entity.anim_sys.set_state(EntityState.IDLE)
            return

        if self.entity.state == EntityState.ATTACK:
            self.attack_time_left -= dt
            if self.attack_time_left <= 0:
                self.entity.anim_sys.set_state(EntityState.IDLE)
            return

        if self.decision_accumulator >= 2500:
            self.decision_accumulator = 0
            if self._check_environment():
                return
            self._ai_decision_tick()

        self.check_combat()

        if self.entity.state != EntityState.ATTACK:
            self.check_interactions()

    # --- Combat API ---

    def check_combat(self) -> None:
        """Checks for combat targets and initiates attacks."""
        _do_check_combat(self)

    def process_combat(self) -> None:
        """Processes attack frame impact and damage dealing."""
        _do_process_combat(self)

    def _default_combat_logic(self, my_center: QPointF, other_center: QPointF) -> None:
        _do_default_combat_logic(self, my_center, other_center)

    def _on_combat_check(self, other_entity: Entity) -> bool:
        return _do_on_combat_check(self, other_entity)

    def _get_distance(self, my_center: QPointF, other_center: QPointF) -> float:
        return _do_get_distance(my_center, other_center)

    # --- Interaction API ---

    def check_interactions(self, centers: Optional[dict[Entity, QPointF]] = None) -> None:
        """Checks proximity to other entities for social interactions."""
        _do_check_interactions(self, centers)

    def start_interaction(self) -> None:
        """Starts social interaction state."""
        _do_start_interaction(self)

    def _on_check_interactions(self, other_entity: Entity) -> bool:
        return _do_on_check_interactions(self, other_entity)

    # --- Decision & Wandering API ---

    def _ai_decision_tick(self) -> None:
        _do_ai_decision_tick(self)

    def _on_ai_decision_tick(self) -> bool:
        return _do_on_ai_decision_tick(self)

    def _default_ai_decision(self) -> None:
        _do_default_ai_decision(self)

    # --- Item Seeking API ---

    def _check_item_seeking(self) -> bool:
        return _do_check_item_seeking(self)

    def _default_survival_seeking(self, ground_items: list[IItem]) -> bool:
        return _do_default_survival_seeking(self, ground_items)

    def _navigate_towards_item(self, item: IItem) -> None:
        _do_navigate_towards_item(self, item)

    # --- Environment API ---

    def _check_environment(self) -> bool:
        return _do_check_environment(self)

    def _trigger_dialogue(self, text: str, duration_ms: int) -> None:
        _do_trigger_dialogue(self, text, duration_ms)

