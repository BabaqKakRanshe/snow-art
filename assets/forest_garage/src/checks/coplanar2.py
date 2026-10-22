"""coplanar same-facing overlapping faces in out/main.blend (or the .blend given last) (z-fighting and black AO patches in the bake)"""
import bpy, sys, math
import numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1] if sys.argv[-1].endswith('.blend') else '/home/claude/uaz/out/garage.blend')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('COL_')]
buckets = {}
F = []
for o in meshes:
    M = o.matrix_world
    M3 = M.to_3x3()
    for p in o.data.polygons:
        if p.area < 1e-6:
            continue
        n = (M3 @ p.normal).normalized()
        pts = [M @ o.data.vertices[i].co for i in p.vertices]
        c = sum(pts, Vector()) / len(pts)
        d = n.dot(c)
        fid = len(F)
        F.append((o.name, p.index, n, d, pts, (o.data.materials[p.material_index].name if o.data.materials else '-'),
                  int(round(o.data.attributes['zone'].data[p.index].value)) if 'zone' in o.data.attributes else -1))
        key = (round(n.x * 100), round(n.y * 100), round(n.z * 100), round(d * 1000))
        buckets.setdefault(key, []).append(fid)


def clip(subject, clipper):
    """Sutherland-Hodgman, both convex, counter-clockwise 2D"""
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9
        def inter(p, q):
            x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
            x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-12:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            if inside(q):
                if not inside(p):
                    out.append(inter(p, q))
                out.append(q)
            elif inside(p):
                out.append(inter(p, q))
    return out


def area2(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s / 2


def to2d(pts, n):
    u = (Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))).cross(n).normalized()
    v = n.cross(u)
    P = [(p.dot(u), p.dot(v)) for p in pts]
    return P if area2(P) > 0 else list(reversed(P))


seen = set()
hits = []
for key, ids in buckets.items():
    cand = list(ids)
    for dk in (-1, 1):
        cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
    for i in range(len(ids)):
        a = F[ids[i]]
        for j_ in cand:
            if j_ <= ids[i] or (ids[i], j_) in seen:
                continue
            seen.add((ids[i], j_))
            b = F[j_]
            if a[2].dot(b[2]) < 0.999 or abs(a[3] - b[3]) > 0.0005:
                continue
            pa, pb = to2d(a[4], a[2]), to2d(b[4], a[2])
            inter = clip(pa, pb)
            if len(inter) >= 3:
                ar = abs(area2(inter))
                if ar > 2e-4:
                    hits.append((ar, a[0], a[1], b[0], b[1], tuple(round(v, 3) for v in sum(a[4], Vector()) / len(a[4])), a[5], b[5], a[6], b[6], round(abs(a[3] - b[3]) * 1000, 2)))
hits.sort(reverse=True)
print('coplanar overlaps', len(hits))
import json, collections
DEC = ('M_Gar_Panel', 'M_Glass', 'M_Lamp_')
dec = [h for h in hits if h[6].startswith(DEC) or h[7].startswith(DEC)]
real = [h for h in hits if not (h[6].startswith(DEC) or h[7].startswith(DEC))]
print('with a decal / lens / glass face (offset by design):', len(dec), ' between atlas faces:', len(real))
same = collections.Counter()
for h in real:
    same[(h[8], h[9])] += 1
print('zone pairs:', same.most_common(25))
for h in real[:60]:
    print('  %.4f m2' % h[0], h[1], h[2], '<->', h[3], h[4], 'at', h[5], 'zones', h[8], h[9], 'dz mm', h[10])
json.dump([list(map(str, h)) for h in real], open('coplanar_real.json', 'w'))
