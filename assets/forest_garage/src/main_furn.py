"""Main building — furniture and equipment pieces (the generator shed's way: real thicknesses, rounded edges where hands
go, screws, handles, wear in the texture), each built around the Update 3 interactable parts it carries (drawers, doors,
breakers ...) at their pivots: the parts keep their names, pivots, axes and ranges (main_ix_u3.IX)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, Z_GALV, Z_STEELBLK
import van3_mech as VM
import main_ix_u3 as X
import main_open as MO

(Z_DESKTOP, Z_STEELF, Z_CABGREY, Z_DRAWER, Z_HANDLEB, Z_CHAIRSEAT, Z_CHAIRBASE, Z_CRT, Z_SCREEN, Z_KEYB, Z_PCBEIGE,
 Z_CONSOLE, Z_CONSOLEP, Z_LED, Z_RACK, Z_RACKDOOR, Z_RACKEQ, Z_PAPER, Z_BINDER, Z_WOODF, Z_LOCKER, Z_OLIVE,
 Z_MATTRESS, Z_BLANKET, Z_PILLOW, Z_ENAMELW, Z_CHROME, Z_LAMINATE, Z_TILESPL, Z_SINK, Z_STOVE, Z_FABRIC_B, Z_FABRIC_G,
 Z_TV, Z_BOOKS, Z_SAFE, Z_CLOCK, Z_BOARD, Z_RADIATOR, Z_VALVE, Z_PIPE_W, Z_SOCKET, Z_SWITCHP, Z_ROCKER, Z_SMOKE,
 Z_SPEAKER, Z_PHONE, Z_EXTING, Z_SIGN, Z_CALLPT, Z_BELL, Z_FIRSTAID, Z_RUBBERB, Z_DRUM_R, Z_DRUM_B, Z_TYRE,
 Z_CRATE, Z_PALLET, Z_QUAD, Z_QUADSEAT, Z_PEGBOARD, Z_TOOL, Z_JERRY, Z_BOILER, Z_BURNER, Z_INSUL, Z_COPPER,
 Z_BRASS, Z_TANKG, Z_PUMPG, Z_GAUGE, Z_CYL, Z_BOARDC, Z_BREAKER, Z_MAINSW, Z_CABLE, Z_TRAY, Z_WOODSHELF, Z_CARDBOX,
 Z_BOOT, Z_BAG, Z_JACKET, Z_MAT, Z_SHOWER, Z_CUBICLE, Z_TROUGH, Z_MIRROR, Z_WASHM, Z_TOWEL, Z_CURTAIN,
 Z_MAPTABLE, Z_MAP, Z_MUG, Z_PLATE, Z_BAR, Z_FASCIA, Z_GRATING, Z_DISH, Z_SCREENP) = range(400, 499)
DRAFT_COL = {Z_DESKTOP: (196, 176, 140), Z_STEELF: (118, 120, 116), Z_CABGREY: (150, 152, 148), Z_DRAWER: (156, 158, 152),
             Z_HANDLEB: (190, 190, 186), Z_CHAIRSEAT: (70, 72, 74), Z_CHAIRBASE: (40, 40, 40), Z_CRT: (200, 190, 160),
             Z_SCREEN: (20, 30, 28), Z_KEYB: (210, 200, 176), Z_PCBEIGE: (200, 190, 162), Z_CONSOLE: (140, 146, 138),
             Z_CONSOLEP: (90, 94, 90), Z_LED: (60, 140, 70), Z_RACK: (36, 38, 40), Z_RACKDOOR: (50, 54, 58),
             Z_RACKEQ: (70, 72, 76), Z_PAPER: (232, 228, 214), Z_BINDER: (40, 80, 150), Z_WOODF: (150, 104, 62),
             Z_LOCKER: (128, 134, 124), Z_OLIVE: (96, 104, 70), Z_MATTRESS: (180, 176, 160), Z_BLANKET: (80, 86, 70),
             Z_PILLOW: (220, 218, 208), Z_ENAMELW: (232, 232, 226), Z_CHROME: (200, 202, 204), Z_LAMINATE: (210, 196, 160),
             Z_TILESPL: (220, 220, 210), Z_SINK: (200, 202, 204), Z_STOVE: (220, 220, 214), Z_FABRIC_B: (120, 90, 60),
             Z_FABRIC_G: (90, 110, 90), Z_TV: (60, 46, 34), Z_BOOKS: (120, 60, 50), Z_SAFE: (80, 90, 80),
             Z_CLOCK: (230, 230, 226), Z_BOARD: (240, 240, 236), Z_RADIATOR: (236, 234, 226), Z_VALVE: (220, 220, 216),
             Z_PIPE_W: (226, 224, 216), Z_SOCKET: (232, 230, 222), Z_SWITCHP: (232, 230, 222), Z_ROCKER: (220, 218, 210),
             Z_SMOKE: (238, 238, 234), Z_SPEAKER: (200, 200, 196), Z_PHONE: (200, 190, 160), Z_EXTING: (190, 30, 24),
             Z_SIGN: (30, 140, 70), Z_CALLPT: (200, 30, 26), Z_BELL: (200, 30, 26), Z_FIRSTAID: (30, 140, 70),
             Z_RUBBERB: (30, 30, 30), Z_DRUM_R: (170, 40, 30), Z_DRUM_B: (40, 70, 140), Z_TYRE: (24, 24, 24),
             Z_CRATE: (90, 100, 66), Z_PALLET: (160, 130, 90), Z_QUAD: (190, 60, 30), Z_QUADSEAT: (30, 30, 30),
             Z_PEGBOARD: (190, 160, 110), Z_TOOL: (140, 30, 30), Z_JERRY: (90, 100, 66), Z_BOILER: (210, 110, 30),
             Z_BURNER: (90, 110, 80), Z_INSUL: (200, 200, 196), Z_COPPER: (190, 110, 60), Z_BRASS: (200, 170, 80),
             Z_TANKG: (90, 110, 80), Z_PUMPG: (40, 120, 70), Z_GAUGE: (236, 236, 230), Z_CYL: (226, 224, 214),
             Z_BOARDC: (210, 200, 176), Z_BREAKER: (40, 40, 40), Z_MAINSW: (180, 30, 26), Z_CABLE: (30, 30, 30),
             Z_TRAY: (176, 178, 176), Z_WOODSHELF: (150, 110, 70), Z_CARDBOX: (170, 140, 100), Z_BOOT: (30, 30, 28),
             Z_BAG: (80, 90, 60), Z_JACKET: (210, 100, 30), Z_MAT: (60, 60, 56), Z_SHOWER: (230, 230, 226),
             Z_CUBICLE: (180, 186, 176), Z_TROUGH: (230, 232, 230), Z_MIRROR: (170, 190, 200), Z_WASHM: (236, 236, 232),
             Z_TOWEL: (60, 90, 150), Z_CURTAIN: (220, 220, 210), Z_MAPTABLE: (140, 110, 80), Z_MAP: (210, 200, 160),
             Z_MUG: (230, 230, 226), Z_PLATE: (236, 236, 232), Z_BAR: (200, 170, 40), Z_FASCIA: (98, 112, 96),
             Z_GRATING: (120, 122, 118), Z_DISH: (226, 226, 220), Z_SCREENP: (14, 24, 22)}
# Z_SCREENP: the screens the station's power lights up (Update 3: M_ScreenOff -> M_ScreenOn); Z_LED likewise (M_LEDOff)


# ---------------------------------------------------------------- the Update 3 parts
def ix(name):
    return X.IX[name]


def ix_part(name, parent='BaseMain', note='', atlas='MainParts', pivot=None):
    """the contract entry of an Update 3 interactable (its pivot, the axis converted from Unity, the range, the flags);
    returns its KB (atlas MainParts)"""
    d = X.IX[name]
    kind = d['kind']
    axis = MO.unity_axis_to_blender(d['axis_u'], kind)
    extra = {k: d[k] for k in ('locked', 'open', 'drives', 'needsPower', 'speed') if k in d}
    unit = 'm' if kind == 'slide' else 'scale' if kind == 'scale' else 'deg'
    part(name, kind, pivot if pivot is not None else d['pivot'], axis=axis, rng=(float(d['min']), float(d['max'])),
         parent=parent, unit=unit, note=note, **extra)
    return kb(name, atlas)


def lohi(name):
    d = X.IX[name]
    return Vector(d['lo']), Vector(d['hi'])


# ---------------------------------------------------------------- small helpers
def B(k, lo, hi, zone, skip=()):
    box6(k, lo, hi, zone, skip=skip)


def rb(k, lo, hi, zone, r=0.01, ch=0.004, axis='z'):
    lo, hi = Vector(lo), Vector(hi)
    VM.rbox(k, (lo + hi) / 2, tuple(abs(v) for v in (hi - lo)), zone, r=r, ch=ch, axis=axis)


def leg(k, x, y, z0, z1, r=0.014, zone=Z_STEELF, seg=8):
    k.cyl(Vector((x, y, z0)), Vector((x, y, z1)), r, zone, seg)


def bar_handle(k, c, length, along, out, zone=Z_HANDLEB, r=0.007, stand=0.03):
    """a bow handle: two posts and the grip, `along` the grip direction, `out` from the surface"""
    c, along, out = Vector(c), Vector(along).normalized(), Vector(out).normalized()
    a, b = c - along * length / 2, c + along * length / 2
    k.cyl(a, a + out * stand, r * 0.8, zone, 6)
    k.cyl(b, b + out * stand, r * 0.8, zone, 6)
    k.cyl(a + out * stand, b + out * stand, r, zone, 8)


# ---------------------------------------------------------------- drawers and pedestals
def drawer(name, front_n, w_zone=Z_DRAWER, handle=True, note='drawer'):
    """an Update 3 drawer: its box and front from the part's box (the front at the pivot plane, the handle in front of
    it, the box behind); front_n = the direction it pulls out (Blender)"""
    k = ix_part(name, note=note)
    lo, hi = lohi(name)
    p = Vector(X.IX[name]['pivot'])
    n = Vector(front_n)
    ax = 0 if abs(n.x) > 0.5 else 1
    # the front panel: from the pivot plane 0.018 back; the box: 0.015 sides behind it to the far end
    f0 = p[ax]
    back = hi[ax] if n[ax] < 0 else lo[ax]
    gap = 0.003
    if ax == 0:
        u0, u1 = lo.y + gap, hi.y - gap
        fa, fb = sorted((f0, f0 - n.x * 0.018))
        B(k, (fa, u0, lo.z + gap), (fb, u1, hi.z - gap), w_zone)
        ba, bb = sorted((f0 - n.x * 0.018, back))
        B(k, (ba, u0 + 0.01, lo.z + 0.02), (bb, u1 - 0.01, hi.z - 0.04), Z_CABGREY, skip=('+z',))
        if handle:
            bar_handle(k, (f0, (u0 + u1) / 2, (lo.z + hi.z) / 2 + 0.02), min(0.12, (u1 - u0) * 0.5), (0, 1, 0), n)
    else:
        u0, u1 = lo.x + gap, hi.x - gap
        fa, fb = sorted((f0, f0 - n.y * 0.018))
        B(k, (u0, fa, lo.z + gap), (u1, fb, hi.z - gap), w_zone)
        ba, bb = sorted((f0 - n.y * 0.018, back))
        B(k, (u0 + 0.01, ba, lo.z + 0.02), (u1 - 0.01, bb, hi.z - 0.04), Z_CABGREY, skip=('+z',))
        if handle:
            bar_handle(k, ((u0 + u1) / 2, f0, (lo.z + hi.z) / 2 + 0.02), min(0.12, (u1 - u0) * 0.5), (1, 0, 0), n)
    # a label holder on the front
    return k


def carcass(k, lo, hi, open_side, zone=Z_CABGREY, t=0.018, plinth=0.04, inset=0.0):
    """a cabinet body lo..hi open at `open_side` ('-x', '+x', '-y', '+y'): sides, top, bottom, back, a recessed plinth;
    inset: the top and the bottom stop that far behind the open side (a door that reaches over them turns clear)"""
    lo, hi = Vector(lo), Vector(hi)
    sides = {'-x': (0, -1), '+x': (0, 1), '-y': (1, -1), '+y': (1, 1)}
    ax, sg = sides[open_side]
    oth = 1 - ax
    # top and bottom
    a, b = Vector(lo), Vector(hi)
    if sg > 0:
        b[ax] -= inset
    else:
        a[ax] += inset
    B(k, (a.x, a.y, hi.z - t), (b.x, b.y, hi.z), zone)
    B(k, (a.x, a.y, lo.z + plinth), (b.x, b.y, lo.z + plinth + t), zone)
    # the two sides (across the open side)
    for e in (lo[oth], hi[oth] - t):
        a = Vector(lo)
        b = Vector(hi)
        a[oth], b[oth] = e, e + t
        a.z, b.z = lo.z, hi.z - t
        B(k, a, b, zone)
    # back
    a, b = Vector(lo), Vector(hi)
    if sg > 0:
        b[ax] = lo[ax] + t
    else:
        a[ax] = hi[ax] - t
    a.z, b.z = lo.z + plinth + t, hi.z - t
    a[oth], b[oth] = lo[oth] + t, hi[oth] - t
    B(k, a, b, zone)
    # recessed plinth
    a, b = Vector(lo), Vector(hi)
    a[oth], b[oth] = lo[oth] + 0.02, hi[oth] - 0.02
    if sg > 0:
        b[ax] = hi[ax] - 0.05
    else:
        a[ax] = lo[ax] + 0.05
    b.z = lo.z + plinth
    B(k, a, b, Z_RUBBERB if zone != Z_WOODF else zone, skip=('-z',))


def desk(k, x0, x1, y0, y1, top_z=0.75, front='-y', pedestal_x=None, zone_top=Z_DESKTOP, zone_frame=Z_STEELF,
         modesty=True, zf=0.0):
    """a 70s office desk: laminate top with a dark edge, steel C-frame legs (or the pedestal on one side), a modesty
    panel at the back; zf = the floor"""
    t = 0.03
    rb(k, (x0, y0, top_z - t), (x1, y1, top_z), zone_top, r=0.006, ch=0.003, axis='z')
    sides = []
    if pedestal_x is None or pedestal_x > (x0 + x1) / 2:
        sides.append(x0 + 0.04)
    if pedestal_x is None or pedestal_x < (x0 + x1) / 2:
        sides.append(x1 - 0.04)
    for xx in sides:
        B(k, (xx - 0.02, y0 + 0.05, zf), (xx + 0.02, y0 + 0.09, top_z - t), zone_frame)
        B(k, (xx - 0.02, y1 - 0.09, zf), (xx + 0.02, y1 - 0.05, top_z - t), zone_frame)
        B(k, (xx - 0.02, y0 + 0.05, zf), (xx + 0.02, y1 - 0.05, zf + 0.03), zone_frame)
        B(k, (xx - 0.02, y0 + 0.05, top_z - t - 0.05), (xx + 0.02, y1 - 0.05, top_z - t), zone_frame)
    if modesty:
        yb = y1 - 0.05 if front == '-y' else y0 + 0.05
        B(k, (x0 + 0.06, yb - 0.01, zf + 0.30), (x1 - 0.06, yb + 0.01, top_z - t), zone_frame)


def crate(k, lo, hi, zone, r=0.012):
    """a transport crate / box with softened edges (Update 3 box measured exactly; planks and stencils in the paint)"""
    lo, hi = Vector(lo), Vector(hi)
    VM.rbox(k, (lo + hi) / 2, tuple(hi - lo), zone, r=r, ch=r * 0.5)


def crate_yaw(k, c, size, yaw, z0, z1, zone, r=0.012):
    """a crate / a loaded pallet as Update 3 set it down, turned about z: centre c (x, y), size (along the yaw, across),
    yaw in degrees, from z0 to z1 (Update 3's boxes measured as oriented boxes)"""
    a = math.radians(yaw)
    u, v, n = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0)), Vector((0, 0, 1))
    w, h, L = size[0], size[1], z1 - z0
    cc = Vector((c[0], c[1], (z0 + z1) / 2))
    ch = min(r * 0.5, L / 3, w / 3, h / 3)
    rings = [VM.rrect(cc - n * (L / 2), u, v, w - 2 * ch, h - 2 * ch, max(0.002, r - ch)),
             VM.rrect(cc - n * (L / 2 - ch), u, v, w, h, r), VM.rrect(cc + n * (L / 2 - ch), u, v, w, h, r),
             VM.rrect(cc + n * (L / 2), u, v, w - 2 * ch, h - 2 * ch, max(0.002, r - ch))]
    k.loft(rings, [zone] * 3, cap0=zone, cap1=zone)


