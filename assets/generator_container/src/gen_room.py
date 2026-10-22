"""Generator shed kit, part 3: the switchboard (cabinet, door with a latch and the circuit card, meters, lamps, kWh
counter, LINE / OFF / GEN changeover, two main breakers, eight circuit breakers), the 100 l day tank on wall brackets
(filler cap, vent, sight glass with a level column, supply valve, drain cock, feed and return lines to the engine),
three 200 l drums (winter diesel, summer diesel, petrol) with bungs and stencils, the spill pallet, the rotary drum
pump with its crank, hose and nozzle, the shelf (engine oil, coolant, spare filter, funnel, toolbox, rags, jumper
cables, bung wrench), the extinguisher, the insulating mat, the logbook on its nail; audio / VFX / hide points, the
static collider boxes and the knock rays.
Shed frame (gen_kit): x east, y north, z up."""
import math
import numpy as np
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import (kb, part, socket, box6, face, quad, uv, GY, FLOOR, X0, X1, Y0, Y1, IX0, IX1, IY0, IY1, ZE, DOOR, WIN,
                     LOUV, EXH_Y, EXH_Z, STACK_X, STACK_TOP, XV, YE, CP, SP, z_rb, BOARD_X,
                     Z_CAB, Z_CABIN, Z_BRK, Z_MCB, Z_TOGGLE, Z_REDH, Z_TANKP, Z_DRUMB, Z_DRUMR, Z_PALLET, Z_PUMP,
                     Z_HOSEP, Z_STEELP, Z_BRASSP, Z_WOOD, Z_OILCAN, Z_JUG, Z_BOXC, Z_TOOLBOX, Z_RAG, Z_CABLEJ, Z_EXT, Z_MAT,
                     Z_HARDB, Z_COPPERP, Z_CABLER, Z_CABLEB)
import gen_set as GS
import gen_tex as GT
from van2_kit import up_axes, rrect, ZERO

BX0, BX1 = BOARD_X
BY_FACE, BZ0 = -1.46, 0.95                         # board plate plane (normal +y) and its bottom edge
B_N = Vector((0, 1, 0))
DT = dict(x0=-1.20, x1=-0.40, y0=1.20, y1=1.52, z0=1.30, z1=1.72)
DR, DH = 0.2925, 0.88                              # drum radius / height
DRUMS = {'Drum_1': (Vector((1.27, 1.235, 0.24)), Z_DRUMB, 'st_dw', -90.0),
         'Drum_2': (Vector((1.88, 1.235, 0.24)), Z_DRUMB, 'st_ds', -90.0),
         'Drum_3': (Vector((1.95, -1.20, FLOOR)), Z_DRUMR, 'st_petrol', 135.0)}
SHELF = dict(x0=IX0, x1=IX0 + 0.30, y0=0.95, y1=1.55)
FUEL_ROUTES = None                                 # (feed, ret) override in the tank's frame (the generator container re-routes them)


def bp(u, v, off=0.0):
    """switchboard plate point: u across (right seen from the room = -x), v up from the plate's bottom edge"""
    return Vector(((BX0 + BX1) / 2 - u, BY_FACE + off, BZ0 + v))


def toggle(name, k_body, c, n, v_ax, body, lever_len, lever_w, zone_body, zone_lever, parent, note, states, rng=(0, 60)):
    """breaker / switch body on a panel point c (normal n) with a lever that flips about n x v (up = +)"""
    u_ax = v_ax.cross(n)
    R = Matrix((u_ax, v_ax, n)).transposed()
    k_body.box_m(c + n * body[2] / 2, body, zone_body, R)
    piv = c + n * body[2]
    L = kb(name, 'Props')
    d0 = (n * 0.87 - v_ax * 0.5).normalized()
    w_ax = d0.cross(u_ax).normalized()
    L.box_m(piv + d0 * lever_len / 2, (lever_w, lever_w * 0.6, lever_len), zone_lever, Matrix((u_ax, w_ax, d0)).transposed())
    part(name, 'hinge', piv, n.cross(v_ax), rng, parent=parent, states=states, note=note)
    socket('Hand_' + name, piv + d0 * lever_len, 'hand', parent=name)
    return piv


