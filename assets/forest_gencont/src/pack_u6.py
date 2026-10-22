"""Package the three asset batches of Forest Update 6 the way the base / far batches are packed: the .blend with relative
texture paths, the textures, the reports and the contract (JSON + Russian reference), the sheets, the renders, the full
source (the import closure of the build scripts) with the checks.
python3 -I pack_u6.py [gencont] [items] [figure]  ->  out/forest_<name>/ and out/forest_<name>_package.zip"""
import os, sys, shutil, zipfile, glob, ast
sys.path.insert(0, '/home/claude/uaz')
import bpy

HERE = '/home/claude/uaz'
RU = {
    'gencont': ('Исходники контейнера генератора на карте Forest (обновление 6): сдвоенный контейнер пакета generator_container на '
                'месте контейнера обновления 3, с его именами частей.',
                'GENCONT_FOREST_CONTRACT.md',
                '- Порядок: gcf_build.py → out/gcf.blend, gcf.json, gcf_contract.json, tex/gcf (gcf_build.py --draft — без запекания);\n'
                '  u6_render.py -- out/gcf.blend rend/u6/gcont u6_views_gcont.json → рендеры; то же с FBX обновления 3 и\n'
                '  u6_views_gcont_u3.json → rend/u6/gcont_u3; make_sheets_u6.py → sheets/gcont_A…D.jpg; pack_u6.py gencont → архив.\n'
                '- Модель строят модули пакета generator_container (cont_kit, gen_room, gen_set …), gcf_kit.py — изменения для карты\n'
                '  (короб горловины, боковая дверь, опоры, точки стука), gcf_build.py — поворот на место обновления 3, имена частей,\n'
                '  данные карты (свет, ореолы, interactables, точка обзора, горловина); gcf_ground.json — рельеф под контейнером.\n'),
    'items': ('Исходники 84 предметов Forest (обновление 6): 83 модели обновления 3 в стиле генераторной и рация пульта Leitstand.',
              'ITEMS_CONTRACT.md',
              '- Порядок: items_build.py → out/items.blend, items.json, tex/items (--draft — без запекания; --only Item_A,Item_B);\n'
              '  item_sheet2.py (checks) → контактные листы; u6_items_cmp.py → обновление 3 и теперь; make_sheets_u6.py →\n'
              '  sheets/items_A…F.jpg; pack_u6.py items → архив.\n'
              '- items_kit.py — модели (кадр и начало координат обновления 3), items_tex.py — панель надписей (пиксельный шрифт),\n'
              '  items_paint.py — покраска атласа; items_u3.json — коробки, треугольники, каталог и GUID моделей обновления 3;\n'
              '  u6_radio.py — место рации на пульте (кадр BaseMain → мир Unity).\n'
              '- checks/: label_check.py (надписи не перекрыты корпусом), shape_cmp.py (центр и заполнение против обновления 3:\n'
              '  перевёрнутая модель видна сразу), radio_check.py (рация на пульте в main.blend: пересечения, виды) — с журналами.\n'),
    'figure': ('Исходники фигуры Apparition (обновление 6) для пугалок X02 и X03.',
               'APPARITION_CONTRACT.md',
               '- Порядок: fig_build.py → out/fig.blend, fig.json, tex/fig (--draft — без запекания); checks/fig_render2.py →\n'
               '  лист поз, fig_sit_render.py → поза в фургоне (макет скамьи, вид зеркала); make_sheets_u6.py → sheets/fig_A…C.jpg;\n'
               '  pack_u6.py figure → архив.\n'
               '- fig_build.py строит меш, скелет (20 костей), веса, атлас и четыре клипа; ход и посадка рассчитываются на сетке:\n'
               '  опорная стопа стоит на земле, маховая проходит над ней, поза Sit — под потолком скамьи фургона (fig.json → sit).\n'
               '- checks/: walk_speed.py (стопа опоры на ходу), fig_top.py, fig_bones.py — с журналом.\n'),
}
CFG = {
    'gencont': dict(blend='gcf.blend', tex='gcf', json=['gcf.json', 'gcf_contract.json'], sheets='gcont_*.jpg',
                    renders={'': 'rend/u6/gcont/*.png', 'u3': 'rend/u6/gcont_u3/*.png'},
                    src=['gcf_build.py', 'gcf_kit.py', 'gcf_ground.json', 'u6_render.py', 'u6_views_gcont.json',
                         'u6_views_gcont_u3.json', 'make_sheets_u6.py', 'pack_u6.py'],
                    checks=[]),
    'items': dict(blend='items.blend', tex='items', json=['items.json'], sheets='items_*.jpg',
                  renders={'u3_vs_now': 'rend/u6/items_cmp/*.png'},
                  src=['items_build.py', 'items_kit.py', 'items_paint.py', 'items_tex.py', 'items_u3.json', 'u6_radio.py',
                       'u6_items_cmp.py', 'make_sheets_u6.py', 'pack_u6.py'],
                  checks=['u6_tools/label_check.py', 'u6_tools/shape_cmp.py', 'u6_tools/item_sheet2.py', 'u6_tools/radio_check.py',
                          'u6_checks/label_check.log', 'u6_checks/shape_cmp.log', 'u6_checks/radio_check.log',
                          'u6_checks/radio_views/*.png']),
    'figure': dict(blend='fig.blend', tex='fig', json=['fig.json'], sheets='fig_*.jpg',
                   renders={'poses': 'rend/u6/figsheets/fr2_tmp/*.png', 'van': 'rend/u6/figsheets/sit_tmp/*.png'},
                   src=['fig_build.py', 'make_sheets_u6.py', 'pack_u6.py'],
                   checks=['u6_tools/fig_render2.py', 'u6_tools/fig_sit_render.py', 'u6_tools/walk_speed.py', 'u6_tools/fig_top.py',
                           'u6_tools/fig_bones.py', 'u6_checks/walk_speed.log']),
}


