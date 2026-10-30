"""Unity package forest_airfield_v3 from the airfield concept (data/af_after.blend, built by concept.py on the World Sync
map export of 28.10 21:41). Writes pkg/forest_airfield_v3/:
  unity/ground_delta.f32 + ground_delta.json + base_ground.r16     the ground for WorldGroundImport (export_ground.py format)
  unity/ForestAirfield.json                                        the airfield's data with the concept's changes
  unity/Assets/Levels/Forest/Airfield/Winter/
     Forest_AirfieldSnow.fbx     windrows, apron and pad banks, drifts at the facade, the threshold lights' caps, the
                                 pale stripes at the ends (world space, planar UVs over 2 m like the ground's snow layer)
     AF_FuelDrum.fbx             the 200 l drum (FuelBarrel_Net's size, origin at its foot)
     T_AF_Runway_Winter.png      T_AF_Runway_BaseColor with the thin snow of the concept baked in (module space)
     AF_Trees.bytes              tree mask, 1 m: R remove, G clearing (big trees there may become stumps)
     AF_Paint.bytes              paint, on the ground grid: R packed snow (TL_TrailTrack), G ruts (TL_RoadRuts), B weight
     ForestAirfieldWinter.json   the step's data (materials, objects, masks' grids, the trees to plant)
python3.11 -I pkg_src/export_pkg.py"""
import bpy, bmesh, json, math, os, sys, shutil
import numpy as np
from mathutils import Vector, Matrix

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, D)
import af_scene as S
import ground_after as GA
import concept as C

OUT = os.path.join(D, 'pkg', 'forest_airfield_v3')
UN = os.path.join(OUT, 'unity')
WIN_REL = 'Assets/Levels/Forest/Airfield/Winter'
WIN = os.path.join(UN, *WIN_REL.split('/'))
PKG = 'F:/ClaudeGames/snow/source/assets/forest_airfield_v3/unity/'
GROUND_TEX = S.GROUND_TEX
RUNWAY_ATLAS = '/mnt/user-data/uploads/snow/Snow/Assets/Locations/Forest/Airfield/Textures/T_AF_Runway_BaseColor.png'
AF_JSON = '/mnt/user-data/uploads/snow/Snow/Assets/Levels/Forest/Airfield/ForestAirfield.json'
R = None


def ss(a, b, x):
    return GA.smoothstep(a, b, x)


# ------------------------------------------------------------------ ground
def ground_delta():
    m = json.load(open(S.MAP + 'map.json', encoding='utf-8'))['ground']
    g = R['g']
    d = R['delta'].astype(np.float32)
    d[np.abs(d) < 0.005] = 0.0
    full = np.zeros((m['nz'], m['nx']), np.float32)
    full[g['j0']:g['j0'] + d.shape[0], g['i0']:g['i0'] + d.shape[1]] = d
    full.tofile(os.path.join(UN, 'ground_delta.f32'))
    zz, xx = np.nonzero(np.abs(full) >= 0.005)
    info = {'nx': m['nx'], 'nz': m['nz'], 'x0': m['x0'], 'z0': m['z0'], 'step': m['step'], 'file': 'ground_delta.f32',
            'blend': 'forest_airfield_v3 src/ground_after.py (map export 2026-10-28 21:41)', 'changed': int(len(zz)),
            'base': PKG + 'base_ground.r16', 'hmin': m['hmin'], 'hmax': m['hmax'],
            'raised_max': float(full.max()), 'lowered_max': float(-full.min()),
            'box': [float(m['x0'] + xx.min() * m['step']), float(m['z0'] + zz.min() * m['step']),
                    float(m['x0'] + xx.max() * m['step']), float(m['z0'] + zz.max() * m['step'])]}
    json.dump(info, open(os.path.join(UN, 'ground_delta.json'), 'w'), indent=1)
    shutil.copy(S.MAP + 'ground.r16', os.path.join(UN, 'base_ground.r16'))
    print('[pkg] ground delta: %d samples, +%.2f / -%.2f m, box %s' % (info['changed'], info['raised_max'], info['lowered_max'],
                                                                       [round(b, 1) for b in info['box']]), flush=True)
    return info


# ------------------------------------------------------------------ trees
TREE_BOX = (700.0, -1180.0, 1200.0, 300.0)


