"""Build geometry and render ID-coloured check views."""
import bpy, sys, math, os
sys.path.insert(0, '/home/claude/plane')
import importlib, plane_geo as G
from mathutils import Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/plane/prev'
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
coll = bpy.data.collections.new('Plane'); sc.collection.children.link(coll)
objs, spots = G.build_all(coll)

COL = {1: (0.55, 0.08, 0.06), 3: (0.75, 0.12, 0.08), 4: (0.6, 0.1, 0.08), 5: (0.6, 0.1, 0.1), 6: (0.05, 0.05, 0.05),
       7: (0.12, 0.1, 0.09), 8: (0.01, 0.01, 0.01), 9: (0.02, 0.04, 0.05), 10: (1, 0, 0), 11: (0.1, 0.11, 0.1),
       12: (0.02, 0.02, 0.02), 13: (0.15, 0.15, 0.15), 14: (0.05, 0.25, 0.2), 15: (0.02, 0.02, 0.02),
       16: (0.6, 0.4, 0.05), 17: (0.15, 0.22, 0.06), 18: (0.05, 0.15, 0.15), 19: (0.04, 0.04, 0.04),
       20: (0.3, 0.3, 0.3), 22: (0.2, 0.2, 0.2)}
mats = {}
for k, c in COL.items():
    m = bpy.data.materials.new(f'id{k}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = 0.5
    if k == 10:
        b.inputs['Emission Color'].default_value = (1, 0, 0, 1); b.inputs['Emission Strength'].default_value = 20
    mats[k] = m
tris = 0
for ob in objs:
    me = ob.data
    ids = sorted({int(round(v.value)) for v in me.attributes['mid'].data})
    for i in ids:
        me.materials.append(mats[i])
    lut = {i: n for n, i in enumerate(ids)}
    for p, a in zip(me.polygons, me.attributes['mid'].data):
        p.material_index = lut[int(round(a.value))]
    me.set_sharp_from_angle(angle=math.radians(40))
    tris += sum(len(p.vertices) - 2 for p in me.polygons)
print('objects', len(objs), 'tris', tris)
for ob in objs:
    print(f"  {ob.name:14s} {ob['group']:12s} verts={len(ob.data.vertices):5d} faces={len(ob.data.polygons):5d}")

# door open for preview
door = bpy.data.objects['CargoDoor']
piv = Vector(door['pivot'])
from mathutils import Matrix
door.matrix_world = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-85), 4, 'Y') @ Matrix.Translation(-piv)

# lighting
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.05, 0.055, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); coll.objects.link(sun)
sun.data.energy = 4; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
gp = bpy.data.meshes.new('ground'); gp.from_pydata([(-30,-30,0),(30,-30,0),(30,30,0),(-30,30,0)],[],[(0,1,2,3)])
g = bpy.data.objects.new('ground', gp); sc.collection.objects.link(g)
gm = bpy.data.materials.new('g'); gm.use_nodes=True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.08,0.08,0.08,1)
gp.materials.append(gm)

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1000, 560
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam

def shot(name, loc, target, ortho=None, lens=50):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'; cam.data.lens = lens
    sc.render.filepath = f'{OUT}/{name}.png'
    bpy.ops.render.render(write_still=True)

views = sys.argv[2].split(',') if len(sys.argv) > 2 else ['hero', 'left', 'front', 'top']
if 'hero' in views: shot('hero', (13, -14, 4.2), (0, 0.3, 1.7), lens=50)
if 'left' in views: shot('left', (30, 1.8, 1.9), (0, 1.8, 1.9), ortho=11.5)
if 'right' in views: shot('right', (-30, 1.8, 1.9), (0, 1.8, 1.9), ortho=11.5)
if 'front' in views: shot('front', (0, -40, 1.9), (0, 0, 1.9), ortho=14.5)
if 'top' in views:
    g.hide_render = True
    shot('top', (0, 1.8, 40), (0, 1.8, 0), ortho=14.5)
    g.hide_render = False
if 'cargo' in views: shot('cargo', (4.5, 1.2, 2.2), (0.3, 2.1, 1.8), lens=35)
if 'prop' in views: shot('prop', (2.8, -5.5, 2.6), (0, -2.9, 2.0), lens=40)
if 'gear' in views: shot('gear', (3.2, -3.0, 0.8), (1.4, -0.96, 0.5), lens=35)
if 'tail' in views: shot('tail', (5.5, 9.5, 3.4), (0, 5.8, 2.3), lens=40)
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/geo_check.blend')