def uniform(k, top, along, zone=Z_OLIVE, length=0.62):
    """a work jacket on a hanger, its shoulders along `along` (inside a locker or on a hook): hook, hanger bar, the body,
    the sleeves hanging along its sides"""
    top, a = Vector(top), Vector(along).normalized()
    side = Vector((0, 0, 1)).cross(a).normalized()
    k.cyl(top, top - Vector((0, 0, 0.05)), 0.004, Z_CHROME, 5)
    k.cyl(top - Vector((0, 0, 0.05)) - a * 0.17, top - Vector((0, 0, 0.05)) + a * 0.17, 0.007, Z_WOODF, 6)
    size = tuple(abs(v) for v in (a * 0.34 + side * 0.075 + Vector((0, 0, length))))
    VM.rbox(k, top - Vector((0, 0, 0.06 + length / 2)), size, zone, r=0.025, ch=0.01)
    VM.rbox(k, top - Vector((0, 0, 0.075)), tuple(abs(v) for v in (a * 0.16 + side * 0.09 + Vector((0, 0, 0.05)))), zone,
            r=0.015, ch=0.008)


def pedestal(k, names, front_n, lo, hi, zone=Z_CABGREY):
    """a drawer pedestal / filing cabinet: the carcass round its Update 3 drawers"""
    n = Vector(front_n)
    side = ('+x' if n.x > 0 else '-x') if abs(n.x) > 0.5 else ('+y' if n.y > 0 else '-y')
    carcass(k, lo, hi, side, zone=zone, t=0.015, plinth=0.03)
    for nm in names:
        drawer(nm, front_n)


