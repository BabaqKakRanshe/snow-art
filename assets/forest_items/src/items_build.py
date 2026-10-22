"""Forest items (Update 6) build: items_kit's 84 KBs -> one object per item with its origin at Update 3's origin (the
print / lens / water KBs joined in), the shared PSX atlas Props (the generator shed's props density, 64 px per metre;
items_paint), the printed panel (items_tex, point-filtered pixel art), Update 3's M_TorchLens and M_Water by name.
The items are laid out on a grid for the bake (each on the ground for its contact shading; the keys and the padlock
hang free, the flashlight lies on its side) and moved back to the origin afterwards.
Checks: each item's box against Update 3's (Forest_Items.json colliders and the placements stay valid), the special
points (the flashlight's light, the jerrycan's spout and grip), triangles.
python3 -I items_build.py [--draft] [--only Item_A,Item_B] -> out/items.blend, out/items.json, tex/items/*"""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import gen_kit as K
import bld_common as BC

DRAFT = '--draft' in sys.argv
ONLY = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'items')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
INFO = {}
U3 = json.load(open(os.path.join(HERE, 'items_u3.json')))
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3M = {m['name']: m for m in json.load(open(SCR + 'u3/Assets/Locations/Forest/Data/Forest_Materials.json'))['materials']}
PB.POS_SCALE = 32.0
HANG = ('Item_Key_Garage', 'Item_Key_Generator', 'Item_Key_Hauptgebaeude', 'Item_Key_Schranke', 'Item_Padlock')
LIFT = {'Item_Flashlight': 0.0285}
for n in HANG:
    LIFT[n] = 0.12


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
import items_tex as IT
PANEL = IT.build(TEX)
import items_kit as IK

names = [n for n in IK.ITEMS if ONLY is None or n in ONLY]
for n in names:
    k = K.kb(n, 'Props')
    pk = K.kb(n + '_Print', 'panel')
    IK.ITEMS[n](k, pk, n)
    K.part(n, 'static', (0, 0, 0), parent=None, note=U3.get(n, {}).get('catalog', {}).get('label', 'new'))
    K.part(n + '_Print', 'static', (0, 0, 0), parent=n)
    for kind, lst in IK.SPECIAL.get(n, {}).items():
        for e in lst:
            K.part(e, 'static', (0, 0, 0), parent=n)
log('items', len(names), 'KBs', len(K.KBS))

# ------------------------------------------------------------------ objects; the layout for the bake
objs = {}
for name, k in K.KBS.items():
    if not k.bm.faces:
        k.bm.free()
        continue
    bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=2e-5)
    objs[name] = k.to_object(name, pivot=Vector((0, 0, 0)))
roots = [n for n in names if n in objs]


def bbox(o_list):
    vs = np.array([tuple(o.matrix_world @ v.co) for o in o_list for v in o.data.vertices])
    return vs.min(0), vs.max(0)


members = {n: [objs[m] for m in objs if m == n or m.startswith(n + '_')] for n in roots}
boxes = {n: bbox(members[n]) for n in roots}
# shelf layout: biggest footprints first, rows along x
order = sorted(roots, key=lambda n: -max(boxes[n][1][0] - boxes[n][0][0], boxes[n][1][1] - boxes[n][0][1]))
LAYOUT, x, y, row_h, ROW_W = {}, -12.0, -12.0, 0.0, 24.0
CELLS = {}
for n in order:
    lo, hi = boxes[n]
    w, d = hi[0] - lo[0] + 0.30, hi[1] - lo[1] + 0.30
    if x + w > -12.0 + ROW_W:
        x, y, row_h = -12.0, y + row_h, 0.0
    off = Vector((x - lo[0] + 0.15, y - lo[1] + 0.15, LIFT.get(n, 0.0)))
    LAYOUT[n] = tuple(off)
    CELLS[n] = (x, x + w, y, y + d)
    x += w
    row_h = max(row_h, d)
assert y + row_h < 12.0, 'layout too big for the bake range'
for n in roots:
    for o in members[n]:
        o.location = Vector(LAYOUT[n])
bpy.context.view_layer.update()
log('layout rows to y', round(y + row_h, 2))

