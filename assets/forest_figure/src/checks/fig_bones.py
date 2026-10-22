"""posed bone heads / tails of the figure at a clip frame: python3 -I fig_bones.py <fig.blend> <clip> <frame>"""
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
arm = bpy.data.objects['Apparition_Rig']
arm.animation_data.action = bpy.data.actions[sys.argv[2]]
bpy.context.scene.frame_set(int(sys.argv[3]))
bpy.context.view_layer.update()
for n in ('Root', 'Hips', 'Spine', 'Chest', 'Neck', 'Head', 'UpperArm.L', 'ForeArm.L', 'Thigh.L', 'Shin.L', 'Foot.L'):
    pb = arm.pose.bones[n]
    print(n, 'head', [round(c, 3) for c in pb.head], 'tail', [round(c, 3) for c in pb.tail], 'q', [round(c, 3) for c in pb.rotation_quaternion])
