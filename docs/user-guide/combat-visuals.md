# Combat & Visual Feedback

PyToNingans features a dynamic combat feedback system designed to provide responsive visual indicators while keeping screen clutter minimal.

---

## Health Bar Display Modes

You can tailor how and when character health bars are rendered on screen:

| Mode | Behavior | Best Used For |
| :--- | :--- | :--- |
| **Show On Damage Only** *(Default)* | Health bars remain invisible until a character takes damage, staying visible for a configurable duration before fading out. | Distraction-free daily work and clean desktops. |
| **Always Visible** | Health bars are pinned above characters permanently. | Active battles, boss fights, or testing stats. |
| **Hidden / Disabled** | Completely disables health bar rendering. | Minimalist aesthetic. |

---

## Visual Feedback Features

### Floating Damage Numbers

When an attack connects, animated floating numbers pop up and float upward above the target, displaying the exact damage dealt with critical hit emphasis.

### Damage Impact Shake

Taking a heavy hit causes the health bar to shake proportionally to the damage taken relative to maximum health.

### Numerical HP Display

Toggles the numerical display of current health and maximum health (e.g., `85 / 100`) centered directly inside the health bar gauge.

---

## Configuring Feedback

All visual combat features are customizable in **Settings** $\rightarrow$ **Combat & Visuals**. Adjustments apply instantly to all active entities without restarting the game.
