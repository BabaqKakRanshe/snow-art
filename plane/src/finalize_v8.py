"""v8 finalize: Unity textures + final materials.
usage: python3 finalize_v8.py [tag=v8]
 - opens out/plane_v8_uv_<tag>.blend (shade_v8.py UVs; the source materials are still the build ones)
 - writes Unity textures to export/unity_v8/Assets/UtilityPlane/Textures:
     T_Airframe_* and T_Wing_* (v8 livery, livery_v8.py): BaseColor (sRGB), Normal (OpenGL), MaskMap (linear:
       R metallic, G occlusion, B 1, A smoothness)
     T_Cockpit_* (v7 bake) and T_Interior_* / T_Floor_* / T_Seats_* (v6 bake) with a new occlusion channel: v8 AO
       baked without the loose props (cases, ladder, key) x the large cabin AO (sky visibility through the windows,
       4 m rays), see cabin_ao()
     T_Details_* unchanged (v7); gauges, displays, webbing, prop discs, grain / leather detail maps copied from v7
     T_Detail_Paint_Albedo / _Normal (new): paint micro-detail for M_Airframe / M_Wing (orange peel, fine scratches)
 - Data/atlas_texel.json (metres per UV unit, detail tiling) for all seven atlases
 - final materials M_Airframe (fuselage, doors, fin, rudder, dorsal, struts, wing details, fuel caps) and M_Wing (wing,
   TE pieces, flaps, ailerons, stabiliser, elevators) - assigned per object - plus the v7 set; saves
   out/plane_v8_final_<tag>.blend"""
