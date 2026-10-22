"""ray-cast wireframe-over-shading image of a dump: python3 wire.py dump.npz out.png view_json"""
import numpy as np, sys, json, math
dump, out, vj = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], 'x', 'x', 'x']
exec(open('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/vis2/viscmp.py').read().split('A = Scene(A_path)')[0])
from PIL import Image
name, eye, fwd, up, fov, W, H = json.loads(vj)
S = Scene(dump)
o, d = rays_persp(eye, fwd, up, fov, W, H)
p, u, v, t = S.cast(o, d)
ok, pos, n, uv, ob, ma = S.attrs(p, u, v)
pp = np.where(ok, p, 0)
P = S.P[pp]
b = np.stack([1 - u - v, u, v], 1)
# distance of the hit to each edge (edge i is opposite vertex i)
e = [P[:, 2] - P[:, 1], P[:, 0] - P[:, 2], P[:, 1] - P[:, 0]]
area2 = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
dist = np.stack([b[:, i] * area2 / np.maximum(np.linalg.norm(e[i], axis=1), 1e-12) for i in range(3)], 1).min(1)
foot = np.where(np.isfinite(t), t, 1e9) * (2 * math.tan(math.radians(fov) / 2) / W)
edge = ok & (dist < 0.55 * foot)
L = np.array([0.35, 0.25, 0.9]); L /= np.linalg.norm(L)
lam = np.clip(np.abs((n * L).sum(1)), 0, 1) * 0.55 + 0.4
c = np.stack([lam] * 3, 1) * np.array([0.93, 0.95, 1.0])
c[~ok] = (1.0, 1.0, 1.0)
c[edge] = (0.10, 0.18, 0.55)
Image.fromarray((c.reshape(H, W, 3) * 255).astype(np.uint8)).save(out)
print('wire', out, 'tris visible', len(np.unique(p[ok])))
