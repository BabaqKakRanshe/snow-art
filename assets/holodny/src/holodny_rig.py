"""Holodny: the developer's Meshy model (A-pose, docs/gdd/monsters/01_holodny/model_v2/model.glb) on a 45-bone
skeleton + the first clips on all fours (docs/gdd/monsters/01_holodny/QUESTIONS.md, answers 29.10).

The mesh comes normalised (~0.95 m): scaled to 2.2 m upright, feet on the ground, face to -y (Blender: x = his left,
y back, z up - as the Lesnik). UV seams are welded (one island after it), joints are measured on mesh slices, the
weights are bone heat + rules (skull rigid to Head, the lower jaw to Jaw).

Posing is done here, not by Blender's IK: every frame a pose (hips, spine bends, head, where each palm and sole
stands on the ground) is solved in plain maths - two-bone IK with a pole for each limb, the hand / foot oriented by its
contact - and written straight into the bones' keys. Planted palms and soles therefore stay exactly where the pose puts
them (no bake, no slide). Clips are in place; the game moves him (cycle lengths in Holodny.json).

Run: blender -b --factory-startup --python holodny_rig.py -- <model.glb> <out_dir> [--render]
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector, Matrix, Quaternion

ARGS = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
RENDER = '--render' in ARGS
os.makedirs(os.path.join(OUT, 'tex'), exist_ok=True)
T0 = time.time()
FPS = 24
HEIGHT = 2.2
INFO = {}
SIDES = (('L', 1), ('R', -1))
Z = Vector((0, 0, 1))


def log(*a):
    print('[holodny_rig %5.1fs]' % (time.time() - T0), *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS

# ------------------------------------------------------------------ the mesh
bpy.ops.import_scene.gltf(filepath=GLB)
ob = next(o for o in sc.objects if o.type == 'MESH')
for o in list(sc.objects):
    if o is not ob:
        bpy.data.objects.remove(o, do_unlink=True)
mw = ob.matrix_world.copy()
ob.parent = None
ob.data.transform(mw)
ob.matrix_world = Matrix.Identity(4)
zs = [v.co.z for v in ob.data.vertices]
S = HEIGHT / (max(zs) - min(zs))
ob.data.transform(Matrix.Translation((0, 0, -min(zs) * S)) @ Matrix.Scale(S, 4))
ob.name = ob.data.name = 'Holodny_Body'
bm = bmesh.new()
bm.from_mesh(ob.data)
n0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
bm.to_mesh(ob.data)
bm.free()
for p in ob.data.polygons:
    p.use_smooth = True
me = ob.data
INFO['verts'] = {'imported': n0, 'welded': len(me.vertices)}
INFO['tris'] = sum(len(p.vertices) - 2 for p in me.polygons)
INFO['scale_from_glb'] = round(S, 4)
log('mesh', INFO['verts'], 'tris', INFO['tris'])

m = ob.active_material
m.name = 'M_Holodny'
for n in m.node_tree.nodes:
    if n.type != 'TEX_IMAGE' or not n.image:
        continue
    to = [l.to_node for l in n.outputs[0].links]
    kind = 'A'
    if any(t.type == 'NORMAL_MAP' for t in to):
        kind = 'N'
    elif any(t.type in ('SEPARATE_COLOR', 'SEPRGB', 'SEPARATE_RGB') for t in to):
        kind = 'MR'
    img = n.image
    img.name = f'T_Holodny_{kind}'
    data = bytes(img.packed_file.data)
    ext = '.png' if data[:4] == b'\x89PNG' else '.jpg'
    with open(os.path.join(OUT, 'tex', f'T_Holodny_{kind}{ext}'), 'wb') as fh:
        fh.write(data)
INFO['textures'] = sorted(i.name for i in bpy.data.images)

# ------------------------------------------------------------------ joints, measured on this mesh (29.10)
V = [v.co.copy() for v in me.vertices]


def slice_c(z, x0, x1, y0=-1.0, y1=1.0, dz=0.008):
    P = [p for p in V if abs(p.z - z) < dz and x0 < p.x < x1 and y0 < p.y < y1]
    return sum(P, Vector()) / len(P)


def comps(sel):
    """connected pieces of the vertex set sel (indices), through the mesh edges"""
    nb = {i: [] for i in sel}
    for e in me.edges:
        a, b = e.vertices
        if a in nb and b in nb:
            nb[a].append(b)
            nb[b].append(a)
    seen, out = set(), []
    for i in sel:
        if i in seen:
            continue
        st, cur = [i], []
        seen.add(i)
        while st:
            k = st.pop()
            cur.append(k)
            for j in nb[k]:
                if j not in seen:
                    seen.add(j)
                    st.append(j)
        out.append(cur)
    return out


J = {}
J['Hips'] = Vector((0, 0.07, 1.12))
J['Spine'] = Vector((0, 0.07, 1.30))
J['Spine2'] = Vector((0, 0.065, 1.46))
J['Chest'] = Vector((0, 0.06, 1.62))
J['Neck1'] = Vector((0, 0.035, 1.78))
J['Neck2'] = Vector((0, 0.02, 1.885))
J['Head'] = Vector((0, 0.01, 1.99))
J['HeadTop'] = Vector((0, 0.0, 2.2))
J['Jaw'] = Vector((0, -0.01, 2.01))
J['Chin'] = Vector((0, -0.105, 1.94))
L = {}                                                   # left side; the right one is mirrored (the mesh is symmetric)
L['clav'] = Vector((0.03, 0.045, 1.76))
L['shoulder'] = Vector((0.175, 0.035, 1.75))
L['elbow'] = slice_c(1.375, 0.18, 0.45)
L['wrist'] = slice_c(0.824, 0.30, 0.55)
L['hip'] = Vector((0.09, 0.06, 1.14))
L['knee'] = slice_c(0.75, 0.04, 0.30)
L['ankle'] = slice_c(0.15, 0.04, 0.35) + Vector((0, -0.01, -0.045))
toe_i = min((i for i, p in enumerate(V) if p.x > 0.08 and p.z < 0.06), key=lambda i: V[i].y)
L['toe'] = V[toe_i].copy()
L['ball'] = Vector((L['toe'].x - 0.025, L['toe'].y + 0.085, 0.03))
# fingers: the pieces of the mesh below the palm; the short one high up is the thumb
CUT = 0.62
fing = []
for c in comps([i for i, p in enumerate(V) if p.z < CUT and p.x > 0.30]):
    top = max((V[i] for i in c), key=lambda p: p.z)
    tip = min((V[i] for i in c), key=lambda p: p.z)
    fing.append((len(c), top, tip))
fing.sort(key=lambda f: -f[0])
four = sorted(fing[:4], key=lambda f: f[1].y)            # index (front) .. pinky (back)
FNAMES = ['Index', 'Middle', 'Ring', 'Pinky']
L['fingers'] = {}
for nm, (_, top, tip) in zip(FNAMES, four):
    d = (top - tip).normalized()
    base = top + d * ((0.655 - top.z) / max(d.z, 0.3))   # up the finger's line to the knuckle line
    L['fingers'][nm] = (base, base.lerp(tip, 0.5), tip)
th = fing[4][2] if len(fing) > 4 else Vector((0.347, -0.076, 0.595))
th_base = Vector((0.37, -0.06, 0.75))
L['fingers']['Thumb'] = (th_base, th_base.lerp(th, 0.5), th.copy())
L['knuck'] = sum((L['fingers'][n][0] for n in FNAMES), Vector()) / 4
INFO['joints_L'] = {k: [round(c, 3) for c in v] for k, v in L.items() if isinstance(v, Vector)}
INFO['fingers_L'] = {k: [[round(c, 3) for c in p] for p in v] for k, v in L['fingers'].items()}
log('joints', INFO['joints_L'])

# the eye sockets (the glow points HolodnyLook puts in them, 30.10): rays from the front over the left orbit; the socket is
# every cell deeper than SOCKET_DEPTH (the brow and the cheek are ~2 cm nearer), its centre the mean, the glow a little in
# front of its floor so the bone hides it from the side. Right = mirrored. Measured 30.10: x 0.0385, z 2.0745, 3 cm across.
from mathutils.bvhtree import BVHTree
SOCKET_DEPTH = -0.09
_bm = bmesh.new()
_bm.from_mesh(me)
_tree = BVHTree.FromBMesh(_bm)
_sock = []
for iz in range(41):
    for ix in range(21):
        x, z = 0.016 + ix * 0.002, 2.035 + iz * 0.002
        hit = _tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
        if hit[0] is not None and hit[0].y >= SOCKET_DEPTH:
            _sock.append((x, z))
if _sock:
    sx = sum(c[0] for c in _sock) / len(_sock)
    sz = sum(c[1] for c in _sock) / len(_sock)
    floor = _tree.ray_cast(Vector((sx, -1.0, sz)), Vector((0, 1, 0)), 2.0)[0]
    INFO['eye_socket_L'] = [round(sx, 4), round((floor.y if floor else -0.08) - 0.008, 4), round(sz, 4)]
    INFO['eye_socket_across'] = round(max(c[0] for c in _sock) - min(c[0] for c in _sock), 4)
_bm.free()
log('eye socket', INFO.get('eye_socket_L'), INFO.get('eye_socket_across'))


def mir(v, sx):
    return Vector((v.x * sx, v.y, v.z))


# ------------------------------------------------------------------ the skeleton
B = {
    'Root': (Vector((0, 0, 0)), Vector((0, 0.15, 0)), None),
    'Hips': (J['Hips'], J['Spine'], 'Root'),
    'Spine': (J['Spine'], J['Spine2'], 'Hips'),
    'Spine2': (J['Spine2'], J['Chest'], 'Spine'),
    'Chest': (J['Chest'], J['Neck1'], 'Spine2'),
    'Neck1': (J['Neck1'], J['Neck2'], 'Chest'),
    'Neck2': (J['Neck2'], J['Head'], 'Neck1'),
    'Head': (J['Head'], J['HeadTop'], 'Neck2'),
    'Jaw': (J['Jaw'], J['Chin'], 'Head'),
}
for s, sx in SIDES:
    B[f'Shoulder.{s}'] = (mir(L['clav'], sx), mir(L['shoulder'], sx), 'Chest')
    B[f'UpperArm.{s}'] = (mir(L['shoulder'], sx), mir(L['elbow'], sx), f'Shoulder.{s}')
    B[f'ForeArm.{s}'] = (mir(L['elbow'], sx), mir(L['wrist'], sx), f'UpperArm.{s}')
    B[f'Hand.{s}'] = (mir(L['wrist'], sx), mir(L['knuck'], sx), f'ForeArm.{s}')
    for nm, (a, b, c) in L['fingers'].items():
        B[f'{nm}1.{s}'] = (mir(a, sx), mir(b, sx), f'Hand.{s}')
        B[f'{nm}2.{s}'] = (mir(b, sx), mir(c, sx), f'{nm}1.{s}')
    B[f'Thigh.{s}'] = (mir(L['hip'], sx), mir(L['knee'], sx), 'Hips')
    B[f'Shin.{s}'] = (mir(L['knee'], sx), mir(L['ankle'], sx), f'Thigh.{s}')
    B[f'Foot.{s}'] = (mir(L['ankle'], sx), mir(L['ball'], sx), f'Shin.{s}')
    B[f'Toe.{s}'] = (mir(L['ball'], sx), mir(L['toe'], sx), f'Foot.{s}')

arm_d = bpy.data.armatures.new('Holodny_Rig')
arm = bpy.data.objects.new('Holodny_Rig', arm_d)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in B.items():
    eb = arm_d.edit_bones.new(name)
    eb.head, eb.tail, eb.roll = h, t, 0.0
    eb.use_deform = name != 'Root'
for name, (h, t, par) in B.items():
    if par:
        eb = arm_d.edit_bones[name]
        eb.parent = arm_d.edit_bones[par]
        eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
INFO['bones'] = list(B)
log('bones', len(B))

# ------------------------------------------------------------------ weights: bone heat, then the rules
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
gi = {g.name: g.index for g in ob.vertex_groups}
gname = {g.index: g.name for g in ob.vertex_groups}
for n in B:
    if n != 'Root' and n not in gi:
        g = ob.vertex_groups.new(name=n)
        gi[n], gname[g.index] = g.index, n


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


SEG = {n: (h, t) for n, (h, t, par) in B.items() if n != 'Root'}


def is_jaw(p):
    """the lower jaw and its teeth (the mouth is open on the model: lower teeth under z 1.99)"""
    if p.y > -0.03 or p.z < 1.915:
        return False
    if p.z < 1.99:
        return True
    return p.z < 2.025 and abs(p.x) > 0.045 and p.y > -0.075      # the jaw's back branches up to the hinge


empty = fixed = 0
for v in me.vertices:
    w = {gname[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
    p = v.co
    if not w:
        empty += 1
        w = {min(SEG, key=lambda n: seg_dist(p, *SEG[n])): 1.0}
    if is_jaw(p):
        w = {'Jaw': 1.0}
        fixed += 1
    elif p.z > 1.995 or (p.z > 1.95 and p.y < -0.03):              # skull, upper teeth: rigid
        w = {'Head': 1.0}
        fixed += 1
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    tot = sum(x for _, x in top) or 1.0
    for g in list(v.groups):
        ob.vertex_groups[g.group].remove([v.index])
    for n, x in top:
        ob.vertex_groups[gi[n]].add([v.index], x / tot, 'REPLACE')
INFO['weights'] = {'heat_empty_to_nearest': empty, 'rule_fixed': fixed}
log('weights', INFO['weights'])

# ------------------------------------------------------------------ the pose solver (plain maths)
pb = arm.pose.bones
for b in pb:
    b.rotation_mode = 'QUATERNION'
REST = {b.name: b.matrix_local.copy() for b in arm_d.bones}
RR = {n: M.to_3x3() for n, M in REST.items()}
PAR = {b.name: (b.parent.name if b.parent else None) for b in arm_d.bones}
ORDER = list(B)                                           # parents first


def rot(flex=0.0, side=0.0, twist=0.0):
    """degrees, about the rest axes: flex + tips the top forward (-y), side + leans to his left (+x), twist + turns
    the front to his left"""
    return (Matrix.Rotation(math.radians(twist), 3, 'Z') @ Matrix.Rotation(math.radians(flex), 3, 'X') @
            Matrix.Rotation(math.radians(side), 3, 'Y'))


def frame(d, s):
    d = d.normalized()
    s = (s - d * s.dot(d)).normalized()
    return Matrix((d, s, d.cross(s))).transposed()


def fmap(d0, s0, d1, s1):
    return frame(d1, s1) @ frame(d0, s0).transposed()


def twist_angle(q, axis):
    """the twist part of rotation q about axis (radians, signed)"""
    v = Vector((q.x, q.y, q.z))
    pr = axis * v.dot(axis)
    t = Quaternion((q.w, pr.x, pr.y, pr.z))
    if t.magnitude < 1e-9:
        return 0.0
    t.normalize()
    a = 2 * math.acos(max(-1.0, min(1.0, t.w)))
    if Vector((t.x, t.y, t.z)).dot(axis) < 0:
        a = -a
    return a - 2 * math.pi if a > math.pi else a


def rhead(n):
    return REST[n].translation


def rtail(n):
    return B[n][1]


# the rest limbs
LIMB = {}
for s, sx in SIDES:
    for kind, a, b, c, pole0 in (('arm', f'UpperArm.{s}', f'ForeArm.{s}', f'Hand.{s}', Vector((0, 1, 0))),
                                 ('leg', f'Thigh.{s}', f'Shin.{s}', f'Foot.{s}', Vector((0, -1, 0)))):
        A0, E0, W0 = rhead(a), rhead(b), rhead(c)
        ax = (W0 - A0).normalized()
        p0 = (E0 - A0) - ax * (E0 - A0).dot(ax)
        p0 = p0.normalized() if p0.length > 0.005 else pole0
        LIMB[(kind, s)] = dict(a=a, b=b, c=c, L1=(E0 - A0).length, L2=(W0 - E0).length,
                               u0=(E0 - A0).normalized(), l0=(W0 - E0).normalized(), h0=ax.cross(p0).normalized())
    hd = (rtail(f'Hand.{s}') - rhead(f'Hand.{s}')).normalized()
    spread = (B[f'Pinky1.{s}'][0] - B[f'Index1.{s}'][0])
    palm = -sx * hd.cross(spread).normalized()           # the inner face of the hand, at rest
    LIMB[('hand', s)] = dict(d=hd, s=spread.normalized(), palm=palm,
                             C0=rhead(f'Hand.{s}').lerp(rtail(f'Hand.{s}'), 0.85))   # contact: the palm under the knuckles
    LIMB[('foot', s)] = dict(C0=rhead(f'Toe.{s}').copy())                             # contact: the ball
INFO['limbs_m'] = {f'{k}.{s}': [round(v['L1'], 3), round(v['L2'], 3)] for (k, s), v in LIMB.items() if k in ('arm', 'leg')}
OVER = {'max_m': 0.0, 'where': ''}


def solve2(lm, A, T, pole):
    """two-bone IK: world deltas of the upper and the lower bone so the chain runs A -> T, bending toward pole"""
    L1, L2 = lm['L1'], lm['L2']
    dv = T - A
    d = dv.length
    hi = (L1 + L2) * 0.9995
    if d > hi and d - hi > OVER['max_m']:
        OVER['max_m'], OVER['where'] = d - hi, lm['c']
    d = max(abs(L1 - L2) + 1e-4, min(hi, d))
    ax = dv.normalized()
    p = pole - ax * pole.dot(ax)
    p = p.normalized() if p.length > 1e-6 else Vector((0, 1, 0))
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    E = A + ax * a + p * h
    Tn = A + ax * d
    hinge = ax.cross(p).normalized()
    return fmap(lm['u0'], lm['h0'], (E - A).normalized(), hinge), fmap(lm['l0'], lm['h0'], (Tn - E).normalized(), hinge)


def hand_D(s, yaw, pitch, roll=0.0):
    """a palm flat on the ground: the hand points forward turned yaw deg out (+ = away from the body), its line pitch
    deg below level (the wrist up), roll deg about its line (+ = the thumb side up)"""
    sx = 1 if s == 'L' else -1
    f = Vector((math.sin(math.radians(yaw)) * sx, -math.cos(math.radians(yaw)), 0))
    d = f * math.cos(math.radians(pitch)) - Z * math.sin(math.radians(pitch))
    lat = Z.cross(f) * sx
    lat = Matrix.Rotation(math.radians(roll) * -sx, 3, d) @ lat
    H = LIMB[('hand', s)]
    return fmap(H['d'], H['s'], d, lat)


def foot_D(s, yaw, pitch=0.0):
    """the rest foot (flat) turned yaw deg out, then pitch deg about its side axis (+ = the heel up / the toes down)"""
    sx = 1 if s == 'L' else -1
    R = Matrix.Rotation(math.radians(-yaw * sx), 3, 'Z')
    return Matrix.Rotation(math.radians(pitch), 3, R @ Vector((1, 0, 0))) @ R


def bone_curl(D_par, s, deg, hand=True):
    """a finger bone bent deg toward the palm (+) from its parent"""
    H = LIMB[('hand', s)]
    d = D_par @ H['d']
    ax = d.cross(D_par @ H['palm']).normalized()
    return Matrix.Rotation(math.radians(deg), 3, ax) @ D_par


def solve(P):
    """P: the pose (see stance()). Returns {bone: (world delta 3x3, head)}"""
    D, Hd = {}, {}
    M = {}

    def place(n, Dn, head=None):
        par = PAR[n]
        if head is None:
            Mp = M[par] if par else REST[par]
            head = (Mp @ REST[par].inverted() @ REST[n].translation.to_4d()).to_3d()
        D[n], Hd[n] = Dn, head
        Mn = (Dn @ RR[n]).to_4x4()
        Mn.translation = head
        M[n] = Mn

    M['Root'] = REST['Root'].copy()
    D['Root'], Hd['Root'] = Matrix.Identity(3), REST['Root'].translation.copy()
    place('Hips', rot(*P['hips_rot']), P['hips'])
    Dc = D['Hips']
    for n, r in zip(('Spine', 'Spine2', 'Chest'), P['spine']):
        Dc = Dc @ rot(*r)
        place(n, Dc)
    Dn_ = D['Chest']
    for n, r in zip(('Neck1', 'Neck2'), P['neck']):
        Dn_ = Dn_ @ rot(*r)
        place(n, Dn_)
    yaw, pitch, roll = P['head']
    place('Head', rot(pitch, roll, yaw))
    place('Jaw', D['Head'] @ rot(P['jaw']))                  # + opens the mouth
    for s, sx in SIDES:
        f_, u_ = P['shoulder'][s]
        place(f'Shoulder.{s}', D['Chest'] @ rot(0, -u_ * sx, -f_ * sx))   # f_ + forward, u_ + up
        # arm: the wrist from the palm's contact point and the hand's turn
        hs = P['hands'][s]
        H = LIMB[('hand', s)]
        Dh = hs['D']
        wrist = hs['C'] - Dh @ (H['C0'] - rhead(f'Hand.{s}'))
        lm = LIMB[('arm', s)]
        place(f'UpperArm.{s}', Matrix.Identity(3))
        A = Hd[f'UpperArm.{s}']
        Du, Dl = solve2(lm, A, wrist, hs['pole'])
        place(f'UpperArm.{s}', Du)
        tw = twist_angle((Dl.inverted() @ Dh).to_quaternion(), lm['l0'])
        place(f'ForeArm.{s}', Dl @ Matrix.Rotation(0.5 * tw, 3, lm['l0']))
        place(f'Hand.{s}', Dh)
        for nm in ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb'):
            c1, c2 = hs['fingers'] if nm != 'Thumb' else hs['thumb']
            place(f'{nm}1.{s}', bone_curl(Dh, s, c1))
            place(f'{nm}2.{s}', bone_curl(D[f'{nm}1.{s}'], s, c2))
        # leg: the ankle from the ball's contact point and the foot's turn
        fs = P['feet'][s]
        Df = fs['D']
        ankle = fs['C'] - Df @ (LIMB[('foot', s)]['C0'] - rhead(f'Foot.{s}'))
        lm = LIMB[('leg', s)]
        place(f'Thigh.{s}', Matrix.Identity(3))
        Dt, Ds = solve2(lm, Hd[f'Thigh.{s}'], ankle, fs['pole'])
        place(f'Thigh.{s}', Dt)
        place(f'Shin.{s}', Ds)
        place(f'Foot.{s}', Df)
        place(f'Toe.{s}', fs.get('toeD', Df))
    return M


def apply(M):
    for n in ORDER:
        if n == 'Root':
            continue
        par = PAR[n]
        Mp = M[par]
        basis = (REST[par].inverted() @ REST[n]).inverted() @ Mp.inverted() @ M[n]
        loc, q, _ = basis.decompose()
        pb[n].rotation_quaternion = q
        pb[n].location = loc


def key_all(frame):
    for b in pb:
        b.keyframe_insert('rotation_quaternion', frame=frame)
        b.keyframe_insert('location', frame=frame)


def mesh_points():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    out = [ob.matrix_world @ v.co for v in m2.vertices]
    e.to_mesh_clear()
    return out


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ the stance on all fours
# side view (the turnaround sheet, refs\ref_user.png): palms flat ahead of the shoulders, arms nearly straight, elbows
# back and a little out; the back rising from the hips to the shoulders (shoulders higher - answer 2), knees bent
# forward and out, soles flat behind them; the long neck forward, the skull low and level, looking ahead.
# 30.10 v2 (user: "слишком человеческий, медленный, скованный"): spider-like - the body lower, the feet wide with the
# knees out and up past the elbows, the palms wide and turned out, the elbows out (the "spider crawl" pose)
ST = dict(hips=Vector((0, 0.42, 0.64)), hips_rot=(64, 0, 0),
          spine=[(4, 0, 0), (2, 0, 0), (0, 0, 0)],
          neck=[(22, 0, 0), (14, 0, 0)], head=(0, 2, 0), jaw=0.0,
          hand_x=0.16, hand_y=-0.30, hand_yaw=32, hand_pitch=12,
          foot_x=0.40, foot_y=0.12, foot_yaw=34,
          elbow_pole=(0.75, 0.8, 0.35), knee_pole=(1.0, -0.45, 0.35))
GROUND = {'hand': 0.0, 'foot': 0.0}                      # contact heights, set by the ground calibration


def body_M(P):
    """the body's pose matrices for this pose with the limbs not solved (where the shoulders and hips land)"""
    Q = dict(P)
    Q.setdefault('shoulder', {'L': (0, 0), 'R': (0, 0)})
    Q['hands'] = {s: dict(C=Vector((0, 0, 0)), D=Matrix.Identity(3), pole=Vector((0, 1, 0)),
                          fingers=(0, 0), thumb=(0, 0)) for s, _ in SIDES}
    Q['feet'] = {s: dict(C=Vector((0, 0, 0)), D=Matrix.Identity(3), pole=Vector((0, -1, 0))) for s, _ in SIDES}
    keep = dict(OVER)
    M = solve(Q)
    OVER.update(keep)                                    # the dummy limbs' reach does not count
    return M


