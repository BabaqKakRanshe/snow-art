"""Winter kit -> Unity (add-on to the Utility Plane v7 package).
python3 kit_export.py
  Models/SM_WinterKit.fbx  root "WinterKit" = plane prefab space (put it under the plane root at local identity) with
                           the 15 installed forms Kit_<Item> (pivot = socket, identity rotation)
  Models/SM_Kit_*.fbx      12 carry forms, pivot at the bottom centre, child Socket_Grip (+ Socket_Pour on the can)
  Data/winter_kit.json     items (id, label, zone, socket, carry form, effects, excludes, install time), carry forms
                           (mass, size, grip), effect descriptions - Unity prefab space, metres
Unity space: (x, y, z) = (-x_b, z_b, -y_b) of the Blender build frame, as in the v7 plane package."""
import bpy, os, sys, json, math
from mathutils import Vector, Matrix
import addon_utils

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY

OUT = os.path.join(HERE, 'export', 'unity_kit', 'Assets', 'UtilityPlane')
MOD, DATA = os.path.join(OUT, 'Models'), os.path.join(OUT, 'Data')
for d in (MOD, DATA):
    os.makedirs(d, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'kit_final_v1.blend'))
O, SC = bpy.data.objects, bpy.context.scene
INFO = json.load(open(os.path.join(HERE, 'out', 'kit_v1.json')))
TH = math.radians(LY.PARK_PITCH_DEG)
PIV = Vector((0.0, LY.MAIN_WHEEL_C[1], LY.MAIN_CONTACT_Z))
R = Matrix.Translation(PIV) @ Matrix.Rotation(-TH, 4, 'X') @ Matrix.Translation(-PIV)
RI = R.inverted()
UP_B = (RI.to_3x3() @ Vector((0, 0, 1))).normalized()          # parked "up" in the build frame


def to_unity(p):
    return [round(-p[0], 4) + 0.0, round(p[2], 4) + 0.0, round(-p[1], 4) + 0.0]


def ext_unity(h):
    return [round(abs(h[0]), 4), round(abs(h[2]), 4), round(abs(h[1]), 4)]


# ------------------------------------------------------------------ keep only the kit
kit = set(o.name for o in bpy.data.collections['Kit'].objects)
for o in [o for o in O if o.name not in kit]:
    bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.collections if c.name != 'Kit']:
    bpy.data.collections.remove(c)
bpy.ops.outliner.orphans_purge(do_recursive=True) if bpy.context.area else None


def verts_w(name):
    ob = O[name]
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def aabb(pts):
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    return (lo + hi) / 2, (hi - lo) / 2


