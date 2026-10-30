"""forest_start_post_v1: the package folder from pkg_build (export_pkg.py): step data, the new ForestStartDress.json, textures,
the ground delta, the step, the apply script, sources and renders. python3 -I make_pkg.py"""
import json, os, shutil, hashlib, math
from PIL import Image

P_ = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(P_)
B = os.path.join(D, 'pkg_build')
PK = os.path.join(D, 'pkg', 'forest_start_post_v1')
U = os.path.join(PK, 'unity')
SP = os.path.join(U, 'Assets', 'Snow', 'Levels', 'Forest', 'StartPost')
ED = os.path.join(U, 'Assets', 'Snow', 'Editor')
UP = '/mnt/user-data/uploads/snow'
GT = UP + '/Snow/Assets/Locations/Forest/Terrain/Ground/'
TEX = UP + '/source/world_sync/forest/map/textures/'
FOLDER = 'Assets/Snow/Levels/Forest/StartPost'

P, BL = 'point', 'bilinear'
MATS = [  # name, texture, colour, smoothness, metallic, emission (r, g, b, intensity), filter
    ('M_SP_Snow', 'T_SP_Snow_A.png', (1.0, 1.0, 1.0), 0.1, 0.0, None, BL),
    ('M_SP_SnowTrodden', 'T_SP_SnowTrodden_A.png', (1.0, 1.0, 1.0), 0.1, 0.0, None, BL),
    ('M_SP_Plate', 'T_SP_Plate_px.png', (1.0, 1.0, 1.0), 0.3, 0.0, None, P),
    ('M_SP_PlateBack', None, (0.55, 0.56, 0.56), 0.3, 0.0, None, P),
    ('M_SP_Plaster', 'T_SP_Plaster_px.png', (1.0, 1.0, 1.0), 0.05, 0.0, None, P),
    ('M_SP_Plinth', 'T_SP_Concrete_px.png', (0.55, 0.54, 0.52), 0.05, 0.0, None, P),
    ('M_SP_RoofEdge', None, (0.07, 0.07, 0.075), 0.2, 0.0, None, P),
    ('M_SP_Frame', None, (0.13, 0.085, 0.05), 0.2, 0.0, None, P),
    ('M_SP_Iron', None, (0.05, 0.05, 0.05), 0.3, 0.4, None, P),
    ('M_SP_Wood', 'T_SP_Wood_px.png', (0.55, 0.45, 0.35), 0.05, 0.0, None, P),
    ('M_SP_Blanket', None, (0.16, 0.18, 0.14), 0.05, 0.0, None, P),
    ('M_SP_Paper', None, (0.75, 0.73, 0.66), 0.05, 0.0, None, P),
    ('M_SP_Coat', None, (0.12, 0.14, 0.10), 0.05, 0.0, None, P),
    ('M_SP_LampGlow', None, (1.0, 0.85, 0.6), 0.2, 0.0, (1.0, 0.78, 0.45, 4.0), P),
    ('M_SP_StoveGlow', None, (0.9, 0.3, 0.05), 0.2, 0.0, (1.0, 0.35, 0.06, 4.0), P),
    ('M_SP_WindowGlow', None, (0.3, 0.15, 0.05), 0.2, 0.0, (1.0, 0.55, 0.22, 2.2), P),
    ('M_SP_Ice', None, (0.72, 0.80, 0.88), 0.85, 0.0, None, P),
]
PART_TARGET = {'Wache_Body': ('StartBooth', 'mesh'), 'Wache_Glass': ('Booth_Glass', ''), 'Wache_Lamp': ('Lamp_Booth', ''),
               'Wache_Lens': ('Lens_Booth', ''), 'Wache_Interior': ('', 'mesh'), 'Wache_StoveGlow': ('', ''), 'Wache_WinGlow': ('', ''),
               'Wache_Snow': ('', ''), 'Wache_Ice': ('', '')}


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def frame_uv(u, v):
    co, si = math.cos(math.radians(-42.3)), math.sin(math.radians(-42.3))
    return -511.5175 + u * co + v * si, 554.2235 - u * si + v * co