import bpy, bmesh, os, sys, math, json, shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'v8'
TEX8 = os.path.join(HERE, 'tex', TAG)
OUT = os.path.join(HERE, 'export', 'unity_v8', 'Assets', 'UtilityPlane')
V7T = os.path.join(HERE, 'export', 'unity_v7', 'Assets', 'UtilityPlane', 'Textures')
UT, DATA = os.path.join(OUT, 'Textures'), os.path.join(OUT, 'Data')
for d in (UT, DATA):
    os.makedirs(d, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v8_uv_{TAG}.blend'))
O, MAT = bpy.data.objects, bpy.data.materials

W_OBJS = {'src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'Flap_L', 'Flap_R', 'Aileron_L',
          'Aileron_R', 'src_Stabilizer', 'Elevator_L', 'Elevator_R'}
A_MATS = ['src_Livery', 'src_Seal', 'src_Struts']
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
ATLAS = {'Cockpit': C_MATS, 'Interior': I_MATS, 'Floor': F_MATS, 'Seats': S_MATS, 'Details': D_MATS}
LETTER = {'Cockpit': 'C', 'Interior': 'I', 'Floor': 'F', 'Seats': 'S'}
SRC = {'Cockpit': os.path.join(HERE, 'tex', 'v7'), 'Interior': os.path.join(HERE, 'tex', 'v6'),
       'Floor': os.path.join(HERE, 'tex', 'v6'), 'Seats': os.path.join(HERE, 'tex', 'v6')}

# ------------------------------------------------------------------ cabin occlusion: small AO x large-scale AO
AOL_FLOOR, AOL_GAMMA = 0.50, 0.60          # ambient left in a fully enclosed corner; response curve (v7 G medians:
#   C 0.675, I 0.867, F 0.671 -> v8 about 0.44, 0.69, 0.52: deep corners darker, window areas unchanged)
CABIN_STATS = {}


def cabin_ao(letter, size):
    aos = np.load(os.path.join(TEX8, f'T8_{letter}_aos.npy')).astype(np.float32)[..., 0]
    aol = np.load(os.path.join(TEX8, f'T8_{letter}_aol.npy')).astype(np.float32)[..., 0]
    valid = aol > 0.0005
    ref = float(np.percentile(aol[valid], 92)) if valid.any() else 1.0
    big = AOL_FLOOR + (1 - AOL_FLOOR) * np.clip(aol / max(ref, 1e-3), 0, 1) ** AOL_GAMMA
    ao = np.clip(aos * big, 0, 1)
    CABIN_STATS[letter] = dict(aol_p92=round(ref, 3), aol_median=round(float(np.median(aol[valid])), 3),
                               result_median=round(float(np.median(ao[valid])), 3))
    im = Image.fromarray((ao * 255 + 0.5).astype(np.uint8), 'L')
    return np.asarray(im.resize(size, Image.BICUBIC))


def unity_textures(name):
    src = SRC[name]
    bc = Image.open(os.path.join(src, f'T_{name}_BaseColor.png')).convert('RGB')
    bc.save(os.path.join(UT, f'T_{name}_BaseColor.png'), optimize=True)
    n = np.asarray(Image.open(os.path.join(src, f'T_{name}_Normal.png'))).astype(np.float32)
    if n.max() > 255:
        n = n / 257.0
    Image.fromarray(n[..., :3].round().clip(0, 255).astype(np.uint8), 'RGB').save(
        os.path.join(UT, f'T_{name}_Normal.png'), optimize=True)
    mr = Image.open(os.path.join(src, f'T_{name}_MR.png')).convert('RGB')
    if mr.size != bc.size:
        mr = mr.resize(bc.size, Image.BICUBIC)
    mr = np.asarray(mr)
    ao = cabin_ao(LETTER[name], bc.size)
    mask = np.dstack([mr[..., 0], ao, np.full_like(ao, 255), 255 - mr[..., 1]]).astype(np.uint8)
    Image.fromarray(mask, 'RGBA').save(os.path.join(UT, f'T_{name}_MaskMap.png'), optimize=True)
    print('unity textures', name, bc.size, CABIN_STATS[LETTER[name]], flush=True)


for nm in ('Airframe', 'Wing'):
    for k in ('BaseColor', 'Normal', 'MaskMap'):
        shutil.copyfile(os.path.join(TEX8, f'T_{nm}_{k}.png'), os.path.join(UT, f'T_{nm}_{k}.png'))
for nm in ('Cockpit', 'Interior', 'Floor', 'Seats'):
    if os.environ.get('PREVIEW_CABIN_V7') == '1':                 # livery preview before the cabin AO bake exists
        for k in ('BaseColor', 'Normal', 'MaskMap'):
            shutil.copyfile(os.path.join(V7T, f'T_{nm}_{k}.png'), os.path.join(UT, f'T_{nm}_{k}.png'))
        continue
    unity_textures(nm)
for f in os.listdir(V7T):
    if f.startswith(('T_Details_', 'T_Gauges_', 'T_Displays_', 'T_Prop', 'T_Webbing_', 'T_Detail_')):
        shutil.copyfile(os.path.join(V7T, f), os.path.join(UT, f))


# ------------------------------------------------------------------ paint micro-detail (tiling, 512)
def height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    nx, ny = -gx * strength, gy * strength
    nz = np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([(nx / L + 1) * 127.5, (ny / L + 1) * 127.5, (nz / L + 1) * 127.5]).clip(0, 255).astype(np.uint8)


def tile_noise(res, freqs, seed, aniso=(1, 1)):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:res, 0:res] / res
    h = np.zeros((res, res))
    for f, amp in freqs:
        for _ in range(6):
            kx, ky = rng.integers(-f, f + 1) * aniso[0], rng.integers(-f, f + 1) * aniso[1]
            if kx == 0 and ky == 0:
                continue
            h += amp * np.sin(2 * np.pi * (kx * xx + ky * yy) + rng.uniform(0, 2 * np.pi))
    h -= h.min()
    return h / max(h.max(), 1e-9)


