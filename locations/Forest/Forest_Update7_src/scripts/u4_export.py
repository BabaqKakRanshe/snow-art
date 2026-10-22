"""Forest Update 4: one FBX per prefab from the six batch blends, in Update 3's FBX convention.

Update 3's FBX (the location generator's): FBX 7400, Y up, front +Z, X right, UnitScaleFactor 100 (metres), the root node is
the prefab root at the origin without rotation, children carry only translations, normals are written (Normals: Import).
Blender's exporter with axis_forward -Z, axis_up Y and Apply Transform (bake_space_transform) writes the same: a Blender
point (x, y, z) of the prefab frame becomes (x, z, -y) in the file, and Unity reads it as (-x, z, -y) - the frame every
contract of these batches gives for Unity.

What goes in: the root and its mesh children. What stays out: COL_* (box colliders of the hut, KPP and yard contracts:
the location builder puts MeshColliders on the meshes, as for every model of the map), Glow_* (halo cards: the builder
makes the halos from prefabGlows) and empties (LIGHT_* sockets: the builder makes the lights from prefabLights).
Materials that the game knows by name get Update 3's names (MAT_REMAP).

python3 -I u4_export.py -- <out_dir> [batch ...]      batches: hut kpp yard main garage road
"""
import bpy, sys, os, json
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PKG = os.path.join(HERE, 'out')

BATCHES = {
    'hut': ('forest_hut/hut.blend', ['TowerHut', 'Hochsitz', 'Sign_Forsthuette']),
    'kpp': ('forest_kpp/kpp.blend', ['Checkpoint', 'Barrier', 'Gate']),
    'yard': ('forest_yard/yard.blend', ['FuelTanks', 'Trafo']),
    'main': ('forest_main/main.blend', ['BaseMain', 'BaseMain_Opening']),
    'garage': ('forest_garage/garage.blend', ['Garage']),
    'road': ('forest_road/road.blend', ['Sign_Observatory', 'Sign_Viewpoint', 'Sign_Lookout', 'Sign_Pump', 'Sign_Radar',
                                        'Sign_Relay', 'Sign_Weather', 'Dist_11', 'Dist_09', 'Dist_07', 'Dist_23', 'Dist_03',
                                        'EuroPost', 'ZoneGate', 'Bridge30', 'OverlookDeck', 'FallenTree', 'LogCut']),
}

# the game and the location core find these by name (flicker, power grid, X01): Update 3's names, the definitions of
# M_Lantern / M_LanternOff / M_Lamp_FluorFlicker are redone in Forest_Materials.json with these lenses' textures
MAT_REMAP = {
    'M_Hut_Lamp_Lantern': 'M_Lantern',            # flicker (Light_lantern), X01 -> M_LanternOff
    'M_Hut_Lamp_Lantern_Off': 'M_LanternOff',
    'M_Hut_Lamp_Oillamp': 'M_Hut_LampOil',        # off at the start, nothing lights it yet
    'M_Hut_Glass': 'M_GlassDirty',
    'M_Kpp_Lamp_Fluor': 'M_Lamp_FluorFlicker',    # flicker (Light_booth)
    'M_Kpp_Lamp_Bulk': 'M_Lamp_BulbOff',          # power grid -> M_Lamp_Bulb
    'M_Kpp_Lamp_Crt': 'M_ScreenOff',              # power grid -> M_ScreenOn
    'M_Kpp_Glass': 'M_GlassClear',
}
SKIP_PREFIX = ('COL_', 'Glow_', 'LIGHT_')


def subtree(root):
    keep, skipped = [root], []
    for o in root.children_recursive:
        if o.type != 'MESH' or o.name.startswith(SKIP_PREFIX):
            skipped.append(o)
        else:
            keep.append(o)
    ks = set(keep)
    for o in keep[1:]:
        p = o.parent
        while p is not None and p != root:
            assert p in ks, f'{o.name}: parent {p.name} is not exported'
            p = p.parent
    return keep, skipped


def clean_parenting(root, objs):
    """matrix_parent_inverse -> identity, keeping every world matrix: the local transform is then the plain transform
    relative to the parent, and the exporter's Apply Transform writes clean child transforms (with a parent inverse
    left in place it writes compensating rotations and 0.01 scales on nested children)."""
    depth = lambda o: 0 if o == root else 1 + depth(o.parent)
    for o in sorted(objs, key=depth):
        if o == root:
            continue
        mw = o.matrix_world.copy()
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = o.parent.matrix_world.inverted() @ mw
    bpy.context.view_layer.update()


