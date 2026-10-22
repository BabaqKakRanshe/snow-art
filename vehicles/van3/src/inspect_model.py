"""Import a downloaded vehicle model, write a report and quick views.
python3 -I inspect_model.py <model file or zip> <tag>   -> work/<tag>_import.blend, work/<tag>_report.json, rend/<tag>_*.png"""
import sys, os
sys.path.insert(0, '/home/claude/uaz')
import bpy
import psxlib as P

src, tag = sys.argv[1], sys.argv[2]
W = os.path.join(P.HERE, 'work')
os.makedirs(W, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
path = P.unpack(src, os.path.join(P.HERE, 'src'))
objs = P.import_any(path)
rep = P.report(objs, os.path.join(W, f'{tag}_report.json'))
print('MODEL', path)
print('objects', rep['objects'], 'meshes', rep['meshes'], 'tris', rep['tris'], 'size', rep['size'])
for r in rep['mesh_rows'][:40]:
    print(f"  {r['name'][:40]:40s} tris {r['tris']:7d}  mats {','.join(r['mats'])[:60]}  uv {len(r['uv'])}")
for m in rep['materials']:
    print('  MAT', m['name'], m.get('color', ''), m['maps'], 'alpha', m.get('alpha'), m.get('blend'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(W, f'{tag}_import.blend'))
print(P.quick_views(objs, os.path.join(P.HERE, 'rend'), tag))
