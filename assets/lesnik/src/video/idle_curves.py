"""Idle from a video: the creature's silhouette per frame -> how far each arm is curled in, where the head sways.
Front view on a light plain background (Viggle, docs/gdd/monsters/02_lesnik/anim_refs). Pose AI (RTMW3D) misses the
joints of these arms (human proportions), the silhouette is exact. Output: idle_curves.json next to this file.
    python idle_curves.py <video.mp4> [loop_frames=120]
curl 0 = the arms as in frame 0 (hanging, open); 1 = most curled in the clip (elbows out, hands hooked in); < 0 wider.
Screen left = the creature's right (it faces the camera). head_x: head off the torso centre, in body heights (+ = its left).
"""
import sys, os, json
import cv2
import numpy as np

src = sys.argv[1]
LOOP = int(sys.argv[2]) if len(sys.argv) > 2 else 120
cap = cv2.VideoCapture(src)
rows = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    m = g < 110                                                      # the dark creature on the light backdrop
    m[:, :380] = False                                               # the watermark
    m[:, 960:] = False
    ys, xs = np.nonzero(m)
    top, bot = ys.min(), ys.max()
    H = bot - top
    band = (ys > top + 0.33 * H) & (ys < top + 0.80 * H)             # arms and hands
    cx = np.median(xs[(ys > top + 0.2 * H) & (ys < top + 0.45 * H)]) # torso centre
    head = ys < top + 0.12 * H
    rows.append(((cx - xs[band].min()) / H, (xs[band].max() - cx) / H, (np.mean(xs[head]) - cx) / H))
v = np.array(rows)
assert len(v) > LOOP, 'the video is shorter than the loop'


def smooth(a, n=7):
    k = np.ones(n) / n
    return np.convolve(np.pad(a, n // 2, mode='edge'), k, mode='valid')


out = {'source': os.path.basename(src), 'fps': 24, 'loop': LOOP}
for key, col in (('curl_R', 0), ('curl_L', 1)):                      # screen left = its right arm
    s = smooth(v[:, col])
    s0 = s[:8].mean()
    c = (s0 - s) / (s0 - s.min())
    c = c[:LOOP + 1] + (c[0] - c[LOOP]) * np.arange(LOOP + 1) / LOOP  # the loop closes
    out[key] = [round(float(x), 4) for x in c]
h = smooth(v[:, 2])
h = h[:LOOP + 1] + (h[0] - h[LOOP]) * np.arange(LOOP + 1) / LOOP
out['head_x'] = [round(float(x - h[0]), 4) for x in h]
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'idle_curves.json'), 'w'), indent=0)
for f in range(0, LOOP + 1, 8):
    print(f'f{f:3d} curl R {out["curl_R"][f]:+.2f} L {out["curl_L"][f]:+.2f} head {out["head_x"][f]:+.3f}')
