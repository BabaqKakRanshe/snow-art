"""The rebuilt main building against Update 3's data (main_u3_data.json = Forest_Layout.json's BaseMain part): every
interactable present with its kind, its axis (Update 3's Unity axis -> the contract's Blender axis), its range and its
flags; the light masks (lighting.assign) on the same nodes; the fixtures of every Update 3 light and glow present; the
objects of the blend = the contract's parts; the named materials where the game expects them.
python3 -I probe_main.py [--test]"""
import sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
import main_open as MO

SFX = '_test' if '--test' in sys.argv else ''
C = json.load(open(f'/home/claude/uaz/out/main_contract{SFX}.json'))
U3 = json.load(open('/home/claude/uaz/main_u3_data.json'))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/main{SFX}.blend')
P = C['parts']
bad = []
for i in U3['interactables']:
    n = i['child']
    p = P.get(n)
    if p is None:
        bad.append((n, 'missing'))
        continue
    if p['kind'] != i['kind']:
        bad.append((n, 'kind', p['kind'], i['kind']))
    ax = MO.unity_axis_to_blender(tuple(i['axis']), i['kind'])
    if i['kind'] != 'scale' and max(abs(a - b) for a, b in zip(ax, p['axis'])) > 1e-4:
        bad.append((n, 'axis', p['axis'], ax))
    if abs(p['range'][0] - i['min']) > 1e-4 or abs(p['range'][1] - i['max']) > 1e-4:
        bad.append((n, 'range', p['range'], (i['min'], i['max'])))
    if bool(p.get('locked', False)) != bool(i.get('locked', False)):
        bad.append((n, 'locked', p.get('locked'), i.get('locked')))
    want_root = 'BaseMain_Opening' if i['model'] == 'BaseMain_Opening' else 'BaseMain'
    if p['root'] != want_root:
        bad.append((n, 'root', p['root'], want_root))
print('interactables', len(U3['interactables']), 'mismatches', len(bad))
for b in bad[:40]:
    print('  ', b)
mb = []
for a in U3['assign']:
    p = P.get(a['node'])
    if p is None:
        mb.append((a['node'], 'node missing'))
    elif p.get('lightMask') != a['mask']:
        mb.append((a['node'], p.get('lightMask'), a['mask']))
print('light masks', len(U3['assign']), 'mismatches', len(mb), mb[:20])
fx = {n for n in P if n.startswith('FX_')}
lf = [(L.get('fx'), L.get('room')) for pl in U3['prefabLights'] for L in pl['lights']]
gf = [g.get('fx') for pg in U3['prefabGlows'] for g in pg['glows']]
print('lights', len(lf), 'fixture missing', sorted({f for f, r in lf if f and f not in fx}))
print('glows', len(gf), 'fixture missing', sorted({f for f in gf if f and f not in fx}))
objs = {o.name for o in bpy.data.objects if o.type == 'MESH'}
print('objects not in the contract', sorted(objs - set(P))[:20], ' parts without object', sorted(set(P) - objs)[:20])
need = {'M_ScreenOff': ('R_Leitstand', 'R_Serverraum', 'R_Kueche'), 'M_LEDOff': ('R_Leitstand', 'R_Serverraum'),
        'M_HeatFault': ('BaseMain_Opening', 'IX_BurnerReset_308'), 'M_GlassDark': ('IX_MainDoor_1',),
        'M_FX_Exit': tuple(n for n in fx if n.startswith('FX_ExitSign')), 'M_LEDOn': tuple(n for n in fx if n.startswith('FX_EmergencyLight'))}
for m, owners in need.items():
    miss = [o for o in owners if o in bpy.data.objects and m not in [s.material.name for s in bpy.data.objects[o].material_slots if s.material]]
    print(f'  {m:14s} on {len(owners) - len(miss)}/{len(owners)}', 'missing on' if miss else '', miss[:6])
lens = {}
for n in fx:
    o = bpy.data.objects.get(n)
    if o:
        lens[n] = [s.material.name for s in o.material_slots if s.material]
nolit = [n for n, ms in lens.items() if not any(m.startswith(('M_FX_', 'M_LEDOn')) for m in ms) and n != 'FX_Raster_14']
print('fixtures without a lit material', nolit)
