"""Renders of the road prefabs (out/road[_draft|_test].blend): each prefab on its own ground (Update 3's terrain under it,
road_ground.json) by day, the signs side by side, details; the map views from Update 3's viewpoints (Start, Bridge,
Windfall, Overlook) on Update 3's terrain with every prefab at its place and the 48 delineators (needs the terrain:
scratchpad/trail2/terrain.blend, made from Update 3's Forest_Terrain.fbx); night views with the signs' and the
reflectors' glow (headlight-like light from the camera).
python3 -I road_render.py <views|all|map> [spp] [--draft|--test] [--tag=x] -> rend/road[_draft|_test]/<view>[_tag].png"""
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
OUT = os.path.join(P.HERE, 'rend', 'road' + sfx)
os.makedirs(OUT, exist_ok=True)
TERRAIN = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend'
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'road{sfx}.blend'))
sc = bpy.context.scene
import road_spec as S
import road_kit as RK

for m in bpy.data.materials:                                         # point filter everywhere (PSX)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'
ROOTS = [c.name for c in sc.collection.children if c.name in bpy.data.objects]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}


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


def studio_ground(name, ext, step=0.25):
    """the ground under a prefab (its own frame), road cells brown"""
    v, f = RK.ground_patch(name, *ext, step=step)
    me = bpy.data.meshes.new('G_' + name)
    me.from_pydata(v, [], f)
    me.materials.append(GM_T)
    me.materials.append(GM_R)
    for poly in me.polygons:
        c = sum((Vector(v[i]) for i in poly.vertices), Vector()) / 4
        poly.material_index = 1 if S.surface(name, c.x, c.y) in 'RT' else 0
    ob = bpy.data.objects.new('G_' + name, me)
    sc.collection.objects.link(ob)
    STUDIO_G.append(ob)
    ob['for'] = name
    return ob


EXT = {'ZoneGate': (-7, 7, -5, 5), 'Bridge30': (-22, 22, -4, 4), 'OverlookDeck': (-4, 4, -3, 6), 'FallenTree': (-6, 30, -12, 12),
       'LogCut': (-8, 8, -5, 5)}


def show_only(names, at_origin=True, offsets=None):
    for n in ROOTS:
        o = bpy.data.objects[n]
        o.hide_render = n not in names
        if n in names:
            off = Vector(offsets[n]) if offsets and n in offsets else Vector()
            o.matrix_world = Matrix.Translation(off) if at_origin else MAPM[n]
        else:
            o.matrix_world = MAPM[n]
    for g in STUDIO_G:
        g.hide_render = True


# the signs side by side in two rows of six, each on its own ground
def _row(names):
    out, x = {}, 0.0
    for n in names:
        w = S.SIGNS[n]['face'][0] + 0.4
        out[n] = (x + w / 2, 0.0, 0.0)
        x += w + 0.6
    return {n: (v[0] - x / 2, 0.0, 0.0) for n, v in out.items()}


SIGN_ROW = _row(S.SIGN_ORDER)
ROW_A, ROW_B = _row(S.SIGN_ORDER[:6]), _row(S.SIGN_ORDER[6:])

w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.2
sun.data.angle = math.radians(2.0)
sun.rotation_euler = (math.radians(50), math.radians(6), math.radians(25))
sc.collection.objects.link(sun)
head = bpy.data.objects.new('head', bpy.data.lights.new('head', 'SPOT'))      # a torch / headlights for the night views
head.data.energy = 900.0
head.data.spot_size = math.radians(60)
head.data.color = (1.0, 0.95, 0.85)
sc.collection.objects.link(head)

