"""(v2 detail) Cockpit for the FP sim: floor, bulkheads, instrument panel + gauges (UV-mapped to T_Gauges),
radios, switches, yokes, pedals, pedestal/levers, trim wheel, seats, compass.
Moving parts are separate objects named after their UE bone, pivots on their real axes (Blender build frame).
Reads out/plane_geo_v2.blend, writes out/plane_v2.blend (+ out/cockpit_rig.json)."""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import *
import layout as LY

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo_v2.blend'))
CP = coll('Cockpit')
COLORS = {
    'src_CP_Panel': (0.022, 0.023, 0.025), 'src_CP_Metal': (0.10, 0.10, 0.10), 'src_CP_Black': (0.008, 0.008, 0.008),
    'src_CP_Seat': (0.11, 0.085, 0.055), 'src_CP_Floor': (0.03, 0.03, 0.03), 'src_CP_Needle': (0.9, 0.9, 0.88),
    'src_CP_GaugeGlass': (0.6, 0.6, 0.6), 'src_CP_KnobRed': (0.6, 0.04, 0.03), 'src_CP_KnobBlue': (0.03, 0.12, 0.5),
    'src_CP_Orange': (0.9, 0.35, 0.02), 'src_CP_Bulkhead': (0.07, 0.075, 0.07),
    'src_CP_Leather': (0.10, 0.07, 0.045), 'src_CP_Strap': (0.02, 0.025, 0.03), 'src_CP_Rubber': (0.012, 0.012, 0.012),
    'src_CP_Chrome': (0.6, 0.6, 0.6), 'src_CP_Trim': (0.13, 0.13, 0.125), 'src_CP_Net': (0.03, 0.03, 0.03),
    'src_CP_Lens': (0.8, 0.8, 0.75), 'src_CP_Headset': (0.02, 0.02, 0.022), 'src_CP_Glare': (0.016, 0.016, 0.017),
    'src_CP_Annun': (0.08, 0.06, 0.03), 'M_Light_Cabin': (1.0, 0.85, 0.62),
}
M = {}
for k, c in COLORS.items():
    m = bpy.data.materials.get(k) or bpy.data.materials.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m
gauge_img = bpy.data.images.load(os.path.join(HERE, 'tex', 'v2', 'T_Gauges_BC.png'), check_existing=True)
MG = bpy.data.materials.get('src_CP_Gauges') or bpy.data.materials.new('src_CP_Gauges')
MG.diffuse_color = (0.2, 0.2, 0.2, 1)
MG['image'] = gauge_img.name
M['src_CP_Gauges'] = MG
M['src_CP_Annun']['image'] = gauge_img.name          # lamps sample the same atlas (blockout preview)
MATS = list(M.values())
MI = {m.name: i for i, m in enumerate(MATS)}

RIG = {}          # bone -> dict(pivot, parent, axis_blender, note)
STATIC = []       # static cockpit objects


def mk(name, bm, pivot=None, parent='Cockpit', axis='', note='', smooth=35):
    fix_normals_keep_uv(bm)
    ob = obj_from_bm(name, bm, CP, MATS)
    shade(ob, smooth)
    if pivot is None:
        STATIC.append(ob.name)
    else:
        set_pivot(ob, pivot)
        RIG[name] = dict(pivot=list(pivot), parent=parent, axis=axis, note=note)
    return ob


def plate_layer(bm):
    return bm.faces.layers.int.get('plate') or bm.faces.layers.int.new('plate')


def fix_normals_keep_uv(bm):
    lay = plate_layer(bm)
    solid = [f for f in bm.faces if f[lay] == 0]
    bmesh.ops.recalc_face_normals(bm, faces=solid)
    for f in bm.faces:
        if f[lay] == 1:
            f.normal_update()
            if f.normal.y < 0:
                f.normal_flip()


