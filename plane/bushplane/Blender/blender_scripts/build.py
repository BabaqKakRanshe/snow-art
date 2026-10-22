"""Сборка геометрии самолёта.

Запуск:
  blender --background --factory-startup --python-exit-code 1 --python build.py -- out/geo.blend

Результат: сцена с плоской иерархией (корень-пустышка + подвижные части первым
уровнем) и тремя слотами материалов-заглушек. Материалы и запекание — в shade.py.

Иерархия намеренно плоская: вложенность глубже первого уровня ломает экспорт
FBX с запечённым преобразованием осей, а без него импорт в Unity требует ручной
галки. Колесо и стойка поэтому соседи, а не родитель с потомком — связать их
обратно стоит рига три строки, зато ассет кладётся в проект без настроек.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import plane_lib as L  # noqa: E402
import plane_params as P  # noqa: E402


# ==========================================================================
# Служебное
# ==========================================================================

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0


def make_materials() -> list:
    """Материалы-заглушки. Настоящие узлы навешивает shade.py."""
    mats = []
    for name in P.MAT_NAMES:
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mats.append(m)
    return mats


def station_at(stations: list[tuple], y: float) -> tuple:
    """Интерполирует станцию фюзеляжа на произвольной координате y.

    Нужно, чтобы границы грузового проёма попадали ровно на станцию: тогда
    проём вырезается пропуском граней, а не булевой операцией, и сетка
    остаётся регулярной.
    """
    ys = [s[0] for s in stations]
    if y >= ys[0]:
        return stations[0]
    if y <= ys[-1]:
        return stations[-1]
    for i in range(len(stations) - 1):
        a, b = stations[i], stations[i + 1]
        if b[0] <= y <= a[0]:
            t = (a[0] - y) / (a[0] - b[0])
            return (y,) + tuple(L.lerp(a[k], b[k], t) for k in range(1, len(a)))
    return stations[-1]


def insert_stations(stations: list[tuple], extra_y: list[float]) -> list[tuple]:
    out = list(stations)
    for y in extra_y:
        if any(abs(s[0] - y) < 1e-6 for s in out):
            continue
        out.append(station_at(stations, y))
    out.sort(key=lambda s: -s[0])
    return out


# ==========================================================================
# Фюзеляж
# ==========================================================================

# Кольцевые индексы проёма при SEG_FUSELAGE=24: 0 — правый борт по миделю,
# 6 — верх, 12 — левый борт, 18 — низ. Семь точек дают проём от пола почти
# до потолка — на референсе он именно во всю высоту борта.
def aperture_rings(n: int) -> tuple[list[int], list[int]]:
    q = n // 4
    right = [(n - 3 + k) % n for k in range(7)]        # 21..3
    left = [(q * 2 - 3 + k) % n for k in range(7)]      # 9..15
    return right, left


def in_window(centre: tuple[float, float, float]) -> bool:
    """Попадает ли центр грани в один из оконных проёмов."""
    x, y, z = centre
    for y0, y1, z0, z1 in P.SIDE_WINDOWS:
        if y0 <= y <= y1 and z0 <= z <= z1 and abs(x) > 0.30:
            return True
    wy0, wy1 = P.WINDSCREEN_Y
    if wy0 <= y <= wy1 and z > P.WINDSCREEN_Z and abs(x) < P.WINDSCREEN_HALF_W:
        return True
    return False


def build_fuselage(b: L.MeshBuilder):
    """Обшивка фюзеляжа сеткой «станции × кольца».

    Возвращает сетку вершин вырезанного под грузовой проём участка — по ней
    створка строится одной оболочкой и садится в проём вершина в вершину.
    """
    n = P.SEG_FUSELAGE
    cy0, cy1 = P.CARGO_Y
    # Станции ставим на границы КАЖДОГО проёма — и грузового, и оконных.
    # Материал грани выбирается по её центру, а грань между станциями длиннее
    # окна: без этих станций центр не попадал внутрь окна, и почти все окна
    # молча красились как обшивка.
    cuts = [cy0, cy1]
    for wy0, wy1, _, _ in P.SIDE_WINDOWS:
        cuts += [wy0, wy1]
    cuts += list(P.WINDSCREEN_Y)
    stations = insert_stations(P.FUSELAGE_STATIONS, cuts)

    rings_world: list[list[L.Vec3]] = []
    for y, hw, ht, hb, e, zc in stations:
        rings_world.append(L.place_yz(L.superellipse(hw, ht, hb, e, n), y, zc))

    idx = [b.add_verts(r) for r in rings_world]

    ap_right, ap_left = aperture_rings(n)
    ap_cols = set()
    for r in (ap_right, ap_left):
        for k in range(len(r) - 1):
            ap_cols.add(r[k])

    # Индексы станций, между которыми лежит проём.
    s_from = next(i for i, s in enumerate(stations) if abs(s[0] - cy1) < 1e-6)
    s_to = next(i for i, s in enumerate(stations) if abs(s[0] - cy0) < 1e-6)

    # Остекление считаем отдельным проходом: утопить стекло нельзя, не зная
    # соседей — рама ставится только там, где окно граничит с обшивкой, а между
    # двумя гранями одного окна перегородки быть не должно.
    rows = len(idx) - 1
    glass_face = [[False] * n for _ in range(rows)]
    for s in range(rows):
        wa, wc = rings_world[s], rings_world[s + 1]
        for i in range(n):
            if s_from <= s < s_to and i in ap_cols:
                continue
            j = (i + 1) % n
            cen = tuple(
                (wa[i][k] + wa[j][k] + wc[j][k] + wc[i][k]) / 4.0 for k in range(3)
            )
            glass_face[s][i] = in_window(cen)

    # Утопленные вершины создаём лениво и с ключом (станция, точка кольца):
    # соседние грани одного окна обязаны их делить.
    inset_cache: dict[tuple[int, int], int] = {}

    def inset_vert(s: int, i: int) -> int:
        key = (s, i)
        v = inset_cache.get(key)
        if v is None:
            x, y, z = rings_world[s][i]
            zc = stations[s][5]
            dx, dz = x, z - zc
            ln = math.hypot(dx, dz) or 1.0
            d = P.WINDOW_INSET
            v = b.add_verts([(x - dx / ln * d, y, z - dz / ln * d)])[0]
            inset_cache[key] = v
        return v

    def is_glass(s: int, i: int) -> bool:
        return 0 <= s < rows and glass_face[s][i % n]

    for s in range(rows):
        a, c = idx[s], idx[s + 1]
        for i in range(n):
            j = (i + 1) % n
            if s_from <= s < s_to and i in ap_cols:
                continue
            if not glass_face[s][i]:
                b.part = P.PART_SKIN
                b.add_face([a[i], a[j], c[j], c[i]], P.MAT_BODY, True)
                continue
            ai, aj = inset_vert(s, i), inset_vert(s, j)
            ci, cj = inset_vert(s + 1, i), inset_vert(s + 1, j)
            b.part = P.PART_GLASS
            b.add_face([ai, aj, cj, ci], P.MAT_GLASS, True)
            # Щёчка рамы — по каждому ребру, за которым не такое же стекло.
            b.part = P.PART_SKIN
            for neighbour, o0, o1, n0, n1 in (
                (is_glass(s - 1, i), a[i], a[j], ai, aj),
                (is_glass(s, i + 1), a[j], c[j], aj, cj),
                (is_glass(s + 1, i), c[j], c[i], cj, ci),
                (is_glass(s, i - 1), c[i], a[i], ci, ai),
            ):
                if not neighbour:
                    b.add_face([o0, o1, n1, n0], P.MAT_BODY, False)

    # Торцы: нос стыкуется с капотом, хвост закрывается.
    b.part = P.PART_SKIN
    b.cap(list(reversed(idx[0])), P.MAT_BODY, False)
    b.cap(idx[-1], P.MAT_BODY, False)

    # Сетка проёма: строки — станции, столбцы — точки кольца.
    grids = {
        "R": [[rings_world[s][i] for i in ap_right] for s in range(s_from, s_to + 1)],
        "L": [[rings_world[s][i] for i in ap_left] for s in range(s_from, s_to + 1)],
    }
    return grids, stations


def build_nose(b: L.MeshBuilder) -> list[L.Vec3]:
    """Секция от перегородки до капота. Возвращает переднее кольцо."""
    n = P.SEG_FUSELAGE
    rings = [
        L.place_yz(L.superellipse(hw, ht, hb, e, n), y, zc)
        for y, hw, ht, hb, e, zc in P.NOSE_STATIONS
    ]
    idx = [b.add_verts(r) for r in rings]
    for s in range(len(idx) - 1):
        wa, wc = rings[s], rings[s + 1]
        for i in range(n):
            j = (i + 1) % n
            quad_w = [wa[i], wa[j], wc[j], wc[i]]
            cen = tuple(sum(v[k] for v in quad_w) / 4.0 for k in range(3))
            glass = in_window(cen)
            # Всё, что впереди перегородки, — капот, а он на референсе тёмный.
            # Раньше секция считалась обшивкой и красилась в красный, из-за чего
            # нос сливался с фюзеляжем в одно красное тело.
            b.part = P.PART_GLASS if glass else P.PART_COWL
            b.add_face([idx[s][i], idx[s][j], idx[s + 1][j], idx[s + 1][i]],
                       P.MAT_GLASS if glass else P.MAT_BODY, True)
    return rings[-1]


def build_cowl(b: L.MeshBuilder, front_ring: list[L.Vec3]) -> None:
    """Лобовая обечайка капота: от кромки внутрь, к кольцу вокруг кока.

    Кок стоит ВПЕРЕДИ капота, поэтому лоб капота — не заглушка, а кольцо.
    Целевое кольцо строится в той же угловой параметризации, что и сечение
    носа, иначе обечайку перекрутит на переходе от коробки к окружности.
    """
    b.part = P.PART_COWL
    n = len(front_ring)
    target = [
        (P.COWL_LIP_R * math.cos(2.0 * math.pi * i / n),
         P.COWL_LIP_R * math.sin(2.0 * math.pi * i / n))
        for i in range(n)
    ]
    prev_i = b.add_verts(front_ring)
    ring: list[L.Vec3] = []
    for y_off, t in ((0.018, 0.34), (0.035, 0.74), (0.045, 1.0)):
        ring = []
        for i, (x, _, z) in enumerate(front_ring):
            tx, tz = target[i]
            ring.append((
                L.lerp(x, tx, t),
                P.Y_COWL_FRONT + y_off,
                L.lerp(z, P.PROP_HUB_Z + tz, t),
            ))
        cur_i = b.add_verts(ring)
        b.bridge(prev_i, cur_i, P.MAT_BODY, True, True)
        prev_i = cur_i

    # Носовая чашка: цилиндр от обечайки вперёд, на него садится кок. Кок шире
    # чашки, поэтому по стыку идёт тень — на референсе именно она отделяет кок
    # от капота. Без чашки лоб капота был плоской шайбой вокруг кока.
    cup = [(x, P.Y_SPINNER_BASE + 0.012, z) for x, _, z in ring]
    ci = b.add_verts(cup)
    b.bridge(prev_i, ci, P.MAT_BODY, True, True)

    # Внутрь — обратный конус: в зазоре между коком и чашкой видна глубина,
    # а не бумажный край и не просвет насквозь.
    inner = [
        (x * 0.62, P.Y_SPINNER_BASE - 0.16, P.PROP_HUB_Z + (z - P.PROP_HUB_Z) * 0.62)
        for x, _, z in ring
    ]
    ii = b.add_verts(inner)
    b.bridge(ci, ii, P.MAT_BODY, True, True)
    b.cap(list(reversed(ii)), P.MAT_BODY, False)


def build_exhaust(b: L.MeshBuilder) -> None:
    """Выхлопной патрубок из-под капота — деталь, ломающая гладкость борта."""
    b.part = P.PART_COWL
    x, y, z, r, ln = P.EXHAUST
    path = [(x - 0.05, y, z + 0.02),
            (x + 0.02, y - ln * 0.45, z - 0.02),
            (x + 0.05, y - ln, z - 0.05)]
    b.tube(path, [r * 1.25, r, r * 0.95], 10, P.MAT_BODY, True)
    # Раструб на срезе — иначе труба обрывается бумажным кольцом.
    b.tube([path[-1], (x + 0.055, y - ln - 0.055, z - 0.058)],
           [r * 1.20, r * 1.12], 10, P.MAT_BODY, True)


def build_chin_scoop(b: L.MeshBuilder) -> None:
    """Подбородочный воздухозаборник под капотом."""
    b.part = P.PART_COWL
    y0, zc, w, h, dep = P.CHIN_SCOOP
    hw, hh = w * 0.5, h * 0.5
    mouth = [(-hw, y0, zc - hh), (hw, y0, zc - hh), (hw, y0, zc + hh), (-hw, y0, zc + hh)]
    # Горло уходит назад и ВВЕРХ, внутрь капота: так заборник сливается с
    # днищем, а не висит под ним отдельным телом.
    throat = [(x * 0.72, y0 - dep, zc + hh * 1.5 + (z - zc) * 0.3) for x, _, z in mouth]
    mi = b.add_verts(mouth)
    ti = b.add_verts(throat)
    b.bridge(mi, ti, P.MAT_BODY, True, True)
    b.cap(list(reversed(ti)), P.MAT_BODY, False)
    # Козырёк: губа чуть шире рта, выдвинутая вперёд и загнутая вверх.
    lip = [(x * 1.08, y0 + 0.045, zc + hh * 0.5 + (z - zc) * 0.85) for x, _, z in mouth]
    li = b.add_verts(lip)
    b.bridge(li, mi, P.MAT_BODY, True, True)


def build_intakes(b: L.MeshBuilder) -> None:
    """Два прямоугольных воздухозаборника в лобовой обечайке, по бокам кока."""
    b.part = P.PART_COWL
    for sx in (-1.0, 1.0):
        x = sx * P.INTAKE_X
        y_mouth = P.Y_SPINNER_BASE - 0.01
        hw, hh = P.INTAKE_W * 0.5, P.INTAKE_H * 0.5
        mouth = [
            (x - hw, y_mouth, P.INTAKE_Z - hh), (x + hw, y_mouth, P.INTAKE_Z - hh),
            (x + hw, y_mouth, P.INTAKE_Z + hh), (x - hw, y_mouth, P.INTAKE_Z + hh),
        ]
        back = [
            (x + (vx - x) * 0.76, y_mouth - P.INTAKE_DEPTH, P.INTAKE_Z + (vz - P.INTAKE_Z) * 0.76)
            for vx, _, vz in mouth
        ]
        mi = b.add_verts(mouth)
        bi = b.add_verts(back)
        b.bridge(mi, bi, P.MAT_BODY, False, True)
        b.cap(list(reversed(bi)), P.MAT_BODY, False)


def build_windscreen_post(b: L.MeshBuilder) -> None:
    """Средняя стойка лобового стекла.

    Разрезать стекло по кольцевой сетке фюзеляжа нельзя: ближайшие точки
    кольца стоят на x = ±0.42, узкой грани под стойку там просто нет.
    Поэтому стойка — отдельная накладная деталь, какой она и бывает в металле.
    """
    b.part = P.PART_SKIN
    y0, y1 = P.WINDSCREEN_Y
    pts = []
    for i in range(5):
        yy = L.lerp(y1, y0 + 0.02, i / 4.0)
        st = station_at(P.FUSELAGE_STATIONS, yy)
        pts.append((0.0, yy, st[5] + st[2]))
    # Сечение: v наружу от обшивки, поэтому стойка выступает, а не тонет.
    sec = [(-0.044, -0.014), (0.044, -0.014), (0.036, 0.018), (-0.036, 0.018)]
    b.beam(pts, sec, 1.0, P.MAT_BODY, False, True, (0.0, 0.0, 1.0))


def build_dorsal(b: L.MeshBuilder) -> None:
    """Форкиль: спина плавно переходит в переднюю кромку киля.

    Без него киль торчит из балки под прямым углом, и хвост читается как
    приклеенный — на референсе переход заметный.
    """
    b.part = P.PART_SKIN
    y0, y1 = P.DORSAL_Y_START, P.FIN_ROOT_Y_LE - 0.15
    n = 8
    rings = []
    for i in range(n):
        s = i / (n - 1)
        y = L.lerp(y0, y1, s)
        st = station_at(P.FUSELAGE_STATIONS, y)
        spine = st[5] + st[2]
        t_fin = max(0.0, min(1.0, (P.FIN_ROOT_Y_LE - y) / P.FIN_SWEEP)) if P.FIN_SWEEP else 0.0
        fin_z = P.FIN_BASE_Z + P.FIN_HEIGHT * t_fin
        top = L.lerp(spine, max(spine, fin_z), s ** 2.0)
        hx = L.lerp(0.012, P.DORSAL_THICK * 0.5, s)
        rings.append([
            (hx, y, spine - 0.14), (hx, y, top),
            (-hx, y, top), (-hx, y, spine - 0.14),
        ])
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)


# ==========================================================================
# Крыло
# ==========================================================================

Y_HINGE_WING = P.Y_WING_LE - P.WING_CUT * P.WING_ROOT_CHORD


def wing_section(frac: float, x_from: float, x_to: float) -> list[L.Vec3]:
    """Сечение крыла на доле полуразмаха frac, в диапазоне хорды [x_from, x_to]."""
    ch = P.wing_chord_at(frac)
    prof = L.naca4(*P.WING_AIRFOIL, P.SEG_AIRFOIL, x_from, x_to)
    return L.place_airfoil(
        prof,
        span_x=frac * P.WING_SEMI,
        chord=ch,
        le_y=P.Y_WING_LE,
        z=P.wing_z_at(frac),
        twist_deg=P.wing_twist_at(frac),
    )


def hinge_frac(frac: float) -> float:
    """Доля хорды, на которой линия навески пересекает данное сечение.

    Линия навески держится постоянной координаты y, а не постоянной доли хорды.
    Только так ось вращения руля параллельна X, и при отклонении руль не
    врезается в крыло на конце размаха.
    """
    return (P.Y_WING_LE - Y_HINGE_WING) / P.wing_chord_at(frac)


def build_wing(b: L.MeshBuilder, side: float) -> None:
    """Крыло участками по размаху.

    Там, где за линией навески стоит подвижный руль, участок обрезан по хорде;
    где руля нет — профиль полный. Стык двух таких участков и есть нервюра на
    краю выреза под закрылок: она нужна, и ради неё внутренние торцы соседних
    участков — приемлемая плата. Альтернатива (один лофт плюс накладные
    заполнители) дала бы совпадающие грани и мерцание на них.
    """
    b.part = P.PART_SKIN
    root = P.WING_ROOT_X / P.WING_SEMI
    segments = [
        (root, P.FLAP_FROM, False),
        (P.FLAP_FROM, P.FLAP_TO, True),
        (P.FLAP_TO, P.AILERON_FROM, False),
        (P.AILERON_FROM, P.AILERON_TO, True),
        (P.AILERON_TO, 1.0, False),
    ]
    for f0, f1, cut in segments:
        if f1 - f0 < 0.005:
            continue
        n = max(2, int(round((f1 - f0) * 8)) + 1)
        rings = []
        for i in range(n):
            f = L.lerp(f0, f1, i / (n - 1))
            sec = wing_section(f, 0.0, hinge_frac(f) if cut else 1.0)
            rings.append([(side * x, y, z) for x, y, z in sec])

        # Крайний участок продолжается обтекателем законцовки.
        if f1 >= 0.999:
            tip = rings[-1]
            cy = sum(v[1] for v in tip) / len(tip)
            cz = sum(v[2] for v in tip) / len(tip)
            for s in (0.45, 0.80, 1.0):
                k = math.sqrt(max(0.0, 1.0 - s * s)) * 0.96 + 0.04
                rings.append([
                    (side * (P.WING_SEMI + P.TIP_FAIRING_LEN * s),
                     cy + (v[1] - cy) * k,
                     cz + (v[2] - cz) * k)
                    for v in tip
                ])

        b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)


def build_control_surface(
    b: L.MeshBuilder, side: float, f0: float, f1: float
) -> tuple[list[L.Vec3], L.Vec3]:
    """Руль на крыле: от линии навески до задней кромки. Возвращает пивот."""
    b.part = P.PART_SKIN
    rings = []
    for f in (f0, f1):
        sec = wing_section(f, hinge_frac(f), 1.0)
        rings.append([(side * x, y, z) for x, y, z in sec])
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)
    # Пивот — на линии навески, по середине толщины, у внутреннего края.
    zs = [v[2] for v in rings[0]]
    pivot = (side * f0 * P.WING_SEMI, Y_HINGE_WING, (min(zs) + max(zs)) * 0.5)
    return rings, pivot


# ==========================================================================
# Оперение
# ==========================================================================

Y_HINGE_FIN = P.FIN_ROOT_Y_LE - P.FIN_CUT * P.FIN_ROOT_CHORD
Y_HINGE_STAB = P.STAB_Y_LE - P.STAB_CUT * P.STAB_ROOT_CHORD


def fin_geom(t: float) -> tuple[float, float, float]:
    """Хорда, координата передней кромки и высота на доле высоты киля t."""
    z = P.FIN_BASE_Z + P.FIN_HEIGHT * t
    chord = L.lerp(P.FIN_ROOT_CHORD, P.FIN_TIP_CHORD, t)
    le_y = P.FIN_ROOT_Y_LE - P.FIN_SWEEP * t
    return chord, le_y, z


def build_fin(b: L.MeshBuilder) -> None:
    b.part = P.PART_SKIN
    steps = [i / 5.0 for i in range(6)]
    rings = []
    for t in steps:
        chord, le_y, z = fin_geom(t)
        cut = (P.FIN_ROOT_Y_LE - P.FIN_SWEEP * t - Y_HINGE_FIN) / chord
        cut = max(0.35, min(0.92, cut))
        prof = L.naca4(0.0, 0.4, P.FIN_THICKNESS, P.SEG_AIRFOIL, 0.0, cut)
        rings.append(L.place_fin(prof, z, chord, le_y))
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)


def build_rudder(b: L.MeshBuilder) -> L.Vec3:
    b.part = P.PART_SKIN
    steps = [i / 4.0 for i in range(5)]
    rings = []
    for t in steps:
        chord, le_y, z = fin_geom(t)
        cut = (P.FIN_ROOT_Y_LE - P.FIN_SWEEP * t - Y_HINGE_FIN) / chord
        cut = max(0.35, min(0.92, cut))
        prof = L.naca4(0.0, 0.4, P.FIN_THICKNESS, P.SEG_AIRFOIL, cut, 1.0)
        rings.append(L.place_fin(prof, z, chord, le_y))
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)
    return (0.0, Y_HINGE_FIN, fin_geom(0.0)[2])


def stab_chord_at(frac: float) -> float:
    return L.lerp(P.STAB_ROOT_CHORD, P.STAB_TIP_CHORD, frac)


def stab_section(frac: float, x_from: float, x_to: float, side: float) -> list[L.Vec3]:
    ch = stab_chord_at(frac)
    prof = L.naca4(0.0, 0.4, P.STAB_THICKNESS, P.SEG_AIRFOIL, x_from, x_to)
    sec = L.place_airfoil(prof, frac * P.STAB_SEMI, ch, P.STAB_Y_LE, P.STAB_Z, 0.0)
    return [(side * x, y, z) for x, y, z in sec]


def stab_hinge_frac(frac: float) -> float:
    return (P.STAB_Y_LE - Y_HINGE_STAB) / stab_chord_at(frac)


def build_stab(b: L.MeshBuilder, side: float) -> None:
    b.part = P.PART_SKIN
    root = 0.12
    steps = [root + (1.0 - root) * i / 4.0 for i in range(5)]
    rings = [stab_section(f, 0.0, stab_hinge_frac(f), side) for f in steps]
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)


def build_elevator(b: L.MeshBuilder, side: float) -> L.Vec3:
    b.part = P.PART_SKIN
    f0, f1 = 0.14, 0.97
    rings = [stab_section(f, stab_hinge_frac(f), 1.0, side) for f in (f0, f1)]
    b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)
    return (side * f0 * P.STAB_SEMI, Y_HINGE_STAB, P.STAB_Z)


# ==========================================================================
# Подкосы, шасси, мелочь
# ==========================================================================

def build_struts(b: L.MeshBuilder) -> None:
    """Подкосы крыла и стабилизатора обтекаемым сечением.

    up_hint задаётся знаком борта: рамка протяжки строится как cross(ход, up),
    поэтому на левом борту ось сечения разворачивается, и капля встала бы
    носом назад. Смена знака up возвращает нос вперёд на обоих бортах.
    """
    b.part = P.PART_METAL
    f = P.STRUT_WING_FRAC
    wz = P.wing_z_at(f) + 0.02
    wx = f * P.WING_SEMI
    sec = L.teardrop(P.STRUT_CHORD, P.STRUT_THICK, 12)
    jury = L.teardrop(P.JURY_CHORD, P.JURY_THICK, 8)
    for side in (-1.0, 1.0):
        up = (0.0, 0.0, side)
        for y_fus, y_wing, k in (
            (0.74, P.Y_WING_LE - 0.26, 1.0),
            (0.08, P.Y_WING_LE - 1.02, 0.88),
        ):
            a = (side * P.STRUT_FUS_X, y_fus, P.STRUT_FUS_Z)
            c = (side * wx, y_wing, wz)
            mid = tuple(L.lerp(a[k2], c[k2], 0.5) for k2 in range(3))
            b.beam([a, mid, c], sec, [k * 1.08, k, k * 0.86], P.MAT_BODY, True, True, up)
            # Кронштейны на обоих концах: подкос не приклеен к обшивке встык.
            b.box(a, (0.10, 0.17, 0.10), P.MAT_BODY, False)
            b.box(c, (0.09, 0.15, 0.08), P.MAT_BODY, False)
        # Распорка между подкосами у крыла — она не даёт им «плавать» в силуэте.
        j0 = (side * wx * 0.72, P.Y_WING_LE - 0.36, L.lerp(P.STRUT_FUS_Z, wz, 0.74))
        j1 = (side * wx * 0.72, P.Y_WING_LE - 0.90, L.lerp(P.STRUT_FUS_Z, wz, 0.74))
        b.beam([j0, j1], jury, 1.0, P.MAT_BODY, True, True, up)

    # Подкосы стабилизатора: от низа балки наружу и вверх, к консоли.
    # Крепление вынесено вперёд по балке — короткий подкос почти у самой
    # консоли в силуэте не читался совсем.
    ssec = L.teardrop(P.STAB_STRUT_CHORD, P.STAB_STRUT_THICK, 8)
    for side in (-1.0, 1.0):
        a = (side * 0.09, -4.48, 1.36)
        c = (side * P.STAB_SEMI * P.STAB_STRUT_FRAC, P.STAB_Y_LE - 0.34, P.STAB_Z - 0.04)
        b.beam([a, c], ssec, [1.0, 0.8], P.MAT_BODY, True, True, (0.0, 0.0, side))


def wheel_profile(radius: float, width: float) -> list[L.Vec2]:
    """Замкнутое сечение покрышки: борт, протектор, обратный борт."""
    hw = width * 0.5
    r_in = radius * P.HUB_R_FRAC
    # Плечо набрано тремя точками вместо одной: тундровая покрышка круглая в
    # сечении, а на одном изломе она гранилась и читалась шестерёнкой.
    return [
        (r_in, -hw * 0.42),
        (radius * 0.70, -hw * 0.96),
        (radius * 0.88, -hw * 0.90),
        (radius * 0.975, -hw * 0.66),
        (radius, -hw * 0.28),
        (radius, hw * 0.28),
        (radius * 0.975, hw * 0.66),
        (radius * 0.88, hw * 0.90),
        (radius * 0.70, hw * 0.96),
        (r_in, hw * 0.42),
    ]


def build_wheel(b: L.MeshBuilder, radius: float, width: float,
                segments: int | None = None) -> None:
    """Колесо в локальных координатах: ось вдоль X, центр в нуле."""
    seg = segments or P.SEG_WHEEL
    b.part = P.PART_RUBBER
    b.revolve(
        wheel_profile(radius, width), seg, axis="X",
        mat=P.MAT_BODY, smooth=True, closed_profile=True,
    )
    # Диск: утопленная тарелка с выступающим колпаком по центру. Прежняя
    # «линза» читалась пузырём — на референсе видны концентрические кольца.
    b.part = P.PART_METAL
    r_in = radius * P.HUB_R_FRAC
    r_cap = radius * P.HUB_CAP_FRAC
    hub = [
        (0.0, -width * 0.26),
        (r_cap * 0.85, -width * 0.26),
        (r_cap, -width * 0.20),
        (r_cap * 1.06, -width * 0.15),
        (r_cap * 1.32, -width * 0.10),
        (r_cap * 1.38, -width * 0.16),
        (r_in * 0.80, -width * 0.13),
        (r_in * 0.86, -width * 0.20),
        (r_in, -width * 0.24),
        (r_in, width * 0.24),
        (r_in * 0.86, width * 0.20),
        (r_in * 0.80, width * 0.13),
        (r_cap * 1.38, width * 0.16),
        (r_cap * 1.32, width * 0.10),
        (r_cap * 1.06, width * 0.15),
        (r_cap, width * 0.20),
        (r_cap * 0.85, width * 0.26),
        (0.0, width * 0.26),
    ]
    b.revolve(hub, seg, axis="X", mat=P.MAT_BODY, smooth=True)


def build_main_leg(b: L.MeshBuilder, side: float) -> L.Vec3:
    """Основная стойка: цилиндр, шток, манжета, ножницы, ось и задний подкос.

    Уступ между цилиндром и штоком — главное, что отличает амортизатор от
    палки: без него стойка читалась чёрной трубой с колесом на конце.
    """
    b.part = P.PART_METAL
    top = (side * P.GEAR_ATTACH_X, P.MAIN_WHEEL_Y, P.GEAR_ATTACH_Z)
    axle = (side * P.MAIN_TRACK_X, P.MAIN_WHEEL_Y, P.MAIN_WHEEL_R)

    def at(t: float) -> L.Vec3:
        return tuple(L.lerp(top[k], axle[k], t) for k in range(3))

    f = P.GEAR_ROD_FROM
    b.tube([top, at(f)], [P.GEAR_LEG_RADIUS * 1.15, P.GEAR_LEG_RADIUS],
           P.SEG_TUBE, P.MAT_BODY, True)
    b.tube([at(f), axle], [P.GEAR_ROD_RADIUS, P.GEAR_ROD_RADIUS * 0.94],
           P.SEG_TUBE, P.MAT_BODY, True)
    # Манжета на переходе — видимый буртик сальника.
    b.tube([at(f - 0.05), at(f + 0.02)], P.GEAR_LEG_RADIUS * 1.22,
           P.SEG_TUBE, P.MAT_BODY, True)
    # Кронштейн крепления к фюзеляжу.
    b.box((top[0], top[1], top[2] + 0.02), (0.13, 0.20, 0.12), P.MAT_BODY, False)

    # Ножницы: два коротких звена впереди штока.
    k0, k1 = at(f + 0.04), at(0.92)
    knuckle = (L.lerp(k0[0], k1[0], 0.5), k0[1] + 0.115, L.lerp(k0[2], k1[2], 0.5))
    b.tube([k0, knuckle], 0.019, 6, P.MAT_BODY, True)
    b.tube([knuckle, k1], 0.019, 6, P.MAT_BODY, True)

    # Ось колеса наружу, чтобы колесо было надето, а не примагничено.
    b.tube([(axle[0] - side * 0.06, axle[1], axle[2]),
            (axle[0] + side * (P.MAIN_WHEEL_W * 0.5 + 0.03), axle[1], axle[2])],
           P.GEAR_AXLE_RADIUS, 10, P.MAT_BODY, True)

    # Задний подкос обтекаемого сечения.
    drag_top = (side * (P.GEAR_ATTACH_X * 0.78), P.MAIN_WHEEL_Y - 0.66, P.GEAR_ATTACH_Z - 0.05)
    b.beam([drag_top, at(0.90)],
           L.teardrop(P.GEAR_BRACE_CHORD, P.GEAR_BRACE_THICK, 8),
           [1.0, 0.85], P.MAT_BODY, True, True, (0.0, 0.0, side))
    return top




def build_tail_leg(b: L.MeshBuilder) -> L.Vec3:
    b.part = P.PART_METAL
    top = (0.0, P.TAIL_WHEEL_Y + 0.22, P.TAIL_LEG_TOP_Z)
    axle = (0.0, P.TAIL_WHEEL_Y, P.TAIL_WHEEL_R)
    b.tube([top, axle], [P.TAIL_LEG_RADIUS * 1.2, P.TAIL_LEG_RADIUS * 0.85],
           P.SEG_TUBE, P.MAT_BODY, True)
    # Вилка: две щеки по бокам колеса и ось насквозь.
    for sx in (-1.0, 1.0):
        b.tube([(sx * (P.TAIL_WHEEL_W * 0.5 + 0.022), P.TAIL_WHEEL_Y + 0.09, P.TAIL_WHEEL_R + 0.10),
                (sx * (P.TAIL_WHEEL_W * 0.5 + 0.022), P.TAIL_WHEEL_Y, P.TAIL_WHEEL_R)],
               0.020, 6, P.MAT_BODY, True)
    b.tube([(-P.TAIL_WHEEL_W * 0.5 - 0.04, P.TAIL_WHEEL_Y, P.TAIL_WHEEL_R),
            (P.TAIL_WHEEL_W * 0.5 + 0.04, P.TAIL_WHEEL_Y, P.TAIL_WHEEL_R)],
           0.018, 8, P.MAT_BODY, True)
    return top


def spinner_profile() -> list[L.Vec2]:
    """Сечение кока: слегка выпуклый конус с кольцевыми стыками секций.

    Стык задаётся уступом радиуса: каждая следующая к вершине секция немного
    уже предыдущей. Плавный конус такого стыка не даёт, а на референсе кольца
    хорошо видны и именно они читаются как «кок», а не «яйцо».
    """
    R, sl = P.SPINNER_RADIUS, P.SPINNER_LEN
    n = 18
    fs = [i / n for i in range(n + 1)]
    for rib in P.SPINNER_RIBS:
        fs += [rib - 1e-3, rib + 1e-3]
    fs = sorted({min(max(f, 0.0), 1.0) for f in fs})

    def rad(f: float) -> float:
        # Косинусный оживал, а не степенной конус: на врезке «ENGINE/PROPELLER»
        # кок — вытянутая пуля с округлым носом, а конус давал остриё.
        r = R * math.cos(min(f, 1.0) * math.pi * 0.5) ** 0.45
        for rib in P.SPINNER_RIBS:
            if f > rib:
                r -= P.SPINNER_RIB_STEP
        return max(r, 0.0)

    prof = [(0.0, 0.0), (R * 0.99, 0.0)]
    prof += [(rad(f), sl * f) for f in fs if 1e-9 < f <= 0.955]
    # Носовой колпачок: последние 4.5% длины сводим дугой, а не в точку.
    tip_r = rad(0.955)
    for t in (0.35, 0.7, 1.0):
        prof.append((tip_r * math.cos(t * math.pi * 0.5), sl * (0.955 + 0.045 * t)))
    return prof


def blade_chord(t: float) -> float:
    """Плановая форма лопасти по доле размаха: комель узкий, максимум на 0.7."""
    if t < P.BLADE_MAX_AT:
        ch = L.lerp(P.BLADE_ROOT_CHORD, P.BLADE_MAX_CHORD,
                    L.smoothstep(t / P.BLADE_MAX_AT))
    else:
        u = (t - P.BLADE_MAX_AT) / (1.0 - P.BLADE_MAX_AT)
        ch = L.lerp(P.BLADE_MAX_CHORD, P.BLADE_TIP_CHORD, L.smoothstep(u))
    # Последние 7% радиуса — скругление по дуге: обрубленный конец в силуэте
    # читается как сломанная лопасть.
    if t > 0.93:
        ch *= math.sqrt(max(0.0, 1.0 - ((t - 0.93) / 0.07) ** 2))
    return max(ch, 0.014)


def build_propeller(b: L.MeshBuilder) -> None:
    """Кок и лопасти в локальных координатах: ось вращения — Y, центр в нуле."""
    b.part = P.PART_SPINNER
    b.revolve(spinner_profile(), P.SEG_SPINNER, axis="Y", mat=P.MAT_BODY, smooth=True)

    b.part = P.PART_BLADE
    # Комель заходит внутрь кока: лопасть обязана выходить из кока, а не
    # начинаться на его поверхности.
    r_root = P.SPINNER_RADIUS * 0.66
    r_tip = P.PROP_DIAMETER * 0.5
    steps = 14
    for k in range(P.PROP_BLADES):
        roll = 360.0 * k / P.PROP_BLADES
        rings = []
        for s in range(steps + 1):
            t = s / steps
            r = L.lerp(r_root, r_tip, t)
            ch = blade_chord(t)
            th = L.lerp(P.BLADE_THICKNESS, 0.055, L.smoothstep(t))
            # place_airfoil кладёт хорду вдоль оси Y, то есть вдоль оси вращения.
            # Угол установки же отсчитывается от плоскости диска, поэтому нужен
            # разворот на 90°: без него винт стоит во флюгерном положении и
            # спереди выглядит набором тонких спиц.
            pitch = L.lerp(P.BLADE_PITCH_ROOT, P.BLADE_PITCH_TIP, t)
            tw = 90.0 - pitch
            prof2 = L.naca4(0.03, 0.5, th, 18, 0.0, 1.0)
            sec = L.place_airfoil(prof2, r, ch, 0.10, 0.0, twist_deg=tw, pivot=0.42)
            rings.append(L.rotate_ring(sec, "Y", roll))
        b.loft(rings, P.MAT_BODY, True, True, cap_start=True, cap_end=True)


def build_cargo_bay(b: L.MeshBuilder) -> None:
    """Пол, потолок и переборки сквозного отсека.

    Коробка заметно уже створки: их внутренняя поверхность лежит примерно на
    x = 0.54, и совпадающие плоскости дали бы мерцание на всём борту.
    """
    b.part = P.PART_INTERIOR
    y0, y1 = P.CARGO_Y
    z0, z1 = P.CARGO_FLOOR_Z, P.CARGO_CEIL_Z
    hw = P.CARGO_HALF_W
    b.box((0.0, (y0 + y1) * 0.5, z0 - 0.03), (hw * 2, y1 - y0, 0.06), P.MAT_BODY, False)
    b.box((0.0, (y0 + y1) * 0.5, z1 + 0.03), (hw * 2, y1 - y0, 0.06), P.MAT_BODY, False)
    for y in (y0 - 0.04, y1 + 0.04):
        b.box((0.0, y, (z0 + z1) * 0.5), (hw * 2, 0.08, z1 - z0), P.MAT_BODY, False)


def build_door_panel(b: L.MeshBuilder, grid: list[list[L.Vec3]]) -> L.Vec3:
    """Створка одной оболочкой по сетке проёма.

    Раньше каждая ячейка становилась отдельной плиткой со своим ободом —
    соседние плитки делили совпадающие боковые грани, и весь борт рябил от
    мерцания. Одна оболочка на всю створку эту причину убирает целиком.
    """
    b.part = P.PART_SKIN
    rows, cols = len(grid), len(grid[0])
    th = P.CARGO_DOOR_THICK
    sign = 1.0 if sum(p[0] for r in grid for p in r) > 0 else -1.0

    outer = [[b.add_verts([p])[0] for p in row] for row in grid]
    inner = [[b.add_verts([(p[0] - sign * th, p[1], p[2])])[0] for p in row] for row in grid]

    for r in range(rows - 1):
        for c in range(cols - 1):
            b.add_face([outer[r][c], outer[r][c + 1], outer[r + 1][c + 1], outer[r + 1][c]],
                       P.MAT_BODY, True)
            b.add_face([inner[r][c], inner[r + 1][c], inner[r + 1][c + 1], inner[r][c + 1]],
                       P.MAT_BODY, True)

    # Обод по всему периметру — он и даёт створке толщину.
    for c in range(cols - 1):
        b.add_face([outer[0][c], inner[0][c], inner[0][c + 1], outer[0][c + 1]], P.MAT_BODY, False)
        b.add_face([outer[rows - 1][c + 1], inner[rows - 1][c + 1],
                    inner[rows - 1][c], outer[rows - 1][c]], P.MAT_BODY, False)
    for r in range(rows - 1):
        b.add_face([outer[r][0], outer[r + 1][0], inner[r + 1][0], inner[r][0]], P.MAT_BODY, False)
        b.add_face([outer[r][cols - 1], inner[r][cols - 1],
                    inner[r + 1][cols - 1], outer[r + 1][cols - 1]], P.MAT_BODY, False)

    xs = [abs(p[0]) for r in grid for p in r]
    ys = [p[1] for r in grid for p in r]
    zs = [p[2] for r in grid for p in r]
    # Пивот на ЗАДНЕЙ вертикальной кромке: проём стоит сразу за задней кромкой
    # крыла, и створка с передней навеской распахивалась бы под центроплан.
    return (sign * max(xs), min(ys), (min(zs) + max(zs)) * 0.5)


def build_cockpit(b: L.MeshBuilder) -> None:
    """Салон: пол, кресла, приборная панель, штурвалы, задняя переборка.

    Всё в коробках и трубах — деталь видно только сквозь стекло и только
    силуэтом, и наращивать здесь сетку смысла нет. Зато пустая кабина за
    большими окнами выдаёт макет мгновенно, поэтому обойтись совсем без салона
    нельзя.
    """
    b.part = P.PART_CABIN
    hw = P.CABIN_HALF_W
    fz = P.CABIN_FLOOR_Z
    # Пол начинается под приборной панелью, а не у перегородки: там обшивка
    # уже сузилась до 0.55 и половина пола вылезла бы наружу.
    y_front, y_rear = P.PANEL_Y + 0.04, P.CABIN_REAR_Y

    # Пол и задняя переборка.
    b.box((0.0, (y_front + y_rear) * 0.5, fz - 0.03), (hw * 2, y_front - y_rear, 0.06),
          P.MAT_BODY, False)
    b.box((0.0, y_rear, fz + 0.58), (hw * 2, 0.06, 1.16), P.MAT_BODY, False)

    # Приборная панель со скосом назад и противобликовый козырёк.
    z0, z1 = P.PANEL_Z
    b.box((0.0, P.PANEL_Y, (z0 + z1) * 0.5), (hw * 1.82, 0.10, z1 - z0), P.MAT_BODY, False)
    b.box((0.0, P.PANEL_Y - P.GLARE_LEN * 0.5, z1 + 0.03),
          (hw * 1.9, P.GLARE_LEN, 0.05), P.MAT_BODY, False)
    # Центральная консоль между креслами.
    b.box((0.0, P.PANEL_Y - 0.34, fz + 0.30), (0.20, 0.62, 0.60), P.MAT_BODY, False)

    for row_i, sy in enumerate(P.SEAT_ROWS):
        for sx in (-1.0, 1.0):
            x = sx * P.SEAT_X
            w = P.SEAT_W
            # Подушка, спинка с наклоном и подголовник.
            b.box((x, sy, P.SEAT_PAN_Z), (w, 0.48, 0.12), P.MAT_BODY, False)
            b.box((x, sy - 0.22, (P.SEAT_PAN_Z + P.SEAT_BACK_TOP) * 0.5 + 0.02),
                  (w, 0.13, P.SEAT_BACK_TOP - P.SEAT_PAN_Z), P.MAT_BODY, False)
            b.box((x, sy - 0.24, P.SEAT_BACK_TOP + 0.06), (w * 0.62, 0.14, 0.16),
                  P.MAT_BODY, False)
            # Ножки — кресло не должно висеть над полом.
            for dy in (-0.16, 0.16):
                b.box((x, sy + dy, (fz + P.SEAT_PAN_Z) * 0.5 - 0.03),
                      (w * 0.78, 0.05, P.SEAT_PAN_Z - fz - 0.06), P.MAT_BODY, False)
        if row_i == 0:
            # Штурвалы: колонка от панели и Т-образная рукоять.
            for sx in (-1.0, 1.0):
                x = sx * P.SEAT_X
                b.tube([(x, P.PANEL_Y - 0.06, P.YOKE_Z - 0.10),
                        (x, sy - 0.26, P.YOKE_Z)], 0.030, 8, P.MAT_BODY, True)
                b.box((x, sy - 0.27, P.YOKE_Z), (0.30, 0.05, 0.05), P.MAT_BODY, False)
                b.box((x, sy - 0.27, P.YOKE_Z + 0.07), (0.05, 0.05, 0.14),
                      P.MAT_BODY, False)


def build_crates(b: L.MeshBuilder) -> None:
    b.part = P.PART_CARGO
    for x, dy, dz, w, d, h, rot in P.CRATES:
        y = P.Y_CARGO_CENTRE + dy
        z = P.CARGO_FLOOR_Z + dz
        b.box((x, y, z + h * 0.5), (w, d, h), P.MAT_BODY, False, rot_z_deg=rot)
        # Крышка чуть шире корпуса — ящик читается как ящик, а не как брусок.
        b.box((x, y, z + h + 0.018), (w * 1.06, d * 1.06, 0.036), P.MAT_BODY, False, rot_z_deg=rot)


def build_antennas(b: L.MeshBuilder) -> None:
    b.part = P.PART_METAL
    for x, y, z, ln, tilt, r in P.ANTENNAS:
        dy = -math.sin(math.radians(tilt)) * ln
        b.tube([(x, y, z), (x, y + dy, z + math.cos(math.radians(tilt)) * ln)],
               [r, r * 0.35], 6, P.MAT_BODY, True)
    y, z, ln, h = P.BLADE_ANTENNA
    b.box((0.0, y, z - h * 0.5), (0.022, ln, h), P.MAT_BODY, False)


def build_lights(b: L.MeshBuilder) -> None:
    """Пять линз навигационных огней: крылья, стабилизатор, киль."""
    b.part = P.PART_LIGHT
    r = P.LIGHT_LENS_R
    spots = []
    # Центр законцовочного сечения берём из той же функции, что строит крыло:
    # иначе при правке профиля или крутки линза уедет внутрь обтекателя.
    tip_sec = wing_section(1.0, 0.0, 1.0)
    tip_cy = sum(v[1] for v in tip_sec) / len(tip_sec)
    tip_cz = sum(v[2] for v in tip_sec) / len(tip_sec)
    for side in (-1.0, 1.0):
        spots.append((side * (P.WING_SEMI + P.TIP_FAIRING_LEN * 0.62), tip_cy, tip_cz))
        spots.append((side * P.STAB_SEMI, P.STAB_Y_LE - P.STAB_TIP_CHORD * 0.5, P.STAB_Z))
    chord, le_y, z = fin_geom(1.0)
    spots.append((0.0, le_y - chord * 0.5, z + 0.02))

    for cx, cy, cz in spots:
        prof = [(0.0, -r * 0.8), (r * 0.7, -r * 0.4), (r, 0.0), (r * 0.7, r * 0.4), (0.0, r * 0.8)]
        b.revolve(prof, P.LIGHT_LENS_SEG, axis="Z", origin=(cx, cy, cz),
                  mat=P.MAT_LIGHT, smooth=True)


def build_hinges(b: L.MeshBuilder) -> None:
    """Кронштейны навески на задней кромке крыла.

    На референсе вдоль кромки идёт ряд круглых узлов — именно они выдают, что
    закрылок отдельная деталь. Картой нормалей такого не нарисовать: узел
    выступает за контур, и в силуэте его видно.
    """
    b.part = P.PART_METAL
    span = P.WING_SEMI
    for side in (-1.0, 1.0):
        for f0, f1 in ((P.FLAP_FROM, P.FLAP_TO), (P.AILERON_FROM, P.AILERON_TO)):
            for t in (0.14, 0.5, 0.86):
                fr = L.lerp(f0, f1, t)
                x = side * fr * span
                # Низ профиля на линии навески: узел должен выходить из-под
                # крыла, а не висеть рядом с ним.
                sec = wing_section(fr, 0.0, 1.0)
                z_low = min(v[2] for v in sec if abs(v[1] - Y_HINGE_WING) < 0.12) \
                    if any(abs(v[1] - Y_HINGE_WING) < 0.12 for v in sec) \
                    else P.wing_z_at(fr) - 0.06
                b.tube([(x, Y_HINGE_WING + 0.07, z_low + 0.01),
                        (x, Y_HINGE_WING - 0.09, z_low - 0.030)],
                       [0.026, 0.019], 8, P.MAT_BODY, True)


def build_step(b: L.MeshBuilder) -> None:
    """Подножка под грузовым проёмом и поручень вдоль низа борта.

    Поручень на референсе тянется почти на всю кабину и заметно оживляет
    пустой низ борта — без него между шасси и проёмом голая плоскость.
    """
    b.part = P.PART_METAL
    for side in (-1.0, 1.0):
        y = P.Y_CARGO_CENTRE
        b.box((side * 0.76, y, 0.58), (0.36, 0.13, 0.030), P.MAT_BODY, False)
        b.box((side * 0.76, y - 0.055, 0.60), (0.36, 0.022, 0.050), P.MAT_BODY, False)
        for dy in (-0.14, 0.14):
            b.tube([(side * 0.48, y + dy, P.FUS_FLOOR_Z + 0.06),
                    (side * 0.76, y + dy, 0.60)],
                   0.017, 6, P.MAT_BODY, True)
        # Поручень: труба вдоль борта на кронштейнах. Идёт по обводу — на
        # сужающейся к хвосту балке труба постоянного отступа отрывалась бы
        # от борта и висела в воздухе.
        def rail_pt(ry: float, out: float) -> L.Vec3:
            st = P.station_at(ry)
            return (side * (st[1] + out), ry, st[5] - st[3] + 0.11)

        rail_ys = [1.62, 1.10, 0.40, -0.50, -1.40, -2.20, -2.80]
        b.tube([rail_pt(ry, 0.055) for ry in rail_ys], 0.016, 6, P.MAT_BODY, True)
        for ry in (1.42, 0.10, -1.40, -2.70):
            b.tube([rail_pt(ry, -0.10), rail_pt(ry, 0.055)],
                   0.013, 5, P.MAT_BODY, True)


# ==========================================================================
# Сборка сцены
# ==========================================================================

def main() -> None:
    out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "out/geo.blend"
    reset_scene()
    mats = make_materials()

    root = bpy.data.objects.new("BushPlane", None)
    root.empty_display_size = 1.2
    bpy.context.collection.objects.link(root)

    created: list = []

    def attach(obj):
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
        created.append(obj)
        return obj

    # --- неподвижный корпус ------------------------------------------------
    body = L.MeshBuilder()
    patches, stations = build_fuselage(body)
    front_ring = build_nose(body)
    build_cowl(body, front_ring)
    build_intakes(body)
    build_windscreen_post(body)
    build_exhaust(body)
    build_chin_scoop(body)
    for side in (-1.0, 1.0):
        build_wing(body, side)
        build_stab(body, side)
    build_fin(body)
    build_dorsal(body)
    build_struts(body)
    build_cargo_bay(body)
    build_cockpit(body)
    build_antennas(body)
    build_lights(body)
    build_step(body)
    build_hinges(body)
    for side in (-1.0, 1.0):
        build_main_leg(body, side)
    build_tail_leg(body)
    print(f"  Body: {body.stats()}")
    attach(body.to_object("Body", mats))

    # --- винт ---------------------------------------------------------------
    pb = L.MeshBuilder()
    build_propeller(pb)
    prop = pb.to_object("Propeller", mats, origin=(0.0, 0.0, 0.0))
    prop.location = (0.0, P.Y_SPINNER_BASE, P.PROP_HUB_Z)
    attach(prop)

    # --- рули крыла ---------------------------------------------------------
    for side, tag in ((1.0, "R"), (-1.0, "L")):
        for name, (f0, f1) in (
            ("Flap", (P.FLAP_FROM, P.FLAP_TO)),
            ("Aileron", (P.AILERON_FROM, P.AILERON_TO)),
        ):
            cb = L.MeshBuilder()
            _, pivot = build_control_surface(cb, side, f0, f1)
            attach(cb.to_object(f"{name}_{tag}", mats, origin=pivot)).location = pivot

    # --- оперение -----------------------------------------------------------
    rb = L.MeshBuilder()
    rpiv = build_rudder(rb)
    attach(rb.to_object("Rudder", mats, origin=rpiv)).location = rpiv

    for side, tag in ((1.0, "R"), (-1.0, "L")):
        eb = L.MeshBuilder()
        epiv = build_elevator(eb, side)
        attach(eb.to_object(f"Elevator_{tag}", mats, origin=epiv)).location = epiv

    # --- колёса -------------------------------------------------------------
    for side, tag in ((1.0, "R"), (-1.0, "L")):
        wb = L.MeshBuilder()
        build_wheel(wb, P.MAIN_WHEEL_R, P.MAIN_WHEEL_W)
        w = wb.to_object(f"Wheel_{tag}", mats)
        w.location = (side * P.MAIN_TRACK_X, P.MAIN_WHEEL_Y, P.MAIN_WHEEL_R)
        attach(w)

    tb = L.MeshBuilder()
    build_wheel(tb, P.TAIL_WHEEL_R, P.TAIL_WHEEL_W, P.SEG_WHEEL_SMALL)
    tw = tb.to_object("Wheel_Tail", mats)
    tw.location = (0.0, P.TAIL_WHEEL_Y, P.TAIL_WHEEL_R)
    attach(tw)

    # --- створки ------------------------------------------------------------
    for tag in ("R", "L"):
        if not patches[tag]:
            continue
        db = L.MeshBuilder()
        piv = build_door_panel(db, patches[tag])
        attach(db.to_object(f"CargoDoor_{tag}", mats, origin=piv)).location = piv

    # --- груз ---------------------------------------------------------------
    cb = L.MeshBuilder()
    build_crates(cb)
    attach(cb.to_object("Cargo_Crates", mats, origin=(0.0, P.Y_CARGO_CENTRE, P.CARGO_FLOOR_Z))).location = (
        0.0, P.Y_CARGO_CENTRE, P.CARGO_FLOOR_Z
    )

    # --- центр масс ---------------------------------------------------------
    com = bpy.data.objects.new("CenterOfMass", None)
    com.empty_display_type = "SPHERE"
    com.empty_display_size = 0.18
    com.location = (0.0, 0.05, 1.28)
    bpy.context.collection.objects.link(com)
    attach(com)

    # --- итог ---------------------------------------------------------------
    tris = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"\n{P.summary()}")
    print(f"объектов: {len(created)}, треугольников: {tris}")

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print(f"сохранено: {out}")


if __name__ == "__main__":
    main()
