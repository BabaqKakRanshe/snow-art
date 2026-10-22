"""Preview renders of the generator container (out/cont.blend posed from out/cont_contract.json): exterior day / night /
snow, the front end with the louvre and the stack, the doors open, inside from the doors at night and by day, the north
half, close-ups of the control panel, the switchboard, the day tank, the drums, the engine's service side and the
radiator; plan views with the points and colliders.
python3 -I cont_render.py <views> [spp]  -> rend/cont/<view>.png"""
import sys, os, math, json, random, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P
import gen_lights as GL

views = sys.argv[1].split(',')
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 48
OUT = os.path.join(P.HERE, 'rend', 'cont')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', 'cont.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', 'cont_contract.json')))


def prop(o):
    o['scene_prop'] = 1
    return o


# ground (snow), trees for the night views
g = prop(P.ground(color=(0.82, 0.84, 0.88)))
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark = bpy.data.materials.new('spruce')
dark.use_nodes = True
dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.035, 0.03, 1)
r = random.Random(7)
for i in range(60):
    a = r.uniform(0, 2 * math.pi)
    d = r.uniform(12, 45)
    x, y = d * math.cos(a), d * math.sin(a)
    h = r.uniform(7, 14)
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.22, depth=h, location=(x, y, h / 2))
    t = bpy.context.object
    t.data.materials.append(dark)
    for c in t.users_collection:
        c.objects.unlink(t)
    trees.objects.link(t)
    prop(t)

# lamps: IES point lights + lens glow (the van / plane method)
LM = GL.meta()
IESDIR = os.path.join(P.HERE, 'tex', 'cont', 'IES')
ies_txt = {}
for t_ in GL.TYPES:
    tx = bpy.data.texts.new('IES_%s.ies' % t_)
    tx.from_string(open(os.path.join(IESDIR, t_ + '.ies')).read())
    ies_txt[t_] = tx


def lamp_axes(e):
    d = Vector(e['dir']).normalized()
    up = Vector(e['up'])
    up = (up - d * up.dot(d)).normalized()
    zl = -d
    return up.cross(zl).normalized(), up, zl


