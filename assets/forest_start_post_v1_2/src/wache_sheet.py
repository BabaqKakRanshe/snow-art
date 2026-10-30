"""2 x 3 sheet of the guard house's renders with Russian captions -> rend/wache_sheet.jpg"""
import os
from PIL import Image, ImageDraw, ImageFont

R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rend')
ITEMS = [('wache_front.png', 'Спереди: большое окно к шлагбауму, табличка ZUFAHRT SPERRGEBIET (Booth_Sign будки)'),
         ('wache_road.png', 'Со стороны дороги: дверь будки IX_Door в проёме, лампа Lamp_Booth над ней, ступени'),
         ('wache_back.png', 'Сзади: труба печки, зелень на северной стене, штукатурка отвалилась до кирпича'),
         ('wache_inside.png', 'Внутри: стол под окном (Slot_Table_1..3), радио, койка (Spot_Bunk), плафон'),
         ('wache_stove.png', 'Печь с огнём в щели (Glow_Stove), полка (Slot_Shelf), календарь 1991'),
         ('wache_night.png', 'Ночь: свет внутри и лампа над дверью')]
W, H = 1100, 700
CAP = 44
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
S = Image.new('RGB', (W * 2 + 30, 60 + (H + CAP + 10) * 3 + 10), (24, 26, 30))
d = ImageDraw.Draw(S)
d.text((12, 14), 'StartWache 1.2 — домик охраны поста в стиле проекта (snow_style, атлас 1024, 51,3 px/м)', fill=(236, 236, 232), font=title)
for i, (f, cap) in enumerate(ITEMS):
    im = Image.open(os.path.join(R, f)).convert('RGB').resize((W, H))
    x, y = 10 + (i % 2) * (W + 10), 60 + (i // 2) * (H + CAP + 10)
    S.paste(im, (x, y))
    d.text((x + 6, y + H + 10), cap, fill=(220, 220, 214), font=font)
S.save(os.path.join(R, 'wache_sheet.jpg'), quality=86)
print(os.path.join(R, 'wache_sheet.jpg'))
