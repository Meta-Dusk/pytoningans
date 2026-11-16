# Example Mod Pack Behavior Scripts

For now, you can only see the pack script (:simple-python: `pack.py`)
if you open the folder containing it. It's usually found inside the root
:material-folder: folder (which is the name of the modpack).

An example file structure would be:

```text
test_pack/
├───entities/
│   ├───botnets/...
│   ├───el_gatito/...
│   ├───migu/...
│   ├───test/...
│   ├───test2/...
│   ├───test3/...
│   ├───teto/...
│   └───the_isaac/...
├───items/
│   └───test_item/...
├───structures/
│   └───test_struc/...
├───pack.json
└───pack.py
```

## Starting Script

```python
"""Shared runtime controller for modpack 'Test Pack'."""
from api import BaseModPack, PackMenuAction

class PackController(BaseModPack):
    def on_pack_loaded(self) -> None:
        # Initialize shared variables across all pack entities
        self.shared_state['status'] = 'Active'

    def on_entity_spawned(self, entity) -> None:
        # Called when any entity belonging to this pack spawns
        pass

    def get_context_menu_actions(self, entity) -> list[PackMenuAction]:
        # Return custom desktop context menu actions for pack entities
        return []
```

The example above is what you would usually find if you create a modpack from the
:material-window-open: **Mod Editor** window.
