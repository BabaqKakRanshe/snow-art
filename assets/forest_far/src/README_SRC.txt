Исходники дальних точек (5 антенн, радом, ретранслятор, метеостанция, пожарная вышка, насосная, часовня, избушка, стоянка). Пакет — папка выше (far.blend, атласы, контракт), архив — ../../forest_far_package.zip,
справочник — docs/gdd/FAR_CONTRACT.md.

- Модели целиком строятся скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint / hut_paint),
  рабица и колючка — базы (base_tex), шрифт табличек — проекта (pxfont).
- Данные обновления 3: far_u3_data.json (места, огни, ореолы, двери, материалы, коробки FBX, GUID), far_ground.json
  (рельеф обновления 3 под каждым префабом в его кадре), far_lookout_stairs.json (ступени и площадки вышки из FBX),
  far_spec.py (размеры, места деталей).
- Порядок: far_build.py → out/far.blend, far.json, far_contract.json, tex/far
  (far_build.py --draft — без запекания, цвета зон; --only Dish16,Chapel — запечь только эти атласы);
  far_render.py <виды | all | map | cmp> [spp] → rend/far (map — места обновления 3 на его рельефе: нужен terrain.blend
  из Forest_Terrain.fbx); make_far_doc.py → docs/FAR_CONTRACT.md; make_sheets_far.py → sheets/far_A…G.jpg;
  pack_far.py → out/forest_far_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- checks/ — проверки (far_checks.py → far_checks.json): префабы, пивоты и оси дверей, коробки против обновления 3,
  копии антенн, изнанки, ничего не висит, ход дверей и проёмы, голова игрока на лестнице вышки, огни в колпаках,
  наложенные грани, UV; render_u3.py — модели обновления 3 с тех же камер.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
