Исходники пакета forest_parts 1.0: насос-дозатор для насосной (со шлангом для установленного положения), натриевая лампа 400 Вт и её коробка, кинескоп радара, блок ретранслятора RT-7, резервный генератор, датчик у озера. Пакет — папка выше, справочник — docs/gdd/PARTS_CONTRACT.md.

- Модели целиком строятся скриптами. parts_kit.py — геометрия, детали, точки и место насоса в насосной forest_far; parts_tex.py — панель надписей (лицевая и задняя панели блока, щиток генератора, схема насоса, шкалы, наклейки, коробка лампы, табличка и ярлык датчика, плата регистратора) и свои текстуры (накладная, экран кинескопа); parts_paint.py — покраска атласов.
- Дата накладной — константа WAYBILL_DATE в parts_tex.py.
- Порядок: parts_build.py → out/parts.blend, parts.json, parts_contract.json, tex/parts (--draft — цвета зон); parts_quick.py -- <blend> <папка> [виды] — рабочие виды; parts_render.py <виды|all> [spp] → rend/parts/*.png (насосная берётся из ../forest_far/far.blend, батарейка 6 В — из ../forest_gear/gear.blend); parts_sheet.py → лист; pack_parts.py → out/forest_parts/.
- Библиотека: gear_kit.py, gear_tex.py, gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/ внутри неё.
