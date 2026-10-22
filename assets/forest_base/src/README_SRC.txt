Исходники базы (люк шахты, ящики, поленница, фонари, опоры ЛЭП и провода, рабица и старый забор, вертолётная площадка, радиомачта). Пакет — папка выше (base.blend, атласы, контракт), архив — ../../forest_base_package.zip,
справочник — docs/gdd/BASE_CONTRACT.md.

- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),
  шрифт табличек — проекта (pxfont).
- Данные обновления 3: base_u3_data.json (места префабов и рассыпки заборов, огни, ореолы, материалы, коробки FBX, GUID —
  из Forest_Layout.json, Forest_Materials.json и FBX), base_ground.json (рельеф обновления 3 под каждым префабом в его
  кадре и под каждой секцией забора), base_spec.py (размеры, места деталей, тексты).
- Порядок: base_build.py → out/base.blend, base.json, base_contract.json, tex/base
  (base_build.py --draft — без запекания, цвета зон; --only Props,Mast — запечь только эти атласы);
  base_render.py <виды | all | map | cmp> [spp] → rend/base (map — места обновления 3 на его рельефе: нужен
  terrain.blend из Forest_Terrain.fbx); make_base_doc.py → docs/BASE_CONTRACT.md; make_sheets_base.py → sheets/base_A…E.jpg;
  pack_base.py → out/forest_base_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- checks/ — проверки (base_checks.py → base_checks.json): префабы, пивот и ось крышки, коробки против обновления 3,
  изнанки, ничего не висит над рельефом, ход крышки люка, огни в колпаках, провода (концы, просвет), раскладка заборов
  обновления 3 на склонах, наложенные грани, UV; render_u3.py — модели обновления 3 с тех же камер.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
