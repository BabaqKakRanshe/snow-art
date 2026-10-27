"""a 200 m piece of the runway assembled from out/af.blend as af_contract meta.assembly says (threshold, 17, slabs mixed and
turned, edge lights every 60 m 1.5 m outside the edges, a green row across the end, markers at the clearing edge, the
pointer), workbench views for the sheet: blender -b --python af_assembly.py -- <af.blend> <out_dir>"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
OUT = a[1]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
ob = bpy.data.objects
coll = bpy.data.collections.new('Assembly')
sc.collection.children.link(coll)


def root_copy(root, M):
    """linked copies of a root and its children, root placed by M (the root's own origin = its display offset)"""
    src = ob[root]
    off = Matrix.Translation(src.matrix_world.translation)
    for o in [src] + [c for c in src.children_recursive if c.type == 'MESH' and not c.name.startswith(('COL_', 'Glow_'))]:
        n = o.copy()
        n.parent = None
        n.matrix_world = M @ off.inverted() @ o.matrix_world
        coll.objects.link(n)


for c in list(sc.collection.children):                       # hide the source roots
    if c.name != 'Assembly':
        c.hide_render = True
seq = ['RWY_Threshold', 'RWY_Num17'] + ['RWY_Slab', 'RWY_SlabWorn', 'RWY_Slab', 'RWY_Slab', 'RWY_SlabWorn'] * 4
for i, r in enumerate(seq[:20]):
    turn = Matrix.Rotation(math.pi, 4, 'Z') if (i > 1 and i % 3 == 0) else Matrix.Identity(4)
    root_copy(r, Matrix.Translation((0, i * 10.0 + 5.0, 0)) @ turn)
for y in range(5, 200, 60):
    for sx in (-1, 1):
        root_copy('AF_EdgeLight', Matrix.Translation((sx * 10.5, y, 0)))
for x in range(-8, 9, 3):
    root_copy('AF_ThresholdLight', Matrix.Translation((x + 0.5, -1.2, 0)))
for y in range(0, 200, 30):
    for sx in (-1, 1):
        root_copy('AF_EdgeMarker', Matrix.Translation((sx * 26.0, y + 15, 0)))
root_copy('AF_Sign', Matrix.Translation((-14.0, -6.0, 0)) @ Matrix.Rotation(math.radians(180), 4, 'Z'))
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 100, -0.05))
g = bpy.context.active_object
gm = bpy.data.materials.new('ground')
gm.diffuse_color = (0.05, 0.07, 0.04, 1)
g.data.materials.append(gm)
sh.color_type = 'TEXTURE'
sc.world = bpy.data.worlds.new('w')
sc.world.color = (0.32, 0.34, 0.36)
cam = bpy.data.objects.new('acam', bpy.data.cameras.new('acam'))
sc.collection.objects.link(cam)
sc.camera = cam
V = {'end': ((-3.0, -9.0, 1.7), (0.0, 60.0, 0.0), 26, (1600, 900)),
     'side': ((-30.0, 20.0, 9.0), (0.0, 40.0, 0.0), 30, (1600, 900)),
     'lights': ((-12.5, 1.0, 1.0), (-10.5, 8.0, 0.2), 30, (1200, 900))}
for nm, (e, t, lens, res) in V.items():
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(e)
    cam.rotation_euler = (Vector(t) - Vector(e)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.05
    cam.data.clip_end = 1000
    sc.render.filepath = os.path.join(OUT, 'asm_' + nm + '.png')
    bpy.ops.render.render(write_still=True)
print('ok')
