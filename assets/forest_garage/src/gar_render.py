"""Renders of the garage (out/garage[_draft|_test].blend posed from its contract): outside by day, inside with Update 3's
lights (the station powered: the fittings and the bulkhead lit), a work light for checking, details; the gate and the side
door posed open on request.
python3 -I gar_render.py <views|all> [spp] [--draft|--test] [--work] [--gate=deg] [--side=deg] [--tag=x]
  -> rend/garage[_draft|_test]/<view>[_tag].png"""
import sys, os, math, json, time, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P

T0 = time.time()
sfx = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
WORK = '--work' in sys.argv
ARG = {a.split('=')[0][2:]: a.split('=')[1] for a in sys.argv if a.startswith('--') and '=' in a}
TAG = ('_' + ARG['tag']) if 'tag' in ARG else ''
OUT = os.path.join(P.HERE, 'rend', 'garage' + sfx)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'garage{sfx}.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', f'garage_contract{sfx}.json')))
MATS = {m['name']: m for m in json.load(open(os.path.join(P.HERE, 'gar_u3_materials.json')))}
import gar_spec as S

for m in bpy.data.materials:                                         # point filter everywhere (PSX)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'


def pose(name, deg):
    p = CON['parts'][name]
    o = bpy.data.objects[name]
    if 'rest' not in o:
        o['rest'] = [list(r) for r in o.matrix_world]
    M0 = Matrix(o['rest'])
    piv = Vector(p['pivot'])
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, Vector(p['axis'])) @ Matrix.Translation(-piv)
    o.matrix_world = R @ M0


pose(S.GATE['name'], float(ARG.get('gate', 0)))
pose(S.SIDE['name'], float(ARG.get('side', 0)))
ON = {'M_Lamp_FluorOff': 'M_Lamp_Fluor', 'M_Lamp_BulbOff': 'M_Lamp_Bulb'}


def u3mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    d = MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*d['color'][:3], 1)
    pb.inputs['Emission Color'].default_value = (*d['emission'][:3], 1)
    pb.inputs['Emission Strength'].default_value = float(d.get('emissionIntensity', 0.0))
    return m


def power(on):
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        for s in o.material_slots:
            if s.material is None:
                continue
            n = s.material.name
            if on and n in ON:
                s.material = u3mat(ON[n])
            elif not on and n in ON.values():
                s.material = u3mat({v: k for k, v in ON.items()}[n])


LIGHTS = []
for pl in CON['prefabLights']:
    for L in pl['lights']:
        u = L['p']
        ld = bpy.data.lights.new('L', 'POINT')
        ld.color = tuple(L['c'][:3])
        ld.energy = 4 * math.pi ** 2 * float(L['i'])
        ld.shadow_soft_size = 0.05
        ob = bpy.data.objects.new('L', ld)
        ob.location = Vector((-u[0], -u[2], u[1]))
        sc.collection.objects.link(ob)
        LIGHTS.append(ob)
WORKL = []
for (x, y) in ((-3.0, -1.5), (3.0, -1.5), (-3.0, 2.2), (3.0, 2.2)):
    L = bpy.data.lights.new('W', 'POINT')
    L.energy = 260.0
    L.shadow_soft_size = 0.6
    lo = bpy.data.objects.new('W', L)
    lo.location = (x, y, 3.6)
    sc.collection.objects.link(lo)
    WORKL.append(lo)
