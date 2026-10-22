"""v7 bake (v6 + new Details parts: prop blades, tundra tyres, exhaust, antennas, locks, ladder, key; Details at 4K): Airframe UVs transferred from the v4 bake (textures reused), UV-unwrap and bake five atlases.
usage: python3 shade_v5.py <resC> <resI> <resF> <resS> <resD> <tag> <ao_samples>
  C = Cockpit (panel, glareshield, pedestal, controls, overhead, headsets, visors)
  I = Interior (sidewall liners, headliner, door trims, insulation, barrier posts, hidden skin)
  F = Floor (tread plate, cockpit floor, tracks, kick strips, steel fittings, trims, seals)
  S = Seats (cushions, frames, harness)          D = Details (gear, wheels, prop, antennas, cases)
Reads out/plane_v7.blend (+ out/plane_v2_src_final4.blend for the Airframe UVs, out/plane_v6_src_v6.blend for I/F/S).
Writes tex/<tag>/T_<Atlas>_{BaseColor,MR,Normal,AO}.png and out/plane_v7_src_<tag>.blend
env ATLASES=CIFSD (subset to bake; the others are only unwrapped), PASSES=BaseColor,MR,Normal,AO, UVONLY=1"""
import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector, kdtree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nodes as ND
import nodes_cp as NC
import nodes7 as N7

RES = dict(C=int(sys.argv[1]), I=int(sys.argv[2]), F=int(sys.argv[3]), S=int(sys.argv[4]), D=int(sys.argv[5]))
TAG = sys.argv[6]
AO_S = int(sys.argv[7])
TEX = os.path.join(HERE, 'tex', TAG)
os.makedirs(TEX, exist_ok=True)
REF = os.path.join(HERE, 'out', 'plane_v2_src_final4.blend')
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v7.blend'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
O, MAT = bpy.data.objects, bpy.data.materials

# ------------------------------------------------------------------ livery part ids + wheel scale (as v2)
PART = {'src_Fuselage': 0, 'src_Wing': 1, 'src_WingTE_Center': 2, 'src_WingTE_TipL': 2, 'src_WingTE_TipR': 2,
        'Flap_L': 2, 'Flap_R': 2, 'Aileron_L': 2, 'Aileron_R': 2, 'src_Fin': 3, 'Rudder': 3, 'src_Dorsal': 3,
        'src_Stabilizer': 4, 'Elevator_L': 4, 'Elevator_R': 4, 'CargoDoor_L': 5, 'CargoDoor_R': 5, 'PilotDoor_L': 5,
        'PilotDoor_R': 5, 'src_Struts': 6}
for k, v in PART.items():
    O[k]['part'] = float(v)
for k, v in (('Wheel_L', 1.0), ('Wheel_R', 1.0), ('TailWheel', 0.59), ('src_StepLadder', 1.0), ('Ladder_RearLegs', 1.0)):
    O[k]['wscale'] = v


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

# ------------------------------------------------------------------ atlas membership
A_MATS = ['src_Livery', 'src_Seal', 'src_Struts']
D_MATS = ['src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark', 'src_Antenna',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal',
          'src_Brake', 'src_Caliper', 'src_Alu', 'src_LadderTread', 'src_KeyMetal', 'src_KeyFob']      # v7
UNBAKED = ['src_Glass', 'src_CP_GaugeGlass', 'src_CP_Gauges', 'src_CP_Net', 'src_CP_Annun', 'src_IN_Webbing',
           'src_CP_Screen', 'src_PropBlur', 'src_PropDisc']
I_MATS = ['src_IN_Liner', 'src_IN_Headliner', 'src_IN_Insul', 'src_IN_Composite', 'src_IN_Vinyl', 'src_IN_Hidden',
          'src_CabinWall', 'src_DoorPanel']
F_MATS = ['src_IN_Tread', 'src_IN_FloorPaint', 'src_IN_Track', 'src_IN_Kick', 'src_IN_Steel', 'src_IN_Trim',
          'src_IN_Seal']
