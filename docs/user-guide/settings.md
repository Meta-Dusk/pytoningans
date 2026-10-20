# Settings & Developer Tools

The **Application Settings** dialog provides a centralized, categorized control hub for personalizing your desktop experience, configuring boundaries, and accessing developer tools.

---

## Dialog Layout & Navigation

The settings window is divided into three intuitive tabs:

```text
+-------------------------------------------------------+
| Application Settings                              [X] |
+-------------------------------------------------------+
| [ Combat & Visuals ] [ Spawning ] [ Developer ]       |
+-------------------------------------------------------+
|  ... (scrollable tab content) ...                     |
|                                                       |
|                                                       |
+-------------------------------------------------------+
| [Reset Defaults]                              [Close] |
+-------------------------------------------------------+
```

* **Auto-Resizing & Scroll Protection**: The dialog dynamically auto-sizes based on content and DPI scaling. If your monitor or scaling prevents displaying everything at once, each tab smoothly scrolls without clipping controls or action buttons.
* **Manual Resize Grip**: Drag the handle in the bottom-right corner to resize the dialog to your liking.

---

## 1. Combat & Visuals Tab

* **Health Bar Display Mode**: Select between *Show On Damage Only*, *Always Visible*, or *Hidden*.
* **Auto-Hide Delay**: Set the timeout (1 to 15 seconds) before health bars fade after taking damage.
* **Floating Damage Numbers**: Toggle popup damage counters on hit.
* **Damage Impact Shake**: Toggle health bar shaking on impacts.
* **Show HP Values**: Toggle numeric `HP / Max HP` text within the bar.
* **Desktop Window Physics**: Toggle solid collision on desktop window title bars.

---

## 2. Spawning Tab

* **Avoid Spawning Over Open Windows**: Directs spawning algorithms to prioritize empty areas of the screen.
* **Spawn Boundary Area**: Choose between full screen geometry or active desktop workspace bounds.

---

## 3. Developer Mode Tab

Checking **Enable Developer Mode** unlocks diagnostic testing capabilities:

* **Mod Browser Debug Menu**: Adds a `Debug ▾` button to the Community Mod Browser top bar.
* **Load Demo / Seed Catalog**: Injects the 6 sample demo mods into your local catalog cache for offline testing.
* **Clear Catalog Cache**: Wipes local catalog items to test empty state handling.
* **Quick Folder Access**: One-click shortcuts to open the App Data directory or local `mods/` directory in Windows Explorer.
