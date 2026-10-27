Исходники пакета sky_systems 1.0: системы высоты Небесного острова — холодильная установка, распылитель костяной пыли, сброс балласта на краю, табло высоты у вышки — и модули мостков под островом. Пакет — папка выше, справочник — docs/gdd/SKY_CONTRACT.md.

- Модели целиком строятся скриптами. sky_kit.py — геометрия, детали, точки, коллайдеры; sky_tex.py — панель (табло высоты, пульты, таблички) и решётка настила; sky_paint.py — покраска атласов SkyMachines и SkyWalk.
- Порядок: sky_build.py → out/sky.blend, sky.json, sky_contract.json, sky_lights.json, tex/sky (--draft — цвета зон; --reuse A,B — те же развёртки и прежние атласы без запекания); sky_quick.py -- <blend> <папка> [виды] — рабочие виды; sky_render.py <виды|all> [spp] → rend/sky/*.png; sky_sheet.py → лист; pack_sky.py → out/sky_systems/.
- Библиотека: gear_tex.py, gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
