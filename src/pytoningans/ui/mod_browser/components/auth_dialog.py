"""
PyToNingans Mod Browser - Creator Account & Auth Dialog
=======================================================
Provides an interactive modal dialog for:
- Signing in with Email & Password
- Creating a new Creator Account
- Google OAuth in system browser
- Configuring optional Supabase Project URL & Anon Key
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QMessageBox, QFrame
)

from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon
from ..auth import AuthManager, UserProfile


class AuthDialog(QDialog):
    """Modal dialog allowing creators to authenticate or configure cloud connection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.auth: AuthManager = AuthManager.get()

        self.setWindowTitle("Creator Account")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(460, 480)

        self._setup_ui()
        self.auth.auth_state_changed.connect(self._on_auth_state_changed)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, "Creator Account", can_minimize=False, can_maximize=False)
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 16, 18, 16); content_layout.setSpacing(12)

        # Tab Widget for Sign In / Create Account / Cloud Config
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #181825;
                padding: 10px;
            }
            QTabBar::tab {
                background: #1e1e2e;
                color: #a6adc8;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #313244;
                color: #cdd6f4;
                font-weight: bold;
            }
        """)

        # Tab 1: Sign In
        sign_in_tab = QWidget()
        si_layout = QVBoxLayout(sign_in_tab)
        si_layout.setSpacing(10)

        si_layout.addWidget(QLabel("Email Address:"))
        self.si_email_input = QLineEdit()
        self.si_email_input.setPlaceholderText("creator@example.com")
        si_layout.addWidget(self.si_email_input)

        si_layout.addWidget(QLabel("Password:"))
        self.si_password_input = QLineEdit()
        self.si_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.si_password_input.setPlaceholderText("••••••••")
        si_layout.addWidget(self.si_password_input)

        self.si_status_lbl = QLabel("")
        self.si_status_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")
        self.si_status_lbl.setVisible(False)
        si_layout.addWidget(self.si_status_lbl)

        self.si_submit_btn = QPushButton("Sign In")
        self.si_submit_btn.setStyleSheet(
            "background-color: #3b82f6; color: white; font-weight: bold; padding: 7px;"
        )
        self.si_submit_btn.clicked.connect(self._on_sign_in_clicked)
        si_layout.addWidget(self.si_submit_btn)

        # Separator
        sep_layout = QHBoxLayout(); sep_layout.setSpacing(8)
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setStyleSheet("color: #313244;")
        sep_layout.addWidget(line1)
        sep_layout.addWidget(QLabel("OR"))
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("color: #313244;")
        sep_layout.addWidget(line2)
        si_layout.addLayout(sep_layout)

        # Google Sign-In Button
        self.google_btn = QPushButton("Continue with Google")
        self.google_btn.setToolTip("Sign in via Google account in default browser")
        self.google_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                font-weight: bold;
                padding: 7px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        self.google_btn.clicked.connect(self._on_google_clicked)
        si_layout.addWidget(self.google_btn)

        si_layout.addStretch()
        self.tabs.addTab(sign_in_tab, "Sign In")

        # Tab 2: Create Account
        su_tab = QWidget()
        su_layout = QVBoxLayout(su_tab)
        su_layout.setSpacing(10)

        su_layout.addWidget(QLabel("Creator Username:"))
        self.su_username_input = QLineEdit()
        self.su_username_input.setPlaceholderText("e.g. PixelArtist")
        su_layout.addWidget(self.su_username_input)

        su_layout.addWidget(QLabel("Email Address:"))
        self.su_email_input = QLineEdit()
        self.su_email_input.setPlaceholderText("creator@example.com")
        su_layout.addWidget(self.su_email_input)

        su_layout.addWidget(QLabel("Password (min 6 chars):"))
        self.su_password_input = QLineEdit()
        self.su_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.su_password_input.setPlaceholderText("••••••••")
        su_layout.addWidget(self.su_password_input)

        su_layout.addWidget(QLabel("Confirm Password:"))
        self.su_confirm_input = QLineEdit()
        self.su_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.su_confirm_input.setPlaceholderText("••••••••")
        su_layout.addWidget(self.su_confirm_input)

        self.su_status_lbl = QLabel("")
        self.su_status_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")
        self.su_status_lbl.setVisible(False)
        su_layout.addWidget(self.su_status_lbl)

        self.su_submit_btn = QPushButton("Create Account")
        self.su_submit_btn.setStyleSheet(
            "background-color: #10b981; color: white; font-weight: bold; padding: 7px;"
        )
        self.su_submit_btn.clicked.connect(self._on_sign_up_clicked)
        su_layout.addWidget(self.su_submit_btn)

        su_layout.addStretch()
        self.tabs.addTab(su_tab, "Create Account")

        # Tab 3: Cloud / Supabase Settings
        cfg_tab = QWidget()
        cfg_layout = QVBoxLayout(cfg_tab)
        cfg_layout.setSpacing(10)

        info_lbl = QLabel(
            "Connect to your own Supabase project for real-time community sync.\n"
            "If left blank, PyToNingans runs seamlessly in offline local mode."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #a6adc8; font-size: 11px;")
        cfg_layout.addWidget(info_lbl)

        cfg_layout.addWidget(QLabel("Supabase Project URL:"))
        self.cfg_url_input = QLineEdit(self.auth.supabase_url)
        self.cfg_url_input.setPlaceholderText("https://your-project.supabase.co")
        cfg_layout.addWidget(self.cfg_url_input)

        cfg_layout.addWidget(QLabel("Supabase Anon Public API Key:"))
        self.cfg_key_input = QLineEdit(self.auth.supabase_anon_key)
        self.cfg_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_key_input.setPlaceholderText("eyJh... (Public anon key)")
        cfg_layout.addWidget(self.cfg_key_input)

        self.cfg_save_btn = QPushButton("Save Cloud Configuration")
        self.cfg_save_btn.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 6px;")
        self.cfg_save_btn.clicked.connect(self._on_save_config_clicked)
        cfg_layout.addWidget(self.cfg_save_btn)

        cfg_layout.addStretch()
        self.tabs.addTab(cfg_tab, "Cloud Settings")

        content_layout.addWidget(self.tabs)

        # Bottom Close Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        content_layout.addLayout(btn_layout)

        main_layout.addWidget(content)

    def _on_sign_in_clicked(self) -> None:
        email = self.si_email_input.text().strip()
        pwd = self.si_password_input.text()
        self.si_status_lbl.setVisible(False)

        success, msg, user = self.auth.sign_in_with_password(email, pwd)
        if success:
            QMessageBox.information(self, "Welcome", msg)
            self.accept()
        else:
            self.si_status_lbl.setText(msg)
            self.si_status_lbl.setVisible(True)

    def _on_sign_up_clicked(self) -> None:
        username = self.su_username_input.text().strip()
        email = self.su_email_input.text().strip()
        pwd = self.su_password_input.text()
        confirm = self.su_confirm_input.text()
        self.su_status_lbl.setVisible(False)

        if pwd != confirm:
            self.su_status_lbl.setText("Passwords do not match.")
            self.su_status_lbl.setVisible(True)
            return

        success, msg, user = self.auth.sign_up(email, pwd, username)
        if success:
            QMessageBox.information(self, "Account Created", msg)
            self.accept()
        else:
            self.su_status_lbl.setText(msg)
            self.su_status_lbl.setVisible(True)

    def _on_google_clicked(self) -> None:
        success, msg = self.auth.start_google_oauth()
        if success:
            QMessageBox.information(self, "Browser Sign-In", msg)
        else:
            QMessageBox.warning(self, "OAuth Error", msg)

    def _on_save_config_clicked(self) -> None:
        url = self.cfg_url_input.text().strip()
        key = self.cfg_key_input.text().strip()
        self.auth.save_config(url, key)
        QMessageBox.information(
            self,
            "Settings Saved",
            "Supabase cloud configuration saved.\n"
            + ("Cloud sync is active!" if (url and key) else "Operating in offline-first mode.")
        )

    def _on_auth_state_changed(self, user: Optional[UserProfile]) -> None:
        if user is not None and self.isVisible():
            self.accept()

