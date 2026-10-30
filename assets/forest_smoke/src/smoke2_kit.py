"""forest_smoke 2.0 geometry (user 27.10: «модели ужасные» -> rebuilt here after the Codex concepts the user picked,
docs/gdd/concept/09_smoking/packs_1.png and lighter_1.png; the pager's recipe). Each root in its own frame (Blender: z up,
the front -y, metres; origin on the surface it stands on under its middle; Unity (x, y, z) -> (-x, z, -y)):
  Item_CigPack_Harzgold / _Nordlicht  54 x 22 x 88 mm flip-top box, the vertical edges chamfered 1.2 mm; the lid (Pack_Lid)
                       its own part hinged at the back 74 mm up, cut at 64 mm in front (the sides slant), the cigarette ends
                       and the inner board seen when it is open
  Item_CigPack_Brocken 54 x 22 x 80 mm soft paper pack, the walls a little crumpled, the top torn open: a ragged foil collar
                       and the tobacco ends
  Item_Lighter         a 1980s disposable: 25 x 12 x 58 mm chamfered body of red see-through plastic, the steel hood with
                       its slots, the ridged wheel (Lighter_Wheel, spins), the red gas lever (Lighter_Button, presses down),
                       the nozzle; the flame (Lighter_Flame) its own object over the nozzle, hidden until lit
  Cigarette            84 mm x 7.8 mm, lying along -y from its mouth end at the origin: the filter is the root (its texture
                       per brand), Cig_Paper (62 mm, pivot at the joint: the game shortens it as it burns), Cig_Tip (the
                       glowing ring, the grey ash, the glowing end)
The printed faces (panel textures, explicit UVs) are merged into their bodies at build time (MERGE)."""
import math
import random
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, face, KBS, CONTRACT, newell
from van2_kit import rrect
import smoke2_tex as ST

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
BRANDS = ST.BRANDS
ROOTS = [f'Item_CigPack_{b}' for b in BRANDS] + ['Item_Lighter', 'Cigarette']
DISPLAY = {'Item_CigPack_Harzgold': Vector((-0.09, 0.0, 0.0)), 'Item_CigPack_Brocken': Vector((0.0, 0.0, 0.0)),
           'Item_CigPack_Nordlicht': Vector((0.09, 0.0, 0.0)), 'Item_Lighter': Vector((0.17, 0.0, 0.0)),
           'Cigarette': Vector((0.24, 0.04, 0.004))}
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
# the Small atlas zones (psxbake)
(Z_GOLD, Z_PAPERB, Z_GREEN, Z_BOARD, Z_FOIL, Z_LBODY, Z_LHOOD, Z_LWHEEL, Z_LBTN, Z_CPAPER, Z_ASH) = range(600, 611)
SMALL_ZONES = list(range(600, 611))
EDGE_ZONE = {'Harzgold': Z_GOLD, 'Brocken': Z_PAPERB, 'Nordlicht': Z_GREEN}
PK = dict(w=0.054, d=0.022, h=0.088, ch=0.0012, hf=0.064, hb=0.074, hs=0.080)
LT = dict(w=0.025, d=0.012, h=0.058, ch=0.0028, hood=0.073, nozzle=(-0.0045, 0.0, 0.073))
CG = dict(r=0.0039, filt=0.022, paper=0.062, ring=0.0012, ash=0.0038, seg=8)
FLAME_BASE = Vector((LT['nozzle'][0], 0.0, LT['hood'] + 0.0032))


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


def map_rect(uvr, u, v):
    u0, v0, u1, v1 = uvr
    return (u0 + (u1 - u0) * u, v0 + (v1 - v0) * v)


