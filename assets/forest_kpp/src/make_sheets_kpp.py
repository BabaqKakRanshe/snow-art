"""Sheets of the checkpoint v2: A outside in the game, B inside and the power, C the base gate, D v1 -> v2 (the Update 7 game
views), E points and atlases.  python3 make_sheets_kpp.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
import make_sheets_main as MSM

MSM.OUT = OUT
sheet, ru, thou, F, INK, DIM, BG, wrap, fit = MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.BG, MSM.wrap, MSM.fit
R = os.path.join(HERE, 'rend', 'kpp2_game')
RQ = os.path.join(HERE, 'rend', 'kpp2_final')
V1G = '/home/claude/fence/game'
WV = os.path.join(HERE, 'walls_v2')
T = os.path.join(HERE, 'tex', 'kpp')
C = json.load(open(os.path.join(HERE, 'out', 'kpp_contract.json')))
INFO = json.load(open(os.path.join(HERE, 'out', 'kpp.json')))
WD = json.load(open(os.path.join(WV, 'diff.json')))


def img(path, W=900, H=506):
    if not os.path.exists(path):
        return Image.new('RGB', (W, H), (40, 10, 10))
    return fit(Image.open(path).convert('RGB'), W, H)


def whole(path, W=900, H=506):
    """the whole picture on a dark canvas (plans)"""
    canvas = Image.new('RGB', (W, H), (245, 245, 245))
    if os.path.exists(path):
        im = Image.open(path).convert('RGB')
        im.thumbnail((W, H), Image.LANCZOS)
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    return canvas


def atlas_tile(path, label, info=None, W=600, H=420):
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    side = 380
    t = a.resize((side, side), Image.NEAREST if s <= side else Image.BOX)
    canvas = Image.new('RGB', (W, H), (10, 10, 12))
    canvas.paste(t, (12, 30))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 404 + (i % 8) * 23, 40 + (i // 8) * 23
        d.rectangle([x0, y0, x0 + 20, y0 + 20], fill=tuple(int(v) for v in c))
    d.text((404, 236), f'{s} × {s}', fill=INK, font=F(20, True))
    if info and info.get('ppm'):
        d.text((404, 264), f'{ru(info["ppm"], 1)} px/м', fill=DIM, font=F(18))
    d.text((404, 290), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


def MSM_plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


KI = C['kit_instances']
nk = len(KI)
items = {}
for v in KI.values():
    items[v['item']] = items.get(v['item'], 0) + 1
sheet('КПП v2.1 — снаружи, в игре',
      'Будка и шлагбаум на месте после ForestRelocation, забор обновления 7 (стены у шлагбаума — v2: одна линия, одна высота); '
      'Cycles, день',
      [(img(os.path.join(R, 'approach.png')), 'подъезд: шлагбаум с тумбой и маячком, крылья ПО-2'),
       (img(os.path.join(R, 'kpp_side.png')), 'тумба шлагбаума, мачта камеры с прожектором, кабели в трубах к будке'),
       (img(os.path.join(R, 'kpp_back.png')), 'сзади: шкаф с аккумулятором, труба к трубостойке, ввод от опоры с трансформатором'),
       (img(os.path.join(R, 'kpp_air.png')), 'сверху: будка, шлагбаум, опоры линии к базе')],
      [('Набор', f'{nk} {MSM_plural(nk, "экземпляр", "экземпляра", "экземпляров")} snow_kit: ' + ', '.join(f'{k.replace("Kit_", "")} × {v}' for k, v in sorted(items.items()))),
       ('Шлагбаум', 'IX_BarrierArm_82 — та же точка, ось и ход 0…80°; тумба-шкаф с мотором, маячок, стойка-упор с резиной; '
                    'старый — префаб Barrier_Manual'),
       ('Линия', 'опора с трансформатором за будкой, ввод — 4 провода Kit_Wire_Drop на трубостойку; 3 провода Kit_Wire_Bare к '
                 'опоре по дороге; дальше к базе — Unity теми же моделями')],
      'kpp_A.jpg', H=506)
sheet('КПП v2.1 — внутри, ток и камеры',
      'Мониторы и пульт на столе у окна выдачи, телефон набора на прежнем месте; ночью с током; камеры на своих мачтах и что '
      'они показывают',
      [(img(os.path.join(R, 'inside_power.png')), 'внутри, день, ток есть: два монитора, пульт SCHRANKE / TOR, телефон'),
       (img(os.path.join(R, 'night_power.png')), 'ночь, ток есть: лампы, экраны, лампы кнопок, прожектор у шлагбаума'),
       (img(os.path.join(R, 'mast_barrier.png')), 'мачта камеры шлагбаума (Kit_Mast): камера, под ней прожектор, кабель из тумбы'),
       (img(os.path.join(R, 'cam_barrier.png')), 'CAM_Barrier — так видит камера шлагбаума (правый монитор, CAM 1)'),
       (img(os.path.join(R, 'cam_barrier_night.png')), 'CAM_Barrier ночью: стрелу и дорогу освещает прожектор'),
       (img(os.path.join(R, 'cam_gate.png')), 'CAM_Gate — так видит камера ворот (левый монитор, CAM 2)')],
      [('Ток', 'аккумулятор машины на полке шкафа, клеммы IX_CabinetClamp_Pos_316 / _Neg_317 на 0, IX_CabinetSwitch_315 на '
               'BATTERIE → замок отпускает IX_BoothDoor_74, горят лампы, мониторы показывают камеры'),
       ('Кнопки', 'Btn_Schranke (IX_ConsoleButton_312) — шлагбаум, Btn_Tor (IX_ConsoleButton_313) — ворота базы; нажал — '
                  'едет само до конца'),
       ('Ключница', 'крючка Schranke нет; остальные крючки и журнал — как в v1')],
      'kpp_B.jpg', H=506)
moved = sum(1 for c in WD['changed'] if abs(c['old']['p'][0] - c['new']['p'][0]) + abs(c['old']['p'][2] - c['new']['p'][2]) > 1e-3)
sheet('Ворота базы v2.1',
      'Сплошное откатное полотно с приводом между бетонными столбами в линии забора ПО-2; привод — от опоры линии; камера ворот '
      'с прожектором — на своей мачте западнее проёма',
      [(img(os.path.join(R, 'gate_out.png')), 'снаружи: SPERRGEBIET … VIDEOÜBERWACHT / CCTV, столбы по краям, забор ровно'),
       (img(os.path.join(R, 'gate_in.png')), 'изнутри: привод у направляющих, кабель на опору линии, мачта камеры ворот'),
       (whole(os.path.join(WV, 'plan_gate.png')), 'план и высоты: было (U7, сетчатая секция) → стало'),
       (img(os.path.join(R, 'u7_gate.png')), 'тот же вид, что в рендерах обновления 7')],
      [('Полотно', 'IX_Gate_81 — то же начало, ось и ход 0…6,6 м; рельс в 0,50 м за линией стены (стаканы ПО-2 до 0,375)'),
       ('Стены', f'изменено {len(WD["changed"])} {MSM_plural(len(WD["changed"]), "запись", "записи", "записей")} u7 ({moved} '
                 f'сдвинуто в плане), добавлена {len(WD["added"])} плита; '
                 'полоса выравнивания 16,018 м, ±2 м + откос 3 м')],
      'kpp_C.jpg', H=506)
sheet('КПП — версия 1 и версия 2 в игре',
      'Те же камеры, что в рендерах обновления 7 (fence/game): слева v1 и забор U7, справа v2 и стены v2',
      [(img(os.path.join(V1G, 'kpp_driver.png')), 'v1: подъезд'), (img(os.path.join(R, 'u7_kpp_driver.png')), 'v2: подъезд'),
       (img(os.path.join(V1G, 'kpp_air.png')), 'v1: сверху'), (img(os.path.join(R, 'u7_kpp_air.png')), 'v2: сверху'),
       (img(os.path.join(V1G, 'gate.png')), 'v1: ворота базы (рабица)'), (img(os.path.join(R, 'u7_gate.png')), 'v2: ворота'),
       (whole(os.path.join(WV, 'plan_barrier.png')), 'стены у шлагбаума: высоты было → стало'),
       (whole(os.path.join(WV, 'closure_v2.png')), 'проверка: машина к базе только через шлагбаум и ворота')],
      [('Изменения', 'полный список — KPP_CONTRACT.md, раздел «Что изменилось против версии 1»')],
      'kpp_D.jpg', H=506)
at = INFO['atlases']
atl = [(atlas_tile(os.path.join(T, 'T_Kpp_Kpp_BaseColor.png'), 'T_Kpp_Kpp (будка)', at.get('Kpp')), ''),
       (atlas_tile(os.path.join(T, 'T_Kpp_KppYard_BaseColor.png'), 'T_Kpp_KppYard (шлагбаум, ворота)', at.get('KppYard')), ''),
       (atlas_tile(os.path.join(T, 'T_Kpp_KppProps_BaseColor.png'), 'T_Kpp_KppProps (мелочи)', at.get('KppProps')), ''),
       (atlas_tile(os.path.join(T, 'T_Kpp_Panel_BaseColor.png'), 'T_Kpp_Panel (таблички, бумаги)'), '')]


def sheet_plan(title, sub, plan_path, tiles, rows, fname):
    """the labelled plan at its own size on the left, the atlases 2 x 2 on the right"""
    g, Wa, Ha = 16, 600, 420
    plan = Image.open(plan_path).convert('RGB')
    Wt = g + plan.width + g + 2 * Wa + g + g
    Sh = Image.new('RGB', (Wt, 130 + max(plan.height, 2 * Ha + g) + 1200), BG)
    d = ImageDraw.Draw(Sh)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sub_lines = wrap(d, sub, F(25), Wt - 2 * g)
    for j, line in enumerate(sub_lines):
        d.text((g, 84 + j * 32), line, fill=DIM, font=F(25))
    top = 130 + 32 * (len(sub_lines) - 1)
    Sh.paste(plan, (g, top))
    for i, (im, _) in enumerate(tiles):
        Sh.paste(im, (g + plan.width + g + (i % 2) * (Wa + g), top + (i // 2) * (Ha + g)))
    y = top + max(plan.height, 2 * Ha + g) + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, Wt - 2 * g - 250)):
            d.text((g + 250, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    Sh = Sh.crop((0, 0, Sh.width, y + 10))
    p = os.path.join(OUT, fname)
    Sh.save(p, quality=92)
    print(p, Sh.size)


sheet_plan('КПП v2.1 — план и атласы', 'План пакета (ворота — как в файле, рядом с будкой; в игре они у двора базы). Атласы '
           'пересобраны (новые зоны: шкафы мотора и привода, полотно ворот); мелочи набора — в атласе snow_kit',
           os.path.join(RQ, 'plan.png'), atl,
           [('Треугольники', f'{thou(INFO["tris"])} (без экземпляров набора): ' + ', '.join(
               f'{k} {thou(v)}' for k, v in sorted(INFO['tris_by_atlas'].items()))),
            ('Точки', f'{len(C["sockets"])} точек, {len(C["colliders"])} коллайдеров, {len(C["parts"])} объектов, '
                      f'{nk} {MSM_plural(nk, "экземпляр", "экземпляра", "экземпляров")} набора')],
           'kpp_E.jpg')
