"""Forest network kit (forest_network 1.0, built locally with tools/snow_style 27.10): what the new forest roads, the power
lines and the runway need that the project does not have (docs/gdd/world/GROUND_PASS.md). Each prefab in its own frame
(Blender: z up, the front -y, metres; origin on the ground, z = 0; Unity (x, y, z) -> (-x, z, -y), the front -> +Z).
  NET_SnowPole     a snow pole of the Harz roads: fibreglass, 2.0 m out of the ground (0.35 m in), orange with a black
                   top and two black rings, a white reflector strip on the -y face (the road); along the forest roads and
                   both runway edges every 30 m
  NET_CulvertHead  one end of the concrete culvert under a forest road: the headwall with the pipe's mouth (1.0 m inside,
                   0.10 m wall), two splayed wing walls, the pipe going 2.2 m into the fill (+y), a dark plug inside (the
                   pipe runs on unseen), an apron slab where the creek leaves it; origin = the invert (the pipe's floor)
                   at the wall's face. Two of them face away from each other at the culvert's ends
  NET_Stone05..12  a forest compartment stone (Abteilungsstein) at the forks 5-12: rough-hewn granite, 0.75 m out of the
                   ground, a white-painted top, the fork's number cut in its -y face
  NET_Schranke     a forest track barrier (28.10, target concept_v1/L24_road_main.png): two round spruce posts 4.6 m
                   apart, a round pole across at 0.95 m, a board WALDWEG (forest track) hanging on it left of the middle;
                   origin = between the posts on the ground, the pole along x, the board faces -y (the road)
  NET_Stake        a marker stake (28.10, giant_bones QUESTIONS_2 answer 4: by each bone of the fall trail): a square
                   spruce stake 1.25 m out of the ground with a cut point, red-white barrier tape tied round it at 1.1 m,
                   one end blowing out (+x), one hanging; origin = the stake's foot on the ground
  NET_CrossWood    a graveyard cross of two squared timbers (1.15 m out of the ground) with a little pent roof;
  NET_CrossIron    a thin wrought-iron cross (1.0 m) with a ring at the crossing;
  NET_GraveWall    2.0 m of a low dry-stone wall (0.55 m high, 0.5 m thick), the top uneven; ends open, segments
                   join end to end along x (28.10, target concept_v1/L21_chapel.png)
  NET_Tent         an old A-frame canvas tent (2.2 m long, 1.7 m wide, 1.15 m high), olive canvas sagging under
                   snow, two poles, guy lines to pegs; the door end (-y) half open;
  NET_FirePit      a ring of field stones (1.1 m) round charred logs and ash (28.10, target concept_v1/L23_campsite.png)
  NET_RopeLadder   a rope ladder 6 m long hanging from its top (origin = the top, the ladder goes down -z), wooden rungs
                   every 0.35 m, the bottom end lying a little on the snow;
  NET_Cloth        a torn canvas sheet thrown over a beam: origin = where it lies on the beam, both halves hang 1.6-2 m
  NET_MeteoHut     the weather observer's hut (28.10, target concept_v1/L15_meteo.png): plank walls 3.0 x 2.4 m, a
                   pitched tin roof, a door on +x, one window on -y (the road side) lit warm from inside; origin = the
                   middle of its floor on the ground, the window side -y
  NET_Abatis       a log barricade (Spanish rider, 28.10, target concept_v1/L11_corridor.png): a 3.6 m log along x
                   on two X-trestles of sharpened poles, 1.1 m high; origin = its middle on the ground
  NET_LogSteps     five log steps up a slope (1.4 m wide, 0.4 m tread, 0.2 m rise, along +y): origin = the first step's
                   front on the ground (target concept_v1/L18_relay.png)
  NET_BunkerPortal a small concrete portal into a slope (28.10, forest_look QUESTIONS 13 by the proposal: a second,
                   locked way into the lake bunker; target concept_v1/L09_bunker.png): a face wall 3.4 x 2.8 m with a
                   steel pressure door (DRUCKTUER), two splayed wing walls, a lamp box over the door, three steps down;
                   origin = the door's threshold on the ground, the face -y (out of the slope)
Everything else is reused: the poles (Kit_Pole, Kit_Pole_Trafo), the wires (Kit_Wire_Bare), the barriers, the pointers."""
import math
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, quad, prism_y, KBS, CONTRACT
from gen_kit import Z_STEELBLK
import net_tex as NT