# ------------------------------------------------------------------ packs
def pack_face_uv(side, p, h):
    """a point on a pack wall -> (u, v) 0..1 of that face's print (seen from outside, v up)"""
    w, d = PK['w'], PK['d']
    if side == 'front':
        return (p.x + w / 2) / w, p.z / h
    if side == 'back':
        return (w / 2 - p.x) / w, p.z / h
    if side == 'left':
        return (d / 2 - p.y) / d, p.z / h
    return (p.y + d / 2) / d, p.z / h                                      # right


def side_of(n):
    if abs(n.y) > 0.9:
        return 'front' if n.y < 0 else 'back'
    if abs(n.x) > 0.9:
        return 'left' if n.x < 0 else 'right'
    return None                                                            # a chamfer


def flip_pack(brand):
    root = f'Item_CigPack_{brand}'
    w, d, h, ch, hf, hb = PK['w'], PK['d'], PK['h'], PK['ch'], PK['hf'], PK['hb']
    edge = EDGE_ZONE[brand]
    body, bp = reg(root, 'Small', root), reg(root + '_Print', 'panel_' + brand, root, merge=root)
    lid, lp = reg('Pack_Lid_' + brand, 'Small', root), reg('Pack_Lid_' + brand + '_Print', 'panel_' + brand, root, merge='Pack_Lid_' + brand)
    ring = rrect(Vector((0, 0, 0)), X, Y, w, d, ch, 1)                     # CCW seen from above
    n = len(ring)

    def ztop(p):
        return hf + (hb - hf) * (p.y + d / 2) / d

    for j in range(n):
        a, b = ring[j], ring[(j + 1) % n]
        mid = (a + b) / 2
        nrm = Vector((mid.x, mid.y, 0))
        side = side_of(Vector((b.y - a.y, -(b.x - a.x), 0)).normalized())
        for kk, kp, z0a, z0b, z1a, z1b in ((body, bp, 0.0, 0.0, ztop(a), ztop(b)), (lid, lp, ztop(a), ztop(b), h, h)):
            pts = [Vector((a.x, a.y, z0a)), Vector((b.x, b.y, z0b)), Vector((b.x, b.y, z1b)), Vector((a.x, a.y, z1a))]
            if side is None:
                face(kk, pts, edge, out=nrm)
            else:
                r = ST.pack_uv(side)
                poly_uv(kp, pts, [map_rect(r, *pack_face_uv(side, p, h)) for p in pts], nrm)
    # bottom and the lid's top: printed
    bot = [Vector((p.x, p.y, 0.0)) for p in ring]
    poly_uv(bp, bot, [map_rect(ST.pack_uv('bottom'), (w / 2 - p.x) / w, (p.y + d / 2) / d) for p in bot], -Z)
    top = [Vector((p.x, p.y, h)) for p in ring]
    poly_uv(lp, top, [map_rect(ST.pack_uv('top'), (p.x + w / 2) / w, (p.y + d / 2) / d) for p in top], Z)
    # inside: the cigarette ends 4 mm under the front cut, the board walls above them, the lid's board inside
    t = 0.0006
    zi = hf - 0.004
    ins = [Vector((-w / 2 + t, -d / 2 + t, zi)), Vector((w / 2 - t, -d / 2 + t, zi)), Vector((w / 2 - t, d / 2 - t, zi)), Vector((-w / 2 + t, d / 2 - t, zi))]
    poly_uv(bp, ins, [map_rect(ST.pack_uv('inner'), (p.x + w / 2) / w, (p.y + d / 2) / d) for p in ins], Z)
    for i in range(4):
        a, b = ins[i], ins[(i + 1) % 4]
        c = Vector((0, 0, 0))
        face(body, [a, b, Vector((b.x, b.y, ztop(b) - 0.0002)), Vector((a.x, a.y, ztop(a) - 0.0002))], Z_BOARD,
             out=c - Vector((((a + b) / 2).x, ((a + b) / 2).y, 0)))
        la = Vector((a.x, a.y, ztop(a) + 0.0002)), Vector((b.x, b.y, ztop(b) + 0.0002))
        face(lid, [la[0], la[1], Vector((b.x, b.y, h - t)), Vector((a.x, a.y, h - t))], Z_BOARD,
             out=c - Vector((((a + b) / 2).x, ((a + b) / 2).y, 0)))
        face(lid, [la[0], la[1], Vector((b.x, b.y, ztop(b))), Vector((a.x, a.y, ztop(a)))], Z_BOARD, out=-Z)   # the lid's cut edge
        face(body, [Vector((a.x, a.y, ztop(a) - 0.0002)), Vector((b.x, b.y, ztop(b) - 0.0002)),
                    Vector((b.x * (w / 2) / (w / 2 - t), b.y * (d / 2) / (d / 2 - t), ztop(b))),
                    Vector((a.x * (w / 2) / (w / 2 - t), a.y * (d / 2) / (d / 2 - t), ztop(a)))], Z_BOARD, out=Z)   # the body's cut edge
    face(lid, [Vector((p.x, p.y, h - t)) for p in ins], Z_BOARD, out=-Z)
    part(root, 'item', (0, 0, 0), note=f'a pack of 20 {brand} (root): flip-top box standing on its bottom, the front to -y')
    part('Pack_Lid_' + brand, 'hinge', (0.0, d / 2, hb), axis=(-1, 0, 0), rng=(0, 115), parent=root,
         note='the flip-top lid: hinged at the back 74 mm up, opens backwards (the game opens it while taking one out)')
    socket('Take_' + brand, (0.0, 0.0, hf), 'point', parent=root, dir=(0, 0, 1), note='where a cigarette comes out of the pack')
    MASS[root] = 0.025
    BOXES.append((brand, root, (-w / 2, w / 2, -d / 2, d / 2, 0.0, h), None))


