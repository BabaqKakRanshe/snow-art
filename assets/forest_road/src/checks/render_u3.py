"""Update 3's road models (FBX, flat material colours) from the same cameras as road_render.py's cmp_* views.
python3 -I render_u3.py -- outdir [names]"""
import bpy, sys, os, math, json
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
a = sys.argv[sys.argv.index('--') + 1:]
outd = a[0]
os.makedirs(outd, exist_ok=True)
CMP = json.load(open('/home/claude/uaz/road_cmp_views.json'))
names = a[1:] or sorted({v['prefab'] for v in CMP.values()})
M = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Models/'
COL = {'Concrete': (0.60, 0.59, 0.56), 'Galvan': (0.55, 0.57, 0.56), 'ChainLink': (0.5, 0.5, 0.5), 'Rust': (0.40, 0.18, 0.08),
       'Steel': (0.42, 0.43, 0.44), 'PaintGreyMetal': (0.42, 0.43, 0.43), 'ObsSigns': (0.8, 0.8, 0.8), 'PaintWhite': (0.85, 0.85, 0.83),
       'MetalGrey': (0.41, 0.42, 0.44), 'WoodPlanks': (0.30, 0.26, 0.21), 'BoardsDark': (0.34, 0.30, 0.26), 'Bark': (0.25, 0.18, 0.12),
       'DeadWood': (0.35, 0.30, 0.24), 'StoveIron': (0.05, 0.05, 0.05), 'WoodPole': (0.55, 0.45, 0.36), 'Boards': (0.5, 0.44, 0.38),
       'RoofTar': (0.08, 0.08, 0.08)}
for n in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=M + n + '.fbx')
    for m in bpy.data.materials:
        c = next((v for k, v in COL.items() if k in m.name), (0.5, 0.5, 0.5))
        m.use_nodes = True
        b = next(nn for nn in m.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = (*c, 1)
        b.inputs['Roughness'].default_value = 0.8
    sc = bpy.context.scene
    import road_kit as RK, road_spec as S                     # the same ground as road_render's comparison views
    EXT = {'ZoneGate': (-7, 7, -5, 5), 'Bridge30': (-22, 22, -4, 4), 'OverlookDeck': (-4, 4, -3, 6)}
    ext = EXT.get(n, (-1.6, 1.6, -0.6, 0.6))
    v, f = RK.ground_patch(n, *ext, step=0.25)
    gm = bpy.data.materials.new('g'); gm.use_nodes = True
    next(nn for nn in gm.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.055, 0.065, 0.042, 1)
    rm = bpy.data.materials.new('r'); rm.use_nodes = True
    next(nn for nn in rm.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.13, 0.11, 0.085, 1)
    me = bpy.data.meshes.new('G'); me.from_pydata(v, [], f); me.materials.append(gm); me.materials.append(rm)
    for poly in me.polygons:
        c = sum((Vector(v[i]) for i in poly.vertices), Vector()) / 4
        poly.material_index = 1 if S.surface(n, c.x, c.y) in 'RT' else 0
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
    for vn, v in CMP.items():
        if v['prefab'] != n:
            continue
        cam.location = Vector(v['eye'])
        cam.rotation_euler = (Vector(v['tgt']) - Vector(v['eye'])).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = v['lens']
        sc.render.filepath = os.path.join(outd, vn + '.png')
        bpy.ops.render.render(write_still=True)
    print('done', n, flush=True)