uv = NT.uv
TAU = 2 * math.pi
NUMBERS = NT.NUMBERS
STONES = [f'NET_Stone{n:02d}' for n in NUMBERS]
POINTERS = {'NET_Sign_Lager': 'sign_lager', 'NET_Sign_Kapelle': 'sign_kapelle'}
ROOTS = ['NET_SnowPole', 'NET_CulvertHead'] + STONES + list(POINTERS) + ['NET_Schranke', 'NET_Stake', 'NET_CrossWood', 'NET_CrossIron', 'NET_GraveWall', 'NET_Tent', 'NET_FirePit', 'NET_RopeLadder', 'NET_Cloth', 'NET_MeteoHut', 'NET_Abatis', 'NET_LogSteps', 'NET_BunkerPortal']
DISPLAY = {'NET_SnowPole': Vector((-3.0, 0.0, 0.0)), 'NET_CulvertHead': Vector((2.0, 0.0, 0.0))}
DISPLAY.update({s: Vector((-2.0 + 0.6 * i, -3.0, 0.0)) for i, s in enumerate(STONES)})
DISPLAY.update({'NET_Sign_Lager': Vector((-4.0, 3.0, 0.0)), 'NET_Sign_Kapelle': Vector((-2.4, 3.0, 0.0)), 'NET_Schranke': Vector((3.0, 8.0, 0.0)), 'NET_Stake': Vector((6.5, 6.0, 0.0)), 'NET_CrossWood': Vector((8.0, 6.0, 0.0)),
                'NET_CrossIron': Vector((9.0, 6.0, 0.0)), 'NET_GraveWall': Vector((11.0, 6.0, 0.0)),
                'NET_Tent': Vector((14.0, 6.0, 0.0)), 'NET_FirePit': Vector((17.0, 6.0, 0.0)),
                'NET_RopeLadder': Vector((20.0, 6.0, 6.2)), 'NET_Cloth': Vector((23.0, 6.0, 2.5)), 'NET_MeteoHut': Vector((27.0, 6.0, 0.0)),
                'NET_Abatis': Vector((31.0, 6.0, 0.0)), 'NET_LogSteps': Vector((35.0, 6.0, 0.0)), 'NET_BunkerPortal': Vector((40.0, 6.0, 0.0))})
ROOT_OF = {}
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot_xyz_deg or None) in the root frame

# ---------------------------------------------------------------- zones
(Z_POLE, Z_REFL, Z_HEAD, Z_PIPE_IN, Z_PIPE_OUT, Z_APRON, Z_PLUG, Z_STONE, Z_STONE_TOP, Z_SPOST, Z_SBOARD, Z_TAPE, Z_CANVAS, Z_ASH, Z_PLANK, Z_TIN, Z_WINLIT) = range(210, 227)


def reg(name, atlas, root):
    ROOT_OF[name] = root
    return kb(name, atlas)


# ================================================================ the snow pole
POLE_R, POLE_TOP, POLE_FOOT = 0.022, 2.0, -0.35


def build_pole():
    k = reg('NET_SnowPole', 'NetProps', 'NET_SnowPole')
    k.cyl((0, 0, POLE_FOOT), (0, 0, POLE_TOP), POLE_R, Z_POLE, 8)
    k.cyl((0, 0, POLE_TOP), (0, 0, POLE_TOP + 0.015), POLE_R, Z_POLE, 8, r2=POLE_R * 0.55)       # the rounded cap
    k.box(-0.016, 0.016, -POLE_R - 0.004, -POLE_R + 0.002, 1.55, 1.75, Z_REFL)                   # reflector strip, road side
    part('NET_SnowPole', 'static', (0, 0, 0), note='snow pole (root): origin = the pole\'s axis at the ground, 0.35 m of it in '
                                                    'the ground; orange, black top 0.25 m and black rings at 1.05 and 1.35 m; the '
                                                    'reflector faces -y (the road)')
    BOXES.append(('Pole', 'NET_SnowPole', (-0.03, 0.03, -0.03, 0.03, 0.0, POLE_TOP), None))


# ================================================================ the culvert's end
PIPE_RI, PIPE_RO, PIPE_IN = 0.50, 0.60, 2.2
HW = dict(x=1.30, z=1.55, t=0.25)                 # headwall half width, height over the invert, thickness (+y)
WING = dict(len=1.25, ang=32.0, z0=1.25, z1=0.35)  # wing walls: length, splay, height at the wall and at the far end


