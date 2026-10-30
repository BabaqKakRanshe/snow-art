"""The Forest base (L12) as it is now, from the World Sync map export of 28.10 20:03, cropped to the base:
ground (ground.r16 + tile 1_1 splat, the 8 ground layers), every placed object inside the box (and world-space meshes
reaching into it), the Terrain trees, the winter snow cover on up-facing faces (ForestWinterStep's decal: full to 40°,
none from 65°), overcast day, linear fog. Blender (x, y, z) = Unity (-x, -z, y), as the export.

python3.11 -I base_scene.py <out.blend>   (imported as a module by base_concept.py / render_base.py)"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Matrix, Vector

D = os.path.dirname(os.path.abspath(__file__))
MAP = '/mnt/user-data/uploads/snow/source/world_sync/forest/map/'
GROUND_TEX = '/mnt/user-data/uploads/snow/Snow/Assets/Locations/Forest/Terrain/Ground/'
BOX = (210.0, -490.0, 480.0, -230.0)                 # Unity x0, z0, x1, z1
FOG = dict(start=6.0, end=140.0, top=0.96, color=(0.92, 0.94, 0.95))    # ForestDayNight dayFogRange 6..140 m, linear
VEG = ('Spruce', 'Fir', 'Birch', 'Dead', 'Bush', 'Leaves', 'Bark', 'Grass', 'Weeds', 'Fern', 'Snag', 'Stump', 'Branches')
NO_SNOW = ('water', 'glass', 'glow', 'halo', 'lamp', 'light', 'mist', 'creek', 'ice', 'screen', 'decal', 'flame', 'fire', 'exit')


def B(ux, uz, uy=0.0):
    return Vector((-ux, -uz, uy))


def mat4(a):
    return Matrix([a[0:4], a[4:8], a[8:12], a[12:16]])


# ---------------------------------------------------------------- materials
def fog_wrap(mat, shader_out):
    N, L = mat.node_tree.nodes, mat.node_tree.links
    cam = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = FOG['start']; mr.inputs['From Max'].default_value = FOG['end']
    mr.inputs['To Max'].default_value = FOG['top']
    L.new(cam.outputs['View Z Depth'], mr.inputs['Value'])    # Unity linear fog: by depth
    k = N.new('ShaderNodeAttribute'); k.attribute_type = 'VIEW_LAYER'; k.attribute_name = 'fog_k'     # scene['fog_k']: 1 game fog, 0 none
    fk = N.new('ShaderNodeMath'); fk.operation = 'MULTIPLY'
    L.new(mr.outputs['Result'], fk.inputs[0]); L.new(k.outputs['Fac'], fk.inputs[1])
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*FOG['color'], 1); em.inputs['Strength'].default_value = 1.0
    mix = N.new('ShaderNodeMixShader')
    L.new(fk.outputs['Value'], mix.inputs['Fac']); L.new(shader_out, mix.inputs[1]); L.new(em.outputs['Emission'], mix.inputs[2])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    L.new(mix.outputs['Shader'], out.inputs['Surface'])


def image(path, noncolor=False, alpha='STRAIGHT'):
    name = os.path.basename(path)
    im = bpy.data.images.get(name) or bpy.data.images.load(path, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    im.alpha_mode = alpha
    return im


def snow_mix(mat, color_socket):
    """the winter cover: snow (the ground's snow texture, Unity x/z over 2 m) on faces up to 40° from flat, none at 65°"""
    N, L = mat.node_tree.nodes, mat.node_tree.links
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.42; mr.inputs['From Max'].default_value = 0.77
    L.new(sep.outputs['Z'], mr.inputs['Value'])
    pos = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], pos.inputs['Vector'])
    comb = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -0.5
        L.new(pos.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], comb.inputs[ax])
    tx = N.new('ShaderNodeTexImage'); tx.image = image(GROUND_TEX + 'T_GR_Floor_A.png'); tx.interpolation = 'Closest'
    L.new(comb.outputs['Vector'], tx.inputs['Vector'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(mr.outputs['Result'], mix.inputs['Factor']); L.new(color_socket, mix.inputs['A']); L.new(tx.outputs['Color'], mix.inputs['B'])
    return mix.outputs['Result']


def game_material(d):
    mat = bpy.data.materials.new(d['name'])
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Roughness'].default_value = 0.9
    c = d.get('color') or [1, 1, 1, 1]
    col = None
    tex = d.get('texture')
    if tex and os.path.exists(MAP + tex):
        t = N.new('ShaderNodeTexImage'); t.image = image(MAP + tex); t.interpolation = 'Closest'
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        L.new(t.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (c[0], c[1], c[2], 1)
        col = mx.outputs['Result']
        if d.get('cutout'):
            gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.42
            L.new(t.outputs['Alpha'], gt.inputs[0]); L.new(gt.outputs['Value'], pb.inputs['Alpha'])
    else:
        pb.inputs['Base Color'].default_value = (c[0], c[1], c[2], 1)
    name = d['name'].lower()
    if col is not None:
        if not any(k.lower() in name for k in VEG) and not any(k in name for k in NO_SNOW):
            col = snow_mix(mat, col)
        L.new(col, pb.inputs['Base Color'])
    if any(k in name for k in ('water', 'creek')):
        pb.inputs['Base Color'].default_value = (0.012, 0.009, 0.006, 1); pb.inputs['Roughness'].default_value = 0.16
    if any(k in name for k in ('glass',)):
        pb.inputs['Roughness'].default_value = 0.2
    if len(c) > 3 and c[3] < 0.99 and not d.get('cutout') and 'water' not in name and 'creek' not in name:
        pb.inputs['Alpha'].default_value = max(0.15, c[3])
    fog_wrap(mat, pb.outputs['BSDF'])
    return mat


# ---------------------------------------------------------------- ground
def ground(m):
    g = m['ground']
    nx, nz = g['nx'], g['nz']
    raw = np.fromfile(MAP + g['file'], dtype='<u2').reshape(nz, nx)
    i0, i1 = int((BOX[0] - g['x0']) / g['step']), int((BOX[2] - g['x0']) / g['step'])
    j0, j1 = int((BOX[1] - g['z0']) / g['step']), int((BOX[3] - g['z0']) / g['step'])
    h = g['hmin'] + raw[j0:j1 + 1, i0:i1 + 1].astype(np.float32) / 65535.0 * (g['hmax'] - g['hmin'])
    ux = g['x0'] + np.arange(i0, i1 + 1) * g['step']; uz = g['z0'] + np.arange(j0, j1 + 1) * g['step']
    X, Z = np.meshgrid(ux, uz)
    co = np.stack([-X, -Z, h], -1).reshape(-1, 3).astype(np.float32)
    cz, cx = h.shape
    a = (np.arange(cz - 1)[:, None] * cx + np.arange(cx - 1)[None, :]).ravel()
    quads = np.stack([a, a + 1, a + cx + 1, a + cx], 1)
    holes = np.fromfile(MAP + g['holes'], dtype=np.uint8).reshape(nz - 1, nx - 1)
    quads = quads[holes[j0:j1, i0:i1].ravel() > 0]
    me = bpy.data.meshes.new('Ground')
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
    me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    me.update(calc_edges=True); me.shade_smooth()
    ob = bpy.data.objects.new('Ground', me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(ground_material())
    np.save(os.path.join(D, 'data', 'ground_crop.npy'), h)
    json.dump({'i0': i0, 'j0': j0, 'x0': g['x0'], 'z0': g['z0'], 'step': g['step']}, open(os.path.join(D, 'data', 'ground_crop.json'), 'w'))
    return ob


def splat_png(sp=None, suffix=''):
    """tile 1_1 splat (rows z bottom-up) -> two RGBA pictures, top = +z"""
    from PIL import Image
    if sp is None:
        sp = np.load(os.path.join(D, 'data', 'tile_splat.npy'))
    for k in range(2):
        Image.fromarray(np.ascontiguousarray(sp[::-1, :, 4 * k:4 * k + 4]).astype(np.uint8), 'RGBA').save(os.path.join(D, 'data', f'splat{k}{suffix}.png'))


def ground_material(suffix=''):
    if not os.path.exists(os.path.join(D, 'data', f'splat0{suffix}.png')):
        splat_png(suffix=suffix)
    mat = bpy.data.materials.new('G_Ground' + suffix)
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.92
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    neg = {}
    for ax in ('X', 'Y'):
        n_ = N.new('ShaderNodeMath'); n_.operation = 'MULTIPLY'; n_.inputs[1].default_value = -1.0
        L.new(sep.outputs[ax], n_.inputs[0]); neg[ax] = n_
    tu = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 2.0
        L.new(neg[ax].outputs['Value'], dv.inputs[0]); L.new(dv.outputs['Value'], tu.inputs[ax])
    su = N.new('ShaderNodeCombineXYZ')
    for ax, o_ in (('X', 0.0), ('Y', -600.0)):                       # tile 1_1: x 0..600, z -600..0
        sb = N.new('ShaderNodeMath'); sb.operation = 'SUBTRACT'; sb.inputs[1].default_value = o_
        dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 600.0
        L.new(neg[ax].outputs['Value'], sb.inputs[0]); L.new(sb.outputs['Value'], dv.inputs[0]); L.new(dv.outputs['Value'], su.inputs[ax])
    weights = []
    for k in range(2):
        t = N.new('ShaderNodeTexImage'); t.image = image(os.path.join(D, 'data', f'splat{k}{suffix}.png'), noncolor=True, alpha='CHANNEL_PACKED')
        t.interpolation = 'Linear'; t.extension = 'EXTEND'
        L.new(su.outputs['Vector'], t.inputs['Vector'])
        sc = N.new('ShaderNodeSeparateColor'); L.new(t.outputs['Color'], sc.inputs['Color'])
        weights += [sc.outputs['Red'], sc.outputs['Green'], sc.outputs['Blue'], t.outputs['Alpha']]
    acc = None
    for k, nm in enumerate(['Floor', 'FloorDark', 'Gravel', 'Soil', 'Rock', 'Ruts', 'Track', 'Asphalt']):
        t = N.new('ShaderNodeTexImage'); t.image = image(GROUND_TEX + f'T_GR_{nm}_A.png'); t.interpolation = 'Closest'
        L.new(tu.outputs['Vector'], t.inputs['Vector'])
        sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'
        L.new(t.outputs['Color'], sc.inputs[0]); L.new(weights[k], sc.inputs['Scale'])
        if acc is None:
            acc = sc.outputs['Vector']
        else:
            ad = N.new('ShaderNodeVectorMath'); ad.operation = 'ADD'
            L.new(acc, ad.inputs[0]); L.new(sc.outputs['Vector'], ad.inputs[1]); acc = ad.outputs['Vector']
    L.new(acc, pb.inputs['Base Color'])
    fog_wrap(mat, pb.outputs['BSDF'])
    return mat


# ---------------------------------------------------------------- objects, trees
def load_meshes(m, ids, mats, blob=None):
    if blob is None:
        blob = np.fromfile(MAP + m['meshes']['file'], dtype=np.uint8)
    out = {}
    for d in m['meshes']['list']:
        if d['id'] not in ids:
            continue
        off, nv = d['offset'], d['v']
        pos = np.frombuffer(blob, np.float32, nv * 3, off); off += nv * 12
        uv = None
        if d.get('uv'):
            uv = np.frombuffer(blob, np.float32, nv * 2, off).reshape(-1, 2); off += nv * 8
        idx, mi = [], []
        for s, nt in enumerate(d['subs']):
            idx.append(np.frombuffer(blob, np.uint32, nt * 3, off)); off += nt * 12
            mi.append(np.full(nt, s, np.int32))
        idx = np.concatenate(idx) if idx else np.zeros(0, np.uint32)
        mi = np.concatenate(mi) if mi else np.zeros(0, np.int32)
        nt = len(idx) // 3
        me = bpy.data.meshes.new(d['id'])
        me.vertices.add(nv); me.vertices.foreach_set('co', pos)
        me.loops.add(nt * 3); me.loops.foreach_set('vertex_index', idx.astype(np.int32))
        me.polygons.add(nt); me.polygons.foreach_set('loop_start', np.arange(0, nt * 3, 3, dtype=np.int32))
        me.polygons.foreach_set('material_index', mi)
        if uv is not None:
            layer = me.uv_layers.new(name='UVMap'); layer.data.foreach_set('uv', uv[idx].ravel())
        for name in d.get('materials', []):
            me.materials.append(mats.get(name))
        me.update()
        out[d['id']] = (me, pos.reshape(-1, 3))
    return out


def inside_u(ux, uz, margin=0.0):
    return BOX[0] - margin <= ux <= BOX[2] + margin and BOX[1] - margin <= uz <= BOX[3] + margin


def build(want_trees=True):
    m = json.load(open(MAP + 'map.json', encoding='utf-8'))
    sc = bpy.context.scene
    ground(m)
    matd = {d['name']: d for d in m['materials']}
    # which roots: placed inside the box, or world-space (at the origin) with geometry inside
    roots = {}
    for r in m['roots']:
        t = r['matrix']; ux, uz = -t[3], -t[7]
        roots[r['key']] = (r, inside_u(ux, uz), abs(t[3]) < 1e-3 and abs(t[7]) < 1e-3)
    blob = np.fromfile(MAP + m['meshes']['file'], dtype=np.uint8)
    mdict = {d['id']: d for d in m['meshes']['list']}
    want = []
    for i in m['instances']:
        r, ins, world = roots[i['root']]
        if ins:
            want.append(i)
        elif world and r['name'] not in ('Forest_Mist', 'IceShove', 'IceHole') and i['mesh'] in mdict:
            d = mdict[i['mesh']]
            P = np.frombuffer(blob, np.float32, d['v'] * 3, d['offset']).reshape(-1, 3)
            M = np.array(i['matrix'], np.float64).reshape(4, 4)
            P = P @ M[:3, :3].T + M[:3, 3]
            if ((-P[:, 0] >= BOX[0]) & (-P[:, 0] <= BOX[2]) & (-P[:, 1] >= BOX[1]) & (-P[:, 1] <= BOX[3])).any():
                want.append(i)
    ids = {i['mesh'] for i in want}
    t = m['trees']
    a = np.fromfile(MAP + t['file'], dtype=np.float32).reshape(-1, 7)
    tb = a[(a[:, 1] >= BOX[0]) & (a[:, 1] <= BOX[2]) & (a[:, 3] >= BOX[1]) & (a[:, 3] <= BOX[3])] if want_trees else a[:0]
    for k in sorted({int(x) for x in tb[:, 0]}):
        for part in t['prototypes'][k]['parts']:
            if '_LOD1' not in part['mesh'] and '_LOD2' not in part['mesh']:
                ids.add(part['mesh'])
    mesh_mats = set()
    for d in m['meshes']['list']:
        if d['id'] in ids:
            mesh_mats.update(d.get('materials', []))
    mats = {n: game_material(matd[n]) for n in mesh_mats if n in matd}
    meshes = load_meshes(m, ids, mats, blob)
    col = bpy.data.collections.new('Base'); sc.collection.children.link(col)
    placed = 0
    for i in want:
        me, pos = meshes.get(i['mesh'], (None, None))
        if me is None:
            continue
        r, ins, world = roots[i['root']]
        ob = bpy.data.objects.new(i.get('name') or me.name, me)
        ob.matrix_world = mat4(i['matrix'])
        ob['root'] = r['name']; ob['group'] = r.get('group', '')
        col.objects.link(ob)
        placed += 1
    # trees: one collection per prototype, instances as empties
    tcol = bpy.data.collections.new('Trees'); sc.collection.children.link(tcol)
    protos = {}
    for k in sorted({int(x) for x in tb[:, 0]}):
        p = t['prototypes'][k]
        src = bpy.data.collections.new('Tree_' + p['name'])
        for part in p['parts']:
            if '_LOD1' in part['mesh'] or '_LOD2' in part['mesh']:
                continue
            me = meshes.get(part['mesh'], (None, None))[0]
            if me is None:
                continue
            o = bpy.data.objects.new(p['name'] + '_part', me); o.matrix_world = mat4(part['matrix']); src.objects.link(o)
        protos[k] = src
    for row in tb:
        k = int(row[0])
        e = bpy.data.objects.new('T_' + t['prototypes'][k]['name'], None)
        e.instance_type = 'COLLECTION'; e.instance_collection = protos[k]
        e.location = B(row[1], row[3], row[2])
        e.rotation_euler = (0, 0, -row[4])
        e.scale = (row[5], row[5], row[6])
        tcol.objects.link(e)
    print(f'[base] objects {placed}, trees {len(tb)} ({len(protos)} kinds), materials {len(mats)}', flush=True)
    return m


# ---------------------------------------------------------------- light, cameras, render
def world_overcast():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('Overcast'); w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.66, 0.68, 0.70, 1); bg.inputs['Strength'].default_value = 1.35
    sc.world = w
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = 1.2; ld.angle = math.radians(12); ld.color = (1.0, 0.96, 0.90)
    so = bpy.data.objects.new('Sun', ld); sc.collection.objects.link(so)
    el, az = math.radians(24.0), math.radians(200.0)
    d = Vector((-math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def ground_h(ux, uz):
    h = np.load(os.path.join(D, 'data', 'ground_crop.npy')); g = json.load(open(os.path.join(D, 'data', 'ground_crop.json')))
    fx = (ux - g['x0']) / g['step'] - g['i0']; fz = (uz - g['z0']) / g['step'] - g['j0']
    j, i = int(np.clip(fx, 0, h.shape[1] - 2)), int(np.clip(fz, 0, h.shape[0] - 2))
    return float(h[i, j])


VIEWS = {   # tools/snow_qa/configs/look_points.json (eye, look in Unity; heights over the ground); horizontal FOV as the
            # frames (CameraSettings fov, the frames were taken at 110)
    'L12_base_yard': ((322.0, 1.7, -322.0), (366.0, 1.5, -366.0), 110.0),
    'L12_base_gate': ((326.9, 1.7, -329.3), (343.9, 8.0, -359.9), 110.0),
    'L12_base_back': ((381.0, 1.7, -396.0), (322.0, 1.5, -325.0), 110.0),
    'L12_base_air': ((286.0, 40.0, -266.0), (345.0, 0.0, -360.0), 90.0),
}


def cameras():
    out = {}
    for k, (e, l, fov) in VIEWS.items():
        eye = B(e[0], e[2], ground_h(e[0], e[2]) + e[1]); tgt = B(l[0], l[2], ground_h(l[0], l[2]) + l[1])
        cd = bpy.data.cameras.new(k); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(fov); cd.clip_start = 0.1; cd.clip_end = 3000
        co = bpy.data.objects.new(k, cd); bpy.context.scene.collection.objects.link(co)
        co.location = eye; co.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        out[k] = co
    return out


def setup_render(spp=16, res=(1280, 720)):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 12; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 1
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.05
    sc.render.image_settings.file_format = 'PNG'


TREE_DRAW = 85.0     # ForestTreeRenderer.drawDistance: the game draws no trees farther than this from the camera (x, z)


def cull_trees(cam, on=True):
    tc = bpy.data.collections.get('Trees')
    if tc is None:
        return
    c = cam.matrix_world.translation
    for o in tc.objects:
        d = math.hypot(o.location.x - c.x, o.location.y - c.y)
        o.hide_render = on and d > TREE_DRAW


def render(cams, views, folder, suffix=''):
    os.makedirs(folder, exist_ok=True)
    sc = bpy.context.scene
    for v in views:
        sc.camera = cams[v]; sc.render.filepath = os.path.join(folder, v + suffix + '.png')
        cull_trees(cams[v], on=not v.endswith('_air'))
        sc['fog_k'] = 0.45 if v.endswith('_air') else 1.0
        bpy.ops.render.render(write_still=True)
        print('rendered', v, flush=True)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    out = argv[0]; views = argv[1].split(',') if len(argv) > 1 and argv[1] != '-' else []
    spp = int(argv[2]) if len(argv) > 2 else 16
    res = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (1280, 720)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene['fog_k'] = 1.0
    build()
    world_overcast()
    cams = cameras()
    setup_render(spp, res)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    render(cams, views, os.environ.get('OUTDIR', os.path.join(D, 'rend', 'before')))


if __name__ == '__main__':
    main()
