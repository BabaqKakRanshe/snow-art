"""Sheets for the station yard: A the fuel tanks (the yard, the bund's front, the pump and its lever, the fill point, the back,
the stile side, between the tanks), B the transformer (the gate side, the gate open, the pole, the back, from above, the yard
at night), C Update 3 vs now in the game (the Update 3 game shots: through the transformer's fence, the pump by torchlight),
D the Update 3 models vs now (the same cameras), E points, colliders, the site, atlases, the panel.
python3 make_sheets_yard.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
U3P = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Previews'
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'yard')
RU3 = os.path.join(HERE, 'rend', 'yard_u3')
INFO = json.load(open(os.path.join(HERE, 'out', 'yard.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'yard_contract.json')))
TEX = os.path.join(HERE, 'tex', 'yard')
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM = (22, 23, 26), (236, 236, 232), (150, 152, 156)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


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


def tag(im, text, xy=(10, 10), f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rectangle([x - 6, y - 4, x + w + 8, y + f.size + 8], fill=(0, 0, 0))
    d.text((x, y), text, fill=INK, font=f)


def tag_wrap(im, text, f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    y = 10
    for line in wrap(d, text, f, im.width - 40):
        w = d.textlength(line, font=f)
        d.rectangle([4, y - 4, 10 + w + 8, y + f.size + 8], fill=(0, 0, 0))
        d.text((10, y), line, fill=INK, font=f)
        y += f.size + 12


def sheet(title, sub, tiles, rows, fname, cols=2, kw=250):
    W, H, g = 900, 600, 16
    nrow = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (cols * W + (cols + 1) * g, 130 + nrow * (H + g) + 960), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sub_lines = wrap(d, sub, F(25), cols * W + (cols - 1) * g)          # a long subtitle wraps instead of running off
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
    return p


def img(v, d=R):
    return Image.open(os.path.join(d, v + '.png')).convert('RGB')


def fit(im):
    if im.size == (900, 600):
        return im
    w, h = im.size
    s = max(900 / w, 600 / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    x0, y0 = (im.width - 900) // 2, (im.height - 600) // 2
    return im.crop((x0, y0, x0 + 900, y0 + 600))


def u3(f):
    return fit(Image.open(os.path.join(U3P, f)).convert('RGB'))


def legend_tile(view, entries):
    im = img(view).copy()
    d = ImageDraw.Draw(im)
    f = F(19)
    y = 560 - 28 * len(entries)
    for col, text in entries:
        d.rectangle([14, y, 32, y + 18], fill=col)
        w = d.textlength(text, font=f)
        d.rectangle([36, y - 2, 44 + w, y + 20], fill=(0, 0, 0))
        d.text((40, y - 1), text, fill=INK, font=f)
        y += 28
    return im


def atlas_tile(path, label, ppm=None, note=None):
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    t = a.resize((s * max(1, 560 // s),) * 2, Image.NEAREST) if s <= 560 else a.resize((560, 560), Image.BOX)
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(t, ((900 - t.width) // 2 - 120, (600 - t.height) // 2 + 10))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 690 + (i % 8) * 24, 60 + (i // 8) * 24
        d.rectangle([x0, y0, x0 + 21, y0 + 21], fill=tuple(int(v) for v in c))
    d.text((690, 270), f"{s} × {s} px", fill=INK, font=F(22, True))
    yy = 302
    if ppm:
        d.text((690, yy), f"{ru(ppm, 1)} px/м", fill=DIM, font=F(20))
        yy += 28
    d.text((690, yy), f"{len(pal)} цветов", fill=DIM, font=F(20))
    if note:
        for j, line in enumerate(wrap(d, note, F(18), 190)):
            d.text((690, yy + 40 + j * 24), line, fill=DIM, font=F(18))
    tag(canvas, label)
    return canvas


def props_panel_tile():
    """the small things' atlas, the panel's signs and the two alpha tiles"""
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    pr = Image.open(os.path.join(TEX, 'T_Yard_YardProps_BaseColor.png')).convert('RGB')
    canvas.paste(pr.resize((256, 256), Image.NEAREST), (14, 56))
    d.text((14, 318), 'T_Yard_YardProps', fill=INK, font=F(16, True))
    d.text((14, 340), f'{pr.size[0]} px · {ru(INFO["atlases"]["YardProps"]["ppm"], 0)} px/м', fill=DIM, font=F(15))
    for j, line in enumerate(wrap(d, 'насос, рычаг, шланг, пистолет, маховик, муфты, циферблаты, огнетушитель, замки, '
                                     'осушитель, заземление', F(15), 256)):
        d.text((14, 366 + j * 19), line, fill=DIM, font=F(15))
    pa = Image.open(os.path.join(TEX, 'T_Yard_Panel_BaseColor.png')).convert('RGB')
    canvas.paste(pa.crop((0, 0, 512, 180)).resize((580, 204), Image.NEAREST), (300, 56))
    d.text((300, 268), 'T_Yard_Panel 512: щит, знаки, шильдики, циферблаты', fill=INK, font=F(16, True))
    for k, (name, label) in enumerate((('T_Yard_ChainLink.png', 'рабица 64 × 64'), ('T_Yard_Barbed.png', 'колючка 64 × 46'))):
        c = Image.open(os.path.join(TEX, name)).convert('RGBA')
        bg = Image.new('RGBA', c.size, (46, 70, 46, 255))
        bg.alpha_composite(c)
        t = bg.convert('RGB').resize((c.width * 2, c.height * 2), Image.NEAREST)
        canvas.paste(t, (300 + k * 170, 304))
        d.text((300 + k * 170, 304 + t.height + 6), label, fill=DIM, font=F(15))
    for j, line in enumerate(wrap(d, 'таблички по правилу проекта: сначала по-немецки, под ним по-английски; надписи на '
                                     'оборудовании — по-английски; трафареты на баках — по краске в атласе Tanks', F(17), 560)):
        d.text((300, 470 + j * 24), line, fill=DIM, font=F(17))
    tag(canvas, 'мелочи, панель, альфа-плитки')
    return canvas


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    at = INFO['atlases']
    pp = INFO['ppm_parts']
    tris = INFO['tris']
    tr = thou(tris)
    moving = sum(1 for p in P_.values() if p['kind'] != 'static')
    a = sheet('Двор · баки ГСМ',
              f'обваловка и два бака на месте обновления 3, в виде генераторной; {thou(INFO["tris_by_root"]["FuelTanks"])} '
              f'треугольников, рычаг насоса — как в обновлении 3',
              [(img('yard_day'), 'двор днём: контейнер генератора, баки, трансформатор, опоры карты'),
               (img('tanks_front'), 'обваловка спереди: насос, щит, огнетушитель, переход, муфты залива; DIESEL по краске'),
               (img('pump'), 'насос: красный корпус, рычаг, пистолет в кольце, поддон с решёткой — здесь стоит канистра двора'),
               (img('pump_lever'), 'рычаг качается −60…+60° (здесь +45°), пока держат «использовать»'),
               (img('fill_point'), 'муфты залива FILL T1 / T2 с крышками на цепочках, циферблаты уровня, датчик перелива, '
                                   'сливной кран на замке'),
               (img('tanks_back'), 'сзади: бак 2 (TANK 2 · 18 000 L), лестница на бак 1, дыхательные трубы с колпаками'),
               (img('tanks_right'), 'справа: переход через стенку опускается за днищем бака 1'),
               (img('bund_inside'), 'проход между баками (укрытие), ложементы, линия всаса по полу, хвоя по углам')],
              [('Обваловка', '8,6 × 7,2 м, стенки 0,2 м по дощатой опалубке (следы досок, стяжки, потёки, мох у основания, '
                             'линия воды внутри), верх на 0,86 над землёй, пол на 0,15, приямок с решёткой, сливной кран на замке'),
               ('Баки', 'два горизонтальных, Ø 2,1 × 5,6 м, по 18 000 л, на сварных ложементах поверх бетонных опор; серо-зелёная '
                        'краска станции, выгоревшая сверху, ржавые потёки от патрубков, солярка у заливного; люк, дыхательная '
                        'труба с колпаком, заливной патрубок, проушины; трафареты DIESEL и TANK 1 / TANK 2 · 18 000 L по краске'),
               ('Насос', 'крыльчатый, на стойке, там же, где насос обновления 3: рычаг с поперечной ручкой, шланг, пистолет — '
                         'носик в точке Pump_Nozzle, под ним поддон; качающий стоит в Stand_PumpOperator'),
               ('Остальное', 'линии залива к муфтам FILL T1 / T2 снаружи, всас из бака 1 через задвижку и через стенку к '
                             'насосу, переход с перилами, лестница на бак 1, щит DIESELKRAFTSTOFF / DIESEL FUEL и RAUCHEN UND '
                             'OFFENES FEUER VERBOTEN / NO SMOKING, NO NAKED FLAMES, огнетушитель под козырьком')],
              'yard_A.jpg')
    b = sheet('Двор · трансформатор',
              f'площадка, трансформатор, забор и калитка на месте обновления 3; {thou(INFO["tris_by_root"]["Trafo"])} '
              f'треугольников, калитка — та же, что в обновлении 3',
              [(img('trafo_front'), 'со стороны калитки: рабица с колючкой, HOCHSPANNUNG — LEBENSGEFAHR, табличка запрета'),
               (img('trafo_open'), 'калитка открыта наружу (100°): трансформатор, маслоприёмник, шкаф НН'),
               (img('trafo_pole'), 'опора: изоляторы, где кончаются провода карты, предохранители, разрядники, спуски'),
               (img('trafo_back'), 'сзади: опора за забором, табличка с молнией, POLE 14'),
               (img('plan_trafo'), 'сверху: трансформатор на рельсах над щебнем, лоток кабеля к шкафу, опора'),
               (img('night'), 'двор ночью, тока нет: светит только луна')],
              [('Трансформатор', 'масляный, 250 кВА, 20 000 / 400 В: бак с радиаторами спереди и сзади, три коричневых ввода ВН, '
                                 'четыре НН, расширитель с циферблатом масла и осушителем (оранжевый силикагель), шильдик, '
                                 'подтёки масла; кабель НН в лоток к серому шкафу LV DISTRIB.'),
               ('Забор', 'рабица 2 м на оцинкованных стойках, три нити колючки, калитка IX_TrafoGate_91 с щеколдой — не заперта, '
                         'открытый замок висит на скобе; таблички по правилу проекта (сначала по-немецки)'),
               ('Опора', 'пропитанное дерево (трещины, светлее к верху), траверса с тремя штыревыми изоляторами на месте концов '
                         'проводов Forest_Wires, предохранители-разъединители, разрядники, заземление по опоре'),
               ('Атлас', f'Trafo {at["Trafo"]["size"]}: трансформатор {ru(pp["transformer"], 1)}, опора {ru(pp["pole"], 1)}, '
                         f'площадка {ru(pp["pad"], 1)} пикс/м — плотность генераторной 51,3')],
              'yard_B.jpg')
    c = sheet('Двор · было и стало в игре',
              'слева — кадры обновления 3 из игры (Unity, ночь), справа — новый двор с тех же мест (ночь, фонарик)',
              [(u3(os.path.join('U3', 'Forest_U3_TanksWide.jpg')), 'обновление 3: баки сквозь забор трансформатора'),
               (img('game_tanks_wide'), 'сейчас: оттуда же'),
               (u3(os.path.join('U3', 'Forest_U3_TanksPump.jpg')), 'обновление 3: насос под фонариком'),
               (img('night_torch'), 'сейчас: насос под фонариком (рычаг отведён)')],
              [('То же', 'места баков и трансформатора, обваловка 8,6 × 7,2 м, два бака, насос с рычагом на том же месте и с той же '
                         'осью, пистолет и место канистры, площадка 5,2 × 4,2 м, забор с калиткой, опора с траверсой'),
               ('Иначе', 'вид генераторной: бетон по опалубке, серо-зелёная краска станции с трафаретами вместо бежевых баков с '
                         'жёлтыми табличками, красный насос вместо зелёного, переход у правого края, трансформатор с '
                         'расширителем, шкафом и арматурой опоры, колючка на заборе; всё запечено в атласы PSX')],
              'yard_C.jpg', cols=2)
    tiles = []
    for v, lab in (('tanks_front', 'баки спереди'), ('tanks_back', 'баки сзади'), ('tanks_top', 'баки сверху'), ('pump', 'насос'),
                   ('trafo_front', 'трансформатор, калитка'), ('trafo_open', 'калитка открыта'), ('trafo_back', 'трансформатор сзади')):
        tiles.append((img(v, RU3), f'обновление 3: {lab}'))
        tiles.append((img(v), f'сейчас: {lab}'))
    d_ = sheet('Двор · было и стало, модель',
               'слева — модели обновления 3 (цвета условные), справа — новые, те же камеры',
               tiles,
               [('Модель', 'те же размеры и места: обваловка, баки Ø 2,1 м на опорах, насос и рычаг, площадка и забор '
                           'трансформатора, калитка, опора с траверсой; добавлены ложементы, люки, линии, переход с перилами, '
                           'лестница, муфты залива, поддон, щит, огнетушитель, расширитель, шкаф НН, арматура опоры, колючка')],
               'yard_D.jpg', cols=2)
    kinds_s = {}
    for s in S_.values():
        kinds_s[s['kind']] = kinds_s.get(s['kind'], 0) + 1
    KC = {'hand': ((255, 216, 26), 'рука'), 'item_slot': ((51, 230, 77), 'место вещи'), 'audio': ((230, 51, 230), 'звук'),
          'vfx': ((255, 115, 26), 'эффект'), 'hide': ((26, 230, 230), 'укрытие'), 'knock': ((242, 38, 38), 'стук'),
          'stand': ((153, 102, 255), 'где стоять')}
    ent = [(c_, f'{t} — {kinds_s.get(k, 0)}') for k, (c_, t) in KC.items() if kinds_s.get(k)]
    e = sheet('Двор · точки, коллайдеры, текстуры',
              f'{len(S_)} {plural(len(S_), "точка", "точки", "точек")}, {len(CON["colliders"])} '
              f'{plural(len(CON["colliders"]), "коробка-коллайдер", "коробки-коллайдера", "коробок-коллайдеров")}, атласы',
              [(legend_tile('points_tanks', ent), 'точки у баков сверху'),
               (img('points_trafo'), 'точки у трансформатора сверху'),
               (img('colliders_tanks'), 'коллайдеры баков: баки — по две коробки крестом, ступени перехода сплошные'),
               (img('colliders_trafo'), 'коллайдеры трансформатора: забор кусками, калитка (едет с ней), трансформатор, шкаф'),
               (img('site_plan'), 'сверху: баки, трансформатор, контейнер генератора, опоры, забор карты'),
               (atlas_tile(os.path.join(TEX, 'T_Yard_Tanks_BaseColor.png'), 'T_Yard_Tanks', at['Tanks']['ppm'],
                           'обваловка, баки, ложементы, линии, переход, лестница, щит; баки '
                           f'{ru(pp["tanks (shells, heads, saddles)"], 1)}, стены {ru(pp["bund walls"], 1)} пикс/м'), None),
               (atlas_tile(os.path.join(TEX, 'T_Yard_Trafo_BaseColor.png'), 'T_Yard_Trafo', at['Trafo']['ppm'],
                           'площадка, трансформатор, вводы, опора, изоляторы, шкаф, сталь забора'), None),
               (props_panel_tile(), None)],
              [('Точки', 'место канистры двора, где стоять качающему, ручка рычага, носик пистолета (струя), капля; звук — насос, '
                         'баки, переход, гул трансформатора, калитка, провода; эффект — вспышка на предохранителях; укрытия — '
                         'между баками и за трансформатором; стук — баки, трансформатор, шкаф'),
               ('Проверки', 'совпадающих граней нет; рычаг и калитка на всём ходу ничего не задевают (у рычага — касание оси); '
                            'снаружи достижимы насос, канистра, муфты, переход; в обваловке — торцы, проход между баками, '
                            'лестница и приямок (в щели 0,6 м перед баком 1 и за баком 2 не протиснуться); подъём ступеней не больше 0,30 м; калитка закрыта — внутрь '
                            'не попасть, открыта — весь пол внутри; места корней, точек пролога и начала рычага и калитки — как '
                            'в обновлении 3; канистра на месте не касается модели, до носика 0,36 м по горизонтали и 0,45 м ниже'),
               ('Unity', 'у каждого корня свой кадр (FuelTanks, Trafo): позиция в Unity (−x, z, −y), угол → −угол; места корней '
                         'на карте — в контракте (map_placement); подробности — YARD_CONTRACT.md')],
              'yard_E.jpg', cols=2)
    print(a, b, c, d_, e)
