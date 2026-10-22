"""Pack Unity textures, build final materials, join static parts, export FBX.
usage: python3 finalize.py <tag> [door_open_deg]"""
import bpy, os, sys, math
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'test'
DOOR_DEG = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
TEX = os.path.join(HERE, 'tex', TAG)
EXP = os.path.join(HERE, 'export', TAG)
UNITY_TEX = os.path.join(EXP, 'Assets', 'UtilityPlane', 'Textures')
UNITY_MOD = os.path.join(EXP, 'Assets', 'UtilityPlane', 'Models')
os.makedirs(UNITY_TEX, exist_ok=True)
os.makedirs(UNITY_MOD, exist_ok=True)


# ---------------------------------------------------------------- texture packing (numpy)
def load(p, mode):
    im = Image.open(p)
    if im.mode.startswith('I;16') or im.mode == 'I':
        a = np.array(im).astype(np.float32) / 65535.0
    else:
        a = np.asarray(im.convert(mode)).astype(np.float32) / 255.0
    return a


for atlas in ('Airframe', 'Details'):
    base = os.path.join(TEX, f'T_{atlas}_')
    bc = Image.open(base + 'BaseColor.png').convert('RGB')
    mr = load(base + 'MR.png', 'RGB')
    ao = load(base + 'AO.png', 'L')
    metal, rough = mr[..., 0], mr[..., 1]
    smooth = 1.0 - rough
    ao = np.clip(ao, 0, 1)
    to8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    ms = np.dstack([metal, metal, metal, smooth])
    mask = np.dstack([metal, ao, np.zeros_like(ao), smooth])
    bc.save(os.path.join(UNITY_TEX, f'T_{atlas}_BaseColor.png'))
    Image.fromarray(to8(ms), 'RGBA').save(os.path.join(UNITY_TEX, f'T_{atlas}_MetallicSmoothness.png'))
    Image.fromarray(to8(mask), 'RGBA').save(os.path.join(UNITY_TEX, f'T_{atlas}_MaskMap.png'))
    Image.fromarray(to8(ao), 'L').save(os.path.join(UNITY_TEX, f'T_{atlas}_AO.png'))
    # normal: keep 16-bit
    nrm = Image.open(base + 'Normal.png')
    nrm.save(os.path.join(UNITY_TEX, f'T_{atlas}_Normal.png'))
    print('packed', atlas)

# ---------------------------------------------------------------- blender scene
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_src_{TAG}.blend'))
O, MAT = bpy.data.objects, bpy.data.materials


def teximg(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def final_material(name, atlas):
    m = MAT.get(name) or MAT.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(pr.outputs[0], out.inputs[0])
    p = lambda s: os.path.join(UNITY_TEX, f'T_{atlas}_{s}.png')
    t_bc = nt.nodes.new('ShaderNodeTexImage')
    t_bc.image = teximg(p('BaseColor'), False)
    nt.links.new(t_bc.outputs['Color'], pr.inputs['Base Color'])
    t_ms = nt.nodes.new('ShaderNodeTexImage')
    t_ms.image = teximg(p('MetallicSmoothness'), True)
    t_ms.image.alpha_mode = 'CHANNEL_PACKED'
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t_ms.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[0], pr.inputs['Metallic'])
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(t_ms.outputs['Alpha'], inv.inputs[1])
    nt.links.new(inv.outputs[0], pr.inputs['Roughness'])
    t_n = nt.nodes.new('ShaderNodeTexImage')
    t_n.image = teximg(p('Normal'), True)
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(t_n.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], pr.inputs['Normal'])
    t_ao = nt.nodes.new('ShaderNodeTexImage')  # not connected: kept for reference / Unity
    t_ao.image = teximg(p('AO'), True)
    t_ao.label = 'AO (use as Occlusion in Unity)'
    for i, n in enumerate([t_bc, t_ms, t_n, t_ao]):
        n.location = (-700, 300 - i * 300)
    sep.location, inv.location, nm.location = (-400, 0), (-250, -100), (-300, -350)
    pr.location, out.location = (0, 0), (350, 0)
    return m


M_A = final_material('M_Airframe', 'Airframe')
M_D = final_material('M_Details', 'Details')
M_L = MAT['M_Lights']
MAP = {'src_Livery': M_A, 'src_Struts': M_A, 'src_InteriorA': M_A}
for k in ('src_InteriorD', 'src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal', 'src_Antenna'):
    MAP[k] = M_D

