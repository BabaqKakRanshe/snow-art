"""Shared cozy-interior and exterior parts for the vehicle concepts."""
import math
from mathutils import Vector, Matrix
import vlib as V


def M():
    return dict(
        quilt=V.mat('quilt', 'quilt', 192, 0.75),
        wood=V.mat('wood', 'wood', 64, 0.7),
        iron=V.mat('iron', 'iron', 50, 0.6, 0.3),
        metal=V.mat('metal', 'metal', 50, 0.4, 0.6),
        dark=V.mat('paint_dark', 'paint_dark', 50, 0.6),
        mat=V.mat('floormat', 'floormat', 64, 0.9),
        blanket=V.mat('blanket', 'blanket', 128, 0.95),
        curtain=V.mat('curtain', 'curtain', 64, 0.95),
        canvas=V.mat('canvas', 'canvas', 50, 0.9),
        mapm=V.mat('map', 'map', 200, 0.9, px=128),
        rubber=V.mat('rubber', 'rubber', 60, 0.85),
        glow=V.emissive('stove_glow', (1.0, 0.40, 0.10), 2.0, 9.0, (0.3, 0.1, 0.03)),
        lamp=V.emissive('lamp_warm', (1.0, 0.68, 0.38), 0.0, 9.0, (0.9, 0.85, 0.7)),
        head=V.emissive('lens_head', (1.0, 0.86, 0.62), 0.0, 14.0),
        tail=V.emissive('lens_tail', (1.0, 0.04, 0.02), 0.0, 5.0, (0.5, 0.05, 0.04)),
        amber=V.emissive('lens_amber', (1.0, 0.42, 0.05), 0.0, 4.0, (0.7, 0.35, 0.05)),
        work=V.emissive('lens_work', (1.0, 0.92, 0.75), 0.0, 10.0),
        red=V.flatcol('red_enamel', (0.55, 0.06, 0.04), 0.4),
        enamel=V.flatcol('enamel', (0.75, 0.78, 0.8), 0.35),
        green=V.flatcol('green_thermos', (0.18, 0.32, 0.2), 0.4),
    )


def light(name, c, power, color=(1.0, 0.62, 0.32), radius=0.05, kind='point', target=None, angle=60, col=None):
    if kind == 'point':
        l = V.point(name, c, power, color, radius, col)
    else:
        l = V.spot(name, c, target, power, angle, color, 0.35, col)
        l.data.shadow_soft_size = radius
    l['veh'] = 1
    return l


def bench(name, x0, x1, y0, y1, zf, wall, m, seat=0.42, back=True, blanket=None, col=None):
    """bench along a side wall; wall = +1 (wall at y1) or -1 (wall at y0)"""
    parts = [V.box(name + '_b', x0, x1, y0, y1, zf, zf + seat - 0.08, m['wood'], col)]
    cu = V.box(name + '_c', x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, zf + seat - 0.08, zf + seat + 0.02, m['quilt'], col)
    V.bevel(cu, 0.03, 2, 40)
    parts.append(cu)
    if back:
        yb = (y1 - 0.09, y1) if wall > 0 else (y0, y0 + 0.09)
        bk = V.box(name + '_k', x0 + 0.02, x1 - 0.02, *yb, zf + seat + 0.06, zf + seat + 0.5, m['quilt'], col)
        V.bevel(bk, 0.03, 2, 40)
        parts.append(bk)
    if blanket:
        bx0, bx1 = blanket
        bl = V.box(name + '_bl', bx0, bx1, y0 - 0.03, y1 - 0.06 if wall > 0 else y1 + 0.02, zf + seat - 0.12,
                   zf + seat + 0.05, m['blanket'], col)
        V.bevel(bl, 0.025, 2, 40)
        parts.append(bl)
        roll = V.cyl(name + '_rl', ((bx0 + bx1) / 2 - 0.35, (y0 + y1) / 2, zf + seat + 0.11), 'y', 0.09, y1 - y0 - 0.1, 10,
                     m['blanket'], col)
        parts.append(roll)
    return V.join(parts, name)


