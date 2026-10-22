"""Road and terrain samples of the Forest (Unity frame) for planning: python3 -I extract_map.py -- Forest.blend out.json"""
import bpy, sys, json
from mathutils import Matrix, Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
Cinv = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))     # Blender -> Unity: (x, y, z) -> (-x, z, -y)
out = {}
road = bpy.data.objects.get('Forest_Road')
if road:
    M = road.matrix_world
    vs = [Cinv @ (M @ v.co) for v in road.data.vertices]
    out['road'] = [[round(v.x, 2), round(v.y, 2), round(v.z, 2)] for v in vs]
    # edges for drawing
    out['road_edges'] = [list(e.vertices) for e in road.data.edges]
names = [o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith(('Forest_', 'Terrain')))]
out['world_meshes'] = names[:80]
json.dump(out, open(a[1], 'w'))
print('road verts', len(out.get('road', [])), 'meshes', names[:20])
