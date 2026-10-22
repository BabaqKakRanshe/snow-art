Исходники дороги пролога (18 префабов: указатели, столбик, ворота SPERRGEBIET, мост, площадка, бурелом). Пакет — папка выше (road.blend, атласы, контракт), архив — ../../forest_road_package.zip,
справочник — docs/gdd/ROAD_CONTRACT.md.

- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),
  рабица — КПП / двора (yard_tex), шрифт табличек — проекта (pxfont).
- Данные обновления 3: road_u3_data.json (места префабов и 48 столбиков, кадры, материалы, коробки FBX — из
  Forest_Layout.json, Forest_Materials.json и FBX), road_ground.json (рельеф обновления 3 под каждым префабом в его кадре:
  снят с Forest_Terrain.fbx скриптом road_ground.py из проверок), road_spec.py (размеры, тексты, цвета).
- Порядок: road_build.py → out/road.blend, road.json, road_contract.json, tex/road
  (road_build.py --draft — без запекания, цвета зон; --only Signs,Gate — запечь только эти атласы);
  road_render.py <виды | all | map | cmp> [spp] → rend/road (map — кадры обновления 3 на его рельефе: нужен
  terrain.blend из Forest_Terrain.fbx); make_road_doc.py → docs/ROAD_CONTRACT.md; make_sheets_road.py → sheets/road_A…E.jpg;
  pack_road.py → out/forest_road_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- checks/ — проверки (road_checks.py → road_checks.json): префабы и коробки против обновления 3, изнанки, всё ли стоит на
  земле, проход капсулы игрока по мосту и на площадку, колеи моста для машины, свободна ли дорога между спилами ели,
  столбики на рельефе; render_u3.py — модели обновления 3 с тех же камер; road_ground.py — снятие рельефа.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