def tree_remove(U, V, Uh, Vh, dl):
    """the concept's tree rules (concept.edit_trees) on any grid: remove = the corridor to the edge, the clearings, deep
    new earth, the hangar's front (the hill behind the facade keeps its trees); clearing = where grown trees may stay as
    stumps"""
    edge = np.where(U < 0, C.EDGE_W(V), C.EDGE_E(V))
    corridor = (V >= GA.END_S - 12) & (V <= GA.END_N + 12) & (np.abs(U) < edge)
    ds, dn = GA.END_S - V, V - GA.END_N
    fun_s = (V < GA.END_S) & (ds < 205.0) & (np.abs(U) < 52.0 + 0.2 * ds + 6.0 * C.noise1(V, 31))
    fun_n = (V > GA.END_N) & (dn < 165.0) & (np.abs(U) < 52.0 + 0.2 * dn + 6.0 * C.noise1(V, 37))
    funnel = fun_s | fun_n
    hill = (np.abs(Uh) < 32) & (Vh > -34) & (Vh < 8)
    remove = np.where(hill, Vh > -4.0, corridor | (np.abs(dl) > 4.0) | funnel)
    return remove, funnel & ~hill


def tree_mask():
    """tree_remove on a 1 m grid: R remove, G clearing"""
    x0, z0, x1, z1 = TREE_BOX
    nx, nz = int(x1 - x0), int(z1 - z0)
    X, Z = np.meshgrid(x0 + 0.5 + np.arange(nx), z0 + 0.5 + np.arange(nz))
    U, V = GA.to_uv(X, Z)
    Uh, Vh = GA.hangar_frame(X, Z)
    dl = GA.sample(R['delta'], R['g'], X.ravel(), Z.ravel()).reshape(X.shape)
    remove, clearing = tree_remove(U, V, Uh, Vh, dl)
    rgb = np.zeros((nz, nx, 3), np.uint8)
    rgb[..., 0] = remove * 255
    rgb[..., 1] = clearing * 255
    rgb.tofile(os.path.join(WIN, 'AF_Trees.bytes'))
    print('[pkg] tree mask %d x %d: remove %d m2, clearings %d m2' % (nx, nz, int(remove.sum()), int(clearing.sum())), flush=True)
    return {'file': 'AF_Trees.bytes', 'x0': x0, 'z0': z0, 'nx': nx, 'nz': nz, 'step': 1.0}


ROAD_KEEP = 6.0          # m from a road's axis: nothing new stands there (ForestWoodsStep's RoadKeep)


def road_axes():
    roads = json.load(open(os.path.join(D, 'data', 'ForestRoads.json'), encoding='utf-8'))['roads']
    segs = []
    for rd in roads:
        P = np.asarray(rd['points'], float).reshape(-1, 3)
        for i in range(len(P) - 1):
            segs.append((P[i, 0], P[i, 1], P[i + 1, 0], P[i + 1, 1]))
    return np.array(segs)


def road_dist(x, z, segs):
    x, z = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(z, float))
    best = np.full(len(x), 1e9)
    for ax, az, bx, bz in segs:
        abx, abz = bx - ax, bz - az
        t = np.clip(((x - ax) * abx + (z - az) * abz) / max(abx * abx + abz * abz, 1e-9), 0, 1)
        best = np.minimum(best, np.hypot(x - ax - abx * t, z - az - abz * t))
    return best


def trees_added():
    rows = json.load(open(os.path.join(D, 'data', 'trees_added.json')))
    d = road_dist([r[1] for r in rows], [r[2] for r in rows], road_axes())
    out = [{'proto': r[0], 'x': r[1], 'z': r[2], 'rot': r[3], 'w': r[4], 'h': r[5]} for r, dd in zip(rows, d) if dd >= ROAD_KEEP]
    print('[pkg] trees to plant: %d (%d of the concept within %.0f m of a road left out)' % (len(out), len(rows) - len(out), ROAD_KEEP), flush=True)
    return out


