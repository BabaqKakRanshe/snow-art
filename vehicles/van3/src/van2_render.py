"""Preview renders of van v2: exterior day / night (light groups), side with a 1.8 m figure, saloon, cab, dashboard
day / night, folding seats, lamp close-ups, texels, in-game 240-line frame.
python3 -I van2_render.py <blend> <views> [spp]  -> rend/van2/<view>.png"""
import sys, os, math, random
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector
import psxlib as P

blend, views = sys.argv[1], sys.argv[2].split(',')
spp = int(sys.argv[3]) if len(sys.argv) > 3 else 48
OUT = os.path.join(P.HERE, 'rend', 'van2')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
veh = [o for o in bpy.data.objects if o.type == 'MESH']
veh_bb = [o for o in veh if not o.name.startswith(('Stove', 'StoveGlow'))]
lo, hi = P.world_bbox(veh_bb)
L, Wd, H = (hi - lo)
cx = (lo[0] + hi[0]) / 2
print('bbox', lo.round(3), hi.round(3))
LIFT = 0.09
import json
json.dump({'lo': [float(v) for v in lo], 'hi': [float(v) for v in hi]}, open(os.path.join(OUT, 'frame.json'), 'w'))


def prop(o):
    o['scene_prop'] = 1
    return o


g = prop(P.ground(color=(0.80, 0.82, 0.86)))
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark = bpy.data.materials.new('spruce')
dark.use_nodes = True
dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.035, 0.03, 1)
r = random.Random(4)
for i in range(70):
    a = r.uniform(0, 2 * math.pi)
    d = r.uniform(16, 55)
    x, y = cx + d * math.cos(a), d * math.sin(a)
    ang = math.degrees(math.atan2(y, x - cx))
    if abs(ang + 49) < 25 or abs(ang - 150) < 20:            # keep the night cameras' views clear
        continue
    h = r.uniform(8, 15)
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.22, depth=h, location=(x, y, h / 2))
    t = bpy.context.object
    t.data.materials.append(dark)
    for c in t.users_collection:
        c.objects.unlink(t)
    trees.objects.link(t)
    prop(t)
hum_m = bpy.data.materials.new('human')
hum_m.use_nodes = True
hum_m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.08, 0.09, 0.11, 1)
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.2, depth=1.45, location=(hi[0] + 0.9, 0.8, 0.725))
body = prop(bpy.context.object)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.13, location=(hi[0] + 0.9, 0.8, 1.67))
head = prop(bpy.context.object)
for o in (body, head):
    o.data.materials.append(hum_m)

# beam test wall 10 m ahead of the lamps (as in headlamp photometry): shows the cut-off, the kink and the hot spot
bpy.ops.mesh.primitive_plane_add(size=1.0)
wall = prop(bpy.context.object)
wall.name = 'BeamWall'
wall.scale = (3.6, 14.0, 1.0)
wall.rotation_euler = (0.0, math.radians(-90), 0.0)
wall.location = (hi[0] + 10.0, 0.0, 1.8)
wall_m = bpy.data.materials.new('beam_wall')
wall_m.use_nodes = True
wall_m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.62, 0.63, 0.65, 1)
wall_m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
wall.data.materials.append(wall_m)

glass = [m for m in bpy.data.materials if m.name.startswith('M_PSX_Glass')]
for m in glass:
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Roughness'].default_value = 0.5
    pb.inputs['Specular IOR Level'].default_value = 0.12
emit_mats = [m for m in bpy.data.materials if m.get('night_emit') is not None]
LENS_GROUP = {'head': 'drive', 'spot': 'spot', 'work': 'work', 'marker': 'drive', 'tail': 'drive', 'amber': 'turn',
              'reverse': 'reverse', 'plate': 'drive', 'dome': 'int', 'night': 'int'}

# ---------------------------------------------------------------- lamps: IES point lights + lens glow (plane v11 method)
from mathutils import Matrix
import van_lights as VL
LM = VL.meta()
IESDIR = os.path.join(P.HERE, 'tex', 'van2', 'IES')
ies_txt = {}
for t_ in VL.TYPES:
    tx = bpy.data.texts.new('IES_%s.ies' % t_)
    tx.from_string(open(os.path.join(IESDIR, t_ + '.ies')).read())
    ies_txt[t_] = tx
RADIUS = {'head': 0.05, 'spot': 0.05, 'work': 0.05, 'reverse': 0.03}


