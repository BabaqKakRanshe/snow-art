"""checks of out/station.blend (snow_style.json#checks, the ones that apply to two static props):
- backfaces seen from eye rings (the first hit faces the eye) round each root, eyes at 0.5 / 1.0 / 1.6 / 2.0 m
- coplanar faces facing the same way that overlap (z-fight)
- the nine monitors on Slot_1..9 (Kit_Monitor_CRT as built: x +-0.17, y -0.202..+0.248, z 0..0.31 about its pivot) clear of
  the rack's faces; the ObjectPC case (0.42 x 0.40 x 0.14) on Slot_PC inside the table top; outer sizes against the brief
- every image resolves, no linked libraries, every mesh has the PSX UV map and the atlas material
blender -b --factory-startup --python tools/snow_style/run_bpy.py -- work/forest_station/station_check.py -> out/station_checks.json"""
import os, sys, json, math
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'station.blend')
bpy.ops.wm.open_mainfile(filepath=path)
O = bpy.data.objects
RACK, TABLE = 'Station_MonitorRack_3x3', 'Station_SideTable'
res = {}
for o in O:
    if o.name.startswith('COL_'):
        o.hide_set(True)
        o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene


def tris_world(o):
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    V = np.array([tuple(M @ v.co) for v in me.vertices])
    T = np.array([tuple(t.vertices) for t in me.loop_triangles])
    return V, T


# ---------------------------------------------------------------- 1. backfaces from eye rings
bf = {}
for root in (RACK, TABLE):
    o = O[root]
    V, _ = tris_world(o)
    lo, hi = V.min(0), V.max(0)
    c = (lo + hi) / 2
    hits = back = 0
    worst = []
    for ez in (0.5, 1.0, 1.6, 2.0):
        for k in range(24):
            a = 2 * math.pi * k / 24
            if root == RACK and math.sin(a) > 0.35:                      # the rack stands against a wall (+y): no eyes behind
                continue
            eye = Vector((c[0] + 2.2 * math.cos(a), c[1] + 2.2 * math.sin(a), ez))
            for gx in np.linspace(lo[0] + 0.0037, hi[0] - 0.0037, 9):
                for gz in np.linspace(lo[2] + 0.0113, hi[2] - 0.0113, 9):
                    for gy in (lo[1] + 0.0029, c[1] + 0.0011, hi[1] - 0.0029):
                        tgt = Vector((gx, gy, gz))
                        d = (tgt - eye).normalized()
                        ok, loc, nor, idx, ob, _ = sc.ray_cast(dg, eye, d)
                        if not ok or ob.name != root:
                            continue
                        hits += 1
                        if nor.dot(d) > 1e-4:
                            back += 1
                            if len(worst) < 8:
                                worst.append(dict(eye=[round(v, 2) for v in eye], hit=[round(v, 3) for v in loc],
                                                  normal=[round(v, 3) for v in nor], dot=round(nor.dot(d), 3)))
    bf[root] = dict(rays_hit=hits, backface_hits=back, examples=worst)
res['backfaces'] = bf

# ---------------------------------------------------------------- 2. coplanar same-facing overlaps (z-fight)


def inside_convex(q, poly, eps=1e-5):
    n = len(poly)
    sg = 0
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        cr = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if abs(cr) < eps * max(1e-9, np.hypot(*(b - a))):
            return False
        s_ = 1 if cr > 0 else -1
        if sg == 0:
            sg = s_
        elif s_ != sg:
            return False
    return True


def real_overlap(a, b):
    """interior sample points of the convex polygon a that lie strictly inside b (2D)"""
    for k in range(1, len(a) - 1):
        for u in np.linspace(0.05, 0.9, 7):
            for v in np.linspace(0.05, 0.9 - u, 5):
                q = a[0] + (a[k] - a[0]) * u + (a[k + 1] - a[0]) * v
                if inside_convex(q, b):
                    return True
    return False

zf = {}
for root in (RACK, TABLE):
    o = O[root]
    me = o.data
    M = o.matrix_world
    F = []
    for p in me.polygons:
        n = (M.to_3x3() @ p.normal).normalized()
        pts = np.array([tuple(M @ me.vertices[i].co) for i in p.vertices])
        F.append((n, float(n.dot(Vector(pts[0]))), pts, p.area))
    bad = []
    for i in range(len(F)):
        ni, di, pi, ai = F[i]
        for j in range(i + 1, len(F)):
            nj, dj, pj, aj = F[j]
            if ni.dot(nj) < 0.999 or abs(di - dj) > 0.0008:
                continue
            ax = int(np.argmax(np.abs(np.array(ni))))
            keep = [k for k in range(3) if k != ax]
            lo = np.maximum(pi[:, keep].min(0), pj[:, keep].min(0))
            hi = np.minimum(pi[:, keep].max(0), pj[:, keep].max(0))
            ov = np.prod(np.maximum(hi - lo, 0))
            if ov > 1e-6 and real_overlap(pi[:, keep], pj[:, keep]):
                bad.append(dict(a=i, b=j, overlap_cm2=round(ov * 1e4, 2), at=[round(v, 3) for v in pi.mean(0)]))
    zf[root] = dict(faces=len(F), overlaps=len(bad), examples=bad[:6])
res['zfight'] = zf

