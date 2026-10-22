"""Main building draft: the shell / openings / rooms built with flat zone colours, quick renders (axonometric views
outside, plan cuts per level, room views) -> rend/main_draft/*.png.  python3 -I main_draft.py [views] [--parts]"""
import sys, os, math, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
from mathutils import Vector, Matrix
import gen_kit as K
import main_spec as S
import main_shell as MS

HERE = '/home/claude/uaz'
OUT = os.path.join(HERE, 'rend', 'main_draft')
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)

COL = {MS.Z_FACADE: (150, 148, 140), MS.Z_PLINTH: (80, 80, 78), MS.Z_BAND: (170, 168, 160), MS.Z_PARIN: (140, 138, 130),
       MS.Z_ROOF: (95, 92, 88), MS.Z_UPSTAND: (40, 40, 40), MS.Z_CONCIN: (160, 158, 150), MS.Z_PLASTER: (225, 218, 196),
       MS.Z_DADO: (150, 120, 80), MS.Z_STRIPE: (210, 120, 40), MS.Z_TILEW: (230, 232, 230), MS.Z_VENEERW: (150, 100, 60),
       MS.Z_CEIL: (235, 235, 230), MS.Z_CEILT: (220, 220, 215), MS.Z_FL_LINO: (160, 90, 60), MS.Z_FL_LINOG: (100, 120, 90),
       MS.Z_FL_CARPET: (90, 100, 120), MS.Z_FL_TILE: (200, 190, 170), MS.Z_FL_RAISED: (190, 190, 190),
       MS.Z_FL_BOARDS: (140, 90, 55), MS.Z_FL_CONC: (150, 150, 145), MS.Z_STAIR: (170, 168, 160),
       MS.Z_BASEB: (60, 50, 40), MS.Z_SILLIN: (200, 200, 195), MS.Z_BRICK: (150, 70, 50), MS.Z_CEILB: (150, 120, 80),
       MS.Z_SOFFIT: (140, 138, 132), MS.Z_REVEALX: (135, 133, 125), MS.Z_FL_GARAGE: (120, 120, 115),
       MS.Z_SLABEDGE: (120, 120, 120), K.Z_GALV: (175, 178, 176), K.Z_STEELBLK: (40, 40, 40)}
try:
    import main_open as MO
    COL.update(MO.DRAFT_COL)
except ImportError:
    MO = None
try:
    import main_rooms as MR
    COL.update(MR.DRAFT_COL)
except ImportError:
    MR = None
import main_fx as MFX
COL.update(MFX.DRAFT_COL)
LENS_COL = {'globe': (1.0, 0.85, 0.6), 'tube': (0.95, 0.97, 1.0), 'diffuser': (0.95, 0.97, 1.0), 'bulb': (1.0, 0.8, 0.5),
            'exit': (0.1, 1.0, 0.35), 'emlens': (1.0, 1.0, 0.95), 'halogen': (1.0, 0.85, 0.6), 'red': (1.0, 0.05, 0.03),
            'led': (0.2, 1.0, 0.3)}


def lin(c):
    return tuple(((v / 255.0) ** 2.2) for v in c)


cache = {}


def zmat(z):
    if z not in cache:
        m = bpy.data.materials.new(f'draft_{z}')
        m.use_nodes = True
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Base Color'].default_value = lin(COL.get(z, (255, 0, 255))) + (1,)
        pb.inputs['Roughness'].default_value = 0.8
        cache[z] = m
    return cache[z]


MS.build_shell()
if MO is not None:
    MO.build_openings()
if MR is not None and '--parts' in sys.argv:
    MR.build_rooms()
    MFX.build_fx()
    import main_signs as MSG
    MSG.build_signs()
