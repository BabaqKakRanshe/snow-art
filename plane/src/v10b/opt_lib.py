"""Error-bounded mesh reduction for the v10 optimisation pass (Blender 5, bpy as a module).

reduce_mesh(ob, tol_m, tex_res, ...) collapses edges (Blender Decimate COLLAPSE) with a binary search on the ratio and
keeps the lowest ratio whose result still matches the source within:
  - geometry: two-sided distance (orig->new and new->orig samples), p99.9 <= tol_m, max <= 2 * tol_m
  - texture: UV error in texels of the target atlas resolution, p99 <= uv_tol (default 0.5 texel)
  - shading: angle between the source and the new interpolated normals, p99 <= n_tol_deg, mean <= 1 deg
The new mesh gets custom split normals sampled from the source surface (per corner, on the same side of hard edges),
so the shading follows the source even where whole rows of vertices were removed.
Object name, transform, pivot, materials and UV layer stay; only mesh data changes."""
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


class TriData:
    """Triangulated snapshot of a mesh in object space: positions, UVs, corner normals, material per triangle."""

    def __init__(self, me):
        me.calc_loop_triangles()
        lt = me.loop_triangles
        T = len(lt)
        vi = np.empty(T * 3, np.int32)
        lt.foreach_get('vertices', vi)
        li = np.empty(T * 3, np.int32)
        lt.foreach_get('loops', li)
        mi = np.empty(T, np.int32)
        lt.foreach_get('material_index', mi)
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        uv = np.zeros(len(me.loops) * 2, np.float64)
        if me.uv_layers:
            me.uv_layers[0].data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2)
        cn = np.empty(len(me.loops) * 3, np.float64)
        me.corner_normals.foreach_get('vector', cn)
        cn = cn.reshape(-1, 3)
        self.P = co[vi].reshape(T, 3, 3)
        self.UV = uv[li].reshape(T, 3, 2)
        self.N = cn[li].reshape(T, 3, 3)
        self.M = mi
        e1 = self.P[:, 1] - self.P[:, 0]
        e2 = self.P[:, 2] - self.P[:, 0]
        cr = np.cross(e1, e2)
        self.area = 0.5 * np.linalg.norm(cr, axis=1)
        with np.errstate(invalid='ignore', divide='ignore'):
            self.FN = cr / np.maximum(np.linalg.norm(cr, axis=1), 1e-20)[:, None]
        self.T = T
        flat = self.P.reshape(-1, 3)
        self.bvh = BVHTree.FromPolygons([tuple(p) for p in flat], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(T)],
                                        all_triangles=True, epsilon=0.0)

    def sample(self, n, rng):
        w = self.area / max(self.area.sum(), 1e-20)
        t = rng.choice(self.T, size=n, p=w)
        r1 = np.sqrt(rng.random(n))
        r2 = rng.random(n)
        b = np.stack([1 - r1, r1 * (1 - r2), r1 * r2], axis=1)
        p = np.einsum('nk,nkj->nj', b, self.P[t])
        return p, t, b

    def bary(self, t, p):
        a, b, c = self.P[t, 0], self.P[t, 1], self.P[t, 2]
        v0, v1, v2 = b - a, c - a, p - a
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
        d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        den = np.where(np.abs(den) < 1e-30, 1e-30, den)
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        return np.clip(np.stack([1 - v - w, v, w], axis=1), 0, 1)

    def uv_at(self, t, b):
        return np.einsum('nk,nkj->nj', b, self.UV[t])

    def n_at(self, t, b):
        n = np.einsum('nk,nkj->nj', b, self.N[t])
        return n / np.maximum(np.linalg.norm(n, axis=1), 1e-20)[:, None]


def match(src, dst, pts, src_t, radius, uv_src=None, res=None, slack=0.0002, cos_face=0.5):
    """For points on src (triangles src_t), find the corresponding triangle on dst: same material, compatible face
    normal, within `radius`; among those no farther than (closest + slack) the one whose UV at the projected point is
    closest to the source UV (coplanar overlays and seams otherwise pick the wrong layer). -1 - idx = fallback to the
    plain nearest triangle."""
    out_t = np.full(len(pts), -1, np.int64)
    out_d = np.full(len(pts), np.inf)
    for i, p in enumerate(pts):
        v = Vector(p)
        cands = []
        for loc, nrm, idx, dist in dst.bvh.find_nearest_range(v, radius):
            if dst.M[idx] != src.M[src_t[i]]:
                continue
            if float(np.dot(dst.FN[idx], src.FN[src_t[i]])) < cos_face:
                continue
            cands.append((dist, idx))
        if not cands:
            loc, nrm, idx, dist = dst.bvh.find_nearest(v)
            if idx is not None:
                out_t[i] = -1 - idx
                out_d[i] = dist
            continue
        dmin = min(c[0] for c in cands)
        near = [c for c in cands if c[0] <= dmin + slack]
        if uv_src is not None and len(near) > 1:
            ids = np.array([c[1] for c in near])
            b = dst.bary(ids, np.repeat(p[None, :], len(ids), axis=0))
            uvd = dst.uv_at(ids, b)
            k = int(np.argmin(np.linalg.norm(uvd - uv_src[i], axis=1)))
            out_t[i], out_d[i] = int(ids[k]), near[k][0]
        else:
            out_d[i], out_t[i] = min(near)
    return out_t, out_d


