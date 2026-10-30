"""Preview of the integrated NW gorge (what Unity gets): new ground with the gorge paint, the rock model, the creek water
and its ice, Bridge30, the Terrain trees (out of the gorge, refill on new ground roughly), fog. Project convention:
Blender (x, y, z) = Unity (-x, -z, y).

python3.11 -I preview.py <out.blend> <views,...|-> <spp> <w> <h>"""
import bpy, json, math, os, sys, zlib
import numpy as np
from PIL import Image
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gorge'))
import full_params as FP
import scene_common as S                       # materials, fog, render setup (frame-independent parts)

D = os.path.dirname(os.path.abspath(__file__))
UP = S.UP
AX0, AX1, AZ0, AZ1 = -600.0, -130.0, 100.0, 600.0          # Unity area of the preview ground


def B(ux, uz, uy=0.0):
    return Vector((-ux, -uz, uy))


# ---------------------------------------------------------------- ground
def ground_area():
    H = np.load(os.path.join(D, 'data', 'H_new.npy')).astype(np.float64)
    i0, i1 = int((AX0 - FP.X0) / FP.ST), int((AX1 - FP.X0) / FP.ST)
    j0, j1 = int((AZ0 - FP.Z0) / FP.ST), min(FP.N - 1, int(round((AZ1 - FP.Z0) / FP.ST)))
    return H, i0, i1, j0, j1