# ---------------------------------------------------------------- seating
def office_chair(k, c, yaw=0.0, zone_seat=Z_CHAIRSEAT):
    """a five-star swivel chair (fabric seat and back, black base, chrome column)"""
    c = Vector(c)
    R = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    for i in range(5):
        a = math.radians(i * 72)
        d = R @ Vector((math.cos(a), math.sin(a), 0))
        k.cyl(c + Vector((0, 0, 0.07)), c + d * 0.30 + Vector((0, 0, 0.05)), 0.016, Z_CHAIRBASE, 6)
        k.cyl(c + d * 0.30 + Vector((0, 0, 0.0)), c + d * 0.30 + Vector((0, 0, 0.05)), 0.022, Z_RUBBERB, 8)
    k.cyl(c + Vector((0, 0, 0.07)), c + Vector((0, 0, 0.42)), 0.025, Z_CHROME, 10)
    VM.rbox(k, c + Vector((0, 0, 0.45)), (0.46, 0.44, 0.07), zone_seat, r=0.03, ch=0.01)
    back = c + R @ Vector((0, 0.21, 0.72))
    VM.obox(k, back, (0.42, 0.06, 0.40), zone_seat, R)
    k.cyl(c + R @ Vector((0, 0.19, 0.46)), c + R @ Vector((0, 0.21, 0.55)), 0.015, Z_CHAIRBASE, 6)


