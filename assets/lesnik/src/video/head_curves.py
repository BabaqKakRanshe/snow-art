"""The dangling head from a video: where the upside-down head hangs off its rest place, frame by frame -> head_curves.json.
Front view, light plain background (docs/gdd/monsters/02_lesnik/anim_refs). The head is followed by template matching
(the first frame's patch, else the last frame's), the track is median-filtered and smoothed, the loop is closed.
    python head_curves.py <video.mp4> <x,y,w,h of the head in frame 0>
side: off its rest place sideways, -1..1 (+ = the creature's left = screen right); lift: up, 0..1 (1 = the highest).
"""
import sys, os, json
import cv2
import numpy as np

src = sys.argv[1]
x0, y0, w, h = [int(v) for v in sys.argv[2].split(',')]
cap = cv2.VideoCapture(src)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
tpl0 = frames[0][y0:y0 + h, x0:x0 + w].copy()
tpl, x, y, pos = tpl0, x0, y0, []
for f in frames:
    R = 40
    sx, sy = max(0, x - R), max(0, y - R)
    win = f[sy:y + h + R, sx:x + w + R]
    _, m, _, loc = cv2.minMaxLoc(cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED))
    _, m0, _, loc0 = cv2.minMaxLoc(cv2.matchTemplate(win, tpl0, cv2.TM_CCOEFF_NORMED))
    if m0 > 0.6:
        loc = loc0
    x, y = sx + loc[0], sy + loc[1]
    tpl = f[y:y + h, x:x + w].copy()
    pos.append((x + w / 2, y + h / 2))
p = np.array(pos)
p = np.vstack([p, p[:1]])                                             # the loop: frame N = frame 0
N = len(p) - 1


def clean(a, n=9):
    med = np.array([np.median(a[max(0, i - 3):i + 4]) for i in range(len(a))])
    return np.convolve(np.pad(med, n // 2, mode='edge'), np.ones(n) / n, mode='valid')


xs, ys = clean(p[:, 0]), clean(p[:, 1])
rx, ry = np.median(xs), np.median(ys)
side = (xs - rx)
side = side / np.abs(side).max()
lift = np.clip((ry - ys) / (ry - ys.min()), 0, 1)
ramp = np.arange(N + 1) / N
side = side + (side[0] - side[N]) * ramp
lift = lift + (lift[0] - lift[N]) * ramp
out = {'source': os.path.basename(src), 'fps': 24, 'loop': N,
       'side_px_max': round(float(np.abs(xs - rx).max()), 1), 'lift_px_max': round(float(ry - ys.min()), 1),
       'side': [round(float(v), 4) for v in side], 'lift': [round(float(max(0.0, v)), 4) for v in lift]}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'head_curves.json'), 'w'), indent=0)
for f in range(0, N + 1, 10):
    print(f'f{f:3d} side {side[f]:+.2f} lift {lift[f]:.2f}')
