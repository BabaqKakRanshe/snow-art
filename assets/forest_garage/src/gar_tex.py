"""Panel atlas of the garage (512 x 512, pixel art, point-filtered): the signs, labels and papers of the stand-alone garage
in the main building's panel style (main_tex's drawing, the project's pixel font); German first, English under it on the
wall signs, the equipment labels in English.
  from main_tex (the same pixels): garage (the GARAGE plate over the gate), befugt (the side door), brand (over the drums),
          pic_ext (F001 over the extinguisher), pic_nosmoke (P002 by the drums), calendar (October 2026, 1-16 crossed, as
          at the hut, the checkpoint and the main building), paper_a (the clipboard on the pegboard)
  new     ausfahrt (AUSFAHRT FREIHALTEN / KEEP EXIT CLEAR, on the gate leaf), rauchen (RAUCHEN VERBOTEN / NO SMOKING),
          torzu (TOR NACH GEBRAUCH SCHLIESSEN / CLOSE THE GATE AFTER USE, inside by the gate), db_lbl (GARAGE DB, the
          sub-distribution board), pallet_lbl (MAX 4 x 200 L, the spill pallet's plate)
python3 gar_tex.py [out_dir] -> T_Gar_Panel_BaseColor.png, gar_panel_regions.json"""
import os, sys, json, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import main_tex as MT

N = 512
FROM_MAIN = ['garage', 'befugt', 'brand', 'pic_ext', 'pic_nosmoke', 'calendar', 'paper_a']
NEW = [('ausfahrt', 168, 72), ('rauchen', 150, 44), ('torzu', 236, 44), ('db_lbl', 96, 20), ('pallet_lbl', 72, 20)]
SIZES = [(n, MT.REG[n][2] - MT.REG[n][0], MT.REG[n][3] - MT.REG[n][1]) for n in FROM_MAIN] + NEW
REG = MT.pack(SIZES, n=N)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def build(out):
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='maintex_')
    pb, _ = MT.build(tmp)                                    # the main building's atlas, the same drawing code
    src = np.array(Image.open(pb).convert('RGB'))
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 128)
    for name in FROM_MAIN:
        x0, y0, x1, y1 = MT.REG[name]
        a0, b0, a1, b1 = REG[name]
        img[b0:b1, a0:a1] = src[y0:y1, x0:x1]
    r = REG['ausfahrt']                                      # white plate, red rim, the no-stopping disc on the left
    MT._plate(img, r, MT.WHITE, MT.RED, 2)
    x0, y0, x1, y1 = r
    cx, cy = x0 + 34, (y0 + y1) / 2
    F.disc(img, cx, cy, 24, (40, 70, 150))                   # Z 283: blue disc, red ring, the red cross
    F.ring(img, cx, cy, 20, 26, MT.RED)
    F.line(img, cx - 15, cy - 15, cx + 15, cy + 15, MT.RED, 5)
    F.line(img, cx - 15, cy + 15, cx + 15, cy - 15, MT.RED, 5)
    rt = (x0 + 64, y0 + 4, x1 - 4, y1 - 4)
    F.text(img, (rt[0] + rt[2]) / 2, y0 + 16, 'AUSFAHRT', F.F57, MT.INK, scale=2)
    F.text(img, (rt[0] + rt[2]) / 2, y0 + 36, 'FREIHALTEN', F.F57, MT.INK)
    F.text(img, (rt[0] + rt[2]) / 2, y0 + 54, 'KEEP EXIT CLEAR', F.F35, MT.GREY_T)
    MT._age(img, r, 211, 30, 0.22)
    r = REG['rauchen']
    MT._plate(img, r, MT.WHITE, MT.RED)
    MT._two(img, r, 'RAUCHEN VERBOTEN', 'NO SMOKING', MT.RED, MT.RED_D)
    MT._age(img, r, 212, 20, 0.2)
    r = REG['torzu']
    MT._plate(img, r, (228, 226, 218), MT.INK)
    MT._two(img, r, 'TOR NACH GEBRAUCH SCHLIESSEN', 'CLOSE THE GATE AFTER USE', MT.INK, MT.GREY_T)
    MT._age(img, r, 213, 26, 0.2)
    r = REG['db_lbl']                                        # equipment label: engraved white-on-black
    MT._plate(img, r, (24, 24, 24), (200, 200, 196))
    F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'GARAGE DB', F.F57, (236, 236, 232))
    r = REG['pallet_lbl']
    MT._plate(img, r, (226, 182, 30), MT.INK)
    F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'MAX 4x200 L', F.F35, MT.INK)
    p = os.path.join(out, 'T_Gar_Panel_BaseColor.png')
    Image.fromarray(img, 'RGB').save(p)
    json.dump({k: list(v) for k, v in REG.items()}, open(os.path.join(out, 'gar_panel_regions.json'), 'w'), indent=0)
    return p


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'garage')
    print(build(o))
