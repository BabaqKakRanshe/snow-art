import sys, math, time
sys.path.insert(0, '/home/claude/uaz')
import bpy
import psxlib as P
import gen_kit as K, gen_set as GS, gen_room as GR
bpy.ops.wm.read_factory_settings(use_empty=True)
K.build_shed(); GS.build_genset(); GR.build_room()
objs = {}
for n, k in K.KBS.items():
    objs[n] = k.to_object(n, pivot=K.CONTRACT['parts'][n]['pivot'])
grp = [o for n, o in objs.items() if K.ATLAS[n] == sys.argv[1]]
nf = sum(len(o.data.polygons) for o in grp)
print('faces', nf, 'objects', len(grp))
for angle, margin, shape in ((62, 0.004, 'CONCAVE'), (75, 0.002, 'CONCAVE'), (62, 0.002, 'AABB')):
    t = time.time()
    P.select_only(grp)
    for o in grp:
        me = o.data
        uv = me.uv_layers.get('PSX') or me.uv_layers.new(name='PSX')
        me.uv_layers.active = uv
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=margin, shape_method=shape)
    bpy.ops.object.mode_set(mode='OBJECT')
    print(angle, margin, shape, 'fill', round(P.uv_fill(grp), 3), 'area', round(P.area3d(grp), 1), '%.1fs' % (time.time() - t))
