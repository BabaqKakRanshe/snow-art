"""Panel flood lamp fixtures (v11): the two red floods (Light_Flood, Light_Flood_2) get a visible lamp - a short black
housing on an arm from the glareshield lip edge, lens at the light's origin, facing down-forward onto the panel.

Geometry is written in the BUILD frame of the source scenes (Blender: x left, y aft, z up, metres; Unity
(x, y, z) = (-xb, zb, -yb)), level pose, as one mesh object (default name 'CP_PanelFloods') with two material slots:
  0 = the glareshield's material (M_Cockpit; UVs inside a flat dark patch of the glareshield's own UV island)
  1 = M_Light_Cabin (lens discs; the export splits them into Lens_Flood_L / Lens_Flood_R)
make_panel_floods(name, mat_body, mat_lens, uv_patch) -> object (not linked to any collection)."""
import bpy, bmesh, math
from mathutils import Vector

# lamp origins and beam axis in Unity plane coordinates (= UtilityPlaneRig LightDefs Flood / Flood_2)
LAMPS = {'L': (-0.30, 2.010, 2.865), 'R': (0.30, 2.010, 2.865)}
AXIS = (0.0, -0.966, 0.259)                  # down and 15 deg forward, onto the panel face
LIP_Z = 2.9425                               # aft face of the glareshield lip (CP_Glareshield z min 2.943)
R_BODY, R_LENS, R_BEZEL = 0.0115, 0.0095, 0.0132
L_BODY, RIM, BEZEL_L = 0.032, 0.003, 0.004
SEG = 16


def U2B(p):
    return Vector((-p[0], -p[2], p[1]))


def make_panel_floods(name, mat_body, mat_lens, uv_patch):
    """uv_patch: (u0, v0, size) - square in the body material's UV space every body face is mapped into."""
    a_u = Vector(AXIS).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    lens_faces = []

    def body_uv(f):
        u0, v0, s = uv_patch
        n = len(f.loops)
        for i, lp in enumerate(f.loops):
            ang = 2 * math.pi * i / n
            lp[uvl].uv = (u0 + s * (0.5 + 0.5 * math.cos(ang)), v0 + s * (0.5 + 0.5 * math.sin(ang)))

    for side, Lp in LAMPS.items():
        L = Vector(Lp)
        uaxis = Vector((1.0, 0.0, 0.0))                                   # lateral
        vaxis = a_u.cross(uaxis).normalized()                             # completes the frame (in the y-z plane)

        def ring(center, r):
            return [bm.verts.new(U2B(center + r * (math.cos(2 * math.pi * k / SEG) * uaxis +
                                                   math.sin(2 * math.pi * k / SEG) * vaxis))) for k in range(SEG)]

        front = L + RIM * a_u                                             # housing rim, 3 mm past the lens
        back = L - L_BODY * a_u
        bz0 = front + 0.0 * a_u
        bz1 = front - BEZEL_L * a_u
        r_front_out = ring(bz0, R_BEZEL)                                  # bezel (slightly wider front ring)
        r_front_in = ring(bz0, R_LENS + 0.0008)
        r_bez_back = ring(bz1, R_BEZEL)
        r_body_front = ring(bz1, R_BODY)
        r_body_back = ring(back, R_BODY)
        r_lens_wall = ring(L, R_LENS + 0.0008)                            # short inner wall down to the lens
        lens_ring = ring(L, R_LENS)
        c_back = bm.verts.new(U2B(back))
        c_lens = bm.verts.new(U2B(L))
        body = []
        for k in range(SEG):
            k1 = (k + 1) % SEG
            body.append(bm.faces.new((r_front_out[k], r_front_out[k1], r_front_in[k1], r_front_in[k])))        # rim face
            body.append(bm.faces.new((r_front_out[k1], r_front_out[k], r_bez_back[k], r_bez_back[k1])))        # bezel side
            body.append(bm.faces.new((r_bez_back[k1], r_bez_back[k], r_body_front[k], r_body_front[k1])))      # step
            body.append(bm.faces.new((r_body_front[k1], r_body_front[k], r_body_back[k], r_body_back[k1])))    # body
            body.append(bm.faces.new((r_body_back[k1], r_body_back[k], c_back)))                               # back cap
            body.append(bm.faces.new((r_front_in[k], r_front_in[k1], r_lens_wall[k1], r_lens_wall[k])))         # inner wall
            body.append(bm.faces.new((r_lens_wall[k], r_lens_wall[k1], lens_ring[k1], lens_ring[k])))           # lens edge
            lens_faces.append(bm.faces.new((lens_ring[k], lens_ring[k1], c_lens)))                             # lens
        # arm: from the housing's forward side near the back end to the lip face, 8 x 4 mm bar, + mounting plate
        n_fwd = Vector((0.0, -a_u.z, a_u.y)).normalized()                 # perpendicular to the axis, pointing +z
        if n_fwd.z < 0:
            n_fwd = -n_fwd
        p0 = back + 0.010 * a_u + (R_BODY - 0.002) * n_fwd
        p1 = Vector((L.x, p0.y + 0.004, LIP_Z - 0.003))
        d = (p1 - p0).normalized()
        w = Vector((1.0, 0.0, 0.0)) * 0.004                               # half width (lateral)
        h = d.cross(Vector((1.0, 0.0, 0.0))).normalized() * 0.002          # half thickness
        q = [bm.verts.new(U2B(p0 + sx * w + sy * h)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        e = [bm.verts.new(U2B(p1 + sx * w + sy * h)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for k in range(4):
            k1 = (k + 1) % 4
            body.append(bm.faces.new((q[k], q[k1], e[k1], e[k])))
        body.append(bm.faces.new((q[3], q[2], q[1], q[0])))
        pc = Vector((L.x, p1.y, LIP_Z - 0.0015))                           # plate on the lip face, 20 x 16 x 3 mm
        pw, ph, pt = 0.010, 0.008, 0.0015
        pv = [bm.verts.new(U2B(pc + Vector((sx * pw, sy * ph, sz * pt))))
              for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            body.append(bm.faces.new([pv[i] for i in f]))
        for f in body:
            f.material_index = 0
            body_uv(f)
    for f in lens_faces:
        f.material_index = 1
        for i, lp in enumerate(f.loops):
            lp[uvl].uv = (0.5 + 0.4 * math.cos(2 * math.pi * i / 3), 0.5 + 0.4 * math.sin(2 * math.pi * i / 3))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # the lens and the rim must face along the beam (down-forward): fix orientation if recalc flipped them
    beam_b = U2B(Vector(AXIS)) - U2B(Vector((0, 0, 0)))
    for f in lens_faces:
        if f.normal.dot(beam_b) < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_body)
    me.materials.append(mat_lens)
    # smooth cylinder walls, flat caps / rim / arm / plate (sharp edges where the face normals turn > 35 deg)
    for p in me.polygons:
        p.use_smooth = True
    me.validate()
    bm2 = bmesh.new(); bm2.from_mesh(me)
    for ed in bm2.edges:
        if len(ed.link_faces) != 2 or ed.calc_face_angle(0.0) > math.radians(35):
            ed.smooth = False
    bm2.to_mesh(me); bm2.free()
    ob = bpy.data.objects.new(name, me)
    return ob
