# API Reference

This page documents the core public classes, constants, and protocols provided by PyToNingans for modders and developers.

---

## Core Modding API (`pytoningans.core.api`)

### `BaseModPack`

The foundational class for Modpack shared controllers.

```python
class BaseModPack:
    """Base class inherited by all custom Modpack controllers."""

    id: str
    name: str
    version: str
    entities: list[BaseEntity]

    def on_pack_loaded(self) -> None:
        """Invoked when the modpack is activated and loaded into the session."""

    def on_entity_spawned(self, entity_id: str) -> None:
        """Invoked whenever a member character is spawned onto the desktop."""

    def on_pack_unloaded(self) -> None:
        """Invoked during cleanup when the modpack is removed."""

    def get_custom_actions(self) -> list[PackMenuAction]:
        """Returns custom actions exposed in member context menus."""
```

### `PackMenuAction`

Encapsulates an interactive context menu item provided by a Modpack.

```python
@dataclass
class PackMenuAction:
    label: str
    callback: Callable[[], None]
    tooltip: str = ""
```

---

## Constants & Schemas (`pytoningans.core.constants`)

### `EntityType`

Enumeration of supported entity categorizations:

* `EntityType.ENTITY`: Standard standalone animated character.
* `EntityType.PACK`: A bundled collection of multiple entities.

### `CURRENT_CONFIG_VERSION`

An integer specifying the latest configuration schema version (`10`).
Mods declaring an older version will display an outdated tag in the browser.

---

## Settings (`pytoningans.core.settings`)

### `HealthBarMode`

* `HealthBarMode.ON_DAMAGE = "on_damage"`
* `HealthBarMode.ALWAYS = "always"`
* `HealthBarMode.HIDDEN = "hidden"`
