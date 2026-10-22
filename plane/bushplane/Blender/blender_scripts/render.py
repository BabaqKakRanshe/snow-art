"""Превью-рендеры с ракурсов, повторяющих референсные.

Запуск:
  blender --background --factory-startup --python render.py -- <scene.blend> <outdir> [views] [samples]

views — через запятую: hero,side,front,rear,top,detail_nose,detail_gear
"""

from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = {
    # имя:        (азимут°, высота°, дистанция, цель, фокус мм)
    # Дистанция и фокус подобраны так, чтобы размах 14.8 м влезал целиком:
    # при 62 мм с 17 м в кадр попадает меньше десяти метров, и самолёт режется.
    "hero":        (128.0, 22.0, 18.0, (0.0, -0.4, 1.7), 45.0),
    "side":        (180.0, 3.0, 21.0, (0.0, -0.9, 1.70), 42.0),
    "side_r":      (0.0, 3.0, 21.0, (0.0, -0.9, 1.70), 42.0),
    "front":       (90.0, 5.0, 21.0, (0.0, 0.0, 1.5), 42.0),
    "rear":        (270.0, 8.0, 21.0, (0.0, -2.0, 1.6), 42.0),
    "rear_q":      (300.0, 20.0, 18.0, (0.0, -1.6, 1.6), 45.0),
    "front_q":     (55.0, 18.0, 18.0, (0.0, 0.2, 1.5), 45.0),
    "top":         (90.0, 86.0, 24.0, (0.0, -0.8, 1.4), 45.0),
    # Ракурс референса: правый передний борт, камера высоко. Подобран так,
    # чтобы силуэт совпадал с REFERENCE.jpeg и детали можно было сравнивать
    # попиксельно, а не на глаз по разным ракурсам.
    "ref":         (52.0, 29.0, 19.5, (0.0, -0.35, 1.55), 50.0),
    "detail_nose": (140.0, 12.0, 7.0, (0.5, 3.0, 1.45), 55.0),
    "detail_gear": (150.0, 8.0, 5.5, (1.0, 1.5, 0.7), 50.0),
    "detail_tail": (215.0, 14.0, 7.5, (0.0, -4.8, 2.1), 50.0),
    "detail_cabin": (48.0, 16.0, 4.6, (0.0, 1.55, 1.80), 50.0),
    "detail_cargo": (335.0, 9.0, 5.6, (0.0, -2.15, 1.50), 50.0),
}

# Временная раскраска для оценки силуэта: пока настоящих материалов нет,
# белый монолит не даёт понять, читается кабина или нет.
PREVIEW_COLOURS = {
    "M_BushPlane_Body": ((0.62, 0.63, 0.65, 1.0), 0.45, 0.0, None),
    "M_BushPlane_Glass": ((0.045, 0.06, 0.08, 1.0), 0.08, 0.0, None),
    "M_BushPlane_Lights": ((0.55, 0.03, 0.03, 1.0), 0.25, 0.0, (2.4, 0.06, 0.05)),
}


def apply_preview_materials() -> None:
    """Временные цвета — только для несобранных материалов.

    После shade.py материалы несут запечённые карты, и затирать их превью
    означало бы смотреть на заглушку вместо результата.
    """
    # Один общий признак: как только в файле появился запечённый базовый цвет,
    # материалы собраны целиком — включая стекло и огни, у которых текстур нет
    # и по которым поштучно этого было бы не понять.
    if bpy.data.images.get("T_BushPlane_BaseColor"):
        return
    for name, (colour, rough, metal, emit) in PREVIEW_COLOURS.items():
        mat = bpy.data.materials.get(name)
        if mat is None:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        # Сокеты адресуем по имени с запасными вариантами: в 4.0 их массово
        # переименовали, и жёсткое имя молча промахнулось бы на другой версии.
        def put(keys, value):
            for k in keys:
                if k in bsdf.inputs:
                    bsdf.inputs[k].default_value = value
                    return
        put(["Base Color", "Base Colour"], colour)
        put(["Roughness"], rough)
        put(["Metallic"], metal)
        if emit:
            put(["Emission Color", "Emission Colour", "Emission"], (*emit, 1.0))
            put(["Emission Strength"], 6.0)


