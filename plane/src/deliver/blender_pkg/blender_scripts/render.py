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
sc.view_settings.look = 'AgX - Medium High Contrast'

if simple:
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        if m.name == 'M_Lights':
            em = nt.nodes.new('ShaderNodeEmission')
            em.inputs['Color'].default_value = m.diffuse_color
            em.inputs['Strength'].default_value = 8
            nt.links.new(em.outputs[0], out.inputs[0])
            continue
        p = nt.nodes.new('ShaderNodeBsdfPrincipled')
        p.inputs['Base Color'].default_value = m.diffuse_color
        p.inputs['Roughness'].default_value = 0.6
        nt.links.new(p.outputs[0], out.inputs[0])

# hide helper-only objects
for ob in bpy.data.objects:
    if ob.name.startswith('HIDE_'):
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


light('key', (10, -12, 14), 9000, 8)
light('fill', (-14, -4, 6), 2500, 10, color=(0.8, 0.85, 1.0))
light('rim', (-4, 14, 8), 6000, 6, color=(1.0, 0.9, 0.8))
light('top', (0, 0, 16), 3000, 14)

cam_d = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cam_d)
sc.collection.objects.link(cam)
sc.camera = cam

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
    'engine': ((2.6, -7.0, 2.4), (0.0, -4.4, 1.7), ('persp', 35), (800, 700)),
    'gear': ((3.2, -4.6, 0.8), (1.25, -2.85, 0.5), ('persp', 35), (800, 700)),
    'rear34': ((-9.5, 9.0, 4.0), (0, 0.8, 1.6), ('persp', 38), (1500, 900)),
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
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = f'{prefix}_{v}.png'
    bpy.ops.render.render(write_still=True)
    print('rendered', v)
