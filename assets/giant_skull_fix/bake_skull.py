"""Texture for the fixed skull: the new B_Skull + B_Mandible (fix_skull.py) get their own UVs (smart project, packed together)
and a seamless bone surface (T_BoneSurface.png) is baked onto them box-projected (no stretching), darkened by ambient
occlusion in the orbits, nose and gaps. The old atlas is not used: its skull part is itself faceted (per-face UV mess).
Writes <out.fbx> (same names and pivots) and <out.png>.

blender -b --factory-startup --python bake_skull.py -- <Giant_Skeleton.fbx> <Giant_SkullFix.fbx> <bone_surface.png> <out.fbx> <out.png> [px] [tile_m]
"""
import bpy, sys

a = sys.argv[sys.argv.index('--') + 1:]
SRC, FIX, ATLAS, OUT_FBX, OUT_PNG = a[:5]
PX = int(a[5]) if len(a) > 5 else 1024
TILE = float(a[6]) if len(a) > 6 else 14.0     # m of skull per texture repeat (skull ~ 60 m)
NAMES = ('B_Skull', 'B_Mandible')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and ob.name not in NAMES:
        bpy.data.objects.remove(ob, do_unlink=True)
src = {n: bpy.data.objects[n] for n in NAMES}
for n, ob in src.items():
    ob.name = n + '_src'
bpy.ops.import_scene.fbx(filepath=FIX)
new = {n: bpy.data.objects[n] for n in NAMES}

for ob in src.values():
    bpy.data.objects.remove(ob, do_unlink=True)
src = {}

# the new meshes: one UV space for both, a bake target image
img = bpy.data.images.new('T_GiantSkullFix_A', PX, PX, alpha=False)
mnew = bpy.data.materials.new('M_Bone'); mnew.use_nodes = True
nt2 = mnew.node_tree
out = next(n for n in nt2.nodes if n.type == 'OUTPUT_MATERIAL')
coord = nt2.nodes.new('ShaderNodeTexCoord')
mp = nt2.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / TILE, 1 / TILE, 1 / TILE)
surf = nt2.nodes.new('ShaderNodeTexImage'); surf.image = bpy.data.images.load(ATLAS)
surf.projection, surf.projection_blend = 'BOX', 0.35
ao = nt2.nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 5.0; ao.samples = 32
curve = nt2.nodes.new('ShaderNodeMapRange'); curve.inputs['To Min'].default_value = 0.35
mul = nt2.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
em = nt2.nodes.new('ShaderNodeEmission')
nt2.links.new(coord.outputs['Object'], mp.inputs['Vector']); nt2.links.new(mp.outputs['Vector'], surf.inputs['Vector'])
nt2.links.new(ao.outputs['AO'], curve.inputs['Value'])
nt2.links.new(surf.outputs['Color'], mul.inputs[6]); nt2.links.new(curve.outputs['Result'], mul.inputs[7])
nt2.links.new(mul.outputs[2], em.inputs['Color']); nt2.links.new(em.outputs['Emission'], out.inputs['Surface'])
t2 = nt2.nodes.new('ShaderNodeTexImage'); t2.image = img
nt2.nodes.active = t2
bpy.ops.object.select_all(action='DESELECT')
for ob in new.values():
    for uv in list(ob.data.uv_layers):
        ob.data.uv_layers.remove(uv)
    ob.data.uv_layers.new(name='UVMap')
    ob.data.materials.clear(); ob.data.materials.append(mnew)
    ob.select_set(True)
bpy.context.view_layer.objects.active = new['B_Skull']
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 16
bk = sc.render.bake
bk.use_selected_to_active, bk.margin = False, 8
first = True
for n in NAMES:
    bpy.ops.object.select_all(action='DESELECT')
    new[n].select_set(True)
    bpy.context.view_layer.objects.active = new[n]
    bk.use_clear = first
    bpy.ops.object.bake(type='EMIT', use_clear=first)
    first = False
img.filepath_raw = OUT_PNG; img.file_format = 'PNG'; img.save()

for ob in src.values():
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in new.values():
    ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, object_types={'MESH'}, mesh_smooth_type='FACE',
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', add_leaf_bones=False)
print('SAVED', OUT_FBX, OUT_PNG)
