"""Walking along a chain-link fence at the game's 240 lines: the old netting (1 px wires in an 8 px lattice, mips with
Preserve Coverage at 0.42 against a 0.5 cut-off, as in the project) and the new one (2 px wires, 16 px diamonds,
jittered; Preserve Coverage at 0.5 = the cut-off). Point sampling, the nearest mip by the screen footprint, alpha test.
python3 moire_gif.py <old.png> <new.png> <out.gif> [frames]"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.argv_ = sys.argv
import importlib.util
spec = importlib.util.spec_from_file_location('mt', '/home/claude/fence/moire_test.py')
W, H = 426, 240
sys.argv = ['x', 'a', 'b', str(W), str(H)]
mt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mt)
sys.argv = sys.argv_
old = np.array(Image.open(sys.argv[1]).convert('RGBA'))
new = np.array(Image.open(sys.argv[2]).convert('RGBA'))
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 28
Lo, Ln = mt.mips(old, preserve=True, ref=0.42), mt.mips(new, preserve=True, ref=0.5)
bg = mt.background()
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
except Exception:
    font = ImageFont.load_default()
frames = []
for i in range(NF):
    x = 0.08 * i
    cam = (x - 2.0, -3.2, 1.62)
    look = (x + 6.0, 0.0, 1.25)
    a = mt.render(Lo, cam=cam, look=look, bg=bg)
    b = mt.render(Ln, cam=cam, look=look, bg=bg)
    S = 2
    im = Image.new('RGB', (W * S * 2 + 12, H * S + 34), (18, 18, 18))
    for k, (img, cap) in enumerate(((a, 'было: ячейка 6 см, провод 1 px'), (b, 'стало: ячейка 12,5 см, провод 2 px'))):
        t = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((W * S, H * S), Image.NEAREST)
        im.paste(t, (k * (W * S + 12), 34))
        ImageDraw.Draw(im).text((k * (W * S + 12) + 8, 7), cap, fill=(255, 220, 120), font=font)
    frames.append(im)
frames[0].save(sys.argv[3].replace('.gif', '_f0.png'))
frames[0].save(sys.argv[3], save_all=True, append_images=frames[1:], duration=90, loop=0)
print('saved', sys.argv[3], len(frames))