def lamp_axes(e):
    """Blender light frame of a lamp: local X = right, Y = up, -Z = beam axis (reads the IES as written)"""
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
    nm.inputs[1].default_value = LM[t_]['k_norm']               # IES peak -> 1
    nt.links.new(ies.outputs['Fac'], nm.inputs[0])
    return nm.outputs[0]


def proj_area(ob, d):
    a = 0.0
    M3 = ob.matrix_world.to_3x3()
    for p_ in ob.data.polygons:
        n_ = (M3 @ p_.normal).normalized()
        a += p_.area * max(0.0, n_.dot(d))
    return max(a, 1e-5)


lights, lens_levels = [], []
for e in sorted([o for o in bpy.data.objects if o.name.startswith('LIGHT_')], key=lambda o: o.name):
    if 'type' not in e:                                  # props (pendant lamp, stove): plain lights as before
        kind = e.get('kind', 'POINT')
        ld = bpy.data.lights.new('L' + e.name[5:], kind)
        ld.energy = e['energy']
        ld.color = tuple(e['color'])
        ld.shadow_soft_size = 0.04
        if kind == 'SPOT':
            ld.spot_size = math.radians(e.get('spot', 45))
            ld.spot_blend = 0.5
        ob = bpy.data.objects.new('L' + e.name[5:], ld)
        sc.collection.objects.link(ob)
        ob.location = e.matrix_world.translation
        if 'dir' in e:
            ob.rotation_euler = Vector(e['dir']).to_track_quat('-Z', 'Y').to_euler()
        ob['group'] = e.get('group', 'int')
        lights.append(ob)
        continue
    t_ = e['type']
    ld = bpy.data.lights.new('L_' + e.name[6:], 'POINT')
    ld.energy = 4 * math.pi ** 2 * e['intensity_urp']             # E = I / d^2 as in URP
    ld.shadow_soft_size = RADIUS.get(t_, 0.015)
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
    lname = e.get('lens', '')
    if not lname or lname not in bpy.data.objects:
        continue
    # the lens glows with the same IES towards the viewer: bright when you look into the beam
    lo_ = bpy.data.objects[lname]
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
    lev.label = 'Level'
    lev.outputs[0].default_value = 0.0
    g1 = N_.new('ShaderNodeMath')
    g1.operation = 'MULTIPLY'
    Lk.new(fm.outputs[0], g1.inputs[0])
    g1.inputs[1].default_value = gain
    g2 = N_.new('ShaderNodeMath')
    g2.operation = 'MULTIPLY'
    Lk.new(g1.outputs[0], g2.inputs[0])
    Lk.new(lev.outputs[0], g2.inputs[1])
    cap = N_.new('ShaderNodeMath')                              # soft ceiling, as the plane's halo clip: the core
    cap.operation = 'MINIMUM'                                   # stays white, the bloom stays bounded
    Lk.new(g2.outputs[0], cap.inputs[0])
    cap.inputs[1].default_value = 40.0
    Lk.new(cap.outputs[0], pb.inputs['Emission Strength'])
    lens_levels.append((lev, e['group']))
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(lo_, attr, False)
print('lamps', len(lights), 'lens glows', len(lens_levels))

# air: a fog layer (two scattering lobes, as the plane previews); density = 0.034 x atmosphere per metre
fme = bpy.data.meshes.new('FogVolume')
x0_, x1_, y0_, y1_, z0_, z1_ = cx - 45, cx + 45, -45.0, 45.0, -0.3, 14.0
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
ATMOS = {'beams': 0.30, 'lightbar': 0.30, 'wall': 0.12, 'wall_all': 0.15, 'night': 0.35, 'ingame': 0.35, 'night_rear': 0.35, 'front_night': 0.35, 'lamps_front_night': 0.08,
         'lamps_rear_night': 0.10, 'cab': 0.35, 'night_work': 0.35}


def set_atmosphere(a):
    fog.hide_render = a <= 0
    sig = 0.034 * a
    vs1.inputs['Density'].default_value, vs2.inputs['Density'].default_value = 0.8 * sig, 0.2 * sig


