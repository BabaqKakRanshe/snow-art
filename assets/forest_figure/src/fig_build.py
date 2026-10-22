"""The apparition for the Forest scares X02 (crosses the road in the headlights) and X03 (on the van's rear seat for 0.6 s):
Apparition - a tall gaunt figure, 2.30 m, in a long ragged coat, very long arms and fingers, a pale long head with dark
hollows for eyes and mouth, thin bare legs below the hem. Low poly, one PSX atlas at the shed's props density, skinned
to a 19-bone armature with four clips (in place, no root motion):
  Stand    the idle pose: hunched, the head tilted, arms hanging to the knees (1 frame)
  Walk     a loop of 1.25 s: long stiff strides, small arm swing; the stance foot flat and planted (the root bobs so the
           lowest point stays on the ground), the swing foot clear of it; the feet keep still on the ground when the
           object moves at INFO['walk_speed'] (about 1.6 m/s)
  Sit      on a seat whose top is at the object's origin, the feet flat on a floor 0.425 m below (van3's benches) and
           everything under a roof 0.705 m above the seat (van3: 0.709): the trunk folded forward almost flat under
           the roof, the head hanging, the long arms down between the knees, the fingertips on the floor
  SitLook  0.6 s from Sit: the head comes up in front of the shoulders and turns its face to the figure's left - the
           cab and its mirror, from the van's left bench - then holds
Frame: Blender x right, y back (the figure faces -y), z up; Unity (-x, z, -y): it faces +z, origin between the feet
(Stand, Walk) or on the seat under the pelvis (Sit, SitLook).
python3 -I fig_build.py [--draft] -> out/fig.blend, out/fig.json, tex/fig/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import psxlib as P
import psxbake as PB
import gen_kit as K
import bld_common as BC
from noise import ss, mixc, fbm, dist_periodic
from psxbake import lin
from gen_paint import _T, _common, GRIME

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'fig')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
Z_COAT, Z_SKIN, Z_DARK, Z_LEG = 1, 2, 3, 4
TAU = 2 * math.pi
FPS = 24


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS

# ------------------------------------------------------------------ bones (rest = standing, arms hanging)
B = {   # name: (head, tail, parent)
    'Root': ((0, 0, 0), (0, 0.12, 0), None),
    'Hips': ((0, 0, 1.15), (0, 0, 1.32), 'Root'),
    'Spine': ((0, 0, 1.32), (0, 0.012, 1.58), 'Hips'),
    'Chest': ((0, 0.012, 1.58), (0, 0.02, 1.88), 'Spine'),
    'Neck': ((0, 0.02, 1.88), (0, 0.0, 2.02), 'Chest'),
    'Head': ((0, 0.0, 2.02), (0, -0.01, 2.30), 'Neck'),
}
for s, sx in (('L', 1), ('R', -1)):
    B[f'Shoulder.{s}'] = ((sx * 0.03, 0.02, 1.84), (sx * 0.19, 0.03, 1.87), 'Chest')
    B[f'UpperArm.{s}'] = ((sx * 0.19, 0.03, 1.87), (sx * 0.235, 0.02, 1.37), f'Shoulder.{s}')
    B[f'ForeArm.{s}'] = ((sx * 0.235, 0.02, 1.37), (sx * 0.255, -0.01, 0.93), f'UpperArm.{s}')
    B[f'Hand.{s}'] = ((sx * 0.255, -0.01, 0.93), (sx * 0.265, -0.03, 0.68), f'ForeArm.{s}')
    B[f'Thigh.{s}'] = ((sx * 0.095, 0.0, 1.13), (sx * 0.105, -0.01, 0.62), 'Hips')
    B[f'Shin.{s}'] = ((sx * 0.105, -0.01, 0.62), (sx * 0.11, 0.02, 0.09), f'Thigh.{s}')
    B[f'Foot.{s}'] = ((sx * 0.11, 0.02, 0.09), (sx * 0.115, -0.20, 0.02), f'Shin.{s}')

# ------------------------------------------------------------------ the mesh (KB with zones + a part tag per face)
k = K.KB()
PART = {}           # face index -> part (for the weights)


def tag(f0, part):
    k.bm.faces.ensure_lookup_table()
    for i in range(f0, len(k.bm.faces)):
        PART[i] = part


def ring(c, rx, ry, n=8, rot=0.0, jag=None):
    out = []
    for i in range(n):
        a = TAU * i / n + rot
        r = 1.0 if jag is None else jag(i)
        out.append(Vector(c) + Vector((rx * math.cos(a) * r, ry * math.sin(a) * r, 0.0)))
    return out


def loft_z(rings, zone, cap0=None, cap1=None):
    k.loft(rings, [zone] * (len(rings) - 1), cap0=cap0, cap1=cap1)


def limb(pts, radii, zone, n=6):
    """a tube through pts with per-point radii (sections perpendicular to the path)"""
    rings = []
    ref = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        rp, e1 = k.ring_pts(p, t, radii[i], n, ref)
        ref = e1
        rings.append(rp)
    k.loft(rings, [zone] * (len(rings) - 1), cap0=zone, cap1=zone)


f0 = len(k.bm.faces)
# head: a long egg on the neck, the face to -y
hz = [(1.95, 0.042, 0.044), (2.00, 0.046, 0.050), (2.035, 0.070, 0.080), (2.09, 0.080, 0.095), (2.16, 0.086, 0.104),
      (2.22, 0.082, 0.100), (2.265, 0.066, 0.082), (2.293, 0.036, 0.046), (2.302, 0.006, 0.008)]
rings = [ring((0, 0.008 if z_ > 2.1 else 0.0, z_), rx, ry, 10, rot=math.pi / 10) for z_, rx, ry in hz]
loft_z(rings, Z_SKIN, cap0=Z_SKIN, cap1=Z_SKIN)
tag(f0, 'head')
# the coat: collar, shoulders, chest, down to a ragged hem at mid-shin
f0 = len(k.bm.faces)
rng = np.random.default_rng(7)
cz = [(1.95, 0.075, 0.075), (1.91, 0.20, 0.105), (1.85, 0.215, 0.11), (1.70, 0.175, 0.115), (1.52, 0.150, 0.105),
      (1.35, 0.140, 0.100), (1.15, 0.165, 0.120), (0.90, 0.195, 0.150), (0.62, 0.220, 0.170), (0.38, 0.240, 0.185)]
hem_j = [1.0 + 0.10 * rng.uniform(-1, 1) for _ in range(12)]
rings = []
for i, (z_, rx, ry) in enumerate(cz):
    rr = ring((0, 0.02, z_), rx, ry, 12)
    if i == len(cz) - 1:                                             # ragged hem: tatters up and down
        rr = [p + Vector((0, 0, 0.07 * (hem_j[j] - 1.0) * 4)) for j, p in enumerate(rr)]
    rings.append(rr)
loft_z(rings, Z_COAT, cap0=None, cap1=None)
inner = [list(reversed(r)) for r in rings[5:]]                       # the lining seen under the hem
loft_z(inner, Z_DARK)                                                 # (the same surface facing in: dark lining)
tag(f0, 'coat')
# sleeves and hands
for s, sx in (('L', 1), ('R', -1)):
    f0 = len(k.bm.faces)
    sh, el, wr = Vector(B[f'UpperArm.{s}'][0]), Vector(B[f'ForeArm.{s}'][0]), Vector(B[f'Hand.{s}'][0])
    limb([sh + Vector((sx * -0.02, 0, 0.0)), sh.lerp(el, 0.5), el, el.lerp(wr, 0.5), wr + Vector((0, 0, 0.03))],
         [0.062, 0.050, 0.046, 0.042, 0.048], Z_COAT, n=7)
    tag(f0, f'arm.{s}')
    f0 = len(k.bm.faces)
    hand_top = wr + Vector((0, 0, 0.02))
    palm = wr + Vector((sx * 0.005, -0.012, -0.08))
    limb([hand_top, wr.lerp(palm, 0.5), palm], [0.024, 0.028, 0.022], Z_SKIN, n=6)
    for j, (dx, dy) in enumerate(((-0.018, -0.012), (-0.006, -0.018), (0.007, -0.017), (0.018, -0.010))):
        b0 = palm + Vector((sx * dx, dy * 0.5, -0.01))
        pts = [b0, b0 + Vector((sx * dx * 0.3, -0.006, -0.07)), b0 + Vector((sx * dx * 0.4, -0.016, -0.14)),
               b0 + Vector((sx * dx * 0.4, -0.010 - 0.01 * j % 2, -0.19 + 0.02 * (j in (0, 3))))]
        limb(pts, [0.0075, 0.0065, 0.0055, 0.004], Z_SKIN, n=4)
    tag(f0, f'hand.{s}')
    # legs below the hem: thin shins and long bare feet
    f0 = len(k.bm.faces)
    kn, an, to = Vector(B[f'Shin.{s}'][0]), Vector(B[f'Foot.{s}'][0]), Vector(B[f'Foot.{s}'][1])
    limb([kn + Vector((0, 0, 0.05)), kn, kn.lerp(an, 0.5), an + Vector((0, 0, 0.02))], [0.040, 0.042, 0.034, 0.028], Z_LEG, n=6)
    tag(f0, f'leg.{s}')
    f0 = len(k.bm.faces)
    limb([an + Vector((0, 0.045, -0.035)), an + Vector((0, 0.0, -0.05)), an.lerp(to, 0.6) + Vector((0, 0, -0.015)),
          to + Vector((0, 0.01, -0.006))], [0.026, 0.036, 0.032, 0.014], Z_LEG, n=6)
    tag(f0, f'foot.{s}')
# the face: dark eye hollows and the mouth slit (faces on the front of the head by position)
k.bm.faces.ensure_lookup_table()
for i, f in enumerate(k.bm.faces):
    if PART.get(i) != 'head':
        continue
    c = f.calc_center_median()
    if c.y < -0.05 and ((2.135 < c.z < 2.20 and 0.012 < abs(c.x) < 0.07) or (2.05 < c.z < 2.085 and abs(c.x) < 0.035)):
        f[k.zl] = Z_DARK
ob = k.to_object('Apparition_Body', pivot=Vector((0, 0, 0)))
me = ob.data
part_of_face = [PART.get(i, 'coat') for i in range(len(me.polygons))]
log('mesh', len(me.vertices), 'verts', P.tri_count(ob), 'tris')

# ------------------------------------------------------------------ armature
arm_d = bpy.data.armatures.new('Apparition_Rig')
arm = bpy.data.objects.new('Apparition_Rig', arm_d)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in B.items():
    eb = arm_d.edit_bones.new(name)
    eb.head, eb.tail = Vector(h), Vector(t)
    eb.roll = 0.0
for name, (h, t, par) in B.items():
    if par:
        eb = arm_d.edit_bones[name]
        eb.parent = arm_d.edit_bones[par]
        eb.use_connect = (Vector(arm_d.edit_bones[par].tail) - Vector(h)).length < 1e-4
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------------------ weights: each part to its chain, by distance to the bones
CHAINS = {'head': ['Neck', 'Head'], 'coat': ['Hips', 'Spine', 'Chest', 'Neck', 'Thigh.L', 'Thigh.R', 'Shin.L', 'Shin.R',
                                             'Shoulder.L', 'Shoulder.R'],
          'arm.L': ['Shoulder.L', 'UpperArm.L', 'ForeArm.L', 'Chest'], 'arm.R': ['Shoulder.R', 'UpperArm.R', 'ForeArm.R', 'Chest'],
          'hand.L': ['ForeArm.L', 'Hand.L'], 'hand.R': ['ForeArm.R', 'Hand.R'],
          'leg.L': ['Thigh.L', 'Shin.L'], 'leg.R': ['Thigh.R', 'Shin.R'], 'foot.L': ['Shin.L', 'Foot.L'], 'foot.R': ['Shin.R', 'Foot.R']}
vpart = {}
for p, pt in zip(me.polygons, part_of_face):
    for vi in p.vertices:
        vpart.setdefault(vi, pt)
groups = {n: ob.vertex_groups.new(name=n) for n in B if n != 'Root'}


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length


SPINE_Z = [('Hips', 1.32), ('Spine', 1.58), ('Chest', 1.88), ('Neck', 9.0)]   # the trunk by height, blended 6 cm at the joints


def trunk_weights(z):
    out = {}
    lo = -9.0
    for i, (n, top) in enumerate(SPINE_Z):
        if z < top:
            out[n] = 1.0
            if i + 1 < len(SPINE_Z) and z > top - 0.06:              # into the next bone above
                t = (z - (top - 0.06)) / 0.12
                out = {n: 1.0 - t, SPINE_Z[i + 1][0]: t}
            elif i > 0 and z < lo + 0.06:                            # out of the bone below
                t = 0.5 + (z - lo) / 0.12
                out = {SPINE_Z[i - 1][0]: 1.0 - t, n: t}
            return out
        lo = top
    return {'Neck': 1.0}


for v in me.vertices:
    pt = vpart.get(v.index, 'coat')
    cand = CHAINS[pt]
    p = v.co
    if pt == 'coat':                                                 # the skirt follows the thigh of its side
        if p.z < 1.10:
            cand = ['Hips', 'Thigh.L', 'Shin.L'] if p.x > 0.03 else (['Hips', 'Thigh.R', 'Shin.R'] if p.x < -0.03 else
                                                                     ['Hips', 'Thigh.L', 'Thigh.R'])
        elif p.z > 1.80 and abs(p.x) > 0.10:
            cand = ['Chest', 'Shoulder.L' if p.x > 0 else 'Shoulder.R', 'UpperArm.L' if p.x > 0 else 'UpperArm.R']
        else:                                                        # the trunk: rigid along the spine, blended at the joints
            for n, w in trunk_weights(p.z).items():
                if w > 0.03:
                    groups[n].add([v.index], w, 'REPLACE')
            continue
    ds = [(seg_dist(p, Vector(B[n][0]), Vector(B[n][1])), n) for n in cand]
    ds.sort()
    ws = [(1.0 / (d + 0.02) ** 3, n) for d, n in ds[:3]]
    tot = sum(w for w, n in ws)
    for w, n in ws:
        if w / tot > 0.03:
            groups[n].add([v.index], w / tot, 'REPLACE')
mod = ob.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
ob.parent = arm

# ------------------------------------------------------------------ the atlas (rest pose)
ob['_atlas'] = 'Figure'


def paint_fig(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 4101)
    T = _T(n_lo, n_hi)
    z = Pp[:, 2]
    col = np.tile(lin(60, 56, 52), (n, 1))
    m = Z == Z_COAT                                                  # a long coat gone grey-brown, wet and rotten at the hem
    c = T(lin(58, 54, 50), 0.18, 0.16)
    folds = ss(0.55, 0.80, fbm(Pp * np.array([2.0, 2.0, 0.25], np.float32), 9.0, 3, seed=4102))
    c = mixc(c, lin(96, 90, 82), folds * 0.45)
    c = mixc(c, lin(30, 28, 26), cav * 0.6)
    c = mixc(c, lin(44, 40, 30), ss(0.75, 0.40, z) * 0.6)                                   # wet, muddy hem
    c = mixc(c, lin(110, 104, 92), ss(0.80, 0.90, fbm(Pp, 50.0, 2, seed=4103)) * 0.35)        # threadbare spots
    col[m] = c[m]
    m = Z == Z_SKIN                                                  # grey-white skin, veins, darker in the hollows
    c = T(lin(196, 198, 190), 0.10, 0.12)
    veins = ss(0.48, 0.50, fbm(Pp, 30.0, 3, seed=4104)) * ss(0.5, 0.52, fbm(Pp, 30.0, 3, seed=4104) + 0.02)
    c = mixc(c, lin(120, 130, 140), np.clip(veins * 4.0, 0, 0.5))
    c = mixc(c, lin(110, 106, 100), cav * 0.7)
    c = mixc(c, lin(150, 150, 140), ss(0.5, 0.8, n_mid) * 0.3)
    col[m] = c[m]
    m = Z == Z_DARK
    col[m] = T(lin(14, 12, 12), 0.1, 0.1)[m]
    m = Z == Z_LEG                                                   # legs and feet: darker, dirty
    c = T(lin(132, 130, 122), 0.12, 0.14)
    c = mixc(c, lin(70, 62, 52), ss(0.20, 0.0, z) * 0.7 + cav * 0.5)
    col[m] = c[m]
    return col, np.zeros(n, np.float32)


INFO['atlases'] = {}
if DRAFT:
    BC.draft([ob], lambda z: {Z_COAT: (58, 54, 50), Z_SKIN: (196, 198, 190), Z_DARK: (14, 12, 12), Z_LEG: (132, 130, 122)}[z])
else:
    ob.modifiers['Armature'].show_render = False
    prep = BC.prep_atlas([ob], 64.0, max_size=512)
    PB.finish_atlas('Figure', [ob], prep, paint_fig, TEX, prefix='T_Fig_', mat_prefix='M_Fig_', ao_min=0.45, ao_dist=0.08,
                    rough=0.85, log=log, info=INFO['atlases'])
    ob.modifiers['Armature'].show_render = True
BC.psx_uv_only()
mat = ob.data.materials[0]
mat.name = 'M_Apparition'

# ------------------------------------------------------------------ poses and clips
pb = arm.pose.bones
for b in pb:
    b.rotation_mode = 'QUATERNION'


def rot_world(bone, axis, deg):
    """a rotation about a world axis (rest pose) as the bone's local quaternion"""
    R = arm_d.bones[bone].matrix_local.to_3x3()
    Q = Matrix.Rotation(math.radians(deg), 3, Vector(axis))
    return (R.inverted() @ Q @ R).to_quaternion()


