import bpy, sys, math, numpy as np
mode = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'wedge'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 64; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 201
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w
w.color = (0, 0, 0)
# ground
me = bpy.data.meshes.new('g'); me.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new('g', me); sc.collection.objects.link(g)
m = bpy.data.materials.new('m')
try:
    m.use_nodes = True
except Exception:
    pass
p = m.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value = (1, 1, 1, 1); p.inputs['Roughness'].default_value = 1.0
p.inputs['Specular IOR Level'].default_value = 0.0
g.data.materials.append(m)
# camera top ortho, image up = +Y
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, 0)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 12
# light
ld = bpy.data.lights.new('L', 'POINT'); ld.energy = 1000.0; ld.shadow_soft_size = 0.0
lo = bpy.data.objects.new('L', ld); sc.collection.objects.link(lo); lo.location = (0, 0, 1.0)
if mode != 'noies':
    try:
        ld.use_nodes = True
    except Exception:
        pass
    nt = ld.node_tree
    N, Lk = nt.nodes, nt.links
    em = [n for n in N if n.type == 'EMISSION'][0]
    ies = N.new('ShaderNodeTexIES')
    fname = {'wedge': 'wedge.ies', 'u1000': 'uniform1000.ies', 'u10': 'uniform10.ies', 'wedge_tc': 'wedge.ies', 'wedge_rot': 'wedge.ies', 'ramp': 'ramp.ies'}[mode]
    txt = bpy.data.texts.new(fname); txt.from_string(open('/home/claude/plane/v11/blender/iestest/' + fname).read())
    ies.mode = 'INTERNAL'; ies.ies = txt
    Lk.new(ies.outputs['Fac'], em.inputs['Strength'])
    if mode in ('wedge_tc', 'wedge_rot'):
        tc = N.new('ShaderNodeTexCoord')
        src = tc.outputs['Normal']
        if mode == 'wedge_rot':
            vr = N.new('ShaderNodeVectorRotate'); vr.rotation_type = 'Z_AXIS'; vr.inputs['Angle'].default_value = math.radians(90)
            Lk.new(src, vr.inputs['Vector']); src = vr.outputs['Vector']
        Lk.new(src, ies.inputs['Vector'])
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.render.filepath = '/home/claude/plane/v11/blender/iestest/out_%s.exr' % mode
bpy.ops.render.render(write_still=True)
print('done', mode)
