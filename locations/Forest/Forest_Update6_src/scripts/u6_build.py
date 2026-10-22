"""Forest Update 6: the package in the location generator's format, over Update 5 (as Update 5 over 4, 4 over 3).

  Models/   86 FBX from u6_export.py: GenContainer and the 83 items Item_* with Update 3's names and GUIDs; new:
            Item_RadioSet (the control room's radio set, scare X08) and Apparition (the figure of X02 / X03, skinned,
            four clips)
  Textures/ the PSX atlases renamed to the core's convention (T_*_A_px albedo, T_*_E_px emission: Point filter, no
            compression, set by the core on import)
  Data/     Forest_Layout.json, Forest_Materials.json = Update 5's files; Forest_Opening.json, Forest_Items.json,
            Forest_Dressing.json = Update 3's (Updates 4 and 5 did not ship them) - each with the changes listed in
            CHANGES (byte-exact elsewhere: same separators, same order); the block u6 in the layout lists them
  README.md Update 5's README + the section "Обновление 6"

python3 u6_build.py <fbx_dir> <u5_dir> <u3_dir> <u3raw_dir> <out_dir>
  u5_dir: out/forest_update5 (its stage/ holds Update 5's Data and README), u3_dir: extracted Update 3, u3raw_dir: its
  unitypackage entries (GUIDs and .meta)"""
import os, sys, json, shutil, hashlib, tarfile, io, time, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u4_build as U4
import u6_radio as RADIO

PKG = os.path.join(HERE, 'out')
ROOT = 'Assets/Locations/Forest'
TEX = [('tex/gcf/T_GCont_Cont_BaseColor.png', 'T_GCont_Cont_A_px.png'),
       ('tex/gcf/T_GCont_Genset_BaseColor.png', 'T_GCont_Genset_A_px.png'),
       ('tex/gcf/T_GCont_Props_BaseColor.png', 'T_GCont_Props_A_px.png'),
       ('tex/gcf/T_GCont_Panel_BaseColor.png', 'T_GCont_Panel_A_px.png'),
       ('tex/items/T_Item_Props_BaseColor.png', 'T_Item_Props_A_px.png'),
       ('tex/items/T_Item_Panel_BaseColor.png', 'T_Item_Panel_A_px.png'),
       ('tex/items/T_Item_Panel_Emission.png', 'T_Item_Panel_E_px.png'),
       ('tex/fig/T_Fig_Figure_BaseColor.png', 'T_Fig_Figure_A_px.png')]
NEW_MATS = [
    U4.atlas('M_GCont_Cont', 'T_GCont_Cont_A_px.png'), U4.atlas('M_GCont_Genset', 'T_GCont_Genset_A_px.png'),
    U4.atlas('M_GCont_Props', 'T_GCont_Props_A_px.png'), U4.atlas('M_GCont_Panel', 'T_GCont_Panel_A_px.png'),
    # the generator's gauge needles and the diesel in the day tank's sight tube: plain colours
    U4.spec('M_GCont_Needle', '', color=(0.95, 0.30, 0.06)),
    U4.spec('M_GCont_Diesel', '', color=(0.62, 0.40, 0.06), smooth=0.8, nospec=False),
    U4.atlas('M_Item_Props', 'T_Item_Props_A_px.png'), U4.atlas('M_Item_Panel', 'T_Item_Panel_A_px.png'),
    # the radio set's channel window: off (dark glass, the unlit segments) / on (X08: the channel lit, orange)
    U4.spec('M_RadioDisplay', 'T_Item_Panel_A_px.png', smooth=0.6, nospec=False),
    U4.spec('M_RadioDisplayOn', 'T_Item_Panel_A_px.png', emap='T_Item_Panel_E_px.png', emission=(1, 1, 1), ei=2.0, smooth=0.6,
            nospec=False),
    U4.atlas('M_Apparition', 'T_Fig_Figure_A_px.png'),
]
NEW_MODELS = ('Item_RadioSet', 'Apparition')


def guid_of(path):
    return hashlib.md5(('snow/Forest/Update6/' + path).encode()).hexdigest()


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def r4(v):
    return [round(float(x), 4) + 0.0 for x in v]


