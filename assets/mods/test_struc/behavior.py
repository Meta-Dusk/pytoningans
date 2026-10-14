from api import BaseStructureBehavior, IStructure, StructureState

class Behavior(BaseStructureBehavior):
    def on_spawn(self, structure: IStructure) -> None:
        # Attach the preset teleportation component
        teleport = structure.attach_teleportation(
            exit_offset_x=90.0,
            exit_offset_y=0.0
        )
        
        # Pair with any matching structure already in the world
        manager = structure.world.manager
        for other in manager.active_structures:
            if other != structure and other.has_component("teleportation"):
                other_teleport = other.get_component("teleportation")
                teleport.linked_portal = other
                other_teleport.linked_portal = structure
                
                structure.state = StructureState.ACTIVE
                other.state = StructureState.ACTIVE
                break