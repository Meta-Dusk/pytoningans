"""Core entity definitions and subsystems."""

from __future__ import annotations

from .ai import AISystem
from .animation import AnimationSystem
from .physics import PhysicsSystem
from .base_entity import BaseEntity
from .base_structure import BaseStructure
from .base_item import BaseItem
from .speech_bubble import SpeechBubble
from pytoningans.ui.context_menu import EntityContextMenu
from .living_entity import Entity

__all__ = [
    # Systems
    "AISystem",
    "AnimationSystem",
    "PhysicsSystem",
    
    # Base Classes
    "BaseEntity",
    "BaseStructure",
    "BaseItem",
    
    # Entity Widgets
    "SpeechBubble",
    "EntityContextMenu",
    
    # Entity Types
    "Entity",
]
