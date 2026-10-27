"""forest_world geometry: things of the Forest map that are not buildings, in the generator shed's style. Four roots, each in
its own frame (Blender: z up, the front -y, metres; origin on the ground, z = 0; Unity (x, y, z) -> (-x, z, -y), the front
-> +Z):
  FireBarrel    a warm island (VISION 4: 'у точек интереса - тёплые островки: бочка с огнём'): a 200 l drum with the lid
                cut out, burnt to rust, air holes round the foot; inside ash, split logs (FireBarrel_Fuel), the glow of the
                embers and the holes (FireBarrel_Glow: M_World_Embers / _Off), the flames (FireBarrel_Flames: three
                crossed cards with the 8-frame flipbook M_World_Fire); Light_Fire, Slot_Fuel
  ShiftCar      the previous shift's car on the base parking (anchors/Car_Parked): an 80s off-roader without make or
                badges in the station's grey-green, RADIOOBSERVATORIUM HOHENMOOS on the front doors; the driver's door
                and the side-hinged rear door with the spare wheel open; ShiftCar_Snow - the snow on it (a separate part)
  WreckCar      a second abandoned car, long gone: an 80s saloon, faded blue, rusted through, the front right wheel
                gone (it sits on the brake disc), the windscreen cracked, the driver's window and the rear right window
                broken; the driver's door and the boot lid open (the boot lid ajar); WreckCar_Snow
  ForesterCave  the Forester's cave (MONSTERS, TASKS I1): a granite outcrop with a low passage into a chamber - the
                rock shell from a distance field (world_cave_sdf.py), the sleeping place in the niche (spruce boughs,
                army blankets), candle stubs on a stone, the bow saw with fresh sawdust (S5), the old shift's boots
                (X11), a heap of stolen junk, the 1991 newspaper, the nail for the key (Slot_Key: forest_gear's
                Item_Key_Stationsleiter), sockets for the stolen things (Slot_Stash_*), Sleep_Forester, the candles'
                lights; COL_Cave - a simplified copy of the shell (MeshCollider)
Explicit-UV faces (the door marking, the newspaper) join their bodies at build time (MERGE); parts / sockets in each
root's frame (the contract); in the .blend the roots stand apart (DISPLAY)."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import gen_kit as K
from gen_kit import kb, box6, face, KBS, CONTRACT, transform_kb
from van2_kit import ZERO
import van3_mech as VM
import world_tex as WT

uv = WT.uv
TAU = 2 * math.pi
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ROOTS = ['FireBarrel', 'ShiftCar', 'WreckCar', 'ForesterCave']
DISPLAY = {'FireBarrel': Vector((-3.2, -6.5, 0.0)), 'ShiftCar': Vector((-3.0, 0.0, 0.0)), 'WreckCar': Vector((3.0, 0.0, 0.0)),
           'ForesterCave': Vector((0.0, 9.0, 0.0))}
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
LIGHTS = []                       # (name, parent, pos, dir, kind, colour, range, note)
CAVE_NPZ = '/home/claude/uaz/out/world_work/cave.npz'

# World atlas: the barrel and the cars
(Z_DRUM, Z_DRUMIN, Z_ASH, Z_LOG, Z_CHAR,
 Z_PAINT_S, Z_PAINT_W, Z_CBLACK, Z_UNDER, Z_TYRE, Z_RIM, Z_CHROME, Z_HEAD, Z_TAIL, Z_SEAT, Z_DASH, Z_CARPET, Z_LINER,
 Z_CARD, Z_GRILLE, Z_PLATE, Z_CARGO, Z_GAUGE, Z_RUBBER, Z_SNOW, Z_DISC, Z_RACK, Z_AMBER) = range(700, 728)
WORLD_ZONES = list(range(700, 728))
# Cave atlas
(Z_ROCK, Z_ROCKIN, Z_CFLOOR, Z_ROCKD, Z_BOUGH, Z_BLANKET, Z_CANDLE, Z_WAX, Z_SAWB, Z_SAWF, Z_SAWDUST, Z_BOOT, Z_SOLE,
 Z_TIN, Z_NAIL, Z_RAG, Z_BUCKET, Z_WIRE, Z_STONE, Z_BOTTLE) = range(760, 780)
CAVE_ZONES = list(range(760, 780))


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


def triangulate_ngons(k):
    big = [f for f in k.bm.faces if len(f.verts) > 4]
    if big:
        bmesh.ops.triangulate(k.bm, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')


def axes(t, ref=Vector((0, 0, 1))):
    """(t, s, w): t along the given direction, s = t x ref, w = s x t (orthonormal)"""
    t = Vector(t).normalized()
    r = Vector(ref).normalized()
    if abs(t.dot(r)) > 0.95:
        r = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    s = t.cross(r).normalized()
    return t, s, s.cross(t).normalized()


def hsh(i, s=0):
    x = math.sin(i * 12.9898 + s * 78.233) * 43758.5453
    return x - math.floor(x)


# ================================================================ FireBarrel
DR = dict(r=0.286, h=0.86, hoops=(0.29, 0.58), ash=0.42, holes=((0.10, 10, 0.0), (0.24, 8, 0.5)))


def build_barrel():
    k = reg('FireBarrel', 'World', 'FireBarrel')
    r, h = DR['r'], DR['h']
    prof = [(0.0, r - 0.006), (0.012, r + 0.006), (0.030, r)]
    for zh in DR['hoops']:                                              # the rolling hoops
        prof += [(zh - 0.022, r), (zh - 0.010, r + 0.011), (zh + 0.010, r + 0.011), (zh + 0.022, r)]
    prof += [(h - 0.03, r), (h, r + 0.008)]                             # the cut rim bent a little outward
    k.lathe(Vector((0, 0, 0)), Z, prof, Z_DRUM, 24, cap0=True, cap1=False)
    inner = [(h, r + 0.004), (h - 0.03, r - 0.004), (DR['ash'], r - 0.004)]   # the inside wall (normals in)
    k.lathe(Vector((0, 0, 0)), Z, inner, Z_DRUMIN, 24, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(h, r + 0.008), (h + 0.004, r + 0.006), (h, r + 0.004)], Z_DRUM, 24, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, DR['ash'])), Z, [(0.0, r - 0.004), (0.006, 0.20), (0.012, 0.0)], Z_ASH, 24, cap0=False, cap1=False)
    # the fuel: split logs on the ash, two standing up over the rim
    f = reg('FireBarrel_Fuel', 'World', 'FireBarrel')
    logs = [((-0.10, 0.04, 0.47), (0.12, -0.10, 0.56), 0.050), ((0.08, 0.09, 0.46), (-0.14, -0.04, 0.52), 0.045),
            ((0.02, -0.15, 0.46), (0.04, 0.16, 0.55), 0.048), ((-0.16, -0.02, 0.50), (-0.02, 0.12, 0.92), 0.042),
            ((0.12, -0.06, 0.48), (0.06, 0.05, 0.96), 0.046), ((-0.04, 0.16, 0.50), (0.10, 0.12, 0.80), 0.040)]
    for i, (a, b, rr) in enumerate(logs):
        a, b = Vector(a), Vector(b)
        t, s, w = axes(b - a, Z)
        sec = []
        for j in range(5):                                              # a split log: a pentagon, one flat face
            ang = TAU * j / 5 + hsh(i, 3) * 1.2
            rad = rr * (0.75 if j == 0 else 1.0)
            sec.append(s * math.cos(ang) * rad + w * math.sin(ang) * rad)
        ra = [a + q for q in sec]
        rb = [b + q for q in sec]
        f.loft([ra, rb], [Z_LOG], cap0=Z_CHAR, cap1=Z_CHAR)
    # the glow: the embers on the ash and the air holes round the foot (one object: M_World_Embers / _Off)
    g = reg('FireBarrel_Glow', 'embers', 'FireBarrel')
    g.lathe(Vector((0, 0, DR['ash'] + 0.016)), Z, [(0.0, 0.27), (0.004, 0.0)], ZERO, 16, cap0=False, cap1=False)
    hole_pts = []
    for zh, n, ph in DR['holes']:
        for i in range(n):
            a = TAU * (i + ph) / n
            nrm = Vector((math.cos(a), math.sin(a), 0.0))
            c = nrm * (r + 0.0025) + Z * zh
            g.quad_uv(c, nrm, 0.036, 0.036 if zh < 0.2 else 0.028, (0, 0, 1, 1))
            hole_pts.append(c)
    # the flames: three crossed cards, both sides, frame 0 of the flipbook
    fl = reg('FireBarrel_Flames', 'fire', 'FireBarrel')
    w_, h_ = 0.52, 0.86
    z0 = DR['ash'] + 0.05
    for i in range(3):
        a = math.pi * i / 3
        d = Vector((math.cos(a), math.sin(a), 0.0))
        p0, p1 = -d * (w_ / 2) + Z * z0, d * (w_ / 2) + Z * z0
        q = [p0, p1, p1 + Z * h_, p0 + Z * h_]
        uvs = [(0.0, 0.0), (1 / 8, 0.0), (1 / 8, 1.0), (0.0, 1.0)]
        fl.poly(q, ZERO, uvs)
        fl.poly(list(reversed(q)), ZERO, list(reversed(uvs)))
    part('FireBarrel', 'static', (0, 0, 0),
         note='the fire barrel (root): a 200 l drum, the lid cut out, air holes round the foot; origin under its middle; '
              'a warm island: R1 (creatures keep off warm yellow light) and no wind-chill within warm_radius (meta)')
    part('FireBarrel_Fuel', 'static', (0, 0, DR['ash']), parent='FireBarrel', states=['empty', 'full'],
         note='the split logs in it (hide when burnt out); Slot_Fuel takes wood and the paper / wood rubbish of forest_trash')
    part('FireBarrel_Glow', 'static', (0, 0, DR['ash']), parent='FireBarrel', states=['cold', 'embers', 'burning'],
         note='the embers on the ash and the 18 air holes: M_World_Embers_Off (cold: dark holes) / M_World_Embers (lit)')
    part('FireBarrel_Flames', 'static', (0, 0, z0), parent='FireBarrel', states=['off', 'on'],
         note='three crossed flame cards, M_World_Fire: the 8 frames side by side - step u by 1/8 at ~10 fps (or play '
              'them in random order); hidden when off; ~0.86 m of flame over the ash, the lower third inside the drum')
    socket('Slot_Fuel', (0, 0, h + 0.02), 'slot', parent='FireBarrel', note='drop wood / paper / wood rubbish in from above',
           dir=(0, 0, -1))
    socket('Light_Fire', (0, 0, 1.05), 'light', parent='FireBarrel',
           note='point light, warm (1.0, 0.55, 0.22) linear, range 9 m, flicker 0.75-1.0 at 6-10 Hz; off when cold, '
                'weak and steady with embers')
    BOXES.append(('FireBarrel', 'FireBarrel', (-r - 0.01, r + 0.01, -r - 0.01, r + 0.01, 0.0, h + 0.01), None))
    MASS['FireBarrel'] = 25.0
    LIGHTS.append(('Light_Fire', 'FireBarrel', (0, 0, 1.05), None, 'point', (1.0, 0.55, 0.22), 9.0, 'flicker'))


# ================================================================ the cars: one generator, two specs
SHIFT = dict(name='ShiftCar', paint=Z_PAINT_S, CW=0.88, YF=-2.10, YR=2.12, YFA=-1.30, YRA=1.10, TRK=0.75, RW=0.36,
             RWID=0.24, RA=0.45, ZSILL=0.50, ZFB=0.40, ZRB=0.42, ZHF=1.06, ZHW=1.12, YWS=-0.80, ZBR=1.15,
             WB=0.86, WR=0.82, ZB=1.16, ZR=1.86, YRF=-0.66, YRR=2.08, ZROOF=1.90, rear='box',
             pillars=[(0.10, 0.20, 0.10, 0.20), (1.02, 1.12, 1.02, 1.12), (1.98, 2.10, 1.98, 2.10)],
             door=dict(y0=-0.74, y1=0.10, z0=0.53), floor=0.66, seat_rows=(0.10, 0.95), lamps='round', rack=True,
             bench=True)
WRECK = dict(name='WreckCar', paint=Z_PAINT_W, CW=0.86, YF=-2.28, YR=2.34, YFA=-1.40, YRA=1.36, TRK=0.72, RW=0.30,
             RWID=0.185, RA=0.37, ZSILL=0.30, ZFB=0.30, ZRB=0.32, ZHF=0.76, ZHW=0.85, YWS=-0.66, ZBR=0.90,
             WB=0.84, WR=0.70, ZB=0.89, ZR=1.36, YRF=0.00, YRR=1.04, ZROOF=1.39, rear='saloon', YDECK=1.66, ZDECK=0.92,
             pillars=[(0.50, 0.58, 0.48, 0.56), (1.28, 1.66, 1.00, 1.04)], door=dict(y0=-0.62, y1=0.50, z0=0.34),
             floor=0.34, seat_rows=(0.08, 0.90), lamps='rect', rack=False, bench=True)


class Car:
    def __init__(self, S):
        self.S = S
        self.n = S['name']

    # ---- the glasshouse's side plane: (x, z) at height fraction t (0 belt .. 1 roof edge)
    def gh(self, t, side):
        S = self.S
        return side * (S['WB'] + (S['WR'] - S['WB']) * t), S['ZB'] + (S['ZR'] - S['ZB']) * t

    def P(self, y, t, side, inset=0.0):
        x, z = self.gh(t, side)
        return Vector((x - side * inset, y, z))

    def z_top(self, y):
        S = self.S
        if y <= S['YWS']:
            return S['ZHF'] + (S['ZHW'] - S['ZHF']) * (y - S['YF']) / (S['YWS'] - S['YF'])
        return S['ZHW'] + (S['ZBR'] - S['ZHW']) * (y - S['YWS']) / (S['YR'] - S['YWS'])

    def arch(self, yc):
        S = self.S
        return [(yc + S['RA'] * math.cos(math.radians(a)), S['RW'] + S['RA'] * math.sin(math.radians(a)) + 0.01)
                for a in range(180, -1, -15)]

    def body(self):
        S, n = self.S, self.n
        k = reg(n, 'World', n)
        self.k = k
        CW, PZ = S['CW'], S['paint']
        d = S['door']
        yd0, yd1, zd0 = d['y0'], d['y1'], d['z0']
        bottom = ([(S['YF'] + 0.005, S['ZFB']), (S['YF'] + 0.07, S['ZSILL'] + 0.01)] + self.arch(S['YFA']) +
                  [(yd0, S['ZSILL']), (yd1, S['ZSILL'])] + self.arch(S['YRA']) + [(S['YR'], S['ZRB'])])
        bottom = sorted(bottom, key=lambda t: t[0])
        full = [(y, z, self.z_top(y)) for y, z in bottom]

        def strips(xs, nx, sta):
            for (ya, za, ta), (yb, zb, tb) in zip(sta[:-1], sta[1:]):
                if yb - ya < 1e-6:
                    continue
                face(k, [(xs, ya, za), (xs, yb, zb), (xs, yb, tb), (xs, ya, ta)], PZ, (nx, 0, 0))
        strips(-CW, -1, full)
        strips(CW, 1, [t for t in full if t[0] <= yd0 + 1e-6])
        strips(CW, 1, [(yd0, S['ZSILL'], zd0), (yd1, S['ZSILL'], zd0)])
        strips(CW, 1, [t for t in full if t[0] >= yd1 - 1e-6])
        for yy, nn in ((yd0, (0, 1, 0)), (yd1, (0, -1, 0))):                       # the door opening's jambs
            face(k, [(CW - 0.05, yy, zd0), (CW, yy, zd0), (CW, yy, self.z_top(yy)), (CW - 0.05, yy, self.z_top(yy))], Z_UNDER, nn)
        face(k, [(CW - 0.05, yd0, zd0), (CW, yd0, zd0), (CW, yd1, zd0), (CW - 0.05, yd1, zd0)], Z_UNDER, (0, 0, 1))
        # the hood (a crown down the middle) to the windscreen
        cr = 0.012
        for xa, xb in ((-CW, 0.0), (0.0, CW)):
            face(k, [(xa, S['YF'], S['ZHF'] + (cr if xa == 0 else 0)), (xb, S['YF'], S['ZHF'] + (cr if xb == 0 else 0)),
                     (xb, S['YWS'], S['ZHW'] + (cr if xb == 0 else 0)), (xa, S['YWS'], S['ZHW'] + (cr if xa == 0 else 0))], PZ, (0, 0, 1))
        # the front face: bumper low, the lamps, the grille, paint between
        yfr = S['YF']
        zb_ = S['ZFB']
        if S['lamps'] == 'round':
            xs = [-CW, -0.30, 0.30, CW]
            zs = [zb_, zb_ + 0.16, S['ZHF'] - 0.06, S['ZHF']]
        else:
            xs = [-CW, -0.80, -0.40, -0.38, 0.38, 0.40, 0.80, CW]
            zs = [zb_, zb_ + 0.16, zb_ + 0.24, S['ZHF'] - 0.04, S['ZHF']]
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                xa, xb, za, zb = xs[i], xs[i + 1], zs[j], zs[j + 1]
                xm, zm = (xa + xb) / 2, (za + zb) / 2
                zone = PZ
                if zb <= zb_ + 0.16 + 1e-6:
                    zone = Z_CBLACK
                elif S['lamps'] == 'round' and abs(xm) < 0.30 and zm < S['ZHF'] - 0.06:
                    zone = Z_GRILLE
                elif S['lamps'] == 'rect' and zb_ + 0.24 <= zm <= S['ZHF'] - 0.04 and 0.40 <= abs(xm) <= 0.80:
                    zone = Z_HEAD
                elif S['lamps'] == 'rect' and abs(xm) < 0.38 and zm > zb_ + 0.16:
                    zone = Z_GRILLE
                face(k, [(xa, yfr, za), (xb, yfr, za), (xb, yfr, zb), (xa, yfr, zb)], zone, (0, -1, 0))
        if S['lamps'] == 'round':                                                 # round headlamps in chrome bezels
            for sx in (-1, 1):
                c = Vector((sx * 0.60, yfr, S['ZHF'] - 0.24))
                k.lathe(c, -Y, [(0.0, 0.105), (0.02, 0.105), (0.025, 0.09)], Z_CHROME, 12, cap0=False, cap1=False)
                k.lathe(c - Y * 0.02, -Y, [(0.0, 0.09), (0.012, 0.075), (0.016, 0.0)], Z_HEAD, 12, cap0=False, cap1=False)
                k.box(sx * 0.60 - 0.06, sx * 0.60 + 0.06, yfr - 0.015, yfr, S['ZHF'] - 0.40, S['ZHF'] - 0.34, Z_AMBER)
        # the rear: the lower face with the lamps (the saloon) or the frame round the rear door (the off-roader)
        yr = S['YR']
        if S['rear'] == 'saloon':
            xs = [-CW, -0.62, -0.24, 0.24, 0.62, CW]
            zs = [S['ZRB'], S['ZRB'] + 0.15, S['ZRB'] + 0.30, S['ZDECK'] - 0.10]
            for i in range(len(xs) - 1):
                for j in range(len(zs) - 1):
                    xa, xb, za, zb = xs[i], xs[i + 1], zs[j], zs[j + 1]
                    xm, zm = (xa + xb) / 2, (za + zb) / 2
                    zone = PZ
                    if zb <= S['ZRB'] + 0.15 + 1e-6:
                        zone = Z_CBLACK
                    elif abs(xm) > 0.62:
                        zone = Z_TAIL
                    elif abs(xm) < 0.24 and zm < S['ZRB'] + 0.30:
                        zone = Z_PLATE
                    face(k, [(xa, yr, za), (xb, yr, za), (xb, yr, zb), (xa, yr, zb)], zone, (0, 1, 0))
        else:
            face(k, [(-CW, yr, S['ZRB']), (CW, yr, S['ZRB']), (CW, yr, S['ZRB'] + 0.16), (-CW, yr, S['ZRB'] + 0.16)], Z_CBLACK, (0, 1, 0))
            for sx in (-1, 1):                                                   # the frame's sides and the tail lamps in them
                xo, xi = sx * CW, sx * 0.80
                face(k, [(xi, yr, S['ZRB'] + 0.16), (xo, yr, S['ZRB'] + 0.16), (xo, yr, S['ZBR']), (xi, yr, S['ZBR'])], PZ, (0, 1, 0))
                k.box(*sorted((sx * 0.81, sx * 0.87)), yr, yr + 0.02, 0.78, 1.02, Z_TAIL)
            face(k, [(-0.80, yr - 0.005, S['ZRB'] + 0.16), (0.80, yr - 0.005, S['ZRB'] + 0.16), (0.80, yr - 0.005, S['ZRB'] + 0.21),
                     (-0.80, yr - 0.005, S['ZRB'] + 0.21)], PZ, (0, 1, 0))
        # under: the floor pan, the front apron, the wheel wells
        face(k, [(-CW, S['YF'] + 0.07, S['ZSILL']), (CW, S['YF'] + 0.07, S['ZSILL']), (CW, yr, S['ZSILL']), (-CW, yr, S['ZSILL'])],
             Z_UNDER, (0, 0, -1))
        face(k, [(-CW, S['YF'] + 0.005, S['ZFB']), (CW, S['YF'] + 0.005, S['ZFB']), (CW, S['YF'] + 0.07, S['ZSILL'] + 0.01),
                 (-CW, S['YF'] + 0.07, S['ZSILL'] + 0.01)], Z_UNDER, (0, -1, -1))
        for yc in (S['YFA'], S['YRA']):
            for s in (-1, 1):
                arc = [(yc + S['RA'] * math.cos(math.radians(a)), S['RW'] + S['RA'] * math.sin(math.radians(a)) + 0.01)
                       for a in range(0, 181, 15)]
                xin = s * (CW - S['RWID'] - 0.06)
                for (ya, za), (yb, zb) in zip(arc[:-1], arc[1:]):
                    nn = Vector((0, -(ya + yb) / 2 + yc, -((za + zb) / 2 - S['RW']))).normalized()
                    face(k, [(s * CW, ya, za), (s * CW, yb, zb), (xin, yb, zb), (xin, ya, za)], Z_UNDER, nn)
                face(k, [(xin, y, z) for y, z in arc], Z_UNDER, (s, 0, 0))
        # bumpers, the scuttle, the wipers, the belt-line tops, the handles
        k.box(-CW - 0.01, CW + 0.01, S['YF'] - 0.10, S['YF'], S['ZFB'] + 0.01, S['ZFB'] + 0.18, Z_CBLACK)
        k.box(-CW - 0.01, CW + 0.01, yr, yr + 0.07, S['ZRB'] + 0.01, S['ZRB'] + 0.18, Z_CBLACK)
        k.box(-CW + 0.08, CW - 0.08, S['YWS'] - 0.02, S['YWS'] + 0.08, S['ZHW'] - 0.01, S['ZHW'] + 0.015, Z_CBLACK)
        for xw in (-0.36, 0.20):
            k.strip([Vector((xw, S['YWS'] + 0.04, S['ZHW'] + 0.025)), Vector((xw + 0.42, S['YWS'] + 0.10, S['ZHW'] + 0.06))],
                    Vector((0, -0.6, 0.8)), 0.02, 0.012, Z_CBLACK)
        for s in (-1, 1):
            segs = [(S['YWS'], yr)] if s < 0 else [(S['YWS'], yd0), (yd1, yr)]
            for ya, yb in segs:
                face(k, [(s * (CW - 0.05), ya, self.z_top(ya)), (s * CW, ya, self.z_top(ya)), (s * CW, yb, self.z_top(yb)),
                         (s * (CW - 0.05), yb, self.z_top(yb))], PZ, (0, 0, 1))
        hz = S['ZB'] - 0.12
        hand = [(-1, (yd0 + yd1) / 2 + 0.25)]
        if S['rear'] == 'saloon':
            hand += [(-1, S['pillars'][0][1] + 0.45), (1, S['pillars'][0][1] + 0.45)]
        for s, yh in hand:
            k.box(*sorted((s * CW, s * (CW + 0.018))), yh - 0.07, yh + 0.07, hz, hz + 0.03, Z_CHROME)
        triangulate_ngons(k)

    def glasshouse(self, broken=()):
        S, n, k = self.S, self.n, self.k
        g = reg(n + '_Glass', 'glass', n)
        self.g = g
        WR, WB, ZR, ZB, ZRF, PZ = S['WR'], S['WB'], S['ZR'], S['ZB'], S['ZROOF'], S['paint']
        yrf, yrr = S['YRF'], S['YRR']
        face(k, [(-WR - 0.01, yrf - 0.02, ZRF), (WR + 0.01, yrf - 0.02, ZRF), (WR + 0.01, yrr + 0.02, ZRF), (-WR - 0.01, yrr + 0.02, ZRF)],
             PZ, (0, 0, 1))
        for s in (-1, 1):
            face(k, [(s * (WR + 0.01), yrf - 0.02, ZRF), (s * (WR + 0.01), yrr + 0.02, ZRF), (s * WR, yrr, ZR), (s * WR, yrf, ZR)], PZ,
                 (s, 0, 0))
        face(k, [(-WR, yrf - 0.02, ZRF), (WR, yrf - 0.02, ZRF), (WR, yrf, ZR), (-WR, yrf, ZR)], PZ, (0, -1, 0))
        face(k, [(-WR, yrr, ZR), (WR, yrr, ZR), (WR, yrr + 0.02, ZRF), (-WR, yrr + 0.02, ZRF)], PZ, (0, 1, 0))
        face(k, [(-WR + 0.03, yrf + 0.02, ZR - 0.035), (WR - 0.03, yrf + 0.02, ZR - 0.035), (WR - 0.03, yrr - 0.02, ZR - 0.035),
                 (-WR + 0.03, yrr - 0.02, ZR - 0.035)], Z_LINER, (0, 0, -1))
        pil = S['pillars']
        for s in (-1, 1):
            P = lambda y, t, inset=0.0: self.P(y, t, s, inset)
            a0, a1 = P(S['YWS'], 0.0), P(yrf, 1.0)                              # the A pillar along the windscreen edge
            k.strip([a0 + Vector((0, 0.02, 0)), a1 + Vector((0, 0.02, -0.01))], Vector((s, 0, 0.25)), 0.08, 0.05, PZ)
            for (b0, b1, r0, r1) in pil:
                q = [P(b0, 0.0), P(b1, 0.0), P(r1, 1.0), P(r0, 1.0)]
                face(k, q, PZ, (s, 0, 0.3))
                qi = [P(b0, 0.0, 0.04), P(b1, 0.0, 0.04), P(r1, 1.0, 0.04), P(r0, 1.0, 0.04)]
                face(k, qi, Z_LINER, (-s, 0, -0.3))
                for (p0, p1, q0, q1), nn in (((q[0], q[3], qi[0], qi[3]), (0, -1, 0)), ((q[1], q[2], qi[1], qi[2]), (0, 1, 0))):
                    face(k, [p0, p1, q1, q0], Z_CBLACK, nn)
            segs = [(S['YWS'], pil[-1][1])] if s < 0 else [(pil[0][1], pil[-1][1])]
            for ya, yb in segs:                                                  # the window rubbers along the belt
                k.box(*sorted((s * (WB - 0.01), s * (WB + 0.012))), ya, yb, ZB - 0.012, ZB + 0.012, Z_RUBBER)
            # the side glass between the pillars (the driver's front window is in its door)
            edges = [('A', None)] + list(pil)
            for i in range(len(edges) - 1):
                if s > 0 and i == 0:
                    continue
                tag = f'{"L" if s > 0 else "R"}{i}'
                if tag in broken:
                    continue
                if i == 0:
                    pts = [P(S['YWS'] + 0.06, 0.04, 0.012), P(pil[0][0], 0.04, 0.012), P(pil[0][2], 0.97, 0.012), P(yrf + 0.05, 0.97, 0.012)]
                else:
                    pa, pb = edges[i], edges[i + 1]
                    pts = [P(pa[1], 0.04, 0.012), P(pb[0], 0.04, 0.012), P(pb[2], 0.97, 0.012), P(pa[3], 0.97, 0.012)]
                face(g, pts, ZERO, (s, 0, 0.3))
                face(g, list(reversed(pts)), ZERO, (-s, 0, -0.3))
        # the windscreen (its own object on the wreck: cracked glass) and its rubbers
        ws = [Vector((-WB + 0.07, S['YWS'] + 0.03, ZB + 0.01)), Vector((WB - 0.07, S['YWS'] + 0.03, ZB + 0.01)),
              Vector((WR - 0.045, yrf + 0.01, ZR - 0.01)), Vector((-WR + 0.045, yrf + 0.01, ZR - 0.01))]
        if 'WS' in broken:
            gw = reg(n + '_Windscreen', 'glasscrack', n)
            gw.poly([ws[1], ws[0], ws[3], ws[2]], ZERO, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
            gw.poly([ws[0], ws[1], ws[2], ws[3]], ZERO, [(1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)])
            part(n + '_Windscreen', 'static', (0, (S['YWS'] + yrf) / 2, (ZB + ZR) / 2), parent=n,
                 note='the cracked windscreen: M_World_GlassCracked (UV 0..1, the impact low on the passenger side)')
        else:
            face(g, ws, ZERO, (0, -0.6, 0.8))
            face(g, list(reversed(ws)), ZERO, (0, 0.6, -0.8))
        k.strip([ws[0], ws[1]], Vector((0, -0.6, 0.8)), 0.03, 0.02, Z_RUBBER, caps=False)
        k.strip([ws[3], ws[2]], Vector((0, -0.6, 0.8)), 0.03, 0.02, Z_RUBBER, caps=False)
        if S['rear'] == 'saloon':                                                # the rear window down to the boot deck
            yd, zd = S['YDECK'], S['ZDECK']
            rw = [Vector((WR - 0.03, yrr + 0.015, ZR - 0.015)), Vector((-WR + 0.03, yrr + 0.015, ZR - 0.015)),
                  Vector((-WB + 0.10, yd - 0.03, zd + 0.02)), Vector((WB - 0.10, yd - 0.03, zd + 0.02))]
            face(g, rw, ZERO, (0, 1, 0.6))
            face(g, list(reversed(rw)), ZERO, (0, -1, -0.6))
            k.strip([rw[2], rw[3]], Vector((0, 1, 0.6)), 0.03, 0.02, Z_RUBBER, caps=False)
            face(k, [(-WB, yd, zd), (WB, yd, zd), (WB - 0.02, yd - 0.06, zd + 0.01), (-WB + 0.02, yd - 0.06, zd + 0.01)], PZ, (0, 0, 1))
            # the parcel shelf under it (inside)
            face(k, [(-WB + 0.05, pil[-1][0], ZB - 0.02), (WB - 0.05, pil[-1][0], ZB - 0.02), (WB - 0.05, yd - 0.05, ZB - 0.02),
                     (-WB + 0.05, yd - 0.05, ZB - 0.02)], Z_DASH, (0, 0, 1))
        part(n + '_Glass', 'static', (0, (yrf + yrr) / 2, ZB + 0.3), parent=n, note='the fixed windows (dirty glass, M_World_Glass)')

    def door(self, broken_glass=False):
        S, n = self.S, self.n
        nm = 'IX_' + n + 'Door'
        D = reg(nm, 'World', n)
        d = S['door']
        CW, PZ = S['CW'], S['paint']
        y0, y1, z0, z1 = d['y0'] + 0.006, d['y1'] - 0.006, d['z0'] + 0.006, self.z_top(d['y1'])
        xo, xi = CW, CW - 0.05
        zt0, zt1 = self.z_top(y0), self.z_top(y1)
        face(D, [(xo, y0, z0), (xo, y1, z0), (xo, y1, zt1), (xo, y0, zt0)], PZ, (1, 0, 0))
        face(D, [(xi, y0, z0), (xi, y1, z0), (xi, y1, zt1), (xi, y0, zt0)], Z_CARD, (-1, 0, 0))
        face(D, [(xi, y0, z0), (xo, y0, z0), (xo, y0, zt0), (xi, y0, zt0)], Z_UNDER, (0, -1, 0))
        face(D, [(xi, y1, z0), (xo, y1, z0), (xo, y1, zt1), (xi, y1, zt1)], Z_UNDER, (0, 1, 0))
        face(D, [(xi, y0, z0), (xo, y0, z0), (xo, y1, z0), (xi, y1, z0)], Z_UNDER, (0, 0, -1))
        face(D, [(xi, y0, zt0), (xo, y0, zt0), (xo, y1, zt1), (xi, y1, zt1)], PZ, (0, 0, 1))
        P = lambda y, t, inset=0.0: self.P(y, t, 1, inset)
        pil = S['pillars']
        yA0, yA1 = S['YWS'] + 0.07, S['YRF'] + 0.06
        D.strip([P(yA0, 0.0), P(yA1, 0.985)], Vector((1, 0, 0.3)), 0.035, 0.03, PZ)
        D.strip([P(yA1, 0.985), P(pil[0][2] - 0.01, 0.985)], Vector((1, 0, 0.3)), 0.035, 0.03, PZ)
        D.strip([P(pil[0][2] - 0.015, 0.985), P(pil[0][0] - 0.015, 0.0)], Vector((1, 0, 0.3)), 0.035, 0.03, PZ)
        D.box(xi + 0.01, xo + 0.008, y0, y1, S['ZB'] - 0.012, S['ZB'] + 0.012, Z_RUBBER)
        if not broken_glass:
            G = reg(nm + '_Glass', 'glass', n)
            pts = [P(yA0 + 0.03, 0.05, 0.012), P(pil[0][0] - 0.035, 0.05, 0.012), P(pil[0][2] - 0.035, 0.96, 0.012),
                   P(yA1 + 0.03, 0.96, 0.012)]
            face(G, pts, ZERO, (1, 0, 0.3))
            face(G, list(reversed(pts)), ZERO, (-1, 0, -0.3))
            part(nm + '_Glass', 'static', (CW - 0.03, (yA0 + pil[0][0]) / 2, S['ZB'] + 0.25), parent=nm,
                 note='the door\'s window (glass material)')
        hz = S['ZB'] - 0.12
        D.box(xo, xo + 0.018, y1 - 0.18, y1 - 0.04, hz, hz + 0.03, Z_CHROME)               # the outside handle
        D.box(xi - 0.03, xi, y0 + 0.30, y0 + 0.55, hz - 0.14, hz - 0.10, Z_CBLACK)         # the pull
        D.box(xi - 0.012, xi, y1 - 0.30, y1 - 0.20, hz - 0.06, hz - 0.02, Z_CHROME)        # the inside lever
        VM.rbox(D, (xo + 0.11, S['YWS'] + 0.06, S['ZB'] + 0.09), (0.16, 0.05, 0.10), Z_CBLACK, r=0.012, ch=0.006, axis='y')
        D.box(xo, xo + 0.05, S['YWS'] + 0.045, S['YWS'] + 0.075, S['ZB'] + 0.06, S['ZB'] + 0.08, Z_CBLACK)
        if n == 'ShiftCar':                                                         # the station's marking (panel), both sides
            mk = reg('ShiftCar_DoorMark', 'panel', n, merge=nm)
            c = Vector((xo + 0.002, (y0 + y1) / 2, (z0 + zt0) / 2 + 0.06))
            mk.quad_uv(c, X, 0.62, 0.22, uv('shift_door'))
            mr = reg('ShiftCar_DoorMarkR', 'panel', n, merge=n)
            mr.quad_uv(Vector((-xo - 0.002, (y0 + y1) / 2, (z0 + zt0) / 2 + 0.06)), -X, 0.62, 0.22, uv('shift_door'))
        piv = Vector((CW + 0.01, d['y0'] + 0.02, (z0 + zt0) / 2))
        part(nm, 'hinge', piv, (0, 0, -1), (0, 72), parent=n, states=['shut', 'open'],
             note='the driver\'s door (front left, +x): hinge at its front edge, opens outward (+) to 72 deg; the window '
                  'and the mirror move with it' + (' - its window is broken (no glass)' if broken_glass else ''))
        socket(f'Hand_{n}Door_Out', (xo + 0.05, y1 - 0.11, hz + 0.015), 'hand', parent=nm, note='the outside handle')
        socket(f'Hand_{n}Door_In', (xi - 0.06, y1 - 0.25, hz - 0.04), 'hand', parent=nm, note='the inside lever')
        BOXES.append((n + 'Door', nm, (xi, xo, d['y0'], d['y1'], d['z0'], S['ZR']), None))
        self.door_name = nm

    def interior(self):
        S, k = self.S, self.k
        CW, fz, yws = S['CW'], S['floor'], S['YWS']
        xi = CW - 0.05
        ybk = S['pillars'][-1][0] if S['rear'] == 'saloon' else S['YR'] - 0.05
        face(k, [(-xi, yws, fz), (xi, yws, fz), (xi, ybk, fz), (-xi, ybk, fz)], Z_CARPET, (0, 0, 1))
        face(k, [(-xi, yws, fz), (xi, yws, fz), (xi, yws, S['ZB']), (-xi, yws, S['ZB'])], Z_CARPET, (0, 1, 0))
        for s in (-1, 1):
            segs = [(yws, ybk)] if s < 0 else [(yws, S['door']['y0']), (S['door']['y1'], ybk)]
            for ya, yb in segs:
                face(k, [(s * xi, ya, fz), (s * xi, yb, fz), (s * xi, yb, S['ZB'] - 0.005), (s * xi, ya, S['ZB'] - 0.005)], Z_CARD, (-s, 0, 0))
        if S['rear'] == 'saloon':                                                  # the bulkhead behind the rear bench
            face(k, [(-xi, ybk, fz), (xi, ybk, fz), (xi, ybk, S['ZB'] - 0.02), (-xi, ybk, S['ZB'] - 0.02)], Z_CARD, (0, -1, 0))
        else:                                                                       # the load floor (ribbed)
            face(k, [(-xi, S['seat_rows'][1] + 0.45, fz + 0.01), (xi, S['seat_rows'][1] + 0.45, fz + 0.01), (xi, ybk, fz + 0.01),
                     (-xi, ybk, fz + 0.01)], Z_CARGO, (0, 0, 1))
        dz = S['ZB'] - 0.89                                                          # the start car's dash heights, lifted
        k.box(-xi, xi, yws, yws + 0.30, 0.60 + dz, 0.86 + dz, Z_DASH)
        k.box(0.16, 0.60, yws + 0.26, yws + 0.36, 0.72 + dz, 0.88 + dz, Z_DASH)
        face(k, [(0.20, yws + 0.361, 0.74 + dz), (0.56, yws + 0.361, 0.74 + dz), (0.56, yws + 0.361, 0.85 + dz),
                 (0.20, yws + 0.361, 0.85 + dz)], Z_GAUGE, (0, 1, 0))
        k.box(-0.10, 0.10, yws + 0.30, yws + 0.62, fz, 0.62 + dz, Z_DASH)
        sc = Vector((0.38, yws + 0.46, 0.80 + dz))
        ax = Vector((0, 0.82, 0.57)).normalized()
        k.cyl(sc - ax * 0.30, sc - ax * 0.02, 0.028, Z_CBLACK, 8)
        e1 = Vector((1, 0, 0))
        e2 = ax.cross(e1).normalized()
        k.tube([sc + (e1 * math.cos(TAU * i / 16) + e2 * math.sin(TAU * i / 16)) * 0.19 for i in range(17)], 0.016, Z_CBLACK, 6,
               caps=False)
        for a in (0, math.pi, -math.pi / 2):
            k.cyl(sc, sc + (e1 * math.cos(a) + e2 * math.sin(a)) * 0.18, 0.012, Z_CBLACK, 5)
        k.cyl(sc - ax * 0.03, sc + ax * 0.03, 0.05, Z_CBLACK, 8)
        k.cyl(Vector((0.0, yws + 0.70, fz + 0.28)), Vector((0.0, yws + 0.66, fz + 0.46)), 0.008, Z_CHROME, 5)
        k.box(-0.025, 0.025, yws + 0.635, yws + 0.685, fz + 0.45, fz + 0.50, Z_CBLACK)
        for xp in (0.26, 0.38, 0.50):
            k.box(xp - 0.035, xp + 0.035, yws + 0.12, yws + 0.15, fz + 0.06, fz + 0.14, Z_CBLACK)
        y1r, y2r = S['seat_rows']
        sz = fz + 0.13
        for xc in (-0.38, 0.38):
            VM.rbox(k, (xc, y1r, sz), (0.48, 0.50, 0.12), Z_SEAT, r=0.03, ch=0.015, axis='z')
            k.box(xc - 0.12, xc + 0.12, y1r - 0.20, y1r + 0.20, fz, sz - 0.06, Z_CBLACK)
            VM.obox(k, Vector((xc, y1r + 0.28, sz + 0.31)), (0.47, 0.11, 0.60), Z_SEAT, Matrix.Rotation(math.radians(-12), 3, 'X'))
            VM.rbox(k, (xc, y1r + 0.35, sz + 0.68), (0.26, 0.09, 0.17), Z_SEAT, r=0.03, ch=0.012, axis='y')
        if S['bench']:
            VM.rbox(k, (0.0, y2r, sz - 0.03), (1.52, 0.44, 0.13), Z_SEAT, r=0.03, ch=0.015, axis='z')
            VM.obox(k, Vector((0.0, y2r + 0.20, sz + 0.31)), (1.52, 0.10, 0.56), Z_SEAT, Matrix.Rotation(math.radians(-8), 3, 'X'))
            k.box(-0.72, 0.72, y2r - 0.20, y2r + 0.20, fz, sz - 0.10, Z_CARD)

    def tyre(self, c, axis, flat=0.0, soft=0.0):
        S, k = self.S, self.k
        r, w = S['RW'], S['RWID']
        ax = Vector(axis).normalized()
        hw = w / 2
        prof = [(-hw, r * 0.62), (-hw * 1.05, r * 0.78), (-hw * 0.95, r * 0.93), (-hw * 0.6, r), (hw * 0.6, r), (hw * 0.95, r * 0.93),
                (hw * 1.05, r * 0.78), (hw, r * 0.62)]
        n0 = len(k.bm.verts)
        k.lathe(c, ax, prof, Z_TYRE, 16, cap0=False, cap1=False)
        k.lathe(c + ax * (hw * 0.55), ax, [(0.0, r * 0.62), (0.01, r * 0.50), (0.025, r * 0.30), (0.03, r * 0.20), (0.045, r * 0.19),
                                            (0.05, 0.0)], Z_RIM, 16, cap0=False, cap1=False)
        k.lathe(c - ax * (hw * 0.55), -ax, [(0.0, r * 0.62), (0.02, r * 0.35), (0.03, 0.0)], Z_UNDER, 16, cap0=False, cap1=False)
        sq = flat or soft
        if sq:
            k.bm.verts.ensure_lookup_table()
            for v in k.bm.verts[n0:]:
                if v.co.z < sq:
                    dd = (v.co - c).dot(ax)
                    bul = 0.5 * sq * (1 - max(v.co.z, 0) / sq)
                    v.co += ax * (math.copysign(bul, dd) if abs(dd) > 0.01 else 0.0)
                    v.co.z = max(v.co.z, 0.0)

    def hub(self, c, axis):
        """a wheel gone: the brake disc and the hub with its studs, resting on the ground"""
        k = self.k
        ax = Vector(axis).normalized()
        k.lathe(c - ax * 0.02, ax, [(0.0, 0.13), (0.024, 0.13)], Z_DISC, 16, cap0=True, cap1=True)
        k.lathe(c + ax * 0.004, ax, [(0.0, 0.075), (0.05, 0.065), (0.06, 0.03)], Z_DISC, 10, cap0=False, cap1=True)
        for i in range(4):
            a = TAU * i / 4
            _, s_, w_ = axes(ax, Z)
            p = c + ax * 0.004 + (s_ * math.cos(a) + w_ * math.sin(a)) * 0.05
            k.cyl(p, p + ax * 0.035, 0.007, Z_DISC, 5)

    def snow(self, decks, name=None, parent=None, note=None):
        """snow lying on the car: slabs over the roof, the hood and the given decks; (x0, x1, y0, y1, z0, z1, thick)"""
        n = self.n
        name = name or n + '_Snow'
        k = reg(name, 'World', n)
        for i, (x0, x1, y0, y1, z0, z1, th) in enumerate(decks):
            nx_, ny_ = 6, max(3, int((y1 - y0) / 0.35) + 1)
            grid = []
            for j in range(ny_ + 1):
                row = []
                for ii in range(nx_ + 1):
                    u, v = ii / nx_, j / ny_
                    x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v
                    zb = z0 + (z1 - z0) * v
                    edge = min(u, 1 - u, v, 1 - v)
                    t = th * min(1.0, edge * 6.0) ** 0.6 * (0.85 + 0.3 * hsh(i * 97 + j * 13 + ii, 5))
                    row.append(Vector((x, y, zb + max(t, 0.004))))
                grid.append(row)
            for j in range(ny_):
                for ii in range(nx_):
                    face(k, [grid[j][ii], grid[j][ii + 1], grid[j + 1][ii + 1], grid[j + 1][ii]], Z_SNOW, (0, 0, 1))
            ring = [grid[0][ii] for ii in range(nx_ + 1)] + [grid[j][nx_] for j in range(1, ny_ + 1)] + \
                   [grid[ny_][ii] for ii in range(nx_ - 1, -1, -1)] + [grid[j][0] for j in range(ny_ - 1, 0, -1)]
            for a, b in zip(ring, ring[1:] + ring[:1]):                            # the slab's edge down to the surface
                a0, b0 = Vector((a.x, a.y, a.z - 0.006)), Vector((b.x, b.y, b.z - 0.006))
                mid = (a + b) / 2
                cen = Vector(((x0 + x1) / 2, (y0 + y1) / 2, mid.z))
                face(k, [a0, b0, b, a], Z_SNOW, mid - cen)
        part(name, 'static', (0, 0, self.S['ZROOF']) if parent is None else (0, self.S.get('YDECK', 0), self.S.get('ZDECK', 0)),
             parent=parent or n, states=['none', 'snowed'],
             note=note or 'the snow on the car (roof, hood, decks): a separate part - show it after a snowfall, the paint under it '
                          'is clean')


def build_shift():
    S = SHIFT
    c = Car(S)
    c.body()
    c.glasshouse()
    c.door()
    c.interior()
    k, n = c.k, c.n
    CW, yr = S['CW'], S['YR']
    # the side-hinged rear door: its skin, the window, the spare wheel on its carrier; hinge on the right (-x)
    T = reg('IX_ShiftCarRearDoor', 'World', n)
    x0, x1, z0, z1 = -0.795, 0.795, S['ZRB'] + 0.215, S['ZR'] - 0.02
    yo = yr + 0.004
    box6(T, (x0, yr - 0.045, z0), (x1, yo, S['ZBR'] + 0.02), {'*': S['paint'], '-y': Z_CARD})
    for (a, b) in ((x0, x0 + 0.07), (x1 - 0.07, x1)):                                # the window frame
        box6(T, (a, yr - 0.045, S['ZBR'] + 0.02), (b, yo, z1), S['paint'])
    box6(T, (x0 + 0.07, yr - 0.045, z1 - 0.07), (x1 - 0.07, yo, z1), S['paint'])
    TG = reg('IX_ShiftCarRearDoor_Glass', 'glass', n)
    pts = [Vector((x0 + 0.07, yr - 0.02, S['ZBR'] + 0.02)), Vector((x1 - 0.07, yr - 0.02, S['ZBR'] + 0.02)),
           Vector((x1 - 0.07, yr - 0.02, z1 - 0.07)), Vector((x0 + 0.07, yr - 0.02, z1 - 0.07))]
    face(TG, pts, ZERO, (0, 1, 0))
    face(TG, list(reversed(pts)), ZERO, (0, -1, 0))
    T.box(0.55, 0.70, yo, yo + 0.025, 0.90, 0.93, Z_CHROME)                           # the handle
    sw = Vector((0.0, yo + 0.13, 1.16))                                              # the spare wheel on its carrier
    T.cyl(Vector((0.0, yo, 1.16)), sw - Y * 0.02, 0.05, Z_CBLACK, 8)
    for i, a in enumerate((0.3, 2.4, 4.5)):
        T.box_m(Vector((0.17 * math.cos(a), yo + 0.01, 1.16 + 0.17 * math.sin(a))), (0.05, 0.02, 0.05), Z_CBLACK)
    hw, r_ = S['RWID'] / 2, S['RW']
    prof = [(-hw, r_ * 0.62), (-hw * 1.05, r_ * 0.78), (-hw * 0.95, r_ * 0.93), (-hw * 0.6, r_), (hw * 0.6, r_), (hw * 0.95, r_ * 0.93),
            (hw * 1.05, r_ * 0.78), (hw, r_ * 0.62)]
    T.lathe(sw, Y, prof, Z_TYRE, 16, cap0=False, cap1=False)
    T.lathe(sw + Y * (hw * 0.55), Y, [(0.0, r_ * 0.62), (0.01, r_ * 0.5), (0.03, r_ * 0.2), (0.05, 0.0)], Z_RIM, 16, cap0=False, cap1=False)
    T.lathe(sw - Y * (hw * 0.55), -Y, [(0.0, r_ * 0.62), (0.03, 0.0)], Z_RIM, 16, cap0=False, cap1=False)
    for zz in (z0 + 0.15, z1 - 0.18):                                                # the hinges (right side)
        T.cyl(Vector((x0 - 0.02, yo + 0.01, zz - 0.06)), Vector((x0 - 0.02, yo + 0.01, zz + 0.06)), 0.016, Z_CBLACK, 6)
    part('IX_ShiftCarRearDoor', 'hinge', (x0 - 0.02, yo + 0.01, (z0 + z1) / 2), (0, 0, 1), (0, 100), parent=n,
         states=['shut', 'open'],
         note='the rear door, side-hinged on the right (-x), opens outward (+) to 100 deg; the spare wheel rides on it')
    part('IX_ShiftCarRearDoor_Glass', 'static', (0, yr - 0.02, (S['ZBR'] + z1) / 2), parent='IX_ShiftCarRearDoor',
         note='the rear door\'s window')
    socket('Hand_ShiftCarRearDoor', (0.62, yo + 0.04, 0.915), 'hand', parent='IX_ShiftCarRearDoor', note='the handle')
    BOXES.append(('ShiftCarRearDoor', 'IX_ShiftCarRearDoor', (x0, x1, yr - 0.05, yr + 0.30, z0, z1), None))
    # the roof rack: two rails on six feet, five cross bars
    for s in (-1, 1):
        k.box(*sorted((s * 0.70, s * 0.74)), S['YRF'] + 0.15, S['YRR'] - 0.10, S['ZROOF'] + 0.09, S['ZROOF'] + 0.12, Z_RACK)
        for yy in (S['YRF'] + 0.18, (S['YRF'] + S['YRR']) / 2, S['YRR'] - 0.13):
            k.box(*sorted((s * 0.69, s * 0.75)), yy - 0.03, yy + 0.03, S['ZROOF'], S['ZROOF'] + 0.09, Z_RACK)
    for i in range(5):
        yy = S['YRF'] + 0.30 + i * (S['YRR'] - S['YRF'] - 0.55) / 4
        k.box(-0.70, 0.70, yy - 0.015, yy + 0.015, S['ZROOF'] + 0.095, S['ZROOF'] + 0.115, Z_RACK)
    for (x, y), soft in (((S['TRK'], S['YFA']), 0.0), ((-S['TRK'], S['YFA']), 0.0), ((S['TRK'], S['YRA']), 0.0),
                         ((-S['TRK'], S['YRA']), 0.05)):                             # the rear right is going soft
        c.tyre(Vector((x, y, S['RW'] - (0.02 if soft else 0.0))), (1 if x > 0 else -1, 0, 0), soft=soft)
    triangulate_ngons(k)
    c.snow([(-0.80, 0.80, S['YRF'] + 0.02, S['YRR'] - 0.02, S['ZROOF'] + 0.115, S['ZROOF'] + 0.115, 0.12),
            (-0.84, 0.84, S['YF'] + 0.04, S['YWS'] - 0.04, S['ZHF'] + 0.01, S['ZHW'] + 0.01, 0.07)])
    part(n, 'static', (0, 0, 0),
         note='the previous shift\'s car (root): an 80s off-roader without make or badges in the station\'s grey-green, '
              'RADIOOBSERVATORIUM HOHENMOOS on both front doors (panel decals); '
              'origin = the middle of its footprint on the ground; stands at forest_main\'s anchors/Car_Parked')
    socket('Seat_ShiftCar_Driver', (0.38, S['seat_rows'][0], S['floor'] + 0.20), 'seat', parent=n, note='the driver\'s seat')
    socket('Slot_ShiftCar_Load_1', (0.30, S['YR'] - 0.40, S['floor'] + 0.02), 'slot', parent=n, note='the load floor, left')
    socket('Slot_ShiftCar_Load_2', (-0.30, S['YR'] - 0.40, S['floor'] + 0.02), 'slot', parent=n, note='the load floor, right')
    socket('Slot_ShiftCar_Seat', (-0.38, S['seat_rows'][0], S['floor'] + 0.20), 'slot', parent=n, note='the passenger seat')
    BOXES.append(('ShiftCar', n, (-CW - 0.01, CW + 0.01, S['YF'] - 0.10, S['YR'] + 0.07, 0.20, S['ZROOF'] + 0.12), None))
    return c


def build_wreck():
    S = WRECK
    c = Car(S)
    c.body()
    c.glasshouse(broken=('WS', 'R1'))
    c.door(broken_glass=True)
    c.interior()
    k, n = c.k, c.n
    CW = S['CW']
    # the boot lid: the deck and the upper rear face, hinged at the deck's front edge
    B = reg('IX_WreckCarBoot', 'World', n)
    yd, zd, yr = S['YDECK'], S['ZDECK'], S['YR']
    zrt = S['ZDECK'] - 0.10
    face(B, [(-CW + 0.02, yd + 0.01, zd), (CW - 0.02, yd + 0.01, zd), (CW - 0.02, yr - 0.004, zd - 0.02), (-CW + 0.02, yr - 0.004, zd - 0.02)],
         S['paint'], (0, 0, 1))
    face(B, [(-CW + 0.02, yr, zrt + 0.004), (CW - 0.02, yr, zrt + 0.004), (CW - 0.02, yr, zd - 0.02), (-CW + 0.02, yr, zd - 0.02)],
         S['paint'], (0, 1, 0))
    face(B, [(-CW + 0.04, yd + 0.03, zd - 0.03), (CW - 0.04, yd + 0.03, zd - 0.03), (CW - 0.04, yr - 0.03, zd - 0.05),
             (-CW + 0.04, yr - 0.03, zd - 0.05)], Z_UNDER, (0, 0, -1))
    B.box(-0.10, 0.10, yr, yr + 0.02, zrt + 0.02, zrt + 0.05, Z_CHROME)                    # the lock
    # the boot: its floor and walls (the lid opens onto it)
    face(k, [(-CW + 0.05, yd, S['ZRB'] + 0.10), (CW - 0.05, yd, S['ZRB'] + 0.10), (CW - 0.05, yr - 0.02, S['ZRB'] + 0.10),
             (-CW + 0.05, yr - 0.02, S['ZRB'] + 0.10)], Z_CARGO, (0, 0, 1))
    for s in (-1, 1):
        face(k, [(s * (CW - 0.05), yd, S['ZRB'] + 0.10), (s * (CW - 0.05), yr - 0.02, S['ZRB'] + 0.10), (s * (CW - 0.05), yr - 0.02, zrt),
                 (s * (CW - 0.05), yd, zd - 0.02)], Z_CARD, (-s, 0, 0))
    face(k, [(-CW + 0.05, yd, S['ZRB'] + 0.10), (CW - 0.05, yd, S['ZRB'] + 0.10), (CW - 0.05, yd, zd - 0.02), (-CW + 0.05, yd, zd - 0.02)],
         Z_CARD, (0, 1, 0))
    face(k, [(-CW + 0.05, yr - 0.02, S['ZRB'] + 0.10), (CW - 0.05, yr - 0.02, S['ZRB'] + 0.10), (CW - 0.05, yr - 0.02, zrt),
             (-CW + 0.05, yr - 0.02, zrt)], Z_CARD, (0, -1, 0))
    for s in (-1, 1):                                                                 # the deck's side strips
        face(k, [(s * (CW - 0.02), yd, zd), (s * CW, yd, zd), (s * CW, yr, zd - 0.02), (s * (CW - 0.02), yr, zd - 0.02)], S['paint'], (0, 0, 1))
    piv = Vector((0.0, yd + 0.01, zd + 0.005))
    part('IX_WreckCarBoot', 'hinge', piv, (1, 0, 0), (0, 75), rest=12.0, parent=n, states=['shut', 'ajar', 'open'],
         note='the boot lid: hinged at its front edge (axis +x), opens up (+) to 75 deg; it stands ajar (12 deg) - the lock '
              'is broken; QUESTIONS_HUT_2: something may lie in the boot (Slot_WreckCar_Boot)')
    socket('Hand_WreckCarBoot', (0.0, yr + 0.03, zrt + 0.035), 'hand', parent='IX_WreckCarBoot', note='lift the lid')
    socket('Slot_WreckCar_Boot', (0.15, (yd + yr) / 2, S['ZRB'] + 0.11), 'slot', parent=n, note='the boot floor')
    socket('Slot_WreckCar_Seat', (-0.38, S['seat_rows'][0], S['floor'] + 0.20), 'slot', parent=n, note='the passenger seat')
    BOXES.append(('WreckCarBoot', 'IX_WreckCarBoot', (-CW + 0.02, CW - 0.02, yd, yr, zrt, zd + 0.01), None))
    # the wheels: the front right gone (the hub on the ground), the others soft
    for (x, y), what in (((CW - 0.14, S['YFA']), 'soft'), ((-(CW - 0.14), S['YFA']), 'hub'), ((CW - 0.14, S['YRA']), 'soft'),
                         ((-(CW - 0.14), S['YRA']), 'flat')):
        ax = (1 if x > 0 else -1, 0, 0)
        if what == 'hub':
            c.hub(Vector((x, y, 0.13)), ax)
        else:
            c.tyre(Vector((x, y, S['RW'] - (0.06 if what == 'flat' else 0.02))), ax, soft=0.09 if what == 'flat' else 0.05)
    triangulate_ngons(k)
    # the body leans to the front right corner (it rests on the disc): everything but the wheels turns
    drop = S['RW'] - 0.13 + 0.02
    roll = -math.degrees(math.atan(drop / 2 / (2 * S['TRK'])))
    pitch = math.degrees(math.atan(drop / 2 / (S['YRA'] - S['YFA'])))
    pv = Vector((S['TRK'], S['YRA'], S['RW']))
    R = (Matrix.Translation(pv) @ Matrix.Rotation(math.radians(pitch), 4, 'X') @ Matrix.Rotation(math.radians(roll), 4, 'Y') @
         Matrix.Translation(-pv))
    c.lean = (R, roll, pitch)
    c.snow([(-0.66, 0.66, S['YRF'] + 0.03, S['YRR'] - 0.03, S['ZROOF'] + 0.002, S['ZROOF'] + 0.002, 0.10),
            (-0.80, 0.80, S['YF'] + 0.05, S['YWS'] - 0.05, S['ZHF'] + 0.012, S['ZHW'] + 0.012, 0.07)])
    c.snow([(-0.80, 0.80, yd + 0.04, yr - 0.06, zd + 0.002, zd - 0.018, 0.07)], name='WreckCar_BootSnow',
           parent='IX_WreckCarBoot', note='the snow on the boot lid: moves with it; show / hide with WreckCar_Snow')
    part(n, 'static', (0, 0, 0),
         note='the second abandoned car (root): an 80s saloon without make or badges, faded blue, rusted; the front right '
              f'wheel gone - it rests on the brake disc and leans ({roll:.1f} deg roll, {pitch:.1f} deg pitch); the windscreen '
              'cracked (WreckCar_Windscreen), the driver\'s and the rear right windows broken; origin = the middle of its '
              'footprint on the ground; no anchor on the map yet')
    BOXES.append(('WreckCar', n, (-CW - 0.01, CW + 0.01, S['YF'] - 0.10, S['YR'] + 0.07, 0.15, S['ZROOF']), None))
    return c


def apply_lean(c):
    """turn the wreck's body (not its wheels: they were added before the lean in build order - here: everything that is
    not a wheel lathe) - done on the whole KBs, then the wheels are rebuilt in place; simpler: lean all but the wheel faces"""
    R, roll, pitch = c.lean
    n = c.n
    names = [nm for nm in KBS if ROOT_OF.get(nm) == n]
    for nm in names:
        k = KBS[nm]
        if nm == n:
            zl = k.zl
            wheel = {Z_TYRE, Z_RIM, Z_DISC}
            vs = set()
            keep = set()
            for f in k.bm.faces:
                if round(f[zl]) in wheel:
                    keep.update(f.verts)
            for v in k.bm.verts:
                if v not in keep:
                    vs.add(v)
            bmesh.ops.transform(k.bm, matrix=R, verts=list(vs))
        else:
            transform_kb(k, R)
    for pn, p in CONTRACT['parts'].items():
        if ROOT_OF.get(pn) == n and pn != n:
            p['pivot'] = K.r4(R @ Vector(p['pivot']))
            if p.get('axis'):
                p['axis'] = K.r4((R.to_3x3() @ Vector(p['axis'])).normalized())
    for sn, s in CONTRACT['sockets'].items():
        par = s.get('parent')
        if par and (ROOT_OF.get(par) == n) and sn.startswith(('Hand_', 'Slot_WreckCar', 'Seat_WreckCar')):
            s['pos'] = K.r4(R @ Vector(s['pos']))
    for i, (bn, par, (x0, x1, y0, y1, z0, z1), rot) in enumerate(BOXES):          # the colliders' centres follow (still axis-aligned)
        if ROOT_OF.get(par) == n and par != n:
            c = R @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
            hx, hy, hz = (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2
            BOXES[i] = (bn, par, (c.x - hx, c.x + hx, c.y - hy, c.y + hy, c.z - hz, c.z + hz), rot)


# ================================================================ ForesterCave
CAVE = {}


def cave_sample(P):
    """the cavity's distance (negative inside the hollow) at points P (n, 3), trilinear on the grid of world_cave_sdf"""
    from scipy.ndimage import map_coordinates
    d = CAVE['npz']
    g = (np.asarray(P, np.float64) - d['lo'][None]) / float(d['vox'])
    return map_coordinates(d['cav'], g.T, order=1, mode='nearest')


