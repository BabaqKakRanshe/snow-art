"""Dimensions of the fence and road-block kit (Forest Update 7), metres.
Frame of every prefab: x along the fence / block, y across (-y = the outside, the side the relief, the signs and the
barbed outriggers face), z up; pivot on the ground in the middle of the section (as Update 3's FenceChain); Unity
prefab-local = (-x, z, -y).

References:
  PO-2 (plita ogrady PO-2, B. Lakhman, 1974; series IZh 31-77): 2.50 m long, 3.00 m tall with the legs, 0.15 m thick,
     ~1.4 t; the legs stand in FO-2 sockets (0.95 x 0.75 x 0.53 m, 0.63 t) set 2.5 m apart, two panels per socket; the
     face a relief of rhombi (light and shade so a long fence is not monotonous); seen ~2.5 m above the ground.
  FBS 24.4.6 foundation block: 2.38 x 0.40 x 0.58 m, two lifting loops, end grooves.
  New Jersey concrete barrier: 2.0 m long, 0.61 m at the foot, 0.81 m tall, 0.15 m at the top.
  Dragon's teeth (Hoecker of the Westwall): truncated pyramids ~1.0 m square at the foot, ~1.1 m tall, in lines.
  Czech hedgehog: three steel beams crossed at their middles, ~1.6 m, standing on three ends.
  Cheval de frise (rogatka): a beam on X-shaped stakes wound with barbed wire.
  Abatis (zaseka): felled trees, crowns and sharpened branches to the outside.
"""
import math

# ---------------------------------------------------------------- PO-2 concrete fence
PO2 = dict(L=2.50, gap=0.02, t=0.15, z0=0.10, z1=2.60, border=0.08, cells=(9, 9), relief=0.018,
           socket=dict(lx=0.95, ly=0.75, top=0.08, bot=-0.45, slot=(0.36, 0.20)))
# outrigger on each joint (at x = +L/2): an angle bar up the panel's end and two arms in a Y, barbed bands on both
BRACKET = dict(w=0.050, t=0.006, z_base=2.10, z_fork=2.78, arm=0.52, angle=40.0, band=0.50, strands=(0.08, 0.21, 0.34, 0.46))
BROKEN = dict(corner=(-1.24, 2.60), cut=((-0.42, 2.60), (-0.62, 2.18), (-0.93, 1.95), (-1.24, 1.62)), rebar=6)
SIGN = dict(c=(0.0, 1.55), w=1.00, h=0.60)                      # on the outer face, x / z of the plate's centre
WICKET = dict(panel=(-1.24, -0.06), opening=(-0.06, 1.18), post_r=0.040, lintel_z=2.05, door_w=1.10, door_h=1.95,
              door_open=100.0)

# ---------------------------------------------------------------- chain-link (the new, flicker-free one)
CHAIN = dict(L=3.0, post_x=1.5, post_r=0.030, post_top=2.30, post_bottom=-0.40, rail_z=2.20, rail_r=0.021,
             mesh_z=(0.04, 2.18), off=0.0012, arm=((0.0, 2.28), (-0.36, 2.64)), band=0.52, strands=(0.141, 0.311, 0.481),
             torn=dict(x=(-0.95, 0.15), z=(0.04, 1.05), flap=0.45))

# ---------------------------------------------------------------- concertina coil (5 m, on three stakes)
COIL = dict(L=5.0, r=0.45, loops=10, seg=14, ribbon=0.060, stakes=(-2.2, 0.0, 2.2), stake_h=0.75)

# ---------------------------------------------------------------- road blocks
FBS = dict(L=2.38, w=0.40, h=0.58, groove=(0.12, 0.05), loop_x=0.70, loop_r=0.055, loop_rod=0.008, ch=0.012)
JERSEY = dict(L=2.0, prof=((-0.305, 0.0), (-0.305, 0.075), (-0.205, 0.330), (-0.075, 0.810), (0.075, 0.810),
                           (0.205, 0.330), (0.305, 0.075), (0.305, 0.0)), slot=(0.30, 0.10), slot_x=0.55)
CUBE = dict(s=1.00, ch=0.05, loop_r=0.07, loop_rod=0.010)
TOOTH = dict(base=1.00, top=0.36, h=1.10, cap=0.06, bury=0.25)
HEDGE = dict(L=1.60, w=0.10, t=0.010, gusset=0.16)
BARRICADE = dict(L=3.0, beam_r=0.055, beam_z=0.82, stake_r=0.040, stake_L=1.75, stake_x=(-1.30, 0.0, 1.30),
                 stake_ang=55.0, wire_band=0.42)
ABATIS = dict(L=7.2, r0=0.19, r1=0.06, lift=0.10, stubs=22, spikes=7, spike_L=(0.9, 1.5), seed=7)

# ---------------------------------------------------------------- signs
HALT = dict(w=1.20, h=0.80, z=1.55, posts=(-0.45, 0.45), post_r=0.035)
NOENTRY = dict(r=0.275, z=1.85, post_r=0.030)


def rad(d):
    return math.radians(d)
