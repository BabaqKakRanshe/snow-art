"""forest_pager geometry: the worker's pager (user 26.10.2026, docs/gdd/research/RESEARCH_UI_3.md, look 1 «Cityruf»): a 1994
alphanumeric pager in black ABS, held up in the left hand to pick a message; the message itself is printed on the screen
by the game. Adapted from forest_gear's Item_Walkie (gear_kit). One root in its own frame (Blender: z up, the front -y,
metres; origin on the surface it stands on, z = 0, under its middle; Unity (x, y, z) -> (-x, z, -y), the front -> +Z):
  Item_Pager   78 x 56 x 22 mm, rounded corners, bevelled front and back; the LCD (20 x 4 characters) its own object behind
               a raised bezel (lit / off, UV 0..1 - the game draws the list into it), three keys under it (up, read, down:
               slide parts), the red LED top right, the BEEP / VIB switch on the top (slide), the station's inventory
               sticker on the right side, the belt clip at the back
The printed faces (panel atlas) are merged into the body at build time (MERGE); parts / sockets in the root's frame."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, face, quad, KBS, CONTRACT, newell
from van2_kit import rrect
import pager_tex as PT

uv = PT.uv
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ROOTS = ['Item_Pager']
DISPLAY = {'Item_Pager': Vector((0.0, 0.0, 0.0))}
ROOT_OF = {}
MERGE = {}                       # explicit-UV KB -> the body it is joined into (a second material on that mesh)
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot or None) in the root frame
MASS = {}                        # root -> kg (a suggestion for the rigidbody)
Z_PG, Z_PG_RUB, Z_PG_METAL = 560, 561, 562
SMALL_ZONES = [Z_PG, Z_PG_RUB, Z_PG_METAL]
# 1.2 (27.10, reference «brick refined»): chamfered corners (seg 1), a thicker bevel, a deep bezel, keys with their signs, the
# LED beside the maker line, the metal belt clip on the left side
PG = dict(w=0.078, h=0.056, d=0.022, r=0.008, bevel=0.0028, seg=1)
FRONT_PX = (78, 56)              # pager_front in px: the front texture covers the whole body outline


def part(name, *a, **kw):
    assert name not in CONTRACT['parts'], f'part {name} twice'
    K.part(name, *a, **kw)


def socket(name, *a, **kw):
    assert name not in CONTRACT['sockets'], f'socket {name} twice'
    K.socket(name, *a, **kw)


def reg(name, atlas, root, merge=None):
    ROOT_OF[name] = root
    if merge:
        MERGE[name] = merge
    return kb(name, atlas)


def front_point(px, py, lift=0.0):
    """a pixel of pager_front (78 x 56, y down) -> a point on the front (x -w/2..w/2, z h..0), lift towards the viewer"""
    w, h = PG['w'], PG['h']
    return Vector((-w / 2 + px / FRONT_PX[0] * w, -PG['d'] / 2 - lift, h - py / FRONT_PX[1] * h))


def poly_uv(k, pts, uvs, out):
    """a polygon with explicit UVs, turned to face `out`"""
    pts = [Vector(p) for p in pts]
    if newell(pts).dot(Vector(out)) < 0:
        pts, uvs = list(reversed(pts)), list(reversed(uvs))
    return k.poly(pts, 0.0, uvs)


def planar_uv(pts, uvrect, lo, hi, ia, ib):
    u0, v0, u1, v1 = uvrect
    return [(u0 + (u1 - u0) * (p[ia] - lo[0]) / (hi[0] - lo[0]), v0 + (v1 - v0) * (p[ib] - lo[1]) / (hi[1] - lo[1])) for p in pts]


def pill(k, kf, c, w, h, depth, r, zone, icon, seg=3):
    """an oval key standing `depth` out of the front (-y) from c (on the surface): the walls in k, the front cap in kf with
    the panel's icon tile (its sign) mapped flat on it"""
    c = Vector(c)
    R0 = rrect(c, X, Z, w, h, r, seg)
    R1 = [p - Y * depth for p in rrect(c, X, Z, w - 0.0008, h - 0.0008, r - 0.0004, seg)]
    n = len(R0)
    for j in range(n):
        j2 = (j + 1) % n
        face(k, [R0[j], R0[j2], R1[j2], R1[j]], zone, out=(R0[j] + R0[j2]) / 2 - c)
    lo, hi = (c.x - w / 2, c.z - h / 2), (c.x + w / 2, c.z + h / 2)
    poly_uv(kf, R1, planar_uv(R1, uv(icon), lo, hi, 0, 2), -Y)


