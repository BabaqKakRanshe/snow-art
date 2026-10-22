"""Sheets for the base prefabs: A the shaft hatch, the crates and the log pile; B the helipad and the radio mast; C the yard
lights, the power line and the fences; D Update 3 and now (Update 3's models from the same cameras, its preview Base and
the same viewpoint now); E the atlases and the sign panel.  python3 make_sheets_base.py [out_dir]"""
import os, sys, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sheets_main as MSM
import make_sheets_road as MSR

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'base')
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3R = SCR + 'u5/checks/u3_base'
U3P = SCR + 'u3/Assets/Locations/Forest/Previews'
INFO = json.load(open(os.path.join(HERE, 'out', 'base.json')))
CHK = json.load(open(SCR + 'u5/checks/base_checks.json'))
TEX = os.path.join(HERE, 'tex', 'base')
MSM.OUT, MSM.R, MSM.INFO, MSM.TEX = OUT, R, INFO, TEX
img, sheet, ru, thou, F, INK, DIM, wrap = MSM.img, MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.wrap
u3 = MSR.u3


def atlas_tile(name, label, W=600, H=420):
    import numpy as np
    path = os.path.join(TEX, f'T_Base_{name}_BaseColor.png')
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    side = 380
    tt = a.resize((side, side), Image.NEAREST if s <= side else Image.BOX)
    canvas = Image.new('RGB', (W, H), (10, 10, 12))
    canvas.paste(tt, (12, 30))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 404 + (i % 8) * 23, 40 + (i // 8) * 23
        d.rectangle([x0, y0, x0 + 20, y0 + 20], fill=tuple(int(v) for v in c))
    info = INFO['atlases'].get(name, {})
    d.text((404, 236), f'{s} × {s}', fill=INK, font=F(20, True))
    if info.get('ppm'):
        d.text((404, 264), f'{ru(info["ppm"], 1)} px/м', fill=DIM, font=F(18))
    d.text((404, 290), f'{len(pal)} цветов', fill=DIM, font=F(18))
    d.rectangle([4, 2, 14 + d.textlength(label, font=F(18, True)), 26], fill=(0, 0, 0))
    d.text((8, 4), label, fill=INK, font=F(18, True))
    return canvas


if __name__ == '__main__':
    at = INFO['atlases']
    tb = dict(INFO['tris_by_object'])
    u3t = dict(INFO['u3_tris'])
    sheet('База — люк шахты, ящики, поленница',
          'Люк шахты в бетонном оголовке: оцинкованная рама, рифлёная крышка на двух петлях, кольцевая ручка, проушина '
          'со скобой и навесным замком (заперт, как в обновлении 3), грибок вентиляции, лестница в шахту, табличка '
          'SCHACHT на двух стойках; ящики и поленница на местах обновления 3; день',
          [(img('hatch'), 'люк: оголовок 3 × 3 м, рама, крышка, вентиляция, табличка'),
           (img('hatch_lid'), 'крышка: рифлёный лист, ручка, проушина на скобе, замок'),
           (img('hatch_hinge'), 'петли: накладки на крышке, листы на раме, оси на линии шарнира обновления 3'),
           (img('hatch_open'), 'открыта на 85°: шахта, лестница, тёмное дно'),
           (img('hatch_sign'), 'SCHACHT — ABSTURZGEFAHR / SHAFT - DANGER OF FALLING'),
           (img('map_hatch'), 'на месте, на рельефе обновления 3'),
           (img('crates'), 'ящики: оливковый транспортный, кейс сверху и рядом, два сосновых'),
           (img('crates_back'), 'с другой стороны: ручки, уголки, трафареты'),
           (img('crates_open'), 'открытый сосновый ящик: солома, крышка прислонена'),
           (img('map_crates'), 'на месте у дороги'),
           (img('logs'), 'поленница: девять еловых брёвен обновления 3 на двух лагах, четыре кола'),
           (img('logs_end'), 'торцы: годичные кольца, синие метки лесника')],
          [('Атлас', f'Props {at["Props"]["size"]} ({ru(at["Props"]["ppm"], 1)} px/м) — люк, крышка, ящики, поленница; '
                     f'табличка — панель базы (160 px/м)'),
           ('Треугольников', f'люк {thou(tb["Hatch"])} + крышка {thou(tb["IX_HatchLid_94"])} (обновление 3 — '
                             f'{thou(u3t["Hatch"])}), ящики {thou(tb["Crates"])} ({thou(u3t["Crates"])}), поленница '
                             f'{thou(tb["LogPile"])} ({thou(u3t["LogPile"])})')],
          'base_A_hatch_crates_logs.jpg')
    sheet('База — вертолётная площадка и радиомачта',
          'Площадка: бетонный круг 20,8 м с фаской, H и жёлтое кольцо, восемь огней по краю (включаются с питанием базы), '
          'ветроуказатель, табличка, ящик огнетушителя, поддон под брезентом. Мачта: 60 м, решётчатая, на трёх ярусах '
          'оттяжек, красно-белые пояса, лестница, кабельный лоток, диполи, заградительные огни на 20, 40 и 60 м',
          [(img('helipad'), 'площадка: H, кольцо, огни, ветроуказатель'),
           (img('heli_top'), 'сверху'),
           (img('heli_sock'), 'ветроуказатель: фундамент, мачта с шарниром, кольцо, конус'),
           (img('heli_sign'), 'HUBSCHRAUBERLANDEPLATZ / HELIPAD; ящик огнетушителя'),
           (img('heli_light'), 'огонь края: стойка, корпус, тёплый колпак'),
           (img('heli_pallet'), 'поддон под брезентом, обвязка'),
           (img('map_helipad'), 'на месте, на рельефе обновления 3'),
           (img('map_helipad_night'), 'ночь, питание включено: огни площадки, фонари'),
           (img('mast'), 'мачта 60 м с оттяжками на три анкера'),
           (img('mast_base'), 'основание: фундаменты, лестница, лоток, табличка'),
           (img('mast_top'), 'верх: огонь, громоотвод, диполи'),
           (img('mast_beacon'), 'огни на 20 м на кронштейнах (места обновления 3)'),
           (img('mast_anchor'), 'анкер: бетонный блок, талрепы'),
           (img('mast_sign'), 'VORSICHT EISFALL / BEWARE OF FALLING ICE'),
           (img('map_mast'), 'мачта на месте'),
           (img('map_mast_night'), 'ночь: заградительные огни')],
          [('Атлас', f'Helipad {at["Helipad"]["size"]} ({ru(at["Helipad"]["ppm"], 1)} px/м), Mast {at["Mast"]["size"]} '
                     f'({ru(at["Mast"]["ppm"], 1)} px/м: элементы решётки — короткими кусками)'),
           ('Треугольников', f'площадка {thou(tb["Helipad"])} (обновление 3 — {thou(u3t["Helipad"])}), мачта '
                             f'{thou(tb["RadioMast"])} ({thou(u3t["RadioMast"])})')],
          'base_B_helipad_mast.jpg')
    sheet('База — фонари, линия электропередачи, заборы',
          'Оцинкованные фонари двора (натриевая лампа, гаснет без питания), деревянные опоры с траверсой и тремя '
          'изоляторами, провода линии от трансформатора двора с провисом и спуски кабеля по опорам 2 и 4; секция '
          'рабицы с колючкой на кронштейне и старый пограничный забор из трёх вариантов',
          [(img('lightpole'), 'фонарь: фундамент, плита, лючок, кронштейн, светильник'),
           (img('lightpole_head'), 'светильник: корпус, рассеиватель (M_Lamp_SodiumOff)'),
           (img('lightpole_foot'), 'низ: фундамент, анкерные болты, лючок'),
           (img('map_lights'), 'фонари на местах обновления 3'),
           (img('map_lights_night'), 'ночь, питание включено'),
           (img('powerpole'), 'опора: пропитанное бревно, траверса, подкосы, изоляторы'),
           (img('powerpole_top'), 'верх опоры: изоляторы на высоте обновления 3 (8,72 м)'),
           (img('map_line'), 'линия от трансформатора к опорам 1 и 2'),
           (img('map_line2'), 'опора 2: спуск кабеля, муфты, защитная труба'),
           (img('fences'), 'рабица (213 секций) и старый забор (294 секции)'),
           (img('fence_chain'), 'рабица: стойка, верхняя труба, сетка, кронштейн с колючкой'),
           (img('fence_old'), 'старый забор: столбы с наклоном обновления 3, ржавая колючка, оборванная нить')],
          [('Атлас', f'Poles {at["Poles"]["size"]} ({ru(at["Poles"]["ppm"], 1)} px/м), Fence {at["Fence"]["size"]} '
                     f'({ru(at["Fence"]["ppm"], 1)} px/м); сетка, колючка, ржавая проволока — повторяющиеся вырезки'),
           ('Треугольников', f'фонарь {thou(tb["LightPole"])} (обновление 3 — {thou(u3t["LightPole"])}), опора '
                             f'{thou(tb["PowerPole"])} ({thou(u3t["PowerPole"])}), провода {thou(tb["Forest_Wires"])} '
                             f'({thou(u3t["Forest_Wires"])}), рабица {thou(tb["FenceChain"])} ({thou(u3t["FenceChain"])}), '
                             f'старый забор {thou(tb["OldFence"])}–{thou(tb["OldFence_c"])} ({thou(u3t["OldFence"])})'),
           ('Провода', f'пролёты {", ".join(f"{k} {ru(v, 1)} м" for k, v in CHK["wires"]["spans_m"].items())}; '
                       f'просвет до земли не меньше {ru(CHK["wires"]["min_clearance_terrain_m"], 1)} м')],
          'base_C_poles_line_fences.jpg')
    tiles = []
    for vn, lab in (('cmp_hatch', 'люк'), ('cmp_crates', 'ящики'), ('cmp_logs', 'поленница'), ('cmp_helipad', 'площадка'),
                    ('cmp_mast', 'низ мачты'), ('cmp_lightpole', 'фонарь'), ('cmp_powerpole', 'опора'),
                    ('cmp_fence', 'рабица'), ('cmp_oldfence', 'старый забор')):
        tiles.append((u3(os.path.join(U3R, vn + '.png')), f'обновление 3: {lab}'))
        tiles.append((img(vn), f'теперь: {lab}'))
    tiles.append((u3(os.path.join(U3P, 'Forest_Base.jpg')), 'обновление 3, превью Base (ночь, с деревьями)'))
    tiles.append((img('map_base_night'), 'теперь, та же камера (ночь, с питанием): рельеф и модели пакета'))
    sheet('База — обновление 3 и теперь',
          'Слева — модели обновления 3 (FBX в цветах материалов) и его превью карты, справа — перестроенные с тех же '
          'камер; места, пивоты, шарнир крышки и огни — те же',
          tiles, [], 'base_D_u3_vs_now.jpg')
    tiles = [(atlas_tile(n, f'T_Base_{n}'), None) for n in ('Props', 'Helipad', 'Mast', 'Poles', 'Fence')
             if os.path.exists(os.path.join(TEX, f'T_Base_{n}_BaseColor.png'))]
    pa = Image.open(os.path.join(TEX, 'T_Base_Panel_BaseColor.png')).convert('RGB')
    pt = Image.new('RGB', (600, 420), (10, 10, 12))
    pt.paste(pa.resize((380, 380), Image.NEAREST), (12, 30))
    d = ImageDraw.Draw(pt)
    d.rectangle([4, 2, 230, 26], fill=(0, 0, 0))
    d.text((8, 4), f'T_Base_Panel {pa.size[0]}', fill=INK, font=F(18, True))
    for j, line in enumerate(wrap(d, 'таблички люка, площадки и мачты (сначала по-немецки, под ним по-английски); '
                                     '160 px/м, ночью слабо светятся', F(16), 190)):
        d.text((404, 40 + j * 22), line, fill=DIM, font=F(16))
    tiles.append((pt, None))
    sheet('База — атласы', 'По 64 цвета, AO в цвете, дизеринг 4×4, фильтр «точка»; до 51,3 px/м (генераторная)',
          tiles, [], 'base_E_atlases.jpg', cols=2, W=600, H=420)
