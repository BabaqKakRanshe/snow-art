Исходники фигуры Apparition (обновление 6) для пугалок X02 и X03. Пакет — папка выше (fig.blend, атласы, отчёты, листы, рендеры), архив — ../../forest_figure_package.zip,
справочник — docs/gdd/APPARITION_CONTRACT.md; пакет для Unity — Forest_Update6.unitypackage (его исходники —
source/locations/Forest/Forest_Update6_src).

- Порядок: fig_build.py → out/fig.blend, fig.json, tex/fig (--draft — без запекания); checks/fig_render2.py →
  лист поз, fig_sit_render.py → поза в фургоне (макет скамьи, вид зеркала); make_sheets_u6.py → sheets/fig_A…C.jpg;
  pack_u6.py figure → архив.
- fig_build.py строит меш, скелет (20 костей), веса, атлас и четыре клипа; ход и посадка рассчитываются на сетке:
  опорная стопа стоит на земле, маховая проходит над ней, поза Sit — под потолком скамьи фургона (fig.json → sit).
- checks/: walk_speed.py (стопа опоры на ходу), fig_top.py, fig_bones.py — с журналом.
- Отделка и покраска — генераторной (psxbake, noise, приёмы gen_paint), шрифт надписей — проекта (pxfont).
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
