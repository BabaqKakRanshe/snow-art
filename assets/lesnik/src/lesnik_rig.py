"""Lesnik (final model): the developer's AI-generated mesh (model.glb, A-pose) on the blockout's 33-bone skeleton + Idle.

The mesh comes in normalised (~0.95 m); it is scaled to the blockout's straight height (3.378 m), feet on the ground,
the face to -y (Blender: x = the figure's left, y back, z up - as the blockout). UV seams are welded (merge by distance:
an AI mesh arrives as ~1000 islands and bone heat fails on them), the skeleton is placed on joints measured on the mesh
(slices, 28.10), the weights are bone heat + three rules (the cap and the head to Head, the hood and the collar off the
neck, the neck kept off the chest), and the clip is keyed per frame and baked through leg IK so the feet stay planted.

Bone names and the hierarchy are the blockout's (README there): the game code looks up Hand.L / Hand.R / Head, and the
neck is 12 loose bones (6 before 28.10) that NeckReach slides apart along their length (location, not scale: Unity multiplies scale down
the chain). Rest = the mesh's A-pose (arms ~23 deg out).

Idle (24 fps, frames 1-241 in Blender = 0-240 in Unity, the last frame equals the first, loop, 10 s): the hunched Stand
pose moved by two videos (docs/gdd/monsters/02_lesnik/anim_refs, 28.10). Idle.mp4 (5 s, run twice): the long arms slowly
curl in - elbows out, wrists and needle fingers hooked in - one after the other and open out again (src/video/
idle_curves.py, the silhouette). "Generated Video ... 10_48PM.mp4" (10 s): the upside-down head on the long neck swings
like a weight on a rope, the lag growing to 12 frames at the head, and once is flung up over the right shoulder,
hangs there and drops back (src/video/head_curves.py, the head tracked). Under it a breath and a slow weight shift on
planted feet. The hunch, the broken neck and the upside-down head stay ours (the videos' figure stands straight).
Cower (Cower.mp4) and Sleep (Sleep.mp4: lies down and curls up, once) are keyed on the videos' frames.

Run: blender -b --factory-startup --python lesnik_rig.py -- <model.glb> <out_dir> [--render]
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector, Matrix, Quaternion

ARGS = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = os.path.abspath(ARGS[0]), os.path.abspath(ARGS[1])
RENDER = '--render' in ARGS
os.makedirs(os.path.join(OUT, 'tex'), exist_ok=True)
T0 = time.time()
FPS = 24
LOOP = 240                      # frames: 10 s (the dangling-head video; the arms' 5 s video runs twice)
HEIGHT = 3.378                  # straight height of the blockout (top of the cap), m
INFO = {}


def log(*a):
    print('[lesnik_rig %5.1fs]' % (time.time() - T0), *a, flush=True)


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
ob.name = ob.data.name = 'Lesnik_Body'

bm = bmesh.new()
bm.from_mesh(ob.data)
n0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
bm.to_mesh(ob.data)
bm.free()
for p in ob.data.polygons:
    p.use_smooth = True
INFO['verts'] = {'imported': n0, 'welded': len(ob.data.vertices)}
INFO['tris'] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
INFO['scale_from_glb'] = round(S, 4)
log('mesh', INFO['verts'], 'tris', INFO['tris'])

# the material and its maps: base colour / normal / metallic-roughness -> tex/
m = ob.active_material
m.name = 'M_Lesnik'
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
    img.name = f'T_Lesnik_{kind}'
    data = bytes(img.packed_file.data)                              # the GLB's own file, as it came
    ext = '.png' if data[:4] == b'\x89PNG' else '.jpg'
    with open(os.path.join(OUT, 'tex', f'T_Lesnik_{kind}{ext}'), 'wb') as fh:
        fh.write(data)
INFO['textures'] = sorted(i.name for i in bpy.data.images)

# ------------------------------------------------------------------ the skeleton, on joints measured on the mesh
NECK_N = 12                     # 6 showed angles at the joints when the head is flung (28.10); 12 bend half as much each
NECK0, HEAD0, HEAD1 = Vector((0, 0.01, 2.52)), Vector((0, 0.0, 2.90)), Vector((0, 0.0, 3.30))
NECK_L = (HEAD0 - NECK0).length / NECK_N
B = {
    'Root': ((0, 0, 0), (0, 0.12, 0), None),
    'Hips': ((0, 0, 1.36), (0, 0, 1.50), 'Root'),
    'Spine': ((0, 0, 1.50), (0, 0.0, 1.95), 'Hips'),
    'Chest': ((0, 0, 1.95), tuple(NECK0), 'Spine'),
}
for i in range(NECK_N):
    a = NECK0.lerp(HEAD0, i / NECK_N)
    b = NECK0.lerp(HEAD0, (i + 1) / NECK_N)
    B[f'Neck{i + 1}'] = (tuple(a), tuple(b), 'Chest' if i == 0 else f'Neck{i}')
B['Head'] = (tuple(HEAD0), tuple(HEAD1), f'Neck{NECK_N}')
WRIST = Vector((0.738, -0.027, 1.175))
TIPS = [Vector(t) for t in ((0.787, -0.036, 0.632), (0.874, -0.006, 0.654), (0.952, 0.001, 0.694), (1.033, 0.001, 0.760))]
BASES = [WRIST.lerp(t, 0.30) for t in TIPS]
KNUCK = sum(BASES, Vector()) / 4
for s, sx in (('L', 1), ('R', -1)):
    X = Vector((sx, 1, 1))

    def mx(v):
        return tuple(Vector(v) * X)
    B[f'Shoulder.{s}'] = (mx((0.04, 0.02, 2.42)), mx((0.22, 0.03, 2.40)), 'Chest')
    B[f'UpperArm.{s}'] = (mx((0.22, 0.03, 2.40)), mx((0.465, 0.02, 1.80)), f'Shoulder.{s}')
    B[f'ForeArm.{s}'] = (mx((0.465, 0.02, 1.80)), mx(WRIST), f'UpperArm.{s}')
    B[f'Hand.{s}'] = (mx(WRIST), mx(KNUCK), f'ForeArm.{s}')
    for j in range(4):
        B[f'Finger{j + 1}.{s}'] = (mx(BASES[j]), mx(TIPS[j]), f'Hand.{s}')
    B[f'Thigh.{s}'] = (mx((0.12, 0.0, 1.36)), mx((0.195, 0.0, 0.78)), 'Hips')
    B[f'Shin.{s}'] = (mx((0.195, 0.0, 0.78)), mx((0.225, 0.04, 0.11)), f'Thigh.{s}')
    B[f'Foot.{s}'] = (mx((0.225, 0.04, 0.11)), mx((0.27, -0.22, 0.02)), f'Shin.{s}')
ARM_OUT = math.degrees(math.atan2(0.738 - 0.22, 2.40 - 1.175))      # rest angle of the arm from the vertical (~23)

arm_d = bpy.data.armatures.new('Lesnik_Rig')
arm = bpy.data.objects.new('Lesnik_Rig', arm_d)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in B.items():
    eb = arm_d.edit_bones.new(name)
    eb.head, eb.tail, eb.roll = Vector(h), Vector(t), 0.0
    eb.use_deform = name != 'Root'
for name, (h, t, par) in B.items():
    if par:
        eb = arm_d.edit_bones[name]
        eb.parent = arm_d.edit_bones[par]
        eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
INFO['bones'] = list(B)

# ------------------------------------------------------------------ the bare neck: more rings
# the AI mesh has a ring every ~7 cm along the middle of the neck; drawn out x1.9 and bent, the skin goes straight
# between rings and shows corners (28.10). Every edge along the neck there is cut twice: a ring every ~2.5 cm.
NAX = (HEAD0 - NECK0).normalized()


def neck_tr(p):
    t = (p - NECK0).dot(NAX)
    return t, ((p - NECK0) - NAX * t).length


bm = bmesh.new()
bm.from_mesh(ob.data)
cut = []
for e in bm.edges:
    (t0, r0), (t1, r1) = neck_tr(e.verts[0].co), neck_tr(e.verts[1].co)
    d = e.verts[1].co - e.verts[0].co
    if max(r0, r1) < 0.065 and 0.08 < min(t0, t1) and max(t0, t1) < 0.42 and d.length > 0 and abs(d.normalized().dot(NAX)) > 0.6:
        cut.append(e)
bmesh.ops.subdivide_edges(bm, edges=cut, cuts=2, use_grid_fill=True)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bm.to_mesh(ob.data)
bm.free()
for p_ in ob.data.polygons:
    p_.use_smooth = True
INFO['neck_rings'] = {'edges_cut': len(cut), 'verts': len(ob.data.vertices), 'tris': sum(len(p_.vertices) - 2 for p_ in ob.data.polygons)}
log('neck rings', INFO['neck_rings'])

# ------------------------------------------------------------------ weights: bone heat, then the rules
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
me = ob.data
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


SEG = {n: (Vector(h), Vector(t)) for n, (h, t, par) in B.items() if n != 'Root'}
NECKS = [f'Neck{i}' for i in range(1, NECK_N + 1)]
empty = fixed = 0
for v in me.vertices:
    w = {gname[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
    p = v.co
    r_neck = math.hypot(p.x, p.y - 0.01)
    if not w:                                                       # heat found nothing: the nearest bone
        empty += 1
        w = {min(SEG, key=lambda n: seg_dist(p, *SEG[n])): 1.0}
    if p.z > 2.95:                                                  # cap and skull: rigid to the head
        w = {'Head': 1.0}
    elif p.z < 2.80 and r_neck > 0.06 and any(n in w for n in NECKS):
        # hood and collar around the neck: they stay on the chest when the neck stretches
        t = sum(w.pop(n, 0.0) for n in NECKS + ['Head'])
        w['Chest'] = w.get('Chest', 0.0) + t
        fixed += 1
    elif r_neck < 0.06 and 2.58 < p.z < 2.95:
        # the bare neck: a smooth ramp along its axis between the bone middles (bone heat leaves it nearly rigid per
        # bone, and every joint then kinks); past the last middle it blends into the head
        s = (p - NECK0).dot(HEAD0 - NECK0) / (HEAD0 - NECK0).length_squared * NECK_N
        chain = NECKS + ['Head']
        c = max(0.0, min(len(chain) - 1.0, s - 0.5))
        i0 = int(c)
        i1 = min(i0 + 1, len(chain) - 1)
        w = {chain[i0]: 1.0 - (c - i0)}
        w[chain[i1]] = w.get(chain[i1], 0.0) + (c - i0)
        fixed += 1
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    tot = sum(x for _, x in top) or 1.0
    for g in list(v.groups):
        ob.vertex_groups[g.group].remove([v.index])
    for n, x in top:
        ob.vertex_groups[gi[n]].add([v.index], x / tot, 'REPLACE')
INFO['weights'] = {'heat_empty_to_nearest': empty, 'rule_fixed': fixed}
log('weights', INFO['weights'])

# ------------------------------------------------------------------ pose helpers (as the blockout)
pb = arm.pose.bones
for b in pb:
    b.rotation_mode = 'QUATERNION'


def rot_world(bone, axis, deg):
    R = arm_d.bones[bone].matrix_local.to_3x3()
    return (R.inverted() @ Matrix.Rotation(math.radians(deg), 3, Vector(axis)) @ R).to_quaternion()


def qmul(*qs):
    out = Quaternion()
    for q in qs:
        out = out @ q
    return out


def rx(bone, deg):
    return rot_world(bone, (1, 0, 0), deg)


def clear():
    for b in pb:
        b.rotation_quaternion = Quaternion()
        b.location = Vector()


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


BACK = 45.0                             # the concept bends him further than the blockout (30): the fingers near the floor
STAND_STRETCH = 1.9                     # this mesh's neck is 0.38 m: drawn out to 0.72 m (the dangling-head video, 28.10)
RR =arm_d.bones['Root'].matrix_local.to_3x3().inverted()
POSE = {}                               # the per-frame extras of Idle, by bone: list of quaternions (applied after base)


def upper(s, x, y=0.0):
    """UpperArm: out of the A-pose to hanging straight down (+4 deg in), then x about the world x (- forward)"""
    sx = 1 if s == 'L' else -1
    return qmul(rx(f'UpperArm.{s}', x), rot_world(f'UpperArm.{s}', (0, 1, 0), sx * (ARM_OUT + 4) + sx * y))


def arm_rx(bone, s, deg):
    """x bend of a bone below the upper arm (forearm, hand, fingers): about the axis that upper() turns into the world x
    (the rest arm is tilted out in the A-pose; bent about the plain x it would swing out sideways)"""
    sx = 1 if s == 'L' else -1
    return rot_world(bone, tuple(Matrix.Rotation(-math.radians(sx * (ARM_OUT + 4)), 3, 'Y') @ Vector((1, 0, 0))), deg)


def per_bone(six):
    """an angle profile written for 6 neck bones -> NECK_N bones: sampled along the neck, each share scaled so the
    whole neck bends as much as before"""
    out = []
    for j in range(NECK_N):
        u = (j + 0.5) / NECK_N * 6 - 0.5
        i0 = max(0, min(5, math.floor(u)))
        i1 = min(5, i0 + 1)
        t = max(0.0, min(1.0, u - i0))
        out.append((six[i0] * (1 - t) + six[i1] * t) * 6 / NECK_N)
    for _ in range(2):                                                  # blurred along the neck: no joint takes a corner
        out = [out[0] * 0.75 + out[1] * 0.25] +               [out[j - 1] * 0.25 + out[j] * 0.5 + out[j + 1] * 0.25 for j in range(1, NECK_N - 1)] +               [out[-2] * 0.25 + out[-1] * 0.75]
    return out


DOWN = per_bone([28, 10, 26, 40, 28, 10])   # the neck in Stand: out of the collar forward, then broken down over 3 bones
LIFT_A = per_bone([-30, -24, -6, 14, 24, 18])   # a flung-up head: the neck's root bends up, its end folds over - an arch the head hangs from
                                        # (one joint at 72 deg creased the skin; linear skinning wants <= ~40 per joint)


def spread_twist(theta):
    """The hanging head is turned theta round the neck. On one joint (Neck6 -> Head) linear skinning pinches the neck
    into a rope at 180; here Neck2..NeckN take their share (15 deg a joint with 12) and every bone keeps its world direction:
    bone k gets twist psi_k about its own length, its child's local is corrected by the parent's psi."""
    chain = [f'Neck{i}' for i in range(1, NECK_N + 1)] + ['Head']
    psi = {n: 0.0 for n in chain}
    for i in range(2, NECK_N + 1):
        psi[f'Neck{i}'] = theta * (i - 1) / NECK_N
    prev = 0.0
    for n in chain:
        b = arm_d.bones[n]
        rel = (b.parent.matrix_local.to_3x3().inverted() @ b.matrix_local.to_3x3()).to_quaternion()
        pb[n].rotation_quaternion = qmul(rel.inverted(), Quaternion((0, 1, 0), math.radians(-prev)), rel,
                                         pb[n].rotation_quaternion, Quaternion((0, 1, 0), math.radians(psi[n])))
        prev = psi[n]


def stand_pose(d=None, back=BACK, reach=0.0, stretch=STAND_STRETCH, aim=16, fold=1.0, head_turn=0.0):
    """the hunched Stand (the blockout's, on this skeleton) + the asymmetry of a body at rest; d: idle extras.
    back: forward bend of the back; reach 0..1: the neck from broken-down to straight out (NeckReach); stretch: neck
    length factor (bones slide apart along their length); aim: where the reached neck points, deg below the horizontal;
    fold: the broken neck folds tighter (Cower); head_turn: the head turned away round its own length (Cower)"""
    d = d or {}
    g = lambda k: d.get(k, 0.0)
    clear()
    pb['Spine'].rotation_quaternion = qmul(rx('Spine', back * 0.35 + g('spine_x')), rot_world('Spine', (0, 1, 0), g('spine_y')),
                                           rot_world('Spine', (0, 0, 1), g('spine_z')))
    pb['Chest'].rotation_quaternion = qmul(rx('Chest', back * 0.65 + g('chest_x')), rot_world('Chest', (0, 1, 0), 2.0 + g('chest_y')))
    out_ = [-back + 90 + aim] + [0.0] * (NECK_N - 1)                # reached: straight out at the target
    for i in range(NECK_N):
        # nl<i>: the break unfolds (the head flung up); ns<i>: the bone swings sideways (+ to the figure's right, -x)
        a = (DOWN[i] * fold + LIFT_A[i] * g(f'nl{i + 1}') + (g('neck_x') if i == NECK_N // 2 else 0.0)) * (1 - reach) + out_[i] * reach
        pb[f'Neck{i + 1}'].rotation_quaternion = qmul(rx(f'Neck{i + 1}', a),
                                                      rot_world(f'Neck{i + 1}', (0, 1, 0), (g('neck_y') if i >= NECK_N // 2 else 0.0) + g(f'ns{i + 1}')))
        if i > 0:
            pb[f'Neck{i + 1}'].location = Vector((0, NECK_L * (stretch - 1.0), 0))   # along the parent bone
    pb['Head'].location = Vector((0, NECK_L * (stretch - 1.0), 0))
    # the head hangs almost upside down, twisted round on the neck so the face still turns to the front;
    # reached out, it untwists and faces forward
    pb['Head'].rotation_quaternion = qmul(rot_world('Head', (0, 0, 1), g('head_z')),
                                          rot_world('Head', (0, 1, 0), (14 + 8 + g('head_y')) * (1 - reach)),   # +8: tilted
                                          rx('Head', (40 + g('head_x')) * (1 - reach) - 106 * reach),
                                          Quaternion((0, 1, 0), math.radians(180 * (1 - reach))),
                                          rot_world('Head', (0, 0, 1), head_turn))
    spread_twist(180 * (1 - reach) + head_turn)                   # head_turn is a turn round the head's length too
    for s, sx in (('L', 1), ('R', -1)):
        pb[f'Shoulder.{s}'].rotation_quaternion = rot_world(f'Shoulder.{s}', (0, 1, 0),
                                                            -sx * (6 + (-4 if s == 'R' else 0)) - sx * g(f'sh_{s}'))
        # the arms hang straight down from the bent torso: undo the A-pose and the back bend, a little forward
        pb[f'UpperArm.{s}'].rotation_quaternion = upper(s, -back * 0.6 - 10 - (5 if s == 'L' else 0) + g(f'arm_x_{s}'), g(f'arm_y_{s}'))
        # *_in: bent in toward the body (about the world y; + in for both sides)
        pb[f'ForeArm.{s}'].rotation_quaternion = qmul(rot_world(f'ForeArm.{s}', (0, 1, 0), sx * g(f'fore_in_{s}')),
                                                      arm_rx(f'ForeArm.{s}', s, -10 + g(f'fore_x_{s}')))
        pb[f'Hand.{s}'].rotation_quaternion = qmul(rot_world(f'Hand.{s}', (0, 1, 0), sx * g(f'hand_in_{s}')),
                                                   arm_rx(f'Hand.{s}', s, g(f'hand_x_{s}')))
        for j in range(1, 5):
            pb[f'Finger{j}.{s}'].rotation_quaternion = qmul(rot_world(f'Finger{j}.{s}', (0, 1, 0), sx * g(f'fin_in_{s}')),
                                                            arm_rx(f'Finger{j}.{s}', s, 8 + 4 * j + g(f'f{j}_{s}')))
        pb[f'Thigh.{s}'].rotation_quaternion = rx(f'Thigh.{s}', -14 - (3 if s == 'R' else 0))
        pb[f'Shin.{s}'].rotation_quaternion = rx(f'Shin.{s}', 22 + (5 if s == 'R' else 0))        # weight on the left leg
        pb[f'Foot.{s}'].rotation_quaternion = rx(f'Foot.{s}', -8 - (2 if s == 'R' else 0))
    pb['Hips'].rotation_quaternion = qmul(rot_world('Hips', (0, 1, 0), g('hips_y')), rot_world('Hips', (0, 0, 1), g('hips_z')))


stand_pose()
ROOT_Z = -min(p.z for p in mesh_points())
INFO['root_drop'] = round(ROOT_Z, 4)


def root_at(x=0.0, y=0.0, z=0.0):
    pb['Root'].location = RR @ Vector((x, y, ROOT_Z + z))


root_at()
bpy.context.view_layer.update()
pts = mesh_points()
INFO['stand_top'] = round(max(p.z for p in pts), 3)
INFO['stand_extents'] = [[round(min(p[i] for p in pts), 3) for i in range(3)], [round(max(p[i] for p in pts), 3) for i in range(3)]]
log('stand top', INFO['stand_top'], 'root drop', INFO['root_drop'])

# ------------------------------------------------------------------ leg IK: the feet stay where Stand put them
targets = {}
for s in ('L', 'R'):
    f = pb[f'Foot.{s}']
    M = arm.matrix_world @ f.matrix
    M.translation = arm.matrix_world @ f.tail
    e = bpy.data.objects.new(f'IK_Foot.{s}', None)
    sc.collection.objects.link(e)
    e.matrix_world = M
    c = f.constraints.new('IK')
    c.target = e
    c.chain_count = 3
    c.use_tail = True
    c.use_rotation = True
    c.use_stretch = False
    targets[s] = e


# ------------------------------------------------------------------ Idle
def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def env(f, a, b, c, d):
    """0 before a, snaps up a->b, holds b->c, eases back c->d"""
    if f < a or f > d:
        return 0.0
    if f < b:
        return smooth((f - a) / (b - a))
    if f <= c:
        return 1.0
    return 1.0 - smooth((f - c) / (d - c))


VIDEO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video', 'idle_curves.json')))
HEADV = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video', 'head_curves.json')))
# the body's life from motion capture of Idle.mp4 (29.10, GEM-X: src/video/gem_joints.py -> mocap_curves.py): the pelvis
# sway and weight shift, the spine's lean / side bend / twist, the shoulders - changes from the mean pose, on top of our
# hunch. GEM fits a human, so only the body is taken (the arms are the silhouette's, the head is HEADV).
MOCAP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video', 'mocap_idle.json')))
MOCAP_K = 1.30 / MOCAP['human_hip_height_m']            # his hips are this much higher: the sway grows with the legs
assert LOOP % VIDEO['loop'] == 0 and LOOP % MOCAP['loop'] == 0 and HEADV['loop'] == LOOP, 'the video curves are for another loop: rerun src/video/*.py'
SWING = per_bone([4, 6, 8, 10, 12, 12])   # the head's sideways swing, deg per neck bone at side = 1
HEAD_FLING = per_bone([26, 24, 16, 2, -6, -8])   # flung up: the arch leans out over the shoulder, its hanging end swings back under


def idle_extras(f):
    t = f / LOOP
    w = lambda k, ph=0.0: math.sin(2 * math.pi * (k * t + ph))
    d = {}
    breath = 0.7 * w(2) + 0.3 * w(3, 0.11)                            # a faint breath under the capture
    m = f % MOCAP['loop']
    mc = lambda k: MOCAP[k][m]
    # blender: left +x, forward -y; a + turn about y lowers +x (roll), about z moves +x back (yaw / twist)
    d['hips_y'] = -mc('pelvis_roll_deg')
    d['hips_z'] = -mc('pelvis_yaw_deg')
    d['spine_x'] = 0.5 * mc('spine_lean_deg') - 0.4 * breath
    d['chest_x'] = 0.5 * mc('spine_lean_deg') - 0.8 * breath
    d['spine_y'] = 0.6 * mc('spine_side_deg')
    d['chest_y'] = 0.4 * mc('spine_side_deg')
    d['spine_z'] = -mc('chest_twist_deg')
    d['sh_L'] = 250 * mc('shrug_l_m') + 0.8 * breath                 # 1 cm of shrug ~ 2.5 deg of the shoulder
    d['sh_R'] = 250 * mc('shrug_r_m') + 0.8 * breath
    # the video: the head swings side to side after the arms (head_x in body heights, + = his left = +x);
    # on the broken neck that is the hanging part swinging about the forward axis (- y moves a hanging bone to +x)
    # the dangling-head video: the upside-down head swings like a weight on a rope - each bone down the neck follows
    # the one above a little late, 12 frames root to head (the whip); once (5-7 s) it is flung up and out over the right shoulder, hangs
    # there and drops back. side + = his left (+x); the turn is about y in the rest pose (neck up): + moves it to +x
    for i in range(1, NECK_N + 1):
        k = (f - round(12 * (i - 1) / NECK_N)) % LOOP                 # 12 frames from the root to the head
        sd, lf = HEADV['side'][k], HEADV['lift'][k]
        d[f'ns{i}'] = SWING[i - 1] * sd + HEAD_FLING[i - 1] * lf * sd
        d[f'nl{i}'] = lf
    k = (f - 12) % LOOP
    d['head_z'] = -50 * HEADV['side'][k] * (1 + HEADV['lift'][k])    # the face turns with the swing, late
    d['head_y'] = 2.0 * w(1, -0.10)
    d['neck_x'] = 3.0 * w(2, -0.08)                                   # the break bobs with the breath, late
    # the video: each arm on its own curve - open (0: hanging wide, as the video's first frame) to curled (1: the elbow
    # out, the forearm and the wrist bent in, the needle fingers hooked) and back; below 0 it opens wider still
    for s in ('L', 'R'):
        c = VIDEO[f'curl_{s}'][f % VIDEO['loop']]
        cf = VIDEO[f'curl_{s}'][(f - 3) % VIDEO['loop']]                # the fingers follow 3 frames late
        d[f'arm_y_{s}'] = -20 + 2 * c                                 # wide; curled, the elbow stays out
        d[f'arm_x_{s}'] = -4 * c
        d[f'fore_x_{s}'] = -10 * c
        d[f'fore_in_{s}'] = 14 * c                                    # the hands stay at the sides
        d[f'hand_x_{s}'] = -18 * cf
        d[f'hand_in_{s}'] = 26 * cf                                   # the wrists hook in
        d[f'fin_in_{s}'] = 6 * cf
        for j in range(1, 5):                                         # the claws close, the outer fingers a bit more
            d[f'f{j}_{s}'] = -(24 + 4 * j) * cf + 2.0 * w(3, 0.29 * j + (0.5 if s == 'R' else 0))
    return d, (MOCAP_K * mc('pelvis_left_m'), -MOCAP_K * mc('pelvis_fwd_m'), MOCAP_K * mc('pelvis_up_m'))


act = bpy.data.actions.new('Idle')
act.use_fake_user = True
arm.animation_data_create()
arm.animation_data.action = act
for fr in range(1, LOOP + 2):
    d, (x, y, z) = idle_extras(fr - 1)
    stand_pose(d)
    root_at(x, y, z)
    key_all(fr)
sc.frame_start, sc.frame_end = 1, LOOP + 1
log('idle keyed')

# bake the IK into plain keys, then drop the IK and its targets
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1, frame_end=LOOP + 1, only_selected=False, visual_keying=True, clear_constraints=True,
                 use_current_action=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for e in targets.values():
    bpy.data.objects.remove(e, do_unlink=True)
act = arm.animation_data.action
act.name = 'Idle'
act.use_fake_user = True
log('baked')

# checks: the feet do not slide, nothing goes below the ground, the loop closes
toe = {s: [] for s in ('L', 'R')}
low = []
for fr in range(1, LOOP + 2, 4):
    sc.frame_set(fr)
    for s in toe:
        toe[s].append(arm.matrix_world @ pb[f'Foot.{s}'].tail)
    low.append(min(p.z for p in mesh_points()))
sc.frame_set(1)
first = {b.name: (b.matrix.copy()) for b in pb}
sc.frame_set(LOOP + 1)
loop_err = max((first[b.name].translation - b.matrix.translation).length for b in pb)
INFO['idle'] = {'frames_blender': [1, LOOP + 1], 'frames_unity': [0, LOOP], 'seconds': LOOP / FPS, 'loop': True,
                'toe_drift_m': {s: round(max((p - v[0]).length for p in v), 4) for s, v in toe.items()},
                'lowest_z': [round(min(low), 3), round(max(low), 3)], 'loop_close_m': round(loop_err, 5)}
log('idle checks', INFO['idle'])
sc.frame_set(1)

# ------------------------------------------------------------------ the logic's clips (the blockout's, on this rig)
# keyed poses as the blockout's (feet not solved); names, lengths and loops are what Lesnik.cs / LesnikBlockout.cs play.
# signs: about x, + tips a down-pointing bone (legs, arms) back (+y), - forward; the figure faces -y
TAU = 2 * math.pi
REACH_M = 6 * 0.09 * 1.087 * 6.0                        # the blockout's reached neck: 6 bones x 0.098 m x 6 = 3.5 m
STRETCH = REACH_M / (NECK_N * NECK_L)                   # the same length on this shorter neck
ARM_X = -BACK * 0.6 - 10                                # the hanging arm's x in Stand
CLIPS = {}


def new_action(name, frames):
    a = bpy.data.actions.new(name)
    a.use_fake_user = True
    arm.animation_data.action = a
    CLIPS[name] = [1, frames]
    return a


def carry_arms(k=1.0, side=('L', 'R')):
    """both long arms folded, the stolen things pressed to the chest"""
    for s in side:
        pb[f'UpperArm.{s}'].rotation_quaternion = upper(s, ARM_X * (1 - k) - 22 * k)
        pb[f'ForeArm.{s}'].rotation_quaternion = arm_rx(f'ForeArm.{s}', s, -10 * (1 - k) - 92 * k)
        for j in range(1, 5):
            pb[f'Finger{j}.{s}'].rotation_quaternion = arm_rx(f'Finger{j}.{s}', s, (8 + 4 * j) * (1 - k) - 70 * k)


new_action('Stand', 2)                                                  # the pose, without the Idle's life
stand_pose()
root_at()
key_all(1)
key_all(2)

for name, aim in (('NeckReach', 16), ('NeckReachUp', -40)):             # 1 s: the neck out to a standing player's
    new_action(name, 25)                                                # face / up to a first-floor window
    for f, t in ((1, 0.0), (5, 0.15), (10, 0.45), (15, 0.75), (20, 0.95), (25, 1.0)):
        e = smooth(t)
        stand_pose(reach=e, stretch=STAND_STRETCH + (STRETCH - STAND_STRETCH) * e, aim=aim)
        root_at()
        key_all(f)

def ik_bake(name, frames, pose_fn, feet_fn, foot_turn=True):
    """a clip keyed per frame through leg IK, then baked to plain keys (as Idle): pose_fn(f) poses the body and the
    root, feet_fn(f, side) -> (offset Vector, toe pitch deg) moves that foot's IK target from where Stand puts it, or
    -> a Matrix: the target's whole world matrix (at the toe tip, oriented as the Stand foot turned)"""
    arm.animation_data.action = None                                    # else the last clip's frame overrides the pose
    stand_pose()
    root_at()
    bpy.context.view_layer.update()
    base, tg = {}, {}
    for side in ('L', 'R'):
        fb = pb[f'Foot.{side}']
        M = arm.matrix_world @ fb.matrix
        M.translation = arm.matrix_world @ fb.tail
        base[side] = M.copy()
        e = bpy.data.objects.new(f'IK_{name}.{side}', None)
        sc.collection.objects.link(e)
        c = fb.constraints.new('IK')
        c.target, c.chain_count, c.use_tail, c.use_rotation, c.use_stretch = e, 3, True, foot_turn, False
        tg[side] = e
    new_action(name, frames)
    for fr in range(1, frames + 1):
        pose_fn(fr - 1)
        key_all(fr)
        for side in ('L', 'R'):
            res = feet_fn(fr - 1, side)
            Mb = base[side]
            if isinstance(res, Matrix):                               # the whole target, world
                tg[side].matrix_world = res
            else:                                                     # (offset from Stand, toe pitch)
                off, pitch = res
                tg[side].matrix_world = Matrix.Translation(Mb.translation + off) @ Matrix.Rotation(math.radians(pitch), 4, 'X') @ \
                    Mb.to_3x3().to_4x4()
            tg[side].keyframe_insert('location', frame=fr)
            tg[side].keyframe_insert('rotation_euler', frame=fr)
    sc.frame_start, sc.frame_end = 1, frames
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=1, frame_end=frames, only_selected=False, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    for e in tg.values():
        if e.animation_data and e.animation_data.action:
            bpy.data.actions.remove(e.animation_data.action)       # not exported as a take
        bpy.data.objects.remove(e, do_unlink=True)
    a = arm.animation_data.action
    a.name = name
    a.use_fake_user = True


# Shuffle (29.10, research Q1): in place, 2 steps a loop, the feet held on the ground by IK while the game moves him
# at SHUF_V (LesnikBlockout plays it by the distance walked: SHUF_CYCLE m a loop, so the feet never slide). A dragging
# limp: long double support, the left foot barely leaves the ground and drags its toes, the right lifts a little more
# and lands sooner; the body bobs down on both feet, sways over the standing foot, the long arms swing late and loose.
# The rhythm step-step-pause is the game's (Lesnik.cs stops him on both feet: SHUF_PAUSE).
SHUF_F = 32                                                           # frames a loop (1.33 s)
SHUF_V = 0.9                                                          # m/s while it steps (= Lesnik.walkSpeed)
SHUF_CYCLE = SHUF_V * SHUF_F / FPS                                    # 1.2 m: 2 short steps
SHUF_STANCE = {'L': 0.62, 'R': 0.58}                                  # of the loop on the ground
SHUF_LIFT = {'L': 0.025, 'R': 0.05}                                   # the left one drags
SHUF_PAUSE = [0.04, 0.55]                                             # both feet down there (double support)
SHUF_BACK = 0.05                                                      # the steps sit this much behind the Stand feet: the bent legs reach


def shuffle_phase(f, side):
    return (f / SHUF_F + (0.0 if side == 'L' else 0.5)) % 1.0


def shuffle_feet(f, side):
    q, st = shuffle_phase(f, side), SHUF_STANCE[side]
    S = SHUF_CYCLE * st                                               # how far the planted foot slides back (in place)
    if q < st:                                                        # on the ground: front -> back (+y)
        return Vector((0, SHUF_BACK - S / 2 + S * q / st, 0)), -6 * max(0.0, 1 - q / 0.08)   # heel down at the strike
    u = (q - st) / (1 - st)                                           # in the air: low and fast forward, toes dragging
    return Vector((0, SHUF_BACK + S / 2 - S * smooth(u), SHUF_LIFT[side] * math.sin(math.pi * u))), 16 * math.sin(math.pi * u) ** 0.7


def shuffle_body(f):
    p = f / SHUF_F
    w = lambda k, ph=0.0: math.sin(TAU * (k * p + ph))
    d = {'spine_x': 3.0, 'chest_x': 1.5 * w(2, 0.15),                  # a little further over, nods with the steps
         'hips_y': -3.0 * w(1, -0.1), 'hips_z': 4.0 * w(1), 'chest_y': 2.0 * w(1, -0.1), 'spine_z': -3.0 * w(1),
         'neck_x': 4.0 * w(2, -0.2), 'head_y': 3.0 * w(1, -0.25)}       # the hanging head lags behind the body
    for side, ph in (('L', 0.0), ('R', 0.5)):
        leg = math.sin(TAU * (p + ph))                                # + : this side's leg going back
        d[f'arm_x_{side}'] = 8.0 * math.sin(TAU * (p + ph) - 0.7)     # the arm swings opposite the leg, late
        d[f'fore_x_{side}'] = -5.0 * math.sin(TAU * (p + ph) - 1.4)
        d[f'hand_x_{side}'] = 6.0 * math.sin(TAU * (p + ph) - 2.0)
        for j in range(1, 5):
            d[f'f{j}_{side}'] = 5.0 * math.sin(TAU * (p + ph) - 2.2 - 0.25 * j)   # the needle fingers trail
    stand_pose(d)
    root_at(x=0.035 * w(1, -0.1), z=-0.02 * (0.5 + 0.5 * math.cos(TAU * 2 * (p - SHUF_PAUSE[0]))))


ik_bake('Shuffle', SHUF_F + 1, shuffle_body, shuffle_feet)
# check: where each toe ends up vs where its IK target was (the leg could not reach = the foot slides in game)
arm.animation_data.action = None
stand_pose()
root_at()
bpy.context.view_layer.update()
base_toe = {sd: arm.matrix_world @ pb[f'Foot.{sd}'].tail for sd in ('L', 'R')}
arm.animation_data.action = bpy.data.actions['Shuffle']
miss = {'L': [], 'R': []}
for fr in range(1, SHUF_F + 1):
    sc.frame_set(fr)
    for sd in miss:
        want = base_toe[sd] + shuffle_feet(fr - 1, sd)[0]
        got = arm.matrix_world @ pb[f'Foot.{sd}'].tail
        miss[sd].append(((got - want).length, round(shuffle_phase(fr - 1, sd), 2)))
INFO['shuffle_ik_miss_m'] = {sd: round(max(m for m, _ in v), 4) for sd, v in miss.items()}
log('shuffle ik miss (max, at phase)', {sd: max(v) for sd, v in miss.items()})

new_action('Grab', 25)                                                  # 1 s: reach down, close the fingers, to the chest
for f, reach, close, home in ((1, 0, 0, 0), (8, 0.7, 0, 0), (12, 1, 0, 0), (15, 1, 1, 0), (20, 1, 1, 0.6), (25, 1, 1, 1)):
    stand_pose()
    pb['Spine'].rotation_quaternion = rx('Spine', BACK * 0.35 + 18 * reach * (1 - home))
    if home > 0:
        carry_arms(home, ('R',))
    else:
        pb['UpperArm.R'].rotation_quaternion = upper('R', ARM_X - 38 * reach)
        pb['ForeArm.R'].rotation_quaternion = arm_rx('ForeArm.R', 'R', -10 - 20 * reach)
        for j in range(1, 5):
            pb[f'Finger{j}.R'].rotation_quaternion = arm_rx(f'Finger{j}.R', 'R', 8 + 4 * j - 70 * close)
    root_at()
    key_all(f)

new_action('Carry', 2)                                                  # pose loop: Stand with the arms folded on the chest
stand_pose()
carry_arms()
root_at()
key_all(1)
key_all(2)

def keys(f, ks):
    """smooth steps through (frame, value) keys"""
    if f <= ks[0][0]:
        return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f <= f1:
            return v0 + (v1 - v0) * smooth((f - f0) / (f1 - f0))
    return ks[-1][1]


# Cower, 2 s, on the video's frames (anim_refs/Cower.mp4, frame 16 = 0 here); 29.10 sharper (RESEARCH_ANIMATION
# Q6: a snap in 2-3 frames, the video's 0.4 s was soft): the light hits, in 3 frames the right
# arm sweeps up across the body and shields the head (fingers spread, palm to the light), the left arm is flung out and
# back, the body straightens away from the light, the broken neck folds tighter and the head turns away; then he holds,
# the raised hand trembling. The game plays its first ~0.5 s and goes on to Flee.
COWER = 49
REC = ((0, 0), (1, 0.6), (2, 1.05), (4, 1.0))                           # the body recoils
SHIELD = ((0, 0), (1, 0.35), (2, 0.85), (3, 1.08), (5, 1.0))            # the right arm up over the head
FLING = ((0, 0), (1, 0.4), (2, 0.95), (3, 1.18), (6, 1.0), (20, 0.85), (48, 0.8))   # the left arm out
new_action('Cower', COWER)
for f in range(COWER):
    k, a, b = keys(f, REC), keys(f, SHIELD), keys(f, FLING)
    hold = smooth((f - 4) / 4)                                          # the tremble once the pose is reached
    tr = lambda hz, ph=0.0: hold * math.sin(2 * math.pi * hz * f / FPS + ph)
    d = {'chest_y': 6 * k, 'spine_z': -4 * k,                           # leans away to his left, turns from the light
         'arm_x_R': -30 * a, 'arm_y_R': -60 * a + 1.5 * tr(2.3),        # the elbow out to the side
         'fore_x_R': -20 * a, 'fore_in_R': 135 * a,                     # the forearm up across, in front of the hanging head
         'hand_x_R': 25 * a + 3 * tr(6.5), 'hand_in_R': 0.0,
         'arm_x_L': 15 * b, 'arm_y_L': -45 * b, 'fore_x_L': -15 * b, 'hand_x_L': 10 * b}
    for j in range(1, 5):
        d[f'f{j}_R'] = (8 + 4 * j) * -a + 4 * tr(7.0, j)                 # straight and spread, shaking
        d[f'f{j}_L'] = -(8 + 4 * j) * b
    stand_pose(d, back=BACK * (1 - 0.6 * k), fold=1 + 0.35 * k, head_turn=55 * k)   # the broken neck folds tighter
    for s in ('L', 'R'):                                                # the knees give a little
        pb[f'Shin.{s}'].rotation_quaternion = rx(f'Shin.{s}', 22 + (5 if s == 'R' else 0) + 8 * k)
    root_at(z=-0.03 * k)
    key_all(f + 1)

# Flee (29.10, RESEARCH_ANIMATION Q3 "on two legs" + item 5): huge low leaps on two legs, in place, 2 leaps a loop,
# the feet held on the ground by IK while the game carries him at FLEE_V (LesnikBlockout plays it by the distance run:
# FLEE_CYCLE m a loop). The body pitched far forward and low (Flee.mp4: ~57 deg over the hips), each leap a short
# stance and a long flight with the knee driven high; the long arms trail behind, and every second leap both reach
# forward and push off the ground beside the landing foot (Little Nightmares' Janitor: the long arms make the speed).
FLEE_F = 18                                                           # frames a loop (0.75 s)
FLEE_V = 6.0                                                          # m/s (= Lesnik.fleeSpeed)
FLEE_CYCLE = FLEE_V * FLEE_F / FPS                                    # 4.5 m: 2 leaps
FLEE_STANCE = 0.22                                                    # of the loop each foot is down
FLEE_BACK = -0.10                                                      # the steps sit this much behind the Stand feet
FLEE_LIFT = 0.42                                                      # the knee driven high: the foot this far up


def flee_phase(f, side):
    return (f / FLEE_F + (0.0 if side == 'L' else 0.5)) % 1.0


def flee_feet(f, side):
    q = flee_phase(f, side)
    S = FLEE_CYCLE * FLEE_STANCE                                       # how far the planted foot slides back (in place)
    if q < FLEE_STANCE:
        return Vector((0, FLEE_BACK - S / 2 + S * q / FLEE_STANCE, 0)), -4 + 10 * q / FLEE_STANCE    # flat, rolling to the toe
    u = (q - FLEE_STANCE) / (1 - FLEE_STANCE)                          # in the air: up and far forward, toes down
    return Vector((0, FLEE_BACK + S / 2 - S * smooth(u), FLEE_LIFT * math.sin(math.pi * u) ** 0.8)), 30 * math.sin(math.pi * u)


def flee_body(f):
    p = f / FLEE_F
    leap = (p % 0.5) * 2                                              # 0..1 through each leap (stance at 0..0.54)
    push = max(0.0, math.sin(math.pi * min(1.0, ((p - 0.85) % 1.0) / 0.4))) if ((p - 0.85) % 1.0) < 0.4 else 0.0
    d = {'spine_x': 6.0 * math.cos(TAU * 2 * p), 'chest_x': 4.0 * math.cos(TAU * 2 * p - 0.5),
         'hips_y': 4.0 * math.sin(TAU * p), 'hips_z': 6.0 * math.sin(TAU * p), 'spine_z': -5.0 * math.sin(TAU * p),
         'neck_x': 8.0 * math.sin(TAU * 2 * p - 1.0)}
    for side in ('L', 'R'):
        trail = 1.0 - push                                              # the arms trail behind, or reach and push
        d[f'arm_x_{side}'] = 35.0 * trail - 55.0 * push + 6.0 * math.sin(TAU * 2 * p + (0 if side == 'L' else 1.0))
        d[f'arm_y_{side}'] = -8.0
        d[f'fore_x_{side}'] = -10.0 * trail - 25.0 * push
        d[f'hand_x_{side}'] = 20.0 * trail - 10.0 * push
        for j in range(1, 5):
            d[f'f{j}_{side}'] = 10.0 * trail - (12 + 4 * j) * push    # spread back / clawing at the ground
    stand_pose(d, back=BACK + 22)
    flight = max(0.0, math.sin(math.pi * (leap - FLEE_STANCE * 2) / (1 - FLEE_STANCE * 2))) if leap > FLEE_STANCE * 2 else 0.0
    sink = math.sin(math.pi * leap / (FLEE_STANCE * 2)) if leap < FLEE_STANCE * 2 else 0.0
    root_at(z=-0.18 + 0.22 * flight - 0.08 * sink)                      # low; up in the flight, down on the landing


ik_bake('Flee', FLEE_F + 1, flee_body, flee_feet)
miss = {'L': [], 'R': []}
arm.animation_data.action = None
stand_pose()
root_at()
bpy.context.view_layer.update()
base_toe = {sd: arm.matrix_world @ pb[f'Foot.{sd}'].tail for sd in ('L', 'R')}
arm.animation_data.action = bpy.data.actions['Flee']
for fr in range(1, FLEE_F + 1):
    sc.frame_set(fr)
    for sd in miss:
        if flee_phase(fr - 1, sd) < FLEE_STANCE:
            got = arm.matrix_world @ pb[f'Foot.{sd}'].tail
            dv = got - (base_toe[sd] + flee_feet(fr - 1, sd)[0])
            miss[sd].append((dv.length, round(flee_phase(fr - 1, sd), 2), tuple(round(c, 3) for c in dv)))
INFO['flee'] = {'speed_mps': FLEE_V, 'cycle_m': round(FLEE_CYCLE, 4), 'frames': FLEE_F, 'stance': FLEE_STANCE,
                'ik_miss_on_ground_m': {sd: round(max(e[0] for e in v), 4) for sd, v in miss.items()}}
log('flee', INFO['flee'], {sd: max(v) for sd, v in miss.items()})

# Sleep, 7 s, once (holds the last frame): lies down on the cave bed - the video Sleep.mp4 (anim_refs, frames 30-200 =
# 0-170 here). 29.10: the body by motion capture of that video (GEM-X -> src/video/mocap_body.py -> mocap_sleep.json):
# the pelvis' path and turn (bends over, squats on his hands, a knee down, sits over on his right hip, lies on his side,
# curls up), the spine's bend, and both feet through leg IK - human sizes scaled by the leg length. GEM fits a human,
# so the long arms stay keyed on the video's frames (reach the floor, lean on the right hand, the left hand rises with
# its fingers twitching, then both wrap round him). After the bake every frame is lifted so nothing goes under the
# floor (GEM sinks a lying body a little).
SLEEP = 171
SK = {'axL':    ((0, 0), (20, -5), (40, -8), (55, -10), (82, -15), (106, -40), (120, -80), (135, -110), (150, -60)),   # the captured
      'axR':    ((0, 0), (20, -5), (40, -10), (55, -12), (82, -15), (106, -40)),   # body leans: the arms hang to the floor
      'ayL':    ((0, 0), (40, -12), (55, -20), (106, -10)),
      'ayR':    ((0, 0), (40, -12), (55, -20), (82, -30), (106, -10)),
      'foL':    ((0, 0), (20, -5), (40, -20), (55, -35), (82, -40), (106, -30)),   # the elbows give: hands on the floor
      'foR':    ((0, 0), (20, -5), (40, -20), (55, -35), (82, -55), (94, -60), (106, -30)),   # he leans on it
      'wrapL':  ((0, 0), (135, 0), (150, 0.6), (170, 1.0)),
      'wrapR':  ((0, 0), (106, 0), (120, 0.5), (150, 0.8), (170, 1.0)),
      'twitch': ((0, 0), (120, 0), (128, 1), (150, 1), (160, 0))}
MSLEEP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video', 'mocap_sleep.json')))
assert MSLEEP['frames'] == SLEEP, 'mocap_sleep.json is for another length: rerun src/video/mocap_body.py'
MS_K = 1.30 / MSLEEP['human_hip_height_m']                              # his legs are this much longer
MS_TR = MSLEEP['track']
RREST = arm_d.bones['Root'].matrix_local.to_3x3()
stand_pose()
pb['Root'].rotation_quaternion = Quaternion()
pb['Root'].location = Vector()
bpy.context.view_layer.update()
HIPS0 = arm.matrix_world @ pb['Hips'].head                              # the pelvis with the Root at rest
FOOT_DIR = {sd: (pb[f'Foot.{sd}'].tail - pb[f'Foot.{sd}'].head).normalized() for sd in ('L', 'R')}
START = HIPS0 + Vector((0, 0, ROOT_Z))                                  # where Stand puts the pelvis
root_at()
bpy.context.view_layer.update()
FOOT_ROT = {sd: (arm.matrix_world @ pb[f'Foot.{sd}'].matrix).to_3x3() for sd in ('L', 'R')}


def sleep_target(f):
    return START + MS_K * (Vector(MS_TR[f]['pelvis']) - Vector(MS_TR[0]['pelvis']))


def sleep_body(f):
    k = {n: keys(f, v) for n, v in SK.items()}
    r = MS_TR[f]
    d = {'spine_x': 0.5 * r['lean'], 'chest_x': 0.5 * r['lean'], 'spine_y': 0.5 * r['side'], 'chest_y': 0.5 * r['side']}
    for s in ('L', 'R'):
        w_ = k[f'wrap{s}']
        base = -BACK * 0.6 - 10 - (5 if s == 'L' else 0)               # stand_pose's hanging arm
        d[f'arm_x_{s}'] = k[f'ax{s}'] * (1 - w_) + (-22 - base) * w_   # wrapped: carry_arms' pose
        d[f'arm_y_{s}'] = k[f'ay{s}'] * (1 - w_)
        d[f'fore_x_{s}'] = k[f'fo{s}'] * (1 - w_) - 82 * w_
        for j in range(1, 5):
            tw = 14 * k['twitch'] * math.sin(f * 1.7 + j) if s == 'L' else 0.0      # the left fingers twitch
            d[f'f{j}_{s}'] = -(78 + 4 * j) * w_ + tw
    stand_pose(d)
    # the Root turned and moved so the pelvis follows the capture (turned about the pelvis, not the feet)
    R = Matrix(r['R'])
    pb['Root'].rotation_quaternion = (RREST.inverted() @ R @ RREST).to_quaternion()
    pb['Root'].location = RR @ (sleep_target(f) - R @ HIPS0)


def sleep_feet(f, side):
    r = MS_TR[f]
    pel = Vector(r['pelvis'])
    toe = Vector(r['toe_l' if side == 'L' else 'toe_r'])
    ankle = Vector(r['ankle_l' if side == 'L' else 'ankle_r'])
    at = sleep_target(f) + MS_K * (toe - pel)                          # the leg as captured, scaled about the pelvis
    turn = FOOT_DIR[side].rotation_difference((toe - ankle).normalized()).to_matrix()
    return Matrix.Translation(at) @ (turn @ FOOT_ROT[side]).to_4x4()


ik_bake('Sleep', SLEEP, sleep_body, sleep_feet)
ARMV = None                                                             # the arms' vertices: their weight goes to arm bones
lift = []
for f in range(SLEEP):                                                  # the body (not the long arms) not under the floor
    sc.frame_set(f + 1)
    if ARMV is None:
        armg = {g.index for g in ob.vertex_groups if g.name.split('.')[0] in ('UpperArm', 'ForeArm', 'Hand') or g.name.startswith('Finger')}
        ARMV = {v.index for v in ob.data.vertices if v.groups and max(v.groups, key=lambda e: e.weight).group in armg}
    pts_ = mesh_points()
    low = min(pts_[i].z for i in range(len(pts_)) if i not in ARMV)
    if low < 0.01:
        pb['Root'].location = pb['Root'].location + RR @ Vector((0, 0, 0.01 - low))
        pb['Root'].keyframe_insert('location', frame=f + 1)
    lift.append(round(max(0.0, 0.01 - low), 3))
INFO['sleep_mocap'] = {'scale': round(MS_K, 3), 'lifted_m_max': max(lift)}
log('sleep mocap', INFO['sleep_mocap'])


def extents(name, frame):
    arm.animation_data.action = bpy.data.actions[name]
    sc.frame_set(frame)
    p_ = mesh_points()
    return [[round(min(p[i] for p in p_), 3) for i in range(3)], [round(max(p[i] for p in p_), 3) for i in range(3)]]


def head_at(name, frame):
    arm.animation_data.action = bpy.data.actions[name]
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    return [round(c, 3) for c in (arm.matrix_world @ pb['Head'].head)]


INFO['clips'] = dict(CLIPS, Idle=[1, LOOP + 1])
INFO['neck_stretch'] = {'Stand': STAND_STRETCH, 'NeckReach_end': round(STRETCH, 3)}
INFO['neck_length_m'] = {'Stand': round(NECK_N * NECK_L * STAND_STRETCH, 3), 'NeckReach_end': round(REACH_M, 3)}
INFO['extents'] = {'Stand': extents('Stand', 1), 'NeckReach_end': extents('NeckReach', 25), 'Grab_reach': extents('Grab', 12),
                   'Cower_hold': extents('Cower', 20), 'Flee_up': extents('Flee', 7), 'Flee_down': extents('Flee', 13),
                   'Sleep_end': extents('Sleep', SLEEP)}
INFO['head'] = {'Stand': head_at('Stand', 1), 'NeckReach_end': head_at('NeckReach', 25), 'NeckReachUp_end': head_at('NeckReachUp', 25)}
INFO['shuffle'] = {'speed_mps': SHUF_V, 'cycle_m': round(SHUF_CYCLE, 4), 'frames': SHUF_F, 'pause_phases': SHUF_PAUSE, 'stance': SHUF_STANCE}
log('clips', list(INFO['clips']), 'head', INFO['head'])
arm.animation_data.action = bpy.data.actions['Idle']
sc.frame_set(1)

# ------------------------------------------------------------------ save + FBX (as the blockout: Generic, not baked axes)
INFO['fps'] = FPS
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Lesnik.blend'))
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
ob.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Lesnik.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         axis_forward='-Z', axis_up='Y', bake_space_transform=False, apply_unit_scale=True,
                         mesh_smooth_type='FACE', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                         bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                         bake_anim_simplify_factor=0.0, path_mode='STRIP')