def ies_chain(nt, t_, vec):
    ies = nt.nodes.new('ShaderNodeTexIES')
    ies.mode = 'INTERNAL'
    ies.ies = ies_txt[t_]
    nt.links.new(vec, ies.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeMath')
    nm.operation = 'MULTIPLY'
    nm.inputs[1].default_value = LM[t_]['k_norm']
    nt.links.new(ies.outputs['Fac'], nm.inputs[0])
    return nm.outputs[0]


def proj_area(ob, d):
    a = 0.0
    M3 = ob.matrix_world.to_3x3()
    for p_ in ob.data.polygons:
        a += p_.area * max(0.0, (M3 @ p_.normal).normalized().dot(d))
    return max(a, 1e-5)


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
    N_, Lk = mat.node_tree.nodes, mat.node_tree.links
    pb = next(n for n in N_ if n.type == 'BSDF_PRINCIPLED')
    geo = N_.new('ShaderNodeNewGeometry')
    cxyz = N_.new('ShaderNodeCombineXYZ')
    for i_, ax_ in enumerate((xl, yl, zl)):
        dp = N_.new('ShaderNodeVectorMath')
        dp.operation = 'DOT_PRODUCT'
        Lk.new(geo.outputs['Incoming'], dp.inputs[0])
        dp.inputs[1].default_value = tuple(ax_)
        Lk.new(dp.outputs['Value'], cxyz.inputs[i_])
    f_ = ies_chain(mat.node_tree, t_, cxyz.outputs[0])
    fl_ = LM[t_]['lens_floor']
    fm = N_.new('ShaderNodeMath')
    fm.operation = 'MULTIPLY_ADD'
    Lk.new(f_, fm.inputs[0])
    fm.inputs[1].default_value, fm.inputs[2].default_value = 1.0 - fl_, fl_
    gain = math.pi * e['intensity_urp'] / proj_area(lo_, Vector(e['dir']).normalized())
    lev = N_.new('ShaderNodeValue')
    lev.outputs[0].default_value = 0.0
    g1 = N_.new('ShaderNodeMath')
    g1.operation = 'MULTIPLY'
    Lk.new(fm.outputs[0], g1.inputs[0])
    g1.inputs[1].default_value = gain
    g2 = N_.new('ShaderNodeMath')
    g2.operation = 'MULTIPLY'
    Lk.new(g1.outputs[0], g2.inputs[0])
    Lk.new(lev.outputs[0], g2.inputs[1])
    cap = N_.new('ShaderNodeMath')
    cap.operation = 'MINIMUM'
    Lk.new(g2.outputs[0], cap.inputs[0])
    cap.inputs[1].default_value = 40.0
    Lk.new(cap.outputs[0], pb.inputs['Emission Strength'])
    lens_levels.append((lev, e['group']))
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(lo_, attr, False)
print('lamps', len(lights))

# fog for the night outside views
fme = bpy.data.meshes.new('FogVolume')
x0_, x1_, y0_, y1_, z0_, z1_ = -40, 40, -40.0, 40.0, -0.3, 12.0
fme.from_pydata([(x0_, y0_, z0_), (x1_, y0_, z0_), (x1_, y1_, z0_), (x0_, y1_, z0_), (x0_, y0_, z1_), (x1_, y0_, z1_),
                 (x1_, y1_, z1_), (x0_, y1_, z1_)], [],
                [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
fog = bpy.data.objects.new('FogVolume', fme)
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


# presentation fill for the close-ups (an area light standing in for a torch / work lamp)
fill = bpy.data.objects.new('L_fill', bpy.data.lights.new('L_fill', 'AREA'))
sc.collection.objects.link(fill)
fill.data.shape = 'DISK'
fill.data.color = (1.0, 0.95, 0.88)
FILLS = {   # view: (location, target, energy W, size m)
    'int_panel': ((-0.73, -1.615, 1.96), (-0.04, -1.015, 1.46), 26, 0.6),
    'int_board': ((-0.95, -1.315, 2.16), (-1.45, -2.215, 1.61), 30, 0.6),
    'int_fuel': ((-0.38, 0.765, 2.31), (-0.18, 1.765, 1.51), 30, 0.8),
    'int_service': ((1.67, -2.115, 1.96), (1.37, -1.215, 0.91), 16, 0.7),
    'int_drums': ((1.32, 1.015, 2.26), (2.22, 1.965, 1.11), 40, 0.8),
    'int_radiator': ((1.62, -0.315, 2.26), (1.92, -1.015, 1.06), 30, 0.7),
    'int_north': ((0.4, 0.2, 2.40), (-1.6, 1.6, 0.8), 60, 1.5),
    'int_day': ((0.0, 0.0, 2.55), (0.0, 0.0, 0.0), 160, 2.5),
}
plan_light = bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA'))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 5.6, 4.5
plan_light.data.energy = 520
plan_light.location = (0, 0, 2.40)

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
    if p_['kind'] == 'stretch':
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Scale(val, 4, ax) @ Matrix.Translation(-t) @ mb
    elif p_.get('unit') == 'm':
        ob.matrix_basis = Matrix.Translation(ax * val) @ mb
    else:
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-t) @ mb
    for k_, q_ in CON['parts'].items():                       # parts linked to this one follow it
        if q_.get('links', {}).get('from') == name:
            pose(k_, val * q_['links']['ratio'])


LOUVRE_OPEN = [('Louvre_Lever', 75)]
BARS_R = [('Door_R_Bar_1', 90), ('Door_R_Bar_2', 90)]
BARS_L = [('Door_L_Bar_1', 90), ('Door_L_Bar_2', 90)]
BOARD_ON = [('Board_Changeover', 60), ('Board_Brk_Gen', 60), ('Board_MCB_8', 60), ('Board_MCB_2', 60), ('Gen_Breaker', 60)]
POSES = {
    'ext_east': LOUVRE_OPEN + [('Exhaust_Flap', 35)],
    'ext_night': BARS_R + [('Door_R', 58)],
    'ext_open': BARS_R + BARS_L + [('Door_R', 120), ('Door_L', 105)] + LOUVRE_OPEN,
    'int_door': LOUVRE_OPEN + BOARD_ON + [('Gen_Key', 52), ('DayTank_Valve', 90), ('Light_Switch', 50)],
    'int_day': BARS_R + BARS_L + [('Door_R', 120), ('Door_L', 105)],
    'int_north': [('Light_Switch', 50)],
    'int_panel': [('Gen_Key', 52)],
    'int_board': [('Board_Latch', 90), ('Board_Door', 98), ('Board_Changeover', 60), ('Board_Brk_Gen', 60), ('Board_MCB_1', 60),
                  ('Board_MCB_2', 60), ('Board_MCB_8', 60)],
    'int_fuel': [('DayTank_Valve', 90)],
    'int_drums': [('Drum_1_Vent', 720)],
    'int_service': [('Engine_BleedScrew', 360), ('Engine_PrimerLever', 25), ('Battery_ClampNeg', 0.04)],
    'int_radiator': LOUVRE_OPEN,
}
HIDE_IN = {'ext_night': ['Padlock'], 'ext_open': ['Padlock'], 'int_day': ['Padlock']}
RUN = {'Needle_GenV': 400, 'Needle_GenHz': 50, 'Needle_GenA': 38, 'Needle_Oil': 3.5, 'Needle_Temp': 82, 'Needle_Batt': 13.8,
       'Needle_BoardV': 400, 'Needle_BoardHz': 50, 'Needle_BoardA': 38}
NEEDLES = {'int_door': RUN, 'int_board': RUN, 'int_panel': {'Needle_Batt': 12.4}}
MOVE = {'int_drums': [('Drum_1_Vent', (0.0, 0.06, 0.012))], 'int_service': [('Battery_ClampNeg', (0.0, -0.04, -0.02))]}
SNOW_VIEWS = {'snow'}

# points / colliders overlays for the plan views
KIND_COL = {'hand': (1.0, 0.85, 0.1), 'pour': (0.2, 0.5, 1.0), 'item_slot': (0.2, 0.9, 0.3), 'audio': (0.9, 0.2, 0.9),
            'vfx': (1.0, 0.45, 0.1), 'hide': (0.1, 0.9, 0.9), 'knock': (0.95, 0.15, 0.15), 'heat': (1.0, 0.5, 0.6)}
markers = []
kmats = {}
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

NIGHT = {'ext_night', 'int_door'}
GROUPS = {'ext_night': {'room', 'outd'}, 'int_door': {'room', 'outd'}}
ATMOS = {'ext_night': 0.30}
EXPOSURE = {'int_panel': 0.6, 'int_board': 0.5, 'int_fuel': 0.4, 'int_drums': 0.4, 'int_service': 0.4, 'int_radiator': 0.5,
            'int_day': 0.5, 'int_north': 0.5,
            'ext_night': 0.0, 'int_door': 0.2}
BLOOM = {'ext_night': 0.30, 'int_door': 0.16}
emit_mats = [m for m in bpy.data.materials if m.get('night_emit') is not None]
IND = {}                                                        # indicator lamps: a material each, lit per view
for o in bpy.data.objects:
    if o.name.startswith(('GLamp_', 'BLamp_')):
        m = o.data.materials[0].copy()
        m.name = 'M_Ind_' + o.name
        o.data.materials[0] = m
        IND[o.name] = m
LIT = {'int_panel': {'GLamp_CHG', 'GLamp_OIL'}, 'int_board': {'BLamp_GEN'}, 'int_door': {'GLamp_RUN', 'BLamp_GEN'},
       'int_fuel': {'GLamp_RUN'}}
glass = [m for m in bpy.data.materials if m.name == 'M_GCont_Glass']


def state(view):
    reset_parts()
    night = view in NIGHT
    on = GROUPS.get(view, set())
    for l in lights:
        l.hide_render = not (night and l['group'] in on)
    for lev_, grp_ in lens_levels:
        lev_.outputs[0].default_value = 1.0 if (night and grp_ in on) else 0.0
    set_atmosphere(ATMOS.get(view, 0.0))
    for k_, v_ in POSES.get(view, []):
        if k_ in REST:
            pose(k_, v_)
    for k_, val_ in NEEDLES.get(view, {}).items():
        sc_ = CON['parts'][k_]['scale']
        ang_ = sc_['angle_min'] + (sc_['angle_max'] - sc_['angle_min']) * (val_ - sc_['min']) / (sc_['max'] - sc_['min'])
        pose(k_, ang_ - CON['parts'][k_]['rest'])
    for k_, d_ in MOVE.get(view, []):
        ob = bpy.data.objects[k_]
        ob.matrix_basis = Matrix.Translation(Vector(d_)) @ ob.matrix_basis
    for o in bpy.data.objects:
        if o.name.startswith('Snow_'):
            o.hide_render = view not in SNOW_VIEWS
        if o.name in HIDE_IN.get(view, []):
            o.hide_render = True
        elif o.type == 'MESH' and not o.name.startswith(('Snow_', 'COL_')) and not o.get('scene_prop'):
            o.hide_render = False
    for o in markers:
        o.hide_render = view != 'points_plan'
    for o in COLS:
        o.hide_render = view != 'colliders_plan' or o.name.startswith(('COL_Roof', 'COL_Header', 'COL_Floor'))
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
        P.world((0.010, 0.013, 0.026), 1.0)
        m = P.sun(0.16, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    elif (view.startswith('int_') and view != 'int_day') or view.endswith('_plan') or view == 'plan':
        P.world((0.30, 0.34, 0.40), 0.35)
        P.sun(1.2, (52, 0, 30))
    else:
        P.world((0.56, 0.62, 0.72), 0.9)
        P.sun(3.4, (48, 0, 215 if view == 'ext_east' else 30))
    for m in emit_mats:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        kind = m.get('lamp_kind')
        lit = night and kind in ('bulk', 'ext')
        pb.inputs['Emission Strength'].default_value = m['night_emit'] if lit else 0.0
    for name_, m in IND.items():
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = (m['night_emit'] * (1.0 if night else 0.5)
                                                        if name_ in LIT.get(view, ()) else 0.0)
    for m in glass:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = 0.0
    trees.hide_render = not (night or view in ('ext_day', 'snow', 'ext_open'))


CAMS = {
    'ext_day': ((-8.6, -7.4, 2.5), (-0.4, -0.5, 1.3), 28, None),
    'ext_east': ((8.2, -5.6, 2.3), (1.8, -0.7, 1.45), 28, None),
    'ext_night': ((-8.4, -4.8, 1.75), (-1.6, -0.9, 1.45), 30, None),
    'ext_open': ((-6.6, -3.2, 1.9), (-2.2, -0.9, 1.25), 24, None),
    'snow': ((-8.2, -6.9, 3.2), (-0.6, -0.4, 1.20), 28, None),
    'int_door': ((-2.70, -1.95, 1.66), (1.6, -0.75, 1.05), 17, None),
    'int_day': ((-2.70, -1.95, 1.66), (1.6, -0.75, 1.05), 17, None),
    'int_north': ((1.25, -0.20, 1.72), (-1.9, 1.75, 1.05), 18, None),
    'int_panel': ((-0.60, -1.015, 1.65), (-0.04, -1.015, 1.50), 36, None),
    'int_board': ((-1.00, -1.385, 1.83), (-1.48, -2.205, 1.59), 22, None),
    'int_fuel': ((-0.68, 0.815, 1.96), (-0.08, 2.165, 1.51), 22, None),
    'int_drums': ((0.97, 0.815, 2.16), (2.22, 2.015, 1.06), 22, None),
    'int_service': ((1.42, -2.165, 1.41), (1.40, -1.165, 0.93), 24, None),
    'int_radiator': ((1.54, -0.445, 1.73), (1.98, -1.045, 1.01), 20, None),
    'plan': ((0.0, 0.0, 5.0), (0.0, 0.0001, 0.0), 30, 7.6),
    'points_plan': ((0.0, 0.0, 5.0), (0.0, 0.0001, 0.0), 30, 7.6),
    'colliders_plan': ((0.0, 0.0, 5.0), (0.0, 0.0001, 0.0), 30, 7.6),
}
P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
ims = sc.render.image_settings
for v in views:
    state(v)
    loc, tgt, lens, ortho = CAMS[v]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
    plan = v.endswith('plan')
    sc.camera.data.clip_start = 2.58 if plan else 0.02
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
    else:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.view_settings.exposure = EXPOSURE.get(v, 0.0)
        P.render(os.path.join(OUT, v + '.png'))
print('rendered', views)
