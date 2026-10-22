"""UV-unwrap, build procedural source materials, bake PBR atlases.
usage: python3 shade.py <airframe_res> <details_res> <tag>"""
import bpy, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nodes as ND

RES_A = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
RES_D = int(sys.argv[2]) if len(sys.argv) > 2 else 512
TAG = sys.argv[3] if len(sys.argv) > 3 else 'test'
TEX = os.path.join(HERE, 'tex', TAG)
os.makedirs(TEX, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo.blend'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
O = bpy.data.objects
MAT = bpy.data.materials

# ---------------------------------------------------------------- part ids for the livery shader
PART = {'src_Fuselage': 0, 'src_Wing': 1, 'src_WingTE_Center': 2, 'src_WingTE_TipL': 2, 'src_WingTE_TipR': 2,
        'Flap_L': 2, 'Flap_R': 2, 'Aileron_L': 2, 'Aileron_R': 2, 'src_Fin': 3, 'Rudder': 3,
        'src_Stabilizer': 4, 'Elevator_L': 4, 'Elevator_R': 4, 'CargoDoor': 5, 'src_Struts': 6}
for k, v in PART.items():
    O[k]['part'] = float(v)
for k in ('Wheel_L', 'Wheel_R'):
    O[k]['wscale'] = 1.0
O['TailWheel']['wscale'] = 0.59

ATLAS_A = [k for k in PART]
ATLAS_D = ['src_CowlDetails', 'Propeller', 'Wheel_L', 'Wheel_R', 'TailWheel', 'src_GearLegs', 'TailWheel_Fork',
           'src_Interior', 'src_Antennas'] + [o.name for o in O if o.name.startswith('src_Case')]

# ---------------------------------------------------------------- materials
logo = bpy.data.images.load(os.path.join(HERE, 'tex_src_logo.png'))
logo.colorspace_settings.name = 'sRGB'
logo.pack()
ND.mat_livery(MAT['src_Livery'], logo)
ND.mat_generic(MAT['src_Struts'], (0.03, 0.03, 0.032, 1), 0.5, chip_amt=0.03, rust_amt=0.6, dirt=0.3)
ND.mat_interior(MAT['src_InteriorA'])
ND.mat_interior(MAT['src_InteriorD'])
ND.mat_gear(MAT['src_GearPaint'])
ND.mat_rubber(MAT['src_Rubber'])
ND.mat_generic(MAT['src_Hub'], (0.035, 0.037, 0.04, 1), 0.45, chip_amt=0.04, rust_amt=0.4, dirt=0.4)
ND.mat_blade(MAT['src_PropBlade'])
ND.mat_generic(MAT['src_Spinner'], (0.022, 0.13, 0.095, 1), 0.33, V='object', chip_amt=0.02, dirt=0.2)
ND.mat_metal_dark(MAT['src_MetalDark'])
ND.mat_case(MAT['src_CaseGreen'], (0.05, 0.085, 0.03, 1))
ND.mat_case(MAT['src_CaseYellow'], (0.50, 0.30, 0.025, 1))
ND.mat_case(MAT['src_CaseDark'], (0.018, 0.022, 0.025, 1))
ND.mat_case(MAT['src_CaseTeal'], (0.018, 0.045, 0.045, 1))
ND.mat_generic(MAT['src_Antenna'], (0.015, 0.015, 0.016, 1), 0.5, dirt=0.1)
ND.mat_lights(MAT['M_Lights'])
MATS_A = ['src_Livery', 'src_Struts', 'src_InteriorA']
MATS_D = ['src_InteriorD', 'src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal', 'src_Antenna']
for m in MATS_A + MATS_D:
    MAT[m].use_fake_user = True


# ---------------------------------------------------------------- UV unwrap + pack per atlas
def unwrap(names, shrink=None):
    bpy.ops.object.select_all(action='DESELECT')
    obs = [O[n] for n in names]
    for o in obs:
        o.select_set(True)
        if not o.data.uv_layers:
            o.data.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    if shrink:
        for n, f in shrink.items():
            uv = O[n].data.uv_layers.active.data
            arr = np.zeros(len(uv) * 2)
            uv.foreach_get('uv', arr)
            uv.foreach_set('uv', arr * f)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004, shape_method='CONCAVE', scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')


t0 = time.time()
unwrap(ATLAS_A, shrink={'src_Struts': 0.8})
unwrap(ATLAS_D, shrink={'src_Interior': 0.55, 'Propeller': 1.25, 'Wheel_L': 1.2, 'Wheel_R': 1.2,
                        'src_GearLegs': 0.9})
# lights: simple unwrap so every mesh has UVs
bpy.ops.object.select_all(action='DESELECT')
O['src_NavLights'].select_set(True)
bpy.context.view_layer.objects.active = O['src_NavLights']
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')
print('uv done', round(time.time() - t0, 1))


# ---------------------------------------------------------------- bake
def img(name, res, noncolor=False, float_buf=False):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=float_buf)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


