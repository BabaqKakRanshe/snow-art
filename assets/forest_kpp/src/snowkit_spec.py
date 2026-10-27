"""Snow kit (snow_kit): shared small models that every building places as instances instead of modelling its own.
This file is the single source of the kit's names, atlas zones, panel regions, lamp kinds, materials and the overhead
wire rule; snowkit_kit.py (geometry), snowkit_tex.py (panel atlas, screens), snowkit_paint.py (atlas painter),
snowkit_build.py (snow_kit.blend), make_snowkit_doc.py (SNOW_KIT_CONTRACT.md) all read it.

Frame of every kit model (Blender): z up, the front faces -y; metres.  Origin ("точка привязки"): wall things - the
middle of the back face on the wall plane (y = 0, the thing stands out to -y); desk / floor / ground things - the middle
of the underside (z = 0); panel things (buttons, labels) - the middle on the panel face, +z = out of the panel; pipe
pieces - on the pipe axis (see each item).  Unity (FBX like the Forest packages): (x, y, z) -> (-x, z, -y), angles ->
-angle; so the front (-y) is the prefab's +Z (forward)."""

KIT_VERSION = '1.1'
UNITY_ROOT = 'Assets/Kit'                  # Models/Kit_*.fbx, Textures/T_Kit_*_px.png, Materials/M_Kit_*.mat, Prefabs/
PREFIX = 'Kit_'

# id, name (FBX / prefab / Blender collection), mount, Russian description (short)
ITEMS = [
    ('K1', 'Kit_Camera_Head', 'mount', 'камера видеонаблюдения: корпус с козырьком, объектив, красный диод'),
    ('K1', 'Kit_Camera_BracketWall', 'wall', 'кронштейн камеры к стене'),
    ('K1', 'Kit_Camera_BracketPole', 'pole', 'кронштейн камеры к столбу (хомуты на столб 0,20–0,26 м)'),
    ('K2', 'Kit_Monitor_CRT', 'desk', 'монитор ЭЛТ 14″ для видеонаблюдения; экран — отдельный объект, UV 0…1'),
    ('K3', 'Kit_Console_2', 'desk', 'пульт на 2 кнопки (корпус с наклонной панелью, места кнопок и подписей)'),
    ('K3', 'Kit_Console_4', 'desk', 'пульт на 4 кнопки'),
    ('K3', 'Kit_Console_Button', 'panel', 'кнопка пульта: колпачок IX_ (ход 5 мм), рамка, лампочка над кнопкой'),
    ('K3', 'Kit_Console_Label_Schranke', 'panel', 'подпись SCHRANKE / BARRIER'),
    ('K3', 'Kit_Console_Label_Tor', 'panel', 'подпись TOR / GATE'),
    ('K3', 'Kit_Console_Label_Licht', 'panel', 'подпись LICHT / LIGHTS'),
    ('K3', 'Kit_Console_Label_Blank', 'panel', 'пустая подпись'),
    ('K4', 'Kit_Phone', 'desk', 'дисковый телефон 70-х: корпус, трубка Phone_Receiver, диск Phone_Dial, шнур'),
    ('K5', 'Kit_Cabinet_Power', 'wall', 'распределительный шкаф: дверца, полка под аккумулятор машины, две клеммы, '
                                        'переключатель NETZ / BATTERIE, лампа «ток есть», табличка NOTSTROM 12V'),
    ('K6', 'Kit_JunctionBox', 'wall', 'коробка распределительная малая'),
    ('K7', 'Kit_Conduit_Straight', 'axis', 'труба для кабеля, прямой кусок 1 м (масштаб по x = длина)'),
    ('K7', 'Kit_Conduit_Elbow', 'axis', 'колено трубы 90°'),
    ('K7', 'Kit_Conduit_Clamp', 'axis', 'крепёжная скоба трубы'),
    ('K7', 'Kit_Conduit_Entry', 'wall', 'ввод трубы в коробку или шкаф (муфта с гайкой)'),
    ('K8', 'Kit_Pole', 'ground', 'опора ЛЭП деревянная: траверса, 3 изолятора линии'),
    ('K8', 'Kit_Pole_Trafo', 'ground', 'опора ЛЭП деревянная с трансформатором-«бочкой»'),
    ('K9', 'Kit_RoofStand', 'wall', 'трубостойка на крыше: труба с хомутами, траверса, изоляторы, ввод'),
    ('K9', 'Kit_Wire_Bare', 'wire', 'провод линии (голый алюминиевый): пролёт 40 м с провисом по правилу; ставится от точки Wire_ '
                                    'одной опоры к точке другой, растягивается по x под пролёт 20–60 м'),
    ('K9', 'Kit_Wire_Drop', 'wire', 'кабель ввода (чёрный): пролёт 10 м; от катушек опоры к трубостойке, растягивается по x под '
                                    'пролёт 3–25 м'),
    ('K10', 'Kit_DoorLock', 'wall', 'электрозамок двери: корпус (накладка) на полотне'),
    ('K10', 'Kit_DoorLock_Strike', 'wall', 'ответная планка электрозамка с лампочкой'),
    ('K11', 'Kit_Beacon', 'desk', 'проблесковый маячок оранжевый'),
    ('K12', 'Kit_Mast', 'ground', 'мачта: стальная труба 4,2 м на бетонной тумбе, люк внизу; два места сбоку на хомутах и место '
                                  'на верхушке — под насадки'),
    ('K12', 'Kit_Mast_Flood', 'side', 'прожектор (галогенный) на хомутах, наклон 30° вниз; свет LIGHT_Flood'),
    ('K12', 'Kit_Mast_Horn', 'side', 'рупорный громкоговоритель на хомутах (оповещение), наклон 15° вниз'),
    ('K12', 'Kit_Mast_Yagi', 'side', 'антенна «волновой канал» для рации (5 элементов, вертикальная поляризация) на выносе 0,6 м'),
    ('K12', 'Kit_Mast_Lamp', 'top', 'уличный фонарь: стакан на верхушку, изогнутый кронштейн, светильник с матовым стеклом; свет '
                                    'LIGHT_Street'),
    ('K12', 'Kit_Mast_Antenna', 'top', 'штыревая УКВ-антенна с четырьмя противовесами на трубе над верхушкой'),
    ('K12', 'Kit_Mast_Siren', 'top', 'электросирена оповещения: мотор, статор с окнами, колпак'),
]
ITEM_NAMES = [n for _, n, _, _ in ITEMS]

