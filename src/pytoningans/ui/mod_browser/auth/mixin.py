from __future__ import annotations

from typing import TYPE_CHECKING, cast, Optional

if TYPE_CHECKING:
    from .manager import AuthManager
    from .models import UserProfile


class BaseAuthMixin:
    def _auth_manager(self) -> AuthManager:
        """AuthManager reference for mixins."""
        return cast("AuthManager", self)
        
    def _current_user(self) -> Optional[UserProfile]:
        """Optional[UserProfile] reference for mixins."""
        return self._auth_manager().current_user