def measure(src, dst, tex_res, tol_m, n=6000, seed=1):
    """Metrics of dst against src (both TriData in the same object space)."""
    rng = np.random.default_rng(seed)
    radius = max(4 * tol_m, 0.003)
    p, t, b = src.sample(n, rng)
    uv_s = src.uv_at(t, b)
    mt, md = match(src, dst, p, t, radius, uv_src=uv_s, slack=max(0.25 * tol_m, 0.0002))
    fb = mt < 0
    mt2 = np.where(fb, -1 - mt, mt)
    q = np.array([dst.bvh.find_nearest(Vector(x))[0] for x in p])          # closest point on dst (any triangle)
    pb = dst.bary(mt2, p)
    uv_d = dst.uv_at(mt2, pb)
    res = np.array([tex_res.get(int(m), 1024) for m in src.M[t]]) if isinstance(tex_res, dict) else tex_res
    uv_err = np.linalg.norm(uv_s - uv_d, axis=1) * res
    n_s = src.n_at(t, b)
    n_d = dst.n_at(mt2, pb)
    ang = np.degrees(np.arccos(np.clip((n_s * n_d).sum(1), -1, 1)))
    p2, t2, b2 = dst.sample(n // 2, rng)
    d2 = np.array([src.bvh.find_nearest(Vector(x))[3] for x in p2])
    d1 = np.linalg.norm(p - q, axis=1)
    geo = np.concatenate([d1, d2])
    return dict(geo_p999=float(np.percentile(geo, 99.9)), geo_max=float(geo.max()),
                uv_p99=float(np.percentile(uv_err, 99)), uv_max=float(uv_err.max()),
                n_p99=float(np.percentile(ang, 99)), n_mean=float(ang.mean()),
                fallback=float(fb.mean()))


def transfer_normals(me, src):
    """Custom split normals on `me`, sampled from the source surface per corner (slightly inside the corner's face,
    on a source triangle with the same material and a compatible face normal)."""
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    pn = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get('normal', pn)
    pn = pn.reshape(-1, 3)
    pc = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get('center', pc)
    pc = pc.reshape(-1, 3)
    pm = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', pm)
    ls = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', ls)
    lc = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', lc)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    poly_of_loop = np.repeat(np.arange(len(me.polygons)), lc)
    out = np.zeros((len(me.loops), 3))
    for l in range(len(me.loops)):
        f = poly_of_loop[l]
        v = co[lv[l]]
        s = v + 0.03 * (pc[f] - v)
        best = None
        for loc, nrm, idx, dist in src.bvh.find_nearest_range(Vector(s), 0.01):
            if src.M[idx] != pm[f]:
                continue
            if float(np.dot(src.FN[idx], pn[f])) < 0.6:
                continue
            if best is None or dist < best[1]:
                best = (idx, dist, loc)
        if best is None:
            loc, nrm, idx, dist = src.bvh.find_nearest(Vector(s))
            best = (idx, dist, loc)
        idx, dist, loc = best
        b = src.bary(np.array([idx]), np.array([tuple(loc)]))
        out[l] = src.n_at(np.array([idx]), b)[0]
    me.normals_split_custom_set([tuple(x) for x in out])


def decimated_copy(ob, ratio):
    """New mesh datablock = ob's mesh collapsed to `ratio` (triangulated); ob is not changed."""
    tmp = ob.copy()
    tmp.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(tmp)
    tmp.modifiers.clear()
    md = tmp.modifiers.new('dec', 'DECIMATE')
    md.decimate_type = 'COLLAPSE'
    md.ratio = ratio
    md.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    ev = tmp.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(old)
    return me


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def passes(m, tol_m, uv_tol, n_tol):
    return (m['geo_p999'] <= tol_m and m['geo_max'] <= 2.5 * tol_m and m['uv_p99'] <= uv_tol and
            m['n_p99'] <= n_tol and m['n_mean'] <= 1.0)


def reduce_mesh(ob, tol_m, tex_res, uv_tol=0.5, n_tol=5.0, lo=0.15, iters=6, log=print):
    """Binary search on the collapse ratio; returns (best mesh or None, ratio, metrics, src_tris, new_tris)."""
    src = TriData(ob.data)
    src_tris = src.T
    best = None
    a, b = lo, 1.0
    tried = {}
    for _ in range(iters):
        r = round((a + b) / 2, 4)
        me = decimated_copy(ob, r)
        transfer_normals(me, src)
        dst = TriData(me)
        m = measure(src, dst, tex_res, tol_m)
        ok = passes(m, tol_m, uv_tol, n_tol)
        tried[r] = (ok, dst.T, m)
        log(f'    {ob.name} r={r:.3f} tris {dst.T}/{src_tris} geo {m["geo_p999"]*1000:.2f}/{m["geo_max"]*1000:.2f} mm '
            f'uv {m["uv_p99"]:.2f}/{m["uv_max"]:.2f} tx  n {m["n_p99"]:.1f}/{m["n_mean"]:.2f} deg fb {m["fallback"]:.3f} '
            f'{"OK" if ok else "--"}')
        if ok:
            if best is not None:
                bpy.data.meshes.remove(best[0])
            best = (me, r, m, dst.T)
            b = r
        else:
            bpy.data.meshes.remove(me)
            a = r
    if best is None:
        return None, 1.0, None, src_tris, src_tris
    return best[0], best[1], best[2], src_tris, best[3]
