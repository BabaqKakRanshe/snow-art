"""Concept 2 «Вахтовка»: bonneted 4x4 with a one-volume bus body (driver + 7 seats, table nook, stove)."""
import math
from mathutils import Vector, Matrix
import vlib as V
import parts as P

NAME = 'Вахтовка'
CAMS = {
    'day': ((6.5, 3.4, 1.6), (-0.6, 0, 1.6), 24),
    'night': ((2.6, -6.4, 1.55), (-0.7, 0, 1.95), 26),
    'inside': ((-1.95, -0.6, 2.32), (-0.3, 0.85, 1.98), 17),
    'side': ((-0.1, 20, 1.75), (-0.1, 0, 1.75), 30, 9.0),
}
DIMS = dict(L=6.6, W=2.4, H=3.35, seats='водитель + 8', wheelbase=3.6)


def set_origin(ob, p):
    ob.data.transform(Matrix.Translation(-Vector(p)))
    ob.location = p


def pane(name, x0, x1, y0, y1, z0, z1, col=None):
    return V.box(name, x0, x1, y0, y1, z0, z1, V.glass(), col)


def build():
    c = V.coll('Vehicle')
    m = P.M()
    liv = V.livery('liv2', band=(1.68, 1.92), dirt=(0.4, 1.45))
    lin = V.twotone('lin2', 2.05)
    dark = m['dark']
    R, W, xF, xR, ty = 0.54, 0.34, 2.05, -1.55, 0.95
    zb, zt = 1.25, 3.10
    night = []

    # ---------------------------------------------------------------- chassis, wheels
    for s in (1, -1):
        V.box(f'rail{s}', -3.2, 3.0, s * 0.38, s * 0.48, 0.62, 0.84, dark, c)
        for xa in (xF, xR):
            V.wheel(f'wh_{xa}_{s}', xa, s * ty, R, R, W, outward=s, col=c)
    for xa in (xF, xR):
        V.cyl(f'axle{xa}', (xa, 0, R), 'y', 0.07, 2 * ty - 0.2, 10, dark, c)
        V.box(f'diff{xa}', xa - 0.18, xa + 0.18, -0.16, 0.16, R - 0.17, R + 0.17, dark, c)
    b = V.box('bumper', 3.05, 3.26, -1.15, 1.15, 0.60, 0.86, dark, c)
    V.bevel(b, 0.03, 1)
    for s in (1, -1):
        V.box(f'hook{s}', 3.26, 3.36, s * 0.52, s * 0.62, 0.66, 0.74, m['red'], c)

    # ---------------------------------------------------------------- bonnet and fenders
    hood = V.prism_y('hood', [(1.95, 0.98), (3.02, 0.98), (3.12, 1.08), (3.12, 1.56), (3.02, 1.70), (2.55, 1.80),
                              (1.95, 1.86)], -0.80, 0.80, liv, c)
    V.bevel(hood, 0.11, 2, 30)
    V.set_smooth(hood, 35)
    V.box('grille', 3.10, 3.16, -0.52, 0.52, 1.08, 1.56, dark, c)
    for k in range(7):
        yy = -0.45 + k * 0.15
        V.box(f'gbar{k}', 3.15, 3.18, yy - 0.025, yy + 0.025, 1.1, 1.54, m['metal'], c)
    for s in (1, -1):
        V.headlight(f'head{s}', (3.12, s * 0.66, 1.36), 0.1, 'x', m['head'], c)
        V.box(f'turn{s}', 3.08, 3.13, *sorted((s * 0.64, s * 0.76)), 1.56, 1.62, m['amber'], c)
        out = V.arc(xF, R, 0.70, 0, 180, 10)
        inn = V.arc(xF, R, 0.60, 180, 0, 10)
        f = V.prism_y(f'fender{s}', out + inn, *sorted((s * 0.78, s * 1.22)), dark, c)
        V.bevel(f, 0.03, 1, 40)
        V.box(f'rfender{s}', xR - 0.62, xR + 0.62, *sorted((s * 0.72, s * 1.15)), 1.13, 1.18, dark, c)
        V.box(f'flap{s}', xR - 0.64, xR - 0.62, *sorted((s * 0.75, s * 1.12)), 0.3, 1.13, m['rubber'], c)
        V.box(f'ubox{s}', -0.85, 0.95, *sorted((s * 0.6, s * 1.12)), 0.78, zb, dark, c)

    # ---------------------------------------------------------------- body
    prof_o = [(-3.3, zb), (2.02, zb), (2.08, 1.95), (1.93, 2.72)] + V.arc(1.65, 2.82, 0.28, 0, 90, 4)[:] + \
        V.arc(-3.08, 2.88, 0.22, 90, 180, 4)
    prof_i = [(-3.25, zb + 0.05), (1.97, zb + 0.05), (2.03, 1.93), (1.88, 2.70)] + V.arc(1.65, 2.82, 0.23, 0, 90, 4) + \
        V.arc(-3.08, 2.88, 0.17, 90, 180, 4)
    bo = V.prism_y('body', prof_o, -1.2, 1.2)
    V.bevel(bo, 0.10, 2, 30)
    bi = V.prism_y('body_i', prof_i, -1.15, 1.15)
    V.bevel(bi, 0.04, 1, 30)
    body = V.shell('Body', bo, bi, liv, lin, c)
    winsL = [(1.5, 0.62), (0.85, 0.8), (-0.25, 0.8), (-1.35, 0.8), (-2.45, 0.8)]
    winsR = [(1.62, 0.42), (-0.25, 0.8), (-1.35, 0.8), (-2.45, 0.8)]
    zw0, zw1 = 2.12, 2.64
    cuts = []
    for y0, y1 in ((0.05, 1.0), (-1.0, -0.05)):
        cuts.append(V.prism_y('ws', [(1.8, 1.98), (2.4, 1.98), (2.4, 2.64), (1.8, 2.64)], y0, y1, dark))
    for cx, w in winsL:
        cuts.append(V.box('w', cx - w / 2, cx + w / 2, 1.0, 1.4, zw0, zw1, dark))
    for cx, w in winsR:
        cuts.append(V.box('w', cx - w / 2, cx + w / 2, -1.4, -1.0, zw0, zw1, dark))
    cuts.append(V.box('pdoor', 0.62, 1.32, -1.4, -1.0, zb + 0.08, 2.86, dark))
    cuts.append(V.box('rdoor', -3.5, -3.15, -0.42, 0.38, zb + 0.08, 2.84, dark))
    for y0, y1 in ((0.6, 1.0), (-1.0, -0.65)):
        cuts.append(V.box('rw', -3.5, -3.15, y0, y1, 2.2, 2.6, dark))
    V.bdiff(body, cuts)
    V.set_smooth(body, 35)

    def xm(z):
        return 2.055 - (z - 1.95) / 0.77 * 0.15
    for y0, y1 in ((0.05, 1.0), (-1.0, -0.05)):
        V.prism_y('ws_gl', [(xm(1.98) - 0.004, 1.98), (xm(1.98) + 0.004, 1.98), (xm(2.64) + 0.004, 2.64),
                            (xm(2.64) - 0.004, 2.64)], y0, y1, V.glass(), c)
    for cx, w in winsL:
        V.box('wg', cx - w / 2, cx + w / 2, 1.17, 1.18, zw0, zw1, V.room_glass() if cx < 1.2 else V.glass(), c)
        V.ring_y('wf', cx - w / 2 - 0.035, cx + w / 2 + 0.035, 1.195, 1.215, zw0 - 0.035, zw1 + 0.035, 0.04, dark, c)
    for cx, w in winsR:
        V.box('wg', cx - w / 2, cx + w / 2, -1.18, -1.17, zw0, zw1, V.room_glass() if cx < 1.2 else V.glass(), c)
        V.ring_y('wf', cx - w / 2 - 0.035, cx + w / 2 + 0.035, -1.215, -1.195, zw0 - 0.035, zw1 + 0.035, 0.04, dark, c)
    for y0, y1 in ((0.6, 1.0), (-1.0, -0.65)):
        V.box('rwg', -3.28, -3.27, y0, y1, 2.2, 2.6, V.room_glass(), c)
    # driver door seams and handle, mirrors, markers
    V.box('dseam1', 1.14, 1.155, 1.195, 1.21, zb + 0.05, 2.75, dark, c)
    V.box('dhandle', 1.22, 1.34, 1.2, 1.23, 1.98, 2.02, m['metal'], c)
    for s in (1, -1):
        P.mirror(f'mirror{s}', (1.98, s * 1.18, 2.35), (2.08, s * 1.46, 2.38), m, c)
        for xx in (-3.0, -1.0, 1.0):
            V.box(f'smark{s}{xx}', xx, xx + 0.08, *sorted((s * 1.2, s * 1.22)), zb + 0.05, zb + 0.11, m['amber'], c)
        V.box(f'tail{s}', -3.32, -3.29, *sorted((s * 0.86, s * 1.08)), 1.42, 1.58, m['tail'], c)
    for yy in (-0.35, 0.0, 0.35):
        V.box(f'mark{yy}', 1.72, 1.82, yy - 0.06, yy + 0.06, 3.07, 3.12, m['amber'], c)
    V.box('rbump', -3.42, -3.3, -1.1, 1.1, 0.62, 0.8, dark, c)
    # passenger door: two folding leaves; steps
    leaves = []
    for k, (h0, h1) in enumerate(((0.62, 0.97), (0.97, 1.32))):
        lf = V.box(f'leaf{k}', h0, h1, -1.215, -1.185, zb + 0.09, 2.85, liv, c)
        V.bdiff(lf, [V.box('lw', h0 + 0.06, h1 - 0.06, -1.4, -1.0, 1.95, 2.72, dark)])
        g = pane(f'lg{k}', h0 + 0.06, h1 - 0.06, -1.205, -1.195, 1.95, 2.72, c)
        lf = V.join([lf, g], f'leaf{k}')
        hinge = (h0, -1.2, 0) if k == 0 else (h1, -1.2, 0)
        set_origin(lf, hinge)
        leaves.append(lf)
    for k, (z, yo) in enumerate(((0.97, 1.0), (0.66, 1.08))):
        V.box(f'pstep{k}', 0.66, 1.28, -yo - 0.18, -yo, z - 0.04, z, m['metal'], c)
    V.box('dstep', 1.15, 1.75, 1.0, 1.18, 0.95, 0.99, m['metal'], c)
    rdoor = V.box('rdoorp', -3.33, -3.29, -0.42, 0.38, zb + 0.09, 2.83, liv, c)
    V.bdiff(rdoor, [V.box('rdw', -3.5, -3.1, -0.22, 0.18, 2.2, 2.6, dark)])
    pane('rdg', -3.315, -3.305, -0.22, 0.18, 2.2, 2.6, c)
    # roof rack, ladder, stove pipe
    for s in (1, -1):
        V.box(f'rr{s}', -3.0, 1.2, *sorted((s * 0.92, s * 0.96)), zt + 0.14, zt + 0.18, m['metal'], c)
        for xx in (-2.9, -1.7, -0.5, 0.7):
            V.box(f'rp{s}{xx}', xx, xx + 0.04, *sorted((s * 0.92, s * 0.96)), zt - 0.01, zt + 0.18, m['metal'], c)
    for xx in (-2.9, -1.7, -0.5, 0.7):
        V.box(f'rx{xx}', xx, xx + 0.04, -0.94, 0.94, zt + 0.02, zt + 0.06, m['metal'], c)
    V.cyl('spare', (-0.3, 0.3, zt + 0.17), 'z', R, 0.3, 20, m['rubber'], c)
    P.jerrycan('rcan1', (0.55, -0.55, zt + 0.06), m, c, math.pi / 2)
    P.jerrycan('rcan2', (0.55, -0.15, zt + 0.06), m, c, math.pi / 2)
    tarp = V.box('tarp', -2.6, -1.4, -0.8, 0.6, zt + 0.06, zt + 0.42, m['canvas'], c)
    V.bevel(tarp, 0.08, 2)
    P.ladder('ladder', -3.30, 0.62, 1.02, zt + 0.2, zb + 0.15, m, c, 6, 0.08)

    # ---------------------------------------------------------------- inside
    zf = zb + 0.07
    V.box('floor', -3.25, 1.97, -1.15, 1.15, zb + 0.05, zf, m['mat'], c)
    V.box('dash', 1.80, 2.0, -1.12, 1.12, 1.78, 1.98, dark, c)
    V.box('dashglow', 1.795, 1.80, 0.35, 0.8, 1.88, 1.93, m['amber'], c)
    P.seat('seatD', 1.05, 1.55, 0.32, 0.92, zf, m, c)
    P.seat('seatC', 1.05, 1.55, -0.92, -0.32, zf, m, c)
    P.steering('wheel', (1.70, 0.62, 2.05), 0.21, 25, m, c)
    V.cyl('column', (1.80, 0.62, 1.92), 'x', 0.03, 0.25, 6, dark, c)
    # cosy nook: two facing seats and a table under the window
    P.pseat('nookA', 0.12, 0.58, 0.32, 1.15, zf, +1, m, c)
    P.table('table', -0.62, 0.06, 0.55, 1.13, 2.02, zf, m, c)
    P.pseat('nookB', -1.18, -0.68, 0.32, 1.15, zf, -1, m, c)
    P.pseat('seatL3', -2.2, -1.7, 0.32, 1.15, zf, -1, m, c)
    for x0 in (-0.75, -1.85):
        P.pseat(f'seatR{x0}', x0, x0 + 0.48, -1.15, -0.62, zf, -1, m, c)
    st, glow_at = P.stove('stove', -2.88, -0.86, zf, zt, m, (1, 0), c, 0.5)
    V.box('shield', -3.24, -3.235, -1.12, -0.5, zf, 2.5, m['metal'], c)
    P.rack('rack', -3.22, -2.62, 0.55, 1.13, zf, 2.3, m, c)
    for s, y0, y1 in ((1, 0.85, 1.14), (-1, -1.14, -0.85)):
        P.shelf_bags(f'shelf{s}', -3.0, 0.9, y0, y1, 2.80, m, c, 4)
    for cx, w in winsL[1:]:
        P.curtains('curL', 1.15, -1, cx - w / 2, cx + w / 2, zw0, zw1, m, 'x', c)
    for cx, w in winsR[1:]:
        P.curtains('curR', -1.15, 1, cx - w / 2, cx + w / 2, zw0, zw1, m, 'x', c)
    lan, l1 = P.lantern('lantern', (-0.28, 0.84, 2.58), m, c, hang=0.3)
    d1, l2 = P.dome('dome1', (0.2, 0.0, zt - 0.05), m, c)
    d2, l3 = P.dome('dome2', (-1.9, 0.0, zt - 0.05), m, c)
    P.coats('coats', 0.4, -1.13, 2.65, -1, m, c, n=1)
    P.first_aid('aid', 0.15, 0.45, -1.15, -1.11, 2.25, 2.48, m, c)
    P.wall_map('map', -1.32, -0.75, 1.14, 1.15, 2.2, 2.62, m, c)
    sm = P.smoke('smoke', (-2.82, -0.86, zt + 0.58), c)

    night += [l1, l2, l3, P.light('stoveL', glow_at, 9, (1.0, 0.45, 0.15), 0.06, col=c),
              P.light('dashL', (1.6, 0.6, 2.05), 1.5, (1.0, 0.6, 0.3), 0.05, col=c)]
    for s in (1, -1):
        night.append(P.light(f'headL{s}', (3.2, s * 0.66, 1.36), 700, (1.0, 0.9, 0.75), 0.05, 'spot',
                             (15, s * 1.4, 0), 55, c))
    night.append(P.light('doorL', (0.97, -1.6, 2.9), 120, (1.0, 0.85, 0.65), 0.05, 'spot', (0.97, -2.6, 0), 80, c))
    for o in night:
        o.hide_render = True
    V.box('doorlamp', 0.87, 1.07, -1.25, -1.2, 2.92, 2.98, m['work'], c)
    hum = V.mannequin('human', 3.9, 0.3, math.pi / 2, c)
    lamp_pb = V.EMIT['lamp_warm'][0]
    stl = night[3]

    def set_state(view):
        op = view == 'night'
        leaves[0].rotation_euler = (0, 0, math.radians(-80) if op else 0)
        leaves[1].rotation_euler = (0, 0, math.radians(80) if op else 0)
        sm.hide_render = view in ('side', 'inside')
        V.set_room_glow(0.42 if view == 'night' else 0.0)
        hum.hide_render = view == 'inside'
        hum.location, hum.rotation_euler = {
            'day': ((1.0, 2.2, 0), (0, 0, -math.pi / 2)), 'night': ((0.2, -2.35, 0), (0, 0, 1.2)),
            'side': ((4.1, 0.3, 0), (0, 0, math.pi / 2)), 'inside': ((0, 0, -5), (0, 0, 0))}[view]
        if op:
            l2.data.energy, l3.data.energy, l1.data.energy, stl.data.energy = 40, 40, 25, 12
        else:
            l2.data.energy, l3.data.energy, l1.data.energy, stl.data.energy = 12, 12, 16, 10
            lamp_pb.inputs['Emission Strength'].default_value = 3.5

    return dict(cams=CAMS, set_state=set_state, night_lights=night, human=hum)
