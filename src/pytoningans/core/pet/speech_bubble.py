from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer

class SpeechBubble(QWidget):
    def __init__(self, parent_pet) -> None:
        super().__init__()
        self.pet = parent_pet
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("")
        self.label.setObjectName("SpeechBubbleLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def speak(self, text: str, duration_ms: int = 4000) -> None:
        self.label.setText(text)
        self.adjustSize()
        self.update_position()
        self.show()
        self.raise_()
        self.hide_timer.start(duration_ms)

    def update_position(self) -> None:
        if not self.isVisible(): return
        # Anchor the bubble centered above the pet's head
        pet_geom = self.pet.geometry()
        x = pet_geom.center().x() - (self.width() // 2)
        y = pet_geom.top() - self.height() - 10
        self.move(x, y)