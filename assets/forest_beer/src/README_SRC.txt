Исходники пакета forest_beer: шесть банок пива (Harzer Pils, Ilsetaler Export, Hexenbräu Schwarzbier, Bergmann Bock, Schneekönig Leicht, Kaloschnizzer Starkbier) и мятая банка каждой марки. Пакет — папка выше, справочник — docs/gdd/BEER_CONTRACT.md, концепты — docs/gdd/items/beer/concept_v1/cans_1.png (выбран 29.10), concept_v2/kalo_front_1.png (шестая, выбрана 30.10). Собран локально (скилл snow-model) по образцу пакета forest_smoke.

- beer_kit.py — геометрия, детали (язычок, клапан) и точки; beer_tex.py — этикетки: перед развёрнут из концепта, зад дорисован пиксельным шрифтом; beer_paint.py — покраска атласа Small (жесть, крышка, язычок, темнота внутри).
- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- <абсолютный путь>/tools/snow_style/work/forest_beer/beer_build.py [--draft]; потом beer_quick.py <blend> <папка> [виды], beer_pack.py; FBX для Unity — blender -b --factory-startup <beer.blend> --python beer_export.py -- <папка>.
- Библиотека (копии из tools/snow_style/lib): gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.2.3.
