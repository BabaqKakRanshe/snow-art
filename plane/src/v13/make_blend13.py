"""v13 Blender files from the v12 ones (same scenes, collections, kit, lights):
 - meshes of Body (+ LOD1/2), CargoDoor_L/R (+ LOD1/2) and the eight exterior Lens_* swapped for the v13 meshes
   (out/plane_unity_v13.blend = the file Models/UtilityPlane.fbx was exported from); Lens_* origins and the eight
   exterior light sockets moved to their v13 places (the Cycles lights of the lights file are children of the sockets);
 - exterior lens materials: T_Lens_BaseColor x lens colour, T_Lens_Emission x emission colour, point-sampled;
 - sliding cargo doors: custom properties cargoDoorL / cargoDoorR (0..1) on the UtilityPlane root drive the doors
   with the formula of UtilityPlaneRig.SlidingDoorPose (simple-expression drivers: no Python auto-run needed; three
   helper empties CargoDoor_*_Ctl hold the intermediate values);
 - lights file: Light_Beacon_Top back on its socket (inside the new lens), every exterior lamp ignores its own lens
   (and the nav / strobe lamps the other lens of the wingtip housing) for shadows.
python3 make_blend13.py <in_v12.blend> <out_v13.blend> <readme_text_name_or_->"""
import bpy, sys, os, math
from mathutils import Matrix

src, dst, readme = sys.argv[-3], sys.argv[-2], sys.argv[-1]
V13 = '/home/claude/plane/out/plane_unity_v13.blend'
L8 = ['Nav_L', 'Nav_R', 'Nav_Tail', 'Strobe_L', 'Strobe_R', 'Beacon_Top', 'Beacon_Bottom', 'Landing']
MESHES = ['Body', 'Body_LOD1', 'Body_LOD2'] + [f'CargoDoor_{s}{l}' for s in 'LR' for l in ('', '_LOD1', '_LOD2')] + \
         ['Lens_' + k for k in L8]
SOCKETS = ['Socket_' + k for k in L8]
NEW_SOCKETS = {'Socket_Handle_CargoDoor_L_Edge': 'CargoDoor_L', 'Socket_Handle_CargoDoor_R_Edge': 'CargoDoor_R'}   # v13.1

bpy.ops.wm.open_mainfile(filepath=src)
O = bpy.data.objects
before = set(O.keys())
mats_before = set(bpy.data.materials.keys())
imgs_before = set(bpy.data.images.keys())
want = MESHES + SOCKETS + list(NEW_SOCKETS)
assert all(NEW_SOCKETS[k] in MESHES for k in NEW_SOCKETS)
with bpy.data.libraries.load(V13, link=False) as (df, dt):
    missing = [n for n in want if n not in df.objects]
    assert not missing, missing
    dt.objects = list(want)
new = dict(zip(want, dt.objects))

# ------------------------------------------------------------------ meshes and transforms
for n in MESHES:
    old, nob = O[n], new[n]
    old_me = old.data
    keep_name = old_me.name
    old.data = nob.data
    old.matrix_basis = nob.matrix_basis.copy()           # local (parent space); v13 moved the Lens_* origins
    if old_me.users == 0:
        bpy.data.meshes.remove(old_me)
    old.data.name = keep_name
    for i, m in enumerate(old.data.materials):            # appended materials -> the file's own (same base name)
        if m is not None and m.name not in mats_before:
            base = m.name.rsplit('.', 1)[0]
            assert base in bpy.data.materials, base
            old.data.materials[i] = bpy.data.materials[base]
for n in SOCKETS:
    O[n].matrix_basis = new[n].matrix_basis.copy()
# v13.1: pull-grip sockets on the cargo doors' front edges (new objects: keep them, parent them to the doors)
added = []
for n, door in NEW_SOCKETS.items():
    nob = new[n]
    ref = O['Socket_Handle_' + door + '_In']                 # same collections as the other door handle sockets
    for c in ref.users_collection:
        if nob.name not in c.objects:
            c.objects.link(nob)
    local = nob.matrix_parent_inverse @ nob.matrix_basis     # relative to the door in the v13 file (appended
    nob.parent = O[door]                                      # objects have no evaluated matrix_world)
    nob.matrix_parent_inverse = Matrix.Identity(4)
    nob.matrix_basis = local
    nob.name = n
    added.append(nob.name)
    before.add(nob.name)
