"""v7 procedural materials for the Details atlas (prop blades, tundra tyres, exhaust heat tint, brakes, ladder, key).
Same conventions as nodes.py: the materials are baked into T_Details_* by shade_v7.py."""
from nodes import NB, weather, mat_generic

EXHAUST_MOUTHS = [(0.725, -3.80, 1.565), (-0.725, -3.80, 1.565)]


def mat_blade_v7(mat):
    """satin black blades (anti-glare, MSFS SDK advice), yellow tip band from r = 1.20 m, light leading-edge wear"""
    nb = NB(mat)
    O = nb.obj()
    ox, oy, oz = nb.sep(O)
    r = nb.sqrt(nb.add(nb.mul(ox, ox), nb.mul(oz, oz)))
    tip = nb.ss(1.195, 1.202, r)
    base = nb.mixc(tip, (0.011, 0.011, 0.012, 1), (0.80, 0.50, 0.02, 1))
    c, m, rr, h = weather(nb, O, base, 0.55, chip_amt=0.0, rust_amt=0.0, dirt=0.10, edge_boost=0.08,
                          chip_scale=22.0)
    nb.finish(c, m, rr, h)


def mat_rubber_v7(mat):
    """black tyre rubber: dust only in the grooves between the lugs and in sidewall recesses, matte"""
    nb = NB(mat)
    O = nb.obj()
    n1 = nb.noise(O, 9.0, 6, 0.6)
    ng = nb.noise(O, 70.0, 4, 0.6)
    cav = nb.ss(0.92, 0.45, nb.cavity_ao(0.06, 8))
    dust = nb.clamp01(nb.mul(nb.add(nb.mul(cav, 0.75), nb.mul(nb.ss(0.55, 0.8, n1), 0.25)), 0.85))
    base = nb.mixc(nb.mul(ng, 0.35), (0.016, 0.016, 0.016, 1), (0.026, 0.025, 0.024, 1))
    c = nb.mixc(nb.mul(dust, 0.75), base, (0.13, 0.11, 0.085, 1))
    r = nb.mixf(dust, nb.add(0.82, nb.mul(ng, 0.08)), 0.95)
    edge = nb.ss(0.95, 0.6, nb.edge_ao(0.008, 6))                   # scuffed lug edges: a little shinier
    r = nb.mixf(nb.mul(edge, 0.5), r, 0.6)
    nb.finish(c, 0.0, r, nb.mul(ng, 0.0003))


def mat_metal_dark_v7(mat):
    """as nodes.mat_metal_dark + heat tint (straw -> blue -> grey) and soot at the exhaust mouths"""
    nb = NB(mat)
    P = nb.P()
    x, y, z = nb.sep(P)
    n = nb.noise(P, 6.0, 5, 0.6)
    col = nb.mixc(nb.ss(0.35, 0.7, n), (0.11, 0.09, 0.075, 1), (0.05, 0.045, 0.04, 1))
    c, m, r, h = weather(nb, P, col, 0.5, chip_amt=0.0, rust_amt=0.8, dirt=0.4, zworld=z, metallic_base=0.9)
    near = 0.0
    for mx_, my_, mz_ in EXHAUST_MOUTHS:
        dx, dy, dz = nb.sub(x, mx_), nb.sub(y, my_), nb.sub(z, mz_)
        d = nb.sqrt(nb.add(nb.mul(dx, dx), nb.mul(dy, dy), nb.mul(dz, dz)))
        near = nb.mx(near, nb.ss(0.30, 0.02, d))
    hn = nb.noise(P, 18.0, 4, 0.6)
    straw = nb.mul(nb.ss(0.15, 0.45, near), nb.ss(0.75, 0.45, near))
    blue = nb.mul(nb.ss(0.45, 0.75, near), nb.ss(0.95, 0.80, near))
    c = nb.mixc(nb.mul(straw, 0.55, hn), c, (0.30, 0.20, 0.08, 1))
    c = nb.mixc(nb.mul(blue, 0.6), c, (0.10, 0.12, 0.20, 1))
    soot = nb.ss(0.80, 0.98, near)                                 # inside the mouth: soot
    c = nb.mixc(soot, c, (0.012, 0.011, 0.010, 1))
    r = nb.mixf(soot, r, 0.95)
    m = nb.mul(m, nb.inv(soot))
    nb.finish(c, m, r, h)


def build_v7(MAT):
    mat_blade_v7(MAT['src_PropBlade'])
    mat_rubber_v7(MAT['src_Rubber'])
    mat_metal_dark_v7(MAT['src_MetalDark'])
    mat_generic(MAT['src_Brake'], (0.42, 0.42, 0.41, 1), 0.35, metallic_base=1.0, rust_amt=0.5, dirt=0.35)
    mat_generic(MAT['src_Caliper'], (0.52, 0.40, 0.14, 1), 0.38, metallic_base=0.85, dirt=0.45)
    mat_generic(MAT['src_Alu'], (0.72, 0.73, 0.74, 1), 0.42, metallic_base=1.0, dirt=0.3)
    mat_generic(MAT['src_LadderTread'], (0.018, 0.018, 0.019, 1), 0.9, dirt=0.35, plastic=True)
    mat_generic(MAT['src_KeyMetal'], (0.70, 0.70, 0.68, 1), 0.25, V='object', metallic_base=1.0, dirt=0.1)
    mat_generic(MAT['src_KeyFob'], (0.78, 0.10, 0.02, 1), 0.5, V='object', dirt=0.15, plastic=True)
