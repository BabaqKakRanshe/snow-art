"""Procedural cockpit materials (baked into T_Cockpit). World-space patterns, metres, Blender build frame."""
import math
from nodes import NB, weather, DIRT

SEAT_XS = (0.33, -0.33)
CAB_BOTTOM = (1.32, 1.07)          # interior grime only near the floor (FLOOR_Z 1.07)


def _grain(nb, P, scale, amt):
    return nb.mul(nb.noise(P, scale, 3, 0.6), amt)


def mat_panel(mat):
    nb = NB(mat)
    P = nb.P()
    _, _, z = nb.sep(P)
    crinkle = nb.noise(P, 420.0, 2, 0.5)
    c, m, r, h = weather(nb, P, (0.016, 0.017, 0.018, 1), 0.62, chip_amt=-0.07, dirt=0.25, edge_boost=0.2,
                         metal_col=(0.35, 0.35, 0.35, 1), primer=(0.05, 0.05, 0.05, 1), chip_scale=22.0, zworld=z, bottom=CAB_BOTTOM)
    nb.finish(c, m, r, nb.add(h, nb.mul(crinkle, 0.00012)))


def mat_black_plastic(mat, col=(0.012, 0.012, 0.013, 1), rough=0.45):
    nb = NB(mat)
    P = nb.P()
    _, _, z = nb.sep(P)
    c, m, r, h = weather(nb, P, col, rough, dirt=0.12, edge_boost=0.15, plastic=True, chip_scale=30.0, zworld=z,
                         bottom=CAB_BOTTOM)
    nb.finish(c, 0.0, r, nb.add(h, _grain(nb, P, 600.0, 0.00004)))


def mat_leather(mat, c0=(0.080, 0.047, 0.026, 1), c1=(0.060, 0.034, 0.019, 1), worn_col=(0.13, 0.085, 0.05, 1),
                thread=(0.14, 0.11, 0.075, 1), rough=0.5):
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    n1 = nb.noise(P, 3.0, 3, 0.5)
    base = nb.mixc(nb.ss(0.35, 0.7, n1), c0, c1)
    # seams: vertical panels on seats/glareshield, horizontal on backrests, one across the cushion
    ax = nb.abs(x)
    seams = []
    for sx in (0.21, 0.45):
        m, d = nb.line_mask(ax, 1000.0, 0.003, sx)       # period huge -> single line at |x| = sx
        seams.append((m, z))
    sz = [nb.line_mask(z, 1000.0, 0.003, zz) for zz in (1.62, 1.82)]
    sy, _ = nb.line_mask(y, 1000.0, 0.003, -2.33)
    groove = nb.mx(*[m for m, _ in seams], *[m for m, _ in sz], nb.mul(sy, nb.ss(1.47, 1.43, z)))
    # stitches: dashes 7 mm apart next to each seam
    dash = nb.ss(0.45, 0.55, nb.fract(nb.m('DIVIDE', nb.add(y, z, x), 0.007)))
    st = []
    for sx in (0.21, 0.45):
        for off in (-0.006, 0.006):
            st.append(nb.line_mask(ax, 1000.0, 0.0008, sx + off)[0])
    for zz in (1.62, 1.82):
        for off in (-0.006, 0.006):
            st.append(nb.line_mask(z, 1000.0, 0.0008, zz + off)[0])
    stitch = nb.mul(nb.mx(*st), dash)
    edge = nb.ss(0.95, 0.55, nb.edge_ao(0.015, 6))
    wear = nb.clamp01(nb.mul(edge, nb.ss(0.3, 0.7, nb.noise(P, 12.0, 4, 0.6)), 1.3))
    c = nb.mixc(nb.mul(wear, 0.6), base, worn_col)
    c = nb.mixc(nb.mul(groove, 0.6), c, (0.02, 0.012, 0.008, 1))
    c = nb.mixc(stitch, c, thread)
    cav = nb.ss(0.97, 0.5, nb.cavity_ao(0.1, 6))
    c = nb.mixc(nb.mul(cav, 0.3), c, DIRT)
    r = nb.add(rough, nb.mul(wear, -0.18), nb.mul(nb.noise(P, 90.0, 3, 0.5), 0.1))
    h = nb.add(_grain(nb, P, 900.0, 0.00012), nb.mul(groove, -0.0025), nb.mul(stitch, 0.0004))
    nb.finish(c, 0.0, nb.clamp01(r), h)


def mat_strap(mat):
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    weave, _ = nb.line_mask(nb.add(x, y, z), 0.0025, 0.0008)
    c = nb.mixc(nb.mul(weave, 0.5), (0.020, 0.024, 0.030, 1), (0.035, 0.04, 0.05, 1))
    nb.finish(c, 0.0, 0.8, nb.mul(weave, 0.0002))


def mat_rubber_mat(mat):
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    rib, _ = nb.line_mask(y, 0.012, 0.004)
    dust = nb.ss(0.45, 0.75, nb.noise(P, 6.0, 5, 0.6))
    c = nb.mixc(nb.mul(dust, 0.5), (0.012, 0.012, 0.012, 1), (0.10, 0.09, 0.075, 1))
    nb.finish(c, 0.0, nb.add(0.8, nb.mul(dust, 0.15)), nb.mul(rib, 0.0015))


