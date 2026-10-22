"""Generate WINTER_KIT.md (Russian) from Data/winter_kit.json: python3 docs_kit/make_kit_docs.py"""
import json, os, math
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(HERE, 'export', 'unity_kit', 'Assets', 'UtilityPlane')
D = json.load(open(os.path.join(KIT, 'Data', 'winter_kit.json')))
items, carry, atl = D['items'], D['carry'], D['atlases']
EFF_RU = {
    'engineStartBlocked': 'запуск запрещён',
    'airspeedBlocked': 'указатель скорости на нуле',
    'liftBlocked': 'взлёт запрещён',
    'viewBlocked': 'стекло закрыто',
    'engineInsulated': 'мотор остывает медленнее',
    'wheelsHeld': 'колёса застопорены',
    'tiedDown': 'самолёт пришвартован',
    'preheating': 'идёт прогрев',
    'moveBlocked': 'двигать нельзя',
}
C = {c['prefab']: c for c in carry}
tris_inst = sum(i['tris'] for i in items)
tris_carry = sum(c['tris'] for c in carry)
L = []
w = L.append
w('# Зимний комплект и канистра — дополнение к Utility Plane v7')
w('')
w('Предполётный комплект для стоянки зимой: заглушки, чехлы, колодки, швартовка, подогреватель двигателя, '
  'плюс канистра и воронка для заправки. Ставится поверх пакета v7: модель самолёта, его FBX и шейдеры не меняются.')
w('')
w('## 1. Состав')
w('')
w('Каждая вещь есть в двух видах: **установленный** (часть префаба WinterKit, стоит на самолёте) и **переносной** '
  '(отдельный префаб Prefabs/Kit/KitCarry_<Key>, его носят в руках). Ид установленных вещей = значения enum `KitItem`.')
w('')
w('| Ид (KitItem) | Что это | Переносной вид | Масса, кг | Последствие | Время, с (предложение) |')
w('|---|---|---|---|---|---|')
for it in items:
    c = C[it['carry']]
    eff = ', '.join(EFF_RU[e] for e in it['effects'])
    if it['excludes']:
        eff += '; не вместе с ' + ', '.join(it['excludes'])
    mass = f"{c['massKg']:g}" + (' (сумка, 3 комплекта)' if c['prefab'] == 'KitCarry_TieDownBag' else '')
    w(f"| {it['id']} | {it['label']} | {c['prefab']} | {mass} | {eff} | {it['installSeconds']:g} |")
w('')
w('Прочие переносные вещи (на самолёт не ставятся):')
w('')
for c in carry:
    if c['prefab'] in ('KitCarry_JerryCan', 'KitCarry_Funnel'):
        if c['prefab'] == 'KitCarry_JerryCan':
            w(f"- {c['prefab']} — канистра {c['capacityL']:g} л: пустая {c['massKg']:g} кг, полная (Jet A-1, 0.80 кг/л) "
              f"{c['fullMassKg']:g} кг; точка слива `Socket_Pour`.")
        else:
            w(f"- {c['prefab']} — {c['label'][0].lower() + c['label'][1:]}, {c['massKg']:g} кг.")
w('')
w('Сколько чего в полном комплекте: заглушек выхлопа 2, сумок с чехлом крыла 2, пар основных колодок 2, '
  'в сумке швартовки 3 комплекта (анкер + верёвка); остальное по одному.')
w('')
w('## 2. Файлы')
w('')
w('Всё кладётся в те же папки, что и v7 (ни один файл v7 не заменяется):')
w('')
w('- `Models/SM_WinterKit.fbx` — корень WinterKit и 15 установленных форм `Kit_<Item>` в системе координат '
  'префаба самолёта (пивот каждой = её сокет, поворот нулевой); '
  f'{tris_inst} треугольников на всё вместе;')
w(f'- `Models/SM_Kit_*.fbx` — 12 переносных форм, пивот в центре низа, дочерние `Socket_Grip` (точка хвата, '
  f'цель IK руки) и у канистры `Socket_Pour`; {tris_carry} треугольников на все;')
w('- `Textures/T_KitCovers_*` (чехлы, 4K) и `T_KitProps_*` (остальное, 4K): BaseColor, Normal (OpenGL), MaskMap '
  '(как в v7: R металл, G AO, B 1, A гладкость), `_DetailMask` (1K, где лежит детальная ткань); '
  '`T_Detail_Fabric_Albedo/_Normal` (512, плетение ткани, тайлится);')
