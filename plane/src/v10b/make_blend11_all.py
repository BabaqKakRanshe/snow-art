"""One Blender file with everything (v10): plane v10 (out/plane_unity_v10.blend, the scene UtilityPlane.fbx was exported
from) + winter kit 1.2 installed on it (WinterKit from out/kit_unity_v1.blend, materials re-made PSX on the 1.2
textures) + every separate model (cargo cases, step ladder, key, 12 kit carry items, 6 survival kit items) laid out in
rows beside the left wing + a hidden preview collection with copies of the stowable items at their Socket_Stow_* poses.
Textures stay external, relative to the package folders that sit side by side in assets\\plane:
  plane -> //../Assets/UtilityPlane/Textures, kit -> //../../UtilityPlane_WinterKit_v1_2/Assets/UtilityPlane/Textures.
python3 make_blend9_all.py <pkg root>   (pkg root mirrors assets\\plane: UtilityPlane_Unity_v10/..., UtilityPlane_WinterKit_v1_2/...)"""
import bpy, os, sys, json, math
from mathutils import Vector, Matrix
PKG = sys.argv[-1]
V10TEX = os.path.join(PKG, 'UtilityPlane_Unity_v11', 'Assets', 'UtilityPlane', 'Textures')
KITTEX = os.path.join(PKG, 'UtilityPlane_WinterKit_v1_2', 'Assets', 'UtilityPlane', 'Textures')
OUT = os.path.join(PKG, 'UtilityPlane_Unity_v11', 'Blender', 'UtilityPlane_v11.blend')
GROUND_Z = -0.124                    # main-wheel contact, model frame (level)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_unity_v11.blend')
sc = bpy.context.scene
plane_objs = set(o.name for o in bpy.data.objects)
E9 = json.load(open('/home/claude/plane/out/ext_v9.json'))

# ---------------------------------------------------------------- append the winter kit scene (all 41 objects)
with bpy.data.libraries.load('/home/claude/plane/out/kit_unity_v1.blend', link=False) as (src, dst):
    dst.objects = list(src.objects)
kit = [o for o in dst.objects if o is not None]
assert len(kit) == 41, len(kit)
assert not (set(o.name for o in kit) & plane_objs)
wk = bpy.data.objects['WinterKit']
assert wk.matrix_world.translation.length < 1e-6


# ---------------------------------------------------------------- kit 1.2 materials: PSX (BaseColor + MaskMap, closest)
def psx_mat(name, prefix):
    m = bpy.data.materials.get(name)
    assert m is not None, name
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    L.new(pr.outputs[0], out.inputs[0])
    t = N.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(os.path.join(KITTEX, prefix + '_BaseColor.png'), check_existing=True)
    t.interpolation = 'Closest'
    L.new(t.outputs['Color'], pr.inputs['Base Color'])
    tm = N.new('ShaderNodeTexImage')
    tm.image = bpy.data.images.load(os.path.join(KITTEX, prefix + '_MaskMap.png'), check_existing=True)
    tm.image.colorspace_settings.name = 'Non-Color'
    tm.interpolation = 'Closest'
    sp = N.new('ShaderNodeSeparateColor')
    L.new(tm.outputs['Color'], sp.inputs[0])
    L.new(sp.outputs[0], pr.inputs['Metallic'])
    inv = N.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(tm.outputs['Alpha'], inv.inputs[1])
    L.new(inv.outputs[0], pr.inputs['Roughness'])


psx_mat('M_KitCovers', 'T_KitCovers')
psx_mat('M_KitProps', 'T_KitProps')

# ---------------------------------------------------------------- textures: package-relative
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    for d in (V10TEX, KITTEX):
        if os.path.exists(os.path.join(d, name)):
            im.filepath = os.path.join(d, name)
            break
    else:
        if im.users:
            raise SystemExit(f'texture not found: {name}')
for im in [im for im in bpy.data.images if im.users == 0]:
    bpy.data.images.remove(im)


def coll(title, hidden=False):
    c = bpy.data.collections.new(title)
    sc.collection.children.link(c)
    if hidden:
        bpy.context.view_layer.layer_collection.children[c.name].hide_viewport = True
        c.hide_render = True
    return c


def move(o, c):
    for x in list(o.users_collection):
        x.objects.unlink(o)
    c.objects.link(o)


# ---------------------------------------------------------------- stowed preview copies (before the rows move them)
def sock(name):
    s = E9['sockets'][name]
    return Matrix.Translation(Vector(s['pos'])) @ Matrix(s['rot']).to_4x4()


c_stow = coll('Stowed items - preview copies (Socket_Stow_*)', hidden=True)
for item, sname in (('SM_Surv_Flashlight', 'Socket_Stow_Flashlight'), ('SM_Surv_FlareGun', 'Socket_Stow_FlareGun'),
                    ('SM_Surv_Shovel', 'Socket_Stow_Shovel'), ('SM_Surv_Bag', 'Socket_Stow_SurvivalBag'),
                    ('SM_Kit_JerryCan', 'Socket_Stow_JerryCan')):
    src_o = bpy.data.objects[item]
    root = src_o.copy()
    root.name = 'Stowed_' + item
    c_stow.objects.link(root)
    root.parent = None
    root.matrix_world = sock(sname)                          # items are built around their pivot (identity here)
    for ch in src_o.children:
        if ch.type == 'MESH' and not ch.name.startswith(('COL_', 'IV_')):
            cc = ch.copy()
            cc.name = 'Stowed_' + ch.name
            c_stow.objects.link(cc)
            cc.parent = root
            cc.matrix_parent_inverse = Matrix.Identity(4)
            cc.matrix_basis = src_o.matrix_world.inverted() @ ch.matrix_world
