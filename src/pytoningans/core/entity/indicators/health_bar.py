from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, cast, Any

from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics
from PySide6.QtCore import QRectF, Qt

from pytoningans.core.settings import SettingsManager, HealthBarMode

if TYPE_CHECKING:
    from pytoningans.core.entity.living_entity import Entity


class HealthBarItem(QGraphicsItem):
    """
    Overhead health bar attached to an Entity.\n
    **Features**:
    - Flashing ghost depletion bar (smoothly drains the subtracted health chunk).
    - Proportional screen shake on damage impact.
    - Centered numeric HP values (current / max).
    - Auto-hide on damage timer or persistent visibility based on settings.
    """
    def __init__(self, parent_entity: Entity) -> None:
        super().__init__(parent_entity)
        self.entity: Optional[Entity] = parent_entity
        self.setZValue(4.0)

        self.card_w: float = 64.0
        self.card_h: float = 27.0
        self.bar_w: float = 64.0
        self.bar_h: float = 27.0

        init_hp: float = float(parent_entity.current_health)
        self.current_hp: float = init_hp
        self.ghost_hp: float = init_hp

        # Feedback timers (ms)
        self.ghost_delay_left: int = 0
        self.flash_time_left: int = 0

        # Shake state
        self.shake_time_left: int = 0
        self.shake_duration: int = 0
        self.shake_amplitude: float = 0.0

        # Auto-hide and fade timers (ms)
        self.visibility_timer: int = 0
        self.fade_time_left: int = 0
        self.is_hovered: bool = False

        from pytoningans.core.settings import SettingsManager
        SettingsManager.get().settings_changed.connect(self.apply_settings)
        self._signals_connected: bool = True

        self.update_position()
        self.apply_settings()

    def set_hovered(self, hovered: bool) -> None:
        """Shows or fades out the health bar based on mouse cursor hover state."""
        self.is_hovered = hovered
        if self.entity is None:
            return
        if hovered:
            if not self.entity.is_dead:
                self.show()
                self.setOpacity(1.0)
                self.fade_time_left = 0
                self.update()
        else:
            settings = SettingsManager.get().settings
            if settings.health_bar_mode == HealthBarMode.ALWAYS.value and not self.entity.is_dead:
                pass
            elif self.visibility_timer > 0:
                pass
            else:
                self.fade_time_left = 350
            self.update()

    def detach_signals(self) -> None:
        if not getattr(self, "_signals_connected", False):
            return
        try:
            SettingsManager.get().settings_changed.disconnect(self.apply_settings)
        except Exception:
            pass
        finally:
            self._signals_connected = False

    def detach(self) -> None:
        """Tears down signals, scene attachment, and parent circular reference."""
        self.detach_signals()
        self.setParentItem(cast(Any, None))
        if self.scene():
            self.scene().removeItem(self)
        self.entity = None

    def apply_settings(self) -> None:
        if self.entity is None: return
        mode: str = SettingsManager.get().settings.health_bar_mode

        if mode == HealthBarMode.ALWAYS.value:
            if not self.entity.is_dead:
                self.show()
                self.setOpacity(1.0)
            else:
                self.hide()
        elif mode == HealthBarMode.HIDDEN.value:
            self.hide()
        elif mode == HealthBarMode.ON_DAMAGE.value:
            if self.visibility_timer <= 0 and self.fade_time_left <= 0:
                self.hide()
        self.update()

    def on_damage_taken(self, damage: int, new_hp: int, old_hp: int) -> None:
        if self.entity is None: return
        settings = SettingsManager.get().settings

        self.current_hp = float(max(0, new_hp))
        if self.ghost_hp < float(old_hp):
            self.ghost_hp = float(old_hp)

        self.ghost_delay_left = 220
        self.flash_time_left = 180

        # Proportional shake calculation
        max_hp: int = max(1, self.entity.mod_manager.max_health if self.entity.mod_manager else 100)
        dmg_ratio: float = max(0.05, min(1.0, damage / max_hp))
        self.shake_duration = int(180 + 220 * dmg_ratio)
        self.shake_time_left = self.shake_duration
        self.shake_amplitude = 2.0 + 6.0 * dmg_ratio

        if settings.health_bar_mode != HealthBarMode.HIDDEN.value:
            self.visibility_timer = settings.auto_hide_delay_ms
            self.fade_time_left = 0
            self.setOpacity(1.0)
            self.show()

        self.update()

    def on_heal(self, heal_amount: int, new_hp: int, old_hp: int) -> None:
        settings = SettingsManager.get().settings

        self.current_hp = float(new_hp)
        self.ghost_hp = float(new_hp)

        if settings.health_bar_mode != HealthBarMode.HIDDEN.value:
            self.visibility_timer = settings.auto_hide_delay_ms
            self.fade_time_left = 0
            self.setOpacity(1.0)
            self.show()

        self.update()

    def on_die(self) -> None:
        self.current_hp = 0.0
        self.hide()
        self.update()

    def on_revive(self) -> None:
        if self.entity is None:
            return
        max_hp: float = float(self.entity.mod_manager.max_health if self.entity.mod_manager else 100)
        self.current_hp = max_hp
        self.ghost_hp = max_hp
        self.apply_settings()
        self.update()

    def tick(self, dt: int) -> None:
        if self.entity is None: return
        settings = SettingsManager.get().settings
        needs_redraw: bool = False

        self.update_position()

        # Flash timer
        if self.flash_time_left > 0:
            self.flash_time_left -= dt
            needs_redraw = True

        # Ghost bar smooth depletion
        if self.ghost_delay_left > 0:
            self.ghost_delay_left -= dt
        if self.ghost_delay_left <= 0 and self.ghost_hp > self.current_hp:
            max_hp = max(1, self.entity.mod_manager.max_health if self.entity.mod_manager else 100)
            diff = self.ghost_hp - self.current_hp
            drain_rate = max(max_hp * 0.7, diff * 5.0)
            self.ghost_hp = max(self.current_hp, self.ghost_hp - drain_rate * (dt / 1000.0))
            needs_redraw = True

        # Shake timer
        if self.shake_time_left > 0:
            self.shake_time_left -= dt
            needs_redraw = True

        # Visibility handling
        if self.is_hovered and not self.entity.is_dead:
            if not self.isVisible():
                self.show()
            self.setOpacity(1.0)
            self.fade_time_left = 0
            needs_redraw = True
        elif settings.health_bar_mode == HealthBarMode.ALWAYS.value:
            if self.entity.is_dead:
                if self.isVisible():
                    self.hide()
            else:
                if not self.isVisible():
                    self.show()
                    self.setOpacity(1.0)
                    needs_redraw = True
        else:
            # ON_DAMAGE and HIDDEN modes
            if self.visibility_timer > 0:
                self.visibility_timer -= dt
                if self.visibility_timer <= 0:
                    self.fade_time_left = 400
            elif self.fade_time_left > 0:
                self.fade_time_left -= dt
                opacity = max(0.0, self.fade_time_left / 400.0)
                self.setOpacity(opacity)
                if self.fade_time_left <= 0:
                    self.hide()
                needs_redraw = True
            else:
                if self.isVisible():
                    self.hide()

        if needs_redraw:
            self.update()

    def update_position(self) -> None:
        if self.entity is None: return
        entity_w: float = self.entity.boundingRect().width()
        name_text: str = self.entity.instance_name or self.entity.display_name or "Entity"

        font = QFont("Pixel Code", 8)
        font.setBold(True)
        font_met = QFontMetrics(font)
        name_text_w: float = float(font_met.horizontalAdvance(name_text))

        card_w: float = max(64.0, min(entity_w * 0.9, 130.0), min(name_text_w + 14.0, 150.0))
        self.card_w = card_w
        self.card_h = 27.0
        self.bar_w = card_w
        self.bar_h = 27.0

        x: float = (entity_w - card_w) / 2.0
        y: float = -self.card_h - 4.0
        self.setPos(x, y)

    def boundingRect(self) -> QRectF:
        pad: float = 14.0
        return QRectF(-pad, -pad / 2.0, self.card_w + pad * 2.0, self.card_h + pad)

    def paint(
        self, painter: QPainter, _: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None
    ) -> None:
        if not self.isVisible() or self.opacity() <= 0.01 or self.entity is None:
            return

        settings = SettingsManager.get().settings

        # Proportional shake offset
        shake_x: float = 0.0
        if self.shake_time_left > 0 and settings.enable_health_shake:
            progress: float = 1.0 - (self.shake_time_left / max(1, self.shake_duration))
            damping: float = (1.0 - progress) ** 1.3
            shake_x = math.sin(progress * 35.0) * self.shake_amplitude * damping

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if shake_x != 0.0:
            painter.translate(shake_x, 0.0)

        w: float = self.card_w
        total_h: float = self.card_h
        radius: float = 4.0

        # Background container for HUD card
        card_rect = QRectF(0, 0, w, total_h)
        painter.setPen(QPen(QColor(40, 40, 40, 230), 1.2))
        painter.setBrush(QBrush(QColor(18, 18, 18, 225)))
        painter.drawRoundedRect(card_rect, radius, radius)

        #? Instance Name Text (Top row)
        name_text: str = self.entity.instance_name or self.entity.display_name or "Entity"
        name_font = QFont("Pixel Code", 8)
        name_font.setBold(True)
        painter.setFont(name_font)
        name_fm = QFontMetrics(name_font)
        elided_name = name_fm.elidedText(name_text, Qt.TextElideMode.ElideRight, int(w - 6))
        name_rect = QRectF(0, 2.0, w, 12.0)

        # Drop shadow + crisp white text
        painter.setPen(QPen(QColor(0, 0, 0, 220)))
        painter.drawText(name_rect.translated(0.8, 0.8), Qt.AlignmentFlag.AlignCenter, elided_name)
        painter.setPen(QPen(QColor(245, 245, 245, 255)))
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, elided_name)

        #? Health Bar Slot (Bottom row)
        bar_x: float = 3.0
        bar_y: float = 15.0
        bar_w: float = max(0.0, w - 6.0)
        bar_h: float = 9.0
        bar_rect = QRectF(bar_x, bar_y, bar_w, bar_h)

        # Inner bar trough
        painter.setPen(QPen(QColor(35, 35, 35, 240), 1.0))
        painter.setBrush(QBrush(QColor(10, 10, 10, 220)))
        painter.drawRoundedRect(bar_rect, 2.5, 2.5)

        inner_pad: float = 1.0
        inner_w: float = max(0.0, bar_w - (inner_pad * 2.0))
        inner_h: float = max(0.0, bar_h - (inner_pad * 2.0))
        max_hp: int = max(1, self.entity.mod_manager.max_health if self.entity.mod_manager else 100)

        # Ghost Depletion Bar (shows subtracted chunk flashing & smoothly draining)
        ghost_ratio: float = max(0.0, min(1.0, self.ghost_hp / max_hp))
        if ghost_ratio > 0:
            ghost_w = inner_w * ghost_ratio
            ghost_rect = QRectF(bar_x + inner_pad, bar_y + inner_pad, ghost_w, inner_h)
            if self.flash_time_left > 0:
                ghost_color = QColor(255, 245, 220, 240)
            else:
                ghost_color = QColor(220, 50, 47, 230)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ghost_color))
            painter.drawRoundedRect(ghost_rect, 2.0, 2.0)

        # Current Health Bar (immediate fill)
        cur_ratio: float = max(0.0, min(1.0, self.current_hp / max_hp))
        if cur_ratio > 0:
            cur_w = inner_w * cur_ratio
            cur_rect = QRectF(bar_x + inner_pad, bar_y + inner_pad, cur_w, inner_h)
            if cur_ratio > 0.5:
                hp_color = QColor(46, 204, 113)  # Healthy emerald
            elif cur_ratio > 0.25:
                hp_color = QColor(243, 156, 18)  # Warning amber
            else:
                hp_color = QColor(231, 76, 60)   # Critical red
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(hp_color))
            painter.drawRoundedRect(cur_rect, 2.0, 2.0)

        # Numerical Health Text (current / max)
        if settings.show_health_numbers:
            text: str = f"{int(self.current_hp)}/{max_hp}"
            font = QFont("Pixel Code", 7)
            font.setBold(True)
            painter.setFont(font)

            text_rect = bar_rect
            # Drop shadow
            painter.setPen(QPen(QColor(0, 0, 0, 220)))
            painter.drawText(text_rect.translated(0.8, 0.8), Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(QPen(QColor(255, 255, 255, 255)))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()


