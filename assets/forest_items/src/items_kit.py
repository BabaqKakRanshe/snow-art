"""Forest items (Update 6): the 83 small things of Update 3 (Item_*) rebuilt in the generator shed's look, and the control
room's radio set (Item_RadioSet, new). Each item is built in its own frame - the frame of Update 3's FBX after import:
x / y / z, z up, Unity prefab-local (-x, z, -y) - with Update 3's origin (bottom centre; keys and the padlock: the
hanging point on top; the flashlight: its centre) and Update 3's size (Forest_Items.json colliders and every placement
stay valid); a few Update 3 models sank into the surface they lie on (z < 0) - those now rest on it.
One KB per item (atlas Items: the shed's painter rules, items_paint), its printed faces in a second KB (atlas panel:
items_tex), the flashlight's glass (M_TorchLens, the game swaps it to M_TorchLensOn) and the bucket's water (M_Water)
in their own KBs; items_build joins them into one mesh per item, as Update 3's.
Zones: see Z_* below (items_paint paints them)."""
import math
import bmesh
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, box6, face
from van2_kit import rrect
import van3_mech as VM
import items_tex as IT

TAU = 2 * math.pi
(Z_PAPER, Z_PAPERY, Z_CARD, Z_CARDG, Z_CLOTH_R, Z_CLOTH_G, Z_CLOTH_B, Z_PP_B, Z_PP_R, Z_TIN, Z_RUSTT, Z_ENW, Z_ENG,
 Z_ENBK, Z_ENBL, Z_STEELB, Z_STEEL, Z_GALV, Z_ALU, Z_BRASS, Z_CHROME, Z_PAINT_R, Z_PAINT_O, Z_PAINT_B, Z_PAINT_Y,
 Z_PAINT_G, Z_PL_BK, Z_PL_BE, Z_PL_R, Z_PL_BL, Z_PL_GR, Z_PL_W, Z_RUBBER, Z_WOOD, Z_PINE, Z_FAB_O, Z_FAB_B, Z_FAB_G,
 Z_JUTE, Z_LEATHER, Z_GLASS_BR, Z_GLASS_GR, Z_GLASS_CL, Z_BREAD, Z_CRUMB, Z_SOAP, Z_ROPE, Z_STRAW, Z_MOPS, Z_BAG,
 Z_FOAM, Z_CIG, Z_FILTER, Z_ASH, Z_TERRY, Z_RUG, Z_PICKLE, Z_FOOD, Z_CABLE_O, Z_TAPE, Z_HARDB, Z_GLASS_ASH, Z_TISSUE,
 Z_GREYM, Z_ENBL_IN, Z_COFFEE) = range(100, 166)
ZONES = list(range(100, 166))
ITEMS = {}          # Item_X -> builder(k, pk, item_name)
SPECIAL = {}        # Item_X -> {'lens': [...], 'water': [...]} extra KB names


def item(name):
    def deco(fn):
        ITEMS[name] = fn
        return fn
    return deco


def uv(name):
    return IT.uv(name)


def sub_uv(name, fx0, fy0, fx1, fy1):
    """a part of a panel region: fractions of its width (left -> right) and height (top -> bottom of the image)"""
    x0, y0, x1, y1 = IT.REG[name]
    w, h = x1 - x0, y1 - y0
    r = (x0 + int(round(fx0 * w)), y0 + int(round(fy0 * h)), x0 + max(int(round(fx1 * w)), int(round(fx0 * w)) + 1),
         y0 + max(int(round(fy1 * h)), int(round(fy0 * h)) + 1))
    import van2_tex as VT
    return VT.uv(r, IT.N)


# ================================================================ helpers
def sheet(k, pk, x0, x1, y0, y1, z0, t, top_uv, bot_uv=None, bot_zone=Z_PAPER, edge_zone=Z_PAPER, nx=4, ny=6,
          lift=None, rot=0.0, centre=(0.0, 0.0)):
    """a thin sheet (paper, card): the top printed (pk, top_uv), the bottom printed (bot_uv) or in k's bot_zone, the edges
    in k; lift(x, y) bends it (z offset); rot (deg) turns it about z through `centre`"""
    lift = lift or (lambda x, y: 0.0)
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cx, cy = centre

    def P(x, y, z):
        dx, dy = x - cx, y - cy
        return Vector((cx + ca * dx - sa * dy, cy + sa * dx + ca * dy, z))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    Zb = [[z0 + lift(x, y) for x in xs] for y in ys]
    u0, v0, u1, v1 = top_uv
    for j in range(ny):
        for i in range(nx):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            pts = [P(xs[a], ys[b], Zb[b][a] + t) for a, b in q]
            uvs = [(u0 + (u1 - u0) * a / nx, v0 + (v1 - v0) * b / ny) for a, b in q]
            pk.poly(pts, 0.0, uvs)
            ptsb = [P(xs[a], ys[b], Zb[b][a]) for a, b in reversed(q)]
            if bot_uv is not None:
                b0, c0, b1, c1 = bot_uv
                uvb = [(b1 - (b1 - b0) * a / nx, c0 + (c1 - c0) * b / ny) for a, b in reversed(q)]
                pk.poly(ptsb, 0.0, uvb)
            else:
                k.poly(ptsb, bot_zone)
    R = Matrix.Rotation(math.radians(rot), 3, 'Z')
    for i in range(nx):                                               # the edges at y0 / y1
        for j, sgn in ((0, -1), (ny, 1)):
            pts = [P(xs[i], ys[j], Zb[j][i]), P(xs[i + 1], ys[j], Zb[j][i + 1]), P(xs[i + 1], ys[j], Zb[j][i + 1] + t),
                   P(xs[i], ys[j], Zb[j][i] + t)]
            face(k, pts, edge_zone, R @ Vector((0, sgn, 0)))
    for j in range(ny):                                               # ... at x0 / x1
        for i, sgn in ((0, -1), (nx, 1)):
            pts = [P(xs[i], ys[j], Zb[j][i]), P(xs[i], ys[j + 1], Zb[j + 1][i]), P(xs[i], ys[j + 1], Zb[j + 1][i] + t),
                   P(xs[i], ys[j], Zb[j][i] + t)]
            face(k, pts, edge_zone, R @ Vector((sgn, 0, 0)))


def slab_print(k, pk, lo, hi, prints, zone, rot=0.0, centre=None):
    """a box whose faces are printed where `prints` names a panel uv ('+z', '-y', ...) and in k's zone elsewhere;
    rot turns it about z through centre"""
    lo, hi = Vector(lo), Vector(hi)
    c = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    cen = Vector(centre) if centre is not None else (lo + hi) / 2
    R = Matrix.Rotation(math.radians(rot), 3, 'Z')
    c = [cen + R @ (p - cen) for p in c]
    UVQ = {'-x': (2, 0, 1, 3), '+x': (4, 6, 7, 5), '-y': (0, 4, 5, 1), '+y': (6, 2, 3, 7), '-z': (2, 6, 4, 0), '+z': (1, 5, 7, 3)}
    for key, (q, n) in K.FACES6.items():
        pts = [c[i] for i in UVQ[key]]
        nn = R @ Vector(n)
        if key in prints:
            u0, v0, u1, v1 = prints[key]
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            f = face(pk, pts, 0.0, nn, uvs)
        else:
            face(k, pts, zone, nn)


def band(pk, c, axis, r, h0, h1, uvrect, seg=20, a0=0.0, a1=360.0, ref=None):
    """a printed band round an axis (labels on bottles and cans): u along the angle a0..a1 (deg, from ref), v along h0..h1"""
    ax = Vector(axis).normalized()
    ref = Vector(ref) if ref is not None else (Vector((0, -1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0)))
    e1 = (ref - ax * ref.dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = uvrect
    n = max(2, int(round(seg * (a1 - a0) / 360.0)))
    c = Vector(c)
    for i in range(n):
        ta, tb = math.radians(a0 + (a1 - a0) * i / n), math.radians(a0 + (a1 - a0) * (i + 1) / n)
        pa = lambda t, h: c + ax * h + (e1 * math.cos(t) + e2 * math.sin(t)) * r
        ua, ub = u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n
        pts = [pa(ta, h0), pa(tb, h0), pa(tb, h1), pa(ta, h1)]
        out = (e1 * math.cos((ta + tb) / 2) + e2 * math.sin((ta + tb) / 2))
        face(pk, pts, 0.0, out, [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])


def crumple(k, c, size, zone, seed, sub=2, amp=0.28):
    """a crumpled ball (paper, a pack): an icosphere with its vertices pushed in and out"""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=0.5)
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(9, 3))
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    for v in bm.verts:
        p = np.array(v.co)
        d = 1.0 + amp * sum(math.sin(7.0 * p.dot(dd) + 2 * i) * 0.4 for i, dd in enumerate(dirs)) / 2.5
        d *= 1.0 + 0.12 * (rng.random() - 0.5)
        v.co = Vector((p[0] * d * size[0], p[1] * d * size[1], p[2] * d * size[2]))
    lo = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co = Vector(c) + v.co - Vector((0, 0, lo))
    bm.normal_update()
    for f in bm.faces:
        k.poly([v.co.copy() for v in f.verts], zone)
    bm.free()


def cloth(k, x0, x1, y0, y1, nx, ny, hfn, t, zone, zone_b=None, outline=None, seed=0):
    """a soft sheet lying on the ground (rag, towel, clothes): a grid with heights hfn(x, y) >= 0, thickness t, both faces;
    outline(x, y) -> (dx, dy) frays the boundary"""
    zone_b = zone_b if zone_b is not None else zone
    outline = outline or (lambda x, y: (0.0, 0.0))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    G = {}
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            dx, dy = outline(x, y) if i in (0, nx) or j in (0, ny) else (0.0, 0.0)
            h = max(0.0, hfn(x, y))
            G[i, j] = (Vector((x + dx, y + dy, h + t)), Vector((x + dx, y + dy, h)))
    for j in range(ny):
        for i in range(nx):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            k.poly([G[a][0] for a in q], zone)
            k.poly([G[a][1] for a in reversed(q)], zone_b)
    for i in range(nx):
        for j, s in ((0, -1), (ny, 1)):
            a, b = (i, j), (i + 1, j)
            pts = [G[a][1], G[b][1], G[b][0], G[a][0]]
            k.poly(pts if s < 0 else list(reversed(pts)), zone)
    for j in range(ny):
        for i, s in ((0, -1), (nx, 1)):
            a, b = (i, j), (i, j + 1)
            pts = [G[a][1], G[b][1], G[b][0], G[a][0]]
            k.poly(list(reversed(pts)) if s < 0 else pts, zone)


def bumps(seed, n=6, amp=1.0, sx=0.1, sy=0.1):
    rng = np.random.default_rng(seed)
    P_ = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.3, 1.0), rng.uniform(0.4, 1.2)) for _ in range(n)]

    def f(x, y):
        return amp * sum(h * math.exp(-(((x / sx - a) / w) ** 2 + ((y / sy - b) / w) ** 2)) for a, b, h, w in P_)
    return f


def lathe(k, c, axis, prof, zone, seg=16, cap0=True, cap1=True):
    k.lathe(Vector(c), Vector(axis), prof, zone, seg, cap0=cap0, cap1=cap1)


