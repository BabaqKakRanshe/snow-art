"""Van v3, phase 1b: what the player takes in hand and what the horror needs.
  repair kit: tool box (spanner, plug spanner, screwdriver, pliers, spare fan belt, tin of spare fuses), bottle jack
  and wheel brace, oil and antifreeze cans, shovel, tow strap, starting crank through the bumper (flap, guide,
  ratchet on the crankshaft);
  light: inspection lamp on a cord with a 12 V socket on the dash, eight dash toggles as moving parts wired to the
  lamps and fuses, fog lamps in the bumper;
  horror: rear-view mirror with a render-texture glass and its camera socket, lock buttons on every door, curtains
  that close (stretch along the rod);
  snow: sand ladders and the winch drum / hook as their own parts;
  driving: wipers, heater controls (temperature, fan, air to the windscreen), frost mask UVs on the windscreen,
  seats with hip / eye / exit points.
Body frame (before the 9 cm lift): x forward, y left, z up, metres."""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import van2_kit as VK
from van2_kit import KB, up_axes, rrect, fillet
import van3_mech as VM
from van3_mech import part, socket, rbox, frame_R, CONTRACT, set_pivot

# new zones of the Mech atlas
Z_TOOLRED, Z_CRVAN, Z_HANDLE, Z_WOOD2, Z_ROPE, Z_OILCAN, Z_TOSOL, Z_LABEL, Z_CAGE = range(76, 85)
EXTRA_ZONES = list(range(76, 85))
Z = VM                                                    # the phase-1 zones (Z.Z_STEEL2 ...)
Z_BLACK, Z_RUBBER, Z_CHROME, Z_PAINT = VK.Z_BLACK, VK.Z_RUBBER, VK.Z_CHROME, VK.Z_PAINT
TOGGLES = ['Toggle_Head', 'Toggle_Fog', 'Toggle_Spot', 'Toggle_Roof', 'Toggle_Work', 'Toggle_Cabin', 'Toggle_Stove',
           'Toggle_Wiper']


def place(dst, M4, build):
    """build(kb) in a local frame, move it by M4 (a proper rotation + translation) and merge it into dst"""
    loc = KB()
    build(loc)
    bm = loc.bm
    bmesh.ops.transform(bm, matrix=M4, verts=list(bm.verts))
    zl = bm.faces.layers.float.get('zone')
    vmap = {v: dst.bm.verts.new(v.co) for v in bm.verts}
    for f in bm.faces:
        dst._f([vmap[v] for v in f.verts], f[zl])
    bm.free()


def ring_strip(kb, c, axis, r, w, h, zone, seg=24):
    """closed band of rectangular section (w across the ring plane, h along the axis) round axis through c"""
    ax = Vector(axis).normalized()
    e1 = (Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0)))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    pts = [Vector(c) + (e1 * math.cos(2 * math.pi * k / seg) + e2 * math.sin(2 * math.pi * k / seg)) * r for k in range(seg)]
    kb.strip(pts + [pts[0]], ax, w, h, zone, caps=False)


# ================================================================ repair kit
TB = dict(x0=0.42, x1=0.84, y0=-0.89, y1=-0.65, z0=0.716, z1=0.876)        # tool box under the folding seat R2