def main(fbx_dir, u5_dir, u3_dir, u3raw_dir, out_dir):
    rep = json.load(open(os.path.join(fbx_dir, 'u6_export_report.json')))
    gcf = json.load(open(os.path.join(PKG, 'gcf.json')))['data']
    items = json.load(open(os.path.join(PKG, 'items.json')))
    fig = json.load(open(os.path.join(PKG, 'fig.json')))
    u5stage = os.path.join(u5_dir, 'stage')
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
    entries, changes = [], []
    base = {}                                   # the files the package writes over: what the project should have before

    def folder(path):
        g = u3guid[path]
        entries.append((path, g, None, open(os.path.join(u3raw_dir, g, 'asset.meta'), encoding='utf-8').read()))

    for f in ('Assets/Locations', ROOT, f'{ROOT}/Models', f'{ROOT}/Textures', f'{ROOT}/Data'):
        folder(f)

    # ---- models: Update 3's GUIDs; two new ones
    src_of = {}
    for name in sorted(rep):
        pn = f'{ROOT}/Models/{name}.fbx'
        if name in NEW_MODELS:
            assert pn not in u3guid, pn
            g, src_of[name] = guid_of(pn), 'new'
        else:
            g, src_of[name] = u3guid[pn], 'Update 3'
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(fbx_dir, rep[name]['file']), dst)
        entries.append((pn, g, dst, None))
    assert sum(1 for v in src_of.values() if v == 'Update 3') == 84, src_of

    # ---- textures (new names: no clash with Update 3's or the project's)
    for src, dn in TEX:
        pn = f'{ROOT}/Textures/{dn}'
        assert pn not in u3guid, pn
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(HERE, src), dst)
        entries.append((pn, guid_of(pn), dst, None))

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
    D_IND1U = lambda o: json.dumps(o, indent=1, ensure_ascii=False)

    # ---- materials: Update 5's file + the new ones at the end
    pn, M = data_file('Forest_Materials.json', u5stage, D_IND1)
    names = {m['name'] for m in M['materials']}
    for s in NEW_MATS:
        assert s['name'] not in names, s['name']
    used = sorted({m for r in rep.values() for m in r['materials']})
    missing = [m for m in used if m not in names and m not in {s['name'] for s in NEW_MATS}]
    assert not missing, f'materials not defined: {missing}'
    M['materials'].extend(NEW_MATS)
    changes.append(f'Forest_Materials.json: {len(NEW_MATS)} new materials at the end: ' + ', '.join(s['name'] for s in NEW_MATS))
    write(pn, M, D_IND1)

    # ---- layout: Update 5's + the GenContainer's lights, halos, interactables, viewpoint; Apparition without collider
    pn_l, L = data_file('Forest_Layout.json', u5stage, D_COMPACT)
    pl = next(e for e in L['prefabLights'] if e['model'] == 'GenContainer')
    changes.append(f'Forest_Layout.json prefabLights GenContainer: {len(pl["lights"])} lights -> {len(gcf["prefabLights"]["lights"])} '
                   f'(3 bulkhead lamps inside, the barn lamp over the cargo doors; tag power, off at the start, room Exterior)')
    pl['lights'] = gcf['prefabLights']['lights']
    pg = next(e for e in L['prefabGlows'] if e['model'] == 'GenContainer')
    changes.append(f'Forest_Layout.json prefabGlows GenContainer: {len(pg["glows"])} halos -> {len(gcf["prefabGlows"]["glows"])} '
                   f'(M_Glow_Bulb at each lamp)')
    pg['glows'] = gcf['prefabGlows']['glows']
    new_ix = {i['new']['child']: i['new'] for i in gcf['interactables']}
    n_ix = 0
    for it in L['interactables']:
        if it['model'] != 'GenContainer':
            continue
        nw = new_ix[it['child']]
        diff = {k: (it[k], nw[k]) for k in ('axis', 'min', 'max') if it[k] != nw[k]}
        if diff:
            changes.append(f'Forest_Layout.json interactables GenContainer/{it["child"]}: ' +
                           ', '.join(f'{k} {a} -> {b}' for k, (a, b) in diff.items()))
            it.update({k: nw[k] for k in diff})
        n_ix += 1
    assert n_ix == len(new_ix) == 9, n_ix
    vp = next(v for v in L['viewpoints'] if v['name'] == 'GenContainer')
    nv = gcf['viewpoint']
    changes.append(f'Forest_Layout.json viewpoints GenContainer: p {vp["p"]} -> {nv["p"]}, target {vp["target"]} -> {nv["target"]}, '
                   f'fov {vp["fov"]} -> {nv["fov"]} (the old camera stands inside the new generator set)')
    vp.update(p=nv['p'], target=nv['target'], fov=nv['fov'])
    L['noColliderPrefixes'].append('Apparition')
    changes.append('Forest_Layout.json noColliderPrefixes: + Apparition (the figure walks through things, no import collider)')

    # ---- opening: the day tank's fill point; the scares X02 / X03 / X08 get their models
    pn_o, O = data_file('Forest_Opening.json', u3_dir, D_IND1U)
    fn = next(e for e in O['interactables'] if e['id'] == 'Gen_FillNeck')
    f6 = gcf['fill']
    changes.append(f'Forest_Opening.json interactables Gen_FillNeck: neck {fn["neck"]} -> {f6["neck"]}, stand {fn["stand"]} -> '
                   f'{f6["stand"]}, label "{fn["label"]}" -> "{f6["label"]}", capacityL {fn["capacityL"]} -> {f6["capacityL"]} '
                   f'(the fill box on the far end; the new container\'s day tank holds 100 l; startL, burnLph unchanged)')
    fn.update(neck=f6['neck'], stand=f6['stand'], label=f6['label'], capacityL=f6['capacityL'])
    rp = RADIO.placement(items['items']['Item_RadioSet']['bounds'], next(e for e in L['prefabs'] if e['m'] == 'BaseMain'))
    sc = {s['id']: s for s in O['scares']}
    sc['X02_Crossing']['figure'] = dict(model='Apparition', clip='Walk', clipSpeedMps=fig['walk_speed'],
                                        note='the Walk clip at speed 1 keeps the feet still at this speed; faster: Animator speed = v / '
                                             'clipSpeedMps (the 2 s crossing) - see FOREST_U6_UNITY.md, appendix V (Приложение В)')
    sc['X03_BackSeat']['figure'] = dict(model='Apparition', clips=['Sit', 'SitLook'], seat='van3 Sit_L1 .. Sit_L4 (the left bench)',
                                        note='the object origin on the seat point, facing the bench\'s front (the aisle); Sit, then '
                                             'SitLook (0.6 s): the head turns to the cab - see FOREST_U6_UNITY.md, appendix V (Приложение В)')
    sc['X08_Radio']['radio'] = dict(prop='Leitstand_RadioSet_1', model='Item_RadioSet', displayOff='M_RadioDisplay',
                                    displayOn='M_RadioDisplayOn', speaker=items_speaker())
    # the procedure note lay on Update 3's panel top (container y 1.890); the new genset panel's top is a flat
    # 0.17 x 0.56 m at y 1.750 (x -0.03..0.14, z -0.06..0.50 in the prefab frame): the form on it, long side along z
    gcp = next(e for e in L['prefabs'] if e['m'] == 'GenContainer')
    note = next(e for e in O['items'] if e['id'] == 'Note_GenProcedure')
    old_p, old_q = note['p'][:], note['q'][:]
    note['p'], note['q'] = NOTE.world(gcp['p'], gcp['q'])
    changes.append(f'Forest_Opening.json items Note_GenProcedure: p {old_p} -> {note["p"]}, q {old_q} -> {note["q"]} (on the top '
                   f'of the new generator panel: container-local {NOTE.local} at yaw {NOTE.yaw} deg; Update 3\'s panel top was '
                   f'0.14 m higher, the form would hang in the air)')
    changes.append('Forest_Opening.json scares: X02_Crossing.figure, X03_BackSeat.figure (Apparition, clips), X08_Radio.radio '
                   '(the prop, its display materials, the speaker point) - data for the scares when they are built (DEFERRED)')

    # ---- items: the radio set; the triangle counts of the new meshes
    pn_i, I = data_file('Forest_Items.json', u3_dir, D_IND1U)
    ntri = 0
    for e in I['items']:
        t = rep[e['model']]['tris']
        if e.get('tris') != t:
            e['tris'] = t
            ntri += 1
    changes.append(f'Forest_Items.json items: tris of {ntri} models (the new meshes; colliders, origins, masses unchanged)')
    radio = dict(model='Item_RadioSet', label='Рация', itemKey='Item_RadioSet', massKg=6.0, collider=RADIO.collider(),
                 kind='prop', clean=False, tris=rep['Item_RadioSet']['tris'],
                 display=dict(off='M_RadioDisplay', on='M_RadioDisplayOn'), speaker=items_speaker())
    I['items'].append(radio)
    changes.append('Forest_Items.json items: + Item_RadioSet (label "Рация", 6 kg, the case as the collider, display off / on, '
                   'speaker)')

    # ---- dressing: the radio set on the west console's shelf in the Leitstand
    pn_d, Dr = data_file('Forest_Dressing.json', u3_dir, D_IND1U)
    prop = dict(id='Leitstand_RadioSet_1', model='Item_RadioSet', room='Leitstand', p=rp['unity']['p'], q=rp['unity']['q'],
                kind='prop', clean=False, massKg=6.0, collider=RADIO.collider())
    Dr['props'].append(prop)
    changes.append(f'Forest_Dressing.json props: + Leitstand_RadioSet_1 (Item_RadioSet) at p {prop["p"]} q {prop["q"]} - the west '
                   f'console\'s writing shelf, its west end, the front to the operator (at the end of the list: the other '
                   f'props keep their indices)')

    # ---- notes: the generator procedure describes the new set (day tank 100 l, DIESEL, the key)
    pn_n, N = data_file('Forest_Notes.json', u3_dir, D_IND1U)
    gp = next(e for e in N['notes'] if e['id'] == 'gen_procedure')
    for lang in ('de', 'ru'):
        for a, b in NOTE_TEXT[lang]:
            assert gp[lang].count(a) == 1, (lang, a)
            gp[lang] = gp[lang].replace(a, b)
    changes.append('Forest_Notes.json gen_procedure: the new generator set - the fill box sign DIESEL (was HEIZÖL), the start '
                   'key on the generator panel (was a START lever), day tank 100 l for about 28 hours (was 60 l / 17 h; '
                   'burnLph 3.5 unchanged)')

    L['u6'] = {'update': 6, 'note': 'Forest Update 6: GenContainer (the twin generator container) and the 83 items rebuilt in the '
                                    'generator shed\'s look (same names and GUIDs; the items keep origins and sizes); new: '
                                    'Item_RadioSet (the control room\'s radio set, X08) and Apparition (the figure of X02 / X03); '
                                    'data changes in "changes"; see FOREST_U6_UNITY.md',
               'replaced': sorted(n for n in rep if n not in NEW_MODELS), 'added': list(NEW_MODELS), 'changes': changes[:]}
    write(pn_l, L, D_COMPACT)
    write(pn_o, O, D_IND1U)
    write(pn_i, I, D_IND1U)
    write(pn_d, Dr, D_IND1U)
    write(pn_n, N, D_IND1U)

    # ---- README: Update 5's + the section "Обновление 6"
    u3items = json.load(open(os.path.join(HERE, 'items_u3.json')))
    k = lambda v: f'{v / 1000:.1f}'.replace('.', ',')
    readme_raw = open(os.path.join(u5stage, ROOT, 'README.md'), encoding='utf-8').read()
    base[f'{ROOT}/README.md'] = hashlib.md5(readme_raw.encode('utf-8')).hexdigest()
    vals = dict(ntex=len(TEX), nmat=len(NEW_MATS), tris_gc=k(rep['GenContainer']['tris']), tris_gc_u3=k(GC_U3_TRIS),
                tris_items=k(sum(rep[n]['tris'] for n in u3items)), tris_items_u3=k(sum(v['tris'] for v in u3items.values())),
                tris_radio=rep['Item_RadioSet']['tris'], tris_fig=rep['Apparition']['tris'],
                walk=f"{fig['walk_speed']:.2f}".replace('.', ','), nbones=len(rep['Apparition']['bones']),
                tris_radio_w=tri_word(rep['Item_RadioSet']['tris']), tris_fig_w=tri_word(rep['Apparition']['tris']))
    section = open(os.path.join(HERE, 'u6_readme_section.md'), encoding='utf-8').read().format(**vals)
    readme = readme_raw.rstrip('\n') + '\n\n' + section.rstrip('\n') + '\n'
    open(os.path.join(out_dir, 'README_u6_section.md'), 'w', encoding='utf-8').write(section)
    open(os.path.join(stage, ROOT, 'README.md'), 'w', encoding='utf-8').write(readme)
    entries.append((f'{ROOT}/README.md', u3guid[f'{ROOT}/README.md'], os.path.join(stage, ROOT, 'README.md'), None))

    # ---- unitypackage (gzip tar: <guid>/asset, <guid>/asset.meta, <guid>/pathname)
    guids = [g for _, g, _, _ in entries]
    assert len(set(guids)) == len(guids), 'duplicate GUID'
    new_guids = {g for p, g, _, _ in entries if src_of.get(os.path.splitext(os.path.basename(p))[0]) == 'new' or '/Textures/' in p}
    assert not (new_guids & set(u3guid.values())), 'a new GUID collides with Update 3'
    pkg = os.path.join(out_dir, 'Forest_Update6.unitypackage')
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
                'over': 'Forest_Update5', 'guid_source': src_of,
                'base_md5': base,
                'files': [{'path': p, 'guid': g, 'bytes': os.path.getsize(s) if s else None, 'md5': md5(s) if s else None}
                          for p, g, s, _ in entries],
                'radio': rp, 'changes': changes}
    json.dump(manifest, open(os.path.join(out_dir, 'Forest_Update6_manifest.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'[u6] {pkg}: {len(entries)} entries, {os.path.getsize(pkg) / 1e6:.2f} MB')
    for c in changes:
        print('   ', c)


GC_U3_TRIS = 19994          # Update 3's GenContainer.fbx (10 objects), counted on import


class NOTE:
    """Note_GenProcedure on the new genset panel top: container-local (Unity, prefab frame) point and yaw"""
    local = (0.055, 1.752, 0.15)            # the form's origin = its underside (collider centre y 0.003, size 0.006)
    yaw = 4.0                               # degrees about +Y, the form's long side (0.21 m, its z) along the panel

    @classmethod
    def world(cls, p0, q0):
        yaw0 = 2.0 * math.degrees(math.atan2(q0[1], q0[3]))          # the container turns about Y only
        a = math.radians(yaw0)
        lx, ly, lz = cls.local
        p = [p0[0] + lx * math.cos(a) + lz * math.sin(a), p0[1] + ly, p0[2] - lx * math.sin(a) + lz * math.cos(a)]
        h = math.radians(yaw0 + cls.yaw) / 2.0
        return r4(p), [0.0, round(math.sin(h), 6) + 0.0, 0.0, round(math.cos(h), 6) + 0.0]


NOTE_TEXT = {
    'de': [('Einfüllkasten außen am Container (HEIZÖL).', 'Einfüllkasten außen am Container (DIESEL).'),
           ('dann Hebel START am Generatorpult.', 'dann Schlüssel am Generatorpult auf START.'),
           ('Tagestank 60 l reicht für ca. 17 Stunden.', 'Tagestank 100 l reicht für ca. 28 Stunden.')],
    'ru': [('заливной лючок снаружи контейнера (HEIZÖL).', 'заливной лючок снаружи контейнера (DIESEL).'),
           ('затем рычаг START на пульте генератора.', 'затем ключ на пульте генератора — в положение START.'),
           ('60 л хватает примерно на 17 часов.', '100 л хватает примерно на 28 часов.')],
}


def tri_word(n):
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return 'треугольник'
    if n % 10 in (2, 3, 4) and not 12 <= n % 100 <= 14:
        return 'треугольника'
    return 'треугольников'


def items_speaker():
    """the radio set's loudspeaker (the grille on its top, items_kit): Unity model space"""
    return [0.0, 0.12, -0.06]


if __name__ == '__main__':
    main(*sys.argv[1:6])
