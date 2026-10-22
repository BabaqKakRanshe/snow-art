"""Repair shading after face deletion (in place on out/plane_v9_final_v10.blend):
A. parts whose hidden faces were deleted (vis_v10_report.json): Blender stores custom normals relative to the smooth
   fan of each corner, so deleting neighbouring faces changes what they decode to (and meshes without custom normals
   re-average their smooth normals). Every remaining corner gets back the normal it had before the deletion (matched
   by face position + material in out/plane_v9_final_v10_meshopt.blend), as an explicit custom normal.
B. a thin plate the reduction collapsed onto one triangle keeps both sides: the second face of such a back-to-back
   pair gets its own copies of its vertices (Blender holds one face per vertex set); every corner keeps its normal.
   Zero-area triangles stay (v9 meshes have them too; they draw nothing)."""
import bpy, bmesh, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_lib
import numpy as np

AFTER = '/home/claude/plane/out/plane_v9_final_v10.blend'
BEFORE = '/home/claude/plane/out/plane_v9_final_v10_meshopt.blend'
OPT = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt'
vis = json.load(open(OPT + '/' + __import__('os').environ.get('VISREP', 'vis_v10b_report.json')))['removed']
R = 6


def corner_table(me):
    """{(material, sorted positions) -> {position: normal}} for every polygon"""
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).round(R)
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get('vector', cn)
    cn = cn.reshape(-1, 3)
    tab = {}
    for p in me.polygons:
        pos = [tuple(co[me.loops[l].vertex_index]) for l in p.loop_indices]
        key = (p.material_index, tuple(sorted(pos)))
        tab[key] = {pp: tuple(cn[l]) for pp, l in zip(pos, p.loop_indices)}
    return tab


bpy.ops.wm.open_mainfile(filepath=BEFORE)
tables = {n: corner_table(bpy.data.objects[n].data) for n in vis}
bpy.ops.wm.open_mainfile(filepath=AFTER)

# ---------------------------------------------------------------- A
for n in vis:
    me = bpy.data.objects[n].data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).round(R)
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get('vector', cn)
    cn = cn.reshape(-1, 3)
    out = cn.copy()
    miss = 0
    for p in me.polygons:
        pos = [tuple(co[me.loops[l].vertex_index]) for l in p.loop_indices]
        t = tables[n].get((p.material_index, tuple(sorted(pos))))
        if t is None:
            miss += 1
            continue
        for pp, l in zip(pos, p.loop_indices):
            out[l] = t[pp]
    b_, a_, dev, how = sharp_lib.set_normals(me, out)
    print(f'A {n:22s} polygons {len(me.polygons)} unmatched {miss} stored {how} dev {dev:.3f}', flush=True)


# ---------------------------------------------------------------- B
def duplicates(me):
    """the second face of every pair that uses the same vertex set (a thin plate collapsed onto one triangle)"""
    dup, seen = [], set()
    for p in me.polygons:
        k = tuple(sorted(p.vertices))
        if len(set(k)) < len(k):
            continue
        if k in seen:
            dup.append(p.index)
        else:
            seen.add(k)
    return dup


for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.data
    dup = duplicates(me)
    if not dup:
        continue
    cn = np.empty(len(me.loops) * 3)
    me.corner_normals.foreach_get('vector', cn)
    cn = cn.reshape(-1, 3)
    for fi in dup:                                     # back-to-back twin: own copies of its vertices
        p = me.polygons[fi]
        lids = list(p.loop_indices)
        base = len(me.vertices)
        me.vertices.add(len(lids))
        for k, l in enumerate(lids):
            me.vertices[base + k].co = me.vertices[me.loops[l].vertex_index].co.copy()
            me.loops[l].vertex_index = base + k
    me.update(calc_edges=True)
    b_, a_, dev, how = sharp_lib.set_normals(me, cn)
    chk = me.copy()
    changed = chk.validate(verbose=False, clean_customdata=False)
    bpy.data.meshes.remove(chk)
    print(f'B {o.name:22s} back-to-back faces split {len(dup)}; still invalid: {changed}', flush=True)

bpy.ops.wm.save_as_mainfile(filepath=AFTER, compress=True)
print('saved', AFTER)
