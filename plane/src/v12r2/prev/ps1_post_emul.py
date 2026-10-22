"""Quick look: PS1 output (15-bit colour, the PS1 GPU 4x4 dither table, at a virtual 240-line pixel grid) applied to a
finished frame. python3 ps1_post_emul.py <in.png> <out.png>"""
import sys
import numpy as np
from PIL import Image
D = np.array([[-4, 0, -3, 1], [2, -2, 3, -1], [-3, 1, -4, 0], [3, -1, 2, -2]], float)   # PS1 GPU dither offsets
im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
H, W = im.shape[:2]
cell = H / 240.0
yy, xx = np.mgrid[0:H, 0:W]
d = D[(np.floor(yy / cell).astype(int)) % 4, (np.floor(xx / cell).astype(int)) % 4]
q = np.clip(np.floor((im + d[..., None]) / 8.0), 0, 31)
out = q * 8 + np.floor(q / 4)                      # 5 -> 8 bit expansion
Image.fromarray(out.astype(np.uint8)).save(sys.argv[2])