def qmul(*qs):
    out = Quaternion()
    for q in qs:
        out = out @ q
    return out


def clear():
    for b in pb:
        b.rotation_quaternion = Quaternion()
        b.location = Vector()


def key_all(frame):
    for b in pb:
        b.keyframe_insert('rotation_quaternion', frame=frame)
        b.keyframe_insert('location', frame=frame)


def stand_base():
    clear()
    pb['Spine'].rotation_quaternion = rot_world('Spine', (1, 0, 0), 6)          # (+ about x: leaning forward, to -y)
    pb['Chest'].rotation_quaternion = rot_world('Chest', (1, 0, 0), 10)
    pb['Neck'].rotation_quaternion = rot_world('Neck', (1, 0, 0), 14)
    pb['Head'].rotation_quaternion = qmul(rot_world('Head', (0, 1, 0), 9), rot_world('Head', (1, 0, 0), 6))
    for s, sx in (('L', 1), ('R', -1)):
        pb[f'UpperArm.{s}'].rotation_quaternion = rot_world(f'UpperArm.{s}', (0, 1, 0), sx * 3)
        pb[f'ForeArm.{s}'].rotation_quaternion = rot_world(f'ForeArm.{s}', (1, 0, 0), -8)
        pb[f'Hand.{s}'].rotation_quaternion = rot_world(f'Hand.{s}', (1, 0, 0), -10)


