"""GEM-X result (.pt from gem-infer motion-video --postprocess) -> joint positions for our Blender scripts.

Runs in the mocap venv (F:/ClaudeGames/snow_tools/mocap/venv, docs/gdd/RESEARCH_MOCAP.md):
    venv/Scripts/python.exe gem_joints.py <motion.pt> <out.npz> [soma_assets]
out.npz: joints (T, 77, 3) world metres (SOMA: y up), fps, contact (T, 6) 0..1 for the joints contact_ids (feet, toes,
hands - GEM's own static-contact confidence), names (77 joint names when the SOMA runtime gives them), kp2d (T, 77, 3).
"""
import sys
import numpy as np
import torch

sys.path.insert(0, 'F:/ClaudeGames/snow_tools/mocap/GEM-X')
from gem.motion.geometry import MotionGeometry                    # noqa: E402
from gem.motion.postprocess.contact import SOMA_CONTACT_JOINT_IDS  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
assets = sys.argv[3] if len(sys.argv) > 3 else 'F:/ClaudeGames/snow_tools/mocap/GEM-X/assets/soma'
res = torch.load(src, map_location='cpu', weights_only=False)
params = res['pred_soma_params_global']
length = int(torch.as_tensor(res['length']).item())
geo = MotionGeometry(assets, device='cuda' if torch.cuda.is_available() else 'cpu', apply_correctives=False)
joints = np.concatenate([chunk['joints'][0].numpy() for _, chunk in geo.iter_chunks(params)], 0)[:length]
contact = torch.sigmoid(res['static_conf_logits'][0, :length].float()).numpy()
runtime = geo.body_model.runtime
names = list(getattr(runtime, 'joint_names', []) or [])
kp2d = res['conditions']['kp2d_native77'][0, :length].numpy() if 'conditions' in res else np.zeros((length, 77, 3))
fps = float(res.get('sampling_fps', 30.0))
np.savez(out, joints=joints.astype(np.float32), fps=fps, contact=contact.astype(np.float32),
         contact_ids=np.array(SOMA_CONTACT_JOINT_IDS), names=np.array(names), kp2d=kp2d.astype(np.float32))
lo, hi = joints.reshape(-1, 3).min(0), joints.reshape(-1, 3).max(0)
print('frames', length, 'fps', fps, 'joints', joints.shape, 'names', len(names))
print('extent min', lo.round(3), 'max', hi.round(3))
print('contact ids', SOMA_CONTACT_JOINT_IDS, [names[i] if i < len(names) else i for i in SOMA_CONTACT_JOINT_IDS])
print('mean contact', contact.mean(0).round(2))
