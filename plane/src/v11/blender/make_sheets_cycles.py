"""Sheets: Cycles (IES + light functions + volumetric fog) next to the URP previews (what Unity shows)."""
import os
from PIL import Image, ImageDraw, ImageFont
CY = '/home/claude/plane/v11/blender/r/'
URP = '/home/claude/plane/v11/prev/r/'
OUT = '/home/claude/plane/v11/deliv/previews/'
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
BG = (245, 245, 243)


def label(im, text, xy=(10, 8)):
    d = ImageDraw.Draw(im)
    l, t, r, b = d.textbbox(xy, text, font=F)
    d.rectangle((l - 6, t - 4, r + 6, b + 4), fill=(20, 20, 20))
    d.text(xy, text, font=F, fill=(255, 255, 255))


def tile(path, text):
    im = Image.open(path).convert('RGB')
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
        for size in range(18, 11, -1):
            fn = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
            if d.textlength(note, font=fn) <= s.width - 2 * (gap + 4):
                break
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


NOTE = 'Cycles: 128 сэмплов + OIDN, тот же bloom 0.25 и sRGB, что у URP-превью. Справа — как это покажет Unity (URP), те же камеры.'
pair = lambda v, a, b: [tile(CY + 'cy_' + v + '.png', 'Blender Cycles — ' + a), tile(URP + 'v11_' + v + '.png', 'Unity URP — ' + b)]
sheet('Utility Plane v11: IES и функции света в Blender (Cycles) рядом с Unity (URP)', [
    pair('ext_front', 'IES фары, объёмный туман с тенями', 'cookie + Airlight/Beam'),
    pair('ext_rear', 'маяк и хвостовой огонь по IES', 'то же в URP'),
    pair('ext_far', '50 м', '50 м'),
], OUT + 'sheet_D_v11_blender_exterior.jpg', note=NOTE)
sheet('Utility Plane v11: кабина и отсек в Blender (Cycles) рядом с Unity (URP)', [
    pair('int_pilot', 'из глаза пилота: плафоны заливки, IES', 'то же в URP'),
    pair('int_bay', 'трубка по IES, отражённый свет — Cycles', 'отражённый свет — Fill_Bay'),
], OUT + 'sheet_E_v11_blender_interior.jpg',
    note='Внутри кабины туман atmosphere 0.05 (в Cycles слой тумана заходит и в салон). Fill-источники в Cycles выключены: отражённый свет он считает сам.')
sheet('Utility Plane v11 в Blender (Cycles): плотность тумана и вспышка строба', [
    [tile(CY + 'cy_ext_front_atm0.png', 'atmosphere 0 — ясная ночь'), tile(CY + 'cy_ext_front.png', 'atmosphere 0.35 — дымка')],
    [tile(CY + 'cy_ext_front_atm1.png', 'atmosphere 1 — метель'), tile(CY + 'cy_ext_front_strobe.png', 'кадр вспышки строба (LF_Strobe)')],
], OUT + 'sheet_F_v11_blender_atmosphere.jpg',
    note='Рассеяние 0.034 × atmosphere на метр, слой 40 м. Сравнить с sheet_C_v11_atmosphere.jpg (URP).')
