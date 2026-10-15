import subprocess
from pathlib import Path
from PySide6.QtWidgets import QWidget, QFormLayout, QVBoxLayout, QPushButton

from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection

class BasePanel(QWidget):
    """Contains the shared methods of all Mod Editor Panels."""
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__()
        self.controller = controller
    
    def _setup_ui(self) -> None: ...
    def _connect_signals(self) -> None: ...
    def load_data(self) -> None: ...

class BaseBehaviorPanel(BasePanel):
    """Contains the shared methods of behavior panels specifically."""
    def __init__(
        self, controller: ModEditorController, *,
        section_name: str = "Custom Behavior", override: bool = False,
        boilerplate_script: str = ""
    ) -> None:
        """Simple setup for similar behavior panels.

        Args:
            controller (ModEditorController): The ModEditorController instance.
            section_name (str, optional): The section name. Defaults to "Custom Behavior".
            override (bool, optional): Set to True if you will override the build methods. Defaults to False.
            boilerplate_script (str, optional): The generated script on create. Defaults to "".
        """
        super().__init__(controller)
        if override: return
        self.boilerplate_script: str = boilerplate_script
        self.section_name: str = section_name
        
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.section = CollapsibleSection(self.section_name)
        form = QFormLayout()
        
        self.add_btn = QPushButton("Create Custom Behavior")
        self.edit_btn = QPushButton("Open in VS Code")
        self.delete_btn = QPushButton("Delete Script")
        
        form.addWidget(self.add_btn)
        form.addWidget(self.edit_btn)
        form.addWidget(self.delete_btn)
        
        self.section.content_layout.addLayout(form)
        layout.addWidget(self.section)
    
    def _connect_signals(self) -> None:
        self.add_btn.clicked.connect(self._create_script)
        self.edit_btn.clicked.connect(self._open_script)
        self.delete_btn.clicked.connect(self._delete_script)
    
    def load_data(self) -> None:
        exists: bool = self._get_script_path().exists()
        self.add_btn.setEnabled(not exists)
        self.edit_btn.setEnabled(exists)
        self.delete_btn.setEnabled(exists)
    
    def _get_script_path(self) -> Path:
        return self.controller.manager.current_mod_path / "behavior.py"
    
    def _open_script(self) -> None:
        path: Path = self._get_script_path()
        if not path.exists(): self._create_script()
        try:
            #? Cast Path objects to strings for the CLI arguments
            subprocess.Popen(['code', str(self.controller.manager.mods_dir), str(path)], shell=True)
        except Exception:
            #? os.startfile natively supports Path-like objects in Python 3.8+
            import os; os.startfile(path)
    
    def _create_script(self) -> None:
        path: Path = self._get_script_path()
        if path.exists(): return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.boilerplate_script)
        self.load_data()
    
    def _delete_script(self) -> None:
        path: Path = self._get_script_path()
        if not path.exists(): return
        path.unlink()
        self.load_data()