# ------------------------------------------------------------------ paint
def plough_masks(U, V, Uh, Vh):
    """the concept's ground masks (concept.ground_after): the plough's packed bands (shoulders, end areas, apron, pad) and
    the tyre tracks; the concept's D1 band is left out (the road model D1 runs north along the strip's west side)"""
    au = np.abs(U)
    runway = (1 - ss(GA.PAVE_V1, GA.PAVE_V1 + 1.0, V)) * ss(GA.PAVE_V0 - 1.0, GA.PAVE_V0, V)
    shoulder = ss(8.0, 8.6, au) * (1 - ss(11.2, 12.0, au)) * runway
    ends_s = ss(GA.END_S + 4, GA.END_S + 10, V) * (1 - ss(GA.PAVE_V0, GA.PAVE_V0 + 1, V)) * (1 - ss(11.0, 13.0, au))
    ends_n = (1 - ss(GA.PAVE_V1 + 22, GA.PAVE_V1 + 28, V)) * ss(GA.PAVE_V1 - 1, GA.PAVE_V1, V) * (1 - ss(11.0, 13.0, au))
    w_ap = np.where(Vh < 6.0, GA.WALL[0] + np.clip(Vh, 0, None) * GA.WALL[1], 20.0)
    apron = (1 - ss(w_ap - 1.2, w_ap, np.abs(Uh))) * ss(-1.0, 0.0, Vh) * (1 - ss(36.0, 37.0, Vh))
    padm = (U < -8) * ss(-50.5, -48.5, U) * ss(GA.PAD['v0'] + 4, GA.PAD['v0'] + 8, V) * (1 - ss(GA.PAD['v1'] - 6, GA.PAD['v1'] - 2, V))
    plough = np.clip(np.maximum.reduce([shoulder, ends_s, ends_n, apron, padm]), 0, 1)
    trk = np.zeros_like(U)
    for c0 in (-3.4, -1.6, 1.6, 3.4):
        trk = np.maximum(trk, (1 - ss(0.25, 0.55, np.abs(U - c0))) * (ends_s + ends_n))
    for c0 in (-4.0, -2.2, 2.2, 4.0):
        trk = np.maximum(trk, (1 - ss(0.25, 0.55, np.abs(Uh - c0))) * apron * ss(1.0, 3.0, Vh))
    return plough, np.clip(trk * 0.85, 0, 1)


def paint():
    """five masks on the ground grid (a byte each, rows south to north): packed, ruts, strip (the exact snow of the strip,
    the apron and the pad), cleared (the dark floor of the trees that went back to snow), regraded (the rock paint of
    slopes the earthwork flattened back to snow)"""
    from scipy import ndimage
    U, V, Uh, Vh, XX, ZZ, g = R['U'], R['V'], R['Uh'], R['Vh'], R['XX'], R['ZZ'], R['g']
    plough, trk = plough_masks(U, V, Uh, Vh)
    strip = (1 - ss(46.0, 52.0, np.abs(U))) * ss(GA.END_S - 16, GA.END_S - 6, V) * (1 - ss(GA.END_N + 6, GA.END_N + 16, V))
    pad = (U < 0) * (1 - ss(54.0, 58.0, -U)) * ss(GA.PAD['v0'] - 8, GA.PAD['v0'] - 2, V) * (1 - ss(GA.PAD['v1'] + 2, GA.PAD['v1'] + 8, V))
    strip = np.maximum(strip, pad)
    remove, _ = tree_remove(U, V, Uh, Vh, R['delta'])
    cleared = np.clip(ndimage.gaussian_filter(remove.astype(np.float32), 1.5 / g['step']) * 1.6 - 0.3, 0, 1)
    regraded = ss(0.1, 0.4, np.abs(R['delta']))
    ch = np.stack([plough * strip, trk * strip, strip, cleared, regraded], -1)
    used = np.any(ch > 0.004, axis=-1)
    jj, ii = np.nonzero(used)
    j0, j1, i0, i1 = jj.min(), jj.max() + 1, ii.min(), ii.max() + 1
    out = np.clip(np.rint(ch[j0:j1, i0:i1] * 255), 0, 255).astype(np.uint8)
    out.tofile(os.path.join(WIN, 'AF_Paint.bytes'))
    nz, nx = out.shape[:2]
    info = {'file': 'AF_Paint.bytes', 'x0': float(XX[j0, i0]), 'z0': float(ZZ[j0, i0]), 'nx': int(nx), 'nz': int(nz), 'step': g['step'],
            'channels': ['packed', 'ruts', 'strip', 'cleared', 'regraded'],
            'floor': 'TL_ForestFloor', 'dark': 'TL_ForestFloorDark', 'rock': 'TL_Rock', 'packed': 'TL_TrailTrack', 'ruts': 'TL_RoadRuts',
            'packedShare': 0.45, 'rockFlat': 24.0, 'rockSteep': 28.0}
    print('[pkg] paint %d x %d at %.3f m from (%.1f, %.1f): strip %d, cleared %d, regraded %d cells' %
          (nx, nz, g['step'], info['x0'], info['z0'], int((out[..., 2] > 0).sum()), int((out[..., 3] > 0).sum()), int((out[..., 4] > 0).sum())), flush=True)
    return info


