"""Lesnik blockout (26.10.2026): the chosen look of docs/gdd/monsters/02_lesnik (concept_v4, 3b + 3d) as plain shapes on
the skeleton the final model will keep. Not the final art: flat colours, no atlas.

The figure: about 3.1 m straight, ~2.6 m in its hunched stance; faceless long head with two white eye points set wide and a
vertical black slit mouth; knitted cap; olive parka down to mid-thigh with short ragged sleeves; very long arms with four
needle fingers each (to the floor); thin bare legs. The neck is a chain of 6 loose bones (Neck1..Neck6): the clip
NeckReach slides each one along its parent, so the neck stretches and the head travels to the player while the body
stays (the "тянет голову" feature).

Clips (in place, 24 fps):
  Stand      hunched: the back bent forward, the neck broken down and forward, the head hanging almost upside down,
             the arms hanging, the fingertips at the floor (1 frame)
  NeckReach  1 s from Stand: the neck straightens forward and stretches to 6x (about 3 m), the head turned to the front,
             then holds (frames 1-25)

Frame: Blender x left of the figure, y back (the figure faces -y), z up; FBX forward -Z, up Y, not baked (as Apparition):
Unity sees it facing +z, origin between the feet.

blender -b --factory-startup --python lesnik_blockout.py -- <out_dir>   ->  Lesnik_Blockout.blend / .fbx / .json
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix, Quaternion

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = ARGS[0] if ARGS else os.path.dirname(os.path.abspath(__file__))
K = float(ARGS[ARGS.index('--k') + 1]) if '--k' in ARGS else 1.0     # skeleton scale: the hunched top at 2.60 m (solved by rerun)
BACK = 30.0                                                         # forward bend of the back in Stand (deg)
os.makedirs(OUT, exist_ok=True)
FPS = 24
TAU = 2 * math.pi
INFO = {}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS

# ------------------------------------------------------------------ bones (rest: standing straight, arms down)
NECK_N, NECK_L = 6, 0.09
B = {
    'Root': ((0, 0, 0), (0, 0.12, 0), None),
    'Hips': ((0, 0, 1.40), (0, 0, 1.55), 'Root'),
    'Spine': ((0, 0, 1.55), (0, 0.01, 1.85), 'Hips'),
    'Chest': ((0, 0.01, 1.85), (0, 0.02, 2.25), 'Spine'),
}
z = 2.25
for i in range(1, NECK_N + 1):
    B[f'Neck{i}'] = ((0, 0.02, z), (0, 0.02, z + NECK_L), 'Chest' if i == 1 else f'Neck{i - 1}')
    z += NECK_L
B['Head'] = ((0, 0.02, z), (0, 0.02, z + 0.32), f'Neck{NECK_N}')
for s, sx in (('L', 1), ('R', -1)):
    B[f'Shoulder.{s}'] = ((sx * 0.04, 0.02, 2.20), (sx * 0.22, 0.02, 2.22), 'Chest')
    B[f'UpperArm.{s}'] = ((sx * 0.22, 0.02, 2.22), (sx * 0.25, 0.02, 1.45), f'Shoulder.{s}')
    B[f'ForeArm.{s}'] = ((sx * 0.25, 0.02, 1.45), (sx * 0.27, 0.01, 0.70), f'UpperArm.{s}')
    B[f'Hand.{s}'] = ((sx * 0.27, 0.01, 0.70), (sx * 0.28, 0.0, 0.58), f'ForeArm.{s}')
    for j, (dx, dy) in enumerate(((-0.030, -0.010), (-0.010, -0.022), (0.012, -0.020), (0.030, -0.006))):
        h = Vector((sx * 0.28 + sx * dx, dy, 0.58))
        B[f'Finger{j + 1}.{s}'] = (tuple(h), tuple(h + Vector((sx * dx * 0.4, dy * 0.8, -0.38))), f'Hand.{s}')
    B[f'Thigh.{s}'] = ((sx * 0.10, 0.0, 1.38), (sx * 0.11, -0.01, 0.74), 'Hips')
    B[f'Shin.{s}'] = ((sx * 0.11, -0.01, 0.74), (sx * 0.115, 0.02, 0.09), f'Thigh.{s}')
    B[f'Foot.{s}'] = ((sx * 0.115, 0.02, 0.09), (sx * 0.12, -0.22, 0.02), f'Shin.{s}')
B = {n: (tuple(c * K for c in h), tuple(c * K for c in t_), p) for n, (h, t_, p) in B.items()}
NECK_L *= K

# ------------------------------------------------------------------ materials (flat colours, sRGB 0-255)
MATS = {}


def mat(name, rgb, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    lin = tuple(((c / 255) ** 2.2) for c in rgb) + (1.0,)    # Blender works in linear; Unity reads FBX colours as sRGB -> fixed there
    bsdf.inputs['Base Color'].default_value = lin
    bsdf.inputs['Roughness'].default_value = 0.9
    if emit:
        bsdf.inputs['Emission Color'].default_value = lin
        bsdf.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = lin
    MATS[name] = m
    return m


for n, c, e in (('M_Lesnik_Skin', (112, 110, 104), 0), ('M_Lesnik_Parka', (66, 70, 48), 0), ('M_Lesnik_Cap', (40, 36, 33), 0),
                ('M_Lesnik_Eye', (255, 255, 250), 6.0), ('M_Lesnik_Mouth', (6, 5, 5), 0)):
    mat(n, c, e)
MAT_IDX = {n: i for i, n in enumerate(MATS)}

# ------------------------------------------------------------------ the mesh: tubes, each ring rigid to one bone
bm = bmesh.new()
VBONE = {}          # vertex index -> bone


def frame_for(t):
    t = t.normalized()
    ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    e1 = t.cross(ref).normalized()
    e2 = t.cross(e1).normalized()
    return e1, e2


def tube(pts, radii, bones, matname, n=8, cap0=True, cap1=True, jag=None, squash=(1.0, 1.0)):
    rings = []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        e1, e2 = frame_for(t)
        ring = []
        for k in range(n):
            a = TAU * k / n
            r = radii[i] * (1.0 if jag is None else jag(i, k))
            v = bm.verts.new(p + e1 * math.cos(a) * r * squash[0] + e2 * math.sin(a) * r * squash[1])
            ring.append(v)
        rings.append(ring)
    bm.verts.index_update()
    for ring, b in zip(rings, bones):
        for v in ring:
            VBONE[v] = b
    mi = MAT_IDX[matname]
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(n):
            f = bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
            f.material_index = mi
    if cap0:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mi
    if cap1:
        f = bm.faces.new(rings[-1])
        f.material_index = mi


def blob(center, size, bone, matname, subdiv=1):
    r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in r['verts']:
        v.co = Vector(center) + Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        VBONE[v] = bone
    for f in {f for v in r['verts'] for f in v.link_faces}:
        f.material_index = MAT_IDX[matname]


V = lambda name, end=0: Vector(B[name][end])

# head: a long smooth egg along the Head bone (rest: pointing up), the face to -y
hz0 = V('Head').z
prof = [(0.00, 0.050), (0.03, 0.075), (0.08, 0.095), (0.15, 0.100), (0.22, 0.094), (0.28, 0.074), (0.31, 0.040), (0.32, 0.008)]
tube([V('Head') + Vector((0, 0, dz)) for dz, _ in prof], [r for _, r in prof], ['Head'] * len(prof), 'M_Lesnik_Skin', n=10,
     squash=(1.0, 0.92))
# eyes: small, set too wide, on the front; the mouth: a vertical slit down the middle of the face
for sx in (1, -1):
    blob((sx * 0.062, 0.02 - 0.086, hz0 + 0.20), (0.012, 0.008, 0.012), 'Head', 'M_Lesnik_Eye')
mouth = bmesh.ops.create_cube(bm, size=1.0)
for v in mouth['verts']:
    v.co = Vector((v.co.x * 0.012, 0.02 - 0.094 + v.co.y * 0.012, hz0 + 0.11 + v.co.z * 0.17))
    VBONE[v] = 'Head'
for f in {f for v in mouth['verts'] for f in v.link_faces}:
    f.material_index = MAT_IDX['M_Lesnik_Mouth']
# cap: a knitted beanie over the back of the skull
tube([V('Head') + Vector((0, 0.012, dz)) for dz in (0.17, 0.24, 0.30, 0.345)], [0.106, 0.104, 0.088, 0.03],
     ['Head'] * 4, 'M_Lesnik_Cap', n=10, cap0=False)
# neck: one tube, a ring at every joint rigid to the bone that starts there (stretches when the bones slide apart)
neck_pts = [V(f'Neck{i}') for i in range(1, NECK_N + 1)] + [V('Head') + Vector((0, 0, 0.02))]
tube(neck_pts, [0.040, 0.034, 0.030, 0.029, 0.029, 0.031, 0.040], [f'Neck{i}' for i in range(1, NECK_N + 1)] + ['Head'],
     'M_Lesnik_Skin', n=7)
# torso skin (thin, mostly under the parka) and the parka: chest to mid-thigh, ragged hem
tube([V('Hips') + Vector((0, 0, -0.05)), V('Spine'), V('Chest'), V('Chest', 1) + Vector((0, 0, -0.03))],
     [0.11, 0.10, 0.13, 0.09], ['Hips', 'Spine', 'Chest', 'Chest'], 'M_Lesnik_Skin', n=8, squash=(1.0, 0.7))
jag = lambda i, k: (1.0 + 0.18 * math.sin(k * 2.7) ** 3) if i == 0 else 1.0
tube([V('Hips') + Vector((0, 0.01, -0.42)), V('Hips') + Vector((0, 0.01, -0.10)), V('Spine'), V('Chest'),
      V('Chest', 1) + Vector((0, 0, -0.05)), V('Neck1') + Vector((0, 0, 0.04))],
     [0.20, 0.17, 0.15, 0.20, 0.19, 0.07], ['Hips', 'Hips', 'Spine', 'Chest', 'Chest', 'Chest'], 'M_Lesnik_Parka', n=12,
     cap0=False, cap1=False, jag=jag, squash=(1.0, 0.72))
for s, sx in (('L', 1), ('R', -1)):
    sh, el, wr = V(f'UpperArm.{s}'), V(f'ForeArm.{s}'), V(f'Hand.{s}')
    tube([sh, el, wr, V(f'Hand.{s}', 1)], [0.032, 0.026, 0.020, 0.024],
         [f'UpperArm.{s}', f'ForeArm.{s}', f'Hand.{s}', f'Hand.{s}'], 'M_Lesnik_Skin', n=6)
    # short ragged sleeve: shoulder to just below the elbow
    tube([sh + Vector((sx * -0.03, 0, 0.03)), sh.lerp(el, 0.5), el + (wr - el) * 0.18],
         [0.07, 0.055, 0.052], [f'Shoulder.{s}', f'UpperArm.{s}', f'ForeArm.{s}'], 'M_Lesnik_Parka', n=7,
         cap0=False, cap1=False, jag=lambda i, k: (1.0 + 0.2 * math.sin(k * 3.1) ** 3) if i == 2 else 1.0)
    for j in range(1, 5):
        fb = f'Finger{j}.{s}'
        h, t = V(fb), V(fb, 1)
        tube([h, h.lerp(t, 0.5), t], [0.0085, 0.0065, 0.002], [fb, fb, fb], 'M_Lesnik_Skin', n=4)
    th, kn, an, to = V(f'Thigh.{s}'), V(f'Shin.{s}'), V(f'Foot.{s}'), V(f'Foot.{s}', 1)
    tube([th, kn, an], [0.055, 0.036, 0.026], [f'Thigh.{s}', f'Shin.{s}', f'Foot.{s}'], 'M_Lesnik_Skin', n=6)
    tube([an + Vector((0, 0.04, -0.04)), an.lerp(to, 0.5) + Vector((0, 0, -0.04)), to],
         [0.03, 0.032, 0.012], [f'Foot.{s}'] * 3, 'M_Lesnik_Skin', n=6)

bm.normal_update()
me = bpy.data.meshes.new('Lesnik_Body')
bm.verts.index_update()
vb = {v.index: VBONE[v] for v in bm.verts}
bm.to_mesh(me)
bm.free()
for m in MATS.values():
    me.materials.append(m)
ob = bpy.data.objects.new('Lesnik_Body', me)
sc.collection.objects.link(ob)
for p in me.polygons:
    p.use_smooth = False
INFO['tris'] = sum(len(p.vertices) - 2 for p in me.polygons)

# ------------------------------------------------------------------ armature + rigid weights
arm_d = bpy.data.armatures.new('Lesnik_Rig')
arm = bpy.data.objects.new('Lesnik_Rig', arm_d)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, par) in B.items():
    eb = arm_d.edit_bones.new(name)
    eb.head, eb.tail, eb.roll = Vector(h), Vector(t), 0.0
for name, (h, t, par) in B.items():
    if par:
        eb = arm_d.edit_bones[name]
        eb.parent = arm_d.edit_bones[par]
        eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
groups = {n: ob.vertex_groups.new(name=n) for n in B if n != 'Root'}
for vi, b in vb.items():
    groups[b].add([vi], 1.0, 'REPLACE')
mod = ob.modifiers.new('Armature', 'ARMATURE')
mod.object = arm
ob.parent = arm

# ------------------------------------------------------------------ poses and clips
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


def clear():
    for b in pb:
        b.rotation_quaternion = Quaternion()
        b.location = Vector()


def key_all(frame):
    for b in pb:
        b.keyframe_insert('rotation_quaternion', frame=frame)
        b.keyframe_insert('location', frame=frame)


def evaluated_z():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    m2 = e.to_mesh()
    zs = [(ob.matrix_world @ v.co) for v in m2.vertices]
    e.to_mesh_clear()
    return zs


BEND = {'back': 0.0}


def stand_pose(back, neck_reach=0.0, stretch=1.0, aim=16):
    """back: forward bend of the back (deg, + to -y); neck_reach 0..1: from broken-down to straight forward;
    stretch: neck length factor (bones slide apart along their length); aim: where the reached neck points, deg below
    the horizontal (16: a standing player's face; negative: up to a first-floor window)"""
    clear()
    pb['Spine'].rotation_quaternion = rot_world('Spine', (1, 0, 0), back * 0.35)
    pb['Chest'].rotation_quaternion = rot_world('Chest', (1, 0, 0), back * 0.65)
    # the neck: broken forward and down (Stand) -> straight out in front (NeckReach)
    down = [10, 6, 6, 78, 22, 12]                       # a sharp break in the middle of the neck
    out_ = [-(back) + 90 + aim, 0, 0, 0, 0, 0]         # the first bone points the neck forward and 16 deg down (to a
                                                        # standing player's face 3-3.5 m away), the rest straight
    for i in range(NECK_N):
        a = down[i] * (1 - neck_reach) + out_[i] * neck_reach
        pb[f'Neck{i + 1}'].rotation_quaternion = rot_world(f'Neck{i + 1}', (1, 0, 0), a)
        if i > 0:
            pb[f'Neck{i + 1}'].location = Vector((0, NECK_L * (stretch - 1.0), 0))   # along the parent bone (its y)
    pb['Head'].location = Vector((0, NECK_L * (stretch - 1.0), 0))
    # head: hanging almost upside down in Stand (face to the front, tipped); in NeckReach turned to face forward
    pb['Head'].rotation_quaternion = qmul(rot_world('Head', (0, 1, 0), 14 * (1 - neck_reach)),
                                          rot_world('Head', (1, 0, 0), 40 * (1 - neck_reach) - 106 * neck_reach),
                                          Quaternion((0, 1, 0), math.radians(180 * (1 - neck_reach))))   # twisted round on the neck:
    # hanging upside down, the face still turns to the front (the player); it untwists while the neck reaches out
    for s, sx in (('L', 1), ('R', -1)):
        pb[f'Shoulder.{s}'].rotation_quaternion = rot_world(f'Shoulder.{s}', (0, 1, 0), -sx * 6)
        # arms hang straight down from the bent torso (undo the back bend), a little forward
        pb[f'UpperArm.{s}'].rotation_quaternion = qmul(rot_world(f'UpperArm.{s}', (0, 1, 0), sx * 4),
                                                       rot_world(f'UpperArm.{s}', (1, 0, 0), -back * 0.6 - 10))
        pb[f'ForeArm.{s}'].rotation_quaternion = rot_world(f'ForeArm.{s}', (1, 0, 0), -10)
        for j in range(1, 5):
            pb[f'Finger{j}.{s}'].rotation_quaternion = rot_world(f'Finger{j}.{s}', (1, 0, 0), 8 + 4 * j)
        pb[f'Thigh.{s}'].rotation_quaternion = rot_world(f'Thigh.{s}', (1, 0, 0), -14)
        pb[f'Shin.{s}'].rotation_quaternion = rot_world(f'Shin.{s}', (1, 0, 0), 22)
        pb[f'Foot.{s}'].rotation_quaternion = rot_world(f'Foot.{s}', (1, 0, 0), -8)


# the hunched stance with a fixed back bend; the top is reported (K is chosen so that it is 2.60 m)
TARGET_TOP = 2.60
BEND['back'] = BACK
stand_pose(BEND['back'])
vs = evaluated_z()
ROOT_Z = -min(v.z for v in vs)
RR = arm_d.bones['Root'].matrix_local.to_3x3().inverted()


def place_root():
    pb['Root'].location = RR @ Vector((0, 0, ROOT_Z))


actions = {}


def new_action(name):
    act = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = act
    act.use_fake_user = True
    actions[name] = act
    return act


new_action('Stand')
stand_pose(BEND['back'])
place_root()
key_all(1)
key_all(2)
new_action('NeckReach')
STRETCH = 6.0
for f, t in ((1, 0.0), (5, 0.15), (10, 0.45), (15, 0.75), (20, 0.95), (25, 1.0)):
    e = t * t * (3 - 2 * t)
    stand_pose(BEND['back'], neck_reach=e, stretch=1.0 + (STRETCH - 1.0) * e)
    place_root()
    key_all(f)

# ------------------------------------------------------------------ the logic's clips (blockout quality: keyed, feet not solved)
# signs: about x, + tips a down-pointing bone (legs, arms) back (+y), - forward; the figure faces -y


def rx(bone, deg):
    return rot_world(bone, (1, 0, 0), deg)


def root_at(dz=0.0, dy=0.0):
    pb['Root'].location = RR @ Vector((0, dy, ROOT_Z + dz))


def shuffle_pose(ph):
    """Shuffle (2 s loop): short dragging steps, the knees hardly lift, a slow sway of the hanging arms"""
    stand_pose(BEND['back'])
    for s, sgn in (('L', 1), ('R', -1)):
        sw = math.sin(ph + (0 if s == 'L' else math.pi))                 # +1: this leg forward
        lift = max(0.0, math.sin(ph + (0 if s == 'L' else math.pi) + math.pi / 2)) ** 2
        pb[f'Thigh.{s}'].rotation_quaternion = rx(f'Thigh.{s}', -14 - 16 * sw)
        pb[f'Shin.{s}'].rotation_quaternion = rx(f'Shin.{s}', 22 + 18 * lift)
        pb[f'UpperArm.{s}'].rotation_quaternion = qmul(rot_world(f'UpperArm.{s}', (0, 1, 0), sgn * 4),
                                                       rx(f'UpperArm.{s}', -BEND['back'] * 0.6 - 10 + 7 * sw))
    pb['Hips'].rotation_quaternion = rot_world('Hips', (0, 0, 1), 4 * math.sin(ph))
    root_at(dz=-0.03 * abs(math.cos(ph)))


def carry_arms(k=1.0, side=('L', 'R')):
    """both long arms folded, the stolen things pressed to the chest"""
    for s in side:
        pb[f'UpperArm.{s}'].rotation_quaternion = rx(f'UpperArm.{s}', (-BEND['back'] * 0.6 - 10) * (1 - k) + (-22) * k)
        pb[f'ForeArm.{s}'].rotation_quaternion = rx(f'ForeArm.{s}', -10 * (1 - k) - 92 * k)
        for j in range(1, 5):
            pb[f'Finger{j}.{s}'].rotation_quaternion = rx(f'Finger{j}.{s}', (8 + 4 * j) * (1 - k) - 70 * k)


new_action('Shuffle')                                                   # 48 frames = 2 s
for f in range(0, 49, 4):
    shuffle_pose(TAU * f / 48)
    key_all(f + 1)

new_action('Grab')                                                      # 1 s: reach down, close the fingers, to the chest
for f, reach, close, home in ((1, 0, 0, 0), (8, 0.7, 0, 0), (12, 1, 0, 0), (15, 1, 1, 0), (20, 1, 1, 0.6), (25, 1, 1, 1)):
    stand_pose(BEND['back'])
    pb['Spine'].rotation_quaternion = rx('Spine', BEND['back'] * 0.35 + 18 * reach * (1 - home))
    if home > 0:
        carry_arms(home, ('R',))
    else:
        pb['UpperArm.R'].rotation_quaternion = rx('UpperArm.R', -BEND['back'] * 0.6 - 10 - 38 * reach)
        pb['ForeArm.R'].rotation_quaternion = rx('ForeArm.R', -10 - 20 * reach)
    if home == 0:
        for j in range(1, 5):
            pb[f'Finger{j}.R'].rotation_quaternion = rx(f'Finger{j}.R', 8 + 4 * j - 70 * close)
    root_at()
    key_all(f)

new_action('Carry')                                                     # pose loop: Stand with the arms folded on the chest
stand_pose(BEND['back'])
carry_arms()
root_at()
key_all(1)
key_all(2)

new_action('Cower')                                                     # 0.4 s: caught by the light - a hand over the face,
for f, k in ((1, 0.0), (4, 0.7), (7, 1.0), (10, 1.0)):                  # the head jerks back and away, then holds
    stand_pose(BEND['back'] * (1 - 0.6 * k))
    pb['Spine'].rotation_quaternion = rx('Spine', BEND['back'] * 0.35 * (1 - k) - 8 * k)
    pb['UpperArm.R'].rotation_quaternion = rx('UpperArm.R', (-BEND['back'] * 0.6 - 10) * (1 - k) - 38 * k)   # forward,
    pb['ForeArm.R'].rotation_quaternion = rx('ForeArm.R', -10 * (1 - k) - 138 * k)                         # folded back to the face
    for i, a in enumerate((10, 6, 6, 78, 22, 12)):                         # the broken neck folds tighter
        pb[f'Neck{i + 1}'].rotation_quaternion = rx(f'Neck{i + 1}', a * (1 + 0.35 * k))
    pb['Head'].rotation_quaternion = qmul(pb['Head'].rotation_quaternion, rot_world('Head', (0, 0, 1), 55 * k))
    root_at()
    key_all(f)

new_action('Flee')                                                      # 1 s loop: huge low leaps, 2 strides per loop
for f in range(0, 25, 2):
    ph = TAU * f / 24
    stand_pose(BEND['back'] + 22)
    for s, sgn in (('L', 1), ('R', -1)):
        sw = math.sin(ph + (0 if s == 'L' else math.pi))
        pb[f'Thigh.{s}'].rotation_quaternion = rx(f'Thigh.{s}', -20 - 50 * sw)
        pb[f'Shin.{s}'].rotation_quaternion = rx(f'Shin.{s}', 30 + 45 * max(0.0, -sw))
        pb[f'UpperArm.{s}'].rotation_quaternion = rx(f'UpperArm.{s}', -BEND['back'] * 0.6 - 30 + 40 * sw)
    root_at(dz=0.22 * abs(math.sin(ph)) - 0.02)                           # in the air between the strides
    key_all(f + 1)
INFO['flee_stride_m'] = 3.0                                             # the object moves ~6 m/s with Flee (2 strides/s)

new_action('NeckReachUp')                                               # NeckReach aimed 40 deg up: the head at a
for f, t in ((1, 0.0), (5, 0.15), (10, 0.45), (15, 0.75), (20, 0.95), (25, 1.0)):   # first-floor window (kitchen)
    e = t * t * (3 - 2 * t)
    stand_pose(BEND['back'], neck_reach=e, stretch=1.0 + (STRETCH - 1.0) * e, aim=-40)
    place_root()
    key_all(f)

new_action('Sleep')                                                     # pose loop: curled on his side on the cave bed
stand_pose(BEND['back'] + 20)
carry_arms()
for s in ('L', 'R'):
    pb[f'Thigh.{s}'].rotation_quaternion = rx(f'Thigh.{s}', -75)
    pb[f'Shin.{s}'].rotation_quaternion = rx(f'Shin.{s}', 110)
pb['Root'].rotation_quaternion = rot_world('Root', (0, 1, 0), 90)
pb['Root'].location = Vector()
vs = evaluated_z()
lowest, mid_x = min(v.z for v in vs), (min(v.x for v in vs) + max(v.x for v in vs)) / 2   # on the ground, centred
pb['Root'].location = RR @ Vector((-mid_x, 0, 0.02 - lowest))
key_all(1)
key_all(2)
INFO['shuffle_speed_mps'] = 0.6


def extents(action, frame):
    arm.animation_data.action = actions[action]
    sc.frame_set(frame)
    vs_ = evaluated_z()
    return ([round(min(v[i] for v in vs_), 3) for i in range(3)], [round(max(v[i] for v in vs_), 3) for i in range(3)])


def head_pos(action, frame):
    arm.animation_data.action = actions[action]
    sc.frame_set(frame)
    bpy.context.view_layer.update()
    return [round(c, 3) for c in (arm.matrix_world @ pb['Head'].head)]


INFO['back_bend_deg'] = round(BEND['back'], 2)
INFO['k'] = K
INFO['stand_top'] = round(INFO.get('_top', 0), 3)
INFO['root_drop'] = round(ROOT_Z, 3)
INFO['extents'] = {'Stand': extents('Stand', 1), 'NeckReach_end': extents('NeckReach', 25), 'Grab_reach': extents('Grab', 12),
                   'Cower_end': extents('Cower', 10), 'Flee_up': extents('Flee', 7), 'Flee_down': extents('Flee', 13)}
INFO['head'] = {'Stand': head_pos('Stand', 1), 'NeckReach_end': head_pos('NeckReach', 25)}
INFO['neck_stretch'] = STRETCH
INFO['neck_length_m'] = {'Stand': round(NECK_N * NECK_L, 3), 'NeckReach_end': round(NECK_N * NECK_L * STRETCH, 3)}
INFO['clips'] = {'Stand': [1, 2], 'NeckReach': [1, 25], 'Shuffle': [1, 49], 'Grab': [1, 25], 'Carry': [1, 2],
                 'Cower': [1, 10], 'Flee': [1, 25], 'NeckReachUp': [1, 25], 'Sleep': [1, 2]}
INFO['head']['NeckReachUp_end'] = head_pos('NeckReachUp', 25)
INFO['extents']['Sleep'] = extents('Sleep', 1)
INFO['fps'] = FPS
INFO['bones'] = list(B)
INFO['materials'] = list(MATS)
INFO['height_straight'] = round(max(Vector(h).z for h, t, p in B.values()) + 0.32, 3)
arm.animation_data.action = actions['Stand']
sc.frame_set(1)
print('[lesnik] ' + json.dumps(INFO), flush=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Lesnik_Blockout.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in (arm, ob):
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Lesnik_Blockout.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         axis_forward='-Z', axis_up='Y', bake_space_transform=False, apply_unit_scale=True,
                         mesh_smooth_type='FACE', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                         bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                         bake_anim_simplify_factor=0.0, path_mode='STRIP')
json.dump(INFO, open(os.path.join(OUT, 'Lesnik_Blockout.json'), 'w'), indent=1)
print('[lesnik] saved to ' + OUT, flush=True)