S_MATS = [m.name for m in MAT if m.name.startswith('src_ST_')]
C_MATS = [m.name for m in MAT if m.name.startswith('src_CP_') and m.name not in UNBAKED]
used = set()
for o in O:
    if o.type == 'MESH':
        ms = o.data.materials
        idx = {p.material_index for p in o.data.polygons}
        used |= {ms[i].name for i in idx if i < len(ms) and ms[i]}
I_MATS, F_MATS, S_MATS, C_MATS = ([m for m in L if m in MAT and m in used] for L in (I_MATS, F_MATS, S_MATS, C_MATS))
D_MATS = [m for m in D_MATS if m in MAT]
BAKED = {'C': C_MATS, 'I': I_MATS, 'F': F_MATS, 'S': S_MATS, 'D': D_MATS}
ATLAS_OF = {m: a for a, L in BAKED.items() for m in L}
ATLAS_NAME = {'A': 'Airframe', 'C': 'Cockpit', 'I': 'Interior', 'F': 'Floor', 'S': 'Seats', 'D': 'Details'}
print('atlases', {a: len(L) for a, L in BAKED.items()})

# ------------------------------------------------------------------ materials
ND.mat_livery(MAT['src_Livery'], bpy.data.images.load(os.path.join(HERE, 'tex_src_logo.png')))
NC.mat_black_plastic(MAT['src_Seal'], (0.010, 0.010, 0.010, 1), 0.6)
ND.mat_generic(MAT['src_Struts'], (0.03, 0.03, 0.032, 1), 0.5, chip_amt=0.03, rust_amt=0.6, dirt=0.3)
ND.mat_gear(MAT['src_GearPaint'])
ND.mat_generic(MAT['src_Hub'], (0.035, 0.037, 0.04, 1), 0.45, chip_amt=0.04, rust_amt=0.4, dirt=0.4)
ND.mat_generic(MAT['src_Spinner'], (0.022, 0.13, 0.095, 1), 0.33, V='object', chip_amt=0.02, dirt=0.2)
N7.build_v7(MAT)                                      # v7: blades, rubber, exhaust tint, brake, ladder, key
ND.mat_case(MAT['src_CaseGreen'], (0.05, 0.085, 0.03, 1))
ND.mat_case(MAT['src_CaseYellow'], (0.50, 0.30, 0.025, 1))
ND.mat_case(MAT['src_CaseDark'], (0.018, 0.022, 0.025, 1))
ND.mat_case(MAT['src_CaseTeal'], (0.018, 0.045, 0.045, 1))
ND.mat_generic(MAT['src_Antenna'], (0.015, 0.015, 0.016, 1), 0.5, dirt=0.1)
NC.build_all({m: MAT[m] for m in C_MATS + I_MATS + F_MATS + S_MATS})
dummy = bpy.data.images.new('BAKE_DUMMY', 8, 8)
FLAT = UNBAKED + [x.name for x in MAT if x.name.startswith('M_Light')]
for m in FLAT:
    if m not in MAT:
        continue
    nt = MAT[m].node_tree if MAT[m].use_nodes else None
    MAT[m].use_nodes = True
    nt = MAT[m].node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs[0])
    for nm in ('BAKE_COLOR', 'BAKE_MR', 'BAKE_PLAIN'):
        nt.nodes.new('ShaderNodeEmission').name = nm
    t = nt.nodes.new('ShaderNodeTexImage')
    t.name = 'BAKE_TARGET'
    t.image = dummy
    nt.nodes.active = t
    nt.nodes.new('ShaderNodeBsdfPrincipled')
for m in list(ATLAS_OF) + A_MATS + FLAT:
    if m in MAT:
        MAT[m].use_fake_user = True
_nobake = [m for m in list(ATLAS_OF) + A_MATS if 'BAKE_COLOR' not in MAT[m].node_tree.nodes]
assert not _nobake, ('materials without bake nodes', _nobake)

MESHES = [o for o in O if o.type == 'MESH']
for o in MESHES:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    o.data.uv_layers[0].name = 'UVMap'
    o.data.uv_layers.active_index = 0
    o.data.uv_layers[0].active_render = True


