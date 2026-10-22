"""compare the convex colliders (COL_*) of two FBX: max distance of each one's vertices outside the other's hull"""
import bpy, sys, numpy as np
from scipy.spatial import ConvexHull
def cols(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    out = {}
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('COL_'):
            M = np.array(o.matrix_world)
            co = np.array([v.co[:] for v in o.data.vertices])
            out[o.name.split('.')[0]] = co @ M[:3, :3].T + M[:3, 3]
    return out
A = cols(sys.argv[-2]); B = cols(sys.argv[-1])
print('colliders', len(A), len(B), 'missing', sorted(set(A) ^ set(B)))
def outside(P, Q):
    try:
        h = ConvexHull(Q)
    except Exception:
        return float('nan')
    d = P @ h.equations[:, :3].T + h.equations[:, 3]
    return float(np.maximum(d.max(1), 0).max())
rows = []
for n in sorted(set(A) & set(B)):
    rows.append((max(outside(A[n], B[n]), outside(B[n], A[n])), n, len(A[n]), len(B[n])))
rows.sort(reverse=True)
for r in rows[:12]:
    print(f'{r[1]:28s} max deviation {r[0]*1000:6.2f} mm  verts {r[2]} -> {r[3]}')
print('all within 0.1 mm:', sum(1 for r in rows if r[0] <= 0.0001), 'of', len(rows))
