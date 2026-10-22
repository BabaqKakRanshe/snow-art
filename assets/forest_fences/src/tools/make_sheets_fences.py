"""Sheets of the fence and road-block kit (Forest Update 7):
  A  the kit by day (the PO-2 run outside / inside / close, the wicket, a checkpoint's approach, the teeth with the abatis,
     the new chain-link)
  B  the catalogue: one picture per model with its triangles
  C  the plan: the whole (base, checkpoint, funnel), the checkpoint, the gate, the closure test
  D  in the game: the in-game forest with the U7 placements (u7_preview.py)
  E  the netting: old and new tiles, why it shimmered
  F  the atlases and the cut-outs
python3 make_sheets_fences.py <out_dir> [A,B,...]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
WHICH = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else set('ABCDEF')
os.makedirs(OUT, exist_ok=True)
FEN = '/home/claude/fence'
UAZ = '/home/claude/uaz'
R = os.path.join(FEN, 'rend')
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM = (22, 23, 26), (236, 236, 232), (150, 152, 156)
REP = json.load(open(os.path.join(UAZ, 'out/forest_update7/fbx/u7_export_report.json')))
KIT = json.load(open(os.path.join(UAZ, 'out/fences.json')))
U7 = json.load(open(os.path.join(UAZ, 'out/forest_update7/u7_layout.json')))


def pl(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and not 12 <= n % 100 <= 14:
        return few
    return many


def thou(n):
    return f'{n:,}'.replace(',', ' ')


def ru(v, n=1):
    return f'{v:.{n}f}'.replace('.', ',')


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


def tag(im, text, f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    y = 10
    for line in wrap(d, text, f, im.width - 40):
        w = d.textlength(line, font=f)
        d.rectangle([4, y - 4, 10 + w + 8, y + f.size + 8], fill=(0, 0, 0))
        d.text((10, y), line, fill=INK, font=f)
        y += f.size + 12


def fit(im, W, H, crop=True):
    w, h = im.size
    s = max(W / w, H / h) if crop else min(W / w, H / h)
    im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    if crop:
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        return im.crop((x0, y0, x0 + W, y0 + H))
    c = Image.new('RGB', (W, H), (10, 10, 12))
    c.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    return c


def load(p, W, H, crop=True):
    if not os.path.exists(p):
        return Image.new('RGB', (W, H), (40, 10, 10))
    return fit(Image.open(p).convert('RGB'), W, H, crop)


def sheet(title, sub, tiles, rows, fname, cols=2, kw=260, W=900, H=600):
    g = 16
    nrow = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (cols * W + (cols + 1) * g, 160 + nrow * (H + g) + 1600), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sl = wrap(d, sub, F(25), cols * W + (cols - 1) * g)
    for j, line in enumerate(sl):
        d.text((g, 84 + j * 32), line, fill=DIM, font=F(25))
    top = 130 + 32 * (len(sl) - 1)
    for i, (im, label) in enumerate(tiles):
        im = im.copy()
        if label:
            tag(im, label, F(22 if W >= 800 else 19))
        S.paste(im, (g + (i % cols) * (W + g), top + (i // cols) * (H + g)))
    y = top + nrow * (H + g) + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, cols * W + (cols - 1) * g - kw)):
            d.text((g + kw, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    S = S.crop((0, 0, S.width, y + 10))
    p = os.path.join(OUT, fname)
    S.save(p, quality=92)
    print(p, S.size)
    return p


T = lambda m: REP[m]['tris']
NAMES = {'ConcreteFence': 'ПО-2, серая', 'ConcreteFence_b': 'ПО-2, темнее (мох, потёки)', 'ConcreteFence_Broken': 'ПО-2, сбит угол',
         'ConcreteFence_Sign': 'ПО-2 с табличкой', 'ConcreteFence_Plain': 'ПО-2 без колючки', 'ConcreteFence_Socket': 'стакан с кронштейном',
         'ConcreteFence_Wicket': 'калитка', 'ChainFence': 'рабица, 3 м', 'ChainFence_Torn': 'рабица с прорехой',
         'WireCoil': 'спираль колючей ленты', 'RoadBlock_FBS': 'блок ФБС', 'RoadBlock_Jersey': 'отбойник',
         'RoadBlock_Jersey_Striped': 'отбойник красно-белый', 'RoadBlock_Cube': 'куб 1 м', 'TankTooth': 'надолб',
         'TankTooth_b': 'надолб со сколом', 'Hedgehog': 'ёж', 'WireBarricade': 'рогатка', 'Abatis': 'завал: две ели',
         'Abatis_b': 'завал: одна ель', 'Sign_Halt': 'щит HALT', 'Sign_NoEntry': 'въезд запрещён'}
ORDER = list(NAMES)
cnt = {}
for r in U7['records']:
    cnt[r['m']] = cnt.get(r['m'], 0) + 1
atl = KIT['atlases']

if 'A' in WHICH:
    tiles = [(load(os.path.join(R, 'po2_out.png'), 900, 600), 'Забор ПО-2 снаружи: рельеф из ромбов, Y-кронштейны с колючкой, табличка SPERRGEBIET, плита со сколом, калитка'),
             (load(os.path.join(R, 'po2_in.png'), 900, 600), 'Изнутри: гладкая сторона, стаканы ФО-2 под каждым стыком, калитка с сетчатой дверью'),
             (load(os.path.join(R, 'po2_detail.png'), 900, 600), 'Вблизи: колючка в два провода на кронштейнах, табличка по-немецки и по-английски'),
             (load(os.path.join(R, 'po2_wicket.png'), 900, 600), 'Калитка: полплиты, рама, дверь открыта (проходит человек, машина — нет)'),
             (load(os.path.join(R, 'kpp_driver.png'), 900, 600), 'Подъезд к КПП глазами водителя: щит HALT, змейка из отбойников, шлагбаум, крылья ПО-2, спирали и ежи'),
             (load(os.path.join(R, 'kpp.png'), 900, 600), 'КПП сверху: крылья от столба и от упора шлагбаума, ФБС в два ряда, кубы, спирали, ежи, рогатка'),
             (load(os.path.join(R, 'teeth.png'), 900, 600), 'Линия надолбов с завалом из поваленных елей'),
             (load(os.path.join(R, 'teeth_top.png'), 900, 600), 'Завал сверху: ели валетом, ветки заточены и развёрнуты наружу, колючка между ними'),
             (load(os.path.join(R, 'chain.png'), 900, 600), 'Новая рабица: секции по 3 м, одна с прорехой; перед ними — спираль колючей ленты'),
             (load(os.path.join(R, 'chain_close.png'), 900, 600), 'Сетка вблизи: ячейка 12,5 см, провод 2 пикселя, неровное плетение — без муара')]
    rows = [('Модели', '22: забор ПО-2 (7 вариантов), рабица (2), спираль, блоки (4), надолбы (2), ёж, рогатка, завалы (2), щит HALT, знак'),
            ('Треугольников', f'плита ПО-2 {T("ConcreteFence")}, со сколом {T("ConcreteFence_Broken")}, с табличкой {T("ConcreteFence_Sign")}, '
                              f'калитка {T("ConcreteFence_Wicket")}; надолб {T("TankTooth")}; отбойник {T("RoadBlock_Jersey")}; ФБС {T("RoadBlock_FBS")}; '
                              f'спираль {T("WireCoil")}; завалы {thou(T("Abatis"))} и {T("Abatis_b")}; щит HALT {T("Sign_Halt")}'),
            ('Атласы', f'бетон {atl["Concrete"]["size"]}² ({ru(atl["Concrete"]["ppm"])} пикс/м), реквизит {atl["Props"]["size"]}² '
                       f'({ru(atl["Props"]["ppm"])} пикс/м); 64 цвета, дизеринг Байера, фильтр «точка»; таблички — отдельная панель'),
            ('Вырезы', 'рабица, колючка, лента — по альфе 0,5, плитка 0,5 м; материалы односторонние, каждая грань сетки — две грани спина к спине в 2,4 мм')]
    sheet('Заборы и заграждения — комплект', 'Обновление 7 карты Forest: бетонный забор ПО-2, блоки и знаки КПП, '
          'надолбы и завалы, новая сетка-рабица. Рендеры Cycles, день, модели как в пакете (атласы PSX, фильтр «точка»).',
          tiles, rows, 'fences_A_kit.jpg')

if 'B' in WHICH:
    tiles = []
    for m in ORDER:
        lab = f'{m} — {NAMES[m]} · {thou(T(m))} тр.' + (f' · {cnt[m]} {pl(cnt[m], "место", "места", "мест")}' if m in cnt else ' · не на карте')
        tiles.append((load(os.path.join(R, 'm_' + m + '.png'), 600, 400, crop=False), lab))
    nrec, ntri = len(U7["records"]), sum(REP[r["m"]]["tris"] for r in U7["records"])
    rows = [('Всего', f'22 модели; на карте {nrec} {pl(nrec, "место", "места", "мест")}, {thou(ntri)} '
                      f'{pl(ntri, "треугольник", "треугольника", "треугольников")} '
                      f'(было 213 секций сетки по 60 = {thou(213 * 60)})'),
            ('Кадр', 'x — вдоль, наружу (рельеф, таблички, шипы) — −y Blender = +z префаба Unity; начало — на земле посередине; '
                     'у плиты свой стакан на +x-конце, первый стакан пролёта — отдельная модель')]
    sheet('Заборы и заграждения — каталог', 'Каждая модель отдельно: имя префаба, что это, треугольники, сколько мест на карте.',
          tiles, rows, 'fences_B_models.jpg', cols=3, W=600, H=400, kw=200)

if 'C' in WHICH:
    P = os.path.join(FEN, 'plan')
    ne, nw = U7['lines']['teeth_post_NE'], U7['lines']['teeth_rest_NW']
    tiles = [(load(os.path.join(P, 'all.png'), 900, 1100, crop=False), 'Вся расстановка (кадр игры): база, КПП, линии надолбов к углам базы; кости великана, крестики — убранные деревья'),
             (load(os.path.join(P, 'closure.png'), 900, 1100, crop=False), 'Проверка: куда доедет фургон снаружи при закрытых шлагбауме и воротах (зелёное — доступно, оранжевое — закрыто)'),
             (load(os.path.join(P, 'kpp.png'), 900, 1100, crop=False), 'КПП: крылья, змейка на подъезде, щит HALT, спирали и ежи, начала линий надолбов'),
             (load(os.path.join(P, 'gate.png'), 900, 1100, crop=False), 'Ворота базы и северо-западный угол: пролёты до рамы ворот, линия надолбов подходит к углу')]
    per = [r for r in U7['records'] if r['group'] == 'perimeter']
    n_pan = sum(1 for r in per if r['m'] != 'ConcreteFence_Socket')
    n_sock = sum(1 for r in per if r['m'] == 'ConcreteFence_Socket')
    gap = max(max(v['max_gap'], *v['end_gaps']) for v in U7['lines'].values())
    rows = [('Периметр', f'{n_pan} {pl(n_pan, "плита", "плиты", "плит")} ПО-2 (одна из них — калитка) и {n_sock} '
                         f'{pl(n_sock, "стакан", "стакана", "стаканов")} начала пролёта по линиям прежнего сетчатого забора '
                         '(как их рисует план двора); калитка у люка шахты; дыры у ворот нет'),
            ('КПП', '2 крыла по 30 м; ФБС, кубы, 2 пары отбойников змейкой (12 и 24 м), щит HALT, знак, спирали, ежи, рогатки'),
            ('Воронка', f'надолбы к северо-восточному углу — {ru(ne["length"], 0)} м ({ne["pieces"]} '
                        f'{pl(ne["pieces"], "предмет", "предмета", "предметов")}, из них {ne["abatis"]} '
                        f'{pl(ne["abatis"], "завал", "завала", "завалов")}), к северо-западному — {ru(nw["length"], 0)} м '
                        f'({nw["pieces"]} {pl(nw["pieces"], "предмет", "предмета", "предметов")}, из них {nw["abatis"]} '
                        f'{pl(nw["abatis"], "завал", "завала", "завалов")}); шаг 2,05 м, просвет на высоте кузова ≤ {ru(gap, 2)} м'),
            ('Проверка', 'фургон (круг 1,94 м, кузов 1,98 м): шлагбаум закрыт — ни в воронку, ни на базу; открыт — к воротам; '
                         'ворота открыты — во двор. Человек: между надолбами — да, на базу — через калитку')]
    sheet('Заборы и заграждения — расстановка', 'План в координатах Unity (x — восток, z — север), кадр игры: после плана двора и переноса КПП.',
          tiles, rows, 'fences_C_plan.jpg', W=900, H=1100)

if 'D' in WHICH:
    G = os.path.join(FEN, 'game')
    caps = {'kpp_driver': 'КПП с подъезда, глазами водителя', 'kpp_air': 'КПП сверху: крылья, змейка, спирали, начала линий надолбов',
            'kpp_inside': 'КПП изнутри воронки: будка, шлагбаум, крылья', 'funnel_line': 'Линия надолбов в лесу (вырубленная полоса)',
            'funnel_out': 'Линия снаружи воронки: завал кроной наружу', 'gate': 'Ворота базы снаружи: ПО-2 до рамы ворот',
            'corner_NW': 'Северо-западный угол: линия надолбов упирается в забор', 'wicket': 'Калитка в южной стороне, у люка шахты',
            'overview': 'Сверху: две линии надолбов идут через лес к углам базы (КПП — левее кадра)'}
    tiles = [(load(os.path.join(G, k + '.png'), 900, 506), v) for k, v in caps.items() if os.path.exists(os.path.join(G, k + '.png'))]
    sheet('Заборы и заграждения — на карте', 'Карта как в игре (обновления 3–6, план двора и перенос КПП), сетчатый забор '
          'базы убран, деревья на линиях убраны, новые предметы — по данным обновления 7. Cycles, день, без тумана.',
          tiles, [], 'fences_D_game.jpg', W=900, H=506)

if 'E' in WHICH:
    old = Image.open(os.path.join(UAZ, 'tex/base/T_Base_ChainLink.png')).convert('RGBA')
    new = Image.open(os.path.join(UAZ, 'tex/fence/T_Fence_ChainLink.png')).convert('RGBA')

    def on_bg(t, W, H, k):
        bg = Image.new('RGBA', (W, H), (70, 78, 62, 255))
        nx, ny = -(-W // (t.width * k)), -(-H // (t.height * k))
        tt = Image.new('RGBA', (t.width * nx, t.height * ny))
        for i in range(nx):
            for j in range(ny):
                tt.paste(t, (i * t.width, j * t.height))
        tt = tt.resize((tt.width * k, tt.height * k), Image.NEAREST)
        bg.alpha_composite(tt.crop((0, 0, min(W, tt.width), min(H, tt.height))))
        return bg.convert('RGB')

    tiles = [(on_bg(old, 900, 600, 3), 'Было: ячейка 8 пикселей (6,25 см), провод 1 пиксель, решётка ровная — с 5–10 м даёт муар'),
             (on_bg(new, 900, 600, 3), 'Стало: ячейка 16 пикселей (12,5 см), провод 2 пикселя, узлы и неровное плетение'),
             (load(os.path.join(R, 'chain_close.png'), 900, 600), 'Новая сетка на секции вблизи'),
             (load(os.path.join(R, 'chain.png'), 900, 600), 'Новая сетка с 10 м')]
    rows = [('Почему рябило', 'сетка и проволока — две грани спина к спине (у базы и ретранслятора — в одной плоскости), а '
                              'материал двусторонний: каждая грань видна с обеих сторон, грани дерутся за глубину и мерцают при '
                              'каждом шаге; провод в 1 пиксель при мелкой ячейке — муар'),
            ('Что сделано', 'материалы сетки и проволоки — односторонние (каждая грань видна только со своей стороны); новая '
                            'текстура с той же раскладкой — модели не меняются: ворота базы, трансформатор, ретранслятор, ворота '
                            'зоны, старый забор; новые модели — те же правила'),
            ('В Unity', 'мип-карты с сохранением покрытия (Preserve Coverage) при пороге 0,5 = порог материала — сетка не тает '
                        'вдали; фильтр «точка», без сжатия')]
    sheet('Сетка-рабица: что было и что стало', 'Текстура 64 × 64 = 0,5 м, вырез по альфе 0,5; показано плиткой, увеличение ×3 (1 пиксель текстуры = 3 пикселя листа).',
          tiles, rows, 'fences_E_netting.jpg')

if 'F' in WHICH:
    def atlas(path, label, W=600, H=420):
        a = Image.open(path).convert('RGBA')
        side = 380
        t = a.resize((side, side), Image.NEAREST if a.size[0] <= side else Image.BOX) if a.size[0] == a.size[1] else \
            a.resize((side, round(side * a.size[1] / a.size[0])), Image.NEAREST)
        c = Image.new('RGBA', (W, H), (10, 10, 12, 255))
        chk = Image.new('RGBA', t.size, (60, 64, 58, 255))
        chk.alpha_composite(t)
        c.paste(chk, (12, 30))
        d = ImageDraw.Draw(c)
        d.text((12, 4), label, fill=INK, font=F(19))
        d.text((404, 40), f'{a.size[0]} × {a.size[1]}', fill=DIM, font=F(19))
        rgb = np.asarray(a.convert('RGB')).reshape(-1, 3)
        al = np.asarray(a)[..., 3].reshape(-1)
        pal = np.unique(rgb[al > 127], axis=0)
        d.text((404, 66), f'{len(pal)} {pl(len(pal), "цвет", "цвета", "цветов")}', fill=DIM, font=F(19))
        pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))][:64]
        for k, col in enumerate(pal):
            x, y = 404 + (k % 8) * 22, 100 + (k // 8) * 22
            d.rectangle([x, y, x + 18, y + 18], fill=tuple(int(v) for v in col) + (255,))
        return c.convert('RGB')

    TX = os.path.join(UAZ, 'tex/fence')
    tiles = [(atlas(os.path.join(TX, 'T_Fence_Concrete_BaseColor.png'), 'T_Fence_Concrete_A_px — бетон'), None),
             (atlas(os.path.join(TX, 'T_Fence_Props_BaseColor.png'), 'T_Fence_Props_A_px — реквизит'), None),
             (atlas(os.path.join(TX, 'T_Fence_Panel_BaseColor.png'), 'T_Fence_Panel_A_px — таблички'), None),
             (atlas(os.path.join(TX, 'T_Fence_ChainLink.png'), 'T_Fence_ChainLink_A_px — рабица'), None),
             (atlas(os.path.join(TX, 'T_Fence_Barbed.png'), 'T_Fence_Barbed_A_px — колючка ПО-2'), None),
             (atlas(os.path.join(TX, 'T_Fence_ChainBarbed.png'), 'T_Fence_ChainBarbed_A_px — колючка рабицы'), None),
             (atlas(os.path.join(TX, 'T_Fence_Razor.png'), 'T_Fence_Razor_A_px — лента спирали'), None),
             (atlas(os.path.join(TX, 'replacements', 'T_Kpp_Barbed_A_px.png'), 'T_Kpp/Yard_Barbed_A_px — замена'), None),
             (atlas(os.path.join(TX, 'replacements', 'T_Base_Rust_A_px.png'), 'T_Base_Rust_A_px — замена'), None)]
    rows = [('Атласы', f'бетон {atl["Concrete"]["size"]}² — {ru(atl["Concrete"]["ppm"])} пикс/м, заполнение {ru(atl["Concrete"]["uv_fill"] * 100, 0)} %; '
                       f'реквизит {atl["Props"]["size"]}² — {ru(atl["Props"]["ppm"])} пикс/м, заполнение {ru(atl["Props"]["uv_fill"] * 100, 0)} %; по 64 цвета'),
            ('Замены', 'на месте, T_Base_ChainLink, T_Base_Barbed, T_Base_Rust, T_Kpp_ChainLink, T_Kpp_Barbed, T_Yard_ChainLink, '
                                  'T_Yard_Barbed, T_Road_ChainLink, T_Road_Barbed — те же имена, GUID, размеры и места проволоки')]
    sheet('Заборы и заграждения — атласы и вырезы', 'Как в пакете (фон под вырезами — серо-зелёный, чтобы видеть альфу).',
          tiles, rows, 'fences_F_atlases.jpg', cols=3, W=600, H=420, kw=260)
