"""Package forest_beer (the pager's pack_pager): the .blend with relative texture paths, the textures, the json contract
and stats, the sheet, the renders, the source (self-contained with the library modules it needs); the Russian reference
goes to docs/gdd (BEER_CONTRACT.md), not into the package.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_beer/beer_pack.py
-> source/assets/forest_beer/"""
import os, sys, shutil, ast
import bpy
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, '..', '..', 'lib'))
PK = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'source', 'assets', 'forest_beer'))
SRC = ['beer_kit.py', 'beer_tex.py', 'beer_paint.py', 'beer_build.py', 'beer_quick.py', 'beer_export.py', 'beer_pack.py']
RENDERS = ['line', 'front', 'back', 'open', 'lever', 'crushed']
CONCEPTS = ['concept_v1/cans_1.png', 'concept_v2/kalo_front_1.png', 'ingame/held_1.png']
README = ('Исходники пакета forest_beer: шесть банок пива (Harzer Pils, Ilsetaler Export, Hexenbräu Schwarzbier, Bergmann Bock, '
          'Schneekönig Leicht, Kaloschnizzer Starkbier) и мятая банка каждой марки. Пакет — папка выше, справочник — '
          'docs/gdd/BEER_CONTRACT.md, концепты — docs/gdd/items/beer/concept_v1/cans_1.png (выбран 29.10), '
          'concept_v2/kalo_front_1.png (шестая, выбрана 30.10). Собран локально (скилл snow-model) по образцу '
          'пакета forest_smoke.\n\n'
          '- beer_kit.py — геометрия, детали (язычок, клапан) и точки; beer_tex.py — этикетки: перед развёрнут из концепта, '
          'зад дорисован пиксельным шрифтом; beer_paint.py — покраска атласа Small (жесть, крышка, язычок, темнота внутри).\n'
          '- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- '
          '<абсолютный путь>/tools/snow_style/work/forest_beer/beer_build.py [--draft]; потом beer_quick.py <blend> <папка> [виды], '
          'beer_pack.py; FBX для Unity — blender -b --factory-startup <beer.blend> --python beer_export.py -- <папка>.\n')
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'beer.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
for extra in ('beer_labels.json',):
    shutil.copy2(os.path.join(HERE, 'tex', extra), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'beer.blend'), relative_remap=False)
for f in ('beer_contract.json', 'beer.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
os.makedirs(os.path.join(PK, 'renders'))
shots = []
for r in RENDERS:
    p = os.path.join(HERE, 'rend', 'full', r + '.png')
    shutil.copy2(p, os.path.join(PK, 'renders', r + '.png'))
    shots.append((r, Image.open(p).convert('RGB')))
concept_dir = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'docs', 'gdd', 'items', 'beer'))
for c in CONCEPTS:
    shots.append((c[:-4], Image.open(os.path.join(concept_dir, c)).convert('RGB')))
# the sheet: renders and the picked concepts in a 5 x 2 grid
cw, ch = 480, 300
sheet = Image.new('RGB', (cw * 5, ch * 2 + 40), (28, 28, 30))
dr = ImageDraw.Draw(sheet)
dr.text((12, 12), 'forest_beer 1.1 - six cans (708 tris, tab + flap) and six crushed (868 tris); atlas Small 512 at 512 px/m, '
                  'labels 512 wide once round (2470 px/m)', fill=(230, 226, 214))
for i, (name, im) in enumerate(shots[:10]):
    im = im.copy()
    im.thumbnail((cw - 8, ch - 24))
    x, y = (i % 5) * cw, 40 + (i // 5) * ch
    sheet.paste(im, (x + 4, y + 20))
    dr.text((x + 6, y + 4), name, fill=(200, 196, 184))
sheet.save(os.path.join(PK, 'forest_beer_A.jpg'), quality=90)
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(local[os.path.splitext(f)[0]], f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека (копии из tools/snow_style/lib): ' + ', '.join(lib_) + '.\n- Blender 5.2.3.\n')
print('packed', PK, sum(len(fs) for _, _, fs in os.walk(PK)), 'files')