import main_tex as MT
PANEL_B, PANEL_E = MT.build(os.path.join(HERE, 'tex', 'main'))
objs = []
for name, k in K.KBS.items():
    p = K.CONTRACT['parts'].get(name)
    o = k.to_object(name, pivot=Vector(p['pivot']) if p else None)
    me = o.data
    if K.ATLAS.get(name) == 'panel':
        m = bpy.data.materials.get('draft_panel')
        if m is None:
            m = bpy.data.materials.new('draft_panel')
            m.use_nodes = True
            nt = m.node_tree
            pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
            uvn = nt.nodes.new('ShaderNodeUVMap')
            uvn.uv_map = 'PSX'
            for img, sock in ((PANEL_B, 'Base Color'), (PANEL_E, 'Emission Color')):
                ti = nt.nodes.new('ShaderNodeTexImage')
                ti.image = bpy.data.images.load(img, check_existing=True)
                ti.interpolation = 'Closest'
                nt.links.new(uvn.outputs[0], ti.inputs[0])
                nt.links.new(ti.outputs[0], pb.inputs[sock])
            pb.inputs['Emission Strength'].default_value = 1.0
            pb.inputs['Roughness'].default_value = 0.6
        me.materials.append(m)
    elif K.ATLAS.get(name, '').startswith('lens:'):
        m = bpy.data.materials.new('lens_' + name)
        m.use_nodes = True
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        col = LENS_COL.get(K.ATLAS[name][5:], (1, 1, 1))
        pb.inputs['Base Color'].default_value = col + (1,)
        pb.inputs['Emission Color'].default_value = col + (1,)
        pb.inputs['Emission Strength'].default_value = 3.0
        me.materials.append(m)
    elif K.ATLAS.get(name) == 'glass':
        m = bpy.data.materials.new('glass_' + name)
        m.use_nodes = True
        pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Base Color'].default_value = (0.6, 0.7, 0.75, 1)
        pb.inputs['Alpha'].default_value = 0.25
        pb.inputs['Roughness'].default_value = 0.05
        me.materials.append(m)
    else:
        zl = [round(a.value) for a in me.attributes['zone'].data] if 'zone' in me.attributes else []
        idx = {}
        for z in sorted(set(zl)):
            idx[z] = len(me.materials)
            me.materials.append(zmat(z))
        for poly, z in zip(me.polygons, zl):
            poly.material_index = idx[z]
    objs.append(o)
for o in objs:                                                      # parts at their start state (shutters rolled up)
    p = K.CONTRACT['parts'].get(o.name)
    if p and p['kind'] == 'scale':
        o.scale.z = p['rest']
for nm, R in S.ROOMS.items():                                       # a working light per room for the draft views
    zc = R['c'] - 0.3 if nm != 'Treppenhaus' else 1.5
    for zz in ([zc] if nm != 'Treppenhaus' else [-1.5, 1.7, 5.0, 8.0]):
        L = bpy.data.lights.new('L_' + nm, 'POINT')
        L.energy = 120.0 * max(1.0, (R['x1'] - R['x0']) * (R['y1'] - R['y0']) / 20.0)
        L.shadow_soft_size = 0.4
        lo = bpy.data.objects.new('L_' + nm, L)
        lo.location = ((R['x0'] + R['x1']) / 2, (R['y0'] + R['y1']) / 2, zz)
        bpy.context.scene.collection.objects.link(lo)
print('objects', len(objs), 'tris', sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'main_draft.blend'))

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 12
sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
sc.cycles.max_bounces = 3
sc.render.resolution_x, sc.render.resolution_y = 1400, 900
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam


def look(o, eye, tgt, lens=28, ortho=None, clip=(0.05, 400)):
    o.location = Vector(eye)
    d = Vector(tgt) - Vector(eye)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    o.data.lens = lens
    o.data.clip_start, o.data.clip_end = clip
    if ortho:
        o.data.type = 'ORTHO'
        o.data.ortho_scale = ortho
    else:
        o.data.type = 'PERSP'