def toolbox(kbs):
    b = TB
    t = 0.008
    c = Vector(((b['x0'] + b['x1']) / 2, (b['y0'] + b['y1']) / 2, 0))
    u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
    w, h = b['x1'] - b['x0'], b['y1'] - b['y0']
    R = lambda z, d, r: rrect(c + Vector((0, 0, z)), u, v, w - d, h - d, r)
    zt = b['z1'] - 0.012
    B = kbs('ToolBox')
    B.loft([R(b['z0'], 0, 0.012), R(zt, 0, 0.012), R(zt, 2 * t, 0.008)], [Z_TOOLRED, Z_TOOLRED], cap0=Z_TOOLRED)
    B.loft([list(reversed(R(b['z0'] + t, 2 * t, 0.008))), list(reversed(R(zt, 2 * t, 0.008)))], [Z_TOOLRED])
    B.poly(R(b['z0'] + t, 2 * t, 0.008), Z_TOOLRED)
    for s in (-1, 1):                                                        # latches on the aisle face
        B.box(c.x + s * 0.13 - 0.012, c.x + s * 0.13 + 0.012, b['y1'], b['y1'] + 0.004, zt - 0.03, zt + 0.004, Z.Z_STEEL2)
    part('ToolBox', 'item', (c.x, c.y, b['z0']), (0, 0, 1), states=['closed', 'open'],
         note='steel tool box under the folding seat R2; carried by the handle on the lid (close it first)')
    L = kbs('ToolBox_Lid')
    L.loft([R(zt - 0.004, -0.004, 0.014), R(b['z1'], -0.004, 0.014), R(b['z1'] + 0.004, 0.02, 0.010)],
           [Z_TOOLRED, Z_TOOLRED], cap0=Z_TOOLRED, cap1=Z_TOOLRED)
    zh = b['z1'] + 0.004
    L.tube([(c.x - 0.07, c.y, zh), (c.x - 0.06, c.y, zh + 0.032), (c.x + 0.06, c.y, zh + 0.032), (c.x + 0.07, c.y, zh)],
           0.006, Z.Z_KNOB, 6)
    for s in (-1, 1):
        L.box(c.x + s * 0.07 - 0.01, c.x + s * 0.07 + 0.01, c.y - 0.01, c.y + 0.01, zh - 0.001, zh + 0.004, Z.Z_STEEL2)
    piv = Vector((c.x, b['y0'] - 0.002, zt))
    part('ToolBox_Lid', 'hinge', piv, (1, 0, 0), (0, 88), parent='ToolBox', note='hinged at the wall, the aisle edge lifts')
    socket('Hand_ToolBox', (c.x, c.y, zh + 0.03), 'hand', parent='ToolBox_Lid', note='carry handle')
    zf = b['z0'] + t                                                          # inner floor
    # combination spanner 13 / 17
    W = kbs('Tool_Wrench')
    y, z = -0.862, zf + 0.003
    W.box(0.465, 0.615, y - 0.007, y + 0.007, z - 0.002, z + 0.002, Z_CRVAN)
    W.cyl((0.625, y, z - 0.003), (0.625, y, z + 0.003), 0.013, Z_CRVAN, 12)
    W.box(0.432, 0.466, y - 0.016, y - 0.008, z - 0.002, z + 0.002, Z_CRVAN)
    W.box(0.432, 0.466, y + 0.008, y + 0.016, z - 0.002, z + 0.002, Z_CRVAN)
    W.box(0.458, 0.472, y - 0.016, y + 0.016, z - 0.002, z + 0.002, Z_CRVAN)
    part('Tool_Wrench', 'item', (0.54, y, z), (1, 0, 0), parent='ToolBox',
         note='spanner 13 / 17: battery clamp bolts, belt tension, fittings')
    socket('Hand_Wrench', (0.54, y, z + 0.006), 'hand', parent='Tool_Wrench')
    # plug spanner: tube with a hex end and a tommy bar
    Ps = kbs('Tool_PlugSpanner')
    y, z = -0.825, zf + 0.011
    Ps.cyl((0.47, y, z), (0.585, y, z), 0.011, Z_CRVAN, 8)
    Ps.cyl((0.44, y, z), (0.47, y, z), 0.0125, Z_CRVAN, 6)
    Ps.cyl((0.575, y - 0.026, z), (0.575, y + 0.026, z), 0.004, Z_CRVAN, 6)
    part('Tool_PlugSpanner', 'item', (0.52, y, z), (1, 0, 0), parent='ToolBox',
         note='spark plug spanner: fits Engine_Plug_N (take the lead off first)')
    socket('Hand_PlugSpanner', (0.575, y, z + 0.01), 'hand', parent='Tool_PlugSpanner')
    # screwdriver
    Sd = kbs('Tool_Screwdriver')
    y, z = -0.778, zf + 0.012
    Sd.cyl((0.53, y, z), (0.63, y, z), 0.012, Z_HANDLE, 6)
    Sd.cyl((0.44, y, z), (0.53, y, z), 0.003, Z_CRVAN, 6)
    part('Tool_Screwdriver', 'item', (0.58, y, z), (1, 0, 0), parent='ToolBox', note='flat screwdriver: clamps, fuse box lid')
    socket('Hand_Screwdriver', (0.58, y, z + 0.012), 'hand', parent='Tool_Screwdriver')
    # pliers
    Pl = kbs('Tool_Pliers')
    y, z = -0.72, zf + 0.004
    for s in (-1, 1):
        Pl.strip([(0.49, y, z), (0.612, y + s * 0.02, z)], (0, 0, 1), 0.011, 0.007, Z_HANDLE)
    Pl.strip([(0.44, y, z), (0.495, y, z)], (0, 0, 1), 0.013, 0.008, Z_CRVAN)
    Pl.cyl((0.49, y, z - 0.004), (0.49, y, z + 0.005), 0.008, Z_CRVAN, 8)
    part('Tool_Pliers', 'item', (0.52, y, z), (1, 0, 0), parent='ToolBox', note='pliers')
    socket('Hand_Pliers', (0.57, y, z + 0.006), 'hand', parent='Tool_Pliers')
    # spare fan belt and a tin of spare fuses
    Bt = kbs('Spare_Belt')
    ring_strip(Bt, (0.74, -0.80, zf + 0.004), (0, 0, 1), 0.058, 0.012, 0.008, Z.Z_HOSE)
    part('Spare_Belt', 'item', (0.74, -0.80, zf + 0.004), (0, 0, 1), parent='ToolBox',
         note='fan belt: fit over the three pulleys to set Engine_Belt broken / loose -> ok')
    socket('Hand_Spare_Belt', (0.74, -0.742, zf + 0.008), 'hand', parent='Spare_Belt')
    Ft = kbs('FuseTin')
    fc = Vector((0.74, -0.70, zf))
    Ft.lathe(fc, (0, 0, 1), [(0.0, 0.030), (0.018, 0.030), (0.018, 0.027), (0.003, 0.027)], Z.Z_STEEL2, 12)
    part('FuseTin', 'item', fc, (0, 0, 1), parent='ToolBox', note='tin with three spare fuses')
    for k, dy in enumerate((-0.012, 0.0, 0.012)):
        fk = kbs(f'Spare_Fuse_{k + 1}')
        p = fc + Vector((0, dy, 0.0075))
        a_, b_ = p - Vector((0.014, 0, 0)), p + Vector((0.014, 0, 0))
        fk.cyl(a_, b_, 0.0042, Z.Z_CERAMIC, 6)
        fk.cyl(a_, a_ + Vector((0.005, 0, 0)), 0.0048, Z.Z_STEEL2, 6)
        fk.cyl(b_ - Vector((0.005, 0, 0)), b_, 0.0048, Z.Z_STEEL2, 6)
        part(f'Spare_Fuse_{k + 1}', 'item', p, (1, 0, 0), parent='FuseTin', states=['ok'],
             note='fits any Fuse_N slot of the fuse box')
    socket('Hand_FuseTin', fc + Vector((0, 0, 0.02)), 'hand', parent='FuseTin')


