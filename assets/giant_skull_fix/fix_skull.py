"""Giant skull fix: B_Skull (37 loose BodyParts3D pieces, 257 open edges -> holes, torn faces in Unity) and B_Mandible of the
shared Giant_Skeleton.fbx become one closed surface each: voxel remesh -> decimate -> UVs moved over from the original
(nearest face, interpolated) -> smooth shading. Pivots and names stay, so a Unity step swaps the meshes in place.

blender -b --factory-startup --python fix_skull.py -- <Giant_Skeleton.fbx> <out.fbx> [voxel_m] [skull_tris] [jaw_tris] [thick_m]
"""
import bpy, sys

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = args[0], args[1]
VOXEL = float(args[2]) if len(args) > 2 else 0.8
THICK = float(args[5]) if len(args) > 5 else 1.2   # m: thin facial plates thickened before the remesh, so they close
TARGET = {'B_Skull': int(args[3]) if len(args) > 3 else 9000, 'B_Mandible': int(args[4]) if len(args) > 4 else 2500}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
keep = set(TARGET)
for ob in list(bpy.data.objects):
    if ob.name not in keep and ob.type == 'MESH':
        bpy.data.objects.remove(ob, do_unlink=True)


def only(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


for name, tris in TARGET.items():
    src = bpy.data.objects[name]
    before = len(src.data.polygons)
    new = src.copy()
    new.data = src.data.copy()
    bpy.context.collection.objects.link(new)
    only(new)
    # thin plates (face, orbit floors) get thickness first, then one closed surface over the gaps between the pieces
    s = new.modifiers.new('thick', 'SOLIDIFY')
    s.thickness, s.offset, s.use_even_offset, s.use_quality_normals = THICK, 0.0, False, True
    bpy.ops.object.modifier_apply(modifier=s.name)
    m = new.modifiers.new('remesh', 'REMESH')
    m.mode, m.voxel_size, m.adaptivity, m.use_smooth_shade = 'VOXEL', VOXEL, 0.0, True
    bpy.ops.object.modifier_apply(modifier=m.name)
    voxel_faces = len(new.data.polygons)
    d = new.modifiers.new('decimate', 'DECIMATE')
    d.ratio = min(1.0, tris / max(1, voxel_faces * 2 if voxel_faces else 1) * 1.0)
    # remesh gives quads: tris ~ 2 x faces
    d.ratio = min(1.0, tris / max(1.0, 2.0 * voxel_faces))
    bpy.ops.object.modifier_apply(modifier=d.name)
    # UVs back from the original (the bone atlas)
    new.data.uv_layers.new(name='UVMap')
    t = new.modifiers.new('uv', 'DATA_TRANSFER')
    t.object = src
    t.use_loop_data = True
    t.data_types_loops = {'UV'}
    t.loop_mapping = 'POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=t.name)
    bpy.ops.object.shade_smooth()
    new.data.materials.clear()
    for mat in src.data.materials:
        new.data.materials.append(mat)
    tri_count = sum(len(p.vertices) - 2 for p in new.data.polygons)
    bpy.data.objects.remove(src, do_unlink=True)
    new.name = name
    new.data.name = name
    print(f'FIX {name}: {before} faces -> voxel {voxel_faces} quads -> {tri_count} tris, {len(new.data.vertices)} verts')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'MESH'}, mesh_smooth_type='FACE',
                         apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=False, axis_forward='-Z', axis_up='Y',
                         use_mesh_modifiers=True, add_leaf_bones=False)
print('SAVED', OUT)
