"""Sheet of the Cycles previews: rend/world/*.png -> rend/world/forest_world_A.jpg   python3 world_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = ('forest_world 1.0 — бочка с огнём, наледь на антеннах, пещера Лесника, две брошенные машины, старый запасной фургон')
CELLS = [('barrel', 'FireBarrel — бочка с огнём, днём, холодная: дрова в ней, отверстия внизу'),
         ('barrel_night', 'ночью горит: M_World_Fire (8 кадров), M_World_Embers, свет Light_Fire'),
         ('shift', 'ShiftCar — машина прежней смены (anchors/Car_Parked), снег на ней — отдельная часть'),
         ('shift_rear', 'сзади: задняя дверь с запаской и водительская дверь открыты'),
         ('wreck', 'WreckCar — вторая брошенная машина: нет переднего правого колеса, стекло треснуло'),
         ('wreck_rear', 'сзади: багажник открыт, разбиты окно водителя и заднее правое'),
         ('cave', 'ForesterCave — пещера Лесника снаружи: гранитный выход, лаз'),
         ('cave_in', 'внутри при свечах: лежанка, свечи, мусор, газета 1991, вещи на Slot_Stash'),
         ('cave_key', 'гвоздь в стене с ключом Stationsleiter (Slot_Key) в луче фонаря'),
         ('ice_relay', 'Ice_RelayMast — наледь на мачте ретранслятора: панели и барабан сбиваются'),
         ('ice_dish', 'Ice_Dish_1 — наледь на антенне № 1: облучатель и снег в чаше сбиваются'),
         ('ice_roof', 'Ice_RoofMast — наледь на мачте на крыше корпуса (корпус серым) и тарелке'),
         ('van_old', 'старый запасной фургон: van3 в старом хаки, ржавый, без лебёдки')]


def make():
    R = os.path.join(HERE, 'rend', 'world')
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
    p = os.path.join(R, 'forest_world_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
