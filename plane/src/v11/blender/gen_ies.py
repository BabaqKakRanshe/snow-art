"""IES (LM-63-2002, type C, absolute candela) for every v11 lamp, from the same emission diagrams as the cookies
(spec_v11.py), plus lights_meta.json for the Blender light rig.

Photometric frame of every file = the lamp's own frame (Unity light frame, see spec_v11.py):
  vertical angle 0 = beam axis (Unity light +Z); C = 270 - phi, phi = angle from light +X towards light +Y.
  => C0 = light -Y (bottom of the cookie), C90 = light -X (cookie left), C180 = +Y (top), C270 = +X (right).
  In Blender: a point light whose local X = light +X, local Y = light +Y, local -Z = beam axis reads it as written
  (Cycles: gamma = acos(-z), C = 270 deg - atan2(y, x)); this is how UtilityPlane_v11_lights.blend places them."""
import sys, json, numpy as np
sys.path.insert(0, '/home/claude/plane/v11'); sys.path.insert(0, '/home/claude/plane/v11/blender')
from spec_v11 import LIGHTS, cct_rgb, light_pos
from ies_lm63 import write_ies

OUT = '/home/claude/plane/v11/blender/IES/'
K_CYCLES = 0.070527          # Cycles IES node: Fac per candela (measured, 64 spp, nadir pixel)
PEAK_CD = {'Nav_L': 40, 'Nav_R': 40, 'Nav_Tail': 20, 'Strobe_L': 2000, 'Strobe_R': 2000, 'Beacon_Top': 400,
           'Beacon_Bottom': 200, 'Landing': 150000, 'Dome_L': 15, 'Dome_R': 15, 'Cargo': 25, 'Cargo_2': 25,
           'Flood': 4, 'Flood_2': 4}
DESC = {'Nav_L': 'left position light, red, 110 deg forward-left sector (FAR 25.1385-25.1391)',
        'Nav_R': 'right position light, green, 110 deg forward-right sector (FAR 25.1385-25.1391)',
        'Nav_Tail': 'tail position light, white, 140 deg aft sector (FAR 25.1385-25.1391)',
        'Strobe_L': 'left wing-tip xenon strobe, outboard half space (peak of the flash)',
        'Strobe_R': 'right wing-tip xenon strobe, outboard half space (peak of the flash)',
        'Beacon_Top': 'top rotating beacon, red, 14 deg fan from +8 to -40 deg, fan at the base heading (aft)',
        'Beacon_Bottom': 'bottom rotating beacon, red, 14 deg fan from -3 to -62 deg, fan at the base heading (forward)',
        'Landing': 'PAR landing lamp: hot core sigma 4.5 deg, lens ring at 7.5 deg, skirt down to -35 deg',
        'Dome_L': 'cabin dome lamp, housing edge at 57 deg', 'Dome_R': 'cabin dome lamp, housing edge at 57 deg',
        'Cargo': 'cargo bay fluorescent tube, wide across the bay, narrower along it',
        'Cargo_2': 'cargo bay fluorescent tube, wide across the bay, narrower along it',
        'Flood': 'red panel flood under the glareshield', 'Flood_2': 'red panel flood under the glareshield'}
LAMP = {'incandescent': 'incandescent', 'xenon': 'xenon flash tube', 'fluorescent': 'fluorescent tube'}

H = np.arange(0.0, 360.0 + 1e-9, 2.5)
meta = {}
for L in LIGHTS:
    key = L['key']
    if L['em'] is None:
        continue
    if key == 'Landing':
        Vg = np.unique(np.r_[np.arange(0, 20, 0.25), np.arange(20, 60, 0.5), np.arange(60, 180.001, 1.0)])
    else:
        Vg = np.arange(0.0, 180.001, 1.0)
    G, C = np.meshgrid(np.radians(Vg), np.radians(H))            # [nH, nV]
    phi = np.radians(270.0) - C
    l = np.stack([np.sin(G) * np.cos(phi), np.sin(G) * np.sin(phi), np.cos(G)], -1)   # Unity light frame
    d = l @ L['R'].T                                                                    # Unity plane frame
    e = np.clip(L['em'](d, l), 0.0, None)
    e[e < 1e-4] = 0.0
    peak = PEAK_CD[key]
    cd = peak * e / max(e.max(), 1e-9)
    kw = {'TEST': 'computed from the v11 emission diagram (spec_v11.py), same shape as T_Cookie_%s.png' % key,
          'TESTLAB': 'Utility Plane v11 (Snow)', 'MANUFAC': 'Utility Plane v11 (Snow)', 'LUMCAT': key,
          'LUMINAIRE': DESC[key], 'LAMP': '%s, %d K' % (LAMP[L['kind']], L['cct']),
          'OTHER': 'nadir (0 deg) = beam axis; C0 = light -Y, C90 = light -X, C180 = light +Y, C270 = light +X',
          'MORE': 'candela = UNITY_CONTRACT section 7 HDRP column (TEMPORARY); shape is final'}
    write_ies(OUT + key + '.ies', Vg, H, cd, kw)
    col = (np.asarray(L['filter']) * cct_rgb(L['cct'])).tolist()
    meta[key] = dict(peak_cd=peak, k_norm=1.0 / (K_CYCLES * peak), intensity_urp=L['intensity'], cct=L['cct'],
                     filter=list(L['filter']), color_lin=col, kind=L['kind'], group=L['group'], socket=L['socket'],
                     offset=list(L['offset']), R=L['R'].tolist(), rotates=bool(L['rotates']), nV=len(Vg), nH=len(H),
                     em_max=float(e.max()))
    print('%-14s V %3d x H %3d  peak %7d cd  max(em) %.3f  nonzero %.1f%%' % (key, len(Vg), len(H), peak, e.max(), 100 * (e > 0).mean()))
for L in LIGHTS:                          # fills: no IES (uniform point lights, URP stand-ins for bounce light)
    if L['em'] is None:
        meta[L['key']] = dict(peak_cd=None, k_norm=None, intensity_urp=L['intensity'], cct=L['cct'], filter=list(L['filter']),
                              color_lin=(np.asarray(L['filter']) * cct_rgb(L['cct'])).tolist(), kind=L['kind'],
                              group=L['group'], socket=L['socket'], offset=list(L['offset']), R=L['R'].tolist(), rotates=False)
json.dump(meta, open(OUT + 'lights_meta.json', 'w'), indent=1)
print('written', len(meta))
