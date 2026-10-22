"""v10 LOD and shadow-proxy meshes with meshoptimizer (edge collapses onto existing vertices: every kept corner keeps
its exact position, UV and normal; UV seams, hard edges and material borders are seams kept watertight).
  lod_mesh(me, ratio, name)        -> new mesh, about `ratio` of the triangles, same material slots
  shadow_mesh(me, error_m, name)   -> new mesh for a ShadowsOnly renderer: positions only, welded, one material slot,
                                      geometric error <= error_m (absolute, object space); open edges may move
                                      within the same error (a shadow map texel near the camera is about 5-10 mm)"""
import ctypes
import bpy
import numpy as np
import meshoptimizer as mo
from meshoptimizer._loader import lib as _lib

_P = ctypes.POINTER
_lib.meshopt_simplifyWithAttributes.argtypes = [
    _P(ctypes.c_uint), _P(ctypes.c_uint), ctypes.c_size_t, _P(ctypes.c_float), ctypes.c_size_t, ctypes.c_size_t,
    _P(ctypes.c_float), ctypes.c_size_t, _P(ctypes.c_float), ctypes.c_size_t, _P(ctypes.c_ubyte), ctypes.c_size_t,
    ctypes.c_float, ctypes.c_uint, _P(ctypes.c_float)]
_lib.meshopt_simplifyWithAttributes.restype = ctypes.c_size_t
_lib.meshopt_simplify.argtypes = [
    _P(ctypes.c_uint), _P(ctypes.c_uint), ctypes.c_size_t, _P(ctypes.c_float), ctypes.c_size_t, ctypes.c_size_t,
    ctypes.c_size_t, ctypes.c_float, ctypes.c_uint, _P(ctypes.c_float)]
_lib.meshopt_simplify.restype = ctypes.c_size_t


def _arrays(me):
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
    uv = np.zeros(len(me.loops) * 2)
    if me.uv_layers:
        me.uv_layers[0].data.foreach_get('uv', uv)
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get('vector', cn)
    return li, mi, lv, co.reshape(-1, 3), uv.reshape(-1, 2), cn.reshape(-1, 3)


