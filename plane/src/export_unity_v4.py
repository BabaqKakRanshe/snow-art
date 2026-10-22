"""Unity export of Utility Plane v4 (from out/plane_v2_final_final4.blend + export/ue/*.json + export/ue/Textures).
usage: python3 export_unity_v4.py
Output: export/unity_v4/Assets/UtilityPlane/{Models,Textures,Data}
 - UtilityPlane.fbx: hierarchy of rigid parts, every moving part = own object, pivot on its hinge/axle,
   Unity axes (nose +Z, up +Y, right +X), metres. Sockets = empties. Collider proxies = COL_* meshes.
 - SM_Cargo_Case1..6.fbx (pivot at the bottom centre)
 - Data/*.json: interaction volumes / cargo layout / displays in Unity space."""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

OUT = os.path.join(HERE, 'export', 'unity_v4', 'Assets', 'UtilityPlane')
MOD, TEXD, DATA = (os.path.join(OUT, d) for d in ('Models', 'Textures', 'Data'))
for d in (MOD, TEXD, DATA):
    os.makedirs(d, exist_ok=True)
UE = os.path.join(HERE, 'export', 'ue')


def to_unity(p):
    """build frame (x left, y aft, z up, m) -> Unity (x right, y up, z forward, m)"""
    return [round(-p[0], 5), round(p[2], 5), round(-p[1], 5)]


# ================================================================== textures (from the shipped UE maps)
def tex_unity():
    for atl in ('Airframe', 'Details', 'Cockpit'):
        bc = Image.open(os.path.join(UE, 'Textures', f'T_{atl}_BC.png')).convert('RGB')
        bc.save(os.path.join(TEXD, f'T_{atl}_BaseColor.png'), optimize=True)
        n = np.asarray(Image.open(os.path.join(UE, 'Textures', f'T_{atl}_N.png')).convert('RGB')).copy()
        n[..., 1] = 255 - n[..., 1]                                   # DirectX -> OpenGL (Unity)
        Image.fromarray(n, 'RGB').save(os.path.join(TEXD, f'T_{atl}_Normal.png'), optimize=True)
        orm = np.asarray(Image.open(os.path.join(UE, 'Textures', f'T_{atl}_ORM.png')).convert('RGB'))
        ms = np.dstack([orm[..., 2], orm[..., 2], orm[..., 2], 255 - orm[..., 1]]).astype(np.uint8)
        Image.fromarray(ms, 'RGBA').save(os.path.join(TEXD, f'T_{atl}_MetallicSmoothness.png'), optimize=True)
        Image.fromarray(orm[..., 0], 'L').save(os.path.join(TEXD, f'T_{atl}_AO.png'), optimize=True)
        print('tex', atl)
    for f in ('T_Gauges_BC.png', 'T_CargoNet_BCA.png'):
        Image.open(os.path.join(UE, 'Textures', f)).save(os.path.join(TEXD, f), optimize=True)


tex_unity()

# ================================================================== scene
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v2_final_final4.blend'))
O = bpy.data.objects
SC = bpy.context.scene
CPR = json.load(open(os.path.join(HERE, 'out', 'cockpit_rig.json')))
RIG = json.load(open(os.path.join(UE, 'rig.json')))
VOL = json.load(open(os.path.join(UE, 'interaction_volumes.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'light_pos.json')))
ROOT = O['UtilityPlane']


def link(ob):
    SC.collection.objects.link(ob) if ob.name not in SC.collection.objects else None


def empty(name, loc, parent, size=0.05):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    SC.collection.objects.link(e)
    e.matrix_world = Matrix.Translation(Vector(loc))
    set_parent(e, parent)
    return e


def set_parent(ob, parent):
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    ob.matrix_world = mw


def split_faces(ob, pred, newname, origin=None):
    """move faces where pred(face, bm) is True into a new object (same materials). Returns the new object."""
    new = ob.copy()
    new.data = ob.data.copy()
    new.name = newname
    new.data.name = newname
    for c in ob.users_collection:
        c.objects.link(new)
    for target, keep in ((new, True), (ob, False)):
        bm = bmesh.new()
        bm.from_mesh(target.data)
        kill = [f for f in bm.faces if bool(pred(f, bm)) != keep]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(target.data)
        bm.free()
    if origin is not None:
        set_origin(new, origin)
    return new


def set_origin(ob, p):
    p = Vector(p)
    mw = ob.matrix_world.copy()
    local = mw.inverted() @ p
    ob.data.transform(Matrix.Translation(-local))
    ob.matrix_world = mw @ Matrix.Translation(local)


def mat_index(ob, name):
    names = [m.name if m else '' for m in ob.data.materials]
    return names.index(name) if name in names else -1


def world_center(ob, f):
    return ob.matrix_world @ f.calc_center_median()


def join(names, newname, parent):
    bpy.ops.object.select_all(action='DESELECT')
    obs = [O[n] for n in names if n in O]
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = newname
    set_parent(ob, parent)
    return ob


# ------------------------------------------------------------------ cargo cases -> separate FBX
cargo = {}
for i, cn in enumerate(sorted(n.name for n in O if n.name.startswith('src_Case')), 1):
    ob = O[cn]
    ob.parent = None
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p[k] for p in pts) for k in range(3)))
    mx = Vector((max(p[k] for p in pts) for k in range(3)))
    bc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.transform(Matrix.Translation(-bc))
    name = f'SM_Cargo_Case{i}'
    ob.name = ob.data.name = name
    cargo[name] = dict(position=to_unity(bc), size=[round(mx.x - mn.x, 3), round(mx.z - mn.z, 3), round(mx.y - mn.y, 3)])
    cargo[name]['note'] = 'position on the concept art, local space of the UtilityPlane root (m); spawn as a free physics body'