def lathe_z(k, c, prof, zones, seg=16, cap0=True, cap1=True):
    """a lathe about +z through c with a zone per profile segment (zones[i] for ring i -> i+1); cap0 closes the first ring"""
    c = Vector(c)
    rings = []
    for h, r in prof:
        rings.append([c + Vector((math.cos(TAU * i / seg) * max(r, 1e-5), math.sin(TAU * i / seg) * max(r, 1e-5), h))
                      for i in range(seg)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        z = zones[i] if isinstance(zones, (list, tuple)) else zones
        for j in range(seg):
            j2 = (j + 1) % seg
            k.poly([a[j], a[j2], b[j2], b[j]], z)
    if cap0 and prof[0][1] > 1e-4:
        k.poly(list(reversed(rings[0])), zones[0] if isinstance(zones, (list, tuple)) else zones)
    if cap1 and prof[-1][1] > 1e-4:
        k.poly(rings[-1], zones[-1] if isinstance(zones, (list, tuple)) else zones)


def turned(k, c, axis, prof, zones, seg=16, cap0=True, cap1=True):
    """lathe about any axis with a zone per segment (rotates lathe_z's result)"""
    tmp = K.KB()
    lathe_z(tmp, (0, 0, 0), prof, zones, seg, cap0=cap0, cap1=cap1)
    ax = Vector(axis).normalized()
    R = Vector((0, 0, 1)).rotation_difference(ax).to_matrix().to_4x4()
    K.merge_kb(k, tmp, Matrix.Translation(Vector(c)) @ R)


def rbox(k, lo, hi, zone, r=0.008, ch=0.004, axis='z'):
    lo, hi = Vector(lo), Vector(hi)
    VM.rbox(k, (lo + hi) / 2, tuple(hi - lo), zone, r=r, ch=ch, axis=axis)


def quadp(pk, c, n, w, h, uvr, up=(0, 0, 1)):
    pk.quad_uv(Vector(c), Vector(n), w, h, uvr, up=Vector(up))


def handle_arc(k, a, b, h, r, zone, seg=10, side=(0, 0, 1)):
    """an arched bail / handle from a to b rising h along side"""
    a, b, s = Vector(a), Vector(b), Vector(side).normalized()
    pts = [a.lerp(b, i / seg) + s * h * math.sin(math.pi * i / seg) for i in range(seg + 1)]
    k.tube(pts, r, zone, 6)


# ================================================================ papers
def _curl(ax, ay, amt, sx, sy):
    return lambda x, y: amt * min(1.0, max(0.0, (x * ax / sx + y * ay / sy - 1.0) / 1.0)) ** 2


@item('Item_Note')
def _note(k, pk, n):
    sheet(k, pk, -0.074, 0.074, -0.105, 0.105, 0.0, 0.0012, uv('note'), bot_uv=uv('note_back'), nx=4, ny=6,
          lift=_curl(1, 1, 0.0045, 0.074, 0.105))


@item('Item_NoteForm')
def _noteform(k, pk, n):
    sheet(k, pk, -0.074, 0.074, -0.105, 0.105, 0.0, 0.0012, uv('noteform'), bot_uv=uv('note_back'), nx=4, ny=6,
          lift=_curl(-1, -1, 0.004, 0.074, 0.105))


@item('Item_StickyNote')
def _sticky(k, pk, n):
    sheet(k, pk, -0.038, 0.038, -0.038, 0.038, 0.0, 0.0008, uv('sticky'), bot_uv=sub_uv('sticky', 0.1, 0.0, 0.9, 0.1),
          nx=2, ny=2, lift=lambda x, y: 0.0015 * max(0.0, (y + 0.038) / 0.076 - 0.6) / 0.4 if y > 0 else 0.0,
          edge_zone=Z_PAINT_Y)


@item('Item_PhotoLoose')
def _photo(k, pk, n):
    sheet(k, pk, -0.068, 0.068, -0.068, 0.068, 0.0, 0.0006, uv('photo'), bot_uv=sub_uv('photo', 0.0, 0.0, 1.0, 0.05),
          nx=3, ny=3, lift=_curl(1, -1, 0.0014, 0.068, 0.068))


@item('Item_Envelope')
def _envelope(k, pk, n):
    sheet(k, pk, -0.119, 0.119, -0.076, 0.076, 0.0, 0.0012, uv('envelope'), bot_uv=uv('envelope_back'), nx=6, ny=4,
          lift=lambda x, y: 0.0028 * math.cos(x / 0.119 * math.pi / 2) * math.cos(y / 0.076 * math.pi / 2), edge_zone=Z_PAPERY)


def _folded(k, pk, x0, x1, y0, y1, h, top, bot, zone, fold_x=None):
    """a folded paper block (newspaper, magazine): the top / bottom printed, the open edges layered, a rounded fold"""
    sheet(k, pk, x0, x1, y0, y1, 0.0, h, uv(top), bot_uv=uv(bot), edge_zone=zone, nx=3, ny=4)
    if fold_x is not None:                                           # the rounded fold over the edge at fold_x
        s = -1 if fold_x < 0 else 1
        for i in range(6):
            a, b = math.pi / 2 - math.pi * i / 6, math.pi / 2 - math.pi * (i + 1) / 6
            pa = lambda t, y: Vector((fold_x + s * h / 2 * math.cos(t), y, h / 2 + h / 2 * math.sin(t)))
            pts = [pa(a, y0), pa(b, y0), pa(b, y1), pa(a, y1)]
            k.poly(pts if s > 0 else list(reversed(pts)), zone)


@item('Item_Newspaper')
def _newspaper(k, pk, n):
    _folded(k, pk, -0.148, 0.15, -0.21, 0.21, 0.010, 'news_front', 'news_back', Z_PAPERY, fold_x=-0.148)


@item('Item_NewspaperOpen')
def _news_open(k, pk, n):
    sheet(k, pk, -0.405, 0.395, -0.27, 0.27, 0.0, 0.0012, uv('news_spread'), bot_uv=uv('news_back'), edge_zone=Z_PAPERY,
          nx=12, ny=6, lift=lambda x, y: 0.0026 * (1 - math.cos(min(abs(x + 0.005) / 0.40, 1.0) * math.pi)) / 2
          + 0.0006 * math.sin(y * 9.0 + x * 3.0) + 0.0006)


@item('Item_Magazine')
def _magazine(k, pk, n):
    _folded(k, pk, -0.139, 0.142, -0.165, 0.165, 0.005, 'mag_cover', 'mag_back', Z_PAPER, fold_x=-0.139)


@item('Item_Clipboard')
def _clipboard(k, pk, n):
    box6(k, (-0.115, -0.16, 0.0), (0.115, 0.16, 0.004), {'*': Z_HARDB, '-z': Z_HARDB})
    sheet(k, pk, -0.105, 0.105, -0.152, 0.13, 0.004, 0.0006, uv('clip_form'), bot_uv=None, bot_zone=Z_PAPER, nx=3, ny=4)
    # the clip: a curved steel plate over the top edge, its pivot roll and the wire lever
    for i in range(5):
        a, b = 0.098 + 0.011 * i, 0.098 + 0.011 * (i + 1)
        za, zb = 0.0055 + 0.0012 * math.sin(i / 5 * math.pi), 0.0055 + 0.0012 * math.sin((i + 1) / 5 * math.pi)
        box6(k, (-0.05, a, za), (0.05, b, zb + 0.0012), Z_CHROME)
    k.cyl((-0.052, 0.146, 0.009), (0.052, 0.146, 0.009), 0.0045, Z_CHROME, 8)
    k.tube([Vector((-0.035, 0.150, 0.012)), Vector((-0.035, 0.144, 0.0155)), Vector((0.035, 0.144, 0.0155)),
            Vector((0.035, 0.150, 0.012))], 0.0016, Z_CHROME, 5)
    for x in (-0.045, 0.045):
        box6(k, (x - 0.006, 0.138, 0.004), (x + 0.006, 0.154, 0.006), Z_CHROME)


@item('Item_PaperStack')
def _paperstack(k, pk, n):
    rng = np.random.default_rng(7)
    z = 0.0
    for i in range(6):
        t = 0.004 if i < 5 else 0.0012
        rot = float(rng.uniform(-4.0, 4.0))
        dx, dy = float(rng.uniform(-0.006, 0.006)), float(rng.uniform(-0.004, 0.004))
        top = uv('paperstack') if i == 5 else sub_uv('paperstack', 0.0, 0.94, 1.0, 1.0)
        sheet(k, pk, -0.105 + dx, 0.105 + dx, -0.1485 + dy, 0.1485 + dy, z, t, top, bot_uv=None, bot_zone=Z_PAPER,
              edge_zone=Z_PAPERY if i % 2 else Z_PAPER, nx=2, ny=2, rot=rot, centre=(dx, dy))
        z += t


@item('Item_PaperBall')
def _paperball(k, pk, n):
    crumple(k, (-0.0015, -0.0055, 0.0), (0.066, 0.064, 0.053), Z_PAPER, 21)


@item('Item_PaperBallB')
def _paperball_b(k, pk, n):
    crumple(k, (-0.001, -0.002, 0.0), (0.071, 0.071, 0.060), Z_PAPERY, 22, amp=0.32)


@item('Item_CardboardFlat')
def _cardboard(k, pk, n):
    box6(k, (-0.275, -0.21, 0.0), (0.275, 0.21, 0.010), Z_CARD)
    quadp(pk, (0.10, -0.03, 0.0104), (0, 0, 1), 0.24, 0.184, uv('cardboard_print'), up=(0, 1, 0))
    box6(k, (-0.275, -0.025, 0.010), (0.275, 0.025, 0.0112), Z_TAPE, skip=('-z',))


@item('Item_Cards')
def _cards(k, pk, n):
    W, H = 0.057, 0.089
    box6(k, (-0.03 - W / 2, -0.04 - H / 2, 0.0), (-0.03 + W / 2, -0.04 + H / 2, 0.0145), Z_PAPER, skip=('+z',))
    quadp(pk, (-0.03, -0.04, 0.0146), (0, 0, 1), W, H, uv('card_back'), up=(0, 1, 0))
    faces = ['card_back', 'card_a', 'card_back', 'card_b', 'card_c', 'card_back', 'card_d', 'card_back']
    spots = [(0.12, 0.10, 18), (0.20, -0.02, -32), (0.075, -0.16, 70), (-0.14, 0.15, 10), (0.24, 0.17, -12),
             (-0.12, -0.17, 40), (0.17, -0.155, -60), (0.03, 0.17, 95)]
    for i, ((x, y, a), fc) in enumerate(zip(spots, faces)):
        z = 0.0006 * (i % 3)
        sheet(k, pk, x - W / 2, x + W / 2, y - H / 2, y + H / 2, z, 0.0004, uv(fc), bot_uv=uv('card_back'),
              edge_zone=Z_PAPER, nx=1, ny=1, rot=a, centre=(x, y))


def _book(k, pk, lo, hi, cloth, rot=0.0, spine_print=False):
    """a closed hardback: boards 2 mm proud of the page block, a rounded spine on -x"""
    lo, hi = Vector(lo), Vector(hi)
    c = (lo + hi) / 2
    R = Matrix.Rotation(math.radians(rot), 4, 'Z')
    tmp, tmpp = K.KB(), K.KB()
    L, Wd, T = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
    bt = 0.0025
    for z0 in (0.0, T - bt):
        box6(tmp, (-L / 2 + 0.004, -Wd / 2, z0), (L / 2, Wd / 2, z0 + bt), cloth)
    box6(tmp, (-L / 2 + 0.006, -Wd / 2 + 0.003, bt), (L / 2 - 0.003, Wd / 2 - 0.003, T - bt), Z_PAPERY, skip=('-x',))
    for i in range(6):
        a, b = math.pi / 2 + math.pi * i / 6, math.pi / 2 + math.pi * (i + 1) / 6
        pa = lambda t, y: Vector((-L / 2 + 0.006 + 0.008 * math.cos(t), y, T / 2 + T / 2 * math.sin(t)))
        tmp.poly([pa(a, Wd / 2), pa(b, Wd / 2), pa(b, -Wd / 2), pa(a, -Wd / 2)], cloth)
    if spine_print:
        quadp(tmpp, (-L / 2 - 0.0025, 0.0, T / 2), (-1, 0, 0), Wd * 0.9, T * 0.8, uv('book_spine_a'), up=(0, 0, 1))
    M = Matrix.Translation(Vector((c.x, c.y, lo.z))) @ R
    K.merge_kb(k, tmp, M)
    K.merge_kb(pk, tmpp, M)


@item('Item_Book')
def _book1(k, pk, n):
    _book(k, pk, (-0.075, -0.11, 0.0), (0.075, 0.11, 0.03), Z_CLOTH_G, spine_print=True)


@item('Item_BookStack')
def _bookstack(k, pk, n):
    _book(k, pk, (-0.104, -0.112, 0.0), (0.072, 0.128, 0.036), Z_CLOTH_R, rot=3.0)
    _book(k, pk, (-0.096, -0.105, 0.036), (0.062, 0.115, 0.067), Z_CLOTH_B, rot=-7.0)
    _book(k, pk, (-0.088, -0.095, 0.067), (0.052, 0.100, 0.094), Z_CLOTH_G, rot=6.0)


@item('Item_BookOpen')
def _book_open(k, pk, n):
    box6(k, (-0.15, -0.11, 0.0), (0.15, 0.11, 0.0025), Z_CLOTH_B)
    # two page blocks: thick at the outer edges, swelling up and diving into the gutter; the text printed on top
    nx = 10
    u0, v0, u1, v1 = uv('book_pages')
    def zt(x):
        s = abs(x) / 0.142
        return 0.0025 + 0.010 + 0.006 * math.sin(min(s, 1.0) * math.pi) * (1 - s * 0.3) - 0.009 * math.exp(-(x / 0.012) ** 2)
    xs = [-0.142 + 0.284 * i / nx for i in range(nx + 1)]
    for i in range(nx):
        xa, xb = xs[i], xs[i + 1]
        ua, ub = u0 + (u1 - u0) * i / nx, u0 + (u1 - u0) * (i + 1) / nx
        pk.poly([Vector((xa, -0.105, zt(xa))), Vector((xb, -0.105, zt(xb))), Vector((xb, 0.105, zt(xb))),
                 Vector((xa, 0.105, zt(xa)))], 0.0, [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
        for y, s in ((-0.105, -1), (0.105, 1)):
            pts = [Vector((xa, y, 0.0025)), Vector((xb, y, 0.0025)), Vector((xb, y, zt(xb))), Vector((xa, y, zt(xa)))]
            k.poly(pts if s < 0 else list(reversed(pts)), Z_PAPERY)
    for x, s in ((-0.142, -1), (0.142, 1)):
        pts = [Vector((x, -0.105, 0.0025)), Vector((x, 0.105, 0.0025)), Vector((x, 0.105, zt(x))), Vector((x, -0.105, zt(x)))]
        k.poly(list(reversed(pts)) if s < 0 else pts, Z_PAPERY)


def _binder(k, pk, cover, lab):
    """a lever-arch file lying flat: PP boards, the spine on -x with its label and finger hole, steel edge guards"""
    T = 0.07
    for z0 in (0.0, T - 0.003):
        box6(k, (-0.156, -0.145, z0), (0.166, 0.145, z0 + 0.003), cover)
    box6(k, (-0.16, -0.145, 0.0), (-0.156, 0.145, T), cover, skip=('+x',))
    quadp(pk, (-0.1604, 0.0, T / 2), (-1, 0, 0), 0.26, 0.062, uv(lab), up=(0, 0, 1))
    box6(k, (-0.152, -0.138, 0.003), (0.155, 0.138, T - 0.008), Z_PAPER, skip=('-x', '-z'))
    for z0 in (0.0, T - 0.003):
        for y0 in (-0.145, 0.133):
            box6(k, (0.154, y0, z0 - 0.0005), (0.166, y0 + 0.012, z0 + 0.0035), Z_STEEL)


@item('Item_BinderBlue')
def _binder_b(k, pk, n):
    _binder(k, pk, Z_PP_B, 'binder_b')


@item('Item_BinderRed')
def _binder_r(k, pk, n):
    _binder(k, pk, Z_PP_R, 'binder_r')


@item('Item_PhotoFrame')
def _photoframe(k, pk, n):
    """a small standing frame: dark laminate, tilted back 12 deg, the photo behind glass, a hinged leg"""
    tmp, tmpp = K.KB(), K.KB()
    W, H, T, b = 0.16, 0.135, 0.012, 0.016
    for lo, hi in (((-W / 2, 0, 0), (W / 2, T, b)), ((-W / 2, 0, H - b), (W / 2, T, H)),
                   ((-W / 2, 0, b), (-W / 2 + b, T, H - b)), ((W / 2 - b, 0, b), (W / 2, T, H - b))):
        rbox(tmp, lo, hi, Z_WOOD, r=0.003, ch=0.002, axis='y')
    box6(tmp, (-W / 2 + b, 0.006, b), (W / 2 - b, T, H - b), Z_CARDG, skip=('-y',))
    quadp(tmpp, (0, 0.0058, H / 2), (0, -1, 0), W - 2 * b + 0.002, H - 2 * b + 0.002, uv('photo_framed'))
    R = Matrix.Rotation(math.radians(-12.0), 4, 'X')
    M = Matrix.Translation((0.0, -0.010, 0.0042)) @ R
    K.merge_kb(k, tmp, M)
    K.merge_kb(pk, tmpp, M)
    top = M @ Vector((0.0, T, H * 0.62))
    k.strip([top, Vector((0.0, 0.044, 0.0015))], (1, 0, 0), 0.003, 0.03, Z_CARDG)


# ================================================================ food, drink, dishes
A14 = 360.0 / 14            # the bottles' lathe step: the labels' edges on its vertices (band 0 sits on a facet's middle)


def _bottle(k, pk, c, axis, kind):
    """glass bottles on a lathe: beer (brown, crown cap), schnapps (clear, square shoulders, screw cap), water (green)"""
    if kind == 'beer':
        prof = [(0.0, 0.029), (0.004, 0.0328), (0.150, 0.0330), (0.170, 0.030), (0.195, 0.018), (0.205, 0.0135),
                (0.236, 0.0128), (0.238, 0.0150), (0.245, 0.0150), (0.245, 0.0155), (0.253, 0.0150), (0.255, 0.0)]
        zones = [Z_GLASS_BR] * 7 + [Z_GALV] * 4
        labels = [('beer_label', 0.0333, 0.062, 0.130, -A14 * 5.5, A14 * 5.5), ('beer_neck', 0.0137, 0.208, 0.226, -A14 * 6.5, A14 * 6.5)]
    elif kind == 'schnaps':
        prof = [(0.0, 0.039), (0.005, 0.042), (0.165, 0.042), (0.185, 0.034), (0.208, 0.016), (0.215, 0.0125),
                (0.247, 0.0125), (0.248, 0.0140), (0.265, 0.0140), (0.265, 0.0)]
        zones = [Z_GLASS_CL] * 6 + [Z_PL_R] * 3
        labels = [('schnaps_label', 0.0423, 0.055, 0.135, -A14 * 1.5, A14 * 1.5)]
    else:
        prof = [(0.0, 0.029), (0.004, 0.031), (0.155, 0.031), (0.180, 0.025), (0.200, 0.0155), (0.212, 0.0140),
                (0.236, 0.0140), (0.237, 0.0152), (0.255, 0.0152), (0.255, 0.0)]
        zones = [Z_GLASS_GR] * 6 + [Z_ALU] * 3
        labels = [('water_label', 0.0313, 0.068, 0.128, -A14 * 5.5, A14 * 5.5)]
    turned(k, c, axis, prof, zones, seg=14)
    for nm, r, h0, h1, a0, a1 in labels:
        band(pk, c, axis, r, h0, h1, uv(nm), seg=14, a0=a0, a1=a1, ref=(0, -1, 0) if abs(Vector(axis).y) < 0.9 else (0, 0, 1))


@item('Item_BottleBeer')
def _beer(k, pk, n):
    _bottle(k, pk, (0.0, 0.0005, 0.0), (0, 0, 1), 'beer')


@item('Item_BottleBeerLying')
def _beer_lying(k, pk, n):
    _bottle(k, pk, (-0.12, 0.0005, 0.033), (1, 0, 0), 'beer')


@item('Item_BottleSchnapps')
def _schnaps(k, pk, n):
    _bottle(k, pk, (0.0, 0.0005, 0.0), (0, 0, 1), 'schnaps')


@item('Item_BottleWater')
def _water(k, pk, n):
    _bottle(k, pk, (0.0, 0.0, 0.0), (0, 0, 1), 'water')


def _can(k, pk, c, axis, r, h, label, open_top=False, lid_bent=None):
    """a food tin: beaded rims, the paper label round it; open_top: the lid cut off (bent up on its tab)"""
    prof = [(0.0, r - 0.003), (0.003, r), (0.006, r - 0.0006), (h - 0.006, r - 0.0006), (h - 0.003, r)]
    if open_top:
        prof += [(h, r - 0.002), (h - 0.002, r - 0.0045), (0.008, r - 0.0045), (0.008, 0.0)]
        zones = [Z_TIN] * 5 + [Z_TIN, Z_TIN, Z_TIN]
    else:
        prof += [(h, r - 0.003), (h - 0.002, r - 0.005), (h - 0.002, 0.0)]
        zones = [Z_TIN] * 7
    turned(k, c, axis, prof, zones, seg=16)
    band(pk, c, axis, r + 0.0003, 0.010, h - 0.010, uv(label), seg=16, ref=(0, -1, 0) if abs(Vector(axis).y) < 0.9 else (0, 0, 1))
    if lid_bent is not None:                                          # the lid on its tab, bent up / out
        ax = Vector(axis).normalized()
        cc = Vector(c) + ax * h
        hinge_dir, ang = lid_bent
        hd = Vector(hinge_dir).normalized()
        piv = cc + hd * (r - 0.004)
        tmp = K.KB()
        lathe_z(tmp, (0, 0, 0), [(0.0, r - 0.004), (0.0012, r - 0.004)], [Z_TIN], seg=16)
        R0 = Vector((0, 0, 1)).rotation_difference(ax).to_matrix().to_4x4()
        Rb = Matrix.Rotation(math.radians(ang), 4, hd.cross(ax).normalized())
        K.merge_kb(k, tmp, Matrix.Translation(piv) @ Rb @ Matrix.Translation(-piv) @ Matrix.Translation(cc) @ R0)


@item('Item_CanRed')
def _can_red(k, pk, n):
    _can(k, pk, (0.0, 0.0, 0.0), (0, 0, 1), 0.031, 0.117, 'can_red')


@item('Item_CanGreen')
def _can_green(k, pk, n):
    _can(k, pk, (0.0, 0.0, 0.0), (0, 0, 1), 0.031, 0.117, 'can_green')


@item('Item_TinOpen')
def _tin_open(k, pk, n):
    _can(k, pk, (0.0, 0.0, 0.0), (0, 0, 1), 0.040, 0.082, 'tin_band', open_top=True)
    k.lathe(Vector((0.036, -0.034, 0.094)), Vector((0, 1, 0)), [(0.0, 0.0115), (0.068, 0.0115)], Z_TIN, 10)   # the lid rolled up
    lathe_z(k, (0.0, 0.0, 0.040), [(0.0, 0.0355), (0.006, 0.030), (0.010, 0.016), (0.011, 0.0)], [Z_FOOD] * 3, seg=12, cap0=False)


@item('Item_TinLying')
def _tin_lying(k, pk, n):
    _can(k, pk, (-0.037, 0.0, 0.042), (1, 0, 0), 0.042, 0.096, 'tin_band', open_top=True, lid_bent=((0, 0, 1), -14.0))


@item('Item_CanCrushed')
def _can_crushed(k, pk, n):
    """a drinks can stepped on: an accordion of folds, squashed flat on one side"""
    prof = [(0.0, 0.024), (0.004, 0.026)]
    for i in range(7):
        prof.append((0.006 + i * 0.0062, 0.033 if i % 2 else 0.027))
    prof += [(0.050, 0.024), (0.052, 0.0)]
    tmp = K.KB()
    lathe_z(tmp, (0, 0, 0), prof, [Z_ALU] * (len(prof) - 1), seg=14)
    rng = np.random.default_rng(31)
    for v in tmp.bm.verts:                                            # stepped on: squashed oval, the folds uneven
        v.co.x *= 1.1
        v.co.y *= 0.72
        v.co += Vector((rng.normal() * 0.0007, rng.normal() * 0.0007, rng.normal() * 0.0005))
        v.co.z = max(0.0, v.co.z)
    K.merge_kb(k, tmp, Matrix.Translation((0.0, -0.0245, 0.0)))


@item('Item_Jar')
def _jar(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.040), (0.004, 0.043), (0.112, 0.043), (0.122, 0.036), (0.128, 0.036)],
            [Z_GLASS_CL] * 4, seg=16)
    lathe_z(k, (0, 0, 0.127), [(0.0, 0.0385), (0.016, 0.0385), (0.018, 0.034), (0.018, 0.0)], [Z_PAINT_R] * 3, seg=16)
    band(pk, (0, 0, 0), (0, 0, 1), 0.0433, 0.040, 0.075, uv('jar_label'), seg=16, a0=-45, a1=45)   # on the lathe's facets


@item('Item_BreadMouldy')
def _bread(k, pk, n):
    """half a loaf: a domed crust, the cut end at +x showing the crumb, mould in patches (painter)"""
    rings = []
    xs = [-0.12, -0.115, -0.10, -0.07, -0.03, 0.02, 0.07, 0.11, 0.12]
    for x in xs:
        s = min(1.0, (x + 0.12) / 0.03) ** 0.5 if x < -0.09 else 1.0
        ring = []
        for i in range(14):
            a = TAU * i / 14
            ca, sa = math.cos(a), math.sin(a)
            yy = 0.0625 * s * (abs(ca) ** 0.6) * (1 if ca >= 0 else -1) - 0.0075
            zz = 0.0455 + 0.0455 * s * (abs(sa) ** 0.7) * (1 if sa >= 0 else -1) * (0.98 if sa < 0 else 1.0)
            ring.append(Vector((x, yy, max(zz, 0.0))))
        rings.append(ring)
    k.loft(rings, [Z_BREAD] * (len(rings) - 1), cap0=Z_BREAD, cap1=Z_CRUMB)


@item('Item_Kettle')
def _kettle(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.082), (0.004, 0.092), (0.075, 0.090), (0.118, 0.072), (0.140, 0.050), (0.146, 0.046),
                           (0.146, 0.040)], [Z_ALU] * 6, seg=16)
    lathe_z(k, (0, 0, 0.146), [(0.0, 0.042), (0.008, 0.040), (0.014, 0.012), (0.016, 0.012), (0.030, 0.011),
                               (0.032, 0.0)], [Z_ALU, Z_ALU, Z_PL_BK, Z_PL_BK, Z_PL_BK], seg=12)
    k.tube([Vector((0.060, 0.0, 0.062)), Vector((0.098, 0.0, 0.080)), Vector((0.126, 0.0, 0.112)), Vector((0.150, 0.0, 0.146))],
           0.0105, Z_ALU, 8)
    k.lathe(Vector((0.150, 0.0, 0.146)), Vector((0.62, 0.0, 0.78)), [(0.0, 0.0095), (0.006, 0.0085)], Z_ALU, 8, cap0=False, cap1=True)
    for s in (-1, 1):
        k.tube([Vector((s * 0.050, 0.0, 0.128)), Vector((s * 0.050, 0.0, 0.150))], 0.0035, Z_STEEL, 5)
    handle_arc(k, (-0.050, 0.0, 0.150), (0.050, 0.0, 0.150), 0.050, 0.008, Z_PL_BK, seg=10)


