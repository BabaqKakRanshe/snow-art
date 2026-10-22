"""Main building (BaseMain) — the layout, measured off the Update 3 model on the Forest map (Models/BaseMain.fbx, the
static rooms R_*, the IX_ parts' pivots and boxes, the glass panes, the shutter curtains): the rebuild keeps every wall,
opening, level, room (= light zone) and part where it was, so Forest_Layout.json / Forest_Opening.json stay valid.

Frame: the prefab's own, Blender axes — x east, y north, z up, origin on the ground floor's finished floor line in the
middle of the main block (Unity: (x, y, z) -> (-x, z, -y)).  Metres."""

# ---------------------------------------------------------------- levels
UG_F, UG_C = -3.00, -0.30                  # basement floor / ceiling (the ground-floor slab -0.30..0.00 above)
EG_F, EG_C = 0.00, 3.10                    # ground floor / slab underside; suspended ceilings at EG_SC
EG_SC = 2.75
OG_F, OG_C = 3.40, 6.30                    # upper floor (slab 3.10..3.40) / ceiling (roof slab 6.30..6.60)
ROOF = 6.60                                # roof membrane + gravel
PARAPET = 7.50                             # parapet top (coping above to PARAPET + 0.04)
TOWER_CEIL = 9.40                          # stair tower: ceiling (roof slab 9.40..9.65, coping above 9.65)
TOWER_TOP = 9.65
GROUND = -0.45                             # the yard at the entrance (the floor sits 0.45 above it)
PLINTH_BOT = -0.75                         # the dark plinth reaches below the ground line
G_F, G_C, G_ROOF, G_PARAPET = -0.15, 3.45, 3.75, 4.20     # garage floor, ceiling (roof slab 3.45..3.75), parapet top

# ---------------------------------------------------------------- the envelope
XO, YO = 8.00, 6.00                        # main block, outer faces
XI, YI = 7.65, 5.65                        # inner faces (0.35 walls: 0.175 board-formed concrete + core + plaster)
GLASS_IN = 0.115                           # window glass line, from the outer face
PAR_IN = 7.825                             # parapet inner face (x), PAR_IN_Y for y
PAR_IN_Y = 5.825
UG_XW = -2.30                              # basement: under the east part, west wall -2.30..-1.95
UG_XWI = -1.95
TOWER = dict(x0=-1.95, x1=1.95, xi0=-1.70, xi1=1.70, y0=1.00, yi0=1.15, yi1=6.75, y1=7.00)   # stair tower (outer/inner)
GARAGE = dict(x0=-18.00, x1=-8.00, xi0=-17.70, y0=-5.00, y1=5.00, yi0=-4.70, yi1=4.70)          # garage hall
CORR = dict(y0=-1.00, y1=1.00, ws0=-1.15, wn1=1.15)       # corridor (all floors) and its walls -1.15..-1.00, 1.00..1.15
CHIMNEY = dict(x0=7.15, x1=7.65, y0=-1.65, y1=-1.15, top=8.20)  # brick flue in the SE corner of the corridor wall