json.dump(cargo, open(os.path.join(DATA, 'cargo_layout.json'), 'w'), indent=1)

# ------------------------------------------------------------------ cockpit: lamps, emissive lenses, statics
cp_rig = CPR['rig']
cockpit = empty('Cockpit', (0, 0, 0), ROOT, 0.2)
ann = O['CP_Annunciator']
lampuv = ann.data.uv_layers['LampUV']
for i in range(len(LY.ANNUN_LAMPS)):
    def is_lamp(f, bm, i=i):
        uvl = bm.loops.layers.uv['LampUV']
        return abs(f.loops[0][uvl].uv[0] - (i + 0.5)) < 0.25
    bm = bmesh.new()
    bm.from_mesh(ann.data)
    uvl = bm.loops.layers.uv['LampUV']
    ctr = [f.calc_center_median() for f in bm.faces if abs(f.loops[0][uvl].uv[0] - (i + 0.5)) < 0.25][0]
    bm.free()
    lamp = split_faces(ann, is_lamp, f'Lamp_{i:02d}', origin=ctr)
    set_parent(lamp, cockpit)
bpy.data.objects.remove(ann)

li = mat_index(O['CP_Overhead'], 'M_Light_Cabin')
dome = split_faces(O['CP_Overhead'], lambda f, bm: f.material_index == li, 'Lens_Dome', origin=(0.0, -2.29, 2.55))
set_parent(dome, cockpit)
li = mat_index(O['CP_CargoLight'], 'M_Light_Cabin')
cz = min((O['CP_CargoLight'].matrix_world @ v.co).z for v in O['CP_CargoLight'].data.vertices)
lcargo = split_faces(O['CP_CargoLight'], lambda f, bm: f.material_index == li, 'Lens_CargoLight',
                     origin=(0.0, LY.CARGO_LIGHT_Y, cz))
set_parent(lcargo, cockpit)

cp_static = [o.name for o in bpy.data.collections['Cockpit'].objects
             if o.type == 'MESH' and o.name not in cp_rig and not o.name.startswith(('Lamp_', 'Lens_'))]
join(cp_static, 'Cockpit_Static', cockpit)
for bone, info in cp_rig.items():
    par = cockpit if info['parent'] == 'Cockpit' else O[info['parent']]
    set_parent(O[bone], par)

# ------------------------------------------------------------------ exterior: light lenses, glass, body
lob = O['src_Lights']
LP = {k: Vector(v) for k, v in LIGHTS.items()}


def nearest_light(c):
    return min(LP, key=lambda k: (LP[k] - c).length)


for key, pos in LIGHTS.items():                      # per-face nearest light (indices shift after every split)
    lens = split_faces(lob, lambda f, bm, key=key: nearest_light(lob.matrix_world @ f.calc_center_median()) == key,
                       f'Lens_{key}', origin=pos)
    set_parent(lens, ROOT)
bpy.data.objects.remove(lob)

glass = O['src_GlassFixed']
glass.name = glass.data.name = 'Glass'
for d in ('PilotDoor_L', 'PilotDoor_R', 'CargoDoor_L', 'CargoDoor_R'):
    g = O[d + '__Glass']
    g.name = g.data.name = d + '_Glass'
    set_parent(g, O[d])

# ------------------------------------------------------------------ collider proxies (convex, <= ~250 tris each)
cols = empty('Colliders', (0, 0, 0), ROOT, 0.2)


def box_obj(name, x0, x1, y0, y1, z0, z1, parent):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    set_parent(ob, parent)
    return ob


def hull_obj(name, pts, parent, max_tris=240):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    if len(me.polygons) > max_tris:
        md = ob.modifiers.new('dec', 'DECIMATE')
        md.ratio = max_tris / len(me.polygons)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier='dec')
    set_parent(ob, parent)
    return ob


