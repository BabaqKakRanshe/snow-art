"""Sheet of the Cycles previews: rend/bunker/*.png -> rend/bunker/forest_bunker_A.jpg   python3 bunker_sheet.py"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
TITLE = 'forest_bunker 1.0 — бункер под озером: ангар с самолётом под брезентом, дверь вниз, вход с люком подо льдом'
CELLS = [('hangar', 'BunkerHangar — ангар в берегу с озера, ворота закрыты (TOR FREIHALTEN / KEEP CLEAR)'),
         ('hangar_open', 'в сумерки: ворота откатаны, лампы горят, внутри самолёт под брезентом, в глубине — дверь вниз'),
         ('hangar_in', 'внутри к воротам: UtilityPlane на Slot_Plane под PlaneTarp, справа дверь NOTAUSGANG на площадке'),
         ('vest', 'BlastDoor — тамбур и круглая дверь (заперта до акта 3), мокрые следы к ней, пульт'),
         ('door_open', 'акт 3: засовы втянуты, створка открыта, за ней первые ступени вниз (Link_Down)'),
         ('entr', 'BunkerEntrance — бетонный спуск у кисти: ступени, перила, навес'),
         ('entr_hatch', 'внизу люк подо льдом: три куска льда над ним сбиваются'),
         ('entr_open', 'лёд сбит, люк открыт: шахта с лестницей (Link_Shaft у её низа)')]


def make():
    R = os.path.join(HERE, 'rend', 'bunker')
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
    p = os.path.join(R, 'forest_bunker_A.jpg')
    sheet.save(p, quality=90)
    print(p, sheet.size)


if __name__ == '__main__':
    make()
