"""mode A test: PSX in the source UVs"""
import sys, os
sys.path.insert(0, '/home/claude/uaz')
import bpy
import psxlib as P

tag = sys.argv[1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'work', f'{tag}_import.blend'))
for o in list(bpy.data.objects):
    if o.name in ('Fabric',):
        bpy.data.objects.remove(o, do_unlink=True)
P.normalise(list(bpy.data.objects), rot_z_deg=0, length=4.4)
objs = P.split_by_material([o for o in bpy.data.objects if o.type == 'MESH'])
fbm = P.faces_by_material(objs)
for m, faces in fbm.items():
    if m is None:
        continue
    users = [o for o in objs if P.main_material(o) == m]
    P.psx_from_source(m, faces, os.path.join(P.HERE, 'tex', tag + '_A'), bake_objs=users)
P.setup_cycles((900, 600), 32)
P.world(); P.sun(); P.ground()
lo, hi = P.world_bbox(objs)
c = (lo + hi) / 2
L = float(hi[0] - lo[0])
P.cam_look('cam', (c[0] + 0.9 * L, c[1] + 0.75 * L, 0.35 * L), (c[0], c[1], c[2]), 35)
P.render(os.path.join(P.HERE, 'rend', f'{tag}_A_q34.png'))
