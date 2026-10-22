"""Utility Plane v11 - Blender light rig with IES profiles and light functions (Cycles).

Opens the v10 scene (UtilityPlane_v10.blend, same folder layout as on the PC so relative texture paths stay valid),
adds:
  - 14 lamps as point lights on their sockets, each shaped by its IES profile (IES/<key>.ies, embedded as text) and
    driven by light-function node groups (LF_*): filament (level -> brightness and colour temperature), xenon strobe
    double flash, rotating beacon (rotates the IES lookup), fluorescent strike, horror flicker, landing-lens gobo;
  - lens materials that read the same IES and light functions in the direction of the viewer (a lamp looks bright
    only from where it shines; the beacon lens flashes when the fan passes the camera);
  - panel backlight and displays as in the URP previews;
  - night world with a volumetric fog (scene property "atmosphere", same meaning as UtilityPlaneRig.atmosphere),
    moon, snow ground, preview cameras and figures;
and parks the plane (UtilityPlaneRig.ParkedPose). Saved as UtilityPlane_v11_lights.blend.
python3 build_lights_v11.py"""
import bpy, json, math, os
import numpy as np
from mathutils import Matrix, Vector

BASE = '/home/claude/plane/v11/deliv/UtilityPlane_Unity_v11/Blender/'
SRC = BASE + 'UtilityPlane_v11.blend'          # the v11 model (v10 + panel flood lamps)
OUT = BASE + 'UtilityPlane_v11_lights.blend'
IES = '/home/claude/plane/v11/blender/IES/'
meta = json.load(open(IES + 'lights_meta.json'))
views = json.load(open('/home/claude/plane/v11/prev/views.json'))

bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
vl = sc.view_layers[0]
PI = math.pi

# ---------------------------------------------------------------- frames
M = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])          # Blender -> Unity:  u = M b ;  b = M.T u


def conv(v):
    return M.T @ np.asarray(v, float)


def u2b(v):
    return Vector(conv(v).tolist())


def m4(R, t):
    m = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            m[i][j] = float(R[i][j])
        m[i][3] = float(t[i])
    return m


# ---------------------------------------------------------------- collections
def new_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or sc.collection).children.link(c)
    return c


def layer_coll(coll, lc=None):
    lc = lc or vl.layer_collection
    if lc.collection == coll:
        return lc
    for ch in lc.children:
        r = layer_coll(coll, ch)
        if r:
            return r
    return None


for cname in ('Winter kit 1.2 - installed (WinterKit)', 'Separate models (own FBX, laid out beside the plane)'):
    c = bpy.data.collections.get(cname)
    if c:
        c.hide_render = True
        lc = layer_coll(c)
        if lc:
            lc.hide_viewport = True
hidden_glass = []
for ob in bpy.data.objects:
    if ob.type == 'MESH' and (ob.name in ('Glass',) or ob.name.endswith('_Glass')):
        ob.hide_render = True
        hidden_glass.append(ob.name)

C_LIGHTS = new_coll('Lights v11 - IES + light functions')
C_FILL = new_coll('Fill lights (URP stand-ins for bounce, off in Cycles)', C_LIGHTS)
C_PREV = new_coll('Preview v11 - moon, snow, cameras')
C_FIG = new_coll('Preview figures', C_PREV)

# ---------------------------------------------------------------- time
sc.render.fps = 24
sc.frame_start, sc.frame_end = 1, 126                                # 5.25 s = 5 strobe periods
sc['lf_time_offset'] = 0.0
sc['atmosphere'] = 0.35
sc['lf_flicker'] = 0.0


def add_time_driver(sock_owner, data_path, expr='frame / fps + t0'):
    fc = sock_owner.driver_add(data_path)
    d = fc.driver
    d.type = 'SCRIPTED'
    v = d.variables.new(); v.name = 'fps'; v.type = 'SINGLE_PROP'
    v.targets[0].id_type = 'SCENE'; v.targets[0].id = sc; v.targets[0].data_path = 'render.fps'
    v = d.variables.new(); v.name = 't0'; v.type = 'SINGLE_PROP'
    v.targets[0].id_type = 'SCENE'; v.targets[0].id = sc; v.targets[0].data_path = '["lf_time_offset"]'
    d.expression = expr
    return fc


def add_scene_prop_driver(owner, data_path, prop, expr):
    fc = owner.driver_add(data_path)
    d = fc.driver
    d.type = 'SCRIPTED'
    v = d.variables.new(); v.name = 'p'; v.type = 'SINGLE_PROP'
    v.targets[0].id_type = 'SCENE'; v.targets[0].id = sc; v.targets[0].data_path = '["%s"]' % prop
    d.expression = expr
    return fc


# ---------------------------------------------------------------- light-function node groups
def group(name, inputs, outputs):
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    for n, t, dv in inputs:
        s = g.interface.new_socket(n, in_out='INPUT', socket_type=t)
        if dv is not None:
            s.default_value = dv
    for n, t in outputs:
        g.interface.new_socket(n, in_out='OUTPUT', socket_type=t)
    gi = g.nodes.new('NodeGroupInput'); go = g.nodes.new('NodeGroupOutput')
    gi.location = (-900, 0); go.location = (900, 0)
    return g, gi, go


