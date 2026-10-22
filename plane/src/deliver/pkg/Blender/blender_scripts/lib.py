"""Geometry helpers for the utility aircraft build (bpy 5.x, metric, Z-up, nose toward -Y)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler

PI = math.pi


# ---------------------------------------------------------------- scene / objects
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = 'METERS'
    return sc


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def obj_from_bm(name, bm, collection, mats=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if mats:
        for m in mats:
            me.materials.append(m)
    return ob


def empty(name, collection, loc=(0, 0, 0), size=0.3, kind='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    collection.objects.link(e)
    return e


def set_pivot(ob, pivot, rot=(0, 0, 0)):
    """Move object origin to world `pivot` with local rotation `rot` (euler XYZ radians),
    keeping geometry where it is. Object must not be parented yet."""
    R = Euler(rot, 'XYZ').to_matrix().to_4x4()
    M = Matrix.Translation(Vector(pivot)) @ R
    ob.data.transform(M.inverted())
    ob.matrix_world = M


def parent_keep(child, parent):
    mw = child.matrix_world.copy() if child.parent else child.matrix_basis.copy()
    child.parent = parent
    child.matrix_parent_inverse.identity()
    child.matrix_world = mw


def shade(ob, angle_deg=40.0, all_sharp=False):
    """Smooth faces, mark edges sharper than angle as sharp (stored in sharp_edge attr)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = math.radians(angle_deg)
    for f in bm.faces:
        f.smooth = not all_sharp
    for e in bm.edges:
        if len(e.link_faces) != 2:
            e.smooth = False
        else:
            e.smooth = e.calc_face_angle(0.0) < lim
    bm.to_mesh(me)
    bm.free()


# ---------------------------------------------------------------- bmesh builders
def loft(bm, rings, closed=True, cap0=True, cap1=True, mat=0):
    """Connect rings (lists of Vector, equal length) with quads. Returns list of vert rings."""
    vrings = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    faces = []
    for a, b in zip(vrings[:-1], vrings[1:]):
        rng = n if closed else n - 1
        for i in range(rng):
            j = (i + 1) % n
            vs = [a[i], a[j], b[j], b[i]]
            # skip degenerate (shared position) quads -> tris
            uniq = []
            for v in vs:
                if all((v.co - u.co).length > 1e-7 for u in uniq):
                    uniq.append(v)
            if len(uniq) >= 3:
                try:
                    f = bm.faces.new(uniq)
                    f.material_index = mat
                    faces.append(f)
                except ValueError:
                    pass
    if closed and cap0:
        f = bm.faces.new(list(reversed(vrings[0])))
        f.material_index = mat
    if closed and cap1:
        f = bm.faces.new(vrings[-1])
        f.material_index = mat
    return vrings


def fix_normals(bm):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def superellipse(hw, hh, n_exp, N, samples=1440):
    """Closed ring of N points (x,z) equally spaced by arc length, starting at (+hw,0), CCW."""
    pts = []
    for i in range(samples):
        t = 2 * PI * i / samples
        c, s = math.cos(t), math.sin(t)
        pts.append((hw * math.copysign(abs(c) ** (2 / n_exp), c),
                    hh * math.copysign(abs(s) ** (2 / n_exp), s)))
    pts.append(pts[0])
    cum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    L = cum[-1]
    out = []
    k = 0
    for i in range(N):
        target = L * i / N
        while cum[k + 1] < target:
            k += 1
        f = (target - cum[k]) / max(cum[k + 1] - cum[k], 1e-12)
        out.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * f,
                    pts[k][1] + (pts[k + 1][1] - pts[k][1]) * f))
    return out


def naca(m, p, t, xc):
    """NACA 4-digit: returns (xu, yu), (xl, yl) at chord fraction xc (closed TE)."""
    yt = 5 * t * (0.2969 * math.sqrt(max(xc, 0)) - 0.1260 * xc - 0.3516 * xc ** 2
                  + 0.2843 * xc ** 3 - 0.1036 * xc ** 4)
    if m == 0 or p == 0:
        yc, dyc = 0.0, 0.0
    elif xc < p:
        yc = m / p ** 2 * (2 * p * xc - xc ** 2)
        dyc = 2 * m / p ** 2 * (p - xc)
    else:
        yc = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xc - xc ** 2)
        dyc = 2 * m / (1 - p) ** 2 * (p - xc)
    th = math.atan(dyc)
    return ((xc - yt * math.sin(th), yc + yt * math.cos(th)),
            (xc + yt * math.sin(th), yc - yt * math.cos(th)))


