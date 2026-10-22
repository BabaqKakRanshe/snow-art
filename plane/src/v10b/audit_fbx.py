"""Audit UtilityPlane.fbx as Unity sees it: per mesh object tris, split verts (unique pos+normal+uv per corner),
materials used, bbox, parent; writes audit_fbx.json"""
import bpy, sys, json, collections
FBX = sys.argv[-2]
OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
dg = bpy.context.evaluated_depsgraph_get()
rows = []
for o in bpy.data.objects:
    r = dict(name=o.name, type=o.type, parent=o.parent.name if o.parent else None)
    if o.type == 'MESH':
        me = o.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        uvl = [l.data for l in me.uv_layers]
        cn = me.corner_normals if hasattr(me, 'corner_normals') else None
        keys = set()
        for li, loop in enumerate(me.loops):
            n = cn[li].vector if cn is not None else me.vertices[loop.vertex_index].normal
            k = (loop.vertex_index, round(n[0], 3), round(n[1], 3), round(n[2], 3)) + tuple(
                (round(u[li].uv[0], 5), round(u[li].uv[1], 5)) for u in uvl)
            keys.add(k)
        used = collections.Counter(p.material_index for p in me.polygons)
        mats = []
        for mi, cnt in sorted(used.items()):
            m = me.materials[mi] if mi < len(me.materials) else None
            mats.append([m.name if m else None, cnt])
        bb = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
        dims = [max(p[i] for p in bb) - min(p[i] for p in bb) for i in range(3)]
        r.update(tris=tris, verts=len(me.vertices), split_verts=len(keys), uv_layers=len(uvl), mats=mats,
                 dims=[round(d, 4) for d in dims], colors=len(me.color_attributes))
    rows.append(r)
json.dump(rows, open(OUT, 'w'), indent=0)
print('objects', len(rows), 'meshes', sum(1 for r in rows if r['type'] == 'MESH'))
