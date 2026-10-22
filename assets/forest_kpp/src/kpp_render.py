"""Preview renders of the checkpoint (out/kpp.blend posed from out/kpp_contract.json) in its Update 3 surroundings: the
terrain from the map's ground points (weeds, ferns, rocks, tree bases round the KPP), the road through the gate, the real
trees (Forest_Layout.json trees: firs, spruces, birches, dead trees as proxies at their places and heights), the map's
chain-link fence (FenceChain proxies at their places).  Views: from the road by day and at night (the batten flickering),
the booth close, the back with the door open, the walkway side, the power-on night from inside the station, the barrier
(the padlock eyes; the boom up), the gate (closed from outside; open from inside), inside by day from the door and from
the window corner, the key cabinet open, the road-side desk, inside at night, plan views (the booth, the points, the
colliders, the site), the Update 3 comparison cameras (look_old_kpp.py) and the map's KPP viewpoint (game view).
python3 -I kpp_render.py <views> [spp] [--draft]  -> rend/kpp/<view>.png (rend/kpp_draft with --draft)"""
import sys, os, math, json, random, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P

views = sys.argv[1].split(',')
spp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 48
DRAFT = '--draft' in sys.argv
sfx = '_draft' if DRAFT else ''
OUT = os.path.join(P.HERE, 'rend', 'kpp' + sfx)
os.makedirs(OUT, exist_ok=True)
SITE = json.load(open(os.path.join(P.HERE, 'kpp_site.json')))      # the map round the KPP (Forest_Layout.json, booth frame)
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'kpp{sfx}.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', f'kpp_contract{sfx}.json')))
LJ = json.load(open(os.path.join(P.HERE, 'out', 'kpp_lights.json')))['lights']
ROAD = [(70, -170), (33, -73), (16, -30), (8.5, -8), (7.5, 0), (4.5, 8), (-6.5, 20), (-30, 55)]


def prop(o):
    o['scene_prop'] = 1
    return o


# ------------------------------------------------------------------ terrain: inverse-distance heights from the map's points,
# flat round the station, the road strip a little lower
G = np.array(SITE['ground'], np.float64)


