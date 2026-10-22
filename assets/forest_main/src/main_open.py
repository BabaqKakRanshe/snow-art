"""Main building — openings: windows (frames, sashes, transoms, glass, inner window boards, galvanised outer sills, the
roller shutters: guide rails, the curtains IX_Shutter_* that scale up under the lintel, the box covers inside, the belt
winders IX_ShutterWinder_*), doors (steel frames wrapping the walls, leaves IX_Door_* / IX_MainDoor_1 / IX_ExitDoor_2 /
IX_RoofDoor_17 / IX_GarageDoor_19 on the Update 3 pivots, handles, closers, kick plates, the panic bar, the glass door
from the lobby), the garage's up-and-over gate IX_GarageGate_18 with its tracks.  Names, pivots, axes and ranges are the
Update 3 ones (Forest_Layout.json interactables)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, Z_GALV, Z_STEELBLK
import van3_mech as VM
import main_spec as S
import main_shell as MS

(Z_WINFRAME, Z_SASH, Z_WINHANDLE, Z_SHUTTER, Z_SHUTEND, Z_SHUTRAIL, Z_BOXCOVER, Z_STRAP, Z_WINDER, Z_DOORFRAME,
 Z_LEAF_W, Z_LEAF_S, Z_LEAF_F, Z_HANDLE, Z_KICK, Z_CLOSER, Z_ALUFRAME, Z_RUBBER, Z_GATE, Z_TRACK, Z_HINGE,
 Z_SILLOUT, Z_THRESH, Z_LOCK, Z_PANIC) = range(340, 365)
DRAFT_COL = {Z_WINFRAME: (96, 112, 92), Z_SASH: (104, 120, 100), Z_WINHANDLE: (200, 200, 196), Z_SHUTTER: (150, 152, 146),
             Z_SHUTEND: (120, 122, 118), Z_SHUTRAIL: (160, 162, 158), Z_BOXCOVER: (230, 226, 214), Z_STRAP: (90, 90, 86),
             Z_WINDER: (220, 216, 204), Z_DOORFRAME: (90, 106, 86), Z_LEAF_W: (226, 222, 210), Z_LEAF_S: (100, 116, 96),
             Z_LEAF_F: (110, 124, 104), Z_HANDLE: (196, 196, 192), Z_KICK: (170, 172, 170), Z_CLOSER: (60, 60, 58),
             Z_ALUFRAME: (180, 180, 176), Z_RUBBER: (30, 30, 30), Z_GATE: (104, 120, 100), Z_TRACK: (150, 152, 148),
             Z_HINGE: (80, 80, 78), Z_SILLOUT: (176, 178, 176), Z_THRESH: (130, 130, 126), Z_LOCK: (190, 170, 90),
             Z_PANIC: (180, 40, 30)}
FD = 0.07                      # window frame depth
FW = 0.05                      # frame / mullion width (the Update 3 panes sit 0.05 apart)


def unity_axis_to_blender(u, kind):
    """the Update 3 data gives axes in Unity (left-handed, y up); the contract is in Blender axes with 'angle -> -angle':
    a hinge's Blender axis is -map^-1(u) = (X, Z, -Y) (the same opening angles), a slide's is map^-1(u) = (-X, -Z, Y)"""
    X, Y, Z = u
    if kind == 'slide':
        return (-X + 0.0, -Z + 0.0, Y + 0.0)
    if kind == 'scale':
        return (0.0, 0.0, 1.0)
    return (X + 0.0, Z + 0.0, -Y + 0.0)


def P3(axis, a, u, z):
    return Vector((a, u, z)) if axis == 'x' else Vector((u, a, z))


def wbox(k, axis, a0, a1, u0, u1, z0, z1, zone, skip=()):
    """box given across (a), along (u) and up (z)"""
    a0, a1 = min(a0, a1), max(a0, a1)
    if axis == 'x':
        box6(k, (a0, u0, z0), (a1, u1, z1), zone, skip=skip)
    else:
        box6(k, (u0, a0, z0), (u1, a1, z1), zone, skip=skip)


def out_sign_of(wall):
    ax, a0, a1 = wall
    return 1 if abs(a1) > abs(a0) else -1


# ================================================================ windows
def window(w):
    ax, a0, a1 = w['wall']
    room = w['room']
    k = MS.rkb(room)
    kg = kb('R_' + room + '_Glass', 'glass')
    u0, u1 = w['u']
    z0, z1 = w['z']
    internal = w.get('internal')
    if internal:
        ag = (a0 + a1) / 2
        s_out = 1                                                    # the server room's glazing: corridor to the north
    else:
        s_out = out_sign_of(w['wall'])
        a_out = a1 if s_out > 0 else a0
        ag = a_out - s_out * w['glass_in']                           # the glass line
    fa0, fa1 = ag - FD / 2, ag + FD / 2
    slit = w.get('slit')
    # outer frame
    wbox(k, ax, fa0, fa1, u0, u0 + FW, z0, z1, Z_WINFRAME)
    wbox(k, ax, fa0, fa1, u1 - FW, u1, z0, z1, Z_WINFRAME)
    wbox(k, ax, fa0, fa1, u0 + FW, u1 - FW, z0, z0 + FW, Z_WINFRAME)
    wbox(k, ax, fa0, fa1, u0 + FW, u1 - FW, z1 - FW, z1, Z_WINFRAME)
    panes = w['panes']
    for (pa, pb), (qa, qb) in zip(panes[:-1], panes[1:]):           # mullions between the panes
        wbox(k, ax, fa0, fa1, pb, qa, z0 + FW, z1 - FW, Z_WINFRAME)
    zt = None
    if w.get('transom'):                                             # a top-hung light over the main panes
        zt = z1 - FW - 0.50
        wbox(k, ax, fa0, fa1, u0 + FW, u1 - FW, zt - FW / 2, zt + FW / 2, Z_WINFRAME)
    if slit:                                                         # the tower's glass slits: a bar at each storey
        for zz in (S.EG_C + 0.15, S.OG_C + 0.15):
            wbox(k, ax, fa0, fa1, u0 + FW, u1 - FW, zz, zz + FW, Z_WINFRAME)
    # sashes (room side, proud of the frame) and the glass
    n_in = -s_out
    for i, (pa, pb) in enumerate(panes):
        rows = [(z0 + FW, zt - FW / 2), (zt + FW / 2, z1 - FW)] if zt else [(z0 + FW, z1 - FW)]
        if slit:
            rows = [(z0 + FW, S.EG_C + 0.15), (S.EG_C + 0.15 + FW, S.OG_C + 0.15), (S.OG_C + 0.15 + FW, z1 - FW)]
        for ra, rb in rows:
            sw = 0.035 if not slit else 0.0
            if sw:
                sa0 = fa1 if n_in > 0 else fa0 - 0.012
                sa1 = sa0 + 0.012
                for (ua, ub, za, zb) in ((pa, pa + sw, ra, rb), (pb - sw, pb, ra, rb), (pa + sw, pb - sw, ra, ra + sw),
                                         (pa + sw, pb - sw, rb - sw, rb)):
                    wbox(k, ax, sa0, sa1, ua, ub, za, zb, Z_SASH, skip=())
            q = [P3(ax, ag, pa, ra), P3(ax, ag, pb, ra), P3(ax, ag, pb, rb), P3(ax, ag, pa, rb)]   # one glass sheet:
            nrm = Vector((s_out, 0, 0)) if ax == 'x' else Vector((0, s_out, 0))                 # the build adds its back
            face(kg, q, 0, nrm)
        # handles: every pane of a single window, every other pane of a band (Update 3: 28 in all)
        if not slit and not internal and (len(panes) <= 3 or i % 2 == 0):
            hz = min(1.25 + (w['z'][0] if w['z'][0] > 2 else 0), (z0 + z1) / 2) if z0 < 3 else min(z0 + 0.9, (z0 + z1) / 2)
            hu = pb - 0.06
            ha = fa1 + 0.012 if n_in > 0 else fa0 - 0.012
            VM.rbox(k, P3(ax, ha + n_in * 0.012, hu, hz), (0.03, 0.03, 0.08) if ax == 'y' else (0.03, 0.03, 0.08),
                    Z_WINHANDLE, r=0.006, ch=0.003)
            c = P3(ax, ha + n_in * 0.035, hu, hz - 0.05)
            box6(k, c - Vector((0.012, 0.012, 0.06)), c + Vector((0.012, 0.012, 0.0)), Z_WINHANDLE)
    if internal:
        return
    # the inner window board and the galvanised outer sill (not on the tower's slits)
    a_in = (a0 if s_out > 0 else a1)
    if not slit and z0 > S.EG_F + 0.3 or (not slit and room == 'Garage'):
        b_in0 = fa0 if s_out > 0 else fa1
        bz = z0
        wbox(k, ax, b_in0, a_in + n_in * 0.035, u0 - 0.02, u1 + 0.02, bz - 0.025, bz, MS.Z_SILLIN)
        ke = MS.ext()
        o0 = fa1 if s_out > 0 else fa0
        o1 = a_out + s_out * 0.045
        ua, ub = u0 - 0.015, u1 + 0.015
        za, zb = z0 - 0.006, z0 - 0.045                               # sloping out
        pts = [P3(ax, o0, ua, za), P3(ax, o1, ua, zb), P3(ax, o1, ub, zb), P3(ax, o0, ub, za)]
        face(ke, pts, Z_SILLOUT, (0, 0, 1))
        face(ke, [P3(ax, o1, ua, zb), P3(ax, o1, ua, zb - 0.025), P3(ax, o1, ub, zb - 0.025), P3(ax, o1, ub, zb)], Z_SILLOUT,
             Vector((s_out, 0, 0)) if ax == 'x' else Vector((0, s_out, 0)))
        for uu, sg in ((ua, -1), (ub, 1)):                           # upturned ends
            face(ke, [P3(ax, o0, uu, za), P3(ax, o1, uu, zb), P3(ax, o1, uu, zb + 0.02), P3(ax, o0, uu, za + 0.02)],
                 Z_SILLOUT, Vector((0, sg, 0)) if ax == 'x' else Vector((sg, 0, 0)))
    if w['shutters']:
        shutters(w, ax, s_out, a_out, ag, a_in, n_in)


def shutters(w, ax, s_out, a_out, ag, a_in, n_in):
    """the curtains (IX parts) in front of the glass, guide rails in the outer reveal, the box's slot under the lintel;
    inside: the box cover over the window (where the window is below the ceiling)"""
    u0, u1 = w['u']
    z0, z1 = w['z']
    ke = MS.ext()
    ac = ag + s_out * 0.055                                          # the curtain's plane (Update 3: 0.055 out of the glass)
    key = w['room'] if w['room'] != 'Flur_OG' else ('Flur_OG_E' if w['name'].endswith('_E') else 'Flur_OG_W')
    rolled = S.SHUTTER_ROLLED[key]
    for name, sa, sb in w['shutters']:
        kc = kb(name, 'MainParts')
        zb_ = z0 + 0.012
        H = z1 - zb_
        # slats: a thin box with the slat rhythm in the texture, the end bar at the bottom
        wbox(kc, ax, ac - 0.006, ac + 0.006, sa, sb, zb_ + 0.04, z1, Z_SHUTTER)
        wbox(kc, ax, ac - 0.010, ac + 0.010, sa, sb, zb_, zb_ + 0.04, Z_SHUTEND)
        piv = P3(ax, ac, (sa + sb) / 2, z1)
        part(name, 'scale', piv, axis=(0.0, 0.0, 1.0), rng=(1.0, rolled), rest=rolled, parent='BaseMain', unit='scale',
             states=['down (window closed)', 'rolled up'], open=True, speed=0.3,
             note=f'roller-shutter curtain, {sb - sa:.2f} x {H:.2f} m: scales along z under the lintel (1 = down, {rolled} = '
                  'rolled up; start rolled up)')
    # guide rails at the curtains' ends (one rail where two curtains meet)
    ends = sorted([e for _, sa, sb in w['shutters'] for e in (sa, sb)])
    rails = []
    for e in ends:
        if rails and e - rails[-1] < 0.03:
            rails[-1] = (rails[-1] + e) / 2
        else:
            rails.append(e)
    for e in rails:
        ua = max(e - 0.015, u0)
        ub = min(e + 0.015, u1)
        wbox(ke, ax, ac - 0.016, ac + 0.016, ua, ub, z0, z1, Z_SHUTRAIL)
    # the slot under the lintel (the box's bottom plate between the glass line and the facade)
    a_fr = ag + s_out * FD / 2
    wbox(ke, ax, a_fr, a_out, u0, u1, z1 - 0.012, z1, Z_SHUTRAIL, skip=('+z',))
    # inside: the box cover over the window, where the window stops below the ceiling
    if w.get('box'):
        k = MS.rkb(w['room'])
        R = S.ROOMS[w['room']]
        zt = min(z1 + 0.25, R['c'])
        wbox(k, ax, a_in, a_in + n_in * 0.07, u0 - 0.05, u1 + 0.05, z1, zt, Z_BOXCOVER, skip=('-x' if (ax == 'x' and n_in > 0) else
                                                                                             '+x' if ax == 'x' else
                                                                                             '-y' if n_in > 0 else '+y',))


def winders():
    """belt winders (IX_ShutterWinder_*): the flush plate with its slot at the Update 3 pivot, the strap up to the box"""
    L = S.WINDERS
    for name, d in L.items():
        k = kb(name, 'MainParts')
        p = Vector(d['pivot'])
        n = Vector(d['n'])
        ax = 'x' if abs(n.x) > 0.5 else 'y'
        a = p.x if ax == 'x' else p.y
        u = p.y if ax == 'x' else p.x
        wbox(k, ax, a, a + n.dot(Vector((1, 0, 0)) if ax == 'x' else Vector((0, 1, 0))) * 0.006, u - 0.04, u + 0.04,
             p.z - 0.105, p.z + 0.105, Z_WINDER)
        wbox(k, ax, a + (n.x if ax == 'x' else n.y) * 0.006, a + (n.x if ax == 'x' else n.y) * 0.009, u - 0.012, u + 0.012,
             p.z + 0.02, p.z + 0.085, Z_STRAP)
        part(name, 'hinge', p, axis=unity_axis_to_blender(d['axis_u'], 'hinge'), rng=(0.0, 0.0), parent='BaseMain',
             drives=d['drives'], open=True, note='roller-shutter belt winder: pull to lower / raise the curtain(s) it drives')
        # the strap from the plate up to the box cover (static, in the room)
        kr = MS.rkb(d['room'])
        wbox(kr, ax, a + (n.x if ax == 'x' else n.y) * 0.004, a + (n.x if ax == 'x' else n.y) * 0.007, u - 0.01, u + 0.01,
             p.z + 0.105, d['top'], Z_STRAP)


# ================================================================ doors
def door(name, d):
    ax, a0, a1 = d['wall']
    u0, u1 = d['u']
    z0, z1 = d['z']
    t = a1 - a0
    pa = d.get('piv_y', d.get('piv_x'))
    hu = d['hinge']
    room, outr = d['room'], d['out']
    kroom = MS.rkb(room) if room != 'Exterior' else MS.ext()
    kout = MS.rkb(outr) if outr != 'Exterior' else MS.ext()
    exterior = outr == 'Exterior'
    thick = t > 0.2
    # the leaf turns about its mid-thickness (the Update 3 pivot): the hinge jamb is rebated -- full on the stop side,
    # set back on the swing side so the leaf's hinge edge clears it all the way open; stop strips on the stop side
    # round the leaf (hinge jamb, lock jamb, head) close the gaps it needs, so no light shows through a shut door
    th = leaf_thickness(d)
    hinge_lo = abs(hu - u0) < abs(hu - u1)                           # the hinge on the u0 side
    sw = swing_sign(name, d)                                         # +1: the open leaf lies on the a1 side
    over = math.radians(max(0.0, float(d['swing']) - 90.0))

    def hinge_jamb(k, fa_lo, fa_hi, ua, ub, za, zb):
        fa_sw = fa_hi if sw > 0 else fa_lo
        reb = th / 2 + 0.002 + abs(fa_sw - pa) * math.sin(over)
        if hinge_lo:                                                 # (the stop side 2 mm short of the leaf's edge)
            box_stop, box_swing = (ua, min(ub, hu - 0.002)), (ua, max(ua + 0.001, min(ub, hu - reb)))
        else:
            box_stop, box_swing = (max(ua, hu + 0.002), ub), (min(ub - 0.001, max(ua, hu + reb)), ub)
        a_stop, a_swing = ((fa_lo, pa), (pa, fa_hi)) if sw > 0 else ((pa, fa_hi), (fa_lo, pa))
        wbox(k, ax, a_stop[0], a_stop[1], box_stop[0], box_stop[1], za, zb, Z_DOORFRAME)
        wbox(k, ax, a_swing[0], a_swing[1], box_swing[0], box_swing[1], za, zb, Z_DOORFRAME)

    # ---- the frame
    if not thick and not exterior:
        # steel frame (Zarge) wrapping the 0.15 wall: liners in the opening, architraves on both faces
        lip, fwid = 0.012, 0.045
        for (ua, ub) in ((u0, u0 + 0.015), (u1 - 0.015, u1)):        # the jambs up to the head (no overlaps)
            if (ua == u0) == hinge_lo:
                hinge_jamb(kroom, a0 - lip, a1 + lip, ua, ub, z0, z1 - 0.015)
            else:
                wbox(kroom, ax, a0 - lip, a1 + lip, ua, ub, z0, z1 - 0.015, Z_DOORFRAME)
        wbox(kroom, ax, a0 - lip, a1 + lip, u0, u1, z1 - 0.015, z1, Z_DOORFRAME)
        for aa, sg in ((a0, -1), (a1, 1)):
            k_ = kroom if (sg > 0) == (room_side_sign(d) > 0) else kout
            for (ua, ub) in ((u0 - fwid, u0), (u1, u1 + fwid)):
                wbox(k_, ax, aa, aa + sg * lip, ua, ub, z0, z1 + fwid, Z_DOORFRAME)
            wbox(k_, ax, aa, aa + sg * lip, u0, u1, z1, z1 + fwid, Z_DOORFRAME)
        clear = (u0 + 0.015, u1 - 0.015)
        head = 0.015
        stop_a = (pa - sw * (th / 2 + 0.013), pa - sw * (th / 2 + 0.001))
        hinge_stop = True
    else:
        # angle frame at the leaf plane, reveals on both sides (concrete outside, plaster inside)
        fa0, fa1 = pa - 0.035, pa + 0.035
        for (ua, ub) in ((u0, u0 + 0.04), (u1 - 0.04, u1)):
            if (ua == u0) == hinge_lo:
                hinge_jamb(kroom, fa0, fa1, ua, ub, z0, z1 - 0.04)
            else:
                wbox(kroom, ax, fa0, fa1, ua, ub, z0, z1 - 0.04, Z_DOORFRAME)
        wbox(kroom, ax, fa0, fa1, u0, u1, z1 - 0.04, z1, Z_DOORFRAME)
        rs = room_side_sign(d)
        a_in = (a1 if rs > 0 else a0) - rs * MS.niche_depth(name)   # the room face (the back of its niche, if any)
        ns = 1 if rs > 0 else -1                                    # normal of the room face: into the room
        inner_depth = abs(a_in - (pa + rs * 0.035))
        R = S.ROOMS.get(room)
        zone = MS.Z_CONCIN if (R is None or R['walls'].get('bare')) else MS.Z_PLASTER
        MS.reveal(kroom, ax, a_in, -ns * -1 if False else ns, (u0, u1), (z0, z1), inner_depth, zone, bottom=False)
        clear = (u0 + 0.04, u1 - 0.04)
        head = 0.04
        stop_a = (pa - sw * 0.035, pa - sw * (th / 2 + 0.001))
        hinge_stop = True
    # the stop strips (on the leaf's stop side, 2 cm over its edges)
    za_l, zb_l = z0 + 0.01, z1 - head - 0.003                        # the leaf (see leaf())
    far = clear[1] if hinge_lo else clear[0]
    jh = clear[0] if hinge_lo else clear[1]                          # the hinge jamb's face
    sgn = 1 if hinge_lo else -1                                      # + u: from the hinge toward the lock side
    jw = 0.015 if head < 0.03 else 0.04                              # the jamb's width (Zarge liner / angle frame)
    jh_ = min(u0 + jw, hu - 0.002) if hinge_lo else max(u1 - jw, hu + 0.002)   # the hinge jamb's stop-side face
    if hinge_stop:
        wbox(kroom, ax, stop_a[0], stop_a[1], jh_, hu + sgn * 0.02, za_l, zb_l - 0.02, Z_DOORFRAME)
    wbox(kroom, ax, stop_a[0], stop_a[1], far - sgn * 0.023, far, za_l, zb_l - 0.02, Z_DOORFRAME)
    wbox(kroom, ax, stop_a[0], stop_a[1], jh_, far, zb_l - 0.02, z1 - head, Z_DOORFRAME)
    # the threshold across the opening's floor (top flush with the floors): exterior doors from the leaf outwards in the
    # envelope's object, the rest (to the room face or its niche) in the room's
    rs_ = room_side_sign(d)
    a_room = (a1 if rs_ > 0 else a0) - rs_ * MS.niche_depth(name)
    a_o = a0 if rs_ > 0 else a1
    if exterior:
        wbox(MS.ext(), ax, pa, a_o, u0, u1, z0 - 0.02, z0, Z_THRESH, skip=('-z',))
        wbox(kroom, ax, pa, a_room, u0, u1, z0 - 0.02, z0, Z_THRESH, skip=('-z',))
    else:
        wbox(kroom, ax, a_o, a_room, u0, u1, z0 - 0.02, z0, Z_THRESH, skip=('-z',))
    # hinges on the frame, on the pivot line
    for zz in (z0 + 0.25, (z0 + z1) / 2 + 0.2, z1 - 0.25):
        c = P3(ax, pa, hu, zz)
        kroom.cyl(c - Vector((0, 0, 0.06)), c + Vector((0, 0, 0.06)), 0.012, Z_HINGE, 8)
    # ---- the leaf (IX part)
    leaf(name, d, ax, pa, hu, clear, z0, z1, head)


def leaf_thickness(d):
    return 0.045 if d['kind'] != 'glass' else 0.05


def swing_sign(name, d):
    """+1 if the leaf, opened (the Update 3 axis, + angle), lies on the wall's a1 side"""
    ax = d['wall'][0]
    u0, u1 = d['u']
    hu = d['hinge']
    far = u1 if abs(hu - u0) < abs(hu - u1) else u0
    axb = Vector(unity_axis_to_blender(S.DOOR_AXES_U3[name], 'hinge')).normalized()
    e = Vector((0, 1, 0)) if ax == 'x' else Vector((1, 0, 0))
    r = Matrix.Rotation(math.radians(min(90.0, float(d['swing']))), 3, axb) @ (e * (1 if far > hu else -1))
    return 1 if (r.x if ax == 'x' else r.y) > 0 else -1