def build_culvert():
    k = reg('NET_CulvertHead', 'NetProps', 'NET_CulvertHead')
    cz = PIPE_RI                                   # the pipe's axis over the invert (origin = the invert at the wall's face)
    seg = 16                                       # 22.5 deg: the square hole's corners fall on vertices
    ring = [(math.cos(TAU * i / seg), math.sin(TAU * i / seg)) for i in range(seg)]
    # the pipe: outer and inner barrels from just proud of the wall's face into the fill
    for i in range(seg):
        (c0, s0), (c1, s1) = ring[i], ring[(i + 1) % seg]
        mid = Vector(((c0 + c1) / 2, 0.0, (s0 + s1) / 2))
        for r, zone, sgn in ((PIPE_RO, Z_PIPE_OUT, 1.0), (PIPE_RI, Z_PIPE_IN, -1.0)):
            p = [(r * c0, -0.06, cz + r * s0), (r * c1, -0.06, cz + r * s1), (r * c1, PIPE_IN, cz + r * s1), (r * c0, PIPE_IN, cz + r * s0)]
            face(k, p, zone, mid * sgn)
        face(k, [(PIPE_RI * c0, -0.06, cz + PIPE_RI * s0), (PIPE_RO * c0, -0.06, cz + PIPE_RO * s0),
                 (PIPE_RO * c1, -0.06, cz + PIPE_RO * s1), (PIPE_RI * c1, -0.06, cz + PIPE_RI * s1)], Z_HEAD, (0, -1, 0))   # the lip
    face(k, [(PIPE_RI * c, 1.0, cz + PIPE_RI * sn) for c, sn in ring], Z_PLUG, (0, -1, 0))   # dark plug: the pipe goes on unseen
    # the headwall: round hole -> square (half side PIPE_RO) by a ring of quads, the slab round the square by four boxes
    x, z, t, s_ = HW['x'], HW['z'], HW['t'], PIPE_RO
    zb = -0.15
    def to_square(c, sn):
        m = max(abs(c), abs(sn))
        return (s_ * c / m, cz + s_ * sn / m)
    for y_, out in ((0.0, (0, -1, 0)), (t, (0, 1, 0))):
        for i in range(seg):
            (c0, s0), (c1, s1) = ring[i], ring[(i + 1) % seg]
            q0, q1 = to_square(c0, s0), to_square(c1, s1)
            face(k, [(PIPE_RO * c0, y_, cz + PIPE_RO * s0), q0[0:1] + (y_,) + q0[1:], q1[0:1] + (y_,) + q1[1:],
                     (PIPE_RO * c1, y_, cz + PIPE_RO * s1)], Z_HEAD, out)
    box6(k, (-x, 0.0, zb), (-s_, t, z), Z_HEAD, skip=('+x',))
    box6(k, (s_, 0.0, zb), (x, t, z), Z_HEAD, skip=('-x',))
    box6(k, (-s_, 0.0, cz + s_), (s_, t, z), Z_HEAD, skip=('-x', '+x', '-z'))
    box6(k, (-s_, 0.0, zb), (s_, t, cz - s_), Z_HEAD, skip=('-x', '+x', '+z'))
    box6(k, (-x - 0.04, -0.04, z), (x + 0.04, t + 0.04, z + 0.10), Z_HEAD, skip=('-z',))          # the coping
    # the wing walls: splayed out in front of the face, sloping down to the bank
    a, L, wt = math.radians(WING['ang']), WING['len'], 0.20
    for sx in (-1.0, 1.0):
        d = Vector((sx * math.sin(a), -math.cos(a), 0.0))
        n = Vector((sx * math.cos(a), math.sin(a), 0.0))
        A0 = Vector((sx * (x - wt), 0.0, zb))
        B0 = A0 + d * L
        A1, B1 = A0 + Vector((0, 0, WING['z0'] - zb)), B0 + Vector((0, 0, WING['z1'] - zb))
        A0o, B0o, A1o, B1o = A0 + n * wt, B0 + n * wt, A1 + n * wt, B1 + n * wt
        face(k, [A0, B0, B1, A1], Z_HEAD, -n)
        face(k, [A0o, A1o, B1o, B0o], Z_HEAD, n)
        face(k, [B0, B0o, B1o, B1], Z_HEAD, d)
        face(k, [A1, B1, B1o, A1o], Z_HEAD, (0, 0, 1))
    # the apron: a slab at the invert where the creek leaves the pipe
    box6(k, (-x, -1.1, -0.12), (x, 0.0, 0.0), {'+z': Z_APRON, '*': Z_HEAD}, skip=('-z', '+y'))
    part('NET_CulvertHead', 'static', (0, 0, 0), note='one end of the culvert (root): origin = the invert (the floor of the pipe, 1.0 m '
                                                       'inside) at the face of the headwall; the pipe runs +y into the fill, the creek '
                                                       'leaves along -y over the apron. Set it 0.3 m into the bed (a third of the pipe in '
                                                       'the bed: forest culverts); the second end is the same prefab turned 180 deg')
    socket('Snap_Pipe_End', (0.0, PIPE_IN, cz), 'snap', parent='NET_CulvertHead', note='where the pipe goes on unseen (into the fill)')
    BOXES.extend([('Culvert_WallL', 'NET_CulvertHead', (-x, -s_, 0.0, t, zb, z + 0.1), None),
                  ('Culvert_WallR', 'NET_CulvertHead', (s_, x, 0.0, t, zb, z + 0.1), None),
                  ('Culvert_WallTop', 'NET_CulvertHead', (-s_, s_, 0.0, t, cz + s_, z + 0.1), None),
                  ('Culvert_Apron', 'NET_CulvertHead', (-x, x, -1.1, 0.0, -0.12, 0.0), None)])