def road_dist(x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(ROAD[:-1], ROAD[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def ground_z(x, y):
    d = np.hypot(G[:, 0] - x, G[:, 1] - y)
    i = np.argsort(d)[:8]
    w = 1.0 / np.maximum(d[i], 0.5) ** 2
    z = float((G[i, 2] * w).sum() / w.sum())
    if abs(x) < 3.2 and abs(y) < 2.7:
        z = min(z, -0.15)
    rd = road_dist(x, y)
    if rd < 3.2:
        z -= 0.22 * (1 - max(0.0, rd - 2.5) / 0.7)
    return z


bm = bmesh.new()
xs = np.concatenate([np.arange(-110, -30, 4.0), np.arange(-30, 30, 1.0), np.arange(30, 110.1, 4.0)])
ys = np.concatenate([np.arange(-150, -30, 4.0), np.arange(-30, 30, 1.0), np.arange(30, 110.1, 4.0)])
vs = {}
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        vs[i, j] = bm.verts.new((x, y, ground_z(x, y) - 0.004))
road_faces = []
for i in range(len(xs) - 1):
    for j in range(len(ys) - 1):
        f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        f.material_index = 1 if road_dist(cx, cy) < 2.6 else 0
gme = bpy.data.meshes.new('Ground')
bm.to_mesh(gme)
bm.free()
g = prop(bpy.data.objects.new('Ground', gme))
sc.collection.objects.link(g)
gm = bpy.data.materials.new('ground')
gm.use_nodes = True
gnt = gm.node_tree
gpb = gnt.nodes['Principled BSDF']
gpb.inputs['Roughness'].default_value = 0.95
noi = gnt.nodes.new('ShaderNodeTexNoise')
noi.inputs['Scale'].default_value = 0.8
ramp = gnt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.050, 0.044, 0.028, 1)
ramp.color_ramp.elements[1].color = (0.10, 0.10, 0.052, 1)
gnt.links.new(noi.outputs['Fac'], ramp.inputs['Fac'])
gnt.links.new(ramp.outputs['Color'], gpb.inputs['Base Color'])
rm = bpy.data.materials.new('road')
rm.use_nodes = True
rm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.045, 0.043, 0.040, 1)
rm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
gme.materials.append(gm)
gme.materials.append(rm)
# trees at their places (the map's trees: firs, spruces, birches, dead trees), cone proxies of their height
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark = bpy.data.materials.new('spruce')
dark.use_nodes = True
dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.018, 0.034, 0.024, 1)
trunk = bpy.data.materials.new('trunk')
trunk.use_nodes = True
trunk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.06, 0.045, 0.035, 1)
birchm = bpy.data.materials.new('birch')
birchm.use_nodes = True
birchm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.11, 0.10, 0.05, 1)
for t in SITE['trees']:
    nm = t['m']
    if nm.startswith(('Weeds', 'Fern', 'Bush', 'Grass')):
        continue
    try:
        h = float(''.join(ch for ch in nm.split('_')[1] if ch.isdigit())) * t['s']
    except ValueError:
        h = 12.0 * t['s']
    x, y, z0 = t['p']
    objs_ = []
    if nm.startswith('Birch'):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=h * 0.16, location=(x, y, z0 + h * 0.68))
        objs_.append(bpy.context.object)
        objs_[-1].data.materials.append(birchm)
    elif nm.startswith('Dead'):
        pass
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.17, depth=h * 0.82, location=(x, y, z0 + h * 0.18 + h * 0.41))
        objs_.append(bpy.context.object)
        objs_[-1].data.materials.append(dark)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=max(0.08, h * 0.012), depth=h * (0.9 if nm.startswith('Dead') else 0.3),
                                        location=(x, y, z0 + h * (0.45 if nm.startswith('Dead') else 0.15)))
    objs_.append(bpy.context.object)
    objs_[-1].data.materials.append(trunk)
    for o_ in objs_:
        for c in o_.users_collection:
            c.objects.unlink(o_)
        trees.objects.link(o_)
        prop(o_)
# the map's chain-link fence (FenceChain, 3 m segments): posts, top rail, the mesh with the KPP chain-link material
fence = bpy.data.collections.new('Fence')
sc.collection.children.link(fence)
chain = bpy.data.materials.get('M_Kpp_ChainLink')
steel = bpy.data.materials.new('fence_steel')
steel.use_nodes = True
steel.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.30, 0.31, 0.30, 1)
for f_ in SITE['fences']:
    x, y, z0 = f_['p']
    a = math.radians(f_['yaw'])
    ux, uy = math.cos(a), math.sin(a)
    bmf = bmesh.new()
    uvl = bmf.loops.layers.uv.new('PSX')
    pts = [(x - 1.5 * ux, y - 1.5 * uy, z0 + 0.05), (x + 1.5 * ux, y + 1.5 * uy, z0 + 0.05), (x + 1.5 * ux, y + 1.5 * uy, z0 + 2.0),
           (x - 1.5 * ux, y - 1.5 * uy, z0 + 2.0)]
    nx_, ny_ = -uy * 0.0006, ux * 0.0006
    for sgn, order in ((1, (0, 1, 2, 3)), (-1, (3, 2, 1, 0))):
        vv = [bmf.verts.new((p_[0] + sgn * nx_, p_[1] + sgn * ny_, p_[2])) for p_ in pts]
        fc = bmf.faces.new([vv[i] for i in order])
        for l_, i in zip(fc.loops, order):
            l_[uvl].uv = ((0.0, 0.0), (6.0, 0.0), (6.0, 3.9), (0.0, 3.9))[i]
    mef = bpy.data.meshes.new('FenceMesh')
    bmf.to_mesh(mef)
    bmf.free()
    of = prop(bpy.data.objects.new('FenceMesh', mef))
    mef.materials.append(chain)
    fence.objects.link(of)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.03, depth=2.5, location=(x - 1.5 * ux, y - 1.5 * uy, z0 + 1.15))
    po = bpy.context.object
    po.data.materials.append(steel)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.018, depth=3.0, location=(x, y, z0 + 2.0),
                                        rotation=(0, math.pi / 2, a))
    tr_ = bpy.context.object
    tr_.data.materials.append(steel)
    for o_ in (po, tr_):
        for c in o_.users_collection:
            c.objects.unlink(o_)
        fence.objects.link(o_)
        prop(o_)

