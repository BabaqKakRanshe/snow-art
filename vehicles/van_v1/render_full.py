"""Final renders of the van concept (plane-preview style) + night, interior, cab and an in-game PS1 frame.
python3 render_full.py <views> [spp]  -> rend/final/<view>.png"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from mathutils import Vector, Matrix
import vb as B

views = sys.argv[1].split(',')
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 48
OUT = os.path.join(B.HERE, 'rend', 'final')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(B.HERE, 'out', 'van_full.blend'))
sc = bpy.context.scene
B.MATS.clear()
snow = B.tex_box('snow', 'snow', 40, 0.9)
ground = B.box('Ground', -150, 150, -150, 150, -0.2, 0.0, snow)
gside = B.box('GroundSide', -150, 150, -150, 6, -0.25, 0.0, snow)
# distant spruce silhouettes for the night views (fade into fog)
trees = B.coll('Trees')
dark = B.flat('spruce_dark', (0.02, 0.035, 0.03), 0.9)
r = random.Random(4)
for i in range(70):
    a = r.uniform(0, 2 * math.pi)
    d = r.uniform(18, 60)
    x, y = 2 + d * math.cos(a), d * math.sin(a)
    h = r.uniform(9, 17)
    parts = [B.cyl(f't{i}_{k}', (x, y, h * (0.18 + 0.2 * k)), 'z', h * 0.22 * (1 - k / 4.5), h * 0.34, 9, dark, trees,
                   r2=0.0) for k in range(4)]
    B.join(parts, f'tree{i}')
# human silhouette for the side view (1.80 m)
hp = [(0.0, 0.0), (0.12, 0.0), (0.14, 0.82), (0.17, 0.82), (0.19, 0.0), (0.31, 0.0), (0.30, 0.86), (0.33, 1.40),
      (0.36, 0.86), (0.42, 0.88), (0.40, 1.42), (0.34, 1.50), (0.27, 1.53), (0.27, 1.58), (0.30, 1.62), (0.30, 1.72),
      (0.25, 1.80), (0.17, 1.80), (0.12, 1.72), (0.12, 1.62), (0.15, 1.58), (0.15, 1.53), (0.08, 1.50), (0.02, 1.42),
      (0.00, 0.88), (0.06, 0.86), (0.09, 1.40), (0.12, 0.86), (0.11, 0.82)]
hum = B.prism('human', [(x - 0.21, z) for x, z in hp], 'y', -0.02, 0.02, B.flat('human_m', (0.08, 0.09, 0.11), 0.9))
hum.location = (3.35, 0.5, 0)
hum.rotation_euler = (0, 0, 0)

night_lights = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.get('night')]
glass_room = bpy.data.materials.get('glass_room')
lamp = bpy.data.materials.get('lamp_warm')
dial = bpy.data.materials.get('dial_glow')
stove = bpy.data.materials.get('stove_glow')
lens_clear = bpy.data.materials.get('lens_clear')
lens_red = bpy.data.materials.get('lens_red')
lens_amber = bpy.data.materials.get('lens_amber')
door = bpy.data.objects.get('SideDoorMain')


def emit(mat, strength, color=None):
    if mat is None:
        return
    pb = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Emission Strength'].default_value = strength
    if color:
        pb.inputs['Emission Color'].default_value = (*color, 1)


def glow(mat, s):
    if mat is None:
        return
    em = mat.node_tree.nodes.get(mat.get('glow_node', 'Emission'))
    em.inputs['Strength'].default_value = s


def state(view):
    night = view in ('night', 'inside', 'cab', 'ingame')
    for l in night_lights:
        l.hide_render = not night
    for l in bpy.data.objects:
        if l.type == 'LIGHT' and l.name.startswith(('Sun', 'Moon')):
            bpy.data.objects.remove(l, do_unlink=True)
    if night:
        B.world((0.010, 0.013, 0.026), 1.0)
        m = B.sun(0.12, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    else:
        B.world((0.56, 0.62, 0.72), 0.9)
        B.sun(3.4, (52, 0, 30))
    emit(lamp, 6.0 if night else 0.0)
    emit(dial, 0.22 if night else 0.0)
    emit(stove, 9.0 if night else 1.5)
    emit(lens_clear, 12.0 if night else 0.0, (1.0, 0.9, 0.75))
    emit(lens_red, 4.0 if night else 0.0, (1.0, 0.05, 0.02))
    emit(lens_amber, 2.5 if night else 0.0, (1.0, 0.45, 0.05))
    glow(glass_room, 0.32 if view in ('night', 'ingame') else 0.0)
    if door:
        door.rotation_euler = (0, 0, math.radians(100) if view in ('night', 'ingame') else 0)
    trees.hide_render = not night
    hum.hide_render = view != 'side'
    ground.hide_render = view == 'side'
    gside.hide_render = view != 'side'


CAMS = {
    'q34': ((6.3, 4.4, 1.72), (0.0, 0, 1.45), 32),
    'q34r': ((-6.0, -4.6, 2.05), (-0.1, 0, 1.45), 32),
    'side': ((0, 16, 1.55), (0.3, 0, 1.55), 30, 7.4),
    'night': ((4.8, -5.6, 1.55), (-0.2, 0, 1.55), 28),
    'ingame': ((4.8, -5.6, 1.55), (-0.2, 0, 1.55), 28),
    'inside': ((-2.05, -0.30, 2.05), (1.6, 0.35, 1.70), 17),
    'cab': ((1.38, 0.60, 2.22), (4.5, 0.25, 1.75), 21),
}
B.setup((900, 600), spp)
for v in views:
    state(v)
    c = CAMS[v]
    B.camera(*c[:3], ortho=c[3] if len(c) > 3 else None)
    sc.cycles.samples = spp * (2 if v in ('inside', 'cab') else 1)
    if v == 'ingame':
        sc.render.resolution_x, sc.render.resolution_y = 427, 240
    else:
        sc.render.resolution_x, sc.render.resolution_y = 900, 600
    B.render(os.path.join(OUT, v + '.png'))
print('rendered', views)
