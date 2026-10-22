"""Package the fence and road-block kit of Forest Update 7 the way the asset batches of Updates 5-6 are packed (the .blend
with relative texture paths, the textures, the reports and the contract, the sheets, the renders, the full source with
the checks), and the Update 7 sources (the scripts that made the unitypackage, its reports).
python3 -I pack_u7.py  ->  out/forest_fences/, out/forest_fences_package.zip, out/forest_update7/src/"""
import os, sys, shutil, zipfile, glob, ast, json
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
FEN = '/home/claude/fence'
PK = os.path.join(HERE, 'out', 'forest_fences')
U7 = os.path.join(HERE, 'out', 'forest_update7')
SRC = ['fence_spec.py', 'fence_kit.py', 'fence_paint.py', 'fence_tex.py', 'fence_build.py', 'fence_layout.py', 'pack_u7.py']
TOOLS = ['kit_render.py', 'kit_preview.py', 'closeup.py', 'u7_preview.py', 'plan_u7.py', 'closure_u7.py', 'bone_probe.py',
         'make_sheets_fences.py', 'moire_test.py', 'moire_gif.py', 'drive_grid.py', 'reach.py', 'extract_map.py', 'map_big.py',
         'bones_footprint.py', 'game_ground.py', 'read_td.py']
CHECKS = [(U7 + '/fbx/u7_verify_fbx.json', 'u7_verify_fbx.json'), (U7 + '/u7_layout_closure.json', 'u7_layout_closure.json'),
          (U7 + '/u7_check_pkg.log', 'u7_check_pkg.log')]


def closure(files, dst):
    """copy the whole import closure of the local modules of HERE used by files"""
    local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
    have = {os.path.splitext(os.path.basename(f))[0] for f in files}
    todo, extra = [p for p in files], []
    while todo:
        f = todo.pop()
        for node in ast.walk(ast.parse(open(f).read())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in {n.split('.')[0] for n in names if n.split('.')[0] in local}:
                if n not in have:
                    have.add(n)
                    p = os.path.join(HERE, n + '.py')
                    todo.append(p)
                    extra.append(n)
                    shutil.copy2(p, os.path.join(dst, n + '.py'))
    for f in ('noise.py',):
        if not os.path.exists(os.path.join(dst, f)):
            shutil.copy2(os.path.join(HERE, f), os.path.join(dst, f))
    return sorted(extra)


def index(root):
    lines = []
    for r, ds, fs in os.walk(root):
        ds.sort()
        for f in sorted(fs):
            if f.endswith('.py'):
                p = os.path.join(r, f)
                d = ast.get_docstring(ast.parse(open(p).read())) or ''
                lines.append(f'{os.path.relpath(p, root):40s} {d.strip().splitlines()[0] if d.strip() else ""}')
    open(os.path.join(root, 'SCRIPTS_INDEX.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


# ---------------------------------------------------------------- the asset package
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex', 'replacements'))
src_tex = os.path.join(HERE, 'tex', 'fence')
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'fences.blend'))
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    fn = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(src_tex, fn)):
        shutil.copy2(os.path.join(src_tex, fn), os.path.join(PK, 'tex'))
        im.filepath = '//tex/' + fn
    else:
        missing.append(im.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'fences.blend'), relative_remap=False)
for f in glob.glob(os.path.join(src_tex, '*.png')) + glob.glob(os.path.join(src_tex, '*.json')):
    if not os.path.exists(os.path.join(PK, 'tex', os.path.basename(f))):
        shutil.copy2(f, os.path.join(PK, 'tex'))
for f in glob.glob(os.path.join(src_tex, 'replacements', '*.png')):
    shutil.copy2(f, os.path.join(PK, 'tex', 'replacements'))