def paint_detail(res=512):
    peel = tile_noise(res, [(18, 1.0), (36, 0.55), (72, 0.3)], 21)              # orange peel
    scr = tile_noise(res, [(2, 1.0), (40, 0.25)], 23, aniso=(1, 9))             # faint wash scratches
    scr = np.clip((scr - 0.72) / 0.28, 0, 1) ** 2
    h = 0.85 * peel - 0.35 * scr
    Image.fromarray(height_to_normal(h, 1.2), 'RGB').save(os.path.join(UT, 'T_Detail_Paint_Normal.png'))
    alb = 128 + (peel - 0.5) * 6 + scr * 10
    Image.fromarray(alb.clip(0, 255).astype(np.uint8), 'L').convert('RGB').save(
        os.path.join(UT, 'T_Detail_Paint_Albedo.png'))


paint_detail()

# ------------------------------------------------------------------ metres per UV unit (detail tiling)
HIDDEN = ('src_CabinWall', 'src_DoorPanel', 'src_IN_Hidden')
DETAIL = {'Airframe': ('Paint', 0.05, 0.30), 'Wing': ('Paint', 0.05, 0.30),
          'Cockpit': ('Grain', 0.06, 0.4), 'Interior': ('Grain', 0.06, 0.6), 'Floor': ('Grain', 0.06, 0.3),
          'Seats': ('Leather', 0.08, 0.8)}


def atlas_of_face(ob, mname):
    if mname in A_MATS:
        return 'Wing' if ob.name in W_OBJS else 'Airframe'
    for a, L in ATLAS.items():
        if mname in L:
            return a
    return None


def texel_stats():
    acc = {}
    for ob in O:
        if ob.type != 'MESH' or not ob.data.uv_layers:
            continue
        names = [m.name if m else '' for m in ob.data.materials]
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        uvl = bm.loops.layers.uv[0]
        for f in bm.faces:
            n = names[f.material_index] if f.material_index < len(names) else ''
            a = atlas_of_face(ob, n)
            if a is None or n in HIDDEN:
                continue
            uv = [l[uvl].uv for l in f.loops]
            a2 = abs(sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y
                         for i in range(len(uv)))) / 2
            s = acc.setdefault(a, [0.0, 0.0])
            s[0] += f.calc_area()
            s[1] += a2
        bm.free()
    rows = []
    for atl in ('Airframe', 'Wing', 'Details', 'Cockpit', 'Interior', 'Floor', 'Seats'):
        a3, a2 = acc[atl]
        mpu = math.sqrt(a3 / a2)
        res = Image.open(os.path.join(UT, f'T_{atl}_BaseColor.png')).size[0]
        row = dict(atlas=atl, material='M_' + atl, metresPerUV=round(mpu, 4), pxPerMetre=round(res / mpu, 1),
                   areaM2=round(a3, 2), detail='', detailTiling=0.0, detailNormalScale=0.0)
        if atl in DETAIL:
            d, tile, ns = DETAIL[atl]
            row.update(detail=d, detailTiling=round(mpu / tile, 2), detailNormalScale=ns)
        rows.append(row)
    return rows


TEXEL = texel_stats()
json.dump(TEXEL, open(os.path.join(DATA, 'atlas_texel.json'), 'w'), indent=1)
json.dump(CABIN_STATS, open(os.path.join(TEX8, 'cabin_ao_stats.json'), 'w'), indent=1)
for r in TEXEL:
    print('texel', r, flush=True)


