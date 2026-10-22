"""Sheets for the road prefabs: A the signs and the gate, B the bridge and the overlook, C the windfall and the road on
Update 3's terrain, D Update 3 and now (the same cameras; Update 3's in-game previews and the same viewpoints now),
E the atlases and the sign panel.  python3 make_sheets_road.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sheets_main as MSM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'road')
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
U3R = SCR + 'road_checks/u3'
U3P = SCR + 'u3/Assets/Locations/Forest/Previews'
INFO = json.load(open(os.path.join(HERE, 'out', 'road.json')))
TEX = os.path.join(HERE, 'tex', 'road')
MSM.OUT, MSM.R, MSM.INFO, MSM.TEX = OUT, R, INFO, TEX
img, sheet, ru, thou, F, INK, DIM, wrap = MSM.img, MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.wrap


def u3(path):
    if not os.path.exists(path):
        return Image.new('RGB', (900, 600), (40, 10, 10))
    return MSM.fit(Image.open(path).convert('RGB'))


def atlas_tile(name, label, W=600, H=420):
    path = os.path.join(TEX, f'T_Road_{name}_BaseColor.png')
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
    tb = INFO['tris_by_object']
    u3t = INFO['u3_tris']
    sheet('Дорога пролога — указатели и ворота',
          'Немецкие дорожные знаки на оцинкованных стойках (щит с отбортовкой, серая обратная сторона, шины и хомуты), '
          'столбик-отражатель дороги, ворота зоны SPERRGEBIET позади машины; день, ночью — свечение плёнки и отражателей',
          [(img('signs_row'), 'указатели дороги: лица, высоты и стойки обновления 3'),
           (img('signs_row2'), 'и остальные указатели станции (та же конструкция)'),
           (img('sign_obs'), 'RADIOOBSERVATORIUM HOHENMOOS у ворот'),
           (img('sign_obs_back'), 'обратная сторона: RAL 7037, наклейка изготовителя, шины, хомуты'),
           (img('sign_dist23'), 'OBSERVATORIUM 2,3 km — тот самый, что врёт'),
           (img('europost'), 'EuroPost: белый столбик, чёрная полоса, янтарные отражатели'),
           (img('gate_out'), 'ворота: бетонные столбы, створки из труб, рабица, колючка, SPERRGEBIET'),
           (img('gate_in'), 'с другой стороны — щит второй створки'),
           (img('gate_lock'), 'притвор: цепь с навесным замком, шпингалет в стакан в дороге'),
           (img('gate_hinge'), 'петля: закладная пластина, штырь, хомут на стойке'),
           (img('map_gate'), 'на месте, со стороны машины: ворота, указатель, столбики (рельеф обновления 3)'),
           (img('map_gate_night'), 'ночь, в свете фар: щит и отражатели светятся')],
          [('Атлас', f'Signs {at["Signs"]["size"]} ({ru(at["Signs"]["ppm"], 1)} px/м) — стойки и обороты всех указателей и '
                     f'столбик; Gate {at["Gate"]["size"]}; лица — панель 512 (160 px/м)'),
           ('Треугольников', f'указатель {thou(tb["Sign_Observatory"])} (обновление 3 — {thou(u3t["Sign_Observatory"])}), '
                             f'столбик {thou(tb["EuroPost"])}, ворота {thou(tb["ZoneGate"])} (обновление 3 — '
                             f'{thou(u3t["ZoneGate"])})')],
          'road_A_signs_gate.jpg')
    sheet('Дорога пролога — мост и обзорная площадка',
          'Деревянный мост через овраг: доски настила, колеи, бревенчатые прогоны, свайные опоры со связями, перила; '
          'площадка на бровке берега из пропитанной сосны; день',
          [(img('bridge_side'), 'мост 32 м: две свайные опоры до дна оврага'),
           (img('bridge_low'), 'снизу, от ручья'),
           (img('bridge_deck'), 'настил и колеи (машина проезжает — уровни обновления 3)'),
           (img('bridge_end'), 'въезд с запада: клинья колей, знак 7,5 t'),
           (img('bridge_under'), 'под мостом: ригель, обвязки, крестовые связи, стыки прогонов'),
           (img('bridge_bank'), 'восточный берег: лежень, стенка из брёвен, камень'),
           (img('deck_front'), 'площадка: ступени, перила, скамья, бинокль'),
           (img('deck_back'), 'со склона: стойки на фундаментах, раскос, схватки'),
           (img('deck_on'), 'на площадке: вид к озеру (+y)'),
           (img('map_bridge'), 'кадр Bridge на рельефе обновления 3'),
           (img('map_bridge_side'), 'мост над оврагом на рельефе обновления 3'),
           (img('map_deck'), 'площадка на бровке берега, на рельефе обновления 3')],
          [('Атлас', f'Bridge {at["Bridge"]["size"]} ({ru(at["Bridge"]["ppm"], 1)} px/м), Deck {at["Deck"]["size"]} '
                     f'({ru(at["Deck"]["ppm"], 1)} px/м)'),
           ('Треугольников', f'мост {thou(tb["Bridge30"])} (обновление 3 — {thou(u3t["Bridge30"])}), площадка '
                             f'{thou(tb["OverlookDeck"])} (обновление 3 — {thou(u3t["OverlookDeck"])})')],
          'road_B_bridge_deck.jpg')
    sheet('Дорога пролога — бурелом',
          'Сухая ель вырвана с корнем и упала поперёк дороги, распилена ровно по кромкам; выпиленный кусок оттащен на '
          'обочину — от разрыва к нему тянется волок',
          [(img('tree_road'), 'с дороги: разрыв, опилки, вершина справа, бревно на обочине'),
           (img('tree_root'), 'корневая тарелка, яма и отвал'),
           (img('tree_cut'), 'спил комлевой части и опилки у кромки'),
           (img('tree_crown'), 'вершинная часть: сухие мутовки, лишайник'),
           (img('log_cut'), 'выпиленный кусок: спилы с обеих сторон, содранная кора'),
           (img('map_windfall'), 'кадр Windfall на рельефе обновления 3'),
           (img('map_windfall_night'), 'ночью, в свете фар')],
          [('Атлас', f'Windfall {at["Windfall"]["size"]} ({ru(at["Windfall"]["ppm"], 1)} px/м) — ель и бревно'),
           ('Треугольников', f'ель {thou(tb["FallenTree"])}, бревно {thou(tb["LogCut"])}'),
           ('Откуда', 'моделей обновления 3 здесь нет: по README (S4) и кадру Windfall, на точках обновления 3; дорога '
                      'между спилами свободна')],
          'road_C_windfall.jpg')
    tiles = []
    for vn, lab in (('cmp_gate_a', 'ворота'), ('cmp_gate_b', 'ворота с другой стороны'), ('cmp_obs_a', 'указатель у ворот'),
                    ('cmp_dist_a', 'указатель расстояния'), ('cmp_view_a', 'AUSSICHTSPUNKT'), ('cmp_bridge_a', 'мост'),
                    ('cmp_bridge_b', 'мост, настил'), ('cmp_deck_a', 'площадка'), ('cmp_deck_b', 'площадка со склона')):
        tiles.append((u3(os.path.join(U3R, vn + '.png')), f'обновление 3: {lab}'))
        tiles.append((img(vn), f'теперь: {lab}'))
    for vp, vn in (('Forest_Start.jpg', 'map_start'), ('Forest_Bridge.jpg', 'map_bridge'), ('Forest_Windfall.jpg', 'map_windfall')):
        tiles.append((u3(os.path.join(U3P, vp)), f'обновление 3, превью {vp[7:-4]} (ночь, с деревьями)'))
        tiles.append((img(vn), f'теперь, та же камера на рельефе обновления 3 (днём, без деревьев)'))
    sheet('Дорога пролога — обновление 3 и теперь',
          'Слева — модели обновления 3 (FBX в цветах материалов) и его превью карты, справа — перестроенные с тех же '
          'камер; места, размеры и уровни — те же',
          tiles, [], 'road_D_u3_vs_now.jpg')
    tiles = [(atlas_tile(n, f'T_Road_{n}'), None) for n in ('Signs', 'Gate', 'Bridge', 'Deck', 'Windfall')
             if os.path.exists(os.path.join(TEX, f'T_Road_{n}_BaseColor.png'))]
    pa = Image.open(os.path.join(TEX, 'T_Road_Panel_BaseColor.png')).convert('RGB')
    pt = Image.new('RGB', (600, 420), (10, 10, 12))
    pt.paste(pa.resize((380, 380), Image.NEAREST), (12, 30))
    d = ImageDraw.Draw(pt)
    d.rectangle([4, 2, 230, 26], fill=(0, 0, 0))
    d.text((8, 4), 'T_Road_Panel 512', fill=INK, font=F(18, True))
    for j, line in enumerate(wrap(d, 'лица указателей (сначала по-немецки, под ним по-английски), SPERRGEBIET — знак '
                                     'КПП, 7,5 t; 160 px/м, ночью слабо светятся', F(16), 190)):
        d.text((404, 40 + j * 22), line, fill=DIM, font=F(16))
    tiles.append((pt, None))
    sheet('Дорога пролога — атласы', 'По 64 цвета, AO в цвете, дизеринг 4×4, фильтр «точка»; 51,3 px/м (генераторная)',
          tiles, [], 'road_E_atlases.jpg', cols=2, W=600, H=420)
