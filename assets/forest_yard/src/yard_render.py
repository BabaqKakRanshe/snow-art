"""Preview renders of the station yard (out/yard.blend posed from out/yard_contract.json) in its Update 3 surroundings: the
map's terrain, road, paved yard and power wires cut out round the tanks (site/fuel_site.blend from Forest_Terrain.fbx /
Forest_Wires.fbx), the trees (Forest_Layout.json, cone proxies), the map's chain-link fence (FenceChain at its places), the
generator container (out/cont.blend at the GenContainer's place), the power and light poles (Update 3 meshes).
Views: the yard by day and at night, the bund's front with the pump, the pump close, the lever swung, the fill point, the
back, the stile side, inside the bund, from above, the transformer (gate side, gate open, the pole, the back), the torch
at the pump (as Update 3's TanksPump), through the transformer's fence (as Update 3's TanksWide), plans (the tanks, the
transformer, the points, the colliders, the site).  --u3: the same cameras on the Update 3 models (rend/yard_u3).
python3 -I yard_render.py <views> [spp] [--draft] [--u3]  -> rend/yard/<view>.png"""
import sys, os, math, json, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P

views = sys.argv[1].split(',')
spp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 48
DRAFT = '--draft' in sys.argv
U3MODE = '--u3' in sys.argv
sfx = '_draft' if DRAFT else ''
OUT = os.path.join(P.HERE, 'rend', 'yard_u3' if U3MODE else 'yard' + sfx)
os.makedirs(OUT, exist_ok=True)
FOREST = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/'
SITE = json.load(open(os.path.join(P.HERE, 'site', 'fuel_site.json')))
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'yard{sfx}.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', f'yard_contract{sfx}.json')))
TP, TY = Vector((8.0, -10.0, -0.044)), -90.0                       # the Trafo in the FuelTanks frame (yard_kit.TRAFO_PLACE)
MT = Matrix.Translation(TP) @ Matrix.Rotation(math.radians(TY), 4, 'Z')


def t2f(p):
    return tuple(MT @ Vector(p))


def prop(o):
    o['scene_prop'] = 1
    return o


def flat_mat(name, rgb, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    pb = m.node_tree.nodes['Principled BSDF']
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    return m


# ------------------------------------------------------------------ the map round the yard
with bpy.data.libraries.load(os.path.join(P.HERE, 'site', 'fuel_site.blend'), link=False) as (src, dst):
    dst.objects = list(src.objects)
site_objs = []
m_ground = bpy.data.materials.new('ground')
m_ground.use_nodes = True
gnt = m_ground.node_tree
gpb = gnt.nodes['Principled BSDF']
gpb.inputs['Roughness'].default_value = 0.95
noi = gnt.nodes.new('ShaderNodeTexNoise')
noi.inputs['Scale'].default_value = 0.8
ramp = gnt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.050, 0.044, 0.028, 1)
ramp.color_ramp.elements[1].color = (0.10, 0.10, 0.052, 1)
gnt.links.new(noi.outputs['Fac'], ramp.inputs['Fac'])
gnt.links.new(ramp.outputs['Color'], gpb.inputs['Base Color'])
m_road = flat_mat('road', (0.045, 0.043, 0.040))
m_paved = flat_mat('paved', (0.085, 0.083, 0.078))
m_wire = flat_mat('wire', (0.02, 0.02, 0.02), 0.6)
for o in dst.objects:
    if o is None:
        continue
    sc.collection.objects.link(o)
    kind = o.get('site', 'terrain')
    o.data.materials.clear()
    o.data.materials.append(m_wire if kind == 'wires' else m_road if kind == 'road' else
                           m_paved if 'Paved' in o.name else m_ground)
    if kind == 'terrain' and 'Paved' not in o.name:
        o.location.z -= 0.004
    site_objs.append(prop(o))
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark, trunk = flat_mat('spruce', (0.018, 0.034, 0.024)), flat_mat('trunk', (0.06, 0.045, 0.035))
for t in SITE['trees']:
    nm = t['m']
    if nm.startswith(('Weeds', 'Fern', 'Bush', 'Grass')):
        continue
    try:
        h = float(''.join(ch for ch in nm.split('_')[1] if ch.isdigit())) * t['s']
    except (ValueError, IndexError):
        h = 12.0 * t['s']
    x, y, z0 = t['p']
    if not nm.startswith('Dead'):
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.17, depth=h * 0.82, location=(x, y, z0 + h * 0.18 + h * 0.41))
        o_ = bpy.context.object
        o_.data.materials.append(dark)
        for c in o_.users_collection:
            c.objects.unlink(o_)
        trees.objects.link(prop(o_))
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=max(0.08, h * 0.012), depth=h * 0.3, location=(x, y, z0 + h * 0.15))
    o_ = bpy.context.object
    o_.data.materials.append(trunk)
    for c in o_.users_collection:
        c.objects.unlink(o_)
    trees.objects.link(prop(o_))
