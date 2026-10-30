"""Package forest_smoke 2.0 (the pager's pack_pager): the .blend with relative texture paths, the textures, the json contract
and stats, the sheet, the renders, the source (self-contained with the library modules it needs); the Russian reference
goes to docs/gdd (SMOKE_CONTRACT.md), not into the package.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_smoke/smoke2_pack.py
-> source/assets/forest_smoke/"""
import os, sys, shutil, ast
import bpy
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, '..', '..', 'lib'))
PK = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'source', 'assets', 'forest_smoke'))
SRC = ['smoke2_kit.py', 'smoke2_tex.py', 'smoke2_paint.py', 'smoke2_build.py', 'smoke2_quick.py', 'smoke2_export.py', 'smoke2_pack.py']
RENDERS = ['line', 'front', 'open', 'back3q', 'lighter', 'cig']
CONCEPTS = ['packs_1.png', 'lighter_1.png']
README = ('Исходники пакета forest_smoke 2.0: три пачки сигарет (Harzgold, Brocken, Nordlicht), зажигалка BLITZ, сигарета. '
          'Пакет — папка выше, справочник — docs/gdd/SMOKE_CONTRACT.md, концепты — docs/gdd/concept/09_smoking (выбраны '
          'packs_1 и lighter_1). Собран локально (скилл snow-model) по образцу пейджера forest_pager.\n\n'
          '- smoke2_kit.py — геометрия, детали и точки; smoke2_tex.py — печать пачек (2000 px/м), этикетка и пламя зажигалки, '
          'фильтры, огонёк, клуб дыма; smoke2_paint.py — покраска атласа Small.\n'
          '- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- '
          'tools/snow_style/work/forest_smoke/smoke2_build.py [--draft]; потом smoke2_quick.py <blend> <папка> [виды], '
          'smoke2_pack.py; FBX для Unity — blender -b --factory-startup <smoke.blend> --python smoke2_export.py -- <папка>.\n')
local = {os.path.splitext(f)[0]: d for d in (HERE, LIB) for f in os.listdir(d) if f.endswith('.py')}


def closure(files):
    need, todo = set(), list(files)
    while todo:
        f = todo.pop()
        path = os.path.join(local[os.path.splitext(f)[0]], f)
        for node in ast.walk(ast.parse(open(path, encoding='utf-8').read())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in {n.split('.')[0] for n in names if n.split('.')[0] in local}:
                if n + '.py' not in files and n not in need:
                    need.add(n)
                    todo.append(n + '.py')
    return sorted(n + '.py' for n in need)


if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'smoke.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
for extra in ('smoke_regions.json', 'T_Smoke_Puff.png'):
    shutil.copy2(os.path.join(HERE, 'tex2', extra), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'smoke.blend'), relative_remap=False)
for f in ('smoke_contract.json', 'smoke.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
os.makedirs(os.path.join(PK, 'renders'))
shots = []
for r in RENDERS:
    p = os.path.join(HERE, 'rend', 'full', r + '.png')
    shutil.copy2(p, os.path.join(PK, 'renders', r + '.png'))
    shots.append((r, Image.open(p).convert('RGB')))
concept_dir = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'docs', 'gdd', 'concept', '09_smoking'))
for c in CONCEPTS:
    shots.append(('concept ' + c[:-4], Image.open(os.path.join(concept_dir, c)).convert('RGB')))
# the sheet: renders and the picked concepts in a 4 x 2 grid
cw, ch = 480, 300
sheet = Image.new('RGB', (cw * 4, ch * 2 + 40), (28, 28, 30))
dr = ImageDraw.Draw(sheet)
dr.text((12, 12), 'forest_smoke 2.0 - packs Harzgold / Brocken / Nordlicht, lighter BLITZ, cigarette: 594 tris, atlas Small 256 at '
                  '512 px/m, pack prints 512 x 256 at 2000 px/m', fill=(230, 226, 214))
for i, (name, im) in enumerate(shots[:8]):
    im = im.copy()
    im.thumbnail((cw - 8, ch - 24))
    x, y = (i % 4) * cw, 40 + (i // 4) * ch
    sheet.paste(im, (x + 4, y + 20))
    dr.text((x + 6, y + 4), name, fill=(200, 196, 184))
sheet.save(os.path.join(PK, 'forest_smoke_A.jpg'), quality=90)
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(local[os.path.splitext(f)[0]], f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека (копии из tools/snow_style/lib): ' + ', '.join(lib_) + '.\n- Blender 5.2.3.\n')
print('packed', PK, sum(len(fs) for _, _, fs in os.walk(PK)), 'files')