def build_cave_shell():
    d = np.load(CAVE_NPZ)
    CAVE['npz'] = {k_: d[k_] for k_ in d.files}
    v, f = d['verts'], d['faces']
    me = bpy.data.meshes.new('cave_tmp')
    me.from_pydata(v.astype(np.float64).tolist(), [], f.tolist())
    me.update()
    ob = bpy.data.objects.new('cave_tmp', me)
    bpy.context.scene.collection.objects.link(ob)
    out = {}
    for tag, target in (('shell', 5200), ('col', 900)):
        dm = ob.modifiers.new('dec', 'DECIMATE')
        dm.decimate_type, dm.ratio, dm.use_collapse_triangulate = 'COLLAPSE', target / len(f), True
        dg = bpy.context.evaluated_depsgraph_get()
        m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        out[tag] = m2
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    # the shell into its KB with zones: inside (near the hollow), the floor, outside, buried
    k = reg('ForesterCave', 'Cave', 'ForesterCave')
    m2 = out['shell']
    V = np.array([vv.co[:] for vv in m2.vertices])
    vs = [k.bm.verts.new(Vector(p)) for p in V]
    cents = np.array([np.mean([V[i] for i in pl.vertices], axis=0) for pl in m2.polygons])
    nrm = np.array([pl.normal[:] for pl in m2.polygons])
    dc = cave_sample(cents)
    for pl, c_, n_, dd in zip(m2.polygons, cents, nrm, dc):
        if dd < 0.32 and c_[1] > -1.0:
            zone = Z_CFLOOR if (n_[2] > 0.80 and c_[2] < 0.12) else Z_ROCKIN
        elif all(V[i][2] < -0.04 for i in pl.vertices):
            zone = Z_ROCKD
        else:
            zone = Z_ROCK
        try:
            f_ = k._f([vs[i] for i in pl.vertices], zone)
            f_.smooth = True                                            # smooth: the AO and the light follow the rock, not its facets
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(k.bm, faces=k.bm.faces)
    CAVE['bvh'] = BVHTree.FromBMesh(k.bm)
    # the collision copy (no zones; a MeshCollider in Unity)
    kc = reg('COLM_Cave', 'none', 'ForesterCave')
    V2 = [vv.co.copy() for vv in out['col'].vertices]
    vs2 = [kc.bm.verts.new(p) for p in V2]
    for pl in out['col'].polygons:
        try:
            kc._f([vs2[i] for i in pl.vertices], 0.0)
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(kc.bm, faces=kc.bm.faces)
    for m_ in out.values():
        bpy.data.meshes.remove(m_)


