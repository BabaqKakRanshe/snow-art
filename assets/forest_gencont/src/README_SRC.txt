Исходники контейнера генератора на карте Forest (обновление 6): сдвоенный контейнер пакета generator_container на месте контейнера обновления 3, с его именами частей. Пакет — папка выше (gcf.blend, атласы, отчёты, листы, рендеры), архив — ../../forest_gencont_package.zip,
справочник — docs/gdd/GENCONT_FOREST_CONTRACT.md; пакет для Unity — Forest_Update6.unitypackage (его исходники —
source/locations/Forest/Forest_Update6_src).

- Порядок: gcf_build.py → out/gcf.blend, gcf.json, gcf_contract.json, tex/gcf (gcf_build.py --draft — без запекания);
  u6_render.py -- out/gcf.blend rend/u6/gcont u6_views_gcont.json → рендеры; то же с FBX обновления 3 и
  u6_views_gcont_u3.json → rend/u6/gcont_u3; make_sheets_u6.py → sheets/gcont_A…D.jpg; pack_u6.py gencont → архив.
- Модель строят модули пакета generator_container (cont_kit, gen_room, gen_set …), gcf_kit.py — изменения для карты
  (короб горловины, боковая дверь, опоры, точки стука), gcf_build.py — поворот на место обновления 3, имена частей,
  данные карты (свет, ореолы, interactables, точка обзора, горловина); gcf_ground.json — рельеф под контейнером.
- Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint), шрифт надписей — проекта (pxfont).
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
