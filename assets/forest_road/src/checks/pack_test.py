"""how the concave packer + shelf repack does on each road group (no bake): time, fill, chosen atlas size"""
import sys, time, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import road_tex as RT
import gen_kit as K
import road_kit as RK
import bld_common as BC
import psxlib as P
import uvpack
_IJ = BC.is_joined
BC.is_joined = lambda a: _IJ(a) or a in ('chainlink', 'barbed')
RK.build_road()
BC.prepare_kbs(set())
objs = BC.make_objects(lambda *a: None)
groups = {}
for n, o in objs.items():
    a = K.ATLAS[n]
    if not BC.is_joined(a):
        groups.setdefault(a, []).append(o)
for g in sys.argv[sys.argv.index('--') + 1:]:
    os_ = groups[g]
    t0 = time.time()
    A = P.area3d(os_)
    size = 256
    while size < 2048 and size * math.sqrt(0.70 / A) < 0.9 * 51.3:
        size *= 2
    P.unwrap_group(os_, margin=2.2 / size, angle=50)
    f1 = P.uv_fill(os_)
    t1 = time.time()
    f2 = uvpack.repack(os_, size, 2.2)
    t2 = time.time()
    f = max(f1, f2)
    if size < 2048 and size * math.sqrt(f / A) < 0.9 * 51.3:
        size2 = size * 2
    else:
        size2 = size
    print(g, 'A', round(A, 1), 'size0', size, 'concave fill', round(f1, 3), f'{t1 - t0:.1f}s', 'shelf fill', round(f2, 3),
          f'{t2 - t1:.1f}s', '-> size', size2, flush=True)