# ---------------------------------------------------------------- rooms = light zones (Forest_Layout lighting.rooms)
# name: (level, x0, x1, y0, y1, floor, ceiling, light layer, finishes)
#   floor: lino (chequer), lino_g (olive), carpet, tile_f (lobby), tile_k (kitchen), tile_b (bath), raised, boards, conc
#   walls: dict(dado=height or 0, dado_col, stripe=bool, tile=height, veneer=height, top=paint colour key, bare=True)
ROOMS = {
    'Windfang':       dict(level='EG', x0=-7.65, x1=-5.25, y0=-5.65, y1=-1.15, f=EG_F, c=EG_C, layer=7, floor='tile_f',
                           walls=dict(dado=1.50, dado_col='brown', top='cream'), ceil='plaster'),
    'Leitstand':      dict(level='EG', x0=-5.10, x1=7.65, y0=-5.65, y1=-1.15, f=EG_F, c=EG_SC, layer=4, floor='carpet',
                           walls=dict(dado=1.35, dado_col='brown', top='cream'), ceil='tiles'),
    'Flur_EG':        dict(level='EG', x0=-7.65, x1=7.65, y0=-1.00, y1=1.00, f=EG_F, c=EG_SC, layer=2, floor='lino',
                           walls=dict(dado=1.50, dado_col='cream', stripe=True, top='cream'), ceil='tiles'),
    'Lager':          dict(level='EG', x0=-7.65, x1=-1.95, y0=1.15, y1=5.65, f=EG_F, c=EG_C, layer=5, floor='conc',
                           walls=dict(dado=1.50, dado_col='grey', top='white'), ceil='plaster'),
    'Serverraum':     dict(level='EG', x0=1.95, x1=7.65, y0=1.15, y1=5.65, f=EG_F, c=EG_SC, layer=8, floor='raised',
                           walls=dict(dado=0, top='white'), ceil='tiles'),
    'Garage':         dict(level='EG', x0=-17.70, x1=-8.00, y0=-4.70, y1=4.70, f=G_F, c=G_C, layer=6, floor='conc_g',
                           walls=dict(bare=True), ceil='boards'),
    'Kaserne':        dict(level='OG', x0=-7.65, x1=-1.60, y0=-5.65, y1=-1.15, f=OG_F, c=OG_C, layer=8, floor='lino_g',
                           walls=dict(dado=1.50, dado_col='olive', top='cream'), ceil='plaster'),
    'Kueche':         dict(level='OG', x0=-1.45, x1=7.65, y0=-5.65, y1=-1.15, f=OG_F, c=OG_C, layer=7, floor='tile_k',
                           walls=dict(dado=1.50, dado_col='brown', top='cream'), ceil='plaster'),
    'Flur_OG':        dict(level='OG', x0=-7.65, x1=7.65, y0=-1.00, y1=1.00, f=OG_F, c=OG_C, layer=3, floor='lino',
                           walls=dict(dado=1.50, dado_col='cream', stripe=True, top='cream'), ceil='plaster'),
    'Waschraum':      dict(level='OG', x0=-7.65, x1=-1.95, y0=1.15, y1=5.65, f=OG_F, c=OG_C, layer=9, floor='tile_b',
                           walls=dict(tile=2.00, top='cream'), ceil='plaster'),
    'Stationsleiter': dict(level='OG', x0=1.95, x1=7.65, y0=1.15, y1=5.65, f=OG_F, c=OG_C, layer=4, floor='boards',
                           walls=dict(veneer=1.24, top='cream'), ceil='plaster'),
    'Heizung':        dict(level='UG', x0=-1.95, x1=7.65, y0=-5.65, y1=-1.15, f=UG_F, c=UG_C, layer=5, floor='conc',
                           walls=dict(dado=0, top='white'), ceil='plaster'),
    'Flur_UG':        dict(level='UG', x0=-1.95, x1=7.65, y0=-1.00, y1=1.00, f=UG_F, c=UG_C, layer=7, floor='conc',
                           walls=dict(dado=1.50, dado_col='grey', top='white'), ceil='plaster'),
    'Schaltraum':     dict(level='UG', x0=1.95, x1=7.65, y0=1.15, y1=5.65, f=UG_F, c=UG_C, layer=9, floor='conc',
                           walls=dict(dado=1.50, dado_col='grey', top='white'), ceil='plaster'),
    'Treppenhaus':    dict(level='ALL', x0=-1.70, x1=1.70, y0=1.15, y1=6.75, f=UG_F, c=TOWER_CEIL, layer=6,
                           floor='conc', walls=dict(bare=True), ceil='conc'),
}
EXTERIOR_LAYER = 1

# ---------------------------------------------------------------- walls (structural; the rooms' faces are built per room)
# (axis of the normal, a0, a1 = the slab across, u0, u1 = along, z0, z1); x-walls run along y, y-walls along x
WALLS = [
    # the main block's envelope (ground and upper floor) and its basement part (below the ground only the rooms' faces)
    ('y', -YO, -YI, -XO, XO, PLINTH_BOT, PARAPET), ('y', YI, YO, -XO, XO, PLINTH_BOT, PARAPET),
    ('x', -XO, -XI, -YO, YO, PLINTH_BOT, PARAPET), ('x', XI, XO, -YO, YO, PLINTH_BOT, PARAPET),
    ('y', -YO, -YI, UG_XW, XO, UG_F - 0.30, PLINTH_BOT), ('y', YI, YO, UG_XW, XO, UG_F - 0.30, PLINTH_BOT),
    ('x', XI, XO, -YO, YO, UG_F - 0.30, PLINTH_BOT), ('x', UG_XW, UG_XWI, -YO, YO, UG_F - 0.30, PLINTH_BOT),
    # corridor walls on every floor
    ('y', -1.15, -1.00, -XI, XI, UG_F, OG_C), ('y', 1.00, 1.15, -XI, XI, UG_F, OG_C),
    # partitions
    ('x', -5.25, -5.10, -YI, -1.15, EG_F, EG_C),          # Windfang | Leitstand
    ('x', -1.60, -1.45, -YI, -1.15, OG_F, OG_C),          # Kaserne | Kueche
    # the stair tower (to TOWER_TOP)
    ('x', -1.95, -1.70, 1.15, 7.00, UG_F - 0.30, TOWER_TOP), ('x', 1.70, 1.95, 1.15, 7.00, UG_F - 0.30, TOWER_TOP),
    ('y', 6.75, 7.00, -1.95, 1.95, UG_F - 0.30, TOWER_TOP), ('y', 1.00, 1.15, -1.95, 1.95, OG_C, TOWER_TOP),
    # garage hall
    ('x', GARAGE['x0'], GARAGE['xi0'], -5.00, 5.00, PLINTH_BOT, G_PARAPET),
    ('y', -5.00, -4.70, -18.00, -8.00, PLINTH_BOT, G_PARAPET), ('y', 4.70, 5.00, -18.00, -8.00, PLINTH_BOT, G_PARAPET),
]

