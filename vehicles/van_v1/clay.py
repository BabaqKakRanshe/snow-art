"""Clay check of the body shape with placeholder wheels.  python3 clay.py <tag>"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import vb as B

tag = sys.argv[1] if len(sys.argv) > 1 else 'a'
B.reset()
d = np.load(os.path.join(B.HERE, 'work', 'body_outer.npz'))
body = B.mesh_np('Body', d['v'], d['f'], m=B.clay())
md = body.modifiers.new('sm', 'SMOOTH'); md.factor = 0.5; md.iterations = 4
B.apply_mods(body)
B.decimate(body, 0.16)
R, W, xF, xR, ty = 0.52, 0.36, 1.45, -1.25, 0.93
cut = []
for xa in (xF, xR):
    for s_ in (1, -1):
        cut.append(B.cyl('arch', (xa, s_ * 1.05, R), 'y', 0.64, 0.5, 48))
B.boolean(body, cut)
B.smooth(body, 35)
print('body faces', len(body.data.polygons))
for xa in (xF, xR):
    for s in (1, -1):
        t = B.cyl(f'w{xa}{s}', (xa, s * ty, R), 'y', R, W, 48, B.flat('tyre', (0.05, 0.05, 0.05), 0.9))
        B.bevel(t, 0.08, 3, 30)
        B.smooth(t, 40)
B.box('ground', -40, 40, -40, 40, -0.1, 0, B.flat('g', (0.75, 0.76, 0.78), 0.9))
B.world()
B.sun()
B.setup((900, 600), 24)
out = os.path.join(B.HERE, 'rend', 'clay_' + tag)
os.makedirs(out, exist_ok=True)
for name, cam in {'q34': ((7.2, 5.2, 2.0), (0.0, 0, 1.4), 32), 'side': ((0, 18, 1.6), (0, 0, 1.6), 30, 7.2),
                  'front': ((18, 0, 1.6), (0, 0, 1.6), 30, 3.4), 'rear34': ((-6.8, -4.8, 2.2), (0, 0, 1.4), 32)}.items():
    B.camera(*cam[:3], ortho=cam[3] if len(cam) > 3 else None)
    B.render(os.path.join(out, name + '.png'))
print('done')
