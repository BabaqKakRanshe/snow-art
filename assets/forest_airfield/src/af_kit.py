"""Forest airfield kit (forest_airfield 1.0, built locally with tools/snow_style 27.10): what the hidden airstrip by the east
road needs that the project does not have yet - ten prefabs, each in its own frame (Blender: z up, the front -y, metres;
origin on the ground, z = 0; Unity (x, y, z) -> (-x, z, -y), the front -> +Z). Everything else is reused (README of the
topic): BunkerHangar + PlaneTarp + UtilityPlane, Sky Island's Windsock / PAPI / Guard_Hut / Flood_Mast / Barrier_Boom /
Earth_Shelter, the KPP's road blocks and signs.
  RWY_Slab       a runway module 18 x 10 m of old concrete slabs (3 x 2 slabs, 6 x 5 m), a faded centre-line dash on its
                 -y half, a 0.30 m skirt down the sides; origin = the middle of its top, +y along the runway
  RWY_SlabWorn   the same module, worn: cracks, weeds and old snow in the joints, an asphalt patch
  RWY_Threshold  the runway's end module: the end bar on its -y edge (the runway ends there), eight threshold stripes
  RWY_Num17      the designator 17 painted after the threshold (heading 175 deg), readable from the -y side
  RWY_Num35      the designator 35 for the other end (the module is turned 180 deg there)
  AF_EdgeLight   elevated runway edge light: a concrete pad with four anchor bolts, a frangible stand with a coupling and
                 a cable gland, a lamp body with an amber ribbed dome (Lamp_Edge, Lens_Edge, Glow_Edge, LIGHT_Edge)
  AF_ThresholdLight  the same with a green dome (Lamp_Thr, Lens_Thr, Glow_Thr, LIGHT_Thr)
  AF_EdgeMarker  a 1 m red and white marker post on a concrete foot
  AF_Sign        the station's pointer at the turn-off from the east road: FLUGPLATZ / AIRFIELD on the arrow board
  AF_HangarPlug  the bricked-up back opening of BunkerHangar (5.0 x 4.6 m): hollow concrete blocks, a locked steel door
                 with the plate KEIN ZUTRITT / NO ENTRY; origin = the hangar's Link_BlastDoor (no rotation)
Each root's parts / sockets are given in its own frame (the contract); in the .blend the roots stand apart (DISPLAY)."""
import math
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_y, quad, KBS, CONTRACT, LAMPS
from gen_kit import Z_STEELBLK
from van2_kit import ZERO
import af_tex as AT

uv = AT.uv
TAU = 2 * math.pi
RWY = ['RWY_Slab', 'RWY_SlabWorn', 'RWY_Threshold', 'RWY_Num17', 'RWY_Num35']
PROPS = ['AF_EdgeLight', 'AF_ThresholdLight', 'AF_EdgeMarker', 'AF_Sign']
ROOTS = RWY + PROPS + ['AF_HangarPlug']
RWY_STEP = 22.0
DISPLAY = {n: Vector(((i - 2) * RWY_STEP, 14.0, 0.0)) for i, n in enumerate(RWY)}
DISPLAY.update({'AF_EdgeLight': Vector((-8.0, -6.0, 0.0)), 'AF_ThresholdLight': Vector((-6.0, -6.0, 0.0)),
                'AF_EdgeMarker': Vector((-4.0, -6.0, 0.0)), 'AF_Sign': Vector((-1.5, -6.0, 0.0)),
                'AF_HangarPlug': Vector((8.0, -4.0, 0.0))})
ROOT_OF = {}
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot_xyz_deg or None) in the root frame

# ---------------------------------------------------------------- zones
(Z_RPLAIN, Z_RWORN, Z_RTHR, Z_RN17, Z_RN35, Z_RSKIRT) = range(180, 186)
RWY_ZONE = {'RWY_Slab': Z_RPLAIN, 'RWY_SlabWorn': Z_RWORN, 'RWY_Threshold': Z_RTHR, 'RWY_Num17': Z_RN17, 'RWY_Num35': Z_RN35}
(Z_PAD, Z_STAND, Z_LAMPB, Z_CABLE, Z_MARK, Z_SPOST, Z_SBOARD) = range(190, 197)
(Z_BLOCK, Z_PDOOR, Z_PFRAME) = range(200, 203)

