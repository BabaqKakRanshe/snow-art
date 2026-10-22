"""cut the map round a prefab out of the Forest scene into a small .blend in that prefab's frame (Blender axes, metres):
the terrain and road patch and the power wires (Forest_Terrain.fbx, Forest_Wires.fbx from the Unity project), plus a json
with the trees, fence posts and other prefabs round it (Forest_Layout.json) — the surroundings for preview renders.
python3 -I site_patch.py <Prefab> <radius_m> <out_stem> [<Prefab#index>]   -> <out_stem>.blend, <out_stem>.json"""
import bpy, bmesh, sys, os, json, math
from mathutils import Matrix, Vector

FOREST = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/'
PREFAB, RAD, OUT = sys.argv[1], float(sys.argv[2]), sys.argv[3]
IDX = int(sys.argv[4]) if len(sys.argv) > 4 else 0
LAY = json.load(open(os.path.join(FOREST, 'Data', 'Forest_Layout.json')))


def yaw_u(q):
    return math.degrees(2 * math.atan2(q[1], q[3]))


root = [p for p in LAY['prefabs'] if p['m'] == PREFAB][IDX]
P0, TH = root['p'], yaw_u(root['q'])
B0 = Vector((-P0[0], -P0[2], P0[1]))
TO_LOCAL = Matrix.Rotation(math.radians(TH), 4, 'Z') @ Matrix.Translation(-B0)


def local(p):
    """Unity world point -> this prefab's frame (Blender axes)"""
    return TO_LOCAL @ Vector((-p[0], -p[2], p[1]))


bpy.ops.wm.read_factory_settings(use_empty=True)
keep = []
for f in ('Forest_Terrain.fbx', 'Forest_Wires.fbx'):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FOREST, 'Models', f))
    for o in set(bpy.data.objects) - before:
        if o.type != 'MESH' or o.name == 'Forest_Marker':
            bpy.data.objects.remove(o)
            continue
        me = o.data
        me.transform(TO_LOCAL @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        bm = bmesh.new()
        bm.from_mesh(me)
        far = [fc for fc in bm.faces if all(math.hypot(v.co.x, v.co.y) > RAD for v in fc.verts)]
        bmesh.ops.delete(bm, geom=far, context='FACES')
        loose = [v for v in bm.verts if not v.link_edges]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(me)
        bm.free()
        if not me.polygons:
            bpy.data.objects.remove(o)
            continue
        o['site'] = 'wires' if 'Wire' in f else ('road' if 'Road' in o.name else 'terrain')
        keep.append(o)
for m in list(bpy.data.materials):
    if m.users == 0:
        bpy.data.materials.remove(m)
bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
near = lambda p: math.hypot(*local(p).xy) < RAD
site = {'prefab': PREFAB, 'unity_p': P0, 'unity_yaw': TH, 'radius': RAD,
        'trees': [{'m': t['m'], 'p': list(map(lambda v: round(v, 3), local(t['p']))), 's': t.get('s', 1.0),
                   'yaw': round(TH - yaw_u(t['q']), 2)} for t in LAY['trees'] if near(t['p'])],
        'rocks': [{'m': r['m'], 'p': list(map(lambda v: round(v, 3), local(r['p']))), 'yaw': round(TH - yaw_u(r['q']), 2)}
                  for r in LAY['rocks'] if near(r['p'])],
        'prefabs': [{'m': p['m'], 'p': list(map(lambda v: round(v, 3), local(p['p']))), 'yaw': round(TH - yaw_u(p['q']), 2)}
                    for p in LAY['prefabs'] if near(p['p'])]}
json.dump(site, open(OUT + '.json', 'w'), indent=0)
print('objects', [(o.name, o['site'], len(o.data.vertices)) for o in keep])
print('trees', len(site['trees']), 'rocks', len(site['rocks']), 'prefabs', [(p['m'], p['p'], p['yaw']) for p in site['prefabs']])
