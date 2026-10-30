# Карта Forest целиком — набор для Blender

Выгружено из Unity 2026-10-28 21:41, сцена `Assets/Locations/Forest/Scenes/Forest.unity`. Правила обмена — `docs/gdd/WORLD_SYNC_CONTRACT.md`.

## Собрать сцену
`blender -b --factory-startup --python build_map.py -- map.json map.blend` (из этой папки). Земля по умолчанию через точку (`--ground-step 2`, 1,2 м); `--ground-step 1` — полная, `--no-trees` — без деревьев.

## Что внутри
- `ground.r16` — высоты 3073 × 3073 точек через 0.586 м, uint16, строки с юга на север, x с запада на восток; высота = -58.71 + v / 65535 × 109.12 м. `holes.u8` — 1 = земля, 0 = дыра (клетки между точками).
- `paint.png` — покраска земли, 1 px на метр, север сверху.
- `meshes.bin` — 1249 моделей по одному разу; `textures/` — их текстуры.
- `map.json` — 2091 объектов (корень + его меши), 77423 деревьев Terrain (104 моделей), 199 ламп.

## Оси
Blender (x, y, z) = Unity (−x, −z, y), метры, мировые координаты Unity не сдвинуты.

## Двигать объекты
За пустышку-корень (ARROWS). У объектов с `world_id` сдвиг уходит в Unity: `blender -b map.blend --python export_moves.py` → `moves_from_blender.json` → Unity: Tools / Snow / World Sync / Import Moves From Blender.
