"""Checks the Forest Update 4 FBX against the export report: every object comes back from the file (Blender's importer,
which undoes the same axis and unit conversion) with the same world bounds (1 mm), triangles and materials; the file is in
Update 3's convention (Y up, front +Z, UnitScaleFactor 100); children carry translations only (no rotation, no scale).

python3 -I u4_verify_fbx.py -- <fbx_dir>"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

a = sys.argv[sys.argv.index('--') + 1:]
d = a[0]
R = json.load(open(os.path.join(d, 'u4_export_report.json')))
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx

problems = []
for name, rep in sorted(R.items()):
    fp = os.path.join(d, rep['file'])
    # 1. file conventions straight from the FBX tree
    root, ver = parse_fbx.parse(fp)
    find = lambda e, n: [c for c in e.elems if c.id == n]
    gs = {p.props[0].decode(): p.props[-1] for p in find(find(root, b'GlobalSettings')[0], b'Properties70')[0].elems}
    want = {'UpAxis': 1, 'UpAxisSign': 1, 'FrontAxis': 2, 'FrontAxisSign': 1, 'CoordAxis': 0, 'CoordAxisSign': 1,
            'UnitScaleFactor': 100.0}
    for k, v in want.items():
        if gs.get(k) != v:
            problems.append(f'{name}: GlobalSettings {k} = {gs.get(k)} (want {v})')
    objs = find(root, b'Objects')[0]
    for e in objs.elems:
        if e.id != b'Model':
            continue
        nm = e.props[1].split(b'\x00')[0].decode()
        kind = e.props[2].decode()
        if kind != 'Mesh':
            problems.append(f'{name}: node {nm} is {kind}')
        for pp in find(find(e, b'Properties70')[0], b'P'):
            key = pp.props[0]
            vals = [round(v, 5) for v in pp.props[4:7]]
            if key == b'Lcl Rotation' and any(abs(v) > 1e-4 for v in vals):
                problems.append(f'{name}: {nm} has rotation {vals}')
            if key == b'Lcl Scaling' and any(abs(v - 1) > 1e-5 for v in vals):
                problems.append(f'{name}: {nm} has scale {vals}')
            if nm == name and key == b'Lcl Translation' and any(abs(v) > 1e-6 for v in vals):
                problems.append(f'{name}: root translated {vals}')
    # 2. geometry back through Blender's importer
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fp)
    got = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
    if set(got) != set(rep['objects']):
        problems.append(f'{name}: objects differ: missing {sorted(set(rep["objects"]) - set(got))}, extra {sorted(set(got) - set(rep["objects"]))}')
    tris = 0
    for on, o in got.items():
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        if on not in rep['aabb']:
            continue
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        lo = [min(v[i] for v in vs) for i in range(3)]
        hi = [max(v[i] for v in vs) for i in range(3)]
        dev = max(max(abs(lo[i] - rep['aabb'][on][0][i]), abs(hi[i] - rep['aabb'][on][1][i])) for i in range(3))
        if dev > 0.001:
            problems.append(f'{name}: {on} bounds off by {dev:.4f} m')
        pv = o.matrix_world.translation
        dp = max(abs(pv[i] - rep['pivots'][on][i]) for i in range(3))
        if dp > 0.001:
            problems.append(f'{name}: {on} pivot off by {dp:.4f} m')
        if not any(p.use_smooth for p in o.data.polygons) and o.data.has_custom_normals is False:
            pass
    if tris != rep['tris']:
        problems.append(f'{name}: {tris} tris in the file, {rep["tris"]} in the blend')
    mats = sorted({m.name.split('.')[0] for o in got.values() for m in o.data.materials if m})
    if mats != rep['materials']:
        problems.append(f'{name}: materials {mats} vs {rep["materials"]}')
    print(f'[verify] {name}: {len(got)} objects, {tris} tris, {len(mats)} materials', flush=True)

print('PROBLEMS', len(problems))
for p in problems:
    print('  ', p)
json.dump(problems, open(os.path.join(d, 'u4_verify_fbx.json'), 'w'), indent=1)
