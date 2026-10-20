"""
PyToNingans Mod and Modpack Inspector Dialog
=========================================
Interactive UI for inspecting mod files, reading Python/JSON sources, previewing spritesheets,
and viewing automated AST Security Scanner audit reports before running or enabling mods.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog, QLayoutItem, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QWidget, QLabel, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QFrame
)

from pytoningans.core.mod_manager.security import (
    scan_mod_or_pack, SecurityReport, SecurityRiskLevel,
)
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon


class ModInspectorDialog(QDialog):
    """Dialog allowing users to inspect files, code, and security audits of a mod/pack."""

    def __init__(self, target_dir: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.target_dir: Path = target_dir.resolve()
        self.report: SecurityReport = scan_mod_or_pack(self.target_dir)

        self.setWindowTitle(f"Inspect Mod - {self.report.target_name}")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(920, 620)
        self.setMinimumSize(750, 480)

        self._setup_ui()
        self._populate_file_tree()
        self._populate_security_tab()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(self, f"Mod Inspector: {self.report.target_name}")
        main_layout.addWidget(self.title_bar)

        # Content container
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12); content_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel: File Explorer Tree ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(6)

        tree_header = QLabel("Package Files:")
        tree_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(tree_header)

        self.file_tree = QTreeWidget(); self.file_tree.setHeaderHidden(True)
        self.file_tree.itemClicked.connect(self._on_file_selected)
        left_layout.addWidget(self.file_tree)

        splitter.addWidget(left_widget)

        # --- Right Panel: Tabs for Security Audit and File Preview ---
        self.tabs = QTabWidget()

        # Tab 1: Security Audit
        self.security_tab = QWidget()
        self._setup_security_tab_ui()
        self.tabs.addTab(self.security_tab, "Security and Safety Audit")

        # Tab 2: Code / Media Preview
        self.preview_tab = QWidget()
        self._setup_preview_tab_ui()
        self.tabs.addTab(self.preview_tab, "Source / File Preview")

        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 3)

        content_layout.addWidget(splitter)

        # Bottom actions
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        close_btn = QPushButton("Close"); close_btn.clicked.connect(self.close)
        bottom_bar.addWidget(close_btn)

        content_layout.addLayout(bottom_bar)
        main_layout.addWidget(content)

    def _setup_security_tab_ui(self) -> None:
        layout = QVBoxLayout(self.security_tab)
        layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(10)

        # Risk Banner
        self.risk_banner = QFrame()
        self.risk_banner.setFrameShape(QFrame.Shape.StyledPanel)
        banner_layout = QVBoxLayout(self.risk_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10); banner_layout.setSpacing(4)

        self.risk_title = QLabel("RISK LEVEL: SAFE")
        self.risk_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        banner_layout.addWidget(self.risk_title)

        self.risk_summary = QLabel(); self.risk_summary.setWordWrap(True)
        banner_layout.addWidget(self.risk_summary)

        layout.addWidget(self.risk_banner)

        # Capabilities Section
        caps_header = QLabel("Detected Capabilities:")
        caps_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 4px;")
        layout.addWidget(caps_header)

        self.caps_container = QWidget()
        self.caps_layout = QHBoxLayout(self.caps_container)
        self.caps_layout.setContentsMargins(0, 0, 0, 0); self.caps_layout.setSpacing(6)
        layout.addWidget(self.caps_container)

        # Issues Table
        issues_header = QLabel("Audit Flags and Security Details:")
        issues_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 6px;")
        layout.addWidget(issues_header)

        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(4)
        self.issues_table.setHorizontalHeaderLabels(
            ["Severity", "Category", "Location", "Description"]
        )
        horizontalHeader = self.issues_table.horizontalHeader()
        horizontalHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        horizontalHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        horizontalHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        horizontalHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.issues_table.verticalHeader().setVisible(False)
        self.issues_table.setAlternatingRowColors(True)
        self.issues_table.setShowGrid(True)
        layout.addWidget(self.issues_table)

    def _setup_preview_tab_ui(self) -> None:
        layout = QVBoxLayout(self.preview_tab)
        layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(6)

        self.preview_header = QLabel("Select a file from the list to view its contents.")
        self.preview_header.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.preview_header)

        self.code_viewer = QPlainTextEdit(); self.code_viewer.setReadOnly(True)
        mono_font = QFont("Consolas", 10); mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_viewer.setFont(mono_font)
        layout.addWidget(self.code_viewer)

        self.image_viewer = QLabel()
        self.image_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_viewer.setVisible(False)
        layout.addWidget(self.image_viewer)

    def _populate_security_tab(self) -> None:
        risk: SecurityRiskLevel = self.report.risk_level

        # Styling banner based on risk
        if risk == SecurityRiskLevel.SAFE:
            bg_color = "rgba(16, 185, 129, 0.15)"
            border_color = "#10b981"
            title_color = "#34d399"
            title_text = "AST SAFETY AUDIT: VERIFIED SAFE"
        elif risk == SecurityRiskLevel.LOW:
            bg_color = "rgba(59, 130, 246, 0.15)"
            border_color = "#3b82f6"
            title_color = "#60a5fa"
            title_text = "AST SAFETY AUDIT: LOW RISK (MINOR SYSTEM CALLS)"
        elif risk == SecurityRiskLevel.MEDIUM:
            bg_color = "rgba(245, 158, 11, 0.15)"
            border_color = "#f59e0b"
            title_color = "#fbbf24"
            title_text = "AST SAFETY AUDIT: WARNING (FILE / DYNAMIC OPERATIONS)"
        else:
            bg_color = "rgba(239, 68, 68, 0.2)"
            border_color = "#ef4444"
            title_color = "#f87171"
            title_text = "AST SAFETY AUDIT: DANGER (POTENTIAL MALICIOUS CODE)"

        self.risk_banner.setStyleSheet(
            f"background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px;"
        )
        self.risk_title.setText(title_text)
        self.risk_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {title_color};")
        self.risk_summary.setText(f"{self.report.summary}\n{self.report.detailed_explanation}")

        # Add capability chips
        # Clear previous
        while self.caps_layout.count():
            item: Optional[QLayoutItem] = self.caps_layout.takeAt(0)
            if item is None: continue
            widget: Optional[QWidget] = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self.report.capabilities:
            for capability in self.report.capabilities:
                chip = QLabel(f" {capability} ")
                chip.setStyleSheet(
                    "background-color: #374151; color: #e5e7eb; border-radius: 4px; "
                    "padding: 3px 6px; font-size: 11px; font-weight: 500;"
                )
                self.caps_layout.addWidget(chip)
        else:
            empty_lbl = QLabel("None detected (standard entity assets).")
            empty_lbl.setStyleSheet("color: gray; font-style: italic;")
            self.caps_layout.addWidget(empty_lbl)
        self.caps_layout.addStretch()

        # Populate Issues Table
        self.issues_table.setRowCount(len(self.report.issues))
        for row, issue in enumerate(self.report.issues):
            severity_item = QTableWidgetItem(issue.severity.upper())
            if issue.severity == "danger":
                severity_item.setForeground(Qt.GlobalColor.red)
            elif issue.severity == "warning":
                severity_item.setForeground(Qt.GlobalColor.yellow)
            else:
                severity_item.setForeground(Qt.GlobalColor.cyan)

            category_item = QTableWidgetItem(issue.category.replace("_", " ").title())
            location_item = QTableWidgetItem(f"{issue.file}:{issue.line}")
            description_text = issue.description
            if issue.code_snippet:
                description_text += f" | Code: `{issue.code_snippet}`"
            description_item = QTableWidgetItem(description_text)

            self.issues_table.setItem(row, 0, severity_item)
            self.issues_table.setItem(row, 1, category_item)
            self.issues_table.setItem(row, 2, location_item)
            self.issues_table.setItem(row, 3, description_item)

    def _populate_file_tree(self) -> None:
        self.file_tree.clear()
        root_item = QTreeWidgetItem(self.file_tree, [self.target_dir.name])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self.target_dir))
        root_item.setExpanded(True)

        def add_dir(dir_path: Path, parent_item: QTreeWidgetItem) -> None:
            for child in sorted(
                dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            ):
                if child.name.startswith(("_", ".")) or child.name == "__pycache__":
                    continue
                item = QTreeWidgetItem(parent_item, [child.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(child))
                if child.is_dir():
                    item.setExpanded(True)
                    add_dir(child, item)

        add_dir(self.target_dir, root_item)

    def _on_file_selected(self, item: QTreeWidgetItem, column: int) -> None:
        file_path_str: Optional[str] = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path_str:
            return

        file_path = Path(file_path_str)
        if not file_path.is_file():
            return

        self.preview_header.setText(
            f"Viewing: {file_path.name} ({file_path.stat().st_size} bytes)"
        )

        # Handle images
        if file_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                self.code_viewer.setVisible(False)
                self.image_viewer.setVisible(True)
                scaled: QPixmap = pixmap.scaled(
                    QSize(500, 350),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_viewer.setPixmap(scaled)
                self.tabs.setCurrentWidget(self.preview_tab)
                return

        # Handle text/code files
        self.image_viewer.setVisible(False)
        self.code_viewer.setVisible(True)
        try:
            content: str = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding="latin-1")
            except Exception as e:
                content = f"[Could not read file contents: {e}]"

        self.code_viewer.setPlainText(content)
        self.tabs.setCurrentWidget(self.preview_tab)

