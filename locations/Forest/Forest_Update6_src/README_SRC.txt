Forest_Update6_src — как собран Forest_Update6.unitypackage

Пакет обновления 6 карты Forest: контейнер генератора GenContainer (сдвоенный контейнер пакета generator_container на месте
контейнера обновления 3, с его именами частей) и 83 предмета Item_* в стиле генераторной — с именами и GUID обновления 3;
новые модели Item_RadioSet (рация пульта Leitstand для X08) и Apparition (фигура для X02 / X03). Ставится поверх
обновления 5. Задание для Unity — docs/gdd/FOREST_U6_UNITY.md, стартовый промпт — docs/start/START_FOREST_U6.txt.

Откуда модели: пакеты source/assets/forest_gencont (gcf.blend), source/assets/forest_items (items.blend) и
source/assets/forest_figure (fig.blend), справочники docs/gdd/GENCONT_FOREST_CONTRACT.md, ITEMS_CONTRACT.md,
APPARITION_CONTRACT.md. Скрипты моделей, покраски и проверок — в src/ этих пакетов.

Порядок сборки (Blender 5.0 как модуль bpy для Python 3.11, запускать из папки со скриптами пакетов и этими):
  1. python3 -I u6_export.py -- <fbx_dir>
     FBX контейнера и предметов в формате обновления 3 (FBX 7400, Y вверх, перед +Z, UnitScaleFactor 100, корень без
     поворота, у детей только сдвиги), фигура — со скелетом и четырьмя дублями (24 к/с); отчёт u6_export_report.json
  2. python3 -I u6_verify_fbx.py -- <fbx_dir>
     каждую FBX читает обратно импортёр Blender: объекты, границы, точки поворота, треугольники, материалы; у фигуры —
     кости, дубли и позы клипов; журнал u6_verify_fbx.log
  3. python3 u6_build.py <fbx_dir> <out/forest_update5> <распакованное обновление 3> <u3raw> <out_dir>
     пакет: Models (86 FBX), Textures (8 атласов *_px), Data (Forest_Layout.json и Forest_Materials.json обновления 5,
     Forest_Opening.json, Forest_Items.json, Forest_Dressing.json и Forest_Notes.json обновления 3 — каждый с правками
     из списка changes, байт в байт в формате своего файла), README.md (обновления 5 + раздел «Обновление 6»);
     опись Forest_Update6_manifest.json (пути, GUID, md5, base_md5 — что должно лежать в проекте до импорта, changes)
  4. python3 u6_check_pkg.py <пакет> <Forest_Update5.unitypackage> <распакованное обновление 3> <u3raw>
     независимая проверка пакета: записи, GUID, данные против обновлений 3 и 5, материалы и текстуры, узлы FBX,
     скелет фигуры; журнал u6_check_pkg.log
  5. python3 make_u6_docs.py <out_dir>  ->  FOREST_U6_UNITY.md, START_FOREST_U6.txt и три справочника моделей
  6. python3 -I pack_u6.py  ->  пакеты source/assets/forest_gencont, forest_items, forest_figure и их архивы
  7. python3 u6_deliver_stage.py <out_dir> <stage_dir>  ->  всё обновление 6 по папкам проекта, архивами по ~18 МБ и md5.txt

scripts/  скрипты сборки пакета (u6_*, make_u6_docs.py, pack_u6.py, листы и рендеры сравнения) и то, что они берут из
          обновления 4 (u4_export.py, u4_build.py) и из пакета предметов (items_u3.json — коробки, треугольники и GUID
          моделей обновления 3)
reports/  опись пакета (Forest_Update6_manifest.json), отчёт экспорта, журналы проверок FBX и пакета, раздел README,
          delivery_md5.txt — md5 всего, что доставлено

Пакет: Forest_Update6.unitypackage, 106 записей, 4 032 536 байт, md5 f1271940f4ff800fe7b577fd00dea332.
