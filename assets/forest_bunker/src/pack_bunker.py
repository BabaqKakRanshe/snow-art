"""Package forest_bunker 1.0: the .blend with relative texture paths, the textures, the json contract, stats and lights, the
sheet, the renders, the source (self-contained); the Russian reference goes to docs/gdd (BUNKER_CONTRACT.md), not into the
package.
python3 -I pack_bunker.py -> out/forest_bunker/ + out/forest_bunker_package.zip"""
import os, sys, shutil, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PK = os.path.join(HERE, 'out', 'forest_bunker')
SRC = ['bunker_spec.py', 'bunker_kit.py', 'bunker_tex.py', 'bunker_paint.py', 'bunker_build.py', 'bunker_tarp_sim.py',
       'bunker_quick.py', 'bunker_render.py', 'bunker_sheet.py', 'pack_bunker.py']
RENDERS = ['hangar', 'hangar_open', 'hangar_in', 'vest', 'door_open', 'entr', 'entr_hatch', 'entr_open']
README = ('Исходники пакета forest_bunker 1.0: бункер под озером — ангар в берегу с воротами на лёд, брезент на '
          'законсервированный самолёт, тамбур с круглой дверью вниз, вход у кисти: бетонный спуск и люк подо льдом. Пакет — '
          'папка выше, справочник — docs/gdd/BUNKER_CONTRACT.md.\n\n'
          '- Модели целиком строятся скриптами. bunker_spec.py — размеры и стоянка самолёта; bunker_kit.py — ангар, тамбур с '
          'дверью, вход, брезент; bunker_tex.py — панель (таблички, пульт двери), мокрые следы (подошва X11 из '
          'T_BVDecal_Cut_px проекта), лёд; bunker_paint.py — покраска атласов; bunker_tarp_sim.py — брезент: своя ткань '
          '(Verlet) по 2,5D-оболочке самолёта UtilityPlane v13 с зимним комплектом, стоящего на Slot_Plane.\n'
          '- Порядок: python3.11 bunker_tarp_sim.py <UtilityPlane_v13.blend> out/bunker_work/tarp.npz; bunker_build.py → '
          'out/bunker.blend, bunker.json, bunker_contract.json, bunker_lights.json, tex/bunker (--draft — цвета зон); '
          'bunker_quick.py -- <blend> <папка> [виды] — рабочие виды; bunker_render.py <виды|all> [spp] → rend/bunker/*.png '
          '(самолёт — из UtilityPlane_v13.blend); bunker_sheet.py → лист; pack_bunker.py → out/forest_bunker/.\n')
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
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'bunker.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
shutil.copy2(os.path.join(HERE, 'tex', 'bunker', 'bunker_panel_regions.json'), os.path.join(PK, 'tex'))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'bunker.blend'), relative_remap=False)
for f in ('bunker_contract.json', 'bunker.json', 'bunker_lights.json'):
    shutil.copy2(os.path.join(HERE, 'out', f), PK)
shutil.copy2(os.path.join(HERE, 'rend', 'bunker', 'forest_bunker_A.jpg'), PK)
os.makedirs(os.path.join(PK, 'renders'))
for r in RENDERS:
    shutil.copy2(os.path.join(HERE, 'rend', 'bunker', r + '.png'), os.path.join(PK, 'renders'))
lib_ = copy_src(PK, SRC)
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека: ' + ', '.join(lib_) + '.\n'
    "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz'; самолёт и\n"
    "  T_BVDecal_Cut_px — из /mnt/user-data/uploads/snow/...) — заменить на свои; скрипты пишут в out/, tex/, rend/.\n")
zip_dir(PK, os.path.join(HERE, 'out', 'forest_bunker_package.zip'))
n = sum(len(fs) for _, _, fs in os.walk(PK))
print('packed forest_bunker', n, 'files; lib', lib_, '; zip', os.path.getsize(os.path.join(HERE, 'out', 'forest_bunker_package.zip')))
