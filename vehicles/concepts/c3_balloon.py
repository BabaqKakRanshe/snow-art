"""Concept 3 «Буханка на баллонах»: 6x6 on low-pressure tyres, one-volume loaf body, boat hull,
dinette at the rear on the wheel wells, stove, winch."""
import math
from mathutils import Vector, Matrix
import vlib as V
import parts as P

NAME = 'Буханка на баллонах'
CAMS = {
    'day': ((6.6, 3.5, 1.75), (-0.3, 0, 1.7), 24),
    'night': ((-7.2, 5.2, 1.7), (-1.0, 0, 2.0), 26),
    'inside': ((1.25, -0.45, 2.42), (-2.2, 0.15, 1.9), 19),
    'side': ((0.1, 20, 1.75), (0.1, 0, 1.75), 30, 9.0),
}
DIMS = dict(L=5.9, W=2.62, H=3.35, seats='2 впереди + 6 за столом', wheelbase=3.2)


def set_origin(ob, p):
    ob.data.transform(Matrix.Translation(-Vector(p)))
    ob.location = p


def build():
    c = V.coll('Vehicle')
    m = P.M()
    liv = V.livery('liv3', band=(1.74, 1.9), dirt=(0.7, 1.6))
    lin = V.twotone('lin3', 2.0)
    dark = m['dark']
    R, W, ty = 0.78, 0.62, 1.0
    axles = (1.75, 0.15, -1.45)
    zb, zt = 1.35, 3.05
    night = []

    # ---------------------------------------------------------------- hull and wheels
    hull = V.prism_y('hull', [(-2.55, 0.62), (2.15, 0.48), (2.72, 0.95), (2.75, zb), (-2.55, zb)], -0.66, 0.66, dark, c)
    V.bevel(hull, 0.07, 2, 30)
    for s in (1, -1):
        for xa in axles:
            V.wheel(f'wh_{xa}_{s}', xa, s * ty, R, R, W, rim_r=0.42, lugs=16, lug_h=0.05, balloon=True,
                    outward=s, col=c)
            V.cyl(f'hub{xa}{s}', (xa, s * 0.6, R), 'y', 0.08, 0.2, 8, dark, c)
    # winch bumper
    V.box('bumper', 2.70, 2.98, -1.0, 1.0, 0.88, 1.12, dark, c)
    V.cyl('winch', (2.86, 0, 1.22), 'y', 0.11, 0.62, 12, dark, c)
    V.cyl('cable', (2.86, 0, 1.22), 'y', 0.12, 0.4, 12, m['metal'], c)
    V.box('fair', 2.97, 3.03, -0.12, 0.12, 1.12, 1.3, m['metal'], c)
    V.box('whook', 3.03, 3.12, -0.04, 0.04, 1.08, 1.2, m['red'], c)

    # ---------------------------------------------------------------- loaf body
    prof_o = [(-2.6, zb), (2.7, zb), (2.86, 1.55), (2.86, 1.78), (2.62, 2.58)] + V.arc(2.25, 2.65, 0.40, 10, 90, 4) + \
        V.arc(-2.2, 2.65, 0.40, 90, 180, 4)
    prof_i = [(-2.55, zb + 0.05), (2.65, zb + 0.05), (2.81, 1.55), (2.81, 1.77), (2.58, 2.56)] + \
        V.arc(2.25, 2.65, 0.35, 10, 90, 4) + V.arc(-2.2, 2.65, 0.35, 90, 180, 4)
    bo = V.prism_y('body', prof_o, -1.12, 1.12)
    V.bevel(bo, 0.16, 3, 30)
    bi = V.prism_y('body_i', prof_i, -1.07, 1.07)
    V.bevel(bi, 0.08, 2, 30)
    body = V.shell('Body', bo, bi, liv, lin, c)
    zw0, zw1 = 1.98, 2.45
    winsL = [(2.0, 0.6), (0.62, 0.62), (-0.5, 0.62), (-1.6, 0.62)]
    winsR = [(2.0, 0.6), (-0.5, 0.62), (-1.6, 0.62)]
    cuts = []
    for y0, y1 in ((0.06, 0.98), (-0.98, -0.06)):
        cuts.append(V.prism_y('ws', [(2.4, 1.86), (3.1, 1.86), (3.1, 2.5), (2.4, 2.5)], y0, y1, dark))
    for cx, w in winsL:
        cuts.append(V.box('w', cx - w / 2, cx + w / 2, 0.9, 1.4, zw0, zw1, dark))
    for cx, w in winsR:
        cuts.append(V.box('w', cx - w / 2, cx + w / 2, -1.4, -0.9, zw0, zw1, dark))
    cuts.append(V.box('sdoor', 0.75, 1.4, -1.4, -0.9, zb + 0.08, 2.72, dark))
    cuts.append(V.box('rdoor', -2.8, -2.4, -0.42, 0.42, zb + 0.08, 2.65, dark))
    for s in (1, -1):
        for xa in axles:
            cuts.append(V.cyl('arch', (xa, s * 1.02, R), 'y', 0.88, 0.8, 20, dark))
    V.bdiff(body, cuts)
    V.set_smooth(body, 35)

    def xm(z):
        return 2.835 - (z - 1.78) / 0.8 * 0.235
    for y0, y1 in ((0.06, 0.98), (-0.98, -0.06)):
        V.prism_y('ws_gl', [(xm(1.86) - 0.004, 1.86), (xm(1.86) + 0.004, 1.86), (xm(2.5) + 0.004, 2.5),
                            (xm(2.5) - 0.004, 2.5)], y0, y1, V.glass(), c)
    for cx, w in winsL:
        V.box('wg', cx - w / 2, cx + w / 2, 1.09, 1.1, zw0, zw1, V.room_glass() if cx < 1.5 else V.glass(), c)
        V.ring_y('wf', cx - w / 2 - 0.04, cx + w / 2 + 0.04, 1.115, 1.135, zw0 - 0.04, zw1 + 0.04, 0.045, dark, c)
    for cx, w in winsR:
        V.box('wg', cx - w / 2, cx + w / 2, -1.1, -1.09, zw0, zw1, V.room_glass() if cx < 1.5 else V.glass(), c)
        V.ring_y('wf', cx - w / 2 - 0.04, cx + w / 2 + 0.04, -1.135, -1.115, zw0 - 0.04, zw1 + 0.04, 0.045, dark, c)
    # arch trims (black wheel-arch flares)
    for s in (1, -1):
        for xa in axles:
            out = V.arc(xa, R, 0.96, 0, 180, 12)
            inn = V.arc(xa, R, 0.88, 180, 0, 12)
            f = V.prism_y(f'flare{xa}{s}', out + inn, *sorted((s * 1.0, s * 1.16)), dark, c)
        V.box(f'dseam{s}', 1.6, 1.615, *sorted((s * 1.12, s * 1.135)), zb + 0.1, 2.68, dark, c)
        V.box(f'dhandle{s}', 1.68, 1.8, *sorted((s * 1.12, s * 1.15)), 1.92, 1.96, m['metal'], c)
        P.mirror(f'mirror{s}', (2.55, s * 1.1, 2.15), (2.65, s * 1.36, 2.18), m, c)
        V.box(f'tail{s}', -2.62, -2.59, *sorted((s * 0.75, s * 0.98)), 1.45, 1.62, m['tail'], c)
        V.box(f'smark{s}', 0.9, 0.98, *sorted((s * 1.12, s * 1.14)), 1.45, 1.52, m['amber'], c)
    for s in (1, -1):
        V.headlight(f'head{s}', (2.86, s * 0.78, 1.62), 0.1, 'x', m['head'], c)
        V.box(f'turn{s}', 2.84, 2.88, *sorted((s * 0.52, s * 0.62)), 1.57, 1.67, m['amber'], c)
    V.box('grille', 2.85, 2.89, -0.36, 0.36, 1.5, 1.72, dark, c)
    for k in range(3):
        V.box(f'gs{k}', 2.88, 2.9, -0.33, 0.33, 1.54 + k * 0.06, 1.56 + k * 0.06, m['metal'], c)
    # side door (right) with a step, rear door with a ladder to the roof
    sd = V.box('sdoorp', 0.75, 1.4, -1.135, -1.105, zb + 0.09, 2.71, liv, c)
    V.bdiff(sd, [V.box('sdw', 0.85, 1.3, -1.4, -0.9, zw0, zw1, dark)])
    sg = V.box('sdg', 0.85, 1.3, -1.125, -1.115, zw0, zw1, V.room_glass(), c)
    sd = V.join([sd, sg], 'SideDoor')
    set_origin(sd, (0.75, -1.12, 0))
    V.box('sstep', 0.8, 1.35, -1.32, -1.1, 1.18, 1.22, m['metal'], c)
    rd = V.box('rdoorp', -2.635, -2.605, -0.42, 0.42, zb + 0.09, 2.64, liv, c)
    V.bdiff(rd, [V.box('rdw', -2.8, -2.4, -0.2, 0.2, 2.05, 2.42, dark)])
    rg = V.box('rdg', -2.625, -2.615, -0.2, 0.2, 2.05, 2.42, V.room_glass(), c)
    rh = V.box('rdh', -2.67, -2.635, 0.25, 0.35, 1.95, 1.99, m['metal'], c)
    rd = V.join([rd, rg, rh], 'RearDoor')
    set_origin(rd, (-2.62, -0.42, 0))
    P.ladder('ladder', -2.6, 0.62, 0.95, zt + 0.15, 0.95, m, c, 6, 0.06)
    V.box('rstep', -2.95, -2.6, -0.4, 0.4, 0.98, 1.02, m['metal'], c)
    # roof: rack, lights, can, shovel, stove pipe
    for s in (1, -1):
        V.box(f'rr{s}', -1.9, 1.6, *sorted((s * 0.82, s * 0.86)), zt + 0.12, zt + 0.16, m['metal'], c)
        for xx in (-1.85, -0.6, 0.6, 1.55):
            V.box(f'rp{s}{xx}', xx, xx + 0.04, *sorted((s * 0.82, s * 0.86)), zt - 0.03, zt + 0.16, m['metal'], c)
    for xx in (-1.85, -0.6, 0.6, 1.55):
        V.box(f'rx{xx}', xx, xx + 0.04, -0.84, 0.84, zt, zt + 0.04, m['metal'], c)
    for k, yy in enumerate((-0.45, -0.15, 0.15, 0.45)):
        V.box(f'lbar{k}', 1.62, 1.72, yy - 0.09, yy + 0.09, zt + 0.12, zt + 0.24, dark, c)
        V.box(f'lbl{k}', 1.72, 1.725, yy - 0.07, yy + 0.07, zt + 0.14, zt + 0.22, m['work'], c)
    P.jerrycan('rcan', (-1.2, 0.45, zt + 0.04), m, c, math.pi / 2)
    P.jerrycan('rcan2', (-1.2, 0.05, zt + 0.04), m, c, math.pi / 2, V.flatcol('olive', (0.2, 0.24, 0.14), 0.6))
    sh = V.box('shovel', -0.5, 0.6, -0.6, -0.5, zt + 0.06, zt + 0.1, m['wood'], c)
    V.box('shovelb', 0.6, 0.85, -0.66, -0.44, zt + 0.06, zt + 0.09, m['metal'], c)
    V.cyl('antenna', (2.1, -0.9, zt + 0.7), 'z', 0.01, 1.4, 6, dark, c)

    # ---------------------------------------------------------------- inside
    zf = zb + 0.07
    V.box('floor', -2.55, 2.65, -1.07, 1.07, zb + 0.05, zf, m['mat'], c)
    for s in (1, -1):
        for xa in axles:
            V.box(f'well{xa}{s}', xa - 0.86, xa + 0.86, *sorted((s * 0.62, s * 1.07)), zf, zf + 0.3, m['metal'], c)
    V.box('dash', 2.45, 2.72, -1.0, 1.0, 1.82, 2.0, dark, c)
    V.box('dashglow', 2.445, 2.45, 0.4, 0.8, 1.9, 1.95, m['amber'], c)
    P.seat('seatD', 1.45, 1.95, 0.25, 0.85, zf, m, c)
    P.seat('seatC', 1.45, 1.95, -0.85, -0.25, zf, m, c)
    P.steering('wheel', (2.3, 0.55, 2.1), 0.2, 30, m, c)
    V.cyl('column', (2.42, 0.55, 1.98), 'x', 0.03, 0.25, 6, dark, c)
    # dinette: benches on the rear wheel wells and along the rear wall, table between
    zw = zf + 0.3
    P.bench('dinL', -2.3, -0.6, 0.62, 1.07, zw - 0.3, 1, m, seat=0.42, blanket=(-1.6, -0.9), col=c)
    P.bench('dinR', -2.3, -0.6, -1.07, -0.62, zw - 0.3, -1, m, seat=0.42, col=c)
    rb = V.box('dinB', -2.55, -2.25, -0.45, 0.45, zf, zf + 0.42, m['wood'], c)
    rbc = V.box('dinBc', -2.55, -2.2, -0.45, 0.45, zf + 0.34, zf + 0.44, m['quilt'], c)
    V.bevel(rbc, 0.03, 2)
    P.table('table', -1.9, -1.05, -0.42, 0.42, zf + 0.72, zf, m, c)
    st, glow_at = P.stove('stove', 0.2, 0.82, zw, zt, m, (0, -1), c, 0.45)
    V.box('shield', -0.15, 0.55, 1.05, 1.07, zw, 2.6, m['metal'], c)
    for cx, w in winsL[1:]:
        P.curtains('curL', 1.07, -1, cx - w / 2, cx + w / 2, zw0, zw1, m, 'x', c)
    for cx, w in winsR[1:]:
        P.curtains('curR', -1.07, 1, cx - w / 2, cx + w / 2, zw0, zw1, m, 'x', c)
    lan, l1 = P.lantern('lantern', (-1.48, 0.0, 2.55), m, c, hang=0.32)
    d1, l2 = P.dome('dome1', (0.6, 0.0, zt - 0.06), m, c)
    P.wall_map('map', -2.555, -2.548, -0.95, -0.5, 2.0, 2.4, m, c)
    P.first_aid('aid', -2.555, -2.52, 0.5, 0.82, 2.08, 2.3, m, c, facing='x')
    P.coats('coats', -2.0, 1.065, 2.62, 1, m, c, n=1)
    sm = P.smoke('smoke', (0.26, 0.82, zt + 0.52), c)

    night += [l1, l2, P.light('stoveL', glow_at, 9, (1.0, 0.45, 0.15), 0.06, col=c),
              P.light('dashL', (2.2, 0.5, 2.1), 1.5, (1.0, 0.6, 0.3), 0.05, col=c)]
    for s in (1, -1):
        night.append(P.light(f'headL{s}', (2.95, s * 0.78, 1.62), 700, (1.0, 0.9, 0.75), 0.05, 'spot',
                             (15, s * 1.4, 0), 55, c))
    night.append(P.light('roofL', (1.8, 0, zt + 0.2), 500, (1.0, 0.92, 0.8), 0.05, 'spot', (12, 0, 0), 70, c))
    for o in night:
        o.hide_render = True
    hum = V.mannequin('human', 3.9, 0.3, math.pi / 2, c)
    lamp_pb = V.EMIT['lamp_warm'][0]
    stl = night[2]

    def set_state(view):
        op = view == 'night'
        rd.rotation_euler = (0, 0, math.radians(-100) if op else 0)
        sm.hide_render = view in ('side', 'inside')
        V.set_room_glow(0.42 if op else 0.0)
        hum.hide_render = view == 'inside'
        hum.location, hum.rotation_euler = {
            'day': ((1.9, 2.25, 0), (0, 0, -math.pi / 2)), 'night': ((-3.6, 1.4, 0), (0, 0, -0.6)),
            'side': ((3.9, 0.3, 0), (0, 0, math.pi / 2)), 'inside': ((0, 0, -5), (0, 0, 0))}[view]
        if op:
            l2.data.energy, l1.data.energy, stl.data.energy = 40, 25, 12
        else:
            l2.data.energy, l1.data.energy, stl.data.energy = 12, 18, 10
            lamp_pb.inputs['Emission Strength'].default_value = 3.5

    return dict(cams=CAMS, set_state=set_state, night_lights=night, human=hum)
