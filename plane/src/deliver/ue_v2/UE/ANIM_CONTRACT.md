# Utility Plane: контракт анимации для UE5.6

Два skeletal mesh с жёсткой сегментацией: каждая деталь на 100% привязана к одной кости.

| Asset | Корень | Кости | Треугольники |
|---|---|---|---|
| SK_UtilityPlane | `root` → `Body` | 41 (18 подвижных + 22 сокета) | 23.7k |
| SK_UtilityPlane_Cockpit | `root` → `Cockpit` | 44 (43 подвижные) | 13.5k |

Кабина цепляется к `Body` внешнего меша с нулевым трансформом: у обоих мешей общее начало координат.

## Оси и знаки

- Компонентные оси: X вперёд (нос), Y вправо, Z вверх, сантиметры.
- **Rest-ориентация каждой кости нулевая**, поэтому оси кости совпадают с осями компонента.
  - Исключение: `Aileron_L/R`, `Flap_L/R`. Их локальная Y лежит на линии петли (V крыла 2°), в покое крен ±2°.
- Для вложенных костей (колёса на стойках, `TailWheel` на вилке, `Yoke_*_Roll`, `ATT_Pitch`) Transform (Modify) Bone ставить в Bone Space.
- Знаки ниже даны в терминах UE FRotator:
  - Pitch+ поднимает +X;
  - Yaw+ поворачивает +X к +Y (вправо);
  - Roll+ — по часовой, если смотреть вперёд по +X, то есть с места пилота.
- Если в BP какая-то часть пойдёт не в ту сторону, инвертируй знак только у неё. Я проверял оси позой в Blender и пересчитывал знаки по правилу ниже. Сам движок у меня не запускался.
- Правило пересчёта из Blender-файла: `Roll(UE) = Rx(Blender)`, `Pitch(UE) = −Ry(Blender)`, `Yaw(UE) = −Rz(Blender)`, `Y(UE) = −Y(Blender)`.

## Внешний меш

| Кость | Канал | Смысл и знак | Диапазон |
|---|---|---|---|
| Propeller | Roll | вращение по часовой с места пилота = +Roll; скорость °/с = RPM × 6 | ∞ |
| Wheel_L / Wheel_R | Pitch | качение вперёд = −Pitch; ° на см пути = 360 / (2π·48) | ∞ |
| TailWheel | Pitch | качение вперёд = −Pitch; r = 28 см | ∞ |
| Gear_L | Roll | сжатие рессоры (колесо вверх) = +Roll; 12° ≈ 12 см хода | 0…+12° |
| Gear_R | Roll | сжатие = −Roll | 0…−12° |
| TailGear | Pitch | сжатие (колесо вверх) = −Pitch | 0…−8° |
| TailWheel_Fork | Yaw | колесо носком вправо = +Yaw; за пределом — свободное ориентирование | ±30° |
| Rudder | Yaw | задняя кромка вправо (правая педаль) = −Yaw | ±25° |
| Elevator_L / _R | Pitch | задняя кромка вверх (штурвал на себя) = −Pitch | −25…+15° |
| Aileron_L / _R | Pitch | задняя кромка вверх = −Pitch. Крен вправо: Aileron_R −, Aileron_L + | ±20° |
| Flap_L / _R | Pitch | выпуск (кромка вниз) = +Pitch; ступени 0/10/20/35 | 0…+35° |
| CargoDoor | Yaw | открытие наружу = −Yaw (петля на задней кромке) | 0…−100° |
| PilotDoor_L | Yaw | открытие наружу = +Yaw (петля спереди) | 0…+70° |
| PilotDoor_R | Yaw | открытие наружу = −Yaw | 0…−70° |

## Сокеты (кости без весов)

Все сокеты с нулевой ориентацией, то есть смотрят по +X. Эффекты «назад» (выхлоп) разворачивай в эмиттере.

- `Socket_PilotEye`, `Socket_CopilotEye` — камера от первого лица, 0.745 м до приборной доски.
- `Socket_WheelContact_L/R/Tail` — центр колеса, отсюда трасса вниз на радиус 48 / 48 / 28 см.
- `Socket_Exhaust_L/R` — срезы выхлопных патрубков.
- `Socket_PropWash` — точка на земле под винтом, для пыли от обдува.
- `Socket_CenterOfMass` — центр масс.
- Огни:
  - `Socket_Nav_L` — красный;
  - `Socket_Nav_R` — зелёный;
  - `Socket_Nav_Tail` — белый;
  - `Socket_Strobe_L/R` — белые;
  - `Socket_Beacon_Top/Bottom` — красные.
