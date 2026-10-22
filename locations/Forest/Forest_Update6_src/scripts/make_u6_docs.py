"""Forest Update 6 documents: the Unity task FOREST_U6_UNITY.md, its start prompt START_FOREST_U6.txt, and the three
references GENCONT_FOREST_CONTRACT.md, ITEMS_CONTRACT.md, APPARITION_CONTRACT.md (numbers from the build reports).
python3 make_u6_docs.py <u6_out_dir> -> docs/*"""
import os, sys, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
U6 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out', 'forest_update6')
DOCS = os.path.join(HERE, 'docs')
MAN = json.load(open(os.path.join(U6, 'Forest_Update6_manifest.json')))
REP = json.load(open(os.path.join(U6, 'fbx', 'u6_export_report.json')))
GJ = json.load(open(os.path.join(HERE, 'out', 'gcf.json')))
GC = json.load(open(os.path.join(HERE, 'out', 'gcf_contract.json')))
IT = json.load(open(os.path.join(HERE, 'out', 'items.json')))
FG = json.load(open(os.path.join(HERE, 'out', 'fig.json')))
U3I = json.load(open(os.path.join(HERE, 'items_u3.json')))
ST = os.path.join(U6, 'stage', 'Assets', 'Locations', 'Forest', 'Data')
CAT = {e['model']: e for e in json.load(open(os.path.join(ST, 'Forest_Items.json'), encoding='utf-8'))['items']}
OPN = json.load(open(os.path.join(ST, 'Forest_Opening.json'), encoding='utf-8'))
LAY = json.load(open(os.path.join(ST, 'Forest_Layout.json')))
DATE = '21.10.2026'
VER = '1.0'


def ru(v, n=2):
    return f'{v:.{n}f}'.replace('.', ',')


def bytes_ru(n):
    n = int(n)
    w = 'байта' if n % 10 in (2, 3, 4) and not 12 <= n % 100 <= 14 else 'байт'
    return f'{th(n)} {w}'


def th(n):
    return f'{n:,}'.replace(',', ' ')


def vec(v, n=3):
    return '(' + '; '.join(ru(x, n) for x in v) + ')'


def fsize(path):
    return next(f['bytes'] for f in MAN['files'] if f['path'].endswith(path))


def fmd5(path):
    return next(f['md5'] for f in MAN['files'] if f['path'].endswith(path))


ROOT = 'Assets/Locations/Forest'
NFILES = sum(1 for f in MAN['files'] if f['md5'])
NFOLD = sum(1 for f in MAN['files'] if not f['md5'])
U3_GC_TRIS = 19994
ITEM_TRIS = sum(REP[n]['tris'] for n in U3I)
ITEM_TRIS_U3 = sum(v['tris'] for v in U3I.values())
LIGHTS = GJ['data']['prefabLights']['lights']
VP = GJ['data']['viewpoint']
FILL = GJ['data']['fill']
RAD = MAN['radio']
IX = ['IX_ContDoorL_83', 'IX_ContDoorR_84', 'IX_ContSideDoor_85', 'IX_GenStart_86', 'IX_Breaker_87', 'IX_Breaker_88',
      'IX_Breaker_89', 'IX_MainSwitch_90', 'IX_GenFillCap_300']
IXDATA = {it['child']: it for it in LAY['interactables'] if it['model'] == 'GenContainer'}
IXNOTE = {'IX_ContDoorL_83': 'левая створка грузовых дверей; ключ «Generator»',
          'IX_ContDoorR_84': 'правая створка; ключ «Generator»',
          'IX_ContSideDoor_85': 'боковая дверь в дальнем торце северного бокса; ключ «Generator»',
          'IX_GenStart_86': 'ключ пуска на панели генератора: 0 — OFF, 52° — пуск/работа',
          'IX_Breaker_87': 'автомат щита (ряд из трёх)', 'IX_Breaker_88': 'автомат щита', 'IX_Breaker_89': 'автомат щита',
          'IX_MainSwitch_90': 'перекидной рубильник щита: 0 — OFF, 60° — GEN',
          'IX_GenFillCap_300': 'крышка короба заливной горловины (петля сверху); табличка DIESEL / DAY TANK 100 L'}
WALK = FG['walk_speed']
SIT = FG['sit']
# clip ranges as Unity shows them: the Blender exporter starts every take at 0 (Blender itself shows 1-based)
CLIPS = {c: (lo - 1, hi - 1) for c, (lo, hi) in REP['Apparition']['clips'].items()}
FPS = REP['Apparition']['fps']
BONES = REP['Apparition']['bones']
TEXSIZE = {'T_GCont_Cont_A_px': 1024, 'T_GCont_Genset_A_px': 512, 'T_GCont_Props_A_px': 512, 'T_GCont_Panel_A_px': 512,
           'T_Item_Props_A_px': 512, 'T_Item_Panel_A_px': 512, 'T_Item_Panel_E_px': 512, 'T_Fig_Figure_A_px': 256}
MEM = sum(s * s * 3 * 4 / 3 for s in TEXSIZE.values()) / 2 ** 20
MEM4 = sum(s * s * 4 * 4 / 3 for s in TEXSIZE.values()) / 2 ** 20


def write(name, text):
    p = os.path.join(DOCS, name)
    open(p, 'w', encoding='utf-8').write(text.rstrip('\n') + '\n')
    print(p, len(text))


# ============================================================================== FOREST_U6_UNITY.md
ixrows = '\n'.join(
    f'| `{n}` | {vec(IXDATA[n]["axis"], 0)} | {ru(IXDATA[n]["min"], 0)}…{ru(IXDATA[n]["max"], 0)}° | '
    f'{vec(GC["parts"][n]["pivotUnity"])} | {IXNOTE[n]} |' for n in IX)
items_tbl = []
for n in sorted(U3I):
    c = CAT[n]
    items_tbl.append(f'`{n}` {th(REP[n]["tris"])} ({th(U3I[n]["tris"])})')
items_line = ', '.join(items_tbl)
base_rows = '\n'.join(f'| `{p.replace(ROOT + "/", "")}` | `{m}` | {"обновление 5" if ("Layout" in p or "Materials" in p or p.endswith("README.md")) else "обновление 3"} |'
                      for p, m in MAN['base_md5'].items())
ch_rows = '\n'.join(f'- {c}' for c in MAN['changes'])

