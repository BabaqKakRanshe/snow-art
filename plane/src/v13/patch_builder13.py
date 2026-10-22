"""One-off: extend build_docs13.py with the v13.1 edge grip (zones 81, sockets 127, FBX 399) and fix the 20.3 ref."""
p = '/home/claude/plane/v13/build_docs13.py'
s = open(p, encoding='utf-8').read()

old_rows_line = "rows = [(OLDROWS[k], f'| {k} | Sockets | {f3(SOCK[k][\"position\"])} |  |') for k in moved]"
assert s.count(old_rows_line) == 1
extra = """
EDGE = {k: SOCK[k]['position_prefab'] for k in ('Socket_Handle_CargoDoor_L_Edge', 'Socket_Handle_CargoDoor_R_Edge')}
rows += [
    ('| Socket_Handle_CargoDoor_L_In | CargoDoor_L |',
     f'| Socket_Handle_CargoDoor_L_Edge | CargoDoor_L | {f3(EDGE["Socket_Handle_CargoDoor_L_Edge"])} |  |\\n| Socket_Handle_CargoDoor_L_In | CargoDoor_L |'),
    ('| Socket_Handle_CargoDoor_R_In | CargoDoor_R |',
     f'| Socket_Handle_CargoDoor_R_Edge | CargoDoor_R | {f3(EDGE["Socket_Handle_CargoDoor_R_Edge"])} |  |\\n| Socket_Handle_CargoDoor_R_In | CargoDoor_R |'),
    ('- FBX проверен повторным импортом в Blender. Объектов в файле: 397 (v11: + плафоны заливки и их линзы);',
     '- FBX проверен повторным импортом в Blender. Объектов в файле: 399 (v13: + сокеты ручек на передней кромке грузовых дверей; v11: + плафоны заливки и их линзы);'),
    ('Объектов в FBX: 397. Треугольников около 140 тыс. без LOD-мешей,',
     'Объектов в FBX: 399 (v13). Треугольников около 143 тыс. без LOD-мешей,'),
    ('Зоны взаимодействия лежат в `Data/interaction_volumes.json`, всего 79: 44 прежних (v6), 21 новая в v7 — `SW_CabinDoor_L/R`, 17 ручек `Knob_*`, `Socket_Keyhole_PilotDoor_L/R` (kind `lock`) — и 14 новых в v9: четыре `PaxSeat_*` (kind `seat`), четыре `PaxSeatFold_*` (kind `hinge`), шесть `Stow_*` (kind `stow`), разделы 10.1 и 10.2.',
     'Зоны взаимодействия лежат в `Data/interaction_volumes.json`, всего 81: 44 прежних (v6), 21 новая в v7 — `SW_CabinDoor_L/R`, 17 ручек `Knob_*`, `Socket_Keyhole_PilotDoor_L/R` (kind `lock`) — 14 новых в v9: четыре `PaxSeat_*` (kind `seat`), четыре `PaxSeatFold_*` (kind `hinge`), шесть `Stow_*` (kind `stow`), разделы 10.1 и 10.2 — и 2 новые в v13: `Socket_Handle_CargoDoor_L/R_Edge` (kind `door`, ручка на передней кромке сдвижной двери, раздел 3.1).'),
    ('| Ручки | Socket_Handle_{PilotDoor,CargoDoor}_{L,R}_{In,Out} | ручки дверей изнутри и снаружи; v5: внутренние стоят на новых ручках обивки |',
     '| Ручки | Socket_Handle_{PilotDoor,CargoDoor}_{L,R}_{In,Out}, v13: Socket_Handle_CargoDoor_{L,R}_Edge | ручки дверей изнутри и снаружи; v5: внутренние стоят на новых ручках обивки; v13: `_Edge` — тёмная накладка на передней кромке сдвижной двери: когда дверь сдвинута назад, кромка стоит у заднего края проёма и достаётся изнутри отсека (внутренняя ручка тогда за стойкой проёма) |'),
]"""
s = s.replace(old_rows_line, old_rows_line + extra)

