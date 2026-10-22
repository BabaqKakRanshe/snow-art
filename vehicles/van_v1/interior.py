"""Cozy interior of the van concept: cab with the engine hump between the seats, saloon with a dinette, iron stove,
rear bed, pine-board walls over tufted vinyl, curtains, lamps.  build(M, col) -> list of night lights"""
import math
import bpy
from mathutils import Vector, Matrix
import vb as B
import van as V

ZF = 1.00            # saloon floor
ZC = 1.20            # cab platform over the front wheel wells


def twotone(name, split, low, low_d, high, high_d):
    if name in B.MATS:
        return B.MATS[name]
    m, nt, pb = B._base(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    def tnode(tex, dens):
        img = B._img(tex)
        mp = nt.nodes.new('ShaderNodeMapping')
        s = dens / img.size[0]
        mp.inputs['Scale'].default_value = (s, s, s)
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = img
        ti.interpolation = 'Closest'
        ti.projection = 'BOX'
        ti.projection_blend = 0.0
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        nt.links.new(mp.outputs['Vector'], ti.inputs['Vector'])
        return ti
    a, b = tnode(low, low_d), tnode(high, high_d)
    sx = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sx.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = split
    nt.links.new(sx.outputs['Z'], gt.inputs[0])
    # cab (x > 0.97): painted metal instead of the pine boards above the vinyl
    c = tnode('cab_paint', 90)
    cx = nt.nodes.new('ShaderNodeMath'); cx.operation = 'GREATER_THAN'; cx.inputs[1].default_value = 0.97
    nt.links.new(sx.outputs['X'], cx.inputs[0])
    hb = nt.nodes.new('ShaderNodeMix'); hb.data_type = 'RGBA'
    nt.links.new(cx.outputs[0], hb.inputs['Factor'])
    nt.links.new(b.outputs['Color'], hb.inputs[6]); nt.links.new(c.outputs['Color'], hb.inputs[7])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    nt.links.new(gt.outputs[0], mx.inputs['Factor'])
    nt.links.new(a.outputs['Color'], mx.inputs[6]); nt.links.new(hb.outputs[2], mx.inputs[7])
    nt.links.new(mx.outputs[2], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 0.75
    B.MATS[name] = m
    return m


def emissive(name, color, strength, base=(0.85, 0.8, 0.7)):
    if name in B.MATS:
        return B.MATS[name]
    m, nt, pb = B._base(name)
    pb.inputs['Base Color'].default_value = (*base, 1)
    pb.inputs['Emission Color'].default_value = (*color, 1)
    pb.inputs['Emission Strength'].default_value = strength
    pb.inputs['Roughness'].default_value = 0.4
    B.MATS[name] = m
    return m


def light(name, c, power, color=(1.0, 0.62, 0.32), radius=0.05, col=None, kind='POINT', target=None, angle=60):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
    l.data.energy = power
    l.data.color = color
    l.data.shadow_soft_size = radius
    if kind == 'SPOT':
        l.data.spot_size = math.radians(angle)
        l.data.spot_blend = 0.35
    l.location = c
    if target is not None:
        B.look(l, target)
    B.link(l, col)
    l['night'] = 1
    return l


def mats():
    return dict(
        vinyl=B.tex_box('vinyl_t', 'vinyl_tufted', 160, 0.7),
        cloth=B.tex_box('cloth', 'seat_cloth', 120, 0.9),
        pine=B.tex_box('pine', 'pine_boards', 130, 0.65),
        lino=B.tex_box('lino', 'linoleum', 90, 0.6),
        blanket=B.tex_box('blanket', 'blanket', 128, 0.95),
        curtain=B.tex_box('curtain', 'curtain', 128, 0.95),
        iron=B.tex_box('iron', 'iron', 90, 0.6, 0.3),
        steel=B.tex_box('steel', 'steel_worn', 90, 0.45, 0.6),
        dash=B.tex_box('chassis', 'chassis_dark', 70, 0.65, 0.2),
        head=B.tex_box('headliner', 'headliner', 90, 0.8),
        crate=B.tex_box('wood_box', 'wood_crate', 90, 0.7),
        canvas=B.tex_box('canvas', 'canvas', 90, 0.9),
        white=B.flat('enamel', (0.78, 0.80, 0.80), 0.3),
        red=B.flat('red_enamel', (0.52, 0.06, 0.04), 0.35),
        green=B.flat('thermos', (0.16, 0.30, 0.20), 0.35),
        black=B.flat('gauge_face', (0.02, 0.02, 0.02), 0.4),
        chrome=B.flat('chrome', (0.75, 0.76, 0.78), 0.2, 1.0),
        felt=B.flat('felt', (0.20, 0.19, 0.17), 1.0),
        glow=emissive('stove_glow', (1.0, 0.42, 0.10), 9.0, (0.3, 0.1, 0.03)),
        lamp=emissive('lamp_warm', (1.0, 0.70, 0.40), 5.0),
        dial=emissive('dial_glow', (1.0, 0.55, 0.2), 0.25, (0.07, 0.07, 0.065)),
    )


def seat(name, x0, x1, y0, y1, z, m, col):
    cu = B.box(name + '_c', x0, x1, y0, y1, z, z + 0.12, m['cloth'], col)
    bk = B.box(name + '_b', x0 - 0.12, x0 + 0.02, y0, y1, z + 0.12, z + 0.70, m['cloth'], col)
    bk.data.transform(Matrix.Translation((x0, 0, z + 0.12)) @ Matrix.Rotation(math.radians(-12), 4, 'Y') @
                      Matrix.Translation((-x0, 0, -(z + 0.12))))
    for o in (cu, bk):
        B.bevel(o, 0.035, 3, 40)
        B.smooth(o, 40)
    fr = B.box(name + '_f', x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05, ZC, z, m['dash'], col)
    return B.join([cu, bk, fr], name)


def bench(name, x0, x1, y0, y1, zs, back, m, col, height=0.48, base=None):
    """bench with the backrest on the x0 side (back=-1) or x1 side (back=+1)"""
    P = [B.box(name + '_base', x0 + 0.02, x1 - 0.02, y0, y1, base or ZF, zs - 0.10, m['pine'], col)]
    cu = B.box(name + '_c', x0, x1, y0, y1, zs - 0.10, zs, m['vinyl'], col)
    bx = (x0, x0 + 0.11) if back < 0 else (x1 - 0.11, x1)
    bk = B.box(name + '_k', *bx, y0, y1, zs, zs + height, m['vinyl'], col)
    for o in (cu, bk):
        B.bevel(o, 0.03, 3, 40)
        B.smooth(o, 40)
    return B.join(P + [cu, bk], name)


def curtains(name, x0, x1, z0, z1, side, m, col):
    """two gathered curtains at the edges of a side window; side = +1 left wall, -1 right wall"""
    y = side * (V.hw((z0 + z1) / 2) - 0.07)
    P = []
    w = x1 - x0
    for k, (a, b) in enumerate(((x0 - 0.05, x0 + w * 0.2), (x1 - w * 0.2, x1 + 0.05))):
        c = B.box(name + f'_{k}', a, b, *sorted((y, y - side * 0.04)), z0 - 0.05, z1 + 0.04, m['curtain'], col)
        B.bevel(c, 0.012, 2, 40)
        P.append(c)
    P.append(B.cyl(name + '_rod', ((x0 + x1) / 2, y + side * 0.0, z1 + 0.06), 'x', 0.007, w + 0.16, 8, m['steel'], col))
    return B.join(P, name)


def build(M, col):
    m = mats()
    lin = twotone('lining2', 1.70, 'vinyl_tufted', 160, 'pine_boards', 130)
    body = bpy.data.objects['Body']
    for i, mt in enumerate(body.data.materials):
        if mt.name.startswith('lining'):
            body.data.materials[i] = lin
    door = bpy.data.objects['SideDoor']
    for i, mt in enumerate(door.data.materials):
        if mt.name.startswith('lining'):
            door.data.materials[i] = lin
    night = []
    yi = lambda z: V.hw(z) - 0.04                      # inner wall half width
    yw = lambda z0, z1: min(V.hw(z0), V.hw(z1), V.hw((z0 + z1) / 2)) - 0.045   # safe half width over a height range

    # ---------------------------------------------------------------- floors, wells
    B.box('floor', -2.40, 0.98, -yw(0.955, ZF), yw(0.955, ZF), 0.955, ZF, m['lino'], col)
    B.box('cab_floor', 0.98, 2.30, -yw(0.955, ZC), yw(0.955, ZC), 0.955, ZC, m['dash'], col)
    B.box('cab_step', 0.90, 1.00, -yw(0.955, 1.1), yw(0.955, 1.1), 0.955, ZC - 0.1, m['steel'], col)
    for s in (1, -1):
        w = B.box(f'well{s}', V.XR - 0.68, V.XR + 0.68, *sorted((s * 0.70, s * yw(0.955, 1.24))), 0.955, 1.24, m['vinyl'], col)
        B.bevel(w, 0.03, 2)
    rug = B.box('rug', -1.30, 0.40, -0.40, 0.30, ZF, ZF + 0.012, m['blanket'], col)

    # ---------------------------------------------------------------- cab
    hump = B.box('hump', 1.02, 2.24, -0.30, 0.30, ZC, 1.72, m['vinyl'], col)
    B.bevel(hump, 0.09, 4, 40)
    B.smooth(hump, 40)
    fold = B.box('hump_blanket', 1.20, 1.75, -0.26, 0.26, 1.72, 1.77, m['blanket'], col)
    B.bevel(fold, 0.02, 2)
    seat('seatD', 1.12, 1.62, 0.34, 0.90, 1.56, m, col)
    seat('seatP', 1.12, 1.62, -0.90, -0.34, 1.56, m, col)
    dash = B.box('dash', 2.18, 2.40, -yw(1.63, 1.80) + 0.05, yw(1.63, 1.80) - 0.05, 1.63, 1.80, m['dash'], col)
    B.bevel(dash, 0.02, 2)
    for k, (yy, zz, r) in enumerate(((0.50, 1.73, 0.044), (0.68, 1.73, 0.044), (0.35, 1.755, 0.024), (0.83, 1.755, 0.024),
                                      (0.35, 1.70, 0.024), (0.83, 1.70, 0.024))):
        B.cyl(f'gface{k}', (2.177, yy, zz), 'x', r, 0.006, 24, m['dial'], col)
        B.lathe(f'gring{k}', [(r, -0.004), (r + 0.008, -0.004), (r + 0.008, 0.008), (r, 0.008)], 'x', 24,
                (2.177, yy, zz), m['chrome'], col)
        nd = B.box(f'needle{k}', 2.170, 2.172, yy - 0.002, yy + 0.002, zz, zz + r * 0.8, m['red'], col)
        nd.data.transform(Matrix.Translation((0, yy, zz)) @ Matrix.Rotation(0.6 - k * 0.35, 4, 'X') @
                          Matrix.Translation((0, -yy, -zz)))
    # steering wheel, column, levers, pedals, visors, mirror
    cw, rw = Vector((1.98, 0.62, 1.92)), 0.20
    tilt = Matrix.Rotation(math.radians(-55), 4, 'Y')
    ring = [tuple(cw + tilt @ Vector((0, rw * math.cos(2 * math.pi * k / 28), rw * math.sin(2 * math.pi * k / 28))))
            for k in range(29)]
    B.tube('steer', ring, 0.016, m['dash'], col, 8)
    for a in (0.0, math.pi):
        B.tube(f'spoke{a:.1f}', [tuple(cw), tuple(cw + tilt @ Vector((0, rw * math.cos(a), rw * math.sin(a))))], 0.012,
               m['dash'], col)
    B.tube('column', [tuple(cw), (2.24, 0.62, 1.58)], 0.03, m['dash'], col)
    for k, (yy, h) in enumerate(((0.10, 0.36), (-0.05, 0.26))):
        B.tube(f'lever{k}', [(1.82, yy, 1.70), (1.72, yy, 1.70 + h)], 0.012, m['steel'], col)
        B.cyl(f'knob{k}', (1.72, yy, 1.70 + h + 0.02), 'z', 0.03, 0.05, 12, m['black'], col)
    for k, yy in enumerate((0.48, 0.62, 0.76)):
        B.box(f'pedal{k}', 2.08, 2.12, yy - 0.04, yy + 0.04, 1.24, 1.36, m['steel'], col)
    for s in (1, -1):
        B.box(f'visor{s}', 1.94, 2.13, *sorted((s * 0.08, s * 0.66)), 2.60, 2.63, m['head'], col)
    B.box('imirror', 2.15, 2.18, -0.12, 0.12, 2.50, 2.57, m['dash'], col)

    # ---------------------------------------------------------------- saloon: dinette (left)
    bench('benchA', 0.02, 0.50, 0.36, yw(ZF, 1.95), 1.45, +1, m, col)
    bench('benchB', -1.34, -0.86, 0.36, yw(1.24, 1.95), 1.45, -1, m, col, base=1.24)
    tb = B.box('table', -0.80, -0.04, 0.40, yw(1.69, 1.72), 1.69, 1.72, m['pine'], col)
    B.bevel(tb, 0.008, 1)
    B.cyl('table_leg', (-0.42, 0.52, (ZF + 1.69) / 2), 'z', 0.025, 1.69 - ZF, 10, m['steel'], col)
    B.cyl('thermos', (-0.26, 0.86, 1.88), 'z', 0.045, 0.32, 14, m['green'], col)
    B.cyl('thermos_cap', (-0.26, 0.86, 2.06), 'z', 0.042, 0.05, 14, m['steel'], col)
    for k, (xx, yy, mc) in enumerate(((-0.52, 0.62, 'white'), (-0.34, 0.56, 'red'))):
        B.lathe(f'mug{k}', [(0.0, 0.0), (0.038, 0.0), (0.038, 0.09), (0.034, 0.09), (0.034, 0.006), (0.0, 0.006)], 'z',
                16, (xx, yy, 1.72), m[mc], col)
    B.box('book', -0.72, -0.56, 0.78, 0.98, 1.72, 1.745, m['red'], col)
    # pendant lamp over the table
    lp = B.lathe('lamp_shade', [(0.02, 0.10), (0.10, 0.0), (0.14, -0.08), (0.13, -0.085), (0.09, -0.005), (0.015, 0.09)],
                 'z', 24, (-0.42, 0.70, 2.48), m['red'], col)
    B.smooth(lp, 40)
    B.cyl('lamp_bulb', (-0.42, 0.70, 2.43), 'z', 0.035, 0.05, 12, m['lamp'], col)
    B.cyl('lamp_cord', (-0.42, 0.70, 2.72), 'z', 0.004, 0.40, 6, m['black'], col)
    night.append(light('L_pendant', (-0.42, 0.70, 2.36), 28, (1.0, 0.62, 0.30), 0.04, col))
    # map and calendar on the wall
    y = yw(1.92, 2.34)
    B.box('map', -1.30, -0.98, y - 0.004, y, 1.94, 2.34, B.tex_box('map', 'map', 330, 0.9), col)

    # ---------------------------------------------------------------- saloon: stove block (right)
    sx0, sx1 = -1.30, -0.44
    B.box('stove_base', sx0, sx1, -yw(1.24, 1.40), -0.58, 1.24, 1.40, m['pine'], col)
    st = B.box('stove', -1.10, -0.72, -0.98, -0.64, 1.40, 1.86, m['iron'], col)
    B.bevel(st, 0.015, 2)
    B.box('stove_door', -1.00, -0.82, -0.645, -0.630, 1.50, 1.70, m['iron'], col)
    B.box('stove_glow', -0.98, -0.84, -0.632, -0.628, 1.53, 1.67, m['glow'], col)
    zr = 2.80
    zr = 2.95
    B.cyl('stove_pipe', (-0.86, -0.82, (1.86 + zr + 0.42) / 2), 'z', 0.06, zr + 0.42 - 1.86, 16, m['iron'], col)
    B.cyl('pipe_cap', (-0.86, -0.82, zr + 0.48), 'z', 0.15, 0.12, 16, m['iron'], col, r2=0.03)
    B.box('heat_shield', sx0, sx1, -yw(1.40, 2.25), -yw(1.40, 2.25) + 0.012, 1.40, 2.25, m['steel'], col)
    k = B.lathe('kettle', [(0.0, 0.0), (0.10, 0.0), (0.105, 0.06), (0.09, 0.14), (0.03, 0.17), (0.0, 0.17)], 'z', 20,
                (-0.98, -0.80, 1.86), m['white'], col)
    B.smooth(k, 40)
    B.tube('kettle_spout', [(-0.89, -0.80, 1.92), (-0.82, -0.80, 2.0)], 0.012, m['white'], col)
    night.append(light('L_stove', (-0.90, -0.40, 1.60), 10, (1.0, 0.45, 0.15), 0.06, col))
    B.box('woodbox', -1.80, -1.42, -yw(1.24, 1.46), -0.70, 1.24, 1.46, m['crate'], col)
    for k_ in range(4):
        B.cyl(f'log{k_}', (-1.61, -0.82 - k_ * 0.06, 1.50), 'x', 0.035, 0.34, 8, B.tex_box('bark', 'wood_crate', 90, 0.9), col)
    for k_, yy in enumerate((-0.56, -0.44)):
        b1 = B.box(f'boot{k_}', -0.40, -0.18, yy - 0.05, yy + 0.05, ZF, ZF + 0.08, m['felt'], col)
        b2 = B.box(f'bootl{k_}', -0.40, -0.30, yy - 0.05, yy + 0.05, ZF + 0.08, ZF + 0.36, m['felt'], col)
        for o in (b1, b2):
            B.bevel(o, 0.02, 2)
    shelf = B.box('shelf_r', -1.95, -1.14, -yw(2.28, 2.30), -yw(2.28, 2.30) + 0.26, 2.28, 2.30, m['pine'], col)
    for k_, xx in enumerate((-1.85, -1.62, -1.40)):
        B.cyl(f'jar{k_}', (xx, -yw(2.28, 2.46) + 0.12, 2.38), 'z', 0.05, 0.16, 12, B.flat('jar', (0.55, 0.62, 0.55), 0.2), col)

    # ---------------------------------------------------------------- rear bed
    B.box('bed_base', -2.40, -1.38, -yw(1.24, 1.45), yw(1.24, 1.45), 1.24, 1.45, m['pine'], col)
    mt = B.box('mattress', -2.38, -1.40, -yw(1.45, 1.57), yw(1.45, 1.57), 1.45, 1.57, m['blanket'], col)
    B.bevel(mt, 0.04, 3)
    B.smooth(mt, 40)
    for s in (1, -1):
        pl = B.box(f'pillow{s}', -2.36, -2.05, *sorted((s * 0.15, s * 0.80)), 1.57, 1.68, m['white'], col)
        B.bevel(pl, 0.05, 3)
        B.smooth(pl, 40)
    sb = B.cyl('sleeping_bag', (-2.0, 0.60, 1.66), 'x', 0.09, 0.62, 16, m['canvas'], col)
    # shelves with bags along the walls under the gutter
    for s in (1, -1):
        y0 = s * yw(2.54, 2.74)
        B.box(f'shelf{s}', -2.35, 0.90 if s > 0 else -1.15, *sorted((y0, y0 - s * 0.26)), 2.54, 2.56, m['pine'], col)
        for k_, xx in enumerate((-2.2, -1.6, -1.0, 0.2)):
            if s < 0 and xx > -1.6:
                continue
            bg = B.box(f'bag{s}{k_}', xx, xx + 0.42, *sorted((y0 - s * 0.02, y0 - s * 0.24)), 2.56, 2.72,
                       [m['canvas'], m['red'], m['blanket'], m['canvas']][k_ % 4], col)
            B.bevel(bg, 0.04, 2)
    # curtains
    for x0, x1 in V.WIN_L[1:]:
        curtains('curL', x0, x1, V.ZW0, V.ZW1, 1, m, col)
    for x0, x1 in V.WIN_R[1:]:
        curtains('curR', x0, x1, V.ZW0, V.ZW1, -1, m, col)
    # ceiling lights, first aid, extinguisher, coats
    for k_, xx in enumerate((0.40, -1.75)):
        B.cyl(f'dome{k_}', (xx, 0.0, 2.895), 'z', 0.10, 0.04, 20, m['lamp'], col)
        night.append(light(f'L_dome{k_}', (xx, 0.0, 2.77), 10, (1.0, 0.72, 0.45), 0.08, col))
    y = -yw(2.00, 2.22)
    B.box('aid', 0.68, 0.94, y, y + 0.08, 2.00, 2.22, m['white'], col)
    B.box('aid_c1', 0.775, 0.845, y + 0.08, y + 0.084, 2.03, 2.19, m['red'], col)
    B.box('aid_c2', 0.73, 0.89, y + 0.08, y + 0.084, 2.08, 2.14, m['red'], col)
    B.cyl('extinguisher', (0.80, -0.80, ZF + 0.22), 'z', 0.06, 0.44, 14, m['red'], col)
    for k_, xx in enumerate((-1.95, -1.65)):
        c = B.box(f'coat{k_}', xx - 0.14, xx + 0.14, -yw(1.70, 2.42) + 0.01, -yw(1.70, 2.42) + 0.17, 1.70, 2.42,
                  [B.flat('coat1', (0.12, 0.16, 0.22), 0.9), B.flat('coat2', (0.33, 0.26, 0.14), 0.9)][k_], col)
        B.bevel(c, 0.05, 3)
        B.smooth(c, 40)
    # cab dash glow
    night.append(light('L_dash', (2.05, 0.6, 1.95), 1.2, (1.0, 0.6, 0.3), 0.05, col))
    return night
