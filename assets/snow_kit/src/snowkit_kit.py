"""Snow kit geometry (snowkit_spec.ITEMS): every model in its own frame at the origin (z up, front -y; origins as the spec
says), one KB per object (gen_kit registry: kb / part / socket), atlases: 'Kit' (baked), 'panel' (labels, signs, the
dial, the camera glass), 'lens:<Kind>' (lamp lenses, lit / off), 'screen' (the CRT glass, UV 0..1), 'glow' (halo cards).
Item roots are named as the items; the build parents every part under its root and lays the roots out for the bake.
  K1 camera head + wall and pole brackets; K2 CRT monitor; K3 console bodies (2 / 4 slots), the button, labels;
  K4 rotary phone; K5 distribution cabinet (door, battery shelf, clamps, NETZ / BATTERIE switch, power lamp);
  K6 junction box; K7 conduit pieces; K8 wooden poles (plain, with the barrel transformer); K9 roof stand;
  K10 electric lock (body, strike with its lamp); K11 beacon; K12 the steel mast and its attachments (side: floodlight,
  horn loudspeaker, Yagi; top: street lamp, radio antenna, motor siren); K9 also the overhead wires as models.
Battery (the van's, Van/Data/parts.json): 0.175 x 0.264 x 0.278 m (x, up, z in its own Unity frame), origin at the
bottom middle, the clamp posts at (+0.04, 0.217, -+0.105): in the cabinet it stands with its posts to the front."""
import math
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, quad, KBS, CONTRACT, LAMPS, merge_kb
from van2_kit import ZERO, KB
import snowkit_spec as S
from snowkit_spec import (Z_KCAB, Z_KCABIN, Z_KGALV, Z_KSTEEL, Z_KBLACK, Z_KPLAST, Z_KCAM, Z_KCRT, Z_KBEZEL, Z_KCONS, Z_KALU,
                          Z_KBTN, Z_KPHONE, Z_KPOLE, Z_KPORC, Z_KTRAFO, Z_KCOPPER, Z_KREDC, Z_KCABLE, Z_KHANDLE, Z_KBRKR,
                          Z_KCONC)

TAU = 2 * math.pi
V = Vector
COLLIDERS = []                 # (name, parent, (x0, x1, y0, y1, z0, z1) in the item frame, rotation xyz deg or None)
ITEM_OF = {}                   # object / socket name -> item name
WIRE_PTS = {}                  # item -> [(socket, pos)] attach points of overhead wires


def uv(name):
    """panel region -> (u0, v0, u1, v1), half-texel inset (the same as kpp_tex.uv / van2_tex.uv)"""
    (x0, y0, x1, y1), _, _ = S.PANEL[name]
    n = S.PANEL_N
    return ((x0 + 0.5) / n, 1 - (y1 - 0.5) / n, (x1 - 0.5) / n, 1 - (y0 + 0.5) / n)


_CUR = [None]


def item(name):
    _CUR[0] = name


def P_(name, kind, pivot, axis=None, rng=None, **kw):
    part(name, kind, pivot, axis, rng, **kw)
    ITEM_OF[name] = _CUR[0]


def S_(name, pos, kind, note='', parent=None, **kw):
    socket(name, pos, kind, note=note, parent=parent, **kw)
    ITEM_OF[name] = _CUR[0]


def col(name, parent, box, rot=None):
    COLLIDERS.append((name, parent, box, rot))
    ITEM_OF['COL_' + name] = _CUR[0]


