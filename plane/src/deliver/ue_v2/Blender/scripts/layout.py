"""Shared cockpit/fuselage layout (Blender build frame: nose -Y, left/port +X, up +Z, metres).
Used by build_v2.py (geometry), cockpit.py, rig_ue.py and the livery shader."""
import math

# ------------------------------------------------------------------ fuselage stations (y, z_bottom, z_top, half_width, n)
# Cowl lowered vs v1 so the pilot sees over the nose: cowl top 2.05 at firewall, thrust line 1.70.
ST_FRONT = [
    (-4.62, 1.40, 1.98, 0.34, 3.0),
    (-4.55, 1.24, 2.02, 0.48, 3.6),
    (-4.40, 1.12, 2.04, 0.58, 4.5),
    (-4.00, 1.04, 2.05, 0.65, 5.5),
    (-3.35, 1.00, 2.05, 0.70, 6.0),
    (-3.25, 0.99, 2.10, 0.71, 6.5),
    (-2.90, 0.97, 2.40, 0.73, 7.0),
    (-2.58, 0.96, 2.66, 0.74, 7.0),
    (-1.00, 0.96, 2.66, 0.74, 7.0),
    (0.60, 0.96, 2.66, 0.74, 7.0),
    (1.10, 0.97, 2.66, 0.74, 7.0),
]
ST_TAIL_A = (1.50, 1.05, 2.645, 0.715, 6.5)
ST_TAIL_B = (5.05, 2.14, 2.38, 0.08, 3.5)
TAIL_YS = (1.50, 2.3, 3.1, 3.9, 4.6, 5.05)
SKIN_T = 0.03            # fuselage wall thickness
PROP_C = (0.0, -4.74, 1.70)
SPINNER_BASE_Y = -4.61

# ------------------------------------------------------------------ openings. Side outlines are (y, z) polygons, radius
W1 = ([(-3.08, 1.80), (-2.06, 1.80), (-2.06, 2.44), (-2.66, 2.44), (-3.08, 2.12)], 0.05)   # pilot-door window
W2 = ([(-1.90, 1.81), (-1.27, 1.81), (-1.27, 2.45), (-1.90, 2.45)], 0.06)
W3 = ([(-0.66, 1.85), (0.26, 1.85), (0.26, 2.37), (-0.66, 2.37)], 0.07)                   # right side only
W4 = ([(0.70, 1.87), (1.26, 1.87), (1.26, 2.37), (0.70, 2.37)], 0.07)
CARGO_WIN = ([(-0.60, 1.87), (0.20, 1.87), (0.20, 2.35), (-0.60, 2.35)], 0.07)             # in cargo door
PILOT_DOOR = ([(-3.12, 1.14), (-1.98, 1.14), (-1.98, 2.52), (-2.62, 2.52), (-3.12, 2.06)], 0.04)
CARGO_DOOR = ([(-0.85, 1.10), (0.45, 1.10), (0.45, 2.44), (-0.85, 2.44)], 0.07)
DOOR_GAP = 0.006
# windshield panes: (x, y) outlines in top projection, cut vertically
WS_L = ([(0.025, -3.28), (0.655, -3.28), (0.655, -2.65), (0.025, -2.65)], 0.06)
WS_R = ([(-0.655, -3.28), (-0.025, -3.28), (-0.025, -2.65), (-0.655, -2.65)], 0.06)

SIDE_FIXED = {'L': [W2, W4], 'R': [W2, W3, W4]}      # fixed side windows (cut from fuselage)
# hinges (Blender frame)
PILOT_DOOR_HINGE_Y = -3.10
CARGO_DOOR_HINGE = (0.752, 0.45, 1.77)

# ------------------------------------------------------------------ crew
SEAT_DY = -0.12            # seats moved forward vs v1 blockout
PILOT_EYE = (0.33, -2.24, 2.22)
COPILOT_EYE = (-0.33, -2.24, 2.22)
FLOOR_Z = 1.07
FIREWALL_Y = -3.32
REAR_BULKHEAD_Y = 1.32

# ------------------------------------------------------------------ instrument panel (vertical face, facing +Y / aft)
PANEL_Y = -2.985          # front face
PANEL_Z = (1.42, 2.04)
PANEL_HW = 0.66
GLARE = dict(y0=-3.26, y1=-2.955, z0=2.02, z1=2.08, hw=0.64)