# ================================================================ the compartment stones
ST = dict(x=0.11, y=0.09, h=0.75, foot=-0.30, peak=0.06)


def build_stone(name, number, seed):
    k = reg(name, 'NetProps', name)
    rnd = [math.sin(seed * 12.9898 + i * 78.233) * 43758.5453 % 1.0 for i in range(16)]
    j = lambda i: (rnd[i] - 0.5) * 0.018                               # rough-hewn: every corner a little off
    x, y, h, f = ST['x'], ST['y'], ST['h'], ST['foot']
    # the -y face (the number's) stays flat so its panel quad lies over it everywhere; the other corners are rough
    lo = [(-x + j(0), -y, f), (x + j(2), -y, f), (x + j(4), y + j(5), f), (-x + j(6), y + j(7), f)]
    hi = [(-x + j(8), -y, h), (x + j(10), -y, h), (x + j(12), y + j(13), h), (-x + j(14), y + j(15), h)]
    for i in range(4):
        jn = (i + 1) % 4
        face(k, [lo[i], lo[jn], hi[jn], hi[i]], Z_STONE, Vector(((lo[i][0] + lo[jn][0]) / 2, (lo[i][1] + lo[jn][1]) / 2, 0)))
    peak = (0.0, 0.0, h + ST['peak'])                                    # the shallow pyramid top, painted white
    for i in range(4):
        jn = (i + 1) % 4
        face(k, [hi[i], hi[jn], peak], Z_STONE_TOP, (0, 0, 1))
    # the whole -y face from the panel atlas (granite with the number cut in at 0.46 m): a quad over the face as it really
    # stands (the corners are rough), 1.5 mm out along its normal, a little wider than the face so no edge of it shows
    c = (Vector(lo[0]) + Vector(lo[1]) + Vector(hi[0]) + Vector(hi[1])) / 4
    nrm = (Vector(lo[1]) - Vector(lo[0])).cross(Vector(hi[0]) - Vector(lo[0])).normalized()
    if nrm.y > 0:
        nrm = -nrm
    Nq = reg(name + '_Number', 'panel', name)
    quad(Nq, c + nrm * 0.0015, tuple(nrm), NT.FACE_M[0], NT.FACE_M[1], uv(f'n{number:02d}'))
    part(name + '_Number', 'static', tuple(c), parent=name, note=f'the -y face with the number {number} cut in (panel atlas)')
    part(name, 'static', (0, 0, 0), note=f'compartment stone of fork {number} (root): origin = the stone\'s middle at the ground '
                                         f'(0.30 m in the ground), the number faces -y (the road); granite, the top painted white '
                                         f'so it is found in the snow')
    BOXES.append((f'{name}_Body', name, (-x, x, -y, y, 0.0, h + ST['peak']), None))


# ================================================================ the pointers (the airfield's AF_Sign construction)
S_POST_TOP = 2.25
S_BOARD = dict(x0=-0.10, x1=0.86, z0=1.60, z1=1.82, y0=-0.085, y1=-0.055)


def build_pointer(root, tile):
    k = reg(root, 'NetProps', root)
    k.box(-0.045, 0.045, -0.045, 0.045, -0.30, S_POST_TOP, Z_SPOST)
    k.box(-0.06, 0.06, -0.06, 0.06, S_POST_TOP, S_POST_TOP + 0.025, Z_SPOST)
    b = S_BOARD
    tip = b['x1'] + 0.12
    poly = [(b['x0'], b['z0']), (b['x1'], b['z0']), (tip, (b['z0'] + b['z1']) / 2), (b['x1'], b['z1']), (b['x0'], b['z1'])]
    prism_y(k, poly, b['y0'], b['y1'], Z_SBOARD, Z_SBOARD, [Z_SBOARD] * len(poly))
    for zz in (b['z0'] + 0.05, b['z1'] - 0.05):
        k.cyl(Vector((0.0, b['y0'] - 0.004, zz)), Vector((0.0, b['y0'], zz)), 0.010, Z_STEELBLK, 6)
    Sg = reg(root + '_Board', 'panel', root)
    w = b['x1'] - b['x0'] - 0.04
    quad(Sg, Vector(((b['x0'] + b['x1']) / 2 + 0.01, b['y0'] - 0.0008, (b['z0'] + b['z1']) / 2)), (0, -1, 0), w, b['z1'] - b['z0'] - 0.03,
         uv(tile))
    de, en = NT.SIGNS[tile]
    part(root + '_Board', 'static', ((b['x0'] + b['x1']) / 2, b['y0'], (b['z0'] + b['z1']) / 2), parent=root,
         note=f'{de} / {en} on the arrow board (panel atlas; German first, English under it)')
    part(root, 'static', (0, 0, 0), note=f'pointer {de} / {en} (root): origin = the foot of the post on the ground (sunk 0.30); the arrow '
                                         f'points +x, the text faces -y (the road)')
    BOXES.extend([(f'{root}_Post', root, (-0.05, 0.05, -0.05, 0.05, 0.0, S_POST_TOP + 0.03), None),
                  (f'{root}_BoardBox', root, (b['x0'], tip, b['y0'], b['y1'], b['z0'], b['z1']), None)])


