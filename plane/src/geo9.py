"""v9 mesh builder: bmesh primitives with per-loop metric UVs (1 UV unit = 1 m on the surface) and face attributes
  fz  = surface zone (what the texture painter puts there: canvas, tube, steel ...), see ZONES in ext_v9.py
  isl = island id (one per primitive part; the packer keeps islands unrotated, the painter knows their orientation)
All islands are non-mirrored (UV winding = face winding). Texture directions: tubes run along V (brushing marks),
straps along V (webbing ribs), canvas is isotropic.
Build frame: x left, y aft, z up (m)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion

TAU = 2 * math.pi


class MB:
    GLOBAL = 0                      # island ids are unique across all builders: each island gets its own UV offset,
    SPACING = 2.5                   # so unrelated islands never overlap before packing (pack merges only true copies)

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.fz = self.bm.faces.layers.int.new('fz')
        self.isl = self.bm.faces.layers.int.new('isl')
        self.n_isl = 0
        self.zone = 0

    def island(self):
        MB.GLOBAL += 1
        self.n_isl += 1
        return MB.GLOBAL

    def v(self, p):
        return self.bm.verts.new(Vector(p))

    def face(self, verts, uvs, isl, zone=None, smooth=True):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        ox, oy = (isl % 400) * MB.SPACING, (isl // 400) * MB.SPACING
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = (uv[0] + ox, uv[1] + oy)
        f[self.fz] = self.zone if zone is None else zone
        f[self.isl] = isl
        f.smooth = smooth
        return f

    # ------------------------------------------------------------------ tubes
    def tube(self, path, r, segs=8, cap0=True, cap1=True, zone=None, up=Vector((0, 0, 1)), v0=0.0, phase=0.0,
             rfun=None):
        """circle swept along a polyline (parallel-transport frames, no twist; round the corners with fillet()).
        UV: u around (m, at radius r), v along (m). rfun(k) -> radius at ring k (optional)."""
        P = [Vector(p) for p in path]
        n = len(P)
        T = []
        for k in range(n):
            if k == 0:
                t = P[1] - P[0]
            elif k == n - 1:
                t = P[-1] - P[-2]
            else:
                t = (P[k + 1] - P[k]).normalized() + (P[k] - P[k - 1]).normalized()
            T.append(t.normalized())
        up = Vector(up)
        n0 = up - T[0] * up.dot(T[0])
        if n0.length < 1e-6:
            alt = Vector((1, 0, 0)) if abs(T[0].x) < 0.9 else Vector((0, 1, 0))
            n0 = alt - T[0] * alt.dot(T[0])
        N = [n0.normalized()]
        for k in range(1, n):
            q = T[k - 1].rotation_difference(T[k])
            nk = q @ N[-1]
            nk = (nk - T[k] * nk.dot(T[k])).normalized()
            N.append(nk)
        vs = [v0]
        for k in range(1, n):
            vs.append(vs[-1] + (P[k] - P[k - 1]).length)
        rings = []
        for k in range(n):
            B = T[k].cross(N[k])
            rk = rfun(k) if rfun else r
            rings.append([self.v(P[k] + (N[k] * math.cos(TAU * i / segs + phase) +
                                         B * math.sin(TAU * i / segs + phase)) * rk) for i in range(segs)])
        isl = self.island()
        circ = TAU * r
        for k in range(n - 1):
            A, Bv = rings[k], rings[k + 1]
            for i in range(segs):
                j = (i + 1) % segs
                u0, u1 = circ * i / segs, circ * (i + 1) / segs
                self.face([A[i], A[j], Bv[j], Bv[i]], [(u0, vs[k]), (u1, vs[k]), (u1, vs[k + 1]), (u0, vs[k + 1])],
                          isl, zone)
        for cap, k in ((cap0, 0), (cap1, n - 1)):
            if not cap:
                continue
            ring = rings[k]
            B = T[k].cross(N[k])
            rk = rfun(k) if rfun else r
            uvs = [((vv.co - P[k]).dot(N[k]) + rk, (vv.co - P[k]).dot(B) + rk) for vv in ring]
            if k == 0:                                   # faces -T: reverse the ring, mirror u to stay CCW in UV
                order = list(reversed(range(segs)))
                uvs = [(2 * rk - u, v) for u, v in uvs]
            else:
                order = list(range(segs))
            self.face([ring[i] for i in order], [uvs[i] for i in order], self.island(), zone, smooth=False)
        return rings, vs[-1]

    # ------------------------------------------------------------------ lathe (bushings, nuts, feet, knobs)
    def lathe(self, origin, axis, profile, segs=12, zone=None, ref=None, cap0=True, cap1=True, phase=0.0,
              smooth=True):
        """profile [(h, r)] along axis from origin (h increasing). UV: u around (m, at the mean radius),
        v = profile arc length (m)."""
        o, ax = Vector(origin), Vector(axis).normalized()
        ref = Vector(ref) if ref is not None else (Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0)))
        e1 = (ref - ax * ref.dot(ax)).normalized()
        e2 = ax.cross(e1)
        rings = []
        for h, r in profile:
            rings.append([self.v(o + ax * h + (e1 * math.cos(TAU * i / segs + phase) +
                                               e2 * math.sin(TAU * i / segs + phase)) * r) for i in range(segs)])
        rm = sum(r for _, r in profile) / len(profile)
        circ = TAU * max(rm, 1e-4)
        vs = [0.0]
        for (h0, r0), (h1, r1) in zip(profile[:-1], profile[1:]):
            vs.append(vs[-1] + math.hypot(h1 - h0, r1 - r0))
        isl = self.island()
        for k in range(len(profile) - 1):
            A, Bv = rings[k], rings[k + 1]
            for i in range(segs):
                j = (i + 1) % segs
                u0, u1 = circ * i / segs, circ * (i + 1) / segs
                self.face([A[i], A[j], Bv[j], Bv[i]], [(u0, vs[k]), (u1, vs[k]), (u1, vs[k + 1]), (u0, vs[k + 1])],
                          isl, zone, smooth)
        for cap, k in ((cap0, 0), (cap1, len(profile) - 1)):
            r = profile[k][1]
            if not cap or r < 1e-6:
                continue
            ring = rings[k]
            c = o + ax * profile[k][0]
            uvs = [((vv.co - c).dot(e1) + r, (vv.co - c).dot(e2) + r) for vv in ring]
            if k == 0:
                order = list(reversed(range(segs)))
                uvs = [(2 * r - u, v) for u, v in uvs]
            else:
                order = list(range(segs))
            self.face([ring[i] for i in order], [uvs[i] for i in order], self.island(), zone, smooth=False)
        return rings

    # ------------------------------------------------------------------ box (oriented), each face its own island
    def box(self, center, size, rot=None, zone=None, smooth=False):
        c = Vector(center)
        R = rot if rot is not None else Matrix.Identity(3)
        hx, hy, hz = (s / 2 for s in size)
        corners = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    corners[(sx, sy, sz)] = self.v(c + R @ Vector((sx * hx, sy * hy, sz * hz)))
        quads = [((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)), ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)),
                 ((1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)), ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
                 ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), ((-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1))]
        for q in quads:
            vs = [corners[k] for k in q]
            lu = (vs[1].co - vs[0].co).length
            lv = (vs[3].co - vs[0].co).length
            self.face(vs, [(0, 0), (lu, 0), (lu, lv), (0, lv)], self.island(), zone, smooth)
        return corners

    # ------------------------------------------------------------------ plate: 2D outline extruded along its normal
    def plate(self, origin, ex, ey, outline, thick, zone=None, side_zone=None, smooth_sides=False):
        """outline [(x, y)] CCW in the (ex, ey) frame at origin; extruded by thick along ez = ex x ey."""
        o, ex, ey = Vector(origin), Vector(ex).normalized(), Vector(ey).normalized()
        ez = ex.cross(ey)
        area2 = sum(outline[i][0] * outline[(i + 1) % len(outline)][1] - outline[(i + 1) % len(outline)][0] *
                    outline[i][1] for i in range(len(outline)))
        if area2 < 0:
            outline = list(reversed(outline))
        top = [self.v(o + ex * x + ey * y + ez * thick) for x, y in outline]
        bot = [self.v(o + ex * x + ey * y) for x, y in outline]
        self.face(top, [(x, y) for x, y in outline], self.island(), zone, smooth=False)
        self.face(list(reversed(bot)), [(-x, y) for x, y in reversed(outline)], self.island(), zone, smooth=False)
        isl = self.island()
        n = len(outline)
        s = 0.0
        for i in range(n):
            j = (i + 1) % n
            L = math.dist(outline[i], outline[j])
            self.face([bot[i], bot[j], top[j], top[i]], [(s, 0), (s + L, 0), (s + L, thick), (s, thick)], isl,
                      side_zone if side_zone is not None else zone, smooth_sides)
            s += L
        return top, bot

    # ------------------------------------------------------------------ grid surface P(s, t)
    def grid(self, P, s_vals, t_vals, zone=None, closed_t=False, flip=False, smooth=True, outward=None):
        """quads between rows (s) and columns (t); UV = arc length measured on the surface along s (u) and t (v).
        flip reverses the faces (normal) and mirrors u so the island stays non-mirrored.
        outward(p, s, t) -> reference direction: when given, flip is decided from the majority of the faces."""
        if outward is not None:
            votes = 0
            for i in range(len(s_vals) - 1):
                for j in range(len(t_vals) - 1 if not closed_t else len(t_vals)):
                    jj = (j + 1) % len(t_vals)
                    q0, q1 = Vector(P(s_vals[i], t_vals[j])), Vector(P(s_vals[i + 1], t_vals[j]))
                    q3 = Vector(P(s_vals[i], t_vals[jj]))
                    n = (q1 - q0).cross(q3 - q0)
                    if n.length > 1e-12:
                        sm, tm = (s_vals[i] + s_vals[i + 1]) / 2, t_vals[j]
                        votes += 1 if n.dot(Vector(outward((q0 + q1 + q3) / 3, sm, tm))) > 0 else -1
            flip = votes < 0
        rows = [[self.v(P(s, t)) for t in t_vals] for s in s_vals]
        U = [[0.0] * len(t_vals) for _ in s_vals]
        V = [[0.0] * len(t_vals) for _ in s_vals]
        for i in range(len(s_vals)):
            for j in range(1, len(t_vals)):
                V[i][j] = V[i][j - 1] + (rows[i][j].co - rows[i][j - 1].co).length
        for j in range(len(t_vals)):
            for i in range(1, len(s_vals)):
                U[i][j] = U[i - 1][j] + (rows[i][j].co - rows[i - 1][j].co).length
        if closed_t:
            V = [r + [r[-1] + (rows[i][0].co - rows[i][-1].co).length] for i, r in enumerate(V)]
        isl = self.island()
        nt = len(t_vals) if closed_t else len(t_vals) - 1
        for i in range(len(s_vals) - 1):
            for j in range(nt):
                jj = (j + 1) % len(t_vals)
                jv = j + 1                                     # UV column (no wrap: seam keeps its own v)
                q = [rows[i][j], rows[i + 1][j], rows[i + 1][jj], rows[i][jj]]
                uv = [(U[i][j], V[i][j]), (U[i + 1][j], V[i + 1][j]), (U[i + 1][jj], V[i + 1][jv]),
                      (U[i][jj], V[i][jv])]
                if flip:
                    q, uv = q[::-1], [(-u, v) for u, v in uv[::-1]]
                self.face(q, uv, isl, zone, smooth)
        return rows

    # ------------------------------------------------------------------ closed slab around a mid-surface
    def slab(self, P, N, s_vals, t_vals, th, zone=None, smooth=True):
        """closed thin shell: P(s, t) mid-surface, N(s, t) unit normal of the top side, thickness th.
        Top, bottom and the four edge strips, all facing outwards."""
        def off(k):
            return lambda s, t: Vector(P(s, t)) + Vector(N(s, t)) * (k * th / 2)
        top = self.grid(off(1), s_vals, t_vals, zone, smooth=smooth, outward=lambda p, s, t: Vector(N(s, t)))
        bot = self.grid(off(-1), s_vals, t_vals, zone, smooth=smooth, outward=lambda p, s, t: -Vector(N(s, t)))
        # edges: strips between top and bottom along the four borders, facing away from the slab centre
        cs, ct = (s_vals[0] + s_vals[-1]) / 2, (t_vals[0] + t_vals[-1]) / 2
        c = Vector(P(cs, ct))
        for sv in (s_vals[0], s_vals[-1]):
            self.grid(lambda a, b, sv=sv: Vector(P(sv, b)) + Vector(N(sv, b)) * (a * th / 2), [-1, 1], t_vals, zone,
                      smooth=False, outward=lambda p, s, t, sv=sv: Vector(P(sv, ct)) - c)
        for tv in (t_vals[0], t_vals[-1]):
            self.grid(lambda a, b, tv=tv: Vector(P(a, tv)) + Vector(N(a, tv)) * (b * th / 2), s_vals, [-1, 1], zone,
                      smooth=False, outward=lambda p, s, t, tv=tv: Vector(P(cs, tv)) - c)
        return top, bot

    def fan(self, center, ring, outward, zone=None, smooth=False):
        """triangle fan from center to a closed ring of points, facing `outward` (a vector)"""
        cv = self.v(center)
        vs = [self.v(p) for p in ring]
        n = len(ring)
        ow = Vector(outward)
        e1 = (Vector(ring[0]) - Vector(center))
        e1 = (e1 - ow.normalized() * e1.dot(ow.normalized())).normalized()
        e2 = ow.normalized().cross(e1)
        isl = self.island()
        uv = lambda p: ((Vector(p) - Vector(center)).dot(e1), (Vector(p) - Vector(center)).dot(e2))
        for j in range(n):
            k = (j + 1) % n
            a, b = Vector(ring[j]), Vector(ring[k])
            if (a - Vector(center)).cross(b - Vector(center)).dot(ow) >= 0:
                self.face([cv, vs[j], vs[k]], [uv(center), uv(a), uv(b)], isl, zone, smooth)
            else:
                self.face([cv, vs[k], vs[j]], [uv(center), uv(b), uv(a)], isl, zone, smooth)
        return cv, vs

    # ------------------------------------------------------------------ strap: ribbon along a path (width x thick)
    def strap(self, path, side_dirs, width, thick, zone=None, ends=True, edges=True):
        """path points, side_dirs[k] = unit vector across the strap at point k; the thickness goes along
        up = side x tangent (the top face faces up). UV: u across (m), v along (m)."""
        P = [Vector(p) for p in path]
        n = len(P)
        T = [(P[min(k + 1, n - 1)] - P[max(k - 1, 0)]).normalized() for k in range(n)]
        rows = []
        for k in range(n):
            sd = Vector(side_dirs[k])
            sd = (sd - T[k] * sd.dot(T[k])).normalized()
            upv = sd.cross(T[k]).normalized()
            a, b = P[k] - sd * width / 2, P[k] + sd * width / 2
            rows.append([self.v(a + upv * thick / 2), self.v(b + upv * thick / 2), self.v(b - upv * thick / 2),
                         self.v(a - upv * thick / 2)])
        vs = [0.0]
        for k in range(1, n):
            vs.append(vs[-1] + (P[k] - P[k - 1]).length)
        top, bot, e1, e2 = self.island(), self.island(), self.island(), self.island()
        for k in range(n - 1):
            A, B = rows[k], rows[k + 1]
            v0, v1 = vs[k], vs[k + 1]
            self.face([A[0], A[1], B[1], B[0]], [(0, v0), (width, v0), (width, v1), (0, v1)], top, zone)
            self.face([A[2], A[3], B[3], B[2]], [(0, v0), (width, v0), (width, v1), (0, v1)], bot, zone)
            if edges:
                self.face([A[1], A[2], B[2], B[1]], [(0, v0), (thick, v0), (thick, v1), (0, v1)], e1, zone)
                self.face([A[3], A[0], B[0], B[3]], [(0, v0), (thick, v0), (thick, v1), (0, v1)], e2, zone)
        if ends:
            for R, first in ((rows[0], True), (rows[-1], False)):
                q = [R[0], R[1], R[2], R[3]]
                uv = [(0, thick), (width, thick), (width, 0), (0, 0)]
                if first:
                    q, uv = q[::-1], [(width - u, v) for u, v in uv[::-1]]
                self.face(q, uv, self.island(), zone, smooth=False)
        return rows, vs[-1]

    # ------------------------------------------------------------------ finish
    def to_object(self, name, coll, mats, sharp_deg=50.0):
        bm = self.bm
        bm.normal_update()
        lim = math.radians(sharp_deg)
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) != 2:
                e.smooth = False
            elif not (lf[0].smooth and lf[1].smooth):
                e.smooth = False
            else:
                e.smooth = e.calc_face_angle(0.0) < lim
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        for m in mats:
            me.materials.append(m)
        return ob


def fillet(points, radius, n_arc=4):
    """polyline corners rounded with arcs of the given radius (n_arc segments per arc)"""
    P = [Vector(p) for p in points]
    out = [P[0]]
    for k in range(1, len(P) - 1):
        a, b, c = P[k - 1], P[k], P[k + 1]
        d1, d2 = (a - b).normalized(), (c - b).normalized()
        ang = d1.angle(d2)
        if ang > math.pi - 1e-3 or radius <= 0:
            out.append(b)
            continue
        tlen = radius / math.tan(ang / 2)
        p1, p2 = b + d1 * tlen, b + d2 * tlen
        bis = (d1 + d2).normalized()
        cen = b + bis * (radius / math.sin(ang / 2))
        v1, v2 = p1 - cen, p2 - cen
        axis = v1.cross(v2).normalized()
        total = v1.angle(v2)
        for i in range(n_arc + 1):
            out.append(cen + Quaternion(axis, total * i / n_arc) @ v1)
    out.append(P[-1])
    return out


def mirror_x_mesh(me):
    """mirror mesh data across x = 0 (geometry flipped, winding and UV islands kept non-mirrored)"""
    me.transform(Matrix.Scale(-1, 4, Vector((1, 0, 0))))
    me.flip_normals()
    # flip_normals reverses the loop order; the UVs travel with their loops, so the UV winding flips with the face:
    # mirror u per island back (u -> -u) so islands stay non-mirrored (the packer re-places them anyway)
    uvl = me.uv_layers[0].data
    for d in uvl:
        d.uv = (-d.uv[0], d.uv[1])
    me.update()