def _piece_labels(lv, li, T):
    """connected piece of every mesh vertex (connectivity through triangles)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    tv = lv[li].reshape(T, 3)
    nv = int(lv.max()) + 1
    r = np.concatenate([tv[:, 0], tv[:, 1], tv[:, 2]])
    c = np.concatenate([tv[:, 1], tv[:, 2], tv[:, 0]])
    _, lab = connected_components(coo_matrix((np.ones(len(r)), (r, c)), shape=(nv, nv)), directed=False)
    return lab


def lod_mesh(me, ratio, name, w_uv=1.0, w_n=0.05):
    li, mi, lv, co, uv, cn = _arrays(me)
    T = len(mi)
    lmat = np.repeat(mi, 3)
    key = np.concatenate([lv[li][:, None].astype(np.float64), lmat[:, None].astype(np.float64),
                          np.round(uv[li] * 1e6), np.round(cn[li] * 1e5)], axis=1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    rv_loop = li[first]
    rv_vert, rv_mat = lv[rv_loop], lmat[first]
    # v10b: meshoptimizer joins vertices by exact position, so separate pieces that touch would share wedges and a
    # collapse could hand one piece the normal / UV of the other. A per-piece offset of a few micrometres (only in the
    # copy given to meshoptimizer; output positions come from the mesh) keeps them apart.
    lab = _piece_labels(lv, li, T)
    jit = ((lab[rv_vert] % 61) + 1).astype(np.float64) * 2e-6
    pos = np.ascontiguousarray(co[rv_vert] + jit[:, None] * np.array([1.0, 0.7, 0.3]), np.float32)
    att = np.ascontiguousarray(np.concatenate([cn[rv_loop], uv[rv_loop]], axis=1), np.float32)
    wts = np.array([w_n, w_n, w_n, w_uv, w_uv], np.float32)
    idx = np.ascontiguousarray(inv, np.uint32)
    dst = np.zeros(len(idx), np.uint32)
    err = ctypes.c_float(0)
    target = max(3, int(len(idx) * ratio) // 3 * 3)
    n = _lib.meshopt_simplifyWithAttributes(
        dst.ctypes.data_as(_P(ctypes.c_uint)), idx.ctypes.data_as(_P(ctypes.c_uint)), len(idx),
        pos.ctypes.data_as(_P(ctypes.c_float)), len(pos), 12, att.ctypes.data_as(_P(ctypes.c_float)), 20,
        wts.ctypes.data_as(_P(ctypes.c_float)), 5, _P(ctypes.c_ubyte)(), target, ctypes.c_float(1.0),
        mo.SIMPLIFY_ERROR_ABSOLUTE, ctypes.byref(err))
    tris = dst[:n].astype(np.int64).reshape(-1, 3)
    mats = rv_mat[tris[:, 0]]
    return _build(name, tris, mats, rv_vert, co, uv[rv_loop], cn[rv_loop], list(me.materials)), err.value


def _build(name, tris, mats, rv_vert, co, rv_uv, rv_n, materials):
    # drop triangles that weld to repeated vertices (collapses along a seam can leave zero-area slivers whose corners
    # are different render vertices of one mesh vertex): Blender cannot hold them and they draw nothing
    w = rv_vert[tris]
    ok = (w[:, 0] != w[:, 1]) & (w[:, 1] != w[:, 2]) & (w[:, 0] != w[:, 2])
    tris, mats = tris[ok], mats[ok]
    verts_used, vmap = np.unique(rv_vert[tris.reshape(-1)], return_inverse=True)
    faces = vmap.reshape(-1, 3)
    pos = [tuple(p) for p in co[verts_used]]
    # a thin plate collapsed onto one triangle keeps both sides (back to back): the second face of such a pair gets
    # its own copies of the three vertices (Blender allows one face per vertex set)
    seen = set()
    for i, f in enumerate(faces):
        k = tuple(sorted(f))
        if k in seen:
            base = len(pos)
            pos += [pos[j] for j in f]
            faces[i] = [base, base + 1, base + 2]
        else:
            seen.add(k)
    nm = bpy.data.meshes.new(name)
    nm.from_pydata(pos, [], [tuple(int(i) for i in f) for f in faces])
    for m in materials:
        nm.materials.append(m)
    nm.polygons.foreach_set('material_index', mats.astype(np.int32))
    rv = tris.reshape(-1)
    if rv_uv is not None:
        uvl = nm.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', rv_uv[rv].astype(np.float32).reshape(-1))
    nm.polygons.foreach_set('use_smooth', np.ones(len(nm.polygons), bool))
    nm.update()
    # v10b: normals stored exactly (sharp edges where they jump; see sharp_lib.py)
    import sys as _s
    _s.path.insert(0, '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt')
    import sharp_lib
    sharp_lib.set_normals(nm, rv_n[rv])
    return nm


def shadow_mesh(me, error_m, name, lock_border=False):
    me.calc_loop_triangles()
    T = len(me.loop_triangles)
    vi = np.empty(T * 3, np.int32)
    me.loop_triangles.foreach_get('vertices', vi)
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    vn = np.empty(len(me.vertices) * 3)
    me.vertex_normals.foreach_get('vector', vn)
    vn = vn.reshape(-1, 3)
    pos = np.ascontiguousarray(co, np.float32)
    idx = np.ascontiguousarray(vi, np.uint32)
    dst = np.zeros(len(idx), np.uint32)
    err = ctypes.c_float(0)
    n = _lib.meshopt_simplify(dst.ctypes.data_as(_P(ctypes.c_uint)), idx.ctypes.data_as(_P(ctypes.c_uint)), len(idx),
                              pos.ctypes.data_as(_P(ctypes.c_float)), len(pos), 12, 3, ctypes.c_float(error_m),
                              mo.SIMPLIFY_ERROR_ABSOLUTE | (mo.SIMPLIFY_LOCK_BORDER if lock_border else 0),
                              ctypes.byref(err))
    tris = dst[:n].astype(np.int64).reshape(-1, 3)
    rv_vert = np.arange(len(co))
    return _build(name, tris, np.zeros(len(tris), np.int32), rv_vert, co, None, vn,
                  [me.materials[0]] if len(me.materials) else []), err.value
