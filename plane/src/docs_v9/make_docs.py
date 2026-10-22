"""Fill the v9 docs from the export data: python3 make_docs.py <export_log> <verify_log>
(templates UNITY_CONTRACT.md / README.md / COMPONENTS.md here -> export/unity_v9/Assets/UtilityPlane/)"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, '..', 'export', 'unity_v9', 'Assets', 'UtilityPlane')
D = lambda n: json.load(open(os.path.join(PKG, 'Data', n)))
exp, ver = open(sys.argv[1]).read(), open(sys.argv[2]).read()
m = re.search(r'UNITY objects (\d+) render tris (\d+) cockpit tris (\d+) colliders (\d+) sockets (\d+) static colliders (\d+)', exp)
n_children, tris, tris_cp, n_col, n_sock, n_col_static = map(int, m.groups())
v = re.search(r'objects (\d+) imported (\d+) missing \[\] extra \[\]', ver)
assert v, 'verify failed'
n_obj = int(v.group(1))
pos_err = float(re.search(r'max pos err mm ([\d.]+)', ver).group(1))
assert 'parent mismatches 0' in ver and 'rot errors > 0.01 deg: 0' in ver and 'VERIFY OK' in ver, 'verify mismatch'
socks, facts, texel, vols = D('sockets.json'), D('model_facts.json'), D('atlas_texel.json'), D('interaction_volumes.json')
ph = facts['parkedHeights']
n_static = sum(1 for k, x in socks.items() if x['parent'] == 'Sockets')
f3 = lambda p: f'{p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}'
f2 = lambda p: f'{p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}'
rows = ['| Атлас | Материал | Разрешение | px на метр | Площадь, м² | PSX | Деталь, тайлинг |', '|---|---|---|---|---|---|---|']
for t in texel:
    res = round(t['pxPerMetre'] * t['metresPerUV'])
    det = f"{t['detail']}, {t['detailTiling']:g}" if t.get('detail') else '—'
    rows.append(f"| {t['atlas']} | {t['material']} | {res} | {t['pxPerMetre']:.0f} | {t['areaM2']:.1f} | "
                f"{'да' if t.get('psx') else '—'} | {det} |")
tab = ['| Сокет | Родитель | X, Y, Z | Вперёд (+Z) |', '|---|---|---|---|']
for k in sorted(socks):
    x = socks[k]
    p = x.get('position', x.get('position_prefab'))
    fw = f2(x['forward']) if 'forward' in x and not k.startswith('Socket_Audio_') else ''
    tab.append(f"| {k} | {x['parent']} | {f3(p)} | {fw} |")
disp = D('displays.json')
dtab = ['| Квад | Блок | Центр X, Y, Z | Окно, мм | Пиксели (10/мм) | Питание |', '|---|---|---|---|---|---|']
for k, x in disp.items():
    p_ = x['position_prefab']
    dtab.append(f"| {k} | {x['unit']} | {f3(p_)} | {x['size'][0] * 1000:.1f} × "
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
lodf = D('lod.json')
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
lad = facts['ladder']
assert lad['eyeAboveCap'] > 0 and lad['sightLineClearanceOverWing'] > 0 and lad['capTopVisible'], lad
val.update({'LAD_PLATFORM': f"{lad['platformHeight']:.2f}", 'LAD_CAP': f"{lad['fuelCapHeight']:.2f}",
            'LAD_REACH': f"{lad['eyeToCap']:.2f}", 'LAD_EYE_ABOVE_CAP': f"{lad['eyeAboveCap']:.2f}",
            'LAD_CLEAR': f"{lad['sightLineClearanceOverWing']:.2f}", 'LAD_LOOK': f"{lad['lookDownDeg']:.0f}",
            'LAD_LATERAL': f"{lad['lateralToCap']:.2f}", 'LAD_STANDOFF': f"{lad['standOffLeadingEdge']:.2f}",
            'LAD_EYE': f"{lad['eyeHeight']:.2f}"})
cab = json.load(open(os.path.join(HERE, '..', 'tex', 'v8', 'cabin_ao_stats.json')))   # v8 cabin AO medians (unchanged)
for k_, l_ in (('AO_C', 'C'), ('AO_I', 'I'), ('AO_F', 'F')):
    val[k_] = f"{cab[l_]['result_median']:.2f}"
# ---------------------------------------------------------------- v9
N_IV_V8, N_SOCK_V8 = 65, 79
n_new = sum(1 for x in vols if x['id'].startswith(('PaxSeat', 'Stow_')))
assert len(vols) == N_IV_V8 + n_new == 79, (len(vols), n_new)
assert n_sock == N_SOCK_V8 + 46, n_sock
val.update({'N_IV_V8': N_IV_V8, 'N_SOCK_V8': N_SOCK_V8})
ps = facts['paxSeats']
val.update({'PAX_H': f"{ps['seatHeightAboveFloor']:.2f}", 'PAX_D': f"{ps['panDepth']:.2f}",
            'PAX_AISLE_LEGS': f"{ps['aisleBetweenFacingLegs']:.2f}",
            'PAX_W': f"{ps['panWidth']:.2f}", 'PAX_AISLE': f"{ps['aisleBetweenFacingPans']:.2f}",
            'PAX_FOLD_TOP': f"{ps['foldedPanTopAboveFloor']:.2f}",
            'PAX_BACK': f"{ps['backCanvas'][0]:.2f} × {ps['backCanvas'][1]:.2f} м (ширина × высота)"})
pax = D('pax_seats.json')
prow = []
for st in pax['seats']:
    s_ = '+1' if st['foldSign'] > 0 else '−1'
    where = {'ahead of the cargo doors': 'впереди проёмов', 'behind the cargo doors': 'за проёмами'}[st['position']]
    side = {'left': 'левый борт', 'right': 'правый борт'}[st['side']]
    prow.append(f"| {st['id']} ({side}, {where}, № {st['number']}) | {st['index']} | {f3(st['hinge'])} | "
                f"{st['pelvis']} / {st['eye']} / {st['exit']} | {s_} |")
val['PAX_TABLE'] = '\n'.join(prow)
hor = D('horror.json')
SC_RU = {'bay floor at the rear bulkhead, facing the cockpit': 'пол отсека у задней перегородки, лицом к кабине',
         'bay floor right behind the cargo barrier, facing the crew': 'пол отсека сразу за сеткой, лицом к экипажу',
         'face point outside the window, looking in': 'лицо за окном снаружи, смотрит внутрь',
         'face point on the cowling in front of the windshield, looking at the crew': 'лицо на капоте перед лобовым стеклом, смотрит на экипаж',
         'ground 2.6 m ahead of the propeller': 'земля в 2.6 м перед винтом',
         'ground behind the tail': 'земля за хвостом',
         'ground under the wing, facing the fuselage': 'земля под крылом, лицом к фюзеляжу',
         'ground under the fuselage (crawling)': 'земля под фюзеляжем (ползком)'}
srow = ['| Сокет | X, Y, Z | Вперёд (+Z) | Где |', '|---|---|---|---|']
for k, x in hor['scare'].items():
    srow.append(f"| {k} | {f3(x['position'])} | {f2(x['forward'])} | {SC_RU.get(x['note'], x['note'])} |")
val['SCARE_TABLE'] = '\n'.join(srow)
AU_RU = {'cabin speaker under the overhead console (radio voices)': 'динамик кабины под потолочной консолью (голоса в эфире)',
         'pilot headset hanging behind the seat (whispers)': 'гарнитура пилота на крючке за креслом (шёпот)',
         'right headset hanging behind the seat': 'правая гарнитура на крючке за креслом',
         'stall warning horn, upper left corner of the windshield': 'сирена сваливания, левый верхний угол лобового стекла',
         'cargo bay (creaks, cargo shifting)': 'отсек (скрип, сдвиг груза)',
         'on top of the wing centre section (steps)': 'крыша над центропланом (шаги)',
         'under the cabin floor (knocks)': 'под полом кабины (стук)',
         'emergency locator transmitter in the tail cone': 'аварийный маяк в хвостовой части',
         'left door seal (whistle)': 'уплотнитель левой двери (свист)',
         'right door seal (whistle)': 'уплотнитель правой двери (свист)',
         'left wing tank (sloshing)': 'левый бак в крыле (плеск)', 'right wing tank (sloshing)': 'правый бак в крыле (плеск)'}
arow = ['| Сокет | X, Y, Z | Что |', '|---|---|---|']
for k, x in hor['audio'].items():
    arow.append(f"| {k} | {f3(x['position'])} | {AU_RU.get(x['note'], x['note'])} |")
val['AUDIO_TABLE'] = '\n'.join(arow)
kit = D('survival_kit.json')
krow = []
for it in kit['items']:
    sz = it['sizeM']
    sk = ', '.join(f"`{k}` ({f2(p)})" for k, p in it['sockets'].items()) or '—'
    extra = ', ' + ', '.join(f'`{c}`' for c in it['children']) if it['children'] else ''
    krow.append(f"| {it['model']} → `{it['prefab']}` | {it['label']}, {it['massKg']:g} кг (TEMPORARY) | "
                f"{sz[0]:.3f} × {sz[1]:.3f} × {sz[2]:.3f} | {sk} | {', '.join('`' + c + '`' for c in it['colliders'])}{extra} |")
val['SURV_TABLE'] = '\n'.join(krow)
for name in ('UNITY_CONTRACT.md', 'README.md', 'COMPONENTS.md'):
    src = os.path.join(HERE, name)
    s = open(src).read()
    s = s.replace('<!--SOCKETS-->', '\n'.join(tab))
    for k, x in val.items():
        s = s.replace('{' + k + '}', str(x))
    left = re.findall(r'\{[A-Z_0-9]+\}', s)
    assert not left, (name, left)
    open(os.path.join(PKG, name), 'w').write(s)
    print('wrote', name, len(s))
