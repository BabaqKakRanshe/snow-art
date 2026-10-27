"""One-off fix of a built .blend: glass panes that were built from both sides and then doubled by the build carry two
identical faces facing each way (darker glass, double transparent draws in Unity). Keeps one face per position and
direction among the faces with a glass material (M_Glass*); updates <name>.json's triangle counts.
python3 -I fix_glass_dupes.py out/main.blend"""
import bpy, bmesh, sys, os, json
path = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=path)
removed, removed_tris, by_root = 0, 0, {}
C = None
cp = path.replace('.blend', '_contract.json') if not path.endswith('main.blend') else os.path.join(os.path.dirname(path), 'main_contract.json')
if os.path.exists(cp):
    C = json.load(open(cp))
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.data
    glass = {i for i, m in enumerate(me.materials) if m and m.name.startswith('M_Glass')}
    if not glass:
        continue
    bm = bmesh.new()
    bm.from_mesh(me)
    seen, kill = set(), []
    for f in bm.faces:
        if f.material_index not in glass:
            continue
        k = (tuple(sorted((round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4)) for v in f.verts)),
             round(f.normal.x, 2), round(f.normal.y, 2), round(f.normal.z, 2))
        if k in seen:
            kill.append(f)
        else:
            seen.add(k)
    if kill:
        t = sum(len(f.verts) - 2 for f in kill)
        removed += len(kill)
        removed_tris += t
        root = C['parts'][o.name]['root'] if C and o.name in C['parts'] else o.name
        by_root[root] = by_root.get(root, 0) + t
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(me)
    bm.free()
bpy.ops.wm.save_as_mainfile(filepath=path)
ip = path.replace('.blend', '.json')
if os.path.exists(ip):
    I = json.load(open(ip))
    I['tris'] -= removed_tris
    for r, t in by_root.items():
        if 'tris_by_root' in I and r in I['tris_by_root']:
            I['tris_by_root'][r] -= t
    I['glass_dupes_removed'] = dict(faces=removed, tris=removed_tris)
    json.dump(I, open(ip, 'w'), indent=1)
print('removed duplicate glass faces', removed, 'tris', removed_tris, by_root)