def airfoil_ring(a, b, n, m=0.02, p=0.4, t=0.12, front=True):
    """2D closed ring (xc, yc) of the airfoil between chord fractions a..b.
    front=True: dense spacing at LE (a should be 0). Returns list of (xc, yc)."""
    if front:
        xs = [a + (b - a) * (1 - math.cos(0.5 * PI * i / (n - 1))) for i in range(n)]
    else:
        xs = [a + (b - a) * i / (n - 1) for i in range(n)]
    up = [naca(m, p, t, x)[0] for x in xs]
    lo = [naca(m, p, t, x)[1] for x in xs]
    if front:  # upper b->a(LE) then lower a->b ; LE shared
        ring = list(reversed(up)) + lo[1:]
    else:      # upper a->b(TE) then lower b->a ; TE shared
        ring = up + list(reversed(lo))[1:]
    return ring


def revolve(bm, profile, axis='Y', center=(0, 0, 0), segs=32, mat=0, close_ends=False, phase=0.0,
            radial_fn=None):
    """Revolve profile [(a, r)] (a = coordinate along axis, r = radius) around an axis through center.
    radial_fn(i_seg, j_prof, r) -> r' lets you modulate radius (tyre lugs)."""
    c = Vector(center)
    rings = []
    for i in range(segs):
        ang = 2 * PI * i / segs + phase
        ring = []
        for j, (a, r) in enumerate(profile):
            rr = radial_fn(i, j, r) if radial_fn else r
            if axis == 'Y':
                v = Vector((rr * math.sin(ang), a, rr * math.cos(ang)))
            elif axis == 'X':
                v = Vector((a, rr * math.sin(ang), rr * math.cos(ang)))
            else:
                v = Vector((rr * math.cos(ang), rr * math.sin(ang), a))
            ring.append(c + v)
        rings.append(ring)
    # rings are along the angle; connect ring i with i+1 (wrap), profile is open
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    faces = []
    for i in range(segs):
        A, B = vr[i], vr[(i + 1) % segs]
        for j in range(len(profile) - 1):
            vs = [A[j], A[j + 1], B[j + 1], B[j]]
            uniq = []
            for v in vs:
                if all((v.co - u.co).length > 1e-7 for u in uniq):
                    uniq.append(v)
            if len(uniq) >= 3:
                try:
                    f = bm.faces.new(uniq)
                    f.material_index = mat
                    faces.append(f)
                except ValueError:
                    pass
    if close_ends:
        for j in (0, len(profile) - 1):
            if profile[j][1] > 1e-6:
                f = bm.faces.new([vr[i][j] for i in range(segs)])
                f.material_index = mat
    return vr


def ring_frame(p0, tangent, up_hint=Vector((0, 0, 1))):
    t = tangent.normalized()
    if abs(t.dot(up_hint)) > 0.95:
        up_hint = Vector((1, 0, 0))
    side = t.cross(up_hint).normalized()
    up = side.cross(t).normalized()
    return side, up


def sweep(bm, path, rx, ry=None, segs=10, cap0=True, cap1=True, mat=0, up_hint=Vector((0, 0, 1))):
    """Sweep an ellipse (rx, ry may be callables of u in [0,1]) along a polyline path."""
    ry = ry if ry is not None else rx
    rings = []
    N = len(path)
    for k, p in enumerate(path):
        p = Vector(p)
        if k == 0:
            tng = Vector(path[1]) - p
        elif k == N - 1:
            tng = p - Vector(path[-2])
        else:
            tng = Vector(path[k + 1]) - Vector(path[k - 1])
        side, up = ring_frame(p, tng, up_hint)
        u = k / (N - 1)
        a = rx(u) if callable(rx) else rx
        b = ry(u) if callable(ry) else ry
        ring = []
        for i in range(segs):
            ang = 2 * PI * i / segs
            ring.append(p + side * (a * math.cos(ang)) + up * (b * math.sin(ang)))
        rings.append(ring)
    return loft(bm, rings, True, cap0, cap1, mat)


def box(bm, center, size, mat=0, bevel=0.0, bevel_segs=2):
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res['verts']
    for v in vs:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    faces = list({f for v in vs for f in v.link_faces})
    for f in faces:
        f.material_index = mat
    if bevel > 0:
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=bevel_segs, affect='EDGES',
                        profile=0.5, clamp_overlap=True)
    return vs


def cylinder(bm, p0, p1, r0, r1=None, segs=8, mat=0, caps=True):
    r1 = r0 if r1 is None else r1
    return sweep(bm, [p0, p1], lambda u: r0 + (r1 - r0) * u, None, segs, caps, caps, mat)


def bezier(p0, p1, p2, n):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2 for t in (i / (n - 1) for i in range(n))]


def add_triangulate(ob):
    m = ob.modifiers.new('Triangulate', 'TRIANGULATE')
    m.quad_method = 'BEAUTY'
    m.ngon_method = 'BEAUTY'
    m.keep_custom_normals = True
    return m