# ------------------------------------------------------------------ lamps: IES point lights + lens glow (the van / plane method)
import van_lights as VL
LM = {}
for it in LJ:
    LM[it['type']] = dict(color=it['colorLinear'], k_norm=1.0 / (VL.K_CYCLES * it['peakCandela']))
IESDIR = os.path.join(P.HERE, 'tex', 'kpp', 'IES')
ies_txt = {}
for t_ in LM:
    pth = os.path.join(IESDIR, t_ + '.ies')
    if os.path.exists(pth):
        tx = bpy.data.texts.new('IES_%s.ies' % t_)
        tx.from_string(open(pth).read())
        ies_txt[t_] = tx


def ies_chain(nt, t_, vec):
    if t_ not in ies_txt:
        v = nt.nodes.new('ShaderNodeValue')
        v.outputs[0].default_value = 1.0
        return v.outputs[0]
    ies = nt.nodes.new('ShaderNodeTexIES')
    ies.mode = 'INTERNAL'
    ies.ies = ies_txt[t_]
    nt.links.new(vec, ies.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeMath')
    nm.operation = 'MULTIPLY'
    nm.inputs[1].default_value = LM[t_]['k_norm']
    nt.links.new(ies.outputs['Fac'], nm.inputs[0])
    return nm.outputs[0]


def lamp_axes(e):
    d = Vector(e['dir']).normalized()
    up = Vector(e['up'])
    up = (up - d * up.dot(d)).normalized()
    zl = -d
    return up.cross(zl).normalized(), up, zl


lights, lens_levels = [], []
for e in sorted([o for o in bpy.data.objects if o.name.startswith('LIGHT_')], key=lambda o: o.name):
    t_ = e['type']
    ld = bpy.data.lights.new('L_' + e.name[6:], 'POINT')
    ld.energy = 4 * math.pi ** 2 * e['intensity_urp']
    ld.shadow_soft_size = 0.03
    ld.use_nodes = True
    nt = ld.node_tree
    em = next(n for n in nt.nodes if n.type == 'EMISSION')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(ies_chain(nt, t_, tc.outputs['Normal']), em.inputs['Strength'])
    em.inputs['Color'].default_value = (*LM[t_]['color'], 1.0)
    ob = bpy.data.objects.new(ld.name, ld)
    sc.collection.objects.link(ob)
    xl, yl, zl = lamp_axes(e)
    ob.matrix_world = Matrix.Translation(e.matrix_world.translation) @ Matrix((xl, yl, zl)).transposed().to_4x4()
    ob['group'] = e['group']
    lights.append(ob)
    lo_ = bpy.data.objects[e['lens']]
    mat = lo_.data.materials[0].copy()
    mat.name = 'M_LensFX_' + e.name[6:]
    lo_.data.materials[0] = mat
    mat.cycles.emission_sampling = 'NONE'
    N2, Lk = mat.node_tree.nodes, mat.node_tree.links
    pb = next(n for n in N2 if n.type == 'BSDF_PRINCIPLED')
    lev = N2.new('ShaderNodeValue')
    lev.outputs[0].default_value = 0.0
    g1 = N2.new('ShaderNodeMath')
    g1.operation = 'MULTIPLY'
    Lk.new(lev.outputs[0], g1.inputs[0])
    g1.inputs[1].default_value = 6.0
    Lk.new(g1.outputs[0], pb.inputs['Emission Strength'])
    lens_levels.append((lev, e['group']))
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(lo_, attr, False)
GLOW_GROUP = {'Glow_Fluor': 'booth', 'Glow_Bulk_Door': 'power'}
glow_objs = [o for o in bpy.data.objects if o.name.startswith('Glow_')]
glow_mats = {m for o in glow_objs for m in o.data.materials}
crt = bpy.data.materials.get('M_Kpp_Lamp_Crt')
print('lamps', len(lights))

# mist for the night views
fme = bpy.data.meshes.new('FogVolume')
x0_, x1_, y0_, y1_, z0_, z1_ = -60, 60, -90.0, 60.0, -9.0, 14.0
fme.from_pydata([(x0_, y0_, z0_), (x1_, y0_, z0_), (x1_, y1_, z0_), (x0_, y1_, z0_), (x0_, y0_, z1_), (x1_, y0_, z1_),
                 (x1_, y1_, z1_), (x0_, y1_, z1_)], [],
                [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
fog = prop(bpy.data.objects.new('FogVolume', fme))
sc.collection.objects.link(fog)
fmat = bpy.data.materials.new('M_FogVolume')
fmat.use_nodes = True
FN = fmat.node_tree.nodes
for n_ in list(FN):
    if n_.type == 'BSDF_PRINCIPLED':
        FN.remove(n_)
fout = next(n_ for n_ in FN if n_.type == 'OUTPUT_MATERIAL')
vs1, vs2 = FN.new('ShaderNodeVolumeScatter'), FN.new('ShaderNodeVolumeScatter')
vs1.inputs['Anisotropy'].default_value, vs2.inputs['Anisotropy'].default_value = 0.72, 0.25
vadd = FN.new('ShaderNodeAddShader')
fmat.node_tree.links.new(vs1.outputs[0], vadd.inputs[0])
fmat.node_tree.links.new(vs2.outputs[0], vadd.inputs[1])
fmat.node_tree.links.new(vadd.outputs[0], fout.inputs['Volume'])
fme.materials.append(fmat)


def set_atmosphere(a):
    fog.hide_render = a <= 0
    sig = 0.034 * a
    vs1.inputs['Density'].default_value, vs2.inputs['Density'].default_value = 0.8 * sig, 0.2 * sig


# presentation fill for the inside / close-up views (an area light standing in for daylight through the windows)
fill = prop(bpy.data.objects.new('L_fill', bpy.data.lights.new('L_fill', 'AREA')))
sc.collection.objects.link(fill)
fill.data.shape = 'DISK'
fill.data.color = (1.0, 0.96, 0.90)
FILLS = {   # view: (location, target, energy W, size m)
    'int_day': ((0.2, -0.6, 2.45), (0.0, 0.2, 0.6), 90, 1.6),
    'int_back': ((0.4, -0.4, 2.45), (-0.4, 0.9, 1.0), 90, 1.6),
    'int_keys': ((-0.5, 0.6, 2.30), (-0.5, 1.4, 1.8), 30, 0.8),
    'int_desk': ((0.9, -0.2, 2.30), (1.6, -0.6, 0.9), 40, 1.0),
    'old_in_a': ((0.0, 0.0, 2.40), (0.0, 0.0, 0.0), 120, 1.8),
    'old_in_b': ((0.0, 0.0, 2.40), (0.0, 0.0, 0.0), 120, 1.8),
}
plan_light = prop(bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA')))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 4.0, 3.0
plan_light.data.energy = 260
plan_light.location = (0, 0, 2.55)

# poses from the contract
REST = {k: bpy.data.objects[k].matrix_basis.copy() for k in CON['parts'] if k in bpy.data.objects}


def reset_parts():
    for k, mb in REST.items():
        bpy.data.objects[k].matrix_basis = mb


def pose(name, val):
    p_ = CON['parts'][name]
    ob, mb = bpy.data.objects[name], REST[name]
    ax = Vector(p_['axis']).normalized()
    pm = ob.parent.matrix_world.to_3x3().inverted() if ob.parent else Matrix.Identity(3)
    ax = (pm @ ax).normalized()
    t = mb.to_translation()
    if p_.get('unit') == 'm':
        ob.matrix_basis = Matrix.Translation(ax * val) @ mb
    else:
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-t) @ mb


DOOR_OPEN = [('IX_BoothDoor_74', 95)]
POSES = {'ext_back': DOOR_OPEN, 'ext_power': DOOR_OPEN, 'int_day': [('IX_BoothWindow_302', 0.54)],
         'int_keys': [('IX_KeyBoxDoor_303', 110)], 'int_desk': [('IX_BoothWindow_302', 0.54), ('IX_Drawer_76', 0.30)],
         'barrier_up': [('IX_BarrierArm_82', 80)], 'gate_open': [('IX_Gate_81', 6.6)],
         'int_back': [('IX_Drawer_78', 0.40)]}
KIND_COL = {'hand': (1.0, 0.85, 0.1), 'item_slot': (0.2, 0.9, 0.3), 'audio': (0.9, 0.2, 0.9), 'vfx': (1.0, 0.45, 0.1),
            'hide': (0.1, 0.9, 0.9), 'knock': (0.95, 0.15, 0.15), 'seat': (0.6, 0.4, 1.0)}
markers, kmats = [], {}
for k_, col_ in KIND_COL.items():
    m_ = bpy.data.materials.new('mk_' + k_)
    m_.use_nodes = True
    pb_ = m_.node_tree.nodes['Principled BSDF']
    pb_.inputs['Base Color'].default_value = (*col_, 1)
    pb_.inputs['Emission Color'].default_value = (*col_, 1)
    pb_.inputs['Emission Strength'].default_value = 1.5
    kmats[k_] = m_
for name_, s_ in CON['sockets'].items():
    if s_['kind'] not in kmats:
        continue
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.035, location=s_['pos'])
    o_ = bpy.context.object
    o_.data.materials.append(kmats[s_['kind']])
    o_.hide_render = True
    markers.append(prop(o_))
COLS = [o for o in bpy.data.objects if o.name.startswith('COL_')]
colm = bpy.data.materials.new('M_col')
colm.use_nodes = True
_pb = colm.node_tree.nodes['Principled BSDF']
_pb.inputs['Base Color'].default_value = (0.1, 0.8, 1.0, 1)
_pb.inputs['Alpha'].default_value = 0.30
try:
    colm.surface_render_method = 'BLENDED'
except Exception:
    pass
for o_ in COLS:
    o_.data.materials.clear()
    o_.data.materials.append(colm)

NIGHT = {'ext_night', 'ext_power', 'int_night', 'game_kpp'}
GROUPS = {'ext_night': {'booth'}, 'ext_power': {'booth', 'power'}, 'int_night': {'booth'}, 'game_kpp': {'booth'}}
ATMOS = {'ext_night': 0.5, 'ext_power': 0.45, 'game_kpp': 0.35}
EXPOSURE = {'int_day': 0.4, 'int_back': 0.4, 'int_keys': 0.3, 'int_desk': 0.3, 'ext_night': 1.2, 'ext_power': 0.8, 'int_night': 0.0,
            'old_in_a': 0.3, 'old_in_b': 0.3, 'game_kpp': 2.6}
BLOOM = {'ext_night': 0.35, 'ext_power': 0.35, 'int_night': 0.2, 'game_kpp': 0.45}
emit_mats = [m for m in bpy.data.materials if m.get('night_emit') is not None and not m.name.startswith('M_LensFX')]


def eye(x, y, h=1.65):
    return (x, y, ground_z(x, y) + h)


CAMS = {   # booth frame: x toward the road, y toward the back; the old views = the Update 3 renders' cameras
    'ext_day': (eye(12.5, -16.0), (3.6, -2.2, 1.2), 26, None),
    'ext_booth': (eye(5.4, -6.6), (0.3, -0.6, 1.45), 24, None),
    'ext_back': (eye(-4.4, 7.0), (0.5, 0.9, 1.3), 24, None),
    'ext_left': (eye(-7.4, -2.6), (-0.9, 0.2, 1.4), 24, None),
    'ext_night': (eye(12.5, -16.0), (3.0, -1.6, 1.5), 26, None),
    'ext_power': (eye(7.5, 7.5), (0.6, 0.6, 1.5), 24, None),
    'barrier': (eye(6.9, -9.6, 1.45), (8.75, -7.0, 0.70), 30, None),
    'barrier_up': (eye(10.5, -15.5), (5.2, -6.6, 2.4), 26, None),
    'gate': (eye(6.8, -6.4), (7.2, 0.2, 0.9), 22, None),
    'gate_open': (eye(3.0, 7.5), (12.5, 0.2, 0.9), 22, None),
    'int_day': ((1.0, 1.25, 1.77), (0.1, -1.3, 1.15), 15, None),
    'int_back': ((-1.45, -0.80, 1.75), (0.2, 1.45, 1.40), 15, None),
    'int_keys': ((-0.62, 0.62, 1.78), (-0.48, 1.47, 1.82), 28, None),
    'int_desk': ((0.40, 0.25, 1.55), (1.75, -0.70, 1.0), 18, None),
    'int_night': ((1.0, 1.25, 1.77), (0.1, -1.3, 1.25), 15, None),
    'plan': ((0.0, 0.0, 12.0), (0.0, 0.0001, 0.0), 30, 7.0),
    'points_plan': ((0.0, 0.0, 12.0), (0.0, 0.0001, 0.0), 30, 7.0),
    'colliders_plan': ((0.0, 0.0, 12.0), (0.0, 0.0001, 0.0), 30, 7.0),
    'site_plan': ((6.5, -3.0, 40.0), (6.5, -2.9999, 0.0), 30, 27.0),
    'old_front': ((0.5, -11.0, 2.6), (0.0, 0.0, 1.4), 30, None),
    'old_back': ((-0.5, 11.0, 2.6), (0.0, 0.0, 1.4), 30, None),
    'old_left': ((-11.0, -0.6, 2.4), (0.0, 0.0, 1.4), 30, None),
    'old_right': ((11.0, -0.6, 2.4), (0.0, 0.0, 1.4), 30, None),
    'old_iso': ((-9.0, -12.0, 7.0), (2.0, -2.0, 1.0), 30, None),
    'old_barrier': ((6.0, -16.0, 3.0), (5.0, -6.0, 1.0), 30, None),
    'old_gate': ((11.0, -14.0, 3.5), (8.0, 0.0, 1.2), 30, None),
    'old_in_a': ((-1.2, -0.9, 1.6), (1.5, 0.8, 1.0), 14, None),
    'old_in_b': ((1.2, 0.9, 1.6), (-1.5, -0.6, 1.2), 14, None),
    'game_kpp': ((33.069, -73.292, -4.183), (6.96, 1.057, 1.404), 35.983, None),     # the map's KPP viewpoint (vertical fov)
}


def state(view):
    reset_parts()
    night = view in NIGHT
    on = GROUPS.get(view, set())
    for l in lights:
        l.hide_render = not (night and l['group'] in on)
    for lev_, grp_ in lens_levels:
        lev_.outputs[0].default_value = 1.0 if (night and grp_ in on) else 0.0
    for o in glow_objs:
        o.hide_render = not (night and GLOW_GROUP.get(o.name, '') in on)
    for m in glow_mats:
        em = next(n for n in m.node_tree.nodes if n.type == 'EMISSION')
        em.inputs['Strength'].default_value = 2.0
    set_atmosphere(ATMOS.get(view, 0.0))
    for k_, v_ in POSES.get(view, []):
        if k_ in REST:
            pose(k_, v_)
    for o in markers:
        o.hide_render = view != 'points_plan'
    for o in COLS:
        o.hide_render = view != 'colliders_plan' or o.name.startswith(('COL_Roof', 'COL_Pad'))
    plan_light.hide_render = view not in ('plan', 'points_plan', 'colliders_plan')
    fill.hide_render = view not in FILLS
    if view in FILLS:
        fl_, ft_, fe_, fs_ = FILLS[view]
        fill.location = fl_
        fill.rotation_euler = (Vector(ft_) - Vector(fl_)).to_track_quat('-Z', 'Y').to_euler()
        fill.data.energy, fill.data.size = fe_, fs_
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith(('Sun', 'Moon'))]:
        bpy.data.objects.remove(o, do_unlink=True)
    if night:
        P.world((0.008, 0.011, 0.022), 1.0)
        m = P.sun(0.10, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    elif view.startswith(('int_', 'old_in')) or view in ('plan', 'points_plan', 'colliders_plan'):
        P.world((0.30, 0.34, 0.40), 0.35)
        P.sun(1.2, (52, 0, -150))
    else:
        P.world((0.50, 0.56, 0.64), 0.8)
        P.sun(2.6, (50, 0, -150 if view not in ('ext_back', 'gate_open', 'ext_power') else 30), (1.0, 0.94, 0.84))
    for m in emit_mats:
        pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if pb is not None:
            pb.inputs['Emission Strength'].default_value = 0.0
    if crt is not None:
        pbc = next(n for n in crt.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pbc.inputs['Emission Strength'].default_value = 1.6 if (night and 'power' in on) else 0.0
    inner = view.startswith(('int_', 'old_in')) or view in ('plan', 'points_plan', 'colliders_plan')
    trees.hide_render = inner or view == 'site_plan'
    cam_, tgt_ = Vector(CAMS[view][0][:2]), Vector(CAMS[view][1][:2])
    seg = tgt_ - cam_
    for t in trees.objects:                                      # no tree in the line of sight (to the target and 3 m on)
        p_ = t.location.xy
        u_ = max(0.0, min(1.0 + 3.0 / max(seg.length, 1e-6), (p_ - cam_).dot(seg) / max(seg.length_squared, 1e-9)))
        t.hide_render = trees.hide_render or (view != 'game_kpp' and (p_ - cam_ - seg * u_).length < 2.2)
    g.hide_render = view in ('plan', 'points_plan', 'colliders_plan')
    fence.hide_render = view in ('plan', 'points_plan', 'colliders_plan')


P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
sc.cycles.transparent_max_bounces = 24
ims = sc.render.image_settings
for v in views:
    state(v)
    loc, tgt, lens, ortho = CAMS[v]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    old = v.startswith('old_')
    sc.render.resolution_x, sc.render.resolution_y = (900, 630) if old else (900, 600)
    if v.startswith('game_'):                                    # Unity camera: vertical field of view, 1280 x 720
        sc.camera.data.sensor_fit = 'VERTICAL'
        sc.camera.data.angle = math.radians(lens)
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    if v in ('plan', 'points_plan', 'colliders_plan'):
        sc.camera.data.clip_start = 12.0 - 2.42
    elif v == 'site_plan':
        sc.camera.data.clip_start = 1.0
    else:
        sc.camera.data.clip_start = 0.02
    sc.camera.data.clip_end = 400.0
    sc.cycles.samples = spp * (2 if v.startswith('int_') else 1)
    if v in NIGHT:
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format, ims.color_depth = 'OPEN_EXR', '32'
        ims.color_management = 'OVERRIDE'
        ims.linear_colorspace_settings.name = 'Linear Rec.709'
        sc.view_settings.exposure = 0.0
        exr = os.path.join(OUT, v + '.exr')
        P.render(exr)
        subprocess.run([sys.executable, '-I', os.path.join(P.HERE, 'post_bloom.py'), exr, os.path.join(OUT, v + '.png'),
                        str(BLOOM.get(v, 0.3)), str(EXPOSURE.get(v, 0.0))], check=True)
        os.remove(exr)
    else:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.view_settings.exposure = EXPOSURE.get(v, 0.0)
        P.render(os.path.join(OUT, v + '.png'))
print('rendered', views)
