"""forest_beer geometry (user 29.10, docs/gdd/items/beer: five cans after concept_v1/cans_1.png and 30.10 the sixth,
Kaloschnizzer, after concept_v2/kalo_front_1.png; the tab opens on all of them, a crushed can of each). Each root in its own frame (Blender: z up, the front -y, metres; origin on the bottom under the
middle; Unity (x, y, z) -> (-x, z, -y)):
  Item_Beer_<Brand>         a 1991 steel can, 16 sides, real size (0.5 l: 66 x 168 mm, 0.33 l: 66 x 115 mm): the domed
                            bottom and its foot ring, the straight side with the printed label (its own texture per brand,
                            explicit UVs, merged into the body), the neck, the rolled rim, the lid sunk 3.5 mm with the opening
                            cut in it; under the lid the dark inside (seen when it is open)
    Can_Tab_<Brand>         the stay-on tab on its rivet: lifts its ring end (hinge about x through the rivet), the nose pushes
    Can_Flap_<Brand>        the scored flap: hinged at its edge nearest the middle, swings down into the can
  Item_BeerCrushed_<Brand>  the same can after drinking (tab up 12 degrees, flap in), stamped down to ~36 % with folds: one
                            mesh, the same label texture and atlas
Opening (the game plays it, QUESTIONS.md 21: code moves the parts; the file has the action 'Open' for the views):
  tab 0 -> 70 degrees in 0.4 s while the flap follows to 82, the tab back to 12 (rest open)."""
import math
import random
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, face, KBS, CONTRACT, newell
import beer_tex as BT

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
BRANDS = BT.BRANDS
ROOTS = [f'Item_Beer_{b}' for b in BRANDS] + [f'Item_BeerCrushed_{b}' for b in BRANDS]
DISPLAY = {}
for i, b in enumerate(BRANDS):
    DISPLAY[f'Item_Beer_{b}'] = Vector(((i - (len(BRANDS) - 1) / 2) * 0.09, 0.0, 0.0))
    DISPLAY[f'Item_BeerCrushed_{b}'] = Vector(((i - (len(BRANDS) - 1) / 2) * 0.09, 0.13, 0.0))
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
(Z_METAL, Z_LID, Z_TAB, Z_INSIDE, Z_RIM) = range(700, 705)
SMALL_ZONES = list(range(700, 705))
SEG = 16
CAN = dict(r=0.033, foot=0.009, neck=0.011, rl=0.0272, lid=0.0035)
HEIGHT = {0.5: 0.168, 0.33: 0.115}
FLAP = dict(c=(0.0, -0.0135), ax=0.0085, ay=0.0068)                    # the opening: an oval in front of the rivet
TAB = dict(h=(0.0, 0.0060), ax=0.0062, up=0.0065, down=0.0145, hx=0.0042, hy=0.0032, t=0.0005)
OPEN = dict(tab_max=70.0, tab_rest=12.0, flap=82.0)


def part(name, *a, **kw):
    assert name not in CONTRACT['parts'], f'part {name} twice'
    K.part(name, *a, **kw)


def socket(name, *a, **kw):
    assert name not in CONTRACT['sockets'], f'socket {name} twice'
    K.socket(name, *a, **kw)


def reg(name, atlas, root, merge=None):
    ROOT_OF[name] = root
    if merge:
        MERGE[name] = merge
    return kb(name, atlas)


def poly_uv(k, pts, uvs, out):
    pts = [Vector(p) for p in pts]
    if newell(pts).dot(Vector(out)) < 0:
        pts, uvs = list(reversed(pts)), list(reversed(uvs))
    return k.poly(pts, 0.0, uvs)


def ring(r, z, seg=SEG):
    """points round the axis; i = 0 at the back (+y), going round to +x through the front (-y) at i = seg / 2"""
    out = []
    for i in range(seg + 1):
        th = -math.pi + 2 * math.pi * i / seg
        out.append(Vector((r * math.sin(th), -r * math.cos(th), z)))
    return out


