"""Unity export of Utility Plane v10 (from out/plane_v9_final_<tag>.blend = the v9 scene after the v10 geometry pass;
textures: export/unity_v10/.../Textures written by tex_v10.py).
usage: python3 export_unity_v10.py [tag=v10]
Output: export/unity_v10/Assets/UtilityPlane/{Models,Data,Textures (fog mask)}
 - UtilityPlane.fbx: hierarchy of rigid parts, every moving part = own object with its pivot on its hinge/axle,
   Unity axes (nose +Z, up +Y, right +X), metres. Sockets = empties. Collider proxies = COL_* meshes.
 - SM_Cargo_Case1..6.fbx (pivot at the bottom centre)
 - Data/interaction_volumes.json, cargo_layout.json, displays.json, sockets.json (atlas_texel.json from finalize)
v5: parked tail-down (9.98 deg), sockets computed here (no UE detour), lined cabin, 6 atlases.
v6: instrument panel v6 - display quads Display_* (UV 0..1), radio faces = Display_Radio, map case lid,
    starter guard, VOLT / VAC needles; 44 interaction zones.
v7: cabin door switches, radio / ALT / HDG knobs, Kollsman disc, heading bug, compass card, door locks + keyhole
    sockets, prop blades with pitch axes + PropBlur / PropDisc, glass fog layers (Glass_Fog, *_Fog, M_GlassFog),
    SM_StepLadder (+ colliders, climb zone) and SM_PlaneKey, ladder sockets at the fuel fillers.
v8: streamlined struts, smooth dorsal fin, two airframe materials (M_Airframe, M_Wing), LOD meshes: <part>_LOD1 /
    <part>_LOD2 children (same pivot, decimated) + Data/lod.json (two LOD groups: Exterior on the root, Cockpit).
v9: cargo bay troop seats PaxSeat_<L1|R1|L2|R2> (+ _Leg) and Cabin_Fittings (M_Fittings) under Cockpit, door clip /
    holster under the pilot doors, Stow_LadderStraps; sockets with rotations (pax seat pelvis / eye / exit, stow
    points, horror apparition points, audio emitters); survival kit SM_Surv_*.fbx (M_Survival, PSX); new Data:
    pax_seats.json, stowage.json, horror.json, survival_kit.json.
v10: optimisation - reduced LOD0 meshes (colliders, sockets and zones still derived from the v9 meshes) (error-bounded, see the contract, section 17), LOD1/LOD2 made with
    meshoptimizer (seams, hard edges and material borders kept), shadow proxies <part>_Shadow (ShadowsOnly renderers in
    LOD0, Data/lod.json shadowProxies), interior atlases 1024 px."""
import meshopt_lod as MO
import bpy, bmesh, os, sys, json, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

TAG = sys.argv[1] if len(sys.argv) > 1 else 'v13'
OUT = os.path.join(HERE, 'export', 'unity_v13fx', 'Assets', 'UtilityPlane')
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


# v10b: everything the export derives from mesh vertices (collider hulls, socket points, zone points) is read from the
# v9 meshes, so colliders and sockets stay exactly as in v9 (a reduced mesh keeps a subset of the v9 vertices: a hull
# of it can shrink by up to the reduction tolerance).
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9_final_v9.blend'))
V9W, V9Z = {}, {}
for _o in bpy.data.objects:
    if _o.type == 'MESH':
        _mw = _o.matrix_world.copy()
        V9W[_o.name] = [_mw @ _v.co for _v in _o.data.vertices]
        if 'fz' in _o.data.attributes:
            _fz = _o.data.attributes['fz'].data
            V9Z[_o.name] = [(_fz[_p.index].value, tuple(_p.vertices)) for _p in _o.data.polygons]
