"""Forest Update 4: the package in the location generator's format (as Forest_Update1..3), over Update 3.

  Models/   29 FBX from u4_export.py (same names and GUIDs as the models they replace)
  Textures/ the batches' PSX atlases renamed to the core's convention (T_*_A_px albedo, T_*_E_px emission: Point filter,
            no compression, set by SkyIslandImport on import)
  Data/     Forest_Layout.json and Forest_Materials.json = Update 3's files with the changes listed in CHANGES (byte-exact
            elsewhere: same separators, same order)
  README.md Update 3's README + the section "Обновление 4"

python3 u4_build.py <fbx_dir> <spots_dir> <u3_dir> <u3raw_dir> <out_dir>
  u3_dir: extracted Update 3 (Assets/Locations/Forest/...), u3raw_dir: its unitypackage entries (GUIDs)
"""
import os, sys, json, shutil, hashlib, tarfile, io, time, copy

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, 'out')
ROOT = 'Assets/Locations/Forest'

# ------------------------------------------------------------------ textures: (batch tex file, Update 4 name)
TEX = [
    ('forest_hut/tex/T_Hut_Hut_BaseColor.png', 'T_Hut_Hut_A_px.png'),
    ('forest_hut/tex/T_Hut_HutProps_BaseColor.png', 'T_Hut_HutProps_A_px.png'),
    ('forest_hut/tex/T_Hut_Panel_BaseColor.png', 'T_Hut_Panel_A_px.png'),
    ('forest_hut/tex/T_Hut_Panel_Emission.png', 'T_Hut_Panel_E_px.png'),
    ('forest_kpp/tex/T_Kpp_Kpp_BaseColor.png', 'T_Kpp_Kpp_A_px.png'),
    ('forest_kpp/tex/T_Kpp_KppYard_BaseColor.png', 'T_Kpp_KppYard_A_px.png'),
    ('forest_kpp/tex/T_Kpp_KppProps_BaseColor.png', 'T_Kpp_KppProps_A_px.png'),
    ('forest_kpp/tex/T_Kpp_Panel_BaseColor.png', 'T_Kpp_Panel_A_px.png'),
    ('forest_kpp/tex/T_Kpp_Panel_Emission.png', 'T_Kpp_Panel_E_px.png'),
    ('forest_kpp/tex/T_Kpp_ChainLink.png', 'T_Kpp_ChainLink_A_px.png'),
    ('forest_kpp/tex/T_Kpp_Barbed.png', 'T_Kpp_Barbed_A_px.png'),
    ('forest_yard/tex/T_Yard_Tanks_BaseColor.png', 'T_Yard_Tanks_A_px.png'),
    ('forest_yard/tex/T_Yard_Trafo_BaseColor.png', 'T_Yard_Trafo_A_px.png'),
    ('forest_yard/tex/T_Yard_YardProps_BaseColor.png', 'T_Yard_YardProps_A_px.png'),
    ('forest_yard/tex/T_Yard_Panel_BaseColor.png', 'T_Yard_Panel_A_px.png'),
    ('forest_yard/tex/T_Yard_ChainLink.png', 'T_Yard_ChainLink_A_px.png'),
    ('forest_yard/tex/T_Yard_Barbed.png', 'T_Yard_Barbed_A_px.png'),
    ('forest_main/tex/T_Main_Ext_BaseColor.png', 'T_Main_Ext_A_px.png'),
    ('forest_main/tex/T_Main_Roof_BaseColor.png', 'T_Main_Roof_A_px.png'),
    ('forest_main/tex/T_Main_Parts_BaseColor.png', 'T_Main_Parts_A_px.png'),
    ('forest_main/tex/T_Main_Opening_BaseColor.png', 'T_Main_Opening_A_px.png'),
    ('forest_main/tex/T_Main_Panel_BaseColor.png', 'T_Main_Panel_A_px.png'),
    ('forest_main/tex/T_Main_Panel_Emission.png', 'T_Main_Panel_E_px.png'),
] + [(f'forest_main/tex/T_Main_Rm_{r}_BaseColor.png', f'T_Main_Rm_{r}_A_px.png') for r in (
    'Flur_EG', 'Flur_OG', 'Flur_UG', 'Garage', 'Heizung', 'Kaserne', 'Kueche', 'Lager', 'Leitstand', 'Schaltraum',
    'Serverraum', 'Stationsleiter', 'Treppenhaus', 'Waschraum', 'Windfang')] + [
    ('forest_garage/tex/T_Gar_Bld_BaseColor.png', 'T_Gar_Bld_A_px.png'),
    ('forest_garage/tex/T_Gar_Parts_BaseColor.png', 'T_Gar_Parts_A_px.png'),
    ('forest_garage/tex/T_Gar_Panel_BaseColor.png', 'T_Gar_Panel_A_px.png'),
    ('forest_road/tex/T_Road_Signs_BaseColor.png', 'T_Road_Signs_A_px.png'),
    ('forest_road/tex/T_Road_Gate_BaseColor.png', 'T_Road_Gate_A_px.png'),
    ('forest_road/tex/T_Road_Bridge_BaseColor.png', 'T_Road_Bridge_A_px.png'),
    ('forest_road/tex/T_Road_Deck_BaseColor.png', 'T_Road_Deck_A_px.png'),
    ('forest_road/tex/T_Road_Windfall_BaseColor.png', 'T_Road_Windfall_A_px.png'),
    ('forest_road/tex/T_Road_Panel_BaseColor.png', 'T_Road_Panel_A_px.png'),
    ('forest_road/tex/T_Road_ChainLink.png', 'T_Road_ChainLink_A_px.png'),
    ('forest_road/tex/T_Road_Barbed.png', 'T_Road_Barbed_A_px.png'),
]