def jack_and_cans(kbs):
    """under the folding seats L2 / L3 on the left wall (the rear wheel arches fill x -1.55..-0.90): bottle jack,
    a 5 l can of engine oil, a 5 l jug of antifreeze, the wheel brace in front of them"""
    c = Vector((-0.80, 0.80, 0.716))
    J = kbs('Jack')
    J.box(c.x - 0.055, c.x + 0.055, c.y - 0.045, c.y + 0.045, c.z, c.z + 0.012, Z_TOOLRED)
    J.cyl(c + Vector((0, 0, 0.012)), c + Vector((0, 0, 0.17)), 0.036, Z_TOOLRED, 12)
    J.cyl(c + Vector((0.034, 0, 0.03)), c + Vector((0.07, 0, 0.03)), 0.009, Z.Z_STEEL2, 6)
    J.cyl(c + Vector((0, 0, 0.17)), c + Vector((0, 0, 0.18)), 0.028, Z.Z_STEEL2, 12)
    part('Jack', 'item', c, (0, 0, 1), note='bottle jack: stand it under the axle; the wheel brace is the pump lever')
    socket('Hand_Jack', c + Vector((0, -0.04, 0.12)), 'hand', parent='Jack')
    socket('Jack_PumpSocket', c + Vector((0.07, 0, 0.03)), 'item_slot', parent='Jack', note='WheelBrace goes in here')
    Rm = kbs('Jack_Ram')
    Rm.cyl(c + Vector((0, 0, 0.05)), c + Vector((0, 0, 0.215)), 0.022, Z_CRVAN, 10)       # long enough to stay in the body at 12 cm
    part('Jack_Ram', 'slide', c + Vector((0, 0, 0.165)), (0, 0, 1), (0, 0.12), unit='m', parent='Jack',
         note='ram: rises 12 cm while pumping (WheelBrace in Jack_PumpSocket)')
    Sw = kbs('Jack_Screw')                            # extension screw in the ram top, like a real bottle jack
    Sw.cyl(c + Vector((0, 0, 0.105)), c + Vector((0, 0, 0.235)), 0.016, Z.Z_STEEL2, 8)  # stays in the ram at 10 cm
    Sw.cyl(c + Vector((0, 0, 0.235)), c + Vector((0, 0, 0.242)), 0.020, Z.Z_STEEL2, 8)
    part('Jack_Screw', 'slide', c + Vector((0, 0, 0.235)), (0, 0, 1), (0, 0.10), unit='m', parent='Jack_Ram',
         note='extension screw in the ram top: turn it out by hand (up to 10 cm), then pump - the ram closes the last '
              '3-6 cm to the axle and lifts the wheel 6-8 cm; closed 0.242 m + screw 0.10 + ram 0.12 = 0.46 m')
    socket('Hand_Jack_Screw', c + Vector((0, 0, 0.242)), 'hand', parent='Jack_Screw')
    Bw = kbs('WheelBrace')
    y, z = 0.62, 0.716 + 0.017
    Bw.cyl((-0.865, y, z), (-0.805, y, z), 0.017, Z_CRVAN, 6)
    Bw.tube([(-0.81, y, z), (-0.47, y, z), (-0.452, y - 0.018, z), (-0.45, y - 0.11, z)], 0.008, Z_CRVAN, 6)
    part('WheelBrace', 'item', (-0.66, y, z), (1, 0, 0),
         note='wheel brace: the wheel nuts (the spare is held by a wing nut, by hand); the jack pump lever')
    socket('Hand_WheelBrace', (-0.45, y - 0.09, z), 'hand', parent='WheelBrace')
    O = kbs('OilCan')
    oc = Vector((-0.62, 0.825, 0.716))
    rbox(O, oc + Vector((0, 0, 0.115)), (0.17, 0.11, 0.23), Z_OILCAN, r=0.008, ch=0.005)
    O.cyl(oc + Vector((0.05, 0, 0.23)), oc + Vector((0.05, 0, 0.252)), 0.016, Z.Z_STEEL2, 8)
    O.cyl(oc + Vector((0.05, 0, 0.252)), oc + Vector((0.05, 0, 0.262)), 0.019, Z.Z_REDPLAST, 8)
    O.tube([oc + Vector((-0.06, 0, 0.23)), oc + Vector((-0.05, 0, 0.26)), oc + Vector((0.0, 0, 0.26)), oc + Vector((0.01, 0, 0.23))],
           0.005, Z.Z_STEEL2, 6)
    part('OilCan', 'item', oc, (0, 0, 1), states=['oil 0..5 l'], note='engine oil: pour into Pour_Oil on the valve cover')
    socket('Pour_OilCan', oc + Vector((0.05, 0, 0.262)), 'pour', parent='OilCan')
    socket('Hand_OilCan', oc + Vector((-0.025, 0, 0.262)), 'hand', parent='OilCan')
    A = kbs('AntifreezeCan')
    ac = Vector((-0.43, 0.82, 0.716))
    rbox(A, ac + Vector((0, 0, 0.105)), (0.15, 0.12, 0.21), Z_TOSOL, r=0.02, ch=0.01)
    A.tube([ac + Vector((-0.06, 0, 0.205)), ac + Vector((-0.05, 0, 0.25)), ac + Vector((0.0, 0, 0.25)), ac + Vector((0.01, 0, 0.205))],
           0.011, Z_TOSOL, 6)
    A.cyl(ac + Vector((0.045, 0, 0.21)), ac + Vector((0.045, 0, 0.235)), 0.017, Z_TOSOL, 8)
    A.cyl(ac + Vector((0.045, 0, 0.235)), ac + Vector((0.045, 0, 0.247)), 0.02, Z.Z_REDPLAST, 8)
    part('AntifreezeCan', 'item', ac, (0, 0, 1), states=['antifreeze 0..5 l'],
         note='antifreeze: pour into Pour_Coolant (bottle) or Pour_Radiator (hatch above the grille)')
    socket('Pour_AntifreezeCan', ac + Vector((0.045, 0, 0.247)), 'pour', parent='AntifreezeCan')
    socket('Hand_AntifreezeCan', ac + Vector((-0.025, 0, 0.25)), 'hand', parent='AntifreezeCan')


def shovel(kbs, zb=2.20):
    """short spade lying across the rear-left quarter of the roof rack, on two cross tubes"""
    def build(kb):
        kb.slab(lambda s, t: Vector((0.27 * t, 0.12 * s, 0.0015 + 0.012 * s * s)),
                lambda s, t: Vector((0, -0.2 * s, 1)).normalized(), np.linspace(-1, 1, 5), np.linspace(0, 1, 4), 0.003,
                Z.Z_STEEL2)
        kb.cyl((0.25, 0, 0.016), (0.33, 0, 0.016), 0.022, Z.Z_STEEL2, 8, r2=0.018)
        kb.cyl((0.32, 0, 0.016), (0.78, 0, 0.016), 0.016, Z_WOOD2, 8)
        kb.tube([(0.77, 0, 0.016), (0.79, -0.055, 0.016), (0.87, -0.055, 0.016), (0.87, 0.055, 0.016),
                 (0.79, 0.055, 0.016), (0.77, 0, 0.016)], 0.009, Z_WOOD2, 6)
    tip = Vector((-1.62, 0.70, zb + 0.012))
    d = Vector((0.64, -0.60, 0)).normalized()
    side = Vector((0, 0, 1)).cross(d)
    R = Matrix((d, side, Vector((0, 0, 1)))).transposed()
    M4 = Matrix.Translation(tip) @ R.to_4x4()
    S = kbs('Shovel')
    place(S, M4, build)
    mid = tip + d * 0.55 + Vector((0, 0, 0.016))
    part('Shovel', 'item', mid, d, parent='Kit_RoofRack',
         note='spade on the roof rack (left rear): dig the wheels out, clear the snow off the hatch')
    socket('Hand_Shovel_Grip', tip + d * 0.83 + Vector((0, 0, 0.016)), 'hand', parent='Shovel')
    socket('Hand_Shovel_Shaft', mid, 'hand', parent='Shovel')


def tow_rope(kbs, Hk):
    """orange tow strap, coiled, hanging on a wall hook above the cargo in the rear right corner"""
    c = Vector((-1.78, -0.875, 1.58))
    T = kbs('TowRope')
    T.lathe(c, (0, 1, 0), [(-0.022, 0.075), (-0.022, 0.13), (0.022, 0.13), (0.022, 0.075), (-0.022, 0.075)], Z_ROPE, 20,
            cap0=False, cap1=False)
    T.strip([c + Vector((0.05, 0, -0.12)), c + Vector((0.07, 0.004, -0.20)), c + Vector((0.075, 0.006, -0.27))],
            (0, 1, 0), 0.045, 0.004, Z_ROPE)
    end = c + Vector((0.075, 0.006, -0.29))
    T.tube([end + Vector((-0.015, 0, 0.02)), end + Vector((-0.02, 0, -0.01)), end + Vector((0, 0, -0.03)),
            end + Vector((0.02, 0, -0.01)), end + Vector((0.015, 0, 0.02))], 0.006, Z.Z_STEEL2, 6)
    part('TowRope', 'item', c, (0, 1, 0), note='tow strap 5 m with two shackles: Tow_Hook_FL / FR on the bumper, Tow_Rear')
    socket('Hand_TowRope', c + Vector((0, 0.03, 0.13)), 'hand', parent='TowRope')
    Hk.tube([(-1.78, -0.899, 1.73), (-1.78, -0.86, 1.73), (-1.78, -0.845, 1.745), (-1.78, -0.845, 1.76)], 0.006, Z.Z_STEEL2, 6)
    socket('Tow_Hook_FL', (2.395, 0.72, 0.455), 'item_slot', note='red tow hook, front left')
    socket('Tow_Hook_FR', (2.395, -0.72, 0.455), 'item_slot', note='red tow hook, front right')
    socket('Tow_Rear', (-2.27, 0.0, 0.58), 'item_slot', note='rear bumper towing eye')


# ---------------------------------------------------------------- starting crank (through the bumper, under the radiator)
CRANK_Z = 0.52                     # crankshaft axis (crank pulley at x 1.43..1.452)
CRANK_TIP = Vector((1.474, 0.0, CRANK_Z))
CRANK_STOW_TIP = Vector((0.858, 0.55, 1.30))            # on clips on the partition, rod along -y


