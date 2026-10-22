"""Main building — the signs, labels, plans, dials and papers of Update 3 (measured off the Forest model: every
M_ObsSigns / M_BV_Safety / M_ClockFace / M_Whiteboard island) as panel quads on main_tex's atlas: one panel object per room
(R_<Room>_Panel: the room's light zone), BaseMain_Panel outside, stickers on the fire doors as children of the leaves (they
swing with them), the dial faces under the Update 3 gauge needles. Backing plates where a sign stands proud."""
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, part, box6
import main_spec as S
import main_shell as MS
import main_ix_u3 as X
import main_tex as T
import main_furn as F

PX, NX, PY, NY, PZ = (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)
UG, OG = S.UG_F, S.OG_F


def panel_kb(owner):
    """the panel object of a room ('Ext' = outside, an IX part name = a sticker on that part)"""
    if owner == 'Ext':
        name, parent = 'BaseMain_Panel', 'BaseMain'
    elif owner.startswith('IX_') or owner == 'BaseMain_Opening':
        name, parent = owner + '_Panel', owner
    else:
        name, parent = 'R_' + owner + '_Panel', 'BaseMain'
    k = kb(name, 'panel')
    if name not in K.CONTRACT['parts']:
        piv = (0.0, 0.0, 0.0)
        if owner.startswith('IX_'):
            piv = X.IX[owner]['pivot']
        part(name, 'static', piv, parent=parent, note='signs, labels and papers (panel atlas)')
    return k


def quad(owner, region, c, n, w, h, lift=0.0015, up=(0, 0, 1)):
    k = panel_kb(owner)
    c, n = Vector(c), Vector(n).normalized()
    k.quad_uv(c + n * lift, n, w, h, T.uv(region), 0, up=Vector(up))


def plate(k, c, n, w, h, d, zone=None):
    """a backing plate standing d proud of its wall, the sign then goes on its front"""
    F.wall_box(k, c, n, w + 0.01, h + 0.01, d, zone or F.Z_STEELF)


def disc(owner, region, c, n, r, lift=0.0015, seg=20):
    """a round face (clock, gauge) on its body: the region's inscribed disc"""
    k = panel_kb(owner)
    c, n = Vector(c), Vector(n).normalized()
    x0, y0, x1, y1 = T.REG[region]
    cx, cy, h = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - 1.5
    k.disc_uv(c + n * lift, n, r, T.VT.uv((cx - h, cy - h, cx + h, cy + h), T.N), seg=seg)


def sign(owner, region, c, n, w, h, d=0.0, room_kb=None):
    """a sign on a wall face at c (centre on the wall plane), normal n; d > 0: on a plate that deep"""
    c, n = Vector(c), Vector(n)
    if d > 0 and room_kb is not None:
        plate(room_kb, c, n, w, h, d)
    quad(owner, region, c + n * d, n, w, h)


