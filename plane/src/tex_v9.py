"""v9 UV packing + bake inputs for the two new atlases (out/plane_v9.blend -> out/plane_v9_uv.blend, tex/v9/*.npy).
 - Fittings (M_Fittings, 2048): Cabin_Fittings, PaxSeat_* + legs, PilotDoor_L_Clip, PilotDoor_R_Holster,
   Stow_LadderStraps. Seats baked in the rest pose (down). Maps: id (face zone fz), pos (world), nrm (world), ao.
 - Survival (M_Survival, baked at 1024, reduced to a PSX 256 atlas by paint_v9.py): SM_Surv_* + Surv_Bag_Strap,
   each item baked alone (everything else hidden) with object-space position.
UV islands come from geo9 (metric, non-mirrored); the packer keeps them unrotated so the painter knows directions:
tubes / straps run along V."""
import bpy, bmesh, math, os, sys, json, time
import numpy as np
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'v9')
os.makedirs(TEX, exist_ok=True)
ONLY = os.environ.get('ONLY', '')
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9_uv.blend' if ONLY == 'aol' else 'plane_v9.blend'))
O, sc = bpy.data.objects, bpy.context.scene
FIT = ['Cabin_Fittings'] + [f'PaxSeat_{t}{s}' for t in ('L1', 'R1', 'L2', 'R2') for s in ('', '_Leg')] + \
      ['PilotDoor_L_Clip', 'PilotDoor_R_Holster', 'Stow_LadderStraps']
SURV = ['SM_Surv_Bag', 'Surv_Bag_Strap', 'SM_Surv_Shovel', 'SM_Surv_FlareGun', 'SM_Surv_FlareShell', 'SM_Surv_Flare',
        'SM_Surv_Flashlight']
RES_F, RES_S = 2048, 1024
MARGIN_F, MARGIN_S = 5, 6
t0 = time.time()


def log(*a):
    print(f'[{time.time() - t0:6.1f}s]', *a, flush=True)


def uv_area(objs):
    tot = 0.0
    for n in objs:
        me = O[n].data
        uv = me.uv_layers[0].data
        for p in me.polygons:
            pts = [uv[li].uv for li in p.loop_indices]
            tot += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                           for i in range(len(pts)))) / 2
    return tot


uv_area_metric = {}


def pack(objs, res, margin):
    metric = uv_area(objs)
    for n in objs:
        uv_area_metric[n] = uv_area([n])
    bpy.ops.object.select_all(action='DESELECT')
    for n in objs:
        O[n].hide_set(False)
        O[n].select_set(True)
    bpy.context.view_layer.objects.active = O[objs[0]]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.reveal(select=True)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=False, margin_method='FRACTION', margin=margin / res, shape_method='CONCAVE',
                            scale=True, merge_overlap=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    packed = uv_area(objs)
    # identical islands are stacked (merge_overlap): density from one object whose UVs are not shared
    ref = objs[-1]
    k = math.sqrt(uv_area([ref]) / uv_area_metric[ref])                 # UV units per metre
    log(f'packed {len(objs)} objects: metric area {metric:.3f} m2, coverage {packed * 100:.1f} %, '
        f'{k * res:.0f} px/m')
    return dict(metresPerUV=1.0 / k, pxPerMetre=k * res, areaM2=metric, coverage=packed)


# ------------------------------------------------------------------ pack
for n in FIT + SURV:
    O[n].hide_viewport = False
    O[n].hide_render = False
if ONLY != 'aol':
    INFO = {'Fittings': pack(FIT, RES_F, MARGIN_F), 'Survival': pack(SURV, RES_S, MARGIN_S)}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9_uv.blend'))

# ------------------------------------------------------------------ bake setup (Cycles, emission passes)
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.use_denoising = False
if not sc.world:
    sc.world = bpy.data.worlds.new('World')
BAKE_MATS = {}


def bake_material(name, space):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    geo = N.new('ShaderNodeNewGeometry')
    tc = N.new('ShaderNodeTexCoord')
    fz = N.new('ShaderNodeAttribute')
    fz.attribute_type = 'GEOMETRY'
    fz.attribute_name = 'fz'
    em = N.new('ShaderNodeEmission')
    em.name = 'EM'
    t = N.new('ShaderNodeTexImage')
    t.name = 'BAKE_TARGET'
    N.active = t
    m['src'] = {'pos': (tc.name if space == 'object' else geo.name), 'nrm': geo.name, 'fz': fz.name}
    BAKE_MATS[name] = (m, out, geo, tc, fz, em, space)
    return m


def set_source(mname, what):
    m, out, geo, tc, fz, em, space = BAKE_MATS[mname]
    nt = m.node_tree
    for l in list(em.inputs['Color'].links):
        nt.links.remove(l)
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    if what == 'pos':
        nt.links.new((tc.outputs['Object'] if space == 'object' else geo.outputs['Position']), em.inputs['Color'])
    elif what == 'nrm':
        nt.links.new(geo.outputs['Normal'], em.inputs['Color'])
    elif what == 'id':
        cmb = nt.nodes.get('CMB') or nt.nodes.new('ShaderNodeCombineXYZ')
        cmb.name = 'CMB'
        if not cmb.inputs[0].links:
            nt.links.new(fz.outputs['Fac'], cmb.inputs[0])
        nt.links.new(cmb.outputs[0], em.inputs['Color'])
    if what in ('pos', 'nrm', 'id'):
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    else:                                                       # AO: plain diffuse surface
        d = nt.nodes.get('DIF') or nt.nodes.new('ShaderNodeBsdfDiffuse')
        d.name = 'DIF'
        nt.links.new(d.outputs[0], out.inputs['Surface'])


