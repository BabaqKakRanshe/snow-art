"""Van concept («буханка»-type, original design) built like the plane: smooth SDF body shell with real openings,
panel gaps, seals, gutters, lights, bumpers, chassis with portal axles, lathe tyres with lugs.
build(stage) -> dict of objects;  python3 van.py  saves out/van.blend"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from mathutils import Vector, Matrix
import vb as B

HERE = B.HERE
PROF = json.load(open(os.path.join(HERE, 'work', 'profiles.json')))
R, W, XF, XR, TY = 0.52, 0.36, 1.45, -1.25, 0.93          # tyre radius / width, axles, half track
ZB = PROF['P']['zb']


def hw(z):
    """half width of the body side wall at height z (straight part of the body)"""
    pts = sorted([(zz, y) for y, zz in PROF['sec'] if y > 0.3])
    zs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    return float(np.interp(z, zs, ys))


def xfront(z):
    pts = [(zz, x) for x, zz in PROF['side'] if x > 1.0]
    pts.sort()
    zs = np.array([p[0] for p in pts]); xs = np.array([p[1] for p in pts])
    return float(np.interp(z, zs, xs))


def xrear(z):
    pts = [(zz, x) for x, zz in PROF['side'] if x < -1.0]
    pts.sort()
    zs = np.array([p[0] for p in pts]); xs = np.array([p[1] for p in pts])
    return float(np.interp(z, zs, xs))


# ------------------------------------------------------------------ layout (original window / door scheme)
ZW0, ZW1 = 1.92, 2.46                                     # side window band
WIN_L = [(1.08, 1.84), (0.12, 0.90), (-0.92, -0.16), (-2.02, -1.34)]       # left side, x ranges
WIN_R = [(1.08, 1.84), (-2.02, -1.34)]                                     # right side (+ side door window)
SIDE_DOOR = (-0.36, 0.60)                                                  # right side door, x range
SD_WIN = (-0.26, 0.50)
CAB_DOOR = (1.00, 1.93, 1.22, 2.58)                                        # x0, x1, z0, z1
REAR_WIN = [(0.12, 0.74), (-0.74, -0.12)]                                  # rear door windows, y ranges
WS = [(0.035, 0.72), (-0.72, -0.035)]                                        # windshield panes, y ranges
ZWS0, ZWS1 = 1.84, 2.42


def mats():
    M = dict(
        paint=B.tex_box('paint', 'paint_red', 60, 0.55),
        lining=B.tex_box('lining', 'vinyl_beige', 120, 0.7),
        seal=B.tex_box('seal', 'rubber', 120, 0.85),
        glass=glass(),
        plastic=B.tex_box('plastic', 'plastic_black', 90, 0.8),
        chassis=B.tex_box('chassis', 'chassis_dark', 70, 0.65, 0.2),
        steel=B.tex_box('steel', 'steel_worn', 90, 0.45, 0.6),
        chrome=B.flat('chrome', (0.75, 0.76, 0.78), 0.2, 1.0),
        tyre=B.tex_box('tyre', 'rubber', 120, 0.9),
        rim=B.tex_box('rim', 'rim_grey', 90, 0.5, 0.4),
        lens=B.flat('lens_clear', (0.85, 0.86, 0.84), 0.08),
        amber=B.flat('lens_amber', (0.85, 0.42, 0.05), 0.15),
        red=B.flat('lens_red', (0.6, 0.04, 0.03), 0.15),
        shackle=B.flat('shackle', (0.65, 0.08, 0.05), 0.4, 0.3),
        wood=B.tex_box('wood_box', 'wood_crate', 90, 0.7),
        canvas=B.tex_box('canvas', 'canvas', 90, 0.9),
    )
    return M


def glass(name='glass', tint=(0.09, 0.11, 0.13), clear=0.68):
    if name in B.MATS:
        return B.MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    gl.inputs['Color'].default_value = (*tint, 1)
    gl.inputs['Roughness'].default_value = 0.05
    mx = nt.nodes.new('ShaderNodeMixShader')
    mx.inputs[0].default_value = 1 - clear
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.56, 0.26, 1)
    em.inputs['Strength'].default_value = 0.0
    ad = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(mx.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], out.inputs[0])
    m['glow_node'] = em.name
    B.MATS[name] = m
    return m


# ------------------------------------------------------------------ body shell
def body_shell(M, col):
    d = np.load(os.path.join(HERE, 'work', 'body_outer.npz'))
    body = B.mesh_np('Body', d['v'], d['f'], col)
    md = body.modifiers.new('sm', 'SMOOTH'); md.factor = 0.5; md.iterations = 4
    B.apply_mods(body)
    B.decimate(body, 0.16)
    me = body.data
    n = np.zeros(len(me.polygons) * 3, np.float32); c = np.zeros_like(n)
    me.polygons.foreach_get('normal', n); me.polygons.foreach_get('center', c)
    n = n.reshape(-1, 3); c = c.reshape(-1, 3)
    if float(((c - c.mean(0)) * n).sum(1).mean()) < 0:            # make the normals point outward
        me.flip_normals()
    body.data.materials.append(M['paint'])
    body.data.materials.append(M['lining'])
    body.data.materials.append(M['seal'])
    B.solidify(body, 0.035, -1.0, 1, 2)
    cuts = []
    # wheel arches (per side, the floor between them stays)
    for xa in (XF, XR):
        for s in (1, -1):
            c = B.cyl('arch', (xa, s * 1.0, R), 'y', 0.645, 0.5, 64, M['seal'])
            cuts.append(c)
    # windows
    for x0, x1 in WIN_L:
        cuts.append(B.prism('w', B.rrect(x0, x1, ZW0, ZW1, 0.075), 'y', 0.7, 1.4, M['seal']))
    for x0, x1 in WIN_R:
        cuts.append(B.prism('w', B.rrect(x0, x1, ZW0, ZW1, 0.075), 'y', -1.4, -0.7, M['seal']))
    for y0, y1 in WS:
        cuts.append(B.prism('ws', B.rrect(y0, y1, ZWS0, ZWS1, 0.06), 'x', 1.9, 2.8, M['seal']))
    for y0, y1 in REAR_WIN:
        cuts.append(B.prism('rw', B.rrect(y0, y1, 1.96, 2.42, 0.06), 'x', -2.8, -2.0, M['seal']))
    B.boolean(body, cuts)
    # side door: separate leaf (shell ∩ door volume), body minus a slightly larger volume (3 mm gap)
    x0, x1 = SIDE_DOOR
    vol = B.prism('sdv', B.rrect(x0, x1, 0.95, 2.58, 0.07), 'y', -1.5, -0.85)
    door = body.copy(); door.data = body.data.copy(); door.name = 'SideDoor'
    col.objects.link(door)
    B.boolean(door, [vol], 'INTERSECT')
    B.boolean(door, [B.prism('sdw', B.rrect(*SD_WIN, ZW0, ZW1, 0.075), 'y', -1.5, -0.8, M['seal'])])
    B.boolean(body, [B.prism('sdv2', B.rrect(x0 - 0.004, x1 + 0.004, 0.946, 2.584, 0.074), 'y', -1.5, -0.85,
                             M['seal'])])
    # panel gaps: cab doors, rear doors, fuel flap
    gaps = []
    cx0, cx1, cz0, cz1 = CAB_DOOR
    for s in (1, -1):
        y0, y1 = (0.95, 1.2) if s > 0 else (-1.2, -0.95)
        g = B.ring('gap', B.rrect(cx0, cx1, cz0, cz1, 0.07), 'y', y0, y1, 0.005)
        gaps.append(g)
    for yy in ((0.004, 0.86), (-0.86, -0.004)):
        gaps.append(B.ring('gap', B.rrect(*yy, 0.97, 2.55, 0.06), 'x', -2.62, -2.3, 0.005))
    gaps.append(B.ring('gap', B.rrect(-2.24, -2.04, 1.24, 1.44, 0.09), 'y', 0.95, 1.2, 0.004))
    # shallow: keep only the outer skin cut (the gap cutters end 2 cm inside the outer surface)
    for g in gaps:
        g.data.materials.clear()
        g.data.materials.append(M['seal'])
    B.boolean(body, gaps)
    B.smooth(body, 35)
    B.smooth(door, 35)
    hinge = (x1, -hw(1.7), 0)
    B.set_origin(door, hinge)
    return body, door


def window_parts(M, col):
    """rubber seals and glass in every opening"""
    parts = []
    def side_win(x0, x1, s, z0=ZW0, z1=ZW1, r=0.075, room=False):
        y = s * hw((z0 + z1) / 2)
        poly = B.rrect(x0 - 0.012, x1 + 0.012, z0 - 0.012, z1 + 0.012, r + 0.012)
        sl = B.ring('seal', poly, 'y', *sorted((y - s * 0.045, y + s * 0.012)), 0.03, M['seal'], col)
        g = B.prism('glass', B.rrect(x0, x1, z0, z1, r), 'y', *sorted((y - s * 0.022, y - s * 0.017)),
                    glass('glass_room') if room else M['glass'], col)
        # tilt glass + seal to the wall lean (tumblehome)
        lean = math.atan2(hw(z0) - hw(z1), z1 - z0)
        for o in (sl, g):
            o.data.transform(Matrix.Translation((0, y, (z0 + z1) / 2)) @ Matrix.Rotation(s * lean, 4, 'X') @
                             Matrix.Translation((0, -y, -(z0 + z1) / 2)))
        return [sl, g]
    for i, (x0, x1) in enumerate(WIN_L):
        parts += side_win(x0, x1, 1, room=i > 0)
    for i, (x0, x1) in enumerate(WIN_R):
        parts += side_win(x0, x1, -1, room=i > 0)
    # windshield: seal + glass on the raked plane
    rk = math.radians(PROF['P']['rake'])
    zc = (ZWS0 + ZWS1) / 2
    xc = xfront(zc)
    for y0, y1 in WS:
        poly = B.rrect(y0 - 0.012, y1 + 0.012, ZWS0 - 0.012, ZWS1 + 0.012, 0.072)
        sl = B.ring('ws_seal', poly, 'x', xc - 0.03, xc + 0.008, 0.024, M['seal'], col)
        g = B.prism('ws_glass', B.rrect(y0, y1, ZWS0, ZWS1, 0.06), 'x', xc - 0.018, xc - 0.013, M['glass'], col)
        for o in (sl, g):
            o.data.transform(Matrix.Translation((xc, 0, zc)) @ Matrix.Rotation(-rk, 4, 'Y') @
                             Matrix.Translation((-xc, 0, -zc)))
        parts += [sl, g]
    xr = xrear(2.19)
    for y0, y1 in REAR_WIN:
        poly = B.rrect(y0 - 0.012, y1 + 0.012, 1.948, 2.432, 0.072)
        parts.append(B.ring('rw_seal', poly, 'x', xr - 0.012, xr + 0.04, 0.03, M['seal'], col))
        parts.append(B.prism('rw_glass', B.rrect(y0, y1, 1.96, 2.42, 0.06), 'x', xr + 0.016, xr + 0.021, glass('glass_room'),
                             col))
    return parts


def door_glass(M, door, col):
    x0, x1 = SD_WIN
    y = -hw((ZW0 + ZW1) / 2)
    lean = math.atan2(hw(ZW0) - hw(ZW1), ZW1 - ZW0)
    sl = B.ring('sd_seal', B.rrect(x0 - 0.012, x1 + 0.012, ZW0 - 0.012, ZW1 + 0.012, 0.087), 'y', y - 0.012, y + 0.045,
                0.03, M['seal'], col)
    g = B.prism('sd_glass', B.rrect(x0, x1, ZW0, ZW1, 0.075), 'y', y + 0.017, y + 0.022, glass('glass_room'), col)
    for o in (sl, g):
        o.data.transform(Matrix.Translation((0, y, (ZW0 + ZW1) / 2)) @ Matrix.Rotation(-lean, 4, 'X') @
                         Matrix.Translation((0, -y, -(ZW0 + ZW1) / 2)))
        o.data.transform(Matrix.Translation(-door.location))
        o.parent = door
    return [sl, g]


# ------------------------------------------------------------------ wheels
def tyre(name, cx, cy, s, M, col):
    """mud-terrain tyre: lathe carcass + lug blocks, steel rim, lug nuts; s = side (+1 left, -1 right)"""
    lug = 0.026
    rc = R - lug
    hw_ = W / 2
    prof = [(0.255, -hw_ + 0.03), (0.30, -hw_ - 0.005), (0.38, -hw_ - 0.012), (0.44, -hw_ + 0.0), (rc - 0.02, -hw_ + 0.02),
            (rc, -hw_ + 0.06), (rc, 0.0), (rc, hw_ - 0.06), (rc - 0.02, hw_ - 0.02), (0.44, hw_), (0.38, hw_ + 0.012),
            (0.30, hw_ + 0.005), (0.255, hw_ - 0.03)]
    parts = [B.lathe(name + '_c', prof, 'y', 64, (cx, cy, R), M['tyre'], col)]
    n = 34
    for k in range(n):
        a = 2 * math.pi * k / n
        for side in (-1, 1):
            off = side * (0.06 if k % 2 else 0.085)
            L = 0.10 if k % 2 else 0.075
            blk = B.box(name + f'_b{k}{side}', -0.03, 0.03, -L / 2, L / 2, 0, lug + 0.004, M['tyre'], col)
            sh = B.box(name + f'_s{k}{side}', -0.028, 0.028, -0.035, 0.035, -0.045, lug, M['tyre'], col)
            sh.data.transform(Matrix.Translation((0, side * (hw_ - 0.025), 0)) @ Matrix.Rotation(-side * 0.6, 4, 'X'))
            blk.data.transform(Matrix.Translation((0, off, 0)))
            for o in (blk, sh):
                o.data.transform(Matrix.Translation((cx, cy, R)) @ Matrix.Rotation(-a, 4, 'Y') @
                                 Matrix.Translation((0, 0, rc - 0.002)))
            parts += [blk, sh]
    tyre_ob = B.join(parts, name)
    B.smooth(tyre_ob, 40)
    # rim: dished steel wheel, 6 holes, hub, 8 nuts
    face = cy + s * (hw_ - 0.04)
    rprof = [(0.255, -0.13), (0.245, -0.12), (0.245, 0.10), (0.255, 0.125), (0.23, 0.125), (0.20, 0.09),
             (0.12, 0.07), (0.07, 0.075), (0.0, 0.075)]
    rp = [(r, s * a) for r, a in rprof]
    rim = B.lathe(name + '_rim', rp, 'y', 40, (cx, cy, R), M['rim'], col)
    holes = []
    for k in range(6):
        aa = 2 * math.pi * k / 6 + 0.26
        holes.append(B.cyl('h', (cx + 0.16 * math.cos(aa), cy + s * 0.08, R + 0.16 * math.sin(aa)), 'y', 0.035, 0.12, 16))
    B.boolean(rim, holes)
    B.smooth(rim, 40)
    hub = B.cyl(name + '_hub', (cx, cy + s * 0.11, R), 'y', 0.075, 0.07, 20, M['chassis'], col)
    nuts = [B.cyl(name + f'_n{k}', (cx + 0.10 * math.cos(2 * math.pi * k / 8), cy + s * 0.088,
                                   R + 0.10 * math.sin(2 * math.pi * k / 8)), 'y', 0.014, 0.03, 6, M['steel'], col)
            for k in range(8)]
    rim_ob = B.join([rim, hub] + nuts, name + '_wheel')
    return tyre_ob, rim_ob


# ------------------------------------------------------------------ chassis
def chassis(M, col):
    P = []
    for s in (1, -1):
        P.append(B.box(f'rail{s}', -2.30, 2.28, *sorted((s * 0.42, s * 0.50)), 0.70, 0.88, M['chassis'], col))
    for xx in (-2.2, -1.25, -0.2, 0.75, 1.45, 2.15):
        P.append(B.box(f'xm{xx}', xx - 0.04, xx + 0.04, -0.42, 0.42, 0.73, 0.85, M['chassis'], col))
    for xx in (-2.0, -0.9, 0.3, 1.2, 2.0):
        for s in (1, -1):
            P.append(B.box(f'mount{xx}{s}', xx - 0.05, xx + 0.05, *sorted((s * 0.44, s * 0.52)), 0.88, ZB + 0.01,
                           M['plastic'], col))
    zt = R + 0.10                                                     # portal: axle tube above the wheel centre
    for xa in (XF, XR):
        P.append(B.cyl(f'axle{xa}', (xa, 0, zt), 'y', 0.065, 1.42, 20, M['chassis'], col))
        dif = B.lathe(f'diff{xa}', [(0.0, -0.13), (0.12, -0.12), (0.17, -0.04), (0.17, 0.03), (0.12, 0.10), (0.0, 0.11)],
                      'y', 24, (xa, 0.12, zt - 0.02), M['chassis'], col)
        B.smooth(dif, 40)
        P.append(dif)
        P.append(B.cyl(f'pinion{xa}', (xa + (0.16 if xa > 0 else -0.16), 0.12, zt), 'x', 0.06, 0.16, 16, M['chassis'], col))
        for s in (1, -1):
            pb = B.prism(f'portal{xa}{s}', B.rrect(xa - 0.13, xa + 0.13, R - 0.12, zt + 0.12, 0.11), 'y',
                         *sorted((s * 0.70, s * 0.80)), M['chassis'], col)
            P.append(pb)
            # leaf spring: 4 leaves, slight arc, eyes, shackle
            for k in range(4):
                L = 0.70 - k * 0.13
                zz = zt + 0.08 + k * 0.018
                pts = [(xa - L, s * 0.46, zz + 0.03 + k * 0.01), (xa - L * 0.5, s * 0.46, zz + 0.008),
                       (xa, s * 0.46, zz), (xa + L * 0.5, s * 0.46, zz + 0.008), (xa + L, s * 0.46, zz + 0.03 + k * 0.01)]
                lf = B.tube(f'leaf{xa}{s}{k}', pts, 0.012, M['steel'], col, 4)
                lf.scale = (1, 3.0, 0.75)
                lf.data.transform(Matrix.Translation((0, s * 0.46, 0)) @ Matrix.Diagonal((1, 3.0, 0.75, 1)) @
                                  Matrix.Translation((0, -s * 0.46, 0)))
                lf.scale = (1, 1, 1)
                P.append(lf)
            P.append(B.box(f'ubolt{xa}{s}', xa - 0.05, xa + 0.05, *sorted((s * 0.42, s * 0.50)), zt - 0.07, zt + 0.17,
                           M['steel'], col))
            # shock absorber
            sb = B.tube(f'shock{xa}{s}', [(xa + 0.16, s * 0.60, zt), (xa + 0.30, s * 0.55, 0.86)], 0.032, M['chassis'], col, 12)
            P.append(sb)
            P.append(B.tube(f'shockc{xa}{s}', [(xa + 0.19, s * 0.59, zt + 0.06), (xa + 0.26, s * 0.565, 0.70)], 0.042,
                            M['steel'], col, 12))
    # steering, driveshafts, transfer case, tank, exhaust
    P.append(B.cyl('tierod', (XF - 0.22, 0, R + 0.02), 'y', 0.02, 1.5, 10, M['steel'], col))
    P.append(B.tube('shaftF', [(XF - 0.16, 0.12, R + 0.10), (0.35, 0.05, 0.70)], 0.035, M['steel'], col, 12))
    P.append(B.tube('shaftR', [(XR + 0.16, 0.12, R + 0.10), (-0.10, 0.05, 0.70)], 0.035, M['steel'], col, 12))
    P.append(B.box('tcase', -0.12, 0.38, -0.12, 0.22, 0.60, 0.86, M['chassis'], col))
    tank = B.prism('tank', B.rrect(-0.75, 0.30, 0.56, 0.88, 0.07), 'y', 0.55, 0.98, M['chassis'], col)
    P.append(tank)
    P.append(B.tube('exhaust', [(1.0, -0.30, 0.66), (0.4, -0.62, 0.64), (-0.6, -0.66, 0.64), (-1.75, -0.66, 0.66),
                                (-2.05, -0.72, 0.64)], 0.03, M['steel'], col, 12))
    P.append(B.prism('muffler', B.rrect(-0.55, 0.20, 0.58, 0.74, 0.07), 'y', -0.78, -0.56, M['chassis'], col))
    return P


# ------------------------------------------------------------------ exterior details
def front_end(M, col):
    P = []
    xf = xfront(1.32)
    # recessed black grille panel across the nose with round lamps and slats (own face, not a replica)
    pan = B.prism('grille_panel', B.rrect(-0.72, 0.72, 1.17, 1.47, 0.05), 'x', xf - 0.02, xf + 0.012, M['plastic'], col)
    P.append(pan)
    for k in range(5):
        zz = 1.21 + k * 0.05
        P.append(B.box(f'slat{k}', xf + 0.008, xf + 0.02, -0.22, 0.22, zz, zz + 0.022, M['steel'], col))
    for s in (1, -1):
        y = s * 0.52
        bez = B.lathe(f'bezel{s}', [(0.0, 0.0), (0.105, 0.0), (0.112, 0.012), (0.105, 0.03), (0.092, 0.03)], 'x', 32,
                      (xf + 0.005, y, 1.32), M['chrome'], col)
        lens = B.lathe(f'head{s}', [(0.0, 0.045), (0.05, 0.042), (0.085, 0.034), (0.093, 0.026)], 'x', 32,
                       (xf + 0.005, y, 1.32), M['lens'], col)
        P += [bez, lens]
        y2 = s * 0.31
        P.append(B.lathe(f'fogb{s}', [(0.0, 0.0), (0.06, 0.0), (0.064, 0.02), (0.052, 0.025)], 'x', 24,
                         (xf + 0.005, y2, 1.32), M['chrome'], col))
        P.append(B.lathe(f'fog{s}', [(0.0, 0.03), (0.05, 0.026)], 'x', 24, (xf + 0.005, y2, 1.32), M['amber'], col))
        # turn signal on the nose corner
        P.append(B.box(f'turn{s}', xfront(1.56) - 0.03, xfront(1.56) + 0.006, *sorted((s * 0.56, s * 0.74)), 1.52, 1.58,
                       M['amber'], col))
    # winch bumper
    bp = B.prism('bumper', [(-1.02, 0.60), (1.02, 0.60), (1.10, 0.70), (1.10, 0.86), (-1.10, 0.86), (-1.10, 0.70)], 'x',
                 2.36, 2.62, M['chassis'], col)
    B.bevel(bp, 0.01, 1)
    P.append(bp)
    P.append(B.box('winch_well', 2.50, 2.63, -0.30, 0.30, 0.64, 0.84, M['plastic'], col))
    P.append(B.cyl('winch', (2.55, 0, 0.74), 'y', 0.085, 0.50, 24, M['chassis'], col))
    P.append(B.cyl('cable', (2.55, 0, 0.74), 'y', 0.092, 0.30, 24, M['steel'], col))
    fl = B.ring('fairlead', B.rrect(-0.13, 0.13, 0.67, 0.81, 0.02), 'x', 2.62, 2.66, 0.035, M['steel'], col)
    P.append(fl)
    P.append(B.tube('hook', [(2.66, 0, 0.74), (2.74, 0, 0.74), (2.76, 0, 0.70)], 0.012, M['steel'], col))
    for s in (1, -1):
        sh = B.tube(f'shackle{s}', [(2.60, s * 0.72, 0.66), (2.70, s * 0.72, 0.66), (2.73, s * 0.72, 0.73),
                                    (2.70, s * 0.72, 0.80), (2.60, s * 0.72, 0.80)], 0.016, M['shackle'], col)
        P.append(sh)
    # wipers
    for s in (1, -1):
        y = s * 0.38
        P.append(B.tube(f'wiper{s}', [(xfront(1.82) - 0.02, y + s * 0.18, 1.80), (xfront(2.15) - 0.04, y - s * 0.08, 2.18)],
                        0.008, M['plastic'], col))
    # licence plate (blank)
    P.append(B.box('plate', 2.62, 2.635, -0.26, 0.26, 0.86, 0.98, B.flat('plate', (0.8, 0.8, 0.76), 0.5), col))
    return P


def flares_steps_mirrors(M, col):
    P = []
    for xa in (XF, XR):
        for s in (1, -1):
            out = [(xa + 0.72 * math.cos(math.radians(a)), R + 0.72 * math.sin(math.radians(a))) for a in range(-8, 189, 6)]
            inn = [(xa + 0.645 * math.cos(math.radians(a)), R + 0.645 * math.sin(math.radians(a))) for a in range(188, -9, -6)]
            y0 = s * (hw(1.0) - 0.03)
            f = B.prism(f'flare{xa}{s}', out + inn, 'y', *sorted((y0, s * (hw(1.0) + 0.09))), M['plastic'], col)
            B.bevel(f, 0.012, 2, 35)
            B.smooth(f, 35)
            P.append(f)
            # inner arch liner
            lo = [(xa + 0.645 * math.cos(math.radians(a)), R + 0.645 * math.sin(math.radians(a))) for a in range(-6, 187, 6)]
            li = [(xa + 0.60 * math.cos(math.radians(a)), R + 0.60 * math.sin(math.radians(a))) for a in range(186, -7, -6)]
            ln = B.prism(f'liner{xa}{s}', lo + li, 'y', *sorted((s * 0.62, s * (hw(1.0) - 0.02))), M['plastic'], col)
            P.append(ln)
            P.append(B.prism(f'linerw{xa}{s}', B.rrect(xa - 0.66, xa + 0.66, ZB - 0.02, R + 0.66, 0.05), 'y',
                             *sorted((s * 0.60, s * 0.625)), M['plastic'], col))
            # mud flap behind the wheel
            P.append(B.box(f'flap{xa}{s}', xa - 0.70, xa - 0.69, *sorted((s * 0.78, s * 1.08)), 0.28, 0.95, M['seal'], col))
    for s in (1, -1):
        # mirror on the A-pillar
        y0 = s * (hw(2.15) - 0.02)
        P.append(B.tube(f'marm{s}', [(1.92, y0, 2.08), (2.02, s * 1.20, 2.12), (2.06, s * 1.27, 2.20)], 0.012, M['plastic'], col))
        mh = B.box(f'mhead{s}', 2.03, 2.09, *sorted((s * 1.20, s * 1.36)), 2.10, 2.40, M['plastic'], col)
        B.bevel(mh, 0.02, 2)
        P.append(mh)
        # cab door handle + hinges
        y = s * hw(1.9)
        P.append(B.box(f'chandle{s}', 1.10, 1.24, *sorted((y, y + s * 0.025)), 1.90, 1.93, M['chrome'], col))
        for zz in (1.45, 2.32):
            P.append(B.cyl(f'chinge{s}{zz}', (1.95, y + s * 0.012, zz), 'z', 0.014, 0.09, 10, M['steel'], col))
        # side markers
        P.append(B.box(f'smark{s}', -2.10, -2.02, *sorted((s * hw(1.25), s * (hw(1.25) + 0.01))), 1.22, 1.27, M['amber'], col))
    # step behind the front wheel (cab) and under the side door
    for s in (1, -1):
        P.append(B.box(f'cstep{s}', 0.66, 0.98, *sorted((s * 0.86, s * 1.12)), 0.72, 0.76, M['steel'], col))
    P.append(B.box('sstep', -0.30, 0.54, -1.14, -0.88, 0.64, 0.68, M['steel'], col))
    for xx in (-0.25, 0.48):
        P.append(B.box(f'sstep_b{xx}', xx, xx + 0.04, -0.98, -0.94, 0.64, ZB, M['steel'], col))
    # gutters along the roof side
    for s in (1, -1):
        y = s * (hw(2.58) + 0.01)
        P.append(B.tube(f'gutter{s}', [(xx, y, 2.58) for xx in np.linspace(-2.10, 1.70, 12)], 0.010, M['paint'], col, 6))
    return P


def rear_end(M, col):
    P = []
    xr = xrear(1.6)
    for s in (1, -1):
        # rear door handles, hinges, tail lights on the corners
        y = s * 0.12
        P.append(B.box(f'rhandle{s}', xr - 0.03, xr, *sorted((y, y + s * 0.12)), 1.62, 1.65, M['chrome'], col))
        for zz in (1.15, 2.32):
            P.append(B.cyl(f'rhinge{s}{zz}', (xr - 0.012, s * 0.86, zz), 'z', 0.014, 0.10, 10, M['steel'], col))
        tl = B.prism(f'tail{s}', B.rrect(0.98, 1.36, s * 0.0 + 0, 0.1, 0.02), 'x', 0, 0.04, M['red'], col)
        bpy.data.objects.remove(tl, do_unlink=True)
        th = B.box(f'tailh{s}', xr - 0.035, xr + 0.02, *sorted((s * 0.84, s * 0.98)), 0.98, 1.36, M['plastic'], col)
        P.append(th)
        P.append(B.box(f'tailr{s}', xr - 0.045, xr - 0.034, *sorted((s * 0.855, s * 0.965)), 1.16, 1.34, M['red'], col))
        P.append(B.box(f'taila{s}', xr - 0.045, xr - 0.034, *sorted((s * 0.855, s * 0.965)), 1.00, 1.14, M['amber'], col))
    bp = B.box('rbumper', -2.66, -2.42, -1.02, 1.02, 0.66, 0.84, M['chassis'], col)
    B.bevel(bp, 0.01, 1)
    P.append(bp)
    P.append(B.box('rstep', -2.78, -2.62, -0.35, 0.35, 0.70, 0.74, M['steel'], col))
    P.append(B.tube('hitch', [(-2.62, 0, 0.62), (-2.82, 0, 0.62)], 0.03, M['steel'], col))
    P.append(B.box('rplate', -2.672, -2.662, -0.26, 0.26, 0.70, 0.82, B.flat('plate', (0.8, 0.8, 0.76), 0.5), col))
    # side ladder near the rear, right side
    y = -(hw(1.8) + 0.06)
    for xx in (-2.30, -1.98):
        P.append(B.tube(f'lad{xx}', [(xx, y, 0.95), (xx, y, 2.66), (xx, -hw(2.72) - 0.02, 2.88), (xx, -0.86, 3.07)],
                        0.016, M['steel'], col))
    for k in range(9):
        zz = 1.08 + k * 0.2
        P.append(B.cyl(f'rung{k}', (-2.14, y, zz), 'x', 0.012, 0.32, 8, M['steel'], col))
    return P


def roof(M, col):
    P = []
    zr = 3.08
    pts_l, pts_r = [], []
    for s in (1, -1):
        y = s * 0.80
        P.append(B.tube(f'rr_side{s}', [(-2.12, y, zr), (1.62, y, zr)], 0.02, M['steel'], col))
        for xx in (-2.05, -1.0, 0.0, 1.0, 1.55):
            P.append(B.tube(f'rr_leg{s}{xx}', [(xx, y, zr), (xx, s * (hw(2.58) - 0.01), 2.60)], 0.016, M['steel'], col))
    for xx in np.linspace(-2.12, 1.62, 9):
        P.append(B.tube(f'rr_x{xx:.2f}', [(xx, -0.80, zr), (xx, 0.80, zr)], 0.014, M['steel'], col))
    P.append(B.tube('rr_front', [(1.62, -0.80, zr), (1.68, 0, zr + 0.02), (1.62, 0.80, zr)], 0.02, M['steel'], col))
    # light bar on the rack front
    for k, yy in enumerate((-0.54, -0.18, 0.18, 0.54)):
        h = B.box(f'lbar{k}', 1.56, 1.68, yy - 0.11, yy + 0.11, zr + 0.03, zr + 0.13, M['chassis'], col)
        B.bevel(h, 0.01, 1)
        P.append(h)
        P.append(B.box(f'lbl{k}', 1.68, 1.685, yy - 0.09, yy + 0.09, zr + 0.045, zr + 0.115, B.flat('lens_bar', (0.8, 0.82, 0.8), 0.1), col))
    # load: spare wheel, cans, crate, tarp roll, shovel
    sp = B.lathe('spare', [(0.25, -0.17), (0.40, -0.18), (0.49, -0.12), (0.50, 0.0), (0.49, 0.12), (0.40, 0.18),
                           (0.25, 0.17)], 'z', 40, (-1.35, 0.0, zr + 0.19), M['tyre'], col)
    B.smooth(sp, 40)
    P.append(sp)
    P.append(B.cyl('spare_rim', (-1.35, 0, zr + 0.19), 'z', 0.25, 0.30, 32, M['rim'], col))
    for k, yy in enumerate((0.42, 0.62)):
        jc = B.box(f'rcan{k}', 0.25, 0.73, yy - 0.085, yy + 0.085, zr + 0.02, zr + 0.36, M['shackle'], col)
        B.bevel(jc, 0.02, 2)
        P.append(jc)
    cr = B.box('crate', -0.15, 0.55, -0.70, 0.0, zr + 0.02, zr + 0.34, M['wood'], col)
    B.bevel(cr, 0.01, 1)
    P.append(cr)
    P.append(B.cyl('tarp', (0.95, -0.2, zr + 0.13), 'y', 0.11, 1.1, 16, M['canvas'], col))
    # snorkel on the right front corner
    sn = [(1.70, -1.12, 1.30), (1.80, -1.12, 1.85), (1.92, -1.05, 2.45), (1.98, -0.98, 2.85), (2.0, -0.95, 3.13)]
    P.append(B.tube('snorkel', sn, 0.045, M['plastic'], col, 14))
    hd = B.box('snork_head', 1.94, 2.12, -1.03, -0.87, 3.11, 3.25, M['plastic'], col)
    B.bevel(hd, 0.03, 2)
    P.append(hd)
    P.append(B.cyl('antenna', (1.2, 0.85, 3.75), 'z', 0.006, 1.3, 6, M['plastic'], col))
    return P


def build(col_name='Van'):
    col = B.coll(col_name)
    M = mats()
    body, door = body_shell(M, col)
    parts = window_parts(M, col)
    dg = door_glass(M, door, col)
    wheels = []
    for xa in (XF, XR):
        for s in (1, -1):
            wheels += tyre(f'tyre{xa}{s}', xa, s * TY, s, M, col)
    ch = chassis(M, col)
    fe = front_end(M, col)
    fs = flares_steps_mirrors(M, col)
    re_ = rear_end(M, col)
    rf = roof(M, col)
    return dict(body=body, door=door, M=M, col=col)


if __name__ == '__main__':
    B.reset()
    r = build()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'van.blend'))
    print('saved', len(bpy.data.objects), 'objects')
