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
def tree(ob, xform):
    me = ob.evaluated_get(DG).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(xform @ ob.matrix_world)
    bmesh.ops.triangulate(t, faces=t.faces[:]); return BVHTree.FromBMesh(t)
side, sg = 'L', 1
fl = O['Flap_L']; door = O['CargoDoor_L']
# door as a BVH at each t; flap BVH at each angle -> overlap test (BVH vs BVH)
dme = door.evaluated_get(DG).to_mesh()
for ang in (0, 5, 10, 15, 20, 25, 30, 35):
    R = fl.matrix_world @ Matrix.Rotation(math.radians(-ang), 4, 'X') @ fl.matrix_world.inverted()
    FT = tree(fl, R)
    first = None; mind = 9
    for k in range(0, 101):
        M = door_mat(k / 100, side)
        t = bmesh.new(); t.from_mesh(dme); t.transform(M @ door.matrix_world); bmesh.ops.triangulate(t, faces=t.faces[:])
        DT = BVHTree.FromBMesh(t)
        ov = DT.overlap(FT)
        # nearest distance from door verts to the flap
        for v in t.verts:
            loc, n, i, d = FT.find_nearest(v.co, 0.2)
            if loc is not None and d < mind: mind = d
        t.free()
        if ov and first is None:
            first = k / 100
    print(f'flap {ang:2d} deg: door path intersects the flap first at t = {first}; min door-flap distance {mind:.3f} m')
