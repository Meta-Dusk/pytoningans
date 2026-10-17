from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from pytoningans.core.components.base_component import BaseComponent

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


class EntityComponentMixin:
    """Encapsulates component management and lifecycle dispatching for entities."""

    components: dict[str, BaseComponent]

    def _init_components(self) -> None:
        self.components = {}

    def add_component(self, component: BaseComponent) -> BaseComponent:
        """Attaches a component to the entity, setting its owner and firing on_attach."""
        component.owner = cast("BaseEntity", self)
        self.components[component.name] = component
        component.on_attach()
        return component

    def get_component(self, name: str) -> Optional[BaseComponent]:
        """Returns the attached component matching the given name, if present."""
        return self.components.get(name)

    def has_component(self, name: str) -> bool:
        """Returns True if a component with the specified name is attached."""
        return name in self.components

    def remove_component(self, name: str) -> Optional[BaseComponent]:
        """Detaches and cleans up a component from the entity."""
        comp: Optional[BaseComponent] = self.components.pop(name, None)
        if comp is not None:
            comp.on_detach()
            comp.owner = None
        return comp

    def _update_components(self, dt: int) -> None:
        """Dispatches ticks to all active attached components."""
        for comp in list(self.components.values()):
            if not comp.enabled: continue
            comp.update(dt)

    def _destroy_components(self) -> None:
        """Detaches and cleans up all components upon entity destruction."""
        for comp in list(self.components.values()):
            comp.on_detach()
            comp.owner = None
        self.components.clear()

