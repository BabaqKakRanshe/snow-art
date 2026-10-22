import sys, numpy as np
sys.argv = ['urp_emulate.py', 'r/ext_front', 'v11', '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/dbg.png', '{"downsample":1, "beam":0, "glow":0, "bloom":0}']
src = open('urp_emulate.py').read()
# stop before the light loop runs: execute up to the definition of shade
cut = src.index("col = np.zeros((H, W, 3))")
exec(src[:cut])
for (x, y) in [(100, 480), (300, 450), (480, 400)]:
    print('pixel', x, y, 'hit', hit[y, x], 'P', np.round(Pw[y, x], 2), 'N', np.round(N[y, x], 2), 'albedo', np.round(alb[y, x], 3))
L = BY_KEY['Landing']
pos = parked_to_world(light_pos(L)); Rl = Rp @ L['R']
c = shade(pos, Rl, np.ones(3), L['intensity'], L['range'], 'spot', L['outer'], L['inner'], load_cookie('Landing'), False)
for (x, y) in [(100, 480), (300, 450), (480, 400)]:
    print('landing contribution at', x, y, np.round(c[y, x], 4))
print('--- all v11 lights at pixel (100,480) and (300,450)')
for L in LIGHTS:
    pos = parked_to_world(light_pos(L)); Rl = Rp @ L['R']
    if L['rotates']:
        ang = O['beacon_top'] if L['key'] == 'Beacon_Top' else O['beacon_bottom']; Rl = Rp @ Ry(ang) @ L['R']
    lin = np.asarray(L['filter']) * cct_rgb(L['cct'])
    c = shade(pos, Rl, lin, L['intensity'], L['range'], 'spot', L['outer'], L['inner'], load_cookie(L['key']), False)
    print('%-14s' % L['key'], np.round(c[480, 100], 4), np.round(c[450, 300], 4))
