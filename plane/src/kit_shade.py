"""Winter kit: procedural materials, two UV atlases and bakes: T_KitCovers (wing/windshield/engine covers, 4K) and
T_KitProps (plugs, chocks, ropes, heater, bags, jerry can..., 4K) - one atlas would leave the small props at 3 px/cm.
python3 kit_shade.py [ao_samples=48]
  env REUSE=1  -> open out/kit_uv_v1.blend (UVs already packed; Blender's packer is not deterministic, so a resumed run
                  must reuse the saved UVs), otherwise unwrap out/kit_geo_v1.blend and save out/kit_uv_v1.blend
  env SKIP=Covers:BaseColor,Props:MR  -> passes already baked (resume after a VM restart)
writes tex/kit1/T_Kit{Covers,Props}_{BaseColor,MR,Normal,AO,DMask}.png, out/kit_src_v1.blend
DMask = URP/Built-in detail mask (fabric weave detail map only on the textile parts)."""
import bpy, bmesh, os, sys, math, time, json
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nodes as ND
from nodes import NB, weather
import layout as LY

AO_S = int(sys.argv[1]) if len(sys.argv) > 1 else 48
TEX = os.path.join(HERE, 'tex', 'kit1')
os.makedirs(TEX, exist_ok=True)
RES, HALF = 4096, 2048
REUSE = os.environ.get('REUSE') == '1'
SKIP = {x for x in os.environ.get('SKIP', '').split(',') if x}
# HYBRID=Kit_A,Kit_B: start from the baked out/kit_src_v1.blend and swap in these objects' meshes from a fresh
# out/kit_geo_v1.blend (kit_geo is not index-stable: bevel order), then UNWRAP=<atlases> re-unwraps only those atlases
HYBRID = [x for x in os.environ.get('HYBRID', '').split(',') if x]
if HYBRID:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'kit_src_v1.blend'))
    with bpy.data.libraries.load(os.path.join(HERE, 'out', 'kit_geo_v1.blend'), link=False) as (src, dst):
        dst.meshes = [n for n in src.meshes if n in HYBRID]
    for me in dst.meshes:
        ob = bpy.data.objects[me.name.split('.')[0]]
        old = ob.data
        ob.data = me
        bpy.data.meshes.remove(old)
        me.name = ob.name
        for i, m in enumerate(me.materials):               # appended duplicates (kit_X.001) -> the existing kit_X
            if m is not None and '.' in m.name and bpy.data.materials.get(m.name.split('.')[0]):
                dup = m
                me.materials[i] = bpy.data.materials[m.name.split('.')[0]]
                if dup.users == 0:
                    bpy.data.materials.remove(dup)
        print('hybrid: new mesh for', ob.name, len(me.vertices), [m.name for m in me.materials][:3], flush=True)
else:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'kit_uv_v1.blend' if REUSE else 'kit_geo_v1.blend'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
O, MAT = bpy.data.objects, bpy.data.materials
KIT = sorted([o for o in bpy.data.collections['Kit'].objects if o.type == 'MESH'], key=lambda o: o.name)
COVERS = ['Kit_EngineCover', 'Kit_WindshieldCover', 'Kit_WingCover_L', 'Kit_WingCover_R']
ATL = {'Covers': [O[n] for n in COVERS], 'Props': [o for o in KIT if o.name not in COVERS]}
for o in ATL['Covers']:                                   # covers get their own material copies (kitC_*)
    for i, m in enumerate(o.data.materials):
        if m and m.name.startswith('kit_'):
            cname = 'kitC_' + m.name[4:]
            mc = MAT.get(cname)
            if mc is None:
                mc = m.copy()
                mc.name = cname
            o.data.materials[i] = mc
AMATS = {a: sorted({m.name for o in objs for m in o.data.materials if m}) for a, objs in ATL.items()}
assert not set(AMATS['Covers']) & set(AMATS['Props']), AMATS
KMATS = AMATS['Covers'] + AMATS['Props']
print('kit objects', len(KIT), 'atlas materials', AMATS, flush=True)

# parked frame helpers (ground items were built level in the parked frame)
TH = math.radians(LY.PARK_PITCH_DEG)
PIV = Vector((0.0, LY.MAIN_WHEEL_C[1], LY.MAIN_CONTACT_Z))
R = Matrix.Translation(PIV) @ Matrix.Rotation(-TH, 4, 'X') @ Matrix.Translation(-PIV)
RI = R.inverted()
GZ = LY.MAIN_CONTACT_Z


