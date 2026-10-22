"""The rebuilt garage against Update 3's data (gar_u3_data.json = Forest_Layout.json's Garage part, gar_spec = the
measured Garage.fbx): both interactables with their kind, axis (Update 3's Unity axis -> the contract's Blender axis),
range, flags and pivot; the leaves' extents against Update 3's; Update 3's lights in free air, every glow at a lamp's
lens; the objects = the contract's parts; the named materials where the game expects them.
python3 -I probe_gar.py [--draft|--test]"""
import sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import main_open as MO
import gar_spec as S

SFX = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
C = json.load(open(f'/home/claude/uaz/out/garage_contract{SFX}.json'))
U3 = json.load(open('/home/claude/uaz/gar_u3_data.json'))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/garage{SFX}.blend')
P = C['parts']
bad = []
SPEC = {S.GATE['name']: S.GATE, S.SIDE['name']: S.SIDE}
for i in U3['interactables']:
    n = i['child']
    p = P.get(n)
    if p is None:
        bad.append((n, 'missing'))
        continue
    if p['kind'] != i['kind']:
        bad.append((n, 'kind', p['kind'], i['kind']))
    ax = MO.unity_axis_to_blender(tuple(i['axis']), i['kind'])
    if max(abs(a - b) for a, b in zip(ax, p['axis'])) > 1e-4:
        bad.append((n, 'axis', p['axis'], ax))
    if abs(p['range'][0] - i['min']) > 1e-4 or abs(p['range'][1] - i['max']) > 1e-4:
        bad.append((n, 'range', p['range'], (i['min'], i['max'])))
    if bool(p.get('locked', False)) != bool(i.get('locked', False)):
        bad.append((n, 'locked', p.get('locked'), i.get('locked')))
    if max(abs(a - b) for a, b in zip(p['pivot'], SPEC[n]['pivot'])) > 1e-4:
        bad.append((n, 'pivot', p['pivot'], SPEC[n]['pivot']))
    if p['root'] != 'Garage':
        bad.append((n, 'root', p['root']))
    o = bpy.data.objects[n]
    V = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
    lo, hi = V.min(0), V.max(0)
    print(f'  {n}: extent {np.round(lo, 3).tolist()} .. {np.round(hi, 3).tolist()}  Update 3 {SPEC[n]["leaf_lo"]} .. '
          f'{SPEC[n]["leaf_hi"]}')
print('interactables', len(U3['interactables']), 'mismatches', len(bad))
for b in bad:
    print('  ', b)
print('locks', C.get('locks'))
# lights and glows
dg = bpy.context.evaluated_depsgraph_get()
V, T, M = [], [], []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    off = len(V)
    V += [o.matrix_world @ v.co for v in me.vertices]
    T += [tuple(i + off for i in t.vertices) for t in me.loop_triangles]
    mats = [s.material.name if s.material else '-' for s in o.material_slots]
    M += [mats[t.material_index] if mats else '-' for t in me.loop_triangles]
    o.evaluated_get(dg).to_mesh_clear()
BV = BVHTree.FromPolygons(V, T)
lens_tris = [i for i, m in enumerate(M) if m.startswith('M_Lamp_')]
LB = BVHTree.FromPolygons(V, [T[i] for i in lens_tris])
for pl in U3['prefabLights']:
    for L in pl['lights']:
        u = L['p']
        b = Vector((-u[0], -u[2], u[1]))
        q = BV.find_nearest(b, 5.0)
        print(f'  light at {tuple(round(x, 3) for x in b)}: free air, nearest surface {q[3]:.3f} m ({M[q[2]]})')
for pg in U3['prefabGlows']:
    for g in pg['glows']:
        u = g['p']
        b = Vector((-u[0], -u[2], u[1]))
        q = LB.find_nearest(b, 5.0)
        mat = M[lens_tris[q[2]]] if q[0] is not None else None
        print(f'  glow {g["m"]} at {tuple(round(x, 3) for x in b)}: nearest lens {q[3]:.3f} m ({mat})')
objs = {o.name for o in bpy.data.objects if o.type == 'MESH'}
print('objects not in the contract', sorted(objs - set(P)), ' parts without object', sorted(set(P) - objs))
for o in sorted(objs):
    print(f'  {o}: materials', [s.material.name for s in bpy.data.objects[o].material_slots if s.material])