def mix_rgb(nodes):
    mx = nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    a = [x for x in mx.inputs if x.name == 'A' and x.type == 'RGBA'][0]
    b_ = [x for x in mx.inputs if x.name == 'B' and x.type == 'RGBA'][0]
    o = [x for x in mx.outputs if x.type == 'RGBA'][0]
    return mx, a, b_, o


class B:
    """tiny builder for math nodes inside a group"""
    def __init__(self, g):
        self.g, self.N, self.L, self.x = g, g.nodes, g.links, -600

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        n.location = (self.x, 0); self.x += 40
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = float(v)
            else:
                self.L.new(v, n.inputs[i])
        return n.outputs[0]

    def noise1(self, w):
        n = self.N.new('ShaderNodeTexWhiteNoise'); n.noise_dimensions = '1D'
        self.L.new(w, n.inputs['W'])
        return n.outputs['Value']


# LF_Filament: level 0..1 -> strength (filament output ~ level) and colour (T = T0 * level^0.2), like UtilityPlaneRig
g, gi, go = group('LF_Filament', [('Level', 'NodeSocketFloat', 1.0), ('T0', 'NodeSocketFloat', 3000.0),
                                  ('Filter', 'NodeSocketColor', (1, 1, 1, 1))], [('Strength', 'NodeSocketFloat'), ('Color', 'NodeSocketColor')])
b = B(g)
lv = b.math('MAXIMUM', gi.outputs['Level'], 0.0)
tk = b.math('MULTIPLY', gi.outputs['T0'], b.math('POWER', lv, 0.2))
bb = g.nodes.new('ShaderNodeBlackbody'); g.links.new(tk, bb.inputs['Temperature'])
sep = g.nodes.new('ShaderNodeSeparateColor'); g.links.new(bb.outputs['Color'], sep.inputs['Color'])
mx = b.math('MAXIMUM', b.math('MAXIMUM', sep.outputs[0], sep.outputs[1]), sep.outputs[2])
inv = b.math('DIVIDE', 1.0, b.math('MAXIMUM', mx, 1e-6))
mul1, ma, mb, mo_ = mix_rgb(g.nodes)
g.links.new(bb.outputs['Color'], ma); g.links.new(gi.outputs['Filter'], mb)
sc1 = g.nodes.new('ShaderNodeVectorMath'); sc1.operation = 'SCALE'
g.links.new(mo_, sc1.inputs[0]); g.links.new(inv, sc1.inputs['Scale'])
g.links.new(lv, go.inputs['Strength']); g.links.new(sc1.outputs['Vector'], go.inputs['Color'])
LF_FIL = g

# LF_Strobe: xenon double flash (0.12 s apart) every Period s; each flash exp(-t/25 ms), cut at 90 ms
g, gi, go = group('LF_Strobe', [('Time', 'NodeSocketFloat', 0.0), ('Period', 'NodeSocketFloat', 1.05),
                                ('Gap', 'NodeSocketFloat', 0.12), ('Level', 'NodeSocketFloat', 1.0)], [('Strength', 'NodeSocketFloat')])
b = B(g)
t1 = b.math('FLOORED_MODULO', gi.outputs['Time'], gi.outputs['Period'])


def env(a):
    on = b.math('MULTIPLY', b.math('GREATER_THAN', a, -1e-6), b.math('LESS_THAN', a, 0.09))
    return b.math('MULTIPLY', on, b.math('EXPONENT', b.math('DIVIDE', b.math('MULTIPLY', a, -1.0), 0.025)))


e1 = env(t1)
e2 = b.math('MULTIPLY', env(b.math('SUBTRACT', t1, gi.outputs['Gap'])), b.math('GREATER_THAN', gi.outputs['Level'], 0.5))
on = b.math('GREATER_THAN', gi.outputs['Level'], 0.25)
g.links.new(b.math('MULTIPLY', b.math('MAXIMUM', e1, e2), on), go.inputs['Strength'])
LF_STROBE = g

# LF_Flicker: the same law as UtilityPlaneRig.FlickerMultiplier (60 ms cells, random drops, slow bus sag)
g, gi, go = group('LF_Flicker', [('Time', 'NodeSocketFloat', 0.0), ('Amount', 'NodeSocketFloat', 0.0),
                                 ('Seed', 'NodeSocketFloat', 0.0), ('Circuit', 'NodeSocketFloat', 0.0)], [('Multiplier', 'NodeSocketFloat')])
b = B(g)
slot = b.math('FLOOR', b.math('DIVIDE', gi.outputs['Time'], 0.06))
w1 = b.math('ADD', b.math('MULTIPLY', slot, 3.0), b.math('ADD', b.math('MULTIPLY', gi.outputs['Seed'], 7919.0), b.math('MULTIPLY', gi.outputs['Circuit'], 1013.0)))
w2 = b.math('ADD', b.math('MULTIPLY', slot, 11.0), b.math('ADD', b.math('ADD', gi.outputs['Seed'], 1.0), b.math('MULTIPLY', gi.outputs['Circuit'], 389.0)))
r1, r2 = b.noise1(w1), b.noise1(w2)
thr = b.math('ADD', 0.04, b.math('MULTIPLY', gi.outputs['Amount'], 0.42))
drop = b.math('MULTIPLY', b.math('LESS_THAN', r1, thr), b.math('ADD', 0.35, b.math('MULTIPLY', r2, 0.65)))
sag = b.math('ADD', 0.5, b.math('MULTIPLY', 0.5, b.math('MULTIPLY', b.math('SINE', b.math('MULTIPLY', gi.outputs['Time'], 7.3)),
                                                         b.math('SINE', b.math('ADD', b.math('MULTIPLY', gi.outputs['Time'], 2.1), 1.0)))))
