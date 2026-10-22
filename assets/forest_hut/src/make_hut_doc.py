"""Russian reference for the forester's hut: out/hut_contract.json + out/hut_lights.json + out/hut.json ->
docs/HUT_CONTRACT.md.  python3 make_hut_doc.py [out.md]"""
import os, sys, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'out', 'hut_contract.json')))
L = json.load(open(os.path.join(HERE, 'out', 'hut_lights.json')))['lights']
INFO = json.load(open(os.path.join(HERE, 'out', 'hut.json')))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'docs', 'HUT_CONTRACT.md')
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def fv(v, n=3):
    return '(' + ', '.join(f'{a:.{n}f}'.rstrip('0').rstrip('.').replace('-0', '−0').replace('-', '−') if a != 0 else '0' for a in v) + ')'


def num(a, n=2):
    s = f'{a:.{n}f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',').replace('-', '−')


KIND = {'hinge': 'петля', 'slide': 'выдвигается', 'item': 'предмет', 'static': 'неподвижно', 'twist': 'крутится'}
SOCK = {'hand': 'рука', 'pour': 'залив', 'item_slot': 'место вещи', 'audio': 'звук', 'vfx': 'эффект', 'knock': 'стук',
        'hide': 'укрытие', 'seat': 'сесть', 'climb': 'лестница'}
RU = {
    'TowerHut': 'хижина: камни-опоры, обвязка, пол, стены с проёмами двери и окна, фронтоны, стропила, прогоны, затяжки, крыша, '
                'наличники, печка и труба, мебель, полки, вешалка, кронштейн фонаря, поленница, бочка, колода, лавка, лестница '
                'на крышу; корень префаба (тот же, что TowerHut на карте)',
    'IX_HutDoor_1': 'дверь из досок на кованых петлях снаружи, белая Z-обвязка, железная скоба снаружи и деревянная ручка '
                    'внутри; открывается наружу (+), до 105°; то же имя, сторона петель и ход, что в обновлении 3; на старте '
                    'пролога открыта',
    'Window_Glass': 'стекло окна (материал стекла, обе стороны)',
    'Window_Shutter': 'внутренний ставень окна, петли у переднего края: 0 — откинут на стену к двери, 180 — закрывает окно; '
                      'держит вертушка Window_Latch',
    'Window_Latch': 'вертушка на стене за окном: 90 — поперёк края закрытого ставня',
    'Stove_Door': 'дверца топки: открыть (+), заложить дрова и растопку (Slot_Stove_Fire); когда печка горит, огонь виден в '
                  'прорезях',
    'Stove_Damper': 'задвижка на трубе: 0 — открыта (плоская ручка вдоль трубы), 90 — закрыта (поперёк: огонь душит, дым в '
                    'комнате)',
    'Hut_Props': 'мелочи: банки, банка с вареньем, коробка, бутылка, верёвка (полки), свеча, кружка (стол), куртка и шляпа '
                 '(вешалка), сапоги, рога на фронтоне',
    'Kettle': 'эмалированный чайник 1,5 л на плите: налить в бочке, вскипятить на печке',
    'Hut_Panel': 'карта района на задней стене над нарами (обсерватория обведена красным) и календарь — октябрь, дни '
                 'зачёркнуты до 16-го (дата записки лесника)',
    'Lantern': 'фонарь «летучая мышь» (керосин) на кронштейне справа от двери: горит на старте (его видно с машины между '
               'ёлками, 92 м), гаснет насовсем, когда берут канистру (X01)',
    'Lens_Lantern': 'стеклянная колба фонаря: M_Hut_Lamp_Lantern, пока горит, M_Hut_Lamp_Lantern_Off после X01',
    'Glow_Lantern': 'ореол вокруг пламени — три скрещённые карточки, аддитивный неосвещаемый материал без теней (как '
                    'M_Glow_Lantern в обновлении 3); скрыть, когда фонарь погас',
    'Lamp_Oil': 'керосиновая лампа под коньком на цепочке, на старте не горит (LIGHT_OilLamp, группа hut)',
    'Lens_OilLamp': 'стекло лампы (светится вместе с LIGHT_OilLamp)',
    'Axe': 'топор, воткнутый в колоду: вытащить (удерживая), колоть дрова; оружием не служит',
    'Sign_Forsthuette': 'вывеска FORSTHÜTTE / FORESTER\'S HUT на двух столбах у тропы — отдельный корень (префаб '
                        'Sign_Forsthuette на карте, то же место)',
    'Sign_Forsthuette_Text': 'лицо вывески (атлас панели)',
    'Hochsitz': 'засидка в 11 м за хижиной — отдельный корень (префаб Hochsitz на карте, то же место): четыре жерди на камнях, '
                'раскосы, площадка на 3,8 м, закрытая кабина с прорезью на три стороны, дверной проём и лестница с '
                'одной стороны, кровля толем',
}
SOCK_RU = {
    'Hand_Door_Out': 'скоба двери снаружи', 'Hand_Door_In': 'ручка двери изнутри', 'Hand_Window_Shutter': 'край ставня',
    'Hand_Window_Latch': 'вертушка', 'Hand_Stove_Door': 'ручка дверцы топки', 'Slot_Stove_Fire': 'топка: сюда дрова и растопку',
    'Hand_Stove_Damper': 'ручка задвижки', 'Hand_Kettle': 'дужка чайника', 'Pour_Barrel': 'бочка с дождевой водой: набрать '
    'в чайник или канистру', 'Hand_Axe': 'топорище', 'Hide_Hochsitz': 'присесть в кабине под прорезью — снизу не видно',
    'Seat_Hochsitz': 'лавка под прорезью: сидя глаза на уровне прорези', 'Ladder_Hochsitz_Bottom': 'низ лестницы засидки',
    'Ladder_Hochsitz_Top': 'верх лестницы у дверного проёма кабины', 'Ladder_Roof_Bottom': 'низ лестницы на крышу (правая '
    'стена)', 'Ladder_Roof_Top': 'отсюда ступить на крышу (к трубе, снег)',
    'Spot_Jerrycan': 'канистра Jerrycan_Hut (под нижней полкой)', 'Spot_Funnel': 'воронка Funnel_Hut на нижней полке (в данных пролога стоит носиком вверх: её начало координат — на 0,31 м выше полки)',
    'Spot_Flashlight': 'фонарик (стол)', 'Spot_Note': 'записка лесника note_forester (стол)',
    'Audio_Lantern': 'фонарь: шипит пламя, скрипит дужка на ветру', 'Audio_Stove': 'печка: треск, металл тикает, нагреваясь '
    'и остывая', 'Audio_Roof': 'жестяная крыша: дождь, иглы и шишки, ветки скребут, шаги по крыше', 'Audio_Door': 'дверь: '
    'скрип петель, хлопает на ветру', 'Audio_Window': 'окно: ветер в раме, стук по стеклу',
    'VFX_Chimney': 'дым из трубы, пока печка горит', 'VFX_StoveGlow': 'отсвет огня в прорезях (и в открытой дверце)',
    'VFX_LanternMoths': 'мотыльки у фонаря (тёплые ночи)', 'Hide_Woodpile': 'присесть за поленницей у заднего угла — '
    'с тропы не видно',
}


