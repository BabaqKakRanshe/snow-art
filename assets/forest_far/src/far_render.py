"""Renders of the far points (out/far[_draft|_test].blend): each prefab on its own ground by day, details, the doors open;
the map views (Update 3's terrain); night views: the beacons, the yard lights powered, the chapel's candles, the torch.
python3 -I far_render.py <views|all|map|cmp> [spp] [--draft|--test] [--tag=x] -> rend/far[_draft|_test]/<view>[_tag].png"""
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
OUT = os.path.join(P.HERE, 'rend', 'far' + sfx)
os.makedirs(OUT, exist_ok=True)
TERRAIN = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend'
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'far{sfx}.blend'))
sc = bpy.context.scene
import far_spec as S

for m in bpy.data.materials:                                         # point filter everywhere (PSX)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'
ROOTS = [c.name for c in sc.collection.children if c.name in bpy.data.objects]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}
DOORS = {o.name: o.matrix_local.copy() for o in bpy.data.objects if o.name.startswith('IX_')}


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
EXT = {'Dish_1': (-9, 9, -6, 9), 'Dish_2': (-9, 9, -6, 9), 'Dish_3': (-8, 8, -6, 8), 'Dish_4': (-8, 8, -6, 8),
       'Dish_5': (-9, 9, -6, 9), 'Radome': (-7, 12, -7, 7), 'RelayMast': (-8, 12, -8, 8), 'MeteoStation': (-8, 8, -8, 8),
       'LookoutTower': (-6, 6, -6, 6), 'PumpHouse': (-4, 4, -3, 6), 'Chapel': (-8, 7, -6, 6), 'Cabin': (-6, 4, -5, 5),
       'Campsite': (-3, 5, -3, 3)}
STUDIO_G = []


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
fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'POINT'))      # an interior's fill (the photographer's lamp)
fill.data.energy = 60.0
fill.data.shadow_soft_size = 0.5
sc.collection.objects.link(fill)