def _mug(k, c, axis, outer, rim, inner, roll=0.0):
    """an enamel mug: the body (outer zone), the dark rim, white inside, a handle"""
    tmp = K.KB()
    lathe_z(tmp, (0, 0, 0), [(0.0, 0.037), (0.003, 0.041), (0.092, 0.041), (0.095, 0.0405), (0.095, 0.0375),
                             (0.092, 0.0375), (0.006, 0.0375), (0.006, 0.0)],
            [outer, outer, rim, rim, rim, inner, inner], seg=16)
    tmp.tube([Vector((0.040, 0.0, 0.074)), Vector((0.062, 0.0, 0.074)), Vector((0.065, 0.0, 0.060)), Vector((0.065, 0.0, 0.036)),
              Vector((0.060, 0.0, 0.022)), Vector((0.040, 0.0, 0.022))], 0.0045, outer, 6)
    ax = Vector(axis).normalized()
    R = Vector((0, 0, 1)).rotation_difference(ax).to_matrix().to_4x4()
    K.merge_kb(k, tmp, Matrix.Translation(Vector(c)) @ R @ Matrix.Rotation(math.radians(roll), 4, 'Z'))


@item('Item_MugGreen')
def _mug_green(k, pk, n):
    _mug(k, (0, 0, 0), (0, 0, 1), Z_ENG, Z_ENBK, Z_ENW)