def _crank_geom(kb):
    """the handle in its working position: tip pin at the ratchet, rod forward through the bumper, arm down, grip"""
    t = CRANK_TIP
    kb.cyl(t + Vector((0, -0.018, 0)), t + Vector((0, 0.018, 0)), 0.0035, Z_CRVAN, 6)
    kb.cyl(t - Vector((0.006, 0, 0)), Vector((2.49, 0, CRANK_Z)), 0.011, Z.Z_STEEL2, 8)
    kb.tube([Vector((2.49, 0, CRANK_Z)), Vector((2.51, 0, CRANK_Z - 0.01)), Vector((2.52, 0, CRANK_Z - 0.03)),
             Vector((2.52, 0, CRANK_Z - 0.16)), Vector((2.53, 0, CRANK_Z - 0.175)), Vector((2.55, 0, CRANK_Z - 0.18))],
            0.011, Z.Z_STEEL2, 8)
    kb.cyl(Vector((2.55, 0, CRANK_Z - 0.18)), Vector((2.68, 0, CRANK_Z - 0.18)), 0.017, Z_WOOD2, 8)
    kb.cyl(Vector((2.68, 0, CRANK_Z - 0.18)), Vector((2.69, 0, CRANK_Z - 0.18)), 0.020, Z.Z_STEEL2, 8)


def crank_stow_matrix():
    """working position -> stowed on the saloon side of the partition (rod along -y, arm down)"""
    return Matrix.Translation(CRANK_STOW_TIP) @ Matrix.Rotation(math.radians(-90), 4, 'Z') @ Matrix.Translation(-CRANK_TIP)


def crank(kbs, engine_kb, guide_kb):
    C = kbs('CrankHandle')
    place(C, crank_stow_matrix(), _crank_geom)
    for yc in (0.40, -0.30):                                        # clips on the partition
        guide_kb.box(0.838, 0.888, yc - 0.012, yc + 0.012, 1.280, 1.288, Z.Z_STEEL2)   # shelf under the rod
        guide_kb.box(0.838, 0.844, yc - 0.012, yc + 0.012, 1.288, 1.312, Z.Z_STEEL2)   # lip in front of it
    part('CrankHandle', 'item', CRANK_STOW_TIP, (0, -1, 0),
         note='starting handle: open CrankHole_Flap, push it in along Crank_Hole until the tip pin catches '
              'Crank_Ratchet, then jerk it round clockwise seen from the front (ignition on, choke out); '
              'working pose: tip at Crank_Ratchet, rod +x, arm down (object property "working")')
    grip_stow = crank_stow_matrix() @ Vector((2.615, 0, CRANK_Z - 0.18))
    socket('Hand_Crank_Grip', grip_stow, 'hand', parent='CrankHandle')
    socket('Crank_Hole', (2.36, 0.0, CRANK_Z), 'item_slot', note='insert the handle along -x; the flap must be up')
    socket('Crank_Ratchet', CRANK_TIP, 'item_slot', note='the tip pin engages here; turning it turns the engine')
    # ratchet nut with two dogs on the crank pulley, guide ring in the bay front wall, grommet in the floor pan,
    # the hole in the bumper with a sprung flap
    engine_kb.cyl((1.452, 0, CRANK_Z), (1.468, 0, CRANK_Z), 0.016, Z.Z_STEEL2, 8)
    for s in (1, -1):
        engine_kb.box(1.462, 1.471, s * 0.010 - 0.004, s * 0.010 + 0.004, CRANK_Z - 0.006, CRANK_Z + 0.006, Z.Z_STEEL2)
    guide_kb.cyl((1.4745, 0, CRANK_Z), (1.468, 0, CRANK_Z), 0.022, Z.Z_STEEL2, 10)
    guide_kb.poly([Vector((1.4675, -0.014, CRANK_Z - 0.014)), Vector((1.4675, 0.014, CRANK_Z - 0.014)),
                   Vector((1.4675, 0.014, CRANK_Z + 0.014)), Vector((1.4675, -0.014, CRANK_Z + 0.014))][::-1], Z_BLACK)
    n = Vector((0.69, 0, -0.72)).normalized()
    guide_kb.cyl(Vector((1.546, 0, CRANK_Z)) - n * 0.006, Vector((1.546, 0, CRANK_Z)) + n * 0.006, 0.019, Z_RUBBER, 10)
    guide_kb.cyl((2.3305, 0, CRANK_Z), (2.3335, 0, CRANK_Z), 0.024, Z_CHROME, 12)
    guide_kb.cyl((2.3336, 0, CRANK_Z), (2.334, 0, CRANK_Z), 0.016, Z_BLACK, 10)
    part('Crank_Guide', 'static', (1.90, 0, CRANK_Z), note='crank hole in the bumper, grommet, guide ring, ratchet')
    F = kbs('CrankHole_Flap')
    F.cyl((2.3345, 0, CRANK_Z), (2.3375, 0, CRANK_Z), 0.028, Z_BLACK, 12)
    F.box(2.334, 2.338, -0.008, 0.008, CRANK_Z + 0.024, CRANK_Z + 0.034, Z.Z_STEEL2)
    part('CrankHole_Flap', 'hinge', (2.337, 0, CRANK_Z + 0.03), (0, -1, 0), (0, 95), parent='Kit_Front',
         note='sprung flap over the crank hole: lift it, then insert the handle')
    socket('Hand_CrankHole_Flap', (2.34, 0, CRANK_Z - 0.01), 'hand', parent='CrankHole_Flap')


