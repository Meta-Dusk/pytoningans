# Examples

In order to spawn in particles yourself, you only can if you get an instance of
the particle manager.

---

## Accessing the Particle Manager

First, you can create a reference to the particle manager (`IParticleManager`) by accessing
the entity's world, like: `entity.world.particle_manager`. Once you verify that this does
return the `IParticleManager`, you can either just use it as-is, or attach it to the
behavior class, and name something like `_pm` so that it doesn't override any internal
declarations (just in case).

You can do all of this by implementing the `on_spawn()` method like this:

```python
...
class TestBehavior(BaseEntityBehavior):
    def on_spawn(self, entity: IEntity) -> None:
        if entity.world is None: return
        self._pm: IParticleManager = entity.world.particle_manager
```

---

## Sample Implementation

Once you have access to the particle manager instance, you can now instantiate
particles! An example implementation would be:

```python
...
class TestBehavior(BaseEntityBehavior):
    def on_spawn(self, entity: IEntity) -> None:
        if entity.world is None: return
        self._pm: IParticleManager = entity.world.particle_manager
        self._pp = ParticlePresets(self._pm)
        
        # Spawn consistent ambient particles on the entity
        self._pp.ambient_aura(
            texture=("dot", 10, "red"),
            target=entity,
        )
```

The example implementation above will work, and all it does is attach a particle emitter
to the entity once it spawns in. **However**, don't forget to clear your references to
the particle system, as they do NOT automatically clean itself after use. A simple example
of this implementation would be:

```python
...
class TestBehavior(BaseEntityBehavior):
    def on_spawn(self, entity: IEntity) -> None:
        if entity.world is None: return
        self._pm: IParticleManager = entity.world.particle_manager
        self._pp = ParticlePresets(self._pm)

        # Internal list of active emitters (not one-shots)
        self._active_emitters: Optional[list[IParticleEmitter]] = []
        
        emitter: IParticleEmitter = self._pp.ambient_aura(
            texture=("dot", 10, "red"),
            target=entity,
        )
        self._active_emitters.append(emitter)
    
    def on_destroy(self, entity: IEntity) -> None:
        if self._active_emitters is not None:
            for emitter in self._active_emitters:
                emitter.destroy()
            
        self._active_emitters = None
```

The method `on_destroy()` gets called once the entity gets destroyed, or basically a despawn.
The implementation above simply iterates through the internal list of `_active_emitters`, then
calling `.destroy()` on them, and to be extra sure that this reference is cleared in memory, we
can also set this list to `None`.

## Full Example Implementation

Below is a full example implementation that I used for testing on an entity I've made:

```python
import random
from typing import TYPE_CHECKING, Optional

from api import BaseEntityBehavior, ParticlePresets

if TYPE_CHECKING:
    from api import IEntity, IItem, IParticleManager, IParticleEmitter


class MiguBehavior(BaseEntityBehavior):
    """Custom behavior for Hatsune Miku!"""
    def on_spawn(self, entity: IEntity) -> None:
        if entity.world is None: return
        self._pm: IParticleManager = entity.world.particle_manager
        self._pp = ParticlePresets(self._pm)
        self._active_emitters: Optional[list[IParticleEmitter]] = []
        
        emitter: IParticleEmitter = self._pp.ambient_aura(
            texture=("dot", 10, "red"),
            target=entity,
        )
        self._active_emitters.append(emitter)
        
        if random.random() > 0.5:
            entity.say("（＾∀＾●）ﾉｼ Miku Dayo!", duration_ms=1500)
        else:
            entity.say("Hehehe", duration_ms=1000)
    
    def on_item_interact(self, entity: IEntity, item: IItem) -> bool:
        if entity.held_item is not None: return False
        entity.say(f"My {item.display_name} now! ( •̀ ω •́ )✧", duration_ms=2000)
        item.pick_up(entity)
        if entity.world is not None:
            self._pp.explode(
                texture=("dot", 10, "orange"),
                pos=entity.position()
            )
        return True
    
    def on_destroy(self, entity: IEntity) -> None:
        if entity.world is not None:
            self._pp.explode(
                texture=("dot", 10, "orange"),
                pos=entity.position()
            )
        if self._active_emitters is not None:
            for emitter in self._active_emitters:
                emitter.destroy()
            
        self._active_emitters = None
```

All it does, is it gives the entity an ambient aura of red dot particles upon it spawning in the world.
Additionally, it will also show an explosion of orange dots, when colliding with an **item**, and also
when it gets destroyed.
For more information about what you can do with the behavior scripts, refer to the **Modding** section
of this documentation website.