# ------------------------------------------------------------------ the runway's winter texture
RUNWAY_STOPS = [(0.00, 0.60), (0.12, 0.52), (0.19, 0.30), (0.27, 0.32), (0.34, 0.58), (0.46, 0.62), (0.53, 0.36), (0.62, 0.38),
                (0.70, 0.66), (0.82, 0.80), (0.90, 0.95), (1.0, 0.98)]
APRON_STOPS = [(0.0, 0.97), (1.0, 0.97)]       # the concept's ramp at |u| > 9 m: the apron's slabs nearly white


def bake_runway(name='T_AF_Runway_Winter', stops=RUNWAY_STOPS):
    """T_AF_Runway_BaseColor with the concept's thin snow (concept.runway_material) baked in module space: the modules all
    lie on the axis, so a module's x is the runway's u (two wheel tracks a side, more snow at the edges); the apron's
    variant: the same snow at the concept's apron level all over"""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
    atlas = bpy.data.images.load(RUNWAY_ATLAS, check_existing=False)
    atlas.colorspace_settings.name = 'sRGB'
    W, H = atlas.size
    tgt = bpy.data.images.new(name, W, H, alpha=False)
    buf = np.empty(W * H * 4, np.float32); atlas.pixels.foreach_get(buf)
    tgt.pixels.foreach_set(buf)
    snow = bpy.data.images.load(GROUND_TEX + 'T_GR_Floor_A.png', check_existing=False)
    for nm in ('RWY_Slab', 'RWY_SlabWorn'):
        src = next(o for o in bpy.data.objects if o.get('root') == nm and o.type == 'MESH')
        ob = bpy.data.objects.new('BAKE_' + nm, src.data.copy())
        sc.collection.objects.link(ob)
        mat = bpy.data.materials.new('BAKE_' + nm); mat.use_nodes = True
        N, L = mat.node_tree.nodes, mat.node_tree.links
        for n in list(N):
            N.remove(n)
        out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
        tc = N.new('ShaderNodeTexCoord')
        at = N.new('ShaderNodeTexImage'); at.image = atlas; at.interpolation = 'Closest'
        L.new(tc.outputs['UV'], at.inputs['Vector'])
        sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
        ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(sep.outputs['X'], ab.inputs[0])
        dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 10.0; L.new(ab.outputs['Value'], dv.inputs[0])
        ramp = N.new('ShaderNodeValToRGB'); el = ramp.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], (stops[0][1],) * 3 + (1,)
        el[1].position, el[1].color = stops[-1][0], (stops[-1][1],) * 3 + (1,)
        for p, val in stops[1:-1]:
            e = el.new(p); e.color = (val, val, val, 1)
        L.new(dv.outputs['Value'], ramp.inputs['Fac'])
        nz1 = N.new('ShaderNodeTexNoise'); nz1.inputs['Scale'].default_value = 0.11; nz1.inputs['Detail'].default_value = 4.0
        L.new(tc.outputs['Object'], nz1.inputs['Vector'])
        r1 = N.new('ShaderNodeMapRange'); r1.inputs['From Min'].default_value = 0.3; r1.inputs['From Max'].default_value = 0.7
        r1.inputs['To Min'].default_value = -0.22; r1.inputs['To Max'].default_value = 0.22; L.new(nz1.outputs['Fac'], r1.inputs['Value'])
        nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 1.6; nz2.inputs['Detail'].default_value = 2.0
        L.new(tc.outputs['Object'], nz2.inputs['Vector'])
        r2 = N.new('ShaderNodeMapRange'); r2.inputs['From Min'].default_value = 0.35; r2.inputs['From Max'].default_value = 0.65
        r2.inputs['To Min'].default_value = -0.12; r2.inputs['To Max'].default_value = 0.12; L.new(nz2.outputs['Fac'], r2.inputs['Value'])
        spc = N.new('ShaderNodeSeparateColor'); L.new(ramp.outputs['Color'], spc.inputs['Color'])
        a1 = N.new('ShaderNodeMath'); a1.operation = 'ADD'; L.new(spc.outputs['Red'], a1.inputs[0]); L.new(r1.outputs['Result'], a1.inputs[1])
        a2 = N.new('ShaderNodeMath'); a2.operation = 'ADD'; a2.use_clamp = True; L.new(a1.outputs['Value'], a2.inputs[0]); L.new(r2.outputs['Result'], a2.inputs[1])
        sn = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Normal'], sn.inputs['Vector'])
        up = N.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = 0.6; up.inputs['From Max'].default_value = 0.9
        L.new(sn.outputs['Z'], up.inputs['Value'])
        k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; L.new(a2.outputs['Value'], k.inputs[0]); L.new(up.outputs['Result'], k.inputs[1])
        cb = N.new('ShaderNodeCombineXYZ')
        for ax in ('X', 'Y'):
            m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = 0.5
            L.new(sep.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], cb.inputs[ax])
        st = N.new('ShaderNodeTexImage'); st.image = snow; st.interpolation = 'Closest'; L.new(cb.outputs['Vector'], st.inputs['Vector'])
        sb = N.new('ShaderNodeMix'); sb.data_type = 'RGBA'; sb.blend_type = 'MULTIPLY'; sb.inputs['Factor'].default_value = 1.0
        L.new(st.outputs['Color'], sb.inputs['A']); sb.inputs['B'].default_value = (1.08, 1.08, 1.11, 1)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(k.outputs['Value'], mx.inputs['Factor']); L.new(at.outputs['Color'], mx.inputs['A']); L.new(sb.outputs['Result'], mx.inputs['B'])
        L.new(mx.outputs['Result'], em.inputs['Color'])
        L.new(em.outputs['Emission'], out.inputs['Surface'])
        tn = N.new('ShaderNodeTexImage'); tn.image = tgt
        for n in N:
            n.select = False
        tn.select = True; N.active = tn
        ob.data.materials.clear(); ob.data.materials.append(mat)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type='EMIT', margin=4, use_clear=False, target='IMAGE_TEXTURES')
        bpy.data.objects.remove(ob)
    tgt.filepath_raw = os.path.join(WIN, name + '.png'); tgt.file_format = 'PNG'
    tgt.save()
    print('[pkg] %s %dx%d' % (name, W, H), flush=True)
    return name + '.png'