# ---------------------------------------------------------------- 3. slot clearances
V, T = tris_world(O[RACK])
off = O[RACK].matrix_world.translation
samp = []
for t in T:
    a, b, c = V[t[0]], V[t[1]], V[t[2]]
    for u in np.linspace(0, 1, 14):
        for v in np.linspace(0, 1 - u, max(2, int(14 * (1 - u)))):
            samp.append(a + (b - a) * u + (c - a) * v)
samp = np.array(samp)
mon = []
for i in range(1, 10):
    s = O[f'Slot_{i}'].matrix_world.translation
    lo = np.array((s.x - 0.17, s.y - 0.202, s.z)) + 0.001
    hi = np.array((s.x + 0.17, s.y + 0.248, s.z + 0.31)) - 0.001
    inside = np.all((samp > lo) & (samp < hi), axis=1).sum()
    # the gaps: above the monitor to the next tray's bottom rim, to the neighbours, to the back face (y 0)
    above = samp[(samp[:, 0] > lo[0]) & (samp[:, 0] < hi[0]) & (samp[:, 1] > lo[1]) & (samp[:, 1] < hi[1]) & (samp[:, 2] > hi[2])]
    gap_up = float(above[:, 2].min() - (s.z + 0.31)) if len(above) else None
    mon.append(dict(slot=f'Slot_{i}', pos_root=[round(v, 4) for v in (s - off)], intersecting_samples=int(inside),
                    gap_above_m=round(gap_up, 3) if gap_up is not None else None,
                    back_gap_m=round(float(-(s.y - off.y) - 0.248), 3), front_inside_m=round(float(0.52 + (s.y - off.y) - 0.202), 3)))
res['monitor_slots'] = mon
VT, TT = tris_world(O[TABLE])
toff = O[TABLE].matrix_world.translation
sp = O['Slot_PC'].matrix_world.translation - toff
top = VT[:, 2].max() - toff.z
case = dict(x=(sp.x - 0.21, sp.x + 0.21), y=(sp.y - 0.20, sp.y + 0.20))
tb = dict(x=(VT[:, 0].min() - toff.x, VT[:, 0].max() - toff.x), y=(VT[:, 1].min() - toff.y, VT[:, 1].max() - toff.y))
res['pc_slot'] = dict(slot_root=[round(v, 4) for v in sp], table_top_z=round(float(top), 4),
                      case_inside_top=bool(case['x'][0] >= tb['x'][0] and case['x'][1] <= tb['x'][1] and
                                           case['y'][0] >= tb['y'][0] and case['y'][1] <= tb['y'][1]),
                      case_back_to_edge_m=round(float(tb['y'][1] - case['y'][1]), 4),
                      stock_keyboard_front_overhang_m=round(float(tb['y'][0] - (sp.y - 0.495)), 4),
                      stock_mouse_overhang_m=dict(front=round(float(tb['y'][0] - (sp.y - 0.40 - 0.056)), 4),
                                                  right=round(float((sp.x + 0.33 + 0.031) - tb['x'][1]), 4)))
# ---------------------------------------------------------------- 4. sizes against the brief
sz = {}
for root, want in ((RACK, dict(w_max=1.25, h=1.75, d=0.52)), (TABLE, dict(w=0.70, d=0.62, h=0.72))):
    o = O[root]
    Vr, _ = tris_world(o)
    Vr = Vr - np.array(o.matrix_world.translation)
    lo, hi = Vr.min(0), Vr.max(0)
    sz[root] = dict(x=[round(lo[0], 4), round(hi[0], 4)], y=[round(lo[1], 4), round(hi[1], 4)], z=[round(lo[2], 4), round(hi[2], 4)],
                    size_wdh=[round(hi[0] - lo[0], 4), round(hi[1] - lo[1], 4), round(hi[2] - lo[2], 4)], brief=want)
res['sizes'] = sz
assert sz[RACK]['size_wdh'][0] <= 1.25 + 1e-6, 'rack wider than 1.25'
# ---------------------------------------------------------------- 5. files
img = []
for im in bpy.data.images:
    if im.source == 'FILE':
        p = bpy.path.abspath(im.filepath)
        img.append(dict(name=im.name, path=im.filepath, exists=os.path.exists(p)))
res['images'] = img
res['libraries'] = [l.filepath for l in bpy.data.libraries]
mesh = {}
for o in O:
    if o.type == 'MESH' and not o.name.startswith('COL_'):
        mesh[o.name] = dict(uv=[u.name for u in o.data.uv_layers], materials=[s.material.name for s in o.material_slots if s.material],
                            tris=sum(len(p.vertices) - 2 for p in o.data.polygons))
res['meshes'] = mesh
res['empties'] = {o.name: dict(parent=o.parent.name if o.parent else None,
                               local=[round(v, 4) for v in o.matrix_local.translation]) for o in O if o.type == 'EMPTY'}
json.dump(res, open(os.path.join(os.path.dirname(path), 'station_checks.json'), 'w'), indent=1)
print('CHECKS', json.dumps({k: res[k] for k in ('backfaces', 'zfight', 'pc_slot', 'sizes')}, indent=1))
print('MON', [(m['slot'], m['intersecting_samples'], m['gap_above_m'], m['back_gap_m'], m['front_inside_m']) for m in mon])
print('FILES', img, res['libraries'], mesh)
