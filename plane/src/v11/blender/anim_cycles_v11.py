"""Short animation of the light functions (Cycles): beacons rotating, strobe double flashes, then the horror flicker
(scene property lf_flicker) kicks in. Renders linear EXR frames; post-processing and encoding happen outside.
python3 anim_cycles_v11.py -- '{"out_dir": "...", "frames": 60, "fps": 20, "samples": 32, "w": 640, "h": 360}'"""
import bpy, sys, json, time, os
a = json.loads(sys.argv[sys.argv.index('--') + 1])
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/v11/deliv/UtilityPlane_Unity_v11/Blender/UtilityPlane_v11_lights.blend')
sc = bpy.context.scene
view = a.get('view', 'ext_front')
sc.camera = bpy.data.objects['Cam_' + view]
for c in bpy.data.collections:
    if c.name.startswith('Figure '):
        c.hide_render = (c.name != 'Figure ' + view)
fps = int(a.get('fps', 20))
sc.render.fps = fps
sc['atmosphere'] = float(a.get('atmosphere', 0.35))
heads = {'Beacon_Top': a.get('beacon_top', -150.0), 'Beacon_Bottom': a.get('beacon_bottom', 20.0)}
for key, hd in heads.items():
    for tr in (bpy.data.lights['L_' + key].node_tree, bpy.data.materials['M_LensFX_' + key].node_tree):
        for n in tr.nodes:
            if n.type == 'GROUP' and n.node_tree and n.node_tree.name == 'LF_BeaconRotate':
                n.inputs['Phase'].default_value = float(hd)          # heading at t = 0
sc.cycles.samples = int(a.get('samples', 32))
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(a.get('w', 640)), int(a.get('h', 360))
sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = 'IMAGE'
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_depth = '16'
sc.render.image_settings.color_management = 'OVERRIDE'
sc.render.image_settings.linear_colorspace_settings.name = 'Linear Rec.709'
os.makedirs(a['out_dir'], exist_ok=True)
t_off = 0.002                                                     # frame 1 = 2 ms after a strobe flash
f_on, f_full = float(a.get('flicker_on', 1.5)), float(a.get('flicker_full', 1.8))
amount = float(a.get('flicker', 0.75))
for f in (a.get('only') or range(1, int(a.get('frames', 60)) + 1)):
    t = (f - 1) / fps + t_off
    sc['lf_time_offset'] = t_off - 0.0                            # Time = frame/fps + offset, frame 1 -> 1/fps
    sc['lf_time_offset'] = t - f / fps
    k = 0.0 if t < f_on else min(1.0, (t - f_on) / max(f_full - f_on, 1e-3))
    sc['lf_flicker'] = amount * k
    sc.frame_set(f)
    sc.render.filepath = os.path.join(a['out_dir'], 'f%03d.exr' % f)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('FRAME', f, 't=%.3f flicker=%.2f' % (t, sc['lf_flicker']), '%.1f s' % (time.time() - t0), flush=True)
print('ANIMDONE', flush=True)