k = b.math('ADD', drop, b.math('MULTIPLY', sag, 0.18))
g.links.new(b.math('SUBTRACT', 1.0, b.math('MULTIPLY', gi.outputs['Amount'], k), clamp=True), go.inputs['Multiplier'])
LF_FLICK = g

# LF_Fluorescent: strike flicker for StrikeTime s after OnTime, then steady; unstable below 75 %, dark below 45 %
g, gi, go = group('LF_Fluorescent', [('Time', 'NodeSocketFloat', 0.0), ('OnTime', 'NodeSocketFloat', -10.0),
                                     ('StrikeTime', 'NodeSocketFloat', 0.8), ('Level', 'NodeSocketFloat', 1.0)], [('Strength', 'NodeSocketFloat')])
b = B(g)
a = b.math('SUBTRACT', gi.outputs['Time'], gi.outputs['OnTime'])
cell = b.math('FLOOR', b.math('DIVIDE', a, 0.07))
blink = b.math('MULTIPLY', b.math('GREATER_THAN', b.noise1(cell), 0.45), b.math('ADD', 0.4, b.math('MULTIPLY', b.noise1(b.math('ADD', cell, 77.0)), 0.6)))
striking = b.math('MULTIPLY', b.math('GREATER_THAN', a, 0.0), b.math('LESS_THAN', a, gi.outputs['StrikeTime']))
lit = b.math('GREATER_THAN', a, gi.outputs['StrikeTime'])
cell2 = b.math('FLOOR', b.math('DIVIDE', gi.outputs['Time'], 0.09))
unstable = b.math('LESS_THAN', gi.outputs['Level'], 0.75)
drop = b.math('MULTIPLY', unstable, b.math('LESS_THAN', b.noise1(b.math('ADD', cell2, 911.0)), 0.25))
steady = b.math('MULTIPLY', b.math('ADD', 0.9, b.math('MULTIPLY', gi.outputs['Level'], 0.1)), b.math('SUBTRACT', 1.0, drop))
steady = b.math('MULTIPLY', steady, b.math('GREATER_THAN', gi.outputs['Level'], 0.45))
g.links.new(b.math('ADD', b.math('MULTIPLY', striking, blink), b.math('MULTIPLY', lit, steady)), go.inputs['Strength'])
LF_FLUO = g

# LF_BeaconRotate: rotates the IES lookup about the plane's up axis: heading = Phase + RPM*6*sqrt(Level)*Time (deg)
g, gi, go = group('LF_BeaconRotate', [('Vector', 'NodeSocketVector', (0, 0, -1)), ('Time', 'NodeSocketFloat', 0.0),
                                      ('RPM', 'NodeSocketFloat', 45.0), ('Level', 'NodeSocketFloat', 1.0),
                                      ('Phase', 'NodeSocketFloat', 0.0), ('Axis', 'NodeSocketVector', (0, 1, 0))], [('Vector', 'NodeSocketVector')])
b = B(g)
rate = b.math('MULTIPLY', b.math('MULTIPLY', gi.outputs['RPM'], 6.0), b.math('SQRT', b.math('MAXIMUM', gi.outputs['Level'], 0.0)))
head = b.math('ADD', gi.outputs['Phase'], b.math('MULTIPLY', rate, gi.outputs['Time']))
vr = g.nodes.new('ShaderNodeVectorRotate'); vr.rotation_type = 'AXIS_ANGLE'
g.links.new(gi.outputs['Vector'], vr.inputs['Vector']); g.links.new(gi.outputs['Axis'], vr.inputs['Axis'])
g.links.new(b.math('RADIANS', head), vr.inputs['Angle'])
g.links.new(vr.outputs['Vector'], go.inputs['Vector'])
LF_BEACON = g

# LF_LensGobo: projected noise across the beam (dirty lens / reflector facets), +-Amount around 1
g, gi, go = group('LF_LensGobo', [('Vector', 'NodeSocketVector', (0, 0, -1)), ('Amount', 'NodeSocketFloat', 0.12),
                                  ('Scale', 'NodeSocketFloat', 9.0)], [('Multiplier', 'NodeSocketFloat')])
b = B(g)
sp = g.nodes.new('ShaderNodeSeparateXYZ'); g.links.new(gi.outputs['Vector'], sp.inputs[0])
den = b.math('MAXIMUM', b.math('MULTIPLY', sp.outputs['Z'], -1.0), 0.05)
cx = b.math('MULTIPLY', b.math('DIVIDE', sp.outputs['X'], den), gi.outputs['Scale'])
cy = b.math('MULTIPLY', b.math('DIVIDE', sp.outputs['Y'], den), gi.outputs['Scale'])
cxyz = g.nodes.new('ShaderNodeCombineXYZ'); g.links.new(cx, cxyz.inputs['X']); g.links.new(cy, cxyz.inputs['Y'])
nz = g.nodes.new('ShaderNodeTexNoise'); nz.noise_dimensions = '3D'
nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 4.0; nz.inputs['Roughness'].default_value = 0.55
g.links.new(cxyz.outputs[0], nz.inputs['Vector'])
dev = b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs['Fac'], 0.5), 2.0)
g.links.new(b.math('ADD', 1.0, b.math('MULTIPLY', dev, gi.outputs['Amount'])), go.inputs['Multiplier'])
LF_GOBO = g

