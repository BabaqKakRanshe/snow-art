"""Package the road prefabs: the .blend with relative texture paths, the textures, the contract (JSON + Russian reference),
the sheets, the full source (self-contained) with the checks.
python3 -I pack_road.py [checks_dir] -> out/forest_road_package.zip (folder forest_road/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
CHECKS = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else None
PK = os.path.join(HERE, 'out', 'forest_road')
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'road')
for f in glob.glob(os.path.join(src_tex, '*.json')):
    shutil.copy2(f, os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'road.blend'))
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
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'road.blend'), relative_remap=False)
for f in ('road_contract.json', 'road.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'ROAD_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'road_*.jpg'))):
    shutil.copy2(f, PK)
SRC = ['road_spec.py', 'road_kit.py', 'road_tex.py', 'road_paint.py', 'road_build.py', 'road_render.py', 'bld_common.py',
       'make_road_doc.py', 'make_sheets_road.py', 'make_sheets_main.py', 'pack_road.py', 'road_u3_data.json',
       'road_ground.json', 'road_cmp_views.json',
       # the shed's / hut's / yard's / checkpoint's modules the road builds on (painters, the chain-link, the font)
       'hut_paint.py', 'hut_kit.py', 'hut_tex.py', 'gen_paint.py', 'yard_tex.py', 'kpp_tex.py', 'main_tex.py', 'main_spec.py',
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
    for pat in ('*.py', '*.sh', '*.log', 'road_checks.json'):
        for f in sorted(glob.glob(os.path.join(CHECKS, pat))):
            if os.path.basename(f) != 'run.log':
                shutil.copy2(f, os.path.join(PK, 'src', 'checks'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники дороги пролога (18 префабов: указатели, столбик, ворота SPERRGEBIET, мост, площадка, бурелом). Пакет — папка '
    'выше (road.blend, атласы, контракт), архив — ../../forest_road_package.zip,\nсправочник — docs/gdd/ROAD_CONTRACT.md.\n\n'
    '- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),\n'
    '  рабица — КПП / двора (yard_tex), шрифт табличек — проекта (pxfont).\n'
    '- Данные обновления 3: road_u3_data.json (места префабов и 48 столбиков, кадры, материалы, коробки FBX — из\n'
    '  Forest_Layout.json, Forest_Materials.json и FBX), road_ground.json (рельеф обновления 3 под каждым префабом в его кадре:\n'
    '  снят с Forest_Terrain.fbx скриптом road_ground.py из проверок), road_spec.py (размеры, тексты, цвета).\n'
    '- Порядок: road_build.py → out/road.blend, road.json, road_contract.json, tex/road\n'
    '  (road_build.py --draft — без запекания, цвета зон; --only Signs,Gate — запечь только эти атласы);\n'
    '  road_render.py <виды | all | map | cmp> [spp] → rend/road (map — кадры обновления 3 на его рельефе: нужен\n'
    '  terrain.blend из Forest_Terrain.fbx); make_road_doc.py → docs/ROAD_CONTRACT.md; make_sheets_road.py → sheets/road_A…E.jpg;\n'
    '  pack_road.py → out/forest_road_package.zip.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке.\n'
    '- checks/ — проверки (road_checks.py → road_checks.json): префабы и коробки против обновления 3, изнанки, всё ли стоит на\n'
    '  земле, проход капсулы игрока по мосту и на площадку, колеи моста для машины, свободна ли дорога между спилами ели,\n'
    '  столбики на рельефе; render_u3.py — модели обновления 3 с тех же камер; road_ground.py — снятие рельефа.\n'
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
zp = os.path.join(HERE, 'out', 'forest_road_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_road', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
