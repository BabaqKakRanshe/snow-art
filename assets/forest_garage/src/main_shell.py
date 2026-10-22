"""Main building — the shell (main_spec gives the measured layout): one object per room (R_<Room> = the room's light
zone: floor, ceiling, walls with their finishes and the inner reveals), the exterior envelope (BaseMain: board-formed
concrete facades over a dark plinth, the slab band, parapets with copings, the gravel roof, the stair tower and the
garage hall outside, the brick flue), the U-stair in the tower (concrete flights with sloped soffits, landings, nosings).
Doors, windows, shutters: main_open.py.  Furniture and equipment: main_rooms.py."""
import math
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, Z_GALV, Z_STEELBLK
from cont_kit import flat_wall, flat_h, _subtract, _split, _grid
import main_spec as S

# ---------------------------------------------------------------- zones (300..)
(Z_FACADE, Z_PLINTH, Z_BAND, Z_PARIN, Z_ROOF, Z_UPSTAND, Z_CONCIN, Z_PLASTER, Z_DADO, Z_STRIPE, Z_TILEW, Z_VENEERW,
 Z_CEIL, Z_CEILT, Z_FL_LINO, Z_FL_LINOG, Z_FL_CARPET, Z_FL_TILE, Z_FL_RAISED, Z_FL_BOARDS, Z_FL_CONC, Z_STAIR,
 Z_BASEB, Z_SILLIN, Z_BRICK, Z_CEILB, Z_SOFFIT, Z_REVEALX, Z_FL_GARAGE, Z_SLABEDGE) = range(300, 330)
FLOOR_ZONE = {'lino': Z_FL_LINO, 'lino_g': Z_FL_LINOG, 'carpet': Z_FL_CARPET, 'tile_f': Z_FL_TILE, 'tile_k': Z_FL_TILE,
              'tile_b': Z_FL_TILE, 'raised': Z_FL_RAISED, 'boards': Z_FL_BOARDS, 'conc': Z_FL_CONC, 'conc_g': Z_FL_GARAGE}
CEIL_ZONE = {'plaster': Z_CEIL, 'tiles': Z_CEILT, 'boards': Z_CEILB, 'conc': Z_CONCIN}
BASEB_H = 0.06                      # skirting
STRIPE = (0.05, 0.03)               # the corridors' 70s stripe: above the dado, three bands (orange, brown, olive) 3 cm each
EPS = 1e-4


def room_atlas(name):
    return 'Rm_' + name


def rkb(name):
    return kb('R_' + name, room_atlas(name))


def ext():
    return kb('BaseMain', 'MainExt')


# ---------------------------------------------------------------- openings
def openings():
    """every opening through a wall: dict(axis, a0, a1, u0, u1, z0, z1, kind, ref)"""
    out = []
    for name, d in S.DOORS.items():
        ax, a0, a1 = d['wall']
        o = dict(axis=ax, a0=a0, a1=a1, u0=d['u'][0], u1=d['u'][1], z0=d['z'][0], z1=d['z'][1], kind='door', ref=name)
        if d.get('niche'):
            R = S.ROOMS[d['room']]
            c = (R['y0'] + R['y1']) / 2 if ax == 'y' else (R['x0'] + R['x1']) / 2
            o['niche'] = dict(d['niche'], a=a1 if c > (a0 + a1) / 2 else a0)
        out.append(o)
    for w in S.WINDOWS:
        ax, a0, a1 = w['wall']
        out.append(dict(axis=ax, a0=a0, a1=a1, u0=w['u'][0], u1=w['u'][1], z0=w['z'][0], z1=w['z'][1], kind='window',
                        ref=w['name']))
    kp = S.KITCHEN_PASS
    out.append(dict(axis='y', a0=kp['wall'][1], a1=kp['wall'][2], u0=kp['u'][0], u1=kp['u'][1], z0=kp['z'][0], z1=kp['z'][1],
                    kind='pass', ref='Kueche_Pass'))
    g = S.GARAGE_GATE
    out.append(dict(axis='y', a0=-5.00, a1=-4.70, u0=g['u'][0], u1=g['u'][1], z0=g['z'][0], z1=g['z'][1], kind='gate',
                    ref=g['name']))
    return out


