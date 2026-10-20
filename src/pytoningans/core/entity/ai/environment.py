from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from .system import AISystem
    from pytoningans.core.entity.living_entity import Entity


def check_environment(ai: AISystem) -> bool:
    """Checks open window titles or idle dialogue opportunities to trigger speech."""
    entity: Optional[Entity] = ai.entity
    if (
        entity is None or
        entity.mod_manager is None or
        entity.entity_manager is None
    ):
        return False
    
    if entity.bubble is not None and entity.bubble.isVisible():
        return False
    
    if random.random() < 0.5:
        return False
        
    windows: list[str] = entity.entity_manager.active_window_titles
    
    for trigger in entity.mod_manager.window_triggers:
        matches: list[str] = trigger.get("title_matches", [])
        chance: float = trigger.get("chance", 1.0)
        
        if any(m.lower() in w.lower() for m in matches for w in windows):
            if random.random() < chance:
                text: str = trigger.get("text", "...")
                duration: int = trigger.get("duration", 4000)
                trigger_dialogue(ai, text, duration)
                return True

    if random.random() < 0.05 and entity.mod_manager.plain_dialogue:
        text: str = random.choice(entity.mod_manager.plain_dialogue)
        trigger_dialogue(ai, text, 3000)
        return True
        
    return False


def trigger_dialogue(ai: AISystem, text: str, duration_ms: int) -> None:
    """Causes the entity to speak a dialogue line and return to idle."""
    entity: Optional[Entity] = ai.entity
    if entity is None or entity.anim_sys is None:
        return
    entity.say(text, duration_ms)
    entity.anim_sys.set_state(EntityState.IDLE)
    entity.target_pos = None
    entity.toFront()

