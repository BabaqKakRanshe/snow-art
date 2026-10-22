"""Sheets for the van concept v2: exterior (day) and night / interior / cab / in-game frame.
python3 make_sheets_van.py <out_dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'rend', 'final')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM, ACC = (22, 23, 26), (236, 236, 232), (150, 152, 156), (214, 64, 48)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def tag(im, text, xy=(10, 10), f=None):
    f = f or F(22)
    d = ImageDraw.Draw(im)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rectangle([x - 6, y - 4, x + w + 8, y + f.size + 8], fill=(0, 0, 0))
    d.text((x, y), text, fill=INK, font=f)


def ps1(path, scale=2):
    """the game's frame: 240 lines, 15-bit colour with Bayer 4x4, nearest upscale"""
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


def sheet(name, title, sub, tiles, rows, fname):
    W, H, g = 900, 600, 16
    S = Image.new('RGB', (2 * W + 3 * g, 130 + 2 * H + g + 340), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    d.text((g, 84), sub, fill=DIM, font=F(25))
    for i, (im, label) in enumerate(tiles):
        im = im.copy()
        if im.size != (W, H):
            canvas = Image.new('RGB', (W, H), (10, 10, 12))
            canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
            im = canvas
        tag(im, label)
        S.paste(im, (g + (i % 2) * (W + g), 130 + (i // 2) * (H + g)))
    y = 130 + 2 * H + g + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=ACC if k in ('Плюсы', 'Минусы') else DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, 2 * W + g - 190)):
            d.text((g + 170, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    S = S.crop((0, 0, S.width, y + 10))
    p = os.path.join(OUT, fname)
    S.save(p, quality=92)
    return p


def img(v):
    return Image.open(os.path.join(R, v + '.png')).convert('RGB')


def side_with_dims():
    im = img('side')
    d = ImageDraw.Draw(im)
    ppm = 900 / 7.4                                      # ortho scale 7.4 m over 900 px, camera x = 0.3, z = 1.55
    X = lambda x: int(450 + (0.3 - x) * ppm)             # the left side faces the camera: +x (nose) is on the left
    Z = lambda z: int(300 - (z - 1.55) * ppm)
    col = (30, 32, 36)
    f = F(18, True)
    # length of the body and wheelbase
    for (x0, x1, z, t) in ((2.464, -2.443, 3.45, 'кузов 4,9 м'), (1.45, -1.25, -0.10, 'база 2,7 м')):
        d.line([(X(x0), Z(z)), (X(x1), Z(z))], fill=col, width=2)
        for xx in (x0, x1):
            d.line([(X(xx), Z(z) - 7), (X(xx), Z(z) + 7)], fill=col, width=2)
        w = d.textlength(t, font=f)
        d.rectangle([(X(x0) + X(x1)) / 2 - w / 2 - 4, Z(z) - 24, (X(x0) + X(x1)) / 2 + w / 2 + 4, Z(z) - 4], fill=(225, 227, 230))
        d.text(((X(x0) + X(x1)) / 2 - w / 2, Z(z) - 23), t, fill=col, font=f)
    # heights
    fs = F(15, True)
    for (z, t) in ((2.95, 'крыша 2,95 м'), (3.10, 'багажник 3,1 м')):
        d.line([(X(-2.62), Z(z)), (X(-2.95), Z(z))], fill=col, width=2)
        w = d.textlength(t, font=fs)
        x0, y0 = 900 - w - 8, Z(z) - (22 if z > 3.0 else -4)
        d.rectangle([x0 - 3, y0 - 1, x0 + w + 3, y0 + 18], fill=(225, 227, 230))
        d.text((x0, y0), t, fill=col, font=fs)
    d.text((X(3.6) - 30, Z(1.86) - 26), '1,8 м', fill=col, font=f)
    return im


if __name__ == '__main__':
    a = sheet('A', 'Буханка-тип · концепт 2',
              'свой кузов-«батон» над мотором, 4×4 на портальных мостах, собран как самолёт',
              [(img('q34'), 'днём, спереди'), (img('q34r'), 'днём, сзади: лестница, багажник, задние двери'),
               (side_with_dims(), 'сбоку, силуэт человека 1,8 м'), (img('night'), 'ночью: печь топится, свет в окнах, дверь открыта')],
              [('Габарит', '5,3 × 2,2 м по бамперам, высота 2,95 м по крыше и 3,5 м с грузом на багажнике; кузов 4,9 × 2,14 м, база 2,7 м, колёса Ø 1,04 м, просвет около 0,43 м'),
               ('Места', '2 в кабине, 4 за столом в салоне, кровать на двоих в корме'),
               ('Снаружи', 'силовой бампер с лебёдкой, шноркель, багажник с люстрой, запаской и ящиком, лестница на крышу, расширители арок, грязевые шины'),
               ('Сборка', 'кузов из гладких поверхностей, проёмы с резиновыми уплотнителями, зазоры дверей, водостоки; окраска запечена в атлас 512 px, 64 цвета, Байер, тень в цвете'),
               ('Реф', 'УАЗ-452: 4,44 × 2,10 × 2,10 м; заводская «Экспедиция» с бамперами — 4,87 м; военные мосты с колёсными редукторами поднимают просвет с 220 до 300 мм')],
              'van_v2_A_exterior.jpg')
    b = sheet('B', 'Буханка-тип · внутри и в игре',
              'салон-автодом: вагонка, стёганый дерматин, стол у окна, печка с трубой, кровать; кабина над мотором',
              [(img('inside'), 'салон ночью'), (img('cab'), 'место водителя: капот мотора между сиденьями'),
               (ps1(os.path.join(R, 'ingame.png'), 2), 'в кадре игры: 240 строк, 15-бит цвет'),
               (img('q34').crop((330, 120, 780, 420)).resize((900, 600), Image.NEAREST), 'крупно: PSX-текстура, как у самолёта')],
              [('Салон', 'пол 1,0 м, потолок 1,9 м — в полный рост; вагонка на стенах и потолке, внизу стёганый дерматин, линолеум, шторки'),
               ('Уют', 'печка с трубой через крышу, чайник, подвесная лампа над столом, спальник и подушки на кровати, валенки у печки, полки с сумками'),
               ('Кабина', 'кожух мотора между сиденьями (тёплый, на нём лежит плед), круглые приборы, руль автобусного наклона, два рычага'),
               ('Игра', 'на ходу в салоне сидят, ходят только на стоянке (так в спецификации техники); двери и свет — на тех же системах, что у самолёта')],
              'van_v2_B_inside.jpg')
    print(a)
    print(b)
