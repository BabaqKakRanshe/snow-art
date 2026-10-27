"""Package forest_rocks 1.0 and forest_trash 1.0: the .blend with relative texture paths, the atlases, the json contract and
stats, the sheet, the renders, the source (self-contained); the Russian references go to docs/gdd (ROCKS_CONTRACT.md,
TRASH_CONTRACT.md), not into the packages. python3 -I pack_rocks_trash.py -> out/forest_rocks/, out/forest_trash/ and their
*_package.zip (the folder inside)"""
import os, sys, shutil, glob, ast, zipfile
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
PKGS = {
    'forest_rocks': dict(blend='rocks', tex='rocks', json=['rocks_contract.json', 'rocks.json'], sheet='rend/rocks/forest_rocks_A.jpg',
                         renders=['stones', 'boulders', 'cliff_1', 'cliff_2', 'cliff_3', 'scene'], rend='rend/rocks',
                         src=['rocks_kit.py', 'rocks_paint.py', 'rocks_build.py', 'rocks_quick.py', 'rocks_render.py'],
                         doc='docs/gdd/ROCKS_CONTRACT.md',
                         readme='Исходники пакета forest_rocks 1.0: 6 камней, 3 валуна и 3 скалы Forest (гранит, как останцы Гарца). '
                                'Пакет — папка выше, справочник — docs/gdd/ROCKS_CONTRACT.md.\n\n'
                                '- Модели целиком строятся скриптами, входных файлов нет.\n'
                                '- rocks_kit.py — геометрия: эллипсоид или «подушка» с шумом и плоскими сколами; скалы — блоки, сращённые '
                                'вокселями (Remesh) и прореженные (Decimate); rocks_paint.py — покраска гранита (лишайник, мох, хвоя, '
                                'потёки, земля у подножия).\n'
                                '- Порядок: rocks_build.py → out/rocks.blend, rocks.json, rocks_contract.json, tex/rocks (--draft — без '
                                'запекания); rocks_quick.py <blend> <папка> [виды] — рабочие виды; rocks_render.py <виды|all> [spp] → '
                                'rend/rocks/*.png; rocks_trash_sheets.py rocks → лист; pack_rocks_trash.py → out/forest_rocks/.\n'),
    'forest_trash': dict(blend='trash', tex='trash', json=['trash_contract.json', 'trash.json'], sheet='rend/trash/forest_trash_A.jpg',
                         renders=['paper', 'plastic', 'metal', 'wood', 'glass', 'mixed'], rend='rend/trash',
                         src=['trash_kit.py', 'trash_paint.py', 'trash_build.py', 'trash_quick.py', 'trash_render.py'],
                         doc='docs/gdd/TRASH_CONTRACT.md',
                         readme='Исходники пакета forest_trash 1.0: мусор как в Voices of the Void — 6 видов, у каждого куча на земле '
                                '(TrashPile_*) и спрессованный ком в руках (TrashClump_*). Пакет — папка выше, справочник — '
                                'docs/gdd/TRASH_CONTRACT.md.\n\n'
                                '- Модели целиком строятся скриптами, входных файлов нет.\n'
                                '- trash_kit.py — вещи (газеты, картон, стаканчики, бутылки, пакеты, банки, лист, доски, ветки, стекло), '
                                'кучи и комья; trash_paint.py — покраска.\n'
                                '- Порядок: trash_build.py → out/trash.blend, trash.json, trash_contract.json, tex/trash (--draft — цвета '
                                'зон); trash_quick.py <blend> <папка> [виды] — рабочие виды; trash_render.py <виды|all> [spp] → '
                                'rend/trash/*.png; rocks_trash_sheets.py trash → лист; pack_rocks_trash.py → out/forest_trash/.\n'),
}
COMMON = ['rocks_trash_sheets.py', 'pack_rocks_trash.py']
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


for pk, d in PKGS.items():
    PK = os.path.join(HERE, 'out', pk)
    if os.path.isdir(PK):
        shutil.rmtree(PK)
    os.makedirs(os.path.join(PK, 'tex'))
    src_tex = os.path.join(HERE, 'tex', d['tex'])
    for f in sorted(os.listdir(src_tex)):
        if f.endswith('_BaseColor.png'):
            shutil.copy2(os.path.join(src_tex, f), os.path.join(PK, 'tex'))
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', d['blend'] + '.blend'))
    missing = []
    for im in bpy.data.images:
        if im.library is not None or im.source != 'FILE' or not im.filepath:
            continue
        name = os.path.basename(bpy.path.abspath(im.filepath))
        if os.path.exists(os.path.join(PK, 'tex', name)):
            im.filepath = '//tex/' + name
        else:
            missing.append(im.filepath)
    assert not missing, missing
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, d['blend'] + '.blend'), relative_remap=False)
    for f in d['json']:
        shutil.copy2(os.path.join(HERE, 'out', f), PK)
    shutil.copy2(os.path.join(HERE, d['sheet']), PK)
    os.makedirs(os.path.join(PK, 'renders'))
    for r in d['renders']:
        shutil.copy2(os.path.join(HERE, d['rend'], r + '.png'), os.path.join(PK, 'renders'))
    src = d['src'] + COMMON
    lib = closure(src)
    os.makedirs(os.path.join(PK, 'src'))
    for f in src + lib:
        shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src'))
    open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
        d['readme'] + '- Библиотека: ' + ', '.join(lib) + '.\n'
        "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
        '  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.\n')
    z = os.path.join(HERE, 'out', pk + '_package.zip')
    if os.path.exists(z):
        os.remove(z)
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(PK):
            for f in sorted(fs):
                p = os.path.join(dp, f)
                zf.write(p, os.path.relpath(p, os.path.join(HERE, 'out')))
    n = sum(len(fs) for _, _, fs in os.walk(PK))
    print('packed', pk, n, 'files; lib', lib, '; zip', os.path.getsize(z))
