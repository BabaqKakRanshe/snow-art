"""Mocap (GEM-X joints, gem_joints.py) -> the whole body's path for lesnik_rig.py: per frame the pelvis position and
turn, the spine's bend in the pelvis' frame, and both feet (ankle and toes) - in Blender axes of the creature at the
clip's start (its left +x, its forward -y, up +z), metres from the ground under the start pelvis, human sizes (the rig
scales them by its leg length).

    venv/Scripts/python.exe mocap_body.py <joints.npz> <out.json> <video_fps> <first_video_frame> <frames> [cut_hz=5]

Clip frame f is the video's frame first_video_frame + f (at video_fps), sampled from the 30 Hz capture, smoothed
(Butterworth, both ways). Joints: SOMA without Root / twists (mocap_curves.py): 0 Hips, 1 Spine1, 3 Chest, 67/72 hips,
69/74 ankles, 70/75 toes.
"""
import sys, json
import numpy as np
from scipy.signal import butter, filtfilt

HIPS, SPINE1, CHEST, L_HIP, R_HIP, L_FOOT, L_TOE, R_FOOT, R_TOE = 0, 1, 3, 67, 72, 69, 70, 74, 75
src, out, vfps, v0, N = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
CUT = float(sys.argv[6]) if len(sys.argv) > 6 else 5.0
d = np.load(src)
J, fps = d['joints'].astype(np.float64), float(d['fps'])
b, a = butter(2, CUT / (fps / 2))
J = filtfilt(b, a, J, axis=0)
ts = (v0 + np.arange(N)) / vfps * fps
assert ts[-1] <= len(J) - 1, f'the capture is {len(J) / fps:.2f} s, the clip needs {(v0 + N) / vfps:.2f} s'
S = np.stack([np.stack([np.interp(ts, np.arange(len(J)), J[:, j, c]) for c in range(3)], -1) for j in range(J.shape[1])], 1)

up = np.array([0.0, 1.0, 0.0])
k0 = slice(0, max(1, min(8, N)))                                # the start: standing
left0 = (S[k0, L_HIP] - S[k0, R_HIP]).mean(0)
left0 -= up * left0.dot(up)
left0 /= np.linalg.norm(left0)
fwd0 = np.cross(left0, up)
M = np.stack([left0, -fwd0, up])                               # mocap -> blender rows: +x left, +y back, +z up
ground = min(J[:, [L_FOOT, L_TOE, R_FOOT, R_TOE], 1].min(), 1e9)
O = S[k0, HIPS].mean(0).copy()
O[1] = ground


def bl(p):
    return (p - O) @ M.T


def basis(t):                                                    # the pelvis' frame in blender axes: columns x, y, z
    x = bl(S[t, L_HIP]) - bl(S[t, R_HIP])
    zz = bl(S[t, SPINE1]) - bl(S[t, HIPS])
    x /= np.linalg.norm(x)
    zz -= x * zz.dot(x)
    zz /= np.linalg.norm(zz)
    return np.stack([x, np.cross(zz, x), zz], 1)


B0 = basis(0)
rows = []
for t in range(N):
    Bt = basis(t)
    R = Bt @ B0.T                                                # the pelvis' turn since the start
    sp = Bt.T @ (bl(S[t, CHEST]) - bl(S[t, HIPS]))               # the spine in the pelvis' own frame
    sp0 = B0.T @ (bl(S[0, CHEST]) - bl(S[0, HIPS]))
    lean = np.degrees(np.arctan2(-sp[1], sp[2]) - np.arctan2(-sp0[1], sp0[2]))   # + : the chest forward
    side = np.degrees(np.arctan2(sp[0], sp[2]) - np.arctan2(sp0[0], sp0[2]))     # + : the chest to its left
    rows.append({'pelvis': bl(S[t, HIPS]).round(5).tolist(), 'R': R.round(6).tolist(),
                 'lean': round(float(lean), 3), 'side': round(float(side), 3),
                 'ankle_l': bl(S[t, L_FOOT]).round(5).tolist(), 'toe_l': bl(S[t, L_TOE]).round(5).tolist(),
                 'ankle_r': bl(S[t, R_FOOT]).round(5).tolist(), 'toe_r': bl(S[t, R_TOE]).round(5).tolist()})
hip_h = float(np.mean([(bl(S[t, L_HIP])[2] + bl(S[t, R_HIP])[2]) / 2 for t in range(k0.stop)]))
json.dump({'source': src, 'video_fps': vfps, 'first_video_frame': v0, 'frames': N, 'human_hip_height_m': round(hip_h, 4),
           'track': rows}, open(out, 'w'), indent=0)
pz = [r['pelvis'][2] for r in rows]
print(f'frames {N}, hip height {hip_h:.2f} m, pelvis height {pz[0]:.2f} -> min {min(pz):.2f} -> end {pz[-1]:.2f} m')
print('pelvis travel (x, y)', np.round(np.array(rows[-1]['pelvis'][:2]) - rows[0]['pelvis'][:2], 2))