def wall(p, d):
    """the wall point hit from p along d inside the cave: (point, normal into the hollow)"""
    hit = CAVE['bvh'].ray_cast(Vector(p), Vector(d).normalized(), 8.0)
    assert hit[0] is not None, f'no wall from {p} along {d}'
    loc, nrm = hit[0], hit[1]
    if nrm.dot(Vector(d)) > 0:
        nrm = -nrm
    return loc, nrm


def ground(x, y, z0=0.6):
    """the floor height under (x, y) inside the cave"""
    hit = CAVE['bvh'].ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 2.0)
    return hit[0].z if hit[0] is not None else 0.0


def blanket(k, c, size, yaw, seed, zone, sag=0.04, nx=6, ny=5, fold=0.0):
    """a draped cloth: a grid over the box footprint with noise, its edges hanging down by `sag`"""
    cx, cy, cz = c
    sx, sy = size
    R = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx - 0.5, j / ny - 0.5
            edge = max(abs(u), abs(v)) * 2
            h = -sag * edge ** 3 + 0.015 * (hsh(i * 31 + j * 7, seed) - 0.5) + fold * math.exp(-((v - 0.2) / 0.12) ** 2)
            row.append(Vector((cx, cy, cz)) + R @ Vector((u * sx, v * sy, h)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            face(k, [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]], zone, (0, 0, 1))
            face(k, [grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]], zone, (0, 0, -1))


