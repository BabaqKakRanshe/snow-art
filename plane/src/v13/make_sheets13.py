"""Preview sheets and the door GIF for the v13 delivery.
python3 make_sheets13.py <out_dir>"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
P = '/home/claude/plane/v13/prev'
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
BG = (24, 26, 30)


def label(im, text, xy=(12, 10), font=F):
    d = ImageDraw.Draw(im)
    x, y = xy
    w = d.textlength(text, font=font)
    d.rectangle([x - 6, y - 4, x + w + 6, y + font.size + 6], fill=(0, 0, 0))
    d.text((x, y), text, fill=(255, 255, 255), font=font)


# ---------------------------------------------------------------- A: fixtures before / after
VIEWS = [('beacon_top', 'Верхний маяк: обтекатель киля + фланец'), ('beacon_bottom', 'Нижний маяк: накладка днища + фланец'),
         ('wingtip_L', 'Законцовка слева: АНО + строб в корпусе'), ('wingtip_R', 'Законцовка справа'),
         ('tail', 'Хвостовой огонь: бобышка'), ('landing', 'Фара: колпак по передней кромке')]
W, H = 600, 400
sheet = Image.new('RGB', (2 * W + 30, len(VIEWS) * (H + 10) + 70), BG)
d = ImageDraw.Draw(sheet)
d.text((10, 16), 'v12 (было)', fill=(230, 230, 230), font=FB)
d.text((W + 20, 16), 'v13 (стало)', fill=(230, 230, 230), font=FB)
for i, (v, t) in enumerate(VIEWS):
    y = 60 + i * (H + 10)
    for j, folder in enumerate(('old', 'c')):
        p = os.path.join(P, folder, v + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
        if j == 1:
            label(im, t)
        sheet.paste(im, (10 + j * (W + 10), y))
sheet.save(os.path.join(OUT, 'sheet_A_v13_light_fixtures.jpg'), quality=90)

# ---------------------------------------------------------------- B: door motion, two views
TS = [(0, '0 — закрыта'), (12, '0.12 — выходит передняя кромка'), (25, '0.25 — вся дверь в 14 см от борта'),
      (60, '0.6 — едет назад'), (100, '1 — открыта, задняя кромка у сужения борта')]
W, H, CAP = 560, 373, 40
sheet = Image.new('RGB', (2 * W + 30, len(TS) * (H + CAP + 10) + 70), BG)
d = ImageDraw.Draw(sheet)
d.text((10, 16), 'Сбоку', fill=(230, 230, 230), font=FB)
d.text((W + 20, 16), 'Сзади-сбоку', fill=(230, 230, 230), font=FB)
for i, (t, txt) in enumerate(TS):
    y = 60 + i * (H + CAP + 10)
    d.text((12, y + 6), 'cargoDoorL = ' + txt, fill=(255, 255, 255), font=F)
    for j, v in enumerate(('door_side', 'door_rear')):
        p = os.path.join(P, 'c', f'{v}_t{t:03d}.png')
        im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
        sheet.paste(im, (10 + j * (W + 10), y + CAP))
sheet.save(os.path.join(OUT, 'sheet_B_v13_sliding_door.jpg'), quality=90)

# ---------------------------------------------------------------- C: from inside (closed / half / open)
ims = []
for t in (0, 25, 100):
    p = os.path.join(P, 'c', f'door_inside_t{t:03d}.png')
    if os.path.exists(p):
        ims.append(Image.open(p).convert('RGB').resize((600, 400), Image.LANCZOS))
if ims:
    sheet = Image.new('RGB', (len(ims) * 610 + 10, 420), BG)
    for k, im in enumerate(ims):
        label(im, ('закрыта', 'вышла наружу', 'открыта')[k])
        sheet.paste(im, (10 + k * 610, 10))
    sheet.save(os.path.join(OUT, 'sheet_C_v13_door_inside.jpg'), quality=90)

# ---------------------------------------------------------------- GIF: door_rear sequence, open then close
seq = sorted(f for f in os.listdir(os.path.join(P, 'seq')) if f.endswith('.png'))
if seq:
    frames = [Image.open(os.path.join(P, 'seq', f)).convert('RGB') for f in seq]
    pal = [f.quantize(colors=192, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    loop = pal + pal[-2:0:-1]
    n = len(pal)
    dur = [900] + [120] * (n - 2) + [1200] + [120] * (n - 2)
    loop[0].save(os.path.join(OUT, 'door_slide_v13.gif'), save_all=True, append_images=loop[1:], duration=dur, loop=0,
                 optimize=True)
print('sheets written to', OUT, sorted(os.listdir(OUT)))
