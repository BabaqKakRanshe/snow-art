"""Van_Unity_v1: assemble the Unity package of the van for source/vehicles/Van_Unity_v1 on the PC.
python3 van_stage_pkg.py <stage_dir>
Sources: out/van_unity (Van.fbx, Data, wipe map, checks, reports), tex/van3 (atlases, masks, cookies, IES),
van_unity_src (Scripts, Editor, Shaders, README.md), the scripts of this folder."""
import os, sys, shutil, hashlib, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'van_unity')
TEX = os.path.join(HERE, 'tex', 'van3')
SRC = os.path.join(HERE, 'van_unity_src')
dst = os.path.abspath(sys.argv[1])
if os.path.exists(dst):
    shutil.rmtree(dst)
A = os.path.join(dst, 'Assets', 'Van')


def cp(src, rel):
    p = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    shutil.copyfile(src, p)


cp(os.path.join(OUT, 'Models', 'Van.fbx'), 'Assets/Van/Models/Van.fbx')
for f in sorted(glob.glob(os.path.join(OUT, 'Assets', 'Van', 'Data', '*.json'))):
    cp(f, 'Assets/Van/Data/' + os.path.basename(f))
ATLASES = ['Body', 'Cabin', 'Gauges', 'Lens', 'Mech', 'Props', 'Seats', 'Snow', 'Trim', 'Wheel']
tex = ['T_Van_%s_BaseColor.png' % a for a in ATLASES] + ['T_Van_Gauges_Emission.png', 'T_Van_Lens_Emission.png',
                                                         'T_Van_Frost.png', 'T_Van_Snow.png', 'T_Van_Fog.png',
                                                         'T_Van_Handprints.png']
for t in tex:
    cp(os.path.join(TEX, t), 'Assets/Van/Textures/' + t)
cp(os.path.join(OUT, 'Assets', 'Van', 'Textures', 'T_Van_WipeMap.png'), 'Assets/Van/Textures/T_Van_WipeMap.png')
for f in sorted(glob.glob(os.path.join(TEX, 'Cookies', 'T_Cookie_*.png'))):
    cp(f, 'Assets/Van/Textures/Cookies/' + os.path.basename(f))
for sub in ('Scripts', 'Editor', 'Shaders'):
    for f in sorted(os.listdir(os.path.join(SRC, sub))):
        cp(os.path.join(SRC, sub, f), 'Assets/Van/%s/%s' % (sub, f))
cp(os.path.join(SRC, 'README.md'), 'Assets/Van/README.md')

# IES: outside Assets
for f in sorted(glob.glob(os.path.join(TEX, 'IES', '*.ies'))):
    cp(f, 'IES/' + os.path.basename(f))
lights = json.load(open(os.path.join(OUT, 'Assets', 'Van', 'Data', 'lights.json')))['lights']
by_ies = {}
for l in lights:
    by_ies.setdefault(l['ies'], []).append(l)
rows = []
for ies in sorted(by_ies):
    L = by_ies[ies]
    l = L[0]
    shape = ('Spot %d° / %d°, маска %s' % (l['spotOuter'], l['spotInner'], l['cookie'])) if l['unityLight'] == 'Spot' else 'Point'
    rows.append('  %-12s %-9s %-44s %s' % (ies, l['type'], shape, ', '.join(x['name'] for x in L)))
ies_txt = """IES — световые диаграммы 41 лампы УАЗа (17 типов), формат IESNA LM-63-2002.

Откуда: посчитаны из диаграмм излучения ламп (van_lights.py в пакете source/vehicles/van3/src) — это не замеры
реальных фар, а формы лучей, которые мы задали: ближний свет с горизонтальной границей слева и подъёмом 15° справа
(правостороннее движение), узкий прожектор, широкая противотуманка, прямоугольник рабочего света, плафоны и т. д.

Где используются:
  - Unity URP: IES не читает. Те же диаграммы запечены в маски света Assets/Van/Textures/Cookies/T_Cookie_*.png
    (для Spot-ламп; маска покрывает конус spotOuter, центр — ось луча, +u — вправо от лампы, +v — вверх), точечные
    лампы — без маски. Риг и меню сборки ставят маски сами. Эти файлы в проект Unity не копировать.
  - Blender (Cycles) и HDRP: IES можно подключить напрямую (ось луча — надир 0°; C0 = −Y лампы, C90 = −X,
    C180 = +Y, C270 = +X). Сила света в файле нормирована к пику; яркость в игре — intensity из lights.json.

Файл        тип       в Unity                                       лампы
""" + '\n'.join(rows) + '\n'
p = os.path.join(dst, 'IES', 'README_IES.txt')
open(p, 'w', encoding='utf-8').write(ies_txt)

# previews
for f in sorted(glob.glob(os.path.join(OUT, 'checks', 'frame', '*'))):
    cp(f, 'previews/frame/' + os.path.basename(f))
for f in ('wipe_map_view.png', 'wipe_over_frost.png'):
    cp(os.path.join(OUT, 'checks', f), 'previews/' + f)
cp(os.path.join(TEX, 'cookies_sheet.png'), 'previews/cookies_sheet.png')

# src
SCRIPTS = ['van_unity_export.py', 'van_unity_data.py', 'van_wipe_map.py', 'van_lights.py', 'van_stage_pkg.py',
           'van_tools/fbx_check.py', 'van_tools/unity_frame_check.py', 'van_tools/data_check.py']
for s in SCRIPTS:
    cp(os.path.join(HERE, s), 'src/scripts/' + s)
for f in sorted(glob.glob(os.path.join(OUT, 'reports', '*'))):
    cp(f, 'src/reports/' + os.path.basename(f))
cp(os.path.join(OUT, 'van_export_report.json'), 'src/reports/van_export_report.json')
src_txt = """Van_Unity_v1/src — как собран пакет машины для Unity

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
"""
open(os.path.join(dst, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(src_txt)

# md5 of everything
lines = []
for root, _, files in os.walk(dst):
    for f in sorted(files):
        p = os.path.join(root, f)
        rel = os.path.relpath(p, dst).replace(os.sep, '/')
        if rel == 'src/reports/package_md5.txt':
            continue
        lines.append('%s  %s' % (hashlib.md5(open(p, 'rb').read()).hexdigest(), rel))
lines.sort(key=lambda s: s[34:])
open(os.path.join(dst, 'src', 'reports', 'package_md5.txt'), 'w').write('\n'.join(lines) + '\n')
total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(dst) for f in fs)
print('[van] staged', len(lines) + 1, 'files,', total, 'bytes ->', dst)
