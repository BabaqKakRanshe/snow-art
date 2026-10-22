"""Развёртка, растеризация карт и запекание.

Запуск:
  blender --background --factory-startup --python-exit-code 1 --python shade.py -- \
      <geo.blend> <texdir> <out.blend> [размер] [сэмплы AO]

Что получается:
  T_BushPlane_BaseColor.png  sRGB
  T_BushPlane_Mask.png       Non-Color, R=metallic G=occlusion B=0 A=smoothness
  T_BushPlane_Normal.png     Non-Color, касательное пространство, зелёный вверх

Разделение труда. Цвет, металличность, шероховатость и рельеф считает
livery.evaluate — обычный numpy по мировой координате точки. А перевод рельефа
в касательное пространство и трассировку затенения делает Cycles: его базис
касательных совпадает с тем, что Unity считает по MikkTSpace, и воспроизводить
это вручную значило бы гадать о знаке зелёного канала.
"""

from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import livery  # noqa: E402
import plane_params as P  # noqa: E402

UV_NAME = "UVMap"


def log(msg: str) -> None:
    print(f"[shade] {msg}", flush=True)


# ==========================================================================
# Развёртка
# ==========================================================================

def unwrap_all(meshes) -> None:
    """Одна развёртка на все объекты сразу — значит один общий атлас.

    Раскладка может быть какой угодно: рисунок ливреи задан в мировых
    координатах, поэтому шов острова его не разрывает. Нам важно только, чтобы
    острова не перекрывались и между ними оставался зазор под поля запекания.
    """
    for o in meshes:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name=UV_NAME)
        o.data.uv_layers.active = o.data.uv_layers[0]
        o.data.uv_layers[0].name = UV_NAME

    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # angle_limit в радианах (в 5.2 значение по умолчанию 1.1519 рад = 66°).
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(64.0),
        island_margin=0.004,
        correct_aspect=True,
        scale_to_bounds=False,
    )
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


# ==========================================================================
# Сбор треугольников
# ==========================================================================

