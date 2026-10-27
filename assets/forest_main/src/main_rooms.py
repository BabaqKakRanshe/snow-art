"""Main building — the rooms' furniture and equipment at the Update 3 places (measured off the Forest model: every
desk, console, rack, locker, bed, radiator, extinguisher), built in the shed's manner; the Update 3 interactables
(drawers, doors, breakers, switches ...) on their pivots.  Static pieces go into the room's object (its light zone)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, Z_GALV, Z_STEELBLK
import van3_mech as VM
import main_spec as S
import main_shell as MS
import main_open as MO
import main_ix_u3 as X
from main_furn import *                                              # noqa: F401,F403
import main_furn as F

DRAFT_COL = dict(F.DRAFT_COL)
NX, PX, NY, PY = (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0)


def R(name):
    return MS.rkb(name)


# ================================================================ ground floor
# ---------------------------------------------------------------- snow_kit instances (KPP v2.1: the base's gate station)
KIT_INST = {}       # name -> dict(item, parent, pos, yaw, slot (parent instance, kit socket) or None, ids, note); main_build
#                     places them as empties instancing the kit's collections (../snow_kit/snow_kit.blend)
LEIT_CCTV = Vector((3.15, -1.42, 0.75))         # the right workstation: a stand with two CCTV monitors (the KPP's cameras)
LEIT_SHELF = 1.10                                # the stand's shelf top (the upper monitor stands on it)
LEIT_CONSOLE = (Vector((2.42, -1.80, 0.75)), 12.0)   # the gate console at the left, turned a little toward the chair


def kit_inst(name, item, parent, pos=None, yaw=0.0, slot=None, ids=None, note=''):
    assert name not in KIT_INST, name
    KIT_INST[name] = dict(item=item, parent=parent, pos=tuple(pos) if pos is not None else None, yaw=yaw, slot=slot,
                          ids=ids or {}, note=note)


def cctv_stand(k, base, shelf_z):
    """a steel stand for two CCTV monitors (kit Kit_Monitor_CRT, 0.34 x 0.45 x 0.31) on a desk: two side frames, the
    shelf for the upper monitor, a back rail"""
    x, y, z = base
    y0, y1 = y - 0.225, y + 0.255
    for sx in (-1, 1):
        xa, xb = sorted((x + sx * 0.194, x + sx * 0.206))
        B(k, (xa, y0, z), (xb, y0 + 0.03, shelf_z - 0.012), F.Z_STEELF)       # the posts, front and back
        B(k, (xa, y1 - 0.03, z), (xb, y1, shelf_z - 0.012), F.Z_STEELF)
        B(k, (xa, y0, z), (xb, y1, z + 0.025), F.Z_STEELF)                     # the foot rail
        B(k, (xa, y0, shelf_z - 0.045), (xb, y1, shelf_z - 0.012), F.Z_STEELF)  # the rail under the shelf
    B(k, (x - 0.212, y0, shelf_z - 0.012), (x + 0.212, y1, shelf_z), F.Z_STEELF)  # the shelf
    B(k, (x - 0.194, y1 - 0.03, z + 0.20), (x + 0.194, y1 - 0.012, z + 0.23), F.Z_STEELF)   # the back rail


def leitstand():
    k = R('Leitstand')
    # two control consoles under the window band: plinth, operator shelf, the sloped instrument panel, a flat top
    for x0, x1 in ((0.90, 3.90), (4.10, 7.11)):
        console(k, x0, x1, -5.65, -4.92)
    # three workstations along the corridor wall: desk, drawer pedestal (Update 3 drawers), CRT, keyboard, PC under it
    peds = {-1.55: ('IX_Drawer_22', 'IX_Drawer_23', 'IX_Drawer_24'), 0.45: ('IX_Drawer_25', 'IX_Drawer_26', 'IX_Drawer_27'),
            2.45: ('IX_Drawer_28', 'IX_Drawer_29', 'IX_Drawer_30')}
    for (x0, x1), px in zip(((-1.80, -0.20), (0.20, 1.80), (2.20, 3.80)), (-1.55, 0.45, 2.45)):
        desk(k, x0, x1, -1.95, -1.15, top_z=0.75, front='-y', pedestal_x=px)
        pedestal(k, peds[px], NY, (px - 0.20, -1.88, 0.0), (px + 0.20, -1.25, 0.72))
        if x0 == 2.20:            # KPP v2.1: the right one is the gate station (kit instances below), not a terminal
            cctv_stand(k, LEIT_CCTV, LEIT_SHELF)
        else:
            crt(k, Vector((x0 + 0.90, -1.42, 0.75)), yaw=0)
            keyboard(k, Vector((x0 + 0.90, -1.78, 0.75)))
        pc_tower(k, Vector((x0 + 1.35, -1.55, 0.0)))
        office_chair(k, ((x0 + x1) / 2 - 0.10, -2.30, 0.0), yaw=180)
    # the base's gate station (KPP v2.1, QUESTIONS_KPP 9): the KPP's two cameras on the stand (the barrier below, the gate
    # above) and the second SCHRANKE / TOR console; all of it on the station's power (after S7)
    kit_inst('Leit_Monitor_Barrier', 'Kit_Monitor_CRT', 'R_Leitstand', LEIT_CCTV,
             note='CCTV monitor (lower): the KPP barrier camera - CAM_Barrier of kpp_contract.json, with the station\'s power')
    kit_inst('Leit_Monitor_Gate', 'Kit_Monitor_CRT', 'R_Leitstand', (LEIT_CCTV.x, LEIT_CCTV.y, LEIT_SHELF),
             note='CCTV monitor (upper, on the stand\'s shelf): the gate camera - CAM_Gate of kpp_contract.json')
    kit_inst('Leit_Console', 'Kit_Console_2', 'R_Leitstand', LEIT_CONSOLE[0], LEIT_CONSOLE[1],
             note='the base\'s gate console: SCHRANKE / BARRIER (left), TOR / GATE (right); the same as the KPP\'s')
    for i, (lab, num_, what) in enumerate((('Schranke', 319, 'the barrier'), ('Tor', 320, 'the gate'))):
        kit_inst(f'Leit_Btn_{lab}', 'Kit_Console_Button', 'Leit_Console', slot=('Leit_Console', f'Slot_Button_{i + 1}'),
                 ids={'IX_ConsoleButton': num_}, note=f'raises / lowers {what} like the KPP\'s button (station power)' if i == 0 else
                 f'opens / closes {what} like the KPP\'s button (station power)')
        kit_inst(f'Leit_Lbl_{lab}', f'Kit_Console_Label_{lab}', 'Leit_Console', slot=('Leit_Console', f'Slot_Label_{i + 1}'),
                 note='its label')
    phone_desk(k, Vector((1.35, -1.40, 0.75)))
    for c in ((2.60, -4.21), (5.80, -4.21)):
        office_chair(k, c + (0.0,), yaw=0)
    # the map table, its chair; the filing cabinets (Update 3 drawers), the wall display and clock on the partition
    map_table(k, -3.80, -2.00, -4.00, -3.00)
    wood_chair(k, (-3.44, -4.03, 0.0), yaw=180)
    wood_chair(k, (-2.26, -2.975, 0.0), yaw=0)
    pedestal(k, ('IX_Drawer_31', 'IX_Drawer_32', 'IX_Drawer_33', 'IX_Drawer_34'), PY, (-4.99, -5.65, 0.0), (-4.51, -5.03, 1.32))
    binders(k, Vector((-4.75, -5.40, 1.32)), n=5, along=PX)
    pedestal(k, ('IX_Drawer_35', 'IX_Drawer_36', 'IX_Drawer_37'), PX, (-5.10, -4.79, 0.0), (-4.48, -4.32, 1.32))
    top_front(k, 'IX_Drawer_37', PX, 1.30)
    wall_display(k, -5.10, -4.15, -1.65, 0.95, 2.35)
    clock(k, (2.0, -1.15, 2.30), NY, r=0.15)
    whiteboard(k, (6.00, -1.15, 1.45), NY, 1.68, 1.08)
    radiator(k, -3.55, -2.14, -5.65, 1, axis='y')
    radiator(k, -5.25, -4.04, 7.65, -1, axis='x')
    radiator(k, -3.55, -2.34, 7.65, -1, axis='x')
    for c in ((-2.0, -3.4), (4.0, -3.4)):
        smoke_detector(k, (c[0], c[1], S.EG_SC))
    for x in (-0.95, 1.05, 3.05):
        socket_outlet(k, (x, -1.15, 0.30), NY)
    socket_outlet(k, (7.65, -1.60, 0.30), NX)
    socket_outlet(k, (0.70, -5.65, 0.30), PY)
    speaker(k, (-5.10, -1.40, 2.45), PX)
    rocker_switch('IX_LightSwitch_Leitstand_89', NY, 'light switch (Leitstand)', k_room=k, pair='IX_ShutterSwitch_Leitstand_128')
    rocker_switch('IX_ShutterSwitch_Leitstand_128', NY, 'roller shutters, electric (Leitstand): all six curtains; needs mains')


def console(k, x0, x1, yw, yf):
    """a 70s control desk: the operator side at yf (north), the wall side at yw: kick plinth, front, the writing shelf,
    the sloped instrument panel (lamps, key switches, meters in the texture), two small monitors set in, a flat top"""
    prof = [(yf, 0.06), (yf, 0.72), (yf - 0.24, 0.72), (yf - 0.24, 0.78), (yw + 0.16, 1.40), (yw, 1.43), (yw, 0.0),
            (yf - 0.06, 0.0), (yf - 0.06, 0.06)]
    poly = [(y, z) for y, z in prof]
    a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if a < 0:
        poly = list(reversed(poly))
    edges = []
    for i in range(len(poly)):
        (ya, za), (yb, zb) = poly[i], poly[(i + 1) % len(poly)]
        sloped = abs(yb - ya) > 0.05 and abs(zb - za) > 0.05
        edges.append(F.Z_CONSOLEP if sloped else F.Z_CONSOLE)
    K.prism_x(k, poly, x0, x1, F.Z_CONSOLE, F.Z_CONSOLE, edges=edges)
    # the writing shelf's laminate and a dark bumper, the panel's frame strips, two monitors set into the slope
    B(k, (x0 + 0.02, yf - 0.24, 0.72), (x1 - 0.02, yf + 0.02, 0.745), F.Z_DESKTOP)
    B(k, (x0 + 0.02, yf + 0.0, 0.70), (x1 - 0.02, yf + 0.025, 0.745), F.Z_RUBBERB)
    n = Vector((0, 0.62, 0.36)).normalized() * -1 if False else Vector((0, 0.36, 0.62)).normalized()
    n = Vector((0, 1, 0)) * 0.0 + n
    for i, xm in enumerate((x0 + 0.55, x1 - 0.55)):
        c = Vector((xm, (yf - 0.24 + yw + 0.16) / 2, (0.78 + 1.40) / 2))
        R_ = Matrix((Vector((1, 0, 0)), Vector((0, -0.62, 0.36)).normalized(), n)).transposed()
        VM.obox(k, c + n * 0.01, (0.36, 0.28, 0.03), F.Z_STEELBLK if hasattr(F, 'Z_STEELBLK') else Z_STEELBLK, R_)
        VM.obox(k, c + n * 0.027, (0.30, 0.22, 0.004), F.Z_SCREENP, R_)
    for xx in (x0 + 1.10, (x0 + x1) / 2, x1 - 1.10):                  # rows of key switches / push buttons
        for j in range(3):
            t = 0.25 + j * 0.25
            p = Vector((xx, yf - 0.24 + t * (yw + 0.16 - (yf - 0.24)), 0.78 + t * (1.40 - 0.78)))
            for m in range(5):
                q = p + Vector((m * 0.05 - 0.10, 0, 0))
                k.cyl(q, q + n * 0.015, 0.009, F.Z_LED if (m + j) % 2 else F.Z_HANDLEB, 8)


def crt(k, base, yaw=0.0):
    """a CRT monitor (beige), screen toward the user"""
    R_ = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    VM.rbox(k, base + Vector((0, 0, 0.012)), (0.26, 0.22, 0.024), F.Z_PCBEIGE, r=0.02, ch=0.005)
    VM.obox(k, base + R_ @ Vector((0, 0.03, 0.06)), (0.10, 0.08, 0.08), F.Z_PCBEIGE, R_)
    VM.obox(k, base + R_ @ Vector((0, 0.02, 0.26)), (0.38, 0.34, 0.33), F.Z_CRT, R_)
    VM.obox(k, base + R_ @ Vector((0, 0.17, 0.25)), (0.26, 0.10, 0.24), F.Z_CRT, R_)
    VM.obox(k, base + R_ @ Vector((0, -0.150, 0.265)), (0.30, 0.012, 0.24), F.Z_SCREENP, R_)


def keyboard(k, c):
    VM.rbox(k, c + Vector((0, 0, 0.015)), (0.46, 0.17, 0.03), F.Z_KEYB, r=0.01, ch=0.004)


def pc_tower(k, c):
    VM.rbox(k, c + Vector((0, 0, 0.21)), (0.19, 0.44, 0.42), F.Z_PCBEIGE, r=0.008, ch=0.004)


def papers(k, c, n=3, w=0.21, h=0.297):
    for i in range(n):
        a = math.radians((i * 37) % 23 - 11)
        R_ = Matrix.Rotation(a, 3, 'Z')
        VM.obox(k, c + Vector((i * 0.03, i * 0.02, 0.002 + i * 0.002)), (w, h, 0.002), F.Z_PAPER, R_)


def mug(k, c):
    k.cyl(c, c + Vector((0, 0, 0.095)), 0.04, F.Z_MUG, 10)
    k.tube([c + Vector((0.04, 0, 0.075)), c + Vector((0.065, 0, 0.06)), c + Vector((0.04, 0, 0.025))], 0.007, F.Z_MUG, 5)


def phone_desk(k, c):
    VM.rbox(k, c + Vector((0, 0, 0.04)), (0.22, 0.20, 0.08), F.Z_PHONE, r=0.02, ch=0.008)
    k.cyl(c + Vector((-0.09, 0.04, 0.095)), c + Vector((0.09, 0.04, 0.095)), 0.022, F.Z_PHONE, 8)


def binders(k, c, n=5, along=(1, 0, 0), zone=None):
    along = Vector(along)
    for i in range(n):
        p = c + along * (i * 0.075 - n * 0.0375)
        size = (0.07, 0.28, 0.31) if abs(along.x) > 0.5 else (0.28, 0.07, 0.31)
        B(k, p - Vector((size[0] / 2, size[1] / 2, 0)), p + Vector((size[0] / 2, size[1] / 2, size[2])),
          zone or (F.Z_BINDER if i % 2 else F.Z_OLIVE))


def map_table(k, x0, x1, y0, y1):
    """the map table (Update 3: laminate top 0.73..0.76 on steel legs; mugs, papers and the control log of Update 3 lie on
    it): the topographic map, a paper stack, the ruler, a mug"""
    rb(k, (x0, y0, 0.73), (x1, y1, 0.76), F.Z_LAMINATE, r=0.006, ch=0.003)
    for x, y in ((x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05), (x0 + 0.05, y1 - 0.05), (x1 - 0.05, y1 - 0.05)):
        B(k, (x - 0.02, y - 0.02, 0.0), (x + 0.02, y + 0.02, 0.73), F.Z_STEELF)
    for (a, b) in (((x0 + 0.07, y0 + 0.04), (x1 - 0.07, y0 + 0.06)), ((x0 + 0.07, y1 - 0.06), (x1 - 0.07, y1 - 0.04))):
        B(k, (a[0], a[1], 0.66), (b[0], b[1], 0.73), F.Z_STEELF)
    B(k, (-2.385, -3.40, 0.76), (-2.175, -3.10, 0.77), F.Z_PAPER)
    B(k, (-2.525, -3.815, 0.76), (-2.175, -3.785, 0.765), Z_STEELBLK)
    mug(k, Vector((-2.30, -3.75, 0.76)))


def top_front(k, name, n, z_top):
    """the fixed front closing a filing cabinet above its last Update 3 drawer"""
    lo, hi = lohi(name)
    p = Vector(X.IX[name]['pivot'])
    n = Vector(n)
    ax = 0 if abs(n.x) > 0.5 else 1
    a0, a1 = sorted((p[ax], p[ax] - n[ax] * 0.018))
    if ax == 0:
        B(k, (a0, lo.y + 0.003, hi.z + 0.02), (a1, hi.y - 0.003, z_top), F.Z_DRAWER)
    else:
        B(k, (lo.x + 0.003, a0, hi.z + 0.02), (hi.x - 0.003, a1, z_top), F.Z_DRAWER)


def wall_display(k, x_wall, y0, y1, z0, z1):
    """the station's overview display on the partition: a dark mimic panel in a steel frame (texture: the antenna field)"""
    B(k, (x_wall, y0 - 0.04, z0 - 0.04), (x_wall + 0.06, y1 + 0.04, z1 + 0.04), F.Z_STEELF, skip=('-x',))
    B(k, (x_wall + 0.06, y0, z0), (x_wall + 0.07, y1, z1), F.Z_SCREEN, skip=('-x',))


