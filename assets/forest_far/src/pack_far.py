"""Package the far prefabs: the .blend with relative texture paths (1.1: the forest_devices instances linked from
../forest_devices/devices.blend), the textures, the contract (JSON; the Russian reference stays in docs/gdd), the sheets, the
full source (self-contained) with the checks.
python3 -I pack_far.py [checks_dir] -> out/forest_far_package.zip (folder forest_far/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_far')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'far')
for f in glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'far.blend'))
missing = []
for im in bpy.data.images:                                # only the textures the models use (not the linked devices')
    if im.source != 'FILE' or not im.filepath or im.library is not None:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    for d_ in (src_tex, os.path.join(HERE, 'tex', 'base')):          # the relay's chain-link and barbed wire: the base's
        if os.path.exists(os.path.join(d_, name)):
            shutil.copy2(os.path.join(d_, name), os.path.join(PK, 'tex'))
            im.filepath = '//tex/' + name
            break
    else:
        missing.append(im.filepath)
for lib in bpy.data.libraries:                            # 1.1: forest_devices next to forest_far
    lib.filepath = '//../forest_devices/devices.blend'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'far.blend'), relative_remap=False)
for f in ('far_contract.json', 'far.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'far_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['far_spec.py', 'far_kit.py', 'far_tex.py', 'far_paint.py', 'far_build.py', 'far_render.py', 'bld_common.py',
       'make_far_doc.py', 'make_sheets_far.py', 'make_sheets_main.py', 'make_sheets_road.py', 'pack_far.py',
       'far_u3_data.json', 'far_ground.json', 'far_cmp_views.json', 'far_lookout_stairs.json', 'unwrap_fast.py',
       # the base's spec, kit and textures (frames, the chain-link and barbed wire), the shed's bake, the painters, the font
       'base_spec.py', 'base_kit.py', 'base_tex.py', 'base_paint.py', 'base_u3_data.json', 'base_ground.json',
       'hut_paint.py', 'hut_kit.py', 'hut_tex.py', 'gen_paint.py', 'yard_tex.py', 'kpp_tex.py', 'main_tex.py', 'main_spec.py',
       'road_kit.py', 'road_tex.py', 'road_spec.py', 'road_paint.py', 'road_build.py',
       'uvpack.py', 'gen_kit.py', 'gen_tex.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py', 'van2_kit.py',
       'van2_tex.py', 'van3_mech.py', 'post_bloom.py',
       # 1.1: the weather station re-baked alone and put into 1.0 (compose_far11), sheet F's one tile, the road's data
       'compose_far11.py', 'patch_sheet_f11.py', 'road_u3_data.json', 'road_ground.json']
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
    for f in ('chk_common.py', 'far_checks.py', 'render_u3.py', 'far_checks.json', 'far_checks.log', 'u3_far.log'):
        if os.path.exists(os.path.join(CHECKS, f)):        # the checks of this package (no probes, no draft runs)
            shutil.copy2(os.path.join(CHECKS, f), os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники дальних точек (5 антенн, радом, ретранслятор, метеостанция, пожарная вышка, насосная, часовня, избушка, '
    'стоянка). Пакет — папка выше (far.blend, атласы, контракт), архив — ../../forest_far_package.zip,\n'
    'справочник — docs/gdd/FAR_CONTRACT.md.\n\n'
    '- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),\n'
    '  рабица и колючка — базы (base_tex), шрифт табличек — проекта (pxfont).\n'
    '- Данные обновления 3: far_u3_data.json (места, огни, ореолы, двери, материалы, коробки FBX, GUID), far_ground.json\n'
    '  (рельеф обновления 3 под каждым префабом в его кадре), far_lookout_stairs.json (ступени и площадки вышки из FBX),\n'
    '  far_spec.py (размеры, места деталей).\n'
    '- Порядок: far_build.py → out/far.blend, far.json, far_contract.json, tex/far\n'
    '  (far_build.py --draft — без запекания, цвета зон; --only Dish16,Chapel — запечь только эти атласы);\n'
    '  far_render.py <виды | all | map | cmp> [spp] → rend/far (map — места обновления 3 на его рельефе: нужен terrain.blend\n'
    '  из Forest_Terrain.fbx); make_far_doc.py → docs/FAR_CONTRACT.md; make_sheets_far.py → sheets/far_A…G.jpg;\n'
    '  pack_far.py → out/forest_far_package.zip.\n'
    '- Версия 1.1 (метеостанция без старой будки, модели forest_devices на точках крепления) собрана без пересборки\n'
    '  остального: far_build.py --only Meteo → out/far_test.blend; compose_far11.py — 1.0 (out/far_v10.blend и её json) +\n'
    '  новая метеостанция + экземпляры forest_devices → out/far.blend, far.json, far_contract.json; far_render.py\n'
    '  meteo,meteo_screen,meteo_gate,dish1_cab,cmp_meteo и map_meteo; make_sheets_far.py --only A,C,G; patch_sheet_f11.py —\n'
    '  одна плитка листа F. far.blend ссылается на ../forest_devices/devices.blend (папки рядом), для сборки рядом нужны\n'
    '  forest_devices и snow_kit.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке.\n'
    '- checks/ — проверки (far_checks.py → far_checks.json): префабы, пивоты и оси дверей, коробки против обновления 3,\n'
    '  копии антенн, изнанки, ничего не висит, ход дверей и проёмы, голова игрока на лестнице вышки, огни в колпаках,\n'
    '  наложенные грани, UV; render_u3.py — модели обновления 3 с тех же камер.\n'
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
zp = os.path.join(HERE, 'out', 'forest_far_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_far', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
