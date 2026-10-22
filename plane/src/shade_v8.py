"""v8 UVs + geometry bakes.
usage: python3 shade_v8.py <tag> [ao_samples=48]
 - opens out/plane_v8.blend (ext_v8.py), splits the door glass, reuses the Cockpit / Interior / Floor / Seats / Details
   UVs of the v7 bake (out/plane_v7_uv_v7final.blend; the antenna mesh by loop index, its vertices only moved)
 - new airframe UVs in two 4K atlases: A = Airframe (fuselage, doors, tail, dorsal, struts, wing details, fuel caps),
   W = Wing (wing box, TE pieces, flaps, ailerons, stabiliser, elevators: the lifting surfaces). Large lofted parts: seams on creases (> 50 deg) + explicit cuts
   (fuselage top / bottom centre lines and the y -3.35 / 1.50 rings, wing x 0 / +-3.895, stabiliser x 0), angle-based
   unwrap; small parts (fittings, VGs, canoes, rings, handle, caps): smart project. Hidden faces get less space.
   The packed UVs are saved to out/plane_v8_uv_<tag>.blend (Blender's pack is not deterministic: a resumed run
   passes REUSE_UV=1 to load them instead of unwrapping again).
 - bakes (Cycles, float images -> .npy in tex/<tag>/), resumable with SKIP=A:pos,W:nrm,...:
     A/W: pos (world position, rest pose, 4K), nrm (shading normal, 4K), id (R part code, G material code, B v8zone,
          A coverage; margin 0), ao (0.45 m, 2K)
     C/I/F/S: aos (0.22 m, as v7) and aol (4 m: sky visibility through the windows, the cabin's large-scale AO), 2K;
     loose props (cargo cases, ladder, key), glass and the prop blades are hidden for every AO bake.
 - saves out/plane_v8_src_<tag>.blend"""
