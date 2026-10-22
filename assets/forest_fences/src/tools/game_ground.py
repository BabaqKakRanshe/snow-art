"""The ground as the game has it: Unity Terrain tile 1_1 of Forest (x 0..600, z -600..0) read from the project's
Forest_TerrainData_1_1.asset (22.10, after the bake and the integration's levelling at the yard and the moved checkpoint):
heights 1025 x 1025, origin Y -84, size Y 136, value / 32766. read_td.py made game_terrain_1_1.npy ([z, x], metres).
ground(x, z): bilinear, as TerrainData.GetInterpolatedHeight."""
import os
import numpy as np

H = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_terrain_1_1.npy'))
X0, Z0, T = 0.0, -600.0, 600.0
STEP = T / (H.shape[0] - 1)


def ground(x, z):
    u, v = (x - X0) / STEP, (z - Z0) / STEP
    i0, j0 = int(np.floor(u)), int(np.floor(v))
    if not (0 <= i0 < H.shape[1] - 1 and 0 <= j0 < H.shape[0] - 1):
        raise ValueError('outside tile 1_1: %.1f %.1f' % (x, z))
    fu, fv = u - i0, v - j0
    return float((H[j0, i0] * (1 - fu) + H[j0, i0 + 1] * fu) * (1 - fv) + (H[j0 + 1, i0] * (1 - fu) + H[j0 + 1, i0 + 1] * fu) * fv)
