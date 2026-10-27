"""The old spare van (VISION 8 / RESEARCH_SURVIVAL: 'начальник присылает старый запасной фургон, хуже, без лебёдки'): van3
repainted - the same model, UVs and parts; a new body texture only, and no winch.
The fleet's red-and-white gives way to the old khaki the bukhanka came in: faded to a dusty olive on the tops, a lot more
rust (sills, arches, the window corners, runs down the sides), chips to primer everywhere it rubs,
road grime and salt low. The body is baked from van3.blend in van3's own UVs (PSX map), so the
texture drops onto the existing model: T_VanOld_Body_BaseColor (256, 64 colours, Bayer, AO in the colour).
python3 -I vanold.py <van3_dir> <out_dir> -> out_dir/tex/T_VanOld_Body_BaseColor.png, out_dir/vanold.blend
vanold.blend: van3.blend with M_VanOld_Body on the body faces, Winch_Drum / Winch_Clutch / Winch_Hook removed; the other
textures are van3's (relative path ../van3/tex)."""
import sys, os, math, json
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector
import psxlib as P
import psxbake as PB
from noise import ss, mixc, fbm
from psxbake import lin

a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
VAN3, OUT = a[0], a[1]
TEX = os.path.join(OUT, 'tex')
os.makedirs(TEX, exist_ok=True)
PB.POS_SCALE = 8.0
SIZE, OVS = 256, 4
WHEEL_X, WHEEL_Z = (1.207, -1.203), 0.323
Z_WIN_BOT = 9.0
C = dict(rust_d=lin(74, 38, 20), rust_o=lin(146, 70, 30), primer=lin(146, 144, 134), dirt=lin(58, 50, 40),
         salt=lin(172, 170, 160), under=lin(28, 26, 23))
PAINT, FADE, REPAINT = lin(94, 102, 64), lin(150, 148, 112), lin(80, 94, 58)
WINCH = ('Winch_Drum', 'Winch_Clutch', 'Winch_Hook')


def paint_body(Pp, Nn, ao, aa, door_box):
    x, y, z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
    n_lo = fbm(Pp, 1.1, 3, seed=1)
    n_mid = fbm(Pp, 6.0, 3, seed=2)
    n_hi = fbm(Pp, 38.0, 2, seed=3)
    up = np.clip(Nn[:, 2], 0, 1)
    col = np.tile(PAINT, (len(x), 1))
    door = np.zeros(len(x), bool)                                        # (the doors share UV islands: no odd panel)
    col = col * (0.86 + 0.22 * n_lo + 0.12 * (n_mid - 0.5) + 0.16 * (n_hi - 0.5))[:, None]
    fade = ss(0.25, 0.95, up) * (0.50 + 0.30 * n_lo) + 0.12 * ss(0.4, 0.8, n_lo)
    col = mixc(col, FADE, fade * (~door))
    patch = ss(0.64, 0.67, fbm(Pp, 2.4, 2, seed=5)) * (1 - up) * (~door)
    col = mixc(col, REPAINT, patch * 0.85)
    low = 1 - ss(0.46, 0.86, z)
    arch = np.zeros_like(x)
    for xc in WHEEL_X:
        r = np.sqrt((x - xc) ** 2 + (z - WHEEL_Z) ** 2)
        arch = np.maximum(arch, (1 - ss(0.43, 0.60, r)) * (np.abs(Nn[:, 1]) > 0.3))
    cav = ss(0.62, 0.30, ao)
    win = ss(0.12, 0.0, np.abs(z - Z_WIN_BOT)) * (np.abs(Nn[:, 1]) > 0.5)
    src = np.clip(np.maximum.reduce([low * 0.95, arch, cav * 0.65, win * 0.7]), 0, 1)
    rn = fbm(Pp, 13.0, 3, seed=7)
    rb = fbm(Pp, 44.0, 2, seed=8)
    rv = rn * 0.72 + rb * 0.28
    rust = ss(0.63 - 0.40 * src, 0.70 - 0.40 * src, rv) * (src > 0.03)
    st = fbm(Pp * np.array([1, 1, 0.10], np.float32), 22.0, 2, seed=12)
    runs = ss(0.66, 0.76, st) * (1 - up) * np.clip(win * 2 + low * 0.7 + rust, 0, 1)
    col = mixc(col, C['rust_d'], np.clip(rust * 0.95 + runs * 0.55, 0, 1))
    col = mixc(col, C['rust_o'], rust * ss(0.40, 0.70, rb) * 0.7)
    chip = ss(0.84 - 0.12 * src, 0.87 - 0.12 * src, fbm(Pp, 62.0, 2, seed=9))
    col = mixc(col, C['primer'], chip * (1 - rust) * 0.9)
    grime = (1 - ss(0.40, 1.05, z)) * (0.55 + 0.45 * n_mid)
    spray = np.zeros_like(x)
    for xc in WHEEL_X:
        spray = np.maximum(spray, np.exp(-((x - (xc - 0.55)) / 0.45) ** 2) * (1 - ss(0.35, 1.25, z)))
    spray = np.maximum(spray, (x < -2.0) * (1 - ss(0.4, 1.4, z)))
    rain = ss(0.60, 0.72, fbm(Pp * np.array([1, 1, 0.07], np.float32), 16.0, 2, seed=10)) * (1 - up)
    col = mixc(col, C['dirt'], np.clip(grime * 0.55 + spray * 0.45 + rain * 0.30 + cav * 0.40, 0, 0.85))
    salt = (1 - ss(0.42, 0.85, z)) * ss(0.46, 0.72, fbm(Pp, 7.5, 3, seed=11))
    col = mixc(col, C['salt'], salt * 0.45)
    col = mixc(col, C['under'], ss(-0.25, -0.7, Nn[:, 2]))
    return col


