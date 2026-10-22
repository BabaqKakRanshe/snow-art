IES — световые диаграммы 41 лампы УАЗа (17 типов), формат IESNA LM-63-2002.

Откуда: посчитаны из диаграмм излучения ламп (van_lights.py в пакете source/vehicles/van3/src) — это не замеры
реальных фар, а формы лучей, которые мы задали: ближний свет с горизонтальной границей слева и подъёмом 15° справа
(правостороннее движение), узкий прожектор, широкая противотуманка, прямоугольник рабочего света, плафоны и т. д.

Где используются:
  - Unity URP: IES не читает. Те же диаграммы запечены в маски света Assets/Van/Textures/Cookies/T_Cookie_*.png
    (для Spot-ламп; маска покрывает конус spotOuter, центр — ось луча, +u — вправо от лампы, +v — вверх), точечные
    лампы — без маски. Риг и меню сборки ставят маски сами. Эти файлы в проект Unity не копировать.
  - Blender (Cycles) и HDRP: IES можно подключить напрямую (ось луча — надир 0°; C0 = −Y лампы, C90 = −X,
    C180 = +Y, C270 = +X). Сила света в файле нормирована к пику; яркость в игре — intensity из lights.json.

Файл        тип       в Unity                                       лампы
  amber.ies    amber     Point                                        Turn_FL, Turn_FR, Turn_RL, Turn_RR
  dome.ies     dome      Spot 140° / 126°, маска T_Cookie_dome        Dome_Saloon_F, Dome_Saloon_R, Dome_Cab
  flare.ies    flare     Point                                        Flare_1, Flare_2, Flare_3
  flood.ies    flood     Spot 140° / 126°, маска T_Cookie_flood       Dash_Flood
  fog.ies      fog       Spot 96° / 86°, маска T_Cookie_fog           Fog_L, Fog_R
  hand.ies     hand      Point                                        WorkLamp
  head.ies     head      Spot 70° / 62°, маска T_Cookie_head          Head_L, Head_R
  marker.ies   marker    Point                                        Marker_Cab0, Marker_Cab1, Marker_Cab2, Marker_Cab3, Marker_Cab4, Marker_SideL0, Marker_SideL1, Marker_SideR0, Marker_SideR1
  night.ies    night     Point                                        Night_Red
  pendant.ies  pendant   Point                                        Pendant
  plate.ies    plate     Spot 120° / 104°, маска T_Cookie_plate       Plate
  reverse.ies  reverse   Spot 130° / 118°, маска T_Cookie_reverse     Reverse_L, Reverse_R
  spot.ies     spot      Spot 40° / 34°, маска T_Cookie_spot          Spot_L, Spot_R
  stove.ies    stove     Point                                        Stove
  tail.ies     tail      Point                                        Tail_L, Tail_R
  torch.ies    torch     Spot 60° / 14°, маска T_Cookie_torch         Torch
  work.ies     work      Spot 110° / 100°, маска T_Cookie_work        LightBar0, LightBar1, LightBar2, LightBar3, Work_Rear
