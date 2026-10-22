"""v8 airframe livery (numpy): BaseColor / MaskMap / Normal for the two airframe atlases from the baked geometry maps.
usage: python3 livery_v8.py <A|W|AW> [tag=v8] [--debug]
inputs  tex/<tag>/T8_<X>_{id,pos,nrm,ao}.npy (shade_v8.py): part code / material / v8zone / coverage, world position
        (build frame, rest pose), shading normal, AO (0.45 m, half res)
outputs tex/<tag>/T_{Airframe|Wing}_{BaseColor,MaskMap,Normal}.png (+ debug mask sheets with --debug)

Same paint scheme as v4-v7 (red, white stripe / bands, grey undersides, dark cowl, dark struts, logo, window seals).
v8: structural panel layout (fuselage frames and lap joints, cowl panels + camlocs, wing spars / ribs / joints,
inspection and tank access plates, tail spars / ribs) and wear and dirt where they really happen:
 leading-edge erosion (wing, tail, struts, cowl lip; stronger in the prop wash), sun-faded upper surfaces,
 exhaust soot behind the stacks, oil mist along the belly, fuel stains and nozzle scratches at the fillers, drain
 stains, slush / mud spray behind the main wheels (fuselage, strut, inboard flaps, tail undersides), boot scuffs at
 the pilot and cargo sills and steps, cargo-sill scrapes to bare metal, hand grime at door handles and the strut
 handle, chipped door / opening edges, hinge grease streaks, rain streaks under the windows, rope rub at the strut
 tie-down, hangar rash at tips, chipped camlocs, grime in seams and corners."""
import os, sys, math, json, time
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

ATL = sys.argv[1] if len(sys.argv) > 1 else 'AW'
TAG = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'v8'
DEBUG = '--debug' in sys.argv
TEX = os.path.join(HERE, 'tex', TAG)
NAME = {'A': 'Airframe', 'W': 'Wing'}
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


# ================================================================== colours (linear) and part codes
RED, RED2 = np.array([0.27, 0.024, 0.019]), np.array([0.20, 0.022, 0.018])
RED_FADE = np.array([0.36, 0.080, 0.064])
WHITE, WHITE_FADE = np.array([0.58, 0.56, 0.51]), np.array([0.56, 0.53, 0.44])
GREYB = np.array([0.36, 0.36, 0.35])
COWL = np.array([0.030, 0.030, 0.032])
STRUTP = np.array([0.030, 0.030, 0.032])
STEEL = np.array([0.42, 0.42, 0.41])
SEAL = np.array([0.018, 0.018, 0.018])
PRIMER = np.array([0.11, 0.115, 0.095])
METAL = np.array([0.56, 0.56, 0.55])
DIRT = np.array([0.075, 0.062, 0.048])
MUD = np.array([0.080, 0.064, 0.048])
SOOT = np.array([0.012, 0.011, 0.010])
OIL = np.array([0.018, 0.013, 0.008])
FUEL = np.array([0.26, 0.19, 0.075])
RUST = np.array([0.15, 0.05, 0.018])

FUS, WING, TE, FLAP, AIL, FIN, RUD, DORS, STAB, ELEV = {1}, {2}, {3, 4, 5}, {6, 7}, {8, 9}, {10}, {11}, {12}, {13}, \
    {14, 15}
PDOOR, CDOOR, STRUT, WDET, CAP = {16, 17}, {18, 19}, {20}, {21}, {22, 23}
W_LE, W_CH, W_Z0, DIH = -2.55, 2.10, 2.648, math.radians(2.0)


# ================================================================== helpers
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mixc(c, col, t):
    """c (n,3) towards colour col (3,) or (n,3) by t (n,)"""
    t = np.clip(t, 0, 1)[:, None]
    return c * (1 - t) + np.asarray(col, np.float32) * t


def isin(part, s):
    return np.isin(part, list(s))


class GNoise:
    """3D gradient (Perlin) noise, vectorised"""
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.perm = np.concatenate([rng.permutation(256)] * 2).astype(np.int32)
        g = rng.normal(size=(256, 3))
        self.grad = (g / np.linalg.norm(g, axis=1, keepdims=True)).astype(np.float32)

    def __call__(self, p):
        pi = np.floor(p)
        f = (p - pi).astype(np.float32)
        pi = pi.astype(np.int64)
        X, Y, Z = pi[:, 0] & 255, pi[:, 1] & 255, pi[:, 2] & 255
        pm, gr = self.perm, self.grad
        A = pm[X] + Y
        B = pm[X + 1] + Y
        AA, AB, BA, BB = pm[A] + Z, pm[A + 1] + Z, pm[B] + Z, pm[B + 1] + Z
        x, y, z = f[:, 0], f[:, 1], f[:, 2]

        def g(h, dx, dy, dz):
            v = gr[pm[h]]
            return v[:, 0] * dx + v[:, 1] * dy + v[:, 2] * dz
        u = f * f * f * (f * (f * 6 - 15) + 10)
        ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
        x1, y1, z1 = x - 1, y - 1, z - 1
        a = lerp(g(AA, x, y, z), g(BA, x1, y, z), ux)
        b = lerp(g(AB, x, y1, z), g(BB, x1, y1, z), ux)
        c = lerp(g(AA + 1, x, y, z1), g(BA + 1, x1, y, z1), ux)
        d = lerp(g(AB + 1, x, y1, z1), g(BB + 1, x1, y1, z1), ux)
        return lerp(lerp(a, b, uy), lerp(c, d, uy), uz)


NOISES = [GNoise(s) for s in range(12)]


