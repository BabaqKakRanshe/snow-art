"""Package the generator shed: the .blend with relative texture paths, textures, IES / cookies, the interaction
contract (JSON + Russian reference), lamps json, sheets, source scripts.  python3 -I pack_gen.py -> out/gen_package.zip"""
import os, sys, shutil, zipfile, glob
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'gen_package')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'gen')
for f in glob.glob(os.path.join(src_tex, '*.png')) + glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
for sub in ('IES', 'Cookies'):
    shutil.copytree(os.path.join(src_tex, sub), os.path.join(PK, 'tex', sub))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'gen.blend'))
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(PK, 'tex', name)):
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'gen.blend'), relative_remap=False)
for f in ('gen_contract.json', 'gen_lights.json', 'gen.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'GEN_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'gen_*.jpg'))):
    shutil.copy2(f, PK)
os.makedirs(os.path.join(PK, 'src'))
for f in ('gen_kit.py', 'gen_set.py', 'gen_room.py', 'gen_paint.py', 'gen_tex.py', 'gen_lights.py', 'gen_build.py',
          'gen_render.py', 'psxbake.py'):
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
zp = os.path.join(HERE, 'out', 'gen_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith('.blend1'):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('generator_shed', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
