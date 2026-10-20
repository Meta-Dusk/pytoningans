# Installation & Requirements

PyToNingans is developed for Windows environments and requires **Python 3.14+** alongside **PySide6**.

---

## Prerequisites

Before running PyToNingans, ensure you have:

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python**: Python 3.14 or newer.
3. **Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended for instant dependency resolution and execution).

---

## Installing with `uv` (Recommended)

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/Meta-Dusk/pytoningans.git
   cd pytoningans
   ```

2. **Sync Dependencies**:
   `uv` automatically installs the appropriate PySide6 wheels matching your Python interpreter:

   ```bash
   uv sync
   ```

3. **Launch the Game**:

   ```bash
   uv run py src/pytoningans/main.py
   ```

   or

   ```bash
   uv run pytoningans
   ```

---

## Standalone Executable Deployment

PyToNingans includes a complete standalone deployment specification via **Nuitka** (`pysidedeploy.spec`).

To compile an optimized, standalone Windows `.exe`:

```bash
pyside6-deploy -c pysidedeploy.spec
```

The output executable will be placed in the `build/` directory with all assets and required Qt plugins bundled.

---

## Documentation Local Preview

To build and preview this documentation website locally on your machine:

```bash
uv run --group docs mkdocs serve
```

Open your browser at `http://127.0.0.1:8000/` to browse with instant live reloading.