def box_rx(bm, center, size, rx, mat, bevel=0.0, segs=1):
    tmp = bmesh.new()
    box(tmp, (0, 0, 0), size, mat=mat, bevel=bevel, bevel_segs=segs)
    T = Matrix.Translation(Vector(center)) @ Matrix.Rotation(math.radians(rx), 4, 'X')
    bmesh.ops.transform(tmp, matrix=T, verts=tmp.verts)
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def disc(bm, center, r, y, segs=32, mat=0, uv_cell=None, uv_scale=1.0, facing=+1):
    """flat disc in the X-Z plane at depth y, facing +Y (towards the pilot). Optional UV to atlas cell."""
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    cx, cz = center
    c = bm.verts.new((cx, y, cz))
    ring = [bm.verts.new((cx + r * math.cos(2 * PI * i / segs), y, cz + r * math.sin(2 * PI * i / segs)))
            for i in range(segs)]
    faces = []
    for i in range(segs):
        f = bm.faces.new((c, ring[(i + 1) % segs], ring[i]))
        f.material_index = mat
        f[pl] = 1
        faces.append(f)
    if uv_cell is not None:
        col, row = uv_cell % 8, uv_cell // 8
        for f in faces:
            for lp in f.loops:
                dx = (lp.vert.co.x - cx) / r
                dz = (lp.vert.co.z - cz) / r
                # pilot looks towards -Y: his right is -X
                u = (col + 0.5 - dx * 0.5 * uv_scale) / 8
                v = 1 - (row + 0.5 - dz * 0.5 * uv_scale) / 4
                lp[uvl].uv = (u, v)
    return faces


def annulus(bm, center, r0, r1, y, segs=32, mat=0, uv_cell=None):
    cx, cz = center
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    inner = [bm.verts.new((cx + r0 * math.cos(2 * PI * i / segs), y, cz + r0 * math.sin(2 * PI * i / segs)))
             for i in range(segs)]
    outer = [bm.verts.new((cx + r1 * math.cos(2 * PI * i / segs), y, cz + r1 * math.sin(2 * PI * i / segs)))
             for i in range(segs)]
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
        f.material_index = mat
        f[pl] = 1
        if uv_cell is not None:
            col, row = uv_cell % 8, uv_cell // 8
            for lp in f.loops:
                dx = (lp.vert.co.x - cx) / r1
                dz = (lp.vert.co.z - cz) / r1
                lp[uvl].uv = ((col + 0.5 - dx * 0.5) / 8, 1 - (row + 0.5 - dz * 0.5) / 4)


def rect_uv(bm, x0, x1, z0, z1, y, mat, u0, u1, v0, v1):
    """rectangle facing +Y; x0 is the pilot-left edge (larger X)."""
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    vs = [bm.verts.new(p) for p in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))]
    f = bm.faces.new(vs)
    f.material_index = mat
    f[pl] = 1
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        lp[uvl].uv = uv
    f.normal_update()
    if f.normal.y < 0:
        f.normal_flip()
    return f


def needle_mesh(bm, cx, cz, y, length, angle_deg, width, mat, tail=0.18):
    """flat needle in the X-Z plane; angle clockwise from 12 o'clock as seen by the pilot (right = -X)."""
    a = math.radians(angle_deg)
    d = Vector((-math.sin(a), 0, math.cos(a)))
    s = Vector((math.cos(a), 0, math.sin(a)))
    base = Vector((cx, y, cz))
    pl = plate_layer(bm)
    pts = [base - d * length * tail + s * width * 0.5, base + d * length * 0.92 + s * width * 0.25,
           base + d * length, base + d * length * 0.92 - s * width * 0.25, base - d * length * tail - s * width * 0.5]
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    f.material_index = mat
    f[pl] = 1
    cylinder(bm, base + Vector((0, 0.0005, 0)), base + Vector((0, 0.003, 0)), width * 0.9, width * 0.9, 12, mat=MI['src_CP_Black'])