fence = bpy.data.collections.new('Fence')
sc.collection.children.link(fence)
chain = bpy.data.materials.get('M_Yard_ChainLink')
steel = flat_mat('fence_steel', (0.30, 0.31, 0.30), 0.6)
for r in SITE['rocks']:
    if r['m'] != 'FenceChain':
        continue
    x, y, z0 = r['p']
    a = math.radians(r['yaw'])
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
    for loc, rot, rad, dep in (((x - 1.5 * ux, y - 1.5 * uy, z0 + 1.15), (0, 0, 0), 0.03, 2.5),
                               ((x, y, z0 + 2.0), (0, math.pi / 2, a), 0.018, 3.0)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=rad, depth=dep, location=loc, rotation=rot)
        po = bpy.context.object
        po.data.materials.append(steel)
        for c in po.users_collection:
            c.objects.unlink(po)
        fence.objects.link(prop(po))
# the generator container (our package) and the Update 3 poles at their places
neighbours = bpy.data.collections.new('Neighbours')
sc.collection.children.link(neighbours)
gc = next((p for p in SITE['prefabs'] if p['m'] == 'GenContainer'), None)
if gc is not None and os.path.exists(os.path.join(P.HERE, 'out', 'cont.blend')):
    with bpy.data.libraries.load(os.path.join(P.HERE, 'out', 'cont.blend'), link=False) as (src, dst2):
        dst2.objects = [n for n in src.objects if not n.startswith(('COL_', 'LIGHT_'))]
    M = Matrix.Translation(Vector(gc['p'])) @ Matrix.Rotation(math.radians(gc['yaw'] - 90.0), 4, 'Z')
    for o in dst2.objects:
        if o is None:
            continue
        neighbours.objects.link(prop(o))
    bpy.context.view_layer.update()
    for o in dst2.objects:
        if o is not None and o.parent is None:
            o.matrix_world = M @ o.matrix_world
        if o is not None and o.name.startswith('Glow_'):
            o.hide_render = True
U3COL = {'Concrete': (0.45, 0.45, 0.43), 'ConcreteDark': (0.25, 0.25, 0.24), 'YellowMetal': (0.75, 0.6, 0.05),
         'SteelDark': (0.08, 0.08, 0.08), 'Galvanized': (0.5, 0.52, 0.52), 'Brass': (0.7, 0.55, 0.2), 'RedMetal': (0.7, 0.05, 0.04),
         'PaintWhite': (0.85, 0.85, 0.85), 'Rubber': (0.05, 0.05, 0.05), 'StoveIron': (0.1, 0.1, 0.1), 'Steel': (0.45, 0.46, 0.46),
         'ObsSigns': (0.75, 0.15, 0.12), 'PumpGreen': (0.15, 0.35, 0.15), 'Safety': (0.9, 0.75, 0.1), 'StripeOlive': (0.35, 0.37, 0.2),
         'Enamel': (0.85, 0.85, 0.8), 'MetalGrey': (0.4, 0.41, 0.41), 'RackGrey': (0.55, 0.56, 0.55), 'WoodPole': (0.3, 0.22, 0.14),
         'TankU3': (0.62, 0.60, 0.52), 'Grating': (0.5, 0.52, 0.52), 'Wood': (0.30, 0.22, 0.14), 'Lamp': (0.8, 0.8, 0.7)}


def import_u3(name, M):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=FOREST + 'Models/' + name + '.fbx')
    new = [o for o in set(bpy.data.objects) - before]
    for o in new:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
        for s in o.material_slots:
            m = s.material
            if m is None or m.get('u3_done'):
                continue
            if 'ChainLink' in m.name:
                s.material = chain
                continue
            col = next((c for k, c in sorted(U3COL.items(), key=lambda kv: -len(kv[0])) if k in m.name), (0.5, 0.3, 0.6))
            m.use_nodes = True
            pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            for l in list(pb.inputs['Base Color'].links):
                m.node_tree.links.remove(l)
            pb.inputs['Base Color'].default_value = (*col, 1)
            if 'Alpha' in pb.inputs:
                for l in list(pb.inputs['Alpha'].links):
                    m.node_tree.links.remove(l)
                pb.inputs['Alpha'].default_value = 1.0
            m['u3_done'] = 1
    return new


for p in SITE['prefabs']:
    if p['m'] in ('PowerPole', 'LightPole'):
        M = Matrix.Translation(Vector(p['p'])) @ Matrix.Rotation(math.radians(p['yaw']), 4, 'Z')
        for o in import_u3(p['m'], M):
            for c in o.users_collection:
                c.objects.unlink(o)
            neighbours.objects.link(prop(o))
