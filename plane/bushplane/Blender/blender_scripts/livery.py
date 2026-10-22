"""Раскраска самолёта: чистая функция от точки поверхности.

Здесь нет ни bpy, ни узлов материала — только numpy. Раскраска задаётся как
функция мировой координаты, нормали и номера детали, а карты получаются
растеризацией этой функции в атлас (см. shade.py).

Почему так, а не узловым материалом: рисунок ливреи привязан к трёхмерной
координате, а не к развёртке. Значит он непрерывен через любой шов атласа, и
раскладку UV можно делать автоматической — она ни на что не влияет. Заодно
полосы, сколы и потёки описываются обычным кодом, который можно прочитать,
вместо полусотни узлов, которые нужно расставить.

Все цвета заданы в sRGB 0..255 (так их проще подбирать по референсу) и
переводятся в линейное пространство на выходе: буфер изображения в Blender
всегда линейный, кодирование в sRGB происходит при записи файла.
"""

from __future__ import annotations

import numpy as np

import plane_params as P

# Осевая линия фюзеляжа как вектор: та же таблица станций, что и у геометрии.
# np.interp требует возрастающий аргумент, поэтому станции разворачиваем.
_FUS_Y = np.array([s[0] for s in P.FUSELAGE_STATIONS][::-1], dtype=np.float32)
_FUS_Z = np.array([s[5] for s in P.FUSELAGE_STATIONS][::-1], dtype=np.float32)


def fuselage_axis_z(y: np.ndarray) -> np.ndarray:
    return np.interp(y, _FUS_Y, _FUS_Z).astype(np.float32)


# --------------------------------------------------------------------------
# Номера деталей — должны совпадать с plane_params.PART_*
# --------------------------------------------------------------------------
(SKIN, COWL, METAL, RUBBER, BLADE, INTERIOR, CARGO, GLASS, LIGHT, SPINNER,
 CABIN) = range(11)

# Линии навески рулей в мировых координатах. Те же выражения, что в build.py:
# руль вращается вокруг оси, параллельной X, поэтому линия стоит на постоянной
# координате y, а не на постоянной доле хорды.
Y_HINGE_WING = P.Y_WING_LE - P.WING_CUT * P.WING_ROOT_CHORD
Y_HINGE_FIN = P.FIN_ROOT_Y_LE - P.FIN_CUT * P.FIN_ROOT_CHORD
Y_HINGE_STAB = P.STAB_Y_LE - P.STAB_CUT * P.STAB_ROOT_CHORD


# --------------------------------------------------------------------------
# Палитра (sRGB 0..255)
# --------------------------------------------------------------------------
C_RED = (164, 54, 43)        # выгоревший пожарно-красный
C_RED_DARK = (118, 37, 30)   # он же в тени панелей
C_WHITE = (212, 208, 198)    # грязно-белый, не бумага
C_WHITE_DARK = (168, 163, 153)
# Под сколом на референсе не блестящий алюминий, а тёмный окислившийся металл;
# светлым он становится только на свежих задирах.
C_BARE = (106, 97, 86)
C_BARE_BRIGHT = (158, 152, 140)
C_CORRODE = (58, 47, 38)
C_RUST = (104, 55, 30)
C_RUST_LIGHT = (142, 82, 42)
C_SOOT = (34, 32, 30)
C_COWL = (68, 71, 74)        # тёмный закопчённый капот
C_SPINNER = (38, 106, 96)    # бирюзовый кок
C_BLADE = (26, 26, 28)
C_BLADE_TIP = (218, 168, 40)
C_RUBBER = (34, 34, 36)
C_METAL = (128, 130, 134)    # подкосы и стойки — светлый потёртый металл
C_INTERIOR = (86, 82, 75)
C_CABIN = (78, 78, 72)       # обивка салона; за тонированным стеклом
                             # всё, что темнее, сливается в чёрное пятно
C_CABIN_TRIM = (44, 44, 42)
C_CRATE_GREEN = (84, 94, 66)
C_CRATE_TAN = (162, 134, 82)
C_CRATE_DARK = (74, 78, 72)


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def rgb(c) -> np.ndarray:
    return np.array(c, dtype=np.float32) / 255.0


# --------------------------------------------------------------------------
# Шум
# --------------------------------------------------------------------------