def inner_box(k, lo, hi, zones, skip=()):
    """the faces of the box lo..hi turned inward (an inside seen from within)"""
    lo, hi = V(lo), V(hi)
    c = [V((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    if isinstance(zones, (int, float)):
        zones = {'*': zones}
    for key, (q, n) in K.FACES6.items():
        if key in skip:
            continue
        face(k, [c[i] for i in q], zones.get(key, zones.get('*')), tuple(-a for a in n))


def uv_cyl(k, c, h0, h1, rect, axis=(0, 0, 1)):
    """cylindrical UVs on every face of k: u round the axis, v along it from h0 to h1"""
    c, ax = V(c), V(axis).normalized()
    e1 = V((1, 0, 0)) if abs(ax.x) < 0.9 else V((0, 1, 0))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = rect
    for f in k.bm.faces:
        cen = f.calc_center_median() - c
        af = math.atan2(cen.dot(e2), cen.dot(e1))
        for l in f.loops:
            d = l.vert.co - c
            a = math.atan2(d.dot(e2), d.dot(e1))
            if a - af > math.pi:                       # keep a face on one side of the seam
                a -= TAU
            elif af - a > math.pi:
                a += TAU
            t = min(max((d.dot(ax) - h0) / (h1 - h0), 0.0), 1.0)
            l[k.uvl].uv = (u0 + (u1 - u0) * ((a / TAU) % 1.0 if abs(a) < math.pi else (a / TAU + 1.0) % 1.0), v0 + (v1 - v0) * t)


def band_ring(k, c, axis, r, w, t, zone, seg=12):
    """flat strap round a circle (a pole clamp band): radius r (inner), width w along the axis, thickness t"""
    ax = V(axis).normalized()
    e1 = V((1, 0, 0)) if abs(ax.x) < 0.9 else V((0, 1, 0))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    c = V(c)
    k.lathe(c - ax * (w / 2), ax, [(0.0, r + t), (w, r + t)], zone, seg, cap0=False, cap1=False)
    k.lathe(c - ax * (w / 2), ax, [(w, r), (0.0, r)], zone, seg, cap0=False, cap1=False)
    for h in (0.0, w):                                  # the two edges (annuli)
        ro = [c - ax * (w / 2) + ax * h + (e1 * math.cos(TAU * i / seg) + e2 * math.sin(TAU * i / seg)) * (r + t) for i in range(seg)]
        ri = [c - ax * (w / 2) + ax * h + (e1 * math.cos(TAU * i / seg) + e2 * math.sin(TAU * i / seg)) * r for i in range(seg)]
        for i in range(seg):
            j = (i + 1) % seg
            face(k, [ro[i], ro[j], ri[j], ri[i]], zone, ax * (1 if h > 0 else -1))


def insulator(k, base, h=0.12, r=0.045, zone=Z_KPORC, pin=True):
    """pin insulator (porcelain, two sheds, the wire groove on top) on a steel pin; returns the wire point"""
    base = V(base)
    if pin:
        k.cyl(base, base + V((0, 0, 0.05)), 0.010, Z_KGALV, 6)
    b = base + V((0, 0, 0.03))
    prof = [(0.0, r * 0.45), (0.02, r * 0.55), (0.03, r), (0.045, r * 0.95), (0.055, r * 0.55), (0.075, r * 0.85),
            (0.088, r * 0.80), (0.095, r * 0.50), (h * 0.86, r * 0.48), (h * 0.90, r * 0.36), (h, r * 0.42), (h, 0.0)]
    k.lathe(b, (0, 0, 1), prof, zone, 10, cap0=True, cap1=False)
    return b + V((0, 0, h * 0.90))


def spool(k, c, axis, r=0.032, L=0.07, zone=Z_KPORC):
    """spool (shackle) insulator on its bolt: returns the groove centre"""
    ax = V(axis).normalized()
    c = V(c)
    k.lathe(c - ax * (L / 2), ax, [(0.0, r), (0.012, r), (0.02, r * 0.62), (L - 0.02, r * 0.62), (L - 0.012, r), (L, r)], zone, 10)
    return c


def lamp_lens(name, kind, c, n, r, parent, dome=0.006, seg=10, note=''):
    """indicator lens (lit / off material by kind) as its own object, with a black bezel ring in the parent's KB"""
    L = kb(name, 'lens:' + kind)
    L.disc_uv(V(c), V(n), r, uv(S.LAMP_KINDS[kind]), seg, dome=dome)
    P_(name, 'static', V(c), parent=parent, note=note or f'indicator lens: M_Kit_Lamp_{kind} (lit) / M_Kit_Lamp_{kind}_Off')
    return L


# ================================================================ K1 the camera
def camera():
    item('Kit_Camera_Head')
    k = kb('Kit_Camera_Head', 'Kit')
    # housing (off-white aluminium extrusion) on the swivel boss; the sunshield over it; the rear gland and cable
    k.cyl(V((0, 0, 0.0)), V((0, 0, 0.036)), 0.018, Z_KBLACK, 10)
    k.box(-0.025, 0.025, -0.04, 0.04, 0.030, 0.038, Z_KCAM)
    VM.rbox(k, (0, -0.07, 0.0805), (0.095, 0.26, 0.085), Z_KCAM, r=0.014, ch=0.006, axis='y')
    k.box(-0.0585, 0.0585, -0.245, 0.045, 0.1225, 0.1285, Z_KCAM)
    for sx in (-1, 1):                                       # the shield's side flanges
        k.box(sx * 0.0585 - 0.002, sx * 0.0585 + 0.002, -0.245, 0.0, 0.105, 0.1255, Z_KCAM)
    k.box(-0.0585, 0.0585, -0.247, -0.243, 0.112, 0.1285, Z_KCAM)       # the shield's front lip
    k.lathe(V((0, -0.2005, 0.0805)), (0, -1, 0), [(0.0, 0.034), (0.004, 0.034), (0.004, 0.030), (0.0, 0.030)], Z_KBLACK, 12,
            cap0=False, cap1=False)
    k.cyl(V((0, 0.06, 0.07)), V((0, 0.078, 0.07)), 0.011, Z_KBLACK, 8)
    k.tube([V((0, 0.078, 0.07)), V((0, 0.095, 0.06)), V((0, 0.07, 0.02)), V((0, 0.03, 0.012))], 0.004, Z_KCABLE, 5, caps=False)
    g = kb('Kit_Camera_Head_Glass', 'panel')
    quad(g, (0, -0.2008, 0.0805), (0, -1, 0), 0.058, 0.058, uv('l_cam'))
    P_('Kit_Camera_Head_Glass', 'static', (0, -0.2008, 0.0805), parent='Kit_Camera_Head', note='the front glass (panel atlas)')
    lamp_lens('Lens_CameraLED', 'Red', (0.032, -0.2012, 0.050), (0, -1, 0), 0.0045, 'Kit_Camera_Head', dome=0.003, seg=8,
              note='the red LED under the glass: M_Kit_Lamp_Red with the power, M_Kit_Lamp_Red_Off without')
    P_('Kit_Camera_Head', 'static', (0, 0, 0), note='camera head; origin = the swivel point under the housing (it goes on the '
                                                      'bracket\'s Mount_Head); looks along -y')
    S_('CAM_View', (0, -0.205, 0.0805), 'camera', parent='Kit_Camera_Head', dir=(0, -1, 0),
       note='the optical centre and the view direction: Unity puts its camera for the monitors here (fov ~55)')
    col('Camera_Head', 'Kit_Camera_Head', (-0.06, 0.06, -0.25, 0.10, 0.0, 0.13))

    item('Kit_Camera_BracketWall')
    k = kb('Kit_Camera_BracketWall', 'Kit')
    k.box(-0.05, 0.05, -0.012, 0.0, -0.07, 0.07, Z_KCAM)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.cyl(V((sx * 0.032, -0.012, sz * 0.050)), V((sx * 0.032, -0.017, sz * 0.050)), 0.006, Z_KSTEEL, 6)
    k.tube([V((0, -0.012, 0.0)), V((0, -0.10, 0.005)), V((0, -0.19, 0.03)), V((0, -0.235, 0.050))], 0.016, Z_KCAM, 8)
    k.lathe(V((0, -0.24, 0.045)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.016), (0.012, 0.022), (0.026, 0.016), (0.03, 0.0)], Z_KBLACK, 10)
    k.tube([V((0.012, -0.235, 0.07)), V((0.016, -0.17, 0.045)), V((0.014, -0.06, 0.03)), V((0.010, -0.012, 0.03))], 0.0035,
           Z_KCABLE, 5, caps=False)
    P_('Kit_Camera_BracketWall', 'static', (0, 0, 0), note='wall bracket of the camera; origin = the middle of the wall plate on '
                                                           'the wall; the arm stands out to -y')
    S_('Mount_Head', (0, -0.24, 0.075), 'mount', parent='Kit_Camera_BracketWall', note='Kit_Camera_Head\'s origin goes here; its '
                                                                                        'pan / tilt is the placement\'s')
    col('Camera_BracketWall', 'Kit_Camera_BracketWall', (-0.05, 0.05, -0.26, 0.0, -0.07, 0.08))

    item('Kit_Camera_BracketPole')
    k = kb('Kit_Camera_BracketPole', 'Kit')
    for zc in (0.0, -0.13):
        band_ring(k, (0, 0, zc), (0, 0, 1), 0.128, 0.035, 0.004, Z_KGALV, seg=14)
    k.box(-0.045, 0.045, -0.145, -0.130, -0.17, 0.035, Z_KGALV)
    for zc in (0.0, -0.13):
        k.box(-0.012, 0.012, -0.150, -0.130, zc - 0.012, zc + 0.012, Z_KSTEEL)
    k.strip([V((0, -0.145, -0.05)), V((0, -0.33, 0.0)), V((0, -0.50, 0.055))], V((0, 0, 1)), 0.035, 0.035, Z_KGALV)
    k.strip([V((0, -0.145, -0.15)), V((0, -0.33, -0.02))], V((0, 0, 1)), 0.025, 0.02, Z_KGALV)
    k.lathe(V((0, -0.515, 0.055)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.016), (0.012, 0.022), (0.026, 0.016), (0.03, 0.0)], Z_KBLACK, 10)
    # the camera's cable along the arm into the pole through the strap plate (a grommet in the plate)
    k.tube([V((0.014, -0.508, 0.078)), V((0.022, -0.47, 0.06)), V((0.022, -0.33, 0.004)), V((0.022, -0.17, -0.05)),
            V((0.012, -0.152, -0.085))], 0.0035, Z_KCABLE, 5, caps=False)
    k.cyl(V((0.012, -0.145, -0.085)), V((0.012, -0.151, -0.085)), 0.0065, Z_KBLACK, 6)
    P_('Kit_Camera_BracketPole', 'static', (0, 0, 0), note='pole bracket of the camera: two straps for a pole of 0.20-0.26 m; '
                                                           'origin = on the pole\'s axis at the upper strap; the arm stands out to '
                                                           '-y; the camera\'s cable runs along the arm into the pole')
    S_('Mount_Head_Pole', (0, -0.515, 0.085), 'mount', parent='Kit_Camera_BracketPole', note='Kit_Camera_Head\'s origin goes '
                                                                                               'here; its pan / tilt is the placement\'s')
    col('Camera_BracketPole', 'Kit_Camera_BracketPole', (-0.05, 0.05, -0.54, -0.12, -0.17, 0.09))


# ================================================================ K12 the steel mast and its attachments
MAST = dict(r0=0.140, r1=0.124, h=4.20, side=(3.95, 3.35), foot=0.25, foot_z=(-0.40, 0.10), flange=0.17, door=(0.55, 0.85, 0.05))
CLAMP_R = 0.128             # every clamp-on attachment: two straps of this inner radius (the mast is 0.125-0.127 at its side
                            # mounts; a wooden pole 0.20-0.26 m across takes them too)
TOP_R = MAST['r1'] + 0.020  # a top attachment's sleeve (over the mast's top and its cap)
LAMP_META = {}              # light name -> dict(item, lens, glow, spot, rpm, startsOn): the lights json


def mast_r(z):
    """the mast's radius at height z (a slight taper from the flange to the top)"""
    z0, z1 = MAST['foot_z'][1] + 0.02, MAST['h']
    return MAST['r0'] + (MAST['r1'] - MAST['r0']) * min(max((z - z0) / (z1 - z0), 0.0), 1.0)


def plate(k, pts, n, t, zone):
    """flat plate: the polygon pts (in a plane with normal n) thickened +-t/2 along n; side faces turned away from its middle"""
    n = V(n).normalized()
    P = [V(p) for p in pts]
    c = sum(P, V((0, 0, 0))) / len(P)
    A = [p - n * (t / 2) for p in P]
    B = [p + n * (t / 2) for p in P]
    face(k, B, zone, n)
    face(k, A, zone, -n)
    m = len(P)
    for i in range(m):
        j = (i + 1) % m
        e = P[j] - P[i]
        out = e.cross(n)
        if out.dot((P[i] + P[j]) / 2 - c) < 0:
            out = -out
        face(k, [A[i], A[j], B[j], B[i]], zone, out)


def arc_slab(k, r0, r1, a0, a1, z0, z1, zone, n=4):
    """curved slab round the z axis (a door on a round pole): radii r0..r1, angles a0..a1 (rad, from +x), heights z0..z1;
    the inner face is left out"""
    angs = [a0 + (a1 - a0) * i / n for i in range(n + 1)]

    def p(r, a, z):
        return V((r * math.cos(a), r * math.sin(a), z))
    for i in range(n):
        a, b = angs[i], angs[i + 1]
        mid = (a + b) / 2
        face(k, [p(r1, a, z0), p(r1, b, z0), p(r1, b, z1), p(r1, a, z1)], zone, V((math.cos(mid), math.sin(mid), 0)))
        face(k, [p(r0, a, z1), p(r1, a, z1), p(r1, b, z1), p(r0, b, z1)], zone, (0, 0, 1))
        face(k, [p(r0, a, z0), p(r0, b, z0), p(r1, b, z0), p(r1, a, z0)], zone, (0, 0, -1))
    for a, s in ((a0, -1), (a1, 1)):
        t = V((-math.sin(a), math.cos(a), 0)) * s
        face(k, [p(r0, a, z0), p(r1, a, z0), p(r1, a, z1), p(r0, a, z1)], zone, t)


def pole_clamp(k, zs=(0.0, -0.13), top=0.035, bottom=-0.17):
    """a pole attachment's clamp: two straps round the pole (origin on its axis at the upper strap), the strap plate on
    their -y side with the bolt tabs; the attachment goes on out to -y"""
    for zc in zs:
        band_ring(k, (0, 0, zc), (0, 0, 1), CLAMP_R, 0.035, 0.004, Z_KGALV, seg=14)
    k.box(-0.045, 0.045, -0.145, -0.130, bottom, top, Z_KGALV)
    for zc in zs:
        k.box(-0.012, 0.012, -0.150, -0.130, zc - 0.012, zc + 0.012, Z_KSTEEL)


def top_sleeve(k):
    """a top attachment's sleeve: slips over the mast's top and its cap (origin on the axis at the mast's top), the bottom
    ring, the lid at z 0.05, two set bolts"""
    k.lathe(V((0, 0, -0.18)), (0, 0, 1), [(0.0, MAST['r1'] + 0.002), (0.0, TOP_R), (0.23, TOP_R), (0.23, 0.0)], Z_KGALV, 12,
            cap0=False, cap1=False)
    for sx in (-1, 1):
        k.cyl(V((sx * TOP_R, 0, -0.10)), V((sx * (TOP_R + 0.014), 0, -0.10)), 0.009, Z_KSTEEL, 6)


def head_M(pivot, tilt):
    """4x4 of a head built in its own frame (pivot at its origin, front -y, up +z), tipped down by tilt (deg) about x"""
    return Matrix.Translation(V(pivot)) @ Matrix.Rotation(math.radians(tilt), 4, 'X')


def box_bounds(M, lo, hi):
    """axis-aligned bounds (x0, x1, y0, y1, z0, z1) of the box lo..hi carried by M"""
    pts = [M @ V((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    return (min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


def mast():
    item('Kit_Mast')
    k = kb('Kit_Mast', 'Kit')
    fh = MAST['foot']
    fz0, fz1 = MAST['foot_z']
    H = MAST['h']
    # the concrete footing (0.10 above the ground, 0.40 down: on a slope it stays in the ground), its top edges chamfered
    box6(k, (-fh, -fh, fz0), (fh, fh, fz1 - 0.02), Z_KCONC, skip=('-z', '+z'))
    lo_ = [V((sx * fh, sy * fh, fz1 - 0.02)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    hi_ = [V((sx * (fh - 0.02), sy * (fh - 0.02), fz1)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        j = (i + 1) % 4
        mid = (lo_[i] + lo_[j]) / 2
        face(k, [lo_[i], lo_[j], hi_[j], hi_[i]], Z_KCONC, V((mid.x, mid.y, 0.6)))
    face(k, hi_, Z_KCONC, (0, 0, 1))
    # the base flange on the concrete, four anchor bolts (nuts), four gussets, the weld collar
    fl = MAST['flange']
    zf = fz1 + 0.02
    box6(k, (-fl, -fl, fz1), (fl, fl, zf), Z_KGALV, skip=('-z',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = V((sx * 0.13, sy * 0.13, zf))
            k.cyl(c, c + V((0, 0, 0.016)), 0.017, Z_KGALV, 6)
            k.cyl(c + V((0, 0, 0.016)), c + V((0, 0, 0.040)), 0.009, Z_KGALV, 6)
    r_b = mast_r(zf)
    for d in (V((1, 0, 0)), V((-1, 0, 0)), V((0, 1, 0)), V((0, -1, 0))):
        n = V((0, 0, 1)).cross(d)
        pts = [d * (r_b - 0.004) + V((0, 0, zf)), d * (fl - 0.005) + V((0, 0, zf)), d * (fl - 0.005) + V((0, 0, zf + 0.03)),
               d * (r_b - 0.004) + V((0, 0, zf + 0.20))]
        plate(k, pts, n, 0.012, Z_KGALV)
    k.lathe(V((0, 0, zf)), (0, 0, 1), [(0.0, r_b + 0.006), (0.06, mast_r(zf + 0.06) + 0.005), (0.07, mast_r(zf + 0.07))],
            Z_KGALV, 12, cap0=False, cap1=False)
    # the tube (a slight taper), the top cap
    zs = [zf + 0.07, 1.2, 2.4, 3.6, H]
    k.lathe(V((0, 0, 0)), (0, 0, 1), [(z, mast_r(z)) for z in zs], Z_KGALV, 12, cap0=False, cap1=False)
    k.lathe(V((0, 0, H)), (0, 0, 1), [(0.0, MAST['r1'] + 0.006), (0.014, MAST['r1'] + 0.006), (0.034, 0.045), (0.042, 0.0)],
            Z_KGALV, 12, cap0=True, cap1=False)
    # the hand-hole door on the back (+y): a curved lid with its screw; the lightning sticker on it
    d0, d1, hw = MAST['door']
    rd = mast_r((d0 + d1) / 2)
    ha = hw / rd
    arc_slab(k, rd - 0.004, rd + 0.005, math.pi / 2 - ha, math.pi / 2 + ha, d0, d1, Z_KGALV, n=4)
    k.cyl(V((0, rd + 0.005, d0 + 0.05)), V((0, rd + 0.010, d0 + 0.05)), 0.008, Z_KSTEEL, 6)
    st = kb('Kit_Mast_Sticker', 'panel')
    quad(st, (0, rd + 0.0065, d1 - 0.085), (0, 1, 0), 0.05, 0.04375, uv('sign_volt'))
    P_('Kit_Mast_Sticker', 'static', (0, rd + 0.006, d1 - 0.085), parent='Kit_Mast',
       note='the lightning sticker on the hand-hole door (panel atlas)')
    P_('Kit_Mast', 'static', (0, 0, 0), note='steel mast: galvanised tube 0.28 -> 0.25 m, 4.2 m, on a base flange (four anchor '
                                             'bolts, gussets) on a concrete footing 0.5 x 0.5 m (0.10 above the ground, 0.40 in '
                                             'it); the hand-hole door on the back (+y); two clamp mounts on its side and one on '
                                             'its top for the attachments; origin = the mast\'s axis at the ground')
    for i, zm in enumerate(MAST['side']):
        S_(f'Mount_Side_{i + 1}', (0, 0, zm), 'mount', parent='Kit_Mast', dir=(0, -1, 0),
           note=('the upper' if i == 0 else 'the lower (0.6 m down)') + ' side mount: a clamp-on attachment\'s origin goes '
                'here (on the axis at its upper strap) - Kit_Camera_BracketPole, Kit_Mast_Flood, Kit_Mast_Horn, Kit_Mast_Yagi; '
                'turn it about z to where it should point (its front is -y)')
    S_('Mount_Top', (0, 0, H), 'mount', parent='Kit_Mast', dir=(0, 0, 1),
       note='the top mount: a top attachment\'s origin goes here (on the axis at the mast\'s top; its sleeve covers the cap) - '
            'Kit_Mast_Lamp, Kit_Mast_Antenna, Kit_Mast_Siren; turn it about z freely')
    S_('Conduit_Base', (0, fh, CR), 'conduit', parent='Kit_Mast', dir=(0, 1, 0),
       note='the cables leave the footing here (its back face, at the ground): a conduit (Kit_Conduit_Entry on the face, '
            'Kit_Conduit_Straight along the ground) goes on along dir')
    col('Mast', 'Kit_Mast', (-MAST['r0'], MAST['r0'], -MAST['r0'], MAST['r0'], zf, H + 0.04))
    col('Mast_Foot', 'Kit_Mast', (-fh, fh, -fh, fh, fz0, zf + 0.04))


def mast_flood():
    """halogen floodlight on a clamp: a yoke on a short arm, the lamp head tipped 30 down, its glass (lens Flood), the halo,
    its light LIGHT_Flood"""
    item('Kit_Mast_Flood')
    k = kb('Kit_Mast_Flood', 'Kit')
    pole_clamp(k)
    zp, yp, tilt = -0.055, -0.47, 30.0
    k.box(-0.02, 0.02, -0.33, -0.145, zp - 0.02, zp + 0.02, Z_KGALV)                    # the arm
    k.box(-0.178, 0.178, -0.345, -0.33, zp - 0.02, zp + 0.02, Z_KGALV)                  # the yoke: its bar and two arms
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.166, sx * 0.178))
        k.box(x0, x1, yp - 0.025, -0.33, zp - 0.02, zp + 0.02, Z_KGALV)
        k.cyl(V((sx * 0.178, yp, zp)), V((sx * 0.196, yp, zp)), 0.016, Z_KHANDLE, 8)      # the tilt knobs
    # the head in its own frame (pivot at the origin): die-cast housing, the bezel round the glass, fins, the pivot bosses
    h = KB()
    VM.rbox(h, (0, 0.005, 0), (0.32, 0.12, 0.22), Z_KSTEEL, r=0.012, ch=0.005, axis='y')
    for bx in ((-0.16, 0.16, 0.09, 0.11), (-0.16, 0.16, -0.11, -0.09), (-0.16, -0.13, -0.09, 0.09), (0.13, 0.16, -0.09, 0.09)):
        h.box(bx[0], bx[1], -0.063, -0.055, bx[2], bx[3], Z_KSTEEL)
    for i in range(6):
        xf = -0.125 + i * 0.05
        h.box(xf - 0.003, xf + 0.003, 0.065, 0.092, -0.09, 0.09, Z_KSTEEL)
    for sx in (-1, 1):
        h.cyl(V((sx * 0.16, 0, 0)), V((sx * 0.172, 0, 0)), 0.02, Z_KSTEEL, 8)
    h.cyl(V((0, 0.04, -0.11)), V((0, 0.04, -0.126)), 0.010, Z_KBLACK, 6)                 # the cable gland underneath
    Mh = head_M((0, yp, zp), tilt)
    merge_kb(k, h, Mh)
    gl = Mh @ V((0, 0.04, -0.126))
    k.tube([gl, gl + V((0, 0, -0.04)), V((0.03, -0.36, zp - 0.06)), V((0.03, -0.22, zp - 0.035)), V((0.012, -0.152, -0.11))],
           0.004, Z_KCABLE, 5, caps=False)
    R3 = Mh.to_3x3()
    fwd, up = R3 @ V((0, -1, 0)), R3 @ V((0, 0, 1))
    L = kb('Lens_Flood', 'lens:Flood')
    quad(L, Mh @ V((0, -0.058, 0)), fwd, 0.26, 0.18, uv('l_flood'), up=up)
    P_('Lens_Flood', 'static', Mh @ V((0, -0.058, 0)), parent='Kit_Mast_Flood',
       note='the floodlight\'s glass: M_Kit_Lamp_Flood (lit) / M_Kit_Lamp_Flood_Off')
    G = kb('Glow_Flood', 'glow')
    quad(G, Mh @ V((0, -0.075, 0)), fwd, 0.80, 0.56, uv('glow_white'), up=up)
    P_('Glow_Flood', 'static', Mh @ V((0, -0.075, 0)), parent='Kit_Mast_Flood',
       note='halo card in front of the glass (additive, unlit): shown while the lamp is lit')
    P_('Kit_Mast_Flood', 'static', (0, 0, 0), note='floodlight on a pole clamp (halogen 500 W, die-cast grey housing 0.32 x '
                                                   '0.22 m): the yoke on a short arm, the head tipped 30 down; origin = on the '
                                                   'pole\'s axis at the upper strap (a side mount); it shines along -y')
    lp = Mh @ V((0, -0.07, 0))
    S_('LIGHT_Flood', lp, 'light', parent='Kit_Mast_Flood', dir=fwd, up=up, note='the floodlight (see the lights json)')
    LAMPS.append(('Flood', lp, tuple(fwd), 'flood', tuple(up)))
    LAMP_META['Flood'] = dict(item='Kit_Mast_Flood', lens='Lens_Flood', glow='Glow_Flood', spot=110, rpm=0)
    col('Mast_Flood_Clamp', 'Kit_Mast_Flood', (-0.20, 0.20, -0.35, -0.12, -0.17, 0.04))
    col('Mast_Flood_Head', 'Kit_Mast_Flood', box_bounds(Mh, (-0.16, -0.063, -0.11), (0.16, 0.092, 0.11)))


def mast_horn():
    """horn loudspeaker on a clamp: a short arm, a post with a band round the driver, the flared horn tipped 15 down
    (grey outside, black inside), its sound point"""
    item('Kit_Mast_Horn')
    k = kb('Kit_Mast_Horn', 'Kit')
    pole_clamp(k)
    k.box(-0.02, 0.02, -0.30, -0.145, -0.075, -0.035, Z_KGALV)                          # the arm
    k.box(-0.015, 0.015, -0.255, -0.225, -0.035, 0.015, Z_KGALV)                        # the post up to the band
    tilt = 15.0
    Mh = head_M((0, -0.30, 0.065), tilt)                                                # the horn's throat, ahead of the band
    h = KB()
    # the driver: a can behind the throat (+y), its rear dome, the band round it, the terminal gland
    h.lathe(V((0, 0, 0)), (0, 1, 0), [(0.0, 0.040), (0.0, 0.066), (0.11, 0.066), (0.13, 0.052), (0.145, 0.0)], Z_KCAB, 12,
            cap0=False, cap1=False)
    band_ring(h, (0, 0.06, 0), (0, 1, 0), 0.067, 0.03, 0.004, Z_KGALV, seg=12)
    h.cyl(V((0, 0.10, -0.066)), V((0, 0.10, -0.080)), 0.009, Z_KBLACK, 6)
    # the flare along -y: outside grey, the mouth's rim, inside black down to the throat
    prof = [(0.0, 0.040), (0.06, 0.046), (0.14, 0.060), (0.22, 0.082), (0.29, 0.110), (0.34, 0.140), (0.37, 0.165), (0.38, 0.172)]
    h.lathe(V((0, 0, 0)), (0, -1, 0), prof, Z_KCAB, 14, cap0=False, cap1=False)
    h.lathe(V((0, 0, 0)), (0, -1, 0), [(0.38, 0.172), (0.38, 0.166)], Z_KCAB, 14, cap0=False, cap1=False)
    inner = [(a, r - 0.006) for a, r in reversed(prof)]
    h.lathe(V((0, 0, 0)), (0, -1, 0), inner, Z_KBLACK, 14, cap0=False, cap1=True)
    merge_kb(k, h, Mh)
    gl = Mh @ V((0, 0.10, -0.080))
    k.tube([gl, V((0.03, gl.y, gl.z - 0.02)), V((0.03, -0.20, -0.09)), V((0.012, -0.152, -0.11))], 0.004, Z_KCABLE, 5, caps=False)
    R3 = Mh.to_3x3()
    fwd = R3 @ V((0, -1, 0))
    P_('Kit_Mast_Horn', 'static', (0, 0, 0), note='horn loudspeaker (pressure-chamber horn, mouth 0.34 m, grey) on a pole clamp, '
                                                  'tipped 15 down; origin = on the pole\'s axis at the upper strap (a side '
                                                  'mount); it sounds along -y')
    S_('Audio_Horn', Mh @ V((0, -0.38, 0)), 'audio', parent='Kit_Mast_Horn', dir=fwd,
       note='the loudspeaker: announcements, a gong, the siren tone, a voice at night (the story decides); loud, directional')
    col('Mast_Horn_Clamp', 'Kit_Mast_Horn', (-0.05, 0.05, -0.31, -0.12, -0.17, 0.04))
    col('Mast_Horn_Horn', 'Kit_Mast_Horn', box_bounds(Mh, (-0.172, -0.38, -0.172), (0.172, 0.145, 0.172)))


def mast_yagi():
    """a 5-element Yagi (vertical elements: vertical polarisation, the base's radio) on a 0.6 m stand-off arm"""
    item('Kit_Mast_Yagi')
    k = kb('Kit_Mast_Yagi', 'Kit')
    pole_clamp(k)
    za = -0.055
    k.cyl(V((0, -0.14, za)), V((0, -0.64, za)), 0.021, Z_KGALV, 8)                       # the stand-off arm
    k.box(-0.03, 0.03, -0.68, -0.62, za - 0.03, 0.012, Z_KGALV)                         # the boom clamp
    for sx in (-1, 1):
        k.cyl(V((sx * 0.03, -0.65, za)), V((sx * 0.042, -0.65, za)), 0.009, Z_KSTEEL, 6)
    y0, y1 = -0.64, -1.74
    k.box(-0.01, 0.01, y1, y0, 0.012, 0.032, Z_KALU)                                    # the boom on the clamp
    zb = 0.022
    els = [(-0.72, 0.96, 'R'), (-0.92, 0.90, 'D'), (-1.16, 0.84, 'D1'), (-1.42, 0.82, 'D2'), (-1.70, 0.80, 'D3')]
    for ye, Le, kind in els:
        k.box(-0.014, 0.014, ye - 0.014, ye + 0.014, zb - 0.016, zb + 0.016, Z_KBLACK)    # the element's insulator
        if kind == 'D':                                                                  # the dipole: two halves, the feed box
            k.box(-0.026, 0.026, ye - 0.02, ye + 0.02, zb - 0.045, zb + 0.045, Z_KBLACK)
            for s in (-1, 1):
                k.cyl(V((0, ye, zb + s * 0.045)), V((0, ye, zb + s * Le / 2)), 0.005, Z_KALU, 5)
        else:
            k.cyl(V((0, ye, zb - Le / 2)), V((0, ye, zb + Le / 2)), 0.005, Z_KALU, 5)
    # the coax from the feed box under the boom back to the clamp, along the arm into the pole
    k.tube([V((0.0, -0.92, zb - 0.045)), V((0.02, -0.90, zb - 0.03)), V((0.02, -0.70, zb - 0.03)), V((0.04, -0.66, za - 0.03)),
            V((0.03, -0.60, za - 0.012)), V((0.03, -0.20, za - 0.012)), V((0.012, -0.152, -0.11))], 0.004, Z_KCABLE, 5,
           caps=False)
    P_('Kit_Mast_Yagi', 'static', (0, 0, 0), note='directional antenna for the radio (5-element Yagi, 2 m band, elements '
                                                  'vertical, boom 1.1 m) on a 0.6 m stand-off arm and a pole clamp; origin = on '
                                                  'the pole\'s axis at the upper strap (a side mount); it points along -y')
    col('Mast_Yagi_Arm', 'Kit_Mast_Yagi', (-0.05, 0.05, -0.69, -0.12, -0.17, 0.04))
    col('Mast_Yagi_Boom', 'Kit_Mast_Yagi', (-0.03, 0.03, y1, y0, zb - 0.48, zb + 0.48))


def mast_lamp():
    """street lamp on the mast's top: the sleeve, a curved arm 1.1 m out, a 70s box luminaire with its opal bowl (lens
    Street), the halo, its light LIGHT_Street"""
    item('Kit_Mast_Lamp')
    k = kb('Kit_Mast_Lamp', 'Kit')
    top_sleeve(k)
    k.tube([V((0, 0, 0.02)), V((0, 0, 0.13)), V((0, -0.08, 0.27)), V((0, -0.27, 0.40)), V((0, -0.58, 0.47)), V((0, -0.95, 0.49)),
            V((0, -1.13, 0.49))], 0.030, Z_KGALV, 8)
    yc, zc = -1.40, 0.47
    VM.rbox(k, (0, yc, zc), (0.27, 0.62, 0.11), Z_KCAB, r=0.03, ch=0.01, axis='z')
    k.box(-0.02, 0.02, yc - 0.20, yc + 0.20, zc + 0.055, zc + 0.07, Z_KCAB)              # the ridge on the lid
    L = kb('Lens_Street', 'lens:Street')
    quad(L, (0, yc, zc - 0.058), (0, 0, -1), 0.50, 0.20, uv('l_street'), up=(1, 0, 0))
    P_('Lens_Street', 'static', (0, yc, zc - 0.058), parent='Kit_Mast_Lamp',
       note='the lamp\'s opal bowl seen from below: M_Kit_Lamp_Street (lit) / M_Kit_Lamp_Street_Off')
    G = kb('Glow_Street', 'glow')
    for n_ in ((1, 0, 0), (0, 1, 0)):
        quad(G, (0, yc, zc - 0.27), n_, 0.90, 0.40, uv('glow_white'), up=(0, 0, 1))
    P_('Glow_Street', 'static', (0, yc, zc - 0.27), parent='Kit_Mast_Lamp',
       note='halo cards under the lamp (additive, unlit): shown while it is lit')
    P_('Kit_Mast_Lamp', 'static', (0, 0, 0), note='street lamp on the mast\'s top (mercury 125 W, 70s box luminaire, grey) on '
                                                  'a curved arm reaching 1.4 m out to -y; origin = on the mast\'s axis at its '
                                                  'top (the top mount)')
    lp = V((0, yc, zc - 0.07))
    S_('LIGHT_Street', lp, 'light', parent='Kit_Mast_Lamp', dir=(0, 0, -1), up=(0, -1, 0), note='the street lamp (see the lights json)')
    LAMPS.append(('Street', lp, (0, 0, -1), 'street', (0, -1, 0)))
    LAMP_META['Street'] = dict(item='Kit_Mast_Lamp', lens='Lens_Street', glow='Glow_Street', spot=160, rpm=0)
    col('Mast_Lamp_Arm', 'Kit_Mast_Lamp', (-0.15, 0.15, -1.13, 0.15, -0.18, 0.52))
    col('Mast_Lamp_Head', 'Kit_Mast_Lamp', (-0.135, 0.135, yc - 0.31, yc + 0.31, zc - 0.06, zc + 0.07))


def mast_antenna():
    """VHF ground-plane antenna on the mast's top: the sleeve, a pipe, the base with four sloping radials, the whip"""
    item('Kit_Mast_Antenna')
    k = kb('Kit_Mast_Antenna', 'Kit')
    top_sleeve(k)
    k.cyl(V((0, 0, 0.05)), V((0, 0, 0.70)), 0.024, Z_KGALV, 8)
    k.cyl(V((0, 0, 0.70)), V((0, 0, 0.79)), 0.036, Z_KBLACK, 10)
    for a in (45, 135, 225, 315):
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        b = d * 0.034 + V((0, 0, 0.73))
        k.cyl(b, b + d * (0.55 * math.cos(math.radians(30))) + V((0, 0, -0.55 * math.sin(math.radians(30)))), 0.005, Z_KALU, 5)
    k.cyl(V((0, 0, 0.79)), V((0, 0, 2.10)), 0.009, Z_KALU, 6, r2=0.004)
    k.lathe(V((0, 0, 2.10)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.008), (0.008, 0.008), (0.016, 0.0)], Z_KALU, 6)
    k.tube([V((0.036, 0, 0.74)), V((0.050, 0, 0.66)), V((0.040, 0, 0.40)), V((0.030, 0, 0.10)), V((0.030, 0, 0.055))], 0.005,
           Z_KCABLE, 5, caps=False)
    P_('Kit_Mast_Antenna', 'static', (0, 0, 0), note='radio antenna on the mast\'s top: a vertical whip 1.3 m over a black base '
                                                     'with four radials sloping 30 down (VHF ground plane, the base\'s radio), '
                                                     'on a pipe; origin = on the mast\'s axis at its top (the top mount)')
    col('Mast_Antenna', 'Kit_Mast_Antenna', (-0.05, 0.05, -0.05, 0.05, 0.05, 0.80))


def mast_siren():
    """motor siren on the mast's top: the sleeve, a stand, the motor housing, the stator with its ports, the rain hat"""
    item('Kit_Mast_Siren')
    k = kb('Kit_Mast_Siren', 'Kit')
    top_sleeve(k)
    k.cyl(V((0, 0, 0.05)), V((0, 0, 0.24)), 0.05, Z_KGALV, 10, caps=False)
    k.lathe(V((0, 0, 0.24)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.12), (0.012, 0.12), (0.012, 0.0)], Z_KGALV, 12)
    k.lathe(V((0, 0, 0.252)), (0, 0, 1), [(0.0, 0.10), (0.01, 0.15), (0.24, 0.15), (0.25, 0.205), (0.45, 0.205), (0.45, 0.0)],
            Z_KCAB, 16, cap0=False, cap1=False)
    for i in range(10):                                                                 # the stator's ports (dark)
        a = math.radians(i * 36 + 18)
        d = V((math.cos(a), math.sin(a), 0))
        t = V((-math.sin(a), math.cos(a), 0))
        VM.obox(k, d * 0.201 + V((0, 0, 0.602)), (0.07, 0.012, 0.13), Z_KBLACK, Matrix((t, d, V((0, 0, 1)))).transposed())
    for i in range(4):
        a = math.radians(i * 90 + 45)
        d = V((math.cos(a), math.sin(a), 0))
        k.box_m(d * 0.15 + V((0, 0, 0.735)), (0.012, 0.012, 0.07), Z_KGALV)
    k.lathe(V((0, 0, 0.77)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.26), (0.016, 0.26), (0.12, 0.06), (0.13, 0.0)], Z_KCAB, 16, cap0=True)
    P_('Kit_Mast_Siren', 'static', (0, 0, 0), note='motor siren for the alarm (grey, the stator\'s ten ports under a rain hat) on '
                                                   'a stand on the mast\'s top; origin = on the mast\'s axis at its top (the top '
                                                   'mount)')
    S_('Audio_Siren', (0, 0, 0.60), 'audio', parent='Kit_Mast_Siren',
       note='the siren: the rising and falling wail (alarm), a long steady tone (all clear); it winds up and down slowly')
    col('Mast_Siren', 'Kit_Mast_Siren', (-0.26, 0.26, -0.26, 0.26, -0.18, 0.90))



# ---------------------------------------------------------------- K9 the overhead wires as models
WIRE_REF = {'Kit_Wire_Bare': (40.0, 'bare', (0.5, 1.5)), 'Kit_Wire_Drop': (10.0, 'lv', (0.3, 2.5))}


def wire_items():
    """one overhead wire per item: a reference span along +x from its origin (one attach point) to (L, 0, 0) (the other),
    sagging by the K9 rule; the placement turns it (yaw, then pitch) from one Wire_ socket to the other and scales it in x
    by span / L (the wire's thickness stays; the sag stays the reference one)"""
    for name, (L, kind, rng) in WIRE_REF.items():
        item(name)
        k = kb(name, 'wire:' + kind)
        pts, sag = wire_points(V((0, 0, 0)), V((L, 0, 0)))
        k.tube(pts, S.WIRE['r_lv'] if kind == 'lv' else S.WIRE['r_bare'], ZERO, S.WIRE['sides'], caps=False)
        what = 'bare aluminium line wire (M_Kit_WireBare)' if kind == 'bare' else 'black twisted service cable (M_Kit_Wire)'
        P_(name, 'stretch', (0, 0, 0), (1, 0, 0), rng, unit='x', sag=round(sag, 3), span=L,
           note=f'one overhead wire: {what}, a {L:.0f} m reference span from the origin along +x, sagging {sag:.2f} m in the '
                f'middle (the K9 rule); scale x = span / {L:.0f} (spans {L * rng[0]:.0f}-{L * rng[1]:.0f} m), turned so that its end '
                f'lands on the other Wire_ point')
        tag = 'Bare' if kind == 'bare' else 'Drop'
        S_(f'{tag}_A', (0, 0, 0), 'wire', parent=name, dir=(1, 0, 0), note='this end goes on a Wire_ point (an insulator\'s groove)')
        S_(f'{tag}_B', (L, 0, 0), 'wire', parent=name, dir=(-1, 0, 0), note='the other end (before the x scale)')


# ================================================================ K2 the CRT monitor
MON = dict(w=0.34, h=0.31, op=(0.130, 0.075, 0.275), scr=(0.125, 0.0785, 0.2715), bez=(-0.19, -0.15))


def monitor():
    item('Kit_Monitor_CRT')
    k = kb('Kit_Monitor_CRT', 'Kit')
    hw, H = MON['w'] / 2, MON['h']
    ox, oz0, oz1 = MON['op']
    yb0, yb1 = MON['bez']
    # bezel: a frame round the opening (front face, reveals into the tube face), rounded outer corners
    for (x0, x1, z0, z1, sk) in ((-hw, hw, 0.0, oz0, ('+z',)), (-hw, hw, oz1, H, ('-z',)), (-hw, -ox, oz0, oz1, ('-z', '+z', '+x')),
                                 (ox, hw, oz0, oz1, ('-z', '+z', '-x'))):
        box6(k, (x0, yb0, z0), (x1, yb1, z1), Z_KBEZEL, skip=('+y',) + sk)
    for (lo, hi, n) in (((-ox, yb0, oz0), (ox, yb0 + 0.012, oz0), (0, 0, 1)), ((-ox, yb0, oz1), (ox, yb0 + 0.012, oz1), (0, 0, -1)),
                        ((-ox, yb0, oz0), (-ox, yb0 + 0.012, oz1), (1, 0, 0)), ((ox, yb0, oz0), (ox, yb0 + 0.012, oz1), (-1, 0, 0))):
        lo, hi = V(lo), V(hi)
        if n[2]:
            face(k, [lo, V((hi.x, lo.y, lo.z)), V((hi.x, hi.y, lo.z)), V((lo.x, hi.y, lo.z))], Z_KBEZEL, n)
        else:
            face(k, [lo, V((lo.x, hi.y, lo.z)), V((lo.x, hi.y, hi.z)), V((lo.x, lo.y, hi.z))], Z_KBEZEL, n)
    face(k, [(-ox, yb0 + 0.012, oz0), (ox, yb0 + 0.012, oz0), (ox, yb0 + 0.012, oz1), (-ox, yb0 + 0.012, oz1)], Z_KBLACK, (0, -1, 0))
    # case (steel, grey-beige), the tapered back with the vents, rubber feet, the cable
    box6(k, (-hw + 0.005, yb1, 0.006), (hw - 0.005, 0.10, H - 0.006), Z_KCRT, skip=('-y', '+y'))
    rings = [[V((sx * (hw - 0.005), 0.10, z)) for sx, z in ((-1, 0.006), (1, 0.006), (1, H - 0.006), (-1, H - 0.006))],
             [V((sx * 0.105, 0.20, z)) for sx, z in ((-1, 0.07), (1, 0.07), (1, 0.255), (-1, 0.255))]]
    k.loft(rings, [Z_KCRT], cap1=Z_KCRT)
    for i in range(5):                                       # vent slots on the top (dark strips, raised a hair)
        y0 = -0.10 + i * 0.035
        k.box(-0.11, 0.11, y0, y0 + 0.012, H - 0.006, H - 0.0045, Z_KBLACK)
    for sx in (-1, 1):
        for yy in (-0.13, 0.08):
            k.box(sx * hw * 0.8 - 0.02, sx * hw * 0.8 + 0.02, yy - 0.02, yy + 0.02, 0.0, 0.006, Z_KBLACK)
    k.cyl(V((0.06, 0.20, 0.12)), V((0.06, 0.216, 0.12)), 0.008, Z_KBLACK, 6)
    k.tube([V((0.06, 0.216, 0.12)), V((0.07, 0.235, 0.07)), V((0.08, 0.245, 0.004))], 0.0035, Z_KCABLE, 5, caps=False)
    # front controls under the screen: two knobs, the power button
    for xk in (-0.027, 0.053):                               # CONTRAST, BRIGHT knobs over the strip's marks (snowkit_tex)
        k.cyl(V((xk, yb0, 0.029)), V((xk, yb0 - 0.012, 0.029)), 0.0075, Z_KHANDLE, 8)
    k.box(0.1085, 0.1285, yb0 - 0.006, yb0, 0.021, 0.037, Z_KBLACK)                        # POWER button
    Lb = kb('Kit_Monitor_Label', 'panel')
    quad(Lb, (0.0, yb0 - 0.0006, 0.042), (0, -1, 0), 0.30, 0.0375, uv('lbl_monitor'))
    P_('Kit_Monitor_Label', 'static', (0, yb0, 0.042), parent='Kit_Monitor_CRT', note='CCTV MONITOR / POWER / BRIGHT / CONTRAST '
                                                                                     'strip under the screen (panel atlas)')
    lamp_lens('Lens_MonitorLED', 'Green', (0.1185, yb0 - 0.0008, 0.067), (0, -1, 0), 0.004, 'Kit_Monitor_CRT', dome=0.002, seg=8,
              note='power LED: M_Kit_Lamp_Green with the power, _Off without')
    # the screen: its own object, a slight bulge, UV 0..1 over the whole glass (Unity shows the camera picture there)
    sc = kb('Kit_Monitor_Screen', 'screen')
    sx, sz0, sz1 = MON['scr']
    nu, nv = 8, 6
    ys = yb0 + 0.010
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            x, z = -sx + 2 * sx * u, sz0 + (sz1 - sz0) * v
            bulge = 0.010 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            row.append((sc.bm.verts.new(V((x, ys - bulge, z))), (u, v)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            a, b, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
            sc._f([a[0], d[0], c[0], b[0]], ZERO, [a[1], d[1], c[1], b[1]])
    zc = (sz0 + sz1) / 2
    P_('Kit_Monitor_Screen', 'static', (0, ys, zc), parent='Kit_Monitor_CRT',
       note='the CRT glass: M_Kit_Screen_Off without the power; with it M_Kit_Screen_On, where Unity puts the camera picture '
            '(render texture); UV 0..1 over the glass, u to the right, v up')
    P_('Kit_Monitor_CRT', 'static', (0, 0, 0), note='14-inch CCTV monitor (metal case); origin = the middle of the underside; '
                                                    'the screen faces -y')
    S_('Screen_Centre', (0, ys - 0.010, zc), 'screen', parent='Kit_Monitor_CRT', dir=(0, -1, 0),
       note='the middle of the glass, facing out (4:3, 0.25 x 0.19 m)')
    S_('Audio_Monitor', (0, 0.0, 0.16), 'audio', parent='Kit_Monitor_CRT', note='the CRT whine and the degauss thump at power-on')
    col('Monitor', 'Kit_Monitor_CRT', (-hw, hw, yb0, 0.20, 0.0, H))


# ================================================================ K3 the console, the button, the labels
CON = dict(d=0.20, zf=0.045, zb=0.11, pitch=0.10, s_btn=0.090, s_lbl=0.050, s_strip=0.186)


def con_frame():
    """the sloped panel: origin of slope coordinate s at the front top edge; returns (point(u, s), normal, up-slope)"""
    d, zf, zb = CON['d'], CON['zf'], CON['zb']
    up = V((0, d, zb - zf)).normalized()
    n = V((0, -(zb - zf), d)).normalized()
    p0 = V((0, -d / 2, zf))
    return (lambda u, s: p0 + V((u, 0, 0)) + up * s), n, up


def console(nslots):
    name = f'Kit_Console_{nslots}'
    item(name)
    k = kb(name, 'Kit')
    W = 0.10 + nslots * CON['pitch']
    d, zf, zb = CON['d'], CON['zf'], CON['zb']
    poly = [(-d / 2, 0.0), (d / 2, 0.0), (d / 2, zb), (-d / 2, zf)]
    prism_x(k, poly, -W / 2, W / 2, Z_KCONS, Z_KCONS, [Z_KCONS, Z_KCONS, Z_KALU, Z_KCONS])
    P, n, up = con_frame()
    L = (V((0, d, zb - zf))).length
    rim = 0.008
    for (u0, u1, s0, s1) in ((-W / 2, W / 2, 0.0, rim), (-W / 2, W / 2, L - rim, L), (-W / 2, -W / 2 + rim, rim, L - rim),
                             (W / 2 - rim, W / 2, rim, L - rim)):
        c = (P(u0, s0) + P(u1, s1)) / 2 + n * 0.002
        R = Matrix((V((1, 0, 0)), up, n)).transposed()
        k.box_m(c, (u1 - u0, s1 - s0, 0.004), Z_KCONS, R)
    for sx in (-1, 1):
        for yy in (-d / 2 + 0.025, d / 2 - 0.025):
            k.box(sx * (W / 2 - 0.03) - 0.012, sx * (W / 2 - 0.03) + 0.012, yy - 0.012, yy + 0.012, -0.004, 0.0, Z_KBLACK)
    k.cyl(V((W / 2 - 0.05, d / 2, 0.03)), V((W / 2 - 0.05, d / 2 + 0.014, 0.03)), 0.008, Z_KBLACK, 6)
    k.tube([V((W / 2 - 0.05, d / 2 + 0.014, 0.03)), V((W / 2 - 0.04, d / 2 + 0.06, 0.012)), V((W / 2 - 0.02, d / 2 + 0.12, 0.003))],
           0.0035, Z_KCABLE, 5, caps=False)
    st = kb(name + '_Strip', 'panel')
    sw, sh = S.PANEL['lbl_console'][1]
    quad(st, P(-W / 2 + 0.012 + sw / 2, CON['s_strip']) + n * 0.0005, n, sw, sh, uv('lbl_console'), up=up)
    P_(name + '_Strip', 'static', P(0, CON['s_strip']), parent=name, note='TORSTEUERUNG / GATE CONTROL strip (panel atlas)')
    P_(name, 'static', (0, 0, 0), note=f'desk console with {nslots} button places on the sloped aluminium panel; origin = the '
                                       'middle of the underside; the operator sits on the -y side')
    for i in range(nslots):
        u = -(nslots - 1) / 2 * CON['pitch'] + i * CON['pitch']
        S_(f'Slot_Button_{i + 1}' + ('' if nslots == 2 else f'_of{nslots}'), P(u, CON['s_btn']), 'kit_slot', parent=name,
           dir=tuple(n), up=tuple(up), note='Kit_Console_Button goes here: its +z along dir, its +y along up')
        S_(f'Slot_Label_{i + 1}' + ('' if nslots == 2 else f'_of{nslots}'), P(u, CON['s_lbl']), 'kit_slot', parent=name,
           dir=tuple(n), up=tuple(up), note='a Kit_Console_Label_* goes here (under its button)')
    col(f'Console_{nslots}', name, (-W / 2, W / 2, -d / 2, d / 2, 0.0, zb))


def button():
    item('Kit_Console_Button')
    k = kb('Kit_Console_Button', 'Kit')
    k.lathe(V((0, 0, 0)), (0, 0, 1), [(0.0, 0.020), (0.006, 0.020), (0.006, 0.0155), (0.002, 0.0155)], Z_KBLACK, 14)
    k.lathe(V((0, 0.045, 0)), (0, 0, 1), [(0.0, 0.0125), (0.004, 0.0125), (0.004, 0.0095)], Z_KALU, 12, cap0=True, cap1=False)
    c = kb('IX_ConsoleButton', 'Kit')
    c.lathe(V((0, 0, 0.002)), (0, 0, 1), [(0.0, 0.0145), (0.010, 0.0145), (0.0125, 0.0125), (0.0135, 0.008), (0.0138, 0.0)],
            Z_KBTN, 14, cap0=False)
    P_('IX_ConsoleButton', 'slide', (0, 0, 0.002), (0, 0, -1), (0, 0.005), unit='m', parent='Kit_Console_Button',
       states=['up', 'pressed'], note='the push-button cap: pressed in 5 mm (along -z of the button, into the panel), springs back')
    lamp_lens('Lens_ConsoleButton', 'Amber', (0, 0.045, 0.004), (0, 0, 1), 0.0095, 'Kit_Console_Button', dome=0.006, seg=12,
              note='the lamp over the button: M_Kit_Lamp_Amber lit / _Off (Unity: lit while its gate / barrier moves or is open)')
    P_('Kit_Console_Button', 'static', (0, 0, 0), note='console push-button with its lamp; origin = the button\'s middle on the '
                                                       'panel face, +z out of the panel, +y up the panel (the lamp side)')
    S_('Hand_ConsoleButton', (0, 0, 0.03), 'hand', parent='IX_ConsoleButton', dir=(0, 0, -1), note='press here')
    S_('Audio_ConsoleButton', (0, 0, 0.005), 'audio', parent='Kit_Console_Button', note='the button clicks')


def labels():
    for key, txt in (('Schranke', 'btn_schranke'), ('Tor', 'btn_tor'), ('Licht', 'btn_licht'), ('Blank', 'btn_blank')):
        name = f'Kit_Console_Label_{key}'
        item(name)
        q = kb(name, 'panel')
        w, h = S.PANEL[txt][1]
        quad(q, (0, 0, 0.0008), (0, 0, 1), w, h, uv(txt), up=(0, 1, 0))
        P_(name, 'static', (0, 0, 0), note=f'engraved label {S.PANEL[txt][2]}; origin = its middle on the panel face, +z out, +y up')


# ================================================================ K4 the rotary phone
def phone():
    item('Kit_Phone')
    k = kb('Kit_Phone', 'Kit')
    W = 0.11
    poly = [(-0.105, 0.0), (0.095, 0.0), (0.095, 0.078), (0.075, 0.098), (-0.02, 0.104), (-0.105, 0.050), (-0.105, 0.012)]
    poly2 = [(y, z) for y, z in poly]
    prism_x(k, poly2, -W, W, Z_KPHONE, Z_KPHONE)
    for sx in (-1, 1):                                        # side chamfers (a softer body)
        k.box(sx * W - 0.002 * sx - 0.002, sx * W - 0.002 * sx + 0.002, -0.10, 0.09, 0.004, 0.07, Z_KPHONE)
    for sx in (-1, 1):                                        # the cradle forks
        x0 = sx * 0.078
        prism_x(k, [(0.015, 0.103), (0.065, 0.100), (0.065, 0.128), (0.052, 0.128), (0.040, 0.116), (0.028, 0.128), (0.015, 0.128)],
                x0 - 0.012, x0 + 0.012, Z_KPHONE, Z_KPHONE)
        k.box(x0 - 0.004, x0 + 0.004, 0.036, 0.044, 0.114, 0.122, Z_KHANDLE)          # the hook switch plunger
    for sx in (-1, 1):
        for yy in (-0.085, 0.075):
            k.box(sx * 0.085 - 0.012, sx * 0.085 + 0.012, yy - 0.012, yy + 0.012, -0.003, 0.0, Z_KBLACK)
    # the dial on the front slope: a bezel ring here, the finger wheel its own object
    a, b = V((0, -0.105, 0.050)), V((0, -0.02, 0.104))
    dvec = (b - a).normalized()
    n = V((0, -dvec.z, dvec.y)).normalized()
    dc = (a + b) / 2
    k.lathe(dc, n, [(0.0, 0.048), (0.004, 0.048), (0.004, 0.045)], Z_KPHONE, 16, cap0=False, cap1=False)
    D = kb('Phone_Dial', 'panel')
    D.disc_uv(dc + n * 0.0045, n, 0.044, uv('phone_dial'), 18)
    P_('Phone_Dial', 'hinge', dc, tuple(n), (0, 300), parent='Kit_Phone', states=['rest', 'wound'],
       note='the finger wheel: turns up to 300 while dialling (+, clockwise seen from the user) and runs back')
    # the receiver: its own object (lifted / animated while in the hand)
    R = kb('Phone_Receiver', 'Kit')
    rc = V((0, 0.040, 0.138))
    R.strip([rc + V((-0.085, 0, 0)), rc + V((-0.04, 0, 0.012)), rc + V((0.04, 0, 0.012)), rc + V((0.085, 0, 0))],
            V((0, 0, 1)), 0.040, 0.022, Z_KPHONE)
    for sx in (-1, 1):
        R.lathe(rc + V((sx * 0.095, 0, -0.004)), (0, 0, -1),
                [(0.0, 0.0), (0.0, 0.026), (0.016, 0.032), (0.026, 0.031), (0.030, 0.026), (0.030, 0.0)], Z_KPHONE, 12)
        R.disc_uv(rc + V((sx * 0.095, 0, -0.0345)), V((0, 0, -1)), 0.022, (0, 0, 0, 0), 10, zone=Z_KBLACK)
    P_('Phone_Receiver', 'static', rc, parent='Kit_Phone', note='the receiver on the cradle: lifted, carried, put back (its own '
                                                               'object); the curly cord stays with the body')
    # curly cord (body left side -> the receiver's mouthpiece end), the line cord out at the back
    pts = []
    for i in range(41):
        t = i / 40
        base = V((-0.112, -0.02, 0.03)).lerp(V((-0.10, 0.03, 0.105)), t) + V((-0.03 * math.sin(math.pi * t), 0.0, 0.0))
        pts.append(base + V((0.0, 0.006 * math.cos(t * TAU * 9), 0.006 * math.sin(t * TAU * 9))))
    k.tube(pts, 0.0026, Z_KPHONE, 5, caps=False)
    k.tube([V((0.0, 0.095, 0.02)), V((0.01, 0.13, 0.004)), V((0.04, 0.22, 0.003))], 0.0025, Z_KBLACK, 5, caps=False)
    P_('Kit_Phone', 'static', (0, 0, 0), note='rotary desk phone of the 70s (FeTAp 611 shape, orange); origin = the middle of '
                                              'the underside; the dial faces the user (-y)')
    S_('Hand_Phone_Receiver', rc + V((0, 0, 0.03)), 'hand', parent='Phone_Receiver', note='pick it up here')
    S_('Audio_Phone', (0, 0.0, 0.06), 'audio', parent='Kit_Phone', note='the bell inside (two bursts), the hook switch click')
    S_('Audio_PhoneEar', rc + V((-0.095, 0, -0.02)), 'audio', parent='Phone_Receiver', note='the earpiece: dial tone, voices')
    col('Phone', 'Kit_Phone', (-W, W, -0.105, 0.095, 0.0, 0.104))
    col('Phone_Receiver', 'Phone_Receiver', (-0.125, 0.125, 0.018, 0.062, 0.100, 0.152))


# ================================================================ K5 the distribution cabinet
CAB = dict(w=0.60, h=0.80, d=0.28, t=0.012)
BATT = dict(size=(0.175, 0.2644, 0.278), post=(0.04, 0.217, 0.105))   # the van's battery (its own Unity frame)


def cabinet():
    item('Kit_Cabinet_Power')
    k = kb('Kit_Cabinet_Power', 'Kit')
    hw, hh, D, t = CAB['w'] / 2, CAB['h'] / 2, CAB['d'], CAB['t']
    # shell: outside (sides, top, bottom), the front rim, inside (the mounting plate at the back, sides, top, floor)
    box6(k, (-hw, -D, -hh), (hw, 0.0, hh), Z_KCAB, skip=('-y', '+y'))
    for (x0, x1, z0, z1) in ((-hw, hw, -hh, -hh + t), (-hw, hw, hh - t, hh), (-hw, -hw + t, -hh + t, hh - t), (hw - t, hw, -hh + t, hh - t)):
        face(k, [(x0, -D, z0), (x1, -D, z0), (x1, -D, z1), (x0, -D, z1)], Z_KCAB, (0, -1, 0))
    inner_box(k, (-hw + t, -D, -hh + t), (hw - t, -0.006, hh - t), {'*': Z_KCAB, '+y': Z_KCABIN}, skip=('-y',))
    k.box(-hw - 0.015, hw + 0.015, -D - 0.035, 0.0, hh, hh + 0.012, Z_KCAB)                 # rain cap
    for sx in (-1, 1):                                                                        # wall lugs
        for sz in (-1, 1):
            k.box(sx * (hw + 0.002), sx * (hw + 0.030), -0.012, -0.004, sz * (hh - 0.06) - 0.02, sz * (hh - 0.06) + 0.02, Z_KCAB)
    # the battery shelf (galvanised, a lip at the front), the battery slot
    zs = -hh + 0.07
    box6(k, (-hw + t, -D + 0.02, zs - 0.015), (hw - t, -0.006, zs), Z_KCABIN, skip=('-x', '+x', '+y'))
    k.box(-hw + t, hw - t, -D + 0.02, -D + 0.032, zs, zs + 0.03, Z_KCABIN)
    bpos = V((0.0, -0.135, zs))
    S_('Slot_Battery', bpos, 'item_slot', parent='Kit_Cabinet_Power', forward=(0, -1, 0), up=(0, 0, 1),
       note='the van\'s Battery (item) stands here: its origin (bottom middle) on this point, its +x (the post side) to the '
            'cabinet\'s front, its +y up, so its posts are under the clamps; Unity: battery local +x -> cabinet +Z, +y -> +Y')
    # the battery's posts in this frame: local (x, y, z) -> (z, -x, y) (see the module docstring)
    px, py, pz = BATT['post']
    posts = {'Pos': bpos + V((-pz, -px, py)), 'Neg': bpos + V((pz, -px, py))}
    # DIN rail with breakers, the circuit card holder, the cable comb at the top, the conduit gland
    zr = 0.06
    k.box(-0.22, 0.22, -0.020, -0.006, zr - 0.0175, zr + 0.0175, Z_KGALV)
    for i in range(6):
        x0 = -0.20 + i * 0.045
        box6(k, (x0, -0.075, zr - 0.045), (x0 + 0.036, -0.020, zr + 0.045), Z_KBRKR, skip=('+y',))
        k.box(x0 + 0.012, x0 + 0.024, -0.083, -0.075, zr - 0.006, zr + 0.012, Z_KHANDLE)
    k.box(-0.24, 0.24, -0.05, -0.006, hh - 0.08, hh - 0.05, Z_KCABIN)
    for xc in (-0.08, 0.0, 0.08):
        k.tube([V((xc, -0.03, hh - 0.08)), V((xc, -0.03, zr + 0.045))], 0.004, Z_KCABLE, 5, caps=False)
    # the two cables to the clamps: from the comb down the plate, each into its clamp
    S_('Conduit_Top', (0.0, -0.12, hh + 0.012), 'conduit', parent='Kit_Cabinet_Power', dir=(0, 0, 1),
       note='cable entry on the top (rain cap): a Kit_Conduit_Entry (its +x along dir) and the conduit up from here')
    S_('Conduit_Bottom', (0.0, -0.12, -hh), 'conduit', parent='Kit_Cabinet_Power', dir=(0, 0, -1),
       note='cable entry in the floor (the other way in)')
    # the change-over switch NETZ / BATTERIE: a black body with the dial plate, the handle (its own object)
    sp = V((0.17, -0.006, 0.22))
    k.box(sp.x - 0.04, sp.x + 0.04, -0.040, -0.006, sp.z - 0.04, sp.z + 0.04, Z_KBLACK)
    pl = kb('Kit_Cabinet_SwitchPlate', 'panel')
    quad(pl, (sp.x, -0.0405, sp.z + 0.076 * (38 / 64 - 0.5)), (0, -1, 0), 0.076, 0.076, uv('lbl_switch'))     # hub at 38/64
    P_('Kit_Cabinet_SwitchPlate', 'static', (sp.x, -0.04, sp.z), parent='Kit_Cabinet_Power',
       note='the switch\'s dial plate: NETZ (0) left, BATTERIE (90) right (panel atlas)')
    hd = kb('IX_CabinetSwitch', 'Kit')
    hc = V((sp.x, -0.041, sp.z))
    hd.lathe(hc, (0, -1, 0), [(0.0, 0.016), (0.012, 0.016), (0.016, 0.012), (0.016, 0.0)], Z_KHANDLE, 12)
    lever = V((-math.sin(math.radians(45)), 0, math.cos(math.radians(45))))
    Rl = VM.frame_R(lever, V((0, -1, 0)))
    hd.box_m(hc + V((0, -0.022, 0)) + lever * 0.028, (0.060, 0.016, 0.014), Z_KHANDLE, Rl)
    hd.box_m(hc + V((0, -0.0302, 0)) + lever * 0.045, (0.020, 0.002, 0.004), Z_KREDC, Rl)
    P_('IX_CabinetSwitch', 'hinge', hc, (0, 1, 0), (0, 90), parent='Kit_Cabinet_Power', states=['netz', 'batterie'],
       note='change-over switch: 0 = NETZ (the line, dead), 90 = BATTERIE (the battery on the shelf); the lever turns clockwise '
            'seen from the front')
    S_('Hand_CabinetSwitch', hc + V((0, -0.03, 0)) + lever * 0.04, 'hand', parent='IX_CabinetSwitch', note='turn the lever')
    S_('Audio_CabinetSwitch', hc, 'audio', parent='Kit_Cabinet_Power', note='the switch clacks over; relays click in the booth')
    # the clamps: red + and black -, each with its cable back to the plate; they slide up off the posts
    for sign, z_cov, nm in (('Pos', Z_KREDC, 'IX_CabinetClamp_Pos'), ('Neg', Z_KBLACK, 'IX_CabinetClamp_Neg')):
        c = posts[sign]
        cl = kb(nm, 'Kit')
        cl.box(c.x - 0.014, c.x + 0.014, c.y - 0.012, c.y + 0.012, c.z - 0.020, c.z + 0.004, Z_KCOPPER)
        cl.cyl(c + V((0.0, -0.012, -0.010)), c + V((0.0, -0.030, -0.010)), 0.004, Z_KSTEEL, 6)
        VM.rbox(cl, c + V((0, 0.004, 0.018)), (0.040, 0.034, 0.036), z_cov, r=0.008, ch=0.004)
        top = c + V((0, 0.012, 0.036))
        cl.tube([top, top + V((0, 0.025, 0.020)), V((c.x * 0.6, -0.030, c.z + 0.075)), V((c.x * 0.5, -0.012, c.z + 0.110))],
                0.0075, Z_KCABLE, 6, caps=False)
        P_(nm, 'slide', c, (0, 0, 1), (0, 0.06), unit='m', parent='Kit_Cabinet_Power', states=['on', 'off'], rest=0.06,
           note=f'battery clamp {"+ (red)" if sign == "Pos" else "- (black)"}: 0 = on the battery post, 0.06 = lifted off '
                f'(the start: no battery); the cable moves with it')
        S_('Hand_CabinetClamp_' + sign, c + V((0, -0.02, 0.02)), 'hand', parent=nm, note='take the clamp here')
    S_('Audio_CabinetClamps', (0, -0.15, posts['Pos'].z), 'audio', parent='Kit_Cabinet_Power',
       note='the clamps: a spark crack when the second one goes on with the switch at BATTERIE')
    # the door (left hinge seen from the front), the sign, the power lamp, the handle; the circuit card inside
    d = kb('IX_CabinetDoor', 'Kit')
    yd0, yd1 = -D - 0.022, -D - 0.002
    box6(d, (-hw, yd0, -hh), (hw, yd1, hh), {'-y': Z_KCAB, '+y': Z_KCAB, '*': Z_KCAB})
    for (x0, x1, z0, z1) in ((-hw + 0.02, hw - 0.02, -hh + 0.02, -hh + 0.035), (-hw + 0.02, hw - 0.02, hh - 0.035, hh - 0.02),
                             (-hw + 0.02, -hw + 0.035, -hh + 0.035, hh - 0.035), (hw - 0.035, hw - 0.02, -hh + 0.035, hh - 0.035)):
        d.box(x0, x1, yd1, yd1 + 0.004, z0, z1, Z_KBLACK)                                    # the gasket
    for zh in (-hh + 0.12, hh - 0.12):                                                        # hinges
        d.cyl(V((-hw - 0.008, yd0 + 0.006, zh - 0.04)), V((-hw - 0.008, yd0 + 0.006, zh + 0.04)), 0.008, Z_KSTEEL, 8)
    hx, hz = hw - 0.06, 0.0
    d.lathe(V((hx, yd0, hz)), (0, -1, 0), [(0.0, 0.020), (0.008, 0.020), (0.010, 0.016)], Z_KSTEEL, 10, cap0=False)
    d.box(hx - 0.006, hx + 0.006, yd0 - 0.040, yd0 - 0.010, hz - 0.035, hz + 0.035, Z_KHANDLE)
    sg = kb('Kit_Cabinet_Sign', 'panel')
    sw, sh = S.PANEL['sign_notstrom'][1]
    quad(sg, (0.0, yd0 - 0.0006, 0.20), (0, -1, 0), sw, sh, uv('sign_notstrom'))
    P_('Kit_Cabinet_Sign', 'static', (0, yd0, 0.20), parent='IX_CabinetDoor', note='NOTSTROM 12V / EMERGENCY 12V with the lightning '
                                                                                    '(panel atlas)')
    d.lathe(V((-0.17, yd0, 0.02)), (0, -1, 0), [(0.0, 0.016), (0.006, 0.016), (0.006, 0.012)], Z_KSTEEL, 12, cap0=False, cap1=False)
    lamp_lens('Lens_CabinetPower', 'Green', (-0.17, yd0 - 0.006, 0.02), (0, -1, 0), 0.012, 'IX_CabinetDoor', dome=0.007, seg=12,
              note='the "power on" lamp on the door: M_Kit_Lamp_Green when the booth has power (battery, both clamps on, the '
                   'switch at BATTERIE), _Off otherwise')
    cd = kb('Kit_Cabinet_Card', 'panel')
    cw, ch = S.PANEL['lbl_cabinet_in'][1]
    quad(cd, (0.04, yd1 + 0.0026, 0.16), (0, 1, 0), cw, ch, uv('lbl_cabinet_in'))
    P_('Kit_Cabinet_Card', 'static', (0.04, yd1, 0.16), parent='IX_CabinetDoor', note='the circuit card inside the door (panel atlas)')
    piv = V((-hw - 0.008, yd0 + 0.006, 0.0))
    P_('IX_CabinetDoor', 'hinge', piv, (0, 0, -1), (0, 110), parent='Kit_Cabinet_Power', states=['shut', 'open'],
       note='cabinet door: hinged on the left (seen from the front), opens outward (+) to 110; quarter-turn handle, not locked')
    S_('Hand_CabinetDoor', (hx, yd0 - 0.045, hz), 'hand', parent='IX_CabinetDoor', note='the handle')
    S_('Audio_CabinetDoor', (0.0, -D, 0.0), 'audio', parent='Kit_Cabinet_Power', note='the door: hinges, the gasket')
    S_('Battery_Post_Pos', posts['Pos'], 'point', parent='Kit_Cabinet_Power', note='where the battery\'s + post is when it stands '
                                                                                    'in Slot_Battery (the red clamp at 0)')
    S_('Battery_Post_Neg', posts['Neg'], 'point', parent='Kit_Cabinet_Power', note='the - post')
    P_('Kit_Cabinet_Power', 'static', (0, 0, 0), note='wall distribution cabinet 0.60 x 0.80 x 0.28 m (light grey); origin = the '
                                                      'middle of the back on the wall; inside: the battery shelf, the clamps, the '
                                                      'change-over switch, breakers')
    for nm_, bx in (('Back', (-hw, hw, -0.012, 0.0, -hh, hh)), ('Left', (-hw, -hw + t, -D, 0.0, -hh, hh)),
                    ('Right', (hw - t, hw, -D, 0.0, -hh, hh)), ('Top', (-hw, hw, -D, 0.0, hh - t, hh + 0.012)),
                    ('Bottom', (-hw, hw, -D, 0.0, -hh, -hh + t)), ('Shelf', (-hw, hw, -D + 0.02, 0.0, -hh, zs))):
        col('Cabinet_' + nm_, 'Kit_Cabinet_Power', bx)
    col('Cabinet_Door', 'IX_CabinetDoor', (-hw, hw, yd0, yd1, -hh, hh))


# ================================================================ K6 the junction box
def junction():
    item('Kit_JunctionBox')
    k = kb('Kit_JunctionBox', 'Kit')
    VM.rbox(k, (0, -0.037, 0), (0.16, 0.074, 0.16), Z_KPLAST, r=0.008, ch=0.004, axis='y')
    VM.rbox(k, (0, -0.081, 0), (0.15, 0.014, 0.15), Z_KPLAST, r=0.010, ch=0.004, axis='y')
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.cyl(V((sx * 0.06, -0.088, sz * 0.06)), V((sx * 0.06, -0.091, sz * 0.06)), 0.006, Z_KSTEEL, 6)
    for (c, a) in (((0, -0.04, -0.080), (0, 0, -1)), ((0, -0.04, 0.080), (0, 0, 1)), ((-0.080, -0.04, 0), (-1, 0, 0)),
                   ((0.080, -0.04, 0), (1, 0, 0))):
        k.cyl(V(c), V(c) + V(a) * 0.006, 0.019, Z_KPLAST, 10)
    st = kb('Kit_JunctionBox_Sticker', 'panel')
    quad(st, (0, -0.0885, 0.02), (0, -1, 0), 0.05, 0.04375, uv('sign_volt'))
    P_('Kit_JunctionBox_Sticker', 'static', (0, -0.088, 0.02), parent='Kit_JunctionBox', note='the lightning sticker (panel atlas)')
    P_('Kit_JunctionBox', 'static', (0, 0, 0), note='small junction box 0.16 x 0.16 x 0.09 m (grey plastic, lid with four screws); '
                                                    'origin = the middle of the back on the wall')
    for nm_, c, a in (('Bottom', (0, -0.04, -0.086), (0, 0, -1)), ('Top', (0, -0.04, 0.086), (0, 0, 1)),
                      ('Left', (-0.086, -0.04, 0), (-1, 0, 0)), ('Right', (0.086, -0.04, 0), (1, 0, 0))):
        S_('Conduit_' + nm_ + '_JB', c, 'conduit', parent='Kit_JunctionBox', dir=a, note='knock-out: a conduit (Kit_Conduit_Entry) '
                                                                                          'goes in here along dir')
    col('JunctionBox', 'Kit_JunctionBox', (-0.08, 0.08, -0.09, 0.0, -0.08, 0.08))


# ================================================================ K7 conduit pieces
CR = 0.016


def conduits():
    item('Kit_Conduit_Straight')
    k = kb('Kit_Conduit_Straight', 'Kit')
    k.cyl(V((0, 0, 0)), V((1.0, 0, 0)), CR, Z_KGALV, 8, caps=False)
    P_('Kit_Conduit_Straight', 'stretch', (0, 0, 0), (1, 0, 0), (0.05, 6.0), unit='m', note='straight conduit (galvanised, 32 mm), '
       '1 m along +x from the origin on its axis; scale x = the length in metres (0.05-6); ends open (an elbow, entry or the '
       'next piece covers them)')
    col('Conduit_Straight', 'Kit_Conduit_Straight', (0.0, 1.0, -CR, CR, -CR, CR))

    item('Kit_Conduit_Elbow')
    k = kb('Kit_Conduit_Elbow', 'Kit')
    Rb = 0.10
    pts = [V((-0.02, 0, 0))] + [V((Rb * math.sin(math.radians(a)), 0, Rb - Rb * math.cos(math.radians(a)))) for a in range(0, 91, 15)] + \
          [V((Rb, 0, Rb + 0.02))]
    k.tube(pts, CR, Z_KGALV, 8, caps=False)
    for c, a in ((V((-0.02, 0, 0)), V((1, 0, 0))), (V((Rb, 0, Rb + 0.02)), V((0, 0, -1)))):
        k.lathe(c, a, [(0.0, CR + 0.003), (0.03, CR + 0.003)], Z_KGALV, 8, cap0=True, cap1=False)
    P_('Kit_Conduit_Elbow', 'static', (0, 0, 0), note='90-degree elbow (bend radius 0.10 m) with sleeves: in along +x at the origin '
                                                      '(on the axis, the sleeve reaches back 0.02), out along +z at (0.10, 0, 0.12)')
    S_('Elbow_Out', (Rb, 0, Rb + 0.02), 'conduit', parent='Kit_Conduit_Elbow', dir=(0, 0, 1), note='the next piece starts here')

    item('Kit_Conduit_Clamp')
    k = kb('Kit_Conduit_Clamp', 'Kit')
    rr = CR + 0.0015
    arc = [V((0, -rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a)) * 0.98)) for a in range(0, 181, 20)]
    k.strip([V((0, -rr - 0.022, -CR + 0.001)), V((0, -rr, -CR + 0.001))] + arc[1:-1] + [V((0, rr, -CR + 0.001)),
                                                                                         V((0, rr + 0.022, -CR + 0.001))],
            V((1, 0, 0)), 0.018, 0.002, Z_KGALV)
    for sy in (-1, 1):
        k.cyl(V((0, sy * (rr + 0.013), -CR + 0.002)), V((0, sy * (rr + 0.013), -CR + 0.006)), 0.004, Z_KSTEEL, 6)
    P_('Kit_Conduit_Clamp', 'static', (0, 0, 0), note='saddle clamp: origin on the conduit\'s axis (along x), its feet on the '
                                                      'surface at z -0.016 (turn -z into the wall or the ground); every ~1 m')

    item('Kit_Conduit_Entry')
    k = kb('Kit_Conduit_Entry', 'Kit')
    k.lathe(V((0, 0, 0)), (1, 0, 0), [(0.0, 0.024), (0.008, 0.024)], Z_KSTEEL, 6)
    k.lathe(V((0.008, 0, 0)), (1, 0, 0), [(0.0, 0.020), (0.032, 0.020), (0.040, CR + 0.002), (0.045, CR + 0.002)], Z_KGALV, 10,
            cap0=False, cap1=False)
    P_('Kit_Conduit_Entry', 'static', (0, 0, 0), note='gland where a conduit enters a box or cabinet: origin on the box face, the '
                                                      'conduit leaves along +x; the conduit starts at x 0.04')


# ================================================================ K8 wooden poles
POLE = dict(h=8.5, r0=0.135, r1=0.105, arm_z=8.18, arm_L=1.60, ins_x=(-0.70, 0.0, 0.70))


def pole_body(k, name):
    H = POLE['h']
    prof = [(0.0, POLE['r0']), (H * 0.25, POLE['r0'] * 0.97), (H * 0.6, (POLE['r0'] + POLE['r1']) / 2), (H - 0.02, POLE['r1']),
            (H, POLE['r1'] * 0.92)]
    k.lathe(V((0, 0, -0.15)), (0, 0, 1), [(0.0, POLE['r0'] * 1.02)] + [(a + 0.15, r) for a, r in prof], Z_KPOLE, 10, cap0=False)
    k.lathe(V((0, 0, H)), (0, 0, 1), [(0.0, POLE['r1'] * 0.95), (0.012, POLE['r1'] * 0.95), (0.03, 0.0)], Z_KGALV, 10, cap0=False)
    for i, z in enumerate((2.6, 3.0, 3.4, 3.8, 4.2, 4.6, 5.0, 5.4, 5.8, 6.2, 6.6, 7.0)):     # climbing step bolts (alternate)
        a = math.radians(90 + (35 if i % 2 else -35))
        d = V((math.cos(a), math.sin(a), 0)) * -1
        r = POLE['r0'] - (POLE['r0'] - POLE['r1']) * z / POLE['h']
        k.cyl(d * (r - 0.01) + V((0, 0, z)), d * (r + 0.13) + V((0, 0, z)), 0.009, Z_KGALV, 6)
    # the earth wire down the pole (from the crossarm to the ground), stapled
    k.tube([V((0.0, POLE['r1'] + 0.006, POLE['arm_z'] - 0.1)), V((0.0, POLE['r0'] + 0.006, 0.0)), V((0.0, POLE['r0'] + 0.006, -0.1))],
           0.004, Z_KGALV, 4, caps=False)
    pl = kb(name + '_Plate', 'panel')
    quad(pl, (0.0, -POLE['r0'] - 0.003, 2.0), (0, -1, 0), 0.06, 0.06, uv('lbl_pole'))
    P_(name + '_Plate', 'static', (0, -POLE['r0'], 2.0), parent=name, note='the pole\'s number plate (panel atlas)')


def crossarm(k, z, L, xs, y_face):
    """galvanised angle crossarm on the -y face of the pole at height z, two braces, pin insulators at xs; wire points"""
    k.box(-L / 2, L / 2, y_face - 0.06, y_face, z - 0.006, z, Z_KGALV)
    k.box(-L / 2, L / 2, y_face - 0.006, y_face, z - 0.06, z, Z_KGALV)
    k.cyl(V((0, y_face + 0.02, z - 0.03)), V((0, y_face - 0.08, z - 0.03)), 0.008, Z_KSTEEL, 6)
    for sx in (-1, 1):
        k.strip([V((0, y_face - 0.003, z - 0.55)), V((sx * 0.55, y_face - 0.003, z - 0.03))], V((0, 1, 0)), 0.035, 0.005, Z_KGALV)
    k.cyl(V((0, y_face + 0.02, z - 0.55)), V((0, y_face - 0.04, z - 0.55)), 0.008, Z_KSTEEL, 6)
    return [insulator(k, V((x, y_face - 0.03, z))) for x in xs]


def poles():
    item('Kit_Pole')
    k = kb('Kit_Pole', 'Kit')
    pole_body(k, 'Kit_Pole')
    yf = -(POLE['r1'] + 0.005)
    tops = crossarm(k, POLE['arm_z'], POLE['arm_L'], POLE['ins_x'], yf)
    P_('Kit_Pole', 'static', (0, 0, 0), note='wooden line pole (creosoted spruce, 8.5 m above the ground), galvanised crossarm '
                                             'across x on its -y face, three pin insulators for the line; origin = the pole\'s axis '
                                             'at the ground')
    for i, p in enumerate(tops):
        S_(f'Wire_{i + 1}', p, 'wire', parent='Kit_Pole', dir=(0, 1, 0),
           note=['L1', 'L2', 'L3'][i] + ': the line wire (bare) rests in this insulator\'s groove; the line runs along y')
    WIRE_PTS['Kit_Pole'] = [f'Wire_{i + 1}' for i in range(3)]
    col('Pole', 'Kit_Pole', (-POLE['r0'], POLE['r0'], -POLE['r0'], POLE['r0'], 0.0, POLE['h']))
    col('Pole_Arm', 'Kit_Pole', (-POLE['arm_L'] / 2, POLE['arm_L'] / 2, yf - 0.06, yf, POLE['arm_z'] - 0.06, POLE['arm_z'] + 0.12))

    item('Kit_Pole_Trafo')
    k = kb('Kit_Pole_Trafo', 'Kit')
    pole_body(k, 'Kit_Pole_Trafo')
    tops = crossarm(k, POLE['arm_z'], POLE['arm_L'], POLE['ins_x'], yf)
    # the barrel transformer on two channels, its bushings, jumpers to the line, the LV arm with four spools
    zt = 4.55
    for zc in (zt - 0.02, zt + 0.55):
        k.box(-0.22, 0.22, yf - 0.62, yf, zc - 0.04, zc, Z_KGALV)
    tc = V((0, yf - 0.40, zt))
    k.lathe(tc, (0, 0, 1), [(0.0, 0.0), (0.0, 0.29), (0.84, 0.29), (0.86, 0.27), (0.92, 0.12), (0.93, 0.0)], Z_KTRAFO, 14)
    for i in range(10):                                                              # cooling fins round the back half
        a = math.radians(-20 - i * 14)
        d = V((math.cos(a), math.sin(a), 0))
        k.box_m(tc + d * 0.33 + V((0, 0, 0.42)), (0.09, 0.72, 0.012), Z_KTRAFO, VM.frame_R(d, V((0, 0, 1))))
    hv = []
    for i, x in enumerate((-0.16, 0.0, 0.16)):
        b = tc + V((x, -0.05 if i == 1 else 0.03, 0.90))
        k.lathe(b, (0, 0, 1), [(0.0, 0.03), (0.04, 0.045), (0.06, 0.03), (0.10, 0.04), (0.12, 0.025), (0.18, 0.03), (0.21, 0.012)],
                Z_KPORC, 8)
        hv.append(b + V((0, 0, 0.21)))
    for b, t in zip(hv, tops):                                                       # jumpers to the line insulators
        mid = (b + t) / 2 + V((0, -0.05, 0.25))
        k.tube([b, mid, t], 0.004, Z_KGALV, 4, caps=False)
    lv = []
    for i in range(4):
        b = tc + V((0.30, -0.10 + i * 0.065, 0.66))
        k.lathe(b, (1, 0, 0), [(0.0, 0.022), (0.03, 0.028), (0.05, 0.02), (0.07, 0.024), (0.08, 0.012)], Z_KPORC, 8)
        lv.append(b + V((0.08, 0, 0)))
    za = 5.75
    k.box(-0.05, 0.75, yf - 0.06, yf, za - 0.006, za, Z_KGALV)
    k.box(-0.05, 0.75, yf - 0.006, yf, za - 0.06, za, Z_KGALV)
    k.strip([V((0.0, yf - 0.003, za - 0.45)), V((0.55, yf - 0.003, za - 0.03))], V((0, 1, 0)), 0.03, 0.005, Z_KGALV)
    drops = []
    for i, x in enumerate((0.25, 0.40, 0.55, 0.70)):
        k.box(x - 0.006, x + 0.006, yf - 0.05, yf - 0.03, za, za + 0.06, Z_KSTEEL)
        drops.append(spool(k, V((x, yf - 0.04, za + 0.09)), (0, 1, 0)))
    for b, dpt in zip(lv, drops):                                                    # LV leads up to the spools (black)
        k.tube([b, b + V((0.06, 0, 0.1)), dpt + V((0, 0.02, -0.04)), dpt], 0.006, Z_KCABLE, 5, caps=False)
    sg = kb('Kit_Pole_Trafo_Sign', 'panel')
    sw, sh = S.PANEL['sign_danger'][1]
    quad(sg, (0.0, -POLE['r0'] - 0.004, 2.65), (0, -1, 0), sw, sh, uv('sign_danger'))
    P_('Kit_Pole_Trafo_Sign', 'static', (0, -POLE['r0'], 2.65), parent='Kit_Pole_Trafo', note='LEBENSGEFAHR / DANGER plate (panel atlas)')
    rp = kb('Kit_Pole_Trafo_Rating', 'panel')
    quad(rp, tc + V((0, -0.292, 0.45)), (0, -1, 0), 0.16, 0.08, uv('lbl_trafo'))
    P_('Kit_Pole_Trafo_Rating', 'static', tc + V((0, -0.29, 0.45)), parent='Kit_Pole_Trafo', note='rating plate on the tank')
    P_('Kit_Pole_Trafo', 'static', (0, 0, 0), note='wooden pole with the pole-mounted ("barrel") transformer 20 / 0.4 kV: the '
                                                   'medium-voltage line on the top crossarm (three insulators), the low-voltage '
                                                   'side on the small arm to +x (four spools) for the drop to a building; origin = '
                                                   'the pole\'s axis at the ground')
    for i, p in enumerate(tops):
        S_(f'Wire_{i + 1}_T', p, 'wire', parent='Kit_Pole_Trafo', dir=(0, 1, 0),
           note=['L1', 'L2', 'L3'][i] + ' of the 20 kV line (bare wire, the line runs along y)')
    for i, p in enumerate(drops):
        S_(f'Wire_{i + 4}_T', p, 'wire', parent='Kit_Pole_Trafo', dir=(0, -1, 0),
           note=['L1', 'L2', 'L3', 'N'][i] + ' of the 0.4 kV drop to a building (black service cable)')
    WIRE_PTS['Kit_Pole_Trafo'] = [f'Wire_{i + 1}_T' for i in range(7)]
    S_('Audio_Trafo', tc + V((0, 0, 0.45)), 'audio', parent='Kit_Pole_Trafo', note='the transformer hums while the line is live')
    col('Pole_T', 'Kit_Pole_Trafo', (-POLE['r0'], POLE['r0'], -POLE['r0'], POLE['r0'], 0.0, POLE['h']))
    col('Pole_T_Tank', 'Kit_Pole_Trafo', (tc.x - 0.36, tc.x + 0.36, tc.y - 0.36, tc.y + 0.36, zt, zt + 0.93))


# ================================================================ K9 the roof stand
RS = dict(off=0.12, r=0.030, h=2.20, arm_z=1.98, ins=(-0.21, -0.07, 0.07, 0.21))


def roofstand():
    item('Kit_RoofStand')
    k = kb('Kit_RoofStand', 'Kit')
    y0, r, H = -RS['off'], RS['r'], RS['h']
    k.lathe(V((0, y0, 0.0)), (0, 0, 1), [(0.0, 0.019), (0.04, 0.019), (0.07, r + 0.004), (0.11, r + 0.004), (0.11, r), (H, r)],
            Z_KGALV, 10, cap0=False, cap1=False)
    k.lathe(V((0, y0, H)), (0, 0, 1), [(0.0, r + 0.006), (0.03, r + 0.006), (0.05, 0.0)], Z_KGALV, 10, cap0=True)      # cap
    for zc in (0.25, 0.85):                                                     # wall clamps
        band_ring(k, (0, y0, zc), (0, 0, 1), r + 0.001, 0.04, 0.004, Z_KGALV, 10)
        k.box(-0.012, 0.012, y0 + r, 0.0, zc - 0.02, zc + 0.02, Z_KGALV)
        k.box(-0.05, 0.05, -0.008, 0.0, zc - 0.05, zc + 0.05, Z_KGALV)
    za = RS['arm_z']
    k.box(-0.30, 0.30, y0 - 0.025, y0 + 0.025, za - 0.005, za, Z_KGALV)
    k.box(-0.30, 0.30, y0 + 0.020, y0 + 0.025, za - 0.05, za, Z_KGALV)
    tops = []
    for x in RS['ins']:
        k.box(x - 0.006, x + 0.006, y0 - 0.006, y0 + 0.006, za, za + 0.05, Z_KSTEEL)
        tops.append(spool(k, V((x, y0, za + 0.085)), (0, 1, 0)))
    # the weather head: a short bend under the cap; the four leads in drip loops from the spools into it
    wh = V((0, y0 - r - 0.04, H - 0.18))
    k.tube([V((0, y0 - r + 0.005, H - 0.10)), V((0, y0 - r - 0.03, H - 0.11)), wh], 0.016, Z_KGALV, 8)
    for t in tops:
        k.tube([t + V((0, -0.02, -0.02)), t + V((0, -0.03, -0.14)), (t + wh) / 2 + V((0, -0.02, -0.12)), wh + V((0, 0, 0.005))],
               0.005, Z_KCABLE, 5, caps=False)
    P_('Kit_RoofStand', 'static', (0, 0, 0), note='roof stand ("Dachständer"): galvanised pipe 60 mm, 2.2 m, 0.12 m off the wall on '
                                                  'two clamps, a crossarm with four spool insulators, the weather head; origin = on '
                                                  'the wall at the pipe\'s bottom end; it goes up through the eave (the building '
                                                  'adds the flashing)')
    for i, p in enumerate(tops):
        S_(f'Wire_{i + 1}_R', p, 'wire', parent='Kit_RoofStand', dir=(0, -1, 0),
           note=['L1', 'L2', 'L3', 'N'][i] + ' of the service drop ends in this spool')
    WIRE_PTS['Kit_RoofStand'] = [f'Wire_{i + 1}_R' for i in range(4)]
    S_('Conduit_Bottom_R', (0, y0, 0.0), 'conduit', parent='Kit_RoofStand', dir=(0, 0, -1),
       note='the conduit (Kit_Conduit_*) continues down from here to the cabinet')
    col('RoofStand', 'Kit_RoofStand', (-0.30, 0.30, y0 - r - 0.06, 0.0, 0.0, H + 0.05))


# ================================================================ K10 the electric lock
def doorlock():
    item('Kit_DoorLock')
    k = kb('Kit_DoorLock', 'Kit')
    VM.rbox(k, (0, -0.0155, 0), (0.080, 0.031, 0.160), Z_KSTEEL, r=0.004, ch=0.003, axis='y')
    k.lathe(V((0.012, -0.031, -0.035)), (0, -1, 0), [(0.0, 0.012), (0.004, 0.012), (0.005, 0.009), (0.005, 0.0)], Z_KCOPPER, 10)
    k.box(0.008, 0.016, -0.0365, -0.0355, -0.042, -0.028, Z_KBLACK)
    k.box(0.038, 0.041, -0.024, -0.006, 0.006, 0.030, Z_KCOPPER)                              # the bolt's face on the latch side
    k.lathe(V((-0.025, -0.031, 0.06)), (0, -1, 0), [(0.0, 0.006), (0.003, 0.006), (0.003, 0.0)], Z_KSTEEL, 6)
    P_('Kit_DoorLock', 'static', (0, 0, 0), note='electric rim lock (box lock) on the door leaf: origin = the middle of its back '
                                                 'on the leaf; the bolt side is +x (toward the strike)')
    col('DoorLock', 'Kit_DoorLock', (-0.04, 0.04, -0.031, 0.0, -0.08, 0.08))

    item('Kit_DoorLock_Strike')
    k = kb('Kit_DoorLock_Strike', 'Kit')
    VM.rbox(k, (0, -0.015, 0), (0.036, 0.030, 0.150), Z_KSTEEL, r=0.003, ch=0.002, axis='y')
    k.box(-0.012, 0.012, -0.0305, -0.0295, -0.005, 0.040, Z_KBLACK)                          # the keeper slot
    k.lathe(V((0, -0.030, 0.058)), (0, -1, 0), [(0.0, 0.009), (0.004, 0.009), (0.004, 0.0065)], Z_KBLACK, 10, cap0=False, cap1=False)
    lamp_lens('Lens_DoorLock', 'Green', (0, -0.034, 0.058), (0, -1, 0), 0.0065, 'Kit_DoorLock_Strike', dome=0.004, seg=10,
              note='lock lamp: M_Kit_Lamp_Green when the lock has power (released, the door opens), _Off without (locked)')
    k.tube([V((0, -0.012, -0.075)), V((0, -0.010, -0.11)), V((0, 0.0, -0.13))], 0.004, Z_KCABLE, 5, caps=False)
    P_('Kit_DoorLock_Strike', 'static', (0, 0, 0), note='electric strike (keeper) on the frame with its lamp; origin = the middle '
                                                        'of its back on the frame')
    S_('Audio_DoorLock', (0, -0.03, 0.01), 'audio', parent='Kit_DoorLock_Strike', note='the release buzz and click')
    col('DoorLock_Strike', 'Kit_DoorLock_Strike', (-0.018, 0.018, -0.03, 0.0, -0.075, 0.075))


# ================================================================ K11 the beacon
def beacon():
    item('Kit_Beacon')
    k = kb('Kit_Beacon', 'Kit')
    k.lathe(V((0, 0, 0)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.072), (0.008, 0.072), (0.008, 0.064), (0.045, 0.060), (0.052, 0.058),
                                      (0.052, 0.0)], Z_KBLACK, 14, cap1=False)
    for a in range(0, 360, 90):
        d = V((math.cos(math.radians(a + 45)), math.sin(math.radians(a + 45)), 0))
        k.cyl(d * 0.062 + V((0, 0, 0.008)), d * 0.062 + V((0, 0, 0.012)), 0.005, Z_KSTEEL, 6)
    L = kb('Lens_Beacon', 'lens:Beacon')
    L.lathe(V((0, 0, 0.052)), (0, 0, 1), [(0.0, 0.056), (0.095, 0.056), (0.115, 0.050), (0.128, 0.034), (0.134, 0.0)], ZERO, 16,
            cap0=False)
    uv_cyl(L, V((0, 0, 0.052)), 0.0, 0.134, uv('l_beacon'))
    P_('Lens_Beacon', 'spin', (0, 0, 0.11), (0, 0, 1), None, parent='Kit_Beacon',
       note='the orange dome: M_Kit_Lamp_Beacon lit / M_Kit_Lamp_Beacon_Off; while it is lit Unity turns the dome about z with '
            'its light (80 rpm): the mirror band in the texture sweeps round')
    G = kb('Glow_Beacon', 'glow')
    for a in (0, 60, 120):
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        quad(G, (0, 0, 0.11), d, 0.40, 0.26, uv('glow_orange'), up=(0, 0, 1))
    P_('Glow_Beacon', 'static', (0, 0, 0.11), parent='Kit_Beacon', note='halo cards (additive, unlit): shown while it turns')
    P_('Kit_Beacon', 'static', (0, 0, 0), note='orange rotating beacon (Ø 0.14 m, 0.19 m tall); origin = the middle of the underside')
    S_('LIGHT_Beacon', (0, 0, 0.11), 'light', parent='Kit_Beacon', dir=(1, 0, 0), note='the rotating light (see the lights json)')
    S_('Audio_Beacon', (0, 0, 0.06), 'audio', parent='Kit_Beacon', note='the motor ticks (quiet)')
    LAMPS.append(('Beacon', V((0, 0, 0.11)), (1, 0, 0), 'beacon', (0, 0, 1)))
    LAMP_META['Beacon'] = dict(item='Kit_Beacon', lens='Lens_Beacon', glow='Glow_Beacon', spot=30, rpm=80)
    col('Beacon', 'Kit_Beacon', (-0.072, 0.072, -0.072, 0.072, 0.0, 0.186))


def build_kit():
    camera()
    monitor()
    console(2)
    console(4)
    button()
    labels()
    phone()
    cabinet()
    junction()
    conduits()
    poles()
    roofstand()
    wire_items()
    doorlock()
    beacon()
    mast()
    mast_flood()
    mast_horn()
    mast_yagi()
    mast_lamp()
    mast_antenna()
    mast_siren()
    missing = [n for n in S.ITEM_NAMES if n not in CONTRACT['parts']]
    assert not missing, missing
    return CONTRACT


# ---------------------------------------------------------------- the overhead wire (K9 rule), for previews and the Unity script
def wire_points(a, b, sag=None):
    a, b = V(a), V(b)
    span = (V((b.x, b.y, 0)) - V((a.x, a.y, 0))).length
    W = S.WIRE
    if sag is None:
        sag = max(W['sag_min'], W['sag_k'] * span * span)
    n = max(W['seg_min'], math.ceil(span / W['seg_len']))
    return [a.lerp(b, i / n) - V((0, 0, 4 * sag * (i / n) * (1 - i / n))) for i in range(n + 1)], sag


def wire_mesh(k, a, b, kind='lv', sag=None, zone=ZERO):
    pts, sag = wire_points(a, b, sag)
    k.tube(pts, S.WIRE['r_lv'] if kind == 'lv' else S.WIRE['r_bare'], zone, S.WIRE['sides'], caps=False)
    return sag