def z_parked(nb, P):
    """world z in the parked frame (height above the parked ground plane + GZ)"""
    x, y, z = nb.sep(P)
    return nb.add(nb.mul(nb.sub(y, PIV.y), -math.sin(TH)), nb.mul(nb.sub(z, PIV.z), math.cos(TH)), PIV.z)


def dmask(nb, v):
    e = nb.new('ShaderNodeEmission', name='BAKE_DMASK', label='BAKE_DMASK')
    nb.set(e.inputs['Color'], (v, v, v, 1))


FADED = (0.105, 0.11, 0.115, 1)


# ------------------------------------------------------------------ materials
def m_fabric(mat, col, rough, seam_period=1.15, fade=0.35, dm=1.0, seams=True):
    """coated polyester cover cloth: sun-faded up-facing panels, dust, damp patches, sewn panel seams"""
    nb = NB(mat)
    P, N, Ob = nb.P(), nb.Nrm(), nb.obj()
    ox, oy, oz = nb.sep(Ob)
    _, _, nz = nb.sep(N)
    n1 = nb.noise(P, 1.1, 4, 0.55)
    n2 = nb.noise(P, 6.0, 6, 0.6)
    ng = nb.noise(P, 70.0, 4, 0.6)
    cr = nb.noise(P, 16.0, 3, 0.5, distortion=1.8)          # small creases
    up = nb.ss(0.15, 0.9, nz)
    c = nb.mixc(nb.mul(up, fade, nb.ss(0.25, 0.75, n1)), col, FADED)
    c = nb.mixc(nb.mul(nb.ss(0.55, 0.78, n2), 0.30), c, ND.DIRT)
    c = nb.mixc(nb.mul(nb.ss(0.6, 0.4, n1), nb.inv(up), 0.25), c, (0.02, 0.02, 0.022, 1))   # damp, darker underside
    c = nb.mixc(nb.mul(ng, 0.10), c, (0.0, 0.0, 0.0, 1))
    h = nb.add(nb.mul(cr, 0.0004), nb.mul(ng, 0.00004))
    if seams:
        seam, _ = nb.line_mask(ox, seam_period, 0.007)
        c = nb.mixc(nb.mul(seam, 0.45), c, (0.015, 0.015, 0.017, 1))
        h = nb.add(h, nb.mul(seam, -0.0007))
    r = nb.add(rough, nb.mul(nb.sub(ng, 0.5), 0.08), nb.mul(up, -0.04))
    nb.finish(c, 0.0, nb.clamp01(r), h)
    dmask(nb, dm)


def m_quilt(mat):
    """insulated engine cover: red ripstop, diamond quilting (stitch valleys, padded pillows), cylindrical layout"""
    nb = NB(mat)
    P, N, Ob = nb.P(), nb.Nrm(), nb.obj()
    ox, oy, oz = nb.sep(Ob)
    _, _, nz = nb.sep(N)
    s = nb.mul(nb.m('ARCTAN2', ox, nb.add(oz, 0.33)), 0.55)  # arc length around the cowl (pivot 1.95, axis ~1.62)
    a, b = nb.add(oy, s), nb.sub(oy, s)
    _, d1 = nb.line_mask(a, 0.17, 0.001)
    _, d2 = nb.line_mask(b, 0.17, 0.001)
    dmin = nb.mn(d1, d2)
    stitch = nb.inv(nb.ss(0.002, 0.008, dmin))
    puff = nb.ss(0.0, 0.05, dmin)
    n1 = nb.noise(P, 1.3, 4, 0.55)
    n2 = nb.noise(P, 6.0, 6, 0.6)
    ng = nb.noise(P, 70.0, 4, 0.6)
    up = nb.ss(0.15, 0.9, nz)
    col = (0.30, 0.032, 0.026, 1)
    c = nb.mixc(nb.mul(up, 0.35, nb.ss(0.25, 0.75, n1)), col, (0.36, 0.075, 0.06, 1))      # sun-faded
    c = nb.mixc(nb.mul(nb.inv(puff), 0.35), c, (0.16, 0.018, 0.015, 1))                    # shaded valleys
    c = nb.mixc(nb.mul(nb.ss(0.55, 0.78, n2), 0.30), c, ND.DIRT)
    c = nb.mixc(nb.mul(ng, 0.08), c, (0.0, 0.0, 0.0, 1))
    r = nb.add(0.62, nb.mul(nb.sub(ng, 0.5), 0.08), nb.mul(stitch, 0.1))
    h = nb.add(nb.mul(puff, 0.006), nb.mul(stitch, -0.0012), nb.mul(ng, 0.00004))
    nb.finish(c, 0.0, nb.clamp01(r), h)
    dmask(nb, 1.0)