def new_action(name):
    act = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = act
    return act


actions = {}
# Stand
actions['Stand'] = new_action('Stand')
stand_base()
key_all(1)
key_all(2)
# Walk: 30 frames = 1.25 s, contact at 1 / 16, stride +-28 deg at the hip; keyed on every frame. The stance foot stays flat
# and planted (the root goes up and down so that the lowest point of the mesh is on the ground, z = 0); the swing foot
# clears the ground (the swing knee bends more where it would scrape)
actions['Walk'] = new_action('Walk')
NF = 30


def leg_phase(ph, s):
    """(thigh angle, swing amount) of a leg: stance (half the loop) from 28 deg in front to 28 deg behind at an even pace
    (the foot keeps still on the ground while the object moves), the swing back to the front eased in and out"""
    u = ((ph - math.pi / 2) / TAU + (0.0 if s == 'L' else 0.5)) % 1.0
    if u < 0.5:
        return -28.0 + 56.0 * (u / 0.5), 0.0
    t = (u - 0.5) / 0.5
    return 28.0 - 56.0 * t * t * (3 - 2 * t), math.sin(math.pi * t)


def walk_pose(f, knee_extra=None):
    ph = TAU * f / NF
    stand_base()
    lifts = {}
    for s in ('L', 'R'):
        th, lift = leg_phase(ph, s)                                  # th: + behind, - in front (rotation about x)
        sw = -th / 28.0                                              # +1: the leg forward
        sh = 8 + 55 * lift ** 1.5 + (knee_extra or {}).get(s, 0.0)
        lifts[s] = lift
        heel = 34 * max(0.0, -sw) ** 2 * max(0.0, 1.0 - lift / 0.35)      # the trailing foot rolls onto its toes, lets go slowly
        pb[f'Thigh.{s}'].rotation_quaternion = rot_world(f'Thigh.{s}', (1, 0, 0), th)
        pb[f'Shin.{s}'].rotation_quaternion = rot_world(f'Shin.{s}', (1, 0, 0), sh)
        pb[f'Foot.{s}'].rotation_quaternion = rot_world(f'Foot.{s}', (1, 0, 0), -(th + sh) + 10 * lift + heel)  # flat; toes drop in the swing
        pb[f'UpperArm.{s}'].rotation_quaternion = qmul(rot_world(f'UpperArm.{s}', (0, 1, 0), (1 if s == 'L' else -1) * 3),
                                                       rot_world(f'UpperArm.{s}', (1, 0, 0), 9 * sw))   # the arm back while its leg is in front
    pb['Hips'].location = Vector((0.0, 0.0, 0.0))
    pb['Hips'].rotation_quaternion = rot_world('Hips', (0, 0, 1), 5 * math.sin(ph))
    pb['Head'].rotation_quaternion = qmul(rot_world('Head', (0, 1, 0), 9), rot_world('Head', (1, 0, 0), 6 + 3 * math.sin(2 * ph)))
    return lifts


