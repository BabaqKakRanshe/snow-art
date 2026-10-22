"""Fill the winter-kit Unity prompt (kit 1.2, plane v9): python3 docs_kit/fill_kit_prompt.py -> deliver/prompt_kit/{PLANE_WINTERKIT_UNITY.md,
START_PLANE_WINTERKIT.txt}"""
import json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(HERE, 'export', 'unity_kit12', 'Assets', 'UtilityPlane')
OUT = os.path.join(HERE, 'deliver', 'prompt_kit')
os.makedirs(OUT, exist_ok=True)
D = json.load(open(os.path.join(KIT, 'Data', 'winter_kit.json')))
EFF = {'engineStartBlocked': 'запуск', 'airspeedBlocked': 'указатель скорости', 'liftBlocked': 'взлёт',
       'viewBlocked': 'обзор (сам меш)', 'engineInsulated': 'утепляет мотор', 'wheelsHeld': 'колёса',
       'tiedDown': 'швартовка', 'preheating': 'греет мотор', 'moveBlocked': 'движение'}
rows = []
for it in D['items']:
    e = ', '.join(EFF[x] for x in it['effects'])
    if it['excludes']:
        e += '; не вместе с `' + '`, `'.join(it['excludes']) + '`'
    lab = it['label'][0].lower() + it['label'][1:]
    rows.append(f"| `{it['id']}` — {lab} | `{it['carry']}` | {e} |")
files = []
for r, _, fs in os.walk(KIT):
    for f in sorted(fs):
        files.append(os.path.relpath(os.path.join(r, f), KIT).replace(os.sep, '/'))
groups = {}
for f in sorted(files):
    d = f.split('/')[0] if '/' in f else '.'
    groups.setdefault(d, []).append(f.split('/')[-1])
flist = []
for d in ('Models', 'Textures', 'Data', 'Scripts', 'Editor', '.'):
    if d in groups:
        flist.append(f"   - `{d}/`: " + ', '.join(f'`{x}`' for x in groups[d]) if d != '.' else
                     '   - в корне: ' + ', '.join(f'`{x}`' for x in groups[d]))
n_items, n_carry = len(D['items']), len(D['carry'])
console = (f'[WinterKit] Done (URP): Assets/UtilityPlane/Prefabs/WinterKit.prefab ({n_items} items, {n_items} zones), {n_carry} carry '
           f'prefabs in Assets/UtilityPlane/Prefabs/Kit, nested into UtilityPlane.prefab.')
t = open(os.path.join(HERE, 'docs_kit', 'PLANE_WINTERKIT_UNITY.tmpl.md')).read()
t = t.replace('ITEM_TABLE', '\n'.join(rows)).replace('FILE_LIST', '\n'.join(flist)).replace('CONSOLE_LINE', console)
assert 'ITEM_TABLE' not in t and 'FILE_LIST' not in t and 'CONSOLE_LINE' not in t
open(os.path.join(OUT, 'PLANE_WINTERKIT_UNITY.md'), 'w').write(t)
start = f"""Добавь самолёту в проекте F:\\ClaudeGames\\snow\\Snow зимний предполётный комплект и канистру (версия комплекта 1.2).

Задание: F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_WINTERKIT_UNITY.md (версия 1.2) — выполни шаги K1–K4 по порядку. Нужна установленная модель v9 (задание PLANE_V9_UPGRADE_UNITY.md); если стоит более старая — сначала v9. После каждого повторного Build Materials + Prefabs модели комплект собрать заново (K3).
Пакет комплекта: F:\\ClaudeGames\\snow\\assets\\plane\\UtilityPlane_WinterKit_v1_2\\Assets\\UtilityPlane (WINTER_KIT.md — описание, Data\\winter_kit.json — вещи, зоны, последствия).
Общие правила, статусы и формат отчёта — из F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_PROMPT_UNITY.md (версия 2.1).

Главное:
- {n_items} вещей на самолёте (заглушки, чехлы, колодки, швартовка, подогреватель) и {n_carry} переносных префабов KitCarry_*, включая канистру 20 л и воронку;
- 1.2: текстуры в стиле PS1/PSX, как экстерьер самолёта v9 (импорт Point, без сжатия задаёт меню модели v9); модели, зоны и скрипты — как в 1.1; старые файлы 1.0/1.1, которые назовёт меню, удалить;
- меню Tools/Utility Plane/Install Winter Kit собирает всё и вкладывает WinterKit в UtilityPlane.prefab;
- состояние — UtilityPlaneWinterKit.Mask (одно число), решает сервер; зоны IV_Kit_* (kind kit) только снаружи и у стоящего самолёта; переносные вещи kind kit_item;
- последствия: запуск, указатель скорости, взлёт, движение, прогрев — флаги компонента, правила TEMPORARY; лучи подвески не должны видеть триггеры;
- канистра закрывает M7: заливка со стремянки; в отсеке v9 для неё есть держатель (Socket_Stow_JerryCan);
- геометрию и файлы модели не менять, новые пакеты не ставить.

В конце — отчёт: что скопировано и собрано, какие файлы кода изменены и почему, результаты KX1–KX10, что осталось открытым.
"""
open(os.path.join(OUT, 'START_PLANE_WINTERKIT.txt'), 'w').write(start)
print('prompt written', len(t), 'chars;', console)