# runway module: half width, half length, skirt depth, slab grid
RW, RL, SKIRT = 9.0, 5.0, 0.30
SLAB_X = (-9.0, -3.0, 3.0, 9.0)
SLAB_Y = (-5.0, 0.0, 5.0)


def reg(name, atlas, root):
    ROOT_OF[name] = root
    return kb(name, atlas)


def lathe_uv(k, c, h0, h1, rect, axis):
    """cylindrical UVs on every face of k (lens domes)"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = rect
    for f in k.bm.faces:
        for l in f.loops:
            d = l.vert.co - c
            a = (math.atan2(d.dot(e2), d.dot(e1)) / TAU) % 1.0
            t = min(max((d.dot(ax) - h0) / (h1 - h0), 0.0), 1.0)
            l[k.uvl].uv = (u0 + (u1 - u0) * (0.05 + 0.9 * a), v0 + (v1 - v0) * t)


# ================================================================ runway modules
def build_runway_module(name):
    k = reg(name, 'Runway', name)
    zt = RWY_ZONE[name]
    for xa, xb in zip(SLAB_X[:-1], SLAB_X[1:]):                       # the slabs' tops (joints are painted grooves)
        for ya, yb in zip(SLAB_Y[:-1], SLAB_Y[1:]):
            face(k, [(xa, ya, 0.0), (xb, ya, 0.0), (xb, yb, 0.0), (xa, yb, 0.0)], zt, (0, 0, 1))
    for sx in (-1, 1):                                                # the skirt: the slab edge down into the ground
        face(k, [(sx * RW, -RL, -SKIRT), (sx * RW, RL, -SKIRT), (sx * RW, RL, 0.0), (sx * RW, -RL, 0.0)], Z_RSKIRT, (sx, 0, 0))
    for sy in (-1, 1):
        face(k, [(-RW, sy * RL, -SKIRT), (RW, sy * RL, -SKIRT), (RW, sy * RL, 0.0), (-RW, sy * RL, 0.0)], Z_RSKIRT, (0, sy, 0))
    notes = {'RWY_Slab': 'plain slabs, a faded centre-line dash on the -y half (dash 5 m, gap 5 m along the runway)',
             'RWY_SlabWorn': 'the same, worn: cracks, weeds and old snow in the joints, a dark asphalt patch',
             'RWY_Threshold': 'the runway end: end bar on the -y edge, eight stripes; the -y edge is the end of the paving',
             'RWY_Num17': 'designator 17 (heading 175), readable from the -y side; goes right after the threshold',
             'RWY_Num35': 'designator 35 for the other end; the module is turned 180 deg there'}
    part(name, 'static', (0, 0, 0), note=f'runway module 18 x 10 m (root): origin = the middle of its top (z = 0), +y along the '
                                          f'runway, the skirt 0.30 m down; {notes[name]}')
    socket(f'Snap_{name}_N', (0.0, RL, 0.0), 'snap', parent=name, note='the +y edge: the next module\'s -y edge goes here')
    BOXES.append((f'{name}_Top', name, (-RW, RW, -RL, RL, -SKIRT, 0.0), None))


# ================================================================ the lights (edge amber, threshold green)
LENS_Z = 0.29


def build_light(root, tag, lens_kind, glow_tile):
    k = reg(root, 'AFProps', root)
    box6(k, (-0.20, -0.20, -0.12), (0.20, 0.20, 0.03), Z_PAD, skip=('-z',))             # the pad, set into the ground
    for sx in (-1, 1):                                                                 # four anchor bolts with nuts
        for sy in (-1, 1):
            c = Vector((sx * 0.15, sy * 0.15, 0.03))
            k.box(c.x - 0.016, c.x + 0.016, c.y - 0.016, c.y + 0.016, 0.03, 0.045, Z_STEELBLK)
            k.cyl(c + Vector((0, 0, 0.015)), c + Vector((0, 0, 0.035)), 0.007, Z_STEELBLK, 5)
    k.cyl((0, 0, 0.03), (0, 0, 0.045), 0.055, Z_STAND, 10)                            # the flange
    k.cyl((0, 0, 0.045), (0, 0, 0.245), 0.022, Z_STAND, 8)                             # the frangible stand
    k.cyl((0, 0, 0.10), (0, 0, 0.145), 0.031, Z_STAND, 8)                              # its breakaway coupling
    for a in (0, 180):                                                                 # the coupling's two clamp screws
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.cyl(Vector((0, 0, 0.122)) + d * 0.030, Vector((0, 0, 0.122)) + d * 0.040, 0.006, Z_STEELBLK, 5)
    k.cyl((0.022, 0.0, 0.075), (0.050, 0.0, 0.075), 0.011, Z_STEELBLK, 6)              # the cable gland
    k.tube([(0.050, 0.0, 0.075), (0.085, 0.0, 0.070), (0.115, 0.015, 0.050), (0.135, 0.035, 0.032)], 0.007, Z_CABLE, 5)
    L = reg('Lamp_' + tag, 'AFProps', root)                                            # lamp body: cup, rim band, three clamps
    L.cyl((0, 0, 0.245), (0, 0, 0.270), 0.028, Z_LAMPB, 12, r2=0.072)
    L.cyl((0, 0, 0.270), (0, 0, LENS_Z + 0.008), 0.078, Z_LAMPB, 12)
    for a in (30, 150, 270):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        c = d * 0.082 + Vector((0, 0, LENS_Z + 0.004))
        L.box(c.x - 0.010, c.x + 0.010, c.y - 0.010, c.y + 0.010, c.z - 0.016, c.z + 0.016, Z_STEELBLK)
    part('Lamp_' + tag, 'static', (0, 0, 0.27), parent=root, note='the lamp body on the stand; the dome and the halo are its '
                                                                   f'children; the light LIGHT_{tag}')
    c = Vector((0, 0, LENS_Z + 0.008))
    Ln = reg('Lens_' + tag, 'lens:' + lens_kind, root)
    Ln.lathe(c, (0, 0, 1), [(0.0, 0.070), (0.030, 0.068), (0.058, 0.056), (0.080, 0.036), (0.092, 0.012)], ZERO, 12, cap0=False)
    lathe_uv(Ln, c, 0.0, 0.092, uv('l_edge' if lens_kind == 'edge' else 'l_thr'), (0, 0, 1))
    part('Lens_' + tag, 'static', c, parent='Lamp_' + tag,
         note=f'the ribbed glass dome: M_AF_Lamp_{lens_kind.capitalize()} (lit) / M_AF_Lamp_{lens_kind.capitalize()}_Off')
    g = c + Vector((0, 0, 0.045))
    Gw = reg('Glow_' + tag, 'glow', root)
    quad(Gw, g + Vector((0, -0.09, 0)), (0, -1, 0), 0.70, 0.70, uv(glow_tile))
    quad(Gw, g + Vector((0.09, 0, 0)), (1, 0, 0), 0.70, 0.70, uv(glow_tile))
    part('Glow_' + tag, 'static', g, parent='Lamp_' + tag, note='halo cards: additive, unlit; shown when the light is on')
    LAMPS.append((tag, g, (0, 0, 1), lens_kind, (0, -1, 0)))
    what = 'amber: along both runway edges every 60 m' if lens_kind == 'edge' else 'green: a row across the threshold, at its -y edge'
    part(root, 'static', (0, 0, 0), note=f'elevated runway light (root), {what}: origin = the middle of the pad on the ground; the pad '
                                         f'is set 0.12 m into the ground, the dome top at 0.39 m')
    BOXES.extend([(f'{tag}_Pad', root, (-0.20, 0.20, -0.20, 0.20, -0.12, 0.03), None),
                  (f'{tag}_Head', root, (-0.08, 0.08, -0.08, 0.08, 0.03, 0.39), None)])


# ================================================================ the marker post
def build_marker():
    k = reg('AF_EdgeMarker', 'AFProps', 'AF_EdgeMarker')
    box6(k, (-0.15, -0.15, -0.12), (0.15, 0.15, 0.04), Z_PAD, skip=('-z',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = Vector((sx * 0.10, sy * 0.10, 0.04))
            k.box(c.x - 0.014, c.x + 0.014, c.y - 0.014, c.y + 0.014, 0.04, 0.055, Z_STEELBLK)
    box6(k, (-0.065, -0.065, 0.04), (0.065, 0.065, 0.05), Z_STEELBLK, skip=('-z',))     # the base plate
    box6(k, (-0.04, -0.04, 0.05), (0.04, 0.04, 1.00), Z_MARK, skip=('-z',))              # the post (bands painted)
    box6(k, (-0.046, -0.046, 1.00), (0.046, 0.046, 1.02), Z_MARK)                        # the cap
    part('AF_EdgeMarker', 'static', (0, 0, 0), note='marker post (root), red-white-red bands: origin = the middle of the foot on the '
                                                     'ground; along the clearing edge and at the taxi link')
    BOXES.append(('Marker', 'AF_EdgeMarker', (-0.05, 0.05, -0.05, 0.05, 0.0, 1.02), None))


# ================================================================ the pointer at the turn-off
S_POST_TOP = 2.25
S_BOARD = dict(x0=-0.10, x1=0.86, z0=1.60, z1=1.82, y0=-0.085, y1=-0.055)


def build_sign():
    """the station pointer (the hut yard's RouteSign): a post, the arrow board FLUGPLATZ / AIRFIELD; the arrow points +x"""
    k = reg('AF_Sign', 'AFProps', 'AF_Sign')
    k.box(-0.045, 0.045, -0.045, 0.045, -0.30, S_POST_TOP, Z_SPOST)
    k.box(-0.06, 0.06, -0.06, 0.06, S_POST_TOP, S_POST_TOP + 0.025, Z_SPOST)
    b = S_BOARD
    tip = b['x1'] + 0.12
    poly = [(b['x0'], b['z0']), (b['x1'], b['z0']), (tip, (b['z0'] + b['z1']) / 2), (b['x1'], b['z1']), (b['x0'], b['z1'])]
    prism_y(k, poly, b['y0'], b['y1'], Z_SBOARD, Z_SBOARD, [Z_SBOARD] * len(poly))
    for zz in (b['z0'] + 0.05, b['z1'] - 0.05):
        k.cyl(Vector((0.0, b['y0'] - 0.004, zz)), Vector((0.0, b['y0'], zz)), 0.010, Z_STEELBLK, 6)
    Sg = reg('AF_Sign_Board', 'panel', 'AF_Sign')
    w = b['x1'] - b['x0'] - 0.04
    quad(Sg, Vector(((b['x0'] + b['x1']) / 2 + 0.01, b['y0'] - 0.0008, (b['z0'] + b['z1']) / 2)), (0, -1, 0), w, b['z1'] - b['z0'] - 0.03,
         uv('sign'))
    part('AF_Sign_Board', 'static', ((b['x0'] + b['x1']) / 2, b['y0'], (b['z0'] + b['z1']) / 2), parent='AF_Sign',
         note='FLUGPLATZ / AIRFIELD on the arrow board (panel atlas; German first, English under it)')
    part('AF_Sign', 'static', (0, 0, 0), note='the pointer at the turn-off (root): origin = the foot of the post on the ground (sunk '
                                               '0.30); the arrow points +x (into the track to the hangar), the text faces -y (the road)')
    BOXES.extend([('Sign_Post', 'AF_Sign', (-0.05, 0.05, -0.05, 0.05, 0.0, S_POST_TOP + 0.03), None),
                  ('Sign_BoardBox', 'AF_Sign', (b['x0'], tip, b['y0'], b['y1'], b['z0'], b['z1']), None)])


# ================================================================ the hangar's back opening, bricked up
P_X, P_Z = 2.5, 4.6                  # BunkerHangar back_open: half width, height
P_Y0, P_Y1 = -0.42, -0.18            # the block wall: its face 0.18 m back from the hall's back wall (inner face y -0.60)
DOOR = dict(x0=0.55, x1=1.55, z1=2.05)


def build_plug():
    k = reg('AF_HangarPlug', 'AFPlug', 'AF_HangarPlug')
    d = DOOR
    xs, zs = [-P_X, d['x0'], d['x1'], P_X], [0.0, d['z1'], P_Z]
    for i, (xa, xb) in enumerate(zip(xs[:-1], xs[1:])):               # the block face round the door opening
        for j, (za, zb) in enumerate(zip(zs[:-1], zs[1:])):
            if (i, j) == (1, 0):
                continue
            face(k, [(xa, P_Y0, za), (xb, P_Y0, za), (xb, P_Y0, zb), (xa, P_Y0, zb)], Z_BLOCK, (0, -1, 0))
    for xa, xb, za, zb, n in ((d['x0'], d['x0'], 0.0, d['z1'], (1, 0, 0)), (d['x1'], d['x1'], 0.0, d['z1'], (-1, 0, 0))):
        face(k, [(xa, P_Y0, za), (xb, P_Y1, za), (xb, P_Y1, zb), (xa, P_Y0, zb)], Z_PFRAME, n)     # the reveals (steel frame)
    face(k, [(d['x0'], P_Y0, d['z1']), (d['x1'], P_Y0, d['z1']), (d['x1'], P_Y1, d['z1']), (d['x0'], P_Y1, d['z1'])], Z_PFRAME, (0, 0, -1))
    for xa, xb in ((d['x0'] - 0.05, d['x0']), (d['x1'], d['x1'] + 0.05)):            # the frame's angles on the face
        box6(k, (xa, P_Y0 - 0.012, 0.0), (xb, P_Y0, d['z1'] + 0.05), Z_PFRAME, skip=('+y', '-z'))
    box6(k, (d['x0'] - 0.05, P_Y0 - 0.012, d['z1']), (d['x1'] + 0.05, P_Y0, d['z1'] + 0.05), Z_PFRAME, skip=('+y',))
    box6(k, (-P_X, P_Y0 - 0.06, 0.0), (P_X, P_Y0, 0.12), Z_BLOCK, skip=('+y', '-z', '-x', '+x'))    # a mortar kick at the foot
    D = reg('Plug_Door', 'AFPlug', 'AF_HangarPlug')                   # the locked steel door, set in the frame
    box6(D, (d['x0'] + 0.01, P_Y0 + 0.04, 0.01), (d['x1'] - 0.01, P_Y0 + 0.08, d['z1'] - 0.01), {'-y': Z_PDOOR, '*': Z_PFRAME},
         skip=('+y',))
    for zh in (0.35, 1.70):                                            # hinges on the left, a lever handle and a padlock hasp
        D.cyl(Vector((d['x0'] + 0.03, P_Y0 + 0.035, zh - 0.06)), Vector((d['x0'] + 0.03, P_Y0 + 0.035, zh + 0.06)), 0.014, Z_STEELBLK, 6)
    hx, hz = d['x1'] - 0.12, 1.02
    D.box(hx - 0.02, hx + 0.02, P_Y0 + 0.01, P_Y0 + 0.04, hz - 0.03, hz + 0.03, Z_STEELBLK)
    D.box(hx - 0.13, hx + 0.02, P_Y0 - 0.01, P_Y0 + 0.01, hz - 0.012, hz + 0.012, Z_STEELBLK)
    D.box(hx - 0.02, hx + 0.02, P_Y0 - 0.03, P_Y0 + 0.01, hz - 0.18, hz - 0.08, Z_STEELBLK)
    part('Plug_Door', 'static', ((d['x0'] + d['x1']) / 2, P_Y0 + 0.06, d['z1'] / 2), parent='AF_HangarPlug',
         note='the locked steel door in the block wall (static: it does not open; a hook for later)')
    Pl = reg('Plug_Plate', 'panel', 'AF_HangarPlug')
    quad(Pl, Vector(((d['x0'] + d['x1']) / 2, P_Y0 + 0.038, 1.55)), (0, -1, 0), 0.42, 0.30, uv('plate'))
    part('Plug_Plate', 'static', ((d['x0'] + d['x1']) / 2, P_Y0 + 0.038, 1.55), parent='Plug_Door',
         note='KEIN ZUTRITT / NO ENTRY enamel plate on the door (panel atlas)')
    part('AF_HangarPlug', 'static', (0, 0, 0), note='the bricked-up back opening of BunkerHangar (root): origin = the hangar\'s '
                                                     'Link_BlastDoor (the back wall\'s outer face, floor level, middle), no rotation; '
                                                     'the block face 0.18 m behind the hall\'s back wall, the door at its right')
    BOXES.extend([('Plug_Wall', 'AF_HangarPlug', (-P_X, P_X, P_Y0, 0.0, 0.0, P_Z), None)])


def build_airfield():
    for n in RWY:
        build_runway_module(n)
    build_light('AF_EdgeLight', 'Edge', 'edge', 'glow_warm')
    build_light('AF_ThresholdLight', 'Thr', 'thr', 'glow_green')
    build_marker()
    build_sign()
    build_plug()