# ------------------------------------------------------------------ items
# id, label, carry form, effects, install seconds (suggestion), excludes
ITEMS = [
    ('IntakePlug', 'Заглушка воздухозаборника', 'IntakePlug', ['engineStartBlocked'], 4, ['Heater']),
    ('ExhaustCover_L', 'Заглушка выхлопа, левая', 'ExhaustCover', ['engineStartBlocked'], 3, []),
    ('ExhaustCover_R', 'Заглушка выхлопа, правая', 'ExhaustCover', ['engineStartBlocked'], 3, []),
    ('PitotCover', 'Чехол приёмника воздушного давления', 'PitotCover', ['airspeedBlocked'], 3, []),
    ('WingCover_L', 'Чехол левого крыла', 'WingCoverBag', ['liftBlocked'], 40, []),
    ('WingCover_R', 'Чехол правого крыла', 'WingCoverBag', ['liftBlocked'], 40, []),
    ('WindshieldCover', 'Чехол лобового стекла', 'WindshieldCoverBag', ['viewBlocked'], 20, []),
    ('EngineCover', 'Утеплённый чехол двигателя', 'EngineCoverBag', ['engineStartBlocked', 'engineInsulated'], 30, []),
    ('Chocks_L', 'Колодки, левое колесо', 'Chocks', ['wheelsHeld', 'moveBlocked'], 4, []),
    ('Chocks_R', 'Колодки, правое колесо', 'Chocks', ['wheelsHeld', 'moveBlocked'], 4, []),
    ('Chocks_Tail', 'Колодки, хвостовое колесо', 'ChocksTail', ['wheelsHeld', 'moveBlocked'], 4, []),
    ('TieDown_L', 'Швартовка левого крыла', 'TieDownBag', ['tiedDown', 'moveBlocked'], 20, []),
    ('TieDown_R', 'Швартовка правого крыла', 'TieDownBag', ['tiedDown', 'moveBlocked'], 20, []),
    ('TieDown_Tail', 'Швартовка хвоста', 'TieDownBag', ['tiedDown', 'moveBlocked'], 15, []),
    ('Heater', 'Подогреватель двигателя', 'HeaterStowed', ['engineStartBlocked', 'preheating', 'moveBlocked'], 25, ['IntakePlug']),
]
EFFECTS = {
    'engineStartBlocked': 'starter must not run: plug / cover / heater duct in the intake or on the exhaust '
                          '(your rule: refuse, or damage the engine)',
    'airspeedBlocked': 'pitot covered: airspeed indicator reads 0',
    'liftBlocked': 'wing cover on: no takeoff (your rule: refuse power, or no lift on that wing)',
    'viewBlocked': 'windshield cover on: the mesh itself blocks the view from the cockpit',
    'engineInsulated': 'engine cover on: the engine cools slower',
    'wheelsHeld': 'chocks in: the aircraft must not roll (wheel colliders: brake torque, or refuse taxi)',
    'tiedDown': 'tied down: the aircraft must not move (also against wind)',
    'preheating': 'heater running into the intake: engine/oil temperature rises over time',
    'moveBlocked': 'chocks, tie-downs or the heater (duct in the intake): the aircraft must not taxi or be towed',
}
CARRY_OF = {'IntakePlug': 'SM_Kit_IntakePlug', 'ExhaustCover': 'SM_Kit_ExhaustCover', 'PitotCover': 'SM_Kit_PitotCover',
            'WingCoverBag': 'SM_Kit_WingCoverBag', 'WindshieldCoverBag': 'SM_Kit_WindshieldCoverBag',
            'EngineCoverBag': 'SM_Kit_EngineCoverBag', 'Chocks': 'SM_Kit_Chocks', 'ChocksTail': 'SM_Kit_ChocksTail',
            'TieDownBag': 'SM_Kit_TieDownBag', 'HeaterStowed': 'SM_Kit_HeaterStowed', 'JerryCan': 'SM_Kit_JerryCan',
            'Funnel': 'SM_Kit_Funnel'}


CARRY_LABEL = {'IntakePlug': 'Заглушка воздухозаборника', 'ExhaustCover': 'Заглушка выхлопа',
               'PitotCover': 'Чехол ПВД', 'WingCoverBag': 'Сумка с чехлом крыла',
               'WindshieldCoverBag': 'Сумка с чехлом лобового стекла', 'EngineCoverBag': 'Сумка с чехлом двигателя',
               'Chocks': 'Колодки (пара)', 'ChocksTail': 'Колодки хвостового колеса',
               'TieDownBag': 'Сумка швартовки (3 комплекта)', 'HeaterStowed': 'Подогреватель двигателя',
               'JerryCan': 'Канистра 20 л', 'Funnel': 'Воронка с фильтром'}


# windshield slab: glass centre line from (y -3.285, z 2.0) to (y -2.629, z 2.6); box axes = lateral, outward normal,
# along the glass; inner face 14 mm off the glass (cover), 0.12 m thick. Euler X in Unity degrees.
_g0, _g1 = Vector((0.0, -3.285, 2.0)), Vector((0.0, -2.629, 2.6))
_d = (_g1 - _g0).normalized()                              # up-aft along the glass
_n = Vector((0.0, -_d.z, _d.y))                             # outward (forward-up)
WS_EULER_X = math.degrees(math.atan2(-_n.y, _n.z))          # n_unity = (0, n_z, -n_y) = Euler(X) * Unity +Y
WS_SLAB = ((_g0 + _g1) / 2 + _n * (0.014 + 0.06), None)
WS_HALF_LOCAL = (0.74, 0.06, 0.42)                          # Unity local: X lateral, Y along the normal, Z along the glass
ZONE_ROT = {'WindshieldCover': (WS_EULER_X, 0.0, 0.0)}