def wood_chair(k, c, yaw=0.0, zone=Z_WOODF, seat_zone=None):
    c = Vector(c)
    R = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    for dx, dy in ((-0.19, -0.19), (0.19, -0.19), (-0.19, 0.19), (0.19, 0.19)):
        p = c + R @ Vector((dx, dy, 0))
        top = 0.88 if dy > 0 else 0.44
        B(k, p - Vector((0.016, 0.016, 0)), p + Vector((0.016, 0.016, top)), zone)
    VM.obox(k, c + Vector((0, 0, 0.455)), (0.44, 0.44, 0.03), seat_zone or zone, R)
    VM.obox(k, c + R @ Vector((0, 0.19, 0.78)), (0.40, 0.02, 0.14), zone, R)


# ---------------------------------------------------------------- lockers and cabinets
def locker_unit(k, names, lo, hi, front_n, zone=Z_LOCKER, door_zone=None, single=False, uniforms=True):
    """steel locker(s) with the Update 3 doors (hinged, louvres, a handle and a hasp), the body lo..hi (single: one body
    per door, as in the barracks); inside each a hat shelf, a rail and a work jacket on its hanger"""
    n = Vector(front_n)
    side = ('+x' if n.x > 0 else '-x') if abs(n.x) > 0.5 else ('+y' if n.y > 0 else '-y')
    ax = 0 if abs(n.x) > 0.5 else 1
    oth = 1 - ax
    lo, hi = Vector(lo), Vector(hi)
    if not single:
        carcass(k, lo, hi, side, zone=zone, t=0.012, plinth=0.06, inset=0.014)
    for nm in names:
        dlo, dhi = lohi(nm)
        if single:
            a, b = Vector(lo), Vector(hi)
            a[oth], b[oth] = dlo[oth] - 0.01, dhi[oth] + 0.01
            carcass(k, a, b, side, zone=zone, t=0.012, plinth=0.06, inset=0.014)
        locker_door(nm, n, door_zone or zone)
        if uniforms:
            u0, u1 = dlo[oth] + 0.012, dhi[oth] - 0.012
            uc = (u0 + u1) / 2
            front = X.IX[nm]['pivot'][ax] - n[ax] * 0.02
            back = hi[ax] if n[ax] < 0 else lo[ax]
            zs = hi.z - 0.30
            a0_, a1_ = sorted((front, back))
            if ax == 0:
                B(k, (a0_, u0, zs - 0.012), (a1_, u1, zs), zone)                       # the hat shelf
                k.cyl(Vector((a0_ + 0.03, uc, zs - 0.06)), Vector((a1_ - 0.03, uc, zs - 0.06)), 0.008, Z_CHROME, 6)
                uniform(k, Vector(((a0_ + a1_) / 2, uc, zs - 0.06)), (1, 0, 0))
            else:
                B(k, (u0, a0_, zs - 0.012), (u1, a1_, zs), zone)
                k.cyl(Vector((uc, a0_ + 0.03, zs - 0.06)), Vector((uc, a1_ - 0.03, zs - 0.06)), 0.008, Z_CHROME, 6)
                uniform(k, Vector((uc, (a0_ + a1_) / 2, zs - 0.06)), (0, 1, 0))


