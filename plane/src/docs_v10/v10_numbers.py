"""v9 vs v10 numbers for the docs and the Unity task (one source for make_docs.py and fill_prompt10.py).
values() -> dict of V10_* placeholders and prompt numbers."""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OPT = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt'
P9 = os.path.join(ROOT, 'export', 'unity_v9', 'Assets', 'UtilityPlane')
P10 = os.path.join(ROOT, 'export', 'unity_v10', 'Assets', 'UtilityPlane')
NOSHADOW = ("Needle_", "Knob_", "SW_", "Guard_", "Rheo_", "Pull_", "Btn_", "Lamp_", "Lens_", "Display_", "ATT_", "HDG_",
            "TC_", "Clock_", "ALT_", "Compass_", "Belt_", "Lock_", "PropBlur", "PropDisc", "Glass")
PSX = ('T_Airframe_', 'T_Wing_', 'T_Details_', 'T_Survival_')
INTERIOR = ('T_Cockpit_', 'T_Interior_', 'T_Floor_', 'T_Seats_', 'T_Fittings_')


def tex_vram(folder, v10):
    """GPU memory (MB) of the plane textures under the Setup's import rules (PC 'Compressed': RGB DXT1 0.5 B/px,
    RGBA DXT5 / normal BC5|DXT5nm 1 B/px; PSX and fog brushes uncompressed RGBA32 4 B/px; mips +1/3)."""
    tot = 0.0
    for f in os.listdir(folder):
        if not f.endswith('.png'):
            continue
        n = f[:-4]
        im = Image.open(os.path.join(folder, f))
        w, h = im.size
        if 'Webbing' in n or '_Detail_' in n or n.startswith('T_Prop') or n.startswith(PSX):
            mx = 512
        elif n.startswith('T_GlassFog') or (v10 and n.startswith(INTERIOR)):
            mx = 1024
        elif n.startswith('T_FogPrint_'):
            mx = 128
        else:
            mx = 2048 if v10 else 4096
        s = min(1.0, mx / max(w, h))
        W, H = round(w * s), round(h * s)
        if n.startswith('T_FogPrint_'):
            bpp, mips = 4, False
        elif n.startswith(PSX):
            bpp, mips = 4, True
        elif n.endswith('_Normal'):
            bpp, mips = 1, True
        elif im.mode in ('RGBA', 'LA'):
            bpp, mips = 1, True
        else:
            bpp, mips = 0.5, True
        tot += W * H * bpp * (4 / 3 if mips else 1)
    return tot / 2 ** 20


def png_mb(folder):
    return sum(os.path.getsize(os.path.join(folder, f)) for f in os.listdir(folder) if f.endswith('.png')) / 1e6


def audit(path):
    return {r['name']: r for r in json.load(open(path)) if r['type'] == 'MESH'}


def lod0_names(lod):
    return [n for g in lod['groups'] for n in g['levels'][0]['renderers']]


def casters(au, lod):
    """LOD0 shadow-caster triangles: Setup rules (small parts off), v10 proxies replace their parts."""
    prox = {p['source']: p['renderer'] for p in lod.get('shadowProxies', [])}
    t = 0
    for n in lod0_names(lod):
        if n in prox.values():
            t += au[n]['tris']
            continue
        if n in prox or n.startswith(NOSHADOW) or n.endswith(('_Glass', '_Fog')):
            continue
        t += au[n]['tris']
    return t


def viewcmp():
    """result line of the v9 / v10 view comparison (S/opt/vis2/viscmp.py)"""
    import re
    log = open(os.path.join(OPT, 'vis2', 'cmp_b.log')).read()
    m = re.search(r'TOTAL defect px (\d+) of (\d+)', log)
    bad, tot = int(m.group(1)), int(m.group(2))
    rep = json.load(open(os.path.join(OPT, 'vis2', 'cmp_b', 'report.json')))
    objs = sorted({n for v in rep for c in v['comps'] for n, _ in c['A'] + c['B']})
    if bad == 0:
        return f'отличий нет ({len(rep)} точек, {tot / 1e6:.0f} млн пикселей)'
    assert objs == ['CP_BarrierNets'], objs
    return (f'{bad} пикселей из {tot / 1e6:.0f} млн — на сетке-перегородке `CP_BarrierNets`, которая не менялась: там в '
            f'v9 две грани лежат в одной плоскости с разной текстурой, и какая из них видна, решает порядок отрисовки '
            f'(то же мерцание есть в v9)')


def lodpop():
    """LOD switch check (S/opt/vis2/lodcheck.py, log lodcheck3.log)"""
    import re
    log = open(os.path.join(OPT, 'vis2', 'lodcheck3.log')).read()
    r = {}
    for m in re.finditer(r'(v9|v10) LOD(\d)->LOD(\d) at (\d+) m: plane px \d+, silhouette changes ([\d.]+) %, normal >25deg ([\d.]+) %', log):
        r[(m.group(1), m.group(2), m.group(3))] = (m.group(4), float(m.group(5)), float(m.group(6)))
    f = lambda x: f'{x:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
    out = []
    for a, b in (('0', '1'), ('1', '2')):
        d, s10, n10 = r[('v10', a, b)]
        _, s9, n9 = r[('v9', a, b)]
        out.append(f'LOD{a} → LOD{b} ({d} м): контур меняется у {f(s10)} % пикселей самолёта (v9 — {f(s9)} %), '
                   f'свет (нормаль больше чем на 25°) — у {f(n10)} % (v9 — {f(n9)} %)')
    return '; '.join(out)


