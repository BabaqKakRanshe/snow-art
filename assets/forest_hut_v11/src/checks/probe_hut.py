"""Hut-specific checks on out/hut.blend: the lantern seen from the car (no part of the hut in the way), the item spots
clear of the model (a box the size of each item), the door at 0 / 100 / 105 against the rest, the stand's ladder and
cabin door, the oil lamp's head room, the sign's and the stand's map placement vs Update 3.
python3 -I probe_hut.py"""
import bpy, json, math, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SUF = '_draft' if '--draft' in sys.argv else ''
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/hut11/out/hut{SUF}.blend')
C = json.load(open(f'/home/claude/hut11/out/hut_contract{SUF}.json'))
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'Glow_')):
        o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
lan = Vector(C['sockets']['Audio_Lantern']['pos'])
# the car (Unity -463.2, 22.9, 495.6) in the hut frame: invert the hut's placement
pl = C['meta']['map_placement']['TowerHut']
yaw = math.radians(pl['yawUnity'])
d_u = Vector((-463.2 - pl['p'][0], 22.9 + 1.4 - pl['p'][1], 495.6 - pl['p'][2]))     # eye 1.4 m over the road
x_l = d_u.x * math.cos(-yaw) + d_u.z * math.sin(-yaw)
z_l = -d_u.x * math.sin(-yaw) + d_u.z * math.cos(-yaw)
car = Vector((-x_l, -z_l, d_u.y))
print('car in the hut frame', tuple(round(v, 2) for v in car), 'distance', round((car - lan).length, 1))
for dz in (0.0, -0.05, 0.05):
    tgt = lan + Vector((0, 0, dz))
    d = (car - tgt)
    hit, loc, nrm, idx, ob, mw = sc.ray_cast(dg, tgt + d.normalized() * 0.09, d.normalized(), distance=d.length)
    print('  lantern -> car', dz, 'blocked by' if hit else 'clear', ob.name if hit else '')
# item spots: boxes of the item sizes must not cut the model
SIZES = {'Spot_Jerrycan': (0.40, 0.32, 0.54), 'Spot_Funnel': (0.26, 0.24, 0.31), 'Spot_Flashlight': (0.25, 0.06, 0.06),
         'Spot_Note': (0.15, 0.21, 0.004)}
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Glow_'))]
BV = {}
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    BV[o.name] = BVHTree.FromPolygons([M @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])


def box_bvh(c, s):
    x, y, z = c
    sx, sy, sz = s
    V = [Vector((x + a * sx / 2, y + b * sy / 2, z + 0.002 + (cc + 1) * sz / 2)) for a in (-1, 1) for b in (-1, 1) for cc in (-1, 1)]
    F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return BVHTree.FromPolygons(V, F)


for k, s in SIZES.items():
    b = box_bvh(C['sockets'][k]['pos'], s)
    hits = [n for n, t in BV.items() if t.overlap(b)]
    print(f'  {k:16s} at {C["sockets"][k]["pos"]}: {"clear" if not hits else "cuts " + ", ".join(hits)}')
# oil lamp head room, door head room
lamp = bpy.data.objects['Lamp_Oil']
lo = min((lamp.matrix_world @ v.co).z for v in lamp.data.vertices)
print('oil lamp bottom above the floor %.2f m' % (lo - 0.33))
cols = {c['name']: c for c in C['colliders']}
hd, fl, fr = cols['COL_Wall_F_Head'], cols['COL_Wall_F_L'], cols['COL_Wall_F_R']
print('door clear height %.3f m, width %.3f m' % (hd['center_hut'][2] - hd['size'][2] / 2 - 0.33,
      (fr['center_hut'][0] - fr['size'][0] / 2) - (fl['center_hut'][0] + fl['size'][0] / 2)))
# map placement vs Update 3
U3 = {'Hochsitz': ((-482.0, 28.9016, 412.0), 160.0), 'Sign_Forsthuette': ((-472.1541, 28.4632, 407.0647), 57.626),
      'TowerHut': ((-474.0, 28.3963, 404.0), 57.626)}                    # Forest_Layout.json (Update 3): p, yaw from q
for k, (v, yu) in U3.items():
    p = C['meta']['map_placement'][k]['p']
    yw = C['meta']['map_placement'][k]['yawUnity']
    print(f'  {k:16s} placement {p} yaw {yw}  Update 3 {v} yaw {yu}  diff {math.dist(p, v) * 1000:.1f} mm, {abs(yw - yu):.3f} deg')