def locker_door(name, n, zone):
    k = ix_part(name, note='locker door')
    lo, hi = lohi(name)
    p = Vector(X.IX[name]['pivot'])
    ax = 0 if abs(n.x) > 0.5 else 1
    th = 0.012
    a0 = p[ax]
    a1 = a0 - n[ax] * th
    am = a0 - n[ax] * 0.0015
    # the leaf: a 1.5 mm front sheet, the pan behind it set in 13 mm on the hinge side (the door turns about its front
    # edge: so its back clears the carcass's side as it opens)
    if ax == 0:
        u0, u1 = lo.y, hi.y
        far = u1 if abs(p.y - u0) < abs(p.y - u1) else u0
        hl = far > p.y                                               # the hinge at u0
        B(k, (min(a0, am), u0 + 0.003, lo.z + 0.003), (max(a0, am), u1 - 0.003, hi.z - 0.003), zone)
        B(k, (min(am, a1), u0 + (0.016 if hl else 0.003), lo.z + 0.003), (max(am, a1), u1 - (0.003 if hl else 0.016),
                                                                         hi.z - 0.003), zone)
        for i in range(5):                                          # louvres at the top
            zz = hi.z - 0.12 - i * 0.03
            B(k, (a0, min(p.y, far) + 0.08, zz), (a0 + n.x * 0.006, max(p.y, far) - 0.08, zz + 0.012), Z_STEELF)
        hc = Vector((a0, far - (0.05 if far > p.y else -0.05), (lo.z + hi.z) / 2 + 0.1))
        bar_handle(k, hc, 0.10, (0, 0, 1), n, stand=0.025)
    else:
        u0, u1 = lo.x, hi.x
        far = u1 if abs(p.x - u0) < abs(p.x - u1) else u0
        hl = far > p.x
        B(k, (u0 + 0.003, min(a0, am), lo.z + 0.003), (u1 - 0.003, max(a0, am), hi.z - 0.003), zone)
        B(k, (u0 + (0.016 if hl else 0.003), min(am, a1), lo.z + 0.003), (u1 - (0.003 if hl else 0.016), max(am, a1),
                                                                         hi.z - 0.003), zone)
        for i in range(5):
            zz = hi.z - 0.12 - i * 0.03
            B(k, (min(p.x, far) + 0.08, a0, zz), (max(p.x, far) - 0.08, a0 + n.y * 0.006, zz + 0.012), Z_STEELF)
        hc = Vector((far - (0.05 if far > p.x else -0.05), a0, (lo.z + hi.z) / 2 + 0.1))
        bar_handle(k, hc, 0.10, (0, 0, 1), n, stand=0.025)


