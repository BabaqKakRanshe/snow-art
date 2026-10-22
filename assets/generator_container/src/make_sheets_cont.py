"""Sheets for the generator container: A outside and inside, B the mechanics up close, C points, colliders, textures,
light.  python3 make_sheets_cont.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
import make_sheets_van2 as MS
import make_sheets_van3 as M3

HERE = MS.HERE
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
os.makedirs(OUT, exist_ok=True)
M3.OUT = MS.OUT = OUT
M3.R3 = os.path.join(HERE, 'rend', 'cont')
INFO = json.load(open(os.path.join(HERE, 'out', 'cont.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'cont_contract.json')))
LIGHTS = json.load(open(os.path.join(HERE, 'out', 'cont_lights.json')))['lights']
TEX = os.path.join(HERE, 'tex', 'cont')
img, plural, ru = M3.img, MS.plural, MS.ru


def legend_tile(view, title, entries):
    im = img(view).copy()
    d = ImageDraw.Draw(im)
    f = MS.F(19)
    y = 560 - 28 * len(entries)
    for col, text in entries:
        d.rectangle([14, y, 32, y + 18], fill=col)
        w = d.textlength(text, font=f)
        d.rectangle([36, y - 2, 44 + w, y + 20], fill=(0, 0, 0))
        d.text((40, y - 1), text, fill=MS.INK, font=f)
        y += 28
    return im


def atlas_tile(path, label, ppm=None, note=None):
    """make_sheets_van2.atlas_tile that also fits a 1024 atlas: shrunk (box filter) to 560 for the preview, its real size
    and palette in the key"""
    a = Image.open(path).convert('RGB')
    s = a.size[0]
    t = a.resize((s * max(1, 560 // s),) * 2, Image.NEAREST) if s <= 560 else a.resize((560, 560), Image.BOX)
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(t, ((900 - t.width) // 2 - 120, (600 - t.height) // 2 + 10))
    pal = np.unique(np.asarray(a).reshape(-1, 3), axis=0)
    pal = pal[np.argsort(pal @ np.array([0.3, 0.59, 0.11]))]
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(pal[::max(1, len(pal) // 64)][:64]):
        x0, y0 = 690 + (i % 8) * 24, 60 + (i // 8) * 24
        d.rectangle([x0, y0, x0 + 21, y0 + 21], fill=tuple(int(v) for v in c))
    d.text((690, 270), f"{s} × {s} px", fill=MS.INK, font=MS.F(22, True))
    yy = 302
    if ppm:
        d.text((690, yy), f"{ru(ppm, 1)} px/м", fill=MS.DIM, font=MS.F(20))
        yy += 28
    d.text((690, yy), f"{len(pal)} цветов", fill=MS.DIM, font=MS.F(20))
    if note:
        for j, line in enumerate(MS.wrap(d, note, MS.F(18), 190)):
            d.text((690, yy + 40 + j * 24), line, fill=MS.DIM, font=MS.F(18))
    MS.tag(canvas, label)
    return canvas


def panel_tile():
    a = Image.open(os.path.join(TEX, 'T_GCont_Panel_BaseColor.png')).convert('RGB')
    e = Image.open(os.path.join(TEX, 'T_GCont_Panel_Emission.png')).convert('RGB')
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    canvas.paste(a.resize((512, 512), Image.NEAREST), (20, 60))
    canvas.paste(e.resize((320, 320), Image.NEAREST), (560, 60))
    d = ImageDraw.Draw(canvas)
    d.text((560, 390), 'эмиссия: горящие лампы', fill=MS.INK, font=MS.F(19))
    d.text((560, 420), 'и светящиеся деления шкал', fill=MS.DIM, font=MS.F(19))
    MS.tag(canvas, 'T_GCont_Panel 512: шкалы, панели, таблички (нем. / англ.), трафареты, журнал')
    return canvas


def cookies_tile():
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    for i, (key, lab) in enumerate((('bulkhead', 'лампа в решётке: 160°, шесть теней от прутьев'),
                                    ('barnlight', 'фонарь над дверями: абажур режет на 72°'))):
        im = Image.open(os.path.join(TEX, 'Cookies', 'T_Cookie_%s.png' % key)).convert('L').resize((380, 380), Image.BILINEAR)
        canvas.paste(Image.merge('RGB', (im, im, im)), (40 + i * 440, 70))
        for j, line in enumerate(MS.wrap(d, lab, MS.F(19), 380)):
            d.text((40 + i * 440, 470 + j * 26), line, fill=MS.INK, font=MS.F(19))
    MS.tag(canvas, 'форма света (cookie = IES): T_Cookie_bulkhead, T_Cookie_barnlight')
    return canvas


if __name__ == '__main__':
    P_, S_ = CON['parts'], CON['sockets']
    kinds = {}
    for p in P_.values():
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    moving = len(P_) - kinds.get('static', 0)
    n_hand = sum(1 for s in S_.values() if s['kind'] == 'hand')
    at = INFO['atlases']
    tris = INFO['tris']
    dr = INFO.get('drift', {}).get('clear_min', '?')
    a = M3.sheet('Генераторная в контейнере · снаружи и внутри',
                 f'два 20-футовых контейнера, внутри — генераторная целиком; '
                 f'{moving} {plural(moving, "подвижная деталь", "подвижные детали", "подвижных деталей")}, '
                 f'{len(S_)} {plural(len(S_), "точка", "точки", "точек")}, '
                 + f'{tris:,}'.replace(',', ' ') + f' {plural(tris, "треугольник", "треугольника", "треугольников")}',
                 [(img('ext_day'), 'днём: рабочие двери в западном торце южного контейнера, окно с решёткой, мачта ввода'),
                  (img('ext_night'), 'ночью: фонарь над дверями, створка приоткрыта, внутри горит свет'),
                  (img('ext_east'), 'передний торец: жалюзи радиатора открыты, труба с заслонкой'),
                  (img('ext_open'), 'обе створки открыты (штанги выведены, замок снят)'),
                  (img('snow'), f'снег на крышах и сугроб у дверей (блендшейпы Clear, по умолчанию скрыты; створки проходят с Clear {dr})'),
                  (img('int_door'), 'внутри от дверей: генератор работает, щит на GEN, свет на автомате 8'),
                  (img('int_day'), 'днём, двери открыты: щит справа, генератор, бак и бочки у северной стены')],
                 [('Контейнеры', '6,06 × 4,88 м, внутри 5,80 × 4,69, до профлиста 2,37, под балками 2,25; общие стенки '
                                 'вырезаны; гофростены, фитинги, опоры, ступенька; сине-серая краска (южный чуть синее), '
                                 'ржавчина, маркировка'),
                  ('Внутри', 'отделка генераторной: фанера (швы листов, гвозди, грязь внизу, копоть у выхлопа), бетонный пол '
                             '(масло, натоптано от дверей, рифлёные крышки кабельного канала, медные трубки на скобах), '
                             'еловые балки с шагом стропил под изнанкой профлиста, доски на створках, белое окно со ставнем; '
                             'покрашено теми же правилами, что в генераторной'),
                  ('Двери', 'у каждой створки две штанги с ручками, кулачки в упорах вверху и внизу; замок на ручке рабочей '
                            'створки, засов изнутри; ключ на крючке за углом на южной стене; двери северного контейнера '
                            'заварены, в них два воздухозаборника; сугроб держит створки'),
                  ('Свет', f'{len(LIGHTS)} {plural(len(LIGHTS), "лампа", "лампы", "ламп")}: три в решётке (над пультом, '
                           'над баком и бочками, над щитом) на автомате 8 и выключателе у двери, фонарь над дверями на '
                           'автомате 2; IES-профили и cookie; свет есть, только когда шины под напряжением'),
                  ('Атласы', f'весь контейнер — один атлас, как у генераторной: {at["Cont"]["size"]} (стены снаружи '
                             f'{ru(at["Cont"]["ppm_parts"]["walls outside"], 1)}, внутри '
                             f'{ru(at["Cont"]["ppm_parts"]["inside (ply, floor, timber, roof underside)"], 1)} пикс/м, у генераторной 51), '
                             f'генератор {at["Genset"]["size"]} '
                             f'({ru(at["Genset"]["ppm"], 1)}), вещи {at["Props"]["size"]} ({ru(at["Props"]["ppm"], 1)}), '
                             f'снег {at["Snow"]["size"]}, панель 512; по 64 цвета, AO в цвете, дизеринг 4×4')],
                 'cont_A.jpg')
    b = M3.sheet('Генераторная в контейнере · механика вблизи',
                 'оборудование генераторной без изменений: у каждого рычага, крана, пробки, кнопки и автомата своя ось; '
                 f'{n_hand} {plural(n_hand, "точка", "точки", "точек")} для руки',
                 [(img('int_panel'), 'пульт: шесть приборов, счётчик моточасов, пять ламп, ключ, GLOW, STOP, грибок, V ADJ'),
                  (img('int_board'), 'щит: дверца открыта, переключатель на GEN, вводной и автоматы 1, 2, 8 включены'),
                  (img('int_fuel'), 'расходный бак у северной стены: пробка, стекло со шкалой, кран подачи открыт, поддончик'),
                  (img('int_drums'), 'бочки на поддоне: насос в зимней солярке, шланг свёрнут, воздушник открыт'),
                  (img('int_service'), 'топливная сторона: водоотделитель, подкачка, фильтр с винтом прокачки, ТНВД, АКБ'),
                  (img('int_radiator'), 'охлаждение: вентилятор в кожухе, радиатор с пробкой; рукав к жалюзи в торце'),
                  (img('int_north'), 'северная половина: полка, огнетушитель и выключатель у двери, бак, трубки по полу'),
                  (img('plan'), 'план без крыши (север сверху)')],
                 [('Пульт', 'ключ OFF / ON / START (пружина назад в ON, вынимается в OFF), GLOW — свечи 20 с, STOP — '
                            'отсечка, аварийный грибок фиксируется; стрелки со шкалами в контракте, лампы GLOW, CHG, OIL, TEMP, RUN'),
                  ('Двигатель', 'щуп и маслозаливная, пробка и сливной краник радиатора, крышка воздушного фильтра, ручной '
                                'стоп и регулятор на ТНВД, винт прокачки, подкачка, краник водоотделителя, топливный фильтр '
                                '(запасной на полке), ремень (ok / ослаб / порван), вентилятор крутится'),
                  ('Щит', 'дверца на замке-вертушке, переключатель LINE / OFF / GEN, вводные GEN и LINE, восемь автоматов '
                          '(восьмой — CONTAINER), три прибора, счётчик, три лампы; карточка цепей внутри дверцы'),
                  ('Топливо', 'бак 100 л у северной стены; медные трубки идут по полу на скобах под раму генератора; бочки: '
                              'зимняя, летняя (парафинится), бензин для фургона; насос переставляется, шланг 3,5 м'),
                  ('Перенос', 'генератор, щит, бак, бочки, полка, огнетушитель, журнал и коврик — из генератор­ной, '
                              'расставлены группами; щит и журнал на южной стене, бак и бочки на северной, полка и '
                              'огнетушитель у двери, генератор радиатором к жалюзи')],
                 'cont_B.jpg')
    kinds_s = {}
    for s in S_.values():
        kinds_s[s['kind']] = kinds_s.get(s['kind'], 0) + 1
    KC = {'hand': ((255, 216, 26), 'рука'), 'pour': ((51, 128, 255), 'залив'), 'item_slot': ((51, 230, 77), 'гнездо'),
          'audio': ((230, 51, 230), 'звук'), 'vfx': ((255, 115, 26), 'эффект'), 'hide': ((26, 230, 230), 'укрытие'),
          'knock': ((242, 38, 38), 'стук'), 'heat': ((255, 128, 153), 'тепло')}
    ent = [(c, f'{t} — {kinds_s.get(k, 0)}') for k, (c, t) in KC.items() if kinds_s.get(k)]
    c = M3.sheet('Генераторная в контейнере · точки, коллайдеры, текстуры',
                 f'{len(S_)} {plural(len(S_), "сокет", "сокета", "сокетов")}, {len(CON["colliders"])} '
                 f'{plural(len(CON["colliders"]), "коробка-коллайдер", "коробки-коллайдера", "коробок-коллайдеров")}, атласы и форма света',
                 [(legend_tile('points_plan', 'точки', ent), 'точки взаимодействия сверху (крыша снята)'),
                  (img('colliders_plan'), 'коллайдеры сверху (крыша, пол и балки не показаны)'),
                  (atlas_tile(os.path.join(TEX, 'T_GCont_Cont_BaseColor.png'), 'T_GCont_Cont', at['Cont']['ppm'],
                                 'весь контейнер: снаружи стены, двери, крыши, фитинги; внутри фанера, бетон, балки, окно; '
                                 f'стены {ru(at["Cont"]["ppm_parts"]["inside (ply, floor, timber, roof underside)"], 1)} px/м '
                                 '(крыша и днище реже)'), None),
                  (atlas_tile(os.path.join(TEX, 'T_GCont_Genset_BaseColor.png'), 'T_GCont_Genset', at['Genset']['ppm'],
                                 'двигатель, радиатор, выхлоп, генератор, рама, АКБ, рукав'), None),
                  (atlas_tile(os.path.join(TEX, 'T_GCont_Props_BaseColor.png'), 'T_GCont_Props', at['Props']['ppm'],
                                 'щит, бак, бочки, поддон, насос, полка, огнетушитель, замок, ключ'), None),
                  (panel_tile(), None), (cookies_tile(), None)],
                 [('Точки', 'рука — где брать деталь; залив — горловины; гнёзда — АКБ, фильтр, насос в бочке, замок, ключ, '
                            'огнетушитель, журнал, розетка, вводы LINE и фидера; звук — двигатель, генератор, вентилятор, '
                            'труба, жалюзи, двери, крыша, ветер, щит; эффекты — дым, пар, прокачка, слив, искры, тёплый '
                            'воздух из жалюзи, снег в дверях; укрытия — в углу за полкой и под окном; стук — по стенам, '
                            'створкам, окну, жалюзи, крыше снаружи'),
                  ('Коллайдеры', 'стены кусками вокруг окна и жалюзи, пол и крыша плитами (крыша — от низа балок), стойки и '
                                 'балка дверного проёма, опоры, ступенька, труба; генератор, щит и его дверца, бак, бочки, '
                                 'поддон, полка; у створок и ставня — свои, едут с ними'),
                  ('Unity', 'система координат контейнера: x — восток, y — север, z — вверх; позиция в Unity (−y, z, x), '
                            'угол → −угол; подробности и привязка к Forest — GENCONT_CONTRACT.md (в проекте — '
                            'docs/gdd/GENCONT_CONTRACT.md)')],
                 'cont_C.jpg', cols=2)
    print(a, b, c)
