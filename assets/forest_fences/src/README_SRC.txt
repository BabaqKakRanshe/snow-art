Исходники комплекта заборов и заграждений Forest (обновление 7): забор ПО-2 (7 вариантов), новая рабица, спираль, блоки, надолбы, ёж, рогатка, завалы, щит HALT и знак; их расстановка на карте.
Пакет — папка выше (fences.blend, атласы, отчёты, листы, рендеры), архив — ../../forest_fences_package.zip, справочник — docs/gdd/FENCES_CONTRACT.md; пакет для Unity — Forest_Update7.unitypackage (его исходники — source/locations/Forest/Forest_Update7_src).

- Порядок: fence_build.py → out/fences.blend, fences.json, fences_contract.json, tex/fence (fence_build.py --draft — без запекания, --only Props — один атлас); fence_layout.py → out/forest_update7/u7_layout.json (места в кадре игры);
  tools/closure_u7.py → проверка замкнутости; tools/kit_render.py, tools/u7_preview.py → рендеры; tools/plan_u7.py → планы; tools/make_sheets_fences.py → листы fences_A…F.jpg; pack_u7.py → этот архив.
- fence_spec.py — размеры, fence_kit.py — геометрия, fence_paint.py — покраска атласов, fence_tex.py — панель надписей и вырезы (новая рабица, колючка, лента; replacements — 9 замен для моделей обновлений 4–5).
- Данные карты для расстановки (tools/extract_map.py, map_big.py, drive_grid.py, bones_footprint.py, bone_probe.py): рельеф, дорога, деревья, кости великана — из локации обновления 3 и данных обновления 6.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz', '/home/claude/fence') — заменить на путь к этой папке.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
