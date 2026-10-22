"""Renders of the base prefabs (out/base[_draft|_test].blend): each prefab on its own ground (Update 3's terrain under it,
base_ground.json) by day, details, the hatch with its lid open, the fences in a row; the map views (Update 3's terrain,
the rebuilt base around them: the prologue buildings from out/*.blend); night views: the mast's beacons, the yard lights
and the helipad lights powered (the game's on-materials and Update 3's lights).
python3 -I base_render.py <views|all|map|cmp> [spp] [--draft|--test] [--tag=x] -> rend/base[_draft|_test]/<view>[_tag].png"""
import sys, os, math, json, time, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P

T0 = time.time()
sfx = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
ARG = {a.split('=')[0][2:]: a.split('=')[1] for a in sys.argv if a.startswith('--') and '=' in a}
TAG = ('_' + ARG['tag']) if 'tag' in ARG else ''
OUT = os.path.join(P.HERE, 'rend', 'base' + sfx)
os.makedirs(OUT, exist_ok=True)
TERRAIN = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend'
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'base{sfx}.blend'))
sc = bpy.context.scene
import base_spec as S

for m in bpy.data.materials:                                         # point filter everywhere (PSX)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'
ROOTS = [c.name for c in sc.collection.children if c.name in bpy.data.objects]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}
LID = bpy.data.objects.get('IX_HatchLid_94')
LID_REST = LID.matrix_local.copy() if LID else None


def ground_mat(name, rgb):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = 1.0
    return m


GM_T, GM_R = ground_mat('M_g_terrain', (0.055, 0.065, 0.042)), ground_mat('M_g_road', (0.13, 0.11, 0.085))
STUDIO_G = []
EXT = {'Hatch': (-3.0, 3.5, -3.0, 3.0), 'Crates': (-2.5, 2.5, -2.0, 2.0), 'LogPile': (-4.0, 4.0, -2.0, 2.0),
       'Helipad': (-16.0, 18.0, -14.0, 13.0), 'RadioMast': (-36.0, 36.0, -36.0, 28.0), 'LightPole': (-2.0, 3.0, -2.0, 2.0),
       'PowerPole': (-2.5, 2.5, -2.0, 2.0)}


def studio_ground(name, ext, step=0.25):
    xs = np.arange(ext[0], ext[1] + 1e-6, step)
    ys = np.arange(ext[2], ext[3] + 1e-6, step)
    v = [(float(x), float(y), S.ground(name, float(x), float(y)) if name in S.GROUND['prefabs'] else 0.0) for y in ys for x in xs]
    nx = len(xs)
    f = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new('G_' + name)
    me.from_pydata(v, [], f)
    me.materials.append(GM_T)
    ob = bpy.data.objects.new('G_' + name, me)
    sc.collection.objects.link(ob)
    STUDIO_G.append(ob)
    ob['for'] = name
    return ob


DUPES = []


def fence_row():
    """three chain-link sections end to end, the three old-fence variants end to end behind them"""
    if DUPES:
        for d in DUPES:
            d.hide_render = False
        return
    for i in range(3):
        for nm, y0, dx in (('FenceChain', 0.0, 3.0), ('OldFence' + ('', '_b', '_c')[i], 3.0, 4.0)):
            src = bpy.data.objects[nm]
            c = src.copy()
            c.name = f'dup_{nm}_{i}'
            c.matrix_world = Matrix.Translation(Vector(((i - 1) * dx, y0, 0.0)))
            c.hide_render = False
            sc.collection.objects.link(c)
            DUPES.append(c)


def show_only(names, at_origin=True, offsets=None):
    for n in ROOTS:
        o = bpy.data.objects[n]
        o.hide_render = n not in names
        for ch in o.children_recursive:                                # the doors / lids go with their roots
            ch.hide_render = n not in names
        if n in names:
            off = Vector(offsets[n]) if offsets and n in offsets else Vector()
            o.matrix_world = Matrix.Translation(off) if at_origin else MAPM[n]
        else:
            o.matrix_world = MAPM[n]
    for g in STUDIO_G:
        g.hide_render = True
    for d in DUPES:
        d.hide_render = True


