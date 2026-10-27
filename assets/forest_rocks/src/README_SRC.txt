Исходники пакета forest_rocks 1.0: 6 камней, 3 валуна и 3 скалы Forest (гранит, как останцы Гарца). Пакет — папка выше, справочник — docs/gdd/ROCKS_CONTRACT.md.

- Модели целиком строятся скриптами, входных файлов нет.
- rocks_kit.py — геометрия: эллипсоид или «подушка» с шумом и плоскими сколами; скалы — блоки, сращённые вокселями (Remesh) и прореженные (Decimate); rocks_paint.py — покраска гранита (лишайник, мох, хвоя, потёки, земля у подножия).
- Порядок: rocks_build.py → out/rocks.blend, rocks.json, rocks_contract.json, tex/rocks (--draft — без запекания); rocks_quick.py <blend> <папка> [виды] — рабочие виды; rocks_render.py <виды|all> [spp] → rend/rocks/*.png; rocks_trash_sheets.py rocks → лист; pack_rocks_trash.py → out/forest_rocks/.
- Библиотека: noise.py, psxbake.py, psxlib.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
