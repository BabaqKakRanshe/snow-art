"""Texture labels vs 3D controls: text boxes from gen_tex (pxfont.BOXES) mapped through the face quads' real UVs into the
shed frame; control footprints projected onto the panel planes; overlaps and nearest-label listing."""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
import numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
import pxfont as F
import gen_tex as GT
OUT = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/review_gen/tex'
F.BOXES = []
GT.build(OUT)
boxes = list(F.BOXES)
N = GT.N


def face_map(objname, region):
    """return f(px, py) -> world point using the quad of `objname` whose UVs span the region"""
    o = bpy.data.objects[objname]
    me = o.data
    uvl = me.uv_layers['PSX'].data
    x0, y0, x1, y1 = GT.REG[region]
    best = None
    for p in me.polygons:
        if len(p.loop_indices) != 4:
            continue
        uvs = [Vector(uvl[l].uv) for l in p.loop_indices]
        pts = [o.matrix_world @ me.vertices[me.loops[l].vertex_index].co for l in p.loop_indices]
        us = [u.x * N for u in uvs]
        vs = [(1 - u.y) * N for u in uvs]
        if min(us) > x0 - 1 and max(us) < x1 + 1 and min(vs) > y0 - 1 and max(vs) < y1 + 1 and max(us) - min(us) > (x1 - x0) * 0.9:
            best = (uvs, pts)
    uvs, pts = best
    # affine map from (px, py) to world using 3 corners
    A = np.array([[uvs[i].x * N, (1 - uvs[i].y) * N, 1] for i in range(3)])
    W = np.array([list(pts[i]) for i in range(3)])
    M = np.linalg.solve(A, W)
    return lambda px, py: Vector(np.array([px, py, 1.0]) @ M)


panels = {
    'gpanel': dict(face='GPanel_Face', to2d=lambda p: (-(p.y - (-0.25)), p.z - 1.04), parts=[
        'Gen_Key', 'Gen_GlowButton', 'Gen_StopButton', 'Gen_EStop', 'Gen_VAdj', 'GLamp_GLOW', 'GLamp_CHG', 'GLamp_OIL',
        'GLamp_TEMP', 'GLamp_RUN', 'Needle_Oil', 'Needle_Temp', 'Needle_Batt', 'Needle_GenV', 'Needle_GenA', 'Needle_GenHz']),
    'board': dict(face='Board_Face', to2d=lambda p: (-(p.x - (-1.45)), p.z - 0.95), parts=[
        'Board_Changeover', 'Board_Brk_Gen', 'Board_Brk_Line'] + ['Board_MCB_%d' % i for i in range(1, 9)] +
        ['BLamp_LINE', 'BLamp_GEN', 'BLamp_OVERLOAD', 'Needle_BoardV', 'Needle_BoardA', 'Needle_BoardHz']),
}
for reg, P in panels.items():
    fm = face_map(P['face'], reg)
    x0, y0, x1, y1 = GT.REG[reg]
    labs = []
    for (bx0, by0, bx1, by1, txt) in boxes:
        if bx0 >= x0 and bx1 < x1 and by0 >= y0 and by1 < y1:
            a = P['to2d'](fm(bx0, by0))
            b = P['to2d'](fm(bx1 + 1, by1 + 1))
            labs.append((txt, min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])))
    # verify the map against GT._p for one control
    W, H = (GT.GP_W, GT.GP_H) if reg == 'gpanel' else (GT.BD_W, GT.BD_H)
    print('====', reg, 'labels', len(labs))
    foot = {}
    for nm in P['parts']:
        o = bpy.data.objects[nm]
        pts = [P['to2d'](o.matrix_world @ v.co) for v in o.data.vertices]
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        foot[nm] = (min(us), max(us), min(vs), max(vs))
    for txt, lu0, lu1, lv0, lv1 in labs:
        # nearest control centre
        best = min(foot.items(), key=lambda kv: math.hypot((kv[1][0] + kv[1][1]) / 2 - (lu0 + lu1) / 2,
                                                           (kv[1][2] + kv[1][3]) / 2 - (lv0 + lv1) / 2))
        hits = [nm for nm, (a, b, c, d) in foot.items() if a < lu1 and b > lu0 and c < lv1 and d > lv0 and not nm.startswith('Needle')]
        print(f'  {txt!r:22s} u {lu0:+.3f}..{lu1:+.3f} v {lv0:.3f}..{lv1:.3f}  nearest {best[0]}' + (f'  OVERLAPS {hits}' if hits else ''))
    for nm, (a, b, c, d) in foot.items():
        print(f'  part {nm:18s} footprint u {a:+.3f}..{b:+.3f} v {c:.3f}..{d:.3f}')
