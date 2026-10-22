"""Package the main building (BaseMain + BaseMain_Opening): the .blend with relative texture paths, the textures, the
interaction contract (JSON + Russian reference), sheets, the full source (self-contained) with the checks.
python3 -I pack_main.py [checks_dir] -> out/forest_main_package.zip (folder forest_main/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_main')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'main')
for f in glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'main.blend'))
missing = []
for im in bpy.data.images:                                # only the textures the model uses (no leftovers of old builds)
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(src_tex, name)):
        shutil.copy2(os.path.join(src_tex, name), os.path.join(PK, 'tex'))
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'main.blend'), relative_remap=False)
for f in ('main_contract.json', 'main.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'MAIN_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'main_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['main_spec.py', 'main_shell.py', 'main_open.py', 'main_furn.py', 'main_rooms.py', 'main_rooms2.py', 'main_fx.py',
       'main_fx_u3.py', 'main_ix_u3.py', 'main_signs.py', 'main_tex.py', 'main_paint.py', 'main_build.py', 'main_render.py',
       'main_draft.py', 'make_main_doc.py', 'make_sheets_main.py', 'pack_main.py', 'main_u3_data.json',
       'main_u3_materials.json', 'uvpack.py', 'gen_kit.py', 'gen_tex.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py',
       'van2_kit.py', 'van2_tex.py', 'van3_mech.py', 'cont_kit.py', 'cont_tex.py', 'kpp_tex.py', 'post_bloom.py']
os.makedirs(os.path.join(PK, 'src'))
for f in SRC:
    os.makedirs(os.path.dirname(os.path.join(PK, 'src', f)), exist_ok=True)
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
    for pat in ('*.py', '*.sh', '*.log', 'checks_summary.json', 'walk_*.png'):   # the scripts, their logs on this build
        for f in sorted(glob.glob(os.path.join(CHECKS, pat))):
            if os.path.basename(f) != 'run.log':
                shutil.copy2(f, os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники главного корпуса станции (BaseMain и BaseMain_Opening). Пакет — папка выше (main.blend, атласы, контракт), '
    'архив — ../../forest_main_package.zip,\nсправочник — docs/gdd/MAIN_CONTRACT.md.\n\n'
    '- Модель целиком строится скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint).\n'
    '- Данные обновления 3, с которых снята планировка: main_spec.py (размеры, комнаты, двери, окна), main_ix_u3.py\n'
    '  (139 деталей: точки, оси, ходы), main_fx_u3.py (64 светильника и их свет), main_u3_data.json (из Forest_Layout.json:\n'
    '  маски света, источники, ореолы, детали), main_u3_materials.json (материалы, которые игра знает по имени).\n'
    '- Порядок: main_build.py → out/main.blend, main.json, main_contract.json, tex/main\n'
    '  (main_build.py --only Rm_Windfang,MainParts — запечь только эти атласы, остальное — плоские цвета → main_test.blend);\n'
    '  main_draft.py — черновик геометрии с цветами зон; main_render.py <виды через запятую | all> [spp] → rend/main;\n'
    '  make_main_doc.py → docs/MAIN_CONTRACT.md; make_sheets_main.py → sheets/main_A…F.jpg; pack_main.py → out/forest_main_package.zip.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.\n'
    '- checks/ — проверки (run_checks.sh → логи и checks_summary.json; логи этой сборки лежат рядом): сверка с данными\n'
    '  обновления 3 (детали, оси, ходы, маски, свет), изнанки, совпадающие грани, предметы и надписи пролога на поверхностях,\n'
    '  проходимость капсулой игрока и досягаемость деталей (walk), ход подвижных деталей с глубиной захода (sweep2).\n'
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
zp = os.path.join(HERE, 'out', 'forest_main_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_main', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
