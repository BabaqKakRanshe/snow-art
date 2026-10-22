"""out/plane_v9_final_v11.blend = the v10 export source + CP_PanelFloods (panel flood lamp housings and lenses)."""
import bpy, sys
sys.path.insert(0, '/home/claude/plane/v11/blender')
import panel_flood_geo as PF
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v10.blend')
ob = PF.make_panel_floods('CP_PanelFloods', bpy.data.materials['M_Cockpit'], bpy.data.materials['M_Light_Cabin'],
                          (0.3354, 0.0478, 0.004))
bpy.data.collections['Cockpit'].objects.link(ob)
print('CP_PanelFloods faces', len(ob.data.polygons), 'verts', len(ob.data.vertices),
      'mats', [m.name for m in ob.data.materials])
bpy.ops.wm.save_as_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v11.blend')
print('saved')
