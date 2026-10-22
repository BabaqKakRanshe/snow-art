"""Cycles renders of the fence and road-block kit (Forest Update 7): scenes set up from instances of the kit's models
on a ground, by day. python3 -I kit_render.py -- <fences.blend> <out_dir> [spp] [only,...]
Shots: po2_out, po2_in, po2_detail, kpp, kpp_driver, teeth, chain, chain_close, models (one per model, for the sheet)."""
import bpy, sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import psxlib as P
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = a[0], a[1]
SPP = int(a[2]) if len(a) > 2 else 32
ONLY = set(a[3].split(',')) if len(a) > 3 else None
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
for m in bpy.data.materials:                                       # point filter (PSX)
    if m.use_nodes and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'
MODELS = [c.name for c in bpy.data.collections if c.name in bpy.data.objects]
def layer_col(lc, name):
    if lc.collection.name == name:
        return lc
    for ch in lc.children:
        r = layer_col(ch, name)
        if r:
            return r


for nm in MODELS:
    c = bpy.data.collections[nm]
    c.instance_offset = bpy.data.objects[nm].matrix_world.translation.copy()
    lc = layer_col(sc.view_layers[0].layer_collection, nm)
    if lc:
        lc.exclude = True                                            # the showroom row itself stays out of the shots
for o in bpy.data.objects:
    if o.name.startswith(('AOG', 'COL_')) or o.type in ('CAMERA', 'LIGHT'):
        o.hide_render = True
inst_col = bpy.data.collections.new('Shots')
sc.collection.children.link(inst_col)