# ------------------------------------------------------------------ Airframe UVs from the v4 bake (geometry unchanged)
def world_of(ob):
    """world matrix of an appended (not linked, never evaluated) object from its basis + parent chain"""
    m = ob.matrix_basis.copy()
    while ob.parent is not None:
        m = ob.parent.matrix_basis @ ob.matrix_parent_inverse @ m
        ob = ob.parent
    return m


def transfer_airframe():
    with bpy.data.libraries.load(REF, link=False) as (src, dst):
        names = [n for n in src.objects]
        dst.objects = names
    ref = {}
    for ob in dst.objects:
        if ob is None or ob.type != 'MESH':
            continue
        nm = ob.name.rsplit('.', 1)[0] if ob.name[-4:-3] == '.' and ob.name[-3:].isdigit() else ob.name
        ref[nm] = ob
    tot = miss = 0
    for o in MESHES:
        names = [m.name if m else '' for m in o.data.materials]
        if not any(n in A_MATS for n in names):
            continue
        r = ref.get(o.name)
        if r is None:
            print('  WARN no reference object for', o.name)
            continue
        rme, rmw = r.data, world_of(r)
        rnames = [m.name.split('.')[0] if m else '' for m in rme.materials]
        rv = [rmw @ v.co for v in rme.vertices]
        kd = kdtree.KDTree(len(rme.polygons))
        for p in rme.polygons:
            kd.insert(sum((rv[i] for i in p.vertices), Vector()) / len(p.vertices), p.index)
        kd.balance()
        ruv = rme.uv_layers[0].data
        me, mw = o.data, o.matrix_world
        vv = [mw @ v.co for v in me.vertices]
        uv = me.uv_layers[0].data
        m0, t0_ = miss, tot
        for p in me.polygons:
            if p.material_index >= len(names) or names[p.material_index] not in A_MATS:
                continue
            tot += 1
            c = sum((vv[i] for i in p.vertices), Vector()) / len(p.vertices)
            co, ri, dist = kd.find(c)
            rp = rme.polygons[ri]
            if dist > 2e-4 or rp.loop_total != p.loop_total or rnames[rp.material_index] != names[p.material_index]:
                miss += 1
                continue
            for li in p.loop_indices:
                pv = vv[me.loops[li].vertex_index]
                best = min(rp.loop_indices, key=lambda rl: (rv[rme.loops[rl].vertex_index] - pv).length)
                uv[li].uv = ruv[best].uv
        if miss - m0:
            print(f'  {o.name}: {miss - m0}/{tot - t0_} airframe faces unmatched', flush=True)
    for ob in list(dst.objects):
        if ob is not None:
            bpy.data.objects.remove(ob)
    print(f'airframe UV transfer: {tot - miss}/{tot} faces matched', flush=True)
    return tot, miss