VIEWS = {
    'dish1': dict(roots=['Dish_1'], eye=(-15.0, 16.0, 8.0), tgt=(0.0, 1.5, 7.0), lens=22),
    'dish1_back': dict(roots=['Dish_1'], eye=(10.0, -14.0, 5.0), tgt=(0.0, 0.0, 6.0), lens=22),
    'dish1_feed': dict(roots=['Dish_1'], eye=(3.0, 9.5, 13.5), tgt=(0.0, 4.8, 11.8), lens=30),
    'dish1_base': dict(roots=['Dish_1'], eye=(7.5, -7.5, 2.8), tgt=(3.0, -2.5, 1.4), lens=24),
    'dish1_cab': dict(roots=['Dish_1'], eye=(4.6, -0.9, 1.6), tgt=(4.2, -3.0, 1.0), lens=30, doors=100.0),
    'dish1_yoke': dict(roots=['Dish_1'], eye=(-4.0, -5.0, 7.0), tgt=(0.0, -0.8, 7.4), lens=26),
    'dish2': dict(roots=['Dish_2'], eye=(-15.0, 16.0, 8.0), tgt=(0.0, 1.5, 7.0), lens=22),
    'dish3': dict(roots=['Dish_3'], eye=(-12.0, 13.0, 6.5), tgt=(0.0, 1.0, 5.5), lens=22),
    'dish4': dict(roots=['Dish_4'], eye=(-12.0, 13.0, 6.5), tgt=(0.0, 1.0, 5.5), lens=22),
    'dish5': dict(roots=['Dish_5'], eye=(-15.0, 16.0, 8.0), tgt=(0.0, 1.5, 7.0), lens=22),
    'radome': dict(roots=['Radome'], eye=(-22.0, -24.0, 10.0), tgt=(2.0, 0.0, 12.0), lens=22),
    'radome_top': dict(roots=['Radome'], eye=(-9.0, -10.0, 24.0), tgt=(0.0, 0.0, 21.0), lens=26),
    'radome_hut': dict(roots=['Radome'], eye=(15.0, 5.0, 2.4), tgt=(9.0, 0.5, 1.4), lens=24),
    'radome_foot': dict(roots=['Radome'], eye=(-1.0, -8.0, 2.4), tgt=(-1.5, -2.8, 2.6), lens=24),
    'relay': dict(roots=['RelayMast'], eye=(-28.0, -30.0, 14.0), tgt=(2.0, 0.0, 18.0), lens=22),
    'relay_top': dict(roots=['RelayMast'], eye=(7.0, -8.0, 38.0), tgt=(0.0, 0.0, 36.0), lens=26),
    'relay_gate': dict(roots=['RelayMast'], eye=(-12.0, -3.0, 1.8), tgt=(-6.0, 0.0, 1.3), lens=24),
    'relay_yard': dict(roots=['RelayMast'], eye=(12.0, -9.0, 4.0), tgt=(3.0, 0.0, 1.5), lens=22),
    'meteo': dict(roots=['MeteoStation'], eye=(-9.0, -11.0, 4.5), tgt=(0.0, 0.0, 1.0), lens=24),
    'meteo_screen': dict(roots=['MeteoStation'], eye=(1.6, -2.6, 1.8), tgt=(0.0, 0.0, 1.4), lens=28),
    'meteo_mast': dict(roots=['MeteoStation'], eye=(0.5, -1.5, 7.0), tgt=(3.0, 2.0, 7.9), lens=28),
    'meteo_gate': dict(roots=['MeteoStation'], eye=(0.6, -9.0, 1.4), tgt=(0.0, -6.0, 0.7), lens=26),
    'lookout': dict(roots=['LookoutTower'], eye=(-18.0, -22.0, 9.0), tgt=(0.0, 0.0, 12.0), lens=22),
    'lookout_cab': dict(roots=['LookoutTower'], eye=(-5.5, -6.5, 25.5), tgt=(0.0, 0.0, 23.2), lens=24),
    'lookout_stairs': dict(roots=['LookoutTower'], eye=(-5.0, -5.6, 2.2), tgt=(0.0, -0.6, 3.5), lens=22),
    'lookout_in': dict(roots=['LookoutTower'], eye=(-1.55, 1.55, 23.75), tgt=(0.8, -0.3, 22.1), lens=18),
    'lookout_ladder': dict(roots=['LookoutTower'], eye=(0.62, -0.78, 22.55), tgt=(1.15, 0.7, 22.35), lens=16),
    'lookout_landing': dict(roots=['LookoutTower'], eye=(-0.2, 1.2, 22.8), tgt=(1.2, -0.3, 21.2), lens=22),
    'pump': dict(roots=['PumpHouse'], eye=(3.8, -5.6, 2.4), tgt=(0.0, 0.0, 1.3), lens=24),
    'pump_back': dict(roots=['PumpHouse'], eye=(-4.0, 6.5, 2.4), tgt=(0.3, 1.8, 0.8), lens=24),
    'pump_in': dict(roots=['PumpHouse'], eye=(-0.1, -2.6, 1.6), tgt=(0.4, 0.4, 0.8), lens=22, doors=95.0),
    'chapel': dict(roots=['Chapel'], eye=(7.0, -11.0, 3.4), tgt=(-0.8, 0.0, 3.4), lens=22),
    'chapel_back': dict(roots=['Chapel'], eye=(-11.0, 7.0, 3.0), tgt=(-1.5, 0.0, 2.6), lens=22),
    'chapel_graves': dict(roots=['Chapel'], eye=(-6.0, -4.5, 1.8), tgt=(-4.2, 0.4, 0.6), lens=24),
    'chapel_in': dict(roots=['Chapel'], eye=(0.6, -3.0, 1.6), tgt=(0.0, 2.6, 1.3), lens=22, doors=95.0, interior=True),
    'chapel_altar': dict(roots=['Chapel'], eye=(0.3, 1.2, 1.5), tgt=(0.0, 2.8, 1.2), lens=26, interior=True),
    'cabin': dict(roots=['Cabin'], eye=(5.0, -8.0, 2.8), tgt=(0.0, -0.5, 2.0), lens=22),
    'cabin_back': dict(roots=['Cabin'], eye=(-8.0, 6.0, 3.0), tgt=(-1.0, 0.0, 1.6), lens=22),
    'cabin_in': dict(roots=['Cabin'], eye=(-1.6, -1.5, 1.6), tgt=(0.6, 0.8, 0.8), lens=18, doors=95.0, interior=True),
    'camp': dict(roots=['Campsite'], eye=(1.2, -4.8, 2.4), tgt=(1.2, 0.0, 0.2), lens=24),
    'camp_fire': dict(roots=['Campsite'], eye=(4.3, -0.3, 1.0), tgt=(3.0, 1.0, 0.1), lens=28),
    'camp_torch': dict(roots=['Campsite'], eye=(1.4, -2.4, 0.5), tgt=(0.5, -1.7, 0.05), lens=30),
}
LOOK = {}                                                               # map views (eyes in a prefab's frame)


def _mapped(prefab, eye, tgt, i=0):
    M = S.map_matrix(prefab, i)
    return (tuple((M @ np.array([*eye, 1.0]))[:3]), tuple((M @ np.array([*tgt, 1.0]))[:3]))