yard_meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name in CON['parts']]
if U3MODE:                                                         # the Update 3 models in place of ours
    for o in yard_meshes:
        o.hide_render = True
    import_u3('FuelTanks', Matrix.Identity(4))
    U3GATE = [o for o in import_u3('Trafo', MT) if o.name.startswith('IX_TrafoGate_91')]
    bpy.context.view_layer.update()
    U3GATE_M = {o.name: o.matrix_world.copy() for o in U3GATE}

# ------------------------------------------------------------------ fog, fills, poses, markers, colliders
fme = bpy.data.meshes.new('FogVolume')
x0_, x1_, y0_, y1_, z0_, z1_ = -70, 70, -70.0, 70.0, -6.0, 18.0
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


torch = prop(bpy.data.objects.new('L_torch', bpy.data.lights.new('L_torch', 'SPOT')))
sc.collection.objects.link(torch)
torch.data.spot_size = math.radians(34)
torch.data.spot_blend = 0.45
torch.data.energy = 60
torch.data.color = (1.0, 0.92, 0.80)
torch.data.shadow_soft_size = 0.02
plan_light = prop(bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA')))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 10.0, 9.0
plan_light.data.energy = 900
REST = {k: bpy.data.objects[k].matrix_basis.copy() for k in CON['parts'] if k in bpy.data.objects}


def reset_parts():
    for k, mb in REST.items():
        bpy.data.objects[k].matrix_basis = mb


def pose(name, val):
    p_ = CON['parts'][name]
    ob, mb = bpy.data.objects[name], REST[name]
    ax = Vector(p_['axis']).normalized()                             # the root frame's axis = the parent's local axis here
    t = mb.to_translation()
    if p_.get('unit') == 'm':
        ob.matrix_basis = Matrix.Translation(ax * val) @ mb
    else:
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-t) @ mb


POSES = {'pump_lever': [('IX_PumpLever_301', 45)], 'trafo_open': [('IX_TrafoGate_91', 100)],
         'night_torch': [('IX_PumpLever_301', -30)]}
KIND_COL = {'hand': (1.0, 0.85, 0.1), 'item_slot': (0.2, 0.9, 0.3), 'audio': (0.9, 0.2, 0.9), 'vfx': (1.0, 0.45, 0.1),
            'hide': (0.1, 0.9, 0.9), 'knock': (0.95, 0.15, 0.15), 'stand': (0.6, 0.4, 1.0)}
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
    pos = s_['pos'] if s_['root'] == 'FuelTanks' else t2f(s_['pos'])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.06, location=pos)
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


def eye(x, y, h=1.65):
    return (x, y, h)


def teye(x, y, h=1.65):
    return t2f((x, y, h - 0.0))


CAMS = {   # FuelTanks frame (the Trafo's own views via t2f): location, target, lens, ortho scale, ortho rotation z
    'yard_day': (eye(2.0, -18.5, 1.75), (1.2, -4.0, 1.3), 22, None),
    'tanks_front': (eye(-0.4, -9.8), (-0.4, -1.8, 1.25), 24, None),
    'pump': ((-0.55, -5.95, 1.50), (-1.35, -4.30, 0.80), 30, None),
    'pump_lever': ((-0.55, -5.95, 1.50), (-1.35, -4.30, 0.95), 30, None),
    'fill_point': ((-2.55, -5.25, 1.30), (-3.35, -3.75, 0.72), 28, None),
    'tanks_back': (eye(6.2, 8.8), (0.4, 1.4, 1.4), 24, None),
    'tanks_right': (eye(8.8, -5.6), (2.4, -1.6, 1.4), 24, None),
    'bund_inside': ((3.62, -0.25, 1.70), (-3.5, 0.05, 0.85), 17, None),
    'tanks_top': ((-7.5, -9.5, 7.8), (0.0, -0.4, 1.4), 26, None),
    'trafo_front': (teye(-0.9, -7.6), t2f((0.0, 0.2, 1.35)), 24, None),
    'trafo_open': (teye(-1.4, -4.6), t2f((-0.3, 0.7, 1.05)), 22, None),
    'trafo_pole': (teye(3.6, -0.6, 1.6), t2f((0.0, 2.0, 6.7)), 30, None),
    'trafo_back': (teye(2.9, 7.0), t2f((0.0, 0.6, 2.4)), 24, None),
    'night': (eye(2.0, -18.5, 1.75), (1.2, -4.0, 1.3), 22, None),
    'night_torch': ((-1.25, -6.15, 1.62), (-1.15, -3.2, 1.25), 26, None),
    'game_tanks_wide': (teye(-2.05, -1.35, 1.7), (0.6, -0.4, 1.6), 24, None),
    'plan_tanks': ((0.0, -0.6, 14.0), (0.0, -0.5999, 0.0), 30, 10.6, 0.0),
    'points_tanks': ((0.0, -0.6, 14.0), (0.0, -0.5999, 0.0), 30, 10.6, 0.0),
    'colliders_tanks': ((0.0, -0.6, 14.0), (0.0, -0.5999, 0.0), 30, 10.6, 0.0),
    'plan_trafo': (t2f((0.0, 0.0, 14.0)), t2f((0.0, 0.0001, 0.0)), 30, 6.4, TY),
    'points_trafo': (t2f((0.0, 0.0, 14.0)), t2f((0.0, 0.0001, 0.0)), 30, 6.4, TY),
    'colliders_trafo': (t2f((0.0, 0.0, 14.0)), t2f((0.0, 0.0001, 0.0)), 30, 6.4, TY),
    'site_plan': ((1.0, -6.0, 40.0), (1.0, -5.9999, 0.0), 30, 30.0, 0.0),
}
NIGHT = {'night', 'night_torch', 'game_tanks_wide'}
ATMOS = {'night': 0.5, 'night_torch': 0.25, 'game_tanks_wide': 0.35}
EXPOSURE = {'night': 1.4, 'night_torch': 0.6, 'game_tanks_wide': 1.6, 'bund_inside': 0.2}
BLOOM = {'night': 0.3, 'night_torch': 0.25, 'game_tanks_wide': 0.3}
PLANS = ('plan_tanks', 'points_tanks', 'colliders_tanks', 'plan_trafo', 'points_trafo', 'colliders_trafo')


