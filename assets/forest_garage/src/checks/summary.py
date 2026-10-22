"""The garage checks' logs -> a short Russian summary for the reference (make_gar_doc.py ... checks_summary.json).
python3 summary.py [dir] -> dir/checks_summary.json"""
import json, os, re, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


def rd(n):
    p = os.path.join(D, n)
    return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''


def num(s):
    return s.replace('.', ',').replace('-', '−')


S = {}
t = rd('probe_gar.log')
m = re.search(r'interactables (\d+) mismatches (\d+)', t)
lights = re.findall(r'light at .*?nearest surface ([\d.]+) m', t)
glows = re.findall(r'glow (\S+) at .*?nearest lens ([\d.]+) m', t)
m5 = re.search(r'objects not in the contract (\[.*?\])\s+parts without object (\[.*?\])', t)
if m:
    S['Сверка с обновлением 3'] = (f'деталей {m.group(1)}, расхождений по виду / оси / ходу / точке / замку {m.group(2)}; '
                                   f'источники света ({len(lights)}) в свободном воздухе (до ближайшей поверхности не меньше '
                                   f'{num(min(lights, key=float))} м); ореолы ({len(glows)}) у линз светильников (не дальше '
                                   f'{num(str(round(max(float(g[1]) for g in glows) * 1000)))} мм); лишних объектов '
                                   f'{"нет" if (m5 and m5.group(1) == "[]") else m5.group(1) if m5 else "?"}')
w = json.load(open(os.path.join(D, 'walk.json'))) if os.path.exists(os.path.join(D, 'walk.json')) else None
if w:
    b, so, go = w['both_open'], w['side_only'], w['gate_only']
    S['Проходимость (капсула игрока r 0,34, рост 1,80, шаг 0,35)'] = (
        f'зал свободен на {num(str(b["hall_free_m2"]))} м², с улицы достижимо {num(str(b["hall_reached_m2"]))} м² (обе двери '
        f'открыты), {num(str(so["hall_reached_m2"]))} м² — только через боковую дверь, {num(str(go["hall_reached_m2"]))} м² — '
        f'только через ворота; под открытыми воротами {num(str(w["gate_open_min_headroom"]))} м; деталей вне досягаемости '
        f'(2,0 м от глаз, луч не перекрыт): {len(w["ix_out_of_reach"])}')
t = rd('sweep2.log')
m = re.search(r'parts swept (\d+) sinking deeper than (\d+) mm while moving: (\d+)', t)
if m:
    S['Ход подвижных деталей'] = (f'{m.group(1)} детали прокручены по всему ходу; заходят во что-то глубже {m.group(2)} мм: '
                                  f'{m.group(3)}')
t = rd('backfaces.log')
m = re.search(r'rays (\d+) eyes dropped \(inside solids\) (\d+) back-facing first hits (\d+) in (\d+)', t)
if m:
    S['Грани изнанкой к зрителю'] = (f'{m.group(1)} лучей из зала (двери закрыты и открыты) и вокруг гаража; первым '
                                     f'попаданием изнанка — {m.group(3)}')
t = rd('coplanar2.log')
m = re.search(r'coplanar overlaps (\d+)', t)
m2 = re.search(r'with a decal / lens / glass face \(offset by design\): (\d+)\s+between atlas faces: (\d+)', t)
if m and m2:
    S['Совпадающие грани (мерцание)'] = (f'перекрытий в одной плоскости: {m.group(1)}, из них надписи / линзы / стекло '
                                         f'{m2.group(1)}, между гранями атласов {m2.group(2)}')
json.dump(S, open(os.path.join(D, 'checks_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in S.items():
    print(k, ':', v)
