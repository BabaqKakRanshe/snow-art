import sys, bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
def geo(path):
    root, ver = parse_fbx.parse(path)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    objs = find(root, b'Objects')[0]
    models = {m.props[0]: m.props[1].split(b'\x00')[0].decode() for m in find(objs, b'Model')}
    geoms = {g.props[0]: tuple(round(v, 5) for v in find(g, b'Vertices')[0].props[0]) for g in find(objs, b'Geometry') if find(g, b'Vertices')}
    out = {}
    for c in find(find(root, b'Connections')[0], b'C'):
        if c.props[0] == b'OO' and c.props[1] in geoms and c.props[2] in models:
            out[models[c.props[2]]] = geoms[c.props[1]]
    return out
A = geo(sys.argv[-2]); B = geo(sys.argv[-1])
diff = [n for n in A if n.startswith('COL_') and A[n] != B.get(n)]
print('COL meshes changed:', diff)
