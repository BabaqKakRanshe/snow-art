"""Package the forester's hut: the .blend with relative texture paths, textures and IES, the interaction contract (JSON +
Russian reference), lamps json, sheets, the full source (self-contained) with the checks.
python3 -I pack_hut.py [checks_dir] -> out/forest_hut_package.zip (folder forest_hut/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_hut')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'hut')
for f in glob.glob(os.path.join(src_tex, '*.png')) + glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
shutil.copytree(os.path.join(src_tex, 'IES'), os.path.join(PK, 'tex', 'IES'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'hut.blend'))
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(PK, 'tex', name)):
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'hut.blend'), relative_remap=False)
for f in ('hut_contract.json', 'hut_lights.json', 'hut.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'HUT_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'hut_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['hut_kit.py', 'hut_tex.py', 'hut_paint.py', 'hut_build.py', 'hut_render.py', 'make_hut_doc.py', 'make_sheets_hut.py',
       'pack_hut.py',
       'gen_kit.py', 'gen_tex.py', 'gen_paint.py', 'gen_lights.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py',
       'van2_kit.py', 'van2_tex.py', 'van3_mech.py', 'van_lights.py', 'ies_lm63.py', 'post_bloom.py']
os.makedirs(os.path.join(PK, 'src'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
need = set()
for f in SRC:
    for node in ast.walk(ast.parse(open(os.path.join(HERE, f)).read())):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        need |= {n.split('.')[0] for n in names if n.split('.')[0] in local}
lost = sorted(n for n in need if n + '.py' not in SRC)
assert not lost, f'local modules imported but not packed: {lost}'
if CHECKS:
    os.makedirs(os.path.join(PK, 'src', 'checks'))
    for f in sorted(glob.glob(os.path.join(CHECKS, '*.py'))):
        shutil.copy2(f, os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники хижины лесника. Пакет — папка выше (hut.blend, атласы, контракт), архив — ../../forest_hut_package.zip,\n'
    'справочник — docs/gdd/HUT_CONTRACT.md.\n\n'
    '- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).\n'
    '- Порядок: hut_build.py → out/hut.blend, hut.json, hut_contract.json, hut_lights.json, tex/hut\n'
    '  (hut_build.py --draft — черновик без запекания); hut_render.py <виды через запятую> [spp] → rend/hut;\n'
    '  make_hut_doc.py → docs/HUT_CONTRACT.md; make_sheets_hut.py → sheets/hut_A…D.jpg; pack_hut.py → out/forest_hut_package.zip.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.\n'
    '- checks/ — проверки: ход деталей, проходимость и места предметов, совпадающие и вывернутые грани, фонарь с дороги, '
    'пакет.\n'
    '- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.\n')
lines = []
for r, ds, fs in os.walk(os.path.join(PK, 'src')):
    ds.sort()
    for f in sorted(fs):
        if f.endswith('.py'):
            p = os.path.join(r, f)
            d = ast.get_docstring(ast.parse(open(p).read())) or ''
            lines.append(f'{os.path.relpath(p, os.path.join(PK, "src")):40s} {d.strip().splitlines()[0] if d.strip() else ""}')
open(os.path.join(PK, 'src', 'SCRIPTS_INDEX.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
zp = os.path.join(HERE, 'out', 'forest_hut_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_hut', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
