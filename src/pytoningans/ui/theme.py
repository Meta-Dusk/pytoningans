LIGHT_THEME = """
QWidget {
    background-color: #f9f9f9;
    color: #1e1e1e;
    font-family: 'Adapa', -apple-system, sans-serif;
    font-size: 20px;
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

QComboBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 4px 8px;
}

QComboBox:hover, QSpinBox:hover {
    border: 1px solid #0078d4;
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
    font-size: 17px;
}

QWidget#ToolTipLabel {
    background-color: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
}

QWidget#CustomTitleBar {
    background-color: #e5e5e5;
    border-bottom: 1px solid #d1d1d1; 
}

QLabel#TitleBarText {
    color: #1e1e1e;
    font-weight: bold; 
}

QPushButton#TitleBarCloseBtn { 
    background: transparent; 
    border: none; 
    color: #666666; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 16px; 
    font-family: 'Adapa', -apple-system, sans-serif;
}

QPushButton#TitleBarCloseBtn:hover { 
    background-color: #e81123; 
    color: white; 
}
"""

DARK_THEME = """
QWidget {
    background-color: #202020;
    color: #f3f3f3;
    font-family: 'Adapa', -apple-system, sans-serif;
    font-size: 20px;
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

QComboBox, QSpinBox {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 8px;
}

QComboBox:hover, QSpinBox:hover {
    border: 1px solid #4a90e2;
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
    font-size: 17px;
}

QWidget#ToolTipLabel {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
}

QWidget#CustomTitleBar {
    background-color: #1a1a1a;
    border-bottom: 1px solid #333333; 
}

QLabel#TitleBarText {
    color: #f3f3f3;
    font-weight: bold; }
    
QPushButton#TitleBarCloseBtn { 
    background: transparent; 
    border: none; 
    color: #aaaaaa; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 16px; 
    font-family: 'Adapa', -apple-system, sans-serif;
}

QPushButton#TitleBarCloseBtn:hover { 
    background-color: #e81123; 
    color: white; 
}
"""