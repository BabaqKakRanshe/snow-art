"""Checks the Forest Update 6 FBX against the export report and the blends.

Static models (GenContainer, the 84 items): every object comes back from the file (Blender's importer undoes the same axis
and unit conversion) with the same world bounds (1 mm), pivots, triangles and materials; the file is in Update 3's
convention (Y up, front +Z, UnitScaleFactor 100); children carry translations only (u5_verify_fbx.py's checks).
Apparition: the axis settings; one armature (19 bones) and one skinned mesh (its triangles, M_Apparition); four takes with
their frame ranges; each clip played back from the file gives the same deformed mesh as fig.blend (world bounds within
5 mm at the checked frames: Stand 1, Walk 1 / 8 / 16 / 24, Sit 1, SitLook 8 / 15).

python3 -I u6_verify_fbx.py -- <fbx_dir> <fig.blend>"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

a = sys.argv[sys.argv.index('--') + 1:]
d, fig_blend = a[0], a[1]
R = json.load(open(os.path.join(d, 'u6_export_report.json')))
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import parse_fbx

problems = []
find = lambda e, n: [c for c in e.elems if c.id == n]


def settings(fp):
    root, ver = parse_fbx.parse(fp)
    gs = {p.props[0].decode(): p.props[-1] for p in find(find(root, b'GlobalSettings')[0], b'Properties70')[0].elems}
    return root, gs


WANT = {'UpAxis': 1, 'UpAxisSign': 1, 'FrontAxis': 2, 'FrontAxisSign': 1, 'CoordAxis': 0, 'CoordAxisSign': 1}
for name, rep in sorted(R.items()):
    if rep.get('skinned'):
        continue
    fp = os.path.join(d, rep['file'])
    root, gs = settings(fp)
    for k, v in dict(WANT, UnitScaleFactor=100.0).items():
        if gs.get(k) != v:
            problems.append(f'{name}: GlobalSettings {k} = {gs.get(k)} (want {v})')
    for e in find(root, b'Objects')[0].elems:
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
    if tris != rep['tris']:
        problems.append(f'{name}: {tris} tris in the file, {rep["tris"]} in the blend')
    mats = sorted({m.name.split('.')[0] for o in got.values() for m in o.data.materials if m})
    if mats != rep['materials']:
        problems.append(f'{name}: materials {mats} vs {rep["materials"]}')
    print(f'[verify] {name}: {len(got)} objects, {tris} tris, {len(mats)} materials', flush=True)

# ---------------------------------------------------------------- the Apparition
FRAMES = {'Stand': [1], 'Walk': [1, 8, 16, 24], 'Sit': [1], 'SitLook': [8, 15]}
rep = R['Apparition']


def posed_bounds(arm, body, action, frame):
    arm.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    e = body.evaluated_get(dg)
    m = e.to_mesh()
    vs = [body.matrix_world @ v.co for v in m.vertices]
    e.to_mesh_clear()
    return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]


bpy.ops.wm.open_mainfile(filepath=fig_blend)
arm0, body0 = bpy.data.objects['Apparition_Rig'], bpy.data.objects['Apparition_Body']
ref = {(c, f): posed_bounds(arm0, body0, bpy.data.actions[c], f) for c, fs in FRAMES.items() for f in fs}
fp = os.path.join(d, rep['file'])
root, gs = settings(fp)
for k, v in WANT.items():
    if gs.get(k) != v:
        problems.append(f'Apparition: GlobalSettings {k} = {gs.get(k)} (want {v})')
takes = sorted(e.props[0].split(b'\x00')[0].decode() for e in find(root, b'Takes')[0].elems if e.id == b'Take') \
    if find(root, b'Takes') else []
want_takes = sorted(f'Apparition_Rig|{c}' for c in rep['clips'])
if takes != want_takes:
    problems.append(f'Apparition: takes {takes} (want {want_takes})')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = rep['fps']
bpy.ops.import_scene.fbx(filepath=fp)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if len(arms) != 1 or len(meshes) != 1:
    problems.append(f'Apparition: {len(arms)} armatures, {len(meshes)} meshes')
else:
    arm, body = arms[0], meshes[0]
    bones = [b.name for b in arm.data.bones]
    if sorted(bones) != sorted(rep['bones']):
        problems.append(f'Apparition: bones {sorted(set(rep["bones"]) ^ set(bones))} differ')
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    if tris != rep['tris']:
        problems.append(f'Apparition: {tris} tris (want {rep["tris"]})')
    mats = sorted(m.name.split('.')[0] for m in body.data.materials)
    if mats != rep['materials']:
        problems.append(f'Apparition: materials {mats}')
    if not body.find_armature():
        problems.append('Apparition: the mesh is not skinned to the armature')
    acts = {ac.name.split('|')[-1]: ac for ac in bpy.data.actions}
    for c, (lo, hi) in rep['clips'].items():
        ac = acts.get(c)
        if ac is None:
            problems.append(f'Apparition: no action {c} after import')
            continue
        fr = [int(round(v)) for v in ac.frame_range]
        if fr != [lo, hi]:
            problems.append(f'Apparition: {c} frames {fr} (want {[lo, hi]})')
    worst = 0.0
    for (c, f), (rlo, rhi) in ref.items():
        if c not in acts:
            continue
        lo, hi = posed_bounds(arm, body, acts[c], f)
        dev = max(max(abs(lo[i] - rlo[i]), abs(hi[i] - rhi[i])) for i in range(3))
        worst = max(worst, dev)
        if dev > 0.005:
            problems.append(f'Apparition: {c} frame {f}: posed bounds off by {dev:.4f} m')
    print(f'[verify] Apparition: {len(bones)} bones, {tris} tris, takes {takes}, posed bounds worst {worst * 1000:.2f} mm', flush=True)

print('PROBLEMS', len(problems))
for p in problems:
    print('  ', p)
json.dump(problems, open(os.path.join(d, 'u6_verify_fbx.json'), 'w'), indent=1)