_ANCH = {}


def anchors(over):
    """the planted contact points of a clip: from the stance with the clip's constant changes (over), NOT from the
    swaying body of each frame - so a planted palm or sole stays put while the body moves over it"""
    key = repr(sorted((k, tuple(v) if isinstance(v, Vector) else v) for k, v in over.items()))
    if key not in _ANCH:
        P = dict(ST)
        P.update(over)
        M = body_M(P)
        out = {}
        for s, sx in SIDES:
            sh, hp = M[f'UpperArm.{s}'].translation, M[f'Thigh.{s}'].translation
            out[('hand', s)] = Vector((sh.x + sx * P['hand_x'], sh.y + P['hand_y'], GROUND['hand']))
            out[('foot', s)] = Vector((sx * P['foot_x'], hp.y + P['foot_y'], GROUND['foot']))
        _ANCH[key] = out
    return _ANCH[key]


def stance(o=None):
    """the pose on all fours; o overrides fields (anchor = the clip's constant changes that move the planted points).
    Hands/feet: their planted contact points + offsets (hand_off / foot_off, in the air when z > 0)"""
    o = o or {}
    P = {k: (v.copy() if isinstance(v, Vector) else v) for k, v in ST.items()}
    P.update(o.get('anchor', {}))
    P.update({k: v for k, v in o.items() if k in ST})
    P['shoulder'] = o.get('shoulder', {'L': (0, 0), 'R': (0, 0)})
    an = anchors(o.get('anchor', {}))
    P['hands'], P['feet'] = {}, {}
    for s, sx in SIDES:
        off = o.get('hand_off', {}).get(s, Vector())
        ep = P['elbow_pole']
        P['hands'][s] = dict(C=an[('hand', s)] + off,
                             D=o.get('hand_D', {}).get(s) or hand_D(s, P['hand_yaw'], P['hand_pitch'] + o.get('hand_pitch_add', {}).get(s, 0.0)),
                             pole=o.get('hand_pole', {}).get(s) or Vector((ep[0] * sx, ep[1], ep[2])),
                             fingers=o.get('fingers', {}).get(s, (-P['hand_pitch'] - 4, 10)),
                             thumb=(-P['hand_pitch'], 6))
        foff = o.get('foot_off', {}).get(s, Vector())
        fp = o.get('foot_pitch', {}).get(s, 0.0)
        kp = P['knee_pole']
        P['feet'][s] = dict(C=an[('foot', s)] + foff, D=foot_D(s, P['foot_yaw'], fp), pole=Vector((kp[0] * sx, kp[1], kp[2])),
                            toeD=foot_D(s, P['foot_yaw'], min(fp, 0.0) if foff.z < 0.01 else fp))
    return P