def terrain_mesh(H, i0, i1, j0, j1, mat):
    sub = H[j0:j1 + 1, i0:i1 + 1]
    nz, nx = sub.shape
    ux = FP.X0 + np.arange(i0, i1 + 1) * FP.ST; uz = FP.Z0 + np.arange(j0, j1 + 1) * FP.ST
    X, Y = np.meshgrid(-ux, -uz)
    V = np.stack([X, Y, sub], -1).reshape(-1, 3).astype(np.float32)
    ii, jj = np.meshgrid(np.arange(nz - 1), np.arange(nx - 1), indexing='ij')
    a = (ii * nx + jj).ravel()
    Q = np.stack([a, a + 1, a + nx + 1, a + nx], -1)          # x and z both negated = a half turn: winding kept
    me = bpy.data.meshes.new('Ground')
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(Q.size); me.loops.foreach_set('vertex_index', Q.ravel().astype(np.int32))
    me.polygons.add(len(Q)); me.polygons.foreach_set('loop_start', np.arange(0, Q.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.shade_smooth()
    ob = bpy.data.objects.new('Ground', me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    up = sum(p.normal.z for p in me.polygons[:200]) / 200
    print('ground', sub.shape, 'normal z (mean of 200)', round(up, 3), flush=True)
    return ob


def splat_after(H):
    """tile 0_2 paint with what the gorge step and the import do: walls rock / ledges snow (mask 1), the creek bed
    rock + gravel (mask 3), new ground of the import (|change| >= 1 m) the forest floor mean"""
    sp = np.load(os.path.join(D, 'data', 'tile_splat.npy')).astype(np.float64) / 255.0       # rows = z up, x 1024
    G = np.load(os.path.join(D, '..', 'gorge', 'data', 'ground_map.npy')).astype(np.float64)
    M = json.load(open(os.path.join(D, 'data', 'mask.json')))
    mask = np.fromfile(os.path.join(D, 'unity', 'gorge_mask.u8'), np.uint8).reshape(M['nz'], M['nx'])
    n = 1024
    ax = -600.0 + (np.arange(n) + 0.5) * 600.0 / n
    az = 0.0 + (np.arange(n) + 0.5) * 600.0 / n
    AXg, AZg = np.meshgrid(ax, az)
    mi = np.round((AXg - M['x0']) / M['step']).astype(int) - M['i0']
    mj = np.round((AZg - M['z0']) / M['step']).astype(int) - M['j0']
    ok = (mi >= 0) & (mj >= 0) & (mi < M['nx']) & (mj < M['nz'])
    mk = np.zeros_like(mi, dtype=np.uint8)
    mk[ok] = mask[mj[ok], mi[ok]]
    gy, gx = np.gradient(H, FP.ST)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    fi = (AZg - FP.Z0) / FP.ST; fj = (AXg - FP.X0) / FP.ST
    from scipy.ndimage import map_coordinates
    sl = map_coordinates(slope, [fi, fj], order=1)
    dz = map_coordinates(np.abs(H - G), [fi, fj], order=1)
    out = sp.copy()
    refill = (dz >= 1.0) & (mk != 1) & (mk != 3)
    out[refill] = 0; out[refill, 0] = 0.35; out[refill, 1] = 0.65
    k = np.clip((sl - 42.0) / 10.0, 0, 1)
    m1 = mk == 1
    out[m1] = 0; out[m1, 4] = k[m1]; out[m1, 0] = 1 - k[m1]
    m3 = mk == 3
    r = (np.sin(AXg * 0.9) * np.cos(AZg * 0.7) * 0.5 + 0.5)
    out[m3] = 0; out[m3, 4] = r[m3]; out[m3, 2] = 1 - r[m3]
    for kk in range(2):
        im = (np.clip(out[::-1, :, 4 * kk:4 * kk + 4], 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(im, 'RGBA').save(os.path.join(D, 'data', f'prev_splat{kk}.png'))


def terrain_material():
    m = bpy.data.materials.new('G_TerrainPrev')
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.92
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    neg = {}
    for ax in ('X', 'Y'):
        n_ = N.new('ShaderNodeMath'); n_.operation = 'MULTIPLY'; n_.inputs[1].default_value = -1.0
        L.new(sep.outputs[ax], n_.inputs[0]); neg[ax] = n_          # Unity x, z
    tu = N.new('ShaderNodeCombineXYZ')
    for ax, src in (('X', neg['X']), ('Y', neg['Y'])):
        dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 2.0
        L.new(src.outputs['Value'], dv.inputs[0]); L.new(dv.outputs['Value'], tu.inputs[ax])
    su = N.new('ShaderNodeCombineXYZ')
    for ax, src, o_ in (('X', neg['X'], -600.0), ('Y', neg['Y'], 0.0)):
        sb = N.new('ShaderNodeMath'); sb.operation = 'SUBTRACT'; sb.inputs[1].default_value = o_
        dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 600.0
        L.new(src.outputs['Value'], sb.inputs[0]); L.new(sb.outputs['Value'], dv.inputs[0]); L.new(dv.outputs['Value'], su.inputs[ax])
    weights = []
    for k in range(2):
        t = N.new('ShaderNodeTexImage')
        t.image = S.img(os.path.join(D, 'data', f'prev_splat{k}.png'), noncolor=True, alpha='CHANNEL_PACKED')
        t.interpolation = 'Linear'; t.extension = 'EXTEND'
        L.new(su.outputs['Vector'], t.inputs['Vector'])
        sc_ = N.new('ShaderNodeSeparateColor'); L.new(t.outputs['Color'], sc_.inputs['Color'])
        weights += [sc_.outputs['Red'], sc_.outputs['Green'], sc_.outputs['Blue'], t.outputs['Alpha']]
    off = N.new('ShaderNodeCombineXYZ')
    L.new(neg['X'].outputs['Value'], off.inputs['X']); L.new(neg['Y'].outputs['Value'], off.inputs['Y']); L.new(sep.outputs['Z'], off.inputs['Z'])
    bmp = N.new('ShaderNodeMapping'); bmp.inputs['Scale'].default_value = (1 / 2.4,) * 3
    L.new(off.outputs['Vector'], bmp.inputs['Vector'])
    acc = None
    for k, nm in enumerate(['Floor', 'FloorDark', 'Gravel', 'Soil', 'Rock', 'Ruts', 'Track', 'Asphalt']):
        t = N.new('ShaderNodeTexImage')
        t.image = S.img(UP + f'/Terrain/Ground/T_GR_{nm}_A.png'); t.interpolation = 'Closest'
        L.new(tu.outputs['Vector'], t.inputs['Vector'])
        sc_ = N.new('ShaderNodeVectorMath'); sc_.operation = 'SCALE'
        L.new(t.outputs['Color'], sc_.inputs[0]); L.new(weights[k], sc_.inputs['Scale'])
        if acc is None:
            acc = sc_.outputs['Vector']
        else:
            ad = N.new('ShaderNodeVectorMath'); ad.operation = 'ADD'
            L.new(acc, ad.inputs[0]); L.new(sc_.outputs['Vector'], ad.inputs[1]); acc = ad.outputs['Vector']
    L.new(acc, pb.inputs['Base Color'])
    S.fog_wrap(m, pb.outputs['BSDF'])
    return m


# ---------------------------------------------------------------- models
def import_fbx(path, keep_lod0=True):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    if keep_lod0:
        for o in list(new):
            if '_LOD' in o.name and not o.name.endswith('_LOD0'):
                bpy.data.objects.remove(o, do_unlink=True); new.remove(o)
    return new


def proto(name, G, cache):
    if name in cache:
        return cache[name]
    path = UP + f'/Models/{name}.fbx'
    if not os.path.exists(path):
        cache[name] = None
        return None
    col = bpy.data.collections.new('P_' + name)
    objs = import_fbx(path)
    S.assign_game_mats(objs, G)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    cache[name] = col
    return col


def bridge(G):
    objs = import_fbx(UP + '/Models/Bridge30.fbx', keep_lod0=False)
    S.assign_game_mats(objs, G)
    x, y, z, w = 0.027617, 0.927355, -0.011108, -0.372997
    q = Quaternion((w, x, z, -y))
    M = Matrix.Translation(B(-331.3327, 331.6444, 19.46)) @ q.to_matrix().to_4x4()
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in objs if o.type == 'MESH' for v in o.data.vertices]
    low = [p for p in pts if p.z < 7.95]
    print('bridge lowest z', round(min(p.z for p in pts), 2), 'post feet (Unity x, z):', sorted({(round(-p.x, 1), round(-p.y, 1)) for p in low})[:6], flush=True)
    return objs


def gorge_model():
    with bpy.data.libraries.load(os.path.join(D, 'out', 'gorge_model.blend')) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('GORGE_')]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
        mat = o.data.materials[0]
        if mat and 'fogged' not in mat:
            pb = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            S.fog_wrap(mat, pb.outputs['BSDF'])
            mat['fogged'] = 1
    return dst.objects


def trees(H, G):
    names = json.load(open(os.path.join(D, '..', 'gorge', 'data', 'proto_names.json')))
    T = np.load(os.path.join(D, 'data', 'tile_trees.npy'))
    M = json.load(open(os.path.join(D, 'data', 'mask.json')))
    mask = np.fromfile(os.path.join(D, 'unity', 'gorge_mask.u8'), np.uint8).reshape(M['nz'], M['nx'])
    Gc = np.load(os.path.join(D, '..', 'gorge', 'data', 'ground_map.npy')).astype(np.float64)

    def mk(x, z):
        i = int(round((x - M['x0']) / M['step'])) - M['i0']; j = int(round((z - M['z0']) / M['step'])) - M['j0']
        return mask[j, i] if 0 <= i < M['nx'] and 0 <= j < M['nz'] else 0
    cache, holder = {}, bpy.data.collections.new('Trees')
    bpy.context.scene.collection.children.link(holder)
    rng = np.random.default_rng(5)
    placed, removed, refill = 0, 0, 0
    kept = []
    for x, y, z, w, h, r, idx in T:
        if not (AX0 + 5 < x < AX1 - 5 and AZ0 + 5 < z < AZ1 - 1):
            continue
        nm = names.get(str(int(idx)))
        if nm is None:
            continue
        if mk(x, z) in (1, 3):
            removed += 1
            continue
        d = abs(FP.sample(H, x, z) - FP.sample(Gc, x, z))
        if d >= 1.0 and rng.random() < 0.5:                 # the import replaces trees on new ground
            removed += 1
            continue
        kept.append((nm, x, z, w, h, r))
    # refill: new ground (|change| >= 1 m, outside the gorge) gets trees like the forest within 40 m
    from scipy.spatial import cKDTree
    kx = np.array([[k[1], k[2]] for k in kept])
    kd = cKDTree(kx)
    for gx in np.arange(AX0 + 5, AX1 - 5, 5.6):
        for gz in np.arange(AZ0 + 5, AZ1 - 1, 5.6):
            x, z = gx + rng.uniform(-2, 2), gz + rng.uniform(-2, 2)
            if mk(x, z) in (1, 3) or abs(FP.sample(H, x, z) - FP.sample(Gc, x, z)) < 1.0:
                continue
            nb = kd.query_ball_point([x, z], 40.0)
            if not nb:
                continue
            dens = len(nb) / (math.pi * 1600) * 31.4
            if rng.random() > dens:
                continue
            k = kept[nb[int(rng.integers(len(nb)))]]
            if k[0].startswith(('Rock', 'RockSet', 'Log', 'Stump', 'Snag', 'Old', 'Euro')):
                continue
            kept.append((k[0], x, z, k[3], k[4], rng.uniform(0, 6.28)))
            refill += 1
    for t in json.load(open(os.path.join(D, 'data', 'gorge_model.json')))['ledgeTrees']:
        kept.append((t['prefab'], t['x'], t['z'], t['scale'], t['scale'], t['yaw']))
    for nm, x, z, w, h, r in kept:
        base = nm.split('_t0')[0] if nm.startswith('Log_') else nm
        if nm.startswith('RockSet_'):
            base = 'Rock_' + str(1 + (zlib.crc32(nm.encode()) % 4))
        col = proto(base, G, cache)
        if col is None:
            continue
        inst = bpy.data.objects.new(f'T_{base}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = col
        if nm.startswith('RockSet_'):
            w = h = 0.35 + 0.35 * ((zlib.crc32(nm.encode()) >> 4) % 10) / 10.0
        inst.location = B(x, z, FP.sample(H, x, z) - 0.05)
        inst.rotation_euler = (0, 0, -r)
        inst.scale = (w, w, h)
        holder.objects.link(inst)
        placed += 1
    print(f'trees placed {placed}, removed {removed}, refill {refill}', flush=True)


# ---------------------------------------------------------------- water: the creek (ForestStreamsStep look) + package water
def water():
    C = json.load(open(os.path.join(D, 'data', 'creek.json')))
    c = C['creek']
    P = np.array(c['points']).reshape(-1, 3)              # x, z, y
    Wd = np.array(c['widths']); kinds = c['kinds']
    n = len(P)
    tan = np.gradient(P[:, :2], axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.stack([-tan[:, 1], tan[:, 0]], 1)
    wm = bpy.data.materials.new('G_CreekWater'); wm.use_nodes = True
    pb = wm.node_tree.nodes['Principled BSDF']
    pb.inputs['Base Color'].default_value = (0.012, 0.009, 0.006, 1); pb.inputs['Roughness'].default_value = 0.16
    S.fog_wrap(wm, pb.outputs['BSDF'])
    im = bpy.data.materials.new('G_LakeIce'); im.use_nodes = True
    Ni, Li = im.node_tree.nodes, im.node_tree.links
    pbi = Ni['Principled BSDF']; pbi.inputs['Roughness'].default_value = 0.4
    tci = Ni.new('ShaderNodeTexCoord'); mpi = Ni.new('ShaderNodeMapping'); mpi.inputs['Scale'].default_value = (1 / 3.0,) * 3
    txi = Ni.new('ShaderNodeTexImage'); txi.image = S.img(UP + '/Terrain/Ground/T_GR_LakeIce_A.png'); txi.interpolation = 'Closest'
    Li.new(tci.outputs['Object'], mpi.inputs['Vector']); Li.new(mpi.outputs['Vector'], txi.inputs['Vector']); Li.new(txi.outputs['Color'], pbi.inputs['Base Color'])
    S.fog_wrap(im, pbi.outputs['BSDF'])
    def strip(name, inner, outer, lift, on, both, mat):
        V, F = [], []
        for sg in ((-1, 1) if both else (1,)):
            base = len(V)
            for i in range(n):
                p = P[i]; sd = side[i] * sg
                a = p[:2] + sd * inner(i); b = p[:2] + sd * outer(i)
                V += [tuple(B(a[0], a[1], p[2] + lift)), tuple(B(b[0], b[1], p[2] + lift))]
                if i and on(i) and on(i - 1):
                    k = base + (i - 1) * 2
                    F.append((k, k + 2, k + 3, k + 1))
        me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.materials.append(mat)
        me.uv_layers.new(name='UVMap')
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        # ice/strip uvs: object coords via generated texture coords are fine for the preview
        return ob
    half = lambda i: Wd[i] / 2
    strip('Creek', lambda i: -half(i), lambda i: half(i), 0.0, lambda i: True, False, wm)
    noise = lambda i, salt: 0.5 + 0.5 * math.sin(i * 0.21 + salt) * math.cos(i * 0.13 + salt * 1.7)
    pool = lambda i: kinds[i] in ('pool', 'intake', 'riffle', 'steppool')
    strip('CreekIce', lambda i: half(i) - (min(half(i) * 0.7, 0.8 + 1.0 * noise(i, 3.1)) if kinds[i] in ('pool', 'intake') else 0.25 + 0.3 * noise(i, 7.3)),
          lambda i: half(i) + 0.25, 0.012, pool, True, im)
    # the package's water outside the cut (lakes, the spring above the line)
    Wf = json.load(open(os.path.join(D, 'data', 'water_full.json')))[0]
    V = np.array(Wf['v']); keepF = []
    cut = np.array(C['cut']['points']).reshape(-1, 2)
    from scipy.spatial import cKDTree
    kd = cKDTree(cut)
    for f in Wf['f']:
        cc = V[f].mean(0)
        if not (AX0 < cc[0] < AX1 and AZ0 < cc[2] < AZ1):
            continue
        d, i = kd.query([cc[0], cc[2]])
        if d < 8.0 and 0 < i < len(cut) - 1:
            continue
        keepF.append(f)
    idx = sorted({k for f in keepF for k in f}); rm = {k: j for j, k in enumerate(idx)}
    me = bpy.data.meshes.new('PkgWater')
    me.from_pydata([tuple(B(V[k][0], V[k][2], V[k][1])) for k in idx], [], [[rm[k] for k in f] for f in keepF])
    me.materials.append(wm)
    ob = bpy.data.objects.new('PkgWater', me); bpy.context.scene.collection.objects.link(ob)
    print('creek points', n, 'package water faces kept', len(keepF), flush=True)


# ---------------------------------------------------------------- light, cameras
def world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('Day'); w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.56, 0.61, 0.69, 1); bg.inputs['Strength'].default_value = 1.15
    sc.world = w
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = 2.6; ld.angle = math.radians(4); ld.color = (1.0, 0.97, 0.92)
    so = bpy.data.objects.new('Sun', ld); sc.collection.objects.link(so)
    el, az = math.radians(28.0), math.radians(225.0)
    d = Vector((-math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))     # Unity dir -> Blender
    so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def cam(name, eye, tgt, vfov):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle = math.radians(vfov); cd.clip_start = 0.1; cd.clip_end = 2000
    co = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(co)
    co.location = eye; co.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
    return co


def U(t, s, y):
    x, z = FP.at(t, s)
    return B(float(x), float(z), y)


TB = FP.TB
WAT = lambda t: float(np.interp(t, FP.TP, FP.WL))
VIEWS = {
    'deck_down': (U(TB + 2.4, 1.5, 21.4), U(TB + 55, 0, 8.5), 52.0),
    'deck_up': (U(TB - 4.2, 1.5, 21.4), U(TB - 55, 0, 8.5), 52.0),
    'cascade_up': (U(118, 0.8, 10.6), U(45, 0, 17.5), 55.0),
    'spring_down': (U(-6, 1.0, 31.5), U(60, 0, 15.0), 55.0),
    'north_down': (U(500, 1.5, 22.5), U(592, 0, 9.0), 52.0),
    'overview': (U(300, -170, 120.0), U(290, 0, 5.0), 58.0),
    'vp_bridge': (B(-351.551, 352.3982, 22.6415), B(-324.2865, 323.1296, 20.6415), 43.0),
    'river': (U(TB + 30, -1.5, 9.4), U(TB - 2, 0.5, 15.5), 58.0),
    'start_side': (U(-25, -28, 42.0), U(12, 0, 22.0), 55.0),
    'north_edge': (U(560, 0.5, 9.6), U(600, 0, 10.5), 60.0),
    'rim_mid': (U(380, -3.0, 30.0), U(460, 0, 12.0), 52.0),
}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    out, want = argv[0], (argv[1].split(',') if len(argv) > 1 and argv[1] != '-' else [])
    spp = int(argv[2]) if len(argv) > 2 else 16
    res = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (1280, 720)
    if '--nofog' in sys.argv:
        S.FOG['start'], S.FOG['end'] = 400.0, 2000.0
    S.reset()
    G = S.game_materials()
    H, i0, i1, j0, j1 = ground_area()
    splat_after(H)
    terrain_mesh(H, i0, i1, j0, j1, terrain_material())
    gorge_model()
    water()
    bridge(G)
    trees(H, G)
    world()
    cams = {k: cam(k, *v) for k, v in VIEWS.items()}
    S.setup_render(spp, res)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    os.makedirs(os.path.join(D, 'rend'), exist_ok=True)
    for v in want:
        S.render(cams[v], os.path.join(D, 'rend', v + '.png'))
        print('rendered', v, flush=True)


if __name__ == '__main__':
    main()
