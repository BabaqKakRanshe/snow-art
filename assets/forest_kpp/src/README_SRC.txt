Исходники КПП v2 (будка, электрический шлагбаум, ворота с приводом). Пакет — папка выше (kpp.blend, атласы, контракт), архив — ../../forest_kpp_package.zip,
справочник — docs/gdd/KPP_CONTRACT.md. Мелочи — экземпляры набора snow_kit (пакет ../../snow_kit, справочник docs/gdd/SNOW_KIT_CONTRACT.md).

- Модель целиком строится скриптами, входных файлов нет. Отделка и покраска — генераторной (gen_kit, gen_paint).
- Сначала собирается набор (snow_kit, его src): kpp_kit.py берёт его контракт (out/snow_kit_contract.json), kpp_build.py
  ссылается на его модели из ../snow_kit/snow_kit.blend; snowkit_spec.py и snowkit_kit.py здесь — для правила провода.
- Порядок: kpp_build.py → out/kpp.blend, kpp.json, kpp_contract.json, kpp_lights.json, tex/kpp (--draft — без запекания);
  kpp2_quick.py <blend> <папка> [виды] — рабочие виды; kpp2_plan.py <blend> <png> — план с подписями;
  kpp2_game.py -- <папка> [spp] [виды|all] — КПП v2 в сцене игры обновления 7 (нужна сцена u7_game.blend из исходников
  forest_fences: u7_preview.py), стены walls/ и выровненная земля → renders/;
  make_kpp_doc.py → docs/KPP_CONTRACT.md (сравнивает с контрактом v1: kpp_contract_v1.json, в скрипте путь
  out/forest_kpp_v1/kpp_contract.json); make_sheets_kpp.py → sheets/kpp_A…E.jpg; pack_kpp.py → out/forest_kpp_package.zip.
- kpp2_frame.py — кадры: будка ↔ Unity ↔ игра (перенос ForestRelocation, двор ForestYardPlan).
- kpp2_ground.py — высота земли игры под точкой в кадре будки или ворот (по walls_v2/terrain_levelled_1_1.npy, его пишет
  walls/walls_v2.py): ею сняты высоты мачт камер и опор в kpp_kit.py (2.1).
- kit_preview.py — только для превью: монитор камеры ворот показывает свою заглушку (CAM 2, T_Kit_Screen_On_Gate набора);
  в Unity на экранах — картинки камер.
- Стены у ворот и шлагбаума — отдельные скрипты в ../walls/ (walls_v2.py и др., отчёт REPORT.md).
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