import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector, kdtree

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'v8'
AO_S = int(sys.argv[2]) if len(sys.argv) > 2 else 48
TEX = os.path.join(HERE, 'tex', TAG)
os.makedirs(TEX, exist_ok=True)
UVBLEND = os.path.join(HERE, 'out', f'plane_v8_uv_{TAG}.blend')
REUSE_UV = os.environ.get('REUSE_UV') == '1'
bpy.ops.wm.open_mainfile(filepath=UVBLEND if REUSE_UV else os.path.join(HERE, 'out', 'plane_v8.blend'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
O, MAT = bpy.data.objects, bpy.data.materials
SKIP = {x for x in os.environ.get('SKIP', '').split(',') if x}
t00 = time.time()


def log(*a):
    print(f'[{time.time() - t00:7.1f}s]', *a, flush=True)


# ------------------------------------------------------------------ part codes (ID bake R channel)
PCODE = {'src_Fuselage': 1, 'src_Wing': 2, 'src_WingTE_Center': 3, 'src_WingTE_TipL': 4, 'src_WingTE_TipR': 5,
         'Flap_L': 6, 'Flap_R': 7, 'Aileron_L': 8, 'Aileron_R': 9, 'src_Fin': 10, 'Rudder': 11, 'src_Dorsal': 12,
         'src_Stabilizer': 13, 'Elevator_L': 14, 'Elevator_R': 15, 'PilotDoor_L': 16, 'PilotDoor_R': 17,
         'CargoDoor_L': 18, 'CargoDoor_R': 19, 'src_Struts': 20, 'src_WingDetails': 21, 'FuelCap_L': 22,
         'FuelCap_R': 23}
MCODE = {'src_Livery': 0, 'src_Seal': 1, 'src_Struts': 2}
A_MATS = list(MCODE)
W_OBJS = {'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'Flap_L', 'Flap_R', 'Aileron_L',
          'Aileron_R', 'src_Stabilizer', 'Elevator_L', 'Elevator_R'}
for k, v in PCODE.items():
    O[k]['pcode'] = float(v)

DOORS = ('PilotDoor_L', 'PilotDoor_R', 'CargoDoor_L', 'CargoDoor_R')


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


if not REUSE_UV:
    for d in DOORS:
        split_by_material(O[d], 'src_Glass', d + '__Glass')
GLASS_OBJS = ['src_GlassFixed'] + [d + '__Glass' for d in DOORS]

# ------------------------------------------------------------------ atlas membership (v7 lists for C / I / F / S / D)
D_MATS = ['src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark', 'src_Antenna',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal',
          'src_Brake', 'src_Caliper', 'src_Alu', 'src_LadderTread', 'src_KeyMetal', 'src_KeyFob']
UNBAKED = ['src_Glass', 'src_CP_GaugeGlass', 'src_CP_Gauges', 'src_CP_Net', 'src_CP_Annun', 'src_IN_Webbing',
           'src_CP_Screen', 'src_PropBlur', 'src_PropDisc']
I_MATS = ['src_IN_Liner', 'src_IN_Headliner', 'src_IN_Insul', 'src_IN_Composite', 'src_IN_Vinyl', 'src_IN_Hidden',
          'src_CabinWall', 'src_DoorPanel']
F_MATS = ['src_IN_Tread', 'src_IN_FloorPaint', 'src_IN_Track', 'src_IN_Kick', 'src_IN_Steel', 'src_IN_Trim',
          'src_IN_Seal']
S_MATS = [m.name for m in MAT if m.name.startswith('src_ST_')]
C_MATS = [m.name for m in MAT if m.name.startswith('src_CP_') and m.name not in UNBAKED]
MESHES = [o for o in O if o.type == 'MESH']
used = set()
for o in MESHES:
    ms = o.data.materials
    used |= {ms[p.material_index].name for p in o.data.polygons if p.material_index < len(ms) and ms[p.material_index]}
I_MATS, F_MATS, S_MATS, C_MATS = ([m for m in L if m in MAT and m in used] for L in (I_MATS, F_MATS, S_MATS, C_MATS))
D_MATS = [m for m in D_MATS if m in MAT]
BAKED = {'C': C_MATS, 'I': I_MATS, 'F': F_MATS, 'S': S_MATS, 'D': D_MATS}
ATLAS_OF = {m: a for a, L in BAKED.items() for m in L}
log('atlases', {a: len(L) for a, L in BAKED.items()})

for o in MESHES:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    o.data.uv_layers[0].name = 'UVMap'
    o.data.uv_layers.active_index = 0
    o.data.uv_layers[0].active_render = True


def world_of(ob):
    m = ob.matrix_basis.copy()
    while ob.parent is not None:
        m = ob.parent.matrix_basis @ ob.matrix_parent_inverse @ m
        ob = ob.parent
    return m


def face_atlas(o):
    """per-face atlas letter ('A', 'W', 'C', 'I', 'F', 'S', 'D' or '')"""
    names = [m.name if m else '' for m in o.data.materials]
    out = []
    for p in o.data.polygons:
        n = names[p.material_index] if p.material_index < len(names) else ''
        if n in MCODE:
            out.append('W' if o.name in W_OBJS else 'A')
        else:
            out.append(ATLAS_OF.get(n, ''))
    return out


# ------------------------------------------------------------------ reuse the v7 UVs of C / I / F / S / D
COPY_BY_INDEX = {'src_Antennas'}


def reuse_v7(ref_path):
    with bpy.data.libraries.load(ref_path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    ref = {}
    for ob in dst.objects:
        if ob is None or ob.type != 'MESH':
            continue
        nm = ob.name.rsplit('.', 1)[0] if ob.name[-4:-3] == '.' and ob.name[-3:].isdigit() else ob.name
        ref[nm] = ob
    n_obj = n_faces = 0
    bad = []
    for o in MESHES:
        fa = face_atlas(o)
        faces = [p for p, a in zip(o.data.polygons, fa) if a in 'CIFSD' and a]
        if not faces:
            continue
        r = ref.get(o.name)
        if r is None:
            bad.append((o.name, 'missing in reference'))
            continue
        uv, ruv = o.data.uv_layers[0].data, r.data.uv_layers[0].data
        if o.name in COPY_BY_INDEX:
            assert len(o.data.loops) == len(r.data.loops) and len(o.data.polygons) == len(r.data.polygons), o.name
            for p in faces:
                for li in p.loop_indices:
                    uv[li].uv = ruv[li].uv
            n_obj += 1
            n_faces += len(faces)
            continue
        rme, rmw = r.data, world_of(r)
        rn = [m.name.split('.')[0] if m else '' for m in rme.materials]
        rv = [rmw @ v.co for v in rme.vertices]
        rfaces = [p for p in rme.polygons if p.material_index < len(rn) and ATLAS_OF.get(rn[p.material_index])]
        kd = kdtree.KDTree(len(rfaces))
        for i, p in enumerate(rfaces):
            kd.insert(sum((rv[k] for k in p.vertices), Vector()) / len(p.vertices), i)
        kd.balance()
        mw = o.matrix_world
        vv = [mw @ v.co for v in o.data.vertices]
        names = [m.name if m else '' for m in o.data.materials]
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
    log(f'reused CIFSD UVs from {os.path.basename(ref_path)}: {n_obj} objects, {n_faces} faces')
    assert not bad, ('cannot reuse', bad)


# ------------------------------------------------------------------ airframe unwrap
MARGIN_PX, RES_A = 10, 4096
SEAM_ANGLE = math.radians(50)
SEAM_ANGLE_FOLLOW = math.radians(75)                     # lofts: keep the leading edge inside one island
SMART_ZONES = {'src_Struts': {1}, 'src_WingDetails': {1, 3, 4, 5, 6, 7, 8, 9}}     # v8zone values -> smart project
SMART_OBJS = {'FuelCap_L', 'FuelCap_R'}
LOW = 0.35                                                # texel scale for faces nobody sees closely


sys.path.insert(0, HERE)
import layout as LY
_ST = LY.fuselage_stations()


def _side_mid(p):
    """vertex on the mid-height side line (ring point 0 / 20) of a cowl or tail-cone station"""
    for y, zb, zt, hw, _n in _ST:
        if abs(p.y - y) < 1e-4:
            return abs(abs(p.x) - hw) < 2e-3 and abs(p.z - (zb + zt) / 2) < 2e-3
    return False


def cut_pred(name):
    """explicit seam edges (world-space vertex pairs) per object"""
    if name == 'src_Fuselage':
        def f(a, b):
            if abs(a.x) < 1e-4 and abs(b.x) < 1e-4:
                return True                                  # top / bottom centre lines
            if any(abs(a.y - yc) < 1e-4 and abs(b.y - yc) < 1e-4 for yc in (-3.35, 1.50)):
                return True                                  # cowl / cabin / tail-cone joints
            if (a.y < -3.34 and b.y < -3.34) or (a.y > 1.49 and b.y > 1.49):
                return _side_mid(a) and _side_mid(b)         # cowl and tail cone: quarter shells
            return False
        return f
    if name == 'src_Wing':
        return lambda a, b: any(abs(a.x - xc) < 1e-4 and abs(b.x - xc) < 1e-4 for xc in (0.0, 3.895, -3.895))
    if name == 'src_Stabilizer':
        return lambda a, b: abs(a.x) < 1e-4 and abs(b.x) < 1e-4
    return None


def low_face(name, c, n):
    """faces hidden in normal use: spar / hinge faces, root caps, the cowl front behind the spinner"""
    if name == 'src_Wing' and n.y > 0.9:
        return True                                          # rear spar face (behind the flaps / ailerons)
    if name in ('Flap_L', 'Flap_R', 'Aileron_L', 'Aileron_R', 'src_WingTE_Center', 'src_WingTE_TipL',
                'src_WingTE_TipR', 'Elevator_L', 'Elevator_R') and n.y < -0.9:
        return True                                          # hinge-side front faces
    if name == 'Rudder' and n.y < -0.9:
        return True
    if name in ('src_Fin', 'src_Stabilizer') and n.y > 0.9:
        return True                                          # hinge faces
    if name == 'src_Fin' and n.z < -0.9:
        return True                                          # root cap inside the tail cone
    if name == 'src_Fuselage' and n.y < -0.95 and c.y < -4.5:
        return True                                          # cowl front face behind the spinner
    if name == 'src_Dorsal' and (n.z < -0.8 or abs(n.y) > 0.95):
        return True                                          # buried bottom strip and end caps
    return False


FOLLOW = {'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'Flap_L', 'Flap_R', 'Aileron_L',
          'Aileron_R', 'src_Stabilizer', 'Elevator_L', 'Elevator_R', 'src_Fin', 'Rudder', 'src_Dorsal', 'src_Struts'}
SEAL_SCALE = 0.5


def islands_of(o, faces):
    """connected face sets through non-seam edges, restricted to `faces`"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    seen, out = set(), []
    for i in faces:
        if i in seen:
            continue
        stack, comp = [i], []
        seen.add(i)
        while stack:
            f = bm.faces[stack.pop()]
            comp.append(f.index)
            for e in f.edges:
                if e.seam:
                    continue
                for g in e.link_faces:
                    if g.index in faces and g.index not in seen:
                        seen.add(g.index)
                        stack.append(g.index)
        quads = all(len(bm.faces[k].verts) == 4 for k in comp)
        area = sum(bm.faces[k].calc_area() for k in comp)
        out.append((comp, quads, area))
    bm.free()
    return out


def follow_quads(o, comp):
    """lay a quad-grid island out as a rectangle grid (active quad = the largest one, set to an exact rectangle)"""
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal(select=False)
    bm = bmesh.from_edit_mesh(o.data)
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    cs = set(comp)
    for f in bm.faces:
        f.select_set(f.index in cs)
    best = max((bm.faces[i] for i in comp), key=lambda f: f.calc_area())
    l = best.loops
    e01 = (l[1].vert.co - l[0].vert.co).length
    e12 = (l[2].vert.co - l[1].vert.co).length
    for lp, uv in zip(l, ((0, 0), (e01, 0), (e01, e12), (0, e12))):
        lp[uvl].uv = uv
    bm.faces.active = best
    bmesh.update_edit_mesh(o.data)
    bpy.ops.mesh.hide(unselected=True)
    bpy.ops.uv.follow_active_quads(mode='LENGTH_AVERAGE')
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def uv_area(objs, atlas):
    tot = 0.0
    for o in objs:
        uv = o.data.uv_layers[0].data
        for p, a in zip(o.data.polygons, face_atlas(o)):
            if a != atlas:
                continue
            pts = [uv[li].uv for li in p.loop_indices]
            tot += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                           for i in range(len(pts)))) / 2
    return tot


def unwrap_airframe():
    objs = [o for o in MESHES if o.name not in GLASS_OBJS and any(a in 'AW' and a for a in face_atlas(o))]
    sel_big, sel_small = {}, {}
    for o in objs:
        fa = face_atlas(o)
        mw = o.matrix_world
        zl = o.data.attributes.get('v8zone')
        smart = SMART_ZONES.get(o.name, set())
        names = [m.name if m else '' for m in o.data.materials]
        big, small = set(), set()
        for p, a in zip(o.data.polygons, fa):
            if a not in ('A', 'W'):
                continue
            z = round(zl.data[p.index].value) if zl is not None else 0
            seal = names[p.material_index] == 'src_Seal'
            if o.name in SMART_OBJS or z in smart or seal:
                small.add(p.index)
            else:
                big.add(p.index)
        # small closed pieces (door handles, trim-tab horns): smart project instead of a seamless unwrap
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        seen = set()
        for i in sorted(big):
            if i in seen:
                continue
            stack, comp = [i], []
            seen.add(i)
            while stack:
                f = bm.faces[stack.pop()]
                comp.append(f.index)
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index in big and g.index not in seen:
                            seen.add(g.index)
                            stack.append(g.index)
            if sum(bm.faces[k].calc_area() for k in comp) < 0.05:
                big -= set(comp)
                small |= set(comp)
        sel_big[o.name], sel_small[o.name] = big, small
        # seams: creases inside the selection + explicit cuts (+ n-gon caps of the lofted parts)
        cp = cut_pred(o.name)
        lim = SEAM_ANGLE_FOLLOW if o.name in FOLLOW else SEAM_ANGLE
        for e in bm.edges:
            e.seam = False
            lf = [f for f in e.link_faces if f.index in big]
            if len(lf) == 2:
                if e.calc_face_angle(0.0) > lim:
                    e.seam = True
                elif o.name in FOLLOW and any(len(f.verts) > 4 for f in lf):
                    e.seam = True
                elif cp is not None and cp(mw @ e.verts[0].co, mw @ e.verts[1].co):
                    e.seam = True
        bm.to_mesh(o.data)
        bm.free()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    def select_faces(which):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.reveal(select=False)
        for o in objs:
            bm = bmesh.from_edit_mesh(o.data)
            s = which[o.name]
            for f in bm.faces:
                f.select_set(f.index in s)
            bmesh.update_edit_mesh(o.data)
        bpy.ops.mesh.hide(unselected=True)

    select_faces(sel_big)
    bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.0)
    log('angle-based unwrap done')
    bpy.ops.object.mode_set(mode='OBJECT')
    select_faces(sel_small)
    bpy.ops.uv.smart_project(angle_limit=math.radians(40), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    log('smart project done')
    bpy.ops.object.mode_set(mode='OBJECT')
    n_follow = 0
    for o in objs:                                   # lofted quad grids -> rectangular islands
        if o.name not in FOLLOW or not sel_big[o.name]:
            continue
        for comp, quads, area in islands_of(o, sel_big[o.name]):
            if quads and len(comp) >= 8 and area > 0.02:
                follow_quads(o, comp)
                n_follow += 1
    log('follow active quads:', n_follow, 'islands')
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for atlas in ('A', 'W'):
        which = {}
        for o in objs:
            fa = face_atlas(o)
            which[o.name] = {i for i, a in enumerate(fa) if a == atlas}
        select_faces(which)
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
        for o in objs:
            if not which[o.name]:
                continue
            bm = bmesh.from_edit_mesh(o.data)
            uvl = bm.loops.layers.uv.active
            mw = o.matrix_world
            nm3 = mw.to_3x3().inverted().transposed()
            names = [m.name if m else '' for m in o.data.materials]
            zl8 = bm.faces.layers.float.get('v8zone')
            for f in bm.faces:
                if not f.select:
                    continue
                c = mw @ f.calc_center_median()
                n = (nm3 @ f.normal).normalized()
                k = LOW if low_face(o.name, c, n) else 1.0
                if names[f.material_index] == 'src_Seal':
                    k *= SEAL_SCALE
                if zl8 is not None and round(f[zl8]) == 7:      # vortex generators: 108 tiny fins
                    k *= 0.5
                if k != 1.0:
                    for lp in f.loops:
                        lp[uvl].uv *= k
            bmesh.update_edit_mesh(o.data)
        bpy.ops.object.mode_set(mode='OBJECT')
        snap = {o.name: np.array([tuple(d.uv) for d in o.data.uv_layers[0].data]) for o in objs if which[o.name]}
        best = None
        for method in ('AXIS_ALIGNED', 'ANY'):
            for o in objs:
                if o.name in snap:
                    o.data.uv_layers[0].data.foreach_set('uv', snap[o.name].ravel())
            select_faces(which)
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(rotate=True, rotate_method=method, margin_method='FRACTION',
                                    margin=MARGIN_PX / RES_A, shape_method='CONCAVE', scale=True)
            bpy.ops.mesh.reveal(select=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            cov = uv_area(objs, atlas)
            log(f'packed {atlas} ({method}): UV coverage {cov * 100:.1f} %')
            if best is None or cov > best[0]:
                best = (cov, method, {o.name: np.array([tuple(d.uv) for d in o.data.uv_layers[0].data])
                                      for o in objs if which[o.name]})
        for o in objs:
            if o.name in best[2]:
                o.data.uv_layers[0].data.foreach_set('uv', best[2][o.name].ravel())
        log(f'atlas {atlas}: kept {best[1]} ({best[0] * 100:.1f} %)')
    for o in objs:
        fa = face_atlas(o)
        uv = o.data.uv_layers[0].data
        for p, a in zip(o.data.polygons, fa):
            if a in ('A', 'W'):
                for li in p.loop_indices:
                    u, v = uv[li].uv
                    assert -1e-4 <= u <= 1.0001 and -1e-4 <= v <= 1.0001, (o.name, u, v)


if not REUSE_UV:
    reuse_v7(os.path.join(HERE, 'out', 'plane_v7_uv_v7final.blend'))
    unwrap_airframe()
    bpy.ops.wm.save_as_mainfile(filepath=UVBLEND, copy=True)
    log('saved', os.path.basename(UVBLEND))
else:
    log('UVs loaded from', os.path.basename(UVBLEND))
if os.environ.get('UVONLY'):
    sys.exit(0)


# ------------------------------------------------------------------ bake materials
def target_node(mt):
    mt.use_nodes = True
    nt = mt.node_tree
    t = nt.nodes.get('BAKE_TARGET')
    if t is None:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.name = 'BAKE_TARGET'
    return t


DUMMY = bpy.data.images.new('BAKE_DUMMY', 8, 8)
GEO_OUT = {}                                             # material -> output node of the geometry tree


def geo_material(mt, code):
    """replace the node tree of an airframe material: emission = position / normal / id (switched per pass)"""
    mt.use_nodes = True
    nt = mt.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    geo = N.new('ShaderNodeNewGeometry')
    e_pos = N.new('ShaderNodeEmission')
    e_pos.name = 'E_POS'
    L.new(geo.outputs['Position'], e_pos.inputs['Color'])
    e_nrm = N.new('ShaderNodeEmission')
    e_nrm.name = 'E_NRM'
    L.new(geo.outputs['Normal'], e_nrm.inputs['Color'])
    pc = N.new('ShaderNodeAttribute')
    pc.attribute_type = 'OBJECT'
    pc.attribute_name = 'pcode'
    zn = N.new('ShaderNodeAttribute')
    zn.attribute_type = 'GEOMETRY'
    zn.attribute_name = 'v8zone'
    cmb = N.new('ShaderNodeCombineXYZ')
    L.new(pc.outputs['Fac'], cmb.inputs[0])
    cmb.inputs[1].default_value = float(code)
    L.new(zn.outputs['Fac'], cmb.inputs[2])
    e_id = N.new('ShaderNodeEmission')
    e_id.name = 'E_ID'
    L.new(cmb.outputs[0], e_id.inputs['Color'])
    t = N.new('ShaderNodeTexImage')
    t.name = 'BAKE_TARGET'
    t.image = DUMMY
    N.active = t
    GEO_OUT[mt.name] = out


for m, code in MCODE.items():
    geo_material(MAT[m], code)
for mt in MAT:
    if mt.name not in MCODE:
        t = target_node(mt)
        t.image = DUMMY
        mt.node_tree.nodes.active = t


def set_pass(pname):
    for m in MCODE:
        nt = MAT[m].node_tree
        out = GEO_OUT[m]
        for l in list(out.inputs['Surface'].links):
            nt.links.remove(l)
        src = {'pos': 'E_POS', 'nrm': 'E_NRM', 'id': 'E_ID'}.get(pname)
        if src:
            nt.links.new(nt.nodes[src].outputs[0], out.inputs['Surface'])


def objs_with(atlas):
    r = []
    for o in MESHES:
        if o.name in GLASS_OBJS or o.name in ('src_Lights', 'PropBlur', 'PropDisc') or not len(o.data.polygons):
            continue
        if atlas in face_atlas(o):
            r.append(o.name)
    return r


def new_image(name, res):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=True, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    im.generated_color = (0, 0, 0, 0)
    return im


def point_targets(atlas, im):
    """atlas materials write into im, everything else into the dummy"""
    for mt in MAT:
        nt = mt.node_tree if mt.use_nodes else None
        if nt is None or 'BAKE_TARGET' not in nt.nodes:
            continue
        t = nt.nodes['BAKE_TARGET']
        mine = (atlas in ('A', 'W') and mt.name in MCODE) or ATLAS_OF.get(mt.name) == atlas
        t.image = im if mine else DUMMY
        nt.nodes.active = t


def save_npy(im, path, channels, dtype):
    W, H = im.size
    buf = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(buf)
    arr = buf.reshape(H, W, 4)[::-1, :, :channels]            # row 0 = top of the image (v = 1)
    np.save(path, arr.astype(dtype))


HIDE_AO = GLASS_OBJS + ['PropBlade_1', 'PropBlade_2', 'PropBlade_3', 'PropBlur', 'PropDisc', 'src_StepLadder',
                        'Ladder_RearLegs', 'src_PlaneKey'] + [o.name for o in MESHES if o.name.startswith('src_Case')]


def bake(atlas, pname, res, typ, samples=1, margin=16, dist=None):
    key = f'{atlas}:{pname}'
    path = os.path.join(TEX, f'T8_{atlas}_{pname}.npy')
    if key in SKIP or (os.environ.get('RESUME') == '1' and os.path.exists(path)):
        log('skip', key)
        return
    im = new_image(f'T8_{atlas}_{pname}', res)
    point_targets(atlas, im)
    set_pass(pname)
    for n in HIDE_AO:
        if n in O:
            O[n].hide_render = typ == 'AO'
    if dist is not None:
        sc.world.light_settings.distance = dist
    sc.cycles.samples = samples
    bk = sc.render.bake
    bk.use_clear = True
    bk.margin = margin
    bk.margin_type = 'EXTEND'
    bk.target = 'IMAGE_TEXTURES'
    names = objs_with(atlas)
    bpy.ops.object.select_all(action='DESELECT')
    for n in names:
        O[n].select_set(True)
    bpy.context.view_layer.objects.active = O[names[0]]
    t0 = time.time()
    bpy.ops.object.bake(type=typ)
    ch, dt = {'pos': (3, np.float32), 'nrm': (3, np.float16), 'id': (4, np.float16)}.get(pname, (1, np.float16))
    save_npy(im, path, ch, dt)
    bpy.data.images.remove(im)
    log('baked', key, res, round(time.time() - t0, 1), 's ->', os.path.basename(path))


if not sc.world:
    sc.world = bpy.data.worlds.new('World')
ONLY = os.environ.get('ATLASES', 'AWCIFS')
for a in 'AW':
    if a not in ONLY:
        continue
    bake(a, 'id', RES_A, 'EMIT', margin=0)
    bake(a, 'pos', RES_A, 'EMIT')
    bake(a, 'nrm', RES_A, 'EMIT')
    bake(a, 'ao', RES_A // 2, 'AO', samples=AO_S, margin=8, dist=0.45)
for a in 'CIFS':
    if a not in ONLY:
        continue
    bake(a, 'aos', 2048, 'AO', samples=AO_S, margin=8, dist=0.22)
    bake(a, 'aol', 2048, 'AO', samples=AO_S, margin=8, dist=4.0)
for n in HIDE_AO:
    if n in O:
        O[n].hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v8_src_{TAG}.blend'))
log('saved src blend')