# ================================================================ switchboard
def switchboard():
    S = kb('Switchboard', 'Props')
    y0, y1, z0, z1, t = IY0, -1.36, 0.90, 2.00, 0.015
    zc = {'*': Z_CAB}
    box6(S, (BX0, y0, z0), (BX1, y0 + t, z1), {'+y': Z_CABIN, '*': Z_CAB})                    # back
    box6(S, (BX0, y0 + t, z0), (BX0 + t, y1, z1), {'+x': Z_CABIN, '*': Z_CAB})                # sides
    box6(S, (BX1 - t, y0 + t, z0), (BX1, y1, z1), {'-x': Z_CABIN, '*': Z_CAB})
    box6(S, (BX0 + t, y0 + t, z1 - t), (BX1 - t, y1, z1), {'-z': Z_CABIN, '*': Z_CAB})       # top, bottom
    box6(S, (BX0 + t, y0 + t, z0), (BX1 - t, y1, z0 + t), {'+z': Z_CABIN, '*': Z_CAB})
    box6(S, (BX0 + 0.02, BY_FACE - 0.010, z0 + 0.02), (BX1 - 0.02, BY_FACE - 0.002, z1 - 0.02), Z_CABIN)   # mounting plate
    for x in (BX0 + 0.10, (BX0 + BX1) / 2, BX1 - 0.12):                                      # cable glands
        S.cyl((x, -1.50, z0), (x, -1.50, z0 - 0.025), 0.018, Z_BRK, 8)
    F = kb('Board_Face', 'panel')
    quad(F, bp(0, GT.BD_H / 2, 0.0), B_N, GT.BD_W, GT.BD_H, uv('board'))
    part('Board_Face', 'static', bp(0, GT.BD_H / 2), parent='Switchboard', note='switchboard face plate (panel atlas)')
    B = GT.BOARD
    scales = {'acv': (0, 500, -120, 120, 'V'), 'aca': (0, 100, -120, 120, 'A'), 'hz': (45, 55, -120, 120, 'Hz')}
    for key, nm in (('acv', 'Needle_BoardV'), ('aca', 'Needle_BoardA'), ('hz', 'Needle_BoardHz')):
        u_, v_, d_ = B[key]
        c = bp(u_, v_)
        F.disc_uv(c + B_N * 0.003, B_N, d_ / 2, uv(key), 16)
        GS.bezel(S, c, B_N, d_ / 2, zone=Z_BRK, h=0.010)
        GS.needle(nm, c + B_N * 0.006, B_N, d_ / 2 * 0.80, scales[key][2], 'Switchboard', scales[key])
    u_, v_, w_, h_ = B['kwh']
    c = bp(u_, v_)
    quad(F, c + B_N * 0.002, B_N, w_, h_, uv('kwh'))
    for lo, hi in (((c.x - w_ / 2 - 0.008, c.y, c.z + h_ / 2), (c.x + w_ / 2 + 0.008, c.y + 0.008, c.z + h_ / 2 + 0.008)),
                   ((c.x - w_ / 2 - 0.008, c.y, c.z - h_ / 2 - 0.008), (c.x + w_ / 2 + 0.008, c.y + 0.008, c.z - h_ / 2)),
                   ((c.x - w_ / 2 - 0.008, c.y, c.z - h_ / 2), (c.x - w_ / 2, c.y + 0.008, c.z + h_ / 2)),
                   ((c.x + w_ / 2, c.y, c.z - h_ / 2), (c.x + w_ / 2 + 0.008, c.y + 0.008, c.z + h_ / 2))):
        box6(S, lo, hi, Z_BRK, skip=('-y',))
    for t_, colr, u_ in B['lamps']:
        c = bp(u_, B['lamp_v'])
        r = B['lamp_d'] / 2
        GS.bezel(S, c, B_N, r + 0.002, zone=Z_BRK, h=0.010, seg=10)
        L = kb('BLamp_' + t_, 'lens:' + colr)
        L.disc_uv(c + B_N * 0.003, B_N, r, uv('l_' + colr), 10, dome=0.007)
        part('BLamp_' + t_, 'static', c + B_N * 0.006, parent='Switchboard',
             note={'LINE': 'white: grid voltage on the LINE drop', 'GEN': 'green: the set is running and Gen_Breaker is on',
                   'OVERLOAD': 'red: more than 63 A drawn (too many circuits at once): a breaker trips'}[t_])
    u_, v_, d_ = B['changeover']
    c = bp(u_, v_)
    S.lathe(c, B_N, [(0.0, d_ / 2), (0.012, d_ / 2), (0.016, d_ / 2 - 0.008)], Z_BRK, 16, cap0=False, cap1=True)
    Ch = kb('Board_Changeover', 'Props')
    Ch.cyl(c + B_N * 0.016, c + B_N * 0.030, 0.022, Z_BRK, 10)
    Ch.box_m(c + B_N * 0.040, (0.028, 0.022, 0.13), Z_REDH)
    part('Board_Changeover', 'hinge', c, -B_N, (-60, 60), parent='Switchboard', states=['LINE -60', 'OFF 0', 'GEN 60'],
         note='changeover switch: the handle points at LINE (-60), OFF (0) or GEN (+60); + = clockwise seen from the room')
    socket('Hand_Board_Changeover', c + B_N * 0.045 + Vector((0, 0, 0.05)), 'hand', parent='Board_Changeover')
    v_ax = Vector((0, 0, 1))
    for key, nm, note in (('brk_gen', 'Board_Brk_Gen', 'GEN main breaker (63 A): up = the set feeds the busbar (with GEN selected)'),
                          ('brk_line', 'Board_Brk_Line', 'LINE main breaker (63 A): up = the grid feeds the busbar (with LINE selected)')):
        u_, v_ = B[key]
        toggle(nm, S, bp(u_, v_), B_N, v_ax, (0.09, 0.13, 0.05), 0.035, 0.022, Z_BRK, Z_TOGGLE, 'Switchboard', note,
               ['off (down)', 'on (up)', 'tripped (middle)'])
    S.box_m(bp(0.0, B['mcb_v'], 0.005), (0.76, 0.01, 0.035), Z_STEELP)                              # DIN rail
    for i, cn in enumerate(GT.CIRCUITS):
        toggle(f'Board_MCB_{i + 1}', S, bp(B['mcb_u0'] + i * B['mcb_du'], B['mcb_v'], 0.01), B_N, v_ax, (0.082, 0.09, 0.045),
               0.022, 0.013, Z_MCB, Z_TOGGLE, 'Switchboard',
               f'circuit breaker {i + 1}: {cn} (up = on); trips on overload', ['off (down)', 'on (up)', 'tripped (middle)'])
    socket('Audio_Board', bp(0, 0.5, 0.05), 'audio', parent='Switchboard', note='hum of the busbar, the clack of the breakers, '
           'the changeover thunk, a breaker tripping')
    socket('VFX_BoardSparks', bp(0.19, 0.40, 0.06), 'vfx', parent='Switchboard', dir=(0, 1, 0),
           note='sparks / smoke when a breaker trips under load or the changeover is thrown on load')
    # door: steel leaf, two hinges at the west edge, quarter-turn latch, DANGER sign outside, circuit card inside
    D = kb('Board_Door', 'Props')
    dx0, dx1, dy0, dy1, dz0, dz1 = BX0 - 0.005, BX1 + 0.005, -1.36, -1.34, z0 - 0.005, z1 + 0.005
    box6(D, (dx0, dy0, dz0), (dx1, dy1, dz1), {'-y': Z_CABIN, '*': Z_CAB})
    piv = Vector((dx0, dy1, (dz0 + dz1) / 2))
    for zh in (1.12, 1.78):
        D.cyl(Vector((dx0, dy1, zh - 0.05)), Vector((dx0, dy1, zh + 0.05)), 0.008, Z_STEELP, 6)
        S.box(BX0 - 0.012, BX0, -1.372, -1.342, zh - 0.04, zh + 0.04, Z_STEELP)
    part('Board_Door', 'hinge', piv, (0, 0, 1), (0, 100), parent='Switchboard', states=['shut', 'open'],
         note='switchboard door: unlock Board_Latch (90), swings into the room on its west hinges')
    socket('Hand_Board_Door', (dx1 - 0.05, dy1 + 0.03, 1.45), 'hand', parent='Board_Door')
    La = kb('Board_Latch', 'Props')
    lp = Vector((dx1 - 0.045, dy1, 1.45))
    La.cyl(lp, lp + Vector((0, 0.014, 0)), 0.015, Z_BRK, 10)
    La.box_m(lp + Vector((0, 0.02, 0)), (0.012, 0.012, 0.065), Z_BRK)
    part('Board_Latch', 'twist', lp, (0, -1, 0), (0, 90), parent='Board_Door', removable=False, states=['locked', 'open'],
         note='quarter-turn latch: + (clockwise seen from the room) to 90 opens the door')
    socket('Hand_Board_Latch', lp + Vector((0, 0.025, 0)), 'hand', parent='Board_Latch')
    Sg = kb('Board_Door_Signs', 'panel')
    quad(Sg, ((BX0 + BX1) / 2, dy1 + 0.003, 1.74), B_N, 0.16, 0.16, uv('sign_danger'))
    quad(Sg, ((BX0 + BX1) / 2, dy0 - 0.003, 1.40), -B_N, 0.16, 0.20, uv('card'))
    part('Board_Door_Signs', 'static', piv, parent='Board_Door', note='DANGER sign outside, the circuit card inside the door')
    part('Switchboard', 'static', ((BX0 + BX1) / 2, IY0, z0), parent='Shed', note='main switchboard cabinet on the south wall')