# ---------------------------------------------------------------- doors (IX parts: the Update 3 names, pivots, swings)
# wall: ('x'|'y', the wall's a0, a1), u0..u1 along, z0..z1; hinge = the hinge side's u; ix: the part; kind: the leaf
DOORS = {
    'IX_MainDoor_1':   dict(wall=('y', -YO, -YI), u=(-7.00, -5.90), z=(EG_F, 2.20), hinge=-6.9675, piv_y=-5.9625,
                            kind='steel_vision', room='Windfang', out='Exterior', swing=90,
                            # the inner face is set back 11 cm round the door: the bar IX_MainDoorBar_311 (pivot y -5.705,
                            # 7 cm thick) lies in this niche across the door and swings up inside it (to z 2.57)
                            niche=dict(u=(-7.24, -5.66), z=(EG_F, 2.62), d=0.11)),
    'IX_ExitDoor_2':   dict(wall=('x', XI, XO), u=(-0.55, 0.55), z=(EG_F, 2.20), hinge=-0.5175, piv_x=7.9625,
                            kind='steel_panic', room='Flur_EG', out='Exterior', swing=90),
    'IX_Door_3':       dict(wall=('x', -XO, -XI), u=(-0.55, 0.55), z=(EG_F, 2.10), hinge=-0.5175, piv_x=-7.9625,
                            kind='steel', room='Flur_EG', out='Garage', swing=95),
    'IX_Door_4':       dict(wall=('x', -XO, -XI), u=(3.00, 3.95), z=(EG_F, 2.10), hinge=3.9175, piv_x=-7.9625,
                            kind='steel', room='Lager', out='Garage', swing=95),
    'IX_Door_5':       dict(wall=('y', -1.15, -1.00), u=(-7.00, -5.90), z=(EG_F, 2.20), hinge=-5.9275, piv_y=-1.0325,
                            kind='glass', room='Windfang', out='Flur_EG', swing=95),
    'IX_Door_6':       dict(wall=('y', -1.15, -1.00), u=(-3.50, -2.50), z=(EG_F, 2.10), hinge=-3.4725, piv_y=-1.1175,
                            kind='room', room='Leitstand', out='Flur_EG', swing=95),
    'IX_Door_7':       dict(wall=('y', 1.00, 1.15), u=(-5.50, -4.50), z=(EG_F, 2.10), hinge=-5.4725, piv_y=1.1175,
                            kind='room', room='Lager', out='Flur_EG', swing=95),
    'IX_Door_8':       dict(wall=('y', 1.00, 1.15), u=(-0.60, 0.60), z=(EG_F, 2.20), hinge=-0.5675, piv_y=1.1125,
                            kind='fire', room='Treppenhaus', out='Flur_EG', swing=95),
    'IX_Door_9':       dict(wall=('y', 1.00, 1.15), u=(2.60, 3.50), z=(EG_F, 2.10), hinge=3.4675, piv_y=1.1125,
                            kind='room', room='Serverraum', out='Flur_EG', swing=95),
    'IX_Door_10':      dict(wall=('y', -1.15, -1.00), u=(-3.50, -2.50), z=(OG_F, OG_F + 2.10), hinge=-3.4725,
                            piv_y=-1.1175, kind='room', room='Kaserne', out='Flur_OG', swing=95),
    'IX_Door_11':      dict(wall=('y', 1.00, 1.15), u=(-5.50, -4.60), z=(OG_F, OG_F + 2.10), hinge=-5.4725,
                            piv_y=1.1175, kind='room', room='Waschraum', out='Flur_OG', swing=95),
    'IX_Door_12':      dict(wall=('y', 1.00, 1.15), u=(-0.60, 0.60), z=(OG_F, OG_F + 2.20), hinge=-0.5675,
                            piv_y=1.1125, kind='fire', room='Treppenhaus', out='Flur_OG', swing=95),
    'IX_Door_13':      dict(wall=('y', 1.00, 1.15), u=(2.60, 3.50), z=(OG_F, OG_F + 2.10), hinge=3.4725,
                            piv_y=1.1175, kind='room', room='Stationsleiter', out='Flur_OG', swing=95),
    'IX_Door_14':      dict(wall=('y', -1.15, -1.00), u=(2.00, 2.95), z=(UG_F, UG_F + 2.10), hinge=2.0325,
                            piv_y=-1.0375, kind='fire', room='Heizung', out='Flur_UG', swing=95),
    'IX_Door_15':      dict(wall=('y', 1.00, 1.15), u=(-0.60, 0.60), z=(UG_F, UG_F + 2.20), hinge=-0.5675,
                            piv_y=1.1125, kind='fire', room='Treppenhaus', out='Flur_UG', swing=95),
    'IX_Door_16':      dict(wall=('y', 1.00, 1.15), u=(3.60, 4.55), z=(UG_F, UG_F + 2.10), hinge=3.6325,
                            piv_y=1.1125, kind='steel', room='Schaltraum', out='Flur_UG', swing=95),
    'IX_RoofDoor_17':  dict(wall=('y', 1.00, 1.15), u=(-0.60, 0.60), z=(ROOF + 0.01, ROOF + 2.20), hinge=-0.5675,
                            piv_y=1.0375, kind='steel', room='Treppenhaus', out='Exterior', swing=95),
    'IX_GarageDoor_19': dict(wall=('y', -5.00, -4.70), u=(-11.30, -10.35), z=(G_F, G_F + 2.10), hinge=-11.2675,
                             piv_y=-4.9625, kind='steel', room='Garage', out='Exterior', swing=90),
}
GARAGE_GATE = dict(name='IX_GarageGate_18', u=(-16.60, -13.10), z=(G_F, 2.85), piv=(-16.58, -4.66, 2.85), swing=85)
KITCHEN_PASS = dict(wall=('y', -1.15, -1.00), u=(1.00, 2.60), z=(OG_F, OG_F + 2.20))   # open doorway, no leaf

