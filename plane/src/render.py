"""Render preview views of a blend. usage: python3 render.py file.blend outprefix [views] [samples] [simple]"""
import bpy, sys, os, math
from mathutils import Vector

blend, prefix = sys.argv[1], sys.argv[2]
views = sys.argv[3].split(',') if len(sys.argv) > 3 else ['hero']
samples = int(sys.argv[4]) if len(sys.argv) > 4 else 32
simple = len(sys.argv) > 5 and sys.argv[5] == 'simple'
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = samples
sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
sc.cycles.max_bounces = 4
sc.render.film_transparent = False
sc.render.image_settings.color_depth = '8'
sc.cycles.adaptive_threshold = 0.02
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = os.environ.get('LOOK', 'AgX - Medium High Contrast')

if simple:
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        if 'Glass' in m.name:
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            gl = nt.nodes.new('ShaderNodeBsdfGlossy')
            gl.inputs['Roughness'].default_value = 0.02
            mx = nt.nodes.new('ShaderNodeMixShader')
            mx.inputs[0].default_value = 0.12
            nt.links.new(tr.outputs[0], mx.inputs[1])
            nt.links.new(gl.outputs[0], mx.inputs[2])
            nt.links.new(mx.outputs[0], out.inputs[0])
            continue
        if m.name.startswith('M_Light') or m.name.startswith('GaugeLight'):
            em = nt.nodes.new('ShaderNodeEmission')
            em.inputs['Color'].default_value = m.diffuse_color
            em.inputs['Strength'].default_value = 8
            nt.links.new(em.outputs[0], out.inputs[0])
            continue
        p = nt.nodes.new('ShaderNodeBsdfPrincipled')
        p.inputs['Base Color'].default_value = m.diffuse_color
        p.inputs['Roughness'].default_value = 0.6
        nt.links.new(p.outputs[0], out.inputs[0])

# hide helper-only objects (+ HIDE=prefix,prefix)
for ob in bpy.data.objects:
    if ob.name.startswith('HIDE_') or any(ob.name.startswith(h) for h in os.environ.get('HIDE', '').split(',') if h):
        ob.hide_render = True

# world
w = bpy.data.worlds.new('W') if not sc.world else sc.world
sc.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes.get('Background') or nt.nodes.new('ShaderNodeBackground')
bg.inputs[0].default_value = (0.045, 0.045, 0.05, 1)
bg.inputs[1].default_value = 1.0
if not nt.nodes.get('World Output'):
    o = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], o.inputs[0])

# floor (shadow catcher-ish dark floor)
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new('floor')
fm.use_nodes = True
fp = fm.node_tree.nodes['Principled BSDF']
fp.inputs['Base Color'].default_value = (0.03, 0.03, 0.032, 1)
fp.inputs['Roughness'].default_value = 0.5
floor.data.materials.append(fm)


def light(name, loc, energy, size, rot_target=(0, 0, 1.5), kind='AREA', color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'AREA':
        ld.size = size
    lo = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(lo)
    lo.location = loc
    d = Vector(rot_target) - Vector(loc)
    lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return lo


if os.environ.get('SKY'):
    nt.nodes.clear()
    bg = nt.nodes.new('ShaderNodeBackground')
    wo = nt.nodes.new('ShaderNodeOutputWorld')
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    try:
        sky.sun_elevation = math.radians(34)
        sky.sun_rotation = math.radians(215)
    except Exception:
        pass
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.3
    nt.links.new(bg.outputs[0], wo.inputs[0])
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = float(os.environ.get('SUN', '4.0'))
    sun.data.angle = math.radians(1.0)
    sun.rotation_euler = (math.radians(56), 0, math.radians(215))
    sc.collection.objects.link(sun)
    fp.inputs['Base Color'].default_value = (0.11, 0.105, 0.095, 1)
    fp.inputs['Roughness'].default_value = 0.9
else:
    light('key', (10, -12, 14), 9000, 8)
    light('fill', (-14, -4, 6), 2500, 10, color=(0.8, 0.85, 1.0))
    light('rim', (-4, 14, 8), 6000, 6, color=(1.0, 0.9, 0.8))
    light('top', (0, 0, 16), 3000, 14)

cam_d = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cam_d)
sc.collection.objects.link(cam)
sc.camera = cam

RES_SCALE = float(os.environ.get('RES', '1.0'))
VIEWS = {
    #        location              target            ortho_scale / lens   res
    'hero': ((11.5, -10.5, 4.6), (0.0, -0.4, 1.55), ('persp', 38), (1500, 900)),
    'front': ((0, -30, 1.9), (0, 0, 1.9), ('ortho', 15.5), (1000, 500)),
    'rear': ((0, 30, 1.9), (0, 0, 1.9), ('ortho', 15.5), (1000, 500)),
    'left': ((30, 0, 1.9), (0, 0, 1.9), ('ortho', 11.5), (1000, 500)),
    'right': ((-30, 0, 1.9), (0, 0, 1.9), ('ortho', 11.5), (1000, 500)),
    'top': ((0, 0.0, 30), (0, 0.0, 0), ('ortho', 15.0), (1000, 800)),
    'bottom': ((0, 0.0, -30), (0, 0.0, 0), ('ortho', 15.0), (1000, 800)),
    'cargo': ((4.2, -2.6, 2.2), (0.3, -0.2, 1.55), ('persp', 30), (800, 700)),
    'cargoR': ((-4.2, -2.6, 2.2), (-0.3, -0.2, 1.55), ('persp', 30), (800, 700)),
    'capL': ((2.6, -3.3, 3.6), (1.55, -2.02, 2.72), ('persp', 30), (800, 600)),
    'engine': ((2.6, -7.0, 2.4), (0.0, -4.4, 1.7), ('persp', 35), (800, 700)),
    'gear': ((3.2, -4.6, 0.8), (1.25, -2.85, 0.5), ('persp', 35), (800, 700)),
    'rear34': ((-9.5, 9.0, 4.0), (0, 0.8, 1.6), ('persp', 38), (1500, 900)),
    'cockpitL': ((3.6, -5.2, 2.9), (0.4, -2.6, 2.0), ('persp', 35), (1000, 700)),
    'wingtop': ((5.6, -4.6, 3.9), (4.2, -1.9, 2.75), ('persp', 32), (1000, 700)),
    'tailc': ((2.8, 7.6, 3.4), (0.0, 4.3, 2.55), ('persp', 35), (1000, 700)),
    'under': ((3.2, -4.8, 0.55), (2.6, -1.4, 2.4), ('persp', 30), (1000, 700)),
}
for v in views:
    loc, tgt, (kind, val), res = VIEWS[v]
    cam.location = loc
    d = Vector(tgt) - Vector(loc)
    up = 'Y'
    if v in ('top', 'bottom'):
        cam.rotation_euler = (0, 0, 0) if v == 'top' else (math.pi, 0, 0)
        cam.rotation_euler[2] = math.pi if v == 'top' else 0.0
    else:
        cam.rotation_euler = d.to_track_quat('-Z', up).to_euler()
    if kind == 'ortho':
        cam_d.type = 'ORTHO'
        cam_d.ortho_scale = val
    else:
        cam_d.type = 'PERSP'
        cam_d.lens = val
    floor.hide_render = v in ('top', 'bottom')
    if v == 'bottom' and not bpy.data.objects.get('under'):
        light('under', (0, 0, -14), 9000, 16, rot_target=(0, 0, 2))
    sc.render.resolution_x, sc.render.resolution_y = int(res[0] * RES_SCALE), int(res[1] * RES_SCALE)
    sc.render.filepath = f'{prefix}_{v}.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', v)
