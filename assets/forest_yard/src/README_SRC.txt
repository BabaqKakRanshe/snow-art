Исходники двора станции (баки ГСМ, трансформатор). Пакет — папка выше (yard.blend, атласы, контракт), архив — ../../forest_yard_package.zip,
справочник — docs/gdd/YARD_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- Порядок: yard_build.py → out/yard.blend, yard.json, yard_contract.json, tex/yard
  (yard_build.py --draft — черновик без запекания); yard_render.py <виды через запятую> [spp] [--u3] → rend/yard
  (окружение — site/fuel_site.blend и .json: земля, дорога, двор, провода, деревья, забор карты вокруг баков;
  их режет site_patch.py из Forest_Terrain.fbx / Forest_Wires.fbx проекта и Forest_Layout.json);
  make_yard_doc.py → docs/YARD_CONTRACT.md; make_sheets_yard.py → sheets/yard_A…E.jpg; pack_yard.py → out/forest_yard_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки: совпадающие грани, ход рычага и калитки, проходимость, места на карте и точки пролога, пакет.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
