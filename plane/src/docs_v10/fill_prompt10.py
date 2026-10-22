"""Fill the v10 upgrade prompt from the export data:
python3 docs_v10/fill_prompt10.py <export_log> <verify_log> -> deliver/prompt/{PLANE_V10_UPGRADE_UNITY.md,START_PLANE_V10_UPGRADE.txt}"""
import json, re, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'docs_v10'))
import v10_numbers as N10
TMPL = os.path.join(HERE, 'docs_v10', 'PLANE_V10_UPGRADE_UNITY.tmpl.md')
OUT = os.path.join(HERE, 'deliver', 'prompt')
DATA = os.path.join(HERE, 'export', 'unity_v10', 'Assets', 'UtilityPlane', 'Data')
exp, ver = open(sys.argv[1]).read(), open(sys.argv[2]).read()
m = re.search(r'UNITY objects (\d+) render tris (\d+) cockpit tris (\d+) colliders (\d+) sockets (\d+)', exp)
n_col, n_sock = int(m.group(4)), int(m.group(5))
nos = int(re.search(r'renderers \d+ noshadow (\d+)', ver).group(1))
vols = json.load(open(os.path.join(DATA, 'interaction_volumes.json')))
lod = json.load(open(os.path.join(DATA, 'lod.json')))


def pct(v):
    s = f'{v * 100:.1f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',') + ' %'


def group(name):
    return next(g for g in lod['groups'] if g['name'] == name)


def thr(name):
    return ' / '.join(pct(l['screenRelativeHeight']) for l in group(name)['levels'])


def tris(name):
    return ' / '.join(f"{l['triangles']:,}".replace(',', ' ') for l in group(name)['levels'])


n10 = N10.values()
_sh = {x['renderer']: x['triangles'] for x in lod.get('shadowProxies', [])}


def lod0_with_proxies(name):
    l0 = group(name)['levels'][0]
    t = l0['triangles'] + sum(_sh[n] for n in l0['renderers'] if n in _sh)
    return f"{t:,}".replace(',', ' ')
val = {'N_COL': n_col, 'N_IV': len(vols), 'N_SOCK': n_sock, 'NOSHADOW': nos, 'LOD_EXT': thr('Exterior'),
       'LOD_CP': thr('Cockpit'), 'LOD_TRIS': f'экстерьер {tris("Exterior")}, кабина {tris("Cockpit")} треугольников по уровням',
       'TRIS9_K': n10['V10_LOD0_K9'], 'TRIS10_K': n10['V10_LOD0_K'], 'HIDDEN': n10['V10_HIDDEN'],
       'SHADOW9_K': n10['V10_SHADOW9'], 'SHADOW10_K': n10['V10_SHADOW'], 'VRAM9': n10['V10_VRAM9'],
       'VRAM10': n10['V10_VRAM'], 'RT_COUNT': n10['V10_RT_COUNT'],
       'LOD0_EXT_SH': lod0_with_proxies('Exterior'), 'LOD0_CP_SH': lod0_with_proxies('Cockpit')}
s = open(TMPL).read()
for k, v in val.items():
    s = s.replace('{{' + k + '}}', str(v))
left = re.findall(r'\{\{[A-Z_0-9]+\}\}', s)
assert not left, left
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'PLANE_V10_UPGRADE_UNITY.md'), 'w').write(s)
start = f"""Обнови модель самолёта в проекте F:\\ClaudeGames\\snow\\Snow до v10 (оптимизация).

Задание: F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_V10_UPGRADE_UNITY.md — выполни шаги U1–U5 по порядку. Сначала определи, какая версия стоит сейчас (v9 … v4). Если ниже v9 — нужно и задание PLANE_V9_UPGRADE_UNITY.md, но с пакетом v10 вместо v9; порядок шагов обоих заданий и отличия — строго по разделу 0 задания v10.
Новый пакет модели: F:\\ClaudeGames\\snow\\assets\\plane\\UtilityPlane_Unity_v10\\Assets\\UtilityPlane (README.md, UNITY_CONTRACT.md — раздел 17 «Что изменилось с v9»).
Общие правила, статусы и формат отчёта — из F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_PROMPT_UNITY.md (версия 2.1).

Главное:
- вид, имена, иерархия, зоны ({len(vols)}), сокеты ({n_sock}), коллайдеры ({n_col}), поля и методы Rig — как в v9;
- треугольников вблизи {n10['V10_LOD0_K9']} тыс. → {n10['V10_LOD0_K']} тыс., новые LOD1/LOD2, теневые копии *_Shadow (только тень) у Cockpit_Static, Cabin_Fittings и колёс;
- текстуры интерьера 1024², шкалы и надписи 2048²: видеопамять текстур около {n10['V10_VRAM9']} → {n10['V10_VRAM']} МБ;
- UtilityPlane.fbx без Read/Write: меню делает читаемые копии мешей коллайдеров и слоёв запотевания (Generated/); если код проекта читает меши самолёта во время игры — KeepMeshesReadable (U4.2);
- код, который перебирает рендереры самолёта (HoverOutline, скрытие модели), должен прятать *_Shadow вместе с частью и не подсвечивать их; Rig пишет части только при изменении полей — после чужих правок частей rig.ResyncPose() (U4.1);
- зимний комплект 1.2 подходит к v10 без изменений (его задание — версия 1.2.1);
- геометрию, текстуры и шейдер модели не менять, новые пакеты не ставить.

В конце — отчёт: с какой версии обновлено, что заменено, какие файлы кода изменены и почему, KeepMeshesReadable, результаты Q1–Q8 (и проверок прежних заданий — по версии, с которой обновлялись), цифры было/стало, что осталось открытым.
"""
open(os.path.join(OUT, 'START_PLANE_V10_UPGRADE.txt'), 'w').write(start)
print('prompt filled', {k: v for k, v in val.items() if k != 'LOD_TRIS'})
