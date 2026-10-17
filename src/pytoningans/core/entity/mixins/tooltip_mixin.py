from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast, Any

from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGraphicsSceneHoverEvent

from pytoningans.core.api import (
    IEntity, BaseEntityBehavior, BaseBehavior, BaseStructureBehavior, IStructure,
    BaseItemBehavior, IItem
)
from pytoningans.ui.tool_tip import CustomToolTipManager

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.entity.base_entity import BaseEntity


class EntityTooltipMixin:
    """Encapsulates hover detection, tooltip display, and identification naming for entities."""

    _instance_name: Optional[str]
    is_hovered: bool
    mod_manager: Optional[ModManager]

    def _entity(self) -> BaseEntity:
        return cast("BaseEntity", self)

    def _init_tooltip(self) -> None:
        self._instance_name = None
        self.is_hovered = False
        self._entity().setAcceptHoverEvents(True)
        self.update_tooltip()

    @property
    def instance_name(self) -> Optional[str]:
        return self._instance_name

    @instance_name.setter
    def instance_name(self, value: Optional[str]) -> None:
        self.set_instance_name(value)

    def set_instance_name(self, name: Optional[str]) -> None:
        """Sets a custom instance name for this entity and updates HUD and tooltip."""
        self._instance_name = name
        self.update_tooltip()
        self.on_instance_name_changed()
        if self.is_hovered:
            self._show_hover_tooltip(QCursor.pos())

    def on_instance_name_changed(self) -> None:
        """Hook for subclasses to react to instance name updates (e.g. updating HUD elements)."""
        pass

    @property
    def display_name(self) -> str:
        if self._instance_name:
            return self._instance_name
        if self.mod_manager is not None:
            if self.mod_manager.current_mod_name:
                return self.mod_manager.current_mod_name
            if self.mod_manager.current_mod_folder:
                return self.mod_manager.current_mod_folder
        return "Entity"

    @property
    def identification(self) -> str:
        """Formatted identification string for the entity: '<entity_type> from <mod_name>'."""
        type_str: str = "Entity"
        if self.mod_manager is not None and self.mod_manager.entity_type:
            type_str = str(self.mod_manager.entity_type).capitalize()
        else:
            cls_name: str = self.__class__.__name__
            if "Structure" in cls_name:
                type_str = "Structure"
            elif "Item" in cls_name:
                type_str = "Item"
            else:
                type_str = "Entity"

        mod_name: str = "Unknown"
        if self.mod_manager is not None:
            if self.mod_manager.current_mod_name:
                mod_name = self.mod_manager.current_mod_name
            elif self.mod_manager.current_mod_folder:
                mod_name = self.mod_manager.current_mod_folder

        return f'{type_str} from "{mod_name}"'

    def update_tooltip(self) -> None:
        """Updates the item tooltip to match its identification."""
        self._entity().setToolTip(self.identification)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_enter()
        self._show_hover_tooltip(event.screenPos())
        super().hoverEnterEvent(event)  # type: ignore[misc]

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if self.is_hovered:
            self._show_hover_tooltip(event.screenPos())
        super().hoverMoveEvent(event)  # type: ignore[misc]

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_leave()
        self._hide_hover_tooltip()
        super().hoverLeaveEvent(event)  # type: ignore[misc]

    def _show_hover_tooltip(self, screen_pos: QPoint) -> None:
        tip_text: str = self.identification
        if tip_text:
            CustomToolTipManager.get().show_tip(None, tip_text, screen_pos)

    def _hide_hover_tooltip(self) -> None:
        CustomToolTipManager.get().hide_tip()

    def on_hover_enter(self) -> None:
        """Hook called when the mouse cursor enters the entity's bounding area."""
        self.is_hovered = True
        self._on_hover_enter()

    def on_hover_leave(self) -> None:
        """Hook called when the mouse cursor leaves the entity's bounding area."""
        self.is_hovered = False
        self._on_hover_leave()

    def _on_hover_enter(self) -> None:
        behavior: Optional[BaseBehavior] = self._entity().behavior
        if behavior is None: return
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_hover_enter(cast(IEntity, self))
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_hover_enter(cast(IStructure, self))
            elif isinstance(behavior, BaseItemBehavior):
                behavior.on_hover_enter(cast(IItem, self))
        except Exception as e:
            print(f"Custom Behavior on_hover_enter Error: {e}")

    def _on_hover_leave(self) -> None:
        behavior: Optional[BaseBehavior] = self._entity().behavior
        if behavior is None: return
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_hover_leave(cast(IEntity, self))
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_hover_leave(cast(IStructure, self))
            elif isinstance(behavior, BaseItemBehavior):
                behavior.on_hover_leave(cast(IItem, self))
        except Exception as e:
            print(f"Custom Behavior on_hover_leave Error: {e}")
