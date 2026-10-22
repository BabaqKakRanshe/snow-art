"""Data/lights.json for the package (from spec_v11)."""
import json, sys, numpy as np
from spec_v11 import LIGHTS, SOCKETS, light_pos, parked_to_world
HDRP = {'Nav_L': 40, 'Nav_R': 40, 'Nav_Tail': 20, 'Strobe_L': 2000, 'Strobe_R': 2000, 'Beacon_Top': 400, 'Beacon_Bottom': 200,
        'Landing': 150000, 'Dome_L': 15, 'Dome_R': 15, 'Cargo': 25, 'Cargo_2': 25, 'Flood': 4, 'Flood_2': 4,
        'Fill_Cockpit': 2, 'Fill_Bay': 3}
FIELD = {'nav': 'navLights', 'strobe': 'strobeLights', 'beacon': 'beaconLights', 'landing': 'landingLight',
         'cabin': 'cabinLight', 'cargo': 'cargoLight', 'flood': 'floodLight (x busPowered)'}
TIER = {'low': 0, 'medium': 1, 'high': 2}
LENS = {'Nav_L': 'Lens_Nav_L', 'Nav_R': 'Lens_Nav_R', 'Nav_Tail': 'Lens_Nav_Tail', 'Strobe_L': 'Lens_Strobe_L',
        'Strobe_R': 'Lens_Strobe_R', 'Beacon_Top': 'Lens_Beacon_Top', 'Beacon_Bottom': 'Lens_Beacon_Bottom',
        'Landing': 'Lens_Landing', 'Dome_L': 'Lens_Dome', 'Cargo': 'Lens_CargoLight', 'Flood': 'Lens_Flood_L', 'Flood_2': 'Lens_Flood_R'}
r = lambda v, n=4: [round(float(x), n) for x in v]
items = []
for L in LIGHTS:
    d = dict(key=L['key'], light='Light_' + L['key'], socket=L['socket'], type=L['type'].capitalize(),
             position=r(light_pos(L)), offsetFromSocket=r(L['offset']), forward=r(L['fwd']), up=r(L['up'], 3),
             range=L['range'], intensityURP=L['intensity'], intensityHDRPcandela=HDRP[L['key']],
             kelvin=L['cct'], filterLinear=r(L['filter'], 3), lamp=L['kind'], drivenBy=FIELD[L['group']],
             lens=LENS.get(L['key']))
    if L['type'] == 'spot':
        d.update(spotOuter=L['outer'], spotInner=L['inner'], cookie='T_Cookie_%s' % L['key'])
    if L['shadows']:
        d.update(shadowTier=TIER[L['shadows']], shadowsFromQuality=L['q'] if L['q'] else 'High', shadowNearPlane=L['near'])
    elif L['group'] == 'beacon':
        d.update(shadowTier=0, shadowsFromQuality='High')
    if L['rotates']:
        d.update(rotates='about the plane up axis, beaconRpm (45) x sqrt(beaconLights)')
    if L['glow']:
        d['glow'] = {k: (r(v, 3) if isinstance(v, np.ndarray) else v) for k, v in L['glow'].items()}
    if L['beam']:
        d['beam'] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in L['beam'].items()}
    d['positionParked'] = r(parked_to_world(light_pos(L)), 3)
    items.append(d)
out = dict(note='v11 lights of UtilityPlane.prefab (UtilityPlaneRig.LightDefs). position: prefab space (+X right, +Y up, '
                '+Z forward); positionParked: world with ParkedPose at the origin. Intensity = 100 % level (the prefab Light.intensity '
                'overrides it). Filters are linear; coloured lamps use 6500 K at full power and redden as they dim.',
           lights=items)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print(len(items), 'lights ->', sys.argv[1])