for f in ('fences.json', 'fences_contract.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'FENCES_CONTRACT.md'), PK)
for f in sorted(glob.glob(os.path.join(FEN, 'sheets', 'fences_*.jpg'))):
    shutil.copy2(f, PK)
REND = {'kit': [p for p in glob.glob(os.path.join(FEN, 'rend', '*.png')) if not os.path.basename(p).startswith('m_')],
        'models': glob.glob(os.path.join(FEN, 'rend', 'm_*.png')),
        'game': glob.glob(os.path.join(FEN, 'game', '*.png')),
        'plan': [os.path.join(FEN, 'plan', f) for f in ('all.png', 'kpp.png', 'gate.png', 'closure.png')],
        'netting': [os.path.join(FEN, 'moire', 'walk_small.gif'), os.path.join(FEN, 'moire', 'walk_f0.png')]}
for sub, fs in REND.items():
    d = os.path.join(PK, 'renders', sub)
    os.makedirs(d, exist_ok=True)
    for f in sorted(fs):
        if os.path.exists(f):
            shutil.copy2(f, d)
os.makedirs(os.path.join(PK, 'src', 'tools'))
os.makedirs(os.path.join(PK, 'src', 'checks'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src', f))
for f in TOOLS:
    if os.path.exists(os.path.join(FEN, f)):
        shutil.copy2(os.path.join(FEN, f), os.path.join(PK, 'src', 'tools', f))
for p, n in CHECKS:
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(PK, 'src', 'checks', n))
extra = closure([os.path.join(HERE, f) for f in SRC] + [os.path.join(FEN, f) for f in TOOLS if os.path.exists(os.path.join(FEN, f))],
                os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Исходники комплекта заборов и заграждений Forest (обновление 7): забор ПО-2 (7 вариантов), новая рабица, спираль, '
    'блоки, надолбы, ёж, рогатка, завалы, щит HALT и знак; их расстановка на карте.\n'
    'Пакет — папка выше (fences.blend, атласы, отчёты, листы, рендеры), архив — ../../forest_fences_package.zip, '
    'справочник — docs/gdd/FENCES_CONTRACT.md; пакет для Unity — Forest_Update7.unitypackage (его исходники — '
    'source/locations/Forest/Forest_Update7_src).\n\n'
    '- Порядок: fence_build.py → out/fences.blend, fences.json, fences_contract.json, tex/fence (fence_build.py --draft — без '
    'запекания, --only Props — один атлас); fence_layout.py → out/forest_update7/u7_layout.json (места в кадре игры);\n'
    '  tools/closure_u7.py → проверка замкнутости; tools/kit_render.py, tools/u7_preview.py → рендеры; '
    'tools/plan_u7.py → планы; tools/make_sheets_fences.py → листы fences_A…F.jpg; pack_u7.py → этот архив.\n'
    '- fence_spec.py — размеры, fence_kit.py — геометрия, fence_paint.py — покраска атласов, fence_tex.py — панель надписей '
    'и вырезы (новая рабица, колючка, лента; replacements — 9 замен для моделей обновлений 4–5).\n'
    '- Данные карты для расстановки (tools/extract_map.py, map_big.py, drive_grid.py, bones_footprint.py, bone_probe.py): рельеф, '
    'дорога, деревья, кости великана — из локации обновления 3 и данных обновления 6.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz', "
    "'/home/claude/fence') — заменить на путь к этой папке.\n- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.\n")
index(os.path.join(PK, 'src'))
zp = os.path.join(HERE, 'out', 'forest_fences_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(PK):
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_fences', os.path.relpath(p, PK)))
print('fences: missing textures', missing, 'also packed', extra)
print(zp, os.path.getsize(zp))

# ---------------------------------------------------------------- the Update 7 sources
S = os.path.join(U7, 'src')
if os.path.isdir(S):
    shutil.rmtree(S)
os.makedirs(os.path.join(S, 'scripts'))
os.makedirs(os.path.join(S, 'reports'))
for f in ('u7_export.py', 'u7_verify_fbx.py', 'u7_build.py', 'u7_check_pkg.py', 'make_u7_docs.py', 'u7_readme_section.md',
          'fence_layout.py', 'u4_export.py', 'u4_build.py'):
    shutil.copy2(os.path.join(HERE, f), os.path.join(S, 'scripts', f))
for f in ('closure_u7.py', 'bone_probe.py', 'plan_u7.py'):
    shutil.copy2(os.path.join(FEN, f), os.path.join(S, 'scripts', f))
for p in (U7 + '/Forest_Update7_manifest.json', U7 + '/fbx/u7_export_report.json', U7 + '/fbx/u7_verify_fbx.json',
          U7 + '/u7_layout.json', U7 + '/u7_layout_closure.json', U7 + '/u7_check_pkg.log', U7 + '/README_u7_section.md'):
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(S, 'reports', os.path.basename(p)))
open(os.path.join(S, 'README_SRC.txt'), 'w', encoding='utf-8').write(
    'Как собран Forest_Update7.unitypackage (обновление 7 карты Forest: заборы и заграждения).\n\n'
    'Порядок (в /home/claude/uaz):\n'
    '1. fence_build.py → out/fences.blend (комплект); fence_layout.py → out/forest_update7/u7_layout.json (места в кадре игры:\n'
    '   периметр ПО-2, КПП, линии надолбов; убираемые деревья; просветы вдоль линий; проверка, что предметы не налезают);\n'
    '   closure_u7.py u7_layout.json → u7_layout_closure.json (куда доедет фургон и дойдёт человек).\n'
    '2. python3 -I u7_export.py -- out/forest_update7/fbx → 22 FBX + u7_export_report.json.\n'
    '3. python3 -I u7_verify_fbx.py -- out/forest_update7/fbx → u7_verify_fbx.json (обратный импорт: 0 замечаний).\n'
    '4. python3 u7_build.py out/forest_update7/fbx out/forest_update6 <u3raw> out/forest_update7 → stage/, пакет, опись.\n'
    '5. python3 -I u7_check_pkg.py <пакет 7> <пакет 6> <пакет 5> <пакет 4> <u3raw> → u7_check_pkg.log (независимая проверка).\n'
    '6. python3 make_u7_docs.py out/forest_update7 → docs/FOREST_U7_UNITY.md, START_FOREST_U7.txt, FENCES_CONTRACT.md.\n\n'
    'reports/: опись пакета (Forest_Update7_manifest.json), отчёты экспорта и обратного импорта, места (u7_layout.json),\n'
    'проверка замкнутости, журнал проверки пакета, раздел README. Исходники моделей — source/assets/forest_fences/src.\n')
print('sources:', S)