# ---------------------------------------------------------------- Kit atlas zones (float face attribute 'zone')
(Z_KCAB, Z_KCABIN, Z_KGALV, Z_KSTEEL, Z_KBLACK, Z_KPLAST, Z_KCAM, Z_KCRT, Z_KBEZEL, Z_KCONS, Z_KALU, Z_KBTN, Z_KPHONE,
 Z_KPOLE, Z_KPORC, Z_KTRAFO, Z_KCOPPER, Z_KREDC, Z_KCABLE, Z_KHANDLE, Z_KBRKR, Z_KCONC) = range(200, 222)
KIT_ZONES = list(range(200, 222))
ZONE_INFO = {   # zone: (name, sRGB base colour for the draft / the painter's base, finish)
    Z_KCAB: ('cabinet', (190, 192, 186), 'light grey powder-coated sheet steel (RAL 7035): chalky where the weather hits, '
                                         'rust at the lower edge and the door corners, dust on top'),
    Z_KCABIN: ('cabinet inside', (176, 178, 172), 'galvanised mounting plate and the cabinet inside: spangle, a little dust'),
    Z_KGALV: ('galvanised', (150, 154, 152), 'galvanised steel (conduits, clamps, brackets, crossarms, the roof stand): '
                                            'spangle, white rust, rust runs where water stands'),
    Z_KSTEEL: ('dark steel', (58, 60, 62), 'dark grey hammer-finish steel (locks, strike, bolts, camera brackets)'),
    Z_KBLACK: ('black plastic', (34, 34, 36), 'black plastic and rubber (bezels, glands, the beacon base, gaskets)'),
    Z_KPLAST: ('grey plastic', (196, 198, 194), 'light grey plastic (the junction box): yellowed a little, grime at the bottom'),
    Z_KCAM: ('camera', (214, 212, 204), 'off-white painted aluminium (the camera housing): grime streaks from the sunshield'),
    Z_KCRT: ('monitor case', (178, 172, 156), 'grey-beige painted steel case of the monitor (RAL 7032), vent slots'),
    Z_KBEZEL: ('monitor bezel', (70, 70, 72), 'dark grey plastic bezel'),
    Z_KCONS: ('console', (170, 166, 150), 'pebble grey console housing (RAL 7032)'),
    Z_KALU: ('aluminium', (176, 178, 182), 'brushed aluminium front panel'),
    Z_KBTN: ('button', (46, 150, 66), 'green push-button cap, glossy plastic'),
    Z_KPHONE: ('phone', (204, 98, 40), 'orange 70s phone plastic (FeTAp 611): glossy, yellowed where held'),
    Z_KPOLE: ('pole', (88, 66, 46), 'creosoted spruce pole: dark brown low down, sun-bleached grey-brown up top, checks '
                                    '(cracks) along the grain, the brand plate'),
    Z_KPORC: ('porcelain', (222, 220, 210), 'white glazed porcelain insulators: grime on the top sheds'),
    Z_KTRAFO: ('transformer', (112, 120, 108), 'grey-green painted transformer tank: rust runs from the lid and the seams'),
    Z_KCOPPER: ('copper', (176, 104, 60), 'copper and brass (terminals, the clamp jaws)'),
    Z_KREDC: ('red cover', (176, 32, 26), 'red insulating cover of the + clamp'),
    Z_KCABLE: ('cable', (30, 30, 30), 'black rubber cable'),
    Z_KHANDLE: ('handle', (28, 28, 30), 'black bakelite handles and knobs'),
    Z_KBRKR: ('breakers', (226, 224, 216), 'white breaker modules on the DIN rail, black toggles'),
    Z_KCONC: ('concrete', (132, 130, 124), 'concrete (the beacon / small pads)'),
}

