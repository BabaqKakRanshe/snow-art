Исходники хижины лесника. Пакет — папка выше (hut.blend, атласы, контракт), архив — ../../forest_hut_package.zip,
справочник — docs/gdd/HUT_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- Порядок: hut_build.py → out/hut.blend, hut.json, hut_contract.json, hut_lights.json, tex/hut
  (hut_build.py --draft — черновик без запекания); hut_render.py <виды через запятую> [spp] → rend/hut;
  make_hut_doc.py → docs/HUT_CONTRACT.md; make_sheets_hut.py → sheets/hut_A…D.jpg; pack_hut.py → out/forest_hut_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки: ход деталей, проходимость и места предметов, совпадающие и вывернутые грани, фонарь с дороги, пакет.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