U6DOC = f'''# Forest, обновление 6: контейнер генератора, предметы, рация пульта и фигура — задание для AI-агента

Версия {VER} от {DATE}. Действует вместе с `PLANE_PROMPT_UNITY.md` (v2.1): правила работы, статусы (CONFIRMED, TEMPORARY, OPEN, DEFERRED, ENGINEERING, NOT_RUN) и формат отчёта — оттуда (§0). Выполняется **после** сборки карты (`FOREST_ASSEMBLY_UNITY.md`, шаги K): обновления 1–5, Unity Terrain, атмосфера уже встроены. Порядок работы, сборщик, интеграция и проверки — те же, что в обновлении 5 (`FOREST_U5_UNITY.md`, шаги H) и в сборке (интеграция с подшагом «Unity Terrain», K5); здесь — только то, что отличается. Контракты описывают модели; если пункт здесь расходится с ними, верно то, что написано здесь: материалы делает сборщик ядра (URP/Lit по `Forest_Materials.json`), у текстур `*_px` мип-карты включены, коллайдеры контейнера — импортные `MeshCollider`, предметам коллайдеры ставит проект по каталогу (F4.1).

Проект: `F:\\ClaudeGames\\snow\\Snow`, Unity 6000.0.67f1, URP 17.0.4, NGO 2.13.3, Multiplayer Play Mode 1.6.3.

| Что | Где |
|---|---|
| Пакет | `F:\\ClaudeGames\\snow\\source\\locations\\Forest\\Forest_Update6.unitypackage` — {MAN["entries"]} записей, {bytes_ru(MAN["bytes"])}, md5 `{MAN["md5"]}`; ставится поверх `Forest_Update5` |
| Опись пакета | `source\\locations\\Forest\\Forest_Update6_src\\reports\\Forest_Update6_manifest.json` (пути, GUID, md5 файлов, `base_md5` — что должно лежать в проекте до импорта, `changes` — правки данных, место рации); как собран — `Forest_Update6_src\\README_SRC.txt` |
| Описание | `Assets/Locations/Forest/README.md`, раздел «Обновление 6» (копия — `source\\locations\\Forest\\README_Forest.md`) |
| Устройство моделей | `docs\\gdd\\GENCONT_FOREST_CONTRACT.md` (контейнер на карте), `docs\\gdd\\ITEMS_CONTRACT.md` (83 предмета и рация), `docs\\gdd\\APPARITION_CONTRACT.md` (фигура: скелет, клипы, посадка); исходный пакет контейнера — `docs\\gdd\\GENCONT_CONTRACT.md` |
| Как должно выглядеть | листы пакетов: `source\\assets\\forest_gencont` (`gcont_A…D.jpg`, рендеры — `renders\\`), `source\\assets\\forest_items` (`items_A…F.jpg`), `source\\assets\\forest_figure` (`fig_A…C.jpg`); «обновление 3 и теперь» — `gcont_C_u3_vs_now.jpg`, `items_E_u3_vs_now.jpg` |
| Журнал работы | `F:\\ClaudeGames\\snow\\docs\\dev\\ImplementationStatus.md` |

## 0. Что и зачем

Пользователь (CONFIRMED, 21.10): «давай сделаем … просто потом подгрузим эти новые модели да и все» — про модели, которых не хватало после обновления 5: контейнер генератора (в сборке он ещё модель обновления 3, OPEN), 83 предмета в старом виде, рация на пульт для X08, фигура для X02 и X03.

Что приходит:
- **`GenContainer`** — прежние имя, GUID и место; внутри — сдвоенный контейнер пакета `generator_container` (генератор, щит, дневной бак, бочки, свет). Те же 9 частей `IX_…` (их имена знают данные пролога и замки) + стекло `Window_Glass`. {th(REP["GenContainer"]["tris"])} треугольников (было {th(U3_GC_TRIS)}).
- **83 предмета `Item_*`** — прежние имена, GUID, начала координат и размеры: коллайдеры каталога и места в данных остаются верными (кроме записки `Note_GenProcedure`: она переложена на крышу новой панели генератора — Приложение Б). {th(ITEM_TRIS)} треугольников (было {th(ITEM_TRIS_U3)}).
- **Новая модель `Item_RadioSet`** — рация на западном пульте Leitstand (для X08): запись в каталоге (84-я) и в обжитом корпусе (`Leitstand_RadioSet_1`); окно канала — свой материал `M_RadioDisplay`, «включённое» состояние — `M_RadioDisplayOn`.
- **Новая модель `Apparition`** — фигура для X02 и X03: скелет из {len(BONES)} костей, клипы `Stand`, `Walk`, `Sit`, `SitLook`. Пугалки X02, X03, X08 — по-прежнему **DEFERRED** (машина, игровые часы, звук); здесь только ассет фигуры и данные для них.
- {len(MAN["changes"])} правок данных (Приложение Б): свет, ореолы, ходы частей и точка обзора контейнера, горловина (бак 100 л), записка о запуске генератора (место — на крыше новой панели, текст — по новому генератору), каталог предметов (`tris` и рация), обжитой корпус (рация), поля для X02/X03/X08, `noColliderPrefixes` + `Apparition`; 8 текстур, 11 материалов.

Поэтому задание короткое: поставить, пересобрать, пересобрать префабы предметов, встроить, настроить импорт фигуры и сделать её префаб, проверить контейнер, предметы и рацию в Play, записать.

Не в задании:
- **DEFERRED:** пугалки X02 (фигура переходит дорогу), X03 (фигура в фургоне) и X08 (рация включается сама) — как в обновлении 3 (нужны машина, игровые часы и звук); звук и эффекты по точкам контрактов (`Audio_…`, `VFX_…`, `Knock_…` — только в json-контрактах).
- **OPEN** (решает пользователь): бак 100 л вместо 60 л (числа пролога — TEMPORARY; вернуть 60 можно одной правкой данных — `Gen_FillNeck` и текст записки `gen_procedure`, табличка на модели останется «100 L»); новые превью карты; память текстур (QJ9); 3 плафона внутри контейнера без теней (`room: Exterior`, как лампа обновления 3) подсвечивают и землю снаружи у стен — если заметно, записать снимок (решение — тени у одного плафона или меньший `r`).

## 1. Что затронуто в проекте

| Где | Что |
|---|---|
| `Assets/Locations/Forest` | пакет: `Models/` — `GenContainer.fbx` и 83 `Item_*.fbx` заменены (те же GUID), новые `Item_RadioSet.fbx`, `Apparition.fbx`; `Textures/` — 8 новых; `Data/` — `Forest_Layout.json`, `Forest_Materials.json`, `Forest_Opening.json`, `Forest_Items.json`, `Forest_Dressing.json`, `Forest_Notes.json`; `README.md`. `Scenes/`, `Prefabs/`, `Materials/` пишет сборщик (J3) |
| `Assets/Snow/Levels/Forest/Items` | 84 префаба предметов (меню F4.1, J3.4), запись `Item_RadioSet` в `Assets/DefaultNetworkPrefabs.asset` |
| `Assets/Snow/Levels/Forest/Apparition` (новая) | `AC_Apparition.controller`, `Apparition.prefab` (J4) |
| `Assets/Snow/Editor`, `Assets/Snow/Runtime` | ничего (кода в пакете нет; имена частей, материалов и данных — прежние) |
| `docs/dev/ImplementationStatus.md` | раздел «Forest U6» (J6) |

## 2. Шаги

### J1. Подготовка
1. **Состояние проекта.** Сборка сделана, если в `docs\\dev\\ImplementationStatus.md` есть раздел «Forest — сборка (K)», в `Assets/Locations/Forest/Data/Forest_Layout.json` — блок `u5`, а в `Assets/Locations/Forest/Terrain/` — `Forest_TerrainData.asset`. Иначе — остановиться и сообщить пользователю: обновление 6 ставится после сборки.
2. Выйти из Play Mode; перед компиляцией — состояние редактора (R-4).
3. **Точка отката** — коммит в git (`git add -A`, `git commit -m "Before Forest U6"` в `F:\\ClaudeGames\\snow`, хэш — в отчёт; если коммитить нечего — хэш текущего `HEAD`). Коммит недоступен — копия в `F:\\ClaudeGames\\snow_archive\\backup\\forest_u6_<дата>\\`: `Assets/Locations/Forest/` целиком, `Assets/Snow/Levels/Forest`, `Assets/Snow/Editor`, `Assets/DefaultNetworkPrefabs.asset` — всё с `.meta`.
4. **Сверка до импорта** (опись → `files`, `base_md5`):
   - у 84 заменяемых моделей (`GenContainer` и 83 `Item_*`) `guid` в `.fbx.meta` проекта совпадает с описью (это GUID обновления 3); у шести файлов данных (`Data/*.json` из таблицы ниже) и `README.md` — тоже (GUID обновления 3); `Models/Item_RadioSet.fbx` и `Models/Apparition.fbx` в проекте ещё нет;
   - md5 файлов, которые пакет перепишет, совпадают с `base_md5` описи — значит, после своих пакетов их никто не менял:

| Файл | md5 до импорта | Чей |
|---|---|---|
{base_rows}

   Не совпадает — **не импортировать**: пакет затрёт эти изменения. Записать, какие файлы и чем отличаются от файлов пакетов (`source\\locations\\Forest\\Forest_Update3.unitypackage`, `Forest_Update5.unitypackage`), и спросить пользователя. `Forest_Look.json` (его могла править сборка, K6.6) пакет не трогает.
5. «До», в Play на хосте (1920 × 1080): контейнер снаружи с обоих торцов и внутри через открытые грузовые двери (ключ «Generator» — как в игре); полка хижины с воронкой и канистрой; ключи в будке КПП; стол кухни; пульты Leitstand. Время кадра хоста и клиента (клиент — если пользователь нажал Join, иначе NOT_RUN) на точках `Base`, `GenContainer` и в Leitstand.

### J2. Импорт
1. `Forest_Update6.unitypackage` — способом BASEV2, U2.2 (`AssetDatabase.ImportPackage(path, false)`, дождаться импорта и перезагрузки домена). Кода в пакете нет; в консоли нет `error CS`.
2. Проверить: md5 всех {NFILES} файлов пакета совпадают с описью (`files` → `md5`; у {NFOLD} папок md5 нет); README с разделом «Обновление 6»; в `Forest_Layout.json` есть блок `u6` ({len(MAN["changes"])} строк в `changes`) и блоки `u5`, `u4`; в `Forest_Materials.json` в конце списка 11 новых — `M_GCont_Cont` … `M_Apparition`; в `Textures/` 8 новых файлов `T_GCont_…`, `T_Item_…`, `T_Fig_Figure_A_px`; `Models/GenContainer.fbx` — {bytes_ru(fsize("GenContainer.fbx"))}, `Models/Apparition.fbx` — {bytes_ru(fsize("Apparition.fbx"))}, `Models/Item_RadioSet.fbx` — {bytes_ru(fsize("Item_RadioSet.fbx"))}.
3. **Без копий.** Модели заменяются на месте, рядом не должно появиться `GenContainer 1.fbx`, `Item_Jerrycan20 1.fbx` и т. п. Появились — GUID пакета в проекте не нашлись (J1.4 пропущен), префабы остались на старых сетках. Остановиться: ничего не удалять и не откатывать, записать, какие файлы появились и какие GUID у моделей в проекте, спросить пользователя.
4. Прежние текстуры (`T_ContainerU3_A_px`, `T_Dress_A_px` и др.) остаются — не удалять.

### J3. Пересборка, префабы предметов, интеграция
1. **Rebuild** — как H3.1 обновления 5 (`Tools → Locations → Location Builder` → `Forest` → **Rebuild**). Строки журнала — те же, кроме сети: `power grid: 19 lights, 19 halos, 6 lamp material pairs` (было 17 / 17: у контейнера 4 лампы вместо 2); `63 light fixtures` — как раньше (светильники — только в `BaseMain`; лампы контейнера — сеть, не светильники; если другое — записать, не чинить); число объектов сцены может отличаться — записать. Нет ни `children not found` (части `IX_…` контейнера), ни `fixture object(s) not found`, ни `power material pair … not found`, ни остальных предупреждений из списка G3.1, ни ошибки `textures are missing`. После сборки — `Mobile_RPAsset` по ответу на BASEV2 U1.6 (как раньше).
2. Импорт (только проверить и записать, настраивает ядро): у `GenContainer.fbx` — `Normals: Import`, `Convert Units`, Generate Colliders включено; у 84 `Item_*.fbx` и `Apparition.fbx` Generate Colliders выключено (`Item_`, `Apparition` в `noColliderPrefixes`); материалы переназначены на `Materials/URP/M_…` с теми же именами (контейнер: `M_GCont_…`, `M_Lamp_BulbOff`, `M_LEDOff`, `M_GlassClear`; предметы: `M_Item_Props`, `M_Item_Panel`, `M_TorchLens`, `M_Water`, `M_RadioDisplay`; фигура: `M_Apparition`); `Materials/URP/M_RadioDisplayOn` создан из данных, как `M_TorchLensOn`; у 8 текстур — фильтр Point, без сжатия, мип-карты включены.
3. **Capture** — сразу после сборки, до интеграции. Сравнить с Capture того же этапа из сборки (H3.3 внутри K2): новый контейнер в кадре только у точек `KPP` и `GenContainer` (пирамида кадра 16 : 9, туман 220 м; предметов при Capture нет — их создаёт игра). `KPP` — числа и кадр без оценки по L3.3 (как в обновлении 5); `GenContainer` — **камера точки перенесена** (прежняя оказалась бы внутри генератора), превью не совпадёт: числа и кадр без оценки; `UnderHand`, `Ribs` — по L3.3; остальные 13 точек — те же числа, что в сборке (в пределах L3.3).
4. **Префабы предметов** — `Tools/Snow/Forest/Build Item Prefabs` (F4.1 обновления 3, повторный запуск заменяет, а не дублирует): 84 префаба (83 + `Item_RadioSet`), все в списке сетевых префабов; правила F4.1 те же (коллайдер из каталога, не меньше 2 см, `CargoItem`, фонарик, канистра). Рация — простой реквизит (`kind: prop`, 6 кг), своего поведения у неё нет. Журнал меню — в отчёт.
5. **Интеграция** — `Tools/Snow/Integrate Location Level/Forest` с подшагом «Unity Terrain» (K5): строки и числа — как после сборки (K5.6); повторный запуск — те же. Capture после интеграции — как в K5.8 сборки: отличаются только `KPP` и `GenContainer`.

### J4. Фигура `Apparition` (ассет для будущих пугалок)
1. **Импорт `Models/Apparition.fbx`** — настройки импортёра (это `.meta` проекта, не файл пакета):
   - Rig: Animation Type **Generic**, Avatar Definition — Create From This Model, Root node — нет (движения корня нет: объект двигает код);
   - Animation: Import Animation включено; в файле 4 дубля `Apparition_Rig|Stand`, `|Walk`, `|Sit`, `|SitLook` — назвать клипы `Stand`, `Walk`, `Sit`, `SitLook`; кадры — как в файле ({FPS} к/с), диапазоны по умолчанию не менять: экспортёр Blender начинает каждый дубль с нуля, Unity показывает {", ".join(f"{c} {lo}–{hi}" for c, (lo, hi) in CLIPS.items())} (Blender показывает те же кадры с единицы — не переносить); Loop Time: Walk, Stand, Sit — включено, SitLook — выключено (держит последний кадр); Loop Pose — выключено;
   - Model: Bake Axis Conversion — выключено. У `Apparition_Rig` и `Apparition_Body` (дети корня префаба) поворот x −90° — так у любой модели из Blender, не ошибка.
   Если после Rebuild настройки сбросились (ядро переписало импорт): ядро не править; разрешена одна правка кода — пост-процессор импорта в проекте `Assets/Snow/Editor/ApparitionImportRule.cs` (`AssetPostprocessor` только для пути `…/Models/Apparition.fbx`: `OnPreprocessModel` ставит Generic, Create From This Model, Import Animation и клипы с циклами по этому пункту; `GetPostprocessOrder` больше, чем у постпроцессора ядра, чтобы ядро его не перезаписало). Записать в журнал как ENGINEERING с причиной.
2. **Animator Controller** `Assets/Snow/Levels/Forest/Apparition/AC_Apparition.controller`: состояния `Stand` (по умолчанию), `Walk`, `Sit`, `SitLook` с одноимёнными клипами; переходы и параметры не нужны (код включает состояние по имени: `Animator.Play`, `CrossFade`).
3. **Префаб** `Assets/Snow/Levels/Forest/Apparition/Apparition.prefab`: модель + `Animator` (контроллер выше, Apply Root Motion — выключено, Culling Mode — Always Animate: фигуру видят и в зеркале); у `SkinnedMeshRenderer` — Update When Offscreen включено (в `Sit` сетка уходит ниже начала координат), тени — включены, **Rendering Layer Mask = `defaultMask` карты (2)**, как у остальных рендереров (L4.8), иначе фонари её не осветят. Без коллайдеров, без `NetworkObject` (пугалки покажут фигуру на каждом клиенте сами; DEFERRED).
4. **Проверка** — во временной сцене (не сохранять) или в окне превью клипа: `Walk` идёт по кругу без рывка на стыке, стопа опоры не скользит при скорости объекта {ru(WALK, 2)} м/с; в `Sit` стопы стоят на полу 0,425 м ниже начала координат, спина — {ru(SIT["frames"]["1"]["top"], 2)} м выше; `SitLook` кончается головой, повёрнутой к левому плечу фигуры. Снимки: `Stand`, два кадра `Walk`, `Sit`, конец `SitLook` — рядом с листами `fig_A_poses.jpg`, `fig_B_van.jpg`.

### J5. Проверка в Play
Хост — в редакторе, клиенты — виртуальные игроки MPPM (Join нажимает пользователь — попросить; без него сетевые пункты — NOT_RUN с причиной). Game View 1920 × 1080. Замки, топливо и сеть — как в игре; другим способом не снимать и не включать.
1. **Контейнер генератора** (шаг S7 пролога, как в игре):
   - ключ «Generator» из будки КПП открывает грузовые двери (`IX_ContDoorL_83` до 160°, `IX_ContDoorR_84` до 170°) и боковую дверь в дальнем торце (`IX_ContSideDoor_85`, до 100°); створки ничего не задевают, в проёмы можно войти, внутри пройти между генератором и щитом, сквозь стены не просвечивает;
   - насос двора → канистра → крышка короба горловины в дальнем торце (`IX_GenFillCap_300`, до 110°, табличка DIESEL / DAY TANK 100 L) → налив у горловины (`Gen_FillNeck`: 1 л/с, бак до 100 л; стоять у короба) → ключ пуска `IX_GenStart_86` (0 → 52°) → рубильник `IX_MainSwitch_90` (0 → 60°) → рубильник корпуса `IX_MainSwitch_75`;
   - с сетью: 3 плафона внутри и фонарь над грузовыми дверями горят, ореолы — у ламп; лампы «работа» на панели генератора и щита зелёные (`M_LEDOn`); без сети всё тёмное; автоматы `IX_Breaker_87…89` ходят 0…60°.
2. **Предметы:** строка журнала `[Snow] Forest items spawned: 233 (11 opening, 202 props, 20 notes).` (было 232 и 201); предметы — как на листах `items_A…D.jpg`, не проваливаются и не прыгают при старте; брать, носить, бросать; фонарик светит, стекло меняется (`M_TorchLens` ↔ `M_TorchLensOn`); канистра наливает; воронка на полке хижины стоит на раструбе; бирки ключей в будке читаются; записки читаются (тексты прежние, кроме `gen_procedure`: короб DIESEL, ключ START, бак 100 л на 28 часов — Приложение Б); записка `Note_GenProcedure` лежит на крыше панели генератора (1,75 м), не висит и не падает.
3. **Рация:** на полке западного пульта Leitstand, у его западного конца (справа от оператора, который стоит лицом к пульту), лицевой панелью к оператору; берётся (6 кг); окно канала тёмное. Проверка второго материала: в Play на хосте временно поставить `M_RadioDisplayOn` в слот окна её рендерера (инспектор, без сохранения) — светится оранжевый канал 27.135; вернуть. Сама X08 — DEFERRED.
4. **Ночь без сети.** Снимки без фонарика с 5–10 м: контейнер снаружи, Leitstand, кухня. Модели не темнее соседних в том же кадре, надписи на предметах видны вблизи.
5. **Клиент.** То же у клиента, в том числе после позднего входа: двери и крышка контейнера, свет, предметы и рация там, где их оставили.

### J6. Документы
`docs/dev/ImplementationStatus.md` — раздел «Forest U6»: пакет и как поставлен; сверка до и после импорта; журнал сборки; таблица `report.txt`; журналы меню предметов и интеграции; импорт и префаб фигуры; проверки QJ со статусами; снимки «до / после»; нагрузка и память текстур; изменённые файлы кода (ожидается: нет); что осталось TEMPORARY, OPEN, DEFERRED.

## 3. Что проверить

| № | Проверка | Ожидание |
|---|---|---|
| QJ1 | импорт и пересборка | сверка J1.4 (GUID, `base_md5`) и md5 после импорта (J2.2); без `error CS`; копий нет (J2.3); строки J3.1 (сеть 19 / 19, светильников 63) без предупреждений из списка; сцена сохранена |
| QJ2 | импорт моделей и текстур | J3.2 у всех 86 FBX и 8 текстур (таблица в отчёт) |
| QJ3 | префабы предметов | 84 префаба, `Item_RadioSet` в списке сетевых префабов, дублей нет (J3.4) |
| QJ4 | интеграция | строки и числа — как после сборки (K5.6); повторный запуск — те же |
| QJ5 | сверка | `UnderHand`, `Ribs` — L3.3; 13 точек — как в сборке; `KPP`, `GenContainer` — числа и кадры без оценки (J3.3) |
| QJ6 | фигура | импорт (J4.1), контроллер и префаб (J4.2–J4.3), снимки клипов (J4.4) |
| QJ7 | контейнер | J5.1: двери с ключом, горловина и налив, пуск, рубильник, свет и лампы с сетью и без |
| QJ8 | предметы и рация | J5.2, J5.3: 233 предмета, рация на пульте, второй материал окна |
| QJ9 | нагрузка и память | время кадра хоста и клиента на `Base`, `GenContainer`, в Leitstand — до (J1.5) и после. Треугольники: контейнер {th(REP["GenContainer"]["tris"])} (было {th(U3_GC_TRIS)}), предметы {th(ITEM_TRIS)} (было {th(ITEM_TRIS_U3)}) + рация {REP["Item_RadioSet"]["tris"]}, фигура {th(REP["Apparition"]["tris"])}. Новые текстуры без сжатия с мип-картами — {ru(MEM, 1)}–{ru(MEM4, 1)} МиБ (RGB24 или RGBA32). Записать; ничего не ужимать |
| QJ10 | консоль и сеть | нет ошибок у хоста и клиентов; поздний вход; первая сцена в Build Settings — та же, что до начала |

## 4. Не делать

- Не править то, что пришло в пакете (модели, данные, текстуры, README), не делать Apply переопределений в префабы локации, не переименовывать части. Если что-то выглядит не так — снимок и запись в отчёт; правку пришлю пакетом.
- Не делать пугалки X02, X03, X08 и не менять код пролога — DEFERRED. Не ставить фигуру в сцену карты и не добавлять ей коллайдер.
- Не расставлять предметы руками вместо данных; не возвращать бак 60 л самому (OPEN — решает пользователь).
- Не ставить и не обновлять пакеты Package Manager. URP-ассеты, Graphics, Quality, Player Settings — только проверять; исключение — возврат `Mobile_RPAsset` после сборки по BASEV2 U1.6.
- Не удалять файлы и не откатывать импорт без решения пользователя (J2.3); не писать руками YAML сцен, префабов, ассетов и `.meta` (настройки импорта фигуры — через импортёр).
- Не менять `Player.prefab` и `BenchBuilder.cs`; первую сцену в Build Settings не менять (по решению пользователя 16.10 загрузочной станет `BaseV2` — не в этом задании); кадр PS1 у игрока не выключать.
- Не трогать Terrain и его правки (`Forest_TerrainData.asset`): пакет его не меняет, интеграция ставит его как в сборке.

## 5. Отчёт

В формате §0 промпта: хэш точки отката; сверка GUID и `base_md5` (J1.4) и md5 после импорта (J2.2), копий нет (J2.3); журнал сборки (J3.1); импорт (J3.2); журналы меню предметов (J3.4) и интеграции (J3.5); таблица `report.txt` (J3.3); фигура (J4) со снимками; QJ1–QJ10 со статусами и доказательствами (снимки «до / после» тех же мест, строки `BenchLog`); нагрузка и память (QJ9); изменённые файлы кода с причиной (ожидается: нет); что осталось TEMPORARY, OPEN, DEFERRED.

## Приложение А. Модели

Кадр каждой модели — кадр её префаба (Y вверх). FBX — в соглашении обновления 3 (тот же экспортёр, что в обновлениях 4 и 5): FBX 7400, Y вверх, вперёд +Z, `UnitScaleFactor` 100, корень без поворота, у детей только сдвиг, нормали записаны (`Normals: Import`); у `Apparition` — скелет и анимация, у `Apparition_Rig` и `Apparition_Body` (дети корня) поворот x −90° (J4.1). Проверено обратным импортом: границы и точки поворота объектов — в пределах 1 мм, у фигуры — позы всех клипов совпадают с исходником.

**`GenContainer`** — место `prefabs` (p {vec(LAY["prefabs"][[e["m"] for e in LAY["prefabs"]].index("GenContainer")]["p"], 4)}), поворот прежний. Объекты: корень (всё неподвижное) + 9 частей + `Window_Glass`. Части (данные `interactables`, ось — в кадре префаба Unity, + открывает):

| Часть | Ось | Ход | Точка поворота (префаб) | Что это |
|---|---|---|---|---|
{ixrows}

Свет (`prefabLights`, все `tag: power`, на старте выключены, `room: Exterior`): {"; ".join(f'{l["t"]} {vec(l["p"])}' for l in LIGHTS)} — 3 плафона и фонарь над грузовыми дверями; ореолы `M_Glow_Bulb` у каждой лампы. Горловина: `Gen_FillNeck` — горловина {vec(FILL["neck"], 4)}, место игрока {vec(FILL["stand"], 4)} (мир), бак {FILL["capacityL"]} л. Подробно — `GENCONT_FOREST_CONTRACT.md`.

**Предметы (84)** — `Models/Item_*.fbx`, начало координат прежнее (низ по центру; у ключей и замка — точка подвеса сверху, у фонарика — центр), по одному мешу на модель, материалы `M_Item_Props` + `M_Item_Panel` (+ `M_TorchLens` у фонарика, `M_Water` у ведра с водой, `M_RadioDisplay` у рации). Треугольники (было): {items_line}; `Item_RadioSet` {REP["Item_RadioSet"]["tris"]} (новая). Подробно — `ITEMS_CONTRACT.md`.

**`Item_RadioSet`** — в каталоге: «Рация», 6 кг, коробка-коллайдер корпуса {vec(CAT["Item_RadioSet"]["collider"]["center"])} / {vec(CAT["Item_RadioSet"]["collider"]["size"])}, `kind: prop`, `display {{off: M_RadioDisplay, on: M_RadioDisplayOn}}`, `speaker` {vec(CAT["Item_RadioSet"]["speaker"])} (точка звука, кадр модели). В обжитом корпусе — `Leitstand_RadioSet_1`, p {vec(RAD["unity"]["p"], 4)}, q {vec(RAD["unity"]["q"], 6)}: полка западного пульта у его западного конца, лицом к оператору, задняя стенка — у ступеньки к наклонной панели (кабель антенны уходит в пульт).

**`Apparition`** — `Models/Apparition.fbx`, мест на карте нет. Скелет: {", ".join(f"`{b}`" for b in BONES)}. Клипы ({FPS} к/с): {", ".join(f"`{c}` {lo}–{hi}" for c, (lo, hi) in CLIPS.items())}. Подробно — `APPARITION_CONTRACT.md`.

## Приложение Б. Изменения данных

Блок `u6` в `Forest_Layout.json` перечисляет их дословно (`changes`); всё остальное в шести файлах — байт в байт как в обновлениях 3 и 5 (форматы файлов те же: раскладка — без отступов, материалы — отступ 1, данные пролога и записки — отступ 1 с кириллицей как есть).

{ch_rows}

## Приложение В. Фигура для будущих пугалок (DEFERRED)

- **X02** (`scares` → `X02_Crossing.figure`): фигуру ставит код на дорогу в точке пугалки, поперёк дороги слева направо относительно машины, клип `Walk`; при скорости объекта {ru(WALK, 2)} м/с ноги не скользят; переход за 2 с (около 8–10 м) — `Animator.speed = v / {ru(WALK, 3)}` (2,5–3,2: шаг частый) или медленнее с проскальзыванием — выбор того, кто будет делать пугалку. Следов нет.
- **X03** (`X03_BackSeat.figure`): фигуру ставят на точку посадки левой скамьи фургона (`Sit_L1` … `Sit_L4`, `VAN3_CONTRACT.md`) началом координат на сиденье, лицом к проходу (передом скамьи); клип `Sit`, при взгляде водителя в зеркало или назад — `SitLook` (0,6 с: голова выходит из плеч и поворачивается к кабине), затем скрыть. Поза рассчитана на скамью фургона: сиденье 0,425 м над полом, потолок 0,709 м над сиденьем, стенка 0,25 м за точкой посадки — фигура 2,3 м сложена под потолком. На правой скамье голова повернётся к стенке, а не к кабине.
- Видна только тем, кому показана пугалка (как решит код пугалок), без сети: префаб без `NetworkObject`.

## Приложение Г. Рация для X08 (DEFERRED)

`scares` → `X08_Radio.radio`: `prop` — `Leitstand_RadioSet_1` (её `NetworkObject` — в таблице id → объект `ForestItems`, F4.2), `displayOff` / `displayOn` — материалы окна канала (слот `M_RadioDisplay` её рендерера), `speaker` — точка звука в кадре модели (сверху, над решёткой). «Включилась сама»: на сервере — событие; у всех — слот окна `M_RadioDisplayOn`, шум и голос из `speaker` 4 с, затем `M_RadioDisplay`. Если рацию унесли — эффект там, где она сейчас.

## Приложение Д. Ловушки

1. **GUID.** Все 84 заменяемые модели — с GUID обновления 3 (как в проекте после F2). Если в проекте другие — копии `… 1.fbx` (J1.4, J2.3).
2. **`base_md5`.** Пакет переписывает шесть файлов данных и README целиком: правки, сделанные в проекте после пакетов 3 и 5, пропали бы — поэтому сверка до импорта (J1.4).
3. **Префабы предметов и интеграция.** Rebuild не трогает префабы предметов (`Assets/Snow/Levels/Forest/Items`), но у новых моделей другой набор материалов — поэтому меню J3.4 после импорта обязательно. Пересборка стирает интеграцию — после Rebuild снова интеграция, и только потом Play.
4. **Нормали** — только `Import`.
5. **Воронка** в модели, как в обновлении 3, — раструбом вверх; на полке хижины её переворачивает поза `Funnel_Hut` (q — 180° вокруг горизонтальной оси). Не «чинить».
6. **Фигура**: поворот x −90° у `Apparition_Rig` и `Apparition_Body` — норма; Generic, не Humanoid; клипы без движения корня (Apply Root Motion — выключено), в `Sit` корень опущен на ~0,96 м (так задумано: начало координат — на сиденье).
7. **Подвижные части двигают трансформ без `Rigidbody`** (ловушка 8 обновления 3): створка, открытая в предмет, проходит сквозь него — TEMPORARY, записать, если мешает.
'''
write('FOREST_U6_UNITY.md', U6DOC)

