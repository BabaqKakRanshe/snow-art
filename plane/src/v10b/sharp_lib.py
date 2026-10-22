"""v10b normal storage helpers.
set_normals(me, cn): store per-corner normals cn exactly as given. Edges across which the corner normals jump are
marked sharp first (meshes rebuilt by from_pydata have none, so one smooth fan could span corners whose stored normals
differ by 90 deg: Blender read them back right, but Cycles shaded such fans wrongly). Then the normals are stored as
Blender custom normals (encoded per smooth fan) - set twice, since the first set can still split fans - and read back;
if any corner is off by more than 0.5 deg (the encoding breaks down on fans of hair-thin triangles), the mesh keeps
them as free normals (a float vector per corner, exact; Blender 4.4+).
mark_sharp_discontinuities(me): the same for the normals a mesh already has."""
import numpy as np


def _readback(me):
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get('vector', cn)
    return cn.reshape(-1, 3)


def _angles(a, b):
    na = np.linalg.norm(a, axis=1); nb = np.linalg.norm(b, axis=1)
    return np.degrees(np.arccos(np.clip((a * b).sum(1) / np.maximum(na * nb, 1e-20), -1, 1)))


def _mark(me, cn, tol_deg=1.0):
    n_loops = len(me.loops)
    lv = np.empty(n_loops, np.int32); me.loops.foreach_get('vertex_index', lv)
    le = np.empty(n_loops, np.int32); me.loops.foreach_get('edge_index', le)
    ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
    lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', lt)
    nxt = np.arange(n_loops) + 1
    nxt[ls + lt - 1] = ls
    cos_t = np.cos(np.radians(tol_deg))
    # corner of each face at each end of each of its edges: (edge, vertex) -> corners
    keys_e = np.concatenate([le, le])
    keys_v = np.concatenate([lv, lv[nxt]])
    corners = np.concatenate([np.arange(n_loops), nxt])
    order = np.lexsort((keys_v, keys_e))
    ke, kv, kc = keys_e[order], keys_v[order], corners[order]
    sharp = np.zeros(len(me.edges), bool)
    if 'sharp_edge' in me.attributes:
        me.attributes['sharp_edge'].data.foreach_get('value', sharp)
    before = int(sharp.sum())
    start = 0
    n = len(ke)
    cnn = cn / np.maximum(np.linalg.norm(cn, axis=1), 1e-20)[:, None]
    # group boundaries
    brk = np.flatnonzero((ke[1:] != ke[:-1]) | (kv[1:] != kv[:-1])) + 1
    bounds = np.concatenate([[0], brk, [n]])
    first = kc[bounds[:-1]]
    grp = np.repeat(np.arange(len(bounds) - 1), np.diff(bounds))
    dots = (cnn[kc] * cnn[first[grp]]).sum(1)
    badg = np.zeros(len(bounds) - 1, bool)
    np.logical_or.at(badg, grp, dots < cos_t)
    sharp[ke[bounds[:-1]][badg]] = True
    if 'sharp_edge' not in me.attributes:
        me.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
    me.attributes['sharp_edge'].data.foreach_set('value', sharp)
    return before, int(sharp.sum())


def set_free(me, cn):
    if 'custom_normal' in me.attributes:
        me.attributes.remove(me.attributes['custom_normal'])
    a = me.attributes.new('custom_normal', 'FLOAT_VECTOR', 'CORNER')
    a.data.foreach_set('vector', np.asarray(cn, np.float32).reshape(-1))
    me.update()


def set_normals(me, cn, tol_deg=0.5):
    """returns (sharp before, sharp after, worst deviation deg, storage 'encoded' | 'free')"""
    cn = np.asarray(cn, np.float64)
    b, a = _mark(me, cn)
    lst = [tuple(x) for x in cn]
    me.normals_split_custom_set(lst)
    me.update()
    me.normals_split_custom_set(lst)
    me.update()
    dev = float(_angles(_readback(me), cn).max()) if len(cn) else 0.0
    if dev <= tol_deg:
        return b, a, dev, 'encoded'
    set_free(me, cn)
    dev2 = float(_angles(_readback(me), cn).max())
    return b, a, dev2, 'free'


def mark_sharp_discontinuities(me, tol_deg=1.0):
    """kept for the callers of the first version: same as set_normals(me, current normals)"""
    b, a, dev, how = set_normals(me, _readback(me))
    return b, a, dev