def room_side_sign(d):
    """+1 if the door's room lies on the wall's a1 side"""
    ax, a0, a1 = d['wall']
    R = S.ROOMS.get(d['room'])
    if R is None:
        return 1
    c = (R['y0'] + R['y1']) / 2 if ax == 'y' else (R['x0'] + R['x1']) / 2
    return 1 if c > (a0 + a1) / 2 else -1


def leaf(name, d, ax, pa, hu, clear, z0, z1, head):
    kind = d['kind']
    k = kb(name, 'MainParts')
    far = clear[1] if abs(hu - clear[0]) < abs(hu - clear[1]) else clear[0]
    far += -0.003 if far > hu else 0.003                             # 3 mm short of the lock-side jamb
    ua, ub = sorted((hu, far))
    if abs(ua - hu) < 1e-6:
        ua = hu + 0.0
    th = leaf_thickness(d)
    la0, la1 = pa - th / 2, pa + th / 2
    za, zb = z0 + 0.01, z1 - head - 0.003                            # 3 mm under the head of the frame
    zone = {'room': Z_LEAF_W, 'steel': Z_LEAF_S, 'fire': Z_LEAF_F, 'steel_vision': Z_LEAF_S, 'steel_panic': Z_LEAF_S,
            'glass': Z_ALUFRAME}[kind]
    rs = room_side_sign(d)
    if kind == 'glass':
        # aluminium frame round a glass panel, a push plate
        fw = 0.07
        for (u_a, u_b, z_a, z_b) in ((ua, ua + fw, za, zb), (ub - fw, ub, za, zb), (ua + fw, ub - fw, za, za + 0.20),
                                     (ua + fw, ub - fw, zb - fw, zb), (ua + fw, ub - fw, 1.0 + za, 1.06 + za)):
            wbox(k, ax, la0, la1, u_a, u_b, z_a, z_b, Z_ALUFRAME)
        kg = kb(name + '_Glass', 'glass')
        for (z_a, z_b) in ((za + 0.20, za + 1.0), (za + 1.06, zb - fw)):
            q = [P3(ax, pa, ua + fw, z_a), P3(ax, pa, ub - fw, z_a), P3(ax, pa, ub - fw, z_b), P3(ax, pa, ua + fw, z_b)]
            face(kg, q, 0, Vector((1, 0, 0)) if ax == 'x' else Vector((0, 1, 0)))     # the build adds its back face
        part(name + '_Glass', 'static', P3(ax, pa, hu, z0 + 0.01), parent=name, note='the glass door\'s panes')
    else:
        wbox(k, ax, la0, la1, ua, ub, za, zb, zone)
        if kind in ('steel', 'fire', 'steel_vision', 'steel_panic'):
            for sg in (-1, 1):                                       # kick plates
                aa = (la1 if sg > 0 else la0)
                wbox(k, ax, aa, aa + sg * 0.002, ua + 0.03, ub - 0.03, za + 0.01, za + 0.30, Z_KICK)
        if kind == 'steel_vision':                                   # a narrow vision panel
            kg = kb(name + '_Glass', 'glass')
            vu = (ua + 0.25, ub - 0.55) if hu < far else (ua + 0.55, ub - 0.25)
            vu = (min(vu), max(vu))
            for side in (1, -1):
                aa = pa + side * (th / 2 + 0.001)
                q = [P3(ax, aa, vu[0], za + 1.05), P3(ax, aa, vu[1], za + 1.05), P3(ax, aa, vu[1], za + 1.95),
                     P3(ax, aa, vu[0], za + 1.95)]
                face(kg, q, 0, Vector((side, 0, 0)) if ax == 'x' else Vector((0, side, 0)))
                wbox(k, ax, aa, aa + side * 0.006, vu[0] - 0.02, vu[1] + 0.02, za + 1.03, za + 1.05, Z_RUBBER)
                wbox(k, ax, aa, aa + side * 0.006, vu[0] - 0.02, vu[1] + 0.02, za + 1.95, za + 1.97, Z_RUBBER)
                wbox(k, ax, aa, aa + side * 0.006, vu[0] - 0.02, vu[0], za + 1.05, za + 1.95, Z_RUBBER)
                wbox(k, ax, aa, aa + side * 0.006, vu[1], vu[1] + 0.02, za + 1.05, za + 1.95, Z_RUBBER)
            part(name + '_Glass', 'static', P3(ax, pa, hu, z0 + 0.01), parent=name, note='the entrance door\'s vision panel')
    # handle side (the edge away from the hinge): lever handles both sides, roses, a lock cylinder
    hu_h = far - (0.07 if far > hu else -0.07)
    hz = z0 + 1.05
    for sg in (-1, 1):
        aa = pa + sg * th / 2
        if kind == 'steel_panic' and sg == rs:
            # the panic bar across the leaf on the room side
            pb0, pb1 = sorted((ua + 0.10, ub - 0.06))
            wbox(k, ax, aa, aa + sg * 0.07, pb0, pb0 + 0.04, hz - 0.06, hz + 0.06, Z_CLOSER)
            wbox(k, ax, aa, aa + sg * 0.07, pb1 - 0.04, pb1, hz - 0.06, hz + 0.06, Z_CLOSER)
            wbox(k, ax, aa + sg * 0.045, aa + sg * 0.075, pb0, pb1, hz - 0.025, hz + 0.025, Z_PANIC)
            continue
        if kind == 'glass':
            wbox(k, ax, aa, aa + sg * 0.008, min(hu_h, hu_h - 0.0) - 0.05, hu_h + 0.05, hz - 0.15, hz + 0.15, Z_HANDLE)
            continue
        wbox(k, ax, aa, aa + sg * 0.008, hu_h - 0.025, hu_h + 0.025, hz - 0.12, hz + 0.08, Z_HANDLE)      # escutcheon plate
        c = P3(ax, aa + sg * 0.05, hu_h, hz)
        lever_dir = -1 if far > hu else 1                           # the lever points back toward the hinge
        e = P3(ax, aa + sg * 0.05, hu_h + lever_dir * 0.12, hz)
        k.cyl(P3(ax, aa, hu_h, hz), c, 0.009, Z_HANDLE, 8)
        k.cyl(c, e, 0.010, Z_HANDLE, 8)
        k.cyl(P3(ax, aa, hu_h, hz - 0.075), P3(ax, aa + sg * 0.006, hu_h, hz - 0.075), 0.012, Z_LOCK, 10)
    # closers on fire / exterior doors (the body on the leaf's top, room side)
    if kind in ('fire', 'steel_vision', 'steel_panic') or (kind == 'steel' and d['out'] == 'Exterior'):
        sg = rs
        aa = pa + sg * th / 2
        cu = hu + (0.30 if far > hu else -0.30)
        wbox(k, ax, aa, aa + sg * 0.05, cu - 0.14, cu + 0.14, zb - 0.10, zb - 0.03, Z_CLOSER)
    # the part
    piv = P3(ax, pa, hu, z0 + 0.01)
    U3AX = S.DOOR_AXES_U3[name]
    part(name, 'hinge', piv, axis=unity_axis_to_blender(U3AX, 'hinge'), rng=(0.0, float(d['swing'])), parent='BaseMain',
         states=['closed', 'open'], note=f'{kind} door, {room_label(d)}')


