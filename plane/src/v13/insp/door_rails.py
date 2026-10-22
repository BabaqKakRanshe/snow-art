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
def bm_of(ob, X=None):
    me = ob.evaluated_get(DG).to_mesh(); t = bmesh.new(); t.from_mesh(me)
    t.transform((X if X is not None else Matrix()) @ ob.matrix_world); bmesh.ops.triangulate(t, faces=t.faces[:]); return t
rails = bm_of(O['src_DoorRails']); RT = BVHTree.FromBMesh(rails)
fuse = bm_of(O['src_Fuselage']); FT = BVHTree.FromBMesh(fuse)
for side in ('L', 'R'):
    door = O[f'CargoDoor_{side}']
    me = door.data
    fl = [i for i, m in enumerate(me.materials) if m.name == 'M_Floor']
    hits_r, hits_f = [], []
    for k in range(0, 101):
        t = k / 100
        b = bm_of(door, door_mat(t, side))
        # split: arms (M_Floor) vs panel
        arm = bmesh.new(); pan = bmesh.new()
        for tgt, keep in ((arm, True), (pan, False)):
            c = b.copy()
            bmesh.ops.delete(c, geom=[f for f in c.faces if (f.material_index in fl) != keep], context='FACES')
            tgt.free(); 
            if keep: arm = c
            else: pan = c
        PT = BVHTree.FromBMesh(pan); AT = BVHTree.FromBMesh(arm)
        if PT.overlap(RT): hits_r.append(('panel', t, len(PT.overlap(RT))))
        if PT.overlap(FT) and t > 0.0: hits_f.append(('panel-fuse', t, len(PT.overlap(FT))))
        if AT.overlap(FT) and t > 0.0: hits_f.append(('arm-fuse', t, len(AT.overlap(FT))))
        b.free(); arm.free(); pan.free()
    print(side, 'panel x rails overlaps (t, tris):', [(h[1], h[2]) for h in hits_r][:12], '... n', len(hits_r))
    pf = [h for h in hits_f if h[0] == 'panel-fuse']; af = [h for h in hits_f if h[0] == 'arm-fuse']
    print(side, 'panel x fuselage overlaps at t:', [h[1] for h in pf][:40], 'n', len(pf))
    print(side, 'arms x fuselage overlaps at t:', [h[1] for h in af][:40], 'n', len(af))
