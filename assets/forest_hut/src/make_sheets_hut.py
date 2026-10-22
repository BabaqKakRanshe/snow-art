"""Sheets for the forester's hut: A outside (day, back, the prologue night, the lantern from the road, the sign, the
stand), B inside (day from the door and from the back, the oil lamp at night, the stove, the map and calendar, the plan),
C Update 3 vs now in the game (the map's Hut viewpoint and the Update 3 game shots), D the Update 3 model vs now (the same
cameras), E points, colliders, atlases, the panel.  Self-contained (the van / container sheet
helpers copied in).  python3 make_sheets_hut.py [out_dir] [old_renders_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
OLD = sys.argv[2] if len(sys.argv) > 2 else '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/hut/old'
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'hut')
INFO = json.load(open(os.path.join(HERE, 'out', 'hut.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'hut_contract.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'hut_lights.json')))['lights']
TEX = os.path.join(HERE, 'tex', 'hut')
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
    S = Image.new('RGB', (cols * W + (cols + 1) * g, 130 + nrow * (H + g) + 900), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    d.text((g, 84), sub, fill=DIM, font=F(25))
    for i, (im, label) in enumerate(tiles):
        im = im.copy()
        if im.size != (W, H):
            canvas = Image.new('RGB', (W, H), (10, 10, 12))
            im.thumbnail((W, H), Image.NEAREST)
            canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
            im = canvas
        if label:
            tag_wrap(im, label)
        S.paste(im, (g + (i % cols) * (W + g), 130 + (i // cols) * (H + g)))
    y = 130 + nrow * (H + g) + 18
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


def img(v):
    return Image.open(os.path.join(R, v + '.png')).convert('RGB')


def legend_tile(view, title, entries):
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


def fit(im):
    """900 x 630 (the Update 3 renders' size) -> 900 x 600, cropped evenly"""
    if im.size == (900, 600):
        return im
    w, h = im.size
    s = max(900 / w, 600 / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    x0, y0 = (im.width - 900) // 2, (im.height - 600) // 2
    return im.crop((x0, y0, x0 + 900, y0 + 600))


def old(v):
    return fit(Image.open(os.path.join(OLD, v + '.png')).convert('RGB'))


def panel_tile():
    a = Image.open(os.path.join(TEX, 'T_Hut_Panel_BaseColor.png')).convert('RGB')
    e = Image.open(os.path.join(TEX, 'T_Hut_Panel_Emission.png')).convert('RGB')
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(a.crop((0, 0, 360, 272)).resize((720, 544), Image.NEAREST), (14, 46))
    canvas.paste(e.crop((360, 0, 512, 72)).resize((152, 72), Image.NEAREST), (740, 60))
    d = ImageDraw.Draw(canvas)
    for j, line in enumerate(wrap(d, 'эмиссия: стекло фонаря и лампы (горят), ореол', F(17), 150)):
        d.text((740, 145 + j * 22), line, fill=DIM, font=F(17))
    tag(canvas, 'T_Hut_Panel 512: карта района, календарь, вывеска, стёкла ламп, ореол')
    return canvas


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    kinds = {}
    for p in P_.values():
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    moving = len(P_) - kinds.get('static', 0)
    at = INFO['atlases']
    tris = INFO['tris']
    pp = at['Hut']['ppm_parts']
    tr = f'{tris:,}'.replace(',', ' ')
    a = sheet('Хижина лесника · снаружи',
                 f'та же хижина на том же месте, построенная как генераторная; {moving} '
                 f'{plural(moving, "подвижная деталь или предмет", "подвижные детали или предмета", "подвижных деталей или предметов")}, '
                 f'{len(S_)} {plural(len(S_), "точка", "точки", "точек")}, {tr} '
                 f'{plural(tris, "треугольник", "треугольника", "треугольников")}',
                 [(img('ext_day'), 'днём от тропы: морёная доска с белыми наличниками, дверь открыта, окно справа, лестница на крышу'),
                  (img('ext_back'), 'сзади: поленница под левым свесом, бочка для дождевой воды, труба печки'),
                  (img('ext_night'), 'старт пролога: дверь открыта, у двери горит фонарь, внутри никого, туман'),
                  (img('ext_far'), 'фонарь между ёлками с дороги (здесь 26 м; в игре с машины видно за 92 м)'),
                  (img('sign'), 'вывеска FORSTHÜTTE / FORESTER\'S HUT у тропы и колода с топором'),
                  (img('stand'), 'засидка (Hochsitz) в 11 м: закрытая кабина с прорезями, лестница, кровля толем')],
                 [('Хижина', '2,68 × 2,40 м, комната 2,44 × 2,16, пол на 0,33 м над землёй на камнях; стены — доска с нащельником '
                             '(тёмная морилка, вытертая до серого дерева у земли, мох внизу), белые угловые доски, наличники, '
                             'ветровые доски; крыша 35° из оцинкованного профлиста с коньком и ржавыми потёками, иглы и мох'),
                  ('Снаружи', 'дверь из досок на кованых петлях с белой Z-обвязкой (открывается наружу, IX_HutDoor_1), '
                              'фонарь «летучая мышь» на кронштейне справа от двери, рога на фронтоне, труба печки с колпаком, '
                              'поленница, бочка, колода с топором, лавка, приставная лестница на крышу, камень у порога'),
                  ('Свет', 'фонарь у двери: точечный, 0,9, радиус 11 (как в обновлении 3), IES — тень от бачка под фонарём '
                           'и от колпака над ним; ореол из трёх карточек; в X01 гаснет насовсем'),
                  ('Атласы', f'хижина, вывеска и засидка — один атлас {at["Hut"]["size"]} при плотности генераторной '
                             f'(стены {ru(pp["walls outside"], 1)}, внутри '
                             f'{ru(pp["inside (ply, floor, timber, roof underside)"], 1)}, засидка {ru(pp["stand"], 1)} пикс/м; '
                             f'у генераторной 51,3), мелочи {at["HutProps"]["size"]} ({ru(at["HutProps"]["ppm"], 1)}), '
                             f'панель 512; по 64 цвета, AO в цвете, дизеринг 4×4')],
                 'hut_A.jpg')
    b = sheet('Хижина лесника · внутри',
                 'отделка генераторной: фанера, еловые стропила и затяжки под изнанкой профлиста, белое окно со ставнем; '
                 'пол дощатый',
                 [(img('int_day'), 'от двери: нары с матрасом и одеялом, карта района и календарь, печка, стол под окном, табурет'),
                  (img('int_back'), 'к двери: полки слева, место канистры под нижней полкой, вешалка с курткой, сапоги'),
                  (img('int_lamp'), 'ночью: зажжена керосиновая лампа под коньком (на старте не горит), за дверью — фонарь'),
                  (img('int_stove'), 'печка: дверца открыта (место для дров), чайник на плите, задвижка на трубе, '
                                     'оцинкованные экраны на стенах и на полу'),
                  (img('int_map'), 'карта района: дорога до станции, обсерватория обведена красным, крест в лесу; '
                                   'октябрь зачёркнут до 16-го'),
                  (img('plan'), 'план без крыши: дверь открыта, нары у задней стены, печка в углу, стол под окном')],
                 [('Внутри', 'фанера (швы листов, гвозди, грязь внизу, копоть над печкой, следы рук у двери и у вешалки), '
                             'еловые стропила, прогоны и две затяжки, изнанка профлиста, подоконник; пол — доски вдоль '
                             'хижины, натоптанная дорожка от двери, грязь у порога, зола у печки'),
                  ('Вещи', 'нары, стол с ящиком, табурет, две полки на кованых кронштейнах (банки, коробка, бутылка, '
                           'моток верёвки), вешалка с оранжевой курткой и шляпой, сапоги, кружка, свеча, чайник; '
                           'канистра, воронка, фонарик и записка — предметы игры, у них свои места (Spot_)'),
                  ('Подвижное', 'дверь, ставень с вертушкой, дверца печки, задвижка на трубе; предметы — чайник и топор; '
                                'лестницы — точки для лазания'),
                  ('Пролог', 'S2: дверь открыта, фонарь горит; канистра под полкой, воронка на нижней полке, записка и '
                             'фонарик на столе — те же места, что в обновлении 3')],
                 'hut_B.jpg')
    U3P = os.path.join(os.path.dirname(OLD), '..', 'u3', 'Assets', 'Locations', 'Forest', 'Previews')
    u3 = lambda f: fit(Image.open(os.path.join(U3P, f)).convert('RGB'))
    c = sheet('Хижина лесника · было и стало в игре',
              'слева — кадры обновления 3 из игры (Unity), справа — новая хижина; верхняя пара — один и тот же вид карты Hut',
              [(u3('Forest_Hut.jpg'), 'обновление 3: вид Hut с тропы'),
               (fit(img('game_hut')), 'сейчас: тот же вид, та же камера'),
               (u3(os.path.join('U3', 'Forest_U3_HutFront.jpg')), 'обновление 3: у двери'),
               (img('ext_night'), 'сейчас: у двери ночью'),
               (u3(os.path.join('U3', 'Forest_U3_HutInside.jpg')), 'обновление 3: внутри'),
               (img('int_day'), 'сейчас: внутри (днём, свет из двери)')],
              [('То же', 'место, размер, дверь (то же имя, ось и ход), окно справа, фонарь у двери, лавка, вывеска и засидка '
                         'на своих местах; места предметов пролога; печка в заднем правом углу, нары у задней стены, '
                         'стол под окном, полки слева'),
               ('Иначе', 'вид генераторной: доска с нащельником в тёмной морилке, белые наличники, профлист, фанера внутри, '
                         'еловые стропила; пол дощатый; стол отодвинут от печки (дверцу топки теперь можно открыть); лестница '
                         '— на правой стене, на крышу; вывеска коричневая; всё запечено в атласы PSX')],
              'hut_C.jpg', cols=2)
    tiles = []
    for ov, nv, lab in (('front', 'old_front', 'спереди'), ('back', 'old_back', 'сзади'), ('iso', 'old_iso', 'сверху'),
                        ('right', 'old_right', 'справа'), ('in_back', 'old_in_back', 'внутри, к двери')):
        tiles.append((old(ov), f'обновление 3: {lab}'))
        tiles.append((fit(img(nv)), f'сейчас: {lab}'))
    c2 = sheet('Хижина лесника · было и стало, модель',
               'слева — модель обновления 3, справа — новая, те же камеры (засидка на старых кадрах стоит не на своём месте — '
               'ошибка снимка; на карте она в 11 м)',
               tiles,
               [('Модель', 'та же коробка 2,68 × 2,40 м и та же высота пола; крыша 35° с теми же свесами; вместо '
                           'бревенчатой обвязки — доска с нащельником и белые угловые доски; поленница под левым свесом, '
                           'бочка за углом, колода с топором перед хижиной — на тех же местах')],
               'hut_D.jpg', cols=2)
    kinds_s = {}
    for s in S_.values():
        kinds_s[s['kind']] = kinds_s.get(s['kind'], 0) + 1
    KC = {'hand': ((255, 216, 26), 'рука'), 'pour': ((51, 128, 255), 'залив'), 'item_slot': ((51, 230, 77), 'места вещей'),
          'audio': ((230, 51, 230), 'звук'), 'vfx': ((255, 115, 26), 'эффект'), 'hide': ((26, 230, 230), 'укрытие'),
          'knock': ((242, 38, 38), 'стук'), 'seat': ((153, 102, 255), 'сесть'), 'climb': ((153, 230, 77), 'лестница')}
    ent = [(c_, f'{t} — {kinds_s.get(k, 0)}') for k, (c_, t) in KC.items() if kinds_s.get(k)]
    e = sheet('Хижина лесника · точки, коллайдеры, текстуры',
                 f'{len(S_)} {plural(len(S_), "точка", "точки", "точек")}, {len(CON["colliders"])} '
                 f'{plural(len(CON["colliders"]), "коробка-коллайдер", "коробки-коллайдера", "коробок-коллайдеров")}, атласы',
                 [(legend_tile('points_plan', 'точки', ent), 'точки взаимодействия сверху (крыша снята)'),
                  (img('colliders_plan'), 'коллайдеры сверху (крыша и пол не показаны)'),
                  (atlas_tile(os.path.join(TEX, 'T_Hut_Hut_BaseColor.png'), 'T_Hut_Hut', at['Hut']['ppm'],
                              'хижина целиком, вывеска и засидка: стены, крыша, фанера, пол, стропила, печка, нары, поленница, '
                              'бочка, камни; доски, жерди и толь засидки; плотность генераторной '
                              f'({ru(pp["walls outside"], 1)} пикс/м)'), None),
                  (atlas_tile(os.path.join(TEX, 'T_Hut_HutProps_BaseColor.png'), 'T_Hut_HutProps', at['HutProps']['ppm'],
                              'банки, коробка, бутылка, верёвка, куртка, сапоги, кружка, свеча, чайник, фонарь, лампа, топор, рога'), None),
                  (panel_tile(), None)],
                 [('Точки', 'места вещей пролога (канистра, воронка, фонарик, записка), топка печки; рука — дверь, ставень, '
                            'вертушка, дверца печки, задвижка, чайник, топор; залив — бочка с водой; звук — фонарь, печка, '
                            'крыша, дверь, окно; эффекты — дым из трубы, огонь в печке, мотыльки у фонаря; укрытия — за '
                            'поленницей и в засидке; сесть — лавка в засидке; лестницы — на крышу и в засидку; стук — '
                            'стены, дверь, окно, крыша'),
                  ('Коллайдеры', 'хижина — стены кусками вокруг двери и окна, пол, фронтоны, два ската крыши, печка, труба, '
                                 'мебель, полки, поленница, бочка, колода, лавка, порог, лестница; у двери и ставня — свои, '
                                 'едут с ними; засидка — пустая внутри (пол, стены, дверной проём, крыша, лавка, ноги); '
                                 'вывеска — щит и столбы'),
                  ('Unity', 'система координат префаба TowerHut: x — вправо, если смотреть на дверь, y — внутрь, z — вверх; '
                            'позиция в Unity (−x, z, −y), угол → −угол; места засидки и вывески на карте — в контракте '
                            '(map_placement); подробности — HUT_CONTRACT.md')],
                 'hut_E.jpg', cols=2)
    print(a, b, c, c2, e)
