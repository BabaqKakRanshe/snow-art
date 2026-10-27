Исходники пакета forest_pager 1.0: пейджер рабочего (вид 1 «Cityruf», docs/gdd/research/RESEARCH_UI_3.md). Пакет — папка выше, справочник — docs/gdd/PAGER_CONTRACT.md. Собран локально (скилл snow-model) по образцу рации forest_gear.

- pager_kit.py — геометрия, детали и точки; pager_tex.py — панель надписей (лицо, наклейка, верх) и экран 20 x 4 знака (горит / погашен); pager_paint.py — покраска атласа.
- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- tools/snow_style/work/forest_pager/pager_build.py [--draft]; потом pager_quick.py -- <blend> <папка> [виды], pager_render.py [виды|all] [spp], pack_pager.py.
- Библиотека (копии из tools/snow_style/lib): gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.2.3.