# ================================================================ the forest track barrier (Waldweg-Schranke)
SCH = dict(half=2.3, post_r=0.085, post_top=1.15, foot=-0.45, pole_r=0.06, pole_z=0.95, board=(-1.45, -0.35, 0.58, 0.82), board_y=(-0.19, -0.165))


def build_schranke():
    k = reg('NET_Schranke', 'NetProps', 'NET_Schranke')
    h = SCH['half']
    for x in (-h, h):
        k.cyl((x, 0, SCH['foot']), (x, 0, SCH['post_top']), SCH['post_r'], Z_SPOST, 8)
        k.cyl((x, 0, SCH['post_top']), (x, 0, SCH['post_top'] + 0.03), SCH['post_r'], Z_SPOST, 8, r2=SCH['post_r'] * 0.5)
    k.cyl((-h - 0.15, -0.10, SCH['pole_z']), (h + 0.15, -0.10, SCH['pole_z'] - 0.03), SCH['pole_r'], Z_SPOST, 7)
    for x in (-h, h):                                     # the pole lies in a fork of iron on each post
        k.box(x - 0.02, x + 0.02, -0.17, -0.03, SCH['pole_z'] - 0.09, SCH['pole_z'] - 0.05, Z_STEELBLK)
    x0, x1, z0, z1 = SCH['board']
    y0, y1 = SCH['board_y']
    k.box(x0, x1, y0, y1, z0, z1, Z_SBOARD)
    for xx in (x0 + 0.08, x1 - 0.08):                    # two wires hold the board on the pole
        k.box(xx - 0.006, xx + 0.006, y0 - 0.004, y0, z1, SCH['pole_z'], Z_STEELBLK)
    Sg = reg('NET_Schranke_Board', 'panel', 'NET_Schranke')
    quad(Sg, Vector(((x0 + x1) / 2, y0 - 0.0008, (z0 + z1) / 2)), (0, -1, 0), x1 - x0 - 0.04, z1 - z0 - 0.03, uv('sign_waldweg'))
    part('NET_Schranke_Board', 'static', ((x0 + x1) / 2, y0, (z0 + z1) / 2), parent='NET_Schranke', note='WALDWEG on the board (panel atlas)')
    part('NET_Schranke', 'static', (0, 0, 0), note='forest track barrier (root): origin = between the posts on the ground (posts sunk 0.45 m); '
                                                   'the pole along x at 0.95 m, the board faces -y (the road side)')
    BOXES.extend([('Schranke_PostL', 'NET_Schranke', (-h - 0.09, -h + 0.09, -0.09, 0.09, 0.0, SCH['post_top']), None),
                  ('Schranke_PostR', 'NET_Schranke', (h - 0.09, h + 0.09, -0.09, 0.09, 0.0, SCH['post_top']), None),
                  ('Schranke_Pole', 'NET_Schranke', (-h - 0.15, h + 0.15, -0.17, -0.03, SCH['pole_z'] - 0.07, SCH['pole_z'] + 0.07), None)])


# ================================================================ the marker stake with barrier tape
STAKE = dict(h=1.25, foot=-0.35, half=0.025, tape_z=1.10)


def build_stake():
    k = reg('NET_Stake', 'NetProps', 'NET_Stake')
    h, a = STAKE['h'], STAKE['half']
    k.box(-a, a, -a, a, STAKE['foot'], h, Z_SPOST)
    k.cyl((0, 0, h), (0, 0, h + 0.08), a * 1.35, Z_SPOST, 4, r2=0.004)                     # the cut point
    t = STAKE['tape_z']
    k.box(-a - 0.004, a + 0.004, -a - 0.004, a + 0.004, t - 0.022, t + 0.022, Z_TAPE)    # the knot round the stake
    k.box(a, a + 0.42, -0.002, 0.002, t - 0.02, t + 0.02, Z_TAPE)                         # the end blowing out
    k.box(a + 0.40, a + 0.44, -0.002, 0.002, t - 0.14, t + 0.02, Z_TAPE)                  # its tip dropping
    k.box(-a - 0.04, -a, -0.002, 0.002, t - 0.30, t, Z_TAPE)                              # the end hanging
    part('NET_Stake', 'static', (0, 0, 0), note='marker stake (root): origin = its foot on the ground (0.35 m in); red-white '
                                                'barrier tape at 1.1 m, the loose end along +x')
    BOXES.append(('Stake', 'NET_Stake', (-0.03, 0.03, -0.03, 0.03, 0.0, h + 0.08), None))


