Исходники фургона v3 («буханка») и предыдущей v2. Пакет — папка выше (van3.blend, текстуры, контракт),
архив — ../../van3_package.zip, справочник — docs/gdd/VAN3_CONTRACT.md.

- Исходная модель: src_in/uaz.zip — «UAZ» by tiunov.se (Sketchfab, CC BY 4.0), распакованная — src/uaz;
  авторство — CREDITS_UAZ.txt и docs/context_pack/CREDITS.md.
- Порядок: inspect_model.py (src_in/uaz.zip → work/uaz_import.blend) → fix_uaz.py (→ work/uaz_fixed.blend)
  → van3_build.py (→ out/van3.blend, van3_contract.json, van3_lights.json, tex/van3) → van3_render.py
  → make_contract_doc.py → make_sheets_van3.py, make_sheets_van3b.py, make_sheets_van3c.py → pack_van3.py.
- Blender 5.0.1 (bpy как модуль Python 3.11). Пути в скриптах абсолютные (HERE = '/home/claude/uaz') — заменить на
  путь к этой папке. Общие модули (psxlib, pxfont, noise, ies_lm63, van2_kit, van2_tex, van3_mech, van_lights,
  make_sheets_van2/3, post_bloom) — те же копии лежат в исходниках генераторной.
- SCRIPTS_INDEX.txt — все скрипты с первой строкой описания.
