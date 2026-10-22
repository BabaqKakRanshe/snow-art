"""Van v3, phase 2: what the player still needed.
  wheels: hub nuts that come off, the spare is a copy of the road wheel on the carrier, steering hinges linked to the
  wheel, jack points, a flat-tyre shape (post-bake, in van3_build section 10);
  cold start: blowtorch (pump, valve) for the sump, radiator drain cock, the kettle on the stove for hot water;
  snow: tyre chains per wheel, a chain bag, snow that settles on the roof / visor / bumper (blend shape) and on the
  lamps (stretch), brush-scraper in the passenger door pocket;
  the saloon stove works (door, vent, ash pan, damper, logs - built by van2_props.build(v3=True));
  horn button on the hub; CB radio: volume / squelch knobs, channel buttons, a display quad with 0..1 UVs, a hand
  mic with PTT on a hook; glovebox: lid, map, logbook, torch, three flares; exhaust with a tailpipe;
  the front panes of the cab doors slide back;
  audio / VFX / knock / handprint / hide points, fog and snow masks, colliders (in van3_build section 11).
Body frame (before the 9 cm lift): x forward, y left, z up, metres."""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, kdtree
from mathutils.bvhtree import BVHTree
import van2_kit as VK
from van2_kit import KB, up_axes, rrect
import van3_mech as VM
from van3_mech import part, socket, rbox, frame_R, CONTRACT, set_pivot
import van3_extras as VX

Z_SNOW, Z_CANVAS, Z_MAP = 85, 86, 87
PLAY_ZONES = [Z_SNOW, Z_CANVAS, Z_MAP]
Z = VM
Z_BLACK, Z_CHROME = VK.Z_BLACK, VK.Z_CHROME
Z_DASHP = VK.Z_DASHP
FLOOR = 0.716
WHEEL_R_FINAL = 0.323 * 1.12                     # hub height of the wheels after the 1.12 scale (they are not lifted)
NO_LIFT = set()                                  # objects built in final (ground) coordinates: skip the body lift


# ================================================================ cold start
BT = Vector((-0.12, 0.80, FLOOR))                # blowtorch on the saloon floor under seat L3, by the left wall


def blowtorch(kbs):
    """brass blowtorch: tank, filler cap, pump with a T-knob, riser and burner along -x, valve, wooden grip"""
    def L(x, y, z):
        return BT + Vector((x, y, z))
    B = kbs('Blowtorch')
    B.lathe(BT, (0, 0, 1), [(0.0, 0.050), (0.004, 0.055), (0.11, 0.055), (0.125, 0.045), (0.135, 0.02)], Z.Z_BRASS, 14)
    B.cyl(L(0.022, 0.0, 0.130), L(0.022, 0.0, 0.150), 0.013, Z.Z_BRASS, 8)
    B.tube([L(0.0, 0.0, 0.13), L(0.0, 0.0, 0.20), L(-0.02, 0.0, 0.205)], 0.008, Z.Z_BRASS, 8)
    B.cyl(L(-0.02, 0.0, 0.205), L(-0.15, 0.0, 0.205), 0.012, Z.Z_BRASS, 10)
    B.cyl(L(-0.15, 0.0, 0.205), L(-0.185, 0.0, 0.205), 0.019, Z.Z_BRASS, 10, r2=0.015)
    B.cyl(L(-0.10, 0.0, 0.17), L(-0.10, 0.0, 0.195), 0.022, Z.Z_STEEL2, 10, r2=0.026)        # pre-heating cup
    B.cyl(L(0.09, 0.0, 0.035), L(0.09, 0.0, 0.115), 0.012, VX.Z_WOOD2, 8)
    for zz in (0.045, 0.105):
        B.cyl(L(0.05, 0.0, zz), L(0.084, 0.0, zz), 0.004, Z.Z_STEEL2, 6)
    part('Blowtorch', 'item', BT, (0, 0, 1), states=['empty', 'filled', 'pumped', 'burning'],
         note='blowtorch: fill with petrol (Pour_Blowtorch), pump, warm the cup, open the valve; hold the flame under '
              'the sump (Heat_OilPan) for a cold start')
    P_ = kbs('Blowtorch_Pump')
    P_.cyl(L(-0.03, 0.0, 0.133), L(-0.03, 0.0, 0.20), 0.004, Z.Z_STEEL2, 6)
    P_.box(BT.x - 0.052, BT.x - 0.008, BT.y - 0.006, BT.y + 0.006, BT.z + 0.20, BT.z + 0.212, Z.Z_KNOB)
    part('Blowtorch_Pump', 'slide', L(-0.03, 0.0, 0.133), (0, 0, 1), (0, 0.06), unit='m', parent='Blowtorch',
         note='pump: ten strokes for the pressure')
    V = kbs('Blowtorch_Valve')
    V.cyl(L(-0.06, 0.0, 0.217), L(-0.06, 0.0, 0.235), 0.003, Z.Z_STEEL2, 6)
    V.cyl(L(-0.06, 0.0, 0.235), L(-0.06, 0.0, 0.243), 0.013, Z.Z_KNOB, 10)
    part('Blowtorch_Valve', 'twist', L(-0.06, 0.0, 0.217), (0, 0, 1), (0, 540), parent='Blowtorch',
         states=['closed', 'open'], note='fuel valve: a turn and a half to full flame')
    socket('Hand_Blowtorch', L(0.09, 0.0, 0.075), 'hand', parent='Blowtorch')
    socket('Hand_Blowtorch_Pump', L(-0.03, 0.0, 0.212), 'hand', parent='Blowtorch_Pump')
    socket('Hand_Blowtorch_Valve', L(-0.06, 0.0, 0.243), 'hand', parent='Blowtorch_Valve')
    socket('Pour_Blowtorch', L(0.022, 0.0, 0.150), 'pour', parent='Blowtorch', note='petrol in here')
    socket('Blowtorch_Flame', L(-0.185, 0.0, 0.205), 'vfx', parent='Blowtorch', note='flame out along -x of the item')
    CONTRACT['sockets']['Blowtorch_Flame']['dir'] = [-1.0, 0.0, 0.0]
    socket('Heat_OilPan', (1.19, 0.0, VM.BAY_LO.z - 0.01), 'heat',
           note='hold the blowtorch flame here (under the skid plate of the sump) for a cold start')
    CONTRACT['sockets']['Heat_OilPan']['dir'] = [0.0, 0.0, 1.0]


def engine_drain(kbs):
    """brass drain cock low on the left side of the block (between the last two ribs): reach it with the cover up"""
    c = Vector((1.31, 0.10, 0.535))
    D = kbs('Engine_Drain')
    D.cyl(c, c + Vector((0, 0.022, 0)), 0.008, Z.Z_BRASS, 8)
    D.box(c.x - 0.003, c.x + 0.003, c.y + 0.018, c.y + 0.024, c.z - 0.020, c.z + 0.020, Z.Z_BRASS)
    part('Engine_Drain', 'twist', c, (0, 1, 0), (0, 90), parent='Engine', states=['closed', 'open'],
         note='coolant drain cock on the block: open it at night if there is only water in the system; refill hot '
              'water (Kettle) through Pour_Radiator')
    socket('Hand_Engine_Drain', c + Vector((0, 0.024, 0.015)), 'hand', parent='Engine_Drain')
    socket('Drain_Engine', c + Vector((0, 0.03, -0.02)), 'vfx', parent='Engine', note='coolant runs out here')
    CONTRACT['sockets']['Drain_Engine']['dir'] = [0.0, 0.3, -0.95]


def exhaust(kbs):
    """pipe from the engine bay along the right side under the floor, silencer behind the rear axle, tailpipe under
    the rear bumper"""
    E = kbs('Exhaust')
    E.tube([(0.92, -0.20, 0.47), (0.80, -0.30, 0.48), (0.40, -0.40, 0.475), (-1.40, -0.42, 0.47)], 0.022, Z.Z_RUST2, 8)
    E.cyl((-1.40, -0.42, 0.47), (-1.45, -0.42, 0.47), 0.03, Z.Z_RUST2, 10, r2=0.075)
    E.cyl((-1.45, -0.42, 0.47), (-1.90, -0.42, 0.47), 0.075, Z.Z_RUST2, 12)
    E.cyl((-1.90, -0.42, 0.47), (-1.95, -0.42, 0.47), 0.075, Z.Z_RUST2, 12, r2=0.03)
    E.tube([(-1.95, -0.42, 0.47), (-2.08, -0.43, 0.455), (-2.20, -0.45, 0.425)], 0.022, Z.Z_RUST2, 8)
    for x in (-1.55, -1.82):                                          # hangers
        E.box(x - 0.01, x + 0.01, -0.425, -0.415, 0.545, 0.62, Z.Z_STEEL2)
    part('Exhaust', 'static', (-0.60, -0.40, 0.47), parent='Kuzov')
    socket('VFX_Exhaust', (-2.21, -0.452, 0.422), 'vfx', parent='Exhaust',
           note='exhaust smoke; thick white steam for the first minute of a cold start')
    CONTRACT['sockets']['VFX_Exhaust']['dir'] = [-0.96, -0.04, -0.27]


