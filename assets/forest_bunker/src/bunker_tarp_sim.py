"""PlaneTarp drape: a canvas sheet dropped over forest's UtilityPlane v13 (the WinterKit 1.2 covers on), parked in the hangar
(BunkerHangar Slot_Plane: nose to the gate, tail wheel down, ~10 deg nose up). Own position-based cloth (Verlet, distance /
shear / bending constraints, friction) against a 2.5D solid of the plane: the top envelope of its meshes (rays from above,
2 cm grid; thin spikes - aerials, the pitot - opened away) extruded down to the floor, so the canvas lies on the wing and
the cabin and hangs straight down past their edges; a vertex inside is pushed up or sideways out, whichever is shorter.
(Blender's cloth leaked through the plane's open, two-sided meshes.)
Writes the settled sheet in the hangar frame and in the plane's own frame (UtilityPlane root: the tarp is its child in
Unity).
python3.11 -I bunker_tarp_sim.py <UtilityPlane_v13.blend> <out.npz>"""
import sys, math, time
import numpy as np
from scipy import ndimage
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, '/home/claude/uaz')
import bunker_spec as BS

SRC, OUT = sys.argv[1], sys.argv[2]
T0 = time.time()
bpy.ops.wm.open_mainfile(filepath=SRC)
PARK = BS.plane_park_matrix()
COLLIDE = ['Body', 'Aileron_L', 'Aileron_R', 'Flap_L', 'Flap_R', 'Elevator_L', 'Elevator_R', 'Rudder', 'CargoDoor_L',
           'CargoDoor_R', 'PilotDoor_L', 'PilotDoor_R', 'Glass', 'Gear_L', 'Gear_R', 'Wheel_L', 'Wheel_R', 'Propeller',
           'PropBlade_1', 'PropBlade_2', 'PropBlade_3', 'TailGear', 'TailWheel', 'TailWheel_Fork',
           'Kit_WingCover_L', 'Kit_WingCover_R', 'Kit_WindshieldCover', 'Kit_EngineCover', 'Kit_PitotCover',
           'Kit_TieDown_L', 'Kit_TieDown_R', 'Kit_Chocks_L', 'Kit_Chocks_R', 'Kit_IntakePlug', 'Kit_ExhaustCover_L',
           'Kit_ExhaustCover_R']
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
for n in COLLIDE:
    o = bpy.data.objects[n]
    me = o.evaluated_get(dg).to_mesh().copy()
    me.transform(PARK @ o.matrix_world)
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
tree = BVHTree.FromBMesh(bm)
print('collider tris', len(bm.faces), round(time.time() - T0, 1), 's', flush=True)

T = BS.TARP
cx, cy = T['centre']
c_h = PARK @ Vector((cx, cy, 2.0))
G = 0.02                                                   # envelope grid (m)
X0, X1 = c_h.x - T['w'] / 2 - 1.0, c_h.x + T['w'] / 2 + 1.0
Y0, Y1 = c_h.y - T['l'] / 2 - 1.0, c_h.y + T['l'] / 2 + 1.0
NI, NJ = int((X1 - X0) / G) + 1, int((Y1 - Y0) / G) + 1
H = np.zeros((NJ, NI), np.float32)                         # [j (y), i (x)]
down = Vector((0, 0, -1))
for j in range(NJ):
    y = Y0 + j * G
    for i in range(NI):
        hit = tree.ray_cast(Vector((X0 + i * G, y, 8.0)), down, 9.0)
        if hit[0] is not None:
            H[j, i] = max(hit[0].z, 0.0)
H = ndimage.grey_opening(H, size=(5, 5))                   # aerials, the pitot tube, wires: away
print('envelope', NI, 'x', NJ, 'max', round(float(H.max()), 3), round(time.time() - T0, 1), 's', flush=True)
DZ = 0.05
NL = int(math.ceil(float(H.max()) / DZ)) + 2
NEAR = np.zeros((NL, 2, NJ, NI), np.int16)
DIST = np.zeros((NL, NJ, NI), np.float32)
for L in range(NL):
    inside = H > L * DZ
    if inside.any():
        d, ind = ndimage.distance_transform_edt(inside, return_indices=True)
        NEAR[L] = ind.astype(np.int16)
        DIST[L] = d * G
    else:
        NEAR[L, 0] = np.arange(NJ)[:, None]
        NEAR[L, 1] = np.arange(NI)[None, :]
print('side maps', NL, round(time.time() - T0, 1), 's', flush=True)

