"""forest_station geometry (27.10.2026, built locally - skill snow-model): two control-room props.
Each root in its own frame (Blender: z up, the front -y, metres; Unity (x, y, z) -> (-x, z, -y), the front -> +Z):
  Station_MonitorRack_3x3  a floor-standing slotted-angle steel rack for nine snow_kit Kit_Monitor_CRT (3 x 3, cell pitch
                           0.40 m): four angle posts 40 x 40 x 2.5 mm (a row of punched holes - texture), three flanged
                           shelf trays (tops 0.62 / 0.98 / 1.34) and a top cap tray (1.75), low tie rails at 0.10, an X brace
                           on the back under the bottom shelf, plastic foot caps. 1.25 x 0.52 x 1.75; origin on the floor
                           under the middle of the BACK face (it stands against a wall: back = Unity z 0, front = Unity +Z).
                           Slot_1..Slot_9: where each monitor's pivot goes (row-major, Slot_1 = top-left seen from the front)
  Station_SideTable        a 1980s office side table: square steel tube legs, an apron frame, a beige laminate top with a
                           dark edge band, plastic glides. 0.70 x 0.62 x 0.72; origin on the floor under its middle.
                           Slot_PC: where forest_devices' ObjectPC root goes (case towards the back)
Painted details (holes, bolts, laminate, edge band, wear) are texture only (station_paint)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, face, box6
import van3_mech as VM

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
RACK, TABLE = 'Station_MonitorRack_3x3', 'Station_SideTable'
ROOTS = [RACK, TABLE]
DISPLAY = {RACK: Vector((0.0, 0.0, 0.0)), TABLE: Vector((1.45, -0.26, 0.0))}
ROOT_OF = {}
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot or None) in the root frame
PART_BOXES = {}                  # name -> [(lo, hi)] solid boxes of the rack / table for the slot clearance check

# zones (float 'zone' attribute -> station_paint)
(Z_POST, Z_SHELF, Z_RAIL, Z_BRACE, Z_FOOT, Z_TTOP, Z_TLEG, Z_TFRAME, Z_TFOOT) = range(700, 709)
ZONES = [Z_POST, Z_SHELF, Z_RAIL, Z_BRACE, Z_FOOT, Z_TTOP, Z_TLEG, Z_TFRAME, Z_TFOOT]

# ---------------------------------------------------------------- the rack's numbers
RK = dict(hx=0.625, d=0.52, h=1.75, a=0.040, t=0.0025, foot=0.012, fl=0.030, plate=0.0015,
          shelves=(0.62, 0.98, 1.34), cap=1.75, pitch=0.40, rail_z=0.10, rail=0.030)
# Kit_Monitor_CRT as built (snow_kit 1.1, measured 27.10): 0.34 wide, 0.31 tall, mesh from y -0.202 (front) to +0.248
# (back) about its pivot (the middle of its underside) - its depth centre is 0.023 behind the pivot
MON = dict(w=0.34, h=0.31, y_front=-0.202, y_back=0.248)
MON_CENTRE_FROM_BACK = 0.26                                      # the monitor's depth centre, in front of the rack's back
SLOT_Y = -(MON_CENTRE_FROM_BACK + (MON['y_front'] + MON['y_back']) / 2)   # the pivot: -0.283

# ---------------------------------------------------------------- the table's numbers
TB = dict(w=0.70, d=0.62, h=0.72, top=0.025, leg=0.025, inset=0.030, apron=0.040, apron_w=0.020, glide=0.010)
PC_Y = 0.10                      # ObjectPC root 0.10 behind the table centre: its case (0.40 deep) ends 1 cm inside the back edge


def part(name, *a, **kw):
    assert name not in K.CONTRACT['parts'], f'part {name} twice'
    K.part(name, *a, **kw)


def socket(name, *a, **kw):
    assert name not in K.CONTRACT['sockets'], f'socket {name} twice'
    K.socket(name, *a, **kw)


def reg(name, atlas, root):
    ROOT_OF[name] = root
    return kb(name, atlas)


def solid(root, lo, hi):
    PART_BOXES.setdefault(root, []).append((tuple(lo), tuple(hi)))


# ---------------------------------------------------------------- a straight prism of a 2D profile
def prism(k, prof, axis, a0, a1, zone, caps):
    """the profile prof [(u, v)] (any winding) swept along `axis` ('x', 'y' or 'z') from a0 to a1; (u, v) are the other two
    axes in order (x: y, z; y: x, z; z: x, y); caps = list of convex sub-polygons (index lists) for the two end faces (an L
    profile is concave: its ends go as two quads)"""
    ia = 'xyz'.index(axis)
    iu, iv = [i for i in range(3) if i != ia]

    def P(u, v, a):
        p = [0.0, 0.0, 0.0]
        p[iu], p[iv], p[ia] = u, v, a
        return Vector(p)

    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    if area < 0:                                                 # counter-clockwise: the outward normal of an edge is (dv, -du)
        prof = list(reversed(prof))
        n = len(prof)
        caps = [[n - 1 - i for i in c] for c in caps]
    n = len(prof)
    for i in range(n):
        (u0, v0), (u1, v1) = prof[i], prof[(i + 1) % n]
        out = [0.0, 0.0, 0.0]
        out[iu], out[iv] = (v1 - v0), -(u1 - u0)
        face(k, [P(u0, v0, a0), P(u1, v1, a0), P(u1, v1, a1), P(u0, v0, a1)], zone, out=Vector(out))
    ax = Vector([1.0 if i == ia else 0.0 for i in range(3)])
    for c in caps:
        face(k, [P(*prof[i], a0) for i in c], zone, out=-ax)
        face(k, [P(*prof[i], a1) for i in c], zone, out=ax)


def L_prof(cu, cv, du, dv, a, b, t):
    """an angle section with its heel at (cu, cv), the legs a (along u, direction du) and b (along v, direction dv), t thick;
    returns (profile, caps)"""
    prof = [(cu, cv), (cu + du * a, cv), (cu + du * a, cv + dv * t), (cu + du * t, cv + dv * t), (cu + du * t, cv + dv * b),
            (cu, cv + dv * b)]
    return prof, [[0, 1, 2, 3], [0, 3, 4, 5]]


def tray(k, x0, x1, y0, y1, zt, fl, plate, zone):
    """a pressed-steel shelf tray: the plate (top zt, `plate` thick) with its four edges turned down `fl`; thin walls, open
    underneath (top, outer sides, the bottom rim, inner sides, the plate's underside)"""
    zb = zt - fl
    w = plate
    O = [Vector((x0, y0, 0)), Vector((x1, y0, 0)), Vector((x1, y1, 0)), Vector((x0, y1, 0))]
    I = [Vector((x0 + w, y0 + w, 0)), Vector((x1 - w, y0 + w, 0)), Vector((x1 - w, y1 - w, 0)), Vector((x0 + w, y1 - w, 0))]
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    face(k, [p + Z * zt for p in O], zone, out=Z)
    face(k, [p + Z * (zt - w) for p in I], zone, out=-Z)
    for i in range(4):
        j = (i + 1) % 4
        m = (O[i] + O[j]) / 2 - c
        m.z = 0
        face(k, [O[i] + Z * zb, O[j] + Z * zb, O[j] + Z * zt, O[i] + Z * zt], zone, out=m)          # outer side
        face(k, [I[i] + Z * zb, I[j] + Z * zb, I[j] + Z * (zt - w), I[i] + Z * (zt - w)], zone, out=-m)   # inner side
        face(k, [O[i] + Z * zb, O[j] + Z * zb, I[j] + Z * zb, I[i] + Z * zb], zone, out=-Z)        # the bottom rim


# ================================================================ the monitor rack
def build_rack():
    k = reg(RACK, 'Props', RACK)
    hx, d, h, a, t, ft = RK['hx'], RK['d'], RK['h'], RK['a'], RK['t'], RK['foot']
    corners = [(sx, cy) for sx in (-1, 1) for cy in (-d, 0.0)]
    for sx, cy in corners:
        cx = sx * hx
        ix, iy = -sx, (1 if cy < -0.01 else -1)                  # inward along x / y
        prof, caps = L_prof(cx, cy, ix, iy, a, a, t)
        prism(k, prof, 'z', ft, h, Z_POST, caps)                 # the post: from the foot cap to the top
        solid(RACK, (min(cx, cx + ix * a), min(cy, cy + iy * a), 0.0), (max(cx, cx + ix * a), max(cy, cy + iy * a), h))
        box6(k, (cx, cy, 0.0), (cx + ix * (a + 0.002), cy + iy * (a + 0.002), ft), Z_FOOT, skip=('-z',))   # the foot cap
        BOXES.append((f'Post_{"L" if sx < 0 else "R"}{"F" if cy < -0.01 else "B"}', RACK,
                      (min(cx, cx + ix * a), max(cx, cx + ix * a), min(cy, cy + iy * a), max(cy, cy + iy * a), 0.0, h), None))
    # the shelf trays sit inside the angles (0.5 mm clear of the posts' inner faces), bolted through the holes (texture)
    g = t + 0.0005
    for zt in RK['shelves'] + (RK['cap'],):
        tray(k, -hx + g, hx - g, -d + g, -g, zt, RK['fl'], RK['plate'], Z_SHELF)
        solid(RACK, (-hx, -d, zt - RK['fl']), (hx, 0.0, zt))
        BOXES.append((f'Shelf_{int(round(zt * 100))}', RACK, (-hx, hx, -d, 0.0, zt - RK['fl'], zt), None))
    # the low tie rails (angle 30 x 30, the vertical leg inside the posts, the horizontal leg inwards at the bottom)
    rz, ra = RK['rail_z'], RK['rail']
    for cy, dv in ((-d + g, 1), (-g, -1)):                       # front and back rails along x
        prof, caps = L_prof(cy, rz - ra / 2, dv, 1, ra, ra, 0.002)
        prism(k, prof, 'x', -hx + g, hx - g, Z_RAIL, caps)
    for sx in (-1, 1):                                            # the side rails along y, on top of the front / back rails' legs
        prof, caps = L_prof(sx * (hx - g), rz - ra / 2 + 0.002, -sx, 1, ra, ra, 0.002)
        prism(k, prof, 'y', -d + g + 0.0025, -g - 0.0025, Z_RAIL, caps)
    solid(RACK, (-hx, -d, rz - ra / 2), (hx, 0.0, rz + ra / 2))
    # the X brace on the back, under the bottom shelf: two flat bars 25 x 3, one in front of the other, bolted to the posts
    zb0, zb1 = rz + ra / 2 + 0.02, RK['shelves'][0] - RK['fl'] - 0.015
    xb = hx - a / 2
    for i, (p0, p1) in enumerate((((-xb, zb0), (xb, zb1)), ((xb, zb0), (-xb, zb1)))):
        a0, a1 = Vector((p0[0], 0, p0[1])), Vector((p1[0], 0, p1[1]))
        L = (a1 - a0).length
        ux = (a1 - a0).normalized()
        R = Matrix((ux, Vector((0, 1, 0)), ux.cross(Vector((0, 1, 0))))).transposed()
        yc = -g - 0.0015 - 0.003 * i
        VM.obox(k, ((a0 + a1) / 2) + Vector((0, yc, 0)), (L, 0.003, 0.025), Z_BRACE, R)
    part(RACK, 'static', (0, 0, 0), note='the monitor rack (root): origin on the floor under the middle of its BACK face (stands '
                                         'against a wall), the front -y (Unity +Z); slotted-angle steel, three shelves and a cap; '
                                         'the nine monitors are snow_kit Kit_Monitor_CRT instances on Slot_1..Slot_9 (the game '
                                         'puts them there, with their paper labels)')
    i = 0
    for zt in reversed(RK['shelves']):                            # top row first
        for col in (-1, 0, 1):                                    # left to right SEEN FROM THE FRONT = -x to +x
            i += 1
            socket(f'Slot_{i}', (col * RK['pitch'], SLOT_Y, zt), 'kit', parent=RACK, dir=(0, -1, 0), up=(0, 0, 1),
                   item='Kit_Monitor_CRT', note=f'monitor {i} (row {(i - 1) // 3 + 1}, column {(i - 1) % 3 + 1} seen from the '
                                                f'front): a Kit_Monitor_CRT\'s pivot (the middle of its underside) here, '
                                                f'facing the front; its depth centre {MON_CENTRE_FROM_BACK:.2f} m in front '
                                                f'of the back')


# ================================================================ the side table
def build_table():
    k = reg(TABLE, 'Props', TABLE)
    w, d, h, tt, lg, ins = TB['w'], TB['d'], TB['h'], TB['top'], TB['leg'], TB['inset']
    VM.rbox(k, Vector((0, 0, h - tt / 2)), (w, d, tt), Z_TTOP, r=0.006, ch=0.003, axis='z')
    solid(TABLE, (-w / 2, -d / 2, h - tt), (w / 2, d / 2, h))
    za = h - tt                                                   # the underside of the top
    lx, ly = w / 2 - ins - lg / 2, d / 2 - ins - lg / 2          # leg centres
    gl = TB['glide']
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * lx, sy * ly
            box6(k, (cx - lg / 2, cy - lg / 2, gl), (cx + lg / 2, cy + lg / 2, za - 0.0005), Z_TLEG, skip=('+z', '-z'))
            box6(k, (cx - lg / 2 + 0.001, cy - lg / 2 + 0.001, 0.0), (cx + lg / 2 - 0.001, cy + lg / 2 - 0.001, gl), Z_TFOOT,
                 skip=('-z',))
            solid(TABLE, (cx - lg / 2, cy - lg / 2, 0.0), (cx + lg / 2, cy + lg / 2, za))
            BOXES.append((f'Leg_{"L" if sx < 0 else "R"}{"F" if sy < 0 else "B"}', TABLE,
                          (cx - lg / 2, cx + lg / 2, cy - lg / 2, cy + lg / 2, 0.0, za), None))
    # the apron frame: 20 x 40 tube between the legs, flush with their outer faces, under the top
    ap, aw = TB['apron'], TB['apron_w']
    z0, z1 = za - ap, za - 0.0005
    ox, oy = lx + lg / 2, ly + lg / 2                             # the legs' outer faces
    for sy in (-1, 1):
        box6(k, (-lx + lg / 2, sy * oy - (aw if sy > 0 else 0), z0), (lx - lg / 2, sy * oy + (0 if sy > 0 else aw), z1),
             Z_TFRAME, skip=('+z', '-x', '+x'))
    for sx in (-1, 1):
        box6(k, (sx * ox - (aw if sx > 0 else 0), -ly + lg / 2, z0), (sx * ox + (0 if sx > 0 else aw), ly - lg / 2, z1),
             Z_TFRAME, skip=('+z', '-y', '+y'))
    BOXES.append(('Top', TABLE, (-w / 2, w / 2, -d / 2, d / 2, za, h), None))
    part(TABLE, 'static', (0, 0, 0), note='the side table (root): origin on the floor under its middle, the front -y (Unity +Z); '
                                          'square steel tube legs, apron frame, beige laminate top with a dark edge band')
    socket('Slot_PC', (0.0, PC_Y, h), 'slot', parent=TABLE, dir=(0, -1, 0), up=(0, 0, 1), item='ObjectPC',
           note='forest_devices ObjectPC root (the middle of the case\'s underside) here, facing the front: the case 0.10 m '
                'behind the table centre, its back 1 cm inside the back edge; the stock keyboard / mouse of ObjectPC then '
                'stand 8.5 / 4.6 cm over the front edge - move them to Slot_Keyboard / Slot_Mouse')
    socket('Slot_Keyboard', (0.0, PC_Y - 0.30, h), 'slot', parent=TABLE, dir=(0, -1, 0), up=(0, 0, 1), item='PC_Keyboard',
           note='optional: where ObjectPC\'s PC_Keyboard pivot fits on this table (0.10 m back from its stock place, 5 mm in '
                'front of the case)')
    socket('Slot_Mouse', (0.29, PC_Y - 0.30, h), 'slot', parent=TABLE, dir=(0, -1, 0), up=(0, 0, 1), item='PC_Mouse',
           note='optional: where ObjectPC\'s PC_Mouse pivot fits on this table (right of the keyboard)')


def build_all():
    build_rack()
    build_table()
