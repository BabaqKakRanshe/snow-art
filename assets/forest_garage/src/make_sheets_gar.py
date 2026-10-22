"""Sheets for the garage: A outside by day (and the gate / the door open), B inside with Update 3's lights, C Update 3's
model vs now (the same cameras), D the atlases and the panel.
python3 make_sheets_gar.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sheets_main as MSM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
R = os.path.join(HERE, 'rend', 'garage')
U3R = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/garage/u3'
INFO = json.load(open(os.path.join(HERE, 'out', 'garage.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'garage_contract.json')))
TEX = os.path.join(HERE, 'tex', 'garage')
MSM.OUT, MSM.R, MSM.INFO, MSM.TEX = OUT, R, INFO, TEX
img, sheet, ru, thou, F, INK, DIM, wrap = MSM.img, MSM.sheet, MSM.ru, MSM.thou, MSM.F, MSM.INK, MSM.DIM, MSM.wrap


def u3(f):
    return MSM.fit(Image.open(os.path.join(U3R, f)).convert('RGB'))


def atlas_tile(name, label, W=600, H=420):
    path = os.path.join(TEX, f'T_Gar_{name}_BaseColor.png')
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
    sheet('Гараж — снаружи',
          'Стальной ангар станции: профлист в серо-зелёной краске на бетонном цоколе, тёмные уголки и обрамления, '
          'плоская кровля со свесом и кромкой, водостоки, въезд; день',
          [(img('ext_sw'), 'с юго-запада: ворота, табличка GARAGE и лампа, въезд'),
           (img('ext_se'), 'с юго-востока: окно, боковая дверь, ступень'),
           (img('ext_ne'), 'с северо-востока: дверь, водостоки'),
           (img('ext_nw'), 'с северо-запада: северное окно, водостоки'),
           (img('ext_gate'), 'ворота: рёбра полотна, Т-ручка, AUSFAHRT FREIHALTEN, упоры рамы'),
           (img('ext_side_open'), 'боковая дверь открыта наружу (100°)'),
           (img('ext_gate_open'), 'ворота открыты (85°): полотно под направляющими'),
           (img('ext_roof'), 'кровля: рубероид, швы, мох и хвоя у бортика, кромка'),
           (img('ext_corner'), 'угол: цоколь, отлив, уголок, профиль'),
           (img('ext_win'), 'окно: рама с импостом, обрамление, отлив')],
          [('Атлас', f'Bld {at["Bld"]["size"]} — снаружи и внутри в одном, как у генераторной ({ru(at["Bld"]["ppm"], 1)} '
                     'px/м — плотность генераторной, кровля сжата на четверть), ворота и дверь — Parts '
                     + f'{at["Parts"]["size"]} ({ru(at["Parts"]["ppm"], 1)} px/м)'),
           ('Треугольников', f'{thou(INFO["tris"])}: Garage {thou(tb.get("Garage", 0))}, ворота '
                             f'{thou(tb.get("IX_GarageDoor_92", 0))}, дверь {thou(tb.get("IX_GarageSideDoor_93", 0))} '
                             '(в обновлении 3 — 5,7 тыс.)'),
           ('Место', 'Forest: p (379,691, 16,4452, −400,9222), поворот 8° — как в обновлении 3')],
          'gar_A_outside.jpg')
    sheet('Гараж — внутри',
          'Кассеты на стенах, профнастил и балки под потолком, бетонный пол; содержимое обновления 3 на своих местах; '
          'свет — источники обновления 3 (станция под питанием)',
          [(img('in_gate'), 'к воротам: бочки на поддоне, квадроцикл, стеллаж'),
           (img('in_back'), 'от ворот: верстак, щиток, огнетушитель, боковая дверь'),
           (img('in_west'), 'запад: стеллаж с коробками, ящики, покрышки'),
           (img('in_east'), 'восток: боковая дверь, щиток, бочки'),
           (img('in_bench'), 'верстак: тиски, перфорированная доска с инструментом, календарь'),
           (img('in_drums'), 'бочки на поддоне-ванне, канистры, знаки'),
           (img('in_ceiling'), 'потолок: профнастил, балки IPE 300, светильники, проводка'),
           (img('night_front'), 'ночью с питанием: лампа над воротами')],
          [('Атлас', f'Bld {at["Bld"]["size"]} ({ru(at["Bld"]["ppm"], 1)} px/м), таблички — панель 512'),
           ('Свет', 'два потолочных светильника (M_Lamp_FluorOff) и лампа над воротами (M_Lamp_BulbOff) — там, где '
                    'источники и ореолы обновления 3')],
          'gar_B_inside.jpg')
    tiles = []
    for a_, b_, lab in (('garage_sw.png', 'cmp_sw', 'с юго-запада'), ('garage_se.png', 'cmp_se', 'с юго-востока'),
                        ('garage_ne.png', 'cmp_ne', 'с северо-востока'), ('garage_nw.png', 'cmp_nw', 'с северо-запада'),
                        ('garage_in1.png', 'cmp_in1', 'зал от ворот (обновление 3 — без крыши)'),
                        ('garage_in2.png', 'cmp_in2', 'зал от верстака (обновление 3 — без крыши)')):
        tiles.append((u3(a_), f'обновление 3: {lab}'))
        tiles.append((img(b_), f'теперь: {lab}'))
    sheet('Гараж — обновление 3 и теперь',
          'Слева — модель обновления 3 (Garage.fbx в цветах материалов), справа — перестроенный гараж с близких ракурсов; '
          'двери, окна, свет и содержимое — на тех же местах',
          tiles, [], 'gar_C_u3_vs_now.jpg')
    tiles = [(atlas_tile(n, f'T_Gar_{n}'), None) for n in ('Bld', 'Parts')
             if os.path.exists(os.path.join(TEX, f'T_Gar_{n}_BaseColor.png'))]
    pa = Image.open(os.path.join(TEX, 'T_Gar_Panel_BaseColor.png')).convert('RGB')
    pt = Image.new('RGB', (600, 420), (10, 10, 12))
    pt.paste(pa.resize((380, 380), Image.NEAREST), (12, 30))
    d = ImageDraw.Draw(pt)
    d.rectangle([4, 2, 230, 26], fill=(0, 0, 0))
    d.text((8, 4), 'T_Gar_Panel 512', fill=INK, font=F(18, True))
    for j, line in enumerate(wrap(d, 'таблички (сначала по-немецки, под ним по-английски), пиктограммы F001 и P002, '
                                     'этикетки оборудования (по-английски), календарь, бумага', F(16), 190)):
        d.text((404, 40 + j * 22), line, fill=DIM, font=F(16))
    tiles.append((pt, None))
    sheet('Гараж — атласы', 'По 64 цвета, AO в цвете, дизеринг 4×4, фильтр «точка»; снаружи и внутри — 51,3 px/м '
          '(генераторная), ворота и дверь — 64', tiles, [], 'gar_D_atlases.jpg', cols=2, W=600, H=420)
