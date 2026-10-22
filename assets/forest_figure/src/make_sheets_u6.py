"""Sheets of Forest Update 6: the generator container (A outside, B inside, C Update 3 and now, D atlases), the items (A..D
the 84 models, E Update 3 and now, F atlases), the figure (A poses and the walk, B in the van, C atlas and rig).
python3 make_sheets_u6.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sheets_main as MSM

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'u6')
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3P = SCR + 'u3/Assets/Locations/Forest/Previews'
MSM.OUT = OUT
sheet, ru, thou, F, INK, DIM, BG, wrap = MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.BG, MSM.wrap
G = json.load(open(os.path.join(HERE, 'out', 'gcf.json')))
GC = json.load(open(os.path.join(HERE, 'out', 'gcf_contract.json')))
IT = json.load(open(os.path.join(HERE, 'out', 'items.json')))
FG = json.load(open(os.path.join(HERE, 'out', 'fig.json')))
REP = json.load(open(os.path.join(HERE, 'out', 'forest_update6', 'fbx', 'u6_export_report.json')))
U3I = json.load(open(os.path.join(HERE, 'items_u3.json')))


def img(path, W=900, H=600):
    return MSM.fit(Image.open(path).convert('RGB'), W, H)


def atlas_tile(path, label, info=None, W=600, H=420):
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
    if info and info.get('ppm'):
        d.text((404, 264), f'{ru(info["ppm"], 1)} px/м', fill=DIM, font=F(18))
    d.text((404, 290), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


def big_sheet(title, sub, image_path, rows, fname, W=1800):
    """one wide picture (a contact sheet) with a title and rows below"""
    pic = Image.open(image_path).convert('RGB')
    if pic.width != W:
        pic = pic.resize((W, round(pic.height * W / pic.width)), Image.LANCZOS)
    g = 16
    S = Image.new('RGB', (W + 2 * g, 160 + pic.height + 1200), BG)
    d = ImageDraw.Draw(S)
    d.text((g, 18), title, fill=INK, font=F(50, True))
    sub_lines = wrap(d, sub, F(25), W)
    for j, line in enumerate(sub_lines):
        d.text((g, 84 + j * 32), line, fill=DIM, font=F(25))
    top = 130 + 32 * (len(sub_lines) - 1)
    S.paste(pic, (g, top))
    y = top + pic.height + 18
    f, fb = F(23), F(23, True)
    for k, v in rows:
        d.text((g, y), k, fill=DIM, font=fb)
        yl = y
        for j, line in enumerate(wrap(d, v, f, W - 250)):
            d.text((g + 250, y + j * 30), line, fill=INK, font=f)
            yl = y + j * 30
        y = yl + 38
    S = S.crop((0, 0, S.width, y + 10))
    p = os.path.join(OUT, fname)
    S.save(p, quality=92)
    print(p, S.size)
    return p


# ======================================================================== the generator container
gc = lambda v: img(os.path.join(R, 'gcont', v + '.png'))
gu = lambda v: img(os.path.join(R, 'gcont_u3', v + '.png'))
tb = G['tris_by_object']
at = G['atlases']
ix = sorted(n for n in GC['parts'] if n.startswith('IX_') and not n.endswith('_Sign'))
lamps = G['data']['prefabLights']['lights']
sheet('Контейнер генератора — снаружи',
      'GenContainer обновления 6: сдвоенный контейнер пакета generator_container на месте контейнера обновления 3 (прежние '
      'имя, GUID, место и поворот). Синяя краска с потёками ржавчины, жалюзи, выхлоп, опоры; грузовые двери у ворот двора, '
      'в дальнем торце — боковая дверь и короб заливной горловины с крышкой',
      [(gc('ext_cargo'), 'грузовые двери (IX_ContDoorL_83, IX_ContDoorR_84), закрыты'),
       (gc('ext_far'), 'дальний торец: боковая дверь IX_ContSideDoor_85, короб горловины IX_GenFillCap_300'),
       (gc('ext_open'), 'грузовые двери открыты (160° и 170°)'),
       (gc('far_open'), 'боковая дверь открыта (90°), крышка горловины поднята (100°)')],
      [('Размеры', f'{ru(G["bbox"][1][0] - G["bbox"][0][0], 2)} × {ru(G["bbox"][1][1] - G["bbox"][0][1], 2)} × '
                   f'{ru(G["bbox"][1][2], 2)} м (с выхлопом); пол 0,31 м над землёй'),
       ('Треугольников', f'{thou(REP["GenContainer"]["tris"])} (обновление 3 — 19 994): корпус {thou(tb["GenContainer"])}, '
                         f'двери {thou(tb["IX_ContDoorL_83"])} / {thou(tb["IX_ContDoorR_84"])}, боковая дверь '
                         f'{thou(tb["IX_ContSideDoor_85"])}'),
       ('Части IX', ', '.join(ix) + ' — прежние имена; + стекло Window_Glass'),
       ('Свет', f'{len(lamps)} источника в сети (tag power, выключены на старте): 3 плафона внутри, фонарь над грузовыми '
                f'дверями; линзы M_Lamp_BulbOff ↔ M_Lamp_Bulb, лампы «работа» M_LEDOff ↔ M_LEDOn')],
      'gcont_A_outside.jpg')
sheet('Контейнер генератора — внутри',
      'Северный бокс: дневной бак 100 л с мерной трубкой, бочки с насосом, кабели; южный бокс: дизель-генератор с панелью '
      '(ключ пуска IX_GenStart_86), щит MAIN SWITCHBOARD с автоматами IX_Breaker_87…89 и перекидным рубильником '
      'IX_MainSwitch_90 (OFF → GEN), дверца щита открыта',
      [(gc('int_vp'), 'точка обзора GenContainer (новая): из грузового проёма вдоль генератора'),
       (gc('int_north'), 'северный бокс: бак, бочки, боковая дверь'),
       (gc('int_board'), 'щит: автоматы, рубильник, схема цепей'),
       (gc('lid_close'), 'крышка горловины: табличка DIESEL / DAY TANK 100 L')],
      [('Горловина', f'топливо — в короб на торце: горловина {G["data"]["fill"]["neck"]}, место игрока '
                     f'{G["data"]["fill"]["stand"]} (мир Unity); бак {G["data"]["fill"]["capacityL"]} л (был 60 л)'),
       ('Ходы частей', 'ключ пуска 0…52°, автоматы 0…60°, рубильник 0…60°, крышка 0…110°, боковая дверь 0…100°, створки '
                       '0…160° и 0…170°'),
       ('Обзор', f'точка GenContainer: p {G["data"]["viewpoint"]["p"]}, цель {G["data"]["viewpoint"]["target"]}, '
                 f'fov {ru(G["data"]["viewpoint"]["fov"], 0)}° (прежняя камера оказалась бы внутри генератора)')],
      'gcont_B_inside.jpg')
pv = os.path.join(U3P, 'Forest_GenContainer.jpg')
sheet('Контейнер генератора — обновление 3 и теперь',
      'Модель обновления 3 (без текстур, серым) и новая — с тех же камер; превью GenContainer обновления 3 снято с прежней '
      'точки, внутри прежнего контейнера',
      [(gu('ext_cargo'), 'обновление 3'), (gc('ext_cargo'), 'теперь'),
       (gu('ext_far'), 'обновление 3'), (gc('ext_far'), 'теперь'),
       (img(pv), 'обновление 3: превью GenContainer'), (gc('int_vp'), 'теперь: новая точка обзора GenContainer')],
      [('Отличия', 'сдвоенный контейнер вместо одного: южный бокс стоит на месте прежнего, северный добавлен рядом; '
                   'горловина и боковая дверь — в дальнем торце; свет — 3 плафона и фонарь')],
      'gcont_C_u3_vs_now.jpg')
T = os.path.join(HERE, 'tex', 'gcf')
tiles = [(atlas_tile(os.path.join(T, f'T_GCont_{a}_BaseColor.png'), f'T_GCont_{a}', at.get(a)), '')
         for a in ('Cont', 'Genset', 'Props')]
tiles.append((atlas_tile(os.path.join(T, 'T_GCont_Panel_BaseColor.png'), 'T_GCont_Panel (надписи, приборы)'), ''))
sheet('Контейнер генератора — атласы', 'PSX-атласы (свет и затенение запечены, точечная фильтрация) и панель надписей',
      tiles, [('Материалы', 'M_GCont_Cont, M_GCont_Genset, M_GCont_Props, M_GCont_Panel (атласы, lit без бликов); '
                            'M_GCont_Needle, M_GCont_Diesel (цвет); из карты: M_Lamp_BulbOff, M_LEDOff, M_GlassClear')],
      'gcont_D_atlases.jpg', W=600, H=420)

# ======================================================================== the items
ti = sum(REP[n]['tris'] for n in U3I)
for i, part in enumerate('ABCD'):
    big_sheet(f'Предметы — {part}', 'Модели обновления 6 (те же имена, начала координат и размеры, что в обновлении 3), '
              'атлас Props и панель надписей; рамка — по каждому предмету отдельно (масштаб разный)',
              os.path.join(R, 'items', f'items_{i}.jpg'),
              [('Всего', f'84 модели: 83 обновления 3 ({thou(ti)} треугольников, было {thou(sum(v["tris"] for v in U3I.values()))}) '
                         f'+ Item_RadioSet ({REP["Item_RadioSet"]["tris"]})')] if part == 'A' else [],
              f'items_{part}.jpg')
N = ['Item_Jerrycan20', 'Item_Flashlight', 'Item_Funnel', 'Item_NoteForm', 'Item_Padlock', 'Item_Key_Generator',
     'Item_CableReel', 'Item_Toolbox', 'Item_Radio', 'Item_Kettle', 'Item_Backpack', 'Item_OilCan']
tiles = []
for n in N:
    tiles.append((img(os.path.join(R, 'items_cmp', f'{n}_u3.png'), 420, 320), f'{n[5:]}: обновление 3'))
    tiles.append((img(os.path.join(R, 'items_cmp', f'{n}_now.png'), 420, 320), 'теперь'))
sheet('Предметы — обновление 3 и теперь', 'Одна камера на пару; модели обновления 3 — без текстур (серым)', tiles,
      [('Размеры', 'коробки моделей совпадают с обновлением 3 (до 12 мм; мягкие вещи — до 3 см): коллайдеры каталога и '
                   'места в данных прежние'),
       ('Особые точки', f'фонарик: стекло спереди на x = {IT["special"]["Item_Flashlight"]["lens_front_x"]} (light.p '
                        f'каталога); канистра: носик и ручка — точки каталога; воронка, как в обновлении 3, — носиком вниз '
                        f'(в хижине её переворачивает поза)')],
      'items_E_u3_vs_now.jpg', cols=4, W=420, H=320)
T = os.path.join(HERE, 'tex', 'items')
tiles = [(atlas_tile(os.path.join(T, 'T_Item_Props_BaseColor.png'), 'T_Item_Props', IT['atlases'].get('Props')), ''),
         (atlas_tile(os.path.join(T, 'T_Item_Panel_BaseColor.png'), 'T_Item_Panel (надписи)'), ''),
         (atlas_tile(os.path.join(T, 'T_Item_Panel_Emission.png'), 'T_Item_Panel_E (окно рации)'), '')]
sheet('Предметы — атласы', 'Атлас Props (128 цветов на 84 модели), панель надписей пиксельным шрифтом и её карта свечения',
      tiles, [('Материалы', 'M_Item_Props, M_Item_Panel (lit без бликов); M_RadioDisplay / M_RadioDisplayOn (окно канала '
                            'рации: X08 меняет на второй — светится 27.135); из карты: M_TorchLens (стекло фонарика), '
                            'M_Water (вода в ведре)')],
      'items_F_atlases.jpg', W=600, H=420)

# ======================================================================== the figure
fs = FG['sit']
big_sheet('Фигура Apparition — позы', 'Ход Walk по кадрам (сбоку) и позы спереди, сбоку, лицо; рост 2,3 м',
          os.path.join(R, 'figsheets', 'fig_poses.jpg'),
          [('Клипы', 'Stand (поза), Walk (цикл 30 кадров = 1,25 с при 24 к/с), Sit, SitLook (15 кадров = 0,6 с)'),
           ('Ход', f'опорная стопа стоит на земле (корень качается так, что нижняя точка — на земле), маховая проходит над '
                   f'землёй; ноги не скользят, когда объект едет на {ru(FG["walk_speed"], 2)} м/с'),
           ('Скелет', f'{len(REP["Apparition"]["bones"])} костей: ' + ', '.join(REP['Apparition']['bones'])),
           ('Треугольников', f'{REP["Apparition"]["tris"]}; атлас T_Fig_Figure {FG["atlases"]["Figure"]["size"]} px, '
                             f'материал M_Apparition')],
          'fig_A_poses.jpg', W=2400)
big_sheet('Фигура Apparition — в фургоне (X03)',
          'Sit и SitLook на макете скамьи фургона van3: сиденье 0,425 м над полом, потолок 0,709 м над сиденьем, стенка '
          '0,25 м за точкой посадки; справа — вид камеры зеркала заднего вида (MirrorCam) с левой скамьи (Sit_L2)',
          os.path.join(R, 'figsheets', 'fig_van.jpg'),
          [('Sit', f'туловище сложено вперёд под потолком (наклон {ru(fs["lean"], 0)}°), голова опущена, длинные руки '
                   f'свисают между колен, пальцы над полом; спина на {ru(fs["frames"]["1"]["top"], 3)} м над сиденьем'),
           ('SitLook', '0,6 с: голова выходит вперёд из плеч и поворачивается лицом к кабине (к зеркалу) — с левой скамьи '
                       'это левая сторона фигуры'),
           ('Начало', 'начало координат — точка сиденья под тазом (Sit, SitLook); между стоп на земле (Stand, Walk)')],
          'fig_B_van.jpg', W=1260)
tiles = [(atlas_tile(os.path.join(HERE, 'tex', 'fig', 'T_Fig_Figure_BaseColor.png'), 'T_Fig_Figure', FG['atlases']['Figure']), '')]
sheet('Фигура Apparition — атлас', 'Пальто, кожа, тёмные провалы глаз и рта, ноги', tiles,
      [('Материал', 'M_Apparition — атлас, lit без бликов; без коллайдера (Apparition в noColliderPrefixes)')],
      'fig_C_atlas.jpg', cols=1, W=600, H=420)
