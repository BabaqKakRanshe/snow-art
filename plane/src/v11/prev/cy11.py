"""v11 lighting previews, step 1 (Blender): the parked plane on snow at night, one camera, render passes only
(albedo, gloss colour, normal, emission; lighting is computed afterwards exactly like URP by urp_emulate.py) and a
dump of the scene triangles for Embree (visibility, shadows).
python3 cy11.py <config.json>
config: {"out": prefix, "cam": {"pos": [ux,uy,uz], "look": [...], "fov": vertical deg}, "W": 1600, "H": 900,
         "lens": {"Lens_Nav_L": [r,g,b, strength], ...}, "gauges": [r,g,b,strength], "figures": [[ux,uz,yaw], ...]}
All positions in the Unity world frame of the parked plane (UtilityPlaneRig.ParkedPose at the origin, heading +Z)."""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Matrix, Vector

cfg = json.load(open(sys.argv[1]))
TEX = '/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Textures'
bpy.ops.wm.open_mainfile(filepath=cfg.get('scene', '/home/claude/plane/out/plane_unity_v10.blend'))
for im in bpy.data.images:                                   # v10 package textures (PSX exterior, 1024 interior)
    if im.source == 'FILE' and im.filepath:
        p = os.path.join(TEX, os.path.basename(bpy.path.abspath(im.filepath)))
        if os.path.exists(p):
            im.filepath = p
            im.reload()
for mn in ('M_Airframe', 'M_Wing', 'M_Details'):             # PSX: point sampled, no normal map
    m = bpy.data.materials.get(mn)
    if m is None:
        continue
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE':
            n.interpolation = 'Closest'
        if n.type == 'NORMAL_MAP':
            n.inputs['Strength'].default_value = 0.0

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 1
sc.cycles.use_denoising = False
sc.cycles.filter_width = 0.01                                # pass samples at pixel centres (= the Embree rays)
sc.cycles.max_bounces = 0
sc.render.resolution_x, sc.render.resolution_y = cfg['W'], cfg['H']
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
vl = sc.view_layers[0]
vl.use_pass_diffuse_color = True
vl.use_pass_glossy_color = True
vl.use_pass_normal = True
vl.use_pass_emit = True
vl.use_pass_z = True

# unit conversion: Unity (x, y, z) = (-xb, zb, -yb)
M = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])
def u2b(v):
    return Vector((M.T @ np.asarray(v, float)).tolist())

# parked pose (UtilityPlaneRig.ParkedPose): Unity Euler(-9.98, 0, 0) about the origin, root at y = -0.372
ph = math.radians(-9.98)
Ru = np.array([[1, 0, 0], [0, math.cos(ph), -math.sin(ph)], [0, math.sin(ph), math.cos(ph)]])
Rb = M.T @ Ru @ M
park = Matrix.Translation(u2b((0, -0.372, 0))) @ Matrix([list(Rb[0]) + [0], list(Rb[1]) + [0], list(Rb[2]) + [0], [0, 0, 0, 1]])
root = bpy.data.objects['UtilityPlane']
root.matrix_world = park @ root.matrix_world

HIDE_PRE = ('COL_', 'IV_', 'SM_', 'src_', 'PropBlur', 'PropDisc', 'Ladder', 'Stow_LadderStraps')
for ob in bpy.data.objects:
    n = ob.name
    if n.startswith(HIDE_PRE) or n.endswith(('_LOD1', '_LOD2', '_Shadow')) or n.endswith('_Glass') or n.endswith('_Fog') or \
            n in ('Glass', 'Glass_Fog') or ob.display_type in ('WIRE', 'BOUNDS'):
        ob.hide_render = True

# snow ground (subtle variation), at world z = 0 (Unity y = 0)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
g = bpy.context.active_object
g.name = 'Ground'
gm = bpy.data.materials.new('snow'); gm.use_nodes = True
N, L = gm.node_tree.nodes, gm.node_tree.links
pr = N['Principled BSDF']
nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; nz.inputs['Detail'].default_value = 3
ramp = N.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.66, 0.69, 0.72, 1); ramp.color_ramp.elements[1].color = (0.80, 0.82, 0.84, 1)
L.new(nz.outputs['Fac'], ramp.inputs[0]); L.new(ramp.outputs[0], pr.inputs['Base Color'])
pr.inputs['Roughness'].default_value = 0.85
g.data.materials.append(gm)