tot, miss = transfer_airframe()
assert miss <= max(20, tot // 500), 'airframe geometry changed - rebake the Airframe atlas'

# ------------------------------------------------------------------ UV unwrap per atlas (face selection by material)
SCALE = {
    'C': {'CP_Panel': 2.2, 'CP_Radios': 2.2, 'CP_Switchgear': 2.2, 'CP_PanelFrame': 1.3, 'CP_Glareshield': 1.5,
          'CP_Pedestal': 1.8, 'CP_Gauges': 1.6, 'CP_Overhead': 1.6, 'CP_Compass_Vents': 1.6, 'CP_Headsets': 1.0,
          'CP_RearKit': 0.6, 'CP_PedalLinkage': 0.8, 'CP_YokeBoot_P': 1.5, 'CP_YokeBoot_C': 1.5, 'CP_Placards': 1.0,
          'CP_PanelBack': 0.05, 'CP_Glovebox': 1.0, 'Glovebox_Lid': 1.4, 'Guard_Starter': 2.0},
    'I': {'CP_Headliner': 0.8, 'CP_Bulkheads': 0.75, 'PilotDoor_L': 1.25, 'PilotDoor_R': 1.25, 'CP_WindshieldFrame': 1.2},
    'F': {'CP_DoorSeals': 0.6, 'CP_Floor': 1.0},
    'S': {'Belt_P_On': 1.3, 'Belt_C_On': 1.3, 'Belt_P_Off': 1.3, 'Belt_C_Off': 1.3},
    'D': {'Propeller': 1.2, 'PropBlade_1': 1.4, 'PropBlade_2': 1.4, 'PropBlade_3': 1.4, 'Wheel_L': 1.3, 'Wheel_R': 1.3,
          'TailWheel': 1.2, 'Lock_PilotDoor_L': 2.0, 'Lock_PilotDoor_R': 2.0, 'src_PlaneKey': 2.0},
}
MAT_SCALE = {'src_CabinWall': 0.05, 'src_DoorPanel': 0.06, 'src_IN_Hidden': 0.04}
PREFIX2 = ('Needle', 'SW_', 'Lever', 'Yoke', 'Pedal', 'Rheo', 'Pull', 'FuelSel', 'ATT', 'HDG', 'TC_', 'Clock', 'Trim',
           'Btn_', 'Guard')


def scale_of(atlas, o):
    s = SCALE[atlas].get(o.name)
    if s is not None:
        return s
    if atlas == 'C' and o.name.startswith(PREFIX2):
        return 2.0 if not o.name.startswith(('Yoke', 'Pedal')) else 1.5
    return 1.0


MARGIN_PX = 8
FINAL_RES = dict(C=4096, I=4096, F=4096, S=4096, D=4096)          # v7: Details 4K


def unwrap(atlas):
    mats = BAKED[atlas]
    objs = [o for o in MESHES if o.name not in GLASS_OBJS and
            any(p.material_index < len(o.data.materials) and o.data.materials[p.material_index] and
                o.data.materials[p.material_index].name in mats for p in o.data.polygons)]
    if not objs:
        return []
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
    bpy.ops.mesh.hide(unselected=True)
    bpy.ops.uv.smart_project(angle_limit=math.radians(68), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    for o in objs:
        f_ = scale_of(atlas, o)
        bm = bmesh.from_edit_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        names = [m.name if m else '' for m in o.data.materials]
        for f in bm.faces:
            if not f.select:
                continue
            k = f_ * MAT_SCALE.get(names[f.material_index], 1.0)
            if abs(k - 1.0) > 1e-6:
                for lp in f.loops:
                    lp[uvl].uv *= k
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=MARGIN_PX / FINAL_RES[atlas],
                            shape_method='CONCAVE', scale=True)
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        names = [m.name if m else '' for m in o.data.materials]
        uv = o.data.uv_layers[0].data
        for p in o.data.polygons:
            if p.material_index < len(names) and names[p.material_index] in mats:
                for li in p.loop_indices:
                    u, v = uv[li].uv
                    assert -1e-4 <= u <= 1.0001 and -1e-4 <= v <= 1.0001, (atlas, o.name, u, v)
    return objs


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


def strap_uv_snapshot():
    o = O['CP_BarrierNets']
    return np.array([tuple(d.uv) for d in o.data.uv_layers[0].data])


def reuse_uvs(ref_path, atlases):
    """v6: copy the UVs of unchanged atlases from an earlier bake, so its textures stay valid and only the changed
    atlases are baked again. Faces are matched by centroid (+ material, corner count), corners by vertex position:
    face order is not stable between builds, the geometry is."""
    with bpy.data.libraries.load(ref_path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    ref = {}
    for ob in dst.objects:
        if ob is None or ob.type != 'MESH':
            continue
        nm = ob.name.rsplit('.', 1)[0] if ob.name[-4:-3] == '.' and ob.name[-3:].isdigit() else ob.name
        ref[nm] = ob
    mats = {m for a in atlases for m in BAKED[a]} | {m for a in atlases for m in
                                                     {'C': [], 'I': I_MATS0, 'F': F_MATS0, 'S': S_MATS0, 'D': D_MATS0}[a]}
    n_obj = n_faces = 0
    bad = []
    for o in MESHES:
        names = [m.name if m else '' for m in o.data.materials]
        faces = [p for p in o.data.polygons if p.material_index < len(names) and names[p.material_index] in mats]
        if not faces:
            continue
        r = ref.get(o.name)
        if r is None:
            bad.append((o.name, 'missing in reference'))
            continue
        rme, rmw = r.data, world_of(r)
        rn = [m.name.split('.')[0] if m else '' for m in rme.materials]
        rv = [rmw @ v.co for v in rme.vertices]
        rfaces = [p for p in rme.polygons if p.material_index < len(rn) and rn[p.material_index] in mats]
        kd = kdtree.KDTree(len(rfaces))
        for i, p in enumerate(rfaces):
            kd.insert(sum((rv[k] for k in p.vertices), Vector()) / len(p.vertices), i)
        kd.balance()
        mw = o.matrix_world
        vv = [mw @ v.co for v in o.data.vertices]
        uv, ruv = o.data.uv_layers[0].data, rme.uv_layers[0].data
        miss = 0
        for p in faces:
            c = sum((vv[k] for k in p.vertices), Vector()) / len(p.vertices)
            q = None
            for co, ri, dist in kd.find_n(c, 6):
                cand = rfaces[ri]
                if dist <= 2e-4 and cand.loop_total == p.loop_total and \
                        rn[cand.material_index] == names[p.material_index]:
                    q = cand
                    break
            if q is None:
                miss += 1
                continue
            for li in p.loop_indices:
                pv = vv[o.data.loops[li].vertex_index]
                lj = min(q.loop_indices, key=lambda l: (rv[rme.loops[l].vertex_index] - pv).length)
                uv[li].uv = ruv[lj].uv
            n_faces += 1
        if miss:
            bad.append((o.name, f'{miss}/{len(faces)} faces unmatched'))
        n_obj += 1
    for ob in list(dst.objects):
        if ob is not None:
            bpy.data.objects.remove(ob)
    print(f'reused {atlases} UVs from {os.path.basename(ref_path)}: {n_obj} objects, {n_faces} faces', flush=True)
    assert not bad, ('cannot reuse', bad)


I_MATS0, F_MATS0, S_MATS0, D_MATS0 = (['src_IN_Hidden'], [], [], [])   # materials that may have left the scene
t0 = time.time()
g0, s0 = gauge_uv_snapshot(), strap_uv_snapshot()
REUSE = os.environ.get('REUSE', '')
for a in 'CIFSD':
    if a in REUSE:
        continue
    unwrap(a)
    print('unwrapped', a, round(time.time() - t0, 1), 's', flush=True)
if REUSE:
    reuse_uvs(os.path.join(HERE, os.environ.get('REUSE_FROM', 'out/plane_v6_src_v6.blend')), REUSE)
for oname, arr in g0.items():
    o = O[oname]
    names = [m.name if m else '' for m in o.data.materials]
    gi = names.index('src_CP_Gauges')
    uv = o.data.uv_layers[0].data
    idx = [li for p in o.data.polygons if p.material_index == gi for li in p.loop_indices]
    for i, (u, v) in zip(idx, arr):
        uv[i].uv = (u, v)
assert all(np.allclose(g0[k], gauge_uv_snapshot()[k]) for k in g0)
assert np.allclose(s0, strap_uv_snapshot())
print('uv done', round(time.time() - t0, 1), 's; gauge + webbing UVs intact', flush=True)
if os.environ.get('UVONLY'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_uv_{TAG}.blend'))
    sys.exit(0)
if 'D' not in REUSE or 'C' not in REUSE:                          # fresh unwrap: keep it for a resumed run
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_uv_{TAG}_run.blend'), copy=True)
    print('saved uv blend for resume', flush=True)


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
IM = {}


def set_output(mt, node_name):
    nt = mt.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    src = nt.nodes[node_name] if node_name else next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(src.outputs[0], out.inputs['Surface'])


BAKE_OBJS = [o.name for o in MESHES if o.name not in GLASS_OBJS and o.name not in ('src_Lights', 'PropBlur', 'PropDisc')
             and len(o.data.polygons)]
PROP_PARTS = ['Propeller', 'PropBlade_1', 'PropBlade_2', 'PropBlade_3']
AO_RES = {a: max(256, RES[a] // 2) for a in 'CIFSD'}


def objs_with(atl):
    r = []
    for n in BAKE_OBJS:
        names = [m.name if m else '' for m in O[n].data.materials]
        if any((ATLAS_OF.get(names[p.material_index]) or '_') in atl for p in O[n].data.polygons
               if p.material_index < len(names)):
            r.append(n)
    return r


def bake(pname, samples=1, names=None, clear=True, margin=None, save=True, atlases='CIFSD', res=None):
    typ, node, noncolor, fbuf = PASSES[pname]
    res = res or RES
    for a in atlases:
        if clear or (a, pname) not in IM:
            IM[(a, pname)] = img(f'T_{ATLAS_NAME[a]}_{pname}', res[a], noncolor, fbuf)
    for mname, a in ATLAS_OF.items():
        mt = MAT[mname]
        set_output(mt, node)
        t = mt.node_tree.nodes['BAKE_TARGET']
        t.image = IM[(a, pname)] if a in atlases else dummy
        mt.node_tree.nodes.active = t
    for mname in A_MATS:                                   # airframe faces: never written (dummy target)
        mt = MAT[mname]
        set_output(mt, node)
        t = mt.node_tree.nodes['BAKE_TARGET']
        t.image = dummy
        mt.node_tree.nodes.active = t
    for mname in FLAT:
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
    names = names or objs_with(atlases)
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


def free(a, pname):
    im = IM.pop((a, pname), None)
    if im is not None:
        bpy.data.images.remove(im)


SKIP = {x for x in os.environ.get('SKIP', '').split(',') if x}     # resume after a crash: 'C:BaseColor,D:MR' = done


def bake_each(pname, atlases='CIFSD', **kw):
    """one atlas per bake call: four 4K targets at once exceed the 6 GB memory limit"""
    for a in atlases:
        if f'{a}:{pname}' in SKIP:
            print('skip', a, pname, flush=True)
            continue
        names = objs_with(a)
        if names:
            bake(pname, names=names, atlases=a, **kw)
        free(a, pname)


if not sc.world:
    sc.world = bpy.data.worlds.new('World')
only = os.environ.get('PASSES', 'BaseColor,MR,Normal,AO').split(',')
ATL = os.environ.get('ATLASES', 'CIFSD')
if 'BaseColor' in only:
    bake_each('BaseColor', atlases=ATL)
if 'MR' in only:
    bake_each('MR', atlases=ATL, res={a: max(256, RES[a] // 2) for a in RES})   # low-frequency: half res
if 'Normal' in only:
    bake_each('Normal', atlases=ATL)
if 'AO' in only:
    for g in GLASS_OBJS:
        O[g].hide_render = True
    for n in PROP_PARTS + ['PropBlur', 'PropDisc']:
        O[n].hide_render = True
    sc.world.light_settings.distance = 0.6
    if 'D' in ATL and 'D:AO' not in SKIP:
        bake('AO', samples=AO_S, names=[n for n in objs_with('D') if n not in PROP_PARTS], save=False, atlases='D',
             res=AO_RES)
        for n in PROP_PARTS:
            O[n].hide_render = False
        bake('AO', samples=AO_S, names=PROP_PARTS, clear=False, margin=2, atlases='D', res=AO_RES)
        free('D', 'AO')
        for n in PROP_PARTS:
            O[n].hide_render = True
    sc.world.light_settings.distance = 0.22
    bake_each('AO', atlases=''.join(a for a in 'CIFS' if a in ATL), samples=AO_S, res=AO_RES)
    for n in PROP_PARTS:
        O[n].hide_render = False
for g in GLASS_OBJS:
    O[g].hide_render = False
for mname in list(ATLAS_OF) + A_MATS:
    set_output(MAT[mname], None)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_src_{TAG}.blend'))
print('saved src blend', flush=True)
