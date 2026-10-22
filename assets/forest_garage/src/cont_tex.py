"""Panel atlas of the generator container: the generator shed's atlas (gen_tex: dials, control panel, switchboard face,
card, stencils, lenses, log page) with circuit 8 renamed to CONTAINER, plus the container's bilingual wall signs
(German first, English under it) drawn into the free space of the same 512 x 512 sheet:
  csign_gen      STROMERZEUGER / GENERATOR plate on the south side wall
  csign_gen_door the same, smaller, on the active door leaf
  csign_danger   VORSICHT 400 V / DANGER 400 V warning triangle (passive leaf)
  csign_flame    KEIN OFFENES FEUER / NO NAKED FLAMES (inside, by the drums)
  csign_louvre   LUFTKLAPPE VOR START OEFFNEN / OPEN LOUVRE BEFORE START (inside, by the louvre lever)
  csign_noentry  ZUTRITT VERBOTEN / NO ENTRY (passive leaf)
Equipment labels (panel, board, card, stencils) stay English.  Umlaut glyphs (A, O, U with dots) are added to both
pixel fonts here.  python3 cont_tex.py [out_dir]  ->  T_GCont_Panel_BaseColor.png / _Emission.png"""
import os, sys, json, tempfile, shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import gen_tex as GT
import van2_tex as VT

GT.CIRCUITS[7] = 'CONTAINER'
GT.BOARD['circuits'][7] = 'CONT'

