"""forest_base_yard_v1: BaseYard.json from the Blender export (data/export_data.json) + the material table; the step, the apply
script, the asphalt, the generator diff, sources and renders in place. python3 -I make_pkg.py"""
import json, os, shutil, hashlib

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PK = os.path.join(D, 'pkg', 'forest_base_yard_v1')
U = os.path.join(PK, 'unity')
BY = os.path.join(U, 'Assets', 'Snow', 'Levels', 'Forest', 'BaseYard')
ED = os.path.join(U, 'Assets', 'Snow', 'Editor')

P, B = 'point', 'bilinear'
MATS = [  # name, texture, colour, smoothness, metallic, emission (r, g, b, intensity), filter
    ('M_BaseConcrete', 'T_BaseConcrete_px.png', (0.78, 0.78, 0.76), 0.05, 0.0, None, P),
    ('M_BaseConcreteDark', 'T_BaseConcrete_px.png', (0.36, 0.33, 0.31), 0.05, 0.0, None, P),
    ('M_BaseCurb', 'T_BaseConcrete_px.png', (0.82, 0.82, 0.80), 0.05, 0.0, None, P),
    ('M_BaseSteel', 'T_BaseSteel_px.png', (0.55, 0.56, 0.58), 0.3, 0.3, None, P),
    ('M_BaseSteelDark', 'T_BaseSteel_px.png', (0.22, 0.23, 0.24), 0.25, 0.3, None, P),
    ('M_BaseOlive', 'T_BaseOlive_px.png', (0.85, 0.90, 0.80), 0.1, 0.0, None, P),
    ('M_BaseRust', 'T_BaseRust_px.png', (0.80, 0.75, 0.70), 0.05, 0.0, None, P),
    ('M_BaseContRed', 'T_BaseContRibs_px.png', (0.50, 0.13, 0.08), 0.15, 0.0, None, P),
    ('M_BaseContBlue', 'T_BaseContRibs_px.png', (0.14, 0.22, 0.32), 0.15, 0.0, None, P),
    ('M_BaseContOlive', 'T_BaseContRibs_px.png', (0.24, 0.28, 0.16), 0.15, 0.0, None, P),
    ('M_BaseCorrDark', 'T_BaseCorr_px.png', (0.24, 0.29, 0.26), 0.15, 0.0, None, P),
    ('M_BaseWood', 'T_BaseWood_px.png', (0.62, 0.52, 0.42), 0.05, 0.0, None, P),
    ('M_BaseWhite', None, (0.78, 0.79, 0.80), 0.2, 0.0, None, P),
    ('M_BaseRed', None, (0.60, 0.05, 0.035), 0.3, 0.0, None, P),
    ('M_BaseYellow', None, (0.90, 0.62, 0.04), 0.3, 0.0, None, P),
    ('M_BaseBlack', None, (0.025, 0.025, 0.025), 0.2, 0.0, None, P),
    ('M_BaseOrange', None, (1.0, 0.33, 0.02), 0.3, 0.0, None, P),
    ('M_BaseGlass', None, (0.03, 0.035, 0.04), 0.8, 0.0, None, P),
    ('M_BaseDrumBlue', None, (0.07, 0.16, 0.38), 0.3, 0.0, None, P),
    ('M_BaseDrumRed', None, (0.42, 0.07, 0.04), 0.3, 0.0, None, P),
    ('M_BaseDrumGreen', None, (0.12, 0.20, 0.10), 0.3, 0.0, None, P),
    ('M_BaseBag', None, (0.015, 0.015, 0.017), 0.6, 0.0, None, P),
    ('M_BaseBin', None, (0.06, 0.15, 0.08), 0.3, 0.0, None, P),
    ('M_BaseSignBlue', None, (0.03, 0.08, 0.25), 0.3, 0.0, None, P),
    ('M_BaseLetters', None, (0.85, 0.85, 0.85), 0.3, 0.0, None, P),
    ('M_BaseSoot', None, (0.03, 0.028, 0.026), 0.05, 0.0, None, P),
    ('M_BasePloughOrange', None, (0.85, 0.30, 0.03), 0.3, 0.0, None, P),
    ('M_BaseIce', None, (0.72, 0.80, 0.88), 0.85, 0.0, None, P),
    ('M_BaseRadome', None, (0.86, 0.87, 0.88), 0.35, 0.0, None, P),
    ('M_BaseStripeYB', 'T_BaseStripeYB_px.png', (1.0, 1.0, 1.0), 0.3, 0.0, None, P),
    ('M_BaseBandRW', 'T_BaseBandRW_px.png', (1.0, 1.0, 1.0), 0.3, 0.0, None, P),
    ('M_BaseWindowGlow', None, (0.20, 0.14, 0.08), 0.2, 0.0, (1.0, 0.62, 0.32, 1.7), P),
    ('M_BaseLampGlow', None, (0.90, 0.80, 0.60), 0.2, 0.0, (1.0, 0.80, 0.50, 6.0), P),
    ('M_BaseRedLight', None, (0.80, 0.05, 0.03), 0.2, 0.0, (1.0, 0.05, 0.02, 6.0), P),
    ('M_BaseSnow', 'T_BaseSnow_A.png', (1.0, 1.0, 1.0), 0.1, 0.0, None, B),
    ('M_BaseSnowDark', 'T_BaseSnowDark_A.png', (1.0, 1.0, 1.0), 0.1, 0.0, None, B),
    ('M_BaseSnowChunk', 'T_BaseSnowChunk_A.png', (1.0, 1.0, 1.0), 0.1, 0.0, None, B),
]


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    ex = json.load(open(os.path.join(D, 'data', 'export_data.json')))
    used = {m for o in ex['objects'] for m in o['materials']}
    defs = [{'name': n, 'texture': t or '', 'color': list(c), 'smoothness': s, 'metallic': mt,
             'emission': list(e) if e else [0, 0, 0, 0], 'filter': f} for (n, t, c, s, mt, e, f) in MATS]
    missing = used - {d['name'] for d in defs}
    assert not missing, missing
    for d in defs:
        if d['texture']:
            assert os.path.exists(os.path.join(BY, d['texture'])), d['texture']
    models = [{'model': m['model'], 'collider': m['collider'], 'pos': m['pos'], 'yaw': m['yaw'],
               'parts': [{'mesh': k, 'materials': v} for k, v in m['materials'].items()]} for m in ex['models']]
    data = {
        'note': 'Base yard of the Blender concept 28.10.2026 (source/assets/forest_base_yard_v1): package model (world space), '
                'project model copies, props, light, smoke, Terrain clearing and paint; Unity x, y, z. Read by '
                'Snow.EditorTools.ForestBaseYardStep.',
        'model': 'Assets/Snow/Levels/Forest/BaseYard/Forest_BaseYard.fbx',
        'materials': [d for d in defs if d['name'] in used],
        'objects': [{'name': o['name'], 'materials': o['materials'], 'collider': o['collider'], 'ground': o['ground']} for o in ex['objects']],
        'models': models, 'prefabs': ex['prefabs'], 'lights': ex['lights'], 'smoke': ex['smoke'],
        'strokes': ex['strokes'], 'clear': [{'w': c.get('w', 0.0), 'p': c['p']} for c in ex['clear']],
    }
    json.dump(data, open(os.path.join(BY, 'BaseYard.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    os.makedirs(ED, exist_ok=True)
    shutil.copy(os.path.join(D, 'pkg_src', 'ForestBaseYardStep.cs'), ED)
    shutil.copy(os.path.join(D, 'pkg_src', 'forest_base_apply.cs'), U)
    asp = os.path.join(U, 'asphalt'); os.makedirs(asp, exist_ok=True)
    for n in ('T_GR_Asphalt_A.png', 'T_GR_Asphalt_M.png'):
        shutil.copy(os.path.join(D, 'asph', 'gen', n), asp)
    tools = os.path.join(PK, 'tools'); os.makedirs(tools, exist_ok=True)
    shutil.copy(os.path.join(D, 'asph', 'asphalt_recipe.diff'), tools)
    src = os.path.join(PK, 'src'); os.makedirs(src, exist_ok=True)
    for f in ('base_scene.py', 'concept.py', 'yard.py', 'export_pkg.py', 'render_blend.py', 'pkg_src/make_textures.py', 'pkg_src/make_pkg.py'):
        shutil.copy(os.path.join(D, f), src)
    ren = os.path.join(PK, 'renders'); os.makedirs(ren, exist_ok=True)
    for f in ('base_yard.jpg', 'base_gate.jpg', 'base_back.jpg', 'base_air.jpg', 'base_top.jpg'):
        shutil.copy(os.path.join(D, 'out', f), ren)
    tot = 0
    for r, _, fs in os.walk(PK):
        for f in fs:
            p = os.path.join(r, f); tot += os.path.getsize(p)
    print('materials %d, objects %d, models %d, prefabs %d, strokes %d, clear %d; %.1f MB' %
          (len(data['materials']), len(data['objects']), len(models), len(data['prefabs']), len(data['strokes']), len(data['clear']), tot / 1e6))
    print('asphalt A md5', md5(os.path.join(asp, 'T_GR_Asphalt_A.png')))


if __name__ == '__main__':
    main()
