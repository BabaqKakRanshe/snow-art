# Задача: перенести локацию Sky Island в Unity-проект игры 1 в 1

Ты работаешь в моём Unity-проекте игры. Нужно собрать в нём готовую локацию «Sky Island» (парящий остров с военным аэродромом в жёлто-оливковом тумане) так, чтобы она выглядела 1 в 1 как на эталонных рендерах: та же геометрия и расстановка, тот же свет, туман, небо и пост-процесс. Потом встроить её в игру.

## Где что лежит
- Unity-проект: `F:\ClaudeGames\snow\Snow`. Сначала убедись, что это корень проекта (`Assets\`, `ProjectSettings\ProjectVersion.txt`, `Packages\manifest.json`); если нет — найди проект внутри `F:\ClaudeGames\snow`.
- Пакет: `F:\ClaudeGames\snow\assets\SkyIsland\SkyIsland_1_Core.unitypackage` … `SkyIsland_5_Assets.unitypackage`. Это пять частей ОДНОГО пакета (общие GUID), всё ставится в `Assets/SkyIsland`. Нужны все пять.
- После импорта прочитай `Assets/SkyIsland/README.md` целиком. Источник истины для света, тумана, неба и поста — `Assets/SkyIsland/Data/SkyIsland_Look.json`; расстановка — `Data/SkyIsland_Layout.json`; эталонные кадры — `Assets/SkyIsland/Previews/SkyIsland_*.jpg` (1280×720).

## Главные правила
1. Сцену собирает только встроенный сборщик пакета (`Tools → Sky Island → Build Scene`, метод `SkyIsland.EditorTools.SkyIslandBuilder.BuildScene`). Не расставляй и не настраивай руками вместо него.
2. Не придумывай и не «улучшай» значения: цвета, интенсивности света, туман, LUT, параметры Volume, материалы, позиции объектов — только из данных пакета. Если результат не совпадает с эталоном, ищи причину в настройках проекта, а не правь лук.
3. Не трогай чужие ассеты и сцены проекта. Меняй только настройки из шага 2 и перечисли все изменения в отчёте.
4. Спроси меня, прежде чем менять render pipeline, переключать Color Space (это переимпорт всех текстур), обновлять Unity/пакеты или что-либо удалять.
5. Ошибки компиляции в `Assets/SkyIsland/Scripts` исправляй минимально (совместимость API твоей версии Unity/URP), не меняя логику, и сообщи, что поменял.

## Шаг 0. Разведка (без изменений)
Выясни и коротко сообщи: версия Unity (поддерживаются 2022.3 LTS и Unity 6); render pipeline и версия URP (`Packages/manifest.json`; какой URP Asset активен в Graphics и на каждом уровне Quality); Color Space; Active Input Handling; какие сцены и какой игрок (контроллер, камера) уже есть в игре. Если проект не на URP — остановись и спроси (пакет умеет и Built-in, но эталон откалиброван под URP).

## Шаг 1. Импорт
- Если редактор Unity открыт — попроси меня импортировать пять пакетов (Assets → Import Package → Custom Package, или перетащить все пять в окно Project) либо закрыть редактор.
- Если закрыт — импортируй сам в batchmode по очереди, каждый раз дожидаясь завершения и проверяя лог:
  `"<Unity.exe>" -batchmode -projectPath "F:\ClaudeGames\snow\Snow" -importPackage "F:\ClaudeGames\snow\assets\SkyIsland\SkyIsland_1_Core.unitypackage" -quit -logFile "%TEMP%\skyisland_import_1.log"`
  `<Unity.exe>` — версия из `ProjectSettings/ProjectVersion.txt`, обычно `C:\Program Files\Unity\Hub\Editor\<версия>\Editor\Unity.exe`. Не используй `-nographics`.
- Компиляция должна быть чистой (в логе нет `error CS`).

## Шаг 2. Настройки проекта, без которых 1 в 1 не получится
- Color Space = Linear (если Gamma — спроси меня).
- Для каждого URP Asset, который реально используется (Graphics и все уровни Quality): HDR on; Post-processing → Grading Mode = High Dynamic Range; LUT Size 32; Additional Lights = Per Pixel; Per Object Limit 8.
- Universal Renderer: Rendering Path = Forward+ (`Tools → Sky Island → Switch URP Renderer To Forward+` или метод `SkyIsland.EditorTools.SkyIslandBuilder.SwitchToForwardPlus`); Post-processing в рендерере включён.
- Сборщик часть этого ставит сам и пишет предупреждения `[SkyIsland]` в консоль — прочитай их все.

## Шаг 3. Сборка
`Tools → Sky Island → Build Scene` (или batchmode: `-executeMethod SkyIsland.EditorTools.SkyIslandBuilder.BuildScene -quit`, без `-nographics`, иначе не запекутся отражения). Результат — `Assets/SkyIsland/Scenes/SkyIsland.unity`: ~6 200 объектов, 82 источника света, 230 ореолов (шейдер `SkyIsland/LightGlow`), туман, небо, отражения, глобальный Volume с пост-процессом.

## Шаг 4. Проверка значений в собранной сцене (сверь с Look.json)
| Что | Ожидается |
|---|---|
| Fog | Exponential, Density 0.0036 у земли (скрипт `SkyIslandFogByAltitude` на камере снижает её до 0.0012 в воздухе), цвет #736324 |
| Ambient | Trilight: Sky #50451A, Equator #463C16, Ground #231D09 |
| Sun | Directional, #FFE7A6, Intensity 0.105, мягкие тени, высота ~20°; на объекте `SkyIslandSky` |
| Skybox | материал `SkyIsland_Skybox` (shader `SkyIsland/Skybox`) |
| Отражения | Custom cubemap неба + 3 box-projected reflection probe (запечены) |
| Volume `SkyIsland_URP_Volume` (global) | Tonemapping Neutral; Color Lookup `SkyIsland_RefLook_LUT32`, contribution 1; Bloom threshold 0.9, intensity 1.1, scatter 0.72, tint #FFF5DE, High Quality; Color Adjustments post exposure −0.1, contrast +10; Vignette color (0.05, 0.035, 0.008), intensity 0.32, smoothness 0.42; Film Grain Medium 1, intensity 0.22, response 0.8; Chromatic Aberration 0.06 |
| Камера | HDR, Post Processing on, SMAA High, Dithering, Far Clip 6000 |

Другие глобальные Volume в сцене или в игре не должны перебивать этот (priority/weight).

## Шаг 5. Визуальная проверка 1 в 1
1. `Tools → Sky Island → Capture Viewpoints (compare with previews)` (или `-executeMethod SkyIsland.EditorTools.SkyIslandBuilder.CaptureViewpoints`). Он рендерит 9 точек обзора основной камерой с пост-процессом в 1280×720 в `<проект>/SkyIslandCaptures/*_unity.png` и пишет `report.txt`: яркость (OKLab L p5/p50/p95) и средний цвет рядом с теми же числами эталонных превью.
2. Открой каждую пару (`SkyIslandCaptures/SkyIsland_<имя>_unity.png` ↔ `Assets/SkyIsland/Previews/SkyIsland_<имя>.jpg`) и сравни глазами: композиция, какие огни горят, ореолы, плотность тумана, цвет.
3. Критерий для каждой точки: |ΔL p50| ≤ 0.03, p5 и p95 в пределах ±0.04, тот же оттенок. Допустимые отличия: отражения в лужах мягче (в URP нет SSR), рисунок зерна, мелкие тени.
4. Если не совпадает, проверь в первую очередь: Grading Mode = LDR; Gamma color space; выключен пост на камере или рендерере; другой Volume перебивает; Forward вместо Forward+ (пропадают лампы); чужой скрипт меняет `RenderSettings.fog`; уровень Quality с другим URP Asset. Исправь причину и повтори захват.

## Шаг 6. Встраивание в игру
- Сцена `SkyIsland.unity` — это уровень. Добавь её в Build Settings.
- Поставь игрока игры (найди его префаб или контроллер) в точку `SkyIsland/Viewpoints/View_Hangars` или спроси меня, где спавн.
- Камера игрока должна получить всё, от чего зависит лук: Post Processing on, HDR, SMAA High, Dithering, Far Clip 6000 и компонент `SkyIslandFogByAltitude` (target = эта камера, остальные поля скопируй с камеры сцены). Тег MainCamera — только у одной камеры: отладочную `Main Camera` с `SkyIslandFlyCamera` отключи, когда есть камера игрока.
- Коллайдеры уже есть (рельеф, покрытия, постройки, заборы, камни; у деревьев капсулы). Проверь, что игрок ходит по земле и не проваливается (слои, Collision Matrix).
- Не удаляй `Beacons` (мигание заградогней), `SkyIslandSky` на солнце, reflection probes и `HazeLayers`.

## Шаг 7. Отчёт
Что сделано; какие настройки проекта изменены (было → стало); таблица из `report.txt` по 9 точкам; пути к захватам; что осталось отличаться и почему.
