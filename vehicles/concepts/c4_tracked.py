"""Concept 4 «Сцепка»: articulated two-unit tracked carrier; front unit = cab for 4, rear unit = warm box for 6
with a stove, benches facing each other, low ceiling."""
import math
from mathutils import Vector, Matrix
import vlib as V
import parts as P

NAME = 'Сцепка'
CAMS = {
    'day': ((6.4, 3.4, 1.5), (-0.4, 0, 1.15), 24),
    'night': ((-7.0, 4.4, 1.45), (-1.5, 0, 1.4), 26),
    'inside': ((-2.98, -0.05, 1.62), (0.0, 0.05, 1.32), 16),
    'side': ((0.25, 20, 1.75), (0.25, 0, 1.75), 30, 9.0),
}
DIMS = dict(L=6.9, W=2.04, H=2.6, seats='4 в передней секции + 6 в задней', wheelbase=0)


def set_origin(ob, p):
    ob.data.transform(Matrix.Translation(-Vector(p)))
    ob.location = p


def stadium(x0, x1, zc, r, seg=6):
    """track outline: two half circles of radius r at x0 and x1, centre height zc, CCW in (x, z)"""
    return V.arc(x1, zc, r, -90, 90, seg) + V.arc(x0, zc, r, 90, 270, seg)


def track(name, x0, x1, yc, m, col):
    """rubber band track with road wheels, sprocket and idler"""
    r, zc, w = 0.31, 0.33, 0.62
    y0, y1 = yc - w / 2, yc + w / 2
    band = V.prism_y(name, stadium(x0, x1, zc, r), y0, y1, m['rubber'], col)
    band = V.bdiff(band, [V.prism_y(name + '_in', stadium(x0, x1, zc, r - 0.06), y0 - 0.1, y1 + 0.1)])
    parts = [band]
    n = int((x1 - x0) / 0.16)
    for k in range(n + 1):
        xx = x0 + (x1 - x0) * k / n
        parts.append(V.box(name + f'_ct{k}', xx - 0.03, xx + 0.03, y0 + 0.02, y1 - 0.02, zc + r - 0.005, zc + r + 0.03,
                           m['rubber'], col))
        parts.append(V.box(name + f'_cb{k}', xx - 0.03, xx + 0.03, y0 + 0.02, y1 - 0.02, zc - r - 0.03, zc - r + 0.005,
                           m['rubber'], col))
    wl = m['dark']
    for k in range(4):
        xx = x0 + 0.05 + (x1 - x0 - 0.1) * (k + 0.5) / 4
        parts.append(V.cyl(name + f'_rw{k}', (xx, yc, 0.23), 'y', 0.18, w - 0.08, 14, wl, col))
        parts.append(V.cyl(name + f'_rh{k}', (xx, yc, 0.23), 'y', 0.07, w + 0.02, 8, m['metal'], col))
    for xx in (x0, x1):
        parts.append(V.cyl(name + f'_sp{xx:.2f}', (xx, yc, zc), 'y', r - 0.07, w - 0.1, 12, wl, col))
        parts.append(V.cyl(name + f'_sh{xx:.2f}', (xx, yc, zc), 'y', 0.08, w + 0.02, 8, m['metal'], col))
    return V.join(parts, name)


