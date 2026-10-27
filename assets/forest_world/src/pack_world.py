"""Package forest_world 1.0 and the old spare van: the .blend with relative texture paths, the textures, the json contract,
stats and lights, the sheet, the renders, the source (self-contained); the Russian reference goes to docs/gdd
(WORLD_CONTRACT.md), not into the packages.
python3 -I pack_world.py -> out/forest_world/ + out/forest_world_package.zip, out/van3_old/ + out/van3_old_package.zip"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_world')
VO = os.path.join(HERE, 'out', 'van3_old')
VO_WORK = os.path.join(HERE, 'out', 'vanold_work', 'vehicles', 'van3_old')
SRC = ['world_kit.py', 'world_ice.py', 'world_tex.py', 'world_paint.py', 'world_build.py', 'world_cave_sdf.py', 'world_quick.py',
       'world_render.py', 'world_sheet.py', 'pack_world.py']
VSRC = ['vanold.py', 'vanold_render.py']
RENDERS = ['barrel', 'barrel_night', 'shift', 'shift_rear', 'wreck', 'wreck_rear', 'cave', 'cave_in', 'cave_key', 'ice_relay',
           'ice_dish', 'ice_roof']
README = ('Исходники пакета forest_world 1.0: бочка с огнём, наледь на антеннах (мачта ретранслятора, пять антенн, мачта и '
          'тарелка на крыше корпуса), пещера Лесника, две брошенные машины (машина прежней смены и старый седан). Пакет — папка '
          'выше, справочник — docs/gdd/WORLD_CONTRACT.md; старый запасной фургон — отдельный пакет source/vehicles/van3_old.\n\n'
          '- Модели целиком строятся скриптами. world_kit.py — бочка, обе машины (один генератор кузова, два набора размеров), '
          'пещера (оболочка из world_cave_sdf.py: поле расстояний → marching cubes, системный python3 со scikit-image) и её '
          'обстановка; world_ice.py — наледь в системах координат своих префабов (размеры мачты и антенн берутся из far_spec.py '
          'пакета forest_far); world_tex.py — панель (надпись станции на дверях, газета 1991 года), огонь (8 кадров), лёд, '
          'треснувшее стекло; world_paint.py — покраска атласов.\n'
          '- Порядок: python3 world_cave_sdf.py out/world_work/cave.npz; world_build.py → out/world.blend, world.json, '
          'world_contract.json, world_lights.json, tex/world (--draft — цвета зон); world_quick.py -- <blend> <папка> [виды] — '
          'рабочие виды; world_render.py <виды|all> [spp] → rend/world/*.png (мачта и антенна — из ../forest_far/far.blend, '
          'корпус — из ../forest_main/main.blend, ключ и вещи — из ../forest_gear/gear.blend); world_sheet.py → лист; '
          'pack_world.py → out/forest_world/ и out/van3_old/.\n')
VREADME = ('Старый запасной фургон: van3 с новой текстурой кузова (старое хаки, ржавчина) и без лебёдки. Справочник — раздел '
           '«Старый запасной фургон» в docs/gdd/WORLD_CONTRACT.md.\n\n'
           '- vanold.py <папка van3> <папка вывода>: запекает положение, нормаль и AO кузова van3 в его же развёртке (PSX) и '
           'красит T_VanOld_Body_BaseColor (256, 64 цвета); vanold.blend — копия van3.blend: материал M_VanOld_Body вместо '
           'M_Van_Body, Winch_Drum, Winch_Clutch, Winch_Hook удалены, остальные текстуры — van3 по пути ../van3/tex.\n'
           '- vanold_render.py <vanold.blend> <png> [spp] — рендер.\n')
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


# ---------------------------------------------------------------- forest_world
for d in (PK, VO):
    if os.path.isdir(d):
        shutil.rmtree(d)
os.makedirs(os.path.join(PK, 'tex'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'world.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'world', 'world_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'world.blend'), relative_remap=False)
for f in ('world_contract.json', 'world.json', 'world_lights.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'world', 'forest_world_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'world', r + '.png'), os.path.join(PK, 'renders'))
lib_ = copy_src(PK, SRC)
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz', far_spec — из\n"
    "  '/home/claude/far') — заменить на путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n")
zip_dir(PK, os.path.join(HERE, 'out', 'forest_world_package.zip'))
n = sum(len(fs) for _, _, fs in os.walk(PK))
print('packed forest_world', n, 'files; lib', lib_, '; zip', os.path.getsize(os.path.join(HERE, 'out', 'forest_world_package.zip')))

# ---------------------------------------------------------------- van3_old (next to van3 in source/vehicles)
os.makedirs(os.path.join(VO, 'tex'))
shutil.copy2(os.path.join(VO_WORK, 'tex', 'T_VanOld_Body_BaseColor.png'), os.path.join(VO, 'tex'))
shutil.copy2(os.path.join(VO_WORK, 'vanold.blend'), VO)
shutil.copy2(os.path.join(VO_WORK, 'vanold.json'), VO)
os.makedirs(os.path.join(VO, 'renders'))
shutil.copy2(os.path.join(HERE, 'rend', 'world', 'van_old.png'), os.path.join(VO, 'renders'))
vlib = copy_src(VO, VSRC)
open(os.path.join(VO, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    VREADME + '- Библиотека: ' + ', '.join(vlib) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz').\n")
zip_dir(VO, os.path.join(HERE, 'out', 'van3_old_package.zip'))
n = sum(len(fs) for _, _, fs in os.walk(VO))
print('packed van3_old', n, 'files; lib', vlib, '; zip', os.path.getsize(os.path.join(HERE, 'out', 'van3_old_package.zip')))
