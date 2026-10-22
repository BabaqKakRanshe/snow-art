import bpy
bpy.ops.wm.open_mainfile(filepath='/home/claude/plane/out/plane_v9_final_v13.blend')
for m in bpy.data.materials:
    if m.name.startswith(('M_Airframe','M_Wing','M_Details','M_Floor','M_Light','M_Interior')):
        imgs = [(n.image.name, n.image.filepath, n.image.size[:]) for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []
        print(m.name, imgs[:3])
print('cameras', [o.name for o in bpy.data.objects if o.type=='CAMERA'], 'lights', [o.name for o in bpy.data.objects if o.type=='LIGHT'][:5])
print('scene', bpy.context.scene.render.engine, bpy.context.scene.world.name if bpy.context.scene.world else None)
