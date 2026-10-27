"""Package forest_gear 1.0: the .blend with relative texture paths, the textures, the json contract and stats, the sheet, the
renders, the source (self-contained); the Russian reference goes to docs/gdd (GEAR_CONTRACT.md), not into the package.
python3 -I pack_gear.py -> out/forest_gear/ and out/forest_gear_package.zip (the folder inside)"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_gear')
SRC = ['gear_kit.py', 'gear_tex.py', 'gear_paint.py', 'gear_build.py', 'gear_quick.py', 'gear_render.py', 'gear_sheet.py',
       'pack_gear.py']
RENDERS = ['cells', 'walkie', 'lantern', 'lantern_battery', 'headlamp', 'cart', 'sled', 'doll', 'doll_turn', 'postcard', 'small',
           'iceaxe']
README = ('Исходники пакета forest_gear 1.0: батарейки (D, упаковка, 6 В), рация, фонарь 6 В с жёлтым стеклом, налобный фонарь, '
          'тележка, волокуша, кукла и открытка, лампочка и коробка, латунный жетон, ключ Stationsleiter, ледоруб. Пакет — папка '
          'выше, справочник — docs/gdd/GEAR_CONTRACT.md.\n\n'
          '- Модели целиком строятся скриптами. gear_kit.py — геометрия, детали и точки; gear_tex.py — панель надписей '
          '(обёртки батареек, лицо и верх рации, таблички фонарей, лицо куклы, коробка лампочки, жетон, бирка ключа) и свои '
          'текстуры (дисплей рации, открытка — картинка и оборот, стекло лампочки новое и перегоревшее); gear_paint.py — покраска '
          'атласов.\n'
          '- Текст открытки и номер жетона — константы в gear_tex.py (POSTCARD_MSG, POSTCARD_SIG, TAG_NUMBER).\n'
          '- Порядок: gear_build.py → out/gear.blend, gear.json, gear_contract.json, tex/gear (--draft — цвета зон); '
          'gear_quick.py -- <blend> <папка> [виды] — рабочие виды; gear_render.py <виды|all> [spp] → rend/gear/*.png; '
          'gear_sheet.py → лист; pack_gear.py → out/forest_gear/.\n')
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'gear.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'gear', 'gear_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'gear.blend'), relative_remap=False)
for f in ('gear_contract.json', 'gear.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'gear', 'forest_gear_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'gear', r + '.png'), os.path.join(PK, 'renders'))
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    '  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n')
z = os.path.join(HERE, 'out', 'forest_gear_package.zip')
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
print('packed forest_gear', n, 'files; lib', lib_, '; zip', os.path.getsize(z))
