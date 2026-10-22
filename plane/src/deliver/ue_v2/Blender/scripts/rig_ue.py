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

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'plane_v2.blend')
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
    'Flap_L': 'Body', 'Flap_R': 'Body', 'CargoDoor': 'Body', 'PilotDoor_L': 'Body', 'PilotDoor_R': 'Body',
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
fus.active_material_index = [m.name for m in fus.data.materials].index('src_CabinWall')
bpy.ops.object.material_slot_select()
bpy.ops.mesh.separate(type='SELECTED')
bpy.ops.object.mode_set(mode='OBJECT')
shell = [o for o in bpy.context.selected_objects if o != fus][0]
shell.name = 'CP_CabinShell'

cockpit_names = set(o.name for o in bpy.data.collections['Cockpit'].objects) | {'CP_CabinShell'}
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
        b = eb.new(s)
        b.head, b.tail, b.roll = Vector(p), Vector(p) + Vector((0, 5.0, 0)), 0.0
        b.parent = top
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
arm_ext, sk_ext = build('SK_UtilityPlane', 'root', ext_objs, 'Body', ext_moving, ext_sockets, HINGE_TILT,
                        lambda o: o.name if o.name in EXT_MOVING else 'Body')
# cockpit
cp_moving = {}
for bone, info in CPR['rig'].items():
    cp_moving[bone] = ((RZ @ Vector(info['pivot']).to_4d()).to_3d(), info['parent'])
arm_cp, sk_cp = build('SK_UtilityPlane_Cockpit', 'root_cockpit', cp_objs, 'Cockpit', cp_moving, {}, {},
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