# ---------------------------------------------------------------- windows (glass panes = the Update 3 panes)
# wall, opening u0..u1 / z0..z1 (frame 0.05 round the panes), panes along u, shutter curtains (IX), room inside
WINDOWS = [
    dict(name='W_Leitstand_S', wall=('y', -YO, -YI), u=(-4.40, 7.65), z=(0.80, 2.75), room='Leitstand',
         panes=[(-4.350, -3.047), (-2.997, -1.719), (-1.669, -0.392), (-0.342, 0.936), (0.986, 2.264), (2.314, 3.592),
                (3.642, 4.919), (4.969, 6.247), (6.297, 7.600)], transom=True,
         shutters=[('IX_Shutter_Leitstand_103', -4.388, -1.700), ('IX_Shutter_Leitstand_104', -1.688, 0.955),
                   ('IX_Shutter_Leitstand_105', 0.967, 3.611), ('IX_Shutter_Leitstand_106', 3.623, 6.266),
                   ('IX_Shutter_Leitstand_107', 6.278, 7.638)], box=False),
    dict(name='W_Leitstand_E', wall=('x', XI, XO), u=(-5.50, -1.80), z=(0.80, 2.75), room='Leitstand',
         panes=[(-5.450, -4.275), (-4.225, -3.075), (-3.025, -1.850)], transom=True,
         shutters=[('IX_Shutter_Leitstand_110', -5.488, -1.812)], box=False),
    dict(name='W_Lager_N', wall=('y', YI, YO), u=(-6.60, -3.20), z=(1.40, 2.30), room='Lager',
         panes=[(-6.550, -5.475), (-5.425, -4.375), (-4.325, -3.250)],
         shutters=[('IX_Shutter_Lager_108', -6.588, -3.212)], box=True),
    dict(name='W_Kaserne_S1', wall=('y', -YO, -YI), u=(-7.00, -4.60), z=(4.30, 5.60), room='Kaserne',
         panes=[(-6.950, -5.825), (-5.775, -4.650)], shutters=[('IX_Shutter_Kaserne_111', -6.988, -4.612)], box=True),
    dict(name='W_Kaserne_S2', wall=('y', -YO, -YI), u=(-4.20, -2.20), z=(4.30, 5.60), room='Kaserne',
         panes=[(-4.150, -3.225), (-3.175, -2.250)], shutters=[('IX_Shutter_Kaserne_113', -4.188, -2.212)], box=True),
    dict(name='W_Kueche_S', wall=('y', -YO, -YI), u=(-0.80, 7.00), z=(4.30, 5.60), room='Kueche',
         panes=[(-0.750, 0.508), (0.558, 1.792), (1.842, 3.075), (3.125, 4.358), (4.408, 5.642), (5.692, 6.950)],
         shutters=[('IX_Shutter_Kueche_115', -0.788, 1.811), ('IX_Shutter_Kueche_116', 1.823, 4.377),
                   ('IX_Shutter_Kueche_117', 4.389, 6.988)], box=True),
    dict(name='W_Kueche_E', wall=('x', XI, XO), u=(-5.00, -2.00), z=(4.30, 5.60), room='Kueche',
         panes=[(-4.950, -3.525), (-3.475, -2.050)], shutters=[('IX_Shutter_Kueche_122', -4.988, -2.012)], box=True),
    dict(name='W_Flur_OG_E', wall=('x', XI, XO), u=(-0.60, 0.60), z=(4.30, 5.60), room='Flur_OG',
         panes=[(-0.550, 0.550)], shutters=[('IX_Shutter_Flur_OG_123', -0.588, 0.588)], box=True),
    dict(name='W_Flur_OG_W', wall=('x', -XO, -XI), u=(-0.60, 0.60), z=(4.40, 5.60), room='Flur_OG',
         panes=[(-0.550, 0.550)], shutters=[('IX_Shutter_Flur_OG_126', -0.588, 0.588)], box=True),
    dict(name='W_Waschraum_N', wall=('y', YI, YO), u=(-6.60, -4.20), z=(5.00, 5.65), room='Waschraum',
         panes=[(-6.550, -5.425), (-5.375, -4.250)], shutters=[('IX_Shutter_Waschraum_118', -6.588, -4.212)], box=True),
    dict(name='W_Stationsleiter_N', wall=('y', YI, YO), u=(2.80, 6.80), z=(4.30, 5.60), room='Stationsleiter',
         panes=[(2.850, 4.125), (4.175, 5.425), (5.475, 6.750)],
         shutters=[('IX_Shutter_Stationsleiter_120', 2.812, 5.444), ('IX_Shutter_Stationsleiter_121', 5.456, 6.788)],
         box=True),
    dict(name='W_Stationsleiter_E', wall=('x', XI, XO), u=(2.20, 5.00), z=(4.30, 5.60), room='Stationsleiter',
         panes=[(2.250, 3.575), (3.625, 4.950)], shutters=[('IX_Shutter_Stationsleiter_125', 2.212, 4.988)], box=True),
    # no shutters: the garage's high windows, the stair tower's two glass slits, the server room's glazed partition
    dict(name='W_Garage_N', wall=('y', 4.70, 5.00), u=(-16.40, -11.40), z=(1.95, 2.95), room='Garage',
         panes=[(-16.350, -15.150), (-15.100, -13.925), (-13.875, -12.700), (-12.650, -11.450)], shutters=[], box=False),
    dict(name='W_Garage_W', wall=('x', -18.00, -17.70), u=(-2.40, 2.40), z=(1.95, 2.95), room='Garage',
         panes=[(-2.350, -1.200), (-1.150, -0.025), (0.025, 1.150), (1.200, 2.350)], shutters=[], box=False),
    dict(name='W_Tower_N1', wall=('y', 6.75, 7.00), u=(-0.85, -0.60), z=(0.60, 8.90), room='Treppenhaus',
         panes=[(-0.800, -0.650)], shutters=[], box=False, slit=True),
    dict(name='W_Tower_N2', wall=('y', 6.75, 7.00), u=(0.60, 0.85), z=(0.60, 8.90), room='Treppenhaus',
         panes=[(0.650, 0.800)], shutters=[], box=False, slit=True),
    dict(name='W_Server_Glazing', wall=('y', 1.00, 1.15), u=(4.00, 7.20), z=(1.00, 2.30), room='Serverraum',
         panes=[(4.045, 5.577), (5.622, 7.155)], shutters=[], box=False, internal='Flur_EG'),
]
for _w in WINDOWS:                         # the glass line from the outer face (Update 3's panes)
    _w.setdefault('glass_in', 0.075 if _w.get('internal') else 0.09 if 'Garage' in _w['name'] else
                  0.125 if 'Tower' in _w['name'] else GLASS_IN)
