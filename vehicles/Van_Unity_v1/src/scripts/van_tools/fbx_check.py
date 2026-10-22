"""Read Van.fbx the way Unity does (node local transforms, X mirrored, metres) with Blender's FBX parser and compare every
node and mesh with van_export_report.json: parent, origin (Unity frame), local rotation / scale (identity), mesh bounds,
UV sets, blend shapes. python3 -I fbx_check.py <Van.fbx> <van_export_report.json>"""
import sys, json, math
import numpy as np
import bpy
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx

fbx, repp = sys.argv[-2], sys.argv[-1]
root, ver = parse_fbx.parse(fbx)
rep = json.load(open(repp))


def find(el, name):
    return [e for e in el.elems if e.id == name]


def props70(el):
    out = {}
    for p in find(el, b'Properties70'):
        for q in p.elems:
            if q.id == b'P':
                key = q.props[0].decode()
                out[key] = q.props[4:]
    return out


gs = props70(find(root, b'GlobalSettings')[0])
print('FBX', ver, 'UpAxis', gs.get('UpAxis'), 'UpAxisSign', gs.get('UpAxisSign'), 'FrontAxis', gs.get('FrontAxis'),
      'FrontAxisSign', gs.get('FrontAxisSign'), 'CoordAxis', gs.get('CoordAxis'), 'CoordAxisSign', gs.get('CoordAxisSign'),
      'UnitScaleFactor', gs.get('UnitScaleFactor'))
objs = find(root, b'Objects')[0]
models, geoms, deformers = {}, {}, {}
for e in objs.elems:
    uid = e.props[0]
    name = e.props[1].split(b'\x00')[0].decode()
    if e.id == b'Model':
        p = props70(e)
        models[uid] = dict(name=name, kind=e.props[2].decode(), t=list(p.get('Lcl Translation', (0, 0, 0))),
                           r=list(p.get('Lcl Rotation', (0, 0, 0))), s=list(p.get('Lcl Scaling', (1, 1, 1))))
    elif e.id == b'Geometry':
        kind = e.props[2].decode()
        g = dict(name=name, kind=kind)
        for c in e.elems:
            if c.id == b'Vertices':
                g['v'] = np.array(c.props[0]).reshape(-1, 3)
            if c.id == b'LayerElementUV':
                g.setdefault('uv', []).append(find(c, b'Name')[0].props[0].decode())
        geoms[uid] = g
    elif e.id == b'Deformer':
        deformers[uid] = dict(name=name, kind=e.props[2].decode())
conns = find(root, b'Connections')[0]
parent, geo_of, shape_parent = {}, {}, {}
for c in conns.elems:
    typ, a, b = c.props[0], c.props[1], c.props[2]
    if typ != b'OO':
        continue
    if a in models and (b in models or b == 0):
        parent[a] = b
    elif a in geoms and b in models:
        if geoms[a]['kind'] == 'Mesh':
            geo_of[b] = a
    elif a in geoms and b in deformers:                 # shape geometry -> BlendShapeChannel
        shape_parent[a] = b
    elif a in deformers and b in deformers:             # channel -> BlendShape
        shape_parent[a] = b
    elif a in deformers and b in geoms:                 # BlendShape -> mesh geometry
        shape_parent[a] = b
byname = {m['name']: uid for uid, m in models.items()}
# blend shapes per mesh geometry
shapes = {}
for g_uid, g in geoms.items():
    if g['kind'] == 'Shape':
        ch = shape_parent.get(g_uid)
        bs = shape_parent.get(ch)
        mesh = shape_parent.get(bs)
        shapes.setdefault(mesh, []).append(deformers[ch]['name'].split('\x00')[0] if ch in deformers else '?')


def unity_world(uid):
    m = models[uid]
    t = np.array([-m['t'][0], m['t'][1], m['t'][2]])
    p = parent.get(uid, 0)
    return t if p == 0 else unity_world(p) + t


bad = []
nodes = {n['name']: n for n in rep['nodes']}
assert len(models) == len(nodes), (len(models), len(nodes))
rot_bad = [m['name'] for m in models.values() if max(abs(x) for x in m['r']) > 1e-4 or max(abs(x - 1) for x in m['s']) > 1e-5]
for name, n in nodes.items():
    uid = byname[name]
    pu = parent.get(uid, 0)
    pname = models[pu]['name'] if pu else ''
    if pname != n['parent']:
        bad.append(f'{name}: parent {pname} != {n["parent"]}')
    w = unity_world(uid)
    d = np.abs(w - np.array(n['origin_unity'])).max()
    if d > 5e-4:
        bad.append(f'{name}: origin {w.round(4).tolist()} != {n["origin_unity"]} ({d:.4f})')
    if n['type'] == 'MESH':
        g = geoms[geo_of[uid]]
        v = g['v'] * [-1, 1, 1] + w
        lo, hi = v.min(0), v.max(0)
        bl, bh = np.array(n['bounds_body'][0]), np.array(n['bounds_body'][1])
        ulo = np.array([-bh[1], bl[2], bl[0]])
        uhi = np.array([-bl[1], bh[2], bh[0]])
        d = max(np.abs(lo - ulo).max(), np.abs(hi - uhi).max())
        if d > 5e-4:
            bad.append(f'{name}: bounds off by {d:.4f}')
        if len(g.get('uv', [])) != len(n['uv']):
            bad.append(f'{name}: uv sets {g.get("uv")} vs {n["uv"]}')
        sk = sorted(shapes.get(geo_of[uid], []))
        if sk != sorted(n['blendshapes']):
            bad.append(f'{name}: blend shapes {sk} vs {n["blendshapes"]}')
print('models', len(models), 'meshes', sum(1 for g in geoms.values() if g['kind'] == 'Mesh'),
      'shape geometries', sum(1 for g in geoms.values() if g['kind'] == 'Shape'))
print('non-identity local rotation / scale:', rot_bad)
print('blend shapes:', {models[[u for u, gg in geo_of.items() if gg == k][0]]['name']: v for k, v in shapes.items()})
print('PROBLEMS', len(bad))
for b in bad[:40]:
    print('  ', b)