FOOTV = {s: [v.index for v in me.vertices if any(g.group == ob.vertex_groups[f'Foot.{s}'].index and g.weight > 0.3
                                                  for g in v.groups)] for s in ('L', 'R')}


def foot_low():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    out = {s: min((ob.matrix_world @ m2.vertices[i].co).z for i in FOOTV[s]) for s in FOOTV}
    allz = min((ob.matrix_world @ v.co).z for v in m2.vertices)
    e.to_mesh_clear()
    return out, allz


arm.animation_data.action = None                                    # solve on the bare pose, then key
extra = {}
for f in range(0, NF):
    ke = {'L': 0.0, 'R': 0.0}
    for it in range(14):
        lifts = walk_pose(f, ke)
        low, _ = foot_low()
        sw_ = max(lifts, key=lifts.get)
        st_ = 'R' if sw_ == 'L' else 'L'
        if lifts[sw_] < 0.05:
            break
        need = 0.04 * min(1.0, lifts[sw_] / 0.4)
        if low[sw_] - low[st_] >= need:
            break
        ke[sw_] += 4.0
    extra[f] = ke
# smooth the extra knee bend over the loop (a pop in one frame would show), then plant the root
sm = {}
for f in range(NF):
    sm[f] = {s: max(extra[(f + d) % NF][s] for d in (-1, 0, 1)) for s in ('L', 'R')}
