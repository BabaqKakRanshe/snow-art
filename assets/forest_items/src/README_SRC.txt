Исходники 84 предметов Forest (обновление 6): 83 модели обновления 3 в стиле генераторной и рация пульта Leitstand. Пакет — папка выше (items.blend, атласы, отчёты, листы, рендеры), архив — ../../forest_items_package.zip,
справочник — docs/gdd/ITEMS_CONTRACT.md; пакет для Unity — Forest_Update6.unitypackage (его исходники —
source/locations/Forest/Forest_Update6_src).

- Порядок: items_build.py → out/items.blend, items.json, tex/items (--draft — без запекания; --only Item_A,Item_B);
  item_sheet2.py (checks) → контактные листы; u6_items_cmp.py → обновление 3 и теперь; make_sheets_u6.py →
  sheets/items_A…F.jpg; pack_u6.py items → архив.
- items_kit.py — модели (кадр и начало координат обновления 3), items_tex.py — панель надписей (пиксельный шрифт),
  items_paint.py — покраска атласа; items_u3.json — коробки, треугольники, каталог и GUID моделей обновления 3;
  u6_radio.py — место рации на пульте (кадр BaseMain → мир Unity).
- checks/: label_check.py (надписи не перекрыты корпусом), shape_cmp.py (центр и заполнение против обновления 3:
  перевёрнутая модель видна сразу), radio_check.py (рация на пульте в main.blend: пересечения, виды) — с журналами.
- Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint), шрифт надписей — проекта (pxfont).
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