@item('Item_MugWhite')
def _mug_white(k, pk, n):
    _mug(k, (0, 0, 0), (0, 0, 1), Z_ENW, Z_ENBL, Z_ENW)


@item('Item_MugTipped')
def _mug_tipped(k, pk, n):
    _mug(k, (-0.047, 0.0, 0.041), (1, 0, 0), Z_ENG, Z_ENBK, Z_ENW, roll=180.0)


def _plate(k, dirty=False):
    lathe_z(k, (0, 0, 0), [(0.0, 0.066), (0.004, 0.070), (0.004, 0.082), (0.012, 0.100), (0.018, 0.118), (0.020, 0.1235),
                           (0.0185, 0.1235), (0.016, 0.116), (0.009, 0.098), (0.007, 0.082), (0.007, 0.0)],
            [Z_ENW, Z_ENW, Z_ENW, Z_ENW, Z_ENBL, Z_ENBL, Z_ENBL, Z_ENW, Z_ENW, Z_ENW], seg=20)


@item('Item_Plate')
def _plate1(k, pk, n):
    _plate(k)


@item('Item_PlateDirty')
def _plate_dirty(k, pk, n):
    _plate(k, True)
    lathe_z(k, (0.012, -0.01, 0.0072), [(0.0, 0.050), (0.0025, 0.040), (0.004, 0.020), (0.0045, 0.0)], [Z_FOOD] * 3, seg=10, cap0=False)
    # a fork across the plate: tines in the well, the shank up over the rim
    pts = [Vector((-0.085, -0.040, 0.0082)), Vector((-0.02, -0.014, 0.0082)), Vector((0.06, 0.018, 0.0125)),
           Vector((0.110, 0.038, 0.0210))]
    k.strip(pts, (0, 0, 1), 0.012, 0.0022, Z_STEEL)
    for dy in (-0.0045, -0.0015, 0.0015, 0.0045):
        d = (pts[1] - pts[0]).normalized()
        sdir = d.cross(Vector((0, 0, 1))).normalized()
        a = pts[0] + sdir * dy
        k.strip([a - d * 0.035, a], (0, 0, 1), 0.0016, 0.0016, Z_STEEL)


@item('Item_Pot')
def _pot(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.105), (0.005, 0.110), (0.135, 0.110), (0.140, 0.112), (0.140, 0.1065), (0.012, 0.1065),
                           (0.012, 0.0)], [Z_ALU] * 6, seg=18)
    lathe_z(k, (0, 0, 0.137), [(0.0, 0.113), (0.004, 0.110), (0.012, 0.090), (0.016, 0.020), (0.016, 0.014), (0.022, 0.016),
                               (0.028, 0.016), (0.028, 0.0)], [Z_ALU, Z_ALU, Z_ALU, Z_PL_BK, Z_PL_BK, Z_PL_BK, Z_PL_BK], seg=18)
    for s in (-1, 1):
        box6(k, (s * 0.108 if s > 0 else -0.140, -0.035, 0.110), (0.140 if s > 0 else -0.108, 0.035, 0.124), Z_PL_BK)


@item('Item_Pan')
def _pan(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.100), (0.004, 0.106), (0.040, 0.122), (0.045, 0.1255), (0.044, 0.1215), (0.010, 0.1035),
                           (0.007, 0.098), (0.007, 0.0)], [Z_STEELB] * 7, seg=20)
    k.strip([Vector((0.110, 0.0, 0.036)), Vector((0.150, 0.0, 0.046)), Vector((0.190, 0.0, 0.052))], (0, 0, 1), 0.020, 0.004, Z_STEELB)
    rbox(k, (0.185, -0.013, 0.044), (0.330, 0.013, 0.060), Z_PL_BK, r=0.006, ch=0.003, axis='x')


@item('Item_Thermos')
def _thermos(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.039), (0.004, 0.043), (0.226, 0.043), (0.240, 0.038), (0.246, 0.026)],
            [Z_GALV, Z_PAINT_G, Z_PAINT_G, Z_GALV], seg=16)
    lathe_z(k, (0, 0, 0.244), [(0.0, 0.039), (0.002, 0.041), (0.070, 0.041), (0.074, 0.038), (0.076, 0.0)], [Z_ALU] * 4, seg=16)
    band(pk, (0, 0, 0), (0, 0, 1), 0.0433, 0.030, 0.056, uv('thermos_band'), seg=16)


@item('Item_Ashtray')
def _ashtray(k, pk, n):
    tmp = K.KB()
    lathe_z(tmp, (0, 0, 0), [(0.0, 0.068), (0.004, 0.075), (0.028, 0.075), (0.030, 0.072), (0.030, 0.058), (0.026, 0.054),
                             (0.012, 0.050), (0.012, 0.0)], [Z_GLASS_ASH] * 7, seg=24)
    for v in tmp.bm.verts:                                                     # three rests cut in the rim
        a = math.atan2(v.co.y, v.co.x)
        for ac in (0.0, TAU / 3, 2 * TAU / 3):
            d = abs((a - ac + math.pi) % TAU - math.pi)
            if d < 0.20 and v.co.z > 0.024:
                v.co.z -= 0.009 * (1 - d / 0.20)
    K.merge_kb(k, tmp)
    lathe_z(k, (0.008, -0.006, 0.0122), [(0.0, 0.035), (0.002, 0.020), (0.0026, 0.0)], [Z_ASH] * 2, seg=12, cap0=False)
    for (x, y, a) in ((0.020, 0.010, 30.0), (-0.015, -0.012, 160.0)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0))
        p = Vector((x, y, 0.0172))
        k.cyl(p - d * 0.012, p + d * 0.004, 0.0039, Z_FILTER, 7)
        k.cyl(p + d * 0.004, p + d * 0.014, 0.0039, Z_CIG, 7)


