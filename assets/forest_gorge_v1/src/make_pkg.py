"""forest_gorge_v1 package: unity data + step + apply script + doc (written separately) + src."""
import json, os, shutil, hashlib
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
UP = '/mnt/user-data/uploads/snow'
PK = os.path.join(D, 'pkg', 'forest_gorge_v1')
U = os.path.join(PK, 'unity')
GORGE = os.path.join(U, 'Assets', 'Snow', 'Levels', 'Forest', 'Gorge')
EDITOR = os.path.join(U, 'Assets', 'Snow', 'Editor')
LEVELS = os.path.join(U, 'Assets', 'Snow', 'Levels', 'Forest')
PKG_DEVICE = 'F:/ClaudeGames/snow/source/assets/forest_gorge_v1/unity/'


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    if os.path.exists(PK):
        shutil.rmtree(PK)
    for p in (GORGE, EDITOR, os.path.join(PK, 'src'), os.path.join(PK, 'renders')):
        os.makedirs(p, exist_ok=True)
    # ground: delta + its own base (the map export it was made on)
    shutil.copy(os.path.join(D, 'unity', 'ground_delta.f32'), U)
    shutil.copy(UP + '/source/world_sync/forest/map/ground.r16', os.path.join(U, 'base_ground.r16'))
    info = json.load(open(os.path.join(D, 'unity', 'ground_delta.json')))
    info['base'] = PKG_DEVICE + 'base_ground.r16'
    info['blend'] = 'forest_gorge_v1 src/full_params.py (map export 2026-10-28 20:03 minus the 28.10 Bridge30 gorge delta = the old ground, new gorge on it)'
    json.dump(info, open(os.path.join(U, 'ground_delta.json'), 'w', encoding='utf-8'), indent=1)
    # the step, the apply script
    shutil.copy(os.path.join(D, 'pkg_src', 'ForestGorgeStep.cs'), EDITOR)
    shutil.copy(os.path.join(D, 'pkg_src', 'forest_gorge_apply.cs'), U)
    # model, textures, mask, data
    shutil.copy(os.path.join(D, 'out', 'Forest_Gorge.fbx'), GORGE)
    shutil.copy(UP + '/Snow/Assets/Locations/Forest/Terrain/Ground/T_GR_Rock_A.png', os.path.join(GORGE, 'T_GorgeRock_A_px.png'))
    shutil.copy(UP + '/Snow/Assets/Locations/Forest/Terrain/Ground/T_GR_Floor_A.png', os.path.join(GORGE, 'T_GorgeSnow_A_px.png'))
    shutil.copy(os.path.join(D, 'unity', 'gorge_mask.u8'), os.path.join(GORGE, 'gorge_mask.bytes'))
    mask = json.load(open(os.path.join(D, 'data', 'mask.json')))
    mask['file'] = 'gorge_mask.bytes'
    model = json.load(open(os.path.join(D, 'data', 'gorge_model.json')))
    data = {
        'note': 'NW river gorge (source/assets/forest_gorge_v1, 28.10.2026): rock model, gorge mask (1 walls and ledges, 3 floor, 2 rim band), '
                'spruces on the wide ledges; Unity x, z. Read by Snow.EditorTools.ForestGorgeStep.',
        'model': 'Assets/Snow/Levels/Forest/Gorge/Forest_Gorge.fbx',
        'mask': mask,
        'materials': [
            {'key': 'RockA', 'name': 'M_GorgeRock_A', 'texture': 'T_GorgeRock_A_px.png', 'color': [1.0, 1.0, 1.0]},
            {'key': 'RockB', 'name': 'M_GorgeRock_B', 'texture': 'T_GorgeRock_A_px.png', 'color': [0.87, 0.88, 0.9]},
            {'key': 'RockC', 'name': 'M_GorgeRock_C', 'texture': 'T_GorgeRock_A_px.png', 'color': [0.74, 0.75, 0.78]},
            {'key': 'Snow', 'name': 'M_GorgeSnow', 'texture': 'T_GorgeSnow_A_px.png', 'color': [1.0, 1.0, 1.0]},
        ],
        'ledgeTrees': model['ledgeTrees'],
    }
    json.dump(data, open(os.path.join(GORGE, 'ForestGorge.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    # streams: the NW_gorge creek and cut replaced, the rest as it is
    src = UP + '/Snow/Assets/Snow/Levels/Forest/ForestStreams.json'
    assert md5(src) == '3282727b171c5b835885cdb248082634', md5(src)
    st = json.loads(open(src, encoding='utf-8').read())
    cr = json.load(open(os.path.join(D, 'data', 'creek.json')))
    st['creeks'] = [c for c in st['creeks'] if c['name'] != 'NW_gorge'] + [cr['creek']]
    st['cut'] = [c for c in st['cut'] if c['name'] != 'NW_gorge'] + [cr['cut']]
    st['note'] += (' NW_gorge (28.10.2026, source/assets/forest_gorge_v1): the NW river in a stepped rock gorge along its whole'
                   ' length, the creek fills the gorge floor; the cut takes the package water off from the spring to the map edge.')
    open(os.path.join(LEVELS, 'ForestStreams.json'), 'w', encoding='utf-8', newline='\n').write(json.dumps(st, ensure_ascii=False))
    json.dump({'creek': cr['creek'], 'cut': cr['cut']}, open(os.path.join(U, 'streams_nw_gorge.json'), 'w', encoding='utf-8'), indent=1)
    # sources
    for f in ('full_params.py', 'gorge_model.py', 'preview.py', 'extract_tile.py', 'make_pkg.py'):
        shutil.copy(os.path.join(D, f), os.path.join(PK, 'src'))
    print('streams md5 new', md5(os.path.join(LEVELS, 'ForestStreams.json')))
    tot = 0
    for r, _, fs in os.walk(PK):
        for f in fs:
            p = os.path.join(r, f); tot += os.path.getsize(p)
            print('%10d  %s' % (os.path.getsize(p), os.path.relpath(p, PK)))
    print('total %.1f MB' % (tot / 1e6))


if __name__ == '__main__':
    main()