def m_vinyl(mat, col):
    """red PVC-coated plug / cap faces: smooth, slightly glossy, creased, grimy"""
    nb = NB(mat)
    P = nb.P()
    n1 = nb.noise(P, 3.0, 4, 0.5)
    ng = nb.noise(P, 45.0, 4, 0.6)
    cr = nb.noise(P, 22.0, 3, 0.5, distortion=2.0)
    c = nb.mixc(nb.mul(nb.ss(0.5, 0.8, n1), 0.35), col, ND.DIRT)
    c = nb.mixc(nb.mul(ng, 0.10), c, (0.0, 0.0, 0.0, 1))
    r = nb.add(0.40, nb.mul(nb.sub(ng, 0.5), 0.1), nb.mul(nb.ss(0.5, 0.8, n1), 0.25))
    h = nb.add(nb.mul(cr, 0.0003), nb.mul(ng, 0.00003))
    nb.finish(c, 0.0, nb.clamp01(r), h)
    dmask(nb, 0.0)


STREAMER_IMG = bpy.data.images.load(os.path.join(HERE, 'tex_kit_streamer.png'), check_existing=True)
STREAMER_IMG.colorspace_settings.name = 'Non-Color'


def m_streamer(mat):
    """REMOVE BEFORE FLIGHT: red nylon, white print along TextUV (u = along the strip)"""
    nb = NB(mat)
    uvn = nb.new('ShaderNodeUVMap', uv_map='TextUV')
    t = nb.new('ShaderNodeTexImage', image=STREAMER_IMG, interpolation='Cubic', extension='CLIP')
    nb.L.new(uvn.outputs[0], t.inputs['Vector'])
    txt = t.outputs['Color']
    P = nb.P()
    n1 = nb.noise(P, 4.0, 3, 0.5)
    ng = nb.noise(P, 60.0, 4, 0.6)
    c = nb.mixc(txt, (0.50, 0.018, 0.015, 1), (0.78, 0.77, 0.74, 1))
    c = nb.mixc(nb.mul(nb.ss(0.55, 0.8, n1), 0.30), c, ND.DIRT)
    r = nb.add(0.55, nb.mul(nb.sub(ng, 0.5), 0.08), nb.mul(txt, -0.08))
    h = nb.add(nb.mul(ng, 0.00008), nb.mul(txt, 0.00004))
    nb.finish(c, 0.0, nb.clamp01(r), h)
    dmask(nb, 0.5)


def m_webbing(mat):
    nb = NB(mat)
    P = nb.P()
    ng = nb.noise(P, 120.0, 3, 0.6)
    n1 = nb.noise(P, 5.0, 3, 0.5)
    c = nb.mixc(nb.mul(nb.ss(0.55, 0.8, n1), 0.35), (0.016, 0.016, 0.018, 1), ND.DIRT)
    r = nb.add(0.66, nb.mul(nb.sub(ng, 0.5), 0.1))
    nb.finish(c, 0.0, nb.clamp01(r), nb.mul(ng, 0.0001))
    dmask(nb, 0.7)


def m_plastic(mat, col, rough, dm=0.0, dirt=0.25):
    nb = NB(mat)
    P = nb.P()
    c, m, r, h = weather(nb, P, col, rough, dirt=dirt, plastic=True, zworld=z_parked(nb, P), bottom=(GZ + 0.15, GZ))
    nb.finish(c, 0.0, r, h)
    dmask(nb, dm)


def m_chock(mat):
    """yellow urethane chocks: scuffed edges, ground dirt at the base"""
    nb = NB(mat)
    P = nb.P()
    zp = z_parked(nb, P)
    c, m, r, h = weather(nb, P, (0.62, 0.40, 0.02, 1), 0.55, dirt=0.5, plastic=True, zworld=zp,
                         bottom=(GZ + 0.10, GZ), edge_boost=0.4)
    scuff = nb.mul(nb.ss(0.6, 0.75, nb.noise(P, 25.0, 6, 0.7)), nb.ss(0.95, 0.6, nb.edge_ao(0.01, 6)))
    c = nb.mixc(nb.mul(scuff, 0.6), c, (0.75, 0.62, 0.30, 1))
    nb.finish(c, 0.0, nb.mixf(scuff, r, 0.8), nb.add(h, nb.mul(scuff, -0.0002)))
    dmask(nb, 0.0)