# ================================================================ front bumper v3: winch drum / clutch / hook own parts,
# the crank hole, fog lamps (the winch sits 2.5 cm higher than in v2 so the crank passes under the drum)
def bumper3(kb, kbs, lens, L):
    WZ = 0.60
    kb.box(2.19, 2.33, -0.965, 0.965, 0.50, 0.655, Z_BLACK)
    for s in (1, -1):
        kb.box_m((2.26, s * 0.99, 0.58), (0.12, 0.06, 0.13), Z_BLACK, Matrix.Rotation(math.radians(s * 25), 3, 'Z'))
    D = kbs('Winch_Drum')
    D.cyl((2.375, -0.17, WZ), (2.375, 0.17, WZ), 0.058, Z_CHROME, 12)
    for s in (1, -1):
        D.cyl((2.375, s * 0.17, WZ), (2.375, s * 0.19, WZ), 0.078, Z_BLACK, 12)
    part('Winch_Drum', 'spin', (2.375, 0, WZ), (0, 1, 0), parent='Kit_Front',
         note='turns while the cable winds in (motor) or pays out (clutch free)')
    kb.cyl((2.375, 0.19, WZ), (2.375, 0.34, WZ), 0.056, Z_BLACK, 12)                     # motor
    kb.cyl((2.375, -0.19, WZ), (2.375, -0.215, WZ), 0.045, Z_BLACK, 10)                 # gear end
    Cl = kbs('Winch_Clutch')
    Cl.box(2.37, 2.38, -0.222, -0.214, WZ - 0.004, WZ + 0.07, Z.Z_REDPLAST)
    part('Winch_Clutch', 'hinge', (2.375, -0.218, WZ), (0, -1, 0), (0, 60), parent='Kit_Front',
         states=['engaged', 'free spool'], note='free spool: pull the cable out by hand to a tree')
    socket('Hand_Winch_Clutch', (2.375, -0.222, WZ + 0.065), 'hand', parent='Winch_Clutch')
    kb.box(2.425, 2.45, -0.12, 0.12, WZ - 0.05, WZ + 0.05, Z_CHROME)                   # fairlead
    kb.box(2.425, 2.452, -0.04, 0.04, WZ - 0.012, WZ + 0.012, Z_BLACK)                 # its slot
    H = kbs('Winch_Hook')
    H.tube([(2.452, 0, WZ), (2.48, 0, WZ), (2.50, 0, WZ - 0.012), (2.508, 0, WZ - 0.035), (2.498, 0, WZ - 0.052),
            (2.478, 0, WZ - 0.055), (2.468, 0, WZ - 0.04)], 0.007, Z.Z_REDPLAST, 6)
    H.cyl((2.452, 0, WZ), (2.47, 0, WZ), 0.010, Z.Z_STEEL2, 6)
    part('Winch_Hook', 'item', (2.46, 0, WZ), (1, 0, 0), parent='Kit_Front',
         note='winch hook: pull it out with the clutch free, hook it round a tree or a stuck car; cable = line from Winch_Fairlead')
    socket('Winch_Fairlead', (2.452, 0, WZ), 'item_slot', note='the cable leaves the drum here (draw it to the hook)')
    socket('Hand_Winch_Hook', (2.49, 0, WZ - 0.03), 'hand', parent='Winch_Hook')
    bar = fillet([(2.33, -0.46, 0.655), (2.355, -0.46, 1.04), (2.36, -0.40, 1.085), (2.36, 0.40, 1.085),
                  (2.355, 0.46, 1.04), (2.33, 0.46, 0.655)], 0.06, 4)
    kb.tube(bar, 0.022, Z_BLACK, 10)
    kb.tube([(2.345, -0.46, 0.86), (2.345, 0.46, 0.86)], 0.019, Z_BLACK, 10)
    sockets = []
    for s in (1, -1):
        y = s * 0.24
        side = 'L' if s > 0 else 'R'
        zc, xf = 1.205, 2.42
        f = VK.round_lamp(kb, lens('Spot_' + side, 'spot'), (xf, y, zc), (1, 0, 0), 0.075, L['spot_round'], depth=0.092,
                          dome=0.013, seg=16)
        VK.u_bracket(kb, (xf - 0.045, y, zc), (0, 1, 0), 0.085, 1.104)
        sockets.append(('Spot_' + side, f, Vector((1, 0, 0)), 'spot', Vector((0, 0, 1))))
        hook = [(2.30, s * 0.72, 0.50), (2.30, s * 0.72, 0.445), (2.35, s * 0.72, 0.425), (2.395, s * 0.72, 0.455)]
        kb.tube(hook, 0.013, VK.Z_REDPAINT, 8)
        # fog lamp set into the bumper face, selective yellow
        c = Vector((2.331, s * 0.60, 0.578))
        f = VK.rect_lamp(kb, lens('Fog_' + side, 'fog'), c, (1, 0, 0), 0.13, 0.062, L['amber'], r=0.012, proud=0.014,
                         border=0.008, chamfer=0.004, seat=0.004, crown=0.008)
        sockets.append(('Fog_' + side, f, Vector((1, 0, 0)), 'fog', Vector((0, 0, 1))))
    return sockets


# ================================================================ light: inspection lamp, 12 V socket, toggles
WL_BASE = Vector((1.56, -0.58, 0.781))                     # stowed on the passenger footwell floor, pointing forward
WL_R = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))           # lamp axis +z -> +x, local x -> +y, local y -> +z


def work_lamp(kbs, lens, L):
    M4 = Matrix.Translation(WL_BASE) @ WL_R.to_4x4()

    def body(kb):
        kb.lathe(Vector((0, 0, 0)), (0, 0, 1), [(0.0, 0.010), (0.004, 0.017), (0.11, 0.017), (0.115, 0.022), (0.125, 0.022)],
                 Z.Z_HOSE, 10)
        for zr in (0.03, 0.055, 0.08):
            kb.cyl((0, 0, zr), (0, 0, zr + 0.006), 0.0185, Z.Z_HOSE, 10)
        kb.cyl((0, 0, 0.125), (0, 0, 0.135), 0.024, Z.Z_STEEL2, 10)
        for k in range(6):
            a = math.radians(60 * k)
            e = Vector((math.cos(a), math.sin(a), 0))
            kb.tube([e * 0.024 + Vector((0, 0, 0.135)), e * 0.036 + Vector((0, 0, 0.19)), e * 0.030 + Vector((0, 0, 0.245)),
                     e * 0.012 + Vector((0, 0, 0.262))], 0.0022, Z.Z_STEEL2, 4, caps=False)
        kb.cyl((0, 0, 0.258), (0, 0, 0.266), 0.014, Z.Z_STEEL2, 8)
        kb.tube([(0, 0, 0.266), (0, 0, 0.285), (0.012, 0, 0.30), (0.026, 0, 0.29), (0.028, 0, 0.275)], 0.003, Z.Z_STEEL2, 5)
        kb.tube([(0, 0, 0.0), (0, 0, -0.03), (0.01, 0, -0.05)], 0.004, Z.Z_WIRE_B, 5)
    W = kbs('WorkLamp')
    place(W, M4, body)
    bc = M4 @ Vector((0, 0, 0.175))
    ax = (WL_R @ Vector((0, 0, 1))).normalized()
    lk = lens('WorkLamp', 'hand')
    lk.disc_uv(bc, ax, 0.021, L['dome'], 12, dome=0.032)
    lk.disc_uv(bc, -ax, 0.021, L['dome'], 12, dome=0.022)
    part('WorkLamp', 'item', WL_BASE, ax, states=['off', 'on'],
         note='inspection lamp on a 5 m cord: plug into Plug_12V; hang it by the hook (Hook_WorkLamp) on the open '
              'engine cover, a door, the rack; the bulb is lamp WorkLamp (type hand) in van3_lights.json')
    socket('Hand_WorkLamp', M4 @ Vector((0, 0, 0.06)), 'hand', parent='WorkLamp')
    socket('Hook_WorkLamp', M4 @ Vector((0.02, 0, 0.30)), 'item_slot', parent='WorkLamp', note='hangs from here')
    Cd = kbs('WorkLamp_Cord')
    cc = Vector((1.66, -0.70, 0.749))
    for k in range(3):
        ring_strip(Cd, cc + Vector((0.008 * k, -0.006 * k, 0.007 * k)), (0, 0, 1), 0.085 - 0.006 * k, 0.008, 0.008,
                   Z.Z_WIRE_B, 16)
    Cd.cyl(cc + Vector((0.06, 0.085, 0.004)), cc + Vector((0.10, 0.085, 0.004)), 0.009, Z.Z_KNOB, 8)
    part('WorkLamp_Cord', 'item', cc, (0, 0, 1),
         note='coiled cord: hide it while the lamp is in use and draw the cord from Plug_12V to the lamp handle')
    return [('WorkLamp', bc, ax, 'hand', Vector((0, 0, 1)))]