# ---------------------------------------------------------------- per-lamp settings
RADIUS = {'Nav_L': 0.015, 'Nav_R': 0.015, 'Nav_Tail': 0.015, 'Strobe_L': 0.012, 'Strobe_R': 0.012, 'Beacon_Top': 0.02,
          'Beacon_Bottom': 0.025, 'Landing': 0.05, 'Dome_L': 0.02, 'Dome_R': 0.02, 'Cargo': 0.06, 'Cargo_2': 0.06,
          'Flood': 0.006, 'Flood_2': 0.006, 'Fill_Cockpit': 0.3, 'Fill_Bay': 0.4}
EXTRA_UP = {'Beacon_Top': 0.03}             # lamp 3 cm higher than the socket: inside the lens, clear of the fin cap
CIRCUIT = {'nav': 0, 'strobe': 1, 'beacon': 2, 'landing': 3, 'cabin': 4, 'cargo': 5, 'flood': 6}
SHADOW_FREE = {'Nav_L': ['Body'], 'Nav_R': ['Body'], 'Strobe_L': ['Body'], 'Strobe_R': ['Body']}   # lamp sits in the tip fairing
LENS_OF = {'Nav_L': 'Lens_Nav_L', 'Nav_R': 'Lens_Nav_R', 'Nav_Tail': 'Lens_Nav_Tail', 'Strobe_L': 'Lens_Strobe_L',
           'Strobe_R': 'Lens_Strobe_R', 'Beacon_Top': 'Lens_Beacon_Top', 'Beacon_Bottom': 'Lens_Beacon_Bottom',
           'Landing': 'Lens_Landing', 'Flood': 'Lens_Flood_L', 'Flood_2': 'Lens_Flood_R'}
BEACON_PHASE = {'Beacon_Top': 150.0, 'Beacon_Bottom': -120.0}       # heading at t = 0, as in the URP previews

ies_texts = {}
for key, m in meta.items():
    if m['peak_cd'] is None:
        continue
    t = bpy.data.texts.new('IES_%s.ies' % key)
    t.from_string(open(IES + key + '.ies').read())
    ies_texts[key] = t

LIGHT_OBJ, LIGHT_RB, UP_LOCAL = {}, {}, {}


LENS_FLOOR = {'Nav_L': 0.06, 'Nav_R': 0.06, 'Nav_Tail': 0.06, 'Strobe_L': 0.04, 'Strobe_R': 0.04, 'Beacon_Top': 0.05,
              'Beacon_Bottom': 0.05, 'Landing': 0.015, 'Flood': 0.06, 'Flood_2': 0.06}          # the lens glows a little from every side (light inside the dome)