def whiteboard(k, c, n, w, h):
    c, n = Vector(c), Vector(n)
    wall_box(k, c, n, w + 0.04, h + 0.04, 0.02, F.Z_STEELF)
    wall_box(k, c + n * 0.02, n, w, h, 0.004, F.Z_BOARD)
    u = Vector((0, 0, 1)).cross(n).normalized()
    wall_box(k, c - Vector((0, 0, h / 2 + 0.03)) + n * 0.02, n, w * 0.8, 0.02, 0.06, F.Z_STEELF)


def windfang():
    k = R('Windfang')
    locker_unit(k, ('IX_LockerDoor_20', 'IX_LockerDoor_21'), (-5.75, -5.00, 0.0), (-5.25, -3.98, 1.80), NX, single=True)
    # coat rack with jackets, boots under it, a shovel and a broom by the door, the doormat, the intercom
    coat_rack(k, -7.65, -3.68, -2.52, 1.70)
    for y in (-2.80, -3.10, -3.40):
        boots(k, Vector((-7.45, y, 0.0)))
    shovel(k, Vector((-7.38, -4.80, 0.0)), lean=(-1.0, 0.0))
    broom(k, Vector((-7.25, -5.36, 0.0)))
    B(k, (-6.95, -5.55, 0.004), (-5.95, -4.90, 0.016), F.Z_MAT)
    call_point(k, (-5.50, -5.65, 1.45), PY)                                   # beside the door (its niche: the bar)
    extinguisher(k, (-5.25, -2.12, 0.52), NX)
    smoke_detector(k, (-6.45, -2.50, S.EG_C))
    rocker_switch('IX_LightSwitch_Windfang_84', NY, 'light switch (Windfang)', k_room=k, pair='IX_LightSwitch_Exterior_102')
    rocker_switch('IX_LightSwitch_Exterior_102', NY, 'outside light (the yard floods, the entrance lamp)')


