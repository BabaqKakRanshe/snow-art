"""Sheets for the far points: A the dishes; B the radome and the relay mast; C the weather station and the fire lookout;
D the pump house and the chapel; E the cabin and the campsite; F Update 3 and now (Update 3's models from the same
cameras, its previews Dish1 and Chapel and the same viewpoints now); G the atlases and the sign panel.
python3 make_sheets_far.py [out_dir] [--only A,C,G] (1.1: only the sheets named)"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sheets_main as MSM
import make_sheets_road as MSR

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith('--') and (sys.argv.index(a) == 0 or sys.argv[sys.argv.index(a) - 1] != '--only')]
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
OUT = ARGS[0] if ARGS else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'far')
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3R = SCR + 'u5/checks/u3_far'
U3P = SCR + 'u3/Assets/Locations/Forest/Previews'
INFO = json.load(open(os.path.join(HERE, 'out', 'far.json')))
CHK = json.load(open(SCR + 'u5/checks/far_checks.json'))
TEX = os.path.join(HERE, 'tex', 'far')
MSM.OUT, MSM.R, MSM.INFO, MSM.TEX = OUT, R, INFO, TEX
img, sheet, ru, thou, F, INK, DIM, wrap = MSM.img, MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.wrap
u3 = MSR.u3


def atlas_tile(name, label, W=600, H=420):
    path = os.path.join(TEX, f'T_Far_{name}_BaseColor.png')
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    side = 380
    t = a.resize((side, side), Image.NEAREST if s <= side else Image.BOX)
    canvas = Image.new('RGB', (W, H), (10, 10, 12))
    canvas.paste(t, (12, 30))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 404 + (i % 8) * 23, 40 + (i // 8) * 23
        d.rectangle([x0, y0, x0 + 20, y0 + 20], fill=tuple(int(v) for v in c))
    d.text((404, 236), f'{s} × {s}', fill=INK, font=F(20, True))
    d.text((404, 264), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


def tris(*names):
    tb = INFO['tris_by_object']
    return thou(sum(tb.get(n, 0) for n in names))


if __name__ == '__main__':
    at = INFO['atlases']
    u3t = INFO['u3_tris']
    want = lambda letter: ONLY is None or letter in ONLY
    if want('A'):
      sheet('Дальние точки — антенны',
          'Пять антенн на местах обновления 3: цоколь, опора со стремянкой, поворотная голова, вилка и вал угла места '
          'за отражателем, отражатель на ребристом каркасе, облучатель с красным огнём; шкаф оборудования с дверцей, '
          'табличка, фонарь двора; день и ночь',
          [(img('dish1'), 'Dish_1: 16 м, угол места 38°'),
           (img('dish1_back'), 'сзади: рёбра, кольца, вал, голова, стремянка, шкаф, фонарь'),
           (img('dish1_feed'), 'облучатель на четырёх растяжках, огонь — место обновления 3'),
           (img('dish1_yoke'), 'вилка, подшипники, вал угла места, приводы'),
           (img('dish1_base'), 'цоколь, шкаф, табличка ANTENNENANLAGE, фонарь'),
           (img('dish1_cab'), 'шкаф открыт: модули, магнитофон TapeDeck (forest_devices), светодиоды, дверца — на 100°'),
           (img('dish2'), 'Dish_2: та же сетка, 42°'), (img('dish5'), 'Dish_5: 36°'),
           (img('dish3'), 'Dish_3: 12 м, 45°'), (img('dish4'), 'Dish_4: 12 м, 40°'),
           (img('map_dish1'), 'Dish_1 на рельефе обновления 3'),
           (img('map_dish1_night'), 'ночь, питание включено: огни, фонарь, светодиоды')],
          [('Атлас', f'Dish16 {at["Dish16"]["size"]} — Dish_1, 2, 5 (общий: одинаковые UV), Dish12 {at["Dish12"]["size"]} — '
                     'Dish_3, 4; табличка — панель (160 px/м)'),
           ('Треугольников', f'Dish_1 {tris("Dish_1", "IX_CabinetDoor_2")} (обновление 3 — {thou(u3t["Dish_1"])}), '
                             f'Dish_3 {tris("Dish_3", "IX_CabinetDoor_4")} ({thou(u3t["Dish_3"])})')],
          'far_A_dishes.jpg')
    if want('B'):
      sheet('Дальние точки — радом и ретранслятор',
          'Радом на 16-метровой башне: стремянка в ограждении, площадка, купол из панелей, огонь на вершине, укрытие с '
          'кондиционером. Ретранслятор: мачта 42 м, огни на 21 и 42 м, антенна-барабан, панельные антенны, укрытие, '
          'двор за рабицей с воротами',
          [(img('radome'), 'радом: башня, площадка, купол'), (img('radome_top'), 'купол: панели, кольцо, огонь'),
           (img('radome_hut'), 'укрытие: дверь, табличка RADARSTATION, кондиционер'),
           (img('radome_foot'), 'низ башни: фундаменты, стремянка'),
           (img('map_radome'), 'радом на рельефе обновления 3'), (img('map_radome_night'), 'ночь: огонь на вершине'),
           (img('relay'), 'ретранслятор: мачта 42 м'), (img('relay_top'), 'верх: барабан, панели, огонь'),
           (img('relay_gate'), 'ворота двора: рабица, колючка, табличка FUNKSTATION'),
           (img('relay_yard'), 'двор: укрытие, фидеры, фундаменты'), (img('map_relay'), 'на рельефе обновления 3')],
          [('Атлас', f'Towers {at["Towers"]["size"]} — радом и ретранслятор; рабица и колючка — материалы базы'),
           ('Треугольников', f'радом {tris("Radome")} (обновление 3 — {thou(u3t["Radome"])}), ретранслятор '
                             f'{tris("RelayMast")} ({thou(u3t["RelayMast"])})')],
          'far_B_radome_relay.jpg')
    lk = CHK['lookout']
    if want('C'):
      sheet('Дальние точки — метеостанция и пожарная вышка',
          'Метеостанция за белым штакетником; вышка 22 м: лестница обновления 3 (те же ступени и площадки), косоуры и '
          'перила, лестничный проём в полу кабины, трап, ограждение, кабина с окнами, пеленгатор',
          [(img('meteo'), 'метеостанция: ограда, будка, мачта, осадкомер, регистратор'),
           (img('meteo_screen'), 'будка — MeteoScreen из forest_devices: дверца на север'), (img('meteo_mast'), 'анемометр и флюгер'),
           (img('meteo_gate'), 'калитка и табличка WETTERSTATION'), (img('map_meteo'), 'на рельефе обновления 3'),
           (img('lookout'), 'вышка: ноги, связи, лестница, кабина'), (img('lookout_stairs'), 'марши обновления 3, косоуры, перила'),
           (img('lookout_cab'), 'кабина: обшивка, окна, шатровая крыша, громоотвод'),
           (img('lookout_ladder'), 'с верхней площадки: трап в проём кабины'),
           (img('lookout_in'), 'в кабине: проём с ограждением, пеленгатор, табурет'),
           (img('lookout_landing'), 'проём сверху: трап, верхняя площадка'), (img('map_lookout'), 'на рельефе обновления 3')],
          [('Атлас', f'Meteo {at["Meteo"]["size"]}, Lookout {at["Lookout"]["size"]}'),
           ('Треугольников', f'метеостанция {tris("MeteoStation")} без будки (будка — 1 328, forest_devices; обновление 3 — '
                             f'{thou(u3t["MeteoStation"])}), вышка '
                             f'{tris("LookoutTower")} ({thou(u3t["LookoutTower"])})'),
           ('Подъём', f'голова игрока на верхней площадке, трапе и в кабине — зазор не меньше '
                      f'{ru(lk["top"]["min_clearance_m"] * 100, 0)} см; лестница обновления 3 — декоративная '
                      f'({ru(min(lk["u3_stairs"]["angle_deg"]), 0)}–{ru(max(lk["u3_stairs"]["angle_deg"]), 0)}°, марши друг над другом)')],
          'far_C_meteo_lookout.jpg')
    if want('D'):
      sheet('Дальние точки — насосная и часовня',
          'Кирпичная насосная у реки со стальной дверью; часовня на каменном цоколе: колокольня, дверь на кованых '
          'полосах, скамьи, алтарь и свечи, погост',
          [(img('pump'), 'насосная: кирпич, плоская крыша, дверь, табличка PUMPSTATION'),
           (img('pump_back'), 'сзади: труба к воде'), (img('pump_in'), 'дверь открыта наружу: насос, мотор, щит'),
           (img('map_pump'), 'на рельефе обновления 3'),
           (img('chapel'), 'часовня: цоколь, штукатурка, дранка, колокольня'),
           (img('chapel_back'), 'с другой стороны'), (img('chapel_graves'), 'погост: шесть могил с железными крестами'),
           (img('chapel_in'), 'внутри: скамьи, алтарь, крест'), (img('chapel_altar'), 'алтарь: покров, четыре свечи (M_Candle)'),
           (img('map_chapel'), 'на рельефе обновления 3'), (img('map_chapel_night'), 'ночь: свечи в окнах')],
          [('Атлас', f'Small {at["Small"]["size"]} — насосная, избушка, стоянка; Chapel {at["Chapel"]["size"]}'),
           ('Треугольников', f'насосная {tris("PumpHouse", "IX_PumpDoor_7")} (обновление 3 — {thou(u3t["PumpHouse"])}), '
                             f'часовня {tris("Chapel", "IX_ChapelDoor_8")} ({thou(u3t["Chapel"])})')],
          'far_D_pump_chapel.jpg')
    if want('E'):
      sheet('Дальние точки — избушка и стоянка',
          'Сруб с конопаткой в пазах, крыльцо, печь, нары; брошенная стоянка: обрушенная палатка, кострище, вещи, фонарик',
          [(img('cabin'), 'избушка: сруб, крыльцо, окно, поленница'), (img('cabin_back'), 'сзади: фронтон, труба'),
           (img('cabin_in'), 'внутри: печь, стол, нары, окно'), (img('map_cabin'), 'на рельефе обновления 3'),
           (img('camp'), 'стоянка: палатка, кострище, стул, рюкзак'), (img('camp_fire'), 'кострище, котелок, угли'),
           (img('camp_torch'), 'фонарик: стекло M_Headlight там, где свет обновления 3'),
           (img('map_camp'), 'на рельефе обновления 3'), (img('map_camp_night'), 'ночь: фонарик светит в траву')],
          [('Треугольников', f'избушка {tris("Cabin", "IX_CabinDoor_9")} (обновление 3 — {thou(u3t["Cabin"])}), стоянка '
                             f'{tris("Campsite")} ({thou(u3t["Campsite"])})')],
          'far_E_cabin_camp.jpg')
    tiles = []
    for vn, lab in (('cmp_dish1', 'антенна 16 м'), ('cmp_dish1_base', 'низ антенны'), ('cmp_dish3', 'антенна 12 м'),
                    ('cmp_radome', 'радом'), ('cmp_relay', 'ретранслятор'), ('cmp_meteo', 'метеостанция'),
                    ('cmp_lookout', 'вышка'), ('cmp_pump', 'насосная'), ('cmp_chapel', 'часовня'), ('cmp_cabin', 'избушка'),
                    ('cmp_camp', 'стоянка')):
        tiles.append((u3(os.path.join(U3R, vn + '.png')), f'обновление 3: {lab}'))
        tiles.append((img(vn), f'теперь: {lab}'))
    for vp, vn in (('Forest_Dish1.jpg', 'map_vp_dish1_night'), ('Forest_Chapel.jpg', 'map_vp_chapel_night')):
        tiles.append((u3(os.path.join(U3P, vp)), f'обновление 3, превью {vp[7:-4]} (ночь, с деревьями)'))
        tiles.append((img(vn), 'теперь, та же камера (ночь): только рельеф и модели пакета'))
    if want('F'):
      sheet('Дальние точки — обновление 3 и теперь',
          'Слева — модели обновления 3 (FBX в цветах материалов) и его превью карты, справа — перестроенные с тех же '
          'камер; места, размеры, пивоты дверей и огни — те же',
          tiles, [], 'far_F_u3_vs_now.jpg')
    tiles = [(atlas_tile(n, f'T_Far_{n}'), None) for n in ('Dish16', 'Dish12', 'Towers', 'Meteo', 'Lookout', 'Chapel', 'Small')
             if os.path.exists(os.path.join(TEX, f'T_Far_{n}_BaseColor.png'))]
    pa = Image.open(os.path.join(TEX, 'T_Far_Panel_BaseColor.png')).convert('RGB')
    pt = Image.new('RGB', (600, 420), (10, 10, 12))
    pt.paste(pa.resize((380, 380), Image.NEAREST), (12, 30))
    d = ImageDraw.Draw(pt)
    d.rectangle([4, 2, 230, 26], fill=(0, 0, 0))
    d.text((8, 4), f'T_Far_Panel {pa.size[0]}', fill=INK, font=F(18, True))
    for j, line in enumerate(wrap(d, 'таблички антенн, радома, ретранслятора, метеостанции, вышки, насосной, часовни '
                                     '(сначала по-немецки, под ним по-английски); 160 px/м, ночью слабо светятся',
                                  F(16), 190)):
        d.text((404, 40 + j * 22), line, fill=DIM, font=F(16))
    tiles.append((pt, None))
    if want('G'):
      sheet('Дальние точки — атласы', 'По 64 цвета, AO в цвете, дизеринг 4×4, фильтр «точка»; до 51,3 px/м (генераторная)',
          tiles, [], 'far_G_atlases.jpg', cols=2, W=600, H=420)
