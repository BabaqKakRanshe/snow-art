import bpy, sys, math, json
key = sys.argv[sys.argv.index('--') + 1]
meta = json.load(open('/home/claude/plane/v11/blender/IES/lights_meta.json'))[key]
outer = {'Landing': 78, 'Nav_L': 160, 'Beacon_Top': 72, 'Dome_L': 118, 'Cargo': 150, 'Flood': 140, 'Strobe_L': 170}[key]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 128
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0, 0, 0)
t = math.tan(math.radians(min(outer, 150) / 2))
me = bpy.data.meshes.new('g'); s = t * 1.2
me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new('g', me); sc.collection.objects.link(g)
m = bpy.data.materials.new('m'); m.use_nodes = True
p = m.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value = (1, 1, 1, 1); p.inputs['Roughness'].default_value = 1.0; p.inputs['Specular IOR Level'].default_value = 0.0
g.data.materials.append(m)
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, 0, 5); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2 * t
ld = bpy.data.lights.new('L', 'POINT'); ld.energy = 1000.0; ld.shadow_soft_size = 0.0
lo = bpy.data.objects.new('L', ld); sc.collection.objects.link(lo); lo.location = (0, 0, 1.0)
ld.use_nodes = True; nt = ld.node_tree; N, Lk = nt.nodes, nt.links
em = [n for n in N if n.type == 'EMISSION'][0]
ies = N.new('ShaderNodeTexIES'); txt = bpy.data.texts.new(key + '.ies'); txt.from_string(open('/home/claude/plane/v11/blender/IES/%s.ies' % key).read())
ies.mode = 'INTERNAL'; ies.ies = txt
Lk.new(ies.outputs['Fac'], em.inputs['Strength'])
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.render.filepath = '/home/claude/plane/v11/blender/iestest/cookie_%s.exr' % key
bpy.ops.render.render(write_still=True)
print('done', key, 'tan', t)