VIEWS = {
    # the signs
    'signs_row': dict(roots=list(S.SIGN_ORDER[:6]), offsets=ROW_A, eye=(0.0, -10.5, 1.8), tgt=(0.0, 0.0, 1.35), lens=24,
                      ground='signs'),
    'signs_row2': dict(roots=list(S.SIGN_ORDER[6:]), offsets=ROW_B, eye=(0.0, -9.0, 1.8), tgt=(0.0, 0.0, 1.35), lens=24,
                       ground='signs'),
    'signs_back': dict(roots=list(S.SIGN_ORDER[:6]), offsets=ROW_A, eye=(3.0, 7.5, 2.2), tgt=(0.5, 0.0, 1.4), lens=24,
                       ground='signs'),
    'sign_obs': dict(roots=['Sign_Observatory'], eye=(1.2, -3.6, 1.7), tgt=(0.0, 0.0, 1.85), lens=26, ground='one'),
    'sign_obs_back': dict(roots=['Sign_Observatory'], eye=(-1.0, 1.5, 1.7), tgt=(0.0, 0.0, 1.9), lens=30, ground='one'),
    'sign_dist23': dict(roots=['Dist_23'], eye=(0.9, -2.6, 1.6), tgt=(0.0, 0.0, 1.45), lens=28, ground='one'),
    'europost': dict(roots=['EuroPost'], eye=(1.4, -1.9, 1.1), tgt=(0.0, 0.0, 0.6), lens=34, ground='flat'),
    # the gate
    'gate_out': dict(roots=['ZoneGate'], eye=(2.5, -9.5, 1.8), tgt=(0.0, 0.0, 1.4), lens=24, ground='one'),
    'gate_in': dict(roots=['ZoneGate'], eye=(-3.0, 9.0, 1.8), tgt=(0.0, 0.0, 1.4), lens=24, ground='one'),
    'gate_lock': dict(roots=['ZoneGate'], eye=(0.6, 1.3, 1.4), tgt=(0.0, 0.0, 1.1), lens=30, ground='one'),
    'gate_hinge': dict(roots=['ZoneGate'], eye=(-2.9, -1.4, 1.9), tgt=(-4.1, 0.0, 1.6), lens=30, ground='one'),
    # the bridge
    'bridge_side': dict(roots=['Bridge30'], eye=(8.0, -24.0, -4.5), tgt=(0.0, 0.0, -4.0), lens=22, ground='one'),
    'bridge_low': dict(roots=['Bridge30'], eye=(3.0, -9.0, -10.6), tgt=(4.0, 0.0, -4.0), lens=18, ground='one'),
    'bridge_deck': dict(roots=['Bridge30'], eye=(-18.5, 0.6, 1.65), tgt=(0.0, 0.0, 0.6), lens=24, ground='one'),
    'bridge_end': dict(roots=['Bridge30'], eye=(-19.5, -6.0, 2.2), tgt=(-14.0, 0.0, -0.3), lens=26, ground='one'),
    'bridge_under': dict(roots=['Bridge30'], eye=(-8.5, -5.5, -2.6), tgt=(-3.0, 0.0, -1.4), lens=22, ground='one'),
    'bridge_bank': dict(roots=['Bridge30'], eye=(10.0, -5.5, -2.8), tgt=(14.0, 0.0, -0.8), lens=24, ground='one'),
    # the overlook
    'deck_front': dict(roots=['OverlookDeck'], eye=(3.2, -5.5, 2.0), tgt=(0.0, 1.6, 0.8), lens=24, ground='one'),
    'deck_back': dict(roots=['OverlookDeck'], eye=(-4.0, 8.0, 0.8), tgt=(0.0, 1.8, 0.6), lens=24, ground='one'),
    'deck_on': dict(roots=['OverlookDeck'], eye=(-1.6, 0.3, 2.35), tgt=(1.2, 3.6, 1.5), lens=22, ground='one'),
    # the windfall
    'tree_road': dict(roots=['FallenTree', 'LogCut'], eye=(15.8, -11.5, 1.9), tgt=(16.0, 3.0, 0.5), lens=22, ground='wind'),
    'tree_root': dict(roots=['FallenTree'], eye=(-5.0, -4.0, 2.2), tgt=(1.5, 0.0, 0.8), lens=24, ground='one'),
    'tree_cut': dict(roots=['FallenTree', 'LogCut'], eye=(14.8, -2.2, 1.2), tgt=(12.8, 0.2, 0.25), lens=30, ground='wind'),
    'tree_crown': dict(roots=['FallenTree'], eye=(28.0, -6.0, 2.6), tgt=(23.0, 0.0, 0.3), lens=24, ground='one'),
    'log_cut': dict(roots=['LogCut'], eye=(2.6, -3.2, 1.4), tgt=(0.0, 0.0, 0.2), lens=26, ground='one'),
}
CMPV = json.load(open(os.path.join(P.HERE, 'road_cmp_views.json')))       # the same cameras as Update 3's renders
for vn, cv in CMPV.items():
    VIEWS[vn] = dict(roots=[cv['prefab']], eye=tuple(cv['eye']), tgt=tuple(cv['tgt']), lens=cv['lens'], ground='one', cmp=True)
MAPV = {}                                                               # Update 3's viewpoints (Forest_Layout.json)
for vn in ('Start', 'Bridge', 'Windfall', 'Overlook'):
    vp = S.U3['viewpoints'][vn]
    MAPV['map_' + vn.lower()] = dict(map=True, eye=(-vp['p'][0], -vp['p'][2], vp['p'][1]),
                                     tgt=(-vp['target'][0], -vp['target'][2], vp['target'][1]), fov=vp['fov'])
def _mapped(prefab, eye, tgt):
    M = S.map_matrix(prefab)
    return (tuple((M @ np.array([*eye, 1.0]))[:3]), tuple((M @ np.array([*tgt, 1.0]))[:3]))