def lf_chain(nt, key, m, vec_out, floor=None):
    """builds the light-function chain in node tree nt; vec_out = lamp-local direction socket.
    returns (strength socket, colour socket)."""
    N, Lk = nt.nodes, nt.links
    x0 = -1400
    tv = N.new('ShaderNodeValue'); tv.name = tv.label = 'Time (s)'; tv.location = (x0, 300)
    add_time_driver(tv.outputs[0], 'default_value')
    lev = N.new('ShaderNodeValue'); lev.name = lev.label = 'Level (switch / dimmer 0..1)'; lev.location = (x0, 150)
    lev.outputs[0].default_value = 1.0
    vec = vec_out
    if m['rotates']:
        br = N.new('ShaderNodeGroup'); br.node_tree = LF_BEACON; br.location = (x0 + 250, 0); br.label = 'LF_BeaconRotate'
        Lk.new(vec, br.inputs['Vector']); Lk.new(tv.outputs[0], br.inputs['Time']); Lk.new(lev.outputs[0], br.inputs['Level'])
        br.inputs['Phase'].default_value = BEACON_PHASE[key]
        br.inputs['Axis'].default_value = UP_LOCAL[key]
        vec = br.outputs['Vector']
    ies = N.new('ShaderNodeTexIES'); ies.mode = 'INTERNAL'; ies.ies = ies_texts[key]; ies.location = (x0 + 500, 0)
    ies.label = 'IES %s' % key
    Lk.new(vec, ies.inputs['Vector'])
    norm = N.new('ShaderNodeMath'); norm.operation = 'MULTIPLY'; norm.location = (x0 + 700, 0); norm.label = 'IES peak -> 1'
    Lk.new(ies.outputs['Fac'], norm.inputs[0]); norm.inputs[1].default_value = m['k_norm']
    s = norm.outputs[0]
    if floor is not None:                                         # lens: floor + (1 - floor) * pattern
        fm_ = N.new('ShaderNodeMath'); fm_.operation = 'MULTIPLY_ADD'; fm_.location = (x0 + 800, 100); fm_.label = 'lens glow floor'
        Lk.new(s, fm_.inputs[0]); fm_.inputs[1].default_value = 1.0 - floor; fm_.inputs[2].default_value = floor
        s = fm_.outputs[0]
    fl = N.new('ShaderNodeGroup'); fl.node_tree = LF_FLICK; fl.location = (x0 + 500, -300); fl.label = 'LF_Flicker'
    Lk.new(tv.outputs[0], fl.inputs['Time']); fl.inputs['Circuit'].default_value = CIRCUIT[m['group']]
    add_scene_prop_driver(fl.inputs['Amount'], 'default_value', 'lf_flicker', 'p')
    if m['kind'] == 'incandescent':
        fil = N.new('ShaderNodeGroup'); fil.node_tree = LF_FIL; fil.location = (x0 + 250, -150); fil.label = 'LF_Filament'
        lvl = N.new('ShaderNodeMath'); lvl.operation = 'MULTIPLY'; lvl.location = (x0 + 100, -150)
        Lk.new(lev.outputs[0], lvl.inputs[0]); Lk.new(fl.outputs['Multiplier'], lvl.inputs[1])   # flicker starves the filament
        Lk.new(lvl.outputs[0], fil.inputs['Level'])
        fil.inputs['T0'].default_value = float(m['cct'])
        fil.inputs['Filter'].default_value = tuple(m['filter']) + (1.0,)
        strength, color = fil.outputs['Strength'], fil.outputs['Color']
    else:
        col = N.new('ShaderNodeRGB'); col.location = (x0 + 250, -150); col.label = 'Colour (filter x %d K)' % m['cct']
        col.outputs[0].default_value = tuple(m['color_lin']) + (1.0,)
        color = col.outputs[0]
        if m['kind'] == 'xenon':
            st = N.new('ShaderNodeGroup'); st.node_tree = LF_STROBE; st.location = (x0 + 250, -150); st.label = 'LF_Strobe'
            Lk.new(tv.outputs[0], st.inputs['Time']); Lk.new(lev.outputs[0], st.inputs['Level'])
            strength = st.outputs['Strength']
        else:
            fu = N.new('ShaderNodeGroup'); fu.node_tree = LF_FLUO; fu.location = (x0 + 250, -150); fu.label = 'LF_Fluorescent'
            Lk.new(tv.outputs[0], fu.inputs['Time']); Lk.new(lev.outputs[0], fu.inputs['Level'])
            strength = fu.outputs['Strength']
        fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.location = (x0 + 700, -300)
        Lk.new(strength, fm.inputs[0]); Lk.new(fl.outputs['Multiplier'], fm.inputs[1])
        strength = fm.outputs[0]
    tot = N.new('ShaderNodeMath'); tot.operation = 'MULTIPLY'; tot.location = (x0 + 900, -100)
    Lk.new(s, tot.inputs[0]); Lk.new(strength, tot.inputs[1])
    s = tot.outputs[0]
    if key == 'Landing':
        gb = N.new('ShaderNodeGroup'); gb.node_tree = LF_GOBO; gb.location = (x0 + 700, 250); gb.label = 'LF_LensGobo'
        Lk.new(vec, gb.inputs['Vector'])
        gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; gm.location = (x0 + 1050, 0)
        Lk.new(s, gm.inputs[0]); Lk.new(gb.outputs['Multiplier'], gm.inputs[1])
        s = gm.outputs[0]
    return s, color


# ---------------------------------------------------------------- lights (built in the level pose, then the plane is parked)
for key, m in meta.items():
    sock = bpy.data.objects[m['socket']]
    R = np.asarray(m['R'])                                       # columns: light X, Y, Z (beam) in Unity plane frame
    Rb = np.stack([conv(R[:, 0]), conv(R[:, 1]), -conv(R[:, 2])], 1)
    off = np.asarray(m['offset'], float) + np.array([0.0, EXTRA_UP.get(key, 0.0), 0.0])
    pos = np.asarray(sock.matrix_world.translation) + conv(off)
    ld = bpy.data.lights.new('L_' + key, 'POINT')
    ld.energy = 4 * PI * PI * m['intensity_urp']                    # same irradiance as Unity URP: E = I / d^2
    ld.shadow_soft_size = RADIUS[key]
    ld.color = (1.0, 1.0, 1.0)
    ob = bpy.data.objects.new('Light_' + key, ld)
    (C_FILL if m['peak_cd'] is None else C_LIGHTS).objects.link(ob)
    ob.parent = sock
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = sock.matrix_world.inverted() @ m4(Rb, pos)
    LIGHT_OBJ[key], LIGHT_RB[key] = ob, Rb
    UP_LOCAL[key] = tuple(float(x) for x in Rb[2, :])            # plane up (Blender +Z) in lamp-local axes
    ld.use_nodes = True
    nt = ld.node_tree
    em = [n for n in nt.nodes if n.type == 'EMISSION'][0]
    if m['peak_cd'] is None:                                      # fill: uniform, colour only
        em.inputs['Color'].default_value = tuple(m['color_lin']) + (1.0,)
        ob.hide_render = True
        continue
    tc = nt.nodes.new('ShaderNodeTexCoord'); tc.location = (-1700, 0)
    s, col = lf_chain(nt, key, m, tc.outputs['Normal'])
    nt.links.new(s, em.inputs['Strength']); nt.links.new(col, em.inputs['Color'])
    if key in SHADOW_FREE:
        cl = bpy.data.collections.new('SL_%s_not_blocking' % key)
        for oname in SHADOW_FREE[key] + [LENS_OF[key]]:
            cl.objects.link(bpy.data.objects[oname])
        ob.light_linking.blocker_collection = cl
        for co in cl.collection_objects:
            co.light_linking.link_state = 'EXCLUDE'