START = f'''Поставь на карту Forest обновление 6: контейнер генератора (сдвоенный, как в пакете generator_container), 83 предмета в стиле генераторной, рация на пульт Leitstand и фигура Apparition для будущих пугалок. Проект F:\\ClaudeGames\\snow\\Snow.

Задание: F:\\ClaudeGames\\snow\\docs\\gdd\\FOREST_U6_UNITY.md (версия {VER}) — шаги J1–J6 по порядку, проверки QJ1–QJ10, отчёт по разделу 5. Общие правила, статусы и формат отчёта — F:\\ClaudeGames\\snow\\docs\\gdd\\PLANE_PROMPT_UNITY.md (версия 2.1, §0). Журнал работы — F:\\ClaudeGames\\snow\\docs\\dev\\ImplementationStatus.md.
Пакет: F:\\ClaudeGames\\snow\\source\\locations\\Forest\\Forest_Update6.unitypackage (md5 {MAN["md5"]}); опись — Forest_Update6_src\\reports\\Forest_Update6_manifest.json там же; описание — README_Forest.md там же, раздел «Обновление 6». Устройство моделей — контракты F:\\ClaudeGames\\snow\\docs\\gdd\\GENCONT_FOREST_CONTRACT.md, ITEMS_CONTRACT.md, APPARITION_CONTRACT.md; как должно выглядеть — листы в F:\\ClaudeGames\\snow\\source\\assets\\forest_gencont\\, forest_items\\, forest_figure\\.

Порядок. Обновление 6 ставится только после сборки карты (FOREST_ASSEMBLY_UNITY.md): если в журнале нет раздела «Forest — сборка (K)», в Forest_Layout.json нет блока u5 или нет Terrain\\Forest_TerrainData.asset — остановись и напиши мне.

Главное:
- одна точка отката — коммит в git перед началом (J1.3; копия в F:\\ClaudeGames\\snow_archive\\backup — только если коммит недоступен);
- до импорта сверить GUID 84 моделей, шести файлов данных и README с описью и md5 этих файлов с base_md5 описи (J1.4); не совпало — не импортировать, записать и спросить меня; после импорта — md5 файлов (J2.2);
- если рядом появились «… 1.fbx» (J2.3) — остановиться: ничего не удалять и не откатывать, записать и спросить меня;
- карту собирает только сборщик: Location Builder → Forest → Rebuild, сразу Capture, потом меню префабов предметов (Tools/Snow/Forest/Build Item Prefabs) и снова интеграция Forest (с подшагом Unity Terrain); данные, материалы, текстуры, Terrain и лук не трогать — если что-то выглядит не так, снимок и запись в отчёт, правку пришлю пакетом;
- фигуре — настройки импорта (Generic, 4 клипа), контроллер и префаб по J4; в сцену карты её не ставить, коллайдер не добавлять; пугалки X02, X03, X08 не делать — DEFERRED;
- бак генератора теперь 100 л (было 60) — так в данных пакета; менять не надо (OPEN, решу сам);
- в Play замки, топливо и сеть — как в игре, другим способом не снимать и не включать;
- снимки «до» (J1.5) и «после» с тех же мест; время кадра хоста и клиента и память новых текстур записать, ничего не ужимать;
- кадр PS1 у игрока — моё решение, не выключать; первую сцену в Build Settings не менять (загрузочной по моему решению 16.10 станет BaseV2 — не в этом задании); пакеты Package Manager не ставить и не обновлять; URP и Quality — только проверять (кроме возврата Mobile_RPAsset после сборки по BASEV2 U1.6); файлы не удалять; Player.prefab и BenchBuilder не менять; Join в окнах виртуальных игроков нажму я — попроси.

В конце — отчёт по разделу 5: хэш коммита, сверка GUID и md5 до и после импорта, журнал сборки, report.txt сверки, журналы меню предметов и интеграции, фигура со снимками клипов, QJ1–QJ10 со снимками «до / после» и строками BenchLog, нагрузка и память текстур, изменённые файлы кода с причиной, что осталось TEMPORARY, OPEN, DEFERRED.
'''
write('START_FOREST_U6.txt', START)


