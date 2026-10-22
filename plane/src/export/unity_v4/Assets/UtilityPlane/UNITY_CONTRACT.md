# Utility Plane v4: технический контракт для Unity

Имена объектов, оси, знаки, формулы стрелок, материалы, сокеты, коллайдеры и зоны взаимодействия. Назначение деталей и связь с системами игры описаны в `COMPONENTS.md`, установка — в `README.md`.

Состояние: FBX проверен повторным импортом в Blender, позиции всех 229 объектов совпали с исходником с точностью до 0.001 мм. Скрипты C# скомпилированы без ошибок и предупреждений против заглушек API Unity (C# 7.3 и 9.0). В самом Unity ничего не запускалось: знаки поворотов выведены из геометрии и нуждаются в проверке глазами на стенде (раздел 11).

## 1. Оси, единицы, начало координат

- Метры. +Z — нос, +Y — вверх, +X — правое крыло (правый борт). Левосторонняя система Unity.
- Начало координат префаба — на земле под грузовым отсеком. Стоянка горизонтальная: основные и хвостовое колёса касаются Y = 0, пол кабины горизонтален (Y = 1.07).
- У всех подвижных частей в покое нулевой поворот. Исключение — элероны и закрылки: у них в покое есть поворот на поперечное V крыла (2°).
- Pivot каждой подвижной части стоит на её оси вращения (петля, ось колеса, ось стрелки). Кабина (`Cockpit`) стоит в начале координат, поэтому её локальные координаты совпадают с координатами префаба.
- Поворот применяется так: `transform.localRotation = restRotation * Quaternion.Euler(x, y, z)`, то есть в локальных осях детали. Так делает `UtilityPlaneRig`.
- Правило стрелок: поворот по часовой стрелке, как видит пилот, — это **отрицательный** угол вокруг локальной Z.

Конвертация из других пакетов:
- из Blender (нос −Y, пилот +X, вверх +Z): Unity (x, y, z) = (−x, z, −y);
- из UE-пакета (X вперёд, Y вправо, Z вверх, см): Unity (X, Y, Z) = (Y, Z, X) / 100;
- повороты из UE-пакета: Unity X = −Pitch, Unity Y = +Yaw, Unity Z = −Roll.

## 2. Иерархия `UtilityPlane.fbx`

```
UtilityPlane                      корень, сюда Rigidbody и UtilityPlaneRig
  Body                            фюзеляж, крыло, оперение, подкосы, капот, салон (M_Airframe, M_Cockpit, M_Details)
  Glass                           неподвижное остекление (M_Glass)
  Propeller                       винт и кок; внутри COL_Propeller
  Gear_L / Gear_R                 рессорные стойки → Wheel_L / Wheel_R; внутри COL_Gear_L / _R
  TailGear → TailWheel_Fork → TailWheel
  Rudder, Elevator_L/R, Aileron_L/R, Flap_L/R
  PilotDoor_L/R, CargoDoor_L/R    двери; внутри <Door>_Glass, COL_<Door>, сокеты ручек
  FuelCap_L/R                     крышки горловин
  Lens_Nav_L/R, Lens_Nav_Tail, Lens_Strobe_L/R, Lens_Beacon_Top/Bottom, Lens_Landing
  Sockets                         56 сокетов экстерьера (пустые объекты)
  Colliders                       30 выпуклых прокси COL_*
  Cockpit                         пустой, в начале координат
    Cockpit_Static                вся неподвижная кабина (M_Cockpit, M_GaugeGlass, M_CargoNet, M_Gauges)
    Yoke_P → Yoke_P_Roll, Yoke_C → Yoke_C_Roll
    PedalP_L/R, PedalC_L/R
    Lever_Power, Lever_Prop, Lever_Condition, Lever_Flap, TrimWheel
    SW_* (13 тумблеров), Btn_AnnunTest, Pull_* (4), Rheo_Panel, Rheo_Flood, FuelSel_L/R
    Visor_P/C, Belt_P_On/Off, Belt_C_On/Off
    Needle_* (15), Clock_Hour/Min, ATT_Roll → ATT_Pitch, HDG_Card, TC_Plane, TC_Ball
    Lamp_00 … Lamp_11             лампы табло, pivot в центре лампы
    Lens_Dome, Lens_CargoLight    линзы плафонов
    Display_GPS                   точка для экрана GPS
    сокеты кабины
SM_Cargo_Case1..6.fbx             ящики отдельными файлами, pivot в центре дна
```