# the sheet
h = T['res']
nx, ny = int(round(T['w'] / h)) + 1, int(round(T['l'] / h)) + 1
gx, gy = np.meshgrid(np.arange(nx) * h - T['w'] / 2 + c_h.x, np.arange(ny) * h - T['l'] / 2 + c_h.y)
ii = np.clip(((gx - X0) / G).astype(int), 0, NI - 1)
jj = np.clip(((gy - Y0) / G).astype(int), 0, NJ - 1)
z0 = float(H[jj, ii].max()) + T['drop']
P = np.stack([gx, gy, np.full_like(gx, z0)], -1).reshape(-1, 3).astype(np.float64)
P[:, 2] += 0.01 * np.sin(np.arange(len(P)) * 0.37)
Pp = P.copy()
idx = np.arange(nx * ny).reshape(ny, nx)
cons = []
for (a, b, k) in ((idx[:, :-1], idx[:, 1:], 1.0), (idx[:-1, :], idx[1:, :], 1.0),           # structural
                  (idx[:-1, :-1], idx[1:, 1:], 0.8), (idx[:-1, 1:], idx[1:, :-1], 0.8),     # shear
                  (idx[:, :-2], idx[:, 2:], T['bend']), (idx[:-2, :], idx[2:, :], T['bend'])):  # bending
    a, b = a.ravel(), b.ravel()
    cons.append((a, b, np.linalg.norm(P[a] - P[b], axis=1), k))
CA = np.concatenate([c[0] for c in cons])
CB = np.concatenate([c[1] for c in cons])
CR = np.concatenate([c[2] for c in cons])
CK = np.concatenate([np.full(len(c[0]), c[3]) for c in cons])
deg = np.bincount(CA, minlength=len(P)) + np.bincount(CB, minlength=len(P))
THICK = 0.025


def collide(P, Pp):
    """push vertices out of the 2.5D solid; friction on the touching ones"""
    i = np.clip(((P[:, 0] - X0) / G + 0.5).astype(int), 0, NI - 1)
    j = np.clip(((P[:, 1] - Y0) / G + 0.5).astype(int), 0, NJ - 1)
    top = H[j, i] + THICK
    ins = P[:, 2] < top
    if not ins.any():
        return np.zeros(len(P), bool)
    L = np.clip((P[:, 2] / DZ).astype(int), 0, NL - 1)
    up = top - P[:, 2]
    side = DIST[L, j, i] + THICK
    k = np.where(ins)[0]
    go_up = up[k] <= side[k]
    ku, ks = k[go_up], k[~go_up]
    P[ku, 2] = top[ku]
    if len(ks):
        tj, ti = NEAR[L[ks], 0, j[ks], i[ks]], NEAR[L[ks], 1, j[ks], i[ks]]
        tx, ty = X0 + ti * G, Y0 + tj * G
        d = np.stack([tx - P[ks, 0], ty - P[ks, 1]], -1)
        n = np.linalg.norm(d, axis=1, keepdims=True)
        P[ks, :2] += d / np.maximum(n, 1e-6) * (n + THICK)
    # friction: the touching vertices keep little of their sliding
    Pp[k] = P[k] - (P[k] - Pp[k]) * 0.15
    return ins


dt = 1.0 / 120.0
g = np.array([0.0, 0.0, -9.81]) * dt * dt
STEPS = T['frames'] * 6
for s in range(STEPS):
    v = (P - Pp) * (0.985 if s < STEPS * 0.7 else 0.90)          # damped harder at the end: settle
    Pp = P.copy()
    P = P + v + g
    for it in range(24):
        d = P[CB] - P[CA]
        L_ = np.linalg.norm(d, axis=1)
        corr = (d * ((L_ - CR) / np.maximum(L_, 1e-9) * CK * 0.5)[:, None])
        acc = np.zeros_like(P)
        np.add.at(acc, CA, corr)
        np.add.at(acc, CB, -corr)
        P += acc / np.maximum(deg, 1)[:, None] * 1.6
        P[:, 2] = np.maximum(P[:, 2], 0.012)
        collide(P, Pp)
    if s % 120 == 0:
        print('step', s, 'z', round(float(P[:, 2].min()), 3), round(float(P[:, 2].max()), 3),
              'v', round(float(np.abs(v).max() / dt), 3), round(time.time() - T0, 1), 's', flush=True)
# settle: a few smoothing passes kept outside
for it in range(3):
    acc = np.zeros_like(P)
    cnt = np.zeros(len(P))
    s1 = CK == 1.0
    np.add.at(acc, CA[s1], P[CB[s1]])
    np.add.at(acc, CB[s1], P[CA[s1]])
    np.add.at(cnt, CA[s1], 1)
    np.add.at(cnt, CB[s1], 1)
    P = P * 0.6 + acc / cnt[:, None] * 0.4
    collide(P, P.copy())
P3 = P.reshape(ny, nx, 3)
inv = PARK.inverted()
Pm = np.array([tuple(inv @ Vector(p)) for p in P]).reshape(ny, nx, 3)
st = np.linalg.norm(P[CA[CK == 1.0]] - P[CB[CK == 1.0]], axis=1) / CR[CK == 1.0]
np.savez(OUT, hangar=P3, plane=Pm, nx=nx, ny=ny, park=np.array(PARK))
print('saved', OUT, 'z', P3[..., 2].min().round(3), P3[..., 2].max().round(3), 'stretch', st.min().round(3),
      st.max().round(3), round(time.time() - T0, 1), 's')
