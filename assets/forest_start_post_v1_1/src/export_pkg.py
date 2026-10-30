"""forest_start_post_v1: the start post concept (concept.py) exported for Unity.
 - Forest_StartPost.fbx (world space): the road strip in four 32 m pieces (SP_Road_0..3, baked colour texture each),
   the snow layer of the pad and the post (SP_SnowLayer: clean / trodden), the zone fence plates (SP_Plate_0..3) and the
   snow caps of the post's props (SPC_*, each in its prop's own space: the step hangs it under that prop);
 - StartWache.fbx (the guard house's own space: x = -u... i.e. Unity +Z = the big window): Wache_Body, Wache_Glass,
   Wache_Lamp, Wache_Lens, Wache_Interior, Wache_StoveGlow, Wache_WinGlow, Wache_Snow, Wache_Ice;
 - pkg_build/export.json: objects, their materials in slot order, caps and their props, the road cut, the paint and the
   clearing areas, the house's anchors (Unity local), the ground delta (ground_delta.f32 + .json) and the road textures.
python3.11 -I export_pkg.py"""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

P_ = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(P_)
sys.path.insert(0, D)
import start_scene as S
import frame as F
import concept as C
from scipy import ndimage
from PIL import Image

OUT = os.path.join(D, 'pkg_build')
GT = S.GROUND_TEX
RNG = random.Random(2911)
HX, HY, T_, TOP, FL = 1.9, 2.0, 0.25, 2.95, 0.35
DOOR = (0.5, 1.5, FL, 2.55)                 # Blender local y0, y1, z0, z1 of the door opening (the booth's door: 0.98 x 2.17 m)
LAMP_Z = 2.82


def to_unity_local(p):
    x, y, z = p
    return [round(-x, 4), round(z, 4), round(-y, 4)]


