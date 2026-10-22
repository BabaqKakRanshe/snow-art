"""meshoptimizer-based error-bounded reduction (v10). Edge collapses only onto existing vertices, so every kept
corner keeps its exact source position, UV and normal; UV seams and hard edges (split render vertices) are kept by
meshoptimizer's seam handling; material borders and open borders are locked (each material is simplified on its own
with SIMPLIFY_LOCK_BORDER). The result is checked with opt_lib.measure (geometry / UV texels / shading) and the
target error is binary-searched per object."""
import bpy
import numpy as np
import ctypes
import meshoptimizer as mo
from meshoptimizer._loader import lib as _lib
import opt_lib as L

_P = ctypes.POINTER
_lib.meshopt_simplifyWithAttributes.argtypes = [
    _P(ctypes.c_uint), _P(ctypes.c_uint), ctypes.c_size_t, _P(ctypes.c_float), ctypes.c_size_t, ctypes.c_size_t,
    _P(ctypes.c_float), ctypes.c_size_t, _P(ctypes.c_float), ctypes.c_size_t, _P(ctypes.c_ubyte), ctypes.c_size_t,
    ctypes.c_float, ctypes.c_uint, _P(ctypes.c_float)]
_lib.meshopt_simplifyWithAttributes.restype = ctypes.c_size_t


def _simplify_attr(idx, pos, att, wts, target_error, options, lock=None):
    dst = np.zeros(len(idx), np.uint32)
    err = ctypes.c_float(0.0)
    n = _lib.meshopt_simplifyWithAttributes(
        dst.ctypes.data_as(_P(ctypes.c_uint)), idx.ctypes.data_as(_P(ctypes.c_uint)), len(idx),
        pos.ctypes.data_as(_P(ctypes.c_float)), len(pos), pos.shape[1] * 4,
        att.ctypes.data_as(_P(ctypes.c_float)), att.shape[1] * 4, wts.ctypes.data_as(_P(ctypes.c_float)), len(wts),
        lock.ctypes.data_as(_P(ctypes.c_ubyte)) if lock is not None else _P(ctypes.c_ubyte)(),
        3, ctypes.c_float(target_error), options, ctypes.byref(err))
    return dst[:n], err.value


class RenderMesh:
    def __init__(self, me):
        me.calc_loop_triangles()
        lt = me.loop_triangles
        T = len(lt)
        li = np.empty(T * 3, np.int32)
        lt.foreach_get('loops', li)
        mi = np.empty(T, np.int32)
        lt.foreach_get('material_index', mi)
        lv = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', lv)
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        uv = np.zeros(len(me.loops) * 2)
        if me.uv_layers:
            me.uv_layers[0].data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2)
        cn = np.empty(len(me.loops) * 3)
        me.corner_normals.foreach_get('vector', cn)
        cn = cn.reshape(-1, 3)
        # render vertex = unique (mesh vertex, uv, normal) over the corners used by triangles
        used = np.unique(li)
        key = np.concatenate([lv[used][:, None].astype(np.float64), np.round(uv[used] * 1e6), np.round(cn[used] * 1e5)],
                             axis=1)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        inv = inv.reshape(-1)
        loop2rv = np.full(len(me.loops), -1, np.int64)
        loop2rv[used] = inv
        src_loop = used[first]
        self.rv_vert = lv[src_loop]                     # mesh vertex of each render vertex
        self.rv_pos = co[self.rv_vert]
        self.rv_uv = uv[src_loop]
        self.rv_n = cn[src_loop]
        self.tris = loop2rv[li].reshape(T, 3)
        self.mat = mi
        self.co = co


def simplify(rm, target_error, w_uv, w_n, lock_border=True):
    """Returns (tris (K,3) render-vertex ids, mats (K,))."""
    out_t, out_m = [], []
    for m in np.unique(rm.mat):
        tri = rm.tris[rm.mat == m]
        vids, local = np.unique(tri.reshape(-1), return_inverse=True)
        idx = local.astype(np.uint32)
        pos = np.ascontiguousarray(rm.rv_pos[vids], np.float32)
        att = np.ascontiguousarray(np.concatenate([rm.rv_n[vids], rm.rv_uv[vids]], axis=1), np.float32)
        wu = w_uv.get(int(m), max(w_uv.values())) if isinstance(w_uv, dict) else w_uv
        wts = np.array([w_n, w_n, w_n, wu, wu], np.float32)
        opts = mo.SIMPLIFY_ERROR_ABSOLUTE | (mo.SIMPLIFY_LOCK_BORDER if lock_border else 0)
        out, _ = _simplify_attr(np.ascontiguousarray(idx), pos, att, wts, float(target_error), opts)
        t2 = vids[out.astype(np.int64)].reshape(-1, 3)
        out_t.append(t2)
        out_m.append(np.full(len(t2), m, np.int32))
    return np.concatenate(out_t), np.concatenate(out_m)


def build_mesh(name, rm, tris, mats, materials):
    """Blender mesh from simplified render triangles (positions welded by source vertex; per-corner UV + normal)."""
    verts_used, vmap = np.unique(rm.rv_vert[tris.reshape(-1)], return_inverse=True)
    faces = vmap.reshape(-1, 3)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in rm.co[verts_used]], [], [tuple(int(i) for i in f) for f in faces])
    for m in materials:
        me.materials.append(m)
    # from_pydata keeps face order; corners follow the triangle vertex order
    me.polygons.foreach_set('material_index', mats.astype(np.int32))
    uvl = me.uv_layers.new(name='UVMap')
    rv = tris.reshape(-1)
    uvl.data.foreach_set('uv', rm.rv_uv[rv].astype(np.float32).reshape(-1))
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    me.update()
    # loops are created in face-corner order = rv order
    me.normals_split_custom_set([tuple(x) for x in rm.rv_n[rv]])
    me.update()
    return me


def reduce_object(ob, tol_m, tex_res, uv_tol=0.5, n_tol=5.0, iters=7, log=print, w_uv=None, w_n=None):
    me0 = ob.data
    src = L.TriData(me0)
    rm = RenderMesh(me0)
    if w_uv is None:
        w_uv = {k: tol_m * v for k, v in tex_res.items()} if isinstance(tex_res, dict) else tol_m * tex_res
    w_n = tol_m * 12.0 if w_n is None else w_n
    best = None
    a, b = 0.0, 3.0 * tol_m                       # meshoptimizer error (absolute, m) search range
    for k in range(iters):
        e = (a + b) / 2
        tris, mats = simplify(rm, e, w_uv, w_n)
        me = build_mesh(ob.name + '_opt', rm, tris, mats, list(me0.materials))
        dst = L.TriData(me)
        m = L.measure(src, dst, tex_res, tol_m)
        ok = L.passes(m, tol_m, uv_tol, n_tol)
        log(f'    {ob.name} e={e*1000:.3f}mm tris {dst.T}/{src.T} geo {m["geo_p999"]*1000:.2f}/{m["geo_max"]*1000:.2f} mm '
            f'uv {m["uv_p99"]:.2f}/{m["uv_max"]:.2f} tx  n {m["n_p99"]:.1f}/{m["n_mean"]:.2f} deg fb {m["fallback"]:.3f} '
            f'{"OK" if ok else "--"}')
        if ok:
            if best is not None:
                bpy.data.meshes.remove(best[0])
            best = (me, e, m, dst.T)
            a = e
        else:
            bpy.data.meshes.remove(me)
            b = e
    if best is None:
        return None, 0.0, None, src.T, src.T
    return best[0], best[1], best[2], src.T, best[3]
