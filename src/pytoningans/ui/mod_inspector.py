"""
PyToNingans Mod and Modpack Inspector Dialog
============================================
Interactive UI for inspecting mod files, reading Python/JSON sources, previewing spritesheets,
and viewing automated AST Security Scanner audit reports before running or enabling mods.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import re

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QTextCharFormat, QSyntaxHighlighter, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QWidget, QLabel, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QFrame, QTextBrowser
)

from pytoningans.core.mod_manager.security import (
    scan_mod_or_pack, SecurityReport, SecurityRiskLevel, SecuritySeverity,
)
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon
from pytoningans.utils.format import formatted_size


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code in the code viewer."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
            "or", "pass", "raise", "return", "try", "while", "with", "yield",
            "True", "False", "None", "self", "cls"
        ]
        for word in keywords:
            pattern = re.compile(rf"\b{word}\b")
            self._rules.append((pattern, keyword_format))

        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#8be9fd"))
        builtins = [
            "print", "len", "range", "enumerate", "zip", "map", "filter", "sorted",
            "list", "dict", "set", "tuple", "str", "int", "float", "bool", "bytes",
            "open", "isinstance", "issubclass", "hasattr", "getattr", "setattr",
            "super", "property", "staticmethod", "classmethod", "type", "object",
            "min", "max", "sum", "abs", "round", "pow", "divmod", "all", "any",
            "next", "iter", "reversed", "slice", "vars", "locals", "globals",
            "dir", "help", "id", "hash", "repr", "ascii", "format", "chr", "ord",
            "bin", "hex", "oct", "complex", "memoryview", "bytearray", "frozenset"
        ]
        for word in builtins:
            pattern = re.compile(rf"\b{word}\b")
            self._rules.append((pattern, builtin_format))

        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#f1fa8c"))
        self._rules.append((re.compile(r"@\w+"), decorator_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c"))
        self._rules.append((re.compile(r'""".*?"""', re.DOTALL), string_format))
        self._rules.append((re.compile(r"'''.*?'''", re.DOTALL), string_format))
        self._rules.append((re.compile(r'".*?"'), string_format))
        self._rules.append((re.compile(r"'.*?'"), string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4"))
        comment_format.setFontItalic(True)
        self._rules.append((re.compile(r"#.*"), comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#bd93f9"))
        self._rules.append((re.compile(r"\b\d+\.?\d*\b"), number_format))

        # Function definitions
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#50fa7b"))
        func_format.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"\bdef\s+(\w+)"), func_format))

        # Class definitions
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#50fa7b"))
        class_format.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"\bclass\s+(\w+)"), class_format))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


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
        self.resize(920, 620); self.setMinimumSize(750, 480)

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

        self.caps_browser = QTextBrowser()
        self.caps_browser.setStyleSheet(
            "background-color: #374151; color: #e5e7eb; border-radius: 4px; "
            "padding: 6px; font-size: 11px; line-height: 1.4; max-height: 100px;"
        )
        self.caps_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.caps_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.caps_browser)

        # Issues Table
        issues_header = QLabel("Audit Flags and Security Details:")
        issues_header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 6px;")
        layout.addWidget(issues_header)

        self.issues_table = QTableWidget(); self.issues_table.setColumnCount(4)
        self.issues_table.setHorizontalHeaderLabels(
            ["Severity", "Category", "Location", "Description"]
        )
        horizontalHeader = self.issues_table.horizontalHeader()
        for i in range(3):
            horizontalHeader.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
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
        self.preview_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_header)

        self.code_viewer = QPlainTextEdit(); self.code_viewer.setReadOnly(True)
        mono_font = QFont("Pixel Code", 10); mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_viewer.setFont(mono_font)
        # Enable syntax highlighting
        self._highlighter = PythonSyntaxHighlighter(self.code_viewer.document())
        layout.addWidget(self.code_viewer)

        self.image_viewer = QLabel()
        self.image_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_viewer.setVisible(False)
        layout.addWidget(self.image_viewer)

    def _populate_security_tab(self) -> None:
        risk: SecurityRiskLevel = self.report.risk_level
        match risk:
            case SecurityRiskLevel.SAFE:
                bg_color = "rgba(16, 185, 129, 0.15)"
                border_color = "#10b981"
                title_color = "#34d399"
                title_text = "AST SAFETY AUDIT: VERIFIED SAFE"
            case SecurityRiskLevel.LOW:
                bg_color = "rgba(59, 130, 246, 0.15)"
                border_color = "#3b82f6"
                title_color = "#60a5fa"
                title_text = "AST SAFETY AUDIT: LOW RISK (MINOR SYSTEM CALLS)"
            case SecurityRiskLevel.MEDIUM:
                bg_color = "rgba(245, 158, 11, 0.15)"
                border_color = "#f59e0b"
                title_color = "#fbbf24"
                title_text = "AST SAFETY AUDIT: WARNING (FILE / DYNAMIC OPERATIONS)"
            case _:
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

        #? Add capability text
        # Clear previous
        self.caps_browser.clear()

        if self.report.capabilities:
            caps_text = "  |  ".join(self.report.capabilities)
            self.caps_browser.setText(caps_text)
        else:
            self.caps_browser.setText("None detected (standard entity assets).")

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
        root_item = QTreeWidgetItem(self.file_tree, [self.target_dir.name + "/"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self.target_dir))
        root_item.setExpanded(True)

        # Build a set of file paths that have security issues, keyed by relative path
        self._issue_files: dict[str, SecuritySeverity] = {}
        for issue in self.report.issues:
            rel_path: str = issue.file
            # Keep the highest severity per file
            existing = self._issue_files.get(rel_path)
            if existing is None or issue.severity == SecuritySeverity.DANGER:
                self._issue_files[rel_path] = issue.severity

        def add_dir(dir_path: Path, parent_item: QTreeWidgetItem) -> None:
            for child in sorted(
                dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            ):
                if child.name.startswith(("_", ".")) or child.name == "__pycache__":
                    continue
                rel_path = str(child.relative_to(self.target_dir)).replace("\\", "/")
                display_name = child.name + ("/" if child.is_dir() else "")
                item = QTreeWidgetItem(parent_item, [display_name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(child))
                self._color_tree_item(item, child, rel_path)
                if child.is_dir():
                    item.setExpanded(True)
                    add_dir(child, item)

        add_dir(self.target_dir, root_item)

    def _color_tree_item(self, item: QTreeWidgetItem, file_path: Path, rel_path: str) -> None:
        """Apply color coding to tree items based on file type and security issues."""
        # Check security issues first (highest priority)
        if rel_path in self._issue_files:
            severity: SecuritySeverity = self._issue_files[rel_path]
            if severity == SecuritySeverity.DANGER:
                item.setForeground(0, Qt.GlobalColor.red)
            elif severity == SecuritySeverity.WARNING:
                item.setForeground(0, Qt.GlobalColor.yellow)
            else:
                item.setForeground(0, Qt.GlobalColor.cyan)
            return

        # Color by file type
        suffix: str = file_path.suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            # Spritesheets and images
            item.setForeground(0, Qt.GlobalColor.cyan)
        elif suffix == ".py":
            # Behavior scripts
            item.setForeground(0, Qt.GlobalColor.green)
        elif suffix in (".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"):
            # Config files (no special color)
            pass
        else:
            # Other/unexpected files
            item.setForeground(0, Qt.GlobalColor.darkYellow)

    def _on_file_selected(self, item: QTreeWidgetItem, column: int) -> None:
        file_path_str: Optional[str] = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path_str is None:
            return

        file_path = Path(file_path_str)
        if not file_path.is_file():
            return

        self.preview_header.setText(
            f"Viewing: {file_path.name} "
            f"({formatted_size(file_path.stat().st_size)})"
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
