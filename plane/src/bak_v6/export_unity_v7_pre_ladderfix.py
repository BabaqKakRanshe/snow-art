"""Unity export of Utility Plane v7 (from out/plane_v7_final_<tag>.blend; textures already written by finalize_v7.py).
usage: python3 export_unity_v7.py [tag=v7]
Output: export/unity_v7/Assets/UtilityPlane/{Models,Data,Textures (fog mask)}
 - UtilityPlane.fbx: hierarchy of rigid parts, every moving part = own object with its pivot on its hinge/axle,
   Unity axes (nose +Z, up +Y, right +X), metres. Sockets = empties. Collider proxies = COL_* meshes.
 - SM_Cargo_Case1..6.fbx (pivot at the bottom centre)
 - Data/interaction_volumes.json, cargo_layout.json, displays.json, sockets.json (atlas_texel.json from finalize)
v5: parked tail-down (9.98 deg), sockets computed here (no UE detour), lined cabin, 6 atlases.
v6: instrument panel v6 - display quads Display_* (UV 0..1), radio faces = Display_Radio, map case lid,
    starter guard, VOLT / VAC needles; 44 interaction zones.
v7: cabin door switches, radio / ALT / HDG knobs, Kollsman disc, heading bug, compass card, door locks + keyhole
    sockets, prop blades with pitch axes + PropBlur / PropDisc, glass fog layers (Glass_Fog, *_Fog, M_GlassFog),
    SM_StepLadder (+ colliders, climb zone) and SM_PlaneKey, ladder sockets at the fuel fillers."""
import bpy, bmesh, os, sys, json, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

TAG = sys.argv[1] if len(sys.argv) > 1 else 'v7'
OUT = os.path.join(HERE, 'export', 'unity_v7', 'Assets', 'UtilityPlane')
MOD, DATA, TEXD = (os.path.join(OUT, d) for d in ('Models', 'Data', 'Textures'))
for d in (MOD, DATA, TEXD):
    os.makedirs(d, exist_ok=True)


def to_unity(p):
    """build frame (x left, y aft, z up, m) -> Unity (x right, y up, z forward, m)"""
    return [round(-p[0], 5) + 0.0, round(p[2], 5) + 0.0, round(-p[1], 5) + 0.0]      # + 0.0: no '-0.0' in JSON


def vec_unity(v):
    return [round(-v[0], 5) + 0.0, round(v[2], 5) + 0.0, round(-v[1], 5) + 0.0]


def ext_unity(h):
    return [round(abs(h[0]), 5), round(abs(h[2]), 5), round(abs(h[1]), 5)]


bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_final_{TAG}.blend'))
O = bpy.data.objects
SC = bpy.context.scene
CPR = json.load(open(os.path.join(HERE, 'out', 'cockpit_rig_v7.json')))
EXT7 = json.load(open(os.path.join(HERE, 'out', 'ext_v7.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'light_pos.json')))
ROOT = O['UtilityPlane']
bpy.context.view_layer.update()
PIVOT = {o.name: o.matrix_world.translation.copy() for o in O if o.type in ('MESH', 'EMPTY')}


def empty(name, loc, parent, size=0.05):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    SC.collection.objects.link(e)
    e.matrix_world = Matrix.Translation(Vector(loc))
    set_parent(e, parent)
    return e


def set_parent(ob, parent):
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    ob.matrix_world = mw


def split_faces(ob, pred, newname, origin=None):
    new = ob.copy()
    new.data = ob.data.copy()
    new.name = newname
    new.data.name = newname
    for c in ob.users_collection:
        c.objects.link(new)
    for target, keep in ((new, True), (ob, False)):
        bm = bmesh.new()
        bm.from_mesh(target.data)
        kill = [f for f in bm.faces if bool(pred(f, bm)) != keep]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(target.data)
        bm.free()
    if origin is not None:
        set_origin(new, origin)
    return new


def set_origin(ob, p):
    p = Vector(p)
    mw = ob.matrix_world.copy()
    local = mw.inverted() @ p
    ob.data.transform(Matrix.Translation(-local))
    ob.matrix_world = mw @ Matrix.Translation(local)


def mat_index(ob, name):
    names = [m.name if m else '' for m in ob.data.materials]
    return names.index(name) if name in names else -1


def join(names, newname, parent):
    bpy.ops.object.select_all(action='DESELECT')
    obs = [O[n] for n in names if n in O]
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = newname
    set_parent(ob, parent)
    return ob


def verts_w(name):
    ob = O[name]
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def top_centroid(name, band=0.02):
    pts = verts_w(name)
    zmax = max(p.z for p in pts)
    sel = [p for p in pts if p.z > zmax - band]
    return tuple(sum((p for p in sel), Vector()) / len(sel))


# ================================================================== sockets (build frame)
W_LE, W_CH, W_Z0, DIH = -2.55, 2.10, 2.648, math.radians(2.0)
wz = lambda x: W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)
gz = LY.ground_z
SOCK = {   # parent 'Sockets' (static)
    'Socket_PilotEye': LY.PILOT_EYE, 'Socket_CopilotEye': LY.COPILOT_EYE,
    'Socket_WheelContact_L': LY.MAIN_WHEEL_C, 'Socket_WheelContact_R': (-LY.MAIN_WHEEL_C[0], *LY.MAIN_WHEEL_C[1:]),
    'Socket_WheelContact_Tail': LY.TAIL_WHEEL_C,
    'Socket_Exhaust_L': (0.78, -3.80, 1.56), 'Socket_Exhaust_R': (-0.78, -3.80, 1.56),
    'Socket_PropWash': (0.0, -4.74, gz(-4.74)), 'Socket_CenterOfMass': (0.0, -1.95, 1.75),
    'Socket_Audio_Engine': (0.0, -4.0, 1.55), 'Socket_Audio_Cabin': (0.0, -2.2, 1.9),
    'Socket_Audio_Gear_L': (0.46, -2.85, 1.03), 'Socket_Audio_Gear_R': (-0.46, -2.85, 1.03),
    'Socket_Audio_Tail': (0.0, 4.35, 1.62), 'Socket_Cam_Chase': (0.0, 14.0, 4.5),
    'Socket_Seat_P': (0.33, -2.20, 1.43), 'Socket_Seat_C': (-0.33, -2.20, 1.43),
    'Socket_Aero_Fin': (0.0, 4.25, 3.0), 'Socket_Aero_Fuselage': (0.0, -1.0, 1.75), 'Socket_Thrust': LY.PROP_C,
}
LADDER_Y = W_LE - 0.65                      # v7 (M5): ladder platform centre 0.65 m ahead of the leading edge
for sg, s_ in ((1, 'L'), (-1, 'R')):
    SOCK[f'Socket_Ladder_Fuel_{s_}'] = (sg * 1.55, LADDER_Y, gz(LADDER_Y))
for k, v in LIGHTS.items():
    SOCK['Socket_' + k] = tuple(v)
for sg, s_ in ((1, 'L'), (-1, 'R')):
    SOCK[f'Socket_Exit_{s_}'] = (sg * 1.20, -2.05, gz(-2.05))
    SOCK[f'Socket_Exit_Cargo_{s_}'] = (sg * 1.35, -0.20, gz(-0.20))
    cap = verts_w('FuelCap_' + s_)
    SOCK[f'Socket_FuelCap_{s_}'] = (sg * 1.55, W_LE + 0.25 * W_CH, min(p.z for p in cap))
    SOCK[f'Socket_Aero_Wing_{s_}_In'] = (sg * 2.0, W_LE + 0.25 * W_CH, wz(2.0) + 0.06)
    SOCK[f'Socket_Aero_Wing_{s_}_Out'] = (sg * 5.2, W_LE + 0.25 * W_CH, wz(5.2) + 0.06)
    SOCK[f'Socket_Aero_HStab_{s_}'] = (sg * 1.2, 4.24, 2.06)
cl = O['CP_CargoLight']
li = mat_index(cl, 'M_Light_Cabin')
lens_pts = [cl.matrix_world @ cl.data.vertices[v].co for p in cl.data.polygons if p.material_index == li
            for v in p.vertices]
CARGO_LIGHTS = [(0.0, yl, min(q.z for q in lens_pts if abs(q.y - yl) < 0.1) - 0.01) for yl in (-0.55, 0.75)]
SOCK['Socket_Light_Cargo'] = CARGO_LIGHTS[0]
SOCK['Socket_Light_Cargo_2'] = CARGO_LIGHTS[1]
for k, v in CPR['sockets'].items():
    if k.startswith('Socket_TieDown_'):                 # floor point under the D-ring (COL_Floor top), ring 3 cm above
        SOCK[k] = (v[0], v[1], LY.FLOOR_Z + 0.004)
DOME_Z = CPR['sockets']['_dome_z'][2] - 0.01
CHILD = {   # sockets riding on a part: name -> (build pos, parent)
    'Socket_Handle_PilotDoor_L_Out': ((0.775, -2.32, 1.70), 'PilotDoor_L'),
    'Socket_Handle_PilotDoor_L_In': ((0.655, -2.83, 1.713), 'PilotDoor_L'),
    'Socket_Handle_PilotDoor_R_Out': ((-0.775, -2.32, 1.70), 'PilotDoor_R'),
    'Socket_Handle_PilotDoor_R_In': ((-0.655, -2.83, 1.713), 'PilotDoor_R'),
    'Socket_Handle_CargoDoor_L_Out': ((0.775, -0.70, 1.75), 'CargoDoor_L'),
    'Socket_Handle_CargoDoor_L_In': ((0.665, -0.68, 1.718), 'CargoDoor_L'),
    'Socket_Handle_CargoDoor_R_Out': ((-0.775, -0.70, 1.75), 'CargoDoor_R'),
    'Socket_Handle_CargoDoor_R_In': ((-0.665, -0.68, 1.718), 'CargoDoor_R'),
    'Socket_Hand_Yoke_L': ((0.488, -2.759, 1.752), 'Yoke_P_Roll'),
    'Socket_Hand_Yoke_R': ((0.172, -2.759, 1.752), 'Yoke_P_Roll'),
    'Socket_Hand_Throttle': (top_centroid('Lever_Power'), 'Lever_Power'),
    'Socket_Foot_L': (top_centroid('PedalP_L', 0.06), 'PedalP_L'),
    'Socket_Foot_R': (top_centroid('PedalP_R', 0.06), 'PedalP_R'),
    'Socket_Light_Dome_L': ((0.085, -2.29, DOME_Z), 'Cockpit'),
    'Socket_Light_Dome_R': ((-0.085, -2.29, DOME_Z), 'Cockpit'),
    'Socket_Light_Flood': ((0.0, -2.965, 2.015), 'Cockpit'),
    'Socket_Belt_P': ((0.33, -2.30, 1.505), 'Cockpit'),
    'Socket_Belt_C': ((-0.33, -2.30, 1.505), 'Cockpit'),
    'Socket_Keyhole_PilotDoor_L': (tuple(EXT7['locks']['L']), 'PilotDoor_L'),       # v7 (M2): lock face centre
    'Socket_Keyhole_PilotDoor_R': (tuple(EXT7['locks']['R']), 'PilotDoor_R'),
}

# ================================================================== interaction volumes (computed before any object surgery)
INTERACT = {
    'SW_Battery': ('toggle', 'АКБ'), 'SW_Avionics': ('toggle', 'Авионика'), 'SW_FuelPump': ('toggle', 'Топл. насос'),
    'SW_Ignition': ('toggle', 'Зажигание'), 'SW_Starter': ('momentary', 'Стартер'),
    'SW_Beacon': ('toggle', 'Маяк'), 'SW_Strobe': ('toggle', 'Стробы'), 'SW_NavLights': ('toggle', 'АНО'),
    'SW_Landing': ('toggle', 'Посадочная фара'), 'Rheo_Panel': ('rotary', 'Подсветка приборов'),
    'Rheo_Flood': ('rotary', 'Заливающий свет'), 'Pull_CabinHeat': ('pull', 'Обогрев кабины'),
    'Pull_Defrost': ('pull', 'Обдув стекла'), 'Pull_ParkBrake': ('pull', 'Стояночный тормоз'),
    'Pull_FuelShutoff': ('pull', 'Перекрывной топливный кран'), 'FuelSel_L': ('selector', 'Кран левого бака'),
    'FuelSel_R': ('selector', 'Кран правого бака'), 'Visor_P': ('hinge', 'Козырёк'), 'Visor_C': ('hinge', 'Козырёк'),
    'Lever_Power': ('lever', 'РУД (газ)'), 'Lever_Prop': ('lever', 'Шаг винта'),
    'Lever_Condition': ('lever', 'Рычаг останова / малый газ'), 'Lever_Flap': ('lever', 'Закрылки'),
    'TrimWheel': ('wheel', 'Триммер РВ'),
    'SW_CargoDoor_L': ('toggle', 'Грузовая дверь, левая'), 'SW_CargoDoor_R': ('toggle', 'Грузовая дверь, правая'),
    'SW_CabinLight': ('toggle', 'Свет кабины'), 'SW_CargoLight': ('toggle', 'Свет отсека'),
    'Btn_AnnunTest': ('momentary', 'Проверка табло'),
    'Glovebox_Lid': ('hinge', 'Бардачок'),
    # v7
    'SW_CabinDoor_L': ('toggle', 'Дверь кабины, левая'), 'SW_CabinDoor_R': ('toggle', 'Дверь кабины, правая'),
    'Knob_ALT_Baro': ('rotary', 'Давление на высотомере'), 'Knob_HDG_Bug': ('rotary', 'Задатчик курса'),
    'Knob_DG_Set': ('rotary', 'Согласование курсового'),
    'Knob_Audio_Vol': ('rotary', 'Аудио: громкость'), 'Knob_Com_Outer': ('rotary', 'COM: МГц'),
    'Knob_Com_Inner': ('rotary', 'COM: кГц'), 'Knob_Nav_Outer': ('rotary', 'NAV: МГц'),
    'Knob_Nav_Inner': ('rotary', 'NAV: кГц'), 'Knob_NavCom_Vol': ('rotary', 'NAV/COM: питание, громкость'),
    'Knob_GPS_Pwr': ('rotary', 'GPS: питание'), 'Knob_GPS_Outer': ('rotary', 'GPS: внешняя ручка'),
    'Knob_GPS_Inner': ('rotary', 'GPS: внутренняя ручка'), 'Knob_XPDR_Mode': ('selector', 'Режим ответчика'),
    'Knob_AP_Baro': ('rotary', 'Автопилот: BARO'), 'Knob_ADF_Vol': ('rotary', 'ADF: питание, громкость'),
    'Knob_ADF_Outer': ('rotary', 'ADF: частота, грубо'), 'Knob_ADF_Inner': ('rotary', 'ADF: частота, точно'),
}
KNOB_TIGHT = {k for k in INTERACT if k.startswith('Knob_')}     # concentric pairs: no 15 mm padding (no overlap)
SOCK_INTERACT = {   # socket: (parent part, half extents in Unity axes (m), kind, label)
    'Socket_Handle_PilotDoor_L_Out': ('PilotDoor_L', (0.04, 0.04, 0.08), 'door', 'Дверь пилота'),
    'Socket_Handle_PilotDoor_L_In': ('PilotDoor_L', (0.04, 0.04, 0.07), 'door', 'Дверь пилота'),
    'Socket_Handle_PilotDoor_R_Out': ('PilotDoor_R', (0.04, 0.04, 0.08), 'door', 'Правая дверь'),
    'Socket_Handle_PilotDoor_R_In': ('PilotDoor_R', (0.04, 0.04, 0.07), 'door', 'Правая дверь'),
    'Socket_Handle_CargoDoor_L_Out': ('CargoDoor_L', (0.04, 0.05, 0.10), 'door', 'Грузовая дверь, левая'),
    'Socket_Handle_CargoDoor_L_In': ('CargoDoor_L', (0.04, 0.04, 0.08), 'door', 'Грузовая дверь, левая'),
    'Socket_Handle_CargoDoor_R_Out': ('CargoDoor_R', (0.04, 0.05, 0.10), 'door', 'Грузовая дверь, правая'),
    'Socket_Handle_CargoDoor_R_In': ('CargoDoor_R', (0.04, 0.04, 0.08), 'door', 'Грузовая дверь, правая'),
    'Socket_FuelCap_L': ('FuelCap_L', (0.06, 0.04, 0.06), 'cap', 'Крышка левого бака'),
    'Socket_FuelCap_R': ('FuelCap_R', (0.06, 0.04, 0.06), 'cap', 'Крышка правого бака'),
    'Socket_Belt_P': ('Cockpit', (0.12, 0.07, 0.09), 'toggle', 'Ремни пилота'),
    'Socket_Belt_C': ('Cockpit', (0.12, 0.07, 0.09), 'toggle', 'Ремни пассажира'),
    'Socket_Keyhole_PilotDoor_L': ('PilotDoor_L', (0.02, 0.02, 0.02), 'lock', 'Замок'),
    'Socket_Keyhole_PilotDoor_R': ('PilotDoor_R', (0.02, 0.02, 0.02), 'lock', 'Замок'),
}
MIN_HALF = 0.015
vols = []
for name, (kind, label) in INTERACT.items():
    ob = O[name]
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    c, h = (mn + mx) / 2 - PIVOT[name], (mx - mn) / 2
    lo = 0.004 if name in KNOB_TIGHT else MIN_HALF
    vols.append(dict(id=name, parent=name, kind=kind, label=label, center=vec_unity(c),
                     halfExtents=[max(lo, e) for e in ext_unity(h)]))
for sk, (par, he, kind, label) in SOCK_INTERACT.items():
    p = Vector(CHILD[sk][0] if sk in CHILD else SOCK[sk])
    base = Vector((0, 0, 0)) if par in ('Cockpit', 'UtilityPlane') else PIVOT[par]
    vols.append(dict(id=sk, parent=par, kind=kind, label=label, center=vec_unity(p - base), halfExtents=list(he)))
for s_, sx in (('P', 0.33), ('C', -0.33)):
    vols.append(dict(id=f'Seat_{s_}', parent='Cockpit', kind='seat',
                     label='Кресло пилота' if s_ == 'P' else 'Кресло пассажира',
                     center=to_unity((sx, -2.22, 1.55)), halfExtents=[0.22, 0.2, 0.22]))
json.dump(vols, open(os.path.join(DATA, 'interaction_volumes.json'), 'w'), ensure_ascii=False, indent=1)
print('volumes', len(vols))

# ================================================================== cargo cases -> separate FBX
cargo = {}
for i, cn in enumerate(sorted(n.name for n in O if n.name.startswith('src_Case')), 1):
    ob = O[cn]
    ob.parent = None
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p[k] for p in pts) for k in range(3)))
    mx = Vector((max(p[k] for p in pts) for k in range(3)))
    bc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.transform(Matrix.Translation(-bc))
    name = f'SM_Cargo_Case{i}'
    ob.name = ob.data.name = name
    cargo[name] = dict(position=to_unity(bc), size=[round(mx.x - mn.x, 3), round(mx.z - mn.z, 3),
                                                     round(mx.y - mn.y, 3)],
                       note='concept-art placement in the UtilityPlane root space (m); spawn as a free physics body')
