"""Common scene: snowy forest road, spruces, day / night presets, render of the four views."""
import bpy, math, random, os, json
from mathutils import Vector
import vlib as V


def build_ground(road_w=6.0, rut_y=0.95, rut_w=0.45):
    c = V.coll('Scene')
    snow = V.mat('snow', 'snow', 36, 0.9, px=128)
    packed = V.mat('snow_packed', 'snow_packed', 36, 0.85, px=128)
    V.box('Ground', -150, 150, -150, 150, -0.2, 0.0, snow, c)
    gs = V.box('GroundSide', -150, 150, -150, 8, -0.3, 0.0, snow, c)
    gs.hide_render = True
    V.box('Road', -150, 150, -road_w / 2, road_w / 2, -0.2, 0.004, packed, c)
    rut = V.flatcol('rut', (0.42, 0.42, 0.45), 0.9)
    for s in (1, -1):
        V.box(f'Rut{s}', -150, 150, s * rut_y - rut_w / 2, s * rut_y + rut_w / 2, -0.2, 0.006, rut, c)
        bank = V.box(f'Bank{s}', -150, 150, s * (road_w / 2 + 0.3), s * (road_w / 2 + 1.7), -0.2, 0.32, snow, c)
        V.bevel(bank, 0.35, 2, 30)


def _in_cone(x, y, cam, tgt, half=34, near=40):
    dx, dy = x - cam[0], y - cam[1]
    d = math.hypot(dx, dy)
    if d > near or d < 0.01:
        return False
    tx, ty = tgt[0] - cam[0], tgt[1] - cam[1]
    a = math.degrees(math.acos(max(-1, min(1, (dx * tx + dy * ty) / (d * math.hypot(tx, ty) + 1e-9)))))
    return a < half and d < math.hypot(tx, ty) + 6


def build_trees(seed=3, keep_clear=(), cones=()):
    c = V.coll('Trees')
    r = random.Random(seed)
    n = 0
    for i in range(400):
        x = r.uniform(-70, 70)
        y = r.choice((-1, 1)) * r.uniform(6.5, 45)
        if any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep_clear):
            continue
        if any(_in_cone(x, y, cam, tgt) for cam, tgt in cones):
            continue
        h = r.uniform(7, 15) * (1.0 if abs(y) > 10 else 0.8)
        V.spruce(f'Tree{n}', x, y, h, c)
        n += 1
        if n >= 85:
            break
    return c


def lights_day():
    V.world(False)
    V.sun(False, (52, 0, 32))
    V.set_night(False)


def lights_night():
    V.world(True)
    V.sun(True, (35, 0, -120))
    V.set_night(True)


def clear_lights():
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT' and o.get('veh') is None:
            bpy.data.objects.remove(o, do_unlink=True)


def run_views(veh, outdir, views=('day', 'night', 'inside', 'side'), samples=48, res=(480, 300)):
    """veh: dict from a concept build(): cams, set_state(view), night_lights (list), hide_in_side"""
    os.makedirs(outdir, exist_ok=True)
    V.setup_render(res, samples)
    trees = bpy.data.collections.get('Trees')
    for view in views:
        clear_lights()
        night = view in ('night', 'inside')
        (lights_night if night else lights_day)()
        for l in veh['night_lights']:
            l.hide_render = not night
        veh['set_state'](view)
        if trees:
            trees.hide_render = view == 'side'
        for n in ('Road', 'Rut1', 'Rut-1', 'Bank1', 'Bank-1', 'Ground'):
            o = bpy.data.objects.get(n)
            if o:
                o.hide_render = view == 'side'
        bpy.data.objects['GroundSide'].hide_render = view != 'side'
        cam = veh['cams'][view]
        V.camera(*cam[:3], ortho=cam[3] if len(cam) > 3 else None)
        sc = bpy.context.scene
        sc.cycles.samples = samples * (2 if view == 'inside' else 1)
        V.render(os.path.join(outdir, f'{view}.png'))
        V.render_depth(os.path.join(outdir, f'{view}_depth.png'))
    return outdir