sm = {f: {s: (sm[(f - 1) % NF][s] + 2 * sm[f][s] + sm[(f + 1) % NF][s]) / 4 for s in ('L', 'R')} for f in range(NF)}
root_z = {}
for f in range(NF):
    walk_pose(f, sm[f])
    _, allz = foot_low()
    root_z[f] = -allz
arm.animation_data.action = actions['Walk']
RR = arm_d.bones['Root'].matrix_local.to_3x3().inverted()
for f in range(0, NF + 1):
    walk_pose(f % NF, sm[f % NF])
    pb['Root'].location = RR @ Vector((0.0, 0.0, root_z[f % NF]))
    key_all(f + 1)
INFO['walk_root_z'] = {f + 1: round(root_z[f], 4) for f in range(NF)}
# the object's speed for the stance foot not to slide: the left foot's centre over its flat stance (frames 13 -> 19)
FOOTC = FOOTV['L']


def foot_y(frame):
    sc.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    y = sum((ob.matrix_world @ m2.vertices[i].co).y for i in FOOTC) / len(FOOTC)
    e.to_mesh_clear()
    return y


INFO['walk_speed'] = round((foot_y(19) - foot_y(13)) / (6 / FPS), 3)
INFO['walk_knee_extra'] = {f + 1: {s: round(v, 1) for s, v in sm[f].items()} for f in range(NF)}
# Sit: the pelvis on the seat at the origin, the feet flat on a floor SEAT_H below it (the van's benches: seat top
# 0.425 m over the floor, VAN3_CONTRACT Sit_L* / Sit_R*); the root drop and the shin bend are solved on the mesh
SEAT_H = 0.425
SIT = dict(root=-1.03, shin=78.0, lean=44.0, fore=-45.0)    # lean: the torso's forward bend from the hips (deg); fore: the forearms
CEIL = 0.705                # the van's roof: 0.709 m over its bench tops (COL_RoofRear underside 1.94, seats 1.231)
WALL = 0.24                 # the van's side wall behind the bench: 0.25 m behind the sit point (Sit_L* y 0.65, wall 0.90)