# ================================================================ day tank and fuel lines
def day_tank():
    T = kb('DayTank', 'Props')
    d = DT
    cx = (d['x0'] + d['x1']) / 2
    VM.rbox(T, (cx, (d['y0'] + d['y1']) / 2, (d['z0'] + d['z1']) / 2), (d['x1'] - d['x0'], d['y1'] - d['y0'], d['z1'] - d['z0']),
            Z_TANKP, r=0.02, ch=0.008)
    for x in (d['x0'] + 0.10, d['x1'] - 0.10):                                                  # wall brackets
        box6(T, (x - 0.02, d['y0'] + 0.02, d['z0'] - 0.03), (x + 0.02, IY1, d['z0']), Z_STEELP)
        T.strip([Vector((x, d['y0'] + 0.05, d['z0'] - 0.02)), Vector((x, IY1 - 0.006, 0.97))], (1, 0, 0), 0.006, 0.03, Z_STEELP)
        box6(T, (x - 0.04, IY1 - 0.012, 0.93), (x + 0.04, IY1, d['z0'] + 0.01), Z_STEELP, skip=('+y',))
    neck = Vector((-0.55, 1.36, d['z1']))
    T.cyl(neck - Vector((0, 0, 0.005)), neck + Vector((0, 0, 0.055)), 0.035, Z_TANKP, 12)
    Cp = kb('DayTank_Cap', 'Props')
    cp = neck + Vector((0, 0, 0.055))
    Cp.lathe(cp, (0, 0, 1), [(0.0, 0.042), (0.02, 0.042), (0.026, 0.03), (0.03, 0.0)], Z_STEELP, 12, cap0=True)
    Cp.box_m(cp + Vector((0, 0, 0.024)), (0.06, 0.01, 0.012), Z_STEELP)
    part('DayTank_Cap', 'twist', cp, (0, 0, 1), (0, 540), parent='DayTank', removable='end', states=['on', 'off'],
         note='filler cap of the day tank: unscrew (+, one and a half turns), then it comes off')
    socket('Hand_DayTank_Cap', cp + Vector((0, 0, 0.025)), 'hand', parent='DayTank_Cap')
    socket('Pour_DayTank', neck + Vector((0, 0, 0.06)), 'pour', parent='DayTank',
           note='diesel goes in here (DrumPump_Nozzle, a jerrycan with the van\'s Spout); 100 l')
    T.tube([Vector((-0.46, 1.46, d['z1'])), Vector((-0.46, 1.46, 2.25)), Vector((-0.46, 1.50, 2.29)), Vector((-0.46, 1.72, 2.29)),
            Vector((-0.46, 1.80, 2.27)), Vector((-0.46, 1.82, 2.20)), Vector((-0.46, 1.82, 2.15))], 0.012, Z_STEELP, 6)
    # sight glass: fittings, glass tube, level column, guard rods
    sg = Vector((-1.12, d['y0'], 0.0))
    for z in (1.34, 1.68):
        T.box(sg.x - 0.015, sg.x + 0.015, d['y0'] - 0.03, d['y0'], z - 0.015, z + 0.015, Z_BRASSP)
    gl = kb('DayTank_Glass', 'glass')
    gl.cyl((sg.x, d['y0'] - 0.03, 1.355), (sg.x, d['y0'] - 0.03, 1.665), 0.009, ZERO, 8, caps=False)
    part('DayTank_Glass', 'static', (sg.x, d['y0'] - 0.03, 1.51), parent='DayTank', note='sight glass tube (glass material)')
    lv = kb('DayTank_Level', 'diesel')
    lv.cyl((sg.x, d['y0'] - 0.03, 1.357), (sg.x, d['y0'] - 0.03, 1.663), 0.0062, ZERO, 8)
    part('DayTank_Level', 'stretch', (sg.x, d['y0'] - 0.03, 1.357), (0, 0, 1), (0, 1), unit='scale', parent='DayTank',
         states=['0 empty', '1 full (100 l)'],
         note='diesel column in the sight glass: scale along +z = tank fraction (1 = modelled full); the scale reads F .. E')
    for dx in (-0.016, 0.016):
        T.cyl((sg.x + dx, d['y0'] - 0.03, 1.34), (sg.x + dx, d['y0'] - 0.03, 1.68), 0.0022, Z_STEELP, 4)
    Dc = kb('DayTank_Decals', 'panel')
    quad(Dc, (sg.x + 0.032, d['y0'] - 0.003, 1.51), (0, -1, 0), 0.035, 0.30, uv('lvl'))
    quad(Dc, (-0.74, d['y0'] - 0.003, 1.52), (0, -1, 0), 0.30, 0.12, uv('st_tank'))
    quad(Dc, (-0.55, d['y0'] - 0.003, 1.675), (0, -1, 0), 0.12, 0.04, uv('sign_diesel'))
    part('DayTank_Decals', 'static', (cx, d['y0'], 1.5), parent='DayTank', note='level scale, DIESEL DAY TANK stencil, DIESEL ONLY')
    # supply valve (ball valve under the tank), drain cock, drip tray
    vx = -0.44
    T.cyl((vx, 1.36, d['z0'] + 0.005), (vx, 1.36, 1.27), 0.012, Z_TANKP, 8)
    T.box(vx - 0.025, vx + 0.025, 1.335, 1.385, 1.21, 1.27, Z_BRASSP)
    T.cyl((vx, 1.335, 1.24), (vx, 1.32, 1.24), 0.006, Z_STEELP, 6)
    Vl = kb('DayTank_Valve', 'Props')
    vp = Vector((vx, 1.32, 1.24))
    Vl.box_m(vp + Vector((0.05, -0.004, 0)), (0.10, 0.006, 0.016), Z_STEELP)
    Vl.box_m(vp + Vector((0.08, -0.004, 0)), (0.05, 0.012, 0.022), Z_REDH)
    part('DayTank_Valve', 'hinge', vp, (0, 1, 0), (0, 90), parent='DayTank', states=['shut (across the pipe)', 'open (along it)'],
         note='fuel supply ball valve: + (clockwise seen from the room) turns the red lever down along the pipe = open; '
              'shut = no fuel to the engine')
    socket('Hand_DayTank_Valve', vp + Vector((0.09, -0.01, 0)), 'hand', parent='DayTank_Valve')
    T.cyl((-1.15, 1.36, d['z0'] + 0.005), (-1.15, 1.36, 1.27), 0.008, Z_TANKP, 6)
    T.box(-1.165, -1.135, 1.345, 1.375, 1.245, 1.27, Z_BRASSP)
    Dr = kb('DayTank_Drain', 'Props')
    dp = Vector((-1.15, 1.36, 1.245))
    Dr.cyl(dp, dp - Vector((0, 0, 0.014)), 0.004, Z_BRASSP, 6)
    Dr.box_m(dp - Vector((0, 0, 0.017)), (0.035, 0.006, 0.008), Z_BRASSP)
    part('DayTank_Drain', 'twist', dp, (0, 0, -1), (0, 180), parent='DayTank', removable=False, states=['shut', 'open'],
         note='drain cock under the tank: + opens (water and sludge first, VFX_TankDrain)')
    socket('Hand_DayTank_Drain', dp - Vector((0, 0, 0.018)), 'hand', parent='DayTank_Drain')
    socket('VFX_TankDrain', dp - Vector((0, 0, 0.025)), 'vfx', parent='DayTank', dir=(0, 0, -1), note='drips into the tray')
    box6(T, (-1.30, 1.25, FLOOR), (-1.00, 1.47, FLOOR + 0.04), Z_STEELP, skip=('-z',))
    # feed (valve -> wall -> floor -> under the skid -> water separator) and return (leak-off -> tank top)
    feed = [(vx, 1.36, 1.21), (vx, 1.36, 1.10), (vx, 1.54, 1.02), (vx, 1.54, 0.115), (vx, 0.40, 0.115), (1.25, 0.40, 0.115),
            (1.25, GY - 0.50, 0.115)]
    ret = [(1.32, GY - 0.52, 0.115), (1.32, 0.43, 0.115), (-0.47, 0.43, 0.115), (-0.47, 1.555, 0.115), (-0.47, 1.555, 1.80),
           (-0.70, 1.48, 1.80), (-0.70, 1.48, d['z1'])]
    if FUEL_ROUTES is not None:
        feed, ret = FUEL_ROUTES
    for pts in (feed, ret):
        P_ = [Vector(p) for p in pts]
        T.tube(P_, 0.005, Z_COPPERP, 5)
        for a, b in zip(P_[:-1], P_[1:]):
            if abs(a.z - 0.115) < 1e-3 and abs(b.z - 0.115) < 1e-3:
                L = (b - a).length
                for i in range(1, int(L / 0.5) + 1):
                    p = a.lerp(b, i / (int(L / 0.5) + 1))
                    T.box(p.x - 0.012, p.x + 0.012, p.y - 0.012, p.y + 0.012, FLOOR, FLOOR + 0.022, Z_STEELP)
    part('DayTank', 'static', (cx, IY1, d['z0']), parent='Shed', states=['fuel 0..100 l'],
         note='100 l day tank, gravity feed to the engine through DayTank_Valve; the level shows in the sight glass')