# ground calibration: the lowest point of each hand / foot on the ground (a few mm up)
arm.animation_data_create()
apply(solve(stance()))
pts = mesh_points()
grp_of = {}
for v in me.vertices:
    if v.groups:
        g = max(v.groups, key=lambda g: g.weight)
        grp_of[v.index] = gname[g.group]
low = {'hand': 9.0, 'foot': 9.0}
for i, p in enumerate(pts):
    n = grp_of.get(i, '')
    k = 'hand' if any(n.startswith(x) for x in ('Hand', 'Index', 'Middle', 'Ring', 'Pinky', 'Thumb')) else \
        'foot' if n.startswith(('Foot', 'Toe')) else None
    if k:
        low[k] = min(low[k], p.z)
GROUND['hand'] = 0.004 - low['hand']
GROUND['foot'] = 0.004 - low['foot']
_ANCH.clear()
INFO['ground_calibration'] = {k: round(v, 4) for k, v in GROUND.items()}
apply(solve(stance()))
pts = mesh_points()
INFO['stance'] = {'lowest_z': round(min(p.z for p in pts), 3), 'top_z': round(max(p.z for p in pts), 3),
                  'y': [round(min(p.y for p in pts), 3), round(max(p.y for p in pts), 3)]}
log('stance', INFO['stance'], 'ground', INFO['ground_calibration'], 'overreach', OVER)