json.dump(INFO, open(os.path.join(OUT, 'Lesnik.json'), 'w'), indent=1)
log('saved', OUT)

# ------------------------------------------------------------------ preview: frames of the Idle + a gif
if RENDER:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools', 'snow_style', 'pydeps'))
    from PIL import Image
    rd = os.path.join(OUT, 'renders')
    os.makedirs(rd, exist_ok=True)
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        log(e)
    sc.render.resolution_x, sc.render.resolution_y = 560, 640
    sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new('W')
    sc.world = wd
    wd.use_nodes = True
    bg = next(n for n in wd.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.55, 0.56, 0.58, 1)
    bg.inputs[1].default_value = 1.4
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new('Cam')
    cd.lens = 50
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    views = {'front34': (Vector((2.6, -6.2, 1.7)), Vector((0, -0.2, 1.35))), 'side': (Vector((-6.8, -0.4, 1.5)), Vector((0, -0.2, 1.35)))}
    gif = {k: [] for k in views}
    for fr in range(1, LOOP + 1, 4):
        sc.frame_set(fr)
        for k, (loc, aim) in views.items():
            cam.location = loc
            cam.rotation_euler = (aim - loc).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(rd, f'_tmp_{k}.png')
            bpy.ops.render.render(write_still=True)
            gif[k].append(Image.open(sc.render.filepath).convert('RGB'))
            if fr in (1, 33, 61, 85):
                gif[k][-1].save(os.path.join(rd, f'idle_{k}_f{fr - 1:03d}.png'))
    frames = [Image.new('RGB', (1120, 640)) for _ in gif['side']]
    for i, fimg in enumerate(frames):
        fimg.paste(gif['front34'][i], (0, 0))
        fimg.paste(gif['side'][i], (560, 0))
    frames[0].save(os.path.join(rd, 'idle.gif'), save_all=True, append_images=frames[1:], duration=int(1000 * 4 / FPS), loop=0)
    for k in views:
        os.remove(os.path.join(rd, f'_tmp_{k}.png'))
    log('renders', rd)