# ================================================================ the graveyard
def build_graves():
    k = reg('NET_CrossWood', 'NetProps', 'NET_CrossWood')
    a = 0.04
    k.box(-a, a, -a, a, -0.35, 1.15, Z_SPOST)
    k.box(-0.32, 0.32, -a, a, 0.78, 0.86, Z_SPOST)
    k.box(-0.09, 0.09, -0.07, 0.07, 1.15, 1.17, Z_SPOST)                     # the little roof over the top
    part('NET_CrossWood', 'static', (0, 0, 0), note='wooden grave cross (root): origin = its foot on the ground (0.35 m in)')
    BOXES.append(('CrossWood', 'NET_CrossWood', (-0.05, 0.05, -0.05, 0.05, 0.0, 1.17), None))
    k = reg('NET_CrossIron', 'NetProps', 'NET_CrossIron')
    b = 0.012
    k.box(-b, b, -b, b, -0.3, 1.0, K.Z_STEELBLK)
    k.box(-0.26, 0.26, -b, b, 0.68, 0.70 + 2 * b, K.Z_STEELBLK)
    n = 10
    for i in range(n):                                                          # the ring round the crossing
        t0, t1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
        p0 = Vector((math.cos(t0) * 0.14, 0.0, 0.69 + math.sin(t0) * 0.14))
        p1 = Vector((math.cos(t1) * 0.14, 0.0, 0.69 + math.sin(t1) * 0.14))
        k.cyl(p0, p1, 0.008, K.Z_STEELBLK, 4)
    part('NET_CrossIron', 'static', (0, 0, 0), note='iron grave cross (root): origin = its foot on the ground (0.3 m in)')
    BOXES.append(('CrossIron', 'NET_CrossIron', (-0.03, 0.03, -0.03, 0.03, 0.0, 1.0), None))
    k = reg('NET_GraveWall', 'NetProps', 'NET_GraveWall')
    for i, (x0, x1) in enumerate(((-1.0, -0.35), (-0.35, 0.3), (0.3, 1.0))):     # three rough blocks of field stone
        top = 0.5 + 0.06 * math.sin(i * 2.3 + 0.7)
        k.box(x0, x1, -0.25 + 0.02 * math.sin(i), 0.25 - 0.02 * math.cos(i), -0.15, top, Z_STONE)
        k.box(x0 + 0.06, x1 - 0.06, -0.21, 0.21, top, top + 0.06, Z_STONE)
    part('NET_GraveWall', 'static', (0, 0, 0), note='dry-stone wall, 2 m along x (root): origin = the middle of its foot; segments join end to end')
    BOXES.append(('GraveWall', 'NET_GraveWall', (-1.0, 1.0, -0.25, 0.25, 0.0, 0.56), None))


# ================================================================ the abandoned camp
def build_camp():
    k = reg('NET_Tent', 'NetProps', 'NET_Tent')
    L, Wd, H, sag = 1.1, 0.85, 1.15, 0.12
    n = 6
    for i in range(n):                                       # the two roof sides, sagging in the middle along the ridge
        y0, y1 = -L + 2 * L * i / n, -L + 2 * L * (i + 1) / n
        s0 = sag * math.sin(math.pi * i / n)
        s1 = sag * math.sin(math.pi * (i + 1) / n)
        for side in (-1, 1):
            quad_pts = [Vector((side * Wd, y0, 0.0)), Vector((side * Wd, y1, 0.0)), Vector((0.0, y1, H - s1)), Vector((0.0, y0, H - s0))]
            face(k, quad_pts, Z_CANVAS, Vector((side * 0.8, 0.0, 1.0)))
    face(k, [Vector((Wd, L, 0.0)), Vector((-Wd, L, 0.0)), Vector((0.0, L, H))], Z_CANVAS, Vector((0.0, 1.0, 0.0)))          # the back
    face(k, [Vector((Wd, -L, 0.0)), Vector((0.0, -L, H)), Vector((0.25, -L - 0.35, 0.25))], Z_CANVAS, Vector((0.3, -1.0, 0.0)))  # a flap half open
    for y in (-L, L):
        k.box(-0.02, 0.02, y - 0.02, y + 0.02, -0.2, H + 0.08, Z_SPOST)
    for y in (-L, L):                                        # guy lines to pegs
        sgn = -1 if y < 0 else 1
        k.cyl(Vector((0, y, H + 0.05)), Vector((0, y + sgn * 0.9, 0.0)), 0.006, Z_SPOST, 3)
        k.box(-0.015, 0.015, y + sgn * 0.9 - 0.015, y + sgn * 0.9 + 0.015, -0.1, 0.12, Z_SPOST)
    part('NET_Tent', 'static', (0, 0, 0), note='canvas A-frame tent (root): origin = the middle of its floor; the ridge along y, the door at -y')
    BOXES.append(('Tent', 'NET_Tent', (-Wd, Wd, -L, L, 0.0, H * 0.7), None))
    k = reg('NET_FirePit', 'NetProps', 'NET_FirePit')
    for i in range(9):
        a = i * 2 * math.pi / 9
        c = Vector((math.cos(a) * 0.55, math.sin(a) * 0.55, 0.0))
        sz = 0.11 + 0.03 * math.sin(i * 1.7)
        k.box(c.x - sz, c.x + sz, c.y - sz * 0.8, c.y + sz * 0.8, -0.05, 0.12 + 0.04 * math.cos(i), Z_STONE)
    k.box(-0.42, 0.42, -0.42, 0.42, -0.04, 0.02, Z_ASH)
    for a in (0.3, 1.5, 2.6):
        d = Vector((math.cos(a), math.sin(a), 0.0))
        k.cyl(d * -0.32 + Vector((0, 0, 0.05)), d * 0.32 + Vector((0, 0, 0.14)), 0.045, Z_ASH, 6)
    part('NET_FirePit', 'static', (0, 0, 0), note='fire pit (root): origin = the middle of the ash on the ground')