SHUTTER_ROLLED = {'Leitstand': 0.0284, 'Lager': 0.05, 'Kaserne': 0.0427, 'Kueche': 0.0427, 'Flur_OG_E': 0.0427,
                  'Flur_OG_W': 0.0463, 'Waschraum': 0.05, 'Stationsleiter': 0.0427}

# ---------------------------------------------------------------- the stair (U-stair in the tower, per storey)
# flight A rises north on the west half (x -1.70..-0.15) from y 2.55, landing at the north (y 5.07..6.70, the full width),
# flight B rises south on the east half (x 0.15..1.70) to the floor landing (y 1.15..2.55); 10 risers per flight,
# going 0.28; basement storey 0.15 risers, the upper ones 0.17
STAIR = dict(xa=(-1.70, -0.15), xb=(0.15, 1.70), y_start=2.55, going=0.28, n=10, mid=(5.07, 6.70), eye=(-0.15, 0.15))
STOREYS = [(UG_F, EG_F), (EG_F, OG_F), (OG_F, ROOF)]          # the last flight pair runs up to the roof door

# ---------------------------------------------------------------- Update 3 axes (Unity) of the doors, the belt winders
DOOR_AXES_U3 = {'IX_MainDoor_1': (0, 1, 0), 'IX_ExitDoor_2': (0, 1, 0), 'IX_Door_3': (0, -1, 0), 'IX_Door_4': (0, 1, 0),
                'IX_Door_5': (0, 1, 0), 'IX_Door_6': (0, 1, 0), 'IX_Door_7': (0, -1, 0), 'IX_Door_8': (0, -1, 0),
                'IX_Door_9': (0, 1, 0), 'IX_Door_10': (0, 1, 0), 'IX_Door_11': (0, -1, 0), 'IX_Door_12': (0, -1, 0),
                'IX_Door_13': (0, 1, 0), 'IX_Door_14': (0, -1, 0), 'IX_Door_15': (0, -1, 0), 'IX_Door_16': (0, -1, 0),
                'IX_RoofDoor_17': (0, 1, 0), 'IX_GarageDoor_19': (0, 1, 0)}