lad, legs = bpy.data.objects['SM_StepLadder'], bpy.data.objects['Ladder_RearLegs']
lc = lad.copy()
lc.name = 'Stowed_SM_StepLadder'
c_stow.objects.link(lc)
lc.parent = None
lc.matrix_world = sock('Socket_Stow_Ladder')
gc = legs.copy()
gc.name = 'Stowed_Ladder_RearLegs'
c_stow.objects.link(gc)
gc.parent = lc
gc.matrix_parent_inverse = Matrix.Identity(4)
gc.matrix_basis = (lad.matrix_world.inverted() @ legs.matrix_world) @ Matrix.Rotation(math.radians(-38), 4, 'X')
move(bpy.data.objects['Stow_LadderStraps'], c_stow)        # straps and battens: only with the stowed ladder

# ---------------------------------------------------------------- collections
c_kit = coll('Winter kit 1.2 - installed (WinterKit)')
for o in [wk] + list(wk.children_recursive):
    move(o, c_kit)
prop_roots = sorted([o for o in bpy.data.objects if o.parent is None and o.name.startswith(('SM_Cargo', 'SM_StepLadder',
                                                                                          'SM_PlaneKey'))],
                    key=lambda o: o.name)
kit_roots = sorted([o for o in bpy.data.objects if o.parent is None and o.name.startswith('SM_Kit_')], key=lambda o: o.name)
surv_roots = sorted([o for o in bpy.data.objects if o.parent is None and o.name.startswith('SM_Surv_')], key=lambda o: o.name)
c_props = coll('Separate models (own FBX, laid out beside the plane)')
for r in prop_roots + kit_roots + surv_roots:
    for o in [r] + list(r.children_recursive):
        move(o, c_props)
HIDDEN = [
    ('LOD (LODGroup, Data/lod.json)', lambda o: '_LOD' in o.name),
    ('Colliders and zones (COL_*, IV_*)', lambda o: o.name.startswith(('COL_', 'IV_'))),
    ('Glass fog (Glass_Fog, *_Fog)', lambda o: o.name == 'Glass_Fog' or o.name.endswith('_Fog')),
    ('Prop blur and disc', lambda o: o.name in ('PropBlur', 'PropDisc')),
    ('Belts fastened (Belt_*_On)', lambda o: o.name.startswith('Belt_') and o.name.endswith('_On')),
    ('Survival bag strap (shown while secured)', lambda o: o.name == 'Surv_Bag_Strap'),
    ('Shadow proxies (*_Shadow, shadow only in Unity)', lambda o: o.name.endswith('_Shadow')),     # v10
]
moved = {}
for title, pred in HIDDEN:
    c = coll(title, hidden=True)
    objs = [o for o in bpy.data.objects if pred(o) and not o.name.startswith('Stowed_')]
    for o in objs:
        move(o, c)
    moved[title] = len(objs)
print('hidden', moved, flush=True)

# ---------------------------------------------------------------- lay the separate models out in rows (left side)


def bbox(r):
    pts = []
    for o in [r] + list(r.children_recursive):
        if o.type == 'MESH' and not o.name.startswith(('COL_', 'IV_')):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def row(roots, x_in, y0, gap=0.35):
    y = y0
    for r in roots:
        lo, hi = bbox(r)
        d = Vector((x_in - lo.x, y - lo.y, GROUND_Z - lo.z))
        r.location += d
        y += (hi.y - lo.y) + gap
    return y


bpy.context.view_layer.update()
end1 = row(prop_roots, 8.6, -5.0)
bpy.context.view_layer.update()
end2 = row(kit_roots, 10.4, -5.0)
bpy.context.view_layer.update()
end3 = row(surv_roots, 12.2, -5.0, gap=0.25)
print('rows end y', round(end1, 2), round(end2, 2), round(end3, 2), flush=True)

assert not [o for o in bpy.data.objects if o.type in ('CAMERA', 'LIGHT')]
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
paths = sorted({im.filepath for im in bpy.data.images if im.source == 'FILE'})
print('image paths', len(paths), [p for p in paths if 'Kit' in p][:4], flush=True)
assert all(p.startswith(('//../Assets/UtilityPlane/Textures/', '//../../UtilityPlane_WinterKit_v1_2/Assets/UtilityPlane/Textures/'))
           for p in paths), paths

bpy.ops.wm.open_mainfile(filepath=OUT)
missing = [im.filepath for im in bpy.data.images if im.source == 'FILE' and not os.path.exists(bpy.path.abspath(im.filepath))]
print('reopened objects', len(bpy.data.objects), 'images', len(bpy.data.images), 'missing', missing,
      'collections', [c.name for c in bpy.data.collections], 'size MB', round(os.path.getsize(OUT) / 1e6, 2), flush=True)
assert not missing
