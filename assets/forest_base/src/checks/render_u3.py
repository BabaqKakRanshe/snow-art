"""Update 3's models (FBX, flat material colours) from the same cameras as base_render.py / far_render.py's cmp_* views.
python3 -I render_u3.py -- views.json outdir [names]"""
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
a = sys.argv[sys.argv.index('--') + 1:]
CMP = json.load(open(a[0]))
outd = a[1]
os.makedirs(outd, exist_ok=True)
names = a[2:] or sorted({v['prefab'] for v in CMP.values()})
M = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u5/u3fbx/'
COL = {'Concrete': (0.60, 0.59, 0.56), 'Galvan': (0.55, 0.57, 0.56), 'ChainLink': (0.5, 0.5, 0.5), 'Rust': (0.40, 0.18, 0.08),
       'Steel': (0.42, 0.43, 0.44), 'PaintWhite': (0.85, 0.85, 0.83), 'CleanWhite': (0.92, 0.92, 0.9), 'PaintRed': (0.6, 0.06, 0.04),
       'PaintYellow': (0.75, 0.55, 0.05), 'MetalGrey': (0.41, 0.42, 0.44), 'WoodPlanks': (0.30, 0.26, 0.21), 'Bark': (0.25, 0.18, 0.12),
       'DeadWood': (0.35, 0.30, 0.24), 'StoveIron': (0.05, 0.05, 0.05), 'WoodPole': (0.55, 0.45, 0.36), 'ArmyGreen': (0.16, 0.19, 0.10),
       'Tarp': (0.12, 0.18, 0.10), 'Cable': (0.02, 0.02, 0.018), 'Enamel': (0.66, 0.66, 0.62), 'RackGrey': (0.3, 0.31, 0.32),
       'Lamp': (0.8, 0.75, 0.6), 'Light_Red': (0.9, 0.05, 0.02), 'PlasticBlack': (0.03, 0.03, 0.03), 'ObsSigns': (0.8, 0.8, 0.8),
       'Brick': (0.42, 0.17, 0.12), 'Radome': (0.86, 0.86, 0.84), 'DishWhite': (0.82, 0.82, 0.8), 'Shingles': (0.22, 0.2, 0.19),
       'PlasterWhite': (0.8, 0.79, 0.74), 'BoardsDark': (0.2, 0.15, 0.11), 'Boards': (0.38, 0.3, 0.22), 'FloorBoards': (0.4, 0.31, 0.22),
       'RoofTar': (0.08, 0.08, 0.08), 'Corrugated': (0.5, 0.51, 0.5), 'Grating': (0.4, 0.41, 0.42), 'Chrome': (0.7, 0.7, 0.72),
       'PaintOlive': (0.25, 0.27, 0.15), 'PaintBlue': (0.1, 0.2, 0.45), 'PaintGrey': (0.45, 0.46, 0.46), 'PaintRed': (0.6, 0.06, 0.04),
       'FabricBlue': (0.1, 0.18, 0.4), 'FabricGrey': (0.4, 0.4, 0.38), 'FabricBeige': (0.6, 0.55, 0.45), 'JacketOrange': (0.8, 0.35, 0.08),
       'Rock': (0.4, 0.39, 0.36), 'ForestFloor': (0.2, 0.17, 0.12), 'Laminate': (0.25, 0.2, 0.15), 'WallPaint': (0.7, 0.7, 0.66),
       'Glass': (0.1, 0.12, 0.12), 'Candle': (0.9, 0.85, 0.7), 'Headlight': (0.9, 0.85, 0.7), 'LED': (0.05, 0.05, 0.04),
       'Rack': (0.08, 0.08, 0.08), 'Grass': (0.2, 0.25, 0.1)}
import base_spec as BS
try:
    import far_spec as FS
except Exception:
    FS = None
for n in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=M + n + '.fbx')
    for m in bpy.data.materials:
        c = next((v for k, v in COL.items() if k in m.name), (0.5, 0.5, 0.5))
        m.use_nodes = True
        b = next(nn for nn in m.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED')
        for ln in list(m.node_tree.links):                              # no textures (missing here): flat colours
            if ln.to_node == b and ln.to_socket.name in ('Base Color', 'Alpha', 'Normal'):   # normal maps missing too
                m.node_tree.links.remove(ln)
        b.inputs['Alpha'].default_value = 1.0
        b.inputs['Metallic'].default_value = 0.0
        for nm_ in ('Transmission Weight', 'Coat Weight', 'Specular IOR Level'):
            if nm_ in b.inputs:
                b.inputs[nm_].default_value = 0.0 if nm_ != 'Specular IOR Level' else 0.3
        b.inputs['Base Color'].default_value = (*c, 1)
        b.inputs['Roughness'].default_value = 0.8
        if 'ChainLink' in m.name:                                   # a cut-out mesh in the game: see-through, one side
            b.inputs['Alpha'].default_value = 0.45                  # of the coplanar front / back pair (no z-fighting)
            m.use_backface_culling = True
            m.surface_render_method = 'DITHERED'
    sc = bpy.context.scene
    S = BS if n in BS.GROUND['prefabs'] or n in ('FenceChain', 'OldFence', 'OldFence_b', 'OldFence_c') else FS
    EXTS = {'RadioMast': (-36, 36, -36, 28), 'Helipad': (-16, 18, -14, 13),
            'Dish_1': (-9, 9, -6, 9), 'Dish_2': (-9, 9, -6, 9), 'Dish_3': (-8, 8, -6, 8), 'Dish_4': (-8, 8, -6, 8),
            'Dish_5': (-9, 9, -6, 9), 'Radome': (-7, 12, -7, 7), 'RelayMast': (-8, 12, -8, 8), 'MeteoStation': (-8, 8, -8, 8),
            'LookoutTower': (-6, 6, -6, 6), 'PumpHouse': (-4, 4, -3, 6), 'Chapel': (-8, 7, -6, 6), 'Cabin': (-6, 4, -5, 5),
            'Campsite': (-3, 5, -3, 3)}
    ext = EXTS.get(n, (-5, 5, -5, 5))
    step = 1.0 if n == 'RadioMast' else 0.5 if (ext[1] - ext[0]) > 12 else 0.25
    xs, ys = np.arange(ext[0], ext[1] + 1e-6, step), np.arange(ext[2], ext[3] + 1e-6, step)
    has = S is not None and n in S.GROUND['prefabs']
    v = [(float(x), float(y), S.ground(n, float(x), float(y)) if has else 0.0) for y in ys for x in xs]
    nx = len(xs)
    f = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1) for i in range(nx - 1)]
    gm = bpy.data.materials.new('g'); gm.use_nodes = True
    next(nn for nn in gm.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.055, 0.065, 0.042, 1)
    me = bpy.data.meshes.new('G'); me.from_pydata(v, [], f); me.materials.append(gm)
    go = bpy.data.objects.new('G', me); sc.collection.objects.link(go)
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 16
    sc.render.resolution_x, sc.render.resolution_y = 800, 520
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.56, 0.62, 0.72, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), math.radians(6), math.radians(25)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    for vn, vv in CMP.items():
        if vv['prefab'] != n:
            continue
        cam.location = Vector(vv['eye'])
        cam.rotation_euler = (Vector(vv['tgt']) - Vector(vv['eye'])).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = vv['lens']
        cam.data.clip_end = 2000
        sc.render.filepath = os.path.join(outd, vn + '.png')
        bpy.ops.render.render(write_still=True)
    print('done', n, flush=True)