@item('Item_Butts')
def _butts(k, pk, n):
    for (x, y, a, L, flat) in ((0.0, 0.0, 20.0, 0.028, 1.0), (0.036, 0.012, -60.0, 0.022, 0.6), (-0.026, -0.030, 110.0, 0.030, 1.0),
                               (0.030, -0.034, 170.0, 0.020, 0.5)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0))
        p = Vector((x, y, 0.0039 * flat))
        tmp = K.KB()
        tmp.cyl(p - d * L / 2, p - d * L / 2 + d * 0.016, 0.0039, Z_FILTER, 7)
        tmp.cyl(p - d * L / 2 + d * 0.016, p + d * L / 2 - d * 0.002, 0.0039, Z_CIG, 7)
        tmp.cyl(p + d * L / 2 - d * 0.002, p + d * L / 2, 0.0037, Z_ASH, 7)
        for v in tmp.bm.verts:
            v.co.z = max(0.0, p.z + (v.co.z - p.z) * flat)
        K.merge_kb(k, tmp)
    k.poly([Vector((0.040, -0.050, 0.0004)), Vector((0.058, -0.044, 0.0004)), Vector((0.050, -0.030, 0.0004))], Z_ASH)


@item('Item_CigPack')
def _cigpack(k, pk, n):
    slab_print(k, pk, (-0.027, -0.011, 0.0), (0.027, 0.011, 0.088),
               {'-y': uv('cig_front'), '+y': uv('cig_back'), '-x': uv('cig_side'), '+x': uv('cig_side'), '+z': uv('cig_top')},
               Z_PAPER)


@item('Item_CigPackCrushed')
def _cigpack_c(k, pk, n):
    tmp, tmpp = K.KB(), K.KB()
    slab_print(tmp, tmpp, (-0.033, -0.024, 0.0), (0.033, 0.024, 0.016),
               {'+z': uv('cig_front'), '-z': uv('cig_back')}, Z_PAPER)
    for kk in (tmp, tmpp):
        bmesh.ops.subdivide_edges(kk.bm, edges=list(kk.bm.edges), cuts=2, use_grid_fill=True)
    rng = np.random.default_rng(41)
    for kk in (tmp, tmpp):
        for v in kk.bm.verts:
            v.co.z = max(0.0, v.co.z + 0.003 * math.sin(v.co.x * 120 + v.co.y * 60) + rng.normal() * 0.0008)
            v.co.x += 0.002 * math.sin(v.co.y * 90)
    K.merge_kb(k, tmp)
    K.merge_kb(pk, tmpp)


@item('Item_TrashBag')
def _trashbag(k, pk, n):
    """a full bag: a lumpy body, the gathered neck twisted and tied, two ears"""
    rings = []
    zs = [0.0, 0.02, 0.08, 0.18, 0.30, 0.40, 0.46, 0.50, 0.52]
    rs = [0.095, 0.152, 0.185, 0.188, 0.18, 0.143, 0.076, 0.035, 0.025]
    rng = np.random.default_rng(51)
    for z, r in zip(zs, rs):
        ring = []
        for i in range(16):
            a = TAU * i / 16
            w = 1.0 + 0.06 * math.sin(3 * a + z * 9) + 0.04 * rng.normal()
            ring.append(Vector((-0.02 + r * w * math.cos(a), r * w * math.sin(a), z)))
        rings.append(ring)
    k.loft(rings, [Z_BAG] * (len(rings) - 1), cap0=Z_BAG, cap1=None)
    k.lathe(Vector((-0.02, 0.0, 0.52)), Vector((0.05, 0.0, 1.0)), [(0.0, 0.025), (0.03, 0.016), (0.05, 0.022), (0.06, 0.0)],
            Z_BAG, 8, cap0=False)
    for s in (-1, 1):
        k.poly([Vector((-0.02, 0.0, 0.56)), Vector((-0.02 + s * 0.09, 0.02, 0.60)), Vector((-0.02 + s * 0.11, -0.015, 0.575)),
                Vector((-0.02 + s * 0.03, -0.01, 0.55))], Z_BAG)
        k.poly([Vector((-0.02 + s * 0.03, -0.01, 0.55)), Vector((-0.02 + s * 0.11, -0.015, 0.575)), Vector((-0.02 + s * 0.09, 0.02, 0.60)),
                Vector((-0.02, 0.0, 0.56))], Z_BAG)


# ================================================================ home, clothes
@item('Item_Broom')
def _broom(k, pk, n):
    rbox(k, (-0.15, -0.022, 0.055), (0.15, 0.022, 0.095), Z_WOOD, r=0.006, ch=0.004, axis='x')
    for i in range(13):                                               # bristle tufts in two rows, splayed
        for row in (-1, 1):
            x = -0.14 + i * 0.0233
            k.box_m((x + row * 0.002, row * 0.010, 0.031), (0.016, 0.014, 0.058), Z_STRAW,
                    Matrix.Rotation(math.radians(x * 30 * row), 3, 'Y'))
    k.cyl((0.0, 0.0, 0.094), (0.0, 0.0, 1.40), 0.0125, Z_WOOD, 8, r2=0.0115)
    k.cyl((0.0, 0.0, 0.094), (0.0, 0.0, 0.13), 0.016, Z_STEEL, 8)


def _bucket(k, body, rim_zone, inside):
    lathe_z(k, (0, 0, 0), [(0.0, 0.112), (0.004, 0.116), (0.285, 0.148), (0.290, 0.152), (0.293, 0.149), (0.288, 0.145),
                           (0.012, 0.112), (0.012, 0.0)], [body, body, rim_zone, rim_zone, rim_zone, inside, inside], seg=18)
    for s in (-1, 1):
        box6(k, (s * 0.142 - 0.012, -0.012, 0.250), (s * 0.142 + 0.012, 0.012, 0.275), body)
    pts = [Vector((-0.150 + 0.300 * i / 12, 0.0, 0.262 + 0.105 * math.sin(math.pi * i / 12))) for i in range(13)]
    k.tube(pts, 0.0028, Z_STEEL, 5)
    k.cyl((-0.045, 0.0, 0.367), (0.045, 0.0, 0.367), 0.0105, Z_WOOD, 8)


@item('Item_Bucket')
def _bucket1(k, pk, n):
    _bucket(k, Z_GALV, Z_GALV, Z_GALV)


@item('Item_BucketWater')
def _bucket2(k, pk, n):
    _bucket(k, Z_ENBL, Z_ENBK, Z_ENBL_IN)
    w = kb('Item_BucketWater_Water', 'water')
    lathe_z(w, (0, 0, 0.215), [(0.0, 0.1365), (0.0, 0.0)], [Z_ENBL_IN], seg=18, cap0=False)
    SPECIAL.setdefault('Item_BucketWater', {})['water'] = ['Item_BucketWater_Water']


@item('Item_Dustpan')
def _dustpan(k, pk, n):
    box6(k, (-0.12, -0.11, 0.0), (0.12, 0.095, 0.0025), Z_PAINT_R)                    # the pan
    for s in (-1, 1):                                                                # side walls rising to the back
        k.poly([Vector((s * 0.12, -0.11, 0.0025)), Vector((s * 0.12, 0.095, 0.0025)), Vector((s * 0.12, 0.095, 0.105)),
                Vector((s * 0.12, -0.02, 0.012))], Z_PAINT_R)
        k.poly([Vector((s * 0.1225, -0.02, 0.012)), Vector((s * 0.1225, 0.095, 0.105)), Vector((s * 0.1225, 0.095, 0.0025)),
                Vector((s * 0.1225, -0.11, 0.0025))], Z_PAINT_R)
    box6(k, (-0.12, 0.095, 0.0), (0.12, 0.098, 0.108), Z_PAINT_R)
    k.cyl((0.0, 0.098, 0.088), (0.0, 0.243, 0.098), 0.012, Z_PL_BK, 8)


@item('Item_Mop')
def _mop(k, pk, n):
    rng = np.random.default_rng(61)
    for i in range(36):                                               # cotton strands flopped out on the floor
        a = TAU * i / 36 + rng.uniform(-0.05, 0.05)
        L = rng.uniform(0.09, 0.125)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        pts = [Vector((0, 0, 0.075)) + d * 0.012, Vector((0, 0, 0.040)) + d * 0.04, Vector((0, 0, 0.011)) + d * (L * 0.75),
               Vector((0, 0, 0.0065)) + d * L]
        k.tube(pts, 0.0055, Z_MOPS, 4)
    k.cyl((0.0, 0.0, 0.060), (0.0, 0.0, 0.120), 0.022, Z_PL_R, 8)
    k.cyl((0.0, 0.0, 0.120), (0.0, 0.0, 1.355), 0.0125, Z_WOOD, 8, r2=0.0115)


@item('Item_Rag')
def _rag(k, pk, n):
    h = bumps(71, n=7, amp=0.014, sx=0.2, sy=0.2)
    cloth(k, -0.25, 0.15, -0.145, 0.23, 10, 9, lambda x, y: h(x, y) * 0.8 + 0.002, 0.0025, Z_FAB_G,
          outline=lambda x, y: (0.012 * math.sin(y * 31), 0.012 * math.sin(x * 27)))


@item('Item_Soap')
def _soap(k, pk, n):
    rbox(k, (-0.04, -0.025, 0.0), (0.04, 0.025, 0.024), Z_SOAP, r=0.014, ch=0.006, axis='z')


@item('Item_ToiletRolls')
def _rolls(k, pk, n):
    for x in (0.0, 0.115, 0.230):
        lathe_z(k, (x, 0.0, 0.0), [(0.0, 0.0215), (0.0, 0.052), (0.100, 0.052), (0.100, 0.0215), (0.0, 0.0215)],
                [Z_TISSUE, Z_TISSUE, Z_TISSUE, Z_CARD], seg=14, cap0=False)


@item('Item_ToothCup')
def _toothcup(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.030), (0.003, 0.032), (0.100, 0.035), (0.100, 0.0325), (0.006, 0.0295), (0.006, 0.0)],
            [Z_PL_BL] * 5, seg=14)
    for (d, z_top, zone) in (((0.024, 0.018), 0.183, Z_PL_R), ((-0.026, -0.012), 0.176, Z_PL_GR)):
        base = Vector((d[0] * 0.35, d[1] * 0.35, 0.012))
        top = Vector((d[0], d[1], z_top - 0.012 - 0.005))
        k.cyl(base, top, 0.0045, zone, 6)
        dirv = (top - base).normalized()
        k.box_m(top + dirv * 0.008 + Vector((0, 0, 0.0)), (0.009, 0.009, 0.018), Z_PL_W,
                VM.frame_R(dirv.cross(Vector((0, 0, 1))).normalized(), dirv))


@item('Item_Towel')
def _towel(k, pk, n):
    for i, (z0, inset) in enumerate(((0.0, 0.0), (0.02, 0.004), (0.04, 0.008))):
        rbox(k, (-0.152 + inset, -0.105 + inset * 0.5, z0), (0.152 - inset * 0.5, 0.105, z0 + 0.0205), Z_TERRY, r=0.010,
             ch=0.006, axis='y')


@item('Item_Rug')
def _rug(k, pk, n):
    box6(k, (-0.86, -0.45, 0.0), (0.86, 0.45, 0.006), Z_RUG)
    for s in (-1, 1):
        for i in range(30):
            y = -0.435 + i * 0.03
            k.box_m((s * 0.88, y, 0.0015), (0.040, 0.008, 0.003), Z_PL_W,
                    Matrix.Rotation(math.radians(6 * math.sin(i * 1.7)), 3, 'Z'))


