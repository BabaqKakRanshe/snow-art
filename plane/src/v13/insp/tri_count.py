import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v13.blend')
O = bpy.data.objects
def tris(n):
    me = O[n].data; return sum(len(p.vertices) - 2 for p in me.polygons)
print('mounts', tris('src_LightMounts'), 'rails', tris('src_DoorRails'), 'lenses', tris('src_Lights'),
      'doorL', tris('CargoDoor_L'), 'doorR', tris('CargoDoor_R'))
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
O = bpy.data.objects
print('old lenses', tris('src_Lights'), 'doorL', tris('CargoDoor_L'), 'doorR', tris('CargoDoor_R'))