def build_signs():
    E = MS.ext()
    # ---------------- outside
    sign('Ext', 'obs_plate', (-5.15, -6.014, 1.75), NY, 1.25, 0.17)          # on its steel plate (main_rooms2)
    sign('Ext', 'garage', (-14.85, -5.0, 3.12), NY, 1.10, 0.442, 0.025, E)
    sign('Ext', 'befugt', (-9.40, -5.0, 1.55), NY, 0.70, 0.126, 0.025, E)
    sign('Ext', 'heizoel', (2.60, -6.0, 0.22), NY, 0.26, 0.118, 0.006, E)
    sign('Ext', 'klingel', (-7.35, -6.0, 1.60), NY, 0.26, 0.060, 0.006, E)
    sign('Ext', 'notstrom', (-8.60, -5.0, 1.36), NY, 0.42, 0.066, 0.006, E)
    # ---------------- stair tower: floor signs by each landing door, the roof door's warning
    T_ = MS.rkb('Treppenhaus')
    for z, reg in ((UG + 1.60, 'floor_UG'), (S.EG_F + 1.60, 'floor_EG'), (OG + 1.60, 'floor_1OG'), (8.20, 'floor_DACH')):
        sign('Treppenhaus', reg, (-0.95, 1.15, z), PY, 0.20, 0.20, 0.004, T_)
    sign('Treppenhaus', 'befugt', (1.15, 1.15, 8.15), PY, 0.50, 0.09, 0.004, T_)
    # ---------------- corridors
    k = MS.rkb('Flur_EG')
    sign('Flur_EG', 'kontroll', (-2.05, -1.0, 1.60), PY, 0.42, 0.118, 0.03, k)
    sign('Flur_EG', 'server', (2.15, 1.0, 1.60), NY, 0.42, 0.14, 0.03, k)
    sign('Flur_EG', 'evac_EG', (-1.30, 1.0, 1.60), NY, 0.594, 0.414, 0.012, k)
    sign('Flur_EG', 'pic_ext', (7.28, -1.0, 1.62), PY, 0.20, 0.20, 0.004, k)
    sign('Flur_EG', 'pic_call', (7.65, 0.85, 1.64), NX, 0.15, 0.15, 0.004, k)
    sign('Flur_EG', 'pic_call', (1.25, 1.0, 1.64), NY, 0.15, 0.15, 0.004, k)
    sign('Flur_EG', 'pic_nosmoke', (2.15, 1.0, 2.00), NY, 0.17, 0.17, 0.004, k)
    sign('Flur_EG', 'paper_a', (-2.78, 1.0, 1.47), NY, 0.15, 0.20)
    k = MS.rkb('Flur_OG')
    sign('Flur_OG', 'wohn', (0.0, -1.0, OG + 1.90), PY, 0.50, 0.154, 0.03, k)
    sign('Flur_OG', 'uv_og', (-3.00, 0.86, OG + 1.58), NY, 0.12, 0.04)
    sign('Flur_OG', 'evac_OG', (-1.30, 1.0, OG + 1.60), NY, 0.594, 0.414, 0.012, k)
    sign('Flur_OG', 'pic_ext', (-0.91, -1.0, OG + 1.62), PY, 0.20, 0.20, 0.004, k)
    sign('Flur_OG', 'pic_call', (1.25, 1.0, OG + 1.64), NY, 0.15, 0.15, 0.004, k)
    k = MS.rkb('Flur_UG')
    sign('Flur_UG', 'brand', (3.35, -1.0, UG + 1.60), PY, 0.42, 0.13, 0.03, k)
    sign('Flur_UG', 'hoch', (4.95, 1.0, UG + 1.60), NY, 0.42, 0.116, 0.03, k)
    sign('Flur_UG', 'technik', (3.20, 1.0, UG + 1.60), NY, 0.42, 0.184, 0.03, k)
    sign('Flur_UG', 'heiznot', (1.55, -1.0, UG + 1.77), PY, 0.42, 0.07, 0.004, k)
    sign('Flur_UG', 'evac_UG', (-1.30, 1.0, UG + 1.60), NY, 0.594, 0.414, 0.012, k)
    sign('Flur_UG', 'pic_call', (1.25, 1.0, UG + 1.64), NY, 0.15, 0.15, 0.004, k)
    sign('Flur_UG', 'pic_nosmoke', (3.35, -1.0, UG + 2.00), PY, 0.17, 0.17, 0.004, k)
    # ---------------- rooms
    k = MS.rkb('Windfang')
    sign('Windfang', 'tueren', (-7.65, -3.10, 2.25), PX, 0.90, 0.118, 0.006, k)
    sign('Windfang', 'pic_ext', (-5.25, -2.12, 1.62), NX, 0.20, 0.20, 0.004, k)
    sign('Windfang', 'pic_call', (-5.50, -5.65, 1.64), PY, 0.15, 0.15, 0.004, k)
    k = MS.rkb('Garage')
    sign('Garage', 'pic_ext', (-8.0, -2.41, 1.47), NX, 0.20, 0.20, 0.004, k)
    sign('Garage', 'pic_call', (-10.05, -4.70, 1.49), PY, 0.15, 0.15, 0.004, k)
    sign('Garage', 'pic_aid', (-8.0, 1.80, 1.57), NX, 0.15, 0.15, 0.004, k)
    sign('Garage', 'pic_aid', (-8.12, 1.80, 1.30), NX, 0.13, 0.13)                  # on the box's front
    sign('Garage', 'pic_nosmoke', (-16.60, 4.70, 1.75), NY, 0.17, 0.17, 0.004, k)
    sign('Garage', 'paper_b', (-12.58, 4.70, 1.32), NY, 0.15, 0.20)
    k = MS.rkb('Heizung')
    sign('Heizung', 'heizoel', (1.45, -4.27, UG + 1.15), PY, 0.42, 0.19, 0.004, k)
    sign('Heizung', 'procedure', (5.62, -1.162, UG + 1.55), NY, 0.15, 0.19)
    sign('Heizung', 'pic_ext', (3.40, -1.15, UG + 1.62), NY, 0.20, 0.20, 0.004, k)
    sign('Heizung', 'boiler_panel', (6.25, -2.155, UG + 1.325), NY, 0.88, 0.35)
    for x in (4.60, 4.74, 5.05, 5.19):                               # the pump group's thermometers
        k.cyl(Vector((x, -1.33, UG + 1.50)), Vector((x, -1.40, UG + 1.50)), 0.006, F.Z_BRASS, 6)
        k.cyl(Vector((x, -1.40, UG + 1.50)), Vector((x, -1.415, UG + 1.50)), 0.034, F.Z_CHROME, 14)
        disc('Heizung', 'therm', (x, -1.415, UG + 1.50), NY, 0.031)
    k.cyl(Vector((3.95, -1.84, UG + 1.20)), Vector((3.95, -1.86, UG + 1.20)), 0.04, F.Z_CHROME, 14)
    disc('Heizung', 'therm', (3.95, -1.86, UG + 1.20), NY, 0.036)                  # on the cylinder's jacket
    k = MS.rkb('Kueche')
    disc('Kueche', 'clock', (3.60, -1.15 - 0.045, OG + 2.00), NY, 0.12)
    sign('Kueche', 'calendar', (-0.50, -1.15, OG + 1.55), NY, 0.30, 0.40, 0.003, k)
    sign('Kueche', 'pic_aid', (7.65, -1.95, OG + 1.72), NX, 0.15, 0.15, 0.004, k)
    sign('Kueche', 'pic_aid', (7.53, -1.95, OG + 1.43), NX, 0.13, 0.13)
    k = MS.rkb('Leitstand')
    disc('Leitstand', 'clock', (2.0, -1.15 - 0.045, 2.30), NY, 0.135)
    sign('Leitstand', 'wb_leit', (6.0, -1.15, 1.45), NY, 1.68, 1.08, 0.024)
    quad('Leitstand', 'map', (-3.0, -3.50, 0.7605), PZ, 1.10, 0.75, lift=0.0, up=(0, 1, 0))
    quad('Leitstand', 'paper_c', (-3.30, -3.25, 0.7615), PZ, 0.266, 0.338, lift=0.0, up=(0, 1, 0))
    quad('Leitstand', 'paper_a', (0.60, -1.55, 0.7505), PZ, 0.29, 0.358, lift=0.0, up=(0, 1, 0))
    quad('Leitstand', 'display', (-5.03, -2.90, 1.65), PX, 2.50, 1.40)
    k = MS.rkb('Schaltraum')
    sign('Schaltraum', 'mimic', (1.98, 3.40, UG + 1.45), PX, 1.40, 0.90)
    sign('Schaltraum', 'hv_ug', (4.60, 5.65, UG + 2.25), NY, 0.20, 0.066, 0.004, k)
    sign('Schaltraum', 'hv_labels', (4.60, 5.30, UG + 1.75), NY, 1.44, 0.04)
    sign('Schaltraum', 'main_lbl', (4.60, 5.30, UG + 1.085), NY, 0.24, 0.05)
    sign('Schaltraum', 'pic_ext', (1.95, 5.215, UG + 1.38), PX, 0.20, 0.20, 0.004, k)
    k = MS.rkb('Stationsleiter')
    disc('Stationsleiter', 'clock', (4.30, 1.15 + 0.045, OG + 2.00), PY, 0.12)
    quad('Stationsleiter', 'paper_d', (4.60, 3.95, OG + 0.7515), PZ, 0.278, 0.348, lift=0.0, up=(0, 1, 0))
    quad('Stationsleiter', 'paper_a', (5.00, 3.85, OG + 0.7505), PZ, 0.238, 0.318, lift=0.0, up=(0, 1, 0))
    k = MS.rkb('Kaserne')
    quad('Kaserne', 'roster', (-1.95, -1.183, OG + 1.53), NY, 0.15, 0.21, lift=0.001)
    quad('Kaserne', 'paper_c', (-2.05, -1.183, OG + 1.60), NY, 0.12, 0.17, lift=0.0015)
    k = MS.rkb('Lager')
    quad('Lager', 'paper_d', (-3.70, 1.15, 1.50), PY, 0.21, 0.297, lift=0.001)
    # ---------------- the heating controller (BaseMain_Opening): its front, the dials under the needles
    quad('BaseMain_Opening', 'ctl_front', (0.90, -1.342, UG + 1.95), NY, 0.48, 1.48, lift=0.0005)
    quad('BaseMain_Opening', 'timer', (0.90, -1.343, UG + 1.52), NY, 0.12, 0.12, lift=0.0006)
    for nm, reg, r in (('IX_HeatGauge_309', 'mano', 0.047), ('IX_HeatTempGauge_310', 'therm', 0.0376)):
        p = Vector(X.IX[nm]['pivot'])
        disc('BaseMain_Opening', reg, (p.x, p.y + 0.0012, p.z), NY, r, lift=0.0)
    disc('BaseMain_Opening', 'mano', (6.15, -2.1612, UG + 1.38), NY, 0.0376, lift=0.0)
    # ---------------- fire-door stickers (both faces of the leaves; they swing with them)
    for nm, (u, z) in (('IX_Door_8', (0.01, 1.56)), ('IX_Door_12', (0.01, 4.96)), ('IX_Door_14', (2.49, -1.44)),
                       ('IX_Door_15', (0.01, -1.44)), ('IX_RoofDoor_17', (0.01, 8.16))):
        d = S.DOORS[nm]
        ax = d['wall'][0]
        pa = d.get('piv_y', d.get('piv_x'))
        th = 0.045
        for sg in (-1, 1):
            n = Vector((0, sg, 0)) if ax == 'y' else Vector((sg, 0, 0))
            c = Vector((u, pa + sg * (th / 2), z)) if ax == 'y' else Vector((pa + sg * (th / 2), u, z))
            quad(nm, 'feuertuer', c, n, 0.30, 0.062, lift=0.001)
