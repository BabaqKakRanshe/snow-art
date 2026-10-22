"""Геометрический фундамент генератора самолёта.

Здесь нет ни одного вызова bpy.ops: всё строится как чистые списки вершин и
граней, и только `MeshBuilder.to_object` касается bpy.data. Так генератор
остаётся предсказуемым — операторы зависят от контекста, выделения и активного
объекта, а в headless-запуске это главный источник плавающих ошибок.

Blender 5.2 / Python 3.13.

Система координат (Blender): +X — правое крыло, +Y — нос, +Z — вверх.
После FBX-конверсии в Unity это даёт нос → +Z, верх → +Y.
"""

from __future__ import annotations

import math

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


# --------------------------------------------------------------------------
# Профили сечений
# --------------------------------------------------------------------------

def superellipse(
    half_w: float,
    half_h_top: float,
    half_h_bot: float,
    exponent: float,
    n: int,
) -> list[Vec2]:
    """Сечение фюзеляжа: суперэллипс с разной высотой верха и низа.

    Параметризация идёт по углу theta, а не по длине дуги. Это принципиально:
    при лофте между сечениями разных пропорций одинаковый theta гарантирует,
    что «угол» одного сечения соединится с «углом» соседнего, и обшивку не
    перекрутит. Ради этого мы и отказались от честного rounded-rect.

    exponent=2 даёт эллипс, exponent→бесконечность — прямоугольник.
    Плоские борта референса живут около 3.5–5.
    """
    pts: list[Vec2] = []
    p = 2.0 / exponent
    for i in range(n):
        t = 2.0 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = half_w * math.copysign(abs(c) ** p, c)
        h = half_h_top if s >= 0.0 else half_h_bot
        z = h * math.copysign(abs(s) ** p, s)
        pts.append((x, z))
    return pts