w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.2
sun.data.angle = math.radians(2.0)
sun.rotation_euler = (math.radians(50), math.radians(6), math.radians(25))
sc.collection.objects.link(sun)

VIEWS = {
    # the hatch
    'hatch': dict(roots=['Hatch'], eye=(3.4, -4.2, 2.3), tgt=(0.4, 0.0, 0.5), lens=26),
    'hatch_lid': dict(roots=['Hatch'], eye=(1.75, -1.25, 1.25), tgt=(0.8, 0.0, 0.58), lens=30),
    'hatch_hinge': dict(roots=['Hatch'], eye=(-1.9, -1.1, 1.05), tgt=(-0.9, 0.0, 0.52), lens=30),
    'hatch_open': dict(roots=['Hatch'], eye=(2.6, -2.4, 2.2), tgt=(0.0, 0.0, 0.5), lens=26, lid=85.0),
    'hatch_sign': dict(roots=['Hatch'], eye=(2.1, -4.2, 1.5), tgt=(2.0, -1.93, 1.32), lens=32),
    # the crates, the logs
    'crates': dict(roots=['Crates'], eye=(1.6, -3.7, 1.8), tgt=(0.0, -0.1, 0.5), lens=28),
    'crates_back': dict(roots=['Crates'], eye=(-2.6, 2.8, 1.9), tgt=(0.0, 0.0, 0.5), lens=28),
    'crates_open': dict(roots=['Crates'], eye=(-0.6, -2.1, 1.75), tgt=(-0.2, -0.5, 0.55), lens=30),
    'logs': dict(roots=['LogPile'], eye=(4.6, -3.8, 1.9), tgt=(0.4, 0.0, 0.5), lens=26),
    'logs_end': dict(roots=['LogPile'], eye=(4.4, -0.8, 1.0), tgt=(2.4, 0.0, 0.55), lens=30),
    # the poles
    'lightpole': dict(roots=['LightPole'], eye=(4.2, -6.0, 2.6), tgt=(0.4, 0.0, 3.0), lens=24),
    'lightpole_head': dict(roots=['LightPole'], eye=(2.5, -1.7, 5.1), tgt=(0.9, 0.0, 5.95), lens=30),
    'lightpole_foot': dict(roots=['LightPole'], eye=(1.0, -1.4, 1.0), tgt=(0.0, 0.0, 0.4), lens=30),
    'powerpole': dict(roots=['PowerPole'], eye=(5.0, -8.0, 3.0), tgt=(0.0, 0.0, 4.6), lens=22),
    'powerpole_top': dict(roots=['PowerPole'], eye=(2.2, -2.6, 7.6), tgt=(0.0, 0.0, 8.45), lens=28),
    # the fences
    'fences': dict(roots=[], fences=True, eye=(5.5, -7.5, 2.6), tgt=(0.0, 1.5, 1.1), lens=24),
    'fence_chain': dict(roots=[], fences=True, eye=(2.6, -2.2, 2.4), tgt=(1.0, -0.1, 2.0), lens=28),
    'fence_old': dict(roots=[], fences=True, eye=(-1.0, 0.6, 1.4), tgt=(1.0, 3.0, 0.9), lens=26),
    # the helipad
    'helipad': dict(roots=['Helipad'], eye=(-17.0, -18.0, 9.0), tgt=(1.0, -1.0, 0.0), lens=22),
    'heli_top': dict(roots=['Helipad'], eye=(0.5, -0.5, 30.0), tgt=(0.5, 0.0, 0.0), lens=24),
    'heli_sock': dict(roots=['Helipad'], eye=(9.0, -1.0, 3.2), tgt=(14.0, 6.0, 4.6), lens=24),
    'heli_sign': dict(roots=['Helipad'], eye=(12.4, -15.2, 1.7), tgt=(13.0, -11.5, 1.45), lens=30),
    'heli_light': dict(roots=['Helipad'], eye=(10.6, -0.9, 0.85), tgt=(9.6, 0.0, 0.35), lens=34),
    'heli_pallet': dict(roots=['Helipad'], eye=(-9.8, 1.2, 1.9), tgt=(-12.5, 4.0, 0.5), lens=28),
    # the radio mast
    'mast': dict(roots=['RadioMast'], eye=(-38.0, -52.0, 12.0), tgt=(0.0, 0.0, 28.0), lens=24),
    'mast_base': dict(roots=['RadioMast'], eye=(4.2, -6.2, 2.4), tgt=(0.0, -0.6, 1.6), lens=24),
    'mast_top': dict(roots=['RadioMast'], eye=(6.5, -9.0, 57.0), tgt=(0.0, 0.0, 59.2), lens=24),
    'mast_beacon': dict(roots=['RadioMast'], eye=(3.4, -4.4, 21.2), tgt=(1.0, -1.0, 20.2), lens=26),
    'mast_anchor': dict(roots=['RadioMast'], eye=(27.6, 4.6, 2.4), tgt=(31.5, 9.8, 0.7), lens=26),
    'mast_sign': dict(roots=['RadioMast'], eye=(1.4, -3.4, 1.7), tgt=(0.6, -1.0, 1.6), lens=30),
}
LOOK = {}                                                               # map views (eyes in a prefab's frame)


