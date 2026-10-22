"""Дымовой тест plane_lib: строит по одному образцу каждого примитива.

Проверяет не красоту, а то, что геометрия замкнута, нормали наружу и
материалы разложились по граням. Запуск:
  blender --background --factory-startup --python smoke_lib.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import plane_lib as L  # noqa: E402


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def dummy_mats(n):
    out = []
    for i in range(n):
        m = bpy.data.materials.new(f"M_{i}")
        out.append(m)
    return out


def check(obj, label):
    me = obj.data
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    # Замкнутость: у герметичной оболочки каждое ребро делят ровно две грани.
    edge_use = {}
    for p in me.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            e = frozenset((vs[i], vs[(i + 1) % len(vs)]))
            edge_use[e] = edge_use.get(e, 0) + 1
    boundary = sum(1 for v in edge_use.values() if v == 1)
    nonmanifold = sum(1 for v in edge_use.values() if v > 2)
    vol = sum(p.area for p in me.polygons)
    mats = sorted({p.material_index for p in me.polygons})
    print(
        f"{label:18s} verts={len(me.vertices):5d} tris={tris:5d} "
        f"area={vol:8.3f} boundary_edges={boundary:4d} nonmanifold={nonmanifold:3d} mats={mats}"
    )
    return boundary, nonmanifold


fresh_scene()
mats = dummy_mats(3)
problems = []

# --- 1. Лофт фюзеляжа: суперэллипс с переменными параметрами ---------------
b = L.MeshBuilder()
stations = [
    # (y, half_w, half_h_top, half_h_bot, exponent, z_centre)
    (-4.2, 0.10, 0.10, 0.08, 3.0, 1.30),
    (-2.5, 0.42, 0.46, 0.34, 3.6, 1.28),
    (0.0, 0.74, 0.72, 0.52, 4.2, 1.20),
    (2.0, 0.72, 0.70, 0.50, 4.0, 1.22),
    (3.4, 0.46, 0.44, 0.36, 3.2, 1.30),
]
rings = [
    L.place_yz(L.superellipse(w, ht, hb, e, 24), y, z)
    for y, w, ht, hb, e, z in stations
]
b.loft(rings, mat=0, smooth=True, closed_ring=True, cap_start=True, cap_end=True)
o = b.to_object("T_Fuselage", mats)
problems += [("fuselage",) + check(o, "loft/fuselage")]

# --- 2. Крыло: профиль NACA, разрезанный на основную часть и элерон --------
b = L.MeshBuilder()
CUT = 0.72
main = [
    L.place_airfoil(L.naca4(0.02, 0.4, 0.12, 28, 0.0, CUT), x, ch, 0.9, z, tw)
    for x, ch, z, tw in [(0.0, 1.75, 1.95, 2.0), (3.5, 1.66, 2.04, 1.0), (7.0, 1.52, 2.14, 0.0)]
]
b.loft(main, mat=0, smooth=True, closed_ring=True, cap_start=True, cap_end=True)
o = b.to_object("T_WingMain", mats)
problems += [("wing_main",) + check(o, "loft/wing_main")]

b = L.MeshBuilder()
ail = [
    L.place_airfoil(L.naca4(0.02, 0.4, 0.12, 28, CUT, 1.0), x, ch, 0.9, z, tw)
    for x, ch, z, tw in [(4.2, 1.62, 2.07, 0.6), (6.8, 1.53, 2.13, 0.1)]
]
b.loft(ail, mat=1, smooth=True, closed_ring=True, cap_start=True, cap_end=True)
o = b.to_object("T_Aileron", mats)
problems += [("aileron",) + check(o, "loft/aileron")]

# --- 3. Тело вращения: кок винта (профиль доходит до r=0) ------------------
b = L.MeshBuilder()
prof = [(0.0, 0.62), (0.10, 0.56), (0.18, 0.44), (0.23, 0.26), (0.25, 0.06), (0.25, 0.0), (0.0, 0.0)]
b.revolve(prof, 20, axis="Y", mat=2, smooth=True)
o = b.to_object("T_Spinner", mats)
problems += [("spinner",) + check(o, "revolve/spinner")]

# --- 4. Труба с изломом: стойка шасси --------------------------------------
b = L.MeshBuilder()
path = [(0.35, 0.2, 1.05), (0.72, 0.18, 0.72), (1.02, 0.15, 0.50)]
b.tube(path, [0.075, 0.062, 0.050], segments=10, mat=2)
o = b.to_object("T_GearLeg", mats)
problems += [("gearleg",) + check(o, "tube/gearleg")]

# --- 5. Колесо: вращение профиля покрышки ----------------------------------
b = L.MeshBuilder()
tyre = [(0.20, -0.16), (0.40, -0.17), (0.48, -0.09), (0.48, 0.09), (0.40, 0.17), (0.20, 0.16)]
b.revolve(tyre, 24, axis="X", mat=1, smooth=True)
o = b.to_object("T_Wheel", mats)
problems += [("wheel",) + check(o, "revolve/wheel")]

# --- 6. Ящик и пивот --------------------------------------------------------
b = L.MeshBuilder()
b.box((0.0, 0.0, 0.0), (0.62, 0.40, 0.34), mat=0, smooth=False)
o = b.to_object("T_Crate", mats, origin=(1.0, 2.0, 3.0))
problems += [("crate",) + check(o, "box/crate")]
print(f"  crate origin -> {tuple(round(c, 3) for c in o.location)} (ожидалось (1.0, 2.0, 3.0))")

# --- 7. Острые рёбра и API, на которые опирается генератор ------------------
me = o.data
print("--- проверка API Blender 5.2 ---")
print("  edge.use_edge_sharp  :", hasattr(me.edges[0], "use_edge_sharp"))
print("  poly.use_smooth      :", hasattr(me.polygons[0], "use_smooth"))
print("  mesh.uv_layers.new   :", hasattr(me.uv_layers, "new"))
print("  bpy.ops.uv.smart_project:", hasattr(bpy.ops.uv, "smart_project"))
print("  bpy.ops.object.bake  :", hasattr(bpy.ops.object, "bake"))
print("  export_scene.fbx     :", hasattr(bpy.ops.export_scene, "fbx"))

print()
bad = [p for p in problems if p[1] != 0 or p[2] != 0]
if bad:
    print("НЕГЕРМЕТИЧНО или non-manifold:", [p[0] for p in bad])
else:
    print("OK: все оболочки замкнуты, non-manifold рёбер нет")

total = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print(f"объектов={len([o for o in bpy.data.objects if o.type=='MESH'])} граней всего={total}")
