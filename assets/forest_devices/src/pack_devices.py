"""Package forest_devices 1.0: the .blend with relative texture paths (the snow kit linked as ../snow_kit/snow_kit.blend), the
textures, the json contract and stats, the sheet, the renders, the source (self-contained); the Russian reference goes to
docs/gdd (DEVICES_CONTRACT.md), not into the package. python3 -I pack_devices.py -> out/forest_devices/ and
out/forest_devices_package.zip (the folder inside)"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_devices')
SRC = ['devices_kit.py', 'devices_tex.py', 'devices_paint.py', 'devices_build.py', 'devices_quick.py', 'devices_render.py',
       'devices_sheet.py', 'pack_devices.py']
RENDERS = ['fax', 'pc', 'laptop', 'tapes', 'deck', 'dropbox', 'screen', 'screen_in']
README = ('Исходники пакета forest_devices 1.0: факс и принятый факс, кассета и коробка кассет, ящик для кассет, компьютер объекта, '
          'ноутбук, магнитофон телеметрии в шкаф антенны, метеобудка. Пакет — папка выше, справочник — docs/gdd/DEVICES_CONTRACT.md.\n\n'
          '- Модели целиком строятся скриптами; монитор компьютера — Kit_Monitor_CRT из ../snow_kit/snow_kit.blend (связь).\n'
          '- devices_kit.py — геометрия, детали и точки; devices_tex.py — панель надписей (панели, клавиши, наклейки, шкалы '
          'термометров, лента термогигрографа), дисплей факса, экран ноутбука, бумага факса; devices_paint.py — покраска атласов.\n'
          '- Порядок: devices_build.py → out/devices.blend, devices.json, devices_contract.json, tex/devices (--draft — цвета зон); '
          'devices_quick.py -- <blend> <папка> [виды] — рабочие виды; devices_render.py <виды|all> [spp] → rend/devices/*.png; '
          'devices_sheet.py → лист; pack_devices.py → out/forest_devices/. Для сборки рядом нужна папка snow_kit '
          '(snow_kit.blend и tex).\n')
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'devices.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'devices', 'devices_panel_regions.json'), os.path.join(PK, 'tex'))
for lib in bpy.data.libraries:
    lib.filepath = '//../snow_kit/snow_kit.blend'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'devices.blend'), relative_remap=False)
for f in ('devices_contract.json', 'devices.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'devices', 'forest_devices_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'devices', r + '.png'), os.path.join(PK, 'renders'))
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n')
z = os.path.join(HERE, 'out', 'forest_devices_package.zip')
if os.path.exists(z):
    os.remove(z)
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dp, _, fs in os.walk(PK):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            zf.write(p, os.path.relpath(p, os.path.join(HERE, 'out')))
n = sum(len(fs) for _, _, fs in os.walk(PK))
print('packed forest_devices', n, 'files; lib', lib_, '; zip', os.path.getsize(z))
