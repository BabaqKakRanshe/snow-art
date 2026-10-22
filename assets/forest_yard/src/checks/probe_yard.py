"""Yard-specific checks on out/yard.blend: the two roots' places vs Update 3 (Forest_Layout.json) and the Trafo's place
beside the tanks in the blend; the prologue's pump points vs Forest_Opening.json (the nozzle, the operator's spot, the yard's
jerrycan) and Update 3's lever / gate origins; the jerrycan's box (Item_Jerrycan20's collider) clear of the model at its
spot; the pump rule (the can within 0.45 m of the nozzle horizontally and at most 0.7 m below it).
python3 -I probe_yard.py <Forest_Data_dir> [<Forest_Models_dir>]"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

DATA = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else sys.argv[-2]
MODELS = sys.argv[2] if len(sys.argv) > 2 and os.path.isdir(sys.argv[2]) else os.path.join(os.path.dirname(DATA), 'Models')
LAY = json.load(open(os.path.join(DATA, 'Forest_Layout.json')))
OPN = json.load(open(os.path.join(DATA, 'Forest_Opening.json')))
C = json.load(open('/home/claude/uaz/out/yard_contract.json'))
S, Pp = C['sockets'], C['parts']


def yaw_u(q):
    return math.degrees(2 * math.atan2(q[1], q[3]))


U3 = {p['m']: p for p in LAY['prefabs'] if p['m'] in ('FuelTanks', 'Trafo')}


def to_root(p, root):
    r = U3[root]
    P0, TH = r['p'], math.radians(yaw_u(r['q']))
    dx, dy, dz = p[0] - P0[0], p[1] - P0[1], p[2] - P0[2]
    xl = dx * math.cos(TH) - dz * math.sin(TH)
    zl = dx * math.sin(TH) + dz * math.cos(TH)
    return Vector((-xl, -zl, dy))


print('== map placement vs Update 3')
for root in ('FuelTanks', 'Trafo'):
    mine = C['meta']['map_placement'][root]
    dp = (Vector(mine['p']) - Vector(U3[root]['p'])).length * 1000
    print(f"  {root:10s} Update 3 p {U3[root]['p']} yaw {yaw_u(U3[root]['q']):.3f} | contract p {mine['p']} yaw {mine['yawUnity']} | "
          f"diff {dp:.1f} mm")
rel = to_root(U3['Trafo']['p'], 'FuelTanks')
ryaw = yaw_u(U3['FuelTanks']['q']) - yaw_u(U3['Trafo']['q'])
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/yard.blend')
T = bpy.data.objects['Trafo'].matrix_world
print(f"  Trafo in the FuelTanks frame: Update 3 ({rel.x:.3f}, {rel.y:.3f}, {rel.z:.3f}) yaw {ryaw:.2f} | blend "
      f"({T.translation.x:.3f}, {T.translation.y:.3f}, {T.translation.z:.3f}) yaw {math.degrees(T.to_euler().z):.2f}")
print('== prologue points vs Forest_Opening.json')
pump = next(i for i in OPN['interactables'] if i.get('id') == 'Pump_FuelTanks')
can = next(i for i in OPN['items'] if i.get('id') == 'Jerrycan_Yard')
for lab, data, sock in (('nozzle', pump['nozzle'], 'Pump_Nozzle'), ('operatorPos', pump['operatorPos'], 'Stand_PumpOperator'),
                        ('Jerrycan_Yard', can['p'], 'Spot_Jerrycan')):
    u = to_root(data, 'FuelTanks')
    s = Vector(S[sock]['pos'])
    print(f'  {lab:14s} data {tuple(round(v, 3) for v in u)}  {sock} {tuple(round(v, 3) for v in s)}  diff {(u - s).length * 1000:.1f} mm')
cy = yaw_u(U3['FuelTanks']['q']) - yaw_u(can['q'])
print(f"  Jerrycan_Yard yaw in the frame {cy:.2f}  Spot_Jerrycan yaw {S['Spot_Jerrycan'].get('yaw')}")
for model, child in (('FuelTanks', 'IX_PumpLever_301'), ('Trafo', 'IX_TrafoGate_91')):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MODELS, model + '.fbx'))
    new = {o.name.split('.')[0]: o for o in set(bpy.data.objects) - before}
    bpy.context.view_layer.update()
    root_o = next(o for o in set(bpy.data.objects) - before if o.parent is None)
    ch = next(o for o in set(bpy.data.objects) - before if o.name.startswith(child))
    org = ch.matrix_world.translation.copy()          # the root stands at the origin: world = the prefab's frame
    mine = Vector(Pp[child]['pivot'])
    print(f'  {child:18s} Update 3 origin {tuple(round(v, 3) for v in org)}  ours {tuple(round(v, 3) for v in mine)}  '
          f'diff {(org - mine).length * 1000:.1f} mm')
    for o in set(bpy.data.objects) - before:
        bpy.data.objects.remove(o, do_unlink=True)
print('== the yard\'s jerrycan at its spot (Item_Jerrycan20 collider 0.355 x 0.52 x 0.175, centre 0.26 up)')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_') and o.name in Pp and
          Pp[o.name]['root'] == 'FuelTanks']
BV = {}
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    BV[o.name] = BVHTree.FromPolygons([M @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
sp = Vector(S['Spot_Jerrycan']['pos'])
a = math.radians(S['Spot_Jerrycan']['yaw'])
R = Matrix.Rotation(a, 3, 'Z')
hx, hy = 0.355 / 2, 0.175 / 2
V = [sp + R @ Vector((x, y, 0.0)) + Vector((0, 0, z)) for x in (-hx, hx) for y in (-hy, hy) for z in (0.002, 0.52)]
F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
box = BVHTree.FromPolygons(V, F)
hits = [n for n, t in BV.items() if t.overlap(box)]
print('  can body', 'clear' if not hits else 'cuts ' + ', '.join(hits))
cc = sp + Vector((0, 0, 0.26))
nz = Vector(S['Pump_Nozzle']['pos'])
print(f'  nozzle -> can collider centre: horizontal {math.hypot(cc.x - nz.x, cc.y - nz.y):.3f} m (<= 0.45), below '
      f'{nz.z - cc.z:.3f} m (<= 0.7)')
