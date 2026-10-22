"""Preview renders of the forester's hut (out/hut.blend posed from out/hut_contract.json): outside by day from the path
and from the back, the prologue night (the door open, the storm lantern burning, mist), the lantern seen from the
road through the trees, inside by day from the door and from the back, the oil lamp lit at night, close-ups of the
stove and of the map and calendar, the hunting stand, the sign; plan views with the points and colliders; and the
same views as the Update 3 hut renders (front, back, iso, inside) for the comparison sheet.
python3 -I hut_render.py <views> [spp] [--draft]  -> rend/hut/<view>.png (rend/hut_draft with --draft)"""
import sys, os, math, json, random, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
from mathutils import Vector, Matrix
import psxlib as P

views = sys.argv[1].split(',')
spp = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 48
DRAFT = '--draft' in sys.argv
sfx = '_draft' if DRAFT else ''
OUT = os.path.join(P.HERE, 'rend', 'hut' + sfx)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'hut{sfx}.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', f'hut_contract{sfx}.json')))
LJ = json.load(open(os.path.join(P.HERE, 'out', 'hut_lights.json')))['lights']
HS = Vector(CON['parts']['Hochsitz']['pivot'])
LAN_XY = Vector(CON['sockets']['Audio_Lantern']['pos'][:2])
CAR_DIR = Vector((71.6, -58.2)).normalized()                     # toward the car at the road (hut frame, 92 m)
FAR = LAN_XY + CAR_DIR * 26.0


def prop(o):
    o['scene_prop'] = 1
    return o


def ground_z(x, y):
    """flat round the hut, rising toward the stand (its root stands 0.5 m higher, 11 m away)"""
    return max(0.0, (x - 3.0) * 0.063) - 0.004


# forest floor: a gently rising grid
bm = bmesh.new()
N_, S_ = 60, 1.5
vs = {}
for i in range(N_ + 1):
    for j in range(N_ + 1):
        x, y = -45 + i * S_, -45 + j * S_
        vs[i, j] = bm.verts.new((x, y, ground_z(x, y)))
for i in range(N_):
    for j in range(N_):
        bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
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
ramp.color_ramp.elements[0].color = (0.055, 0.045, 0.030, 1)
ramp.color_ramp.elements[1].color = (0.11, 0.10, 0.055, 1)
gnt.links.new(noi.outputs['Fac'], ramp.inputs['Fac'])
gnt.links.new(ramp.outputs['Color'], gpb.inputs['Base Color'])
gme.materials.append(gm)
# spruces round the clearing
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark = bpy.data.materials.new('spruce')
dark.use_nodes = True
dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.018, 0.034, 0.024, 1)
trunk = bpy.data.materials.new('trunk')
trunk.use_nodes = True
trunk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.06, 0.045, 0.035, 1)
r = random.Random(7)
placed = 0
while placed < 110:
    a = r.uniform(0, 2 * math.pi)
    d = r.uniform(6.5, 44)
    x, y = d * math.cos(a), d * math.sin(a)
    if (Vector((x, y)) - HS.xy).length < 4.0 or (-3.5 < x < 3.5 and y < -2 and y > -16):        # the stand, the path
        continue
    t_ = max(0.0, min(1.0, (Vector((x, y)) - LAN_XY).dot(CAR_DIR)))
    if t_ > 0.0 and (Vector((x, y)) - LAN_XY - CAR_DIR * (Vector((x, y)) - LAN_XY).dot(CAR_DIR)).length < 1.3 and \
            (Vector((x, y)) - LAN_XY).dot(CAR_DIR) < 30.0:                                      # keep a gap toward the road
        continue
    h = r.uniform(9, 19)
    z0 = ground_z(x, y)
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.17, depth=h * 0.82, location=(x, y, z0 + h * 0.18 + h * 0.41))
    t = bpy.context.object
    t.data.materials.append(dark)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=h * 0.012, depth=h * 0.3, location=(x, y, z0 + h * 0.15))
    tk = bpy.context.object
    tk.data.materials.append(trunk)
    for o_ in (t, tk):
        for c in o_.users_collection:
            c.objects.unlink(o_)
        trees.objects.link(o_)
        prop(o_)
    placed += 1

