import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False
sc.render.resolution_x = 160; sc.render.resolution_y = 40
sc.view_settings.view_transform = 'Standard'
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); pl = bpy.context.active_object
pl.scale = (20, 5, 1)
m = bpy.data.materials.new('w'); m.use_nodes = True; m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1, 1, 1, 1)
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
pl.data.materials.append(m)
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0, 0, 10); cam.type = 'ORTHO'; cam.ortho_scale = 20
L = bpy.data.lights.new('p', 'POINT'); L.energy = 1000; L.shadow_soft_size = 0
lo = bpy.data.objects.new('p', L); sc.collection.objects.link(lo); lo.location = (-10, 0, 0.5)
L.use_nodes = True; nt = L.node_tree
em = [n for n in nt.nodes if n.type == 'EMISSION'][0]
tc = nt.nodes.new('ShaderNodeTexCoord')
ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
nt.links.new(tc.outputs['Object'], ln.inputs[0])
nt.links.new(ln.outputs['Value'], em.inputs['Strength'])
for i in range(3):
    lo.location = (-10, 0, 0.5)
sc.render.filepath = '/home/claude/plane/v11/prev/falloff_out.exr'
sc.render.image_settings.file_format = 'OPEN_EXR'
bpy.ops.render.render(write_still=True)
