"""Sheets for the van v2: A exterior (less of a 'bukhanka'), B dashboard in the plane's style, C folding troop seats,
D lighting.  python3 make_sheets_van2.py <out_dir>"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'rend', 'van2')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
INFO = json.load(open(os.path.join(HERE, 'out', 'van2.json')))
FRAME = json.load(open(os.path.join(R, 'frame.json')))
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM = (22, 23, 26), (236, 236, 232), (150, 152, 156)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0
LO, HI = np.array(FRAME['lo']), np.array(FRAME['hi'])
LEN, WID, HGT = HI - LO
CX = (LO[0] + HI[0]) / 2
ZC = LO[2] + 0.38 * HGT
CREDIT = '"UAZ" 3D model by tiunov.se (Sketchfab), CC BY 4.0, modified'


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def ru(v, n=2):
    return f'{v:.{n}f}'.replace('.', ',')


def tag(im, text, xy=(10, 10), f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rectangle([x - 6, y - 4, x + w + 8, y + f.size + 8], fill=(0, 0, 0))
    d.text((x, y), text, fill=INK, font=f)


def ps1(path, scale=2):
    a = np.asarray(Image.open(path).convert('RGB'), np.float32) / 255
    H, W, _ = a.shape
    th = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    q = np.floor(np.clip(a, 0, 1) * 31 + th) / 31
    im = Image.fromarray((np.clip(q, 0, 1) * 255 + 0.5).astype(np.uint8))
    return im.resize((W * scale, H * scale), Image.NEAREST)


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


def sheet(title, sub, tiles, rows, fname, cols=2):
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
            tag(im, label)
        S.paste(im, (g + (i % cols) * (W + g), 130 + (i // cols) * (H + g)))
    y = 130 + nrow * (H + g) + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, cols * W + (cols - 1) * g - 220)):
            d.text((g + 220, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    S = S.crop((0, 0, S.width, y + 10))
    p = os.path.join(OUT, fname)
    S.save(p, quality=92)
    return p


def img(v, base=R):
    return Image.open(os.path.join(base, v + '.png')).convert('RGB')


def side_with_dims():
    im = img('side')
    d = ImageDraw.Draw(im)
    ppm = 900 / (LEN * 1.62)
    xc = CX + 0.25
    X = lambda x: int(450 + (xc - x) * ppm)                 # the left side faces the camera: the nose is on the left
    Z = lambda z: int(300 - (z - ZC) * ppm)
    col = (30, 32, 36)
    f = F(18, True)
    wb = 1.207 + 1.203
    for (x0, x1, z, t) in ((HI[0], LO[0], HGT + 0.22, f'{ru(LEN)} м'), (1.207, -1.203, -0.13, f'база {ru(wb)} м')):
        d.line([(X(x0), Z(z)), (X(x1), Z(z))], fill=col, width=2)
        for xx in (x0, x1):
            d.line([(X(xx), Z(z) - 7), (X(xx), Z(z) + 7)], fill=col, width=2)
        w = d.textlength(t, font=f)
        d.rectangle([(X(x0) + X(x1)) / 2 - w / 2 - 4, Z(z) - 24, (X(x0) + X(x1)) / 2 + w / 2 + 4, Z(z) - 4], fill=(225, 227, 230))
        d.text(((X(x0) + X(x1)) / 2 - w / 2, Z(z) - 23), t, fill=col, font=f)
    xh = LO[0] - 0.30
    d.line([(X(xh), Z(0)), (X(xh), Z(HGT))], fill=col, width=2)
    for zz in (0, HGT):
        d.line([(X(xh) - 7, Z(zz)), (X(xh) + 7, Z(zz))], fill=col, width=2)
    t = f'{ru(HGT)} м'
    w = d.textlength(t, font=f)
    d.rectangle([X(xh) + 10, Z(HGT / 2) - 12, X(xh) + 18 + w, Z(HGT / 2) + 10], fill=(225, 227, 230))
    d.text((X(xh) + 14, Z(HGT / 2) - 11), t, fill=col, font=f)
    d.text((X(HI[0] + 0.9) - 26, Z(1.86) - 26), '1,8 м', fill=col, font=f)
    return im


def atlas_tile(path, label, ppm=None, note=None):
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    k = max(1, 560 // s)
    t = a.resize((s * k, s * k), Image.NEAREST)
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(t, ((900 - t.width) // 2 - 120, (600 - t.height) // 2 + 10))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    lum = pal @ np.array([0.3, 0.59, 0.11])
    pal = pal[np.argsort(lum)]
    d = ImageDraw.Draw(canvas)
    step = max(1, len(pal) // 64)
    for i, c in enumerate(pal[::step][:64]):
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


def shapes_tile():
    """cookies (light shapes) in a row + the lens atlas base / emission"""
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    cdir = os.path.join(HERE, 'tex', 'van2', 'Cookies')
    names = [('head', 'ближний'), ('spot', 'прожектор'), ('work', 'люстра'), ('reverse', 'задний ход'),
             ('dome', 'плафон'), ('plate', 'номер')]
    x = 14
    for key, lab in names:
        im = Image.open(os.path.join(cdir, 'T_Cookie_%s.png' % key)).convert('L').resize((136, 136), Image.BILINEAR)
        canvas.paste(Image.merge('RGB', (im, im, im)), (x, 52))
        d.text((x, 194), lab, fill=INK, font=F(18))
        x += 146
    for i, (n, lab) in enumerate((('BaseColor', 'стёкла днём'), ('Emission', 'свечение'))):
        a = Image.open(os.path.join(HERE, 'tex', 'van2', 'T_Van_Lens_%s.png' % n)).convert('RGB')
        a = a.resize((272, 272), Image.NEAREST)
        canvas.paste(a, (40 + i * 430, 262))
        d.text((40 + i * 430, 540), lab, fill=INK, font=F(18))
    tag(canvas, 'форма света (cookie / IES) и атлас стёкол')
    return canvas


def crop_zoom(v, box, label=None):
    im = img(v).crop(box)
    return im.resize((900, int(900 * im.height / im.width)), Image.LANCZOS)


if __name__ == '__main__':
    tris = INFO.get('tris', 0)
    lamps = INFO.get('lamps', {})
    n_out = sum(1 for k, v in lamps.items() if v['group'] != 'int')
    n_in = sum(1 for k, v in lamps.items() if v['group'] == 'int')
    old = os.path.join(HERE, 'rend', 'final')
    a = sheet('Фургон v2 · внешний вид',
              'меньше «буханки»: новое лицо, силовой бампер, козырёк, экспедиционный багажник, окраска как у самолёта',
              [(img('q34'), 'стало: спереди'), (img('q34', old), 'было: v1'),
               (img('q34r'), 'сзади: лестница и запаска на дверях'), (img('front'), 'анфас'),
               (side_with_dims(), 'сбоку, человек 1,8 м'), (img('close'), 'крупно: панель, фары, лебёдка')],
              [('Лицо', 'вместо «хлебного» носа — чёрная панель по всей ширине: круглые фары в хромированных ободках, '
                        'поворотники под ними, решётка из шести планок в хромированной рамке; штатные фары, решётка и '
                        'стёкла под панелью удалены'),
               ('Бампер', 'силовой, с лебёдкой (барабан, мотор, клюз, красный крюк), кенгурятник из трубы и два круглых '
                          'прожектора на нём, красные буксирные крюки'),
               ('Верх', 'козырёк над лобовым стеклом с пятью оранжевыми габаритами; экспедиционный багажник на всю '
                        'крышу: люстра из четырёх фар, два оранжевых сэнд-трака, канистры, ящик, скатка брезента'),
               ('Борта и зад', 'расширители арок, отбойники вдоль бортов, ступени под кабиной и у боковой двери, брызговики, '
                               'боковые габариты; лестница на левой задней двери, запаска на кронштейне на правой; '
                               f'кузов поднят на 9 см, колёса больше на 12 %; длина {ru(LEN)} м, высота с грузом {ru(HGT)} м'),
               ('Окраска', 'как у самолёта: красный, белый пояс и белая крыша, тёмный низ; выгорание, ржавчина у арок '
                           'и порогов, сколы, грязь от колёс, соль, снег на багажнике'),
               ('Модель', f'{CREDIT}. {tris // 1000} тыс. треугольников вместе с салоном')],
              'van2_A_exterior.jpg')
    b = sheet('Фургон v2 · приборная панель',
              'своя, не от УАЗа: по образцу панели самолёта',
              [(img('dash'), 'днём, с места водителя'), (img('dash_night'), 'ночью: подсветка шкал и заливка'),
               (img('cab'), 'кабина ночью: вид с места водителя'),
               (atlas_tile(os.path.join(HERE, 'tex', 'van2', 'T_Van_Gauges_BaseColor.png'), 'атлас приборов',
                           note='шрифты самолёта, без фильтрации; карта Emission — ночная подсветка'), None)],
              [('Щиток', 'тахометр и спидометр по обе стороны рулевой колонки — ступица руля их не закрывает; топливо и '
                         'температура слева, масло и вольтметр справа; над колонкой полоса из восьми контрольных ламп; '
                         'козырёк щитка, винты по углам, как на панелях самолёта'),
               ('Центр', 'восемь тумблеров с подписями (фары, противотуманки, прожекторы, люстра, рабочий свет, салон, '
                         'печка, дворник) и ON/OFF; CB-рация 27 МГц с зелёным дисплеем; печка с вентилятором; часы и компас'),
               ('Пассажир', 'бардачок с замком, поручень, табличка «MAX 8 PERS / NO SMOKING»'),
               ('Шкалы', 'зелёные, жёлтые и красные дуги как на приборах самолёта; ночью светятся шкалы, цифры, '
                         'контрольные лампы и дисплей рации, панель подсвечена тёплым светом из-под козырька'),
               ('Стрелки', 'шесть отдельных объектов Needle_*: ось в центре шкалы, поворот вокруг нормали панели; '
                           'углы покоя и оси записаны в van2.json — в игре стрелки можно крутить')],
              'van2_B_dashboard.jpg')
    c = sheet('Фургон v2 · откидные сиденья',
              'в салоне — десантные сиденья, которые складываются к стене так же, как в самолёте',
              [(img('fold0'), 'разложено'), (img('fold50'), 'складывается'), (img('fold100'), 'сложено к стене'),
               (img('seats'), 'левый борт: три разложены, одно сложено'), (img('inside'), 'салон ночью: правые сложены'),
               (img('plan'), 'план салона (крыша срезана)')],
              [('Устройство', 'шесть мест вдоль бортов: четыре слева, два справа по сторонам боковой двери. '
                              'Брезентовая спинка на стене, сиденье — рама из алюминиевой трубы с брезентом, поясной '
                              'ремень с пряжкой, U-образная опора с резиновыми пятками, петли и кронштейны на стене'),
               ('Складывание', 'как у самолёта: сиденье поворачивается вверх к стене на 90° вокруг оси петли, опора '
                               'складывается под него на 90° в обратную сторону. Seat_XX — сиденье (ось в петле), '
                               'Seat_XX_Leg — опора, дочерний объект, Seat_XX_Fixed — неподвижная часть'),
               ('Зачем', 'сложенные сиденья освобождают проход к боковой двери и место под груз; в кабине — два '
                         'обычных кресла')],
              'van2_C_seats.jpg')
    d = sheet('Фургон v2 · фары и свет',
              'как на самолёте v13: объёмные корпуса и стёкла, у каждой лампы своя форма луча, ореолы и лучи в дымке',
              [(img('lamps_front'), 'круглые фары в хромированном ободке, прожекторы на кронштейнах'),
               (img('lamps_rear'), 'задний фонарь: корпус, три стекла с рисунком'),
               (img('roof'), 'габариты-колпачки на козырьке, люстра на кронштейнах'),
               (shapes_tile(), None),
               (img('night'), 'ночью: лучи в дымке, ореолы, отсвет фонарей'),
               (img('front_night'), 'спереди ночью: ближний свет и прожекторы'),
               (img('wall'), 'ближний свет на стене в 10 м: срез, подъём справа'),
               (img('wall_all'), 'всё вместе: ближний, прожекторы, люстра'),
               (img('night_rear'), 'сзади: габариты, задний ход, рабочая фара'),
               (img('domes'), 'салон: плафоны и красный ночник')],
              [('Корпуса', 'как у ламп самолёта v13: у каждой лампы объёмный корпус, ободок с фаской и выпуклое стекло. '
                           'Фары — круглые, 7″, в хромированном ободке с фаской, выпуклое стекло с кольцами и '
                           'рифлением; прожекторы — глубокие чаши на U-кронштейнах; '
                           'люстра и рабочая фара — банки на кронштейнах; габариты — колпачки на основании; задний '
                           'фонарь — корпус с тремя стёклами и перегородками; ночник — колпак на шестигранной бобышке'),
               ('Стёкла', 'рисунок отражателя, линз Френеля, призм и колбы — 32 px на стекло, 8 ступеней серого с '
                          'дизерингом, цвет задаёт материал. Каждое стекло — отдельный объект Lens_*: любую лампу можно '
                          'включить или мигать отдельно'),
               ('Форма луча', 'посчитана из диаграммы излучения, как на самолёте: ближний свет со срезом и подъёмом '
                              'справа на 15°, узкий луч прожекторов, широкая заливка люстры и рабочей фары, задний ход '
                              'на землю, плафоны со срезом корпуса. Из одной диаграммы — IES для Blender и Unreal и '
                              'cookie для Unity'),
               ('Цвет и сила', 'галоген 3300–3400 K у фар, 2900 K у фонарей с красным и янтарным фильтром, 2800 K в '
                               'салоне; сила в единицах URP, как у самолёта: снег в пятне фар 0,2–1'),
               ('Стекло ночью', 'светится по той же диаграмме в сторону зрителя: в луче слепит, сбоку горит слабее; '
                                'ореолы и лучи дают дымка и bloom, как в превью самолёта'),
               ('Файлы', f'IES — {len(os.listdir(os.path.join(HERE, "tex", "van2", "IES")))} типов, cookie — '
                         f'{len(os.listdir(os.path.join(HERE, "tex", "van2", "Cookies")))}, van2_lights.json — '
                         f'{len(lamps)} {plural(len(lamps), "лампа", "лампы", "ламп")} ({n_out} снаружи, {n_in} внутри): '
                         'позиция, направление, тип, группа включения, K, фильтр, сила, углы')],
              'van2_D_lights.jpg')
    for p in (a, b, c, d):
        print(p)
