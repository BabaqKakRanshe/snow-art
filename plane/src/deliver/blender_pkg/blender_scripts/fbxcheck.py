"""Print FBX global axes + per-model local transforms, and what Unity will show (X mirrored)."""
import sys, bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx

root, ver = parse_fbx.parse(sys.argv[1])
find = lambda e, n: [c for c in e.elems if c.id == n]
gs = find(find(root, b'GlobalSettings')[0], b'Properties70')[0]
print('FBX', ver, {p.props[0].decode(): p.props[-1] for p in gs.elems
                   if p.props[0] in (b'UpAxis', b'FrontAxis', b'FrontAxisSign', b'UnitScaleFactor')})
for m in find(find(root, b'Objects')[0], b'Model'):
    name = m.props[1].split(b'\x00')[0].decode()
    pr = {}
    for pp in find(find(m, b'Properties70')[0], b'P'):
        if pp.props[0] in (b'Lcl Translation', b'Lcl Rotation', b'Lcl Scaling'):
            pr[pp.props[0].decode()[4:]] = [round(v, 3) for v in pp.props[4:7]]
    t = pr.get('Translation', [0, 0, 0])
    r = pr.get('Rotation', [0, 0, 0])
    s = pr.get('Scaling', [1, 1, 1])
    ut = [-t[0], t[1], t[2]]
    ur = [r[0], -r[1] + 0.0, -r[2] + 0.0]
    print(f'{name:15s} Unity pos {ut}  rot {ur}  scale {s}')