def build_ladder_cloth():
    k = reg('NET_RopeLadder', 'NetProps', 'NET_RopeLadder')
    L, w = 6.0, 0.22
    for x in (-w, w):
        k.cyl(Vector((x, 0, 0)), Vector((x, 0.0, -L)), 0.012, Z_CANVAS, 4)
    z = -0.3
    while z > -L + 0.1:
        k.box(-w - 0.02, w + 0.02, -0.02, 0.02, z - 0.02, z + 0.02, Z_SPOST)
        z -= 0.35
    part('NET_RopeLadder', 'static', (0, 0, 0), note='rope ladder (root): origin = its top; it hangs 6 m down -z')
    k = reg('NET_Cloth', 'NetProps', 'NET_Cloth')
    nx, ny = 6, 5
    def pt(i, j):                                            # i across the beam (x), j down from the beam on both sides
        x = -1.2 + 2.4 * i / nx
        t = (j - ny) / ny                                     # -1 .. 1: one side, over the beam, the other side
        y = 0.35 * t
        zz = -1.8 * abs(t) ** 1.4 + 0.08 * math.sin(i * 1.9 + j)
        return Vector((x, y + 0.15 * math.sin(i * 0.8) * abs(t), zz))
    for i in range(nx):
        for j in range(2 * ny):
            if (i + j) % 7 == 3 and abs(j - ny) > 2:          # torn holes
                continue
            face(k, [pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], Z_CANVAS, Vector((0.0, 0.0, 1.0)))
            face(k, [pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], Z_CANVAS, Vector((0.0, 0.0, -1.0)))   # both sides
    part('NET_Cloth', 'static', (0, 0, 0), note='canvas thrown over a beam (root): origin = on the beam; the halves hang along -y and +y')


def build_meteo_hut():
    k = reg('NET_MeteoHut', 'NetProps', 'NET_MeteoHut')
    hx, hy, wall, ridge = 1.5, 1.2, 2.1, 2.9
    k.box(-hx, hx, -hy, hy, -0.1, wall, Z_PLANK)                                   # the walls as one block
    for sx in (-1, 1):                                                            # the gables
        face(k, [Vector((sx * hx, -hy, wall)), Vector((sx * hx, hy, wall)), Vector((sx * hx, 0.0, ridge))], Z_PLANK, Vector((sx, 0, 0)))
    over = 0.25
    for sy in (-1, 1):                                                            # the roof, overhanging
        p = [Vector((-hx - over, sy * (hy + over), wall - 0.12)), Vector((hx + over, sy * (hy + over), wall - 0.12)),
             Vector((hx + over, 0.0, ridge + 0.03)), Vector((-hx - over, 0.0, ridge + 0.03))]
        face(k, p, Z_TIN, Vector((0, sy, 1)))
        face(k, p, Z_TIN, Vector((0, -sy, -1)))
    k.box(-0.45, 0.45, -hy - 0.02, -hy, 1.0, 1.6, Z_WINLIT)                       # the lit window on the road side
    k.box(-0.52, 0.52, -hy - 0.05, -hy, 0.93, 1.0, Z_PLANK)                       # its sill
    k.box(hx, hx + 0.02, -0.4, 0.4, 0.0, 1.9, Z_SPOST)                            # the door
    k.box(hx + 0.02, hx + 0.6, -0.6, 0.6, -0.05, 0.12, Z_PLANK)                   # the step
    part('NET_MeteoHut', 'static', (0, 0, 0), note='weather hut (root): origin = the middle of its floor; the lit window faces -y, the door +x')
    BOXES.append(('MeteoHut', 'NET_MeteoHut', (-hx, hx, -hy, hy, 0.0, wall), None))


