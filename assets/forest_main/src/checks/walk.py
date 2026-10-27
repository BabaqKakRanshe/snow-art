"""Walkability of the rebuilt main building (out/main.blend posed from the contract: every door open, the gate shut, the
shutters rolled up): Snow's player capsule (HLCharacterMotor: r 0.34, h 1.80, step 0.35). Per level band (basement,
ground floor with the yard and the garage, upper floor, roof) a 5 cm grid: the floor under each cell by a ray down, the
cell free when the capsule's spine (0.40 .. 1.75 above that floor) keeps r from everything; neighbours joined when their
floors differ by <= the step. Flood fill from the yard at the entrance (EG), from the stair landing on the other levels;
the flights between the levels walked tread by tread (clearance, headroom). Then: the rooms reached, every IX part within
hand reach (1.0 m across, 0.2 .. 2.1 m above a reached floor), the sockets of kind hand.
python3 -I walk.py [--test]  -> walk.json + walk_<level>.png next to this script"""
import bpy, sys, os, json, math
import numpy as np
from collections import deque
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from scipy.ndimage import distance_transform_edt
sys.path.insert(0, '/home/claude/uaz')
import main_spec as S

SFX = '_test' if '--test' in sys.argv else ''
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/main{SFX}.blend')
for _lib in list(bpy.data.libraries):                 # 1.2: the snow_kit instances (linked) are not the building's
    bpy.data.libraries.remove(_lib)                  # geometry: checked as in 1.1, the station has main_leit_check.py
C = json.load(open(f'/home/claude/uaz/out/main_contract{SFX}.json'))
R, H, STEP = 0.34, 1.80, 0.35
DOORS = [n for n in C['parts'] if n.startswith(('IX_Door_', 'IX_MainDoor_', 'IX_ExitDoor_', 'IX_RoofDoor_', 'IX_GarageDoor_'))]
for n, p in C['parts'].items():                                     # the pose: doors open, shutters rolled up
    o = bpy.data.objects.get(n)
    if o is None:
        continue
    if n in DOORS:
        piv, ax = Vector(p['pivot']), Vector(p['axis']).normalized()
        o.matrix_world = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(p['range'][1]), 4, ax) @
                          Matrix.Translation(-piv) @ o.matrix_world)
    elif p['kind'] == 'scale':
        o.scale.z = p['range'][1] if p.get('open', True) else p['range'][0]
    elif n == 'IX_MainDoorBar_311':                                  # the bar lifted (Update 3: Awake)
        piv, ax = Vector(p['pivot']), Vector(p['axis']).normalized()
        o.matrix_world = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(p['range'][1]), 4, ax) @
                          Matrix.Translation(-piv) @ o.matrix_world)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
V, T, TOBJ = [], [], []
PARTV = {}                                                           # IX part -> its world vertices (reach targets)
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    M = o.matrix_world
    off = len(V)
    V += [M @ v.co for v in me.vertices]
    T += [tuple(i + off for i in t.vertices) for t in me.loop_triangles]
    TOBJ += [o.name] * len(me.loop_triangles)
    if o.name.startswith('IX_'):
        PARTV[o.name] = (np.array([tuple(M @ v.co) for v in me.vertices]),
                         [tuple(M @ v.co for v in (me.vertices[i] for i in t.vertices)) for t in me.loop_triangles])
    o.evaluated_get(dg).to_mesh_clear()
NOBJ = len(T)                                                        # triangles below this index belong to objects
FOOT = [(-18.0, -8.0, -5.0, 5.0), (-8.0, 8.0, -6.0, 6.0), (-1.95, 1.95, 6.0, 7.0)]   # garage, main block, stair tower
for gx in np.arange(-40.0, 30.0, 0.5):                               # the yard round the building (the terrain)
    for gy in np.arange(-40.0, 30.0, 0.5):
        cx, cy = gx + 0.25, gy + 0.25
        if any(a <= cx <= b and c <= cy <= d for (a, b, c, d) in FOOT):
            continue
        g0 = len(V)
        V += [Vector((gx, gy, S.GROUND)), Vector((gx + 0.5, gy, S.GROUND)), Vector((gx + 0.5, gy + 0.5, S.GROUND)),
              Vector((gx, gy + 0.5, S.GROUND))]
        T += [(g0, g0 + 1, g0 + 2), (g0, g0 + 2, g0 + 3)]
