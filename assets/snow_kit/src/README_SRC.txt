Исходники набора snow_kit (общие мелкие модели K1–K12). Пакет — папка выше (snow_kit.blend, атлас, контракт), архив — ../../snow_kit_package.zip,
справочник — docs/gdd/SNOW_KIT_CONTRACT.md.

- Модели целиком строятся скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- snowkit_spec.py — имена моделей, зоны покраски, области панели, правило провода (K9); snowkit_kit.py — геометрия, детали,
  точки, коллайдеры; snowkit_tex.py — панель надписей и экраны; snowkit_paint.py — покраска атласа.
- Порядок: snowkit_build.py → out/snow_kit.blend, snow_kit.json, snow_kit_contract.json, snow_kit_lights.json, tex/snow_kit
  (--draft — без запекания); snowkit_sheet.py и snowkit_detail.py → rend/snow_kit (рабочие виды); snowkit_render.py →
  rend/snow_kit_cycles (в работе); make_sheets_snowkit.py → sheets/snow_kit_A…D.jpg; make_snowkit_doc.py →
  docs/SNOW_KIT_CONTRACT.md; pack_snowkit.py → out/snow_kit_package.zip.
- KitWire.cs — образец скрипта Unity для провода K9 (справка, в проект ставит агент Unity).
- inventory/ — что набор заменит в готовых пакетах (forest_kpp, forest_main, forest_garage, forest_gencont, forest_yard,
  forest_hut, forest_base): json и таблица; в справочнике — раздел «Что набор заменит».
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