# ------------------------------------------------------------------ clips
CLIPS = {}
TAU = 2 * math.pi


def new_action(name, frames, loop):
    a = bpy.data.actions.new(name)
    a.use_fake_user = True
    arm.animation_data.action = a
    CLIPS[name] = {'frames_blender': [1, frames], 'seconds': round((frames - 1) / FPS, 3), 'loop': loop}
    return a


def bake(name, frames, loop, pose_fn):
    new_action(name, frames, loop)
    OVER['max_m'] = 0.0
    for fr in range(1, frames + 1):
        apply(solve(pose_fn(fr - 1)))
        key_all(fr)
    CLIPS[name]['overreach_m'] = round(OVER['max_m'], 3)
    log('clip', name, frames, 'overreach', round(OVER['max_m'], 3), OVER['where'])


# Stand4: the pose itself
bake('Stand4', 2, True, lambda f: stance())

# Idle4 (4 s loop): breathing in the ribs, a slow weight shift, the skull still most of the time and then two sharp
# twitches (a snap to the side and back, a tilt), fingers flexing one by one on the ground
IDLE_F = 96


def idle_pose(f):
    t = f / IDLE_F
    br = math.sin(TAU * 2 * t)                              # two breaths a loop
    sway = math.sin(TAU * t)
    o = {'hips': ST['hips'] + Vector((0.012 * sway, 0.0, 0.006 * br)),
         'hips_rot': (ST['hips_rot'][0] + 0.8 * br, 1.5 * sway, 0),
         'spine': [(ST['spine'][0][0] - 1.2 * br, -0.8 * sway, 0), (ST['spine'][1][0] - 1.5 * br, -0.6 * sway, 0),
                   (ST['spine'][2][0], 0, 0)],
         'jaw': 3 + 3 * max(0.0, br)}
    # the head: still, then twitches (frames): snap 20 deg to his right at 30 (2 frames), hold, back at 52;
    # a tilt at 70-74 held to 86
    yaw = 0.0
    if 30 <= f < 52:
        yaw = -22 * smooth((f - 30) / 2)
    elif 52 <= f < 60:
        yaw = -22 * (1 - smooth((f - 52) / 8))
    roll = 0.0
    if 70 <= f < 90:
        roll = 18 * smooth((f - 70) / 3) * (1 - smooth((f - 84) / 6))
    o['head'] = (yaw, ST['head'][1] + 1.5 * br, roll)
    o['neck'] = [(ST['neck'][0][0], 0, yaw * 0.3), (ST['neck'][1][0], 0, yaw * 0.3)]
    o['shoulder'] = {'L': (0, 1.5 * br), 'R': (0, 1.5 * br)}
    o['fingers'] = {}
    for s, sx in SIDES:
        k = 0.5 + 0.5 * math.sin(TAU * (t * 2 + (0.0 if s == 'L' else 0.37)))
        o['fingers'][s] = (-ST['hand_pitch'] - 4 - 10 * k ** 4, 10 + 25 * k ** 4)
    return stance(o)