def build():
    c = V.coll('Vehicle')
    m = P.M()
    liv = V.livery('liv4', band=(1.42, 1.58), dirt=(0.55, 1.2))
    lin = V.twotone('lin4', 1.5)
    dark = m['dark']
    yc = 0.70
    night = []

    # ---------------------------------------------------------------- tracks and coupling
    for s in (1, -1):
        track(f'trF{s}', 0.95, 3.0, s * yc, m, c)
        track(f'trR{s}', -2.95, -0.35, s * yc, m, c)
    V.cyl('joint', (0.25, 0, 0.88), 'x', 0.24, 0.5, 14, m['rubber'], c)
    for k in range(4):
        V.cyl(f'jr{k}', (0.07 + k * 0.12, 0, 0.88), 'x', 0.27, 0.03, 14, dark, c)
    V.box('jbar', -0.1, 0.6, -0.12, 0.12, 0.62, 0.72, dark, c)

    # ---------------------------------------------------------------- front unit
    zb = 0.70
    pf_o = [(0.5, zb), (3.15, zb), (3.48, 0.98), (3.48, 1.28), (3.05, 1.47), (2.6, 1.52), (2.32, 2.22)] + \
        V.arc(2.05, 2.15, 0.27, 15, 90, 3) + [(0.5, 2.42)]
    pf_i = [(0.55, zb + 0.05), (2.55, zb + 0.05), (2.55, 1.47), (2.27, 2.2)] + V.arc(2.05, 2.15, 0.22, 15, 90, 3) + \
        [(0.55, 2.37)]
    fo = V.prism_y('front', pf_o, -1.0, 1.0)
    V.bevel(fo, 0.1, 2, 30)
    fi = V.prism_y('front_i', pf_i, -0.95, 0.95)
    V.bevel(fi, 0.04, 1, 30)
    front = V.shell('Front', fo, fi, liv, V.flatcol('cab_in', (0.30, 0.28, 0.24), 0.8), c)
    cuts = []
    for y0, y1 in ((0.32, 0.9), (-0.28, 0.28), (-0.9, -0.32)):
        cuts.append(V.prism_y('ws', [(2.1, 1.6), (2.8, 1.6), (2.8, 2.16), (2.1, 2.16)], y0, y1, dark))
    for s in (1, -1):
        cuts.append(V.box('fdw', 1.6, 2.25, *sorted((s * 0.85, s * 1.2)), 1.62, 2.2, dark))
        cuts.append(V.box('fsw', 0.75, 1.4, *sorted((s * 0.85, s * 1.2)), 1.62, 2.2, dark))
    V.bdiff(front, cuts)
    V.set_smooth(front, 35)

    def xm(z):
        return 2.575 - (z - 1.52) / 0.70 * 0.28
    for y0, y1 in ((0.32, 0.9), (-0.28, 0.28), (-0.9, -0.32)):
        V.prism_y('ws_gl', [(xm(1.6) - 0.004, 1.6), (xm(1.6) + 0.004, 1.6), (xm(2.16) + 0.004, 2.16),
                            (xm(2.16) - 0.004, 2.16)], y0, y1, V.glass(), c)
    for s in (1, -1):
        for x0, x1 in ((1.6, 2.25), (0.75, 1.4)):
            V.box('fg', x0, x1, *sorted((s * 0.97, s * 0.975)), 1.62, 2.2, V.glass(), c)
            V.ring_y('ff', x0 - 0.035, x1 + 0.035, *sorted((s * 0.995, s * 1.01)), 1.585, 2.235, 0.04, dark, c)
        V.box(f'fseam{s}', 1.52, 1.535, *sorted((s * 0.995, s * 1.008)), zb + 0.1, 2.3, dark, c)
        V.box(f'fhandle{s}', 1.6, 1.72, *sorted((s * 1.0, s * 1.03)), 1.5, 1.54, m['metal'], c)
        V.headlight(f'head{s}', (3.47, s * 0.72, 1.14), 0.09, 'x', m['head'], c)
        V.box(f'turn{s}', 3.45, 3.49, *sorted((s * 0.5, s * 0.6)), 1.1, 1.18, m['amber'], c)
        V.box(f'skirtF{s}', 0.6, 3.1, *sorted((s * 0.98, s * 1.03)), 0.62, 0.74, dark, c)
        P.mirror(f'mirror{s}', (2.35, s * 0.98, 1.9), (2.42, s * 1.22, 1.93), m, c)
    V.box('grille', 3.47, 3.5, -0.38, 0.38, 1.0, 1.25, dark, c)
    V.box('fbump', 3.4, 3.58, -0.95, 0.95, 0.72, 0.9, dark, c)
    V.box('frack', 0.7, 1.9, -0.75, 0.75, 2.42, 2.46, m['metal'], c)
    V.cyl('antenna', (0.7, -0.85, 3.1), 'z', 0.01, 1.4, 6, dark, c)
    # front interior
    zf = zb + 0.05
    V.box('ffloor', 0.55, 2.55, -0.95, 0.95, zf, zf + 0.02, m['mat'], c)
    V.box('dash', 2.3, 2.55, -0.95, 0.95, 1.3, 1.5, dark, c)
    V.box('dashglow', 2.295, 2.3, 0.35, 0.75, 1.38, 1.43, m['amber'], c)
    P.seat('seatD', 1.6, 2.05, 0.2, 0.8, zf, m, c)
    P.seat('seatC', 1.6, 2.05, -0.8, -0.2, zf, m, c)
    P.pseat('fbench', 0.6, 1.05, -0.9, 0.9, zf, -1, m, c)
    P.steering('wheel', (2.18, 0.5, 1.62), 0.19, 30, m, c)

    # ---------------------------------------------------------------- rear unit (warm box)
    xr0, xr1, zrt = -3.35, 0.05, 2.32
    ro = V.box('rear', xr0, xr1, -1.0, 1.0, zb, zrt)
    V.bevel(ro, 0.12, 2, 30)
    ri = V.box('rear_i', xr0 + 0.05, xr1 - 0.05, -0.95, 0.95, zb + 0.05, zrt - 0.05)
    V.bevel(ri, 0.04, 1, 30)
    rear = V.shell('Rear', ro, ri, liv, lin, c)
    wins = [(-0.75, 0.5), (-2.15, 0.5)]
    zw0, zw1 = 1.55, 1.95
    cuts = []
    for s in (1, -1):
        for cx, w in wins:
            cuts.append(V.box('rw', cx - w / 2, cx + w / 2, *sorted((s * 0.85, s * 1.2)), zw0, zw1, dark))
    cuts.append(V.box('rd', -3.5, -3.2, -0.38, 0.38, zb + 0.1, 2.12, dark))
    V.bdiff(rear, cuts)
    V.set_smooth(rear, 35)
    for s in (1, -1):
        for cx, w in wins:
            V.box('rg', cx - w / 2, cx + w / 2, *sorted((s * 0.97, s * 0.975)), zw0, zw1, V.room_glass(), c)
            V.ring_y('rf', cx - w / 2 - 0.035, cx + w / 2 + 0.035, *sorted((s * 0.995, s * 1.01)), zw0 - 0.035,
                     zw1 + 0.035, 0.04, dark, c)
        V.box(f'skirtR{s}', -3.2, -0.1, *sorted((s * 0.98, s * 1.03)), 0.62, 0.74, dark, c)
        V.box(f'tail{s}', -3.37, -3.34, *sorted((s * 0.65, s * 0.88)), 0.95, 1.08, m['tail'], c)
        V.box(f'rrail{s}', -3.1, -0.3, *sorted((s * 0.8, s * 0.84)), zrt, zrt + 0.1, m['metal'], c)
    rdp = V.box('rdoorp', -3.365, -3.335, -0.38, 0.38, zb + 0.11, 2.11, liv, c)
    V.bdiff(rdp, [V.box('rdw', -3.5, -3.2, -0.18, 0.18, 1.6, 1.92, dark)])
    rg = V.box('rdg', -3.355, -3.345, -0.18, 0.18, 1.6, 1.92, V.room_glass(), c)
    rh = V.box('rdh', -3.4, -3.365, 0.22, 0.32, 1.42, 1.46, m['metal'], c)
    rdoor = V.join([rdp, rg, rh], 'RearDoor')
    set_origin(rdoor, (-3.35, -0.38, 0))
    V.box('rstep', -3.62, -3.35, -0.36, 0.36, 0.42, 0.46, m['metal'], c)
    V.box('worklight', -3.42, -3.35, -0.12, 0.12, zrt - 0.18, zrt - 0.08, dark, c)
    V.box('worklens', -3.425, -3.42, -0.09, 0.09, zrt - 0.17, zrt - 0.09, m['work'], c)
    tarp = V.box('tarp', -2.9, -1.6, -0.7, 0.7, zrt + 0.02, zrt + 0.3, m['canvas'], c)
    V.bevel(tarp, 0.07, 2)

    # rear interior: low ceiling, benches facing each other, stove at the front
    zf = zb + 0.05
    V.box('rfloor', xr0 + 0.05, xr1 - 0.05, -0.95, 0.95, zf, zf + 0.02, m['mat'], c)
    zf += 0.02
    P.bench('benchL', -3.2, -0.65, 0.5, 0.95, zf, 1, m, seat=0.38, blanket=(-2.3, -1.4), col=c)
    P.bench('benchR', -3.2, -0.65, -0.95, -0.5, zf, -1, m, seat=0.38, col=c)
    st, glow_at = P.stove('stove', -0.3, 0.55, zf, zrt, m, (-1, 0), c, 0.4)
    V.box('shield', -0.06, -0.05, 0.2, 0.95, zf, 2.1, m['metal'], c)
    P.table('table', -0.6, -0.12, -0.92, -0.35, 1.45, zf, m, c)
    for s in (1, -1):
        for cx, w in wins:
            P.curtains('cur', s * 0.95, -s, cx - w / 2, cx + w / 2, zw0, zw1, m, 'x', c)
    lan, l1 = P.lantern('lantern', (-1.55, 0.0, 1.98), m, c, hang=0.14)
    P.wall_map('map', -0.056, -0.05, -0.9, -0.4, 1.55, 1.95, m, c)
    P.first_aid('aid', -0.25, -0.0, -0.95, -0.91, 1.62, 1.84, m, c)
    P.coats('coats', -3.29, 0.48, 2.1, -1, m, c, n=2, along='y')
    for i, yy in enumerate((-0.15, 0.15)):
        P.jerrycan(f'ican{i}', (-2.95, yy, zf), m, c, 0.0)
    sm = P.smoke('smoke', (-0.24, 0.55, zrt + 0.48), c)

    night += [l1, P.light('stoveL', glow_at, 9, (1.0, 0.45, 0.15), 0.06, col=c),
              P.light('roomL', (-1.9, 0, 2.15), 10, (1.0, 0.7, 0.42), 0.1, col=c),
              P.light('dashL', (2.1, 0.5, 1.65), 1.5, (1.0, 0.6, 0.3), 0.05, col=c)]
    for s in (1, -1):
        night.append(P.light(f'headL{s}', (3.55, s * 0.72, 1.14), 700, (1.0, 0.9, 0.75), 0.05, 'spot',
                             (15, s * 1.4, 0), 55, c))
    night.append(P.light('workL', (-3.48, 0, zrt - 0.13), 250, (1.0, 0.92, 0.8), 0.05, 'spot', (-6.5, 0, 0), 95, c))
    for o in night:
        o.hide_render = True
    hum = V.mannequin('human', 4.2, 0.3, math.pi / 2, c)
    lamp_pb = V.EMIT['lamp_warm'][0]
    stl, rml = night[1], night[2]

    def set_state(view):
        op = view == 'night'
        rdoor.rotation_euler = (0, 0, math.radians(-100) if op else 0)
        sm.hide_render = view in ('side', 'inside')
        V.set_room_glow(0.42 if op else 0.0)
        hum.hide_render = view == 'inside'
        hum.location, hum.rotation_euler = {
            'day': ((1.4, 2.0, 0), (0, 0, -math.pi / 2)), 'night': ((-4.55, -1.35, 0), (0, 0, 0.85)),
            'side': ((4.3, 0.3, 0), (0, 0, math.pi / 2)), 'inside': ((0, 0, -5), (0, 0, 0))}[view]
        if op:
            l1.data.energy, stl.data.energy, rml.data.energy = 25, 12, 30
        else:
            l1.data.energy, stl.data.energy, rml.data.energy = 16, 10, 6
            lamp_pb.inputs['Emission Strength'].default_value = 3.5

    return dict(cams=CAMS, set_state=set_state, night_lights=night, human=hum)
