# Standalone Behavior Scripts

Once you click the button in the **Mod Editor** window, in the collapsible section for the
entity's **Behavior Options**, you can go ahead and open it by clicking the **Open in VS Code**
action button. This will open up :material-microsoft-visual-studio-code: **VS Code**,
and show a workspace with the :material-folder: `mods/` directory as the root.
You will see the :material-folder: `api/` directory there, which is basically
the decoupled, and abstracted definitions, types, and methods that you can use to interface with the
application.

---

## Folder Structure

Below is the folder structure of the application's data (example). You can find this inside your temp folder like
(`MY_PC/Documents/PyToNingans`):

```text
PyToNingans/
├───avatars/
└───mods/
    ├───api/
    │   ├───protocol/
    │   │   ├───core/
    │   │   ├───entity/
    │   │   └───particle/
    ├───just_migu/
    ├───just_teto/
    └───test_pack/
        ├───entities/
        │   ├───botnets/
        │   ├───el_gatito/
        │   ├───migu/
        │   ├───test/
        │   ├───test2/
        │   ├───test3/
        │   ├───teto/
        │   └───the_isaac/
        ├───items/
        │   └───test_item/
        └───structures/
            └───test_struc/
```

As for the workspace that would open if you open it with :material-microsoft-visual-studio-code: VS Code,
it will show this folder structure (as an example):

```text
mods/
├───api/
│   ├───protocol/
│   │   ├───core/
│   │   ├───entity/
│   │   ├───particle/
├───just_migu/
├───just_teto/
└───test_pack/
    ├───entities/
    │   ├───botnets/
    │   ├───el_gatito/
    │   ├───migu/
    │   ├───test/
    │   ├───test2/
    │   ├───test3/
    │   ├───teto/
    │   └───the_isaac/
    ├───items/
    │   └───test_item/
    └───structures/
        └───test_struc/
```
