import sys

from PySide6.QtCore import QEvent, Qt, QPoint
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QHBoxLayout
from typing import Optional

class CustomToolTip(QWidget):
    """A completely customized overlay widget acting as a modern tooltip."""
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Custom layout and design
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Add components (e.g., an icon or specific text styles)
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #FFFFFF; font-family: 'Segoe UI'; font-size: 12px;")
        layout.addWidget(self.label)
        
        # Main background container style
        self.setStyleSheet("""
            QWidget {
                background-color: #2C3E50;
                border: 1px solid #34495E;
                border-radius: 6px;
            }
        """)
# TODO: Implement custom label for hint tool tips
# class IconLabel(QLabel):
#     """A label for showing custom tool tips."""
#     def __init__(self, /, parent: QWidget | None = ..., f: Qt.WindowType = ..., *, text: str | None = ..., textFormat: Qt.TextFormat | None = ..., pixmap: QPixmap | None = ..., scaledContents: bool | None = ..., alignment: Qt.AlignmentFlag | None = ..., wordWrap: bool | None = ..., margin: int | None = ..., indent: int | None = ..., openExternalLinks: bool | None = ..., textInteractionFlags: Qt.TextInteractionFlag | None = ..., hasSelectedText: bool | None = ..., selectedText: str | None = ...) -> None:
#         super().__init__(parent, f, text=text, textFormat=textFormat, pixmap=pixmap, scaledContents=scaledContents, alignment=alignment, wordWrap=wordWrap, margin=margin, indent=indent, openExternalLinks=openExternalLinks, textInteractionFlags=textInteractionFlags, hasSelectedText=hasSelectedText, selectedText=selectedText)

class CustomButton(QPushButton):
    def __init__(self, text, tooltip_text, parent=None):
        super().__init__(text, parent)
        self.tooltip_text = tooltip_text
        self.custom_tooltip = None

    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            if not self.custom_tooltip:
                self.custom_tooltip = CustomToolTip(self.tooltip_text)
            
            # Position the custom tooltip just below the cursor
            self.custom_tooltip.move(self.mapToGlobal(QPoint(0, self.height() + 5)))
            self.custom_tooltip.show()
            return True
            
        elif event.type() == QEvent.Type.Leave:
            if self.custom_tooltip:
                self.custom_tooltip.hide()
                
        return super().event(event)

# Execution block
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.resize(300, 200)
    layout = QVBoxLayout(window)
    
    btn = CustomButton("Hover Over Me", "This is a fully custom widget tooltip! 🚀")
    layout.addWidget(btn)
    
    window.show()
    sys.exit(app.exec())
