"""Package forest_station 1.0 (adapted from forest_pager's pack_pager): the .blend with relative texture paths, the texture, the
json contract, lights (none) and stats, the sheet (2 x 3 of the renders, Russian captions), the renders, the source
(self-contained with the library modules it needs); the Russian reference goes to docs/gdd (STATION_CONTRACT.md).
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_station/pack_station.py
-> source/assets/forest_station/ (the FBX: station_export.py afterwards, into its fbx/)"""
import os, sys, shutil, ast, json
import bpy
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, '..', '..', 'lib'))
PK = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'source', 'assets', 'forest_station'))
SRC = ['station_kit.py', 'station_paint.py', 'station_build.py', 'station_view.py', 'station_quick.py', 'station_render.py',
       'station_check.py', 'pack_station.py', 'station_export.py']
RENDERS = ['rack', 'room', 'post', 'table', 'both', 'rack_empty', 'game']
SHEET = [('rack', 'Station_MonitorRack_3x3: 9 мониторов Kit_Monitor_CRT на Slot_1…Slot_9'),
         ('room', 'У стены Leitstand: задняя грань = Unity z 0, Slot_1 сверху слева'),
         ('post', 'Стойка-уголок 40×40: ряд пробитых отверстий, болты полок'),
         ('table', 'Station_SideTable: ObjectPC на Slot_PC (клавиатура свисает: Slot_Keyboard)'),
         ('both', 'Обе модели и фигура 1,8 м'),
         ('rack_empty', 'Стеллаж пустой: 3 полки, крышка, связи, X-раскос сзади')]
README = ('Исходники пакета forest_station 1.0: стеллаж на 9 мониторов (Station_MonitorRack_3x3) и приставной столик '
          '(Station_SideTable) для пункта охраны. Пакет — папка выше, справочник — docs/gdd/STATION_CONTRACT.md. Собран '
          'локально (скилл snow-model), класс prop (64 px/м, стойки 128 px/м).\n\n'
          '- station_kit.py — геометрия и точки Slot_*; station_paint.py — покраска атласа Props; station_view.py — '
          'мониторы и компьютер для превью (связью из ../snow_kit и ../forest_devices, в station.blend их нет).\n'
          '- Порядок (из корня репозитория): blender -b --factory-startup --python tools/snow_style/run_bpy.py -- '
          'tools/snow_style/work/forest_station/station_build.py [--draft]; потом station_check.py, station_quick.py '
          '<blend> <папка> [виды], station_render.py [виды|all] [spp], pack_station.py, station_export.py.\n')
local = {os.path.splitext(f)[0]: d for d in (HERE, LIB) for f in os.listdir(d) if f.endswith('.py')}


def closure(files):
    need, todo = set(), list(files)
    while todo:
        f = todo.pop()
        path = os.path.join(local[os.path.splitext(f)[0]], f)
        for node in ast.walk(ast.parse(open(path, encoding='utf-8').read())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for n in {n.split('.')[0] for n in names if n.split('.')[0] in local}:
                if n + '.py' not in files and n not in need:
                    need.add(n)
                    todo.append(n + '.py')
    return sorted(n + '.py' for n in need)


keep_fbx = None
if os.path.isdir(PK):
    if os.path.isdir(os.path.join(PK, 'fbx')):
        keep_fbx = os.path.join(HERE, 'out', '_fbx_keep')
        shutil.rmtree(keep_fbx, ignore_errors=True)
        shutil.move(os.path.join(PK, 'fbx'), keep_fbx)
    shutil.rmtree(PK)
os.makedirs(os.path.join(PK, 'tex'))
if keep_fbx:
    shutil.move(keep_fbx, os.path.join(PK, 'fbx'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'station.blend'))
for im in bpy.data.images:
    if im.library is not None or im.source != 'FILE' or not im.filepath:
        continue
    src = bpy.path.abspath(im.filepath)
    name = os.path.basename(src)
    assert os.path.exists(src), src
    shutil.copy2(src, os.path.join(PK, 'tex', name))
    im.filepath = '//tex/' + name
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PK, 'forest_station.blend'), relative_remap=False)
for f, g in (('station_contract.json', 'forest_station_contract.json'), ('station.json', 'forest_station.json'),
             ('station_lights.json', 'forest_station_lights.json'), ('station_checks.json', 'forest_station_checks.json')):
    shutil.copy2(os.path.join(HERE, 'out', f), os.path.join(PK, g))
c = json.load(open(os.path.join(PK, 'forest_station_contract.json'), encoding='utf-8'))
c['meta']['model'] = 'forest_station.blend'
json.dump(c, open(os.path.join(PK, 'forest_station_contract.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
os.makedirs(os.path.join(PK, 'renders'))
shots = {}
for r in RENDERS:
    p = os.path.join(HERE, 'rend', 'station', r + '.png')
    shutil.copy2(p, os.path.join(PK, 'renders', r + '.png'))
    shots[r] = Image.open(p).convert('RGB')
# the sheet: 2 x 3 of 1100 x 700, captions in Russian
info = json.load(open(os.path.join(PK, 'forest_station.json')))
try:
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 26)
    font_t = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
except OSError:
    font = font_t = ImageFont.load_default()
cw, ch, head = 1100, 700, 56
sheet = Image.new('RGB', (cw * 2, ch * 3 + head), (28, 28, 30))
dr = ImageDraw.Draw(sheet)
a = info['atlases']['Props']
tr = info['tris_by_root']
dr.text((16, 12), f'forest_station 1.0 — стеллаж {tr["Station_MonitorRack_3x3"]} тр., столик {tr["Station_SideTable"]} тр.; '
                  f'атлас Props {a["size"]} px, {a["ppm_base"]} px/м (стойки {a["ppm_posts"]}), {a["colours"]} цветов',
        fill=(230, 226, 214), font=font_t)
for i, (r, cap) in enumerate(SHEET):
    x, y = (i % 2) * cw, head + (i // 2) * ch
    sheet.paste(shots[r], (x, y))
    dr.rectangle((x, y + ch - 44, x + cw, y + ch), fill=(20, 20, 22))
    dr.text((x + 14, y + ch - 38), cap, fill=(226, 222, 210), font=font)
sheet.save(os.path.join(PK, 'forest_station_A.jpg'), quality=90)
lib_ = closure(SRC)
os.makedirs(os.path.join(PK, 'src'))
for f in SRC + lib_:
    shutil.copy2(os.path.join(local[os.path.splitext(f)[0]], f), os.path.join(PK, 'src'))
open(os.path.join(PK, 'src', 'README_SRC.txt'), 'w', encoding='utf-8').write(
    README + '- Библиотека (копии из tools/snow_style/lib): ' + ', '.join(lib_) + '.\n- Blender 5.2.3.\n')
print('packed', PK, sum(len(fs) for _, _, fs in os.walk(PK)), 'files')
