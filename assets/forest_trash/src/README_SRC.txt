Исходники пакета forest_trash 1.0: мусор как в Voices of the Void — 6 видов, у каждого куча на земле (TrashPile_*) и спрессованный ком в руках (TrashClump_*). Пакет — папка выше, справочник — docs/gdd/TRASH_CONTRACT.md.

- Модели целиком строятся скриптами, входных файлов нет.
- trash_kit.py — вещи (газеты, картон, стаканчики, бутылки, пакеты, банки, лист, доски, ветки, стекло), кучи и комья; trash_paint.py — покраска.
- Порядок: trash_build.py → out/trash.blend, trash.json, trash_contract.json, tex/trash (--draft — цвета зон); trash_quick.py <blend> <папка> [виды] — рабочие виды; trash_render.py <виды|all> [spp] → rend/trash/*.png; rocks_trash_sheets.py trash → лист; pack_rocks_trash.py → out/forest_trash/.
- Библиотека: noise.py, psxbake.py, psxlib.py, van2_kit.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