def room_label(d):
    return f"{d['room']} <-> {d['out']}"


def gate():
    """IX_GarageGate_18: the up-and-over leaf (ribbed steel) inside the wall, hinged across the top; side frames,
    the ceiling tracks it runs back on, a handle"""
    g = S.GARAGE_GATE
    k = kb(g['name'], 'MainParts')
    u0, u1 = g['u']
    z0, z1 = g['z']
    piv = Vector(g['piv'])
    ya, yb = -4.72, -4.66
    xa, xb = u0 + 0.02, u1 - 0.02
    box6(k, (xa, ya, z0 + 0.03), (xb, yb, z1), Z_GATE)
    for i in range(1, 12):                                          # ribs on the outer face
        zz = z0 + 0.03 + i * (z1 - z0 - 0.03) / 12
        box6(k, (xa + 0.04, ya - 0.012, zz - 0.012), (xb - 0.04, ya, zz + 0.012), Z_GATE, skip=('+y',))
    box6(k, (xa, ya - 0.015, z0 + 0.03), (xb, ya, z0 + 0.08), Z_RUBBER, skip=('+y',))
    c = Vector(((xa + xb) / 2, ya - 0.04, z0 + 0.95))
    box6(k, c - Vector((0.10, 0.03, 0.02)), c + Vector((0.10, 0.0, 0.02)), Z_HANDLE)
    k.cyl(Vector((c.x, ya, z0 + 0.95)), Vector((c.x, ya - 0.012, z0 + 0.95)), 0.018, Z_LOCK, 10)
    part(g['name'], 'hinge', piv, axis=unity_axis_to_blender((1.0, 0.0, 0.0), 'hinge'), rng=(0.0, float(g['swing'])),
         parent='BaseMain', states=['closed', 'open'],
         note='up-and-over garage gate: swings up and in about the top edge to lie under the ceiling')
    # static: side frames in the opening and the tracks under the ceiling
    kr = MS.rkb('Garage')
    for x0_, x1_ in ((u0 - 0.06, u0), (u1, u1 + 0.06)):
        box6(kr, (x0_, -4.75, S.G_F), (x1_, -4.65, z1 + 0.05), Z_TRACK)
        box6(kr, (x0_, -4.65, z1 - 0.02), (x1_, -1.40, z1 + 0.05), Z_TRACK)
        box6(kr, (x0_, -1.50, z1 + 0.05), (x1_, -1.40, S.G_C), Z_TRACK)
    box6(kr, (u0 - 0.06, -4.75, z1 + 0.05), (u1 + 0.06, -4.65, z1 + 0.15), Z_TRACK)


def build_openings():
    for w in S.WINDOWS:
        window(w)
    winders()
    for name, d in S.DOORS.items():
        door(name, d)
    gate()
