"""Sheets of the snow kit: A all models, B details, C at work (lit lamps and screens, the cabinet with the battery, the line at
dusk), D atlases.  python3 make_sheets_snowkit.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
import make_sheets_main as MSM
import snowkit_spec as S

MSM.OUT = OUT
sheet, ru, thou, F, INK, DIM, BG, wrap, fit = MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.BG, MSM.wrap, MSM.fit
R = os.path.join(HERE, 'rend', 'snow_kit')
RC = os.path.join(HERE, 'rend', 'snow_kit_cycles')
T = os.path.join(HERE, 'tex', 'snow_kit')
KC = json.load(open(os.path.join(HERE, 'out', 'snow_kit_contract.json')))
KI = json.load(open(os.path.join(HERE, 'out', 'snow_kit.json')))


def img(path, W=900, H=600):
    if not os.path.exists(path):
        return Image.new('RGB', (W, H), (40, 10, 10))
    return fit(Image.open(path).convert('RGB'), W, H)


def big_sheet(title, sub, image_path, rows, fname, W=1800):
    pic = Image.open(image_path).convert('RGB')
    if pic.width != W:
        pic = pic.resize((W, round(pic.height * W / pic.width)), Image.LANCZOS)
    g = 16
    Sh = Image.new('RGB', (W + 2 * g, 160 + pic.height + 1200), BG)
    d = ImageDraw.Draw(Sh)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sub_lines = wrap(d, sub, F(25), W)
    for j, line in enumerate(sub_lines):
        d.text((g, 84 + j * 32), line, fill=DIM, font=F(25))
    top = 130 + 32 * (len(sub_lines) - 1)
    Sh.paste(pic, (g, top))
    y = top + pic.height + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, W - 250)):
            d.text((g + 250, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    Sh = Sh.crop((0, 0, Sh.width, y + 10))
    p = os.path.join(OUT, fname)
    Sh.save(p, quality=92)
    print(p, Sh.size)


def atlas_tile(path, label, info=None, W=600, H=420):
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    side = 380
    t = a.resize((side, round(side * a.size[1] / a.size[0])), Image.NEAREST if s <= side else Image.BOX)
    canvas = Image.new('RGB', (W, H), (10, 10, 12))
    canvas.paste(t, (12, 30))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 404 + (i % 8) * 23, 40 + (i // 8) * 23
        d.rectangle([x0, y0, x0 + 20, y0 + 20], fill=tuple(int(v) for v in c))
    d.text((404, 236), f'{a.size[0]} × {a.size[1]}', fill=INK, font=F(20, True))
    if info and info.get('ppm'):
        d.text((404, 264), f'{ru(info["ppm"], 1)} px/м', fill=DIM, font=F(18))
    d.text((404, 290), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


ZRU = {'cabinet': 'шкаф', 'cabinet inside': 'шкаф внутри', 'galvanised': 'оцинковка', 'dark steel': 'тёмная сталь',
       'black plastic': 'чёрный пластик', 'grey plastic': 'серый пластик', 'camera': 'камера', 'monitor case': 'корпус монитора',
       'monitor bezel': 'рамка экрана', 'console': 'пульт', 'aluminium': 'алюминий', 'button': 'кнопка', 'phone': 'телефон',
       'pole': 'дерево опоры', 'porcelain': 'фарфор', 'transformer': 'бак трансформатора', 'copper': 'медь',
       'red cover': 'красная крышка', 'cable': 'кабель', 'handle': 'ручка', 'breakers': 'автоматы', 'concrete': 'бетон'}
items = KC['items']
tris = sum(v['tris'] for v in items.values())
by_k = {}
for kid, name, _, _ in S.ITEMS:
    by_k.setdefault(kid, []).append(name)
at = KI['atlases']['Kit']
big_sheet('Набор snow_kit — A: все модели',
          'Каждая вещь — отдельная модель со своей точкой привязки и своим префабом; один атлас набора (64 px/м — плотность '
          'предметов), панель надписей; рамка — по каждой модели отдельно (масштаб разный)',
          os.path.join(R, 'contact_fl.jpg'),
          [('Всего', f'{len(items)} {plural(len(items), "модель", "модели", "моделей")}, {thou(tris)} '
                     f'{plural(tris, "треугольник", "треугольника", "треугольников")}; K1–K12: ' +
            '; '.join(f'{k} — {len(v)}' for k, v in by_k.items())),
           ('Атлас', f'T_Kit_Kit {at["size"]} px, {ru(at["ppm"], 0)} px/м, 64 цвета; панель T_Kit_Panel 512 + свечение; экран '
                     'монитора — свои текстуры 128 × 96 (UV 0…1)'),
           ('Unity', f'{S.UNITY_ROOT}/Models/Kit_*.fbx, префаб на модель; постройки ставят экземпляры (пустышка с kit_item)')],
          'snow_kit_A.jpg')
DET = [('pole_top', 'K8: верх опоры — траверса, подкосы, три изолятора линии'),
       ('trafo', 'K8: опора с трансформатором — бак, вводы, малая траверса ввода в здание'),
       ('trafo_top', 'K8: перемычки от линии к вводам бака'),
       ('roofstand_top', 'K9: трубостойка — траверса с катушками, ввод-«гусак»'),
       ('cabinet_front', 'K5: шкаф — табличка NOTSTROM 12V, лампа «ток есть», ручка'),
       ('cabinet_open', 'K5: дверца открыта — автоматы, переключатель, полка, клеммы'),
       ('cabinet_clamps', 'K5: клеммы + и −, полка под аккумулятор'),
       ('phone_front', 'K4: телефон — диск, трубка, витой шнур'),
       ('camera_front', 'K1: камера — стекло, объектив, диод'),
       ('monitor_front', 'K2: монитор — экран отдельным объектом, ручки, диод'),
       ('console_2', 'K3: пульт на 2 кнопки — места кнопок и подписей на наклонной панели'),
       ('campole_base', 'K12: низ мачты — бетонная тумба, фланец с анкерами и косынками, люк с наклейкой')]
sheet('Набор snow_kit — B: детали', 'Рабочие виды (без освещения сцены, цвет — из атласа)',
      [(img(os.path.join(R, f'{v}.png'), 640, 480), lab) for v, lab in DET],
      [('Подвижное', 'IX_ConsoleButton (5 мм), IX_CabinetDoor (0…110°), IX_CabinetSwitch (0 NETZ / 90 BATTERIE), '
                     'IX_CabinetClamp_Pos / _Neg (0 на выводе / 0,06 снята), Phone_Receiver, Phone_Dial (0…300°), Lens_Beacon '
                     '(вращение)'),
       ('Точки', 'руки (Hand_), звуки (Audio_), места (Slot_Battery, Slot_Button_*, Slot_Label_*), крепления (Mount_Head, '
                 'Mount_Head_Pole; на мачте Mount_Side_1, Mount_Side_2, Mount_Top), камера (CAM_View), свет (LIGHT_), провода '
                 '(Wire_*; концы проводов Bare_A/B, Drop_A/B), вводы труб (Conduit_*)')],
      'snow_kit_B.jpg', cols=3, W=640, H=480)
CY = [('desk_power_off', 'без тока: экраны и лампы погашены'),
      ('desk_power_on', 'с током: экраны (картинка камеры — у Unity своя), лампы кнопок, маячок, диод камеры'),
      ('cabinet_battery', 'шкаф: аккумулятор машины на полке, клеммы надеты, переключатель на BATTERIE, лампа горит'),
      ('cabinet_wall', 'на стене: шкаф, труба K7 вверх к трубостойке K9, коробка K6, электрозамок K10'),
      ('line_dusk', 'линия: опора с трансформатором, ввод в здание на трубостойку, линия к следующей опоре (правило провиса K9)'),
      ('mast_camera', 'K12: камера на мачте (кронштейн K1 на хомутах), под ней прожектор; кабель из тумбы в трубе K7 по земле в '
                      'стену'),
      ('masts', 'K12: мачты с насадками — наблюдение (камера, прожектор), свет (фонарь), связь (антенна, «волновой канал»), '
                'оповещение (сирена, рупор)'),
      ('masts_night', 'те же мачты ночью: прожектор и фонарь горят (с током), их свет — LIGHT_Flood, LIGHT_Street')]
sheet('Набор snow_kit — C: в работе', 'Cycles; аккумулятор — заглушка его размеров (в игре — деталь Battery машины)',
      [(img(os.path.join(RC, f'{v}.png'), 900, 563), lab) for v, lab in CY],
      [('Ток', 'есть, когда аккумулятор на полке, обе клеммы на 0 и переключатель на 90° (BATTERIE): лампа шкафа, лампы '
               'постройки, экраны (M_Kit_Screen_On), лампа замка'),
       ('Провод', f'парабола между точками Wire_: провис = max({ru(S.WIRE["sag_min"], 2)}; {ru(S.WIRE["sag_k"], 4)}·L²); '
                  'ввод — чёрный кабель, линия — голый провод; моделями — Kit_Wire_Drop (10 м) и Kit_Wire_Bare (40 м): от точки '
                  'к точке, растягиваются по x'),
       ('Мачта', 'K12 Kit_Mast: сбоку Mount_Side_1 / _2 — кронштейн камеры, прожектор, рупор, «волновой канал»; сверху '
                 'Mount_Top — фонарь, штыревая антенна, сирена')],
      'snow_kit_C.jpg', cols=2, W=900, H=563)
tiles = [(atlas_tile(os.path.join(T, 'T_Kit_Kit_BaseColor.png'), 'T_Kit_Kit (атлас набора)', at), ''),
         (atlas_tile(os.path.join(T, 'T_Kit_Panel_BaseColor.png'), 'T_Kit_Panel (надписи, линзы)'), ''),
         (atlas_tile(os.path.join(T, 'T_Kit_Panel_Emission.png'), 'T_Kit_Panel_Emission (свечение)'), ''),
         (atlas_tile(os.path.join(T, 'T_Kit_Screen_On.png'), 'T_Kit_Screen_On (CAM 1, шлагбаум) / _Off'), ''),
         (atlas_tile(os.path.join(T, 'T_Kit_Screen_On_Gate.png'), 'T_Kit_Screen_On_Gate (CAM 2, ворота)'), '')]
sheet('Набор snow_kit — D: атласы', 'PSX-атлас (свет и затенение запечены, точечная фильтрация), панель надписей пиксельным '
      'шрифтом, её свечение, экран монитора: заглушки камер для превью (в Unity — картинка камеры)', tiles,
      [('Зоны', f'{len(S.ZONE_INFO)} отделок: ' + ', '.join(ZRU.get(v[0], v[0]) for v in S.ZONE_INFO.values()))],
      'snow_kit_D.jpg', W=600, H=420)