# ------------------------------------------------------------------ materials
def spec(name, albedo, typ='lit', emap='', emission=(0, 0, 0), ei=0.0, smooth=0.0, cutoff=0.5, two=False, inst=False,
         nospec=True, color=(1, 1, 1)):
    s = {'name': name, 'type': typ, 'albedo': albedo, 'normal': '', 'mask': '', 'emissionMap': emap, 'tiling': [1, 1],
         'color': list(color), 'emission': list(emission), 'emissionIntensity': ei, 'smoothness': smooth, 'metallic': 0.0,
         'cutoff': cutoff, 'normalScale': 1.0, 'doubleSided': two, 'instancing': inst, 'softness': 2.6,
         'detail': {'albedo': '', 'normal': '', 'tiling': [1, 1], 'normalScale': 1.0}}
    if nospec:
        s['noSpecular'] = True
    return s


def atlas(name, tex):
    return spec(name, tex)


def cut(name, tex):
    return spec(name, tex, typ='cutout', cutoff=0.5, two=True, inst=True)


NEW_MATS = [
    atlas('M_Hut_Hut', 'T_Hut_Hut_A_px.png'), atlas('M_Hut_HutProps', 'T_Hut_HutProps_A_px.png'),
    atlas('M_Hut_Panel', 'T_Hut_Panel_A_px.png'),
    spec('M_Hut_LampOil', 'T_Hut_Panel_A_px.png', smooth=0.5, nospec=False),
    atlas('M_Kpp_Kpp', 'T_Kpp_Kpp_A_px.png'), atlas('M_Kpp_KppYard', 'T_Kpp_KppYard_A_px.png'),
    atlas('M_Kpp_KppProps', 'T_Kpp_KppProps_A_px.png'), atlas('M_Kpp_Panel', 'T_Kpp_Panel_A_px.png'),
    cut('M_Kpp_ChainLink', 'T_Kpp_ChainLink_A_px.png'), cut('M_Kpp_Barbed', 'T_Kpp_Barbed_A_px.png'),
    atlas('M_Yard_Tanks', 'T_Yard_Tanks_A_px.png'), atlas('M_Yard_Trafo', 'T_Yard_Trafo_A_px.png'),
    atlas('M_Yard_YardProps', 'T_Yard_YardProps_A_px.png'), atlas('M_Yard_Panel', 'T_Yard_Panel_A_px.png'),
    cut('M_Yard_ChainLink', 'T_Yard_ChainLink_A_px.png'), cut('M_Yard_Barbed', 'T_Yard_Barbed_A_px.png'),
    atlas('M_Main_Ext', 'T_Main_Ext_A_px.png'), atlas('M_Main_Roof', 'T_Main_Roof_A_px.png'),
    atlas('M_Main_Parts', 'T_Main_Parts_A_px.png'), atlas('M_Main_Opening', 'T_Main_Opening_A_px.png'),
    # labels, signs, papers; the emission map holds the exit pictograms and lit lenses: a faint glow at night (0.06)
    spec('M_Main_Panel', 'T_Main_Panel_A_px.png', emap='T_Main_Panel_E_px.png', emission=(1, 1, 1), ei=0.06),
] + [atlas(f'M_Main_Rm_{r}', f'T_Main_Rm_{r}_A_px.png') for r in (
    'Flur_EG', 'Flur_OG', 'Flur_UG', 'Garage', 'Heizung', 'Kaserne', 'Kueche', 'Lager', 'Leitstand', 'Schaltraum',
    'Serverraum', 'Stationsleiter', 'Treppenhaus', 'Waschraum', 'Windfang')] + [
    atlas('M_Gar_Bld', 'T_Gar_Bld_A_px.png'), atlas('M_Gar_Parts', 'T_Gar_Parts_A_px.png'),
    atlas('M_Gar_Panel', 'T_Gar_Panel_A_px.png'),
    atlas('M_Road_Signs', 'T_Road_Signs_A_px.png'), atlas('M_Road_Gate', 'T_Road_Gate_A_px.png'),
    atlas('M_Road_Bridge', 'T_Road_Bridge_A_px.png'), atlas('M_Road_Deck', 'T_Road_Deck_A_px.png'),
    atlas('M_Road_Windfall', 'T_Road_Windfall_A_px.png'),
    # sign faces: the retroreflective glow of Update 3's M_ObsSigns (emission = the albedo at 0.06)
    spec('M_Road_Panel', 'T_Road_Panel_A_px.png', emap='T_Road_Panel_A_px.png', emission=(1, 1, 1), ei=0.06),
    cut('M_Road_ChainLink', 'T_Road_ChainLink_A_px.png'), cut('M_Road_Barbed', 'T_Road_Barbed_A_px.png'),
]