# ============================================================================== GENCONT_FOREST_CONTRACT.md
S = GC['sockets']


def sock_rows(kind, limit=None):
    rows = []
    for k, v in S.items():
        if v['kind'] != kind:
            continue
        par = v.get('parent') or 'GenContainer'
        obj = par if par in IX + ['Window_Glass'] else 'GenContainer'
        rows.append(f'| `{k}` | {vec(v["posUnity"])} | `{obj}` | {v.get("note", "")} |')
    return '\n'.join(rows[:limit] if limit else rows)


tb = GJ['tris_by_object']
GCDOC = f'''# Контейнер генератора на карте Forest (обновление 6) — справочник для Unity

Версия {VER} от {DATE}. Модель `GenContainer` обновления 6: сдвоенный контейнер пакета `generator_container` (`GENCONT_CONTRACT.md` — его полный контракт: все подвижные детали, точки, сценарий) поставлен на место контейнера обновления 3 с его именами частей. Здесь — что отличается на карте: кадр, объекты FBX, части `IX_…`, свет, точки, материалы, данные. Источник чисел — `gcf_contract.json`, `gcf.json` пакета `source\\assets\\forest_gencont`.

## Кадр и объекты
- Кадр — префаб `GenContainer` (FBX после импорта): Unity, начало — точка установки обновления 3 (p {vec(LAY["prefabs"][[e["m"] for e in LAY["prefabs"]].index("GenContainer")]["p"], 4)}, поворот 8° вокруг Y, как раньше), земля y = 0, пол 0,31 м. Вдоль x — боксы, грузовые двери — на −x, дальний торец с боковой дверью и горловиной — на +x; «южный» бокс (генератор, щит; названия боксов — из `GENCONT_CONTRACT.md`) стоит на месте прежнего контейнера, «северный» (бак, бочки) — рядом, на +z.
- Габарит: x {ru(-GJ["bbox"][1][0], 2)}…{ru(-GJ["bbox"][0][0], 2)}, y {ru(GJ["bbox"][0][2], 2)}…{ru(GJ["bbox"][1][2], 2)} (с выхлопом), z {ru(-GJ["bbox"][1][1], 2)}…{ru(-GJ["bbox"][0][1], 2)} м.
- Объекты FBX: `GenContainer` (корень: всё неподвижное — стены, рамы, генератор, щит с открытой на 165° дверцей, бак, бочки, насос, кабели, свет, жалюзи), 9 частей `IX_…`, `Window_Glass` (стекло окна, `M_GlassClear`). Треугольников {th(REP["GenContainer"]["tris"])}: корень {th(tb["GenContainer"])}, створки {th(tb["IX_ContDoorL_83"])} и {th(tb["IX_ContDoorR_84"])}, боковая дверь {th(tb["IX_ContSideDoor_85"])}, крышка горловины {th(tb["IX_GenFillCap_300"])}, ключ {th(tb["IX_GenStart_86"])}, рубильник {th(tb["IX_MainSwitch_90"])}, автоматы по {th(tb["IX_Breaker_87"])}, стекло окна {th(tb["Window_Glass"])}.
- Всё, что в исходном пакете двигалось само (крышки, краны, дверца щита, жалюзи, засовы), на карте неподвижно и входит в корень; двигаются только 9 частей обновления 3. Коллайдеры — импортные `MeshCollider` у всех объектов (как у всей карты).

## Части `IX_…`
Ось — в кадре префаба Unity, + открывает (как в данных `interactables`); точка поворота — начало объекта части.

| Часть | Ось | Ход | Точка поворота | Что это |
|---|---|---|---|---|
{ixrows}

Изменения против обновления 3 (данные `interactables` обновлены): у ключа, автоматов и рубильника — новые оси и ходы (новые рукоятки: ключ вращается вокруг оси x, автоматы — рычажки вниз-вверх, рубильник — поворот вокруг оси z), у крышки — новая ось (петля сверху), ход прежний — 0…110°; у левой створки ход 160° (за 160° она упирается в стенку северного бокса).

## Свет
Все 4 — в сети (`tag: power`, выключены на старте, `room: Exterior`), у каждого ореол `M_Glow_Bulb`; линзы плафонов — `M_Lamp_BulbOff` (сеть меняет на `M_Lamp_Bulb`), лампы «работа» на панели генератора и щита — `M_LEDOff` (→ `M_LEDOn`, зелёные).

| Тип | Точка | Направление | Цвет | Яркость | Дальность | Что |
|---|---|---|---|---|---|---|
''' + '\n'.join(f'| {l["t"]} | {vec(l["p"])} | {vec(l["d"])} | {vec(l["c"], 2)} | {ru(l["i"], 2)} | {ru(l["r"], 1)} м | '
                + ('фонарь над грузовыми дверями (конус 140°)' if l['t'] == 'spot' else 'плафон') + ' |' for l in LIGHTS) + f'''

## Горловина и бак
`Forest_Opening.json` → `Gen_FillNeck`: горловина {vec(FILL["neck"], 4)}, место игрока {vec(FILL["stand"], 4)} (мир Unity), подпись «{FILL["label"]}», бак {FILL["capacityL"]} л (было 60; `startL`, `burnLph` прежние). В кадре префаба горловина — точка `Pour_Fill` {vec(S["Pour_Fill"]["posUnity"])}: в коробе на дальнем торце северного бокса, под крышкой `IX_GenFillCap_300`; труба идёт внутри к дневному баку.

## Точки (кадр префаба)
Точки исходного пакета — в кадре префаба; у точек частей `IX_…` объект — сама часть (двигается с ней). В FBX их нет — только в `gcf_contract.json` (`sockets`), для будущих звуков, эффектов и пугалок.

### Руки у частей и горловина
| Точка | Где | Объект | Что |
|---|---|---|---|
''' + '\n'.join(f'| `{k}` | {vec(S[k]["posUnity"])} | `{S[k].get("parent")}` | {S[k].get("note", "")} |'
                for k in S if k.startswith('Hand_IX') or k in ('Pour_Fill', 'Line_In', 'Feed_Out')) + f'''

### Звук (audio)
| Точка | Где | Объект | Что |
|---|---|---|---|
{sock_rows("audio")}

### Стук снаружи (knock) — для пугалок вроде X07
| Точка | Где | Объект | Что |
|---|---|---|---|
{sock_rows("knock")}

### Тепло, укрытия, эффекты
| Точка | Где | Объект | Что |
|---|---|---|---|
{sock_rows("heat")}
{sock_rows("hide")}
{sock_rows("vfx")}

## Материалы и текстуры
- Атласы (`lit`, без бликов): `M_GCont_Cont` (`T_GCont_Cont_A_px`, 1024, {ru(GJ["atlases"]["Cont"]["ppm"], 1)} px/м), `M_GCont_Genset` (`T_GCont_Genset_A_px`, 512, {ru(GJ["atlases"]["Genset"]["ppm"], 1)} px/м), `M_GCont_Props` (`T_GCont_Props_A_px`, 512, {ru(GJ["atlases"]["Props"]["ppm"], 1)} px/м), `M_GCont_Panel` (`T_GCont_Panel_A_px`, 512: таблички, приборы, щит, табличка горловины).
- Цвет: `M_GCont_Needle` (стрелки приборов), `M_GCont_Diesel` (дизель в мерной трубке бака).
- Имена карты: `M_Lamp_BulbOff`, `M_LEDOff` (пары сети), `M_GlassClear` (окно).
- Надписи на оборудовании — по-английски (MAIN SWITCHBOARD, CIRCUITS, DIESEL / DAY TANK 100 L), таблички на стенах — сначала по-немецки, ниже — по-английски.

## Данные (обновление 6)
`Forest_Layout.json`: `prefabLights` / `prefabGlows` контейнера (2 → 4), оси и ходы 7 частей, точка обзора `GenContainer` (p {vec(VP["p"], 4)}, цель {vec(VP["target"], 4)}, fov {ru(VP["fov"], 0)}°: из грузового проёма вдоль генератора; прежняя камера оказалась бы внутри генератора); `Forest_Opening.json`: `Gen_FillNeck`. Дословно — блок `u6` → `changes`. Замки (`locks`: ключ «Generator» у `IX_ContSideDoor_85`, `IX_ContDoorL_83`, `IX_ContDoorR_84`) и шаг S7 — прежние.
'''
write('GENCONT_FOREST_CONTRACT.md', GCDOC)


