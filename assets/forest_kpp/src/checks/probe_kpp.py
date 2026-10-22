"""KPP-specific checks on out/kpp.blend: the map placement of the three roots vs Update 3 (Forest_Layout.json prefabs), the
prologue's points vs Forest_Opening.json (the keys' hanging points, the guard book, the padlock, the phone zone, the bell, the
key cabinet door's pivot), the item shapes at their spots clear of the model (a box the size of each item), the padlock's
shackle inside both eyes, the booth's window band seen from the road.  python3 -I probe_kpp.py <Forest_Data_dir>"""
import bpy, json, math, sys, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

DATA = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/kpp.blend')
C = json.load(open('/home/claude/uaz/out/kpp_contract.json'))
LAY = json.load(open(os.path.join(DATA, 'Forest_Layout.json')))
OPN = json.load(open(os.path.join(DATA, 'Forest_Opening.json')))
P0 = Vector((313.0406, 16.4376, -289.5625))
TH = math.radians(8.0)


def to_booth(p):
    d = Vector(p) - P0
    xl = d.x * math.cos(TH) - d.z * math.sin(TH)
    zl = d.x * math.sin(TH) + d.z * math.cos(TH)
    return Vector((-xl, -zl, d.y))


print('== map placement vs Update 3 (Forest_Layout prefabs)')
for pf in LAY['prefabs']:
    if pf['m'] in ('Checkpoint', 'Barrier', 'Gate'):
        mine = C['meta']['map_placement'][pf['m']]
        dp = (Vector(mine['p']) - Vector(pf['p'])).length * 1000
        yu = 2 * math.degrees(math.atan2(pf['q'][1], pf['q'][3]))
        print(f"  {pf['m']:11s} Update 3 p {pf['p']} yaw {yu:.3f} | now p {mine['p']} yaw {mine['yawUnity']} | diff {dp:.1f} mm, "
              f"{abs(yu - mine['yawUnity']):.3f} deg")
print('== prologue points vs Forest_Opening.json')
S = C['sockets']
pairs = {'Key_Schranke': 'Key_Hook_Schranke', 'Key_Hauptgebaeude': 'Key_Hook_Hauptgebaeude', 'Key_Garage': 'Key_Hook_Garage',
         'Key_Generator': 'Key_Hook_Generator', 'Note_KPPLog': 'Spot_KPPLog', 'Padlock_Barrier': 'Spot_Padlock'}
for it in OPN['items']:
    if it['id'] in pairs:
        u = to_booth(it['p'])
        m = Vector(S[pairs[it['id']]]['pos'])
        print(f"  {it['id']:18s} data {tuple(round(v, 3) for v in u)}  socket {tuple(round(v, 3) for v in m)}  diff {(u - m).length * 1000:.1f} mm")
for z in OPN['zones']:
    if z['id'] == 'Phone_KPP':
        u = to_booth(z['p'])
        rc = Vector(C['parts']['Phone_Receiver']['pivot'])
        sz = z['size']
        inside = abs(rc.x - u.x) <= sz[0] / 2 and abs(rc.y - u.y) <= sz[2] / 2 and abs(rc.z - u.z) <= sz[1] / 2
        print(f"  zone Phone_KPP at {tuple(round(v, 3) for v in u)} size {sz}: the receiver {tuple(round(v, 3) for v in rc)} inside: {inside}")
for sc_ in OPN['scares']:
    if sc_['id'] == 'X05_Phone':
        u = to_booth(sc_['bell'])
        b = Vector(C['parts']['Phone_Bell']['pivot'])
        print(f"  X05 bell data {tuple(round(v, 3) for v in u)}  Phone_Bell {tuple(round(v, 3) for v in b)}  diff {(u - b).length * 1000:.1f} mm")
for it in OPN['interactables']:
    if it.get('child') == 'IX_KeyBoxDoor_303':
        u = to_booth(it['p'])
        k = Vector(C['parts']['IX_KeyBoxDoor_303']['pivot'])
        print(f"  KeyBox data {tuple(round(v, 3) for v in u)}  IX_KeyBoxDoor_303 pivot {tuple(round(v, 3) for v in k)}  diff {(u - k).length * 1000:.1f} mm")
# item shapes (their own meshes' sizes, from the Update 3 package) at their spots: must not cut the model
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Glow_'))]
BV = {}
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    BV[o.name] = BVHTree.FromPolygons([M @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])


def box_bvh(lo, hi):
    V = [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return BVHTree.FromPolygons(V, F)


print('== item shapes at their spots (Update 3 item meshes, booth axes)')
KEY = ((-0.016, -0.003, -0.084), (0.016, 0.003, 0.001))           # Item_Key_*: x, y (thickness), z
for k in ('Key_Hook_Schranke', 'Key_Hook_Hauptgebaeude', 'Key_Hook_Garage', 'Key_Hook_Generator'):
    p = Vector(S[k]['pos'])
    b = box_bvh(p + Vector(KEY[0]), p + Vector(KEY[1]))
    hits = [n for n, t in BV.items() if t.overlap(b)]
    print(f'  {k:24s} key body {"clear" if not hits else "cuts " + ", ".join(hits)}')
p = Vector(S['Spot_KPPLog']['pos'])                                # Item_NoteForm 0.148 x 0.21 x 0.006, turned 90 deg
b = box_bvh(p + Vector((-0.105, -0.074, 0.001)), p + Vector((0.105, 0.074, 0.006)))
hits = [n for n, t in BV.items() if t.overlap(b)]
print(f'  Spot_KPPLog              note {"clear" if not hits else "cuts " + ", ".join(hits)}')
p = Vector(S['Spot_Padlock']['pos'])                               # Item_Padlock: body below the hanging point, turned 90 deg
body = box_bvh(p + Vector((-0.012, -0.025, -0.070)), p + Vector((0.014, 0.025, -0.012)))
hits = [n for n, t in BV.items() if t.overlap(body)]
print(f'  Spot_Padlock             lock body {"clear" if not hits else "cuts " + ", ".join(hits)}')
# the shackle's bend (y across, at the top) must pass through both eyes: points on the bend inside the two rings' holes
eye_c = Vector((5.85 + 3.10, -7.0, 1.026 - 0.3867))
for yy in (-0.007, 0.007):
    c = eye_c + Vector((0, yy, 0))
    top = Vector((p.x, p.y + yy, p.z + 0.009))
    dxz = math.hypot(top.x - c.x, top.z - c.z)
    print(f'  eye at y {yy:+.3f}: the shackle top {dxz * 1000:.1f} mm from the eye centre (inside the hole if < 8 mm)')
# the windows seen from the road: rays from the driver's eye at the barrier to the front window lights hit glass first
dg = bpy.context.evaluated_depsgraph_get()
eye = Vector((7.5, -9.0, 1.2 - 0.38))
for tx in (-1.513, -0.913, -0.30, 0.30, 0.913, 1.513):            # pane centres (each light has a glazing cross)
    t = Vector((tx, -1.54, 1.50))
    d = (t - eye)
    hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(dg, eye, d.normalized(), distance=d.length + 0.05)
    mat = ob.material_slots[ob.data.polygons[idx].material_index].material.name if hit and ob.material_slots else None
    print(f'  road -> front window pane at x {tx:+.2f}: first hit {ob.name if hit else None} ({mat})')