def build_pager():
    k = reg('Item_Pager', 'Small', 'Item_Pager')
    pk = reg('Pager_Print', 'panel', 'Item_Pager', merge='Item_Pager')
    w, h, d, r, bv, sg = PG['w'], PG['h'], PG['d'], PG['r'], PG['bevel'], PG['seg']
    c0 = Vector((0.0, 0.0, h / 2))
    out_ring = rrect(c0, X, Z, w, h, r, sg)                                  # the outline, CCW seen from the front
    in_ring = rrect(c0, X, Z, w - 2 * bv, h - 2 * bv, r - bv, sg)
    n = len(out_ring)
    Fo = [p + Y * (-d / 2 + bv) for p in out_ring]                           # the walls run between the bevels
    Bo = [p + Y * (d / 2 - bv) for p in out_ring]
    Fi = [p + Y * (-d / 2) for p in in_ring]                                 # the front and back faces
    Bi = [p + Y * (d / 2) for p in in_ring]
    k_ = sg
    RIGHT, TOP = k_, 2 * k_ + 1                                              # the flat walls (rrect: corners of k+1 points)
    for j in range(n):
        j2 = (j + 1) % n
        wall = [Fo[j], Fo[j2], Bo[j2], Bo[j]]
        mid = (out_ring[j] + out_ring[j2]) / 2 - c0
        if j == RIGHT:                                                       # the inventory sticker seen from +x: u front -> back, v up
            u0, v0, u1, v1 = uv('pager_side')
            uvs = [((u1 if p.y > 0 else u0), v0 + (v1 - v0) * (p.z / h)) for p in wall]
            poly_uv(pk, wall, uvs, mid)
        elif j == TOP:                                                       # BEEP / VIB: reads from the front, its top to the back
            u0, v0, u1, v1 = uv('pager_top')
            uvs = [(u0 + (u1 - u0) * (p.x + w / 2) / w, v0 + (v1 - v0) * (p.y + d / 2) / d) for p in wall]
            poly_uv(pk, wall, uvs, mid)
        else:
            face(k, wall, Z_PG, out=mid)
        face(k, [Fi[j], Fi[j2], Fo[j2], Fo[j]], Z_PG, out=mid - Y * 0.01)   # the front bevel
        face(k, [Bo[j], Bo[j2], Bi[j2], Bi[j]], Z_PG, out=mid + Y * 0.01)   # the back bevel
    poly_uv(pk, Fi, planar_uv(Fi, uv('pager_front'), (-w / 2, 0.0), (w / 2, h), 0, 2), -Y)   # the printed front
    face(k, Bi, Z_PG, out=Y)                                                 # the back
    # the bezel: a frame 1.2 mm proud round the LCD window, so the glass sits in a well
    lx0, ly0, lx1, ly1 = PT.FRONT['lcd']
    a, b = front_point(lx0, ly1), front_point(lx1, ly0)                     # bottom left, top right of the window
    t, fr, y0, y1 = 0.0036, 0.0018, -d / 2 - 0.0018, -d / 2                  # 1.2: thicker and deeper
    for x0_, x1_, z0_, z1_ in ((a.x - t, b.x + t, b.z, b.z + t), (a.x - t, b.x + t, a.z - t, a.z),
                               (a.x - t, a.x, a.z, b.z), (b.x, b.x + t, a.z, b.z)):
        k.box(x0_, x1_, y0, y1, z0_, z1_, Z_PG)
    lc = Vector(((a.x + b.x) / 2, -d / 2 - 0.0002, (a.z + b.z) / 2))     # 1.6 mm down in the bezel's well
    lcd = reg('Pager_LCD', 'lcd', 'Item_Pager')
    quad(lcd, lc, (0, -1, 0), b.x - a.x, b.z - a.z, (0.0, 0.0, 1.0, 1.0))
    part('Pager_LCD', 'static', lc, parent='Item_Pager',
         note=f'the LCD, {PT.LCD_COLS} x {PT.LCD_ROWS} characters of 5 x 7 dots: M_Pager_LCD (lit: green backlight, a sample '
              f'list) / M_Pager_LCD_Off (in the file); its own texture {PT.LCD_PX[0]} x {PT.LCD_PX[1]}, UV 0..1 (u right, '
              f'v up) - the game draws its own list into it (cells 6 x 9 px from (2, 2))', size=[round(b.x - a.x, 4), round(b.z - a.z, 4)])
    # the keys (slide in 1.2 mm), the LED, the mode switch on the top
    hx, hy = PT.FRONT['key_half']
    kw_, kh_ = hx * 2 / FRONT_PX[0] * w, hy * 2 / FRONT_PX[1] * h
    for (px, py), nm, note in zip(PT.FRONT['keys'], ('Pager_Key_Up', 'Pager_Key_Read', 'Pager_Key_Down'),
                                  ('up: the previous message (the game: arrow up / wheel)',
                                   'read: open the picked message on the screen / back (the game: E)',
                                   'down: the next message (the game: arrow down / wheel)')):
        c = front_point(px, py)
        kk = reg(nm, 'Small', 'Item_Pager')
        kf = reg(nm + '_Face', 'panel', 'Item_Pager', merge=nm)
        pill(kk, kf, c, kw_, kh_, 0.0016, 0.0042, Z_PG_RUB, {'Pager_Key_Up': 'key_up', 'Pager_Key_Read': 'key_read',
                                                              'Pager_Key_Down': 'key_down'}[nm])
        part(nm, 'slide', c, axis=(0, 1, 0), rng=(0.0, 0.0012), unit='m', parent='Item_Pager', note=note + '; pushes in 1.2 mm')
    led = reg('Pager_LED', 'led', 'Item_Pager')
    cl = front_point(*PT.FRONT['led'], lift=0.0003)
    quad(led, cl, (0, -1, 0), 0.0042, 0.0022, (0.0, 0.0, 1.0, 1.0))   # a small rectangular LED
    part('Pager_LED', 'static', cl, parent='Item_Pager', note='the message LED: M_Pager_LEDR (blinks while a message is unread) / '
                                                              'M_Pager_LED_Off (in the file)')
    sw = reg('Pager_Switch', 'Small', 'Item_Pager')
    cs = Vector((-w / 2 + 32.5 / 78.0 * w, 0.0, h))
    sw.box(cs.x - 0.002, cs.x + 0.002, -0.0015, 0.0015, h - 0.0004, h + 0.0016, Z_PG_RUB)
    part('Pager_Switch', 'slide', cs, axis=(1, 0, 0), rng=(0.0, 0.003), unit='m', parent='Item_Pager',
         note='the alert switch on the top: 0 = BEEP (left), 0.003 = VIB (right); silent is in the pager\'s menu')
    # the belt clip on the left side (seen from the front): a steel spring plate standing off the side, its bridge at the top
    cx0, cx1 = -w / 2 - 0.0030, -w / 2 - 0.0014
    k.box(cx0, cx1, -0.005, 0.007, 0.010, h - 0.012, Z_PG_METAL)
    k.box(cx0, -w / 2 + 0.0004, -0.005, 0.007, h - 0.016, h - 0.012, Z_PG_METAL)
    k.cyl(Vector((cx0 - 0.0002, 0.001, h - 0.020)), Vector((-w / 2, 0.001, h - 0.020)), 0.0014, Z_PG_METAL, 6)   # the rivet
    part('Item_Pager', 'item', (0, 0, 0), note='the worker\'s pager (root): standing on its bottom, origin under its middle; the '
                                               'front (LCD, keys) to -y, the belt clip on the left side (-x); raised in the LEFT hand to pick a '
                                               'message, the message itself is printed on the screen by the game')
    socket('Hand_Pager', (0.0, 0.004, 0.022), 'hand', parent='Item_Pager', note='the left hand\'s grip: the lower body, the '
                                                                               'thumb on the keys')
    socket('Screen', lc, 'point', parent='Item_Pager', dir=(0, -1, 0), up=(0, 0, 1),
           note='the LCD centre, its normal and up: where the game aims the raised pager at the eye')
    socket('LED', cl, 'light', parent='Item_Pager', dir=(0, -1, 0), color=[1.0, 0.12, 0.06], range=0.15,
           note='a tiny red point light while the LED blinks (optional)')
    socket('Beeper', Vector((0.020, 0.0, h)), 'audio', parent='Item_Pager', dir=(0, 0, 1), note='the beeper (alert sound)')
    socket('Belt', Vector((-w / 2 - 0.0022, 0.001, 0.030)), 'attach', parent='Item_Pager', dir=(-1, 0, 0),
           note='the clip on the belt: worn at the hip when lowered')
    MASS['Item_Pager'] = 0.11
    BOXES.append(('Pager', 'Item_Pager', (-w / 2 - 0.003, w / 2, -d / 2 - 0.0018, d / 2, 0.0, h + 0.0016), None))


def build_all():
    build_pager()