def zone(item):
    """interaction box (build frame centre, half extents); non-overlapping, reachable from the ground when parked"""
    ob = 'Kit_' + item
    pv = O[ob].matrix_world.translation
    if item == 'IntakePlug':
        return Vector((0.0, -4.62, 1.335)), Vector((0.23, 0.09, 0.11))
    if item.startswith('ExhaustCover'):
        return pv.copy(), Vector((0.11, 0.11, 0.10))
    if item == 'PitotCover':
        return Vector((pv.x, -2.39, pv.z)), Vector((0.05, 0.12, 0.05))
    if item.startswith('WingCover'):                     # slab along the trailing-edge hem (2.4 m above the ground)
        vs = verts_w(ob)
        y_te = max(v.y for v in vs)
        te = [v for v in vs if v.y > y_te - 0.06]
        z0, z1 = min(v.z for v in te), max(v.z for v in te)
        sg = 1 if pv.x > 0 else -1
        x0, x1 = sorted((sg * 1.0, sg * 6.9))
        return Vector(((x0 + x1) / 2, y_te - 0.07, (z0 + z1) / 2)), Vector(((x1 - x0) / 2, 0.13, (z1 - z0) / 2 + 0.08))
    if item == 'WindshieldCover':                         # slab on the glass, outside the cabin (see WS_SLAB)
        return WS_SLAB[0], WS_SLAB[1]
    if item == 'EngineCover':
        return Vector((0.0, -3.985, 1.90)), Vector((0.76, 0.615, 0.22))     # y -4.60 .. -3.37
    if item.startswith('Chocks'):                         # front chock only: clear of the axle-down suspension ray
        cp = R @ pv
        return parked_box([p for p in (R @ v for v in verts_w(ob)) if p.y < cp.y - 0.12])
    if item.startswith('TieDown'):
        cp = R @ pv
        return parked_box([cp + Vector((sx * 0.13, sy * 0.13, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (0.0, 0.25)])
    if item == 'Heater':
        cp = R @ pv
        return parked_box([p for p in (R @ v for v in verts_w(ob))
                           if (p - cp).to_2d().length < 0.55 and p.z < GZ_P + 0.72])
    raise KeyError(item)


GZ_P = LY.MAIN_CONTACT_Z


def parked_box(pts_parked, pad=0.02):
    """box level with the parked ground: returns (centre in the build frame, PARKED half extents); the zone gets
    rotationEuler X = +parked pitch so that it is level when the root is pitched nose-up"""
    lo = Vector((min(p[i] for p in pts_parked) for i in range(3)))
    hi = Vector((max(p[i] for p in pts_parked) for i in range(3)))
    lo.z = max(lo.z, GZ_P)                              # nothing below the ground
    c, h = (lo + hi) / 2, (hi - lo) / 2 + Vector((pad, pad, pad))
    return RI @ c, ('parked', h)


items = []
for it, label, carry, eff, secs, excl in ITEMS:
    ob = O['Kit_' + it]
    c, h = zone(it)
    if isinstance(h, tuple) and h[0] == 'parked':      # ground-aligned (local Y = parked up)
        hp = h[1]
        zrow = dict(center=to_unity(c), halfExtents=[round(hp.x, 4), round(hp.z, 4), round(hp.y, 4)],
                    rotationEuler=[round(LY.PARK_PITCH_DEG, 3), 0.0, 0.0])
    else:
        zrow = dict(center=to_unity(c), halfExtents=ext_unity(h) if h is not None else list(WS_HALF_LOCAL),
                    rotationEuler=list(round(v, 3) for v in ZONE_ROT.get(it, (0.0, 0.0, 0.0))))
    row = dict(id=it, object='Kit_' + it, label=label, socket=to_unity(ob.matrix_world.translation),
               zone=zrow, carry='KitCarry_' + carry, carryFbx=CARRY_OF[carry],
               effects=eff, excludes=excl, installSeconds=secs,
               groundItem=it.startswith(('Chocks', 'TieDown')) or it == 'Heater')
    if it.startswith('TieDown'):
        row['attach'] = to_unity(INFO['installed']['Kit_' + it]['attach'])
        row['ropeLength'] = INFO['installed']['Kit_' + it]['ropeLength']
    if it == 'Heater':
        row['attach'] = to_unity(INFO['installed']['Kit_Heater']['ductEnd'])            # duct end at the intake
    items.append(row)

def zone_axes(z):
    """box axes in Unity prefab space (Unity Euler X only is used here: rotation about +X)"""
    ex = math.radians(z['rotationEuler'][0])
    return [Vector((1, 0, 0)), Vector((0, math.cos(ex), math.sin(ex))), Vector((0, -math.sin(ex), math.cos(ex)))]


def zone_corners(z):
    A, c, h = zone_axes(z), Vector(z['center']), z['halfExtents']
    return [tuple(c + A[0] * (sx * h[0]) + A[1] * (sy * h[1]) + A[2] * (sz * h[2]))
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


# heights above flat ground in the parked pose (root pitched nose-up), for the docs / reach checks
def _rot_x(p, a):
    x, y, z = p
    return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))


_main = to_unity((LY.MAIN_WHEEL_C[0], LY.MAIN_WHEEL_C[1], LY.MAIN_CONTACT_Z))
_root_h = -_rot_x(_main, -TH)[1]
for row in items:
    c = row['zone']['center']
    ys = [_rot_x(p, -TH)[1] + _root_h for p in zone_corners(row['zone'])]
    row['parkedHeight'] = [round(_rot_x(c, -TH)[1] + _root_h, 3), round(min(ys), 3), round(max(ys), 3)]


# zones must not overlap (a ray would stop on the outer one): separating-axis test of oriented boxes
def overlap(a, b):
    A, B = zone_axes(a), zone_axes(b)
    ca, cb = Vector(a['center']), Vector(b['center'])
    ha, hb = a['halfExtents'], b['halfExtents']
    axes = A + B + [x.cross(y) for x in A for y in B]
    for ax in axes:
        if ax.length < 1e-9:
            continue
        ax = ax.normalized()
        ra = sum(ha[i] * abs(A[i].dot(ax)) for i in range(3))
        rb = sum(hb[i] * abs(B[i].dot(ax)) for i in range(3))
        if abs((cb - ca).dot(ax)) >= ra + rb:
            return False
    return True


for i, a in enumerate(items):
    for b in items[i + 1:]:
        assert not overlap(a['zone'], b['zone']), ('zones overlap', a['id'], b['id'])

# ------------------------------------------------------------------ root + installed forms
root = bpy.data.objects.new('WinterKit', None)
root.empty_display_type = 'PLAIN_AXES'
SC.collection.objects.link(root)
for it, *_ in ITEMS:
    ob = O['Kit_' + it]
    mw = ob.matrix_world.copy()
    ob.parent = root
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_world = mw

# ------------------------------------------------------------------ carry forms at the origin + sockets
carry = []
CARRY_SOCKETS = {}
for key, fbx in CARRY_OF.items():
    ob = O[fbx]
    ob.matrix_world = Matrix.Identity(4)
    vs = [v.co for v in ob.data.vertices]
    lo = Vector((min(v[i] for v in vs) for i in range(3)))
    hi = Vector((max(v[i] for v in vs) for i in range(3)))
    if key in ('WingCoverBag', 'WindshieldCoverBag', 'EngineCoverBag', 'TieDownBag'):
        grip = Vector((0.0, 0.0, hi.z - 0.012))
    elif key == 'JerryCan':
        grip = Vector((0.0, 0.0, hi.z - 0.006))
    elif key == 'Funnel':
        grip = Vector((hi.x - 0.006, 0.0, 0.235))
    elif key == 'HeaterStowed':
        grip = Vector((0.0, lo.y + 0.04, 0.62))
    elif key == 'IntakePlug':
        grip = Vector((0.0, lo.y + 0.012, (lo.z + hi.z) / 2 + 0.02))
    elif key in ('Chocks', 'ChocksTail'):
        grip = Vector((hi.x - 0.012, 0.0, hi.z * 0.55))
    else:
        grip = (lo + hi) / 2
    sockets = {'Socket_Grip': grip}
    if key == 'JerryCan':
        sockets['Socket_Pour'] = Vector(INFO['carry']['SM_Kit_JerryCan']['pourPoint'])
    CARRY_SOCKETS[fbx] = sockets
    meta = INFO['carry'][fbx]
    row = dict(prefab='KitCarry_' + key, fbx=fbx, label=CARRY_LABEL[key], massKg=meta['mass'], note=meta['note'],
               sizeM=ext_unity(Vector(meta['size'])), grip=to_unity(grip))
    if key == 'JerryCan':
        row.update(pour=to_unity(sockets['Socket_Pour']), capacityL=20, fuel='Jet A-1 0.80 kg/l',
                   fullMassKg=round(meta['mass'] + 20 * 0.8, 1))
    if key == 'TieDownBag':
        row['sets'] = 3
    if key in ('WingCoverBag', 'Chocks', 'ExhaustCover'):
        row['count'] = 2
    carry.append(row)

# ------------------------------------------------------------------ FBX (same axis setup as the v7 plane)
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
    if ob.type == 'MESH':
        ob.data.name = ob.name
        ob.data.uv_layers[0].name = 'UVMap'
        if not any(m.type == 'TRIANGULATE' for m in ob.modifiers):
            m = ob.modifiers.new('tri', 'TRIANGULATE')
            m.quad_method = m.ngon_method = 'BEAUTY'
            m.keep_custom_normals = True
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


export(os.path.join(MOD, 'SM_WinterKit.fbx'), [root] + list(root.children_recursive))
for key, fbx in CARRY_OF.items():                          # sockets made per export: names must be exact
    made = []
    for sn, p in CARRY_SOCKETS[fbx].items():
        e = bpy.data.objects.new(sn, None)
        assert e.name == sn, ('socket name taken', e.name)
        e.empty_display_size = 0.03
        SC.collection.objects.link(e)
        e.parent = O[fbx]
        e.matrix_parent_inverse = Matrix.Identity(4)
        e.location = p
        made.append(e)
    export(os.path.join(MOD, fbx + '.fbx'), [O[fbx]] + made)
    for e in made:
        e.name = f'{e.name}__{fbx}'                          # kept in the blend for the verification

# ------------------------------------------------------------------ data
dg = bpy.context.evaluated_depsgraph_get()


def tris(ob):
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
    return n


for row in items:
    row['tris'] = tris(O[row['object']])
for row in carry:
    row['tris'] = tris(O[row['fbx']])
park = dict(parkedPitchDeg=round(LY.PARK_PITCH_DEG, 3),
            note='ground items (chocks, tie-down anchors, heater) are modelled level on flat ground in the parked '
                 'pose (root pitched nose-up by parkedPitchDeg), as children of the plane root')
doc = dict(version=1, space='plane prefab space (WinterKit root at local identity under the plane root), metres',
           park=park, items=items, carry=carry, effects=EFFECTS,
           atlases=json.load(open(os.path.join(DATA, 'kit_texel.json'))))
json.dump(doc, open(os.path.join(DATA, 'winter_kit.json'), 'w'), ensure_ascii=False, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'kit_unity_v1.blend'))
print('KIT EXPORT items', len(items), 'carry', len(carry), 'installed tris', sum(r['tris'] for r in items),
      'carry tris', sum(r['tris'] for r in carry))
for r in items:
    print(f"  {r['id']:16s} zone c {r['zone']['center']} h {r['zone']['halfExtents']} tris {r['tris']}")