# Update 3 names the game knows (flicker, X01, the power grid) - only these models use them, so their definitions take
# the new lenses' textures; colours, intensities and types stay Update 3's
REDEFINE = {
    'M_Lantern': dict(albedo='T_Hut_Panel_A_px.png', emissionMap='T_Hut_Panel_E_px.png', color=[1, 1, 1]),
    'M_LanternOff': dict(albedo='T_Hut_Panel_A_px.png', color=[1, 1, 1]),
    'M_Lamp_FluorFlicker': dict(albedo='T_Kpp_Panel_A_px.png', emissionMap='T_Kpp_Panel_E_px.png', color=[1, 1, 1]),
}
REDEFINE_USERS = {'M_Lantern': ['TowerHut'], 'M_LanternOff': ['TowerHut'], 'M_Lamp_FluorFlicker': ['Checkpoint']}


# viewpoints that see the rebuilt models (frustum and 220 m fog, no occlusion; interiors of BaseMain) / that do not
CHANGED_VP = ['Start', 'Hut', 'Bridge', 'Windfall', 'Overlook', 'KPP', 'Base', 'Dish1', 'Chapel', 'ControlRoom',
              'Corridor', 'Kitchen', 'SwitchRoom']          # Chapel: Sign_Pump at 133 m, deep in the fog
SAME_VP = ['UnderHand', 'Ribs', 'Woods', 'GenContainer']


def guid_of(path):
    return hashlib.md5(('snow/Forest/Update4/' + path).encode()).hexdigest()


