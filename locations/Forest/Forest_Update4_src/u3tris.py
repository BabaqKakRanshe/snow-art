import bpy, json, os, sys
M = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Models/'
R = json.load(open('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u4/fbx/u4_export_report.json'))
out = {}
for n in sorted(R):
    fp = M + n + '.fbx'
    if not os.path.exists(fp):
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fp)
    out[n] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
print('U3TRIS', json.dumps(out))