def _mapped(prefab, eye, tgt, i=0):
    M = S.map_matrix(prefab, i)
    return (tuple((M @ np.array([*eye, 1.0]))[:3]), tuple((M @ np.array([*tgt, 1.0]))[:3]))


for vn, (pf, i, eye, tgt, fov) in {'map_helipad': ('Helipad', 0, (-22.0, -24.0, 8.0), (2.0, 0.0, 1.0), 45.0),
                                   'map_mast': ('RadioMast', 0, (-30.0, -62.0, 6.0), (0.0, 0.0, 22.0), 50.0),
                                   'map_hatch': ('Hatch', 0, (6.0, -8.0, 2.4), (0.0, 0.0, 0.6), 45.0),
                                   'map_line': ('PowerPole', 0, (-6.0, -14.0, 2.0), (0.0, 0.0, 6.0), 50.0),
                                   'map_line2': ('PowerPole', 1, (8.0, -10.0, 2.2), (0.0, 0.0, 6.5), 50.0),
                                   'map_logs': ('LogPile', 0, (6.0, -7.0, 2.0), (0.0, 0.0, 0.6), 45.0),
                                   'map_crates': ('Crates', 0, (4.0, -6.0, 1.8), (0.0, 0.0, 0.6), 45.0),
                                   'map_lights': ('LightPole', 1, (-8.0, -9.0, 2.0), (0.0, 0.0, 3.0), 50.0)}.items():
    e, t = _mapped(pf, eye, tgt, i)
    LOOK[vn] = dict(map=True, eye=e, tgt=t, fov=fov)
LOOK['map_mast_night'] = dict(LOOK['map_mast'], night=True, exp=2.2)
LOOK['map_lights_night'] = dict(LOOK['map_lights'], night=True, power=True, exp=2.0)
LOOK['map_helipad_night'] = dict(LOOK['map_helipad'], night=True, power=True, exp=2.0)
# Update 3's viewpoint Base (Forest_Layout.json viewpoints, Unity p / target / vertical fov; its preview Forest_Base.jpg)
_vp = dict(p=(316.6939, 18.0023, -310.2725), target=(344.2394, 18.8943, -358.5762), fov=44.458)
LOOK['map_base'] = dict(map=True, eye=(-_vp['p'][0], -_vp['p'][2], _vp['p'][1]),
                        tgt=(-_vp['target'][0], -_vp['target'][2], _vp['target'][1]), fov=_vp['fov'])
LOOK['map_base_night'] = dict(LOOK['map_base'], night=True, power=True, exp=2.0)
VIEWS.update(LOOK)
CMPV = {}
if os.path.exists(os.path.join(P.HERE, 'base_cmp_views.json')):
    CMPV = json.load(open(os.path.join(P.HERE, 'base_cmp_views.json')))
    for vn, cv in CMPV.items():
        VIEWS[vn] = dict(roots=[cv['prefab']], eye=tuple(cv['eye']), tgt=tuple(cv['tgt']), lens=cv['lens'], cmp=True)

TERR = []
CONTEXT = ['main', 'garage', 'kpp', 'yard', 'hut', 'road']           # the rebuilt prologue around the base (if built)


