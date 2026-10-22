import bpy
for tag in ('v11', 'v13'):
    bpy.ops.wm.open_mainfile(filepath=f'/home/claude/plane/out/plane_unity_{tag}.blend')
    O = bpy.data.objects
    def zr(n):
        ob = O[n]; zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
        return round(min(zs), 4), round(max(zs), 4)
    w = O['Wheel_L']; wz = [(w.matrix_world @ v.co).z for v in w.data.vertices]
    print(tag, 'beacon top lens z', zr('Lens_Beacon_Top'), 'bottom lens', zr('Lens_Beacon_Bottom'), 'wheel L min z', round(min(wz), 4),
          'body max z', zr('Body')[1])