# umlauts: the dots replace the top row of the glyph
F.F35['glyphs']['Ä'] = F._compile({'x': '#.#|.#.|#.#|###|#.#'})['x']
F.F35['glyphs']['Ö'] = F._compile({'x': '#.#|...|###|#.#|###'})['x']
F.F35['glyphs']['Ü'] = F._compile({'x': '#.#|...|#.#|#.#|###'})['x']
F.F57['glyphs']['Ä'] = F._compile({'x': '.#.#.|.....|.###.|#...#|#####|#...#|#...#'})['x']
F.F57['glyphs']['Ö'] = F._compile({'x': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.'})['x']
F.F57['glyphs']['Ü'] = F._compile({'x': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})['x']

CREG = {
    'csign_gen': (160, 320, 336, 368), 'csign_gen_door': (336, 320, 428, 356), 'csign_danger': (428, 320, 492, 400),
    'csign_flame': (428, 400, 492, 464), 'csign_louvre': (112, 368, 240, 408), 'csign_noentry': (240, 368, 336, 408),
}
for _k, _r in CREG.items():
    for _o, _ro in GT.REG.items():                       # must not overlap the shed's regions
        assert _r[2] <= _ro[0] or _ro[2] <= _r[0] or _r[3] <= _ro[1] or _ro[3] <= _r[1], (_k, _o)
GT.REG.update(CREG)
N = GT.N
BLUE, BLUE_L, BLUE_D = (34, 62, 128), (70, 100, 160), (18, 34, 76)
WHITE, INK, RED, YEL = GT.WHITE, GT.INK, GT.RED, GT.YEL


def uv(name, n=N):
    return VT.uv(GT.REG[name], n)


def _two(img, r, de, en, col_de, col_en, font_de=F.F57, font_en=F.F35, gap=3):
    """German line over the English one, centred in region r"""
    hd, he = font_de['h'], font_en['h']
    cy = (r[1] + r[3]) / 2
    top = cy - (hd + gap + he) / 2
    F.text(img, (r[0] + r[2]) / 2, top + hd / 2, de, font_de, col_de)
    F.text(img, (r[0] + r[2]) / 2, top + hd + gap + he / 2, en, font_en, col_en)


def _triangle(img, cx, y0, h, fill, edge):
    for k in range(h):
        w = k * 0.58
        F.rect(img, cx - w, y0 + k, cx + w - 1, y0 + k, edge if (k > h - 4 or k < 4) else fill)
    for k in range(4, h - 3):
        w = k * 0.58
        F.rect(img, cx - w, y0 + k, cx - w + 2, y0 + k, edge)
        F.rect(img, cx + w - 3, y0 + k, cx + w - 1, y0 + k, edge)


def draw_container_signs(img):
    r = CREG['csign_gen']                                              # blue enamel plate, white letters, frame
    GT._plate(img, r, BLUE, BLUE_L, BLUE_D)
    F.frame(img, r[0] + 3, r[1] + 3, r[2] - 4, r[3] - 4, WHITE)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 17, 'STROMERZEUGER', F.F57, WHITE, scale=2)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 35, 'GENERATOR', F.F57, (200, 210, 230))
    r = CREG['csign_gen_door']
    GT._plate(img, r, BLUE, BLUE_L, BLUE_D)
    F.frame(img, r[0] + 2, r[1] + 2, r[2] - 3, r[3] - 3, WHITE)
    _two(img, r, 'STROMERZEUGER', 'GENERATOR', WHITE, (200, 210, 230))
    r = CREG['csign_danger']                                           # yellow triangle with the flash, two lines under it
    F.rect(img, r[0], r[1], r[2] - 1, r[3] - 1, (236, 232, 220))
    cx = (r[0] + r[2]) / 2
    _triangle(img, cx, r[1] + 5, 36, YEL, (20, 20, 20))
    F.line(img, cx + 3, r[1] + 15, cx - 3, r[1] + 27, (20, 20, 20), 2)
    F.line(img, cx - 3, r[1] + 27, cx + 3, r[1] + 27, (20, 20, 20), 2)
    F.line(img, cx + 3, r[1] + 27, cx - 2, r[1] + 37, (20, 20, 20), 2)
    F.text(img, cx, r[1] + 50, 'VORSICHT', F.F35, RED)
    F.text(img, cx, r[1] + 57, '400 VOLT', F.F35, INK)
    F.rect(img, r[0] + 6, r[1] + 62, r[2] - 7, r[1] + 62, (160, 156, 146))
    F.text(img, cx, r[1] + 68, 'DANGER', F.F35, RED)
    F.text(img, cx, r[1] + 75, '400 VOLTS', F.F35, INK)
    r = CREG['csign_flame']                                            # prohibition: a crossed-out flame
    F.rect(img, r[0], r[1], r[2] - 1, r[3] - 1, (236, 232, 220))
    F.frame(img, r[0], r[1], r[2] - 1, r[3] - 1, RED)
    cx = (r[0] + r[2]) / 2
    F.ring(img, cx, r[1] + 16, 9, 12, RED)
    F.disc(img, cx, r[1] + 17, 4.5, (236, 150, 30))
    F.disc(img, cx, r[1] + 13, 2.5, (236, 150, 30))
    F.line(img, cx - 8, r[1] + 8, cx + 8, r[1] + 24, RED, 2)
    F.text(img, cx, r[1] + 34, 'KEIN OFFENES', F.F35, INK)
    F.text(img, cx, r[1] + 40, 'FEUER', F.F35, INK)
    F.rect(img, r[0] + 8, r[1] + 45, r[2] - 9, r[1] + 45, (170, 160, 150))
    F.text(img, cx, r[1] + 51, 'NO NAKED', F.F35, (70, 68, 64))
    F.text(img, cx, r[1] + 57, 'FLAMES', F.F35, (70, 68, 64))
    r = CREG['csign_louvre']                                           # yellow instruction plate
    GT._plate(img, r, YEL, (246, 214, 90), (150, 120, 20))
    F.text(img, (r[0] + r[2]) / 2, r[1] + 7, 'LUFTKLAPPE VOR', F.F35, INK)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 14, 'START ÖFFNEN', F.F35, INK)
    F.rect(img, r[0] + 10, r[1] + 19, r[2] - 11, r[1] + 19, (150, 120, 20))
    F.text(img, (r[0] + r[2]) / 2, r[1] + 25, 'OPEN LOUVRE', F.F35, (70, 56, 14))
    F.text(img, (r[0] + r[2]) / 2, r[1] + 32, 'BEFORE START', F.F35, (70, 56, 14))
    r = CREG['csign_noentry']                                          # white plate, red band
    GT._plate(img, r, (232, 228, 216), (246, 244, 236), (160, 156, 146))
    F.rect(img, r[0] + 2, r[1] + 2, r[2] - 3, r[1] + 13, RED)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 8, 'ZUTRITT', F.F57, WHITE)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 21, 'VERBOTEN', F.F57, RED)
    F.text(img, (r[0] + r[2]) / 2, r[1] + 32, 'NO ENTRY', F.F35, INK)


def build(out):
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    b, e = GT.build(tmp)
    img = np.array(Image.open(b).convert('RGB'))
    emi = np.array(Image.open(e).convert('RGB'))
    draw_container_signs(img)
    pb, pe = os.path.join(out, 'T_GCont_Panel_BaseColor.png'), os.path.join(out, 'T_GCont_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    json.dump(dict(size=N, regions=GT.REG, gpanel=GT.GPANEL, board=GT.BOARD), open(os.path.join(out, 'gcont_panel_regions.json'), 'w'),
              indent=1)
    shutil.rmtree(tmp)
    return pb, pe


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'cont')
    print(build(out))