# ------------------------------------------------------------------ models
SNOW_PREFIX = ('Windrow_', 'ApronBank_', 'PadBank', 'HangarDrift_', 'LightCap_', 'LightDrift_', 'Stripe_')


def export_fbx(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', use_tspace=False, use_triangles=True, colors_type='NONE', add_leaf_bones=False,
                             bake_anim=False, path_mode='STRIP', embed_textures=False, use_mesh_modifiers=True)


def road_footprint_hits(x, z):
    """True where a point lies on a road model of ForestRoads.json (lane + shoulder + berm + 0.5 m)"""
    roads = json.load(open(os.path.join(D, 'data', 'ForestRoads.json'), encoding='utf-8'))['roads']
    hit = np.zeros(len(x), bool)
    for rd in roads:
        P = np.asarray(rd['points'], float).reshape(-1, 3)
        berm = np.maximum(np.asarray(rd['bermLeft'], float).reshape(-1, 2)[:, 1], np.asarray(rd['bermRight'], float).reshape(-1, 2)[:, 1])
        half = np.asarray(rd['halfs'], float) + float(rd.get('shoulder', 0.6)) + berm + 0.5
        for i in range(len(P) - 1):
            ax, az, bx, bz = P[i, 0], P[i, 1], P[i + 1, 0], P[i + 1, 1]
            if min(ax, bx) > x.max() + 10 or max(ax, bx) < x.min() - 10 or min(az, bz) > z.max() + 10 or max(az, bz) < z.min() - 10:
                continue
            abx, abz = bx - ax, bz - az
            t = np.clip(((x - ax) * abx + (z - az) * abz) / max(abx * abx + abz * abz, 1e-9), 0, 1)
            hit |= np.hypot(x - ax - abx * t, z - az - abz * t) < half[i]
    return hit


