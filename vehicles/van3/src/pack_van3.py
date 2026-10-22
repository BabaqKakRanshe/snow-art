"""Package van v3 for the user: the .blend with relative texture paths, textures, IES / cookies, the interaction
contract (JSON + Russian reference), lamps json, sheets.  python3 -I pack_van3.py -> out/van3_package.zip"""
import os, sys, shutil, zipfile, glob
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'van3_package')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'van3')
for f in glob.glob(os.path.join(src_tex, '*.png')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
for sub in ('IES', 'Cookies'):
    shutil.copytree(os.path.join(src_tex, sub), os.path.join(PK, 'tex', sub))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'van3.blend'))
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(PK, 'tex', name)):
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'van3.blend'), relative_remap=False)
for f in ('van3_contract.json', 'van3_lights.json', 'van3.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'VAN3_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'van3_*.jpg'))):
    shutil.copy2(f, PK)
zp = os.path.join(HERE, 'out', 'van3_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in files:
            if f.endswith('.blend1'):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('van3', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