BV = BVHTree.FromPolygons(V, T)
print('triangles', len(T), flush=True)
res = 0.05
xs = np.arange(-19.0, 11.5, res)
ys = np.arange(-11.0, 8.0, res)
LEVELS = {'UG': dict(top=S.UG_F + 2.0, start=(3.0, 0.0), x=(-2.5, 8.5)),
          'EG': dict(top=2.0, start=(-6.45, -9.5), x=(-19.0, 11.5)),
          'OG': dict(top=S.OG_F + 2.0, start=(0.0, 1.8), x=(-8.5, 8.5)),
          'Dach': dict(top=S.ROOF + 0.70, start=(0.0, 0.2), x=(-8.5, 8.5))}
out = {}
reached = {}
for lv, L in LEVELS.items():
    fl = np.full((len(xs), len(ys)), np.nan, np.float32)
    free = np.zeros((len(xs), len(ys)), bool)
    for i, x in enumerate(xs):
        if not (L['x'][0] <= x <= L['x'][1]):
            continue
        for j, y in enumerate(ys):
            hit = BV.ray_cast(Vector((x, y, L['top'])), Vector((0, 0, -1)), 4.0)
            if hit[0] is None:
                continue
            f = hit[0].z
            if hit[1].z < 0.7:                                       # not a floor (a slope steeper than 45 deg)
                continue
            fl[i, j] = f
            ok = True
            for h in (STEP + R, 0.88, 1.07, 1.27, H - R):             # the capsule above the step height (lower = steps)
                q = BV.find_nearest(Vector((x, y, f + h)), R)
                if q[0] is not None:
                    ok = False
                    break
            free[i, j] = ok
    s = (int(round((L['start'][0] - xs[0]) / res)), int(round((L['start'][1] - ys[0]) / res)))
    reach = np.zeros_like(free)
    if free[s]:
        q = deque([s])
        reach[s] = True
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < free.shape[0] and 0 <= b < free.shape[1] and free[a, b] and not reach[a, b] and \
                        abs(fl[a, b] - fl[i, j]) <= STEP:
                    reach[a, b] = True
                    q.append((a, b))
    reached[lv] = (reach, fl)
    rooms = {}
    for rn, Rm in S.ROOMS.items():
        X0, X1, Y0, Y1 = Rm['x0'], Rm['x1'], Rm['y0'], Rm['y1']
        ia, ib = np.searchsorted(xs, X0), np.searchsorted(xs, X1)
        ja, jb = np.searchsorted(ys, Y0), np.searchsorted(ys, Y1)
        sub_r = reach[ia:ib, ja:jb]
        sub_f = fl[ia:ib, ja:jb]
        lvl = np.abs(sub_f - Rm['f']) < 0.25
        if not lvl.any():
            continue
        rooms[rn] = dict(free_m2=round(float((free[ia:ib, ja:jb] & lvl).sum() * res * res), 2),
                         reached_m2=round(float((sub_r & lvl).sum() * res * res), 2))
    out[lv] = dict(start_free=bool(free[s]), reached_m2=round(float(reach.sum() * res * res), 1), rooms=rooms)
    print(lv, 'start free', bool(free[s]), 'reached %.1f m2' % (reach.sum() * res * res), flush=True)
    for rn, r in rooms.items():
        print(f'   {rn:15s} free {r["free_m2"]:6.2f}  reached {r["reached_m2"]:6.2f}')
    try:
        from PIL import Image
        img = np.zeros((len(ys), len(xs), 3), np.uint8)
        img[...] = (30, 30, 30)
        img[(~np.isnan(fl)).T] = (90, 90, 90)
        img[free.T] = (150, 150, 150)
        img[reach.T] = (60, 170, 80)
        Image.fromarray(img[::-1]).resize((len(xs) * 2, len(ys) * 2), Image.NEAREST).save(os.path.join(HERE, f'walk_{lv}.png'))
    except Exception as e:
        print('png', e)
