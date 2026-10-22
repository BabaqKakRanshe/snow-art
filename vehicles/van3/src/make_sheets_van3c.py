"""Sheets for the van v3, phase 2: G wheels, snow, cold start, colliders; H stove, radio, glovebox, windows, points.
python3 make_sheets_van3c.py [out_dir]"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
import make_sheets_van2 as MS
import make_sheets_van3 as M3

HERE = MS.HERE
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'sheets')
M3.OUT = OUT
INFO = json.load(open(os.path.join(HERE, 'out', 'van3.json')))
CON = json.load(open(os.path.join(HERE, 'out', 'van3_contract.json')))
img = M3.img
TEX = os.path.join(HERE, 'tex', 'van3')


def mask_tile(name, title, amounts, glass=(0.20, 0.24, 0.27), label='снег'):
    a = np.asarray(Image.open(os.path.join(TEX, name)).convert('RGBA'), np.float32) / 255
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    g = np.array(glass, np.float32)
    for i, f in enumerate(amounts):
        m = (a[..., 3] > 1 - f)[..., None]
        im = np.where(m, a[..., :3], g)
        t = Image.fromarray((im * 255).astype(np.uint8)).resize((400, 200), Image.NEAREST)
        x, y = 40 + (i % 2) * 440, 60 + (i // 2) * 260
        canvas.paste(t, (x, y))
        d.text((x, y + 206), f'{label} {int(f * 100)} %', fill=MS.INK, font=MS.F(20))
    MS.tag(canvas, title)
    return canvas


def fog_tile():
    """fogged glass at two amounts and the hand print atlas"""
    a = np.asarray(Image.open(os.path.join(TEX, 'T_Van_Fog.png')).convert('RGBA'), np.float32) / 255
    hp = Image.open(os.path.join(TEX, 'T_Van_Handprints.png')).convert('RGBA')
    canvas = Image.new('RGB', (900, 600), (10, 10, 12))
    d = ImageDraw.Draw(canvas)
    g = np.array((0.08, 0.09, 0.10), np.float32)
    for i, f in enumerate((0.45, 0.85)):
        m = (a[..., 3] > 1 - f)[..., None]
        im = np.where(m, a[..., :3], g)
        t = Image.fromarray((im * 255).astype(np.uint8)).resize((400, 200), Image.NEAREST)
        canvas.paste(t, (40, 60 + i * 260))
        d.text((40, 60 + i * 260 + 206), f'запотело на {int(f * 100)} %', fill=MS.INK, font=MS.F(20))
    al = np.asarray(hp, np.float32)[..., 3] / 255
    t = Image.fromarray((np.dstack([al] * 3) * 230 + 12).astype(np.uint8)).resize((360, 360), Image.NEAREST)
    canvas.paste(t, (500, 80))
    d.text((500, 450), 'атлас отпечатков 2 × 2', fill=MS.INK, font=MS.F(20))
    MS.tag(canvas, 'T_Van_Fog и T_Van_Handprints (UV-слой FOG)')
    return canvas


if __name__ == '__main__':
    n_nuts = sum(1 for k in CON['parts'] if '_Nut_' in k)
    n_col = len(CON.get('colliders', []))
    n_box = sum(1 for p in CON['parts'].values() if 'box' in p)
    g = M3.sheet('Фургон v3 · колёса, снег, холодный пуск',
                 'менять колесо, надевать цепи, счищать снег, греть мотор паяльной лампой; коллайдеры для езды с людьми внутри',
                 [(img('wheel_change'), 'замена колеса: домкрат под мостом, гайки на снегу, запаска'),
                  (img('chains'), 'цепи на заднем колесе, сумка с цепями'),
                  (img('snow_cover'), 'снег на крыше, козырьке, бампере и фарах'),
                  (img('cold_start'), 'холодный пуск: паяльная лампа под поддоном, чайник'),
                  (img('colliders'), 'коллайдеры: полый короб, двери, всё внутри (крыша снята)'),
                  (mask_tile('T_Van_Snow.png', 'снег на лобовом стекле (T_Van_Snow, UV 0…1)', (0.25, 0.5, 0.75, 0.95)), None)],
                 [('Колёса', 'каждое колесо — своя деталь с центром на ступице; передние сидят на шарнирах Steer_FL/FR, '
                             'связанных с рулём (передаточное 16,875, ±32°); радиус 0,364, ширина 0,343, ход подвески '
                             '0,10 м — для WheelCollider; блендшейп Flat — спущенная шина'),
                  ('Замена колеса', f'{n_nuts} {MS.plural(n_nuts, "гайка", "гайки", "гаек")} — по шесть на колесо, по три оборота баллонником; точки под домкрат '
                                    'под обоими мостами: домкрат с винтом достаёт до моста и поднимает колесо на 6–8 см; '
                                    'запаска — то же колесо на кронштейне правой задней двери, держит барашек'),
                  ('Снег', 'на крыше, козырьке и бампере — блендшейп Clear (100 = снега нет); снег над люком не даёт его '
                           'открыть; шапки на фарах, противотуманках и прожекторах гасят свет (× (1 − 0,85 × снег)); '
                           'щётка со скребком в кармане двери пассажира; маска снега на лобовом'),
                  ('Цепи', 'сумка с цепями на правой задней арке под сиденьем R1; цепи для каждого колеса скрыты, пока их '
                           'не надели, и крутятся вместе с колесом'),
                  ('Холодный пуск', 'на ночь открыть сливной краник на блоке (под кожухом); утром дрова в печку, чайник на '
                                    'огонь, паяльная лампа (насос, вентиль) — пламенем под поддон, кипяток в радиатор; '
                                    'первую минуту из трубы валит белый пар; выхлоп с глушителем добавлен'),
                  ('Коллайдеры', f'{n_col} {MS.plural(n_col, "коробка", "коробки", "коробок")}: полый короб для езды с людьми внутри (пол, стены, крыша из четырёх '
                                 f'частей вокруг проёма вентиляционного люка), двери и лестница двигаются со своими '
                                 f'объектами, внутри арки, сиденья, стол, печка, ящики; снаружи бамперы и настил багажника с вырезом над люком. '
                                 f'У {n_box} {MS.plural(n_box, "подвижной детали", "подвижных деталей", "подвижных деталей")} своя коробка захвата в их системе')],
                 'van3_G_wheels_snow.jpg')
    lamps = json.load(open(os.path.join(HERE, 'out', 'van3_lights.json')))['lights']
    hides = sum(1 for s in CON['sockets'].values() if s['kind'] == 'hide')
    knocks = sum(1 for s in CON['sockets'].values() if s['kind'] in ('knock', 'decal'))
    audio = sum(1 for s in CON['sockets'].values() if s['kind'] in ('audio', 'vfx'))
    h = M3.sheet('Фургон v3 · печка, связь, укрытия',
                 'печка топится, рация и сигнал, бардачок, окна сдвигаются и запотевают; точки для звуков и пряток',
                 [(img('stove_open'), 'печка: дверца открыта, огонь, полено, зольник'),
                  (img('radio_glovebox'), 'тангента на шнуре; бардачок: карта, журнал, фонарь, фальшфейеры'),
                  (img('cab_window'), 'окно водителя сдвинуто назад, сигнал на ступице руля'),
                  (img('fog_windows'), 'запотевшие окна салона, отпечаток ладони снаружи'),
                  (img('points_plan'), 'вид сверху: зелёные — укрытия (глаза), синие и бирюзовые — звук и эффекты, красные — стук и отпечатки'),
                  (fog_tile(), None)],
                 [('Печка', 'дверца на петлях, поддувало, заслонка трубы (закрыть рано — дым в салоне), зольник, четыре '
                            'полена в ящике, чайник; огонь — эффект Fire_Stove, свечение в дверце и лампа печки'),
                  ('Сигнал и рация', 'сигнал — накладка на ступице руля, на звук идут к машине в метель; рация: питание и '
                                     'громкость, шумоподавитель, канал вверх и вниз, дисплей с UV-слоем RT под живую '
                                     'текстуру; тангента с кнопкой на крючке, точки для витого шнура'),
                  ('Бардачок', 'крышка откидывается; внутри карта с маршрутом до базы, путевой журнал прежнего экипажа, '
                               'фонарь (лампа torch, узкий луч) и три фальшфейера (лампа flare, красная, около минуты)'),
                  ('Окна', 'передние половины окон в дверях кабины сдвигаются назад на 30 см; у всех боковых и задних '
                           'стёкол UV-слой FOG 0…1: маска запотевания и атлас отпечатков ладоней'),
                  ('Звук и стук', f'{audio} {MS.plural(audio, "точка", "точки", "точек")} звука и эффектов (мотор, печка, вентилятор, дворники, рация, сигнал, '
                                  f'шины, выхлоп, пар, огонь, слив), {knocks} {MS.plural(knocks, "точка", "точки", "точек")} стука и отпечатков на крыше, стенах, '
                                  f'дверях и окнах — с нормалью наружу'),
                  ('Укрытия', f'{hides} {MS.plural(hides, "точка", "точки", "точек")}: в ногах водителя и пассажира, на сиденье пассажира, на откидных L2–L3, на полу '
                              f'салона, у задних дверей; поза, глаза и взгляд — глаза ниже окон'),
                  ('Свет', f'{len(lamps)} {MS.plural(len(lamps), "лампа", "лампы", "ламп")}: добавились фонарь и три фальшфейера — едут со своими предметами; огонь печки '
                           f'(LIGHT_Stove, мерцает, с закрытой дверцей тусклее) и подвесная лампа над столом (тумблер '
                           f'«салон») теперь тоже в списке ламп')],
                 'van3_H_coop_horror.jpg')
    print(g)
    print(h)
