"""Forest Update 7: the fence and road-block package over Update 6 (as 6 over 5, 5 over 4, 4 over 3).

  Models/   22 new FBX (u7_export.py): the PO-2 concrete fence (ConcreteFence, _b, _Broken, _Sign, _Plain, _Socket, _Wicket),
            the new chain-link (ChainFence, ChainFence_Torn), WireCoil, the road blocks (RoadBlock_FBS, RoadBlock_Jersey,
            RoadBlock_Jersey_Striped, RoadBlock_Cube), the tank traps (TankTooth, TankTooth_b, Hedgehog, WireBarricade,
            Abatis, Abatis_b) and the signs (Sign_Halt, Sign_NoEntry)
  Textures/ 7 new (T_Fence_*: two atlases, the sign panel, four cut-outs) and 9 replaced in place (same names and GUIDs:
            the chain-link, barbed and rust cut-outs of Updates 4 and 5 - the new netting without the shimmer)
  Data/     Forest_Layout.json = Update 6's with Update 3's chain-link fence (213 FenceChain) out of rocks, the 528 U7
            placements at the end of rocks, 54 trees out of trees (the strips cleared along the tank-trap lines, the wings);
            Forest_Materials.json = Update 6's + 7 materials at the end, the 9 chain-link / barbed / rust materials
            one-sided; the block u7 in the layout lists it all
  README.md Update 6's README + the section "Обновление 7"

python3 u7_build.py <fbx_dir> <u6_dir> <u3raw_dir> <out_dir>"""
import os, sys, json, shutil, hashlib, tarfile, io, time, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u4_build as U4

ROOT = 'Assets/Locations/Forest'
LAYOUT7 = os.path.join(HERE, 'out/forest_update7/u7_layout.json')
NEW_TEX = [('tex/fence/T_Fence_Concrete_BaseColor.png', 'T_Fence_Concrete_A_px.png'),
           ('tex/fence/T_Fence_Props_BaseColor.png', 'T_Fence_Props_A_px.png'),
           ('tex/fence/T_Fence_Panel_BaseColor.png', 'T_Fence_Panel_A_px.png'),
           ('tex/fence/T_Fence_ChainLink.png', 'T_Fence_ChainLink_A_px.png'),
           ('tex/fence/T_Fence_Barbed.png', 'T_Fence_Barbed_A_px.png'),
           ('tex/fence/T_Fence_ChainBarbed.png', 'T_Fence_ChainBarbed_A_px.png'),
           ('tex/fence/T_Fence_Razor.png', 'T_Fence_Razor_A_px.png')]
# replaced in place: the file, its GUID (Update 4 / 5) and the md5 the project should have before
REPL_TEX = {
    'T_Base_ChainLink_A_px.png': ('75f2403c3883bad9ac80db0706d7c7f5', '0c095e108a85c9dd81d2761efd404063', 5),
    'T_Base_Barbed_A_px.png': ('8529c4c4cdc91d13918f08b814389090', 'b6ee110f8eeee04ee70f586ee4490146', 5),
    'T_Base_Rust_A_px.png': ('0500de58628a80a0adb4f8daf8fd7c08', 'cc4fa592645ec382a581d7e02b2db705', 5),
    'T_Kpp_ChainLink_A_px.png': ('ac5bcfa2d95c69a612edbf4575ebe5e9', '0c095e108a85c9dd81d2761efd404063', 4),
    'T_Kpp_Barbed_A_px.png': ('013a7824eeb83fe3a24835d1d91c2756', 'a629f3711cfb39438e605f480a165395', 4),
    'T_Yard_ChainLink_A_px.png': ('cd632a2d29bfb27751382ffd77164752', '0c095e108a85c9dd81d2761efd404063', 4),
    'T_Yard_Barbed_A_px.png': ('503d804f6f4071330dfa328a3febbe35', 'a629f3711cfb39438e605f480a165395', 4),
    'T_Road_ChainLink_A_px.png': ('b6f8173ec2ca5d3702cb126b4bcfaf2d', '0c095e108a85c9dd81d2761efd404063', 4),
    'T_Road_Barbed_A_px.png': ('b622cc7d5c10b24c74064dc8ef9b74bd', '7d0344f1344c0d9c27ec1925a8598e41', 4),
}


def cut1(name, tex):
    """a cut-out drawn on one side only (Cull Back): the models carry two faces back to back"""
    return U4.spec(name, tex, typ='cutout', cutoff=0.5, two=False, inst=True)


