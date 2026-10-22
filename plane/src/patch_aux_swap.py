"""v4 fix without re-baking: left cargo-door / cabin-light toggles belong on the pilot's left (larger X).
Renames the toggle objects pairwise, re-maps their placard UVs and swaps the rig entries."""
import bpy, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY
blend = os.path.join(HERE, 'out', sys.argv[1])
bpy.ops.wm.open_mainfile(filepath=blend)
O = bpy.data.objects
PAIRS = [('SW_CargoDoor_L', 'SW_CargoDoor_R'), ('SW_CabinLight', 'SW_CargoLight')]
for a, b in PAIRS:
    O[a].name = a + '__tmp'
    O[b].name = a
    O[a + '__tmp'].name = b
# placards under the toggles: slot by position (layout.AUX_SWITCHES already holds the swapped x)
slot_at = {(round(x, 3), round(z, 3)): slot for _, x, z, slot in LY.AUX_SWITCHES}
sw = O['CP_Switchgear']
me = sw.data
gi = [m.name for m in me.materials].index('M_Gauges')
uv = me.uv_layers['UVMap'].data
mw = sw.matrix_world
n = 0
for p in me.polygons:
    if p.material_index != gi:
        continue
    c = mw @ p.center
    for (x, z), slot in slot_at.items():
        if abs(c.x - x) < 0.005 and abs(c.z - (z - 0.026)) < 0.004:
            col, row = slot % 8, slot // 8
            u0, u1 = (col * 512 + 6) / 4096, (col * 512 + 506) / 4096
            v1, v0 = 1 - (1700 + row * 90) / 2048, 1 - (1780 + row * 90) / 2048
            x0, x1, z0, z1 = x + 0.026, x + 0.026 - 0.052, z - 0.026 - 0.004, z - 0.026 + 0.004
            for li in p.loop_indices:
                v = mw @ me.vertices[me.loops[li].vertex_index].co
                uv[li].uv = (u0 + (x0 - v.x) / (x0 - x1) * (u1 - u0), v0 + (v.z - z0) / (z1 - z0) * (v1 - v0))
            n += 1
print('placards remapped', n)
bpy.ops.wm.save_as_mainfile(filepath=blend)
# rig json
p = os.path.join(HERE, 'out', 'cockpit_rig.json')
r = json.load(open(p))
for a, b in PAIRS:
    r['rig'][a], r['rig'][b] = r['rig'][b], r['rig'][a]
json.dump(r, open(p, 'w'), indent=1)
print('rig swapped')