def soft_pack(brand):
    root = f'Item_CigPack_{brand}'
    w, d, hs = PK['w'], PK['d'], PK['hs']
    body, bp = reg(root, 'Small', root), reg(root + '_Print', 'panel_' + brand, root, merge=root)
    rnd = random.Random(27)
    nu, nv = 4, 5
    corners = [Vector((-w / 2, -d / 2, 0)), Vector((w / 2, -d / 2, 0)), Vector((w / 2, d / 2, 0)), Vector((-w / 2, d / 2, 0))]
    for i, side in enumerate(('front', 'right', 'back', 'left')):
        a, b = corners[i], corners[(i + 1) % 4]
        nrm = Vector((b.y - a.y, -(b.x - a.x), 0)).normalized()
        cols = nu if side in ('front', 'back') else 2
        grid = {}
        for iu in range(cols + 1):
            for iv in range(nv + 1):
                base = a + (b - a) * (iu / cols) + Z * (hs * iv / nv)
                inner = 0 < iu < cols and 0 < iv < nv
                grid[iu, iv] = (base + nrm * (rnd.uniform(-0.0007, 0.0004) if inner else 0.0), base)
        r = ST.pack_uv(side)
        for iu in range(cols):
            for iv in range(nv):
                q = [grid[iu, iv], grid[iu + 1, iv], grid[iu + 1, iv + 1], grid[iu, iv + 1]]
                for tri in ((0, 1, 2), (0, 2, 3)):                                        # crumpled: triangles stay flat
                    pts = [q[t][0] for t in tri]
                    poly_uv(bp, pts, [map_rect(r, *pack_face_uv(side, q[t][1], hs)) for t in tri], nrm)
    bot = [Vector((c.x, c.y, 0.0)) for c in corners]
    poly_uv(bp, bot, [map_rect(ST.pack_uv('bottom'), (w / 2 - p.x) / w, (p.y + d / 2) / d) for p in bot], -Z)
    # the torn top: the paper's rim, a ragged foil collar standing up inside it, the tobacco ends below
    t = 0.0008
    zi = hs - 0.002
    ins = [Vector((-w / 2 + t, -d / 2 + t, zi)), Vector((w / 2 - t, -d / 2 + t, zi)), Vector((w / 2 - t, d / 2 - t, zi)), Vector((-w / 2 + t, d / 2 - t, zi))]
    poly_uv(bp, ins, [map_rect(ST.pack_uv('inner'), (p.x + w / 2) / w, (p.y + d / 2) / d) for p in ins], Z)
    rim = []
    for i in range(4):                                                                     # 12 points round the top
        a, b = corners[i], corners[(i + 1) % 4]
        steps = 4 if i % 2 == 0 else 2
        for s in range(steps):
            rim.append(a + (b - a) * (s / steps))
    m = len(rim)
    for i in range(m):                                                                     # the paper's rim (a narrow ledge)
        a, b = rim[i], rim[(i + 1) % m]
        ai, bi = Vector((a.x * (1 - 2 * t / w), a.y * (1 - 2 * t / d), 0)), Vector((b.x * (1 - 2 * t / w), b.y * (1 - 2 * t / d), 0))
        face(body, [Vector((a.x, a.y, hs)), Vector((b.x, b.y, hs)), Vector((bi.x, bi.y, hs)), Vector((ai.x, ai.y, hs))], Z_PAPERB, out=Z)
    tops = [hs + rnd.uniform(0.0015, 0.0075) for _ in range(m)]
    for i in range(m):
        a, b = rim[i], rim[(i + 1) % m]
        ai, bi = Vector((a.x * (1 - 2 * t / w), a.y * (1 - 2 * t / d), 0)), Vector((b.x * (1 - 2 * t / w), b.y * (1 - 2 * t / d), 0))
        nrm = Vector((b.y - a.y, -(b.x - a.x), 0))
        q = [Vector((ai.x, ai.y, zi)), Vector((bi.x, bi.y, zi)), Vector((bi.x, bi.y, tops[(i + 1) % m])), Vector((ai.x, ai.y, tops[i]))]
        face(body, q, Z_FOIL, out=nrm)
        face(body, list(reversed(q)), Z_FOIL, out=-nrm)                                    # the foil seen from inside
    part(root, 'item', (0, 0, 0), note=f'a soft pack of 20 {brand} without filter (root): the top torn open, foil and '
                                        'tobacco ends showing; standing on its bottom, the front to -y')
    socket('Take_' + brand, (0.0, 0.0, hs), 'point', parent=root, dir=(0, 0, 1), note='where a cigarette comes out of the pack')
    MASS[root] = 0.024
    BOXES.append((brand, root, (-w / 2, w / 2, -d / 2, d / 2, 0.0, hs + 0.006), None))


