"""Fill the v9 upgrade prompt from the export data:
python3 docs_v9/fill_prompt9.py <export_log> <verify_log> -> deliver/prompt/{PLANE_V9_UPGRADE_UNITY.md,START_PLANE_V9_UPGRADE.txt}"""
import json, re, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPL = os.path.join(HERE, 'docs_v9', 'PLANE_V9_UPGRADE_UNITY.tmpl.md')
OUT = os.path.join(HERE, 'deliver', 'prompt')
DATA = os.path.join(HERE, 'export', 'unity_v9', 'Assets', 'UtilityPlane', 'Data')
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


val = {'N_COL': n_col, 'N_IV': len(vols), 'N_SOCK': n_sock, 'NOSHADOW': nos, 'LOD_EXT': thr('Exterior'),
       'LOD_CP': thr('Cockpit'), 'LOD_TRIS': f'экстерьер {tris("Exterior")}, кабина {tris("Cockpit")} треугольников по уровням'}
s = open(TMPL).read()
for k, v in val.items():
    s = s.replace('{{' + k + '}}', str(v))
left = re.findall(r'\{\{[A-Z_0-9]+\}\}', s)
assert not left, left
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'PLANE_V9_UPGRADE_UNITY.md'), 'w').write(s)
start = f"""Обнови модель самолёта в проекте F:\\ClaudeGames\\snow\\Snow до v9.

Задание: F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_V9_UPGRADE_UNITY.md — выполни шаги U1–U5 по порядку. Сначала определи, какая версия стоит сейчас (v8 … v4). Ставь сразу пакет v9: пакеты v7 и v8 отдельно ставить не нужно, но с v4–v7 нужны правки кода из заданий PLANE_V7_UPGRADE_UNITY.md и PLANE_V8_UPGRADE_UNITY.md — какие именно, сказано в разделе 0 задания v9.
Новый пакет модели: F:\\ClaudeGames\\snow\\assets\\plane\\UtilityPlane_Unity_v9\\Assets\\UtilityPlane (README.md, UNITY_CONTRACT.md — раздел 16 «Что изменилось с v8», разделы 7.2 и 10.1–10.4).
Общие правила, статусы и формат отчёта — из F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_PROMPT_UNITY.md (версия 2.1).

Главное:
- экстерьер в стиле PS1/PSX (512 px, 64 цвета, без карт нормалей, импорт Point без сжатия — не менять); интерьер прежний;
- четыре откидных кресла в отсеке: SeatAnchor на каждое, положение кресел — серверное состояние, сидеть только на опущенном, выход — внутри самолёта на пол отсека (не через FindExit на землю);
- места хранения Stow_* для фонаря, ракетницы, лопаты, сумки, канистры и стремянки: предмет встаёт точно в позу сокета; аварийный комплект — префабы Surv_* (что предметы делают — OPEN);
- отпечатки на запотевших стёклах — события сервера (RPC), Rig их только рисует; сокеты хоррора и звука — записать в документы;
- {len(vols)} зон, {n_sock} сокетов, {n_col} коллайдеров; имена и каналы прежних частей не менялись;
- если зимний комплект уже стоял — после меню модели поставить комплект 1.2 и выполнить его меню (U3.6); если нет — ставить его после v9 по его заданию (версия 1.2);
- геометрию, текстуры и шейдер модели не менять, новые пакеты не ставить.

В конце — отчёт: с какой версии обновлено, что заменено, какие файлы кода изменены и почему, результаты Z1–Z12 (и проверок прежних заданий — по версии, с которой обновлялись), что осталось открытым.
"""
open(os.path.join(OUT, 'START_PLANE_V9_UPGRADE.txt'), 'w').write(start)
print('prompt filled', val)