w('- `Data/winter_kit.json` — вещи, зоны, сокеты, последствия, переносные формы; `Data/kit_texel.json` — плотность '
  'текселей и тайлинг детальной ткани;')
w('- `Scripts/UtilityPlaneWinterKit.cs`, `Scripts/UtilityPlaneKitItem.cs` (runtime), '
  '`Editor/UtilityPlaneWinterKitSetup.cs` (меню).')
w('')
w('Плотность текселей: ' + '; '.join(f"{a['atlas']} {a['pxPerMetre'] / 100:.1f} px/см (детальная ткань — тайлинг "
                                     f"{a['detailTiling']:g} на UV)" for a in atl) +
  '. Мелкие вещи (канистра, заглушки, колодки) упакованы плотнее — до ×1.6.')
w('')
w('## 3. Установка в Unity')
w('')
w('1. Нужен установленный v7 (меню Tools/Utility Plane/Build Materials + Prefabs уже выполнено) с исправлением '
  'детальных карт для URP в `Editor/UtilityPlaneSetup.cs` (строка `ti.sRGBTexture = DetectPipeline() != "URP";`).')
w('2. Скопировать файлы пакета в `Assets/UtilityPlane/` (те же подпапки).')
w('3. Tools / Utility Plane / **Install Winter Kit**. Делает: материалы M_KitCovers и M_KitProps; 12 переносных '
  'префабов `Prefabs/Kit/KitCarry_<Key>`; `Prefabs/WinterKit.prefab` (15 установленных форм выключены, 15 зон '
  '`IV_Kit_<Item>`, точки `Attach_*`, компонент `UtilityPlaneWinterKit`); вкладывает WinterKit в '
  '`Prefabs/UtilityPlane.prefab` (корень, локально ноль). Если WinterKit там уже есть, его не трогает (настройки '
  'варианта сохраняются).')
w('4. Вариант игры (`UtilityPlane_Game.prefab`) наследует WinterKit от базового префаба — второй не добавлять. После '
  'каждого повторного Build Materials + Prefabs (он пересобирает UtilityPlane.prefab) — снова Install Winter Kit. Если '
  'у вас свой префаб самолёта не от UtilityPlane.prefab, положите WinterKit.prefab под его корень с нулевым трансформом.')
w('5. Rigidbody и сетевой объект переносным вещам добавлять в своих вариантах префабов `KitCarry_*` (в папке игры), '
  'а не в префабах пакета: меню пересоздаёт их при каждом запуске.')
w('')
w('## 4. Как работает')
w('')
w('`UtilityPlaneWinterKit` только хранит состояние и показывает/прячет формы. Решает сервер.')
w('')
w('- `SetInstalled(KitItem, bool)` возвращает true, только если состояние изменилось; false — уже так было или вещь '
  'исключена (`CanInstall`: подогреватель и заглушка воздухозаборника занимают один воздухозаборник). Выдавать и '
  'забирать переносные вещи — только по true. `IsInstalled(item)`, `GetSlot(item)`.')
w('- `Mask` (int, бит i = KitItem i) — реплицировать; на клиентах `ApplyMask(mask)`. Событие `Changed(item, on)`.')
w('- Слоты (`slots`): форма, `label`, `installSeconds` (предлагаемое время), `groundItem`, `carryPrefab` (какая '
  'переносная вещь получается при снятии; выдавать её вариант из папки игры с Rigidbody и сетевым объектом — '
  'по `UtilityPlaneKitItem.key`, через таблицу в игре), `attach` (у швартовок — узел на самолёте, у подогревателя — '
  'конец рукава в воздухозаборнике). Всё это есть и в `Data/winter_kit.json`, но в игре читать из префаба.')
w('- Флаги: `EngineStartBlocked`, `AirspeedBlocked`, `LiftBlocked`, `ViewBlocked`, `EngineInsulated`, `WheelsHeld`, '
  '`TiedDown`, `Preheating`, `MoveBlocked` (колодки, швартовка или подогреватель — самолёт не рулит и не буксируется), '
  '`ReadyForFlight` (ничего не стоит), `InstalledItems()` — для чек-листа обхода. Маски флагов — `EngineStartMask`, '
  '`LiftMask`, `ChocksMask`, `TieDownMask`, `MoveMask`.')