def coat_rack(k, x_wall, y0, y1, z):
    B(k, (x_wall, y0, z - 0.10), (x_wall + 0.02, y1, z + 0.02), F.Z_WOODF, skip=('-x',))
    for i in range(6):
        y = y0 + 0.10 + i * (y1 - y0 - 0.20) / 5
        k.tube([Vector((x_wall + 0.02, y, z - 0.04)), Vector((x_wall + 0.09, y, z - 0.04)), Vector((x_wall + 0.11, y, z))],
               0.008, F.Z_CHROME, 6)
    jacket(k, Vector((x_wall + 0.10, y0 + 0.30, z - 0.05)), F.Z_JACKET)
    jacket(k, Vector((x_wall + 0.10, y0 + 0.75, z - 0.05)), F.Z_FABRIC_G)


def jacket(k, top, zone):
    """a jacket hanging by its loop from a hook on a west wall (+x into the room): the collar, the body falling from
    narrow shoulders to the hem and settling back against the wall (rounded sections), the sleeves hanging at its
    sides a little forward, the cuffs"""
    from van2_kit import rrect
    uy, ux = Vector((0, 1, 0)), Vector((1, 0, 0))                    # width along y, thickness along x
    secs = [(0.00, 0.10, 0.05, 0.020, 0.000), (-0.04, 0.26, 0.09, 0.030, 0.000), (-0.09, 0.40, 0.11, 0.045, -0.010),
            (-0.30, 0.44, 0.13, 0.050, -0.025), (-0.55, 0.42, 0.12, 0.050, -0.035), (-0.70, 0.45, 0.11, 0.040, -0.040)]
    rings = [rrect(top + Vector((0.06 + dx, 0, dz)), uy, ux, w, d, r) for dz, w, d, r, dx in secs]
    k.loft(rings, [zone] * (len(rings) - 1), cap0=zone, cap1=zone)
    for sg in (-1, 1):
        sh = top + Vector((0.07, sg * 0.18, -0.11))
        arm = [sh, sh + Vector((0.012, sg * 0.045, -0.22)), sh + Vector((0.020, sg * 0.040, -0.50))]
        k.tube(arm, 0.046, zone, 8)
        k.cyl(arm[-1], arm[-1] + Vector((0.004, 0, -0.03)), 0.040, zone, 8)


