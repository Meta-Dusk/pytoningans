from PySide6.QtWidgets import (
    QSpinBox, QFormLayout, QDialog, QLineEdit, QDoubleSpinBox, QDialogButtonBox
)

class TriggerDialog(QDialog):
    """A custom popup form to gather all window trigger variables."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Window Trigger")
        layout = QFormLayout(self)
        
        self.text_input = QLineEdit()
        
        self.matches_input = QLineEdit()
        self.matches_input.setPlaceholderText("vscode, code.exe, visual studio")
        
        self.chance_spin = QDoubleSpinBox()
        self.chance_spin.setRange(0.01, 1.0)
        self.chance_spin.setSingleStep(0.1)
        self.chance_spin.setValue(0.5)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(500, 20000)
        self.duration_spin.setValue(4000)
        
        layout.addRow("Spoken Text:", self.text_input)
        layout.addRow("Window Matches (comma-separated):", self.matches_input)
        layout.addRow("Trigger Chance (0.01 to 1.0):", self.chance_spin)
        layout.addRow("Duration (ms):", self.duration_spin)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> dict:
        # Clean up the comma-separated string into a proper list
        matches = [m.strip() for m in self.matches_input.text().split(",") if m.strip()]
        return {
            "text": self.text_input.text().strip(),
            "title_matches": matches,
            "chance": self.chance_spin.value(),
            "duration": self.duration_spin.value()
        }
    
    def set_data(self, data: dict) -> None:
        """Pre-fills the form fields for editing an existing trigger."""
        self.text_input.setText(data.get("text", ""))
        
        matches = data.get("title_matches", [])
        self.matches_input.setText(", ".join(matches))
        
        self.chance_spin.setValue(data.get("chance", 1.0))
        self.duration_spin.setValue(data.get("duration", 4000))