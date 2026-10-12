LIGHT_THEME = """
QWidget {
    background-color: #f9f9f9;
    color: #1e1e1e;
    font-family: 'Pixel Code', monospace;
    font-size: 14px;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f0f0f0;
    border: 1px solid #0078d4;
}

QPushButton:pressed {
    background-color: #e5e5e5;
}

QComboBox, QSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 4px 8px;
}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #0078d4;
}

QLineEdit:focus {
    border: 1px solid #0078d4;
}

QCheckBox {
    color: #1e1e1e;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border: 1px solid #0078d4;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border: 1px solid #0078d4;
}

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f7f7f7;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    gridline-color: #f0f0f0;
    selection-background-color: #e3f2fd;
    selection-color: #0d47a1;
}

QTableWidget::item {
    padding: 5px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #e3f2fd;
    color: #0d47a1;
}

QHeaderView::section {
    background-color: #f0f0f0;
    color: #333333;
    font-weight: bold;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #dcdcdc;
    border-bottom: 1px solid #dcdcdc;
}

QHeaderView::section:hover {
    background-color: #e5e5e5;
}

QLabel {
    color: #1e1e1e;
    background: transparent;
    border: none;
}

QLabel#HelperText {
    color: #666666;
    font-style: italic;
}

QLabel#BannerText {
    font-weight: bold; 
    color: #444444; 
    background-color: #eeeeee; 
    padding: 5px;
}

QLabel#PreviewTitle {
    font-weight: bold; 
    color: #666666;
}

QLabel#ToolTipText {
    color: #1e1e1e;
    font-size: 12px;
}

QWidget#ToolTipLabel {
    background-color: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
}

QWidget#CustomTitleBar {
    background-color: #e5e5e5;
    border: 1px solid #b0b0b0;
}

QLabel#TitleBarText {
    color: #1e1e1e;
    font-weight: bold; 
}

QLabel#TitleBarVersion {
    color: #666666;
    font-size: 11px;
    font-weight: normal;
    padding-left: 2px;
}

QPushButton#TitleBarBtn { 
    background: transparent; 
    border: none; 
    color: #666666; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}

QPushButton#TitleBarBtn:hover { 
    color: black; 
}

QPushButton#TitleBarCloseBtn { 
    background: transparent; 
    border: none; 
    color: #666666; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}

QPushButton#TitleBarCloseBtn:hover { 
    background-color: #e81123; 
    color: white; 
}

QLabel#SectionHeader {
    font-weight: bold;
    color: #333333;
    font-size: 14px;
}

QFrame#MenuSeparator {
    border: none;
    border-top: 1px solid #d1d1d1;
    max-height: 1px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 4px 0px;
}
QMenu::item {
    padding: 6px 24px;
    color: #1e1e1e;
}
QMenu::item:selected {
    background-color: #f0f0f0;
    color: #0078d4;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    border: 1px solid #e5e5e5;
    color: #a0a0a0;
}

#SpeechBubbleLabel {
    background-color: #FFFFFF;
    color: #000000;
    border: 2px solid #333333;
    border-radius: 8px;
    padding: 8px;
    font-family: 'Pixel Code', monospace;
    font-size: 14px;
}

QFrame#ActionRow {
    background-color: #f2f2f2;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
}

QPushButton#RowBtn {
    padding: 3px 10px;
    font-size: 12px;
}

QLabel#StatAliveLabel {
    color: #2e7d32;
    font-weight: bold;
    font-size: 13px;
}

QLabel#StatDeadLabel {
    color: #c62828;
    font-weight: bold;
    font-size: 13px;
}

QLabel#StatStructLabel {
    color: #1565c0;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#DangerBtn {
    background-color: #ffffff;
    border: 1px solid #f5c2c7;
    color: #c62828;
    font-weight: 500;
}

QPushButton#DangerBtn:hover {
    background-color: #dc3545;
    border: 1px solid #dc3545;
    color: #ffffff;
}

QPushButton#DangerBtn:pressed {
    background-color: #b02a37;
}

QPushButton#DangerBtn:disabled {
    background-color: #f5f5f5;
    border: 1px solid #e5e5e5;
    color: #a0a0a0;
}
"""

