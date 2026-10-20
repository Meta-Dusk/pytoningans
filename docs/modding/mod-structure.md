# Mod Architecture & Configuration

PyToNingans is built from the ground up for modding. Each companion or character is a self-contained directory containing its configuration, spritesheets, and sound effects.

---

## Mod Directory Structure

A standalone entity mod is organized as follows:

```text
mods/
└── my_cool_character/
    ├── config.json          # Main manifest, stats, and animation definitions
    └── sprite_sheet.png     # Grid of character animation frames
    
```

---

## The `config.json` Manifest

The `config.json` file dictates stats, behaviors, and animation framing.

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

The `config_version` field tracks schema compatibility. The current version is defined by `CURRENT_CONFIG_VERSION` (`10`).

If a community mod was authored for an older schema version, the Community Mod Browser flags it with an **`Outdated Config (vX)`** warning tag, helping users make informed download decisions.
