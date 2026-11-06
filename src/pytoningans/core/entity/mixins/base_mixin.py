from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ...entity import BaseEntity


class BaseEntityMixin:
    """All mixins for entities inherit this base class."""

    def _entity(self) -> BaseEntity:
        """Returns `self` as the base entity class."""
        return cast("BaseEntity", self)

    def _verify_mixin_setups(self) -> None:
        """Verifies that all mixins in the MRO had their setup methods called."""
        missing: list[str] = []
        for base in type(self).__mro__:
            if base is object or base is BaseEntityMixin:
                continue

            # Look for attributes ending in '_setup_done' declared on mixins
            for attr in base.__dict__:
                if not attr.startswith("_setup_") or not attr.endswith("_done"): continue
                if getattr(self, attr, False): continue
                missing.append(f"{base.__name__} (requires setup for '{attr}')")

        if missing:
            raise RuntimeError(
                f"Class '{type(self).__name__}' instantiated without calling required setup methods: "
                f"{', '.join(missing)}"
            )
