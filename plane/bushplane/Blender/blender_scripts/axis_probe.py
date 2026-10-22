"""Маркер для измерения осей на пути Blender → FBX → Unity.

Три несимметричных выступа разной длины, каждый строго по своей оси:
  +Y (нос)     — шип длиной 5.0
  +X (правое)  — язычок длиной 2.0
  +Z (вверх)   — киль высотой 3.0
Корпус — куб 0.4. По длинам в импортированном меше однозначно читается,
какая ось Blender во что превратилась и не сменился ли знак.

Запуск:
  blender --background --factory-startup --python axis_probe.py -- <out.fbx>
"""

import os
import sys

import bpy

NOSE_Y, TAB_X, FIN_Z = 5.0, 2.0, 3.0


def main() -> None:
    out = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0

    verts, faces = [], []

    def box(cx, cy, cz, sx, sy, sz):
        base = len(verts)
        for dx in (-1, 1):
            for dy in (-1, 1):
                for dz in (-1, 1):
                    verts.append((cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2))
        for f in ([0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
                  [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]):
            faces.append([base + i for i in f])

    box(0, 0, 0, 0.4, 0.4, 0.4)                                  # корпус
    box(0, NOSE_Y / 2, 0, 0.2, NOSE_Y, 0.2)                      # нос  -> +Y
    box(TAB_X / 2, 0, 0, TAB_X, 0.2, 0.2)                        # право -> +X
    box(0, 0, FIN_Z / 2, 0.2, 0.2, FIN_Z)                        # верх  -> +Z

    me = bpy.data.meshes.new("AxisProbe")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    obj = bpy.data.objects.new("AxisProbe", me)
    bpy.context.collection.objects.link(obj)

    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    print("BLENDER_MIN", [round(v, 3) for v in lo])
    print("BLENDER_MAX", [round(v, 3) for v in hi])
    print(f"BLENDER_SIZE x={hi[0]-lo[0]:.2f} y={hi[1]-lo[1]:.2f} z={hi[2]-lo[2]:.2f}")

    # Измерение показало: при этом пресете Blender +Y уезжает в Unity −Z, то
    # есть нос смотрел бы назад. Разворот на 180° вокруг Z — настоящий поворот
    # (определитель +1), в отличие от отражения по одной оси: оно вывернуло бы
    # нормали и сделало крутку винта левой. Правый борт при этом попадает на
    # Unity +X, что для носа в +Z и есть право, поэтому имена _L/_R остаются.
    if "--no-spin" not in sys.argv:
        from mathutils import Matrix
        R = Matrix.Rotation(3.141592653589793, 4, "Z")
        me.transform(R)
        me.update()

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    # Тот самый «комбинированный» пресет, которым сделаны существующие модели
    # проекта: преобразование осей запекается в вершины, корень остаётся
    # единичным, метр Blender равен юниту Unity.
    bpy.ops.export_scene.fbx(
        filepath=os.path.abspath(out),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True,
        axis_forward="-Z",
        axis_up="Y",
        object_types={"MESH", "EMPTY"},
        mesh_smooth_type="FACE",
        use_triangles=True,
        use_tspace=False,
        bake_anim=False,
        path_mode="COPY",
    )
    print("EXPORTED", os.path.abspath(out))


if __name__ == "__main__":
    main()
