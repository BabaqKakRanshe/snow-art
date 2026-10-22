"""First-person renders from the pilot eye point. usage: python3 render_eye.py <blend> <prefix> <views> <samples>"""
import bpy, sys, os, math
from mathutils import Vector, Euler
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

blend, prefix = sys.argv[1], sys.argv[2]
views = sys.argv[3].split(',')
samples = int(sys.argv[4]) if len(sys.argv) > 4 else 48
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = float(os.environ.get('EV', '0'))      # eye adaptation for interior views

# ---- blockout materials (KEEPMAT=1 keeps the final textured materials)
for m in ([] if os.environ.get('KEEPMAT') else bpy.data.materials):
    m.use_nodes = True
    nt = m.node_tree
    if m.name.startswith('src_') and 'BAKE_TARGET' in nt.nodes and 'image' not in m.keys():
        pass
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    if 'Glass' in m.name:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        gl = nt.nodes.new('ShaderNodeBsdfGlossy')
        gl.inputs['Roughness'].default_value = 0.03
        mx = nt.nodes.new('ShaderNodeMixShader')
        mx.inputs[0].default_value = 0.08 if m.name == 'src_Glass' else 0.03
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(gl.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
        continue
    if m.name.startswith('M_Light'):
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = m.diffuse_color
        em.inputs['Strength'].default_value = 6
        nt.links.new(em.outputs[0], out.inputs[0])
        continue
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    p.inputs['Roughness'].default_value = 0.55
    if 'image' in m.keys():
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(os.path.join(HERE, 'tex', 'v2', m['image']), check_existing=True)
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
        p.inputs['Roughness'].default_value = 0.6
    else:
        p.inputs['Base Color'].default_value = m.diffuse_color
    if 'Metal' in m.name:
        p.inputs['Metallic'].default_value = 0.8
        p.inputs['Roughness'].default_value = 0.4
    nt.links.new(p.outputs[0], out.inputs[0])

for ob in bpy.data.objects:
    if any(ob.name.startswith(h) for h in os.environ.get('HIDE', '').split(',') if h):
        ob.hide_render = True

# ---- world: sky + sun
w = bpy.data.worlds.new('Sky')
sc.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
o = nt.nodes.new('ShaderNodeOutputWorld')
try:
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    try:
        sky.sun_elevation = math.radians(38)
        sky.sun_rotation = math.radians(140)
    except Exception:
        pass
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.35
except Exception:
    bg.inputs[0].default_value = (0.5, 0.65, 0.9, 1)
nt.links.new(bg.outputs[0], o.inputs[0])
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 4.0
sun.data.angle = math.radians(1.0)
sun.rotation_euler = Euler((math.radians(52), 0, math.radians(140)), 'XYZ')
sc.collection.objects.link(sun)

# ---- ground + runway
bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
gnd = bpy.context.active_object
gm = bpy.data.materials.new('ground')
gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.09, 0.12, 0.05, 1)
gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
gnd.data.materials.append(gm)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -250, 0.005))
rw = bpy.context.active_object
rw.scale = (18, 520, 1)
rm = bpy.data.materials.new('runway')
rm.use_nodes = True
rm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.16, 0.14, 0.11, 1)
rw.data.materials.append(rm)

# ---- camera at the pilot eye. yaw: + = look left (towards +X). pitch: + = up
cam = bpy.data.objects.new('eye', bpy.data.cameras.new('eye'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.sensor_fit = 'HORIZONTAL'
cam.data.angle = math.radians(75)
cam.data.clip_start = 0.02
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
VIEWS = {'fwd': (0, -6), 'panel': (0, -30), 'panelL': (22, -30), 'panelC': (-18, -32), 'yoke': (8, -45), 'left': (75, -8), 'right': (-50, -10), 'up': (-20, 40),
         'back': (150, -15), 'seat': (-100, -35), 'pedestal': (-25, -50), 'annun': (-2, -28), 'lpanel': (18, -35)}
eye = Vector(LY.PILOT_EYE)
for v in views:
    yaw, pitch = VIEWS[v]
    y, p = math.radians(yaw), math.radians(pitch)
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    cam.location = eye
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f'{prefix}_{v}.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', v)
