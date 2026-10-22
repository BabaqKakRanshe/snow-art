"""Compose a turnaround sheet from renders. usage: python3 sheet.py <prefix> <out.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont
P, OUT = sys.argv[1], sys.argv[2]
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
W, H = 2400, 1640
bg = (26, 26, 28)
S = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(S)
fT, fS, fL = ImageFont.truetype(FB, 58), ImageFont.truetype(FR, 22), ImageFont.truetype(FR, 20)
d.text((40, 30), 'UTILITY PLANE  /  UNITY READY', font=fT, fill=(205, 205, 205))
d.text((42, 102), 'STOL TURBOPROP  ·  1:1 METERS  ·  +Z FORWARD  ·  +Y UP', font=fS, fill=(140, 140, 140))


def put(name, box, label=None, crop=None):
    im = Image.open(f'{P}_{name}.png').convert('RGB')
    if crop:
        im = im.crop(crop)
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    r = min(bw / im.width, bh / im.height)
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    S.paste(im, (x0 + (bw - im.width) // 2, y0 + (bh - im.height) // 2))
    if label:
        tw = d.textlength(label, font=fL)
        d.text((x0 + (bw - tw) / 2, y1 + 6), label, font=fL, fill=(150, 150, 150))


put('hero', (380, 140, 2020, 1000))
spec = ['SPAN      14.2 m', 'LENGTH    10.15 m', 'HEIGHT    3.95 m', 'TRIS      ~21k', '',
        'MATERIALS 3', ' Airframe 4096²', ' Details  2048²', ' Lights   emissive', '',
        'PBR  BaseColor', '     Normal (GL)', '     MetallicSmooth', '     AO / HDRP Mask']
for i, s in enumerate(spec):
    d.text((40, 200 + i * 30), s, font=fL, fill=(150, 150, 150))
parts = ['ANIMATED PIVOTS', '', 'Propeller     Z', 'Wheel_L/R     X', 'TailWheel     X', 'TailWheel_Fork Y',
         'Rudder        Y', 'Elevator_L/R  X', 'Aileron_L/R   X', 'Flap_L/R      X', 'CargoDoor     Y']
for i, s in enumerate(parts):
    d.text((2050, 200 + i * 30), s, font=fL, fill=(150, 150, 150))
d.line((30, 1010, W - 30, 1010), fill=(60, 60, 62), width=2)
row = [('front', 'FRONT'), ('left', 'LEFT'), ('right', 'RIGHT'), ('rear', 'REAR')]
for i, (n, l) in enumerate(row):
    put(n, (30 + i * 590, 1020, 30 + (i + 1) * 590 - 10, 1300), l)
d.line((30, 1340, W - 30, 1340), fill=(60, 60, 62), width=2)
put('top', (30, 1350, 480, 1600), 'TOP')
put('bottom', (490, 1350, 940, 1600), 'BOTTOM')
put('engine', (960, 1350, 1430, 1600), 'ENGINE / PROPELLER')
put('cargo', (1440, 1350, 1910, 1600), 'CARGO BAY')
put('gear', (1920, 1350, 2370, 1600), 'LANDING GEAR')
S.save(OUT)
print('sheet', OUT)
