# Utility Plane v4 — пакет для Unity

Грузовой STOL-самолёт для игры от первого лица: экстерьер, полная кабина, 12 ламп табло, 4 двери, крышки баков, коллайдеры салона с пустыми проёмами, зоны взаимодействия, скрипт отображения.

Под Unity 6000.0.67f1. Скрипт установки сам определяет пайплайн: Built-in, URP или HDRP. Для HDRP в пакете уже лежат MaskMap.

## Установка

1. Скопировать папку `UtilityPlane` в `Assets/` проекта так, чтобы получилось `Assets/UtilityPlane/...`. Путь важен: скрипт установки ищет файлы там.
2. Дождаться импорта. Настройки текстур и FBX применяются автоматически при первом импорте:
   - нормали как Normal Map;
   - маски в линейном пространстве;
   - FBX без камер, света, анимации и автоколлайдеров, Read/Write включён.
3. Выполнить меню `Tools → Utility Plane → Build Materials + Prefabs`. Оно:
   - определяет пайплайн (Built-in / URP / HDRP) и создаёт материалы в `Materials/`, переназначает их на FBX;
   - заводит слой `Interact`, если его нет;
   - собирает `Prefabs/UtilityPlane.prefab`:
     - 30 выпуклых коллайдеров из прокси `COL_*`;
     - 43 зоны `IV_*`;
     - 12 источников света в сокетах;
     - компонент `UtilityPlaneRig`;
   - собирает `Prefabs/Cargo_Case1..6.prefab`.
4. В Physics settings выключить столкновения слоя `Interact` со всеми слоями.

Rigidbody скрипт не добавляет. Физика — дело систем самолёта и груза, см. `docs/gdd/PLANE_FULL_INTEGRATION_UNITY.md`.

## Быстрая проверка без кода

- Поставить префаб в сцену.
- В Play Mode двигать поля `UtilityPlaneRig`:
  - двери, рули, штурвал, стрелки;
  - `busPowered` + `annunciatorTestPressed` → горят все лампы;
  - `navLights`, `strobeLights`, `beaconLights`, `landingLight` → огни.
- Порядок проверки — `UNITY_CONTRACT.md`, раздел 11.

## Состав

| Путь | Что |
|---|---|
| `Models/UtilityPlane.fbx` | самолёт одной иерархией, метры, нос +Z |
| `Models/SM_Cargo_Case1..6.fbx` | ящики |
| `Textures/` | атласы Airframe (4K), Details (2K), Cockpit (4K): BaseColor, Normal, MetallicSmoothness, AO, MaskMap (HDRP); T_Gauges_BC; T_CargoNet_BCA |
| `Data/interaction_volumes.json` | зоны взаимодействия |
| `Data/cargo_layout.json` | расстановка ящиков с концепта |
| `Data/displays.json` | экран GPS |
| `Scripts/` | `UtilityPlaneRig`, `UtilityPlaneInteractable`, сборка `UtilityPlane.Runtime` |
| `Editor/` | `UtilityPlaneSetup`, сборка `UtilityPlane.Editor` |
| `COMPONENTS.md` | что за что отвечает, габариты, пробелы модели |
| `UNITY_CONTRACT.md` | оси, знаки, формулы стрелок, лампы, огни, материалы, сокеты, коллайдеры |

## Состояние

- **Проверено:**
  - FBX повторным импортом в Blender: иерархия и позиции всех объектов совпадают с исходником;
  - скрипты компилируются без ошибок против заглушек API Unity.
- **Не проверено:** в Unity пакет не открывался. Первая задача интеграции (P00) — импорт, меню установки и визуальная проверка знаков.