# ---------------------------------------------------------------- panel atlas T_Kit_Panel (512 x 512, point filter)
# name: (x0, y0, x1, y1) pixels, top-left origin; physical size of the quad that shows it (w, h) metres
PANEL_N = 512
PANEL = {
    'btn_schranke': ((0, 0, 80, 28), (0.070, 0.0245), 'SCHRANKE over BARRIER, white on black'),
    'btn_tor': ((80, 0, 160, 28), (0.070, 0.0245), 'TOR over GATE'),
    'btn_licht': ((160, 0, 240, 28), (0.070, 0.0245), 'LICHT over LIGHTS'),
    'btn_blank': ((240, 0, 320, 28), (0.070, 0.0245), 'blank black label (worn)'),
    'lbl_console': ((320, 0, 448, 16), (0.240, 0.030), 'strip on the console top: TORSTEUERUNG / GATE CONTROL'),
    'sign_notstrom': ((0, 32, 120, 112), (0.240, 0.160), 'cabinet door plate: yellow triangle with the black lightning, '
                                                         'NOTSTROM 12V over EMERGENCY 12V'),
    'lbl_switch': ((120, 32, 184, 96), (0.080, 0.080), 'switch dial plate: NETZ (left, 0) and BATTERIE (right, 90), '
                                                       'MAINS / BATTERY small under them'),
    'sign_volt': ((184, 32, 232, 74), (0.100, 0.0875), 'yellow warning triangle with the black lightning (sticker)'),
    'sign_danger': ((232, 32, 296, 112), (0.200, 0.250), 'pole plate: lightning symbol, LEBENSGEFAHR over DANGER'),
    'phone_dial': ((296, 32, 344, 80), (0.090, 0.090), 'rotary dial: cream face, ten finger holes, the finger stop'),
    'lbl_monitor': ((344, 32, 472, 48), (0.300, 0.0375), 'monitor front strip under the screen: CCTV MONITOR, '
                                                         'POWER, BRIGHT, CONTRAST'),
    'lbl_cabinet_in': ((0, 112, 96, 160), (0.240, 0.120), 'inside the cabinet: the circuit card (hand-drawn diagram, '
                                                          'BATTERIE 12V -> SCHRANKE / TOR / LICHT)'),
    'lbl_trafo': ((96, 112, 160, 144), (0.160, 0.080), 'transformer rating plate (20 kV / 0.4 kV, 50 kVA, 1974)'),
    'lbl_pole': ((160, 112, 192, 144), (0.060, 0.060), 'pole number plate (enamel, white on blue: a number)'),
    # lenses (base = dark / unlit look, emission = lit) and halo tiles (emission only)
    'l_red': ((0, 192, 32, 224), (0.020, 0.020), 'red indicator dome'),
    'l_green': ((32, 192, 64, 224), (0.020, 0.020), 'green indicator dome'),
    'l_amber': ((64, 192, 96, 224), (0.020, 0.020), 'amber indicator dome'),
    'l_beacon': ((96, 192, 160, 256), (0.400, 0.130), 'beacon dome, cylindrical UV (u round, v up): orange fresnel '
                                                     'ribs, the reflector behind'),
    'l_cam': ((160, 192, 192, 224), (0.060, 0.060), 'camera front glass: dark, the lens and a reflection'),
    'glow_red': ((192, 192, 224, 224), (0.1, 0.1), 'halo tile'),
    'glow_green': ((224, 192, 256, 224), (0.1, 0.1), 'halo tile'),
    'glow_amber': ((256, 192, 288, 224), (0.1, 0.1), 'halo tile'),
    'glow_orange': ((288, 192, 352, 256), (0.1, 0.1), 'halo tile (beacon)'),
    'l_flood': ((0, 264, 64, 308), (0.26, 0.18), 'floodlight front glass: prismatic ribs, the reflector and the halogen tube '
                                                 'behind'),
    'l_street': ((64, 264, 144, 296), (0.50, 0.20), 'street lamp bowl (opal acrylic) seen from below: the lamp a soft glow in '
                                                    'the middle'),
    'glow_white': ((144, 256, 208, 320), (0.1, 0.1), 'halo tile (floodlight, street lamp)'),
}
SCREEN = dict(size=(128, 96), off='T_Kit_Screen_Off', on='T_Kit_Screen_On', on_gate='T_Kit_Screen_On_Gate',
              note='the CRT screen object has its own UV 0..1 over the whole glass; Unity puts the camera picture there '
                   '(render texture) in M_Kit_Screen_On; T_Kit_Screen_On (CAM 1, the barrier) and T_Kit_Screen_On_Gate '
                   '(CAM 2, the gate) are stand-in CCTV pictures for the previews')