def build_cave_props():
    k = reg('ForesterCave_Props', 'Cave', 'ForesterCave')
    # the sleeping place in the niche: a mat of spruce boughs, two army blankets, a rolled blanket for a pillow
    bx, by = -1.75, 4.30
    gz = ground(bx, by)
    for i in range(9):
        a = math.radians(-35 + 70 * hsh(i, 1) + (90 if i % 3 == 0 else 0))
        L = 0.9 + 0.5 * hsh(i, 2)
        c = Vector((bx - 0.55 + 1.1 * hsh(i, 3), by - 0.35 + 0.7 * hsh(i, 4), gz + 0.03 + 0.02 * (i % 3)))
        dd = Vector((math.cos(a), math.sin(a), 0.0))
        side = Vector((-dd.y, dd.x, 0.0))
        w = 0.28 + 0.12 * hsh(i, 5)
        pts = [c - dd * L / 2, c - dd * L / 2 + side * w * 0.2, c + side * w * 0.5, c + dd * L / 2, c - side * w * 0.5,
               c - dd * L / 2 - side * w * 0.2]
        face(k, [p + Z * (0.03 if j in (2, 4) else 0.0) for j, p in enumerate(pts)], Z_BOUGH, (0, 0, 1))
        face(k, [p + Z * (0.03 if j in (2, 4) else 0.0) for j, p in reversed(list(enumerate(pts)))], Z_BOUGH, (0, 0, -1))
    blanket(k, (bx + 0.05, by - 0.05, gz + 0.12), (1.85, 0.95), 8.0, 11, Z_BLANKET, sag=0.10, fold=0.05)
    blanket(k, (bx + 0.25, by + 0.05, gz + 0.16), (1.10, 0.85), -14.0, 12, Z_BLANKET, sag=0.08, fold=0.06)
    roll = Vector((bx - 0.80, by + 0.05, gz + 0.18))
    k.cyl(roll - Vector((0.0, 0.32, 0.0)), roll + Vector((0.0, 0.32, 0.0)), 0.09, Z_BLANKET, 8)
    socket('Sleep_Forester', (bx + 0.05, by - 0.05, gz + 0.22), 'pose', parent='ForesterCave',
           note='where the Forester lies by day (head at -x, on the rolled blanket), curled under the blankets', dir=(1, 0, 0))
    # the candle stubs on a flat stone by the bed (their flames: sockets + lights, off by day)
    sx_, sy_ = -0.70, 5.10
    sgz = ground(sx_, sy_)
    VM.rbox(k, (sx_, sy_, sgz + 0.10), (0.55, 0.38, 0.20), Z_STONE, r=0.05, ch=0.02, axis='z')
    tz = sgz + 0.20
    for i, (dx, dy, hh) in enumerate(((-0.16, -0.06, 0.09), (-0.03, 0.08, 0.05), (0.10, -0.04, 0.12), (0.18, 0.09, 0.04))):
        c = Vector((sx_ + dx, sy_ + dy, tz))
        k.lathe(c, Z, [(0.0, 0.05), (0.008, 0.035), (0.010, 0.0)], Z_WAX, 8, cap0=False, cap1=False)      # the puddle of wax
        k.cyl(c, c + Z * hh, 0.021, Z_CANDLE, 8)
        k.cyl(c + Z * hh, c + Z * (hh + 0.012), 0.0015, Z_RAG, 3)
        socket(f'Light_Candle_{i + 1}', c + Z * (hh + 0.03), 'light', parent='ForesterCave',
               note='a candle flame: point light (1.0, 0.62, 0.30), range 3 m, flicker; unlit by day')
        LIGHTS.append((f'Light_Candle_{i + 1}', 'ForesterCave', tuple(c + Z * (hh + 0.03)), None, 'point', (1.0, 0.62, 0.30), 3.0,
                       'flicker'))
    # the nail in the wall and the key's place on it (I1): on the right of the passage where it opens into the chamber
    p, n_ = wall((0.55, 2.55, 1.30), (1.0, -0.25, 0.0))
    k.cyl(p - n_ * 0.02, p + n_ * 0.055, 0.004, Z_NAIL, 5)
    k.cyl(p + n_ * 0.052, p + n_ * 0.058, 0.008, Z_NAIL, 6)
    socket('Slot_Key', p + n_ * 0.045 - Z * 0.012, 'slot', parent='ForesterCave',
           note='forest_gear\'s Item_Key_Stationsleiter hangs here on the nail by its ring (TASKS I1)', dir=tuple(n_))
    # the bow saw leaning on the passage wall, fresh sawdust under it (S5)
    p2, n2 = wall((0.10, 1.35, 0.55), (1.0, 0.0, 0.0))
    foot = Vector((p2.x - 0.12, p2.y, ground(p2.x - 0.12, p2.y) + 0.01))
    top = Vector((p2.x - 0.03, p2.y + 0.05, foot.z + 0.62))
    dd = (top - foot).normalized()
    t, s_, w_ = axes(dd, Y)
    bow = [foot, foot + dd * 0.05 + s_ * 0.22, foot + dd * 0.35 + s_ * 0.32, top + s_ * 0.22, top]
    k.tube(bow, 0.012, Z_SAWF, 6, caps=True)
    k.strip([foot + dd * 0.02, top - dd * 0.02], s_, 0.002, 0.03, Z_SAWB, caps=True)
    for i in range(14):                                                                   # the sawdust: a low pale heap
        a = TAU * i / 14
        rr = 0.12 + 0.10 * hsh(i, 21)
        c = foot + Vector((math.cos(a) * rr * 0.5 - 0.05, math.sin(a) * rr, 0.0))
        k.box_m(Vector((c.x, c.y, foot.z + 0.004)), (0.10, 0.09, 0.012), Z_SAWDUST,
                Matrix.Rotation(a, 3, 'Z'))
    VM.rbox(k, (foot.x - 0.06, foot.y + 0.02, foot.z + 0.02), (0.26, 0.30, 0.04), Z_SAWDUST, r=0.03, ch=0.01, axis='z')
    # the old shift's boots by the bed's foot: one standing, one on its side showing the sole (X11)
    for i, (x, y, yaw, side) in enumerate(((-0.55, 3.55, 20.0, False), (-0.30, 3.40, 70.0, True))):
        gz2 = ground(x, y)
        R = Matrix.Rotation(math.radians(yaw), 3, 'Z')
        if side:
            R = R @ Matrix.Rotation(math.radians(85), 3, 'Y')
        base = Vector((x, y, gz2 + (0.06 if side else 0.0)))
        k.box_m(base + R @ Vector((0.0, 0.0, 0.02)), (0.11, 0.30, 0.04), Z_SOLE, R)
        k.box_m(base + R @ Vector((0.0, 0.03, 0.12)), (0.10, 0.17, 0.17), Z_BOOT, R)
        k.box_m(base + R @ Vector((0.0, -0.08, 0.075)), (0.10, 0.11, 0.07), Z_BOOT, R)
    # the heap of stolen junk in the right-hand recess: tins, a bucket, a coil of wire, rags, bottles
    jx, jy = 1.55, 4.80
    gz3 = ground(jx, jy)
    for i in range(7):
        c = Vector((jx - 0.35 + 0.7 * hsh(i, 31), jy - 0.3 + 0.6 * hsh(i, 32), gz3))
        if i % 3 == 0:
            ax = Vector((math.cos(i), math.sin(i), 0.0))
            k.cyl(c + Z * 0.04 - ax * 0.055, c + Z * 0.04 + ax * 0.055, 0.04, Z_TIN, 8)
        else:
            k.cyl(c, c + Z * 0.11, 0.04, Z_TIN, 8)
    k.lathe(Vector((jx + 0.25, jy + 0.10, gz3)), Z, [(0.0, 0.11), (0.25, 0.14), (0.26, 0.145)], Z_BUCKET, 10, cap0=True, cap1=False)
    k.lathe(Vector((jx + 0.25, jy + 0.10, gz3 + 0.26)), Z, [(0.0, 0.14), (-0.22, 0.13)], Z_BUCKET, 10, cap0=False, cap1=False)
    coil = [Vector((jx - 0.30 + 0.13 * math.cos(a), jy + 0.25 + 0.13 * math.sin(a), gz3 + 0.012 + 0.004 * a)) for a in
            np.linspace(0, TAU * 3, 40)]
    k.tube(coil, 0.006, Z_WIRE, 4, caps=False)
    blanket(k, (jx + 0.05, jy - 0.15, gz3 + 0.05), (0.45, 0.35), 25.0, 33, Z_RAG, sag=0.04, nx=4, ny=3)
    for i in range(2):
        c = Vector((jx - 0.10 + 0.25 * i, jy + 0.40, gz3 + 0.035))
        ax = Vector((math.cos(1.1 + i), math.sin(1.1 + i), 0.0))
        k.lathe(c - ax * 0.12, ax, [(0.0, 0.035), (0.17, 0.035), (0.21, 0.012), (0.25, 0.012)], Z_BOTTLE, 8, cap0=True, cap1=True)
    # the newspaper (1991) on the floor by the bed (panel)
    nx_, ny_ = -1.10, 3.75
    pk = reg('ForesterCave_Paper', 'panel', 'ForesterCave', merge='ForesterCave_Props')
    pk.quad_uv(Vector((nx_, ny_, ground(nx_, ny_) + 0.012)), Z, 0.30, 0.40, uv('paper'), up=Vector((-0.3, 1.0, 0.0)))
    # the sockets for the stolen things (the game puts what the Forester took here) - on the floor round the chamber
    stash = [(1.25, 4.35), (1.85, 4.30), (1.95, 5.15), (1.10, 5.25), (0.45, 5.20), (-0.15, 5.35), (1.35, 3.40), (-0.95, 4.85)]
    for i, (x, y) in enumerate(stash):
        gz4 = ground(x, y)
        assert cave_sample(np.array([[x, y, gz4 + 0.4]]))[0] < -0.2, f'stash {i} not in the hollow'
        socket(f'Slot_Stash_{i + 1}', (x, y, gz4 + 0.005), 'slot', parent='ForesterCave',
               note='a stolen thing lies here (canister, battery, cassettes, torch, radio, a can of food ... - MONSTERS)')
    part('ForesterCave_Props', 'static', (0, 3.6, 0), parent='ForesterCave',
         note='the dressing: boughs, blankets, candles on their stone, the nail, the bow saw and the sawdust, the boots, the junk '
              'heap, the 1991 newspaper (panel)')


