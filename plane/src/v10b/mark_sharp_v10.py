"""Last geometry step of v10b (in place on out/plane_v9_final_v10.blend): on every mesh with custom normals (the
reduced and repaired ones; untouched v9 meshes have none) mark sharp the edges across which the corner normals
jump, and set the same normals again. Shading data is unchanged (max deviation is printed); Blender's Cycles and any
importer that reads smoothing groups then agree with the stored normals."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_lib
PATH = '/home/claude/plane/out/plane_v9_final_v10.blend'
bpy.ops.wm.open_mainfile(filepath=PATH)
n = 0
worst = 0.0
for me in bpy.data.meshes:
    if me.users == 0 or not me.has_custom_normals:
        continue
    b, a, dev, how = sharp_lib.set_normals(me, sharp_lib._readback(me))
    worst = max(worst, dev)
    n += 1
    print(f'{me.name:28s} sharp edges {b:6d} -> {a:6d}  stored {how}  deviation {dev:.4f} deg', flush=True)
print('meshes', n, 'max normal change', round(worst, 4), 'deg')
bpy.ops.wm.save_as_mainfile(filepath=PATH, compress=True)
print('saved', PATH)