def m_rope(mat):
    nb = NB(mat)
    P = nb.P()
    zp = z_parked(nb, P)
    ng = nb.noise(P, 220.0, 3, 0.6)
    tw = nb.noise(P, 90.0, 2, 0.5, distortion=3.0)            # twisted strands, read as fibre ridges
    n1 = nb.noise(P, 6.0, 3, 0.5)
    c = nb.mixc(nb.mul(tw, 0.25), (0.72, 0.53, 0.05, 1), (0.45, 0.30, 0.03, 1))
    g = nb.clamp01(nb.add(nb.mul(nb.ss(0.55, 0.8, n1), 0.4), nb.ss(GZ + 0.06, GZ, zp)))
    c = nb.mixc(nb.mul(g, 0.6), c, ND.DIRT)
    r = nb.add(0.72, nb.mul(nb.sub(ng, 0.5), 0.1))
    nb.finish(c, 0.0, nb.clamp01(r), nb.add(nb.mul(tw, 0.0004), nb.mul(ng, 0.0001)))
    dmask(nb, 0.0)


def m_galv(mat):
    """galvanised steel (screw anchors, adapter, can cap): spangle, white rust, mud on the buried part"""
    nb = NB(mat)
    P = nb.P()
    zp = z_parked(nb, P)
    sp = nb.noise(P, 40.0, 2, 0.4)
    ng = nb.noise(P, 120.0, 3, 0.6)
    n2 = nb.noise(P, 9.0, 6, 0.7)
    mud = nb.ss(GZ + 0.01, GZ - 0.03, zp)
    wrust = nb.ss(0.62, 0.75, n2)
    c = nb.mixc(nb.mul(sp, 0.3), (0.56, 0.57, 0.58, 1), (0.42, 0.43, 0.44, 1))
    c = nb.mixc(nb.mul(wrust, 0.6), c, (0.62, 0.62, 0.60, 1))
    c = nb.mixc(mud, c, ND.MUD)
    metal = nb.mul(nb.inv(mud), nb.inv(nb.mul(wrust, 0.7)))
    r = nb.add(0.36, nb.mul(sp, 0.12), nb.mul(wrust, 0.3), nb.mul(ng, 0.05))
    r = nb.mixf(mud, r, 0.92)
    nb.finish(c, metal, nb.clamp01(r), nb.add(nb.mul(ng, 0.00005), nb.mul(mud, 0.0004)))
    dmask(nb, 0.0)


def m_painted(mat, col, rough, chip=0.03, rust=0.4, dirt=0.35, edge=0.25):
    nb = NB(mat)
    P, Ob = nb.P(), nb.obj()
    c, m, r, h = weather(nb, Ob, col, rough, chip_amt=chip, rust_amt=rust, dirt=dirt, zworld=z_parked(nb, P),
                         bottom=(GZ + 0.25, GZ), edge_boost=edge)
    nb.finish(c, m, r, h)
    dmask(nb, 0.0)


def m_duct(mat):
    nb = NB(mat)
    P = nb.P()
    zp = z_parked(nb, P)
    ng = nb.noise(P, 80.0, 3, 0.6)
    n1 = nb.noise(P, 3.0, 4, 0.5)
    g = nb.clamp01(nb.add(nb.mul(nb.ss(0.5, 0.8, n1), 0.4), nb.ss(GZ + 0.12, GZ, zp)))
    c = nb.mixc(nb.mul(g, 0.5), (0.022, 0.022, 0.024, 1), ND.DIRT)
    r = nb.add(0.74, nb.mul(nb.sub(ng, 0.5), 0.08))
    nb.finish(c, 0.0, nb.clamp01(r), nb.mul(ng, 0.0001))
    dmask(nb, 0.4)


def m_rubber(mat):
    nb = NB(mat)
    P = nb.P()
    ng = nb.noise(P, 60.0, 4, 0.6)
    c = nb.mixc(nb.mul(ng, 0.3), (0.02, 0.02, 0.02, 1), (0.04, 0.038, 0.035, 1))
    nb.finish(c, 0.0, nb.clamp01(nb.add(0.84, nb.mul(nb.sub(ng, 0.5), 0.1))), nb.mul(ng, 0.0001))
    dmask(nb, 0.0)