# ------------------------------------------------------------------ helpers
def mesh_obj(name, verts, faces, mats, uvs=None, mi=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if uvs is not None:
        layer = me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            for li in p.loop_indices:
                layer.data[li].uv = uvs[me.loops[li].vertex_index]
    for m in mats:
        me.materials.append(m)
    if mi is not None:
        me.polygons.foreach_set('material_index', np.asarray(mi, np.int32))
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box_uv(ob, tiles):
    """box projection per face by its dominant normal axis, tile size per material slot (metres)"""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers[0]
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        t = tiles[p.material_index] if p.material_index < len(tiles) else 1.0
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                a, b = co.y, co.z
            elif ax == 1:
                a, b = co.x, co.z
            else:
                a, b = co.x, co.y
            uv.data[li].uv = (a / t, b / t)


def drop_unused_slots(ob):
    me = ob.data
    used = sorted({p.material_index for p in me.polygons})
    remap = {old: new for new, old in enumerate(used)}
    mats = [me.materials[i] for i in used]
    for p in me.polygons:
        p.material_index = remap[p.material_index]
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    return [m.name for m in mats]


# ------------------------------------------------------------------ the road strip, baked
def srgb_to_lin(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055) * 255.0


def road_pieces(tex_dir, ppm=64):
    R = C.ROADGRID
    ss, vv = R['ss'], R['vv']
    nv, ns = R['h'].shape
    texs = {k: srgb_to_lin(np.asarray(Image.open(GT + f'T_GR_{k}_A.png').convert('RGB'), np.float64)) for k in ('Floor', 'Track', 'Ruts', 'Gravel')}
    tint = {'Floor': 1.04, 'Track': 0.98, 'Ruts': 1.12, 'Gravel': 0.86}
    rows_per = 80
    pieces = []
    k = 0
    r0 = 0
    while r0 < nv - 1:
        r1 = min(r0 + rows_per, nv - 1)
        if nv - 1 - r1 < rows_per // 4:                                   # no sliver at the end: the last piece takes it
            r1 = nv - 1
        L = vv[r1] - vv[r0]
        W_px, H_px = int(round(14.0 * ppm)), int(round(L * ppm))
        # mesh
        rows = np.arange(r0, r1 + 1)
        x, z = R['x'][rows], R['z'][rows]
        hh = (R['gh'] + R['h'])[rows]
        co = np.stack([-x, -z, hh], -1).reshape(-1, 3)
        uu = (ss + 7.0) / 14.0
        vcoord = (vv[rows] - vv[r0]) / L
        U_, V_ = np.meshgrid(uu, vcoord)
        uvs = [tuple(p) for p in np.stack([U_, V_], -1).reshape(-1, 2)]
        n_r, n_s = len(rows), ns
        idx = np.arange(n_r * n_s).reshape(n_r, n_s)
        faces = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
        name = 'SP_Road_%d' % k
        mat = bpy.data.materials.new('M_SP_Road_%d' % k)
        ob = mesh_obj(name, co, faces, [mat], uvs=uvs, smooth=True)
        if ob.data.polygons[len(ob.data.polygons) // 2].normal.z < 0:
            ob.data.flip_normals()
        # texture: texel centres -> grid coordinates -> weights and world position -> ground layers in the terrain mapping
        cs = -7.0 + (np.arange(W_px) + 0.5) / ppm
        ts = vv[r0] + (np.arange(H_px) + 0.5) / ppm
        S_, T2 = np.meshgrid(cs, ts)                                        # rows from v0 up
        fs = (S_ - ss[0]) / (ss[1] - ss[0]); ft = (T2 - vv[0]) / (vv[1] - vv[0])
        coords = np.stack([ft.ravel(), fs.ravel()])
        samp = {key: ndimage.map_coordinates(R[key], coords, order=1, mode='nearest').reshape(S_.shape) for key in ('wp', 'wr', 'wd', 'x', 'z')}
        gu, gv = samp['x'] / 2.0, samp['z'] / 2.0
        ci = (np.floor((gu - np.floor(gu)) * 64).astype(int)) % 64
        rb = (np.floor((gv - np.floor(gv)) * 64).astype(int)) % 64
        col = {key: texs[key][63 - rb, ci] * tint[key] for key in texs}
        c = col['Floor']
        for key, w in (('Track', 'wp'), ('Ruts', 'wr'), ('Gravel', 'wd')):
            ww = samp[w][..., None]
            c = c * (1 - ww) + col[key] * ww
        img = lin_to_srgb(c)[::-1].round().astype(np.uint8)                # picture rows top = far end (v 1)
        tn = 'T_SP_Road_%d.png' % k
        Image.fromarray(img, 'RGB').save(os.path.join(tex_dir, tn))
        pieces.append({'name': name, 'material': 'M_SP_Road_%d' % k, 'texture': tn, 'v0': float(vv[r0]), 'v1': float(vv[r1]), 'px': [W_px, H_px]})
        k += 1
        r0 = r1
    print('[pkg] road: %d pieces, v %.1f..%.1f' % (len(pieces), vv[0], vv[-1]), flush=True)
    return pieces


# ------------------------------------------------------------------ the snow layer
def snow_layer():
    ob = bpy.data.objects['SP_SnowLayer']
    me = ob.data
    dirt = np.zeros(len(me.vertices), np.float32); me.attributes['dirt'].data.foreach_get('value', dirt)
    m_clean = bpy.data.materials.new('M_SP_Snow'); m_trod = bpy.data.materials.new('M_SP_SnowTrodden')
    me.materials.clear(); me.materials.append(m_clean); me.materials.append(m_trod)
    mi = []
    for p in me.polygons:
        mi.append(1 if float(np.mean(dirt[list(p.vertices)])) > 0.25 else 0)
    me.polygons.foreach_set('material_index', np.asarray(mi, np.int32))
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (-co.x / 2.0, -co.y / 2.0)                       # Unity x / 2, z / 2: the terrain's own tiling
    me.attributes.remove(me.attributes['dirt'])
    print('[pkg] snow layer: %d faces, %d trodden' % (len(mi), sum(mi)), flush=True)
    return ob


# ------------------------------------------------------------------ caps in their props' space
def root_matrices():
    roots = {r['key']: r for r in C.MAPJ['roots']}
    return roots


def caps():
    roots = root_matrices()
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    count = {}
    mat = bpy.data.materials.get('M_SP_Snow') or bpy.data.materials.new('M_SP_Snow')
    for ob in list(bpy.data.objects):
        if not ob.name.endswith('_snow') or ob.type != 'MESH':
            continue
        src = bpy.data.objects.get(ob.name[:-5])
        if src is None or 'root_key' not in src:
            continue
        r = roots[src['root_key']]
        M_root0 = S.mat4(r['matrix']); M_inst0 = S.mat4(list(src['inst_m']))
        M_root = src.matrix_world @ (M_inst0.inverted() @ M_root0)           # the root now (after the concept's moves)
        ev = ob.evaluated_get(dg)
        tm = ev.to_mesh()
        verts = [M_root.inverted() @ (ob.matrix_world @ v.co) for v in tm.vertices]
        faces = [list(p.vertices) for p in tm.polygons]
        ev.to_mesh_clear()
        root_name = r['name']
        target = ('Structures/' + root_name) if r.get('group') == 'Structures' else root_name.split(' (')[0]
        k = count.get(target, 0); count[target] = k + 1
        name = 'SPC_%s_%d' % (target.replace('Structures/', ''), k)
        cap = mesh_obj(name, verts, faces, [mat], smooth=True)
        uvl = cap.data.uv_layers.new(name='UVMap')
        for p in cap.data.polygons:
            for li in p.loop_indices:
                co = cap.data.vertices[cap.data.loops[li].vertex_index].co
                uvl.data[li].uv = (co.x / 2.0, co.y / 2.0)
        t = M_root.translation
        ux, uz = -t.x, -t.y
        out.append({'name': name, 'target': target, 'x': round(ux, 3), 'z': round(uz, 3)})
        bpy.data.objects.remove(ob)
    print('[pkg] caps: %d' % len(out), flush=True)
    return out


# ------------------------------------------------------------------ plates
def plates():
    res = []
    k = 0
    for ob in list(bpy.data.objects):
        if not ob.name.startswith('SP_Plate'):
            continue
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        nm = 'SP_Plate_%d' % k
        no = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(no)
        me.materials.clear()
        me.materials.append(bpy.data.materials.get('M_SP_Plate') or bpy.data.materials.new('M_SP_Plate'))
        me.materials.append(bpy.data.materials.get('M_SP_PlateBack') or bpy.data.materials.new('M_SP_PlateBack'))
        for p in me.polygons:                                               # the face looks to -v (local -y), the back is plain
            p.material_index = 0 if (ob.matrix_world.to_3x3() @ Vector((0, -1, 0))).dot(p.normal) > 0 else 1
        bpy.data.objects.remove(ob)
        res.append(nm); k += 1
    return res


# ------------------------------------------------------------------ the guard house, in its own space
def house_parts():
    M = {n: bpy.data.materials.new(n) for n in ('M_SP_Plaster', 'M_SP_Plinth', 'M_SP_RoofEdge', 'M_SP_Frame', 'M_SP_Iron', 'M_SP_GlassKeep',
                                                 'M_SP_LensKeep', 'M_SP_Wood', 'M_SP_Blanket', 'M_SP_Paper', 'M_SP_Coat', 'M_SP_LampGlow',
                                                 'M_SP_StoveGlow', 'M_SP_WindowGlow', 'M_SP_Ice')}
    M['M_SP_Snow'] = bpy.data.materials.get('M_SP_Snow') or bpy.data.materials.new('M_SP_Snow')
    hx, hy, t = HX, HY, T_
    top, fl = TOP, FL
    body = C.MB('Wache_Body', [M['M_SP_Plaster'], M['M_SP_Plinth'], M['M_SP_RoofEdge'], M['M_SP_Frame'], M['M_SP_Iron']])
    PL, PN, RE, FR, IR = range(5)
    wx0, wx1, wz0, wz1 = -0.95, 0.85, 1.25, 2.35
    y0, y1 = -hy, -hy + t
    body.box((-hx, y0, 0), (wx0, y1, top), PL); body.box((wx1, y0, 0), (hx, y1, top), PL)
    body.box((wx0, y0, 0), (wx1, y1, wz0), PL); body.box((wx0, y0, wz1), (wx1, y1, top), PL)
    body.box((-hx, hy - t, 0), (hx, hy, top), PL)
    body.box((-hx, -hy + t, 0), (-hx + t, hy - t, top), PL)
    x0, x1 = hx - t, hx
    dy0, dy1, dz0, dz1 = DOOR
    segs = [(-hy + t, -1.5, None), (-1.5, -0.7, (1.35, 2.2)), (-0.7, dy0, None), (dy0, dy1, (0.0, dz1)), (dy1, hy - t, None)]
    for (ya, yb, op) in segs:
        if op is None:
            body.box((x0, ya, 0), (x1, yb, top), PL)
        else:
            if op[0] > 0:
                body.box((x0, ya, 0), (x1, yb, op[0]), PL)
            body.box((x0, ya, op[1]), (x1, yb, top), PL)
    # plinth band (the door's sill at the floor), roof slab, sills, the step
    body.box((-hx - 0.03, -hy - 0.03, -0.3), (dy0 * 0 + hx + 0.03, hy + 0.03, fl), PN)
    body.box((-hx - 0.3, -hy - 0.3, top), (hx + 0.3, hy + 0.3, top + 0.24), RE)
    body.box((wx0 - 0.05, -hy - 0.12, wz0 - 0.06), (wx1 + 0.05, -hy + 0.02, wz0), PN)
    body.box((hx - 0.02, -1.55, 1.29), (hx + 0.12, -0.65, 1.35), PN)
    body.box((hx, dy0 - 0.1, -0.1), (hx + 0.55, dy1 + 0.1, fl - 0.02), PN)

    def frame_y(xa, xb, za, zb, y, depth=0.08, bar=0.06):
        body.box((xa, y - depth / 2, za), (xb, y + depth / 2, za + bar), FR); body.box((xa, y - depth / 2, zb - bar), (xb, y + depth / 2, zb), FR)
        body.box((xa, y - depth / 2, za), (xa + bar, y + depth / 2, zb), FR); body.box((xb - bar, y - depth / 2, za), (xb, y + depth / 2, zb), FR)
        xm = (xa + xb) / 2; body.box((xm - bar / 2, y - depth / 2, za), (xm + bar / 2, y + depth / 2, zb), FR)
        zm = (za + zb) / 2 + 0.12; body.box((xa, y - depth / 2, zm - bar / 2), (xb, y + depth / 2, zm + bar / 2), FR)

    def frame_x(ya, yb, za, zb, x, depth=0.08, bar=0.06):
        body.box((x - depth / 2, ya, za), (x + depth / 2, yb, za + bar), FR); body.box((x - depth / 2, ya, zb - bar), (x + depth / 2, yb, zb), FR)
        body.box((x - depth / 2, ya, za), (x + depth / 2, ya + bar, zb), FR); body.box((x - depth / 2, yb - bar, za), (x + depth / 2, yb, zb), FR)
        ym = (ya + yb) / 2; body.box((x - depth / 2, ym - bar / 2, za), (x + depth / 2, ym + bar / 2, zb), FR)
    frame_y(wx0, wx1, wz0, wz1, -hy + 0.12)
    frame_x(-1.5, -0.7, 1.35, 2.2, hx - 0.12)
    # door frame (the booth's door IX_Door hangs in it)
    body.box((hx - 0.1, dy0 - 0.06, fl), (hx + 0.03, dy0, dz1 + 0.06), FR); body.box((hx - 0.1, dy1, fl), (hx + 0.03, dy1 + 0.06, dz1 + 0.06), FR)
    body.box((hx - 0.1, dy0 - 0.06, dz1), (hx + 0.03, dy1 + 0.06, dz1 + 0.06), FR)
    # stove pipe above the roof, cap
    px, py = -1.3, 1.35
    body.cyl((px, py, top + 0.6), 0.075, 1.2, IR, seg=10)
    body.cyl((px, py, top + 1.27), 0.16, 0.1, IR, seg=10, r2=0.02)
    parts = {'Wache_Body': body}
    glass = C.MB('Wache_Glass', [M['M_SP_GlassKeep']])
    glass.box((wx0, -hy + 0.115, wz0), (wx1, -hy + 0.125, wz1), 0)
    glass.box((hx - 0.125, -1.5, 1.35), (hx - 0.115, -0.7, 2.2), 0)
    parts['Wache_Glass'] = glass
    lamp = C.MB('Wache_Lamp', [M['M_SP_Iron']])
    lamp.box((hx, 0.97 + (dy0 + dy1) / 2 - 1.0, LAMP_Z - 0.02), (hx + 0.32, 1.03 + (dy0 + dy1) / 2 - 1.0, LAMP_Z + 0.02), 0)
    lamp.cyl((hx + 0.32, (dy0 + dy1) / 2, LAMP_Z - 0.06), 0.13, 0.1, 0, seg=10, r2=0.05)
    parts['Wache_Lamp'] = lamp
    lens = C.MB('Wache_Lens', [M['M_SP_LensKeep']])
    lens.cyl((hx + 0.32, (dy0 + dy1) / 2, LAMP_Z - 0.14), 0.05, 0.06, 0, seg=8)
    parts['Wache_Lens'] = lens
    inter = C.MB('Wache_Interior', [M['M_SP_Wood'], M['M_SP_Iron'], M['M_SP_Blanket'], M['M_SP_Paper'], M['M_SP_Coat'], M['M_SP_LampGlow']])
    WD, IRi, BL, PA, CO, BU = range(6)
    inter.box((-hx + t, -hy + t, fl - 0.08), (hx - t, hy - t, fl), WD)                              # floor boards
    tz = fl + 0.74
    inter.box((-0.95, -hy + t, tz - 0.04), (0.75, -hy + t + 0.65, tz), WD)                          # table under the window
    for (lx, ly) in ((-0.9, -hy + t + 0.05), (0.7, -hy + t + 0.05), (-0.9, -hy + t + 0.6), (0.7, -hy + t + 0.6)):
        inter.box((lx - 0.03, ly - 0.03, fl), (lx + 0.03, ly + 0.03, tz - 0.04), WD)
    inter.box((-0.7, -hy + t + 0.15, tz), (-0.4, -hy + t + 0.38, tz + 0.04), PA)                    # the post's log book
    inter.box((-0.25, -hy + t + 0.08, tz), (-0.02, -hy + t + 0.2, tz + 0.14), IRi)                  # radio
    inter.box((-0.35, -hy + t + 0.75, fl), (0.05, -hy + t + 1.15, fl + 0.45), WD)                    # chair
    inter.box((-0.35, -hy + t + 1.1, fl + 0.45), (0.05, -hy + t + 1.15, fl + 0.95), WD)
    inter.box((-1.6, 0.95, fl), (-1.05, 1.6, fl + 0.72), IRi)                                       # stove
    inter.cyl((px, py, (fl + 0.72 + top) / 2), 0.065, top - fl - 0.72, IRi, seg=8)                   # its pipe to the roof
    inter.box((-hx + t, -0.95, fl), (-hx + t + 0.8, 0.95, fl + 0.45), WD)                           # bunk, blanket
    inter.box((-hx + t + 0.02, -0.9, fl + 0.45), (-hx + t + 0.78, 0.9, fl + 0.55), BL)
    inter.box((hx - t - 0.12, dy1 + 0.05, 1.0), (hx - t - 0.02, dy1 + 0.2, 1.9), CO)                 # coat on the hook by the door
    inter.box((-0.5, hy - t - 0.01, 1.4), (-0.1, hy - t, 1.95), PA)                                 # calendar 1991
    inter.cyl((0.0, -0.2, top - 0.12), 0.05, 0.08, BU, seg=8)                                       # ceiling bulb
    parts['Wache_Interior'] = inter
    sg = C.MB('Wache_StoveGlow', [M['M_SP_StoveGlow']])
    sg.box((-1.05, 1.12, fl + 0.22), (-1.035, 1.45, fl + 0.3), 0)
    parts['Wache_StoveGlow'] = sg
    objs = {k: v.done() for k, v in parts.items()}
    for o in objs.values():
        bpy.context.scene.collection.objects.link(o)
    # window glow: single-sided quads just inside the panes, facing out (from inside they are culled)
    gy = -hy + 0.2
    gv = [(wx0 + 0.03, gy, wz0 + 0.03), (wx1 - 0.03, gy, wz0 + 0.03), (wx1 - 0.03, gy, wz1 - 0.03), (wx0 + 0.03, gy, wz1 - 0.03),
          (hx - 0.2, -1.47, 1.38), (hx - 0.2, -0.73, 1.38), (hx - 0.2, -0.73, 2.17), (hx - 0.2, -1.47, 2.17)]
    wg = mesh_obj('Wache_WinGlow', gv, [(0, 1, 2, 3), (4, 5, 6, 7)], [M['M_SP_WindowGlow']])
    for p in wg.data.polygons:                                             # the front quad must face -y, the side quad +x
        c = p.center
        want = Vector((0, -1, 0)) if c.y < -1.5 else Vector((1, 0, 0))
        if p.normal.dot(want) < 0:
            p.flip()
    objs['Wache_WinGlow'] = wg
    # roof snow: a 0.32 m cushion with rounded edges, cornices with icicles on the front and the road side
    sb = bmesh.new()
    r = bmesh.ops.create_cube(sb, size=1.0)
    bmesh.ops.transform(sb, matrix=Matrix.Translation((0, 0, top + 0.24 + 0.16)) @ Matrix.Diagonal((2 * hx + 0.5, 2 * hy + 0.5, 0.32, 1)), verts=r['verts'])
    bmesh.ops.bevel(sb, geom=list(sb.edges), offset=0.14, segments=3, affect='EDGES')
    roof_top = top + 0.24
    ice = bmesh.new()

    def cornice(a, b, out, rr, sag, ice_len, every, skip=None):
        a, b, out = Vector(a), Vector(b), Vector(out).normalized()
        d = b - a; Ln = d.length
        n = max(1, int(Ln / 0.6))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            p0 = a + d * t0 + out * (rr * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            p1 = a + d * t1 + out * (rr * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            dd = p1 - p0
            res = bmesh.ops.create_cone(sb, cap_ends=True, cap_tris=False, segments=8, radius1=rr * (0.75 + 0.5 * RNG.random()),
                                        radius2=rr * (0.75 + 0.5 * RNG.random()), depth=dd.length)
            q = dd.to_track_quat('Z', 'Y')
            bmesh.ops.transform(sb, matrix=Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), verts=res['verts'])
        s = 0.0
        while s < Ln:
            s += every[0] + (every[1] - every[0]) * RNG.random()
            if s >= Ln:
                break
            p = a + d * (s / Ln)
            if skip is not None and skip[0] <= p.y <= skip[1]:
                continue
            p = p + out * (rr * 0.9)
            ln = ice_len[0] + (ice_len[1] - ice_len[0]) * RNG.random() ** 2
            rad = 0.025 + 0.03 * RNG.random()
            res = bmesh.ops.create_cone(ice, cap_ends=True, cap_tris=False, segments=5, radius1=0.0, radius2=rad, depth=ln)
            bmesh.ops.transform(ice, matrix=Matrix.Translation(p + Vector((0, 0, -ln / 2 - rr * 0.3))), verts=res['verts'])
    cornice((-hx - 0.3, -hy - 0.3, roof_top + 0.22), (hx + 0.3, -hy - 0.3, roof_top + 0.22), (0, -1, 0), 0.17, 0.08, (0.1, 0.55), (0.22, 0.55))
    cornice((hx + 0.3, -hy - 0.3, roof_top + 0.22), (hx + 0.3, hy + 0.3, roof_top + 0.22), (1, 0, 0), 0.24, 0.12, (0.15, 0.8), (0.2, 0.5),
            skip=(dy0 - 0.1, dy1 + 0.1))
    me = bpy.data.meshes.new('Wache_Snow'); sb.to_mesh(me); sb.free(); me.materials.append(M['M_SP_Snow']); me.shade_smooth()
    so = bpy.data.objects.new('Wache_Snow', me); bpy.context.scene.collection.objects.link(so)
    uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.x / 2.0, co.y / 2.0)
    objs['Wache_Snow'] = so
    mi = bpy.data.meshes.new('Wache_Ice'); ice.to_mesh(mi); ice.free(); mi.materials.append(M['M_SP_Ice'])
    io = bpy.data.objects.new('Wache_Ice', mi); bpy.context.scene.collection.objects.link(io)
    objs['Wache_Ice'] = io
    # UVs: box projection, tile per material (plaster 4 m, plinth 1.5 m, wood 1 m)
    tiles = {'Wache_Body': [4.0, 1.5, 1.0, 1.0, 1.0], 'Wache_Interior': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]}
    for nm, o in objs.items():
        if nm in ('Wache_Snow',):
            continue
        box_uv(o, tiles.get(nm, [1.0] * max(1, len(o.data.materials))))
    anchors = {
        'door': {'centre': to_unity_local((HX - T_ / 2, (dy0 + dy1) / 2, dz0)), 'width': dy1 - dy0, 'height': dz1 - dz0, 'wallNormal': [-1, 0, 0]},
        'lamp': to_unity_local((HX + 0.32, (dy0 + dy1) / 2, LAMP_Z - 0.2)),
        'inside': to_unity_local((0.0, -0.2, TOP - 0.3)),
        'stove': to_unity_local((-0.95, 1.28, FL + 0.3)),
        'smoke': to_unity_local((px, py, TOP + 1.38)),
        'bounds': [to_unity_local((-HX, -HY, -0.3)), to_unity_local((HX, HY, TOP + 0.24))],
    }
    print('[pkg] house parts:', ', '.join(objs), flush=True)
    return objs, anchors


# ------------------------------------------------------------------ export
def export_fbx(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', use_tspace=False, use_triangles=True, colors_type='NONE', add_leaf_bones=False,
                             bake_anim=False, path_mode='STRIP', embed_textures=False, use_mesh_modifiers=True)


def frame_poly(us_vs):
    out = []
    for (u, v) in us_vs:
        x, z = F.uv_to_unity(u, v)
        out += [round(float(x), 3), round(float(z), 3)]
    return out


def corridor(half, v0, v1, step=2.0):
    vs = np.arange(v0, v1 + 1e-6, step)
    uc = np.interp(vs, C.CENTRE[0], C.CENTRE[1])
    du = np.gradient(uc, vs); tl = np.sqrt(1 + du ** 2)
    nu, nv = 1 / tl, -du / tl
    left = [(u - half * a, v - half * b) for u, v, a, b in zip(uc, vs, nu, nv)]
    right = [(u + half * a, v + half * b) for u, v, a, b in zip(uc, vs, nu, nv)]
    return frame_poly(left + right[::-1]), frame_poly(list(zip(uc, vs)))


def ground_delta(unity_dir):
    """the concept's ground (terrain(): H1, and the 12 cm under the road strip) minus the export's, on the map grid"""
    m = C.MAPJ['ground']
    g = json.load(open(os.path.join(D, 'data', 'ground_crop.json')))
    H0 = C.G0.h
    H1 = C.G.h
    me = bpy.data.objects['Ground'].data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co)
    H2 = co.reshape(-1, 3)[:, 2].reshape(H0.shape).astype(np.float64)
    d = (H2 - H0).astype(np.float32)
    d[np.abs(d) < 0.005] = 0.0
    full = np.zeros((m['nz'], m['nx']), np.float32)
    j0, i0 = g['j0'], g['i0']
    full[j0:j0 + d.shape[0], i0:i0 + d.shape[1]] = d
    full.tofile(os.path.join(unity_dir, 'ground_delta.f32'))
    zz, xx = np.nonzero(np.abs(full) >= 0.005)
    info = {'nx': m['nx'], 'nz': m['nz'], 'x0': m['x0'], 'z0': m['z0'], 'step': m['step'], 'file': 'ground_delta.f32',
            'blend': 'forest_start_post_v1 src/concept.py terrain() (map export 2026-10-28 21:41)', 'changed': int(len(zz)),
            'base': 'F:/ClaudeGames/snow/source/assets/forest_start_post_v1/unity/base_ground.r16', 'hmin': m['hmin'], 'hmax': m['hmax'],
            'raised_max': float(full.max()), 'lowered_max': float(-full.min()),
            'box': [float(m['x0'] + xx.min() * m['step']), float(m['z0'] + zz.min() * m['step']), float(m['x0'] + xx.max() * m['step']), float(m['z0'] + zz.max() * m['step'])]}
    json.dump(info, open(os.path.join(unity_dir, 'ground_delta.json'), 'w'), indent=1)
    print('[pkg] ground delta: %d samples, +%.2f / -%.2f m' % (info['changed'], info['raised_max'], info['lowered_max']), flush=True)
    return info


