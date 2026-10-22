"""Pose the UE skeletons in Blender (UE frame: cm, nose +X, left +Y, up +Z) and render to validate pivots/axes.
Blender->UE rotation mapping: UE Roll = +Rx(Blender), UE Pitch = -Ry(Blender), UE Yaw = -Rz(Blender)."""
import bpy, sys, os, math
from mathutils import Vector, Euler
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

prefix = sys.argv[1]
views = sys.argv[2].split(',')
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 24
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_ue.blend'))
sc = bpy.context.scene
O = bpy.data.objects
D = math.radians

POSE_EXT = {   # bone: (rot_euler_deg XYZ in Blender bone space, location cm)
    'CargoDoor': ((0, 0, 100), None), 'PilotDoor_L': ((0, 0, -65), None),
    'Rudder': ((0, 0, 20), None), 'Elevator_L': ((0, 20, 0), None), 'Elevator_R': ((0, 20, 0), None),
    'Aileron_L': ((0, 18, 0), None), 'Aileron_R': ((0, -18, 0), None),
    'Flap_L': ((0, -25, 0), None), 'Flap_R': ((0, -25, 0), None),
    'Gear_L': ((10, 0, 0), None), 'Gear_R': ((-4, 0, 0), None), 'TailGear': ((0, 6, 0), None),
    'TailWheel_Fork': ((0, 0, 25), None), 'Propeller': ((25, 0, 0), None),
}
POSE_CP = {
    'Yoke_P': ((0, 0, 0), (-6, 0, 0)), 'Yoke_P_Roll': ((30, 0, 0), None),
    'Yoke_C': ((0, 0, 0), (-6, 0, 0)), 'Yoke_C_Roll': ((30, 0, 0), None),
    'Needle_ASI': ((1.6 * 95, 0, 0), None), 'Needle_ALT100': ((0.36 * 450, 0, 0), None),
    'Needle_ALT1000': ((0.036 * 3450, 0, 0), None), 'Needle_VSI': ((0.0825 * 500, 0, 0), None),
    'ATT_Roll': ((-20, 0, 0), None), 'ATT_Pitch': ((0, 0, 0), (0, 0, -0.3)), 'HDG_Card': ((-45, 0, 0), None),
    'TC_Plane': ((20, 0, 0), None), 'TC_Ball': ((-6, 0, 0), None),
    'Needle_TRQ': ((0.1125 * 1500, 0, 0), None), 'Needle_ITT': ((0.27 * 620, 0, 0), None),
    'Needle_NG': ((2.4545 * 92, 0, 0), None), 'Needle_PROP': ((0.1125 * 1850, 0, 0), None),
    'Needle_FF': ((0.675 * 280, 0, 0), None), 'Needle_OILP': ((0.6 * 95, 0, 0), None),
    'Needle_OILT': ((-0.8 * 75, 0, 0), None), 'Needle_FUELL': ((2.0 * 40, 0, 0), None),
    'Needle_FUELR': ((2.0 * 38, 0, 0), None), 'Clock_Hour': ((30 * 10.2, 0, 0), None),
    'Clock_Min': ((6 * 12, 0, 0), None), 'Needle_AMP': ((1.5 * 20, 0, 0), None),
    'Lever_Power': ((0, 20, 0), None), 'Lever_Condition': ((0, 15, 0), None), 'Lever_Flap': ((0, -24, 0), None),
    'PedalP_L': ((0, 12, 0), None), 'PedalP_R': ((0, -12, 0), None),
    'SW_Battery': ((0, -40, 0), None), 'SW_Avionics': ((0, -40, 0), None), 'SW_NavLights': ((0, -40, 0), None),
    'SW_Beacon': ((0, -40, 0), None),
}


def apply_pose(arm_name, table):
    arm = O[arm_name]
    for b, (rot, loc) in table.items():
        pb = arm.pose.bones[b]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler([D(a) for a in rot], 'XYZ')
        if loc:
            pb.location = Vector(loc)


apply_pose('root', POSE_EXT)
apply_pose('root_cockpit', POSE_CP)

# ---- materials (blockout)
img = bpy.data.images.load(os.path.join(HERE, 'tex', 'v2', 'T_Gauges_BC.png'), check_existing=True)
for m in bpy.data.materials:
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    if 'Glass' in m.name:
        tr, gl, mx = nt.nodes.new('ShaderNodeBsdfTransparent'), nt.nodes.new('ShaderNodeBsdfGlossy'), nt.nodes.new('ShaderNodeMixShader')
        gl.inputs['Roughness'].default_value = 0.03
        mx.inputs[0].default_value = 0.08 if m.name == 'src_Glass' else 0.03
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
        continue
    if m.name.startswith('M_Light'):
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = m.diffuse_color
        em.inputs['Strength'].default_value = 8
        nt.links.new(em.outputs[0], out.inputs[0])
        continue
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    p.inputs['Roughness'].default_value = 0.55
    if m.name == 'src_CP_Gauges':
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = img
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    else:
        p.inputs['Base Color'].default_value = m.diffuse_color
    if 'Metal' in m.name:
        p.inputs['Metallic'].default_value = 0.8
    nt.links.new(p.outputs[0], out.inputs[0])

sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = samples
sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Medium High Contrast'
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = Euler((D(50), 0, D(-130)), 'XYZ')
sc.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=300000, location=(0, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new('g')
gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.10, 0.12, 0.07, 1)
g.data.materials.append(gm)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.clip_start = 2
cam.data.clip_end = 100000
eye = Vector((-LY.PILOT_EYE[1] * 100, LY.PILOT_EYE[0] * 100, LY.PILOT_EYE[2] * 100))   # build -> UE frame
VIEWS = {
    'ext': ((780, 1150, 520), (0, 50, 150), 35, (1400, 900)),
    'tail': ((-1050, 700, 480), (-420, 0, 220), 35, (1000, 700)),
    'panel': (tuple(eye), tuple(eye + Vector((80, -12, -45))), 75, (1280, 720)),
}
for v in views:
    loc, tgt, fov, res = VIEWS[v]
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.angle = D(fov)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = f'{prefix}_{v}.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', v)
