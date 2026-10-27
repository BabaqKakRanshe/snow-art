"""Package sky_systems 1.0: the .blend with relative texture paths, the textures, the json contract, stats and lights, the
sheet, the renders, the source (self-contained); the Russian reference goes to docs/gdd (SKY_CONTRACT.md), not into the
package.
python3 -I pack_sky.py -> out/sky_systems/ + out/sky_systems_package.zip"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'sky_systems')
SRC = ['sky_kit.py', 'sky_tex.py', 'sky_paint.py', 'sky_build.py', 'sky_quick.py', 'sky_render.py', 'sky_sheet.py', 'pack_sky.py']
RENDERS = ['chiller', 'chiller_open', 'sprayer', 'ballast', 'altimeter', 'walk', 'walk_close']
README = ('Исходники пакета sky_systems 1.0: системы высоты Небесного острова — холодильная установка, распылитель костяной '
          'пыли, сброс балласта на краю, табло высоты у вышки — и модули мостков под островом. Пакет — папка выше, '
          'справочник — docs/gdd/SKY_CONTRACT.md.\n\n'
          '- Модели целиком строятся скриптами. sky_kit.py — геометрия, детали, точки, коллайдеры; sky_tex.py — панель '
          '(табло высоты, пульты, таблички) и решётка настила; sky_paint.py — покраска атласов SkyMachines и SkyWalk.\n'
          '- Порядок: sky_build.py → out/sky.blend, sky.json, sky_contract.json, sky_lights.json, tex/sky (--draft — цвета '
          'зон; --reuse A,B — те же развёртки и прежние атласы без запекания); sky_quick.py -- <blend> <папка> [виды] — '
          'рабочие виды; sky_render.py <виды|all> [spp] → rend/sky/*.png; sky_sheet.py → лист; pack_sky.py → out/sky_systems/.\n')
local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}


def closure(files):
    need, todo = set(), list(files)
    while todo:
        f = todo.pop()
        p = os.path.join(HERE, f) if os.path.exists(os.path.join(HERE, f)) else os.path.join('/home/claude/far', f)
        for node in ast.walk(ast.parse(open(p).read())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in {n.split('.')[0] for n in names}:
                if n in local or os.path.exists(os.path.join('/home/claude/far', n + '.py')):
                    if n + '.py' not in files and n not in need:
                        need.add(n)
                        todo.append(n + '.py')
    return sorted(n + '.py' for n in need)


def copy_src(dst, files):
    lib_ = closure(files)
    os.makedirs(os.path.join(dst, 'src'))
    for f in files + lib_:
        p = os.path.join(HERE, f) if os.path.exists(os.path.join(HERE, f)) else os.path.join('/home/claude/far', f)
        shutil.copy2(p, os.path.join(dst, 'src', f))
    return lib_


def zip_dir(d, z):
    if os.path.exists(z):
        os.remove(z)
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(d):
            for f in sorted(fs):
                if f.endswith(('.blend1', '.pyc')):
                    continue
                p = os.path.join(dp, f)
                zf.write(p, os.path.relpath(p, os.path.dirname(d)))


if os.path.isdir(PK):
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'sky.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'sky', 'sky_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'sky.blend'), relative_remap=False)
for f in ('sky_contract.json', 'sky.json', 'sky_lights.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'sky', 'sky_systems_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'sky', r + '.png'), os.path.join(PK, 'renders'))
lib_ = copy_src(PK, SRC)
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
    "  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n")
zip_dir(PK, os.path.join(HERE, 'out', 'sky_systems_package.zip'))
n = sum(len(fs) for _, _, fs in os.walk(PK))
print('packed sky_systems', n, 'files; lib', lib_, '; zip', os.path.getsize(os.path.join(HERE, 'out', 'sky_systems_package.zip')))
