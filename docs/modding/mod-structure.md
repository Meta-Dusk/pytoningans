# Mod Architecture & Configuration

PyToNingans is built from the ground up for modding. Each entity is a self-contained :material-folder: directory
containing its :material-code-json: configuration, :material-image: spritesheet, and
:simple-python: optional behavior script.

---

## Mod Directory Structure

A standalone entity mod is organized as follows:

```text
mods/
└── my_cool_character/
    ├── behavior.py (optional)
    ├── config.json
    └── sprite_sheet.png
```

> Do note that the file names below needs to be exactly the same!

=== ":material-code-json: `config.json`"
    This contains the main manifest, stats, and animation definitions.
    It's best to not modify this manually, as the app auto-generates this via the **Mod Editor**.

=== ":material-image: `sprite_sheet.png`"
    Grid of character animation frames. Do note that you can edit how the app renders your sprites
    in the **Mod Editor**.

=== ":simple-python: `behavior.py`"
    Custom entity behavior. You can easily create one by clicking the **Create...** action button
    found in the **Behavior ... Options** dropdown section in the **Mod Editor**. For more details on this,
    you can refer to the **Creating Custom Behaviors** section found in the **Modding** category of the
    documentation!

---

## The `config.json` Manifest

Below is an example:

```json
{
  "name": "Bouncing Slime Knight",
  "version": "1.0.4",
  "author": "RetroGamer",
  "description": "A brave tiny slime equipped with a sword and shield.",
  "entity_type": "entity",
  "config_version": 10,
  "stats": {
    "max_hp": 100,
    "speed": 3.5,
    "attack_power": 15,
    "gravity": 0.4
  },
  "spritesheet": {
    "path": "sprite_sheet.png",
    "frame_width": 32,
    "frame_height": 32,
    "columns": 4,
    "rows": 4
  },
  "animations": {
    "idle": {
      "row": 0,
      "frames": 4,
      "frame_rate_ms": 150,
      "loop": true
    },
    "walk": {
      "row": 1,
      "frames": 4,
      "frame_rate_ms": 120,
      "loop": true
    },
    "attack": {
      "row": 2,
      "frames": 3,
      "frame_rate_ms": 90,
      "loop": false
    }
  }
}
```

---

## Config Versioning

The `config_version` field tracks schema compatibility. The current version is defined by
`CURRENT_CONFIG_VERSION` (`10`).

If a community mod was authored for an older schema version, the Community Mod Browser flags it with an
**`Outdated Config (vX)`** warning tag, helping users make informed download decisions.