R = [
    ('- `COL_CargoDoor_L/R` — прежняя оболочка двери со стеклом (кронштейны роликов в неё не входят), едет с дверью.',
     '- `COL_CargoDoor_L/R` — прежняя оболочка двери со стеклом (кронштейны роликов в неё не входят), едет с дверью.\n'
     '- Ручка на кромке (v13): тёмная накладка 24 см на передней кромке двери, сокет и зона `Socket_Handle_CargoDoor_L/R_Edge` (kind `door`). У открытой двери передняя кромка стоит у заднего края проёма — за неё дверь закрывают изнутри отсека: внутренняя ручка `_In` у сдвинутой двери уходит за стойку проёма, луч из отсека её не достаёт. В закрытом положении зона лежит в щели 6 мм между кромкой и передней стойкой проёма.'),
    ('| `CargoDoor_L/R` | — | + ролики на кронштейнах (три на дверь) |',
     '| `CargoDoor_L/R` | — | + ролики на кронштейнах (три на дверь), ручка-накладка на передней кромке |\n'
     '| Зоны, сокеты | 79 / 125 | 81 / 127: + `Socket_Handle_CargoDoor_L/R_Edge` (сокет и зона kind `door`, ручка на передней кромке) |'),
    ('Не изменились: имена, иерархия и pivot всех частей, остальные каналы Rig, 60 коллайдеров, 79 зон, 16 источников света, LOD-группы и теневые копии, остальные `Data/*.json`, атласы. Треугольники вблизи: 143.0 тыс. (v12 — 140.1 тыс.).',
     'Не изменились: имена, иерархия и pivot всех частей, остальные каналы Rig, 60 коллайдеров (те же меши), прежние 79 зон, 16 источников света, LOD-группы и теневые копии, остальные `Data/*.json`, атласы. Объектов в FBX 399 (v12 — 397: + два сокета ручек). Треугольники вблизи: 143.0 тыс. (v12 — 140.1 тыс.).'),
    ('- **Огни.** Если код читает позиции сокетов огней',
     '- **Ручки на кромке.** Две новые зоны `Socket_Handle_CargoDoor_L/R_Edge` (kind `door`): код игры должен их обработать — изнутри как `_In`, снаружи как `_Out` (с замком). Без них открытую дверь без питания изнутри не закрыть.\n'
     '- **Огни.** Если код читает позиции сокетов огней'),
    ('65. v13, установка: меню пишет те же числа, что у v12 (60 коллайдеров, 79 зон, 16 источников, LOD 3 + 3, 5 теневых копий), и `Done (URP), v13`;',
     '65. v13, установка: меню пишет 60 коллайдеров, 81 зону (v12 — 79), 16 источников, LOD 3 + 3, 5 теневых копий и `Done (URP), v13`;'),
    ('70. v13, коллайдер: в Scene view с отображением физики `COL_CargoDoor_*` едет с дверью и совпадает с ней на всём ходу; зоны ручек `IV_Socket_Handle_CargoDoor_*` едут с дверью.',
     '70. v13, коллайдер и ручки: в Scene view с отображением физики `COL_CargoDoor_*` едет с дверью и совпадает с ней на всём ходу; зоны ручек `IV_Socket_Handle_CargoDoor_*` едут с дверью; при `cargoDoorL` = 1 луч из отсека (стоя у проёма, взгляд назад вдоль борта) попадает в `IV_Socket_Handle_CargoDoor_L_Edge` у заднего края проёма.'),
    ('восемь сокетов наружных огней сдвинуты в корпуса (приложение А); коллайдеры прежние; закрылки',
     'восемь сокетов наружных огней сдвинуты в корпуса (приложение А); две новые зоны-ручки на передней кромке грузовых дверей `Socket_Handle_CargoDoor_L/R_Edge` — ими открытую дверь закрывают изнутри (обработать как ручки); коллайдеры прежние; закрылки'),
    ('  - FBX: состав объектов, имена, иерархия и pivot — как в v12; изменились меши',
     '  - FBX: состав объектов, имена, иерархия и pivot — как в v12, плюс два сокета ручек на кромке грузовых дверей (399 объектов); изменились меши'),
    ('из `Data/*.json` изменились только `sockets.json` (8 сокетов огней), `lod.json`, `lights.json`, `atlas_texel.json`, новый `doors.json`;',
     'из `Data/*.json` изменились только `sockets.json` (8 сокетов огней сдвинуты, 2 новых), `interaction_volumes.json` (2 новые зоны), `lod.json`, `lights.json`, `atlas_texel.json`, новый `doors.json`;'),
    ('| CargoDoor_L | грузовая дверь, левый борт; v13: сдвижная, три ролика на кронштейнах | `SW_CargoDoor_L` из кабины, ручки изнутри и снаружи |',
     '| CargoDoor_L | грузовая дверь, левый борт; v13: сдвижная, три ролика на кронштейнах | `SW_CargoDoor_L` из кабины, ручки изнутри и снаружи; v13: ручка на передней кромке (`_Edge`) — закрыть открытую дверь изнутри |'),
    ('Одно поле Rig на дверь (`cargoDoorL` / `cargoDoorR`); формула — в контракте (раздел 3.1) и в `UtilityPlaneRig.SlidingDoorPose`.',
     'Одно поле Rig на дверь (`cargoDoorL` / `cargoDoorR`); формула — в контракте (раздел 3.1) и в `UtilityPlaneRig.SlidingDoorPose`. На передней кромке двери — тёмная ручка-накладка с зоной `Socket_Handle_CargoDoor_L/R_Edge`: у открытой двери кромка стоит у заднего края проёма, за неё дверь закрывают изнутри.'),
    ('Модель этого не запрещает — правило игры (раздел 20.3).', 'Модель этого не запрещает — правило игры (раздел 20.1).'),
    ("""    ('# Utility Plane v12 — пакет для Unity', '# Utility Plane v13 — пакет для Unity'),""",
     """    ('# Utility Plane v12 — пакет для Unity', '# Utility Plane v13 — пакет для Unity'),
    ('60 выпуклых коллайдеров из прокси `COL_*`, 79 зон `IV_*`,',
     '60 выпуклых коллайдеров из прокси `COL_*`, 81 зону `IV_*` (v13: + ручки на кромке грузовых дверей),'),"""),
    ('изменились: `UtilityPlane.fbx`, `Data/sockets.json`, `lod.json`, `lights.json`, `atlas_texel.json`, `UtilityPlaneRig.cs`, `UtilityPlaneSetup.cs` |',
     'изменились: `UtilityPlane.fbx`, `Data/sockets.json`, `interaction_volumes.json`, `lod.json`, `lights.json`, `atlas_texel.json`, `UtilityPlaneRig.cs`, `UtilityPlaneSetup.cs` |'),
]
for a, b in R:
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('builder updated')
