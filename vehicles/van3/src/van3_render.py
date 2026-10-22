"""Preview renders of van v3: the v2 views plus the mechanics posed from out/van3_contract.json (doors, hatches,
engine cover, service pose of the engine, battery box under the folded seat, fuse box, controls, fuel filler and
pouring from a jerrycan, tanks underneath, roof hatch, the new wheel).
python3 -I van3_render.py <blend> <views> [spp]  -> rend/van3/<view>.png"""
import sys, os, math, random
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Euler
import psxlib as P

blend, views = sys.argv[1], sys.argv[2].split(',')
spp = int(sys.argv[3]) if len(sys.argv) > 3 else 48
OUT = os.path.join(P.HERE, 'rend', 'van3')
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
              'reverse': 'reverse', 'plate': 'drive', 'dome': 'int', 'night': 'int', 'fog': 'fog', 'hand': 'hand',
              'torch': 'torch', 'flare': 'flare'}

# ---------------------------------------------------------------- lamps: IES point lights + lens glow (plane v11 method)
from mathutils import Matrix
import van_lights as VL
LM = VL.meta()
IESDIR = os.path.join(P.HERE, 'tex', 'van3', 'IES')
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
ATMOS = {'fog_night': 0.35, 'beams': 0.30, 'lightbar': 0.30, 'wall': 0.12, 'wall_all': 0.15, 'night': 0.35, 'ingame': 0.35, 'night_rear': 0.35, 'front_night': 0.35, 'lamps_front_night': 0.08,
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
fill2 = bpy.data.objects.new('L_fill2', bpy.data.lights.new('L_fill2', 'AREA'))
sc.collection.objects.link(fill2)
fill2.data.shape = 'DISK'
fill2.data.color = (1.0, 0.96, 0.90)
FILLS = {   # view: (location, target, energy W, size m)
    'engine_closed': ((1.18, -0.30, 1.80 + LIFT), (1.18, 0.0, 0.9 + LIFT), 30, 0.5),
    'engine_open': ((1.18, -0.30, 1.80 + LIFT), (1.18, 0.0, 0.7 + LIFT), 40, 0.5),
    'engine_top': ((1.30, -0.10, 1.80 + LIFT), (1.18, 0.0, 0.6 + LIFT), 45, 0.6),
    'fusebox': ((1.35, -0.40, 1.40 + LIFT), (1.70, -0.30, 1.0 + LIFT), 14, 0.4),
    'controls': ((1.40, 0.70, 1.35 + LIFT), (1.80, 0.45, 0.85 + LIFT), 22, 0.4),
    'dash_controls': ((1.40, 0.30, 1.45 + LIFT), (1.75, 0.33, 1.10 + LIFT), 10, 0.3),
    'radiator': ((3.2, 0.3, 1.6), (2.16, 0.0, 1.10), 60, 0.8),
    'fuel': ((-0.30, 1.55, 1.35), (0.15, 0.98, 0.90), 30, 0.6),
    'tanks': ((0.3, 1.6, 0.12), (0.25, 0.5, 0.45), 15, 0.8),
    'toolkit': ((0.60, -0.25, 1.55 + LIFT), (0.63, -0.77, 0.80 + LIFT), 12, 0.5),
    'jack': ((-0.62, 0.05, 1.50 + LIFT), (-0.62, 0.78, 0.82 + LIFT), 12, 0.5),
    'lock': ((1.12, 0.25, 1.58 + LIFT), (1.30, 0.86, 1.30 + LIFT), 10, 0.4),
    'heater': ((1.40, -0.05, 1.45 + LIFT), (1.76, -0.02, 1.17 + LIFT), 10, 0.3),
    'crank': ((3.3, 0.6, 1.0), (2.35, 0.0, 0.55), 40, 0.8),
    'radio_glovebox': ((1.30, -0.28, 1.55 + LIFT), (1.80, -0.40, 1.20 + LIFT), 14, 0.4),
    'cab_window': ((1.20, -0.20, 1.75 + LIFT), (1.55, 0.75, 1.50 + LIFT), 10, 0.4),
    'cold_start': ((2.6, 1.6, 0.9), (1.4, 0.4, 0.3), 50, 1.0),
}
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


# ---------------------------------------------------------------- mechanics: poses from the interaction contract
CON = json.load(open(os.path.join(P.HERE, 'out', 'van3_contract.json')))
REST = {k: bpy.data.objects[k].matrix_basis.copy() for k in CON['parts']
        if k in bpy.data.objects and not k.startswith(('Seat_', 'Needle_'))}


LENS_REST = {o.name: o.matrix_world.copy() for o in bpy.data.objects if o.name.startswith('Lens_')}
LIGHT_REST = {l_.name: l_.matrix_world.copy() for l_ in lights}


def rope(name, pts, r, colr=(0.02, 0.02, 0.02)):
    """render-only cord / cable through pts (a poly curve with a round bevel)"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i_, p_ in enumerate(pts):
        sp.points[i_].co = (*p_, 1.0)
    ob = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(ob)
    m_ = bpy.data.materials.new(name + '_m')
    m_.use_nodes = True
    m_.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colr, 1)
    m_.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.6
    cu.materials.append(m_)
    ob.hide_render = True
    ob['scene_prop'] = 1
    return ob


def sag(p0, p1, depth, n=14):
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, i / (n - 1)) - Vector((0, 0, depth * 4 * (i / (n - 1)) * (1 - i / (n - 1)))) for i in range(n)]


_plug = Vector(CON['sockets']['Plug_12V']['pos'])
CORD = rope('Cord_WorkLamp', sag(_plug, Vector((1.14, -0.05, 1.445)), 0.35), 0.004)
_fl = Vector(CON['sockets']['Winch_Fairlead']['pos'])
CABLE = rope('Cable_Winch', sag(_fl, _fl + Vector((0.85, 0.75, -0.62)), 0.03), 0.004, (0.25, 0.25, 0.26))
FROST_VIEWS = {'frost'}


def ghost_figure(name, base, yaw_deg, head_turn_deg=0.0):
    """render-only figure sitting on the floor, knees up, arms round them - the silhouette for the mirror view.
    base: floor point under the pelvis; yaw 0 = facing +x"""
    import bmesh
    bm = bmesh.new()

    def ell(c, r, rot=(0.0, 0.0, 0.0), seg=(14, 9)):
        res = bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
        R = Euler(tuple(math.radians(a_) for a_ in rot)).to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ R @ Matrix.Diagonal((*r, 1.0)), verts=res['verts'])
    ht = head_turn_deg
    ell((0.0, 0.0, 0.11), (0.14, 0.17, 0.10))                               # pelvis
    ell((0.0, 0.0, 0.36), (0.12, 0.18, 0.24), (0, 15, 0))                   # torso, leaning forward
    ell((0.06, 0.0, 0.56), (0.11, 0.22, 0.075))                             # shoulders
    ell((0.09, 0.0, 0.65), (0.05, 0.05, 0.07))                              # neck
    ell((0.12, 0.0, 0.76), (0.10, 0.085, 0.12), (0, 15, ht))                # head
    ell((0.09, 0.0, 0.78), (0.09, 0.10, 0.14), (0, 30, ht))                 # hair over the face
    for sy in (1, -1):
        ell((0.19, sy * 0.095, 0.25), (0.21, 0.075, 0.07), (0, -47, 0))     # thighs, knees up
        ell((0.375, sy * 0.10, 0.225), (0.055, 0.055, 0.19), (0, -14, 0))   # shins
        ell((0.46, sy * 0.10, 0.035), (0.11, 0.045, 0.035))                 # feet
        ell((0.13, sy * 0.205, 0.44), (0.05, 0.05, 0.14), (0, -32, 0))      # upper arms
        ell((0.29, sy * 0.125, 0.355), (0.13, 0.045, 0.045), (0, 0, -sy * 40))  # forearms round the knees
        ell((0.39, sy * 0.04, 0.38), (0.05, 0.035, 0.05))                   # hands
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.matrix_world = Matrix.Translation(base) @ Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')
    m_ = bpy.data.materials.new(name + '_m')
    m_.use_nodes = True
    pb_ = m_.node_tree.nodes['Principled BSDF']
    pb_.inputs['Base Color'].default_value = (0.003, 0.003, 0.0035, 1)
    pb_.inputs['Roughness'].default_value = 1.0
    for k_ in ('Specular IOR Level', 'Specular'):                 # no sheen: a flat black shape
        if k_ in pb_.inputs:
            pb_.inputs[k_].default_value = 0.0
    me.materials.append(m_)
    ob.hide_render = True
    ob['scene_prop'] = 1
    return ob


if 'M_Van_MirrorRT' in bpy.data.materials:                     # preview: a sharp mirror (Unity uses a render texture)
    _mpb = next(n_ for n_ in bpy.data.materials['M_Van_MirrorRT'].node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    _mpb.inputs['Roughness'].default_value = 0.0
GHOST = ghost_figure('Ghost_Mirror', Vector((-1.72, -0.36, 0.716 + LIFT)), 6.0)   # by the rear doors, beside the pendant lamp's line
_lob = bpy.data.objects['lob']
_lob_mats = [m for m in _lob.data.materials]
frost_m = bpy.data.materials.new('M_Frost_Preview')
frost_m.use_nodes = True
_N, _K = frost_m.node_tree.nodes, frost_m.node_tree.links
_pbf = _N['Principled BSDF']
_pbf.inputs['Roughness'].default_value = 0.7
_tx = _N.new('ShaderNodeTexImage')
_tx.image = bpy.data.images.load(os.path.join(P.HERE, 'tex', 'van3', 'T_Van_Frost.png'))
_tx.interpolation = 'Closest'
_uvn = _N.new('ShaderNodeUVMap')
_uvn.uv_map = 'PSX'
_K.new(_uvn.outputs[0], _tx.inputs[0])
_K.new(_tx.outputs['Color'], _pbf.inputs['Base Color'])
_gt = _N.new('ShaderNodeMath')
_gt.operation = 'GREATER_THAN'
_gt.inputs[1].default_value = 0.15                          # frost amount 0.85 (flat mask: covers 85 %)
_K.new(_tx.outputs['Alpha'], _gt.inputs[0])
_gl = _N.new('ShaderNodeBsdfGlass')
_gl.inputs['Roughness'].default_value = 0.05
_mx = _N.new('ShaderNodeMixShader')
_K.new(_gt.outputs[0], _mx.inputs[0])
_K.new(_gl.outputs[0], _mx.inputs[1])
_K.new(_pbf.outputs[0], _mx.inputs[2])
_out = next(n_ for n_ in _N if n_.type == 'OUTPUT_MATERIAL')
_K.new(_mx.outputs[0], _out.inputs['Surface'])


def reset_parts():
    for k, mb in REST.items():
        bpy.data.objects[k].matrix_basis = mb
        bpy.data.objects[k].hide_render = False


def pose(name, val):
    """hinge / twist: degrees about the contract axis through the pivot; slide: metres along the axis"""
    p_ = CON['parts'][name]
    ob, mb = bpy.data.objects[name], REST[name]
    ax = Vector(p_['axis']).normalized()
    if p_['kind'] == 'stretch':
        t = mb.to_translation()
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Scale(val, 4, ax) @ Matrix.Translation(-t) @ mb
    elif p_.get('unit') == 'm':
        ob.matrix_basis = Matrix.Translation(ax * val) @ mb
    else:
        t = mb.to_translation()
        ob.matrix_basis = Matrix.Translation(t) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-t) @ mb


def move(name, d, turn=None):
    """items: shift by d (world) on top of the current pose, optionally turned (deg, axis) about the pivot first"""
    ob = bpy.data.objects[name]
    mb = ob.matrix_basis.copy()
    t = mb.to_translation()
    R = Matrix.Identity(4) if turn is None else Matrix.Rotation(math.radians(turn[0]), 4, Vector(turn[1]).normalized())
    ob.matrix_basis = Matrix.Translation(t + Vector(d)) @ R @ Matrix.Translation(-t) @ mb


def pour_pose(can='Jerrycan_1', side='L', tilt=77.0):
    """the jerrycan held over the filler, the spout screwed on and its tip in the neck"""
    ob = bpy.data.objects[can]
    M4 = Matrix([ob['upright'][i * 4:i * 4 + 4] for i in range(4)])          # upright can -> body (unlifted)
    c0 = REST[can].to_translation() - Vector((0, 0, LIFT))
    s_ = 1 if side == 'L' else -1
    tip_local = Vector((0, -0.255, 0.82))
    target = Vector(CON['sockets']['Pour_Fuel_' + side]['pos']) - Vector((0, s_ * 0.025, 0))     # 2.5 cm into the neck
    Rc = Matrix.Rotation(math.radians(s_ * tilt), 4, 'X')
    X = target - (Rc @ tip_local)
    Mn = Matrix.Translation(X) @ Rc
    ob.matrix_basis = Mn @ M4.inverted() @ Matrix.Translation(c0)
    sp = bpy.data.objects['Spout']
    p0 = REST['Spout'].to_translation() - Vector((0, 0, LIFT))
    A_s, A_c = p0 - Vector((0.025, 0, 0)), Vector((0, -0.135, 0.475))
    Rsc = Matrix(((0, 0, 1), (0, -1, 0), (1, 0, 0))).transposed().to_4x4()
    sp.matrix_basis = Mn @ Matrix.Translation(A_c) @ Rsc @ Matrix.Translation(-A_s) @ Matrix.Translation(p0)


ALL_OPEN = [('doorL', 70), ('doorP', 70), ('doorZL', 100), ('dooZP', 100), ('doorSalon', 80), ('RoofHatch', 35),
            ('RadiatorHatch', 100), ('FuelFlap_L', 110), ('FuelFlap_R', 110), ('EngineCover', 85)]
POSES = {
    'doors': ALL_OPEN, 'doors_rear': ALL_OPEN,
    'engine_closed': [('doorP', 70)],
    'engine_open': [('doorP', 70), ('EngineCover', 85)],
    'engine_top': [('doorP', 70), ('EngineCover', 85), ('Engine_Dipstick', 0.30), ('Engine_OilCap', 90),
                   ('Engine_Lead_1', 0.04), ('M:Engine_OilCap', (0, 0, 0.05)), ('M:Engine_DistributorCap', (0, 0, 0.06)),
                   ('M:Engine_AirFilterLid', (0.02, -0.46, 0.13))],
    'radiator': [('RadiatorHatch', 100), ('M:Radiator_Cap', (0.05, 0.0, 0.06))],
    'battery': [('BatteryBox_Lid', 65), ('MassSwitch_Key', 90), ('Battery_ClampNeg', 0.05), ('Battery_ClampPos', 0.05)],
    'fusebox': [('doorP', 70), ('FuseBox_Lid', 100), ('M:Fuse_3', (-0.025, 0, 0))],
    'controls': [('doorL', 70), ('Pedal_Brake', 10), ('Knob_Choke', 0.03), ('Handbrake', 0.06)],
    'dash_controls': [('doorL', 70), ('Ignition_Key', 60), ('Knob_Choke', 0.035)],
    'fuel': [('FuelFlap_L', 100), ('FuelCap_L', 200), ('M:FuelCap_L', (0, 0.035, 0))],
    'fuel_pour': [('FuelFlap_L', 110), ('H:FuelCap_L', None), ('POUR', 'L')],
    'roofhatch': [('RoofHatch', 35)], 'roofhatch_in': [('RoofHatch', 35)],
    'tanks': [],
}


def set_world(name, M):
    ob = bpy.data.objects[name]
    ob.matrix_basis = M


def follow(item, lens, light):
    """a lens and a light that belong to a moved item follow it"""
    ob = bpy.data.objects[item]
    d = ob.matrix_basis @ REST[item].inverted()
    if lens in bpy.data.objects and bpy.data.objects[lens].parent is None:   # a parented lens rides along by itself
        lo_ = bpy.data.objects[lens]
        lo_.matrix_world = d @ LENS_REST[lens]
    for l_ in lights:
        if l_.name == light:
            l_.matrix_world = d @ LIGHT_REST[light]


def pose_worklamp():
    """the inspection lamp hangs by its hook from the open engine cover, over the engine"""
    WL_R = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_4x4()
    hook = Vector((1.16, -0.05, 1.655 + LIFT))
    base = hook - Vector((0.02, 0, 0.30))
    set_world('WorkLamp', Matrix.Translation(base) @ WL_R.inverted())
    follow('WorkLamp', 'Lens_WorkLamp', 'L_WorkLamp')


def pose_crank():
    ob = bpy.data.objects['CrankHandle']
    W = Matrix([ob['working'][i * 4:i * 4 + 4] for i in range(4)])
    set_world('CrankHandle', Matrix.Translation((0, 0, LIFT)) @ W)


def pose_snow():
    rest = REST['SandLadder_1'].to_translation()
    set_world('SandLadder_1', Matrix.Translation(Vector((1.90, 0.83, 0.016)) - rest) @ REST['SandLadder_1'])
    d_old = Vector((0.64, -0.60, 0)).normalized()
    R_old = Matrix((d_old, Vector((0, 0, 1)).cross(d_old), Vector((0, 0, 1)))).transposed().to_4x4()
    tip_old = Vector((-1.62, 0.70, 2.212 + LIFT))
    a = Vector((0.16, -0.10, 1.0)).normalized()
    side = Vector((0.6, 1.0, 0.0))
    side = (side - a * side.dot(a)).normalized()
    R_new = Matrix((a, side, a.cross(side))).transposed().to_4x4()
    tip_new = Vector((2.75, 1.55, -0.10))
    set_world('Shovel', Matrix.Translation(tip_new) @ R_new @ R_old.inverted() @ Matrix.Translation(-tip_old) @ REST['Shovel'])
    pose('Winch_Clutch', 60)
    set_world('Winch_Hook', Matrix.Translation(Vector((0.85, 0.75, -0.62))) @ REST['Winch_Hook'])


ALL_OPEN2 = ALL_OPEN + [('Lock_doorL', 0.008)]
POSES.update({
    'toolkit': [('ToolBox_Lid', 88), ('M:Tool_PlugSpanner', (0.0, 0.0, 0.0))],
    'jack': [('Jack_Ram', 0.06)],
    'crank': [('CrankHole_Flap', 92), ('CRANK', None), ('Winch_Clutch', 60)],
    'worklamp': [('doorP', 70), ('EngineCover', 85), ('WORKLAMP', None)],
    'mirror': [],
    'lock': [('Lock_doorL', 0.008)],
    'curtains': [(f'Curtain_R{k}{t}', CON['parts'][f'Curtain_R{k}{t}']['range'][1]) for k in (1, 2, 3) for t in 'AB'
                 if f'Curtain_R{k}{t}' in CON['parts']],
    'heater': [('Toggle_Head', 57.6), ('Toggle_Cabin', 57.6), ('Toggle_Stove', 57.6), ('Heater_Temp', 0.05),
               ('Heater_Fan', 0.0338), ('Heater_Air', 90), ('Socket_12V_Cap', 95)],
    'frost': [('Wiper_L', 42), ('Wiper_R', 42)],
    'fog_night': [('Toggle_Fog', 57.6)],
    'snow': [('SNOW', None)],
    'wheel_change': [('WHEELCHANGE', None)],
    'chains': [('M:ChainBag', (0.18, 1.81, -0.916 - LIFT))],
    'snow_cover': [('Wiper_L', 0), ('Wiper_R', 0)],
    'cold_start': [('COLDSTART', None)],
    'stove_open': [('StoveDoor', 105), ('Stove_AshPan', 0.10), ('StoveDoor_Vent', 0.03), ('Stove_Damper', 0), ('STOVE', None)],
    'radio_glovebox': [('doorP', 70), ('RADIO', None)],
    'cab_window': [('Window_doorL', 0.30), ('Horn_Button', 0.005)],
    'fog_windows': [],
    'colliders': [],
    'points_plan': [],
})


# ---------------------------------------------------------------- phase 2: wheel change, snow, cold start, stove, radio
OPTIONAL = [o for o in bpy.data.objects if o.name.startswith(('Snow_', 'Chains_'))]
COLS = [o for o in bpy.data.objects if o.name.startswith('COL_')]
SHOW = {'snow_cover': ('Snow_',), 'chains': ('Chains_RL', 'Chains_RR')}


def place(name, M):
    """world matrix for any object, parented or not (the parent chain is evaluated first)"""
    bpy.context.view_layer.update()
    bpy.data.objects[name].matrix_world = M


def pose_wheel_change():
    jp = Vector(CON['sockets']['Jack_Point_FL']['pos'])
    place('Jack', Matrix.Translation((jp.x, jp.y, 0.0)))
    pose('Jack_Ram', 0.06)                                      # pumped a little ...
    pose('Jack_Screw', max(0.0, min(0.10, jp.z - 0.242 - 0.06)))  # ... the screw turned up to the axle
    place('Wheel_FL', Matrix.Translation((1.72, 1.62, 0.1715)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    place('SpareWheel', Matrix.Translation((0.55, 1.42, 0.364)) @ Matrix.Rotation(math.radians(-25), 4, 'Z'))
    for i in range(6):
        nm = f'Wheel_FL_Nut_{i + 1}'
        if nm in bpy.data.objects:
            place(nm, Matrix.Translation((1.70 + 0.045 * i, 1.08, 0.0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    place('WheelBrace', Matrix.Translation((1.98, 1.22, 0.017)) @ Matrix.Rotation(math.radians(-20), 4, 'Z'))


def pose_cold_start():
    place('Blowtorch', Matrix.Translation((1.62, 0.22, 0.0)))
    pose('Blowtorch_Valve', 360)
    place('Kettle', Matrix.Translation((2.08, 0.62, 0.0)))
    pose('Engine_Drain', 90)
    pose('RadiatorHatch', 100)
    move('Radiator_Cap', (0.05, 0.0, 0.06))


def pose_stove():
    place('Log_1', Matrix.Translation((-1.64, 0.585, 0.716 + LIFT + 0.31)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
    move('Kettle', (0.0, 0.0, 0.0))


def _coil(p0, p1, r=0.011, turns=16, n=200):
    d = (p1 - p0)
    t = d.normalized()
    a = t.cross(Vector((0, 0, 1)))
    if a.length < 1e-3:
        a = t.cross(Vector((1, 0, 0)))
    a.normalize()
    b = t.cross(a)
    return [p0 + d * (i / (n - 1)) + (a * math.cos(2 * math.pi * turns * i / (n - 1)) +
                                       b * math.sin(2 * math.pi * turns * i / (n - 1))) * r for i in range(n)]


MIC_MOVE = Vector((-0.11, 0.03, -0.07))
_c0 = Vector(CON['sockets']['Radio_Cord_Radio']['pos'])
_c1 = Vector(CON['sockets']['Radio_Cord_Mic']['pos']) + MIC_MOVE
MIC_CORD = rope('Cord_Mic', _coil(_c0, _c1), 0.0035, (0.02, 0.02, 0.02))


def pose_radio():
    pose('Glovebox_Lid', 78)
    move('Radio_Mic', tuple(MIC_MOVE))


# fogged side windows with a hand print (preview): FOG UVs, T_Van_Fog alpha, one print from T_Van_Handprints
def _tile_image():
    """the top-left print of T_Van_Handprints as its own image (CLIP outside it)"""
    from PIL import Image as _I
    t_ = _I.open(os.path.join(P.HERE, 'tex', 'van3', 'T_Van_Handprints.png')).convert('RGBA')
    w_, h_ = t_.size
    path_ = os.path.join(OUT, '_hp_tile.png')
    t_.crop((0, 0, w_ // 2, h_ // 2)).save(path_)
    return bpy.data.images.load(path_)


fog_m = bpy.data.materials.new('M_Fog_Preview')
fog_m.use_nodes = True
_FN, _FK = fog_m.node_tree.nodes, fog_m.node_tree.links
for _n in list(_FN):
    if _n.type == 'BSDF_PRINCIPLED':
        _FN.remove(_n)
_fout = next(n_ for n_ in _FN if n_.type == 'OUTPUT_MATERIAL')
_fuv = _FN.new('ShaderNodeUVMap')
_fuv.uv_map = 'FOG'
_ftex = _FN.new('ShaderNodeTexImage')
_ftex.image = bpy.data.images.load(os.path.join(P.HERE, 'tex', 'van3', 'T_Van_Fog.png'))
_ftex.interpolation = 'Closest'
_FK.new(_fuv.outputs[0], _ftex.inputs[0])
_fgt = _FN.new('ShaderNodeMath')
_fgt.operation = 'GREATER_THAN'
_fgt.inputs[1].default_value = 0.06                                   # fog amount 0.94 (flat mask: 94 % misted)
_FK.new(_ftex.outputs['Alpha'], _fgt.inputs[0])
_map = _FN.new('ShaderNodeMapping')
_map.inputs['Scale'].default_value = (1 / 0.30, 1 / 0.64, 1.0)
_map.inputs['Location'].default_value = (0.5 - 0.40 / 0.30, 0.5 - 0.40 / 0.64, 0.0)
_FK.new(_fuv.outputs[0], _map.inputs[0])
_htex = _FN.new('ShaderNodeTexImage')
_htex.image = _tile_image()
_htex.interpolation = 'Closest'
_htex.extension = 'CLIP'
_FK.new(_map.outputs[0], _htex.inputs[0])
_hgt = _FN.new('ShaderNodeMath')
_hgt.operation = 'GREATER_THAN'
_hgt.inputs[1].default_value = 0.45
_FK.new(_htex.outputs['Alpha'], _hgt.inputs[0])
_inv = _FN.new('ShaderNodeMath')
_inv.operation = 'SUBTRACT'
_inv.inputs[0].default_value = 1.0
_FK.new(_hgt.outputs[0], _inv.inputs[1])
_fac = _FN.new('ShaderNodeMath')
_fac.operation = 'MULTIPLY'
_FK.new(_fgt.outputs[0], _fac.inputs[0])
_FK.new(_inv.outputs[0], _fac.inputs[1])
_gls = _FN.new('ShaderNodeBsdfGlass')
_gls.inputs['Roughness'].default_value = 0.04
_dif = _FN.new('ShaderNodeBsdfPrincipled')
_dif.inputs['Base Color'].default_value = (0.70, 0.73, 0.76, 1)
_dif.inputs['Roughness'].default_value = 0.8
_FK.new(_ftex.outputs['Color'], _dif.inputs['Base Color'])
_fmx = _FN.new('ShaderNodeMixShader')
_FK.new(_fgt.outputs[0], _fmx.inputs[0])
_FK.new(_gls.outputs[0], _fmx.inputs[1])
_FK.new(_dif.outputs[0], _fmx.inputs[2])
_wet = _FN.new('ShaderNodeBsdfPrincipled')                         # the print: wiped, wet, dark glass
_wet.inputs['Base Color'].default_value = (0.015, 0.017, 0.02, 1)
_wet.inputs['Roughness'].default_value = 0.08
_pm = _FN.new('ShaderNodeMath')
_pm.operation = 'MULTIPLY'
_FK.new(_fgt.outputs[0], _pm.inputs[0])
_FK.new(_hgt.outputs[0], _pm.inputs[1])
_fmx2 = _FN.new('ShaderNodeMixShader')
_FK.new(_pm.outputs[0], _fmx2.inputs[0])
_FK.new(_fmx.outputs[0], _fmx2.inputs[1])
_FK.new(_wet.outputs[0], _fmx2.inputs[2])
_FK.new(_fmx2.outputs[0], _fout.inputs['Surface'])
GLASS_SLOTS = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name != 'lob' and 'FOG' in o.data.uv_layers:
        for i_, m_ in enumerate(o.data.materials):
            if m_ and m_.name.startswith('M_PSX_Glass'):
                GLASS_SLOTS.append((o, i_, m_))

COL_MATS = {}
for nm_, colr_ in (('shell', (0.20, 0.42, 0.95)), ('door', (1.0, 0.50, 0.10)), ('inside', (0.20, 0.80, 0.30)),
                   ('top', (0.6, 0.6, 0.6))):
    m_ = bpy.data.materials.new('M_Col_' + nm_)
    m_.use_nodes = True
    pb_ = m_.node_tree.nodes['Principled BSDF']
    pb_.inputs['Base Color'].default_value = (*colr_, 1)
    pb_.inputs['Alpha'].default_value = 0.55
    pb_.inputs['Roughness'].default_value = 0.6
    COL_MATS[nm_] = m_


def col_group(name):
    n_ = name[4:]
    if n_.startswith(('door', 'dooZ', 'Ladder')):
        return 'door'
    if n_.startswith(('Arch', 'CabSeat', 'SeatBack', 'Table', 'Stove', 'WoodBox', 'Cargo', 'Extinguisher', 'BatteryBox', 'Dash')):
        return 'inside'
    if n_.startswith(('RoofRack', 'RoofLoad')):
        return 'top'
    return 'shell'


for o in COLS:
    o.data.materials.clear()
    o.data.materials.append(COL_MATS[col_group(o.name)])
    o.display_type = 'TEXTURED'
COL_HIDDEN = []
MARKERS = []
_mk_col = {'hide': (0.10, 0.85, 0.20), 'audio': (0.15, 0.45, 1.0), 'vfx': (0.0, 0.85, 0.85), 'knock': (0.95, 0.12, 0.10),
           'decal': (0.95, 0.12, 0.10), 'jack': (1.0, 0.85, 0.05), 'heat': (1.0, 0.45, 0.05)}
_mk_mats = {}
for k_, c_ in _mk_col.items():
    m_ = bpy.data.materials.new('M_Marker_' + k_)
    m_.use_nodes = True
    pb_ = m_.node_tree.nodes['Principled BSDF']
    pb_.inputs['Base Color'].default_value = (*c_, 1)
    pb_.inputs['Emission Color'].default_value = (*c_, 1)
    pb_.inputs['Emission Strength'].default_value = 2.0
    _mk_mats[k_] = m_
for n_, s_ in CON['sockets'].items():
    if s_['kind'] not in _mk_col:
        continue
    pos_ = s_.get('eye') if s_['kind'] == 'hide' else s_['pos']
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.065 if s_['kind'] == 'hide' else 0.045,
                                         location=tuple(pos_))
    mk_ = bpy.context.object
    mk_.name = 'MK_' + n_
    mk_.data.materials.append(_mk_mats[s_['kind']])
    mk_['scene_prop'] = 1
    mk_.hide_render = True
    MARKERS.append(mk_)


def phase2_visibility(view):
    """optional geometry by view; the colliders view shows only the boxes (roof boxes cut away) and the wheels"""
    for o in OPTIONAL:
        o.hide_render = not any(o.name.startswith(p_) for p_ in SHOW.get(view, ()))
    MIC_CORD.hide_render = view != 'radio_glovebox'
    for mk_ in MARKERS:
        mk_.hide_render = view != 'points_plan'
    for (o, i_, m_) in GLASS_SLOTS:
        o.data.materials[i_] = fog_m if view == 'fog_windows' else m_
    if view == 'colliders':
        for o in bpy.data.objects:
            if o.type == 'MESH' and not o.get('scene_prop'):
                show_ = (o.name.startswith('COL_') and not o.name.startswith('COL_Roof')) or o.name.startswith('Wheel_')
                if not show_ and not o.hide_render:
                    COL_HIDDEN.append(o)
                o.hide_render = not show_
    else:
        for o in COL_HIDDEN:
            o.hide_render = False
        COL_HIDDEN.clear()
        for o in COLS:
            o.hide_render = True


def apply_poses(view):
    reset_parts()
    for k_ in ('WorkLamp',):
        if k_ in REST:
            follow(k_, 'Lens_WorkLamp', 'L_WorkLamp')
    for k, v in POSES.get(view, []):
        if k == 'POUR':
            pour_pose(side=v)
        elif k == 'CRANK':
            pose_crank()
        elif k == 'WORKLAMP':
            pose_worklamp()
        elif k == 'SNOW':
            pose_snow()
        elif k == 'WHEELCHANGE':
            pose_wheel_change()
        elif k == 'COLDSTART':
            pose_cold_start()
        elif k == 'STOVE':
            pose_stove()
        elif k == 'RADIO':
            pose_radio()
        elif k.startswith('M:'):
            move(k[2:], v)
        elif k.startswith('H:'):
            bpy.data.objects[k[2:]].hide_render = True
        else:
            pose(k, v)


GROUPS = {
    'night': {'drive', 'int', 'spot'}, 'ingame': {'drive', 'int', 'spot'}, 'night_rear': {'drive', 'int', 'work', 'reverse'},
    'night_work': {'drive', 'int', 'work', 'spot'}, 'inside': {'int'}, 'stove': {'int'}, 'cab': {'int', 'drive'},
    'dash_night': {'int', 'drive'}, 'seats': {'int'}, 'lamps_front_night': {'drive', 'spot', 'work'},
    'lamps_rear_night': {'drive', 'work', 'reverse'}, 'domes': {'int'}, 'front_night': {'drive', 'spot', 'int'}, 'lightbar': {'drive', 'work', 'int'},
    'beams': {'drive', 'spot', 'int'},
    'fold0': {'int'}, 'fold50': {'int'}, 'fold100': {'int'}, 'wall': {'drive'}, 'wall_all': {'drive', 'spot', 'work'},
    'battery': {'int'}, 'toolkit': {'int'}, 'jack': {'int'}, 'worklamp': {'hand'}, 'mirror': {'int'},
    'curtains': {'int'}, 'fog_night': {'drive', 'fog', 'int'}, 'stove_open': {'int'},
}
NIGHT = set(GROUPS)
FOLDS = {'inside': {'R1': 1, 'R2': 1}, 'stove': {'R1': 1, 'R2': 1}, 'seats': {'R1': 1, 'R2': 0.0, 'L4': 1},
         'plan': {'R1': 1, 'R2': 1}, 'fold0': {'R1': 1, 'R2': 1}, 'fold50': {'L2': 0.5, 'R1': 1, 'R2': 1},
         'fold100': {'L2': 1, 'R1': 1, 'R2': 1}, 'battery': {'L4': 1, 'R2': 1}, 'toolkit': {'R2': 1},
         'jack': {'L2': 1}, 'curtains': {'L1': 1, 'L2': 1}}
EXPOSURE = {'dash': 0.4, 'cab': 0.6, 'fold0': 0.3, 'fold50': 0.3, 'fold100': 0.3, 'battery': 0.8, 'engine_closed': 0.3,
            'engine_open': 0.3, 'engine_top': 0.2, 'fusebox': 0.5, 'controls': 0.5, 'dash_controls': 0.3, 'roofhatch_in': 0.2,
            'tanks': 0.2, 'toolkit': 0.9, 'jack': 0.9, 'worklamp': 0.6, 'mirror': 1.4, 'curtains': 0.6, 'lock': 0.5,
            'heater': 0.3, 'stove_open': 0.5, 'radio_glovebox': 0.4, 'cab_window': 0.3, 'cold_start': 0.3}


def state(view):
    night = view in NIGHT
    on = GROUPS.get(view, set())
    for l in lights:
        l.hide_render = not (night and l['group'] in on)
    for lev_, grp_ in lens_levels:
        lev_.outputs[0].default_value = 1.0 if (night and grp_ in on) else 0.0
    set_atmosphere(ATMOS.get(view, 0.0))
    plan_light.hide_render = view not in ('plan', 'points_plan')
    fill.hide_render = view != 'dash'
    CORD.hide_render = view != 'worklamp'
    CABLE.hide_render = view != 'snow'
    GHOST.hide_render = view != 'mirror'
    for n_ in ('L_Dome_Cab', 'L_Night_Red', 'L_lamp'):             # mirror: the cab dark, the saloon lit by the domes
        if view == 'mirror' and n_ in bpy.data.objects:
            bpy.data.objects[n_].hide_render = True
    _lob.data.materials.clear()
    for m_ in ([frost_m] if view in FROST_VIEWS else _lob_mats):
        _lob.data.materials.append(m_)
    fill2.hide_render = view not in FILLS
    if view in FILLS:
        fl_, ft_, fe_, fs_ = FILLS[view]
        fill2.location = fl_
        fill2.rotation_euler = (Vector(ft_) - Vector(fl_)).to_track_quat('-Z', 'Y').to_euler()
        fill2.data.energy, fill2.data.size = fe_, fs_
    apply_poses(view)
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith(('Sun', 'Moon'))]:
        bpy.data.objects.remove(o, do_unlink=True)
    if night:
        P.world((0.010, 0.013, 0.026), 1.0)
        m = P.sun(0.16, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    else:
        P.world((0.56, 0.62, 0.72), 0.9)
        P.sun(3.4, (52, 0, 30))
    outside_night = view in ('night', 'ingame', 'night_rear', 'night_work', 'front_night', 'lamps_rear_night', 'lamps_front_night', 'beams', 'lightbar', 'fog_night')
    for m in glass:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = (m.get('glow', 0.35) if outside_night else 0.0)
    for m in emit_mats:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        grp = m.get('group')
        if grp is not None:
            lit = night and LENS_GROUP.get(grp, 'int') in on and not (view == 'mirror' and grp == 'night')
        else:
            lit = night
        pb.inputs['Emission Strength'].default_value = m['night_emit'] if lit else m.get('day_emit', 0.0)
    trees.hide_render = not night
    wall.hide_render = not view.startswith('wall')
    body.hide_render = head.hide_render = view != 'side'
    for tag in ('L1', 'L2', 'L3', 'L4', 'R1', 'R2'):
        if 'Seat_' + tag in seats:
            fold(tag, FOLDS.get(view, {}).get(tag, 0.0))
    phase2_visibility(view)


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
    'points_plan': ((0.0, 0.0, 3.0 + Z), Vector((0.0, 0.0001, 0.0)), 30, 4.75),
    'doors': ((cx + 1.0 * L, -0.85 * L, 0.36 * L), c, 40, None),
    'doors_rear': ((cx - 1.0 * L, -0.85 * L, 0.38 * L), c, 38, None),
    'engine_closed': ((1.72, -0.48, 1.50 + Z), Vector((1.15, 0.02, 0.86 + Z)), 16, None),
    'engine_open': ((1.72, -0.48, 1.50 + Z), Vector((1.15, 0.02, 0.86 + Z)), 16, None),
    'engine_top': ((1.52, -0.40, 1.70 + Z), Vector((1.17, 0.02, 0.76 + Z)), 17, None),
    'radiator': ((2.95, -0.25, 1.70), Vector((2.18, 0.0, 1.22)), 36, None),
    'battery': ((0.60, 0.10, 1.62 + Z), Vector((0.39, 0.72, 0.84 + Z)), 22, None),
    'fusebox': ((1.36, -0.62, 1.20 + Z), Vector((1.70, -0.30, 0.99 + Z)), 26, None),
    'controls': ((1.42, 1.05, 1.30 + Z), Vector((1.80, 0.45, 0.88 + Z)), 18, None),
    'dash_controls': ((1.45, 0.20, 1.32 + Z), Vector((1.75, 0.34, 1.10 + Z)), 30, None),
    'fuel': ((-0.45, 1.60, 1.15), Vector((0.15, 0.98, 0.90)), 34, None),
    'fuel_pour': ((1.45, 2.65, 1.70), Vector((0.20, 1.20, 0.98)), 30, None),
    'tanks': ((0.25, 2.30, 0.16), Vector((0.25, 0.30, 0.46)), 24, None),
    'roofhatch': ((-2.55, -1.95, 3.70), Vector((-0.85, -0.05, 2.20)), 30, None),
    'roofhatch_in': ((0.25, -0.55, 1.35 + Z), Vector((-0.43, -0.40, 2.02 + Z)), 20, None),
    'wheel': ((1.5, -2.05, 0.62), Vector((1.207, -0.85, 0.36)), 35, None),
    'toolkit': ((0.47, -0.18, 1.30 + Z), Vector((0.63, -0.77, 0.80 + Z)), 26, None),
    'jack': ((-0.58, -0.15, 1.30 + Z), Vector((-0.62, 0.76, 0.84 + Z)), 28, None),
    'crank': ((3.55, 0.95, 0.78), Vector((2.30, 0.0, 0.50)), 30, None),
    'worklamp': ((1.52, -0.40, 1.70 + Z), Vector((1.17, 0.0, 0.80 + Z)), 17, None),
    'mirror': ((1.15, 0.53, 1.77 + Z), Vector((1.57, 0.0, 1.79 + Z)), 50, None),
    'lock': ((1.13, 0.05, 1.62 + Z), Vector((1.31, 0.84, 1.33 + Z)), 32, None),
    'curtains': ((-1.75, 0.55, 1.55 + Z), Vector((-0.15, -0.88, 1.55 + Z)), 20, None),
    'heater': ((1.40, 0.07, 1.33 + Z), Vector((1.76, 0.0, 1.17 + Z)), 32, None),
    'frost': ((2.95, 1.05, 2.15), Vector((1.80, 0.0, 1.62)), 34, None),
    'fog_night': ((cx + 1.15 * L, 0.85 * L, 1.25), Vector((cx + 0.12 * L, 0.0, 1.00)), 28, None),
    'snow': ((3.6, 2.9, 1.35), Vector((2.0, 0.55, 0.30)), 28, None),
    'wheel_change': ((3.15, 2.75, 1.10), Vector((1.30, 0.95, 0.30)), 28, None),
    'chains': ((-0.30, 2.25, 0.80), Vector((-1.10, 0.86, 0.32)), 30, None),
    'snow_cover': ((4.4, 3.1, 3.4), Vector((0.55, 0.0, 1.55)), 30, None),
    'cold_start': ((2.85, 1.20, 0.50), Vector((1.40, 0.18, 0.30)), 26, None),
    'stove_open': ((-1.24, 0.30, 1.48 + Z), Vector((-1.80, 0.60, 1.00 + Z)), 24, None),
    'radio_glovebox': ((1.28, -0.20, 1.48 + Z), Vector((1.82, -0.40, 1.20 + Z)), 26, None),
    'cab_window': ((1.12, -0.25, 1.66 + Z), Vector((1.52, 0.82, 1.52 + Z)), 24, None),
    'fog_windows': ((-0.55, 3.10, 1.62), Vector((-0.55, 0.90, 1.58)), 30, None),
    'colliders': ((cx + 1.05 * L, 0.90 * L, 0.80 * L), Vector((cx, 0, lo[2] + 0.30 * H)), 30, None),
}
P.setup_cycles((900, 600), spp)
sc.cycles.sample_clamp_indirect = 10.0
BLOOM = {'domes': 0.18, 'inside': 0.15, 'stove': 0.15, 'seats': 0.15, 'dash_night': 0.2, 'fold0': 0.12, 'fold50': 0.12,
         'fold100': 0.12, 'battery': 0.12, 'toolkit': 0.12, 'jack': 0.12, 'worklamp': 0.2, 'mirror': 0.15,
         'curtains': 0.15, 'fog_night': 0.3}
ims = sc.render.image_settings
import subprocess
for v in views:
    state(v)
    loc, tgt, lens, ortho = CAMS[v]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    sc.render.resolution_x, sc.render.resolution_y = (427, 240) if v == 'ingame' else (900, 600)
    if v in ('plan', 'points_plan'):
        sc.render.resolution_x, sc.render.resolution_y = 900, 450
    interior = v in ('inside', 'stove', 'seats', 'cab', 'dash', 'dash_night', 'domes', 'plan', 'fold0', 'fold50', 'fold100',
                     'battery', 'engine_closed', 'engine_open', 'engine_top', 'fusebox', 'controls', 'dash_controls',
                     'roofhatch_in', 'toolkit', 'jack', 'worklamp', 'mirror', 'lock', 'curtains', 'heater',
                     'stove_open', 'radio_glovebox', 'cab_window')
    sc.cycles.samples = spp * (2 if interior else 1)
    sc.camera.data.clip_start = (1.20 if v in ('plan', 'points_plan') else 0.02)
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
