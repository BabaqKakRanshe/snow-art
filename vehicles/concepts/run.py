"""python3 run.py <concept module> [views] [samples] -> rend/<module>/{view}.png, _depth, _psx"""
import sys, os, importlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import vlib as V
import scene as S
import post

mod = sys.argv[1]
views = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] != 'all' else ['day', 'night', 'inside', 'side']
spp = int(sys.argv[3]) if len(sys.argv) > 3 else 48
t0 = time.time()
V.reset()
S.build_ground()
C = importlib.import_module(mod)
cones = [(c[0], c[1]) for k, c in C.CAMS.items() if k in ('day', 'night')]
S.build_trees(keep_clear=[(c[0][0], c[0][1], 5) for c in cones], cones=cones)
veh = C.build()
print('built', mod, f'{time.time() - t0:.1f}s', len(bpy.data.objects), 'objects')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rend', mod)
S.run_views(veh, out, views, spp)
for v in views:
    post.process(out, v)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, mod + '.blend'))
print('done', mod, f'{time.time() - t0:.1f}s')
