"""Sheet of the Cycles previews: rend/sky/*.png -> rend/sky/sky_systems_A.jpg   python3 sky_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = 'sky_systems 1.0 — системы высоты Небесного острова и мостки под ним'
CELLS = [('chiller', 'SkyChiller — холодильная установка: компрессор, ремни под кожухом, конденсатор; авария (FAULT, маяк)'),
         ('chiller_open', 'кожух ремней открыт: три клиновых ремня мотор → компрессор (их и меняют)'),
         ('sprayer', 'SkySprayer — распылитель костяной пыли: бункер с крышкой, питатель, воздуходувка, мачта с соплом'),
         ('ballast', 'SkyBallast — сброс балласта на краю: наклонная платформа, три блока по 3,5 т, пост с рычагом'),
         ('altimeter', 'SkyAltimeter — табло высоты у вышки в сумерки: прожекторы, лампы до отметки 1200 м'),
         ('walk', 'SkyWalk_* — мостки под островом: прямой, площадка, лестница, прямой; тросы к анкерам в скале'),
         ('walk_close', 'на мостках: решётчатый настил, перила с бортиком, фонарь на стойке')]


def make():
    R = os.path.join(HERE, 'rend', 'sky')
    ims = [Image.open(os.path.join(R, n + '.png')).convert('RGB') for n, _ in CELLS]
    W, H = ims[0].size
    CAP, PAD, rows = 34, 10, (len(CELLS) + 1) // 2
    sheet = Image.new('RGB', (2 * W + 3 * PAD, rows * (H + CAP) + (rows + 1) * PAD + 44), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), TITLE, font=FB, fill=(235, 235, 235))
    for i, ((n, cap), im) in enumerate(zip(CELLS, ims)):
        x = PAD + (i % 2) * (W + PAD)
        y = 44 + PAD + (i // 2) * (H + CAP + PAD)
        sheet.paste(im.resize((W, H)), (x, y))
        d.text((x + 4, y + H + 7), cap, font=F, fill=(220, 220, 220))
    p = os.path.join(R, 'sky_systems_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
