"""Sheets for the forester's hut 1.1: A the door and the porch of forest_hut_yard (the hut with the porch, the swing over
its deck in plan and in section, outside by day, the door shut, the prologue night, from the back, inside toward the
door), E points, colliders, atlases, the panel. Only the views that changed from 1.0 are rendered.  Self-contained (the
van / container sheet helpers copied in).  python3 make_sheets_hut.py [out_dir] [yard.blend's yard_contract.json]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
FIT = os.path.join(HERE, 'checks', 'porch_fit.json')
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



# ---------------------------------------------------------------- v1.1: the door over the porch (plan and section)
# the porch of forest_hut_yard 1.0 (src/yard_kit.py there: PW 1.20, PD 1.25, P_DECK 0.32, P_WALL_Z 2.42, P_FRONT_Z 2.12,
# rafters at x -1.20 / -0.40 / 0.40 / 1.20 from the wall plate over the beam), at (0, -1.2, 0) in the hut frame
Y0 = -1.20
PORCH = dict(deck=(-1.20, 1.20, Y0 - 1.25, Y0), step=(-0.88, 0.12, Y0 - 1.53, Y0 - 1.25), bench=(0.78, 1.12, Y0 - 1.05, Y0 - 0.20),
             posts=[(-1.14, Y0 - 1.19), (1.14, Y0 - 1.19)], beam=(Y0 - 1.24, Y0 - 1.14, 2.12, 2.24), plate=(2.36, 2.48),
             rafters=(-1.20, -0.40, 0.40, 1.20), raft_front=Y0 - 1.55, slope=(2.48 - 2.24) / 1.19)


def porch_tile():
    import math
    im = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(im)
    fit_ = json.load(open(FIT))
    pm = fit_['piece_min']
    dp = CON['parts']['IX_HutDoor_1']
    hx, hy = dp['pivot'][0], dp['pivot'][1]
    cx_, sx_ = dp['box']['center'][0], dp['box']['size'][0]
    U0, U1 = cx_ - sx_ / 2, cx_ + sx_ / 2                 # the leaf along its own x from the pivot
    LINE, DIMC, HUT, GOLD, RED = (210, 212, 216), (120, 124, 130), (88, 70, 58), (255, 205, 60), (235, 80, 70)
    # plan (top view): x right, the hut at the top
    S, ox, oy = 150.0, 24 + 1.45 * 150, 70 + (-0.95) * 150
    P = lambda x, y: (ox + x * S, oy - y * S)
    def rect(x0, x1, y0, y1, **kw):
        d.rectangle([P(x0, y1), P(x1, y0)], **kw)
    def dashed(a, b, col, n=14):
        for k in range(n):
            if k % 2 == 0:
                t0, t1 = k / n, (k + 1) / n
                d.line([P(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), P(a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)],
                       fill=col, width=1)
    rect(-1.34, -0.85, Y0, Y0 + 0.12, fill=HUT)                          # the front wall either side of the door
    rect(0.15, 1.34, Y0, Y0 + 0.12, fill=HUT)
    rect(*PORCH['deck'], outline=DIMC, width=2)
    rect(*PORCH['step'], outline=DIMC, width=1)
    rect(*PORCH['bench'], fill=(70, 72, 78), outline=DIMC)
    for (px_, py_) in PORCH['posts']:
        rect(px_ - 0.05, px_ + 0.05, py_ - 0.05, py_ + 0.05, fill=(150, 120, 90))
    for xr in PORCH['rafters']:
        dashed((xr, Y0), (xr, PORCH['raft_front']), DIMC)
    b0, b1 = PORCH['beam'][0], PORCH['beam'][1]
    dashed((-1.30, (b0 + b1) / 2), (1.30, (b0 + b1) / 2), DIMC, 22)
    # the leaf: shut, at 67.5 deg (the tightest under the middle rafter), open at 105 deg; the arc of its free edge
    def leaf(a_deg, col, w):
        a = math.radians(a_deg)
        c, s_ = math.cos(a), math.sin(a)
        pts = []
        for (u, v) in ((U0, 0.0), (U1, 0.0), (U1, 0.07), (U0, 0.07)):
            pts.append(P(hx + u * c + v * s_, hy - u * s_ + v * c))
        d.polygon(pts, outline=col, width=w)
    r = U1
    box_ = [P(hx - r, hy + r)[0], P(hx - r, hy + r)[1], P(hx + r, hy - r)[0], P(hx + r, hy - r)[1]]
    d.arc(box_, start=0, end=105, fill=(160, 140, 60), width=1)
    leaf(0, LINE, 2)
    leaf(67.5, RED, 2)
    leaf(105, GOLD, 3)
    f = F(15)
    d.text(P(-1.45, -0.97), 'хижина', fill=DIMC, font=f)
    d.text(P(-0.80, -1.02), 'проём 1,00 × 1,915', fill=LINE, font=f)
    d.text(P(0.45, -1.30), 'лавка', fill=DIMC, font=f)
    d.text(P(-0.84, -2.78), 'ступенька', fill=DIMC, font=f)
    d.text(P(-1.46, -2.90), f'105°: до стропила x −1,20 — {ru(pm["rafter x -1.20"][0] * 100, 1)} см, '
                            f'до столба — {ru(pm["post x -1.14"][0] * 100, 1)} см', fill=GOLD, font=f)
    d.text(P(-1.46, -3.03), f'67,5°: под стропилом x −0,40 — {ru(pm["rafter x -0.40"][0] * 100, 1)} см', fill=RED, font=f)
    d.text(P(-1.46, -3.16), 'пунктир — стропила и балка над головой', fill=DIMC, font=f)
    # section along the middle rafter (x -0.40): distance from the wall -> z, the height 3 x exaggerated
    X0s, Y0s, SH, SV, ZB_ = 590, 520, 240.0, 720.0, 2.08
    Q = lambda dist, z: (X0s + dist * SH, Y0s - (z - ZB_) * SV)
    zt = dp['box']['center'][2] + dp['box']['size'][2] / 2 + dp['pivot'][2]
    raft = lambda dist: 2.48 - PORCH['slope'] * dist
    WOOD = (110, 84, 60)
    d.polygon([Q(0, raft(0)), Q(1.20, raft(1.20)), Q(1.20, raft(1.20) + 0.09), Q(0, raft(0) + 0.09)], fill=WOOD)
    d.rectangle([Q(0, 2.48), Q(0.06, 2.36)], fill=WOOD)                                            # wall plate
    d.rectangle([Q(1.14, 2.24), Q(1.24, 2.12)], fill=WOOD)                                         # beam
    d.rectangle([Q(-0.08, 2.60), Q(0.0, ZB_)], fill=HUT)                                           # the wall
    reach = 1.02
    d.line([Q(0.07, zt), Q(reach, zt)], fill=RED, width=3)
    d.line([Q(reach, zt), Q(reach, raft(reach))], fill=LINE, width=2)
    d.text((X0s - 20, 70), 'разрез по стропилу x −0,40', fill=LINE, font=F(16, True))
    d.text((X0s - 20, 92), 'высота ×3', fill=DIMC, font=f)
    d.text(Q(0.42, raft(0.42) + 0.14), 'стропило крыльца', fill=DIMC, font=f)
    d.text(Q(0.09, 2.395), 'обвязка', fill=DIMC, font=f)
    d.text(Q(0.10, zt - 0.012), f'верх полотна {ru(zt, 2)}', fill=RED, font=f)
    d.line([Q(reach, zt + 0.006), Q(reach - 0.10, zt + 0.06)], fill=LINE, width=1)
    d.text(Q(reach - 0.28, zt + 0.09), f'{ru((raft(reach) - zt) * 100, 1)} см', fill=LINE, font=F(17, True))
    d.text(Q(0.98, 2.115), 'балка', fill=DIMC, font=f)
    d.text(Q(-0.08, ZB_ - 0.012), 'стена', fill=DIMC, font=f)
    tag(im, 'дверь над крыльцом forest_hut_yard: план и разрез')
    return im


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    at = INFO['atlases']
    tris = INFO['tris']
    pp = at['Hut']['ppm_parts']
    tr = f'{tris:,}'.replace(',', ' ')
    M = CON['meta']
    pm = json.load(open(FIT))['piece_min']
    cm = lambda k: ru(pm[k][0] * 100, 1)
    a = sheet('Хижина лесника 1.1 · дверь и крыльцо',
              f'та же хижина, что 1.0, с дверью 1,00 × 1,915 м под крыльцо forest_hut_yard; {tr} '
              f'{plural(tris, "треугольник", "треугольника", "треугольников")}, атласы как в 1.0',
              [(img('porch_day'), 'с крыльцом forest_hut_yard на его месте: дверь открыта на 105° и стоит между стропилами, '
                                  'лавка крыльца справа'),
               (porch_tile(), None),
               (img('ext_day'), 'днём от тропы, без крыльца: проём 1,00 × 1,915, лавка под окном, колода у левого угла, '
                                'рога под коньком'),
               (img('sign'), 'дверь закрыта: полотно 1,04 × 1,93 на двух кованых петлях, белая Z-обвязка'),
               (img('ext_night'), 'старт пролога: дверь открыта, у двери горит фонарь, туман'),
               (img('ext_back'), 'сзади: колода с топором теперь у левого переднего угла'),
               (img('int_back'), 'изнутри к двери: проём 1,00 × 1,915, слева вешалка и сапоги, справа полки')],
              [('Дверь', 'проём 1,00 × 1,915 м (x −0,85…0,15, z 0,33…2,245), полотно 1,04 × 1,93 (низ 0,33, верх 2,26) '
                         'снаружи стены на кованых петлях слева; IX_HutDoor_1 — то же имя, сторона петель и ход 0…105° '
                         'наружу; скоба и ручка — у правого края, вертушка — на правом откосе внутри'),
               ('Крыльцо', 'HutPorch стоит в префабе TowerHut на (0, 0, 1,2): на всём ходе дверь ничего не задевает — '
                           f'настил 1 см, стропило над дверью {cm("rafter x -0.40")} см, стропило слева {cm("rafter x -1.20")} см '
                           f'(открыта), балка {cm("beam / fascia")} см, левый столб и раскос {cm("post x -1.14")} см, лавка 0,6 м; '
                           'выше 1,915 дверь не даёт стропило над ней: его низ на 2,275 там, где проходит край полотна'),
               ('Переставлено', 'лавка — под окно на правой стене, колода с топором — к левому переднему углу, рога — на '
                                'фронтон под конёк (0,85 прежнего размера): в 1.0 они стояли там, где теперь крыльцо'),
               ('Атласы', f'хижина, вывеска и засидка — один атлас {at["Hut"]["size"]} ({ru(at["Hut"]["ppm"], 1)} пикс/м, стены '
                          f'{ru(pp["walls outside"], 1)}, внутри {ru(pp["inside (ply, floor, timber, roof underside)"], 1)}, '
                          f'засидка {ru(pp["stand"], 1)}), мелочи {at["HutProps"]["size"]} ({ru(at["HutProps"]["ppm"], 1)}), '
                          'панель 512; по 64 цвета, AO в цвете, дизеринг 4×4')],
              'hut_A.jpg')
    kinds_s = {}
    for s in S_.values():
        kinds_s[s['kind']] = kinds_s.get(s['kind'], 0) + 1
    KC = {'hand': ((255, 216, 26), 'рука'), 'pour': ((51, 128, 255), 'залив'), 'item_slot': ((51, 230, 77), 'места вещей'),
          'audio': ((230, 51, 230), 'звук'), 'vfx': ((255, 115, 26), 'эффект'), 'hide': ((26, 230, 230), 'укрытие'),
          'knock': ((242, 38, 38), 'стук'), 'seat': ((153, 102, 255), 'сесть'), 'climb': ((153, 230, 77), 'лестница')}
    ent = [(c_, f'{t} — {kinds_s.get(k, 0)}') for k, (c_, t) in KC.items() if kinds_s.get(k)]
    e = sheet('Хижина лесника 1.1 · точки, коллайдеры, текстуры',
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
              [('Точки', 'те же, что в 1.0; у двери сдвинулись вместе с ней — скоба и ручка (Hand_Door_Out / _In), звук петель '
                         '(Audio_Door), точка стука (Knock_Door); у топора — вместе с колодой (Hand_Axe)'),
               ('Коллайдеры', 'те же коробки, что в 1.0; по новой двери — стены у проёма (Wall_F_L, Wall_F_R, Wall_F_Head) и '
                              'полотно (Door, едет с IX_HutDoor_1); по новым местам — лавка (Bench) и колода (Block)'),
               ('Unity', 'система координат префаба TowerHut: x — вправо, если смотреть на дверь, y — внутрь, z — вверх; '
                         'позиция в Unity (−x, z, −y), угол → −угол; подробности — HUT_V11_CONTRACT.md')],
              'hut_E.jpg', cols=2)
    print(a, e)