def pack(name):
    c = CFG[name]
    PK = os.path.join(HERE, 'out', f'forest_{name}')
    if os.path.isdir(PK):
        shutil.rmtree(PK)
    os.makedirs(os.path.join(PK, 'tex'))
    src_tex = os.path.join(HERE, 'tex', c['tex'])
    for f in glob.glob(os.path.join(src_tex, '*.json')):
        shutil.copy2(f, os.path.join(PK, 'tex'))
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', c['blend']))
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
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, c['blend']), relative_remap=False)
    for f in glob.glob(os.path.join(src_tex, '*.png')):            # every atlas of the batch, used or not by a material
        if not os.path.exists(os.path.join(PK, 'tex', os.path.basename(f))):
            shutil.copy2(f, os.path.join(PK, 'tex'))
    for f in c['json']:
        shutil.copy2(os.path.join(HERE, 'out', f), PK)
    title, contract, order = RU[name]
    shutil.copy2(os.path.join(HERE, 'docs', contract), PK)
    for f in sorted(glob.glob(os.path.join(HERE, 'sheets', c['sheets']))):
        shutil.copy2(f, PK)
    for sub, pat in c['renders'].items():
        d = os.path.join(PK, 'renders', sub)
        os.makedirs(d, exist_ok=True)
        for f in sorted(glob.glob(os.path.join(HERE, pat))):
            shutil.copy2(f, d)
    os.makedirs(os.path.join(PK, 'src', 'checks'))
    for f in c['src']:
        shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src', os.path.basename(f)))
    for pat in c['checks']:
        for f in sorted(glob.glob(os.path.join(HERE, pat))):
            shutil.copy2(f, os.path.join(PK, 'src', 'checks', os.path.basename(f)))
    local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith('.py')}
    have = {os.path.splitext(os.path.basename(f))[0] for f in c['src'] if f.endswith('.py')}
    todo, extra = list(have), []
    while todo:                                                    # the whole import closure of the local modules
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
    for f in ('noise.py',):                                        # imported inside functions by some modules
        if not os.path.exists(os.path.join(PK, 'src', f)):
            shutil.copy2(os.path.join(HERE, f), os.path.join(PK, 'src', f))
    open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
        title + f' Пакет — папка выше ({c["blend"]}, атласы, отчёты, листы, рендеры), архив — ../../forest_{name}_package.zip,\n'
        f'справочник — docs/gdd/{contract}; пакет для Unity — Forest_Update6.unitypackage (его исходники —\n'
        'source/locations/Forest/Forest_Update6_src).\n\n' + order +
        '- Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint), шрифт надписей — проекта (pxfont).\n'
        "- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на\n"
        '  путь к этой папке.\n- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.\n')
    lines = []
    for r, ds, fs in os.walk(os.path.join(PK, 'src')):
        ds.sort()
        for f in sorted(fs):
            if f.endswith('.py'):
                p = os.path.join(r, f)
                d = ast.get_docstring(ast.parse(open(p).read())) or ''
                lines.append(f'{os.path.relpath(p, os.path.join(PK, "src")):40s} {d.strip().splitlines()[0] if d.strip() else ""}')
    open(os.path.join(PK, 'src', 'SCRIPTS_INDEX.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    zp = os.path.join(HERE, 'out', f'forest_{name}_package.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(PK):
            for f in sorted(files):
                if f.endswith(('.blend1', '.pyc')):
                    continue
                p = os.path.join(root, f)
                z.write(p, os.path.join(f'forest_{name}', os.path.relpath(p, PK)))
    print(name, 'missing textures', missing, 'also packed', sorted(extra))
    print(zp, os.path.getsize(zp))


if __name__ == '__main__':
    for n in (sys.argv[1:] or list(CFG)):
        pack(n)
