"""forest_bunker sizes (metres; Blender frame: z up, the front -y; Unity (x, y, z) -> (-x, z, -y)).
BunkerHangar   origin on the floor in the middle of the gate line (the facade's front face, y = 0); the gate faces -y
               (the lake), the hall runs to +y into the shore
BlastDoor      origin on the floor in the middle of the vestibule's open end; the vestibule runs to +y, the round door at
               its far end; it fits the hangar's back opening (BunkerHangar Link_BlastDoor, no rotation)
BunkerEntrance origin on the ground at the top step's edge, in the middle; the stair trench goes down to +y under the
               portal canopy, the hatch in the landing floor, the shaft below it
PlaneTarp      in the frame of forest's UtilityPlane (v13 model: root on the ground under the fuselage, the nose -y); a child
               of the plane root in Unity"""
import math
import bpy                                               # (provides mathutils)
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- the hangar
H = dict(
    xi=9.0,            # inner half width (the hall 18 m)
    y_in0=0.8,         # front wall's inner face (the facade's front face at y = 0)
    y_in1=15.8,        # back wall's inner face
    t_side=0.6, t_back=0.6,
    zc=6.5,            # ceiling (the roof slab's underside)
    z_roof=7.3,        # the roof slab's top
    z_par=8.0,         # the facade's parapet
    z_foot=-0.3,       # the facade's foot below the apron
    gate_x=8.0, gate_z=5.2,             # the gate opening: |x| < 8, z < 5.2
    fac_x=16.9,                          # the facade's half width (the open leaves park in front of it)
    leaf_w=8.3, leaf_z0=0.05, leaf_z1=5.45, leaf_y0=-0.60, leaf_y1=-0.30,
    rail_y=-0.45, guide_z=(5.50, 5.80),
    apron_y=-6.0, apron_drop=0.20, apron_x=17.0,
    wing_len=6.0, wing_ang=30.0, wing_t=0.5, wing_z_end=1.0,
    pil_y=(3.8, 6.8, 9.8, 12.8), pil_w=0.5, pil_d=0.30,
    beam_d=0.60, beam_f=0.30, beam_web=0.02, beam_flange=0.025,
    lamps=[(sx * 4.5, y) for y in (5.3, 8.3, 11.3) for sx in (-1, 1)], lamp_z=5.2,
    back_open=(2.5, 4.6),                # half width, height of the back opening (the vestibule)
    # the side door: in the -x wall, up on a landing, steps down toward the hall's middle
    door_y=2.2, door_w=1.20, door_h=2.10, door_sill=1.20,
    land_x=1.10, land_y=(1.40, 3.00), steps=6, rise=0.20, run=0.28, step_w=(1.60, 2.80),
)
HY_BACK = H['y_in1'] + H['t_back']                      # the back wall's outer face: Link_BlastDoor

# ---------------------------------------------------------------- the vestibule with the round door ("die Tür nach unten")
V = dict(
    xi=2.5, zc=4.6, L=8.0, t=0.5,         # inner half width, height, length (open end y = 0 to the end wall)
    door_c=1.96, leaf_r=1.58, leaf_t=0.45, ring_r=(1.60, 1.94), ring_t=0.16, leaf_front=0.20,   # leaf front proud of the wall
    hinge_x=-2.12, hinge_dy=-0.36,        # the hinge axis: vertical, x -2.12, 0.36 m in front of the end wall
    arms=6, hub_r=0.44, wheel_r=0.40,
    tunnel_L=2.4, steps=4,
    chan_w=0.60, chan_d=0.40,            # the drain channel along the +x wall
)

# ---------------------------------------------------------------- the entrance
E = dict(
    xi=1.0, t=0.30, wall_top=0.25,       # trench inner half width, wall thickness, wall tops above the ground
    risers=16, rise=0.19, run=0.29,
    land_y1=7.60,                        # the landing's far end (back wall's inner face)
    portal_y=5.40, canopy_t=0.50, clear=2.50,
    hatch_c=6.60, hatch_in=0.50, hatch_lid=0.56, frame_w=0.07,
    shaft_d=4.0, ice_t=0.12,
)
E_DROP = E['risers'] * E['rise']                        # 3.04
E_Y_LAND = E['risers'] * E['run']                       # 4.64

# ---------------------------------------------------------------- the plane in the hangar (forest UtilityPlane v13)
PLANE = dict(
    contact=(0.0, -2.85, -0.12),          # main wheels' ground line in the plane's frame (Wheel_L/R bottom)
    tail=(0.0, 4.47, 1.17),               # the tail wheel's bottom
    y_main=5.55,                          # where the main wheels stand in the hangar (y)
)
PLANE['pitch'] = math.degrees(math.atan2(PLANE['tail'][2] - PLANE['contact'][2], PLANE['tail'][1] - PLANE['contact'][1]))


def plane_park_matrix():
    """plane root -> hangar frame: nose to the gate (-y), pitched nose-up about the main wheels' ground line until the
    tail wheel touches the floor"""
    c = Vector(PLANE['contact'])
    R = Matrix.Rotation(-math.radians(PLANE['pitch']), 4, 'X')
    return Matrix.Translation(Vector((0.0, PLANE['y_main'], 0.0))) @ R @ Matrix.Translation(-c)


# ---------------------------------------------------------------- the tarp (canvas thrown over the cabin and the wing's middle)
TARP = dict(w=5.2, l=6.0, res=0.12, centre=(0.0, -1.40), drop=0.05, bend=0.25, frames=100)