_items = sorted(cargo.values(), key=lambda c: c['position'][1])      # audit N5: no vertical overlap in stacks
for i, a in enumerate(_items):
    for b in _items[:i]:
        ox = min(a['position'][0] + a['size'][0] / 2, b['position'][0] + b['size'][0] / 2) - \
            max(a['position'][0] - a['size'][0] / 2, b['position'][0] - b['size'][0] / 2)
        oz = min(a['position'][2] + a['size'][2] / 2, b['position'][2] + b['size'][2] / 2) - \
            max(a['position'][2] - a['size'][2] / 2, b['position'][2] - b['size'][2] / 2)
        top = b['position'][1] + b['size'][1]
        if ox > 0.02 and oz > 0.02 and a['position'][1] < top:
            a['position'][1] = round(top + 0.002, 4)
            a['note'] = 'stacked: rests on the case below (m, UtilityPlane root space); spawn as a free physics body'
json.dump(cargo, open(os.path.join(DATA, 'cargo_layout.json'), 'w'), indent=1)

# ================================================================== cockpit: lamps, emissive lenses, statics
cp_rig = CPR['rig']
cockpit = empty('Cockpit', (0, 0, 0), ROOT, 0.2)
ann = O['CP_Annunciator']
for i in range(len(LY.ANNUN_LAMPS)):
    def is_lamp(f, bm, i=i):
        uvl = bm.loops.layers.uv['LampUV']
        return abs(f.loops[0][uvl].uv[0] - (i + 0.5)) < 0.25
    bm = bmesh.new()
    bm.from_mesh(ann.data)
    uvl = bm.loops.layers.uv['LampUV']
    ctr = [ann.matrix_world @ f.calc_center_median() for f in bm.faces
           if abs(f.loops[0][uvl].uv[0] - (i + 0.5)) < 0.25][0]
    bm.free()
    lamp = split_faces(ann, is_lamp, f'Lamp_{i:02d}', origin=ctr)
    set_parent(lamp, cockpit)
