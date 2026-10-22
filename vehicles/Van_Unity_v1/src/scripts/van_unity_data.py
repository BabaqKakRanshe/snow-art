"""Van v3 -> Unity: the data files of the Unity package (Assets/Van/Data/*.json), all in the Unity frame.

Frame: the prefab root Van sits on the ground at the origin with identity rotation; "van space" = Unity axes
(x right, y up, z forward, metres) from that root. Body frame (x forward, y left, z up) -> van space (-y, z, x).
Every node of Van.fbx has an identity local rotation at rest, so a parent-local position is the van-space position
minus the parent's origin, and a parent-local direction is the van-space direction.

Rotations: the contract's angle stays as it is (doors open 0..70, needles from 12 o'clock, ignition 0..90 ...);
rotAxis = minus the converted axis (Unity is left-handed), so  localRotation = rest * Quaternion.AngleAxis(value, rotAxis)
gives the contract's motion. Slides / items move along dir (the converted axis, not negated); stretch scales along dir.

python3 -I van_unity_data.py -- <pkg_assets_van_dir> <export_report.json>
  -> Data/parts.json, sockets.json, colliders.json, lights.json, glass.json, seats.json, vehicle.json,
     materials.json, model_facts.json; Textures/T_Van_WipeMap.png"""
import os, sys, json, re, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'out', 'van3_contract.json')))
L = json.load(open(os.path.join(HERE, 'out', 'van3_lights.json')))['lights']
V = json.load(open(os.path.join(HERE, 'out', 'van3.json')))
MD = open(os.path.join(HERE, 'docs', 'VAN3_CONTRACT.md'), encoding='utf-8').read().splitlines()


def U(p):
    """body frame point / direction -> van space (Unity)"""
    return [round(-p[1], 5) + 0.0, round(p[2], 5) + 0.0, round(p[0], 5) + 0.0]


def Usize(s):
    return [round(abs(s[1]), 5), round(abs(s[2]), 5), round(abs(s[0]), 5)]


def neg(v):
    return [round(-x, 5) + 0.0 for x in v]


def sub(a, b):
    return [round(x - y, 5) + 0.0 for x, y in zip(a, b)]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 5) + 0.0 for x in v]


# ------------------------------------------------------------------ Russian texts of the contract (VAN3_CONTRACT.md)
DESC = {}
for l in MD:
    m = re.match(r'^\| `([^`]+)` \|', l)
    if m:
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        DESC[cells[0].strip('`')] = cells[-1]

LABEL = {   # short hover labels (the game shows them on the part); everything else: the contract text up to ':'
    'Radio_Volume': 'Рация: громкость', 'Radio_Squelch': 'Рация: шумоподавитель', 'Radio_ChDown': 'Рация: канал вниз',
    'Radio_ChUp': 'Рация: канал вверх', 'Radio_MicHook': 'Крючок тангенты', 'Radio_Mic': 'Тангента',
    'Radio_Mic_PTT': 'Кнопка «говорить»', 'Window_doorL': 'Окно двери водителя', 'Window_doorP': 'Окно двери пассажира',
    'RearMirror': 'Зеркало заднего вида', 'doorZL': 'Левая задняя дверь', 'dooZP': 'Правая задняя дверь',
    'doorSalon': 'Боковая дверь салона', 'Stove': 'Печка', 'WoodBox': 'Ящик для дров', 'Kettle': 'Чайник',
    'Battery': 'Аккумулятор', 'Ignition_Key': 'Ключ зажигания', 'FuelFiller_L': 'Горловина левого бака',
    'FuelFiller_R': 'Горловина правого бака', 'FuelTanks': 'Топливные баки', 'Jerrycan_1': 'Канистра 20 л',
    'Jerrycan_2': 'Канистра 20 л', 'ToolBox': 'Ящик с инструментом', 'Jack': 'Домкрат', 'Shovel': 'Лопата',
    'TowRope': 'Буксировочная стропа', 'Crank_Guide': 'Отверстие под рукоятку', 'CrankHole_Flap': 'Шторка отверстия под рукоятку',
    'Socket_12V_Cap': 'Крышка розетки 12 В', 'Heater_Fan': 'Вентилятор печки', 'Heater_Air': 'Заслонка печки',
    'Heater_Temp': 'Температура печки', 'Engine_Drain': 'Сливной краник', 'Exhaust': 'Выхлопная труба',
    'ChainBag': 'Сумка с цепями', 'DoorPocket_P': 'Карман двери', 'SnowBrush': 'Щётка со скребком',
    'BatteryBox': 'Ящик АКБ', 'BatteryBox_Lid': 'Крышка ящика АКБ', 'FuseBox': 'Блок предохранителей',
    'FuseBox_Lid': 'Крышка блока предохранителей', 'ToolBox_Lid': 'Крышка ящика с инструментом', 'DashControls': 'Панель',
    'TankValve': 'Кран баков', 'TankValve_Lever': 'Кран баков', 'Saloon_Hooks': 'Крюк', 'MassSwitch_Key': 'Ключ массы',
    'GearLever_Boot': 'Чехол рычага КПП', 'PedalBox': 'Педали', 'WorkLamp': 'Переноска', 'WorkLamp_Cord': 'Шнур переноски',
    'Map': 'Карта', 'SandLadder_1': 'Сэнд-трак', 'SandLadder_2': 'Сэнд-трак', 'Steer_FL': 'Поворотный кулак',
    'Steer_FR': 'Поворотный кулак', 'Stove_Damper': 'Заслонка трубы', 'EngineBay': 'Моторный отсек',
    'Lens_Torch': 'Стекло фонаря', 'Lens_WorkLamp': 'Колба переноски', 'StoveGlow': 'Огонь', 'Blowtorch': 'Паяльная лампа',
    'OilCan': 'Канистра масла 5 л', 'AntifreezeCan': 'Канистра антифриза 5 л', 'Spout': 'Лейка',
    'RadiatorHatch': 'Лючок радиатора', 'Winch_Hook': 'Крюк лебёдки', 'Glovebox_Lid': 'Бардачок',
    'Logbook': 'Путевой журнал', 'Radio_Display': 'Дисплей рации', 'RearMirror_Glass': 'Зеркало',
}


def label(n):
    if n in LABEL:
        return LABEL[n]
    if n.startswith('Curtain_'):
        return 'Шторка'
    if n.startswith('Chains_'):
        return 'Цепи противоскольжения'
    if n.startswith('Snow_'):
        return 'Снег'
    if n.startswith('Lock_'):
        return 'Кнопка блокировки'
    if n.startswith('Toggle_'):
        m = re.search(r'«[^»]+»', DESC.get(n, ''))
        return 'Тумблер ' + (m.group(0).replace(' »', '»').replace('« ', '«') if m else '')
    if n.startswith('Needle_'):
        return 'Стрелка'
    if n.startswith('Lens_Flare'):
        return 'Фальшфейер'
    if n.startswith('Lens_'):
        return 'Стекло фары'
    t = re.split(r'[:;]', DESC.get(n, n))[0]
    t = re.sub(r'\s*\(.*?\)\s*', ' ', t).strip()
    t = t.split(', ')[0] if len(t) > 32 else t
    return t[:1].upper() + t[1:]