# ============================================================================== ITEMS_CONTRACT.md
def unity_box(b):
    lo, hi = b
    return [-hi[0], lo[2], -hi[1]], [-lo[0], hi[2], -lo[1]]


rows = []
for n in sorted(REP):
    if not n.startswith('Item_'):
        continue
    c = CAT[n]
    ulo, uhi = unity_box(IT['items'][n]['bounds'])
    size = [uhi[i] - ulo[i] for i in range(3)]
    mats = ', '.join(m.replace('M_Item_', '') for m in REP[n]['materials'])
    dev = IT['items'][n].get('max_dev')
    rows.append(f'| `{n}` | {c["label"]} | {c["kind"]} | {ru(c["massKg"], 3).rstrip("0").rstrip(",")} | '
                f'{vec(size, 3)} | {th(REP[n]["tris"])} ({th(U3I[n]["tris"]) if n in U3I else "—"}) | '
                f'{"—" if dev is None else ru(dev * 1000, 0)} | {mats} |')
ITDOC = f'''# Предметы Forest (обновление 6) — справочник для Unity

Версия {VER} от {DATE}. 84 модели `Models/Item_*.fbx`: 83 предмета обновления 3, перестроенные в стиле генераторной (прежние имена, GUID, начала координат и размеры), и новая `Item_RadioSet` — рация пульта Leitstand для X08. Каталог — `Data/Forest_Items.json`, места — `Forest_Opening.json` (`items`) и `Forest_Dressing.json` (`props`, `notes`); префабы и поведение делает проект (F4 обновления 3). Источник чисел — `items.json` пакета `source\\assets\\forest_items`.

## Общее
- Кадр модели — кадр её FBX после импорта (Unity, Y вверх); начало координат: низ по центру; у ключей и замка — точка подвеса сверху; у фонарика — центр. Размеры совпадают с обновлением 3 (до 12 мм; мягкие вещи — мешок, мешок для мусора, сапоги, швабра, карты, опрокинутая кружка — до 3 см): коллайдеры каталога и места в данных прежние. Несколько моделей обновления 3 немного уходили ниже нуля — новые стоят на нуле (молоток и тряпка — на 3–4 мм выше нуля).
- Один меш на модель; материалы: `M_Item_Props` (атлас `T_Item_Props_A_px`, 512, 64 px/м, 128 цветов) и `M_Item_Panel` (панель надписей `T_Item_Panel_A_px`, 512: этикетки, бирки, газета, журнал, бланки, записки, карты — пиксельный шрифт; надписи на товарах — немецкие, на оборудовании — английские); у фонарика стекло — `M_TorchLens` (код меняет на `M_TorchLensOn`), у ведра с водой — `M_Water`, у рации окно канала — `M_RadioDisplay`.
- Коллайдеров в FBX нет (`Item_` в `noColliderPrefixes`): коробка из каталога (F4.1).
- Воронка, как в обновлении 3, — раструбом вверх, носиком вниз (начало — кончик носика); на полке хижины её переворачивает поза `Funnel_Hut`. Швабры и метла стоят с наклоном у стен — позы данных.

## Особые точки (каталог, кадр модели Unity)
- Фонарик: свет из {vec(CAT["Item_Flashlight"]["light"]["p"])} в направлении {vec(CAT["Item_Flashlight"]["light"]["d"])} — стекло стоит там же (передний край стекла на x = {ru(-IT["special"]["Item_Flashlight"]["lens_front_x"], 4)}).
- Канистра 20 л: ручка {vec(CAT["Item_Jerrycan20"]["grip"], 4)}, носик {vec(CAT["Item_Jerrycan20"]["spout"], 4)} — по модели.
- Ключи: бирки читаются (SCHRANKE, HAUPTGEB., GARAGE, GENERATOR), метки замков — `key` каталога, прежние.

## Рация `Item_RadioSet` (новая)
- Стационарная рация на пульте: серый корпус 0,32 × 0,24 × 0,12 м на резиновых ножках, лицевая панель (стрелочный индикатор, окно канала, кнопки, FUG 8, TRANSMIT / RECEIVE / SQUELCH), ручки, микрофон на зажиме сбоку со спиральным шнуром, кабель антенны сзади. Перед модели — −Y кадра Blender, в Unity — +Z.
- Каталог: «Рация», `itemKey` `Item_RadioSet`, 6 кг, коллайдер корпуса {vec(CAT["Item_RadioSet"]["collider"]["center"])} / {vec(CAT["Item_RadioSet"]["collider"]["size"])}, `kind: prop`, `clean: false`, `display {{off: M_RadioDisplay, on: M_RadioDisplayOn}}`, `speaker` {vec(CAT["Item_RadioSet"]["speaker"])} — точка звука над решёткой на крышке.
- Окно канала — отдельный квад с материалом `M_RadioDisplay`: тёмное стекло с незажжёнными сегментами «88.888»; `M_RadioDisplayOn` — тот же атлас + карта свечения `T_Item_Panel_E_px` (светится оранжевый канал «27.135», яркость 2). Для X08 код меняет слот окна и включает звук в `speaker`.
- Место (`Forest_Dressing.json` → `Leitstand_RadioSet_1`): p {vec(RAD["unity"]["p"], 4)}, q {vec(RAD["unity"]["q"], 6)} — в кадре `BaseMain` (Blender) {vec(RAD["building"]["origin"], 3)}, поворот 180°: полка западного пульта (x 0,90…3,90, полка y −5,16…−4,90 на высоте 0,745), у западного конца (x {ru(RAD["building"]["span_x"][0], 3)}…{ru(RAD["building"]["span_x"][1], 3)}), задняя стенка — у ступеньки к наклонной панели, лицом к оператору; кабель антенны уходит в пульт.

## Модели
Размер — габарит модели по осям Unity (x, y, z), м; «откл.» — наибольшее отклонение габарита от обновления 3, мм.

| Модель | Подпись | Вид | Масса, кг | Размер | Треугольников (было) | Откл. | Материалы |
|---|---|---|---|---|---|---|---|
''' + '\n'.join(rows) + f'''

Всего {th(ITEM_TRIS)} треугольников у 83 моделей (обновление 3 — {th(ITEM_TRIS_U3)}) и {REP["Item_RadioSet"]["tris"]} у рации.
'''
write('ITEMS_CONTRACT.md', ITDOC)


