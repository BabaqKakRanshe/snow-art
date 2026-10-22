"""v10 geometry pass, revision b (after the first v10 showed wrong shading on a few small places: door chamfers, liner
fillets, wheel lugs - wedges of unrelated touching pieces mixed up by the collapse, and fillets spanned by one long
triangle). Error-bounded reduction of out/plane_v9_final_v9.blend -> out/plane_v9_final_v10.blend (and a copy
_meshopt.blend for the later normal repair):
 - meshoptimizer per material AND per connected piece (touching pieces never share wedges);
 - target error from the first v10 run (opt_v10_report.json: the binary-searched error), lowered if the sampled
   metrics fail;
 - per-triangle acceptance (opt_lib2.tri_check): every new triangle, at 10 points, must match the source surface
   within N_MAX deg of shading normal and UV_MAX texels; every source triangle of real size (>= (4 tol)^2) at its
   centre too. Places that fail get their source vertices locked and the piece is simplified again, until none fail;
 - optional extra locks from the view comparison (locks JSON: {object: [[x, y, z] world points], radius}).
python3 opt_v10b.py [locks.json]
Results are cached per object (cache_v10b/<name>.npz, keyed by target error, view locks and thresholds), so a rerun
with new view locks only redoes the objects whose inputs changed."""
import bpy, sys, json, time, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import opt_lib as L
import opt_mo as M
import opt_lib2 as L2

SRC = '/home/claude/plane/out/plane_v9_final_v9.blend'
DST = '/home/claude/plane/out/plane_v9_final_v10.blend'
MOPT = '/home/claude/plane/out/plane_v9_final_v10_meshopt.blend'
RES = {'M_Cockpit': 1024, 'M_Interior': 1024, 'M_Floor': 1024, 'M_Seats': 1024, 'M_Fittings': 1024, 'M_Gauges': 2048,
       'M_Airframe': 512, 'M_Wing': 512, 'M_Details': 512, 'M_Webbing': 512, 'M_GaugeGlass': 512}
EXCLUDE = {'src_GlassFixed', 'src_Lights', 'src_StepLadder', 'PedalP_R'}     # PedalP_R carries Socket_Foot_R
NEAR = ('CP_Panel', 'CP_Gauges', 'CP_Glareshield', 'CP_Pedestal', 'CP_Switchgear', 'CP_Radios', 'CP_Compass_Vents',
        'CP_Glovebox', 'CP_Overhead', 'CP_PanelFrame', 'CP_YokeBoot', 'CP_Headsets', 'CP_Seat_', 'Yoke_', 'Pedal',
        'Lever_', 'TrimWheel', 'Pull_', 'Rheo_', 'Belt_', 'Glovebox_Lid')
CABIN = ('CP_Floor', 'CP_Headliner', 'CP_Liner', 'CP_Trims', 'CP_Bulkheads', 'CP_DoorSeals', 'CP_WindshieldFrame',
         'CP_Barrier', 'CP_RearKit', 'CP_PedalLinkage', 'Cabin_Fittings', 'PaxSeat_', 'PilotDoor_R_Holster')
DOORS = ('PilotDoor_L', 'PilotDoor_R', 'CargoDoor_L', 'CargoDoor_R')
N_MAX, UV_MAX = 10.0, 1.0


def category(n):
    if n.startswith('Knob_'):
        return 'knob', 0.0005
    if n in DOORS:
        return 'door', 0.0010
    if n.startswith(NEAR):
        return 'near', 0.0008
    if n.startswith(CABIN):
        return 'cabin', 0.0012
    return 'exterior', 0.0025


import hashlib
args = [a for a in sys.argv[1:] if not a.startswith('--')]
ext_locks = json.load(open(args[0])) if args else {}
prev = {r['name']: r for r in json.load(open(os.path.join(HERE, 'opt_v10_report.json')))}
prev_b_path = os.path.join(HERE, 'opt_v10b_report.json')
CACHE = os.path.join(HERE, 'cache_v10b')
os.makedirs(CACHE, exist_ok=True)
VERSION = 'b8'


def cache_key(n, e):
    h = hashlib.md5(json.dumps([VERSION, n, round(e, 9), N_MAX, UV_MAX, ext_locks.get(n)], sort_keys=True).encode())
    return h.hexdigest()

bpy.ops.wm.open_mainfile(filepath=SRC)
src_meshes = {}
cands = []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name in EXCLUDE or o.name.startswith(('SM_Surv_', 'src_Case', 'Surv_')):
        continue
    t = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if t >= 300:
        cands.append((t, o.name))
cands.sort(reverse=True)
logf = open(os.path.join(HERE, 'opt_v10b.log'), 'w')


def log(s):
    print(s, flush=True)
    logf.write(s + '\n')
    logf.flush()


report = []
t_all = time.time()
TEST = set(os.environ['ONLY'].split(',')) if os.environ.get('ONLY') else None
if TEST:
    MOPT = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/test_v10b.blend'
    prev_b_path = prev_b_path.replace('.json', '_test.json')