# ------------------------------------------------------------------ interaction zones and item types
# zone kinds the game knows (InteractionSensor / ServerUse): toggle, momentary, rotary, pull, selector, lever, hinge, door,
# cap, seat, lock, stow, ladder; the van adds slot (use the item in hand here: pour, plug, insert, jack point, load the
# stove), hide (crouch / lie here) and item (a removable part you take: fuse, plug, cap, key, nut, distributor cap).
ZONE = {
    'momentary': ['Horn_Button', 'Radio_ChDown', 'Radio_ChUp', 'Radio_Mic_PTT', 'Engine_PrimerLever', 'Blowtorch_Pump'],
    'rotary': ['Radio_Volume', 'Radio_Squelch', 'Heater_Air', 'Blowtorch_Valve', 'RearMirror', 'Stove_Damper',
               'Jack_Screw'],
    'selector': ['Ignition_Key', 'MassSwitch_Key', 'TankValve_Lever', 'Heater_Fan', 'Heater_Temp', 'Engine_Drain'],
    'pull': ['Knob_Choke', 'Knob_Throttle', 'Handbrake', 'Engine_Dipstick', 'Stove_AshPan', 'StoveDoor_Vent',
             'Engine_Lead_1', 'Engine_Lead_2', 'Engine_Lead_3', 'Engine_Lead_4', 'Battery_ClampPos', 'Battery_ClampNeg'],
    'lever': ['TransferLever_Axle', 'TransferLever_Range', 'Winch_Clutch'],
    'door': ['doorL', 'doorP', 'doorSalon', 'doorZL', 'dooZP', 'EngineCover', 'RoofHatch'],
    'lock': ['Lock_doorL', 'Lock_doorP', 'Lock_doorSalon', 'Lock_doorZL', 'Lock_dooZP'],
    'slot': ['Engine_Belt'],                # fit the spare belt (Spare_Belt in hand)
}
NO_ZONE = {'SteeringWheel', 'Steer_FL', 'Steer_FR', 'GearLever', 'Pedal_Clutch', 'Pedal_Brake', 'Pedal_Gas', 'Wiper_L',
           'Wiper_R', 'Engine_Fan', 'Winch_Drum', 'Jack_Ram', 'Radio_Display', 'RearMirror_Glass', 'StoveGlow',
           'WorkLamp_Cord'}
# zones reachable only from inside / outside (the game's _In / _Out rule judges it against one interior box)
SIDE_IN = ('Toggle_', 'Radio_', 'Heater_', 'Knob_', 'Handbrake', 'Ignition', 'TransferLever', 'Lock_', 'Glovebox',
           'Socket_12V', 'FuseBox', 'Fuse_', 'MassSwitch', 'BatteryBox', 'Battery', 'Seat_', 'Curtain_', 'Stove', 'Kettle',
           'Log_', 'ToolBox', 'Tool_', 'Spare_', 'FuseTin', 'Jack', 'WheelBrace', 'OilCan', 'AntifreezeCan', 'TowRope',
           'CrankHandle', 'Blowtorch', 'ChainBag', 'WorkLamp', 'Map', 'Logbook', 'Flashlight', 'Flare_', 'TankValve',
           'EngineCover', 'Engine', 'RearMirror', 'Horn', 'Window_door', 'RoofHatch')
SIDE_OUT = ('Radiator', 'Winch', 'CrankHole', 'FuelFlap', 'FuelCap', 'SandLadder', 'Jerrycan', 'Spout', 'Shovel',
            'Wheel_', 'SpareWheel', 'Snow_', 'Chains_')
ITEM_TYPE = [   # (type, parts regex, label, kg, hands, extra)
    ('Wheel', r'SpareWheel$|Wheel_(FL|FR|RL|RR)$', 'Колесо', 31.0, 2, {}),
    ('WheelNut', r'Wheel_(FL|FR|RL|RR)_Nut_\d$', 'Гайка колеса', 0.08, 1, {}),
    ('WingNut', r'SpareWheel_Nut$', 'Барашек запаски', 0.15, 1, {}),
    ('SandLadder', r'SandLadder_\d$', 'Сэнд-трак', 3.2, 1, {}),
    ('WinchHook', r'Winch_Hook$', 'Крюк лебёдки', 0.8, 1, dict(tether='cable', tetherFrom='Winch_Fairlead', tetherM=25.0)),
    ('WorkLamp', r'WorkLamp$', 'Переноска', 0.7, 1, dict(tether='cord', tetherFrom='Plug_12V', tetherM=5.0, lamp='WorkLamp')),
    ('Map', r'Map$', 'Карта', 0.05, 1, dict(readable='van_map')),
    ('Logbook', r'Logbook$', 'Путевой журнал', 0.25, 1, dict(readable='van_logbook')),
    ('Flashlight', r'Flashlight$', 'Фонарь', 0.45, 1, dict(lamp='Torch')),
    ('Flare', r'Flare_\d$', 'Фальшфейер', 0.25, 1, dict(lamp='Flare_N')),
    ('RadioMic', r'Radio_Mic$', 'Тангента', 0.2, 1, dict(tether='cord', tetherFrom='Radio_Cord_Radio', tetherM=1.2)),
    ('Kettle', r'Kettle$', 'Чайник', 0.8, 1, dict(capacityL=1.5, contents='water')),
    ('Log', r'Log_\d$', 'Полено', 1.2, 1, {}),
    ('DistributorCap', r'Engine_DistributorCap$', 'Крышка трамблёра', 0.3, 1, {}),
    ('SparkPlug', r'Engine_Plug_\d$', 'Свеча', 0.06, 1, {}),
    ('Battery', r'Battery$', 'Аккумулятор', 18.0, 2, dict(charge=True)),
    ('Fuse', r'(Spare_)?Fuse_\d$', 'Предохранитель', 0.005, 1, {}),
    ('Jerrycan', r'Jerrycan_\d$', 'Канистра 20 л', 3.6, 1, dict(capacityL=20.0, contents='petrol', densityKgL=0.74)),
    ('Spout', r'Spout$', 'Лейка', 0.4, 1, {}),
    ('ToolBox', r'ToolBox$', 'Ящик с инструментом', 3.0, 1, {}),
    ('Wrench', r'Tool_Wrench$', 'Ключ 13/17', 0.35, 1, {}),
    ('PlugSpanner', r'Tool_PlugSpanner$', 'Свечной ключ', 0.3, 1, {}),
    ('Screwdriver', r'Tool_Screwdriver$', 'Отвёртка', 0.15, 1, {}),
    ('Pliers', r'Tool_Pliers$', 'Пассатижи', 0.3, 1, {}),
    ('FanBelt', r'Spare_Belt$', 'Запасной ремень', 0.25, 1, {}),
    ('FuseTin', r'FuseTin$', 'Жестянка с предохранителями', 0.1, 1, {}),
    ('Jack', r'Jack$', 'Домкрат', 4.5, 1, {}),
    ('WheelBrace', r'WheelBrace$', 'Баллонный ключ', 1.2, 1, {}),
    ('OilCan', r'OilCan$', 'Канистра масла 5 л', 0.5, 1, dict(capacityL=5.0, contents='oil', densityKgL=0.9)),
    ('AntifreezeCan', r'AntifreezeCan$', 'Канистра антифриза 5 л', 0.5, 1, dict(capacityL=5.0, contents='antifreeze',
                                                                                densityKgL=1.07)),
    ('Shovel', r'Shovel$', 'Лопата', 1.6, 1, {}),
    ('TowRope', r'TowRope$', 'Буксировочная стропа', 2.2, 1, {}),
    ('CrankHandle', r'CrankHandle$', 'Заводная рукоятка', 1.8, 1, {}),
    ('Blowtorch', r'Blowtorch$', 'Паяльная лампа', 1.6, 1, dict(capacityL=0.75, contents='petrol', densityKgL=0.74)),
    ('ChainBag', r'ChainBag$', 'Сумка с цепями', 1.0, 2, dict(chainsKg=12.0)),
    ('SnowBrush', r'SnowBrush$', 'Щётка со скребком', 0.3, 1, {}),
    ('RadiatorCap', r'Radiator_Cap$', 'Пробка радиатора', 0.15, 1, {}),
    ('FuelCap', r'FuelCap_(L|R)$', 'Крышка бака', 0.2, 1, {}),
    ('OilFillerCap', r'Engine_OilCap$', 'Крышка маслозаливной горловины', 0.05, 1, {}),
    ('CoolantCap', r'Engine_CoolantCap$', 'Крышка расширительного бачка', 0.05, 1, {}),
    ('AirFilterLid', r'Engine_AirFilterLid$', 'Крышка воздушного фильтра', 0.6, 1, {}),
    ('IgnitionKey', r'Ignition_Key$', 'Ключ зажигания', 0.02, 1, {}),
    ('MassKey', r'MassSwitch_Key$', 'Ключ массы', 0.03, 1, {}),
]