def assign(objs, mname):
    for n in objs:
        me = O[n].data
        me.materials.clear()
        me.materials.append(BAKE_MATS[mname][0])
        for p in me.polygons:
            p.material_index = 0


def new_image(name, res):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=True, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    im.generated_color = (0, 0, 0, 0)
    return im


def save_npy(im, path, channels, dtype):
    W, H = im.size
    buf = np.empty(W * H * 4, np.float32)
    im.pixels.foreach_get(buf)
    arr = buf.reshape(H, W, 4)[::-1, :, :channels]                     # row 0 = top (v = 1)
    np.save(path, arr.astype(dtype))


def bake(objs, mname, what, res, path, samples=1, margin=8, dist=None, ch=3, dtype=np.float32):
    im = new_image('BK_' + what, res)
    m = BAKE_MATS[mname][0]
    m.node_tree.nodes['BAKE_TARGET'].image = im
    m.node_tree.nodes.active = m.node_tree.nodes['BAKE_TARGET']
    set_source(mname, what)
    sc.cycles.samples = samples
    if dist is not None:
        sc.world.light_settings.distance = dist
    bk = sc.render.bake
    bk.use_clear = True
    bk.margin = margin
    bk.margin_type = 'EXTEND'
    bk.target = 'IMAGE_TEXTURES'
    bpy.ops.object.select_all(action='DESELECT')
    for n in objs:
        O[n].select_set(True)
    bpy.context.view_layer.objects.active = O[objs[0]]
    t1 = time.time()
    bpy.ops.object.bake(type='AO' if what == 'ao' else 'EMIT')
    save_npy(im, path, ch, dtype)
    bpy.data.images.remove(im)
    log('baked', os.path.basename(path), res, round(time.time() - t1, 1), 's')


# ------------------------------------------------------------------ fittings (in place, cabin present for AO)
bake_material('BK_FIT', 'world')
assign(FIT, 'BK_FIT')
for n in SURV + ['src_StepLadder', 'Ladder_RearLegs', 'src_PlaneKey'] + [o.name for o in O if o.name.startswith('src_Case')]:
    if n in O:
        O[n].hide_render = True
if ONLY == 'aol':                               # cabin-scale AO: sky through the windows (glass hidden)
    for o in O:
        if 'Glass' in o.name or o.name.endswith('_Fog'):
            o.hide_render = True
    bake(FIT, 'BK_FIT', 'ao', RES_F // 2, os.path.join(TEX, 'F9_aol.npy'), samples=int(os.environ.get('AO_S', 64)),
         margin=MARGIN_F, dist=4.0, ch=1, dtype=np.float16)
    sys.exit(0)
bake(FIT, 'BK_FIT', 'id', RES_F, os.path.join(TEX, 'F9_id.npy'), margin=0, ch=1, dtype=np.float16)
bake(FIT, 'BK_FIT', 'pos', RES_F, os.path.join(TEX, 'F9_pos.npy'), margin=MARGIN_F)
bake(FIT, 'BK_FIT', 'nrm', RES_F, os.path.join(TEX, 'F9_nrm.npy'), margin=MARGIN_F, dtype=np.float16)
bake(FIT, 'BK_FIT', 'ao', RES_F, os.path.join(TEX, 'F9_ao.npy'), samples=int(os.environ.get('AO_S', 64)),
     margin=MARGIN_F, dist=0.12, ch=1, dtype=np.float16)

# ------------------------------------------------------------------ survival items: alone, object space
for o in O:
    o.hide_render = True
bake_material('BK_SURV', 'object')
assign(SURV, 'BK_SURV')
saved = {}
for i, n in enumerate(SURV):
    o = O[n]
    saved[n] = (o.parent, o.matrix_world.copy())
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = Matrix.Translation((50.0 + 3.0 * i, 50.0, 0.0)) @ mw.to_3x3().to_4x4() if n != 'Surv_Bag_Strap' \
        else Matrix.Translation((50.0, 50.0, 0.0)) @ O['SM_Surv_Bag'].matrix_world.to_3x3().to_4x4() @ \
        (saved['SM_Surv_Bag'][1].inverted() @ mw)
    o.hide_render = False
bpy.context.view_layer.update()
bake(SURV, 'BK_SURV', 'id', RES_S, os.path.join(TEX, 'S9_id.npy'), margin=0, ch=1, dtype=np.float16)
bake(SURV, 'BK_SURV', 'pos', RES_S, os.path.join(TEX, 'S9_pos.npy'), margin=MARGIN_S)
bake(SURV, 'BK_SURV', 'nrm', RES_S, os.path.join(TEX, 'S9_nrm.npy'), margin=MARGIN_S, dtype=np.float16)
bake(SURV, 'BK_SURV', 'ao', RES_S, os.path.join(TEX, 'S9_ao.npy'), samples=int(os.environ.get('AO_S', 64)),
     margin=MARGIN_S, dist=0.08, ch=1, dtype=np.float16)
json.dump(INFO, open(os.path.join(TEX, 'atlas9.json'), 'w'), indent=1)
log('done', json.dumps(INFO))
