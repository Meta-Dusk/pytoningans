# PyToNingans

An app about putting little creatures on your desktop... Like Teto :)

## About

Initially, this app was supposed to be made with Flutter, but after testing its performance,
I have concluded that it would be better to try a different GUI framework, that supports
multiple window instances, that focuses more on performance. The Flutter version does work,
but the issue with that, is that each new window instance has their own Flutter engine,
which means that it's not exactly lightweight.

And that's how this app was born... After searching for some easy to setup GUI frameworks,
one of them was the Python version of Qt; PySide6. I have tried this before with C++, but
the issue with that, was I'm not that good with C++ yet, and was also my very first
language (and GUI framework used), which dates back a couple of years ago...

Now you might ask yourself, what does `PyToNingans` mean? Well, it's literally just a
combination of puns and acronyms:

- **Py**: Python
- **To**: (_Te_)to (_Yes, Kasane Teto_)
- **Ningans**: This is a combination of the Japanese term for "human" or "person," which is "Ningen," and "Shenanigans," which just means
random stuff :D

Anyway, hope you'll like this simple app about desktop pets! You can refer to the rest of the
sections below about what this app offers and such :)

## Feature List

| Feature | Description |
| --- | --- |
| **Customizable Pets** | Refer to the `Modding` section on how to add your own! |
| **Custom AI Behavior** | Pets can have their own behavior, interact with other pets, and (in the future) interact with your PC. |

## Modding

Yes, this app technically supports modding, but it's not fully finished yet. I'm adding support, yes,
but it's not fully finished yet, as there are a lot of missing event hooks,
and other stuff. What it does support now though, is the following:

| Modding Feature | Description |
| --- | --- |
| **Custom Sprites** | You can use your own sprite sheets! Animate it, and tweak it to render properly in the mod editor. |
| **Mod Creator / Editor** | You can create and edits mods directly in the app itself. Yippee! |
