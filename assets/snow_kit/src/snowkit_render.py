"""The kit at work (Cycles): lit lamps and screens, the cabinet open with the van's battery on its shelf (a stand-in box),
clamps on, the switch at BATTERIE; the line at dusk (poles, the drop to a roof stand, the wires by the K9 rule); the steel
masts with their attachments by day and at night (the camera with a floodlight, the street lamp, the radio antennas, the
siren with a horn).
python3 -I snowkit_render.py -- <out_dir> [spp] [views|all]  (reads out/snow_kit.blend, out/snow_kit_contract.json)"""
import bpy, sys, os, json, math
sys.path.insert(0, '/home/claude/uaz')
from mathutils import Vector, Matrix
import psxlib as P
import snowkit_spec as S
import snowkit_kit as SKK

a = sys.argv[sys.argv.index('--') + 1:]
OUT = a[0]
SPP = int(a[1]) if len(a) > 1 else 48
ONLY = set(a[2].split(',')) if len(a) > 2 and a[2] != 'all' else None
os.makedirs(OUT, exist_ok=True)
HERE = '/home/claude/uaz'
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'snow_kit.blend'))
KC = json.load(open(os.path.join(HERE, 'out', 'snow_kit_contract.json')))
sc = bpy.context.scene
# the showroom row out of the render: its collection excluded from the view layer (instances of its item collections still
# render; hiding the objects instead would hide them in the instances too)
sc.view_layers[0].layer_collection.children['Snow_Kit'].exclude = True
for m in bpy.data.materials:
    if m.node_tree:
        for n_ in m.node_tree.nodes:
            if n_.type == 'TEX_IMAGE':
                n_.interpolation = 'Closest'
stage = bpy.data.collections.new('Stage')
sc.collection.children.link(stage)


def show(item, M, name=None):
    e = bpy.data.objects.new(name or ('I_' + item), None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = bpy.data.collections[item]
    e.matrix_world = M
    stage.objects.link(e)
    for o in bpy.data.collections[item].objects:
        o.hide_render = o.name.startswith('COL_')
    return e


def M_(pos, yaw=0.0, tilt=0.0, sx=1.0):
    R = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(tilt), 3, 'X')
    return Matrix.Translation(Vector(pos)) @ R.to_4x4() @ Matrix.Diagonal((sx, 1, 1, 1))


def slotM(parentM, item, sock):
    s = KC['sockets'][sock]
    z, y = Vector(s['dir']).normalized(), Vector(s['up']).normalized()
    x = y.cross(z).normalized()
    return parentM @ Matrix.Translation(Vector(s['pos'])) @ Matrix((x, y, z)).transposed().to_4x4()


def sockp(M, sock):
    return M @ Vector(KC['sockets'][sock]['pos'])


def pose(part, v):
    """turn / slide a kit part in place (all its instances follow)"""
    p = KC['parts'][part]
    o = bpy.data.objects[part]
    root = bpy.data.objects[p['item']]
    if 'rest_mw' not in o:
        o['rest_mw'] = [list(r) for r in o.matrix_world]
    mw0 = Matrix([list(r) for r in o['rest_mw']])
    piv = root.matrix_world @ Vector(p['pivot'])
    ax = (root.matrix_world.to_3x3() @ Vector(p['axis'])).normalized()
    if p['kind'] in ('hinge', 'twist', 'spin'):
        T = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(v), 4, ax) @ Matrix.Translation(-piv)
    else:
        T = Matrix.Translation(ax * v)
    o.matrix_world = T @ mw0


