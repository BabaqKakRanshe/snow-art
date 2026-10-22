"""Per-triangle acceptance check for the v10 reduction (added after the v10 wheel lugs showed 56 deg shading errors
that the sampled p99 metrics of opt_lib.measure let through: the error sat on <1 % of the area).

tri_check(src, dst, tex_res, tol_m) -> dict of arrays
  d_n, d_uv : per dst triangle, worst over 10 points inside it of the best-matching src surface (same material,
              compatible face, within the geometric tolerance): shading-normal angle (deg) and UV error (texels)
  s_n, s_uv : per src triangle, the same at its centroid against the dst surface (catches narrow src features that a
              big dst triangle spans)
"Best matching" = among the candidate faces no farther than the nearest + slack, the one with the smallest error, so a
point next to a hard edge or a UV seam is never judged against the face on the other side."""
import numpy as np
from mathutils import Vector

def closest_on_tri(p, A, B, C):
    """exact (float64) closest points of p (n,3) on triangles A,B,C (n,3 each): (q, bary). Blender's BVH loses
    precision on long slivers (a 3 m x 1.5 mm seat-rail chamfer came back 70 mm away from a point lying on it)."""
    p = np.asarray(p, np.float64); A = np.asarray(A, np.float64); B = np.asarray(B, np.float64); C = np.asarray(C, np.float64)
    n = len(p)
    bary = np.zeros((n, 3))
    done = np.zeros(n, bool)
    ab, ac, ap = B - A, C - A, p - A
    d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    m = (d1 <= 0) & (d2 <= 0)
    bary[m] = (1, 0, 0); done |= m
    bp = p - B
    d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1)
    m = ~done & (d3 >= 0) & (d4 <= d3)
    bary[m] = (0, 1, 0); done |= m
    vc = d1 * d4 - d3 * d2
    m = ~done & (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    if m.any():
        v = d1[m] / np.where(np.abs(d1[m] - d3[m]) < 1e-300, 1e-300, d1[m] - d3[m])
        bary[m] = np.stack([1 - v, v, np.zeros_like(v)], 1)
    done |= m
    cp = p - C
    d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    m = ~done & (d6 >= 0) & (d5 <= d6)
    bary[m] = (0, 0, 1); done |= m
    vb = d5 * d2 - d1 * d6
    m = ~done & (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    if m.any():
        w = d2[m] / np.where(np.abs(d2[m] - d6[m]) < 1e-300, 1e-300, d2[m] - d6[m])
        bary[m] = np.stack([1 - w, np.zeros_like(w), w], 1)
    done |= m
    va = d3 * d6 - d5 * d4
    m = ~done & (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    if m.any():
        den = (d4[m] - d3[m]) + (d5[m] - d6[m])
        w = (d4[m] - d3[m]) / np.where(np.abs(den) < 1e-300, 1e-300, den)
        bary[m] = np.stack([np.zeros_like(w), 1 - w, w], 1)
    done |= m
    m = ~done
    if m.any():
        den = va[m] + vb[m] + vc[m]
        den = np.where(np.abs(den) < 1e-300, 1e-300, den)
        v = vb[m] / den; w = vc[m] / den
        bary[m] = np.stack([1 - v - w, v, w], 1)
    q = bary[:, :1] * A + bary[:, 1:2] * B + bary[:, 2:3] * C
    return q, bary


class Near:
    """candidate search on a TriData: Blender BVH range query plus every sliver triangle (aspect > 40) whose box is
    within the radius; distances and barycentrics recomputed exactly"""

    def __init__(self, td):
        self.td = td
        e = np.stack([td.P[:, 1] - td.P[:, 0], td.P[:, 2] - td.P[:, 1], td.P[:, 0] - td.P[:, 2]], 1)
        L_ = np.linalg.norm(e, axis=2).max(1)
        h = 2 * td.area / np.maximum(L_, 1e-20)
        self.sl = np.where(L_ > 40 * np.maximum(h, 1e-12))[0]
        self.lo = td.P[self.sl].min(1)
        self.hi = td.P[self.sl].max(1)

    def query(self, p, radius):
        from mathutils import Vector
        ids = [idx for loc, nrm, idx, dist in self.td.bvh.find_nearest_range(Vector(p), radius)]
        if len(self.sl):
            m = np.all((p >= self.lo - radius) & (p <= self.hi + radius), axis=1)
            ids += self.sl[m].tolist()
        if not ids:
            return np.zeros(0, np.int64), np.zeros(0), np.zeros((0, 3)), np.zeros((0, 3))
        ids = np.unique(np.array(ids, np.int64))
        P = self.td.P[ids]
        q, b = closest_on_tri(np.repeat(p[None, :], len(ids), 0), P[:, 0], P[:, 1], P[:, 2])
        d = np.linalg.norm(q - p, axis=1)
        k = d <= radius
        return ids[k], d[k], b[k], q[k]

    def nearest(self, p, radius):
        ids, d, b, q = self.query(p, radius)
        if len(ids):
            i = int(np.argmin(d))
            return ids[i], d[i], b[i]
        from mathutils import Vector
        loc, nrm, idx, dist = self.td.bvh.find_nearest(Vector(p))
        if idx is None:
            return None, None, None
        q, b = closest_on_tri(p[None, :], self.td.P[idx:idx + 1, 0], self.td.P[idx:idx + 1, 1], self.td.P[idx:idx + 1, 2])
        return idx, float(np.linalg.norm(q[0] - p)), b[0]


BARY = np.array([[1 / 3, 1 / 3, 1 / 3], [.8, .1, .1], [.1, .8, .1], [.1, .1, .8], [.45, .45, .1], [.1, .45, .45],
                 [.45, .1, .45], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]])


def _res(tex_res, m):
    return tex_res.get(int(m), 1024) if isinstance(tex_res, dict) else tex_res


def _point_errors(A, B, pts, tri_a, n_a, uv_a, tex_res, radius, slack, nearB=None):
    """for points on A (triangles tri_a, interpolated normals n_a, uvs uv_a): best-match errors against B
    (vectorised: candidate pairs from the BVH range query + slivers, exact distances, per-point minima)"""
    from mathutils import Vector
    nearB = nearB or Near(B)
    n = len(pts)
    pi_l, ti_l = [], []
    bvh = B.bvh
    for i, p in enumerate(pts):
        r = bvh.find_nearest_range(Vector(p), radius)
        if r:
            pi_l.append(np.full(len(r), i, np.int64))
            ti_l.append(np.fromiter((x[2] for x in r), np.int64, len(r)))
    sl = nearB.sl
    if len(sl):
        for s0 in range(0, n, 4096):
            P = pts[s0:s0 + 4096]
            m = np.all((P[:, None, :] >= nearB.lo[None] - radius) & (P[:, None, :] <= nearB.hi[None] + radius), axis=2)
            ii, jj = np.nonzero(m)
            if len(ii):
                pi_l.append(ii + s0)
                ti_l.append(sl[jj])
    if pi_l:
        pi = np.concatenate(pi_l); ti = np.concatenate(ti_l)
        key = np.unique(pi * (B.T + 1) + ti)
        pi, ti = key // (B.T + 1), key % (B.T + 1)
    else:
        pi = np.zeros(0, np.int64); ti = np.zeros(0, np.int64)
    q, b = closest_on_tri(pts[pi], B.P[ti, 0], B.P[ti, 1], B.P[ti, 2])
    d = np.linalg.norm(q - pts[pi], axis=1)
    ok = (d <= radius) & (B.M[ti] == A.M[tri_a[pi]]) & ((B.FN[ti] * A.FN[tri_a[pi]]).sum(1) >= 0.5)
    pi, ti, b, d = pi[ok], ti[ok], b[ok], d[ok]
    fb = np.ones(n, bool)
    fb[pi] = False
    # points without a compatible candidate: plain nearest triangle (fallback)
    for i in np.where(fb)[0]:
        idx, dist, bb = nearB.nearest(pts[i], 1e9)
        if idx is None:
            continue
        pi = np.append(pi, i); ti = np.append(ti, idx); b = np.vstack([b, bb[None, :]]); d = np.append(d, dist)
    dmin = np.full(n, np.inf)
    np.minimum.at(dmin, pi, d)
    near = d <= dmin[pi] + slack
    pi, ti, b = pi[near], ti[near], b[near]
    nb = B.n_at(ti, b)
    ub = B.uv_at(ti, b)
    ang = np.degrees(np.arccos(np.clip((nb * n_a[pi]).sum(1), -1, 1)))
    res = np.array([_res(tex_res, m) for m in A.M[tri_a[pi]]]) if isinstance(tex_res, dict) else tex_res
    uve = np.linalg.norm(ub - uv_a[pi], axis=1) * res
    n_err = np.full(n, np.inf); uv_err = np.full(n, np.inf)
    np.minimum.at(n_err, pi, ang)
    np.minimum.at(uv_err, pi, uve)
    n_err[~np.isfinite(n_err)] = 0.0
    uv_err[~np.isfinite(uv_err)] = 0.0
    return n_err, uv_err, fb


def tri_check(src, dst, tex_res, tol_m):
    radius = max(2.5 * tol_m, 0.0015)
    slack = max(0.5 * tol_m, 0.0003)
    # dst triangles, 10 points each
    T = dst.T
    t = np.repeat(np.arange(T), len(BARY))
    b = np.tile(BARY, (T, 1))
    p = np.einsum('nk,nkj->nj', b, dst.P[t])
    n_d = dst.n_at(t, b)
    uv_d = dst.uv_at(t, b)
    ne, ue, fb = _point_errors(dst, src, p, t, n_d, uv_d, tex_res, radius, slack, Near(src))
    d_n = ne.reshape(T, -1).max(1)
    d_uv = ue.reshape(T, -1).max(1)
    d_fb = fb.reshape(T, -1).any(1)
    pt = dict(p=p, t=t, n=ne, uv=ue, fb=fb)
    # src triangles, centroid
    S = src.T
    ts = np.arange(S)
    bs = np.tile(BARY[:1], (S, 1))
    ps = np.einsum('nk,nkj->nj', bs, src.P[ts])
    n_s = src.n_at(ts, bs)
    uv_s = src.uv_at(ts, bs)
    ne2, ue2, fb2 = _point_errors(src, dst, ps, ts, n_s, uv_s, tex_res, radius, slack, Near(dst))
    return dict(d_n=d_n, d_uv=d_uv, d_fb=d_fb, s_n=ne2, s_uv=ue2, s_fb=fb2, pt=pt)


def tri_fail(c, dst, src, n_max, uv_max, min_area=1e-8):
    """boolean masks of failing dst / src triangles (degenerate triangles ignored)"""
    fd = ((c['d_n'] > n_max) | (c['d_uv'] > uv_max)) & (dst.area > min_area)
    fs = ((c['s_n'] > n_max) | (c['s_uv'] > uv_max)) & (src.area > min_area)
    return fd, fs


# ---------------------------------------------------------------------------------------------------------------------
# v10b reduction core: meshoptimizer per connected piece, with vertex locks
import ctypes
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import opt_mo as M
import meshoptimizer as mo


def pieces(rm, m):
    """triangles of material m grouped by connected piece (mesh-vertex connectivity): list of index arrays into
    rm.tris. Separate pieces that merely touch (coincident vertices of different mesh vertices) stay separate, so
    meshoptimizer never treats them as one vertex with several wedges."""
    sel = np.where(rm.mat == m)[0]
    tv = rm.rv_vert[rm.tris[sel]]                         # (k,3) mesh vertices
    nv = int(rm.rv_vert.max()) + 1
    r = np.concatenate([tv[:, 0], tv[:, 1], tv[:, 2]])
    c = np.concatenate([tv[:, 1], tv[:, 2], tv[:, 0]])
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(nv, nv))
    _, lab = connected_components(g, directed=False)
    tl = lab[tv[:, 0]]
    order = np.argsort(tl, kind='stable')
    tl_s = tl[order]
    cuts = np.flatnonzero(np.diff(tl_s)) + 1
    return [sel[g_] for g_ in np.split(order, cuts)]


def simplify_locked(rm, target_error, w_uv, w_n, vlock=None, lock_border=True, min_piece=4):
    """meshoptimizer per material and connected piece; vlock: bool per MESH vertex (never removed)."""
    out_t, out_m = [], []
    for m in np.unique(rm.mat):
        wu = w_uv.get(int(m), max(w_uv.values())) if isinstance(w_uv, dict) else w_uv
        wts = np.array([w_n, w_n, w_n, wu, wu], np.float32)
        opts = mo.SIMPLIFY_ERROR_ABSOLUTE | (mo.SIMPLIFY_LOCK_BORDER if lock_border else 0)
        for ti in pieces(rm, m):
            tri = rm.tris[ti]
            if len(ti) < min_piece:
                out_t.append(tri)
                out_m.append(np.full(len(tri), m, np.int32))
                continue
            vids, local = np.unique(tri.reshape(-1), return_inverse=True)
            idx = np.ascontiguousarray(local.astype(np.uint32))
            pos = np.ascontiguousarray(rm.rv_pos[vids], np.float32)
            att = np.ascontiguousarray(np.concatenate([rm.rv_n[vids], rm.rv_uv[vids]], axis=1), np.float32)
            lk = None
            if vlock is not None:
                lk = np.ascontiguousarray(vlock[rm.rv_vert[vids]].astype(np.uint8))
                if lk.all():
                    out_t.append(tri)
                    out_m.append(np.full(len(tri), m, np.int32))
                    continue
            o, _ = M._simplify_attr(idx, pos, att, wts, float(target_error), opts, lock=lk)
            t2 = vids[o.astype(np.int64)].reshape(-1, 3)
            out_t.append(t2)
            out_m.append(np.full(len(t2), m, np.int32))
    return np.concatenate(out_t), np.concatenate(out_m)


def tri_fail2(c, dst, src, n_max, uv_max, src_min_area, min_area=1e-8):
    """failing dst triangles (any non-degenerate size; fallback = fail) and src triangles (>= src_min_area)"""
    fd = (((c['d_n'] > n_max) | (c['d_uv'] > uv_max)) | c['d_fb']) & (dst.area > min_area)
    fs = ((c['s_n'] > n_max) | (c['s_uv'] > uv_max)) & (src.area >= src_min_area)
    return fd, fs


def locks_for(fd, fs, dst, src, rm, tol, scale=1.0):
    """mesh vertices of the source to lock so the failing places keep their source triangles"""
    co = rm.co
    lock = np.zeros(len(co), bool)
    # src failing triangles: their own vertices (snap TriData positions back to mesh vertex ids)
    from scipy.spatial import cKDTree
    kd = cKDTree(co)
    if fs.any():
        if scale <= 1.0:
            P = src.P[fs].reshape(-1, 3)
            d, i = kd.query(P)
            lock[i[d < 1e-7]] = True
        else:
            cen = src.P[fs].mean(axis=1)
            rad = scale * (np.linalg.norm(src.P[fs] - cen[:, None, :], axis=2).max(1) + max(tol, 0.0005))
            for cc, rr in zip(cen, rad):
                for i in kd.query_ball_point(cc, rr):
                    lock[i] = True
    if fd.any():
        cen = dst.P[fd].mean(axis=1)
        rad = scale * (np.linalg.norm(dst.P[fd] - cen[:, None, :], axis=2).max(1) + max(tol, 0.0005))
        for cc, rr in zip(cen, rad):
            for i in kd.query_ball_point(cc, rr):
                lock[i] = True
    return lock


def locks_precise(c, fd, fs, dst, src, rm, tol, n_max, uv_max):
    """lock only the source vertices next to the failing points: for every failing sample point of a failing dst
    triangle the three vertices of the nearest source triangle; for failing source triangles their own vertices"""
    from scipy.spatial import cKDTree
    from mathutils import Vector
    lock = np.zeros(len(rm.co), bool)
    kd = cKDTree(rm.co)
    pt = c['pt']
    bad = ((pt['n'] > n_max) | (pt['uv'] > uv_max) | pt['fb']) & fd[pt['t']]
    corners = []
    ns = Near(src)
    for p in pt['p'][bad]:
        idx, dist, b = ns.nearest(p, max(2.5 * tol, 0.0015))
        if idx is not None:
            corners.append(src.P[idx])
    if fs.any():
        corners.extend(list(src.P[fs]))
    if corners:
        C = np.concatenate(corners).reshape(-1, 3)
        d, i = kd.query(C)
        lock[i[d < 1e-7]] = True
    return lock


def build_mesh2(name, rm, tris, mats, materials):
    """opt_mo.build_mesh for v10b: triangles whose corners coincide (zero area: nothing to draw) are dropped - at a
    point where several pieces of a fan meet (rivet tips modelled as a collapsed ring) they made Blender decode the
    stored normals into garbage; edges where the corner normals jump are marked sharp (sharp_lib)."""
    import sharp_lib
    P = rm.co[rm.rv_vert[tris]]
    d01 = np.linalg.norm(P[:, 0] - P[:, 1], axis=1)
    d12 = np.linalg.norm(P[:, 1] - P[:, 2], axis=1)
    d20 = np.linalg.norm(P[:, 2] - P[:, 0], axis=1)
    ok = (d01 > 1e-9) & (d12 > 1e-9) & (d20 > 1e-9)
    me = M.build_mesh(name, rm, tris[ok], mats[ok], materials)
    sharp_lib.set_normals(me, rm.rv_n[tris[ok].reshape(-1)])
    return me
