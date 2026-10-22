import bpy, json, os
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
S = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad'
L = json.load(open(S + '/u3/Assets/Locations/Forest/Data/Forest_Layout.json'))
kind = {(i['model'], i['child']): i['kind'] for i in L['interactables']}
def trans(fp):
    root, ver = parse_fbx.parse(fp)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    out = {}
    for e in find(root, b'Objects')[0].elems:
        if e.id != b'Model': continue
        nm = e.props[1].split(b'\x00')[0].decode()
        t = [0.0, 0.0, 0.0]
        for pp in find(find(e, b'Properties70')[0], b'P'):
            if pp.props[0] == b'Lcl Translation': t = list(pp.props[4:7])
        out[nm] = (-t[0], t[1], t[2])       # Unity
    return out
rows = []
for m in sorted({k[0] for k in kind}):
    a = S + '/u3/Assets/Locations/Forest/Models/' + m + '.fbx'; b = S + '/u4/fbx2/' + m + '.fbx'
    if not (os.path.exists(a) and os.path.exists(b)): continue
    ta, tb = trans(a), trans(b)
    for (mm, c), k in kind.items():
        if mm != m or c not in ta or c not in tb: continue
        d = [tb[c][i] - ta[c][i] for i in range(3)]
        h = (d[0] ** 2 + d[2] ** 2) ** 0.5
        rows.append((m, c, k, round(h, 3), round(d[1], 3)))
big = [r for r in rows if r[3] > 0.02 or abs(r[4]) > 0.02]
print('IX compared', len(rows), 'moved >2 cm', len(big))
for r in big: print('  ', r)
