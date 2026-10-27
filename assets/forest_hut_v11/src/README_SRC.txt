Исходники хижины лесника 1.1. Пакет — папка выше (hut.blend, атласы, контракт), архив — ../../forest_hut_v11_package.zip,
справочник — ../HUT_V11_CONTRACT.md.

- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- Порядок: hut_build.py → out/hut.blend, hut.json, hut_contract.json, hut_lights.json, tex/hut
  (hut_build.py --draft — черновик без запекания); checks/porch_fit.py <yard.blend> → checks/porch_fit.json (ход двери
  над крыльцом forest_hut_yard); hut_render.py <виды через запятую> [spp] [--yard=<yard.blend>] → rend/hut;
  make_hut_doc.py → docs/HUT_V11_CONTRACT.md; make_sheets_hut.py → sheets/hut_A.jpg, hut_E.jpg;
  pack_hut.py → out/forest_hut_v11_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11), post_bloom.py — OpenEXR. Пути в скриптах абсолютные (HERE = '/home/claude/hut11') —
  заменить на путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- Размеры двери, места лавки, колоды и рогов — в начале hut_kit.py (DOOR, LEAF_ZL / LEAF_ZH, BENCH_C, CHOP_C, ANTLER_C).
- checks/ — проверки: ход деталей, ход двери над крыльцом, проходимость и места предметов, совпадающие и вывернутые
  грани, фонарь с дороги, пакет.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
