"""Blender helpers for the ground-vehicle concepts: meshes, PSX materials (box projection, point filter),
wheels, tracks, lights, a mannequin, spruces, scene, cameras, renders.
Frame: X forward (nose +X), Y left, Z up, ground Z = 0, metres."""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
MATS = {}
EMIT = {}          # emissive material name -> (node, day strength, night strength)
GLOW = {}          # lit-window glass emission nodes
NIGHT = False


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    EMIT.clear()
    GLOW.clear()


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


# ------------------------------------------------------------------ materials
def _img(name):
    p = os.path.join(TEX, name + '.png')
    im = bpy.data.images.get(name + '.png') or bpy.data.images.load(p)
    return im


def _tex_node(nt, tex, dens, px=64):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = dens / px
    mp.inputs['Scale'].default_value = (s, s, s)
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = _img(tex)
    ti.interpolation = 'Closest'
    ti.projection = 'BOX'
    ti.projection_blend = 0.0
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], ti.inputs['Vector'])
    return ti, tc


def _base(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(pb.outputs[0], out.inputs[0])
    return m, nt, pb, out


def mat(name, tex, dens=50, rough=0.6, metal=0.0, px=64, tint=None):
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    ti, tc = _tex_node(nt, tex, dens, px)
    src = ti.outputs['Color']
    if tint is not None:
        mx = nt.nodes.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        nt.links.new(src, mx.inputs[6])
        mx.inputs[7].default_value = (*tint, 1)
        src = mx.outputs[2]
    nt.links.new(src, pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    MATS[name] = m
    return m


def _zband(nt, tc, z0, z1):
    """1 where z0 < object z < z1"""
    sx = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sx.inputs[0])
    a = nt.nodes.new('ShaderNodeMath'); a.operation = 'GREATER_THAN'; a.inputs[1].default_value = z0
    b = nt.nodes.new('ShaderNodeMath'); b.operation = 'LESS_THAN'; b.inputs[1].default_value = z1
    nt.links.new(sx.outputs['Z'], a.inputs[0]); nt.links.new(sx.outputs['Z'], b.inputs[0])
    m = nt.nodes.new('ShaderNodeMath'); m.operation = 'MULTIPLY'
    nt.links.new(a.outputs[0], m.inputs[0]); nt.links.new(b.outputs[0], m.inputs[1])
    return m.outputs[0], sx


def livery(name, band=(1.55, 1.85), dirt=(0.35, 1.25), base='paint_red', stripe='paint_white'):
    """fleet livery like the plane: red, white band, road dirt baked low on the body"""
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    t1, tc = _tex_node(nt, base, 50)
    t2, _ = _tex_node(nt, stripe, 50)
    f, sx = _zband(nt, tc, *band)
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    nt.links.new(f, mx.inputs['Factor'])
    nt.links.new(t1.outputs['Color'], mx.inputs[6]); nt.links.new(t2.outputs['Color'], mx.inputs[7])
    # dirt: darker, browner toward the bottom
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = dirt[0]; mr.inputs['From Max'].default_value = dirt[1]
    mr.inputs['To Min'].default_value = 0.55; mr.inputs['To Max'].default_value = 0.0
    nt.links.new(sx.outputs['Z'], mr.inputs['Value'])
    q = nt.nodes.new('ShaderNodeMath'); q.operation = 'SNAP'; q.inputs[1].default_value = 0.11
    nt.links.new(mr.outputs[0], q.inputs[0])
    md = nt.nodes.new('ShaderNodeMix'); md.data_type = 'RGBA'
    nt.links.new(q.outputs[0], md.inputs['Factor'])
    nt.links.new(mx.outputs[2], md.inputs[6]); md.inputs[7].default_value = (0.09, 0.075, 0.06, 1)
    nt.links.new(md.outputs[2], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 0.55
    MATS[name] = m
    return m


def twotone(name, split, low='quilt', high='paint_interior'):
    """interior lining: quilted leatherette below `split`, painted above"""
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    t1, tc = _tex_node(nt, low, 192)
    t2, _ = _tex_node(nt, high, 50)
    f, sx = _zband(nt, tc, split, 99.0)
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    nt.links.new(f, mx.inputs['Factor'])
    nt.links.new(t1.outputs['Color'], mx.inputs[6]); nt.links.new(t2.outputs['Color'], mx.inputs[7])
    nt.links.new(mx.outputs[2], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 0.7
    MATS[name] = m
    return m


def glass(name='glass', tint=(0.10, 0.13, 0.16), clear=0.72, glow=None):
    """window glass: transparent + glossy; glow = warm colour of a lit, frosted living-room window at night
    (its strength is set per view through EMIT[name])"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    gl.inputs['Color'].default_value = (*tint, 1)
    gl.inputs['Roughness'].default_value = 0.08
    mx = nt.nodes.new('ShaderNodeMixShader')
    mx.inputs[0].default_value = 1 - clear
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    if glow:
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*glow, 1)
        em.inputs['Strength'].default_value = 0.0
        ad = nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(mx.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
        nt.links.new(ad.outputs[0], out.inputs[0])
        GLOW[name] = em
    else:
        nt.links.new(mx.outputs[0], out.inputs[0])
    MATS[name] = m
    return m


def room_glass():
    return glass('glass_room', glow=(1.0, 0.55, 0.24))


def set_room_glow(strength):
    for em in GLOW.values():
        em.inputs['Strength'].default_value = strength


def emissive(name, color, day=0.0, night=6.0, base=(0.8, 0.8, 0.78)):
    """lens / lamp: lit only at night (strength set by set_night)"""
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    pb.inputs['Base Color'].default_value = (*base, 1)
    pb.inputs['Roughness'].default_value = 0.15
    pb.inputs['Emission Color'].default_value = (*color, 1)
    pb.inputs['Emission Strength'].default_value = day
    EMIT[name] = (pb, day, night)
    MATS[name] = m
    return m


def flatcol(name, rgb, rough=0.6, metal=0.0, alpha=1.0):
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    pb.inputs['Base Color'].default_value = (*rgb, 1)
    pb.inputs['Roughness'].default_value = rough
    pb.inputs['Metallic'].default_value = metal
    if alpha < 1:
        pb.inputs['Alpha'].default_value = alpha
    MATS[name] = m
    return m


def snowtop(name, tex, rgb_snow=(0.86, 0.89, 0.94), thr=0.55, dens=40):
    """foliage with snow on the upward faces"""
    if name in MATS:
        return MATS[name]
    m, nt, pb, out = _base(name)
    ti, tc = _tex_node(nt, tex, dens)
    gm = nt.nodes.new('ShaderNodeNewGeometry')
    sx = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(gm.outputs['Normal'], sx.inputs[0])
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = thr
    nt.links.new(sx.outputs['Z'], st.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    nt.links.new(st.outputs[0], mx.inputs['Factor'])
    nt.links.new(ti.outputs['Color'], mx.inputs[6]); mx.inputs[7].default_value = (*rgb_snow, 1)
    nt.links.new(mx.outputs[2], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = 0.9
    MATS[name] = m
    return m


def set_night(night):
    global NIGHT
    NIGHT = night
    for n, (pb, d, ni) in EMIT.items():
        pb.inputs['Emission Strength'].default_value = ni if night else d


# ------------------------------------------------------------------ meshes
def _obj(name, bm, m=None, col=None, smooth=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    if m is not None:
        ob.data.materials.append(m)
    if smooth:
        set_smooth(ob, smooth)
    return ob


def set_smooth(ob, angle=35):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def box(name, x0, x1, y0, y1, z0, z1, m=None, col=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0),
                       (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    return _obj(name, bm, m, col)


def prism_y(name, prof, y0, y1, m=None, col=None):
    """polygon [(x, z), ...] extruded along Y from y0 to y1"""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in prof]
    b = [bm.verts.new((x, y1, z)) for x, z in prof]
    n = len(prof)
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, m, col)


def prism_x(name, prof, x0, x1, m=None, col=None):
    """polygon [(y, z), ...] extruded along X"""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    n = len(prof)
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, m, col)


def cyl(name, c, axis, r, length, n=16, m=None, col=None, r2=None, cap=True):
    """cylinder (or cone with r2) centred at c along axis 'x' | 'y' | 'z'"""
    bm = bmesh.new()
    r2 = r if r2 is None else r2
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=n, radius1=r, radius2=r2, depth=length)
    rot = {'x': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'y': Matrix.Rotation(math.pi / 2, 4, 'X'),
           'z': Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ rot, verts=bm.verts)
    return _obj(name, bm, m, col)


def ico(name, c, r, sub=1, m=None, col=None, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*scale, 1)), verts=bm.verts)
    return _obj(name, bm, m, col)


def rounded_rect(x0, x1, z0, z1, r, seg=3):
    """polygon of a rectangle with rounded corners (radius r, seg steps per corner), CCW in (x, z)"""
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def arc(cx, cz, r, a0, a1, seg):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / seg)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / seg))) for k in range(seg + 1)]


def bevel(ob, w, seg=2, angle=40, apply=True):
    md = ob.modifiers.new('bv', 'BEVEL')
    md.width = w
    md.segments = seg
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(angle)
    md.harden_normals = False
    if apply:
        apply_mods(ob)
    return ob


def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    for md in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
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


def bdiff(ob, cutters, union=False):
    """boolean difference with materials transferred from the cutters (rims get the cutter material)"""
    if not cutters:
        return ob
    cut = join(cutters, ob.name + '_cut') if len(cutters) > 1 else cutters[0]
    md = ob.modifiers.new('b', 'BOOLEAN')
    md.operation = 'UNION' if union else 'DIFFERENCE'
    md.solver = 'EXACT'
    md.object = cut
    md.use_self = True
    md.use_hole_tolerant = True
    try:
        md.material_mode = 'TRANSFER'
    except Exception:
        pass
    n0 = len(ob.data.vertices)
    apply_mods(ob)
    bpy.data.objects.remove(cut, do_unlink=True)
    if n0 and not len(ob.data.vertices):
        raise RuntimeError('boolean emptied ' + ob.name)
    return ob


def shell(name, outer, inner, m_out, m_in, col=None):
    """hollow body: outer solid minus inner solid; outer faces m_out, inner faces m_in"""
    outer.name = name
    outer.data.materials.clear()
    outer.data.materials.append(m_out)
    inner.data.materials.clear()
    inner.data.materials.append(m_in)
    return bdiff(outer, [inner])


# ------------------------------------------------------------------ parts
def wheel(name, cx, cy, cz, R, W, rim_r=0.55, lugs=18, lug_h=0.035, balloon=False, m_tire=None, m_rim=None,
          col=None, outward=1):
    """tyre along Y with tread lugs; outward = +1 (left side) / -1 (right side) puts the rim face outside"""
    m_tire = m_tire or mat('rubber', 'rubber', 60, 0.85)
    m_rim = m_rim or mat('rim', 'paint_dark', 50, 0.5, 0.3)
    parts = []
    t = cyl(name + '_t', (cx, cy, cz), 'y', R - lug_h, W, 24, m_tire, col)
    bevel(t, W * (0.42 if balloon else 0.22), 3 if balloon else 2, 30)
    parts.append(t)
    for k in range(lugs):
        a = 2 * math.pi * k / lugs
        off = (W * 0.22) * (1 if k % 2 else -1)
        lw = W * (0.55 if not balloon else 0.7)
        lx, lz = cx + (R - lug_h * 0.6) * math.cos(a), cz + (R - lug_h * 0.6) * math.sin(a)
        lg = box(name + f'_l{k}', -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, m_tire, col)
        sc = Matrix.Diagonal((lug_h * 2.2, lw, 2 * math.pi * R / lugs * 0.45, 1))
        rot = Matrix.Rotation(-a + math.pi / 2, 4, 'Y')
        lg.data.transform(Matrix.Translation((lx, cy + off * (0.0 if balloon else 1.0), lz)) @ rot @ sc)
        parts.append(lg)
    rr = R * rim_r
    face = cy + outward * (W / 2 - 0.02)
    rim = cyl(name + '_r', (cx, face - outward * 0.05, cz), 'y', rr, 0.1, 16, m_rim, col)
    hub = cyl(name + '_h', (cx, face + outward * 0.01, cz), 'y', rr * 0.35, 0.08, 10, mat('metal', 'metal', 50, 0.4, 0.6), col)
    parts += [rim, hub]
    for k in range(6):
        a = 2 * math.pi * k / 6
        parts.append(cyl(name + f'_n{k}', (cx + rr * 0.6 * math.cos(a), face + outward * 0.02,
                                            cz + rr * 0.6 * math.sin(a)), 'y', 0.022, 0.05, 6,
                         mat('metal', 'metal', 50, 0.4, 0.6), col))
    return join(parts, name)


def headlight(name, c, r, facing='x', m_lens=None, col=None, depth=0.12):
    m_lens = m_lens or emissive('lens_head', (1.0, 0.86, 0.62), 0.0, 14.0)
    hous = cyl(name + '_h', c, facing, r * 1.18, depth, 16, mat('chrome', 'metal', 50, 0.3, 0.8), col)
    off = Vector({'x': (depth / 2 + 0.004, 0, 0), 'y': (0, depth / 2 + 0.004, 0), 'z': (0, 0, depth / 2)}[facing])
    lens = cyl(name + '_l', Vector(c) + off, facing, r, 0.012, 16, m_lens, col)
    return join([hous, lens], name)


def mannequin(name, x, y, rotz=0.0, col=None, h=1.8, coat=(0.12, 0.16, 0.22)):
    """low-poly person in a parka for scale"""
    mc = flatcol('coat_' + name, coat, 0.9)
    mp = flatcol('pants', (0.06, 0.06, 0.07), 0.9)
    ms = flatcol('skin', (0.62, 0.45, 0.36), 0.8)
    mfur = flatcol('fur', (0.45, 0.40, 0.33), 1.0)
    k = h / 1.8
    parts = [box(name + '_lL', -0.09, 0.09, 0.03, 0.17, 0, 0.82 * k, mp, col),
             box(name + '_lR', -0.09, 0.09, -0.17, -0.03, 0, 0.82 * k, mp, col),
             box(name + '_bL', -0.12, 0.13, 0.02, 0.18, 0, 0.1 * k, flatcol('boot', (0.05, 0.04, 0.03)), col),
             box(name + '_bR', -0.12, 0.13, -0.18, -0.02, 0, 0.1 * k, flatcol('boot', (0.05, 0.04, 0.03)), col),
             box(name + '_t', -0.15, 0.15, -0.25, 0.25, 0.78 * k, 1.5 * k, mc, col),
             box(name + '_aL', -0.08, 0.08, 0.25, 0.37, 0.85 * k, 1.47 * k, mc, col),
             box(name + '_aR', -0.08, 0.08, -0.37, -0.25, 0.85 * k, 1.47 * k, mc, col)]
    hd = ico(name + '_hd', (0.0, 0, 1.64 * k), 0.12 * k, 1, ms, col)
    hood = ico(name + '_ho', (-0.03, 0, 1.66 * k), 0.15 * k, 1, mfur, col, (1, 1, 1.05))
    face = box(name + '_fc', 0.06, 0.16, -0.08, 0.08, 1.56 * k, 1.72 * k, ms, col)
    hood = bdiff(hood, [box('cut', 0.04, 0.4, -0.09, 0.09, 1.54 * k, 1.74 * k)])
    parts += [hd, hood, face]
    for p in parts:
        bevel(p, 0.025, 1, 40)
    ob = join(parts, name)
    ob.rotation_euler = (0, 0, rotz)
    ob.location = (x, y, 0)
    return ob


def spruce(name, x, y, h, col=None, tiers=4):
    m = snowtop('spruce_m', 'spruce', thr=0.45)
    parts = [cyl(name + '_tr', (x, y, h * 0.12), 'z', h * 0.035, h * 0.24, 6, mat('bark', 'bark', 40, 0.9), col)]
    for i in range(tiers):
        z0 = h * (0.12 + 0.2 * i)
        r = h * 0.3 * (1 - i / (tiers + 0.6))
        parts.append(cyl(name + f'_c{i}', (x, y, z0 + h * 0.18), 'z', r, h * 0.36, 7, m, col, r2=0.0))
    ob = join(parts, name)
    return ob


# ------------------------------------------------------------------ scene
def world(night):
    w = bpy.data.worlds.new('W')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    if night:
        bg.inputs[0].default_value = (0.012, 0.016, 0.03, 1)
        bg.inputs[1].default_value = 1.0
    else:
        bg.inputs[0].default_value = (0.58, 0.63, 0.72, 1)
        bg.inputs[1].default_value = 0.85


def sun(night, rot=(50, 0, 35)):
    s = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    s.data.energy = 0.12 if night else 3.2
    s.data.color = (0.55, 0.65, 1.0) if night else (1.0, 0.96, 0.9)
    s.data.angle = math.radians(2)
    s.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.context.scene.collection.objects.link(s)
    return s


def point(name, c, power, color=(1.0, 0.62, 0.32), radius=0.05, col=None):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'POINT'))
    l.data.energy = power
    l.data.color = color
    l.data.shadow_soft_size = radius
    l.location = c
    (col or bpy.context.scene.collection).objects.link(l)
    return l


def spot(name, c, target, power, angle=55, color=(1.0, 0.9, 0.72), blend=0.4, col=None):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SPOT'))
    l.data.energy = power
    l.data.color = color
    l.data.spot_size = math.radians(angle)
    l.data.spot_blend = blend
    l.data.shadow_soft_size = 0.05
    l.location = c
    look(l, target)
    (col or bpy.context.scene.collection).objects.link(l)
    return l


def look(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(c, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new('Cam')
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 400
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    cam = bpy.data.objects.get('Cam')
    if cam is None:
        cam = bpy.data.objects.new('Cam', cd)
        bpy.context.scene.collection.objects.link(cam)
    else:
        cam.data = cd
    cam.location = c
    look(cam, target)
    bpy.context.scene.camera = cam
    return cam


def setup_render(res=(480, 300), samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'
    sc.render.filter_size = 0.8


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


_DEPTH = None


def render_depth(path):
    """camera distance / 200 as 16-bit grey (material override, 1 sample) for fog in post"""
    global _DEPTH
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    if _DEPTH is None:
        m = bpy.data.materials.new('DEPTH')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        cd = nt.nodes.new('ShaderNodeCameraData')
        dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 200.0
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(cd.outputs['View Distance'], dv.inputs[0])
        nt.links.new(dv.outputs[0], em.inputs['Color'])
        nt.links.new(em.outputs[0], out.inputs[0])
        _DEPTH = m
    keep = (sc.cycles.samples, sc.cycles.use_denoising, sc.world.node_tree.nodes['Background'].inputs[1].default_value,
            sc.view_settings.view_transform, sc.render.image_settings.color_depth, sc.render.filter_size)
    vl.material_override = _DEPTH
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0.0
    bg = sc.world.node_tree.nodes['Background'].inputs[0].default_value[:]
    sc.view_settings.view_transform = 'Raw' if 'Raw' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
    sc.render.image_settings.color_depth = '16'
    sc.render.filter_size = 0.01
    hidden = []
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    render(path)
    for o in hidden:
        o.hide_render = False
    vl.material_override = None
    (sc.cycles.samples, sc.cycles.use_denoising, w, sc.view_settings.view_transform,
     sc.render.image_settings.color_depth, sc.render.filter_size) = keep
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = w


def ring_y(name, x0, x1, y0, y1, z0, z1, t, m=None, col=None):
    """rectangular frame in the XZ plane (window rubber / trim), hole = inner rectangle"""
    o = box(name, x0, x1, y0, y1, z0, z1, m, col)
    return bdiff(o, [box(name + '_h', x0 + t, x1 - t, y0 - 0.1, y1 + 0.1, z0 + t, z1 - t)])


def ring_x(name, x0, x1, y0, y1, z0, z1, t, m=None, col=None):
    """rectangular frame in the YZ plane"""
    o = box(name, x0, x1, y0, y1, z0, z1, m, col)
    return bdiff(o, [box(name + '_h', x0 - 0.1, x1 + 0.1, y0 + t, y1 - t, z0 + t, z1 - t)])
