"""Garage (the stand-alone one on the Forest map: prefab Garage, Forest_Layout.json p [379.691, 16.4452, -400.9222], yaw 8
deg) -- the layout measured off Update 3's Garage.fbx: the hall 12 x 9 m in profiled sheet on a concrete plinth, the
up-and-over door IX_GarageDoor_92 in the south wall, the side door IX_GarageSideDoor_93 in the east wall, a window in the
south and the north wall, the two ceiling fittings and the lamp over the door (Update 3's lights and glows), inside the
station's quad on its stand, the shelving, the crates, the workbench with its pegboard, the drums. Names, pivots, axes and
ranges are Update 3's.
Frame: Blender axes as Update 3's FBX imports -- x east, y north, z up, origin on the floor's finish in the middle of the
hall (Unity prefab-local = (-x, z, -y)). Metres."""

# ---------------------------------------------------------------- levels and the envelope
FLOOR = 0.0                      # the hall's floor (power-floated concrete)
GROUND = -0.10                   # the base's asphalt round the garage (Forest_Terrain at the prefab: 16.345)
PLINTH_BOT = -0.50               # the plinth's foot (Update 3)
XO, YO = 6.00, 4.50              # the walls' outer face (the sheet's crests)
XI, YI = 5.80, 4.30              # the inner face (the liner)
EAVES = 4.40                     # the walls' top = the ceiling's underside
ROOF_T = 4.64                    # the roof slab's top (Update 3)
ROOF_OV = 0.20                   # the roof's overhang (Update 3: 12.4 x 9.4)
PLX, PLY = 6.03, 4.53            # the plinth's outer face (Update 3: 12.06 x 9.06)

# ---------------------------------------------------------------- openings (wall: 'S', 'N', 'E', 'W'; u along the wall)
GATE = dict(name='IX_GarageDoor_92', wall='S', u=(-3.30, 0.30), z=(0.0, 3.20),
            pivot=(-3.28, -4.40, 3.18), axis_u=(1.0, 0.0, 0.0), range=(0.0, 85.0),
            leaf_lo=(-3.28, -4.48, 0.02), leaf_hi=(0.28, -4.375, 3.18))
SIDE = dict(name='IX_GarageSideDoor_93', wall='E', u=(1.025, 1.975), z=(0.0, 2.10),
            pivot=(5.965, 1.055, 0.01), axis_u=(0.0, 1.0, 0.0), range=(0.0, 100.0),
            leaf_lo=(5.916, 1.055, 0.01), leaf_hi=(5.99, 1.965, 2.09))
WINDOWS = [dict(name='W_South', wall='S', u=(3.20, 4.40), z=(1.40, 2.40)),
           dict(name='W_North', wall='N', u=(-0.80, 0.80), z=(1.60, 2.60))]
LOCK_KEY = 'Garage'              # Forest_Opening.json: both doors locked, the key Item_Key_Garage

# ---------------------------------------------------------------- Update 3's lights and glows (Forest_Layout prefabLights /
# prefabGlows, model Garage; tag power: dark until the station has mains), here in the building frame
FITTINGS = [(-3.0, 0.0), (3.0, 0.0)]          # the two ceiling fittings (0.64 square, under the ceiling)
WALL_LAMP = (-1.50, -4.50, 3.55)              # the lamp over the gate (its glow at y -4.62)
SIGN = dict(c=(-1.50, -4.50, 3.85), w=1.10, h=0.44)   # GARAGE over the gate (Update 3: z 3.63 .. 4.07)