def boots(k, c):
    for dy in (-0.05, 0.05):
        p = c + Vector((0, dy, 0))
        VM.rbox(k, p + Vector((0.03, 0, 0.04)), (0.28, 0.10, 0.08), F.Z_BOOT, r=0.03, ch=0.01)
        VM.rbox(k, p + Vector((-0.06, 0, 0.17)), (0.12, 0.10, 0.22), F.Z_BOOT, r=0.03, ch=0.01)


def shovel(k, base, lean=(0.0, 1.0)):
    """a snow shovel leaning against the wall: the blade on the floor, the handle's top toward `lean`"""
    d = Vector((lean[0] * 0.20, lean[1] * 0.20, 1.30)).normalized()
    top = base + d * 1.30
    k.cyl(base + d * 0.30, top, 0.016, F.Z_WOODF, 8)
    side = Vector((0, 0, 1)).cross(Vector((lean[0], lean[1], 0))).normalized()
    k.cyl(top - side * 0.07, top + side * 0.07, 0.014, F.Z_RUBBERB, 6)
    R_ = Matrix((side, Vector((lean[0], lean[1], 0)).normalized(), Vector((0, 0, 1)))).transposed()
    VM.obox(k, base + d * 0.16, (0.36, 0.02, 0.34), Z_STEELBLK, R_)


def broom(k, base):
    """a broom leaning into the corner: the red head along y on the floor, the stick's top at the west wall"""
    top = base + Vector((-0.36, -0.02, 1.27))
    k.cyl(base + Vector((0, 0, 0.10)), top, 0.013, F.Z_WOODF, 8)
    B(k, base + Vector((-0.04, -0.20, 0.0)), base + Vector((0.04, 0.20, 0.12)), F.Z_DRUM_R)


def flur_eg():
    k = R('Flur_EG')
    extinguisher(k, (7.28, -1.00, 0.52), PY)
    phone(k, (-3.02, 1.00, 1.35), NY)
    alarm_bell(k, (0.60, -1.00, 2.45), PY)
    hose_cabinet(k, (-1.40, -1.00, 1.20), PY)
    call_point(k, (7.65, 0.85, 1.45), NX)
    call_point(k, (1.25, 1.00, 1.45), NY)
    speaker(k, (-4.60, -1.00, 2.48), PY)
    for x in (-3.80, 3.80):
        smoke_detector(k, (x, 0.0, S.EG_SC))
    rocker_switch('IX_LightSwitch_Flur_EG_85', NY, 'light switch (corridor, ground floor) by the stair door', k_room=k)
    rocker_switch('IX_LightSwitch_Flur_EG_86', PY, 'light switch (corridor, ground floor) by the lobby door', k_room=k)
    rocker_switch('IX_LightSwitch_Serverraum_93', PY, 'light switch (Serverraum) by its door', k_room=R('Serverraum'))
    socket_outlet(k, (-6.00, 1.00, 0.30), NY)
    socket_outlet(k, (5.00, -1.00, 0.30), PY)


def hose_cabinet(k, c, n):
    """the wall hydrant: a red steel cabinet with a glass window, the hose reel inside"""
    wall_box(k, c, n, 0.70, 0.70, 0.40, F.Z_EXTING)
    c, n = Vector(c), Vector(n)
    wall_box(k, c + n * 0.40, n, 0.56, 0.56, 0.004, F.Z_SCREEN)


def evac_plan(k, c, n):
    """the evacuation plan (DIN ISO 23601: green head, the floor plan) in a frame; its print is in the panel atlas"""
    wall_box(k, c, n, 0.44, 0.32, 0.012, F.Z_STEELF)
    wall_box(k, Vector(c) + Vector(n) * 0.012, n, 0.42, 0.30, 0.002, F.Z_PAPER)


