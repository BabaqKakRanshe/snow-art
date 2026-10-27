"""Package the checkpoint v2: kpp.blend with relative texture paths and the snow kit linked from ../snow_kit/snow_kit.blend,
the atlases, the panel, Update 7's barbed wire texture and the IES, the interaction contract (JSON + the Russian reference, also
in docs/gdd), lamps json, sheets A-E, renders, walls/ (the Update 7 walls at the gate and the barrier), the full source
(self-contained).  python3 -I pack_kpp.py -> out/forest_kpp/ and out/forest_kpp_package.zip (folder forest_kpp/ inside)"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_kpp')
KIT_REL = '//../snow_kit/snow_kit.blend'
if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
src_tex = os.path.join(HERE, 'tex', 'kpp')
for f in ('T_Kpp_Kpp_BaseColor.png', 'T_Kpp_KppYard_BaseColor.png', 'T_Kpp_KppProps_BaseColor.png', 'T_Kpp_Panel_BaseColor.png',
          'T_Kpp_Panel_Emission.png', 'kpp_panel_regions.json'):
    shutil.copy2(os.path.join(src_tex, f), os.path.join(PK, 'tex'))
shutil.copy2(os.path.join(HERE, 'out', 'forest_fences', 'tex', 'replacements', 'T_Kpp_Barbed_A_px.png'), os.path.join(PK, 'tex'))
shutil.copytree(os.path.join(src_tex, 'IES'), os.path.join(PK, 'tex', 'IES'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'kpp.blend'))
missing = []
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    name = os.path.basename(bpy.path.abspath(im.filepath))
    if os.path.exists(os.path.join(PK, 'tex', name)):
        im.filepath = '//tex/' + name
    else:
        missing.append(im.filepath)
libs = [l.filepath for l in bpy.data.libraries]
assert libs == [KIT_REL], libs                        # the kit: linked, not copied (forest_kpp and snow_kit side by side)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'kpp.blend'), relative_remap=False)
for f in ('kpp_contract.json', 'kpp_lights.json', 'kpp.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'docs', 'KPP_CONTRACT.md'), PK)                 # the same file goes to docs/gdd
for f in sorted(glob.glob(os.path.join(HERE, 'sheets', 'kpp_[A-E].jpg'))):
    shutil.copy2(f, PK)
os.makedirs(os.path.join(PK, 'renders'))
for f in sorted(glob.glob(os.path.join(HERE, 'rend', 'kpp2_game', '*.png'))):
    shutil.copy2(f, os.path.join(PK, 'renders'))
shutil.copy2(os.path.join(HERE, 'rend', 'kpp2_final', 'plan.png'), os.path.join(PK, 'renders', 'plan.png'))
WV = os.path.join(HERE, 'walls_v2')
os.makedirs(os.path.join(PK, 'walls'))
for f in ('REPORT.md', 'u7_layout_v2.json', 'diff.json', 'levelling.json', 'tables_v2.json', 'walls_v2_data.json',
          'plan_gate.png', 'plan_barrier.png', 'closure_v2.png', 'u7_layout_v1_copy_closure.json', 'u7_layout_v2_closure.json',
          'u7_layout_v2_closure_nobones.json', 'u7_layout_v2_closure_nobones_nosockets.json',
          'walls_v2.py', 'verify_v2.py', 'closure_v2.py', 'plans_v2.py', 'tables_v2.py', 'probe_u7.py', 'make_walls_report.py'):
    shutil.copy2(os.path.join(WV, f), os.path.join(PK, 'walls'))
SRC = ['kpp_kit.py', 'kpp_tex.py', 'kpp_paint.py', 'kpp_build.py', 'kpp2_frame.py', 'kpp2_game.py', 'kpp2_quick.py',
       'kpp2_plan.py', 'make_kpp_doc.py', 'make_sheets_kpp.py', 'pack_kpp.py', 'snowkit_spec.py', 'snowkit_kit.py',
       'gen_kit.py', 'gen_tex.py', 'gen_paint.py', 'gen_lights.py', 'psxbake.py', 'psxlib.py', 'noise.py', 'pxfont.py',
       'van2_kit.py', 'van2_tex.py', 'van3_mech.py', 'van_lights.py', 'ies_lm63.py', 'post_bloom.py', 'make_sheets_main.py',
       'kpp2_ground.py', 'kit_preview.py']
os.makedirs(os.path.join(PK, 'src'))
for f in SRC:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
shutil.copy2(os.path.join(HERE, 'out', 'forest_kpp_v1', 'kpp_contract.json'), os.path.join(PK, 'src', 'kpp_contract_v1.json'))
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
    'Исходники КПП v2 (будка, электрический шлагбаум, ворота с приводом). Пакет — папка выше (kpp.blend, атласы, контракт), '
    'архив — ../../forest_kpp_package.zip,\nсправочник — docs/gdd/KPP_CONTRACT.md. Мелочи — экземпляры набора snow_kit '
    '(пакет ../../snow_kit, справочник docs/gdd/SNOW_KIT_CONTRACT.md).\n\n'
    '- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).\n'
    '- Сначала собирается набор (snow_kit, его src): kpp_kit.py берёт его контракт (out/snow_kit_contract.json), kpp_build.py\n'
    '  ссылается на его модели из ../snow_kit/snow_kit.blend; snowkit_spec.py и snowkit_kit.py здесь — для правила провода.\n'
    '- Порядок: kpp_build.py → out/kpp.blend, kpp.json, kpp_contract.json, kpp_lights.json, tex/kpp (--draft — без запекания);\n'
    '  kpp2_quick.py <blend> <папка> [виды] — рабочие виды; kpp2_plan.py <blend> <png> — план с подписями;\n'
    '  kpp2_game.py -- <папка> [spp] [виды|all] — КПП v2 в сцене игры обновления 7 (нужна сцена u7_game.blend из исходников\n'
    '  forest_fences: u7_preview.py), стены walls/ и выровненная земля → renders/;\n'
    '  make_kpp_doc.py → docs/KPP_CONTRACT.md (сравнивает с контрактом v1: kpp_contract_v1.json, в скрипте путь\n'
    '  out/forest_kpp_v1/kpp_contract.json); make_sheets_kpp.py → sheets/kpp_A…E.jpg; pack_kpp.py → out/forest_kpp_package.zip.\n'
    '- kpp2_frame.py — кадры: будка ↔ Unity ↔ игра (перенос ForestRelocation, двор ForestYardPlan).\n'
    '- kpp2_ground.py — высота земли игры под точкой в кадре будки или ворот (по walls_v2/terrain_levelled_1_1.npy, его пишет\n'
    '  walls/walls_v2.py): ею сняты высоты мачт камер и опор в kpp_kit.py (2.1).\n'
    '- kit_preview.py — только для превью: монитор камеры ворот показывает свою заглушку (CAM 2, T_Kit_Screen_On_Gate набора);\n'
    '  в Unity на экранах — картинки камер.\n'
    '- Стены у ворот и шлагбаума — отдельные скрипты в ../walls/ (walls_v2.py и др., отчёт REPORT.md).\n'
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
zp = os.path.join(HERE, 'out', 'forest_kpp_package.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, ds, files in os.walk(PK):
        ds.sort()
        for f in sorted(files):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join('forest_kpp', os.path.relpath(p, PK)))
print('missing', missing)
print(zp, os.path.getsize(zp))