def band(k, r0, z0, r1, z1, zone):
    """a ring of quads from profile point (r0, z0) to (r1, z1); it faces (dz, -dr) in (radius, z): walk the profile so that
    the outside is on the right (up the outer wall, inwards over a top, outwards under a foot, down an inner wall)"""
    a, b = ring(r0, z0), ring(r1, z1)
    dr, dz = r1 - r0, z1 - z0
    for i in range(SEG):
        q = [a[i], a[i + 1], b[i + 1], b[i]]
        rad = (q[0] + q[1]).normalized() if (q[0] + q[1]).length > 1e-9 else Vector((0, 0, 0))
        rad.z = 0.0
        out = rad.normalized() * dz + Z * (-dr)
        face(k, q, zone, out=out)


def disc(k, r, z, zone, up=True):
    face(k, ring(r, z)[:SEG], zone, out=Z if up else -Z)


def oval(c, ax, ay, n=24):
    return [Vector((c[0] + ax * math.cos(2 * math.pi * j / n), c[1] + ay * math.sin(2 * math.pi * j / n), 0.0)) for j in range(n)]


def ray_circle(c, d, R):
    """t > 0 where c + t d meets the circle |p| = R (c inside)"""
    b = c.dot(d)
    cc = c.dot(c) - R * R
    return -b + math.sqrt(b * b - cc)


# ------------------------------------------------------------------ one can (into the given KBs)
def can_body(k, kl, H, label_rings=1):
    """the shell: bottom dome, foot, the label side (kl, explicit UVs), neck, rim, the inside under the lid"""
    r, foot, neck = CAN['r'], CAN['foot'], CAN['neck']
    zl = H - CAN['lid']
    disc(k, 0.019, 0.0045, Z_METAL, up=False)                               # the dome seen from below
    band(k, 0.019, 0.0045, 0.0245, 0.0, Z_METAL)
    band(k, 0.0245, 0.0, 0.0285, 0.0, Z_RIM)                                 # the foot ring the can stands on
    band(k, 0.0285, 0.0, r, foot, Z_METAL)
    z0, z1 = foot, H - neck
    for j in range(label_rings):
        za, zb = z0 + (z1 - z0) * j / label_rings, z0 + (z1 - z0) * (j + 1) / label_rings
        va, vb = j / label_rings, (j + 1) / label_rings
        a, b = ring(r, za), ring(r, zb)
        for i in range(SEG):
            q = [a[i], a[i + 1], b[i + 1], b[i]]
            uv = [(i / SEG, va), ((i + 1) / SEG, va), ((i + 1) / SEG, vb), (i / SEG, vb)]
            mid = (a[i] + a[i + 1]) / 2
            poly_uv(kl, q, uv, Vector((mid.x, mid.y, 0)))
    band(k, r, z1, 0.0292, H - 0.0035, Z_METAL)                              # the neck
    band(k, 0.0292, H - 0.0035, 0.0296, H, Z_RIM)                            # the rolled rim
    band(k, 0.0296, H, 0.0278, H, Z_RIM)
    band(k, 0.0278, H, CAN['rl'], zl, Z_RIM)                    # the rim's inner wall down to the lid
    # inside: a short dark wall under the lid and the dark floor (beer / shadow) 16 mm down
    band(k, CAN['rl'] - 0.0004, zl - 0.0002, CAN['rl'] - 0.0004, zl - 0.016, Z_INSIDE)
    disc(k, CAN['rl'] - 0.0004, zl - 0.016, Z_INSIDE, up=True)