def lager():
    k = R('Lager')
    for (y0, y1) in ((1.28, 3.33), (3.48, 5.52)):
        shelving(k, -2.47, -1.95, y0, y1, 2.30, facing=NX)
    shelving(k, -7.65, -7.13, 3.79, 5.57, 2.28, facing=PX)
    # the crates and loaded pallets where Update 3 set them down, each turned a little (its boxes measured as oriented
    # boxes: centre, size along / across its yaw, yaw, bottom, top)
    for c, sz, yaw, z0, z1, z in (((-5.961, 5.173), (0.839, 0.600), 13.7, 0.0, 0.599, F.Z_PALLET),
                                  ((-5.818, 4.249), (0.934, 0.667), 10.8, 0.0, 0.667, F.Z_CRATE),
                                  ((-4.857, 4.216), (1.061, 0.758), 13.1, 0.0, 0.758, F.Z_CRATE),
                                  ((-4.095, 4.986), (0.812, 0.580), 3.7, 0.0, 0.580, F.Z_PALLET),
                                  ((-5.818, 4.249), (0.500, 0.350), 22.9, 0.667, 1.067, F.Z_CRATE)):
        F.crate_yaw(k, c, sz, yaw, z0, z1, z)
    cardboard(k, -7.39, -6.91, 1.23, 1.98, 0.84)
    rocker_switch('IX_LightSwitch_Lager_88', PY, 'light switch (Lager), surface box', k_room=None)
    junction_box(k, (-4.28, 1.15, 1.05), PY)
    socket_outlet(k, (-3.20, 1.15, 1.10), PY, kind='surface')
    for x, zb in ((-4.28, 2.92), (-3.20, 2.57)):
        conduit_run(k, [Vector((x, 1.17, 1.15)), Vector((x, 1.17, zb - 0.04))])
        junction_box(k, (x, 1.15, zb), PY)
        conduit_run(k, [Vector((x, 1.17, zb + 0.04)), Vector((x, 1.17, S.EG_C - 0.02))])
    smoke_detector(k, (-4.80, 3.40, S.EG_C))


def shelving(k, x0, x1, y0, y1, h, facing=(1, 0, 0), levels=5, zf=0.0):
    """steel shelving (4 cm uprights, galvanised shelves from 0.087 to h - 0.063 as in Update 3) loaded with boxes,
    binders and folded tarps; zf = the floor"""
    for x in (x0 + 0.02, x1 - 0.02):
        for y in (y0 + 0.02, y1 - 0.02):
            B(k, (x - 0.02, y - 0.02, zf), (x + 0.02, y + 0.02, zf + h), F.Z_STEELF)
    for i in range(levels):
        z = zf + 0.087 + i * (h - 0.15) / (levels - 1)
        B(k, (x0 + 0.01, y0 + 0.01, z), (x1 - 0.01, y1 - 0.01, z + 0.025), Z_GALV)
        if i < levels - 1:
            # boxes on the shelf
            n = int((y1 - y0) / 0.42)
            for j in range(n):
                ya = y0 + 0.05 + j * (y1 - y0 - 0.1) / n
                hh = 0.18 + ((i * 7 + j * 3) % 5) * 0.03
                if (i + j) % 4 == 3:
                    continue
                zone = (F.Z_CRATE, F.Z_CARDBOX, F.Z_OLIVE, F.Z_BINDER)[(i * 3 + j) % 4]
                B(k, (x0 + 0.04, ya, z + 0.025), (x1 - 0.06, ya + (y1 - y0 - 0.1) / n - 0.03, z + 0.025 + hh), zone)


def pallet_crates(k, x0, x1, y0, y1):
    B(k, (x0, y0, 0.0), (x1, y1, 0.12), F.Z_PALLET)
    nx = int((x1 - x0) / 0.62)
    for i in range(nx):
        for j in range(2):
            xa = x0 + 0.02 + i * (x1 - x0) / nx
            ya = y0 + 0.02 + j * (y1 - y0) / 2
            h = 0.38 if (i + j) % 2 else 0.45
            VM.rbox(k, Vector((xa + (x1 - x0) / nx / 2 - 0.01, ya + (y1 - y0) / 4 - 0.01, 0.12 + h / 2)),
                    ((x1 - x0) / nx - 0.04, (y1 - y0) / 2 - 0.04, h), F.Z_CRATE, r=0.01, ch=0.005)
            if (i + j) % 3 == 0:
                VM.rbox(k, Vector((xa + (x1 - x0) / nx / 2 - 0.01, ya + (y1 - y0) / 4 - 0.01, 0.12 + h + 0.20)),
                        ((x1 - x0) / nx - 0.10, (y1 - y0) / 2 - 0.10, 0.40), F.Z_CRATE, r=0.01, ch=0.005)


def cardboard(k, x0, x1, y0, y1, h):
    n = 3
    for i in range(n):
        z0 = i * h / n
        d = 0.02 * ((i * 5) % 3 - 1)
        B(k, (x0 + d, y0, z0), (x1 + d, y1, z0 + h / n - 0.005), F.Z_CARDBOX)


def serverraum():
    k = R('Serverraum')
    xs = [(2.30, 2.90), (2.92, 3.52), (3.54, 4.14), (4.16, 4.76), (4.78, 5.38), (5.40, 6.00), (6.02, 6.62)]
    for i, (x0, x1) in enumerate(xs):
        rack(k, x0, x1, 4.757, 5.65, 2.00, f'IX_RackDoor_{38 + i}', seed=i)
    # the cable tray over the racks, cables dropping into them
    B(k, (2.25, 5.00, 2.20), (6.65, 5.37, 2.25), F.Z_TRAY)
    for x in (2.25, 6.65):
        B(k, (x - 0.01, 5.00, 2.25), (x + 0.01, 5.37, 2.33), F.Z_TRAY)
    for x in (2.6, 3.2, 3.8, 4.5, 5.1, 5.7, 6.3):
        k.tube([Vector((x, 5.20, 2.26)), Vector((x + 0.02, 5.20, 2.12)), Vector((x, 5.25, 2.01))], 0.012, F.Z_CABLE, 5)
    for x in (2.4, 4.0, 6.5):
        B(k, (x - 0.01, 5.10, 2.25), (x + 0.01, 5.27, S.EG_SC), F.Z_STEELF)
    # the distribution board on the east wall with its breakers and isolator (Update 3 parts)
    dist_board(k, 'x', 7.65, -1, 2.70, 3.50, 0.75, 1.85, ['IX_Breaker_%d' % i for i in range(45, 51)], 'IX_Isolator_51')
    # UPS cabinet and CEE sockets on the tower wall, conduits up
    B(k, (1.95, 3.40, 0.0), (2.55, 4.10, 1.10), F.Z_RACK)
    B(k, (2.55, 3.45, 0.30), (2.56, 4.05, 0.95), F.Z_RACKEQ)
    socket_outlet(k, (1.95, 2.00, 0.44), PX, kind='cee_blue')
    socket_outlet(k, (1.95, 2.50, 0.44), PX, kind='cee_blue')
    terminal_rack(k, 7.05, 7.65, 1.60, 2.10, 0.90)
    for y in (2.00, 2.50):
        conduit_run(k, [Vector((1.97, y, 0.55)), Vector((1.97, y, S.EG_SC - 0.02))])
    extinguisher(k, (7.65, 1.60, 0.52), NX)
    smoke_detector(k, (4.80, 3.40, S.EG_SC))


