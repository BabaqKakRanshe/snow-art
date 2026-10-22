"""Preview renders of the PSX vehicle: day 3/4 front and rear, side with a 1.8 m figure, night (lit windows,
headlights), texel close-up, in-game 240-line frame.  python3 -I uaz_render.py <blend> <views> [spp]"""
import sys, os, math, random
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector
import psxlib as P

blend, views = sys.argv[1], sys.argv[2].split(',')
spp = int(sys.argv[3]) if len(sys.argv) > 3 else 48
OUT = os.path.join(P.HERE, 'rend', 'final')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
veh = [o for o in bpy.data.objects if o.type == 'MESH' and not o.get('scene_prop')]
veh_bb = [o for o in veh if not o.name.startswith(('Stove', 'StoveGlow'))]
lo, hi = P.world_bbox(veh_bb)
L, Wd, H = (hi - lo)
cx = (lo[0] + hi[0]) / 2
print('bbox', lo.round(3), hi.round(3))


def prop(o):
    o['scene_prop'] = 1
    return o


# snow ground (plane-preview style: light, matte) and dark spruces for the night
g = prop(P.ground(color=(0.80, 0.82, 0.86)))
trees = bpy.data.collections.new('Trees')
sc.collection.children.link(trees)
dark = bpy.data.materials.new('spruce')
dark.use_nodes = True
dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.035, 0.03, 1)
r = random.Random(4)
for i in range(60):
    a = r.uniform(0, 2 * math.pi)
    d = r.uniform(16, 55)
    x, y = cx + d * math.cos(a), d * math.sin(a)
    if abs(math.degrees(math.atan2(y, x - cx)) + 49) < 25:     # keep the night camera's view clear
        continue
    h = r.uniform(8, 15)
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=h * 0.22, depth=h, location=(x, y, h / 2))
    t = bpy.context.object
    t.data.materials.append(dark)
    for c in t.users_collection:
        c.objects.unlink(t)
    trees.objects.link(t)
    prop(t)
# human figure 1.8 m for the side view
hum_m = bpy.data.materials.new('human')
hum_m.use_nodes = True
hum_m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.08, 0.09, 0.11, 1)
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.2, depth=1.45, location=(hi[0] + 0.9, 0.8, 0.725))
body = prop(bpy.context.object)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.13, location=(hi[0] + 0.9, 0.8, 1.67))
head = prop(bpy.context.object)
for o in (body, head):
    o.data.materials.append(hum_m)

glass = [m for m in bpy.data.materials if m.name.startswith('M_PSX_Glass')]
for m in glass:                                             # PS1 glass: no sharp sun glint, a soft sheen only
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Roughness'].default_value = 0.5
    pb.inputs['Specular IOR Level'].default_value = 0.12
emit_mats = [m for m in bpy.data.materials if m.get('night_emit')]
night_lights = []


def add_light(name, kind, loc, energy, color, rot=None, size=0.1, spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == 'SPOT':
        ld.spot_size = math.radians(spot or 60)
        ld.spot_blend = 0.6
    ld.shadow_soft_size = size
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    night_lights.append(ob)
    return ob


# night: the kit's own lights (pendant lamp, stove, dash), headlights forward
marks = [o for o in bpy.data.objects if o.name.startswith('LIGHT_')]
for e in marks:
    add_light('L_' + e.name[6:], e['kind'], e.location.copy(), e['energy'], tuple(e['color']), size=0.06)
if not marks:
    add_light('L_saloon', 'POINT', (cx - 0.25 * L, 0, lo[2] + 0.70 * H), 30, (1.0, 0.62, 0.32), size=0.3)
for s in (1, -1):
    add_light(f'L_head{s}', 'SPOT', (hi[0] + 0.05, s * 0.55 * Wd / 2, 0.85), 700, (1.0, 0.92, 0.78),
              rot=(0, math.radians(95), 0), spot=55)


plan_light = bpy.data.objects.new('L_plan', bpy.data.lights.new('L_plan', 'AREA'))
sc.collection.objects.link(plan_light)
plan_light.data.shape = 'RECTANGLE'
plan_light.data.size, plan_light.data.size_y = 4.0, 1.7
plan_light.data.energy = 260
plan_light.data.color = (1.0, 0.93, 0.84)
plan_light.location = (0, 0, 1.86)


def state(view):
    plan_light.hide_render = view != 'plan'
    night = view in ('night', 'ingame', 'inside', 'cab', 'stove')
    for l in night_lights:
        l.hide_render = not night
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith(('Sun', 'Moon'))]:
        bpy.data.objects.remove(o, do_unlink=True)
    if night:
        P.world((0.013, 0.017, 0.033), 1.0)
        m = P.sun(0.20, (38, 0, -130), (0.6, 0.7, 1.0))
        m.name = 'Moon'
    else:
        P.world((0.56, 0.62, 0.72), 0.9)
        P.sun(3.4, (52, 0, 30))
    outside_night = view in ('night', 'ingame')
    for m in glass:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = (m.get('glow', 0.35) if outside_night else 0.0)
    for m in emit_mats:
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Emission Strength'].default_value = m['night_emit'] if night else m.get('day_emit', 0.0)
    trees.hide_render = not night
    body.hide_render = head.hide_render = view != 'side'


c = Vector((cx, 0, lo[2] + 0.42 * H))
CAMS = {
    'q34': ((cx + 1.30 * L, 0.95 * L, 0.36 * L), c, 32, None),
    'q34r': ((cx - 1.25 * L, -0.95 * L, 0.42 * L), c, 32, None),
    'side': ((cx, 16, lo[2] + 0.38 * H), Vector((cx + 0.25, 0, lo[2] + 0.38 * H)), 30, L * 1.62),
    'night': ((cx + 1.0 * L, -1.18 * L, 0.33 * L), Vector((cx - 0.05 * L, 0, lo[2] + 0.40 * H)), 28, None),
    'ingame': ((cx + 1.0 * L, -1.18 * L, 0.33 * L), Vector((cx - 0.05 * L, 0, lo[2] + 0.40 * H)), 28, None),
    'close': ((hi[0] + 0.55, 0.62 * Wd + 0.55, lo[2] + 0.55 * H), Vector((hi[0] - 0.55, 0.25 * Wd, lo[2] + 0.45 * H)), 30, None),
    'inside': ((-1.95, -0.30, 1.60), Vector((1.2, 0.25, 1.22)), 17, None),
    'cab': ((1.12, 0.46, 1.66), Vector((3.6, 0.30, 1.30)), 20, None),
    'insideday': ((-1.95, -0.30, 1.60), Vector((1.2, 0.25, 1.22)), 17, None),
    'stove': ((0.30, -0.55, 1.58), Vector((-1.95, 0.50, 1.02)), 19, None),
    'plan': ((0.0, 0.0, 3.0), Vector((0.0, 0.0001, 0.0)), 30, 4.75),
}
P.setup_cycles((900, 600), spp)
for v in views:
    state(v)
    loc, tgt, lens, ortho = CAMS[v]
    P.cam_look('cam_' + v, loc, tgt, lens, ortho)
    sc.render.resolution_x, sc.render.resolution_y = (427, 240) if v == 'ingame' else (900, 600)
    sc.cycles.samples = spp * (2 if v in ('inside', 'cab', 'insideday', 'stove') else 1)
    bpy.context.scene.camera.data.clip_start = 1.20 if v == 'plan' else 0.02
    if v == 'plan':
        sc.render.resolution_x, sc.render.resolution_y = 900, 450
    P.render(os.path.join(OUT, v + '.png'))
print('rendered', views)
