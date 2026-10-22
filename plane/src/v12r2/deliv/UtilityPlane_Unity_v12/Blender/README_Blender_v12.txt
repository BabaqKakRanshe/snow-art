Utility Plane v12 — файлы Blender (интерьер PSX, пиксельные шкалы и надписи)

Редакция 2 (16.10.2026): файлы .blend те же, что в редакции 1, — текстуры подключены относительными путями и берутся из пакета рядом (..\Assets\UtilityPlane\Textures), поэтому сразу показывают атласы редакции 2.

Открывать в Blender 5.0 или новее (сохранены в 5.0.1).

- UtilityPlane_v12.blend — модель, из неё выгружен Models/UtilityPlane.fbx (FBX тот же, что в v11). Сцена v11: самолёт, зимний комплект 1.2, отдельные модели (ящики, стремянка, ключ, аварийный комплект).
- UtilityPlane_v12_lights.blend — та же модель со светом для Cycles: IES-профили и функции света, туман, камеры. Как устроен свет — текст README_v12_lights внутри файла (Text Editor) и README_IES.txt в папке IES.

Что изменилось с v11 (только материалы):
- M_Cockpit, M_Interior, M_Floor, M_Seats, M_Fittings, M_Webbing — без карт нормалей, текстуры по точкам (Interpolation: Closest), как в Unity v12 (фильтр Point). Сами текстуры — PSX-атласы v12, редакция 2: 512² (арматура 256²), 32 цвета, дизеринг, затенение, рисованный свет и зерно в цвете.
- M_Gauges, M_Annunciator, M_RadioDisplay — атлас надписей v12 (пиксельная графика 1024²), тоже по точкам. M_RadioDisplay теперь как в Unity: цвет T_Gauges_BC, свечение T_Displays_Emission (в файлах v11 лицевые панели радио светились ровным белым).
- Геометрия, UV, имена, свет, камеры и сцены — как в v11.

Текстуры подключены относительными путями:
- самолёт — ..\Assets\UtilityPlane\Textures (пакет UtilityPlane_Unity_v12);
- зимний комплект — ..\..\UtilityPlane_WinterKit_v1_2\Assets\UtilityPlane\Textures.
Если файл открыт из другой папки: File → External Data → Find Missing Files.

Чтобы пиксели были видны в окне Blender: вид Material Preview или Rendered; в Cycles буквы чёткие при любом увеличении, потому что текстуры берутся по точкам.