# ------------------------------------------------------------------ the atlas Items (+ the ground for contact shading)
import items_paint as IP
IP.LAYOUT, IP.CELLS = LAYOUT, CELLS
group = [objs[n] for n in roots]
me = bpy.data.meshes.new('AOG')
me.from_pydata([(-13, -13, 0), (13, -13, 0), (13, 13, 0), (-13, 13, 0)], [], [(0, 1, 2, 3)])
ground = bpy.data.objects.new('AOG', me)
bpy.context.scene.collection.objects.link(ground)
others = [o for o in objs.values() if o not in group]
SPEC = {'Props': dict(cap=64.0, ao_min=0.42, ao_dist=0.045, rough=0.8, zs=None, max=1024, ncol=128)}   # 84 colourful things
INFO['atlases'] = {}
BC.bake_groups({'Props': group}, ['Props'], SPEC, IP.paint_items, TEX, 'T_Item_', 'M_Item_', prio=IP.PRIO,
               only=(set() if DRAFT else None), colour_of=IP.draft_colour, hide_always=others, log=log, info=INFO['atlases'])
bpy.data.objects.remove(ground)
bpy.data.meshes.remove(me)

# ------------------------------------------------------------------ explicit materials; one mesh per item
m_panel = PB.tex_mat('M_Item_Panel', PANEL, PANEL, 0.0, rough=0.6)
m_lens = BC.u3_mat('M_TorchLens', U3M)
m_water = BC.u3_mat('M_Water', U3M)
m_disp = PB.tex_mat('M_RadioDisplay', PANEL, os.path.join(TEX, 'T_Item_Panel_Emission.png'), 0.0, rough=0.3)  # X08: -> M_RadioDisplayOn
for name, o in objs.items():
    a = K.ATLAS[name]
    if a == 'Props':
        continue
    o.data.materials.clear()
    o.data.materials.append({'panel': m_panel, 'lens:torch': m_lens, 'water': m_water, 'display': m_disp}[a])
for n in roots:
    extra = [o for o in members[n] if o.name != n]
    if extra:
        P.select_only(extra + [objs[n]], active=objs[n])
        bpy.ops.object.join()
    o = objs[n]
    o.location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
BC.psx_uv_only()

# ------------------------------------------------------------------ checks against Update 3
rep = {}
for n in roots:
    o = bpy.data.objects[n]
    vs = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = vs.min(0), vs.max(0)
    u3 = U3.get(n)
    r = dict(bounds=[lo.round(4).tolist(), hi.round(4).tolist()], tris=P.tri_count(o),
             materials=[m.name for m in o.data.materials])
    if u3:
        ulo, uhi = np.array(u3['bounds'][0]), np.array(u3['bounds'][1])
        if n not in HANG and n != 'Item_Flashlight':
            ulo[2] = max(ulo[2], 0.0)                          # Update 3's few sunk models now rest on z = 0
        r['u3_bounds'] = [ulo.round(4).tolist(), uhi.round(4).tolist()]
        r['d_lo'] = (lo - ulo).round(4).tolist()
        r['d_hi'] = (hi - uhi).round(4).tolist()
        r['max_dev'] = float(np.abs(np.concatenate([lo - ulo, hi - uhi])).max().round(4))
        r['u3_tris'] = u3['tris']
    rep[n] = r
INFO['items'] = rep
bad = {n: r['max_dev'] for n, r in rep.items() if r.get('max_dev', 0) > 0.012}
log('bounds off by > 12 mm:', bad)
# special points (Blender frame of the item; Forest_Items.json is in Unity: (-x, z, -y))
cat = {n: U3[n]['catalog'] for n in roots if n in U3}
spec = {}
if 'Item_Flashlight' in roots:
    o = bpy.data.objects['Item_Flashlight']
    lens = [o.matrix_world @ v.co for v in o.data.vertices]
    xm = max(v.x for v in lens)
    spec['Item_Flashlight'] = dict(lens_front_x=round(xm, 4), light_p_blender=[-cat['Item_Flashlight']['light']['p'][0], 0.0, 0.0])
if 'Item_Jerrycan20' in roots:
    sp = cat['Item_Jerrycan20']['spout']
    gr = cat['Item_Jerrycan20']['grip']
    spec['Item_Jerrycan20'] = dict(spout_blender=[-sp[0], -sp[2], sp[1]], grip_blender=[-gr[0], -gr[2], gr[1]])
INFO['special'] = spec
INFO['tris'] = sum(r['tris'] for r in rep.values())
INFO['layout'] = {n: list(v) for n, v in LAYOUT.items()}
log('tris', INFO['tris'], 'items', len(rep))
sfx = '_draft' if DRAFT else ('_test' if ONLY else '')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f'items{sfx}.blend'))
json.dump(BC.nz(INFO), open(os.path.join(OUT, f'items{sfx}.json'), 'w'), indent=1, ensure_ascii=False)
log('saved items' + sfx)