def _hash01(ix, iy, iz, seed: int) -> np.ndarray:
    """Детерминированный хеш решётки в [0,1). Math.random здесь недопустим:
    пересборка ассета обязана давать тот же результат до байта."""
    h = (ix * np.int64(374761393) + iy * np.int64(668265263)
         + iz * np.int64(2147483647) + np.int64(seed) * np.int64(362437))
    h &= np.int64(0x7FFFFFFF)
    h = (h ^ (h >> np.int64(13))) * np.int64(1274126177)
    h &= np.int64(0x7FFFFFFF)
    h = h ^ (h >> np.int64(16))
    return (h & np.int64(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)


def value_noise(p: np.ndarray, seed: int = 0) -> np.ndarray:
    """Трилинейно интерполированный шум значений по точкам (N,3)."""
    f = np.floor(p)
    i = f.astype(np.int64)
    t = p - f
    # Квинтическая кривая, а не t²(3−2t): вторая нужна только чтобы убрать
    # решётку, а карта нормалей берёт производную шума, и на её изломах
    # проступала сеть трещин по всей обшивке.
    t = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    ix, iy, iz = i[:, 0], i[:, 1], i[:, 2]
    tx, ty, tz = t[:, 0], t[:, 1], t[:, 2]

    def h(dx, dy, dz):
        return _hash01(ix + dx, iy + dy, iz + dz, seed)

    c00 = h(0, 0, 0) * (1 - tx) + h(1, 0, 0) * tx
    c10 = h(0, 1, 0) * (1 - tx) + h(1, 1, 0) * tx
    c01 = h(0, 0, 1) * (1 - tx) + h(1, 0, 1) * tx
    c11 = h(0, 1, 1) * (1 - tx) + h(1, 1, 1) * tx
    c0 = c00 * (1 - ty) + c10 * ty
    c1 = c01 * (1 - ty) + c11 * ty
    return c0 * (1 - tz) + c1 * tz


def fbm(p: np.ndarray, octaves: int = 4, seed: int = 0, lacunarity: float = 2.0,
        gain: float = 0.5) -> np.ndarray:
    total = np.zeros(len(p), dtype=np.float32)
    amp, freq, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * value_noise(p * freq, seed + o * 101)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / max(norm, 1e-6)


# --------------------------------------------------------------------------
# Вспомогательные формы
# --------------------------------------------------------------------------

def smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / (b - a + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def band(x: np.ndarray, lo: float, hi: float, soft: float = 0.02) -> np.ndarray:
    """Мягкая полоса: 1 внутри [lo, hi], 0 снаружи."""
    return smoothstep(lo - soft, lo + soft, x) * (1.0 - smoothstep(hi - soft, hi + soft, x))


def ridge(x: np.ndarray, centre: float, half: float, soft: float) -> np.ndarray:
    """Линия: 1 на расстоянии < half от centre."""
    d = np.abs(x - centre)
    return 1.0 - smoothstep(half, half + soft, d)


def periodic_lines(x: np.ndarray, period: float, half: float, soft: float,
                   phase: float = 0.0) -> np.ndarray:
    """Регулярные линии с шагом period — технологические стыки обшивки."""
    d = np.abs(((x - phase + period * 0.5) % period) - period * 0.5)
    return 1.0 - smoothstep(half, half + soft, d)


def mix(a: np.ndarray, b: np.ndarray, t) -> np.ndarray:
    t = np.asarray(t, dtype=np.float32)
    if a.ndim == 2 and t.ndim == 1:
        t = t[:, None]
    return a * (1.0 - t) + b * t


def col(c, n: int) -> np.ndarray:
    return np.tile(rgb(c), (n, 1)).astype(np.float32)


# --------------------------------------------------------------------------
# Раскладка обшивки на поверхности
# --------------------------------------------------------------------------
S_FUS, S_WING, S_FIN, S_STAB = 0, 1, 2, 3

# Шаг технологических стыков и заклёпок, в метрах. Прежние 0.86 и 0.105 были
# втрое реже референса: на рендере ряды читались пунктиром, а не клёпкой.
# Шаг подобран по референсу: у него на крыле видны одна-две нервюры на метр,
# а не клетка. Прежние 0.62×0.78 давали миллиметровку, в которой тонули и
# заклёпки, и сама ливрея.
PANEL_FUS_Y = 0.54       # шпангоуты
PANEL_FUS_V = 0.62       # стрингеры
PANEL_WING_X = 1.08      # нервюры
PANEL_WING_Y = 0.95      # лонжероны
PANEL_TAIL = 0.58
RIVET_PITCH = 0.032
RIVET_R = 0.0055
RIVET_SOFT = 0.0035
SEAM_HALF = 0.0045
SEAM_SOFT = 0.0070


def surface_id(pos: np.ndarray) -> np.ndarray:
    """Какой поверхности принадлежит точка обшивки.

    Нужно затем, что раскладка панелей у каждой поверхности своя: на фюзеляже
    шпангоуты идут поперёк, на крыле нервюры — по размаху, на киле — по высоте.
    Одна общая сетка по мировым осям давала на оперении случайную штриховку.
    Порядок проверок важен: киль лежит и выше 2.02, и был бы принят за крыло.
    """
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    s = np.full(len(pos), S_FUS, dtype=np.int32)
    s = np.where(z > 2.02, S_WING, s)
    s = np.where((y < -3.90) & (ax < 0.38) & (z > 1.95), S_FIN, s)
    s = np.where((y < -4.30) & (ax > 0.30) & (z < 1.98) & (z > 1.05), S_STAB, s)
    return s


def _skin_uv(pos: np.ndarray, nrm: np.ndarray, sid: np.ndarray) -> tuple:
    """Две координаты раскладки (u вдоль рядов, v поперёк) для каждой точки."""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    nx, nz = np.abs(nrm[:, 0]), np.abs(nrm[:, 2])

    # Фюзеляж: u — вдоль корпуса, v — по обводу. На бортах обвод идёт по z,
    # на крыше и днище — по x. Выбираем по нормали, а не по координате: на
    # скруглении углов иначе стрингеры сходились бы в узел.
    v_fus = np.where(nx > nz, z - fuselage_axis_z(y), x)

    u = np.where(sid == S_FUS, y, ax)
    v = np.where(sid == S_FUS, v_fus, y)
    u = np.where(sid == S_FIN, z, u)
    v = np.where(sid == S_FIN, y, v)
    return u, v


def _panel_grid(u, v, sid) -> tuple:
    """Стыки панелей и ряды заклёпок по раскладке поверхности."""
    pu = np.where(sid == S_FUS, PANEL_FUS_Y,
                  np.where(sid == S_WING, PANEL_WING_X, PANEL_TAIL))
    pv = np.where(sid == S_FUS, PANEL_FUS_V,
                  np.where(sid == S_WING, PANEL_WING_Y, PANEL_TAIL * 1.6))

    def plines(t, period, half, soft):
        """periodic_lines с шагом-вектором: период у каждой поверхности свой."""
        d = np.abs(((t + period * 0.5) % period) - period * 0.5)
        return 1.0 - smoothstep(half, half + soft, d)

    seam_u = plines(u, pu, SEAM_HALF, SEAM_SOFT)
    seam_v = plines(v, pv, SEAM_HALF, SEAM_SOFT)
    seam = np.maximum(seam_u, seam_v)

    # Заклёпки сидят вдоль стыков: полоса стыка × регулярный шаг вдоль него.
    riv_along_u = (plines(u, pu, RIVET_R * 1.7, RIVET_SOFT)
                   * periodic_lines(v, RIVET_PITCH, RIVET_R, RIVET_SOFT))
    riv_along_v = (plines(v, pv, RIVET_R * 1.7, RIVET_SOFT)
                   * periodic_lines(u, RIVET_PITCH, RIVET_R, RIVET_SOFT))
    rivets = np.maximum(riv_along_u, riv_along_v)
    return seam, rivets


def edge_strips(pos: np.ndarray, sid: np.ndarray) -> tuple:
    """Голый металл по передним кромкам и по задней кромке крыла.

    На референсе передние кромки крыла, киля и стабилизатора тёмные — краски
    там нет вовсе. Это самое заметное отличие, которое не давала ливрея:
    без полос все поверхности читались сплошным красным.

    Кромки берём из тех же выражений, что и геометрия: крыло и стабилизатор
    имеют прямую переднюю кромку на постоянной y (сужение идёт назад), у киля
    кромка уезжает назад со стреловидностью по высоте.
    """
    y, z = pos[:, 1], pos[:, 2]
    ax = np.abs(pos[:, 0])
    le = np.zeros(len(pos), dtype=np.float32)

    le = np.where(sid == S_WING,
                  1.0 - smoothstep(0.09, 0.16, np.abs(y - P.Y_WING_LE)), le)
    t_fin = np.clip((z - P.FIN_BASE_Z) / P.FIN_HEIGHT, 0.0, 1.0)
    le_fin = P.FIN_ROOT_Y_LE - P.FIN_SWEEP * t_fin
    le = np.where(sid == S_FIN,
                  1.0 - smoothstep(0.08, 0.15, np.abs(y - le_fin)), le)
    le = np.where(sid == S_STAB,
                  1.0 - smoothstep(0.07, 0.13, np.abs(y - P.STAB_Y_LE)), le)

    # Задняя кромка крыла: узкая тёмная полоса, вдоль неё и стоят кронштейны
    # навески. Хорда сужается к концу, поэтому кромка не на постоянной y.
    frac = np.clip(ax / P.WING_SEMI, 0.0, 1.0)
    chord = P.WING_ROOT_CHORD + (P.WING_TIP_CHORD - P.WING_ROOT_CHORD) * frac
    te_y = P.Y_WING_LE - chord
    te = np.where(sid == S_WING,
                  1.0 - smoothstep(0.04, 0.10, np.abs(y - te_y)), 0.0)
    return np.clip(le, 0.0, 1.0), np.clip(te, 0.0, 1.0)


def hinge_lines(pos: np.ndarray, sid: np.ndarray) -> np.ndarray:
    """Щели навески рулей. Без них рули сливаются с неподвижной частью."""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    h = np.zeros(len(pos), dtype=np.float32)

    span = P.WING_SEMI
    wing = (sid == S_WING) & (
        ((ax > P.FLAP_FROM * span) & (ax < P.FLAP_TO * span))
        | ((ax > P.AILERON_FROM * span) & (ax < P.AILERON_TO * span))
    )
    h = np.maximum(h, ridge(y, Y_HINGE_WING, 0.010, 0.012) * wing)
    # Торцы рулей: поперечные щели на краях закрылка и элерона.
    for f in (P.FLAP_FROM, P.FLAP_TO, P.AILERON_FROM, P.AILERON_TO):
        gap = ridge(ax, f * span, 0.010, 0.010) * (sid == S_WING) * (y < Y_HINGE_WING)
        h = np.maximum(h, gap)

    h = np.maximum(h, ridge(y, Y_HINGE_FIN, 0.010, 0.012) * (sid == S_FIN))
    h = np.maximum(h, ridge(y, Y_HINGE_STAB, 0.010, 0.012) * (sid == S_STAB))
    return np.clip(h, 0.0, 1.0)


def door_outlines(pos: np.ndarray) -> np.ndarray:
    """Контуры дверей и грузового проёма на борту — линии разъёма обшивки."""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    side = ax > 0.40
    o = np.zeros(len(pos), dtype=np.float32)

    def rect(y0, y1, z0, z1):
        inside_y = band(y, y0, y1, 0.004)
        inside_z = band(z, z0, z1, 0.004)
        frame = np.maximum(
            (ridge(y, y0, 0.006, 0.006) + ridge(y, y1, 0.006, 0.006)) * inside_z,
            (ridge(z, z0, 0.006, 0.006) + ridge(z, z1, 0.006, 0.006)) * inside_y,
        )
        return np.clip(frame, 0.0, 1.0) * side

    # Дверь пилота — вокруг первого окна, с запасом вниз до пола кабины.
    wy0, wy1, _, wz1 = P.SIDE_WINDOWS[0]
    o = np.maximum(o, rect(wy0 - 0.16, wy1 + 0.13, 1.02, wz1 + 0.09))
    # Рамка грузового проёма.
    cy0, cy1 = P.CARGO_Y
    o = np.maximum(o, rect(cy0 - 0.05, cy1 + 0.05, P.CARGO_FLOOR_Z - 0.05,
                           P.CARGO_CEIL_Z + 0.05))
    return o


# --------------------------------------------------------------------------
# Ливрея
# --------------------------------------------------------------------------

def livery_mask(pos: np.ndarray) -> np.ndarray:
    """Где белая краска, а где красная. 1 = белое.

    Полосы на референсе идут поперёк каждой поверхности: вдоль борта широкая
    лента на полувысоте, на крыле и стабилизаторе — поперечные полосы по
    размаху, на киле — горизонтальная лента. Задаются в мировых координатах,
    поэтому на стыке крыла с фюзеляжем рисунок продолжается без разрыва.
    """
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    w = np.zeros(len(pos), dtype=np.float32)

    # --- фюзеляж: широкая лента по борту, идущая вдоль осевой линии ---------
    centre = fuselage_axis_z(y) - 0.24
    fus = (1.0 - smoothstep(0.265, 0.295, np.abs(z - centre))) * band(y, -5.4, 2.70, 0.10)
    w = np.maximum(w, fus * (ax < 0.95) * (z < 2.24))

    # --- поперечная лента сразу за грузовым проёмом -------------------------
    w = np.maximum(w, band(y, -3.95, -3.15, 0.03) * (ax < 0.95) * (z > 0.9) * (z < 2.28))

    # --- крыло: две поперечные полосы по размаху ---------------------------
    on_wing = (z > 2.02) & (ax > 0.55)
    w = np.maximum(w, band(ax, 2.10, 3.65, 0.025) * on_wing)
    w = np.maximum(w, band(ax, 5.20, 6.50, 0.025) * on_wing)

    # --- киль: горизонтальная лента ----------------------------------------
    on_fin = (y < -3.9) & (ax < 0.32) & (z > 2.05)
    w = np.maximum(w, band(z, 2.42, 3.02, 0.025) * on_fin)

    # --- стабилизатор: полоса по размаху -----------------------------------
    on_stab = (y < -4.4) & (z < 2.00) & (z > 1.05) & (ax > 0.32)
    w = np.maximum(w, band(ax, 1.05, 2.00, 0.025) * on_stab)

    return np.clip(w, 0.0, 1.0)


def hex_logo(pos: np.ndarray) -> np.ndarray:
    """Белый шестиугольник с кубом на бортах носа — эмблема с референса.

    Шестиугольник строится как пересечение трёх полос под 60°: это ровно то,
    чем он и является, и обходится без растрового файла с логотипом.
    """
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    cy, cz, r = 1.38, 1.24, 0.30
    u = (y - cy) / r
    v = (z - cz) / r
    side = np.abs(x) > 0.40          # только борта, не крыша и не днище

    c60, s60 = 0.5, 0.8660254
    d = np.maximum.reduce([
        np.abs(v),
        np.abs(v * c60 + u * s60),
        np.abs(v * c60 - u * s60),
    ])
    outer = 1.0 - smoothstep(0.86, 0.94, d)
    inner = 1.0 - smoothstep(0.62, 0.70, d)
    ringed = outer - inner                      # контур шестиугольника

    # Куб внутри: квадрат с двумя рёбрами, намёком на изометрию.
    box = band(u, -0.34, 0.34, 0.04) * band(v, -0.34, 0.30, 0.04)
    box_in = band(u, -0.22, 0.22, 0.03) * band(v, -0.24, 0.16, 0.03)
    cube = box - box_in * 0.55

    return np.clip((ringed + cube) * side, 0.0, 1.0)


def panel_height(pos: np.ndarray, nrm: np.ndarray, part: np.ndarray,
                 sid: np.ndarray, seam: np.ndarray, rivets: np.ndarray,
                 hinge: np.ndarray, doors: np.ndarray) -> np.ndarray:
    """Рельеф обшивки: стыки, заклёпки, щели навески. 0.5 — нейтраль."""
    h = np.full(len(pos), 0.5, dtype=np.float32)
    skin = part == SKIN

    # Заклёпка — выпуклость, стык и щель — канавка. Заклёпки заметно выше
    # прежних: при 0.16 они терялись под шагренью и в карту нормалей почти
    # не попадали.
    relief = -seam * 0.26 - hinge * 0.46 - doors * 0.30 + rivets * 0.30
    h = np.where(skin, 0.5 + relief, h)

    # Капот: сетка мельче, панели заметнее — на референсе он набран из
    # отдельных пластин с бортиками.
    cowl = part == COWL
    if cowl.any():
        y, z = pos[:, 1], pos[:, 2]
        ang = np.arctan2(z - P.PROP_HUB_Z, pos[:, 0])
        c_seam = np.maximum(periodic_lines(y, 0.26, 0.007, 0.010),
                            periodic_lines(ang, 0.52, 0.010, 0.014))
        c_riv = (periodic_lines(y, 0.26, 0.012, 0.007)
                 * periodic_lines(ang, 0.10, 0.030, 0.020))
        c_riv = np.maximum(c_riv, periodic_lines(ang, 0.52, 0.018, 0.010)
                           * periodic_lines(y, 0.042, 0.009, 0.006))
        h = np.where(cowl, 0.5 - c_seam * 0.22 + c_riv * 0.24, h)

    # Кок: кольцевые стыки секций уже сделаны геометрией, здесь только шагрень.
    # Протектор покрышки: грунтозацепы поперёк беговой дорожки.
    # Угол берём из нормали, а не из координаты: ось всех колёс направлена по X,
    # поэтому нормаль на протекторе смотрит строго от оси, и такой угол не
    # зависит от того, где колесо стоит.
    rub = part == RUBBER
    if rub.any():
        ang = np.arctan2(nrm[:, 2], nrm[:, 1])
        # Шашка, а не сплошное ребро: ряд грунтозацепов разбит поперёк, иначе
        # покрышка читалась шестерёнкой с непрерывными кольцевыми рёбрами.
        lug = periodic_lines(ang, 0.26, 0.055, 0.035)
        across = periodic_lines(pos[:, 0], 0.085, 0.030, 0.018, phase=0.0)
        tread = np.maximum(lug * (0.45 + 0.55 * across),
                           periodic_lines(ang, 0.13, 0.018, 0.018) * 0.35)
        h = np.where(rub, 0.5 + tread * 0.40 - 0.12, h)

    # Мелкая шагрень по всему металлу — иначе поверхность стеклянно ровная.
    # Шагрень на 26 м⁻¹ при 4096 давала фактуру кожи. Крупные пологие вмятины
    # (обшивка между шпангоутами всегда слегка играет) плюс тихая мелкая
    # шероховатость читаются металлом.
    dent = (fbm(pos * 1.8, 2, 777) - 0.5) * 0.020
    grain = (fbm(pos * 15.0, 3, 991) - 0.5) * 0.011
    return np.clip(h + dent + grain, 0.0, 1.0)


def evaluate(pos: np.ndarray, nrm: np.ndarray, part: np.ndarray, seed: int = 7) -> dict:
    """Возвращает base (N,3) линейный RGB, metallic, roughness, height (N,)."""
    n = len(pos)
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    ax = np.abs(x)
    ny = nrm[:, 1]

    base = col(C_BARE, n)
    metal = np.full(n, 0.0, dtype=np.float32)
    rough = np.full(n, 0.62, dtype=np.float32)

    # --- раскладка панелей --------------------------------------------------
    sid = surface_id(pos)
    u, v = _skin_uv(pos, nrm, sid)
    seam, rivets = _panel_grid(u, v, sid)
    hinge = hinge_lines(pos, sid)
    doors = door_outlines(pos)
    le_strip, te_strip = edge_strips(pos, sid)
    seam = np.maximum(seam, np.maximum(hinge, doors))

    # ---------------------------------------------------------------- обшивка
    white = livery_mask(pos)
    paint = mix(col(C_RED, n), col(C_WHITE, n), white)
    dark = mix(col(C_RED_DARK, n), col(C_WHITE_DARK, n), white)

    # Неровность выгорания: краска нигде не лежит одним тоном.
    fade = fbm(pos * 0.9, 4, seed)
    paint = mix(dark, paint, np.clip(fade * 0.7 + 0.42, 0.0, 1.0))

    # Эмблема поверх краски.
    logo = hex_logo(pos)
    paint = mix(paint, col(C_WHITE, n), logo * 0.92)

    # --- сколы ---------------------------------------------------------------
    # Краска на референсе съедена крупными пятнами с рваными краями, а не
    # присыпана равномерной крапиной. Поэтому сколы собираются из трёх частот:
    # крупные пятна задают форму, средняя даёт рваный край, мелкая — крапину.
    # Держится краска хуже там, где её задевают: передние кромки, стыки,
    # заклёпки, границы полос ливреи и низ, куда летит из-под колёс.
    lead = np.clip(ny, 0.0, 1.0) ** 2
    edge_of_band = 1.0 - np.abs(white * 2.0 - 1.0)
    seam_zone = np.clip(seam + rivets * 0.7, 0.0, 1.0)
    belly = smoothstep(1.45, 0.85, z)

    chip_big = fbm(pos * 3.4, 4, seed + 31)
    chip_mid = fbm(pos * 11.0, 4, seed + 57)
    chip_fine = fbm(pos * 34.0, 3, seed + 83)
    # Постоянное слагаемое намеренно маленькое: на референсе середина панели
    # почти цела, а съедена краска у стыков, заклёпок, передних кромок и внизу.
    # При прежнем 0.20 скол шёл сплошным полем и превращал ливрею в камуфляж.
    drive = (0.05 + 0.44 * lead + 0.20 * edge_of_band
             + 0.52 * seam_zone + 0.22 * belly) * (1.0 - 0.32 * white)
    # Вес сдвинут с крупной частоты на мелкую, а переход сужен: крупные мягкие
    # пятна читались плесенью, тогда как у референса скол мелкий и с резким
    # краем.
    n_chip = (smoothstep(0.34, 0.74, chip_big) * 0.32
              + chip_mid * 0.36 + chip_fine * 0.32)
    chips = np.clip(smoothstep(0.655, 0.775, n_chip + drive * 0.30), 0.0, 1.0)

    bare = mix(col(C_BARE, n), col(C_BARE_BRIGHT, n), chip_fine)
    bare = mix(bare, col(C_CORRODE, n), smoothstep(0.55, 0.85, chip_mid) * 0.65)
    skin_col = mix(paint, bare, chips)

    # Тёмная кайма по краю скола: облезающая краска всегда с тёмным ободком,
    # без него пятно выглядит наклейкой.
    rim = band(n_chip + drive * 0.30, 0.628, 0.665, 0.016)
    skin_col = mix(skin_col, col(C_CORRODE, n), np.clip(rim, 0.0, 1.0) * 0.55)

    # --- ржавые потёки -------------------------------------------------------
    # Вытянуты по вертикали: шум сжат по z, поэтому следы текут вниз.
    streak_p = np.stack([x * 5.0, y * 5.0, z * 0.55], axis=1)
    streak = fbm(streak_p, 4, seed + 77)
    below = smoothstep(2.15, 1.20, z)
    rust_amt = np.clip(smoothstep(0.55, 0.85, streak) * below * (0.35 + 0.9 * chips), 0.0, 1.0)
    rust_col = mix(col(C_RUST, n), col(C_RUST_LIGHT, n), chip_fine)
    skin_col = mix(skin_col, rust_col, rust_amt * 0.8)

    # --- грязь снизу и копоть за капотом ------------------------------------
    # Копоть, стекающая вниз от стыков и оконных сливов. На референсе это
    # самый заметный слой грязи, и без него обшивка выглядит только выгоревшей,
    # но не грязной. Шум сжат по z в 12 раз — отсюда вертикальные хвосты.
    drip_p = np.stack([x * 9.0, y * 9.0, z * 0.75], axis=1)
    drip = fbm(drip_p, 4, seed + 131)
    drip_amt = np.clip(smoothstep(0.60, 0.86, drip) * smoothstep(2.45, 1.50, z), 0.0, 1.0)
    skin_col = mix(skin_col, col(C_SOOT, n), drip_amt * 0.55)

    grime = smoothstep(1.35, 0.80, z) * (0.35 + 0.5 * fbm(pos * 3.2, 3, seed + 13))
    skin_col = mix(skin_col, col(C_SOOT, n), np.clip(grime, 0.0, 1.0) * 0.45)
    soot = band(y, 1.8, 3.2, 0.35) * smoothstep(1.85, 1.30, z) * (ax > 0.30)
    skin_col = mix(skin_col, col(C_SOOT, n), np.clip(soot, 0.0, 1.0) * 0.5)

    # --- стыки, заклёпки и щели в цвете -------------------------------------
    # В карте высот они уже есть, но одного рельефа мало: на референсе шов
    # заметен прежде всего тем, что в нём собралась грязь, а заклёпка — тем,
    # что вокруг неё краска потёрта до металла.
    # Голый металл кромок кладём поверх сколов: краски там нет вообще, и
    # спорить с ней незачем.
    edge_metal = np.clip(le_strip * 0.92 + te_strip * 0.70, 0.0, 1.0)
    edge_col = mix(col(C_BARE, n), col(C_CORRODE, n), smoothstep(0.4, 0.8, chip_mid))
    skin_col = mix(skin_col, edge_col, edge_metal)

    seam_dirt = np.clip(seam, 0.0, 1.0) * (0.35 + 0.65 * fbm(pos * 6.0, 3, seed + 5))
    skin_col = mix(skin_col, col(C_SOOT, n), seam_dirt * 0.30)
    skin_col = mix(skin_col, col(C_CORRODE, n), np.clip(hinge + doors, 0.0, 1.0) * 0.40)
    # Заклёпку рисует прежде всего карта нормалей; в цвете от неё нужен лишь
    # намёк, иначе ряды читаются пунктирной строчкой поверх краски.
    skin_col = mix(skin_col, col(C_BARE, n), rivets * 0.20)

    skin_rough = (0.74 - 0.16 * white + 0.10 * rust_amt - 0.24 * chips
                  + 0.10 * np.clip(seam, 0.0, 1.0))
    skin_metal = np.clip(chips * 0.88 + rivets * 0.20 + edge_metal * 0.75, 0.0, 1.0)

    is_skin = part == SKIN
    base = np.where(is_skin[:, None], skin_col, base)
    metal = np.where(is_skin, skin_metal, metal)
    rough = np.where(is_skin, skin_rough, rough)

    # ---------------------------------------------------------------- капот
    is_cowl = part == COWL
    cowl_wear = fbm(pos * 9.0, 4, seed + 5)
    cowl_fine = fbm(pos * 30.0, 3, seed + 95)
    cowl_col = mix(col(C_COWL, n), col(C_BARE, n),
                   smoothstep(0.52, 0.82, cowl_wear) * 0.75)
    cowl_col = mix(cowl_col, col(C_SOOT, n),
                   smoothstep(0.35, 0.0, np.abs(z - 1.2)) * 0.4)
    # Сетка пластин капота: её считает panel_height, здесь только затемнение шва.
    ang = np.arctan2(z - P.PROP_HUB_Z, x)
    c_seam = np.maximum(periodic_lines(y, 0.26, 0.008, 0.012),
                        periodic_lines(ang, 0.52, 0.012, 0.016))
    cowl_col = mix(cowl_col, col(C_SOOT, n), c_seam * 0.28)
    cowl_col = mix(cowl_col, col(C_BARE_BRIGHT, n),
                   smoothstep(0.74, 0.92, cowl_fine) * 0.30)
    base = np.where(is_cowl[:, None], cowl_col, base)
    metal = np.where(is_cowl, 0.62, metal)
    rough = np.where(is_cowl, 0.55 + 0.24 * cowl_wear, rough)

    # ---------------------------------------------------------------- кок
    # Отдельный номер детали вместо прежней догадки «впереди и близко к оси»:
    # носовая чашка капота лежит ровно там же и красилась бирюзовой.
    is_spin = part == SPINNER
    spin_col = mix(col(C_SPINNER, n), col(C_BARE, n),
                   smoothstep(0.70, 0.92, cowl_wear) * 0.5)
    base = np.where(is_spin[:, None], spin_col, base)
    metal = np.where(is_spin, 0.45, metal)
    rough = np.where(is_spin, 0.40, rough)

    # ---------------------------------------------------------------- лопасти
    is_blade = part == BLADE
    r_blade = np.sqrt(x * x + (z - P.PROP_HUB_Z) ** 2)
    r_tip = P.PROP_DIAMETER * 0.5
    # Законцовка: жёлтая зона, а внутри неё чёрная полоса — так на референсе.
    yellow = smoothstep(r_tip - 0.20, r_tip - 0.17, r_blade)
    yellow *= 1.0 - band(r_blade, r_tip - 0.125, r_tip - 0.085, 0.006)
    blade_col = mix(col(C_BLADE, n), col(C_BLADE_TIP, n), yellow)
    blade_wear = fbm(pos * 16.0, 3, seed + 41)
    blade_col = mix(blade_col, col(C_BARE, n),
                    smoothstep(0.74, 0.92, blade_wear) * 0.50 * (1.0 - 0.85 * yellow))
    base = np.where(is_blade[:, None], blade_col, base)
    metal = np.where(is_blade, 0.45, metal)
    rough = np.where(is_blade, 0.38, rough)

    # ---------------------------------------------------------------- металл
    is_metal = part == METAL
    mw = fbm(pos * 11.0, 4, seed + 19)
    mf = fbm(pos * 38.0, 3, seed + 29)
    met_col = mix(col(C_METAL, n), col(C_RUST, n), smoothstep(0.66, 0.92, mw) * 0.45)
    met_col = mix(met_col, col(C_BARE_BRIGHT, n), smoothstep(0.55, 0.80, mf) * 0.35)
    # Стойки и подножка снизу всегда в грязи.
    met_col = mix(met_col, col(C_SOOT, n), smoothstep(0.90, 0.30, z) * 0.35)
    base = np.where(is_metal[:, None], met_col, base)
    metal = np.where(is_metal, 0.88, metal)
    rough = np.where(is_metal, 0.30 + 0.30 * mw, rough)

    # ---------------------------------------------------------------- резина
    is_rub = part == RUBBER
    dust = fbm(pos * 13.0, 3, seed + 23)
    rub_col = mix(col(C_RUBBER, n), col(C_BARE, n), dust * 0.22)
    base = np.where(is_rub[:, None], rub_col, base)
    metal = np.where(is_rub, 0.0, metal)
    rough = np.where(is_rub, 0.90, rough)

    # ---------------------------------------------------------------- отсек
    is_int = part == INTERIOR
    # Пол отличаем по нормали: он смотрит вверх, стенки и потолок — нет.
    floor = np.clip(nrm[:, 2], 0.0, 1.0) ** 2
    int_col = mix(col(C_INTERIOR, n), col(C_CRATE_TAN, n), floor * 0.30)
    int_col = mix(int_col, col(C_SOOT, n),
                  periodic_lines(y, 0.16, 0.006, 0.006) * 0.45)
    int_col = mix(int_col, col(C_SOOT, n), fbm(pos * 9.0, 3, seed + 71) * 0.25)
    base = np.where(is_int[:, None], int_col, base)
    metal = np.where(is_int, 0.15, metal)
    rough = np.where(is_int, 0.85, rough)

    # ---------------------------------------------------------------- груз
    # Ячейку берём по раскладке ящиков (они разнесены по y и сложены по z), а не
    # кубическую: кубическая рассекала ящик пополам, и он выходил полосатым.
    is_cargo = part == CARGO
    cy_i = np.floor((y - P.Y_CARGO_CENTRE + 0.75) / P.CRATE_CELL_Y).astype(np.int64)
    cz_i = np.floor((z - P.CARGO_FLOOR_Z) / P.CRATE_CELL_Z).astype(np.int64)
    pick = _hash01(cy_i, cz_i, np.zeros_like(cy_i), 404)
    crate = np.where((pick < 0.38)[:, None], col(C_CRATE_GREEN, n),
                     np.where((pick < 0.72)[:, None], col(C_CRATE_TAN, n),
                              col(C_CRATE_DARK, n)))
    scuff = fbm(pos * 19.0, 3, seed + 67)
    crate = mix(crate, col(C_SOOT, n), smoothstep(0.62, 0.9, scuff) * 0.35)
    # Доски по высоте и поперечная оковка: без них ящик читается крашеным
    # кубиком, а в проём он виден вблизи и весь смысл груза в нём.
    planks = periodic_lines(z, 0.085, 0.0035, 0.004)
    strap = np.maximum(periodic_lines(y, 0.30, 0.022, 0.008),
                       periodic_lines(x, 0.30, 0.022, 0.008))
    crate = mix(crate, col(C_SOOT, n), planks * 0.45)
    crate = mix(crate, col(C_METAL, n), strap * 0.55)
    base = np.where(is_cargo[:, None], crate, base)
    metal = np.where(is_cargo, 0.05, metal)
    metal = np.where(is_cargo & (strap > 0.5), 0.35, metal)
    rough = np.where(is_cargo, 0.86 - 0.16 * strap, rough)

    # ---------------------------------------------------------------- салон
    is_cab = part == CABIN
    wear = fbm(pos * 14.0, 3, seed + 87)
    cab = mix(col(C_CABIN, n), col(C_CABIN_TRIM, n), smoothstep(0.42, 0.75, wear))
    # Пол светлее обивки: иначе сквозь стекло салон читается сплошной чернотой.
    floor_up = np.clip(nrm[:, 2], 0.0, 1.0) ** 2
    cab = mix(cab, col(C_INTERIOR, n), floor_up * 0.55)
    base = np.where(is_cab[:, None], cab, base)
    metal = np.where(is_cab, 0.05, metal)
    rough = np.where(is_cab, 0.88, rough)

    height = panel_height(pos, nrm, part, sid, seam, rivets, hinge, doors)

    return {
        "base": srgb_to_linear(np.clip(base, 0.0, 1.0)),
        "metallic": np.clip(metal, 0.0, 1.0),
        "roughness": np.clip(rough, 0.05, 1.0),
        "height": height,
    }