def socket_12v(kbs):
    n = Vector(VK.DASH_N)
    p = VK.on_face(-0.24, 1.085, 0.0)
    D = kbs('DashControls')
    D.lathe(p, n, [(0.0, 0.016), (0.004, 0.016), (0.008, 0.013)], Z.Z_KNOB, 10)
    D.cyl(p + n * 0.0081, p + n * 0.0083, 0.009, Z_BLACK, 8)
    Cp = kbs('Socket_12V_Cap')
    Cp.cyl(p + n * 0.0085, p + n * 0.012, 0.0135, Z.Z_KNOB, 10)
    u, v = up_axes(n)
    part('Socket_12V_Cap', 'hinge', p + n * 0.01 + v * 0.0135, -u, (0, 100), parent='DashControls',
         note='cap of the 12 V socket (hinged at the top)')
    socket('Plug_12V', p + n * 0.01, 'item_slot', note='12 V socket: the inspection lamp plug goes in here')


def toggles_contract(lamps):
    """lamps: {name: type}.  Each dash toggle switches a circuit (and has a fuse of the same number)."""
    by = lambda *types: sorted(k for k, t in lamps.items() if t in types)
    controls = {
        'Toggle_Head': by('head', 'tail', 'plate') + sorted(k for k in lamps if k.startswith('Marker_')),
        'Toggle_Fog': by('fog'),
        'Toggle_Spot': by('spot'),
        'Toggle_Roof': sorted(k for k in lamps if k.startswith('LightBar')),
        'Toggle_Work': sorted(k for k in lamps if k.startswith('Work_')),
        'Toggle_Cabin': by('dome', 'night', 'flood', 'pendant'),
        'Toggle_Stove': ['Heater_Fan'],
        'Toggle_Wiper': ['Wiper_L', 'Wiper_R'],
    }
    for i, name in enumerate(TOGGLES):
        piv = VK.TOGGLE_PIVOTS[i]
        part(name, 'hinge', piv, (0, 1, 0), (0, 57.6), parent='Dash', states=['off (down)', 'on (up)'],
             note=f'dash toggle {name[7:].upper()}: works through Fuse_{i + 1}; switches ' + ', '.join(controls[name]))
        CONTRACT['parts'][name]['controls'] = controls[name]
        CONTRACT['parts'][name]['fuse'] = f'Fuse_{i + 1}'
        socket('Hand_' + name, piv + Vector(VK.DASH_N) * 0.02, 'hand', parent=name)


def heater_controls(kbs):
    """the heater plate on the centre stack: temperature slider on the HEAT bar, fan lever 0..3, AIR knob
    (feet / windscreen)"""
    n = Vector(VK.DASH_N)
    u, v = up_axes(n)                                   # u = to the passenger (-y), v = up the panel
    c = VK.on_face(0.0, 1.110, 0.009)
    pt = lambda a, b, off: c + u * a + v * b + n * off
    R = Matrix((u, v, n)).transposed()
    T = kbs('Heater_Temp')
    T.box_m(pt(-0.105, -0.005, 0.006), (0.010, 0.012, 0.010), Z.Z_KNOB, R)
    part('Heater_Temp', 'slide', pt(-0.105, -0.005, 0.0), u, (0, 0.062), unit='m', parent='Dash',
         states=['cold', 'hot'], note='heat: slide towards the red end of the bar')
    F = kbs('Heater_Fan')
    F.box_m(pt(0.0012, -0.004, 0.006), (0.008, 0.014, 0.010), Z.Z_KNOB, R)
    part('Heater_Fan', 'slide', pt(0.0012, -0.004, 0.0), u, (0, 0.0507), unit='m', parent='Dash',
         states=['0', '1 (0.0169)', '2 (0.0338)', '3 (0.0507)'], note='fan speed 0..3 (needs Toggle_Stove on)')
    A = kbs('Heater_Air')
    A.lathe(pt(0.086, 0.0, 0.0), n, [(0.0, 0.009), (0.008, 0.009), (0.010, 0.006)], Z.Z_KNOB, 10)
    A.box_m(pt(0.086, 0.0, 0.011), (0.003, 0.012, 0.003), Z.Z_STEEL2, R)
    part('Heater_Air', 'twist', pt(0.086, 0.0, 0.0), -n, (0, 90), parent='Dash', states=['feet', 'windscreen'],
         note='air flap, clockwise from feet to windscreen (the axis points into the panel): with heat and fan it '
              'clears the frost (see lob)')
    for nm in ('Heater_Temp', 'Heater_Fan', 'Heater_Air'):
        socket('Hand_' + nm, Vector(CONTRACT['parts'][nm]['pivot']) + n * 0.015, 'hand', parent=nm)


# ================================================================ horror: mirror, locks, curtains
MIRROR_C = Vector((1.57, 0.0, 1.79))
EYE_DRIVER = Vector((1.15, 0.53, 1.77))


def rear_mirror(kbs, glass_kb):
    """interior rear-view mirror on a stem from the header; the glass is its own object with 0..1 UVs (render
    texture), angled so the driver sees the saloon and the rear doors"""
    to_eye = (EYE_DRIVER - MIRROR_C).normalized()
    to_rear = (Vector((-2.0, 0.0, 1.55)) - MIRROR_C).normalized()
    nm = (to_eye + to_rear).normalized()
    u = Vector((0, 0, 1)).cross(nm).normalized()              # right as seen in the mirror
    v = nm.cross(u)
    M = kbs('RearMirror')
    M.loft([rrect(MIRROR_C - nm * 0.014, u, v, 0.20, 0.048, 0.02), rrect(MIRROR_C - nm * 0.006, u, v, 0.24, 0.064, 0.026),
            rrect(MIRROR_C + nm * 0.002, u, v, 0.24, 0.064, 0.026), rrect(MIRROR_C + nm * 0.002, u, v, 0.228, 0.054, 0.022)],
           [Z.Z_KNOB, Z.Z_KNOB, Z.Z_KNOB], cap0=Z.Z_KNOB)
    top = Vector((1.60, 0.0, 1.884))
    M.tube([top, top + Vector((-0.01, 0, -0.03)), MIRROR_C - nm * 0.012 + Vector((0, 0, 0.012))], 0.006, Z.Z_KNOB, 6)
    M.box(1.585, 1.615, -0.02, 0.02, 1.877, 1.886, Z.Z_KNOB)
    gp = MIRROR_C + nm * 0.0025
    w, h = 0.226, 0.052
    glass_kb.poly([gp - u * w / 2 - v * h / 2, gp + u * w / 2 - v * h / 2, gp + u * w / 2 + v * h / 2, gp - u * w / 2 + v * h / 2],
                  VK.ZERO, [(0, 0), (1, 0), (1, 1), (0, 1)])
    part('RearMirror', 'hinge', MIRROR_C, (0, 0, 1), (-15, 15), parent='Kuzov', note='ball joint: the player can turn it')
    part('RearMirror_Glass', 'static', MIRROR_C, parent='RearMirror',
         note='render texture quad (UV 0..1, flip U): M_Van_MirrorRT')
    d_in = (MIRROR_C - EYE_DRIVER).normalized()
    d_out = d_in - nm * 2 * d_in.dot(nm)
    socket('MirrorCam', MIRROR_C - nm * 0.02, 'camera', parent='RearMirror',
           note='camera for the mirror render texture: looks along dir (the reflection of the driver\'s eye ray); '
                'fov 32; the back seat is in view: ghost scares show here')
    CONTRACT['sockets']['MirrorCam']['dir'] = [round(float(x), 4) for x in d_out]
    CONTRACT['sockets']['MirrorCam']['up'] = [0.0, 0.0, 1.0]
    CONTRACT['sockets']['MirrorCam']['fov'] = 32


