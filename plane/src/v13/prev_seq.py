"""Door motion frames for a GIF: python3 prev_seq.py <blend> <outdir> <view> <frames> <w> <h> <samples>
Uses prev_src.py's scene setup and door pose (imported by exec with a guard)."""
import sys, os, math
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
blend, outdir, view, nfr, W, H, spp = args[0], args[1], args[2], int(args[3]), int(args[4]), int(args[5]), int(args[6])
# reuse the scene setup of prev_src.py without rendering its views
sys.argv = [sys.argv[0], blend, outdir, '']
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prev_src.py')).read()
src = src.split('for name in want:')[0]
exec(compile(src, 'prev_src.py', 'exec'))
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.cycles.samples = spp
eye, at, lens = VIEWS[view]
look(eye, at, lens)
ts = [k / (nfr - 1) for k in range(nfr)]          # the GIF holds the first and the last frame longer
for i, t in enumerate(ts):
    pose_doors(t)
    sc.render.filepath = os.path.join(outdir, f'{view}_{i:03d}.png')
    bpy.ops.render.render(write_still=True)
print('done', len(ts))