def main(fbx_dir, spots_dir, u3_dir, u3raw_dir, out_dir):
    rep = json.load(open(os.path.join(fbx_dir, 'u4_export_report.json')))
    spots = {}
    for b in ('hut', 'kpp'):
        spots.update(json.load(open(os.path.join(spots_dir, f'spots_{b}.json'))))
    stage = os.path.join(out_dir, 'stage')
    if os.path.exists(stage):
        shutil.rmtree(stage)
    for sub in ('Models', 'Textures', 'Data'):
        os.makedirs(os.path.join(stage, ROOT, sub))
    changes = []

    # ---- GUIDs of Update 3 (and of the project, for models the Update 3 package does not carry)
    u3guid = {}
    for g in os.listdir(u3raw_dir):
        p = os.path.join(u3raw_dir, g, 'pathname')
        if os.path.exists(p):
            u3guid[open(p, encoding='utf-8').read().split('\n')[0]] = g
    project_guid = {f'{ROOT}/Models/EuroPost.fbx': '47ee0862def446e696f77605525628d5',
                    f'{ROOT}/Models/FallenTree.fbx': 'ee4e1164bd4e27d5104894280c7bbfd7',
                    f'{ROOT}/Models/LogCut.fbx': '1a0d28a5db802f234ea2f37cefe53e59'}
    entries = []          # (pathname, guid, source file or None for folders, meta text)

    def folder(path):
        g = u3guid[path]
        meta = open(os.path.join(u3raw_dir, g, 'asset.meta'), encoding='utf-8').read()
        entries.append((path, g, None, meta))

    for f in ('Assets/Locations', ROOT, f'{ROOT}/Models', f'{ROOT}/Textures', f'{ROOT}/Data'):
        folder(f)

    # ---- models
    for name in sorted(rep):
        pn = f'{ROOT}/Models/{name}.fbx'
        g = u3guid.get(pn) or project_guid.get(pn)
        assert g, f'no GUID for {pn}'
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(fbx_dir, name + '.fbx'), dst)
        entries.append((pn, g, dst, None))

    # ---- textures
    for src, dn in TEX:
        pn = f'{ROOT}/Textures/{dn}'
        assert pn not in u3guid, pn
        dst = os.path.join(stage, pn)
        shutil.copyfile(os.path.join(PKG, src), dst)
        entries.append((pn, guid_of(pn), dst, None))

    # ---- materials
    mats_raw = open(os.path.join(u3_dir, ROOT, 'Data/Forest_Materials.json'), encoding='utf-8').read()
    M = json.loads(mats_raw)
    assert json.dumps(M, indent=1) == mats_raw
    names = {m['name']: m for m in M['materials']}
    for s in NEW_MATS:
        assert s['name'] not in names, s['name']
    for n, ch in REDEFINE.items():
        names[n].update(ch)
        changes.append(f'material {n}: ' + ', '.join(f'{k}={v}' for k, v in ch.items()))
    M['materials'].extend(NEW_MATS)
    open(os.path.join(stage, ROOT, 'Data/Forest_Materials.json'), 'w', encoding='utf-8').write(json.dumps(M, indent=1))
    entries.append((f'{ROOT}/Data/Forest_Materials.json', u3guid[f'{ROOT}/Data/Forest_Materials.json'],
                    os.path.join(stage, ROOT, 'Data/Forest_Materials.json'), None))

    # ---- layout
    lay_raw = open(os.path.join(u3_dir, ROOT, 'Data/Forest_Layout.json'), encoding='utf-8').read()
    L = json.loads(lay_raw)
    assert json.dumps(L, separators=(',', ':')) == lay_raw
    U = lambda n: [round(v, 4) for v in spots[n]['unity']]
    light_at = {('TowerHut', 'lantern'): U('LIGHT_Lantern'), ('Checkpoint', 'booth'): U('LIGHT_Fluor'),
                ('Checkpoint', 'power'): U('LIGHT_Bulk_Door')}
    glow_at = {('TowerHut', 'M_Glow_Lantern'): U('Lens_Lantern'), ('Checkpoint', 'M_Glow_FluorFlicker'): U('Lens_Fluor'),
               ('Checkpoint', 'M_Glow_Bulb'): U('Lens_Bulk_Door')}
    for pl in L['prefabLights']:
        for l in pl['lights']:
            k = (pl['model'], l['tag'])
            if k in light_at:
                changes.append(f'prefabLights {pl["model"]} {l["tag"]}: p {l["p"]} -> {light_at[k]}')
                l['p'] = light_at[k]
    for pg in L['prefabGlows']:
        for gd in pg['glows']:
            k = (pg['model'], gd['m'])
            if k in glow_at:
                changes.append(f'prefabGlows {pg["model"]} {gd["m"]}: p {gd["p"]} -> {glow_at[k]}')
                gd['p'] = glow_at[k]
    for it in L['interactables']:
        if it['model'] == 'BaseMain' and it['child'] in ('IX_Drawer_31', 'IX_Drawer_32', 'IX_Drawer_33', 'IX_Drawer_34'):
            changes.append(f'interactables {it["child"]}: max {it["max"]} -> 0.2 (the drawer cabinet stands 0.20 m in front)')
            it['max'] = 0.2
    L['u4'] = {'update': 4, 'note': 'Forest Update 4: 29 models of the prologue route rebuilt in the generator shed\'s look '
                                    '(same names, GUIDs, IX parts, axes, travel and places; the hut door and the KPP booth '
                                    'door, window and drawers pivot where they stand in the new models); see '
                                    'FOREST_U4_UNITY.md',
               'replaced': sorted(rep), 'changes': changes[:]}
    open(os.path.join(stage, ROOT, 'Data/Forest_Layout.json'), 'w', encoding='utf-8').write(
        json.dumps(L, separators=(',', ':')))
    entries.append((f'{ROOT}/Data/Forest_Layout.json', u3guid[f'{ROOT}/Data/Forest_Layout.json'],
                    os.path.join(stage, ROOT, 'Data/Forest_Layout.json'), None))

    # ---- README
    u3tris = json.load(open(os.path.join(spots_dir, 'u3tris.json')))
    k = lambda v: f'{v / 1000:.1f}'.replace('.', ',')
    comparable = [n for n in rep if n in u3tris]
    vals = dict(nmodels=len(rep), ntex=len(TEX), nmat=len(NEW_MATS), ncmp=len(comparable),
                tris_u4=k(sum(rep[n]['tris'] for n in rep)), tris_u3=k(sum(u3tris[n] for n in comparable)),
                tris_u4_cmp=k(sum(rep[n]['tris'] for n in comparable)),
                tris_main=k(rep['BaseMain']['tris']), tris_main_u3=k(u3tris['BaseMain']),
                tris_hut=k(rep['TowerHut']['tris']), tris_hut_u3=k(u3tris['TowerHut']),
                changed_vp=', '.join(f'`{v}`' for v in CHANGED_VP), same_vp=', '.join(f'`{v}`' for v in SAME_VP))
    section = open(os.path.join(HERE, 'u4_readme_section.md'), encoding='utf-8').read().format(**vals)
    readme = open(os.path.join(u3_dir, ROOT, 'README.md'), encoding='utf-8').read().rstrip('\n') + '\n\n' + \
        section.rstrip('\n') + '\n'
    open(os.path.join(out_dir, 'README_u4_section.md'), 'w', encoding='utf-8').write(section)
    open(os.path.join(stage, ROOT, 'README.md'), 'w', encoding='utf-8').write(readme)
    entries.append((f'{ROOT}/README.md', u3guid[f'{ROOT}/README.md'], os.path.join(stage, ROOT, 'README.md'), None))

    # ---- unitypackage (gzip tar: <guid>/asset, <guid>/asset.meta, <guid>/pathname, as Update 3)
    guids = [g for _, g, _, _ in entries]
    assert len(set(guids)) == len(guids), 'duplicate GUID'
    new_guids = {g for p, g, _, _ in entries if p.startswith(f'{ROOT}/Textures/')}
    assert not (new_guids & set(u3guid.values())), 'texture GUID collides with Update 3'
    pkg = os.path.join(out_dir, 'Forest_Update4.unitypackage')
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
    manifest = {'package': os.path.basename(pkg), 'bytes': os.path.getsize(pkg), 'entries': len(entries),
                'files': [{'path': p, 'guid': g, 'bytes': os.path.getsize(s) if s else None,
                           'md5': hashlib.md5(open(s, 'rb').read()).hexdigest() if s else None} for p, g, s, _ in entries],
                'changes': changes}
    json.dump(manifest, open(os.path.join(out_dir, 'Forest_Update4_manifest.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'[u4] {pkg}: {len(entries)} entries, {os.path.getsize(pkg) / 1e6:.2f} MB')
    for c in changes:
        print('   ', c)


if __name__ == '__main__':
    main(*sys.argv[1:6])