@item('Item_Clothes')
def _clothes(k, pk, n):
    hj = bumps(81, n=8, amp=0.05, sx=0.35, sy=0.25)
    cloth(k, -0.395, 0.16, -0.325, 0.19, 10, 9, lambda x, y: hj(x + 0.1, y) + 0.01, 0.006, Z_FAB_O,
          outline=lambda x, y: (0.02 * math.sin(y * 13), 0.025 * math.sin(x * 11)))
    ht = bumps(82, n=6, amp=0.04, sx=0.3, sy=0.2)
    cloth(k, -0.05, 0.36, -0.26, 0.20, 9, 8, lambda x, y: 0.045 + ht(x - 0.15, y) * 0.8, 0.008, Z_FAB_B,
          outline=lambda x, y: (0.015 * math.sin(y * 17), 0.02 * math.sin(x * 19)))
    hs = bumps(83, n=5, amp=0.03, sx=0.2, sy=0.15)
    cloth(k, -0.30, 0.02, -0.10, 0.18, 7, 6, lambda x, y: 0.085 + hs(x + 0.15, y - 0.05), 0.008, Z_FAB_G,
          outline=lambda x, y: (0.01 * math.sin(y * 23), 0.01 * math.sin(x * 21)))
    lo = min(v.co.z for v in k.bm.verts)
    for v in k.bm.verts:
        v.co.z -= lo


def _boot(k, y0, rot):
    """a high lace-up work boot: rubber sole and heel, black leather foot and shaft, a toe cap"""
    tmp = K.KB()
    rbox(tmp, (-0.055, -0.048, 0.0), (0.195, 0.048, 0.022), Z_RUBBER, r=0.03, ch=0.006, axis='z')
    rings = []
    for x, w, h in ((-0.052, 0.040, 0.13), (-0.03, 0.044, 0.14), (0.02, 0.045, 0.12), (0.08, 0.045, 0.085), (0.13, 0.043, 0.07),
                    (0.17, 0.036, 0.06), (0.19, 0.022, 0.045)):
        rings.append([Vector((x, w * math.cos(a), 0.022 + (h * 0.5) * (1 + math.sin(a)) * (0.9 if math.sin(a) < 0 else 1.0)))
                      for a in [TAU * i / 12 for i in range(12)]])
    tmp.loft(rings, [Z_LEATHER] * (len(rings) - 1), cap0=Z_LEATHER, cap1=Z_LEATHER)
    tmp.lathe(Vector((0.0, 0.0, 0.12)), Vector((0.08, 0.0, 1.0)), [(0.0, 0.046), (0.07, 0.044), (0.135, 0.046), (0.14, 0.040)],
              Z_LEATHER, 12, cap0=False, cap1=False)
    tmp.lathe(Vector((0.0, 0.0, 0.12)), Vector((0.08, 0.0, 1.0)), [(0.14, 0.040), (0.13, 0.040), (0.0, 0.0)], Z_FAB_G, 12,
              cap0=False, cap1=False)
    K.merge_kb(k, tmp, Matrix.Translation((0.0, y0, 0.0)) @ Matrix.Rotation(math.radians(rot), 4, 'Z'))


@item('Item_Boots')
def _boots(k, pk, n):
    _boot(k, -0.075, 3.0)
    _boot(k, 0.072, -4.0)


@item('Item_Backpack')
def _backpack(k, pk, n):
    rbox(k, (-0.15, -0.105, 0.0), (0.15, 0.115, 0.43), Z_FAB_O, r=0.05, ch=0.02, axis='z')
    rbox(k, (-0.155, -0.135, 0.33), (0.155, 0.12, 0.40), Z_FAB_O, r=0.03, ch=0.012, axis='x')            # the lid
    rbox(k, (-0.11, -0.148, 0.05), (0.11, -0.10, 0.25), Z_FAB_O, r=0.02, ch=0.008, axis='y')             # front pocket
    for x in (-0.07, 0.07):                                                                          # buckle straps
        box6(k, (x - 0.014, -0.140, 0.26), (x + 0.014, -0.128, 0.40), Z_FAB_G)
        box6(k, (x - 0.016, -0.150, 0.25), (x + 0.016, -0.138, 0.28), Z_PL_BK)
    for x in (-0.08, 0.08):                                                                          # shoulder straps
        k.strip([Vector((x, 0.118, 0.40)), Vector((x * 1.1, 0.152, 0.30)), Vector((x * 1.2, 0.150, 0.15)),
                 Vector((x * 1.3, 0.125, 0.04))], (0, 1, 0), 0.055, 0.012, Z_FAB_G)
    k.tube([Vector((-0.03, 0.10, 0.43)), Vector((0.0, 0.11, 0.49)), Vector((0.03, 0.10, 0.43))], 0.008, Z_FAB_G, 5)


@item('Item_Headphones')
def _headphones(k, pk, n):
    for s in (-1, 1):
        k.lathe(Vector((s * 0.118, 0.0, 0.040)), Vector((-s, 0.0, 0.0)),
                [(0.0, 0.028), (0.006, 0.040), (0.026, 0.040), (0.030, 0.034)], Z_PL_BK, 12, cap0=True, cap1=False)
        k.lathe(Vector((s * (0.118 - 0.030), 0.0, 0.040)), Vector((-s, 0.0, 0.0)),
                [(0.0, 0.036), (0.012, 0.034), (0.016, 0.020), (0.016, 0.0)], Z_FOAM, 12, cap0=False)
        k.strip([Vector((s * 0.105, 0.0, 0.070)), Vector((s * 0.100, 0.0, 0.086))], (0, 1, 0), 0.010, 0.006, Z_STEEL)
    pts = [Vector((0.100 * math.cos(math.pi * i / 12), 0.0, 0.086 + 0.020 * math.sin(math.pi * i / 12))) for i in range(13)]
    k.strip(pts, (0, 1, 0), 0.006, 0.030, Z_PL_BK)


@item('Item_Medicine')
def _medicine(k, pk, n):
    slab_print(k, pk, (-0.045, -0.02, 0.0), (0.045, 0.02, 0.04),
               {'-y': uv('med_front'), '+y': uv('med_front'), '+z': uv('med_front'), '-x': uv('med_end'), '+x': uv('med_end')},
               Z_PAPER)


@item('Item_Radio')
def _radio(k, pk, n):
    rbox(k, (-0.14, -0.045, 0.0), (0.14, 0.045, 0.165), Z_PL_BE, r=0.018, ch=0.006, axis='y')
    box6(k, (-0.128, -0.0465, 0.012), (0.010, -0.044, 0.120), Z_GREYM, skip=('+y',))                  # speaker grille
    quadp(pk, (0.068, -0.0466, 0.120), (0, -1, 0), 0.115, 0.036, uv('radio_dial'))
    for x in (0.040, 0.095):
        k.cyl((x, -0.046, 0.055), (x, -0.060, 0.055), 0.013, Z_PL_BK, 10)
    k.strip([Vector((-0.12, 0.0, 0.160)), Vector((-0.11, 0.0, 0.205)), Vector((0.11, 0.0, 0.205)), Vector((0.12, 0.0, 0.160))],
            (0, 1, 0), 0.008, 0.028, Z_PL_BK)
    k.cyl((0.118, 0.030, 0.150), (0.135, 0.032, 0.551), 0.0032, Z_CHROME, 6)
    k.cyl((0.118, 0.030, 0.150), (0.122, 0.031, 0.25), 0.0045, Z_CHROME, 6)


# ================================================================ tools, boxes
@item('Item_CableReel')
def _cablereel(k, pk, n):
    for s in (-1, 1):
        k.lathe(Vector((0.0, s * 0.105, 0.185)), Vector((0, s, 0)), [(0.0, 0.150), (0.010, 0.150)], Z_PAINT_R, 18)
    k.lathe(Vector((0.0, -0.095, 0.185)), Vector((0, 1, 0)), [(0.0, 0.118), (0.19, 0.118)], Z_CABLE_O, 18, cap0=False, cap1=False)
    for s in (-1, 1):                                                         # the frame: two hoops, the handle, feet
        k.tube([Vector((-0.17, s * 0.125, 0.0)), Vector((-0.17, s * 0.125, 0.30)), Vector((-0.10, s * 0.125, 0.355)),
                Vector((0.10, s * 0.125, 0.355)), Vector((0.17, s * 0.125, 0.30)), Vector((0.17, s * 0.125, 0.0))],
               0.011, Z_STEELB, 6)
    k.cyl((0.0, -0.135, 0.355), (0.0, 0.135, 0.355), 0.017, Z_PL_BK, 8)
    for x in (-0.17, 0.17):
        k.cyl((x, -0.135, 0.008), (x, 0.135, 0.008), 0.010, Z_STEELB, 6)
    k.cyl((0.0, -0.135, 0.185), (0.0, 0.135, 0.185), 0.010, Z_STEELB, 6)
    for x in (-0.05, 0.05):                                                   # two sockets on the front flange
        k.box_m((x, -0.122, 0.205), (0.05, 0.022, 0.05), Z_PL_BK)
    k.tube([Vector((0.10, -0.06, 0.07)), Vector((0.16, -0.03, 0.04)), Vector((0.18, 0.02, 0.012))], 0.006, Z_CABLE_O, 6)


@item('Item_Hammer')
def _hammer(k, pk, n):
    rings = []
    for x, w, h in ((-0.14, 0.013, 0.010), (-0.10, 0.016, 0.012), (0.00, 0.014, 0.011), (0.09, 0.012, 0.010), (0.125, 0.012, 0.011)):
        rings.append([Vector((x, w * math.cos(a), 0.018 + h * math.sin(a))) for a in [TAU * i / 10 for i in range(10)]])
    k.loft(rings, [Z_WOOD] * 4, cap0=Z_WOOD, cap1=Z_WOOD)
    rbox(k, (0.118, -0.050, 0.004), (0.150, 0.042, 0.032), Z_STEEL, r=0.003, ch=0.002, axis='y')
    k.cyl((0.134, 0.042, 0.018), (0.134, 0.055, 0.018), 0.012, Z_STEEL, 8)
    k.box_m((0.134, -0.053, 0.018), (0.024, 0.008, 0.022), Z_STEEL)


@item('Item_OilCan')
def _oilcan(k, pk, n):
    rbox(k, (-0.10, -0.05, 0.0), (0.10, 0.05, 0.25), Z_PAINT_B, r=0.012, ch=0.004, axis='z')
    quadp(pk, (0.0, -0.0505, 0.13), (0, -1, 0), 0.17, 0.134, uv('oil_label'))
    k.strip([Vector((-0.08, 0.0, 0.245)), Vector((-0.06, 0.0, 0.286)), Vector((0.02, 0.0, 0.286)), Vector((0.04, 0.0, 0.245))],
            (0, 1, 0), 0.022, 0.012, Z_PAINT_B)
    lathe_z(k, (0.068, 0.0, 0.25), [(0.0, 0.017), (0.012, 0.017), (0.014, 0.020), (0.030, 0.020), (0.032, 0.0)],
            [Z_PAINT_B, Z_PAINT_Y, Z_PAINT_Y, Z_PAINT_Y], seg=12)