def ru_note(k, p):
    if k in RU:
        return RU[k]
    return p.get('note', '')


lines = []
A = lines.append
P_, S_, COL = C['parts'], C['sockets'], C['colliders']
meta = C['meta']
at = INFO['atlases']
pl = meta['map_placement']
A('# Хижина лесника (FORSTHÜTTE) — модель и контракт')
A('')
A(f'Версия 1.0 от {datetime.date.today().strftime("%d.%m.%Y")}. Пакет `source/assets/forest_hut/` (архив рядом — '
  '`forest_hut_package.zip`): `hut.blend`, атласы и панель в `tex/`, IES в `tex/IES/`, контракт `hut_contract.json`, лампы '
  '`hut_lights.json`, листы A–E, исходники в `src/`.')
A('')
A('Хижина из пролога карты Forest (шаг S2, пугалка X01) перестроена в виде генераторной: те же отделка, текстуры и '
  'плотность пикселя, тот же способ покраски. Место, размер, дверь, фонарь, вывеска, засидка и места предметов — как в '
  'обновлении 3, так что данные пролога (`Forest_Opening.json`) подходят без правок. Снаружи — тёмная морёная доска с '
  'белыми наличниками (выбор пользователя), внутри — как в генераторной: фанера, еловые стропила, изнанка профлиста.')
A('')
A('В Unity ничего не поставлено: замена префабов `TowerHut`, `Hochsitz`, `Sign_Forsthuette` на карте — в обновлении 4 '
  'вместе с остальными постройками (DEFERRED).')
A('')
A('## Что внутри')
A('')
kinds = {}
for p in P_.values():
    kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
ks = {}
for s in S_.values():
    ks[s['kind']] = ks.get(s['kind'], 0) + 1