# gauges: name -> (x, z, bezel_diameter, cell, needles)
#   needles: list of (bone_name, length_fraction, kind) ; kind in needle / card / plane / ball / pitchcard
G6, GE = 0.086, 0.064
GAUGES = {
    'ASI':   (0.426, 1.935, G6, 0, [('Needle_ASI', 0.88, 'needle')]),
    'ATT':   (0.330, 1.935, G6, 1, [('ATT_Roll', 1.0, 'rollcard')]),
    'ALT':   (0.234, 1.935, G6, 3, [('Needle_ALT100', 0.88, 'needle'), ('Needle_ALT1000', 0.55, 'needle_short')]),
    'TC':    (0.426, 1.835, G6, 4, [('TC_Plane', 0.8, 'plane'), ('TC_Ball', 1.0, 'ball')]),
    'HDG':   (0.330, 1.835, G6, 5, [('HDG_Card', 1.0, 'card')]),
    'VSI':   (0.234, 1.835, G6, 6, [('Needle_VSI', 0.88, 'needle')]),
    'TRQ':   (0.132, 1.950, GE, 7, [('Needle_TRQ', 0.85, 'needle')]),
    'ITT':   (0.132, 1.880, GE, 8, [('Needle_ITT', 0.85, 'needle')]),
    'NG':    (0.132, 1.810, GE, 9, [('Needle_NG', 0.85, 'needle')]),
    'PROP':  (0.132, 1.740, GE, 10, [('Needle_PROP', 0.85, 'needle')]),
    'FF':    (0.062, 1.950, GE, 11, [('Needle_FF', 0.85, 'needle')]),
    'OIL':   (0.062, 1.880, GE, 12, [('Needle_OILP', 0.8, 'needle'), ('Needle_OILT', 0.8, 'needle')]),
    'FUELL': (0.062, 1.810, GE, 13, [('Needle_FUELL', 0.85, 'needle')]),
    'FUELR': (0.062, 1.740, GE, 14, [('Needle_FUELR', 0.85, 'needle')]),
    'CLOCK': (-0.300, 1.935, GE, 15, [('Clock_Hour', 0.55, 'needle_short'), ('Clock_Min', 0.85, 'needle')]),
    'AMP':   (-0.380, 1.935, GE, 16, [('Needle_AMP', 0.85, 'needle')]),
}
ATT_CARD_CELL = 2
# needle rest angles (deg clockwise from 12 o'clock, as seen by the pilot) = value zero on the dial
NEEDLE_REST = {
    'Needle_ASI': 10.0, 'Needle_ALT100': 0.0, 'Needle_ALT1000': 0.0, 'Needle_VSI': -90.0,
    'Needle_TRQ': -135.0, 'Needle_ITT': -135.0, 'Needle_NG': -135.0, 'Needle_PROP': -135.0,
    'Needle_FF': -135.0, 'Needle_OILP': -150.0, 'Needle_OILT': 150.0,
    'Needle_FUELL': -60.0, 'Needle_FUELR': -60.0, 'Clock_Hour': 0.0, 'Clock_Min': 0.0, 'Needle_AMP': 0.0,
}
# radio stack boxes: name -> (x_center, z_center, width, height, cell)
RADIOS = {
    'GPSCOM': (-0.110, 1.935, 0.160, 0.100, 17),
    'AUDIO':  (-0.110, 1.862, 0.160, 0.034, 18),
    'XPDR':   (-0.110, 1.810, 0.160, 0.048, 19),
}
# toggle switches: bone -> x   (row at SWITCH_Z)
SWITCH_Z = 1.585
SWITCHES = [('SW_Battery', 0.600), ('SW_Avionics', 0.555), ('SW_FuelPump', 0.510), ('SW_Ignition', 0.465),
            ('SW_Starter', 0.420), ('SW_Beacon', 0.330), ('SW_Strobe', 0.285), ('SW_NavLights', 0.240),
            ('SW_Landing', 0.195)]
SWITCH_LABEL_CELL = 20

# ------------------------------------------------------------------ controls
YOKE_X = (0.33, -0.33)
YOKE_Z = 1.70
YOKE_HUB_Y = -2.78
PEDAL_HINGE = (-3.12, 1.10)     # (y, z)
PEDAL_DX = 0.10
PEDESTAL = dict(hw=0.07, y0=-2.985, y1=-2.55, z_top_front=1.42, z_top_back=1.36)
LEVERS = [('Lever_Power', 0.040, 'black'), ('Lever_Prop', 0.0, 'blue'), ('Lever_Condition', -0.040, 'red')]
LEVER_PIVOT = (-2.84, 1.395)    # (y, z)
FLAP_LEVER = ('Lever_Flap', -0.085, -2.66, 1.30)
TRIM_WHEEL = ('TrimWheel', 0.082, -2.72, 1.24, 0.075)

SEATS_X = (0.33, -0.33)


# ------------------------------------------------------------------ helpers
def rounded_poly(pts, r, seg=5):
    """Convex polygon corners rounded by r. Returns dense CCW-consistent point list (same winding as input)."""
    out = []
    n = len(pts)
    for i in range(n):
        p = pts[i]
        a = pts[i - 1]
        b = pts[(i + 1) % n]
        u1 = _norm((a[0] - p[0], a[1] - p[1]))
        u2 = _norm((b[0] - p[0], b[1] - p[1]))
        cosang = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        ang = math.acos(cosang)
        t = r / math.tan(ang / 2)
        bis = _norm((u1[0] + u2[0], u1[1] + u2[1]))
        dc = r / math.sin(ang / 2)
        c = (p[0] + bis[0] * dc, p[1] + bis[1] * dc)
        s = (p[0] + u1[0] * t, p[1] + u1[1] * t)
        e = (p[0] + u2[0] * t, p[1] + u2[1] * t)
        a0 = math.atan2(s[1] - c[1], s[0] - c[0])
        a1 = math.atan2(e[1] - c[1], e[0] - c[0])
        d = a1 - a0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        for k in range(seg + 1):
            aa = a0 + d * k / seg
            out.append((c[0] + r * math.cos(aa), c[1] + r * math.sin(aa)))
    return out


def offset_poly(pts, d):
    """Offset a convex polygon by d (positive = outward). Works for either winding."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1        # CCW -> outward normal is (dy, -dx)
    lines = []
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = dy / L * sgn, -dx / L * sgn
        lines.append(((p[0] + nx * d, p[1] + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def point_in_poly(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def _norm(v):
    L = math.hypot(v[0], v[1])
    return (v[0] / L, v[1] / L)


def fuselage_stations():
    st = list(ST_FRONT)
    a, b = ST_TAIL_A, ST_TAIL_B
    for y in TAIL_YS:
        t = (y - a[0]) / (b[0] - a[0])
        st.append(tuple([y] + [a[i] + (b[i] - a[i]) * t for i in range(1, 5)]))
    return st