@item('Item_PaintCan')
def _paintcan(k, pk, n):
    lathe_z(k, (0, 0, 0), [(0.0, 0.082), (0.004, 0.085), (0.196, 0.085), (0.200, 0.083), (0.203, 0.078), (0.203, 0.0)],
            [Z_TIN] * 5, seg=18)
    band(pk, (0, 0, 0), (0, 0, 1), 0.0853, 0.020, 0.175, uv('paint_label'), seg=18, ref=(1, 0, 0))   # on the lathe's facets
    for s in (-1, 1):
        k.box_m((s * 0.087, 0.0, 0.175), (0.008, 0.020, 0.024), Z_TIN)
    pts = [Vector((-0.090, 0.0, 0.178)), Vector((-0.07, 0.0, 0.25)), Vector((-0.03, 0.0, 0.293)), Vector((0.03, 0.0, 0.293)),
           Vector((0.07, 0.0, 0.25)), Vector((0.090, 0.0, 0.178))]
    k.tube(pts, 0.0028, Z_STEEL, 5)


@item('Item_RopeCoil')
def _rope(k, pk, n):
    pts = []
    turns = 4.2
    for i in range(int(turns * 24) + 1):
        a = TAU * i / 24
        r = 0.160 - 0.009 * (a / TAU)
        z = 0.0145 + (0.016 if 1.0 < a / TAU < 2.4 else 0.0) + 0.004 * math.sin(a * 0.5)
        pts.append(Vector((r * math.cos(a), r * math.sin(a) * 0.96, z)))
    pts += [Vector((0.06, -0.10, 0.0105)), Vector((0.0, -0.16, 0.0105))]
    k.tube(pts, 0.010, Z_ROPE, 6)


@item('Item_Sack')
def _sack(k, pk, n):
    rings = []
    xs = [-0.236, -0.225, -0.19, -0.12, -0.02, 0.08, 0.15, 0.19, 0.21]
    for x in xs:
        t = (x + 0.236) / 0.446
        s = min(1.0, (x + 0.236) / 0.04) ** 0.5
        neck = 1.0 - 0.75 * max(0.0, (t - 0.80) / 0.20)
        ring = []
        for i in range(14):
            a = TAU * i / 14
            ca, sa = math.cos(a), math.sin(a)
            yy = 0.165 * s * neck * (abs(ca) ** 0.45) * (1 if ca >= 0 else -1) - 0.011
            zz = 0.155 + 0.155 * s * neck * (abs(sa) ** 0.65) * (1 if sa >= 0 else -1)
            ring.append(Vector((x, yy, max(0.0, zz))))
        rings.append(ring)
    k.loft(rings, [Z_JUTE] * (len(rings) - 1), cap0=Z_JUTE, cap1=None)
    k.lathe(Vector((0.21, -0.011, 0.155)), Vector((1, 0, 0)), [(0.0, 0.040), (0.02, 0.020), (0.035, 0.030), (0.05, 0.036),
                                                                (0.05, 0.0)], Z_JUTE, 10, cap0=False)
    k.lathe(Vector((0.228, -0.011, 0.155)), Vector((1, 0, 0)), [(0.0, 0.024), (0.008, 0.024)], Z_ROPE, 10)


@item('Item_Screwdriver')
def _screwdriver(k, pk, n):
    k.lathe(Vector((-0.050, 0.0, 0.011)), Vector((1, 0, 0)), [(0.0, 0.008), (0.004, 0.011), (0.075, 0.0115), (0.090, 0.008),
                                                               (0.098, 0.006)], Z_PL_R, 8)
    k.cyl((0.048, 0.0, 0.011), (0.132, 0.0, 0.011), 0.0034, Z_CHROME, 6)
    k.box_m((0.136, 0.0, 0.011), (0.008, 0.007, 0.0015), Z_CHROME)


@item('Item_Toolbox')
def _toolbox(k, pk, n):
    rbox(k, (-0.23, -0.10, 0.0), (0.23, 0.10, 0.165), Z_PAINT_R, r=0.006, ch=0.003, axis='x')
    for s in (-1, 1):                                                # the two lid halves sloping to the ridge
        k.poly([Vector((-0.226, s * 0.100, 0.165)), Vector((0.226, s * 0.100, 0.165)), Vector((0.226, s * 0.012, 0.205)),
                Vector((-0.226, s * 0.012, 0.205))][::(1 if s > 0 else -1)], Z_PAINT_R)
        for x in (-0.226, 0.226):
            k.poly([Vector((x, s * 0.100, 0.165)), Vector((x, s * 0.012, 0.205)), Vector((x, 0.0, 0.205)),
                    Vector((x, 0.0, 0.165))][::(1 if x * s > 0 else -1)], Z_PAINT_R)
    box6(k, (-0.226, -0.012, 0.205), (0.226, 0.012, 0.208), Z_PAINT_R)
    for x in (-0.12, 0.12):
        box6(k, (x - 0.008, -0.010, 0.205), (x + 0.008, 0.010, 0.235), Z_STEEL)
    k.cyl((-0.13, 0.0, 0.240), (0.13, 0.0, 0.240), 0.013, Z_PL_BK, 8)
    for s in (-1, 1):
        box6(k, (s * 0.2305 - 0.003, -0.025, 0.12), (s * 0.2305 + 0.003, 0.025, 0.175), Z_STEEL)


@item('Item_Wrench')
def _wrench(k, pk, n):
    k.strip([Vector((-0.094, 0.0, 0.0055)), Vector((0.088, 0.0, 0.0030))], (0, 0, 1), 0.014, 0.005, Z_CHROME)
    k.lathe(Vector((-0.108, 0.0, 0.0055)), Vector((0, 0, 1)), [(-0.003, 0.018), (0.003, 0.018)], Z_CHROME, 12)
    for s in (-1, 1):
        k.box_m((0.110, s * 0.012, 0.0030), (0.032, 0.010, 0.006), Z_CHROME)
    k.box_m((0.094, 0.0, 0.0030), (0.010, 0.030, 0.006), Z_CHROME)


def _carton(k, lo, hi, tape=True, open_flaps=False):
    lo, hi = Vector(lo), Vector(hi)
    if not open_flaps:
        rbox(k, lo, hi, Z_CARD, r=0.004, ch=0.002, axis='z')
        if tape:
            box6(k, (lo.x - 0.0005, -0.025, hi.z), (hi.x + 0.0005, 0.025, hi.z + 0.001), Z_TAPE, skip=('-z',))
            for x, s in ((lo.x, -1), (hi.x, 1)):
                box6(k, (x - 0.0005 if s < 0 else x, -0.025, hi.z - 0.07), (x if s < 0 else x + 0.0005, 0.025, hi.z), Z_TAPE)
        return
    t = 0.004
    box6(k, lo, Vector((hi.x, hi.y, lo.z + t)), Z_CARD)
    for s in (-1, 1):
        y = hi.y if s > 0 else lo.y
        box6(k, (lo.x, y - (t if s > 0 else 0), lo.z), (hi.x, y + (0 if s > 0 else t), hi.z), Z_CARD)
        x = hi.x if s > 0 else lo.x
        box6(k, (x - (t if s > 0 else 0), lo.y, lo.z), (x + (0 if s > 0 else t), hi.y, hi.z), Z_CARD)


@item('Item_BoxLarge')
def _box_large(k, pk, n):
    _carton(k, (-0.275, -0.2, 0.0), (0.275, 0.2, 0.399))
    for s in (-1, 1):
        quadp(pk, (0.0, s * 0.2005, 0.25), (0, s, 0), 0.24, 0.128, uv('carton_top'))


@item('Item_BoxSmall')
def _box_small(k, pk, n):
    _carton(k, (-0.15, -0.11, 0.0), (0.15, 0.11, 0.199))
    for s in (-1, 1):
        quadp(pk, (0.0, s * 0.1105, 0.11), (0, s, 0), 0.20, 0.056, uv('carton_parts'))


@item('Item_BoxOpen')
def _box_open(k, pk, n):
    _carton(k, (-0.225, -0.18, 0.0), (0.225, 0.18, 0.30), open_flaps=True)
    for s in (-1, 1):                                                # long flaps open out, end flaps hanging down
        y = s * 0.18
        k.poly([Vector((-0.222, y, 0.30)), Vector((0.222, y, 0.30)), Vector((0.222, y + s * 0.112, 0.336)),
                Vector((-0.222, y + s * 0.112, 0.336))][::(1 if s < 0 else -1)], Z_CARD)
        k.poly([Vector((-0.222, y, 0.30)), Vector((-0.222, y + s * 0.112, 0.336)), Vector((0.222, y + s * 0.112, 0.336)),
                Vector((0.222, y, 0.30))][::(1 if s < 0 else -1)], Z_CARD)
        x = s * 0.225
        k.poly([Vector((x + s * 0.003, -0.176, 0.30)), Vector((x + s * 0.003, 0.176, 0.30)), Vector((x + s * 0.004, 0.176, 0.13)),
                Vector((x + s * 0.004, -0.176, 0.13))][::(1 if s > 0 else -1)], Z_CARD)
        k.poly([Vector((x + s * 0.004, -0.176, 0.13)), Vector((x + s * 0.004, 0.176, 0.13)), Vector((x + s * 0.003, 0.176, 0.30)),
                Vector((x + s * 0.003, -0.176, 0.30))][::(1 if s > 0 else -1)], Z_CARD)
    crumple(k, (-0.10, 0.05, 0.004), (0.12, 0.10, 0.07), Z_PAPER, 91)
    k.cyl((0.02, -0.12, 0.03), (0.17, 0.10, 0.06), 0.016, Z_STEELB, 8)
    k.box_m((0.10, -0.05, 0.03), (0.12, 0.07, 0.05), Z_STEELB, Matrix.Rotation(0.4, 3, 'Z'))


@item('Item_WoodCrate')
def _crate(k, pk, n):
    for x in (-0.285, 0.285):
        for y in (-0.235, 0.235):
            box6(k, (x - 0.02, y - 0.02, 0.0), (x + 0.02, y + 0.02, 0.40), Z_PINE)
    for z0 in (0.02, 0.15, 0.28):
        for s in (-1, 1):
            box6(k, (-0.305, s * 0.255 - 0.009 if s > 0 else -0.255, z0), (0.305, 0.255 if s > 0 else -0.255 + 0.009, z0 + 0.10), Z_PINE)
            box6(k, (s * 0.305 - 0.009 if s > 0 else -0.305, -0.235, z0), (0.305 if s > 0 else -0.305 + 0.009, 0.235, z0 + 0.10), Z_PINE)
    for y in (-0.16, -0.05, 0.06, 0.17):
        box6(k, (-0.265, y - 0.045, 0.0), (0.265, y + 0.045, 0.012), Z_PINE)


