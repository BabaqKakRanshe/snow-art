"""forest_station 1.0 (source/assets/forest_station/forest_station.blend) -> one FBX per root for Unity, the steps and
settings of tools/forest_packs/export_fbx.py (as forest_devices / snow_kit): forward -Z, up Y, Apply Transform, scale 1
(FBX_SCALE_ALL), flat shading (FACE), no leaf bones, path STRIP; each root at the origin (its display offset dropped); COL_
left out (the colliders come from the contract). One addition: the Slot_* socket empties go into the FBX too, as child
transforms of the root (Unity imports them as empty GameObjects at posUnity). Then each FBX is imported back and its
pivots, bounds and empties compared with the .blend (1 mm). The .blend is not saved.
blender -b --factory-startup source/assets/forest_station/forest_station.blend --python tools/snow_style/work/forest_station/station_export.py -- <out_dir>
-> <out_dir>/<Root>.fbx, <out_dir>/forest_station_export.json"""
import bpy, sys, os, json
import numpy as np
from mathutils import Matrix

SKIP_PREFIX = ('COL_', 'HIT_', 'LIGHT_')
ROOTS = ['Station_MonitorRack_3x3', 'Station_SideTable']
FBX = dict(use_selection=True, use_visible=False, object_types={'MESH', 'EMPTY'},
           global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
           axis_forward='-Z', axis_up='Y', bake_space_transform=True,
           use_mesh_modifiers=True, mesh_smooth_type='FACE', use_subsurf=False,
           use_mesh_edges=False, use_tspace=False, use_triangles=False, use_custom_props=False,
           colors_type='NONE', add_leaf_bones=False, bake_anim=False,
           path_mode='STRIP', embed_textures=False, batch_mode='OFF')


def r4(v):
    return [round(float(a), 4) + 0.0 for a in v]


def bounds(objs):
    pts = np.array([tuple(o.matrix_world @ v.co) for o in objs if o.type == 'MESH' for v in o.data.vertices])
    return r4(pts.min(0)), r4(pts.max(0))


def export_root(root, out_dir):
    root.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    kids = [o for o in root.children_recursive if o.library is None and not o.name.startswith(SKIP_PREFIX) and
            (o.type == 'MESH' or (o.type == 'EMPTY' and o.name.startswith('Slot_')))]
    for o in kids:
        mw = o.matrix_world.copy()
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = mw
    bpy.context.view_layer.update()
    keep = [root] + kids
    bpy.ops.object.select_all(action='DESELECT')
    for o in keep:
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    fp = os.path.join(out_dir, root.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=fp, **FBX)
    mats = sorted({s.material.name for o in keep if o.type == 'MESH' for s in o.material_slots if s.material})
    imgs = sorted({n.image.name for o in keep if o.type == 'MESH' for s in o.material_slots if s.material and s.material.node_tree
                   for n in s.material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image})
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in keep if o.type == 'MESH')
    want = dict(bounds=bounds([o for o in keep if o.type == 'MESH']),
                empties={o.name: r4(o.matrix_world.translation) for o in kids if o.type == 'EMPTY'})
    print(f'[export] {root.name}: {len(keep)} objects, {tris} tris, materials {mats}', flush=True)
    return fp, dict(file=os.path.basename(fp), objects=[o.name for o in keep], materials=mats, textures=imgs, tris=tris,
                    bytes=os.path.getsize(fp)), want


def verify(fp, want):
    """import the FBX into an empty scene (the importer's defaults: forward -Z, up Y) and compare in Blender axes"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fp)
    objs = list(bpy.data.objects)
    roots = [o for o in objs if o.parent is None]
    got_b = bounds(objs)
    emp = {o.name: r4(o.matrix_world.translation) for o in objs if o.type == 'EMPTY' and o.name.startswith('Slot_')}
    err_b = max(abs(a - b) for lo_hi in zip(got_b, want['bounds']) for a, b in zip(*lo_hi))
    err_e = max([abs(a - b) for k, v in want['empties'].items() for a, b in zip(v, emp.get(k, [9, 9, 9]))] or [0.0])
    scl = [r4(o.matrix_world.to_scale()) for o in objs if o.type == 'MESH']
    return dict(roots=[(o.name, r4(o.matrix_world.translation)) for o in roots], bounds=got_b, bounds_err_m=round(err_b, 5),
                empties=emp, empties_err_m=round(err_e, 5), missing_empties=sorted(set(want['empties']) - set(emp)),
                mesh_world_scale=scl, ok=bool(err_b < 0.001 and err_e < 0.001 and not set(want['empties']) - set(emp)))


def main():
    out_dir = sys.argv[sys.argv.index('--') + 1]
    os.makedirs(out_dir, exist_ok=True)
    blend = bpy.data.filepath
    for c in bpy.data.collections:
        c.hide_viewport = False
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
        lc.hide_viewport = False
    rep, todo = {}, []
    for n in ROOTS:
        fp, r, want = export_root(bpy.data.objects[n], out_dir)
        rep[n] = r
        todo.append((n, fp, want))
    for n, fp, want in todo:
        rep[n]['reimport'] = verify(fp, want)
        print('[verify]', n, json.dumps(rep[n]['reimport']), flush=True)
    rep['_settings'] = {k: (sorted(v) if isinstance(v, set) else v) for k, v in FBX.items()}
    rep['_source'] = os.path.basename(blend)
    json.dump(rep, open(os.path.join(out_dir, 'forest_station_export.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


main()
