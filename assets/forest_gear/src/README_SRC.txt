Исходники пакета forest_gear 1.0: батарейки (D, упаковка, 6 В), рация, фонарь 6 В с жёлтым стеклом, налобный фонарь, тележка, волокуша, кукла и открытка, лампочка и коробка, латунный жетон, ключ Stationsleiter, ледоруб. Пакет — папка выше, справочник — docs/gdd/GEAR_CONTRACT.md.

- Модели целиком строятся скриптами. gear_kit.py — геометрия, детали и точки; gear_tex.py — панель надписей (обёртки батареек, лицо и верх рации, таблички фонарей, лицо куклы, коробка лампочки, жетон, бирка ключа) и свои текстуры (дисплей рации, открытка — картинка и оборот, стекло лампочки новое и перегоревшее); gear_paint.py — покраска атласов.
- Текст открытки и номер жетона — константы в gear_tex.py (POSTCARD_MSG, POSTCARD_SIG, TAG_NUMBER).
- Порядок: gear_build.py → out/gear.blend, gear.json, gear_contract.json, tex/gear (--draft — цвета зон); gear_quick.py -- <blend> <папка> [виды] — рабочие виды; gear_render.py <виды|all> [spp] → rend/gear/*.png; gear_sheet.py → лист; pack_gear.py → out/forest_gear/.
- Библиотека: gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
