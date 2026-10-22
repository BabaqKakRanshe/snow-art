"""Blender helpers for the van concept (plane-level build): mesh import, booleans, curves, lathe, materials,
bake to PSX, lights, cameras, renders.  Frame: x forward, y left, z up, metres."""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
MATS = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()


def link(ob, col=None):
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def mesh_np(name, v, f, col=None, m=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set('co', np.asarray(v, np.float32).ravel())
    f = np.asarray(f, np.int32)
    me.loops.add(f.size)
    me.loops.foreach_set('vertex_index', f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set('loop_start', np.arange(0, f.size, f.shape[1], dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(f), f.shape[1], np.int32))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    link(ob, col)
    if m:
        ob.data.materials.append(m)
    return ob


def from_bm(name, bm, m=None, col=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob, col)
    if m is not None:
        ob.data.materials.append(m)
    return ob


def select_only(ob):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    select_only(ob)
    for md in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)


def smooth(ob, angle=32):
    me = ob.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.set_sharp_from_angle(angle=math.radians(angle))


def decimate(ob, ratio):
    md = ob.modifiers.new('dec', 'DECIMATE')
    md.ratio = ratio
    md.use_collapse_triangulate = False
    apply_mods(ob)


def solidify(ob, t, offset=-1.0, mat_off=0, rim_off=0):
    md = ob.modifiers.new('sol', 'SOLIDIFY')
    md.thickness = t
    md.offset = offset
    md.use_even_offset = True
    md.material_offset = mat_off
    md.material_offset_rim = rim_off
    md.use_rim = True
    apply_mods(ob)


def bevel(ob, w, seg=2, angle=40):
    md = ob.modifiers.new('bv', 'BEVEL')
    md.width = w
    md.segments = seg
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(angle)
    apply_mods(ob)
    return ob


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        if name:
            objs[0].name = name
        return objs[0]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name:
        ob.name = name
    return ob


def boolean(ob, cutters, op='DIFFERENCE', keep=False):
    if not cutters:
        return ob
    cut = join([c for c in cutters], ob.name + '_cut')
    md = ob.modifiers.new('b', 'BOOLEAN')
    md.operation = op
    md.solver = 'EXACT'
    md.object = cut
    md.use_self = True
    md.use_hole_tolerant = True
    md.material_mode = 'TRANSFER'
    n0 = len(ob.data.vertices)
    apply_mods(ob)
    if not keep:
        bpy.data.objects.remove(cut, do_unlink=True)
    if n0 and not len(ob.data.vertices):
        raise RuntimeError('boolean emptied ' + ob.name)
    return ob if not keep else (ob, cut)


def box(name, x0, x1, y0, y1, z0, z1, m=None, col=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return from_bm(name, bm, m, col)


def cyl(name, c, axis, r, length, n=24, m=None, col=None, r2=None, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=n, radius1=r, radius2=r if r2 is None else r2, depth=length)
    rot = {'x': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'y': Matrix.Rotation(math.pi / 2, 4, 'X'),
           'z': Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ rot, verts=bm.verts)
    return from_bm(name, bm, m, col)


def prism(name, poly, axis, a0, a1, m=None, col=None):
    """2D polygon extruded: axis 'y' -> poly in (x, z); 'x' -> poly in (y, z); 'z' -> poly in (x, y)"""
    bm = bmesh.new()
    def P(u, v, a):
        return {'y': (u, a, v), 'x': (a, u, v), 'z': (u, v, a)}[axis]
    A = [bm.verts.new(P(u, v, a0)) for u, v in poly]
    B = [bm.verts.new(P(u, v, a1)) for u, v in poly]
    n = len(poly)
    bm.faces.new(A)
    bm.faces.new(B[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, m, col)


def rrect(u0, u1, v0, v1, r, seg=6):
    """rounded rectangle polygon (CCW) in (u, v)"""
    r = min(r, (u1 - u0) / 2 - 1e-4, (v1 - v0) / 2 - 1e-4)
    pts = []
    for cu, cv, a0 in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def offset_poly(poly, d):
    """naive inward offset of a convex CCW polygon by d (miter)"""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector((*poly[i - 1], 0)), Vector((*poly[i], 0)), Vector((*poly[(i + 1) % n], 0))
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x, 0))
        n2 = Vector((-e2.y, e2.x, 0))
        nb = (n1 + n2).normalized()
        cos = max(0.2, nb.dot(n1))
        q = p1 + nb * (d / cos)
        out.append((q.x, q.y))
    return out


def ring(name, poly, axis, a0, a1, t, m=None, col=None):
    """outline ring (frame / groove cutter): polygon minus its inward offset by t"""
    o = prism(name, poly, axis, a0, a1, m, col)
    i = prism(name + '_i', offset_poly(poly, t), axis, a0 - 0.05, a1 + 0.05)
    return boolean(o, [i])


def lathe(name, prof, axis='y', n=48, c=(0, 0, 0), m=None, col=None):
    """revolve a profile [(r, a), ...] around an axis through c"""
    bm = bmesh.new()
    rows = []
    for k in range(n):
        ang = 2 * math.pi * k / n
        row = []
        for r, a in prof:
            if axis == 'y':
                p = (c[0] + r * math.cos(ang), c[1] + a, c[2] + r * math.sin(ang))
            elif axis == 'x':
                p = (c[0] + a, c[1] + r * math.cos(ang), c[2] + r * math.sin(ang))
            else:
                p = (c[0] + r * math.cos(ang), c[1] + r * math.sin(ang), c[2] + a)
            row.append(bm.verts.new(p))
        rows.append(row)
    m_ = len(prof)
    for k in range(n):
        r0, r1 = rows[k], rows[(k + 1) % n]
        for j in range(m_ - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, m, col)


def tube(name, pts, r, m=None, col=None, n=10, closed=False):
    """round tube along a polyline (curve with bevel), converted to mesh"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    sp.use_cyclic_u = closed
    cu.bevel_depth = r
    cu.bevel_resolution = max(1, n // 4)
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    link(ob, col)
    select_only(ob)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    if m:
        ob.data.materials.clear()
        ob.data.materials.append(m)
    return ob


def set_origin(ob, p):
    ob.data.transform(Matrix.Translation(-Vector(p)))
    ob.location = p


# ------------------------------------------------------------------ materials
def _img(name, px=None):
    p = os.path.join(TEX, name + '.png')
    return bpy.data.images.get(name + '.png') or bpy.data.images.load(p)


def _base(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(pb.outputs[0], out.inputs[0])
    return m, nt, pb


def tex_box(name, tex, dens=60, rough=0.6, metal=0.0, px=None, tint=None, alpha_clip=False):
    """PSX texture by box projection in object space at `dens` texels per metre, point filtered"""
    if name in MATS:
        return MATS[name]
    m, nt, pb = _base(name)
    img = _img(tex)
    px = px or img.size[0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = dens / px
    mp.inputs['Scale'].default_value = (s, s, s)
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = img
    ti.interpolation = 'Closest'
    ti.projection = 'BOX'
    ti.projection_blend = 0.0
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], ti.inputs['Vector'])
    col = ti.outputs['Color']
    if tint:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        nt.links.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1)
        col = mx.outputs[2]
    nt.links.new(col, pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    MATS[name] = m
    return m


def tex_uv(name, img_path, rough=0.6, metal=0.0, emit=None):
    """material with a UV-mapped, point-filtered image (baked PSX atlas)"""
    m, nt, pb = _base(name)
    img = bpy.data.images.load(img_path, check_existing=True)
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = img
    ti.interpolation = 'Closest'
    nt.links.new(ti.outputs['Color'], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    if emit:
        nt.links.new(ti.outputs['Color'], pb.inputs['Emission Color'])
        pb.inputs['Emission Strength'].default_value = emit
    MATS[name] = m
    return m


def flat(name, rgb, rough=0.6, metal=0.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m, nt, pb = _base(name)
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    if alpha < 1:
        pb.inputs['Alpha'].default_value = alpha
    MATS[name] = m
    return m


def clay():
    return flat('clay', (0.62, 0.62, 0.6), 0.6)


# ------------------------------------------------------------------ scene, render
def world(rgb=(0.55, 0.62, 0.72), strength=0.9):
    w = bpy.data.worlds.new('W')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength
    return w


def sun(energy=3.5, rot=(50, 0, 35), color=(1, 0.97, 0.92)):
    s = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    s.data.energy = energy
    s.data.color = color
    s.data.angle = math.radians(3)
    s.rotation_euler = tuple(math.radians(a) for a in rot)
    link(s)
    return s


def look(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(c, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new('Cam')
    cd.lens = lens
    cd.clip_start = 0.03
    cd.clip_end = 500
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    cam = bpy.data.objects.get('Cam')
    if cam is None:
        cam = bpy.data.objects.new('Cam', cd)
        link(cam)
    else:
        cam.data = cd
    cam.location = c
    look(cam, target)
    bpy.context.scene.camera = cam
    return cam


def setup(res=(900, 600), spp=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filter_size = 1.0


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
