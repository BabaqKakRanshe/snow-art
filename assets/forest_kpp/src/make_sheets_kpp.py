"""Sheets for the checkpoint: A outside (from the road by day and at night, the booth, the back, the walkway side, the power
on, the barrier, the gate), B inside (from the door, toward the door, the key cabinet, the road-side desk, at night, the plan),
C Update 3 vs now in the game (the map's KPP viewpoint and the Update 3 game shots), D the Update 3 model vs now (the same
cameras), E points, colliders, the moving parts, the site, atlases, the panel.  Self-contained (the hut sheet helpers).
python3 make_sheets_kpp.py [out_dir] [old_renders_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
OLD = sys.argv[2] if len(sys.argv) > 2 else '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/kpp/old'
U3P = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Previews'
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'kpp')
INFO = json.load(open(os.path.join(HERE, 'out', 'kpp.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'kpp_contract.json')))
TEX = os.path.join(HERE, 'tex', 'kpp')
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
            im.thumbnail((W, H), Image.LANCZOS)
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


def atlas_pair_tile(items, label):
    """two atlases side by side: items = [(path, name, ppm, note), ...]"""
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    for i, (path, name, ppm, note) in enumerate(items):
        a = Image.open(path).convert('RGB')
        s = a.size[0]
        t = a.resize((384, 384), Image.NEAREST if 384 % s == 0 else Image.BOX)
        x0 = 30 + i * 440
        canvas.paste(t, (x0, 50))
        ncol = len(np.unique(np.asarray(a).reshape(-1, 3), axis=0))
        d.text((x0, 442), name, fill=INK, font=F(18, True))
        d.text((x0, 466), f'{s} × {s} px · {ru(ppm, 1)} px/м · {ncol} цветов', fill=DIM, font=F(16))
        for j, line in enumerate(wrap(d, note, F(16), 384)):
            d.text((x0, 492 + j * 21), line, fill=DIM, font=F(16))
    tag(canvas, label)
    return canvas


def fit(im):
    """any size -> 900 x 600, cropped evenly"""
    if im.size == (900, 600):
        return im
    w, h = im.size
    s = max(900 / w, 600 / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    x0, y0 = (im.width - 900) // 2, (im.height - 600) // 2
    return im.crop((x0, y0, x0 + 900, y0 + 600))


def old(v):
    return fit(Image.open(os.path.join(OLD, v + '.png')).convert('RGB'))


def u3(f):
    return fit(Image.open(os.path.join(U3P, f)).convert('RGB'))


def panel_tile():
    a = Image.open(os.path.join(TEX, 'T_Kpp_Panel_BaseColor.png')).convert('RGB')
    e = Image.open(os.path.join(TEX, 'T_Kpp_Panel_Emission.png')).convert('RGB')
    c = Image.open(os.path.join(TEX, 'T_Kpp_ChainLink.png')).convert('RGBA')
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(a.crop((0, 0, 488, 248)).resize((732, 372), Image.NEAREST), (10, 46))
    canvas.paste(e.crop((392, 144, 456, 192)).resize((128, 96), Image.NEAREST), (752, 60))
    canvas.paste(e.crop((0, 256, 128, 320)).resize((128, 64), Image.NEAREST), (752, 170))
    bg = Image.new('RGBA', c.size, (46, 70, 46, 255))
    bg.alpha_composite(c)
    canvas.paste(bg.convert('RGB').resize((128, 128), Image.NEAREST), (752, 250))
    bw = Image.open(os.path.join(TEX, 'T_Kpp_Barbed.png')).convert('RGBA')
    bg = Image.new('RGBA', bw.size, (46, 70, 46, 255))
    bg.alpha_composite(bw)
    canvas.paste(bg.convert('RGB').resize((bw.width * 2, bw.height * 2), Image.NEAREST), (752, 388))
    d = ImageDraw.Draw(canvas)
    for j, line in enumerate(wrap(d, 'эмиссия: экран и ореолы; ниже — рабица и колючка (плитка 0,5 м, альфа)', F(14), 140)):
        d.text((752, 488 + j * 18), line, fill=DIM, font=F(14))
    for j, line in enumerate(wrap(d, 'таблички по правилу проекта: сначала по-немецки, под ним по-английски; бумаги охраны — '
                                     'по-немецки (их писали сами), подписи приборов — по-английски', F(18), 720)):
        d.text((14, 430 + j * 26), line, fill=DIM, font=F(18))
    tag(canvas, 'T_Kpp_Panel 512: таблички, бумаги, подписи, часы, экран, ореолы')
    return canvas


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    kinds = {}
    for p in P_.values():
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    moving = len(P_) - kinds.get('static', 0)
    at = INFO['atlases']
    tris = INFO['tris']
    pp = at['Kpp']['ppm_parts']
    tr = f'{tris:,}'.replace(',', ' ')
    a = sheet('КПП · снаружи',
              f'будка, шлагбаум и ворота на своих местах, построены как генераторная; {moving} '
              f'{plural(moving, "подвижная деталь", "подвижные детали", "подвижных деталей")}, {len(S_)} '
              f'{plural(len(S_), "точка", "точки", "точек")}, {tr} {plural(tris, "треугольник", "треугольника", "треугольников")}',
              [(img('ext_day'), 'с дороги днём: шлагбаум, будка, ворота, сетка забора карты; деревья — с карты, на своих местах'),
               (img('ext_night'), 'с дороги ночью (старт пролога): в будке мигает лампа дневного света, тока нет'),
               (img('ext_booth'), 'будка: серо-зелёная доска с нащельником, белые наличники, лента окон, окно выдачи, HALT!'),
               (img('ext_back'), 'сзади, со стороны станции: дверь навешена снаружи (открыта), светильник над ней, окно слева'),
               (img('ext_left'), 'проход для пешехода слева от будки — по нему к двери; окно будки смотрит на него'),
               (img('ext_power'), 'ночью с током: горит светильник над дверью, монитор показывает камеру'),
               (img('barrier'), 'стойка-упор: вилка держит стрелу, замок вешается в две проушины (стойки и стрелы)'),
               (img('gate'), 'ворота снаружи: полотно на рельсе, ловитель, направляющие ролики, табличка SPERRGEBIET')],
              [('Будка', '4,20 × 3,20 м, комната 3,96 × 2,96, пол 0,15 над землёй на бетонной площадке со столбиками; стены — '
                         'доска с нащельником в серо-зелёной краске станции (выгорела на фасаде к дороге, вытерта до серого '
                         'дерева внизу), белые угловые доски и наличники; односкатная крыша 5° из профлиста на открытых '
                         'стропилах, белые лобовые и ветровые доски, щит KONTROLLPUNKT / CHECKPOINT'),
               ('Снаружи', 'лента из трёх окон на дорогу, окно выдачи со створкой и полкой, табличка HALT! AUSWEIS VORZEIGEN / '
                           'STOP! SHOW YOUR ID, звонок телефона и камера видеонаблюдения под свесом, светильник с клеткой над '
                           'дверью; дверь — доски, белая Z-обвязка, остеклённый верх, кованые петли'),
               ('Шлагбаум', 'бетонный фундамент, стойка сбоку от стрелы (противовес при подъёме уходит мимо неё), стрела '
                            '6 м в красно-белую полосу, стойка-упор с вилкой; замок вешается в две проушины за упором — '
                            'под ними пусто, он висит свободно'),
               ('Ворота', 'полотно 7 м на двух колёсах по рельсу в бетоне, в 0,22 м за линией забора (открытое уходит за '
                          'неподвижную секцию и сетку карты, не сквозь них), две стойки с роликами, ловитель, упор, '
                          'колючая проволока; сетка-рабица — материал с вырезкой по альфе'),
               ('Атласы', f'будка — атлас {at["Kpp"]["size"]} (стены {ru(pp["walls outside"], 1)}, внутри '
                          f'{ru(pp["inside (ply, floor, timber, roof underside)"], 1)} пикс/м), шлагбаум и ворота — '
                          f'{at["KppYard"]["size"]} (шлагбаум {ru(pp["barrier (boom, posts)"], 1)}, ворота '
                          f'{ru(pp["gate (galvanised)"], 1)}); у генераторной 51,3; мелочи {at["KppProps"]["size"]} '
                          f'({ru(at["KppProps"]["ppm"], 1)}), панель 512, сетка и колючка — плитки с альфой; по 64 цвета, '
                          'AO в цвете, дизеринг 4×4')],
              'kpp_A.jpg')
    b = sheet('КПП · внутри',
              'отделка генераторной: фанера, еловые стропила и прогоны под изнанкой профлиста, белые окна; пол бетонный',
              [(img('int_day'), 'от двери: стол буквой Г у окон, окно выдачи открыто, телефон, рация, монитор, стул'),
               (img('int_back'), 'к двери: доска объявлений, ключница, часы, аптечка, огнетушитель, жилеты, картотека'),
               (img('int_keys'), 'ключница открыта: пять подписанных крючков (ключи игры повесит сама; крючок Stationsleiter '
                                 'пустой)'),
               (img('int_desk'), 'стол у окна выдачи: телефон, ящик тумбы выдвинут; место журнала охраны'),
               (img('int_night'), 'ночью: только мигающая лампа дневного света'),
               (img('plan'), 'план без крыши: стол буквой Г, стул, картотека в углу, ключница, дверь в задней стене')],
              [('Внутри', 'фанера (швы листов, гвозди, грязь внизу, никотиновая желтизна к потолку, следы рук у ключницы, окна '
                          'выдачи и двери, светлое пятно от снятого объявления), еловые стропила и прогоны, изнанка профлиста; '
                          'бетонный пол: натоптано от двери к столу и к ключнице, следы колёсиков стула, листья у порога'),
               ('Вещи', 'стол из фанеры с тумбой (3 ящика), серая картотека (3 ящика), ключница с подписями SCHRANKE, '
                        'HAUPTGEB., GARAGE, GENERATOR, LEITER (по-английски под ними), доска объявлений (график дежурств, '
                        'телефоны, календарь), рация, монитор, телефон, стул, термос, кружка, папки, часы (стоят на 2:40), '
                        'аптечка, огнетушитель, два жилета, конвектор, лампа дневного света'),
               ('Подвижное', 'дверь, створка окна выдачи, шесть ящиков, дверца ключницы; трубка телефона — отдельный объект'),
               ('Пролог', 'S6: ключи на крючках, журнал на столе у окна выдачи, замок на шлагбауме — те же места, что в '
                          'обновлении 3; X05: звонят телефон и звонок снаружи')],
              'kpp_B.jpg')
    c = sheet('КПП · было и стало в игре',
              'слева — кадры обновления 3 из игры (Unity, ночь), справа — новый КПП; верхняя пара — вид карты KPP с дороги',
              [(u3('Forest_KPP.jpg'), 'обновление 3: вид KPP с дороги'),
               (fit(img('game_kpp')), 'сейчас: тот же вид, та же камера (ночь, мигает лампа в будке)'),
               (u3(os.path.join('U3', 'Forest_U3_KPPRoad.jpg')), 'обновление 3: у шлагбаума'),
               (img('ext_night'), 'сейчас: у шлагбаума ночью'),
               (u3(os.path.join('U3', 'Forest_U3_KPPInside.jpg')), 'обновление 3: внутри'),
               (img('int_night'), 'сейчас: внутри ночью'),
               (u3(os.path.join('U3', 'Forest_U3_KPPKeys.jpg')), 'обновление 3: ключница'),
               (img('int_keys'), 'сейчас: ключница (днём)')],
              [('То же', 'места будки, шлагбаума и ворот; размер будки и площадки; окна на дорогу и окно выдачи; дверь сзади '
                         '(то же имя, сторона петель и ход); ключница на задней стене и точки подвеса ключей; стол у окна выдачи, '
                         'журнал и телефон на своих местах; картотека и тумба с теми же ящиками; мигающая лампа и лампа над '
                         'дверью с тем же светом; таблички HALT и SPERRGEBIET'),
               ('Иначе', 'вид генераторной: доска с нащельником вместо панелей, серо-зелёная краска, белые наличники, профлист, '
                         'фанера внутри, открытые стропила; дверь навешена снаружи; ворота ходят за линией забора; стойка '
                         'шлагбаума сбоку от стрелы (противовес больше не бьёт в неё); всё запечено в атласы PSX')],
              'kpp_C.jpg', cols=2)
    tiles = []
    for ov, nv, lab in (('front', 'old_front', 'спереди'), ('back', 'old_back', 'сзади'), ('left', 'old_left', 'слева'),
                        ('right', 'old_right', 'справа'), ('iso', 'old_iso', 'сверху'), ('barrier', 'old_barrier', 'шлагбаум'),
                        ('gate', 'old_gate', 'ворота'), ('in_a', 'old_in_a', 'внутри, к окну выдачи'),
                        ('in_b', 'old_in_b', 'внутри, к ключнице')):
        tiles.append((old(ov), f'обновление 3: {lab}'))
        tiles.append((fit(img(nv)), f'сейчас: {lab}'))
    c2 = sheet('КПП · было и стало, модель',
               'слева — модель обновления 3 (цвета условные), справа — новая, те же камеры',
               tiles,
               [('Модель', 'та же площадка 6,1 × 5,1 м и будка 4,2 × 3,2 м на тех же местах, тот же пол; крыша односкатная '
                           '(в обновлении 3 — плоская с козырьком); окна той же полосой, но деревянные с переплётами; ключница '
                           'и картотека на своих местах (картотека развёрнута вдоль задней стены, чтобы ящики выдвигались); '
                           'шлагбаум и ворота — те же размеры и ходы')],
               'kpp_D.jpg', cols=2)
    kinds_s = {}
    for s in S_.values():
        kinds_s[s['kind']] = kinds_s.get(s['kind'], 0) + 1
    KC = {'hand': ((255, 216, 26), 'рука'), 'item_slot': ((51, 230, 77), 'места вещей'), 'audio': ((230, 51, 230), 'звук'),
          'vfx': ((255, 115, 26), 'эффект'), 'hide': ((26, 230, 230), 'укрытие'), 'knock': ((242, 38, 38), 'стук'),
          'seat': ((153, 102, 255), 'сесть')}
    ent = [(c_, f'{t} — {kinds_s.get(k, 0)}') for k, (c_, t) in KC.items() if kinds_s.get(k)]
    e = sheet('КПП · точки, коллайдеры, текстуры',
              f'{len(S_)} {plural(len(S_), "точка", "точки", "точек")}, {len(CON["colliders"])} '
              f'{plural(len(CON["colliders"]), "коробка-коллайдер", "коробки-коллайдера", "коробок-коллайдеров")}, атласы',
              [(legend_tile('points_plan', ent), 'точки взаимодействия в будке сверху (крыша снята)'),
               (img('colliders_plan'), 'коллайдеры будки сверху (крыша и площадка не показаны)'),
               (img('barrier_up'), 'стрела поднята на 80°: противовес ушёл вниз рядом со стойкой'),
               (img('gate_open'), 'ворота откачены на 6,6 м: полотно за неподвижной секцией, проезд 6,5 м'),
               (img('site_plan'), 'сверху: будка, шлагбаум, ворота, дорога, забор карты'),
               (atlas_tile(os.path.join(TEX, 'T_Kpp_Kpp_BaseColor.png'), 'T_Kpp_Kpp', at['Kpp']['ppm'],
                           'будка: стены, крыша, фанера, пол, стропила, площадка, столбики, стол, картотека, ключница'),
                None),
               (atlas_pair_tile([(os.path.join(TEX, 'T_Kpp_KppYard_BaseColor.png'), 'T_Kpp_KppYard', at['KppYard']['ppm'],
                                  'шлагбаум и ворота: стрела, стойки, фундаменты, полотно, рельс, направляющие, ловитель'),
                                 (os.path.join(TEX, 'T_Kpp_KppProps_BaseColor.png'), 'T_Kpp_KppProps', at['KppProps']['ppm'],
                                  'телефон, звонок, жилеты, огнетушитель, монитор, рация, стул, папки, термос, кружка, часы, '
                                  'аптечка, камера')],
                                'атласы шлагбаума с воротами и мелочей'), None),
               (panel_tile(), None)],
              [('Точки', 'места вещей пролога (четыре ключа и пустой крючок, журнал, замок); рука — дверь, створка, ящики, '
                         'дверца ключницы, трубка, стрела, ворота (два игрока); звук — телефон, звонок, лампа, рация, дверь, '
                         'крыша, шлагбаум, ворота, ловитель; эффект — мигание лампы; укрытие — под столом; сесть — стул; '
                         'стук — стены, окна, дверь, крыша'),
               ('Коллайдеры', 'будка — площадка, стены кусками вокруг окон и двери, окна, стол, картотека, ключница, '
                              'конвектор, лист крыши (наклонный), столбики; у двери, дверцы ключницы, створки, стула — свои; '
                              'шлагбаум — фундамент, стойка, упор, стрела (едет с ней); ворота — ловитель, направляющие, упор, '
                              'неподвижная секция, полотно (едет с ним)'),
               ('Проверки', 'проход: от дороги через проход у будки к двери и в комнату; все точки пролога в досягаемости; '
                            'со снятым замком и откаченными воротами — проезд 5,3 м под шлагбаумом и 6,5 м в воротах; '
                            'подвижные детали не задевают остальное на всём ходу; совпадающих граней нет'),
               ('Unity', 'система координат префаба Checkpoint: x — к дороге, y — назад, z — вверх; позиция в Unity (−x, z, '
                         '−y), угол → −угол; места шлагбаума и ворот на карте — в контракте (map_placement); подробности — '
                         'KPP_CONTRACT.md')],
              'kpp_E.jpg', cols=2)
    print(a, b, c, c2, e)
