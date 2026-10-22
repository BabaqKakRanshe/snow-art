"""Post for the concept renders: fog from the depth pass, light glow at night, 15-bit colour with
Bayer 4x4 (the game's PS1 frame), nearest-neighbour upscale.  python3 post.py <dir> [scale]"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0
FOG = {'day': ((0.74, 0.77, 0.82), 70.0, 4.0), 'night': ((0.035, 0.045, 0.075), 32.0, 3.0),
       'inside': ((0.035, 0.045, 0.075), 40.0, 6.0), 'side': (None, 0, 0)}


def process(d, view, scale=2):
    im = np.asarray(Image.open(os.path.join(d, f'{view}.png')).convert('RGB'), np.float32) / 255
    dp = os.path.join(d, f'{view}_depth.png')
    fogc, D, d0 = FOG[view]
    if fogc is not None and os.path.exists(dp):
        z = np.asarray(Image.open(dp), np.float32)
        z = (z[..., 0] if z.ndim == 3 else z) / 65535.0 * 200.0
        far = z <= 0.001                                    # sky
        f = 1 - np.exp(-np.maximum(z - d0, 0) / D)
        f = np.where(far, 0.92, f)[..., None]
        im = im * (1 - f) + np.array(fogc)[None, None] * f
    if view in ('night', 'inside'):                        # glow of lamps and lit windows, as in fog
        lum = im.max(-1)
        hi = np.clip((lum - 0.72) / 0.28, 0, 1)[..., None] * im
        g = np.stack([ndimage.gaussian_filter(hi[..., k], 6) for k in range(3)], -1)
        im = im + g * (1.6 if view == 'night' else 0.6)
    H, W, _ = im.shape
    th = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    q = np.floor(np.clip(im, 0, 1) * 31 + th) / 31                  # 5 bits per channel + ordered dither
    out = Image.fromarray((np.clip(q, 0, 1) * 255 + 0.5).astype(np.uint8))
    out = out.resize((W * scale, H * scale), Image.NEAREST)
    out.save(os.path.join(d, f'{view}_psx.png'))
    return out


if __name__ == '__main__':
    d = sys.argv[1]
    sc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    for v in ('day', 'night', 'inside', 'side'):
        if os.path.exists(os.path.join(d, f'{v}.png')):
            process(d, v, sc)
    print('post done', d)
