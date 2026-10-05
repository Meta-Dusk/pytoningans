from dataclasses import dataclass, field, asdict
from typing import Any

from pytoningans.core.constants import (
    PetState, BehaviorType, AnimationMeta, AttackType, DeathAnimation
)

CURRENT_CONFIG_VERSION = 9

@dataclass
class BehaviorConfig:
    type: str = BehaviorType.NEUTRAL.value
    can_fly: bool = False
    max_health: int = 100
    attack_damage: int = 10
    attack_range: int = 50
    jump_height: int = 15
    attack_type: str = AttackType.SINGLE.value
    
    max_targets: int = 1
    """Used if `attack_type` is \"multi\""""
    
    death_animation: DeathAnimation = DeathAnimation.SPRITE
    auto_close_on_death: bool = False

@dataclass
class DialogueConfig:
    plain_dialogue: list[str] = field(
        default_factory=lambda: ["Just hanging out.", "Lovely weather.", "Need a break?"]
    )
    window_triggers: list[dict[str, Any]] = field(default_factory=lambda: [
        {
            "title_matches": ["secret_diary.txt", "diary - notepad", "diary"], 
            "text": "Are you writing about me?", 
            "duration": 4000, 
            "chance": 0.5
        },
        {
            "title_matches": ["visual studio code", "vscode", "code.exe"], 
            "text": "Writing bugs or features today?", 
            "duration": 4000, 
            "chance": 0.1
        }
    ])

@dataclass
class ModConfig:
    name: str
    version: int = CURRENT_CONFIG_VERSION
    columns: int = 4
    rows: int = len(PetState)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    animations: dict[str, AnimationMeta] = field(
        default_factory=lambda: {
            state.value: AnimationMeta(row=i, start_frame=0, end_frame=3) 
            for i, state in enumerate(PetState)
        }
    )
    dialogue: DialogueConfig = field(default_factory=DialogueConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)