def hinged_door(name, n, zone, th=0.018, handle='knob', note='cabinet door'):
    """a generic hinged door from the Update 3 box (cabinets, bedside units, the fridge, rack doors, the panel)"""
    k = ix_part(name, note=note)
    lo, hi = lohi(name)
    p = Vector(X.IX[name]['pivot'])
    ax = 0 if abs(n.x) > 0.5 else 1
    a0 = p[ax] - n[ax] * 0.008                                       # 8 mm behind the pivot plane, the rest in front
    a1 = a0 + n[ax] * th
    am = p[ax]
    # in front of the pivot plane the full leaf; behind it (8 mm) set in 1.2 cm on the hinge side: the door turns about
    # the pivot line, so its back clears the carcass as it opens
    if ax == 0:
        u0, u1 = lo.y, hi.y
        far = u1 if abs(p.y - u0) < abs(p.y - u1) else u0
        hl = far > p.y
        B(k, (min(am, a1), u0 + 0.002, lo.z + 0.002), (max(am, a1), u1 - 0.002, hi.z - 0.002), zone)
        B(k, (min(a0, am), u0 + (0.014 if hl else 0.002), lo.z + 0.002), (max(a0, am), u1 - (0.002 if hl else 0.014),
                                                                         hi.z - 0.002), zone)
        hc = Vector((a0, far - (0.05 if far > p.y else -0.05), (lo.z + hi.z) / 2))
    else:
        u0, u1 = lo.x, hi.x
        far = u1 if abs(p.x - u0) < abs(p.x - u1) else u0
        hl = far > p.x
        B(k, (u0 + 0.002, min(am, a1), lo.z + 0.002), (u1 - 0.002, max(am, a1), hi.z - 0.002), zone)
        B(k, (u0 + (0.014 if hl else 0.002), min(a0, am), lo.z + 0.002), (u1 - (0.002 if hl else 0.014), max(a0, am),
                                                                         hi.z - 0.002), zone)
        hc = Vector((far - (0.05 if far > p.x else -0.05), a0, (lo.z + hi.z) / 2))
    hc[ax] = max(a0, a1) if n[ax] > 0 else min(a0, a1)
    if handle == 'knob':
        k.cyl(hc, hc + n * 0.025, 0.012, Z_HANDLEB, 8)
    elif handle == 'bar':
        bar_handle(k, hc, min(0.20, (hi.z - lo.z) * 0.4), (0, 0, 1), n)
    return k


# ---------------------------------------------------------------- wall devices
def wall_box(k, c, n, w, h, d, zone, up=(0, 0, 1)):
    """a box standing on a wall: centre of its back c, outward normal n, width w (along the wall), height h, depth d"""
    c, n = Vector(c), Vector(n).normalized()
    u = Vector(up).cross(n).normalized()
    R = Matrix((u, Vector(up), n)).transposed()
    VM.obox(k, c + n * d / 2, (w, h, d), zone, R)


def radiator(k, x0, x1, y_wall, n_sign, z0=None, h=0.60, axis='y', valve_side=1, zf=0.0):
    """a 70s panel radiator (two panels, convector fins between, a top grille) on brackets, the thermostatic valve and its
    pipes into the floor"""
    zb = zf + 0.12
    zt = zb + h
    d0 = 0.03
    for k_ in range(2):
        off = d0 + k_ * 0.055
        if axis == 'y':
            a0, a1 = sorted((y_wall + n_sign * off, y_wall + n_sign * (off + 0.022)))
            B(k, (x0, a0, zb), (x1, a1, zt), Z_RADIATOR)
            for i in range(int((x1 - x0) / 0.05)):
                xx = x0 + 0.025 + i * 0.05
                B(k, (xx - 0.004, a0 + 0.001, zb + 0.01), (xx + 0.004, a1 - 0.001, zt - 0.01), Z_RADIATOR)
        else:
            a0, a1 = sorted((y_wall + n_sign * off, y_wall + n_sign * (off + 0.022)))
            B(k, (a0, x0, zb), (a1, x1, zt), Z_RADIATOR)
    a_top0, a_top1 = sorted((y_wall + n_sign * d0, y_wall + n_sign * (d0 + 0.077)))
    if axis == 'y':
        B(k, (x0, a_top0, zt), (x1, a_top1, zt + 0.006), Z_RADIATOR)
        vx = x1 + 0.05 if valve_side > 0 else x0 - 0.05
        ya = y_wall + n_sign * 0.08
        k.cyl(Vector((vx, ya, zf)), Vector((vx, ya, zb + 0.02)), 0.009, Z_PIPE_W, 8)
        k.cyl(Vector((vx, ya, zb + 0.02)), Vector((x1 if valve_side > 0 else x0, ya, zb + 0.02)), 0.009, Z_PIPE_W, 8)
        k.cyl(Vector((vx, ya, zt - 0.06)), Vector((vx, ya, zt + 0.03)), 0.018, Z_VALVE, 10)
        k.cyl(Vector((vx, ya, zt + 0.03)), Vector((vx, ya, zt + 0.10)), 0.026, Z_VALVE, 12)
        k.cyl(Vector((vx, ya, zt - 0.06)), Vector((x1 if valve_side > 0 else x0, ya, zt - 0.06)), 0.009, Z_PIPE_W, 8)
        k.cyl(Vector((vx, ya, zf)), Vector((vx, ya, zt - 0.06)), 0.009, Z_PIPE_W, 8)
    else:
        B(k, (a_top0, x0, zt), (a_top1, x1, zt + 0.006), Z_RADIATOR)
        vy = x1 + 0.05 if valve_side > 0 else x0 - 0.05
        xa = y_wall + n_sign * 0.08
        k.cyl(Vector((xa, vy, zf)), Vector((xa, vy, zt - 0.06)), 0.009, Z_PIPE_W, 8)
        k.cyl(Vector((xa, vy, zb + 0.02)), Vector((xa, x1 if valve_side > 0 else x0, zb + 0.02)), 0.009, Z_PIPE_W, 8)
        k.cyl(Vector((xa, vy, zt - 0.06)), Vector((xa, vy, zt + 0.03)), 0.018, Z_VALVE, 10)
        k.cyl(Vector((xa, vy, zt + 0.03)), Vector((xa, vy, zt + 0.10)), 0.026, Z_VALVE, 12)
        k.cyl(Vector((xa, vy, zt - 0.06)), Vector((xa, x1 if valve_side > 0 else x0, zt - 0.06)), 0.009, Z_PIPE_W, 8)


