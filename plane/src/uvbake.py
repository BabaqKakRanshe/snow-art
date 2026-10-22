"""Build geometry, UV-unwrap per texture set, bake helper maps (position, normal, id, AO) to .npy."""
import bpy, bmesh, sys, os, math, time
import numpy as np
sys.path.insert(0, '/home/claude/plane')
import plane_geo as G

WORK = '/home/claude/plane/work'
os.makedirs(WORK, exist_ok=True)
SETS = {'Fuselage': 4096, 'Surfaces': 4096, 'Details': 4096}
AO_RES = {'Fuselage': 2048, 'Surfaces': 2048, 'Details': 2048}
ONLY = sys.argv[1].split(',') if len(sys.argv) > 1 else list(SETS)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 1.0
coll = bpy.data.collections.new('Plane')
sc.collection.children.link(coll)
objs, spots = G.build_all(coll)


def set_of(ob):
    ids = {int(round(a.value)) for a in ob.data.attributes['mid'].data}
    sets = {G.SET_OF[i] for i in ids}
    assert len(sets) == 1, (ob.name, sets)
    return sets.pop()


for ob in objs:
    ob['tset'] = set_of(ob)
    ob.data.set_sharp_from_angle(angle=math.radians(40))
    ob.data.uv_layers.new(name='UVMap')

vl = bpy.context.view_layer
sc.tool_settings.use_uv_select_sync = True


def select_only(obs, active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    vl.objects.active = active


def smart_subsets(ob, subsets):
    """subsets: list of predicates on face centre (Vector) -> smart project each group separately."""
    select_only([ob], ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(ob.data)
    for pred in subsets:
        n = 0
        for f in bm.faces:
            f.select = pred(f.calc_center_median())
            n += f.select
        bmesh.update_edit_mesh(ob.data)
        if n:
            bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0,
                                     correct_aspect=True, scale_to_bounds=False)
        bm = bmesh.from_edit_mesh(ob.data)
    bpy.ops.object.mode_set(mode='OBJECT')


SUBSETS = {
    'Fuselage': [lambda c: c.y < -1.0, lambda c: -1.0 <= c.y < 1.6, lambda c: 1.6 <= c.y < 3.8, lambda c: c.y >= 3.8],
    'Wing': [lambda c: c.x < -3.4, lambda c: -3.4 <= c.x < 0, lambda c: 0 <= c.x < 3.4, lambda c: c.x >= 3.4],
    'Tail': [lambda c: c.z < 2.25 and c.x >= 0, lambda c: c.z < 2.25 and c.x < 0, lambda c: c.z >= 2.25],
    'Elevator': [lambda c: c.x >= 0, lambda c: c.x < 0],
}
t0 = time.time()
for ob in objs:
    smart_subsets(ob, SUBSETS.get(ob.name, [lambda c: True]))
print(f'smart project done {time.time() - t0:.1f}s')

# ---- per set: equalise texel density and pack
for tset in list(SETS) + ['Glass', 'Lights']:
    obs = [o for o in objs if o['tset'] == tset]
    select_only(obs, obs[0])
    bpy.ops.object.mode_set(mode='EDIT')
    for o in obs:
        bm = bmesh.from_edit_mesh(o.data)
        for f in bm.faces:
            f.select = True
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.average_islands_scale()
    # the dark cargo-bay walls need far less texel density than the cases
    for o in obs:
        if o.name != 'CargoBay':
            continue
        bm = bmesh.from_edit_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        ml = bm.faces.layers.float['mid']
        for f in bm.faces:
            if int(round(f[ml])) == G.ID['INTERIOR']:
                for l in f.loops:
                    l[uvl].uv *= 0.4
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=0.0045,
                            shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
print(f'pack done {time.time() - t0:.1f}s')

# texel density report
for tset, res in SETS.items():
    area3d = areauv = 0.0
    for o in objs:
        if o['tset'] != tset:
            continue
        me = o.data
        uv = me.uv_layers.active.data
        for p in me.polygons:
            area3d += p.area
            pts = [uv[li].uv for li in p.loop_indices]
            a = 0.0
            for i in range(1, len(pts) - 1):
                a += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) / 2
            areauv += a
    print(f'{tset}: 3D area {area3d:.1f} m2, UV fill {areauv * 100:.1f}%, texel density {math.sqrt(areauv / area3d) * res:.0f} px/m')

