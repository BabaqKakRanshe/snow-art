"""Plans of the v2 walls: plan_gate.png, plan_barrier.png - the plan before (U7 with the v1 gate / barrier) and after (v2),
the levelling strip, and the wall line in elevation (1:1 and the panels' feet with the heights stretched).
python3 plans_v2.py"""
import json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle

U = json.load(open('/home/claude/uaz/out/forest_update7/u7_layout.json'))
V = json.load(open('u7_layout_v2.json'))
D = json.load(open('walls_v2_data.json'))
H0 = np.load('/home/claude/fence/game_terrain_1_1.npy')
H1 = np.load('terrain_levelled_1_1.npy')
STEP = 600.0 / (H0.shape[0] - 1)
PANELS = ('ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign', 'ConcreteFence_Plain',
          'ConcreteFence_Wicket')
FOOT = {'ConcreteFence_Socket': (0.475, 0.375), 'TankTooth': (0.5, 0.5), 'TankTooth_b': (0.5, 0.5),
        'RoadBlock_FBS': (1.19, 0.20), 'RoadBlock_Jersey': (1.0, 0.31), 'RoadBlock_Jersey_Striped': (1.0, 0.31),
        'RoadBlock_Cube': (0.5, 0.5), 'WireCoil': (2.5, 0.48), 'WireBarricade': (1.5, 0.75), 'Hedgehog': (0.8, 0.8),
        'Abatis': (4.3, 1.35), 'Abatis_b': (3.8, 1.3), 'Sign_Halt': (0.62, 0.10), 'Sign_NoEntry': (0.30, 0.08)}


def sample(H, x, z):
    u, v = x / STEP, (z + 600.0) / STEP
    i0, j0 = int(np.floor(u)), int(np.floor(v))
    fu, fv = u - i0, v - j0
    return float((H[j0, i0] * (1 - fu) + H[j0, i0 + 1] * fu) * (1 - fv) + (H[j0 + 1, i0] * (1 - fu) + H[j0 + 1, i0 + 1] * fu) * fv)


def yaw_of(q):
    return math.degrees(2 * math.atan2(q[1], q[3]))


def ux_of(yaw):
    t = math.radians(yaw)
    return np.array([math.cos(t), -math.sin(t)])


def uz_of(yaw):
    t = math.radians(yaw)
    return np.array([math.sin(t), math.cos(t)])


class Frame:
    def __init__(self, k):
        f = D[k]
        self.P, self.X, self.Y = np.array(f['P']), np.array(f['X']), np.array(f['Y'])

    def loc(self, p):
        d = np.asarray(p, float) - self.P
        return np.array([d @ self.X, d @ self.Y])

    def world(self, x, y=0.0):
        return self.P + self.X * x + self.Y * y


