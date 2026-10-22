"""Renders for the Update 6 sheets (Workbench, the PSX textures point-filtered, studio light with shadows, a ground plane).
python3 -I u6_render.py -- <blend|fbx> <out_dir> <views.json>
views: [{name, eye, target, lens | vfov, w, h, hide: [names], rot: {obj: [axis, deg, pivot]}, ground: z | null}]"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index('--') + 1:]
src, out, views = a[0], a[1], json.load(open(a[2]))
os.makedirs(out, exist_ok=True)
if src.endswith('.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=src)
else:
    bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE' if not src.endswith('.fbx') else 'MATERIAL'
sh.show_cavity = False
sh.show_shadows = True
sh.shadow_intensity = 0.45
sh.show_backface_culling = True
sc.display.light_direction = (0.45, -0.35, 0.82)
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
for o in bpy.data.objects:
    if o.name.startswith(('COL_', 'AOG', 'qcam')) or o.type == 'EMPTY':
        o.hide_render = True
gm = bpy.data.materials.new('u6_ground')
gm.diffuse_color = (0.20, 0.22, 0.18, 1.0)
cam = bpy.data.objects.new('u6cam', bpy.data.cameras.new('u6cam'))
sc.collection.objects.link(cam)
sc.camera = cam
ground = None
for v in views:
    if ground is not None:
        bpy.data.objects.remove(ground)
        ground = None
    if v.get('ground') is not None:
        me = bpy.data.meshes.new('u6g')
        z = v['ground']
        me.from_pydata([(-40, -40, z), (40, -40, z), (40, 40, z), (-40, 40, z)], [], [(0, 1, 2, 3)])
        me.materials.append(gm)
        ground = bpy.data.objects.new('u6g', me)
        sc.collection.objects.link(ground)
    saved = {}
    for n, (ax, deg, piv) in v.get('rot', {}).items():
        o = bpy.data.objects[n]
        saved[n] = o.matrix_world.copy()
        M = Matrix.Translation(Vector(piv)) @ Matrix.Rotation(math.radians(deg), 4, Vector(ax)) @ Matrix.Translation(-Vector(piv))
        o.matrix_world = M @ o.matrix_world
    hid = []
    for n in v.get('hide', []):
        o = bpy.data.objects.get(n)
        if o and not o.hide_render:
            o.hide_render = True
            hid.append(o)
    sc.render.resolution_x, sc.render.resolution_y = v.get('w', 1200), v.get('h', 800)
    if v.get('vfov'):
        cam.data.sensor_fit = 'VERTICAL'
        cam.data.angle = math.radians(v['vfov'])
    else:
        cam.data.sensor_fit = 'AUTO'
        cam.data.lens = v.get('lens', 28)
    cam.data.clip_start = 0.02
    cam.data.clip_end = 300
    e, t = Vector(v['eye']), Vector(v['target'])
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out, v['name'] + '.png')
    bpy.ops.render.render(write_still=True)
    for o in hid:
        o.hide_render = False
    for n, mw in saved.items():
        bpy.data.objects[n].matrix_world = mw
print('rendered', len(views))
