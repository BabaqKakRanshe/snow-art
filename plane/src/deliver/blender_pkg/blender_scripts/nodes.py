"""Tiny shader-node DSL + procedural materials for the aircraft (Cycles, baked later)."""
import bpy, math

RED = (0.30, 0.028, 0.022, 1)
RED2 = (0.20, 0.022, 0.018, 1)
WHITE = (0.58, 0.56, 0.51, 1)
GREYB = (0.36, 0.36, 0.35, 1)
COWL = (0.026, 0.026, 0.028, 1)
PRIMER = (0.034, 0.036, 0.033, 1)
METAL = (0.40, 0.40, 0.39, 1)
RUST = (0.15, 0.05, 0.018, 1)
DIRT = (0.075, 0.062, 0.048, 1)
SOOT = (0.012, 0.011, 0.01, 1)
GLASS = (0.006, 0.008, 0.01, 1)
SEAL = (0.018, 0.018, 0.018, 1)
MUD = (0.10, 0.072, 0.045, 1)


class NB:
    def __init__(self, mat):
        mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.N, self.L = self.nt.nodes, self.nt.links
        self._geo = None
        self._tc = None

    # ---- plumbing
    def set(self, sock, val):
        if val is None:
            return
        if isinstance(val, bpy.types.NodeSocket):
            self.L.new(val, sock)
            return
        dv = sock.default_value
        if isinstance(val, (int, float)):
            try:
                n = len(dv)
                sock.default_value = [val] * n if n != 4 else (val, val, val, 1.0)
            except TypeError:
                sock.default_value = val
        else:
            val = tuple(val)
            try:
                n = len(dv)
            except TypeError:
                n = 1
            if n == 4 and len(val) == 3:
                val = val + (1.0,)
            if n == 3 and len(val) == 4:
                val = val[:3]
            sock.default_value = val

    def new(self, t, **props):
        n = self.N.new(t)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    # ---- inputs
    def geo(self):
        if not self._geo:
            self._geo = self.new('ShaderNodeNewGeometry')
        return self._geo

    def P(self):
        return self.geo().outputs['Position']

    def Nrm(self):
        return self.geo().outputs['True Normal']

    def obj(self):
        if not self._tc:
            self._tc = self.new('ShaderNodeTexCoord')
        return self._tc.outputs['Object']

    def attr(self, name):
        n = self.new('ShaderNodeAttribute', attribute_type='OBJECT', attribute_name=name)
        return n.outputs['Fac']

    # ---- math
    def m(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        self.set(n.inputs[2], c)
        return n.outputs[0]

    def add(self, *xs):
        r = xs[0]
        for x in xs[1:]:
            r = self.m('ADD', r, x)
        return r

    def sub(self, a, b): return self.m('SUBTRACT', a, b)
    def mul(self, *xs):
        r = xs[0]
        for x in xs[1:]:
            r = self.m('MULTIPLY', r, x)
        return r
    def mad(self, a, b, c): return self.m('MULTIPLY_ADD', a, b, c)
    def abs(self, a): return self.m('ABSOLUTE', a)
    def mn(self, *xs):
        r = xs[0]
        for x in xs[1:]:
            r = self.m('MINIMUM', r, x)
        return r
    def mx(self, *xs):
        r = xs[0]
        for x in xs[1:]:
            r = self.m('MAXIMUM', r, x)
        return r
    def clamp01(self, a): return self.m('ADD', a, 0.0, clamp=True)
    def gt(self, a, b): return self.m('GREATER_THAN', a, b)
    def fract(self, a): return self.m('FRACT', a)
    def sqrt(self, a): return self.m('SQRT', a)
    def inv(self, a): return self.sub(1.0, a)

    def ss(self, e0, e1, x):
        n = self.new('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='SMOOTHSTEP', clamp=True)
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], e0)
        self.set(n.inputs[2], e1)
        self.set(n.inputs[3], 0.0)
        self.set(n.inputs[4], 1.0)
        return n.outputs[0]

    def lin(self, e0, e1, x, a=0.0, b=1.0):
        n = self.new('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='LINEAR', clamp=True)
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], e0)
        self.set(n.inputs[2], e1)
        self.set(n.inputs[3], a)
        self.set(n.inputs[4], b)
        return n.outputs[0]

    def in_range(self, v, a, b, soft=0.003):
        return self.mul(self.ss(a - soft, a + soft, v), self.inv(self.ss(b - soft, b + soft, v)))

    def eq(self, a, k):
        return self.inv(self.ss(0.3, 0.5, self.abs(self.sub(a, k))))

    def sep(self, v):
        n = self.new('ShaderNodeSeparateXYZ')
        self.set(n.inputs[0], v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def comb(self, x, y, z):
        n = self.new('ShaderNodeCombineXYZ')
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], y)
        self.set(n.inputs[2], z)
        return n.outputs[0]

    def vm(self, op, a, b=None):
        n = self.new('ShaderNodeVectorMath', operation=op)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs['Vector']

    def mixc(self, fac, a, b, blend='MIX'):
        n = self.new('ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_factor=True)
        self.set(n.inputs[0], fac)
        self.set(n.inputs[6], a)
        self.set(n.inputs[7], b)
        return n.outputs[2]

    def mixf(self, fac, a, b):
        # a + (b - a) * fac
        return self.mad(self.sub(b, a), fac, a)

    def noise(self, vec, scale, detail=4.0, rough=0.55, distortion=0.0):
        n = self.new('ShaderNodeTexNoise', noise_dimensions='3D')
        self.set(n.inputs['Vector'], vec)
        self.set(n.inputs['Scale'], scale)
        self.set(n.inputs['Detail'], detail)
        self.set(n.inputs['Roughness'], rough)
        self.set(n.inputs['Distortion'], distortion)
        return n.outputs['Fac']

    def edge_ao(self, dist=0.05, samples=8):
        n = self.new('ShaderNodeAmbientOcclusion', inside=True, only_local=True, samples=samples)
        self.set(n.inputs['Distance'], dist)
        return n.outputs['AO']

    def cavity_ao(self, dist=0.25, samples=8):
        n = self.new('ShaderNodeAmbientOcclusion', inside=False, only_local=False, samples=samples)
        self.set(n.inputs['Distance'], dist)
        return n.outputs['AO']

    # ---- patterns
    def line_mask(self, coord, period, width, offset=0.0):
        d = self.mul(self.abs(self.sub(self.fract(self.add(self.m('DIVIDE', self.sub(coord, offset), period), 0.5)), 0.5)), period)
        return self.inv(self.ss(width * 0.4, width, d)), d

    def rivets(self, coord_line, period, offset, coord_along, spacing, radius):
        _, d1 = self.line_mask(coord_line, period, 0.001, offset)
        _, d2 = self.line_mask(coord_along, spacing, 0.001, 0.0)
        r = self.sqrt(self.add(self.mul(d1, d1), self.mul(d2, d2)))
        return self.inv(self.ss(radius * 0.55, radius, r))

    def sd_round_box(self, u, v, cu, cv, hu, hv, r):
        qx = self.add(self.sub(self.abs(self.sub(u, cu)), hu), r)
        qy = self.add(self.sub(self.abs(self.sub(v, cv)), hv), r)
        ox, oy = self.mx(qx, 0.0), self.mx(qy, 0.0)
        outside = self.sqrt(self.add(self.mul(ox, ox), self.mul(oy, oy)))
        inside = self.mn(self.mx(qx, qy), 0.0)
        return self.sub(self.add(outside, inside), r)

    # ---- output
    def finish(self, col, metal, rough, height, bump_strength=1.0, emission=None):
        """Create Principled + bump and the bake emission helpers.  Returns nothing; stores sockets."""
        bump = self.new('ShaderNodeBump')
        self.set(bump.inputs['Strength'], bump_strength)
        self.set(bump.inputs['Distance'], 1.0)
        self.set(bump.inputs['Height'], height)
        pr = self.new('ShaderNodeBsdfPrincipled')
        self.set(pr.inputs['Base Color'], col)
        self.set(pr.inputs['Metallic'], metal)
        self.set(pr.inputs['Roughness'], rough)
        self.L.new(bump.outputs['Normal'], pr.inputs['Normal'])
        if emission is not None:
            self.set(pr.inputs['Emission Color'], emission)
            self.set(pr.inputs['Emission Strength'], 1.0)
        out = self.new('ShaderNodeOutputMaterial', target='ALL')
        self.L.new(pr.outputs[0], out.inputs['Surface'])
        e_col = self.new('ShaderNodeEmission', label='BAKE_COLOR', name='BAKE_COLOR')
        self.set(e_col.inputs['Color'], col)
        e_mr = self.new('ShaderNodeEmission', label='BAKE_MR', name='BAKE_MR')
        self.set(e_mr.inputs['Color'], self.comb(metal, rough, 0.0))
        self.new('ShaderNodeBsdfDiffuse', name='BAKE_PLAIN', label='BAKE_PLAIN')
        img = self.new('ShaderNodeTexImage', name='BAKE_TARGET', label='BAKE_TARGET')
        self.nt.nodes.active = img
        self.pr, self.out = pr, out


# ================================================================== generic weathering
def weather(nb, V, col, rough, chip_amt=0.0, rust_amt=0.0, dirt=0.3, metal_col=METAL, metal_rough=0.38,
            primer=PRIMER, edge_boost=0.25, chip_scale=9.0, zworld=None, metallic_base=0.0, plastic=False):
    n1 = nb.noise(V, 1.6, 4, 0.55)
    n2 = nb.noise(V, chip_scale, 10, 0.72)
    nr = nb.noise(V, 5.0, 3, 0.5)
    ng = nb.noise(V, 35.0, 5, 0.6)
    edge = nb.ss(0.95, 0.55, nb.edge_ao(0.012, 6))
    cav = nb.ss(0.95, 0.4, nb.cavity_ao(0.15, 6))
    chipv = nb.add(n2, nb.mul(edge, edge_boost), chip_amt)
    chip = nb.ss(0.625, 0.64, chipv)
    deep = nb.ss(0.665, 0.68, chipv)
    rustm = nb.mul(chip, nb.ss(0.70 - 0.3 * rust_amt, 0.76 - 0.3 * rust_amt, nr))
    if plastic:
        worn = nb.mixc(0.5, col, (0.5, 0.5, 0.48, 1))
        c = nb.mixc(nb.mul(chip, 0.8), col, worn)
    else:
        c = nb.mixc(chip, col, primer)
        c = nb.mixc(nb.mul(deep, chip), c, metal_col)
        c = nb.mixc(rustm, c, RUST)
    bottom = nb.ss(1.3, 0.3, zworld) if zworld is not None else 0.0
    g = nb.clamp01(nb.mul(dirt, nb.add(nb.ss(0.42, 0.72, n1), nb.mul(cav, 0.8), bottom)))
    c = nb.mixc(nb.mul(g, 0.55), c, DIRT)
    # value variation
    r = nb.add(rough, nb.mul(nb.sub(ng, 0.5), 0.18))
    if not plastic:
        r = nb.mixf(chip, r, 0.72)
        r = nb.mixf(nb.mul(deep, chip), r, metal_rough)
        r = nb.mixf(rustm, r, 0.9)
    r = nb.mixf(g, r, 0.88)
    metal = metallic_base
    if not plastic:
        metal = nb.mul(nb.mul(deep, chip), nb.inv(rustm))
        if metallic_base:
            metal = nb.mx(metal, nb.mul(metallic_base, nb.inv(rustm)))
    h = nb.add(nb.mul(nb.inv(chip), 0.0002), nb.mul(ng, 0.00006))
    return c, metal, nb.clamp01(r), h


# ================================================================== LIVERY (airframe skin)
LEFT_WIN = [(-2.665, 2.12, 0.40, 0.33, 0.06), (-1.69, 2.13, 0.42, 0.32, 0.06), (-0.20, 2.11, 0.40, 0.24, 0.07),
            (0.98, 2.12, 0.28, 0.25, 0.07)]
RIGHT_WIN = [(-2.665, 2.12, 0.40, 0.33, 0.06), (-1.69, 2.13, 0.42, 0.32, 0.06), (-0.20, 2.11, 0.46, 0.26, 0.07),
             (0.98, 2.12, 0.28, 0.25, 0.07)]
LOGO = (-2.0, 1.31, 0.42)


def mat_livery(mat, logo_img):
    nb = NB(mat)
    P, N = nb.P(), nb.Nrm()
    x, y, z = nb.sep(P)
    nx, ny, nz = nb.sep(N)
    part = nb.attr('part')
    ax = nb.abs(x)
    side = nb.ss(0.45, 0.65, nb.abs(nx))
    up = nb.ss(0.1, 0.4, nz)
    down = nb.ss(0.1, 0.4, nb.m('MULTIPLY', nz, -1.0))
    isF = nb.eq(part, 0)
    isDoor = nb.eq(part, 5)
    isFD = nb.clamp01(nb.add(isF, isDoor))
    isWing = nb.clamp01(nb.add(nb.eq(part, 1), nb.eq(part, 2)))
    isFin = nb.eq(part, 3)
    isStab = nb.eq(part, 4)
    cowl = nb.mul(nb.ss(-3.29, -3.36, y), isF)

    # ---- livery masks
    ya = nb.mx(nb.sub(y, 1.1), 0.0)
    zs = nb.mad(ya, 0.1468, 1.64)
    hws = nb.sub(0.12, nb.mul(ya, 0.0152))
    dz = nb.abs(nb.sub(z, zs))
    stripe = nb.inv(nb.ss(nb.sub(hws, 0.003), nb.add(hws, 0.003), dz))
    stripe = nb.mul(stripe, isFD, nb.inv(cowl), nb.inv(nb.ss(0.45, 0.7, nb.m('MULTIPLY', nz, -1.0))))
    tailband = nb.mul(nb.in_range(y, 2.45, 2.80), isF)
    wingband = nb.mul(nb.add(nb.in_range(ax, 2.0, 2.8), nb.in_range(ax, 5.1, 5.9)), isWing)
    finband = nb.mul(nb.in_range(z, 2.95, 3.20), isFin)
    stabband = nb.mul(nb.in_range(ax, 0.9, 1.5), isStab)
    paintW = nb.clamp01(nb.mx(stripe, tailband, wingband, finband, stabband))
    under = nb.clamp01(nb.add(nb.mul(down, nb.clamp01(nb.add(isWing, isStab))),
                              nb.mul(nb.ss(0.5, 0.7, nb.m('MULTIPLY', nz, -1.0)), isFD, nb.inv(cowl))))

    n1 = nb.noise(P, 1.3, 4, 0.55)
    base = nb.mixc(nb.ss(0.4, 0.65, n1), RED, RED2)
    base = nb.mixc(paintW, base, WHITE)
    base = nb.mixc(under, base, GREYB)
    base = nb.mixc(cowl, base, COWL)

    # ---- logo decal
    sgn = nb.sub(nb.mul(nb.gt(x, 0.0), 2.0), 1.0)
    lu = nb.add(nb.m('DIVIDE', nb.mul(nb.sub(y, LOGO[0]), sgn), LOGO[2]), 0.5)
    lv = nb.add(nb.m('DIVIDE', nb.sub(z, LOGO[1]), LOGO[2]), 0.5)
    tex = nb.new('ShaderNodeTexImage', image=logo_img, extension='CLIP', interpolation='Cubic')
    nb.set(tex.inputs['Vector'], nb.comb(lu, lv, 0.0))
    logo_m = nb.mul(tex.outputs['Alpha'], side, isF)
    base = nb.mixc(logo_m, base, tex.outputs['Color'])

    # ---- windows
    def dmin(wins):
        ds = [nb.sd_round_box(y, z, cu, cv, hu, hv, r) for cu, cv, hu, hv, r in wins]
        return nb.mn(*ds)
    dl, dr = dmin(LEFT_WIN), dmin(RIGHT_WIN)
    xpos = nb.gt(x, 0.0)
    dside = nb.mixf(xpos, dr, dl)
    gside = nb.mul(side, isFD, nb.in_range(z, 1.6, 2.6))
    dws = nb.sd_round_box(x, y, 0.0, -2.92, 0.62, 0.27, 0.06)
    dws = nb.mx(dws, nb.sub(0.02, ax))
    gws = nb.mul(nb.ss(0.1, 0.25, nz), isF, nb.ss(2.26, 2.30, z), nb.in_range(y, -3.3, -2.55))
    d = nb.mixf(gside, 1.0, dside)
    d = nb.mixf(gws, d, dws)
    glass = nb.inv(nb.ss(-0.002, 0.002, d))
    frame = nb.mul(nb.ss(-0.004, -0.001, d), nb.inv(nb.ss(0.026, 0.032, d)))
    nowin = nb.clamp01(nb.inv(nb.add(glass, frame)))

    # ---- panel lines & rivets
    ly, _ = nb.line_mask(y, 0.55, 0.0045)
    lz, _ = nb.line_mask(z, 0.42, 0.0045)
    lx, _ = nb.line_mask(x, 0.5, 0.0045)
    topbot = nb.clamp01(nb.add(up, down))
    panel = nb.mul(nb.mx(ly, nb.mul(lz, side), nb.mul(lx, topbot)), nowin)
    s_along = nb.add(x, z)
    rv = nb.mx(nb.rivets(y, 0.55, 0.018, s_along, 0.055, 0.0065),
               nb.mul(nb.rivets(z, 0.42, 0.016, y, 0.055, 0.0065), side),
               nb.mul(nb.rivets(x, 0.5, 0.016, y, 0.055, 0.0065), topbot))
    rv = nb.mul(rv, nowin)

    # ---- weathering
    n2 = nb.noise(P, 8.5, 10, 0.72)
    n3 = nb.noise(nb.vm('MULTIPLY', P, (1.0, 1.0, 0.1)), 9.0, 5, 0.6)
    n4 = nb.noise(nb.vm('MULTIPLY', P, (1.0, 0.1, 1.0)), 9.0, 5, 0.6)
    nr = nb.noise(P, 4.0, 3, 0.5)
    ng = nb.noise(P, 40.0, 5, 0.6)
    edge = nb.ss(0.95, 0.55, nb.edge_ao(0.012, 6))
    cav = nb.ss(0.97, 0.5, nb.cavity_ao(0.3, 6))
    le = nb.mul(isWing, nb.ss(-2.35, -2.55, y))
    chipv = nb.add(n2, nb.mul(edge, 0.15), nb.mul(panel, 0.06), nb.mul(le, 0.08), nb.mul(cowl, 0.02),
                   nb.mul(nb.ss(1.5, 1.0, z), 0.05))
    chip = nb.mul(nb.ss(0.635, 0.65, chipv), nowin)
    deep = nb.ss(0.69, 0.705, chipv)
    rustm = nb.mul(chip, nb.ss(0.64, 0.70, nr))
    c = nb.mixc(chip, base, PRIMER)
    c = nb.mixc(nb.mul(deep, chip), c, METAL)
    c = nb.mixc(rustm, c, RUST)
    streak = nb.ss(0.5, 0.78, nb.mixf(side, n4, n3))
    bottomf = nb.ss(1.9, 1.0, z)
    g = nb.clamp01(nb.add(nb.mul(nb.ss(0.42, 0.75, n1), 0.30), nb.mul(streak, 0.32), nb.mul(bottomf, 0.35),
                          nb.mul(cav, 0.35)))
    c = nb.mixc(nb.mul(g, nb.sub(0.4, nb.mul(cowl, 0.25))), c, DIRT)
    rstreak = nb.mul(side, nb.ss(0.6, 0.8, n3), nb.ss(0.45, 0.7, nr), nb.inv(cowl), nowin)
    c = nb.mixc(nb.mul(rstreak, 0.45), c, RUST)
    soot = nb.mul(side, nb.ss(-3.95, -3.72, y), nb.ss(-0.6, -3.6, y),
                  nb.inv(nb.ss(0.04, 0.30, nb.abs(nb.sub(z, nb.mad(y, 0.035, 1.78))))),
                  nb.add(0.55, nb.mul(n3, 0.6)))
    oil = nb.mul(nb.ss(0.5, 0.7, nb.m('MULTIPLY', nz, -1.0)), isF, nb.ss(-4.3, -3.9, y), nb.ss(1.5, -2.0, y),
                 nb.ss(0.45, 0.7, n4))
    c = nb.mixc(nb.clamp01(nb.mul(nb.add(soot, oil), 0.85)), c, SOOT)
    c = nb.mixc(frame, c, SEAL)
    c = nb.mixc(glass, c, nb.mixc(nb.mul(streak, 0.25), GLASS, DIRT))

    # roughness / metallic
    r = nb.add(0.5, nb.mul(nb.sub(ng, 0.5), 0.2), nb.mul(paintW, 0.06), nb.mul(cowl, -0.08))
    r = nb.mixf(chip, r, 0.74)
    r = nb.mixf(nb.mul(deep, chip), r, 0.36)
    r = nb.mixf(rustm, r, 0.9)
    r = nb.mixf(g, r, 0.85)
    r = nb.mixf(nb.clamp01(nb.add(soot, oil)), r, 0.8)
    r = nb.mixf(frame, r, 0.7)
    r = nb.mixf(glass, r, nb.add(0.04, nb.mul(streak, 0.12)))
    metal = nb.mul(deep, chip, nb.inv(rustm), nowin)
    h = nb.add(nb.mul(panel, -0.0012), nb.mul(rv, 0.0007), nb.mul(nb.inv(chip), 0.00022), nb.mul(glass, -0.004),
               nb.mul(frame, 0.0008), nb.mul(ng, 0.00005))
    nb.finish(c, metal, nb.clamp01(r), h)


# ================================================================== simple / details materials
def mat_generic(mat, col, rough, V='world', **kw):
    nb = NB(mat)
    Vv = nb.P() if V == 'world' else nb.obj()
    _, _, zw = nb.sep(nb.P())
    c, m, r, h = weather(nb, Vv, col, rough, zworld=zw, **kw)
    nb.finish(c, m, r, h)


def mat_gear(mat):
    nb = NB(mat)
    P = nb.P()
    _, _, z = nb.sep(P)
    c, m, r, h = weather(nb, P, (0.022, 0.022, 0.024, 1), 0.5, chip_amt=0.04, rust_amt=0.6, dirt=0.35, zworld=z)
    mud = nb.mul(nb.ss(0.75, 0.25, z), nb.ss(0.45, 0.6, nb.noise(P, 6, 6, 0.65)))
    c = nb.mixc(mud, c, MUD)
    r = nb.mixf(mud, r, 0.92)
    nb.finish(c, nb.mul(m, nb.inv(mud)), r, nb.add(h, nb.mul(mud, 0.0006)))


def mat_rubber(mat):
    nb = NB(mat)
    O = nb.obj()
    ox, oy, oz = nb.sep(O)
    ws = nb.attr('wscale')
    rn = nb.m('DIVIDE', nb.sqrt(nb.add(nb.mul(oy, oy), nb.mul(oz, oz))), ws)
    n1 = nb.noise(O, 7.0, 6, 0.6)
    ng = nb.noise(O, 60.0, 4, 0.6)
    low = nb.ss(0.472, 0.458, rn)
    dust = nb.clamp01(nb.mul(nb.add(nb.mul(low, 0.6), 0.06), nb.ss(0.4, 0.72, n1), 0.9))
    c = nb.mixc(nb.mul(ng, 0.3), (0.021, 0.02, 0.019, 1), (0.03, 0.029, 0.027, 1))
    c = nb.mixc(dust, c, (0.14, 0.115, 0.085, 1))
    r = nb.mixf(dust, nb.add(0.78, nb.mul(ng, 0.1)), 0.95)
    r = nb.mixf(nb.ss(0.476, 0.482, rn), r, 0.62)   # worn lug tops a bit shinier
    sipes, _ = nb.line_mask(nb.m('ARCTAN2', oy, oz), 0.0654, 0.006)
    h = nb.add(nb.mul(ng, 0.0003), nb.mul(sipes, nb.ss(0.47, 0.478, rn), -0.0012))
    nb.finish(c, 0.0, r, h)


def mat_blade(mat):
    nb = NB(mat)
    O = nb.obj()
    ox, oy, oz = nb.sep(O)
    r = nb.sqrt(nb.add(nb.mul(ox, ox), nb.mul(oz, oz)))
    tip = nb.ss(1.165, 1.172, r)
    base = nb.mixc(tip, (0.014, 0.014, 0.015, 1), (0.78, 0.44, 0.02, 1))
    c, m, rr, h = weather(nb, O, base, 0.42, chip_amt=0.0, rust_amt=0.0, dirt=0.15, edge_boost=0.35,
                          chip_scale=14.0)
    nb.finish(c, m, rr, h)


def mat_interior(mat):
    nb = NB(mat)
    P, N = nb.P(), nb.Nrm()
    x, y, z = nb.sep(P)
    nx, ny, nz = nb.sep(N)
    floor = nb.mul(nb.ss(0.8, 0.9, nz), nb.ss(1.12, 1.09, z))
    # diamond plate
    a = nb.add(x, y)
    b = nb.sub(x, y)
    d1, _ = nb.line_mask(a, 0.035, 0.004)
    d2, _ = nb.line_mask(b, 0.035, 0.004)
    _, da = nb.line_mask(a, 0.035, 0.001)
    _, db = nb.line_mask(b, 0.035, 0.001)
    lug1 = nb.inv(nb.ss(0.004, 0.006, nb.sqrt(nb.add(nb.mul(nb.mul(da, 0.5), nb.mul(da, 0.5)), nb.mul(db, db)))))
    lug2 = nb.inv(nb.ss(0.004, 0.006, nb.sqrt(nb.add(nb.mul(da, da), nb.mul(nb.mul(db, 0.5), nb.mul(db, 0.5))))))
    plate = nb.mul(floor, nb.mx(lug1, lug2))
    col = nb.mixc(floor, (0.07, 0.08, 0.065, 1), (0.22, 0.22, 0.21, 1))
    c, m, r, h = weather(nb, P, col, 0.72, chip_amt=0.02, dirt=0.45, zworld=z)
    m = nb.mx(m, nb.mul(floor, 0.85))
    r = nb.mixf(floor, r, nb.add(0.45, nb.mul(plate, -0.1)))
    nb.finish(c, m, r, nb.add(h, nb.mul(plate, 0.0015)))


def mat_case(mat, col):
    nb = NB(mat)
    O = nb.obj()
    _, _, z = nb.sep(nb.P())
    c, m, r, h = weather(nb, nb.P(), col, 0.55, chip_amt=0.0, dirt=0.3, edge_boost=0.3, plastic=True, zworld=z)
    tex = nb.noise(nb.P(), 180.0, 2, 0.5)
    nb.finish(c, 0.0, r, nb.add(h, nb.mul(tex, 0.00012)))


def mat_metal_dark(mat):
    nb = NB(mat)
    P = nb.P()
    _, _, z = nb.sep(P)
    n = nb.noise(P, 6.0, 5, 0.6)
    col = nb.mixc(nb.ss(0.35, 0.7, n), (0.11, 0.09, 0.075, 1), (0.05, 0.045, 0.04, 1))
    c, m, r, h = weather(nb, P, col, 0.5, chip_amt=0.0, rust_amt=0.8, dirt=0.4, zworld=z, metallic_base=0.9)
    nb.finish(c, m, r, h)


def mat_lights(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pr.inputs['Base Color'].default_value = (0.8, 0.02, 0.01, 1)
    pr.inputs['Roughness'].default_value = 0.15
    pr.inputs['Emission Color'].default_value = (1.0, 0.03, 0.01, 1)
    pr.inputs['Emission Strength'].default_value = 6.0
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(pr.outputs[0], out.inputs[0])
