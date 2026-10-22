"""Package the garage (prefab Garage): the .blend with relative texture paths, the textures, the interaction contract
(JSON + Russian reference), sheets, the full source (self-contained) with the checks.
python3 -I pack_gar.py [checks_dir] -> out/forest_garage_package.zip (folder forest_garage/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_garage')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'garage')
for f in glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'garage.blend'))
missing = []
for im in bpy.data.images:                                # only the textures the model uses
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(src_tex, name)):
        shutil.copy2(os.path.join(src_tex, name), os.path.join(PK, 'tex'))
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'garage.blend'), relative_remap=False)
for f in ('garage_contract.json', 'garage.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'GARAGE_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'gar_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['gar_spec.py', 'gar_kit.py', 'gar_tex.py', 'gar_paint.py', 'gar_build.py', 'gar_render.py', 'bld_common.py',
       'make_gar_doc.py', 'make_sheets_gar.py', 'make_sheets_main.py', 'pack_gar.py', 'gar_u3_data.json',
       'gar_u3_materials.json',
       # the main building's modules the garage builds on (its furniture, openings' hardware, painters, panel drawing)
       'main_spec.py', 'main_shell.py', 'main_open.py', 'main_furn.py', 'main_rooms.py', 'main_fx.py', 'main_fx_u3.py',
       'main_ix_u3.py', 'main_tex.py', 'main_paint.py', 'main_rooms2.py',
       'uvpack.py', 'gen_kit.py', 'gen_tex.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py', 'van2_kit.py',
       'van2_tex.py', 'van3_mech.py', 'cont_kit.py', 'cont_tex.py', 'kpp_tex.py', 'post_bloom.py']
os.makedirs(os.path.join(PK, 'src'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src', f))
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
need = set()
for f in [f for f in SRC if f.endswith('.py')]:
    for node in ast.walk(ast.parse(open(os.path.join(HERE, f)).read())):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        need |= {n.split('.')[0] for n in names if n.split('.')[0] in local}
lost = sorted(n for n in need if n + '.py' not in SRC)
assert not lost, f'local modules imported but not packed: {lost}'
if CHECKS:
    os.makedirs(os.path.join(PK, 'src', 'checks'))
    for pat in ('*.py', '*.sh', '*.log', 'checks_summary.json', 'walk_*.png', 'walk.json'):
        for f in sorted(glob.glob(os.path.join(CHECKS, pat))):
            if os.path.basename(f) != 'run.log':
                shutil.copy2(f, os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники гаража (префаб Garage). Пакет — папка выше (garage.blend, атласы, контракт), архив — '
    '../../forest_garage_package.zip,\nсправочник — docs/gdd/GARAGE_CONTRACT.md.\n\n'
    '- Модель целиком строится скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint);\n'
    '  мебель, фурнитура и часть красок — модули главного корпуса (main_furn, main_rooms, main_open, main_paint).\n'
    '- Данные обновления 3: gar_spec.py (размеры, проёмы, двери с точками, осями и ходами, окна, свет, содержимое — сняты с\n'
    '  Garage.fbx), gar_u3_data.json (из Forest_Layout.json: детали, источники, ореолы, питание), gar_u3_materials.json\n'
    '  (материалы, которые игра знает по имени).\n'
    '- Порядок: gar_build.py → out/garage.blend, garage.json, garage_contract.json, tex/garage\n'
    '  (gar_build.py --draft — без запекания, цвета зон → garage_draft.blend; --only Parts — запечь только этот атлас);\n'
    '  gar_render.py <виды через запятую | all> [spp] [--gate=85 --side=100 --tag=open] → rend/garage;\n'
    '  make_gar_doc.py → docs/GARAGE_CONTRACT.md; make_sheets_gar.py → sheets/gar_A…D.jpg; pack_gar.py → '
    'out/forest_garage_package.zip.\n'
    '- bld_common.py — общие шаги сборки (из сборки главного корпуса): объекты, сварка, разведение совпадающих граней,\n'
    '  атласы через один запекаемый прокси, материалы обновления 3, присоединение стекла, табличек и линз.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.\n'
    '- checks/ — проверки (run_checks.sh → логи и checks_summary.json; логи этой сборки лежат рядом): сверка с данными\n'
    '  обновления 3 (детали, оси, ходы, точки, замки, свет), изнанки, совпадающие грани, проходимость капсулой игрока и\n'
    '  досягаемость деталей (walk), ход ворот и двери с глубиной захода (sweep2).\n'
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
zp = os.path.join(HERE, 'out', 'forest_garage_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_garage', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