def wall_plane(p, n):
    """the room face behind a wall-mounted point p (n = the face's normal into the room)"""
    import main_spec as S
    ax = 0 if abs(n[0]) > 0.5 else 1
    cands = set()
    for R in S.ROOMS.values():
        cands |= ({R['x0'], R['x1']} if ax == 0 else {R['y0'], R['y1']})
    behind = [c for c in cands if (p[ax] - c) * n[ax] >= -1e-4]
    return min(behind, key=lambda c: abs(p[ax] - c))


def rocker_switch(name, n, note, k_room=None, double=False, pair=None):
    """light / shutter switch: the IX rocker round its Update 3 pivot; behind it a flush plate on the wall (k_room) or,
    where the pivot stands well off the wall, the grey surface box of an open installation; pair = the switch above it
    (a light switch with the shutter switch): one double plate under both"""
    k = ix_part(name, note=note)
    p = Vector(X.IX[name]['pivot'])
    n = Vector(n)
    u = Vector((0, 0, 1)).cross(n).normalized()
    R = Matrix((u, Vector((0, 0, 1)), n)).transposed()
    rocker(k, p, n, u, (0.036, 0.046, 0.010), Z_ROCKER, 10.0)
    ax = 0 if abs(n.x) > 0.5 else 1
    w = wall_plane(p, n)
    gap = abs(p[ax] - w) - 0.005
    if k_room is not None and gap > 0.001:
        c = p.copy()
        c[ax] = w + n[ax] * gap / 2
        wid, hgt = 0.08, 0.08
        if pair:
            q = Vector(X.IX[pair]['pivot'])
            m = (p + q) / 2
            c.z = m.z
            c[1 - ax] = m[1 - ax]
            wid = abs((q - p).dot(u)) + 0.08
            hgt = abs(q.z - p.z) + 0.08
        elif double:
            hgt = 0.16
        VM.obox(k_room, c, (wid, hgt, gap), Z_SWITCHP if gap < 0.03 else Z_SOCKET, R)


def convex_prism(k, ring, d, zone):
    """a prism over a convex ring of points, extruded by d; the faces turned outwards"""
    a = [Vector(q) for q in ring]
    b = [q + d for q in a]
    c = (sum(a, Vector()) + sum(b, Vector())) / (2 * len(a))

    def add(pts):
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if nrm.dot(sum(pts, Vector()) / len(pts) - c) < 0:
            pts = list(reversed(pts))
        k.poly(pts, zone)
    add(a)
    add(b)
    for i in range(len(a)):
        j = (i + 1) % len(a)
        add([a[i], a[j], b[j], b[i]])


def rocker(k, p, n, u, size, zone, tilt, back=None):
    """a rocker round its pivot p (the axis along u): a flat face toward n, its back two planes falling away from the
    middle by tilt (deg, a little more than the rocker's travel) so it rocks without touching what lies behind;
    size = (width along u, height, depth along n); back = the back's distance behind p (default: half the depth)"""
    w, h, t = size
    up = n.cross(u).normalized()
    if up.z < 0:
        up = -up
    bk = t / 2 if back is None else back
    e = (h / 2) * math.tan(math.radians(tilt))
    prof = [(-h / 2, t - bk), (-h / 2, -bk + e), (0.0, -bk), (h / 2, -bk + e), (h / 2, t - bk)]
    ring = [p - u * (w / 2) + up * zz + n * nn for (zz, nn) in prof]
    convex_prism(k, ring, u * w, zone)