def mat_vinyl(mat, col, seam_period=None):
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    c, m, r, h = weather(nb, P, col, 0.62, chip_amt=-0.06, dirt=0.3, edge_boost=0.2, plastic=True, chip_scale=18.0,
                         zworld=z, bottom=CAB_BOTTOM)
    h = nb.add(h, _grain(nb, P, 500.0, 0.00008))
    if seam_period:
        sm, _ = nb.line_mask(y, seam_period, 0.004)
        c = nb.mixc(nb.mul(sm, 0.5), c, (0.02, 0.02, 0.02, 1))
        h = nb.add(h, nb.mul(sm, -0.0015))
    nb.finish(c, 0.0, r, h)


def mat_floor(mat):
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    dots = nb.rivets(x, 0.02, 0.0, y, 0.02, 0.004)
    c, m, r, h = weather(nb, P, (0.035, 0.036, 0.038, 1), 0.75, dirt=0.6, edge_boost=0.2, plastic=True,
                         chip_scale=10.0, zworld=z, bottom=CAB_BOTTOM)
    scuff = nb.ss(0.55, 0.7, nb.noise(nb.vm('MULTIPLY', P, (1.0, 6.0, 1.0)), 5.0, 6, 0.7))
    c = nb.mixc(nb.mul(scuff, 0.4), c, (0.12, 0.11, 0.10, 1))
    nb.finish(c, 0.0, r, nb.add(h, nb.mul(dots, 0.0008)))


def mat_painted(mat, col, rough=0.55, chip=0.0):
    nb = NB(mat)
    P = nb.P()
    _, _, z = nb.sep(P)
    c, m, r, h = weather(nb, P, col, rough, chip_amt=chip, dirt=0.35, zworld=z, chip_scale=14.0,
                         bottom=CAB_BOTTOM)
    nb.finish(c, m, r, h)


def mat_metal(mat, col=(0.45, 0.45, 0.44, 1), rough=0.35):
    nb = NB(mat)
    P = nb.P()
    scratch = nb.ss(0.6, 0.75, nb.noise(nb.vm('MULTIPLY', P, (40.0, 1.0, 40.0)), 3.0, 4, 0.7))
    c = nb.mixc(nb.mul(scratch, 0.3), col, (0.6, 0.6, 0.6, 1))
    r = nb.add(rough, nb.mul(scratch, -0.1), nb.mul(nb.noise(P, 60.0, 3, 0.5), 0.1))
    nb.finish(c, 1.0, nb.clamp01(r), nb.mul(scratch, 0.00005))


def mat_flat(mat, col, rough=0.45, metal=0.0):
    nb = NB(mat)
    P = nb.P()
    nb.finish(col, metal, nb.add(rough, nb.mul(nb.noise(P, 80.0, 2, 0.5), 0.06)), nb.mul(nb.noise(P, 500.0, 2, 0.5), 0.00003))


def build_all(M):
    """M: dict name -> material"""
    get = lambda n: M.get(n)
    if get('src_CP_Panel'): mat_panel(M['src_CP_Panel'])
    if get('src_CP_Black'): mat_black_plastic(M['src_CP_Black'])
    if get('src_CP_Headset'): mat_black_plastic(M['src_CP_Headset'], (0.018, 0.018, 0.02, 1), 0.4)
    if get('src_CP_Leather'): mat_leather(M['src_CP_Leather'])
    if get('src_CP_Seat'): mat_leather(M['src_CP_Seat'])
    if get('src_CP_Glare'): mat_leather(M['src_CP_Glare'], (0.016, 0.016, 0.017, 1), (0.012, 0.012, 0.013, 1),
                                        (0.035, 0.035, 0.036, 1), (0.03, 0.03, 0.03, 1), rough=0.8)
    if get('src_CP_Strap'): mat_strap(M['src_CP_Strap'])
    if get('src_CP_Rubber'): mat_rubber_mat(M['src_CP_Rubber'])
    if get('src_CP_Trim'): mat_vinyl(M['src_CP_Trim'], (0.19, 0.19, 0.18, 1))
    if get('src_CabinWall'): mat_vinyl(M['src_CabinWall'], (0.11, 0.11, 0.105, 1), seam_period=0.6)
    if get('src_DoorPanel'): mat_vinyl(M['src_DoorPanel'], (0.12, 0.115, 0.11, 1))
    if get('src_CP_Floor'): mat_floor(M['src_CP_Floor'])
    if get('src_CP_Bulkhead'): mat_painted(M['src_CP_Bulkhead'], (0.07, 0.078, 0.07, 1), 0.6, chip=0.02)
    if get('src_CP_Metal'): mat_metal(M['src_CP_Metal'])
    if get('src_CP_Chrome'): mat_metal(M['src_CP_Chrome'], (0.75, 0.75, 0.74, 1), 0.12)
    if get('src_CP_Needle'): mat_flat(M['src_CP_Needle'], (0.85, 0.85, 0.82, 1), 0.4)
    if get('src_CP_KnobRed'): mat_flat(M['src_CP_KnobRed'], (0.55, 0.03, 0.02, 1), 0.35)
    if get('src_CP_KnobBlue'): mat_flat(M['src_CP_KnobBlue'], (0.02, 0.08, 0.40, 1), 0.35)
    if get('src_CP_Orange'): mat_flat(M['src_CP_Orange'], (0.85, 0.30, 0.02, 1), 0.4)
    if get('src_CP_Lens'): mat_flat(M['src_CP_Lens'], (0.75, 0.75, 0.72, 1), 0.2)
