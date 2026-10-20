# Modpacks & Shared Controllers

In addition to single-character mods, PyToNingans supports **Modpacks**—multi-entity bundles capable of executing coordinated behaviors, shared team mechanics, and synchronized events.

---

## Modpack Directory Layout

A Modpack bundles multiple entities under a shared controller:

```text
mods/
└── vocaloid_crew_pack/
    ├── pack.json            # Modpack manifest and entity roster
    ├── pack.py              # Shared controller inheriting BaseModPack
    └── entities/            # Contained entity subdirectories
        ├── hatsune_miku/
        │   ├── config.json
        │   └── sprite_sheet.png
        ├── kagamine_rin/
        │   ├── config.json
        │   └── sprite_sheet.png
        └── kagamine_len/
            ├── config.json
            └── sprite_sheet.png
```

---

## The `pack.json` Manifest

```json
{
  "id": "vocaloid_crew_pack",
  "name": "Vocaloid Desktop Companions",
  "version": "1.2.0",
  "author": "MikuFan99",
  "description": "A delightful bundle containing Hatsune Miku, Rin, and Len!",
  "is_pack": true,
  "config_version": 10,
  "contained_entities": [
    "Hatsune Miku",
    "Kagamine Rin",
    "Kagamine Len"
  ]
}
```

---

## The Shared Controller (`pack.py`)

Every Modpack can define a `pack.py` script that extends `BaseModPack`:

```python
"""Shared controller for Vocaloid Desktop Companions."""
from pytoningans.core.api import BaseModPack, PackMenuAction

class PackController(BaseModPack):
    """Coordinates behavior and shared abilities across all pack members."""

    def on_pack_loaded(self) -> None:
        print(f"Modpack {self.name} loaded with {len(self.entities)} entities!")

    def on_entity_spawned(self, entity_id: str) -> None:
        # Example: Play a fanfare when a pack member joins the desktop
        pass

    def get_custom_actions(self) -> list[PackMenuAction]:
        """Provides custom context menu actions shared across pack members."""
        return [
            PackMenuAction(
                label="Sing Duet",
                callback=self._trigger_duet_routine,
                tooltip="Synchronize dancing and singing animations"
            )
        ]

    def _trigger_duet_routine(self) -> None:
        # Custom coordination logic
        pass
```

### Key Controller Lifecycle Hooks

* `on_pack_loaded()`: Called when the pack is registered into the game session.
* `on_entity_spawned(entity_id)`: Fired whenever a member of the pack is spawned.
* `on_pack_unloaded()`: Cleanup hook when the pack is uninstalled or deactivated.
* `get_custom_actions()`: Returns action buttons added to the context menu of all member characters.