# ------------------------------------------------------------------ lighter
def lighter():
    root = 'Item_Lighter'
    w, d, h, ch, hz = LT['w'], LT['d'], LT['h'], LT['ch'], LT['hood']
    k = reg(root, 'Small', root)
    kp = reg('Lighter_Print', 'lpanel', root, merge=root)
    ring = rrect(Vector((0, 0, 0)), X, Y, w, d, ch, 1)
    n = len(ring)
    for j in range(n):
        a, b = ring[j], ring[(j + 1) % n]
        face(k, [Vector((a.x, a.y, 0)), Vector((b.x, b.y, 0)), Vector((b.x, b.y, h)), Vector((a.x, a.y, h))], Z_LBODY,
             out=Vector((((a + b) / 2).x, ((a + b) / 2).y, 0)))
    face(k, [Vector((p.x, p.y, 0)) for p in ring], Z_LBODY, out=-Z)
    face(k, [Vector((p.x, p.y, h)) for p in ring], Z_LBODY, out=Z)
    # the steel hood over the left two thirds, its top left corner bevelled; the side plates either side of the wheel
    x0, x1, y0, y1 = -w / 2 + 0.0005, 0.0035, -d / 2 + 0.0004, d / 2 - 0.0004
    K.prism_y(k, [(x0, h - 0.0015), (x1, h - 0.0015), (x1, hz), (x0 + 0.003, hz), (x0, hz - 0.003)], y0, y1, Z_LHOOD, Z_LHOOD)
    for yy in (y0, y1 - 0.0008):
        k.box(x1, w / 2 - 0.0012, yy, yy + 0.0008, h - 0.0015, hz - 0.002, Z_LHOOD)
    nz = Vector(LT['nozzle'])
    k.cyl(nz, nz + Z * 0.0028, 0.0016, Z_LHOOD, 8)                                          # the nozzle
    # the BLITZ label on the front, a hair proud
    poly_uv(kp, [Vector((-0.008, -d / 2 - 0.0002, 0.040)), Vector((0.008, -d / 2 - 0.0002, 0.040)),
                 Vector((0.008, -d / 2 - 0.0002, 0.046)), Vector((-0.008, -d / 2 - 0.0002, 0.046))],
            [map_rect(ST.lighter_uv('label'), u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))], -Y)
    # the wheel (spins about y) and the gas lever (presses down)
    wc = Vector((0.0074, 0.0, hz - 0.0016))
    kw = reg('Lighter_Wheel', 'Small', root)
    kw.cyl(wc - Y * 0.0042, wc + Y * 0.0042, 0.0041, Z_LWHEEL, 12)
    part('Lighter_Wheel', 'spin', wc, axis=(0, 1, 0), parent=root, note='the flint wheel: the thumb rolls it towards the user')
    kb_ = reg('Lighter_Button', 'Small', root)
    bx0, bx1 = 0.0040, w / 2 - 0.0004
    K.prism_y(kb_, [(bx0, h), (bx1, h), (bx1, h + 0.0062), (bx0 + 0.002, h + 0.0062)], -0.0045, 0.0045, Z_LBTN, Z_LBTN)
    part('Lighter_Button', 'slide', (bx0, 0.0, h), axis=(0, 0, -1), rng=(0.0, 0.0015), unit='m', parent=root,
         note='the gas lever under the wheel: held down while it burns')
    # the flame: a narrow double cone over the nozzle, its own emissive material, hidden in the game until lit
    kf = reg('Lighter_Flame', 'flame', root)
    fb, ftop = FLAME_BASE, FLAME_BASE + Z * 0.022
    rr = [FLAME_BASE + Z * 0.006 + Vector((0.0032 * math.cos(a), 0.0032 * math.sin(a), 0)) for a in (0, math.pi / 2, math.pi, 1.5 * math.pi)]
    u0, v0, u1, v1 = ST.lighter_uv('flame')
    um = (u0 + u1) / 2
    vm = v0 + (v1 - v0) * 0.28
    for j in range(4):
        p, q = rr[j], rr[(j + 1) % 4]
        out = (p + q) / 2 - FLAME_BASE - Z * 0.006
        poly_uv(kf, [fb, q, p], [(um, v0), (u1, vm), (u0, vm)], out - Z * 0.002)
        poly_uv(kf, [p, q, ftop], [(u0, vm), (u1, vm), (um, v1)], out + Z * 0.002)
    part('Lighter_Flame', 'static', FLAME_BASE, parent=root, note='the flame (M_Lighter_Flame, emissive): hidden until lit, '
                                                                   'the game flickers its height (scale z from the base)')
    socket('Socket_Flame', FLAME_BASE, 'light', parent=root, dir=(0, 0, 1), color=[1.0, 0.7, 0.35], range=3.5,
           note='the flame\'s base: a small warm point light while lit; a cigarette is lit here')
    part(root, 'item', (0, 0, 0), note='a disposable gas lighter BLITZ (root): standing on its bottom, the label to -y')
    MASS[root] = 0.02
    BOXES.append(('Lighter', root, (-w / 2, w / 2, -d / 2, d / 2, 0.0, hz), None))