def gather_triangles(meshes):
    """Треугольники всех объектов в мировых координатах: UV, позиции, нормали, деталь."""
    uv_all, pos_all, nrm_all, part_all = [], [], [], []

    for obj in meshes:
        me = obj.data
        me.calc_loop_triangles()
        n_tri = len(me.loop_triangles)
        if n_tri == 0:
            continue

        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)

        vn = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("normal", vn)
        vn = vn.reshape(-1, 3)

        tri_v = np.empty(n_tri * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", tri_v)
        tri_v = tri_v.reshape(-1, 3)

        tri_l = np.empty(n_tri * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("loops", tri_l)
        tri_l = tri_l.reshape(-1, 3)

        tri_p = np.empty(n_tri, dtype=np.int32)
        me.loop_triangles.foreach_get("polygon_index", tri_p)

        uvl = me.uv_layers[UV_NAME].uv
        uvs = np.empty(len(uvl) * 2, dtype=np.float32)
        uvl.foreach_get("vector", uvs)
        uvs = uvs.reshape(-1, 2)

        attr = me.attributes.get("part")
        if attr is None:
            face_part = np.zeros(len(me.polygons), dtype=np.int32)
        else:
            face_part = np.empty(len(me.polygons), dtype=np.int32)
            attr.data.foreach_get("value", face_part)

        # Локальные координаты -> мировые. Повороты у всех объектов единичные,
        # но перенос пивота есть у каждой подвижной части.
        mw = np.array(obj.matrix_world.to_4x4())
        rot = mw[:3, :3]
        loc = mw[:3, 3]

        p = co[tri_v] @ rot.T + loc                      # (T,3,3)
        n = vn[tri_v] @ rot.T
        nlen = np.linalg.norm(n, axis=2, keepdims=True)
        n = n / np.maximum(nlen, 1e-9)

        uv_all.append(uvs[tri_l])
        pos_all.append(p.astype(np.float32))
        nrm_all.append(n.astype(np.float32))
        part_all.append(face_part[tri_p])

    return (
        np.concatenate(uv_all),
        np.concatenate(pos_all),
        np.concatenate(nrm_all),
        np.concatenate(part_all),
    )


# ==========================================================================
# Растеризация в атлас
# ==========================================================================

def rasterize(uv, pos, nrm, part, size: int):
    """Строит буфер поверхности: в каждом тексéле — точка, нормаль и деталь."""
    w = h = size
    pos_buf = np.zeros((h, w, 3), dtype=np.float32)
    nrm_buf = np.zeros((h, w, 3), dtype=np.float32)
    part_buf = np.zeros((h, w), dtype=np.int32)
    cov = np.zeros((h, w), dtype=bool)

    scale = np.array([w, h], dtype=np.float32)
    # Небольшой отрицательный допуск: иначе между соседними треугольниками
    # остаётся цепочка незакрашенных пикселей и по атласу идут тонкие швы.
    eps = -0.004

    for t in range(len(uv)):
        q = uv[t] * scale
        x0 = max(int(math.floor(q[:, 0].min())) - 1, 0)
        x1 = min(int(math.ceil(q[:, 0].max())) + 2, w)
        y0 = max(int(math.floor(q[:, 1].min())) - 1, 0)
        y1 = min(int(math.ceil(q[:, 1].max())) + 2, h)
        if x1 <= x0 or y1 <= y0:
            continue

        e0 = q[1] - q[0]
        e1 = q[2] - q[0]
        den = e0[0] * e1[1] - e1[0] * e0[1]
        if abs(den) < 1e-12:
            continue

        px = np.arange(x0, x1, dtype=np.float32) + 0.5
        py = np.arange(y0, y1, dtype=np.float32) + 0.5
        gx, gy = np.meshgrid(px, py)
        dx = gx - q[0, 0]
        dy = gy - q[0, 1]
        b1 = (dx * e1[1] - e1[0] * dy) / den
        b2 = (e0[0] * dy - dx * e0[1]) / den
        b0 = 1.0 - b1 - b2
        inside = (b0 >= eps) & (b1 >= eps) & (b2 >= eps)
        if not inside.any():
            continue

        sel = np.nonzero(inside)
        ys = sel[0] + y0
        xs = sel[1] + x0
        w0 = b0[inside][:, None]
        w1 = b1[inside][:, None]
        w2 = b2[inside][:, None]

        pos_buf[ys, xs] = w0 * pos[t, 0] + w1 * pos[t, 1] + w2 * pos[t, 2]
        nn = w0 * nrm[t, 0] + w1 * nrm[t, 1] + w2 * nrm[t, 2]
        nrm_buf[ys, xs] = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
        part_buf[ys, xs] = part[t]
        cov[ys, xs] = True

    return pos_buf, nrm_buf, part_buf, cov


def dilate(img: np.ndarray, cov: np.ndarray, rounds: int = 12) -> np.ndarray:
    """Растягивает края островов наружу.

    Без этого при мипмаппинге в шов между островами затекает фон, и по модели
    идут тёмные линии. Полям запекания Cycles соответствует вручную только для
    своих карт, растеризованные приходится расширять самим.
    """
    out = img.copy()
    filled = cov.copy()
    for _ in range(rounds):
        acc = np.zeros_like(out)
        cnt = np.zeros(cov.shape, dtype=np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sh = np.roll(np.roll(out, dy, axis=0), dx, axis=1)
            sm = np.roll(np.roll(filled, dy, axis=0), dx, axis=1)
            m = sm.astype(np.float32)
            acc += sh * (m[..., None] if out.ndim == 3 else m)
            cnt += m
        new = (~filled) & (cnt > 0)
        if not new.any():
            break
        safe = np.maximum(cnt, 1.0)
        avg = acc / (safe[..., None] if out.ndim == 3 else safe)
        out[new] = avg[new]
        filled |= new
    return out


# ==========================================================================
# Изображения Blender
# ==========================================================================

def make_image(name: str, size: int, is_data: bool, alpha: bool = False,
               float_buffer: bool = False):
    """float_buffer нужен промежуточной карте высот.

    В 8 битах пологий рельеф (вмятины обшивки — три уровня из 256) квантуется
    ступенями, а Bump берёт производную и превращает границы ступеней в сетку
    тонких светлых линий по всей поверхности: на рендере это читается как
    краклюр по краске. В поставку эта карта не идёт, поэтому лишняя память
    ничего не стоит.
    """
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    # Цветовое пространство задаётся ТОЛЬКО здесь: присвоение
    # colorspace_settings.name после записи обнуляет буфер.
    return bpy.data.images.new(
        name, width=size, height=size, alpha=alpha,
        float_buffer=float_buffer, is_data=is_data,
    )


def write_image(img, rgba: np.ndarray) -> None:
    """rgba: (H, W, 4), значения 0..1. Строки идут снизу вверх, как в Blender."""
    img.pixels.foreach_set(rgba.reshape(-1).astype(np.float32))
    img.update()


def save_image(img, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    # filepath_raw, а не filepath: второй пересоздаёт источник изображения и
    # записывает полностью чёрный файл.
    img.filepath_raw = os.path.abspath(path)
    img.file_format = "PNG"
    img.save()
    log(f"сохранено {os.path.basename(path)}  {os.path.getsize(path) // 1024} КБ")


def read_image(img) -> np.ndarray:
    buf = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(img.size[1], img.size[0], 4)


# ==========================================================================
# Запекание
# ==========================================================================

def enable_gpu() -> str:
    """Включает OPTIX/CUDA, если есть. RNA в фоне отдаёт пустой список
    устройств, поэтому присваиваем вслепую и проверяем результатом."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        try:
            prefs.refresh_devices()
        except Exception:
            pass
        for d in prefs.devices:
            d.use = d.type != "CPU"
        if getattr(prefs, "has_active_device", lambda: False)():
            bpy.context.scene.cycles.device = "GPU"
            return kind
    return "CPU"


def clear_nodes(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    return nt


def setup_bake_material(mat, height_img, target_img, bump_distance: float):
    """Материал на время запекания: высота -> Bump -> нормаль Principled.

    Distance у Bump в 5.2 по умолчанию 0.001 — при нём карта нормалей
    запекается идеально плоской, без единой ошибки в логе.
    """
    nt = clear_nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    bump = nt.nodes.new("ShaderNodeBump")

    tex.image = height_img
    tex.interpolation = "Smart"
    bump.inputs["Distance"].default_value = bump_distance
    bump.inputs["Strength"].default_value = 1.0

    nt.links.new(tex.outputs["Color"], bump.inputs["Height"])
    sock = next(s for s in bsdf.inputs if s.identifier == "Normal")
    nt.links.new(bump.outputs["Normal"], sock)
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    # Узел-приёмник: Cycles пишет в активное выделенное изображение.
    dst = nt.nodes.new("ShaderNodeTexImage")
    dst.image = target_img
    dst.select = True
    nt.nodes.active = dst
    return dst


def setup_ao_material(mat, target_img):
    nt = clear_nodes(mat)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    dst = nt.nodes.new("ShaderNodeTexImage")
    dst.image = target_img
    dst.select = True
    nt.nodes.active = dst
    return dst


def do_bake(meshes, bake_type: str, samples: int, target_img, extra=None) -> None:
    sc = bpy.context.scene
    sc.cycles.samples = samples
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    kw = dict(
        type=bake_type,
        margin=16,
        margin_type="ADJACENT_FACES",
        use_clear=True,
        use_selected_to_active=False,
        target="IMAGE_TEXTURES",
        save_mode="INTERNAL",
    )
    if extra:
        kw.update(extra)
    t0 = time.time()
    bpy.ops.object.bake(**kw)
    log(f"запечено {bake_type}: {time.time() - t0:.1f} с")


# ==========================================================================
# Итоговые материалы
# ==========================================================================

def build_final_materials(base_img, mask_img, normal_img) -> None:
    body = bpy.data.materials[P.MAT_NAMES[0]]
    nt = clear_nodes(body)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    def sock(name):
        return next(s for s in bsdf.inputs if s.identifier == name)

    t_base = nt.nodes.new("ShaderNodeTexImage")
    t_base.image = base_img
    t_base.location = (-700, 300)
    nt.links.new(t_base.outputs["Color"], sock("Base Color"))

    t_mask = nt.nodes.new("ShaderNodeTexImage")
    t_mask.image = mask_img
    t_mask.location = (-700, 0)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t_mask.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Red"], sock("Metallic"))
    # В маске лежит гладкость (так её читает URP), а Principled ждёт
    # шероховатость — переворачиваем.
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(t_mask.outputs["Alpha"], inv.inputs[1])
    nt.links.new(inv.outputs[0], sock("Roughness"))

    t_nrm = nt.nodes.new("ShaderNodeTexImage")
    t_nrm.image = normal_img
    t_nrm.location = (-700, -300)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(t_nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], sock("Normal"))

    glass = bpy.data.materials[P.MAT_NAMES[1]]
    nt = clear_nodes(glass)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    g = nt.nodes.new("ShaderNodeBsdfPrincipled")
    for name, val in (
        ("Base Color", (0.030, 0.038, 0.046, 1.0)),
        ("Roughness", 0.24),
        ("Metallic", 0.0),
        ("Alpha", 0.58),
    ):
        s = next((s for s in g.inputs if s.identifier == name), None)
        if s:
            s.default_value = val
    nt.links.new(g.outputs[0], out.inputs["Surface"])
    glass.blend_method = "BLEND"
    glass.use_backface_culling = True

    lights = bpy.data.materials[P.MAT_NAMES[2]]
    nt = clear_nodes(lights)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeBsdfPrincipled")
    for name, val in (
        ("Base Color", (0.30, 0.02, 0.02, 1.0)),
        ("Roughness", 0.25),
        ("Emission Color", (1.0, 0.025, 0.015, 1.0)),
        ("Emission Strength", 9.0),
    ):
        s = next((s for s in e.inputs if s.identifier == name), None)
        if s:
            s.default_value = val
    nt.links.new(e.outputs[0], out.inputs["Surface"])


# ==========================================================================

# Пачка подобрана по памяти: fbm держит по несколько временных массивов
# int64 на точку, и при 4096² разом это десятки гигабайт.
CHUNK = 1_500_000


def evaluate_chunked(pos, nrm, part) -> dict:
    """livery.evaluate по частям. Функция чистая, поэтому склейка безопасна."""
    n = len(pos)
    if n <= CHUNK:
        return livery.evaluate(pos, nrm, part)
    parts: list[dict] = []
    for a in range(0, n, CHUNK):
        b = min(a + CHUNK, n)
        parts.append(livery.evaluate(pos[a:b], nrm[a:b], part[a:b]))
        log(f"  раскраска {b}/{n}")
    return {k: np.concatenate([p[k] for p in parts], axis=0) for k in parts[0]}


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    geo, texdir, outblend = argv[0], argv[1], argv[2]
    size = int(argv[3]) if len(argv) > 3 else 2048
    ao_samples = int(argv[4]) if len(argv) > 4 else 48

    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(geo))
    sc = bpy.context.scene
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    meshes.sort(key=lambda o: o.name)
    log(f"объектов: {len(meshes)}")

    t0 = time.time()
    unwrap_all(meshes)
    log(f"развёртка: {time.time() - t0:.1f} с")

    uv, pos, nrm, part = gather_triangles(meshes)
    log(f"треугольников: {len(uv)}")

    t0 = time.time()
    pos_buf, nrm_buf, part_buf, cov = rasterize(uv, pos, nrm, part, size)
    fill = cov.mean() * 100.0
    log(f"растеризация: {time.time() - t0:.1f} с, заполнение атласа {fill:.1f}%")
    if fill < 8.0:
        raise SystemExit(f"атлас заполнен всего на {fill:.1f}% — развёртка не удалась")

    idx = np.nonzero(cov)
    t0 = time.time()
    res = evaluate_chunked(pos_buf[idx], nrm_buf[idx], part_buf[idx])
    log(f"раскраска: {time.time() - t0:.1f} с по {len(idx[0])} тексéлям")

    def scatter(vals, channels: int, default: float):
        buf = np.full((size, size, channels), default, dtype=np.float32)
        buf[idx] = vals if channels > 1 else vals[:, None]
        return dilate(buf, cov)

    base_rgb = scatter(res["base"], 3, 0.0)
    metal = scatter(res["metallic"], 1, 0.0)[..., 0]
    rough = scatter(res["roughness"], 1, 0.6)[..., 0]
    height = scatter(res["height"], 1, 0.5)[..., 0]

    # --- базовый цвет --------------------------------------------------------
    base_img = make_image("T_BushPlane_BaseColor", size, is_data=False, alpha=False)
    rgba = np.concatenate([base_rgb, np.ones((size, size, 1), np.float32)], axis=2)
    write_image(base_img, rgba)
    save_image(base_img, os.path.join(texdir, "T_BushPlane_BaseColor.png"))

    # --- высота (промежуточная, в поставку не идёт) -------------------------
    height_img = make_image("_BushPlane_Height", size, is_data=True, alpha=False,
                            float_buffer=True)
    hh = np.repeat(height[..., None], 3, axis=2)
    write_image(height_img, np.concatenate([hh, np.ones((size, size, 1), np.float32)], axis=2))

    # --- запекание -----------------------------------------------------------
    try:
        sc.render.engine = "CYCLES"
    except TypeError as exc:
        raise SystemExit(f"Cycles недоступен, запекание невозможно: {exc}")
    dev = enable_gpu()
    log(f"устройство Cycles: {dev}")

    normal_img = make_image("T_BushPlane_Normal", size, is_data=True, alpha=False)
    mats = [bpy.data.materials[n] for n in P.MAT_NAMES]
    # Bump-узел вешаем на ВСЕ материалы: без узла-приёмника материал молча
    # пропускается, и его область карты остаётся чёрной, а чёрный в карте
    # нормалей — это не «нет рельефа», а недопустимый вектор.
    for m in mats:
        setup_bake_material(m, height_img, normal_img, bump_distance=0.26)
    do_bake(meshes, "NORMAL", 4, normal_img)
    save_image(normal_img, os.path.join(texdir, "T_BushPlane_Normal.png"))

    ao_img = make_image("_BushPlane_AO", size, is_data=True, alpha=False)
    for m in mats:
        setup_ao_material(m, ao_img)
    do_bake(meshes, "AO", ao_samples, ao_img)

    ao = read_image(ao_img)[..., 0]
    # Незакрытые тексели после запекания остаются чёрными, то есть «полностью
    # в тени». В зазорах атласа это даёт тёмную кайму — подставляем единицу.
    ao = np.where(cov, ao, 1.0)
    ao = dilate(ao[..., None], cov)[..., 0]

    # --- упакованная маска под URP -------------------------------------------
    # R = metallic, G = occlusion, B = 0, A = smoothness.
    # Именно smoothness, а не roughness: URP читает канал как гладкость, и
    # перепутанные местами дают зеркальный самолёт там, где должен быть матовый.
    mask = np.zeros((size, size, 4), dtype=np.float32)
    mask[..., 0] = metal
    mask[..., 1] = ao
    mask[..., 2] = 0.0
    mask[..., 3] = 1.0 - rough
    mask_img = make_image("T_BushPlane_Mask", size, is_data=True, alpha=True)
    write_image(mask_img, mask)
    save_image(mask_img, os.path.join(texdir, "T_BushPlane_Mask.png"))

    # --- итоговые материалы ---------------------------------------------------
    build_final_materials(base_img, mask_img, normal_img)
    for tmp in ("_BushPlane_Height", "_BushPlane_AO"):
        img = bpy.data.images.get(tmp)
        if img:
            img.use_fake_user = False

    os.makedirs(os.path.dirname(os.path.abspath(outblend)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(outblend))
    log(f"сцена сохранена: {outblend}")


if __name__ == "__main__":
    main()
