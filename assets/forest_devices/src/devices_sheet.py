"""Sheet of the Cycles previews: rend/devices/*.png -> rend/devices/forest_devices_A.jpg   python3 devices_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = 'forest_devices 1.0 — факс, компьютер, ноутбук, кассеты, магнитофон, ящик для кассет, метеобудка'
CELLS = [('fax', 'Fax — факс: START / STOP, дисплей, трубка на витом шнуре; FaxPaper — принятый факс'),
         ('pc', 'ObjectPC — компьютер, клавиатура, мышь; монитор — Kit_Monitor_CRT (snow_kit)'),
         ('laptop', 'Laptop — ноутбук, крышка IX_LaptopLid открыта'),
         ('tapes', 'Cassette — кассета телеметрии; CassetteBox — коробка на 10 кассет'),
         ('deck', 'TapeDeck — магнитофон TR-4 для шкафа антенны: дверца открыта, кассета внутри'),
         ('dropbox', 'DropBox — ящик для кассет у вертолётной площадки'),
         ('screen', 'MeteoScreen — метеобудка, дверца IX_ScreenDoor открыта'),
         ('screen_in', 'Внутри: сухой и смоченный, максимальный и минимальный термометры, термогигрограф')]


def make():
    R = os.path.join(HERE, 'rend', 'devices')
    ims = [Image.open(os.path.join(R, n + '.png')).convert('RGB') for n, _ in CELLS]
    W, H = ims[0].size
    CAP, PAD, rows = 34, 10, (len(CELLS) + 1) // 2
    sheet = Image.new('RGB', (2 * W + 3 * PAD, rows * (H + CAP) + (rows + 1) * PAD + 44), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), TITLE, font=FB, fill=(235, 235, 235))
    for i, ((n, cap), im) in enumerate(zip(CELLS, ims)):
        x = PAD + (i % 2) * (W + PAD)
        y = 44 + PAD + (i // 2) * (H + CAP + PAD)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + H + 7), cap, font=F, fill=(220, 220, 220))
    p = os.path.join(R, 'forest_devices_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
