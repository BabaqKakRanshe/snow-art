"""forest_far 1.1 from 1.0 without re-baking what did not change: far 1.0 (out/far_v10.blend, its far.json and contract) +
the weather station from a Meteo-only build (python3 -I far_build.py --only Meteo -> out/far_test.blend: the MeteoStation
without its old screen, the new T_Far_Meteo atlas) + the forest_devices instances (MeteoScreen on Mount_MeteoScreen, TapeDeck
in each dish cabinet, linked from ../forest_devices/devices.blend). Every other prefab, door and atlas stays 1.0's, byte for
byte. Textures: //tex/ next to the blend (out/tex here, tex/ in the package).
python3 -I compose_far11.py -> out/far.blend, out/far.json, out/far_contract.json"""
import os, sys, json, math, shutil
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix

HERE = '/home/claude/uaz'
OUT = os.path.join(HERE, 'out')
DEV_BLEND = os.path.join(HERE, 'forest_devices', 'devices.blend')
C10 = json.load(open(os.path.join(OUT, 'far_contract_v10.json')))
CT = json.load(open(os.path.join(OUT, 'far_contract_test.json')))
I10 = json.load(open(os.path.join(OUT, 'far_v10.json')))
IT = json.load(open(os.path.join(OUT, 'far_test.json')))

# ---- the textures next to the blend: 1.0's, with the new Meteo atlas
T = os.path.join(OUT, 'tex')
os.makedirs(T, exist_ok=True)
for d_ in ('far', 'base'):
    for f in os.listdir(os.path.join(HERE, 'tex', d_)):
        if f.endswith('.png'):
            shutil.copy2(os.path.join(HERE, 'tex', d_, f), T)

# ---- 1.0, the station's mesh swapped for the Meteo-only build's
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'far_v10.blend'))
old_mats = {m.name: m for m in bpy.data.materials}
old_imgs = {i.name: i for i in bpy.data.images}
st = bpy.data.objects['MeteoStation']
old_me = st.data
with bpy.data.libraries.load(os.path.join(OUT, 'far_test.blend'), link=False) as (src, dst):
    dst.meshes = ['MeteoStation']
new_me = dst.meshes[0]
for i, m in enumerate(new_me.materials):
    base = m.name.split('.')[0]
    assert base in old_mats, base
    new_me.materials[i] = old_mats[base]
st.data = new_me
bpy.data.meshes.remove(old_me)
new_me.name = 'MeteoStation'
for m in [m for m in bpy.data.materials if m.name not in old_mats]:
    bpy.data.materials.remove(m)
for im in [i for i in bpy.data.images if i.name not in old_imgs]:
    bpy.data.images.remove(im)

# ---- the forest_devices instances at their mounts (as far_build 1.1 makes them)
DEV = [('MeteoScreen', 'MeteoScreen', 'MeteoStation', 'Mount_MeteoScreen')] + \
      [('TapeDeck_' + d[-1], 'TapeDeck', d, 'Mount_TapeDeck_' + d[-1]) for d in ('Dish_1', 'Dish_2', 'Dish_3', 'Dish_4', 'Dish_5')]
with bpy.data.libraries.load(DEV_BLEND, link=True) as (src, dst):
    dst.collections = sorted({it for _, it, _, _ in DEV})
dcoll = {c.name: c for c in dst.collections}
inst = bpy.data.collections.new('Devices_Instances')
bpy.context.scene.collection.children.link(inst)
R180 = Matrix.Rotation(math.pi, 4, 'Z')
bpy.context.view_layer.update()
for name, item, par, sock in DEV:
    e = bpy.data.objects.new(name, None)
    inst.objects.link(e)
    e.instance_type = 'COLLECTION'
    e.instance_collection = dcoll[item]
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', 0.1
    P_ = bpy.data.objects[par]
    e.matrix_world = P_.matrix_world @ Matrix.Translation(Vector(CT['sockets'][sock]['pos'])) @ R180
    e.parent = P_
    e.matrix_parent_inverse = P_.matrix_world.inverted()
    e['devices_item'] = item
    e['package'] = 'forest_devices'
for lib in bpy.data.libraries:
    lib.filepath = '//../forest_devices/devices.blend'
for im in bpy.data.images:
    if im.library is None and im.source == 'FILE':
        assert im.filepath.startswith('//tex/'), im.filepath
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'far.blend'), relative_remap=False)

# ---- the contract: the Meteo-only build's (new sockets, devices_instances, meta), 1.0's materials on the other parts
C = CT
for k, p in C['parts'].items():
    q = C10['parts'][k]
    if k != 'MeteoStation':
        p['materials'] = q['materials']
        assert p == q, f'{k} differs from 1.0'
assert {k: v for k, v in C['sockets'].items() if k in C10['sockets']} == C10['sockets']
json.dump(C, open(os.path.join(OUT, 'far_contract.json'), 'w'), indent=1, ensure_ascii=False)
I = dict(I10)
I['atlases'] = dict(I10['atlases'], Meteo=IT['atlases']['Meteo'])
I['tris_by_object'] = dict(I10['tris_by_object'], MeteoStation=IT['tris_by_object']['MeteoStation'])
I['tris'] = sum(I['tris_by_object'].values())
I['part_boxes'] = IT['part_boxes']
I['devices_instances'] = IT['devices_instances']
I['version'] = '1.1'
json.dump(I, open(os.path.join(OUT, 'far.json'), 'w'), indent=1)
print('far 1.1:', I['tris'], 'tris; MeteoStation', I['tris_by_object']['MeteoStation'], '(1.0:', I10['tris_by_object']['MeteoStation'],
      '); Meteo atlas', I['atlases']['Meteo'], '; devices', I['devices_instances'])
