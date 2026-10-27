"""Sheets of the Cycles previews: rend/rocks/*.png -> rend/rocks/forest_rocks_A.jpg, rend/trash/*.png -> rend/trash/forest_trash_A.jpg
python3 rocks_trash_sheets.py [rocks|trash]"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
SHEETS = {
    'rocks': ('forest_rocks_A.jpg', 'forest_rocks 1.0 — камни, валуны и скалы Forest (гранит, как останцы Гарца)', [
        ('stones', 'ForestStone_1…6: булыжник, обломок, плита, клин, три камня, большой во мху'),
        ('boulders', 'ForestBoulder_1…3: круглый, расколотый, плоская глыба'),
        ('cliff_1', 'ForestCliff_1 — скальная стенка, ~10 м, высота 4,5 м'),
        ('cliff_2', 'ForestCliff_2 — останец, высота 6,3 м'),
        ('cliff_3', 'ForestCliff_3 — уступ с нависающей плитой'),
        ('scene', 'Пример расстановки: останец, валуны и камни вокруг')]),
    'trash': ('forest_trash_A.jpg', 'forest_trash 1.0 — мусор: куча на земле и спрессованный ком в руках', [
        ('paper', 'Paper — бумага и картон'), ('plastic', 'Plastic — пластик'), ('metal', 'Metal — металл'),
        ('wood', 'Wood — дерево'), ('glass', 'Glass — стекло'), ('mixed', 'Mixed — бытовой')]),
}


def make(key):
    out, title, cells = SHEETS[key]
    R = os.path.join(HERE, 'rend', key)
    ims = [Image.open(os.path.join(R, n + '.png')).convert('RGB') for n, _ in cells]
    W, H = ims[0].size
    CAP, PAD = 34, 10
    sheet = Image.new('RGB', (2 * W + 3 * PAD, 3 * (H + CAP) + 4 * PAD + 44), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), title, font=FB, fill=(235, 235, 235))
    for i, ((n, cap), im) in enumerate(zip(cells, ims)):
        x = PAD + (i % 2) * (W + PAD)
        y = 44 + PAD + (i // 2) * (H + CAP + PAD)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + H + 7), cap, font=F, fill=(220, 220, 220))
    p = os.path.join(R, out)
    sheet.save(p, quality=90)
    print(p, sheet.size)


for k in (sys.argv[1:] or SHEETS):
    make(k)
