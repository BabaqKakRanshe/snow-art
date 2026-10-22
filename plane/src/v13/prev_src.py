"""Quick Cycles close-ups of the v13 source (fixtures, rails, door poses). python3 prev_src.py <blend> <outdir> [views]"""
import bpy, sys, math, json, os
from mathutils import Vector, Matrix, Euler

blend, outdir = sys.argv[-3], sys.argv[-2]
want = sys.argv[-1].split(',')
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
O = bpy.data.objects
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 900, 600
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
# world + sun
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
sun.data.energy = 3.5
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(35)))
sc.collection.objects.link(sun)
# ground
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.003))
gnd = bpy.context.active_object
gm = bpy.data.materials.new('G')
gm.diffuse_color = (0.35, 0.36, 0.38, 1)
gnd.data.materials.append(gm)
# lens preview materials: T_Lens x tint, point sampled
LT = '/home/claude/plane/v13/tex/T_Lens_BaseColor.png'
TINT = {'M_Light_Red': (0.35, 0.02, 0.01), 'M_Light_Green': (0.02, 0.3, 0.05), 'M_Light_White': (0.6, 0.6, 0.6),
        'M_Light_Beacon': (0.35, 0.03, 0.01), 'M_Light_Landing': (0.7, 0.7, 0.65)}
img = bpy.data.images.load(LT)
OLD = O.get('src_LightMounts') is None and O.get('Body') is None   # v12 source (before): keep its lens materials
if OLD:                                                              # ... but switched off, like the v13 lenses here
    for mn in TINT:
        for nd in bpy.data.materials[mn].node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0
for mn, t in (() if OLD else TINT.items()):
    m = bpy.data.materials[mn]
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = img
    tx.interpolation = 'Closest'
    mul = nt.nodes.new('ShaderNodeMix')
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    mul.inputs[7].default_value = (*t, 1)
    nt.links.new(tx.outputs['Color'], mul.inputs[6])
    nt.links.new(mul.outputs[2], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 0.25
    nt.links.new(pb.outputs[0], out.inputs[0])
for n in ('M_Airframe', 'M_Wing', 'M_Details', 'M_Floor', 'M_Interior'):
    for nd in bpy.data.materials[n].node_tree.nodes:
        if nd.type == 'TEX_IMAGE':
            nd.interpolation = 'Closest'

DJ = json.load(open('/home/claude/plane/out/doors_v13.json'))


def S3(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def S5(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (10 - 15 * x + 6 * x * x)


def door_mat(t, side):
    d = DJ['doors'][side]
    sg = 1 if side == 'L' else -1
    p = t / DJ['T_POP']
    of = DJ['D_OUT'] * S3(p / 0.75)
    orr = DJ['D_OUT'] * S3((p - 0.25) / 0.75)
    back = DJ['D_BACK'] * S5((t - DJ['T_SLIDE0']) / (1 - DJ['T_SLIDE0']))
    s = min(max((back - DJ.get('B_TUCK0', 9)) / (DJ['D_BACK'] - DJ.get('B_TUCK0', 9)), 0.0), 1.0)
    orr -= DJ.get('D_TUCK', 0.0) * s * s
    yaw = math.atan2(of - orr, d['length'])
    P = Vector(d['pivot'])
    return Matrix.Translation(P + Vector((sg * orr, back, 0))) @ Matrix.Rotation(sg * yaw, 4, 'Z') @ Matrix.Translation(-P)


BASE = {}
for side in ('L', 'R'):
    for n in (f'CargoDoor_{side}', f'CargoDoor_{side}__Glass'):
        BASE[n] = O[n].matrix_world.copy()


def pose_doors(t):
    for side in ('L', 'R'):
        M = door_mat(t, side)
        for n in (f'CargoDoor_{side}', f'CargoDoor_{side}__Glass'):
            O[n].matrix_world = M @ BASE[n]


cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
sc.collection.objects.link(cam)
sc.camera = cam


def look(eye, at, lens=50):
    cam.location = Vector(eye)
    d = (Vector(at) - Vector(eye)).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens


VIEWS = {
    'beacon_top': ((0.55, 3.85, 4.25), (0, 4.42, 3.94), 85),
    'beacon_bottom': ((0.55, 2.35, 0.55), (0, 1.65, 1.06), 70),
    'wingtip_L': ((7.75, -3.15, 3.05), (7.1, -2.25, 2.87), 70),
    'wingtip_R': ((-7.75, -3.15, 3.05), (-7.1, -2.25, 2.87), 70),
    'tail': ((0.45, 5.75, 2.42), (0, 5.07, 2.26), 85),
    'landing': ((2.75, -3.35, 2.75), (2.3, -2.55, 2.69), 85),
    'door_side': ((3.4, -0.2, 1.75), (0.75, 0.35, 1.75), 32),
    'door_rear': ((2.2, 3.2, 1.9), (0.75, 0.2, 1.75), 32),
    'door_front': ((2.6, -2.7, 1.5), (0.75, 0.0, 1.8), 30),
    'door_inside': ((-0.45, 0.75, 2.12), (0.72, -0.15, 1.72), 24),
}
# a fill light in the bay for the inside view (the preview world alone leaves the cabin black)
fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'POINT'))
fill.data.energy = 0.0
fill.location = (0.0, 0.3, 2.35)
sc.collection.objects.link(fill)
for name in want:
    if name.startswith('door'):
        fill.data.energy = 120.0 if name == 'door_inside' else 0.0
        for t in (0.0, 0.12, 0.25, 0.6, 1.0):
            pose_doors(t)
            eye, at, lens = VIEWS[name]
            look(eye, at, lens)
            sc.render.filepath = os.path.join(outdir, f'{name}_t{int(t * 100):03d}.png')
            bpy.ops.render.render(write_still=True)
        pose_doors(0.0)
    else:
        eye, at, lens = VIEWS[name]
        look(eye, at, lens)
        sc.render.filepath = os.path.join(outdir, f'{name}.png')
        bpy.ops.render.render(write_still=True)
print('done')
