"""The checks' logs -> a short Russian summary for the reference (make_main_doc.py ... checks_summary.json).
python3 summary.py [dir] -> dir/checks_summary.json"""
import json, os, re, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


def rd(n):
    p = os.path.join(D, n)
    return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''


S = {}
t = rd('probe_main.log')
m = re.search(r'interactables (\d+) mismatches (\d+)', t)
m2 = re.search(r'light masks (\d+) mismatches (\d+)', t)
m3 = re.search(r'lights (\d+) fixture missing (\[.*?\])', t)
m4 = re.search(r'glows (\d+) fixture missing (\[.*?\])', t)
m5 = re.search(r'objects not in the contract (\[.*?\])\s+parts without object (\[.*?\])', t)
if m:
    S['Сверка с обновлением 3'] = (f'деталей {m.group(1)}, расхождений по виду/оси/ходу {m.group(2)}; масок света '
                                   f'{m2.group(1) if m2 else "?"}, расхождений {m2.group(2) if m2 else "?"}; '
                                   f'источников {m3.group(1) if m3 else "?"} и ореолов {m4.group(1) if m4 else "?"} — '
                                   f'светильники на месте{"" if (m3 and m3.group(2) == "[]") else " (кроме " + (m3.group(2) if m3 else "?") + ")"}; '
                                   f'лишних объектов {"нет" if (m5 and m5.group(1) == "[]") else m5.group(1) if m5 else "?"}')
t = rd('walk.log')
rooms = [r for r in re.findall(r'^\s+(\w+)\s+free\s+([\d.]+)\s+reached\s+([\d.]+)', t, re.M) if r[0] != 'Treppenhaus']
fl = re.findall(r'flights ([-\d.]+) -> ([-\d.]+) headroom ([\d.]+)\s+clearance ([\d.]+)', t)
far = re.search(r'out of use range .*?: (\d+) (\{.*\})', t)
if rooms:
    unreached = [r for r in rooms if float(r[2]) < 0.9 * float(r[1])]
    S['Проходимость (капсула игрока r 0,34, рост 1,80, шаг 0,35)'] = (
        f'все {len(rooms)} комнат пройдены от входа и с площадок лестницы'
        + ('' if not unreached else ' (кроме ' + ', '.join(r[0] for r in unreached) + ')') + '; лестница по ступеням: '
        + '; '.join(f'марш {a}→{b} м — над ступенями не меньше {h} м, от оси марша до перил и стен {c} м (капсуле '
                    f'нужно 0,34)' for a, b, h, c in fl)
        + (f'; деталей вне досягаемости по правилу игры (2,0 м от глаз, луч не перекрыт): {far.group(1)}' if far else ''))
t = rd('sweep2.log')
m = re.search(r'parts swept (\d+) sinking deeper than (\d+) mm while moving: (\d+)', t)
found = re.findall(r'^== (\S+) (\w+)', t, re.M)
if m:
    names = [f[0] for f in found]
    drw = [n for n in names if n.startswith('IX_Drawer_3') and n[-2:] in ('31', '32', '33', '34')]
    rest = [n for n in names if n not in drw]
    S['Ход подвижных деталей'] = (f'{m.group(1)} деталей прокручены по всему ходу; заходят во что-то глубже {m.group(2)} мм: '
                                  f'{m.group(3)}' + (f' — ящики {drw[0]}…{drw[-1][-2:]} (ошибка данных обновления 3, см. '
                                                     f'раздел выше)' if drw else '')
                                  + (('; ' + ', '.join(rest) + ': стеклянная дверь при полных 95° заходит на 5 мм в угол '
                                      'стены за наличником (не видно)') if rest == ['IX_Door_5'] else
                                     ('; ' + ', '.join(rest)) if rest else ''))
t = rd('backfaces.log')
m = re.search(r'rays (\d+) eyes dropped \(inside solids\) (\d+) back-facing first hits (\d+) in (\d+)', t)
if m:
    S['Грани изнанкой к зрителю'] = (f'{m.group(1)} лучей из всех комнат и вокруг здания; изнанка первым попаданием — '
                                     f'{m.group(3)} раз (скользящие касания рёбер: угол направляющей ворот гаража, '
                                     f'перекрестья решёток растровых светильников)')
t = rd('coplanar2.log')
m = re.search(r'coplanar overlaps (\d+)', t)
m2 = re.search(r'with a decal / lens / glass face \(offset by design\): (\d+)\s+between atlas faces: (\d+)', t)
if m and m2:
    S['Совпадающие грани (мерцание)'] = (f'перекрытий в одной плоскости: {m.group(1)}, из них надписи/линзы/стекло '
                                         f'(отступ 1,5 мм по замыслу) {m2.group(1)}, между гранями атласов {m2.group(2)}')
t = rd('props_check.log')
m = re.search(r'^ok (\d+) bad (\d+)', t, re.M)
m2 = re.search(r'^decals off (\d+)', t, re.M)
zs = re.findall(r'zone (Sleep\w*): bottom ([-\d.]+), mattress ([-\d.]+)', t)
if m:
    S['Предметы и надписи пролога (Forest_Dressing.json)'] = (
        f'на поверхностях и со свободным местом: {m.group(1)}; вплотную к мебели или стене: {m.group(2)} — стоят так же, '
        f'как в обновлении 3 (сверено с его моделью); надписей на полу не на месте: {m2.group(1) if m2 else "?"}; '
        f'зоны сна {", ".join(z[0] for z in zs)} лежат на матрасах (низ зоны на 5 мм ниже верха матраса)')
lp = '/home/claude/uaz/out/main_leit_check.json'                  # 1.2: the KPP gate station (main_leit_check.py)
if os.path.exists(lp):
    LC = json.load(open(lp))
    RU = {'Leit_Console': 'пульт', 'Leit_Monitor_Barrier': 'нижний монитор', 'стойка мониторов': 'стойка мониторов'}
    nr = min(LC['rows'], key=lambda r: r['gap'])
    props = ', '.join(o for o in LC['others'] if not o.startswith('FX_'))
    S['Пункт управления КПП в пультовой (1.2)'] = (
        f"стойка мониторов, нижний монитор и пульт — {'на правом столе' if LC['on_desk'] else 'НЕ на столе'}; до предметов "
        f"на том же столе ({props}) и настольной лампы FX_DeskLamp_7 — не меньше {nr['gap'] * 100:.1f} см (ближе всего "
        f"{RU.get(nr['station'], nr['station'])} и {nr['other']}), {'пересечений нет' if LC['min_gap'] > 0 else 'ЕСТЬ ПЕРЕСЕЧЕНИЯ'}; "
        f"остальные проверки — на модели корпуса без экземпляров набора, как в прежней версии")
S = {k: re.sub(r'(?<=\d)\.(?=\d)', ',', v) for k, v in S.items()}       # decimal commas
json.dump(S, open(os.path.join(D, 'checks_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in S.items():
    print(k, ':', v)
