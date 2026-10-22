"""v13 package: export/unity_v13/Assets/UtilityPlane from the v12 edition-2 package (export/unity_v12r2) +
 - Models/UtilityPlane.fbx and Data (sockets, lod, doors - new) from the v13 export (export/unity_v13fx: light fixtures,
   lenses with T_Lens UVs, sliding-door rails in Body, roller arms on CargoDoor_L/R);
 - Textures/T_Lens_BaseColor.png, T_Lens_Emission.png (v13/tex, lens_tex_v13.py);
 - Scripts/UtilityPlaneRig.cs, Editor/UtilityPlaneSetup.cs (v13/pkg_src: sliding cargo doors, textured lenses);
 - Data/lights.json: positions of the 8 exterior lights from the new sockets; Data/atlas_texel.json: + Lens.
The other files are the v12 edition-2 files unchanged; docs are patched by build_docs13.py.
python3 make_package_v13.py"""
import os, shutil, json, re, hashlib
import numpy as np

SRC = '/home/claude/plane/export/unity_v12r2/Assets/UtilityPlane'
FX = '/home/claude/plane/export/unity_v13fx/Assets/UtilityPlane'
DST = '/home/claude/plane/export/unity_v13/Assets/UtilityPlane'
V13 = '/home/claude/plane/v13'

if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)

# ------------------------------------------------------------------ model and data from the v13 export
shutil.copyfile(os.path.join(FX, 'Models', 'UtilityPlane.fbx'), os.path.join(DST, 'Models', 'UtilityPlane.fbx'))
changed = []
for f in sorted(os.listdir(os.path.join(FX, 'Data'))):
    a, b = os.path.join(FX, 'Data', f), os.path.join(DST, 'Data', f)
    if not os.path.exists(b) or open(a, 'rb').read() != open(b, 'rb').read():
        changed.append(f)
        shutil.copyfile(a, b)
print('Data from the export, changed or new:', changed)
for m in sorted(os.listdir(os.path.join(FX, 'Models'))):            # the separate models must be the v12 ones
    if m != 'UtilityPlane.fbx':
        assert os.path.getsize(os.path.join(FX, 'Models', m)) > 0

# ------------------------------------------------------------------ textures, scripts
for n in ('T_Lens_BaseColor.png', 'T_Lens_Emission.png'):
    shutil.copyfile(os.path.join(V13, 'tex', n), os.path.join(DST, 'Textures', n))
shutil.copyfile(os.path.join(V13, 'pkg_src', 'UtilityPlaneRig.cs'), os.path.join(DST, 'Scripts', 'UtilityPlaneRig.cs'))
shutil.copyfile(os.path.join(V13, 'pkg_src', 'UtilityPlaneSetup.cs'), os.path.join(DST, 'Editor', 'UtilityPlaneSetup.cs'))

# ------------------------------------------------------------------ Rig constants == Data/doors.json
rig = open(os.path.join(DST, 'Scripts', 'UtilityPlaneRig.cs'), encoding='utf-8').read()
dj = json.load(open(os.path.join(DST, 'Data', 'doors.json')))


def const(name):
    m = re.search(r'\b' + name + r'\s*=\s*([0-9.]+)f', rig)
    assert m, name
    return float(m.group(1))


for cname, key in (('SlideOut', 'out'), ('SlideBack', 'slide'), ('SlidePopEnd', 'popEnd'), ('SlideStart', 'slideStart'),
                   ('SlideTuck', 'tuck'), ('SlideTuckStart', 'tuckStart')):
    assert abs(const(cname) - dj[key]) < 1e-6, (cname, const(cname), dj[key])
for dn, d in dj['doors'].items():
    assert abs(const('CargoDoorLength') - d['length']) < 5e-4, (dn, d['length'])
print('Rig constants match Data/doors.json')

# ------------------------------------------------------------------ lights.json: exterior positions from the sockets
sock = json.load(open(os.path.join(DST, 'Data', 'sockets.json')))
lj = json.load(open(os.path.join(DST, 'Data', 'lights.json')))
PITCH, ROOTY = 9.98, -0.372


def parked(p):
    p = np.asarray(p, float)
    ph = np.radians(-PITCH)
    y = p[1] * np.cos(ph) - p[2] * np.sin(ph)
    z = p[1] * np.sin(ph) + p[2] * np.cos(ph)
    return [round(float(p[0]), 3), round(float(y + ROOTY), 3), round(float(z), 3)]


moved = []
for L in lj['lights']:
    e = sock[L['socket']]
    s = e['position'] if 'position' in e else e['position_prefab']       # Cockpit sockets: prefab-space copy
    pos = [round(a + b, 4) for a, b in zip(s, L['offsetFromSocket'])]
    if pos != L['position']:
        moved.append((L['key'], L['position'], pos))
        L['position'] = pos
        L['positionParked'] = parked(pos)
lj['note'] = lj['note'].replace('v11 lights of UtilityPlane.prefab', 'v13 lights of UtilityPlane.prefab (v13: the 8 exterior '
                                'lights sit in their new fixtures, sockets moved; everything else as v11)')
json.dump(lj, open(os.path.join(DST, 'Data', 'lights.json'), 'w'), indent=1)
print('lights moved:', len(moved))
for m in moved:
    print('  ', m)

# ------------------------------------------------------------------ atlas_texel.json: + the lens texture
at = json.load(open(os.path.join(DST, 'Data', 'atlas_texel.json')))
at = [a for a in at if a.get('atlas') != 'Lens']
at.append(dict(atlas='Lens', material='M_Light_Red, M_Light_Green, M_Light_White, M_Light_Beacon, M_Light_Landing',
               metresPerUV=0.0, pxPerMetre=0.0, areaM2=0.11, detail='', detailTiling=0.0, detailNormalScale=0.0, psx=True,
               note='v13: T_Lens_BaseColor / T_Lens_Emission 64 px (32 px per region), grey (the material colour tints '
                    'it), 8 / 6 grey steps with ordered dither; four regions: ribbed side of a round lens, dome cap, nav '
                    'lens of the wingtip housing, landing light cover with its reflector. About 180-360 px/m.'))
json.dump(at, open(os.path.join(DST, 'Data', 'atlas_texel.json'), 'w'), indent=1)

# ------------------------------------------------------------------ listing + md5
rows = []
for dp, dn, fn in os.walk(DST):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        rows.append((os.path.relpath(p, DST), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))
print('files', len(rows), 'bytes', sum(r[1] for r in rows))