A(f'- Объектов {len(P_)}: ' + ', '.join(f'{KIND.get(k, k)} — {v}' for k, v in sorted(kinds.items())) + '.')
A(f'- Точек {len(S_)}: ' + ', '.join(f'{SOCK.get(k, k)} — {v}' for k, v in sorted(ks.items())) + '.')
A(f'- Коллайдеров {len(COL)} (коробки), ламп {len(L)}.')
A(f'- Треугольников {INFO["tris"]:,}'.replace(',', ' ') + ': ' + ', '.join(f'{k} — {v:,}'.replace(',', ' ')
                                                                          for k, v in sorted(INFO['tris_by_atlas'].items())) + '.')
A(f'- Атласы: Hut {at["Hut"]["size"]} — хижина, вывеска и засидка вместе ({num(at["Hut"]["ppm"], 1)} пикс/м; стены снаружи '
  f'{num(at["Hut"]["ppm_parts"]["walls outside"], 1)}, внутри {num(at["Hut"]["ppm_parts"]["inside (ply, floor, timber, roof underside)"], 1)}, '
  f'засидка {num(at["Hut"]["ppm_parts"]["stand"], 1)} — плотность генераторной 51,3), HutProps {at["HutProps"]["size"]} '
  f'(мелочи, {num(at["HutProps"]["ppm"], 1)}), панель 512 (карта, календарь, вывеска, стёкла ламп, ореол). По 64 цвета, '
  'AO в цвете, дизеринг 4×4, фильтр «точка».')
A('')
A('## Система координат и место на карте')
A('')
A('Кадр хижины — кадр префаба `TowerHut`: x — вправо, если смотреть на дверь снаружи, y — внутрь хижины (от двери к задней '
  'стене), z — вверх, метры; начало — середина основания на земле, пол на z = 0,33. В Unity (в префабе): позиция '
  '(x, y, z) → (−x, z, −y), ось так же, угол → −угол; размер коробки (sx, sy, sz) → (sx, sz, sy).')
A('')
A('Три корня — три префаба на своих местах из обновления 3. У засидки и вывески свой поворот (`part.yaw`, градусы вокруг z '
  'в кадре хижины): объект несёт его как вращение, сетка — в своих осях. Мировые позиции в Forest (Unity):')
A('')
A('| Корень | p (Unity) | q (x, y, z, w) | поворот вокруг Y |')
A('|---|---|---|---|')
for k in ('TowerHut', 'Hochsitz', 'Sign_Forsthuette'):
    v = pl[k]
    A(f'| `{k}` | {fv(v["p"], 3)} | {fv(v["q"], 6)} | {num(v["yawUnity"], 2)}° |')
A('')
A('## Детали')
A('')
A('| Объект | Что | Ось и ход | Родитель | Описание |')
A('|---|---|---|---|---|')
for k, p in P_.items():
    rng = ''
    if p['kind'] in ('hinge', 'slide'):
        u = 'м' if p.get('unit') == 'm' else '°'
        rng = f'ось {fv(p["axis"], 3)}, {num(p["range"][0])}…{num(p["range"][1])} {u}'
    elif p['kind'] == 'item':
        rng = 'берётся в руки'
    A(f'| `{k}` | {KIND.get(p["kind"], p["kind"])} | {rng} | {p.get("parent") or "—"} | {ru_note(k, p)} |')
A('')
A('Точка вращения детали — начало её объекта (`pivot` в контракте, кадр хижины). `states` — состояния по порядку от 0. '
  'У подвижных деталей и предметов `box` — коробка для захвата в их собственном кадре.')
A('')
A('## Точки взаимодействия')
A('')
for kind in ('item_slot', 'hand', 'pour', 'climb', 'seat', 'hide', 'audio', 'vfx', 'knock'):
    names = [k for k, s in S_.items() if s['kind'] == kind]
    if not names:
        continue
    A(f'**{SOCK.get(kind, kind).capitalize()}** ({len(names)}):')
    A('')
    if kind == 'knock':
        A('стук и царапанье снаружи (звук, след инея): ' + ', '.join(f'`{k}`' for k in names) + ' — найдены лучами на '
          'стены, дверь, окно и крышу; `dir` — нормаль поверхности.')
    else:
        for k in names:
            s = S_[k]
            A(f'- `{k}` {fv(s["pos"], 3)} на `{s.get("parent")}` — {SOCK_RU.get(k, s.get("note", ""))}')
    A('')
A('## Лампы')
A('')
A('| Свет | Тип | Unity | Сила (URP) | Радиус | Цвет | Группа | На старте | Стекло / ореол |')
A('|---|---|---|---|---|---|---|---|---|')
for it in L:
    A(f'| `{it["socket"]}` | {it["type"]} | {it["unityLight"]} | {num(it["intensityURP"])} | {num(it["range"], 1)} м | '
      f'{it["kelvin"]} K | {it["group"]} | {"горит" if it["startsOn"] else "не горит"} | `{it["lens"]}`'
      + (f' / `{it["glow"]}`' if it.get('glow') else '') + ' |')