# lamps: IES point lights + lens glow (the van / plane method), glow cards
import gen_lights as GL
import van_lights as VL
LM = {}
for it in LJ:
    LM[it['type']] = dict(color=it['colorLinear'], k_norm=1.0 / (VL.K_CYCLES * it['peakCandela']), lens_floor=0.15)
IESDIR = os.path.join(P.HERE, 'tex', 'hut', 'IES')
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
    ld.shadow_soft_size = 0.02
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
glow_objs = [o for o in bpy.data.objects if o.name.startswith('Glow_')]
glow_mats = {m for o in glow_objs for m in o.data.materials}
print('lamps', len(lights))

# mist for the night outside views
fme = bpy.data.meshes.new('FogVolume')
x0_, x1_, y0_, y1_, z0_, z1_ = -45, 45, -45.0, 45.0, -0.3, 14.0
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


# presentation fill for the inside / close-up views (an area light standing in for daylight through the door)
fill = prop(bpy.data.objects.new('L_fill', bpy.data.lights.new('L_fill', 'AREA')))
sc.collection.objects.link(fill)
fill.data.shape = 'DISK'
fill.data.color = (1.0, 0.95, 0.88)
FILLS = {   # view: (location, target, energy W, size m)
    'int_day': ((-0.4, -0.95, 2.25), (0.4, 0.6, 0.6), 70, 1.4),
    'int_back': ((0.4, 0.7, 2.25), (-0.6, -0.6, 0.8), 70, 1.4),
    'int_stove': ((0.30, 0.10, 1.95), (0.94, 0.70, 0.8), 26, 0.6),
    'int_map': ((-0.20, 0.10, 1.95), (-0.20, 1.08, 1.85), 22, 0.8),
    'old_in_back': ((0.3, 0.2, 2.0), (0.3, 0.2, 0.0), 120, 1.5),
}
plan_light = prop(bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA')))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 2.6, 2.4
plan_light.data.energy = 180
plan_light.location = (0, 0, 2.30)

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


DOOR_OPEN = [('IX_HutDoor_1', 100)]
POSES = {'ext_night': DOOR_OPEN, 'ext_far': DOOR_OPEN, 'int_day': DOOR_OPEN, 'int_back': DOOR_OPEN, 'int_lamp': DOOR_OPEN,
         'int_stove': [('Stove_Door', 95)], 'ext_day': DOOR_OPEN, 'iso': DOOR_OPEN, 'old_in_back': DOOR_OPEN,
         'game_hut': DOOR_OPEN}
# the prologue items at their spots (placeholders: the game spawns them)
KIND_COL = {'hand': (1.0, 0.85, 0.1), 'pour': (0.2, 0.5, 1.0), 'item_slot': (0.2, 0.9, 0.3), 'audio': (0.9, 0.2, 0.9),
            'vfx': (1.0, 0.45, 0.1), 'hide': (0.1, 0.9, 0.9), 'knock': (0.95, 0.15, 0.15), 'seat': (0.6, 0.4, 1.0),
            'climb': (0.6, 0.9, 0.3)}
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
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.03, location=s_['pos'])
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

NIGHT = {'ext_night', 'ext_far', 'int_lamp', 'game_hut'}
GROUPS = {'ext_night': {'lantern'}, 'ext_far': {'lantern'}, 'int_lamp': {'lantern', 'hut'}, 'game_hut': {'lantern'}}
ATMOS = {'ext_night': 0.55, 'ext_far': 0.45, 'game_hut': 0.5}
EXPOSURE = {'int_day': 0.5, 'int_back': 0.5, 'int_stove': 0.4, 'int_map': 0.4, 'ext_night': 1.0, 'ext_far': 1.4, 'int_lamp': 0.3,
            'old_in_back': 0.3}
BLOOM = {'ext_night': 0.35, 'ext_far': 0.45, 'int_lamp': 0.2, 'game_hut': 0.4}
EXPOSURE['game_hut'] = 2.0
emit_mats = [m for m in bpy.data.materials if m.get('night_emit') is not None and not m.name.startswith('M_LensFX')]