# ================================================================ drums, pallet, pump
def drum_mesh(k, base, zone, bungs):
    h = DH
    prof = [(0.0, 0.272), (0.004, 0.286), (0.006, DR + 0.006), (0.024, DR + 0.006), (0.030, DR)]
    for f in (0.33, 0.66):
        prof += [(h * f - 0.012, DR), (h * f - 0.006, DR + 0.009), (h * f + 0.006, DR + 0.009), (h * f + 0.012, DR)]
    prof += [(h - 0.030, DR), (h - 0.024, DR + 0.006), (h - 0.006, DR + 0.006), (h - 0.002, 0.286), (h - 0.006, 0.276),
             (h - 0.012, 0.272)]
    k.lathe(base, (0, 0, 1), prof, zone, 16, cap0=True, cap1=True)
    for c, r in bungs:                                                   # raised flanges
        k.lathe(c, (0, 0, 1), [(0.0, r + 0.008), (0.004, r + 0.008), (0.004, r + 0.002)], Z_STEELP, 10, cap0=False, cap1=True)


def drums():
    for name, (base, zone, st, face_deg) in DRUMS.items():
        k = kb(name, 'Props')
        top = base.z + DH - 0.012
        a = math.radians(face_deg)
        fdir = Vector((math.cos(a), math.sin(a), 0))
        bl = Vector((base.x, base.y, top)) + fdir * 0.19
        bv = Vector((base.x, base.y, top)) - fdir * 0.20
        drum_mesh(k, base, zone, [(bl, 0.032), (bv, 0.016)])
        plugs = [(name + '_Vent', bv, 0.016, 720, '3/4" vent bung: open it when pumping so the drum breathes')]
        if name != 'Drum_1':                                                  # drum 1's 2" hole holds the pump
            plugs.insert(0, (name + '_Bung', bl, 0.031, 1080, '2" bung: needs the BungWrench, three turns (+), then it comes out'))
        for nm, c, r, turns, note in plugs:
            b = kb(nm, 'Props')
            b.cyl(c + Vector((0, 0, 0.004)), c + Vector((0, 0, 0.012)), r, Z_STEELP, 6)
            b.box_m(c + Vector((0, 0, 0.015)), (r * 1.6, 0.006, 0.006), Z_STEELP)
            part(nm, 'twist', c + Vector((0, 0, 0.004)), (0, 0, 1), (0, turns), parent=name, removable='end', states=['in', 'out'],
                 note=note)
            socket('Hand_' + nm, c + Vector((0, 0, 0.016)), 'hand', parent=nm)
        socket('Slot_DrumPump_' + name[-1], bl + Vector((0, 0, 0.004)), 'item_slot', parent=name,
               note='the DrumPump stands in this bung hole (bung out)')
        # curved stencil between the hoops, facing the room
        S = kb(name + '_Stencil', 'panel')
        u0, v0, u1, v1 = uv(st)
        r = DR + 0.0015
        zb, zt = base.z + 0.375, base.z + 0.495
        span = 0.36 / r
        segs = 6
        for i in range(segs):
            t0, t1 = a + span * (i / segs - 0.5), a + span * ((i + 1) / segs - 0.5)
            pa = [Vector((base.x + r * math.cos(t0), base.y + r * math.sin(t0), zb)),
                  Vector((base.x + r * math.cos(t1), base.y + r * math.sin(t1), zb)),
                  Vector((base.x + r * math.cos(t1), base.y + r * math.sin(t1), zt)),
                  Vector((base.x + r * math.cos(t0), base.y + r * math.sin(t0), zt))]
            # seen from outside, the viewer's right is the direction of increasing angle: u grows with t
            ua, ub = u0 + (u1 - u0) * i / segs, u0 + (u1 - u0) * (i + 1) / segs
            out = Vector((math.cos((t0 + t1) / 2), math.sin((t0 + t1) / 2), 0))
            face(S, pa, ZERO, out, [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
        part(name + '_Stencil', 'static', (base.x, base.y, (zb + zt) / 2), parent=name, note='painted stencil (panel atlas)')
    part('Drum_1', 'static', DRUMS['Drum_1'][0], parent='Pallet', states=['full', 'half', 'empty'],
         note='200 l drum, WINTER diesel (blue): the one that works in the cold; its 2" bung is out - the DrumPump lives here')
    part('Drum_2', 'static', DRUMS['Drum_2'][0], parent='Pallet', states=['full', 'half', 'empty', 'waxed'],
         note='200 l drum, SUMMER diesel (blue): waxes below about -10 C - it clogs the filter if used (story trap)')
    part('Drum_3', 'static', DRUMS['Drum_3'][0], parent='Shed', states=['full', 'half', 'empty'],
         note='200 l drum, PETROL (red): for the van, never for the genset')
    P = kb('Pallet', 'Props')
    for lo, hi in (((0.95, 0.92, FLOOR), (2.20, 0.94, 0.25)), ((0.95, 1.53, FLOOR), (2.20, 1.55, 0.25)),
                   ((0.95, 0.94, FLOOR), (0.97, 1.53, 0.25)), ((2.18, 0.94, FLOOR), (2.20, 1.53, 0.25))):
        box6(P, lo, hi, Z_PALLET, skip=('-z',))                          # sump walls
    face(P, [Vector((0.97, 0.94, 0.12)), Vector((2.18, 0.94, 0.12)), Vector((2.18, 1.53, 0.12)), Vector((0.97, 1.53, 0.12))],
         Z_PALLET, (0, 0, 1))                                            # sump floor
    face(P, [Vector((0.97, 0.94, 0.24)), Vector((2.18, 0.94, 0.24)), Vector((2.18, 1.53, 0.24)), Vector((0.97, 1.53, 0.24))],
         Z_PALLET, (0, 0, 1))
    part('Pallet', 'static', (1.575, 1.235, FLOOR), parent='Shed', note='spill pallet under the two diesel drums (grid deck)')


def pump():
    d1 = DRUMS['Drum_1'][0]
    top = d1.z + DH - 0.012
    bl = Vector((d1.x, d1.y - 0.19, top))
    P = kb('DrumPump', 'Props')
    P.cyl(bl, bl + Vector((0, 0, 0.022)), 0.036, Z_PUMP, 6)
    P.cyl(bl + Vector((0, 0, 0.022)), bl + Vector((0, 0, 0.18)), 0.016, Z_STEELP, 8)
    P.cyl(bl - Vector((0, 0, 0.002)), bl - Vector((0, 0, 0.80)), 0.014, Z_STEELP, 8, caps=False)
    bc = bl + Vector((0, 0, 0.247))
    P.cyl(bc + Vector((0, 0.045, 0)), bc - Vector((0, 0.045, 0)), 0.065, Z_PUMP, 14)
    P.lathe(bc - Vector((0, 0.045, 0)), (0, -1, 0), [(0.0, 0.068), (0.008, 0.068), (0.008, 0.05)], Z_PUMP, 14, cap0=False, cap1=True)
    P.tube([bc + Vector((0.035, 0, 0.045)), bc + Vector((0.08, 0, 0.085)), bc + Vector((0.11, 0, 0.085))], 0.016, Z_PUMP, 8)
    barb = bc + Vector((0.13, 0, 0.085))
    P.cyl(bc + Vector((0.11, 0, 0.085)), barb, 0.011, Z_STEELP, 6)
    coil_c = Vector((d1.x, d1.y, top + 0.014))
    path = [barb, barb + Vector((0.05, 0.03, -0.04)), barb + Vector((0.04, 0.12, -0.22)), coil_c + Vector((0.10, 0.0, 0.0))]
    for t in np.linspace(0, 10 * math.pi, 81)[1:]:                      # five turns: 3.5 m of hose with the run
        path.append(coil_c + Vector((0.10 * math.cos(t), 0.10 * math.sin(t), 0.024 * t / (2 * math.pi))))
    end = path[-1]
    P.tube(path, 0.012, Z_HOSEP, 6)
    part('DrumPump', 'item', bl, (0, 0, 1), parent='Drum_1', states=['in a drum', 'carried'],
         note='rotary drum pump: stands in a 2" bung hole (Slot_DrumPump_N), suction tube down to the bottom; crank to pump; '
              'the coiled hose goes with it (draw a rope from DrumPump_Hose_Start to the nozzle when it is taken off the coil)')
    socket('Hand_DrumPump', bc + Vector((0, 0, 0.07)), 'hand', parent='DrumPump')
    socket('DrumPump_Hose_Start', barb, 'item_slot', parent='DrumPump', note='hose leaves the pump here (3.5 m: reaches the day '
           'tank from any drum on the pallet)')
    socket('Audio_DrumPump', bc, 'audio', parent='DrumPump', note='clank of the crank, gurgle, splash in the tank')
    Cr = kb('DrumPump_Crank', 'Props')
    hub = bc - Vector((0, 0.05, 0))
    Cr.cyl(hub, hub - Vector((0, 0.015, 0)), 0.02, Z_STEELP, 8)
    Cr.box_m(hub + Vector((0, -0.012, 0.075)), (0.025, 0.01, 0.15), Z_STEELP)
    Cr.cyl(hub + Vector((0, -0.017, 0.14)), hub + Vector((0, -0.11, 0.14)), 0.014, Z_PUMP, 8)
    part('DrumPump_Crank', 'spin', hub, (0, -1, 0), parent='DrumPump', note='crank either way: about 0.3 l per turn')
    socket('Hand_DrumPump_Crank', hub + Vector((0, -0.08, 0.14)), 'hand', parent='DrumPump_Crank')
    Nz = kb('DrumPump_Nozzle', 'Props')
    n0 = end + Vector((-0.02, 0.0, 0.012))
    n1 = n0 + Vector((-0.06, 0.20, 0.0))
    Nz.cyl(end, n0, 0.013, Z_STEELP, 8)
    Nz.cyl(n0, n1, 0.010, Z_STEELP, 8)
    Nz.tube([n1, n1 + Vector((-0.01, 0.03, -0.02)), n1 + Vector((-0.012, 0.04, -0.05))], 0.008, Z_STEELP, 6)
    part('DrumPump_Nozzle', 'item', end, (n1 - n0).normalized(), parent='DrumPump', states=['on the coil', 'in hand', 'in a filler'],
         note='hose nozzle: into Pour_DayTank (or a jerrycan), then crank')
    socket('Hand_DrumPump_Nozzle', n0.lerp(n1, 0.3), 'hand', parent='DrumPump_Nozzle')
    socket('Nozzle_Tip', n1 + Vector((-0.012, 0.04, -0.05)), 'vfx', parent='DrumPump_Nozzle', dir=(0, 0, -1),
           note='fuel stream while cranking (splash if not in a filler)')


# ================================================================ shelf and props
def shelf_and_props():
    s = SHELF
    S = kb('Shelf', 'Props')
    for y in (s['y0'], s['y1'] - 0.02):
        box6(S, (s['x0'], y, FLOOR), (s['x1'], y + 0.02, 1.75), Z_WOOD)
    for z in (0.45, 0.95, 1.45):
        box6(S, (s['x0'], s['y0'] + 0.02, z), (s['x1'], s['y1'] - 0.02, z + 0.02), Z_WOOD)
    for z in (0.75, 1.25):
        box6(S, (s['x0'], s['y0'] + 0.02, z), (s['x0'] + 0.015, s['y1'] - 0.02, z + 0.07), Z_WOOD, skip=('-x',))
    VM.rbox(S, (s['x0'] + 0.15, 1.47, 0.52), (0.16, 0.11, 0.05), Z_RAG, r=0.025, ch=0.012)       # rags
    VM.rbox(S, (s['x0'] + 0.13, 1.45, 0.565), (0.12, 0.08, 0.04), Z_RAG, r=0.02, ch=0.01)
    for z in (0.80, 1.22):                                                                     # nails on the side
        S.cyl((s['x0'] + 0.12 if z > 1 else s['x0'] + 0.08, s['y0'], z), (s['x0'] + 0.12 if z > 1 else s['x0'] + 0.08, s['y0'] - 0.03, z),
              0.0025, Z_STEELP, 4)
    part('Shelf', 'static', (s['x0'], (s['y0'] + s['y1']) / 2, FLOOR), parent='Shed', note='wooden shelf on the west wall north of the door')
    xc = s['x0'] + 0.15
    # engine oil can (top board)
    O = kb('EngineOil', 'Props')
    ob = Vector((xc, 1.38, 1.47))
    VM.rbox(O, ob + Vector((0, 0, 0.14)), (0.12, 0.20, 0.28), Z_OILCAN, r=0.012, ch=0.006)
    O.tube([ob + Vector((0, 0.03, 0.28)), ob + Vector((0, 0.03, 0.31)), ob + Vector((0, 0.09, 0.31)), ob + Vector((0, 0.09, 0.28))],
           0.007, Z_OILCAN, 6, caps=False)
    sp = ob + Vector((0, -0.06, 0.28))
    O.cyl(sp, sp + Vector((0, 0, 0.022)), 0.017, Z_OILCAN, 8)
    part('EngineOil', 'item', ob, (0, 0, 1), parent='Shed', states=['oil 0..5 l'], note='5 l engine oil can: tip into Pour_Oil')
    socket('Hand_EngineOil', ob + Vector((0, 0.06, 0.31)), 'hand', parent='EngineOil')
    socket('Pour_EngineOil', sp + Vector((0, 0, 0.03)), 'pour', parent='EngineOil', note='oil comes out here (cap off)')
    Oc = kb('EngineOil_Cap', 'Props')
    Oc.cyl(sp + Vector((0, 0, 0.018)), sp + Vector((0, 0, 0.036)), 0.021, Z_REDH, 8)
    part('EngineOil_Cap', 'twist', sp + Vector((0, 0, 0.018)), (0, 0, 1), (0, 360), parent='EngineOil', removable='end',
         states=['on', 'off'], note='screw cap of the oil can')
    # coolant jug (middle board)
    J = kb('Coolant', 'Props')
    jb = Vector((xc, 1.40, 0.97))
    VM.rbox(J, jb + Vector((0, 0, 0.13)), (0.12, 0.16, 0.26), Z_JUG, r=0.02, ch=0.008)
    J.tube([jb + Vector((0, 0.03, 0.23)), jb + Vector((0, 0.03, 0.29)), jb + Vector((0, 0.075, 0.29)), jb + Vector((0, 0.075, 0.23))],
           0.009, Z_JUG, 6, caps=False)
    jsp = jb + Vector((0, -0.045, 0.26))
    J.cyl(jsp, jsp + Vector((0, 0, 0.02)), 0.018, Z_JUG, 8)
    part('Coolant', 'item', jb, (0, 0, 1), parent='Shed', states=['coolant 0..5 l'], note='5 l coolant (antifreeze mix): into Pour_Coolant')
    socket('Hand_Coolant', jb + Vector((0, 0.05, 0.29)), 'hand', parent='Coolant')
    socket('Pour_CoolantJug', jsp + Vector((0, 0, 0.03)), 'pour', parent='Coolant', note='coolant comes out here (cap off)')
    Jc = kb('Coolant_Cap', 'Props')
    Jc.cyl(jsp + Vector((0, 0, 0.016)), jsp + Vector((0, 0, 0.034)), 0.021, Z_BOXC, 8)
    part('Coolant_Cap', 'twist', jsp + Vector((0, 0, 0.016)), (0, 0, 1), (0, 360), parent='Coolant', removable='end',
         states=['on', 'off'], note='screw cap of the coolant jug')
    # spare fuel filter, funnel, toolbox
    Ff = kb('FuelFilter_Spare', 'Props')
    box6(Ff, (xc - 0.06, 1.04, 0.97), (xc + 0.06, 1.16, 1.13), Z_BOXC)
    part('FuelFilter_Spare', 'item', (xc, 1.10, 0.97), (0, 0, 1), parent='Shed',
         note='spare fuel filter in its box: replaces the clogged one (waxed summer diesel)')
    socket('Hand_FuelFilter_Spare', (xc, 1.10, 1.13), 'hand', parent='FuelFilter_Spare')
    Fu = kb('Funnel', 'Props')
    fb = Vector((xc, 1.10, 1.47))
    prof = [(0.0, 0.08), (0.075, 0.022), (0.14, 0.012), (0.15, 0.011)]
    Fu.lathe(fb, (0, 0, 1), prof, Z_STEELP, 12, cap0=False, cap1=False)
    Fu.lathe(fb, (0, 0, 1), [(a, r - 0.0015) for a, r in reversed(prof)], Z_STEELP, 12, cap0=False, cap1=False)
    part('Funnel', 'item', fb, (0, 0, 1), parent='Shed', note='steel funnel (stands on its rim): goes into any filler')
    socket('Hand_Funnel', fb + Vector((0, 0, 0.10)), 'hand', parent='Funnel')
    Tb = kb('Toolbox', 'Props')
    tb = Vector((xc, 1.20, 0.47))
    VM.rbox(Tb, tb + Vector((0, 0, 0.09)), (0.20, 0.36, 0.18), Z_TOOLBOX, r=0.01, ch=0.004)
    Tb.tube([tb + Vector((0, -0.08, 0.18)), tb + Vector((0, -0.08, 0.22)), tb + Vector((0, 0.08, 0.22)), tb + Vector((0, 0.08, 0.18))],
            0.008, Z_STEELP, 6, caps=False)
    part('Toolbox', 'item', tb, (0, 0, 1), parent='Shed', note='red toolbox (spanners: lets Engine_GovernorLever move)')
    socket('Hand_Toolbox', tb + Vector((0, 0, 0.22)), 'hand', parent='Toolbox')
    # jumper cables and the bung wrench hanging on the shelf side (facing the door)
    Jm = kb('JumperCables', 'Props')
    jc = Vector((s['x0'] + 0.12, s['y0'] - 0.035, 1.12))
    for k, (zone, dy) in enumerate(((Z_CABLER, 0.0), (Z_CABLEB, -0.016))):
        ring = [jc + Vector((0.09 * math.sin(t), dy, 0.10 - 0.10 * math.cos(t))) for t in np.linspace(0, 2 * math.pi, 15)]
        Jm.tube(ring, 0.006, zone, 5, caps=False)
        for sx in (-1, 1):
            e = jc + Vector((sx * 0.05, dy, -0.02))
            Jm.tube([jc + Vector((sx * 0.03, dy, 0.01)), e, e + Vector((0, 0, -0.05))], 0.006, zone, 5)
            Jm.box_m(e + Vector((0, 0, -0.08)), (0.02, 0.012, 0.06), Z_CABLEJ)
    for k, (col_, dy) in enumerate((('Red', 0.0), ('Black', -0.016))):
        for sx, end_ in ((-1, 'A'), (1, 'B')):
            socket(f'JumperCables_{col_}{end_}', jc + Vector((sx * 0.05, dy, -0.11)), 'item_slot', parent='JumperCables',
                   note=f'{col_.lower()} clamp, end {end_}: clips onto Jump_Pos / Jump_Neg (or the van\'s battery posts)')
    part('JumperCables', 'item', jc + Vector((0, 0, 0.10)), (0, 0, 1), parent='Shed',
         note='jumper cables (red +, black -), 3 m: the van battery to the genset battery when it is flat (ropes between the clamp ends)')
    socket('Hand_JumperCables', jc + Vector((0, 0, 0.19)), 'hand', parent='JumperCables')
    Bw = kb('BungWrench', 'Props')
    bw = Vector((s['x0'] + 0.08, s['y0'] - 0.035, 0.80))
    Bw.box_m(bw + Vector((0, 0, -0.16)), (0.035, 0.008, 0.33), Z_STEELP)
    Bw.box_m(bw + Vector((0, 0, -0.33)), (0.07, 0.012, 0.03), Z_STEELP)
    Bw.lathe(bw, (0, 1, 0), [(-0.004, 0.012), (0.004, 0.012)], Z_STEELP, 8, cap0=False, cap1=False)
    part('BungWrench', 'item', bw, (0, 0, 1), parent='Shed', note='drum bung wrench: opens Drum_N_Bung and Drum_N_Vent')
    socket('Hand_BungWrench', bw + Vector((0, 0, -0.10)), 'hand', parent='BungWrench')
    # extinguisher on its bracket (west wall, south of the door)
    E = kb('Extinguisher', 'Props')
    eb = Vector((IX0 + 0.085, -1.30, 0.70))
    E.lathe(eb, (0, 0, 1), [(0.0, 0.07), (0.01, 0.075), (0.45, 0.075), (0.50, 0.05), (0.52, 0.025)], Z_EXT, 12, cap0=True, cap1=True)
    E.cyl(eb + Vector((0, 0, 0.52)), eb + Vector((0, 0, 0.56)), 0.018, Z_STEELP, 8)
    E.box_m(eb + Vector((0.02, 0, 0.566)), (0.10, 0.02, 0.012), Z_STEELP)
    E.tube([eb + Vector((-0.02, 0, 0.55)), eb + Vector((-0.08, 0, 0.50)), eb + Vector((-0.085, 0, 0.20)), eb + Vector((-0.08, 0, 0.12))],
           0.007, Z_HOSEP, 5)
    part('Extinguisher', 'item', eb, (0, 0, 1), parent='Shed', states=['full', 'used'],
         note='6 kg powder extinguisher on its wall bracket: squeeze the lever (VFX_Extinguisher at the hose end)')
    socket('Hand_Extinguisher', eb + Vector((0.02, 0, 0.58)), 'hand', parent='Extinguisher')
    socket('VFX_Extinguisher', eb + Vector((-0.08, 0, 0.12)), 'vfx', parent='Extinguisher', dir=(0, 0, -1), note='powder cloud')
    socket('Slot_Extinguisher', eb, 'item_slot', parent='Shed', note='the extinguisher hangs here')
    # insulating mat in front of the board, logbook on a nail between the board and the window
    M = kb('Mat', 'Props')
    box6(M, (BX0, -1.26, FLOOR), (BX1, -0.70, FLOOR + 0.008), Z_MAT, skip=('-z',))
    part('Mat', 'static', ((BX0 + BX1) / 2, -0.98, FLOOR), parent='Shed', note='rubber insulating mat in front of the switchboard')
    K.KBS['Shed'].cyl((-0.75, IY0, 1.62), (-0.75, IY0 + 0.03, 1.62), 0.0025, K.Z_STEELBLK, 4)
    Lb = kb('Logbook', 'Props')
    lb = Vector((-0.75, IY0 + 0.012, 1.45))
    box6(Lb, (lb.x - 0.115, IY0 + 0.009, lb.z - 0.16), (lb.x + 0.115, IY0 + 0.015, lb.z + 0.16), Z_HARDB)
    box6(Lb, (lb.x - 0.04, IY0 + 0.015, lb.z + 0.12), (lb.x + 0.04, IY0 + 0.026, lb.z + 0.15), Z_STEELP)
    Lp = kb('Logbook_Page', 'panel')
    quad(Lp, (lb.x, IY0 + 0.018, lb.z - 0.02), (0, 1, 0), 0.21, 0.27, uv('logpage'))
    part('Logbook', 'item', lb, (0, 0, 1), parent='Shed', note='generator log on a clipboard (hangs on a nail): the last entries')
    part('Logbook_Page', 'static', (lb.x, IY0 + 0.0158, lb.z), parent='Logbook', note='the log page (panel atlas)')
    socket('Hand_Logbook', lb + Vector((0, 0.01, 0.14)), 'hand', parent='Logbook')
    socket('Nail_Logbook', (-0.75, IY0 + 0.025, 1.62), 'item_slot', parent='Shed', note='the logbook hangs here')


# ================================================================ points
def play_points():
    for name, kind, par, pos, d, note in (
            ('Audio_Exhaust', 'audio', 'Shed', (STACK_X, EXH_Y, STACK_TOP), None, 'exhaust beat at the stack (outside), the flap rattling'),
            ('Audio_Louvre', 'audio', 'Shed', (IX1, GY, 0.95), None, 'louvre blades rattling in the wind / in the fan blast'),
            ('Audio_Door', 'audio', 'Shed', (X0, 0.0, 1.10), None, 'door leaves: creak, the hasp, the padlock, wind gap whistle'),
            ('Audio_Roof', 'audio', 'Shed', (0.0, 0.0, 3.30), None, 'roof: creaks in the cold, snow sliding off, footsteps up there'),
            ('Audio_Wind', 'audio', 'Shed', (X0, 0.0, 2.77), None, 'wind through the intake louvre in the west gable'),
            ('VFX_Exhaust', 'vfx', 'Shed', (STACK_X, EXH_Y, STACK_TOP + 0.03), (0, 0, 1),
             'exhaust: a black puff on starting, grey smoke under load, thin haze idling'),
            ('VFX_LouvreHeat', 'vfx', 'Shed', (X1 + 0.05, GY, 0.95), (1, 0, 0),
             'warm air from the radiator through the open louvre: steam in the frost, melts the snow below'),
            ('VFX_DoorSnow', 'vfx', 'Shed', (IX0 + 0.05, 0.0, 0.20), (1, 0, 0), 'snow blowing in under / between the leaves'),
            ('Heat_Louvre', 'heat', 'Shed', (X1 + 0.20, GY, 0.95), None, 'warm spot outside the louvre while the set runs')):
        socket(name, pos, kind, note=note, parent=par)
        if d is not None:
            K.CONTRACT['sockets'][name]['dir'] = list(d)
    for name, pose, hip, eye, facing, note in (
            ('Hide_Nook', 'crouch', (1.98, 0.62, FLOOR + 0.30), (1.92, 0.62, FLOOR + 0.88), (-1, 0, 0),
             'crouched in the nook between the radiator duct and the diesel drums (behind the genset from the door)'),
            ('Hide_UnderWindow', 'crouch', (-0.10, -1.27, FLOOR + 0.30), (-0.10, -1.21, FLOOR + 0.86), (0, 1, 0),
             'crouched under the window sill: not seen from outside through the glass')):
        socket(name, hip, 'hide', note=note, parent='Shed')
        K.CONTRACT['sockets'][name].update(pose=pose, eye=K.r4(eye), facing=list(facing))


def static_boxes():
    """(name, parent, (x0, x1, y0, y1, z0, z1), rotation_deg_xyz or None) in the shed frame"""
    sl = 0.12
    B = [('Slab', 'Shed', (X0 - sl, X1 + sl, Y0 - sl, Y1 + sl, 0.0, FLOOR), None),
         ('Wall_W_S', 'Shed', (X0, IX0, Y0, DOOR['y0'], FLOOR, ZE), None),
         ('Wall_W_N', 'Shed', (X0, IX0, DOOR['y1'], Y1, FLOOR, ZE), None),
         ('Wall_W_Head', 'Shed', (X0, IX0, DOOR['y0'], DOOR['y1'], DOOR['z1'], ZE), None),
         ('Gable_W_1', 'Shed', (X0, IX0, -1.70, 1.70, ZE, 2.65), None),
         ('Gable_W_2', 'Shed', (X0, IX0, -1.27, 1.27, 2.65, 2.85), None),
         ('Gable_W_3', 'Shed', (X0, IX0, -0.84, 0.84, 2.85, 3.05), None),
         ('Gable_W_4', 'Shed', (X0, IX0, -0.41, 0.41, 3.05, 3.25), None),
         ('Wall_E_S', 'Shed', (IX1, X1, Y0, LOUV['y0'], FLOOR, ZE), None),
         ('Wall_E_N', 'Shed', (IX1, X1, LOUV['y1'], Y1, FLOOR, ZE), None),
         ('Wall_E_Low', 'Shed', (IX1, X1, LOUV['y0'], LOUV['y1'], FLOOR, LOUV['z0']), None),
         ('Wall_E_High', 'Shed', (IX1, X1, LOUV['y0'], LOUV['y1'], LOUV['z1'], ZE), None),
         ('Louvre', 'Shed', (IX1, X1, LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1']), None),
         ('Gable_E_1', 'Shed', (IX1, X1, -1.70, 1.70, ZE, 2.65), None),
         ('Gable_E_2', 'Shed', (IX1, X1, -1.27, 1.27, 2.65, 2.85), None),
         ('Gable_E_3', 'Shed', (IX1, X1, -0.84, 0.84, 2.85, 3.05), None),
         ('Gable_E_4', 'Shed', (IX1, X1, -0.41, 0.41, 3.05, 3.25), None),
         ('Ridge', 'Shed', (-XV - 0.025, XV + 0.025, -0.12, 0.12, 3.28, 3.50), None),
         ('Wall_S_W', 'Shed', (IX0, WIN['x0'], Y0, IY0, FLOOR, ZE), None),
         ('Wall_S_E', 'Shed', (WIN['x1'], IX1, Y0, IY0, FLOOR, ZE), None),
         ('Wall_S_Low', 'Shed', (WIN['x0'], WIN['x1'], Y0, IY0, FLOOR, WIN['z0']), None),
         ('Wall_S_High', 'Shed', (WIN['x0'], WIN['x1'], Y0, IY0, WIN['z1'], ZE), None),
         ('Window', 'Shed', (WIN['x0'], WIN['x1'], Y0, IY0, WIN['z0'], WIN['z1']), None),
         ('Wall_N', 'Shed', (IX0, IX1, IY1, Y1, FLOOR, ZE), None),
         ('Stack', 'Shed', (STACK_X - 0.045, STACK_X + 0.045, EXH_Y - 0.045, EXH_Y + 0.045, EXH_Z - 0.05, STACK_TOP), None),
         ('StackPipe', 'Shed', (X1, STACK_X, EXH_Y - 0.045, EXH_Y + 0.045, EXH_Z - 0.045, EXH_Z + 0.045), None),
         ('Door_L', 'Door_L', (-2.47, -2.40, 0.0, 0.81, 0.11, 2.12), None),
         ('Door_R', 'Door_R', (-2.47, -2.40, -0.81, 0.0, 0.11, 2.12), None),
         ('Shutter', 'Window_Shutter', (0.23, 0.89, -1.565, -1.515, WIN['z0'], WIN['z1'] + 0.03), None),
         ('Genset_Skid', 'Genset', (GS.SK_X0, GS.SK_X1, GY - 0.42, GY + 0.42, FLOOR, GS.ZS), None),
         ('Genset_Engine', 'Genset', (0.20, 1.45, GY - 0.33, GY + 0.36, GS.ZS, 1.22), None),
         ('Genset_AirFilter', 'Genset', (0.57, 0.75, GY - 0.47, GY - 0.29, 1.00, 1.36), None),
         ('Genset_Silencer', 'Genset', (0.40, 1.12, GY + 0.05, GY + 0.23, 1.22, 1.51), None),
         ('Genset_Alternator', 'Genset', (-0.58, 0.20, GY - 0.40, GY + 0.42, GS.ZS, 0.90), None),
         ('Genset_Radiator', 'Genset', (1.40, 1.62, GY - 0.41, GY + 0.41, GS.ZS, 1.34), None),
         ('Genset_Duct', 'Genset', (1.62, IX1, GY - 0.50, GY + 0.50, 0.32, 1.42), None),
         ('Genset_Panel', 'Genset', (-0.67, -0.47, GY - 0.31, GY + 0.31, 0.98, 1.55), None),
         ('Genset_Riser', 'Genset', (1.16, 1.24, EXH_Y - 0.04, EXH_Y + 0.04, 1.40, 1.99), None),
         ('Genset_ExhaustPipe', 'Genset', (1.20, IX1, EXH_Y - 0.04, EXH_Y + 0.04, 1.91, 1.99), None),
         ('Switchboard', 'Switchboard', (BX0, BX1, IY0, -1.36, 0.90, 2.00), None),
         ('Board_Door', 'Board_Door', (BX0 - 0.005, BX1 + 0.005, -1.36, -1.34, 0.895, 2.005), None),
         ('DayTank', 'DayTank', (DT['x0'] - 0.02, DT['x1'] + 0.02, DT['y0'] - 0.04, IY1, 1.20, 1.80), None),
         ('Pallet', 'Pallet', (0.95, 2.20, 0.92, 1.55, FLOOR, 0.25), None),
         ('Shelf', 'Shelf', (SHELF['x0'], SHELF['x1'], SHELF['y0'] - 0.04, SHELF['y1'], FLOOR, 1.75), None)]
    for name, (base, zone, st, fd) in DRUMS.items():
        B.append((name, name, (base.x - DR - 0.01, base.x + DR + 0.01, base.y - DR - 0.01, base.y + DR + 0.01, base.z, base.z + DH), None))
    for s, nm in ((1, 'Roof_N'), (-1, 'Roof_S')):
        n = Vector((0, s * SP, CP))
        c = Vector((0, s * 1.0, z_rb(1.0))) + n * 0.11
        L = YE / CP + 0.06
        B.append((nm, 'Shed', (-XV - 0.025, XV + 0.025, c.y - L / 2, c.y + L / 2, c.z - 0.11, c.z + 0.11), (-s * 25.0, 0.0, 0.0)))
    return B


def knock_rays():
    """(name, origin, direction) rays from outside onto the shell; the build turns hits into knock sockets"""
    R = []
    for i, y in enumerate((-1.1, -0.2, 0.7)):
        R.append((f'Knock_WallE_{i + 1}', (3.4, y, 1.85 if abs(y - GY) < 0.6 else 1.25), (-1, 0, 0)))
    for i, x in enumerate((-1.6, -0.7, 0.9, 1.8)):
        R.append((f'Knock_WallS_{i + 1}', (x, -2.6, 1.15), (0, 1, 0)))
    for i, x in enumerate((-1.6, -0.6, 0.5, 1.6)):
        R.append((f'Knock_WallN_{i + 1}', (x, 2.6, 1.20), (0, -1, 0)))
    R += [('Knock_WallW_S', (-3.4, -1.25, 1.30), (1, 0, 0)), ('Knock_WallW_N', (-3.4, 1.25, 1.30), (1, 0, 0)),
          ('Knock_Door_L', (-3.4, 0.40, 1.20), (1, 0, 0)), ('Knock_Door_R', (-3.4, -0.40, 1.20), (1, 0, 0)),
          ('Knock_Window', (-0.25, -2.6, 1.42), (0, 1, 0))]                  # on a pane, not the glazing bar
    for i, (x, y) in enumerate(((-1.5, 0.9), (0.0, -0.9), (1.5, 0.9), (0.6, -1.4))):
        R.append((f'Knock_Roof_{i + 1}', (x, y, 4.5), (0, 0, -1)))
    return R


def build_room():
    switchboard()
    day_tank()
    drums()
    pump()
    shelf_and_props()
    play_points()