Треугольников: экстерьер около 28k, кабина около 50k, коллайдеры по 12–240 каждый.

## 3. Экстерьер: каналы и знаки

| Объект | Ось | Диапазон | Знак |
|---|---|---|---|
| Propeller | Z | непрерывно, RPM × 6 °/с | отрицательный: по часовой стрелке, если смотреть из кабины |
| Wheel_L, Wheel_R | X | непрерывно, r = 0.484 м | + = качение вперёд |
| TailWheel | X | непрерывно, r = 0.285 м | + = качение вперёд |
| Gear_L | Z | 0 … −12° (≈ 12 см хода колеса) | сжатие = отрицательный угол |
| Gear_R | Z | 0 … +12° | сжатие = положительный угол |
| TailGear | X | 0 … +8° | сжатие = положительный угол |
| TailWheel_Fork | Y | ±30° | + = передняя часть колеса вправо |
| Rudder | Y | ±25° | руль вправо (задняя кромка вправо) = **отрицательный** Y |
| Elevator_L, Elevator_R | X | −25 … +15° | + = задняя кромка вверх |
| Aileron_R | X | ±20° | + = задняя кромка вверх |
| Aileron_L | X | ±20° | + = задняя кромка вверх; при крене вправо левый идёт вниз, поэтому в Rig −aileron |
| Flap_L, Flap_R | X | 0 … −35° (ступени 0/10/20/35) | вниз = отрицательный |
| PilotDoor_L | Y | 0 … +70° | петля спереди, открытие наружу |
| PilotDoor_R | Y | 0 … −70° | петля спереди |
| CargoDoor_L | Y | 0 … −100° | петля на задней кромке |
| CargoDoor_R | Y | 0 … +100° | петля на задней кромке |
| FuelCap_L, FuelCap_R | X | 0 … −110° | петля на задней кромке, открывается вверх |

## 4. Кабина: каналы и знаки

| Объект | Канал | Диапазон | Знак |
|---|---|---|---|
| Yoke_P, Yoke_C | смещение по локальной Z | ±0.08 м | + = от себя |
| Yoke_P_Roll, Yoke_C_Roll | поворот Z | ±50° | вправо = отрицательный (по часовой) |
| PedalP_L / PedalC_L | поворот X | ±12° | правая педаль вперёд → левая −12·p |
| PedalP_R / PedalC_R | поворот X | ±12° | правая педаль вперёд → +12·p |
| Lever_Power, Lever_Prop, Lever_Condition | поворот X | ±25° | + = вперёд |
| Lever_Flap | поворот X | 0, −12, −24, −36° | ступень × −12° |
| TrimWheel | поворот X | свободно | на кабрирование = отрицательный |
| SW_* (13 тумблеров) | поворот X | 0 / +40° | +40 = вверх = ВКЛ; SW_Starter кнопочный: держать, пока нажат |
| Btn_AnnunTest | смещение по Z | 0 / +0.003 м | нажата = +0.003 (в панель) |
| Pull_CabinHeat, Pull_Defrost, Pull_ParkBrake, Pull_FuelShutoff | смещение по Z | 0 … −0.06 м | вытянута = −0.06 (к пилоту) |
| Rheo_Panel, Rheo_Flood | поворот Z | 0 … −270° | по часовой = ярче |
| FuelSel_L, FuelSel_R | поворот X | 0 / +60° | 0 = ON (ручка вниз), +60 = OFF |
| Visor_P, Visor_C | поворот X | 0 … −80° | опущен = −80 |
| Belt_P_On / Belt_P_Off, Belt_C_On / Belt_C_Off | localScale | 1 / 0 | видна одна из пары |

## 5. Приборы

У стрелок в `UtilityPlaneRig` пружина второго порядка: ω = 11 рад/с, ζ = 0.6. Это даёт небольшой перелёт. Для часов, высотомера и курса используется перенос через 360°. Угол задаётся вокруг локальной Z, отрицательный угол = по часовой стрелке.