# ------------------------------------------------------------------ materials (preview / export names)
def load(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def new_mat(name):
    old = MAT.get(name)
    if old:
        old.name = name + '_old'
    m = MAT.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree.nodes, m.node_tree.links


def tex_node(N, im, x, y, vec=None, L=None):
    t = N.new('ShaderNodeTexImage')
    t.image = im
    t.location = (x, y)
    if vec is not None:
        L.new(vec, t.inputs['Vector'])
    return t


def pbr_material(name, bc_path, ms_path, n_path, tiling=None):
    m, N, L = new_mat(name)
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    L.new(pr.outputs[0], out.inputs[0])
    vec = None
    if tiling:
        tc = N.new('ShaderNodeTexCoord')
        mp = N.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (tiling[0], tiling[1], 1.0)
        L.new(tc.outputs['UV'], mp.inputs['Vector'])
        vec = mp.outputs['Vector']
    bc = tex_node(N, load(bc_path, False), -700, 300, vec, L)
    if ms_path:
        ms = tex_node(N, load(ms_path, True), -700, 0, vec, L)
        sp = N.new('ShaderNodeSeparateColor')
        L.new(ms.outputs['Color'], sp.inputs[0])
        L.new(sp.outputs[0], pr.inputs['Metallic'])
        inv = N.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        L.new(ms.outputs['Alpha'], inv.inputs[1])
        L.new(inv.outputs[0], pr.inputs['Roughness'])
        L.new(bc.outputs['Color'], pr.inputs['Base Color'])      # Cycles computes its own occlusion: G unused
    else:
        L.new(bc.outputs['Color'], pr.inputs['Base Color'])
        pr.inputs['Roughness'].default_value = 0.8
    nt = tex_node(N, load(n_path, True), -700, -300, vec, L)
    nm = N.new('ShaderNodeNormalMap')
    L.new(nt.outputs['Color'], nm.inputs['Color'])
    L.new(nm.outputs[0], pr.inputs['Normal'])
    return m, pr


def glass_material(name, tint, refl):
    m, N, L = new_mat(name)
    out = N.new('ShaderNodeOutputMaterial')
    tr = N.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = tint
    gl = N.new('ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.03
    lw = N.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.1
    f = N.new('ShaderNodeMath')
    f.operation = 'MULTIPLY_ADD'
    L.new(lw.outputs['Fresnel'], f.inputs[0])
    f.inputs[1].default_value = 1.0 - refl
    f.inputs[2].default_value = refl
    mx = N.new('ShaderNodeMixShader')
    L.new(f.outputs[0], mx.inputs[0])
    L.new(tr.outputs[0], mx.inputs[1])
    L.new(gl.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs[0])
    return m


FINAL = {}
for atl, mats in ATLAS.items():
    fm, _ = pbr_material('M_' + atl, os.path.join(UT, f'T_{atl}_BaseColor.png'),
                         os.path.join(UT, f'T_{atl}_MaskMap.png'), os.path.join(UT, f'T_{atl}_Normal.png'))
    for mn in mats:
        FINAL[mn] = fm
M_AIR, _ = pbr_material('M_Airframe', os.path.join(UT, 'T_Airframe_BaseColor.png'),
                        os.path.join(UT, 'T_Airframe_MaskMap.png'), os.path.join(UT, 'T_Airframe_Normal.png'))
M_WING, _ = pbr_material('M_Wing', os.path.join(UT, 'T_Wing_BaseColor.png'),
                         os.path.join(UT, 'T_Wing_MaskMap.png'), os.path.join(UT, 'T_Wing_Normal.png'))
FINAL['src_Glass'] = glass_material('M_Glass', (0.93, 0.96, 0.95, 1), 0.06)
FINAL['src_CP_GaugeGlass'] = glass_material('M_GaugeGlass', (1, 1, 1, 1), 0.008)
wm, _ = pbr_material('M_Webbing', os.path.join(UT, 'T_Webbing_BaseColor.png'), None,
                     os.path.join(UT, 'T_Webbing_Normal.png'), tiling=(10.0, 1.0))
FINAL['src_IN_Webbing'] = wm
FINAL['src_CP_Net'] = wm
for key, mname in (('src_CP_Gauges', 'M_Gauges'), ('src_CP_Annun', 'M_Annunciator')):
    m, N, L = new_mat(mname)
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    t = tex_node(N, load(os.path.join(UT, 'T_Gauges_BC.png'), False), -400, 0)
    L.new(t.outputs['Color'], pr.inputs['Base Color'])
    e = tex_node(N, load(os.path.join(UT, 'T_Gauges_Emission.png' if key == 'src_CP_Gauges' else
                                      'T_Displays_Emission.png'), False), -400, -300)
    L.new(e.outputs['Color'], pr.inputs['Emission Color'])
    pr.inputs['Emission Strength'].default_value = 0.0
    pr.inputs['Roughness'].default_value = 0.7 if key == 'src_CP_Gauges' else 0.25
    L.new(pr.outputs[0], out.inputs[0])
    FINAL[key] = m
for key, mname, tex in (('src_PropBlur', 'M_PropBlur', 'T_PropBlur'), ('src_PropDisc', 'M_PropDisc', 'T_PropDisc')):
    m, N, L = new_mat(mname)
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    t = tex_node(N, load(os.path.join(UT, tex + '.png'), False), -400, 0)
    L.new(t.outputs['Color'], pr.inputs['Base Color'])
    L.new(t.outputs['Alpha'], pr.inputs['Alpha'])
    pr.inputs['Roughness'].default_value = 0.6
    L.new(pr.outputs[0], out.inputs[0])
    FINAL[key] = m
m, N, L = new_mat('M_Screen')
out = N.new('ShaderNodeOutputMaterial')
pr = N.new('ShaderNodeBsdfPrincipled')
pr.inputs['Base Color'].default_value = (0.010, 0.013, 0.013, 1)
pr.inputs['Roughness'].default_value = 0.2
pr.inputs['Emission Color'].default_value = (0.05, 0.12, 0.10, 1)
pr.inputs['Emission Strength'].default_value = 0.0
L.new(pr.outputs[0], out.inputs[0])
FINAL['src_CP_Screen'] = m
LIGHT = {'M_Light_Red': ((1.0, 0.02, 0.01, 1), 12), 'M_Light_Green': ((0.02, 1.0, 0.15, 1), 12),
         'M_Light_White': ((1.0, 1.0, 0.95, 1), 10), 'M_Light_Beacon': ((1.0, 0.08, 0.01, 1), 8),
         'M_Light_Landing': ((1.0, 0.97, 0.9, 1), 3), 'M_Light_Cabin': ((1.0, 0.85, 0.62, 1), 0.0)}
for ln, (c, s) in LIGHT.items():
    if ln not in MAT:
        continue
    mt = MAT[ln]
    mt.use_nodes = True
    mt.node_tree.nodes.clear()
    N, L = mt.node_tree.nodes, mt.node_tree.links
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    pr.inputs['Base Color'].default_value = (c[0] * 0.3, c[1] * 0.3, c[2] * 0.3, 1)
    pr.inputs['Roughness'].default_value = 0.1
    pr.inputs['Emission Color'].default_value = c
    pr.inputs['Emission Strength'].default_value = s
    pr.inputs['Coat Weight'].default_value = 1.0
    L.new(pr.outputs[0], out.inputs[0])

# ------------------------------------------------------------------ remap slots per object, merge duplicates
for ob in O:
    if ob.type != 'MESH':
        continue
    me = ob.data
    mats = list(me.materials)

    def final_of(mt):
        if mt is None:
            return None
        if mt.name in A_MATS:
            return M_WING if ob.name in W_OBJS else M_AIR
        return FINAL.get(mt.name, mt)
    new = [final_of(mt) for mt in mats]
    uniq = []
    for p in me.polygons:
        mt = new[p.material_index] if p.material_index < len(new) else None
        if mt not in uniq:
            uniq.append(mt)
    idx = [uniq.index(new[p.material_index]) if p.material_index < len(new) else 0 for p in me.polygons]
    me.materials.clear()
    for mt in uniq:
        me.materials.append(mt)
    for p, i in zip(me.polygons, idx):
        p.material_index = i

for mt in list(MAT):
    if mt.name.startswith('src_') and mt.use_fake_user:
        mt.use_fake_user = False
bpy.data.orphans_purge(do_recursive=True)
left = sorted({m.name for ob in O if ob.type == 'MESH' for m in ob.data.materials if m and m.name.startswith('src_')})
print('materials', sorted(m.name for m in MAT), flush=True)
assert not left, ('unmapped source materials', left)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v8_final_{TAG}.blend'))
print('saved final blend')
