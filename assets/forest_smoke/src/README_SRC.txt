Исходники пакета forest_smoke 2.0: три пачки сигарет (Harzgold, Brocken, Nordlicht), зажигалка BLITZ, сигарета. Пакет — папка выше, справочник — docs/gdd/SMOKE_CONTRACT.md, концепты — docs/gdd/concept/09_smoking (выбраны packs_1 и lighter_1). Собран локально (скилл snow-model) по образцу пейджера forest_pager.

- smoke2_kit.py — геометрия, детали и точки; smoke2_tex.py — печать пачек (2000 px/м), этикетка и пламя зажигалки, фильтры, огонёк, клуб дыма; smoke2_paint.py — покраска атласа Small.
- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- tools/snow_style/work/forest_smoke/smoke2_build.py [--draft]; потом smoke2_quick.py <blend> <папка> [виды], smoke2_pack.py; FBX для Unity — blender -b --factory-startup <smoke.blend> --python smoke2_export.py -- <папка>.
- Библиотека (копии из tools/snow_style/lib): gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.2.3.
