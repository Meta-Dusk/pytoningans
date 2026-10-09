from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity

class BaseComponent:
    """Foundational class for all entity and structure components."""
    name: str = "base"

    def __init__(self, owner: Optional[BaseEntity] = None) -> None:
        self.owner: Optional[BaseEntity] = owner
        self.enabled: bool = True

    def on_attach(self) -> None:
        """Invoked when attached to an entity."""
        pass

    def update(self, dt: int) -> None:
        """Invoked on every frame/tick."""
        pass

    def on_detach(self) -> None:
        """Invoked when removed from an entity or when the entity is destroyed."""
        pass