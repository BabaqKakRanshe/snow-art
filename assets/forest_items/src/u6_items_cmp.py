"""Update 3 and now for a dozen items: the same camera for both (framed on the union of their boxes); Update 3's FBX come
without their textures (flat grey), the new ones with the atlas. python3 -I u6_items_cmp.py -- <items.blend> <u3_fbx_dir> <out_dir>"""
import bpy, sys, os, math
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
blend, u3dir, out = a
os.makedirs(out, exist_ok=True)
NAMES = ['Item_Jerrycan20', 'Item_Flashlight', 'Item_Funnel', 'Item_NoteForm', 'Item_Padlock', 'Item_Key_Generator',
         'Item_CableReel', 'Item_Toolbox', 'Item_Radio', 'Item_Kettle', 'Item_Backpack', 'Item_OilCan']


def setup(textured):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'TEXTURE' if textured else 'SINGLE'
    sh.single_color = (0.62, 0.62, 0.60)
    sh.show_cavity = True
    sh.show_backface_culling = True
    for m in bpy.data.materials:
        if m.node_tree:
            for nd in m.node_tree.nodes:
                if nd.type == 'TEX_IMAGE':
                    nd.interpolation = 'Closest'
    sc.render.resolution_x, sc.render.resolution_y = 420, 320
    cam = bpy.data.objects.new('cmpcam', bpy.data.cameras.new('cmpcam'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 50
    return sc, cam


def bounds(objs):
    vs = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    return Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)])


def shoot(sc, cam, lo, hi, path):
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.02)
    d = Vector((-0.55, -0.85, 0.55)).normalized()
    e = c + d * r * 3.0
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = r * 0.05
    cam.data.clip_end = r * 20
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# the new boxes first (for the common framing), then Update 3's renders, then the new renders
bpy.ops.wm.open_mainfile(filepath=blend)
newb = {n: bounds([bpy.data.objects[n]]) for n in NAMES}
u3b = {}
for n in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(u3dir, n + '.fbx'))
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    lo, hi = bounds(objs)
    u3b[n] = (lo, hi)
    lo = Vector([min(lo[i], newb[n][0][i]) for i in range(3)])
    hi = Vector([max(hi[i], newb[n][1][i]) for i in range(3)])
    sc, cam = setup(False)
    shoot(sc, cam, lo, hi, os.path.join(out, f'{n}_u3.png'))
bpy.ops.wm.open_mainfile(filepath=blend)
sc, cam = setup(True)
for n in NAMES:
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = o.name != n
    lo = Vector([min(u3b[n][0][i], newb[n][0][i]) for i in range(3)])
    hi = Vector([max(u3b[n][1][i], newb[n][1][i]) for i in range(3)])
    shoot(sc, cam, lo, hi, os.path.join(out, f'{n}_now.png'))
print('done', len(NAMES))