def fbm(p, freq, octaves=3, gain=0.5, seed=0, stretch=(1.0, 1.0, 1.0)):
    """fractal noise mapped to ~[0, 1] (mean 0.5)"""
    q = p * np.asarray(stretch, np.float32) * freq
    tot = np.zeros(len(p), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        tot += amp * NOISES[(seed + o) % len(NOISES)](q + np.float32(17.31 * (seed + 1) + 3.7 * o))
        norm += amp
        amp *= gain
        q = q * 2.03
    return np.clip(0.5 + 1.1 * tot / norm, 0, 1)


def dist_sorted(v, arr):
    """distance from v to the nearest value of the sorted array arr"""
    arr = np.asarray(arr, np.float64)
    i = np.clip(np.searchsorted(arr, v), 1, len(arr) - 1)
    return np.minimum(np.abs(v - arr[i - 1]), np.abs(v - arr[i]))


def dist_periodic(v, period, offset=0.0):
    w = (v - offset) / period
    return np.abs(w - np.round(w)) * period


def groove(d, width, aa):
    """1 on a panel line of full width `width` (antialiased over aa)"""
    return 1.0 - ss(width * 0.5 - aa, width * 0.5 + aa, d)


def rivets(d_perp, s_along, spacing, radius, aa, offset=0.0):
    da = dist_periodic(s_along, spacing, offset)
    r = np.sqrt(d_perp * d_perp + da * da)
    t = 1.0 - ss(radius - aa, radius + aa, r)
    dome = np.sqrt(np.clip(1 - (r / radius) ** 2, 0, 1))
    return t, dome


def seg_dist(p, a, b):
    """distance from points p (n,3) to the segment a-b"""
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def sd_poly(u, v, poly, r):
    """signed distance to a convex polygon (u, v) with corner radius r (outside > 0)"""
    inner = LY.offset_poly(poly, -r)
    n = len(inner)
    area = sum(inner[i][0] * inner[(i + 1) % n][1] - inner[(i + 1) % n][0] * inner[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    d = None
    for i in range(n):
        (ax, ay), (bx, by) = inner[i], inner[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        nx, ny = dy / L * sg, -dx / L * sg
        e = (u - ax) * nx + (v - ay) * ny
        d = e if d is None else np.maximum(d, e)
    return d - r


def wz(x):
    return W_Z0 + np.maximum(0.0, np.abs(x) - 0.76) * math.tan(DIH)


def stab_le_te(x):
    ax = np.minimum(np.abs(x), 2.5)
    return 3.95 + (4.17 - 3.95) * ax / 2.5, 5.08 + (4.95 - 5.08) * ax / 2.5


def fin_le_te(z):
    lo = z <= 2.60
    t1 = (z - 2.36) / 0.24
    t2 = (z - 2.60) / 1.22
    le = np.where(lo, 3.22 + 0.25 * t1, 3.47 + 0.65 * t2)
    te = np.where(lo, 5.08 - 0.01 * t1, 5.07 - 0.09 * t2)
    return le, te


ST = LY.fuselage_stations()
ST_Y = np.array([s[0] for s in ST])
ST_ZB = np.array([s[1] for s in ST])
ST_ZT = np.array([s[2] for s in ST])
ST_HW = np.array([s[3] for s in ST])


def fus_section(y):
    return np.interp(y, ST_Y, ST_ZB), np.interp(y, ST_Y, ST_ZT), np.interp(y, ST_Y, ST_HW)


EXT = json.load(open(os.path.join(HERE, 'out', 'ext_v8.json')))
LOGO = (-1.42, 1.40, 0.40)
LOGO_IMG = np.asarray(Image.open(os.path.join(HERE, 'tex_src_logo.png')).convert('RGBA')).astype(np.float32) / 255.0


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def sample_logo(u, v):
    """bilinear sample of the logo (u, v in 0..1, v up); outside -> alpha 0"""
    h, w = LOGO_IMG.shape[:2]
    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
    fx = np.clip(u, 0, 1) * (w - 1)
    fy = (1 - np.clip(v, 0, 1)) * (h - 1)
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    tx, ty = (fx - x0)[:, None], (fy - y0)[:, None]
    c = (LOGO_IMG[y0, x0] * (1 - tx) * (1 - ty) + LOGO_IMG[y0, x1] * tx * (1 - ty) +
         LOGO_IMG[y1, x0] * (1 - tx) * ty + LOGO_IMG[y1, x1] * tx * ty)
    c[~inside] = 0
    return c


# ================================================================== the livery for one chunk of texels
def paint(P, Nn, part, mat, zone, ao, aa):
    """P (n,3) build-frame position, Nn (n,3) normal, part/mat/zone codes, ao (n,), aa = texel size (m)
    returns colour (n,3) linear, metal, rough, height (m), cavity (AO multiplier), debug dict"""
    n = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    nx, ny, nz = Nn[:, 0], Nn[:, 1], Nn[:, 2]
    ax = np.abs(x)
    sgx = np.where(x >= 0, 1.0, -1.0)
    isF = isin(part, FUS)
    isPD, isCD = isin(part, PDOOR), isin(part, CDOOR)
    isD = isPD | isCD
    isFD = isF | isD
    isW = isin(part, WING)
    isWall = isin(part, WING | TE | FLAP | AIL)
    isFinA = isin(part, FIN | RUD | DORS)
    isStabA = isin(part, STAB | ELEV)
    isS = isin(part, STRUT)
    isWD = isin(part, WDET)
    isCap = isin(part, CAP)
    liv = mat == 0
    seal = mat == 1
    sm = mat == 2                                          # strut paint material (struts, wing details, caps)
    side = ss(0.45, 0.65, np.abs(nx))
    up = ss(0.1, 0.4, nz)
    down = ss(0.1, 0.4, -nz)
    fwd = -ny                                              # facing the airflow
    D = {}

    # ------------------------------------------------------------ noise fields
    n_lo = fbm(P, 1.3, 3, seed=1)
    n_mid = fbm(P, 7.0, 3, seed=2)
    n_hi = fbm(P, 38.0, 2, seed=3)
    n_chip = fbm(P, 50.0, 3, gain=0.55, seed=4)
    n_clu = fbm(P, 3.5, 2, seed=10)
    n_spk = fbm(P, 110.0, 1, seed=5)
    n_flow = fbm(P, 5.0, 3, seed=6, stretch=(1.4, 0.12, 1.4))          # streaks along the airflow (y)
    n_rain = fbm(P, 9.0, 3, seed=7, stretch=(1.0, 1.0, 0.10))          # streaks running down (z)
    n_scr = fbm(P, 140.0, 2, seed=8, stretch=(1.0, 0.04, 1.0))         # long fine scratches along y
    n_spl = fbm(P, 22.0, 3, gain=0.6, seed=9)                          # splatter

    # ------------------------------------------------------------ paint scheme (v4..v7)
    cowl = isF & (y < -3.32)
    ya = np.maximum(y - 1.1, 0.0)
    zs = 1.64 + 0.1468 * ya
    hws = 0.12 - 0.0152 * ya
    stripe = (1 - ss(hws - 0.003, hws + 0.003, np.abs(z - zs))) * isFD * (~cowl) * (1 - ss(0.45, 0.7, -nz))
    inr = lambda v, a, b, s=0.003: ss(a - s, a + s, v) * (1 - ss(b - s, b + s, v))
    tailband = inr(y, 2.45, 2.80) * isF
    wingband = (inr(ax, 2.0, 2.8) + inr(ax, 5.1, 5.9)) * isWall
    finband = inr(z, 2.95, 3.20) * isFinA
    stabband = inr(ax, 0.9, 1.5) * isStabA
    paintW = np.clip(np.maximum.reduce([stripe, tailband, wingband, finband, stabband]), 0, 1)
    under = np.clip(down * (isWall | isStabA) + ss(0.5, 0.7, -nz) * isFD * (~cowl), 0, 1)
    col = mixc(np.tile(RED, (n, 1)).astype(np.float32), RED2, ss(0.4, 0.65, n_lo))
    # sun fade on upward painted surfaces (red goes pink-orange and chalky, white yellows a little)
    fade = ss(0.05, 0.85, nz) * (0.18 + 0.12 * n_lo) * liv
    col = mixc(col, RED_FADE, fade)
    whitec = mixc(np.tile(WHITE, (n, 1)).astype(np.float32), WHITE_FADE, fade * 0.8)
    col = mixc(col, whitec, paintW)
    col = mixc(col, GREYB, under)
    col = mixc(col, COWL, cowl.astype(np.float32))
    # logo on both fuselage sides
    lu = (y - LOGO[0]) * sgx / LOGO[2] + 0.5
    lv = (z - LOGO[1]) / LOGO[2] + 0.5
    lg = np.zeros((n, 4), np.float32)
    m = isF & (side > 0.01) & (np.abs(lu - 0.5) < 0.6) & (np.abs(lv - 0.5) < 0.6)
    if m.any():
        lg[m] = sample_logo(lu[m], lv[m])
    logo_a = lg[:, 3] * side * isF
    col = mixc(col, srgb_to_lin(lg[:, :3]), logo_a)
    # strut paint and steel fittings
    col = np.where(sm[:, None], STRUTP, col)
    fitting = (sm & (zone == 6)) | isCap                    # bare metal: tie-down ring, fuel caps
    pfit = sm & np.isin(zone, [1, 4])                        # strut / jury fittings: painted with the strut, a bit lighter
    col = np.where(pfit[:, None], STRUTP * 1.8, col)
    col = np.where(fitting[:, None], STEEL, col)
    col = np.where(seal[:, None], SEAL, col)
    rough = np.where(liv, 0.46 + 0.10 * (n_hi - 0.5) + 0.05 * paintW + 0.22 * fade - 0.06 * cowl, 0.5)
    rough = np.where(sm, 0.52 + 0.08 * (n_hi - 0.5), rough)
    rough = np.where(fitting, 0.38 + 0.1 * n_hi, rough)
    rough = np.where(seal, 0.72, rough)
    metal = np.where(fitting, 1.0, 0.0).astype(np.float32)
    height = 0.00002 * (n_spk - 0.5)

    # window frames (painted rubber ring round the real openings) on fuselage + doors
    d_side = None
    for poly, r in (LY.W1, LY.W2, LY.CARGO_WIN, LY.W4):
        d = sd_poly(y, z, poly, r)
        d_side = d if d_side is None else np.minimum(d_side, d)
    d_ws = np.minimum(sd_poly(x, y, *LY.WS_L), sd_poly(x, y, *LY.WS_R))
    g_side = side * isFD * inr(z, 1.6, 2.6)
    g_ws = ss(0.1, 0.25, nz) * isF * ss(2.0, 2.05, z) * inr(y, -3.34, -2.55)
    dwin = np.where(g_side > 0.5, d_side, 1.0)
    dwin = np.where(g_ws > 0.5, d_ws, dwin)
    frame = ss(-0.004, -0.001, dwin) * (1 - ss(0.026, 0.032, dwin)) * liv
    col = mixc(col, SEAL, frame)
    rough = lerp(rough, 0.7, frame)
    height += frame * 0.0006

    # ------------------------------------------------------------ structure: panel lines, rivets, camlocs, plates
    pl = np.zeros(n, np.float32)            # panel-line groove
    rv = np.zeros(n, np.float32)            # rivet heads (dome height 0..1)
    cam = np.zeros(n, np.float32)
    cam_ring = np.zeros(n, np.float32)
    W_G, R_RV, SP = 0.0045, 0.0048, 0.040
    aa2 = aa * 0.7
    # fuselage frames (rivet rows) and skin joints
    frames = np.array([-4.40, -3.90, -3.35, -2.95, -2.55, -2.05, -1.55, -1.05, -0.55, -0.05, 0.45, 0.95, 1.50, 2.0,
                       2.5, 3.0, 3.5, 4.0, 4.5])
    joints = np.array([-4.40, -3.35, -1.05, 1.50, 3.0])
    zb, ztp, hw = fus_section(y)
    eta = (z - zb) / np.maximum(ztp - zb, 0.05)
    hgt = np.maximum(ztp - zb, 0.05)
    s_ring = np.where(np.abs(nx) > np.abs(nz), z, x)
    nofr = isFD & (np.abs(ny) < 0.75) & (dwin > 0.03)
    d_fr = dist_sorted(y, frames)
    t, dm = rivets(d_fr, s_ring, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * (nofr & ~cowl & (d_fr < 0.02)))
    pl = np.maximum(pl, groove(dist_sorted(y, joints), W_G, aa2) * nofr)
    laps = np.array([0.16, 0.50, 0.86])
    d_lap = dist_sorted(eta, laps) * hgt
    pl = np.maximum(pl, groove(d_lap, W_G, aa2) * isF * (np.abs(nz) < 0.9) * (dwin > 0.03) * (~cowl))
    t, dm = rivets(np.abs(d_lap - 0.012), y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * isF * (np.abs(nz) < 0.9) * (dwin > 0.03) * (~cowl))
    keel = isF & (nz < -0.85)
    pl = np.maximum(pl, groove(np.abs(x), W_G, aa2) * keel)
    # rivet rows round the window and door openings (doublers 3.5 cm out)
    t, dm = rivets(np.abs(dwin - 0.045), y + z, 0.035, R_RV, aa2)
    rv = np.maximum(rv, dm * t * (g_side > 0.5) * liv * (dwin > 0.03))
    # cowl: nose bowl joint, side hinge line at mid height, camlocs along joints
    cj = groove(np.abs(y + 4.40), W_G, aa2) * cowl + groove(np.abs(eta - 0.55) * hgt, W_G, aa2) * cowl * side + \
        groove(np.abs(y + 3.35), W_G, aa2) * isF * (np.abs(y + 3.35) < 0.02)
    pl = np.maximum(pl, cj)
    # one row per joint, on the removable panel: aft of the nose-bowl joint, above the side hinge line, ahead of the
    # firewall joint
    for dperp, salong in (((y + 4.40) - 0.016, s_ring), ((eta - 0.55) * hgt - 0.016, y), ((y + 3.35) + 0.016, s_ring)):
        t, dm = rivets(np.abs(dperp), salong, 0.10, 0.008, aa2)
        cam = np.maximum(cam, t * cowl * (np.abs(dperp) < 0.02))
        t2, _ = rivets(np.abs(dperp), salong, 0.10, 0.019, aa2)
        cam_ring = np.maximum(cam_ring, t2 * (1 - t) * cowl * (np.abs(dperp) < 0.03))
    # wing box: LE skin joint, spars, station joints, ribs; inspection plates and tank panels underneath
    le = np.where(ax >= 3.9, W_LE - 0.059, W_LE)
    xc = (y - le) / W_CH
    upper = nz > 0
    wbox = isW & liv
    for xc_l, kind in ((0.11, 'pl'), (0.25, 'rv'), (0.69, 'rv')):
        d = np.abs(xc - xc_l) * W_CH
        if kind == 'pl':
            pl = np.maximum(pl, groove(d, W_G, aa2) * wbox * (fwd < 0.6))
        t, dm = rivets(np.abs(d - (0.012 if kind == 'pl' else 0.0)), x, SP, R_RV, aa2)
        rv = np.maximum(rv, dm * t * wbox * (fwd < 0.6))
    st_j = np.array([0.76, 2.30, 3.90, 5.30, 6.82])
    d_st = dist_sorted(ax, st_j)
    pl = np.maximum(pl, groove(d_st, W_G, aa2) * wbox * (np.abs(nx) < 0.7))
    ribs = dist_periodic(ax, 0.40, 0.76)
    t, dm = rivets(ribs, y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * wbox * (xc > 0.12) * (xc < 0.70) * (np.abs(nx) < 0.7))
    lower_w = wbox & ~upper
    insp = np.zeros(n, np.float32)
    for xi in (1.15, 2.05, 2.95, 4.35, 5.55, 6.40):
        for sg in (1, -1):
            r = np.hypot(x - sg * xi, (y - (W_LE + 0.45 * W_CH)))
            ring_ = groove(np.abs(r - 0.075), W_G, aa2)
            insp = np.maximum(insp, ring_ * lower_w)
            ang = np.arctan2(y - (W_LE + 0.45 * W_CH), x - sg * xi)
            t, dm = rivets(np.abs(r - 0.062), ang * 0.062, 2 * math.pi * 0.062 / 8, 0.0045, aa2)
            rv = np.maximum(rv, dm * t * lower_w * (r < 0.08))
    for sg in (1, -1):                                   # fuel tank access panels (screwed), inboard lower surface
        dpx = np.abs(x - sg * 1.55) - 0.22
        dpy = np.abs(y - (W_LE + 0.36 * W_CH)) - 0.14
        dbox = np.maximum(dpx, dpy)
        insp = np.maximum(insp, groove(np.abs(dbox), W_G, aa2) * lower_w)
        t, dm = rivets(np.abs(dbox + 0.014), np.where(np.abs(dpx) < np.abs(dpy), y, x), 0.05, 0.0045, aa2)
        rv = np.maximum(rv, dm * t * lower_w * (np.abs(dbox + 0.014) < 0.01))
    pl = np.maximum(pl, insp)
    # TE pieces, flaps, ailerons: front spar rivet row, ribs every 0.25 m
    cs = isin(part, TE | FLAP | AIL) & liv
    t, dm = rivets(dist_periodic(ax, 0.25, 0.80), y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * cs * (np.abs(nx) < 0.7) * (np.abs(ny) < 0.8))
    t, dm = rivets(np.abs(xc - 0.78) * W_CH, x, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * cs * (np.abs(ny) < 0.8))
    # stabiliser / elevators
    sle, ste = stab_le_te(x)
    xcs = (y - sle) / (ste - sle)
    stb = isin(part, STAB) & liv
    for xl in (0.12, 0.32):
        d = np.abs(xcs - xl) * (ste - sle)
        t, dm = rivets(d, x, SP, R_RV, aa2)
        rv = np.maximum(rv, dm * t * stb * (fwd < 0.6))
    pl = np.maximum(pl, groove(np.abs(xcs - 0.12) * (ste - sle), W_G, aa2) * stb * (fwd < 0.6))
    t, dm = rivets(dist_periodic(ax, 0.35, 0.0), y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * isStabA * liv * (np.abs(nx) < 0.7) * (np.abs(ny) < 0.8) * (ax > 0.25))
    # fin / rudder / dorsal
    fle, fte = fin_le_te(z)
    xcf = (y - fle) / (fte - fle)
    fn = isin(part, FIN) & liv
    for xl in (0.12, 0.32):
        d = np.abs(xcf - xl) * (fte - fle)
        t, dm = rivets(d, z, SP, R_RV, aa2)
        rv = np.maximum(rv, dm * t * fn * (fwd < 0.6) * (z > 2.45))
    pl = np.maximum(pl, groove(np.abs(xcf - 0.12) * (fte - fle), W_G, aa2) * fn * (fwd < 0.6) * (z > 2.45))
    t, dm = rivets(dist_periodic(z, 0.30, 2.45), y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * isin(part, FIN | RUD) * liv * (np.abs(nz) < 0.7) * (np.abs(ny) < 0.8) * (z > 2.5))
    dors = isin(part, DORS) & liv
    zt_line = np.interp(y, ST_Y, ST_ZT)
    t, dm = rivets(np.abs(z - zt_line - 0.045), y, SP, R_RV, aa2)
    rv = np.maximum(rv, dm * t * dors)
    pl = np.maximum(pl, groove(np.abs(z - zt_line - 0.03), W_G, aa2) * dors)
    # doors: rivet row along the skin edge doubler
    rv = rv * liv
    pl = pl * (liv | seal)

    # ------------------------------------------------------------ wear masks (0..1)
    # leading-edge erosion: facing the airflow, stronger in the prop wash; the cowl only at its lip
    le_k = np.select([isW | isin(part, TE), isStabA, isFinA, isS | isWD, cowl & (y < -4.42)], [1.0, 1.0, 0.85, 0.8, 1.0],
                     0.0)
    wash = 1 + 0.35 * (np.hypot(x, z - 1.70) < 1.45) * isStabA + 0.25 * (ax < 1.6) * isW
    E = ss(0.75, 0.98, fwd) * le_k * wash
    E = np.where(isFinA, E * ss(0.70, 0.99, fwd / np.maximum(np.hypot(ny, nz), 1e-3)), E)   # fin: true LE only
    E = np.clip(E * (0.75 + 0.5 * (n_mid - 0.5)), 0, 1)
    D['le_erosion'] = E
    # chip sources -> wear intensity W; the chips themselves are small (n_chip, 50 / m) and come in clusters (n_clu)
    # prop-wash gravel: lower cowl and forward belly, strongest at the front, fine specks (own term below)
    grav = isFD * ss(-0.05, -0.35, nz) * ss(1.38, 1.18, z) * ss(-1.2, -2.6, y) * (0.25 + 0.75 * ss(-3.4, -4.4, y)) * \
        np.clip(0.6 + 0.9 * (n_lo - 0.5), 0.2, 1.0)
    tips = (isWall & (ax > 6.92)) | (isStabA & (ax > 2.46)) | (isin(part, FIN | RUD) & (z > 3.78)) | \
        (isin(part, AIL) & (ax > 6.70)) | (isin(part, ELEV) & (ax > 2.45))  # hangar rash
    te_zone = isin(part, FLAP | AIL | ELEV | RUD | TE) * ss(0.92, 0.985, np.where(
        isin(part, RUD), (y - fle) / (fte - fle), np.where(isin(part, ELEV), xcs, xc)))
    d_pd = sd_poly(y, z, *LY.PILOT_DOOR)
    d_cd = sd_poly(y, z, *LY.CARGO_DOOR)
    d_door = np.minimum(np.abs(d_pd), np.abs(d_cd))
    edge_band = (1 - ss(0.010, 0.030, d_door)) * (isFD & (side > 0.3) & liv) * (1 + 0.5 * (z < 1.35))
    handles = [((0.752, -2.32, 1.70), PDOOR), ((0.752, -0.70, 1.75), CDOOR)]
    hand = np.zeros(n, np.float32)
    for (hx, hy, hz), parts_ in handles:
        r = np.hypot(y - hy, (z - hz) * 1.25)
        hand = np.maximum(hand, (1 - ss(0.03, 0.13, r)) * isin(part, parts_))
    hand *= (0.55 + 0.45 * n_mid) * side
    # boot scuffs: fuselage below the pilot door (from the gear-leg step), the door bottom, round the cargo step
    boot_p = isF & (side > 0.3) & (y > -3.10) & (y < -2.00) & (z > 0.97) & (z < 1.30)
    boot_p = boot_p * ss(1.30, 1.16, z) * ss(-3.10, -2.90, y) * ss(-2.00, -2.20, y)
    boot_pd = isPD * ss(1.36, 1.15, z) * 0.8
    boot_c = isF * (side > 0.3) * ss(-0.50, -0.38, y) * ss(0.10, -0.02, y) * ss(1.22, 1.00, z) * (z > 0.94)
    boot = np.clip(boot_p + boot_pd + boot_c, 0, 1) * (0.5 + 0.5 * n_mid)
    # cargo sill: fine scratches along y, the rim worn to metal; scratches on the door bottom
    scr = ss(0.70, 0.76, n_scr)
    sill = isF * (side > 0.3) * ss(-0.92, -0.80, y) * ss(0.52, 0.40, y) * ss(0.98, 1.06, z) * ss(1.115, 1.10, z)
    cdoor_low = isCD * ss(1.32, 1.12, z)
    scr_zone = np.maximum(sill, cdoor_low * 0.8)
    scrape_lines = scr_zone * scr
    scrape_metal = np.maximum(sill * ss(1.06, 1.095, z) * ss(0.40, 0.55, n_mid), scrape_lines * ss(0.76, 0.82, n_scr))
    D['scrape'] = np.maximum(scrape_lines, scrape_metal)
    # strut: hand grime at the grab handle, rope rub near the top
    strut_hand = np.zeros(n, np.float32)
    rope = np.zeros(n, np.float32)
    for k, sg in (('L', 1), ('R', -1)):
        gh = EXT['grab_handle'][k]
        dh = seg_dist(P, gh['a'], gh['b'])
        strut_hand = np.maximum(strut_hand, (1 - ss(0.02, 0.14, dh)) * (isS | isWD))
        dr = np.linalg.norm(P - np.array([3.36 * sg, -1.75, 2.585], np.float32), axis=1)
        rope = np.maximum(rope, (1 - ss(0.05, 0.13, dr)) * (isS | isWD))
        dt = np.linalg.norm(P - np.array([3.2 * sg, -1.62, 2.52], np.float32), axis=1)
        rope = np.maximum(rope, (1 - ss(0.03, 0.09, dt)) * (isW | isWD))
    handle_wear = isWD & (zone == 5)
    # fuel fillers: nozzle scratches ahead of the filler, stain ring + streaks aft; drains underneath
    fuel = np.zeros(n, np.float32)
    nozzle = np.zeros(n, np.float32)
    for sg in (1, -1):
        cx, cy = sg * 1.55, W_LE + 0.25 * W_CH
        dx, dy = x - cx, y - cy
        r = np.hypot(dx, dy)
        top = isW & (nz > 0.3)
        ring_ = (1 - ss(0.06, 0.13, r)) * top
        streak = np.exp(-(dx / (0.022 + 0.07 * np.clip(dy, 0, 1))) ** 2) * ss(-0.02, 0.05, dy) * (1 - ss(0.2, 0.8, dy))
        fuel = np.maximum(fuel, np.maximum(ring_ * 0.8, streak * top * (0.45 + 0.55 * n_flow)))
        # nozzle scratches round the filler neck, a narrow hose-drag path forward over the leading edge
        ann = ss(0.045, 0.06, r) * (1 - ss(0.11, 0.18, r))
        hose = np.exp(-(dx / 0.05) ** 2) * ss(-0.60, -0.45, dy) * ss(-0.04, -0.10, dy) * 0.6
        nozzle = np.maximum(nozzle, top * np.maximum(ann, hose))
        for dxd in (1.0, 2.4):                              # quick drains, lower surface
            ddx, ddy = x - sg * dxd, y - (-1.35)
            fuel = np.maximum(fuel, isW * (nz < -0.3) * np.exp(-(ddx / (0.012 + 0.05 * np.clip(ddy, 0, 1))) ** 2) *
                              ss(-0.02, 0.03, ddy) * (1 - ss(0.1, 0.45, ddy)) * 0.8)
    nozzle_lines = nozzle * ss(0.78, 0.82, n_scr)
    D['fuel'] = fuel
    # exhaust soot: from the stacks aft and slightly down along the sides
    soot = np.zeros(n, np.float32)
    for sg in (1, -1):
        t_ = y - (-3.80)
        zc = 1.56 - 0.07 * np.clip(t_, 0, None)
        sig = 0.07 + 0.11 * np.clip(t_, 0, None)
        core = np.exp(-((z - zc) / sig) ** 2) * ss(-0.08, 0.10, t_) * np.exp(-np.clip(t_, 0, None) / 2.2)
        soot = np.maximum(soot, core * isFD * (x * sg > 0.25) * (nz < 0.55) * (0.75 + 0.40 * n_flow))
    soot = np.clip(soot * 2.0, 0, 1)
    D['soot'] = soot
    # oil mist along the belly from the breather / drain, and seeping at the lower cowl joints
    t_ = y - (-3.70)
    oil = np.exp(-((x - 0.08 - 0.015 * np.clip(t_, 0, None)) / (0.05 + 0.07 * np.clip(t_, 0, None))) ** 2) * \
        ss(-0.05, 0.10, t_) * np.exp(-np.clip(t_, 0, None) / 3.2) * isF * (nz < -0.35)
    oil = oil * (0.4 + 0.8 * n_flow)
    oil = np.maximum(oil, cowl * (nz < 0.2) * pl * 0.8)
    oil = np.clip(oil, 0, 1)
    D['oil'] = oil
    # slush / mud spray behind the main wheels (fuselage sides + belly, lower strut, inboard flaps, tail undersides)
    mud = np.zeros(n, np.float32)
    for sg in (1, -1):
        t_ = y - (-2.85)
        fall = ss(-0.35, 0.15, t_) * np.exp(-np.clip(t_ - 0.15, 0, None) / 1.5)
        ztop = 1.20 + 0.22 * np.exp(-np.clip(t_, 0, None) / 0.9) + 0.10 * (n_lo - 0.5)
        hz = ss(ztop + 0.08, ztop - 0.10, z)
        faces = np.clip(0.45 + 0.4 * np.maximum(-ny, 0) + 0.5 * np.maximum(-nz, 0) + 0.3 * np.maximum(nx * sg, 0),
                        0, 1)
        fus_m = fall * hz * faces * isFD * (x * sg > -0.15)
        dstr = np.abs(x - sg * 1.25)
        str_m = (isS | isWD) * ss(1.85, 1.40, z) * (1 - ss(0.25, 0.9, dstr)) * \
            (0.25 + 0.75 * np.maximum(-nz, 0)) * (0.55 + 0.45 * np.maximum(ny, 0)) * 0.75
        flap_m = isin(part, FLAP | TE) * (nz < -0.3) * (1 - ss(0.5, 1.2, np.abs(x - sg * 1.25))) * 0.45
        mud = np.maximum(mud, np.maximum.reduce([fus_m, str_m, flap_m]))
    mud = np.maximum(mud, isStabA * (nz < -0.3) * (0.30 + 0.25 * (ax < 0.9)))
    mud = np.maximum(mud, isF * (y > 1.4) * (nz < -0.3) * (0.30 + 0.25 * ss(3.8, 4.4, y)))
    mud = np.maximum(mud, isFD * ss(1.30, 0.98, z) * (0.12 + 0.18 * n_lo))     # general lower-side road film
    spl = ss(0.42, 0.62, n_spl * 0.7 + mud * 0.45)
    mud_v = np.clip(mud * (0.35 + 0.65 * spl), 0, 1)
    D['mud'] = mud_v
    # hinge grease streaks (door hinges run down)
    hinge = np.zeros(n, np.float32)
    for hy, hzs in ((-3.11, (1.35, 2.00)), (0.462, (1.35, 2.20))):
        for hz_ in hzs:
            dzh = hz_ - z
            hinge = np.maximum(hinge, isFD * (side > 0.3) * np.exp(-((y - hy) / (0.012 + 0.03 * np.clip(dzh, 0, 1))) ** 2)
                               * ss(-0.03, 0.02, dzh) * (1 - ss(0.05, 0.35, dzh)) * (0.5 + 0.5 * n_rain))
    # rain streaks under the windows (lower corners and sill)
    rain = np.zeros(n, np.float32)
    rng = np.random.default_rng(5)
    for poly, r in (LY.W1, LY.W2, LY.CARGO_WIN, LY.W4):
        ys_ = [p[0] for p in poly]
        zb_w = min(p[1] for p in poly)
        y0, y1 = min(ys_), max(ys_)
        for ys in list(np.linspace(y0 + r, y1 - r, 5)) + [y0 + 0.01, y1 - 0.01]:
            L = rng.uniform(0.12, 0.45)
            w = rng.uniform(0.008, 0.02)
            dzr = zb_w - 0.03 - z
            rain = np.maximum(rain, isFD * side * np.exp(-((y - ys) / (w * (1 + 1.5 * np.clip(dzr / L, 0, 1)))) ** 2) *
                              ss(-0.02, 0.02, dzr) * (1 - ss(0.2 * L, L, dzr)) * rng.uniform(0.4, 0.9))
    rain *= (0.5 + 0.7 * n_rain)
    # grime: corners (AO), lower surfaces, seams
    cav = np.clip((0.78 - ao) / 0.45, 0, 1)
    grime = np.clip(0.55 * cav + 0.18 * ss(0.45, 0.75, n_lo) + 0.25 * down * isFD + 0.15 * ss(0.5, 0.8, n_flow) * side,
                    0, 1)
    seam_dirt = np.clip(pl * 0.9 + rv * 0.25 + insp * 0.5, 0, 1)
    # antenna-base and static-port halos
    halo = np.zeros(n, np.float32)
    for c, rr in (((0, 0.85, 2.66), 0.17), ((0, 1.30, 2.65), 0.07), ((0, 0.25, 2.66), 0.09), ((0, -1.05, 0.975), 0.17),
                  ((0.74, 2.30, 1.72), 0.05), ((-0.74, 2.30, 1.72), 0.05), ((0.28, -1.30, 2.75), 0.06),
                  ((-0.28, -1.30, 2.75), 0.06)):
        dd = np.linalg.norm(P - np.array(c, np.float32), axis=1)
        halo = np.maximum(halo, (1 - ss(rr * 0.6, rr * 1.4, dd)) * liv)
    # tail bumper scrapes (tail strike / tie-down)
    bumper = isF * (nz < -0.3) * (1 - ss(0.10, 0.30, np.hypot(y - 4.45, x))) * scr
    heat = cowl * np.exp(-((y + 3.95) / 0.25) ** 2) * np.exp(-((z - 1.58) / 0.22) ** 2) * side

    # ------------------------------------------------------------ combine
    painted = liv | sm
    Wc = np.clip(np.maximum.reduce([0.55 * tips, 0.45 * te_zone, 0.5 * edge_band, 0.75 * boot,
                                    0.55 * rope, 0.35 * cam_ring, 0.55 * pfit]), 0, 1) * painted
    cv = n_chip + 0.12 * (n_clu - 0.5)
    chip_p = ss(0.84 - 0.18 * Wc, 0.865 - 0.18 * Wc, cv) * (Wc > 0.02)
    chip_m = ss(0.89 - 0.18 * Wc, 0.915 - 0.18 * Wc, cv) * (Wc > 0.02)
    # gravel: fine specks (n_spk, 110 / m) in loose clusters, a few through to metal
    gv = n_spk + 0.15 * (n_clu - 0.5)
    grav_p = ss(0.95 - 0.10 * grav, 0.97 - 0.10 * grav, gv) * (grav > 0.02) * painted
    grav_m = ss(0.99 - 0.06 * grav, 1.01 - 0.06 * grav, gv) * (grav > 0.02) * painted
    chip_p = np.maximum(chip_p, grav_p)
    chip_m = np.maximum(chip_m, grav_m)
    D['chips'] = chip_p
    # erosion look: paint thinned (lighter, matte), pitting to primer in clusters, a broken metal line at the
    # stagnation edge
    thin = ss(0.15, 0.6, E) * painted
    col = mixc(col, col * 0.78 + 0.22 * np.array([0.30, 0.28, 0.26]), thin * 0.6)
    rough = lerp(rough, 0.72, thin)
    cl = 0.6 + 0.8 * n_clu
    pit = ss(0.90 - 0.12 * E * cl, 0.92 - 0.12 * E * cl, n_spk + 0.1 * (n_chip - 0.5)) * (E > 0.25)
    le_metal = ss(0.80, 0.92, E) * ss(0.42, 0.55, n_mid)
    to_primer = np.clip(np.maximum.reduce([chip_p, pit, scrape_lines * 0.9, nozzle_lines * 0.9,
                                           handle_wear * ss(0.40, 0.55, n_mid), bumper * 0.8]), 0, 1) * painted
    to_metal = np.clip(np.maximum.reduce([chip_m, le_metal * painted, scrape_metal, nozzle_lines * ss(0.74, 0.8, n_scr),
                                          handle_wear * ss(0.50, 0.62, n_mid)]), 0, 1) * painted
    col = mixc(col, PRIMER, to_primer)
    col = mixc(col, METAL, to_metal)
    rough = lerp(rough, 0.80, to_primer * (1 - to_metal))
    rough = lerp(rough, 0.34 + 0.12 * n_hi, to_metal)
    metal = np.maximum(metal, to_metal)
    height -= 0.00012 * to_primer                              # chipped paint: a paint-thickness step
    # hand grime (darker, slightly greasy but polished in the middle)
    hand_all = np.clip(hand + strut_hand * 0.8, 0, 1)
    col = mixc(col, col * 0.55 + DIRT * 0.45, hand_all * 0.75)
    rough = lerp(rough, 0.30, hand_all * 0.5)
    # dirt layers
    col = mixc(col, DIRT, np.clip(grime * 0.55 + seam_dirt * 0.45 + halo * 0.35 + rain * 0.6 + boot * 0.35, 0, 1) *
               (1 - to_metal * 0.5))
    rough = lerp(rough, 0.86, np.clip(grime * 0.5 + rain * 0.4 + boot * 0.3, 0, 1))
    col = mixc(col, MUD, mud_v * 0.85)
    rough = lerp(rough, 0.92, mud_v)
    metal = metal * (1 - mud_v)
    height += 0.00025 * mud_v * ss(0.5, 0.75, n_spl)
    col = mixc(col, FUEL * 0.5 + col * 0.5, fuel * 0.6)
    rough = lerp(rough, 0.55, fuel * 0.5)
    col = mixc(col, SOOT * 0.6 + DIRT * 0.4, soot * 0.92)
    rough = lerp(rough, 0.80, soot * 0.7)
    col = mixc(col, OIL, np.clip(oil * 0.85 + hinge * 0.8, 0, 1))
    rough = lerp(rough, 0.24, np.clip(oil + hinge, 0, 1) * 0.8)
    col = mixc(col, RUST, rope * isWD * (zone == 6) * 0.5)
    col = mixc(col, col * np.array([0.8, 0.75, 0.9]), heat * 0.6)
    metal = metal * (1 - np.clip(soot + oil + fuel * 0.5, 0, 1) * 0.8)
    # camlock heads: painted over with the cowl, worn through to dull steel on the crown
    col = mixc(col, STEEL * 0.45, cam * 0.55)
    metal = np.maximum(metal, cam * 0.45)
    rough = lerp(rough, 0.50, cam)
    # heights: panel grooves, rivets, camlocs
    height += -0.0007 * pl + 0.00035 * rv + 0.0009 * cam - 0.0003 * insp
    cavity = 1.0 - 0.25 * pl - 0.12 * insp
    D.update(panel=pl, rivet=rv, grime=grime, rain=rain, hand=hand_all, boot=boot, hinge=hinge)
    return col.astype(np.float32), metal.astype(np.float32), np.clip(rough, 0.05, 1).astype(np.float32), \
        height.astype(np.float32), cavity.astype(np.float32), D


# ================================================================== per atlas
_PAD = {}


def pad(img, covered):
    """fill uncovered texels from the nearest covered texel (texture padding for mip maps)"""
    key = id(covered)
    if key not in _PAD:
        _PAD.clear()
        _PAD[key] = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
    idx = _PAD[key]
    return img[idx[0], idx[1]]


def run(atl):
    name = NAME[atl]
    idm = np.load(os.path.join(TEX, f'T8_{atl}_id.npy'), mmap_mode='r')
    pos = np.load(os.path.join(TEX, f'T8_{atl}_pos.npy'), mmap_mode='r')
    nrm = np.load(os.path.join(TEX, f'T8_{atl}_nrm.npy'), mmap_mode='r')
    ao_half = np.load(os.path.join(TEX, f'T8_{atl}_ao.npy')).astype(np.float32)[..., 0]
    H, W = idm.shape[:2]
    ao = np.asarray(Image.fromarray(ao_half).resize((W, H), Image.BILINEAR), np.float32)
    covered = np.asarray(idm[..., 3]) > 0.5
    rows, cols = np.nonzero(covered)
    N = len(rows)
    log(f'{name}: {H}x{W}, covered {N} texels ({N / (H * W) * 100:.1f} %)')
    # texel size (m): median distance between horizontally adjacent covered texels
    samp = np.random.default_rng(0).choice(N, min(N, 200000), replace=False)
    r_, c_ = rows[samp], np.minimum(cols[samp] + 1, W - 1)
    ok = covered[r_, c_]
    dpos = np.linalg.norm(np.asarray(pos[r_[ok], c_[ok]]) - np.asarray(pos[rows[samp][ok], cols[samp][ok]]), axis=1)
    texel = float(np.median(dpos))
    log(f'  texel size {texel * 1000:.2f} mm ({1 / texel:.0f} px/m)')
    BC = np.zeros((H, W, 3), np.float32)
    MET = np.zeros((H, W), np.float32)
    RGH = np.zeros((H, W), np.float32)
    HGT = np.zeros((H, W), np.float32)
    CAV = np.ones((H, W), np.float32)
    dbg = {}
    CH = 1_000_000
    for s in range(0, N, CH):
        rr, cc = rows[s:s + CH], cols[s:s + CH]
        P = np.asarray(pos[rr, cc], np.float32)
        Nn = np.asarray(nrm[rr, cc], np.float32)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-6)
        ids = np.asarray(idm[rr, cc], np.float32)
        part, mat, zone = (np.round(ids[:, k]).astype(np.int32) for k in range(3))
        col, met, rgh, hgt, cav, D = paint(P, Nn, part, mat, zone, ao[rr, cc], texel)
        BC[rr, cc], MET[rr, cc], RGH[rr, cc], HGT[rr, cc], CAV[rr, cc] = col, met, rgh, hgt, cav
        if DEBUG:
            for k, v in D.items():
                if k not in dbg:
                    dbg[k] = np.zeros((H, W), np.float32)
                dbg[k][rr, cc] = v
        log(f'  chunk {s // CH + 1}/{(N + CH - 1) // CH}')
    # padding, normal map from height, packing
    BC, MET, RGH, HGT, CAV = (pad(a, covered) for a in (BC, MET, RGH, HGT, CAV))
    gx = (np.roll(HGT, -1, axis=1) - np.roll(HGT, 1, axis=1)) / (2 * texel)
    gv = -(np.roll(HGT, -1, axis=0) - np.roll(HGT, 1, axis=0)) / (2 * texel)      # +v = up = towards row 0
    nrm_ts = np.dstack([-gx, -gv, np.ones_like(gx)])
    nrm_ts /= np.linalg.norm(nrm_ts, axis=2, keepdims=True)
    Image.fromarray((lin_to_srgb(BC) * 255 + 0.5).astype(np.uint8), 'RGB').save(
        os.path.join(TEX, f'T_{name}_BaseColor.png'), optimize=True)
    Image.fromarray(((nrm_ts * 0.5 + 0.5) * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGB').save(
        os.path.join(TEX, f'T_{name}_Normal.png'), optimize=True)
    ao_final = np.clip(pad(ao, covered) * CAV, 0, 1)
    mask = np.dstack([MET, ao_final, np.ones_like(MET), 1 - RGH])
    Image.fromarray((mask * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA').save(
        os.path.join(TEX, f'T_{name}_MaskMap.png'), optimize=True)
    log(f'  saved T_{name}_BaseColor / Normal / MaskMap')
    if DEBUG:
        keys = sorted(dbg)
        thumbs = []
        for k in keys:
            im = Image.fromarray((np.clip(dbg[k], 0, 1) * 255).astype(np.uint8), 'L').resize((1024, 1024),
                                                                                         Image.BILINEAR)
            thumbs.append((k, im))
        cols_ = 4
        sheet = Image.new('L', (cols_ * 1024, ((len(thumbs) + cols_ - 1) // cols_) * 1024))
        for i, (k, im) in enumerate(thumbs):
            sheet.paste(im, ((i % cols_) * 1024, (i // cols_) * 1024))
        sheet.save(os.path.join(TEX, f'dbg_{name}.png'))
        json.dump(keys, open(os.path.join(TEX, f'dbg_{name}.json'), 'w'))
    return texel


if __name__ == '__main__':
    info = {}
    for a in ATL:
        info[NAME[a]] = run(a)
    print('texel sizes (m):', info)