OPENINGS = openings()


def sides(R):
    """the four walls of a room: (key, axis, a (face plane), n_sign (into the room), u0, u1)"""
    return [('S', 'y', R['y0'], 1, R['x0'], R['x1']), ('N', 'y', R['y1'], -1, R['x0'], R['x1']),
            ('W', 'x', R['x0'], 1, R['y0'], R['y1']), ('E', 'x', R['x1'], -1, R['y0'], R['y1'])]


def holes_on(axis, a, n_sign, u0, u1, z0, z1):
    """openings in the wall plane `a` seen from the side the normal n_sign points to"""
    res = []
    for o in OPENINGS:
        if o['axis'] != axis:
            continue
        face_a = o['a1'] if n_sign > 0 else o['a0']
        if abs(face_a - a) > 1e-3:
            continue
        ou0, ou1, oz0, oz1 = o['u0'], o['u1'], o['z0'], o['z1']
        nic = o.get('niche')
        if nic and abs(nic['a'] - a) < 1e-3:                       # the room face: the niche's outline
            (ou0, ou1), (oz0, oz1) = nic['u'], nic['z']
        hu0, hu1, hz0, hz1 = max(ou0, u0), min(ou1, u1), max(oz0, z0), min(oz1, z1)
        if hu1 - hu0 > 0.01 and hz1 - hz0 > 0.01:
            res.append(dict(o, hu=(hu0, hu1), hz=(hz0, hz1), depth=o['a1'] - o['a0']))
    return res


# ---------------------------------------------------------------- the rooms
def wall_zone_fn(R):
    f, W = R['f'], R['walls']
    if W.get('bare'):
        return lambda z: Z_CONCIN
    if W.get('tile'):
        return lambda z: Z_TILEW if z < f + W['tile'] else Z_PLASTER
    if W.get('veneer'):
        return lambda z: Z_VENEERW if z < f + W['veneer'] else Z_PLASTER
    dado = W.get('dado', 0)
    if W.get('stripe'):
        s0 = f + dado + STRIPE[0]
        s1 = s0 + 3 * STRIPE[1]
        return lambda z: Z_DADO if z < f + dado else Z_STRIPE if s0 <= z < s1 else Z_PLASTER
    return lambda z: Z_DADO if z < f + dado else Z_PLASTER


def wall_cuts(R):
    f, W = R['f'], R['walls']
    cuts = [f + BASEB_H]
    for key in ('dado', 'tile', 'veneer'):
        if W.get(key):
            cuts.append(f + W[key])
    if W.get('stripe'):
        s0 = f + W['dado'] + STRIPE[0]
        cuts += [s0 + i * STRIPE[1] for i in range(4)]
    return cuts


NOTCHES = {'Heizung': [S.CHIMNEY], 'Leitstand': [S.CHIMNEY], 'Kueche': [S.CHIMNEY]}   # the flue in the rooms' NE corner


