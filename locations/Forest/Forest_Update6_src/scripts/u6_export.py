"""Forest Update 6: the FBX of the package.

  gcf    GenContainer (+ the nine IX parts and Window_Glass as children) - Update 3's FBX convention, the same exporter as
         Updates 4 and 5 (u4_export.py: FBX 7400, Y up, front +Z, UnitScaleFactor 100, the root at the origin without
         rotation, children with translations only, normals written)
  items  the 84 item models Item_* (83 of Update 3 + Item_RadioSet): one mesh each, the origin where Update 3 had it
  fig    Apparition: the skinned figure - the armature Apparition_Rig (19 bones, Root first) and the mesh
         Apparition_Body, four takes (Stand, Walk, Sit, SitLook) at 24 fps. Skinned models do not take Blender's
         "apply transform" (it breaks the bind pose), so this one is written the usual way for Unity: front -Z, up Y,
         scale "FBX all" - in Unity the prefab root stands upright at identity, its child Apparition_Rig carries the
         axis conversion (rotation x -90), as with any model from Blender. The takes are named "Apparition_Rig|<clip>".

The lens, water, display and panel faces are already joined into their objects as extra materials with the names the
game knows (M_TorchLens, M_Water, M_RadioDisplay; M_Lamp_BulbOff, M_LEDOff, M_GlassClear in the container): nothing to
remap.

python3 -I u6_export.py -- <out_dir> [gcf] [items] [fig]  ->  <out_dir>/*.fbx, u6_export_report.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import u4_export as E

ITEMS = json.load(open(os.path.join(E.OUT_PKG, 'items.json')))['items']
E.BATCHES = {
    'gcf': ('gcf.blend', ['GenContainer']),
    'items': ('items.blend', sorted(ITEMS)),
}
E.MAT_REMAP = {}
FIG_CLIPS = ('Stand', 'Walk', 'Sit', 'SitLook')


def export_fig(out_dir):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(E.OUT_PKG, 'fig.blend'))
    sc = bpy.context.scene
    arm = bpy.data.objects['Apparition_Rig']
    body = bpy.data.objects['Apparition_Body']
    assert body.parent == arm and arm.parent is None
    assert arm.matrix_world.is_identity and body.matrix_world.is_identity
    acts = [bpy.data.actions[n] for n in FIG_CLIPS]
    for a in list(bpy.data.actions):
        if a.name not in FIG_CLIPS:                       # only the four clips go into the file
            bpy.data.actions.remove(a)
    ranges = {}
    for a in acts:
        lo, hi = a.frame_range
        a.use_frame_range = True
        a.frame_start, a.frame_end = lo, hi
        ranges[a.name] = [int(lo), int(hi)]
    arm.animation_data.action = bpy.data.actions['Stand']
    sc.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (arm, body):
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    fp = os.path.join(out_dir, 'Apparition.fbx')       # the mesh goes in its bind pose (the armature modifier is not applied)
    bpy.ops.export_scene.fbx(filepath=fp, use_selection=True, use_visible=False, object_types={'ARMATURE', 'MESH'},
                             global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                             use_mesh_modifiers=False, mesh_smooth_type='FACE', use_subsurf=False, use_mesh_edges=False,
                             use_tspace=False, use_triangles=False, use_custom_props=False, colors_type='NONE',
                             add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             use_armature_deform_only=False, armature_nodetype='NULL',
                             bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                             bake_anim_simplify_factor=0.0, path_mode='STRIP', embed_textures=False, batch_mode='OFF')
    vs = [body.matrix_world @ v.co for v in body.data.vertices]
    aabb = [[round(min(v[i] for v in vs), 4) for i in range(3)], [round(max(v[i] for v in vs), 4) for i in range(3)]]
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    return {'Apparition': {'file': 'Apparition.fbx', 'objects': ['Apparition_Body'], 'armature': 'Apparition_Rig',
                           'bones': [b.name for b in arm.data.bones], 'clips': ranges, 'fps': sc.render.fps,
                           'materials': sorted(m.name for m in body.data.materials), 'tris': tris,
                           'aabb': {'Apparition_Body': aabb}, 'pivots': {'Apparition_Body': [0.0, 0.0, 0.0]},
                           'bytes': os.path.getsize(fp), 'skinned': True}}


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_dir = a[0]
    os.makedirs(out_dir, exist_ok=True)
    rep = {}
    for b in (a[1:] or ['gcf', 'items', 'fig']):
        if b == 'fig':
            rep.update(export_fig(out_dir))
        else:
            rep.update(E.export(b, out_dir))
    jp = os.path.join(out_dir, 'u6_export_report.json')
    old = json.load(open(jp)) if os.path.exists(jp) else {}
    old.update(rep)
    json.dump(old, open(jp, 'w'), indent=1, ensure_ascii=False)
    print('[u6] exported', len(rep), 'models ->', jp)