NEW_MATS = [
    U4.atlas('M_Fence_Concrete', 'T_Fence_Concrete_A_px.png'),
    U4.atlas('M_Fence_Props', 'T_Fence_Props_A_px.png'),
    # the plates and boards glow a little at night, as the base's (M_Base_Panel)
    U4.spec('M_Fence_Panel', 'T_Fence_Panel_A_px.png', emap='T_Fence_Panel_A_px.png', emission=(1, 1, 1), ei=0.06),
    cut1('M_Fence_ChainLink', 'T_Fence_ChainLink_A_px.png'), cut1('M_Fence_Barbed', 'T_Fence_Barbed_A_px.png'),
    cut1('M_Fence_ChainBarbed', 'T_Fence_ChainBarbed_A_px.png'), cut1('M_Fence_Razor', 'T_Fence_Razor_A_px.png'),
]
ONE_SIDED = ['M_Base_ChainLink', 'M_Base_Barbed', 'M_Base_Rust', 'M_Kpp_ChainLink', 'M_Kpp_Barbed', 'M_Yard_ChainLink',
             'M_Yard_Barbed', 'M_Road_ChainLink', 'M_Road_Barbed']
UNPLACED = ('ChainFence', 'ChainFence_Torn', 'ConcreteFence_Plain')     # in the kit, not on the map