bake('Idle4', IDLE_F + 1, True, idle_pose)


# the gait engine: each limb steps on its own phase; planted, its contact slides back under the body at the clip's
# ground speed (the game moves him forward at that speed, so nothing slides in the world)
def snap_swing(sw):
    """a jerky swing (30.10): the limb hesitates (first quarter), snaps across (next third), then settles"""
    if sw < 0.25:
        return 0.06 * sw / 0.25
    if sw < 0.6:
        return 0.06 + 0.88 * smooth((sw - 0.25) / 0.35)
    return 0.94 + 0.06 * smooth((sw - 0.6) / 0.4)


def gait(f, F, stride, duty, phases, lift, extra, snap=False):
    """f frame, F frames a cycle, stride m a cycle, duty of the cycle on the ground, phases {limb: 0..1} of touchdown,
    lift {kind: m}, extra(t) -> overrides for the body; snap: the jerky swing"""
    t = f / F
    o = extra(t)
    sweep = stride * duty
    o.setdefault('hand_off', {})
    o.setdefault('foot_off', {})
    o.setdefault('hand_pitch_add', {})
    o.setdefault('foot_pitch', {})
    o.setdefault('fingers', {})
    for (kind, s), ph in phases.items():
        u = (t - ph) % 1.0
        if u < duty:                                        # planted: from the front of its sweep to the back
            y = -sweep / 2 + sweep * (u / duty)
            z = 0.0
            sw = None
        else:
            sw = (u - duty) / (1 - duty)
            y = sweep / 2 - sweep * (snap_swing(sw) if snap else smooth(sw))
            z = lift[kind] * (math.sin(math.pi * min(1.0, sw * 1.25)) ** 0.6 if snap else math.sin(math.pi * sw) ** 0.8)
        if kind == 'hand':
            o['hand_off'][s] = Vector((0, y, z))
            if sw is not None:                              # in the air: the wrist leads, the fingers hang and curl
                o['hand_pitch_add'][s] = 18 * math.sin(math.pi * sw)
                o['fingers'][s] = (-ST['hand_pitch'] + 20 * math.sin(math.pi * sw), 10 + 30 * math.sin(math.pi * sw))
            elif u / duty > 0.8:                            # pushing off: the wrist rises over the knuckles
                k = (u / duty - 0.8) / 0.2
                o['hand_pitch_add'][s] = 25 * k
                o['fingers'][s] = (-ST['hand_pitch'] - 25 * k, 10)
        else:
            o['foot_off'][s] = Vector((0, y, z))
            if sw is not None:
                o['foot_pitch'][s] = 25 * math.sin(math.pi * sw)
            elif u / duty > 0.75:                           # the heel comes up over the ball
                o['foot_pitch'][s] = 30 * (u / duty - 0.75) / 0.25
    return stance(o)


# Sneak v2 (30.10): a quick, uneven crawl - lateral sequence with the right hand late, each limb hesitates and then
# snaps across; the body does not bob, it bends from side to side and twists over the planted limbs; the skull level.
SNEAK_F, SNEAK_STRIDE, SNEAK_DUTY = 28, 1.1, 0.62
SNEAK_ANCHOR = {'hips': ST['hips'] + Vector((0, 0, -0.03)), 'hand_y': -0.26}
SNEAK_PH = {('foot', 'L'): 0.0, ('hand', 'L'): 0.27, ('foot', 'R'): 0.5, ('hand', 'R'): 0.81}


def sneak_body(t):
    s1 = math.sin(TAU * t)
    c1 = math.cos(TAU * t)
    return {'anchor': SNEAK_ANCHOR,
            'hips': SNEAK_ANCHOR['hips'] + Vector((0.035 * s1, 0, 0.006 * math.sin(TAU * 2 * t))),
            'hips_rot': (ST['hips_rot'][0], 7 * s1, -8 * s1),
            'spine': [(ST['spine'][0][0], -6 * s1, 5 * s1), (ST['spine'][1][0], -5 * s1, 4 * s1), (ST['spine'][2][0], 4 * s1, -4 * s1)],
            'neck': [(ST['neck'][0][0], 0, 6 * s1), (ST['neck'][1][0], 0, 4 * s1)],
            'head': (0, ST['head'][1], 0),
            'shoulder': {'L': (7 * c1, 2 * s1), 'R': (-7 * c1, -2 * s1)}}


bake('Sneak', SNEAK_F + 1, True, lambda f: gait(f, SNEAK_F, SNEAK_STRIDE, SNEAK_DUTY, SNEAK_PH,
                                                 {'hand': 0.14, 'foot': 0.10}, sneak_body, snap=True))


# Run v2 (30.10): a low fast scuttle - diagonal pairs (left hind with right fore, then the others), each pair a hair
# apart, the limbs snapping across, the body flat and low, bending side to side; the jaw open, the skull forward.
RUN_F, RUN_STRIDE, RUN_DUTY = 10, 1.6, 0.45
RUN_PH = {('foot', 'L'): 0.0, ('hand', 'R'): 0.03, ('foot', 'R'): 0.5, ('hand', 'L'): 0.53}
RUN_ANCHOR = {'hips': ST['hips'] + Vector((0, 0, -0.05)), 'hand_y': -0.24, 'foot_y': 0.08}


