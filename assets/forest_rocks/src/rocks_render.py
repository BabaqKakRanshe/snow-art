"""Cycles previews of out/rocks.blend: the stones, the boulders, each cliff, and a scene put together from them (a tor with
boulders and stones around it, on a forest floor). python3 -I rocks_render.py <views|all> [spp] -> rend/rocks/<view>.png"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'rocks')
os.makedirs(OUT, exist_ok=True)
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 24
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'rocks.blend'))
sc = bpy.context.scene
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
O = bpy.data.objects
ROCKS = [o for o in O if o.type == 'MESH' and o.name.startswith('Forest')]
HOME = {o.name: o.matrix_world.copy() for o in ROCKS}
gme = bpy.data.meshes.new('Ground')
gme.from_pydata([(-80, -80, -0.01), (80, -80, -0.01), (80, 80, -0.01), (-80, 80, -0.01)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new('Ground', gme)
gm = bpy.data.materials.new('M_ground')
gm.use_nodes = True
pb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pb.inputs['Base Color'].default_value = (0.050, 0.044, 0.032, 1)
pb.inputs['Roughness'].default_value = 0.95
gme.materials.append(gm)
sc.collection.objects.link(gob)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
P.world((0.55, 0.61, 0.70), 0.9)
P.sun(3.0, (50, 0, 32))
SCENE = {   # the composed scene: name -> (x, y, yaw)
    'ForestCliff_2': (0.0, 6.0, 15), 'ForestBoulder_1': (-5.2, 3.2, 40), 'ForestBoulder_3': (5.6, 4.4, -25),
    'ForestStone_6': (-2.6, 0.2, 10), 'ForestStone_3': (2.4, -0.4, 60), 'ForestStone_1': (-1.0, -1.6, 0),
    'ForestStone_5': (0.9, -1.2, 30), 'ForestStone_2': (3.9, 1.2, -40), 'ForestStone_4': (-4.2, -0.8, 20)}


def place(layout):
    for o in ROCKS:
        o.matrix_world = HOME[o.name]
        o.hide_render = layout is not None and o.name not in layout
    for n, (x, y, yaw) in (layout or {}).items():
        O[n].matrix_world = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    bpy.context.view_layer.update()


def centre(names):
    pts = [O[n].matrix_world @ Vector(c) for n in names for c in O[n].bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def frame(names, d, el, az, lens=40):
    lo, hi = centre(names)
    c = (lo + hi) / 2
    c.z = (lo.z + hi.z) * 0.42
    r = max((hi - lo).length * 0.5, 0.4)
    dist = r * d
    e = c + Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)),
                    math.sin(math.radians(el)))) * dist
    return e, c, lens


STONES = {'ForestStone_1': (-1.6, 1.0, 0), 'ForestStone_2': (0.0, 1.0, 20), 'ForestStone_3': (1.6, 1.0, 0),
          'ForestStone_4': (-1.6, -0.6, 0), 'ForestStone_5': (0.0, -0.6, 0), 'ForestStone_6': (1.75, -0.6, 0)}
VIEWS = {
    'stones': (STONES, list(STONES), 2.75, 24, 10),
    'boulders': (None, [o.name for o in ROCKS if 'Boulder' in o.name], 1.95, 16, 12),
    'cliff_1': (None, ['ForestCliff_1'], 2.3, 14, 24),
    'cliff_2': (None, ['ForestCliff_2'], 2.6, 10, -30),
    'cliff_3': (None, ['ForestCliff_3'], 2.4, 16, 32),
    'scene': (SCENE, list(SCENE), 1.85, 14, 16),
}
P.setup_cycles((1100, 700), spp)
sc.cycles.max_bounces = 4
for nm, (layout, names, d, el, az) in VIEWS.items():
    if want and nm not in want:
        continue
    place(layout)
    if layout is None:
        for o in ROCKS:
            o.hide_render = o.name not in names
    e, t, lens = frame(names, d, el, az)
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.05
    P.render(os.path.join(OUT, nm + '.png'))
    print('rendered', nm, flush=True)
