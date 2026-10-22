"""Full build: exterior, interior, livery bake (PSX), exterior night lights -> out/van_full.blend"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import vb as B
import van as V
import interior as I
import bake as K

t0 = time.time()
B.reset()
r = V.build()
col = r['col']
night = I.build(r['M'], col)
print('geometry', f'{time.time() - t0:.0f}s')
# livery: paint faces of the body and of the side door -> PSX atlases
for name in ('Body', 'SideDoor'):
    ob = bpy.data.objects[name]
    parts = K.separate_by_material(ob)
    paint = next(o for k, o in parts.items() if k.startswith('paint'))
    door_loc = ob.location.copy()
    K.bake_livery(paint, 'Van' + name, 1024 if name == 'Body' else 512, 16, 512 if name == 'Body' else 256)
    for k, o in parts.items():
        if name == 'SideDoor':
            o.location = door_loc
    print('baked', name, f'{time.time() - t0:.0f}s')
# keep door pieces together: parent lining / seal of the door to its paint part
door_parts = [o for o in bpy.data.objects if o.name.startswith('SideDoor')]
main = next(o for o in door_parts if any(s.material and s.material.name.startswith('M_VanSideDoor') for s in o.material_slots))
for o in bpy.data.objects:
    if (o.name.startswith('SideDoor') or o.name.startswith('sd_')) and o is not main:
        mw = o.matrix_world.copy()
        o.parent = main
        o.matrix_world = mw
main.name = 'SideDoorMain'
# exterior night lights
for s in (1, -1):
    night.append(I.light(f'L_head{s}', (2.58, s * 0.52, 1.32), 900, (1.0, 0.9, 0.75), 0.05, col, 'SPOT', (16, s * 1.6, 0), 55))
    night.append(I.light(f'L_tail{s}', (-2.62, s * 0.92, 1.25), 6, (1.0, 0.05, 0.02), 0.05, col))
night.append(I.light('L_door', (0.12, -1.30, 2.6), 120, (1.0, 0.8, 0.55), 0.05, col, 'SPOT', (0.12, -2.4, 0), 85))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(B.HERE, 'out', 'van_full.blend'))
print('saved', len(bpy.data.objects), 'objects', f'{time.time() - t0:.0f}s')
