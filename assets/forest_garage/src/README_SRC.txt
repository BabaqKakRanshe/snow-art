Исходники гаража (префаб Garage). Пакет — папка выше (garage.blend, атласы, контракт), архив — ../../forest_garage_package.zip,
справочник — docs/gdd/GARAGE_CONTRACT.md.

- Модель целиком строится скриптами. Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint);
  мебель, фурнитура и часть красок — модули главного корпуса (main_furn, main_rooms, main_open, main_paint).
- Данные обновления 3: gar_spec.py (размеры, проёмы, двери с точками, осями и ходами, окна, свет, содержимое — сняты с
  Garage.fbx), gar_u3_data.json (из Forest_Layout.json: детали, источники, ореолы, питание), gar_u3_materials.json
  (материалы, которые игра знает по имени).
- Порядок: gar_build.py → out/garage.blend, garage.json, garage_contract.json, tex/garage
  (gar_build.py --draft — без запекания, цвета зон → garage_draft.blend; --only Parts — запечь только этот атлас);
  gar_render.py <виды через запятую | all> [spp] [--gate=85 --side=100 --tag=open] → rend/garage;
  make_gar_doc.py → docs/GARAGE_CONTRACT.md; make_sheets_gar.py → sheets/gar_A…D.jpg; pack_gar.py → out/forest_garage_package.zip.
- bld_common.py — общие шаги сборки (из сборки главного корпуса): объекты, сварка, разведение совпадающих граней,
  атласы через один запекаемый прокси, материалы обновления 3, присоединение стекла, табличек и линз.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке; скрипты пишут в out/, tex/, rend/, sheets/, docs/ внутри неё.
- checks/ — проверки (run_checks.sh → логи и checks_summary.json; логи этой сборки лежат рядом): сверка с данными
  обновления 3 (детали, оси, ходы, точки, замки, свет), изнанки, совпадающие грани, проходимость капсулой игрока и
  досягаемость деталей (walk), ход ворот и двери с глубиной захода (sweep2).
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