# pivot (on the inner wall face), n = the wall's normal into the room, the Unity axis, the curtain(s) driven, the box's
# bottom (the window head) the strap runs up to
WINDERS = {
    'IX_ShutterWinder_Lager_109': dict(pivot=(-3.09, 5.646, 1.00), n=(0, -1, 0), axis_u=(0, 0, -1), room='Lager',
                                       drives=['IX_Shutter_Lager_108'], top=2.30),
    'IX_ShutterWinder_Kaserne_112': dict(pivot=(-7.11, -5.646, 4.40), n=(0, 1, 0), axis_u=(0, 0, 1), room='Kaserne',
                                         drives=['IX_Shutter_Kaserne_111'], top=5.60),
    'IX_ShutterWinder_Kaserne_114': dict(pivot=(-2.09, -5.646, 4.40), n=(0, 1, 0), axis_u=(0, 0, 1), room='Kaserne',
                                         drives=['IX_Shutter_Kaserne_113'], top=5.60),
    'IX_ShutterWinder_Waschraum_119': dict(pivot=(-4.09, 5.646, 4.40), n=(0, -1, 0), axis_u=(0, 0, -1), room='Waschraum',
                                           drives=['IX_Shutter_Waschraum_118'], top=5.65),
    'IX_ShutterWinder_Flur_OG_124': dict(pivot=(7.646, 0.71, 4.40), n=(-1, 0, 0), axis_u=(-1, 0, 0), room='Flur_OG',
                                         drives=['IX_Shutter_Flur_OG_123'], top=5.60),
    'IX_ShutterWinder_Flur_OG_127': dict(pivot=(-7.646, 0.71, 4.40), n=(1, 0, 0), axis_u=(1, 0, 0), room='Flur_OG',
                                         drives=['IX_Shutter_Flur_OG_126'], top=5.60),
}