# lamp lens kinds -> panel tile and colour: material M_Kit_Lamp_<Kind> (lit) and M_Kit_Lamp_<Kind>_Off
LAMP_KINDS = {'Red': 'l_red', 'Green': 'l_green', 'Amber': 'l_amber', 'Beacon': 'l_beacon', 'Flood': 'l_flood', 'Street': 'l_street'}

# ---------------------------------------------------------------- overhead wire rule (K9 and the line)
WIRE = dict(
    sag_k=0.0010, sag_min=0.05,             # sag at mid-span = max(sag_min, sag_k * span^2) (a parabola ~ the catenary;
                                            # forest_base's Forest_Wires used 0.0024: looser)
    seg_len=1.5, seg_min=6,                 # segments = max(seg_min, ceil(span / seg_len))
    r_lv=0.007,                             # LV twisted service cable (ABC, black): radius
    r_bare=0.0045,                          # bare aluminium line wire: radius
    sides=5,                                # tube sides
    note='parabola through the two attach points: p(t) = A + (B - A) t - up * 4 sag t (1 - t), t = 0..1; sag = '
         'max(sag_min, sag_k * L^2), L = the horizontal span; segments = max(seg_min, ceil(L / seg_len)); a tube of `sides` '
         'sides and radius r_lv (service drop, black, M_Kit_Wire) or r_bare (line wires, M_Kit_WireBare)')