def item_type(name):
    for t, rx, *_ in ITEM_TYPE:
        if re.fullmatch(rx, name):
            return t
    return ''


def zone_kind(name, p):
    """the zone the setup puts on the part (IV_<part>); '' = none"""
    if name in NO_ZONE or re.fullmatch(r'Seat_[LR]\d_Leg', name):
        return ''
    for k, names in ZONE.items():
        if name in names:
            return k
    if name.startswith('Toggle_'):
        return 'toggle'
    if name.startswith('Snow_'):
        return 'slot'                       # brush it off (SnowBrush in hand)
    if name.startswith('Needle_') or p['kind'] == 'static':
        return ''
    if p['kind'] == 'item':
        return 'cap' if p.get('range') else 'stow'      # spark plugs unscrew along their axis; the rest sit in a stow place
    if p['kind'] == 'twist':
        return 'cap' if p.get('removable') in ('end', 'start') else 'rotary'
    if p['kind'] == 'spin':
        return 'item' if name.startswith('Wheel_') else ''
    return 'hinge'                          # hinges, slides, curtains


def anc_has(name, node):
    p = C['parts'].get(name)
    while p is not None and p.get('parent'):
        if p['parent'] == node:
            return True
        p = C['parts'].get(p['parent'])
    return False


def zone_side(name):
    if name.startswith(SIDE_IN):
        return 'in'
    if name.startswith(SIDE_OUT):
        return 'out'
    return 'both'