def can_lid(k, H):
    """the lid with the oval opening cut out (rays from the opening's middle out to the lid's edge), the rivet"""
    zl = H - CAN['lid']
    c = Vector((FLAP['c'][0], FLAP['c'][1], 0.0))
    hole = oval(FLAP['c'], FLAP['ax'], FLAP['ay'])
    n = len(hole)
    outer = []
    for p in hole:
        d = (p - c).normalized()
        outer.append(c + d * ray_circle(c, d, CAN['rl']))
    for j in range(n):
        a, b = hole[j], hole[(j + 1) % n]
        A, B = outer[j], outer[(j + 1) % n]
        face(k, [Vector((a.x, a.y, zl)), Vector((b.x, b.y, zl)), Vector((B.x, B.y, zl)), Vector((A.x, A.y, zl))], Z_LID, out=Z)
        # the cut's edge: a 0.4 mm lip down into the can
        face(k, [Vector((a.x, a.y, zl)), Vector((b.x, b.y, zl)), Vector((b.x, b.y, zl - 0.0004)), Vector((a.x, a.y, zl - 0.0004))],
             Z_LID, out=c - (a + b) / 2)
    k.cyl(Vector((0, 0, zl)), Vector((0, 0, zl + 0.0011)), 0.0018, Z_LID, 8)  # the rivet


def flap_mesh(k, H):
    zl = H - CAN['lid']
    pts = [Vector((p.x, p.y, zl + 0.0001)) for p in oval(FLAP['c'], FLAP['ax'] * 0.97, FLAP['ay'] * 0.97)]
    face(k, pts, Z_LID, out=Z)
    face(k, [p - Z * 0.0003 for p in pts], Z_LID, out=-Z)                    # its underside, seen when it is pushed in


def tab_mesh(k, H):
    """the tab: a flat plate round a finger hole, its nose over the flap; top, bottom and the outer and hole edges"""
    zt = H - CAN['lid'] + 0.0011
    zb = zt - TAB['t']
    h = Vector((TAB['h'][0], TAB['h'][1], 0.0))
    n = 28
    hole, outer = [], []
    for j in range(n):
        a = 2 * math.pi * j / n
        ca, sa = math.cos(a), math.sin(a)
        e = 2.6                                                              # a superellipse: a rounded-off oblong
        ry = TAB['up'] if sa >= 0 else TAB['down']
        rx = TAB['ax'] * (1.0 if sa >= 0 else 1.0 - 0.35 * (-sa) ** 2)       # the nose narrows
        f = lambda v: math.copysign(abs(v) ** (2 / e), v)
        outer.append(h + Vector((rx * f(ca), ry * f(sa), 0)))
        hole.append(h + Vector((TAB['hx'] * f(ca), TAB['hy'] * f(sa), 0)))
    for j in range(n):
        a, b, A, B = hole[j], hole[(j + 1) % n], outer[j], outer[(j + 1) % n]
        face(k, [a + Z * zt, b + Z * zt, B + Z * zt, A + Z * zt], Z_TAB, out=Z)
        face(k, [a + Z * zb, b + Z * zb, B + Z * zb, A + Z * zb], Z_TAB, out=-Z)
        face(k, [A + Z * zb, B + Z * zb, B + Z * zt, A + Z * zt], Z_TAB, out=(A + B) / 2 - h)
        face(k, [a + Z * zb, b + Z * zb, b + Z * zt, a + Z * zt], Z_TAB, out=h - (a + b) / 2)


def tab_pivot(H):
    return Vector((0.0, 0.0, H - CAN['lid'] + 0.0011 - TAB['t'] / 2))


def flap_pivot(H):
    return Vector((0.0, FLAP['c'][1] + FLAP['ay'] * 0.97, H - CAN['lid']))