for o in [o for o in O if o.name not in before]:          # the appended objects (and their appended parents)
    bpy.data.objects.remove(o)
for m in [m for m in bpy.data.materials if m.name not in mats_before and m.users == 0]:
    bpy.data.materials.remove(m)
for me in [me for me in bpy.data.meshes if me.users == 0]:
    bpy.data.meshes.remove(me)
for im in [im for im in bpy.data.images if im.name not in imgs_before and im.users == 0]:
    bpy.data.images.remove(im)

# ------------------------------------------------------------------ lens materials (as Unity: texture x colour)
TEX = '//../Assets/UtilityPlane/Textures/'


PKG_TEX = '/home/claude/plane/export/unity_v13/Assets/UtilityPlane/Textures/'


def img(name):
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.load(PKG_TEX + name, check_existing=True)     # load from the package, keep a relative path
        im.name = name
    im.filepath = TEX + name
    if name.endswith('_Emission.png'):
        im.colorspace_settings.name = 'sRGB'
    return im


for mn in ('M_Light_Red', 'M_Light_Green', 'M_Light_White', 'M_Light_Beacon', 'M_Light_Landing'):
    m = bpy.data.materials[mn]
    nt = m.node_tree
    pb = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    if any(n.type == 'TEX_IMAGE' for n in nt.nodes):
        continue
    for sock, im_name, loc in (('Base Color', 'T_Lens_BaseColor.png', (-500, 250)),
                               ('Emission Color', 'T_Lens_Emission.png', (-500, -150))):
        col = tuple(pb.inputs[sock].default_value)
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = img(im_name)
        tx.interpolation = 'Closest'
        tx.location = loc
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        mx.inputs[7].default_value = col
        mx.location = (loc[0] + 280, loc[1])
        nt.links.new(tx.outputs['Color'], mx.inputs[6])
        nt.links.new(mx.outputs[2], pb.inputs[sock])
    pb.inputs['Roughness'].default_value = 0.3                 # smoothness 0.7 as the Unity material

# ------------------------------------------------------------------ sliding doors: drivers
root = O['UtilityPlane']
coll = bpy.data.collections.get('v13 door drivers') or bpy.data.collections.new('v13 door drivers')
if coll.name not in [c.name for c in bpy.context.scene.collection.children]:
    bpy.context.scene.collection.children.link(coll)
X = lambda e: f"min(max({e},0),1)"
x1, x2, x5 = X("d/0.1875"), X("(d-0.0625)/0.1875"), X("(d-0.22)/0.78")


def drv(ob, path, idx, expr, vars_):
    fc = ob.driver_add(path) if idx is None else ob.driver_add(path, idx)
    dr = fc.driver
    dr.type = 'SCRIPTED'
    for v in list(dr.variables):
        dr.variables.remove(v)
    for name, idb, dp in vars_:
        v = dr.variables.new()
        v.name, v.type = name, 'SINGLE_PROP'
        v.targets[0].id = idb
        v.targets[0].data_path = dp
    dr.expression = expr
    assert dr.is_simple_expression, (ob.name, path, expr)


for side, sg in (('L', 1), ('R', -1)):
    prop = f'cargoDoor{side}'
    root[prop] = 0.0
    root.id_properties_ui(prop).update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, step=1,
                                       description=f'v13: sliding cargo door {side}, 0 closed .. 0.25 out .. 1 open '
                                                   '(UtilityPlaneRig.SlidingDoorPose)')
    ctl = O.get(f'CargoDoor_{side}_Ctl') or bpy.data.objects.new(f'CargoDoor_{side}_Ctl', None)
    if ctl.name not in coll.objects:
        coll.objects.link(ctl)
    ctl.empty_display_size = 0.02
    ctl.parent = root
    ctl.location = (0.0, 0.0, 0.0)
    for k in ('of', 'orr0', 'back'):
        ctl[k] = 0.0
    D = [('d', root, f'["{prop}"]')]
    drv(ctl, '["of"]', None, f"0.14*{x1}*{x1}*(3-2*{x1})", D)
    drv(ctl, '["orr0"]', None, f"0.14*{x2}*{x2}*(3-2*{x2})", D)
    drv(ctl, '["back"]', None, f"1.3*{x5}*{x5}*{x5}*(10-15*{x5}+6*{x5}*{x5})", D)
    door = O[f'CargoDoor_{side}']
    rx, ry, rz = door.location
    rot_z = door.rotation_euler.z
    S = X("(b-0.57)/0.73")
    orr = f"(o-0.068*{S}*{S})"
    V = [('o', ctl, '["orr0"]'), ('b', ctl, '["back"]'), ('f', ctl, '["of"]')]
    drv(door, 'location', 0, f"{rx:.4f}{'+' if sg > 0 else '-'}{orr}", V)
    drv(door, 'location', 1, f"{ry:.4f}+b", V)
    drv(door, 'rotation_euler', 2, f"{rot_z:.6f}{'+' if sg > 0 else '-'}atan((f-{orr})/1.294)", V)
