"""Inspect a UE-bound skeletal FBX: axes/units, root + bone rest transforms, clusters, mesh bounds.
Also prints bone positions converted to UE space (Blender->UE: x, -y, z in cm) as UE's importer does with
Convert Scene on."""
import sys, bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx

path = sys.argv[1]
root, ver = parse_fbx.parse(path)
find = lambda e, n: [c for c in e.elems if c.id == n]
gs = find(find(root, b'GlobalSettings')[0], b'Properties70')[0]
g = {p.props[0].decode(): p.props[-1] for p in gs.elems}
print('FBX', ver, {k: g[k] for k in ('UpAxis', 'UpAxisSign', 'FrontAxis', 'FrontAxisSign', 'CoordAxis',
                                     'CoordAxisSign', 'UnitScaleFactor')})
objs = find(root, b'Objects')[0]
models = {}
for m in find(objs, b'Model'):
    name = m.props[1].split(b'\x00')[0].decode()
    kind = m.props[2].decode()
    pr = {}
    for pp in find(find(m, b'Properties70')[0], b'P'):
        k = pp.props[0].decode()
        if k in ('Lcl Translation', 'Lcl Rotation', 'Lcl Scaling', 'PreRotation'):
            pr[k] = [round(v, 3) for v in pp.props[4:7]]
    models[name] = (kind, pr)
kinds = {}
for n, (k, pr) in models.items():
    kinds.setdefault(k, []).append(n)
print({k: len(v) for k, v in kinds.items()})
nonzero_rot = [n for n, (k, pr) in models.items() if k == 'LimbNode' and any(abs(x) > 1e-3 for x in pr.get('Lcl Rotation', [0, 0, 0]))]
print('LimbNodes with non-zero rest rotation:', nonzero_rot)
for n in sys.argv[2:]:
    print(' ', n, models.get(n))
clusters = [d for d in find(objs, b'Deformer') if d.props[2] == b'Cluster']
print('skin clusters:', len(clusters))
for geo in find(objs, b'Geometry'):
    v = find(geo, b'Vertices')
    if v:
        arr = v[0].props[0]
        xs, ys, zs = arr[0::3], arr[1::3], arr[2::3]
        print('geometry', geo.props[1].split(b'\x00')[0].decode(), 'bounds x', round(min(xs), 1), round(max(xs), 1),
              'y', round(min(ys), 1), round(max(ys), 1), 'z', round(min(zs), 1), round(max(zs), 1))