print('v9 vertices cached for', len(V9W), 'meshes', flush=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v9_final_{TAG}.blend'))
O = bpy.data.objects
SC = bpy.context.scene
CPR = json.load(open(os.path.join(HERE, 'out', 'cockpit_rig_v7.json')))
EXT7 = json.load(open(os.path.join(HERE, 'out', 'ext_v7.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'light_pos_v13.json')))   # v13: fixtures, belly beacon up on the skin
E9 = json.load(open(os.path.join(HERE, 'out', 'ext_v9.json')))
S9 = E9['seat']
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
    if name in V9W:                                    # v10b: v9 geometry (see the cache above)
        return [p.copy() for p in V9W[name]]
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
LAD_SOCK = tuple(EXT7['ladder_socket'])     # v7 (M5): ground under the platform centre, outboard of the main wheel,
for sg, s_ in ((1, 'L'), (-1, 'R')):        # 0.40 m ahead of the leading edge in the parked pose (ext_v7.ladder_socket)
    SOCK[f'Socket_Ladder_Fuel_{s_}'] = (sg * LAD_SOCK[0], LAD_SOCK[1], LAD_SOCK[2])
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
    # v13: pull grip on the front edge of the sliding door (reachable from inside the bay when the door is slid aft)
    'Socket_Handle_CargoDoor_L_Edge': ((0.726, -0.847, 1.70), 'CargoDoor_L'),
    'Socket_Handle_CargoDoor_R_Edge': ((-0.726, -0.847, 1.70), 'CargoDoor_R'),
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
    'Socket_Handle_CargoDoor_L_Edge': ('CargoDoor_L', (0.03, 0.13, 0.03), 'door', 'Грузовая дверь, левая'),     # v13
    'Socket_Handle_CargoDoor_R_Edge': ('CargoDoor_R', (0.03, 0.13, 0.03), 'door', 'Грузовая дверь, правая'),    # v13
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
PRE9 = [dict(v) for v in vols]                                  # zones up to v8 (stow zones keep clear of them)
# v9: cargo bay seats (sit volume over the pan, fold handle strip on the pan front) and stow points
PAX_LABEL = {'L1': 'Откидное кресло, левое переднее', 'R1': 'Откидное кресло, правое переднее',
             'L2': 'Откидное кресло, левое заднее', 'R2': 'Откидное кресло, правое заднее'}
for tag, sd in E9['seats'].items():
    sg, yc = sd['sgn'], sd['yc']
    vols.append(dict(id=f'PaxSeat_{tag}', parent='Cockpit', kind='seat', label=PAX_LABEL[tag],
                     center=to_unity((sg * 0.44, yc, 1.725)), halfExtents=ext_unity((0.17, 0.20, 0.205))))
    c = Vector((sg * (S9['XF'] + 0.045), yc, S9['ZH'] - 0.008)) - PIVOT[f'PaxSeat_{tag}']
    vols.append(dict(id=f'PaxSeatFold_{tag}', parent=f'PaxSeat_{tag}', kind='hinge', label='Откинуть / сложить сиденье',
                     center=vec_unity(c), halfExtents=ext_unity((0.065, 0.20, 0.035))))


def world_box(names):
    pts = []
    for n in names:
        ob = O[n]
        pts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector([min(q[i] for q in pts) for i in range(3)])
    mx = Vector([max(q[i] for q in pts) for i in range(3)])
    return mn, mx


STOW_LABEL = {'Flashlight': 'Держатель фонаря', 'FlareGun': 'Кобура ракетницы', 'Shovel': 'Крепление лопаты',
              'SurvivalBag': 'Место аварийной сумки', 'JerryCan': 'Держатель канистры',
              'Ladder': 'Место стремянки (на полу, стропы)'}
STOW_BOX = {}
for k, s in E9['stow'].items():
    if k == 'Ladder':
        b = E9['ladder_stowed_box']
        mn, mx = Vector(b['min']), Vector(b['max'])
    elif k == 'JerryCan':
        J = E9['jerry']
        mn = Vector((J['x0'], J['yb'] - J['depth'], J['z0']))
        mx = Vector((J['x1'], J['yb'], J['z0'] + 0.48))
    else:
        mn, mx = world_box([s['item']] + (['Surv_Bag_Strap'] if False else []))
    STOW_BOX[k] = (mn.copy(), mx.copy())
    base = Vector((0, 0, 0)) if s['parent'] == 'Cockpit' else PIVOT[s['parent']]
    mn, mx = mn - Vector((0.01, 0.01, 0.01)), mx + Vector((0.01, 0.01, 0.01))
    for v in PRE9:                      # e.g. the flare gun grip right under the inner handle of the right door
        vb = Vector((0, 0, 0)) if v['parent'] in ('Cockpit', 'UtilityPlane') else PIVOT[v['parent']]
        vc = vb + Vector((-v['center'][0], -v['center'][2], v['center'][1]))
        vh = Vector((v['halfExtents'][0], v['halfExtents'][2], v['halfExtents'][1]))
        lo, hi = vc - vh, vc + vh
        if min(min(mx[i], hi[i]) - max(mn[i], lo[i]) for i in range(3)) <= 0:
            continue
        cuts = [((mx[i] - lo[i] + 0.005), i, 1) if vc[i] > (mn[i] + mx[i]) / 2 else ((hi[i] + 0.005 - mn[i]), i, 0)
                for i in range(3)]
        d, i, top = min(cuts)
        if top:
            mx[i] = lo[i] - 0.005
        else:
            mn[i] = hi[i] + 0.005
        print('stow zone', k, 'clipped against', v['id'], 'axis', 'xyz'[i], 'by', round(d, 4), flush=True)
    c, h = (mn + mx) / 2 - base, (mx - mn) / 2
    vols.append(dict(id=f'Stow_{k}', parent=s['parent'], kind='stow', label=STOW_LABEL[k], center=vec_unity(c),
                     halfExtents=ext_unity(h)))
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
for n in ['Cabin_Fittings', 'Stow_LadderStraps'] + [f'PaxSeat_{t}' for t in E9['seats']]:      # v9 cargo bay
    set_parent(O[n], cockpit)
SURV = sorted(o.name for o in O if o.name.startswith('SM_Surv_'))
for n in SURV:                                                 # display placements (door clip / holster) undone
    ob = O[n]
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.hide_viewport = ob.hide_render = False
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
# v11: panel flood lamps under the glareshield lip (CP_PanelFloods: housings + arms join Cockpit_Static, the lenses are
# Lens_Flood_L / Lens_Flood_R with their origin at the light origin of Light_Flood / Light_Flood_2)
_pf = O['CP_PanelFloods']
li = mat_index(_pf, 'M_Light_Cabin')
for _side, _ux in (('L', -0.30), ('R', 0.30)):
    _lf = split_faces(_pf, lambda f, bm, ux=_ux: f.material_index == li and
                      ((-(_pf.matrix_world @ f.calc_center_median()).x) > 0) == (ux > 0),
                      f'Lens_Flood_{_side}', origin=(-_ux, -2.865, 2.010))
    set_parent(_lf, cockpit)
for _side, _ux in (('L', -0.30), ('R', 0.30)):                    # the housing + arm + plate of each lamp: own renderer,
    _ph = split_faces(_pf, lambda f, bm, ux=_ux: ((-(_pf.matrix_world @ f.calc_center_median()).x) > 0) == (ux > 0),
                      f'PanelFlood_{_side}', origin=(-_ux, -2.865, 2.010))   # LOD0 only (Cockpit_Static LODs unchanged)
    set_parent(_ph, cockpit)
bpy.data.objects.remove(_pf)

SEAT_PTS = {t: verts_w('CP_Seat_' + t) for t in ('P', 'C')}       # seat colliders are hulls of the real seats
cp_static = [o.name for o in bpy.data.collections['Cockpit'].objects
             if o.type == 'MESH' and o.name not in cp_rig and not o.name.startswith(('Lamp_', 'Lens_', 'Display_', 'PanelFlood_')) and
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
        out += [p for p in verts_w(n) if cond(p)]
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
        # v13: the cargo door hull leaves out the roller arms (inboard of the trim, which reaches |x| 0.621): a hull
        # through the arm tips (|x| 0.566) would add a 5 cm slab across the bay side of the closed door
        cond = (lambda p, sg=sg: p.x * sg > 0.618) if d.startswith('CargoDoor') else (lambda p: True)
        hull_obj(f'COL_{d}', verts_of([d, d + '_Glass'], cond), O[d])
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

# v9 cargo bay: seat pan + leg hulls ride with their parts; the wall part of each seat (rails, back canvas, brackets)
# and the jerry-can bracket are static boxes
for tag, sd in E9['seats'].items():
    sg, yc = sd['sgn'], sd['yc']
    pan, leg = O[f'PaxSeat_{tag}'], O[f'PaxSeat_{tag}_Leg']
    hull_obj(f'COL_PaxSeat_{tag}', verts_of([pan.name]), pan)
    hull_obj(f'COL_PaxSeatLeg_{tag}', verts_of([leg.name]), leg)
    box_obj(f'COL_PaxBack_{tag}', sg * (S9['XR'] - 0.018), sg * S9['XW'], yc - 0.245, yc + 0.245, S9['ZH'] - 0.036,
            S9['ZU'] + 0.016, cols)
J = E9['jerry']
box_obj('COL_JerryBracket', J['x0'] - 0.003, J['x1'] + 0.003, J['yb'] - J['depth'] - 0.003, J['yb'], J['z0'],
        J['z0'] + 0.12, cols)

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

# v9 survival kit: each item at the origin (pivot = grip, model -Y = forward = Unity +Z), convex hull colliders and
# its working points as sockets
ZN = E9['zones']


def zone_verts(name, zones):
    if name in V9Z:                                    # v10b: v9 geometry
        idx = {vi for z, vs in V9Z[name] if z in zones for vi in vs}
        return [V9W[name][i].copy() for i in idx]
    me = O[name].data
    fz = me.attributes['fz'].data
    idx = {vi for p_ in me.polygons if fz[p_.index].value in zones for vi in p_.vertices}
    return [O[name].matrix_world @ me.vertices[i].co for i in idx]


SURV_SOCK = {'SM_Surv_Flashlight': {'Socket_Light': 'light'}, 'SM_Surv_Flare': {'Socket_Flame': 'flame'},
             'SM_Surv_FlareGun': {'Socket_Muzzle': 'muzzle', 'Socket_Breech': 'breech'},
             'SM_Surv_Shovel': {'Socket_BladeTip': 'blade_tip'}, 'SM_Surv_Bag': {'Socket_Bottom': 'bottom'},
             'SM_Surv_FlareShell': {}}
for n in SURV:
    ob = O[n]
    if n == 'SM_Surv_Shovel':
        hull_obj('COL_Shovel_Blade', zone_verts(n, [ZN['SHOVEL_BLADE']]), ob)
        hull_obj('COL_Shovel_Shaft', zone_verts(n, [ZN['SHOVEL_SHAFT'], ZN['SHOVEL_GRIP']]), ob)
    elif n == 'SM_Surv_Bag':
        hull_obj('COL_Surv_Bag', zone_verts(n, [ZN['BAG']]), ob)
    else:
        hull_obj('COL_' + n[3:], verts_w(n), ob)
    for sk, key_ in SURV_SOCK[n].items():
        empty(sk, tuple(E9['items'][n][key_]), ob, 0.02)

# ================================================================== body + hierarchy tidy
ext_static = ['src_Fuselage', 'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'src_Struts',
              'src_Fin', 'src_Stabilizer', 'src_CowlDetails', 'src_Antennas', 'src_WingDetails', 'src_FuseDetails',
              'src_Dorsal', 'src_LightMounts', 'src_DoorRails']          # v13: light fixtures, sliding-door rails
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
# v9 sockets with an orientation (pax pelvis / eye / exit, stow points, scare points): Unity +Z of the socket =
# where the occupant / item / figure faces, +Y = up
C_U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))
SOCK9_JSON = {}
for name, s in E9['sockets'].items():
    par = socks if s['parent'] == 'Sockets' else cockpit if s['parent'] == 'Cockpit' else O[s['parent']]
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 0.05
    SC.collection.objects.link(e)
    R = Matrix(s['rot'])
    e.matrix_world = Matrix.Translation(Vector(s['pos'])) @ R.to_4x4()
    set_parent(e, par)
    RU = C_U @ R @ C_U.transposed()
    q = RU.to_quaternion()
    base = Vector((0, 0, 0)) if s['parent'] in ('Sockets', 'Cockpit') else PIVOT[s['parent']]
    SOCK9_JSON[name] = dict(parent=s['parent'], position_prefab=to_unity(s['pos']),
                            **({'position': to_unity(s['pos'])} if s['parent'] == 'Sockets' else {}),
                            position_local=to_unity(Vector(s['pos']) - base),
                            rotation=[round(q.x, 6) + 0.0, round(q.y, 6) + 0.0, round(q.z, 6) + 0.0, round(q.w, 6) + 0.0],
                            forward=[round(c, 5) + 0.0 for c in RU @ Vector((0, 0, 1))],
                            up=[round(c, 5) + 0.0 for c in RU @ Vector((0, 1, 0))])
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
# v13: sliding cargo doors (out/doors_v13.json from src_v13.py) in Unity prefab space
_dj = json.load(open(os.path.join(HERE, 'out', 'doors_v13.json')))
_doors = dict(note='v13 sliding cargo doors (Unity prefab space, m). t = cargoDoorL / cargoDoorR (0 closed .. 1 open). '
                   'Pose: localRotation = AngleAxis(side * yawDeg, up) * rest, localPosition = rest + (side * outRear, 0, '
                   '-back), side = -1 left / +1 right (outward). p = t / popEnd; outFront = out * S3(p / 0.75), outRear = '
                   'out * S3((p - 0.25) / 0.75), back = slide * S5((t - slideStart) / (1 - slideStart)); outRear -= '
                   'tuck * s^2, s = clamp01((back - tuckStart) / (slide - tuckStart)) (the rear follows the tapering side); '
                   'yawDeg = atan2(outFront - outRear, length) (front swings out first). S3 = smoothstep, S5 = smootherstep. '
                   'UtilityPlaneRig.SlidingDoorPose gives the same pose (use it for presentation and obstruction tests).',
              out=_dj['D_OUT'], slide=_dj['D_BACK'], popEnd=_dj['T_POP'], slideStart=_dj['T_SLIDE0'],
              tuck=_dj['D_TUCK'], tuckStart=_dj['B_TUCK0'],
              doors={})
for _s, _d in _dj['doors'].items():
    _doors['doors'][f'CargoDoor_{_s}'] = dict(
        side=-1 if _s == 'L' else 1, pivot=to_unity(_d['pivot']), length=_d['length'],
        frontEdgeZ=round(-_d['y_front'], 4),
        rails={k: dict(heightY=round(r['z'], 4), fromZ=round(-r['y_from'], 4), toZ=round(-r['y_to'], 4),
                       outerX=round((-1 if _s == 'L' else 1) * r['x_outer'], 4), rollerClosed=to_unity(r['tip_closed']))
               for k, r in _d['rails'].items()})
json.dump(_doors, open(os.path.join(DATA, 'doors.json'), 'w'), indent=1)
json.dump({k: dict(parent='Sockets', position=to_unity(v)) for k, v in SOCK.items()} |
          {k: dict(parent=par, position_prefab=to_unity(p)) for k, (p, par) in CHILD.items()} | SOCK9_JSON,
          open(os.path.join(DATA, 'sockets.json'), 'w'), indent=1)

# ================================================================== v8 LODs: decimated children + Data/lod.json
# Every LOD mesh is a child of its source part with an identity local transform, so moving parts (doors, wheels,
# yokes, propeller) carry their LODs along. 'keep' = the LOD level reuses the source renderer, 'drop' = not drawn.
LOD_SPEC = {
    'Body': (0.40, 0.12), 'PilotDoor_L': (0.35, 0.10), 'PilotDoor_R': (0.35, 0.10), 'CargoDoor_L': (0.35, 0.10),
    'CargoDoor_R': (0.35, 0.10), 'Wheel_L': (0.25, 0.06), 'Wheel_R': (0.25, 0.06), 'TailWheel': (0.25, 0.06),
    'Propeller': ('keep', 0.30), 'Gear_L': ('keep', 0.45), 'Gear_R': ('keep', 0.45),
    'Cockpit_Static': (0.25, 0.05), 'Yoke_P_Roll': (0.30, 'drop'), 'Yoke_C_Roll': (0.30, 'drop'),
    'Cabin_Fittings': (0.40, 'drop'), 'Stow_LadderStraps': ('keep', 'drop'),                         # v9
}
for _t in E9['seats']:
    LOD_SPEC[f'PaxSeat_{_t}'] = (0.40, 'drop')
    LOD_SPEC[f'PaxSeat_{_t}_Leg'] = ('keep', 'drop')
EXT_DROP1 = ('Lock_', 'PilotDoor_L_Clip', 'PilotDoor_R_Holster')   # not drawn from LOD1 on (v9: door clip, holster)
EXT_DROP2 = ('Lock_', 'FuelCap_', 'Glass_Fog', 'PilotDoor_L_Clip', 'PilotDoor_R_Holster')   # ... from LOD2 on (+ *_Fog)
CP_KEEP1 = ('Yoke_P', 'Yoke_C', 'Belt_', 'Display_', 'Lens_Dome', 'Lens_CargoLight', 'Visor_', 'Glovebox_Lid')
CP_KEEP2 = ('Lens_Dome', 'Lens_CargoLight')
LOD_HEIGHTS = {'Exterior': (0.25, 0.08, 0.004), 'Cockpit': (0.30, 0.10, 0.03)}   # exterior hidden > ~3 km (kit items stay sub-pixel)


LOD_METHOD = {}
V9LOD = json.load(open(os.path.join(HERE, 'out', 'lod_budget_v9.json')))['tris']


def make_lod(src_name, ratio, suffix):
    """v10: meshoptimizer LOD (see meshopt_lod.py: seams, hard edges and material borders kept) as a child of the part
    with an identity local transform. Where the seams stop it short of the target (tread blocks, dense cabin parts),
    the v8/v9 method instead: Blender Decimate (collapse) to the target ratio."""
    src = O[src_name]
    name = f'{src_name}_{suffix}'
    src_tris = sum(len(p.vertices) - 2 for p in src.data.polygons)
    if name in V9LOD:                       # v10b: the same triangle budget as the v9 LOD (smaller pops at the switch)
        ratio = min(1.0, V9LOD[name] / src_tris)
    target = src_tris * ratio
    me, err = MO.lod_mesh(src.data, ratio, name)
    if sum(len(p.vertices) - 2 for p in me.polygons) <= 1.15 * target:
        ob = bpy.data.objects.new(name, me)
        SC.collection.objects.link(ob)
        ob.parent = src
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = Matrix.Identity(4)
        LOD_METHOD[name] = 'meshoptimizer'
        return ob
    bpy.data.meshes.remove(me)
    me = src.data.copy()
    if 'custom_normal' in me.attributes:    # v10b: Decimate cannot carry stored normals (they would decode against
        me.attributes.remove(me.attributes['custom_normal'])    # the new fans): normals from the faces and sharp edges
    ob = bpy.data.objects.new(name, me)
    me.name = name
    SC.collection.objects.link(ob)
    ob.parent = src
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Identity(4)
    md = ob.modifiers.new('dec', 'DECIMATE')
    md.decimate_type = 'COLLAPSE'
    md.ratio = ratio
    md.use_collapse_triangulate = True
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier='dec')
    # v10b: shading normals of the decimated LOD taken from the part's own surface (as drawn in LOD0), corner by
    # corner on the same side of hard edges - the LOD switch then changes the outline, not the light
    import sys as _s
    _s.path.insert(0, '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt')
    import opt_lib as _OL, sharp_lib as _SL
    _src_td = _OL.TriData(src.data)
    _OL.transfer_normals(ob.data, _src_td)
    _SL.set_normals(ob.data, _SL._readback(ob.data))
    LOD_METHOD[name] = 'decimate'
    return ob


cockpit_set = {o.name for o in cockpit.children_recursive}
renderers = [o for o in ROOT.children_recursive if o.type == 'MESH' and not o.name.startswith(('COL_', 'IV_'))]
lods = {}
for src_name, (r1, r2) in LOD_SPEC.items():
    for lvl, r in ((1, r1), (2, r2)):
        if isinstance(r, float):
            lods[(src_name, lvl)] = make_lod(src_name, r, f'LOD{lvl}').name
        else:
            lods[(src_name, lvl)] = r                       # 'keep' / 'drop'
levels = {'Exterior': [[], [], []], 'Cockpit': [[], [], []]}
for o in renderers:
    n = o.name
    grp = 'Cockpit' if n in cockpit_set else 'Exterior'
    levels[grp][0].append(n)
    for lvl in (1, 2):
        spec = lods.get((n, lvl))
        if spec == 'drop':
            continue
        if spec not in (None, 'keep'):
            levels[grp][lvl].append(spec)
            continue
        if grp == 'Exterior':
            drop = EXT_DROP1 if lvl == 1 else EXT_DROP2
            if n.startswith(drop) or (lvl == 2 and n.endswith('_Fog')):
                continue
        else:
            keep = CP_KEEP1 if lvl == 1 else CP_KEEP2
            if spec != 'keep' and not n.startswith(keep):
                continue
        levels[grp][lvl].append(n)
# v10 shadow proxies: <part>_Shadow = simplified welded copy (borders locked) drawn ShadowsOnly in LOD0; the part
# itself casts no shadow in LOD0. LOD1 / LOD2 meshes cast their own shadows.
SHADOW_SPEC = {'Cockpit_Static': 0.004, 'Cabin_Fittings': 0.004, 'Wheel_L': 0.008, 'Wheel_R': 0.008,
               'TailWheel': 0.008}
shadow_proxies = []
for src_name, err_m in SHADOW_SPEC.items():
    src = O[src_name]
    me, err = MO.shadow_mesh(src.data, err_m, f'{src_name}_Shadow')
    ob = bpy.data.objects.new(f'{src_name}_Shadow', me)
    SC.collection.objects.link(ob)
    ob.parent = src
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Identity(4)
    grp = 'Cockpit' if src_name in cockpit_set else 'Exterior'
    levels[grp][0].append(ob.name)
    shadow_proxies.append(dict(renderer=ob.name, source=src_name, group=grp, errorMm=round(err_m * 1000, 1)))
dg = bpy.context.evaluated_depsgraph_get()


def tri_count(objs):
    t = 0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        t += len(me.loop_triangles)
        o.evaluated_get(dg).to_mesh_clear()
    return t


SHADOW_NAMES = {p['renderer'] for p in shadow_proxies}
for p in shadow_proxies:
    p['triangles'] = tri_count([O[p['renderer']]])
    p['sourceTriangles'] = tri_count([O[p['source']]])
lod_json = dict(
    note='LODGroups built by the Setup: Exterior on the prefab root, Cockpit on the Cockpit object. Renderer names are '
         'unique in the prefab; <part>_LOD1 / _LOD2 are children of <part> (identity local transform). '
         'screenRelativeHeight = Unity LOD.screenRelativeTransitionHeight (fraction of the screen height). '
         'v10: shadowProxies - <part>_Shadow renderers (children of <part>, identity transform) listed in LOD0: '
         'ShadowCastingMode.ShadowsOnly; the <part> renderer itself: ShadowCastingMode.Off. triangles = drawn '
         'renderers only (proxies excluded).',
    groups=[dict(name=g, root='UtilityPlane' if g == 'Exterior' else 'Cockpit',
                 levels=[dict(screenRelativeHeight=LOD_HEIGHTS[g][i], renderers=sorted(levels[g][i]),
                              triangles=tri_count([O[n] for n in levels[g][i] if n not in SHADOW_NAMES]))
                         for i in range(3)])
            for g in ('Exterior', 'Cockpit')],
    shadowProxies=shadow_proxies)
json.dump(lod_json, open(os.path.join(DATA, 'lod.json'), 'w'), indent=1)
for g in lod_json['groups']:
    print('LOD', g['name'], [(l['screenRelativeHeight'], len(l['renderers']), l['triangles']) for l in g['levels']])
print('shadow proxies', [(p['renderer'], p['sourceTriangles'], p['triangles']) for p in shadow_proxies])
print('lod methods', LOD_METHOD)

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
for n in SURV:                                                  # v9 survival kit
    export(os.path.join(MOD, n + '.fbx'), [O[n]] + list(O[n].children_recursive))
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


def _build_from_parked(u):                        # inverse of _parked_world (Unity parked -> build frame)
    x, y, z = _rot_x((u[0], u[1] - _root_h, u[2]), _pitch)
    return Vector((-x, -z, y))


EYE_ABOVE_FEET = 1.65
lad_ground = _parked_world(SOCK['Socket_Ladder_Fuel_L'])
assert abs(lad_ground.y) < 1e-3, ('ladder socket not on the parked ground', lad_ground)
lad_ground.y = 0.0
eye = lad_ground + Vector((0.0, LAD['H'] + EYE_ABOVE_FEET, 0.0))
cap = _parked_world(SOCK['Socket_FuelCap_L'])
cap_pts = verts_w('FuelCap_L')
cap_top_b = sum(cap_pts, Vector()) / len(cap_pts)
cap_top_b.z = max(p.z for p in cap_pts)
le_w = _parked_world((LAD_SOCK[0], W_LE, wz(LAD_SOCK[0])))
# sight line from the eye to the filler cap against the airframe (Body), in the build frame
from mathutils.bvhtree import BVHTree
_dg = bpy.context.evaluated_depsgraph_get()
_bme = O['Body'].evaluated_get(_dg).to_mesh()
_bmw = O['Body'].matrix_world
_bvh = BVHTree.FromPolygons([_bmw @ v.co for v in _bme.vertices], [tuple(p.vertices) for p in _bme.polygons])
O['Body'].evaluated_get(_dg).to_mesh_clear()
eye_b = _build_from_parked(eye)


def _sight(target):
    d = target - eye_b
    hit = _bvh.ray_cast(eye_b, d.normalized(), d.length - 0.005)
    clear = min(_bvh.find_nearest(eye_b + d * (i / 200))[3] for i in range(1, 200)
                if (d * (1 - i / 200)).length > 0.12)
    return hit[0] is None, clear


vis_top, clear_top = _sight(cap_top_b)
vis_low, clear_low = _sight(Vector(SOCK['Socket_FuelCap_L']) + Vector((0, 0, 0.01)))   # 1 cm above the cap base
assert vis_top, ('filler cap hidden from the ladder platform', vis_top, vis_low)
hd = math.hypot(cap.x - eye.x, cap.z - eye.z)
facts['ladder'] = dict(
    note='SM_StepLadder at Socket_Ladder_Fuel_L/R (flat ground, same yaw as the plane, its +Z = the plane nose): '
         'outboard of the main wheel, platform centre ahead of the leading edge; player feet on the platform, '
         'eye 1.65 m above them (assumption, set your own). Distances from the eye at the platform centre.',
    platformHeight=LAD['H'], treadHeights=list(LAD['treads']), railTop=LAD['rail_top'],
    eyeHeight=round(eye.y, 3), fuelCapHeight=round(cap.y, 3), eyeToCap=round((cap - eye).length, 3),
    eyeAboveCap=round(eye.y - cap.y, 3), lookDownDeg=round(math.degrees(math.atan2(eye.y - cap.y, hd)), 1),
    lateralToCap=round(abs(cap.x - eye.x), 3), leadingEdgeHeight=round(le_w.y, 3),
    standOffLeadingEdge=round(lad_ground.z - le_w.z, 3),
    capTopVisible=bool(vis_top), capBaseVisible=bool(vis_low),
    sightLineClearanceOverWing=round(min(clear_top, clear_low), 3))
facts['propeller'] = dict(
    note='PropBlade_1..3 are children of Propeller, pivot on the hub centre; local Y (Unity) = blade span = pitch axis. '
         'Modelled at fine pitch (blade angle 28 deg at r = 0.76 m); feather: localRotation = rest * Euler(0, -62, 0) '
         '(blade angle 90 deg at r = 0.76 m), see the contract, section 3.',
    tipRadius=1.322, rpmMax=1900)
# v9 cargo bay facts
facts['paxSeats'] = dict(
    note='Folding troop seats (canvas laced to an aluminium tube frame). The model rests with every seat down; '
         'UtilityPlaneRig.paxSeatDown[i] (0 = folded up against the wall, the rig default) drives pan and leg.',
    seatHeightAboveFloor=round(S9['ZH'] + 0.002 - S9['FLOOR'], 3), panDepth=S9['DEPTH'], panWidth=round(2 * 0.205 + 0.022, 3),
    backCanvas=[round(S9['ZLB'] + 0.011 + 0.016 - S9['FLOOR'], 3), round(S9['ZU'] - 0.011 - 0.016 - S9['FLOOR'], 3)],
    aisleBetweenFacingPans=round(2 * (S9['XF'] - 0.011), 3),
    aisleBetweenFacingLegs=round(2 * min(abs((O[f'PaxSeat_{t}_Leg'].matrix_world @ v.co).x)
                                         for t in E9['seats'] for v in O[f'PaxSeat_{t}_Leg'].data.vertices), 3),
    foldedPanTopAboveFloor=round(S9['ZH'] + S9['DEPTH'] - S9['FLOOR'], 3),
    foldDeg=90.0)
lb = E9['ladder_stowed_box']
facts['ladderStowed'] = dict(
    note='Socket_Stow_Ladder: ladder root (pivot on the ground under the platform) with Ladder_RearLegs folded -38 deg '
         'about its local X, lying on its back on the right half of the bay floor, feet forward. It covers the '
         'floor under seats R1 and R2: they cannot be put down while the ladder is stowed (game rule).',
    boxMin=[min(a, b) for a, b in zip(to_unity(lb['min']), to_unity(lb['max']))],
    boxMax=[max(a, b) for a, b in zip(to_unity(lb['min']), to_unity(lb['max']))], blocksSeats=['PaxSeat_R1', 'PaxSeat_R2'])
_lmn, _lmx = Vector(lb['min']), Vector(lb['max'])
_ties = [k for k in SOCK if k.startswith('Socket_TieDown_')]
facts['ladderStowed']['ringsCovered'] = sorted(k for k in _ties if _lmn.x <= SOCK[k][0] <= _lmx.x and _lmn.y <= SOCK[k][1] <= _lmx.y)
facts['ladderStowed']['ringsForStraps'] = sorted({min(_ties, key=lambda k: (Vector(SOCK[k][:2]) - Vector(p_)).length)
                                                  for p_ in ((0.42, -0.80), (0.42, 0.50))})
print('ladder stowed rings', facts['ladderStowed']['ringsCovered'], facts['ladderStowed']['ringsForStraps'], flush=True)
json.dump(facts, open(os.path.join(DATA, 'model_facts.json'), 'w'), indent=1)

pax = dict(note='Unity prefab space, m. Pan pivot = hinge pin, leg pivot = front tube of the pan. Folding: pan '
                'localRotation = rest * Euler(0, 0, s * 90 * (1 - down)), leg = rest * Euler(0, 0, -s * 90 * (1 - down)), '
                's = +1 for L seats, -1 for R seats (UtilityPlaneRig does this). Sit only when down; seats face the cabin '
                'centre (the pelvis / eye sockets carry that rotation).',
           seats=[])
for i, (tag, sd) in enumerate(E9['seats'].items()):
    pax['seats'].append(dict(
        index=i, id=f'PaxSeat_{tag}', pan=f'PaxSeat_{tag}', leg=f'PaxSeat_{tag}_Leg', foldSign=sd['sgn'],
        side='left' if sd['sgn'] > 0 else 'right', position='ahead of the cargo doors' if sd['yc'] < 0 else 'behind the cargo doors',
        number=sd['digit'], pelvis=f'Socket_Seat_Pax{tag}', eye=f'Socket_PaxEye_{tag}', exit=f'Socket_PaxExit_{tag}',
        sitZone=f'PaxSeat_{tag}', foldZone=f'PaxSeatFold_{tag}',
        colliders=[f'COL_PaxSeat_{tag}', f'COL_PaxSeatLeg_{tag}', f'COL_PaxBack_{tag}'],
        hinge=to_unity(PIVOT[f'PaxSeat_{tag}']), blockedByLadder=sd['sgn'] < 0))
json.dump(pax, open(os.path.join(DATA, 'pax_seats.json'), 'w'), ensure_ascii=False, indent=1)

stow = dict(note='Stow points: put the item root on Socket_Stow_<id> (position and rotation; the socket rides on its '
                 'parent: the pilot doors move). Each has a trigger zone Stow_<id> (kind stow). Items are free physics '
                 'bodies elsewhere (the game decides); snapping them here works like a tie-down.', points=[])
ITEM_PREFAB = {'SM_Surv_Flashlight': 'Surv_Flashlight', 'SM_Surv_FlareGun': 'Surv_FlareGun', 'SM_Surv_Shovel': 'Surv_Shovel',
               'SM_Surv_Bag': 'Surv_Bag', 'SM_Kit_JerryCan': 'KitCarry_JerryCan (winter kit)', 'SM_StepLadder': 'StepLadder'}
for k, s in E9['stow'].items():
    mn, mx = STOW_BOX[k]
    e = dict(id=k, socket=f'Socket_Stow_{k}', zone=f'Stow_{k}', parent=s['parent'], item=s['item'],
             prefab=ITEM_PREFAB.get(s['item'], s['item']), size=ext_unity((mx - mn) / 1.0))
    if k == 'Ladder':
        e['note'] = 'fold Ladder_RearLegs (-38 deg about local X) first; show Stow_LadderStraps (UtilityPlaneRig.ladderStowed)'
    if k == 'SurvivalBag':
        e['note'] = 'under seat L1, against the wall; Surv_Bag_Strap (child of the bag) = the strap shown while secured'
    if k == 'JerryCan':
        e['size'] = [0.34, 0.476, 0.189]                            # the winter-kit can (zone = the bracket's inside)
        e['note'] = 'winter kit can (pivot at its bottom centre); the bungee of the bracket stays across'
    stow['points'].append(e)
json.dump(stow, open(os.path.join(DATA, 'stowage.json'), 'w'), ensure_ascii=False, indent=1)

horror = dict(note='Points for the game\'s horror and sound design. Unity prefab space (parked: the root is pitched '
                   'nose-up 9.98 deg, ground points sit on the parked ground). Scare sockets: +Z = where the figure '
                   'looks; Socket_Scare_Window_*: the face point 0.35 m outside the pane, looking in; the others: feet. '
                   'Audio sockets: emitters (identity rotation).',
              scare={}, audio={}, existingAudio=['Socket_Audio_Engine', 'Socket_Audio_Cabin', 'Socket_Audio_Gear_L',
                                                  'Socket_Audio_Gear_R', 'Socket_Audio_Tail', 'Socket_Thrust (propeller)',
                                                  'Socket_Exhaust_L/R', 'Socket_Handle_* (doors, knocks)'],
              alsoUseful=['Socket_Seat_Pax* (a figure sitting in a bay seat)', 'Socket_Seat_C (the right cockpit seat)'],
              fogPrints='UtilityPlaneRig.StampFogPrint(worldPoint, brush, sizeM, angleDeg, wipe, strength): a hand / '
                        'finger print on the fogged glass; StampFogStroke(a, b, width) writes; ClearFogPrints() cleans.')
SCARE_NOTE = {'Socket_Scare_Bay_Aft': 'bay floor at the rear bulkhead, facing the cockpit',
              'Socket_Scare_Bay_Fwd': 'bay floor right behind the cargo barrier, facing the crew',
              'Socket_Scare_Windshield': 'face point on the cowling in front of the windshield, looking at the crew',
              'Socket_Scare_Nose': 'ground 2.6 m ahead of the propeller',
              'Socket_Scare_Tail': 'ground behind the tail', 'Socket_Scare_Belly': 'ground under the fuselage (crawling)'}
for name, s in SOCK9_JSON.items():
    if name.startswith('Socket_Scare_'):
        note = SCARE_NOTE.get(name, 'face point outside the window, looking in' if '_Window_' in name else
                              'ground under the wing, facing the fuselage')
        horror['scare'][name] = dict(position=s['position_prefab'], forward=s['forward'], note=note)
AUD_NOTE = {'Socket_Audio_Radio': 'cabin speaker under the overhead console (radio voices)',
            'Socket_Audio_Headset_P': 'pilot headset hanging behind the seat (whispers)',
            'Socket_Audio_Headset_C': 'right headset hanging behind the seat',
            'Socket_Audio_StallHorn': 'stall warning horn, upper left corner of the windshield',
            'Socket_Audio_Bay': 'cargo bay (creaks, cargo shifting)', 'Socket_Audio_Roof': 'on top of the wing centre section (steps)',
            'Socket_Audio_Belly': 'under the cabin floor (knocks)', 'Socket_Audio_ELT': 'emergency locator transmitter in the tail cone',
            'Socket_Audio_Wind_L': 'left door seal (whistle)', 'Socket_Audio_Wind_R': 'right door seal (whistle)',
            'Socket_Audio_FuelTank_L': 'left wing tank (sloshing)', 'Socket_Audio_FuelTank_R': 'right wing tank (sloshing)'}
for k, s in E9['sockets'].items():
    if k.startswith('Socket_Audio_'):
        horror['audio'][k] = dict(position=to_unity(s['pos']), note=AUD_NOTE.get(k, ''))
json.dump(horror, open(os.path.join(DATA, 'horror.json'), 'w'), ensure_ascii=False, indent=1)
# v9 survival kit: one record per model (Unity units, item local space: pivot = grip, +Z forward, +Y up)
SURV_INFO = {'SM_Surv_Flashlight': ('Фонарь', 0.45, 'Flashlight'), 'SM_Surv_Flare': ('Фальшфейер', 0.30, None),
             'SM_Surv_FlareShell': ('Патрон к ракетнице, 26.5 мм', 0.05, None),
             'SM_Surv_FlareGun': ('Ракетница', 0.60, 'FlareGun'), 'SM_Surv_Shovel': ('Лопата', 1.50, 'Shovel'),
             'SM_Surv_Bag': ('Аварийная сумка', 6.0, 'SurvivalBag')}
kit = dict(note='Survival kit models -> Prefabs/Surv_<Name>.prefab. Item local space (Unity): pivot = the grip '
                '(the bag: its top handle), +Z = forward (light, muzzle, flame, blade), +Y = up. massKg is a '
                'TEMPORARY suggestion. sockets: working points in item space. stow: Data/stowage.json id.', items=[])
for n in SURV:
    ob = O[n]
    pts = [v.co for v in ob.data.vertices]
    mn = Vector([min(q[i] for q in pts) for i in range(3)])
    mx = Vector([max(q[i] for q in pts) for i in range(3)])
    lab, mass, stow_id = SURV_INFO[n]
    kit['items'].append(dict(model=n, prefab='Surv_' + n[len('SM_Surv_'):], label=lab, massKg=mass,
                             sizeM=ext_unity(mx - mn), boundsCenter=vec_unity((mn + mx) / 2),
                             sockets={c.name: vec_unity(c.matrix_world.translation - ob.matrix_world.translation)
                                      for c in ob.children if c.name.startswith('Socket_')},
                             colliders=sorted(c.name for c in ob.children if c.name.startswith('COL_')),
                             children=sorted(c.name for c in ob.children if not c.name.startswith(('COL_', 'Socket_'))),
                             stow=stow_id, castsShadows=n in ('SM_Surv_Bag', 'SM_Surv_Shovel')))
json.dump(kit, open(os.path.join(DATA, 'survival_kit.json'), 'w'), ensure_ascii=False, indent=1)
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


rend = [o for o in ROOT.children_recursive if o.type == 'MESH' and not o.name.startswith('COL_') and '_LOD' not in o.name
        and not o.name.endswith('_Shadow')]                    # v10: shadow proxies are not drawn
cp_objs = [o for o in rend if o.name in cp_rig or o.name.startswith(('Cockpit', 'Lamp_', 'Lens_Dome', 'Lens_Cargo',
                                                                        'Display_', 'Cabin_Fittings', 'PaxSeat_',
                                                                        'Stow_'))]
print('UNITY objects', len(ROOT.children_recursive), 'render tris', tri_count(rend), 'cockpit tris', tri_count(cp_objs),
      'colliders', sum(1 for o in ROOT.children_recursive if o.name.startswith('COL_')),
      'sockets', len(SOCK) + len(CHILD) + len(SOCK9_JSON), 'static colliders', len(cols.children))
