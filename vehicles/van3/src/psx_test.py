"""pipeline test on a stand-in model: normalise, split, PSX atlases, Cycles preview"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
import psxlib as P

tag = sys.argv[1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'work', f'{tag}_import.blend'))
for o in list(bpy.data.objects):
    if o.name in ('Fabric',):
        bpy.data.objects.remove(o, do_unlink=True)
objs = list(bpy.data.objects)
s = P.normalise(objs, rot_z_deg=0, length=4.4)
objs = [o for o in bpy.data.objects if o.type == 'MESH']
objs = P.split_by_material(objs)
groups = {}
for o in objs:
    m = P.main_material(o)
    key = m.name if m else 'none'
    if 'glass' in key.lower():
        continue
    groups.setdefault(key, []).append(o)
infos = []
for k, g in groups.items():
    mat, info = P.psx_atlas(f'{tag}_{k}', g, os.path.join(P.HERE, 'tex', tag), ppm=50)
    infos.append(info)
P.setup_cycles((900, 600), 32)
P.world()
P.sun()
P.ground()
lo, hi = P.world_bbox([o for o in bpy.data.objects if o.type == 'MESH' and o.name != 'Ground'])
c = (lo + hi) / 2
P.cam_look('cam', (c[0] + 5.6, c[1] + 4.0, 1.6), (c[0], c[1], 0.7), 35)
P.render(os.path.join(P.HERE, 'rend', f'{tag}_psx_q34.png'))
P.cam_look('cam2', (c[0] + 2.2, c[1] + 1.6, 1.2), (c[0] + 1.0, c[1], 0.7), 35)
P.render(os.path.join(P.HERE, 'rend', f'{tag}_psx_close.png'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(P.HERE, 'work', f'{tag}_psx.blend'))
print('INFOS', infos)