bpy.data.objects.remove(ann)
for lamp in [o for o in O if o.name.startswith('Lamp_')]:          # the second UV set only served the split
    while len(lamp.data.uv_layers) > 1:
        lamp.data.uv_layers.remove(lamp.data.uv_layers[-1])

li = mat_index(O['CP_Overhead'], 'M_Light_Cabin')
dome = split_faces(O['CP_Overhead'], lambda f, bm: f.material_index == li, 'Lens_Dome', origin=(0.0, -2.29, DOME_Z))
set_parent(dome, cockpit)
li = mat_index(O['CP_CargoLight'], 'M_Light_Cabin')
lcargo = split_faces(O['CP_CargoLight'], lambda f, bm: f.material_index == li, 'Lens_CargoLight',
                     origin=CARGO_LIGHTS[0])
set_parent(lcargo, cockpit)

SEAT_PTS = {t: verts_w('CP_Seat_' + t) for t in ('P', 'C')}       # seat colliders are hulls of the real seats
cp_static = [o.name for o in bpy.data.collections['Cockpit'].objects
             if o.type == 'MESH' and o.name not in cp_rig and not o.name.startswith(('Lamp_', 'Lens_', 'Display_')) and
             o.name != 'CP_RadioFaces']
join(cp_static, 'Cockpit_Static', cockpit)
for bone, info in cp_rig.items():
    par = cockpit if info['parent'] == 'Cockpit' else O[info['parent']]
    set_parent(O[bone], par)

# v6: radio unit faces (+ button tops) = Display_Radio with M_RadioDisplay (base T_Gauges_BC, backlit legends in
# T_Displays_Emission, driven by UtilityPlaneRig.avionicsPower); every display window is its own quad Display_<name>
# (UV 0..1 over the visible window, material M_Screen) for live content drawn by the game.
DISP = json.load(open(os.path.join(HERE, 'out', 'displays_v7.json')))
radio = O['CP_RadioFaces']
radio.name = radio.data.name = 'Display_Radio'
rp = [radio.matrix_world @ v.co for v in radio.data.vertices]
set_origin(radio, sum(rp, Vector()) / len(rp))
set_parent(radio, cockpit)
gi = mat_index(radio, 'M_Gauges')
assert gi >= 0 and len(radio.data.materials) == 1, [m.name for m in radio.data.materials]
radio.data.materials[gi] = bpy.data.materials.new('M_RadioDisplay')
for dn, d in DISP.items():
    ob = O[dn]
    set_origin(ob, d['centre'])
    set_parent(ob, cockpit)
    assert [m.name for m in ob.data.materials if m] == ['M_Screen'] or \
        {m.name for m in ob.data.materials if m} == {'M_Screen'}, (dn, [m.name for m in ob.data.materials])
print('Display_Radio faces', len(radio.data.polygons), '| display quads', sorted(DISP))

# ================================================================== exterior: light lenses, glass
lob = O['src_Lights']
LP = {k: Vector(v) for k, v in LIGHTS.items()}
for key, pos in LIGHTS.items():
    lens = split_faces(lob, lambda f, bm, key=key: min(LP, key=lambda k: (LP[k] - (lob.matrix_world @
                       f.calc_center_median())).length) == key, f'Lens_{key}', origin=pos)
    set_parent(lens, ROOT)
bpy.data.objects.remove(lob)
glass = O['src_GlassFixed']
glass.name = glass.data.name = 'Glass'
for d in ('PilotDoor_L', 'PilotDoor_R', 'CargoDoor_L', 'CargoDoor_R'):
    g = O[d + '__Glass']
    g.name = g.data.name = d + '_Glass'
    set_parent(g, O[d])

# ================================================================== v7 glass fog layers (SYS-01: demist / cabin heat)
# Inner copies of every pane, 3 mm towards the cabin, own UVs into T_GlassFog_Mask (4 x 3 cells of 256 x 341 px):
# R = clearing order (0 clears first .. 1 last), G = density, B = 1 on the windshield (defrost) / 0 elsewhere.
import numpy as np
from PIL import Image
FOG_CELLS = {}
CABIN_C = Vector((0.0, -1.0, 1.85))