def join_nested(root, keep, log):
    """Every direct child of the root takes its descendants into its own mesh (glass, sign plates, lenses become extra
    materials of the door, gate or lamp they belong to), as in Update 3's models and the main building's and garage's
    batches. The exporter's Apply Transform writes wrong local frames for grandchildren; one level is exact. The pivot
    stays the direct child's origin."""
    keep_set = set(keep)
    out = [root]
    for d in [o for o in root.children if o in keep_set]:
        desc = [o for o in d.children_recursive if o in keep_set]
        if desc:
            bpy.ops.object.select_all(action='DESELECT')
            for o in [d] + desc:
                o.hide_set(False)
                o.hide_viewport = False
                o.select_set(True)
            bpy.context.view_layer.objects.active = d
            names = [o.name for o in desc]
            bpy.ops.object.join()
            log.append(f'{d.name} <- {", ".join(names)}')
        out.append(d)
    return out


def remap(objs, log):
    for o in objs:
        for slot in o.material_slots:
            m = slot.material
            if m is None:
                raise RuntimeError(f'{o.name}: empty material slot')
            t = MAT_REMAP.get(m.name)
            if t:
                tm = bpy.data.materials.get(t) or bpy.data.materials.new(t)
                assert tm.name == t, tm.name
                slot.material = tm
                log.append(f'{o.name}: {m.name} -> {t}')


def export(batch, out_dir):
    path, roots = BATCHES[batch]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT_PKG, path))
    vl = bpy.context.view_layer
    for c in bpy.data.collections:
        c.hide_viewport = False
    for lc in vl.layer_collection.children:
        lc.exclude = False
        lc.hide_viewport = False
    report = {}
    for rn in roots:
        root = bpy.data.objects[rn]
        keep, skipped = subtree(root)
        skipped_names = [o.name for o in skipped]
        log = []
        remap(keep, log)
        saved = root.matrix_world.copy()
        root.matrix_world = Matrix.Identity(4)
        bpy.context.view_layer.update()
        clean_parenting(root, keep)
        joined = []
        keep = join_nested(root, keep, joined)
        bpy.ops.object.select_all(action='DESELECT')
        for o in keep:
            o.hide_set(False)
            o.hide_viewport = False
            o.select_set(True)
        vl.objects.active = root
        vl.update()
        fp = os.path.join(out_dir, rn + '.fbx')
        bpy.ops.export_scene.fbx(filepath=fp, use_selection=True, use_visible=False, object_types={'MESH'},
                                 global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                                 use_mesh_modifiers=True, mesh_smooth_type='FACE', use_subsurf=False,
                                 use_mesh_edges=False, use_tspace=False, use_triangles=False, use_custom_props=False,
                                 colors_type='NONE', add_leaf_bones=False, bake_anim=False,
                                 path_mode='STRIP', embed_textures=False, batch_mode='OFF')
        aabb = {}
        for o in keep:
            vs = [o.matrix_world @ v.co for v in o.data.vertices]
            if vs:
                aabb[o.name] = [[round(min(v[i] for v in vs), 4) for i in range(3)],
                                [round(max(v[i] for v in vs), 4) for i in range(3)]]
        pivots = {o.name: [round(c, 4) for c in o.matrix_world.translation] for o in keep}
        root.matrix_world = saved
        mats = sorted({s.material.name for o in keep for s in o.material_slots})
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in keep)
        report[rn] = {'file': os.path.basename(fp), 'objects': [o.name for o in keep], 'skipped': skipped_names,
                      'joined': joined, 'materials': mats, 'tris': tris, 'remap': log, 'bytes': os.path.getsize(fp),
                      'aabb': aabb, 'pivots': pivots}
        print(f'[u4] {batch}/{rn}: {len(keep)} objects ({len(skipped)} left out), {tris} tris, {len(mats)} materials',
              flush=True)
    return report


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_dir = a[0]
    os.makedirs(out_dir, exist_ok=True)
    rep = {}
    for b in (a[1:] or list(BATCHES)):
        rep.update(export(b, out_dir))
    jp = os.path.join(out_dir, 'u4_export_report.json')
    old = json.load(open(jp)) if os.path.exists(jp) else {}
    old.update(rep)
    json.dump(old, open(jp, 'w'), indent=1, ensure_ascii=False)
