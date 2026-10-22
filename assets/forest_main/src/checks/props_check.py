"""Update 3's dressing props, notes and floor decals against the rebuilt main building: each prop must rest on a surface
(gap 0..15 mm under its origin), have room for its collider above it and around it; decals must lie 4 mm over a floor.
python3 -I props_check.py  -> report (and props_check.json)"""
import sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
bpy.ops.wm.read_factory_settings(use_empty=True)
import gen_kit as K
import main_shell as MS
import main_open as MO
import main_rooms as MR
MS.build_shell()
MO.build_openings()
MR.build_rooms()
import main_fx as MFX
MFX.build_fx()
import main_signs as MSG
MSG.build_signs()
trees = []
for name, k in K.KBS.items():
    if K.ATLAS.get(name) == 'glass':
        continue
    p = K.CONTRACT['parts'].get(name)
    if p and p['kind'] == 'scale':
        continue                                                   # shutters rolled up at the start
    bm = k.bm.copy()
    trees.append((name, BVHTree.FromBMesh(bm)))
    bm.free()


def cast(o, d, dist=5.0):
    best = None
    for name, t in trees:
        hit = t.ray_cast(Vector(o), Vector(d), dist)
        if hit[0] is not None and (best is None or hit[3] < best[1]):
            best = (name, hit[3], hit[0])
    return best


DATA = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Data/'
P = [340, 16.7443, -360]
q = [0, 0.069756, 0, 0.997564]
yaw = 2 * math.atan2(q[1], q[3])
c_, s_ = math.cos(-yaw), math.sin(-yaw)


def to_b(w):
    dx, dy, dz = w[0] - P[0], w[1] - P[1], w[2] - P[2]
    lx = c_ * dx + s_ * dz
    lz = -s_ * dx + c_ * dz
    return Vector((-lx, -lz, dy))


def dir_b(v):
    lx = c_ * v[0] + s_ * v[2]
    lz = -s_ * v[0] + c_ * v[2]
    return Vector((-lx, -lz, v[1]))


d = json.load(open(DATA + 'Forest_Dressing.json'))
items = [('prop', e) for e in d['props']] + [('note', e) for e in d['notes']]
bad, ok = [], 0
rep = []
for kind, e in items:
    b = to_b(e['p'])
    if not (-19 < b.x < 11 and -9 < b.y < 8 and -4 < b.z < 20):
        continue
    col = e.get('collider', {'center': [0, 0.05, 0], 'size': [0.1, 0.1, 0.1]})
    # the collider's centre and size in Blender axes (the prop's yaw only; Unity y = up)
    qq = e.get('q', [0, 0, 0, 1])
    Rq = Quaternion((qq[3], qq[0], qq[1], qq[2]))                  # Unity quaternion (x, y, z, w)
    cu = Rq @ Vector(col['center'])
    cw = to_b([e['p'][0] + cu.x, e['p'][1] + cu.y, e['p'][2] + cu.z])
    sz = col['size']
    h = abs((Rq @ Vector((0, sz[1], 0))).y) if abs((Rq @ Vector((0, 1, 0))).y) > 0.7 else max(sz)
    h = sz[1]
    down = cast(b + Vector((0, 0, 0.03)), (0, 0, -1), 1.0)
    gap = (0.03 - down[1]) * -1 if down else None
    gap = down[1] - 0.03 if down else None
    up = cast(b + Vector((0, 0, 0.004)), (0, 0, 1), 3.0)
    head = up[1] + 0.004 if up else 9.0
    side = []
    hmin = min(sz[0], sz[2]) / 2
    for dv in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
        r = cast(cw, dv, 1.0)
        side.append(r[1] if r else 9.0)
    problems = []
    if gap is None or gap > 0.02 or gap < -0.003:
        problems.append(f'support gap {gap if gap is None else round(gap * 1000)} mm ({down[0] if down else "-"})')
    if head < h * 0.9:
        problems.append(f'head {head:.3f} < {h:.3f} ({up[0]})')
    if min(side) < hmin * 0.6:
        problems.append(f'side {min(side):.3f} < {hmin:.3f}')
    rec = dict(kind=kind, id=e['id'], pos=[round(v, 3) for v in b], gap_mm=None if gap is None else round(gap * 1000, 1),
               on=down[0] if down else None, problems=problems)
    rep.append(rec)
    if problems:
        bad.append(rec)
    else:
        ok += 1
print('ok', ok, 'bad', len(bad))
for r in bad:
    print(f"  {r['kind']:4s} {r['id']:32s} {r['pos']} on {r['on']}: {'; '.join(r['problems'])}")
# decals: 4 mm over a floor
nd = 0
for e in d['decals']:
    b = to_b(e['p'])
    if not (-19 < b.x < 11 and -9 < b.y < 8 and -4 < b.z < 20):
        continue
    down = cast(b + Vector((0, 0, 0.02)), (0, 0, -1), 0.2)
    g = down[1] - 0.02 if down else None
    if g is None or not (0.0 <= g <= 0.012):
        nd += 1
        print(f"  decal {e['id']:28s} {[round(v, 3) for v in b]} gap {None if g is None else round(g * 1000, 1)} mm on {down[0] if down else '-'}")
print('decals off', nd)
# the sleep zones of the opening: above a mattress, clear of the upper frame
o = json.load(open(DATA + 'Forest_Opening.json'))
for z in o['zones']:
    if not z['id'].startswith('Sleep'):
        continue
    b = to_b(z['p'])
    sz = z['size']
    lo = b.z - sz[1] / 2
    down = cast(Vector((b.x, b.y, lo + 0.05)), (0, 0, -1), 1.0)
    up = cast(Vector((b.x, b.y, lo + 0.05)), (0, 0, 1), 2.0)
    print(f"  zone {z['id']}: bottom {lo:.3f}, mattress {lo + 0.05 - down[1]:.3f} ({down[0]}), free above {up[1] - 0.05 + lo - lo:.3f} ({up[0]})")
json.dump(rep, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'props_check.json'), 'w'),
          indent=0)
