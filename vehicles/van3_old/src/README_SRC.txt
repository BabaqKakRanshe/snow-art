Старый запасной фургон: van3 с новой текстурой кузова (старое хаки, ржавчина) и без лебёдки. Справочник — раздел «Старый запасной фургон» в docs/gdd/WORLD_CONTRACT.md.

- vanold.py <папка van3> <папка вывода>: запекает положение, нормаль и AO кузова van3 в его же развёртке (PSX) и красит T_VanOld_Body_BaseColor (256, 64 цвета); vanold.blend — копия van3.blend: материал M_VanOld_Body вместо M_Van_Body, Winch_Drum, Winch_Clutch, Winch_Hook удалены, остальные текстуры — van3 по пути ../van3/tex.
- vanold_render.py <vanold.blend> <png> [spp] — рендер.
- Библиотека: noise.py, psxbake.py, psxlib.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz').
