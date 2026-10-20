"""
PyToNingans Mod Browser - Creator Account and Auth Dialog
=======================================================
Provides an interactive modal dialog for:
- Signing in with Email and Password
- Creating a new Creator Account
- Google OAuth in system browser
- Configuring optional Supabase Project URL and Anon Key
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QMessageBox, QFrame, QInputDialog
)

from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon, get_google_icon, get_github_icon
from ..auth import AuthManager, UserProfile
from ..async_workers import AuthWorker


class AuthDialog(QDialog):
    """Modal dialog allowing creators to authenticate or configure cloud connection."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.auth: AuthManager = AuthManager.get()
        self._auth_worker: Optional[AuthWorker] = None


        self.setWindowTitle("Creator Account")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(460, 520)

        self._setup_ui()
        self.auth.auth_state_changed.connect(self._on_auth_state_changed)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            self, "Creator Account", can_minimize=False, can_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 16, 18, 16); content_layout.setSpacing(12)

        # Tab Widget for Sign In / Create Account / Cloud Config
        self.tabs = QTabWidget()

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
        self.si_submit_btn.setObjectName("PrimaryBtn")
        self.si_submit_btn.clicked.connect(self._on_sign_in_clicked)
        si_layout.addWidget(self.si_submit_btn)

        # Separator
        sep_layout = QHBoxLayout(); sep_layout.setSpacing(8)
        line_1 = QFrame(); line_1.setFrameShape(QFrame.Shape.HLine)
        sep_layout.addWidget(line_1)
        sep_layout.addWidget(QLabel("OR", alignment=Qt.AlignmentFlag.AlignCenter))
        line_2 = QFrame(); line_2.setFrameShape(QFrame.Shape.HLine)
        sep_layout.addWidget(line_2)
        si_layout.addLayout(sep_layout)

        # OAuth Sign-In Buttons
        self.github_btn = QPushButton("  Continue with GitHub")
        self.github_btn.setIcon(get_github_icon()); self.github_btn.setIconSize(QSize(18, 18))
        self.github_btn.setToolTip("Sign in via GitHub account in default browser")
        self.github_btn.setObjectName("SecondaryBtn")
        self.github_btn.clicked.connect(self._on_github_clicked)
        si_layout.addWidget(self.github_btn)

        self.google_btn = QPushButton("  Continue with Google")
        self.google_btn.setIcon(get_google_icon()); self.google_btn.setIconSize(QSize(18, 18))
        self.google_btn.setToolTip("Sign in via Google account in default browser")
        self.google_btn.setObjectName("SecondaryBtn")
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
        self.su_submit_btn.setObjectName("SuccessBtn")
        self.su_submit_btn.clicked.connect(self._on_sign_up_clicked)
        su_layout.addWidget(self.su_submit_btn)

        su_layout.addStretch()
        self.tabs.addTab(su_tab, "Create Account")

        # Tab 3: Cloud / Supabase Settings
        cfg_tab = QWidget()
        cfg_layout = QVBoxLayout(cfg_tab); cfg_layout.setSpacing(10)

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

        cfg_layout.addWidget(QLabel("Supabase Publishable API Key:"))
        self.cfg_key_input = QLineEdit(self.auth.supabase_pub_key)
        self.cfg_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_key_input.setPlaceholderText("sb_publishable... (Publishable key)")
        cfg_layout.addWidget(self.cfg_key_input)

        self.cfg_save_btn = QPushButton("Save Cloud Configuration")
        self.cfg_save_btn.setObjectName("InfoBtn")
        self.cfg_save_btn.clicked.connect(self._on_save_config_clicked)
        cfg_layout.addWidget(self.cfg_save_btn)

        cfg_layout.addStretch()
        self.cfg_tab: QWidget = cfg_tab

        content_layout.addWidget(self.tabs)

        # Bottom Bar: Offline Mode / Advanced Server Settings + Cancel
        btn_layout = QHBoxLayout()
        self.offline_creator_btn = QPushButton("Continue in Offline Mode")
        self.offline_creator_btn.setToolTip("Set up a local creator profile for offline mod management")
        self.offline_creator_btn.setObjectName("LinkBtn")
        self.offline_creator_btn.clicked.connect(self._on_offline_creator_clicked)
        btn_layout.addWidget(self.offline_creator_btn)

        btn_layout.addSpacing(12)

        self.server_btn = QPushButton("Custom Server (Advanced)")
        self.server_btn.setToolTip(
            "Configure a custom self-hosted Supabase server URL and anon key"
        )
        self.server_btn.setObjectName("LinkBtn")
        self.server_btn.clicked.connect(self.show_server_settings)
        btn_layout.addWidget(self.server_btn)

        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def show_server_settings(self) -> None:
        """Reveals and switches to the Cloud / Server configuration tab."""
        if self.tabs.indexOf(self.cfg_tab) == -1:
            self.tabs.addTab(self.cfg_tab, "Server Settings")
        self.tabs.setCurrentWidget(self.cfg_tab)

    def _on_offline_creator_clicked(self) -> None:
        """Configures a local offline creator profile without connecting to Supabase."""
        username, ok = QInputDialog.getText(
            self,
            "Offline Creator Profile",
            "Enter your local creator handle (e.g. PixelArtist):",
            text="LocalCreator",
        )
        if ok and username.strip():
            user = self.auth.sign_in_locally(username.strip())
            QMessageBox.information(
                self, "Offline Mode", f"Operating in offline mode as '{user.username}'."
            )
            self.accept()

    def _on_sign_in_clicked(self) -> None:
        email: str = self.si_email_input.text().strip()
        pwd: str = self.si_password_input.text()
        self.si_status_lbl.setVisible(False)

        if not email or not pwd:
            self.si_status_lbl.setText("Please enter both email and password.")
            self.si_status_lbl.setVisible(True)
            return

        self.si_submit_btn.setEnabled(False)
        self.si_submit_btn.setText("Signing In...")

        self._auth_worker = AuthWorker(self.auth, "signin", email, pwd, parent=self)
        self._auth_worker.auth_completed.connect(self._on_auth_completed)
        self._auth_worker.start()

    def _on_sign_up_clicked(self) -> None:
        username: str = self.su_username_input.text().strip()
        email: str = self.su_email_input.text().strip()
        pwd: str = self.su_password_input.text()
        confirm: str = self.su_confirm_input.text()
        self.su_status_lbl.setVisible(False)

        if not username or not email or not pwd:
            self.su_status_lbl.setText("All fields are required.")
            self.su_status_lbl.setVisible(True)
            return

        if pwd != confirm:
            self.su_status_lbl.setText("Passwords do not match.")
            self.su_status_lbl.setVisible(True)
            return

        if len(pwd) < 6:
            self.su_status_lbl.setText("Password must be at least 6 characters.")
            self.su_status_lbl.setVisible(True)
            return

        self.su_submit_btn.setEnabled(False)
        self.su_submit_btn.setText("Creating Account...")

        self._auth_worker = AuthWorker(
            self.auth, "signup", email, pwd, username=username, parent=self
        )
        self._auth_worker.auth_completed.connect(self._on_auth_completed)
        self._auth_worker.start()

    def _on_auth_completed(
        self, success: bool, msg: str, user: Optional[UserProfile]
    ) -> None:
        self.si_submit_btn.setEnabled(True)
        self.si_submit_btn.setText("Sign In")
        self.su_submit_btn.setEnabled(True)
        self.su_submit_btn.setText("Create Account")

        if success:
            QMessageBox.information(self, "Welcome", msg)
            self.accept()
        else:
            is_signup: bool = (self.tabs.currentIndex() == 1)
            target_lbl = self.su_status_lbl if is_signup else self.si_status_lbl
            target_lbl.setText(msg)
            target_lbl.setVisible(True)


    def _on_github_clicked(self) -> None:
        success, msg = self.auth.start_github_oauth()
        if success:
            QMessageBox.information(self, "Browser Sign-In", msg)
        else:
            QMessageBox.warning(self, "OAuth Error", msg)

    def _on_google_clicked(self) -> None:
        success, msg = self.auth.start_google_oauth()
        if success:
            QMessageBox.information(self, "Browser Sign-In", msg)
        else:
            QMessageBox.warning(self, "OAuth Error", msg)

    def _on_save_config_clicked(self) -> None:
        url: str = self.cfg_url_input.text().strip()
        key: str = self.cfg_key_input.text().strip()
        self.auth.save_config(url, key)
        QMessageBox.information(
            self, "Settings Saved",
            "Supabase cloud configuration saved.\n"
            + ("Cloud sync is active!" if (url and key) else "Operating in offline-first mode.")
        )

    def _on_auth_state_changed(self, user: Optional[UserProfile]) -> None:
        if user is not None and self.isVisible():
            self.accept()