for t, n in cands:
    if TEST and n not in TEST:
        continue
    ob = bpy.data.objects[n]
    cat, tol = category(n)
    pr = prev.get(n)
    if pr is None or pr['kept']:
        report.append(dict(name=n, category=cat, tol_mm=tol * 1000, src=t, new=t, error_mm=0.0, kept=True, rounds=0,
                           locked=0, mesh=ob.data.name))
        log(f'{n:24s} kept (as in the first v10 pass)')
        continue
    tex = {i: RES.get(m.name if m else '', 512) for i, m in enumerate(ob.data.materials)}
    w_uv = {k: tol * v for k, v in tex.items()}
    w_n = tol * 12.0
    me0 = ob.data
    src = L.TriData(me0)
    rm = M.RenderMesh(me0)
    vlock = np.zeros(len(rm.co), bool)
    if n in ext_locks:
        from scipy.spatial import cKDTree
        mwi = np.array(ob.matrix_world.inverted())
        pts = np.array(ext_locks[n]['points'])
        loc = pts @ mwi[:3, :3].T + mwi[:3, 3]
        kd = cKDTree(rm.co)
        for i in set(j for js in kd.query_ball_point(loc, ext_locks[n].get('radius', 0.03)) for j in js):
            vlock[i] = True
        log(f'    {n}: {int(vlock.sum())} vertices locked from the view comparison')
    key = cache_key(n, 0.0)
    cpath = os.path.join(CACHE, n + '.npz')
    t0 = time.time()
    if os.path.exists(cpath):
        cz = np.load(cpath, allow_pickle=False)
        if str(cz['key']) == key:
            info = json.loads(str(cz['info']))
            if info['kept']:
                report.append(info)
                log(f'{n:24s} {cat:8s} kept (cache)')
                continue
            me = L2.build_mesh2(n + '_b', rm, cz['tris'], cz['mats'], list(me0.materials))
            old = ob.data
            nm = old.name
            ob.data = me
            if old.users == 0:
                bpy.data.meshes.remove(old)
            me.name = nm
            info['mesh'] = me.name
            report.append(info)
            log(f'{n:24s} {cat:8s} {info["src"]:6d} -> {info["new"]:6d} (cache)')
            continue
    # 1. target error: binary search on the sampled metrics (per-piece simplification, view locks only)
    a_, b_ = 0.0, 3.0 * tol
    e = None
    for it in range(7):
        ee = (a_ + b_) / 2
        tris, mats = L2.simplify_locked(rm, ee, w_uv, w_n, vlock)
        me_t = L2.build_mesh2(n + '_s', rm, tris, mats, list(me0.materials))
        m = L.measure(src, L.TriData(me_t), tex, tol)
        bpy.data.meshes.remove(me_t)
        if L.passes(m, tol, 0.5, 5.0):
            e, a_ = ee, ee
        else:
            b_ = ee
    log(f'    {n}: target error {0 if e is None else e*1000:.3f} mm (first v10 pass {pr["error_mm"]:.3f} mm)')
    me = None
    rounds = 0
    if e is not None:
        # 2. per-triangle acceptance: lock the failing places, simplify again
        for rounds in range(1, 25):
            tris, mats = L2.simplify_locked(rm, e, w_uv, w_n, vlock)
            if me is not None:
                bpy.data.meshes.remove(me)
            me = L2.build_mesh2(n + '_b', rm, tris, mats, list(me0.materials))
            dst = L.TriData(me)
            m = L.measure(src, dst, tex, tol)
            c = L2.tri_check(src, dst, tex, tol)
            fd, fs = L2.tri_fail2(c, dst, src, N_MAX, UV_MAX, (4 * tol) ** 2)
            log(f'    {n} round {rounds}: tris {dst.T}/{src.T} fail dst {int(fd.sum())} src {int(fs.sum())} '
                f'locked {int(vlock.sum())}/{len(vlock)}  sampled {"ok" if L.passes(m, tol, 0.5, 5.0) else "FAIL"}')
            if not fd.any() and not fs.any() and L.passes(m, tol, 0.5, 5.0):
                break
            add = L2.locks_precise(c, fd, fs, dst, src, rm, tol, N_MAX, UV_MAX)
            scale = 1.0
            while not (add & ~vlock).any() and scale < 64:  # nothing new: lock around the failing triangles
                add = L2.locks_for(fd, fs, dst, src, rm, tol, scale)
                scale *= 2
            vlock |= add
        else:
            log(f'    {n}: still failing after {rounds} rounds -> kept')
            bpy.data.meshes.remove(me)
            me = None
    if me is None or dst.T > 0.97 * src.T:
        if me is not None:
            bpy.data.meshes.remove(me)
        info = dict(name=n, category=cat, tol_mm=tol * 1000, src=src.T, new=src.T, error_mm=round((e or 0.0) * 1000, 4),
                    kept=True, rounds=rounds, locked=int(vlock.sum()), mesh=me0.name)
        e = e or 0.0
        report.append(info)
        np.savez(cpath, key=key, info=json.dumps(info), tris=np.zeros((0, 3), np.int64), mats=np.zeros(0, np.int32))
        log(f'{n:24s} {cat:8s} kept ({time.time()-t0:.1f}s)')
        continue
    old = ob.data
    nm = old.name
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    me.name = nm
    info = dict(name=n, category=cat, tol_mm=tol * 1000, src=src.T, new=dst.T, error_mm=round(e * 1000, 4),
                metrics=m, kept=False, rounds=rounds, locked=int(vlock.sum()), mesh=me.name,
                max_n=round(float(c['d_n'].max()), 2), max_uv=round(float(c['d_uv'].max()), 3))
    report.append(info)
    np.savez(cpath, key=key, info=json.dumps(info), tris=tris, mats=mats)
    log(f'{n:24s} {cat:8s} tol {tol*1000:.1f}mm  {src.T:6d} -> {dst.T:6d}  ({100*(1-dst.T/src.T):4.1f} %)  '
        f'rounds {rounds} locked {int(vlock.sum())}  {time.time()-t0:.1f}s')
src_tot = sum(r['src'] for r in report)
new_tot = sum(r['new'] for r in report)
log(f'TOTAL reduced set {src_tot} -> {new_tot} ({100*(1-new_tot/src_tot):.1f} %), {time.time()-t_all:.0f}s')
json.dump(report, open(prev_b_path, 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=MOPT, compress=True)
log('saved ' + MOPT)