def build_cave():
    build_cave_shell()
    build_cave_props()
    part('ForesterCave', 'static', (0, 0, 0),
         note='the Forester\'s cave (root): a granite outcrop ~12 x 10 m, 5 m high; the passage (1.7 m wide, 1.9 m high) from '
              'the front (-y) into a chamber 5 x 4 m, 2.3 m high; origin = the floor in the mouth (z = 0 is the cave floor and '
              'the ground in front of it); the rock goes 0.6 m into the ground: set it into a slope, the mouth free')
    part('COLM_Cave', 'static', (0, 0, 0), parent='ForesterCave',
         note='the collision shell: a simplified copy of the rock (~900 tris) for a MeshCollider; not rendered')
    socket('Zone_CaveInside', (0.3, 3.4, 1.1), 'volume', parent='ForesterCave',
           note='a box 5.6 x 5.4 x 2.4 m round the chamber and the inner passage: inside the cave (ambience, no wind)',
           size=(5.6, 5.4, 2.4))
    socket('View_CaveMouth', (0.0, -2.5, 1.6), 'view', parent='ForesterCave', note='the first look into the mouth', dir=(0, 1, -0.1))


def build_world():
    build_barrel()
    sc = build_shift()
    wc = build_wreck()
    apply_lean(wc)
    build_cave()
    return sc, wc
