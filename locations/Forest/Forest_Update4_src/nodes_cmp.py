import bpy
import sys, json, os
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx
S = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad'
U3M = S + '/u3/Assets/Locations/Forest/Models/'
R = json.load(open(S + '/u4/fbx/u4_export_report.json'))
L = json.load(open(S + '/u3/Assets/Locations/Forest/Data/Forest_Layout.json'))
def nodes(fp):
    root, ver = parse_fbx.parse(fp)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    out = {}
    for e in find(root, b'Objects')[0].elems:
        if e.id == b'Model':
            nm = e.props[1].split(b'\x00')[0].decode()
            mats = []
            out[nm] = 1
    return out
probs = []
for name in sorted(R):
    mine = set(nodes(S + '/u4/fbx/' + name + '.fbx'))
    u3p = U3M + name + '.fbx'
    u3 = set(nodes(u3p)) if os.path.exists(u3p) else None
    refs = set()
    for it in L['interactables']:
        if it['model'] == name: refs.add(it['child'])
        for dv in (it.get('drives') or []):
            if it['model'] == name: refs.add(dv)
    for a in L['lighting'].get('assign', []):
        if a['model'] == name: refs.add(a['node'])
    for pl in L['prefabLights']:
        if pl['model'] == name:
            for l in pl['lights']:
                if l.get('fx'): refs.add(l['fx'])
    for pg in L['prefabGlows']:
        if pg['model'] == name:
            for g in pg['glows']:
                if g.get('fx'): refs.add(g['fx'])
    for rd in (L.get('rotators') or []):
        if rd['model'] == name and rd.get('child'): refs.add(rd['child'])
    missing_refs = sorted(refs - mine)
    if missing_refs: probs.append((name, 'layout refs missing', missing_refs))
    if u3 is not None:
        gone = sorted(u3 - mine); new = sorted(mine - u3)
        print(f'{name:18s} u3 {len(u3):4d} mine {len(mine):4d} refs {len(refs):4d} | only u3: {gone[:12]}{"..." if len(gone)>12 else ""} | new: {new[:10]}{"..." if len(new)>10 else ""}')
    else:
        print(f'{name:18s} (no U3 FBX here) mine {len(mine)} refs {len(refs)}')
print('PROBLEMS', probs)
