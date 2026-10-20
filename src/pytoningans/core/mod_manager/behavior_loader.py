from __future__ import annotations

import importlib.util, inspect, sys
from pathlib import Path
from typing import Optional, cast

from pytoningans.core.api import BaseBehavior
from pytoningans.core.constants import EntityType


def compile_behavior_mod(
    mod_folder_name: str, mod_path: Path, entity_type: str
) -> Optional[BaseBehavior]:
    """Compiles and instantiates the custom behavior class from a mod's behavior.py."""
    behavior_path: Path = mod_path / "behavior.py"
    if not behavior_path.exists():
        return None

    try:
        # Guarantee that 'import api' inside any mod's behavior.py resolves
        # directly to the engine's core API module and submodules in memory
        import pytoningans.core.api as core_api
        import pytoningans.core.api.types as api_types
        import pytoningans.core.api.components as api_components
        import pytoningans.core.api.protocols as api_protocols
        import pytoningans.core.api.behaviors as api_behaviors
        import pytoningans.core.api.modpack as api_modpack

        sys.modules["api"] = core_api
        sys.modules["api.types"] = api_types
        sys.modules["api.components"] = api_components
        sys.modules["api.protocols"] = api_protocols
        sys.modules["api.behaviors"] = api_behaviors
        sys.modules["api.modpack"] = api_modpack

        spec = importlib.util.spec_from_file_location(
            f"mod_behavior_{mod_folder_name}", str(behavior_path)
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if entity_type == EntityType.STRUCTURE:
            target_base_name: str = "BaseStructureBehavior"
        elif entity_type == EntityType.ITEM:
            target_base_name: str = "BaseItemBehavior"
        else:
            target_base_name: str = "BaseEntityBehavior"

        for _, obj in inspect.getmembers(module, inspect.isclass):
            mro_names: list[str] = [base.__name__ for base in inspect.getmro(obj)]
            if target_base_name in mro_names and obj.__name__ != target_base_name:
                return cast(BaseBehavior, obj())

    except Exception as e:
        print(f"Failed to load behavior.py for {mod_folder_name}: {e}")

    return None