def sit_pose(e=0.0, neck=24.0):
    """e = 0: Sit (hunched under a low roof, the shoulders up, the neck bent so the head hangs forward and tips to
    one side); e = 1: the end of SitLook (the head turned to its front-left - the cab, from the van's left bench - and
    raised as far as the roof lets it). neck: the neck's forward bend (solved against the roof)"""
    clear()
    L = SIT['lean']
    pb['Root'].location = arm_d.bones['Root'].matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, SIT['root']))
    pb['Hips'].rotation_quaternion = rot_world('Hips', (1, 0, 0), 4)
    pb['Spine'].rotation_quaternion = rot_world('Spine', (1, 0, 0), 0.45 * (L - 4))
    pb['Chest'].rotation_quaternion = rot_world('Chest', (1, 0, 0), 0.55 * (L - 4))
    pb['Neck'].rotation_quaternion = rot_world('Neck', (1, 0, 0), neck)
    pb['Head'].rotation_quaternion = qmul(rot_world('Head', (0, 0, 1), 95 * e), rot_world('Head', (0, 1, 0), -26 * (1 - e)),
                                          rot_world('Head', (1, 0, 0), 14 - 18 * e))
    for s, sx in (('L', 1), ('R', -1)):
        pb[f'Shoulder.{s}'].rotation_quaternion = rot_world(f'Shoulder.{s}', (0, 1, 0), -sx * 10)          # shrugged up
        pb[f'Thigh.{s}'].rotation_quaternion = qmul(rot_world(f'Thigh.{s}', (0, 0, 1), sx * 6),
                                                    rot_world(f'Thigh.{s}', (1, 0, 0), -96))
        pb[f'Shin.{s}'].rotation_quaternion = rot_world(f'Shin.{s}', (1, 0, 0), SIT['shin'])
        pb[f'Foot.{s}'].rotation_quaternion = rot_world(f'Foot.{s}', (1, 0, 0), 96 - SIT['shin'])      # flat on the floor
        # the long arms hang from the bent torso between the knees, the fingertips just over the floor
        pb[f'UpperArm.{s}'].rotation_quaternion = qmul(rot_world(f'UpperArm.{s}', (0, 1, 0), sx * 4),
                                                       rot_world(f'UpperArm.{s}', (1, 0, 0), -L - 8))
        pb[f'ForeArm.{s}'].rotation_quaternion = rot_world(f'ForeArm.{s}', (1, 0, 0), SIT['fore'])   # forward, down between the knees
        pb[f'Hand.{s}'].rotation_quaternion = rot_world(f'Hand.{s}', (1, 0, 0), -SIT['fore'] * 0.8)   # the fingers hang to the floor


