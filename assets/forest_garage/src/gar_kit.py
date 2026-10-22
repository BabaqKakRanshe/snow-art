"""Garage (stand-alone, Forest map, prefab Garage) -- Update 3's hall (gar_spec) rebuilt in the generator shed's language
as one of the station's buildings: a small steel hall on a concrete upstand, trapezoidal sheet in the station's grey-green
paint, darker trims round the corners and openings, a drip flashing over the concrete; a flat roof (felt on the deck)
with an overhang, a steel edge profile and soffit, two scuppers and downpipes at the back; the concrete apron in front
of the gate, a step at the side door.
  openings: the up-and-over gate IX_GarageDoor_92 (ribbed leaf on a tube frame, the T-handle and lock rods, pivots at the
  top corners; the steel frame with its outer stops, the tracks and springs inside), the side door IX_GarageSideDoor_93
  (steel leaf opening out, steel frame with the stop inside, hinges outside), two steel windows with a mullion.
  inside: liner trays on the walls over the concrete upstand, the trapezoidal deck and three steel beams overhead, a
  power-floated floor with a drain; Update 3's contents where they stood: the quad (facing the gate's side, east),
  the shelving and its boxes, the crates, the workbench with the pegboard, the three drums (now on a spill pallet,
  the third inside the wall); the extinguisher, the sub-distribution board and its conduits, the two ceiling fittings
  and the bulkhead over the gate (Update 3's lights and glows stay where they were).
Objects: Garage (the static mesh, as Update 3's: built as KBs Garage (atlas GarExt), Garage__in (GarIn), Garage_Glass,
Garage_Panel, Garage__fluor / Garage__bulb (the lamp lenses, M_Lamp_FluorOff / M_Lamp_BulbOff) -- joined at export),
IX_GarageDoor_92 and IX_GarageSideDoor_93 (atlas GarParts, their panel decals joined in).
Frame: x east, y north, z up, origin on the floor in the middle of the hall (gar_spec); Unity (x, y, z) -> (-x, z, -y)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, merge_kb, Z_GALV, Z_STEELBLK
from cont_kit import corrugated, corr_profile, flat_wall, flat_h, _subtract, _split, _grid
import van2_kit as VK
import van3_mech as VM
import main_furn as F
import main_open as MO
import main_rooms as MR
import main_fx as FX
import gar_spec as S
import gar_tex as T

# ---------------------------------------------------------------- zones (700..)
(Z_SKIN, Z_TRIM, Z_LINER, Z_FLOOR, Z_PLINTH, Z_FELT, Z_FASCIA, Z_SOFFIT, Z_DECK, Z_BEAM, Z_APRON, Z_GATE, Z_GATEIN,
 Z_LEAF, Z_FRAME, Z_WINFRAME, Z_SPILL, Z_HOOK) = range(700, 718)
DRAFT_COL = {Z_SKIN: (104, 118, 94), Z_TRIM: (66, 76, 62), Z_LINER: (214, 214, 206), Z_FLOOR: (128, 126, 120),
             Z_PLINTH: (132, 130, 124), Z_FELT: (52, 52, 54), Z_FASCIA: (62, 70, 60), Z_SOFFIT: (120, 132, 112),
             Z_DECK: (150, 154, 152), Z_BEAM: (128, 62, 44), Z_APRON: (126, 124, 118), Z_GATE: (104, 118, 94),
             Z_GATEIN: (96, 108, 88), Z_LEAF: (104, 118, 94), Z_FRAME: (66, 76, 62), Z_WINFRAME: (66, 76, 62),
             Z_SPILL: (214, 170, 40), Z_HOOK: (40, 40, 40)}

# ---------------------------------------------------------------- dimensions (beyond gar_spec)
XO, YO, XI, YI = S.XO, S.YO, S.XI, S.YI
PLX, PLY = S.PLX, S.PLY
UPSTAND = 0.30                       # the concrete upstand's top: the sheets start here (the steel off the wet ground)
CORR = dict(pitch=0.207, crest=0.035, slope=0.045, depth=0.035)       # the walls' trapezoidal sheet (ribs outward)
DECK = dict(pitch=0.30, crest=0.06, slope=0.07, depth=0.06)          # the roof deck seen from below (narrow flanges down)
DECK_Z = S.EAVES                     # the deck's bottom flanges (Update 3's ceiling)
LINER_TOP = DECK_Z + DECK['depth']   # the liner trays run up to the deck's top flanges
BEAMS_X = (-4.0, 0.0, 4.0)           # IPE 300 across the hall (y), on columns inside the walls
BEAM = dict(h=0.30, b=0.15, tf=0.011, tw=0.0071)
EDGE_X, EDGE_Y = XO + S.ROOF_OV, YO + S.ROOF_OV                       # the roof's edge (Update 3: 12.4 x 9.4)
FASCIA_BOT, FASCIA_TOP, KERB = 4.36, S.ROOF_T + 0.03, 0.04
GATE_HEAD = 3.215                    # the gate's lintel: the leaf's inner top edge rises to 3.205 as it opens
LIP = (-YO - 0.02, -YO + 0.015)      # the gate frame's outer stops (y): 2 cm proud of the crests, 5 mm off the leaf
DRAIN = (-1.50, -1.20, 0.30)         # the floor drain: centre x, y, size
SCUPPERS_X = (-4.60, 4.60)
PIPE_Y = YO + 0.085                  # the downpipes' axis (clear of the plinth face)
SPILL = dict(x=(4.47, 5.75), y=(-2.93, -1.69), h=0.16)
TRACK = dict(z=(3.24, 3.30), y1=-1.10, w=0.06)
NOTCH = {S.SIDE['name']: (0.03, 0.0)}   # the concrete cut back outside the hinge jamb
PX, NX, PY, NY, PZ = (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)
EXT, HALL = 'Garage', 'Garage__in'


def ext():
    return kb(EXT, 'GarExt')


def hall():
    return kb(HALL, 'GarIn')


def glass():
    return kb('Garage_Glass', 'glass')


def lens(kind):
    return kb('Garage__' + kind, 'lens:' + kind + 'off')


def P3(axis, a, u, z):
    return Vector((a, u, z)) if axis == 'x' else Vector((u, a, z))


def wbox(k, axis, a0, a1, u0, u1, z0, z1, zone, skip=()):
    MO.wbox(k, axis, a0, a1, u0, u1, z0, z1, zone, skip=skip)


# ---------------------------------------------------------------- the walls and their openings
def walls():
    """(key, axis, a_out (crest plane), out_sign, a_in (liner), a_plinth, u0, u1)"""
    return [('S', 'y', -YO, -1, -YI, -PLY, -XO, XO), ('N', 'y', YO, 1, YI, PLY, -XO, XO),
            ('E', 'x', XO, 1, XI, PLX, -YO, YO), ('W', 'x', -XO, -1, -XI, -PLX, -YO, YO)]


def openings(key):
    """the openings through wall `key`: (u0, u1, z0, z1, kind, name)"""
    out = []
    g, d = S.GATE, S.SIDE
    if key == g['wall']:
        out.append((g['u'][0], g['u'][1], 0.0, GATE_HEAD, 'gate', g['name']))
    if key == d['wall']:
        out.append((d['u'][0], d['u'][1], 0.0, d['z'][1], 'door', d['name']))
    for w in S.WINDOWS:
        if w['wall'] == key:
            out.append((w['u'][0], w['u'][1], w['z'][0], w['z'][1], 'window', w['name']))
    return out


def plinth_and_skin():
    """the concrete plinth / upstand (outer face to the sheets' foot), the drip flashing over it, the trapezoidal sheet
    (outer face, vertical ribs) round the openings, the corner trims"""
    k = ext()
    c = CORR
    for key, ax, a_out, sg, a_in, a_pl, u0, u1 in walls():
        ops = openings(key)
        # the concrete is cut where an opening reaches the floor; at the side door's hinge side 3 cm wider outside the
        # sheet's plane (the leaf opens out to 100 degrees and its edge passes there)
        low = []
        for o in ops:
            if o[2] < UPSTAND:
                e0, e1 = NOTCH.get(o[5], (0.0, 0.0))
                low.append((o[0] - e0, o[1] + e1, 0.0, UPSTAND, o[4], o[0], o[1]))
        # plinth's outer face (reaches past the corners to the other walls' plinth faces)
        pu0, pu1 = (-PLX, PLX) if ax == 'y' else (-PLY, PLY)
        flat_wall(k, ax, a_pl, sg, pu0, pu1, S.PLINTH_BOT, UPSTAND, lambda z: Z_PLINTH, holes=[o[:4] for o in low],
                  step=1.5, zcuts=[S.FLOOR])
        # its top (from the sheet's valleys to the plinth face) and the drip flashing over it
        a_v = a_out - sg * c['depth']
        # the S / N strips run over the plinth's corners, the E / W ones stop at the S / N valleys
        span = (-PLX, PLX) if ax == 'y' else (-(YO - c['depth']), YO - c['depth'])
        for su0, su1 in _subtract(span, [(o[0], o[1]) for o in low]):
            face(k, [P3(ax, a_v, su0, UPSTAND), P3(ax, a_pl, su0, UPSTAND), P3(ax, a_pl, su1, UPSTAND),
                     P3(ax, a_v, su1, UPSTAND)], Z_PLINTH, (0, 0, 1))
            e0 = su0 - (0.016 if ax == 'y' and su0 <= -PLX + 1e-6 else 0.0)
            e1 = su1 + (0.016 if ax == 'y' and su1 >= PLX - 1e-6 else 0.0)
            drip(k, ax, a_v, a_pl, sg, e0, e1)
        # the concrete's cut faces in the low openings, from the plinth face to the frame / the sheet's plane
        for o in low:
            a_stop = LIP[0] if o[4] == 'gate' else a_out
            for uu, s_ in ((o[0], 1), (o[1], -1)):
                ua = Vector((0, s_, 0)) if ax == 'x' else Vector((s_, 0, 0))
                face(k, [P3(ax, a_pl, uu, 0.0), P3(ax, a_stop, uu, 0.0), P3(ax, a_stop, uu, UPSTAND),
                         P3(ax, a_pl, uu, UPSTAND)], Z_PLINTH, ua)
            for (na, nb) in ((o[0], o[5]), (o[6], o[1])):              # a notch: its back face and the top under the sheet
                if nb - na < 1e-4:
                    continue
                nrm = Vector((sg, 0, 0)) if ax == 'x' else Vector((0, sg, 0))
                face(k, [P3(ax, a_out, na, 0.0), P3(ax, a_out, nb, 0.0), P3(ax, a_out, nb, UPSTAND),
                         P3(ax, a_out, na, UPSTAND)], Z_PLINTH, nrm)
                face(k, [P3(ax, a_v, na, UPSTAND), P3(ax, a_out, na, UPSTAND), P3(ax, a_out, nb, UPSTAND),
                         P3(ax, a_v, nb, UPSTAND)], Z_PLINTH, (0, 0, 1))
                face(k, [P3(ax, a_out, na, 0.0), P3(ax, a_pl, na, 0.0), P3(ax, a_pl, nb, 0.0), P3(ax, a_out, nb, 0.0)],
                     Z_PLINTH, (0, 0, 1))
        # the sheet
        corrugated(k, ax, a_out, sg, c['depth'], u0, u1, UPSTAND, S.EAVES, c['pitch'], c['crest'], c['slope'], Z_SKIN,
                   along='u', phase=u0, holes=[(o[0], o[1], o[2], o[3]) for o in ops], step=1.5)
    # corner trims: an angle over each corner, 12 cm legs, 1.2 cm proud of the crests
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, ya = sx * XO, sy * YO
            box6(k, (xa - sx * 0.12, ya, UPSTAND - 0.01), (xa + sx * 0.012, ya + sy * 0.012, S.EAVES), Z_TRIM,
                 skip=('-z',))
            box6(k, (xa, ya - sy * 0.12, UPSTAND - 0.01), (xa + sx * 0.012, ya, S.EAVES), Z_TRIM, skip=('-z',))


def drip(k, ax, a_v, a_pl, sg, u0, u1):
    """the drip flashing on the upstand: from behind the sheet's valleys sloping out past the plinth face, a lip down"""
    z0 = UPSTAND
    a0, a1 = a_v - sg * 0.002, a_pl + sg * 0.016
    top0, top1 = z0 + 0.034, z0 + 0.010
    face(k, [P3(ax, a0, u0, top0), P3(ax, a1, u0, top1), P3(ax, a1, u1, top1), P3(ax, a0, u1, top0)], Z_TRIM, (0, 0, 1))
    nrm = Vector((sg, 0, 0)) if ax == 'x' else Vector((0, sg, 0))
    face(k, [P3(ax, a1, u0, top1), P3(ax, a1, u0, z0 - 0.018), P3(ax, a1, u1, z0 - 0.018), P3(ax, a1, u1, top1)], Z_TRIM,
         nrm)
    face(k, [P3(ax, a1 - sg * 0.004, u0, z0 - 0.018), P3(ax, a1, u0, z0 - 0.018), P3(ax, a1, u1, z0 - 0.018),
             P3(ax, a1 - sg * 0.004, u1, z0 - 0.018)], Z_TRIM, (0, 0, -1))
    face(k, [P3(ax, a1 - sg * 0.004, u0, z0 - 0.018), P3(ax, a1 - sg * 0.004, u0, z0 + 0.004),
             P3(ax, a1 - sg * 0.004, u1, z0 + 0.004), P3(ax, a1 - sg * 0.004, u1, z0 - 0.018)], Z_TRIM, -nrm)
    face(k, [P3(ax, a1 - sg * 0.004, u0, z0 + 0.004), P3(ax, a_pl, u0, z0 + 0.004), P3(ax, a_pl, u1, z0 + 0.004),
             P3(ax, a1 - sg * 0.004, u1, z0 + 0.004)], Z_TRIM, (0, 0, -1))
    for uu, s_ in ((u0, -1), (u1, 1)):                                # the ends
        ua = Vector((0, s_, 0)) if ax == 'x' else Vector((s_, 0, 0))
        face(k, [P3(ax, a0, uu, top0), P3(ax, a1, uu, top1), P3(ax, a1, uu, z0 - 0.018), P3(ax, a_pl, uu, z0 + 0.004),
                 P3(ax, a0, uu, z0)], Z_TRIM, ua)


def opening_trims():
    """the outer flashings round the windows (head with a drip, jambs, the galvanised sill) and the side door; the
    gate's outer stops are its frame (gate_frame)"""
    k = ext()
    for key, ax, a_out, sg, a_in, a_pl, u0, u1 in walls():
        for (ou0, ou1, oz0, oz1, kind, name) in openings(key):
            if kind == 'gate':
                continue
            a1 = a_out + sg * 0.012
            w = 0.07
            if kind == 'window':
                wbox(k, ax, a_out, a1, ou0 - w, ou0, oz0 - 0.03, oz1, Z_TRIM)
                wbox(k, ax, a_out, a1, ou1, ou1 + w, oz0 - 0.03, oz1, Z_TRIM)
                wbox(k, ax, a_out, a1 + sg * 0.01, ou0 - w - 0.02, ou1 + w + 0.02, oz1, oz1 + 0.07, Z_TRIM)
                # the head's drip: a small slope out over the frame
                face(k, [P3(ax, a1 + sg * 0.01, ou0 - w - 0.02, oz1), P3(ax, a_out - sg * 0.01, ou0 - w - 0.02, oz1),
                         P3(ax, a_out - sg * 0.01, ou1 + w + 0.02, oz1), P3(ax, a1 + sg * 0.01, ou1 + w + 0.02, oz1)],
                     Z_TRIM, (0, 0, -1))
            else:
                # the side door: the lock side and the head; the hinge side stops 13 mm short of the jamb (the leaf opens
                # out to 100 degrees and passes the corner there)
                hinge_u = S.SIDE['pivot'][1] if ax == 'x' else S.SIDE['pivot'][0]
                lo_side = abs(hinge_u - ou0) < abs(hinge_u - ou1)
                hu0, hu1 = (ou0 - w - 0.01, ou0 - 0.013) if lo_side else (ou1 + 0.013, ou1 + w + 0.01)
                lu0, lu1 = (ou1, ou1 + w) if lo_side else (ou0 - w, ou0)
                wbox(k, ax, a_out, a1, hu0, hu1, UPSTAND - 0.01, oz1, Z_TRIM)
                wbox(k, ax, a_out, a1, lu0, lu1, UPSTAND - 0.01, oz1, Z_TRIM)
                wbox(k, ax, a_out, a1 + sg * 0.01, ou0 - w - 0.01, ou1 + w + 0.01, oz1, oz1 + 0.08, Z_TRIM)


# ---------------------------------------------------------------- the roof
def roof():
    """felt on the roof (inside a 3 cm kerb of the edge profile), the edge profile (fascia, cap, drip lip), the soffit
    under the overhang, the scuppers at the back with their hoppers and downpipes, splash blocks"""
    k = ext()
    xi, yi = EDGE_X - KERB, EDGE_Y - KERB
    flat_h(k, S.ROOF_T, 1, -xi, xi, -yi, yi, Z_FELT, step=1.5)
    for (axis, a, sg, u0, u1) in (('x', xi, -1, -yi, yi), ('x', -xi, 1, -yi, yi), ('y', yi, -1, -xi, xi),
                                  ('y', -yi, 1, -xi, xi)):
        flat_wall(k, axis, a, sg, u0, u1, S.ROOF_T, FASCIA_TOP, lambda z: Z_FASCIA, step=3.0)       # the kerb's inside
    # the cap (top of the profile) and the fascia
    ring = [(-EDGE_X, -EDGE_Y), (EDGE_X, -EDGE_Y), (EDGE_X, EDGE_Y), (-EDGE_X, EDGE_Y)]
    inner = [(-xi, -yi), (xi, -yi), (xi, yi), (-xi, yi)]
    for i in range(4):
        j = (i + 1) % 4
        face(k, [(*ring[i], FASCIA_TOP), (*ring[j], FASCIA_TOP), (*inner[j], FASCIA_TOP), (*inner[i], FASCIA_TOP)],
             Z_FASCIA, (0, 0, 1))
    for (axis, a, sg, u0, u1) in (('x', EDGE_X, 1, -EDGE_Y, EDGE_Y), ('x', -EDGE_X, -1, -EDGE_Y, EDGE_Y),
                                  ('y', EDGE_Y, 1, -EDGE_X, EDGE_X), ('y', -EDGE_Y, -1, -EDGE_X, EDGE_X)):
        flat_wall(k, axis, a, sg, u0, u1, FASCIA_BOT, FASCIA_TOP, lambda z: Z_FASCIA, step=1.5)
    # the drip lip (the profile's bottom, 1.5 cm in) and its inner face down from the soffit
    lx, ly = EDGE_X - 0.015, EDGE_Y - 0.015
    ring2 = [(-lx, -ly), (lx, -ly), (lx, ly), (-lx, ly)]
    for i in range(4):
        j = (i + 1) % 4
        face(k, [(*ring[i], FASCIA_BOT), (*ring[j], FASCIA_BOT), (*ring2[j], FASCIA_BOT), (*ring2[i], FASCIA_BOT)],
             Z_FASCIA, (0, 0, -1))
    for (axis, a, sg, u0, u1) in (('x', lx, -1, -ly, ly), ('x', -lx, 1, -ly, ly), ('y', ly, -1, -lx, lx),
                                  ('y', -ly, 1, -lx, lx)):
        flat_wall(k, axis, a, sg, u0, u1, FASCIA_BOT, S.EAVES, lambda z: Z_FASCIA, step=3.0)
    # the soffit: from the sheets' valley plane out to the lip
    vx, vy = XO - CORR['depth'], YO - CORR['depth']
    sv = [(-vx, -vy), (vx, -vy), (vx, vy), (-vx, vy)]
    for i in range(4):
        j = (i + 1) % 4
        face(k, [(*ring2[i], S.EAVES), (*ring2[j], S.EAVES), (*sv[j], S.EAVES), (*sv[i], S.EAVES)], Z_SOFFIT, (0, 0, -1))
    # scuppers through the north edge, hoppers, downpipes with offsets to the wall, clips, shoes, splash blocks
    for x in SCUPPERS_X:
        box6(k, (x - 0.05, EDGE_Y - 0.01, S.ROOF_T - 0.035), (x + 0.05, EDGE_Y + 0.16, S.ROOF_T - 0.005), Z_GALV,
             skip=('-y',))
        hy = EDGE_Y + 0.10
        k.lathe(Vector((x, hy, S.ROOF_T - 0.30)), Vector((0, 0, 1)), [(0.0, 0.055), (0.12, 0.10), (0.20, 0.10)], Z_GALV, 12,
                cap0=True, cap1=False)
        p = [Vector((x, hy, S.ROOF_T - 0.30)), Vector((x, hy, 4.12)), Vector((x, PIPE_Y, 3.86)),
             Vector((x, PIPE_Y, 0.30)), Vector((x, YO + 0.21, 0.10))]
        k.tube(p, 0.05, Z_GALV, 10)
        for zc in (3.40, 2.10, 0.80):
            k.lathe(Vector((x, PIPE_Y, zc - 0.02)), Vector((0, 0, 1)), [(0.0, 0.056), (0.04, 0.056)], Z_GALV, 10,
                    cap0=False, cap1=False)
            box6(k, (x - 0.012, YO, zc - 0.02), (x + 0.012, PIPE_Y - 0.05, zc + 0.02), Z_GALV)
        box6(k, (x - 0.16, YO + 0.12, S.GROUND - 0.02), (x + 0.16, YO + 0.62, S.GROUND + 0.05), Z_APRON, skip=('-z',))


# ---------------------------------------------------------------- outside the gate and the side door
def apron():
    """the concrete apron in front of the gate (falls 6 cm away from the threshold) and the step at the side door"""
    k = ext()
    x0, x1 = S.GATE['u'][0] - 0.60, S.GATE['u'][1] + 0.60
    ya, yb = -0.0 - 4.40, -6.30
    za, zb, zbot = S.FLOOR, S.FLOOR - 0.06, S.GROUND - 0.08
    xs = _grid({x0, x1, S.GATE['u'][0], S.GATE['u'][1]}, 1.5)
    ys = [ya, -PLY, -5.40, yb]
    zf = lambda y: za + (zb - za) * (ya - y) / (ya - yb)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if ys[j] > -PLY + 1e-6 and not (S.GATE['u'][0] - 1e-6 <= xs[i] and xs[i + 1] <= S.GATE['u'][1] + 1e-6):
                continue                                                  # inside the wall line: only the threshold
            face(k, [(xs[i], ys[j], zf(ys[j])), (xs[i + 1], ys[j], zf(ys[j])), (xs[i + 1], ys[j + 1], zf(ys[j + 1])),
                     (xs[i], ys[j + 1], zf(ys[j + 1]))], Z_APRON, (0, 0, 1))
    face(k, [(x0, yb, zbot), (x1, yb, zbot), (x1, yb, zf(yb)), (x0, yb, zf(yb))], Z_APRON, (0, -1, 0))
    for x, s_ in ((x0, -1), (x1, 1)):
        face(k, [(x, -PLY, zbot), (x, yb, zbot), (x, yb, zf(yb)), (x, -PLY, zf(-PLY))], Z_APRON, (s_, 0, 0))
    # the side door: the threshold strip outside the leaf and the step (2 cm under the threshold)
    d = S.SIDE
    y0, y1 = d['u']
    face(k, [(5.95, y0, S.FLOOR), (PLX, y0, S.FLOOR), (PLX, y1, S.FLOOR), (5.95, y1, S.FLOOR)], Z_APRON, (0, 0, 1))
    box6(k, (PLX, y0 - 0.20, S.GROUND - 0.08), (PLX + 0.62, y1 + 0.20, S.FLOOR - 0.02), Z_APRON, skip=('-z', '-x'))


# ---------------------------------------------------------------- inside: floor, liner, deck, beams
def hall_shell():
    k = hall()
    # floor (and the thresholds under the leaves), the drain
    dx, dy, ds = DRAIN
    xs = _grid({-XI, XI, dx - ds / 2, dx + ds / 2, S.GATE['u'][0], S.GATE['u'][1]}, 1.0)
    ys = _grid({-YI, YI, dy - ds / 2, dy + ds / 2}, 1.0)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            xm, ym = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if abs(xm - dx) < ds / 2 and abs(ym - dy) < ds / 2:
                continue
            face(k, [(xs[i], ys[j], 0), (xs[i + 1], ys[j], 0), (xs[i + 1], ys[j + 1], 0), (xs[i], ys[j + 1], 0)], Z_FLOOR,
                 (0, 0, 1))
    g = S.GATE
    face(k, [(g['u'][0], -4.40, 0), (g['u'][1], -4.40, 0), (g['u'][1], -YI, 0), (g['u'][0], -YI, 0)], Z_FLOOR, (0, 0, 1))
    d = S.SIDE
    face(k, [(XI, d['u'][0], 0), (5.95, d['u'][0], 0), (5.95, d['u'][1], 0), (XI, d['u'][1], 0)], Z_FLOOR, (0, 0, 1))
    # the drain: a 3 cm recess, the grating 8 mm down, its frame
    x0, x1, y0, y1 = dx - ds / 2, dx + ds / 2, dy - ds / 2, dy + ds / 2
    for (pa, pb, n) in (((x0, y0), (x1, y0), (0, 1, 0)), ((x1, y0), (x1, y1), (-1, 0, 0)), ((x1, y1), (x0, y1), (0, -1, 0)),
                        ((x0, y1), (x0, y0), (1, 0, 0))):
        face(k, [(pa[0], pa[1], 0), (pb[0], pb[1], 0), (pb[0], pb[1], -0.03), (pa[0], pa[1], -0.03)], Z_GALV, n)
    face(k, [(x0, y0, -0.03), (x1, y0, -0.03), (x1, y1, -0.03), (x0, y1, -0.03)], Z_STEELBLK, (0, 0, 1))
    box6(k, (x0 + 0.01, y0 + 0.01, -0.012), (x1 - 0.01, y1 - 0.01, -0.008), F.Z_GRATING, skip=('-z',))
    # walls: the concrete upstand's inner face, the liner trays above
    for key, ax, a_out, sg, a_in, a_pl, u0, u1 in walls():
        ui0, ui1 = (-XI, XI) if ax == 'y' else (-YI, YI)
        ops = openings(key)
        low = [(o[0], o[1], 0.0, UPSTAND) for o in ops if o[2] < UPSTAND]
        flat_wall(k, ax, a_in, -sg, ui0, ui1, 0.0, UPSTAND, lambda z: Z_PLINTH, holes=low, step=1.0)
        flat_wall(k, ax, a_in, -sg, ui0, ui1, UPSTAND, LINER_TOP, lambda z: Z_LINER,
                  holes=[(o[0], o[1], o[2], o[3]) for o in ops], step=1.0, zcuts=[DECK_Z])
        # the liner's base angle on the upstand (galvanised, 3 cm)
        for su0, su1 in _subtract((ui0, ui1), [(o[0], o[1]) for o in low]):
            wbox(k, ax, a_in, a_in - sg * 0.03, su0, su1, UPSTAND - 0.003, UPSTAND + 0.004, Z_GALV, skip=())
    # the deck (narrow flanges down) and the beams
    corr_h(k, DECK_Z, DECK['depth'], -XI, XI, -YI, YI, DECK['pitch'], DECK['crest'], DECK['slope'], Z_DECK, phase=-YI)
    for x in BEAMS_X:
        b, h, tf, tw = BEAM['b'], BEAM['h'], BEAM['tf'], BEAM['tw']
        zt = DECK_Z
        box6(k, (x - b / 2, -YI, zt - tf), (x + b / 2, YI, zt), Z_BEAM, skip=('+z', '-y', '+y'))
        box6(k, (x - tw / 2, -YI, zt - h + tf), (x + tw / 2, YI, zt - tf), Z_BEAM, skip=('-y', '+y', '+z', '-z'))
        box6(k, (x - b / 2, -YI, zt - h), (x + b / 2, YI, zt - h + tf), Z_BEAM, skip=('-y', '+y'))
        for y in (-YI, YI):                                          # the end plates at the walls (bolted to the columns)
            s_ = 1 if y < 0 else -1
            box6(k, (x - 0.09, y, zt - h - 0.02), (x + 0.09, y + s_ * 0.012, zt), Z_BEAM, skip=('-y' if s_ > 0 else '+y',))


def corr_h(k, z_low, depth, x0, x1, y0, y1, pitch, crest, slope, zone, phase=0.0, xstep=1.5):
    """a trapezoidal deck seen from below: profile across y (ribs along x), its bottom flanges at z_low"""
    prof = corr_profile(y0, y1, pitch, crest, slope, phase)
    xs = [a for a, b in _split(x0, x1, xstep)] + [x1]
    for (ya, da), (yb, db) in zip(prof[:-1], prof[1:]):
        za, zb = z_low + da * depth, z_low + db * depth
        for xa, xb in zip(xs[:-1], xs[1:]):
            face(k, [(xa, ya, za), (xb, ya, za), (xb, yb, zb), (xa, yb, zb)], zone, (0, 0, -1))


# ---------------------------------------------------------------- the gate
def gate_frame():
    """the steel frame of the gate: the linings of the reveal, the outer stops in front of the leaf's edges, the inner
    architraves on the liner, the pivot bearings, the tracks under the ceiling on their hangers, the balance springs"""
    g = S.GATE
    u0, u1 = g['u']
    k = ext()
    kh = hall()
    yo, yi = -YO, -YI
    # linings (the reveal) behind the outer stops
    face(k, [(u0, LIP[1], 0), (u0, yi, 0), (u0, yi, GATE_HEAD), (u0, LIP[1], GATE_HEAD)], Z_FRAME, (1, 0, 0))
    face(k, [(u1, LIP[1], 0), (u1, yi, 0), (u1, yi, GATE_HEAD), (u1, LIP[1], GATE_HEAD)], Z_FRAME, (-1, 0, 0))
    face(k, [(u0, LIP[1], GATE_HEAD), (u1, LIP[1], GATE_HEAD), (u1, yi, GATE_HEAD), (u0, yi, GATE_HEAD)], Z_FRAME, (0, 0, -1))
    # outer stops: the jambs to the ground line of the floor, the head between them
    box6(k, (u0 - 0.08, LIP[0], 0.0), (u0 + 0.03, LIP[1], 3.32), Z_FRAME)
    box6(k, (u1 - 0.03, LIP[0], 0.0), (u1 + 0.08, LIP[1], 3.32), Z_FRAME)
    box6(k, (u0 + 0.03, LIP[0], 3.165), (u1 - 0.03, LIP[1], 3.32), Z_FRAME, skip=('-x', '+x'))
    # the sheet's cut edge beside the frame: a flashing strip on the face, to the stops
    for (a, b) in ((u0 - 0.15, u0 - 0.08), (u1 + 0.08, u1 + 0.15)):
        box6(k, (a, yo - 0.012, UPSTAND - 0.01), (b, yo, 3.32), Z_TRIM, skip=('-z',))
    box6(k, (u0 - 0.15, yo - 0.012, 3.32), (u1 + 0.15, yo, 3.40), Z_TRIM)
    # the pivot bearings on the jambs
    py, pz = g['pivot'][1], g['pivot'][2]
    for x, s_ in ((u0, 1), (u1, -1)):
        box6(k, (x, py - 0.035, pz - 0.05), (x + s_ * 0.016, py + 0.035, GATE_HEAD - 0.004), Z_FRAME,
             skip=('-x' if s_ > 0 else '+x',))
        k.cyl(Vector((x, py, pz)), Vector((x + s_ * 0.022, py, pz)), 0.010, Z_GALV, 8)
    # inside: architraves on the liner round the opening
    for (a, b) in ((u0 - 0.06, u0), (u1, u1 + 0.06)):
        box6(kh, (a, yi, 0.0), (b, yi + 0.012, GATE_HEAD), Z_FRAME, skip=('-y', '-z'))
    box6(kh, (u0 - 0.06, yi, GATE_HEAD), (u1 + 0.06, yi + 0.012, GATE_HEAD + 0.06), Z_FRAME, skip=('-y',))
    # tracks (outside the leaf's width, over its open position), hangers to the deck, end stops
    z0, z1 = TRACK['z']
    w = TRACK['w']
    for xa, xb in ((u0 - 0.10 - w, u0 - 0.10), (u1 + 0.10, u1 + 0.10 + w)):
        box6(kh, (xa, yi + 0.012, z1 - 0.006), (xb, TRACK['y1'], z1), MO.Z_TRACK)
        box6(kh, (xa, yi + 0.012, z0), (xb, TRACK['y1'], z0 + 0.006), MO.Z_TRACK)
        xo_ = xa if xa < u0 else xb
        box6(kh, (xo_ - 0.003, yi + 0.012, z0), (xo_ + 0.003, TRACK['y1'], z1), MO.Z_TRACK)
        box6(kh, (xa, TRACK['y1'] - 0.03, z0 + 0.006), (xb, TRACK['y1'], z1 - 0.006), Z_STEELBLK)
        for yh in (TRACK['y1'] - 0.08, -2.75):
            xm = (xa + xb) / 2
            box6(kh, (xm - 0.02, yh - 0.0025, z1), (xm + 0.02, yh + 0.0025, DECK_Z), Z_GALV)
        # the balance spring beside the jamb and its anchor brackets
        xs_ = (xa + xb) / 2
        ys_ = yi + 0.05
        kh.cyl(Vector((xs_, ys_, 0.42)), Vector((xs_, ys_, 2.30)), 0.022, Z_STEELBLK, 10)
        kh.cyl(Vector((xs_, ys_, 2.30)), Vector((xs_, ys_, 2.86)), 0.005, Z_GALV, 6)
        kh.cyl(Vector((xs_, ys_, 0.42)), Vector((xs_, ys_, 0.20)), 0.005, Z_GALV, 6)
        for zb_ in (0.16, 2.86):
            box6(kh, (xs_ - 0.03, yi + 0.012, zb_ - 0.03), (xs_ + 0.03, ys_ + 0.02, zb_ + 0.04), Z_FRAME, skip=('-y',))


def gate_leaf():
    """IX_GarageDoor_92: ribbed outer sheet (horizontal ribs), a tube frame behind it (perimeter, two posts, a rail),
    the bottom seal, the T-handle with its lock outside, the grip inside and the lock rods to the jambs, the pivot plates
    at the top corners; the AUSFAHRT FREIHALTEN plate"""
    g = S.GATE
    name = g['name']
    k = kb(name, 'GarParts')
    (x0, ya, z0), (x1, yb, z1) = g['leaf_lo'], g['leaf_hi']        # -3.28..0.28, -4.48..-4.375, 0.02..3.18
    ys = ya + 0.010                                                   # the sheet's back
    corrugated(k, 'y', ya, -1, 0.006, x0, x1, z0, z1, 0.1975, 0.05, 0.008, Z_GATE, along='z', phase=z0, step=1.2)
    face(k, [(x0, ys, z0), (x1, ys, z0), (x1, ys, z1), (x0, ys, z1)], Z_GATEIN, (0, 1, 0))
    for (xa, za, zb) in ((x0, z0, z1), (x1, z0, z1)):
        face(k, [(xa, ya, za), (xa, ys, za), (xa, ys, zb), (xa, ya, zb)], Z_GATE, (1 if xa > 0 else -1, 0, 0))
    face(k, [(x0, ya, z1), (x1, ya, z1), (x1, ys, z1), (x0, ys, z1)], Z_GATE, (0, 0, 1))
    face(k, [(x0, ya, z0), (x1, ya, z0), (x1, ys, z0), (x0, ys, z0)], Z_GATE, (0, 0, -1))
    # the frame: perimeter tubes 40 mm on the face, 70 deep; two posts and a mid rail 50 deep
    fb = ys + 0.070
    box6(k, (x0, ys, z0), (x0 + 0.04, fb, z1), Z_GATEIN, skip=('-y',))
    box6(k, (x1 - 0.04, ys, z0), (x1, fb, z1), Z_GATEIN, skip=('-y',))
    box6(k, (x0 + 0.04, ys, z1 - 0.04), (x1 - 0.04, fb, z1), Z_GATEIN, skip=('-y', '-x', '+x'))
    box6(k, (x0 + 0.04, ys, z0), (x1 - 0.04, fb, z0 + 0.04), Z_GATEIN, skip=('-y', '-x', '+x'))
    xp = [x0 + (x1 - x0) / 3, x0 + 2 * (x1 - x0) / 3]
    for x in xp:
        box6(k, (x - 0.02, ys, z0 + 0.04), (x + 0.02, ys + 0.05, z1 - 0.04), Z_GATEIN, skip=('-y', '-z', '+z'))
    zr = (z0 + z1) / 2
    for (a, b) in ((x0 + 0.04, xp[0] - 0.02), (xp[0] + 0.02, xp[1] - 0.02), (xp[1] + 0.02, x1 - 0.04)):
        box6(k, (a, ys, zr - 0.02), (b, ys + 0.05, zr + 0.02), Z_GATEIN, skip=('-y', '-x', '+x'))
    # the bottom seal
    box6(k, (x0, ya, 0.004), (x1, ya + 0.035, z0), MO.Z_RUBBER, skip=('+z',))
    # pivot plates at the top corners (to the Update 3 box), the pin stubs on the axis
    piv = Vector(g['pivot'])
    for xa, xb, s_ in ((x0, x0 + 0.025, -1), (x1 - 0.025, x1, 1)):
        box6(k, (xa, fb, z1 - 0.13), (xb, yb, z1), Z_GATEIN, skip=('-y',))
        k.cyl(Vector((xb if s_ > 0 else xa, piv.y, piv.z)), Vector(((xb if s_ > 0 else xa) + s_ * 0.004, piv.y, piv.z)),
              0.014, Z_GALV, 8)
    # the T-handle outside (rose, stem, grip), the lock cylinder under it; inside the grip box and the lock rods
    hx, hz = (x0 + x1) / 2, z0 + 1.03
    yf = ya - 0.006                                                   # in front of the ribs' crests
    k.cyl(Vector((hx, yf + 0.006, hz)), Vector((hx, yf - 0.006, hz)), 0.032, MO.Z_HANDLE, 12)
    k.cyl(Vector((hx, yf - 0.006, hz)), Vector((hx, yf - 0.045, hz)), 0.009, MO.Z_HANDLE, 8)
    VM.rbox(k, Vector((hx, yf - 0.052, hz)), (0.16, 0.022, 0.026), MO.Z_HANDLE, r=0.008, ch=0.004, axis='x')
    k.cyl(Vector((hx, yf + 0.006, hz - 0.075)), Vector((hx, yf - 0.004, hz - 0.075)), 0.013, MO.Z_LOCK, 10)
    box6(k, (hx - 0.06, ys, hz - 0.11), (hx + 0.06, ys + 0.045, hz + 0.09), Z_GATEIN, skip=('-y',))
    k.cyl(Vector((hx, ys + 0.045, hz)), Vector((hx, ys + 0.075, hz)), 0.009, MO.Z_HANDLE, 8)
    VM.rbox(k, Vector((hx, ys + 0.082, hz)), (0.12, 0.016, 0.024), MO.Z_HANDLE, r=0.006, ch=0.003, axis='x')
    yr = ys + 0.052
    for xa, xb in ((x0 + 0.05, hx - 0.06), (hx + 0.06, x1 - 0.05)):
        k.cyl(Vector((xa, yr, hz)), Vector((xb, yr, hz)), 0.007, Z_GALV, 6)
        for xg in xp + [x0 + 0.06, x1 - 0.06]:
            if xa + 0.02 < xg < xb - 0.02:
                box6(k, (xg - 0.015, ys + 0.045, hz - 0.015), (xg + 0.015, yr + 0.012, hz + 0.015), Z_GALV, skip=('-y',))
    # the sign: a backing plate in front of the ribs, the panel quad on it
    sw, sh = 0.42, 0.18
    sz = z0 + 1.62
    box6(k, (hx - sw / 2 - 0.006, yf - 0.008, sz - sh / 2 - 0.006), (hx + sw / 2 + 0.006, yf, sz + sh / 2 + 0.006),
         Z_GATE, skip=('+y',))
    kp = kb(name + '_Panel', 'panel')
    kp.quad_uv(Vector((hx, yf - 0.008 - 0.0015, sz)), Vector((0, -1, 0)), sw, sh, T.uv('ausfahrt'), 0, up=Vector((0, 0, 1)))
    part(name + '_Panel', 'static', g['pivot'], parent=name, note='the leaf\'s sign (panel atlas); joined at export')
    part(name, 'hinge', g['pivot'], axis=MO.unity_axis_to_blender(g['axis_u'], 'hinge'), rng=g['range'], parent=EXT,
         states=['closed', 'open'], lock_key=S.LOCK_KEY,
         note='up-and-over gate: the leaf swings up and in about its top edge to lie under the tracks (85 deg); locked, '
              'key Garage (Forest_Opening.json)')


# ---------------------------------------------------------------- the side door
def side_door():
    """IX_GarageSideDoor_93 (steel leaf, opens out to 100 deg about the south jamb) and its steel frame: the reveal
    lined, the stop strips inside behind the leaf's edges, architraves on the liner, three hinges outside on the axis"""
    d = S.SIDE
    name = d['name']
    u0, u1 = d['u']                         # y 1.025 .. 1.975
    zt = d['z'][1]                          # 2.10
    k = ext()
    kh = hall()
    a_in, a_out = XI, XO
    piv = Vector(d['pivot'])
    # the frame's linings in the reveal (liner face to the crests)
    face(k, [(a_in, u0, 0), (a_out, u0, 0), (a_out, u0, zt), (a_in, u0, zt)], Z_FRAME, (0, 1, 0))
    face(k, [(a_in, u1, 0), (a_out, u1, 0), (a_out, u1, zt), (a_in, u1, zt)], Z_FRAME, (0, -1, 0))
    face(k, [(a_in, u0, zt), (a_out, u0, zt), (a_out, u1, zt), (a_in, u1, zt)], Z_FRAME, (0, 0, -1))
    # stops behind the leaf (inside: the leaf closes against them from outside)
    sa, sb = 5.888, d['leaf_lo'][0] - 0.002
    box6(k, (sa, u0, 0.0), (sb, u0 + 0.045, zt - 0.03), Z_FRAME, skip=('-y', '+z'))
    box6(k, (sa, u1 - 0.025, 0.0), (sb, u1, zt - 0.03), Z_FRAME, skip=('+y', '+z'))
    box6(k, (sa, u0, zt - 0.03), (sb, u1, zt), Z_FRAME, skip=('+z',))
    # architraves inside
    for (a, b) in ((u0 - 0.05, u0), (u1, u1 + 0.05)):
        box6(kh, (a_in - 0.012, a, 0.0), (a_in, b, zt), Z_FRAME, skip=('+x', '-z'))
    box6(kh, (a_in - 0.012, u0 - 0.05, zt), (a_in, u1 + 0.05, zt + 0.05), Z_FRAME, skip=('+x',))
    # three hinges outside, on the axis
    for zc in (0.25, 1.05, 1.85):
        k.cyl(Vector((piv.x, piv.y, zc - 0.07)), Vector((piv.x, piv.y, zc + 0.07)), 0.011, MO.Z_HINGE, 8)
    # the leaf
    kl = kb(name, 'GarParts')
    (lx0, ly0, lz0), (lx1, ly1, lz1) = d['leaf_lo'], d['leaf_hi']   # 5.916..5.99, 1.055..1.965, 0.01..2.09
    box6(kl, (lx0, ly0 + 0.002, lz0), (lx1, ly1, lz1), {'*': Z_LEAF})
    # handle side: levers both sides, escutcheons, the cylinder outside; the closer's body inside at the top
    hu, hz = ly1 - 0.07, 1.05
    for sg, aa in ((1, lx1), (-1, lx0)):
        box6(kl, (min(aa, aa + sg * 0.008), hu - 0.025, hz - 0.12), (max(aa, aa + sg * 0.008), hu + 0.025, hz + 0.08),
             MO.Z_HANDLE)
        c = Vector((aa + sg * 0.05, hu, hz))
        kl.cyl(Vector((aa, hu, hz)), c, 0.009, MO.Z_HANDLE, 8)
        kl.cyl(c, Vector((aa + sg * 0.05, hu - 0.12, hz)), 0.010, MO.Z_HANDLE, 8)
    kl.cyl(Vector((lx1, hu, hz - 0.075)), Vector((lx1 + 0.006, hu, hz - 0.075)), 0.012, MO.Z_LOCK, 10)
    box6(kl, (lx0 - 0.05, ly0 + 0.16, lz1 - 0.10), (lx0, ly0 + 0.44, lz1 - 0.03), MO.Z_CLOSER, skip=('+x',))
    kp = kb(name + '_Panel', 'panel')
    kp.quad_uv(Vector((lx1 + 0.0015, (ly0 + ly1) / 2, 1.55)), Vector((1, 0, 0)), 0.48, 0.088, T.uv('befugt'), 0,
               up=Vector((0, 0, 1)))
    part(name + '_Panel', 'static', d['pivot'], parent=name, note='the leaf\'s sign (panel atlas); joined at export')
    part(name, 'hinge', d['pivot'], axis=MO.unity_axis_to_blender(d['axis_u'], 'hinge'), rng=d['range'], parent=EXT,
         states=['closed', 'open'], lock_key=S.LOCK_KEY,
         note='steel side door, opens out (east) about the south jamb to 100 deg; locked, key Garage (Forest_Opening.json)')


# ---------------------------------------------------------------- windows
def windows():
    """steel windows (dark green): frame 5 cm, a mullion, the glass in two lights at Update 3's glass line; inside the
    liner's reveal and a galvanised board; outside a sloped galvanised sill (the flashings: opening_trims)"""
    k = ext()
    kh = hall()
    kg = glass()
    for w in S.WINDOWS:
        key = w['wall']
        _, ax, a_out, sg, a_in, a_pl, wu0, wu1 = next(t for t in walls() if t[0] == key)
        u0, u1 = w['u']
        z0, z1 = w['z']
        ag = a_out - sg * 0.04                                      # Update 3's glass line (|y| 4.46)
        fa0, fa1 = sorted((ag - 0.035, ag + 0.035))
        fw = 0.05
        um = (u0 + u1) / 2
        for (ua, ub, za, zb) in ((u0, u0 + fw, z0, z1), (u1 - fw, u1, z0, z1), (u0 + fw, u1 - fw, z0, z0 + fw),
                                 (u0 + fw, u1 - fw, z1 - fw, z1), (um - 0.03, um + 0.03, z0 + fw, z1 - fw)):
            wbox(k, ax, fa0, fa1, ua, ub, za, zb, Z_WINFRAME)
        for (pa, pb) in ((u0 + fw, um - 0.03), (um + 0.03, u1 - fw)):
            q = [P3(ax, ag, pa, z0 + fw), P3(ax, ag, pb, z0 + fw), P3(ax, ag, pb, z1 - fw), P3(ax, ag, pa, z1 - fw)]
            face(kg, q, 0, Vector((sg, 0, 0)) if ax == 'x' else Vector((0, sg, 0)))    # (the build adds its back face)
            # glazing beads inside
            ab = ag - sg * 0.006
            for (ua, ub, za, zb) in ((pa, pa + 0.015, z0 + fw, z1 - fw), (pb - 0.015, pb, z0 + fw, z1 - fw),
                                     (pa + 0.015, pb - 0.015, z0 + fw, z0 + fw + 0.015),
                                     (pa + 0.015, pb - 0.015, z1 - fw - 0.015, z1 - fw)):
                wbox(k, ax, ab, ab - sg * 0.012, ua, ub, za, zb, Z_WINFRAME)
        # the reveal inside (liner) from the liner face to the frame, the board at the bottom
        f_in = fa0 if sg > 0 else fa1
        for uu, s_ in ((u0, 1), (u1, -1)):
            ua_ = Vector((0, s_, 0)) if ax == 'x' else Vector((s_, 0, 0))
            face(kh, [P3(ax, a_in, uu, z0), P3(ax, f_in, uu, z0), P3(ax, f_in, uu, z1), P3(ax, a_in, uu, z1)], Z_LINER, ua_)
        face(kh, [P3(ax, a_in, u0, z1), P3(ax, f_in, u0, z1), P3(ax, f_in, u1, z1), P3(ax, a_in, u1, z1)], Z_LINER, (0, 0, -1))
        wbox(kh, ax, f_in, a_in - sg * 0.03, u0 - 0.02, u1 + 0.02, z0 - 0.015, z0, Z_GALV)
        # the reveal outside (the trims' returns) and the sill
        f_out = fa1 if sg > 0 else fa0
        for uu, s_ in ((u0, 1), (u1, -1)):
            ua_ = Vector((0, s_, 0)) if ax == 'x' else Vector((s_, 0, 0))
            face(k, [P3(ax, f_out, uu, z0), P3(ax, a_out, uu, z0), P3(ax, a_out, uu, z1), P3(ax, f_out, uu, z1)], Z_TRIM, ua_)
        face(k, [P3(ax, f_out, u0, z1), P3(ax, a_out, u0, z1), P3(ax, a_out, u1, z1), P3(ax, f_out, u1, z1)], Z_TRIM,
             (0, 0, -1))
        o1 = a_out + sg * 0.05
        ua, ub = u0 - 0.09, u1 + 0.09
        za, zb = z0 - 0.004, z0 - 0.040
        nrm = Vector((sg, 0, 0)) if ax == 'x' else Vector((0, sg, 0))
        face(k, [P3(ax, f_out, ua, za), P3(ax, o1, ua, zb), P3(ax, o1, ub, zb), P3(ax, f_out, ub, za)], Z_GALV, (0, 0, 1))
        face(k, [P3(ax, o1, ua, zb), P3(ax, o1, ua, zb - 0.025), P3(ax, o1, ub, zb - 0.025), P3(ax, o1, ub, zb)], Z_GALV, nrm)
        face(k, [P3(ax, a_out, ua, zb - 0.025), P3(ax, o1, ua, zb - 0.025), P3(ax, o1, ub, zb - 0.025),
                 P3(ax, a_out, ub, zb - 0.025)], Z_GALV, (0, 0, -1))
        for uu, s_ in ((ua, -1), (ub, 1)):
            ua_ = Vector((0, s_, 0)) if ax == 'x' else Vector((s_, 0, 0))
            face(k, [P3(ax, f_out, uu, za), P3(ax, o1, uu, zb), P3(ax, o1, uu, zb + 0.02), P3(ax, f_out, uu, za + 0.02)],
                 Z_GALV, ua_)
        # a window handle on the east light (a tilting light)
        hu = um + 0.03 + 0.06
        ha = f_in - sg * 0.012
        VM.rbox(kh, P3(ax, ha, hu, z1 - fw - 0.10), (0.03, 0.03, 0.03), MO.Z_WINHANDLE, r=0.006, ch=0.003)
        kh.cyl(P3(ax, ha, hu, z1 - fw - 0.10), P3(ax, ha - sg * 0.03, hu, z1 - fw - 0.10), 0.006, MO.Z_WINHANDLE, 6)
        kh.cyl(P3(ax, ha - sg * 0.03, hu, z1 - fw - 0.10), P3(ax, ha - sg * 0.03, hu, z1 - fw - 0.20), 0.007, MO.Z_WINHANDLE, 6)


# ---------------------------------------------------------------- contents
def shelving():
    """steel shelving against the west wall (Update 3: 0.6 x 2.4 x 2.4, four shelves): slotted angle posts, galvanised
    shelves at Update 3's heights, X braces at the back, Update 3's boxes on it"""
    k = hall()
    sp = S.SHELF
    x0, x1 = sp['x']
    y0, y1 = sp['y']
    h = sp['h']
    for x in (x0 + 0.025, x1 - 0.025):
        for y in (y0 + 0.02, y1 - 0.02):
            box6(k, (x - 0.02, y - 0.02, 0.0), (x + 0.02, y + 0.02, h), F.Z_STEELF)
            box6(k, (x - 0.03, y - 0.03, 0.0), (x + 0.03, y + 0.03, 0.006), Z_STEELBLK, skip=('-z',))
    for zl in sp['levels']:
        za, zb = zl - 0.013, zl + 0.012                       # Update 3: 0.087..0.112 etc.
        box6(k, (x0 + 0.005, y0 + 0.005, za), (x1 - 0.005, y1 - 0.005, zb), Z_GALV)
    for (za, zb) in ((sp['levels'][0], sp['levels'][1]), (sp['levels'][2], sp['levels'][3])):
        xb_ = x0 + 0.006
        k.tube([Vector((xb_, y0 + 0.04, za + 0.03)), Vector((xb_, y1 - 0.04, zb - 0.03))], 0.004, Z_GALV, 4)
        k.tube([Vector((xb_, y1 - 0.04, za + 0.03)), Vector((xb_, y0 + 0.04, zb - 0.03))], 0.004, Z_GALV, 4)
    zone = {'card': F.Z_CARDBOX, 'olive': F.Z_OLIVE, 'wood': F.Z_PALLET, 'army': F.Z_CRATE}
    for (cx, cy), (sx, sy), z0, z1, kind in S.SHELF_BOXES:
        F.crate(k, (cx - sx / 2, cy - sy / 2, z0), (cx + sx / 2, cy + sy / 2, z1), zone[kind], r=0.008 if kind == 'card' else 0.012)
        if kind == 'card':                                          # the tape across the lid
            box6(k, (cx - sx / 2 + 0.02, cy - 0.025, z1), (cx + sx / 2 - 0.02, cy + 0.025, z1 + 0.002), F.Z_PAPER,
                 skip=('-z',))


def crates():
    k = hall()
    zone = {'crate': F.Z_CRATE, 'pallet': F.Z_PALLET}
    for c, size, yaw, z0, z1, kind in S.CRATES:
        F.crate_yaw(k, c, size, yaw, z0, z1, zone[kind])


def workbench():
    """Update 3's bench (top 2.4 x 0.75 at 0.87..0.93, two side frames): a thick beech top on welded steel frames, a
    shelf under it with a toolbox and a battery, the vice at the left end; the pegboard on battens with tools on hooks,
    the clipboard; at the back of the top a small parts cabinet and an oil can"""
    k = hall()
    b = S.BENCH
    x0, x1 = b['x']
    y0, y1 = b['y']
    top = b['top']
    F.rb(k, (x0, y0, top - 0.06), (x1, y1, top), F.Z_WOODF, r=0.006, ch=0.003)
    for x in (x0 + 0.10, x1 - 0.10):
        for y in (y0 + 0.05, y1 - 0.05):
            box6(k, (x - 0.025, y - 0.025, 0.0), (x + 0.025, y + 0.025, top - 0.06), F.Z_STEELF)
        box6(k, (x - 0.02, y0 + 0.05, 0.16), (x + 0.02, y1 - 0.05, 0.20), F.Z_STEELF, skip=('-y', '+y'))
        box6(k, (x - 0.02, y0 + 0.05, top - 0.12), (x + 0.02, y1 - 0.05, top - 0.06), F.Z_STEELF, skip=('-y', '+y'))
    box6(k, (x0 + 0.125, y0 + 0.08, 0.20), (x1 - 0.125, y1 - 0.06, 0.22), F.Z_WOODSHELF)
    VM.rbox(k, Vector((x0 + 0.55, y0 + 0.35, 0.32)), (0.52, 0.24, 0.20), F.Z_TOOL, r=0.012, ch=0.005)        # toolbox
    k.cyl(Vector((x0 + 0.37, y0 + 0.35, 0.42)), Vector((x0 + 0.73, y0 + 0.35, 0.42)), 0.010, Z_STEELBLK, 6)
    VM.rbox(k, Vector((x1 - 0.55, y0 + 0.40, 0.31)), (0.28, 0.18, 0.18), Z_STEELBLK, r=0.01, ch=0.004)        # battery
    for dx in (-0.08, 0.08):
        k.cyl(Vector((x1 - 0.55 + dx, y0 + 0.40, 0.40)), Vector((x1 - 0.55 + dx, y0 + 0.40, 0.42)), 0.012, F.Z_BRASS, 8)
    # the vice on the left end of the top
    vx, vy = x0 + 0.22, y0 + 0.06
    box6(k, (vx - 0.08, vy, top), (vx + 0.08, vy + 0.22, top + 0.05), F.Z_PUMPG)
    box6(k, (vx - 0.09, vy - 0.03, top + 0.05), (vx + 0.09, vy + 0.02, top + 0.15), F.Z_PUMPG)
    box6(k, (vx - 0.09, vy + 0.07, top + 0.05), (vx + 0.09, vy + 0.12, top + 0.15), F.Z_PUMPG)
    k.cyl(Vector((vx, vy - 0.03, top + 0.09)), Vector((vx, vy - 0.20, top + 0.09)), 0.010, F.Z_CHROME, 6)
    k.cyl(Vector((vx - 0.10, vy - 0.20, top + 0.09)), Vector((vx + 0.10, vy - 0.20, top + 0.09)), 0.007, F.Z_CHROME, 6)
    # the parts cabinet and the oil can at the back
    VM.rbox(k, Vector((x1 - 0.30, y1 - 0.12, top + 0.13)), (0.40, 0.16, 0.26), F.Z_CABGREY, r=0.006, ch=0.003)
    for i in range(3):
        for j in range(4):
            box6(k, (x1 - 0.48 + j * 0.09, y1 - 0.205, top + 0.025 + i * 0.08), (x1 - 0.41 + j * 0.09, y1 - 0.20, top + 0.085 + i * 0.08),
                 F.Z_PCBEIGE, skip=('+y',))
    k.cyl(Vector((x1 - 0.70, y1 - 0.12, top)), Vector((x1 - 0.70, y1 - 0.12, top + 0.16)), 0.045, F.Z_DRUM_R, 12)
    k.cyl(Vector((x1 - 0.70, y1 - 0.12, top + 0.16)), Vector((x1 - 0.62, y1 - 0.12, top + 0.30)), 0.006, F.Z_DRUM_R, 6)
    # the pegboard on battens, the tools, the clipboard
    pg = S.PEGBOARD
    yb = YI
    box6(k, (pg['x'][0] + 0.05, yb - 0.015, pg['z'][0] + 0.05), (pg['x'][0] + 0.09, yb, pg['z'][1] - 0.05), F.Z_WOODSHELF,
         skip=('+y',))
    box6(k, (pg['x'][1] - 0.09, yb - 0.015, pg['z'][0] + 0.05), (pg['x'][1] - 0.05, yb, pg['z'][1] - 0.05), F.Z_WOODSHELF,
         skip=('+y',))
    yf = yb - 0.035
    box6(k, (pg['x'][0], yf, pg['z'][0]), (pg['x'][1], yb - 0.015, pg['z'][1]), F.Z_PEGBOARD)
    tools(k, pg, yf)
    kp = panel_hall()
    kp.quad_uv(Vector((pg['x'][1] - 0.30, yf - 0.012, pg['z'][0] + 0.55)), Vector((0, -1, 0)), 0.17, 0.235,
               T.uv('paper_a'), 0, up=Vector((0, 0, 1)))
    VM.rbox(k, Vector((pg['x'][1] - 0.30, yf - 0.005, pg['z'][0] + 0.545)), (0.19, 0.008, 0.27), F.Z_WOODF, r=0.004,
            ch=0.002)
    box6(k, (pg['x'][1] - 0.33, yf - 0.014, pg['z'][0] + 0.655), (pg['x'][1] - 0.27, yf - 0.009, pg['z'][0] + 0.675),
         F.Z_CHROME)


def tools(k, pg, yf):
    """tools on pegboard hooks (Update 3: red, iron and yellow ones in a row): hammer, spanners, screwdrivers, a saw, pliers,
    a file, a tyre lever"""
    x0, x1 = pg['x']
    z0, z1 = pg['z']
    n = Vector((0, -1, 0))

    def hook(x, z):
        k.cyl(Vector((x, yf, z)), Vector((x, yf - 0.05, z + 0.012)), 0.0035, Z_HOOK, 4)

    zt = z1 - 0.20
    x = x0 + 0.20
    hook(x, zt)                                                       # hammer: handle down, head across
    k.cyl(Vector((x, yf - 0.03, zt - 0.02)), Vector((x, yf - 0.03, zt - 0.32)), 0.013, F.Z_WOODF, 6)
    box6(k, (x - 0.06, yf - 0.05, zt - 0.03), (x + 0.06, yf - 0.012, zt + 0.0), F.Z_STEELF)
    x += 0.24
    for i, L in enumerate((0.16, 0.20, 0.24, 0.28)):                 # spanners, rising sizes
        xx = x + i * 0.06
        hook(xx, zt)
        box6(k, (xx - 0.010, yf - 0.03, zt - 0.02 - L), (xx + 0.010, yf - 0.024, zt - 0.02), F.Z_CHROME)
        box6(k, (xx - 0.020, yf - 0.03, zt - 0.06 - L), (xx + 0.020, yf - 0.024, zt - 0.02 - L), F.Z_CHROME)
    x += 0.34
    for i, col in enumerate((F.Z_EXTING, F.Z_BAR, F.Z_EXTING, F.Z_BAR)):     # screwdrivers: red / yellow handles
        xx = x + i * 0.05
        hook(xx, zt - 0.02)
        k.cyl(Vector((xx, yf - 0.03, zt - 0.02)), Vector((xx, yf - 0.03, zt - 0.13)), 0.012, col, 6)
        k.cyl(Vector((xx, yf - 0.03, zt - 0.13)), Vector((xx, yf - 0.03, zt - 0.27)), 0.0035, F.Z_CHROME, 4)
    x += 0.30
    hook(x, zt + 0.02)                                                 # the saw
    face(k, [(x - 0.04, yf - 0.026, zt - 0.05), (x + 0.30, yf - 0.026, zt - 0.10), (x + 0.30, yf - 0.026, zt - 0.02),
             (x - 0.04, yf - 0.026, zt + 0.01)], F.Z_CHROME, n)
    box6(k, (x - 0.12, yf - 0.035, zt - 0.06), (x - 0.03, yf - 0.018, zt + 0.03), F.Z_WOODF)
    x += 0.46
    hook(x, zt)                                                        # pliers, file, tyre lever
    k.cyl(Vector((x - 0.01, yf - 0.03, zt - 0.02)), Vector((x - 0.025, yf - 0.03, zt - 0.20)), 0.007, F.Z_EXTING, 5)
    k.cyl(Vector((x + 0.01, yf - 0.03, zt - 0.02)), Vector((x + 0.025, yf - 0.03, zt - 0.20)), 0.007, F.Z_EXTING, 5)
    hook(x + 0.10, zt)
    k.cyl(Vector((x + 0.10, yf - 0.03, zt - 0.02)), Vector((x + 0.10, yf - 0.03, zt - 0.32)), 0.006, F.Z_STEELF, 4)
    k.cyl(Vector((x + 0.10, yf - 0.03, zt - 0.02)), Vector((x + 0.10, yf - 0.03, zt + 0.06)), 0.011, F.Z_WOODF, 6)
    hook(x + 0.20, zt)
    k.cyl(Vector((x + 0.20, yf - 0.03, zt - 0.01)), Vector((x + 0.20, yf - 0.03, zt - 0.40)), 0.009, F.Z_TOOL, 6)
    # a row of smaller things lower down: tape, wire spool, a torch
    zl = z0 + 0.32
    xx = x0 + 0.30
    hook(xx, zl)
    k.cyl(Vector((xx, yf - 0.012, zl - 0.06)), Vector((xx, yf - 0.05, zl - 0.06)), 0.045, F.Z_BAR, 12)
    hook(xx + 0.18, zl)
    k.cyl(Vector((xx + 0.18, yf - 0.012, zl - 0.07)), Vector((xx + 0.18, yf - 0.06, zl - 0.07)), 0.055, F.Z_COPPER, 12)
    hook(xx + 0.36, zl)
    k.cyl(Vector((xx + 0.36, yf - 0.03, zl - 0.03)), Vector((xx + 0.36, yf - 0.03, zl - 0.24)), 0.020, F.Z_EXTING, 8)


def drums():
    """the spill pallet (yellow, galvanised grating) with Update 3's three drums on it (the third, which stood half
    through the east wall in Update 3, inside now) and two jerrycans in the fourth place; the pallet's plate"""
    k = hall()
    x0, x1 = SPILL['x']
    y0, y1 = SPILL['y']
    h = SPILL['h']
    box6(k, (x0, y0, 0.0), (x1, y1, h - 0.02), Z_SPILL, skip=('-z', '+z'))
    face(k, [(x0, y0, h - 0.02), (x1, y0, h - 0.02), (x1, y1, h - 0.02), (x0, y1, h - 0.02)], Z_SPILL, (0, 0, 1))
    box6(k, (x0 + 0.03, y0 + 0.03, h - 0.02), (x1 - 0.03, y1 - 0.03, h), F.Z_GRATING, skip=('-z',))
    for (a, b, c_, d_) in ((x0, x1, y0, y0 + 0.03), (x0, x1, y1 - 0.03, y1), (x0, x0 + 0.03, y0 + 0.03, y1 - 0.03),
                           (x1 - 0.03, x1, y0 + 0.03, y1 - 0.03)):
        box6(k, (a, c_, h - 0.02), (b, d_, h + 0.004), Z_SPILL, skip=('-z',))
    for xf in (x0 + 0.20, x1 - 0.20):                                   # fork pockets
        box6(k, (xf - 0.09, y0 - 0.001, 0.02), (xf + 0.09, y0 + 0.002, 0.09), Z_STEELBLK, skip=('+y',))
    for (cx, cy), col in zip([(4.80, -2.60), (5.42, -2.60), (5.42, -2.02)], ('blue', 'red', 'blue')):
        drum(k, Vector((cx, cy, h)), F.Z_DRUM_B if col == 'blue' else F.Z_DRUM_R)
    MR.jerrycan(k, Vector((4.72, -2.02, h)), F.Z_DRUM_R)
    MR.jerrycan(k, Vector((4.92, -2.02, h)), F.Z_JERRY)
    kp = panel_hall()
    kp.quad_uv(Vector(((x0 + x1) / 2, y0 - 0.0015, 0.08)), Vector((0, -1, 0)), 0.18, 0.05, T.uv('pallet_lbl'), 0,
               up=Vector((0, 0, 1)))


def drum(k, base, zone, r=0.28):
    """a 200 l drum (Update 3: 0.56 across, 0.88 high): rolling hoops, the chimes, two bungs on the lid"""
    k.cyl(base + Vector((0, 0, 0.01)), base + Vector((0, 0, 0.87)), r, zone, 18)
    for z in (0.0, 0.87):
        k.cyl(base + Vector((0, 0, z)), base + Vector((0, 0, z + 0.012)), r + 0.006, zone, 18)
    for z in (0.30, 0.58):
        k.cyl(base + Vector((0, 0, z - 0.012)), base + Vector((0, 0, z + 0.012)), r + 0.006, zone, 18)
    for dx, rr in ((0.17, 0.028), (-0.18, 0.016)):
        k.cyl(base + Vector((dx, 0.03, 0.882)), base + Vector((dx, 0.03, 0.892)), rr, F.Z_STEELF, 8)


def quad():
    """the station's quad (Update 3: wheels at x -2.12 / -0.88, y 0.5 / 1.5, the headlight to the east): main_rooms'
    quad turned to face east"""
    tmp = VK.KB()
    MR.quad_bike(tmp, Vector((0, 0, 0)))
    q = S.QUAD
    M = Matrix.Translation(Vector((q['c'][0], q['c'][1], 0.0))) @ Matrix.Rotation(math.radians(-90.0), 4, 'Z')
    merge_kb(hall(), tmp, M)
    k = hall()                                                        # its headlight (Update 3's dark lens) in the front
    c = Vector((q['c'][0] + 0.86, q['c'][1], 0.66))
    k.cyl(c - Vector((0.03, 0, 0)), c + Vector((0.01, 0, 0)), 0.055, F.Z_QUAD, 12)
    k.cyl(c + Vector((0.01, 0, 0)), c + Vector((0.016, 0, 0)), 0.046, F.Z_SCREEN, 12)


def spare_tyres():
    """four spare quad tyres stacked by the shelving"""
    k = hall()
    for i in range(4):
        base = Vector((-5.30, 3.45, i * 0.205))
        k.lathe(base, Vector((0, 0, 1)), [(0.0, 0.24), (0.015, 0.27), (0.19, 0.27), (0.205, 0.24)], F.Z_TYRE, 16, cap0=False,
                cap1=False)
        k.lathe(base, Vector((0, 0, 1)), [(0.205, 0.14), (0.0, 0.14)], F.Z_TYRE, 14, cap0=False, cap1=False)
        k.lathe(base + Vector((0, 0, 0.205)), Vector((0, 0, 1)), [(0.0, 0.24), (0.0, 0.14)], F.Z_TYRE, 16, cap0=False,
                cap1=False)


def wall_kit():
    """the sub-distribution board by the side door with its conduits (supply from the floor; up and along the ceiling to
    the two fittings and through the south wall to the lamp over the gate), sockets under it; the extinguisher and its
    sign; the signs by the drums and by the gate; the calendar; a snow shovel and a broom by the door"""
    k = hall()
    kp = panel_hall()
    # the board
    db = Vector((XI, 2.62, 1.55))
    F.wall_box(k, db, NX, 0.40, 0.50, 0.14, F.Z_CABGREY)
    box6(k, (XI - 0.142, 2.62 - 0.17, 1.55 + 0.17), (XI - 0.14, 2.62 + 0.17, 1.55 + 0.20), Z_STEELBLK, skip=('+x',))
    kp.quad_uv(Vector((XI - 0.1415, 2.62, 1.55 + 0.185)), Vector((-1, 0, 0)), 0.15, 0.031, T.uv('db_lbl'), 0,
               up=Vector((0, 0, 1)))
    k.cyl(Vector((XI - 0.14, 2.62 + 0.15, 1.50)), Vector((XI - 0.15, 2.62 + 0.15, 1.50)), 0.012, Z_STEELBLK, 8)
    F.conduit_run(k, [Vector((XI - 0.03, 2.55, UPSTAND)), Vector((XI - 0.03, 2.55, 1.30))])
    F.socket_outlet(k, (XI, 2.40, 1.10), NX, kind='surface')
    F.socket_outlet(k, (XI, 2.84, 1.10), NX, kind='cee_red')
    F.conduit_run(k, [Vector((XI - 0.03, 2.40, 1.14)), Vector((XI - 0.03, 2.40, 1.30))])
    F.conduit_run(k, [Vector((XI - 0.03, 2.84, 1.14)), Vector((XI - 0.03, 2.84, 1.30))])
    zc = 4.24                                                         # the ceiling run: through the beams' webs
    F.conduit_run(k, [Vector((XI - 0.03, 2.70, 1.80)), Vector((XI - 0.03, 2.70, zc)), Vector((XI - 0.03, 0.42, zc)),
                      Vector((-3.0, 0.42, zc))])
    for x in (-3.0, 3.0):
        F.conduit_run(k, [Vector((x, 0.42, zc)), Vector((x, 0.42, DECK_Z - 0.035)), Vector((x, 0.32, DECK_Z - 0.035))])
    F.conduit_run(k, [Vector((-1.50, 0.42, zc)), Vector((-1.50, -YI + 0.03, zc)), Vector((-1.50, -YI + 0.03, 3.55))])
    # the extinguisher south of the door, its sign
    F.extinguisher(k, (XI, 0.62, 0.42), NX)
    kp.quad_uv(Vector((XI - 0.0015, 0.62, 1.32)), Vector((-1, 0, 0)), 0.20, 0.20, T.uv('pic_ext'), 0, up=Vector((0, 0, 1)))
    # over the drums: BRANDGEFAHR, RAUCHEN VERBOTEN with the pictogram
    kp.quad_uv(Vector((XI - 0.0015, -2.30, 1.86)), Vector((-1, 0, 0)), 0.40, 0.124, T.uv('brand'), 0, up=Vector((0, 0, 1)))
    kp.quad_uv(Vector((XI - 0.0015, -2.30, 1.40)), Vector((-1, 0, 0)), 0.40, 0.117, T.uv('rauchen'), 0, up=Vector((0, 0, 1)))
    kp.quad_uv(Vector((XI - 0.0015, -2.30, 1.62)), Vector((-1, 0, 0)), 0.20, 0.20, T.uv('pic_nosmoke'), 0,
               up=Vector((0, 0, 1)))
    # by the gate, inside
    kp.quad_uv(Vector((1.25, -YI + 0.0015, 1.60)), Vector((0, 1, 0)), 0.54, 0.10, T.uv('torzu'), 0, up=Vector((0, 0, 1)))
    # the calendar left of the pegboard
    kp.quad_uv(Vector((2.10, YI - 0.0015, 1.62)), Vector((0, -1, 0)), 0.25, 0.30, T.uv('calendar'), 0, up=Vector((0, 0, 1)))
    k.cyl(Vector((2.10, YI, 1.78)), Vector((2.10, YI - 0.02, 1.78)), 0.003, Z_HOOK, 4)
    # shovel and broom leaning by the door (north of it)
    MR.shovel(k, Vector((5.52, 3.30, 0.0)), lean=(1.0, 0.0))
    broom(k, Vector((5.60, 3.70, 0.0)))


def broom(k, base):
    top = base + Vector((0.16, 0.02, 1.27))
    k.cyl(base + Vector((0, 0, 0.10)), top, 0.013, F.Z_WOODF, 8)
    box6(k, base + Vector((-0.04, -0.20, 0.0)), base + Vector((0.04, 0.20, 0.12)), F.Z_DRUM_R)


def panel_hall():
    k = kb('Garage_Panel', 'panel')
    if 'Garage_Panel' not in K.CONTRACT['parts']:
        part('Garage_Panel', 'static', (0, 0, 0), parent=EXT, note='signs, labels and papers (panel atlas); joined at export')
    return k


def outside_signs():
    """GARAGE over the gate on its plate (Update 3: 1.10 x 0.44 at z 3.63..4.07)"""
    k = ext()
    s = S.SIGN
    c = Vector(s['c'])
    box6(k, (c.x - s['w'] / 2 - 0.015, -YO - 0.02, c.z - s['h'] / 2 - 0.015),
         (c.x + s['w'] / 2 + 0.015, -YO, c.z + s['h'] / 2 + 0.015), F.Z_STEELF, skip=('+y',))
    panel_hall().quad_uv(Vector((c.x, -YO - 0.02 - 0.0015, c.z)), Vector((0, -1, 0)), s['w'], s['h'], T.uv('garage'), 0,
                         up=Vector((0, 0, 1)))


# ---------------------------------------------------------------- the lamps (Update 3's lights and glows stay put)
def fittings():
    """the two ceiling fittings (Update 3: 0.64 square under the ceiling, lens M_Lamp_FluorOff): a sheet-steel box on
    the deck's flanges, the prismatic diffuser under it; the bulkhead over the gate (lens M_Lamp_BulbOff at Update 3's
    glow, y -4.62): the cast base on a plate, the glass, the cage"""
    k = hall()
    kl = lens('fluor')
    for (x, y) in S.FITTINGS:
        zt, zb = DECK_Z, DECK_Z - 0.065
        box6(k, (x - 0.32, y - 0.32, zb + 0.008), (x + 0.32, y + 0.32, zt), FX.Z_FX_WHITE, skip=('+z',))
        for (a, b) in (((x - 0.32, y - 0.32), (x + 0.32, y - 0.30)), ((x - 0.32, y + 0.30), (x + 0.32, y + 0.32)),
                       ((x - 0.32, y - 0.30), (x - 0.30, y + 0.30)), ((x + 0.30, y - 0.30), (x + 0.32, y + 0.30))):
            box6(k, (a[0], a[1], zb), (b[0], b[1], zb + 0.008), FX.Z_FX_ALU)
        face(kl, [(x - 0.30, y - 0.30, zb + 0.004), (x + 0.30, y - 0.30, zb + 0.004), (x + 0.30, y + 0.30, zb + 0.004),
                  (x - 0.30, y + 0.30, zb + 0.004)], 0, (0, 0, -1))
    # the bulkhead over the gate
    ke = ext()
    kb_ = lens('bulb')
    c = Vector(S.WALL_LAMP)
    c.y = -YO
    u, v, n = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))
    box6(ke, (c.x - 0.17, -YO - 0.008, c.z - 0.11), (c.x + 0.17, -YO, c.z + 0.11), F.Z_STEELF, skip=('+y',))
    c0 = c + n * 0.008
    FX.loft_oval(ke, c0, u, v, n, [(0.0, 0.135, 0.081), (0.03, 0.135, 0.081), (0.04, 0.126, 0.072)], FX.Z_FX_ALU, 24,
                 cap0=FX.Z_FX_ALU, cap1=FX.Z_FX_ALU)
    rings = [(0.04 + 0.072 * math.sin(a), 0.112 * math.cos(a), 0.062 * math.cos(a)) for a in (0.0, 0.35, 0.7, 1.0, 1.25, 1.45)]
    FX.loft_oval(kb_, c0, u, v, n, rings, 0, 20, cap1=0)
    for s in (-0.06, 0.0, 0.06):
        pts = []
        for i in range(9):
            a = -1.35 + 2.7 * i / 8
            w = 0.116 * math.sin(a)
            hgt = 0.04 + 0.077 * math.cos(a) * math.sqrt(max(0.0, 1 - (s / 0.066) ** 2))
            pts.append(c0 + u * w + v * s + n * hgt)
        ke.tube(pts, 0.004, FX.Z_FX_CAGE, 5)
    FX.loft_oval(ke, c0, u, v, n, [(0.036, 0.122, 0.069), (0.046, 0.122, 0.069), (0.046, 0.114, 0.061), (0.036, 0.114, 0.061)],
                 FX.Z_FX_CAGE, 24)
    for nm in ('Garage__fluor', 'Garage__bulb'):
        part(nm, 'static', (0, 0, 0), parent=EXT, note='lamp lenses (M_Lamp_FluorOff / M_Lamp_BulbOff, swapped by the game '
                                                      'with the station\'s power); joined at export')


# ---------------------------------------------------------------- the build
def build_garage():
    part(EXT, 'static', (0, 0, 0), parent=None, note='the garage: envelope, roof, hall, contents (Update 3: one mesh)')
    part(HALL, 'static', (0, 0, 0), parent=EXT, note='the hall\'s inside (atlas GarIn); joined into Garage at export')
    part('Garage_Glass', 'static', (0, 0, 0), parent=EXT, note='the window glass (M_GlassDirty); joined at export')
    plinth_and_skin()
    opening_trims()
    roof()
    apron()
    hall_shell()
    gate_frame()
    gate_leaf()
    side_door()
    windows()
    shelving()
    crates()
    workbench()
    drums()
    quad()
    spare_tyres()
    wall_kit()
    outside_signs()
    fittings()
