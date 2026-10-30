"""forest_base_v1: the base yard concept (data/after_final.blend) out for Unity.
 - every new mesh of the concept in world space, modifiers applied, box-projected UVs per material (metres per UV unit as
   the texture's tile), materials renamed to the package's M_Base* and unused slots dropped -> Forest_BaseYard.fbx (project
   FBX settings: Blender (x, y, z) = Unity (-x, -z, y));
 - the yard snow (banks, end piles, drifts) resampled from the concept's 0.25 m layer to 0.5 m, cut in 12 pieces, clean
   and dirty snow by face, UVs = the terrain's own mapping (Unity x / 2, z / 2) so the snow meets the ground seamlessly;
 - the copies of project models (garages, cars, the gate boom with its beacon) and props (crates, cable drum) as placements;
 - the entry light, the chimney smoke, the Terrain strokes (paths, lanes, ruts) and the rects cleared of yard saplings.
python3.11 -I export_pkg.py <in.blend> <unity folder> <data json>"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import yard as Y

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
SRC, OUTDIR, DATA = argv[0], argv[1], argv[2]
bpy.ops.wm.open_mainfile(filepath=SRC)
import concept as C                                   # PATHS, LANE2, offset_poly (definitions only)
G = Y.Ground()
MAPJ = json.load(open('/mnt/user-data/uploads/snow/source/world_sync/forest/map/map.json', encoding='utf-8'))

# Blender concept material -> (Unity material, metres per UV unit; 0 = the terrain's world mapping)
MAT = {
    'C_Concrete': ('M_BaseConcrete', 2.0), 'C_ConcreteDark': ('M_BaseConcreteDark', 2.0), 'C_Curb': ('M_BaseCurb', 1.0),
    'C_Steel': ('M_BaseSteel', 2.0), 'C_SteelDark': ('M_BaseSteelDark', 2.0), 'C_Olive': ('M_BaseOlive', 1.5),
    'C_Rust': ('M_BaseRust', 1.5), 'C_ContRed': ('M_BaseContRed', 2.4), 'C_ContBlue': ('M_BaseContBlue', 2.4),
    'C_ContOlive': ('M_BaseContOlive', 2.4), 'C_CorrDark': ('M_BaseCorrDark', 2.4), 'C_Wood': ('M_BaseWood', 1.2),
    'C_White': ('M_BaseWhite', 1.0), 'C_Red': ('M_BaseRed', 1.0), 'C_Yellow': ('M_BaseYellow', 1.0), 'C_Black': ('M_BaseBlack', 1.0),
    'C_Orange': ('M_BaseOrange', 1.0), 'C_Glass': ('M_BaseGlass', 1.0), 'C_DrumBlue': ('M_BaseDrumBlue', 1.0),
    'C_DrumRed': ('M_BaseDrumRed', 1.0), 'C_DrumGreen': ('M_BaseDrumGreen', 1.0), 'C_Bag': ('M_BaseBag', 1.0),
    'C_Bin': ('M_BaseBin', 1.0), 'C_SignBlue': ('M_BaseSignBlue', 1.0), 'C_Letters': ('M_BaseLetters', 1.0),
    'C_Soot': ('M_BaseSoot', 1.0), 'C_PloughOrange': ('M_BasePloughOrange', 1.0), 'C_Ice': ('M_BaseIce', 1.0),
    'C_YellowBlack': ('M_BaseStripeYB', 0.4), 'C_RedWhiteBand': ('M_BaseBandRW', 2.0), 'C_Glow': ('M_BaseWindowGlow', 1.0),
    'C_Lamp': ('M_BaseLampGlow', 1.0), 'C_RedLight': ('M_BaseRedLight', 1.0), 'C_Snow': ('M_BaseSnow', 0.0),
    'C_SnowClean': ('M_BaseSnow', 2.0), 'C_SnowChunk': ('M_BaseSnowChunk', 1.0), 'C_Radome': ('M_BaseRadome', 2.0),
}
SKIP = ('Smoke', 'Path', 'Lane', 'Rut', 'GarRut', 'G_', 'SnowLayer')
NO_COLLIDER = ('Snow_', 'Bag', 'GasBottle', 'SnowPole', 'Shovel', 'HandPump', 'GenExhaust', 'PloughChunks', 'Rails', 'CableTray',
               'EntryLamp', 'WindowGlow', 'RoofKit', 'Dish', 'SignText', 'StationSign', 'Radome_crown', 'Radome_plinth_snow')
GROUND = ('SnowLayer', 'Curbs', 'PloughChunks')
KIT_MODELS = {   # concept kit copy -> the project model (no prefab: no scripts, no network ids, doors stay shut)
    'Garage': 'Assets/Locations/Forest/Models/Garage.fbx',
    'ShiftCar': 'Assets/Locations/Forest/ShiftCar/Models/ShiftCar.fbx',
    'StartCar': 'Assets/Locations/Forest/Cars/Models/StartCar.fbx',
    'WreckCar': 'Assets/Locations/Forest/Cars/Models/WreckCar.fbx',
    'Barrier': 'Assets/Locations/Forest/Models/Barrier.fbx',
    'Beacon_Barrier': 'Assets/Kit/Models/Kit_Beacon.fbx',
}
KIT_PREFABS = {'Crates': 'Assets/Locations/Forest/Prefabs/Crates.prefab', 'Cable_Drum': 'Assets/SkyIsland/Prefabs/Cable_Drum.prefab'}


def U(v):
    """Blender point -> Unity [x, y, z]"""
    return [round(-v[0], 4), round(v[2], 4), round(-v[1], 4)]


def part_materials(model_fbx):
    """mesh name -> material names, from the map export (the meshes of that FBX as the scene renders them)"""
    out = {}
    for d in MAPJ['meshes']['list']:
        if d.get('fbx') == model_fbx and d['name'] not in out:
            out[d['name']] = d.get('materials', [])
    return out


def world_mesh(ob, dg):
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)
    me.transform(ob.matrix_world)
    if ob.matrix_world.determinant() < 0:
        me.flip_normals()
    return me


def remap(me, names):
    """materials -> package names, unused slots dropped; returns the Unity names and tiles in slot order"""
    n = len(me.materials)
    idx = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', idx)
    idx = np.clip(idx, 0, max(n - 1, 0))                 # faces copied from other meshes keep their old index: Blender clamps it
    order, new_of = [], {}
    for i in range(n):
        m = me.materials[i]
        uname, tile = MAT.get(m.name if m else '', ('M_BaseConcrete', 2.0))
        if not np.any(idx == i):
            continue
        key = uname
        if key not in new_of:
            new_of[key] = len(order); order.append((uname, tile))
        new_of[i] = new_of[key]
    lut = np.array([new_of.get(i, 0) for i in range(max(n, 1))], np.int32)
    me.materials.clear()
    for uname, _ in order:
        me.materials.append(bpy.data.materials.get(uname) or bpy.data.materials.new(uname))
    if n:
        me.polygons.foreach_set('material_index', lut[idx])
    return order


def box_uv(me, tiles):
    """box projection in world space, metres per UV unit per slot; tile 0: Unity (x / 2, z / 2) as the Terrain layers"""
    uvl = me.uv_layers.new(name='UVMap')
    nl = len(me.loops)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    vi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', vi)
    nrm = np.zeros(len(me.polygons) * 3, np.float32); me.polygons.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    mi = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', mi)
    ls = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
    lt = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', lt)
    poly_of_loop = np.repeat(np.arange(len(me.polygons)), lt)
    P = co[vi]; N = nrm[poly_of_loop]; T = np.array([t for _, t in tiles] or [1.0], np.float32)[mi[poly_of_loop]]
    ax = np.argmax(np.abs(N), 1)
    u = np.where(ax == 2, P[:, 0], np.where(ax == 0, P[:, 1] * np.sign(N[:, 0] + 1e-9), -P[:, 0] * np.sign(N[:, 1] + 1e-9)))
    v = np.where(ax == 2, P[:, 1], P[:, 2])
    t = np.where(T > 0, T, 1.0)
    uu, vv = u / t, v / t
    world = T <= 0
    uu = np.where(world, -P[:, 0] / 2.0, uu); vv = np.where(world, -P[:, 1] / 2.0, vv)
    uvl.data.foreach_set('uv', np.stack([uu, vv], 1).astype(np.float32).ravel())


# ------------------------------------------------------------------ the yard snow at 0.5 m
def snow_pieces(col, dg):
    src = bpy.data.objects['SnowLayer']
    bvh = BVHTree.FromObject(src, dg)
    me = src.data
    dirt = np.zeros(len(me.vertices), np.float32); me.attributes['dirt'].data.foreach_get('value', dirt)
    kd = KDTree(len(me.vertices))
    for i, v in enumerate(me.vertices):
        kd.insert(v.co, i)
    kd.balance()
    st = 0.5
    uu = np.arange(-71.5, 71.5 + 1e-6, st); vv = np.arange(-50.5, 47.5 + 1e-6, st)
    Uu, Vv = np.meshgrid(uu, vv)
    x, y = Y.uv_to_blender_xy(Uu, Vv)
    gh = G.at(Uu, Vv)
    h = np.zeros(Uu.shape); dd = np.zeros(Uu.shape)
    for j in range(Uu.shape[0]):
        for i in range(Uu.shape[1]):
            hit = bvh.ray_cast(Vector((x[j, i], y[j, i], 200.0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                h[j, i] = max(0.0, hit[0].z + 0.015 - gh[j, i])
                dd[j, i] = dirt[kd.find(hit[0])[1]]
    on = h > 0.03
    cell = on[:-1, :-1] | on[1:, :-1] | on[:-1, 1:] | on[1:, 1:]
    out = []
    edges_u = np.linspace(0, len(uu) - 1, 5).astype(int); edges_v = np.linspace(0, len(vv) - 1, 4).astype(int)
    k = 0
    for a in range(4):
        for b in range(3):
            i0, i1, j0, j1 = edges_u[a], edges_u[a + 1], edges_v[b], edges_v[b + 1]
            c = np.zeros_like(cell); c[j0:j1, i0:i1] = cell[j0:j1, i0:i1]
            if not c.any():
                continue
            need = np.zeros_like(on)
            need[:-1, :-1] |= c; need[1:, :-1] |= c; need[:-1, 1:] |= c; need[1:, 1:] |= c
            idx = np.full(on.shape, -1, np.int64); idx[need] = np.arange(need.sum())
            co = np.stack([x[need], y[need], gh[need] + h[need] - 0.015], 1).astype(np.float32)
            jj, ii = np.nonzero(c)
            quads = np.stack([idx[jj, ii], idx[jj, ii + 1], idx[jj + 1, ii + 1], idx[jj + 1, ii]], 1)
            fd = (dd[jj, ii] + dd[jj, ii + 1] + dd[jj + 1, ii + 1] + dd[jj + 1, ii]) / 4
            m = bpy.data.meshes.new('BY_SnowLayer_%02d' % k)
            m.vertices.add(len(co)); m.vertices.foreach_set('co', co.ravel())
            m.loops.add(quads.size); m.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
            m.polygons.add(len(quads)); m.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
            m.update(calc_edges=True)
            m.materials.append(bpy.data.materials.get('M_BaseSnow') or bpy.data.materials.new('M_BaseSnow'))
            m.materials.append(bpy.data.materials.get('M_BaseSnowDark') or bpy.data.materials.new('M_BaseSnowDark'))
            m.polygons.foreach_set('material_index', (fd > 0.35).astype(np.int32))
            m.shade_smooth()
            box_uv(m, [('M_BaseSnow', 0.0), ('M_BaseSnowDark', 0.0)])
            o = bpy.data.objects.new('BY_SnowLayer_%02d' % k, m); col.objects.link(o)
            out.append((o, [('M_BaseSnow', 0.0), ('M_BaseSnowDark', 0.0)]))
            k += 1
    print('[pkg] snow: %d pieces, %d quads, max %.2f m' % (k, int(cell.sum()), float(h.max())), flush=True)
    return out


def lighten():
    """game weight: the kerb without its bevel; snow slabs dissolved where flat (4 deg), as they are flat on flat roofs"""
    con = bpy.data.collections['Concept']
    for ob in con.objects:
        if ob.type != 'MESH':
            continue
        if ob.name == 'Curbs' and 'b' in ob.modifiers:
            ob.modifiers.remove(ob.modifiers['b'])
        if ob.name.endswith('_snow') or ob.name.startswith('Snow_'):
            md = ob.modifiers.new('lite', 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = math.radians(4.0)
    bpy.context.view_layer.update()


def main():
    lighten()
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    con = bpy.data.collections['Concept']
    exp = bpy.data.collections.new('Export'); bpy.context.scene.collection.children.link(exp)
    objects, models, prefabs = [], [], []
    names = {}
    for ob in list(con.objects):
        base = ob.name
        if ob.type != 'MESH' or base.startswith(SKIP) or '_snow_snow' in base:
            continue
        if base.startswith('K_') and not base.endswith('_snow'):
            continue
        me = world_mesh(ob, dg)
        if not me.polygons:
            continue
        order = remap(me, None)
        box_uv(me, order)
        stem = base.replace('.', '_')
        k = names.get(stem, 0); names[stem] = k + 1
        nm = 'BY_%s' % stem if k == 0 else 'BY_%s_%d' % (stem, k)
        o = bpy.data.objects.new(nm, me); exp.objects.link(o)
        objects.append((o, order, base))
    for o, order in snow_pieces(exp, dg):
        objects.append((o, order, 'SnowLayer'))
    # project models and props placed as in the concept
    for ob in con.objects:
        if ob.type != 'MESH':
            continue
        base = ob.name.split('.')[0]
        if base.startswith('K_') and not ob.name.endswith('_snow'):
            kind = base[2:]
            loc, rz = ob.location, ob.rotation_euler.z
            if kind in KIT_PREFABS:
                prefabs.append({'prefab': KIT_PREFABS[kind], 'pos': U(loc), 'yaw': round(-math.degrees(rz), 3)})
            elif kind in KIT_MODELS:
                models.append({'model': KIT_MODELS[kind], 'pos': U(loc), 'yaw': round(-math.degrees(rz), 3),
                               'materials': part_materials(KIT_MODELS[kind]), 'collider': 'mesh'})
        elif base in ('G_Barrier', 'G_Beacon_Barrier'):
            kind = base[2:]
            mw = ob.matrix_world
            rz = mw.to_euler().z
            models.append({'model': KIT_MODELS[kind], 'pos': U(mw.translation), 'yaw': round(-math.degrees(rz), 3),
                           'materials': part_materials(KIT_MODELS[kind]), 'collider': 'mesh' if kind == 'Barrier' else 'none'})
    # export
    bpy.ops.object.select_all(action='DESELECT')
    for o, _, _ in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0][0]
    os.makedirs(OUTDIR, exist_ok=True)
    fbx = os.path.join(OUTDIR, 'Forest_BaseYard.fbx')
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', use_tspace=False, use_triangles=True, colors_type='NONE', add_leaf_bones=False,
                             bake_anim=False, path_mode='STRIP', embed_textures=False, use_mesh_modifiers=True)
    info = []
    tris = 0
    for o, order, base in objects:
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        tris += t
        coll = 'none' if base.startswith(NO_COLLIDER) or base.endswith(('_snow', '_cornice')) or 'cornice' in base else 'mesh'
        info.append({'name': o.name, 'materials': [u for u, _ in order], 'collider': coll,
                     'ground': base.startswith(GROUND), 'tris': t})
    # the entry light, the smoke
    lt = bpy.data.objects['EntryLight']
    chim = bpy.data.objects['Chimney']
    top = chim.matrix_world @ Vector((0.0, 0.0, 22.6))
    wind = Y.uv_to_unity(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    wx, wz = float(wind[0][1] - wind[0][0]), float(wind[1][1] - wind[1][0]); n = math.hypot(wx, wz)
    lights = [{'name': 'BaseEntryLight', 'pos': U(lt.matrix_world.translation), 'color': [1.0, 0.75, 0.45], 'intensity': 1.6, 'range': 7.0}]
    smoke = {'pos': U(top), 'wind': [round(wx / n, 4), 0.0, round(wz / n, 4)]}
    # Terrain: strokes and cleared rects, Unity x / z
    def poly_u(pts):
        x, z = Y.uv_to_unity(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
        return [round(float(a), 3) for xz in zip(x, z) for a in xz]
    lane_g = [(21.0, -15.0), (12.0, -24.0), (5.0, -32.5), (-3.0, -35.5), (-14.0, -35.5)]
    strokes = [{'n': 'path %d' % k, 'layer': 'TL_TrailTrack', 'w': round(w + 0.4, 2), 'soft': 0.5, 'p': poly_u(p)} for k, (w, p) in enumerate(C.PATHS)]
    for nm, ln in (('garage lane', lane_g), ('storage lane', C.LANE2)):
        strokes.append({'n': nm, 'layer': 'TL_TrailSoil', 'w': 4.0, 'soft': 0.8, 'p': poly_u(ln)})
        for off in (-0.8, 0.8):
            strokes.append({'n': nm + ' rut', 'layer': 'TL_TrailTrack', 'w': 0.6, 'soft': 0.25, 'p': poly_u(C.offset_poly(ln, off))})
    for gu in (4.0, -10.0):
        for off in (-0.8, 0.8):
            strokes.append({'n': 'garage door rut', 'layer': 'TL_TrailTrack', 'w': 0.6, 'soft': 0.25,
                            'p': poly_u([(gu + 1.3 + off, -35.5), (gu + 1.3 + off, -37.8)])})
    clear_uv = [(-23.5, -30.6, -8.8, -14.0), (-3.0, -49.5, 11.0, -33.0), (-17.0, -49.5, -3.0, -33.0), (-67.5, -20.5, -53.5, 2.5),
                (0.0, 29.0, 32.0, 46.7), (60.0, -42.0, 70.7, -20.0)]
    clear = [{'p': poly_u([(a, b), (c, b), (c, d), (a, d)])} for (a, b, c, d) in clear_uv]
    clear += [{'w': 6.0, 'p': poly_u(lane_g)}, {'w': 6.0, 'p': poly_u(C.LANE2)}]
    json.dump({'objects': info, 'models': models, 'prefabs': prefabs, 'lights': lights, 'smoke': smoke, 'strokes': strokes,
               'clear': clear, 'tris': tris}, open(DATA, 'w'), indent=1)
    print('[pkg] FBX %s: %d objects, %d tris; %d models, %d prefabs, %d strokes' % (fbx, len(objects), tris, len(models), len(prefabs), len(strokes)), flush=True)


main()