SEATV = [v.index for v in me.vertices if vpart.get(v.index, 'coat') == 'coat']
BODYV = [v.index for v in me.vertices if vpart.get(v.index, 'coat') != 'head']
HANDV = [v.index for v in me.vertices if vpart.get(v.index, 'coat').startswith('hand')]


def sit_lows():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    vs = [ob.matrix_world @ v.co for v in m2.vertices]
    feet = min(vs[i].z for s in FOOTV for i in FOOTV[s])
    seat = min(vs[i].z for i in SEATV if -0.25 <= vs[i].y <= 0.15)    # under the pelvis and the back of the thighs
    top = max(v.z for v in vs)
    back = max(v.y for v in vs)
    low = min(v.z for v in vs)
    body = max(vs[i].z for i in BODYV)                               # all but the head
    hands = min(vs[i].z for i in HANDV)
    e.to_mesh_clear()
    return feet, seat, top, back, low, body, hands


def neck_for(e_):
    """the least neck bend that keeps the figure under the roof at look e_"""
    lo_, hi_ = 0.0, 60.0
    for _ in range(18):
        mid = (lo_ + hi_) / 2
        sit_pose(e_, mid)
        if sit_lows()[2] > CEIL:
            lo_ = mid
        else:
            hi_ = mid
    return hi_