# ------------------------------------------------------------------ the roots
def can(brand):
    root = f'Item_Beer_{brand}'
    L = BT.LITRES[brand]
    H = HEIGHT[L]
    body = reg(root, 'Small', root)
    lab = reg(root + '_Label', 'label_' + brand, root, merge=root)
    can_body(body, lab, H)
    can_lid(body, H)
    tab = reg('Can_Tab_' + brand, 'Small', root)
    tab_mesh(tab, H)
    flap = reg('Can_Flap_' + brand, 'Small', root)
    flap_mesh(flap, H)
    part(root, 'item', (0, 0, 0), note=f'{BT.NAME[brand]}, {L} l, {BT.ABV[brand]} % (root): a steel can standing on its '
                                       'foot, the label\'s front to -y')
    part('Can_Tab_' + brand, 'hinge', tab_pivot(H), axis=(1, 0, 0), rng=(0, 85), parent=root,
         states=[dict(name='closed', value=0), dict(name='open', value=OPEN['tab_rest']), dict(name='lever', value=OPEN['tab_max'])],
         note='the stay-on tab on the rivet: + lifts the ring end (+y), the nose dips onto the flap; open = 0 -> 70 -> 12')
    part('Can_Flap_' + brand, 'hinge', flap_pivot(H), axis=(1, 0, 0), rng=(0, 90), parent=root,
         states=[dict(name='closed', value=0), dict(name='open', value=OPEN['flap'])],
         note='the scored flap: hinged at its edge nearest the rivet, + swings its front down into the can (follows the tab\'s nose)')
    socket('Mouth_' + brand, (FLAP['c'][0], FLAP['c'][1], H), 'point', parent=root, dir=(0, 0, 1),
           note='the opening: where the lips go, where the foam and the hiss come out')
    MASS[root] = round(L * 1.03 + 0.03, 3)
    BOXES.append((brand, root, (-CAN['r'], CAN['r'], -CAN['r'], CAN['r'], 0.0, H), None))


def crushed(brand):
    """the same shell with 6 label rings, tab and flap set open, stamped down with folds"""
    root = f'Item_BeerCrushed_{brand}'
    L = BT.LITRES[brand]
    H = HEIGHT[L]
    body = reg(root, 'Small', root)
    lab = reg(root + '_Label', 'label_' + brand, root, merge=root)
    can_body(body, lab, H, label_rings=6)
    can_lid(body, H)
    t = K.KB()
    tab_mesh(t, H)
    K.merge_kb(body, t, K.rot_about(tab_pivot(H), X, OPEN['tab_rest']))
    f = K.KB()
    flap_mesh(f, H)
    K.merge_kb(body, f, K.rot_about(flap_pivot(H), X, OPEN['flap']))
    rnd = random.Random(hash(brand) & 0xffff)
    ph = rnd.uniform(0, 6.28)
    tilt = rnd.uniform(-0.25, 0.25)

    sq = rnd.uniform(0.72, 0.85)                                            # stepped on: a little flattened sideways

    def stamp(p):
        tt = max(0.0, min(1.0, p.z / H))
        th = math.atan2(p.x, -p.y)
        rr = math.hypot(p.x, p.y)
        mid = math.sin(math.pi * tt)
        fold = mid * (0.5 + 0.5 * math.sin(4 * th + ph + 9 * tt))                          # the accordion: diamond folds
        rr2 = rr * (1.0 + 0.32 * fold) if rr > 0.02 else rr
        z2 = H * 0.36 * tt + 0.009 * math.sin(3 * th + ph) * mid                           # stamped down, the folds wave
        z2 += tilt * 0.03 * tt * math.sin(th)                                               # the top a little askew
        x2, y2 = rr2 * math.sin(th), -rr2 * math.cos(th)
        return Vector((x2 / sq ** 0.5, y2 * sq, max(z2, 0.0)))

    for k_ in (body, lab):
        for v in k_.bm.verts:
            v.co = stamp(v.co)
    part(root, 'item', (0, 0, 0), note=f'a crushed empty {BT.NAME[brand]} can (root): stamped down to 36 %, folded, tab up, '
                                       'flap in; lies in the world for ever (QUESTIONS.md 6)')
    MASS[root] = 0.02
    hr = CAN['r'] * 1.4
    BOXES.append(('Crushed_' + brand, root, (-hr, hr, -hr * 0.9, hr * 0.9, 0.0, H * 0.36 + 0.01), None))


def build_all():
    for b in BRANDS:
        can(b)
    for b in BRANDS:
        crushed(b)
