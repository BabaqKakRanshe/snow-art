"""airfield plan: ortho top view in the runway frame (image up = +v north, right = +u east), all trees, no fog, 100 m ticks
python3.11 -I plan_af2.py <blend> <out.png> [spp]"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ground_after as GA

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
sc = bpy.context.scene
sc['fog_k'] = 0.0
for o in (bpy.data.collections['Trees'].objects if 'Trees' in bpy.data.collections else []):
    o.hide_render = False
U0, U1, V0, V1 = -165.0, 165.0, -650.0, 570.0
uc, vc = (U0 + U1) / 2, (V0 + V1) / 2
x, z = GA.to_xz(uc, vc)
x1, z1 = GA.to_xz(uc + 1, vc)
ry = math.atan2(-(float(z1) - float(z)), -(float(x1) - float(x)))     # Blender angle of +u
cd = bpy.data.cameras.new('Plan'); cd.type = 'ORTHO'; cd.ortho_scale = V1 - V0; cd.sensor_fit = 'VERTICAL'; cd.clip_end = 3000
co = bpy.data.objects.new('Plan', cd); sc.collection.objects.link(co)
co.location = Vector((-float(x), -float(z), 400.0)); co.rotation_euler = (0, 0, ry)
sc.camera = co
PX = 2.0
sc.render.resolution_y = int((V1 - V0) * PX); sc.render.resolution_x = int((U1 - U0) * PX)
sc.render.resolution_percentage = 100
sc.cycles.samples = int(argv[2]) if len(argv) > 2 else 6
sc.cycles.use_denoising = True
sc.render.filepath = argv[1]
bpy.ops.render.render(write_still=True)
print('plan', argv[1])
