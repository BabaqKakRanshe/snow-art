"""Package the base prefabs: the .blend with relative texture paths, the textures, the contract (JSON + Russian reference),
the sheets, the full source (self-contained) with the checks.
python3 -I pack_base.py [checks_dir] -> out/forest_base_package.zip (folder forest_base/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_base')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'base')
for f in glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'base.blend'))
missing = []
for im in bpy.data.images:                                # only the textures the models use
    if im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(src_tex, name)):
        shutil.copy2(os.path.join(src_tex, name), os.path.join(PK, 'tex'))
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'base.blend'), relative_remap=False)
for f in ('base_contract.json', 'base.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'BASE_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'base_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['base_spec.py', 'base_kit.py', 'base_tex.py', 'base_paint.py', 'base_build.py', 'base_render.py', 'bld_common.py',
       'make_base_doc.py', 'make_sheets_base.py', 'make_sheets_main.py', 'make_sheets_road.py', 'pack_base.py',
       'base_u3_data.json', 'base_ground.json', 'base_cmp_views.json', 'unwrap_fast.py',
       # the modules the base builds on (the shed's bake, the hut's / road's painters and kits, the font)
       'hut_paint.py', 'hut_kit.py', 'hut_tex.py', 'gen_paint.py', 'yard_tex.py', 'kpp_tex.py', 'main_tex.py', 'main_spec.py',
       'road_kit.py', 'road_tex.py', 'road_spec.py', 'road_paint.py', 'road_build.py',
       'uvpack.py', 'gen_kit.py', 'gen_tex.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py', 'van2_kit.py',
       'van2_tex.py', 'van3_mech.py', 'post_bloom.py']
os.makedirs(os.path.join(PK, 'src'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src', f))
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
have = {os.path.splitext(f)[0] for f in SRC if f.endswith('.py')}
todo, extra = list(have), []
while todo:                                                # the whole import closure of the local modules
    f = todo.pop()
    for node in ast.walk(ast.parse(open(os.path.join(HERE, f + '.py')).read())):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        for n in {n.split('.')[0] for n in names if n.split('.')[0] in local}:
            if n not in have:
                have.add(n)
                todo.append(n)
                extra.append(n)
                shutil.copy2(os.path.join(HERE, n + '.py'), os.path.join(PK, 'src', n + '.py'))
print('also packed (imported by the shared modules):', sorted(extra))
if CHECKS:
    os.makedirs(os.path.join(PK, 'src', 'checks'))
    for f in ('chk_common.py', 'base_checks.py', 'render_u3.py', 'base_checks.json', 'base_checks.log', 'u3_base.log'):
        if os.path.exists(os.path.join(CHECKS, f)):        # the checks of this package (no probes, no draft runs)
            shutil.copy2(os.path.join(CHECKS, f), os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники базы (люк шахты, ящики, поленница, фонари, опоры ЛЭП и провода, рабица и старый забор, вертолётная '
    'площадка, радиомачта). Пакет — папка выше (base.blend, атласы, контракт), архив — ../../forest_base_package.zip,\n'
    'справочник — docs/gdd/BASE_CONTRACT.md.\n\n'
    '- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),\n'
    '  шрифт табличек — проекта (pxfont).\n'
    '- Данные обновления 3: base_u3_data.json (места префабов и рассыпки заборов, огни, ореолы, материалы, коробки FBX, GUID —\n'
    '  из Forest_Layout.json, Forest_Materials.json и FBX), base_ground.json (рельеф обновления 3 под каждым префабом в его\n'
    '  кадре и под каждой секцией забора), base_spec.py (размеры, места деталей, тексты).\n'
    '- Порядок: base_build.py → out/base.blend, base.json, base_contract.json, tex/base\n'
    '  (base_build.py --draft — без запекания, цвета зон; --only Props,Mast — запечь только эти атласы);\n'
    '  base_render.py <виды | all | map | cmp> [spp] → rend/base (map — места обновления 3 на его рельефе: нужен\n'
    '  terrain.blend из Forest_Terrain.fbx); make_base_doc.py → docs/BASE_CONTRACT.md; make_sheets_base.py → sheets/base_A…E.jpg;\n'
    '  pack_base.py → out/forest_base_package.zip.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке.\n'
    '- checks/ — проверки (base_checks.py → base_checks.json): префабы, пивот и ось крышки, коробки против обновления 3,\n'
    '  изнанки, ничего не висит над рельефом, ход крышки люка, огни в колпаках, провода (концы, просвет), раскладка заборов\n'
    '  обновления 3 на склонах, наложенные грани, UV; render_u3.py — модели обновления 3 с тех же камер.\n'
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
zp = os.path.join(HERE, 'out', 'forest_base_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_base', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