# the flights: tread by tread up the U-stair, clearance at the waist and headroom
st = S.STAIR
flights = []
for (z0, z1) in S.STOREYS:
    rise = (z1 - z0) / (2 * st['n'])
    xa = (st['xa'][0] + st['xa'][1]) / 2
    xb = (st['xb'][0] + st['xb'][1]) / 2
    worst = (9.0, 9.0)
    for k in range(st['n']):
        for (x, y, z) in ((xa, st['y_start'] + st['going'] * (k + 0.5), z0 + rise * (k + 1)),
                          (xb, st['y_start'] + st['going'] * (st['n'] - k - 0.5), z0 + rise * (st['n'] + k + 1))):
            hit = BV.ray_cast(Vector((x, y, z + 0.30)), Vector((0, 0, -1)), 1.0)
            f = hit[0].z if hit[0] is not None else z
            up = BV.ray_cast(Vector((x, y, f + 0.05)), Vector((0, 0, 1)), 4.0)
            head = (up[0].z - f) if up[0] is not None else 9.0
            clr = min(((BV.find_nearest(Vector((x, y, f + h)), 2.0)[3] or 9.0) for h in (0.9, 1.4)))
            worst = (min(worst[0], head), min(worst[1], clr))
            if head < 2.0 or clr < 0.4:
                print('   tread', k, 'at', round(x, 2), round(y, 2), 'floor', round(f, 3), 'head', round(head, 2), 'clr', round(clr, 2))
    flights.append(dict(storey=[z0, z1], min_headroom=round(worst[0], 3), min_clearance_at_waist=round(worst[1], 3)))
    print('flights', z0, '->', z1, 'headroom %.2f  clearance %.2f' % worst)
out['flights'] = flights
# every IX part within Snow's use range (InteractionHost.UseRange 2.0 m from the eye; the first thing the ray hits must be
# the part): eyes over the reached cells (standing 1.65, crouched 0.75), the nearest point of the part's mesh
EYE = (1.65, 0.75)
USE = 2.0
far = {}
from mathutils.bvhtree import BVHTree as _B
for n, p in C['parts'].items():
    if not n.startswith('IX_') or p['kind'] == 'scale' or n not in PARTV:
        continue
    verts, tris = PARTV[n]
    if not tris:
        continue
    pb = _B.FromPolygons([v for t in tris for v in t], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))])
    lo, hi = verts.min(0), verts.max(0)
    best = 99.0
    for lv, (reach, fl) in reached.items():
        ia, ib = np.searchsorted(xs, lo[0] - USE), np.searchsorted(xs, hi[0] + USE)
        ja, jb = np.searchsorted(ys, lo[1] - USE), np.searchsorted(ys, hi[1] + USE)
        sub = reach[ia:ib, ja:jb]
        if not sub.any():
            continue
        ii, jj = np.nonzero(sub)
        keep = ((ii % 2) == 0) & ((jj % 2) == 0)                     # every 10 cm
        for i_, j_ in zip(ii[keep], jj[keep]):
            x, y, f = xs[ia + i_], ys[ja + j_], fl[ia + i_, ja + j_]
            for e in EYE:
                eye = Vector((x, y, f + e))
                q = pb.find_nearest(eye, USE)
                if q[0] is None:
                    continue
                d = q[3]
                if d >= best:
                    continue
                dirv = (q[0] - eye)
                hit = BV.ray_cast(eye, dirv.normalized(), d + 0.02)
                if hit[0] is not None and hit[3] < d - 0.02:
                    idx = hit[2]
                    if idx is None or idx >= NOBJ or not TOBJ[idx].startswith(n):
                        continue                                     # something else is in the way
                best = d
    if best > USE:
        far[n] = round(best, 2)
out['ix_out_of_reach'] = far
print('IX parts out of use range (no eye over a reached floor within 2.0 m with a clear line):', len(far), far)
json.dump(out, open(os.path.join(HERE, 'walk.json'), 'w'), indent=1)
