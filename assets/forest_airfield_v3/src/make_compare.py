"""before / after sheets for the airfield: one per view (before above after) + the plan side by side
python3 -I make_compare.py <before dir> <after dir> <out dir>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

B, A, O = sys.argv[1:4]
os.makedirs(O, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
Fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
NAMES = {'af_north': 'с северного торца вдоль полосы',
         'af_mid': 'середина полосы, взгляд на запад: коридор и откос',
         'af_hangar': 'перед ангаром',
         'af_pad': 'южный конец: площадка для разворота',
         'af_south': 'с южного въезда на полосу',
         'af_air': 'сверху с запада, 55 м',
         'af_app': 'заход на посадку с юга, 250 м до торца',
         'plan': 'план'}
OUT = {k: k for k in NAMES}


def label(im, text, sub):
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=F) + (d.textlength('   ' + sub, font=Fs) if sub else 0) + 36
    d.rectangle([0, 0, w, 50], fill=(18, 20, 24))
    d.text((14, 8), text, font=F, fill=(255, 214, 90) if text == 'СТАЛО' else (235, 235, 235))
    if sub:
        d.text((24 + d.textlength(text, font=F), 15), sub, font=Fs, fill=(200, 200, 200))


for v in NAMES:
    pb, pa = os.path.join(B, v + '.png'), os.path.join(A, v + '.png')
    if not (os.path.exists(pb) and os.path.exists(pa)):
        continue
    b, a = Image.open(pb).convert('RGB'), Image.open(pa).convert('RGB')
    W, H = b.size
    if v == 'plan':
        sheet = Image.new('RGB', (W * 2 + 8, H), (18, 20, 24))
        label(b, 'БЫЛО', ''); label(a, 'СТАЛО', '')
        sheet.paste(b, (0, 0)); sheet.paste(a, (W + 8, 0))
    else:
        sheet = Image.new('RGB', (W, H * 2 + 8), (18, 20, 24))
        label(b, 'БЫЛО', NAMES[v]); label(a, 'СТАЛО', '')
        sheet.paste(b, (0, 0)); sheet.paste(a, (0, H + 8))
    sheet.save(os.path.join(O, 'airfield_' + OUT[v] + '.jpg'), quality=90)
    print('sheet', v)
