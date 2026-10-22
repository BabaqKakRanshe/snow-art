"""the radio set on the Leitstand console: overlaps with the room, renders. python3 -I radio_check.py -- <main.blend> <items.blend> <x> <y> <z> <out_dir>"""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
with bpy.data.libraries.load(a[1]) as (src, dst):
    dst.objects = ['Item_RadioSet']
r = dst.objects[0]
bpy.context.scene.collection.objects.link(r)
x, y, z = float(a[2]), float(a[3]), float(a[4])
out = a[5]
os.makedirs(out, exist_ok=True)
base = bpy.data.objects['BaseMain']
r.matrix_world = base.matrix_world @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.pi, 4, 'Z')
bpy.context.view_layer.update()


def bvh(o):
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    m = e.to_mesh()
    vs = [o.matrix_world @ v.co for v in m.vertices]
    fs = [tuple(p.vertices) for p in m.polygons]
    mats = [p.material_index for p in m.polygons]
    e.to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs), vs, fs


tr, rvs, rfs = bvh(r)
room = bpy.data.objects['R_Leitstand']
tl, lvs, lfs = bvh(room)
pairs = tr.overlap(tl)
hit_r = sorted({i for i, j in pairs})
print('overlap pairs', len(pairs), 'radio faces', len(hit_r))
pts = [sum((rvs[k] for k in rfs[i]), Vector()) / len(rfs[i]) for i in hit_r]
inv = base.matrix_world.inverted()
for p in pts[:40]:
    q = inv @ p
    print('  at building', [round(c, 3) for c in q])
rz = min((inv @ v).z for v in rvs)
print('radio lowest building z', round(rz, 4))
# renders
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.show_shadows = True
for m in bpy.data.materials:
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
views = [('operator', (2.0, -3.6, 1.55), (1.15, -5.05, 0.85), 30), ('close', (1.4, -4.3, 1.15), (1.13, -5.05, 0.80), 35),
         ('door', (-3.0, -2.6, 1.7), (1.4, -5.0, 0.9), 28)]
for n, e, t, lens in views:
    E = base.matrix_world @ Vector(e)
    T = base.matrix_world @ Vector(t)
    cam.location = E
    cam.rotation_euler = (T - E).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
    sc.render.filepath = os.path.join(out, n + '.png')
    bpy.ops.render.render(write_still=True)
print('done')
