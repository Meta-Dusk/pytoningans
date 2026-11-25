# TODO (For App)

## Planned Features

- [ ] Add animation triggers (to call the event attached to it)
- [ ] Maybe transfer some features into a new window: the `Sprite Editor`
- [ ] Optional Audio Systems
- [ ] Update the config to be a lot more flexible; instead of hardcoding states, make it support dynamic states, such as making it of type `str | Literal` instead (make sure to add a new supporting class for this, or just update the existing one)

### Immersive Conversations Modpack

- [ ] Add AI conversations for the pets (shared conversation to save performance)
- [ ] "Dumb Mode": disable AI, and leave only player interactions to it

### Idler Modpack

- [ ] Find a better name for the modpack
- [ ] Add a "Town Hall" where it represents as the house, where the pets can go in/out of
- [ ] Add a score counter (for time passed), where optionally, it can upgrade the *town hall*
- [ ] Add an affection meter for pets

## Important Fixes

- [ ] Make sure to bundle a modpack as sample content when installing offline
- [ ] Fix the `pack.json` modpack manifest, as it lacks fields

## Main Features

- [ ] Implement actual idler game mechanics (most likely via a modpack implementation)
- [ ] Add an optional FPS display (maybe as a new window, or just in the Main Menu)
- [ ] Add option in settings for manually updating the API

## Mod Editor Improvements

- [ ] Add method to combine multiple sprite sheets, to lessen burden on the modder
- [ ] Fix the interactive cropping feature, since it kinda doesn't work that well
- [ ] Clean up mod editor (such as moving the buttons to make it make sense)
