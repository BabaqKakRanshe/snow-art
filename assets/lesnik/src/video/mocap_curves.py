"""Mocap (GEM-X joints, gem_joints.py) -> the body's life as curves for lesnik_rig.py: the pelvis sways and shifts its
weight, the spine leans and twists, the shoulders rise - each as a change from the clip's mean pose, in the
creature's own frame (left / forward / up), so it can ride on top of our hunched pose.

    venv/Scripts/python.exe mocap_curves.py <joints.npz> <out.json> [loop_frames=120] [fps=24]

The 77 joints are SOMA's rig without Root and the twist joints (assets/soma/SOMA_template_rig.usda): 0 Hips, 1 Spine1,
2 Spine2, 3 Chest, 11 LeftShoulder, 12 LeftArm, 39 RightShoulder, 40 RightArm, 67 LeftLeg (hip), 72 RightLeg, 69/74
feet. Filtered (Butterworth 6 Hz, both ways), resampled to fps, the first loop_frames taken and the loop closed by a
linear ramp. Lengths are in human metres (scale them by the leg length), angles in degrees.
"""
import sys, json
import numpy as np
from scipy.signal import butter, filtfilt

HIPS, SPINE1, CHEST, L_ARM, R_ARM, L_HIP, R_HIP = 0, 1, 3, 12, 40, 67, 72
src, out = sys.argv[1], sys.argv[2]
LOOP = int(sys.argv[3]) if len(sys.argv) > 3 else 120
FPS = float(sys.argv[4]) if len(sys.argv) > 4 else 24.0
d = np.load(src)
J, fps_in = d['joints'].astype(np.float64), float(d['fps'])

b, a = butter(2, 6.0 / (fps_in / 2))                          # jitter off, timing kept (zero phase)
J = filtfilt(b, a, J, axis=0)
t_in = np.arange(len(J)) / fps_in
t = np.arange(LOOP + 1) / FPS
assert t[-1] <= t_in[-1] + 1e-6, f'the clip is {t_in[-1]:.2f} s, the loop needs {t[-1]:.2f} s'
J = np.stack([np.stack([np.interp(t, t_in, J[:, j, c]) for c in range(3)], -1) for j in range(J.shape[1])], 1)

# the body's frame from the mean pose: up = SOMA +y, left = from the right hip to the left, forward = left x up
up = np.array([0.0, 1.0, 0.0])
left = (J[:, L_HIP] - J[:, R_HIP]).mean(0)
left -= up * left.dot(up)
left /= np.linalg.norm(left)
fwd = np.cross(left, up)


def local(v):                                                    # world vectors -> (left, forward, up)
    return np.stack([v @ left, v @ fwd, v @ up], -1)


hip_h = (J[:, L_HIP, 1] + J[:, R_HIP, 1]).mean() / 2 - J[:, [69, 74], 1].min()
pel = local(J[:, HIPS] - J[:, HIPS].mean(0))
hips_v = local(J[:, L_HIP] - J[:, R_HIP])
spine_v = local(J[:, CHEST] - J[:, HIPS])
sh_v = local(J[:, L_ARM] - J[:, R_ARM])
deg = np.degrees
roll = deg(np.arctan2(hips_v[:, 2], hips_v[:, 0]))               # + : the left hip up
yaw = deg(np.arctan2(hips_v[:, 1], hips_v[:, 0]))                # + : the left hip forward
lean = deg(np.arctan2(spine_v[:, 1], spine_v[:, 2]))             # + : the chest forward
side = deg(np.arctan2(spine_v[:, 0], spine_v[:, 2]))             # + : the chest to its left
twist = deg(np.arctan2(sh_v[:, 1], sh_v[:, 0])) - yaw            # + : the left shoulder forward, against the pelvis
shrug_l = J[:, L_ARM, 1] - J[:, CHEST, 1]
shrug_r = J[:, R_ARM, 1] - J[:, CHEST, 1]


def curve(x):
    x = x - x.mean()
    x = x + (x[0] - x[-1]) * np.arange(len(x)) / (len(x) - 1)  # the loop closes
    return [round(float(v), 5) for v in x]


res = {'source': str(d.get('source', src)), 'fps': FPS, 'loop': LOOP, 'human_hip_height_m': round(float(hip_h), 4),
       'pelvis_left_m': curve(pel[:, 0]), 'pelvis_fwd_m': curve(pel[:, 1]), 'pelvis_up_m': curve(pel[:, 2]),
       'pelvis_roll_deg': curve(roll), 'pelvis_yaw_deg': curve(yaw), 'spine_lean_deg': curve(lean),
       'spine_side_deg': curve(side), 'chest_twist_deg': curve(twist),
       'shrug_l_m': curve(shrug_l), 'shrug_r_m': curve(shrug_r)}
json.dump(res, open(out, 'w'), indent=0)
for k, v in res.items():
    if isinstance(v, list):
        print(f'{k:16s} range {min(v):+.3f} .. {max(v):+.3f}')
print('hip height (human)', round(float(hip_h), 3))
