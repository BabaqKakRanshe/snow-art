Исходники КПП (будка, шлагбаум, ворота). Пакет — папка выше (kpp.blend, атласы, контракт), архив — ../../forest_kpp_package.zip,
справочник — docs/gdd/KPP_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- Порядок: kpp_build.py → out/kpp.blend, kpp.json, kpp_contract.json, kpp_lights.json, tex/kpp
  (kpp_build.py --draft — черновик без запекания); kpp_render.py <виды через запятую> [spp] → rend/kpp
  (окружение — kpp_site.json: деревья, земля и забор карты вокруг КПП из Forest_Layout.json);
  make_kpp_doc.py → docs/KPP_CONTRACT.md; make_sheets_kpp.py → sheets/kpp_A…E.jpg; pack_kpp.py → out/forest_kpp_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки: ход деталей, проходимость и места предметов, совпадающие грани, места на карте, пакет.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
