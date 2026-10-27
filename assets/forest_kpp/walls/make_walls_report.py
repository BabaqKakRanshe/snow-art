"""walls/REPORT.md (Russian): the Update 7 walls at the base gate and at the barrier for KPP v2 - what changed, the heights
before and after, the levelling strips, the clearances, the closure check, the order for Unity.
python3 make_walls_report.py [out.md]"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'REPORT.md')
D = json.load(open(os.path.join(HERE, 'diff.json')))
L = json.load(open(os.path.join(HERE, 'levelling.json')))
W = json.load(open(os.path.join(HERE, 'walls_v2_data.json')))
T = json.load(open(os.path.join(HERE, 'tables_v2.json')))
V = json.load(open(os.path.join(HERE, 'u7_layout_v2.json')))
CL = {k: json.load(open(os.path.join(HERE, f))) for k, f in (
    ('v1', 'u7_layout_v1_copy_closure.json'), ('v2', 'u7_layout_v2_closure.json'),
    ('v2_nobones', 'u7_layout_v2_closure_nobones.json'))}


def num(a, n=3):
    s = f'{a:.{n}f}'.rstrip('0').rstrip('.')
    s = s.replace('.', ',').replace('-', '−')
    return '0' if s in ('−0', '') else s


def sgn(a, n=3):
    s = num(a, n)
    return ('+' + s) if a > 0 and s != '0' else s


MOD = {'ConcreteFence': 'плита', 'ConcreteFence_b': 'плита (вариант b)', 'ConcreteFence_Sign': 'плита с табличкой',
       'ConcreteFence_Socket': 'стакан (начало ряда)', 'RoadBlock_FBS': 'блок ФБС', 'RoadBlock_Cube': 'бетонный куб',
       'Sign_NoEntry': 'знак «въезд запрещён»', 'WireCoil': 'спираль колючки'}
WHAT = {'east post': 'восточный столб ворот', 'west post': 'западный столб ворот',
        'rail strip': 'рельс в бетоне (полоса 0,40…0,60 м за линией)', 'leaf (parked)': 'полотно открыто',
        'leaf (shut)': 'полотно закрыто', 'drive cabinet': 'шкаф привода', 'guide rollers, outer stand': 'направляющая стойка снаружи',
        'guide rollers, inner stand': 'направляющая стойка внутри', 'pole (0.5 m round it)': 'опора линии (круг 0,5 м)',
        'pad': 'подушка тумбы шлагбаума', 'cabinet': 'тумба с мотором', 'rest pad': 'фундамент стойки-упора',
        'conduit (from the cabinet to the booth, +y)': 'труба кабеля от тумбы к будке',
        'conduit to the booth (out of the pad, +y)': 'труба к будке: выход из подушки',
        'conduit to the booth (across, y 1.10)': 'труба к будке: поперёк, в 1,10 м за линией',
        'conduit to the booth (to its pad, x -1.10)': 'труба к будке: вдоль, до площадки будки',
        'conduit to the wall box (out of the pad, -y)': 'труба к коробке на плите: выход из подушки (улица)',
        'conduit to the wall box (on the ground, y -0.62)': 'труба к коробке на плите: по земле',
        'conduit to the wall box (to the panel, x -1.55)': 'труба к коробке на плите: к плите и вверх',
        'wall box (on the panel face)': 'коробка K6 на плите (со стороны улицы)',
        'camera mast footing (v2.1)': 'тумба мачты камеры (2.1)',
        'camera cable to the booth (v2.1, x -1.60)': 'труба кабеля камеры к площадке будки (2.1)',
        'camera cable (v2.1, down to y 0.80)': 'труба кабеля камеры: от тумбы (2.1)',
        'camera cable (v2.1, y 0.80 to the drive)': 'труба кабеля камеры: вдоль, к фундаменту привода (2.1)'}
CASE = {'van, barrier closed, gate closed (the wicket open, as built)': 'машина; шлагбаум и ворота закрыты (калитка открыта, '
                                                                        'как построено)',
        'van, barrier open, gate closed': 'машина; шлагбаум открыт, ворота закрыты',
        'van, barrier open, gate open': 'машина; шлагбаум и ворота открыты',
        'walker, barrier closed, gate closed (wicket open)': 'пешком; шлагбаум и ворота закрыты, калитка открыта',
        'walker, the wicket shut too': 'пешком; калитка тоже закрыта'}
PLACE = {'outside, on the road 40 m before the barrier': 'дорога в 40 м до шлагбаума',
         'the road 15 m behind the barrier (in the funnel)': 'дорога в 15 м за шлагбаумом',
         'in front of the base gate (in the funnel)': 'перед воротами базы',
         'inside the base': 'внутри базы'}
RES = {'reachable from outside': 'да', 'closed off': 'нет'}

moved = [c for c in D['changed'] if math.hypot(c['new']['p'][0] - c['old']['p'][0], c['new']['p'][2] - c['old']['p'][2]) > 1e-4]
dh = [c['new']['p'][1] - c['old']['p'][1] for c in D['changed']]
out = []
A = out.append
A('# Стены обновления 7 у ворот базы и у шлагбаума КПП — версия 2 (к КПП v2)')
A('')
A('Что сделано: плиты ПО-2 у ворот базы и у шлагбаума стоят одной ровной линией на одной высоте, без ступенек и сдвигов; '
  'ворота — ровно в линии стены между бетонными столбами ворот (`Gate_PostE`, `Gate_PostW`), забор подходит к столбам с обеих '
  'сторон. Землю под линиями выравнивают две полосы Terrain. Всё остальное в обновлении 7 — без изменений.')
A('')
A(f'Записей блока `u7`: было {len(V["records"]) - len(D["added"])}, стало {len(V["records"])}. Изменено {len(D["changed"])} '
  f'(сдвинуто в плане {len(moved)}, остальные — только высота; высота от {sgn(min(dh))} до {sgn(max(dh))} м), добавлено '
  f'{len(D["added"])}, удалено {len(D["removed"])}. Повороты не менялись.')
A('')
A('## Файлы')
A('- `u7_layout_v2.json` — весь блок `u7` в формате обновления 7 (`records`, `keep_clear` и прочее): заменяет данные '
  '`u7_layout.json` пакета обновления 7. Запись i — это `rocks[5649 + i]` в `Forest_Layout.json`; новая запись добавлена в '
  'конец (id 6182).')
A('- `diff.json` — список изменений: id, модель, было / стало (`p`, `q` в координатах Unity), причина.')
A('- `levelling.json` — полосы выравнивания земли (формула в `note`).')
A('- `plan_gate.png`, `plan_barrier.png` — план было / стало, полоса, профиль низа плит вдоль линии, разрез 1:1.')
A('- `closure_v2.png`, `u7_layout_*_closure*.json` — проверка «машина не проедет».')
A('- `tables_v2.json` — высоты вдоль обеих линий (ниже — те же таблицы).')
A('- Скрипты: `walls_v2.py` (расчёт; пишет `u7_layout_v2.json`, `diff.json`, `levelling.json`, `walls_v2_data.json`), '
  '`verify_v2.py` (проверки), `closure_v2.py`, `plans_v2.py`, `tables_v2.py`, `probe_u7.py`, `make_walls_report.py` (этот файл).')
A('')
A('## Ворота базы')
g = W['gate']
A(f'Кадр корня `Gate` (в игре ({num(g["P"][0])}; {num(g["P"][1])}), поворот 8°): x — вдоль стены (+ — на запад, туда '
  f'откатывается полотно), y — внутрь базы. Высота линии {num(g["H"], 4)} м (земля у корня ворот).')
A('')
A(f'- Западный ряд (сторона, куда уезжает полотно) начинается у западного столба: стакан 5649 переехал с x +2,925 на '
  f'+{num(g["runW0"], 3)}; на месте неподвижной сетчатой секции v1 — новая плита 6182; следующие пять плит (5650–5654) '
  f'раздвинуты с шагом {num(g["sW2"], 4)} м (было 2,4427), чтобы встретить стык обновления 7 на x +{num(g["w_joint"], 3)}.')
A(f'- Восточный ряд кончается у восточного столба (x {num(g["runE0"], 2)}): семь плит у ворот (5697–5703) раздвинуты с шагом '
  f'{num(g["sE2"], 4)} м (было 2,4717) до стыка на x {num(g["e_joint"], 3)}.')
A(f'- Концы плит у столбов: запад x +{num(g["ends"]["west"], 3)} (столб 0,15…0,45 — плита 6182 заходит в него на 16 мм, стык '
  f'без щели), восток x {num(g["ends"]["east"], 3)} (столб −7,45…−7,15 — щель 28 мм).')
A('')
A('| x, м | id | Что | Высота U7, м | Высота v2, м | Сдвиг по x, м |')
A('|---|---|---|---|---|---|')
for r in T['gate']:
    xo = r['x_u7']
    dx = '—' if xo is None else (sgn(r['x'] - xo, 3) if abs(r['x'] - xo) > 5e-4 else '0')
    A(f"| {num(r['x'], 3)} | {r['id']} | {MOD.get(r['m'], r['m'])} | {'новая' if r['y_u7'] is None else num(r['y_u7'], 4)} | "
      f"{num(r['y'], 4)} | {dx} |")
A('')
A('## Шлагбаум КПП')
b = W['barrier']
A(f'Кадр корня `Barrier` (в игре ({num(b["P"][0])}; {num(b["P"][1])})): x — от тумбы вдоль стрелы к упору, y — к будке. '
  f'Крылья стоят где стояли (тумба, подушка, упор и труба v2 их не задевают — см. зазоры), выровнены по высоте '
  f'{num(b["H"], 4)} м — высота площадки переноса КПП (ForestRelocation). На торцевой плите 5852 со стороны улицы висит '
  f'коробка шлагбаума K6 (`JunctionBox_Wall` КПП v2, как на концепте) — её место в контракте КПП посчитано по этой плите, плиту '
  f'не двигать.')
A('')
A('| x, м | id | Что | Высота U7, м | Высота v2, м |')
A('|---|---|---|---|---|')
for r in T['barrier']:
    A(f"| {num(r['x'], 3)} | {r['id']} | {MOD.get(r['m'], r['m'])} | {num(r['y_u7'], 4)} | {num(r['y'], 4)} |")
A('')
other = [c for c in D['changed'] if c['m'] not in ('ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Sign',
                                                   'ConcreteFence_Socket')]
if other:
    A('Кроме плит, на выровненную землю сели: ' + '; '.join(
        f"{c['id']} {MOD.get(c['m'], c['m'])} ({sgn(c['new']['p'][1] - c['old']['p'][1], 3)} м)" for c in other) + '.')
    A('')
A('## Земля: полосы выравнивания')
A('Для каждой точки карты высот: A, B — концы линии, s — расстояние вдоль A→B от A, t — поперёк. '
  'Поперёк: вес 1 до полуширины, дальше плавно (smoothstep) до 0 на полуширине + откосе. Вдоль: 1 между A и B, до A — '
  '1 + s / рампа_начала, после B — 1 − (s − |AB|) / рампа_конца (линейно, в пределах 0…1). h ← h + w·(высота − h).')
A('')
A('| Полоса | Линия (x; z в игре) | Высота, м | Полуширина / откос, м | Рампы по концам, м | Наибольшая ступенька на рампе, м |')
A('|---|---|---|---|---|---|')
for st in L['strips']:
    (ax_, az_), (bx_, bz_) = st['line']
    rs = W['ramps'][f"{st['name']} ramp_start"]
    re_ = W['ramps'][f"{st['name']} ramp_end"]
    A(f"| {'ворота' if st['name'] == 'gate' else 'шлагбаум'} | ({num(ax_, 2)}; {num(az_, 2)}) → ({num(bx_, 2)}; {num(bz_, 2)}) | "
      f"{num(st['height'], 4)} | {num(st['half_width'], 1)} / {num(st['falloff'], 1)} | {num(st['ramp_start'], 1)} и "
      f"{num(st['ramp_end'], 1)} | {num(rs[1], 3)} и {num(re_[1], 3)} |")
A('')
steps = []
for nm_, rows in (('ворота', T['gate']), ('шлагбаум', T['barrier'])):
    rr = [r for r in rows if r['y_u7'] is not None]
    for r0, r1 in zip(rr, rr[1:]):
        d2, d7 = abs(r1['y'] - r0['y']), abs(r1['y_u7'] - r0['y_u7'])
        if d2 > 0.10 and (r0['y'] != r0['y_u7'] or r1['y'] != r1['y_u7']):
            steps.append(f"{nm_}: {r0['id']}–{r1['id']} {num(d2, 3)} м (в U7 там было {num(d7, 3)})")
A('Ступенька по высоте между соседними плитами, которых коснулось выравнивание, — не больше 0,10 м' +
  (', кроме: ' + '; '.join(steps) + '.' if steps else '.'))
A('')
ins = W['in_strips']
A('На меняющейся земле стоят: у ворот — ' + f"{ins['gate']['trees']} растений ({', '.join(ins['gate']['tree_models'])}), "
  f"сдвиг до {num(ins['gate']['trees_max_dz'], 2)} м; у шлагбаума — {ins['barrier']['trees']} "
  f"({', '.join(ins['barrier']['tree_models'])}), до {num(ins['barrier']['trees_max_dz'], 2)} м; камней нет. Деревья и трава "
  'Terrain садятся на новую землю сами — выравнивать до перепекания растительности.')
A('')
A('## Зазоры (план, в кадре корня)')
A('Наименьшее расстояние от деталей ворот и шлагбаума v2 до плит и стаканов ПО-2; минус — заходит внутрь.')
A('')
A('| Деталь | Ближайшее | Зазор, м |')
A('|---|---|---|')
def piece(t):
    parts = t.split()
    pid, m = parts[0], parts[1]
    if len(parts) > 2 and parts[2] == 'socket':
        return f'стакан плиты {pid}'
    return f'{MOD.get(m, m)} {pid}'


for c in g['clear'] + b['clear']:
    A(f"| {WHAT.get(c['what'], c['what'])} | {piece(c['nearest'])} | {num(c['gap'], 3)} |")
A('')
A('Столбы ворот стоят на стаканах своих рядов — так задумано (в таблице сравнение со стаканами для них не делается).')
A('')
A('## Проверка «машина не проедет»')
A('Заливка по сетке 0,25 м с пятнами всех деталей на высоте кузова (как в обновлении 7). Машина — диск 0,97 м, пешеход — '
  '0,35 м.')
A('')
places = list(next(iter(CL['v2'].values())).keys())
A('| Случай | ' + ' | '.join(PLACE.get(p, p) for p in places) + ' |')
A('|---|' + '---|' * len(places))
for case, res in CL['v2'].items():
    A(f"| {CASE.get(case, case)} | " + ' | '.join(RES.get(res[p], res[p]) for p in places) + ' |')
A('')
same = CL['v1'] == CL['v2'] == CL['v2_nobones']
A(('Те же результаты, что у обновления 7 (`u7_layout_v1_copy_closure.json`), и без коллайдера костей (`_nobones`): к базе на '
   'машине — только через шлагбаум и ворота.') if same else 'Есть отличия от обновления 7 — см. json.')
A('')
A('## Порядок в Unity (вместе с КПП v2)')
A('1. Terrain: полосы `levelling.json` (тайл 1_1) — до установки плит.')
A('2. Блок `u7`: записи из `u7_layout_v2.json` (42 изменены, 6182 добавлена в конец); `keep_clear` — оттуда же.')
A('3. Контрольные точки обновления 7 у ворот (5650, 5703 — их места сдвинулись): список `controls` пересобрать.')
A('4. КПП v2: префабы `Checkpoint`, `Barrier`, `Gate` на прежние места (`KPP_CONTRACT.md`), экземпляры набора.')
A('5. Перепечь растительность / проверить, что деревья и папоротники на полосах стоят на земле.')
A('')
open(OUT, 'w').write('\n'.join(out) + '\n')
print('wrote', OUT, len(out), 'lines')
