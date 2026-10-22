"""Clearance of the sliding cargo doors along their path: door vertices vs the fuselage outer skin (aft of the opening),
the flaps (deflected 35 deg) and the wing; t = 0..1. Build frame."""
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v13.blend')
O = bpy.data.objects
DG = bpy.context.evaluated_depsgraph_get()
DJ = json.load(open('/home/claude/plane/out/doors_v13.json'))
def S3(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def S5(x): x = min(max(x, 0), 1); return x ** 3 * (10 - 15 * x + 6 * x * x)
def door_mat(t, side):
    d = DJ['doors'][side]; sg = 1 if side == 'L' else -1
    p = t / DJ['T_POP']
    of = DJ['D_OUT'] * S3(p / 0.75); orr = DJ['D_OUT'] * S3((p - 0.25) / 0.75)
    back = DJ['D_BACK'] * S5((t - DJ['T_SLIDE0']) / (1 - DJ['T_SLIDE0']))
    s = min(max((back - DJ['B_TUCK0']) / (DJ['D_BACK'] - DJ['B_TUCK0']), 0), 1); orr -= DJ['D_TUCK'] * s * s
    yaw = math.atan2(of - orr, d['length']); P = Vector(d['pivot'])
    return Matrix.Translation(P + Vector((sg * orr, back, 0))) @ Matrix.Rotation(sg * yaw, 4, 'Z') @ Matrix.Translation(-P)
def tree(names, xform=None):
    bm = bmesh.new()
    for n in names:
        ob = O[n]; me = ob.evaluated_get(DG).to_mesh(); t = bmesh.new(); t.from_mesh(me)
        t.transform(xform @ ob.matrix_world if xform is not None else ob.matrix_world)
        m = bpy.data.meshes.new('_t'); t.to_mesh(m); t.free(); bm.from_mesh(m)
    bmesh.ops.triangulate(bm, faces=bm.faces[:]); return BVHTree.FromBMesh(bm)
FUSE = tree(['src_Fuselage'])
# the door without the roller arms (M_Floor faces = arms and the arm-like parts; keep the rest)
res = {}
for side, sg in (('L', 1), ('R', -1)):
    door = O[f'CargoDoor_{side}']; me = door.data
    fl = [i for i, m in enumerate(me.materials) if m.name == 'M_Floor']
    arm_v = set()
    for p in me.polygons:
        if p.material_index in fl:
            arm_v.update(p.vertices)
    W = [door.matrix_world @ v.co for i, v in enumerate(me.vertices) if i not in arm_v]
    worst = (9, None, None)
    for k in range(0, 101):
        t = k / 100; M = door_mat(t, side)
        for q in W:
            p = M @ q
            if p.y < 0.50 or p.z < 1.0 or p.z > 2.6:     # only behind the opening (there the skin is closed)
                continue
            h = FUSE.ray_cast(Vector((sg * 1.6, p.y, p.z)), Vector((-sg, 0, 0)), 1.6)
            if h[0] is None:
                continue
            gap = sg * (p.x - h[0].x)
            if gap < worst[0]:
                worst = (gap, t, tuple(round(c, 3) for c in p))
    res[side] = worst
    print(side, 'min gap door-skin behind the opening', round(worst[0], 4), 'at t', worst[1], 'point', worst[2])
# flaps fully down (35 deg) vs the door top edge path
for side, sg in (('L', 1), ('R', -1)):
    fl = O[f'Flap_{side}']
    bb = [fl.matrix_world @ Vector(c) for c in fl.bound_box]
    print('Flap', side, 'bbox x', round(min(b.x for b in bb), 3), round(max(b.x for b in bb), 3), 'y', round(min(b.y for b in bb), 3),
          round(max(b.y for b in bb), 3), 'z', round(min(b.z for b in bb), 3), round(max(b.z for b in bb), 3))
    door = O[f'CargoDoor_{side}']
    dz = [ (door.matrix_world @ v.co).z for v in door.data.vertices]
    print('door', side, 'z range', round(min(dz), 3), round(max(dz), 3))
# the flap hinge: rotate the flap about its local X by -35 deg (contract: 0 .. -35, down = negative) and test the door
for side, sg in (('L', 1), ('R', -1)):
    fl = O[f'Flap_{side}']
    R = fl.matrix_world @ Matrix.Rotation(math.radians(-35), 4, 'X') @ fl.matrix_world.inverted()
    FT = tree([f'Flap_{side}'], R)
    door = O[f'CargoDoor_{side}']
    W = [door.matrix_world @ v.co for v in door.data.vertices]
    hit = None
    for k in range(0, 101):
        M = door_mat(k / 100, side)
        for q in W:
            p = M @ q
            loc, n, i, dist = FT.find_nearest(p, 0.03)
            if loc is not None:
                hit = (k / 100, round(dist, 4), tuple(round(c, 3) for c in p)); break
        if hit: break
    fb = [R @ fl.matrix_world @ Vector(c) for c in fl.bound_box]
    print('flap', side, 'at -35: z min', round(min(b.z for b in fb), 3), 'x', round(min(abs(b.x) for b in fb), 3), '| door within 3 cm of the flap:', hit)