# ================================================================ snow
def wheel_centres(wheels):
    """final hub centres by corner (x, y from the stock wheel boxes, z = the scaled hub height)"""
    out = {}
    for w in wheels:
        V = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
        cx, cy = (V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2
        out[('F' if cx > 0 else 'R') + ('L' if cy > 0 else 'R')] = Vector((cx, cy, WHEEL_R_FINAL))
    return out


def chains(kbs, centres):
    """snow chains for each wheel (ladder pattern): two side chains on the shoulders, eight cross chains over the
    tread; built on the final wheels, hidden until fitted"""
    S = 1.12
    for k, c in centres.items():
        name = 'Chains_' + k
        C = kbs(name)
        out = Vector((0, 1 if c.y > 0 else -1, 0))
        for a_side in (-1, 1):
            VX.ring_strip(C, c + out * (a_side * 0.155 * S), (0, 1, 0), 0.272 * S, 0.012, 0.012, Z.Z_STEEL2, 20)
        for i in range(8):
            ang = 2 * math.pi * (i + 0.25) / 8
            rad = Vector((math.cos(ang), 0, math.sin(ang)))
            pts = [c + out * (a * S) + rad * (r * S) for a, r in ((-0.152, 0.272), (-0.135, 0.300), (-0.10, 0.322),
                                                                   (0.0, 0.330), (0.10, 0.322), (0.135, 0.300),
                                                                   (0.152, 0.272))]
            C.tube(pts, 0.008, Z.Z_STEEL2, 4, caps=False)
        part(name, 'static', c, parent='Wheel_' + k, states=['hidden', 'fitted'],
             note='snow chains on this wheel: hidden until fitted from the ChainBag (they turn with the wheel)')
        CONTRACT['parts'][name]['default'] = 'hidden'
        NO_LIFT.add(name)


CHAIN_BAG = Vector((-1.03, -0.76, 0.916))         # on the right rear wheel arch, under seat R1


def chain_bag(kbs):
    G = kbs('ChainBag')
    c = CHAIN_BAG
    rbox(G, c + Vector((0, 0, 0.055)), (0.26, 0.13, 0.11), Z_CANVAS, r=0.03, ch=0.015)
    G.tube([c + Vector((-0.08, 0.0, 0.11)), c + Vector((-0.03, 0.02, 0.135)), c + Vector((0.03, -0.02, 0.135)),
            c + Vector((0.08, 0.0, 0.11))], 0.008, Z_CANVAS, 6)
    for i in range(5):                                                    # links spilling out of the mouth
        p = c + Vector((0.10 + 0.012 * i, 0.03 - 0.012 * i, 0.10 - 0.02 * i))
        VX.ring_strip(G, p, (1, 0.4, 0), 0.010, 0.0035, 0.0035, Z.Z_STEEL2, 6)
    part('ChainBag', 'item', c, (1, 0, 0), states=['full', 'empty'],
         note='canvas bag with the snow chains: fitting it shows Chains_<wheel> on the chosen wheel')
    socket('Hand_ChainBag', c + Vector((0, 0, 0.135)), 'hand', parent='ChainBag')


SNOW_BASE = {}                                     # name -> (kdtree of full vertex positions, base z per vertex)


def _blanket(kb, grid, thick, edge=0.22):
    """snow blanket over a height grid {(i, j): (x, y, z_base)}: thickest in the middle, zero on the edge ring"""
    keys = set(grid)
    ii = sorted({i for i, _ in keys})
    jj = sorted({j for _, j in keys})
    verts, base = {}, []
    for (i, j), (x, y, zb) in grid.items():
        nb = sum((i + di, j + dj) in keys for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        # distance to the blanket border in cells -> thickness
        d = 0
        while d < 6 and all((i + di * (d + 1), j + dj * (d + 1)) in keys for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            d += 1
        t = 0.0 if nb < 4 else min(1.0, d / 3.0)
        t = t * t * (3 - 2 * t)
        verts[(i, j)] = kb.bm.verts.new(Vector((x, y, zb + 0.004 + thick * t)))
        base.append(((x, y, zb + 0.004 + thick * t), zb + 0.003))
    for (i, j) in keys:
        q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        if all(k in verts for k in q):
            vs = [verts[k] for k in q]
            if (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co).z < 0:
                vs = vs[::-1]
            kb._f(vs, Z_SNOW)
    return base


def snow(kbs, roof_fn, kit_front, lamp_sockets):
    """snow that settles: blankets on the roof, the visor and the bumper (blend shape 'Clear' = none) and caps on the
    lamps (stretch along the lamp axis: 0 = none) - the lamp shines through a cap at (1 - 0.85 * amount)"""
    # roof: from the probe of the stock roof (also over the hatch: snow keeps the hatch shut until cleared)
    grid = {}
    xs = np.linspace(-2.08, 1.90, 25)
    ys = np.linspace(-0.90, 0.90, 13)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            try:
                z = roof_fn(float(x), float(y))
            except Exception:
                z = None
            if z is not None and z > 1.9:
                grid[(i, j)] = (float(x), float(y), float(z))
    kb = kbs('Snow_Roof')
    base = _blanket(kb, grid, 0.07)
    SNOW_BASE['Snow_Roof'] = base
    part('Snow_Roof', 'static', (-0.09, 0.0, 2.08), parent='Kuzov', states=['0 none', '1 full (7 cm)'],
         note='snow on the roof: blend shape Clear (100 = no snow); the roof hatch cannot open while it lies over it')
    # visor and bumper: rays down onto the front kit
    me = kit_front.data
    bvh = BVHTree.FromPolygons([kit_front.matrix_world @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    for name, xr_, yr_, zr_, nx, ny, thick, ok in (
            ('Snow_Visor', (1.90, 2.24), (-0.80, 0.80), (1.80, 1.95), 8, 15, 0.05, lambda y: True),
            ('Snow_Bumper', (2.19, 2.33), (-0.95, 0.95), (0.62, 0.70), 4, 21, 0.045, lambda y: abs(y) > 0.37)):
        grid = {}
        for i, x in enumerate(np.linspace(*xr_, nx)):
            for j, y in enumerate(np.linspace(*yr_, ny)):
                if not ok(y):
                    continue
                hit = bvh.ray_cast(Vector((float(x), float(y), zr_[1] + 0.3)), Vector((0, 0, -1)), 0.6)
                if hit[0] is not None and zr_[0] < hit[0].z < zr_[1]:
                    grid[(i, j)] = (float(x), float(y), float(hit[0].z))
        kb = kbs(name)
        SNOW_BASE[name] = _blanket(kb, grid, thick)
        part(name, 'static', ((xr_[0] + xr_[1]) / 2, 0.0, (zr_[0] + zr_[1]) / 2), parent='Kit_Front',
             states=['0 none', '1 full'], note='snow: blend shape Clear (100 = no snow)')
    for nm in ('Snow_Roof', 'Snow_Visor', 'Snow_Bumper'):
        CONTRACT['parts'][nm]['blendshape'] = 'Clear'
        CONTRACT['parts'][nm]['default'] = 'hidden'
    # lamp caps
    size = {'head': 0.088, 'spot': 0.078, 'fog': 0.05}
    for (name, f, n, typ, up) in lamp_sockets:
        if typ not in size:
            continue
        n = Vector(n).normalized()
        up = Vector(up).normalized()
        r = size[typ]
        cn = 'Snow_' + name
        C = kbs(cn)
        c0 = Vector(f) + n * 0.003
        if typ == 'fog':
            u = up.cross(n).normalized()
            C.box_m(c0 + n * 0.012 + up * 0.004, (0.14, 0.072, 0.024), Z_SNOW, Matrix((u, up, n)).transposed())
        else:
            C.lathe(c0 + up * r * 0.08, n, [(0.0, r), (0.010, r * 0.93), (0.019, r * 0.62), (0.024, 0.0)], Z_SNOW, 12,
                    cap0=True, cap1=False)
            C.lathe(c0 + up * r * 0.75, n, [(0.0, r * 0.45), (0.015, r * 0.35), (0.028, 0.0)], Z_SNOW, 8, cap0=True, cap1=False)
        part(cn, 'stretch', Vector(f), n, (0.05, 1.0), unit='x', parent='Kit_Front', states=['0 none', '1 full'],
             note=f'snow on lamp {name}: scale along the lamp axis; light x (1 - 0.85 * amount); brush it off')
        CONTRACT['parts'][cn]['dims'] = name
        CONTRACT['parts'][cn]['default'] = 'hidden'


def brush_and_pocket(kbs):
    """door pocket on the passenger door and a snow brush with an ice scraper in it"""
    Pk = kbs('DoorPocket_P')
    y_in, y_out = -0.861, -0.833
    x0, x1, z0, z1 = 1.00, 1.51, 0.82, 0.95
    for q in ([(x0, y_out, z0), (x1, y_out, z0), (x1, y_out, z1), (x0, y_out, z1)],        # front face (cabin side)
              [(x0, y_in, z0), (x1, y_in, z0), (x1, y_out, z0), (x0, y_out, z0)],          # bottom
              [(x0, y_in, z0), (x0, y_out, z0), (x0, y_out, z1), (x0, y_in, z1)],
              [(x1, y_out, z0), (x1, y_in, z0), (x1, y_in, z1), (x1, y_out, z1)]):
        Pk.poly(q, Z.Z_KNOB)
        Pk.poly(q[::-1], Z.Z_KNOB)
    part('DoorPocket_P', 'static', ((x0 + x1) / 2, y_out, (z0 + z1) / 2), parent='doorP')
    Br = kbs('SnowBrush')
    yb, zb = -0.847, 0.905
    Br.cyl((1.03, yb, zb), (1.43, yb, zb), 0.011, VX.Z_HANDLE, 8)
    Br.box(1.03, 1.14, yb - 0.009, yb + 0.009, zb + 0.008, zb + 0.06, Z.Z_KNOB)                # bristles up
    Br.box(1.03, 1.14, yb - 0.011, yb + 0.011, zb - 0.004, zb + 0.010, VX.Z_HANDLE)
    Br.box(1.43, 1.49, yb - 0.003, yb + 0.003, zb - 0.03, zb + 0.03, Z.Z_YELLOW)               # scraper blade
    part('SnowBrush', 'item', (1.26, yb, zb), (1, 0, 0), parent='doorP',
         note='snow brush and ice scraper: clears Snow_* from the glass, the lamps and the roof hatch, frost off lob')
    socket('Hand_SnowBrush', (1.28, yb, zb), 'hand', parent='SnowBrush')


# ================================================================ horn, radio, glovebox
def horn_button(kbs, steer):
    C, N = VM.WHEEL_C, VM.WHEEL_N
    co = [steer.matrix_world @ v.co for v in steer.data.vertices]
    front = max(((p - C).dot(N) for p in co if ((p - C) - N * (p - C).dot(N)).length < 0.05), default=0.03)
    H = kbs('Horn_Button')
    c = C + N * (front + 0.001)
    H.lathe(c, N, [(0.0, 0.034), (0.008, 0.032), (0.012, 0.022), (0.013, 0.0)], Z.Z_KNOB, 14, cap0=True, cap1=False)
    H.cyl(c + N * 0.0125, c + N * 0.0135, 0.010, Z.Z_REDPLAST, 10)
    part('Horn_Button', 'slide', c, -N, (0, 0.005), unit='m', parent='SteeringWheel',
         note='horn: press the pad; in a blizzard the others find the van by it (Audio_Horn)')
    socket('Hand_Horn', c + N * 0.016, 'hand', parent='Horn_Button')
    socket('Audio_Horn', (2.08, 0.25, 0.86), 'audio', parent='Kit_Front', note='horn behind the grille')


RADIO_C = (0.0, 1.172, 0.009)                       # the CB radio plate on the centre stack (VK.dashboard)


def radio(kbs, display_kb, lcd_uv):
    """CB radio: VOL (power + volume) and SQ knobs over the drawn ones, two channel buttons, a display quad (atlas UVs
    + a second 0..1 'RT' layer for a live render texture), hand mic with a press-to-talk bar on a hook"""
    n = Vector(VK.DASH_N)
    u, v = up_axes(n)                                    # u = to the passenger (-y), v = up the panel
    c = VK.on_face(*RADIO_C)
    pt = lambda a, b, off: c + u * a + v * b + n * off
    R = Matrix((u, v, n)).transposed()
    for name, a, note in (('Radio_Volume', 0.0625, 'power and volume: click on past 0'),
                          ('Radio_Squelch', 0.0844, 'squelch: noise gate')):
        K = kbs(name)
        K.lathe(pt(a, 0.0016, 0.0), n, [(0.0, 0.0085), (0.009, 0.0085), (0.012, 0.0065), (0.0125, 0.0)], Z.Z_KNOB, 10)
        K.box_m(pt(a, 0.0016 + 0.005, 0.0125), (0.002, 0.005, 0.0012), Z.Z_STEEL2, R)
        part(name, 'twist', pt(a, 0.0016, 0.0), -n, (0, 270), parent='Dash', states=['off', 'max'] if 'Vol' in name else [],
             note=note + ' (clockwise = more; the axis points into the panel)')
        socket('Hand_' + name, pt(a, 0.0016, 0.015), 'hand', parent=name)
    for name, a in (('Radio_ChDown', 0.0141), ('Radio_ChUp', 0.0313)):
        K = kbs(name)
        K.box_m(pt(a, -0.0172, 0.0015), (0.0115, 0.0055, 0.004), Z.Z_KNOB, R)
        part(name, 'slide', pt(a, -0.0172, 0.0), -n, (0, 0.003), unit='m', parent='Dash',
             note='channel ' + ('down' if 'Down' in name else 'up') + ' (1..40), shown on Radio_Display')
        socket('Hand_' + name, pt(a, -0.0172, 0.006), 'hand', parent=name)
    w, h = 58 / 128 * 0.20, 16 / 32 * 0.05
    display_kb.quad_uv(pt(-0.0016, 0.0031, 0.0005), n, w, h, lcd_uv)
    part('Radio_Display', 'static', pt(-0.0016, 0.0031, 0.0005), parent='Dash',
         note='CB display: UV map RT is 0..1 over the glass - put a render texture with the frequency / channel on it')
    socket('Audio_Radio', pt(0.0, 0.0, -0.02), 'audio', parent='Dash', note='radio loudspeaker (static, voices)')
    # hand mic on a hook beside the glovebox
    hook = VK.on_face(-0.285, 1.300, 0.0)
    Hk = kbs('Radio_MicHook')
    Hk.box_m(hook + n * 0.006, (0.012, 0.016, 0.012), Z.Z_STEEL2, R)
    Hk.box_m(hook + n * 0.013 + v * 0.004, (0.004, 0.016, 0.004), Z.Z_STEEL2, R)
    part('Radio_MicHook', 'static', hook, parent='Dash')
    socket('Hook_Radio_Mic', hook + n * 0.013, 'item_slot', parent='Radio_MicHook', note='the mic hangs here')
    mc = VK.on_face(-0.285, 1.2475, 0.019)
    M = kbs('Radio_Mic')
    Rm = Matrix((n, -u, v)).transposed()                 # mic frame: x = towards the cab, y = left, z = up
    loc = lambda x, y, z: mc + Rm @ Vector((x, y, z))
    M.box_m(mc, (0.030, 0.055, 0.085), Z.Z_KNOB, Rm)
    M.box_m(loc(-0.0155, 0.0, 0.012), (0.002, 0.040, 0.040), Z.Z_STEEL2, Rm)          # grille faces the cab
    M.box_m(loc(0.0, 0.0, 0.0445), (0.010, 0.012, 0.006), Z.Z_STEEL2, Rm)             # clip
    M.cyl(loc(0.0, 0.0, -0.0425), loc(0.0, 0.0, -0.065), 0.005, Z.Z_WIRE_B, 6)
    part('Radio_Mic', 'item', mc, v, parent='Dash', note='hand mic on a coiled cord: draw the cord from Radio_Cord_Radio '
                                                        'to Radio_Cord_Mic (about 1.2 m stretched)')
    P_ = kbs('Radio_Mic_PTT')
    P_.box_m(loc(0.0, 0.0295, 0.008), (0.012, 0.004, 0.040), Z.Z_STEEL2, Rm)
    part('Radio_Mic_PTT', 'slide', loc(0.0, 0.0295, 0.008), -(Rm @ Vector((0, 1, 0))), (0, 0.003), unit='m',
         parent='Radio_Mic', note='press to talk')
    socket('Hand_Radio_Mic', mc, 'hand', parent='Radio_Mic')
    socket('Radio_Cord_Mic', loc(0.0, 0.0, -0.065), 'item_slot', parent='Radio_Mic', note='coiled cord, mic end')
    socket('Radio_Cord_Radio', pt(0.085, -0.024, 0.0), 'item_slot', parent='Dash', note='coiled cord, radio end')


def glovebox_kit(kbs, lens, L):
    """glovebox lid (built by VK.dashboard into Glovebox_Lid) and what lies in the bin: folded map, logbook, torch,
    three road flares.  Returns the lamp sockets (torch, flares)"""
    g = VK.GLOVE
    n = Vector(VK.DASH_N)
    u, v = up_axes(n)
    hinge = VK.on_face(-0.56, 1.195, 0.012) - v * 0.075
    part('Glovebox_Lid', 'hinge', hinge, (0, -1, 0), (0, 80), parent='Dash', states=['closed', 'open'],
         note='glovebox lid, hinged at the bottom; inside: Map, Logbook, Flashlight, Flare_1..3')
    socket('Hand_Glovebox_Lid', VK.on_face(-0.56, 1.255, 0.024), 'hand', parent='Glovebox_Lid')
    zf = g['z0']
    Mp = kbs('Map')
    Mp.box(1.766, 1.914, -0.515, -0.346, zf, zf + 0.008, Z_MAP)
    part('Map', 'item', (1.84, -0.4305, zf + 0.004), (0, 1, 0), parent='Dash', states=['folded', 'open'],
         note='folded map of the area with the route to the base pencilled in')
    socket('Hand_Map', (1.80, -0.38, zf + 0.008), 'hand', parent='Map')
    Lb = kbs('Logbook')
    Lb.box(1.776, 1.904, -0.506, -0.354, zf + 0.008, zf + 0.025, Z_CANVAS)
    Lb.box(1.779, 1.904, -0.503, -0.357, zf + 0.0105, zf + 0.0225, Z.Z_CERAMIC)            # page edges
    part('Logbook', 'item', (1.84, -0.43, zf + 0.0165), (0, 1, 0), parent='Dash', states=['closed', 'open'],
         note='trip logbook: dates, fuel, the notes of the previous crew (the story goes in here)')
    socket('Hand_Logbook', (1.80, -0.43, zf + 0.025), 'hand', parent='Logbook')
    # torch along -y, head at y -0.76
    Fl = kbs('Flashlight')
    tc = Vector((1.80, -0.56, zf + 0.026))
    a = Vector((0, -1, 0))
    Fl.lathe(tc, a, [(0.0, 0.0), (0.0, 0.017), (0.006, 0.019), (0.12, 0.019), (0.15, 0.025), (0.195, 0.025)], Z.Z_KNOB, 12,
             cap0=False, cap1=False)
    Fl.lathe(tc, a, [(0.195, 0.025), (0.20, 0.026), (0.203, 0.021)], Z.Z_STEEL2, 12, cap0=False, cap1=False)
    Fl.box(tc.x - 0.006, tc.x + 0.006, tc.y - 0.07, tc.y - 0.05, tc.z + 0.017, tc.z + 0.023, Z.Z_REDPLAST)   # switch
    head = tc + a * 0.201
    lens('Torch', 'torch').disc_uv(head, a, 0.021, L['spot_round'], 12, dome=0.004)
    part('Flashlight', 'item', tc + a * 0.10, a, parent='Dash', states=['off', 'on'],
         note='hand torch: the light is lamp Torch (type torch) in van3_lights.json; it rides on the item')
    socket('Hand_Flashlight', tc + a * 0.06, 'hand', parent='Flashlight')
    lamps = [('Torch', head + a * 0.004, a, 'torch', Vector((0, 0, 1)))]
    for k in range(3):
        name = f'Flare_{k + 1}'
        F = kbs(name)
        x = 1.848 + 0.029 * k
        f0, f1 = Vector((x, -0.53, zf + 0.0145)), Vector((x, -0.76, zf + 0.0145))
        F.cyl(f0, f1 + Vector((0, 0.03, 0)), 0.014, Z.Z_REDPLAST, 10)
        F.cyl(f1 + Vector((0, 0.03, 0)), f1, 0.0145, Z.Z_CERAMIC, 10)                       # striker cap
        F.cyl(f0 + Vector((0, -0.10, 0)), f0 + Vector((0, -0.13, 0)), 0.0143, Z.Z_CERAMIC, 10)   # label band
        lens(name, 'flare').disc_uv(f1 + Vector((0, -0.0005, 0)), (0, -1, 0), 0.011, L['tail_red'], 8)
        part(name, 'item', (f0 + f1) / 2, (0, -1, 0), parent='Dash', states=['new', 'burning', 'spent'],
             note='road flare: strike the cap; about a minute of red light (lamp ' + name + ', type flare)')
        socket('Hand_' + name, f0 + Vector((0, -0.04, 0)), 'hand', parent=name)
        lamps.append((name, f1 + Vector((0, -0.004, 0)), Vector((0, -1, 0)), 'flare', Vector((0, 0, 1))))
    return lamps


# ================================================================ cab windows
def cab_windows(Z_GLASS):
    """the front pane of each cab door window becomes its own part: it slides back behind the fixed rear pane"""
    out = []
    for door, side in (('doorL', 1), ('doorP', -1)):
        o = bpy.data.objects[door]
        name = 'Window_' + door
        w = VX.split_faces(o, lambda c, z: z == Z_GLASS and c.x > 1.311 and c.z > 1.30 and abs(c.y) > 0.80, name)
        w.data.transform(Matrix.Translation((0, -side * 0.008, 0)))                 # inside the fixed pane
        co = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
        lo, hi = co.min(0), co.max(0)
        tab = KB()
        yt = (lo[1] if side > 0 else hi[1]) - side * 0.004
        tab.box(hi[0] - 0.05, hi[0] - 0.035, yt - 0.004, yt + 0.004, lo[2] + 0.17, lo[2] + 0.23, Z.Z_KNOB)
        to = tab.to_object('tmp_tab')
        for ob in bpy.context.selected_objects:
            ob.select_set(False)
        w.select_set(True)
        to.select_set(True)
        bpy.context.view_layer.objects.active = w
        bpy.ops.object.join()
        w['orig'] = name
        piv = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
        set_pivot(w, piv)
        part(name, 'slide', piv, (-1, 0, 0), (0, 0.30), unit='m', parent=door, states=['closed', 'open'],
             note='front pane of the cab door window: slides back 30 cm behind the fixed pane (talk, hand things out)')
        socket('Hand_' + name, Vector((hi[0] - 0.042, yt - side * 0.006, lo[2] + 0.20)), 'hand', parent=name)
        out.append(w)
    return out


# ================================================================ points: audio, VFX, hide (body frame, lifted later)
def play_points(stove):
    s = stove
    sx1 = s['x1']
    yc = (s['y0'] + s['y1']) / 2
    for name, kind, par, pos, d, note in (
            ('Audio_Engine', 'audio', 'EngineBay', (1.19, 0.0, 0.75), None, 'engine (idle, revs, the crank turning it over)'),
            ('Audio_Heater', 'audio', 'Dash', (1.80, 0.0, 1.20), None, 'heater fan'),
            ('Audio_Wipers', 'audio', 'Kuzov', (1.99, 0.0, 1.40), None, 'wiper motor'),
            ('Audio_Stove', 'audio', 'Stove', (sx1 - 0.15, yc, FLOOR + 0.30), None, 'stove: fire, the door, ticking iron'),
            ('Audio_Tyres', 'audio', 'Kuzov', (0.0, 0.0, 0.40), None, 'tyres on snow / ice (follow the speed)'),
            ('Fire_Stove', 'vfx', 'Stove', (sx1 - 0.15, yc, FLOOR + 0.28), (1.0, 0.0, 0.0),
             'fire in the stove (VFX); lamp LIGHT_Stove (type stove) is its light; StoveGlow lights up'),
            ('Stove_Load', 'item_slot', 'Stove', (sx1 + 0.04, yc, FLOOR + 0.31), (-1.0, 0.0, 0.0),
             'logs go in here (door open)'),
            ('VFX_EngineSteam', 'vfx', 'EngineBay', (1.19, 0.0, 1.13), (0.0, 0.0, 1.0),
             'steam out of the engine bay when it boils over (through the cover seams, or straight up with the cover open)'),
            ('VFX_RadiatorSteam', 'vfx', 'Kit_Front', (2.14, 0.0, 1.31), (0.6, 0.0, 0.8), 'steam out of the radiator hatch')):
        socket(name, pos, kind, note=note, parent=par)
        if d is not None:
            CONTRACT['sockets'][name]['dir'] = list(d)
    # hide points: pose, hip, eye, facing; below_windows = the eye is under the window band
    for name, pose, hip, eye, face, note in (
            ('Hide_Footwell_P', 'crouch', (1.55, -0.48, 0.80), (1.48, -0.45, 1.02), (-1, 0, 0), 'down in the passenger footwell'),
            ('Hide_Footwell_D', 'crouch', (1.47, 0.48, 0.80), (1.42, 0.45, 1.02), (-1, 0, 0), 'down behind the pedals'),
            ('Hide_CabSeat', 'lie', (1.12, -0.53, 1.04), (1.12, -0.36, 1.19), (0, 1, 0), 'curled up on the passenger seat'),
            ('Hide_Bench_L2', 'lie', (-0.57, 0.66, 1.17), (-0.80, 0.66, 1.27), (0, -1, 0),
             'flat across the folding seats L2 and L3 (both must be down)'),
            ('Hide_Aisle', 'lie', (-0.35, 0.05, 0.76), (-0.75, 0.05, 0.86), (1, 0, 0), 'flat on the saloon floor'),
            ('Hide_RearRight', 'crouch', (-1.80, -0.25, 0.76), (-1.74, -0.25, 1.14), (1, 0, 0),
             'crouched by the rear doors behind the cargo')):
        socket(name, hip, 'hide', note=note, parent='Seat_L2' if name == 'Hide_Bench_L2' else 'Kuzov')
        CONTRACT['sockets'][name].update(pose=pose, eye=list(eye), facing=list(face))


# ================================================================ textures: fog and handprints, snow on the windscreen
def _noise(H, W, scale, seed):
    from scipy import ndimage
    g = np.random.default_rng(seed).random((int(H / scale) + 2, int(W / scale) + 2)).astype(np.float32)
    return ndimage.zoom(g, (H / (g.shape[0] - 1), W / (g.shape[1] - 1)), order=3)[:H, :W]


def _q(x, lv, bay):
    return np.floor(np.clip(x, 0, 1) * (lv - 1) + bay) / (lv - 1)


def uniform_alpha8(a, bay, lv=16):
    """'when it freezes / settles' mask with a flat histogram: the order of the texels is kept, the values are spread
    evenly, so at amount t (texel shown where alpha > 1 - t) about t of the glass is covered: none at 0, all at 1.
    lv dithered levels at (k + 0.5) / lv"""
    r = np.argsort(np.argsort(a.ravel(), kind='stable'), kind='stable').reshape(a.shape).astype(np.float32)
    u = (r + 0.5) / r.size
    k = np.clip(np.floor(u * lv + bay - 0.5), 0, lv - 1)
    return np.round((k + 0.5) / lv * 255).astype(np.uint8)


def mask_textures(tex):
    """T_Van_Fog (side windows: RGB = condensation, A = when it mists up: the bottom and the corners first, then it
    climbs; drips run down), T_Van_Handprints (2 x 2 atlas: palm prints and finger smears, A = print),
    T_Van_Snow (windscreen: RGB = snow, A = when it settles: the bottom edge and the corners, then drifts)"""
    from PIL import Image
    from psxlib import BAYER4
    out = []
    H, W = 128, 256
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = (xx + 0.5) / W, 1 - (yy + 0.5) / H
    bay = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W]
    n1, n2, n3 = _noise(H, W, 18, 11), _noise(H, W, 6, 12), _noise(H, W, 2.5, 13)
    d_edge = np.minimum.reduce([v * 0.62 + 0.04, u * 1.1 + 0.12 * v, (1 - u) * 1.1 + 0.12 * v])
    grow = d_edge - 0.14 * (n1 - 0.5) - 0.05 * (n2 - 0.5)
    a = 1.0 - np.clip(grow / 0.55, 0, 1)                         # the bottom and the sides mist up first
    drips = (np.abs(np.sin(u * 23.0 + n1 * 2.5)) > 0.996) * (v < 0.35 + 0.25 * n2) * (v > 0.04)
    a = np.where(drips, a * 0.4, a)
    rgb = np.stack([0.74 + 0.10 * n3, 0.77 + 0.10 * n3, 0.80 + 0.09 * n3], -1)
    img = np.dstack([(np.clip(_q(rgb[..., i], 16, bay), 0, 1) * 255).astype(np.uint8) for i in range(3)] +
                    [uniform_alpha8(a, bay)])
    p = tex + '/T_Van_Fog.png'
    Image.fromarray(img, 'RGBA').save(p)
    out.append(p)
    # handprints, 2 x 2 tiles of 64 px: palm + four fingers + thumb, a smear running down
    S = 128
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    A = np.zeros((S, S), np.float32)
    rng = np.random.default_rng(5)

    def seg_d(px, py, ax_, ay_, bx_, by_):
        vx, vy = bx_ - ax_, by_ - ay_
        t = np.clip(((px - ax_) * vx + (py - ay_) * vy) / (vx * vx + vy * vy), 0, 1)
        return np.hypot(px - ax_ - t * vx, py - ay_ - t * vy)
    for t in range(4):
        ox, oy = (t % 2) * 64 + 32, (t // 2) * 64 + 36
        rot = math.radians(rng.uniform(-25, 25))
        cs, sn = math.cos(rot), math.sin(rot)
        lx, ly = xx - ox, yy - oy
        X, Y = cs * lx + sn * ly, -sn * lx + cs * ly                  # hand frame: fingers towards -Y (up)
        m = np.clip(1.3 - np.hypot(X / 10.5, Y / 12.0), 0, 1)        # palm
        for (bx_, by_, tx, ty, w_) in ((-8, -9, -12, -26, 2.6), (-3, -10, -4, -30, 2.8), (3, -10, 4, -30, 2.8),
                                       (8, -9, 11, -25, 2.5), (10, 2, 21, -8, 2.7)):
            m = np.maximum(m, np.clip(1.4 - seg_d(X, Y, bx_, by_, tx, ty) / w_, 0, 1))
        smear = np.clip(1.2 - np.abs(X) / 8.0, 0, 1) * (Y > 6) * np.exp(-(Y - 6) / (5.0 + 6.0 * t)) * 0.7
        m = np.maximum(m, smear) * (np.abs(lx) < 31) * (np.abs(ly + 4) < 31)
        A = np.maximum(A, np.clip(m, 0, 1))
    nz = _noise(S, S, 3, 21)
    A = np.clip(A * (0.70 + 0.5 * nz), 0, 1)
    bay2 = np.tile(BAYER4, (S // 4, S // 4))
    a8 = (np.clip(_q(A, 8, bay2), 0, 1) * 255).astype(np.uint8)
    img = np.dstack([np.full((S, S), 236, np.uint8)] * 3 + [a8])
    p = tex + '/T_Van_Handprints.png'
    Image.fromarray(img, 'RGBA').save(p)
    out.append(p)
    # snow on the windscreen (same 0..1 UVs as the frost)
    H, W = 128, 256
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = (xx + 0.5) / W, 1 - (yy + 0.5) / H
    n1, n2, n3 = _noise(H, W, 20, 31), _noise(H, W, 7, 32), _noise(H, W, 2.0, 33)
    pane_u = np.where(u < 0.5, u / 0.5, (u - 0.5) / 0.5)
    d_edge = np.minimum.reduce([pane_u * 0.8, (1 - pane_u) * 0.8, v * 0.35, (1 - v) * 1.4])
    grow = d_edge - 0.16 * (n1 - 0.5) - 0.06 * (n2 - 0.5)
    a = 1.0 - np.clip(grow / 0.45, 0, 1)
    rgb = np.stack([0.88 + 0.08 * n3, 0.90 + 0.07 * n3, 0.94 + 0.05 * n3], -1) - 0.06 * (n2 > 0.7)[..., None]
    bay = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W]
    img = np.dstack([(np.clip(_q(rgb[..., i], 16, bay), 0, 1) * 255).astype(np.uint8) for i in range(3)] +
                    [uniform_alpha8(a, bay)])
    p = tex + '/T_Van_Snow.png'
    Image.fromarray(img, 'RGBA').save(p)
    out.append(p)
    return out


def fog_uvs(windows, glass_mats):
    """second UV map FOG on every side / rear window: 0..1 across each pane, u from the front edge seen from outside,
    v up (Kuzov: the saloon panes; doors and sliding panes: their own glass); other faces (0, 0)"""
    done = {}
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.data.materials or o.name == 'lob':
            continue
        me = o.data
        gi = {i for i, m in enumerate(me.materials) if m and m.name in glass_mats}
        polys = [p for p in me.polygons if p.material_index in gi and p.area > 0.003] if gi else []
        if not polys:
            continue
        uv = me.uv_layers.get('FOG') or me.uv_layers.new(name='FOG')
        for d in uv.data:
            d.uv = (0.0, 0.0)
        Mw, R3 = o.matrix_world, o.matrix_world.to_3x3()
        groups = {}
        for p in polys:
            n = (R3 @ p.normal).normalized()
            key = ('y', 1 if n.y > 0 else -1) if abs(n.y) >= abs(n.x) else ('x', 1 if n.x > 0 else -1)
            groups.setdefault(key, []).append(p)
        for (ax, sg), ps in groups.items():
            pts = np.array([tuple(Mw @ me.vertices[i].co) for p in ps for i in p.vertices])
            h_ax = 0 if ax == 'y' else 1
            obox = (pts[:, h_ax].min(), pts[:, h_ax].max(), pts[:, 2].min(), pts[:, 2].max())
            for p in ps:
                c = Mw @ p.center
                box = obox
                if o.name == 'Kuzov' and ax == 'y':
                    for (x0, x1, sd, zb, zt) in windows:
                        if x0 - 0.05 < c.x < x1 + 0.05 and sd == sg:
                            box = (x0, x1, zb, zt)
                            break
                for li in p.loop_indices:
                    co = Mw @ me.vertices[me.loops[li].vertex_index].co
                    h = co.x if ax == 'y' else co.y
                    uu = (h - box[0]) / max(box[1] - box[0], 1e-4)
                    if (ax == 'y' and sg > 0) or (ax == 'x' and sg < 0):
                        uu = 1 - uu                                   # seen from outside, u runs from the front edge
                    vv = (co.z - box[2]) / max(box[3] - box[2], 1e-4)
                    uv.data[li].uv = (min(max(uu, 0.0), 1.0), min(max(vv, 0.0), 1.0))
        done[o.name] = len(polys)
    return done


# ================================================================ post-bake: wheels, spare, snow blend shapes
def _set_origin(ob, p):
    """move the origin of ob to the world point p without moving the geometry"""
    M = ob.matrix_world.copy()
    lp = M.inverted() @ Vector(p)
    ob.data.transform(Matrix.Translation(-lp))
    ob.matrix_world = M @ Matrix.Translation(lp)


def _attach(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def wheels_post(WS, spare_hub):
    """after the scale: Wheel_FL/FR/RL/RR with their origin at the hub, Steer_FL/FR hinges for the front pair, six nuts
    per wheel split off (twist parts), a Flat blend shape on each tyre, and the spare = a copy of a road wheel on the
    carrier (outer face back) with its wing nut.  Returns {corner: hub centre} (world, ground frame)"""
    found = [o for o in bpy.data.objects if o.name == 'Wheel' or o.name.startswith('Wheel.')]
    hubs = {}
    for w in found:
        co = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
        c = Vector(((co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2, WHEEL_R_FINAL))
        k = ('F' if c.x > 0 else 'R') + ('L' if c.y > 0 else 'R')
        w.name = 'Wheel_' + k
        w.data.name = 'Wheel_' + k
        w['orig'] = w.name
        _set_origin(w, c)
        hubs[k] = c
    nut_r = VM.WHEEL_NUT_R * WS
    nuts = {}
    for k, c in hubs.items():
        w = bpy.data.objects['Wheel_' + k]
        out = Vector((0, 1 if c.y > 0 else -1, 0))
        me = w.data
        groups = {i: [] for i in range(6)}
        for p in me.polygons:
            pc = w.matrix_world @ p.center
            d = pc - c
            ax = d.dot(out)
            rad = (d - out * ax)
            if ax > 0.0625 * WS and abs(rad.length - nut_r) < 0.0135 * WS:
                ang = math.atan2(rad.z, rad.x)
                gi = int(round(ang / (math.pi / 3))) % 6
                groups[gi].append(p.index)
        made = []
        for gi, faces in groups.items():
            if not faces:
                continue
            name = f'Wheel_{k}_Nut_{gi + 1}'
            fs = set(faces)
            new_me = me.copy()
            no = bpy.data.objects.new(name, new_me)
            bpy.context.scene.collection.objects.link(no)
            no.matrix_world = w.matrix_world.copy()
            bm = bmesh.new()
            bm.from_mesh(new_me)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in fs], context='FACES')
            bm.to_mesh(new_me)
            bm.free()
            nc = np.array([tuple(no.matrix_world @ v.co) for v in new_me.vertices])
            ctr = Vector(nc.mean(0))
            base = ctr - out * ((ctr - c).dot(out) - 0.062 * WS)
            _set_origin(no, base)
            no['orig'] = name
            made.append((name, base, fs))
        allf = set().union(*[m[2] for m in made]) if made else set()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in allf], context='FACES')
        bm.to_mesh(me)
        bm.free()
        me.update()
        nuts[k] = [(m[0], m[1]) for m in made]
    # the spare: a copy of the left front wheel (outer face +y) turned so its outer face looks back (-x)
    src = bpy.data.objects['Wheel_FL']
    sp = bpy.data.objects.new('SpareWheel', src.data.copy())
    sp.data.name = 'SpareWheel'
    bpy.context.scene.collection.objects.link(sp)
    hub = Vector(spare_hub)
    ctr = hub + Vector((-0.1715 - 0.002, 0.0, 0.02))
    sp.matrix_world = Matrix.Translation(ctr) @ Matrix.Rotation(math.radians(90), 4, 'Z')
    sp['orig'] = 'SpareWheel'
    nut_src = bpy.data.objects[nuts['FL'][0][0]]
    wn = bpy.data.objects.new('SpareWheel_Nut', nut_src.data.copy())
    wn.data.name = 'SpareWheel_Nut'
    bpy.context.scene.collection.objects.link(wn)
    wn_pos = ctr + Vector((-(0.090 * WS) - 0.003, 0.0, 0.0))
    wn.matrix_world = Matrix.Translation(wn_pos) @ Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Scale(1.7, 4)
    wn['orig'] = 'SpareWheel_Nut'
    # flat tyre blend shape (road wheels only)
    for k, c in hubs.items():
        w = bpy.data.objects['Wheel_' + k]
        out = Vector((0, 1 if c.y > 0 else -1, 0))
        w.shape_key_add(name='Basis')
        key = w.shape_key_add(name='Flat')
        R = 0.364
        for i, vtx in enumerate(w.data.vertices):
            p = vtx.co.copy()                                    # local = world - hub (no rotation)
            r_xz = math.hypot(p.x, p.z)
            if r_xz > 0.20 * WS and p.z < -0.45 * R:
                zf = -0.80 * R
                if p.z < zf:
                    t = min(1.0, (zf - p.z) / (R - 0.80 * R + 1e-6))
                    p.z = zf - 0.004 * t
                    p.y += math.copysign(0.025 * t, p.y if abs(p.y) > 1e-4 else out.y)
                else:
                    t = (p.z - (-0.45 * R)) / (zf + 0.45 * R)
                    p.y += math.copysign(0.012 * max(0.0, min(1.0, t)), p.y if abs(p.y) > 1e-4 else out.y)
            key.data[i].co = p
    return hubs, nuts, ctr, wn_pos


def snow_blendshapes():
    """blend shape Clear on the snow blankets: every vertex down to its base (snow gone)"""
    for name, base in SNOW_BASE.items():
        ob = bpy.data.objects.get(name)
        if ob is None or not base:
            continue
        kd = kdtree.KDTree(len(base))
        for i, (full, _) in enumerate(base):
            kd.insert(Vector(full), i)
        kd.balance()
        ob.shape_key_add(name='Basis')
        key = ob.shape_key_add(name='Clear')
        M = ob.matrix_world
        Mi = M.inverted()
        for i, v in enumerate(ob.data.vertices):
            wco = M @ v.co
            _, j, _ = kd.find(wco)
            tgt = Vector((wco.x, wco.y, base[j][1]))
            key.data[i].co = Mi @ tgt


# ================================================================ colliders (lifted frame, in van3_build section 11)
def static_boxes(L, side_door, hatch):
    """the hollow shell of the van and the big things inside, as boxes (x0, x1, y0, y1, z0, z1) in the body frame
    (before the lift; L is added).  parent = the object the box rides on"""
    sd, h = side_door, hatch
    B = [  # name, parent, (x0, x1, y0, y1, z0, z1)
        ('Floor', 'Kuzov', (-2.10, 0.888, -0.90, 0.90, 0.616, 0.716)),
        ('FloorCab', 'Kuzov', (0.888, 1.98, -0.90, 0.90, 0.645, 0.745)),
        ('RoofRear', 'Kuzov', (-2.15, h['x0'], -0.98, 0.98, 1.941, 2.06)),
        ('RoofFront', 'Kuzov', (h['x1'], 1.95, -0.98, 0.98, 1.941, 2.06)),
        ('RoofHatchL', 'Kuzov', (h['x0'], h['x1'], h['y1'], 0.98, 1.941, 2.06)),
        ('RoofHatchR', 'Kuzov', (h['x0'], h['x1'], -0.98, h['y0'], 1.941, 2.06)),
        ('WallL', 'Kuzov', (-2.10, 0.87, 0.90, 0.99, 0.716, 1.946)),
        ('WallR_Rear', 'Kuzov', (-2.10, sd['x0'] - 0.007, -0.99, -0.90, 0.716, 1.946)),
        ('WallR_Front', 'Kuzov', (sd['x1'] + 0.017, 0.87, -0.99, -0.90, 0.716, 1.946)),
        ('CabFront', 'Kuzov', (1.95, 2.15, -0.95, 0.95, 0.75, 1.95)),
        ('APillarL', 'Kuzov', (1.862, 1.98, 0.80, 0.99, 0.75, 1.95)),
        ('APillarR', 'Kuzov', (1.862, 1.98, -0.99, -0.80, 0.75, 1.95)),
        ('Dash', 'Dash', (1.70, 1.98, -0.845, 0.845, 1.06, 1.372)),
        ('Partition', 'Kuzov', (0.888, 0.93, -0.90, 0.90, 0.716, 1.37)),
        ('ArchL', 'Kuzov', (-1.55, -0.90, 0.65, 0.90, 0.716, 0.916)),
        ('ArchR', 'Kuzov', (-1.55, -0.90, -0.90, -0.65, 0.716, 0.916)),
        ('CabSeatD', 'Kuzov', (0.95, 1.40, 0.28, 0.80, 0.745, 1.023)),
        ('CabSeatP', 'Kuzov', (0.95, 1.40, -0.80, -0.28, 0.745, 1.023)),
        ('CabSeatBackD', 'Kuzov', (0.89, 0.98, 0.28, 0.80, 1.023, 1.70)),
        ('CabSeatBackP', 'Kuzov', (0.89, 0.98, -0.80, -0.28, 1.023, 1.70)),
        ('SeatBacksL', 'Kuzov', (-1.302, 0.642, 0.809, 0.90, 1.10, 1.376)),
        ('SeatBackR1', 'Kuzov', (-1.252, -0.748, -0.90, -0.809, 1.10, 1.376)),
        ('SeatBackR2', 'Kuzov', (0.368, 0.872, -0.90, -0.809, 1.10, 1.376)),
        ('TableTop', 'Kuzov', (-1.24, -0.84, -0.22, 0.22, 1.331, 1.356)),
        ('TableLeg', 'Kuzov', (-1.065, -1.015, -0.025, 0.025, 0.716, 1.331)),
        ('Stove', 'Stove', (-2.045, -1.695, 0.405, 0.775, 0.716, 1.261)),
        ('StovePipe', 'Stove', (-1.975, -1.865, 0.575, 0.685, 1.276, 1.941)),
        ('WoodBox', 'WoodBox', (-1.50, -1.33, 0.06, 0.38, 0.716, 0.956)),
        ('Cargo', 'Cargo', (-2.04, -1.46, -0.82, -0.44, 0.716, 1.416)),
        ('Extinguisher', 'Kuzov', (0.77, 0.88, 0.70, 0.82, 0.716, 1.116)),
        ('BatteryBox', 'BatteryBox', (0.238, 0.542, 0.546, 0.87, 0.716, 0.98)),
        ('Underbody', 'Kuzov', (-2.10, 2.10, -0.60, 0.60, 0.38, 0.616)),
        ('Tanks', 'FuelTanks', (-0.15, 0.62, -0.851, 0.851, 0.265, 0.616)),
        ('BumperF', 'Kit_Front', (2.19, 2.45, -0.99, 0.99, 0.50, 0.70)),
        ('BullBar', 'Kit_Front', (2.33, 2.38, -0.48, 0.48, 0.655, 1.105)),
        ('BumperR', 'Kuzov', (-2.251, -1.884, -0.97, 0.97, 0.481, 0.693)),
        # roof rack: a deck at the cross-bar level with a hole over the vent hatch (its lid rises above the bars)
        # (deck top 2.295 m after the lift: the shovel and the spout lie on the bars from 2.296 m)
        ('RoofRackRear', 'Kit_RoofRack', (-1.716, -0.616, -0.816, 0.816, 2.18, 2.205)),
        ('RoofRackFront', 'Kit_RoofRack', (-0.250, 1.166, -0.816, 0.816, 2.18, 2.205)),
        ('RoofRackMidL', 'Kit_RoofRack', (-0.616, -0.250, -0.150, 0.816, 2.18, 2.205)),
        ('RoofRackMidR', 'Kit_RoofRack', (-0.616, -0.250, -0.816, -0.650, 2.18, 2.205)),
        ('LightBar', 'Kit_RoofRack', (1.17, 1.27, -0.62, 0.62, 2.215, 2.355)),     # the four lamps on the rack front
        ('RoofLoadCrate', 'Kit_RoofLoad', (0.22, 0.76, -0.70, -0.22, 2.22, 2.52)),
        ('RoofLoadBag', 'Kit_RoofLoad', (0.49, 0.71, 0.05, 0.74, 2.22, 2.44)),
        ('doorL', 'doorL', (0.867, 1.862, 0.86, 0.99, 0.518, 1.88)),
        ('doorP', 'doorP', (0.867, 1.862, -0.99, -0.86, 0.518, 1.88)),
        ('doorSalon', 'doorSalon', (sd['x0'] - 0.007, sd['x1'] + 0.017, -0.99, -0.90, 0.636, 1.886)),
        ('doorZL', 'doorZL', (-2.20, -2.09, 0.0, 0.713, 0.62, 1.86)),
        ('dooZP', 'dooZP', (-2.20, -2.09, -0.713, 0.0, 0.62, 1.86)),
        ('Ladder', 'doorZL', (-2.25, -2.22, 0.186, 0.594, 0.62, 1.86)),
    ]
    return [(n, p, (b[0], b[1], b[2], b[3], b[4] + L, b[5] + L)) for n, p, b in B]


def colliders_build(L, side_door, hatch):
    """box proxies COL_<name> (wire, not rendered) in a Colliders collection, parented like the boxes; returns the
    contract list: name, parent, centre and size in the parent's local frame, the centre in the body frame and the
    parent's origin in the body frame (Kuzov, Dash, Kit_* and Cargo sit at z = L after the lift)"""
    coll = bpy.data.collections.get('Colliders') or bpy.data.collections.new('Colliders')
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    out = []
    bpy.context.view_layer.update()
    for name, par, (x0, x1, y0, y1, z0, z1) in static_boxes(L, side_door, hatch):
        P = bpy.data.objects.get(par) or bpy.data.objects['Kuzov']
        c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        size = Vector((x1 - x0, y1 - y0, z1 - z0))
        kb = KB()
        kb.box(x0, x1, y0, y1, z0, z1, 0)
        ob = kb.to_object('COL_' + name, coll=coll)
        ob.display_type = 'WIRE'
        ob.hide_render = True
        ob['collider'] = 'box'
        _attach(ob, P)
        lc = P.matrix_world.inverted() @ c
        out.append(dict(name='COL_' + name, parent=P.name, type='box', center=[round(v, 4) for v in lc],
                        size=[round(v, 4) for v in size], center_body=[round(v, 4) for v in c],
                        parent_origin=[round(v, 4) for v in P.matrix_world.translation]))
    return out


def part_boxes(parts):
    """a box per moving part in its own local frame (from its vertices): the grab / hit volume that moves with it"""
    n = 0
    for k, p in parts.items():
        o = bpy.data.objects.get(p.get('object') or '')
        if o is None or o.type != 'MESH' or not o.data.vertices or p['kind'] == 'static' or k.startswith(('Needle_', 'Lens_')):
            continue
        co = np.array([tuple(v.co) for v in o.data.vertices])
        lo, hi = co.min(0), co.max(0)
        sz = np.maximum(hi - lo, 0.004)
        p['box'] = dict(center=[round(float(v), 4) for v in (lo + hi) / 2], size=[round(float(v), 4) for v in sz])
        n += 1
    return n


def knock_points(sockets, windows, L):
    """points on the outside of the body where something knocks, scratches or leaves a hand print: rays from outside
    onto the evaluated scene (lifted frame); the socket gets the hit object as parent and the outward normal as dir"""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    rays = []
    for i, x in enumerate((-1.55, -0.75, 0.05, 0.85, 1.55)):
        rays.append((f'Knock_Roof_{i + 1}', (x, 0.0, 3.5), (0, 0, -1), 'knock'))
    for i, x in enumerate((-1.60, -0.90, -0.10, 0.60)):
        rays.append((f'Knock_WallL_{i + 1}', (x, 2.0, 1.55 + L), (0, -1, 0), 'knock'))
    for i, x in enumerate((-1.60, -1.00, 0.60)):
        rays.append((f'Knock_WallR_{i + 1}', (x, -2.0, 1.55 + L), (0, 1, 0), 'knock'))
    rays += [('Knock_doorSalon', (-0.12, -2.0, 1.25 + L), (0, 1, 0), 'knock'),
             ('Knock_doorZL', (-3.2, 0.35, 1.30 + L), (1, 0, 0), 'knock'),
             ('Knock_dooZP', (-3.2, -0.30, 1.75 + L), (1, 0, 0), 'knock'),
             ('Knock_doorL', (1.35, 2.0, 1.20 + L), (0, -1, 0), 'knock'),
             ('Knock_doorP', (1.35, -2.0, 1.20 + L), (0, 1, 0), 'knock'),
             ('Knock_Floor', (-0.60, 0.0, -0.5), (0, 0, 1), 'knock')]
    for k, (x0, x1, sd, zb, zt) in enumerate(windows):
        rays.append((f'Handprint_{"L" if sd > 0 else "R"}{k % 3 + 1}', ((x0 + x1) / 2, sd * 2.0, (zb + zt) / 2 + L),
                     (0, -sd, 0), 'decal'))
    rays += [('Handprint_lob', (3.0, 0.25, 1.68 + L), (-1, 0, 0), 'decal'),
             ('Handprint_doorL', (1.10, 2.0, 1.62 + L), (0, -1, 0), 'decal'),
             ('Handprint_doorP', (1.10, -2.0, 1.62 + L), (0, 1, 0), 'decal'),
             ('Handprint_doorZL', (-3.2, 0.35, 1.62 + L), (1, 0, 0), 'decal')]
    made = 0
    for name, o, d, kind in rays:
        org = Vector(o)
        for _ in range(6):
            hit, loc, nrm, idx, ob, mw = sc.ray_cast(dg, org, Vector(d), distance=5.0)
            if not hit or not ob.name.startswith(('Snow_', 'Chains_', 'COL_')):
                break
            org = loc + Vector(d) * 0.002
        if not hit:
            continue
        while ob.parent is not None and ob.name.startswith(('Lens_', 'Seat_')):
            ob = ob.parent
        n_out = Vector(nrm).normalized()              # the surface normal, turned to face the ray's origin (outside)
        if n_out.dot(Vector(d)) > 0:
            n_out = -n_out
        note = {'knock': 'something knocks / scratches here from outside (sound, dent decal)',
                'decal': 'hand print from outside: decal from T_Van_Handprints on the fogged glass (FOG UVs)'}[kind]
        if name == 'Handprint_lob':
            note = ('hand print from outside on the windscreen: lob has no FOG layer - use its main UV (0..1, as the '
                    'frost / snow masks) for the print')
        sockets[name] = dict(pos=[round(v, 4) for v in loc], kind=kind, parent=ob.name, note=note,
                             dir=[round(v, 3) for v in n_out])
        made += 1
    return made


def stove_parts(VP):
    """pivots and contract for the stove pieces built separately by van2_props.build(v3=True)"""
    s = VP.STOVE
    sx0, sx1, sy0, sy1 = s['x0'], s['x1'], s['y0'], s['y1']
    hx, hy = (sx0 + sx1) / 2 - 0.05, (sy0 + sy1) / 2 + 0.04
    yc = (sy0 + sy1) / 2
    kx, ky = sx1 - 0.08, sy0 + 0.085                  # kettle on the front-aisle corner of the top, clear of the flue
    LOG = lambda i: Vector((-1.453 + 0.076 * (i % 2), 0.22, FLOOR + 0.048 + 0.07 * (i // 2)))  # 2 x 2 in the open crate
    spec = [
        ('Stove', 'static', ((sx0 + sx1) / 2, yc, FLOOR), None, None, 'Kuzov', [], 'wood stove with the flue through the roof'),
        ('StoveGlow', 'static', (sx1 + 0.001, yc, FLOOR + 0.31), None, None, 'Stove', ['dark', 'glowing'],
         'the fire seen through the open door: emissive (M_Van_StoveGlow) while it burns'),
        ('WoodBox', 'static', (-1.415, 0.22, FLOOR), None, None, 'Kuzov', [],
         'box for the firewood, beside the stove-front space on the aisle side (clear of the door swing and the ash pan)'),
        ('StoveDoor', 'hinge', (sx1 + 0.006, sy1 - 0.07, FLOOR + 0.32), (0, 0, 1), (0, 110), 'Stove', ['closed', 'open'],
         'stove door, hinged on the wall side; logs go in through Stove_Load'),
        ('StoveDoor_Vent', 'slide', (sx1 + 0.014, sy0 + 0.165, FLOOR + 0.245), (0, 1, 0), (0, 0.03), 'StoveDoor',
         ['shut', 'open'], 'air vent on the door: more air = hotter and faster'),
        ('Stove_AshPan', 'slide', (sx1 + 0.010, yc, FLOOR + 0.1375), (1, 0, 0), (0, 0.15), 'Stove', ['in', 'out'],
         'ash pan: pull it out to empty it'),
        ('Stove_Damper', 'twist', (hx, hy, 1.45), (1, 0, 0), (0, 90), 'Stove', ['open', 'shut'],
         'flue damper: shut it too early and the saloon fills with smoke'),
        ('Kettle', 'item', (kx, ky, FLOOR + 0.545), (0, 0, 1), None, 'Stove', ['empty', 'cold', 'hot'],
         'kettle on the stove: hot water for tea or for the radiator on a cold start (Pour_Radiator)'),
    ]
    for i in range(4):
        spec.append((f'Log_{i + 1}', 'item', LOG(i), (0, 1, 0), None,
                     'WoodBox', [], 'firewood log: put it in the stove (Stove_Load)'))
    for name, kind, piv, axis, rng, par, states, note in spec:
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        set_pivot(o, piv)
        part(name, kind, piv, axis, rng, parent=par, unit='m' if kind == 'slide' else 'deg', states=states, note=note)
    socket('Hand_StoveDoor', (sx1 + 0.045, sy0 + 0.095, FLOOR + 0.32), 'hand', parent='StoveDoor')
    socket('Hand_StoveDoor_Vent', (sx1 + 0.018, sy0 + 0.165, FLOOR + 0.245), 'hand', parent='StoveDoor_Vent')
    socket('Hand_Stove_AshPan', (sx1 + 0.03, yc, FLOOR + 0.1375), 'hand', parent='Stove_AshPan')
    socket('Hand_Stove_Damper', (hx + 0.125, hy, 1.45), 'hand', parent='Stove_Damper')
    socket('Hand_Kettle', (kx, ky, FLOOR + 0.695), 'hand', parent='Kettle')
    socket('Pour_Kettle', (kx + 0.125, ky, FLOOR + 0.62), 'pour', parent='Kettle')
    for i in range(4):
        socket(f'Hand_Log_{i + 1}', LOG(i) + Vector((0, 0, 0.035)), 'hand', parent=f'Log_{i + 1}')