def run_body(t):
    s1 = math.sin(TAU * t)
    return {'anchor': RUN_ANCHOR,
            'hips': RUN_ANCHOR['hips'] + Vector((0.025 * s1, 0, 0.008 * math.cos(TAU * 2 * t))),
            'hips_rot': (ST['hips_rot'][0] + 2, 6 * s1, -7 * s1),
            'spine': [(ST['spine'][0][0], -5 * s1, 4 * s1), (ST['spine'][1][0], -4 * s1, 3 * s1), (ST['spine'][2][0] - 2, 3 * s1, -3 * s1)],
            'neck': [(ST['neck'][0][0] - 4, 0, 4 * s1), (ST['neck'][1][0], 0, 2 * s1)],
            'head': (0, ST['head'][1] - 4, 0), 'jaw': 16.0,
            'shoulder': {'L': (6 * s1, 0), 'R': (-6 * s1, 0)}}


bake('Run', RUN_F + 1, True, lambda f: gait(f, RUN_F, RUN_STRIDE, RUN_DUTY, RUN_PH, {'hand': 0.13, 'foot': 0.11}, run_body, snap=True))
CYCLE = {'Sneak': {'cycle_m': SNEAK_STRIDE, 'speed_mps': round(SNEAK_STRIDE * FPS / SNEAK_F, 3)},
         'Run': {'cycle_m': RUN_STRIDE, 'speed_mps': round(RUN_STRIDE * FPS / RUN_F, 3)}}
# Listen: freezes - the breath stops, the skull snaps to his left and tilts (3 frames), holds dead still, a second
# small tilt, then slowly back. The game turns the whole body to the sound; this is the head's part.
LISTEN_F = 72


def listen_pose(f):
    k = smooth((f - 4) / 3) * (1 - smooth((f - 58) / 12))
    k2 = smooth((f - 40) / 2) * (1 - smooth((f - 58) / 12))
    yaw, roll = 45 * k, 15 * k + 8 * k2
    return stance({'head': (yaw, ST['head'][1] - 6 * k, roll), 'jaw': -2 * k,
                   'neck': [(ST['neck'][0][0], 0, yaw * 0.25), (ST['neck'][1][0], 0, yaw * 0.25)],
                   'spine': [ST['spine'][0], ST['spine'][1], (ST['spine'][2][0], 0, 6 * k)],
                   'fingers': {s_: (-ST['hand_pitch'] - 4 - 6 * k, 10 + 14 * k) for s_, _ in SIDES}})


bake('Listen', LISTEN_F + 1, False, listen_pose)


# Upright: he stands where his feet were on all fours (the clips share one origin: the middle of the body on all
# fours - standing, he is ~0.4 m behind it). Hunched, the long neck forward, the arms hanging to the shins.
def upright(o=None):
    o = o or {}
    an = anchors({})
    ball0 = rhead('Toe.L')
    P = {'hips': Vector((0, an[('foot', 'L')].y + (rhead('Hips').y - ball0.y), 1.08)) + o.get('hips_add', Vector()),
         'hips_rot': (6, 0, 0), 'spine': [(5, 0, 0), (5, 0, 0), (4, 0, 0)], 'neck': [(10, 0, 0), (8, 0, 0)],
         'head': (0, 4, 0), 'jaw': 0.0, 'shoulder': o.get('shoulder', {'L': (0, 0), 'R': (0, 0)})}
    P.update({k: v for k, v in o.items() if k in ('hips_rot', 'spine', 'neck', 'head', 'jaw')})
    M = body_M(P)
    P['hands'], P['feet'] = {}, {}
    for s, sx in SIDES:
        A = M[f'UpperArm.{s}'].translation
        R = Matrix.Rotation(math.radians(4 * sx), 3, 'Y') @ Matrix.Rotation(math.radians(-8 - o.get('arm_fwd', 0.0)), 3, 'X')
        W = A + R @ (rhead(f'Hand.{s}') - rhead(f'UpperArm.{s}'))
        H = LIMB[('hand', s)]
        P['hands'][s] = dict(C=W + R @ (H['C0'] - rhead(f'Hand.{s}')), D=R, pole=Vector((0.12 * sx, 1, 0.1)),
                             fingers=o.get('fingers', {}).get(s, (8, 14)), thumb=(4, 6))
        P['feet'][s] = dict(C=an[('foot', s)].copy(), D=foot_D(s, 10, 0), pole=Vector((0.3 * sx, -1, 0)),
                            toeD=foot_D(s, 10, 0))
    return P


def qlerp(A, B, t):
    return A.to_quaternion().slerp(B.to_quaternion(), t).to_matrix()