w('- Зоны `IV_Kit_<Item>` (слой Interact, `UtilityPlaneInteractable` kind `kit`, id = KitItem) работают и когда вещь '
  'стоит, и когда нет: с подходящей переносной вещью в руках — установить, по установленной — снять. Подходит та '
  'переносная вещь, у которой в `UtilityPlaneKitItem.installs` есть этот KitItem. Луч использования (слой Interact) '
  'проходит сквозь самолёт, поэтому зоны достаются и из кабины: `SetZonesEnabled(false)`, пока самолёт движется или '
  'в воздухе, и правило сервера — kind `kit` только для игрока снаружи, на земле, у стоящего самолёта.')
w('- Переносные префабы `KitCarry_<Key>`: в корне меш, выпуклый MeshCollider на слое Default и `UtilityPlaneKitItem` '
  '(massKg, count, sets, installs, grip, pour; у канистры capacityLitres; изменяемые `fuelLitres` и `setsLeft` — '
  'реплицировать; `TotalMassKg` = масса + топливо). Дочерний `IV_KitItem` — триггер на слое Interact с '
  '`UtilityPlaneInteractable` kind `kit_item`: луч попадает в него, вещь — `GetComponentInParent<UtilityPlaneKitItem>()`.')
w('- Колодки при показе опускаются/поднимаются на землю под собой (луч вниз; свои коллайдеры самолёта, триггеры и '
  'тела с Rigidbody не считаются; не больше `maxSnap` = 0.3 м; `snapChocksToGround`, `groundMask`, `aircraftRoot`). '
  'После спавна, когда самолёт осел, вызвать `SnapChocks()`. Анкеры, верёвки и подогреватель стоят как смоделированы: '
  'их верёвки и рукав привязаны к точкам на самолёте.')
w('- У установленных форм нет коллайдеров: они дочерние объекты самолёта, их коллайдеры стали бы частью его '
  'физического тела (колодки упёрлись бы в землю, самолёт поднялся бы). Сквозь подогреватель и колодки можно пройти; '
  'если это мешает — отдельный статический коллайдер в сцене на слое, который не сталкивается с самолётом.')
w('- Лучи подвески колёс и проверки земли у персонажей должны игнорировать триггеры (`QueryTriggerInteraction.Ignore`) '
  'или слой Interact: зоны колодок, швартовок и подогревателя лежат у земли.')
w('- Пока стоит чехол крыла, закрылки и элероны держать в нейтрали (входы Rig = 0): чехол закрывает их целиком.')
w('')
w('## 5. Зоны и высоты')
w('')
w('Зоны не пересекаются друг с другом и с 65 зонами v7. Зона чехла стекла наклонена вдоль стекла и лежит снаружи кабины, чтобы не перехватывать лучи к приборной доске и козырькам. Зоны вещей на земле стоят ровно по земле (поворот по X на угол стоянки); зона колодок — только передняя колодка, чтобы луч подвески от оси её не задевал. Высота над ровной землёй на стоянке (центр; низ … верх), м:')
w('')
w('| Ид | Центр | Низ … верх |')
w('|---|---|---|')
for it in items:
    h = it.get('parkedHeight')
    if h:
        w(f"| {it['id']} | {h[0]:.2f} | {h[1]:.2f} … {h[2]:.2f} |")
w('')
w('Чехлы крыльев снимаются/надеваются за задний край (≈2.4 м над землёй — достаёт рука); если хотите, требуйте '
  'стремянку. Чехол стекла и чехол двигателя — с земли или с подножки.')
w('')
w('## 6. Канистра и заправка')
w('')
w('Канистра 20 л: корпус 470×340×165 мм (NATO), с ручками и рёбрами 476×340×189 мм. Заливают через горловину бака на крыле (`Socket_FuelCap_L/R`, v7) со '
  'стремянки (`Socket_Ladder_Fuel_L/R`, v7) через воронку с сеткой-фильтром. Предложение: 10 л/мин, '
  '`fuelLitres` канистры уменьшается, `TotalMassKg` = масса + литры × 0.8.')
w('')
w('## 7. Открытые вопросы (решает геймдизайн)')
w('')
w('- Что делать при запуске с заглушками/чехлом: отказ стартера или повреждение двигателя.')
w('- Чехлы крыльев: запрет взлёта целиком или потеря подъёмной силы на одном крыле; нужна ли стремянка.')
w('- Подогреватель: откуда питание/топливо, скорость прогрева, нужен ли включатель.')
w('- Где хранится комплект (грузовой отсек, ящик на стоянке) и сколько комплектов в мире.')
w('- Колодки на неровной земле: оставить подгонку по высоте или ставить по наклону.')
open(os.path.join(KIT, 'WINTER_KIT.md'), 'w').write('\n'.join(L) + '\n')
print('WINTER_KIT.md', len(L), 'lines')