BUILD = {
    'kit_CoverFabric': lambda m: m_fabric(m, (0.045, 0.05, 0.055, 1), 0.82),
    'kit_CoverInner': lambda m: m_fabric(m, (0.10, 0.10, 0.10, 1), 0.9, fade=0.0, seams=False),
    'kit_CoverRed': m_quilt,
    'kit_RedVinyl': lambda m: m_vinyl(m, (0.42, 0.03, 0.022, 1)),
    'kit_Streamer': m_streamer,
    'kit_Webbing': m_webbing,
    'kit_Buckle': lambda m: m_plastic(m, (0.02, 0.02, 0.02, 1), 0.4),
    'kit_ChockYellow': m_chock,
    'kit_Rope': m_rope,
    'kit_Steel': m_galv,
    'kit_HeaterBody': lambda m: m_painted(m, (0.70, 0.27, 0.02, 1), 0.45, chip=0.03, rust=0.4, dirt=0.4),
    'kit_Duct': m_duct,
    'kit_CanOlive': lambda m: m_painted(m, (0.085, 0.095, 0.04, 1), 0.5, chip=0.02, rust=0.5, dirt=0.35, edge=0.0),
    'kit_PlasticBlack': lambda m: m_plastic(m, (0.02, 0.02, 0.02, 1), 0.45),
    'kit_Rubber': m_rubber,
    'kit_DuctRib': m_duct,
    'kit_SteelHidden': m_galv,
}
base = lambda n: 'kit_' + n[5:] if n.startswith('kitC_') else n
missing = [m for m in KMATS if base(m) not in BUILD]
assert not missing, ('no builder for', missing)
for m in KMATS:
    BUILD[base(m)](MAT[m])
    MAT[m].use_fake_user = True

# ------------------------------------------------------------------ UV atlas
MARGIN_PX = 8
SCALE_MAT = {'kit_Streamer': 1.8, 'kit_CoverInner': 0.22, 'kit_Duct': 0.6, 'kit_DuctRib': 0.3, 'kit_SteelHidden': 0.15,
             'kit_Webbing': 1.2, 'kit_Buckle': 1.6}
SCALE_OBJ = {'SM_Kit_JerryCan': 1.6, 'SM_Kit_Funnel': 1.4, 'SM_Kit_IntakePlug': 1.3, 'SM_Kit_ExhaustCover': 1.4,
             'SM_Kit_PitotCover': 1.5, 'Kit_IntakePlug': 1.3, 'Kit_ExhaustCover_L': 1.4, 'Kit_ExhaustCover_R': 1.4,
             'Kit_PitotCover': 1.5, 'Kit_Chocks_L': 1.2, 'Kit_Chocks_R': 1.2, 'Kit_Chocks_Tail': 1.2,
             'SM_Kit_Chocks': 1.2, 'SM_Kit_ChocksTail': 1.2}


def ensure_uvmap(ob):
    me = ob.data
    if 'UVMap' not in me.uv_layers:
        me.uv_layers.new(name='UVMap')
    me.uv_layers.active = me.uv_layers['UVMap']
    me.uv_layers['UVMap'].active_render = True


def unwrap(objs):
    for o in objs:
        ensure_uvmap(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.reveal(select=True)
    for o in objs:                                        # tubes come with their own strip UVs (kit_uvdone)
        bm = bmesh.from_edit_mesh(o.data)
        lay = bm.faces.layers.int.get('kit_uvdone')
        for f in bm.faces:
            f.select_set(not (lay and f[lay]))
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    for o in objs:
        bm = bmesh.from_edit_mesh(o.data)
        uvl = bm.loops.layers.uv['UVMap']
        names = [m.name if m else '' for m in o.data.materials]
        fo = SCALE_OBJ.get(o.name, 1.0)
        for f in bm.faces:
            k = fo * SCALE_MAT.get(base(names[f.material_index]), 1.0)
            if abs(k - 1.0) > 1e-6:
                for lp in f.loops:
                    lp[uvl].uv *= k
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=MARGIN_PX / RES, shape_method='CONCAVE',
                            scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        if 'kit_uvdone' in o.data.attributes:
            o.data.attributes.remove(o.data.attributes['kit_uvdone'])
        for d in o.data.uv_layers['UVMap'].data:
            u, v = d.uv
            assert -1e-4 <= u <= 1.0001 and -1e-4 <= v <= 1.0001, (o.name, u, v)


def texel(objs):
    a3 = a2 = 0.0
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        uvl = bm.loops.layers.uv['UVMap']
        names = [m.name if m else '' for m in o.data.materials]
        for f in bm.faces:
            if base(names[f.material_index]) in ('kit_CoverInner', 'kit_Streamer', 'kit_SteelHidden', 'kit_DuctRib'):
                continue
            uv = [l[uvl].uv for l in f.loops]
            a2 += abs(sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y
                          for i in range(len(uv)))) / 2
            a3 += f.calc_area()
        bm.free()
    mpu = math.sqrt(a3 / a2)
    return dict(metresPerUV=round(mpu, 4), pxPerMetre=round(RES / mpu, 1), areaM2=round(a3, 2))


