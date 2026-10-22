Исходники генераторной. Пакет — папка выше (gen.blend, атласы, контракт), архив — ../../gen_package.zip,
справочник — docs/gdd/GEN_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет.
- Порядок: gen_build.py → out/gen.blend, gen.json, gen_contract.json, gen_lights.json, tex/gen;
  gen_render.py <виды через запятую> [spp] → rend/gen; make_gen_doc.py → docs/GEN_CONTRACT.md;
  make_sheets_gen.py → sheets/gen_A…C.jpg; pack_gen.py → out/gen_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки: оси и ход деталей, проходимость, совпадающие и вывернутые грани, плавающие куски, сугроб.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
