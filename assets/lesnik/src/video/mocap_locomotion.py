"""Mocap (GEM-X joints, gem_joints.py) of a walk / run -> one in-place loop for lesnik_rig.py's ik_bake.

    venv/Scripts/python.exe mocap_locomotion.py <joints.npz> <out.json> <first_s> <last_s> [frames=24] [cut_hz=8]

From the steady stretch [first_s, last_s] of the video: the direction and the mean speed of the pelvis, the left foot's
touch-downs (GEM's contact confidence, else the foot's lowest points) -> one cycle (left touch-down to the next); then
per frame, in the body's own frame (left / forward / up), the pelvis and both feet with the travel taken out - the
planted foot slides back at exactly the mean speed, as the game moves the body forward at it. Resampled to `frames`
frames, the loop closed. Lengths in human metres (lesnik_rig.py scales them by the leg length), angles in degrees.
Joints: SOMA without Root / twists (see mocap_curves.py): 0 Hips, 3 Chest, 67/72 hips, 69/74 feet, 70/75 toes.
"""
import sys, json
import numpy as np
from scipy.signal import butter, filtfilt

HIPS, CHEST, L_HIP, R_HIP, L_FOOT, L_TOE, R_FOOT, R_TOE = 0, 3, 67, 72, 69, 70, 74, 75
src, out, t0, t1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
N = int(sys.argv[5]) if len(sys.argv) > 5 else 24
CUT = float(sys.argv[6]) if len(sys.argv) > 6 else 8.0
d = np.load(src)
J, C, fps = d['joints'].astype(np.float64), d['contact'].astype(np.float64), float(d['fps'])
b, a = butter(2, CUT / (fps / 2))
J = filtfilt(b, a, J, axis=0)
i0, i1 = int(t0 * fps), min(len(J) - 1, int(t1 * fps))
up = np.array([0.0, 1.0, 0.0])
move = J[i1, HIPS] - J[i0, HIPS]
move -= up * move.dot(up)
dist = np.linalg.norm(move)
fwd = move / dist
left = np.cross(up, fwd)                                       # (blender: z x -y = +x: left)
speed = dist / ((i1 - i0) / fps)

# the left foot's touch-downs in the stretch: contact rises through 0.5, else local minima of its height
cl = C[i0:i1 + 1, 0]
downs = [i0 + k for k in range(1, len(cl)) if cl[k - 1] < 0.5 <= cl[k]]
if len(downs) < 2:
    h = J[i0:i1 + 1, L_FOOT, 1]
    downs = [i0 + k for k in range(2, len(h) - 2) if h[k] == h[k - 2:k + 3].min() and h[k] < h.min() + 0.05]
assert len(downs) >= 2, f'no full step cycle found in {t0}-{t1} s (touch-downs {downs})'
cyc = [(downs[k], downs[k + 1]) for k in range(len(downs) - 1)]
c0, c1 = min(cyc, key=lambda p: abs((p[1] - p[0]) - np.median([q[1] - q[0] for q in cyc])))   # the most typical cycle
period = (c1 - c0) / fps
cycle_m = speed * period


def frame(v):
    return np.stack([v @ left, v @ fwd, v @ up], -1)


ts = np.linspace(c0, c1, N + 1)
travel = lambda t: (t - c0) / fps * speed


def track(j):
    raw = np.stack([np.interp(ts, np.arange(len(J)), J[:, j, c]) for c in range(3)], -1)
    loc = frame(raw)
    loc[:, 1] -= travel(ts)                                     # in place: the body stays, the world slides back
    return loc


pel, lf, rf, lt, rt, ch = (track(j) for j in (HIPS, L_FOOT, R_FOOT, L_TOE, R_TOE, CHEST))
ground = min(lf[:, 2].min(), rf[:, 2].min(), lt[:, 2].min(), rt[:, 2].min())
hip_h = float(np.mean([track(L_HIP)[:, 2].mean(), track(R_HIP)[:, 2].mean()]) - ground)


def close(x):                                                    # the loop's seam spread over the cycle
    x = np.asarray(x, dtype=np.float64)
    return x + (x[0] - x[-1])[None] * (np.arange(len(x)) / (len(x) - 1))[:, None] if x.ndim == 2 else \
        x + (x[0] - x[-1]) * np.arange(len(x)) / (len(x) - 1)


spine = ch - pel
lean = np.degrees(np.arctan2(spine[:, 1], spine[:, 2]))          # + : the chest ahead of the pelvis
hips_v = track(L_HIP) - track(R_HIP)
roll = np.degrees(np.arctan2(hips_v[:, 2], hips_v[:, 0]))
yaw = np.degrees(np.arctan2(hips_v[:, 1], hips_v[:, 0]))
pc = pel.mean(0)
res = {'source': src, 'stretch_s': [t0, t1], 'cycle_frames_video': int(c1 - c0), 'period_s': round(period, 4),
       'speed_mps': round(speed, 4), 'cycle_m': round(cycle_m, 4), 'frames': N, 'human_hip_height_m': round(hip_h, 4),
       'pelvis': [[round(v, 5) for v in r] for r in close(pel - pc)],
       'pelvis_height_m': round(float(pc[2] - ground), 4),
       'foot_l': [[round(v, 5) for v in r] for r in close(lf - [0, 0, ground])],
       'foot_r': [[round(v, 5) for v in r] for r in close(rf - [0, 0, ground])],
       'toe_l': [[round(v, 5) for v in r] for r in close(lt - [0, 0, ground])],
       'toe_r': [[round(v, 5) for v in r] for r in close(rt - [0, 0, ground])],
       'lean_deg': [round(v, 3) for v in close(lean)], 'roll_deg': [round(v, 3) for v in close(roll - roll.mean())],
       'yaw_deg': [round(v, 3) for v in close(yaw - yaw.mean())],
       'contact_l': [round(float(np.interp(t, np.arange(len(C)), C[:, 0])), 3) for t in ts],
       'contact_r': [round(float(np.interp(t, np.arange(len(C)), C[:, 2])), 3) for t in ts]}
json.dump(res, open(out, 'w'), indent=0)
print(f'speed {speed:.2f} m/s, cycle {period:.2f} s = {cycle_m:.2f} m (video frames {c0}-{c1}), touch-downs {downs}')
print(f'hip height {hip_h:.2f} m, pelvis height {res["pelvis_height_m"]} m, lean {np.mean(lean):.0f} deg mean')
