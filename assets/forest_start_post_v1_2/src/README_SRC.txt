Исходники домика охраны StartWache (forest_start_post 1.2). Строятся библиотекой стиля tools/snow_style/lib (как будка forest_start):
- wache_kit.py — геометрия (gen_kit KB), контракт: детали, точки, коллайдеры, сдвиги деталей будки (MOVES);
- wache_paint.py — покраска атласа Wache (psxbake: AO в цвете, 64 цвета, дизеринг 4×4, точечный фильтр);
- wache_build.py — сборка: out/wache.blend, wache.json, wache_contract.json, StartWache.fbx, tex/T_Start_Wache_BaseColor.png
  (--draft — без запекания, цвета зон);
- wache_render.py <blend> <папка> <виды|all> [spp] [--wb] [--open] — виды с дверью, лампой и табличкой будки (StartBooth.fbx проекта);
- wache_sheet.py — лист рендеров renders/wache_sheet.jpg.
Запуск: положить файлы в tools/snow_style/lib, blender -b --factory-startup --python tools/snow_style/run_bpy.py -- wache_build.py.
В скриптах пути к StartBooth.fbx и текстурам проекта — из песочницы (/mnt/user-data/uploads/snow/...): заменить на свои.
