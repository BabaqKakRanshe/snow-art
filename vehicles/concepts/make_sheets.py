"""Concept sheets: one per concept (4 views + facts), an overview of the four, a size comparison.
python3 make_sheets.py <out_dir>"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REND = os.path.join(HERE, 'rend')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM, ACC = (22, 23, 26), (236, 236, 232), (150, 152, 156), (214, 64, 48)
DIMS = json.load(open(os.path.join(REND, 'dims.json')))


def m(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


C = [
    dict(mod='c1_kung', n=1, name='Кунг', sub='кабина над мотором 4×4 и утеплённая будка — «Шишига» с кунгом, своя машина без марки',
         seats='2 в кабине + 6 в будке', room='будка внутри 3,65 × 2,22 м, потолок 1,73 м',
         inside='печка с трубой, лавки друг напротив друга, столик, фонарь, окошко-лаз в кабину, стеллаж с канистрами; снаружи — лесенка к двери',
         plus='груз и люди в одной машине; будка — дом на колёсах; водитель отделён — говорят через окошко',
         minus='из будки не видно дорогу; высокая; водитель в кабине один',
         ref='ГАЗ-66 с кунгом К-66: 6,19 × 2,40 × 3,26 м, кунг внутри 3,68 × 2,25 × 1,80 м'),
    dict(mod='c2_vahta', n=2, name='Вахтовка', sub='капотный 4×4, кабина и салон — один кузов-автобус',
         seats='водитель + 9', room='салон 5,2 × 2,3 м, потолок 1,73 м',
         inside='столик у окна, как в купе; багажные полки; печка в корме; снаружи — складная дверь, багажник и лестница',
         plus='все в одном объёме, видят друг друга и дорогу; окна по кругу — лучший вид наружу',
         minus='окна везде: снаружи видно всё, спрятаться негде; места под груз мало',
         ref='ПАЗ-3206 4×4: 7,0 × 2,52 × 3,1 м; вахтовки на шасси ГАЗ-3308 «Садко» (6,35 × 2,34 × 2,6 м)'),
    dict(mod='c3_balloon', n=3, name='Буханка на баллонах', sub='6×6 на шинах низкого давления, кузов-«батон» на корпусе-лодке',
         seats='2 впереди + 6 за столом', room='салон 5,2 × 2,1 м, потолок 1,58 м',
         inside='П-образный диван на арках колёс вокруг стола, печка; снаружи — лебёдка и фары на крыше',
         plus='самый «буханочный» вайб; лучший из колёсных по снегу, может плавать',
         minus='низкий потолок; шесть колёс и качка — больше работы в физике',
         ref='Трэкол-39294: 5,67 × 2,54 × 2,72 м, до 8 мест, шины 0,1–0,5 кг/см², плавает'),
    dict(mod='c4_tracked', n=4, name='Сцепка', sub='две гусеничные секции на шарнире: впереди кабина, сзади тёплая «нора»',
         seats='4 впереди + 6 сзади', room='задняя секция 3,3 × 1,9 м, потолок 1,5 м',
         inside='лавки друг напротив друга, печка, столик, фонарь, шторки; сидеть, а не стоять',
         plus='проходит по любому снегу; задняя секция отделена от водителя — кооп через переговоры',
         minus='гусеницы и шарнир — самая сложная физика и сеть; узкая, груза мало',
         ref='Hägglunds Bv206: 6,9 × 1,87 × 2,4 м, 6 + 11 мест, служит антарктическим экспедициям'),
]
LBL = {'day': 'днём', 'night': 'ночью: печь топится, свет в окнах', 'inside': 'внутри, ночью',
       'side': 'сбоку, человек 1,8 м'}


def tag(im, text, xy=(10, 10), f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rectangle([x - 6, y - 4, x + w + 8, y + f.size + 8], fill=(0, 0, 0))
    d.text((x, y), text, fill=INK, font=f)


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


def concept_sheet(c):
    d0 = os.path.join(REND, c['mod'])
    ims = {v: Image.open(os.path.join(d0, f'{v}_psx.png')).convert('RGB') for v in ('day', 'night', 'inside', 'side')}
    W, H = ims['day'].size
    g = 16
    S = Image.new('RGB', (2 * W + 3 * g, 130 + 2 * H + g + 300), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), f"{c['n']}  {c['name']}", fill=INK, font=F(52, True))
    d.text((g, 84), c['sub'], fill=DIM, font=F(26))
    for i, v in enumerate(('day', 'night', 'inside', 'side')):
        im = ims[v].copy()
        tag(im, LBL[v])
        S.paste(im, (g + (i % 2) * (W + g), 130 + (i // 2) * (H + g)))
    k = DIMS[c['mod']]
    size = f"{m(k['L'])} × {m(k['W'])} × {m(k['H'])} м"
    if k['H_pipe'] > k['H'] + 0.05:
        size += f" (с трубой {m(k['H_pipe'])} м)"
    rows = [('Габарит', size), ('Места', c['seats']), ('Салон', c['room']), ('Внутри', c['inside']),
            ('Плюсы', c['plus']), ('Минусы', c['minus']), ('Реф', c['ref'])]
    y = 130 + 2 * H + g + 18
    f, fb = F(23), F(23, True)
    for k_, v in rows:
        d.text((g, y), k_, fill=ACC if k_ in ('Плюсы', 'Минусы') else DIM, font=fb)
        for j, line in enumerate(wrap(d, v, f, 2 * W + g - 170)):
            d.text((g + 150, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    S = S.crop((0, 0, S.width, min(S.height, y + 10)))
    p = os.path.join(OUT, f"concept_{c['n']}_{c['mod'].split('_')[1]}.jpg")
    S.save(p, quality=92)
    return p


def overview():
    W, H = 480, 300
    g = 12
    S = Image.new('RGB', (4 * W + 5 * g, 86 + 3 * H + 3 * g + 10), BG)
    d = ImageDraw.Draw(S)
    for i, c in enumerate(C):
        x = g + i * (W + g)
        d.text((x, 14), f"{c['n']}  {c['name']}", fill=INK, font=F(30, True))
        k = DIMS[c['mod']]
        d.text((x, 54), f"{m(k['L'])} × {m(k['W'])} × {m(k['H'])} м · {c['seats']}", fill=DIM, font=F(18))
        for j, v in enumerate(('day', 'night', 'inside')):
            im = Image.open(os.path.join(REND, c['mod'], f'{v}_psx.png')).convert('RGB').resize((W, H), Image.NEAREST)
            S.paste(im, (x, 86 + j * (H + g)))
    p = os.path.join(OUT, 'concepts_overview.jpg')
    S.save(p, quality=92)
    return p


def sizes():
    """side views at one scale: ortho 9.0 m over 960 px -> 106.67 px/m; ground at z = 0"""
    ppm = 960 / 9.0
    z_top, z_bot = 4.1, -0.12
    def zy(z):
        return int(round((1.75 + 9.0 / 1.6 / 2 - z) * ppm))
    g = 14
    rows = []
    for c in C:
        im = Image.open(os.path.join(REND, c['mod'], 'side_psx.png')).convert('RGB')
        rows.append((c, im.crop((0, zy(z_top), 960, zy(z_bot)))))
    rh = rows[0][1].height
    ref_h = int(3.1 * ppm)
    CW = 380
    S = Image.new('RGB', (960 + 2 * g + CW, 70 + 4 * (rh + g) + ref_h + 50), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 16), 'Размер: все четыре в одном масштабе, человек 1,8 м', fill=INK, font=F(30, True))
    y = 70
    for c, im in rows:
        S.paste(im, (g, y))
        k = DIMS[c['mod']]
        tx = 960 + 2 * g
        d.text((tx, y + 30), f"{c['n']}  {c['name']}", fill=INK, font=F(24, True))
        d.text((tx, y + 72), f"длина {m(k['L'])} м", fill=INK, font=F(22))
        d.text((tx, y + 102), f"ширина {m(k['W'])} м", fill=INK, font=F(22))
        d.text((tx, y + 132), f"высота {m(k['H'])} м", fill=INK, font=F(22))
        d.text((tx, y + 166), c['seats'], fill=DIM, font=F(20))
        y += rh + g
    # reference outlines of real vehicles, same scale, on one baseline (front at the same x)
    base = y + ref_h
    x = g + 20
    d.line([(g, base), (g + 960, base)], fill=(110, 112, 118), width=2)
    for name, L, Hh, col in (('Урал-4320', 7.37, 2.72, (150, 152, 158)), ('УАЗ-452 «Буханка»', 4.36, 2.09, (205, 140, 120))):
        w, h = int(L * ppm), int(Hh * ppm)
        d.rectangle([x, base - h, x + w, base], outline=col, width=3)
        ty = base - h + 8
        d.text((x + w - d.textlength(f'{name}  {m(L)} × {m(Hh)} м', font=F(20, True)) - 10, ty),
               f'{name}  {m(L)} × {m(Hh)} м', fill=col, font=F(20, True))
    tx = 960 + 2 * g
    d.text((tx, base - 110), 'Для сравнения', fill=INK, font=F(22, True))
    d.text((tx, base - 78), 'габариты настоящих машин', fill=DIM, font=F(20))
    d.text((tx, base - 52), '(длина × высота, без тента)', fill=DIM, font=F(20))
    p = os.path.join(OUT, 'concepts_sizes.jpg')
    S.save(p, quality=92)
    return p


if __name__ == '__main__':
    out = [concept_sheet(c) for c in C] + [overview(), sizes()]
    print('\n'.join(out))