def socket_outlet(k, c, n, kind='flush'):
    """a socket outlet: flush plate (offices) or a grey splash-proof surface box (plant rooms, garage); CEE: blue / red"""
    c, n = Vector(c), Vector(n)
    u = Vector((0, 0, 1)).cross(n).normalized()
    R = Matrix((u, Vector((0, 0, 1)), n)).transposed()
    if kind == 'flush':
        VM.obox(k, c + n * 0.004, (0.08, 0.08, 0.008), Z_SOCKET, R)
        k.cyl(c + n * 0.008, c + n * 0.010, 0.022, Z_SOCKET, 12)
    elif kind == 'surface':
        VM.obox(k, c + n * 0.025, (0.08, 0.08, 0.05), Z_SOCKET, R)
        VM.obox(k, c + n * 0.052, (0.07, 0.07, 0.006), Z_SOCKET, R)
    else:
        zone = Z_DRUM_B if kind == 'cee_blue' else Z_DRUM_R
        VM.obox(k, c + n * 0.03, (0.09, 0.10, 0.06), zone, R)
        k.cyl(c + n * 0.06, c + n * 0.10, 0.03, zone, 12)


def smoke_detector(k, c):
    c = Vector(c)
    k.cyl(c, c - Vector((0, 0, 0.012)), 0.055, Z_SMOKE, 16)
    k.cyl(c - Vector((0, 0, 0.012)), c - Vector((0, 0, 0.045)), 0.045, Z_SMOKE, 16)


def extinguisher(k, c, n, h=0.60):
    """a 6 kg extinguisher on a wall bracket (red cylinder, black hose, gauge), the F001 sign above (panel atlas)"""
    c, n = Vector(c), Vector(n)
    base = c + n * 0.09
    k.cyl(base, base + Vector((0, 0, h - 0.12)), 0.075, Z_EXTING, 14)
    k.lathe(base + Vector((0, 0, h - 0.12)), Vector((0, 0, 1)), [(0.0, 0.075), (0.05, 0.06), (0.08, 0.03), (0.10, 0.0)],
            Z_EXTING, 14, cap0=False)
    k.cyl(base + Vector((0, 0, h - 0.04)), base + Vector((0, 0, h + 0.02)), 0.018, Z_STEELBLK, 8)
    side = Vector((0, 0, 1)).cross(n).normalized()
    k.tube([base + Vector((0, 0, h)) + side * 0.02, base + Vector((0, 0, h - 0.05)) + side * 0.09,
            base + Vector((0, 0, 0.25)) + side * 0.09], 0.008, Z_RUBBERB, 6)
    B(k, c + side * -0.03 + Vector((0, 0, h * 0.55)), c + n * 0.02 + side * 0.03 + Vector((0, 0, h * 0.60)), Z_STEELBLK)


def call_point(k, c, n):
    wall_box(k, c, n, 0.09, 0.09, 0.05, Z_CALLPT)


def alarm_bell(k, c, n):
    c, n = Vector(c), Vector(n)
    wall_box(k, c, n, 0.06, 0.06, 0.03, Z_BELL)
    k.lathe(c + n * 0.03, n, [(0.0, 0.0), (0.0, 0.08), (0.05, 0.075), (0.06, 0.0)], Z_BELL, 14, cap0=False)


def speaker(k, c, n):
    """a ceiling-corner PA horn box (grey) on a bracket"""
    c, n = Vector(c), Vector(n)
    wall_box(k, c, n, 0.20, 0.26, 0.10, Z_SPEAKER)


def phone(k, c, n):
    """a 70s wall telephone (beige), the handset in its cradle, the coiled cord"""
    c, n = Vector(c), Vector(n)
    wall_box(k, c, n, 0.16, 0.22, 0.07, Z_PHONE)
    u = Vector((0, 0, 1)).cross(n).normalized()
    k.cyl(c + n * 0.09 + u * 0.06 + Vector((0, 0, 0.06)), c + n * 0.09 - u * 0.06 + Vector((0, 0, 0.06)), 0.02, Z_PHONE, 8)
    k.tube([c + n * 0.08 + u * 0.07 + Vector((0, 0, 0.0)), c + n * 0.11 + u * 0.08 + Vector((0, 0, -0.25)),
            c + n * 0.08 + u * 0.06 + Vector((0, 0, -0.40))], 0.006, Z_CABLE, 5)


def clock(k, c, n, r=0.15):
    c, n = Vector(c), Vector(n)
    k.cyl(c, c + n * 0.04, r, Z_STEELBLK, 20)
    k.cyl(c + n * 0.04, c + n * 0.045, r * 0.9, Z_CLOCK, 20)


def first_aid(k, c, n):
    wall_box(k, c, n, 0.30, 0.22, 0.12, Z_FIRSTAID)


def conduit_run(k, pts, r=0.010):
    K.conduit(k, pts, r=r, zone=Z_PIPE_W, clamps=0.5)


def junction_box(k, c, n, d=0.05):
    """a grey surface box on the wall; a switch's rocker (an Update 3 pivot) standing on it: its front is the rocker's
    back, so the rocker rocks clear of it"""
    c, n = Vector(c), Vector(n)
    for nm, it in X.IX.items():
        if nm.startswith(('IX_LightSwitch_', 'IX_ShutterSwitch_')):
            q = Vector(it['pivot'])
            off = (q - c).dot(n)
            if ((q - c) - n * off).length < 0.03 and 0.0 < off < d + 0.02:
                d = off - 0.005
    wall_box(k, c, n, 0.08, 0.08, d, Z_SOCKET)
