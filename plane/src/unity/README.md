# Utility Plane — STOL-самолёт для Unity

Турбовинтовой bush plane по концепту «Vehicle Turnaround»: красно-белая ливрея, потёртая краска, тундровые колёса, открытый грузовой отсек с кейсами.

## Импорт в Unity

1. Скопируй папку `Assets/UtilityPlane` в `Assets` проекта.
2. Меню **Tools → Utility Plane → Create Materials + Prefab**.
   Скрипт определит пайплайн (Built-in / URP / HDRP) и создаст `M_Airframe`, `M_Details`, `M_Lights`. Он же настроит импорт текстур (Normal Map, sRGB off для масок), сделает ремап материалов FBX и соберёт `Prefabs/UtilityPlane.prefab` с компонентом `UtilityPlaneRig`.

## Масштаб и оси

- Единицы — метры, scale 1. У всех объектов rotation 0 и scale 1, кроме перечисленных ниже.
- Нос → **+Z** (transform.forward), верх → **+Y**, грузовая дверь **слева** (−X).
- Пивот корня стоит на земле по оси самолёта. `CenterOfMass` — пустышка в примерном центре масс; риг сам назначает её в `Rigidbody.centerOfMass`.
- Размах 14.2 м, длина 10.15 м, высота 3.95 м. Около 21k треугольников.

## Подвижные части (пивот на петле или оси)

| Объект | Ось вращения | Примечание |
|---|---|---|
| Propeller | local Z | лопасти + кок |
| Wheel_L / Wheel_R | local X | r = 0.48 м |
| TailWheel_Fork | local Y | руление |
| TailWheel (дочерний к вилке) | local X | r = 0.28 м |
| Rudder | local Y | |
| Elevator_L / Elevator_R | local X | +X = задняя кромка вверх |
| Aileron_L/R, Flap_L/R | local X | в покое Z ±2° (V крыла) |
| CargoDoor | local Y | 0 = закрыта, −100° = открыта (так в FBX) |

## Материалы и текстуры

| Материал | Текстуры | Сабмеши |
|---|---|---|
| M_Airframe | T_Airframe_* 4096² | фюзеляж, крыло, оперение, рули, дверь, подкосы |
| M_Details | T_Details_* 2048² | шасси, колёса, винт, выхлоп, антенны, грузовой отсек, кейсы |
| M_Lights | только emission | навигационные огни |

Карты в каждом наборе:
- `_BaseColor` (sRGB)
- `_Normal` (OpenGL / Y+)
- `_MetallicSmoothness` (R = metallic, A = smoothness; для Built-in и URP)
- `_AO`
- `_MaskMap` (для HDRP: R metallic, G AO, B 0, A smoothness)

## Blender

- `UtilityPlane.blend` — та же иерархия с запечёнными материалами. Процедурные исходные материалы (`src_*`) оставлены в файле с fake user, их можно перепечь.
- В `blender_scripts/` весь пайплайн на bpy: `build.py` (геометрия), `shade.py` (UV + запекание), `finalize.py` (упаковка каналов, объединение статики, экспорт FBX с фиксом Apply Transform для вложенной иерархии), `render.py` (превью).
