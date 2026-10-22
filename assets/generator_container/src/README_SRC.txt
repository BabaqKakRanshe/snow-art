Исходники генераторной в контейнере. Пакет — папка выше (cont.blend, атласы, контракт), архив — ../../cont_package.zip,
справочник — docs/gdd/GENCONT_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет. Оборудование внутри — генераторной (gen_set, gen_room):
  строится теми же модулями и переносится в контейнер группами (таблица переноса — в cont_kit.py).
- Порядок: cont_build.py → out/cont.blend, cont.json, cont_contract.json, cont_lights.json, tex/cont
  (cont_build.py --draft — черновик без запекания); cont_render.py <виды через запятую> [spp] → rend/cont;
  make_cont_doc.py → docs/GENCONT_CONTRACT.md; make_sheets_cont.py → sheets/cont_A…C.jpg; pack_cont.py → out/cont_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки: оси и ход деталей, проходимость, совпадающие и вывернутые грани, пакет.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
