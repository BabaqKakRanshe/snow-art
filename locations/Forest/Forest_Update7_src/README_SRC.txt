Как собран Forest_Update7.unitypackage (обновление 7 карты Forest: заборы и заграждения).

Порядок (в /home/claude/uaz):
1. fence_build.py → out/fences.blend (комплект); fence_layout.py → out/forest_update7/u7_layout.json (места в кадре игры:
   периметр ПО-2, КПП, линии надолбов; убираемые деревья; просветы вдоль линий; проверка, что предметы не налезают);
   closure_u7.py u7_layout.json → u7_layout_closure.json (куда доедет фургон и дойдёт человек).
2. python3 -I u7_export.py -- out/forest_update7/fbx → 22 FBX + u7_export_report.json.
3. python3 -I u7_verify_fbx.py -- out/forest_update7/fbx → u7_verify_fbx.json (обратный импорт: 0 замечаний).
4. python3 u7_build.py out/forest_update7/fbx out/forest_update6 <u3raw> out/forest_update7 → stage/, пакет, опись.
5. python3 -I u7_check_pkg.py <пакет 7> <пакет 6> <пакет 5> <пакет 4> <u3raw> → u7_check_pkg.log (независимая проверка).
6. python3 make_u7_docs.py out/forest_update7 → docs/FOREST_U7_UNITY.md, START_FOREST_U7.txt, FENCES_CONTRACT.md.

reports/: опись пакета (Forest_Update7_manifest.json), отчёты экспорта и обратного импорта, места (u7_layout.json),
проверка замкнутости, журнал проверки пакета, раздел README. Исходники моделей — source/assets/forest_fences/src.