def mat(name, rgb, rough=0.6, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n_ for n_ in m.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    if emit:
        pb.inputs['Emission Color'].default_value = (*rgb, 1)
        pb.inputs['Emission Strength'].default_value = emit
    return m


def box(name, lo, hi, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    o.data.materials.append(m)
    for c in o.users_collection:
        c.objects.unlink(o)
    stage.objects.link(o)
    return o


def lights(on):
    for m in bpy.data.materials:
        if m.node_tree is None or m.get('night_emit') is None:
            continue
        pb = next((n_ for n_ in m.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED'), None)
        if pb is not None:
            pb.inputs['Emission Strength'].default_value = float(m['night_emit']) if (on and not m.name.endswith('_Off')) else 0.0


def screens(on):
    sc_on, sc_off = bpy.data.materials['M_Kit_Screen_On'], bpy.data.materials['M_Kit_Screen_Off']
    bpy.data.objects['Kit_Monitor_Screen'].data.materials[0] = sc_on if on else sc_off


P.setup_cycles((1280, 800), SPP)
sc.cycles.max_bounces = 4
cam = bpy.data.objects.new('cam_k', bpy.data.cameras.new('cam_k'))
sc.collection.objects.link(cam)
sc.camera = cam
m_wall = mat('St_Wall', (0.30, 0.34, 0.27), 0.85)
m_desk = mat('St_Desk', (0.45, 0.33, 0.20), 0.6)
m_floor = mat('St_Floor', (0.18, 0.18, 0.17), 0.9)
m_batt = mat('St_Batt', (0.03, 0.03, 0.035), 0.4)
m_battl = mat('St_BattLid', (0.10, 0.10, 0.11), 0.5)
m_lead = mat('St_Lead', (0.42, 0.42, 0.40), 0.4, 0.5)
m_ground = mat('St_Ground', (0.10, 0.11, 0.07), 0.95)
m_wire = mat('St_Wire', (0.012, 0.012, 0.012), 0.6)
m_bare = mat('St_Bare', (0.32, 0.33, 0.34), 0.45, 0.6)

# ---------------------------------------------------------------- set 1: the console desk, lit (x around 0)
box('Desk', (-1.2, -0.45, 0.0), (1.2, 0.45, 0.90), m_desk)
box('DeskWall', (-1.6, 0.45, 0.0), (1.6, 0.55, 2.4), m_wall)
box('Floor', (-60, -60, -0.02), (80, 80, 0.0), m_floor)
D = 0.90
Mm1 = M_((-0.62, 0.18, D), yaw=14)                       # fronts to -y, turned a little toward the camera (+x)
Mm2 = M_((-0.20, 0.20, D), yaw=10)
show('Kit_Monitor_CRT', Mm1, 'I_Mon1')
show('Kit_Monitor_CRT', Mm2, 'I_Mon2')
Mc = M_((0.30, -0.05, D), yaw=8)
show('Kit_Console_2', Mc)
for i, lab in enumerate(('Kit_Console_Label_Schranke', 'Kit_Console_Label_Tor')):
    show('Kit_Console_Button', slotM(Mc, 'Kit_Console_2', f'Slot_Button_{i + 1}'), f'I_Btn{i}')
    show(lab, slotM(Mc, 'Kit_Console_2', f'Slot_Label_{i + 1}'), f'I_Lab{i}')
show('Kit_Phone', M_((0.78, 0.05, D), yaw=4))
show('Kit_Beacon', M_((1.02, 0.30, D)))
show('Kit_Camera_BracketWall', M_((1.0, 0.45, 1.55)))                # on the wall face (y 0.45), out to -y
mh = sockp(M_((1.0, 0.45, 1.55)), 'Mount_Head')
show('Kit_Camera_Head', M_(mh, yaw=0, tilt=25))

# ---------------------------------------------------------------- set 2: the cabinet on a wall, the battery in it (x around 6)
box('CabWall', (4.0, 0.0, 0.0), (8.5, 0.12, 3.2), m_wall)
Mk = M_((6.0, 0.0, 1.05))
show('Kit_Cabinet_Power', Mk)
bp = sockp(Mk, 'Slot_Battery')
bs = KC['meta']['battery']
L_, W_, H_ = bs['size'][2], bs['size'][0], 0.19                        # along x, along y, the box (posts on top)
box('Battery', (bp.x - L_ / 2, bp.y - W_ / 2, bp.z), (bp.x + L_ / 2, bp.y + W_ / 2, bp.z + H_), m_batt)
box('BatteryLid', (bp.x - L_ / 2 + 0.005, bp.y - W_ / 2 + 0.005, bp.z + H_), (bp.x + L_ / 2 - 0.005, bp.y + W_ / 2 - 0.005, bp.z + H_ + 0.008), m_battl)
for sgn, sock in ((-1, 'Battery_Post_Pos'), (1, 'Battery_Post_Neg')):
    pp = sockp(Mk, sock)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.009, depth=0.03, location=(pp.x, pp.y, pp.z - 0.012))
    o = bpy.context.active_object
    o.data.materials.append(m_lead)
    for c in o.users_collection:
        c.objects.unlink(o)
    stage.objects.link(o)
show('Kit_Conduit_Entry', M_(sockp(Mk, 'Conduit_Top'), tilt=0) @ Matrix.Rotation(math.radians(-90), 4, 'Y'))
ct = sockp(Mk, 'Conduit_Top')
show('Kit_Conduit_Straight', Matrix.Translation(ct + Vector((0, 0, 0.04))) @ Matrix.Rotation(math.radians(-90), 4, 'Y') @
     Matrix.Diagonal((0.55, 1, 1, 1)))
show('Kit_RoofStand', M_((6.0, 0.0, ct.z + 0.59), yaw=0))
show('Kit_JunctionBox', M_((7.3, 0.0, 1.1)))
show('Kit_DoorLock_Strike', M_((4.6, 0.0, 1.2)))
show('Kit_DoorLock', M_((4.75, 0.0, 1.2)))

# ---------------------------------------------------------------- set 3: the line at dusk (x around 16)
box('Ground3', (10, -30, -0.02), (40, 30, 0.002), m_ground)
Mp1 = M_((15.0, 6.0, 0.0))
Mp2 = M_((15.5, 34.0, 0.0))
show('Kit_Pole_Trafo', Mp1)
show('Kit_Pole', Mp2)
box('Hut', (13.0, -3.6, 0.0), (17.0, -0.12, 2.9), m_wall)
Mrs = M_((15.2, -0.12, 1.2), yaw=180)
show('Kit_RoofStand', Mrs, 'I_RS3')
from van2_kit import KB
wk, wk2 = KB(), KB()
p1 = sorted([f'Wire_{i}_T' for i in (4, 5, 6, 7)], key=lambda w: sockp(Mp1, w).x)
rs = sorted([f'Wire_{i}_R' for i in (1, 2, 3, 4)], key=lambda w: sockp(Mrs, w).x)
for a_, b_ in zip(p1, rs):
    pts, _ = SKK.wire_points(sockp(Mp1, a_), sockp(Mrs, b_))
    wk.tube(pts, S.WIRE['r_lv'], 0, S.WIRE['sides'], caps=False)
for i in (1, 2, 3):
    pts, _ = SKK.wire_points(sockp(Mp1, f'Wire_{i}_T'), sockp(Mp2, f'Wire_{i}'))
    wk2.tube(pts, S.WIRE['r_bare'], 0, S.WIRE['sides'], caps=False)
    a2 = sockp(Mp2, f'Wire_{i}')
    pts, _ = SKK.wire_points(a2, a2 + Vector((0.6, 30.0, -0.2)))
    wk2.tube(pts, S.WIRE['r_bare'], 0, S.WIRE['sides'], caps=False)
for k_, nm_, m_ in ((wk, 'Wires_Drop', m_wire), (wk2, 'Wires_Line', m_bare)):
    o = k_.to_object(nm_, coll=stage)
    o.data.materials.append(m_)

# ---------------------------------------------------------------- set 4: the steel masts and their attachments (x around 34):
# surveillance (camera + floodlight, the cable in conduit into a shed), light (street lamp), radio (antenna + Yagi), alarm
# (siren + horn); the lamps' real lights for the night shot
box('Shed4', (27.0, -16.0, 0.0), (29.0, -12.0, 2.6), m_wall)
MAST_LIGHTS = []


def on_mast(Mm, sock, item, target, name):
    p = sockp(Mm, sock)
    d = Vector(target) - p
    M = M_(p, yaw=math.degrees(math.atan2(d.x, -d.y)))
    show(item, M, name)
    return M


def mast_light(M, sock, typ):
    s_ = KC['sockets'][sock]
    MAST_LIGHTS.append((M @ Vector(s_['pos']), (M.to_3x3() @ Vector(s_['dir'])).normalized(), typ))


M1 = M_((31.0, -14.0, 0.0), yaw=90)                                    # the footing's back (+y) to -x: the conduit to the shed
show('Kit_Mast', M1, 'I_Mast1')
T1 = Vector((36.5, -20.0, 0.0))
Mbr = on_mast(M1, 'Mount_Side_1', 'Kit_Camera_BracketPole', T1, 'I_CamBr4')
mh_ = sockp(Mbr, 'Mount_Head_Pole')
dd = T1 - (mh_ + Vector((0, 0, 0.08)))
show('Kit_Camera_Head', M_(mh_, yaw=math.degrees(math.atan2(dd.x, -dd.y)), tilt=math.degrees(math.atan2(-dd.z, math.hypot(dd.x, dd.y)))),
     'I_Cam4')
Mf1 = on_mast(M1, 'Mount_Side_2', 'Kit_Mast_Flood', (35.0, -21.0, 0.0), 'I_Flood4')
mast_light(Mf1, 'LIGHT_Flood', 'flood')
cb_ = sockp(M1, 'Conduit_Base')                                       # out of the footing along -x, into the shed's wall
Rx = Matrix.Rotation(math.radians(180), 4, 'Z')
show('Kit_Conduit_Entry', Matrix.Translation(cb_) @ Rx, 'I_CEntry4a')
show('Kit_Conduit_Entry', Matrix.Translation(Vector((29.0, cb_.y, cb_.z))), 'I_CEntry4b')
Lc = cb_.x - 0.04 - 29.04
show('Kit_Conduit_Straight', Matrix.Translation(cb_ - Vector((0.04, 0, 0))) @ Rx @ Matrix.Diagonal((Lc, 1, 1, 1)), 'I_CStr4')
show('Kit_Conduit_Clamp', Matrix.Translation(cb_ - Vector((0.04 + Lc * 0.5, 0, 0))) @ Rx, 'I_CClamp4')
M2 = M_((33.6, -14.0, 0.0))
show('Kit_Mast', M2, 'I_Mast2')
Ml2 = M_(sockp(M2, 'Mount_Top'), yaw=0)                                 # the lamp reaches out to -y, over the way
show('Kit_Mast_Lamp', Ml2, 'I_Lamp4')
mast_light(Ml2, 'LIGHT_Street', 'street')
M3 = M_((36.2, -14.0, 0.0))
show('Kit_Mast', M3, 'I_Mast3')
show('Kit_Mast_Antenna', M_(sockp(M3, 'Mount_Top')), 'I_Ant4')
on_mast(M3, 'Mount_Side_1', 'Kit_Mast_Yagi', (45.0, -9.0, 4.0), 'I_Yagi4')
M4 = M_((38.8, -14.0, 0.0))
show('Kit_Mast', M4, 'I_Mast4')
show('Kit_Mast_Siren', M_(sockp(M4, 'Mount_Top')), 'I_Siren4')
on_mast(M4, 'Mount_Side_1', 'Kit_Mast_Horn', (36.0, -24.0, 1.5), 'I_Horn4')

pose('IX_CabinetDoor', 105)
pose('IX_CabinetSwitch', 90)
SHOTS = {   # eye, target, lens, lamps / screens on, world (colour, strength), sun
    'desk_power_on': ((0.9, -2.3, 1.55), (0.15, 0.1, 1.05), 32, True, ((0.02, 0.022, 0.03), 0.4), None),
    'desk_power_off': ((0.9, -2.3, 1.55), (0.15, 0.1, 1.05), 32, False, ((0.30, 0.31, 0.33), 0.8), None),
    'cabinet_battery': ((6.55, -1.45, 1.35), (6.0, -0.2, 0.95), 30, True, ((0.28, 0.30, 0.33), 0.9), None),
    'cabinet_wall': ((8.0, -5.5, 2.4), (6.0, 0.0, 2.5), 24, True, ((0.32, 0.34, 0.38), 1.0), (3.0, (40, 0, 150))),
    'line_dusk': ((25.5, 0.0, 3.4), (15.2, 3.2, 3.9), 24, True, ((0.16, 0.13, 0.20), 1.2), (1.0, (8, 0, 220))),
    'mast_camera': ((33.0, -20.6, 1.9), (31.0, -14.0, 2.15), 30, True, ((0.32, 0.34, 0.38), 1.0), (3.0, (45, 0, 150))),
    'masts': ((35.2, -25.5, 2.3), (34.9, -14.0, 2.6), 28, False, ((0.32, 0.34, 0.38), 1.0), (3.0, (45, 0, 150))),
    'masts_night': ((35.2, -25.5, 2.3), (34.9, -14.0, 2.6), 28, True, ((0.012, 0.014, 0.024), 0.5), None),
}
for nm, (eye, tgt, lens, on, wld, sun) in SHOTS.items():
    if ONLY and nm not in ONLY:
        continue
    lights(on)
    screens(on)
    for c in ('Pos', 'Neg'):
        pose('IX_CabinetClamp_' + c, 0.0 if nm.startswith('cabinet') else 0.06)
    for o in list(sc.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)
    P.world(*wld)
    if sun:
        P.sun(*sun)
    if nm == 'masts_night':                                       # the mast lamps' real lights (spot along each LIGHT_)
        for i, (lp_, ld_, typ) in enumerate(MAST_LIGHTS):
            ld = bpy.data.lights.new(f'ml{i}', 'SPOT')
            ld.energy = 900.0 if typ == 'flood' else 450.0
            ld.spot_size = math.radians(110 if typ == 'flood' else 150)
            ld.spot_blend = 0.6
            ld.color = (1.0, 0.86, 0.66) if typ == 'flood' else (0.80, 0.90, 1.0)
            ld.shadow_soft_size = 0.05
            lo = bpy.data.objects.new(f'ml{i}', ld)
            sc.collection.objects.link(lo)
            lo.location = lp_
            lo.rotation_euler = ld_.to_track_quat('-Z', 'Y').to_euler()
    if nm.startswith('desk'):
        ld = bpy.data.lights.new('fill', 'AREA')
        ld.energy = 40.0 if on else 120.0
        ld.size = 2.0
        lo = bpy.data.objects.new('fill', ld)
        sc.collection.objects.link(lo)
        lo.location = (0.0, -1.5, 2.6)
        lo.rotation_euler = (math.radians(35), 0, 0)
    cam.location = Vector(eye)
    cam.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', nm, flush=True)
