"""Package forest_pager 1.0 (adapted from forest_gear's pack_gear): the .blend with relative texture paths, the textures, the
json contract and stats, the sheet, the renders, the source (self-contained with the library modules it needs); the Russian
reference goes to docs/gdd (PAGER_CONTRACT.md), not into the package.
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_pager/pack_pager.py
-> source/assets/forest_pager/"""
import os, sys, shutil, ast
import bpy
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, '..', '..', 'lib'))
PK = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'source', 'assets', 'forest_pager'))
SRC = ['pager_kit.py', 'pager_tex.py', 'pager_paint.py', 'pager_build.py', 'pager_quick.py', 'pager_render.py', 'pack_pager.py']
RENDERS = [('rend/pager', 'desk'), ('rend/pager', 'night'), ('rend/full', 'front'), ('rend/full', 'front3q'),
           ('rend/full', 'back3q'), ('rend/full', 'side'), ('rend/full', 'top')]
README = ('Исходники пакета forest_pager 1.0: пейджер рабочего (вид 1 «Cityruf», docs/gdd/research/RESEARCH_UI_3.md). '
          'Пакет — папка выше, справочник — docs/gdd/PAGER_CONTRACT.md. Собран локально (скилл snow-model) по образцу рации '
          'forest_gear.\n\n'
          '- pager_kit.py — геометрия, детали и точки; pager_tex.py — панель надписей (лицо, наклейка, верх) и экран 20 x 4 '
          'знака (горит / погашен); pager_paint.py — покраска атласа.\n'
          '- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- '
          'tools/snow_style/work/forest_pager/pager_build.py [--draft]; потом pager_quick.py -- <blend> <папка> [виды], '
          'pager_render.py [виды|all] [spp], pack_pager.py.\n')
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'pager.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'pager', 'pager_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'pager.blend'), relative_remap=False)
for f in ('pager_contract.json', 'pager.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
os.makedirs(os.path.join(PK, 'renders'))
shots = []
for d, r in RENDERS:
    p = os.path.join(HERE, d, r + '.png')
    shutil.copy2(p, os.path.join(PK, 'renders', r + '.png'))
    shots.append((r, Image.open(p).convert('RGB')))
# the sheet: the renders in a 4 x 2 grid, the atlas and the LCD (nearest, x4) in the last cell
cw, ch = 480, 384
sheet = Image.new('RGB', (cw * 4, ch * 2 + 40), (28, 28, 30))
dr = ImageDraw.Draw(sheet)
dr.text((12, 12), 'forest_pager 1.0 - Item_Pager (Cityruf look): 302 tris, atlas Small 128 px at 512 px/m, panel 128, LCD 124 x 40',
        fill=(230, 226, 214))
for i, (name, im) in enumerate(shots):
    im = im.copy()
    im.thumbnail((cw - 8, ch - 24))
    x, y = (i % 4) * cw, 40 + (i // 4) * ch
    sheet.paste(im, (x + 4, y + 20))
    dr.text((x + 6, y + 4), name, fill=(200, 196, 184))
tx = os.path.join(PK, 'tex')
at = Image.open(os.path.join(tx, 'T_Pager_Small_BaseColor.png')).convert('RGB').resize((256, 256), Image.NEAREST)
lc = Image.open(os.path.join(tx, 'T_Pager_LCD_Emission.png')).convert('RGB').resize((124 * 2, 40 * 2), Image.NEAREST)
pn = Image.open(os.path.join(tx, 'T_Pager_Panel_BaseColor.png')).convert('RGB').resize((192, 192), Image.NEAREST)
x, y = 3 * cw, 40 + ch
sheet.paste(at, (x + 4, y + 20))
sheet.paste(pn, (x + 268, y + 20))
sheet.paste(lc, (x + 4, y + 290))
dr.text((x + 6, y + 4), 'atlas / panel / LCD', fill=(200, 196, 184))
sheet.save(os.path.join(PK, 'forest_pager_A.jpg'), quality=90)
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(local[os.path.splitext(f)[0]], f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека (копии из tools/snow_style/lib): ' + ', '.join(lib_) + '.\n- Blender 5.2.3.\n')
print('packed', PK, sum(len(fs) for _, _, fs in os.walk(PK)), 'files')
