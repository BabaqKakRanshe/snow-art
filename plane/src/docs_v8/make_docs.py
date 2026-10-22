"""Fill the v8 docs from the export data: python3 make_docs.py <export_log> <verify_log>"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, '..', 'export', 'unity_v8', 'Assets', 'UtilityPlane')
D = lambda n: json.load(open(os.path.join(PKG, 'Data', n)))
exp, ver = open(sys.argv[1]).read(), open(sys.argv[2]).read()
m = re.search(r'UNITY objects (\d+) render tris (\d+) cockpit tris (\d+) colliders (\d+) sockets (\d+) static colliders (\d+)', exp)
n_children, tris, tris_cp, n_col, n_sock, n_col_static = map(int, m.groups())
radio = int(re.search(r'Display_Radio faces (\d+)', exp).group(1))
v = re.search(r'objects (\d+) imported (\d+) missing \[\] extra \[\]', ver)
assert v, 'verify failed'
n_obj = int(v.group(1))
pos_err = float(re.search(r'max pos err mm ([\d.]+)', ver).group(1))
assert 'parent mismatches 0' in ver and 'rot errors > 0.01 deg: 0' in ver, 'verify mismatch'
socks, facts, texel, vols = D('sockets.json'), D('model_facts.json'), D('atlas_texel.json'), D('interaction_volumes.json')
ph = facts['parkedHeights']
n_static = sum(1 for k, x in socks.items() if x['parent'] == 'Sockets')
rows = ['| Атлас | Материал | Разрешение | px на метр | Площадь, м² | Деталь, тайлинг |', '|---|---|---|---|---|---|']
if isinstance(texel, dict):                     # old test format: {atlas: {metres_per_uv, area_m2}}
    texel = [dict(atlas=a, material='M_' + a, metresPerUV=x['metres_per_uv'], areaM2=x['area_m2'],
                  pxPerMetre=(2048 if a == 'Details' else 4096) / x['metres_per_uv']) for a, x in texel.items()]
for t in texel:
    res = round(t['pxPerMetre'] * t['metresPerUV'])
    det = f"{t['detail']}, {t['detailTiling']:g}" if t.get('detail') else '—'
    rows.append(f"| {t['atlas']} | {t['material']} | {res} | {t['pxPerMetre']:.0f} | {t['areaM2']:.1f} | {det} |")
order = lambda k: (0 if socks[k]['parent'] == 'Sockets' else 1, k)
tab = ['| Сокет | Родитель | X, Y, Z |', '|---|---|---|']
for k in sorted(socks, key=lambda k: k):
    x = socks[k]
    p = x.get('position', x.get('position_prefab'))
    tab.append(f"| {k} | {x['parent']} | {p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f} |")
disp = D('displays.json')
dtab = ['| Квад | Блок | Центр X, Y, Z | Окно, мм | Пиксели (10/мм) | Питание |', '|---|---|---|---|---|---|']
for k, x in disp.items():
    p_ = x['position_prefab']
    dtab.append(f"| {k} | {x['unit']} | {p_[0]:.3f}, {p_[1]:.3f}, {p_[2]:.3f} | {x['size'][0] * 1000:.1f} × "
                f"{x['size'][1] * 1000:.1f} | {x['suggestedPixels'][0]} × {x['suggestedPixels'][1]} | `{x['power']}` |")
val = {
    'N_OBJ': n_obj, 'POS_ERR': f'{pos_err:g}', 'PITCH': f"{facts['parkedPitchDeg']:.2f}",
    'ROOTH_ABS': f"{abs(facts['parkedRootHeight']):.3f}",
    'SILL_P': f"{ph['pilotDoorSill'][1]:.2f}–{ph['pilotDoorSill'][0]:.2f}",
    'SILL_C': f"{ph['cargoDoorSill'][1]:.2f}–{ph['cargoDoorSill'][0]:.2f}",
    'EYE': f"{ph['pilotEye']:.2f}", 'PROP_AXIS': f"{ph['propAxis']:.2f}",
    'PROP_CLR_P': f"{ph['propTipClearance']:.2f}", 'PROP_CLR_L': f"{ph['propTipClearanceTailUp']:.2f}",
    'STEP_C': f"{ph['cargoStepTop']:.2f}", 'STEP_P': f"{ph['pilotStepTop']:.2f}",
    'N_SOCK_STATIC': n_static, 'N_SOCK': n_sock, 'N_COL': n_col, 'N_COL_STATIC': n_col_static, 'N_IV': len(vols),
    'TRIS_K': round(tris / 1000), 'TRIS_CP_K': round(tris_cp / 1000), 'DISPLAY_TABLE': '\n'.join(dtab),
    'TEXEL_TABLE': '\n'.join(rows),
}
lodf = D('lod.json')                                       # v8: LOD groups
GN = {'Exterior': ('Экстерьер', 'корень `UtilityPlane`'), 'Cockpit': ('Кабина', '`Cockpit`')}
lrows = []
for g in lodf['groups']:
    lv = g['levels']
    def _pl(n, forms=('рендерер', 'рендерера', 'рендереров')):
        k = 2 if 11 <= n % 100 <= 14 else (0 if n % 10 == 1 else (1 if 2 <= n % 10 <= 4 else 2))
        return f'{n} {forms[k]}'
    cells = [f"≥ {l['screenRelativeHeight']:g}: {_pl(len(l['renderers']))}, {l['triangles'] / 1000:.1f} тыс. треуг."
             for l in lv]
    lrows.append(f"| {GN[g['name']][0]} | {GN[g['name']][1]} | {cells[0]} | {cells[1]} | {cells[2]} | "
                 f"< {lv[-1]['screenRelativeHeight']:g} |")
val['LOD_TABLE'] = '\n'.join(lrows)
lad = facts['ladder']                                     # v7 (M5): step ladder reach numbers
assert lad['eyeAboveCap'] > 0 and lad['sightLineClearanceOverWing'] > 0 and lad['capTopVisible'], lad
val.update({'LAD_PLATFORM': f"{lad['platformHeight']:.2f}", 'LAD_CAP': f"{lad['fuelCapHeight']:.2f}",
            'LAD_REACH': f"{lad['eyeToCap']:.2f}", 'LAD_EYE_ABOVE_CAP': f"{lad['eyeAboveCap']:.2f}",
            'LAD_CLEAR': f"{lad['sightLineClearanceOverWing']:.2f}", 'LAD_LOOK': f"{lad['lookDownDeg']:.0f}",
            'LAD_LATERAL': f"{lad['lateralToCap']:.2f}", 'LAD_STANDOFF': f"{lad['standOffLeadingEdge']:.2f}",
            'LAD_EYE': f"{lad['eyeHeight']:.2f}"})
cab = json.load(open(os.path.join(HERE, '..', 'tex', 'v8', 'cabin_ao_stats.json')))   # v8: cabin AO medians
for k_, l_ in (('AO_C', 'C'), ('AO_I', 'I'), ('AO_F', 'F')):
    val[k_] = f"{cab[l_]['result_median']:.2f}"
assert len(vols) == 65, len(vols)
for name in ('UNITY_CONTRACT.md', 'README.md', 'COMPONENTS.md'):
    src = os.path.join(HERE, name)
    if not os.path.exists(src):
        continue
    s = open(src).read()
    s = s.replace('<!--SOCKETS-->', '\n'.join(tab))
    for k, x in val.items():
        s = s.replace('{' + k + '}', str(x))
    left = re.findall(r'\{[A-Z_]+\}', s)
    assert not left, (name, left)
    open(os.path.join(PKG, name), 'w').write(s)
    print('wrote', name, 'placeholders left', left)
