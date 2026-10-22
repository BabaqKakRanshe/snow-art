"""Independent look at the Unity package data: imports Models/Van.fbx back (Blender's FBX importer, default axes) and
draws the data of Assets/Van/Data in it, converted from van space: collider boxes (colliders.json, on their parent
nodes), lamp arrows (lights.json), sockets (sockets.json), part pivots with their rotation axes (parts.json) and the
seats' eye points. Blender (X, Y, Z) of the imported model = (-Ux, -Uz, Uy) of van space.
python3 -I unity_frame_check.py -- <Van.fbx> <Data dir> <out dir>"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index('--') + 1:]
FBX, DATA, OUT = a
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
O = bpy.data.objects
J = lambda n: json.load(open(os.path.join(DATA, n)))


def B(u):
    return Vector((-u[0], -u[2], u[1]))


def mat(name, rgba, emit=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


M_COL = mat('col', (1.0, 0.25, 0.1, 0.35))
M_LIGHT = mat('light', (1.0, 0.9, 0.2, 1.0))
M_SOCK = mat('sock', (0.1, 0.8, 1.0, 1.0))
M_AXIS = mat('axis', (0.3, 1.0, 0.3, 1.0))
M_SEAT = mat('seat', (1.0, 0.2, 1.0, 1.0))
coll = bpy.data.collections.new('overlay')
bpy.context.scene.collection.children.link(coll)


def box(name, cvan, size, m):
    me = bpy.data.meshes.new(name)
    sx, sy, sz = size[0], size[2], size[1]               # van (x, y, z) sizes -> Blender (x, y, z) = (Ux, Uz, Uy)
    vs = [Vector((dx * sx / 2, dy * sy / 2, dz * sz / 2)) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(vs, [], fs)
    o = bpy.data.objects.new(name, me)
    o.location = B(cvan)
    o.data.materials.append(m)
    coll.objects.link(o)
    o.display_type = 'WIRE'
    return o


def arrow(name, p, d, length, m, r=0.006):
    p, d = B(p), B(d).normalized()
    me = bpy.data.meshes.new(name)
    q = d.to_track_quat('Z', 'Y')
    n = 6
    vs = []
    for k in range(n):
        ang = 2 * math.pi * k / n
        off = Vector((math.cos(ang) * r, math.sin(ang) * r, 0))
        vs.append(p + q @ off)
        vs.append(p + q @ off + d * length)
    vs.append(p + d * (length + 3 * r))
    fs = [(2 * k, 2 * ((k + 1) % n), 2 * ((k + 1) % n) + 1, 2 * k + 1) for k in range(n)]
    fs += [(2 * k + 1, 2 * ((k + 1) % n) + 1, 2 * n) for k in range(n)]
    me.from_pydata(vs, [], fs)
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(m)
    coll.objects.link(o)
    return o


def dot(name, p, m, r=0.012):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=B(p))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(m)
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)


origin = {o.name: o.matrix_world.translation.copy() for o in O if o.type in ('MESH', 'EMPTY')}
bad = []
for c in J('colliders.json')['colliders']:
    # center is parent-local: parent origin (imported) + center (van axes)
    po = origin[c['parent']]
    cw = po + Vector((-c['center'][0], -c['center'][2], c['center'][1]))
    if (cw - B(c['centerVan'])).length > 1e-3:
        bad.append(f'{c["name"]}: centre != centerVan ({(cw - B(c["centerVan"])).length:.4f})')
    box('C_' + c['name'], c['centerVan'], c['size'], M_COL)
for l in J('lights.json')['lights']:
    po = origin.get(l['parent'], Vector()) if l['parent'] else Vector()
    pw = po + Vector((-l['positionLocal'][0], -l['positionLocal'][2], l['positionLocal'][1]))
    if (pw - B(l['position'])).length > 1e-3:
        bad.append(f'light {l["name"]}: local != van ({(pw - B(l["position"])).length:.4f})')
    arrow('L_' + l['name'], l['position'], l['forward'], 0.35 if l['unityLight'] == 'Spot' else 0.12, M_LIGHT)
for s in J('sockets.json')['sockets']:
    po = origin.get(s['parent'], Vector()) if s['parent'] else Vector()
    pw = po + Vector((-s['positionLocal'][0], -s['positionLocal'][2], s['positionLocal'][1]))
    if (pw - B(s['position'])).length > 1e-3:
        bad.append(f'socket {s["name"]}: local != van')
    dot('S_' + s['name'], s['position'], M_SOCK, 0.01)
for p in J('parts.json')['parts']:
    o = O.get(p['name'])
    if o is None:
        bad.append(f'part {p["name"]} missing in the FBX')
        continue
    if (o.matrix_world.translation - B(p['pivot'])).length > 1e-3:
        bad.append(f'part {p["name"]}: pivot {tuple(round(c, 4) for c in o.matrix_world.translation)} != {tuple(round(c, 4) for c in B(p["pivot"]))}')
    if p['kind'] in ('hinge', 'twist') and p['hasAxis']:
        arrow('A_' + p['name'], p['pivot'], p['rotAxis'], 0.08, M_AXIS, 0.003)
for s in J('seats.json')['seats']:
    dot('E_' + s['name'], s['eye'], M_SEAT, 0.03)
    arrow('F_' + s['name'], s['eye'], s['facing'], 0.25, M_SEAT, 0.005)
print('CHECK problems', len(bad))
for b in bad[:30]:
    print('  ', b)

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'MATERIAL'
sh.show_xray = False
sc.render.resolution_x, sc.render.resolution_y = 1200, 800
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam


def shot(name, eye, look, lens=35, hide_model=False, xray=False):
    cam.location = Vector(eye)
    cam.rotation_euler = (Vector(look) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    for o in O:
        if o.type == 'MESH' and o.name not in coll.objects:
            o.hide_render = hide_model
    sh.show_xray = xray
    sh.xray_alpha = 0.35
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)


# Blender frame of the import: forward = -Y, left = +X, up = +Z
shot('q34_front_left', (4.8, -6.0, 3.2), (0, 0, 1.1), 35)
shot('q34_rear_right', (-4.5, 6.2, 3.4), (0, 0, 1.1), 35)
shot('xray_side', (7.5, 0.0, 1.4), (0, 0, 1.2), 40, xray=True)
shot('xray_top', (0.0, 0.0, 9.0), (0, -0.001, 0), 40, xray=True)
print('renders in', OUT)