def terminal_rack(k, x0, x1, y0, y1, h):
    """the low terminal rack by the door (Update 3: 0.90 high; a mug and papers of Update 3 lie on it): black cabinet,
    a modem shelf with LEDs, a small monitor set into its front"""
    B(k, (x0, y0, 0.0), (x1, y1, h), F.Z_RACK)
    B(k, (x0 - 0.004, y0 + 0.05, 0.50), (x0, y1 - 0.05, 0.80), F.Z_RACKEQ)
    B(k, (x0 - 0.006, y0 + 0.10, 0.55), (x0 - 0.004, y1 - 0.10, 0.75), F.Z_SCREENP)
    for i in range(3):
        z = 0.12 + i * 0.12
        B(k, (x0 - 0.004, y0 + 0.04, z), (x0, y1 - 0.04, z + 0.08), F.Z_RACKEQ)
        for j in range(5):
            k.cyl(Vector((x0 - 0.004, y0 + 0.08 + j * 0.035, z + 0.06)), Vector((x0 - 0.008, y0 + 0.08 + j * 0.035, z + 0.06)),
                  0.004, F.Z_LED, 6)


def rack(k, x0, x1, y0, y1, h, door, seed=0):
    """a 19-inch rack: black frame, side panels, equipment units with LEDs behind the Update 3 door"""
    B(k, (x0, y0 + 0.03, 0.0), (x1, y1, h), F.Z_RACK, skip=('-y',))
    B(k, (x0, y0, 0.0), (x0 + 0.04, y0 + 0.03, h), F.Z_RACK)
    B(k, (x1 - 0.04, y0, 0.0), (x1, y0 + 0.03, h), F.Z_RACK)
    B(k, (x0 + 0.04, y0, h - 0.10), (x1 - 0.04, y0 + 0.03, h), F.Z_RACK)
    B(k, (x0 + 0.04, y0, 0.0), (x1 - 0.04, y0 + 0.03, 0.10), F.Z_RACK)
    z = 0.12
    i = 0
    while z < h - 0.20:
        u = 1 + ((seed * 3 + i * 7) % 4)
        hh = u * 0.0445
        if (seed + i) % 5 != 4:
            B(k, (x0 + 0.06, y0 + 0.05, z), (x1 - 0.06, y0 + 0.07, z + hh - 0.004),
              F.Z_RACKEQ if (seed + i) % 3 else F.Z_CRT)
        z += hh
        i += 1
    d = hinged_door(door, Vector(NY), F.Z_RACKDOOR, th=0.02, handle='bar', note='rack door')
    lo, hi = lohi(door)
    kg = kb(door + '_Glass', 'glass')
    p = Vector(X.IX[door]['pivot'])
    for side in (1, -1):
        yy = p.y - 0.01 + side * 0.011
        face(kg, [(lo.x + 0.06, yy, lo.z + 0.15), (hi.x - 0.06, yy, lo.z + 0.15), (hi.x - 0.06, yy, hi.z - 0.15),
                  (lo.x + 0.06, yy, hi.z - 0.15)], 0, (0, side, 0))
    part(door + '_Glass', 'static', p, parent=door, note='the rack door\'s smoked glass')


def dist_board(k, axis, a_wall, n_sign, u0, u1, z0, z1, breakers, isolator=None, panel_door=None):
    """a wall distribution board: steel box, the DIN rail row of breakers (Update 3 parts), the isolator, a door. The
    toggles (Update 3: 3 x 4 cm above their pivots) tip 45 deg back into their breakers: the board's front stands 3.5 cm
    behind the pivots, each breaker's body recessed above the pivot where its toggle goes"""
    ia = 0 if axis == 'x' else 1
    pa_ = X.IX[breakers[0]]['pivot'][ia]
    af = pa_ - n_sign * 0.035                                        # the board's front
    a0, a1 = sorted((a_wall, af))
    if axis == 'x':
        B(k, (a0, u0, z0), (a1, u1, z1), F.Z_BOARDC)
    else:
        B(k, (u0, a0, z0), (u1, a1, z1), F.Z_BOARDC)
    for nm in breakers:
        bk = ix_part(nm, note='circuit breaker toggle, 0..45 deg')
        p = Vector(X.IX[nm]['pivot'])
        lo, hi = lohi(nm)
        B(bk, lo, hi, F.Z_BREAKER)
        # the breaker's body on the rail: below the pivot its face 2 mm behind it, above it 3.1 cm (the toggle's recess)
        for (za, zb, dep) in ((p.z - 0.045, p.z - 0.001, 0.002), (p.z - 0.001, p.z + 0.045, 0.031)):
            b0, b1 = sorted((af, p[ia] - n_sign * dep))
            if axis == 'x':
                B(k, (b0, p.y - 0.009, za), (b1, p.y + 0.009, zb), F.Z_RUBBERB)
            else:
                B(k, (p.x - 0.009, b0, za), (p.x + 0.009, b1, zb), F.Z_RUBBERB)
    if isolator:
        ik = ix_part(isolator, note='rotary isolator, 0..90 deg')
        lo, hi = lohi(isolator)
        p = Vector(X.IX[isolator]['pivot'])
        n = Vector((n_sign, 0, 0)) if axis == 'x' else Vector((0, n_sign, 0))
        b0, b1 = sorted((af, p[ia] - n_sign * 0.002))
        if axis == 'x':
            B(k, (b0, p.y - 0.06, p.z - 0.06), (b1, p.y + 0.06, p.z + 0.06), F.Z_BAR)
        else:
            B(k, (p.x - 0.06, b0, p.z - 0.06), (p.x + 0.06, b1, p.z + 0.06), F.Z_BAR)
        ik.cyl(p, p + n * 0.025, 0.028, F.Z_MAINSW, 14)
        u = Vector((0, 1, 0)) if axis == 'x' else Vector((1, 0, 0))
        VM.obox(ik, p + n * 0.045, (0.03, 0.17, 0.035) if axis == 'x' else (0.17, 0.03, 0.035), F.Z_MAINSW,
                Matrix.Identity(3))


