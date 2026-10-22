"""Renders of the van like the plane previews.  python3 render_van.py <blend> <outdir> <views> [spp] [res]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import vb as B

blend, outdir, views = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 32
res = tuple(int(v) for v in sys.argv[5].split('x')) if len(sys.argv) > 5 else (900, 600)
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
if bpy.data.objects.get('Ground') is None:
    g = B.box('Ground', -60, 60, -60, 60, -0.2, 0.0, B.tex_box('snow', 'snow', 40, 0.9) if os.path.exists(
        os.path.join(B.TEX, 'snow.png')) else B.flat('g', (0.78, 0.79, 0.81), 0.9))
B.world()
B.sun(3.4, (52, 0, 30))
B.setup(res, spp)
CAMS = {
    'q34': ((6.4, 4.6, 1.75), (0.05, 0, 1.45), 32),
    'q34r': ((-6.2, -4.5, 2.0), (-0.1, 0, 1.45), 32),
    'side': ((0, 16, 1.55), (0, 0, 1.55), 30, 6.9),
    'front': ((14, 0, 1.6), (0, 0, 1.6), 30, 3.2),
    'rear': ((-14, 0, 1.6), (0, 0, 1.6), 30, 3.2),
    'close': ((4.2, 2.6, 1.45), (2.2, 0.2, 1.3), 30),
    'under': ((3.5, 3.8, 0.5), (0.2, 0, 0.75), 24),
}
for v in views:
    c = CAMS[v]
    B.camera(*c[:3], ortho=c[3] if len(c) > 3 else None)
    B.render(os.path.join(outdir, v + '.png'))
print('rendered', views)