def piece_polys(R, F, box):
    """(model, polygon in the local frame, kind) of the pieces inside box"""
    x0, x1, y0, y1 = box
    out = []
    for r in R:
        c = np.array([r['p'][0], r['p'][2]])
        lc = F.loc(c)
        if not (x0 - 3 < lc[0] < x1 + 3 and y0 - 3 < lc[1] < y1 + 3):
            continue
        yaw = yaw_of(r['q'])
        bx, by = -ux_of(yaw), -uz_of(yaw)                     # the piece's Blender +x, +y in the world
        ax = np.array([bx @ F.X, bx @ F.Y])
        ay = np.array([by @ F.X, by @ F.Y])

        def rect(cc, hx, hy):
            return np.array([cc + ax * sx * hx + ay * sy * hy for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        if r['m'] in PANELS:
            out.append((r['m'], rect(lc, 1.24, 0.075), 'panel'))
            out.append((r['m'], rect(lc + ax * 1.25 - ay * 0.0, 0.475, 0.375), 'socket'))
        elif r['m'] == 'ConcreteFence_Socket':
            out.append((r['m'], rect(lc, 0.475, 0.375), 'socket'))
        else:
            hx, hy = FOOT[r['m']]
            off = {'Abatis': -0.55, 'Abatis_b': -0.75}.get(r['m'], 0.0)
            out.append((r['m'], rect(lc + ay * off, hx, hy), 'other'))
    return out


def draw_pieces(ax, polys, alpha=1.0):
    col = {'panel': '#6f6f6a', 'socket': '#b9b6ad', 'other': '#8a7f6a'}
    for m, poly, kind in sorted(polys, key=lambda t: t[2] != 'socket'):
        fc = col[kind] if kind != 'panel' else ('#5a6f8a' if m.endswith('_b') else ('#a0472f' if 'Sign' in m else col[kind]))
        ax.add_patch(Polygon(poly, closed=True, fc=fc, ec='#222', lw=0.4, alpha=alpha, zorder=3 if kind == 'panel' else 2))


def strip_outline(ax, st, F):
    """the flat part and the edge of the modified ground, in the local frame"""
    a, b = st['local']
    hw, fp, r0, r1 = st['half_width'], st['falloff'], st['ramp_start'], st['ramp_end']
    ax.add_patch(Rectangle((a, -hw), b - a, 2 * hw, fc='#f2d06b', ec='#c49a12', lw=0.8, alpha=0.35, zorder=1))
    ax.add_patch(Rectangle((a - r0, -hw - fp), (b - a) + r0 + r1, 2 * (hw + fp), fc='none', ec='#c49a12', lw=0.8, ls='--',
                           zorder=1))


def kit_gate(ax, v2):
    if not v2:
        # v1: the chain-link fixed panel, the receiver post, the guides, the rail strip, the leaf shut
        ax.add_patch(Rectangle((0.20, -0.03), 2.20, 0.06, fc='#9ca7a8', ec='#333', lw=0.5, zorder=4))
        for xp in (0.20, 2.40):
            ax.add_patch(Circle((xp, 0.0), 0.03, fc='#555', zorder=5))
        ax.add_patch(Rectangle((-6.95, 0.07), 13.61, 0.30, fc='#d8d4c8', ec='#999', lw=0.4, zorder=1.5))
        ax.add_patch(Rectangle((-7.40, -0.01), 0.45, 0.46, fc='#c9c5ba', ec='#555', lw=0.5, zorder=4))
        for yp in (0.09, 0.35):
            ax.add_patch(Rectangle((-0.20, yp - 0.04), 0.08, 0.08, fc='#555', zorder=5))
        ax.add_patch(Rectangle((-7.0, 0.19), 7.0, 0.06, fc='#3d6e3d', ec='#123', lw=0.5, zorder=6))
        ax.text(-3.5, 0.45, 'v1: сетчатое полотно 0,22 м внутри', ha='center', va='bottom', fontsize=6.5, color='#123')
        ax.text(1.3, -0.55, 'v1: неподвижная секция рабицы', ha='center', va='top', fontsize=6.5)
    else:
        for x0_ in (-7.45, 0.15):
            ax.add_patch(Rectangle((x0_, -0.15), 0.30, 0.30, fc='#555b60', ec='#111', lw=0.6, zorder=6))
        ax.add_patch(Rectangle((-7.10, 0.40), 13.90, 0.20, fc='#d8d4c8', ec='#999', lw=0.4, zorder=1.5))
        ax.add_patch(Rectangle((-7.0, 0.46), 7.0, 0.08, fc='#3d5e46', ec='#123', lw=0.5, zorder=6))
        ax.add_patch(Rectangle((-0.40, 0.46), 7.0, 0.08, fc='none', ec='#3d5e46', lw=0.8, ls='--', zorder=6))
        ax.add_patch(Rectangle((-0.32, 0.64), 0.30, 0.26, fc='#c8cbc6', ec='#222', lw=0.6, zorder=6))     # the drive
        for gx_, gy_ in ((-0.10, 0.37), (0.04, 0.63)):                                                   # guide stands
            ax.add_patch(Rectangle((gx_ - 0.04, gy_ - 0.04), 0.08, 0.08, fc='#7d8285', ec='#222', lw=0.5, zorder=6.5))
        ax.add_patch(Circle((1.6, 2.2), 0.13, fc='#6b4f35', ec='#222', zorder=6))
        ax.add_patch(Circle((1.6, 2.2), 0.5, fc='none', ec='#6b4f35', ls=':', zorder=6))
        ax.text(-3.5, 0.62, 'v2: сплошное полотно 0,50 м внутри (закрыто)', ha='center', va='bottom', fontsize=6.5, color='#123')
        ax.text(3.6, 0.62, 'открыто (стоит здесь)', ha='center', va='bottom', fontsize=6.5, color='#3d5e46')
        ax.text(-0.45, 1.05, 'привод', ha='right', va='center', fontsize=6.5)
        ax.text(1.6, 2.85, 'опора K8', ha='center', fontsize=6.5)
        ax.add_patch(Rectangle((0.70, 1.20), 0.50, 0.50, fc='#c9c5ba', ec='#555', lw=0.5, zorder=5))      # v2.1: the camera mast
        ax.add_patch(Circle((0.95, 1.45), 0.14, fc='#9aa0a0', ec='#222', lw=0.6, zorder=6))
        ax.plot([0.95, 0.95, 0.02], [1.20, 0.80, 0.80], color='#444', lw=1.0, ls='--', zorder=5)
        ax.text(0.62, 1.45, 'мачта: камера, прожектор', ha='right', va='center', fontsize=6.5)
        ax.text(-7.3, -0.6, 'столб', ha='center', fontsize=6.5)
        ax.text(0.3, -0.6, 'столб', ha='center', fontsize=6.5)


def kit_barrier(ax, v2):
    if not v2:
        ax.add_patch(Rectangle((-0.375, -0.375), 0.75, 0.75, fc='#c9c5ba', ec='#555', lw=0.5, zorder=4))
        ax.add_patch(Rectangle((-0.10, 0.10), 0.20, 0.20, fc='#ddd', ec='#222', lw=0.5, zorder=5))
        ax.text(0.0, -0.9, 'v1: стойка и противовес', ha='center', fontsize=7)
    else:
        ax.add_patch(Rectangle((-0.40, -0.40), 0.80, 0.90, fc='#c9c5ba', ec='#555', lw=0.5, zorder=4))
        ax.add_patch(Rectangle((-0.18, 0.06), 0.36, 0.32, fc='#c8cbc6', ec='#111', lw=0.7, zorder=5))
        ax.plot([-0.20, -0.20, -1.10, -1.10], [0.50, 1.10, 1.10, 4.45], color='#444', lw=1.0, ls='--', zorder=5)
        ax.text(-0.95, 2.6, 'кабель к будке', fontsize=6.5, rotation=90)
        ax.plot([-0.30, -0.30, -1.55, -1.55], [-0.40, -0.62, -0.62, -0.135], color='#444', lw=1.0, ls='--', zorder=5)
        ax.add_patch(Rectangle((-1.636, -0.186), 0.172, 0.091, fc='#c8cbc6', ec='#111', lw=0.6, zorder=6))
        ax.text(-1.75, -0.85, 'коробка на плите', ha='right', fontsize=6.5)
        ax.text(0.0, -1.0, 'v2: тумба с мотором', ha='center', fontsize=7)
        ax.add_patch(Rectangle((-1.85, 1.25), 0.50, 0.50, fc='#c9c5ba', ec='#555', lw=0.5, zorder=5))    # v2.1: the camera mast
        ax.add_patch(Circle((-1.60, 1.50), 0.14, fc='#9aa0a0', ec='#222', lw=0.6, zorder=6))
        ax.plot([-1.60, -1.60], [1.75, 4.45], color='#444', lw=1.0, ls='--', zorder=5)
        ax.text(-1.95, 1.50, 'мачта: камера, прожектор', ha='right', va='center', fontsize=6.5)
    ax.add_patch(Rectangle((5.40, -0.20), 0.35 if v2 else 0.40, 0.40, fc='#c9c5ba', ec='#555', lw=0.5, zorder=4))
    ax.add_patch(Rectangle((-0.57 if not v2 else -0.30, -0.05), 6.57 if not v2 else 6.30, 0.10, fc='#c43a2a', ec='#300',
                           lw=0.4, zorder=6))
    ax.text(2.7, 0.18, 'стрела (закрыто)', ha='center', va='bottom', fontsize=6.5, color='#7a1d12')


def elevation(ax, axz, F, R_old, R_new, st, x0, x1, H_old, H_new, title):
    xs = np.linspace(x0, x1, 600)
    g0 = [sample(H_old, *F.world(x)) for x in xs]
    g1 = [sample(H_new, *F.world(x)) for x in xs]
    for R, col, lab, k in ((R_old, '#c0392b', 'U7', 0), (R_new, '#1f5fa8', 'v2', 1)):
        for r in R:
            if r['m'] not in PANELS:
                continue
            lc = F.loc([r['p'][0], r['p'][2]])
            if abs(lc[1]) > 0.05 or not (x0 - 1 < lc[0] < x1 + 1):
                continue
            y = r['p'][1]
            ax.add_patch(Rectangle((lc[0] - 1.24, y + 0.10), 2.48, 2.50, fc=col if k else 'none', ec=col, lw=0.6,
                                   alpha=0.25 if k else 0.9, zorder=3 + k))
            axz.plot([lc[0] - 1.24, lc[0] + 1.24], [y + 0.10, y + 0.10], color=col, lw=2.2 if k else 1.2,
                     alpha=0.95 if k else 0.8, zorder=3 + k, solid_capstyle='butt')
    ax.plot(xs, g0, color='#8a6d3b', lw=0.8, label='земля U7')
    ax.plot(xs, g1, color='#2e7d32', lw=1.2, label='земля после выравнивания')
    axz.plot(xs, np.array(g0) + 0.10, color='#8a6d3b', lw=0.6, ls=':', label='земля U7 + 0,10')
    axz.plot(xs, np.array(g1) + 0.10, color='#2e7d32', lw=0.8, ls=':', label='земля v2 + 0,10')
    a, b = st['local']
    for axx in (ax, axz):
        axx.axvspan(a, b, color='#f2d06b', alpha=0.25, zorder=0)
        axx.axvspan(a - st['ramp_start'], a, color='#f2d06b', alpha=0.10, zorder=0)
        axx.axvspan(b, b + st['ramp_end'], color='#f2d06b', alpha=0.10, zorder=0)
        axx.set_xlim(x0, x1)
    ax.set_title(title, fontsize=9, loc='left')
    ax.set_aspect('equal')
    ax.legend(fontsize=6.5, loc='upper right')
    axz.set_ylabel('низ плит, м', fontsize=7)
    axz.legend(fontsize=6, loc='lower left', ncol=2)
    axz.text(x0 + 0.3, axz.get_ylim()[1] - 0.02, 'красное — U7, синее — v2 (высота растянута)', fontsize=6.5, va='top')


def plan(ax, kind, F, st, R, v2, box, lab, labels=True):
    if v2:
        strip_outline(ax, st, F)
    draw_pieces(ax, piece_polys(R, F, box))
    (kit_gate if kind == 'gate' else kit_barrier)(ax, v2) if labels else (kit_gate if kind == 'gate' else kit_barrier)(ax, v2)
    ax.set_xlim(box[0], box[1])
    ax.set_ylim(box[2], box[3])
    ax.set_aspect('equal')
    ax.axhline(0, color='#999', lw=0.5, ls=':', zorder=0)
    ax.set_title(lab, fontsize=10, loc='left')
    ax.tick_params(labelsize=7)
    out_txt, in_txt = ('снаружи (подъезд)', 'внутри базы') if kind == 'gate' else ('подъезд (снаружи)', 'к базе, к будке (+y)')
    ax.text(box[0] + 0.2, box[2] + 0.15 * (box[3] - box[2]) / 6, out_txt, fontsize=7, va='bottom')
    ax.text(box[0] + 0.2, box[3] - 0.15 * (box[3] - box[2]) / 6, in_txt, fontsize=7, va='top')
    if v2 and box[1] - box[0] > 30:
        ax.text(st['local'][0] - st['ramp_start'] + 0.3, -st['half_width'] - st['falloff'] + 0.25,
                'жёлтое — ровная полоса %.3f м (полуширина 2 м); пунктир — край изменённой земли (откос 3 м поперёк, рампы '
                'по концам)' % st['height'], fontsize=7, color='#8a6a00', va='bottom')


def elev_zoom(ax, kind, F, R_old, R_new, x0, x1, H_old, H_new):
    xs = np.linspace(x0, x1, 400)
    for R, col, k in ((R_old, '#c0392b', 0), (R_new, '#1f5fa8', 1)):
        for r in R:
            if r['m'] not in PANELS:
                continue
            lc = F.loc([r['p'][0], r['p'][2]])
            if abs(lc[1]) > 0.05 or not (x0 - 1.3 < lc[0] < x1 + 1.3):
                continue
            ax.add_patch(Rectangle((lc[0] - 1.24, r['p'][1] + 0.10), 2.48, 2.50, fc=col if k else 'none', ec=col,
                                   lw=0.8 if k else 1.0, alpha=0.30 if k else 0.9, zorder=3 + k))
    ax.plot(xs, [sample(H_old, *F.world(x)) for x in xs], color='#8a6d3b', lw=0.9, label='земля U7')
    ax.plot(xs, [sample(H_new, *F.world(x)) for x in xs], color='#2e7d32', lw=1.4, label='земля v2')
    h = D[kind]['H']
    if kind == 'gate':
        for x_ in (-7.30, 0.30):
            ax.add_patch(Rectangle((x_ - 0.15, h), 0.30, 2.70, fc='#555b60', ec='#111', lw=0.6, zorder=6))
        ax.add_patch(Rectangle((-7.0, h + 0.10), 7.0, 2.30, fc='#3d5e46', ec='#123', lw=0.6, alpha=0.55, zorder=5))
        ax.text(-3.5, h + 1.2, 'полотно v2 (за линией, 0,50 м внутри)', ha='center', fontsize=7, color='white', zorder=7)
    else:
        ax.add_patch(Rectangle((-0.18, h), 0.36, 1.34, fc='#c8cbc6', ec='#111', lw=0.6, zorder=6))
        ax.plot([0.0, 6.0], [h + 1.17, h + 1.17], color='#c43a2a', lw=3, zorder=6)
    ax.set_xlim(x0, x1)
    ax.set_aspect('equal')
    ax.legend(fontsize=6.5, loc='upper right')
    ax.set_title('у %s в разрезе, 1:1: плиты U7 — красный контур, v2 — синие' % ('ворот' if kind == 'gate' else 'шлагбаума'),
                 fontsize=9, loc='left')
    ax.tick_params(labelsize=7)


def elev_feet(axz, F, R_old, R_new, st, x0, x1, H_old, H_new):
    xs = np.linspace(x0, x1, 600)
    for R, col, k in ((R_old, '#c0392b', 0), (R_new, '#1f5fa8', 1)):
        for r in R:
            if r['m'] not in PANELS:
                continue
            lc = F.loc([r['p'][0], r['p'][2]])
            if abs(lc[1]) > 0.05 or not (x0 - 1 < lc[0] < x1 + 1):
                continue
            y = r['p'][1]
            axz.plot([lc[0] - 1.24, lc[0] + 1.24], [y + 0.10, y + 0.10], color=col, lw=2.4 if k else 1.3,
                     alpha=0.95 if k else 0.85, zorder=3 + k, solid_capstyle='butt')
    axz.plot(xs, [sample(H_old, *F.world(x)) + 0.10 for x in xs], color='#8a6d3b', lw=0.6, ls=':', label='земля U7 + 0,10')
    axz.plot(xs, [sample(H_new, *F.world(x)) + 0.10 for x in xs], color='#2e7d32', lw=0.9, ls=':', label='земля v2 + 0,10')
    a, b = st['local']
    axz.axvspan(a, b, color='#f2d06b', alpha=0.25, zorder=0)
    axz.axvspan(a - st['ramp_start'], a, color='#f2d06b', alpha=0.10, zorder=0)
    axz.axvspan(b, b + st['ramp_end'], color='#f2d06b', alpha=0.10, zorder=0)
    axz.set_xlim(x0, x1)
    axz.set_ylabel('низ плит, м', fontsize=7)
    axz.legend(fontsize=6.5, loc='upper center', ncol=2)
    axz.set_title('низ плит вдоль линии (высота растянута): красные — U7, синие — v2; жёлтое — ровная полоса, светлее — рампы',
                  fontsize=9, loc='left')
    axz.tick_params(labelsize=7)


def page(kind, F, st, box, zoom, x_el, x_zoom, out, title, sub):
    R_old, R_new = U['records'], V['records']
    fig = plt.figure(figsize=(16, 15.5), dpi=100)
    gs = fig.add_gridspec(5, 2, height_ratios=[2.7, 2.7, 2.7, 3.0, 2.3], hspace=0.38, wspace=0.08, top=0.915)
    plan(fig.add_subplot(gs[0, :]), kind, F, st, R_old, False, box, 'было: U7 и КПП v1')
    plan(fig.add_subplot(gs[1, :]), kind, F, st, R_new, True, box, 'стало: v2')
    plan(fig.add_subplot(gs[2, 0]), kind, F, st, R_old, False, zoom, 'было, ближе')
    plan(fig.add_subplot(gs[2, 1]), kind, F, st, R_new, True, zoom, 'стало, ближе')
    elev_feet(fig.add_subplot(gs[3, :]), F, R_old, R_new, st, x_el[0], x_el[1], H0, H1)
    elev_zoom(fig.add_subplot(gs[4, :]), kind, F, R_old, R_new, x_zoom[0], x_zoom[1], H0, H1)
    import textwrap
    fig.text(0.125, 0.975, title, fontsize=14, ha='left', va='top')
    fig.text(0.125, 0.958, '\n'.join(textwrap.wrap(sub, 175)), fontsize=9, color='#444', ha='left', va='top')
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)


S = {s['name']: s for s in V['levelling']}
G = Frame('gate')
page('gate', G, S['gate'], (-34, 26, -6.0, 6.0), (-10.5, 4.5, -2.4, 3.2), (-34, 26), (-12.5, 6.5), 'plan_gate.png',
     'Ворота базы: стены в одну линию, на одной высоте, столбы по краям',
     'Кадр корня Gate: x вдоль стены (+ запад, сторона, куда откатывается полотно), y — внутрь базы. Западный ряд начинается у '
     'западного столба (+1 плита на месте сетчатой секции v1), восточный кончается у восточного; полоса выравнивания %.3f м, '
     'по краям рампы %.1f / %.1f м.' % (S['gate']['height'], S['gate']['ramp_start'], S['gate']['ramp_end']))
B = Frame('barrier')
page('barrier', B, S['barrier'], (-30, 36, -7.5, 7.5), (-4.5, 9.5, -2.4, 3.2), (-30, 36), (-6.0, 12.0), 'plan_barrier.png',
     'Шлагбаум КПП: крылья ПО-2 на одной высоте',
     'Кадр корня Barrier: x от тумбы вдоль стрелы к упору, y — к будке и базе. Места крыльев не менялись; полоса выравнивания '
     '%.4f м (высота площадки переноса КПП), рампы %.1f / %.1f м.' % (S['barrier']['height'], S['barrier']['ramp_start'],
                                                                       S['barrier']['ramp_end']))
print('ok')
