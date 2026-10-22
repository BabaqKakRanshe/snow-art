"""Render one preview of UtilityPlane_v11_lights.blend in Cycles (linear EXR).
python3 render_cycles_v11.py -- '{"view": "ext_front", "out": "...exr", "time": 0.6, "beacon_top": -60, "beacon_bottom": -100,
                                  "atmosphere": 0.35, "samples": 128, "scale": 50}'"""
import bpy, sys, json, time
a = json.loads(sys.argv[sys.argv.index('--') + 1])
bpy.ops.wm.open_mainfile(filepath=a.get('blend', '/home/claude/plane/v11/deliv/UtilityPlane_Unity_v11/Blender/UtilityPlane_v11_lights.blend'))
sc = bpy.context.scene
view = a['view']
sc.camera = bpy.data.objects['Cam_' + view]
for c in bpy.data.collections:
    if c.name.startswith('Figure '):
        c.hide_render = (c.name != 'Figure ' + view)
t = float(a.get('time', 0.6))
sc.frame_set(1)
sc['lf_time_offset'] = t - 1.0 / sc.render.fps
sc['atmosphere'] = float(a.get('atmosphere', 0.35))
sc['lf_flicker'] = float(a.get('flicker', 0.0))
heads = {'Beacon_Top': a.get('beacon_top', 150.0), 'Beacon_Bottom': a.get('beacon_bottom', -120.0)}
for key, hd in heads.items():
    phase = float(hd) - 270.0 * t                  # heading(t) = phase + 45 rpm * 6 * t
    trees = [bpy.data.lights['L_' + key].node_tree, bpy.data.materials['M_LensFX_' + key].node_tree]
    for tr in trees:
        for n in tr.nodes:
            if n.type == 'GROUP' and n.node_tree and n.node_tree.name == 'LF_BeaconRotate':
                n.inputs['Phase'].default_value = phase
for key, lv in a.get('levels', {}).items():           # e.g. {"Strobe_L": 0}
    for tr in [bpy.data.lights['L_' + key].node_tree] + ([bpy.data.materials['M_LensFX_' + key].node_tree] if ('M_LensFX_' + key) in bpy.data.materials else []):
        for n in tr.nodes:
            if n.type == 'VALUE' and n.label.startswith('Level'):
                n.outputs[0].default_value = float(lv)
w = bpy.data.materials['M_FogVolume']
if 'sigma_per_atm' in a or 'g_fwd' in a or 'split' in a or 'sky' in a:
    for fc in w.node_tree.animation_data.drivers:
        if 'p * ' in fc.driver.expression and 'sigma_per_atm' in a:
            fc.driver.expression = 'p * %g' % float(a['sigma_per_atm'])
    scat = [n for n in w.node_tree.nodes if n.type == 'VOLUME_SCATTER']
    scat.sort(key=lambda n: -n.inputs['Anisotropy'].default_value)
    if 'g_fwd' in a:
        scat[0].inputs['Anisotropy'].default_value = float(a['g_fwd'])
    if 'g_wide' in a:
        scat[1].inputs['Anisotropy'].default_value = float(a['g_wide'])
    if 'split' in a:
        for n in w.node_tree.nodes:
            if n.type == 'MATH' and n.operation == 'MULTIPLY' and n.outputs[0].links and n.outputs[0].links[0].to_node == scat[0]:
                n.inputs[1].default_value = float(a['split'])
            if n.type == 'MATH' and n.operation == 'MULTIPLY' and n.outputs[0].links and n.outputs[0].links[0].to_node == scat[1]:
                n.inputs[1].default_value = 1.0 - float(a['split'])
    if 'sky' in a:
        sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = tuple(a['sky']) + (1.0,)
sc.frame_set(1)
sc.cycles.samples = int(a.get('samples', 128))
sc.cycles.use_denoising = bool(a.get('denoise', True))
sc.render.resolution_percentage = int(a.get('scale', 50))
sc.render.image_settings.media_type = 'IMAGE'
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_depth = '32'
sc.render.image_settings.color_management = 'OVERRIDE'
sc.render.image_settings.linear_colorspace_settings.name = 'Linear Rec.709'
sc.render.filepath = a['out']
t0 = time.time()
bpy.ops.render.render(write_still=True)
print('RENDERED', view, a['out'], '%.1f s' % (time.time() - t0), flush=True)