def verts_of(names, cond=lambda p: True):
    out = []
    for n in names:
        ob = O[n]
        out += [p for p in (ob.matrix_world @ v.co for v in ob.data.vertices) if cond(p)]
    return out


F, YA = LY.FLOOR_Z, LY.REAR_BULKHEAD_Y
body_parts = ['src_Fuselage', 'src_CowlDetails']
box_obj('COL_Floor', -0.70, 0.70, -3.32, YA, 0.93, F, cols)
box_obj('COL_Roof', -0.74, 0.74, -2.62, YA, 2.60, 2.70, cols)
box_obj('COL_RearBulkhead', -0.72, 0.72, YA, YA + 0.08, 0.96, 2.66, cols)
PD, CD = LY.PILOT_DOOR[0], LY.CARGO_DOOR[0]
pd_y0, pd_y1 = min(p[0] for p in PD), max(p[0] for p in PD)
pd_z0, pd_z1 = min(p[1] for p in PD), max(p[1] for p in PD)
cd_y0, cd_y1 = min(p[0] for p in CD), max(p[0] for p in CD)
cd_z0, cd_z1 = min(p[1] for p in CD), max(p[1] for p in CD)
for sg, s_ in ((1, 'L'), (-1, 'R')):
    xa, xb = sorted((sg * 0.69, sg * 0.77))
    box_obj(f'COL_Wall_{s_}_Front', xa, xb, -3.32, pd_y0, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_Mid', xa, xb, pd_y1, cd_y0, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_Aft', xa, xb, cd_y1, YA, 0.96, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_PilotSill', xa, xb, pd_y0, pd_y1, 0.96, pd_z0, cols)
    box_obj(f'COL_Wall_{s_}_PilotHead', xa, xb, pd_y0, pd_y1, pd_z1, 2.62, cols)
    box_obj(f'COL_Wall_{s_}_CargoSill', xa, xb, cd_y0, cd_y1, 0.96, cd_z0, cols)
    box_obj(f'COL_Wall_{s_}_CargoHead', xa, xb, cd_y0, cd_y1, cd_z1, 2.62, cols)
    hull_obj(f'COL_Wing_{s_}', verts_of(['src_Wing', 'src_WingTE_Center', f'src_WingTE_Tip{s_}', f'Flap_{s_}',
                                         f'Aileron_{s_}'], lambda p, sg=sg: p.x * sg >= -0.01), cols)
    hull_obj(f'COL_Strut_{s_}', verts_of(['src_Struts'], lambda p, sg=sg: p.x * sg > 0), cols)
    hull_obj(f'COL_Gear_{s_}', verts_of([f'Gear_{s_}']), O[f'Gear_{s_}'])
    for d in (f'PilotDoor_{s_}', f'CargoDoor_{s_}'):
        hull_obj(f'COL_{d}', verts_of([d, d + '_Glass']), O[d])
    sx = sg * 0.33
    box_obj(f'COL_Seat_{"P" if sg > 0 else "C"}', sx - 0.25, sx + 0.25, -2.49, -1.98, F, 2.22, cols)
hull_obj('COL_Nose', verts_of(body_parts, lambda p: p.y < LY.FIREWALL_Y + 0.02), cols)
hull_obj('COL_Windshield', verts_of(['src_Fuselage'], lambda p: -3.34 < p.y < -2.60 and p.z > 2.0), cols)
hull_obj('COL_TailCone', verts_of(['src_Fuselage'], lambda p: p.y > YA - 0.02), cols)
hull_obj('COL_HStab', verts_of(['src_Stabilizer', 'Elevator_L', 'Elevator_R']), cols)
hull_obj('COL_Fin', verts_of(['src_Fin', 'Rudder', 'src_Dorsal']), cols)
box_obj('COL_Panel', -0.66, 0.66, -3.32, -2.975, F, 2.08, cols)
box_obj('COL_Pedestal', -0.075, 0.075, -2.975, -2.55, F, 1.42, cols)
hull_obj('COL_Propeller', verts_of(['Propeller']), O['Propeller'])

# ------------------------------------------------------------------ body + hierarchy tidy
ext_static = ['src_Fuselage', 'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'src_Struts',
              'src_Fin', 'src_Stabilizer', 'src_CowlDetails', 'src_Antennas', 'src_WingDetails', 'src_FuseDetails',
              'src_Dorsal']
join(ext_static, 'Body', ROOT)
set_parent(glass, ROOT)

# ------------------------------------------------------------------ sockets (empties)
socks = empty('Sockets', (0, 0, 0), ROOT, 0.2)
for part in ('exterior', 'cockpit'):
    for name, b in RIG[part].items():
        if b['deform']:
            continue
        h = b['head']
        pos = (h[1] / 100.0, -h[0] / 100.0, h[2] / 100.0)        # rotated UE-prep frame (cm) -> build frame (m)
        par = b['parent']
        parent = cockpit if par == 'Cockpit' else socks if par in ('Body', None) else O[par]
        empty(name, pos, parent, 0.04)
# glass-cockpit style display overlay for the GPS/COM unit (quad size in displays.json)
gps_c = (-0.110, LY.PANEL_Y + 0.0130, 1.8907)
empty('Display_GPS', gps_c, cockpit, 0.03)
json.dump({'Display_GPS': dict(parent='Cockpit', size=[0.0874, 0.0653],
                               note='quad in the local XY plane, facing -Z (towards the pilot); '
                                    'powered by avionics bus; the static texture shows a placeholder screen')},
          open(os.path.join(DATA, 'displays.json'), 'w'), indent=1)

# ------------------------------------------------------------------ interaction volumes in Unity space
vols = []
for vid, v in VOL.items():
    c, h = v['center_cm'], v['half_extent_cm']            # UE axes: X fwd, Y right, Z up (cm), relative to bone
    parent = v['bone']
    if parent == 'Body':
        parent = 'UtilityPlane'
    vols.append(dict(id=vid, parent=parent, kind=v['kind'], label=v['label'],
                     center=[round(c[1] / 100, 4), round(c[2] / 100, 4), round(c[0] / 100, 4)],
                     halfExtents=[round(h[1] / 100, 4), round(h[2] / 100, 4), round(h[0] / 100, 4)]))
for s_, sx in (('P', 0.33), ('C', -0.33)):
    vols.append(dict(id=f'Seat_{s_}', parent='Cockpit', kind='seat',
                     label='Кресло пилота' if s_ == 'P' else 'Кресло пассажира',
                     center=to_unity((sx, -2.22, 1.55)), halfExtents=[0.22, 0.2, 0.22]))
json.dump(vols, open(os.path.join(DATA, 'interaction_volumes.json'), 'w'), ensure_ascii=False, indent=1)
print('volumes', len(vols))

# ------------------------------------------------------------------ export FBX (Unity axes) with the nested-object fix
import addon_utils
addon_utils.enable('io_scene_fbx')
from io_scene_fbx import fbx_utils
_orig = fbx_utils.ObjectWrapper.fbx_object_matrix


def _patched(self, scene_data, rest=False, local_space=False, global_space=False):
    par = self.parent
    if (not local_space and not global_space and par is not None and self._tag == 'OB' and par._tag == 'OB'
            and not self.parented_to_armature and self.use_bake_space_transform(scene_data)
            and par.use_bake_space_transform(scene_data)):
        L = self.matrix_rest_local if rest else self.matrix_local
        return scene_data.settings.global_matrix @ L @ scene_data.settings.global_matrix_inv
    return _orig(self, scene_data, rest, local_space, global_space)


fbx_utils.ObjectWrapper.fbx_object_matrix = _patched
for ob in O:
    if ob.type == 'MESH' and ob.data.materials:          # drop unused material slots (one submesh per used material)
        me = ob.data
        used = sorted(set(p.material_index for p in me.polygons))
        keep = [me.materials[i] for i in used]
        idx = [used.index(p.material_index) for p in me.polygons]
        me.materials.clear()
        for m in keep:
            me.materials.append(m)
        for p, i in zip(me.polygons, idx):
            p.material_index = i
for ob in O:
    if ob.type == 'MESH':
        ob.data.name = ob.name
        if ob.data.uv_layers:
            ob.data.uv_layers[0].name = 'UVMap'
            ob.data.uv_layers.active_index = 0
        if not any(m.type == 'TRIANGULATE' for m in ob.modifiers):
            m = ob.modifiers.new('tri', 'TRIANGULATE')
            m.quad_method = m.ngon_method = 'BEAUTY'
    for k in list(ob.keys()):
        del ob[k]


def export(path, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'EMPTY', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Z', axis_up='Y', bake_space_transform=True,
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, use_triangles=False,
        use_custom_props=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False)


export(os.path.join(MOD, 'UtilityPlane.fbx'), [ROOT] + list(ROOT.children_recursive))
for name in cargo:
    export(os.path.join(MOD, name + '.fbx'), [O[name]])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_unity_v4.blend'))

tris = sum(len(o.data.polygons) for o in ROOT.children_recursive if o.type == 'MESH' and not o.name.startswith('COL_'))
print('UNITY objects', len(ROOT.children_recursive), 'render polys', tris,
      'colliders', sum(1 for o in ROOT.children_recursive if o.name.startswith('COL_')))
