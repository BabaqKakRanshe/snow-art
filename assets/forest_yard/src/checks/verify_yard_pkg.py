"""open the packaged yard from a clean unzip: every image resolves inside the package, the contract agrees with the blend
(objects, pivots in their roots' frames, colliders), the doc, sheets, sources and the map patch are there, both roots keep
their places (FuelTanks at the origin, Trafo beside it as on the map).
python3 -I verify_yard_pkg.py [forest_yard_package.zip]"""
import bpy, os, sys, json, zipfile, tempfile, math
from mathutils import Vector

ZP = sys.argv[-1] if sys.argv[-1].endswith('.zip') else '/home/claude/uaz/out/forest_yard_package.zip'
D = tempfile.mkdtemp(prefix='yard_pkg_check_')
zipfile.ZipFile(ZP).extractall(D)
root = os.path.join(D, 'forest_yard')
files = sorted(os.path.relpath(os.path.join(r, f), root) for r, _, fs in os.walk(root) for f in fs)
print('files', len(files))
bpy.ops.wm.open_mainfile(filepath=os.path.join(root, 'yard.blend'))
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
C = json.load(open(os.path.join(root, 'yard_contract.json')))
for k, p in C['parts'].items():
    o = bpy.data.objects.get(k)
    if p['object'] and o is None:
        bad.append(('part object missing', k))
        continue
    R = bpy.data.objects[p['root']].matrix_world
    if (R.inverted() @ o.matrix_world.translation - Vector(p['pivot'])).length > 1e-4:
        bad.append(('object not at its pivot (root frame)', k))
for c in C['colliders']:
    if c['name'] not in bpy.data.objects:
        bad.append(('collider missing', c['name']))
for k, s in C['sockets'].items():
    if s['parent'] not in bpy.data.objects:
        bad.append(('socket parent missing', k))
T = bpy.data.objects['Trafo'].matrix_world
if (T.translation - Vector((8.0, -10.0, -0.044))).length > 1e-4 or abs(math.degrees(T.to_euler().z) + 90.0) > 0.01:
    bad.append(('Trafo not at its place beside the tanks',))
if bpy.data.objects['FuelTanks'].matrix_world.translation.length > 1e-6:
    bad.append(('FuelTanks not at the origin',))
for need in ('YARD_CONTRACT.md', 'yard_A.jpg', 'yard_B.jpg', 'yard_C.jpg', 'yard_D.jpg', 'yard_E.jpg', 'yard.json', 'src/yard_build.py',
             'src/yard_kit.py', 'src/yard_paint.py', 'src/site_patch.py', 'src/site/fuel_site.json', 'src/site/fuel_site.blend',
             'src/gen_paint.py', 'tex/T_Yard_Tanks_BaseColor.png', 'tex/T_Yard_Trafo_BaseColor.png', 'tex/T_Yard_YardProps_BaseColor.png',
             'tex/T_Yard_Panel_BaseColor.png', 'tex/T_Yard_Panel_Emission.png', 'tex/T_Yard_ChainLink.png', 'tex/T_Yard_Barbed.png',
             'src/checks/walk.py', 'src/checks/probe_yard.py'):
    if need not in files:
        bad.append(('missing file', need))
for m in ('M_Yard_Tanks', 'M_Yard_Trafo', 'M_Yard_YardProps', 'M_Yard_Panel', 'M_Yard_ChainLink', 'M_Yard_Barbed'):
    if m not in bpy.data.materials:
        bad.append(('material missing', m))
mats = sorted({m.name for o in bpy.data.objects if o.type == 'MESH' for m in o.data.materials if m})
print('materials on meshes', mats)
print('objects', len([o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_')]),
      'colliders', len([o for o in bpy.data.objects if o.name.startswith('COL_')]))
print('placement', {k: v['p'] for k, v in C['meta']['map_placement'].items()})
print('PROBLEMS', bad or 'none')