| Объект | Величина | Угол, ° | Шкала |
|---|---|---|---|
| Needle_ASI | приборная скорость, kt | −1.6 · IAS | 0…200 |
| Needle_ALT100 | высота, ft | −0.36 · (ft mod 1000) | один оборот = 1000 ft |
| Needle_ALT1000 | высота, ft | −0.036 · (ft mod 10000) | один оборот = 10000 ft |
| Needle_VSI | вертикальная скорость, fpm | −0.0825 · fpm | ±2000 |
| Needle_TRQ | крутящий момент, ft·lb | −0.1125 · Q | 0…2400 |
| Needle_PROP | обороты винта | −0.1125 · RPM | 0…2400 |
| Needle_ITT | температура газов, °C | −0.27 · (ITT − 100) | 100…1100 |
| Needle_NG | обороты газогенератора, % | −2.4545 · Ng | 0…110 |
| Needle_OILP | давление масла, psi | −0.6 · P | 0…200 |
| Needle_OILT | температура масла, °C | **+0.8** · T | 0…150, эта стрелка идёт против часовой |
| Needle_FF | расход топлива, pph | −0.675 · FF | 0…400 |
| Needle_FUELL, Needle_FUELR | топливо в баке, gal | −2 · gal | 0…60 |
| Needle_AMP | ток, A | −1.5 · A | −60…+60 |
| Needle_OAT | наружная температура, °C | −3 · (T + 20) | −40…+50 |
| Clock_Hour, Clock_Min | время | −30 · h, −6 · min | без пружины |
| ATT_Roll | крен, ° | +bank | карточка поворачивается против крена |
| ATT_Pitch (внутри ATT_Roll) | тангаж, ° | смещение по локальной Y: −0.0006 · pitch, м | ±20° |
| HDG_Card | курс, ° | +heading | карточка вращается |
| TC_Plane | угловая скорость поворота, °/с | −(20/3) · rate | ±6 °/с, стандартный разворот 3 °/с = 20° |
| TC_Ball | скольжение, −1…+1 | +15 · slip | + = шарик вправо |

Прибор показывает выход своей модели датчика, а не истину: запаздывание, ошибки, отказ по питанию.

## 6. Табло сигнализации

Табло состоит из 12 отдельных рендереров `Lamp_00` … `Lamp_11` с материалом `M_Annunciator`. Надпись напечатана в атласе `T_Gauges_BC`; этот же атлас служит картой свечения. Лампа горит, когда её `_EmissionColor` (URP/Built-in) или `_EmissiveColor` (HDRP) не чёрный. Цвет свечения берётся из надписи.

| Lamp | Надпись | Цвет | Условие |
|---|---|---|---|
| 00 | OIL PRESS | красный | давление масла ниже нормы при работающем двигателе |
| 01 | ENG HOT | красный | ITT выше порога |
| 02 | FUEL LOW L | жёлтый | мало топлива в левом баке |
| 03 | FUEL LOW R | жёлтый | мало топлива в правом баке |
| 04 | GEN OFF | жёлтый | генератор не заряжает |
| 05 | BATT LOW | жёлтый | низкое напряжение аккумулятора |
| 06 | STARTER ON | зелёный | стартер крутит |
| 07 | IGNITION | зелёный | зажигание включено |
| 08 | DOOR | жёлтый | открыта или не заперта дверь кабины |
| 09 | CARGO DOOR | жёлтый | грузовая дверь не закрыта |
| 10 | CARGO LOOSE | жёлтый | в отсеке есть незакреплённый груз |
| 11 | SEAT BELT | жёлтый | занятое кресло с расстёгнутым ремнём |

- `Btn_AnnunTest`: пока кнопка нажата, горят все 12 ламп.
- Без питания шины не горит ни одна лампа, даже при нажатой кнопке теста.
- Надписи в том же порядке лежат в коде: `UtilityPlaneRig.LampLegends`.

## 7. Огни, линзы, подсветка

