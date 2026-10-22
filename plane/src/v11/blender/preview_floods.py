import bpy, sys, json, math
sys.path.insert(0, '/home/claude/plane/v11/blender')
from mathutils import Vector
import panel_flood_geo as PF
a = json.loads(sys.argv[sys.argv.index('--') + 1])
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/v11/deliv/UtilityPlane_Unity_v11/Blender/UtilityPlane_v11_lights.blend')
sc = bpy.context.scene
ob = PF.make_panel_floods('CP_PanelFloods', bpy.data.materials['M_Cockpit'], bpy.data.materials['M_Light_Cabin'], (0.3354, 0.0478, 0.004))
lm = bpy.data.materials['M_Light_Cabin'].copy(); lm.name = 'M_LensFX_Flood_preview'
p = [n for n in lm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
p.inputs['Emission Color'].default_value = (1.0, 0.05, 0.02, 1.0); p.inputs['Emission Strength'].default_value = float(a.get('lens', 40.0))
lm.cycles.emission_sampling = 'NONE'
ob.data.materials[1] = lm
root = bpy.data.objects['UtilityPlane']
bpy.data.objects['Cockpit'].users_collection[0].objects.link(ob)
ob.parent = root; ob.matrix_parent_inverse.identity(); ob.matrix_basis.identity()
cam = bpy.data.objects.new('Cam_flood', bpy.data.cameras.new('Cam_flood')); sc.collection.objects.link(cam); sc.camera = cam
def u2b(v): return Vector((-v[0], -v[2], v[1]))
pos, look = u2b(a['pos']), u2b(a['look'])
cam.location = pos; cam.rotation_euler = (look - pos).to_track_quat('-Z', 'Y').to_euler()
cam.data.sensor_fit = 'VERTICAL'; cam.data.angle_y = math.radians(a.get('fov', 50)); cam.data.clip_start = 0.01
sc['atmosphere'] = 0.05
sc['lf_time_offset'] = 0.6 - 1 / 24
sc.frame_set(1)
sc.cycles.samples = int(a.get('samples', 64))
sc.render.resolution_x, sc.render.resolution_y = int(a.get('w', 760)), int(a.get('h', 428)); sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.render.image_settings.color_management = 'OVERRIDE'; sc.render.image_settings.linear_colorspace_settings.name = 'Linear Rec.709'
sc.render.filepath = a['out']
bpy.ops.render.render(write_still=True)
print('RENDERED', a['out'], 'tris', len(ob.data.polygons))