def load_terrain():
    if TERR:
        return
    with bpy.data.libraries.load(TERRAIN) as (src, dst):
        dst.objects = [n for n in src.objects if n != 'Forest_Marker']
    for o in dst.objects:
        if o is not None and o.type == 'MESH':
            sc.collection.objects.link(o)
            for s_ in o.material_slots:
                nm = s_.material.name if s_.material else ''
                s_.material = GM_R if ('Road' in nm or 'Trail' in nm or 'Asphalt' in nm) else GM_T
            TERR.append(o)
    for b in CONTEXT:                                                  # their roots stand at their map places already
        p = os.path.join(P.HERE, 'out', b + '.blend')
        if not os.path.exists(p):
            continue
        with bpy.data.libraries.load(p) as (src, dst):
            dst.objects = [n for n in src.objects]
        for o in dst.objects:
            if o is not None and o.name not in sc.objects and o.type in ('MESH',):
                sc.collection.objects.link(o)
                TERR.append(o)
    U3 = S.U3                                                          # the scatter: every fence section at its place
    for nm in ('FenceChain', 'OldFence', 'OldFence_b', 'OldFence_c'):
        src = bpy.data.objects[nm]
        for i, e in enumerate(U3['scatter'][nm][1:]):
            c = src.copy()
            c.name = f'sc_{nm}_{i}'
            c.matrix_world = Matrix([list(r) for r in S.frame_matrix(e['p'], e['q'])])
            sc.collection.objects.link(c)
            TERR.append(c)
    lp = bpy.data.objects['LightPole']
    for i, e in enumerate(U3['prefabs']['LightPole'][1:]):
        c = lp.copy()
        c.name = f'pl_LightPole_{i}'
        c.matrix_world = Matrix([list(r) for r in S.frame_matrix(e['p'], e['q'])])
        sc.collection.objects.link(c)
        TERR.append(c)
    pp = bpy.data.objects['PowerPole']
    for i, e in enumerate(U3['prefabs']['PowerPole'][1:]):
        c = pp.copy()
        c.name = f'pl_PowerPole_{i}'
        c.matrix_world = Matrix([list(r) for r in S.frame_matrix(e['p'], e['q'])])
        sc.collection.objects.link(c)
        TERR.append(c)


NIGHT_L = []


def night_lights(on, power):
    """Update 3's lights (the mast's beacons always; the yard lights when powered) at every placement on the map"""
    for o in NIGHT_L:
        bpy.data.objects.remove(o)
    NIGHT_L.clear()
    if not on:
        return
    U3 = S.U3
    for pl in U3['prefabLights']:
        model = pl['model']
        for i, e in enumerate(U3['prefabs'].get(model, [])):
            M = S.frame_matrix(e['p'], e['q'])
            for L in pl['lights']:
                if L.get('tag') == 'power' and not power:
                    continue
                pu = L['p']
                pb = (-pu[0], -pu[2], pu[1])                         # Unity prefab-local -> own frame
                wp = (M @ np.array([*pb, 1.0]))[:3]
                ld = bpy.data.lights.new('nl', 'SPOT' if L['t'] == 'spot' else 'POINT')
                ld.color = L['c'][:3]
                ld.energy = L['i'] * (40.0 if L['t'] == 'spot' else 25.0)
                ld.shadow_soft_size = 0.05
                if L['t'] == 'spot':
                    ld.spot_size = math.radians(L.get('a', 90.0))
                ob = bpy.data.objects.new('nl', ld)
                ob.location = Vector(wp)
                d = Vector(M[:3, :3] @ np.array([-L['d'][0], -L['d'][2], L['d'][1]]))
                ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
                sc.collection.objects.link(ob)
                NIGHT_L.append(ob)


def set_power(on):
    """the game's materials for the lamps: off -> on (M_Lamp_SodiumOff -> M_Light_Sodium, M_Lamp_WarmOff -> M_Light_WarmWhite)"""
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if pb is None:
            continue
        if m.name == 'M_Lamp_SodiumOff':
            pb.inputs['Emission Color'].default_value = (1.0, 0.55, 0.18, 1) if on else (0, 0, 0, 1)
            pb.inputs['Emission Strength'].default_value = 12.0 if on else 0.0
        if m.name == 'M_Lamp_WarmOff':
            pb.inputs['Emission Color'].default_value = (1.0, 0.82, 0.6, 1) if on else (0, 0, 0, 1)
            pb.inputs['Emission Strength'].default_value = 10.0 if on else 0.0