| Рендерер | Материал | Источник света `Light_<ключ>` | Built-in/URP | HDRP, кд | Сокет |
|---|---|---|---|---|---|
| Lens_Nav_L | M_Light_Red | Nav_L: Point, красный, 3 м | 2 | 40 | Socket_Nav_L |
| Lens_Nav_R | M_Light_Green | Nav_R: Point, зелёный, 3 м | 2 | 40 | Socket_Nav_R |
| Lens_Nav_Tail | M_Light_White | Nav_Tail: Point, белый, 3 м | 2 | 20 | Socket_Nav_Tail |
| Lens_Strobe_L/R | M_Light_White | Strobe_L/R: Point, 10 м, двойная вспышка раз в 1.2 с | 8 | 800 | Socket_Strobe_L/R |
| Lens_Beacon_Top/Bottom | M_Light_Beacon | Beacon_Top/Bottom: Point, красный, 8 м, импульс раз в 1.33 с | 4 | 150 | Socket_Beacon_Top/Bottom |
| Lens_Landing | M_Light_Landing | Landing: Spot 28°, 150 м, вниз 4° | 12 | 50 000 | Socket_Landing |
| Lens_Dome | M_Light_Cabin | Light_Dome_L/R: два Point, 1.8 м | 0.8 | 2 | Socket_Light_Dome_L/R |
| Lens_CargoLight | M_Light_Cabin | Light_Cargo: Point, 3 м | 1 | 4 | Socket_Light_Cargo |
| — | — | Light_Flood: Spot 100°, 1.5 м, вниз на панель | 0.6 | 3 | Socket_Light_Flood |
| Cockpit_Static, подматериал M_Gauges | M_Gauges | — | — | — | подсветка шкал от `panelLight` |

- Свечение задаётся через `MaterialPropertyBlock.SetVector` линейным значением. `SetColor` не подходит: значения больше 1 он пересчитывает как sRGB. Общие материалы не меняются, копии не создаются. Рендереры с MPB выпадают из SRP Batcher — это 22 небольших объекта (лампы и линзы) и `Cockpit_Static`.
- Источники света кладёт в префаб меню установки: объекты `Light_<ключ>` внутри сокетов, выключенные. `Light.intensity` в префабе — это 100 % яркости: её можно подстроить в префабе, и Rig умножает её на 0…1. Если префаб собран без источников, Rig создаёт их в `Awake` (флаг `createLights`).
- HDRP (Unity 6): к каждому источнику добавляется `HDAdditionalLightData`. `Light.intensity` пишется в канделах — это родная единица точечных и прожекторных источников. Все значения **TEMPORARY**: от них требуется быть видимыми, реальные огни самолёта сертифицируются по минимальной силе света, а не по этим цифрам.
- Свечение линз и ламп в HDRP умножается на `hdrpEmissionScale` (по умолчанию 400 нит на единицу, **TEMPORARY**, подбирается под экспозицию сцены).
- Поля `navLights` … `cargoLight` в Rig — фактическая яркость 0…1. Выключатели, питание и просадку напряжения учитывает ваш код, а вспышки строба и маяка Rig делает сам.
- В URP Forward по умолчанию до 8 дополнительных источников на объект. Если часть огней на корпусе пропадает, нужен Forward+.

## 8. Материалы

| Материал | Шейдер | Текстуры | Примечание |
|---|---|---|---|
| M_Airframe | Lit | T_Airframe_BaseColor / Normal / MetallicSmoothness / AO, 4K | обшивка, крыло, оперение, рули, двери снаружи, крышки |
| M_Details | Lit | T_Details_*, 2K | шасси, колёса, винт, выхлоп, антенны, ящики |
| M_Cockpit | Lit | T_Cockpit_*, 4K | кабина, салон, двери изнутри, стрелки |
| M_Gauges | Lit + свечение | T_Gauges_BC (цвет и свечение) | шкалы, таблички, надписи АЗС; подсветка через MPB |
| M_Annunciator | Lit + свечение | T_Gauges_BC | 12 ламп табло |
| M_Glass | Transparent | — | остекление, двустороннее |
| M_GaugeGlass | Transparent | — | стёкла приборов |
| M_CargoNet | Cutout, двусторонний | T_CargoNet_BCA | грузовая сетка |
| M_Light_Red / Green / White / Beacon / Landing / Cabin | Lit + свечение | — | линзы, свечение чёрное до команды |

Раскладка текстур:
- `_Normal` — в формате OpenGL (+Y), импортируется как Normal Map;
- `_MetallicSmoothness` — R металличность, A гладкость, линейная;
- `_AO` — линейная, одноканальная;
- `_MaskMap` для HDRP уже лежит в пакете: R металл, G AO, B 0, A гладкость. Если его удалить, скрипт установки соберёт его заново из MetallicSmoothness и AO.