bpy.ops.wm.save_as_mainfile(filepath=f'{WORK}/uv.blend')

# ---- bake helper maps
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.render.bake.margin = 0
sc.render.bake.use_clear = True
world = bpy.data.worlds.new('W')
sc.world = world
world.light_settings.distance = 0.9

bake_mat = bpy.data.materials.new('BAKE')
bake_mat.use_nodes = True
nt = bake_mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new('ShaderNodeOutputMaterial')
emi = nt.nodes.new('ShaderNodeEmission')
geo = nt.nodes.new('ShaderNodeNewGeometry')
att = nt.nodes.new('ShaderNodeAttribute')
att.attribute_type = 'GEOMETRY'
att.attribute_name = 'mid'
vm_add = nt.nodes.new('ShaderNodeVectorMath'); vm_add.operation = 'MULTIPLY_ADD'
vm_add.inputs[1].default_value = (0.05, 0.05, 0.05); vm_add.inputs[2].default_value = (0.5, 0.5, 0.5)
nm_add = nt.nodes.new('ShaderNodeVectorMath'); nm_add.operation = 'MULTIPLY_ADD'
nm_add.inputs[1].default_value = (0.5, 0.5, 0.5); nm_add.inputs[2].default_value = (0.5, 0.5, 0.5)
idm = nt.nodes.new('ShaderNodeMath'); idm.operation = 'DIVIDE'; idm.inputs[1].default_value = 64.0
nt.links.new(geo.outputs['Position'], vm_add.inputs[0])
nt.links.new(geo.outputs['Normal'], nm_add.inputs[0])
nt.links.new(att.outputs['Fac'], idm.inputs[0])
nt.links.new(emi.outputs[0], out.inputs['Surface'])
img_node = nt.nodes.new('ShaderNodeTexImage')
nt.nodes.active = img_node


def run_bake(obs, src, img, btype='EMIT', samples=1):
    for l in list(emi.inputs['Color'].links):
        nt.links.remove(l)
    if src is not None:
        nt.links.new(src, emi.inputs['Color'])
    img_node.image = img
    nt.nodes.active = img_node
    sc.cycles.samples = samples
    select_only(obs, obs[0])
    t = time.time()
    bpy.ops.object.bake(type=btype, margin=0, use_clear=True)
    print(f'   bake {img.name} {btype} {time.time() - t:.1f}s')
    arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(img.size[1], img.size[0], 4)


for tset in ONLY:
    res = SETS[tset]
    obs = [o for o in objs if o['tset'] == tset]
    saved = {}
    for o in obs:
        saved[o.name] = [m for m in o.data.materials]
        o.data.materials.clear()
        o.data.materials.append(bake_mat)
    print(tset, [o.name for o in obs])
    for key, src in (('pos', vm_add.outputs[0]), ('nrm', nm_add.outputs[0]), ('id', idm.outputs[0])):
        img = bpy.data.images.new(f'{tset}_{key}', res, res, alpha=True, float_buffer=True)
        img.generated_color = (0, 0, 0, 0)
        a = run_bake(obs, src, img)
        if key == 'pos':
            np.save(f'{WORK}/{tset}_cov.npy', (a[..., 3] > 0.5))
            print('   coverage', (a[..., 3] > 0.5).mean())
        np.save(f'{WORK}/{tset}_{key}.npy', a[..., :3] if key != 'id' else a[..., 0])
        bpy.data.images.remove(img)
    ar = AO_RES[tset]
    img = bpy.data.images.new(f'{tset}_ao', ar, ar, alpha=True, float_buffer=True)
    img.generated_color = (0, 0, 0, 0)
    a = run_bake(obs, None, img, btype='AO', samples=48)
    np.save(f'{WORK}/{tset}_ao.npy', a[..., :4])
    bpy.data.images.remove(img)
    for o in obs:
        o.data.materials.clear()
print(f'all done {time.time() - t0:.1f}s')