def tlerp(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def blend(P, Q, tb, th=None, tf=None, arc=0.0):
    """P -> Q: tb the body, th the hands (lifted arc m at the middle of the way), tf the feet"""
    th = tb if th is None else th
    tf = tb if tf is None else tf
    R = {'hips': P['hips'].lerp(Q['hips'], tb), 'hips_rot': tlerp(P['hips_rot'], Q['hips_rot'], tb),
         'spine': [tlerp(a, b, tb) for a, b in zip(P['spine'], Q['spine'])],
         'neck': [tlerp(a, b, tb) for a, b in zip(P['neck'], Q['neck'])],
         'head': tlerp(P['head'], Q['head'], tb), 'jaw': lerp(P['jaw'], Q['jaw'], tb),
         'shoulder': {s: tlerp(P['shoulder'][s], Q['shoulder'][s], tb) for s, _ in SIDES}, 'hands': {}, 'feet': {}}
    for s, _ in SIDES:
        a, b = P['hands'][s], Q['hands'][s]
        R['hands'][s] = dict(C=a['C'].lerp(b['C'], th) + Z * arc * math.sin(math.pi * th), D=qlerp(a['D'], b['D'], th),
                             pole=a['pole'].lerp(b['pole'], th), fingers=tlerp(a['fingers'], b['fingers'], th),
                             thumb=tlerp(a['thumb'], b['thumb'], th))
        a, b = P['feet'][s], Q['feet'][s]
        R['feet'][s] = dict(C=a['C'].lerp(b['C'], tf), D=qlerp(a['D'], b['D'], tf), pole=a['pole'].lerp(b['pole'], tf),
                            toeD=qlerp(a['toeD'], b['toeD'], tf))
    return R


# Stand (4 s loop): upright, a slow breath, the arms swaying a little after it, one sharp tilt of the skull
STAND_F = 96


def stand_pose(f):
    t = f / STAND_F
    br = math.sin(TAU * 2 * t)
    roll = 20 * smooth((f - 40) / 2) * (1 - smooth((f - 62) / 8))
    o = {'spine': [(5 - 1.0 * br, 0, 0), (5 - 1.2 * br, 0, 0), (4, 0, 0)], 'head': (0, 4 + 1.5 * br, roll),
         'shoulder': {'L': (0, 1.5 * br), 'R': (0, 1.5 * br)}, 'jaw': 3 + 3 * max(0.0, br),
         'arm_fwd': 2 * math.sin(TAU * 2 * t - 0.8),
         'fingers': {s_: (8 + 6 * (0.5 + 0.5 * math.sin(TAU * (2 * t + (0 if s_ == 'L' else 0.4)))) ** 4, 14) for s_, _ in SIDES}}
    return upright(o)


bake('Stand', STAND_F + 1, True, stand_pose)
P4, PU = stance(), upright()

# StandUp (1.5 s): the palms come off the ground first, then he unfolds over his feet
STANDUP_F = 36
bake('StandUp', STANDUP_F + 1, False, lambda f: blend(P4, PU, smooth((f / STANDUP_F - 0.15) / 0.8),
                                                        smooth((f / STANDUP_F - 0.05) / 0.45), smooth(f / STANDUP_F / 0.9), 0.12))

# DropDown (1.2 s): falls forward onto the palms - they reach the ground before the body has settled
DROP_F = 28
bake('DropDown', DROP_F + 1, False, lambda f: blend(PU, P4, smooth(f / DROP_F / 0.85),
                                                     smooth((f / DROP_F - 0.1) / 0.65), smooth(f / DROP_F), 0.10))


# Flinch (1.25 s): caught by a yellow light - recoils back in 3 frames, the skull turns away and up, the right palm
# comes up in front of the face, holds trembling; then drops back onto all fours. The game then backs him off.
FLINCH_F = 30


def flinch_key(tremble=0.0):
    o = {'hips': ST['hips'] + Vector((0, 0.16, -0.16)), 'hips_rot': (ST['hips_rot'][0] - 10, -4, 0),
         'spine': [(2, -3, 0), (2, -2, 0), (-2, 0, -6)], 'neck': [(4, 0, -6), (10, 0, -8)],
         'head': (-25 + 3 * tremble, 22, -12), 'jaw': 10.0}
    P = stance(o)
    M = body_M(P)
    hd = M['Head'].translation
    # the left palm hops back with the body: replanted ahead of the shoulder, at 95 % of the arm's reach
    sh = M['UpperArm.L'].translation
    lm, H = LIMB[('arm', 'L')], LIMB[('hand', 'L')]
    reach = (lm['L1'] + lm['L2']) * 0.95
    wrist_up = (P['hands']['L']['D'] @ (rhead('Hand.L') - H['C0'])).z + GROUND['hand']
    dy = math.sqrt(max(0.0, reach ** 2 - (sh.z - wrist_up) ** 2 - 0.04 ** 2))
    P['hands']['L']['C'] = Vector((sh.x + 0.04, sh.y - dy, GROUND['hand']))
    s = 'R'
    H = LIMB[('hand', s)]
    d = Vector((0.25, -0.2, 1.0)).normalized()                  # the palm up in front of the skull, facing the light
    D = fmap(H['d'], H['s'], d, Vector((-1, 0, 0)))
    P['hands'][s] = dict(C=hd + Vector((-0.04 + 0.01 * tremble, -0.17, 0.0)), D=D, pole=Vector((-0.9, 0.3, -0.4)),
                         fingers=(-8 + 4 * tremble, -6), thumb=(-6, -4))
    return P


FK1 = flinch_key()


def flinch_pose(f):
    if f <= 3:
        return blend(P4, FK1, smooth(f / 3), arc=0.05)
    if f <= 20:
        return flinch_key(math.sin(f * 2.7) * (1 - (f - 3) / 30))
    t = (f - 20) / (FLINCH_F - 20)
    return blend(FK1, P4, smooth(t), smooth(t), smooth(t), 0.05)


bake('Flinch', FLINCH_F + 1, False, flinch_pose)

# Grab (0.5 s, holds the last frame): a lunge - the body surges forward and down, the jaw opens, the right palm shoots
# out to the ground ahead and the fingers close on what is there (a fallen player's leg). The game then plays Drag.
GRAB_F = 12
GRAB_KEY = dict(hips=ST['hips'] + Vector((0, -0.30, -0.06)), hips_rot=(ST['hips_rot'][0] + 8, 0, 0))


def grab_pose(f):
    k = smooth(f / 8)
    c = smooth((f - 7) / 4)
    o = {'hips': ST['hips'].lerp(GRAB_KEY['hips'], k), 'hips_rot': tlerp(ST['hips_rot'], GRAB_KEY['hips_rot'], k),
         'head': (0, ST['head'][1] + 10 * k, 0), 'jaw': 25 * k - 10 * c,
         'hand_off': {'L': Vector((0, -0.18 * smooth((f - 2) / 5), 0.06 * math.sin(math.pi * smooth((f - 2) / 5)))),
                      'R': Vector((0, -0.55 * k, 0.10 * math.sin(math.pi * k)))},
         'hand_pitch_add': {'R': 25 * k},
         'fingers': {'R': (-ST['hand_pitch'] - 15 * k + 55 * c, 10 + 60 * c)}}
    return stance(o)


bake('Grab', GRAB_F + 1, False, grab_pose)


# Drag: walks backwards on three limbs, the right hand held out in front, low, closed on the victim's leg; the body
# leans back against the weight, the skull looks at the victim. 0.8 m a loop backwards (the game plays it by distance)
DRAG_F, DRAG_STRIDE, DRAG_DUTY = 24, -0.8, 0.72
DRAG_PH = {('foot', 'L'): 0.0, ('hand', 'L'): 0.33, ('foot', 'R'): 0.66}
DRAG_ANCHOR = {'hips': ST['hips'] + Vector((0, 0.04, -0.06)), 'hand_y': -0.22}


def drag_body(t):
    s1 = math.sin(TAU * t)
    return {'anchor': DRAG_ANCHOR,
            'hips': DRAG_ANCHOR['hips'] + Vector((0.02 * s1, 0, 0.01 * math.sin(TAU * 3 * t))),
            'hips_rot': (ST['hips_rot'][0] - 6, 3 * s1, -4 * s1),
            'spine': [(ST['spine'][0][0], -2 * s1, 2 * s1), (ST['spine'][1][0], -2 * s1, 0), (ST['spine'][2][0], 0, -6)],
            'head': (-8, ST['head'][1] + 14, 0), 'jaw': 6.0,
            'hand_off': {'R': Vector((0.05, -0.30 + 0.03 * math.sin(TAU * 3 * t), 0.16))},
            'hand_pitch_add': {'R': 35}, 'fingers': {'R': (40, 70)}}


bake('Drag', DRAG_F + 1, True, lambda f: gait(f, DRAG_F, DRAG_STRIDE, DRAG_DUTY, DRAG_PH, {'hand': 0.08, 'foot': 0.06}, drag_body))



# DragFast (30.10): he runs off forwards on three limbs, the right arm trailing behind him low, closed on the victim's
# leg; the skull keeps glancing back at him. 1.3 m a loop forwards.
DRAGF_F, DRAGF_STRIDE, DRAGF_DUTY = 16, 1.3, 0.5
DRAGF_PH = {('foot', 'L'): 0.0, ('hand', 'L'): 0.35, ('foot', 'R'): 0.62}
DRAGF_ANCHOR = {'hips': ST['hips'] + Vector((0, 0.02, -0.04)), 'hand_y': -0.26}


def dragf_body(t):
    s1 = math.sin(TAU * t)
    back = 0.5 + 0.5 * math.sin(TAU * t * 0.5 + 1.0)            # the glance back comes and goes
    return {'anchor': DRAGF_ANCHOR,
            'hips': DRAGF_ANCHOR['hips'] + Vector((0.02 * s1, 0, 0.008 * math.cos(TAU * 2 * t))),
            'hips_rot': (ST['hips_rot'][0] + 2, 5 * s1, -6 * s1 - 6),
            'spine': [(ST['spine'][0][0], -4 * s1, 3 * s1 - 4), (ST['spine'][1][0], -3 * s1, -4), (ST['spine'][2][0], 2 * s1, -6)],
            'neck': [(ST['neck'][0][0], 0, -12 * back), (ST['neck'][1][0], 0, -10 * back)],
            'head': (-35 * back, ST['head'][1] + 6, -6 * back), 'jaw': 10.0,
            'hand_off': {'R': Vector((-0.10, 0.95, 0.15 + 0.03 * s1))},              # trailing low behind, on the leg
            'hand_D': {'R': hand_D('R', 180, 55)}, 'hand_pole': {'R': Vector((-0.8, 0.5, -0.3))},
            'fingers': {'R': (40, 70)}}


bake('DragFast', DRAGF_F + 1, True, lambda f: gait(f, DRAGF_F, DRAGF_STRIDE, DRAGF_DUTY, DRAGF_PH,
                                                     {'hand': 0.12, 'foot': 0.10}, dragf_body, snap=True))
CYCLE_DRAGF = {'cycle_m': DRAGF_STRIDE, 'speed_mps': round(DRAGF_STRIDE * FPS / DRAGF_F, 3)}


# Throw (0.83 s, once): from the end of Grab - rears back and twists right, the right arm swings up and behind with
# the victim, then whips forward and across to his left and opens at frame 11 (THROW_RELEASE: the game flings the
# player then), and he drops back onto all fours.
THROW_F, THROW_RELEASE = 20, 11
_G = grab_pose(GRAB_F)


def throw_key(k):
    if k == 'wind':
        return stance({'hips': ST['hips'] + Vector((0, 0.12, 0.10)), 'hips_rot': (ST['hips_rot'][0] - 16, 0, -10),
                       'spine': [(2, 0, -8), (0, 0, -8), (-4, 0, -8)], 'neck': [(14, 0, 8), (10, 0, 8)],
                       'head': (20, -8, 0), 'jaw': 20.0,
                       'hand_off': {'L': Vector((0, 0.28, 0)), 'R': Vector((-0.25, 0.77, 1.68))},   # overhead, behind
                       'hand_D': {'R': hand_D('R', 160, -60)}, 'hand_pole': {'R': Vector((-1, 0, 0.5))},
                       'fingers': {'R': (40, 70)}})
    return stance({'hips': ST['hips'] + Vector((0, -0.14, 0.02)), 'hips_rot': (ST['hips_rot'][0] + 6, 0, 14),
                   'spine': [(6, 0, 10), (4, 0, 10), (2, 0, 8)], 'neck': [(22, 0, -6), (14, 0, -6)],
                   'head': (-10, 4, 0), 'jaw': 28.0,
                   'hand_off': {'L': Vector((0, 0.28, 0)), 'R': Vector((0.40, -0.40, 0.75))},
                   'hand_D': {'R': hand_D('R', -40, -30)}, 'hand_pole': {'R': Vector((-0.8, 0.6, 0.2))},
                   'fingers': {'R': (-12, -6)}})


_TW, _TR = throw_key('wind'), throw_key('release')


def throw_pose(f):
    if f <= 7:
        return blend(_G, _TW, smooth(f / 7), smooth(f / 7), 0.0, 0.0)
    if f <= THROW_RELEASE:
        k = ((f - 7) / (THROW_RELEASE - 7)) ** 2                   # the whip: slow out of the wind-up, fast at the release
        return blend(_TW, _TR, k, k, 0.0)
    return blend(_TR, stance(), smooth((f - THROW_RELEASE) / (THROW_F - THROW_RELEASE)), None, 0.0, 0.06)


bake('Throw', THROW_F + 1, False, throw_pose)
CLIPS['Throw']['release_s'] = round(THROW_RELEASE / FPS, 3)

CYCLE['Drag'] = {'cycle_m': -DRAG_STRIDE, 'speed_mps': round(-DRAG_STRIDE * FPS / DRAG_F, 3), 'backwards': True}
CYCLE['DragFast'] = CYCLE_DRAGF
INFO['gaits'] = CYCLE

# ------------------------------------------------------------------ checks: planted palms / soles do not slide in the world
SLIP = {}
for name, F, stride, duty, phases in (('Sneak', SNEAK_F, SNEAK_STRIDE, SNEAK_DUTY, SNEAK_PH),
                                      ('Run', RUN_F, RUN_STRIDE, RUN_DUTY, RUN_PH),
                                      ('DragFast', DRAGF_F, DRAGF_STRIDE, DRAGF_DUTY, DRAGF_PH)):
    arm.animation_data.action = bpy.data.actions[name]
    v = stride / F
    worst = 0.0
    for (kind, s), ph in phases.items():
        bone = f'Hand.{s}' if kind == 'hand' else f'Toe.{s}'
        prev = None
        for fr in range(1, F + 1):
            u = ((fr - 1) / F - ph) % 1.0
            if u >= duty * 0.8:
                prev = None
                continue
            sc.frame_set(fr)
            p = arm.matrix_world @ pb[bone].head + Vector((0, -v * (fr - 1), 0))   # into the world: he moves -y
            if prev is not None:
                worst = max(worst, (p - prev).length)
            prev = p
    SLIP[name] = round(worst, 4)
INFO['slip_m_per_frame'] = SLIP
log('slip', SLIP)
INFO['clips'] = CLIPS
arm.animation_data.action = bpy.data.actions['Idle4']
sc.frame_set(1)

# ------------------------------------------------------------------ save + FBX (as the Lesnik: Generic, axes not baked)
INFO['fps'] = FPS
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Holodny.blend'))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Holodny.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         axis_forward='-Z', axis_up='Y', bake_space_transform=False, apply_unit_scale=True,
                         mesh_smooth_type='FACE', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                         bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                         bake_anim_simplify_factor=0.0, path_mode='STRIP')