def fog_layer(src_name, new_name, parent, panes_tag):
    src = O[src_name]
    bm = bmesh.new()
    bm.from_mesh(src.data)
    bm.transform(src.matrix_world)
    bm.faces.ensure_lookup_table()
    seen, comps = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        comps.append(comp)
    uvl = bm.loops.layers.uv.verify()
    moved = set()
    tags = []
    for comp in comps:
        c = sum((g.calc_center_median() for g in comp), Vector()) / len(comp)
        n = sum((g.normal * g.calc_area() for g in comp), Vector()).normalized()
        if n.dot(c - CABIN_C) < 0:
            n = -n                                              # outward
        ws = c.z > 2.0 and c.y < -2.6                          # windshield halves
        side = 'L' if c.x > 0 else 'R'
        if ws:
            tag = 'ws_' + side
            ax_u = Vector((-1, 0, 0))                          # pilot's right
        else:
            tag = panes_tag + side if panes_tag else ('side_' if c.y < 0 else 'aft_') + side
            ax_u = Vector((0, -1, 0)) if side == 'L' else Vector((0, 1, 0))   # towards the nose seen from inside
        ax_v = n.cross(ax_u).normalized()
        if ax_v.z < 0:
            ax_v = -ax_v
        ax_u = ax_v.cross(n).normalized() if not ws else ax_u
        vs = {v for g in comp for v in g.verts}
        us = [v.co.dot(ax_u) for v in vs]
        vv = [v.co.dot(ax_v) for v in vs]
        u0, u1, v0, v1 = min(us), max(us), min(vv), max(vv)
        cell = FOG_ORDER.index(tag)
        cx, cy = (cell % 4) * 256, (cell // 4) * 341
        FOG_CELLS[tag] = dict(rect=[cx, cy, 256, 341], windshield=ws)
        m = 0.04
        for g in comp:
            for lp in g.loops:
                uu = (lp.vert.co.dot(ax_u) - u0) / max(u1 - u0, 1e-6)
                ww = (lp.vert.co.dot(ax_v) - v0) / max(v1 - v0, 1e-6)
                px = cx + (m + (1 - 2 * m) * uu) * 256
                py = cy + (1 - (m + (1 - 2 * m) * ww)) * 341
                lp[uvl].uv = (px / 1024.0, 1.0 - py / 1024.0)
        for v in vs:
            if v.index not in moved:
                v.co -= n * 0.003
                moved.add(v.index)
        for g in comp:                                          # face the cabin (Cull Off in Unity anyway)
            if g.normal.dot(n) > 0:
                g.normal_flip()
        tags.append(tag)
    me = bpy.data.meshes.new(new_name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(new_name, me)
    SC.collection.objects.link(ob)
    while me.uv_layers and len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    me.materials.clear()
    me.materials.append(FOG_MAT)
    for p in me.polygons:
        p.material_index = 0
    ob.matrix_world = Matrix.Identity(4)
    set_origin(ob, parent.matrix_world.translation if parent is not ROOT else Vector((0, 0, 0)))
    set_parent(ob, parent)
    return tags


FOG_ORDER = ['ws_L', 'ws_R', 'pilot_L', 'pilot_R', 'side_L', 'side_R', 'cargo_L', 'cargo_R', 'aft_L', 'aft_R']
FOG_MAT = bpy.data.materials.new('M_GlassFog')
FOG_MAT.use_nodes = True
_pr = FOG_MAT.node_tree.nodes.get('Principled BSDF')
if _pr is not None:
    _pr.inputs['Alpha'].default_value = 0.0
FOG_OBJS = {'Glass_Fog': fog_layer('Glass', 'Glass_Fog', ROOT, None)}
for d, t in (('PilotDoor_L', 'pilot_'), ('PilotDoor_R', 'pilot_'), ('CargoDoor_L', 'cargo_'), ('CargoDoor_R', 'cargo_')):
    FOG_OBJS[d + '_Fog'] = fog_layer(d + '_Glass', d + '_Fog', O[d], t)
assert sorted(FOG_CELLS) == sorted(FOG_ORDER), sorted(FOG_CELLS)


def fog_mask():
    rng = np.random.default_rng(11)
    img = np.zeros((1024, 1024, 4), np.float32)
    img[..., 3] = 1.0
    yy, xx = np.mgrid[0:341, 0:256].astype(np.float32)
    u, v = (xx + 0.5) / 256, 1 - (yy + 0.5) / 341               # v = 0 at the pane bottom
    def blobs(sx, sy, n):
        h = np.zeros((341, 256), np.float32)
        for _ in range(n):
            kx, ky = rng.uniform(0.5, sx), rng.uniform(0.5, sy)
            h += np.sin(2 * np.pi * (kx * u + ky * v) + rng.uniform(0, 6.28)) / n
        return (h - h.min()) / max(h.max() - h.min(), 1e-6)
    for tag, info in FOG_CELLS.items():
        x0, y0 = info['rect'][:2]
        edge = np.clip(1 - np.minimum.reduce([u, 1 - u, v, 1 - v]) / 0.12, 0, 1)
        noise = blobs(9, 7, 14)
        if info['windshield']:                                # defrost vents along the bottom edge, centre first
            centre = 1.0 - (u * 2 - 1) ** 2 if tag == 'ws_L' else 1.0 - (u * 2 - 1) ** 2
            r = 0.10 + 0.62 * v + 0.18 * (1 - centre) + 0.20 * edge + 0.12 * (noise - 0.5)
        else:                                                   # cabin heat: from the bottom, slower at the edges
            r = 0.22 + 0.48 * v + 0.28 * edge + 0.12 * (noise - 0.5)
        dens = 0.70 + 0.30 * blobs(24, 20, 18)
        drops = rng.random((341, 256)) > 0.985
        dens = np.where(drops & (v < 0.35), 1.0, dens)
        cell = np.dstack([np.clip(r, 0, 1), np.clip(dens, 0, 1), np.full_like(r, 1.0 if info['windshield'] else 0.0),
                          np.ones_like(r)])
        img[y0:y0 + 341, x0:x0 + 256] = cell
    Image.fromarray((img * 255).round().astype(np.uint8), 'RGBA').save(os.path.join(TEXD, 'T_GlassFog_Mask.png'))


fog_mask()
json.dump(dict(note='UV cells of T_GlassFog_Mask (px rects in 1024 x 1024); R clearing order, G density, B windshield',
               cells=FOG_CELLS, objects=FOG_OBJS), open(os.path.join(DATA, 'glass_fog.json'), 'w'), indent=1)
print('fog layers', {k: len(v) for k, v in FOG_OBJS.items()})

# ================================================================== collider proxies (convex, <= ~250 tris each)
cols = empty('Colliders', (0, 0, 0), ROOT, 0.2)


def box_obj(name, x0, x1, y0, y1, z0, z1, parent):
    x0, x1 = sorted((x0, x1))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    set_parent(ob, parent)
    return ob


def hull_obj(name, pts, parent, max_tris=240):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    if len(me.polygons) > max_tris:
        md = ob.modifiers.new('dec', 'DECIMATE')
        md.ratio = max_tris / len(me.polygons)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier='dec')
    set_parent(ob, parent)
    return ob


def verts_of(names, cond=lambda p: True):
    out = []
    for n in names:
        ob = O[n]
        out += [p for p in (ob.matrix_world @ v.co for v in ob.data.vertices) if cond(p)]
    return out


F, YA = LY.FLOOR_Z, LY.REAR_BULKHEAD_Y
BAR = -1.72
box_obj('COL_Floor', -0.70, 0.70, LY.FIREWALL_Y, YA, 0.93, F + 0.004, cols)
box_obj('COL_Roof_Fwd', -0.74, 0.74, -2.62, -0.90, 2.528, 2.70, cols)
box_obj('COL_Roof_Aft', -0.74, 0.74, -0.90, YA, 2.585, 2.70, cols)
box_obj('COL_RearBulkhead', -0.72, 0.72, YA - 0.03, YA + 0.06, 0.96, 2.66, cols)
box_obj('COL_Barrier_Center', -0.28, 0.28, BAR - 0.025, BAR + 0.05, F, 2.55, cols)
for sg, s_ in ((1, 'L'), (-1, 'R')):
    box_obj(f'COL_Barrier_{s_}', sg * 0.28, sg * 0.67, BAR - 0.025, BAR + 0.05, F, 2.55, cols)
PDo, CDo = LY.PILOT_DOOR[0], LY.CARGO_DOOR[0]
pd_y0, pd_y1 = min(p[0] for p in PDo), max(p[0] for p in PDo)
pd_z0, pd_z1 = min(p[1] for p in PDo), max(p[1] for p in PDo)
cd_y0, cd_y1 = min(p[0] for p in CDo), max(p[0] for p in CDo)
cd_z0, cd_z1 = min(p[1] for p in CDo), max(p[1] for p in CDo)
for sg, s_ in ((1, 'L'), (-1, 'R')):
    xa, xb = sg * 0.665, sg * 0.77
    box_obj(f'COL_Wall_{s_}_Front', xa, xb, LY.FIREWALL_Y, pd_y0, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_Mid', xa, xb, pd_y1, cd_y0, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_Aft', xa, xb, cd_y1, YA, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_PilotSill', sg * 0.555, xb, pd_y0, pd_y1, 0.96, pd_z0 + 0.008, cols)
    box_obj(f'COL_Wall_{s_}_PilotHead', xa, xb, pd_y0, pd_y1, pd_z1, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_CargoSill', sg * 0.555, xb, cd_y0, cd_y1, 0.96, cd_z0 + 0.008, cols)
    box_obj(f'COL_Wall_{s_}_CargoHead', xa, xb, cd_y0, cd_y1, cd_z1, 2.62, cols)
    hull_obj(f'COL_Wing_{s_}', verts_of(['src_Wing', 'src_WingTE_Center', f'src_WingTE_Tip{s_}', f'Flap_{s_}',
                                         f'Aileron_{s_}'], lambda p, sg=sg: p.x * sg >= -0.01), cols)
    hull_obj(f'COL_Strut_{s_}', verts_of(['src_Struts'], lambda p, sg=sg: p.x * sg > 0), cols)
    hull_obj(f'COL_Gear_{s_}', verts_of([f'Gear_{s_}']), O[f'Gear_{s_}'])
    for d in (f'PilotDoor_{s_}', f'CargoDoor_{s_}'):
        hull_obj(f'COL_{d}', verts_of([d, d + '_Glass']), O[d])
for tag in ('P', 'C'):
    pts = SEAT_PTS[tag]
    low = [p for p in pts if p.z <= 1.46]
    hull_obj(f'COL_Seat_{tag}', low + [Vector((p.x, p.y, F)) for p in low], cols)
    hull_obj(f'COL_SeatBack_{tag}', [p for p in pts if p.z > 1.44 and p.y > -2.12], cols)
hull_obj('COL_Nose', verts_of(['src_Fuselage', 'src_CowlDetails'], lambda p: p.y < LY.FIREWALL_Y + 0.02), cols)
hull_obj('COL_Windshield', verts_of(['src_Fuselage'], lambda p: -3.34 < p.y < -2.60 and p.z > 2.0), cols)
hull_obj('COL_TailCone', verts_of(['src_Fuselage'], lambda p: p.y > YA - 0.02), cols)
hull_obj('COL_HStab', verts_of(['src_Stabilizer', 'Elevator_L', 'Elevator_R']), cols)
hull_obj('COL_Fin', verts_of(['src_Fin', 'Rudder', 'src_Dorsal']), cols)
box_obj('COL_Panel', -0.655, 0.655, LY.FIREWALL_Y, -2.975, F, 2.085, cols)
box_obj('COL_Pedestal', -0.09, 0.09, -2.985, -2.55, F, 1.45, cols)
hull_obj('COL_Propeller', verts_of(['Propeller', 'PropBlade_1', 'PropBlade_2', 'PropBlade_3']), O['Propeller'])
for sg, s_ in ((1, 'L'), (-1, 'R')):                      # audit N7
    box_obj(f'COL_Step_Cargo_{s_}', sg * 0.765, sg * 0.835, -0.35, -0.05, 0.82, 0.851, cols)
    st = Vector((sg * 0.961, -2.614, 0.474))               # tread on the aft gear blade (build_v2: sp + offset)
    near = sum(1 for p in verts_w(f'Gear_{s_}') if abs(p.x - st.x) < 0.07 and abs(p.y - st.y) < 0.055 and abs(p.z - st.z) < 0.02)
    assert near > 20, ('gear step not found', s_, near)
    box_obj(f'COL_Step_Pilot_{s_}', st.x - 0.065, st.x + 0.065, st.y - 0.05, st.y + 0.05, st.z - 0.025, st.z + 0.006,
            O[f'Gear_{s_}'])

# ================================================================== v7 props: step ladder (M5) and key (M2) -> separate FBX
LAD = EXT7['ladder']
lad = O['src_StepLadder']
legs = O['Ladder_RearLegs']
lad.parent = None
lad.matrix_world = Matrix.Identity(4)                      # mesh is built around the ground point under the platform
bpy.context.view_layer.update()
lad.name = lad.data.name = 'SM_StepLadder'
hw = LAD['half_w']


def lad_box(name, x0, x1, y0, y1, z0, z1, parent):
    ob = box_obj(name, x0, x1, y0, y1, z0, z1, None)
    set_parent(ob, parent)
    return ob


PROPS = {'SM_StepLadder': [], 'SM_PlaneKey': []}
H = LAD['H']
for i, h in enumerate(LAD['treads'], 1):
    y = LAD['y_front'] + (LAD['y_top_front'] - LAD['y_front']) * h / H
    PROPS['SM_StepLadder'].append(lad_box(f'COL_Ladder_Tread{i}', -hw + 0.01, hw - 0.01, y - 0.015, y + 0.115,
                                          h - 0.024, h, lad))
PROPS['SM_StepLadder'].append(lad_box('COL_Ladder_Platform', -hw + 0.01, hw - 0.01, LAD['y_top_front'] - 0.02,
                                      LAD['y_top_rear'] + 0.02, H - 0.03, H, lad))
for sx, s_ in ((-1, 'R'), (1, 'L')):
    PROPS['SM_StepLadder'].append(lad_box(f'COL_Ladder_Stile_{s_}', sx * hw - 0.02, sx * hw + 0.02,
                                          LAD['y_front'] - 0.03, LAD['y_top_front'] + 0.03, 0.0, H, lad))
    PROPS['SM_StepLadder'].append(lad_box(f'COL_Ladder_Rail_{s_}', sx * hw - 0.015, sx * hw + 0.015,
                                          LAD['y_top_front'] - 0.02, LAD['y_top_rear'] + 0.02, H, LAD['rail_top'], lad))
PROPS['SM_StepLadder'].append(lad_box('COL_Ladder_RearLegs', -hw - 0.04, hw + 0.04, LAD['y_rear'] - 0.15,
                                      LAD['y_rear'] + 0.02, 0.0, 0.55, legs))
# climb zone (trigger) in front of the treads; becomes IV_Ladder_Climb in the prefab
iv = lad_box('IV_Ladder_Climb', -hw + 0.02, hw - 0.02, LAD['y_front'] - 0.10, LAD['y_top_front'] + 0.05, 0.05,
             H + 0.20, lad)
PROPS['SM_StepLadder'].append(iv)
key = O['src_PlaneKey']
key.parent = None
kp = [key.matrix_world @ v.co for v in key.data.vertices]
kc = sum(kp, Vector()) / len(kp)
key.data.transform(key.matrix_world)
key.matrix_world = Matrix.Identity(4)
key.data.transform(Matrix.Translation(-kc))
key.name = key.data.name = 'SM_PlaneKey'

# ================================================================== body + hierarchy tidy
ext_static = ['src_Fuselage', 'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'src_Struts',
              'src_Fin', 'src_Stabilizer', 'src_CowlDetails', 'src_Antennas', 'src_WingDetails', 'src_FuseDetails',
              'src_Dorsal']
join([n for n in ext_static if n in O], 'Body', ROOT)
set_parent(glass, ROOT)

# audit N1: meshes without faces (ATT_Roll) become empties with the same transform and children
for ob in [o for o in ROOT.children_recursive if o.type == 'MESH' and len(o.data.polygons) == 0]:
    name, par, mw, kids = ob.name, ob.parent, ob.matrix_world.copy(), list(ob.children)
    ob.name = name + '__mesh'
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', 0.02
    SC.collection.objects.link(e)
    e.matrix_world = mw
    set_parent(e, par)
    for k in kids:
        set_parent(k, e)
    bpy.data.objects.remove(ob)
    print('mesh -> empty', name)

# ================================================================== sockets (empties)
socks = empty('Sockets', (0, 0, 0), ROOT, 0.2)
for name, pos in SOCK.items():
    empty(name, pos, socks, 0.04)
for name, (pos, par) in CHILD.items():
    empty(name, pos, cockpit if par == 'Cockpit' else O[par], 0.04)
PX_PER_MM = 10.0
POWER = {'Hobbs': 'busPowered'}
displays = {}
for dn, d in sorted(DISP.items()):
    w, h = d['size']
    displays[dn] = dict(
        parent='Cockpit', unit=d['unit'], position_prefab=to_unity(d['centre']), size=[w, h],
        aspect=round(w / h, 4), suggestedPixels=[int(round(w * 1000 * PX_PER_MM)), int(round(h * 1000 * PX_PER_MM))],
        power=POWER.get(d['unit'], 'avionicsPower'),
        note='mesh quad in the local XY plane facing -Z (towards the pilot), pivot at its centre, UV 0..1 = the '
             'visible window (u to the right, v up); material M_Screen (dark LCD). Draw live content into it '
             '(RenderTexture on its material, or a world-space canvas of this size at this transform).')
json.dump(displays, open(os.path.join(DATA, 'displays.json'), 'w'), indent=1)
json.dump({k: dict(parent='Sockets', position=to_unity(v)) for k, v in SOCK.items()} |
          {k: dict(parent=par, position_prefab=to_unity(p)) for k, (p, par) in CHILD.items()},
          open(os.path.join(DATA, 'sockets.json'), 'w'), indent=1)

# ================================================================== export FBX (Unity axes) with the nested-object fix
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import fbx_utils
_orig = fbx_utils.ObjectWrapper.fbx_object_matrix


def _patched(self, scene_data, rest=False, local_space=False, global_space=False):
    par = self.parent
    if (not local_space and not global_space and par is not None and self._tag == 'OB' and par._tag == 'OB'
            and not self.parented_to_armature and self.use_bake_space_transform(scene_data)
            and par.use_bake_space_transform(scene_data)):
        L = self.matrix_rest_local if rest else self.matrix_local
        return scene_data.settings.global_matrix @ L @ scene_data.settings.global_matrix_inv
    return _orig(self, scene_data, rest, local_space, global_space)


fbx_utils.ObjectWrapper.fbx_object_matrix = _patched
for ob in O:
    if ob.type == 'MESH' and ob.data.materials:          # drop unused material slots (one submesh per used material)
        me = ob.data
        used = sorted(set(p.material_index for p in me.polygons))
        keep = [me.materials[i] for i in used]
        idx = [used.index(p.material_index) for p in me.polygons]
        me.materials.clear()
        for m in keep:
            me.materials.append(m)
        for p, i in zip(me.polygons, idx):
            p.material_index = i
for ob in O:
    if ob.type == 'MESH':
        ob.data.name = ob.name
        if ob.data.uv_layers:
            ob.data.uv_layers[0].name = 'UVMap'
            ob.data.uv_layers.active_index = 0
        if not any(m.type == 'TRIANGULATE' for m in ob.modifiers):
            m = ob.modifiers.new('tri', 'TRIANGULATE')
            m.quad_method = m.ngon_method = 'BEAUTY'
            m.keep_custom_normals = True
    for k in list(ob.keys()):
        del ob[k]


def export(path, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'EMPTY', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Z', axis_up='Y', bake_space_transform=True,
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, use_triangles=False,
        use_custom_props=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False)


export(os.path.join(MOD, 'UtilityPlane.fbx'), [ROOT] + list(ROOT.children_recursive))
for name in cargo:
    export(os.path.join(MOD, name + '.fbx'), [O[name]])
export(os.path.join(MOD, 'SM_StepLadder.fbx'), [O['SM_StepLadder']] + list(O['SM_StepLadder'].children_recursive))
export(os.path.join(MOD, 'SM_PlaneKey.fbx'), [O['SM_PlaneKey']])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_unity_{TAG}.blend'))

def _rot_x(p, a):                                   # Unity Euler(a, 0, 0) applied to a Unity-space point
    x, y, z = p
    return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))


_pitch = math.radians(LY.PARK_PITCH_DEG)
_main_c = to_unity((LY.MAIN_WHEEL_C[0], LY.MAIN_WHEEL_C[1], LY.MAIN_CONTACT_Z))
_tail_c = to_unity((0.0, LY.TAIL_WHEEL_C[1], LY.TAIL_CONTACT_Z))
_root_h = -_rot_x(_main_c, -_pitch)[1]


def _arm(pivot, wheel, lateral):
    h = abs(wheel[0] - pivot[0]) if lateral else abs(wheel[1] - pivot[1])
    v = pivot[2] - wheel[2]
    return dict(r=round(math.hypot(h, v), 4), phi0Deg=round(math.degrees(math.atan2(v, h)), 3))


def _parked_y(p_build):
    return round(_rot_x(to_unity(p_build), -_pitch)[1] + _root_h, 3)


facts = dict(
    note='Unity prefab space, m. Model frame is level (cabin floor Y 1.07); parked on flat ground the root is pitched '
         'nose-up (Euler X = -parkedPitchDeg) and its height over the ground is parkedRootHeight (struts unloaded).',
    parkedPitchDeg=round(LY.PARK_PITCH_DEG, 3), parkedRootHeight=round(_root_h, 4),
    mainWheelCentreL=to_unity(LY.MAIN_WHEEL_C), mainWheelRadius=LY.MAIN_WHEEL_R,
    tailWheelCentre=to_unity(LY.TAIL_WHEEL_C), tailWheelRadius=LY.TAIL_WHEEL_R,
    mainContactY=round(LY.MAIN_CONTACT_Z, 4), tailContactY=round(LY.TAIL_CONTACT_Z, 4),
    wheelbase=round(LY.TAIL_WHEEL_C[1] - LY.MAIN_WHEEL_C[1], 3), track=round(2 * LY.MAIN_WHEEL_C[0], 3),
    mainGearArm=_arm((0.46, -2.85, LY.MAIN_LEG_TOP_Z), LY.MAIN_WHEEL_C, True),
    tailGearArm=_arm(LY.TAIL_SPRING_MOUNT, LY.TAIL_WHEEL_C, False),
    parkedHeights=dict(
        note='m above flat ground in the parked pose; door sills as [front end, aft end]',
        pilotDoorSill=[_parked_y((0.70, min(p[0] for p in LY.PILOT_DOOR[0]), min(p[1] for p in LY.PILOT_DOOR[0]))),
                       _parked_y((0.70, max(p[0] for p in LY.PILOT_DOOR[0]), min(p[1] for p in LY.PILOT_DOOR[0])))],
        cargoDoorSill=[_parked_y((0.70, min(p[0] for p in LY.CARGO_DOOR[0]), min(p[1] for p in LY.CARGO_DOOR[0]))),
                       _parked_y((0.70, max(p[0] for p in LY.CARGO_DOOR[0]), min(p[1] for p in LY.CARGO_DOOR[0])))],
        cargoStepTop=_parked_y((0.80, -0.20, 0.851)), pilotStepTop=_parked_y((0.961, -2.614, 0.48)),
        pilotEye=_parked_y(LY.PILOT_EYE), propAxis=_parked_y(LY.PROP_C),
        propTipClearance=round(_parked_y(LY.PROP_C) - 1.3205 * math.cos(_pitch), 3),
        propTipClearanceTailUp=round(LY.PROP_C[2] - 1.3205 - LY.MAIN_CONTACT_Z, 3)),
)


def _parked_world(p_build):
    u = _rot_x(to_unity(p_build), -_pitch)
    return Vector((u[0], u[1] + _root_h, u[2]))


def _wing_upper_z(x, xc):
    t = 0.13
    yt = 5 * t * (0.2969 * math.sqrt(max(xc, 0)) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3 - 0.1036 * xc ** 4)
    p_, m_ = 0.4, 0.02
    yc = m_ / p_ ** 2 * (2 * p_ * xc - xc ** 2) if xc < p_ else m_ / (1 - p_) ** 2 * ((1 - 2 * p_) + 2 * p_ * xc - xc ** 2)
    return wz(x) + (yc + yt) * W_CH


EYE_ABOVE_FEET = 1.65
lad_ground = _parked_world(SOCK['Socket_Ladder_Fuel_L'])
lad_ground.y = 0.0
eye = lad_ground + Vector((0.0, LAD['H'] + EYE_ABOVE_FEET, 0.0))
cap = _parked_world(SOCK['Socket_FuelCap_L'])
clear = min((eye.y + (cap.y - eye.y) * ((_parked_world((1.55, W_LE + xc * W_CH, _wing_upper_z(1.55, xc))).z - eye.z) /
                                         (cap.z - eye.z))) - _parked_world((1.55, W_LE + xc * W_CH,
                                                                            _wing_upper_z(1.55, xc))).y
            for xc in [i / 40 * 0.24 for i in range(1, 40)])
le_w = _parked_world((1.55, W_LE, wz(1.55)))
facts['ladder'] = dict(
    note='SM_StepLadder at Socket_Ladder_Fuel_L/R (flat ground, same yaw as the plane, its +Z = the plane nose): '
         'player feet on the platform, eye 1.65 m above them (assumption, set your own)',
    platformHeight=LAD['H'], treadHeights=list(LAD['treads']), eyeHeight=round(eye.y, 3),
    fuelCapHeight=round(cap.y, 3), eyeToCap=round((cap - eye).length, 3),
    eyeAboveCap=round(eye.y - cap.y, 3), sightLineClearanceOverWing=round(clear, 3),
    leadingEdgeHeight=round(le_w.y, 3), playerToLeadingEdge=round(abs(le_w.z - lad_ground.z), 3),
    railTop=LAD['rail_top'])
facts['propeller'] = dict(
    note='PropBlade_1..3 are children of Propeller, pivot on the hub centre; local Y (Unity) = blade span = pitch axis. '
         'Modelled at fine pitch (blade angle 28 deg at r = 0.76 m); feather = +62 deg about the span (see contract).',
    tipRadius=1.322, rpmMax=1900)
json.dump(facts, open(os.path.join(DATA, 'model_facts.json'), 'w'), indent=1)
print('facts', json.dumps(facts))

dg = bpy.context.evaluated_depsgraph_get()


def tri_count(objs):
    t = 0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        t += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return t


rend = [o for o in ROOT.children_recursive if o.type == 'MESH' and not o.name.startswith('COL_')]
cp_objs = [o for o in rend if o.name in cp_rig or o.name.startswith(('Cockpit', 'Lamp_', 'Lens_Dome', 'Lens_Cargo',
                                                                        'Display_'))]
print('UNITY objects', len(ROOT.children_recursive), 'render tris', tri_count(rend), 'cockpit tris', tri_count(cp_objs),
      'colliders', sum(1 for o in ROOT.children_recursive if o.name.startswith('COL_')),
      'sockets', len(SOCK) + len(CHILD), 'static colliders', len(cols.children))