def pick_engine(scene, prefer: str) -> str:
    """Движок выбирается попыткой присвоения.

    RNA не перечисляет движки, зарегистрированные аддонами, а идентификатор
    EEVEE менялся между версиями. Текущее значение всегда валидно, поэтому
    пробуем желаемое и молча откатываемся.
    """
    current = scene.render.engine
    for name in (prefer, "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = name
            return name
        except TypeError:
            continue
    scene.render.engine = current
    return current


def setup_world(strength: float = 0.55) -> None:
    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.065, 1.0)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_light(name, kind, loc, energy, size=3.0, rot=(0, 0, 0), colour=(1, 1, 1)):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = colour
    if kind == "AREA":
        data.size = size
    elif kind == "SUN":
        data.angle = math.radians(3.0)
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.collection.objects.link(obj)
    return obj


def aim(obj, target: Vector) -> None:
    d = target - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_lights() -> None:
    """Три источника: ключевой сверху-слева, заполняющий справа, контровой сзади."""
    key = add_light("Key", "AREA", (-7.0, 6.5, 8.5), 6000.0, size=7.0)
    aim(key, Vector((0.0, 0.0, 1.4)))
    fill = add_light("Fill", "AREA", (8.5, 2.0, 3.2), 1400.0, size=8.0, colour=(0.82, 0.88, 1.0))
    aim(fill, Vector((0.0, 0.0, 1.4)))
    rim = add_light("Rim", "AREA", (3.0, -10.0, 5.0), 3000.0, size=6.0, colour=(1.0, 0.95, 0.88))
    aim(rim, Vector((0.0, -1.5, 1.6)))


def ensure_ground() -> None:
    me = bpy.data.meshes.new("PreviewGround")
    me.from_pydata(
        [(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [[0, 1, 2, 3]]
    )
    me.update()
    obj = bpy.data.objects.new("PreviewGround", me)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.new("PreviewGroundMat")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.055, 0.055, 0.06, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.38
    me.materials.append(mat)
    return obj


def make_camera(view: str):
    az, el, dist, target, lens = VIEWS[view]
    cam_data = bpy.data.cameras.new(f"Cam_{view}")
    cam_data.lens = lens
    cam = bpy.data.objects.new(f"Cam_{view}", cam_data)
    bpy.context.collection.objects.link(cam)
    a, e = math.radians(az), math.radians(el)
    t = Vector(target)
    cam.location = t + Vector((
        math.cos(a) * math.cos(e) * dist,
        math.sin(a) * math.cos(e) * dist,
        math.sin(e) * dist,
    ))
    aim(cam, t)
    return cam


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    scene_path = argv[0]
    outdir = argv[1]
    views = argv[2].split(",") if len(argv) > 2 else ["hero", "side", "front", "rear_q"]
    samples = int(argv[3]) if len(argv) > 3 else 32

    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(scene_path))
    scene = bpy.context.scene

    engine = pick_engine(scene, "BLENDER_EEVEE_NEXT")
    print(f"движок: {engine}")
    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    else:
        try:
            scene.eevee.taa_render_samples = samples
        except AttributeError:
            pass

    scene.render.resolution_x = 1200
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        pass

    setup_world()
    setup_lights()
    ensure_ground()
    apply_preview_materials()

    # Створки распахиваем: в модели они в нейтральной закрытой позе, а на
    # референсе открыты, и сравнивать надо в одинаковом положении.
    # Открываем только левую створку: на референсе распахнут один борт, и
    # отсек за ним тёмный. С обеими открытыми сквозь самолёт светит фон.
    import math as _m
    o = bpy.data.objects.get("CargoDoor_R")
    if o is not None:
        o.rotation_euler = (0.0, 0.0, _m.radians(-104.0))

    # Подложки-референсы и служебные объекты в кадр попадать не должны.
    for o in bpy.data.objects:
        if o.name.startswith(("REF_", "CAL_")):
            o.hide_render = True

    os.makedirs(os.path.abspath(outdir), exist_ok=True)
    for v in views:
        if v not in VIEWS:
            print(f"  неизвестный ракурс: {v}")
            continue
        # Ракурс сравнения печатаем в пропорции референса (4:3), иначе силуэты
        # не совместить наложением.
        if v == "ref":
            scene.render.resolution_x, scene.render.resolution_y = 1456, 1080
        else:
            scene.render.resolution_x, scene.render.resolution_y = 1200, 820
        cam = make_camera(v)
        scene.camera = cam
        scene.render.filepath = os.path.join(os.path.abspath(outdir), f"{v}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  {v}.png")


if __name__ == "__main__":
    main()
