"""The generator container for the Forest map (Update 6): cont_kit's twin container with what the map needs, built in the
container frame (x east = the radiator louvre end, y north, z up; ground z = 0 under the pads, floor 0.31) and turned
onto Update 3's GenContainer by gcf_build:
  - the personnel door IX_ContSideDoor_85 in the north box's front (east) end wall: steel frame welded into the
    corrugation, a steel leaf with a pressed border, three barrel hinges, lever handles and a lock cylinder (the key
    "Generator"), the ZUTRITT VERBOTEN / NO ENTRY plate; opens out
  - the remote fuel fill point beside it: a welded box on the wall with a lid hinged at the top (IX_GenFillCap_300),
    the 2" fill neck and cap inside, the fill pipe through the wall, up, along the front and north walls on clamps and
    down into the day tank's top
  - the cargo doors without the padlock and the key on its hook (the map's key "Generator" is in the KPP's key box):
    a lock box (welded shroud) round the catch of the active leaf's inner bar instead
  - the feeder: an underground cable riser down the south wall instead of the overhead mast (the map has no line here)
  - no snow (the Forest has none); the funnel off the shelf (the prologue's funnel is the hut's, Item_Funnel)
Everything else is cont_kit's, unchanged."""
import math
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, quad, conduit, KBS, CONTRACT, LAMPS
from gen_kit import (Z_SLAB, Z_TIMBER, Z_STEELBLK, Z_GALV, Z_CHEQUER, Z_LINING, Z_FLOOR, Z_ROOFUNDER, Z_BRASSP, Z_STEELP)
import cont_kit as CK
from cont_kit import (XO, YO, ZB, ZT, FC, CI, XI, XR, XRI, XF, XF_BOX, CAST, RPW, FPW, REC, HDR_Z0, ROOF_Z, BOXES_Y, CR,
                      LEAF, XL_O, XL_C, BAR_X, HANDLE_Z, HANDLE_L, WIN, LOUV, INTAKES, PLY, JOIST_X, JOIST_W, ZJ, CZ,
                      LEAVES, PADS, STEP, MAST_X, SW_Y, G_EXT, corrugated, flat_wall, flat_h, sleeve, flange, Z_CPAINT_S,
                      Z_CPAINT_N, Z_CROOF, Z_CCAST, Z_CINPAINT, Z_UNDER)
import cont_tex as CT

uv = CT.uv
SD = dict(y0=0.40, y1=1.28, z0=FC, z1=2.33)                   # side door: rough opening in the north box's front wall
SD_LEAF = dict(y0=0.412, y1=1.268, z0=FC + 0.008, z1=2.322, xo=3.013, xi=2.968)
SD_PIV = Vector((3.016, 0.410, (FC + 2.33) / 2))              # hinge line: the leaf's outer face, its south edge
SD_HINGE_Z = (0.62, 1.40, 2.08)
FB = dict(y0=1.55, y1=1.90, z0=1.02, z1=1.37, x0=XO - 0.008, x1=XO + 0.142)    # fill box on the wall (outer crest plane)
FB_NECK = Vector((XO + 0.02, (FB['y0'] + FB['y1']) / 2, 1.17))
FILL_X = XI - 0.035                                             # the fill pipe on the inside of the front wall
FILL_Y = CK.YI - 0.045                                          # ... and along the north wall
FILL_Z = 2.20
TANK_IN = Vector((-0.35, 2.20, 2.01))                           # where it drops into the day tank's top (set by gcf_build)


def inner_box(k, lo, hi, zone, skip=()):
    """the inside faces of a box lo..hi (normals pointing in): a cavity seen from within"""
    lo, hi = Vector(lo), Vector(hi)
    c = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    for key, (q, n) in K.FACES6.items():
        if key in skip:
            continue
        face(k, [c[i] for i in q], zone, tuple(-a for a in n))