# ---------------------------------------------------------------- Update 3's contents (static), measured
QUAD = dict(c=(-1.50, 1.00), along='x', front=+1)             # wheels at x -2.12 / -0.88, y 0.5 / 1.5; faces east
SHELF = dict(x=(-5.80, -5.20), y=(0.30, 2.70), h=2.40, levels=(0.10, 0.85, 1.60, 2.35))
BENCH = dict(x=(2.40, 4.80), y=(3.525, 4.275), top=0.93)     # top 2.4 x 0.75 (Update 3: 0.87 .. 0.93), legs 0.9
PEGBOARD = dict(x=(2.40, 4.80), y=4.28, z=(1.10, 2.10))
CRATES = [((-2.994, 3.429), (0.934, 0.667), 86.1, 0.0, 0.667, 'crate'),       # centre, size along / across, yaw, z0, z1
          ((-2.994, 3.429), (0.500, 0.350), 22.9, 0.667, 1.067, 'crate'),
          ((-3.365, 2.442), (0.719, 0.514), 6.2, 0.0, 0.514, 'crate'),
          ((-3.773, 2.572), (0.773, 1.082), 81.2, 0.0, 0.773, 'pallet'),
          ((-4.186, 3.008), (0.803, 0.574), 7.7, 0.0, 0.573, 'pallet')]
DRUMS = [((4.80, -2.60), 'blue'), ((5.42, -2.60), 'red'), ((5.42, -2.04), 'blue')]   # (Update 3's third stood half
#                                                                                       through the east wall: inside now)
ROOM = dict(x0=-XI, x1=XI, y0=-YI, y1=YI, f=FLOOR, c=EAVES)    # the hall, one light zone (Update 3: exterior layer)
SHELF_BOXES = [                  # on the shelving: centre (x, y), size (x, y), z0, z1, kind (Update 3's boxes)
    ((-5.5, 1.553), (0.371, 0.421), 0.115, 0.429, 'card'),
    ((-5.5, 1.958), (0.539, 0.288), 0.115, 0.435, 'olive'),
    ((-5.5, 0.547), (0.495, 0.531), 0.865, 1.085, 'olive'),
    ((-5.5, 1.014), (0.402, 0.302), 0.865, 1.253, 'card'),
    ((-5.5, 1.398), (0.489, 0.367), 0.865, 1.145, 'olive'),
    ((-5.5, 1.758), (0.513, 0.251), 0.865, 1.092, 'olive'),
    ((-5.5, 2.076), (0.494, 0.285), 0.865, 1.105, 'card'),
    ((-5.5, 0.611), (0.436, 0.531), 1.615, 1.964, 'wood'),
    ((-5.5, 1.144), (0.484, 0.435), 1.615, 1.936, 'army'),
    ((-5.5, 1.589), (0.468, 0.355), 1.615, 1.982, 'wood'),
    ((-5.5, 1.955), (0.532, 0.276), 1.615, 1.823, 'olive'),
    ((-5.5, 2.371), (0.502, 0.457), 1.615, 1.991, 'army'),
    ((-5.5, 0.506), (0.517, 0.344), 2.365, 2.705, 'wood'),
    ((-5.5, 0.873), (0.375, 0.291), 2.365, 2.698, 'wood'),
    ((-5.5, 1.23), (0.499, 0.321), 2.365, 2.727, 'army'),
    ((-5.5, 1.586), (0.393, 0.291), 2.365, 2.682, 'olive'),
    ((-5.5, 2.027), (0.511, 0.493), 2.365, 2.673, 'card'),
    ((-5.5, 2.462), (0.504, 0.276), 2.365, 2.632, 'olive'),
]
PLACE = dict(p=[379.691, 16.4452, -400.9222], q=[0.0, 0.069756, 0.0, 0.997564])   # Forest_Layout.json prefab Garage
U3_LIGHTS = [dict(t='point', p=(-3.0, 0.0, 4.03), c=(0.86, 0.96, 1.0), i=0.4, r=6.5, fixture='FX_GarageFluor_1'),
             dict(t='point', p=(3.0, 0.0, 4.03), c=(0.86, 0.96, 1.0), i=0.4, r=6.5, fixture='FX_GarageFluor_2'),
             dict(t='point', p=(-1.5, -5.0, 3.35), c=(1.0, 0.72, 0.42), i=1.0, r=9.0, fixture='FX_GarageLamp')]
U3_GLOWS = [dict(p=(-3.0, 0.0, 4.33), m='M_Glow_Fluor', s=0.9), dict(p=(3.0, 0.0, 4.33), m='M_Glow_Fluor', s=0.9),
            dict(p=(-1.5, -4.62, 3.55), m='M_Glow_Bulb', s=0.6)]
