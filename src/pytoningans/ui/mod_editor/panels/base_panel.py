from PySide6.QtWidgets import QWidget

from pytoningans.ui.mod_editor.controller import ModEditorController

class BasePanel(QWidget):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__()
        self.controller = controller
    
    def _setup_ui(self) -> None:
        ...
    
    def _connect_signals(self) -> None:
        ...
    
    def load_data(self) -> None:
        ...