# ================================================================ the prologue's things (Forest_Opening.json)
@item('Item_Jerrycan20')
def _jerrycan(k, pk, n):
    """a NATO jerrycan: two pressed halves welded round the edge (the seam rib), the X pressed into both faces,
    three handles on the top in a row (the middle one = Update 3's grip), the spout with its cam-lever cap at +x"""
    rbox(k, (-0.172, -0.081, 0.0), (0.172, 0.081, 0.47), Z_PAINT_O, r=0.022, ch=0.006, axis='y')
    k.strip([Vector((-0.167, 0.0, 0.025)), Vector((-0.167, 0.0, 0.445)), Vector((-0.147, 0.0, 0.465)), Vector((0.147, 0.0, 0.465)),
             Vector((0.167, 0.0, 0.445)), Vector((0.167, 0.0, 0.025)), Vector((0.147, 0.0, 0.005)), Vector((-0.147, 0.0, 0.005))],
            (0, 1, 0), 0.010, 0.010, Z_PAINT_O, caps=True)
    for s in (-1, 1):                                                   # the X on both faces, pressed out 4 mm
        y = s * 0.081
        for (a, b) in (((-0.130, 0.060), (0.130, 0.410)), ((-0.130, 0.410), (0.130, 0.060))):
            d = Vector((b[0] - a[0], 0, b[1] - a[1]))
            L = d.length
            R = VM.frame_R(d.normalized(), Vector((0, 0, 1)) if abs(d.normalized().z) < 0.9 else Vector((1, 0, 0)))
            VM.obox(k, Vector(((a[0] + b[0]) / 2, y + s * 0.002, (a[1] + b[1]) / 2)), (L, 0.004, 0.045), Z_PAINT_O,
                    VM.frame_R(d.normalized(), Vector((0, s, 0))))
        box6(k, (-0.150, y - 0.0005 if s > 0 else y - 0.003, 0.03), (0.150, y + 0.003 if s > 0 else y + 0.0005, 0.044), Z_PAINT_O)
    for xc in (-0.125, -0.035, 0.055):                                   # three handles
        k.tube([Vector((xc - 0.040, 0.0, 0.47)), Vector((xc - 0.034, 0.0, 0.504)), Vector((xc + 0.034, 0.0, 0.504)),
                Vector((xc + 0.040, 0.0, 0.47))], 0.0065, Z_PAINT_O, 6)
    sp = Vector((0.118, 0.0, 0.468))
    mouth = Vector((0.1393, 0.0, 0.5193))                          # Forest_Items.json spout (Unity (-0.1393, 0.5193, 0))
    d = (mouth - sp).normalized()
    Ls = (mouth - sp).length
    k.cyl(sp, mouth, 0.021, Z_PAINT_O, 10)
    k.lathe(mouth, d, [(0.0, 0.027), (0.016, 0.027), (0.020, 0.020), (0.020, 0.0)], Z_PAINT_O, 10)
    k.strip([mouth + d * 0.010 + Vector((-0.026, 0.0, 0.004)), mouth + d * 0.010 + Vector((0.030, 0.0, -0.010)),
             mouth + Vector((0.034, 0.0, -0.032))], (0, 1, 0), 0.005, 0.012, Z_STEEL)


@item('Item_Funnel')
def _funnel(k, pk, n):
    """a galvanised funnel as Update 3's model: the spout down (its tip at the origin), the rim up, a strap loop on its
    side by the rim; the hut's placement (Funnel_Hut, q = 180 deg about a level axis) turns it over onto its rim"""
    H = 0.307
    prof = [(0.0, 0.117), (0.004, 0.117), (0.012, 0.112), (0.175, 0.020), (H, 0.0125),
            (H, 0.0100), (0.177, 0.016), (0.014, 0.108), (0.005, 0.113), (0.0, 0.113), (0.0, 0.117)]
    lathe_z(k, (0, 0, 0), [(H - z, r) for z, r in reversed(prof)], [Z_GALV] * 10, seg=18, cap0=False, cap1=False)
    strap = [Vector((0.108, 0.0, 0.020)), Vector((0.137, 0.0, 0.030)), Vector((0.131, 0.0, 0.065)), Vector((0.090, 0.0, 0.058))]
    k.strip([Vector((v.x, v.y, H - v.z)) for v in reversed(strap)], (0, 1, 0), 0.003, 0.016, Z_GALV)


@item('Item_Flashlight')
def _flashlight(k, pk, n):
    """an olive torch (origin = its centre, the light along +x: Forest_Items.json light.p / d): rubber tail cap, the
    knurled body, the switch, the head with its steel bezel; the glass in M_TorchLens"""
    k.lathe(Vector((-0.118, 0.0, 0.0)), Vector((1, 0, 0)),
            [(0.021, 0.0212), (0.170, 0.0212), (0.190, 0.026), (0.215, 0.028), (0.240, 0.028)], Z_PAINT_O, 14, cap0=False,
            cap1=False)
    k.lathe(Vector((-0.118, 0.0, 0.0)), Vector((1, 0, 0)), [(0.0, 0.0165), (0.003, 0.0215), (0.020, 0.0225), (0.021, 0.0)],
            Z_RUBBER, 14, cap0=True, cap1=False)
    k.lathe(Vector((0.122, 0.0, 0.0)), Vector((1, 0, 0)), [(0.0, 0.028), (0.003, 0.0285), (0.010, 0.0285), (0.010, 0.023)],
            Z_STEEL, 14, cap0=False, cap1=False)
    k.box_m((-0.020, 0.0, 0.0225), (0.024, 0.014, 0.006), Z_RUBBER)
    L = kb('Item_Flashlight_Lens', 'lens:torch')
    L.disc_uv(Vector((0.1315, 0.0, 0.0)), Vector((1, 0, 0)), 0.0232, (0.0, 0.0, 1.0, 1.0), 14, dome=0.002)
    SPECIAL.setdefault('Item_Flashlight', {})['lens'] = ['Item_Flashlight_Lens']


def _key(k, pk, tag_zone, tag_print):
    """a key on a split ring with its tag (origin = the hanging point, the top of the ring)"""
    k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, 1, 0)), [(-0.0012, 0.0115), (0.0012, 0.0115)], Z_STEEL, 12, cap0=False, cap1=False)
    k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, 1, 0)), [(0.0012, 0.0095), (-0.0012, 0.0095)], Z_STEEL, 12, cap0=False, cap1=False)
    for s in (-1, 1):
        k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, s, 0)), [(0.0012, 0.0095), (0.0012, 0.0115)], Z_STEEL, 12, cap0=False, cap1=False)
    # the key (in front, +y): bow, shoulder, blade with the bitting
    yk = 0.0012
    k.lathe(Vector((0.0, yk, -0.0315)), Vector((0, 1, 0)), [(0.0, 0.0105), (0.0022, 0.0105)], Z_BRASS, 12)
    box6(k, (-0.0045, yk, -0.050), (0.0045, yk + 0.0022, -0.040), Z_BRASS)
    box6(k, (-0.0035, yk, -0.0835), (0.0035, yk + 0.0022, -0.050), Z_BRASS)
    for i, d in enumerate((0.002, 0.004, 0.0015, 0.0035, 0.002)):
        z = -0.055 - i * 0.0055
        box6(k, (0.0035, yk, z - 0.0026), (0.0035 + d, yk + 0.0022, z + 0.0026), Z_BRASS)
    # the tag (behind, -y): a rounded plastic tag on a short link, the paper insert printed
    rbox(k, (-0.0145, -0.0032, -0.078), (0.0145, -0.0010, -0.026), tag_zone, r=0.005, ch=0.0008, axis='y')
    quadp(pk, (0.0, -0.00325, -0.052), (0, -1, 0), 0.040, 0.022, uv(tag_print), up=(1, 0, 0))
    k.tube([Vector((0.0, -0.002, -0.0215)), Vector((0.0, -0.002, -0.027))], 0.0012, Z_STEEL, 4)


@item('Item_Key_Schranke')
def _k1(k, pk, n):
    _key(k, pk, Z_PL_R, 'tag_schranke')


@item('Item_Key_Hauptgebaeude')
def _k2(k, pk, n):
    _key(k, pk, Z_PL_BL, 'tag_haupt')


@item('Item_Key_Garage')
def _k3(k, pk, n):
    _key(k, pk, Z_PL_GR, 'tag_garage')


@item('Item_Key_Generator')
def _k4(k, pk, n):
    _key(k, pk, Z_PAINT_Y, 'tag_generator')


@item('Item_Padlock')
def _padlock(k, pk, n):
    """a brass padlock with its steel shackle (origin = the hanging point: the inside of the shackle's top)"""
    rbox(k, (-0.025, -0.0125, -0.070), (0.025, 0.0115, -0.030), Z_BRASS, r=0.006, ch=0.002, axis='y')
    pts = [Vector((-0.0155, -0.0005, -0.031)), Vector((-0.0155, -0.0005, -0.010))]
    for i in range(1, 12):
        a = math.pi - math.pi * i / 12
        pts.append(Vector((0.0155 * math.cos(a), -0.0005, -0.010 + 0.0155 * math.sin(a) * 1.05)))
    pts += [Vector((0.0155, -0.0005, -0.010)), Vector((0.0155, -0.0005, -0.026))]
    k.tube(pts, 0.0042, Z_STEEL, 6)
    k.box_m((0.0, -0.0128, -0.062), (0.004, 0.001, 0.010), Z_STEELB)


# ================================================================ new: the control room's radio set (X08)
@item('Item_RadioSet')
def _radioset(k, pk, n):
    """an old fixed transceiver on the console: grey hammered case, the front printed (meter, channel window, keys),
    knobs, the hand microphone on its clip with a coiled cord, rubber feet; the antenna lead out of the back"""
    box6(k, (-0.16, -0.12, 0.012), (0.16, 0.12, 0.120), Z_GREYM, skip=('-y',))
    quadp(pk, (0.0, -0.1202, 0.066), (0, -1, 0), 0.32, 0.108, uv('radio_set'))
    box6(k, (-0.162, -0.122, 0.012), (0.162, -0.115, 0.016), Z_STEELB)
    box6(k, (-0.162, -0.122, 0.116), (0.162, -0.115, 0.120), Z_STEELB)
    for x in (0.105, 0.128):
        k.cyl((x, -0.121, 0.086), (x, -0.137, 0.086), 0.009, Z_PL_BK, 10)
    k.cyl((0.116, -0.121, 0.040), (0.116, -0.140, 0.040), 0.014, Z_PL_BK, 10)
    for x in (-0.14, 0.14):
        for y in (-0.10, 0.10):
            k.cyl((x, y, 0.0), (x, y, 0.012), 0.009, Z_RUBBER, 8)
    for i in range(7):                                               # vents on the top
        box6(k, (-0.11 + i * 0.03, 0.02, 0.1195), (-0.10 + i * 0.03, 0.10, 0.1205), Z_STEELB, skip=('-z',))
    # the microphone on its clip at the right side, the coiled cord to the front
    box6(k, (0.160, -0.03, 0.06), (0.166, 0.01, 0.09), Z_STEELB)
    rbox(k, (0.166, -0.045, 0.040), (0.196, 0.025, 0.110), Z_PL_BK, r=0.012, ch=0.004, axis='y')
    box6(k, (0.170, -0.046, 0.085), (0.188, -0.044, 0.095), Z_GREYM)
    pts = []
    for i in range(40):
        t = i / 39
        a = TAU * 9 * t
        c = Vector((0.181, -0.045, 0.040)).lerp(Vector((0.140, -0.122, 0.020)), t)
        pts.append(c + Vector((0.0, 0.006 * math.cos(a), 0.006 * math.sin(a))))
    k.tube(pts, 0.0022, Z_PL_BK, 4)
    k.tube([Vector((-0.10, 0.12, 0.08)), Vector((-0.10, 0.15, 0.08)), Vector((-0.12, 0.17, 0.02)), Vector((-0.14, 0.17, 0.004))],
           0.004, Z_PL_BK, 5)
    # the channel display: its own quad and material over the print's window (M_RadioDisplay; X08 swaps to
    # M_RadioDisplayOn, whose emission map lights the channel)
    px0, py0, px1, py1 = 36, 8, 92, 18                                # the window in the radio_set print (132 x 48 px)
    cx = -0.16 + (px0 + px1) / 2 / 132 * 0.32
    cz = 0.120 - (py0 + py1) / 2 / 48 * 0.108
    D = kb('Item_RadioSet_Display', 'display')
    quadp(D, (cx, -0.1207, cz), (0, -1, 0), (px1 - px0) / 132 * 0.32, (py1 - py0) / 48 * 0.108, uv('radio_disp'))
    SPECIAL.setdefault('Item_RadioSet', {})['display'] = ['Item_RadioSet_Display']