DARK_THEME = """
QWidget {
    background-color: #202020;
    color: #f3f3f3;
    font-family: 'Pixel Code', monospace;
    font-size: 14px;
}

QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383838;
    border: 1px solid #4a90e2;
}

QPushButton:pressed {
    background-color: #1e1e1e;
}

QComboBox, QSpinBox, QLineEdit {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 8px;
}

QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #4a90e2;
}

QLineEdit:focus {
    border: 1px solid #4a90e2;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4d4d4d;
    border-radius: 4px;
    background-color: #252526;
}

QCheckBox::indicator:hover {
    border: 1px solid #4a90e2;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border: 1px solid #0078d4;
}

QTableWidget {
    background-color: #252525;
    alternate-background-color: #2a2a2a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    gridline-color: #333333;
    selection-background-color: #1e3a5f;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 5px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #1e3a5f;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #2d2d2d;
    color: #e0e0e0;
    font-weight: bold;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #3d3d3d;
    border-bottom: 1px solid #3d3d3d;
}

QHeaderView::section:hover {
    background-color: #383838;
}

QLabel {
    color: #f3f3f3;
    background: transparent;
    border: none;
}

QLabel#HelperText {
    color: #aaaaaa;
    font-style: italic;
}

QLabel#BannerText {
    font-weight: bold; 
    color: #e0e0e0; 
    background-color: #333333; 
    padding: 5px;
}

QLabel#PreviewTitle {
    font-weight: bold; 
    color: #aaaaaa;
}

QLabel#ToolTipText {
    color: #f3f3f3;
    font-size: 12px;
}

QWidget#ToolTipLabel {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
}

QWidget#CustomTitleBar {
    background-color: #1a1a1a;
    border: 1px solid #4a4a4a;
}

QLabel#TitleBarText {
    color: #f3f3f3;
    font-weight: bold; 
}

QLabel#TitleBarVersion {
    color: #888888;
    font-size: 11px;
    font-weight: normal;
    padding-left: 2px;
}

QPushButton#TitleBarBtn { 
    background: transparent; 
    border: none; 
    color: #aaaaaa; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}

QPushButton#TitleBarBtn:hover { 
    color: white; 
}

QPushButton#TitleBarCloseBtn { 
    background: transparent; 
    border: none; 
    color: #aaaaaa; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}

QPushButton#TitleBarCloseBtn:hover { 
    background-color: #e81123; 
    color: white; 
}

QLabel#SectionHeader {
    font-weight: bold;
    color: #cccccc;
    font-size: 14px;
}

QFrame#MenuSeparator {
    border: none;
    border-top: 1px solid #3d3d3d;
    max-height: 1px;
}

QMenu {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 0px;
}
QMenu::item {
    padding: 6px 24px;
    color: #f3f3f3;
}
QMenu::item:selected {
    background-color: #383838;
    color: #4a90e2;
}

QPushButton:disabled {
    background-color: #222222;
    border: 1px solid #2a2a2a;
    color: #666666;
}

#SpeechBubbleLabel {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 2px solid #555555;
    border-radius: 8px;
    padding: 8px;
    font-family: 'Pixel Code', monospace;
    font-size: 14px;
}

QFrame#ActionRow {
    background-color: #262626;
    border: 1px solid #363636;
    border-radius: 6px;
}

QPushButton#RowBtn {
    padding: 3px 10px;
    font-size: 12px;
}

QLabel#StatAliveLabel {
    color: #4caf50;
    font-weight: bold;
    font-size: 13px;
}

QLabel#StatDeadLabel {
    color: #ef5350;
    font-weight: bold;
    font-size: 13px;
}

QLabel#StatStructLabel {
    color: #42a5f5;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#DangerBtn {
    background-color: #2d2020;
    border: 1px solid #4d2d2d;
    color: #ef5350;
    font-weight: 500;
}

QPushButton#DangerBtn:hover {
    background-color: #e53935;
    border: 1px solid #e53935;
    color: #ffffff;
}

QPushButton#DangerBtn:pressed {
    background-color: #b71c1c;
}

QPushButton#DangerBtn:disabled {
    background-color: #222222;
    border: 1px solid #2a2a2a;
    color: #666666;
}
"""