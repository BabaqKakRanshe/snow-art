"""Разворот под Unity, экспорт FBX и сборка переносимого пакета.

Запуск:
  blender --background --factory-startup --python-exit-code 1 --python finalize.py -- \
      <shaded.blend> <корень пакета>

Пресет экспорта не выдуман: он снят с уже работающих моделей проекта и
перепроверен измерением в живом редакторе Unity (см. axis_probe.py). Сочетание
apply_scale_options='FBX_SCALE_ALL' + bake_space_transform=True запекает
преобразование осей в вершины, поэтому корень приходит с единичным трансформом,
а метр Blender равен юниту Unity. «Bake Axis Conversion» в импортёре при этом
обязан остаться выключенным — иначе поворот применится дважды.
"""

from __future__ import annotations

import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

import plane_params as P  # noqa: E402

TEXTURES = [
    ("T_BushPlane_BaseColor", "T_BushPlane_BaseColor.png", "sRGB"),
    ("T_BushPlane_Mask", "T_BushPlane_Mask.png", "Non-Color"),
    ("T_BushPlane_Normal", "T_BushPlane_Normal.png", "Non-Color"),
]


def log(msg: str) -> None:
    print(f"[finalize] {msg}", flush=True)


def spin_for_unity() -> None:
    """Разворот сцены на 180° вокруг Z.

    Измерено в редакторе: при выбранном пресете Blender +Y уходит в Unity −Z,
    то есть нос смотрел бы назад. Разворот на 180° — настоящий поворот
    (определитель +1). Отражение по одной оси дало бы тот же нос, но вывернуло
    бы нормали и сделало крутку винта левой. Правый борт после разворота
    попадает на Unity +X, что при носе в +Z и есть право, поэтому суффиксы
    _L/_R остаются верными и переименовывать ничего не нужно.
    """
    R = Matrix.Rotation(math.pi, 4, "Z")
    seen = set()
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.data.name not in seen:
            obj.data.transform(R)
            obj.data.update()
            seen.add(obj.data.name)
        obj.location = R @ obj.location
    log(f"развёрнуто мешей: {len(seen)}")


def relink_textures(texdir_rel: str) -> None:
    """Переводит изображения с внутреннего буфера на файлы рядом с пакетом."""
    for name, fn, cs in TEXTURES:
        img = bpy.data.images.get(name)
        if img is None:
            log(f"[!] изображение {name} не найдено в сцене")
            continue
        img.filepath = f"{texdir_rel}/{fn}"
        img.source = "FILE"
        img.reload()
        # Цветовое пространство задаём после перепривязки: буфер теперь читается
        # из файла, и обнулять уже нечего.
        img.colorspace_settings.name = cs


def purge_scratch() -> None:
    """Убирает служебное: подложки, промежуточные карты, камеры и свет превью."""
    for img in list(bpy.data.images):
        if img.name.startswith("_BushPlane") or img.name.startswith("Render Result"):
            bpy.data.images.remove(img)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("REF_", "CAL_", "Cam_", "Preview")) or obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def export_fbx(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    root = bpy.data.objects.get("BushPlane")
    if root:
        bpy.context.view_layer.objects.active = root

    bpy.ops.export_scene.fbx(
        filepath=os.path.abspath(path),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True,
        axis_forward="-Z",
        axis_up="Y",
        object_types={"MESH", "EMPTY"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_triangles=True,
        # Касательные считает Unity по MikkTSpace — тот же базис, против
        # которого запекалась карта нормалей, и файл выходит меньше.
        use_tspace=False,
        use_custom_props=False,
        bake_anim=False,
        # STRIP: пути к текстурам в FBX не нужны, материалы всё равно
        # переназначаются по имени Editor-скриптом.
        path_mode="STRIP",
        embed_textures=False,
    )
    log(f"FBX: {path}  {os.path.getsize(path) // 1024} КБ")


def report() -> dict:
    tris = 0
    objs = []
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for o in sorted(bpy.data.objects, key=lambda a: a.name):
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            n = len(o.data.loop_triangles)
            tris += n
            objs.append((o.name, n))
            for v in o.data.vertices:
                w = o.matrix_world @ v.co
                for k in range(3):
                    lo[k] = min(lo[k], w[k])
                    hi[k] = max(hi[k], w[k])
        elif o.type == "EMPTY":
            objs.append((o.name, 0))
    return {"tris": tris, "objects": objs, "min": lo, "max": hi}


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    shaded, root = argv[0], os.path.abspath(argv[1])

    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(shaded))

    assets = os.path.join(root, "Assets", "BushPlane")
    tex_dst = os.path.join(assets, "Textures")
    model_dst = os.path.join(assets, "Models")
    blend_dst = os.path.join(root, "Blender")
    for d in (tex_dst, model_dst, blend_dst,
              os.path.join(assets, "Editor"), os.path.join(assets, "Scripts")):
        os.makedirs(d, exist_ok=True)

    # Карты уже лежат в рабочей папке запекания — переносим в пакет.
    src_tex = os.path.join(os.path.dirname(os.path.abspath(shaded)), "..", "..", "tex")
    src_tex = os.path.normpath(src_tex)
    for _, fn, _ in TEXTURES:
        s = os.path.join(src_tex, fn)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(tex_dst, fn))
            log(f"текстура -> {fn}  {os.path.getsize(s) // 1024} КБ")
        else:
            log(f"[!] нет файла {s}")

    purge_scratch()
    spin_for_unity()

    export_fbx(os.path.join(model_dst, "BushPlane.fbx"))

    rep = report()
    log(f"треугольников: {rep['tris']}, объектов: {len(rep['objects'])}")
    size = [rep["max"][k] - rep["min"][k] for k in range(3)]
    # После разворота оси Blender ещё Z-вверх: X — размах, Y — длина, Z — высота.
    log(f"габариты (Blender XYZ): {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} м")
    log(f"низ по Z: {rep['min'][2]:.3f} м (должен быть ~0 — самолёт стоит на земле)")

    # Сначала сохраняем в конечное место, и только потом привязываем текстуры.
    # Относительный путь Blender сворачивает относительно ОТКРЫТОГО файла: пока
    # открыт был out/shaded.blend, «//../Assets» указывал не туда, и после
    # сохранения «..» схлопывалось в несуществующий Blender/Assets.
    blend_path = os.path.join(blend_dst, "BushPlane.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    relink_textures("//../Assets/BushPlane/Textures")
    bpy.ops.wm.save_mainfile()
    log(f"blend: {blend_path}")

    missing = [i.name for i in bpy.data.images
               if i.source == "FILE" and not os.path.exists(bpy.path.abspath(i.filepath))]
    if missing:
        raise SystemExit(f"в .blend не разрешились текстуры: {missing}")
    log("текстуры в .blend связаны относительными путями")

    with open(os.path.join(root, "manifest.txt"), "w", encoding="utf-8") as f:
        f.write(f"BushPlane — {P.summary()}\n")
        f.write(f"треугольников: {rep['tris']}\n")
        f.write(f"габариты: {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} м\n\n")
        for name, n in rep["objects"]:
            f.write(f"{name:22s} {n if n else '-':>6}\n")
    log("manifest.txt записан")


if __name__ == "__main__":
    main()
