"""Sheet of the Cycles previews: rend/parts/*.png -> rend/parts/forest_parts_A.jpg   python3 parts_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = ('forest_parts 1.0 — насос-дозатор, натриевая лампа, кинескоп радара, блок ретранслятора, резервный генератор, '
         'датчик у озера')
CELLS = [('pump', 'Item_DosingPump — насос-дозатор: бак, краны V1–V3, манометр, схема, накладная на баке'),
         ('pump_installed', 'установлен в насосной forest_far (placements): краны открыты, шланг к трубе'),
         ('lamp', 'Item_SodiumLamp и Item_SodiumLampBox — натриевая лампа 400 Вт E40, горелка горит'),
         ('crt', 'Item_RadarCRT — кинескоп радара: стоит на экране и лежит экраном вверх'),
         ('relay', 'Item_RelayUnit — блок RT-7: спереди (крышка предохранителя снята) и сзади'),
         ('gen', 'Item_BackupGenerator — резервный генератор 2,8 кВА'),
         ('sensor', 'LakeSensor — датчик у озера: столб, ящик, табличка, кабель к зонду в воде'),
         ('sensor_box', 'ящик открыт: регистратор и батарейка 6 В из forest_gear (Slot_Battery)')]


def make():
    R = os.path.join(HERE, 'rend', 'parts')
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
    p = os.path.join(R, 'forest_parts_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
