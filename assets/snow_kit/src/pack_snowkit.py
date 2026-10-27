"""Package the snow kit: snow_kit.blend with relative texture paths, the atlas, the panel, the screens and the beacon's IES,
the contract (JSON + the Russian reference, also in docs/gdd), lamps json, sheets A-D, renders, the full source (self-contained)
with the inventory of the old packages and the Unity wire script.
python3 -I pack_snowkit.py -> out/snow_kit/ and out/snow_kit_package.zip (folder snow_kit/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
INV = '/home/claude/snowkit'
PK = os.path.join(HERE, 'out', 'snow_kit')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'snow_kit')
for f in sorted(glob.glob(os.path.join(src_tex, 'T_Kit_*.png'))) + [os.path.join(src_tex, 'kit_panel_regions.json')]:
    shutil.copy2(f, os.path.join(PK, 'tex'))
shutil.copytree(os.path.join(src_tex, 'IES'), os.path.join(PK, 'tex', 'IES'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'snow_kit.blend'))
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(PK, 'tex', name)):
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
assert not bpy.data.libraries, [l.filepath for l in bpy.data.libraries]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'snow_kit.blend'), relative_remap=False)
for f in ('snow_kit.json', 'snow_kit_contract.json', 'snow_kit_lights.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'SNOW_KIT_CONTRACT.md'), PK)          # the same file goes to docs/gdd
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'snow_kit_[A-D].jpg'))):
    shutil.copy2(f, PK)
os.makedirs(os.path.join(PK, 'renders', 'models'))
for f in sorted(glob.glob(os.path.join(HERE, 'rend', 'snow_kit_cycles', '*.png'))):
    shutil.copy2(f, os.path.join(PK, 'renders'))
for f in sorted(glob.glob(os.path.join(HERE, 'rend', 'snow_kit', 'Kit_*.png'))):
    shutil.copy2(f, os.path.join(PK, 'renders', 'models'))
for f in ('contact_fl.jpg', 'details.jpg'):
    p = os.path.join(HERE, 'rend', 'snow_kit', f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(PK, 'renders'))
SRC = ['snowkit_spec.py', 'snowkit_kit.py', 'snowkit_tex.py', 'snowkit_paint.py', 'snowkit_build.py', 'snowkit_sheet.py',
       'snowkit_detail.py', 'snowkit_render.py', 'make_sheets_snowkit.py', 'make_snowkit_doc.py', 'pack_snowkit.py', 'KitWire.cs',
       'gen_kit.py', 'gen_tex.py', 'gen_paint.py', 'gen_lights.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py',
       'van2_kit.py', 'van2_tex.py', 'van3_mech.py', 'van_lights.py', 'ies_lm63.py', 'post_bloom.py', 'make_sheets_main.py']
os.makedirs(os.path.join(PK, 'src', 'inventory'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
for f in ('inventory.json', 'inventory.md'):
    shutil.copy2(os.path.join(INV, f), os.path.join(PK, 'src', 'inventory'))
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
need = set()
for f in [f for f in SRC if f.endswith('.py')]:
    for node in ast.walk(ast.parse(open(os.path.join(HERE, f)).read())):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        need |= {n.split('.')[0] for n in names if n.split('.')[0] in local}
lost = sorted(n for n in need if n + '.py' not in SRC)
assert not lost, f'local modules imported but not packed: {lost}'
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники набора snow_kit (общие мелкие модели K1–K12). Пакет — папка выше (snow_kit.blend, атлас, контракт), архив — '
    '../../snow_kit_package.zip,\nсправочник — docs/gdd/SNOW_KIT_CONTRACT.md.\n\n'
    '- Модели целиком строятся скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).\n'
    '- snowkit_spec.py — имена моделей, зоны покраски, области панели, правило провода (K9); snowkit_kit.py — геометрия, детали,\n'
    '  точки, коллайдеры; snowkit_tex.py — панель надписей и экраны; snowkit_paint.py — покраска атласа.\n'
    '- Порядок: snowkit_build.py → out/snow_kit.blend, snow_kit.json, snow_kit_contract.json, snow_kit_lights.json, tex/snow_kit\n'
    '  (--draft — без запекания); snowkit_sheet.py и snowkit_detail.py → rend/snow_kit (рабочие виды); snowkit_render.py →\n'
    '  rend/snow_kit_cycles (в работе); make_sheets_snowkit.py → sheets/snow_kit_A…D.jpg; make_snowkit_doc.py →\n'
    '  docs/SNOW_KIT_CONTRACT.md; pack_snowkit.py → out/snow_kit_package.zip.\n'
    '- KitWire.cs — образец скрипта Unity для провода K9 (справка, в проект ставит агент Unity).\n'
    '- inventory/ — что набор заменит в готовых пакетах (forest_kpp, forest_main, forest_garage, forest_gencont, forest_yard,\n'
    '  forest_hut, forest_base): json и таблица; в справочнике — раздел «Что набор заменит».\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.\n'
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
zp = os.path.join(HERE, 'out', 'snow_kit_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, ds, files in os.walk(PK):
        ds.sort()
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('snow_kit', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
