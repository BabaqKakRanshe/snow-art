"""Compare two FBX files: model names, parents, local transforms; geometry vertex counts by model."""
import sys, bpy, addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
def load(path):
    root, ver = parse_fbx.parse(path)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    objs = find(root, b'Objects')[0]
    models, geoms = {}, {}
    for m in find(objs, b'Model'):
        uid = m.props[0]; name = m.props[1].split(b'\x00')[0].decode()
        pr = {}
        for pp in find(find(m, b'Properties70')[0], b'P'):
            if pp.props[0] in (b'Lcl Translation', b'Lcl Rotation', b'Lcl Scaling'):
                pr[pp.props[0].decode()[4:]] = tuple(round(v, 5) for v in pp.props[4:7])
        models[uid] = (name, pr)
    for g in find(objs, b'Geometry'):
        v = find(g, b'Vertices')
        geoms[g.props[0]] = len(v[0].props[0]) // 3 if v else 0
    par, geo = {}, {}
    for c in find(find(root, b'Connections')[0], b'C'):
        if c.props[0] == b'OO':
            a, b = c.props[1], c.props[2]
            if a in models:
                par[models[a][0]] = models[b][0] if b in models else 'ROOT'
            if a in geoms and b in models:
                geo[models[b][0]] = geoms[a]
    return {n: (pr, par.get(n), geo.get(n)) for n, pr in models.values()}
A = load(sys.argv[-2]); B = load(sys.argv[-1])
print('models', len(A), len(B), 'only A', sorted(set(A) - set(B)), 'only B', sorted(set(B) - set(A)))
tr = [n for n in A if n in B and (A[n][0] != B[n][0] or A[n][1] != B[n][1])]
print('transform / parent changed:', tr)
gv = [(n, A[n][2], B[n][2]) for n in A if n in B and A[n][2] != B[n][2]]
print('geometry vertex count changed:', len(gv))
for g in gv: print('  ', g)
