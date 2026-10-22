"""Build UE5 rigid skeletal meshes from out/plane_v2.blend and export FBX.
 - scene rotated so the nose points +X (UE forward), up +Z, left = +Y in Blender (-> UE -Y, UE's left)
 - every bone has identity rest orientation (bone axes == component axes: X fwd, Y lateral, Z up),
   except ailerons/flaps whose local Y follows the hinge line (2 deg dihedral)
 - every mesh part is weighted 100 % to one bone; static parts -> Body / Cockpit
 - sockets are zero-weight bones
Outputs: export/ue/SK_UtilityPlane.fbx, export/ue/SK_UtilityPlane_Cockpit.fbx, out/plane_ue.blend, export/ue/rig.json"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'plane_v2_final_final2.blend')
OUT = os.path.join(HERE, 'export', 'ue')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
CPR = json.load(open(os.path.join(HERE, 'out', 'cockpit_rig.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'light_pos.json')))
RZ = Matrix.Scale(100.0, 4) @ Matrix.Rotation(math.radians(90), 4, 'Z')   # build frame (m, nose -Y) -> UE (cm, nose +X)
us = bpy.context.scene.unit_settings
us.system, us.scale_length, us.length_unit = 'METRIC', 0.01, 'CENTIMETERS'
DIH = math.radians(2.0)


def to_ue(p):
    return (RZ @ Vector(p).to_4d()).to_3d() if len(p) == 3 else None


# ------------------------------------------------------------------ bone tables
EXT_MOVING = {  # bone: parent
    'Propeller': 'Body', 'Gear_L': 'Body', 'Gear_R': 'Body', 'Wheel_L': 'Gear_L', 'Wheel_R': 'Gear_R',
    'TailGear': 'Body', 'TailWheel_Fork': 'TailGear', 'TailWheel': 'TailWheel_Fork',
    'Rudder': 'Body', 'Elevator_L': 'Body', 'Elevator_R': 'Body', 'Aileron_L': 'Body', 'Aileron_R': 'Body',
    'Flap_L': 'Body', 'Flap_R': 'Body', 'CargoDoor_L': 'Body', 'CargoDoor_R': 'Body', 'PilotDoor_L': 'Body',
    'PilotDoor_R': 'Body', 'FuelCap_L': 'Body', 'FuelCap_R': 'Body',
}
HINGE_TILT = {'Aileron_L': +1, 'Flap_L': +1, 'Aileron_R': -1, 'Flap_R': -1}
EXT_SOCKETS = {   # build-frame positions
    'Socket_PilotEye': LY.PILOT_EYE, 'Socket_CopilotEye': LY.COPILOT_EYE,
    'Socket_WheelContact_L': (1.25, -2.85, 0.48), 'Socket_WheelContact_R': (-1.25, -2.85, 0.48),
    'Socket_WheelContact_Tail': (0.0, 2.06, 0.285),
    'Socket_Exhaust_L': (0.78, -3.80, 1.56), 'Socket_Exhaust_R': (-0.78, -3.80, 1.56),
    'Socket_PropWash': (0.0, -4.74, 0.0), 'Socket_CenterOfMass': (0.0, -1.95, 1.75),
    'Socket_Audio_Engine': (0.0, -4.0, 1.55), 'Socket_Audio_Cabin': (0.0, -2.2, 1.9),
    'Socket_Audio_Gear_L': (0.46, -2.85, 1.03), 'Socket_Audio_Gear_R': (-0.46, -2.85, 1.03),
    'Socket_Audio_Tail': (0.0, 1.55, 1.10), 'Socket_Cam_Chase': (0.0, 14.0, 4.5),
}
for k, v in LIGHTS.items():
    EXT_SOCKETS['Socket_' + k] = tuple(v)

W_LE, W_CH, W_Z0 = -2.55, 2.10, 2.648
wz = lambda x: W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)


def verts_w(name):
    ob = O[name]
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def top_centroid(name, band=0.02):
    pts = verts_w(name)
    zmax = max(p.z for p in pts)
    sel = [p for p in pts if p.z > zmax - band]
    return tuple(sum((p for p in sel), Vector()) / len(sel))


def fuel_cap(sgn):
    """filler neck = centre of the closed cap, at its underside (the cap is FuelCap_L/R)"""
    pts = verts_w('FuelCap_' + ('L' if sgn > 0 else 'R'))
    return (sgn * 1.55, W_LE + 0.25 * W_CH, min(p.z for p in pts))


# game-integration sockets (VEHICLE_SYSTEM_AI_SPEC: SEAT-02, VIEW-01, PHYS-02.3, SYS-02, O-02)
for sg, s_ in ((1, 'L'), (-1, 'R')):
    EXT_SOCKETS[f'Socket_Exit_{s_}'] = (sg * 1.20, -2.05, 0.0)             # ground, between wheel and strut
    EXT_SOCKETS[f'Socket_Exit_Cargo_{s_}'] = (sg * 1.35, -0.20, 0.0)       # ground, in front of the cargo opening
    EXT_SOCKETS[f'Socket_FuelCap_{s_}'] = fuel_cap(sg)
    EXT_SOCKETS[f'Socket_Aero_Wing_{s_}_In'] = (sg * 2.0, W_LE + 0.25 * W_CH, wz(2.0) + 0.06)
    EXT_SOCKETS[f'Socket_Aero_Wing_{s_}_Out'] = (sg * 5.2, W_LE + 0.25 * W_CH, wz(5.2) + 0.06)
    EXT_SOCKETS[f'Socket_Aero_HStab_{s_}'] = (sg * 1.2, 4.24, 2.06)
EXT_SOCKETS['Socket_Seat_P'] = (0.33, -2.20, 1.43)
EXT_SOCKETS['Socket_Seat_C'] = (-0.33, -2.20, 1.43)
EXT_SOCKETS['Socket_Aero_Fin'] = (0.0, 4.25, 3.0)
EXT_SOCKETS['Socket_Aero_Fuselage'] = (0.0, -1.0, 1.75)
EXT_SOCKETS['Socket_Thrust'] = LY.PROP_C
_cl = verts_w('CP_CargoLight')
EXT_SOCKETS['Socket_Light_Cargo'] = (0.0, LY.CARGO_LIGHT_Y, min(p.z for p in _cl) - 0.01)
k = 0
for yy in (-1.70, -1.00, -0.30, 0.40, 1.10):                                # TEMPORARY test tie-downs (O-02)
    for xx in (0.50, 0.0, -0.50):
        k += 1
        EXT_SOCKETS[f'Socket_TieDown_{k:02d}'] = (xx, yy, LY.FLOOR_Z + 0.005)
# sockets that ride on a moving part: name -> (build-frame pos, parent bone)
EXT_CHILD_SOCKETS = {
    'Socket_Handle_PilotDoor_L_Out': ((0.775, -2.32, 1.70), 'PilotDoor_L'),
    'Socket_Handle_PilotDoor_L_In': ((0.675, -2.30, 1.74), 'PilotDoor_L'),
    'Socket_Handle_PilotDoor_R_Out': ((-0.775, -2.32, 1.70), 'PilotDoor_R'),
    'Socket_Handle_PilotDoor_R_In': ((-0.675, -2.30, 1.74), 'PilotDoor_R'),
    'Socket_Handle_CargoDoor_L_Out': ((0.775, -0.70, 1.75), 'CargoDoor_L'),
    'Socket_Handle_CargoDoor_L_In': ((0.675, -0.70, 1.72), 'CargoDoor_L'),
    'Socket_Handle_CargoDoor_R_Out': ((-0.775, -0.70, 1.75), 'CargoDoor_R'),
    'Socket_Handle_CargoDoor_R_In': ((-0.675, -0.70, 1.72), 'CargoDoor_R'),
}
CP_CHILD_SOCKETS = {
    'Socket_Hand_Yoke_L': ((0.484, -2.76, 1.76), 'Yoke_P_Roll'),
    'Socket_Hand_Yoke_R': ((0.176, -2.76, 1.76), 'Yoke_P_Roll'),
    'Socket_Hand_Throttle': (top_centroid('Lever_Power'), 'Lever_Power'),
    'Socket_Foot_L': (top_centroid('PedalP_L', 0.06), 'PedalP_L'),
    'Socket_Foot_R': (top_centroid('PedalP_R', 0.06), 'PedalP_R'),
    'Socket_Light_Dome_L': ((0.085, -2.29, 2.55), 'Cockpit'),
    'Socket_Light_Dome_R': ((-0.085, -2.29, 2.55), 'Cockpit'),
    'Socket_Light_Flood': ((0.0, -2.97, 2.00), 'Cockpit'),
    'Socket_Belt_P': ((0.33, -2.325, 1.465), 'Cockpit'),        # buckle position when fastened
    'Socket_Belt_C': ((-0.33, -2.325, 1.465), 'Cockpit'),
}

# ------------------------------------------------------------------ flatten transforms into the UE frame
bpy.context.view_layer.update()
pivots = {}
for ob in O:
    if ob.type == 'MESH':
        pivots[ob.name] = ob.matrix_world.translation.copy()
for ob in list(O):
    if ob.type != 'MESH':
        continue
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.data.transform(RZ @ mw)
    ob.matrix_world = Matrix.Identity(4)
for ob in list(O):
    if ob.type == 'EMPTY':
        bpy.data.objects.remove(ob)

# split the fuselage inner skin (cabin wall) into the cockpit group
fus = O['src_Fuselage']
bpy.ops.object.select_all(action='DESELECT')
fus.select_set(True)
bpy.context.view_layer.objects.active = fus
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
_fm = [m.name for m in fus.data.materials]
fus.active_material_index = _fm.index('M_Cockpit' if 'M_Cockpit' in _fm else 'src_CabinWall')
bpy.ops.object.material_slot_select()
bpy.ops.mesh.separate(type='SELECTED')
bpy.ops.object.mode_set(mode='OBJECT')
shell = [o for o in bpy.context.selected_objects if o != fus][0]
shell.name = 'CP_CabinShell'

cockpit_names = set(o.name for o in bpy.data.collections['Cockpit'].objects) | {'CP_CabinShell'}

# ---- interaction volumes (UE component space, cm): box per interactive part, relative to its bone
INTERACT = {  # object/bone: (kind, label_ru)
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
}
EXT_INTERACT = {  # socket-based handles: (bone, half extent cm, kind, label)
    'Socket_Handle_PilotDoor_L_Out': ('PilotDoor_L', (4, 8, 4), 'door', 'Дверь пилота'),
    'Socket_Handle_PilotDoor_L_In': ('PilotDoor_L', (4, 8, 4), 'door', 'Дверь пилота'),
    'Socket_Handle_PilotDoor_R_Out': ('PilotDoor_R', (4, 8, 4), 'door', 'Правая дверь'),
    'Socket_Handle_PilotDoor_R_In': ('PilotDoor_R', (4, 8, 4), 'door', 'Правая дверь'),
    'Socket_Handle_CargoDoor_L_Out': ('CargoDoor_L', (4, 10, 5), 'door', 'Грузовая дверь, левая'),
    'Socket_Handle_CargoDoor_L_In': ('CargoDoor_L', (4, 8, 4), 'door', 'Грузовая дверь, левая'),
    'Socket_Handle_CargoDoor_R_Out': ('CargoDoor_R', (4, 10, 5), 'door', 'Грузовая дверь, правая'),
    'Socket_Handle_CargoDoor_R_In': ('CargoDoor_R', (4, 8, 4), 'door', 'Грузовая дверь, правая'),
    'Socket_FuelCap_L': ('FuelCap_L', (6, 6, 4), 'cap', 'Крышка левого бака'),
    'Socket_FuelCap_R': ('FuelCap_R', (6, 6, 4), 'cap', 'Крышка правого бака'),
    'Socket_Belt_P': ('Cockpit', (9, 12, 7), 'toggle', 'Ремни пилота'),
    'Socket_Belt_C': ('Cockpit', (9, 12, 7), 'toggle', 'Ремни пассажира'),
}
MIN_HALF = 1.5
volumes = {}
for name, (kind, label) in INTERACT.items():
    ob = O[name]
    pts = [v.co for v in ob.data.vertices]          # meshes are already in the rotated UE frame (cm, +Y = left)
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    c, h = (mn + mx) / 2, (mx - mn) / 2
    head = (RZ @ pivots[name].to_4d()).to_3d()
    rel = c - head
    volumes[name] = dict(mesh='SK_UtilityPlane_Cockpit', bone=name, kind=kind, label=label,
                         center_cm=[round(rel.x, 2), round(-rel.y, 2), round(rel.z, 2)],
                         half_extent_cm=[round(max(MIN_HALF, h[i]), 2) for i in range(3)])
for sock, (bone, he, kind, label) in EXT_INTERACT.items():
    allsock = {**{k: v[0] for k, v in EXT_CHILD_SOCKETS.items()}, **{k: v[0] for k, v in CP_CHILD_SOCKETS.items()},
               **EXT_SOCKETS}
    p = allsock[sock]
    pu = (RZ @ Vector(p).to_4d()).to_3d()
    head = Vector((0, 0, 0)) if bone in ('Body', 'Cockpit') else (RZ @ pivots[bone].to_4d()).to_3d()
    rel = pu - head
    volumes[sock] = dict(mesh='SK_UtilityPlane_Cockpit' if bone == 'Cockpit' else 'SK_UtilityPlane', bone=bone,
                         kind=kind, label=label,
                         center_cm=[round(rel.x, 2), round(-rel.y, 2), round(rel.z, 2)], half_extent_cm=list(he))
json.dump(volumes, open(os.path.join(OUT, 'interaction_volumes.json'), 'w'), ensure_ascii=False, indent=1)

# ---- cargo cases: not part of the airframe (CARGO-01) -> separate static meshes, pivot at the bottom centre
cases = sorted(o for o in (x.name for x in O if x.type == 'MESH') if o.startswith('src_Case'))
layout = {}
for i, cn in enumerate(cases, 1):
    ob = O[cn]
    pts = [v.co for v in ob.data.vertices]
    mn = Vector((min(p[k] for p in pts) for k in range(3)))
    mx = Vector((max(p[k] for p in pts) for k in range(3)))
    bc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    ob.data.transform(Matrix.Translation(-bc))
    sm = f'SM_Cargo_Case{i}'
    ob.name = ob.data.name = sm
    layout[sm] = dict(location_cm=[round(bc.x, 1), round(-bc.y, 1), round(bc.z, 1)],
                      size_cm=[round(mx.x - mn.x, 1), round(mx.y - mn.y, 1), round(mx.z - mn.z, 1)],
                      note='placement as on the concept art (inside the cargo bay), component space of SK_UtilityPlane')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(OUT, sm + '.fbx'), use_selection=True, object_types={'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Z', axis_up='Y', bake_space_transform=False, use_mesh_modifiers=False,
        mesh_smooth_type='FACE', use_triangles=True, use_tspace=False, path_mode='STRIP', embed_textures=False)
    bpy.data.objects.remove(ob)
json.dump(layout, open(os.path.join(OUT, 'cargo_layout.json'), 'w'), indent=1)

ext_objs = [o for o in O if o.type == 'MESH' and o.name not in cockpit_names]
cp_objs = [o for o in O if o.type == 'MESH' and o.name in cockpit_names]


def triangulate(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(ob.data)
    bm.free()


def weight_all(ob, bone):
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')


def build(name, arm_name, objs, top_bone, moving, sockets, hinge_tilt, obj_to_bone):
    arm_data = bpy.data.armatures.new(arm_name)
    arm = bpy.data.objects.new(arm_name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    L = 10.0
    top = eb.new(top_bone)
    top.head, top.tail, top.roll = (0, 0, 0), (0, 50.0, 0), 0.0
    made = {top_bone: top}
    for bone, (piv, parent) in moving.items():
        b = eb.new(bone)
        h = Vector(piv)
        if bone in hinge_tilt:
            d = Vector((0, math.cos(DIH), hinge_tilt[bone] * math.sin(DIH)))
        else:
            d = Vector((0, 1, 0))
        b.head, b.tail, b.roll = h, h + d * L, 0.0
        made[bone] = b
    for bone, (piv, parent) in moving.items():
        made[bone].parent = made[parent]
        made[bone].use_connect = False
    for s, p in sockets.items():
        par = top_bone
        if isinstance(p, tuple) and len(p) == 2 and isinstance(p[1], str):
            p, par = p
        b = eb.new(s)
        b.head, b.tail, b.roll = Vector(p), Vector(p) + Vector((0, 5.0, 0)), 0.0
        b.parent = made[par]
        b.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        triangulate(o)
        weight_all(o, obj_to_bone(o))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    mesh.name = name
    mesh.data.name = name
    # drop unused material slots
    used = sorted(set(p.material_index for p in mesh.data.polygons))
    keep = [mesh.data.materials[i] for i in used]
    remap = {old: new for new, old in enumerate(used)}
    idx = [remap[p.material_index] for p in mesh.data.polygons]
    mesh.data.materials.clear()
    for m in keep:
        mesh.data.materials.append(m)
    for p, i in zip(mesh.data.polygons, idx):
        p.material_index = i
    mesh.parent = arm
    md = mesh.modifiers.new('Armature', 'ARMATURE')
    md.object = arm
    return arm, mesh


# exterior
ext_moving = {}
for bone, parent in EXT_MOVING.items():
    ext_moving[bone] = ((RZ @ pivots[bone].to_4d()).to_3d(), parent)
ext_sockets = {k: (RZ @ Vector(v).to_4d()).to_3d() for k, v in EXT_SOCKETS.items()}
ext_sockets.update({k: ((RZ @ Vector(p).to_4d()).to_3d(), par) for k, (p, par) in EXT_CHILD_SOCKETS.items()})
arm_ext, sk_ext = build('SK_UtilityPlane', 'root', ext_objs, 'Body', ext_moving, ext_sockets, HINGE_TILT,
                        lambda o: o.name.split('__')[0] if o.name.split('__')[0] in EXT_MOVING else 'Body')
# cockpit
cp_moving = {}
for bone, info in CPR['rig'].items():
    cp_moving[bone] = ((RZ @ Vector(info['pivot']).to_4d()).to_3d(), info['parent'])
cp_sockets = {k: ((RZ @ Vector(p).to_4d()).to_3d(), par) for k, (p, par) in CP_CHILD_SOCKETS.items()}
arm_cp, sk_cp = build('SK_UtilityPlane_Cockpit', 'root_cockpit', cp_objs, 'Cockpit', cp_moving, cp_sockets, {},
                      lambda o: o.name if o.name in CPR['rig'] else 'Cockpit')


def report(arm):
    out = {}
    for b in arm.data.bones:
        m = b.matrix_local
        out[b.name] = dict(head=[round(v, 4) for v in b.head_local],
                           parent=b.parent.name if b.parent else None,
                           rot_identity=all(abs(m.to_3x3()[i][j] - (1.0 if i == j else 0.0)) < 1e-5
                                            for i in range(3) for j in range(3)),
                           deform=b.use_deform)
    return out


rig = {'exterior': report(arm_ext), 'cockpit': report(arm_cp)}
json.dump(rig, open(os.path.join(OUT, 'rig.json'), 'w'), indent=1)
for n, sk in (('exterior', sk_ext), ('cockpit', sk_cp)):
    print(n, 'tris', len(sk.data.polygons), 'bones', len(rig[n]), 'materials', [m.name for m in sk.data.materials])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_ue.blend'))


def export(arm, mesh, path):
    old = arm.name
    other = [o for o in O if o.type == 'ARMATURE' and o != arm and o.name == 'root']
    for o in other:
        o.name = 'root_tmp'
    arm.name = 'root'                       # UE reads the armature object as the root bone
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    mesh.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Z', axis_up='Y', bake_space_transform=False,
        use_mesh_modifiers=False, mesh_smooth_type='FACE', use_triangles=True, use_tspace=False,
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', armature_nodetype='NULL',
        use_armature_deform_only=False, bake_anim=False, path_mode='STRIP', embed_textures=False)
    arm.name = old
    for o in other:
        o.name = 'root'


export(arm_ext, sk_ext, os.path.join(OUT, 'SK_UtilityPlane.fbx'))
export(arm_cp, sk_cp, os.path.join(OUT, 'SK_UtilityPlane_Cockpit.fbx'))
print('exported')
