"""Sheet of the Cycles previews: rend/gear/*.png -> rend/gear/forest_gear_A.jpg   python3 gear_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = ('forest_gear 1.0 — батарейки, рация, фонари, тележка, волокуша, кукла с открыткой, лампочка, жетон, '
         'ключ Stationsleiter, ледоруб')
CELLS = [('cells', 'Item_Battery, Item_BatteryPack, Item_Battery6V — батарейка D, упаковка из четырёх, 6 В 4R25'),
         ('walkie', 'Item_Walkie — рация: ручки канала и громкости, PTT сбоку, дисплей горит'),
         ('lantern', 'Item_Lantern — фонарь 6 В с жёлтым стеклом, включён (ночь)'),
         ('lantern_battery', 'Item_Lantern — крышка сзади открыта, внутри Item_Battery6V (Slot_Battery)'),
         ('headlamp', 'Item_Headlamp — налобный фонарь, включён, лампа наклонена'),
         ('cart', 'Item_Cart — тележка: поворотные колёса у ручки'),
         ('sled', 'Item_Sled — волокуша, буксирная верёвка с ручкой (Sled_Tow)'),
         ('doll', 'Item_Doll и Item_Postcard — кукла и открытка'),
         ('doll_turn', 'Doll_Head — голова повёрнута (последний кадр демо)'),
         ('postcard', 'Item_Postcard — картинка и оборот: подпись «— K» без точки'),
         ('small', 'Item_Bulb, Item_BulbBox, Item_WorkerTag (жетон 3817), Item_Key_Stationsleiter'),
         ('iceaxe', 'Item_IceAxe — ледоруб')]


def make():
    R = os.path.join(HERE, 'rend', 'gear')
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
    p = os.path.join(R, 'forest_gear_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
