"""forest_smoke 2.0 (out/smoke.blend or the package's smoke.blend) -> one FBX per root for Unity, the pager's export settings
(forward -Z, up Y, Apply Transform): each root at the origin with its parts as children (their origins = their pivots),
COL_ left out (the colliders come from the contract). Copies the textures the materials use next to the models.
blender -b --factory-startup <smoke.blend> --python tools/snow_style/work/forest_smoke/smoke2_export.py -- <unity_dir>
-> <unity_dir>/Models/<root>.fbx, <unity_dir>/Textures/*.png"""
import bpy, sys, os, json, shutil
from mathutils import Matrix

ROOTS = ['Item_CigPack_Harzgold', 'Item_CigPack_Brocken', 'Item_CigPack_Nordlicht', 'Item_Lighter', 'Cigarette']


def main():
    out = sys.argv[sys.argv.index('--') + 1]
    models, textures = os.path.join(out, 'Models'), os.path.join(out, 'Textures')
    os.makedirs(models, exist_ok=True)
    os.makedirs(textures, exist_ok=True)
    for c in bpy.data.collections:
        c.hide_viewport = False
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
        lc.hide_viewport = False
    report = []
    for name in ROOTS:
        root = bpy.data.objects[name]
        root.matrix_world = Matrix.Identity(4)
        bpy.context.view_layer.update()
        keep = [root] + [o for o in root.children_recursive if o.type == 'MESH' and not o.name.startswith('COL_')]
        bpy.ops.object.select_all(action='DESELECT')
        for o in keep:
            o.hide_set(False)
            o.hide_viewport = False
            o.select_set(True)
        bpy.context.view_layer.objects.active = root
        fp = os.path.join(models, name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=fp, use_selection=True, use_visible=False, object_types={'MESH'},
                                 global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                                 use_mesh_modifiers=True, mesh_smooth_type='FACE', use_subsurf=False,
                                 use_mesh_edges=False, use_tspace=False, use_triangles=False, use_custom_props=False,
                                 colors_type='NONE', add_leaf_bones=False, bake_anim=False,
                                 path_mode='STRIP', embed_textures=False, batch_mode='OFF')
        mats = sorted({s.material.name for o in keep for s in o.material_slots if s.material})
        report.append(dict(file=fp, objects=[o.name for o in keep], materials=mats,
                           tris=sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in keep)))
    n = 0
    for im in bpy.data.images:
        if im.source == 'FILE' and im.filepath and im.users:
            src = bpy.path.abspath(im.filepath)
            if os.path.exists(src) and not os.path.basename(src).startswith('T_Black'):
                shutil.copy2(src, os.path.join(textures, os.path.basename(src)))
                n += 1
    print('[export] ' + json.dumps(dict(roots=report, textures=n)), flush=True)


main()
