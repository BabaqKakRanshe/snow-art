"""tiunov.se UAZ FBX: the Kuzov children came in with a Y-up frame inside a Z-up parent; put them back,
then nose to +x, real size, ground at z = 0.  -> work/uaz_fixed.blend"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Matrix
import psxlib as P

bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'work', 'uaz_import.blend'))
kz = bpy.data.objects['Kuzov']
C = Matrix.Rotation(math.radians(180), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X')
for o in [o for o in bpy.data.objects if o.parent == kz]:
    mw = C @ o.matrix_world
    o.parent = None
    o.matrix_world = mw
bpy.context.view_layer.update()
LEN = float(sys.argv[1]) if len(sys.argv) > 1 else 4.36
# scale from the body length (bumpers are separate objects)
lo, hi = P.world_bbox([kz])
body_len = float(hi[1] - lo[1])
objs = list(bpy.data.objects)
s = P.normalise(objs, rot_z_deg=-90, length=None)
bpy.context.view_layer.update()
k = LEN / body_len
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.transform(Matrix.Scale(k, 4))
bpy.context.view_layer.update()
lo, hi = P.world_bbox([o for o in bpy.data.objects if o.type == 'MESH'])
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])))
bpy.context.view_layer.update()
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    a, b = P.world_bbox([o])
    print('OBJ', f'{o.name:10s}', a.round(3).tolist(), b.round(3).tolist())
lo, hi = P.world_bbox([o for o in bpy.data.objects if o.type == 'MESH'])
print('BBOX', lo.round(3).tolist(), hi.round(3).tolist(), 'size', (hi - lo).round(3).tolist(), 'body_len_src', round(body_len, 3), 'k', round(k, 4))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(P.HERE, 'work', 'uaz_fixed.blend'))
P.quick_views([o for o in bpy.data.objects if o.type == 'MESH'], os.path.join(P.HERE, 'rend'), 'fixed')