def main():
    os.makedirs(OUT, exist_ok=True)
    tex_dir = os.path.join(OUT, 'tex'); os.makedirs(tex_dir, exist_ok=True)
    unity_dir = os.path.join(OUT, 'unity'); os.makedirs(unity_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene['fog_k'] = 1.0
    S.build()
    C.build_concept()
    bpy.context.view_layer.update()
    gd = ground_delta(unity_dir)
    pieces = road_pieces(tex_dir)
    snow = snow_layer()
    cap_list = caps()
    plate_names = plates()
    house, anchors = house_parts()
    post_objs = [bpy.data.objects[p['name']] for p in pieces] + [snow] + [bpy.data.objects[n] for n in plate_names] + \
                [bpy.data.objects[c['name']] for c in cap_list]
    objects = []
    for o in post_objs:
        mats = drop_unused_slots(o)
        kind = 'road' if o.name.startswith('SP_Road') else 'snow' if o.name == 'SP_SnowLayer' else 'plate' if o.name.startswith('SP_Plate') else 'cap'
        objects.append({'name': o.name, 'materials': mats, 'collider': 'mesh' if kind in ('road', 'snow') else 'none', 'ground': kind in ('road', 'snow')})
    export_fbx(post_objs, os.path.join(unity_dir, 'Forest_StartPost.fbx'))
    parts = []
    for nm, o in house.items():
        mats = drop_unused_slots(o)
        parts.append({'mesh': nm, 'materials': mats})
    export_fbx(list(house.values()), os.path.join(unity_dir, 'StartWache.fbx'))
    # areas (Unity x, z)
    cut_poly, cline = corridor(9.5, C.V0 - 0.5, C.V1 + 2.0)
    tree_poly, _ = corridor(5.0, C.V0, C.V1)
    zone = frame_poly([(-24, -46), (12, -46), (12, 20), (-24, 20)])
    dead = F.uv_to_unity(-13.56, -7.25)
    data = {
        'pieces': pieces, 'objects': objects, 'caps': cap_list, 'wacheParts': parts, 'anchors': anchors,
        'roadCut': cut_poly, 'centreline': cline, 'treeBand': tree_poly, 'zone': zone,
        'deadLamp': [round(float(dead[0]), 3), round(float(dead[1]), 3)],
        'wind': [round(F.CO, 4), 0.0, round(-F.SI, 4)], 'ground': gd,
        'house': {'u': C.HOUSE['u'], 'v': C.HOUSE['v']}, 'v0': C.V0, 'v1': C.V1,
    }
    json.dump(data, open(os.path.join(OUT, 'export.json'), 'w'), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'export.blend'))
    print('[pkg] done: %d post objects, %d house parts, %d caps' % (len(post_objs), len(parts), len(cap_list)), flush=True)


if __name__ == '__main__':
    main()