# ============================================================================== APPARITION_CONTRACT.md
import importlib.util
spec = importlib.util.spec_from_file_location('fig_bones', os.path.join(HERE, 'fig_build.py'))
FB_SRC = open(os.path.join(HERE, 'fig_build.py')).read()
B_START = FB_SRC.index('B = {')
B_END = FB_SRC.index("    B[f'Foot.{s}']")
bones_src = FB_SRC[B_START:FB_SRC.index('\n', B_END)]
ns = {}
exec(bones_src, ns)
B = ns['B']


def to_u(v):
    return [-v[0], v[2], -v[1]]


bone_rows = '\n'.join(f'| `{n}` | {"`" + p + "`" if p else "—"} | {vec(to_u(h))} | {vec(to_u(t))} |' for n, (h, t, p) in B.items())
fr = SIT['frames']
APDOC = f'''# Фигура Apparition (обновление 6) — справочник для Unity

Версия {VER} от {DATE}. Фигура для пугалок X02 (переходит дорогу в свете фар) и X03 (на заднем сиденье фургона 0,6 с): высокая худая фигура 2,3 м в длинном рваном пальто, очень длинные руки и пальцы, бледная вытянутая голова с тёмными провалами глаз и рта, тонкие босые ноги под подолом. `Models/Apparition.fbx`, пакет `source\\assets\\forest_figure` (`fig.blend`, `fig.json`).

## Файл
- Скелет `Apparition_Rig` ({len(BONES)} костей) и меш `Apparition_Body` (треугольников — {th(REP["Apparition"]["tris"])}, материал `M_Apparition`, атлас `T_Fig_Figure_A_px` {FG["atlases"]["Figure"]["size"]} px, {ru(FG["atlases"]["Figure"]["ppm"], 0)} px/м), меш привязан к скелету (до 3 костей на вершину).
- FBX 7400, Y вверх, вперёд +Z, `UnitScaleFactor` 100; записан обычным для Blender способом (без «применения» осей — оно ломает привязку): у `Apparition_Rig` и `Apparition_Body` поворот x −90°, корень префаба — без поворота. Фигура смотрит вдоль +Z префаба.
- Дубли (клипы) {FPS} к/с: {", ".join(f"`Apparition_Rig|{c}` — кадры {lo}–{hi}" for c, (lo, hi) in CLIPS.items())} (так их показывает Unity: каждый дубль начинается с кадра 0; Blender показывает их с 1). Ключи на каждом кадре у всех костей.
- Импорт в Unity: Generic, Avatar — Create From This Model, Root node — нет; клипы переименовать в `Stand`, `Walk`, `Sit`, `SitLook`; Loop Time — Walk, Stand, Sit; Bake Axis Conversion — выключено (FOREST_U6_UNITY, J4).

## Клипы
| Клип | Кадры | Длина | Петля | Начало координат | Что |
|---|---|---|---|---|---|
| `Stand` | {CLIPS['Stand'][0]}–{CLIPS['Stand'][1]} | поза | да | между стоп на земле | стоит сгорбившись, голова набок, руки висят до колен |
| `Walk` | {CLIPS['Walk'][0]}–{CLIPS['Walk'][1]} | 1,25 с | да | между стоп на земле | длинные негнущиеся шаги, руки чуть качаются; опорная стопа плоско стоит на земле, корень качается (на {ru(-min(FG["walk_root_z"].values()), 3)} м вниз), маховая стопа проходит над землёй; ноги не скользят при скорости объекта {ru(WALK, 3)} м/с вдоль +Z |
| `Sit` | {CLIPS['Sit'][0]}–{CLIPS['Sit'][1]} | поза | да | на сиденье под тазом | сидит, сложившись вперёд под низким потолком: стопы на полу {ru(SIT["seat_h"], 3)} м ниже, спина — {ru(fr["1"]["top"], 3)} м выше начала, голова опущена, руки свисают между колен (пальцы {ru(-fr["1"]["hands"], 3)} м ниже начала) |
| `SitLook` | {CLIPS['SitLook'][0]}–{CLIPS['SitLook'][1]} | 0,6 с | нет | на сиденье | из `Sit`: голова выходит вперёд из плеч и поворачивается к левому плечу фигуры, держит последний кадр |

Корень `Root` в `Sit` и `SitLook` опущен на {ru(-SIT["root"], 3)} м — так задумано (таз на сиденье). Apply Root Motion — выключено.

## Посадка (X03)
Поза `Sit` / `SitLook` рассчитана на скамью фургона `van3` (`VAN3_CONTRACT.md`): сиденье {ru(SIT["seat_h"], 3)} м над полом, потолок 0,709 м над сиденьем (низ `COL_RoofRear` на 1,94, сиденья на 1,231), стенка 0,25 м за точкой посадки. Проверено на макете: фигура ниже потолка ({ru(max(f["top"] for f in fr.values()), 3)} м над сиденьем во всех кадрах), не заходит за стенку (спина на {ru(max(f["back"] for f in fr.values()), 3)} м за точкой), стопы и пальцы — не ниже пола. Ставить на точку посадки левой скамьи (`Sit_L1` … `Sit_L4`), передом к проходу: тогда в `SitLook` лицо поворачивается к кабине и к зеркалу (камера `MirrorCam`). На правой скамье (`Sit_R1`, `Sit_R2`) голова повернётся к стенке.

## Скелет (покой, кадр префаба Unity)
| Кость | Родитель | Начало | Конец |
|---|---|---|---|
{bone_rows}

## Для пугалок (DEFERRED)
- X02: `Forest_Opening.json` → `scares` → `X02_Crossing.figure` (`model`, `clip: Walk`, `clipSpeedMps` {WALK}); переход за 2 с — `Animator.speed = v / {ru(WALK, 3)}`.
- X03: `X03_BackSeat.figure` (`clips: [Sit, SitLook]`, `seat`: левая скамья).
- Без коллайдера (`Apparition` в `noColliderPrefixes`), без сети (префаб без `NetworkObject`), Rendering Layer Mask = `defaultMask` карты (2), тени включены, Update When Offscreen — включено.
'''
write('APPARITION_CONTRACT.md', APDOC)