def lod_methods():
    """which LOD meshes meshoptimizer made and which Decimate (export log)"""
    import re, ast
    log = open(os.path.join(ROOT, 'logs10', 'exp10.log')).read()
    m = ast.literal_eval(re.search(r"lod methods (\{.*\})", log).group(1))
    mo = sorted(k for k, v in m.items() if v == 'meshoptimizer')
    de = sorted(k for k, v in m.items() if v == 'decimate')
    return (f'Тем же методом, что LOD0 (meshoptimizer: швы UV, жёсткие рёбра и границы материалов не рвутся) — '
            f'{len(mo)} мешей ({", ".join("`" + k + "`" for k in mo)}); где швы не дают дойти до бюджета — как в v8–v9, '
            f'Decimate Blender ({", ".join("`" + k + "`" for k in de)}).')


def values():
    l9 = json.load(open(os.path.join(P9, 'Data', 'lod.json')))
    l10 = json.load(open(os.path.join(P10, 'Data', 'lod.json')))
    a9 = audit(os.path.join(OPT, 'audit_fbx.json'))
    a10 = audit(os.path.join(OPT, 'audit_fbx_v10.json'))

    def lv(l, g):
        return [x['triangles'] for x in next(gg for gg in l['groups'] if gg['name'] == g)['levels']]
    e9, e10, c9, c10 = lv(l9, 'Exterior'), lv(l10, 'Exterior'), lv(l9, 'Cockpit'), lv(l10, 'Cockpit')
    k = lambda x: f'{x / 1000:.1f}'
    trip = lambda xs: ' / '.join(k(x) for x in xs)
    prox = {p['renderer'] for p in l10.get('shadowProxies', [])}
    verts9 = sum(a9[n]['split_verts'] for n in lod0_names(l9))
    verts10 = sum(a10[n]['split_verts'] for n in lod0_names(l10) if n not in prox)
    mesh_bytes = lambda au: sum(r['split_verts'] * (48 + 8 * max(0, r['uv_layers'] - 1)) +
                                r['tris'] * 3 * (4 if r['split_verts'] > 65535 else 2) for r in au.values())
    rt = [r for n, r in a10.items() if n.startswith('COL_') or n == 'Glass_Fog' or n.endswith('_Fog')]
    rt_bytes = sum(r['split_verts'] * 48 + r['tris'] * 3 * 2 for r in rt)
    opt = {r['name']: r for r in json.load(open(os.path.join(OPT, 'opt_v10b_report.json')))}
    vis = json.load(open(os.path.join(OPT, 'vis_v10b_report.json')))['removed']
    hidden = sum(b - a for b, a in vis.values())
    names = sorted(opt, key=lambda n: -opt[n]['src'])[:16]
    rows = ['| Часть (в FBX — внутри) | v9 | v10 | Допуск формы | Невидимых граней удалено |', '|---|---|---|---|---|']
    for n in names:
        r = opt[n]
        final = r['new'] - (vis[n][0] - vis[n][1] if n in vis else 0)
        host = 'Body' if n.startswith('src_') else ('Cockpit_Static' if n.startswith('CP_') else n)
        label = f'`{n}` ({host})' if host != n else f'`{n}`'
        rows.append(f"| {label} | {r['src']} | {final} | {r['tol_mm']:g} мм | "
                    f"{(vis[n][0] - vis[n][1]) if n in vis else '—'} |")
    v = {
        'V10_LOD0_K9': k(e9[0] + c9[0]), 'V10_LOD0_K': k(e10[0] + c10[0]),
        'V10_EXT9': trip(e9), 'V10_EXT': trip(e10), 'V10_CP9': trip(c9), 'V10_CP': trip(c10),
        'V10_SHADOW9': k(casters(a9, l9)), 'V10_SHADOW': k(casters(a10, l10)),
        'V10_VERTS9': k(verts9), 'V10_VERTS': k(verts10),
        'V10_VRAM9': f'{tex_vram(os.path.join(P9, "Textures"), False):.0f}',
        'V10_VRAM': f'{tex_vram(os.path.join(P10, "Textures"), True):.0f}',
        'V10_PNG9': f'{png_mb(os.path.join(P9, "Textures")):.0f}', 'V10_PNG': f'{png_mb(os.path.join(P10, "Textures")):.0f}',
        'V10_MESHMB9': f'{mesh_bytes(a9) / 2 ** 20:.0f}', 'V10_RT_COUNT': len(rt), 'V10_RT_KB': f'{rt_bytes / 1024:.0f}',
        'V10_HIDDEN': hidden, 'V10_PARTS_TABLE': '\n'.join(rows), 'V10_VIEWCMP': viewcmp(),
        'V10_LODPOP': lodpop(), 'V10_LOD_METHODS': lod_methods(),
    }
    return v


if __name__ == '__main__':
    for kk, vv in values().items():
        print(kk, '=', vv if '\n' not in str(vv) else '\n' + vv)