arm.animation_data.action = None
for it in range(3):
    sit_pose(0.0, 40.0)
    seat = sit_lows()[1]
    SIT['root'] -= seat                                              # the buttocks on the seat (z = 0)
    lo_, hi_ = 30.0, 96.0                                            # less bend: the feet forward and up
    for _ in range(24):
        SIT['shin'] = (lo_ + hi_) / 2
        sit_pose(0.0, 40.0)
        if sit_lows()[0] < -SEAT_H:
            hi_ = SIT['shin']
        else:
            lo_ = SIT['shin']
    lo_, hi_ = 20.0, 85.0                                            # the least lean that brings the back under the roof
    for _ in range(18):
        SIT['lean'] = (lo_ + hi_) / 2
        sit_pose(0.0, 60.0)
        if sit_lows()[5] > CEIL:
            lo_ = SIT['lean']
        else:
            hi_ = SIT['lean']
    SIT['lean'] = hi_ + 10.0                                         # the shoulders a little lower: room for the head
    lo_, hi_ = -85.0, 0.0                                            # the forearms: the fingertips 5 mm over the floor
    for _ in range(18):
        SIT['fore'] = (lo_ + hi_) / 2
        sit_pose(0.0, 60.0)
        if sit_lows()[6] < -SEAT_H + 0.005:
            hi_ = SIT['fore']
        else:
            lo_ = SIT['fore']
    SIT['fore'] = lo_
LOOK = [(1, 0.0), (4, 0.25), (8, 0.6), (11, 0.9), (15, 1.0)]
NECK = {f: max(neck_for(t * t * (3 - 2 * t)), 60.0 * (1 - t * t * (3 - 2 * t))) for f, t in LOOK}   # bowed, then up to the roof
checks = {}
for f, t in LOOK:
    sit_pose(t * t * (3 - 2 * t), NECK[f])
    feet, seat, top, back, low, body, hands = sit_lows()
    checks[f] = dict(neck=round(NECK[f], 1), top=round(top, 3), back=round(back, 3), low=round(low, 3), seat=round(seat, 3),
                     hands=round(hands, 3))
INFO['sit'] = dict(seat_h=SEAT_H, ceiling=CEIL, wall=WALL, root=round(SIT['root'], 4), shin=round(SIT['shin'], 2),
                   lean=round(SIT['lean'], 2), fore=round(SIT['fore'], 2), frames=checks)
SIT_OK = all(c['back'] <= WALL and c['low'] >= -SEAT_H - 0.002 and c['top'] <= CEIL + 0.002 for c in checks.values())
log('sit checks', SIT_OK, checks)
actions['Sit'] = new_action('Sit')
sit_pose(0.0, NECK[1])
key_all(1)
key_all(2)
# SitLook: 0.6 s (15 frames) from Sit: the head turns to the front-left and lifts as far as the roof lets it, then holds
actions['SitLook'] = new_action('SitLook')
for f, t in LOOK:
    sit_pose(t * t * (3 - 2 * t), NECK[f])
    key_all(f)
for a in actions.values():
    a.use_fake_user = True
    for fc in a.fcurves if hasattr(a, 'fcurves') else []:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR' if a.name == 'Walk' else 'BEZIER'
arm.animation_data.action = actions['Stand']
clear()

# ------------------------------------------------------------------ checks: the poses' extents
def extents(action, frame):
    arm.animation_data.action = actions[action]
    sc.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    vs = np.array([tuple(ob.matrix_world @ v.co) for v in m2.vertices])
    e.to_mesh_clear()
    return vs.min(0).round(3).tolist(), vs.max(0).round(3).tolist()


INFO['walk_floor'] = {f: extents('Walk', f)[0][2] for f in range(1, NF + 2)}       # the lowest point per frame


def feet_at(frame):
    arm.animation_data.action = actions['Walk']
    sc.frame_set(frame)
    low, _ = foot_low()
    return {k_: round(v, 3) for k_, v in low.items()}


INFO['walk_feet'] = {f: feet_at(f) for f in range(1, NF + 2)}
INFO['extents'] = {'Stand': extents('Stand', 1), 'Walk_0': extents('Walk', 1), 'Walk_8': extents('Walk', 8),
                   'Sit': extents('Sit', 1), 'SitLook_end': extents('SitLook', 15)}
arm.animation_data.action = actions['Stand']
sc.frame_set(1)
INFO['clips'] = {'Stand': [1, 2], 'Walk': [1, NF + 1], 'Sit': [1, 2], 'SitLook': [1, 15]}
INFO['fps'] = FPS
INFO['tris'] = P.tri_count(ob)
INFO['bones'] = list(B)
INFO['material'] = mat.name
log('extents', INFO['extents'])
sfx = '_draft' if DRAFT else ''
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'fig{sfx}.blend'))
json.dump(BC.nz(INFO), open(os.path.join(OUT, f'fig{sfx}.json'), 'w'), indent=1)
log('saved fig' + sfx)