def main(pkg, report_path):
    D = os.path.join(pkg, 'Data')
    T = os.path.join(pkg, 'Textures')
    os.makedirs(D, exist_ok=True)
    os.makedirs(T, exist_ok=True)
    rep = json.load(open(report_path))
    NODES = {n['name']: n for n in rep['nodes']}
    origin = {n: NODES[n]['origin_unity'] for n in NODES}
    origin[''] = [0.0, 0.0, 0.0]

    def local(node, p_van):
        return sub(p_van, origin[node])

    P, S = C['parts'], C['sockets']
    # ------------------------------------------------------------------ parts
    parts = []
    for name, p in P.items():
        assert name in NODES, name
        node = NODES[name]
        parent = node['parent']
        assert parent == p['parent'], (name, parent, p['parent'])
        piv = U(p['pivot'])
        assert max(abs(a - b) for a, b in zip(piv, node['origin_unity'])) < 2e-3, (name, piv, node['origin_unity'])
        e = dict(name=name, kind=p['kind'], parent=parent, label=label(name), note=p.get('note', ''),
                 descRu=DESC.get(name, ''), pivot=node['origin_unity'], pivotLocal=local(parent, node['origin_unity']),
                 unit=p['unit'], rest=p['rest'], hasRange=bool(p.get('range')),
                 min=(p['range'][0] if p.get('range') else 0.0), max=(p['range'][1] if p.get('range') else 0.0),
                 removable=(p.get('removable') or ''), states=p.get('states') or [],
                 defaultHidden=p.get('default') == 'hidden', zoneKind=zone_kind(name, p), zoneSide=zone_side(name),
                 itemType=item_type(name))
        ax = p.get('axis')
        e['hasAxis'] = ax is not None
        e['dir'] = norm(U(ax)) if ax else [0.0, 0.0, 0.0]
        e['rotAxis'] = neg(e['dir']) if ax else [0.0, 0.0, 0.0]
        b = p.get('box')
        e['hasBox'] = b is not None
        e['boxCenter'] = U(b['center']) if b else [0.0, 0.0, 0.0]
        e['boxSize'] = Usize(b['size']) if b else [0.0, 0.0, 0.0]
        e['controls'] = p.get('controls', [])
        e['fuse'] = p.get('fuse', '')
        e['dims'] = p.get('dims', '')
        sc = p.get('scale')
        e['hasScale'] = sc is not None
        e['scaleMin'], e['scaleMax'] = (sc['min'], sc['max']) if sc else (0.0, 0.0)
        e['angleMin'], e['angleMax'] = (sc['angle_min'], sc['angle_max']) if sc else (0.0, 0.0)
        e['scaleUnit'] = sc['unit'] if sc else ''
        w = p.get('wheel')
        e['hasWheel'] = w is not None
        e['wheelRadius'] = w['radius'] if w else 0.0
        e['wheelWidth'] = w['width'] if w else 0.0
        e['suspensionTravel'] = w['suspension_travel'] if w else 0.0
        e['steer'] = bool(w and w['steer'])
        e['driven'] = bool(w and w['driven'])
        e['side'] = w['side'] if w else ''
        e['flatBlendshape'] = (w.get('flat_blendshape') or '') if w else ''
        lk = p.get('links')
        e['linkFrom'] = lk['from'] if lk else ''
        e['linkRatio'] = lk['ratio'] if lk else 0.0
        e['blendshape'] = p.get('blendshape', '')
        e['gears'] = []
        if name == 'GearLever':
            # states 'N (0, 0)', '1 (-8, -12)', ... 'R (-14, -12, lift)': (side deg about body +x, fore-aft deg about +y)
            for s in p['states']:
                m = re.match(r'(\w+) \(([-+\d.]+), ([-+\d.]+)(, lift)?\)', s)
                e['gears'].append(dict(name=m.group(1), sideDeg=float(m.group(2)), foreAftDeg=float(m.group(3)),
                                       lift=0.01 if m.group(4) else 0.0))
            e['hasAxis'] = True
            e['dir'] = U([0, 1, 0])                                     # fore-aft: about body +y
            e['rotAxis'] = neg(e['dir'])
            e['dir2'] = U([1, 0, 0])                                    # side: about body +x
            e['rotAxis2'] = neg(e['dir2'])
            e['liftDir'] = U([0, 0, 1])
        for k in ('dir2', 'rotAxis2', 'liftDir'):
            e.setdefault(k, [0.0, 0.0, 0.0])
        parts.append(e)
    names = {e['name'] for e in parts}
    # ------------------------------------------------------------------ sockets
    socks = []
    panes = {p['name']: p for p in rep['panes']}
    for name, s in S.items():
        parent = s['parent'] or ''
        if parent and parent not in NODES:
            raise RuntimeError(name)
        pv = U(s['pos'])
        e = dict(name=name, kind=s['kind'], parent=parent, note=s.get('note', ''), position=pv,
                 positionLocal=local(parent, pv), hasDir='dir' in s, dir=norm(U(s['dir'])) if 'dir' in s else [0.0, 0.0, 0.0],
                 hasUp='up' in s, up=norm(U(s['up'])) if 'up' in s else [0.0, 0.0, 0.0],
                 hasEye='eye' in s, eye=U(s['eye']) if 'eye' in s else [0.0, 0.0, 0.0],
                 hasFacing='facing' in s, facing=norm(U(s['facing'])) if 'facing' in s else [0.0, 0.0, 0.0],
                 hasExit='exit' in s, exit=U(s['exit']) if 'exit' in s else [0.0, 0.0, 0.0],
                 door=s.get('door', ''), pose=s.get('pose', ''), exitNote=s.get('exit_note', ''), fov=s.get('fov', 0.0),
                 pane='')
        if s['kind'] == 'decal':
            # the pane this hand print goes on: the nearest pane centre (body frame), lob for the windscreen
            if name == 'Handprint_lob':
                e['pane'] = 'lob'
            else:
                best = min(panes.values(), key=lambda q: sum((a - b) ** 2 for a, b in zip(q['centre_body'], s['pos'])))
                e['pane'] = best['name']
        socks.append(e)
    assert not names & {s['name'] for s in socks}
    # ------------------------------------------------------------------ colliders (BoxCollider on its parent node)
    cols = []
    for c in C['colliders']:
        par = c['parent']
        assert par in NODES, c['name']
        cv = U(c['center_body'])
        cols.append(dict(name=c['name'], parent=par, center=local(par, cv), centerVan=cv, size=Usize(c['size']),
                         group=('door' if par.startswith(('door', 'dooZ')) else
                                'roof' if par.startswith('Kit_Roof') or 'Roof' in c['name'] else
                                'front' if par == 'Kit_Front' else
                                'underbody' if c['name'] in ('COL_Underbody', 'COL_Tanks', 'COL_BumperR') else 'body')))
    # ------------------------------------------------------------------ lights
    TOGGLE, FUSE = {}, {}
    for n, p in P.items():
        for lamp in p.get('controls', []):
            TOGGLE[lamp] = n
            FUSE[lamp] = p.get('fuse', '')
    WATT = dict(head=55, spot=55, fog=55, work=55, marker=5, tail=5, plate=5, amber=21, reverse=21, dome=10, night=2,
                flood=3, pendant=15, hand=21, torch=0, flare=0, stove=0)
    FLICKER = dict(amber='flasher', flare='flare', stove='fire')
    SHADOW_PRIO = dict(head=1, torch=1, spot=2, work=2, dome=2, pendant=2, hand=2, fog=3, flare=3, stove=3)
    GLOW = {'head', 'spot', 'fog', 'work', 'marker', 'tail', 'amber', 'reverse', 'plate', 'flare', 'torch', 'hand'}
    BEAM = {'head', 'spot', 'fog', 'torch', 'work'}
    OWN_POWER = {'torch', 'flare', 'stove'}                     # not on the van's bus
    lights = []
    for l in L:
        key = l['socket'][len('LIGHT_'):]
        lens = l['lens']
        if lens and lens in NODES:
            parent = NODES[lens]['parent']
        elif key == 'Dash_Flood':
            parent = 'Dash'
        else:
            raise RuntimeError(key)
        pv = [round(x, 5) + 0.0 for x in l['positionUnity']]
        e = dict(name=key, light='Light_' + key, type=l['type'], group=l['group'], toggle=TOGGLE.get(key, ''),
                 fuse=FUSE.get(key, ''), parent=parent, lens=lens if lens in NODES else '',
                 position=pv, positionLocal=local(parent, pv), forward=norm(l['forwardUnity']), up=norm(l['upUnity']),
                 unityLight=l['unityLight'], intensity=l['intensityURP'], peakCandela=l['peakCandela'], kelvin=l['kelvin'],
                 filter=l['filterLinear'], range=l['range'], spotOuter=l.get('spotOuter', 0), spotInner=l.get('spotInner', 0),
                 cookie=l.get('cookie') or '', ies=os.path.basename(l['ies']), shadows=bool(l['shadows']),
                 shadowPriority=SHADOW_PRIO.get(l['type'], 9) if l['shadows'] else 0,
                 watts=WATT[l['type']], ownPower=l['type'] in OWN_POWER, flicker=FLICKER.get(l['type'], 'filament'),
                 glow=l['type'] in GLOW, beam=l['type'] in BEAM, desc=l['desc'],
                 dimmedBy=next((n for n, p in P.items() if p.get('dims') == key), ''))
        lights.append(e)
    # ------------------------------------------------------------------ glass panes
    hp = {s['pane']: s['name'] for s in socks if s['kind'] == 'decal'}
    pane_list = []
    for pn in ['lob'] + [p['name'] for p in rep['panes']]:
        n = NODES[pn]
        host = n['parent'] if pn != 'lob' else ''
        lo, hi = n['bounds_body']
        cen = U([(a + b) / 2 for a, b in zip(lo, hi)])
        mat = n['materials'][0]
        side = 'front' if pn == 'lob' else ('left' if (lo[1] + hi[1]) > 0 else 'right')
        if pn in ('Glass_ZL', 'Glass_ZP'):
            side = 'rear'
        fit = rep['lob_fit'] if pn == 'lob' else next(p['uv_affine'] for p in rep['panes'] if p['name'] == pn)
        pane_list.append(dict(name=pn, host=host, material=mat, cab=mat == 'M_PSX_Glass_Cab', side=side,
                              centre=cen, maskUv=1, frost=pn == 'lob', snow=pn == 'lob',
                              fog=True, wipers=pn == 'lob', handprint=hp.get(pn, ''), uvU=fit['u'], uvV=fit['v'],
                              uvFitError=fit['max_err']))
    glass = dict(note='Panes of glass: one renderer each (lob = the windscreen). Masks on UV1 for every pane (side / rear '
                      'panes: FOG, 0..1 per pane; lob: a copy of its own 0..1 UVs). uvU / uvV: uv = (dot(uvU.xyz, p) + uvU.w, '
                      'dot(uvV.xyz, p) + uvV.w), p = the point in the pane\'s local frame (metres): where a palm or a ray '
                      'meets the pane. Masks (alpha = '
                      'when the texel freezes / snows over / fogs up; shown if alpha > 1 - amount): T_Van_Frost and '
                      'T_Van_Snow (lob), T_Van_Fog (FOG panes); T_Van_Handprints: 2 x 2 atlas of hand prints (alpha); '
                      'T_Van_WipeMap (lob UV0): R = Wiper_L angle / 100 at which its blade passes the texel, G = Wiper_R, '
                      '1 = never.',
                 panes=pane_list, frostMask='T_Van_Frost', snowMask='T_Van_Snow', fogMask='T_Van_Fog',
                 handprints='T_Van_Handprints', wipeMap='T_Van_WipeMap', mirror='RearMirror_Glass', mirrorCamera='MirrorCam',
                 radioDisplay='Radio_Display')
    # ------------------------------------------------------------------ seats
    seats = []
    for s in socks:
        if s['kind'] != 'sit':
            continue
        n = s['name'][4:]
        role = 'Driver' if n == 'Driver' else 'Passenger' if n == 'Passenger' else 'Saloon'
        seats.append(dict(name=s['name'], seat=n, role=role, parent=s['parent'], hip=s['position'], hipLocal=s['positionLocal'],
                          eye=s['eye'], facing=s['facing'], exit=s['exit'], door=s['door'], exitNote=s['exitNote'],
                          foldPart=('Seat_' + n) if role == 'Saloon' else '', legPart=('Seat_' + n + '_Leg') if role == 'Saloon' else '',
                          drives=role == 'Driver'))
    # ------------------------------------------------------------------ interaction zones (IV_<id>: trigger boxes, layer Interact)
    LAB_SOCK = {'Pour_Radiator': 'Радиатор (залить)', 'Pour_Oil': 'Масло (залить)', 'Pour_Coolant': 'Бачок (залить)',
                'Pour_Fuel_L': 'Горловина левого бака', 'Pour_Fuel_R': 'Горловина правого бака',
                'Hook_Radio_Mic': 'Крючок тангенты', 'Tow_Hook_FL': 'Буксирный крюк', 'Tow_Hook_FR': 'Буксирный крюк',
                'Tow_Rear': 'Буксирная проушина', 'Crank_Hole': 'Отверстие под рукоятку', 'Plug_12V': 'Розетка 12 В',
                'Stove_Load': 'Топка', 'Heat_OilPan': 'Поддон двигателя (греть)',
                'Jack_PumpSocket': 'Домкрат: качать баллонным ключом'}
    ZS = {'pour': (0.10, 0.10, 0.10), 'item_slot': (0.10, 0.10, 0.10), 'jack': (0.30, 0.20, 0.30), 'heat': (0.30, 0.20, 0.30),
          'hide': (0.50, 0.50, 0.50), 'sit': (0.50, 0.55, 0.50)}
    SOCK_ZONES = set(LAB_SOCK) | {n for n, s_ in S.items() if s_['kind'] in ('jack', 'hide', 'sit')}
    zones = []
    MINZ = 0.02

    def hideable(e):
        # the rig hides these (SetVisible false: taken, unscrewed, removed): their zone must stay to put them back
        return e['kind'] == 'item' or e['removable'] in ('start', 'end') or (e['kind'] == 'spin' and e['name'].startswith('Wheel_'))

    for e in parts:
        if not e['zoneKind']:
            continue
        if not e['hasBox']:
            if not (e['name'].startswith('Snow_') or e['name'] == 'Engine_Belt'):
                continue
            # snow layers (roof, visor, bumper) and the fan belt have no part box: their bounds (+ 3 cm all round)
            lo, hi = NODES[e['name']]['bounds_body']
            cv = U([(a + b) / 2 for a, b in zip(lo, hi)])
            size = [max(0.06, v + 0.06) for v in Usize([b - a for a, b in zip(lo, hi)])]
            # the belt is hidden when it breaks: its zone sits on the engine to fit the spare one
            par = e['parent'] if e['name'] == 'Engine_Belt' else e['name']
            zones.append(dict(id=e['name'], kind=e['zoneKind'], side=e['zoneSide'], label=e['label'], parent=par,
                              center=local(par, cv), size=size, part=e['name'], socket='', itemType='', pane=''))
            continue
        size = [max(MINZ, v) for v in e['boxSize']]
        if hideable(e):
            par, c = e['parent'], [a + b for a, b in zip(e['pivotLocal'], e['boxCenter'])]
        else:
            par, c = e['name'], e['boxCenter']
        zones.append(dict(id=e['name'], kind=e['zoneKind'], side=e['zoneSide'], label=e['label'], parent=par,
                          center=c, size=size, part=e['name'], socket='', itemType=e['itemType'], pane=''))
    for tool, lab in (('Jack', 'Забрать домкрат'), ('Blowtorch', 'Забрать паяльную лампу')):
        e = next(x for x in parts if x['name'] == tool)
        zones.append(dict(id=tool + '_Take', kind='item', side='both', label=lab, parent=tool, center=e['boxCenter'],
                          size=[max(MINZ, v) for v in e['boxSize']], part=tool, socket='', itemType=e['itemType'], pane=''))
    for s_ in socks:
        if s_['name'] not in SOCK_ZONES:
            continue
        sz = list(ZS[s_['kind']])
        c = list(s_['positionLocal'])
        if s_['kind'] == 'sit':
            c[1] += 0.2                                   # around the seated body, above the seat point
        kind = {'sit': 'seat', 'hide': 'hide'}.get(s_['kind'], 'slot')
        # the oil filler and the coolant tank are under the engine cover between the cab seats: reached from inside
        side = 'in' if s_['kind'] in ('sit', 'hide') or s_['name'] in ('Stove_Load', 'Hook_Radio_Mic', 'Plug_12V', 'Pour_Oil',
                                                                       'Pour_Coolant') else 'out'
        if s_['name'] == 'Jack_PumpSocket':
            side = 'both'                                 # the jack works where it stands (under the van: outside)
        lab = LAB_SOCK.get(s_['name']) or {'jack': 'Под домкрат', 'hide': 'Спрятаться', 'sit': 'Сесть'}[s_['kind']]
        zones.append(dict(id=s_['name'], kind=kind, side=side, label=lab, parent=s_['parent'], center=c, size=sz, part='',
                          socket=s_['name'], itemType='', pane=''))
    for pn in pane_list:
        n = NODES[pn['name']]
        lo, hi = n['bounds_body']
        cv = U([(a + b) / 2 for a, b in zip(lo, hi)])
        sz = [max(0.02, v + 0.02) for v in Usize([b - a for a, b in zip(lo, hi)])]
        par = pn['name']
        zones.append(dict(id='Glass_' + pn['name'] if not pn['name'].startswith('Glass_') else pn['name'], kind='slot',
                          side='both', label='Стекло', parent=par, center=local(par, cv), size=sz, part='', socket='',
                          itemType='', pane=pn['name']))
    lad = next(c for c in cols if c['name'] == 'COL_Ladder')
    zones.append(dict(id='Ladder_doorZL', kind='ladder', side='out', label='Лестница на багажник', parent=lad['parent'],
                      center=lad['center'], size=[lad['size'][0] + 0.2, lad['size'][1] + 0.3, lad['size'][2] + 0.2],
                      part='doorZL', socket='', itemType='', pane=''))
    ids = [z['id'] for z in zones]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    COVER = {'FuelFlap_L': ['FuelCap_L', 'Pour_Fuel_L'], 'FuelFlap_R': ['FuelCap_R', 'Pour_Fuel_R'],
             'RadiatorHatch': ['Radiator_Cap', 'Pour_Radiator'], 'FuseBox_Lid': ['Fuse_%d' % i for i in range(1, 9)],
             'BatteryBox_Lid': ['Battery', 'Battery_ClampPos', 'Battery_ClampNeg'], 'Seat_L4': ['BatteryBox_Lid'],
             'ToolBox_Lid': ['Tool_Wrench', 'Tool_PlugSpanner', 'Tool_Screwdriver', 'Tool_Pliers', 'Spare_Belt', 'FuseTin',
                             'Spare_Fuse_1', 'Spare_Fuse_2', 'Spare_Fuse_3'],
             'Glovebox_Lid': ['Map', 'Logbook', 'Flashlight', 'Flare_1', 'Flare_2', 'Flare_3'],
             'Socket_12V_Cap': ['Plug_12V'], 'CrankHole_Flap': ['Crank_Hole'], 'StoveDoor': ['Stove_Load'],
             'EngineCover': [n for n in P if anc_has(n, 'Engine')] + ['Pour_Oil', 'Pour_Coolant']}
    covered = {z: c for c, zs in COVER.items() for z in zs}
    for z in zones:
        z['coveredBy'] = covered.get(z['id'], '')
    zid = {z['id'] for z in zones}
    assert all(c in zid for c in COVER) and all(z in zid for z in covered if z not in ('Engine_Fan',)), \
        [x for x in list(COVER) + list(covered) if x not in zid]
    # zones inside other zones at rest (van space, all boxes axis-aligned): insideOf = the smallest one around it.
    # The game's sensor takes the first zone the ray enters, so the inner zone needs a rule (VAN3_INTEGRATION_UNITY.md 3.3)
    box = {}
    for z in zones:
        c = [o + v for o, v in zip(origin[z['parent']], z['center'])]
        box[z['id']] = ([a - b / 2 for a, b in zip(c, z['size'])], [a + b / 2 for a, b in zip(c, z['size'])])
    vol = {k: (h[0] - l[0]) * (h[1] - l[1]) * (h[2] - l[2]) for k, (l, h) in box.items()}
    for z in zones:
        l, h = box[z['id']]
        outer = [k for k, (L, H) in box.items() if k != z['id'] and vol[k] > vol[z['id']]
                 and all(L[i] <= l[i] + 1e-3 and h[i] <= H[i] + 1e-3 for i in range(3))]
        z['insideOf'] = min(outer, key=lambda k: vol[k]) if outer else ''
    # ------------------------------------------------------------------ item types and the stow places of the kit
    types = []
    for t, rx, lab, kg, hands, extra in ITEM_TYPE:
        members = [e['name'] for e in parts if e['itemType'] == t]
        assert members, t
        src = members[0] if t != 'Wheel' else 'SpareWheel'
        types.append(dict(type=t, label=lab, massKg=kg, hands=hands, prefab='VanItem_' + t, sourcePart=src, parts=members,
                          tether=extra.get('tether', ''), tetherFrom=extra.get('tetherFrom', ''), tetherM=extra.get('tetherM', 0.0),
                          lamp=extra.get('lamp', ''), readable=extra.get('readable', ''), capacityL=extra.get('capacityL', 0.0),
                          contents=extra.get('contents', ''), densityKgL=extra.get('densityKgL', 0.0),
                          charge=extra.get('charge', False), chainsKg=extra.get('chainsKg', 0.0)))
    stows = [dict(stowId=e['name'], parent=e['parent'], position=e['pivotLocal'], accepts=e['itemType'], part=e['name'])
             for e in parts if e['zoneKind'] == 'stow']

    # ------------------------------------------------------------------ write
    def dump(fn, obj):
        json.dump(obj, open(os.path.join(D, fn), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    FRAME = ('van space = Unity frame of the prefab root Van (x right, y up, z forward, metres, ground y = 0); '
             'body frame of VAN3_CONTRACT.md (x forward, y left, z up) -> (-y, z, x). Every part has an identity local '
             'rotation at rest: parent-local = van space - parent origin.')
    dump('parts.json', dict(version=1, frame=FRAME,
                            rules='hinge / twist / spin: localRotation = rest * Quaternion.AngleAxis(value, rotAxis) (value in '
                                  'the contract units and sense: degrees, + as described; rotAxis already flipped for the '
                                  'left-handed frame). slide (and the pull-out travel of an item with a range): localPosition = '
                                  'restPosition + dir * value (metres). stretch: scale along dir from the pivot, value = '
                                  'the scale (x). GearLever: rotAxis = fore-aft (about body +y), rotAxis2 = side (about body '
                                  '+x), lift along liftDir; gears = the H pattern. Needles: angle(value) = lerp(angleMin, '
                                  'angleMax, (value - scaleMin) / (scaleMax - scaleMin)); turn by angle - rest. box: grab / '
                                  'hit box in the part frame (BoxCollider.center / size on the part).',
                            parts=parts))
    dump('sockets.json', dict(version=1, frame=FRAME, sockets=socks))
    dump('colliders.json', dict(version=1, frame=FRAME,
                                note='BoxCollider per entry on its parent node (center / size in the parent frame). The '
                                     'body is a hollow box for riding inside: floor, walls, roof around the vent hatch, '
                                     'partition, arches, seats, table, stove, boxes; outside bumpers, underbody, tanks; '
                                     'the roof rack deck with a cut-out over the hatch, its light bar and load. Doors and '
                                     'the ladder ride on their doors. Items have no collider here: while stowed they get a '
                                     'kinematic one from their part box. Wheels: your wheel model (Data/vehicle.json).',
                                colliders=cols))
    dump('lights.json', dict(version=1, frame=FRAME,
                             note='41 lamps. Light_<name> under its parent node at positionLocal, looking along forward with '
                                  'up (LookRotation). intensity: URP units at 100 % (E = I / d^2), peakCandela: the IES peak. '
                                  'Spot lights carry the cookie made from the same emission diagram as IES/<ies> (the shape '
                                  'of the IES profile inside the cone); point lights no cookie. toggle / fuse: the switch '
                                  'and fuse of the circuit (empty: turn -> the flasher, reverse -> gear R, hand -> the '
                                  'WorkLamp item on Plug_12V, torch -> Flashlight, flare -> Flare_N, fire -> the stove). '
                                  'ownPower: not on the van bus. lens: the renderer that glows with the lamp. dimmedBy: the '
                                  'snow part over the lamp (light x (1 - 0.85 x snow)). watts: draw at 12 V (load on the '
                                  'battery). Tail lamps double as brake lamps (x4).',
                             lights=lights))
    dump('glass.json', glass)
    dump('zones.json', dict(version=1, frame=FRAME,
                            note='Interaction zones the setup builds: IV_<id> under <parent>, trigger BoxCollider (center / size in '
                                 'the parent frame), layer Interact, VanInteractable {id, kind, side, label, part, socket, '
                                 'itemType}. kind: the game\'s (toggle, momentary, rotary, selector, pull, lever, hinge, door, cap, '
                                 'lock, seat, ladder, stow) + the van\'s: slot (use the item in hand here: pour, plug, insert, '
                                 'tow, jack point, the stove, brush snow / wipe a pane), hide (crouch / lie here), item (a road '
                                 'wheel to take off once its nuts are off). side: in / out / both - the _In / _Out rule '
                                 '(interior box in model_facts.json). Parts smaller than 2 cm get a 2 cm box.',
                            zones=zones))
    dump('items.json', dict(version=1, frame=FRAME,
                            note='Item types of the van kit. Prefabs/Items/VanItem_<type>.prefab: the source part (and its '
                                 'children) at the origin, a BoxCollider from its part box - no Rigidbody / network: the game '
                                 'makes its network variant (NetItem recipe). parts: every part of this type in the model '
                                 '(stowed in the van, or screwed on: caps, nuts, keys, plugs, wheels). massKg: empty; with '
                                 'capacityL x densityKgL of contents when full. tether: the item stays on a cord / cable of '
                                 'tetherM metres from the socket tetherFrom. lamp: the lamp of lights.json that travels with it.',
                            types=types, stows=stows))
    dump('seats.json', dict(version=1, frame=FRAME,
                            note='Sit_Driver drives; Sit_Passenger and the six saloon troop seats (must be down: foldPart = 0) '
                                 'ride. hip = seat point, eye = eyes of a seated player, facing = look direction, exit = '
                                 'where the player appears outside (cab seats, on the ground by the door) or stands up '
                                 'crouched inside (saloon: the saloon is 1.22-1.27 m high, nobody stands upright).',
                            seats=seats))
    # ------------------------------------------------------------------ vehicle parameters (TEMPORARY, for tuning)
    wheels = []
    for wn in ('Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR'):
        p = P[wn]
        wheels.append(dict(name=wn, steerNode=('Steer_' + wn[-2:]) if p['wheel']['steer'] else '', centre=U(p['pivot']),
                           radius=p['wheel']['radius'], width=p['wheel']['width'], travel=p['wheel']['suspension_travel'],
                           steer=p['wheel']['steer'], driven=p['wheel']['driven'], flat=p['wheel'].get('flat_blendshape') or '',
                           nuts=[f'{wn}_Nut_{i}' for i in range(1, 7)], chains='Chains_' + wn[-2:],
                           jackPoint='Jack_Point_' + wn[-2:]))
    veh = dict(version=1, status='TEMPORARY: starting values for tuning on the bench (real UAZ-452 figures where known)',
               massKg=1950.0, massNote='UAZ-452 curb ~1720 kg + kit (stove, winch, rack, load, tools) ~230 kg; fuel adds 0.74 kg/l',
               centreOfMass=U([0.15, 0.0, 0.88]), inertiaNote='let Unity compute from the colliders, then scale the tensor '
                                                               'x1.0 (bench)',
               wheels=wheels, wheelbase=round(P['Wheel_FL']['pivot'][0] - P['Wheel_RL']['pivot'][0], 4),
               track=round(P['Wheel_FL']['pivot'][1] - P['Wheel_FR']['pivot'][1], 4),
               steeringRatio=16.875, steeringWheelMaxDeg=540.0, maxSteerDeg=32.0,
               springRate=42000.0, damperBump=3500.0, damperRebound=5000.0, suspensionTravel=0.10, antiRollNote='solid axles',
               engine=dict(name='UMZ-451M 2.445 l', idleRpm=600.0, maxRpm=4000.0, redlineRpm=4200.0, stallRpm=350.0,
                           torqueRpm=[600, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4300],
                           torqueNm=[118, 140, 158, 165, 167, 162, 152, 135, 110],
                           inertia=0.18, frictionNm=18.0, crankRpmStarter=180.0, crankRpmHandle=90.0, startRpm=70.0,
                           fuelIdleLph=1.2, fuelFullLph=19.0, chokeRichness='cold start needs choke below 10 C'),
               gearbox=dict(type='automatic logic over the 4-speed UAZ box (INPUT-01: no manual clutch / shifting)',
                            ratios=[4.124, 2.641, 1.58, 1.0], reverse=5.224, shiftUpRpm=3000.0, shiftUpFloorFactor=0.8,
                            shiftDownRpm=1300.0, shiftTime=0.6, shiftLockout=1.2,
                            shiftNote='up at shiftUpRpm x (0.8 + 0.2 x gas) = 2400..3000 rpm: after the shift the rpm stays '
                                      'above shiftDownRpm (ratio steps 0.60..0.64); no shift for shiftLockout s after one'),
               transfer=dict(high=1.0, low=1.94, frontAxleDefault=False), finalDrive=5.125,
               brakes=dict(maxTorqueFrontNm=2600.0, maxTorqueRearNm=1700.0, handbrakeNm=1400.0, handbrakeOn='transmission drum'),
               tyres=dict(rollingResistance=0.015, muPeakAsphaltSnow=0.45, muPackedSnow=0.32, muLooseSnow=0.22, muIce=0.10,
                          chainsBonusSnow=0.12, chainsBonusIce=0.18, deepSnowDragPerM=2500.0, flatMuFactor=0.6),
               electrics=dict(batteryAh=60.0, batteryOcvFull=12.7, batteryOcvEmpty=11.6, batteryRintOhm=0.006,
                              coldRintFactorAtMinus20=1.5, alternatorAmps=40.0, alternatorCutInRpm=900.0, regulatorVolts=14.2,
                              starterOhm=0.045, starterClickBelowVolts=8.0, crankVolts=[8.0, 9.5, 11.0], crankRpm=[0.0, 120.0, 180.0],
                              starterNote='starter current = OCV / (R_batt x cold factor + starterOhm), ~220 A; the bus under it '
                                          '= OCV - I x R_batt; below starterClickBelowVolts the relay only clicks',
                              kneeCharge=0.2, ocvDropBelowKneePerUnit=9.0, rintRiseBelowKneePerUnit=30.0,
                              kneeNote='charge q below kneeCharge: OCV = OCV(knee) - 9 x (knee - q), R_batt x (1 + 30 x (knee - q)); '
                                       'so at -10 C the starter turns at 22 % (~10 V) and only clicks at 7 % (~5.6 V)',
                              ignitionAmps=4.0, sparkMinVolts=6.5,
                              lampWatts=[dict(type=k, watts=v) for k, v in WATT.items()], heaterFanWatts=[0, 25, 45, 70], wiperWatts=35.0,
                              radioWatts=15.0),
               fuel=dict(tankLitres=56.0, tankDefaultLitres=[18.0, 0.0], jerrycanLitres=20.0, pourLitresPerMin=12.0,
                         carbBowlLitres=0.12, primerLitresPerStroke=0.01),
               thermal=dict(coolantLitres=13.0, thermostatC=80.0, boilC=108.0, overheatC=100.0, warmRateIdleCPerMin=4.5,
                            coolRateCPerMin=1.2, beltBrokenHeatCPerMin=8.0, oilLitres=5.8),
               cabin=dict(stoveKw=6.0, heaterKw=4.5, saloonVolumeM3=5.5, cabVolumeM3=2.3),
               winch=dict(ropeWatts=1500.0, maxPullN=30000.0, maxSpeedMps=0.15, amps=170.0,
                          note='rope speed = ropeWatts / pull (N), at most maxSpeedMps; stalls at maxPullN; engine running'),
               forestStart=dict(status='TEMPORARY (Forest_Opening.json car.suggestedStart: "tank empty (needs the hut '
                                       'jerrycan), weak battery: 3 starter tries, then a crank / push start")',
                                anchor='Car_Start', tankLitres=[0.0, 0.0], tankValve='left', jerrycansLitres=[0.0, 0.0],
                                batteryCharge=0.22, starterTries=3,
                                starterTriesNote='explicit rule: a try = 2 s or more of cranking; after 3 the cold battery only '
                                                 'clicks (its cold-cranking reserve is spent) until the engine has charged it for '
                                                 '10 min or it was warmed indoors',
                                carbBowlLitres=0.0, engineC=-10.0, coolantOk=True,
                                beltState='ok', fusesBlown=[], frost=0.6, snowRoof=0.4, keyInIgnition=True,
                                massSwitchOn=True, doorsLocked=False, seatsDown=['L1', 'L2', 'L3', 'R1', 'R2'],
                                seatsFolded=['L4'], note='seat L4 folded: the battery box under it is reachable'))
    dump('vehicle.json', veh)
    # ------------------------------------------------------------------ materials (what the setup builds)
    MATS = {
        'M_Van_Body': dict(kind='lit', baseMap='T_Van_Body_BaseColor', smoothness=0.38),
        'M_Van_Trim': dict(kind='lit', baseMap='T_Van_Trim_BaseColor', smoothness=0.30),
        'M_Van_Cabin': dict(kind='lit', baseMap='T_Van_Cabin_BaseColor', smoothness=0.15),
        'M_Van_Mech': dict(kind='lit', baseMap='T_Van_Mech_BaseColor', smoothness=0.30),
        'M_Van_Props': dict(kind='lit', baseMap='T_Van_Props_BaseColor', smoothness=0.20),
        'M_Van_Seats': dict(kind='lit', baseMap='T_Van_Seats_BaseColor', smoothness=0.25),
        'M_Van_Wheel': dict(kind='lit', baseMap='T_Van_Wheel_BaseColor', smoothness=0.15),
        'M_Van_Snow': dict(kind='lit', baseMap='T_Van_Snow_BaseColor', smoothness=0.10),
        'M_Van_Gauges': dict(kind='emissive', baseMap='T_Van_Gauges_BaseColor', emissionMap='T_Van_Gauges_Emission',
                             smoothness=0.5),
        'M_Van_Needle': dict(kind='emissive', color=[0.95, 0.3, 0.06], emissionColor=[1.0, 0.35, 0.08], smoothness=0.5),
        'M_Van_LampBulb': dict(kind='emissive', color=[1.0, 0.8, 0.52], emissionColor=[1.0, 0.8, 0.52], smoothness=0.5),
        'M_Van_StoveGlow': dict(kind='emissive', color=[1.0, 0.42, 0.1], emissionColor=[1.0, 0.42, 0.1], smoothness=0.5),
        'M_Van_MirrorRT': dict(kind='mirror', color=[0.62, 0.64, 0.66], smoothness=0.95),
        'M_PSX_Glass_Cab': dict(kind='glass', color=[0.16, 0.2, 0.22], alpha=0.42, smoothness=0.9),
        'M_PSX_Glass_Room': dict(kind='glass', color=[0.16, 0.2, 0.22], alpha=0.42, smoothness=0.9),
        'M_Van_RadioDisplay': dict(kind='display', color=[0.05, 0.07, 0.05], emissionColor=[0.55, 1.0, 0.45], smoothness=0.7),
    }
    for m in sorted({m for n in NODES.values() for m in n.get('materials', [])}):
        if m.startswith('M_Van_Lens_'):
            MATS[m] = dict(kind='lens', baseMap='T_Van_Lens_BaseColor', emissionMap='T_Van_Lens_Emission', smoothness=0.75)
    used = sorted({m for n in NODES.values() for m in n.get('materials', [])})
    assert set(used) <= set(MATS), set(used) - set(MATS)
    dump('materials.json', dict(version=1, note='kind: lit (URP Lit, PSX atlas, Point), emissive (Lit + emission the rig drives), '
                                                'lens (lamp lens: atlas + emission map, per-lens emission from the rig), glass '
                                                '(Van/Glass shader: frost, snow, fog, hand prints, wipers), mirror (render '
                                                'texture of MirrorCam), display (the radio LCD: base + emission = the texture the '
                                                'rig draws, UV0 0..1 over the glass).',
                                materials=[dict(name=k, **{**dict(baseMap='', emissionMap='', color=[1.0, 1.0, 1.0],
                                                                  emissionColor=[0.0, 0.0, 0.0], alpha=1.0), **v})
                                           for k, v in sorted(MATS.items()) if k in used]))
    # ------------------------------------------------------------------ facts
    allb = [n['bounds_body'] for n in NODES.values() if n['type'] == 'MESH']
    lo = [min(b[0][i] for b in allb) for i in range(3)]
    hi = [max(b[1][i] for b in allb) for i in range(3)]
    facts = dict(version=1, frame=FRAME, tris=rep['tris'], meshes=rep['meshes'], nodes=len(NODES),
                 boundsVanMin=[-hi[1], lo[2], lo[0]], boundsVanMax=[-lo[1], hi[2], hi[0]],
                 lengthM=round(hi[0] - lo[0], 3), widthM=round(hi[1] - lo[1], 3), heightM=round(hi[2] - lo[2], 3),
                 wheelbaseM=veh['wheelbase'], trackM=veh['track'], wheelRadiusM=0.364, groundClearanceM=0.30,
                 saloonFloorY=0.81, saloonCeilingY=[2.03, 2.08], parts=len(parts), sockets=len(socks), colliders=len(cols),
                 lights=len(lights), panes=len(pane_list), zones=len(zones), itemTypes=len(types), stows=len(stows),
                 interiorCenter=[0.0, 1.42, -0.07], interiorSize=[1.80, 1.24, 4.04],
                 interiorNote='one box over the cab and the saloon (inner faces of walls, floor, roof, partition '
                              'included): the _In / _Out rule of the zones',
                 credit='UAZ 3D model by tiunov.se (Sketchfab), CC BY 4.0, modified')
    dump('model_facts.json', facts)
    print('[data] parts', len(parts), 'sockets', len(socks), 'colliders', len(cols), 'lights', len(lights),
          'panes', len(pane_list), 'seats', len(seats), 'materials', len(used), 'zones', len(zones), 'item types', len(types),
          'stows', len(stows))
    return NODES


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    main(a[0], a[1])
