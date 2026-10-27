"""open the packaged forester's hut 1.1 from a clean unzip: every image resolves inside the package, the contract and
lamps agree with the blend, the doc, sheets, renders and sources are there, the three roots keep their map placement.
python3 -I verify_hut_pkg.py [forest_hut_v11_package.zip]"""
import bpy, os, sys, json, zipfile, tempfile, math
ZP = sys.argv[-1] if sys.argv[-1].endswith('.zip') else '/home/claude/hut11/out/forest_hut_v11_package.zip'
D = tempfile.mkdtemp(prefix='hut_pkg_check_')
zipfile.ZipFile(ZP).extractall(D)
root = os.path.join(D, 'forest_hut_v11')
files = sorted(os.path.relpath(os.path.join(r, f), root) for r, _, fs in os.walk(root) for f in fs)
print('files', len(files))
bpy.ops.wm.open_mainfile(filepath=os.path.join(root, 'hut.blend'))
bad = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    p = bpy.path.abspath(im.filepath)
    if not os.path.isfile(p) or not os.path.realpath(p).startswith(os.path.realpath(root)):
        bad.append(('image', im.name, im.filepath))
    else:
        im.reload()
        if im.size[0] == 0:
            bad.append(('image not loading', im.name))
C = json.load(open(os.path.join(root, 'hut_contract.json')))
L = json.load(open(os.path.join(root, 'hut_lights.json')))
for k, p in C['parts'].items():
    if p['object'] and p['object'] not in bpy.data.objects:
        bad.append(('part object missing', k))
    o = bpy.data.objects.get(k)
    if o is not None and p.get('parent') is None:
        if (o.matrix_world.translation - __import__('mathutils').Vector(p['pivot'])).length > 1e-4:
            bad.append(('root not at its pivot', k))
        if abs(math.degrees(o.matrix_world.to_euler().z) - p.get('yaw', 0.0)) > 0.01:
            bad.append(('root yaw', k))
for c in C['colliders']:
    if c['name'] not in bpy.data.objects:
        bad.append(('collider missing', c['name']))
for l in L['lights']:
    for k in ('socket', 'lens'):
        if l[k] not in bpy.data.objects:
            bad.append(('light', l['socket'], k))
    if l.get('glow') and l['glow'] not in bpy.data.objects:
        bad.append(('glow', l['glow']))
    if not os.path.isfile(os.path.join(root, 'tex', l['ies'])):
        bad.append(('light file missing', l['ies']))
for need in ('HUT_V11_CONTRACT.md', 'hut_A.jpg', 'hut_E.jpg', 'hut.json', 'renders/porch_day.png', 'src/hut_build.py', 'src/hut_kit.py',
             'src/checks/porch_fit.py',
             'src/gen_paint.py', 'tex/T_Hut_Hut_BaseColor.png', 'tex/T_Hut_HutProps_BaseColor.png', 'tex/T_Hut_Panel_BaseColor.png',
             'tex/T_Hut_Panel_Emission.png'):
    if need not in files:
        bad.append(('missing file', need))
for m in ('M_Hut_Lamp_Lantern', 'M_Hut_Lamp_Lantern_Off', 'M_Hut_Glow', 'M_Hut_Hut', 'M_Hut_HutProps', 'M_Hut_Panel', 'M_Hut_Glass'):
    if m not in bpy.data.materials:
        bad.append(('material missing', m))
mats = sorted({m.name for o in bpy.data.objects if o.type == 'MESH' for m in o.data.materials if m})
print('materials on meshes', mats)
print('objects', len([o for o in bpy.data.objects if o.type == 'MESH']), 'empties', len([o for o in bpy.data.objects if o.type == 'EMPTY']))
print('placement', {k: v['p'] for k, v in C['meta']['map_placement'].items()})
if C['meta'].get('version') != '1.1':
    bad.append(('contract version', C['meta'].get('version')))
print('PROBLEMS', bad or 'none')