_e, _t = _mapped('ZoneGate', (2.5, 13.0, 0.7), (0.0, 0.0, 1.3))           # from the car's side (+y)
MAPV['map_gate'] = dict(map=True, eye=_e, tgt=_t, fov=40.0)
_e, _t = _mapped('OverlookDeck', (4.5, -7.0, 2.2), (0.0, 1.6, 0.8))
MAPV['map_deck'] = dict(map=True, eye=_e, tgt=_t, fov=40.0)
_e, _t = _mapped('Bridge30', (-24.0, -9.0, 3.0), (0.0, 0.0, -2.5))
MAPV['map_bridge_side'] = dict(map=True, eye=_e, tgt=_t, fov=40.0)
MAPV['map_gate_night'] = dict(map=True, night=True, exp=2.4, **{k: MAPV['map_gate'][k] for k in ('eye', 'tgt', 'fov')})
MAPV['map_windfall_night'] = dict(map=True, night=True, exp=2.4, **{k: MAPV['map_windfall'][k] for k in ('eye', 'tgt', 'fov')})
VIEWS.update(MAPV)

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
    ep = bpy.data.objects['EuroPost']
    for i, e in enumerate(S.U3['europosts'][1:]):
        c = ep.copy()
        c.name = f'EP_{i}'
        c.matrix_world = Matrix([list(r) for r in S.frame_matrix(e['p'], e['q'])])
        sc.collection.objects.link(c)
        TERR.append(c)


P.setup_cycles((1100, 700), int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 24)
sc.cycles.max_bounces = 4
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
want = ([v for v in VIEWS if v not in MAPV and v not in CMPV] if sys.argv[1] == 'all' else list(MAPV) if sys.argv[1] == 'map'
        else list(CMPV) if sys.argv[1] == 'cmp' else sys.argv[1].split(','))
for v in want:
    c = VIEWS[v]
    night = c.get('night', False)
    if c.get('map'):
        load_terrain()
        for n in ROOTS:
            o = bpy.data.objects[n]
            o.hide_render = False
            o.matrix_world = MAPM[n]
        for g in STUDIO_G:
            g.hide_render = True
        for o in TERR:
            o.hide_render = False
        sc.render.resolution_x, sc.render.resolution_y = 1281, 720
        cam.data.sensor_fit = 'VERTICAL'
        cam.data.angle_y = math.radians(c['fov'])
    else:
        for o in TERR:
            o.hide_render = True
        show_only(c['roots'], True, c.get('offsets'))
        if c.get('ground') == 'signs':
            for n in c['roots']:
                g = next((g for g in STUDIO_G if g['for'] == n), None) or studio_ground(n, (-1.6, 1.6, -0.6, 0.6), 0.1)
                g.matrix_world = Matrix.Translation(Vector(c['offsets'][n]))
                g.hide_render = False
        elif c.get('ground') == 'flat':
            g = next((g for g in STUDIO_G if g['for'] == 'flat'), None)
            if g is None:
                me = bpy.data.meshes.new('G_flat')
                me.from_pydata([(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [], [(0, 1, 2, 3)])
                me.materials.append(GM_T)
                g = bpy.data.objects.new('G_flat', me)
                sc.collection.objects.link(g)
                g['for'] = 'flat'
                STUDIO_G.append(g)
            g.hide_render = False
        elif c.get('ground') in ('one', 'wind'):
            for n in c['roots']:
                ext = EXT.get(n, (-1.6, 1.6, -0.6, 0.6))
                g = next((g for g in STUDIO_G if g['for'] == n), None) or studio_ground(n, ext, 0.25 if n != 'FallenTree' else 0.5)
                g.hide_render = n != c['roots'][0] if c.get('ground') == 'one' else n != 'FallenTree'
            if c.get('ground') == 'wind':                               # the log at its place in the tree's frame
                F = np.array(S.GROUND['prefabs']['FallenTree']['world'])
                Lm = np.array(S.GROUND['prefabs']['LogCut']['world'])
                bpy.data.objects['LogCut'].matrix_world = Matrix([list(r) for r in (np.linalg.inv(F) @ Lm)])
        sc.render.resolution_x, sc.render.resolution_y = (800, 520) if c.get('cmp') else (1100, 700)
        cam.data.sensor_fit = 'AUTO'
        cam.data.lens = c['lens']
    cam.location = Vector(c['eye'])
    cam.rotation_euler = (Vector(c['tgt']) - Vector(c['eye'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start, cam.data.clip_end = 0.05, 1500
    bg.inputs[0].default_value = (0.02, 0.025, 0.035, 1) if night else (0.56, 0.62, 0.72, 1)
    bg.inputs[1].default_value = 0.25 if night else 0.9
    sun.data.energy = 0.05 if night else 3.2
    sun.data.color = (0.62, 0.72, 1.0) if night else (1.0, 0.97, 0.92)
    head.hide_render = not night
    head.location = cam.location + Vector((0, 0, -0.6))
    head.rotation_euler = cam.rotation_euler
    ims = sc.render.image_settings
    if not night:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.render.filepath = os.path.join(OUT, v + TAG + '.png')
        bpy.ops.render.render(write_still=True)
    else:
        for m in bpy.data.materials:                                  # the signs' and reflectors' glow (game values)
            if m.use_nodes and 'night_emit' in m:
                pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
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
            if m.use_nodes and 'night_emit' in m:
                pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                pb.inputs['Emission Strength'].default_value = 0.0
    print('view', v, f'{time.time() - T0:.1f}s', flush=True)
