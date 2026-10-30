Исходники пакета forest_station 1.0: стеллаж на 9 мониторов (Station_MonitorRack_3x3) и приставной столик (Station_SideTable) для пункта охраны. Пакет — папка выше, справочник — docs/gdd/STATION_CONTRACT.md. Собран локально (скилл snow-model), класс prop (64 px/м, стойки 128 px/м).

- station_kit.py — геометрия и точки Slot_*; station_paint.py — покраска атласа Props; station_view.py — мониторы и компьютер для превью (связью из ../snow_kit и ../forest_devices, в station.blend их нет).
- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- tools/snow_style/work/forest_station/station_build.py [--draft]; потом station_check.py, station_quick.py <blend> <папка> [виды], station_render.py [виды|all] [spp], pack_station.py, station_export.py.
- Библиотека (копии из tools/snow_style/lib): gen_kit.py, gen_paint.py, gen_tex.py, noise.py, psxbake.py, psxlib.py, pxfont.py, van2_kit.py, van2_tex.py, van3_mech.py.
- Blender 5.2.3.
