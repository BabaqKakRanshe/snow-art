"""Cozy kit for the UAZ saloon: wood stove with a flue through the roof, heat shield, wood box with logs,
table with thermos / mugs / book, pendant lamp, curtains on the saloon windows, crates, jerrycan, bags,
felt boots, first-aid kit, extinguisher.  Every face carries a 'zone' attribute for the Props atlas.
Frame: x forward, y left, z up; floor 0.716, partition x 0.888, rear wall x -2.09, walls |y| ~0.90."""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

Z_IRON, Z_GLOW, Z_WOOD, Z_LOG, Z_CLOTH, Z_LAMP, Z_BULB, Z_CRATE, Z_CAN, Z_BAG, Z_KIT, Z_FELT, Z_STEEL = range(20, 33)
FLOOR = 0.716
PROPS = []
LIGHTS = []


def _obj(name, bm, zone):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    a = me.attributes.new('zone', 'FLOAT', 'FACE')
    a.data.foreach_set('value', np.full(len(me.polygons), zone, np.float32))
    o['orig'] = name
    PROPS.append(o)
    return o


def box(name, x0, x1, y0, y1, z0, z1, zone, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES')
    return _obj(name, bm, zone)


def cyl(name, c, axis, r, length, zone, seg=10, r2=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2,
                          depth=length)
    R = {'z': Matrix.Identity(3), 'x': Matrix.Rotation(math.pi / 2, 3, 'Y'), 'y': Matrix.Rotation(math.pi / 2, 3, 'X')}[axis]
    for v in bm.verts:
        v.co = R @ v.co + Vector(c)
    return _obj(name, bm, zone)


def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = objs[0]
    o.name = name
    o['orig'] = name
    for x in objs[1:]:
        if x in PROPS:
            PROPS.remove(x)
    return o


def curtain(name, x0, x1, side, z_top, z_bot, wall_y, folds=5):
    """a gathered curtain bundle: zig-zag strip hanging from z_top to z_bot, against the wall"""
    bm = bmesh.new()
    n = folds * 2 + 1
    ys = wall_y - side * 0.035
    rows = []
    for zz in (z_top, (z_top + z_bot) / 2, z_bot):
        row = []
        for i in range(n):
            x = x0 + (x1 - x0) * i / (n - 1)
            dy = (0.022 if i % 2 else 0.0) * (1.0 if zz > z_bot + 0.01 else 0.8)
            row.append(bm.verts.new((x, ys - side * dy, zz)))
        rows.append(row)
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for i in range(n - 1):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
    o = _obj(name, bm, Z_CLOTH)
    m = o.modifiers.new('solid', 'SOLIDIFY')
    m.thickness = 0.008
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def build(windows, wall_y=0.90, ceil_z=1.97, roof_z=2.05):
    """windows: list of (x0, x1, side, z_bot, z_top) of the saloon side panes"""
    # --- wood stove, rear left corner
    sx0, sx1, sy0, sy1 = -2.03, -1.71, 0.42, 0.76
    legs = [cyl(f'stove_leg{i}', (x, y, FLOOR + 0.05), 'z', 0.012, 0.10, Z_IRON, 6)
            for i, (x, y) in enumerate([(sx0 + 0.03, sy0 + 0.03), (sx1 - 0.03, sy0 + 0.03), (sx0 + 0.03, sy1 - 0.03), (sx1 - 0.03, sy1 - 0.03)])]
    body = box('stove_body', sx0, sx1, sy0, sy1, FLOOR + 0.10, FLOOR + 0.52, Z_IRON, bevel=0.012)
    top = box('stove_top', sx0 - 0.015, sx1 + 0.015, sy0 - 0.015, sy1 + 0.015, FLOOR + 0.52, FLOOR + 0.545, Z_IRON)
    door = box('stove_door', sx1, sx1 + 0.012, sy0 + 0.07, sy1 - 0.07, FLOOR + 0.20, FLOOR + 0.42, Z_IRON)
    glow = box('stove_glow', sx1 + 0.012, sx1 + 0.016, sy0 + 0.11, sy1 - 0.11, FLOOR + 0.27, FLOOR + 0.36, Z_GLOW)
    hx, hy = (sx0 + sx1) / 2 - 0.05, (sy0 + sy1) / 2 + 0.04
    pipe = cyl('stove_pipe', (hx, hy, (FLOOR + 0.545 + roof_z + 0.22) / 2), 'z', 0.055, roof_z + 0.22 - FLOOR - 0.545, Z_IRON, 10)
    cap = cyl('stove_cap', (hx, hy, roof_z + 0.27), 'z', 0.11, 0.07, Z_IRON, 10, r2=0.02)
    collar = cyl('stove_collar', (hx, hy, ceil_z - 0.01), 'z', 0.10, 0.02, Z_IRON, 10)
    kettle = cyl('kettle', (sx0 + 0.09, sy1 - 0.10, FLOOR + 0.62), 'z', 0.075, 0.13, Z_STEEL, 10, r2=0.05)
    spout = cyl('kettle_spout', (sx0 + 0.17, sy1 - 0.10, FLOOR + 0.63), 'x', 0.012, 0.09, Z_STEEL, 6)
    stove = join([body, top, door, pipe, cap, collar, kettle, spout] + legs, 'Stove')
    glow = join([glow], 'StoveGlow')
    shield = box('heat_shield', -2.05, -1.62, wall_y - 0.075, wall_y - 0.065, FLOOR + 0.12, FLOOR + 0.95, Z_STEEL)
    LIGHTS.append(('stove', (sx1 + 0.10, (sy0 + sy1) / 2, FLOOR + 0.32), 'POINT', 14.0, (1.0, 0.45, 0.12)))
    # --- wood box with logs
    wb = box('woodbox', -1.62, -1.34, 0.50, 0.84, FLOOR, FLOOR + 0.24, Z_WOOD, bevel=0.006)
    logs = [cyl(f'log{i}', (-1.48, 0.55 + 0.075 * i, FLOOR + 0.28 + 0.06 * (i % 2)), 'x', 0.035, 0.30, Z_LOG, 8)
            for i in range(4)]
    join([wb] + logs, 'WoodBox')
    # --- felt boots by the stove
    boots = []
    for i, y in enumerate((0.22, 0.32)):
        boots.append(box(f'boot{i}', -1.72, -1.62, y - 0.04, y + 0.04, FLOOR, FLOOR + 0.28, Z_FELT, bevel=0.012))
        boots.append(box(f'bootf{i}', -1.66, -1.52, y - 0.04, y + 0.04, FLOOR, FLOOR + 0.07, Z_FELT, bevel=0.01))
    join(boots, 'FeltBoots')
    # --- right rear corner: crates, jerrycan, bags
    c1 = box('crate1', -2.04, -1.66, -0.80, -0.44, FLOOR, FLOOR + 0.30, Z_CRATE, bevel=0.006)
    c2 = box('crate2', -2.00, -1.70, -0.76, -0.48, FLOOR + 0.30, FLOOR + 0.54, Z_CRATE, bevel=0.006)
    can = box('jerrycan', -1.62, -1.46, -0.82, -0.66, FLOOR, FLOOR + 0.46, Z_CAN, bevel=0.015)
    can_c = cyl('jerrycan_cap', (-1.50, -0.70, FLOOR + 0.49), 'z', 0.02, 0.05, Z_CAN, 6)
    bag = box('bag1', -1.98, -1.66, -0.78, -0.46, FLOOR + 0.54, FLOOR + 0.70, Z_BAG, bevel=0.04)
    join([c1, c2, can, can_c, bag], 'Cargo')
    # --- table between the facing seats on the left, with a thermos, mugs and a book
    tx0, tx1, ty0, ty1, tz = -0.22, 0.18, 0.40, 0.86, FLOOR + 0.64
    tbl = box('table_top', tx0, tx1, ty0, ty1, tz - 0.025, tz, Z_WOOD, bevel=0.005)
    leg = cyl('table_leg', ((tx0 + tx1) / 2, ty0 + 0.06, (FLOOR + tz) / 2), 'z', 0.02, tz - FLOOR, Z_STEEL, 8)
    th = cyl('thermos', (tx0 + 0.08, ty1 - 0.10, tz + 0.13), 'z', 0.04, 0.26, Z_STEEL, 10)
    thc = cyl('thermos_cap', (tx0 + 0.08, ty1 - 0.10, tz + 0.285), 'z', 0.042, 0.05, Z_CAN, 10)
    m1 = cyl('mug1', (tx1 - 0.10, ty0 + 0.12, tz + 0.045), 'z', 0.035, 0.09, Z_LAMP, 10)
    m2 = cyl('mug2', (tx1 - 0.08, ty1 - 0.14, tz + 0.045), 'z', 0.035, 0.09, Z_STEEL, 10)
    book = box('book', tx0 + 0.14, tx0 + 0.30, ty0 + 0.16, ty0 + 0.28, tz, tz + 0.03, Z_KIT)
    join([tbl, leg, th, thc, m1, m2, book], 'Table')
    # --- pendant lamp over the table
    lx, ly = (tx0 + tx1) / 2, (ty0 + ty1) / 2 - 0.05
    cord = cyl('lamp_cord', (lx, ly, (ceil_z + 1.80) / 2), 'z', 0.004, ceil_z - 1.80, Z_STEEL, 4)
    shade = cyl('lamp_shade', (lx, ly, 1.77), 'z', 0.15, 0.10, Z_LAMP, 14, r2=0.03, cap=False)
    sh_m = shade.modifiers.new('solid', 'SOLIDIFY')
    sh_m.thickness = 0.006
    for x in bpy.context.selected_objects:
        x.select_set(False)
    shade.select_set(True)
    bpy.context.view_layer.objects.active = shade
    bpy.ops.object.modifier_apply(modifier=sh_m.name)
    join([cord, shade], 'Lamp')
    bulb = cyl('lamp_bulb', (lx, ly, 1.735), 'z', 0.03, 0.05, Z_BULB, 8)
    join([bulb], 'LampBulb')
    LIGHTS.append(('lamp', (lx, ly, 1.70), 'POINT', 22.0, (1.0, 0.70, 0.40)))
    # --- curtains: a gathered bundle at both ends of every saloon pane, and a rod
    cur = []
    for k, (x0, x1, side, zb, zt) in enumerate(windows):
        wy = side * wall_y
        cur.append(curtain(f'cur{k}a', x0 - 0.02, x0 + 0.13, side, zt + 0.03, zb - 0.02, wy))
        cur.append(curtain(f'cur{k}b', x1 - 0.13, x1 + 0.02, side, zt + 0.03, zb - 0.02, wy))
        cur.append(cyl(f'rod{k}', ((x0 + x1) / 2, wy - side * 0.035, zt + 0.045), 'x', 0.006, x1 - x0 + 0.08, Z_STEEL, 6))
    if cur:
        join(cur, 'Curtains')
    # --- first-aid kit and extinguisher on the partition
    kit = box('aid_kit', 0.835, 0.885, -0.78, -0.56, 1.42, 1.58, Z_KIT, bevel=0.006)
    ext = cyl('extinguisher', (0.835, -0.78, FLOOR + 0.24), 'z', 0.055, 0.40, Z_CAN, 10)
    join([kit, ext], 'Safety')
    # cab: a dim dash glow for the night
    LIGHTS.append(('dash', (1.72, 0.40, 1.42), 'POINT', 2.5, (1.0, 0.75, 0.45)))
    return PROPS, LIGHTS
