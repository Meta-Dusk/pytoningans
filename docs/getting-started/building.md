# Building & Requirements

PyToNingans is developed for Windows environments and requires **Python 3.14+** alongside **PySide6**.
This section is intended for people who intends to build the project from source. If you just want to download
the installer for the application, please refer to the **Releases** section in the GitHub repository.

---

## Prerequisites

Before running PyToNingans, ensure you have:

- **Operating System**: :fontawesome-brands-windows: Windows 10 or Windows 11 (64-bit).
- **Python**: :simple-python: Python 3.14 or newer.
- **Package Manager**: [:simple-uv: uv](https://docs.astral.sh/uv/) (recommended for instant dependency resolution and execution).

---

## Building with `uv` (Recommended)

### Step 1: **Clone the Repository**

   ```bash
   git clone https://github.com/Meta-Dusk/pytoningans.git
   cd pytoningans
   ```

### Step 2: **Sync Dependencies**

   `uv` automatically installs the appropriate PySide6 wheels matching your Python interpreter:

   ```bash
   uv sync
   ```

### Step 3: **Launch the App**

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

---

## Hosting Your Own Database

If ever you don't want to connect to the Supabase database that the app by default connects to, you can just
host your own! If you go to **Settings** in the **Control Panel**, then in the **Profile** tab, you will see
the **Account Options** context button besides your profile widget. If you click it and select the
**Cloud Server Settings** context menu option, it will open up the **Server Settings** tab, which is just the
same menu that opens when you sign-in. In that tab, you can then provide your `Supabase Project URL` and your
`Supabase Publishable API Key`. The URL and the API key are okay to be shown to the public, as these serve as
public identification only, and will NOT allow users unauthorized access to your database.

### Usual Setup

You can refer to the documentation found in
[**Supabase**](https://supabase.com/docs/guides/getting-started/the-supabase-way-to-build) on how to setup your own
project + database. Once you finish setting up your project, copy the project URL, and the publishable API key,
in which you finally paste in the **Server Settings** tab found in the **Sign-In** (or **Creator Account**) menu.
Don't forget to click the **Save Cloud Configuration** button!

### How to Supabase

I'm not an expert with how **Supabase** works, or its intricacies, so it would be best if you just go to their
[website](https://supabase.com/) and read their
[documentation](https://supabase.com/docs/guides/getting-started/the-supabase-way-to-build) on how to use their services.

A good start would be clicking the **Start your project** once you open their website, and then just finish setting it up.

---

## Building an Installer

While I can't really provide a concrete step-by-step tutorial on how to build an installer from your compiled `nuitka`
build, I can however, provide you the main gist of how the installer is made for this project.
The installer is made possible with [Inno Setup Compiler](https://jrsoftware.org/isinfo.php). You can just look it up,
and see how to setup this software, and how you can start making installers for your projects.
This project does have an installer script, that is visible in the :material-folder: `installer/` directory,
and you may refer to that as a script guide.
