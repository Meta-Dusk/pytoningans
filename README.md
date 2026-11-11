# PyToNingans

> An app about putting little creatures on your desktop... Like Teto :)

That was the original premise, but now after expanding on the idea so much, it's no longer just a "Desktop Pets" app... It's uh,
something like a **Desktop Entities Engine Platform**? I'm unsure about the terminology because, well... Yeah; It has modding
capabilities built-in, a way to easily create your own entities that can roam around and interact with you desktop, and even
an _optional_ platform where users of this application can just upload their mods/modpacks they have made. It's optional, because
you don't really have to upload to _my_ database, meaning; you can just host your own!

It's all about flexibility over here, and giving people the tools to also be able to reasonably recreate,
what I have done here with this entire project so far.

![Current Application Icon](assets/icon.png)

## About

Initially, this app was supposed to be made with `Flutter`, but after testing its performance,
I have concluded that it would be better to try a different GUI framework, that supports
multiple window instances, that focuses more on performance. The `Flutter` version does work,
but the issue with that, is that each new window instance has their own `Flutter` engine,
which means that it's not exactly lightweight.

And that's how this app was born... After searching for some easy to setup GUI frameworks,
one of them was the `Python` version of `Qt`; `PySide6`. I have tried this before with `C++`, but
the issue with that, was I'm not that good with `C++` yet, and was also my very first
language (and GUI framework used), which dates back a couple of years ago...

Now you might ask yourself, what does `PyToNingans` mean? Well, it's literally just a
combination of puns and acronyms:

| Root | Meaning |
| ---- | ------- |
| **Py** | Python |
| **To** | (_Te_)to (_Yes, Kasane Teto_) |
| **Ningans** | This is a combination of the Japanese term for "human" or "person," which is "Ningen," and "Shenanigans," which just means random stuff :D |

Anyway, hope you'll like this game about having desktop critters roam around! You can refer to the documentation website
in the about section of this repo to the right, or you can just go here: [PyToNingans Documentation](https://meta-dusk.github.io/pytoningans/)
