"""Painters for the forest_parts atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
Parts (the dosing pump, the sodium lamp's cap and frame, the radar tube, the relay unit, the generator; 1024 px at
256 px/m) and Sensor (the lake sensor; 512 px at 256 px/m). New spares out of the store and the parcel: the pump's skid in
the station's grey-green, a milky HDPE tank with its level lines, a blue motor and gearbox, grey PVC pipework, red valve
levers; the radar tube's black graphite coating and grey-green glass shoulder, a black implosion band; the relay unit's
dark grey powder coat and zinc-plated case; the generator's black frame, olive tank and covers, an aluminium engine, a
sooty muffler. The lake sensor weathered: a galvanised post with white rust and splash, a grey box gone chalky, mud on the
cable, the probe's steel darkened by the water."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, hash1
from gen_paint import RUST, _T, _common
import parts_kit as PK

DRAFT_COL = {
    PK.Z_SKID: (88, 104, 92), PK.Z_HANDLE: (88, 104, 92), PK.Z_TANK: (214, 210, 196), PK.Z_TANKCAP: (40, 70, 140),
    PK.Z_GEARBOX: (52, 80, 132), PK.Z_MOTOR: (52, 80, 132), PK.Z_HEAD: (170, 172, 168), PK.Z_PVC: (130, 132, 134),
    PK.Z_VALVE: (150, 152, 150), PK.Z_LEVER: (186, 40, 30), PK.Z_GAUGE: (30, 30, 32), PK.Z_HOSE: (40, 70, 130),
    PK.Z_TAPE: (156, 112, 58), PK.Z_LAMPCAP: (196, 196, 190), PK.Z_INSUL: (24, 24, 26), PK.Z_SOLDER: (176, 176, 172),
    PK.Z_WIRE: (170, 172, 170), PK.Z_BAND: (36, 36, 38), PK.Z_FUNNEL: (28, 28, 30), PK.Z_CRTGLASS: (120, 136, 130),
    PK.Z_NECK: (150, 160, 156), PK.Z_TUBEBASE: (30, 28, 26), PK.Z_PIN: (200, 190, 140), PK.Z_RACK: (66, 70, 74),
    PK.Z_RACKBODY: (160, 162, 160), PK.Z_RHANDLE: (190, 192, 196), PK.Z_KNURL: (34, 34, 36), PK.Z_CONN: (190, 186, 170),
    PK.Z_GFRAME: (30, 30, 32), PK.Z_GOLIVE: (82, 98, 64), PK.Z_ENGINE: (150, 152, 150), PK.Z_GBLACK: (34, 34, 36),
    PK.Z_MUFFLER: (70, 66, 62), PK.Z_RUBBER: (28, 28, 28), PK.Z_PANEL_D: (54, 56, 58), PK.Z_CHROME: (200, 202, 206),
    PK.Z_POST: (150, 154, 152), PK.Z_BOX: (176, 178, 172), PK.Z_BOXIN: (110, 112, 108), PK.Z_LATCH: (60, 60, 62),
    PK.Z_ANT: (30, 30, 30), PK.Z_SCABLE: (30, 30, 30), PK.Z_PROBE: (120, 124, 124), PK.Z_SIGNBACK: (176, 178, 176),
    PK.Z_CLIP: (150, 152, 150)}


def _local(Pp, root):
    o = PK.DISPLAY[root]
    return Pp[:, 0] - o.x, Pp[:, 1] - o.y, Pp[:, 2] - o.z


# ================================================================ Parts
def paint_parts(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp * 2.0, Nn, ao, 3101)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    dust = up * (0.4 + 0.6 * ss(0.35, 0.85, fbm(Pp, 50.0, 2, seed=3102)))
    px_, py_, pz_ = _local(Pp, 'Item_DosingPump')
    # ---- the dosing pump: the skid and handles in the station's grey-green, chipped at the edges
    for zz in (PK.Z_SKID, PK.Z_HANDLE):
        m = M(zz)
        c = T(lin(88, 104, 92), 0.05, 0.04)
        c = mixc(c, lin(128, 70, 44), ss(0.55, 0.85, edge * 1.2 + ss(0.86, 0.95, fbm(Pp, 40.0, 2, seed=3103)) * 0.4) * 0.6)
        c = mixc(c, lin(56, 64, 58), cav * 0.4)
        c = mixc(c, lin(130, 136, 128), dust * 0.25)
        col[m] = c[m]
    m = M(PK.Z_TANK)                                          # milky HDPE, the level lines on the front, a little dirt
    c = T(lin(214, 210, 196), 0.03, 0.03)
    c = mixc(c, lin(170, 166, 150), cav * 0.4 + ss(0.06, 0.0, pz_ - 0.06) * 0.3)
    front = (Nn[:, 1] < -0.3) & (px_ < -0.10) & (px_ > -0.30)
    lv = front & (pz_ > 0.10) & (pz_ < 0.50) & (np.abs(px_ + 0.29) < 0.02)
    c = np.where((lv & (dist_periodic(pz_, 0.05) < 0.0012))[:, None], lin(70, 70, 70), c)
    col[m] = c[m]
    m = M(PK.Z_TANKCAP)
    col[m] = mixc(T(lin(40, 70, 140), 0.04, 0.04), lin(90, 120, 190), edge * 0.4)[m]
    for zz in (PK.Z_GEARBOX, PK.Z_MOTOR):                     # RAL-blue drive, the motor's fins
        m = M(zz)
        c = T(lin(52, 80, 132), 0.04, 0.03)
        c = mixc(c, lin(110, 140, 190), edge * 0.35)
        c = mixc(c, lin(30, 44, 70), cav * 0.4)
        col[m] = c[m]
    fins = M(PK.Z_MOTOR) & (np.abs(Nn[:, 0]) < 0.7) & (px_ > 0.23) & (px_ < 0.37)
    gr = np.where(fins, gline(dist_periodic(np.arctan2(pz_ - 0.145, py_ - 0.02) * 0.064, 0.064 * 2 * math.pi / 20), 0.0012,
                              aa) * 0.8, gr)
    m = M(PK.Z_HEAD)
    col[m] = mixc(T(lin(170, 172, 168), 0.04, 0.05), lin(110, 112, 110), cav * 0.5)[m]
    m = M(PK.Z_PVC)
    col[m] = mixc(T(lin(130, 132, 134), 0.03, 0.03), lin(176, 178, 180), edge * 0.4)[m]
    m = M(PK.Z_VALVE)
    c = T(lin(156, 156, 150), 0.05, 0.06)
    col[m] = mixc(c, lin(200, 186, 120), ss(0.6, 0.8, fbm(Pp, 60.0, 2, seed=3104)) * 0.3)[m]
    m = M(PK.Z_LEVER)
    col[m] = mixc(T(lin(186, 40, 30), 0.03, 0.03), lin(236, 110, 90), edge * 0.4)[m]
    m = M(PK.Z_GAUGE)
    col[m] = mixc(T(lin(30, 30, 32), 0.04, 0.04), lin(120, 120, 124), edge * 0.5)[m]
    m = M(PK.Z_HOSE)                                          # a blue reinforced hose, a white stripe along it
    c = T(lin(40, 70, 130), 0.04, 0.05)
    c = mixc(c, lin(200, 200, 196), ss(0.92, 0.97, 0.5 + 0.5 * np.sin((x + y) * 9.0 + z * 40.0)) * 0.5)
    col[m] = mixc(c, lin(90, 84, 70), up * 0.2)[m]
    m = M(PK.Z_TAPE)
    col[m] = mixc(T(lin(156, 112, 58), 0.05, 0.06), lin(204, 164, 108), ss(0.6, 0.85, fbm(Pp, 80.0, 1, seed=3105)) * 0.3)[m]
    # ---- the sodium lamp's cap, insulator, contact and frame
    m = M(PK.Z_LAMPCAP)
    lz = _local(Pp, 'Item_SodiumLamp')[2]
    c = T(lin(196, 196, 190), 0.04, 0.05) * (0.80 + 0.24 * (0.5 + 0.5 * np.cos((lz - 0.010) * 2 * math.pi / 0.00635)))[:, None]
    col[m] = c[m]
    col[M(PK.Z_INSUL)] = mixc(T(lin(24, 24, 26), 0.02, 0.02), lin(90, 90, 96), edge * 0.5)[M(PK.Z_INSUL)]
    col[M(PK.Z_SOLDER)] = T(lin(176, 176, 172), 0.04, 0.05)[M(PK.Z_SOLDER)]
    col[M(PK.Z_WIRE)] = mixc(T(lin(170, 172, 170), 0.04, 0.06), lin(90, 92, 90), cav * 0.5)[M(PK.Z_WIRE)]
    # ---- the radar tube: the band (black enamel), the funnel's graphite, the glass shoulder, the neck, the base, the pins
    cx_, cy_, cz_ = _local(Pp, 'Item_RadarCRT')
    m = M(PK.Z_BAND)
    c = T(lin(36, 36, 38), 0.04, 0.04)
    c = mixc(c, lin(96, 96, 100), edge * 0.5)
    col[m] = c[m]
    m = M(PK.Z_FUNNEL)
    c = T(lin(28, 28, 30), 0.06, 0.10) * (0.9 + 0.2 * ss(0.4, 0.7, fbm(Pp, 30.0, 2, seed=3111)))[:, None]
    col[m] = c[m]
    m = M(PK.Z_CRTGLASS)
    refl = 0.5 + 0.5 * np.sin(Nn[:, 2] * 4.0 + np.arctan2(cy_, cx_) * 2.0)
    c = mixc(T(lin(96, 112, 106), 0.03, 0.03), lin(200, 214, 210), refl * 0.35)
    col[m] = c[m]
    m = M(PK.Z_NECK)
    col[m] = mixc(T(lin(150, 160, 156), 0.03, 0.03), lin(80, 86, 84), cav * 0.4)[m]
    col[M(PK.Z_TUBEBASE)] = mixc(T(lin(30, 28, 26), 0.04, 0.04), lin(80, 74, 66), edge * 0.4)[M(PK.Z_TUBEBASE)]
    col[M(PK.Z_PIN)] = T(lin(200, 190, 140), 0.05, 0.06)[M(PK.Z_PIN)]
    # ---- the relay unit: dark grey powder-coated front, the zinc-plated case with its vents, chrome handles
    rx_, ry_, rz_ = _local(Pp, 'Item_RelayUnit')
    m = M(PK.Z_RACK)
    c = T(lin(62, 66, 70), 0.04, 0.03)
    col[m] = mixc(mixc(c, lin(104, 108, 112), edge * 0.35), lin(40, 42, 44), cav * 0.4)[m]
    m = M(PK.Z_RACKBODY)
    c = T(lin(160, 162, 160), 0.05, 0.08)
    c = mixc(c, lin(186, 184, 170), ss(0.6, 0.8, fbm(Pp, 16.0, 2, seed=3121)) * 0.10)
    side = np.abs(Nn[:, 0]) > 0.9
    vents = side & (ry_ > -0.10) & (ry_ < 0.10) & (rz_ > 0.03) & (rz_ < 0.10)
    c = np.where((vents & (dist_periodic(ry_, 0.012) < 0.003))[:, None], lin(30, 30, 30), c)
    topc = Nn[:, 2] > 0.9
    for sx in (-0.19, 0.19):
        for sy in (-0.13, 0.13):
            c = np.where((topc & (np.hypot(rx_ - sx, ry_ - sy) < 0.003))[:, None], lin(60, 60, 60), c)
    col[m] = c[m]
    m = M(PK.Z_RHANDLE)
    col[m] = mixc(T(lin(190, 192, 196), 0.04, 0.05), lin(90, 92, 96), cav * 0.5)[m]
    m = M(PK.Z_KNURL)
    col[m] = mixc(T(lin(34, 34, 36), 0.04, 0.04), lin(90, 90, 94), edge * 0.6)[m]
    m = M(PK.Z_CONN)
    col[m] = mixc(T(lin(190, 186, 170), 0.05, 0.06), lin(110, 106, 90), cav * 0.5)[m]
    m = M(PK.Z_CHROME)
    col[m] = mixc(T(lin(200, 202, 206), 0.04, 0.05), lin(90, 92, 96), cav * 0.5)[m]
    # ---- the generator: black frame, olive tank and covers, aluminium engine, sooty muffler, rubber
    gx_, gy_, gz_ = _local(Pp, 'Item_BackupGenerator')
    m = M(PK.Z_GFRAME)
    c = T(lin(30, 30, 32), 0.05, 0.05)
    c = mixc(c, lin(90, 90, 92), edge * 0.5 + ss(0.85, 0.95, fbm(Pp, 40.0, 2, seed=3131)) * 0.3)
    col[m] = c[m]
    m = M(PK.Z_GOLIVE)
    c = T(lin(82, 98, 64), 0.05, 0.04)
    c = mixc(c, lin(130, 142, 110), edge * 0.35)
    c = mixc(c, lin(50, 58, 40), cav * 0.4)
    c = mixc(c, lin(120, 110, 80), ss(0.88, 0.96, fbm(Pp, 30.0, 2, seed=3132)) * 0.35)        # fuel spills by the cap
    col[m] = c[m]
    m = M(PK.Z_ENGINE)
    c = T(lin(150, 152, 150), 0.05, 0.08)
    c = mixc(c, lin(70, 66, 58), cav * 0.6 + ss(0.75, 0.92, fbm(Pp, 24.0, 2, seed=3133)) * 0.3)
    col[m] = c[m]
    m = M(PK.Z_GBLACK)
    col[m] = mixc(T(lin(34, 34, 36), 0.04, 0.04), lin(86, 86, 90), edge * 0.45)[m]
    m = M(PK.Z_MUFFLER)
    c = T(lin(70, 66, 62), 0.06, 0.08)
    c = mixc(c, lin(120, 74, 44), ss(0.55, 0.85, fbm(Pp, 30.0, 2, seed=3134)) * 0.5)
    c = mixc(c, lin(20, 18, 16), ss(0.30, 0.10, np.hypot(gx_ - 0.21, gz_ - 0.275)) * 0.6)
    col[m] = c[m]
    shield = M(PK.Z_MUFFLER) & (np.abs(Nn[:, 1]) > 0.8)
    gr = np.where(shield, (dist_periodic(gx_, 0.014) < 0.004) * (dist_periodic(gz_, 0.014) < 0.004) * 0.9, gr)
    m = M(PK.Z_RUBBER)
    col[m] = mixc(T(lin(28, 28, 28), 0.05, 0.05), lin(70, 70, 70), up * 0.3)[m]
    m = M(PK.Z_PANEL_D)
    col[m] = mixc(T(lin(54, 56, 58), 0.04, 0.04), lin(110, 112, 114), edge * 0.4)[m]
    return col, gr


# ================================================================ Sensor
def paint_sensor(Pp, Nn, Z, ao, aa):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n = len(x)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 3201)
    T = _T(n_lo, n_hi)
    M = lambda zz: (Z == zz)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    sx, sy, sz = _local(Pp, 'LakeSensor')
    m = M(PK.Z_POST)                                          # galvanised: spangle, white rust, splash and mud at the foot
    spang = hash1(np.floor(x * 140.0) + np.floor(y * 140.0) * 31.0 + np.floor(z * 140.0) * 57.0, 3202)
    c = T(lin(150, 154, 152), 0.08, 0.10) * (0.94 + 0.10 * spang)[:, None]
    c = mixc(c, lin(196, 198, 192), ss(0.60, 0.80, fbm(Pp, 12.0, 2, seed=3203)) * 0.45)
    c = mixc(c, RUST, ss(0.20, 0.05, sz) * ss(0.4, 0.7, fbm(Pp, 30.0, 2, seed=3204)) * 0.6)
    c = mixc(c, lin(92, 78, 60), ss(0.35, 0.02, sz) * 0.6)
    c = mixc(c, lin(66, 56, 44), ss(0.0, -0.05, sz) * 0.9)
    col[m] = c[m]
    m = M(PK.Z_BOX)                                           # grey polyester box, chalky on top, streaks under the lid
    c = T(lin(176, 178, 172), 0.05, 0.04)
    c = mixc(c, lin(206, 206, 200), up * 0.35)
    c = mixc(c, lin(120, 122, 116), cav * 0.4)
    streak = (Nn[:, 1] < -0.5) * ss(0.6, 0.85, fbm(Pp * np.array([1, 1, 0.15], np.float32), 30.0, 2, seed=3205))
    c = mixc(c, lin(130, 126, 110), streak * 0.3)
    col[m] = c[m]
    m = M(PK.Z_BOXIN)
    col[m] = mixc(T(lin(110, 112, 108), 0.04, 0.04), lin(60, 62, 60), cav * 0.5)[m]
    m = M(PK.Z_LATCH)
    col[m] = mixc(T(lin(60, 60, 62), 0.05, 0.05), lin(130, 130, 134), edge * 0.5)[m]
    m = M(PK.Z_ANT)
    col[m] = mixc(T(lin(30, 30, 30), 0.04, 0.04), lin(80, 80, 80), up * 0.2)[m]
    m = M(PK.Z_SCABLE)
    c = T(lin(30, 30, 30), 0.05, 0.05)
    c = mixc(c, lin(96, 82, 62), ss(0.04, 0.0, sz) * 0.7 + up * 0.15)
    col[m] = c[m]
    m = M(PK.Z_PROBE)
    c = T(lin(120, 124, 124), 0.06, 0.08)
    col[m] = mixc(c, lin(70, 62, 50), ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=3206)) * 0.5)[m]
    m = M(PK.Z_SIGNBACK)
    col[m] = mixc(T(lin(176, 178, 176), 0.05, 0.06), RUST, edge * 0.3)[m]
    m = M(PK.Z_CLIP)
    col[m] = mixc(T(lin(150, 152, 150), 0.06, 0.08), RUST, ss(0.7, 0.9, fbm(Pp, 50.0, 2, seed=3207)) * 0.4)[m]
    return col, gr
