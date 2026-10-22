"""Concept 1 «Кунг»: cab-over 4x4 truck with an insulated box body (stove, benches, table, lamp)."""
import math
from mathutils import Vector, Matrix
import vlib as V
import parts as P

NAME = 'Кунг'
CAMS = {
    'day': ((5.9, 3.3, 1.55), (-0.7, 0, 1.5), 24),
    'night': ((-6.8, 4.7, 1.55), (-1.3, 0, 1.8), 26),
    'inside': ((-2.3, -0.12, 2.28), (0.45, 0.18, 1.92), 17),
    'side': ((-0.2, 20, 1.75), (-0.2, 0, 1.75), 30, 9.0),
}
DIMS = dict(L=6.3, W=2.32, H=3.62, seats='2 в кабине + 5 в кунге', wheelbase=3.3)


def set_origin(ob, p):
    ob.data.transform(Matrix.Translation(-Vector(p)))
    ob.location = p


def pane(name, x0, x1, y0, y1, z0, z1, col=None):
    return V.box(name, x0, x1, y0, y1, z0, z1, V.glass(), col)


def build():
    c = V.coll('Vehicle')
    m = P.M()
    liv = V.livery('liv1', band=(1.62, 1.84), dirt=(0.4, 1.35))
    lin = V.twotone('lin1', 2.02)
    cab_in = V.flatcol('cab_in', (0.30, 0.28, 0.24), 0.8)
    dark = m['dark']
    R, W, xF, xR, ty = 0.53, 0.34, 1.95, -1.35, 0.92
    night = []

    # ---------------------------------------------------------------- chassis, wheels
    for s in (1, -1):
        V.box(f'rail{s}', -2.95, 2.72, s * 0.38, s * 0.48, 0.62, 0.84, dark, c)
        for xa in (xF, xR):
            V.wheel(f'wh_{xa}_{s}', xa, s * ty, R, R, W, outward=s, col=c)
    for xx in (2.3, 0.9, -0.4, -2.0):
        V.box(f'xm{xx}', xx - 0.05, xx + 0.05, -0.38, 0.38, 0.66, 0.80, dark, c)
    for xa in (xF, xR):
        V.cyl(f'axle{xa}', (xa, 0, R), 'y', 0.07, 2 * ty - 0.2, 10, dark, c)
        V.box(f'diff{xa}', xa - 0.18, xa + 0.18, -0.16, 0.16, R - 0.17, R + 0.17, dark, c)
    bump = V.box('bumper', 2.70, 2.94, -1.12, 1.12, 0.60, 0.86, dark, c)
    V.bevel(bump, 0.03, 1)
    for s in (1, -1):
        V.box(f'hook{s}', 2.94, 3.04, s * 0.52, s * 0.62, 0.66, 0.74, m['red'], c)
    tank = V.cyl('tank', (0.12, 0.80, 0.84), 'x', 0.2, 1.1, 14, liv, c)
    V.box('toolbox', -0.45, 0.55, -1.02, -0.58, 0.62, 1.0, dark, c)

    # ---------------------------------------------------------------- cab
    prof_o = [(1.02, 0.98), (2.74, 0.98), (2.78, 1.68), (2.64, 2.36), (2.50, 2.50), (1.02, 2.50)]
    prof_i = [(1.07, 1.03), (2.69, 1.03), (2.73, 1.66), (2.60, 2.31), (2.47, 2.45), (1.07, 2.45)]
    co = V.prism_y('cab', prof_o, -1.08, 1.08)
    V.bevel(co, 0.09, 2, 30)
    ci = V.prism_y('cab_i', prof_i, -1.03, 1.03)
    V.bevel(ci, 0.04, 1, 30)
    cab = V.shell('Cab', co, ci, liv, cab_in, c)
    cuts = []
    for y0, y1 in ((0.06, 0.96), (-0.96, -0.06)):
        cuts.append(V.prism_y('ws', [(2.45, 1.76), (3.0, 1.76), (3.0, 2.33), (2.45, 2.33)], y0, y1, dark))
    for s in (1, -1):
        cuts.append(V.box('sw', 1.72, 2.46, *sorted((s * 0.9, s * 1.3)), 1.78, 2.32, dark))
    cuts.append(V.box('rw', 0.9, 1.2, -0.32, 0.32, 1.92, 2.28, dark))
    cuts.append(V.cyl('arch', (xF, 0, R), 'y', 0.68, 2.6, 20, dark))
    V.bdiff(cab, cuts)
    V.set_smooth(cab, 35)

    def xm(z):
        return 2.755 - (z - 1.67) / 0.68 * 0.135
    for y0, y1 in ((0.06, 0.96), (-0.96, -0.06)):
        V.prism_y('ws_gl', [(xm(1.76) - 0.004, 1.76), (xm(1.76) + 0.004, 1.76), (xm(2.33) + 0.004, 2.33),
                            (xm(2.33) - 0.004, 2.33)], y0, y1, V.glass(), c)
    for s in (1, -1):
        pane('sw_gl', 1.72, 2.46, *sorted((s * 1.045, s * 1.055)), 1.78, 2.32, c)
        V.box(f'seam_a{s}', 1.655, 1.67, *sorted((s * 1.075, s * 1.09)), 1.0, 2.45, dark, c)
        V.box(f'seam_b{s}', 2.575, 2.59, *sorted((s * 1.075, s * 1.09)), 1.25, 2.40, dark, c)
        V.box(f'handle{s}', 1.72, 1.84, *sorted((s * 1.08, s * 1.11)), 1.70, 1.74, m['metal'], c)
        V.box(f'step{s}', 1.75, 2.35, *sorted((s * 0.98, s * 1.16)), 0.70, 0.74, m['metal'], c)
        P.mirror(f'mirror{s}', (2.50, s * 1.07, 2.02), (2.58, s * 1.33, 2.06), m, c)
        V.box(f'flare{s}', 1.30, 2.62, *sorted((s * 1.02, s * 1.14)), 1.17, 1.24, dark, c)
    pane('rw_gl', 1.04, 1.05, -0.32, 0.32, 1.92, 2.28, c)
    V.box('grille', 2.745, 2.80, -0.6, 0.6, 1.10, 1.58, dark, c)
    for k in range(4):
        V.box(f'slat{k}', 2.79, 2.82, -0.56, 0.56, 1.16 + k * 0.11, 1.19 + k * 0.11, m['metal'], c)
    for s in (1, -1):
        V.headlight(f'head{s}', (2.79, s * 0.83, 1.30), 0.1, 'x', m['head'], c)
        V.box(f'turn{s}', 2.77, 2.81, *sorted((s * 0.76, s * 0.92)), 1.46, 1.54, m['amber'], c)
    for yy in (-0.3, 0.0, 0.3):
        V.box(f'mark{yy}', 2.38, 2.46, yy - 0.06, yy + 0.06, 2.49, 2.55, m['amber'], c)
    V.box('visor', 2.48, 2.70, -1.0, 1.0, 2.44, 2.47, dark, c)
    # cab interior
    eng = V.box('engcover', 1.42, 2.45, -0.27, 0.27, 1.03, 1.56, cab_in, c)
    V.bevel(eng, 0.06, 2)
    V.box('dash', 2.40, 2.66, -1.0, 1.0, 1.48, 1.70, dark, c)
    V.box('dashglow', 2.395, 2.40, 0.45, 0.85, 1.58, 1.64, m['amber'], c)
    P.seat('seatL', 1.25, 1.75, 0.38, 0.96, 1.03, m, c)
    P.seat('seatR', 1.25, 1.75, -0.96, -0.38, 1.03, m, c)
    P.steering('wheel', (2.18, 0.66, 1.92), 0.2, 55, m, c)
    V.cyl('column', (2.32, 0.66, 1.72), 'x', 0.03, 0.4, 6, dark, c)

    # cans behind the cab
    for i, yy in enumerate((-0.82, -0.46)):
        P.jerrycan(f'can{i}', (0.86, yy, 0.86), m, c)
    V.box('canbracket', 0.75, 0.98, -1.0, -0.28, 0.80, 0.86, dark, c)

    # ---------------------------------------------------------------- box body (кунг)
    zb, zt = 1.22, 3.07
    ko = V.box('kung', -3.05, 0.70, -1.16, 1.16, zb, zt)
    V.bevel(ko, 0.07, 2, 30)
    ki = V.box('kung_i', -3.0, 0.65, -1.11, 1.11, zb + 0.05, zt - 0.05)
    V.bevel(ki, 0.02, 1, 30)
    kung = V.shell('Kung', ko, ki, liv, lin, c)
    wins_l = [(-0.35, 0.5), (-1.95, 0.5)]
    wins_r = [(-0.35, 0.5), (-1.85, 0.5)]
    cuts = []
    for cx, w in wins_l:
        cuts.append(V.box('kw', cx - w / 2, cx + w / 2, 1.0, 1.3, 2.05, 2.45, dark))
    for cx, w in wins_r:
        cuts.append(V.box('kw', cx - w / 2, cx + w / 2, -1.3, -1.0, 2.05, 2.45, dark))
    cuts.append(V.box('kf', 0.6, 0.8, -0.28, 0.28, 2.0, 2.36, dark))
    cuts.append(V.box('kd', -3.15, -2.9, -0.38, 0.42, zb + 0.08, 2.88, dark))
    cuts.append(V.box('kr', -3.15, -2.9, -1.0, -0.62, 2.12, 2.46, dark))
    V.bdiff(kung, cuts)
    for cx, w in wins_l:
        V.box('kw_gl', cx - w / 2, cx + w / 2, 1.13, 1.14, 2.05, 2.45, V.room_glass(), c)
        V.ring_y('kw_fr', cx - w / 2 - 0.04, cx + w / 2 + 0.04, 1.155, 1.175, 2.01, 2.49, 0.045, dark, c)
    for cx, w in wins_r:
        V.box('kw_gl', cx - w / 2, cx + w / 2, -1.14, -1.13, 2.05, 2.45, V.room_glass(), c)
        V.ring_y('kw_fr', cx - w / 2 - 0.04, cx + w / 2 + 0.04, -1.175, -1.155, 2.01, 2.49, 0.045, dark, c)
    pane('kf_gl', 0.67, 0.68, -0.28, 0.28, 2.0, 2.36, c)
    V.box('kr_gl', -3.03, -3.02, -1.0, -0.62, 2.12, 2.46, V.room_glass(), c)
    for s in (1, -1):
        V.box(f'skid{s}', -3.0, 0.65, *sorted((s * 0.38, s * 0.5)), 0.84, zb, dark, c)
        V.box(f'fender{s}', -1.95, -0.75, *sorted((s * 0.70, s * 1.12)), 1.12, 1.17, dark, c)
        V.box(f'flap{s}', -1.97, -1.95, *sorted((s * 0.72, s * 1.1)), 0.30, 1.12, m['rubber'], c)
        for xx in (-2.9, 0.5):
            V.box(f'smark{s}{xx}', xx, xx + 0.08, *sorted((s * 1.16, s * 1.18)), 1.28, 1.34, m['amber'], c)
        V.box(f'rail_roof{s}', -2.9, 0.5, *sorted((s * 1.0, s * 1.04)), zt, zt + 0.05, m['metal'], c)
    for s in (1, -1):                          # panel seams with rivet rows on the box sides
        for xx in (-2.3, -1.15, 0.05):
            V.box(f'kseam{s}{xx}', xx - 0.012, xx + 0.012, *sorted((s * 1.158, s * 1.168)), zb + 0.08, zt - 0.08, dark, c)
        V.box(f'kbelt{s}', -2.98, 0.63, *sorted((s * 1.158, s * 1.17)), zb + 0.1, zb + 0.14, m['metal'], c)
    # rear
    rb = V.box('rbump', -2.98, -2.86, -1.1, 1.1, 0.55, 0.72, dark, c)
    for s in (1, -1):
        V.box(f'tail{s}', -3.0, -2.94, *sorted((s * 0.82, s * 1.02)), 0.74, 0.86, m['tail'], c)
    door = V.box('Door', -3.075, -3.035, -0.38, 0.42, zb + 0.08, 2.88, liv, c)
    V.bdiff(door, [V.box('dw', -3.2, -2.9, -0.12, 0.22, 2.25, 2.6, dark)])
    dgl = V.box('door_gl', -3.06, -3.05, -0.12, 0.22, 2.25, 2.6, V.room_glass(), c)
    dh = V.box('door_h', -3.11, -3.075, 0.25, 0.36, 1.95, 1.99, m['metal'], c)
    door = V.join([door, dgl, dh], 'Door')
    set_origin(door, (-3.055, -0.38, 0))
    P.ladder('ladder', -3.05, -0.28, 0.32, zb + 0.02, 0.42, m, c, 3, 0.22)
    # roof
    V.box('hatch', -1.3, -0.8, -0.28, 0.28, zt, zt + 0.07, dark, c)
    V.cyl('antenna', (0.55, -1.0, zt + 0.75), 'z', 0.01, 1.5, 6, dark, c)
    V.box('worklight', -3.13, -3.05, -0.13, 0.13, zt - 0.17, zt - 0.07, dark, c)
    V.box('worklens', -3.135, -3.13, -0.1, 0.1, zt - 0.16, zt - 0.08, m['work'], c)

    # ---------------------------------------------------------------- inside the box
    zf = zb + 0.07
    V.box('floor', -3.0, 0.65, -1.11, 1.11, zb + 0.05, zf, m['mat'], c)
    P.bench('benchL', -2.82, -0.15, 0.62, 1.11, zf, 1, m, blanket=(-1.7, -0.6), col=c)
    P.bench('benchR', -1.95, -0.35, -1.11, -0.62, zf, -1, m, col=c)
    st, glow_at = P.stove('stove', 0.38, 0.78, zf, zt, m, (-1, 0), c)
    V.box('shield1', 0.08, 0.64, 1.09, 1.105, zf, 2.4, m['metal'], c)
    V.box('shield2', 0.635, 0.645, 0.45, 1.1, zf, 2.4, m['metal'], c)
    P.table('table', -0.05, 0.6, -1.09, -0.45, 2.0, zf, m, c)
    lan, l1 = P.lantern('lantern', (0.28, -0.77, 2.62), m, c, hang=0.3)
    dm, l2 = P.dome('dome', (-1.35, 0.0, zt - 0.05), m, c)
    P.rack('rack', -2.95, -2.2, -1.10, -0.62, zf, 2.4, m, c)
    P.coats('coats', -2.98, 0.6, 2.5, -1, m, c, n=2, along='y')
    P.wall_map('map', 0.636, 0.645, -1.0, -0.4, 2.12, 2.55, m, c)
    P.extinguisher('ext', (-2.86, -0.5, zf), m, c)
    P.first_aid('aid', -1.32, -1.0, -1.11, -1.07, 2.2, 2.42, m, c)
    for cx, w in wins_l:
        P.curtains('curL', 1.11, -1, cx - w / 2, cx + w / 2, 2.05, 2.45, m, 'x', c)
    for cx, w in wins_r:
        P.curtains('curR', -1.11, 1, cx - w / 2, cx + w / 2, 2.05, 2.45, m, 'x', c)
    P.curtains('curF', 0.65, -1, -0.28, 0.28, 2.0, 2.36, m, 'y', c)
    V.box('kf_fr', 0.62, 0.65, -0.34, 0.34, 1.95, 2.41, m['wood'], c)
    pil = V.box('pillow', -2.78, -2.45, 0.66, 1.05, zf + 0.44, zf + 0.56, m['quilt'], c)
    V.bevel(pil, 0.04, 2)
    sm = P.smoke('smoke', (0.44, 0.78, zt + 0.62), c)

    # lights
    night += [l1, l2, P.light('stoveL', glow_at, 9, (1.0, 0.45, 0.15), 0.06, col=c),
              P.light('dashL', (2.30, 0.6, 1.75), 1.5, (1.0, 0.6, 0.3), 0.05, col=c)]
    for s in (1, -1):
        night.append(P.light(f'headL{s}', (2.86, s * 0.83, 1.30), 700, (1.0, 0.9, 0.75), 0.05, 'spot',
                             (14, s * 1.4, 0), 55, c))
    night.append(P.light('workL', (-3.2, 0, zt - 0.12), 300, (1.0, 0.92, 0.8), 0.05, 'spot', (-6.5, 0, 0), 95, c))
    for o in night:
        o.hide_render = True

    hum = V.mannequin('human', 3.9, 0.3, math.pi / 2, c)
    lamp_pb = V.EMIT['lamp_warm'][0]
    stl = night[2]

    def set_state(view):
        door.rotation_euler = (0, 0, math.radians(-105) if view == 'night' else 0)
        sm.hide_render = view in ('side', 'inside')
        V.set_room_glow(0.42 if view == 'night' else 0.0)
        hum.hide_render = view == 'inside'
        hum.location, hum.rotation_euler = {
            'day': ((1.25, 2.25, 0), (0, 0, -math.pi / 2)), 'night': ((-4.3, 0.55, 0), (0, 0, -0.25)),
            'side': ((3.9, 0.3, 0), (0, 0, math.pi / 2)), 'inside': ((0, 0, -5), (0, 0, 0))}[view]
        if view == 'night':
            l2.data.energy, l1.data.energy, stl.data.energy = 45, 25, 12
        else:
            l2.data.energy, l1.data.energy, stl.data.energy = 14, 18, 11
            lamp_pb.inputs['Emission Strength'].default_value = 3.5

    return dict(cams=CAMS, set_state=set_state, night_lights=night, human=hum)
