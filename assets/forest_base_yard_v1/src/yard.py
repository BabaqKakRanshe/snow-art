"""yard frame helpers (ForestYardDress.json): u east, v north, metres from (340, -360), turned 8 deg with the main building.
Unity x = 340 + u cos8 + v sin8, z = -360 - u sin8 + v cos8; Blender = (-x, -z, y). In Blender the yard frame is a turn of
172 deg about +z (local x = +u, local y = +v), right-handed."""
import json, math, os
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
CX, CZ, YAW = 340.0, -360.0, 8.0
CO, SI = math.cos(math.radians(YAW)), math.sin(math.radians(YAW))
ROTZ = math.radians(180.0 - YAW)            # Blender rotation of the yard frame


def uv_to_unity(u, v):
    u = np.asarray(u, dtype=np.float64); v = np.asarray(v, dtype=np.float64)
    return CX + u * CO + v * SI, CZ - u * SI + v * CO


def unity_to_uv(x, z):
    dx = np.asarray(x, dtype=np.float64) - CX; dz = np.asarray(z, dtype=np.float64) - CZ
    return dx * CO - dz * SI, dx * SI + dz * CO


def uv_to_blender_xy(u, v):
    x, z = uv_to_unity(u, v)
    return -x, -z


def blender_to_uv(bx, by):
    return unity_to_uv(-np.asarray(bx), -np.asarray(by))


class Ground:
    """bilinear heights from the ground crop of base_scene (Unity metres)"""
    def __init__(self):
        self.h = np.load(os.path.join(D, 'data', 'ground_crop.npy')).astype(np.float64)
        g = json.load(open(os.path.join(D, 'data', 'ground_crop.json')))
        self.x0 = g['x0'] + g['i0'] * g['step']; self.z0 = g['z0'] + g['j0'] * g['step']; self.s = g['step']

    def at_unity(self, x, z):
        fx = (np.asarray(x, np.float64) - self.x0) / self.s; fz = (np.asarray(z, np.float64) - self.z0) / self.s
        nz, nx = self.h.shape
        i = np.clip(np.floor(fx).astype(int), 0, nx - 2); j = np.clip(np.floor(fz).astype(int), 0, nz - 2)
        tx = np.clip(fx - i, 0, 1); tz = np.clip(fz - j, 0, 1)
        h = self.h
        return (h[j, i] * (1 - tx) * (1 - tz) + h[j, i + 1] * tx * (1 - tz) + h[j + 1, i] * (1 - tx) * tz + h[j + 1, i + 1] * tx * tz)

    def at(self, u, v):
        x, z = uv_to_unity(u, v)
        return self.at_unity(x, z)


def raster_max(tris_uvh, u0, v0, step, nu, nv):
    """max height of triangles (n, 3, 3: u, v, h) on a grid (cell centres u0 + (i + .5) step); -inf where none"""
    H = np.full((nv, nu), -np.inf)
    for t in tris_uvh:
        a, b, c = t
        lo_u, hi_u = min(a[0], b[0], c[0]), max(a[0], b[0], c[0]); lo_v, hi_v = min(a[1], b[1], c[1]), max(a[1], b[1], c[1])
        i0 = max(0, int(math.floor((lo_u - u0) / step - 0.5)) + 1); i1 = min(nu - 1, int(math.floor((hi_u - u0) / step - 0.5)))
        j0 = max(0, int(math.floor((lo_v - v0) / step - 0.5)) + 1); j1 = min(nv - 1, int(math.floor((hi_v - v0) / step - 0.5)))
        if i1 < i0 or j1 < j0:
            continue
        uu = u0 + (np.arange(i0, i1 + 1) + 0.5) * step; vv = v0 + (np.arange(j0, j1 + 1) + 0.5) * step
        U, V = np.meshgrid(uu, vv)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (U - c[0]) + (c[0] - b[0]) * (V - c[1])) / d
        l2 = ((c[1] - a[1]) * (U - c[0]) + (a[0] - c[0]) * (V - c[1])) / d
        l3 = 1 - l1 - l2
        ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not ins.any():
            continue
        z = l1 * a[2] + l2 * b[2] + l3 * c[2]
        sub = H[j0:j1 + 1, i0:i1 + 1]
        np.maximum(sub, np.where(ins, z, -np.inf), out=sub)
    return H