def textures(ex):
    os.makedirs(SP, exist_ok=True)
    for p in ex['pieces']:
        shutil.copy(os.path.join(B, 'tex', p['texture']), SP)
    shutil.copy(GT + 'T_GR_Floor_A.png', os.path.join(SP, 'T_SP_Snow_A.png'))
    shutil.copy(GT + 'T_GR_Track_A.png', os.path.join(SP, 'T_SP_SnowTrodden_A.png'))
    shutil.copy(TEX + 'T_Concrete_A_px.png', os.path.join(SP, 'T_SP_Concrete_px.png'))
    Image.open(TEX + 'T_WoodSiding_A.jpg').convert('RGB').resize((128, 128), Image.BOX).save(os.path.join(SP, 'T_SP_Wood_px.png'))
    for n in ('T_SP_Plaster_px.png', 'T_SP_Plate_px.png'):
        shutil.copy(os.path.join(D, 'tex', n), SP)


def step_data(ex):
    mats = [{'name': n, 'texture': t or '', 'color': list(c), 'smoothness': s, 'metallic': mt, 'emission': list(e) if e else [0, 0, 0, 0], 'filter': f}
            for (n, t, c, s, mt, e, f) in MATS]
    mats += [{'name': p['material'], 'texture': p['texture'], 'color': [1, 1, 1], 'smoothness': 0.1, 'metallic': 0.0, 'emission': [0, 0, 0, 0],
              'filter': BL} for p in ex['pieces']]
    names = {m['name'] for m in mats}
    used = {m for o in ex['objects'] for m in o['materials']} | {m for p in ex['wacheParts'] for m in p['materials'] if not m.endswith('Keep')}
    assert used <= names, used - names
    for m in mats:
        if m['texture']:
            assert os.path.exists(os.path.join(SP, m['texture'])), m['texture']
    a = ex['anchors']
    parts = []
    for p in ex['wacheParts']:
        tgt, col = PART_TARGET[p['mesh']]
        parts.append({'mesh': p['mesh'], 'target': tgt, 'collider': col, 'materials': p['materials']})
    data = {
        'note': 'Start post of the Blender concept 29.10.2026 (source/assets/forest_start_post_v1): the package model (world space: road '
                'strip, pad snow, plates; caps in their props\' space), the guard house prefab from the booth\'s, the RoadNet cut under the '
                'strip, the dead pad lamp, the zone under snow. Unity x, y, z. Read by Snow.EditorTools.ForestStartPostStep.',
        'model': FOLDER + '/Forest_StartPost.fbx',
        'roadMeshPrefix': 'ROADNET_',
        'materials': [m for m in mats if m['name'] in used],
        'objects': ex['objects'],
        'caps': ex['caps'],
        'wache': {
            'fbx': FOLDER + '/StartWache.fbx',
            'template': 'Assets/Locations/Forest/Start/Prefabs/StartBooth.prefab',
            'prefab': FOLDER + '/StartWache.prefab',
            'parts': parts,
            'remove': ['Booth_Sign'],
            'door': {'centre': a['door']['centre'], 'width': round(a['door']['width'], 3), 'height': round(a['door']['height'], 3)},
            'lamp': a['lamp'], 'smoke': a['smoke'], 'wind': ex['wind'],
            'lights': [{'name': 'Light_Wache_Inside', 'pos': a['inside'], 'color': [1.0, 0.66, 0.36], 'intensity': 1.4, 'range': 5.0},
                       {'name': 'Light_Wache_Stove', 'pos': a['stove'], 'color': [1.0, 0.42, 0.12], 'intensity': 0.5, 'range': 2.2}],
        },
        'roadCut': ex['roadCut'], 'treeBand': ex['treeBand'], 'zone': ex['zone'], 'zoneSoft': 5.0,
        'paint': [{'layer': 'TL_ForestFloor', 'w': 0.86}, {'layer': 'TL_ForestFloorDark', 'w': 0.14}],
        'deadLamp': ex['deadLamp'],
    }
    json.dump(data, open(os.path.join(SP, 'ForestStartPost.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return data


def dress_json():
    """ForestStartDress.json of the project (28.10) with the concept's post: the house in the booth's place, the barrier turned
    and moved before the window, props where the concept has them (the scene of the 21:41 export), the pad under snow"""
    src = UP + '/Snow/Assets/Snow/Levels/Forest/ForestStartDress.json'
    d = json.load(open(src, encoding='utf-8'))
    old = {p['prefab'].split('/')[-1].replace('.prefab', ''): p for p in d['props']}

    def prop(name, u, v, yaw, **kw):
        p = dict(old.get(name, {}))
        p.update({'prefab': p.get('prefab', ''), 'u': u, 'v': v, 'yaw': yaw})
        p.update(kw)
        return p
    stones = [p for p in d['props'] if 'ForestStone' in p['prefab']]
    props = [
        {'prefab': FOLDER + '/StartWache.prefab', 'u': -8.5, 'v': -3.4, 'yaw': 180, 'lamp': old['StartBooth'].get('lamp', {'color': [1.0, 0.74, 0.46]})},
        prop('StartLamp', -4.9, -0.9, 125.3),
        prop('LightPole', -13.56, -7.25, -168.4),
        prop('StartCar', -9.02, -18.18, 0),
        prop('StartTrash', -12.16, -7.39, 12),
        prop('StartTyres', -12.74, -8.72, 30),
        prop('StartTyres', -11.81, -10.54, -23.2),
        prop('Sign_Halt', -4.79, 1.69, 28.7),
        prop('Sign_NoEntry', 4.12, 2.77, 0),
        prop('Crates', -12.5, -6.4, 8),
        dict(old['RoadBlock_Jersey'], u=-12.11, v=-22.8, yaw=0),
        dict(old['RoadBlock_Jersey'], u=-9.33, v=-22.8, yaw=0),
        dict(old['RoadBlock_Jersey'], u=-6.57, v=-23.35, yaw=6),
        prop('Barrier_Manual', -3.15, -4.0, 180),
    ] + stones
    for p in props:
        assert p.get('prefab'), p
    d['props'] = props
    d['moves'] = [{'name': 'Sign_Observatory', 'u': 5.1, 'v': -5.0, 'yaw': 180.0}]
    d['asphaltShare'] = 0.0
    d['pebbles'] = 0.0
    d['_doc'] = d['_doc'] + (' Package forest_start_post_v1 (29.10, Blender concept, targets concept_v3 arrive_wache + night_wache, QUESTIONS_3 '
                             'all accepted): the booth gives way to the guard house StartWache.prefab (u -8.5, v -3.4, yaw 180: big window to '
                             'the barrier, door to the road); the barrier turned (pivot at the house, arm over the road, raised) and set before '
                             'the window inside the gate; props where the scene had them (export 28.10 21:41), the crates off the house corner, '
                             'the tripod at the gate post, one pad lamp (dead: ForestStartPostStep); the wire barricade gone; the pad under '
                             'snow (asphaltShare 0, pebbles 0).')
    text = json.dumps(d, ensure_ascii=False, indent=1)
    open(os.path.join(U, 'ForestStartDress.json'), 'w', encoding='utf-8', newline='\n').write(text)
    return md5(src)


def main():
    if os.path.exists(PK):
        shutil.rmtree(PK)
    os.makedirs(SP); os.makedirs(ED)
    ex = json.load(open(os.path.join(B, 'export.json')))
    textures(ex)
    for f in ('Forest_StartPost.fbx', 'StartWache.fbx'):
        shutil.copy(os.path.join(B, 'unity', f), SP)
    data = step_data(ex)
    base_md5 = dress_json()
    shutil.copy(os.path.join(P_, 'ForestStartPostStep.cs'), ED)
    shutil.copy(os.path.join(P_, 'forest_start_post_apply.cs'), U)
    for f in ('ground_delta.f32', 'ground_delta.json'):
        shutil.copy(os.path.join(B, 'unity', f), U)
    shutil.copy(UP + '/source/world_sync/forest/map/ground.r16', os.path.join(U, 'base_ground.r16'))
    src = os.path.join(PK, 'src'); os.makedirs(src)
    for f in ('start_scene.py', 'frame.py', 'concept.py', 'make_tex.py', 'plan_view.py', 'make_compare.py',
              'pkg_src/export_pkg.py', 'pkg_src/make_pkg.py'):
        shutil.copy(os.path.join(D, f), src)
    ren = os.path.join(PK, 'renders'); os.makedirs(ren)
    for f in ('start_arrive.jpg', 'start_booth.jpg', 'start_spawn.jpg', 'start_air.jpg', 'start_plan.jpg'):
        shutil.copy(os.path.join(D, 'out', f), ren)
    tot = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(PK) for f in fs)
    print('materials %d, objects %d, caps %d, wache parts %d; base ForestStartDress md5 %s; %.1f MB' %
          (len(data['materials']), len(data['objects']), len(data['caps']), len(data['wache']['parts']), base_md5, tot / 1e6))
    print('new ForestStartDress md5', md5(os.path.join(U, 'ForestStartDress.json')))


if __name__ == '__main__':
    main()