VIEWS = {
    'axo_se': dict(eye=(22, -24, 18), tgt=(-4, 0, 2), lens=30),
    'axo_nw': dict(eye=(-30, 22, 18), tgt=(-4, 0, 2), lens=30),
    'south': dict(eye=(-4, -30, 3), tgt=(-4, 0, 3), lens=26),
    'plan_UG': dict(eye=(-5, 0, 60), tgt=(-5, 0, 0), ortho=31, clip=(60 - (-1.8), 120), plan=True),
    'plan_EG': dict(eye=(-5, 0, 60), tgt=(-5, 0, 0), ortho=31, clip=(60 - 1.2, 120), plan=True),
    'plan_OG': dict(eye=(-5, 0, 60), tgt=(-5, 0, 0), ortho=31, clip=(60 - 4.6, 120), plan=True),
    'plan_roof': dict(eye=(-5, 0, 60), tgt=(-5, 0, 0), ortho=31, plan=True),
    'in_leitstand': dict(eye=(-4.6, -3.0, 1.6), tgt=(7.0, -4.0, 1.2), lens=18),
    'in_flur_eg': dict(eye=(-7.2, 0.0, 1.6), tgt=(7.0, 0.0, 1.2), lens=20),
    'in_kueche': dict(eye=(-1.0, -1.6, 5.0), tgt=(7.0, -5.0, 4.6), lens=18),
    'in_tower': dict(eye=(1.3, 1.5, 1.6), tgt=(-1.0, 6.5, 3.0), lens=16),
    'in_garage': dict(eye=(-8.6, 4.0, 1.7), tgt=(-17.0, -4.0, 1.0), lens=18),
    'in_leitstand2': dict(eye=(6.8, -2.0, 1.7), tgt=(-4.0, -3.6, 0.9), lens=18),
    'in_server': dict(eye=(7.2, 1.5, 1.7), tgt=(3.0, 5.0, 1.0), lens=18),
    'in_windfang': dict(eye=(-5.5, -1.6, 1.7), tgt=(-7.2, -5.2, 1.0), lens=18),
    'in_lager': dict(eye=(-2.4, 1.5, 1.7), tgt=(-7.0, 5.0, 1.0), lens=18),
    'in_garage2': dict(eye=(-17.2, -4.2, 1.8), tgt=(-9.0, 4.0, 0.8), lens=18),
    'in_kaserne': dict(eye=(-2.3, -1.6, 5.1), tgt=(-7.4, -4.6, 4.0), lens=18),
    'in_kaserne2': dict(eye=(-7.3, -5.3, 5.2), tgt=(-3.0, -1.4, 4.0), lens=18),
    'in_kueche2': dict(eye=(6.9, -5.3, 5.1), tgt=(3.0, -1.4, 4.2), lens=18),
    'in_kueche3': dict(eye=(3.0, -2.0, 5.0), tgt=(-1.4, -4.4, 3.9), lens=18),
    'in_waschraum': dict(eye=(-2.3, 1.5, 5.1), tgt=(-7.4, 5.0, 4.0), lens=18),
    'in_stationsleiter': dict(eye=(2.3, 1.5, 5.1), tgt=(7.4, 5.0, 4.0), lens=18),
    'in_heizung': dict(eye=(-1.6, -1.6, -1.3), tgt=(7.0, -4.0, -2.4), lens=18),
    'in_heizung2': dict(eye=(7.3, -5.3, -1.3), tgt=(2.0, -1.4, -2.0), lens=18),
    'in_flur_ug': dict(eye=(7.3, 0.6, -1.3), tgt=(-1.8, -0.4, -1.6), lens=20),
    'in_schaltraum': dict(eye=(2.3, 1.5, -1.3), tgt=(7.4, 5.0, -2.0), lens=18),
    'in_windfang2': dict(eye=(-6.4, -2.2, 1.6), tgt=(-6.4, -6.0, 1.2), lens=18),
    'ext_entrance': dict(eye=(-1.0, -13.0, 2.2), tgt=(-5.5, -6.5, 1.0), lens=24),
    'ext_roof': dict(eye=(12.0, -12.0, 14.0), tgt=(0.0, 0.0, 7.0), lens=24),
    'ext_garage': dict(eye=(-20.0, -12.0, 3.0), tgt=(-13.0, -5.0, 1.2), lens=24),
}
want = sys.argv[1].split(',') if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else list(VIEWS)
for v in want:
    c = VIEWS[v]
    up = c.get('plan')
    if up:
        cam.location = Vector(c['eye'])
        cam.rotation_euler = (0, 0, 0)
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = c['ortho']
        cam.data.clip_start, cam.data.clip_end = c.get('clip', (0.1, 200))
        sc.render.resolution_x, sc.render.resolution_y = 1500, 900
    else:
        look(cam, c['eye'], c['tgt'], c.get('lens', 28), clip=(0.05, 400))
        sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    sc.render.filepath = os.path.join(OUT, v + '.png')
    bpy.ops.render.render(write_still=True)
    print('view', v, f'{time.time() - T0:.1f}s', flush=True)