def build_abatis_steps():
    k = reg('NET_Abatis', 'NetProps', 'NET_Abatis')
    k.cyl(Vector((-1.8, 0.0, 0.62)), Vector((1.8, 0.0, 0.62)), 0.11, Z_SPOST, 7)            # the log along x
    for x in (-1.3, 0.0, 1.3):                                                            # X-trestles of sharp poles
        for sy in (-1, 1):
            k.cyl(Vector((x, -sy * 0.55, 0.0)), Vector((x, sy * 0.55, 1.15)), 0.045, Z_SPOST, 5, r2=0.012)
    part('NET_Abatis', 'static', (0, 0, 0), note='log barricade (root): origin = its middle on the ground; the log along x')
    BOXES.append(('Abatis', 'NET_Abatis', (-1.85, 1.85, -0.6, 0.6, 0.0, 1.15), None))
    k = reg('NET_LogSteps', 'NetProps', 'NET_LogSteps')
    for i in range(5):
        y, z = 0.4 * i + 0.1, 0.2 * i + 0.09
        k.cyl(Vector((-0.7, y, z)), Vector((0.7, y, z)), 0.09, Z_SPOST, 6)                  # the riser log
        k.box(-0.7, 0.7, y, y + 0.32, z - 0.15, z + 0.05, Z_STONE)                          # the tread fill behind it
        for x in (-0.75, 0.75):
            k.box(x - 0.03, x + 0.03, y - 0.13, y - 0.07, z - 0.4, z + 0.12, Z_SPOST)       # pegs holding it
    part('NET_LogSteps', 'static', (0, 0, 0), note='log steps (root): origin = the first step\'s front on the ground; they climb along +y')
    BOXES.append(('LogSteps', 'NET_LogSteps', (-0.7, 0.7, 0.0, 2.0, 0.0, 0.9), None))


def build_portal():
    k = reg('NET_BunkerPortal', 'NetProps', 'NET_BunkerPortal')
    k.box(-1.7, 1.7, 0.0, 0.35, -0.3, 2.8, Z_HEAD)                            # the face wall
    k.box(-1.9, 1.9, -0.05, 0.4, 2.8, 3.0, Z_HEAD)                           # its coping
    for sx in (-1, 1):                                                       # wing walls splayed out into the slope
        x0 = sx * 1.7
        p0, p1 = Vector((x0, 0.0, 0.0)), Vector((x0 + sx * 1.3, -1.6, 0.0))
        h0, h1 = 2.8, 0.5
        face(k, [p0, p1, p1 + Vector((0, 0, h1)), p0 + Vector((0, 0, h0))], Z_HEAD, Vector((-sx * 0.8, -0.6, 0)))
        face(k, [p0, p1, p1 + Vector((0, 0, h1)), p0 + Vector((0, 0, h0))], Z_HEAD, Vector((sx * 0.8, 0.6, 0)))
    k.box(-0.6, 0.6, -0.04, 0.0, 0.0, 2.05, Z_STEELBLK)                       # the door
    Sg = reg('NET_BunkerPortal_Sign', 'panel', 'NET_BunkerPortal')
    quad(Sg, Vector((0.0, -0.045, 1.55)), (0, -1, 0), 0.9, 0.22, uv('sign_druck'))
    part('NET_BunkerPortal_Sign', 'static', (0.0, -0.045, 1.55), parent='NET_BunkerPortal', note='DRUCKTUER on the door (panel atlas)')
    k.box(-0.18, 0.18, -0.25, 0.0, 2.25, 2.45, Z_STEELBLK)                   # the lamp box over the door
    for i in range(3):                                                       # steps down to the door
        k.box(-0.8, 0.8, -1.4 + i * 0.45, -0.95 + i * 0.45, -0.3, 0.45 - 0.15 * i, Z_APRON)
    part('NET_BunkerPortal', 'static', (0, 0, 0), note='bunker portal (root): origin = the door threshold; the face looks -y')
    BOXES.append(('BunkerPortal', 'NET_BunkerPortal', (-1.7, 1.7, 0.0, 0.4, 0.0, 3.0), None))


def build_network():
    build_pole()
    build_culvert()
    for i, (name, n) in enumerate(zip(STONES, NUMBERS)):
        build_stone(name, n, 17 + i)
    for root, tile in POINTERS.items():
        build_pointer(root, tile)
    build_schranke()
    build_stake()
    build_graves()
    build_camp()
    build_ladder_cloth()
    build_meteo_hut()
    build_abatis_steps()
    build_portal()
