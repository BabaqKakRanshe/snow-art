"""The Forester's cave as a distance field -> marching cubes (system python3: numpy, scipy, scikit-image).
The rock mass: granite 'woolsack' blocks (superellipsoids with low-frequency noise, smooth union) like forest_rocks'
cliffs, a broad base, an upper block, side blocks; the cavity: a low entrance passage (1.7 m wide, 1.9 m high) that turns a
little to the left into a chamber (5 x 4 m, 2.3 m high) with a sleeping niche on the left; the floor flat at z = 0 (the
origin: the floor in the mouth, the front -y). The mass goes 0.6 m into the ground.
python3 world_cave_sdf.py out.npz -> verts (n, 3), faces (m, 3), cavity grid (for the zones and the props)"""
import sys, math
import numpy as np
from scipy import ndimage
from skimage import measure

VOX = 0.10
LO, HI = np.array([-6.8, -2.6, -0.8]), np.array([6.8, 9.8, 6.2])
# rock blocks: centre, half sizes, exponent, yaw (deg), noise seed
BLOCKS = [((0.0, 3.2, 1.2), (5.6, 4.8, 2.1), 4.0, 4.0, 1),
          ((-1.2, 3.8, 3.3), (4.0, 3.4, 1.6), 4.0, -9.0, 2),
          ((2.9, 2.0, 2.4), (2.4, 2.6, 1.7), 3.6, 18.0, 3),
          ((-4.1, 1.6, 1.5), (2.1, 2.4, 1.9), 3.4, -22.0, 4),
          ((0.6, 5.9, 2.7), (3.6, 2.4, 1.8), 3.8, 12.0, 5),
          ((1.9, 0.4, 0.9), (1.3, 1.1, 1.2), 2.6, 30.0, 6),
          ((-2.2, -0.1, 1.0), (1.4, 1.2, 1.25), 2.6, -35.0, 7)]
# cavity ellipsoids: centre, radii
CAVES = [((0.0, -1.0, 0.75), (0.86, 2.6, 1.15)),          # the passage, from outside into the hill
         ((0.15, 1.6, 0.80), (0.95, 1.6, 1.15)),
         ((0.35, 3.7, 1.00), (2.55, 2.05, 1.32)),          # the chamber
         ((-1.85, 4.35, 0.62), (1.35, 1.15, 0.90)),        # the sleeping niche (left, deeper)
         ((1.55, 4.75, 0.70), (1.10, 0.95, 0.95))]         # a recess on the right (the stash)


def hash3(i, j, k, seed):
    h = np.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453
    return h - np.floor(h)


def vnoise(P, freq, seed):
    p = P * freq
    i = np.floor(p)
    f = p - i
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm(P, freq, octaves, seed):
    s, a, n = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * vnoise(P, freq * 2 ** o, seed + o * 7)
        n += a
        a *= 0.5
    return s / n


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def block_sdf(P, c, half, p, yaw, seed):
    q = P - np.array(c)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    x = q[..., 0] * ca + q[..., 1] * sa
    y = -q[..., 0] * sa + q[..., 1] * ca
    z = q[..., 2]
    a, b, cc = half
    r = (np.abs(x / a) ** p + np.abs(y / b) ** p + np.abs(z / cc) ** p) ** (1.0 / p)
    d = (r - 1.0) * min(half)
    d = d + 0.45 * (fbm(P, 0.45, 3, seed) - 0.5) + 0.10 * (fbm(P, 2.2, 2, seed + 50) - 0.5)
    rng = np.random.default_rng(seed)                                   # fracture facets: planar cuts (half-spaces)
    for _ in range(5):
        th = rng.uniform(0, 2 * math.pi)
        nz_ = rng.uniform(-0.15, 0.85)
        rr = math.sqrt(1 - nz_ * nz_)
        n_ = np.array([rr * math.cos(th), rr * math.sin(th), nz_])
        ext = abs(n_[0]) * a + abs(n_[1]) * b + abs(n_[2]) * cc            # the box's support along n
        off = ext * rng.uniform(0.72, 0.86)
        pl = (x * n_[0] + y * n_[1] + z * n_[2]) - off
        d = np.maximum(d, pl)
    return d


def main(out):
    nx, ny, nz = np.round((HI - LO) / VOX).astype(int) + 1
    xs, ys, zs = (np.linspace(LO[i], LO[i] + (n - 1) * VOX, n) for i, n in enumerate((nx, ny, nz)))
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X, Y, Z], -1)
    mass = None
    for c, half, p, yaw, seed in BLOCKS:
        d = block_sdf(P, c, half, p, yaw, seed)
        mass = d if mass is None else smin(mass, d, 0.30)
    mass = np.maximum(mass, -(Z + 0.6))                                 # flat foot 0.6 m under the ground
    cav = None
    for c, r in CAVES:
        q = (P - np.array(c)) / np.array(r)
        d = (np.linalg.norm(q, axis=-1) - 1.0) * min(r)
        cav = d if cav is None else smin(cav, d, 0.45)
    cav = cav + 0.16 * (fbm(P, 1.6, 2, 90) - 0.5) + 0.07 * (fbm(P, 5.0, 2, 95) - 0.5)
    cav = np.maximum(cav, -Z)                                           # the floor: flat at z = 0
    rock = np.maximum(mass, -cav)
    rock = ndimage.gaussian_filter(rock, 0.45)
    v, f, n, _ = measure.marching_cubes(rock, level=0.0, spacing=(VOX, VOX, VOX))
    v = v + LO
    np.savez_compressed(out, verts=v.astype(np.float32), faces=f.astype(np.int32), cav=cav.astype(np.float32),
                        lo=LO, vox=VOX, shape=np.array(cav.shape))
    print('verts', len(v), 'faces', len(f), 'bbox', v.min(0).round(2), v.max(0).round(2))


if __name__ == '__main__':
    main(sys.argv[1])
