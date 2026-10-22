import json, math, sys
import numpy as np
from scipy import ndimage
from collections import deque
G = np.load('drive_grid.npz')
N0, CELL = -600, 1.0
n = G['H'].shape[0]
def idx(x, z): return int((x - N0) / CELL), int((z - N0) / CELL)
def pos(i, j): return N0 + (i + 0.5) * CELL, N0 + (j + 0.5) * CELL
base_block = G['slope'] | G['water'] | G['trees'] | G['bones'] | G['fence'] | G['edge']
K = json.load(open('kpp_reloc.json'))
new = np.array([K['new'][0], K['new'][2]]); nt = np.array([K['new_tan'][0], K['new_tan'][2]]); perp = np.array([-nt[1], nt[0]])
def line_mask(polys, width=2.6):
    m = np.zeros((n, n), bool)
    for poly in polys:
        for a, b in zip(poly[:-1], poly[1:]):
            a, b = np.array(a, float), np.array(b, float)
            L = np.linalg.norm(b - a)
            for t in np.linspace(0, 1, int(L / 0.25) + 2):
                p = a + (b - a) * t
                i, j = idx(*p)
                if 0 <= i < n and 0 <= j < n: m[i, j] = True
    r = int(width / 2 / CELL)
    return ndimage.binary_dilation(m, iterations=max(1, r))
def bfs(block, seed):
    seen = np.zeros((n, n), bool); par = {}
    s = idx(*seed); q = deque([s]); seen[s] = True
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < n and not seen[a, b] and not block[a, b]:
                seen[a, b] = True; par[(a, b)] = (i, j); q.append((a, b))
    return seen, par
def path(par, seed, goal):
    s = idx(*seed); g = idx(*goal); out = [g]
    while out[-1] != s and out[-1] in par: out.append(par[out[-1]])
    return [pos(*c) for c in out[::-1]]
seed = new - nt * 60                      # the road NW of the checkpoint (outside)
inside_road = new + nt * 30               # the road SE of the checkpoint (inside)
gate = np.array([302.0, -279.0])          # in front of the base gate (outside the base fence)
if __name__ == '__main__':
    lines = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
    block = base_block | (line_mask(lines) if lines else False)
    seen, par = bfs(block, seed)
    for name, p in (('road SE of KPP', inside_road), ('base gate', gate)):
        i, j = idx(*p)
        print(name, 'reachable' if seen[i, j] else 'NOT reachable', 'blocked cell' if block[i, j] else '')
        if seen[i, j]:
            pth = path(par, seed, p)
            print('  path length %d m, via:' % len(pth), [tuple(round(c) for c in pth[k]) for k in range(0, len(pth), max(1, len(pth) // 12))])
    print('reachable share %.1f%%' % (100 * seen.mean()))
    np.save('seen.npy', seen)
