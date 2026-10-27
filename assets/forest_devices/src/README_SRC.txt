Исходники пакета forest_devices 1.0: факс и принятый факс, кассета и коробка кассет, ящик для кассет, компьютер объекта, ноутбук, магнитофон телеметрии в шкаф антенны, метеобудка. Пакет — папка выше, справочник — docs/gdd/DEVICES_CONTRACT.md.

- Модели целиком строятся скриптами; монитор компьютера — Kit_Monitor_CRT из ../snow_kit/snow_kit.blend (связь).
- devices_kit.py — геометрия, детали и точки; devices_tex.py — панель надписей (панели, клавиши, наклейки, шкалы термометров, лента термогигрографа), дисплей факса, экран ноутбука, бумага факса; devices_paint.py — покраска атласов.
- Порядок: devices_build.py → out/devices.blend, devices.json, devices_contract.json, tex/devices (--draft — цвета зон); devices_quick.py -- <blend> <папка> [виды] — рабочие виды; devices_render.py <виды|all> [spp] → rend/devices/*.png; devices_sheet.py → лист; pack_devices.py → out/forest_devices/. Для сборки рядом нужна папка snow_kit (snow_kit.blend и tex).
- Библиотека: gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