Имена свойств свечения: URP и Built-in — `_EmissionColor` (ключевое слово `_EMISSION` включено), HDRP — `_EmissiveColor`.

## 9. Сокеты

Сокеты — пустые объекты с нулевым поворотом, то есть смотрят по +Z. Координаты ниже — в пространстве префаба (метры). Сокеты с родителем `Sockets` или `Cockpit` не двигаются; сокеты на дверях, педалях, РУД и штурвале ездят вместе с ними.

| Группа | Сокеты | Назначение |
|---|---|---|
| Камера | Socket_PilotEye, Socket_CopilotEye | глаза в левом и правом кресле |
| Посадка | Socket_Seat_P, Socket_Seat_C | таз персонажа в кресле |
| Выход | Socket_Exit_L/R, Socket_Exit_Cargo_L/R | точка на земле при выходе; перед спавном проверить капсулу |
| Ручки | Socket_Handle_{PilotDoor,CargoDoor}_{L,R}_{In,Out} | ручки дверей изнутри и снаружи |
| Руки и ноги | Socket_Hand_Yoke_L/R, Socket_Hand_Throttle, Socket_Foot_L/R | IK для тела пилота |
| Ремни | Socket_Belt_P/C | замок ремня |
| Горловины | Socket_FuelCap_L/R | точка заливки под крышкой |
| Колёса | Socket_WheelContact_L/R/Tail | **центр** колеса; луч подвески вниз на радиус 0.484 / 0.484 / 0.285 м |
| Аэродинамика | Socket_Aero_Wing_{L,R}_{In,Out}, Socket_Aero_HStab_L/R, Socket_Aero_Fin, Socket_Aero_Fuselage | точки приложения сил, 1/4 хорды |
| Тяга | Socket_Thrust | центр винта, тяга по +Z |
| Масса | Socket_CenterOfMass | ориентир центра масс пустого самолёта, **TEMPORARY** |
| Груз | Socket_TieDown_01…15 | тестовые точки крепления, сетка 3 × 5 |
| Огни | Socket_Nav_*, Socket_Strobe_*, Socket_Beacon_*, Socket_Landing, Socket_Light_Dome_L/R, Socket_Light_Cargo, Socket_Light_Flood | источники света |
| Эффекты и звук | Socket_Exhaust_L/R, Socket_PropWash, Socket_Audio_Engine/Cabin/Gear_L/Gear_R/Tail | частицы и звук |
| Отладка | Socket_Cam_Chase | внешняя камера только для отладки |
| Экран | Display_GPS | центр экрана GPS/COM, квад 0.0874 × 0.0653 м в плоскости XY, смотрит на −Z (`Data/displays.json`) |

Полная таблица координат — в приложении А.

## 10. Коллайдеры и зоны взаимодействия

Коллайдеры `COL_*` в FBX — это меши-прокси. Меню установки превращает их в выпуклые `MeshCollider` и убирает с них рендереры.

| Где | Коллайдеры |
|---|---|
| `Colliders` (неподвижные) | Floor, Roof, RearBulkhead, стены Wall_{L,R}_{Front, PilotSill, PilotHead, Mid, CargoSill, CargoHead, Aft}, Panel, Pedestal, Seat_P, Seat_C, Nose, Windshield, TailCone, Wing_L/R, Strut_L/R, HStab, Fin |
| на подвижных частях | COL_PilotDoor_L/R, COL_CargoDoor_L/R (двигаются с дверью), COL_Gear_L/R |
| COL_Propeller | в FBX лежит внутри Propeller; меню установки переносит его в корень, чтобы коллайдер не вращался вместе с винтом |

- Салон собран из отдельных плит, а дверные и грузовые проёмы оставлены пустыми. Поэтому персонаж может ходить внутри, а груз — проходить через проём.
- На колёсах коллайдеров нет: колёса делаются лучами подвески из `Socket_WheelContact_*`.
- Rigidbody скрипт установки не добавляет. Физическое тело — забота систем самолёта и груза.