for ob in O:
    if ob.type != 'MESH':
        continue
    for slot in ob.material_slots:
        if slot.material and slot.material.name in MAP:
            slot.material = MAP[slot.material.name]
    # merge duplicate slots
    me = ob.data
    uniq = []
    remap = []
    for m in me.materials:
        if m not in uniq:
            uniq.append(m)
        remap.append(uniq.index(m))
    if len(uniq) != len(me.materials):
        idx = np.zeros(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get('material_index', idx)
        idx = np.array(remap, dtype=np.int32)[idx]
        me.materials.clear()
        for m in uniq:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', idx)
    for k in ('part', 'wscale'):
        if k in ob.keys():
            del ob[k]

# ---------------------------------------------------------------- join static parts into Body
static = ['src_Fuselage', 'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'src_Struts', 'src_Fin',
          'src_Stabilizer', 'src_CowlDetails', 'src_GearLegs', 'src_Interior', 'src_Antennas', 'src_NavLights'] + \
         [o.name for o in O if o.name.startswith('src_Case')]
bpy.ops.object.select_all(action='DESELECT')
for n in static:
    O[n].select_set(True)
bpy.context.view_layer.objects.active = O['src_Fuselage']
bpy.ops.object.join()
body = O['src_Fuselage']
body.name = 'Body'
body.data.name = 'Body'
# order slots: Airframe, Details, Lights
me = body.data
order = [M_A, M_D, M_L]
cur = list(me.materials)
idx = np.zeros(len(me.polygons), dtype=np.int32)
me.polygons.foreach_get('material_index', idx)
remap = np.array([order.index(m) for m in cur], dtype=np.int32)
me.materials.clear()
for m in order:
    me.materials.append(m)
me.polygons.foreach_set('material_index', remap[idx])

for ob in O:
    if ob.type == 'MESH':
        ob.data.name = ob.name
        ob.data.uv_layers[0].name = 'UVMap'
        if not any(md.type == 'TRIANGULATE' for md in ob.modifiers):
            md = ob.modifiers.new('Triangulate', 'TRIANGULATE')
            md.quad_method = 'BEAUTY'
            md.ngon_method = 'BEAUTY'
            md.keep_custom_normals = True

O['CenterOfMass'].location = (0.0, -1.95, 1.75)  # approx. CG: wing quarter-chord, mid cabin height
# door opened (hinge on the rear edge, rotates about local Z)
O['CargoDoor'].rotation_euler[2] = math.radians(DOOR_DEG)

# tidy: remove source materials from the file except as fake-user library
for m in MAT:
    if m.name.startswith('src_'):
        m.use_fake_user = True

# drop bake-target images (the src materials keep their node trees for re-baking) and pack the rest
for m in MAT:
    if m.node_tree and 'BAKE_TARGET' in m.node_tree.nodes:
        m.node_tree.nodes['BAKE_TARGET'].image = None
for im in list(bpy.data.images):
    if (im.name.startswith('T_Airframe_') or im.name.startswith('T_Details_')) and not im.name.endswith('.png'):
        bpy.data.images.remove(im)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        im.pack()
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_final_{TAG}.blend'))
os.makedirs(os.path.join(EXP, 'Blender'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, 'Blender', 'UtilityPlane.blend'), copy=True, compress=True)

# ---------------------------------------------------------------- FBX export (Unity axes)
# Blender's "Apply Transform" (bake_space_transform) mis-converts objects nested 2+ levels deep
# (TailWheel under TailWheel_Fork). For a pure-rotation axis conversion G, the correct FBX local matrix at any
# depth is G @ L @ G^-1, so patch the exporter to use that for object-under-object parenting.
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import fbx_utils
_orig_mtx = fbx_utils.ObjectWrapper.fbx_object_matrix


def _patched_mtx(self, scene_data, rest=False, local_space=False, global_space=False):
    par = self.parent
    if (not local_space and not global_space and par is not None and self._tag == 'OB' and par._tag == 'OB'
            and not self.parented_to_armature and self.use_bake_space_transform(scene_data)
            and par.use_bake_space_transform(scene_data)):
        L = self.matrix_rest_local if rest else self.matrix_local
        return scene_data.settings.global_matrix @ L @ scene_data.settings.global_matrix_inv
    return _orig_mtx(self, scene_data, rest, local_space, global_space)


fbx_utils.ObjectWrapper.fbx_object_matrix = _patched_mtx
bpy.ops.object.select_all(action='DESELECT')
root = O['UtilityPlane']
for ob in [root] + list(root.children_recursive):
    ob.select_set(True)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(UNITY_MOD, 'UtilityPlane.fbx'),
    use_selection=True, object_types={'EMPTY', 'MESH'},
    global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Z', axis_up='Y', bake_space_transform=True,
    use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, use_triangles=False,
    use_custom_props=False, add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', embed_textures=False, use_metadata=True)
print('exported fbx')