def state(view):
    reset_parts()
    night = view in NIGHT
    on = GROUPS.get(view, set())
    for l in lights:
        l.hide_render = not (night and l['group'] in on)
    for lev_, grp_ in lens_levels:
        lev_.outputs[0].default_value = 1.0 if (night and grp_ in on) else 0.0
    for o in glow_objs:
        o.hide_render = not (night and 'lantern' in on)
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
        o.hide_render = view != 'colliders_plan' or o.name.startswith(('COL_Roof', 'COL_Floor', 'COL_HS_Roof'))
    plan_light.hide_render = not view.endswith('plan')
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
    elif view.startswith(('int_', 'old_in')) or view.endswith('plan'):
        P.world((0.30, 0.34, 0.40), 0.35)
        P.sun(1.2, (52, 0, -150))
    else:
        P.world((0.50, 0.56, 0.64), 0.8)
        P.sun(2.6, (50, 0, -150 if view != 'ext_back' else 40), (1.0, 0.94, 0.84))
    for m in emit_mats:
        nt_ = m.node_tree
        pb = next((n for n in nt_.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if pb is not None:
            pb.inputs['Emission Strength'].default_value = 0.0
    trees.hide_render = view.endswith('plan') or view.startswith(('int_', 'old_in'))
    cam_, tgt_ = Vector(CAMS[view][0][:2]), Vector(CAMS[view][1][:2])
    seg = tgt_ - cam_
    for t in trees.objects:                                      # no tree in the line of sight (to the target and 3 m on)
        p_ = t.location.xy
        u_ = max(0.0, min(1.0 + 3.0 / max(seg.length, 1e-6), (p_ - cam_).dot(seg) / max(seg.length_squared, 1e-9)))
        t.hide_render = trees.hide_render or (view not in ('ext_far',) and (p_ - cam_ - seg * u_).length < 2.2)
    g.hide_render = view.endswith('plan')


CAMS = {   # hut frame: the door is on the front (-y); the old views = the Update 3 renders' cameras
    'ext_day': ((4.6, -6.4, 1.75), (0.0, -0.4, 1.35), 26, None),
    'ext_back': ((-5.4, 5.6, 2.1), (-0.5, 0.2, 1.25), 26, None),
    'ext_night': ((2.2, -6.8, 1.65), (0.1, -1.2, 1.45), 28, None),
    'ext_far': ((FAR.x, FAR.y, 1.60), (LAN_XY.x, LAN_XY.y, 1.75), 50, None),
    'int_day': ((-0.42, -1.10, 1.62), (0.55, 0.90, 1.05), 15, None),
    'int_back': ((0.35, 0.95, 1.62), (-0.55, -1.10, 1.00), 15, None),
    'int_lamp': ((-0.42, -1.10, 1.62), (0.40, 0.90, 1.55), 15, None),
    'int_stove': ((0.33, 0.18, 1.28), (0.98, 0.74, 0.70), 20, None),
    'int_map': ((-0.20, 0.05, 1.70), (-0.25, 1.08, 1.85), 22, None),
    'stand': ((6.9, -3.6, 1.9), (10.9, 2.3, 3.0), 24, None),
    'sign': ((3.1, -6.2, 1.55), (1.0, -2.2, 1.35), 30, None),
    'plan': ((0.0, -0.6, 12.0), (0.0, -0.5999, 0.0), 30, 7.0),
    'points_plan': ((0.0, -0.6, 12.0), (0.0, -0.5999, 0.0), 30, 7.0),
    'colliders_plan': ((0.0, -0.6, 12.0), (0.0, -0.5999, 0.0), 30, 7.0),
    'old_front': ((0.5, -9.0, 2.0), (0, 0, 1.6), 30, None),
    'old_back': ((-0.5, 9.0, 2.2), (0, 0, 1.6), 30, None),
    'old_iso': ((-7.0, -8.0, 5.0), (0, -0.5, 1.4), 30, None),
    'old_right': ((9.0, -0.6, 2.0), (0, -0.6, 1.6), 30, None),
    'old_in_back': ((0.6, 1.0, 1.6), (-0.4, -1.3, 1.1), 14, None),
    'game_hut': ((3.627, -14.795, 1.665), (0.0, 0.0, 1.58), 41.555, None),     # the map's 'Hut' viewpoint (vertical fov)
}
P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
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
    plan = v.endswith('plan')
    sc.camera.data.clip_start = 12.0 - 2.25 if plan else 0.02
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
