"""render views of a saved airfield scene: python3.11 -I rv.py <blend> <views,..> <spp> <w> <h> <outdir> [suffix]
cameras from af_scene.VIEWS over the BEFORE ground (data/ground_crop.npy), so before and after frames match"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import af_scene as S

AIR_FOG = {'af_air': 0.30, 'af_air_s': 0.30, 'af_app': 0.22, 'af_air_n': 0.30}
GROUND_FOG = float(os.environ.get('GROUND_FOG', '0.5'))      # lighter than the game's 6..140 m so the whole strip reads
CULL = os.environ.get('CULL', '0') == '1'                    # the game's 85 m tree draw distance (off: the far forest edge shows)


LOOK2 = os.environ.get('LOOK', '') == '2'       # the game's look by its 27.10 frames: light haze far out, bluish, contrast
FOV_GROUND = float(os.environ.get('FOV', '0'))   # horizontal FOV for the ground views (0: as in VIEWS)


def look2():
    """haze 25..700 m to 0.9 of a blue-grey (the game frames see the runway's far end), sky light bluer, a soft sun,
    AgX medium-high contrast, a little darker"""
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.node_tree is None:
            continue
        for n in mat.node_tree.nodes:
            if n.type == 'MAP_RANGE' and n.inputs['Value'].is_linked and n.inputs['Value'].links[0].from_node.type == 'CAMERA':
                n.inputs['From Min'].default_value = 25.0; n.inputs['From Max'].default_value = 700.0; n.inputs['To Max'].default_value = 0.9
            if n.type == 'EMISSION' and abs(n.inputs['Color'].default_value[0] - 0.92) < 1e-3 and abs(n.inputs['Color'].default_value[2] - 0.95) < 1e-3:
                n.inputs['Color'].default_value = (0.66, 0.71, 0.78, 1)
    w = bpy.context.scene.world
    if w and w.node_tree:
        bg = w.node_tree.nodes.get('Background')
        if bg:
            bg.inputs['Color'].default_value = (0.50, 0.56, 0.66, 1); bg.inputs['Strength'].default_value = float(os.environ.get('SKY', '0.85'))
    sun = bpy.data.objects.get('Sun')
    if sun is not None:
        sun.data.energy = float(os.environ.get('SUN_E', '2.6')); sun.data.color = (1.0, 0.95, 0.88)
        if os.environ.get('SUN_EL'):
            from mathutils import Vector
            el, az = math.radians(float(os.environ['SUN_EL'])), math.radians(float(os.environ.get('SUN_AZ', '200')))
            d = Vector((-math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
            sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    v = bpy.context.scene.view_settings
    v.look = 'AgX - Medium High Contrast'; v.exposure = -0.15
    # contact shading on everything (both scenes alike): base colour x (0.55 + 0.45 AO within 1.5 m), so snow shapes read
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.node_tree is None:
            continue
        N, L = mat.node_tree.nodes, mat.node_tree.links
        pb = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        if pb is None or not pb.inputs['Base Color'].is_linked or any(n.type == 'AMBIENT_OCCLUSION' for n in N):
            continue
        src = pb.inputs['Base Color'].links[0].from_socket
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 1.5; ao.samples = 8
        mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.55; mr.inputs['To Max'].default_value = 1.0
        L.new(ao.outputs['AO'], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        L.new(src, mx.inputs['A'])
        cb = N.new('ShaderNodeCombineXYZ')
        for ax in ('X', 'Y', 'Z'):
            L.new(mr.outputs['Result'], cb.inputs[ax])
        L.new(cb.outputs['Vector'], mx.inputs['B'])
        L.new(mx.outputs['Result'], pb.inputs['Base Color'])


def make_cams(views):
    cams = {}
    for k in views:
        old = bpy.data.objects.get(k)
        if old is not None:
            if FOV_GROUND and k not in AIR_FOG:
                old.data.angle = math.radians(FOV_GROUND)
            cams[k] = old
            continue
        e, l, fov = S.VIEWS[k]
        if FOV_GROUND and k not in AIR_FOG:
            fov = FOV_GROUND
        eye = S.B(e[0], e[2], S.ground_h(e[0], e[2]) + e[1]); tgt = S.B(l[0], l[2], S.ground_h(l[0], l[2]) + l[1])
        cd = bpy.data.cameras.new(k); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(fov); cd.clip_start = 0.1; cd.clip_end = 3000
        co = bpy.data.objects.new(k, cd); bpy.context.scene.collection.objects.link(co)
        co.location = eye; co.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        cams[k] = co
    return cams


def render(cams, views, folder, suffix=''):
    os.makedirs(folder, exist_ok=True)
    sc = bpy.context.scene
    for v in views:
        sc.camera = cams[v]; sc.render.filepath = os.path.join(folder, v + suffix + '.png')
        air = v in AIR_FOG
        S.cull_trees(cams[v], on=CULL and not air)
        sc['fog_k'] = 1.0 if LOOK2 else AIR_FOG.get(v, GROUND_FOG)
        bpy.ops.render.render(write_still=True)
        print('rendered', v, flush=True)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    views = argv[1].split(',')
    cams = make_cams(views)
    S.setup_render(int(argv[2]), (int(argv[3]), int(argv[4])))
    sun = bpy.data.objects.get('Sun')
    if sun is not None and os.environ.get('SUN'):
        sun.data.energy = float(os.environ['SUN'])
    if LOOK2:
        look2()
    render(cams, views, argv[5], argv[6] if len(argv) > 6 else '')
