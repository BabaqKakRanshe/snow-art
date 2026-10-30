"""labels on the plan renders (runway frame, PX 2 px per metre, u -165..165, v -650..570)
python3 -I label_plan.py <before.png> <after.png> <out_before.png> <out_after.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont

U0, U1, V0, V1, PX = -165.0, 165.0, -650.0, 570.0, 2.0
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 19)
Fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)


def P(u, v):
    return ((u - U0) * PX, (V1 - v) * PX)


def mark(d, u, v, text, dx=12, dy=-12, anchor_left=True):
    x, y = P(u, v)
    d.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 70, 40), width=3)
    w = d.textlength(text, font=F)
    tx = x + dx if anchor_left else x - dx - w - 10
    d.rectangle([tx - 4, y + dy - 4, tx + w + 6, y + dy + 24], fill=(18, 20, 24))
    d.text((tx + 1, y + dy), text, font=F, fill=(255, 214, 90))


def ticks(d, im):
    W, H = im.size
    for v in range(-600, 571, 100):
        x0, y = P(U0, v)
        d.line([(0, y), (14, y)], fill=(255, 255, 255), width=2)
        d.text((18, y - 9), f'{v:+d} м', font=Fs, fill=(255, 255, 255))


def label(path_in, path_out, marks):
    im = Image.open(path_in).convert('RGB'); d = ImageDraw.Draw(im)
    ticks(d, im)
    for m in marks:
        mark(d, *m)
    im.save(path_out)


BEFORE = [(45, 200, 'ангар', 12, -12, False), (-36, -366, 'топливный склад', 12, -12, False),
          (0, 400, 'лес в 55 м за торцом', 12, -12, True), (0, -470, 'лес в 100 м за торцом', 12, -12, True),
          (0, -351, 'огни торца', 12, 8, True)]
AFTER = [(45, 200, 'ангар в холме, ящики, бочки', 12, -12, False), (-28.5, -393, 'бочки, генератор, шкаф у будки', 12, 10, True),
         (-57.5, -344, 'колдун', 12, -22, False), (0, 470, 'вырубка 165 м', 12, -12, True), (0, -540, 'вырубка 200 м', 12, -12, True),
         (0, -351, 'огни торца', 12, 8, True), (-58, 40, 'край леса 40–60 м от плит, подрост', 12, -12, True), (75, 0, 'откос 1:4', 12, -12, True),
         (-70, -200, 'насыпь 1:3', 12, -12, True), (15, -120, 'валы снега ~1 м', 12, -12, True)]

if __name__ == '__main__':
    bi, ai, bo, ao = sys.argv[1:5]
    label(bi, bo, BEFORE)
    label(ai, ao, AFTER)