def door_locks(kbs):
    """a lock button on the inner panel of every door: push in = locked (locked doors do not open from outside)"""
    spec = {'doorL': ((1.30, 0.0, 1.30), (0, 1, 0)), 'doorP': ((1.30, 0.0, 1.30), (0, -1, 0)),
            'doorSalon': ((-0.50, 0.0, 1.27), (0, -1, 0)), 'doorZL': ((-1.5, 0.12, 1.27), (-1, 0, 0)),
            'dooZP': ((-1.5, -0.12, 1.27), (-1, 0, 0))}
    out = {}
    for dn, (o_, d_) in spec.items():
        ob = bpy.data.objects[dn]
        Mw = ob.matrix_world
        bvh = BVHTree.FromPolygons([tuple(Mw @ v.co) for v in ob.data.vertices], [list(p.vertices) for p in ob.data.polygons])
        loc, nor, idx, dist = bvh.ray_cast(Vector(o_), Vector(d_), 2.5)
        if loc is None:
            continue
        inward = -Vector(d_)
        name = 'Lock_' + dn
        K = kbs(name)
        p = loc + inward * 0.001
        K.cyl(p - inward * 0.004, p + inward * 0.014, 0.007, Z.Z_STEEL2, 8)
        K.lathe(p + inward * 0.014, inward, [(0.0, 0.012), (0.005, 0.012), (0.009, 0.005)], Z.Z_REDPLAST, 10)
        part(name, 'slide', p, -inward, (0, 0.008), unit='m', parent=dn, states=['unlocked', 'locked'],
             note='lock button: pushed in = locked; a locked door does not open from outside')
        socket('Hand_' + name, p + inward * 0.022, 'hand', parent=name)
        out[dn] = p
    return out


def curtains(VP, windows, door_name, wall_y=0.875):     # 2.5 cm off the wall: clear of the seat-back tops
    """gathered curtains as parts that stretch along the rod to close the window (open = scale 1); rods static.
    Returns (curtain objects, rods of the body, rod of the door)"""
    objs, rods_body, rods_door = [], [], []
    for side in (1, -1):
        wins = sorted([w for w in windows if w[2] == side], key=lambda w: w[0])
        for k, (x0, x1, s_, zb, zt) in enumerate(wins):
            wy = side * wall_y
            S = 'L' if side > 0 else 'R'
            in_door = side < 0 and x0 > VM.SIDE_DOOR['x0'] - 0.05 and x1 < VM.SIDE_DOOR['x1'] + 0.05
            close = ((x1 - x0) / 2 + 0.02) / 0.15
            for tag, xa, xb, piv_x, axis in (('A', x0 - 0.02, x0 + 0.13, x0 - 0.02, (1, 0, 0)),
                                             ('B', x1 - 0.13, x1 + 0.02, x1 + 0.02, (-1, 0, 0))):
                name = f'Curtain_{S}{k + 1}{tag}'
                o = VP.curtain(name, xa, xb, side, zt + 0.03, zb - 0.02, wy)
                if o in VP.PROPS:
                    VP.PROPS.remove(o)
                piv = Vector((piv_x, wy - side * 0.02, zt + 0.03))
                set_pivot(o, piv)
                o['orig'] = name
                objs.append(o)
                part(name, 'stretch', piv, axis, (1.0, round(close, 3)), unit='x', parent=door_name if in_door else 'Kuzov',
                     states=['open', 'closed'], note='curtain: scale along axis from the window edge; '
                                                     f'{round(close, 2)} = closed (meets its pair in the middle)')
                socket(f'Hand_{name}', piv + Vector(axis) * 0.12 + Vector((0, 0, -0.25)), 'hand', parent=name)
            rod = VP.cyl(f'CurtainRod_{S}{k + 1}', ((x0 + x1) / 2, wy - side * 0.035, zt + 0.045), 'x', 0.006, x1 - x0 + 0.04,
                         VP.Z_STEEL, 6)
            if rod in VP.PROPS:
                VP.PROPS.remove(rod)
            (rods_door if in_door else rods_body).append(rod)
    return objs, rods_body, rods_door


# ================================================================ snow: sand ladders out of the roof load
def split_faces(o, fpred, name):
    """move the faces of o for which fpred(centre, zone) holds into a new object (same transform)"""
    me = o.data.copy()
    new = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(new)
    new.matrix_world = o.matrix_world.copy()
    for ob, keep in ((o, False), (new, True)):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        zl = bm.faces.layers.float.get('zone')
        dead = [f for f in bm.faces if bool(fpred(ob.matrix_world @ f.calc_center_median(), int(round(f[zl])))) != keep]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    new['orig'] = name
    return new


def sand_ladders(kit_load, zb=2.20):
    out = []
    for i, (y0, y1) in enumerate(((0.06, 0.38), (0.42, 0.74))):
        name = f'SandLadder_{i + 1}'
        o = split_faces(kit_load, lambda c, z: -0.92 < c.x < 0.22 and y0 < c.y < y1 and c.z > zb, name)
        piv = Vector((-0.35, (y0 + y1) / 2, zb + 0.034))
        set_pivot(o, piv)
        part(name, 'item', piv, (1, 0, 0), parent='Kit_RoofRack',
             note='sand ladder (1.1 m): off the rack, under a wheel that spins in the snow, studs up')
        socket(f'Hand_{name}_A', piv + Vector((-0.50, 0, 0.02)), 'hand', parent=name)
        socket(f'Hand_{name}_B', piv + Vector((0.50, 0, 0.02)), 'hand', parent=name)
        out.append(o)
    return out


# ================================================================ driving: wipers, windscreen frost, seats
WS_N = Vector((0.446, 0.0, 0.392)).normalized()            # windscreen normal (outwards), average over the glass
# wiper spindle axes: the rigid arm turning about them stays closest to the curved glass over its 0..100 deg sweep
# (searched against lob: at most 1 cm into the glass, 4 cm off it); tilt 13.5 deg, yaw 14 deg towards the side
WIPER_AXIS = {1: Vector((-0.9435, -0.2419, -0.2265)).normalized(), -1: Vector((0.9435, -0.2419, 0.2265)).normalized()}


