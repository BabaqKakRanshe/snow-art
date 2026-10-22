Van_Unity_v1/src — как собран пакет машины для Unity

Исходник модели: пакет source/vehicles/van3 (van3.blend, VAN3_CONTRACT.md — в docs/gdd). Blender 5.0 как модуль bpy
для Python 3.11 + numpy, Pillow; скрипты ждут рядом out/van3.blend и tex/van3 (атласы, маски, Cookies, IES из пакета van3).

  1. python3 -I van_unity_export.py -- <out>
     out/van3.blend -> <out>/Models/Van.fbx в осях Unity (тело x вперёд, y влево, z вверх -> Unity (-y, z, x);
     у деталей единичный локальный поворот, начало — шарнир), стёкла — отдельные объекты с масками на UV1,
     треугольники, отчёт van_export_report.json
  2. python3 -I van_tools/fbx_check.py <out>/Models/Van.fbx <out>/van_export_report.json
     FBX читается заново парсером Blender так, как его читает Unity: узлы, родители, начала, границы, UV, blend
     shapes против отчёта -> reports/fbx_check.log (PROBLEMS 0)
  3. python3 -I van_wipe_map.py -- <out>   ->  Textures/T_Van_WipeMap.png (дуги дворников на UV лобового)
  4. python3 -I van_unity_data.py -- <out>  ->  Assets/Van/Data/*.json (детали, сокеты, коллайдеры, свет, стёкла,
     зоны, места, предметы, материалы, машина, сводка)
  5. python3 van_tools/data_check.py <Data> <out>/van_export_report.json <Editor/VanSetup.cs>
     имена деталей, родителей, линз, сокетов, материалов и blend shapes против FBX; типы полей против классов
     JsonUtility в VanSetup; вложенные массивы -> reports/data_check.log (PROBLEMS 0)
  6. python3 -I van_tools/unity_frame_check.py -- <Van.fbx> <Data> <out>/checks/frame
     модель импортируется обратно, поверх неё рисуются данные (коллайдеры, лампы, сокеты, оси деталей, глаза мест)
     -> previews/frame/*, reports/unity_frame_check.log
  7. python3 van_stage_pkg.py <stage>  ->  эта папка пакета, md5 всех файлов в reports/package_md5.txt

van_lights.py — диаграммы излучения ламп: IES и маски Cookies (из пакета van3, для справки).
C#: Scripts / Editor пакета собраны компилятором Roslyn (dotnet 8, C# 9 и 7.3) против заглушек API Unity —
reports/compile_check.log; в самом Unity пакет не запускался (этап В1 задания VAN3_INTEGRATION_UNITY.md).
