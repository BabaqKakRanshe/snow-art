"""far 1.1: sheet F (Update 3 vs now) needs Update 3's renders and previews, which live outside the package - so 1.1 swaps
only the one tile that changed, 'теперь: метеостанция' (rend/far/cmp_meteo.png), into 1.0's sheet, laid out exactly as
make_sheets_far / make_sheets_main.sheet place it (checked against 1.0's own tile first).
python3 patch_sheet_f11.py <far_F 1.0 jpg> <cmp_meteo 1.0 png> -> sheets/far_F_u3_vs_now.jpg"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
old_sheet, old_tile = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], os.path.join(HERE, 'sheets')]             # make_sheets_main reads its out_dir on import
import make_sheets_main as MSM
SUB = ('Слева — модели обновления 3 (FBX в цветах материалов) и его превью карты, справа — перестроенные с тех же '
       'камер; места, размеры, пивоты дверей и огни — те же')
W, H, g, cols, idx = 900, 600, 16, 2, 11                     # the 12th tile: cmp_meteo, 'теперь: метеостанция'
S = Image.open(old_sheet).convert('RGB')
d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
top = 130 + 32 * (len(MSM.wrap(d, SUB, MSM.F(25), cols * W + (cols - 1) * g)) - 1)
x, y = g + (idx % cols) * (W + g), top + (idx // cols) * (H + g)


def tile(path):
    im = MSM.fit(Image.open(path).convert('RGB'))
    MSM.tag_wrap(im, 'теперь: метеостанция')
    return im


ref = np.asarray(tile(old_tile), np.float32)
got = np.asarray(S.crop((x, y, x + W, y + H)), np.float32)
err = float(np.abs(ref - got).mean())
print('1.0 tile vs sheet: mean abs diff', round(err, 2))
assert err < 4.0, 'layout mismatch'
S.paste(tile(os.path.join(HERE, 'rend', 'far', 'cmp_meteo.png')), (x, y))
os.makedirs(os.path.join(HERE, 'sheets'), exist_ok=True)
p = os.path.join(HERE, 'sheets', 'far_F_u3_vs_now.jpg')
S.save(p, quality=92)
print(p, S.size)
