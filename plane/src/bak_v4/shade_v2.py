"""v2 bake: UV-unwrap three atlases and bake BaseColor / MR / Normal / AO, then assemble preview materials.
usage: python3 shade_v2.py <resA> <resD> <resC> <tag> <ao_samples>
  A = Airframe (livery skin, seals, struts)  D = Details (gear, wheels, prop, exhaust, antennas, cases)
  C = Cockpit (cabin shell, door panels, all cockpit parts except gauge faces / glass / net)"""
import bpy, bmesh, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nodes as ND
import nodes_cp as NC

RES = dict(A=int(sys.argv[1]), D=int(sys.argv[2]), C=int(sys.argv[3]))
TAG = sys.argv[4]
AO_S = int(sys.argv[5])
TEX = os.path.join(HERE, 'tex', TAG)
os.makedirs(TEX, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v2.blend'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
O, MAT = bpy.data.objects, bpy.data.materials

# ------------------------------------------------------------------ livery part ids + wheel scale
PART = {'src_Fuselage': 0, 'src_Wing': 1, 'src_WingTE_Center': 2, 'src_WingTE_TipL': 2, 'src_WingTE_TipR': 2,
        'Flap_L': 2, 'Flap_R': 2, 'Aileron_L': 2, 'Aileron_R': 2, 'src_Fin': 3, 'Rudder': 3, 'src_Dorsal': 3,
        'src_Stabilizer': 4, 'Elevator_L': 4, 'Elevator_R': 4, 'CargoDoor_L': 5, 'CargoDoor_R': 5, 'PilotDoor_L': 5, 'PilotDoor_R': 5,
        'src_Struts': 6}
for k, v in PART.items():
    O[k]['part'] = float(v)
for k, v in (('Wheel_L', 1.0), ('Wheel_R', 1.0), ('TailWheel', 0.59)):
    O[k]['wscale'] = v


# ------------------------------------------------------------------ split door glass into own objects (AO exclusion)
def split_by_material(ob, matname, newname):
    names = [m.name for m in ob.data.materials]
    if matname not in names:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    ob.active_material_index = names.index(matname)
    bpy.ops.object.material_slot_select()
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    new = [o for o in bpy.context.selected_objects if o != ob][0]
    new.name = newname
    return new


DOORS = ('PilotDoor_L', 'PilotDoor_R', 'CargoDoor_L', 'CargoDoor_R')
for d in DOORS:
    split_by_material(O[d], 'src_Glass', d + '__Glass')
GLASS_OBJS = ['src_GlassFixed'] + [d + '__Glass' for d in DOORS]

# ------------------------------------------------------------------ materials
A_MATS = ['src_Livery', 'src_Seal', 'src_Struts']
D_MATS = ['src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark', 'src_Antenna',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal']
UNBAKED = ['src_Glass', 'src_CP_GaugeGlass', 'src_CP_Gauges', 'src_CP_Net', 'src_CP_Annun']
C_MATS = [m.name for m in MAT if (m.name.startswith('src_CP_') and m.name not in UNBAKED)] + ['src_CabinWall',
                                                                                             'src_DoorPanel']
C_MATS = [m for m in C_MATS if m in MAT]
logo = bpy.data.images.load(os.path.join(HERE, 'tex_src_logo.png'))
logo.pack()
ND.mat_livery(MAT['src_Livery'], logo)
NC.mat_black_plastic(MAT['src_Seal'], (0.010, 0.010, 0.010, 1), 0.6)
ND.mat_generic(MAT['src_Struts'], (0.03, 0.03, 0.032, 1), 0.5, chip_amt=0.03, rust_amt=0.6, dirt=0.3)
ND.mat_gear(MAT['src_GearPaint'])
ND.mat_rubber(MAT['src_Rubber'])
ND.mat_generic(MAT['src_Hub'], (0.035, 0.037, 0.04, 1), 0.45, chip_amt=0.04, rust_amt=0.4, dirt=0.4)
ND.mat_blade(MAT['src_PropBlade'])
ND.mat_generic(MAT['src_Spinner'], (0.022, 0.13, 0.095, 1), 0.33, V='object', chip_amt=0.02, dirt=0.2)
ND.mat_metal_dark(MAT['src_MetalDark'])
ND.mat_case(MAT['src_CaseGreen'], (0.05, 0.085, 0.03, 1))
ND.mat_case(MAT['src_CaseYellow'], (0.50, 0.30, 0.025, 1))
ND.mat_case(MAT['src_CaseDark'], (0.018, 0.022, 0.025, 1))
ND.mat_case(MAT['src_CaseTeal'], (0.018, 0.045, 0.045, 1))
ND.mat_generic(MAT['src_Antenna'], (0.015, 0.015, 0.016, 1), 0.5, dirt=0.1)
NC.build_all({m: MAT[m] for m in C_MATS if m in MAT})
dummy = bpy.data.images.new('BAKE_DUMMY', 8, 8)
for m in UNBAKED + [x.name for x in MAT if x.name.startswith('M_Light')]:
    if m not in MAT:
        continue
    mt = MAT[m]
    mt.use_nodes = True
    nt = mt.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs[0])
    for nm in ('BAKE_COLOR', 'BAKE_MR', 'BAKE_PLAIN'):
        e = nt.nodes.new('ShaderNodeEmission')
        e.name = nm
    t = nt.nodes.new('ShaderNodeTexImage')
    t.name = 'BAKE_TARGET'
    t.image = dummy
    nt.nodes.active = t
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
for m in A_MATS + D_MATS + C_MATS + UNBAKED:
    if m in MAT:
        MAT[m].use_fake_user = True
ATLAS_OF = {m: 'A' for m in A_MATS} | {m: 'D' for m in D_MATS} | {m: 'C' for m in C_MATS}

# ------------------------------------------------------------------ UV unwrap per atlas (face-selection by material)
MESHES = [o for o in O if o.type == 'MESH']
for o in MESHES:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    o.data.uv_layers[0].name = 'UVMap'
    o.data.uv_layers.active_index = 0          # CP_Annunciator carries a second set (LampUV) that must stay untouched
    o.data.uv_layers[0].active_render = True

SCALE_C = {'CP_Panel': 2.2, 'CP_Radios': 2.2, 'CP_Switchgear': 2.2, 'CP_Glareshield': 1.8, 'CP_Pedestal': 2.0,
           'CP_Gauges': 1.6, 'CP_Seat_P': 1.3, 'CP_Seat_C': 1.3, 'CP_Headliner': 0.8, 'src_Fuselage': 0.7,
           'CP_Floor': 0.7, 'CP_Bulkheads': 0.5, 'CP_Headsets': 1.0, 'CP_Overhead': 1.6}


def scale_c(o):
    if o.name in SCALE_C:
        return SCALE_C[o.name]
    if o.name.startswith(('Needle', 'SW_', 'Lever', 'Yoke', 'Pedal', 'Rheo', 'Pull', 'FuelSel', 'ATT', 'HDG', 'TC_',
                          'Clock', 'Trim')):
        return 2.0
    if o.name.startswith(('PilotDoor', 'CargoDoor')):
        return 1.2
    return 1.0


SCALE_A = {'src_Struts': 0.8, 'src_WingDetails': 0.8}
SCALE_D = {'Propeller': 1.3, 'Wheel_L': 1.2, 'Wheel_R': 1.2}


MARGIN_PX = 8
FINAL_RES = dict(A=4096, D=2048, C=4096)      # layout is resolution independent: test bakes reuse the final layout


def unwrap(atlas, mats, scale_fn):
    objs = [o for o in MESHES if o.name not in GLASS_OBJS and
            any(p.material_index < len(o.data.materials) and o.data.materials[p.material_index] and
                o.data.materials[p.material_index].name in mats for p in o.data.polygons)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    for o in objs:
        bm = bmesh.from_edit_mesh(o.data)
        names = [m.name if m else '' for m in o.data.materials]
        for f in bm.faces:
            f.select_set(names[f.material_index] in mats if f.material_index < len(names) else False)
        bmesh.update_edit_mesh(o.data)
    # hide faces of the other atlases: in 5.0 pack_islands otherwise re-packs every island of the edited meshes
    bpy.ops.mesh.hide(unselected=True)
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    for o in objs:
        f_ = scale_fn(o)
        if abs(f_ - 1.0) < 1e-6:
            continue
        bm = bmesh.from_edit_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        for f in bm.faces:
            if f.select:
                for lp in f.loops:
                    lp[uvl].uv *= f_
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=MARGIN_PX / FINAL_RES[atlas],
                            shape_method='CONCAVE', scale=True)
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:                                 # packer overflow puts islands into other UDIM tiles
        names = [m.name if m else '' for m in o.data.materials]
        uv = o.data.uv_layers[0].data
        for p in o.data.polygons:
            if p.material_index < len(names) and names[p.material_index] in mats:
                for li in p.loop_indices:
                    u, v = uv[li].uv
                    assert -1e-4 <= u <= 1.0001 and -1e-4 <= v <= 1.0001, (atlas, o.name, u, v)
    return objs


# keep gauge-atlas UVs untouched: snapshot and verify
def gauge_uv_snapshot():
    snap = {}
    for o in MESHES:
        names = [m.name if m else '' for m in o.data.materials]
        if 'src_CP_Gauges' not in names:
            continue
        gi = names.index('src_CP_Gauges')
        uv = o.data.uv_layers[0].data
        idx = [li for p in o.data.polygons if p.material_index == gi for li in p.loop_indices]
        snap[o.name] = np.array([tuple(uv[i].uv) for i in idx])
    return snap


t0 = time.time()
g0 = gauge_uv_snapshot()
unwrap('A', A_MATS, lambda o: SCALE_A.get(o.name, 1.0))
unwrap('D', D_MATS, lambda o: SCALE_D.get(o.name, 1.0))
unwrap('C', C_MATS, scale_c)
# restore the gauge-atlas UVs (they index T_Gauges, not the baked atlases)
for oname, arr in g0.items():
    o = O[oname]
    names = [m.name if m else '' for m in o.data.materials]
    gi = names.index('src_CP_Gauges')
    uv = o.data.uv_layers[0].data
    idx = [li for p in o.data.polygons if p.material_index == gi for li in p.loop_indices]
    for i, (u, v) in zip(idx, arr):
        uv[i].uv = (u, v)
g1 = gauge_uv_snapshot()
assert all(np.allclose(g0[k], g1[k]) for k in g0)
print('uv done', round(time.time() - t0, 1), 's; gauge UVs restored')
if os.environ.get('UVONLY'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_uv_{TAG}.blend'))
    sys.exit(0)


# ------------------------------------------------------------------ bake
def img(name, res, noncolor=False, float_buf=False):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=float_buf)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


PASSES = {'BaseColor': ('EMIT', 'BAKE_COLOR', False, False), 'MR': ('EMIT', 'BAKE_MR', True, False),
          'Normal': ('NORMAL', None, True, True), 'AO': ('AO', 'BAKE_PLAIN', True, False)}
ATLAS_NAME = {'A': 'Airframe', 'D': 'Details', 'C': 'Cockpit'}
IM = {}


def set_output(mt, node_name):
    nt = mt.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    src = nt.nodes[node_name] if node_name else next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(src.outputs[0], out.inputs['Surface'])


BAKE_OBJS = [o.name for o in MESHES if o.name not in GLASS_OBJS and o.name != 'src_Lights' and len(o.data.polygons)]


AO_RES = {a: max(256, RES[a] // 2) for a in 'ADC'}      # AO is low frequency: half res, upscaled when packing ORM


def bake(pname, samples=1, names=None, clear=True, margin=None, save=True, atlases='ADC', res=None):
    typ, node, noncolor, fbuf = PASSES[pname]
    res = res or RES
    for a in atlases:
        if clear or (a, pname) not in IM:
            IM[(a, pname)] = img(f'T_{ATLAS_NAME[a]}_{pname}', res[a], noncolor, fbuf)
    for mname, a in ATLAS_OF.items():
        if mname not in MAT:
            continue
        mt = MAT[mname]
        set_output(mt, node)
        t = mt.node_tree.nodes['BAKE_TARGET']
        t.image = IM[(a, pname)] if a in atlases else dummy
        mt.node_tree.nodes.active = t
    for mname in UNBAKED + [x.name for x in MAT if x.name.startswith('M_Light')]:
        if mname in MAT:
            set_output(MAT[mname], node if node else None)
    sc.cycles.samples = samples
    bk = sc.render.bake
    bk.use_clear = clear
    bk.margin = margin if margin is not None else max(4, max(res[a] for a in atlases) // 256)
    bk.margin_type = 'EXTEND'
    bk.target = 'IMAGE_TEXTURES'
    bk.normal_space = 'TANGENT'
    bk.normal_r, bk.normal_g, bk.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
    bpy.ops.object.select_all(action='DESELECT')
    names = names or BAKE_OBJS
    for n in names:
        O[n].select_set(True)
    bpy.context.view_layer.objects.active = O[names[0]]
    t0 = time.time()
    bpy.ops.object.bake(type=typ)
    print('baked', pname, atlases, round(time.time() - t0, 1), 's', flush=True)
    if not save:
        return
    for a in atlases:
        im = IM[(a, pname)]
        p = os.path.join(TEX, im.name + '.png')
        im.filepath_raw = p
        im.file_format = 'PNG'
        if fbuf:
            sc.render.image_settings.file_format = 'PNG'
            sc.render.image_settings.color_depth = '16'
            sc.render.image_settings.color_mode = 'RGB'
            im.save_render(p, scene=sc)
        else:
            im.save()


def objs_with(atl):
    r = []
    for n in BAKE_OBJS:
        names = [m.name if m else '' for m in O[n].data.materials]
        if any((ATLAS_OF.get(names[p.material_index]) or '_') in atl for p in O[n].data.polygons if p.material_index < len(names)):
            r.append(n)
    return r


if not sc.world:
    sc.world = bpy.data.worlds.new('World')
bake('BaseColor')
bake('MR')
bake('Normal')
for g in GLASS_OBJS:
    O[g].hide_render = True
O['Propeller'].hide_render = True
# exterior AO: 0.6 m reach (wing root, struts, gear), interior AO: 0.22 m (the cabin is closed, a long reach is black)
sc.world.light_settings.distance = 0.6
ext = [n for n in objs_with('AD') if n != 'Propeller']
bake('AO', samples=AO_S, names=ext, save=False, atlases='AD', res=AO_RES)
O['Propeller'].hide_render = False
bake('AO', samples=AO_S, names=['Propeller'], clear=False, margin=2, atlases='AD', res=AO_RES)
O['Propeller'].hide_render = True
sc.world.light_settings.distance = 0.22
bake('AO', samples=AO_S, names=objs_with('C'), atlases='C', res=AO_RES)
O['Propeller'].hide_render = False
for g in GLASS_OBJS:
    O[g].hide_render = False
for mname in ATLAS_OF:
    if mname in MAT:
        set_output(MAT[mname], None)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_src_{TAG}.blend'))
print('saved src blend', flush=True)