for o in coll.objects:
    o.hide_render = True
    try:
        o.hide_set(True)
    except RuntimeError:
        pass

# ------------------------------------------------------------------ lights file: lamps in the new fixtures
lights = {o.name: o for o in O if o.type == 'LIGHT'}
changed_lights = []
if lights:
    lb = lights.get('Light_Beacon_Top')
    if lb is not None:
        lb.location = (0.0, 0.0, 0.0)                          # v12: +3 cm into the old cap; v13 socket is in the lens
        changed_lights.append('Light_Beacon_Top on its socket')
    OWN = {'Nav_L': ['Lens_Nav_L', 'Lens_Strobe_L'], 'Nav_R': ['Lens_Nav_R', 'Lens_Strobe_R'],
           'Strobe_L': ['Lens_Strobe_L', 'Lens_Nav_L'], 'Strobe_R': ['Lens_Strobe_R', 'Lens_Nav_R'],
           'Beacon_Top': ['Lens_Beacon_Top'], 'Beacon_Bottom': ['Lens_Beacon_Bottom'], 'Nav_Tail': ['Lens_Nav_Tail']}
    for key, lens_names in OWN.items():
        L = lights.get('Light_' + key)
        if L is None:
            continue
        bc = L.light_linking.blocker_collection
        if bc is None:
            bc = bpy.data.collections.new(f'SL_{key}_not_blocking')
            L.light_linking.blocker_collection = bc
        for ln in lens_names:
            if ln not in bc.objects:
                bc.objects.link(O[ln])
        for co, ob in zip(bc.collection_objects, bc.objects):
            co.light_linking.link_state = 'EXCLUDE'
        changed_lights.append(f'{L.name}: not blocked by {[o.name for o in bc.objects]}')

# ------------------------------------------------------------------ readme text
NOTE = '''v13 (16.10.2026): lights are part of the aircraft and the cargo doors slide.
- Exterior light fixtures in Body: fin-cap fairing + flange (top beacon), belly doubler + flange (bottom beacon, it hung
  9 cm under the skin in v5-v12), wingtip housings (nav lens nose, gasket, strobe band), tail-cone boss, landing light
  cover following the leading edge in a raised frame. Lens_* meshes are new (UVs into T_Lens); the eight exterior light
  sockets moved into the fixtures (UNITY_CONTRACT.md, section 7.8 and appendix A).
- Lens materials: T_Lens_BaseColor x lens colour, emission T_Lens_Emission x emission colour, point-sampled.
- Sliding cargo doors (UNITY_CONTRACT.md, section 3.1): select the UtilityPlane root, N panel -> Item -> Properties:
  cargoDoorL / cargoDoorR 0..1 (0 closed, 0.25 popped out, 1 slid aft). The drivers are simple expressions (no Python
  auto-run needed); helper empties CargoDoor_L_Ctl / _R_Ctl in the collection "v13 door drivers" (hidden).
  Rails are part of Body, rollers part of the door meshes.
'''
if lights:
    NOTE += '''- Lights: Light_Beacon_Top sits on its socket again (v12 lifted it 3 cm into the old cap); every exterior lamp
  ignores its own lens for shadows (nav / strobe also the other lens of the wingtip housing, as before also Body).
'''
NOTE += '\n'
t = bpy.data.texts.get(readme) if readme != '-' else None
if t is not None:
    body = t.as_string()
    t.clear()
    t.write(NOTE + body)
    t.name = readme.replace('v12', 'v13')
else:
    t = bpy.data.texts.new('README_v13')
    t.write(NOTE)
bpy.context.preferences.filepaths.use_relative_paths = True
os.makedirs(os.path.dirname(dst), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True, relative_remap=False)
print('SAVED', dst, '| new sockets:', added, '| lights:', changed_lights)