# ---------------------------------------------------------------- lenses: same IES + light functions towards the viewer
def proj_area(ob, axis_world):
    me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    mw = ob.matrix_world
    a = 0.0
    for p in me.polygons:
        n = (mw.to_3x3() @ p.normal).normalized()
        area = p.area * mw.to_3x3().determinant() ** (2 / 3)
        a += area * max(0.0, n.dot(axis_world))
    ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return max(a, 1e-5)


for key, lname in LENS_OF.items():
    lo = bpy.data.objects[lname]
    m = meta[key]
    src = lo.material_slots[0].material
    mat = src.copy(); mat.name = 'M_LensFX_' + key
    lo.material_slots[0].link = 'OBJECT'; lo.material_slots[0].material = mat
    mat.cycles.emission_sampling = 'NONE'
    nt = mat.node_tree; N, Lk = nt.nodes, nt.links
    p = [n for n in N if n.type == 'BSDF_PRINCIPLED'][0]
    geo = N.new('ShaderNodeNewGeometry'); geo.location = (-2100, 0)
    vt = N.new('ShaderNodeVectorTransform'); vt.vector_type = 'VECTOR'; vt.convert_from = 'WORLD'; vt.convert_to = 'OBJECT'
    vt.location = (-1900, 0); Lk.new(geo.outputs['Incoming'], vt.inputs[0])
    Rl = np.array(LIGHT_OBJ[key].matrix_world.to_3x3())          # level pose; both objects ride on the plane
    Ro = np.array(lo.matrix_world.to_3x3().normalized())
    Mx = Rl.T @ Ro                                                # lens-object local -> lamp local
    comps = []
    for r in range(3):
        dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'; dp.location = (-1750, 150 - 120 * r)
        Lk.new(vt.outputs[0], dp.inputs[0]); dp.inputs[1].default_value = tuple(float(x) for x in Mx[r])
        comps.append(dp.outputs['Value'])
    cx = N.new('ShaderNodeCombineXYZ'); cx.location = (-1600, 0)
    for i, c in enumerate(comps):
        Lk.new(c, cx.inputs[i])
    s, col = lf_chain(nt, key, m, cx.outputs[0], floor=LENS_FLOOR[key])
    axis_w = Vector(LIGHT_OBJ[key].matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    A = proj_area(lo, axis_w)
    gain = PI * m['intensity_urp'] / A                            # radiance of the lens = intensity / projected area
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; gm.location = (-200, -300); gm.label = 'lens radiance gain'
    Lk.new(s, gm.inputs[0]); gm.inputs[1].default_value = gain
    Lk.new(gm.outputs[0], p.inputs['Emission Strength']); Lk.new(col, p.inputs['Emission Color'])
    lo['lens_projected_area_m2'] = A
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(lo, attr, False)

# diffuser lenses (one lens over two lamps): glow with the lamps' level
for lname, keys in (('Lens_Dome', ('Dome_L', 'Dome_R')), ('Lens_CargoLight', ('Cargo', 'Cargo_2'))):
    lo = bpy.data.objects[lname]
    src = lo.material_slots[0].material
    mat = src.copy(); mat.name = 'M_LensFX_' + lname[5:]
    lo.material_slots[0].link = 'OBJECT'; lo.material_slots[0].material = mat
    mat.cycles.emission_sampling = 'NONE'
    nt = mat.node_tree; N, Lk = nt.nodes, nt.links
    p = [n for n in N if n.type == 'BSDF_PRINCIPLED'][0]
    m = meta[keys[0]]
    tc = N.new('ShaderNodeValue'); tc.outputs[0].default_value = 0.0      # dummy direction source not needed
    # level / light function of the first lamp (both lamps share the switch)
    tv = N.new('ShaderNodeValue'); tv.label = 'Time (s)'; add_time_driver(tv.outputs[0], 'default_value')
    lev = N.new('ShaderNodeValue'); lev.label = 'Level (switch / dimmer 0..1)'; lev.outputs[0].default_value = 1.0
    if m['kind'] == 'incandescent':
        fil = N.new('ShaderNodeGroup'); fil.node_tree = LF_FIL
        Lk.new(lev.outputs[0], fil.inputs['Level']); fil.inputs['T0'].default_value = float(m['cct'])
        fil.inputs['Filter'].default_value = tuple(m['filter']) + (1.0,)
        s, col = fil.outputs['Strength'], fil.outputs['Color']
    else:
        fu = N.new('ShaderNodeGroup'); fu.node_tree = LF_FLUO
        Lk.new(tv.outputs[0], fu.inputs['Time']); Lk.new(lev.outputs[0], fu.inputs['Level'])
        rgb = N.new('ShaderNodeRGB'); rgb.outputs[0].default_value = tuple(m['color_lin']) + (1.0,)
        s, col = fu.outputs['Strength'], rgb.outputs[0]
    axis_w = Vector((0, 0, -1))
    A = proj_area(lo, axis_w)
    gain = PI * m['intensity_urp'] * len(keys) / A
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; gm.inputs[1].default_value = gain
    Lk.new(s, gm.inputs[0]); Lk.new(gm.outputs[0], p.inputs['Emission Strength']); Lk.new(col, p.inputs['Emission Color'])
    lo['lens_projected_area_m2'] = A
    for attr in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(lo, attr, False)

# ---------------------------------------------------------------- panel backlight and displays (as the URP previews)
def cct_rgb(T):
    T = float(np.clip(T, 1000.0, 25000.0))
    if T <= 4000:
        x = -0.2661239e9 / T**3 - 0.2343589e6 / T**2 + 0.8776956e3 / T + 0.179910
    else:
        x = -3.0258469e9 / T**3 + 2.1070379e6 / T**2 + 0.2226347e3 / T + 0.240390
    if T <= 2222:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif T <= 4000:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    c = np.maximum(np.array([3.2406 * X - 1.5372 * Y - 0.4986 * Z, -0.9689 * X + 1.8758 * Y + 0.0415 * Z,
                             0.0557 * X - 0.2040 * Y + 1.0570 * Z]), 0.0)
    return c / c.max()


def set_emission(mn, strength, tint=None):
    mt = bpy.data.materials.get(mn)
    if mt is None:
        return
    p = [n for n in mt.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    p.inputs['Emission Strength'].default_value = strength
    if tint is not None:
        ec = p.inputs['Emission Color']
        if ec.is_linked:
            src = ec.links[0].from_socket
            mx, ma, mb, mo_ = mix_rgb(mt.node_tree.nodes)
            mt.node_tree.links.new(src, ma); mb.default_value = tuple(tint) + (1.0,)
            mt.node_tree.links.new(mo_, ec)
        else:
            ec.default_value = tuple(tint) + (1.0,)


set_emission('M_Gauges', 0.75, (np.array([1.0, 0.9, 0.78]) * cct_rgb(3000)).tolist())
set_emission('M_RadioDisplay', 1.2)
set_emission('M_Screen', 0.6, [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in (0.05, 0.12, 0.10)])

# ---------------------------------------------------------------- world: night sky; fog = a 40 m deep volume layer
# (a world volume is infinite in Cycles: it would swallow the moon and the sky light completely)
w = bpy.data.worlds.new('Night sky v11'); sc.world = w
w.use_nodes = True
WN, WL = w.node_tree.nodes, w.node_tree.links
bg = WN.get('Background'); bg.inputs['Color'].default_value = (0.006, 0.0075, 0.010, 1.0); bg.inputs['Strength'].default_value = 1.0

me = bpy.data.meshes.new('FogVolume')
x0, x1, y0, y1, z0, z1 = -200.0, 200.0, -200.0, 200.0, -0.5, 40.0
vv = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
ff = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
me.from_pydata(vv, [], ff)
fog = bpy.data.objects.new('FogVolume', me)
fmat = bpy.data.materials.new('M_FogVolume'); fmat.use_nodes = True
FN, FL = fmat.node_tree.nodes, fmat.node_tree.links
for n in list(FN):
    if n.type == 'BSDF_PRINCIPLED':
        FN.remove(n)
fo = [n for n in FN if n.type == 'OUTPUT_MATERIAL'][0]
dv = FN.new('ShaderNodeValue'); dv.label = 'scattering per metre = 0.034 x atmosphere'
add_scene_prop_driver(dv.outputs[0], 'default_value', 'atmosphere', 'p * 0.034')
v1 = FN.new('ShaderNodeVolumeScatter'); v1.inputs['Anisotropy'].default_value = 0.72; v1.label = 'forward lobe (fog droplets, snow)'
v2 = FN.new('ShaderNodeVolumeScatter'); v2.inputs['Anisotropy'].default_value = 0.25; v2.label = 'wide part'
m1 = FN.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = 0.8
m2 = FN.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = 0.2
FL.new(dv.outputs[0], m1.inputs[0]); FL.new(dv.outputs[0], m2.inputs[0])
FL.new(m1.outputs[0], v1.inputs['Density']); FL.new(m2.outputs[0], v2.inputs['Density'])
ad = FN.new('ShaderNodeAddShader'); FL.new(v1.outputs[0], ad.inputs[0]); FL.new(v2.outputs[0], ad.inputs[1])
FL.new(ad.outputs[0], fo.inputs['Volume'])
fmat.cycles.volume_sampling = 'MULTIPLE_IMPORTANCE'
me.materials.append(fmat)
fog.display_type = 'WIRE'
for attr in ('visible_shadow',):
    setattr(fog, attr, True)

# moon (as the URP previews: 0.03 x (0.55, 0.65, 1.0), from (-0.45, 0.55, -0.70) in Unity axes)
moon = bpy.data.lights.new('Moon', 'SUN'); moon.energy = 0.05 * PI; moon.color = (0.55, 0.65, 1.0); moon.angle = math.radians(0.5)
mo = bpy.data.objects.new('Moon', moon); C_PREV.objects.link(mo); C_PREV.objects.link(fog)
to_moon = Vector(conv(np.array([-0.45, 0.55, -0.70]) / np.linalg.norm([-0.45, 0.55, -0.70])).tolist())
mo.rotation_euler = to_moon.to_track_quat('Z', 'Y').to_euler()

# snow
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
gnd = bpy.context.active_object; gnd.name = 'Snow'
for c in gnd.users_collection:
    c.objects.unlink(gnd)
C_PREV.objects.link(gnd)
gm_ = bpy.data.materials.new('M_Snow'); gm_.use_nodes = True
N, L = gm_.node_tree.nodes, gm_.node_tree.links
pr = N['Principled BSDF']
nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; nz.inputs['Detail'].default_value = 3
ramp = N.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.66, 0.69, 0.72, 1); ramp.color_ramp.elements[1].color = (0.80, 0.82, 0.84, 1)
L.new(nz.outputs['Fac'], ramp.inputs[0]); L.new(ramp.outputs[0], pr.inputs['Base Color'])
pr.inputs['Roughness'].default_value = 0.85
gnd.data.materials.append(gm_)

# figures (simple dark people, as in the URP previews)
fm = bpy.data.materials.new('M_Figure'); fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.055, 1)
fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
for vname, vv in views.items():
    for i, (fx, fz, yaw) in enumerate(vv.get('figures', [])):
        cf = new_coll('Figure %s' % vname, C_FIG)
        base = u2b((fx, 0.0, fz))
        parts = [('body', (0.0, 0.0, 1.05), (0.21, 0.15, 0.42)), ('head', (0.0, 0.0, 1.62), (0.11, 0.12, 0.13)),
                 ('legL', (0.1, 0.0, 0.42), (0.09, 0.09, 0.43)), ('legR', (-0.1, 0.0, 0.42), (0.09, 0.09, 0.43)),
                 ('armL', (0.27, 0.0, 1.08), (0.06, 0.06, 0.36)), ('armR', (-0.27, 0.0, 1.08), (0.06, 0.06, 0.36))]
        for nm, offp, sc3 in parts:
            me = bpy.data.meshes.new('fig')
            import bmesh
            bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0); bm.to_mesh(me); bm.free()
            for pl in me.polygons:
                pl.use_smooth = True
            o = bpy.data.objects.new('Figure_%s_%s' % (vname, nm), me)
            o.location = (base.x + offp[0], base.y + offp[1], base.z + offp[2]); o.scale = sc3
            o.data.materials.append(fm)
            cf.objects.link(o)

