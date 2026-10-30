"""start frame helpers (ForestStartDress.json): centre = the ZoneGate (-511.5175, 554.2235), yaw -42.3; u across the road
(+u north-east, downhill), v along it (+v north-west, out of the zone; the pad, van and spawn are at -v). Metres.
Unity x = CX + u cos(yaw) + v sin(yaw), z = CZ - u sin(yaw) + v cos(yaw); Blender = (-x, -z, y). In Blender the frame is a
turn of 180 - yaw = 222.3 deg about +z (local x = +u, local y = +v), right-handed."""
import json, math, os
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
CX, CZ, YAW = -511.5175, 554.2235, -42.3
CO, SI = math.cos(math.radians(YAW)), math.sin(math.radians(YAW))
ROTZ = math.radians(180.0 - YAW)


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
    """bilinear heights from the ground crop of start_scene (Unity metres)"""
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
