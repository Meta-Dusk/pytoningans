import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QComboBox
)
from PySide6.QtCore import QModelIndex, QRect, Qt, Signal, QUrl
from PySide6.QtGui import QGuiApplication, QDesktopServices, QScreen, QResizeEvent

from pytoningans.core.mod_manager import ModManager
from pytoningans.core.constants import EntityType
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_creation_dialog import ModCreationDialog
from pytoningans.ui.mod_editor import ModEditorWindow
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.utils.assets import get_main_icon


class ModManagerHub(QWidget):
    mods_updated = Signal()
    
    def __init__(self, mod_manager: ModManager) -> None:
        super().__init__(
            windowTitle="Mod Manager Hub",
            windowIcon=get_main_icon()
        )
        self.mod_manager: ModManager = mod_manager
        self.editor_window: Optional[ModEditorWindow] = None
        self._current_sort_col: int = 1
        self._current_sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
        
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(720, 440)
        self.setMinimumSize(560, 320)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, "Mod Manager Hub")
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # --- Left Column: Search & Table ---
        table_layout = QVBoxLayout()
        table_layout.setSpacing(8)
        
        # Filter & Search Bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by name or folder...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", "all")
        self.type_filter.addItem("Entities Only", EntityType.ENTITY.value)
        self.type_filter.addItem("Structures Only", EntityType.STRUCTURE.value)
        self.type_filter.currentIndexChanged.connect(self._apply_filter)
        
        filter_layout.addWidget(self.search_input, stretch=2)
        filter_layout.addWidget(self.type_filter, stretch=1)
        table_layout.addLayout(filter_layout)
        
        # 3-Column Table
        self.mod_table = QTableWidget()
        self.mod_table.setColumnCount(3)
        self.mod_table.setHorizontalHeaderLabels(["Entity Type", "Entity Name", "Folder Name"])
        
        header = self.mod_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mod_table.setColumnWidth(2, 190)
        
        self.mod_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mod_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.mod_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mod_table.setAlternatingRowColors(True)
        self.mod_table.verticalHeader().setVisible(False)
        self.mod_table.setShowGrid(True)
        
        self.mod_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.mod_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        header.sortIndicatorChanged.connect(self._on_sort_changed)
        self.mod_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.mod_table.cellDoubleClicked.connect(lambda row, col: self._on_edit_clicked())
        
        table_layout.addWidget(self.mod_table)
        
        # Status footer
        self.status_label = QLabel("0 mods installed")
        self.status_label.setObjectName("HelperText")
        table_layout.addWidget(self.status_label)
        
        content_layout.addLayout(table_layout, stretch=3)
        
        # --- Right Column: Actions ---
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        actions_header = QLabel("Actions:")
        actions_header.setObjectName("SectionHeader")
        btn_layout.addWidget(actions_header)
        
        self.create_btn = QPushButton("Create New Mod")
        self.create_btn.setToolTip("Create a new custom entity or structure mod")
        self.create_btn.clicked.connect(self._on_create_clicked)
        btn_layout.addWidget(self.create_btn)
        
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.setToolTip("Open selected mod in Mod Editor")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_layout.addWidget(self.edit_btn)
        
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setToolTip("Open mod folder in File Explorer")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        btn_layout.addWidget(self.open_folder_btn)
        
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.setToolTip("Permanently remove selected mod folder")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout, stretch=1)
        
        main_layout.addWidget(content_widget)
        
        self.grip = CustomSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        
        self._center_window()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height()
        )

    def _center_window(self) -> None:
        screen: QScreen = QGuiApplication.primaryScreen()
        if not screen: return
        
        screen_geom: QRect = screen.availableGeometry()
        window_geom: QRect = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())

    def _get_selected_folder(self) -> Optional[str]:
        """Returns the folder name associated with the currently selected row."""
        selected_rows: list[QModelIndex] = self.mod_table.selectionModel().selectedRows()
        if selected_rows:
            row: int = selected_rows[0].row()
            item: Optional[QTableWidgetItem] = self.mod_table.item(row, 2)
            if item is not None:
                return item.data(Qt.ItemDataRole.UserRole) or item.text()
                
        row = self.mod_table.currentRow()
        if row >= 0:
            item = self.mod_table.item(row, 2)
            if item is not None:
                return item.data(Qt.ItemDataRole.UserRole) or item.text()
                
        return None

    def _select_folder(self, folder: str) -> None:
        """Selects the row matching the specified folder name."""
        for row in range(self.mod_table.rowCount()):
            item: Optional[QTableWidgetItem] = self.mod_table.item(row, 2)
            if item and (item.data(Qt.ItemDataRole.UserRole) == folder or item.text() == folder):
                self.mod_table.selectRow(row)
                break
        self._on_selection_changed()

    def _refresh_list(self) -> None:
        """Reloads mods from disk into the 3-column table, preserving sort & selection."""
        prev_selected: Optional[str] = self._get_selected_folder()
        
        self.mod_table.setSortingEnabled(False)
        self.mod_table.setRowCount(0)
        
        mods: dict[str, tuple[str, str]] = self.mod_manager.get_available_mods_with_type()
        self.mod_table.setRowCount(len(mods))
        
        for row, (folder, (name, entity_type)) in enumerate(mods.items()):
            type_item = QTableWidgetItem(entity_type.capitalize())
            type_item.setData(Qt.ItemDataRole.UserRole, entity_type.lower())
            
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            
            folder_item = QTableWidgetItem(folder)
            folder_item.setData(Qt.ItemDataRole.UserRole, folder)
            
            self.mod_table.setItem(row, 0, type_item)
            self.mod_table.setItem(row, 1, name_item)
            self.mod_table.setItem(row, 2, folder_item)
            
        self.mod_table.setSortingEnabled(True)
        self.mod_table.horizontalHeader().setSortIndicator(self._current_sort_col, self._current_sort_order)
        self.mod_table.sortItems(self._current_sort_col, self._current_sort_order)
        self._on_sort_changed(self._current_sort_col, self._current_sort_order)
            
        self._apply_filter()
        
        if prev_selected:
            self._select_folder(prev_selected)
        else:
            self._on_selection_changed()

    def _on_sort_changed(self, sort_col: int, order: Qt.SortOrder) -> None:
        """Updates header text with explicit direction indicators (A-Z / Z-A)."""
        if 0 <= sort_col < 3:
            self._current_sort_col = sort_col
            self._current_sort_order = order
            
        base_labels: list[str] = ["Entity Type", "Entity Name", "Folder Name"]
        for col, base in enumerate(base_labels):
            item: Optional[QTableWidgetItem] = self.mod_table.horizontalHeaderItem(col)
            if col == self._current_sort_col:
                direction_str: str = (
                    "\n▲ (A-Z)"
                    if self._current_sort_order == Qt.SortOrder.AscendingOrder else
                    "\n▼ (Z-A)"
                )
                text: str = f"{base}{direction_str}"
                tooltip: str = (
                    f"Sorted {('A to Z (Ascending)'
                    if self._current_sort_order == Qt.SortOrder.AscendingOrder else
                    'Z to A (Descending)')}. "
                    "Click to reverse sort direction."
                )
            else:
                text = base
                tooltip = f"Click to sort by {base} (A-Z)"
                
            if item:
                item.setText(text)
                item.setToolTip(tooltip)
            else:
                header_item = QTableWidgetItem(text)
                header_item.setToolTip(tooltip)
                self.mod_table.setHorizontalHeaderItem(col, header_item)

    def _apply_filter(self) -> None:
        """Filters table rows in real-time according to search query and type filter."""
        query: str = self.search_input.text().strip().lower()
        selected_type: str = self.type_filter.currentData() or "all"
        
        visible_count: int = 0
        total_count: int = self.mod_table.rowCount()
        
        for row in range(total_count):
            type_item: Optional[QTableWidgetItem] = self.mod_table.item(row, 0)
            name_item: Optional[QTableWidgetItem] = self.mod_table.item(row, 1)
            folder_item: Optional[QTableWidgetItem] = self.mod_table.item(row, 2)
            
            if (
                type_item is None or
                name_item is None or
                folder_item is None
            ):
                continue
                
            raw_type: str = str(type_item.data(Qt.ItemDataRole.UserRole) or type_item.text()).lower()
            matches_type: bool = (selected_type == "all" or raw_type == selected_type)
            
            name_text: str = name_item.text().lower()
            folder_text: str = folder_item.text().lower()
            matches_query: bool = (not query or query in name_text or query in folder_text or query in raw_type)
            
            show_row: bool = matches_type and matches_query
            self.mod_table.setRowHidden(row, not show_row)
            if show_row: visible_count += 1
                
        if query or selected_type != "all":
            self.status_label.setText(f"Showing {visible_count} of {total_count} mods")
        else:
            self.status_label.setText(f"{total_count} mods installed")
            
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        has_selection: bool = self._get_selected_folder() is not None
        self.edit_btn.setEnabled(has_selection)
        self.open_folder_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def _on_create_clicked(self) -> None:
        dialog = ModCreationDialog(self.mod_manager.mods_dir, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_list()
            self.mods_updated.emit()
            self._select_folder(dialog.new_mod_folder)
            self._open_editor(dialog.new_mod_folder)

    def _on_edit_clicked(self) -> None:
        selected_folder: Optional[str] = self._get_selected_folder()
        if selected_folder is None: return
        self._open_editor(selected_folder)

    def _open_editor(self, mod_folder: str) -> None:
        if self.editor_window is None or not self.editor_window.isVisible():
            self.editor_window = ModEditorWindow(self.mod_manager)
            self.editor_window.mods_updated.connect(self._on_editor_saved)
            self.editor_window.show()
        else:
            self.editor_window.activateWindow()
            
        idx: int = self.editor_window.mod_combo.findData(mod_folder)
        if idx >= 0:
            self.editor_window.mod_combo.setCurrentIndex(idx)

    def _on_delete_clicked(self) -> None:
        selected_folder: Optional[str] = self._get_selected_folder()
        if selected_folder is None: return
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to permanently delete the '{selected_folder}' "
            "mod?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            target_dir: Path = self.mod_manager.mods_dir / selected_folder
            try:
                shutil.rmtree(target_dir)
                self._refresh_list()
                self.mods_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete mod: {str(e)}")

    def _on_open_folder_clicked(self) -> None:
        selected_folder: Optional[str] = self._get_selected_folder()
        if selected_folder is None: return
        
        target_dir: Path = self.mod_manager.mods_dir / selected_folder
        if target_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir.resolve())))

    def _on_editor_saved(self) -> None:
        """Refreshes the hub's list when the editor saves, preserving selection."""
        selected_folder: Optional[str] = self._get_selected_folder()
        self._refresh_list()
        if selected_folder is not None:
            self._select_folder(selected_folder)
        self.mods_updated.emit()