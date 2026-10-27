Исходники главного корпуса станции (BaseMain и BaseMain_Opening). Пакет — папка выше (main.blend, атласы, контракт), архив — ../../forest_main_package.zip,
справочник — docs/gdd/MAIN_CONTRACT.md.

- Модель целиком строится скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint).
- Данные обновления 3, с которых снята планировка: main_spec.py (размеры, комнаты, двери, окна), main_ix_u3.py
  (139 деталей: точки, оси, ходы), main_fx_u3.py (64 светильника и их свет), main_u3_data.json (из Forest_Layout.json:
  маски света, источники, ореолы, детали), main_u3_materials.json (материалы, которые игра знает по имени).
- 1.2: main.blend берёт модели набора snow_kit по ссылке ../snow_kit/snow_kit.blend (пункт управления КПП в пультовой:
  экземпляры — KIT_INST в main_rooms.py, раздел 1b в main_build.py; пакет набора — source/assets/snow_kit).
- kit_preview.py — только для превью: монитор камеры ворот показывает свою заглушку (CAM 2, T_Kit_Screen_On_Gate набора);
  в Unity на экранах — картинки камер КПП.
- Порядок: main_build.py → out/main.blend, main.json, main_contract.json, tex/main; затем fix_glass_dupes.py out/main.blend
  (стекло — по одной грани на сторону); main_leit_check.py → out/main_leit_check.json (зазоры пункта управления до
  предметов Forest_Dressing и настольной лампы на том же столе)
  (main_build.py --only Rm_Windfang,MainParts — запечь только эти атласы, остальное — плоские цвета → main_test.blend);
  main_draft.py — черновик геометрии с цветами зон; main_render.py <виды через запятую | all> [spp] → rend/main;
  make_main_doc.py → docs/MAIN_CONTRACT.md; make_sheets_main.py → sheets/main_A…F.jpg; pack_main.py → out/forest_main_package.zip.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки (run_checks.sh → логи и checks_summary.json; логи этой сборки лежат рядом): сверка с данными
  обновления 3 (детали, оси, ходы, маски, свет), изнанки, совпадающие грани, предметы и надписи пролога на поверхностях,
  проходимость капсулой игрока и досягаемость деталей (walk), ход подвижных деталей с глубиной захода (sweep2).
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