Зоны взаимодействия лежат в `Data/interaction_volumes.json`, всего 43. Формат записи:
```json
{"id": "SW_Battery", "parent": "SW_Battery", "kind": "toggle", "label": "АКБ",
 "center": [0.0, -0.0041, -0.0103], "halfExtents": [0.015, 0.015, 0.015]}
```
- `center` и `halfExtents` заданы в метрах, в локальных осях объекта `parent`. `parent` = `UtilityPlane` означает корень.
- `kind` — одно из: `toggle`, `momentary`, `rotary`, `pull`, `selector`, `lever`, `wheel`, `hinge`, `door`, `cap`, `seat`.
- Скрипт установки создаёт для каждой записи `IV_<id>`: триггер `BoxCollider` на слое `Interact` и компонент `UtilityPlaneInteractable` (`id`, `kind`, `label`). Состояния компонент не хранит. Если слоя `Interact` нет, скрипт заводит его в первом свободном слоте. Столкновения этого слоя со всеми остальными нужно выключить в Physics settings: зоны служат только для лучей.
- `id` совпадает с именем управляемого объекта, для ручек, горловин и ремней — с именем сокета.
- Для кресел `Seat_P` и `Seat_C` отдельного объекта нет.

## 11. Что проверить на стенде в первую очередь

1. Прогнать все каналы разделов 3 и 4 через крайние значения и посмотреть глазами. Главное — знаки дверей, педалей, топливных кранов и рычага закрылков.
2. Все стрелки на 0, середине и максимуме шкалы. Стрелка должна совпадать с оцифровкой шкалы.
3. Лампы: `busPowered` + тест → все 12 горят. Без питания не горит ничего.
4. Коллайдеры: в Scene view включить отображение физики. Проёмы должны быть свободны, стены не должны торчать внутрь салона.
5. Масштаб: капсула высотой 1.8 м рядом с дверью. Порог двери пилота должен быть на высоте 1.14 м.

## Приложение А. Координаты сокетов (метры, пространство префаба)