def put(model, loc, rz=0.0, z=0.0):
    e = bpy.data.objects.new('i_' + model, None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = bpy.data.collections[model]
    e.location = Vector((loc[0], loc[1], z))
    e.rotation_euler = (0.0, 0.0, math.radians(rz))
    inst_col.objects.link(e)
    return e


# the ground: earth and dry grass in patches (procedural), a gravel strip for the road
def ground_mat():
    m = bpy.data.materials.new('M_ground')
    m.use_nodes = True
    nt = m.node_tree
    pb = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.35
    nz.inputs['Detail'].default_value = 6.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (0.060, 0.052, 0.036, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.085, 0.092, 0.050, 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 1.0
    return m


bpy.ops.mesh.primitive_plane_add(size=400, location=(40, 60, 0))
G = bpy.context.object
G.data.materials.append(ground_mat())
P.world((0.56, 0.62, 0.72), 0.85)
sun = P.sun(3.0, (52, 0, -35))
P.setup_cycles((1400, 820), SPP)
sc.cycles.max_bounces = 4
sc.view_settings.view_transform = 'Standard'


def cam(name, eye, target, lens=32.0, res=(1400, 820)):
    cd = bpy.data.cameras.new(name)
    co = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(co)
    co.location = Vector(eye)
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 600
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    return co


def shot(name, eye, target, lens=32.0, res=(1400, 820)):
    if ONLY and name not in ONLY:
        return
    cam(name, eye, target, lens, res)
    P.render(os.path.join(OUT, name + '.png'))
    print('rendered', name, flush=True)


# ---------------------------------------------------------------- A. a PO-2 run (outside = -y)
x0 = 0.0
run = ['ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Sign', 'ConcreteFence', 'ConcreteFence_Broken', 'ConcreteFence_b',
       'ConcreteFence_Wicket', 'ConcreteFence', 'ConcreteFence_b']
put('ConcreteFence_Socket', (x0, 0))
for i, m in enumerate(run):
    put(m, (x0 + 1.25 + 2.5 * i, 0))
put('ConcreteFence_Plain', (x0 + 1.25 + 2.5 * 9 + 6.0, 4.0), rz=-25)
put('ConcreteFence_Plain', (x0 + 1.25 + 2.5 * 10 + 6.0 - 0.2, 4.0 - 1.1), rz=-25)

# ---------------------------------------------------------------- B. a checkpoint's approach (the road along +y at x 60)
R0 = (60.0, 0.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(R0[0] + 3.0, R0[1] + 10, 0.004))
road = bpy.context.object
road.scale = (6.6, 70, 1)
rm = bpy.data.materials.new('M_road')
rm.use_nodes = True
rm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.11, 0.10, 0.085, 1)
rm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
road.data.materials.append(rm)
bx, by = R0
for i in range(5):                                                   # the wings from the barrier's line (y = by)
    put('ConcreteFence' if i % 3 else 'ConcreteFence_b', (bx - 0.9 - 1.25 - 2.5 * i, by))
    put('ConcreteFence_b' if i % 3 == 1 else 'ConcreteFence', (bx + 6.25 + 1.25 + 2.5 * i, by))
put('ConcreteFence_Socket', (bx - 0.9 - 12.5, by))                   # each run's first socket at its -x end
put('ConcreteFence_Socket', (bx + 6.25, by))
# the barrier itself (the checkpoint package, for scale): its pivot at the post, the boom along +x
with bpy.data.libraries.load('/home/claude/uaz/out/forest_kpp/kpp.blend', link=False) as (src_, dst_):
    dst_.objects = [n for n in src_.objects if n == 'Barrier' or n.startswith('IX_BarrierArm_82')]
loaded = [o for o in dst_.objects if o is not None]
for o in loaded:
    inst_col.objects.link(o)
    if o.name.startswith('COL_'):
        o.hide_render = True
barrier = bpy.data.objects.get('Barrier')
if barrier is not None:
    off = Vector((bx, by, 0.0)) - barrier.matrix_world.translation
    for o in loaded:
        if o.parent is None or o.parent not in loaded:
            o.location = o.location + off
for c_, sg in ((bx - 2.3, -1), (bx + 7.65, 1)):                      # FBS two high and a cube at the wing roots
    put('RoadBlock_FBS', (c_, by - 1.3))
    put('RoadBlock_FBS', (c_, by - 1.3), z=0.58)
    put('RoadBlock_Cube', (c_ + sg * 2.1, by - 1.4), rz=sg * 9)
for c_ in (bx - 7.9, bx - 13.2, bx + 13.25, bx + 18.55):
    put('WireCoil', (c_, by - 1.9))
for c_, d_ in ((bx - 5.9, 5.5), (bx - 13.9, 7.0), (bx + 11.25, 5.5), (bx + 19.25, 7.0)):
    put('Hedgehog', (c_, by - d_), rz=(c_ * 37) % 360)
put('RoadBlock_Jersey_Striped', (bx + 1.0, by - 12.0))
put('RoadBlock_Jersey', (bx + 3.05, by - 12.0))
put('RoadBlock_Jersey_Striped', (bx + 5.4, by - 24.0))
put('RoadBlock_Jersey', (bx + 3.35, by - 24.0))
put('Sign_Halt', (bx + 7.9, by - 32.0))
put('Sign_NoEntry', (bx + 7.4, by - 3.0))
put('WireBarricade', (bx - 0.9 - 12.5 - 0.5, by - 1.5))

# ---------------------------------------------------------------- C. a line of teeth with the abatis (along +x at y 40)
ty = 40.0
xs = 0.0
seq = ['TankTooth'] * 4 + ['TankTooth_b'] + ['TankTooth'] * 2 + ['Abatis'] + ['TankTooth'] * 3 + ['TankTooth_b'] + \
      ['TankTooth'] * 2 + ['Abatis_b'] + ['TankTooth'] * 4
for i, m in enumerate(seq):
    if m.startswith('Abatis'):
        hx = 4.3 if m == 'Abatis' else 3.8
        put(m, (xs - 0.5 + hx + 0.2, ty), rz=(i * 13) % 7 - 3)
        xs += 2 * hx + 0.4 + 0.8
    else:
        put(m, (xs, ty), rz=((i * 47) % 21 - 10) if m == 'TankTooth' else ((i * 31) % 45 - 22))
        xs += 2.05

# ---------------------------------------------------------------- D. the chain-link (along +x at y 80)
cy = 80.0
for i, m in enumerate(['ChainFence', 'ChainFence', 'ChainFence_Torn', 'ChainFence', 'ChainFence']):
    put(m, (3.0 * i, cy))
put('WireCoil', (4.5, cy - 2.2))
put('WireCoil', (9.6, cy - 2.2))

# ---------------------------------------------------------------- the shots
shot('po2_out', (-5.0, -11.0, 2.4), (10.0, 0.0, 1.2), 30)
shot('po2_in', (23.5, 9.5, 2.2), (9.0, 0.0, 1.3), 30)
shot('po2_detail', (8.2, -3.1, 3.3), (6.25, 0.0, 2.35), 35)
shot('po2_wicket', (14.0, 5.0, 1.7), (16.25, 0.0, 1.1), 30)
shot('kpp', (bx - 16.0, by - 46.0, 9.0), (bx + 2.8, by - 8.0, 0.5), 30)
shot('kpp_driver', (bx + 4.6, by - 44.0, 1.9), (bx + 3.0, by + 2.0, 1.0), 30)
shot('teeth', (-6.0, ty - 9.5, 2.0), (14.0, ty, 0.4), 28)
shot('teeth_top', (12.0, ty - 14.0, 10.0), (18.0, ty, 0.0), 30)
shot('chain', (-3.5, cy - 10.0, 1.8), (7.0, cy, 1.1), 32)
shot('chain_close', (5.4, cy - 2.3, 1.5), (6.6, cy, 1.0), 35)
print('done', flush=True)

# ---------------------------------------------------------------- E. one picture per model (for the catalogue sheet)
if ONLY is None or 'models' in ONLY:
    for o in inst_col.objects:
        o.hide_render = True                                   # only the catalogue row from here on
    road.hide_render = True
    my = 200.0
    order = ['ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign', 'ConcreteFence_Plain',
             'ConcreteFence_Socket', 'ConcreteFence_Wicket', 'ChainFence', 'ChainFence_Torn', 'WireCoil', 'RoadBlock_FBS',
             'RoadBlock_Jersey', 'RoadBlock_Jersey_Striped', 'RoadBlock_Cube', 'TankTooth', 'TankTooth_b', 'Hedgehog',
             'WireBarricade', 'Abatis', 'Abatis_b', 'Sign_Halt', 'Sign_NoEntry']
    for i, nm in enumerate(order):
        x = i * 20.0
        put(nm, (x, my))
        src_o = bpy.data.objects[nm]
        off = src_o.matrix_world.translation
        vs = [src_o.matrix_world @ Vector(c) - off for c in src_o.bound_box]
        lo = Vector([min(v[k] for v in vs) for k in range(3)])
        hi = Vector([max(v[k] for v in vs) for k in range(3)])
        c = Vector((x, my, 0)) + (lo + hi) / 2
        r = max((hi - lo).length / 2, 0.6)
        d = Vector((-0.55, -1.0, 0.42)).normalized()
        vfov = 2 * math.atan(18.0 * 480 / 720 / 35.0)               # 35 mm on the 36 mm sensor, 720 x 480
        cam('m_' + nm, tuple(c + d * r / math.sin(vfov / 2) * 1.04), tuple(c), 35, (720, 480))
        P.render(os.path.join(OUT, 'm_' + nm + '.png'))
        print('rendered m_' + nm, flush=True)
