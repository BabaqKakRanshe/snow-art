"""Sheets for the main building: A outside by day, B the ground floor, C the upper floor and the stair, D the basement and
the prologue's places, E1 / E2 Update 3's game shots vs now (the same corners), F the atlases and the panel.
python3 make_sheets_main.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
U3P = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Previews'
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'main')
INFO = json.load(open(os.path.join(HERE, 'out', 'main.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'main_contract.json')))
TEX = os.path.join(HERE, 'tex', 'main')
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM = (22, 23, 26), (236, 236, 232), (150, 152, 156)


def ru(v, n=2):
    return f'{v:.{n}f}'.replace('.', ',')


def thou(n):
    return f'{n:,}'.replace(',', ' ')


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


def tag_wrap(im, text, f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    y = 10
    for line in wrap(d, text, f, im.width - 40):
        w = d.textlength(line, font=f)
        d.rectangle([4, y - 4, 10 + w + 8, y + f.size + 8], fill=(0, 0, 0))
        d.text((10, y), line, fill=INK, font=f)
        y += f.size + 12


def fit(im, W=900, H=600):
    w, h = im.size
    s = max(W / w, H / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x0, y0, x0 + W, y0 + H))


def img(v):
    p = os.path.join(R, v + '.png')
    if not os.path.exists(p):
        return Image.new('RGB', (900, 600), (40, 10, 10))
    return fit(Image.open(p).convert('RGB'))


def u3(f):
    return fit(Image.open(os.path.join(U3P, f)).convert('RGB'))


def sheet(title, sub, tiles, rows, fname, cols=2, kw=250, W=900, H=600):
    g = 16
    nrow = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (cols * W + (cols + 1) * g, 130 + nrow * (H + g) + 1400), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sub_lines = wrap(d, sub, F(25), cols * W + (cols - 1) * g)
    for j, line in enumerate(sub_lines):
        d.text((g, 84 + j * 32), line, fill=DIM, font=F(25))
    top = 130 + 32 * (len(sub_lines) - 1)
    for i, (im, label) in enumerate(tiles):
        im = im.copy()
        if im.size != (W, H):
            canvas = Image.new('RGB', (W, H), (10, 10, 12))
            im.thumbnail((W, H), Image.LANCZOS)
            canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
            im = canvas
        if label:
            tag_wrap(im, label)
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


def atlas_tile(name, label, W=600, H=420):
    path = os.path.join(TEX, f'T_Main_{name}_BaseColor.png')
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
    info = INFO['atlases'].get(name, {})
    d.text((404, 236), f'{s} × {s}', fill=INK, font=F(20, True))
    if info.get('ppm'):
        d.text((404, 264), f'{ru(info["ppm"], 1)} px/м', fill=DIM, font=F(18))
    d.text((404, 290), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    at = INFO['atlases']
    tb = INFO['tris_by_root']
    ix = [n for n in P_ if n.startswith('IX_')]
    sheet('Главный корпус — снаружи',
          'Бетон по дощатой опалубке (доски 12 см, стяжки, потёки под парапетом и подоконниками, водоросли и брызги у '
          'цоколя), серо-зелёная краска станции на металле, гравийная крыша, лестничная башня, гараж-мастерская; день',
          [(img('axo_se'), 'с юго-востока: вход, пандус, запасный выход, мачта, вентустановка, антенна'),
           (img('axo_nw'), 'с северо-запада: гараж, башня, окна склада и умывальной'),
           (img('ext_entrance'), 'вход: площадка, козырёк с фризом, звонок, табличка, ворота и дверь гаража'),
           (img('ext_south'), 'южный фасад: ленточное окно пультовой, окна спальни и кухни с коробами ставен'),
           (img('ext_east'), 'восточный фасад: запасный выход, окна пультовой, кухни, начальника'),
           (img('ext_garage'), 'гараж: подъёмно-поворотные ворота, пандус, ввод аварийного питания'),
           (img('ext_roof'), 'крыша: гравий, парапеты с отливами, выход из башни, труба, мачта'),
           (img('ext_wall'), 'вблизи: опалубка, рамы, отлив, водосток')],
          [('Атлас', f'Ext {at["Ext"]["size"]} ({ru(at["Ext"]["ppm"], 1)} px/м — плотность генераторной), крыши — Roof '
                     f'{at["Roof"]["size"]} ({ru(at["Roof"]["ppm"], 1)} px/м), оба на объекте BaseMain'),
           ('Треугольников', f'{thou(INFO["tris"])}: BaseMain {thou(tb.get("BaseMain", 0))} (в обновлении 3 — 164 тыс.), '
                             f'BaseMain_Opening {thou(tb.get("BaseMain_Opening", 0))}'),
           ('Место', 'Forest: p (340, 16,7443, −360), поворот 8° — оба префаба, как в обновлении 3')],
          'main_A_outside.jpg')
    sheet('Главный корпус — 1-й этаж',
          'Тамбур, пультовая, коридор, склад, серверная, гараж; свет — источники обновления 3 (станция под питанием: '
          'экраны и светодиоды горят)',
          [(img('in_windfang'), 'тамбур: вешалка, сапоги, шкафчики, огнетушитель'),
           (img('in_windfang2'), 'входная дверь в нише, засов IX_MainDoorBar_311 в держателе'),
           (img('in_leitstand'), 'пультовая: пульты под ленточным окном, рабочие места, стол с картой'),
           (img('in_leitstand2'), 'пультовая от окна: картотеки, табло, доска, часы'),
           (img('in_leitstand_kpp'), '1.2 — пункт управления КПП: камеры шлагбаума и ворот, пульт SCHRANKE / TOR'),
           (img('in_flur_eg'), 'коридор: линолеум в шашку, полоса 70-х, пожарный кран'),
           (img('in_lager'), 'склад: стеллажи, ящики на поддонах'),
           (img('in_server'), 'серверная: стойки за дымчатыми дверцами, щит, терминал'),
           (img('in_garage'), 'гараж: квадроцикл, верстак, бочки, ворота изнутри')],
          [('Комнаты', 'каждая — свой объект R_<Room> со своей маской света; мебель и оборудование — в её атласе '
                       '(51,3 px/м), таблички и бумаги — панель, экраны — M_ScreenOff, светодиоды — M_LEDOff')],
          'main_B_ground_floor.jpg')
    sheet('Главный корпус — 2-й этаж и лестница',
          'Спальня, кухня и комната отдыха, коридор, умывальная, кабинет начальника, лестничная клетка',
          [(img('in_kaserne'), 'спальня: койки (зоны сна — на матрасах), стол на козлах, шкафчики'),
           (img('in_kueche'), 'кухня: кухонный ряд, холодильник, стол, диван, телевизор'),
           (img('in_kueche3'), 'кухня к окну: кресло, телевизор'),
           (img('in_flur_og'), 'коридор 2-го этажа: щит УВ-ОГ, проём в кухню'),
           (img('in_waschraum'), 'умывальная: умывальник на четыре чаши, кабинки, душ'),
           (img('in_stationsleiter'), 'кабинет начальника: стол, красный телефон, сейф, книжный шкаф'),
           (img('in_tower'), 'лестничная клетка: П-образная лестница, перила, указатели этажей')],
          [], 'main_C_upper_floor.jpg')
    sheet('Главный корпус — подвал и пролог',
          'Котельная (второй префаб BaseMain_Opening: регулятор, кран подпитки, манометр, термометр, кнопка сброса горелки, '
          'засов входной двери), коридор подвала, электрощитовая с главным выключателем; вход ночью',
          [(img('in_heizung'), 'котельная: котёл, горелка, бойлер, склад топлива'),
           (img('in_heizung2'), 'котельная от бака: регулятор у двери, коллекторы, щит'),
           (img('in_heatctl'), 'регулятор: насос, горелка, STÖRUNG, термостат, суточный таймер'),
           (img('in_burner'), 'горелка и кнопка сброса IX_BurnerReset_308'),
           (img('in_flur_ug'), 'коридор подвала: магистрали, аварийный выключатель отопления'),
           (img('in_schaltraum'), 'электрощитовая: ГРЩ, IX_MainSwitch_75, мнемосхема'),
           (img('night_entrance'), 'вход ночью: фонари обновления 3, лампа над дверью'),
           (img('cmp_base'), 'со двора ночью')],
          [('Пролог', 'S7 — главный выключатель; S8 — отопление (BaseMain_Opening); S9 — засов, ставни, ворота; S10 — сон в '
                      'спальне. Имена, оси, ходы и маски — как в обновлении 3')],
          'main_D_basement_prologue.jpg')
    pairs = [('Forest_Base.jpg', 'cmp_base', 'со двора ночью'), ('Forest_ControlRoom.jpg', 'cmp_control', 'пультовая'),
             ('Forest_Corridor.jpg', 'cmp_corridor', 'коридор 1-го этажа'), ('Forest_Kitchen.jpg', 'cmp_kitchen', 'кухня'),
             ('Forest_SwitchRoom.jpg', 'cmp_switch', 'электрощитовая'), ('U3/Forest_U3_MainDoorBar.jpg', 'cmp_doorbar', 'засов'),
             ('U3/Forest_U3_HeatPanel.jpg', 'in_heatctl', 'регулятор отопления'),
             ('U3/Forest_U3_HeatBoiler.jpg', 'cmp_boiler', 'котёл'),
             ('U3/Forest_U3_DressBarracks.jpg', 'cmp_barracks', 'спальня'),
             ('U3/Forest_U3_DressChief.jpg', 'cmp_chief', 'кабинет начальника'),
             ('U3/Forest_U3_DressWash.jpg', 'cmp_wash', 'умывальная'), ('U3/Forest_U3_DressStorage.jpg', 'cmp_storage', 'склад')]
    for part_, sl in (('E1', pairs[:6]), ('E2', pairs[6:])):
        tiles = []
        for f_, v, lab in sl:
            tiles.append((u3(f_), f'обновление 3: {lab}'))
            tiles.append((img(v), f'теперь: {lab}'))
        sheet(f'Главный корпус — обновление 3 и теперь ({part_[1]}/2)',
              'Слева — кадры игры обновления 3 (Previews), справа — перестроенный корпус с той же стороны (камера на глаз); '
              'мебель, детали и точки — на тех же местах',
              tiles, [], f'main_{part_}_u3_vs_now.jpg')
    names = ['Ext', 'Roof'] + sorted(a for a in at if a.startswith('Rm_')) + ['Parts', 'Opening']
    tiles = [(atlas_tile(n, f'T_Main_{n}'), None) for n in names if os.path.exists(os.path.join(TEX, f'T_Main_{n}_BaseColor.png'))]
    pa = Image.open(os.path.join(TEX, 'T_Main_Panel_BaseColor.png')).convert('RGB')
    pt = Image.new('RGB', (600, 420), (10, 10, 12))
    pt.paste(pa.resize((380, 380), Image.BOX), (12, 30))
    d = ImageDraw.Draw(pt)
    d.rectangle([4, 2, 230, 26], fill=(0, 0, 0))
    d.text((8, 4), 'T_Main_Panel 1024', fill=INK, font=F(18, True))
    for j, line in enumerate(wrap(d, 'таблички (сначала по-немецки, под ним по-английски), пиктограммы, планы эвакуации '
                                     'по этажам, лицевая панель регулятора, циферблаты, бумаги, календарь, линзы',
                                     F(16), 190)):
        d.text((404, 40 + j * 22), line, fill=DIM, font=F(16))
    tiles.append((pt, None))
    sheet('Главный корпус — атласы', 'По 64 цвета, AO в цвете, дизеринг 4×4, фильтр «точка»; комнаты и фасады — 51,3 '
          'px/м (генераторная), детали и светильники — 64, регулятор — 96',
          tiles, [], 'main_F_atlases.jpg', cols=3, W=600, H=420)