P.setup_cycles((1100, 700), int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 24)
sc.cycles.max_bounces = 4
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
want = ([v for v in VIEWS if v not in LOOK and v not in CMPV] if sys.argv[1] == 'all' else list(LOOK) if sys.argv[1] == 'map'
        else list(CMPV) if sys.argv[1] == 'cmp' else sys.argv[1].split(','))
for v in want:
    c = VIEWS[v]
    night = c.get('night', False)
    if LID is not None:
        LID.matrix_local = LID_REST @ Matrix.Rotation(math.radians(-c.get('lid', 0.0)), 4, 'Y') if c.get('lid') else LID_REST
    if c.get('map'):
        load_terrain()
        for n in ROOTS:
            o = bpy.data.objects[n]
            o.hide_render = False
            for ch in o.children_recursive:
                ch.hide_render = False
            o.matrix_world = MAPM[n]
        for g in STUDIO_G:
            g.hide_render = True
        for d in DUPES:
            d.hide_render = True
        for o in TERR:
            o.hide_render = False
        sc.render.resolution_x, sc.render.resolution_y = 1281, 720
        cam.data.sensor_fit = 'VERTICAL'
        cam.data.angle_y = math.radians(c['fov'])
    else:
        for o in TERR:
            o.hide_render = True
        show_only(c['roots'], True)
        if c.get('fences'):
            fence_row()
            g = next((g for g in STUDIO_G if g['for'] == 'flat'), None) or studio_ground('flat', (-7.0, 7.0, -3.0, 6.0), 1.0)
            g.hide_render = False
        else:
            for n in c['roots']:
                g = next((g for g in STUDIO_G if g['for'] == n), None) or studio_ground(n, EXT.get(n, (-3, 3, -3, 3)),
                                                                                       0.25 if n not in ('RadioMast',) else 1.0)
                g.hide_render = False
        sc.render.resolution_x, sc.render.resolution_y = (800, 520) if c.get('cmp') else (1100, 700)
        cam.data.sensor_fit = 'AUTO'
        cam.data.lens = c['lens']
    cam.location = Vector(c['eye'])
    cam.rotation_euler = (Vector(c['tgt']) - Vector(c['eye'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start, cam.data.clip_end = 0.05, 2000
    bg.inputs[0].default_value = (0.02, 0.025, 0.035, 1) if night else (0.56, 0.62, 0.72, 1)
    bg.inputs[1].default_value = 0.25 if night else 0.9
    sun.data.energy = 0.05 if night else 3.2
    sun.data.color = (0.62, 0.72, 1.0) if night else (1.0, 0.97, 0.92)
    night_lights(night, c.get('power', False))
    set_power(c.get('power', False))
    ims = sc.render.image_settings
    if not night:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.render.filepath = os.path.join(OUT, v + TAG + '.png')
        bpy.ops.render.render(write_still=True)
    else:
        for m in bpy.data.materials:                                  # the signs' glow (game values)
            pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
            if pb is not None and 'night_emit' in m:
                pb.inputs['Emission Strength'].default_value = float(m['night_emit']) * 8.0
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format, ims.color_depth = 'OPEN_EXR', '32'
        ims.color_management = 'OVERRIDE'
        ims.linear_colorspace_settings.name = 'Linear Rec.709'
        exr = os.path.join(OUT, v + TAG + '.exr')
        sc.render.filepath = exr
        bpy.ops.render.render(write_still=True)
        subprocess.run([sys.executable, '-I', os.path.join(P.HERE, 'post_bloom.py'), exr, os.path.join(OUT, v + TAG + '.png'),
                        '0.25', str(c.get('exp', 1.0))], check=True)
        os.remove(exr)
        for m in bpy.data.materials:
            pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
            if pb is not None and 'night_emit' in m:
                pb.inputs['Emission Strength'].default_value = 0.0
    print('view', v, f'{time.time() - T0:.1f}s', flush=True)