json.dump(INFO, open(os.path.join(OUT, 'Holodny.json'), 'w'), indent=1)
log('saved', OUT)

# ------------------------------------------------------------------ preview frames (textured, ortho side + 3/4)
if RENDER:
    rd = os.path.join(OUT, 'renders', 'frames')
    os.makedirs(rd, exist_ok=True)
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
    except TypeError:
        pass
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'TEXTURE'
    sh.background_type = 'VIEWPORT'
    sh.background_color = (0.62, 0.63, 0.65)
    sc.render.resolution_x, sc.render.resolution_y = 640, 480
    floor = bpy.data.objects.new('Floor', bpy.data.meshes.new('Floor'))
    fm = floor.data
    fm.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(floor)
    cd = bpy.data.cameras.new('Cam')
    cd.type = 'ORTHO'
    cd.ortho_scale = 3.4
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    views = {'side': ((-7, 0, 1.05), (math.radians(90), 0, math.radians(-90))),
             'q34': ((-4.2, -4.6, 2.9), (math.radians(73), 0, math.radians(-42))),
             'front': ((0, -7, 1.05), (math.radians(90), 0, 0))}
    want = [a for a in ARGS if a.startswith('--clips=')]
    names = want[0][8:].split(',') if want else list(CLIPS)
    for name in names:
        arm.animation_data.action = bpy.data.actions[name]
        a, b = CLIPS[name]['frames_blender']
        step = 1 if b - a <= 30 else 2
        for vn, (loc, rt) in views.items():
            cam.location, cam.rotation_euler = loc, rt
            for fr in range(a, b + 1, step):
                sc.frame_set(fr)
                sc.render.filepath = os.path.join(rd, f'{name}_{vn}_{fr:03d}.png')
                bpy.ops.render.render(write_still=True)
    log('rendered', names)