def garage():
    k = R('Garage')
    shelving(k, -17.70, -17.18, -0.22, 1.62, 1.60, facing=PX, levels=4, zf=S.G_F)
    shelving(k, -17.70, -17.18, 1.88, 3.72, 1.60, facing=PX, levels=4, zf=S.G_F)
    quad_bike(k, Vector((-12.40, 1.60, S.G_F)))
    workbench(k, -11.20, -9.20, 3.95, 4.70)
    drum(k, Vector((-17.25, 4.20, S.G_F)), F.Z_DRUM_B)
    drum(k, Vector((-16.62, 4.25, S.G_F)), F.Z_DRUM_R)
    drum(k, Vector((-16.88, 3.40, S.G_F)), F.Z_DRUM_B)                  # (Update 3 had it inside the shelving)
    jerrycan(k, Vector((-16.15, 4.35, S.G_F)), F.Z_DRUM_R)
    jerrycan(k, Vector((-15.90, 4.35, S.G_F)), F.Z_JERRY)
    for c, sz, yaw, z0, z1, z in (((-9.289, -3.699), (0.934, 0.668), 37.6, S.G_F, 0.517, F.Z_CRATE),
                                  ((-9.289, -3.699), (0.500, 0.350), 52.9, 0.517, 0.917, F.Z_CRATE),
                                  ((-9.486, -2.722), (0.943, 0.674), 28.6, S.G_F, 0.523, F.Z_PALLET),
                                  ((-10.488, -3.272), (0.764, 0.546), 19.1, S.G_F, 0.396, F.Z_CRATE)):
        F.crate_yaw(k, c, sz, yaw, z0, z1, z)                       # (Update 3's oriented boxes, as in the store)
    for i in range(4):
        tyre(k, Vector((-8.45, 1.80, S.G_F + i * 0.21)))
    extinguisher(k, (-8.00, -2.41, 0.40), NX)
    phone(k, (-12.83, 4.70, 1.20), NY)
    first_aid(k, (-8.00, 1.80, 1.30), NX)
    call_point(k, (-10.05, -4.70, 1.30), PY)
    speaker(k, (-8.00, -2.80, 2.80), NX)
    socket_outlet(k, (-8.50, 4.70, 1.20), NY, kind='cee_red')
    conduit_run(k, [Vector((-8.50, 4.68, 1.30)), Vector((-8.50, 4.68, S.G_C - 0.02))])
    for x in (-11.45, -8.95):
        socket_outlet(k, (x, 4.70, 1.10), NY, kind='surface')
        conduit_run(k, [Vector((x, 4.68, 1.15)), Vector((x, 4.68, 2.38))])
        junction_box(k, (x, 4.70, 2.42), NY)
        conduit_run(k, [Vector((x, 4.68, 2.46)), Vector((x, 4.68, S.G_C - 0.02))])
    rocker_switch('IX_LightSwitch_Garage_87', NX, 'light switch (garage), surface box')
    junction_box(k, (-8.00, 0.77, 0.90), NX)
    conduit_run(k, [Vector((-8.02, 0.77, 0.95)), Vector((-8.02, 0.77, 2.88))])
    junction_box(k, (-8.00, 0.77, 2.92), NX)
    conduit_run(k, [Vector((-8.02, 0.77, 2.96)), Vector((-8.02, 0.77, S.G_C - 0.02))])
    smoke_detector(k, (-13.0, 0.0, S.G_C))


def quad_bike(k, c):
    """the station's quad: red plastics, a black seat, racks front and back, fat tyres (along y)"""
    for dx in (-0.48, 0.48):
        for dy in (-0.62, 0.62):
            p = c + Vector((dx, dy, 0.27))
            k.cyl(p - Vector((0.12, 0, 0)), p + Vector((0.12, 0, 0)), 0.27, F.Z_TYRE, 14)
            k.cyl(p - Vector((0.125, 0, 0)), p + Vector((0.125, 0, 0)), 0.14, F.Z_STEELF, 10)
    VM.rbox(k, c + Vector((0, 0, 0.42)), (0.62, 1.40, 0.24), F.Z_STEELF, r=0.04, ch=0.02)
    VM.rbox(k, c + Vector((0, 0.55, 0.62)), (1.10, 0.62, 0.20), F.Z_QUAD, r=0.08, ch=0.03)
    VM.rbox(k, c + Vector((0, -0.55, 0.62)), (1.10, 0.62, 0.20), F.Z_QUAD, r=0.08, ch=0.03)
    VM.rbox(k, c + Vector((0, -0.05, 0.70)), (0.36, 0.70, 0.14), F.Z_QUADSEAT, r=0.05, ch=0.02)
    VM.rbox(k, c + Vector((0, 0.32, 0.72)), (0.40, 0.30, 0.22), F.Z_QUAD, r=0.06, ch=0.02)
    k.cyl(c + Vector((0, 0.40, 0.82)), c + Vector((0, 0.36, 0.98)), 0.02, F.Z_STEELF, 6)
    k.cyl(c + Vector((-0.36, 0.38, 0.98)), c + Vector((0.36, 0.38, 0.98)), 0.014, F.Z_STEELF, 6)
    for dy, w in ((0.70, 0.9), (-0.72, 0.9)):
        for xx in (-w / 2, 0.0, w / 2):
            k.cyl(c + Vector((xx, dy - 0.15, 0.76)), c + Vector((xx, dy + 0.15, 0.76)), 0.010, F.Z_STEELF, 6)
        k.cyl(c + Vector((-w / 2, dy + 0.15, 0.76)), c + Vector((w / 2, dy + 0.15, 0.76)), 0.010, F.Z_STEELF, 6)
        k.cyl(c + Vector((-w / 2, dy - 0.15, 0.76)), c + Vector((w / 2, dy - 0.15, 0.76)), 0.010, F.Z_STEELF, 6)


