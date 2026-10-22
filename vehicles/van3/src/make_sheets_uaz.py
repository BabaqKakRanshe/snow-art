"""Sheets for the PSX UAZ-452: A exterior, B saloon / cab / game frame / texels, C the PSX atlases.
python3 make_sheets_uaz.py <out_dir>"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'rend', 'final')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
INFO = json.load(open(os.path.join(HERE, 'out', 'uaz_psx.json')))
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(FB if b else FR, s)
BG, INK, DIM, ACC = (22, 23, 26), (236, 236, 232), (150, 152, 156), (214, 64, 48)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0
# vehicle bounds used by the renderer (bumpers, mirrors, roof vent; the stove flue cap is left out)
LEN, WID, HGT = 4.502, 2.34, 2.108
CX, ZC = 0.0, 0.38 * 2.108


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
    S = Image.new('RGB', (cols * W + (cols + 1) * g, 130 + nrow * (H + g) + 420), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    d.text((g, 84), sub, fill=DIM, font=F(25))
    for i, (im, label) in enumerate(tiles):
        im = im.copy()
        if im.size != (W, H):
            canvas = Image.new('RGB', (W, H), (10, 10, 12))
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
        for j, line in enumerate(wrap(d, v, f, cols * W + (cols - 1) * g - 200)):
            d.text((g + 200, y + j * 30), line, fill=INK, font=f)
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
    ortho = LEN * 1.62
    ppm = 900 / ortho
    xc = CX + 0.25
    X = lambda x: int(450 + (xc - x) * ppm)                 # the left side faces the camera: the nose is on the left
    Z = lambda z: int(300 - (z - ZC) * ppm)
    col = (30, 32, 36)
    f = F(18, True)
    wb = INFO.get('wheelbase', 2.41)
    for (x0, x1, z, t) in ((LEN / 2, -LEN / 2, HGT + 0.30, f'{LEN:.2f} м'.replace('.', ',')),
                           (1.207, -1.203, -0.13, f'база {wb:.2f} м'.replace('.', ','))):
        d.line([(X(x0), Z(z)), (X(x1), Z(z))], fill=col, width=2)
        for xx in (x0, x1):
            d.line([(X(xx), Z(z) - 7), (X(xx), Z(z) + 7)], fill=col, width=2)
        w = d.textlength(t, font=f)
        d.rectangle([(X(x0) + X(x1)) / 2 - w / 2 - 4, Z(z) - 24, (X(x0) + X(x1)) / 2 + w / 2 + 4, Z(z) - 4], fill=(225, 227, 230))
        d.text(((X(x0) + X(x1)) / 2 - w / 2, Z(z) - 23), t, fill=col, font=f)
    # height
    xh = -LEN / 2 - 0.35
    d.line([(X(xh), Z(0)), (X(xh), Z(HGT))], fill=col, width=2)
    for zz in (0, HGT):
        d.line([(X(xh) - 7, Z(zz)), (X(xh) + 7, Z(zz))], fill=col, width=2)
    t = f'{HGT:.2f} м'.replace('.', ',')
    w = d.textlength(t, font=f)
    d.rectangle([X(xh) + 10, Z(HGT / 2) - 12, X(xh) + 18 + w, Z(HGT / 2) + 10], fill=(225, 227, 230))
    d.text((X(xh) + 14, Z(HGT / 2) - 11), t, fill=col, font=f)
    d.text((X(LEN / 2 + 0.9) - 26, Z(1.86) - 26), '1,8 м', fill=col, font=f)
    return im


def atlas_tile(name, label):
    p = os.path.join(HERE, 'tex', 'uaz', f'T_UAZ_{name}_BaseColor.png')
    a = Image.open(p).convert('RGB')
    s = a.size[0]
    k = max(1, 560 // s)
    t = a.resize((s * k, s * k), Image.NEAREST)
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(t, ((900 - t.width) // 2 - 120, (600 - t.height) // 2 + 10))
    # palette swatches
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    lum = pal @ np.array([0.3, 0.59, 0.11])
    pal = pal[np.argsort(lum)]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[:64]):
        x0, y0 = 690 + (i % 8) * 24, 60 + (i // 8) * 24
        d.rectangle([x0, y0, x0 + 21, y0 + 21], fill=tuple(int(v) for v in c))
    inf = INFO.get(name, {})
    d.text((690, 270), f"{s} × {s} px", fill=INK, font=F(22, True))
    d.text((690, 302), f"{inf.get('ppm', '?')} px/м".replace('.', ','), fill=DIM, font=F(20))
    d.text((690, 330), f"{len(pal)} цветов", fill=DIM, font=F(20))
    tag(canvas, label)
    return canvas


if __name__ == '__main__':
    tris = INFO.get('tris', 0)
    a = sheet('УАЗ-452 «буханка» · PSX',
              'готовая модель (tiunov.se, CC BY 4.0), перекрашена и переведена в PSX по рецепту самолёта',
              [(img('q34'), 'днём, спереди'), (img('q34r'), 'днём, сзади'),
               (side_with_dims(), 'сбоку, силуэт человека 1,8 м'), (img('night'), 'ночью: печь, лампа и шторки, фары')],
              [('Модель', f'«Uaz», автор tiunov.se, Sketchfab, лицензия CC BY 4.0 — автора указать в титрах. '
                          f'{tris // 1000} тыс. треугольников вместе с салоном и уютным набором; двери кабины и задние двери — отдельные объекты'),
               ('Размеры', 'кузов 4,36 м, с бамперами 4,50 м; ширина 1,97 м (2,34 с зеркалами); высота 2,11 м; колёса Ø 0,65 м'),
               ('Окраска', 'хаки «защитный»: выгоревшая крыша, ржавчина по низу, аркам и под окнами, сколы до грунта, грязь от колёс, '
                           'соль на пороге, снег в протекторе'),
               ('PSX', 'как у самолёта: тень запечена в цвет, швы — тёмная линия в 1 тексель, палитра 64 цвета на атлас, '
                       'Байер 4×4, точечная фильтрация, без normal map')],
              'uaz_A_exterior.jpg')
    b = sheet('УАЗ-452 · салон и кадр игры',
              'потолок поднят до 1,25 м над полом — сидящий игрок помещается; уютный набор внутри',
              [(img('inside'), 'салон ночью: вперёд, к кабине'), (img('stove'), 'салон ночью: назад, к печке'),
               (img('plan'), 'план салона (крыша срезана)'), (img('cab'), 'место водителя ночью'),
               (img('close'), 'крупно: тексели, как у самолёта'),
               (ps1(os.path.join(R, 'ingame.png'), 2), 'в кадре игры: 240 строк, 15-бит цвет')],
              [('Салон', 'пол 0,72 м, потолок 1,97 м (было 1,88): 1,25 м внутри; 6 мест в салоне (3 + 2 + 1) и 2 в кабине'),
               ('Уют', 'печка-буржуйка с трубой через крышу и экраном, дровница с берёзовыми поленьями, валенки, чайник; '
                       'стол с термосом и кружками, подвесная лампа, шторки на окнах, вагонка, стёганый дерматин, плед, коврик'),
               ('Свет', 'точки света лампы, печки и приборов — для ночных сцен; стёкла салона светятся снаружи'),
               ('Дальше', 'для пакета Unity: вырезать боковую дверь салона, поставить шарниры дверям, сиденья и сокеты, '
                          'ужать колёса (сейчас 4 × 8 тыс. треугольников)')],
              'uaz_B_inside.jpg')
    c = sheet('УАЗ-452 · PSX-атласы',
              'шесть атласов с уникальной развёрткой; цвет нарисован по месту (ржавчина, грязь, соль) и сведён к 64 цветам',
              [(atlas_tile('Body', 'Body — кузов'), None), (atlas_tile('Trim', 'Trim — чёрный металл, резина, фары'), None),
               (atlas_tile('Wheel', 'Wheel — колесо (общее на 4)'), None), (atlas_tile('Cabin', 'Cabin — вагонка, дерматин, пол'), None),
               (atlas_tile('Seats', 'Seats — сиденья и пледы'), None), (atlas_tile('Props', 'Props — печка, стол, шторки'), None)],
              [('Плотность', 'кузов ~37 px/м, салон ~53 px/м — тексель 2–3 см, как на самолёте'),
               ('Формат', 'PNG, 64 цвета на атлас, Байер 4×4; в Unity — Point filter, без мипмапов и без сжатия')],
              'uaz_C_atlases.jpg')
    print(a)
    print(b)
    print(c)
