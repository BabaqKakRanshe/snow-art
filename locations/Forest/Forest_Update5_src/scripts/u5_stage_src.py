"""Forest_Update5_src: how Forest_Update5.unitypackage was made (scripts and check reports), for
source/locations/Forest/Forest_Update5_src on the PC.
python3 u5_stage_src.py <u5_out_dir> <fbx_dir>"""
import os, sys, shutil, json

HERE = os.path.dirname(os.path.abspath(__file__))
out_dir, fbx_dir = sys.argv[1:3]
dst = os.path.join(out_dir, 'src')
if os.path.exists(dst):
    shutil.rmtree(dst)
os.makedirs(os.path.join(dst, 'scripts'))
os.makedirs(os.path.join(dst, 'reports'))

SCRIPTS = ['u5_export.py', 'u5_build.py', 'u5_verify_fbx.py', 'u5_check_pkg.py', 'u5_stage_src.py', 'make_u5_doc.py',
           'u5_readme_section.md', 'u5_deliver_stage.py', 'u4_export.py', 'u4_build.py', 'base_spec.py', 'far_spec.py',
           'base_u3_data.json', 'far_u3_data.json', 'base_ground.json', 'far_ground.json', 'far_lookout_stairs.json']
for s in SCRIPTS:
    shutil.copyfile(os.path.join(HERE, s), os.path.join(dst, 'scripts', s))
REPORTS = [(out_dir, 'Forest_Update5_manifest.json'), (out_dir, 'README_u5_section.md'),
           (fbx_dir, 'u5_export_report.json'), (fbx_dir, 'u5_verify_fbx.json'), (fbx_dir, 'u5_verify_fbx.log'),
           (out_dir, 'u5_check_pkg.log')]
for d, f in REPORTS:
    p = os.path.join(d, f)
    if os.path.exists(p):
        shutil.copyfile(p, os.path.join(dst, 'reports', f))
    else:
        print('missing', p)

man = json.load(open(os.path.join(out_dir, 'Forest_Update5_manifest.json')))
txt = f"""Forest_Update5_src — как собран Forest_Update5.unitypackage

Пакет обновления 5 карты Forest: 25 моделей базы и дальних точек в стиле генераторной, с именами и GUID обновления 3
(или проекта — для LogPile, FenceChain, OldFence, OldFence_b, OldFence_c, Forest_Wires). Ставится поверх обновления 4.
Задание для Unity — docs/gdd/FOREST_U5_UNITY.md, стартовый промпт — docs/start/START_FOREST_U5.txt.

Откуда модели: пакеты source/assets/forest_base (base.blend) и source/assets/forest_far (far.blend), справочники
docs/gdd/BASE_CONTRACT.md и docs/gdd/FAR_CONTRACT.md. Скрипты моделей, покраски и проверок — в src/ этих пакетов.

Порядок сборки (Blender 5.0 как модуль bpy для Python 3.11, запускать из папки со скриптами пакетов и этими):
  1. python3 -I u5_export.py -- <fbx_dir>
     одна FBX на префаб, формат обновления 3 (FBX 7400, Y вверх, перед +Z, UnitScaleFactor 100, корень в начале
     координат без поворота, у детей только сдвиги); отчёт u5_export_report.json
  2. python3 -I u5_verify_fbx.py -- <fbx_dir>
     каждую FBX читает обратно импортёр Blender: объекты, границы (1 мм), точки поворота, треугольники, материалы,
     настройки осей файла; отчёт u5_verify_fbx.json
  3. python3 u5_build.py <fbx_dir> <out/forest_update4> <u3raw> <out_dir>
     пакет: Models (25 FBX), Textures (атласы T_Base_… и T_Far_…, все *_px), Data (Forest_Layout.json и
     Forest_Materials.json обновления 4 + блок u5 и новые материалы в конце), README.md (обновления 4 + раздел
     «Обновление 5»); опись Forest_Update5_manifest.json, точки превью, в кадр которых попадают новые модели
  4. python3 -I u5_check_pkg.py <пакет> <Forest_Update4.unitypackage> <распакованное обновление 3> <u3raw> <project_textures.txt>
     независимая проверка пакета: записи, GUID, данные против обновлений 3 и 4, материалы и текстуры, узлы FBX для
     interactables, prefabLights, prefabGlows, lighting.assign; отчёт u5_check_pkg.log
  5. python3 make_u5_doc.py <out_dir> <fbx_dir>  ->  FOREST_U5_UNITY.md и START_FOREST_U5.txt

scripts/  скрипты сборки пакета (u5_*, make_u5_doc.py) и то, что они берут из обновления 4 (u4_export.py, u4_build.py) и
          из пакетов (base_spec.py, far_spec.py и их данные: base_u3_data.json, far_u3_data.json — данные обновления 3
          этих моделей, base_ground.json, far_ground.json — рельеф под ними, far_lookout_stairs.json — ступени вышки);
          u5_deliver_stage.py раскладывает всё обновление 5 по папкам проекта для доставки
reports/  опись пакета (Forest_Update5_manifest.json: пути, GUID, md5, откуда GUID, точки превью), отчёты экспорта и
          проверок, раздел README

Пакет: {man['package']}, {man['entries']} записей, {man['bytes']:,} байт.
"""
txt = txt.replace(f"{man['bytes']:,}", f"{man['bytes']:,}".replace(',', ' '))
open(os.path.join(dst, 'README_SRC.txt'), 'w', encoding='utf-8', newline='\r\n').write(txt)
print('[u5] src staged:', sum(len(f) for _, _, f in os.walk(dst)), 'files ->', dst)