def naca4(
    camber: float,
    camber_pos: float,
    thickness: float,
    n: int,
    x_from: float = 0.0,
    x_to: float = 1.0,
    close_te: bool = True,
) -> list[Vec2]:
    """Профиль NACA 4-значной серии как замкнутый контур (x/c, y/c).

    camber      — максимальная вогнутость m (у 2412 это 0.02)
    camber_pos  — её положение p (у 2412 — 0.4)
    thickness   — относительная толщина t (у 2412 — 0.12)

    x_from/x_to режут профиль по хорде: так из одного профиля получается и
    основная часть крыла, и отдельный элерон, причём линия разреза у обоих
    совпадает вершина в вершину.

    Точки идут по верхней поверхности от x_from к x_to, затем по нижней
    обратно — замкнутый контур против часовой стрелки в плоскости (x, y).
    """
    m, p, t = camber, camber_pos, thickness

    def camber_line(x: float) -> tuple[float, float]:
        """Возвращает (yc, dyc/dx)."""
        if m == 0.0:
            return 0.0, 0.0
        if x < p:
            yc = m / (p * p) * (2.0 * p * x - x * x)
            dy = 2.0 * m / (p * p) * (p - x)
        else:
            q = 1.0 - p
            yc = m / (q * q) * ((1.0 - 2.0 * p) + 2.0 * p * x - x * x)
            dy = 2.0 * m / (q * q) * (p - x)
        return yc, dy

    def half_thickness(x: float) -> float:
        # Последний коэффициент -0.1036 вместо канонического -0.1015 смыкает
        # заднюю кромку в ноль. Открытая кромка дала бы дыру в замкнутом лофте.
        a4 = -0.1036 if close_te else -0.1015
        return (t / 0.2) * (
            0.2969 * math.sqrt(max(x, 0.0))
            - 0.1260 * x
            - 0.3516 * x * x
            + 0.2843 * x * x * x
            + a4 * x * x * x * x
        )

    def surface(x: float, upper: bool) -> Vec2:
        yc, dy = camber_line(x)
        yt = half_thickness(x)
        th = math.atan(dy)
        if upper:
            return (x - yt * math.sin(th), yc + yt * math.cos(th))
        return (x + yt * math.sin(th), yc - yt * math.cos(th))

    # Косинусное сгущение: точки собираются к носку и к задней кромке, где
    # кривизна велика. Равномерный шаг там даёт видимые грани на силуэте.
    half = max(n // 2, 3)
    xs = [
        x_from + (x_to - x_from) * 0.5 * (1.0 - math.cos(math.pi * i / (half - 1)))
        for i in range(half)
    ]

    upper = [surface(x, True) for x in xs]
    lower = [surface(x, False) for x in xs]

    # Контур: нижняя поверхность от задней кромки к передней, затем верхняя назад.
    # Выбрасывать концы верхней поверхности можно только там, где они реально
    # совпадают с нижней: на остром носке (x_from == 0) и на сомкнутой задней
    # кромке (x_to == 1). На линии разреза хорды точки различны — там обе нужны,
    # иначе у элерона пропадёт торец.
    drop_head = x_from <= 1e-9
    drop_tail = (x_to >= 1.0 - 1e-9) and close_te
    head = 1 if drop_head else 0
    tail = len(upper) - 1 if drop_tail else len(upper)
    return list(reversed(lower)) + upper[head:tail]


def circle(radius: float, n: int, phase: float = 0.0) -> list[Vec2]:
    return [
        (
            radius * math.cos(phase + 2.0 * math.pi * i / n),
            radius * math.sin(phase + 2.0 * math.pi * i / n),
        )
        for i in range(n)
    ]


def rounded_rect(half_w: float, half_h: float, radius: float, n: int) -> list[Vec2]:
    """Скруглённый прямоугольник, равномерно по длине дуги.

    Годится для сечений, которые ни с чем не лофтятся (ступенька, ящики) —
    там корреляция вершин между сечениями не нужна, зато форма честнее
    суперэллипса.
    """
    r = max(0.0, min(radius, half_w, half_h))
    ax, az = half_w - r, half_h - r
    corners = [(ax, az, 0.0), (-ax, az, math.pi * 0.5), (-ax, -az, math.pi), (ax, -az, math.pi * 1.5)]
    per = max(1, n // 4)
    pts: list[Vec2] = []
    for cx, cz, base in corners:
        for i in range(per):
            a = base + math.pi * 0.5 * i / per
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


# --------------------------------------------------------------------------
# Размещение сечений в пространстве
# --------------------------------------------------------------------------

def teardrop(chord: float, thickness: float, n: int, tail: float = 0.40) -> list[Vec2]:
    """Обтекаемое сечение подкоса: круглый нос, вытянутый хвост.

    Возвращает замкнутый контур в (u, v): u — вдоль хорды (нос в −u), v —
    толщина. Строится как окружность носа, сшитая с сужающимся хвостом, а не
    как NACA: подкосу нужен именно вытянутый каплевидный силуэт, а профиль с
    острой задней кромкой на такой толщине превращается в лезвие.
    """
    r = thickness * 0.5
    nose_c = -chord * 0.5 + r            # центр носового радиуса
    tail_u = chord * 0.5
    tail_v = r * tail
    arc = max(3, n - 2)
    pts: list[Vec2] = [(tail_u, tail_v)]
    # Дуга носа от верхней точки касания через переднюю к нижней: 90° → 270°.
    for i in range(arc + 1):
        a = math.pi * (0.5 + i / arc)
        pts.append((nose_c + r * math.cos(a), r * math.sin(a)))
    pts.append((tail_u, -tail_v))
    return pts


def place_yz(section: list[Vec2], y: float, z: float = 0.0, x: float = 0.0) -> list[Vec3]:
    """Сечение (x, z) ставится в плоскость, перпендикулярную оси Y.

    Так строится фюзеляж: набор станций вдоль продольной оси.
    """
    return [(x + sx, y, z + sz) for sx, sz in section]


def place_airfoil(
    section: list[Vec2],
    span_x: float,
    chord: float,
    le_y: float,
    z: float,
    twist_deg: float = 0.0,
    pivot: float = 0.25,
) -> list[Vec3]:
    """Профиль крыла ставится в сечение, перпендикулярное размаху (оси X).

    section в координатах (x/c, y/c); x/c идёт от передней кромки назад.
    В мире хорда ложится вдоль −Y (нос самолёта — +Y), толщина — по Z.
    Крутка вращает профиль вокруг точки `pivot` по хорде.
    """
    tw = math.radians(twist_deg)
    ct, st = math.cos(tw), math.sin(tw)
    out: list[Vec3] = []
    for xc, yc in section:
        # Относительно оси крутки, в метрах.
        c = (xc - pivot) * chord
        t = yc * chord
        cr = c * ct - t * st
        tr = c * st + t * ct
        out.append((span_x, le_y - pivot * chord - cr, z + tr))
    return out


def place_fin(
    section: list[Vec2],
    z: float,
    chord: float,
    le_y: float,
    x: float = 0.0,
    sweep_x: float = 0.0,
    pivot: float = 0.25,
) -> list[Vec3]:
    """Профиль киля: сечение, перпендикулярное оси Z (вертикальное оперение)."""
    out: list[Vec3] = []
    for xc, yc in section:
        out.append((x + sweep_x + yc * chord, le_y - xc * chord, z))
    return out


def rotate_ring(ring: list[Vec3], axis: str, angle_deg: float, origin: Vec3 = (0.0, 0.0, 0.0)) -> list[Vec3]:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    ox, oy, oz = origin
    out: list[Vec3] = []
    for x, y, z in ring:
        dx, dy, dz = x - ox, y - oy, z - oz
        if axis == "X":
            dy, dz = dy * c - dz * s, dy * s + dz * c
        elif axis == "Y":
            dx, dz = dx * c + dz * s, -dx * s + dz * c
        else:
            dx, dy = dx * c - dy * s, dx * s + dy * c
        out.append((ox + dx, oy + dy, oz + dz))
    return out


def mirror_ring(ring: list[Vec3], axis: str = "X") -> list[Vec3]:
    i = {"X": 0, "Y": 1, "Z": 2}[axis]
    out = []
    for v in ring:
        lv = list(v)
        lv[i] = -lv[i]
        out.append(tuple(lv))
    return out


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------
# Сборка меша
# --------------------------------------------------------------------------

class MeshBuilder:
    """Накопитель вершин и граней с материалом и флагом сглаживания на грань.

    Намотка граней сознательно не отслеживается: нормали пересчитываются
    в `to_object` через bmesh. Для замкнутых оболочек это надёжнее ручного
    контроля порядка вершин, который легко сломать при первой же правке формы.
    """

    def __init__(self) -> None:
        self.verts: list[Vec3] = []
        self.faces: list[list[int]] = []
        self.face_mat: list[int] = []
        self.face_smooth: list[bool] = []
        self.face_part: list[int] = []
        self.sharp: set[frozenset[int]] = set()
        # Текущая деталь. Пишется в каждую добавляемую грань и доезжает до
        # атрибута меша, по которому растеризатор карт отличает покрышку от
        # обшивки, а лопасть — от подкоса. Классифицировать потом по координате
        # не вышло бы: детали переплетены в пространстве.
        self.part: int = 0

    # -- низкий уровень -----------------------------------------------------

    def add_verts(self, pts: list[Vec3]) -> list[int]:
        base = len(self.verts)
        self.verts.extend(pts)
        return list(range(base, base + len(pts)))

    def add_face(self, idx: list[int], mat: int = 0, smooth: bool = True) -> None:
        if len(idx) < 3:
            return
        if len(set(idx)) < 3:
            return
        self.faces.append(list(idx))
        self.face_mat.append(mat)
        self.face_smooth.append(smooth)
        self.face_part.append(self.part)

    def mark_sharp(self, ring: list[int], closed: bool = True) -> None:
        n = len(ring)
        last = n if closed else n - 1
        for i in range(last):
            self.sharp.add(frozenset((ring[i], ring[(i + 1) % n])))

    # -- средний уровень ----------------------------------------------------

    def bridge(
        self,
        ring_a: list[int],
        ring_b: list[int],
        mat: int = 0,
        smooth: bool = True,
        closed: bool = True,
    ) -> None:
        """Соединяет два кольца одинаковой длины полосой четырёхугольников."""
        n = len(ring_a)
        assert n == len(ring_b), f"кольца разной длины: {n} и {len(ring_b)}"
        last = n if closed else n - 1
        for i in range(last):
            j = (i + 1) % n
            self.add_face([ring_a[i], ring_a[j], ring_b[j], ring_b[i]], mat, smooth)

    def cap(self, ring: list[int], mat: int = 0, smooth: bool = False) -> None:
        """Закрывает кольцо n-угольником."""
        self.add_face(list(ring), mat, smooth)

    def cap_fan(self, ring: list[int], centre: Vec3, mat: int = 0, smooth: bool = True) -> int:
        """Закрывает кольцо веером на новую центральную вершину."""
        c = self.add_verts([centre])[0]
        n = len(ring)
        for i in range(n):
            self.add_face([ring[i], ring[(i + 1) % n], c], mat, smooth)
        return c

    def loft(
        self,
        rings: list[list[Vec3]],
        mat: int = 0,
        smooth: bool = True,
        closed_ring: bool = True,
        cap_start: bool = False,
        cap_end: bool = False,
        mats_per_span: list[int] | None = None,
    ) -> list[list[int]]:
        """Протягивает оболочку через последовательность сечений.

        mats_per_span задаёт материал для каждого промежутка между сечениями —
        так на одном лофте уживаются, например, борт и остекление.
        """
        idx_rings = [self.add_verts(r) for r in rings]
        for k in range(len(idx_rings) - 1):
            m = mats_per_span[k] if mats_per_span else mat
            self.bridge(idx_rings[k], idx_rings[k + 1], m, smooth, closed_ring)
        if cap_start:
            self.cap(list(reversed(idx_rings[0])), mat, False)
        if cap_end:
            self.cap(idx_rings[-1], mat, False)
        return idx_rings

    def revolve(
        self,
        profile: list[Vec2],
        segments: int,
        axis: str = "Y",
        origin: Vec3 = (0.0, 0.0, 0.0),
        mat: int = 0,
        smooth: bool = True,
        arc_deg: float = 360.0,
        closed_profile: bool = False,
    ) -> list[list[int]]:
        """Тело вращения из профиля (радиус, смещение вдоль оси).

        profile — список (r, h): r — расстояние от оси, h — положение вдоль неё.
        Точки с r == 0 схлопываются в полюс, поэтому кок и ступица получаются
        без вырожденного «зонтика» из тонких треугольников.

        closed_profile замыкает последнюю точку профиля на первую. Это нужно
        сечениям-кольцам: покрышка обходит борт, протектор и обратный борт и
        возвращается в начало, давая герметичный тор. Без замыкания у колеса
        остаются открытыми оба торца.
        """
        full = abs(arc_deg - 360.0) < 1e-6
        steps = segments if full else segments + 1
        rings: list[list[Vec3]] = []
        for s in range(steps):
            a = math.radians(arc_deg) * s / segments
            c, si = math.cos(a), math.sin(a)
            ring: list[Vec3] = []
            for r, h in profile:
                if axis == "Y":
                    ring.append((origin[0] + r * c, origin[1] + h, origin[2] + r * si))
                elif axis == "X":
                    ring.append((origin[0] + h, origin[1] + r * c, origin[2] + r * si))
                else:
                    ring.append((origin[0] + r * c, origin[1] + r * si, origin[2] + h))
            rings.append(ring)

        idx_rings = [self.add_verts(r) for r in rings]
        n = len(profile)
        last = steps if full else steps - 1
        spans = n if closed_profile else n - 1
        for s in range(last):
            a_ring = idx_rings[s]
            b_ring = idx_rings[(s + 1) % steps]
            for i in range(spans):
                j = (i + 1) % n
                quad = [a_ring[i], a_ring[j], b_ring[j], b_ring[i]]
                # Схлопнутые у оси рёбра дают треугольник вместо четырёхугольника.
                uniq: list[int] = []
                for v in quad:
                    if v not in uniq:
                        uniq.append(v)
                self.add_face(uniq, mat, smooth)
        return idx_rings

    def frames(
        self, path: list[Vec3], up_hint: Vec3 = (0.0, 0.0, 1.0)
    ) -> list[tuple[Vec3, Vec3, Vec3]]:
        """Ортонормированные рамки (точка, u, v) в каждом узле ломаной.

        Нормаль сечения берётся из усреднённого направления соседних отрезков,
        иначе на изломе (стойка шасси, подкос) протяжка схлопывается в складку.
        """

        def norm(v: Vec3) -> Vec3:
            l = math.sqrt(sum(c * c for c in v))
            return (v[0] / l, v[1] / l, v[2] / l) if l > 1e-9 else (0.0, 1.0, 0.0)

        def sub(a: Vec3, b: Vec3) -> Vec3:
            return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

        def add(a: Vec3, b: Vec3) -> Vec3:
            return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

        def cross(a: Vec3, b: Vec3) -> Vec3:
            return (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )

        out: list[tuple[Vec3, Vec3, Vec3]] = []
        for i, p in enumerate(path):
            if i == 0:
                d = norm(sub(path[1], path[0]))
            elif i == len(path) - 1:
                d = norm(sub(path[-1], path[-2]))
            else:
                d = norm(add(norm(sub(path[i], path[i - 1])), norm(sub(path[i + 1], path[i]))))

            up = up_hint
            if abs(sum(a * b for a, b in zip(d, norm(up)))) > 0.98:
                up = (1.0, 0.0, 0.0)
            u = norm(cross(d, up))
            v = norm(cross(u, d))
            out.append((p, u, v))
        return out

    def tube(
        self,
        path: list[Vec3],
        radii: list[float] | float,
        segments: int = 8,
        mat: int = 0,
        smooth: bool = True,
        cap_ends: bool = True,
        up_hint: Vec3 = (0.0, 0.0, 1.0),
    ) -> list[list[int]]:
        """Труба переменного радиуса вдоль ломаной."""
        if isinstance(radii, (int, float)):
            radii = [float(radii)] * len(path)
        assert len(radii) == len(path)

        rings: list[list[Vec3]] = []
        for i, (p, u, v) in enumerate(self.frames(path, up_hint)):
            r = radii[i]
            ring = []
            for s in range(segments):
                a = 2.0 * math.pi * s / segments
                cu, sv = math.cos(a) * r, math.sin(a) * r
                ring.append((
                    p[0] + u[0] * cu + v[0] * sv,
                    p[1] + u[1] * cu + v[1] * sv,
                    p[2] + u[2] * cu + v[2] * sv,
                ))
            rings.append(ring)

        return self.loft(rings, mat, smooth, True, cap_ends, cap_ends)

    def beam(
        self,
        path: list[Vec3],
        section: list[Vec2],
        scales: list[float] | float = 1.0,
        mat: int = 0,
        smooth: bool = True,
        cap_ends: bool = True,
        up_hint: Vec3 = (0.0, 0.0, 1.0),
    ) -> list[list[int]]:
        """Протяжка произвольного замкнутого сечения вдоль ломаной.

        Нужна подкосам: круглая труба в силуэте читается как водопроводная, а
        настоящий подкос — обтекаемая капля. Сечение задаётся в осях (u, v)
        рамки: u — поперёк пути в горизонтали, v — вдоль up_hint. Развернуть
        сечение на 180° можно, подав up_hint с обратным знаком.
        """
        if isinstance(scales, (int, float)):
            scales = [float(scales)] * len(path)
        assert len(scales) == len(path)

        rings: list[list[Vec3]] = []
        for i, (p, u, v) in enumerate(self.frames(path, up_hint)):
            k = scales[i]
            rings.append([
                (p[0] + u[0] * su * k + v[0] * sv * k,
                 p[1] + u[1] * su * k + v[1] * sv * k,
                 p[2] + u[2] * su * k + v[2] * sv * k)
                for su, sv in section
            ])
        return self.loft(rings, mat, smooth, True, cap_ends, cap_ends)

    def box(
        self,
        centre: Vec3,
        size: Vec3,
        mat: int = 0,
        smooth: bool = False,
        rot_z_deg: float = 0.0,
    ) -> list[int]:
        cx, cy, cz = centre
        hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
        raw = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
        ]
        a = math.radians(rot_z_deg)
        c, s = math.cos(a), math.sin(a)
        pts = [(cx + x * c - y * s, cy + x * s + y * c, cz + z) for x, y, z in raw]
        v = self.add_verts(pts)
        for f in (
            [0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1],
            [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0],
        ):
            self.add_face([v[i] for i in f], mat, smooth)
        return v

    # -- выгрузка -----------------------------------------------------------

    def to_object(self, name: str, materials: list, origin: Vec3 = (0.0, 0.0, 0.0)):
        """Создаёт объект Blender. Требует bpy — вызывать только внутри Blender.

        origin задаёт положение пивота: вершины сдвигаются на −origin, а сам
        объект ставится в origin. Для игрового ассета это обязательно — иначе
        рули и колёса вращаются вокруг центра сцены, а не вокруг своей оси.
        """
        import bmesh  # noqa: PLC0415 — импорт внутри, чтобы модуль читался вне Blender
        import bpy  # noqa: PLC0415

        ox, oy, oz = origin
        verts = [(x - ox, y - oy, z - oz) for x, y, z in self.verts]

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], self.faces)
        mesh.validate(verbose=False)
        mesh.update()

        for m in materials:
            mesh.materials.append(m)

        if len(mesh.polygons) == len(self.face_mat):
            mesh.polygons.foreach_set("material_index", self.face_mat)
            mesh.polygons.foreach_set("use_smooth", self.face_smooth)
            # Атрибут детали создаём здесь, до прохода через bmesh: слой
            # пользовательских данных переживает пересчёт нормалей и склейку
            # вершин вместе со своими гранями, а проставить его после было бы
            # нельзя — remove_doubles может удалить вырожденную грань и сбить
            # нумерацию.
            attr = mesh.attributes.new(name="part", type="INT", domain="FACE")
            attr.data.foreach_set("value", self.face_part)
        else:
            # from_pydata мог отбросить вырожденную грань — тогда индексы
            # поехали, и молча красить материалы нельзя.
            print(f"  [!] {name}: граней {len(mesh.polygons)}, ожидалось {len(self.face_mat)}")
            for i, poly in enumerate(mesh.polygons):
                if i < len(self.face_mat):
                    poly.material_index = self.face_mat[i]
                    poly.use_smooth = self.face_smooth[i]

        obj = bpy.data.objects.new(name, mesh)
        obj.location = origin
        bpy.context.collection.objects.link(obj)

        # Намотка граней произвольная — нормали приводим к наружным здесь.
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        return obj

    def stats(self) -> str:
        tris = sum(max(0, len(f) - 2) for f in self.faces)
        return f"verts={len(self.verts)} faces={len(self.faces)} tris={tris}"