| Сокет | Родитель | X, Y, Z |
|---|---|---|
| Display_GPS | Cockpit | 0.110, 1.891, 2.972 |
| Socket_Aero_Fin | Sockets | 0.000, 3.000, -4.250 |
| Socket_Aero_Fuselage | Sockets | 0.000, 1.750, 1.000 |
| Socket_Aero_HStab_L | Sockets | -1.200, 2.060, -4.240 |
| Socket_Aero_HStab_R | Sockets | 1.200, 2.060, -4.240 |
| Socket_Aero_Wing_L_In | Sockets | -2.000, 2.751, 2.025 |
| Socket_Aero_Wing_L_Out | Sockets | -5.200, 2.863, 2.025 |
| Socket_Aero_Wing_R_In | Sockets | 2.000, 2.751, 2.025 |
| Socket_Aero_Wing_R_Out | Sockets | 5.200, 2.863, 2.025 |
| Socket_Audio_Cabin | Sockets | 0.000, 1.900, 2.200 |
| Socket_Audio_Engine | Sockets | 0.000, 1.550, 4.000 |
| Socket_Audio_Gear_L | Sockets | -0.460, 1.030, 2.850 |
| Socket_Audio_Gear_R | Sockets | 0.460, 1.030, 2.850 |
| Socket_Audio_Tail | Sockets | 0.000, 1.100, -1.550 |
| Socket_Beacon_Bottom | Sockets | 0.000, 0.955, -1.650 |
| Socket_Beacon_Top | Sockets | 0.000, 3.915, -4.400 |
| Socket_Belt_C | Cockpit | 0.330, 1.465, 2.325 |
| Socket_Belt_P | Cockpit | -0.330, 1.465, 2.325 |
| Socket_Cam_Chase | Sockets | 0.000, 4.500, -14.000 |
| Socket_CenterOfMass | Sockets | 0.000, 1.750, 1.950 |
| Socket_CopilotEye | Sockets | 0.330, 2.220, 2.240 |
| Socket_Exhaust_L | Sockets | -0.780, 1.560, 3.800 |
| Socket_Exhaust_R | Sockets | 0.780, 1.560, 3.800 |
| Socket_Exit_Cargo_L | Sockets | -1.350, 0.000, 0.200 |
| Socket_Exit_Cargo_R | Sockets | 1.350, 0.000, 0.200 |
| Socket_Exit_L | Sockets | -1.200, 0.000, 2.050 |
| Socket_Exit_R | Sockets | 1.200, 0.000, 2.050 |
| Socket_Foot_L | PedalP_L | -0.430, 1.373, 3.027 |
| Socket_Foot_R | PedalP_R | -0.230, 1.373, 3.027 |
| Socket_FuelCap_L | Sockets | -1.550, 2.848, 2.025 |
| Socket_FuelCap_R | Sockets | 1.550, 2.848, 2.025 |
| Socket_Hand_Throttle | Lever_Power | -0.040, 1.542, 2.890 |
| Socket_Hand_Yoke_L | Yoke_P_Roll | -0.484, 1.760, 2.760 |
| Socket_Hand_Yoke_R | Yoke_P_Roll | -0.176, 1.760, 2.760 |
| Socket_Handle_CargoDoor_L_In | CargoDoor_L | -0.675, 1.720, 0.700 |
| Socket_Handle_CargoDoor_L_Out | CargoDoor_L | -0.775, 1.750, 0.700 |
| Socket_Handle_CargoDoor_R_In | CargoDoor_R | 0.675, 1.720, 0.700 |
| Socket_Handle_CargoDoor_R_Out | CargoDoor_R | 0.775, 1.750, 0.700 |
| Socket_Handle_PilotDoor_L_In | PilotDoor_L | -0.675, 1.740, 2.300 |
| Socket_Handle_PilotDoor_L_Out | PilotDoor_L | -0.775, 1.700, 2.320 |
| Socket_Handle_PilotDoor_R_In | PilotDoor_R | 0.675, 1.740, 2.300 |
| Socket_Handle_PilotDoor_R_Out | PilotDoor_R | 0.775, 1.700, 2.320 |
| Socket_Landing | Sockets | -2.300, 2.690, 2.570 |
| Socket_Light_Cargo | Sockets | 0.000, 2.586, -0.200 |
| Socket_Light_Dome_L | Cockpit | -0.085, 2.550, 2.290 |
| Socket_Light_Dome_R | Cockpit | 0.085, 2.550, 2.290 |
| Socket_Light_Flood | Cockpit | 0.000, 2.000, 2.970 |
| Socket_Nav_L | Sockets | -7.070, 2.868, 2.300 |
| Socket_Nav_R | Sockets | 7.070, 2.868, 2.300 |
| Socket_Nav_Tail | Sockets | 0.000, 2.260, -5.100 |
| Socket_PilotEye | Sockets | -0.330, 2.220, 2.240 |
| Socket_PropWash | Sockets | 0.000, 0.000, 4.740 |
| Socket_Seat_C | Sockets | 0.330, 1.430, 2.200 |
| Socket_Seat_P | Sockets | -0.330, 1.430, 2.200 |
| Socket_Strobe_L | Sockets | -7.075, 2.868, 2.080 |
| Socket_Strobe_R | Sockets | 7.075, 2.868, 2.080 |
| Socket_Thrust | Sockets | 0.000, 1.700, 4.740 |
| Socket_TieDown_01 | Sockets | -0.500, 1.075, 1.700 |
| Socket_TieDown_02 | Sockets | 0.000, 1.075, 1.700 |
| Socket_TieDown_03 | Sockets | 0.500, 1.075, 1.700 |
| Socket_TieDown_04 | Sockets | -0.500, 1.075, 1.000 |
| Socket_TieDown_05 | Sockets | 0.000, 1.075, 1.000 |
| Socket_TieDown_06 | Sockets | 0.500, 1.075, 1.000 |
| Socket_TieDown_07 | Sockets | -0.500, 1.075, 0.300 |
| Socket_TieDown_08 | Sockets | 0.000, 1.075, 0.300 |
| Socket_TieDown_09 | Sockets | 0.500, 1.075, 0.300 |
| Socket_TieDown_10 | Sockets | -0.500, 1.075, -0.400 |
| Socket_TieDown_11 | Sockets | 0.000, 1.075, -0.400 |
| Socket_TieDown_12 | Sockets | 0.500, 1.075, -0.400 |
| Socket_TieDown_13 | Sockets | -0.500, 1.075, -1.100 |
| Socket_TieDown_14 | Sockets | 0.000, 1.075, -1.100 |
| Socket_TieDown_15 | Sockets | 0.500, 1.075, -1.100 |
| Socket_WheelContact_L | Sockets | -1.250, 0.480, 2.850 |
| Socket_WheelContact_R | Sockets | 1.250, 0.480, 2.850 |
| Socket_WheelContact_Tail | Sockets | 0.000, 0.285, -2.060 |
