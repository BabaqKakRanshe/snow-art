import sys, numpy as np
sys.argv = ['urp_emulate.py', 'r/ext_rear', 'v11', '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/dbg.png', '{}']
src = open('urp_emulate.py').read()
cut = src.index("col = np.zeros((H, W, 3))")
exec(src[:cut])
for key in ('Landing', 'Nav_L', 'Beacon_Top', 'Nav_Tail'):
    L = BY_KEY[key]
    c = parked_to_world(light_pos(L))
    v = c - ro
    dist = np.linalg.norm(v)
    # project into the camera
    Rc = Mb @ S['cam_rot_b']                       # camera axes (columns) in Unity world: x right, y up, -z forward
    lc = v @ Rc
    x = lc[0] / -lc[2] / tanh / (W / H); y = lc[1] / -lc[2] / tanh
    px_ = (x + 1) / 2 * W; py_ = (1 - y) / 2 * H
    i, j = int(np.clip(px_, 0, W - 1)), int(np.clip(py_, 0, H - 1))
    print('%-11s pixel (%d, %d)  dist %.2f  scene T there %.2f  hit %s  -> occluded by %.2f m' % (key, i, j, dist, tfar[j, i], hit[j, i], dist - tfar[j, i]))
