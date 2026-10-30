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
                  zone_scale={W.Z_FELT: 0.6, W.Z_SOFFIT: 0.8, K.Z_LINING: 0.8, W.Z_CAL: 2.0, W.Z_BOOK: 2.0, W.Z_RADIO: 2.0},
                  prio_zones=(W.Z_CAL, W.Z_RADIO, W.Z_BOOK, W.Z_COAT, K.Z_RUSTPIPE))

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
roof_top = W.ZR + 0.012
OVR = {'-y': 0.16, '+x': 0.22, '+y': 0.03, '-x': 0.03}
x0g, x1g = -W.FX - 0.012 - OVR['-x'], W.FX + 0.012 + OVR['+x']
y0g, y1g = -W.FY - 0.012 - OVR['-y'], W.FY + 0.012 + OVR['+y']
NXg, NYg = 20, 22
xs = np.linspace(x0g, x1g, NXg + 1)
ys = np.linspace(y0g, y1g, NYg + 1)
XX, YY = np.meshgrid(xs, ys, indexing='ij')
pts = np.stack([XX.ravel(), YY.ravel(), np.zeros(XX.size)], 1).astype(np.float32)
nz = fbm(pts, 0.9, 3, seed=77).reshape(XX.shape)
nz2 = fbm(pts, 3.5, 2, seed=78).reshape(XX.shape)
ex, ey = W.FX + 0.012, W.FY + 0.012
# how far past the roof edge (>0 outside), per side, normalised by that side's overhang
ox = np.maximum((XX - ex) / OVR['+x'], (-ex - XX) / OVR['-x'])
oy = np.maximum((YY - ey) / OVR['+y'], (-ey - YY) / OVR['-y'])
o = np.maximum(ox, oy)                                            # 0 at the edge, 1 at the lip's end
inside_d = np.minimum(np.minimum(ex - XX, XX + ex), np.minimum(ey - YY, YY + ey))
H = 0.27 + 0.06 * (nz - 0.5) * 2 + 0.03 * (nz2 - 0.5) * 2
H = H * (0.55 + 0.45 * np.clip(inside_d / 0.35, 0, 1) ** 0.5) * np.where(o > 0, 1.0, 1.0)
lip = np.clip(o, 0, 1)
ztop = roof_top + H * np.where(o > 0, (1 - lip ** 1.6) * 0.85 + 0.15 * (1 - lip), 1.0)
zbot = np.where(o > 0, roof_top - 0.02 - 0.10 * np.sin(np.clip(lip, 0, 1) * math.pi * 0.5) ** 0.7, roof_top - 0.002)
ztop = np.maximum(ztop, zbot + 0.004)
sb = bmesh.new()
VT = [[sb.verts.new((float(XX[i, j]), float(YY[i, j]), float(ztop[i, j]))) for j in range(NYg + 1)] for i in range(NXg + 1)]
VB = [[sb.verts.new((float(XX[i, j]), float(YY[i, j]), float(zbot[i, j]))) for j in range(NYg + 1)] for i in range(NXg + 1)]
for i in range(NXg):
    for j in range(NYg):
        sb.faces.new((VT[i][j], VT[i + 1][j], VT[i + 1][j + 1], VT[i][j + 1]))
        sb.faces.new((VB[i][j], VB[i][j + 1], VB[i + 1][j + 1], VB[i + 1][j]))
for i in range(NXg):
    sb.faces.new((VT[i][0], VB[i][0], VB[i + 1][0], VT[i + 1][0]))
    sb.faces.new((VT[i + 1][NYg], VB[i + 1][NYg], VB[i][NYg], VT[i][NYg]))
for j in range(NYg):
    sb.faces.new((VT[0][j + 1], VB[0][j + 1], VB[0][j], VT[0][j]))
    sb.faces.new((VT[NXg][j], VB[NXg][j], VB[NXg][j + 1], VT[NXg][j + 1]))
bmesh.ops.recalc_face_normals(sb, faces=list(sb.faces))
# icicles from the lips (front and the road side; none over the door lamp)
ice = bmesh.new()
for side in ('-y', '+x'):
    L_ = (x1g - x0g) if side == '-y' else (y1g - y0g)
    s_ = 0.0
    while True:
        s_ += 0.18 + 0.40 * RNG.random()
        if s_ >= L_ - 0.05:
            break
        if side == '-y':
            px, py = x0g + s_, -ey - OVR['-y'] * (0.55 + 0.25 * RNG.random())
        else:
            px, py = ex + OVR['+x'] * (0.55 + 0.25 * RNG.random()), y0g + s_
            if abs(py - W.LAMP.y) < 0.55:
                continue
        if side == '-y' and px > ex:
            continue
        lp = (0.10 + 0.55 * RNG.random() ** 2) * (1.3 if side == '+x' else 1.0)
        rad = 0.022 + 0.028 * RNG.random()
        zb_ = roof_top - 0.06 - 0.06 * RNG.random()
        res = bmesh.ops.create_cone(ice, cap_ends=True, cap_tris=False, segments=5, radius1=0.0, radius2=rad, depth=lp)
        bmesh.ops.transform(ice, matrix=Matrix.Translation(Vector((px, py, zb_ - lp / 2))), verts=res['verts'])
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
