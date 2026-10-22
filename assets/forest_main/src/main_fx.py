"""Main building — the 64 light fixtures of Update 3 (FX_*), rebuilt at their Update 3 transforms: bulkheads (wall /
ceiling), raster louvre luminaires, battens, enamel pendants, desk lamps, exit signs, emergency lights, wall floods, the
mast's obstruction light. Each fixture is one object FX_<n> (pivot = Update 3's, body in the MainFx atlas) plus its lit
part FX_<n>__lit with the Update 3 material name the game switches (M_FX_Globe, M_FX_Tube, M_FX_Diffuser, M_FX_Bulb,
M_FX_Exit, M_FX_EmergencyLens, M_FX_Halogen, M_FX_Red, M_LEDOn): main_build joins the two into one mesh with two
materials, as in Update 3. The lights themselves are the game's (Forest_Layout prefabLights): the lit parts sit where
those lights are."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, box6, face, Z_GALV, Z_STEELBLK
import van3_mech as VM
import main_fx_u3 as D

(Z_FX_ALU, Z_FX_WHITE, Z_FX_GREEN, Z_FX_ENAMELW, Z_FX_POLY, Z_FX_REFL, Z_FX_LOUVRE, Z_FX_FLOOD, Z_FX_CABLE,
 Z_FX_CAGE, Z_FX_CHROME) = range(500, 511)
DRAFT_COL = {Z_FX_ALU: (150, 152, 150), Z_FX_WHITE: (232, 232, 228), Z_FX_GREEN: (60, 96, 70), Z_FX_ENAMELW: (240, 240, 236),
             Z_FX_POLY: (200, 200, 196), Z_FX_REFL: (210, 212, 214), Z_FX_LOUVRE: (220, 222, 224), Z_FX_FLOOD: (50, 52, 54),
             Z_FX_CABLE: (24, 24, 24), Z_FX_CAGE: (110, 112, 110), Z_FX_CHROME: (200, 202, 204)}
LIT = {'globe': 'M_FX_Globe', 'tube': 'M_FX_Tube', 'diffuser': 'M_FX_Diffuser', 'bulb': 'M_FX_Bulb', 'exit': 'M_FX_Exit',
       'emlens': 'M_FX_EmergencyLens', 'halogen': 'M_FX_Halogen', 'red': 'M_FX_Red', 'led': 'M_LEDOn'}


def frame(n, up_hint=(0, 0, 1)):
    """local axes for a mounting normal n: (u along the surface, v the surface's 'up', n out)"""
    n = Vector(n).normalized()
    up = Vector(up_hint)
    if abs(n.dot(up)) > 0.9:
        up = Vector((0, 1, 0))
    u = up.cross(n).normalized()
    v = n.cross(u).normalized()
    return u, v, n


def body(r):
    return kb(r['name'], 'MainFx')


def lit(r, kind):
    k = kb(r['name'] + '__lit', 'lens:' + kind)
    part(r['name'] + '__lit', 'static', r['loc'], parent=r['name'],
         note=f'lit part of {r["name"]} (material {LIT[kind]}); joined into it at export')
    return k


def register(r, note):
    L = r.get('light')
    extra = {}
    if L:
        extra = dict(light=dict(L))
    part(r['name'], 'static', r['loc'], parent='BaseMain', note=note, fixture=r['type'], **extra)


def oval(c, u, v, ru, rv, seg=20):
    return [c + u * (ru * math.cos(t)) + v * (rv * math.sin(t)) for t in (2 * math.pi * i / seg for i in range(seg))]


def loft_oval(k, c, u, v, n, rings, zone, seg=20, cap0=None, cap1=None):
    """rings = [(along n, ru, rv)] -> a closed loft of ovals"""
    pts = [oval(c + n * a, u, v, ru, rv, seg) for a, ru, rv in rings]
    k.loft(pts, [zone] * (len(pts) - 1), closed=True, cap0=cap0, cap1=cap1)


# ---------------------------------------------------------------- bulkheads (wall and ceiling)
def fx_bulkhead(r, ceiling=False):
    """the cast-aluminium oval bulkhead (27 x 16 cm, 13 cm deep): base with its rim, the glass half-globe, the cage"""
    c = Vector(r['loc'])
    u, v, n = frame(r['n'], (0, 1, 0) if ceiling else (0, 0, 1))
    if ceiling:
        u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
        n = Vector((0, 0, -1))
        u = v.cross(n).normalized() * -1 if False else u
    k = body(r)
    loft_oval(k, c, u, v, n, [(0.0, 0.135, 0.081), (0.03, 0.135, 0.081), (0.04, 0.126, 0.072)], Z_FX_ALU, 24,
              cap0=Z_FX_ALU, cap1=Z_FX_ALU)
    g = lit(r, 'globe')
    rings = [(0.04 + 0.092 * math.sin(a), 0.112 * math.cos(a), 0.062 * math.cos(a)) for a in
             (0.0, 0.35, 0.7, 1.0, 1.25, 1.45)]
    loft_oval(g, c, u, v, n, rings, 0, 20, cap1=0)
    for s in (-0.06, 0.0, 0.06):                                     # the cage's bars across the globe
        pts = []
        for i in range(9):
            a = -1.35 + 2.7 * i / 8
            w = 0.116 * math.sin(a)
            hgt = 0.04 + 0.097 * math.cos(a) * math.sqrt(max(0.0, 1 - (s / 0.066) ** 2))
            pts.append(c + u * w + v * s + n * hgt)
        k.tube(pts, 0.004, Z_FX_CAGE, 5)
    loft_oval(k, c, u, v, n, [(0.036, 0.122, 0.069), (0.046, 0.122, 0.069), (0.046, 0.114, 0.061), (0.036, 0.114, 0.061)],
              Z_FX_CAGE, 24)
    register(r, 'bulkhead lamp (cast aluminium, glass globe, cage)')


def fx_bulkheadceiling(r):
    fx_bulkhead(r, ceiling=True)


# ---------------------------------------------------------------- raster louvre luminaire (62 x 62, 8 cm)
def fx_raster(r):
    c = Vector(r['loc'])                                             # the ceiling plane (top)
    lo, hi = Vector(r['lo']), Vector(r['hi'])
    k = body(r)
    t = 0.008
    zt, zb = hi.z, lo.z
    box6(k, (lo.x, lo.y, zt - t), (hi.x, hi.y, zt), Z_FX_WHITE)
    for (a, b) in (((lo.x, lo.y), (hi.x, lo.y + t)), ((lo.x, hi.y - t), (hi.x, hi.y)), ((lo.x, lo.y + t), (lo.x + t, hi.y - t)),
                   ((hi.x - t, lo.y + t), (hi.x, hi.y - t))):
        box6(k, (a[0], a[1], zb), (b[0], b[1], zt - t), Z_FX_WHITE)
    # the reflector troughs over the two tubes, the louvre grid, the tubes (FX_Raster_14 has none: broken)
    for s in (-1, 1):
        yc = c.y + s * 0.15
        for side in (-1, 1):
            y0, y1 = yc + side * 0.02, yc + side * 0.14
            face(k, [(lo.x + t, y0, zt - t), (hi.x - t, y0, zt - t), (hi.x - t, y1, zb + 0.022), (lo.x + t, y1, zb + 0.022)],
                 Z_FX_REFL, (0, -side * 0.5, -1))
    for i in range(1, 6):
        y = lo.y + i * (hi.y - lo.y) / 6
        box6(k, (lo.x + t, y - 0.002, zb), (hi.x - t, y + 0.002, zb + 0.03), Z_FX_LOUVRE)
    for i in range(1, 8):
        x = lo.x + i * (hi.x - lo.x) / 8
        box6(k, (x - 0.002, lo.y + t, zb), (x + 0.002, hi.y - t, zb + 0.03), Z_FX_LOUVRE)
    if r.get('light'):
        g = lit(r, 'tube')
        for s in (-1, 1):
            g.cyl(Vector((lo.x + 0.03, c.y + s * 0.15, zb + 0.045)), Vector((hi.x - 0.03, c.y + s * 0.15, zb + 0.045)), 0.013,
                  0, 10)
    note = 'raster luminaire (2 tubes, parabolic louvre)' if r.get('light') else 'raster luminaire, tubes missing (no light)'
    register(r, note)


# ---------------------------------------------------------------- battens (opal diffuser)
def fx_batten(r, wide=False):
    lo, hi = Vector(r['lo']), Vector(r['hi'])
    c = Vector(r['loc'])
    along_x = (hi.x - lo.x) > (hi.y - lo.y)
    L = (hi.x - lo.x) if along_x else (hi.y - lo.y)
    W = (hi.y - lo.y) if along_x else (hi.x - lo.x)
    a = Vector((1, 0, 0)) if along_x else Vector((0, 1, 0))
    b = Vector((0, 0, 1)).cross(a)                                   # (a, b, z) right-handed whichever way it runs
    zt = c.z
    zb = lo.z
    m = (lo + hi) / 2
    m.z = zt
    k = body(r)
    hh = 0.05
    R = Matrix((a, b, Vector((0, 0, 1)))).transposed()
    VM.obox(k, m - Vector((0, 0, hh / 2)), (L - 0.02, W, hh), Z_FX_POLY, R)
    for s in (-1, 1):                                                # end caps, the clips
        VM.obox(k, m + a * s * (L / 2 - 0.012) - Vector((0, 0, (zt - zb) / 2)), (0.024, W + 0.004, zt - zb), Z_FX_POLY, R)
        for t_ in (0.25, 0.75):
            p = m + a * s * (L / 2 * t_) - Vector((0, 0, hh + 0.004))
            VM.obox(k, p, (0.02, W + 0.006, 0.008), Z_GALV, R)
    k.cyl(m + a * (L / 2 - 0.05) - Vector((0, 0, 0.01)), m + a * (L / 2 + 0.10) + Vector((0, 0, -0.01)), 0.005,
          Z_FX_CABLE, 5)
    g = lit(r, 'diffuser')
    d = zt - hh - zb
    ring = []
    for i in range(9):
        t_ = math.pi * i / 8
        ring.append((math.cos(t_) * (W / 2 - 0.004), -math.sin(t_) * d))
    rings = []
    for s in (-1, 1):
        x0 = m + a * s * (L / 2 - 0.024) - Vector((0, 0, hh))
        rings.append([x0 + b * yy + Vector((0, 0, zz)) for yy, zz in ring])
    g.loft(rings, [0], closed=False, cap0=0, cap1=0)
    register(r, 'fluorescent batten, opal diffuser' + (' (wide)' if wide else ''))


def fx_fluorbatten(r):
    fx_batten(r)


def fx_fluorbatten2(r):
    fx_batten(r, wide=True)


# ---------------------------------------------------------------- enamel pendant
def fx_pendant(r):
    """ceiling rose, the cable, the enamel shade (green outside, white inside, 41 cm), the bulb at the light"""
    c = Vector(r['loc'])
    lo = Vector(r['lo'])
    L = r.get('light')
    bulb_z = L['p'][2] if L else lo.z + 0.07
    rim = lo.z
    top = rim + 0.17
    k = body(r)
    k.cyl(c, c - Vector((0, 0, 0.03)), 0.05, Z_FX_ALU, 14)
    k.cyl(c - Vector((0, 0, 0.03)), Vector((c.x, c.y, top + 0.05)), 0.004, Z_FX_CABLE, 5)
    k.cyl(Vector((c.x, c.y, top + 0.05)), Vector((c.x, c.y, top - 0.01)), 0.022, Z_FX_ALU, 12)
    prof = [(0.0, 0.205), (0.03, 0.19), (0.08, 0.14), (0.13, 0.07), (0.17, 0.035)]
    k.lathe(Vector((c.x, c.y, rim)), Vector((0, 0, 1)), prof, Z_FX_GREEN, 20, cap0=False, cap1=True)
    k.lathe(Vector((c.x, c.y, rim + 0.002)), Vector((0, 0, 1)), [(a, rr - 0.004) for a, rr in reversed(prof)],
            Z_FX_ENAMELW, 20, cap0=False, cap1=False)                   # the white inside faces inward
    g = lit(r, 'bulb')
    g.lathe(Vector((c.x, c.y, bulb_z - 0.035)), Vector((0, 0, 1)), [(0.0, 0.0), (0.015, 0.028), (0.04, 0.032), (0.065, 0.02),
                                                                    (0.08, 0.013)], 0, 12, cap0=False, cap1=True)
    register(r, 'enamel pendant lamp')


# ---------------------------------------------------------------- desk lamp
def fx_desklamp(r):
    """green enamel desk lamp: base on the desk, the jointed arm, the shade aimed along its light"""
    L = r['light']
    p, d = Vector(L['p']), Vector(L['d']).normalized()
    base = Vector(r['loc'])
    if r['name'] == 'FX_DeskLamp_36':                                # Update 3's base hung off the desk's edge: on the
        base = Vector((5.15, 3.62, base.z))                          # desk, clear of the dressing (envelope, medicine)
    if r['name'] == 'FX_DeskLamp_6':                                 # Update 3's clipboard lies where its base stood
        base = Vector((-0.62, -1.47, base.z))
    k = body(r)
    k.lathe(base, Vector((0, 0, 1)), [(0.0, 0.075), (0.012, 0.075), (0.022, 0.06), (0.03, 0.02)], Z_FX_GREEN, 16)
    joint = base + Vector((0, 0, 0.03))
    elbow = Vector((base.x + (p.x - base.x) * 0.35, base.y + (p.y - base.y) * 0.35, p.z + 0.17))
    head = p - d * 0.11
    k.tube([joint, elbow, head], 0.007, Z_GALV, 6)
    k.lathe(elbow, Vector((1, 0, 0)), [(-0.012, 0.012), (0.012, 0.012)], Z_FX_ALU, 8)
    k.lathe(head, d, [(-0.02, 0.018), (0.0, 0.03), (0.06, 0.055), (0.11, 0.072)], Z_FX_GREEN, 16, cap0=True, cap1=False)
    k.lathe(head + d * 0.002, d, [(0.106, 0.069), (0.06, 0.052), (0.0, 0.027), (-0.015, 0.016)], Z_FX_ENAMELW, 16,
            cap0=False, cap1=False)
    g = lit(r, 'bulb')
    g.lathe(p - d * 0.075, d, [(0.0, 0.0), (0.01, 0.02), (0.035, 0.024), (0.05, 0.012)], 0, 12, cap0=False, cap1=True)
    register(r, 'desk lamp (green enamel)')


# ---------------------------------------------------------------- exit sign, emergency light
def fx_exitsign(r):
    c = Vector(r['loc'])
    lo, hi = Vector(r['lo']), Vector(r['hi'])
    u, v, n = frame(r['n'])
    w = abs((hi - lo).dot(u))
    h = hi.z - lo.z
    dpt = abs((hi - lo).dot(n))
    m = (lo + hi) / 2
    mw = m - n * (m - c).dot(n)                                      # its centre on the wall
    R = Matrix((u, v, n)).transposed()
    k = body(r)
    VM.obox(k, mw + n * dpt / 2, (w, h, dpt), Z_FX_WHITE, R)
    g = lit(r, 'exit')                    # the front, UV 0..1 as Update 3's (M_FX_Exit samples T_FX_Exit_A_px over it)
    g.quad_uv(mw + n * (dpt + 0.0006), n, w - 0.03, h - 0.03, (0.0, 0.0, 1.0, 1.0), 0, up=Vector((0, 0, 1)))
    register(r, 'exit sign (battery, always lit)')


def fx_emergencylight(r):
    c = Vector(r['loc'])
    lo, hi = Vector(r['lo']), Vector(r['hi'])
    u, v, n = frame(r['n'])
    w = abs((hi - lo).dot(u))
    h = hi.z - lo.z
    dpt = abs((hi - lo).dot(n))
    m = (lo + hi) / 2
    mw = m - n * (m - c).dot(n)
    R = Matrix((u, v, n)).transposed()
    k = body(r)
    VM.obox(k, mw + n * dpt / 2 + Vector((0, 0, 0.012)), (w, h - 0.024, dpt), Z_FX_WHITE, R)
    g = lit(r, 'emlens')
    VM.obox(g, mw + n * dpt * 0.55 - Vector((0, 0, h / 2 - 0.012)), (w - 0.03, 0.024, dpt * 0.8), 0, R)
    led = lit_extra(r, 'led')
    led.cyl(mw + n * dpt + u * (w / 2 - 0.03) + Vector((0, 0, 0.02)), mw + n * (dpt + 0.004) + u * (w / 2 - 0.03) +
            Vector((0, 0, 0.02)), 0.004, 0, 8)
    register(r, 'emergency light (battery)')


def lit_extra(r, kind):
    k = kb(r['name'] + '__lit2', 'lens:' + kind)
    part(r['name'] + '__lit2', 'static', r['loc'], parent=r['name'],
         note=f'second lit part of {r["name"]} (material {LIT[kind]}); joined into it at export')
    return k


# ---------------------------------------------------------------- wall flood, obstruction light
def fx_wallflood(r):
    """the halogen flood on its U-bracket: finned body, the glass toward its light, the cable"""
    c = Vector(r['loc'])
    L = r['light']
    p, d = Vector(L['p']), Vector(L['d']).normalized()
    u, v, n = frame(r['n'])
    k = body(r)
    arm = c + n * 0.10
    k.cyl(c, arm, 0.012, Z_GALV, 8)
    VM.obox(k, c + n * 0.004, (0.08, 0.10, 0.008), Z_GALV, Matrix((u, v, n)).transposed())
    for s in (-1, 1):
        k.cyl(arm + u * s * 0.15, p - d * 0.06 + u * s * 0.15, 0.008, Z_GALV, 6)
    k.cyl(arm - u * 0.15, arm + u * 0.15, 0.008, Z_GALV, 6)
    up = d.cross(u).normalized()
    R = Matrix((u, up, d)).transposed()
    VM.obox(k, p - d * 0.075, (0.27, 0.18, 0.11), Z_FX_FLOOD, R)
    for i in range(5):
        VM.obox(k, p - d * 0.135 + up * (-0.06 + i * 0.03), (0.25, 0.008, 0.03), Z_FX_FLOOD, R)
    g = lit(r, 'halogen')
    VM.obox(g, p - d * 0.018, (0.23, 0.14, 0.004), 0, R)
    k.tube([p - d * 0.13 - up * 0.08, c + n * 0.03 - v * 0.15, c - v * 0.40], 0.005, Z_FX_CABLE, 5)
    register(r, 'halogen wall flood')


def fx_obstruction(r):
    c = Vector(r['loc'])
    k = body(r)
    k.cyl(c, c + Vector((0, 0, 0.05)), 0.065, Z_FX_FLOOD, 14)
    g = lit(r, 'red')
    g.lathe(c + Vector((0, 0, 0.05)), Vector((0, 0, 1)), [(0.0, 0.058), (0.05, 0.055), (0.08, 0.04), (0.095, 0.0)], 0, 14,
            cap0=True)
    register(r, 'aviation obstruction light (red, no switch)')


def build_fx():
    for r in D.FX:
        globals()['fx_' + r['type'].lower()](r)
