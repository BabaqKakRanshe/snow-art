import bpy, math, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.device = 'CPU'
sc.render.resolution_x = 200; sc.render.resolution_y = 200
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
# camera straight above looking down: image right = world +X, image up = world +Y
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0, 0, 8); co.rotation_euler = (0, 0, 0)
cam.type = 'ORTHO'; cam.ortho_scale = 10
L = bpy.data.lights.new('s', 'SPOT'); L.energy = 2000; L.spot_size = math.radians(90); L.spot_blend = 0.0
lo = bpy.data.objects.new('s', L); sc.collection.objects.link(lo)
lo.location = (0, 0, 3)
# light local axes: -Z down (beam), +Y = world +Y, +X = world +X  -> identity rotation
lo.rotation_euler = (0, 0, 0)
L.use_nodes = True
nt = L.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_LIGHT' and n.type != 'EMISSION': nt.nodes.remove(n)
em = [n for n in nt.nodes if n.type == 'EMISSION'][0]
tc = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(tc.outputs['Normal'], sep.inputs[0])
# u = 0.5 + 0.5 * x/(-z)/tan(45) ; v = 0.5 + 0.5 * y/(-z)
negz = nt.nodes.new('ShaderNodeMath'); negz.operation = 'MULTIPLY'; negz.inputs[1].default_value = -1
nt.links.new(sep.outputs['Z'], negz.inputs[0])
du = nt.nodes.new('ShaderNodeMath'); du.operation = 'DIVIDE'; nt.links.new(sep.outputs['X'], du.inputs[0]); nt.links.new(negz.outputs[0], du.inputs[1])
dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; nt.links.new(sep.outputs['Y'], dv.inputs[0]); nt.links.new(negz.outputs[0], dv.inputs[1])
comb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(du.outputs[0], comb.inputs[0]); nt.links.new(dv.outputs[0], comb.inputs[1])
mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.5, 0.5, 1); mp.inputs['Location'].default_value = (0.5, 0.5, 0)
nt.links.new(comb.outputs[0], mp.inputs['Vector'])
im = nt.nodes.new('ShaderNodeTexImage'); im.image = bpy.data.images.load('/home/claude/plane/v11/prev/gobo_test.png'); im.extension = 'CLIP'; im.interpolation = 'Closest'
nt.links.new(mp.outputs[0], im.inputs['Vector'])
nt.links.new(im.outputs['Color'], em.inputs['Color'])
sc.render.filepath = '/home/claude/plane/v11/prev/gobo_test_out.png'
bpy.ops.render.render(write_still=True)
