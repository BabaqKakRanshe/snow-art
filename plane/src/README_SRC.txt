Исходники самолёта Utility Plane (v2…v13) и зимнего комплекта. Готовые пакеты лежат рядом:
../UtilityPlane_Unity_v13 и ../UtilityPlane_WinterKit_v1_2.

- Скрипты Python для Blender 5.0.1: bpy как модуль Python 3.11 (python -I script.py) или blender -b -P script.py.
  Пути в скриптах абсолютные (HERE = '/home/claude/plane') — заменить на путь к этой папке.
- Рабочие сцены линии v9 → v13 и комплекта — out/*.blend. Текстуры к ним подключены относительными путями:
  export/unity_v9 — мастера высокого разрешения, export/unity_v11 — вход PSX-ступени v12, export/unity_kit — комплект,
  export/unity_v7 — две карты нормалей для сцен комплекта.
- Порядок v9 → v13: export_unity_v13.py (out/plane_v9_final_v9.blend → plane_v9_final_v13.blend, plane_unity_v13.blend,
  export/unity_v13fx) → v13/make_package_v13.py (export/unity_v13 поверх пакета v12r2; продолжать от
  ../UtilityPlane_Unity_v13) → v13/make_blend13.py → v13/build_docs13.py. PSX-текстуры — v12/ и v12r2/.
  Ранние версии — скрипты в корне и docs_v*/.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