def workbench(k, x0, x1, y0, y1):
    """the workbench (Update 3: top at 0.76, 0.91 over the garage floor; a tin of Update 3 stands on it): thick beech top
    on a steel frame, a drawer box, the vice; the pegboard with tools above"""
    rb(k, (x0, y0, 0.70), (x1, y1, 0.76), F.Z_WOODF, r=0.006, ch=0.003)
    for x in (x0 + 0.05, x1 - 0.05):
        for y in (y0 + 0.05, y1 - 0.05):
            B(k, (x - 0.025, y - 0.025, S.G_F), (x + 0.025, y + 0.025, 0.70), F.Z_STEELF)
    B(k, (x0 + 0.05, y0 + 0.05, S.G_F + 0.10), (x1 - 0.05, y1 - 0.05, S.G_F + 0.13), F.Z_STEELF)
    B(k, (x1 - 0.70, y0 + 0.02, 0.48), (x1 - 0.08, y1 - 0.04, 0.70), F.Z_CABGREY)
    VM.rbox(k, Vector((x0 + 0.30, y0 + 0.05, 0.83)), (0.22, 0.16, 0.14), F.Z_TOOL, r=0.01, ch=0.004)
    B(k, (x0, y1 - 0.03, 0.85), (x1, y1, 1.75), F.Z_PEGBOARD, skip=('+y',))
    for i in range(9):                                               # tools on hooks
        x = x0 + 0.15 + i * (x1 - x0 - 0.3) / 8
        h = 0.18 + (i % 3) * 0.08
        B(k, (x - 0.015, y1 - 0.05, 1.40 - h / 2), (x + 0.015, y1 - 0.03, 1.40 + h / 2), F.Z_TOOL if i % 2 else F.Z_CHROME)


def drum(k, base, zone):
    k.cyl(base, base + Vector((0, 0, 0.88)), 0.29, zone, 16)
    for z in (0.30, 0.58):
        k.cyl(base + Vector((0, 0, z - 0.012)), base + Vector((0, 0, z + 0.012)), 0.295, zone, 16)
    k.cyl(base + Vector((0.15, 0, 0.88)), base + Vector((0.15, 0, 0.90)), 0.03, F.Z_STEELF, 8)


def jerrycan(k, base, zone):
    VM.rbox(k, base + Vector((0, 0, 0.235)), (0.165, 0.345, 0.47), zone, r=0.02, ch=0.01)
    k.cyl(base + Vector((0, 0.10, 0.47)), base + Vector((0, 0.10, 0.52)), 0.022, Z_STEELBLK, 8)
    for dy in (-0.07, 0.0, 0.07):
        B(k, base + Vector((-0.012, dy - 0.012, 0.47)), base + Vector((0.012, dy + 0.012, 0.53)), zone)


def tyre(k, base):
    k.lathe(base, Vector((0, 0, 1)), [(0.0, 0.33), (0.02, 0.36), (0.18, 0.36), (0.20, 0.33)], F.Z_TYRE, 16, cap0=False,
            cap1=False)
    k.lathe(base, Vector((0, 0, 1)), [(0.20, 0.20), (0.0, 0.20)], F.Z_TYRE, 16, cap0=False, cap1=False)    # the bore
    k.lathe(base + Vector((0, 0, 0.2)), Vector((0, 0, 1)), [(0.0, 0.33), (0.0, 0.20)], F.Z_TYRE, 16, cap0=False,
            cap1=False)                                                  # the top (facing up)


# ================================================================ the stair tower (handrails, signs, switches)
def treppenhaus():
    k = R('Treppenhaus')
    ST = S.STAIR
    for (z0, z1) in S.STOREYS:
        h = (z1 - z0) / 20
        zm = z0 + 10 * h
        # wall handrails on brackets (flight A west wall, flight B east wall), the balustrade at the eye
        for x_w, sg, ya, yb, za, zb in ((-1.635, 1, 2.55, 5.07, z0, zm), (1.635, -1, 5.35, 2.83, zm, z1)):
            p0 = Vector((x_w, ya, za + 0.90 + h))
            p1 = Vector((x_w, yb, zb + 0.90))
            k.cyl(p0, p1, 0.022, F.Z_WOODF, 8)
            L = (p1 - p0).length
            for t in (0.15, 0.5, 0.85):
                q = p0 + (p1 - p0) * t
                k.cyl(q, q + Vector((-sg * 0.065, 0, -0.05)), 0.008, F.Z_STEELF, 6)
        for x_e, ya, yb, za, zb in ((-0.18, 2.55, 5.07, z0, zm), (0.18, 5.35, 2.83, zm, z1)):
            # balustrade: posts on the flight's edge, top rail, infill bars
            for t in (0.0, 0.5, 1.0):
                y = ya + (yb - ya) * t
                zz = za + (zb - za) * t
                k.cyl(Vector((x_e, y, zz)), Vector((x_e, y, zz + 0.95)), 0.016, F.Z_STEELF, 8)
            k.cyl(Vector((x_e, ya, za + 0.95)), Vector((x_e, yb, zb + 0.95)), 0.024, F.Z_WOODF, 8)
            k.cyl(Vector((x_e, ya, za + 0.45)), Vector((x_e, yb, zb + 0.45)), 0.010, F.Z_STEELF, 6)
        # the eye at the half landing: a short rail across
        k.cyl(Vector((-0.18, 5.07, zm + 0.95)), Vector((0.18, 5.35, zm + 0.95)), 0.024, F.Z_WOODF, 8)
    # at the roof landing: the rail across the eye above flight A's well
    k.cyl(Vector((-1.68, 2.58, S.ROOF + 0.95)), Vector((-0.18, 2.58, S.ROOF + 0.95)), 0.024, F.Z_WOODF, 8)
    for x in (-1.60, -0.95, -0.25):
        k.cyl(Vector((x, 2.58, S.ROOF)), Vector((x, 2.58, S.ROOF + 0.95)), 0.016, F.Z_STEELF, 8)
    # switches (surface boxes, conduits up), the floor signs, a smoke detector at the top
    for nm, z in (('IX_LightSwitch_Treppenhaus_92', S.UG_F), ('IX_LightSwitch_Treppenhaus_90', S.EG_F),
                  ('IX_LightSwitch_Treppenhaus_91', S.OG_F)):
        rocker_switch(nm, PY, 'light switch (stair tower), surface box')
        junction_box(k, (0.82, 1.15, z + 1.05), PY)
        conduit_run(k, [Vector((0.82, 1.17, z + 1.10)), Vector((0.82, 1.17, z + 2.32)), Vector((0.82, 1.17, z + 2.90))])
    smoke_detector(k, (0.0, 4.20, S.TOWER_CEIL))


def build_rooms():
    leitstand()
    windfang()
    flur_eg()
    lager()
    serverraum()
    garage()
    treppenhaus()
    import main_rooms2 as R2
    R2.build()
