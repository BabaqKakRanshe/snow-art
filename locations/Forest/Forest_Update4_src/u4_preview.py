"""Forest Update 4: the package's FBX with the package's material definitions (Forest_Materials.json -> Blender nodes,
textures with Closest filtering), rendered like a quick look in the editor: does every slot find its texture, do the UVs
land on the atlases, do lenses, glass and cut-outs read. python3 -I u4_preview.py -- <stage_root> <out_dir> [models]"""
import bpy, sys, os, json, math
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
stage, out = a[0], a[1]
os.makedirs(out, exist_ok=True)
ROOT = os.path.join(stage, 'Assets/Locations/Forest')
U3TEX = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/u3/Assets/Locations/Forest/Textures'
M = {m['name']: m for m in json.load(open(os.path.join(ROOT, 'Data/Forest_Materials.json')))['materials']}
models = a[2:] or ['TowerHut', 'Checkpoint', 'FuelTanks', 'Trafo', 'Garage', 'BaseMain', 'Bridge30', 'ZoneGate',
                   'Sign_Observatory', 'OverlookDeck', 'FallenTree', 'Gate', 'Barrier', 'Hochsitz', 'EuroPost']
VIEWS = {  # model: (azimuth deg, elevation deg, distance factor)
    'default': [(35, 18, 1.5), (215, 22, 1.5)],
}


def srgb_to_lin(c):
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


def tex_path(f):
    for d in (os.path.join(ROOT, 'Textures'), U3TEX):
        p = os.path.join(d, f)
        if os.path.exists(p):
            return p
    return None


missing = set()


def build_mat(name):
    s = M.get(name)
    mat = bpy.data.materials.new(name + '_pv')
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 1.0 - (s or {}).get('smoothness', 0.0) if s else 0.8
    if s is None:
        b.inputs['Base Color'].default_value = (1, 0, 1, 1)
        missing.add(name)
        return mat
    col = list(s.get('color', [1, 1, 1]))[:3]
    if s.get('albedo'):
        p = tex_path(s['albedo'])
        if p is None:
            missing.add(s['albedo'])
            b.inputs['Base Color'].default_value = (1, 0, 1, 1)
        else:
            t = nt.nodes.new('ShaderNodeTexImage')
            t.image = bpy.data.images.load(p, check_existing=True)
            t.interpolation = 'Closest'
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            nt.links.new(t.outputs['Color'], mix.inputs['A'])
            mix.inputs['B'].default_value = (*col, 1)
            nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
            if s['type'] == 'cutout':
                nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
                mat.blend_method = 'CLIP' if hasattr(mat, 'blend_method') else None
    else:
        b.inputs['Base Color'].default_value = (*col, 1)
    if s.get('emissionIntensity', 0) > 0 and any(s.get('emission', [0, 0, 0])):
        e = s['emission']
        if s.get('emissionMap') and tex_path(s['emissionMap']):
            t2 = nt.nodes.new('ShaderNodeTexImage')
            t2.image = bpy.data.images.load(tex_path(s['emissionMap']), check_existing=True)
            t2.interpolation = 'Closest'
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            nt.links.new(t2.outputs['Color'], mix.inputs['A'])
            mix.inputs['B'].default_value = (*e, 1)
            nt.links.new(mix.outputs['Result'], b.inputs['Emission Color'])
        else:
            b.inputs['Emission Color'].default_value = (*e, 1)
        b.inputs['Emission Strength'].default_value = s['emissionIntensity'] * 0.5
    if s['type'] == 'transparent':
        b.inputs['Alpha'].default_value = s.get('alpha') or 0.6
    return mat


cards = []
for name in models:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, 'Models', name + '.fbx'))
    objs = [o for o in bpy.data.objects if o.type == 'MESH']
    cache = {}
    for o in objs:
        for slot in o.material_slots:
            n = slot.material.name.split('.')[0]
            if n not in cache:
                cache[n] = build_mat(n)
            slot.material = cache[n]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (lo + hi) / 2; rad = (hi - lo).length / 2
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24
    sc.render.resolution_x, sc.render.resolution_y = 640, 420
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.5, 0.55, 0.62, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.8
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 2.6
    sun.rotation_euler = (math.radians(48), 0, math.radians(30)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 35
    for i, (az, el, df) in enumerate(VIEWS.get(name, VIEWS['default'])):
        d = rad * df * 1.6
        eye = ctr + Vector((math.cos(math.radians(az)) * math.cos(math.radians(el)),
                            math.sin(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el)))) * d
        cam.location = eye
        cam.rotation_euler = (ctr - eye).to_track_quat('-Z', 'Y').to_euler()
        cam.data.clip_end = d * 4
        fp = os.path.join(out, f'{name}_{i}.png')
        sc.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        cards.append((name, fp))
    print('[preview]', name, len(objs), 'objects', flush=True)
print('MISSING', sorted(missing))
json.dump(cards, open(os.path.join(out, 'cards.json'), 'w'))
