"""StartWache build (tools/snow_style lib, after start_build): the guard house's objects with their pivots as origins, the
Wache atlas (1024, the shed's 51.3 px/m) baked with psxbake + wache_paint, the start panel (start_tex) on the lens and the halo
card, glass; the roof snow and the icicles (the post's snow materials M_SP_Snow / M_SP_Ice in Unity); the contract
(parts, sockets, colliders, the booth's parts that move into the house) and StartWache.fbx (each object at its pivot).
python3.11 -I wache_build.py [--draft] -> out/wache.blend, out/wache.json, out/wache_contract.json, out/StartWache.fbx, tex/*"""
import sys, os, math, json, time, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import start_tex as ST
import gen_kit as K
import wache_kit as W

DRAFT = '--draft' in sys.argv
ROOTDIR = os.path.dirname(HERE)
TEX = os.path.join(ROOTDIR, 'tex')
OUT = os.path.join(ROOTDIR, 'out')
os.makedirs(TEX, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
INFO = {}
SHED_PPM = 51.3
PB.POS_SCALE = 12.0
RNG = random.Random(2912)


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def r4(v):
    return [round(float(a), 4) + 0.0 for a in v]


def to_unity(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
PB_BASE, PB_EMI = ST.build(TEX)

# ------------------------------------------------------------------ 1. geometry
W.build_wache()
C = K.CONTRACT
missing = [n for n in K.KBS if n not in C['parts']]
assert not missing, f'objects without a contract entry: {missing}'
coll = bpy.data.collections.new(W.ROOT)
bpy.context.scene.collection.children.link(coll)
objs = {}
for name, k in K.KBS.items():
    if name == W.ROOT:
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-4)
    big = [f for f in k.bm.faces if len(f.verts) > 4]
    if big:
        bmesh.ops.triangulate(k.bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    o = k.to_object(name, coll=coll, pivot=Vector(C['parts'][name]['pivot']))
    objs[name] = o
log('objects', len(objs), sorted(objs))
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 2. the atlas (or flat zone colours for the draft)
import wache_paint as WP
atlas_objs = [o for n, o in objs.items() if K.ATLAS[n] == 'Wache']
if DRAFT:
    cache = {}
    for o in atlas_objs:
        me = o.data
        zl = [round(a.value) for a in me.attributes['zone'].data]
        me.materials.clear()
        idx = {}
        for z in sorted(set(zl)):
            if z not in cache:
                m = bpy.data.materials.new(f'draft_{z}')
                m.use_nodes = True
                pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                c = PB.lin(*WP.DRAFT_COL.get(z, (255, 0, 255)))
                pb.inputs['Base Color'].default_value = (float(c[0]), float(c[1]), float(c[2]), 1)
                pb.inputs['Roughness'].default_value = 0.8
                cache[z] = m
            idx[z] = len(me.materials)
            me.materials.append(cache[z])
        for poly, z in zip(me.polygons, zl):
            poly.material_index = idx[z]
else:
    INFO['atlases'] = {}
    PB.make_atlas('Wache', atlas_objs, WP.paint_wache, TEX, prefix='T_Start_', mat_prefix='M_Start_', size=1024, ao_min=0.35,
                  ao_dist=0.40, rough=0.85, log=log, info=INFO['atlases'], ppm_cap=SHED_PPM,
                  zone_scale={W.Z_FELT: 0.6, W.Z_SOFFIT: 0.8, K.Z_LINING: 0.8, W.Z_CAL: 2.0, W.Z_BOOK: 2.0, W.Z_RADIO: 2.0,
                              W.Z_EXT: 2.0, W.Z_METER: 2.0, W.Z_PORC: 2.0},
                  prio_zones=(W.Z_CAL, W.Z_RADIO, W.Z_BOOK, K.Z_RUSTPIPE, W.Z_EXT, W.Z_METER))

# ------------------------------------------------------------------ 3. explicit materials (the project's: M_Start_*)
m_lens = PB.tex_mat('M_Start_Lamp_Booth', PB_BASE, PB_EMI, 3.0, rough=0.2)
m_glow = bpy.data.materials.new('M_Start_Glow')
m_glow.use_nodes = True
nt = m_glow.node_tree
nt.nodes.clear()
o_ = nt.nodes.new('ShaderNodeOutputMaterial')
uvn = nt.nodes.new('ShaderNodeUVMap')
uvn.uv_map = 'PSX'
ti = nt.nodes.new('ShaderNodeTexImage')
ti.image = bpy.data.images.load(PB_EMI, check_existing=True)
ti.interpolation = 'Closest'
nt.links.new(uvn.outputs[0], ti.inputs[0])
em = nt.nodes.new('ShaderNodeEmission')
em.inputs['Strength'].default_value = 0.0
nt.links.new(ti.outputs[0], em.inputs['Color'])
tr = nt.nodes.new('ShaderNodeBsdfTransparent')
add = nt.nodes.new('ShaderNodeAddShader')
nt.links.new(tr.outputs[0], add.inputs[0])
nt.links.new(em.outputs[0], add.inputs[1])
nt.links.new(add.outputs[0], o_.inputs['Surface'])
m_glow['night_emit'] = 2.0
m_glow['blend'] = 'additive'
try:
    m_glow.surface_render_method = 'BLENDED'
except AttributeError:
    pass
m_glass = P.psx_glass('M_Start_Glass', tint=(0.12, 0.13, 0.12), alpha=0.45)
MAP_PNG = os.path.join(TEX, 'T_Start_WacheMap.png')        # the site plan's own texture (wache_map.py)
m_map = P.psx_material('M_Start_WacheMap', MAP_PNG, rough=0.85) if os.path.exists(MAP_PNG) else bpy.data.materials.new('M_Start_WacheMap')
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'Wache':
        continue
    o.data.materials.clear()
    if a == 'glass':
        o.data.materials.append(m_glass)
    elif a.startswith('lens:'):
        o.data.materials.append(m_lens)
    elif a == 'glow':
        o.data.materials.append(m_glow)
        o.visible_shadow = False
    elif a == 'map':
        o.data.materials.append(m_map)
    else:
        raise ValueError(a)

# ------------------------------------------------------------------ 4. the roof snow (cushion, cornices) and the icicles
m_snow = bpy.data.materials.new('M_SP_Snow')
m_snow.use_nodes = True
pbs = next(n for n in m_snow.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pbs.inputs['Base Color'].default_value = (0.80, 0.84, 0.90, 1)
pbs.inputs['Roughness'].default_value = 0.9
m_ice = bpy.data.materials.new('M_SP_Ice')
m_ice.use_nodes = True
pbi = next(n for n in m_ice.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pbi.inputs['Base Color'].default_value = (0.55, 0.64, 0.74, 1)
pbi.inputs['Roughness'].default_value = 0.15
# the cushion: a closed heightfield over the roof; it hangs over the front (-y) and the road side (+x) as a cornice with a
# curled lip (the wind brings the snow from the back), stops at the drip edge at the back and the left
from noise import fbm
sb = bmesh.new()
ice = bmesh.new()


def cushion(x0, x1, y0, y1, base, H, lip, nx, ny, seed):
    """a closed snow heightfield over [x0, x1] x [y0, y1]: bottom at base(x, y), thickness H(x, y) * shape, where lip(x, y) > 0
    past the support's edge (0 at the edge .. 1 at the lip's end) the cushion curls down and thins to the lip"""
    xs = np.linspace(x0, x1, nx + 1)
    ys = np.linspace(y0, y1, ny + 1)
    XX, YY = np.meshgrid(xs, ys, indexing='ij')
    pts = np.stack([XX.ravel(), YY.ravel(), np.zeros(XX.size)], 1).astype(np.float32)
    nz = fbm(pts, 0.9, 3, seed=seed).reshape(XX.shape)
    nz2 = fbm(pts, 3.5, 2, seed=seed + 1).reshape(XX.shape)
    o = lip(XX, YY)
    h = H(XX, YY) * (1.0 + 0.24 * (nz - 0.5) * 2 + 0.12 * (nz2 - 0.5) * 2)
    lp = np.clip(o, 0, 1)
    zb0 = base(XX, YY)
    ztop = zb0 + h * np.where(o > 0, (1 - lp ** 1.6) * 0.85 + 0.15 * (1 - lp), 1.0)
    zbot = np.where(o > 0, zb0 - 0.02 - 0.09 * np.sin(lp * math.pi * 0.5) ** 0.7, zb0 - 0.002)
    ztop = np.maximum(ztop, zbot + 0.004)
    VT = [[sb.verts.new((float(XX[i, j]), float(YY[i, j]), float(ztop[i, j]))) for j in range(ny + 1)] for i in range(nx + 1)]
    VB = [[sb.verts.new((float(XX[i, j]), float(YY[i, j]), float(zbot[i, j]))) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            sb.faces.new((VT[i][j], VT[i + 1][j], VT[i + 1][j + 1], VT[i][j + 1]))
            sb.faces.new((VB[i][j], VB[i][j + 1], VB[i + 1][j + 1], VB[i + 1][j]))
    for i in range(nx):
        sb.faces.new((VT[i][0], VB[i][0], VB[i + 1][0], VT[i + 1][0]))
        sb.faces.new((VT[i + 1][ny], VB[i + 1][ny], VB[i][ny], VT[i][ny]))
    for j in range(ny):
        sb.faces.new((VT[0][j + 1], VB[0][j + 1], VB[0][j], VT[0][j]))
        sb.faces.new((VT[nx][j], VB[nx][j], VB[nx][j + 1], VT[nx][j + 1]))
    return xs, ys


def edge_lip(ex0, ex1, ey0, ey1, ov):
    """0 inside the support [ex0, ex1] x [ey0, ey1], rising to 1 at the end of each side's overhang ov[side]"""
    def f(X, Y):
        return np.maximum(np.maximum((X - ex1) / ov['+x'], (ex0 - X) / ov['-x']), np.maximum((Y - ey1) / ov['+y'], (ey0 - Y) / ov['-y']))
    return f


def icicles(pts, lmin, lmax, seed):
    rng = random.Random(seed)
    for (px, py, pz) in pts:
        ln = lmin + (lmax - lmin) * rng.random() ** 2
        rad = 0.02 + 0.026 * rng.random()
        res = bmesh.ops.create_cone(ice, cap_ends=True, cap_tris=False, segments=5, radius1=0.0, radius2=rad, depth=ln)
        bmesh.ops.transform(ice, matrix=Matrix.Translation(Vector((px, py, pz - ln / 2))), verts=res['verts'])


# the roof: ~0.25 on the felt; a cornice over the front (the wind brings the snow over the high edge), a little over the road
# verge, to the fascia at the back (the gutter stays clear, icicles hang from it)
OVR = {'-y': 0.16, '+x': 0.10, '+y': 0.04, '-x': 0.03}
ex0, ex1, ey0, ey1 = -W.XV - 0.022, W.XV + 0.022, W.YF - 0.012, W.YB + 0.022
cushion(ex0 - OVR['-x'], ex1 + OVR['+x'], ey0 - OVR['-y'], ey1 + OVR['+y'], lambda X, Y: W.z_bt(Y) + 0.008,
        lambda X, Y: 0.25 * (0.6 + 0.4 * np.clip(np.minimum(np.minimum(X - ex0, ex1 - X), np.minimum(Y - ey0, ey1 - Y)) / 0.35, 0, 1) ** 0.5),
        edge_lip(ex0, ex1, ey0, ey1, OVR), 22, 24, 77)
# the canopy: ~0.14, a lip over its outer edge
C_ = W.CANOPY
czt = lambda X: C_['z_wall'] + (C_['z_edge'] - C_['z_wall']) * (X - W.HX) / (C_['x1'] - W.HX)
cov = {'+x': 0.08, '-x': 0.001, '+y': 0.03, '-y': 0.03}
cushion(W.HX + 0.01, C_['x1'] + 0.022 + cov['+x'], C_['y0'] - 0.03, C_['y1'] + 0.03, lambda X, Y: czt(X) + 0.006,
        lambda X, Y: 0.14 * np.ones_like(X), edge_lip(W.HX, C_['x1'] + 0.022, C_['y0'], C_['y1'], cov), 8, 10, 81)
# the woodpile's top, the outer sills and the counter
P_ = W.PILE
xs_, top_ = W.PILE_TOP                                     # the stack's uneven top, the gaps between its pieces bridged (6 cm)
env_ = np.array([top_[max(0, j - 12):j + 13].max() for j in range(len(top_))])
cushion(P_['x0'] - 0.08, P_['x1'] + 0.08, P_['y0'] - 0.01, P_['y1'] + 0.05, lambda X, Y: np.interp(X, xs_, env_) + 0.004,
        lambda X, Y: 0.12 * np.ones_like(X), edge_lip(P_['x0'], P_['x1'], P_['y0'], P_['y1'], {'+x': 0.08, '-x': 0.08, '+y': 0.05, '-y': 0.01}),
        24, 4, 83)
for (x0_, x1_, y0_, y1_, z_) in ((W.WIN_F['u0'] - 0.02, 0.24, -W.HY - 0.045, -W.HY + 0.0, W.WIN_F['z0']),
                                 (0.26, W.WIN_F['u1'] + 0.02, -W.HY - 0.34, -W.HY + 0.0, W.WIN_F['z0']),
                                 (W.HX, W.HX + 0.045, W.WIN_S['u0'] - 0.02, W.WIN_S['u1'] + 0.02, W.WIN_S['z0']),
                                 (-W.HX - 0.045, -W.HX, W.WIN_L['u0'] - 0.02, W.WIN_L['u1'] + 0.02, W.WIN_L['z0'])):
    cushion(x0_, x1_, y0_, y1_, lambda X, Y, z_=z_: z_ + 0.002 + 0.0 * X, lambda X, Y: 0.045 * np.ones_like(X),
            lambda X, Y: -np.ones_like(X), 4, 4, 85)
# icicles: from the gutter (many), the front cornice, the canopy's edge (none over the door's swing)
rng_ = random.Random(2913)
gyc, gzc = W.YB + 0.022 + 0.065, W.z_bt(W.YB) - 0.04 - 0.06
pts = []
xg = -W.XV + 0.05
while xg < W.XV - 0.05:
    pts.append((xg, gyc + (rng_.random() - 0.5) * 0.06, gzc))
    xg += 0.10 + 0.28 * rng_.random()
icicles(pts, 0.10, 0.75, 91)
pts = []
xg = -W.XV + 0.1
while xg < W.XV:
    pts.append((xg, ey0 - OVR['-y'] * (0.5 + 0.3 * rng_.random()), W.z_bt(ey0) - 0.06))
    xg += 0.25 + 0.55 * rng_.random()
icicles(pts, 0.08, 0.40, 92)
pts = []
yg = C_['y0'] + 0.05
while yg < C_['y1']:
    if not (W.DOOR['u1'] - 0.95 < yg < W.DOOR['u1'] + 0.05):
        pts.append((C_['x1'] + 0.05, yg, czt(C_['x1']) - 0.03))
    yg += 0.12 + 0.25 * rng_.random()
icicles(pts, 0.06, 0.35, 93)
me = bpy.data.meshes.new('Wache_Snow')
sb.to_mesh(me)
sb.free()
me.materials.append(m_snow)
me.shade_smooth()
so = bpy.data.objects.new('Wache_Snow', me)
coll.objects.link(so)
uvl = me.uv_layers.new(name='UVMap')
for p_ in me.polygons:
    for li in p_.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        uvl.data[li].uv = (co.x / 2.0, co.y / 2.0)
mi = bpy.data.meshes.new('Wache_Ice')
ice.to_mesh(mi)
ice.free()
mi.materials.append(m_ice)
io = bpy.data.objects.new('Wache_Ice', mi)
coll.objects.link(io)
objs['Wache_Snow'], objs['Wache_Ice'] = so, io
C['parts']['Wache_Snow'] = dict(kind='static', pivot=[0.0, 0.0, 0.0], parent=W.ROOT, note='the roof snow (~0.27) hanging over the '
                                'front and the road side as a cornice (M_SP_Snow, the post\'s snow)', states=[], axis=None, range=None, unit='deg', rest=0.0)
C['parts']['Wache_Ice'] = dict(kind='static', pivot=[0.0, 0.0, 0.0], parent=W.ROOT, note='icicles under the cornices (M_SP_Ice)',
                               states=[], axis=None, range=None, unit='deg', rest=0.0)

# ------------------------------------------------------------------ 5. the contract in Unity terms
for k_, p in C['parts'].items():
    p['pivotUnity'] = to_unity(p['pivot'])
for s in C['sockets'].values():
    s['posUnity'] = to_unity(s['pos'])
C['colliders'] = []
for name, par, (x0, x1, y0, y1, z0, z1) in W.BOXES:
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    size = Vector((x1 - x0, y1 - y0, z1 - z0))
    C['colliders'].append(dict(name='COL_' + name, parent=par, center=r4(c), size=r4(size), centerUnity=to_unity(c),
                               sizeUnity=r4((size.x, size.z, size.y))))
C['moves'] = {k_: dict(delta=r4(v), deltaUnity=to_unity(v)) for k_, v in W.MOVES.items()}
tris = {}
for o in objs.values():
    tris[o.name] = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
INFO['tris'] = tris
INFO['tris_total'] = sum(tris.values())
C['meta'] = dict(version='1.2', units='metres', frame='StartWache in its own frame: z up, the front (the big window) -y, the road wall '
                 '(the door) +x; origin on the ground in the middle of the footprint; Unity (x, y, z) -> (-x, z, -y)',
                 template='StartBooth.prefab: its root takes the body (StartWache mesh, M_Start_Wache), its children move by '
                          '`moves` (deltaUnity), its slots go to `sockets`, its boxes are replaced by `colliders`')
sfx = '_draft' if DRAFT else ''
json.dump(C, open(os.path.join(OUT, f'wache_contract{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(INFO, open(os.path.join(OUT, f'wache{sfx}.json'), 'w'), indent=1)
log('tris', INFO['tris_total'], tris)
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    uvs = o.data.uv_layers
    if 'PSX' in uvs:
        for u in [u for u in uvs if u.name != 'PSX']:
            uvs.remove(u)
        uvs['PSX'].active = True
    if 'zone' in o.data.attributes and not DRAFT:
        o.data.attributes.remove(o.data.attributes['zone'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'wache{sfx}.blend'))
log('saved', f'wache{sfx}.blend')

# ------------------------------------------------------------------ 6. FBX (each object at its pivot, Unity axes baked)
if not DRAFT:
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs.values():
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[W.ROOT]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'StartWache.fbx'), use_selection=True, object_types={'MESH'}, global_scale=1.0,
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=True, mesh_smooth_type='FACE', use_tspace=False, use_triangles=True,
                             colors_type='NONE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_mesh_modifiers=True)
    log('fbx', os.path.join(OUT, 'StartWache.fbx'))