for vn, (pf, eye, tgt, fov) in {'map_dish1': ('Dish_1', (-30.0, 34.0, 4.0), (0.0, 0.0, 8.0), 45.0),
                               'map_radome': ('Radome', (-30.0, -40.0, 4.0), (0.0, 0.0, 14.0), 45.0),
                               'map_relay': ('RelayMast', (-40.0, 30.0, 4.0), (0.0, 0.0, 18.0), 50.0),
                               'map_lookout': ('LookoutTower', (-26.0, -30.0, 3.0), (0.0, 0.0, 12.0), 50.0),
                               'map_chapel': ('Chapel', (8.0, -16.0, 2.0), (-1.0, 0.0, 3.0), 45.0),
                               'map_cabin': ('Cabin', (6.0, -12.0, 1.9), (-0.5, 0.0, 1.8), 45.0),
                               'map_meteo': ('MeteoStation', (-12.0, -16.0, 2.5), (0.0, 0.0, 1.5), 45.0),
                               'map_pump': ('PumpHouse', (5.0, -9.0, 1.8), (0.0, 0.5, 1.2), 45.0),
                               'map_camp': ('Campsite', (2.0, -7.0, 1.8), (1.2, 0.0, 0.2), 45.0)}.items():
    e, t = _mapped(pf, eye, tgt)
    LOOK[vn] = dict(map=True, eye=e, tgt=t, fov=fov)
LOOK['map_dish1_night'] = dict(LOOK['map_dish1'], night=True, power=True, exp=2.2)
LOOK['map_radome_night'] = dict(LOOK['map_radome'], night=True, exp=2.2)
LOOK['map_chapel_night'] = dict(LOOK['map_chapel'], night=True, exp=2.6)
LOOK['map_camp_night'] = dict(LOOK['map_camp'], night=True, exp=2.4)
# Update 3's viewpoints Dish1 and Chapel (Forest_Layout.json viewpoints: Unity p / target / vertical fov; their previews
# Forest_Dish1.jpg, Forest_Chapel.jpg)
for vn, vp in {'map_vp_dish1': ((-424.3373, 26.1613, 444.936), (-470.0, 37.0689, 380.0), 40.134),
               'map_vp_chapel': ((458.0, 6.3674, -106.0), (470.0, 7.6627, -120.0), 40.134)}.items():
    LOOK[vn] = dict(map=True, eye=(-vp[0][0], -vp[0][2], vp[0][1]), tgt=(-vp[1][0], -vp[1][2], vp[1][1]), fov=vp[2])
    LOOK[vn + '_night'] = dict(LOOK[vn], night=True, power=True, exp=2.4)
VIEWS.update(LOOK)
CMPV = {}
if os.path.exists(os.path.join(P.HERE, 'far_cmp_views.json')):
    CMPV = json.load(open(os.path.join(P.HERE, 'far_cmp_views.json')))
    for vn, cv in CMPV.items():
        VIEWS[vn] = dict(roots=[cv['prefab']], eye=tuple(cv['eye']), tgt=tuple(cv['tgt']), lens=cv['lens'], cmp=True)

TERR = []


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
                if L.get('tag') == 'candle':
                    pass
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
        if m.name == 'M_LEDOff':
            pb.inputs['Emission Color'].default_value = (0.2, 1.0, 0.3, 1) if on else (0, 0, 0, 1)
            pb.inputs['Emission Strength'].default_value = 6.0 if on else 0.0
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
    for dn, rest in DOORS.items():                                     # the doors open about their hinges (vertical)
        o_ = bpy.data.objects[dn]
        o_.matrix_local = rest @ Matrix.Rotation(math.radians(c.get('doors', 0.0)), 4,
                                                 Vector((0, 0, 1)) if 'Cabinet' in dn else Vector((0, 0, -1))) \
            if c.get('doors') else rest                                  # +angle about the contract's axis: open out
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
        for n in c['roots']:
            g = next((g for g in STUDIO_G if g['for'] == n), None) or studio_ground(n, EXT.get(n, (-3, 3, -3, 3)), 0.5)
            g.hide_render = False
        sc.render.resolution_x, sc.render.resolution_y = (800, 520) if c.get('cmp') else (1100, 700)
        cam.data.sensor_fit = 'AUTO'
        cam.data.lens = c['lens']
    cam.location = Vector(c['eye'])
    cam.rotation_euler = (Vector(c['tgt']) - Vector(c['eye'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start, cam.data.clip_end = 0.05, 2000
    bg.inputs[0].default_value = (0.02, 0.025, 0.035, 1) if night else (0.56, 0.62, 0.72, 1)
    bg.inputs[1].default_value = 0.25 if night else 0.9
    sun.data.energy = 0.05 if night else (0.6 if c.get('interior') else 3.2)
    sun.data.color = (0.62, 0.72, 1.0) if night else (1.0, 0.97, 0.92)
    night_lights(night, c.get('power', False))
    fill.hide_render = not c.get('interior')
    fill.location = Vector(c['eye']) + Vector((0, 0, 0.3))
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