- Звук: `Socket_Audio_Engine/Cabin/Gear_L/Gear_R/Tail`.
- `Socket_Cam_Chase` — камера сзади и сверху.

## Кабина

Органы управления. Для симулятора ставить 1:1, в тот же кадр, без сглаживания.

| Кость | Канал | Смысл | Диапазон |
|---|---|---|---|
| Yoke_P / Yoke_C | Translation X | от себя = +X (нос вниз) | ±8 см |
| Yoke_P_Roll / Yoke_C_Roll | Roll | крен вправо = +Roll | ±50° |
| PedalP_L, PedalP_R, PedalC_L, PedalC_R | Pitch | педаль вперёд = −Pitch; левая педаль вперёд = рыскание влево | ±12° |
| Lever_Power / Lever_Prop / Lever_Condition | Pitch | рычаг вперёд = −Pitch; в покое середина хода | ±25° |
| Lever_Flap | Pitch | 0/10/20/35 = 0 / +12 / +24 / +36° | 0…+36° |
| TrimWheel | Pitch | триммер на кабрирование = +Pitch | ±360° |
| SW_Battery, SW_Avionics, SW_FuelPump, SW_Ignition, SW_Starter, SW_Beacon, SW_Strobe, SW_NavLights, SW_Landing | Pitch | в покое OFF (вниз), ON = −40°; SW_Starter кнопочный | 0 / −40° |

Приборы. Стрелки в покое показывают ноль шкалы. Roll+ = по часовой для пилота. Угол = коэффициент × значение.

| Кость | Формула Roll |
|---|---|
| Needle_ASI | 1.6 × kt (0–200) |
| Needle_ALT100 | 0.36 × ft (один оборот на 1000 ft) |
| Needle_ALT1000 | 0.036 × ft |
| Needle_VSI | 0.0825 × fpm (±2000) |
| Needle_TRQ | 0.1125 × ft·lb (0–2400) |
| Needle_ITT | 0.27 × (°C − 100) |
| Needle_NG | 2.4545 × % |
| Needle_PROP | 0.1125 × RPM (0–2400) |
| Needle_FF | 0.675 × pph (0–400) |
| Needle_OILP | 0.6 × psi |
| Needle_OILT | −0.8 × °C (стрелка идёт против часовой) |
| Needle_FUELL / Needle_FUELR | 2.0 × gal (0–60) |
| Needle_AMP | 1.5 × A (±60) |
| Clock_Hour / Clock_Min | 30 × ч / 6 × мин |
| ATT_Roll | −крен (горизонт наклоняется против крена самолёта) |
| ATT_Pitch | Translation Z = −0.06 см на градус тангажа, ограничить ±20° |
| HDG_Card | −курс |
| TC_Plane | +20° на стандартной угловой скорости (3°/с) |
| TC_Ball | скольжение: шарик вправо = −Roll, ±15° |

Стрелкам нужны пружина и небольшой перелёт (ω ≈ 10–12 рад/с, ζ ≈ 0.6), а от оборотов двигателя — дрожание ±0.3°. Так они выглядят как настоящие механические приборы.

## Импорт в UE5.6 (FBX, Interchange или legacy)

- Skeletal Mesh, Skeleton — создать новый (для каждого меша свой).
- Convert Scene: вкл. Force Front X Axis: **выкл.** (нос уже по +X). Convert Scene Unit: вкл. (файл уже в сантиметрах, UnitScaleFactor 1, ×100 на корне не будет).
- Uniform Scale 1.0. Normals: Import. Tangents: Mikk. Morph Targets: пока нет.
- Create Physics Asset: выкл. Для коллизии фюзеляжа и крыльев лучше простые тела вручную, а шасси — трассы из `Socket_WheelContact_*`.
- Материалы пока блокинговые (`src_*`). На следующем шаге их заменят атласы BC / N (DirectX) / ORM и скрипт Unreal Python.