PASSES = {
    'BaseColor': dict(type='EMIT', node='BAKE_COLOR', noncolor=False, float_buf=False),
    'MR': dict(type='EMIT', node='BAKE_MR', noncolor=True, float_buf=False),
    'Normal': dict(type='NORMAL', node=None, noncolor=True, float_buf=True),
    'AO': dict(type='AO', node='BAKE_PLAIN', noncolor=True, float_buf=False),
}
IMGS = {}


def set_output(mat, node_name):
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    src = nt.nodes[node_name] if node_name else next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(src.outputs[0], out.inputs['Surface'])


def bake(pass_name, samples=1, names=None, clear=True, margin=None, save=True):
    p = PASSES[pass_name]
    if clear:
        ia = img(f'T_Airframe_{pass_name}', RES_A, p['noncolor'], p['float_buf'])
        idt = img(f'T_Details_{pass_name}', RES_D, p['noncolor'], p['float_buf'])
        IMGS[('A', pass_name)], IMGS[('D', pass_name)] = ia, idt
    else:
        ia, idt = IMGS[('A', pass_name)], IMGS[('D', pass_name)]
    for m, im in [(m, ia) for m in MATS_A] + [(m, idt) for m in MATS_D]:
        mat = MAT[m]
        set_output(mat, p['node'])
        t = mat.node_tree.nodes['BAKE_TARGET']
        t.image = im
        mat.node_tree.nodes.active = t
    sc.cycles.samples = samples
    bk = sc.render.bake
    bk.use_clear = clear
    bk.margin = margin if margin is not None else max(4, RES_A // 256)
    bk.margin_type = 'EXTEND'
    bk.target = 'IMAGE_TEXTURES'
    bk.normal_space = 'TANGENT'
    bk.normal_r, bk.normal_g, bk.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
    bpy.ops.object.select_all(action='DESELECT')
    names = names or (ATLAS_A + ATLAS_D)
    for n in names:
        O[n].select_set(True)
    bpy.context.view_layer.objects.active = O[names[0]]
    t0 = time.time()
    if p['type'] == 'EMIT':
        bpy.ops.object.bake(type='EMIT')
    elif p['type'] == 'NORMAL':
        bpy.ops.object.bake(type='NORMAL')
    else:
        bpy.ops.object.bake(type='AO')
    print('baked', pass_name, round(time.time() - t0, 1), 's')
    if not save:
        return
    for im in (ia, idt):
        fmt = 'PNG'
        im.filepath_raw = os.path.join(TEX, im.name + '.png')
        im.file_format = fmt
        if p['float_buf']:
            sc.render.image_settings.file_format = 'PNG'
            sc.render.image_settings.color_depth = '16'
            sc.render.image_settings.color_mode = 'RGB'
            im.save_render(im.filepath_raw, scene=sc)
        else:
            im.save()


# AO: bake with the propeller hidden so blade shadows don't get baked onto the cowl,
# and with the cargo door open so the cargo bay receives light.
door = O['CargoDoor']
DOOR_OPEN = math.radians(100)

bake('BaseColor')
bake('MR')
bake('Normal')
door.rotation_euler[2] = DOOR_OPEN
AO_S = int(sys.argv[4]) if len(sys.argv) > 4 else 16
O['Propeller'].hide_render = True
bake('AO', samples=AO_S, names=[n for n in ATLAS_A + ATLAS_D if n != 'Propeller'], save=False)
O['Propeller'].hide_render = False
bake('AO', samples=AO_S, names=['Propeller'], clear=False, margin=2)
door.rotation_euler[2] = 0.0
for m in MATS_A + MATS_D:
    set_output(MAT[m], None)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_src_{TAG}.blend'))
print('saved source blend')