w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.2
sun.data.angle = math.radians(2.0)
sun.rotation_euler = (math.radians(50), math.radians(6), math.radians(25))
sc.collection.objects.link(sun)
gme = bpy.data.meshes.new('Ground')
gme.from_pydata([(-60, -60, S.GROUND - 0.004), (60, -60, S.GROUND - 0.004), (60, 60, S.GROUND - 0.004),
                 (-60, 60, S.GROUND - 0.004)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new('Ground', gme)
gm = bpy.data.materials.new('M_ground')
gm.use_nodes = True
next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.09, 0.09, 0.085, 1)
gme.materials.append(gm)
sc.collection.objects.link(gob)

VIEWS = {
    'ext_sw': dict(eye=(-13.0, -13.0, 4.5), tgt=(0.0, 0.0, 1.6), lens=26, day=True),
    'ext_se': dict(eye=(13.5, -12.5, 4.0), tgt=(0.0, 0.0, 1.6), lens=26, day=True),
    'ext_ne': dict(eye=(13.0, 12.5, 4.5), tgt=(0.0, 0.0, 1.6), lens=26, day=True),
    'ext_nw': dict(eye=(-13.5, 12.0, 4.0), tgt=(0.0, 0.0, 1.6), lens=26, day=True),
    'ext_gate': dict(eye=(-0.4, -10.5, 1.7), tgt=(-1.5, -4.5, 2.0), lens=28, day=True),
    'ext_side': dict(eye=(9.0, -1.0, 1.7), tgt=(6.0, 1.5, 1.3), lens=28, day=True),
    'ext_back': dict(eye=(2.0, 11.0, 2.0), tgt=(0.0, 4.5, 2.2), lens=24, day=True),
    'ext_roof': dict(eye=(10.0, -9.0, 11.0), tgt=(0.0, 0.0, 4.4), lens=26, day=True),
    'ext_corner': dict(eye=(7.8, -6.3, 1.0), tgt=(6.0, -4.5, 0.6), lens=30, day=True),
    'ext_win': dict(eye=(4.6, -6.6, 1.9), tgt=(3.8, -4.5, 1.9), lens=30, day=True),
    'in_gate': dict(eye=(5.2, 3.6, 1.7), tgt=(-1.5, -4.3, 1.4), lens=18),
    'in_back': dict(eye=(-1.0, -3.9, 1.7), tgt=(1.0, 4.3, 1.2), lens=18),
    'in_west': dict(eye=(4.8, -0.5, 1.7), tgt=(-5.8, 1.5, 1.0), lens=18),
    'in_east': dict(eye=(-4.6, 0.5, 1.7), tgt=(5.8, -0.5, 1.2), lens=18),
    'in_bench': dict(eye=(3.4, 1.9, 1.6), tgt=(3.6, 4.3, 1.2), lens=22),
    'in_drums': dict(eye=(3.0, -0.5, 1.6), tgt=(5.4, -2.4, 0.8), lens=22),
    'in_shelf': dict(eye=(-3.4, 1.2, 1.6), tgt=(-5.8, 1.8, 1.2), lens=22),
    'in_ceiling': dict(eye=(1.5, -2.0, 1.6), tgt=(-1.5, 1.0, 4.4), lens=18),
    'in_quad': dict(eye=(1.2, -0.6, 1.5), tgt=(-1.5, 1.0, 0.5), lens=24),
    'night_front': dict(eye=(1.0, -12.0, 1.7), tgt=(-1.5, -4.5, 2.2), lens=26, exp=0.6, moon=True),
    # the cameras of the Update 3 renders (scratchpad garage/render_u3.py: the FBX's box centre, 0.9 x its diagonal)
    'cmp_se': dict(eye=(10.45, -11.86, 9.49), tgt=(0.065, 0.0, 2.07), lens=30, day=True),
    'cmp_nw': dict(eye=(-10.32, 11.86, 9.49), tgt=(0.065, 0.0, 2.07), lens=30, day=True),
    'cmp_sw': dict(eye=(-11.80, -10.38, 7.26), tgt=(0.065, 0.0, 2.07), lens=30, day=True),
    'cmp_ne': dict(eye=(11.93, 10.38, 7.26), tgt=(0.065, 0.0, 2.07), lens=30, day=True),
    'cmp_in1': dict(eye=(3.82, -3.90, 3.90), tgt=(-0.935, 1.0, 0.5), lens=20),
    'cmp_in2': dict(eye=(-3.69, 3.90, 3.90), tgt=(1.065, -1.0, 0.5), lens=20),
    'night_in': dict(eye=(5.2, 3.6, 1.7), tgt=(-1.5, -4.3, 1.4), lens=18, exp=0.6),
}
DETAIL = {
    'det_gatehead': dict(eye=(-2.4, -3.2, 2.6), tgt=(-3.3, -4.35, 3.15), lens=30),
    'det_sidehinge': dict(eye=(7.0, 0.2, 1.3), tgt=(5.98, 1.05, 1.0), lens=34, day=True),
    'det_downpipe': dict(eye=(-3.2, 6.6, 1.2), tgt=(-4.6, 4.6, 1.6), lens=26, day=True),
}
ALL = list(VIEWS)
VIEWS.update(DETAIL)
P.setup_cycles((1100, 700), int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 24)
sc.cycles.max_bounces = 4
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
want = ALL if sys.argv[1] == 'all' else sys.argv[1].split(',')
for v in want:
    c = VIEWS[v]
    cam.location = Vector(c['eye'])
    cam.rotation_euler = (Vector(c['tgt']) - Vector(c['eye'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = c['lens']
    cam.data.clip_start, cam.data.clip_end = 0.03, 400
    day = c.get('day', False)
    bg.inputs[0].default_value = (0.56, 0.62, 0.72, 1) if day else (0.02, 0.025, 0.03, 1)
    bg.inputs[1].default_value = 0.9 if day else 0.2
    sun.hide_render = not (day or c.get('moon'))
    sun.data.energy = 3.2 if day else 0.06
    sun.data.color = (1.0, 0.97, 0.92) if day else (0.62, 0.72, 1.0)
    for o in LIGHTS:
        o.hide_render = day or WORK
    for o in WORKL:
        o.hide_render = day or not WORK
    power(not day and not WORK)
    ims = sc.render.image_settings
    if day or WORK:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.render.filepath = os.path.join(OUT, v + TAG + '.png')
        bpy.ops.render.render(write_still=True)
    else:
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format, ims.color_depth = 'OPEN_EXR', '32'
        ims.color_management = 'OVERRIDE'
        ims.linear_colorspace_settings.name = 'Linear Rec.709'
        exr = os.path.join(OUT, v + TAG + '.exr')
        sc.render.filepath = exr
        bpy.ops.render.render(write_still=True)
        subprocess.run([sys.executable, '-I', os.path.join(P.HERE, 'post_bloom.py'), exr, os.path.join(OUT, v + TAG + '.png'),
                        '0.25', str(c.get('exp', 0.9))], check=True)
        os.remove(exr)
    print('view', v, f'{time.time() - T0:.1f}s', flush=True)