def body_copies(objs):
    """temporary copies holding only the body-material faces (the other atlases share the PSX map's 0..1 space)"""
    out = []
    for o in objs:
        me = o.data.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        idx = [i for i, m in enumerate(o.data.materials) if m and m.name == 'M_Van_Body']
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in idx], context='FACES')
        bm.to_mesh(me)
        bm.free()
        me.materials.clear()
        c = bpy.data.objects.new(o.name + '_bake', me)
        bpy.context.scene.collection.objects.link(c)
        c.matrix_world = o.matrix_world.copy()
        me.uv_layers.active = me.uv_layers['PSX']
        out.append(c)
    return out


def main():
    from PIL import Image
    bpy.ops.wm.open_mainfile(filepath=os.path.join(VAN3, 'van3.blend'))
    body = [o for o in bpy.data.objects if o.type == 'MESH' and any(m and m.name == 'M_Van_Body' for m in o.data.materials)]
    print('body objects', [o.name for o in body])
    bpy.context.view_layer.update()
    dp = bpy.data.objects['doorP']
    bb = [dp.matrix_world @ Vector(c) for c in dp.bound_box]
    door_box = (np.array([min(v[i] for v in bb) for i in range(3)]), np.array([max(v[i] for v in bb) for i in range(3)]))
    tmp = body_copies(body)
    for o in body:
        o.hide_render = False
    hi = SIZE * OVS
    pos = PB.bake_pass(tmp, 'pos', hi)
    nor = PB.bake_pass(tmp, 'nor', hi)
    ao = PB.bake_pass(tmp, 'ao', hi, samples=40, ao_dist=0.35)[..., 0]
    cov = P.coverage_mask(tmp, hi, uv_name='PSX')
    baked = np.abs(np.linalg.norm(nor[..., :3] * 2 - 1, axis=-1) - 1) < 0.1
    cov &= baked
    Pp = (pos[..., :3] - 0.5) * PB.POS_SCALE
    Nn = nor[..., :3] * 2 - 1
    Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-6)
    ci = cov.reshape(-1)
    A = P.area3d(tmp)
    fill = max(P.uv_fill(tmp), 1e-6)
    aa = 1.0 / (SIZE * math.sqrt(fill / A)) / OVS
    out = paint_body(Pp.reshape(-1, 3)[ci].astype(np.float32), Nn.reshape(-1, 3)[ci].astype(np.float32), ao.reshape(-1)[ci], aa,
                     door_box)
    col = np.zeros((hi * hi, 3), np.float32)
    col[ci] = out
    q, _ = PB.psx_step(col.reshape(hi, hi, 3), np.clip(ao, 0, 1), cov, np.zeros((hi, hi), np.float32), OVS, ao_min=0.35)
    lo_cov = P.blocks(cov.astype(np.float32), OVS).mean(2) > 0.25      # (psx_step fills the gutters from the nearest texel)
    p = os.path.join(TEX, 'T_VanOld_Body_BaseColor.png')
    Image.fromarray(q, 'RGB').save(p)
    print('texture', p, 'coverage', round(float(lo_cov.mean()), 3), 'colours', len(np.unique(q.reshape(-1, 3), axis=0)))
    for o in tmp:
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)
    # the variant .blend: the new body material, no winch, van3's other textures by relative path
    m_old = bpy.data.materials['M_Van_Body'].copy()
    m_old.name = 'M_VanOld_Body'
    for nd in m_old.node_tree.nodes:
        if nd.type == 'TEX_IMAGE':
            img = bpy.data.images.load(p, check_existing=False)
            img.name = 'T_VanOld_Body_BaseColor.png'
            nd.image = img
    for o in body:
        for i, m in enumerate(o.data.materials):
            if m and m.name == 'M_Van_Body':
                o.data.materials[i] = m_old
    removed = []
    for nm in WINCH:
        ob = bpy.data.objects.get(nm)
        if ob:
            for ch in list(ob.children_recursive):
                removed.append(ch.name)
                bpy.data.objects.remove(ch)
            removed.append(nm)
            bpy.data.objects.remove(ob)
    for img in bpy.data.images:
        if img.name == 'T_VanOld_Body_BaseColor.png':
            img.filepath = '//tex/T_VanOld_Body_BaseColor.png'
        elif img.source == 'FILE' and img.filepath.startswith('//tex/'):
            img.filepath = '//../van3/tex/' + img.filepath[len('//tex/'):]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'vanold.blend'), relative_remap=False)
    json.dump(dict(removed=removed, body_objects=[o.name for o in body], texture='tex/T_VanOld_Body_BaseColor.png',
                   replaces='tex/T_Van_Body_BaseColor.png (van3)', material='M_VanOld_Body (instead of M_Van_Body)'),
              open(os.path.join(OUT, 'vanold.json'), 'w'), indent=1)
    print('removed', removed)


main()
