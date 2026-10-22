import bpy, sys
import numpy as np
sys.path.insert(0, '/home/claude/uaz')
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
import gen_kit as K
o = bpy.data.objects['Snow_Roof']
kb = o.data.shape_keys.key_blocks
Cl = np.array([tuple(o.matrix_world @ k.co) for k in kb['Clear'].data])
B = np.array([tuple(o.matrix_world @ k.co) for k in kb['Basis'].data])
dz = Cl[:, 2] - np.array([K.z_st(abs(y)) for y in Cl[:, 1]])
print('Snow_Roof at Clear=100: height above roof top min %.4f max %.4f m; basis thickness max %.3f' % (dz.min(), dz.max(), (B[:, 2] - np.array([K.z_st(abs(y)) for y in B[:, 1]])).max()))
me = o.data
up = sum(1 for p in me.polygons if p.normal.z > 0.5)
print('faces', len(me.polygons), 'facing up', up, 'hide_render', o.hide_render, 'hide_viewport', o.hide_viewport, 'hidden', o.hide_get())
# ridge gap: snow on each slope begins at y=0 -> both slopes meet at the ridge? check the ridge cap vs snow
print('snow verts at |y|<0.01: z range', B[np.abs(B[:, 1]) < 0.01][:, 2].min(), B[np.abs(B[:, 1]) < 0.01][:, 2].max(), 'ridge cap top', K.z_st(0) + 0.025)