UNWRAP = [x for x in os.environ.get('UNWRAP', 'Covers,Props').split(',') if x]
if not REUSE:
    for a_, objs in ATL.items():
        if a_ not in UNWRAP:
            for o in objs:
                ensure_uvmap(o)
            continue
        t0 = time.time()
        unwrap(objs)
        print('unwrapped', a_, round(time.time() - t0, 1), 's', texel(objs), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'kit_uv_v1.blend'), copy=True)
    print('saved kit_uv_v1.blend', flush=True)
else:
    for o in KIT:
        ensure_uvmap(o)
    print('reused UVs', {a_: texel(objs) for a_, objs in ATL.items()}, flush=True)
json.dump({a_: texel(objs) for a_, objs in ATL.items()}, open(os.path.join(TEX, 'texel.json'), 'w'), indent=1)


# ------------------------------------------------------------------ bake
def img(name, res, noncolor=False, float_buf=False):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=float_buf)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def set_output(mt, node_name):
    nt = mt.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    src = nt.nodes[node_name] if node_name else next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(src.outputs[0], out.inputs['Surface'])


PASSES = {'BaseColor': ('EMIT', 'BAKE_COLOR', False, False, RES, 1), 'MR': ('EMIT', 'BAKE_MR', True, False, HALF, 1),
          'Normal': ('NORMAL', None, True, True, RES, 1), 'DMask': ('EMIT', 'BAKE_DMASK', True, False, RES, 1),
          'AO': ('AO', 'BAKE_PLAIN', True, False, HALF, AO_S)}


def bake(atlas, pname):
    typ, node, noncolor, fbuf, res, samples = PASSES[pname]
    im = img(f'T_Kit{atlas}_{pname}', res, noncolor, fbuf)
    for m in AMATS[atlas]:
        mt = MAT[m]
        set_output(mt, node)
        t = mt.node_tree.nodes['BAKE_TARGET']
        t.image = im
        mt.node_tree.nodes.active = t
    sc.cycles.samples = samples
    bk = sc.render.bake
    bk.use_clear = True
    bk.margin = max(4, res // 256)
    bk.margin_type = 'EXTEND'
    bk.target = 'IMAGE_TEXTURES'
    bk.normal_space = 'TANGENT'
    bk.normal_r, bk.normal_g, bk.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
    bpy.ops.object.select_all(action='DESELECT')
    for o in ATL[atlas]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ATL[atlas][0]
    t0 = time.time()
    bpy.ops.object.bake(type=typ)
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
    bpy.data.images.remove(im)
    print('baked', atlas, pname, res, round(time.time() - t0, 1), 's', flush=True)


if not sc.world:
    sc.world = bpy.data.worlds.new('World')
for a_ in ATL:
    for p_ in ('BaseColor', 'MR', 'Normal', 'DMask'):
        if f'{a_}:{p_}' not in SKIP:
            bake(a_, p_)
if any(f'{a_}:AO' not in SKIP for a_ in ATL):
    hide = [o for o in O if o.type == 'MESH' and (any(k in o.name for k in ('PropBlur', 'PropDisc', 'Fog', 'StepLadder'))
                                                  or o.name.startswith('COL_'))]
    for o in hide:
        o.hide_render = True
    gm = bpy.data.meshes.new('_aoground')                 # parked ground plane, for contact occlusion
    s = 30.0
    gm.from_pydata([(-s, -s, GZ), (s, -s, GZ), (s, s, GZ), (-s, s, GZ)], [], [(0, 1, 2, 3)])
    gm.transform(RI)
    g = bpy.data.objects.new('_aoground', gm)
    sc.collection.objects.link(g)
    sc.world.light_settings.distance = 0.25
    for a_ in ATL:
        if f'{a_}:AO' not in SKIP:
            bake(a_, 'AO')
    bpy.data.objects.remove(g)
    for o in hide:
        o.hide_render = False
for m in KMATS:
    set_output(MAT[m], None)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'kit_src_v1.blend'))
print('saved kit_src_v1.blend', flush=True)