def stove(name, cx, cy, zf, z_roof_out, m, door=(-1, 0), col=None, pipe_top=0.55):
    """small iron stove (буржуйка) with a glowing door, kettle and a pipe through the roof; door = facing dir (dx, dy)"""
    w, d, h = 0.36, 0.38, 0.52
    parts = [V.box(name + '_sheet', cx - 0.3, cx + 0.3, cy - 0.3, cy + 0.3, zf, zf + 0.01, m['metal'], col)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(V.box(name + f'_leg{sx}{sy}', cx + sx * (w / 2 - 0.04) - 0.02, cx + sx * (w / 2 - 0.04) + 0.02,
                               cy + sy * (d / 2 - 0.04) - 0.02, cy + sy * (d / 2 - 0.04) + 0.02, zf, zf + 0.14, m['iron'], col))
    body = V.box(name + '_body', cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, zf + 0.14, zf + 0.14 + h, m['iron'], col)
    V.bevel(body, 0.015, 1, 40)
    parts.append(body)
    dx, dy = door
    fx, fy = cx + dx * (w / 2 + 0.006), cy + dy * (d / 2 + 0.006)
    if dx:
        gw = V.box(name + '_glow', fx - 0.01, fx + 0.01, cy - 0.09, cy + 0.09, zf + 0.26, zf + 0.40, m['glow'], col)
        fr = V.box(name + '_door', fx - 0.012, fx + 0.012, cy - 0.13, cy + 0.13, zf + 0.22, zf + 0.44, m['iron'], col)
    else:
        gw = V.box(name + '_glow', cx - 0.09, cx + 0.09, fy - 0.01, fy + 0.01, zf + 0.26, zf + 0.40, m['glow'], col)
        fr = V.box(name + '_door', cx - 0.13, cx + 0.13, fy - 0.012, fy + 0.012, zf + 0.22, zf + 0.44, m['iron'], col)
    fr = V.bdiff(fr, [V.box('c', cx - 0.5 if not dx else fx - 0.05, cx + 0.5 if not dx else fx + 0.05,
                             cy - 0.09 if dx else fy - 0.05, cy + 0.09 if dx else fy + 0.05, zf + 0.26, zf + 0.40)])
    parts += [gw, fr]
    top = zf + 0.14 + h
    parts.append(V.cyl(name + '_pipe', (cx + 0.06, cy, (top + z_roof_out + pipe_top) / 2), 'z', 0.058,
                       z_roof_out + pipe_top - top, 12, m['iron'], col))
    parts.append(V.cyl(name + '_cap', (cx + 0.06, cy, z_roof_out + pipe_top + 0.06), 'z', 0.14, 0.12, 12, m['iron'], col,
                       r2=0.02))
    k = V.cyl(name + '_kettle', (cx - 0.08, cy, top + 0.08), 'z', 0.09, 0.15, 12, m['enamel'], col, r2=0.07)
    parts.append(k)
    parts.append(V.cyl(name + '_spout', (cx - 0.19, cy, top + 0.1), 'x', 0.015, 0.1, 6, m['enamel'], col))
    glow_at = (fx + dx * 0.25, fy + dy * 0.25, zf + 0.33)
    return V.join(parts, name), glow_at


def table(name, x0, x1, y0, y1, zt, zf, m, col=None, items=True):
    parts = [V.box(name + '_top', x0, x1, y0, y1, zt - 0.03, zt, m['wood'], col)]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts.append(V.cyl(name + '_leg', (cx, cy, (zt + zf) / 2), 'z', 0.025, zt - zf, 8, m['metal'], col))
    if items:
        parts.append(V.cyl(name + '_th', (cx + 0.12, cy + 0.08, zt + 0.15), 'z', 0.045, 0.30, 10, m['green'], col))
        parts.append(V.cyl(name + '_thc', (cx + 0.12, cy + 0.08, zt + 0.32), 'z', 0.04, 0.05, 10, m['metal'], col))
        for i, (ox, oy) in enumerate(((-0.1, -0.08), (0.02, -0.14))):
            parts.append(V.cyl(name + f'_mug{i}', (cx + ox, cy + oy, zt + 0.045), 'z', 0.038, 0.09, 10,
                               m['enamel'] if i else m['red'], col))
        parts.append(V.box(name + '_book', cx - 0.2, cx - 0.04, cy + 0.02, cy + 0.2, zt, zt + 0.03, m['red'], col))
    return V.join(parts, name)


def lantern(name, c, m, col=None, hang=0.25):
    x, y, z = c
    parts = [V.cyl(name + '_base', (x, y, z - 0.1), 'z', 0.07, 0.04, 10, m['red'], col),
             V.cyl(name + '_gl', (x, y, z), 'z', 0.05, 0.16, 10, m['lamp'], col),
             V.cyl(name + '_top', (x, y, z + 0.1), 'z', 0.07, 0.05, 10, m['red'], col, r2=0.03),
             V.cyl(name + '_wire', (x, y, z + 0.12 + hang / 2), 'z', 0.006, hang, 4, m['iron'], col)]
    for a in range(4):
        aa = a * math.pi / 2
        parts.append(V.box(name + f'_g{a}', x + 0.06 * math.cos(aa) - 0.005, x + 0.06 * math.cos(aa) + 0.005,
                           y + 0.06 * math.sin(aa) - 0.005, y + 0.06 * math.sin(aa) + 0.005, z - 0.09, z + 0.09,
                           m['red'], col))
    ob = V.join(parts, name)
    lt = light(name + '_L', (x, y, z), 14, (1.0, 0.62, 0.30), 0.04, col=col)
    return ob, lt


def dome(name, c, m, col=None, power=18):
    x, y, z = c
    d = V.cyl(name, (x, y, z - 0.03), 'z', 0.12, 0.05, 12, m['lamp'], col, r2=0.1)
    lt = light(name + '_L', (x, y, z - 0.12), power, (1.0, 0.72, 0.45), 0.08, col=col)
    return d, lt


def curtains(name, axis_pos, side, u0, u1, z0, z1, m, along='x', col=None):
    """two gathered curtain panels at the edges of a window on a wall at y = axis_pos (along='x') or
    x = axis_pos (along='y'); side = direction into the room (+1 / -1)"""
    parts = []
    w = (u1 - u0)
    for k, (a, b) in enumerate(((u0 - 0.06, u0 + w * 0.22), (u1 - w * 0.22, u1 + 0.06))):
        if along == 'x':
            p = V.box(name + f'_{k}', a, b, axis_pos + side * 0.012, axis_pos + side * 0.05, z0 - 0.06, z1 + 0.03,
                      m['curtain'], col)
        else:
            p = V.box(name + f'_{k}', axis_pos + side * 0.012, axis_pos + side * 0.05, a, b, z0 - 0.06, z1 + 0.03,
                      m['curtain'], col)
        parts.append(p)
    if along == 'x':
        parts.append(V.cyl(name + '_rod', ((u0 + u1) / 2, axis_pos + side * 0.03, z1 + 0.05), 'x', 0.008, w + 0.2, 6,
                           m['metal'], col))
    else:
        parts.append(V.cyl(name + '_rod', (axis_pos + side * 0.03, (u0 + u1) / 2, z1 + 0.05), 'y', 0.008, w + 0.2, 6,
                           m['metal'], col))
    return V.join(parts, name)


def jerrycan(name, c, m, col=None, rotz=0.0, colr=None):
    x, y, z = c
    mc = colr or m['red']
    b = V.box(name, -0.085, 0.085, -0.175, 0.175, 0, 0.47, mc, col)
    V.bevel(b, 0.02, 1, 40)
    h = V.box(name + '_h', -0.03, 0.03, -0.12, 0.12, 0.47, 0.52, mc, col)
    ob = V.join([b, h], name)
    ob.rotation_euler = (0, 0, rotz)
    ob.location = (x, y, z)
    return ob


def rack(name, x0, x1, y0, y1, zf, ztop, m, col=None):
    """shelf rack with jerrycans below, crates and a radio on top"""
    parts = []
    for xx in (x0, x1 - 0.03):
        for yy in (y0, y1 - 0.03):
            parts.append(V.box(name + f'_p{xx:.2f}{yy:.2f}', xx, xx + 0.03, yy, yy + 0.03, zf, ztop, m['metal'], col))
    zs = zf + 0.6
    parts.append(V.box(name + '_s1', x0, x1, y0, y1, zs - 0.02, zs, m['wood'], col))
    parts.append(V.box(name + '_s2', x0, x1, y0, y1, ztop - 0.02, ztop, m['wood'], col))
    for i in range(int((x1 - x0) / 0.2)):
        parts.append(jerrycan(name + f'_jc{i}', (x0 + 0.12 + i * 0.2, (y0 + y1) / 2, zf + 0.01), m, col,
                              colr=m['red'] if i % 2 == 0 else V.flatcol('olive', (0.2, 0.24, 0.14), 0.6)))
    parts.append(V.box(name + '_crate', x0 + 0.04, x0 + 0.45, y0 + 0.04, y1 - 0.04, zs, zs + 0.3, m['wood'], col))
    rd = V.box(name + '_radio', x1 - 0.42, x1 - 0.05, y0 + 0.06, y1 - 0.06, zs, zs + 0.24,
               V.flatcol('radio', (0.22, 0.26, 0.2), 0.5), col)
    parts.append(rd)
    parts.append(V.box(name + '_dial', x1 - 0.30, x1 - 0.16, y0 + 0.04, y0 + 0.06, zs + 0.08, zs + 0.18, m['lamp'], col))
    return V.join(parts, name)


def coats(name, x, y, z, side, m, col=None, n=2, along='x'):
    """parkas on hooks; along='x': wall at y (side = +1 wall on +y), along='y': wall at x (side = +1 wall on +x)"""
    parts = []
    cols = [V.flatcol('coat1', (0.12, 0.16, 0.22), 0.9), V.flatcol('coat2', (0.32, 0.26, 0.14), 0.9),
            V.flatcol('coat3', (0.5, 0.12, 0.08), 0.9)]
    for i in range(n):
        if along == 'x':
            xx = x + i * 0.3
            hook = V.box(name + f'_hk{i}', xx - 0.01, xx + 0.01, *sorted((y - side * 0.06, y)), z, z + 0.02, m['metal'], col)
            cb = V.box(name + f'_c{i}', xx - 0.14, xx + 0.14, *sorted((y - side * 0.17, y - side * 0.03)), z - 0.75,
                       z - 0.03, cols[i % 3], col)
        else:
            yy = y + i * 0.3
            hook = V.box(name + f'_hk{i}', *sorted((x - side * 0.06, x)), yy - 0.01, yy + 0.01, z, z + 0.02, m['metal'], col)
            cb = V.box(name + f'_c{i}', *sorted((x - side * 0.17, x - side * 0.03)), yy - 0.14, yy + 0.14, z - 0.75,
                       z - 0.03, cols[i % 3], col)
        V.bevel(cb, 0.04, 2, 40)
        parts += [hook, cb]
    return V.join(parts, name)


def first_aid(name, x0, x1, y0, y1, z0, z1, m, col=None, facing='y'):
    b = V.box(name, x0, x1, y0, y1, z0, z1, V.flatcol('white_box', (0.85, 0.86, 0.84), 0.5), col)
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    s = 0.035
    if facing == 'y':
        yy = (y0 - 0.004, y1 + 0.004)
        c1 = V.box(name + '_c1', cx - s * 2.5, cx + s * 2.5, *yy, cz - s / 2 * 2, cz + s / 2 * 2, m['red'], col)
        c2 = V.box(name + '_c2', cx - s, cx + s, *yy, cz - s * 2.5, cz + s * 2.5, m['red'], col)
    else:
        xx = (x0 - 0.004, x1 + 0.004)
        c1 = V.box(name + '_c1', *xx, cy - s * 2.5, cy + s * 2.5, cz - s, cz + s, m['red'], col)
        c2 = V.box(name + '_c2', *xx, cy - s, cy + s, cz - s * 2.5, cz + s * 2.5, m['red'], col)
    return V.join([b, c1, c2], name)


def wall_map(name, x0, x1, y0, y1, z0, z1, m, col=None):
    return V.box(name, x0, x1, y0, y1, z0, z1, m['mapm'], col)


def extinguisher(name, c, m, col=None):
    x, y, z = c
    a = V.cyl(name, (x, y, z + 0.2), 'z', 0.06, 0.4, 10, m['red'], col)
    b = V.cyl(name + '_t', (x, y, z + 0.44), 'z', 0.02, 0.08, 6, m['dark'], col)
    return V.join([a, b], name)


def ladder(name, x_out, y0, y1, z_top, z_bot, m, col=None, steps=3, depth=0.25):
    parts = []
    for yy in (y0, y1 - 0.04):
        parts.append(V.box(name + f'_r{yy:.2f}', x_out - depth, x_out - depth + 0.04, yy, yy + 0.04, z_bot, z_top, m['metal'], col))
    for i in range(steps):
        z = z_bot + (z_top - z_bot) * (i + 0.5) / steps
        parts.append(V.box(name + f'_s{i}', x_out - depth - 0.02, x_out - depth + 0.14, y0, y1, z - 0.02, z + 0.02,
                           m['metal'], col))
    return V.join(parts, name)


def mirror(name, base, tip, m, col=None):
    bx, by, bz = base
    tx, ty, tz = tip
    arm = V.box(name + '_a', min(bx, tx) - 0.015, max(bx, tx) + 0.015, min(by, ty), max(by, ty), bz - 0.015, bz + 0.015,
                m['dark'], col)
    gl = V.box(name + '_m', tx - 0.03, tx + 0.03, ty - 0.11, ty + 0.11, tz - 0.17, tz + 0.17, m['dark'], col)
    V.bevel(gl, 0.02, 1, 40)
    vert = V.box(name + '_v', tx - 0.012, tx + 0.012, ty - 0.012, ty + 0.012, min(bz, tz - 0.17), bz, m['dark'], col)
    return V.join([arm, gl, vert], name)


def steering(name, c, r, tilt, m, col=None):
    """steering wheel as a 12-segment ring, tilted back by `tilt` degrees about Y"""
    x, y, z = c
    parts = []
    n = 12
    for k in range(n):
        a = 2 * math.pi * k / n
        seg = V.box(name + f'_{k}', -0.016, 0.016, -0.016, 0.016, -r * math.pi / n, r * math.pi / n, m['dark'], col)
        seg.data.transform(Matrix.Rotation(a, 4, 'X') @ Matrix.Translation((0, 0, 0)))
        seg.data.transform(Matrix.Translation((0, r * math.cos(a + math.pi / 2), r * math.sin(a + math.pi / 2))))
        parts.append(seg)
    parts.append(V.box(name + '_sp', -0.015, 0.015, -r, r, -0.015, 0.015, m['dark'], col))
    parts.append(V.cyl(name + '_hub', (0, 0, 0), 'x', 0.05, 0.05, 8, m['dark'], col))
    ob = V.join(parts, name)
    ob.data.transform(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(-tilt), 4, 'Y'))
    return ob