# cameras
for vname, vv in views.items():
    c = vv['cam']
    cam = bpy.data.objects.new('Cam_' + vname, bpy.data.cameras.new('Cam_' + vname))
    C_PREV.objects.link(cam)
    pos, look = u2b(c['pos']), u2b(c['look'])
    cam.location = pos
    cam.rotation_euler = (look - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle_y = math.radians(c['fov'])
    cam.data.clip_start = 0.02; cam.data.clip_end = 1000
sc.camera = bpy.data.objects['Cam_ext_front']

# ---------------------------------------------------------------- park the plane (UtilityPlaneRig.ParkedPose)
ph = math.radians(-9.98)
Ru = np.array([[1, 0, 0], [0, math.cos(ph), -math.sin(ph)], [0, math.sin(ph), math.cos(ph)]])
park = Matrix.Translation(u2b((0, -0.372, 0))) @ m4(M.T @ Ru @ M, (0, 0, 0))
for rn in ('UtilityPlane', 'WinterKit'):
    r = bpy.data.objects.get(rn)
    if r:
        r.matrix_world = park @ r.matrix_world

# ---------------------------------------------------------------- render settings
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 128
sc.cycles.preview_samples = 32
sc.cycles.use_denoising = True
sc.cycles.use_preview_denoising = True
sc.cycles.use_light_tree = True
sc.cycles.max_bounces = 8
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 3
sc.cycles.transmission_bounces = 4
sc.cycles.volume_bounces = 1
sc.cycles.transparent_max_bounces = 8
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.sample_clamp_indirect = 10.0
sc.render.resolution_x, sc.render.resolution_y = 1520, 856
sc.render.resolution_percentage = 100
sc.frame_set(1)

# notes inside the file
txt = bpy.data.texts.new('README_v11_lights')
txt.from_string(open('/home/claude/plane/v11/blender/README_v11_lights.txt').read() if os.path.exists('/home/claude/plane/v11/blender/README_v11_lights.txt') else 'see README_Blender_v11.txt')

bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=False, compress=True)
print('saved', OUT)
nsimple = nall = 0
for idb in list(bpy.data.lights) + list(bpy.data.materials) + list(bpy.data.worlds) + list(bpy.data.node_groups):
    ad = getattr(idb, 'animation_data', None) or (idb.node_tree.animation_data if getattr(idb, 'node_tree', None) else None)
    if ad:
        for fc in ad.drivers:
            nall += 1; nsimple += fc.driver.is_simple_expression
print('drivers', nall, 'simple expressions', nsimple)
o = bpy.data.objects['Light_Nav_L']
cl_ = o.light_linking.blocker_collection
print('Nav_L blockers', [(ob_.name, co.light_linking.link_state) for ob_, co in zip(cl_.objects, cl_.collection_objects)])
print('hidden glass', hidden_glass)
for k, o in LIGHT_OBJ.items():
    print('%-14s pos %s  energy %.1f W' % (k, tuple(round(x, 3) for x in o.matrix_world.translation), o.data.energy))
for lname in list(LENS_OF.values()) + ['Lens_Dome', 'Lens_CargoLight']:  # incl. Lens_Flood_L / _R
    print(lname, 'projected area %.4f m2' % bpy.data.objects[lname]['lens_projected_area_m2'])
