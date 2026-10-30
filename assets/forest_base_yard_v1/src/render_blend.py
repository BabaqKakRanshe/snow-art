"""render views of a saved scene (base_scene / concept): python3.11 -I render_blend.py <in.blend> <outdir> <views> <spp> <w> <h>
the game's rules as in base_scene.render: trees past 85 m are not drawn (player views), fog k 0.45 for the air view"""
import bpy, sys, os, math

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
src, out, views, spp, w, h = argv[0], argv[1], argv[2].split(','), int(argv[3]), int(argv[4]), int(argv[5])
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.cycles.samples = spp
sc.render.resolution_x, sc.render.resolution_y = w, h
os.makedirs(out, exist_ok=True)
trees = bpy.data.collections.get('Trees')
for v in views:
    cam = bpy.data.objects[v]
    sc.camera = cam
    c = cam.matrix_world.translation
    air = v.endswith('_air')
    if trees is not None:
        for o in trees.objects:
            o.hide_render = (not air) and math.hypot(o.location.x - c.x, o.location.y - c.y) > 85.0
    sc['fog_k'] = 0.45 if air else 1.0
    sc.render.filepath = os.path.join(out, v + '.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', v, flush=True)
