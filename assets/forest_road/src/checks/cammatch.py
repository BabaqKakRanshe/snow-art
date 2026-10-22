"""render the U3 terrain from a viewpoint with markers at prefab pivots; overlay on the preview.
python3 -I cammatch.py -- Viewpoint out.png [extra.blend]"""
import bpy, sys, math, json
from mathutils import Vector, Quaternion, Matrix
a = sys.argv[sys.argv.index('--') + 1:]
vpn, out = a[0], a[1]
extra = a[2] if len(a) > 2 else None
L = json.load(open('/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Data/Forest_Layout.json'))
bpy.ops.wm.open_mainfile(filepath='/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend')
sc = bpy.context.scene
def U(p):
    return Vector((-p[0], -p[2], p[1]))
vp = next(v for v in L['viewpoints'] if v['name'] == vpn)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = U(vp['p'])
cam.rotation_euler = (U(vp['target']) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.sensor_fit = 'VERTICAL'
cam.data.angle_y = math.radians(vp['fov'])
cam.data.clip_end = 2000
sc.render.resolution_x, sc.render.resolution_y = 1281, 720
COL = {'M_ForestTerrain': (0.18, 0.22, 0.14), 'M_RoadDirt': (0.40, 0.34, 0.26), 'M_TrailSoil': (0.35, 0.28, 0.2), 'M_Asphalt': (0.2, 0.2, 0.2), 'M_Concrete': (0.5, 0.5, 0.5)}
for m in bpy.data.materials:
    m.use_nodes = True
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Base Color'].default_value = (*COL.get(m.name, (0.5, 0.2, 0.5)), 1)
        b.inputs['Roughness'].default_value = 1.0
mk = bpy.data.materials.new('mk'); mk.use_nodes = True
bb = mk.node_tree.nodes['Principled BSDF']; bb.inputs['Base Color'].default_value = (1, 0.1, 0.05, 1); bb.inputs['Emission Color'].default_value = (1, 0.1, 0.05, 1); bb.inputs['Emission Strength'].default_value = 2
mx = bpy.data.materials.new('mx'); mx.use_nodes = True
bx = mx.node_tree.nodes['Principled BSDF']; bx.inputs['Base Color'].default_value = (0.1, 0.4, 1, 1); bx.inputs['Emission Color'].default_value = (0.1, 0.4, 1, 1); bx.inputs['Emission Strength'].default_value = 2
import bmesh
def bar(name, p0, p1, r, mat):
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    bm = bmesh.new()
    d = p1 - p0
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    bm.to_mesh(me); me.materials.append(mat)
for p in L['prefabs']:
    P = U(p['p'])
    if (P - cam.location).length > 80:
        continue
    q = p['q']   # unity quaternion (x,y,z,w) -> blender: rotation about blender z by -yaw... use matrix approach
    qu = Quaternion((q[3], q[0], q[1], q[2]))
    # unity local axes in unity world
    ex = qu @ Vector((1, 0, 0)); ez = qu @ Vector((0, 0, 1))
    EX = Vector((-ex.x, -ex.z, ex.y)); EZ = Vector((-ez.x, -ez.z, ez.y))
    bar('pv_' + p['m'], P, P + Vector((0, 0, 3)), 0.08, mk)
    bar('px_' + p['m'], P + Vector((0, 0, 0.3)), P + Vector((0, 0, 0.3)) + EX * 2.0, 0.05, mk)
    bar('pz_' + p['m'], P + Vector((0, 0, 0.3)), P + Vector((0, 0, 0.3)) + EZ * 2.0, 0.05, mx)
    print('marker', p['m'], [round(v, 2) for v in P], 'unity +x ->', [round(v, 2) for v in EX], 'unity +z ->', [round(v, 2) for v in EZ])
for r in L['rocks']:
    P = U(r['p'])
    if (P - cam.location).length < 60 and r['m'] == 'EuroPost':
        bar('ep', P, P + Vector((0, 0, 1.0)), 0.06, mx)
if extra:
    with bpy.data.libraries.load(extra) as (src, dst):
        dst.objects = src.objects
    for o in dst.objects:
        if o is not None:
            sc.collection.objects.link(o)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.5, 0.55, 0.65, 1)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3
sun.rotation_euler = (math.radians(40), 0, math.radians(200)); sc.collection.objects.link(sun)
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