def wipers(kz, kill_islands_fn=None):
    """the stock wipers (rubber islands on the cowl) become two parts turning about their spindles"""
    out = {}
    for s, name in ((1, 'Wiper_L'), (-1, 'Wiper_R')):
        lo = Vector((1.93, min(0.0, s * 0.48), 1.32))
        hi = Vector((2.02, max(0.0, s * 0.48), 1.46))
        bm = bmesh.new()
        bm.from_mesh(kz.data)
        zl = bm.faces.layers.float.get('zone')
        bm.faces.ensure_lookup_table()
        cand = {f.index for f in bm.faces if int(round(f[zl])) in (VK.Z_RUBBER, VK.Z_BLACK)}
        keep = set()
        while cand:
            f0 = cand.pop()
            st, isl = [f0], [f0]
            while st:
                f = bm.faces[st.pop()]
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index in cand:
                            cand.remove(g.index)
                            st.append(g.index)
                            isl.append(g.index)
            C = np.array([tuple(bm.faces[i].calc_center_median()) for i in isl])
            if np.all(C.min(0) > np.array(lo)) and np.all(C.max(0) < np.array(hi)):
                keep.update(isl)
        cen = [tuple(bm.faces[i].calc_center_median()) for i in keep]
        bm.free()
        if not keep:
            continue
        keys = {tuple(round(v, 6) for v in c) for c in cen}
        o = VM.split_off(kz, lambda c: tuple(round(v, 6) for v in c) in keys, name)
        piv = Vector((1.9885, s * 0.4605, 1.3455))
        set_pivot(o, piv)
        ax = WIPER_AXIS[s]
        part(name, 'hinge', piv, ax, (0, 100), parent='Kuzov', states=['parked', 'sweeping'],
             note='wiper: sweeps up across its pane and back (Toggle_Wiper, fuse 8); clears snow and frost in its arc')
        out[name] = o
    return out


def frost_uv(lob):
    """windscreen UV 0..1 across the whole glass (u from the left edge to the right, v from the bottom up the slope):
    T_Van_Frost alpha says how early each texel freezes"""
    me = lob.data
    uv = me.uv_layers.get('PSX') or me.uv_layers.new(name='PSX')
    Mw = lob.matrix_world
    P0, P1 = Vector((1.984, 0, 1.392)), Vector((1.592, 0, 1.838))
    up = (P1 - P0)
    Lup = up.length
    up.normalize()
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = Mw @ me.vertices[me.loops[li].vertex_index].co
            uu = (0.792 - co.y) / 1.584
            vv = (co - P0).dot(up) / Lup
            uv.data[li].uv = (min(max(uu, 0.0), 1.0), min(max(vv, 0.0), 1.0))
    uv.active = True
    uv.active_render = True


def frost_texture(path, W=256, H=128):
    """PSX frost for the windscreen: RGB = ice (white-blue with crystal sparkle), A = when the texel freezes
    (edges and the corners first, then fern-like fingers grow in); the pillar splits the glass in two panes"""
    from PIL import Image
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx + 0.5) / W
    v = (yy + 0.5) / H
    pane_u = np.where(u < 0.5, u / 0.5, (u - 0.5) / 0.5)
    d_edge = np.minimum.reduce([pane_u, 1 - pane_u, v * 0.55, (1 - v) * 0.9])
    def noise(scale, seed):
        r = np.random.default_rng(seed)
        g = r.random((int(H / scale) + 2, int(W / scale) + 2)).astype(np.float32)
        from scipy import ndimage
        return ndimage.zoom(g, (H / (g.shape[0] - 1), W / (g.shape[1] - 1)), order=3)[:H, :W]
    n1, n2, n3 = noise(16, 1), noise(6, 2), noise(2.5, 3)
    fern = np.abs(np.sin((u * 37 + v * 23) + n2 * 6.0)) * np.abs(np.sin((u * 29 - v * 41) + n1 * 5.0))
    grow = d_edge - 0.10 * (n1 - 0.5) - 0.05 * (fern - 0.5) - 0.03 * (n3 - 0.5)
    a = 1.0 - np.clip(grow / 0.55, 0, 1)
    a = np.clip(a ** 1.3, 0, 1)
    ice = np.stack([0.80 + 0.12 * n3, 0.86 + 0.10 * n3, 0.92 + 0.06 * n3], -1)
    spark = (n3 > 0.82).astype(np.float32)[..., None] * 0.12
    rgb = np.clip(ice + spark - 0.10 * fern[..., None], 0, 1)
    from psxlib import BAYER4
    bay = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W]
    q = lambda x, lv: np.floor(np.clip(x, 0, 1) * (lv - 1) + bay[..., None] if x.ndim == 3 else
                               np.clip(x, 0, 1) * (lv - 1) + bay) / (lv - 1)
    rgb8 = (np.clip(q(rgb, 16), 0, 1) * 255 + 0.5).astype(np.uint8)
    import van3_play as _VPL                           # flat histogram: amount t covers about t of the glass
    a8 = _VPL.uniform_alpha8(a, bay)
    Image.fromarray(np.dstack([rgb8, a8]), 'RGBA').save(path)
    return path


TABLE_X = (-1.24, -0.84)                               # the cozy kit's table (van2_props), x extent


def seat_sockets(seats_info, X_cab=1.12):
    """hip, eye and exit points for everyone who sits in the van; eye heights fit the low saloon (about 1.25 m from
    the floor to the ceiling: no standing up in the saloon, crouch or sit)"""
    for s, nm in ((1, 'Sit_Driver'), (-1, 'Sit_Passenger')):
        hip = Vector((X_cab, s * 0.53, 1.07))
        socket(nm, hip, 'sit', note='cab seat; look forward')
        CONTRACT['sockets'][nm].update(eye=[round(float(v), 4) for v in (1.15, s * 0.53, 1.77)], facing=[1.0, 0.0, 0.0],
                                       exit=[round(float(v), 4) for v in (1.30, s * 1.45, -0.09)],
                                       door='doorL' if s > 0 else 'doorP')
    for tag, sd in seats_info.items():
        sgn = 1 if sd['side'] == 'left' else -1
        xc = sd['pan_pivot'][0]
        nm = 'Sit_' + tag
        socket(nm, (xc, sgn * 0.65, 1.141), 'sit', parent='Seat_' + tag, note='folding troop seat (must be down)')
        ex = (xc, 0.0)
        if TABLE_X[0] - 0.05 < xc < TABLE_X[1] + 0.05:    # the cozy table stands between L1 and R1: step out past it
            ex = (TABLE_X[1] + 0.29, 0.15 if sgn > 0 else -0.20)    # >= 0.28 m from the table and seat L2's leg
        elif TABLE_X[1] < xc < TABLE_X[1] + 0.40:          # L2: its spot moves forward, clear of the L1 / R1 spots
            ex = (xc + 0.12, 0.0)
        CONTRACT['sockets'][nm].update(eye=[round(float(xc), 4), round(sgn * 0.60, 4), 1.78], facing=[0.0, -float(sgn), 0.0],
                                       exit=[round(float(ex[0]), 4), round(float(ex[1]), 4), 0.716],
                                       door='doorSalon or the rear doors',
                                       exit_note='preferred spot to stand up (crouched: the saloon is low); if another '
                                                 'player is there, slide along the aisle')
