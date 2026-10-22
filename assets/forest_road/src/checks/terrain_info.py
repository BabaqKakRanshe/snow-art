import bpy, sys
from mathutils import Vector
M = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Models/'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=M + 'Forest_Terrain.fbx')
for o in bpy.data.objects:
    print(o.name, o.type, o.parent.name if o.parent else None, tuple(round(v,3) for v in o.location), tuple(round(v,3) for v in o.rotation_euler), tuple(round(v,3) for v in o.scale))
    if o.type == 'MESH':
        me = o.data
        print('  verts', len(me.vertices), 'faces', len(me.polygons), 'mats', [m.name for m in me.materials])
        V = [o.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), 37)]
        print('  bb', [round(min(v[i] for v in V),1) for i in range(3)], [round(max(v[i] for v in V),1) for i in range(3)])
bpy.ops.wm.save_as_mainfile(filepath='/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend')
