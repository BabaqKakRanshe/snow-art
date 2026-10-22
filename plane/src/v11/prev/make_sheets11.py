"""v11 preview sheets (v10 vs v11 lighting, same cameras) -> export/unity_v11/previews/sheet_*_v11_*.jpg"""
import os
from PIL import Image, ImageDraw, ImageFont
R = '/home/claude/plane/v11/prev/r/'
OUT = '/home/claude/plane/export/unity_v11/previews/'
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
BG = (245, 245, 243)


def label(im, text, xy=(10, 8)):
    d = ImageDraw.Draw(im)
    l, t, r, b = d.textbbox(xy, text, font=F)
    d.rectangle((l - 6, t - 4, r + 6, b + 4), fill=(20, 20, 20))
    d.text(xy, text, font=F, fill=(255, 255, 255))


def tile(name, text):
    im = Image.open(R + name + '.png').convert('RGB')
    label(im, text)
    return im


def sheet(title, rows, out, gap=8, note=None):
    W = max(sum(t.width for t in r) + gap * (len(r) - 1) for r in rows)
    top = 60 + (34 if note else 0)
    H = top + sum(max(t.height for t in r) for r in rows) + gap * (len(rows) - 1)
    s = Image.new('RGB', (W + 2 * gap, H + gap), BG)
    d = ImageDraw.Draw(s)
    for size in range(30, 15, -1):
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        if d.textlength(title, font=fb) <= s.width - 2 * (gap + 4):
            break
    d.text((gap + 4, 12 + (30 - size) // 2), title, font=fb, fill=(30, 30, 30))
    if note:
        fn = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
        d.text((gap + 4, 58), note, font=fn, fill=(60, 60, 60))
    y = top
    for r in rows:
        x = gap
        for t in r:
            s.paste(t, (x, y))
            x += t.width + gap
        y += max(t.height for t in r) + gap
    s.save(out, quality=90, optimize=True)
    print(os.path.basename(out), s.size, round(os.path.getsize(out) / 1e6, 2), 'MB')


NOTE = 'Ночь, снег, туман exp² 0.02, atmosphere 0.35, Bloom 0.25 (как в профиле ПК). Расчёт по модели света URP, тени — как в Unity при shadowQuality Medium.'
pair = lambda v, a, b: [tile('v10_' + v, 'v10 — ' + a), tile('v11_' + v, 'v11 — ' + b)]
sheet('Utility Plane v10 → v11: свет снаружи', [
    pair('ext_front', 'точечные огни, фара смотрит вверх', 'фара: луч, пятно на снегу, тень человека'),
    pair('ext_rear', 'красное и белое пятна под хвостом', 'маяк и хвостовой огонь, ореолы в дымке'),
    pair('ext_far', '50 м: самолёт почти не виден', '50 м: зелёный АНО, луч фары, человек в луче'),
], OUT + 'sheet_A_v11_exterior.jpg', note=NOTE)
sheet('Utility Plane v10 → v11: свет в кабине и отсеке', [
    pair('int_pilot', 'из глаза пилота: заливка оранжевая, ровная', 'две красные заливки из плафонов у козырька, тени штурвалов'),
    pair('int_bay', 'точечные лампы светят сквозь стены', 'люминесцентная трубка вниз + отражённый свет, тени'),
], OUT + 'sheet_B_v11_interior.jpg', note='Все огни и плафоны включены на 100 %, panelLight 1, floodLight 1. Кабина — из глаза пилота (Socket_PilotEye). Через окна отсека — красный маяк на снегу.')
sheet('Utility Plane v11: плотность воздуха и вспышка строба', [
    [tile('v11_ext_front_atm0', 'atmosphere 0 — ясная ночь: только пятна света'), tile('v11_ext_front', 'atmosphere 0.35 — дымка')],
    [tile('v11_ext_front_atm1', 'atmosphere 1 — метель'), tile('v11_ext_front_strobe', 'кадр вспышки строба (0.35)')],
], OUT + 'sheet_C_v11_atmosphere.jpg', note='Поле atmosphere (или туман сцены: atmosphereFromSceneFog) задаёт ореолы и лучи; свет на поверхностях от него не зависит.')
