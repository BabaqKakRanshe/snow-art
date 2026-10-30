"""before / after sheets: one per view (before above after) + the plan side by side;
python3 -I make_compare.py <before dir> <after dir> <out dir>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

B, A, O = sys.argv[1:4]
os.makedirs(O, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
Fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
NAMES = {'L01_start_arrive': 'подъезд к посту (L01_start_arrive)',
         'L01_start_booth': 'с площадки на пост (L01_start_booth)',
         'spawn': 'место появления, лицом к посту',
         'start_air': 'сверху, 17 м',
         'plan': 'план поста, сетка 5 м (u поперёк дороги, v вдоль)'}
OUT = {'L01_start_arrive': 'start_arrive', 'L01_start_booth': 'start_booth', 'spawn': 'start_spawn', 'start_air': 'start_air', 'plan': 'start_plan'}


def label(im, text, sub):
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=F) + d.textlength('   ' + sub, font=Fs) + 36
    d.rectangle([0, 0, w, 50], fill=(18, 20, 24))
    d.text((14, 8), text, font=F, fill=(255, 214, 90) if text == 'СТАЛО' else (235, 235, 235))
    d.text((24 + d.textlength(text, font=F), 15), sub, font=Fs, fill=(200, 200, 200))


for v in NAMES:
    pb, pa = os.path.join(B, v + '.png'), os.path.join(A, v + '.png')
    if not (os.path.exists(pb) and os.path.exists(pa)):
        continue
    b, a = Image.open(pb).convert('RGB'), Image.open(pa).convert('RGB')
    W, H = b.size
    if v == 'plan':
        sheet = Image.new('RGB', (W * 2 + 8, H), (18, 20, 24))
        label(b, 'БЫЛО', NAMES[v]); label(a, 'СТАЛО', '')
        sheet.paste(b, (0, 0)); sheet.paste(a, (W + 8, 0))
    else:
        sheet = Image.new('RGB', (W, H * 2 + 8), (18, 20, 24))
        label(b, 'БЫЛО', NAMES[v]); label(a, 'СТАЛО', '')
        sheet.paste(b, (0, 0)); sheet.paste(a, (0, H + 8))
    sheet.save(os.path.join(O, OUT[v] + '.jpg'), quality=90)
    print('sheet', v)
