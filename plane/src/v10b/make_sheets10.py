"""v10 preview sheets (v9 vs v10, same cameras) -> r/fin/sheet_*_v10_*.jpg"""
import os
from PIL import Image, ImageDraw, ImageFont
S = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/'
R, W2D = S + 'r/', S + 'vis2/'
OUT = R + 'fin/'
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
BG = (245, 245, 243)


def label(im, text, xy=(10, 8)):
    d = ImageDraw.Draw(im)
    x, y = xy
    l, t, r, b = d.textbbox((x, y), text, font=F)
    d.rectangle((l - 6, t - 4, r + 6, b + 4), fill=(20, 20, 20))
    d.text((x, y), text, font=F, fill=(255, 255, 255))


def tile(path, w, h=None, crop=None, text=None, nearest=False):
    im = Image.open(path).convert('RGB')
    if crop:
        im = im.crop(crop)
    if h is None:
        h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.NEAREST if nearest else Image.LANCZOS)
    if text:
        label(im, text)
    return im


def sheet(title, rows, out, gap=8):
    W = max(sum(t.width for t in r) + gap * (len(r) - 1) for r in rows)
    H = 60 + sum(max(t.height for t in r) for r in rows) + gap * (len(rows) - 1)
    s = Image.new('RGB', (W + 2 * gap, H + gap), BG)
    d = ImageDraw.Draw(s)
    for size in range(30, 15, -1):
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        if d.textlength(title, font=fb) <= s.width - 2 * (gap + 4):
            break
    assert d.textlength(title, font=fb) <= s.width - 2 * (gap + 4), title
    d.text((gap + 4, 12 + (30 - size) // 2), title, font=fb, fill=(30, 30, 30))
    y = 60
    for r in rows:
        x = gap
        for t in r:
            s.paste(t, (x, y))
            x += t.width + gap
        y += max(t.height for t in r) + gap
    s.save(out, quality=88, optimize=True)
    print(os.path.basename(out), s.size, 'title px', size, round(os.path.getsize(out) / 1e6, 2), 'MB')


W2, H2 = 760, 486
pair = lambda v, cap: [tile(R + f'v9_{v}.png', W2, H2, text=f'v9 — {cap}'), tile(R + f'v10_{v}.png', W2, H2, text=f'v10 — {cap}')]
# A: cockpit
rows = [pair('p_fwd', 'кресло пилота, вперёд'), pair('p_down', 'вниз: педали, пульт, дверь'), pair('p_right', 'вправо')]
rows.append([tile(R + 'v9_p_fwd.png', W2, H2, crop=(330, 300, 650, 505), text='v9 вблизи: шкалы 4096', nearest=False),
             tile(R + 'v10_p_fwd.png', W2, H2, crop=(330, 300, 650, 505), text='v10 вблизи: шкалы 2048', nearest=False)])
rows.append([tile(W2D + 'wire_v9_pfwd.png', W2, H2, crop=(250, 320, 750, 640), text='v9: сетка доски'),
             tile(W2D + 'wire_v10_pfwd.png', W2, H2, crop=(250, 320, 750, 640), text='v10: та же форма, меньше треугольников')])
sheet('Utility Plane: v9 → v10 — кабина: вид тот же, треугольников меньше; текстуры интерьера 1024 (были 4096)', rows,
      OUT + 'sheet_A_v10_cockpit.jpg')
# B: bay
rows = [pair('bay_fwd', 'отсек, вперёд'), pair('seatL1', 'кресло L1'), pair('bay_low', 'отсек присев'), pair('door_in', 'в дверь пилота снаружи'),
        [tile(W2D + 'wire_v9_bay.png', W2, H2, text='v9: сетка отсека'), tile(W2D + 'wire_v10_bay.png', W2, H2, text='v10: сетка отсека')]]
sheet('Utility Plane: v9 → v10 — грузовой отсек: вид тот же (текстуры мягче вблизи), треугольников меньше', rows,
      OUT + 'sheet_B_v10_bay.jpg')
# C: exterior
rows = [pair('x_front34', 'общий вид'), pair('wheel', 'колесо, подкос'), pair('dorsal_rear34', 'форкиль, киль'),
        [tile(W2D + 'wire_v9_x.png', W2, H2, text='v9: сетка'), tile(W2D + 'wire_v10_x.png', W2, H2, text='v10: сетка')]]
sheet('Utility Plane: v9 → v10 — экстерьер: PSX-текстуры и вид те же, треугольников меньше', rows, OUT + 'sheet_C_v10_exterior.jpg')
