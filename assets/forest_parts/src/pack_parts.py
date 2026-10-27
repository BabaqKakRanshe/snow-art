"""Package forest_parts 1.0: the .blend with relative texture paths, the textures, the json contract and stats, the sheet,
the renders, the source (self-contained); the Russian reference goes to docs/gdd (PARTS_CONTRACT.md), not into the package.
python3 -I pack_parts.py -> out/forest_parts/ and out/forest_parts_package.zip (the folder inside)"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_parts')
SRC = ['parts_kit.py', 'parts_tex.py', 'parts_paint.py', 'parts_build.py', 'parts_quick.py', 'parts_render.py',
       'parts_sheet.py', 'pack_parts.py']
RENDERS = ['pump', 'pump_installed', 'lamp', 'crt', 'relay', 'gen', 'sensor', 'sensor_box']
README = ('Исходники пакета forest_parts 1.0: насос-дозатор для насосной (со шлангом для установленного положения), натриевая '
          'лампа 400 Вт и её коробка, кинескоп радара, блок ретранслятора RT-7, резервный генератор, датчик у озера. Пакет — '
          'папка выше, справочник — docs/gdd/PARTS_CONTRACT.md.\n\n'
          '- Модели целиком строятся скриптами. parts_kit.py — геометрия, детали, точки и место насоса в насосной forest_far; '
          'parts_tex.py — панель надписей (лицевая и задняя панели блока, щиток генератора, схема насоса, шкалы, наклейки, '
          'коробка лампы, табличка и ярлык датчика, плата регистратора) и свои текстуры (накладная, экран кинескопа); '
          'parts_paint.py — покраска атласов.\n'
          '- Дата накладной — константа WAYBILL_DATE в parts_tex.py.\n'
          '- Порядок: parts_build.py → out/parts.blend, parts.json, parts_contract.json, tex/parts (--draft — цвета зон); '
          'parts_quick.py -- <blend> <папка> [виды] — рабочие виды; parts_render.py <виды|all> [spp] → rend/parts/*.png (насосная '
          'берётся из ../forest_far/far.blend, батарейка 6 В — из ../forest_gear/gear.blend); parts_sheet.py → лист; '
          'pack_parts.py → out/forest_parts/.\n')
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}


def closure(files):
    need, todo = set(), list(files)
    while todo:
        f = todo.pop()
        for node in ast.walk(ast.parse(open(os.path.join(HERE, f)).read())):
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'parts.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'parts', 'parts_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'parts.blend'), relative_remap=False)
for f in ('parts_contract.json', 'parts.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'parts', 'forest_parts_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'parts', r + '.png'), os.path.join(PK, 'renders'))
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n')
z = os.path.join(HERE, 'out', 'forest_parts_package.zip')
if os.path.exists(z):
    os.remove(z)
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dp, _, fs in os.walk(PK):
        for f in sorted(fs):
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(dp, f)
            zf.write(p, os.path.relpath(p, os.path.join(HERE, 'out')))
n = sum(len(fs) for _, _, fs in os.walk(PK))
print('packed forest_parts', n, 'files; lib', lib_, '; zip', os.path.getsize(z))