def snow_model():
    """the concept's snow meshes, two slots: M_AF_Snow, M_AF_SnowDirty (faces the plough pushed: the concept's 'dirt' over
    0.3); each vertex follows the ground's change by the road protection (ground_after.road_protect), banks lying on a road
    model are left out"""
    m_snow = bpy.data.materials.new('M_AF_Snow'); m_dirty = bpy.data.materials.new('M_AF_SnowDirty')
    objs, defs, skipped = [], [], []
    d_concept = GA.compute(big=True, protect_roads=False, facade_cap=False)['delta']      # the ground the concept's meshes sit on
    for o in sorted([o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(SNOW_PREFIX)], key=lambda o: o.name):
        name = o.name
        o.name = name + '__src'; o.data.name = name + '__src'      # the exported object and mesh keep the plain name
        me = o.data.copy(); me.name = name
        Wm = o.matrix_world.copy()
        co = np.array([Wm @ v.co for v in me.vertices])
        ux, uz = -co[:, 0], -co[:, 1]
        bank_kind = not name.startswith(('LightCap_', 'LightDrift_', 'Stripe_'))
        if bank_kind and road_footprint_hits(ux, uz).mean() > 0.3:
            skipped.append(name)
            bpy.data.meshes.remove(me)
            continue
        shift = GA.sample(R['delta'], R['g'], ux, uz) - GA.sample(d_concept, R['g'], ux, uz)
        co[:, 2] += shift
        me.vertices.foreach_set('co', co.astype(np.float32).ravel()); me.update()
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        me.materials.clear(); me.materials.append(m_snow)
        dirty = False
        if 'dirt' in me.attributes:
            dv = np.zeros(len(me.vertices), np.float32); me.attributes['dirt'].data.foreach_get('value', dv)
            idx = []
            for p in me.polygons:
                f = float(np.mean(dv[list(p.vertices)]))
                idx.append(1 if f > 0.3 else 0)
            if any(idx):
                me.materials.append(m_dirty); dirty = True
                me.polygons.foreach_set('material_index', np.array(idx, np.int32))
        # planar UVs in Unity x / z over 2 m (the ground's snow layer tiles the same way); the mesh is in world space now
        while len(me.uv_layers):
            me.uv_layers.remove(me.uv_layers[0])
        uvl = me.uv_layers.new(name='UVMap')
        li = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', li)
        uv = np.stack([-co[li, 0] / 2.0, -co[li, 1] / 2.0], 1).astype(np.float32)
        uvl.data.foreach_set('uv', uv.ravel())
        objs.append(ob)
        kind = 'cap' if name.startswith('LightCap_') else ('stripe' if name.startswith('Stripe_') else 'bank')
        defs.append({'name': name, 'materials': ['M_AF_Snow', 'M_AF_SnowDirty'] if dirty else ['M_AF_Snow'],
                     'collider': kind == 'bank' and not name.startswith('LightDrift_')})
    export_fbx(objs, os.path.join(WIN, 'Forest_AirfieldSnow.fbx'))
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print('[pkg] snow model: %d objects, %d triangles; left out (on a road): %s' % (len(objs), tris, skipped), flush=True)
    for o in objs:
        bpy.data.objects.remove(o)
    return defs


def drum_model():
    me = C.drum_mesh().copy(); me.name = 'AF_FuelDrum'
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.translate(bm, vec=(0, 0, 0.44), verts=bm.verts)          # origin at the foot
    bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(bpy.data.materials.new('M_FuelDrum'))
    ob = bpy.data.objects.new('AF_FuelDrum', me); bpy.context.scene.collection.objects.link(ob)
    export_fbx([ob], os.path.join(WIN, 'AF_FuelDrum.fbx'))
    bpy.data.objects.remove(ob)
    print('[pkg] drum model', flush=True)


# ------------------------------------------------------------------ ForestAirfield.json
def xz(u, v):
    x, z = GA.to_xz(u, v)
    return round(float(x), 2), round(float(z), 2)


def hxz(Uh, Vh):
    return xz(*C.hangar_uv(Uh, Vh))