# presentation fill for the daytime dashboard close-up (the panel faces away from the windscreen)
fill = bpy.data.objects.new('L_fill', bpy.data.lights.new('L_fill', 'AREA'))
sc.collection.objects.link(fill)
fill.data.shape = 'RECTANGLE'
fill.data.size, fill.data.size_y = 0.8, 0.5
fill.data.energy = 26
fill.data.color = (1.0, 0.97, 0.92)
fill.location = (1.02, 0.15, 1.78 + 0.09)
fill.rotation_euler = (Vector((1.76, 0.35, 1.20 + 0.09)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
plan_light = bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA'))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 4.0, 1.7
plan_light.data.energy = 260
plan_light.data.color = (1.0, 0.93, 0.84)
plan_light.location = (0, 0, 1.86 + LIFT)
seats = {o.name: o for o in bpy.data.objects if o.name.startswith('Seat_') and not o.name.endswith(('_Fixed', '_Leg'))}


def fold(tag, f):
    pan = seats['Seat_' + tag]
    leg = bpy.data.objects['Seat_' + tag + '_Leg']
    sgn = pan.get('sgn', 1)
    pan.rotation_euler.x = math.radians(-sgn * 90 * f)
    leg.rotation_euler.x = math.radians(sgn * 90 * f)


GROUPS = {
    'night': {'drive', 'int', 'spot'}, 'ingame': {'drive', 'int', 'spot'}, 'night_rear': {'drive', 'int', 'work', 'reverse'},
    'night_work': {'drive', 'int', 'work', 'spot'}, 'inside': {'int'}, 'stove': {'int'}, 'cab': {'int', 'drive'},
    'dash_night': {'int', 'drive'}, 'seats': {'int'}, 'lamps_front_night': {'drive', 'spot', 'work'},
    'lamps_rear_night': {'drive', 'work', 'reverse'}, 'domes': {'int'}, 'front_night': {'drive', 'spot', 'int'}, 'lightbar': {'drive', 'work', 'int'},
    'beams': {'drive', 'spot', 'int'},
    'fold0': {'int'}, 'fold50': {'int'}, 'fold100': {'int'}, 'wall': {'drive'}, 'wall_all': {'drive', 'spot', 'work'},
}
NIGHT = set(GROUPS)
FOLDS = {'inside': {'R1': 1, 'R2': 1}, 'stove': {'R1': 1, 'R2': 1}, 'seats': {'R1': 1, 'R2': 0.0, 'L4': 1},
         'plan': {'R1': 1, 'R2': 1}, 'fold0': {'R1': 1, 'R2': 1}, 'fold50': {'L2': 0.5, 'R1': 1, 'R2': 1},
         'fold100': {'L2': 1, 'R1': 1, 'R2': 1}}
EXPOSURE = {'dash': 0.4, 'cab': 0.6, 'fold0': 0.3, 'fold50': 0.3, 'fold100': 0.3}


def state(view):
    night = view in NIGHT
    on = GROUPS.get(view, set())
    for l in lights:
        l.hide_render = not (night and l['group'] in on)
    for lev_, grp_ in lens_levels:
        lev_.outputs[0].default_value = 1.0 if (night and grp_ in on) else 0.0
    set_atmosphere(ATMOS.get(view, 0.0))
    plan_light.hide_render = view != 'plan'
    fill.hide_render = view != 'dash'
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith(('Sun', 'Moon'))]:
        bpy.data.objects.remove(o, do_unlink=True)
    if night:
        P.world((0.010, 0.013, 0.026), 1.0)
        m = P.sun(0.16, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    else:
        P.world((0.56, 0.62, 0.72), 0.9)
        P.sun(3.4, (52, 0, 30))
    outside_night = view in ('night', 'ingame', 'night_rear', 'night_work', 'front_night', 'lamps_rear_night', 'lamps_front_night', 'beams', 'lightbar')
    for m in glass:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = (m.get('glow', 0.35) if outside_night else 0.0)
    for m in emit_mats:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        grp = m.get('group')
        if grp is not None:
            lit = night and LENS_GROUP.get(grp, 'int') in on
        else:
            lit = night
        pb.inputs['Emission Strength'].default_value = m['night_emit'] if lit else m.get('day_emit', 0.0)
    trees.hide_render = not night
    wall.hide_render = not view.startswith('wall')
    body.hide_render = head.hide_render = view != 'side'
    for tag in ('L1', 'L2', 'L3', 'L4', 'R1', 'R2'):
        if 'Seat_' + tag in seats:
            fold(tag, FOLDS.get(view, {}).get(tag, 0.0))


c = Vector((cx, 0, lo[2] + 0.42 * H))
Z = LIFT
CAMS = {
    'q34': ((cx + 1.30 * L, 0.95 * L, 0.36 * L), c, 32, None),
    'q34r': ((cx - 1.25 * L, -0.95 * L, 0.42 * L), c, 32, None),
    'side': ((cx, 16, lo[2] + 0.38 * H), Vector((cx + 0.25, 0, lo[2] + 0.38 * H)), 30, L * 1.62),
    'night': ((cx + 1.0 * L, -1.18 * L, 0.33 * L), Vector((cx - 0.05 * L, 0, lo[2] + 0.40 * H)), 28, None),
    'ingame': ((cx + 1.0 * L, -1.18 * L, 0.33 * L), Vector((cx - 0.05 * L, 0, lo[2] + 0.40 * H)), 28, None),
    'night_rear': ((cx - 1.15 * L, 1.0 * L, 0.36 * L), Vector((cx + 0.05 * L, 0, lo[2] + 0.38 * H)), 28, None),
    'close': ((hi[0] + 0.45, 1.25, 1.25), Vector((2.05, 0.35, 1.0)), 30, None),
    'inside': ((-1.95, -0.10, 1.62 + Z), Vector((1.2, 0.20, 1.25 + Z)), 17, None),
    'stove': ((0.30, -0.50, 1.58 + Z), Vector((-1.95, 0.45, 1.00 + Z)), 19, None),
    'seats': ((-0.35, -0.62, 1.50 + Z), Vector((-0.45, 0.90, 1.10 + Z)), 16, None),
    'cab': ((1.02, 0.50, 1.74 + Z), Vector((3.6, 0.30, 1.32 + Z)), 17, None),
    'dash': ((1.04, 0.47, 1.70 + Z), Vector((1.76, 0.36, 1.21 + Z)), 24, None),
    'dash_night': ((1.04, 0.47, 1.70 + Z), Vector((1.76, 0.36, 1.21 + Z)), 24, None),
    'front': ((7.4, 0.0, 1.30), Vector((2.0, 0.0, 1.22)), 42, None),
    'front_night': ((cx + 1.15 * L, 0.85 * L, 1.25), Vector((cx + 0.12 * L, 0.0, 1.00)), 28, None),
    'beams': ((cx - 0.95 * L, 0.60 * L, 3.6), Vector((cx + 2.3 * L, -0.15 * L, 0.0)), 24, None),
    'wall': ((cx - 1.2, 3.4, 2.3), Vector((hi[0] + 10.0, -0.6, 1.0)), 26, None),
    'wall_all': ((cx - 1.2, 3.4, 2.3), Vector((hi[0] + 10.0, -0.6, 1.0)), 26, None),
    'lightbar': ((cx - 0.95 * L, 0.60 * L, 3.6), Vector((cx + 2.3 * L, -0.15 * L, 0.0)), 24, None),
    'fold0': ((0.05, -0.62, 1.30 + Z), Vector((-0.57, 0.85, 0.96 + Z)), 22, None),
    'fold50': ((0.05, -0.62, 1.30 + Z), Vector((-0.57, 0.85, 0.96 + Z)), 22, None),
    'fold100': ((0.05, -0.62, 1.30 + Z), Vector((-0.57, 0.85, 0.96 + Z)), 22, None),
    'lamps_front': ((3.55, 1.25, 1.35), Vector((2.25, 0.20, 1.05)), 30, None),
    'lamps_front_night': ((3.55, 1.25, 1.35), Vector((2.25, 0.20, 1.05)), 30, None),
    'lamps_rear': ((-3.45, -1.2, 1.40), Vector((-2.2, -0.15, 1.15)), 30, None),
    'lamps_rear_night': ((-3.45, -1.2, 1.40), Vector((-2.2, -0.15, 1.15)), 30, None),
    'roof': ((3.2, -1.8, 3.25), Vector((0.6, 0.0, 2.20)), 30, None),
    'domes': ((-0.6, -0.45, 1.35 + Z), Vector((0.6, 0.15, 2.00 + Z)), 18, None),
    'plan': ((0.0, 0.0, 3.0 + Z), Vector((0.0, 0.0001, 0.0)), 30, 4.75),
}
P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
BLOOM = {'domes': 0.18, 'inside': 0.15, 'stove': 0.15, 'seats': 0.15, 'dash_night': 0.2, 'fold0': 0.12, 'fold50': 0.12,
         'fold100': 0.12}
ims = sc.render.image_settings
import subprocess
for v in views:
    state(v)
    loc, tgt, lens, ortho = CAMS[v]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    sc.render.resolution_x, sc.render.resolution_y = (427, 240) if v == 'ingame' else (900, 600)
    if v == 'plan':
        sc.render.resolution_x, sc.render.resolution_y = 900, 450
    interior = v in ('inside', 'stove', 'seats', 'cab', 'dash', 'dash_night', 'domes', 'plan', 'fold0', 'fold50', 'fold100')
    sc.cycles.samples = spp * (2 if interior else 1)
    sc.camera.data.clip_start = (1.20 if v == 'plan' else 0.02)
    night = v in NIGHT
    if night:
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