def seat(name, x0, x1, y0, y1, zf, m, col=None, mq=None):
    mq = mq or m['quilt']
    s = V.box(name + '_s', x0, x1, y0, y1, zf, zf + 0.42, mq, col)
    b = V.box(name + '_b', x0 - 0.12, x0 + 0.02, y0, y1, zf + 0.42, zf + 1.0, mq, col)
    b.data.transform(Matrix.Translation((x0, 0, zf + 0.42)) @ Matrix.Rotation(math.radians(-10), 4, 'Y') @
                     Matrix.Translation((-x0, 0, -(zf + 0.42))))
    for o in (s, b):
        V.bevel(o, 0.04, 2, 40)
    return V.join([s, b], name)


def smoke(name, c, col=None, n=6):
    """puffs rising from a stove pipe"""
    m = V.flatcol('smoke', (0.62, 0.64, 0.68), 1.0, alpha=0.32)
    parts = []
    x, y, z = c
    for i in range(n):
        r = 0.09 + i * 0.05
        parts.append(V.ico(name + f'_{i}', (x - i * 0.16, y + 0.03 * math.sin(i), z + 0.12 + i * 0.2), r, 1, m, col))
    return V.join(parts, name)


def pseat(name, x0, x1, y0, y1, zf, back, m, col=None, seat=0.44, height=0.55):
    """passenger seat / double seat with the backrest on the x0 side (back=-1, faces +x) or x1 side (back=+1, faces -x)"""
    base = V.box(name + '_f', x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05, zf, zf + seat - 0.1, m['metal'], col)
    cu = V.box(name + '_c', x0, x1, y0, y1, zf + seat - 0.1, zf + seat, m['quilt'], col)
    bx = (x0, x0 + 0.12) if back < 0 else (x1 - 0.12, x1)
    bk = V.box(name + '_k', *bx, y0, y1, zf + seat, zf + seat + height, m['quilt'], col)
    for o in (cu, bk):
        V.bevel(o, 0.035, 2, 40)
    return V.join([base, cu, bk], name)


def shelf_bags(name, x0, x1, y0, y1, z, m, col=None, n=3):
    parts = [V.box(name + '_s', x0, x1, y0, y1, z - 0.02, z, m['metal'], col)]
    step = (x1 - x0) / n
    cols = [m['canvas'], V.flatcol('bagblue', (0.12, 0.2, 0.35), 0.9), m['red']]
    for i in range(n):
        b = V.box(name + f'_b{i}', x0 + i * step + 0.05, x0 + (i + 1) * step - 0.08, y0 + 0.02, y1 - 0.02, z,
                  z + 0.18 + 0.06 * (i % 2), cols[i % 3], col)
        V.bevel(b, 0.04, 2, 40)
        parts.append(b)
    return V.join(parts, name)
