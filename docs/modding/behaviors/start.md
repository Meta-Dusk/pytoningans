# Behavior Scripts

Once you click the button in the **Mod Editor** window, in the collapsible section for the
entity's **Behavior Options**, you can go ahead and open it by clicking the **Open in VS Code**
action button. This will open up :material-microsoft-visual-studio-code: **VS Code**,
and show a workspace with the :material-folder: `mods/` directory as the root.
You will see the :material-folder: `api/` directory there, which is basically
the decoupled, and abstracted definitions, types, and methods that you can use to interface with the
application.

---

## Folder Structure

> The information below just simply expands on what has been discussed in the **Mod Architecture & Config** and
> **Modpacks & Shared Controllers**.

Below is the folder structure of the application's data (example). You can find this inside your temp folder like
(`MY_PC/Documents/PyToNingans`):

```text
PyToNingans/
├───avatars/
├───mods/
│   ├───api/
│   ├───just_migu/...
│   ├───just_teto/...
│   └───test_pack/...
│       ├───entities/
│       │   ├───botnets/...
│       │   ├───el_gatito/...
│       │   ├───migu/...
│       │   ├───test/...
│       │   ├───test2/...
│       │   ├───test3/...
│       │   ├───teto/...
│       │   └───the_isaac/...
│       ├───items/
│       │   └───test_item/...
│       └───structures/
│           └───test_struc/...
├───creator_roles_cache.json
└───settings.json
```

=== ":material-folder: `avatars/`"
    These are where user profile avatars are stored if there are any.
    You can delete these, as these are just downloaded for performance.

=== ":material-folder: `mods/`"
    These are where your mods and modpacks are found. The root folder is where
    the :material-code-json: `config.json` and :material-image: `sprite_sheet.png` are found.
    The name of this root folder is the mod's identifier.

=== ":material-folder: `api/`"
    This folder contains all of the methods, declarations, and types that you can use to
    interface with the backend of the application.

=== ":material-folder: `creator_roles_cache.json`"
    This is just a temporary file for caching in the available creator roles.

=== ":material-folder: `settings.json`"
    This file contains all of the global settings (which are recommended to tweak in-app instead).

As for the workspace that would open if you open it with :material-microsoft-visual-studio-code: VS Code,
it will show this folder structure (as an example):

```text
mods/
├───api/
├───just_migu/
│   ├───behavior.py
│   ├───config.json
│   └───sprite_sheet.png
├───just_teto/
│   ├───behavior.py
│   ├───config.json
│   └───sprite_sheet.png
└───test_pack/
    ├───entities/
    │   ├───botnets/
    │   │   ├───config.json
    │   │   └───sprite_sheet.png
    │   ├───el_gatito/...
    │   ├───migu/...
    │   ├───test/...
    │   ├───test2/...
    │   ├───test3/...
    │   ├───teto/...
    │   └───the_isaac/...
    ├───items/
    │   └───test_item/...
    └───structures/
        └───test_struc/...
```

=== ":material-folder: `behavior.py`"
    This contains custom entity behavior that you can implement. It's entirely optional,
    as the engine has default behaviors for all entities. Items and structures are
    recommended to have custom behavior implemented, such as giving creatures the ability
    to pick up items
    (you'll implement this behavior for entries in :material-folder: `entities/` instead.)

=== ":material-code-json: `config.json`"
    This contains the main manifest, stats, and animation definitions.
    It's best to not modify this manually, as the app auto-generates this via the **Mod Editor**.

=== ":material-image: `sprite_sheet.png`"
    Grid of character animation frames. Do note that you can edit how the app renders your sprites
    in the **Mod Editor**.

If you want, you can also setup the modding folder to use git for your version control as well.
You would expect like a new file and a new folder in :material-folder: `mods/`, which are:

=== ":material-folder: `.git/`"
    Contains the necessary stuff for a git repository.

=== ":simple-git: `.gitignore`"
    Contains files/folders that you don't want to be included when comitting changes in the
    repository. A good example would be:
    ```text
    # Python-generated files
    __pycache__/
    *.py[oc]
    ```
