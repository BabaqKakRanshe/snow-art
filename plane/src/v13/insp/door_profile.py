import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
for n in ('CargoDoor_L', 'CargoDoor_L__Glass'):
    o = O.get(n)
    print(n, o.type if o else None, [m.name for m in o.data.materials] if o else None, 'pivot', tuple(round(v,3) for v in o.matrix_world.translation) if o else None, 'parent', o.parent.name if o and o.parent else None)
o = O['CargoDoor_L']
vs = [o.matrix_world @ v.co for v in o.data.vertices]
import collections
print('verts', len(vs), 'faces', len(o.data.polygons))
# inner (min x) and outer (max x) per y-bin
for y0 in [-0.85,-0.7,-0.5,-0.3,-0.1,0.1,0.3,0.4]:
    sel = [p for p in vs if y0 <= p.y < y0+0.1]
    if sel: print(f'y {y0:5.2f}..{y0+0.1:5.2f}: x {min(p.x for p in sel):.3f}..{max(p.x for p in sel):.3f}  z {min(p.z for p in sel):.3f}..{max(p.z for p in sel):.3f}')
for z0 in [1.1,1.3,1.5,1.7,1.9,2.1,2.3]:
    sel = [p for p in vs if z0 <= p.z < z0+0.2]
    if sel: print(f'z {z0:4.2f}..{z0+0.2:4.2f}: x {min(p.x for p in sel):.3f}..{max(p.x for p in sel):.3f}')
# material usage
cnt = collections.Counter(p.material_index for p in o.data.polygons)
print('faces per material', {o.data.materials[k].name: v for k, v in cnt.items()})
# inner part deeper than 0.70?
deep = [p for p in vs if p.x < 0.70]
print('verts with x<0.70:', len(deep), 'y range', (round(min(p.y for p in deep),3), round(max(p.y for p in deep),3)) if deep else None, 'z', (round(min(p.z for p in deep),3), round(max(p.z for p in deep),3)) if deep else None)
