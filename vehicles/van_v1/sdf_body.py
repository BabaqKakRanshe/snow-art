"""Outer body surface of the van concept: intersection of three extruded 2D profiles (side, plan, section)
as a signed distance field with smooth blends, then marching cubes.  python3 sdf_body.py -> work/body_outer.npz
Frame: x forward, y left, z up, metres.  Original design of the 'loaf' van type (not a replica of any vehicle)."""
import math, os, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ profiles (edit here)
P = dict(
    zb=0.92,                       # body bottom
    zt=2.95,                       # roof at the side profile
    xf=2.45, xr=-2.45,             # front face / rear face
    rake=12.0,                     # windshield rake from vertical, deg
    zws=1.72,                      # windshield base on the front face
    hw_belt=1.08, hw_bot=0.99, hw_roof=0.95, crown=0.05, zbelt=1.56,
    r_front_plan=0.46, r_rear_plan=0.24, r_roof_front=0.55, r_roof_rear=0.44, r_roof_side=0.44,
)


def fillet_poly(pts, radii, seg=12):
    """polygon (CCW) with a tangent arc of the given radius at each vertex"""
    out = []
    n = len(pts)
    Q = [np.array(p, float) for p in pts]
    for i in range(n):
        r = radii[i]
        p0, p1, p2 = Q[i - 1], Q[i], Q[(i + 1) % n]
        if r <= 0:
            out.append(tuple(p1))
            continue
        d1 = (p0 - p1) / np.linalg.norm(p0 - p1)
        d2 = (p2 - p1) / np.linalg.norm(p2 - p1)
        ang = math.acos(float(np.clip(np.dot(d1, d2), -1, 1)))
        t = r / math.tan(ang / 2)
        a, b = p1 + d1 * t, p1 + d2 * t
        bis = (d1 + d2) / np.linalg.norm(d1 + d2)
        c = p1 + bis * (r / math.sin(ang / 2))
        a0, a1 = math.atan2(a[1] - c[1], a[0] - c[0]), math.atan2(b[1] - c[1], b[0] - c[0])
        da = a1 - a0
        while da > math.pi:
            da -= 2 * math.pi
        while da < -math.pi:
            da += 2 * math.pi
        for k in range(seg + 1):
            aa = a0 + da * k / seg
            out.append((c[0] + r * math.cos(aa), c[1] + r * math.sin(aa)))
    return out


def sdf2d(poly, u0, u1, v0, v1, res=0.004):
    W, H = int((u1 - u0) / res) + 1, int((v1 - v0) / res) + 1
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).polygon([((u - u0) / res, (v - v0) / res) for u, v in poly], fill=255)
    m = np.asarray(im) > 127
    s = np.where(m, -ndimage.distance_transform_edt(m), ndimage.distance_transform_edt(~m)) * res
    s = ndimage.gaussian_filter(s, 2.0)            # remove raster stair-steps (they show up as ripples)
    return s, (u0, v0, res)


def sample(sm, U, V):
    s, (u0, v0, res) = sm
    return ndimage.map_coordinates(s, [(V - v0) / res, (U - u0) / res], order=1, mode='nearest')


def smax(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.maximum(a, b) + h * h * k * 0.25


def profiles(p=P):
    xw = p['xf'] - (p['zt'] - p['zws']) * math.tan(math.radians(p['rake']))
    # side: convex nose (bumper level -> windshield base), raked windshield, big round roof front, rear face
    # leaning in at the top
    side = fillet_poly([(p['xr'] + 0.03, p['zb']), (p['xf'] - 0.10, p['zb']), (p['xf'] - 0.01, 1.18),
                        (p['xf'] + 0.02, p['zws']), (xw, p['zt']), (p['xr'] + 0.06, p['zt']),
                        (p['xr'], 1.30)],
                       [0.10, 0.12, 0.30, 0.10, p['r_roof_front'], p['r_roof_rear'], 0.30])
    plan = fillet_poly([(p['xr'], -p['hw_belt']), (p['xf'] + 0.03, -p['hw_belt']), (p['xf'] + 0.03, p['hw_belt']),
                        (p['xr'], p['hw_belt'])], [p['r_rear_plan'], p['r_front_plan'], p['r_front_plan'],
                                                   p['r_rear_plan']])
    hb, hm, hr, zb, zbl, zt = p['hw_bot'], p['hw_belt'], p['hw_roof'], p['zb'], p['zbelt'], p['zt']
    sec = fillet_poly([(-hb, zb), (hb, zb), (hm, zbl), (hr, zt), (0.0, zt + p['crown']), (-hr, zt), (-hm, zbl)],
                      [0.12, 0.12, 0.35, p['r_roof_side'], 0.0, p['r_roof_side'], 0.35])
    return side, plan, sec


def build(h=0.02, out='work/body_outer.npz'):
    side, plan, sec = profiles()
    S = sdf2d(side, -3.0, 3.0, 0.7, 3.3)
    PL = sdf2d(plan, -3.0, 3.0, -1.4, 1.4)
    SE = sdf2d(sec, -1.4, 1.4, 0.7, 3.3)
    xs = np.arange(-2.8, 2.86, h)
    ys = np.arange(-1.2, 1.2001, h)
    zs = np.arange(0.86, 3.16, h)
    X2, Z2 = np.meshgrid(xs, zs, indexing='ij')
    sd = sample(S, X2, Z2)                                   # (nx, nz)
    X3, Y3 = np.meshgrid(xs, ys, indexing='ij')
    pl = sample(PL, X3, Y3)                                  # (nx, ny)
    Y4, Z4 = np.meshgrid(ys, zs, indexing='ij')
    se = sample(SE, Y4, Z4)                                  # (ny, nz)
    f = smax(sd[:, None, :], pl[:, :, None], 0.05)
    f = smax(f, se[None, :, :], 0.06)
    v, fc, nrm, _ = measure.marching_cubes(f.astype(np.float32), 0.0, spacing=(h, h, h))
    v += np.array([xs[0], ys[0], zs[0]])
    fc = fc[:, ::-1]                                          # outward winding for Blender
    np.savez_compressed(os.path.join(HERE, out), v=v.astype(np.float32), f=fc.astype(np.int32))
    json.dump(dict(P=P, side=side, plan=plan, sec=sec), open(os.path.join(HERE, 'work', 'profiles.json'), 'w'))
    print('verts', len(v), 'faces', len(fc), 'bbox', v.min(0).round(3), v.max(0).round(3))


if __name__ == '__main__':
    build()