# figures: simple dark standing people (for shadows in the landing light / beam occlusion)
fm = bpy.data.materials.new('figure'); fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.055, 1)
fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
for i, (fx, fz, yaw) in enumerate(cfg.get('figures', [])):
    base = u2b((fx, 0.0, fz))
    parts = [('body', (0.0, 0.0, 1.05), (0.21, 0.15, 0.42)), ('head', (0.0, 0.0, 1.62), (0.11, 0.12, 0.13)),
             ('legL', (0.1, 0.0, 0.42), (0.09, 0.09, 0.43)), ('legR', (-0.1, 0.0, 0.42), (0.09, 0.09, 0.43)),
             ('armL', (0.27, 0.0, 1.08), (0.06, 0.06, 0.36)), ('armR', (-0.27, 0.0, 1.08), (0.06, 0.06, 0.36))]
    for nm, off, sc3 in parts:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0,
                                             location=(base.x + off[0], base.y + off[1], base.z + off[2]))
        o = bpy.context.active_object
        o.name = 'Figure%d_%s' % (i, nm)
        o.scale = sc3
        o.data.materials.append(fm)

# emission at unit strength, white; urp_emulate.py scales it per material index (IndexMA) for each variant
LENS = ['Lens_Nav_L', 'Lens_Nav_R', 'Lens_Nav_Tail', 'Lens_Strobe_L', 'Lens_Strobe_R', 'Lens_Beacon_Top', 'Lens_Beacon_Bottom',
        'Lens_Landing', 'Lens_Dome', 'Lens_CargoLight', 'Lens_Flood_L', 'Lens_Flood_R']
for i, lname in enumerate(LENS):
    ob = bpy.data.objects.get(lname)
    if ob is None:
        continue
    src = ob.material_slots[0].material
    m = src.copy(); m.name = src.name + '_' + lname
    ob.material_slots[0].link = 'OBJECT'
    ob.material_slots[0].material = m
    m.pass_index = 1 + i
    p = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    p.inputs['Emission Color'].default_value = (1, 1, 1, 1)
    p.inputs['Emission Strength'].default_value = 1.0
for mn, idx in (('M_Gauges', 20), ('M_RadioDisplay', 21), ('M_Annunciator', 22), ('M_Screen', 23)):
    m = bpy.data.materials.get(mn)
    if m is None:
        continue
    m.pass_index = idx
    p = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    p.inputs['Emission Strength'].default_value = 1.0
    if not p.inputs['Emission Color'].is_linked:
        p.inputs['Emission Color'].default_value = (1, 1, 1, 1)
vl.use_pass_material_index = True

# camera
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
c = cfg['cam']
pos, look = u2b(c['pos']), u2b(c['look'])
cam.location = pos
cam.rotation_euler = (look - pos).to_track_quat('-Z', 'Y').to_euler()
cam.data.sensor_fit = 'VERTICAL'
cam.data.angle_y = math.radians(c['fov'])
cam.data.clip_start = 0.02
cam.data.clip_end = 1000
bpy.context.view_layer.update()

sc.render.image_settings.media_type = 'MULTI_LAYER_IMAGE'
sc.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
sc.render.image_settings.color_depth = '32'
sc.render.filepath = cfg['out'] + '_passes.exr'
bpy.ops.render.render(write_still=True)

# scene dump for Embree (Unity world frame): visible triangles + shadow caster flag + glass flag
NO_SHADOW = ('Needle_', 'Knob_', 'SW_', 'Guard_', 'Rheo_', 'Pull_', 'Btn_', 'Lamp_', 'Lens_', 'Display_', 'ATT_', 'HDG_',
             'TC_', 'Clock_', 'ALT_', 'Compass_', 'Belt_', 'Lock_', 'PropBlur', 'PropDisc', 'Glass')
dg = bpy.context.evaluated_depsgraph_get()
V, T, CAST, OBJ, names = [], [], [], [], []
off = 0
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.hide_render:
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    if len(me.loop_triangles) == 0:
        ev.to_mesh_clear(); continue
    mw = np.array(ev.matrix_world)
    v = np.array([vv.co for vv in me.vertices]) @ mw[:3, :3].T + mw[:3, 3]
    t = np.array([lt.vertices[:] for lt in me.loop_triangles])
    mats = [s.material.name if s.material else '' for s in ob.material_slots]
    glass = np.array([('Glass' in mats[lt.material_index]) if lt.material_index < len(mats) else False for lt in me.loop_triangles])
    keep = ~glass
    t = t[keep]
    V.append(v @ M.T)                                   # -> Unity frame
    T.append(t + off)
    off += len(v)
    cast = not ob.name.startswith(NO_SHADOW) and not ob.name.endswith('_Glass')
    CAST.append(np.full(len(t), cast))
    OBJ.append(np.full(len(t), len(names)))
    names.append(ob.name)
    ev.to_mesh_clear()
cm = np.array(cam.matrix_world)
np.savez_compressed(cfg['out'] + '_scene.npz', V=np.concatenate(V).astype(np.float32), T=np.concatenate(T).astype(np.int32),
                    cast=np.concatenate(CAST), obj=np.concatenate(OBJ), names=np.array(names),
                    cam_pos=np.asarray(c['pos'], float), cam_rot_b=cm[:3, :3], fov=c['fov'], W=cfg['W'], H=cfg['H'])
print('dumped', off, 'verts', sum(len(t) for t in T), 'tris', flush=True)