def state(view):
    reset_parts()
    if U3MODE:                                                     # the Update 3 gate swings the same way as ours
        for o in U3GATE:
            m0 = U3GATE_M[o.name]
            if view == 'trafo_open':
                t = m0.translation
                o.matrix_world = Matrix.Translation(t) @ Matrix.Rotation(math.radians(-100), 4, 'Z') @ Matrix.Translation(-t) @ m0
            else:
                o.matrix_world = m0
    night = view in NIGHT
    set_atmosphere(ATMOS.get(view, 0.0))
    for k_, v_ in POSES.get(view, []):
        if k_ in REST:
            pose(k_, v_)
    for o in markers:
        o.hide_render = not view.startswith('points_')
    for o in COLS:
        o.hide_render = not view.startswith('colliders_') or o.name.startswith(('COL_Bund_Slab', 'COL_Trafo_Pad'))
    plan_light.hide_render = view not in PLANS
    if view in PLANS:
        loc = CAMS[view][0]
        plan_light.location = (loc[0], loc[1], 5.0)
    torch.hide_render = view != 'night_torch'
    if view == 'night_torch':
        loc, tgt = Vector(CAMS[view][0]), Vector(CAMS[view][1])
        torch.location = loc + Vector((0.18, 0.0, -0.25))
        torch.rotation_euler = (tgt - torch.location).to_track_quat('-Z', 'Y').to_euler()
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith(('Sun', 'Moon'))]:
        bpy.data.objects.remove(o, do_unlink=True)
    if night:
        P.world((0.008, 0.011, 0.022), 1.0)
        m = P.sun(0.10, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    elif view in PLANS:
        P.world((0.30, 0.34, 0.40), 0.5)
        P.sun(1.6, (52, 0, -150))
    else:
        P.world((0.50, 0.56, 0.64), 0.8)
        P.sun(2.6, (50, 0, -150 if view not in ('tanks_back', 'trafo_back') else 30), (1.0, 0.94, 0.84))
    plan = view in PLANS
    trees.hide_render = plan or view == 'site_plan'
    cam_, tgt_ = Vector(CAMS[view][0][:2]), Vector(CAMS[view][1][:2])
    seg = tgt_ - cam_
    for t in trees.objects:                                      # no tree in the line of sight
        p_ = t.location.xy
        u_ = max(0.0, min(1.0 + 3.0 / max(seg.length, 1e-6), (p_ - cam_).dot(seg) / max(seg.length_squared, 1e-9)))
        t.hide_render = trees.hide_render or (p_ - cam_ - seg * u_).length < 2.2
    for o in site_objs:
        o.hide_render = plan and o.get('site') != 'terrain'
    fence.hide_render = plan
    neighbours.hide_render = plan


P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
sc.cycles.transparent_max_bounces = 24
ims = sc.render.image_settings
for v in views:
    state(v)
    cv = CAMS[v]
    loc, tgt, lens, ortho = cv[:4]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    if ortho:
        sc.camera.rotation_euler = (0.0, 0.0, math.radians(cv[4]))
        sc.camera.data.clip_start = 1.0
    else:
        sc.camera.data.clip_start = 0.02
    sc.camera.data.clip_end = 400.0
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
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