# ================================================================ the boxes (cont_kit.structure + the side door opening)
def structure():
    k = kb('GenContainer', 'Cont')
    for nm, (ya, yb) in BOXES_Y.items():
        zp = Z_CPAINT_S if nm == 'S' else Z_CPAINT_N
        so = -1 if nm == 'S' else 1
        yo = ya if nm == 'S' else yb
        yj = yb if nm == 'S' else ya
        js = '+y' if nm == 'S' else '-y'
        for x0, x1 in ((-XO, -XO + CAST[0]), (XO - CAST[0], XO)):
            for y0, y1 in ((ya, ya + CAST[1]), (yb - CAST[1], yb)):
                for z0, z1 in ((ZB, ZB + CAST[2]), (ZT - CAST[2], ZT)):
                    box6(k, (x0, y0, z0), (x1, y1, z1), Z_CCAST, skip=(js,) if yj in (y0, y1) else ())
        r0, r1 = sorted((yo - so * REC, yo - so * 0.09))
        box6(k, (XR, r0, ZB + 0.01), (XF, r1, FC), zp, skip=('-x', '+x'))
        box6(k, (XR, r0, ZT - 0.10), (XF, r1, ZT - REC), zp, skip=('-x', '+x'))
        for p0, p1 in ((ya, ya + FPW), (yb - FPW, yb)):
            box6(k, (XF, p0, ZB + CAST[2]), (XO, p1, ZT - CAST[2]), zp,
                 skip=('-z', '+z') + ((js,) if yj in (p0, p1) else ()))
        box6(k, (XO - 0.10, ya + FPW, ZB + 0.01), (XO - REC, yb - FPW, FC), zp, skip=('-y', '+y'))
        box6(k, (XO - 0.10, ya + FPW, ZT - 0.10), (XO - REC, yb - FPW, ZT - REC), zp, skip=('-y', '+y'))
        for p0, p1 in ((ya, ya + RPW), (yb - RPW, yb)):
            box6(k, (XR, p0, ZB + CAST[2]), (XRI, p1, ZT - CAST[2]), zp,
                 skip=('-z', '+z', '+x') + ((js,) if yj in (p0, p1) else ()))
        box6(k, (XR, ya + RPW, ZB + 0.01), (XRI, yb - RPW, FC), zp,
             skip=('-y', '+y') + (('+z',) if nm == 'N' else ()))
        box6(k, (XR, ya + RPW, HDR_Z0), (XRI, yb - RPW, ZT - REC), zp,
             skip=('-y', '+y', '+x') + (('-z',) if nm == 'N' else ()))
        holes = [(WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1'])] if nm == 'S' else []
        corrugated(k, 'y', yo - so * 0.008, so, CR['depth'], XRI, XF, FC, ZT - 0.10, CR['pitch'], CR['crest'],
                   CR['slope'], zp, phase=XRI + 0.03, holes=holes)
        holes = ([(LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1'])] if nm == 'S' else
                 [(SD['y0'], SD['y1'], SD['z0'], SD['z1'])])
        corrugated(k, 'x', XO - 0.008, 1, CR['depth'], ya + FPW, yb - FPW, FC, ZT - 0.10, CR['pitch'], CR['crest'],
                   CR['slope'], zp, phase=ya + FPW + 0.04, holes=holes)
        y0r, y1r = sorted((yo - so * 0.09, yj))
        flat_h(k, ROOF_Z, 1, XRI, XO - 0.10, y0r, y1r, Z_CROOF, step=1.0)
    box6(k, (XR, -0.09, ROOF_Z), (XO - 0.10, 0.09, 2.745), Z_GALV, skip=('-z',))
    flat_h(k, ZB + 0.03, -1, XR, XF, -YO + REC, YO - REC, Z_UNDER, step=1.5)
    for x, y, sx, sy in PADS:
        box6(k, (x - sx / 2, y - sy / 2, -0.10), (x + sx / 2, y + sy / 2, ZB - 0.001), Z_SLAB, skip=('-z',))
    x0, x1, y0, y1, h = STEP
    box6(k, (x0, y0, 0.0), (x1, y1, h - 0.006), Z_STEELBLK, skip=('-z',))
    box6(k, (x0 - 0.005, y0 - 0.005, h - 0.006), (x1 + 0.005, y1 + 0.005, h), Z_CHEQUER, skip=('-z',))
    # a second step at the side door (on the ground in front of the north box's front end)
    box6(k, (XO + 0.02, SD['y0'] - 0.05, 0.0), (XO + 0.36, SD['y1'] + 0.05, 0.154), Z_STEELBLK, skip=('-z',))
    box6(k, (XO + 0.015, SD['y0'] - 0.055, 0.154), (XO + 0.365, SD['y1'] + 0.055, 0.16), Z_CHEQUER, skip=('-z',))
    return k


def interior_shell():
    """cont_kit.interior_shell with the side door cut through the north box's front lining"""
    ki = kb('GenContainer_In', 'Cont')
    lz = lambda zm: Z_LINING
    flat_h(ki, FC, 1, XRI, XI, -CK.YI, CK.YI, Z_FLOOR, step=1.0)
    flat_h(ki, FC, 1, -XI, XRI, RPW, CK.YI, Z_FLOOR, step=1.0)
    flat_wall(ki, 'y', -CK.YI, 1, XRI + PLY, XI, FC, CI, lz, holes=[(WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1'])])
    flat_wall(ki, 'y', CK.YI, -1, XRI + PLY, XI, FC, CI, lz)
    yc = CAST[1] + 0.01
    flat_wall(ki, 'x', XI, -1, -CK.YI, -yc, FC, CI, lz, holes=[(LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1'])])
    flat_wall(ki, 'x', XI, -1, yc, CK.YI, FC, CI, lz, holes=[(SD['y0'], SD['y1'], SD['z0'], SD['z1'])])
    box6(ki, (XF_BOX, -yc, FC), (XI, yc, CI), Z_LINING, skip=('+x', '-z', '+z'))
    box6(ki, (XF_BOX, YO - yc, FC), (XI, CK.YI, CI), Z_LINING, skip=('+x', '+y', '-z', '+z'))
    box6(ki, (XF_BOX, -CK.YI, FC), (XI, -YO + yc, CI), Z_LINING, skip=('+x', '-y', '-z', '+z'))
    flat_wall(ki, 'x', -XI, 1, RPW + PLY, YO - RPW - PLY, FC, HDR_Z0, lz,
              holes=[(h['y0'], h['y1'], h['z0'], h['z1']) for h in INTAKES])
    yp = -YO + RPW
    box6(ki, (XRI, -CK.YI, FC), (XRI + PLY, yp, CI), Z_LINING, skip=('-x', '-y', '-z', '+z'))
    box6(ki, (XRI, -RPW, FC), (XRI + PLY, RPW, CI), Z_LINING, skip=('-x', '+y', '-z', '+z'))
    box6(ki, (XRI, yp, HDR_Z0), (XRI + PLY, -RPW, CI), Z_LINING, skip=('-x', '-y', '+y', '+z'))
    box6(ki, (-XI, RPW, FC), (XRI + PLY, RPW + PLY, CI), Z_LINING, skip=('-x', '-y', '-z', '+z'))
    box6(ki, (-XI, YO - RPW - PLY, FC), (XRI + PLY, CK.YI, CI), Z_LINING, skip=('-x', '+y', '-z', '+z'))
    box6(ki, (-XI, RPW + PLY, HDR_Z0), (XRI + PLY, YO - RPW - PLY, CI), Z_TIMBER, skip=('-x', '-y', '+y', '+z'))
    flat_h(ki, CI, -1, XRI + PLY, XI, -CK.YI, CK.YI, Z_ROOFUNDER, step=1.0)
    for xj in JOIST_X:
        box6(ki, (xj - JOIST_W / 2, -CK.YI, ZJ), (xj + JOIST_W / 2, CK.YI, CI), Z_TIMBER, skip=('-y', '+y', '+z'))
    for s in (-1, 1):
        ya, yb = (CK.YI - 0.05, CK.YI) if s > 0 else (-CK.YI, -CK.YI + 0.05)
        for xa, xb in zip(JOIST_X[:-1], JOIST_X[1:]):
            box6(ki, (xa + JOIST_W / 2, ya, ZJ), (xb - JOIST_W / 2, yb, CI), Z_TIMBER,
                 skip=('-x', '+x', '+z', '+y' if s > 0 else '-y'))
    return ki


# ================================================================ cargo doors (no padlock, no key on the hook: a lock box)
def doors():
    k = KBS['GenContainer']
    planks = {'Door_R': (-YO + RPW + 0.008, LEAVES['Door_R'][1] - 0.006), 'Door_L': (LEAVES['Door_L'][1] + 0.006, -RPW - 0.008)}
    for name, (yh, yf, piv, sg, bars) in LEAVES.items():
        D = kb(name, 'Cont')
        ya, yb = sorted((yh, yf))
        CK.leaf_mesh(D, ya, yb, Z_CPAINT_S, boards=planks[name] + (FC + 0.01, HDR_Z0 - 0.01))
        s = 1 if yf > yh else -1
        CK.leaf_hardware(D, yh, s, piv, bars, Z_CPAINT_S)
        for zc in CK.HINGE_Z:
            if name == 'Door_R':
                box6(k, (piv[0], piv[1] - 0.006, zc + 0.037), (XR - 0.005, piv[1] + 0.006, zc + 0.062), Z_CPAINT_S)
                box6(k, (-2.995, piv[1] + 0.006, zc + 0.037), (XR, -YO + 0.001, zc + 0.062), Z_CPAINT_S, skip=('+x', '+y'))
            else:
                box6(k, (piv[0], piv[1], zc + 0.037), (XR, piv[1] + 0.010, zc + 0.062), Z_CPAINT_S, skip=('+x',))
            k.cyl((piv[0], piv[1], zc - 0.04), (piv[0], piv[1], zc + 0.07), 0.006, Z_STEELBLK, 6)
        for i, yb_ in enumerate(bars):
            bn = f'{name}_Bar_{i + 1}'
            B = kb(bn, 'Cont')
            CK.bar_mesh(B, yb_)
            CK.keepers(k, yb_)
            part(bn, 'hinge', (BAR_X, yb_, HANDLE_Z), (0, 0, -1), (0, 90), parent=name, states=['locked', 'turned out'],
                 note='locking bar (modelled locked; on the map it goes with its leaf: the lock is the key "Generator")')
        pz = (LEAF['z0'] + LEAF['z1']) / 2
        part(name, 'hinge', (piv[0], piv[1], pz), (0, 0, sg), (0, 170 if name == 'Door_R' else 160), parent='GenContainer',
             states=['shut', 'open'],
             note=('active cargo leaf (south box, south hinge): unlocked with the key "Generator", swings out' if name == 'Door_R'
                   else 'passive cargo leaf (hinged at the joint): stops against the welded doors of the north box at 160'))
        yd = -1.42 if name == 'Door_R' else -1.02
        D.tube([Vector((CK.XB, yd, 0.95)), Vector((CK.XB + 0.045, yd, 0.95)), Vector((CK.XB + 0.045, yd, 1.17)),
                Vector((CK.XB, yd, 1.17))], 0.010, Z_STEELBLK, 6, caps=False)
        socket('Hand_' + name + '_In', (CK.XB + 0.05, yd, 1.06), 'hand', parent=name)
        socket('Hand_' + name + '_Out', (BAR_X - 0.04, bars[1] - HANDLE_L + 0.01, HANDLE_Z + 0.08), 'hand', parent=name)
    kR, kL = KBS['Door_R'], KBS['Door_L']
    # lock box: a welded steel shroud round the catch of Door_R_Bar_2 (the padlock sits inside it, out of reach of
    # bolt cutters); open at the bottom and on the handle's side
    ye = LEAVES['Door_R'][4][1] - HANDLE_L
    lb0, lb1 = Vector((-3.085, ye - 0.055, HANDLE_Z - 0.10)), Vector((XL_O, ye + 0.040, HANDLE_Z + 0.075))
    box6(kR, lb0, lb1, Z_GALV, skip=('+x', '-z', '+y'))
    box6(kR, (lb0.x + 0.004, lb0.y + 0.004, lb0.z), (XL_O, lb1.y, lb1.z - 0.004), Z_STEELBLK, skip=('+x', '-x', '-z', '+y'))
    socket('Lock_Door_R', ((lb0.x + lb1.x) / 2, (lb0.y + lb1.y) / 2, lb0.z + 0.03), 'item_slot', parent='Door_R',
           note='lock box on the active leaf: the key "Generator" unlocks here (the padlock is inside the shroud)')
    bb = Vector((CK.XB + 0.012, -1.235, 1.30))
    for y0 in (-1.33, -1.27):
        kR.box(CK.XB, CK.XB + 0.022, y0, y0 + 0.02, 1.283, 1.317, Z_STEELBLK)
    kL.box(CK.XB, CK.XB + 0.022, -1.20, -1.17, 1.283, 1.317, Z_STEELBLK)
    B = kb('Door_Bolt', 'Cont')
    B.cyl(bb - Vector((0, 0.12, 0)), bb, 0.0065, Z_STEELBLK, 6)
    B.cyl(bb - Vector((0, 0.07, 0)), bb - Vector((-0.03, 0.07, 0)), 0.006, Z_STEELBLK, 6)
    part('Door_Bolt', 'slide', bb, (0, 1, 0), (0, 0.06), unit='m', parent='Door_R', states=['drawn', 'shot'],
         note='barrel bolt on the planks inside the active leaf (modelled drawn; on the map it goes with the leaf)')
    for yh, yf, bars, holes in CK.STATIC_LEAVES:
        ya, yb = sorted((yh, yf))
        hs = [(h['y0'], h['y1'], h['z0'], h['z1']) for h in holes]
        CK.leaf_mesh(k, ya, yb, Z_CPAINT_N, hs, inner=False)
        s = 1 if yf > yh else -1
        piv = (-3.015, 2.455) if yh > 1 else (-3.015, 0.016)
        hz_ = tuple(z - 0.08 for z in CK.HINGE_Z) if yh < 1 else CK.HINGE_Z
        CK.leaf_hardware(k, yh, s, piv, bars, Z_CPAINT_N, hinge_z=hz_, hd=1)
        for zc in hz_:
            ya_, yb_ = sorted((piv[1] - 0.014 * s, piv[1] + 0.03 * s))
            box6(k, (-3.03, ya_, zc - 0.062), (XR, yb_, zc - 0.037), Z_CPAINT_N, skip=('+x',))
            k.cyl((piv[0], piv[1], zc - 0.07), (piv[0], piv[1], zc + 0.04), 0.006, Z_STEELBLK, 6)
        for yb_ in bars:
            CK.bar_mesh(k, yb_, hd=1)
            CK.keepers(k, yb_)
        for h in holes:
            CK.intake_louvre(k, h)


# ================================================================ the personnel door in the north box's front end
def side_door():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    y0, y1, z0, z1 = SD['y0'], SD['y1'], SD['z0'], SD['z1']
    xo = XO - 0.008                                                          # the corrugation's crest plane
    # frame: an angle frame welded into the corrugation (outside flange, the reveal through to the lining), a
    # chequer threshold over the front sill
    flange(k, 'x', xo, 1, y0, y1, z0, z1, 0.05, 0.006, Z_CPAINT_N, sides='tlr')
    sleeve(k, 'x', XI, xo, y0, y1, z0, z1, Z_CPAINT_N, bottom=False)
    box6(k, (XI - 0.02, y0, FC - 0.004), (xo + 0.004, y1, FC + 0.004), Z_CHEQUER, skip=('-z',))
    box6(ki, (XI - 0.012, y0 - 0.04, z0), (XI, y0, z1 + 0.04), Z_TIMBER, skip=('+x',))           # ply edge trims
    box6(ki, (XI - 0.012, y1, z0), (XI, y1 + 0.04, z1 + 0.04), Z_TIMBER, skip=('+x',))
    box6(ki, (XI - 0.012, y0, z1), (XI, y1, z1 + 0.04), Z_TIMBER, skip=('+x',))
    # the leaf: steel, a pressed border outside, a kick plate, three barrel hinges, lever handles both sides, the
    # lock cylinder outside
    L = SD_LEAF
    D = kb('IX_ContSideDoor_85', 'Cont')
    box6(D, (L['xi'], L['y0'], L['z0']), (L['xo'], L['y1'], L['z1']), {'+x': Z_CPAINT_N, '-x': Z_CINPAINT, '*': Z_CPAINT_N})
    bw = 0.055
    for lo, hi in (((L['xo'], L['y0'] + 0.03, L['z1'] - 0.03 - bw), (L['xo'] + 0.008, L['y1'] - 0.03, L['z1'] - 0.03)),
                   ((L['xo'], L['y0'] + 0.03, L['z0'] + 0.30), (L['xo'] + 0.008, L['y1'] - 0.03, L['z0'] + 0.30 + bw)),
                   ((L['xo'], L['y0'] + 0.03, L['z0'] + 0.30 + bw), (L['xo'] + 0.008, L['y0'] + 0.03 + bw, L['z1'] - 0.03 - bw)),
                   ((L['xo'], L['y1'] - 0.03 - bw, L['z0'] + 0.30 + bw), (L['xo'] + 0.008, L['y1'] - 0.03, L['z1'] - 0.03 - bw)),
                   ((L['xo'], L['y0'] + 0.03 + bw, 1.33), (L['xo'] + 0.008, L['y1'] - 0.03 - bw, 1.33 + 0.045))):
        box6(D, lo, hi, Z_CPAINT_N, skip=('-x',))
    box6(D, (L['xo'], L['y0'] + 0.02, L['z0'] + 0.02), (L['xo'] + 0.004, L['y1'] - 0.02, L['z0'] + 0.24), Z_GALV, skip=('-x',))
    for zc in SD_HINGE_Z:
        D.cyl(SD_PIV + Vector((0, 0, zc - SD_PIV.z - 0.05)), SD_PIV + Vector((0, 0, zc - SD_PIV.z + 0.05)), 0.012, Z_STEELBLK, 8)
        box6(D, (L['xo'], SD_PIV.y, zc - 0.04), (L['xo'] + 0.005, SD_PIV.y + 0.07, zc + 0.04), Z_STEELBLK, skip=('-x',))
        box6(k, (xo, SD_PIV.y - 0.06, zc - 0.04), (xo + 0.009, SD_PIV.y - 0.006, zc + 0.04), Z_STEELBLK, skip=('-x',))
    yh, zh = L['y1'] - 0.075, 1.05
    for xs, sgn in ((L['xo'], 1), (L['xi'], -1)):                          # escutcheons and levers (pointing at the hinges)
        xe = xs + sgn * 0.005
        box6(D, (min(xs, xe), yh - 0.022, zh - 0.13), (max(xs, xe), yh + 0.022, zh + 0.05), Z_GALV, skip=('-x' if sgn > 0 else '+x',))
        D.cyl(Vector((xe, yh, zh)), Vector((xe + sgn * 0.045, yh, zh)), 0.010, Z_GALV, 8)
        D.tube([Vector((xe + sgn * 0.045, yh, zh)), Vector((xe + sgn * 0.055, yh - 0.02, zh)),
                Vector((xe + sgn * 0.055, yh - 0.12, zh - 0.005))], 0.009, Z_GALV, 6)
    D.lathe(Vector((L['xo'] + 0.005, yh, zh - 0.085)), (1, 0, 0), [(0.0, 0.016), (0.008, 0.016), (0.010, 0.012)], Z_BRASSP, 10)
    socket('Hand_IX_ContSideDoor_85_Out', (L['xo'] + 0.06, yh - 0.10, zh), 'hand', parent='IX_ContSideDoor_85')
    socket('Hand_IX_ContSideDoor_85_In', (L['xi'] - 0.06, yh - 0.10, zh), 'hand', parent='IX_ContSideDoor_85')
    socket('Lock_IX_ContSideDoor_85', (L['xo'] + 0.012, yh, zh - 0.085), 'item_slot', parent='IX_ContSideDoor_85',
           note='lock cylinder: the key "Generator"')
    # ZUTRITT VERBOTEN / NO ENTRY plate (the cargo leaf's panel region)
    S = kb('IX_ContSideDoor_85_Sign', 'panel')
    yc_ = (L['y0'] + L['y1']) / 2
    box6(D, (L['xo'] + 0.008, yc_ - 0.125, 1.62 - 0.055), (L['xo'] + 0.011, yc_ + 0.125, 1.62 + 0.055), Z_STEELBLK, skip=('-x',))
    quad(S, (L['xo'] + 0.0125, yc_, 1.62), (1, 0, 0), 0.24, 0.10, uv('csign_noentry'))
    part('IX_ContSideDoor_85_Sign', 'static', (L['xo'] + 0.0125, yc_, 1.62), parent='IX_ContSideDoor_85',
         note='ZUTRITT VERBOTEN / NO ENTRY on the side door')
    part('IX_ContSideDoor_85', 'hinge', SD_PIV, (0, 0, -1), (0, 100), parent='GenContainer', states=['shut', 'open'],
         note='personnel door in the north box\'s front end (the far end from the cargo doors): steel leaf, hinged on its '
              'south edge, opens out to 100; locked with the key "Generator" like the cargo doors (Update 3: IX_ContSideDoor_85)')


# ================================================================ remote fuel fill point and the fill pipe
def filler():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    y0, y1, z0, z1, x0, x1 = FB['y0'], FB['y1'], FB['z0'], FB['z1'], FB['x0'], FB['x1']
    t = 0.004
    box6(k, (x0, y0, z0), (x1, y1, z1), Z_CPAINT_N, skip=('-x', '+x'))                       # the welded box, open front
    inner_box(k, (x0 + 0.002, y0 + t, z0 + t), (x1 - 0.003, y1 - t, z1 - t), Z_STEELBLK, skip=('+x',))   # its inside
    for lo, hi in (((x1 - 0.003, y0, z1 - t), (x1, y1, z1)), ((x1 - 0.003, y0, z0), (x1, y1, z0 + t)),
                   ((x1 - 0.003, y0, z0 + t), (x1, y0 + t, z1 - t)), ((x1 - 0.003, y1 - t, z0 + t), (x1, y1, z1 - t))):
        box6(k, lo, hi, Z_CPAINT_N, skip=('-x',))                                               # the rim
    # 2" fill neck with its cap (black), a chain to the cap, a drip tray lip
    n = FB_NECK
    k.lathe(Vector((x0 + 0.002, n.y, n.z)), (1, 0, 0), [(0.0, 0.030), (0.06, 0.030), (0.06, 0.036), (0.075, 0.036)], Z_GALV, 12,
            cap0=False, cap1=True)
    k.lathe(Vector((x0 + 0.077, n.y, n.z)), (1, 0, 0), [(0.0, 0.040), (0.03, 0.040), (0.034, 0.030)], Z_STEELBLK, 12, cap1=True)
    k.tube([Vector((x0 + 0.09, n.y + 0.035, n.z)), Vector((x0 + 0.06, n.y + 0.06, n.z - 0.06)),
            Vector((x0 + 0.01, n.y + 0.07, n.z - 0.03))], 0.003, Z_STEELBLK, 4, caps=False)
    # the lid: a plate over the front with a turned-down lip, hinged on its top edge, a hasp tab at the bottom
    Ld = kb('IX_GenFillCap_300', 'Cont')
    lo, hi = Vector((x1, y0 - 0.006, z0 - 0.012)), Vector((x1 + 0.006, y1 + 0.006, z1 + 0.006))
    box6(Ld, lo, hi, Z_CPAINT_N)
    box6(Ld, (x1 - 0.022, y0 - 0.006, z0 - 0.012), (x1, y1 + 0.006, z0 - 0.006), Z_CPAINT_N, skip=('+x',))      # lip
    box6(Ld, (x1 + 0.006, (y0 + y1) / 2 - 0.02, z0 + 0.005), (x1 + 0.014, (y0 + y1) / 2 + 0.02, z0 + 0.045), Z_GALV, skip=('-x',))
    piv = Vector((x1 + 0.003, (y0 + y1) / 2, z1 + 0.006))
    Ld.cyl(Vector((piv.x, y0 + 0.02, piv.z)), Vector((piv.x, y1 - 0.02, piv.z)), 0.008, Z_STEELBLK, 8)
    Sg = kb('IX_GenFillCap_300_Sign', 'panel')                        # the day tank's stencil plate on the lid
    quad(Sg, (x1 + 0.0066, (y0 + y1) / 2, 1.235), (1, 0, 0), 0.25, 0.10, uv('st_tank'))
    part('IX_GenFillCap_300_Sign', 'static', (x1 + 0.0066, (y0 + y1) / 2, 1.235), parent='IX_GenFillCap_300',
         note='DIESEL / DAY TANK 100 L on the fill box lid')
    part('IX_GenFillCap_300', 'hinge', piv, (0, -1, 0), (0, 110), parent='GenContainer', states=['shut', 'open'],
         note='lid of the fuel fill box on the north box\'s front end, hinged on its top edge: lift it (to 110) and the '
              '2" fill neck is there - the jerrycan goes in here; the pipe runs inside to the day tank (Update 3: '
              'IX_GenFillCap_300, the filler on the container wall)')
    socket('Pour_Fill', (x0 + 0.112, n.y, n.z), 'pour', parent='GenContainer', dir=(-1, 0, 0),
           note='fill neck (cap off): the jerrycan pours here, the fuel goes to the day tank (100 l)')
    socket('Hand_IX_GenFillCap_300', (x1 + 0.02, (y0 + y1) / 2, z0 + 0.03), 'hand', parent='IX_GenFillCap_300')
    # through the wall and inside: up the front wall's ply, along it to the corner, along the north wall, down into
    # the day tank's top (galvanised, clamps every ~0.6 m)
    zi = n.z
    pts = [Vector((XO - 0.02, n.y, zi)), Vector((FILL_X, n.y, zi)), Vector((FILL_X, n.y, FILL_Z)),
           Vector((FILL_X, FILL_Y, FILL_Z)), Vector((TANK_IN.x, FILL_Y, FILL_Z)), Vector((TANK_IN.x, FILL_Y, TANK_IN.z + 0.06)),
           Vector((TANK_IN.x, TANK_IN.y, TANK_IN.z + 0.03)), Vector((TANK_IN.x, TANK_IN.y, TANK_IN.z - 0.01))]
    conduit(ki, pts, r=0.021, zone=Z_GALV, clamps=0.6)
    ki.lathe(Vector((XI - 0.004, n.y, zi)), (-1, 0, 0), [(0.0, 0.045), (0.006, 0.045)], Z_GALV, 10)          # wall plate
    sign = kb('GenContainer_FillSign', 'panel')
    quad(sign, (XI - 0.003, n.y, 1.62), (-1, 0, 0), 0.20, 0.20, uv('csign_flame'))
    part('GenContainer_FillSign', 'static', (XI - 0.003, n.y, 1.62), parent='GenContainer',
         note='no naked flames, inside by the fill pipe')


# ================================================================ services (cont_kit's, the feeder underground)
def services():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    mx, yo = MAST_X, -YO - 0.04
    zl = 2.31
    ki.cyl(Vector((mx, -CK.YI + 0.02, zl)), Vector((mx, -CK.YI - 0.01, zl)), 0.02, Z_GALV, 8)
    k.cyl(Vector((mx, -YO + 0.03, zl)), Vector((mx, yo, zl)), 0.02, Z_GALV, 8)
    k.box(mx - 0.035, mx + 0.035, yo - 0.03, yo + 0.03, zl - 0.04, zl + 0.04, Z_GALV)
    # the riser: from the LB fitting down the south wall into the ground (the cables to the base and from the trafo)
    k.cyl(Vector((mx, yo, zl - 0.04)), Vector((mx, yo, 0.10)), 0.024, Z_GALV, 8)
    k.cyl(Vector((mx, yo, 0.22)), Vector((mx, yo, -0.12)), 0.034, Z_STEELBLK, 8)
    for zc in (0.55, 1.30, 2.05):
        k.box(mx - 0.02, mx + 0.02, -YO - 0.07, -YO + 0.008, zc - 0.01, zc + 0.01, Z_GALV)
    socket('Line_In', (mx, yo, 0.0), 'item_slot', parent='GenContainer', dir=(0, 0, -1),
           note='LINE (grid) cable: underground from the trafo; feeds the board via Board_Brk_Line')
    socket('Feed_Out', (mx, yo - 0.01, 0.0), 'item_slot', parent='GenContainer', dir=(0, 0, -1),
           note='feeder to the base: the eight circuits go underground from here')
    yi = -CK.YI + 0.025
    conduit(ki, [Vector((mx, yi, 2.21)), Vector((mx, yi, zl)), Vector((mx, -CK.YI - 0.005, zl))], r=0.02)
    conduit(ki, [Vector((-1.45, yi, 2.21)), Vector((-1.45, yi, 2.37))])
    lg, lc = CK.LAMP_C['Bulk_Genset'], CK.LAMP_C['Bulk_Ceiling']
    conduit(ki, [Vector((-1.62, yi, 2.21)), Vector((-1.62, yi, CZ)), Vector((lg.x, yi, CZ)), Vector((lg.x, lg.y - 0.05, CZ))])
    across = [Vector((lg.x, lg.y + 0.05, CZ)), Vector((lg.x, 0.40, CZ)), Vector((lc.x, 0.40, CZ)), Vector((lc.x, lc.y - 0.05, CZ))]
    conduit(ki, across, clamps=99.0)
    for p_ in ([Vector((lg.x, yy, CZ)) for yy in (-0.55, -0.05)] + [Vector((JOIST_X[3], 0.40, CZ))] +
               [Vector((lc.x, yy, CZ)) for yy in (0.72,)]):
        d_ = Vector((1, 0, 0)) if abs(p_.y - 0.40) < 1e-6 else Vector((0, 1, 0))
        ki.box_m(p_, (0.026, 0.028, 0.026) if d_.x else (0.028, 0.026, 0.026), Z_GALV)
    xh, xw, hz = XRI + PLY + 0.025, -XI + 0.025, 2.62
    conduit(ki, [Vector((-1.78, yi, 2.21)), Vector((-1.78, yi, CZ)), Vector((xh, yi, CZ)), Vector((xh, yi, hz)), Vector((xh, SW_Y, hz)),
                 Vector((xh, SW_Y, 2.555)), Vector((xw, SW_Y, 2.555)), Vector((xw, SW_Y, 1.655))])
    conduit(ki, [Vector((xw, SW_Y, 1.565)), Vector((xw, SW_Y, 0.72))])
    ki.box(xh - 0.03, xh + 0.03, -1.25, -1.19, hz - 0.03, hz + 0.03, Z_GALV)
    conduit(ki, [Vector((xh, -1.22, hz)), Vector((XR - 0.01, -1.22, hz))])
    sw = Vector((-XI, SW_Y, 1.61))
    box6(ki, (-XI, SW_Y - 0.04, 1.565), (-XI + 0.045, SW_Y + 0.04, 1.655), Z_GALV, skip=('-x',))
    S = kb('Light_Switch', 'Cont')
    sp = sw + Vector((0.045, 0, 0))
    S.cyl(sp, sp + Vector((0.025, 0, -0.012)), 0.005, Z_STEELBLK, 6, r2=0.0035)
    part('Light_Switch', 'hinge', sp, (0, -1, 0), (0, 50), parent='GenContainer', states=['off (down)', 'on (up)'],
         note='container lights switch (static on the map: the lamps follow the power grid)')
    box6(ki, (-XI, SW_Y - 0.045, 0.60), (-XI + 0.05, SW_Y + 0.045, 0.72), Z_GALV, skip=('-x',))
    socket('Outlet_Wall', (-XI + 0.052, SW_Y, 0.66), 'item_slot', parent='GenContainer', dir=(1, 0, 0),
           note='230 V outlet on the CONTAINER circuit')
    box6(ki, (0.35, -CK.YI + 0.06, FC), (0.59, -1.385, FC + 0.006), Z_CHEQUER, skip=('-z',))
    box6(ki, (-1.57, -CK.YI + 0.06, FC), (0.35, -CK.YI + 0.30, FC + 0.006), Z_CHEQUER, skip=('-z', '+x'))
    conduit(ki, [Vector((-1.45, -CK.YI + 0.04, FC + 0.006)), Vector((-1.45, -CK.YI + 0.04, 1.11))], r=0.022, clamps=0.35)
    ey = G_EXT.y - 1.30
    ki.box(-XI, -XI + 0.012, ey - 0.03, ey + 0.03, 1.16, 1.46, Z_STEELBLK)
    ki.box(-XI, -XI + 0.10, ey - 0.06, ey + 0.06, 0.90, 0.91, Z_STEELBLK)


def play_points():
    """cont_kit's points without the snow; the side door and the fill point added"""
    for name, kind, pos, d, note in (
            ('Audio_Exhaust', 'audio', (CK.STACK_X, CK.EXH_Y, CK.STACK_TOP), None, 'exhaust beat at the stack, the flap rattling'),
            ('Audio_Louvre', 'audio', (XI, -1.015, 1.16), None, 'louvre blades rattling in the wind / in the fan blast'),
            ('Audio_Door', 'audio', (XR, -1.22, 1.30), None, 'cargo doors: the bars and cams, hinges groaning, wind'),
            ('Audio_SideDoor', 'audio', (XO, (SD['y0'] + SD['y1']) / 2, 1.20), None, 'side door: the latch, the hinges'),
            ('Audio_Roof', 'audio', (0.0, 0.0, 3.0), None, 'steel roof: ticks and booms in the cold, needles and cones '
                                                           'dropping, footsteps up there'),
            ('Audio_Wind', 'audio', (-2.95, 1.22, 2.22), None, 'wind through the two intake louvres in the north box\'s doors'),
            ('VFX_Exhaust', 'vfx', (CK.STACK_X, CK.EXH_Y, CK.STACK_TOP + 0.03), (0, 0, 1),
             'exhaust: a black puff on starting, grey smoke under load, thin haze idling'),
            ('VFX_LouvreHeat', 'vfx', (XO + 0.05, -1.015, 1.16), (1, 0, 0),
             'warm air from the radiator through the open louvre: steam in the cold night air'),
            ('VFX_FillSpill', 'vfx', (FB['x0'] + 0.11, FB_NECK.y, FB_NECK.z - 0.05), (0, 0, -1),
             'diesel spilling at the fill neck (poured without the funnel)'),
            ('Heat_Louvre', 'heat', (XO + 0.20, -1.015, 1.16), None, 'warm spot outside the louvre while the set runs')):
        socket(name, pos, kind, note=note, parent='GenContainer')
        if d is not None:
            CONTRACT['sockets'][name]['dir'] = list(d)
    s2 = 1 / math.sqrt(2)
    for name, pose, hip, eye, facing, note in (
            ('Hide_UnderWindow', 'crouch', (-0.10, -2.035, FC + 0.30), (-0.10, -1.975, FC + 0.86), (0, 1, 0),
             'crouched under the window: not seen from outside through the glass'),
            ('Hide_ShelfCorner', 'crouch', (-2.55, 2.00, FC + 0.30), (-2.50, 1.95, FC + 0.86), (s2, -s2, 0),
             'crouched in the north-west corner behind the shelf: not seen from the cargo doors')):
        socket(name, hip, 'hide', note=note, parent='GenContainer')
        CONTRACT['sockets'][name].update(pose=pose, eye=K.r4(eye), facing=list(facing))


def knock_rays():
    R = CK.knock_rays()
    return [r for r in R if r[0] != 'Knock_WallE_2'] + [('Knock_SideDoor', (3.9, 0.84, 1.30), (-1, 0, 0))]


def build_container():
    structure()
    interior_shell()
    doors()
    CK.window()
    CK.louvres()
    services()
    CK.lamps()
    CK.signs()
    side_door()
    filler()
    play_points()
    part('GenContainer', 'static', (0, 0, 0), parent=None,
         note='the twin container (castings, posts, rails, corrugated walls, roofs, the welded doors of the north box, pads, '
              'steps, the feeder riser, the stack, the fill box); prefab root')
    part('GenContainer_In', 'static', (0, 0, FC), parent='GenContainer',
         note='inside of the container, finished as the generator shed: ply lining, concrete floor, spruce joists and '
              'blocking under the roof\'s underside, chequer covers, the window, conduits, the fill pipe, lamps')