# ------------------------------------------------------------------ cigarette
def cigarette():
    root = 'Cigarette'
    r, fl, pl, rg, ash, seg = CG['r'], CG['filt'], CG['paper'], CG['ring'], CG['ash'], CG['seg']
    kf = reg(root, 'filter', root)
    ring = lambda yy, rad: [Vector((rad * math.cos(2 * math.pi * i / seg), yy, rad * math.sin(2 * math.pi * i / seg))) for i in range(seg)]
    a, b = ring(0.0, r), ring(-fl, r)
    vj, vm = 1.0, 4 / 32                                                    # the filter texture: the joint at the top row
    for i in range(seg):
        i2 = (i + 1) % seg
        mid = (a[i] + a[i2]) / 2
        poly_uv(kf, [a[i], a[i2], b[i2], b[i]], [(i / seg, vm), ((i + 1) / seg, vm), ((i + 1) / seg, vj), (i / seg, vj)],
                Vector((mid.x, 0.0, mid.z)))
    poly_uv(kf, a, [(0.5 + 0.45 * math.cos(2 * math.pi * i / seg), (0.5 + 0.45 * math.sin(2 * math.pi * i / seg)) * vm) for i in range(seg)], Y)
    kp = reg('Cig_Paper', 'Small', root)
    kp.cyl(Vector((0, -fl, 0)), Vector((0, -fl - pl, 0)), r, Z_CPAPER, seg, caps=False)
    part('Cig_Paper', 'stretch', (0.0, -fl, 0.0), axis=(0, -1, 0), parent=root,
         note='the paper: the game scales it along its axis (1 new .. 0 burnt down to the filter)')
    kt = reg('Cig_Tip', 'Small', root)
    ke = reg('Cig_Tip_Ember', 'ember', root, merge='Cig_Tip')
    y0 = -fl - pl
    e0, e1 = ring(y0, r), ring(y0 - rg, r * 0.99)                           # the glowing ring next to the paper
    for i in range(seg):
        i2 = (i + 1) % seg
        poly_uv(ke, [e0[i], e0[i2], e1[i2], e1[i]], [(0, 0), (1, 0), (1, 1), (0, 1)], (e0[i] + e0[i2]) / 2 - Vector((0, y0, 0)))
    rnd = random.Random(84)
    jag = [Vector((p.x * rnd.uniform(0.86, 1.0), y0 - rg - ash + rnd.uniform(0, 0.0012), p.z * rnd.uniform(0.86, 1.0))) for p in e1]
    for i in range(seg):                                                    # the grey ash, a ragged end
        i2 = (i + 1) % seg
        face(kt, [e1[i], e1[i2], jag[i2], jag[i]], Z_ASH, out=(e1[i] + e1[i2]) / 2 - Vector((0, y0, 0)))
    yc = sum(p.y for p in jag) / seg
    poly_uv(ke, jag, [(0.5 + 0.5 * math.cos(2 * math.pi * i / seg), 0.5 + 0.5 * math.sin(2 * math.pi * i / seg)) for i in range(seg)],
            Vector((0, -1, 0)))
    part('Cig_Tip', 'static', (0.0, y0, 0.0), parent=root, note='the burning end: the glowing ring and end (M_Cig_Ember, the '
                                                                  'game drives its emission), the grey ash between; moved to '
                                                                  'the paper\'s end as it burns')
    part(root, 'item', (0, 0, 0), note='a cigarette (root = the filter, its texture per brand): the mouth end at the origin, '
                                       'along -y (Unity +Z); shown in the mouth and as a butt, never a loose item')
    socket('Mouth', (0, 0, 0), 'point', parent=root, dir=(0, 1, 0), note='the mouth end')
    MASS[root] = 0.001


def build_all():
    for b in BRANDS:
        if b == 'Brocken':
            soft_pack(b)
        else:
            flip_pack(b)
    lighter()
    cigarette()
