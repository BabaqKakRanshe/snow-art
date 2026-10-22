"""Fill the v8 upgrade prompt from the export data:
python3 docs_v8/fill_prompt8.py <export_log> <verify_log> -> deliver/prompt/{PLANE_V8_UPGRADE_UNITY.md,START_PLANE_V8_UPGRADE.txt}"""
import json, re, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMPL = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/v8/PLANE_V8_UPGRADE_UNITY.tmpl.md'
OUT = os.path.join(HERE, 'deliver', 'prompt')
DATA = os.path.join(HERE, 'export', 'unity_v8', 'Assets', 'UtilityPlane', 'Data')
exp, ver = open(sys.argv[1]).read(), open(sys.argv[2]).read()
m = re.search(r'UNITY objects (\d+) render tris (\d+) cockpit tris (\d+) colliders (\d+) sockets (\d+)', exp)
n_col = int(m.group(4))
nos = int(re.search(r'renderers \d+ noshadow (\d+)', ver).group(1))
vols = json.load(open(os.path.join(DATA, 'interaction_volumes.json')))
tex = json.load(open(os.path.join(DATA, 'atlas_texel.json')))
lod = json.load(open(os.path.join(DATA, 'lod.json')))


def pxm(name):
    rows = tex if isinstance(tex, list) else tex.get('atlases', [])
    a = next(r for r in rows if r['atlas'] == name)
    return int(round(a['pxPerMetre'] / 10.0) * 10)


def pct(v):
    s = f'{v * 100:.1f}'.rstrip('0').rstrip('.')
    return s.replace('.', ',') + ' %'


def group(name):
    return next(g for g in lod['groups'] if g['name'] == name)


def thr(name):
    return ' / '.join(pct(l['screenRelativeHeight']) for l in group(name)['levels'])


def tris(name):
    return ' / '.join(f"{l['triangles']:,}".replace(',', ' ') for l in group(name)['levels'])


val = {'N_COL': n_col, 'N_IV': len(vols), 'NOSHADOW': nos, 'TEX_A': f'≈{pxm("Airframe")}', 'TEX_W': f'≈{pxm("Wing")}',
       'LOD_EXT': thr('Exterior'), 'LOD_CP': thr('Cockpit'),
       'LOD_TRIS': f'экстерьер {tris("Exterior")}, кабина {tris("Cockpit")} треугольников по уровням'}
s = open(TMPL).read()
for k, v in val.items():
    s = s.replace('{{' + k + '}}', str(v))
left = re.findall(r'\{\{[A-Z_0-9]+\}\}', s)
assert not left, left
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'PLANE_V8_UPGRADE_UNITY.md'), 'w').write(s)
start = f"""Обнови модель самолёта в проекте F:\\ClaudeGames\\snow\\Snow до v8.

Задание: F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_V8_UPGRADE_UNITY.md — выполни шаги U1–U5 по порядку. Сначала определи, какая версия стоит сейчас (v7, v6, v5 или v4). Ставь сразу пакет v8: пакет v7 отдельно ставить не нужно, но с v4–v6 нужны правки кода U4 и проверки X1–X13 из PLANE_V7_UPGRADE_UNITY.md (и то, что оно велит взять из заданий v5 и v6).
Новый пакет модели: F:\\ClaudeGames\\snow\\assets\\plane\\UtilityPlane_Unity_v8\\Assets\\UtilityPlane (README.md, UNITY_CONTRACT.md — раздел 15 «Что изменилось с v7», раздел 8.1 «LOD»).
Общие правила, статусы и формат отчёта — из F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_PROMPT_UNITY.md (версия 2.1).

Главное:
- обтекаемые подкосы, плавный форкиль, антенны на крыше кабины; имена частей, сокеты, {len(vols)} зон и скрипты — как в v7;
- обшивка в двух атласах 4K с новой развёрткой: M_Airframe и новый M_Wing (крыло, закрылки, элероны, стабилизатор, рули высоты); ссылки кода на M_Airframe, индексы подмешей Body и маски в UV обшивки проверить (U4.2);
- износ и грязь по настоящим местам, новое AO салона;
- LOD: дочерние <часть>_LOD1 / _LOD2 и два LODGroup (экстерьер на корне, кабина на Cockpit); код, перебирающий или рисующий рендереры самолёта, проверить (U4.3); правки LOD варианта — только в коде его сборки (U4.4, U4.5);
- если зимний комплект уже стоял — сразу после меню модели собрать его заново (U3.6); если нет — ставить его после v8 по его заданию;
- геометрию, текстуры и шейдер модели не менять, новые пакеты не ставить.

В конце — отчёт: с какой версии обновлено, что заменено, какие файлы кода изменены и почему, результаты Y1–Y10 (и X1–X13 задания v7, W1–W10 задания v6, V1–V12 задания v5 — по версии, с которой обновлялись), что осталось открытым.
"""
open(os.path.join(OUT, 'START_PLANE_V8_UPGRADE.txt'), 'w').write(start)
print('prompt filled', val)