def guid_of(path):
    return hashlib.md5(('snow/Forest/Update7/' + path).encode()).hexdigest()


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main(fbx_dir, u6_dir, u3raw_dir, out_dir):
    rep = json.load(open(os.path.join(fbx_dir, 'u7_export_report.json')))
    U7 = json.load(open(LAYOUT7))
    u6stage = os.path.join(u6_dir, 'stage')
    stage = os.path.join(out_dir, 'stage')
    if os.path.exists(stage):
        shutil.rmtree(stage)
    for sub in ('Models', 'Textures', 'Data'):
        os.makedirs(os.path.join(stage, ROOT, sub))
    u3guid = {}
    for g in os.listdir(u3raw_dir):
        p = os.path.join(u3raw_dir, g, 'pathname')
        if os.path.exists(p):
            u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
    entries, changes, base, src_of = [], [], {}, {}

    def folder(path):
        g = u3guid[path]
        entries.append((path, g, None, open(os.path.join(u3raw_dir, g, 'asset.meta'), encoding='utf-8').read()))

    for f in ('Assets/Locations', ROOT, f'{ROOT}/Models', f'{ROOT}/Textures', f'{ROOT}/Data'):
        folder(f)

    # ---- models: all new
    for name in sorted(rep):
        pn = f'{ROOT}/Models/{name}.fbx'
        assert pn not in u3guid, pn
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(fbx_dir, rep[name]['file']), dst)
        entries.append((pn, guid_of(pn), dst, None))
        src_of[name] = 'new'
    assert len(rep) == 22, len(rep)

    # ---- textures: new ones, then the replaced ones with their GUIDs
    for src, dn in NEW_TEX:
        pn = f'{ROOT}/Textures/{dn}'
        assert pn not in u3guid, pn
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(HERE, src), dst)
        entries.append((pn, guid_of(pn), dst, None))
    for dn, (g, old_md5, upd) in REPL_TEX.items():
        pn = f'{ROOT}/Textures/{dn}'
        assert hashlib.md5((f'snow/Forest/Update{upd}/' + pn).encode()).hexdigest() == g, dn
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(HERE, 'tex/fence/replacements', dn), dst)
        assert md5(dst) != old_md5, f'{dn}: the replacement is the old file'
        entries.append((pn, g, dst, None))
        base[pn] = old_md5
    changes.append('Textures: replaced in place (same names and GUIDs): ' + ', '.join(sorted(REPL_TEX)) +
                   ' - the netting with 2 px wires in 12.5 cm diamonds (was 1 px in 6.25 cm), the barbed and rusty wire '
                   '2 px; the same sizes and strand positions, the models\' UVs unchanged')

    def data_file(name, src_dir, dump):
        pn = f'{ROOT}/Data/{name}'
        raw = open(os.path.join(src_dir, ROOT, 'Data', name), encoding='utf-8').read()
        obj = json.loads(raw)
        assert dump(obj) == raw, f'{name}: no byte-exact round trip'
        base[pn] = hashlib.md5(raw.encode('utf-8')).hexdigest()
        return pn, obj

    def write(pn, obj, dump):
        dst = os.path.join(stage, pn)
        open(dst, 'w', encoding='utf-8').write(dump(obj))
        entries.append((pn, u3guid[pn], dst, None))

    D_COMPACT = lambda o: json.dumps(o, separators=(',', ':'))
    D_IND1 = lambda o: json.dumps(o, indent=1)

    # ---- materials
    pn_m, M = data_file('Forest_Materials.json', u6stage, D_IND1)
    names = {m['name'] for m in M['materials']}
    for s in NEW_MATS:
        assert s['name'] not in names, s['name']
    used = sorted({m for r in rep.values() for m in r['materials']})
    missing = [m for m in used if m not in names and m not in {s['name'] for s in NEW_MATS}]
    assert not missing, f'materials not defined: {missing}'
    M['materials'].extend(NEW_MATS)
    changes.append(f'Forest_Materials.json: {len(NEW_MATS)} new materials at the end: ' + ', '.join(s['name'] for s in NEW_MATS) +
                   ' (the cut-outs one-sided: doubleSided false)')
    n1 = 0
    for m in M['materials']:
        if m['name'] in ONE_SIDED:
            assert m['type'] == 'cutout' and m['doubleSided'] is True, m['name']
            m['doubleSided'] = False
            n1 += 1
    assert n1 == len(ONE_SIDED), n1
    changes.append('Forest_Materials.json: doubleSided true -> false (in place): ' + ', '.join(ONE_SIDED) + ' - their models '
                   'carry the netting and the wire as two faces back to back (the base and far ones in one plane, the kpp, '
                   'yard and road ones 1.2 mm apart); drawn two-sided, both faces showed from either side and fought for '
                   'the depth (the shimmer); one-sided, each face shows from its own side')
    write(pn_m, M, D_IND1)

    # ---- layout
    pn_l, L = data_file('Forest_Layout.json', u6stage, D_COMPACT)
    fence = [r for r in L['rocks'] if r['m'] == 'FenceChain']
    assert len(fence) == 213, len(fence)
    L['rocks'] = [r for r in L['rocks'] if r['m'] != 'FenceChain']
    changes.append(f'Forest_Layout.json rocks: - {len(fence)} FenceChain (Update 3\'s chain-link fence of the base: the PO-2 '
                   f'concrete fence stands on its lines now)')
    # the trees in the way: by index, each checked against its model and place
    rem = sorted(U7['removed_trees'], key=lambda t: -t['index'])
    for t in rem:
        cur = L['trees'][t['index']]
        assert cur['m'] == t['m'] and cur['p'] == t['p'], (t, cur)
    for t in rem:
        del L['trees'][t['index']]
    why = {}
    for t in U7['removed_trees']:
        k = t['why'].split(' ')[0]
        why[k] = why.get(k, 0) + 1
    changes.append(f'Forest_Layout.json trees: - {len(rem)} ({", ".join(f"{k} {v}" for k, v in sorted(why.items()))}): '
                   f'the strips cleared along the tank-trap lines (trunks within 1.3 m of a line, undergrowth within 1 m), '
                   f'the footprints of the wings, the blocks and the perimeter; listed in u7.removed')
    first = len(L['rocks'])
    recs = [dict(m=r['m'], p=r['p'], q=r['q']) for r in U7['records']]
    for r in recs:
        assert set(r) == {'m', 'p', 'q'} and len(r['p']) == 3 and len(r['q']) == 4
        assert r['m'] in rep and r['m'] not in UNPLACED, r['m']
    L['rocks'].extend(recs)
    from collections import Counter
    cnt = Counter(r['m'] for r in recs)
    changes.append(f'Forest_Layout.json u7.keepClear: {len(U7["keep_clear"])} strips (segment a-b in plan, distance r) the '
                   f'Terrain bake keeps its own planting off (old yard regrowth, saplings, boulders, clutter, ground cover): '
                   f'one per U7 piece, its footprint\'s long axis and half depth + 1 m')
    changes.append(f'Forest_Layout.json rocks: + {len(recs)} U7 placements at the end (indices {first}..{first + len(recs) - 1}) '
                   f'in the frame of the game as it is now (after ForestYardPlan and ForestRelocation): ' +
                   ', '.join(f'{m} {n}' for m, n in sorted(cnt.items())))
    groups = Counter(r['group'] for r in U7['records'])
    controls = control_points(U7, first)
    L['u7'] = {'update': 7,
               'note': 'Forest Update 7: the base behind a PO-2 concrete fence (Update 3\'s chain-link out), the checkpoint '
                       'closed off (PO-2 wings, road blocks, a chicane) and the funnel of tank traps from its wings to the base\'s '
                       'corners - a car reaches the base only through the barrier and the gate; the chain-link and wire '
                       'textures redone (no shimmer), their materials one-sided; see FOREST_U7_UNITY.md',
               'replaced': [], 'added': sorted(rep), 'unplaced': list(UNPLACED),
               'frame': 'game: the U7 records stand where the game shows things now - after ForestYardPlan (the yard drawn '
                        'in x0.7071 about (340, -360) within 135 m) and ForestRelocation (the checkpoint 274 m out). The builder '
                        'places them as they are: no Map(), no relocation; see u7.controls',
               'records': {'list': 'rocks', 'first': first, 'count': len(recs), 'groups': dict(groups)},
               'removed': [{'list': 'rocks', 'm': 'FenceChain', 'p': r['p']} for r in fence] +
                          [{'list': 'trees', 'm': t['m'], 'p': t['p']} for t in sorted(U7['removed_trees'], key=lambda t: t['index'])],
               'controls': controls,
               'keepClear': U7['keep_clear'],
               'changes': changes[:]}
    write(pn_l, L, D_COMPACT)
    # the check: the layout's own lists must not hold nested arrays beyond Update 6's (JsonUtility)
    for r in L['rocks'][first:]:
        assert not any(isinstance(v, list) and any(isinstance(x, list) for x in v) for v in r.values())

    # ---- README
    readme_raw = open(os.path.join(u6stage, ROOT, 'README.md'), encoding='utf-8').read()
    base[f'{ROOT}/README.md'] = hashlib.md5(readme_raw.encode('utf-8')).hexdigest()
    tris = {n: rep[n]['tris'] for n in rep}

    def pl(k, one, few, many):
        """'252 предмета': a number with the Russian noun form it takes"""
        w = one if k % 10 == 1 and k % 100 != 11 else (few if k % 10 in (2, 3, 4) and not 12 <= k % 100 <= 14 else many)
        return f'{k} {w}'

    trunks = sum(1 for t in rem if t['m'].split('_')[0] in ('Spruce', 'SpruceHC', 'Fir', 'Birch', 'Dead', 'Bush'))
    lines_ = U7['lines']
    max_gap = max(max(v['max_gap'], *v['end_gaps']) for v in lines_.values())
    vals = dict(ntex=len(NEW_TEX), nmat=len(NEW_MATS), t_po2=tris['ConcreteFence'],
                w_perim=pl(groups['perimeter'], 'предмет', 'предмета', 'предметов'),
                w_kpp=pl(groups['kpp'], 'предмет', 'предмета', 'предметов'),
                w_funnel=pl(groups['funnel'], 'предмет', 'предмета', 'предметов'),
                w_fence=pl(len(fence), 'секция', 'секции', 'секций'),
                w_teeth=pl(cnt['TankTooth'] + cnt['TankTooth_b'], 'надолб', 'надолба', 'надолбов'),
                w_ab=pl(cnt['Abatis'] + cnt['Abatis_b'], 'завал', 'завала', 'завалов'),
                w_trunks=pl(trunks, 'дерево или куст', 'дерева и куста', 'деревьев и кустов'),
                w_grass=pl(len(rem) - trunks, 'пучок травы или папоротника', 'пучка травы и папоротника',
                           'пучков травы и папоротника'),
                w_rep=pl(len(REPL_TEX), 'текстура', 'текстуры', 'текстур'),
                max_gap=f'{max_gap:.2f}'.replace('.', ','),
                len_ne=f"{lines_['teeth_post_NE']['length']:.0f}", len_nw=f"{lines_['teeth_rest_NW']['length']:.0f}")
    section = open(os.path.join(HERE, 'u7_readme_section.md'), encoding='utf-8').read().format(**vals)
    readme = readme_raw.rstrip('\n') + '\n\n' + section.rstrip('\n') + '\n'
    open(os.path.join(out_dir, 'README_u7_section.md'), 'w', encoding='utf-8').write(section)
    open(os.path.join(stage, ROOT, 'README.md'), 'w', encoding='utf-8').write(readme)
    entries.append((f'{ROOT}/README.md', u3guid[f'{ROOT}/README.md'], os.path.join(stage, ROOT, 'README.md'), None))

    # ---- unitypackage
    guids = [g for _, g, _, _ in entries]
    assert len(set(guids)) == len(guids), 'duplicate GUID'
    new_guids = {guid_of(p) for p, g, s, _ in entries if s is not None and g == guid_of(p)}
    assert not (new_guids & set(u3guid.values())), 'a new GUID collides with Update 3'
    for u in (4, 5, 6):                                  # nor with the GUIDs Updates 4-6 made
        mf = os.path.join(HERE, f'out/forest_update{u}/Forest_Update{u}_manifest.json')
        old = {f['guid'] for f in json.load(open(mf))['files']}
        clash = new_guids & old
        assert not clash, (u, clash)
    pkg = os.path.join(out_dir, 'Forest_Update7.unitypackage')
    mtime = int(time.time())

    def add(t, name, data):
        ti = tarfile.TarInfo(name)
        ti.size = len(data)
        ti.mtime = mtime
        ti.mode = 0o644
        t.addfile(ti, io.BytesIO(data))

    with tarfile.open(pkg, 'w:gz', format=tarfile.GNU_FORMAT) as t:
        for pn, g, src, meta in entries:
            if src is not None:
                add(t, f'{g}/asset', open(src, 'rb').read())
            add(t, f'{g}/asset.meta', (meta or f'fileFormatVersion: 2\nguid: {g}\n').encode('utf-8'))
            add(t, f'{g}/pathname', pn.encode('utf-8'))
    manifest = {'package': os.path.basename(pkg), 'bytes': os.path.getsize(pkg), 'md5': md5(pkg), 'entries': len(entries),
                'over': 'Forest_Update6', 'guid_source': src_of, 'replaced_textures': {k: v[0] for k, v in REPL_TEX.items()},
                'base_md5': base,
                'files': [{'path': p, 'guid': g, 'bytes': os.path.getsize(s) if s else None, 'md5': md5(s) if s else None}
                          for p, g, s, _ in entries],
                'records': L['u7']['records'], 'controls': controls, 'changes': changes}
    json.dump(manifest, open(os.path.join(out_dir, 'Forest_Update7_manifest.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'[u7] {pkg}: {len(entries)} entries, {os.path.getsize(pkg) / 1e6:.2f} MB')
    for c in changes:
        print('   ', c[:300])


def control_points(U7, first):
    """pieces whose places the Unity side checks after Rebuild (they must stand at p within 1 cm, yaw within 0.1 deg):
    the four corners' sockets, the run ends at the gate, the wicket, the wings' roots, two teeth by the corners (inside the
    yard plan's radius), one tooth far out, the HALT board"""
    recs = U7['records']
    out = []

    def near(m, pt, group=None):
        best, bi = 1e9, None
        for i, r in enumerate(recs):
            if r['m'] != m or (group and r['group'] != group):
                continue
            d = math.hypot(r['p'][0] - pt[0], r['p'][2] - pt[1])
            if d < best:
                best, bi = d, i
        return bi

    picks = []
    for k in ('NW', 'NE', 'SE', 'SW'):
        picks.append((f'socket at the {k} corner', near('ConcreteFence_Socket', U7['corners'][k], 'perimeter')))
    picks.append(('the panel west of the gate (lowered: the leaf passes over its socket)',
                  near('ConcreteFence', U7['gate']['west_end'], 'perimeter')))
    picks.append(('the run end east of the gate', near('ConcreteFence', U7['gate']['east_end'], 'perimeter')))
    picks.append(('the wicket by the hatch', near('ConcreteFence_Wicket', U7['wicket'])))
    def near_any(models, pt, group):
        best, bi = 1e9, None
        for i, r in enumerate(recs):
            if r['m'] in models and r['group'] == group:
                d = math.hypot(r['p'][0] - pt[0], r['p'][2] - pt[1])
                if d < best:
                    best, bi = d, i
        return bi

    wing = ('ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Sign', 'ConcreteFence_Socket')
    picks.append(('the wing root at the barrier post', near_any(wing, U7['barrier']['post'], 'kpp')))
    picks.append(('the wing root at the boom rest', near_any(wing, U7['barrier']['rest'], 'kpp')))
    picks.append(('the tooth by the NW corner', near('TankTooth', U7['corners']['NW'], 'funnel')))
    picks.append(('the tooth by the NE corner', near('TankTooth', U7['corners']['NE'], 'funnel')))
    mid = U7['lines']['teeth_post_NE']
    A, B = mid['A'], mid['B']
    picks.append(('a tooth halfway along the NE line', near('TankTooth', ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2), 'funnel')))
    picks.append(('the HALT board', next(i for i, r in enumerate(recs) if r['m'] == 'Sign_Halt')))
    for what, i in picks:
        r = recs[i]
        out.append({'what': what, 'index': first + i, 'm': r['m'], 'p': r['p'], 'q': r['q']})
    return out


if __name__ == '__main__':
    main(*sys.argv[1:5])