A('')
A('Фонарь — те же значения, что у света фонаря в обновлении 3 (Point, 0,9, радиус 11); мерцание — как сейчас '
  '(`SkyIslandFlicker`). IES-профили (`tex/IES/`) описывают форму света: под фонарём тень от бачка, над ним — от колпака, '
  'четыре прута защиты дают слабые лучи; точечный свет URP профили не использует — они для превью и на будущее.')
A('')
A('## Пролог: S2 и X01')
A('')
A('- S2: на старте дверь `IX_HutDoor_1` открыта, фонарь горит, внутри никого. Предметы появляются по позам из '
  '`Forest_Opening.json` (не менялись): канистра под нижней полкой, воронка на ней, фонарик и записка на столе; `Spot_*` — '
  'точки на поверхности под каждым предметом (пол 0,33, полка 1,092, стол 1,08), всё стоит, ничего не висит в воздухе.')
A('- X01 (взяли `Jerrycan_Hut`): выключить `LIGHT_Lantern`, скрыть `Glow_Lantern`, у `Lens_Lantern` материал '
  '`M_Hut_Lamp_Lantern` → `M_Hut_Lamp_Lantern_Off`; мерцание больше его не трогает.')
A('- Соответствие обновлению 3: `Light_lantern` → `LIGHT_Lantern`; стекло с `M_Lantern` → `Lens_Lantern` '
  '(`M_Hut_Lamp_Lantern`); `M_LanternOff` → `M_Hut_Lamp_Lantern_Off`; ореол `M_Glow_Lantern` → объект `Glow_Lantern` '
  '(`M_Hut_Glow`); `IX_HutDoor_1` — то же имя.')
A('')
A('## Коллайдеры')
A('')
by_par = {}
for c in COL:
    by_par.setdefault(c['parent'], []).append(c['name'][4:])
for par, names in by_par.items():
    A(f'- `{par}`: ' + ', '.join(names) + '.')
A('')
A('BoxCollider на родителе: `center` / `size` — в собственном кадре родителя (Blender), `centerUnity` / `sizeUnity` — то же '
  'в осях Unity; у двух скатов крыши `rotation` (Blender) и `rotationUnity`. Засидка внутри пустая: пол, стены вокруг '
  'дверного проёма, крыша, лавка — можно подняться и встать в кабине. Лестницы — точки `climb`, не коллайдеры.')
A('')
A('## Текстуры и материалы')
A('')
A('- `M_Hut_Hut` — атлас `T_Hut_Hut_BaseColor` (хижина, вывеска и засидка: у трёх префабов один материал), '
  '`M_Hut_HutProps` — `T_Hut_HutProps_BaseColor` (мелочи); фильтр «точка», без мип-карт, как у генераторной.')
A('- `M_Hut_Panel` — `T_Hut_Panel_BaseColor` / `_Emission`: карта, календарь, лицо вывески; `M_Hut_Lamp_Lantern` и '
  '`M_Hut_Lamp_Oillamp` — стёкла (эмиссия ночью — сила 3), варианты `_Off` — погасшие; `M_Hut_Glow` — ореол (только '
  'эмиссия, аддитивно); `M_Hut_Glass` — стекло окна.')
A('- Покраска — правила генераторной (`gen_paint.paint_shed`): фанера, ель, белые наличники, профлист и его изнанка, '
  'доски, металлы — те же цвета, шумы и износ; своё у хижины — морилка, пол, камни, печка, мебель, постель, поленница, '
  'бочка, засидка.')
A('')
A('## Файлы')
A('')
A('- `hut.blend` — модель: объекты с осями в точках вращения, иерархия, `LIGHT_*` (пустышки: +Z — луч, +Y — верх), '
  'коллекция `Colliders` (скрыта).')
A('- `hut_contract.json` — детали, точки, коллайдеры, `meta` (кадр, Unity, места корней на карте); `hut_lights.json` — '
  'лампы; `hut.json` — сводка сборки (атласы, плотность, треугольники).')
A('- `tex/` — атласы, панель, `hut_panel_regions.json`, `IES/`.')
A('- `hut_A.jpg` … `hut_E.jpg` — листы: снаружи, внутри, было и стало в игре, было и стало (модель), точки и текстуры.')
A('- `src/` — исходники: `hut_build.py` собирает всё (`--draft` — без запекания), `hut_render.py` — превью, '
  '`make_sheets_hut.py`, `make_hut_doc.py`, `pack_hut.py`.')
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(OUT, len(lines))