def airfield_json():
    d = json.load(open(AF_JSON, encoding='utf-8'))
    items = d['items']
    P = 'Assets/Levels/'
    W = P + 'Forest/Airfield/Prefabs/'
    RY, HY = 173.08, -96.92
    out, moved = [], 0
    for it in items:
        name = it['prefab'].rsplit('/', 1)[-1].replace('.prefab', '')
        if name == 'Fuel_Depot':
            continue                                                     # the tank farm off the pad
        if name == 'Windsock':
            it['x'], it['z'] = xz(-57.5, -344.0); it['note'] = 'beside the south turning pad, clear of it (concept 29.10)'; moved += 1
        elif name == 'Flood_Mast':
            it['x'], it['z'] = hxz(25.5, 10.0); it['note'] = 'out of the hangar bank to the apron side (concept 29.10)'; moved += 1
        elif name == 'Electrical_Cabinet':
            it['x'], it['z'] = hxz(-24.0, 9.5); it['note'] = 'out of the hangar bank to the apron side (concept 29.10)'; moved += 1
        out.append(it)
    def add(prefab, u, v, yaw, mode='ground', note=''):
        x, z = xz(u, v)
        out.append({'prefab': prefab, 'x': x, 'z': z, 'yaw': round(yaw, 2), 'mode': mode, 'note': note})
    def addh(prefab, Uh, Vh, yaw, note=''):
        add(prefab, *C.hangar_uv(Uh, Vh), yaw, 'ground', note)
    # the modules lost with the numbers 17 / 35: plain slabs
    add(W + 'RWY_Slab.prefab', 0.0, 335.0, RY - 180.0, 'runway', 'plain slab where the number 35 was (concept 29.10)')
    add(W + 'RWY_Slab.prefab', 0.0, -335.0, RY, 'runway', 'plain slab where the number 17 was (concept 29.10)')
    # the south hut: fuel, generator, power, firewood, the fire barrel, the sign at the barrier
    for k, (u, v) in enumerate(((-28.6, -390.4), (-29.3, -390.4), (-28.95, -389.8), (-27.9, -389.9), (-29.8, -389.7), (-28.3, -389.3))):
        add(W + 'AF_FuelDrum.prefab', u, v, RY - 90 + 37 * k, note='fuel by the hut (answer 9)')
    add(W + 'AF_FuelDrum_Lying.prefab', -30.9, -391.2, RY - 90 + 17, note='fuel by the hut')
    add(W + 'AF_FuelDrum_Lying.prefab', -26.8, -391.4, RY - 90 + 69, note='fuel by the hut')
    add(W + 'AF_Generator.prefab', -27.6, -398.3, RY - 90, note='the lights\' generator by the hut (answer 11)')
    add(P + 'SkyIsland/_Level/Prefabs/Electrical_Cabinet.prefab', -27.2, -395.2, RY - 90, note='power cabinet at the hut (answer 11)')
    add(P + 'Forest/_Level/Prefabs/LogPile.prefab', -25.8, -399.0, RY, note='firewood at the hut')
    add(P + 'Forest/World/Props/Prefabs/FireBarrel.prefab', -15.6, -392.2, 0.0, note='the guard\'s fire barrel')
    add(P + 'Forest/_Level/Prefabs/Sign_NoEntry.prefab', 6.2, -389.5, RY + 90, note='at the south barrier, to the road')
    add(P + 'Forest/_Level/Prefabs/Sign_NoEntry.prefab', -21.4, 321.0, -85.7, note='at the D1 barrier, beside the road model\'s berm')
    # the hangar's apron
    C_ = 'Assets/Common/Vehicles/Plane/Prefabs/'
    for k, (nm, Uh, Vh, dy) in enumerate((('Cargo_Case1', -12.6, 3.0, 0), ('Cargo_Case2', -13.5, 3.3, 11), ('Cargo_Case3', -11.8, 3.9, -17),
                                          ('Cargo_Case4', -12.7, 4.3, 29))):
        addh(C_ + nm + '.prefab', Uh, Vh, HY + dy, 'the plane\'s cases by the gate')
    addh(P + 'Forest/_Level/Prefabs/Crates.prefab', 14.3, 3.4, HY, 'crates by the gate')
    addh(P + 'SkyIsland/_Level/Prefabs/Cable_Drum.prefab', -22.6, 12.0, HY + 69, 'by the power cabinet')
    addh(P + 'Forest/_Level/Prefabs/LightPole.prefab', -21.8, 25.0, HY, 'apron lamp')
    addh(P + 'Forest/_Level/Prefabs/LightPole.prefab', 21.8, 25.0, HY + 180, 'apron lamp')
    for k, (Uh, Vh) in enumerate(((-18.6, 13.0), (-18.0, 13.7), (-18.9, 13.9), (-18.3, 14.6))):
        addh(W + 'AF_FuelDrum.prefab', Uh, Vh, HY + 41 * k, 'the plane\'s fuel at the apron')
    d['items'] = out
    # the Terrain holes at the facade follow the new hill (ground_after: the earth at the facade's back 4 cm under its top,
    # the step down to the apron at V_h -0.9): the gate's holes only over that step, the side door's over its open passage
    holes = {'holes over the hall at the facade (the gate)': [-9.6, -1.8, 9.6, 0.4],
             'holes over the side door corridor': [9.0, -2.2, 11.6, -0.6]}
    for r in d['ground']:
        if r.get('name') in holes:
            r['rect'] = holes[r['name']]
    d['ground_note'] = d.get('ground_note', '') + (' 29.10 (forest_airfield_v3): the ground comes from the concept through '
                                                   'WorldGroundImport; the hole rectangles moved to the new hill.')
    d['layout_note'] = d.get('layout_note', '') + (' 29.10 (forest_airfield_v3, the Blender concept docs/gdd/locations/airfield/concept_v3): '
                                                   'slabs back at v +-335, Fuel_Depot gone, fuel drums / generator / cabinet / firewood / '
                                                   'fire barrel at the south hut, the hangar apron dressed, windsock, flood mast and cabinet moved; '
                                                   'snow, trees and paint by ForestAirfieldWinterStep.')
    path = os.path.join(UN, 'ForestAirfield.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print('[pkg] ForestAirfield.json: %d items (was %d), %d moved' % (len(out), len(items), moved), flush=True)


def main():
    global R
    os.makedirs(WIN, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(D, 'data', 'af_after.blend'))
    R = GA.compute(big=True)                         # the whole reach of the grading (the concept's crop stops at x 820 / 1110)
    C.R = R
    gd = ground_delta()
    tm = tree_mask()
    add = trees_added()
    pt = paint()
    rw = bake_runway()
    ap = bake_runway('T_AF_Apron_Winter', APRON_STOPS)
    snow = snow_model()
    drum_model()
    airfield_json()
    data = {
        'version': '3.0',
        'note': 'Forest airfield in winter, Blender concept 29.10.2026 (docs/gdd/locations/airfield/concept_v3, package '
                'source/assets/forest_airfield_v3): the runway slabs under thin ploughed snow, the snow banks, the trees and the '
                'paint; read by ForestAirfieldWinterStep. The ground comes once through WorldGroundImport (the apply script).',
        'model': WIN_REL + '/Forest_AirfieldSnow.fbx',
        'objects': snow,
        'materials': [
            {'name': 'M_AF_Snow', 'texture': 'Assets/Levels/Forest/_Level/Terrain/Ground/T_GR_Floor_A.png', 'color': [1.0, 1.0, 1.0]},
            {'name': 'M_AF_SnowDirty', 'texture': 'Assets/Levels/Forest/_Level/Terrain/Ground/T_GR_Track_A.png', 'color': [0.92, 0.9, 0.88]}],
        'runway': {'material': 'Assets/Levels/Forest/Airfield/Materials/M_AF_Runway.mat', 'texture': WIN_REL + '/' + rw,
                   'winter': WIN_REL + '/M_AF_RunwayWinter.mat', 'apronTexture': WIN_REL + '/' + ap,
                   'apronWinter': WIN_REL + '/M_AF_ApronWinter.mat', 'x': GA.RW['x'], 'z': GA.RW['z'], 'yaw': GA.RW['yaw'], 'apronFrom': 12.0},
        'trees': {'mask': tm, 'stumpProto': 'Stump', 'stumpShare': 0.35, 'stumpScale': [0.8, 1.3],
                  'bigKinds': ['Spruce', 'Fir', 'Birch', 'Dead'], 'bigHeight': 8.0, 'roadKeep': ROAD_KEEP,
                  'keep': ['OldFence', 'EuroPost', 'FenceChain'], 'add': add},
        'paint': pt,
    }
    with open(os.path.join(WIN, 'ForestAirfieldWinter.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('[pkg] data: %d snow objects, %d trees to plant' % (len(snow), len(add)), flush=True)


if __name__ == '__main__':
    main()