def room_shell(name):
    """floor, ceiling, walls (finish bands as zones), the inner reveals of the room's own windows (plaster, to the frame)
    and the skirting; the stair tower's walls and floor-to-floor landings are built by stair()"""
    R = dict(S.ROOMS[name])
    k = rkb(name)
    zf = wall_zone_fn(R)
    cuts = wall_cuts(R)
    notches = NOTCHES.get(name, [])
    xc = [c for n in notches for c in (n['x0'], n['x1'])]
    yc = [c for n in notches for c in (n['y0'], n['y1'])]

    def in_notch(x, y):
        return any(n['x0'] < x < n['x1'] and n['y0'] < y < n['y1'] for n in notches)

    # floor and ceiling, cells round the notches left out
    for z, sgn, zone in ((R['f'], 1, FLOOR_ZONE[R['floor']]), (R['c'], -1, CEIL_ZONE[R['ceil']])):
        if name == 'Treppenhaus' and sgn > 0:
            continue                                             # the tower's floors are the stair's landings
        xs = _grid({R['x0'], R['x1']} | set(c for c in xc if R['x0'] < c < R['x1']), 1.0)
        ys = _grid({R['y0'], R['y1']} | set(c for c in yc if R['y0'] < c < R['y1']), 1.0)
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                if in_notch((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2):
                    continue
                face(k, [(xs[i], ys[j], z), (xs[i + 1], ys[j], z), (xs[i + 1], ys[j + 1], z), (xs[i], ys[j + 1], z)], zone,
                     (0, 0, sgn))
    # walls
    for key, axis, a, ns, u0, u1 in sides(R):
        hs = holes_on(axis, a, ns, u0, u1, R['f'], R['c'])
        holes = [(h['hu'][0], h['hu'][1], h['hz'][0], h['hz'][1]) for h in hs]
        spans = [(u0, u1)]
        for n in notches:                                        # the notch takes a piece of the N / E wall
            nu = (n['x0'], n['x1']) if axis == 'y' else (n['y0'], n['y1'])
            na = n['y1'] if (axis == 'y' and ns < 0) else n['x1'] if (axis == 'x' and ns < 0) else None
            if na is not None and abs(na - a) < 1e-3:
                spans = [s for sp in spans for s in _subtract(sp, [nu])]
        for su0, su1 in spans:
            flat_wall(k, axis, a, ns, su0, su1, R['f'], R['c'], zf, holes=[h for h in holes if h[1] > su0 and h[0] < su1],
                      step=1.0, zcuts=cuts)
        # skirting along the wall, broken at the doors / passages
        if not R['walls'].get('bare') and not R['walls'].get('tile') and name not in ('Serverraum',):
            gaps = [(h['hu'][0], h['hu'][1]) for h in hs if h['kind'] in ('door', 'pass', 'gate') and h['hz'][0] <= R['f'] + 0.01]
            for su0, su1 in spans:
                for b0, b1 in _subtract((su0, su1), gaps):
                    t = 0.012
                    if axis == 'y':
                        lo = (b0, a if ns > 0 else a - t, R['f'])
                        hi = (b1, a + t if ns > 0 else a, R['f'] + BASEB_H)
                    else:
                        lo = (a if ns > 0 else a - t, b0, R['f'])
                        hi = (a + t if ns > 0 else a, b1, R['f'] + BASEB_H)
                    box6(k, lo, hi, Z_BASEB, skip=('-z', '-y' if (axis == 'y' and ns > 0) else '+y' if axis == 'y' else
                                                   ('-x' if ns > 0 else '+x')))
        # reveals of the room's windows and open passages (doors get their steel frames in main_open)
        for h in hs:
            if h['kind'] not in ('window', 'pass'):
                continue
            depth = reveal_depth(h, ns)
            w_ = next((w for w in S.WINDOWS if w['name'] == h.get('ref')), None)
            reveal(k, axis, a, ns, h['hu'], h['hz'], depth, Z_PLASTER if not R['walls'].get('bare') else Z_CONCIN,
                   bottom=(h['kind'] == 'pass') or bool(w_ and w_.get('internal')))   # glazing: no window board
        for h in hs:
            if h.get('niche') and abs(h['niche']['a'] - a) < 1e-3:
                door_niche(k, R, axis, a, ns, h, zf, cuts)
    # the notch faces (the flue's casing in the corner)
    for n in notches:
        box6(k, (n['x0'], n['y0'], R['f']), (n['x1'], n['y1'], R['c']), zf(R['f'] + 2.0),
             skip=('+x', '+y', '-z', '+z'))
    return k


def door_niche(k, R, axis, a, ns, h, zf, cuts):
    """a door set into a niche of the room face: the niche's back face round the door opening, its sides and top (the
    wall's finish bands), the floor in it, the skirting either side of the door"""
    nic = h['niche']
    d = nic['d']
    (nu0, nu1), (nz0, nz1) = h['hu'], h['hz']
    ab = a - ns * d
    du = (h['u0'], h['u1'])
    flat_wall(k, axis, ab, ns, nu0, nu1, nz0, nz1, zf, holes=[(du[0], du[1], h['z0'], h['z1'])], step=1.0, zcuts=cuts)
    P = (lambda aa, u, z: Vector((aa, u, z))) if axis == 'x' else (lambda aa, u, z: Vector((u, aa, z)))
    ua = Vector((0, 1, 0)) if axis == 'x' else Vector((1, 0, 0))
    zs = [nz0] + sorted(c for c in cuts if nz0 < c < nz1) + [nz1]
    for u, sg in ((nu0, 1), (nu1, -1)):
        for z0, z1 in zip(zs[:-1], zs[1:]):
            face(k, [P(a, u, z0), P(ab, u, z0), P(ab, u, z1), P(a, u, z1)], zf((z0 + z1) / 2), ua * sg)
    face(k, [P(a, nu0, nz1), P(ab, nu0, nz1), P(ab, nu1, nz1), P(a, nu1, nz1)], Z_PLASTER, (0, 0, -1))
    face(k, [P(a, nu0, R['f']), P(ab, nu0, R['f']), P(ab, nu1, R['f']), P(a, nu1, R['f'])], FLOOR_ZONE[R['floor']],
         (0, 0, 1))
    t = 0.012
    for b0, b1 in ((nu0, du[0]), (du[1], nu1)):
        if b1 - b0 < 0.02:
            continue
        a0_, a1_ = sorted((ab, ab + ns * t))
        lo = (a0_, b0, R['f']) if axis == 'x' else (b0, a0_, R['f'])
        hi = (a1_, b1, R['f'] + BASEB_H) if axis == 'x' else (b1, a1_, R['f'] + BASEB_H)
        back = ('-x' if ns > 0 else '+x') if axis == 'x' else ('-y' if ns > 0 else '+y')
        box6(k, lo, hi, Z_BASEB, skip=('-z', back))


def niche_depth(name):
    """how far a door's room face is set back (its niche), 0 without one"""
    n = S.DOORS[name].get('niche')
    return n['d'] if n else 0.0


def reveal_depth(h, ns):
    """from the room face into the wall: to the window frame (exterior walls) or the wall's middle"""
    w = next((w for w in S.WINDOWS if w['name'] == h['ref']), None)
    if w is not None:
        t = h['depth']
        if w.get('internal'):                                      # the server room's glazing: the glass mid-wall
            return t / 2 - 0.02
        return max(t - w['glass_in'] - 0.035, 0.02)                # the frame is 0.07 deep round the glass line
    return h['depth'] / 2


def reveal(k, axis, a, ns, hu, hz, depth, zone, bottom=True, top=True):
    """the reveal of an opening: from the face plane `a` (normal ns into the room) `depth` into the wall"""
    a0, a1 = a, a - ns * depth
    P = (lambda aa, u, z: Vector((aa, u, z))) if axis == 'x' else (lambda aa, u, z: Vector((u, aa, z)))
    ua = Vector((0, 1, 0)) if axis == 'x' else Vector((1, 0, 0))
    u0, u1 = hu
    z0, z1 = hz
    face(k, [P(a0, u0, z0), P(a1, u0, z0), P(a1, u0, z1), P(a0, u0, z1)], zone, ua)
    face(k, [P(a0, u1, z0), P(a1, u1, z0), P(a1, u1, z1), P(a0, u1, z1)], zone, -ua)
    if bottom:
        face(k, [P(a0, u0, z0), P(a1, u0, z0), P(a1, u1, z0), P(a0, u1, z0)], zone, (0, 0, 1))
    if top:
        face(k, [P(a0, u0, z1), P(a1, u0, z1), P(a1, u1, z1), P(a0, u1, z1)], zone, (0, 0, -1))


# ---------------------------------------------------------------- the exterior
def facade_zone(z):
    return Z_PLINTH if z < S.EG_F - 1e-4 else Z_FACADE


def ext_wall(axis, a, ns, u0, u1, z0, z1, covers=(), zcuts=()):
    """an outer face with the openings through it (the exterior side) and the outer reveals; covers: rectangles (u0, u1,
    z0, z1) another part of the building sits against (left out)"""
    k = ext()
    hs = holes_on(axis, a, ns, u0, u1, z0, z1)
    holes = [(h['hu'][0], h['hu'][1], h['hz'][0], h['hz'][1]) for h in hs] + list(covers)
    flat_wall(k, axis, a, ns, u0, u1, z0, z1, facade_zone, holes=holes, step=1.5, zcuts=[S.EG_F, S.EG_C, S.OG_F] + list(zcuts))
    for h in hs:
        if h['kind'] == 'window':
            w = next(w for w in S.WINDOWS if w['name'] == h['ref'])
            reveal(k, axis, a, ns, h['hu'], h['hz'], w['glass_in'] - 0.035, Z_REVEALX, bottom=False)
        elif h['kind'] == 'door':
            d = S.DOORS[h['ref']]
            pa = d.get('piv_y', d.get('piv_x'))
            reveal(k, axis, a, ns, h['hu'], h['hz'], max(abs(pa - a) - 0.03, 0.01), Z_REVEALX, bottom=False)
        elif h['kind'] == 'gate':
            reveal(k, axis, a, ns, h['hu'], h['hz'], h['depth'], Z_REVEALX, bottom=False)


def envelope():
    """the main block's facades (the garage and the tower stand against the west / north faces), the slab band, the
    parapet with its coping, the gravel roof round the tower and the flue, the tower above the roof, the garage hall"""
    k = ext()
    G, T = S.GARAGE, S.TOWER
    zb, zt = S.PLINTH_BOT, S.PARAPET
    # main block: south, north (the tower from x -1.95 to 1.95), east, west (the garage hall to y +-5, up to its roof)
    band = (S.EG_C, S.OG_F)
    ext_wall('y', -S.YO, -1, -S.XO, S.XO, zb, zt, covers=[(-S.XO, S.XO) + band])
    for u0, u1 in ((-S.XO, T['x0']), (T['x1'], S.XO)):
        ext_wall('y', S.YO, 1, u0, u1, zb, zt, covers=[(u0, u1) + band])
    ext_wall('x', S.XO, 1, -S.YO, S.YO, zb, zt, covers=[(-S.YO, S.YO) + band])
    ext_wall('x', -S.XO, -1, -S.YO, S.YO, zb, zt, covers=[(G['y0'], G['y1'], zb, S.G_ROOF), (-S.YO, G['y0']) + band,
                                                          (G['y1'], S.YO) + band], zcuts=[S.G_ROOF])
    # the slab band at the upper floor (5 cm proud), not where the garage stands
    zb0, zb1, d = S.EG_C, S.OG_F, 0.05
    for (lo, hi, skip) in (((-S.XO - d, -S.YO - d, zb0), (S.XO + d, -S.YO, zb1), ('+y',)),
                           ((-S.XO - d, S.YO, zb0), (T['x0'], S.YO + d, zb1), ('-y', '+x')),
                           ((T['x1'], S.YO, zb0), (S.XO + d, S.YO + d, zb1), ('-y', '-x')),
                           ((S.XO, -S.YO, zb0), (S.XO + d, S.YO, zb1), ('-x', '-y', '+y')),
                           ((-S.XO - d, -S.YO, zb0), (-S.XO, G['y0'], zb1), ('+x', '-y')),
                           ((-S.XO - d, G['y1'], zb0), (-S.XO, S.YO, zb1), ('+x', '+y'))):
        box6(k, lo, hi, Z_BAND, skip=skip)
    # parapet: inner faces, coping
    pi, piy = S.PAR_IN, S.PAR_IN_Y
    flat_wall(k, 'y', -piy, 1, -pi, pi, S.ROOF, zt, lambda z: Z_PARIN, step=1.5)
    flat_wall(k, 'y', piy, -1, -pi, T['x0'], S.ROOF, zt, lambda z: Z_PARIN, step=1.5)
    flat_wall(k, 'y', piy, -1, T['x1'], pi, S.ROOF, zt, lambda z: Z_PARIN, step=1.5)
    flat_wall(k, 'x', -pi, 1, -piy, piy, S.ROOF, zt, lambda z: Z_PARIN, step=1.5)
    flat_wall(k, 'x', pi, -1, -piy, piy, S.ROOF, zt, lambda z: Z_PARIN, step=1.5)
    coping_ring(k, [(T['x0'], S.YO), (-S.XO, S.YO), (-S.XO, -S.YO), (S.XO, -S.YO), (S.XO, S.YO), (T['x1'], S.YO)], zt,
                S.XO - S.PAR_IN)
    # roof (gravel) round the tower and the flue
    C = S.CHIMNEY
    xs = _grid({-pi, pi, T['x0'], T['x1'], C['x0'], C['x1']}, 1.5)
    ys = _grid({-piy, piy, T['y0'], C['y0'], C['y1']}, 1.5)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            xm, ym = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if T['x0'] < xm < T['x1'] and ym > T['y0']:
                continue
            if C['x0'] < xm < C['x1'] and C['y0'] < ym < C['y1']:
                continue
            face(k, [(xs[i], ys[j], S.ROOF), (xs[i + 1], ys[j], S.ROOF), (xs[i + 1], ys[j + 1], S.ROOF),
                     (xs[i], ys[j + 1], S.ROOF)], Z_ROOF, (0, 0, 1))
    # the brick flue above the roof, a concrete cap
    box6(k, (C['x0'], C['y0'], S.ROOF), (C['x1'], C['y1'], C['top']), Z_BRICK, skip=('-z', '+z'))
    box6(k, (C['x0'] - 0.04, C['y0'] - 0.04, C['top']), (C['x1'] + 0.04, C['y1'] + 0.04, C['top'] + 0.06), Z_BAND)
    # the stair tower outside: below the roof its three outer faces north of the block, above the roof all four
    ext_wall('x', T['x0'], -1, S.YO, T['y1'], zb, S.TOWER_TOP)
    ext_wall('x', T['x1'], 1, S.YO, T['y1'], zb, S.TOWER_TOP)
    ext_wall('y', T['y1'], 1, T['x0'], T['x1'], zb, S.TOWER_TOP)
    ext_wall('x', T['x0'], -1, T['y0'], S.YO, S.ROOF, S.TOWER_TOP, zcuts=[zt])
    ext_wall('x', T['x1'], 1, T['y0'], S.YO, S.ROOF, S.TOWER_TOP, zcuts=[zt])
    ext_wall('y', T['y0'], -1, T['x0'], T['x1'], S.ROOF, S.TOWER_TOP)
    flat_h(k, S.TOWER_TOP, 1, T['x0'], T['x1'], T['y0'], T['y1'], Z_ROOF, step=1.5)
    coping_ring(k, [(T['x0'], T['y0']), (T['x1'], T['y0']), (T['x1'], T['y1']), (T['x0'], T['y1'])], S.TOWER_TOP, 0.25,
                closed=True)
    # the garage hall: three outer faces, its parapet, coping and roof
    gp = 0.15
    ext_wall('x', G['x0'], -1, G['y0'], G['y1'], zb, S.G_PARAPET)
    ext_wall('y', G['y0'], -1, G['x0'], G['x1'], zb, S.G_PARAPET)
    ext_wall('y', G['y1'], 1, G['x0'], G['x1'], zb, S.G_PARAPET)
    flat_wall(k, 'x', G['x0'] + gp, 1, G['y0'] + gp, G['y1'] - gp, S.G_ROOF, S.G_PARAPET, lambda z: Z_PARIN)
    flat_wall(k, 'y', G['y0'] + gp, 1, G['x0'] + gp, G['x1'], S.G_ROOF, S.G_PARAPET, lambda z: Z_PARIN)
    flat_wall(k, 'y', G['y1'] - gp, -1, G['x0'] + gp, G['x1'], S.G_ROOF, S.G_PARAPET, lambda z: Z_PARIN)
    flat_h(k, S.G_ROOF, 1, G['x0'] + gp, G['x1'], G['y0'] + gp, G['y1'] - gp, Z_ROOF, step=1.5)
    coping_ring(k, [(G['x1'], G['y1']), (G['x0'], G['y1']), (G['x0'], G['y0']), (G['x1'], G['y0'])], S.G_PARAPET, gp)
    return k


def _offset(pts, d, closed):
    """offset a polyline (counter-clockwise outline from above) by d along its outward normals, mitred corners"""
    n = len(pts)
    P = [Vector((x, y, 0)) for x, y in pts]
    out = []
    for i in range(n):
        nbr = []
        if closed or i > 0:
            a, b = P[i - 1], P[i]
            t = (b - a).normalized()
            nbr.append(Vector((t.y, -t.x, 0)))
        if closed or i < n - 1:
            a, b = P[i], P[(i + 1) % n]
            t = (b - a).normalized()
            nbr.append(Vector((t.y, -t.x, 0)))
        if len(nbr) == 2:
            m = nbr[0] + nbr[1]
            m = m * (1.0 / max(m.dot(nbr[0]), 1e-6))
        else:
            m = nbr[0]
        out.append(P[i] + m * d)
    return out


def coping_ring(k, pts, z, width, closed=False, over=0.03, inner_over=0.02, h=0.04):
    """a galvanised coping along a parapet's top: pts = the outer face's corners, counter-clockwise from above (an open
    polyline ends flush against the wall it runs into); `width` = the parapet's thickness"""
    O = _offset(pts, over, closed)
    I = _offset(pts, -(width + inner_over), closed)
    n = len(pts)
    segs = range(n) if closed else range(n - 1)
    for i in segs:
        j = (i + 1) % n
        o0, o1, i0_, i1_ = O[i], O[j], I[i], I[j]
        nrm = Vector(((o1 - o0).y, -(o1 - o0).x, 0)).normalized()
        L = lambda p, zz: Vector((p.x, p.y, zz))
        face(k, [L(o0, z + h), L(o1, z + h), L(i1_, z + h), L(i0_, z + h)], Z_GALV, (0, 0, 1))
        face(k, [L(o0, z), L(o1, z), L(o1, z + h), L(o0, z + h)], Z_GALV, nrm)
        face(k, [L(i0_, z), L(i0_, z + h), L(i1_, z + h), L(i1_, z)], Z_GALV, -nrm)
        face(k, [L(o0, z), L(i0_, z), L(i1_, z), L(o1, z)], Z_GALV, (0, 0, -1))
    if not closed:
        for idx, sgn in ((0, -1), (n - 1, 1)):
            a, b = (O[0], I[0]) if idx == 0 else (O[-1], I[-1])
            t = (Vector(pts[1] + (0,)) - Vector(pts[0] + (0,))) if idx == 0 else (Vector(pts[-1] + (0,)) - Vector(pts[-2] + (0,)))
            face(k, [Vector((a.x, a.y, z)), Vector((b.x, b.y, z)), Vector((b.x, b.y, z + h)), Vector((a.x, a.y, z + h))],
                 Z_GALV, t.normalized() * sgn)


# ---------------------------------------------------------------- the stair
def stair():
    """U-stair per storey (main_spec.STAIR): the floor landings at each level (west half to y 2.55, east half to 2.83),
    flight A up north on the west half, the half landing across the tower, flight B up south on the east half; concrete
    with sloped soffits, galvanised nosings; the tower's own floor and walls are room_shell's (bare concrete)"""
    k = rkb('Treppenhaus')
    T, ST = S.TOWER, S.STAIR
    xa, xb = ST['xa'], ST['xb']
    g, n = ST['going'], ST['n']
    y0 = ST['y_start']
    ym0, ym1 = ST['mid']
    for (z0, z1) in S.STOREYS:
        h = (z1 - z0) / (2 * n)
        zm = z0 + n * h
        # flight A (west, rising north): steps i = 1..n-1 at y0 + (i-1) g .. y0 + i g, then the landing riser at ym0
        poly = [(y0, z0)]
        for i in range(1, n):
            poly += [(y0 + (i - 1) * g, z0 + i * h), (y0 + i * g, z0 + i * h)]
        poly += [(ym0, zm)]
        soffit = 0.18
        poly += [(ym0, zm - soffit - 0.05), (y0 + 0.30, z0 - 0.12)]
        flight(k, poly, xa[0], xa[1], ('A', z0))
        # half landing (y ym0..ym1 over the tower's width), 0.20 slab
        box6(k, (T['xi0'], ym0, zm - 0.20), (T['xi1'], T['yi1'], zm), {'+z': Z_STAIR, '*': Z_SOFFIT},
             skip=('+y', '-x', '+x'))
        # flight B (east, rising south): from the landing at y ym0 + g down to y 2.83
        yb0 = ym0 + g                                           # 5.35: the first riser
        poly = [(yb0, zm)]
        for j in range(1, n):
            poly += [(yb0 - (j - 1) * g, zm + j * h), (yb0 - j * g, zm + j * h)]
        poly += [(yb0 - (n - 1) * g, z1)]
        poly += [(yb0 - (n - 1) * g, z1 - soffit - 0.05), (yb0 - 0.30, zm - 0.12)]
        flight(k, [(-yy, zz) for yy, zz in poly], xb[0], xb[1], ('B', z0), mirror=True)
        # the floor landing at z1 (y 1.15 .. 2.55 on the west half, .. 2.83 on the east), 0.30 slab under it
        yl_w, yl_e = y0, yb0 - (n - 1) * g
        top = z1
        for (x0, x1, y1_) in ((T['xi0'], 0.0, yl_w), (0.0, T['xi1'], yl_e)):
            face(k, [(x0, T['yi0'], top), (x1, T['yi0'], top), (x1, y1_, top), (x0, y1_, top)], Z_STAIR, (0, 0, 1))
            face(k, [(x0, T['yi0'], top - 0.30), (x1, T['yi0'], top - 0.30), (x1, y1_, top - 0.30), (x0, y1_, top - 0.30)],
                 Z_SOFFIT, (0, 0, -1))
        face(k, [(T['xi0'], yl_w, top - 0.30), (0.0, yl_w, top - 0.30), (0.0, yl_w, top), (T['xi0'], yl_w, top)], Z_STAIR,
             (0, 1, 0))
        face(k, [(0.0, yl_e, top - 0.30), (T['xi1'], yl_e, top - 0.30), (T['xi1'], yl_e, top), (0.0, yl_e, top)], Z_STAIR,
             (0, 1, 0))
        face(k, [(0.0, yl_w, top - 0.30), (0.0, yl_e, top - 0.30), (0.0, yl_e, top), (0.0, yl_w, top)], Z_STAIR, (-1, 0, 0))
    # the basement floor of the tower
    flat_h(k, S.UG_F, 1, T['xi0'], T['xi1'], T['yi0'], T['yi1'], Z_FL_CONC)
    return k


def flight(k, poly, x0, x1, tag, mirror=False):
    """a concrete flight: the side profile poly [(y, z)] (counter-clockwise seen from -x: y right, z up) extruded x0..x1;
    galvanised nosing angles on the treads' fronts; mirror: poly is given in -y (flight B)"""
    if mirror:
        P = [(-yy, zz) for yy, zz in poly]
        P = list(reversed(P))
    else:
        P = poly
    # make sure the polygon runs counter-clockwise in (y, z)
    a = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    if a < 0:
        P = list(reversed(P))
    edges = []
    for i in range(len(P)):
        (ya, za), (yb, zb) = P[i], P[(i + 1) % len(P)]
        edges.append(Z_SOFFIT if (zb - za) * (yb - ya) != 0 and abs(zb - za) > 0.05 and abs(yb - ya) > 0.05 else Z_STAIR)
    prism_x(k, P, x0, x1, Z_STAIR, Z_STAIR, edges=edges)


def build_shell():
    for name in S.ROOMS:
        room_shell(name)
    envelope()
    stair()
