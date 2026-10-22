"""Forest Update 5: the package in the location generator's format, over Update 4 (as Update 4 over Update 3).

  Models/   25 FBX from u5_export.py (same names and GUIDs as the models they replace: Update 3's package or, for
            LogPile, FenceChain, OldFence a / b / c and Forest_Wires, the project's)
  Textures/ the base's and far points' PSX atlases renamed to the core's convention (T_*_A_px: Point filter, no
            compression, set by SkyIslandImport on import)
  Data/     Forest_Layout.json and Forest_Materials.json = Update 4's files (byte-exact round trip) with the block u5 in the
            layout and the new materials at the end of the list; nothing else changes (places, lights, halos,
            interactables, power, flickers stay Update 3's)
  README.md Update 4's README + the section "Обновление 5"

The viewpoints whose previews see the new models (frustum at 16:9 and 220 m of fog, no occlusion) are computed here.

python3 u5_build.py <fbx_dir> <u4_dir> <u3raw_dir> <out_dir>
  u4_dir: out/forest_update4 (its stage/ holds Update 4's Data and README), u3raw_dir: Update 3's unitypackage entries"""
import os, sys, json, shutil, hashlib, tarfile, io, time, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u4_build as U4
import base_spec as BS
import far_spec as FS

PKG = os.path.join(HERE, 'out')
ROOT = 'Assets/Locations/Forest'

BASE_ATL = ('Props', 'Helipad', 'Mast', 'Poles', 'Fence')
FAR_ATL = ('Dish16', 'Dish12', 'Towers', 'Meteo', 'Lookout', 'Chapel', 'Small')
TEX = ([(f'forest_base/tex/T_Base_{a}_BaseColor.png', f'T_Base_{a}_A_px.png') for a in BASE_ATL + ('Panel',)] +
       [(f'forest_base/tex/T_Base_{a}.png', f'T_Base_{a}_A_px.png') for a in ('ChainLink', 'Barbed', 'Rust')] +
       [(f'forest_far/tex/T_Far_{a}_BaseColor.png', f'T_Far_{a}_A_px.png') for a in FAR_ATL + ('Panel',)])

NEW_MATS = ([U4.atlas(f'M_Base_{a}', f'T_Base_{a}_A_px.png') for a in BASE_ATL] +
            # sign faces: the retroreflective glow of Update 3's M_ObsSigns (emission = the albedo at 0.06)
            [U4.spec('M_Base_Panel', 'T_Base_Panel_A_px.png', emap='T_Base_Panel_A_px.png', emission=(1, 1, 1), ei=0.06)] +
            [U4.cut(f'M_Base_{a}', f'T_Base_{a}_A_px.png') for a in ('ChainLink', 'Barbed', 'Rust')] +
            [U4.atlas(f'M_Far_{a}', f'T_Far_{a}_A_px.png') for a in FAR_ATL] +
            [U4.spec('M_Far_Panel', 'T_Far_Panel_A_px.png', emap='T_Far_Panel_A_px.png', emission=(1, 1, 1), ei=0.06)])

GUIDS = dict(BS.U3['guids'], **FS.U3['guids'])
FOG = 220.0


def guid_of(path):
    return hashlib.md5(('snow/Forest/Update5/' + path).encode()).hexdigest()


def _qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, np.float64)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def placements():
    """(model, Unity p, q) of every place of the 25 models; Forest_Wires is a world model at the origin"""
    out = []
    for S in (BS, FS):
        for m, lst in S.U3['prefabs'].items():
            out += [(m, e['p'], e['q']) for e in lst]
        for m, lst in S.U3.get('scatter', {}).items():
            out += [(m, e['p'], e['q']) for e in lst]
    out.append(('Forest_Wires', [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]))
    return out


def seen_from(vp, rep):
    """does the viewpoint's preview (16:9, its vertical fov, 220 m of fog) see any of the models? (a 3 x 3 x 3 sample of each
    object's box, in Unity world coordinates; no occlusion)"""
    p = np.array(vp['p'], np.float64)
    f = np.array(vp['target'], np.float64) - p
    f /= np.linalg.norm(f)
    r = np.cross([0.0, 1.0, 0.0], f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    tv = math.tan(math.radians(vp['fov']) / 2)
    th = tv * 16 / 9
    hits = set()
    for m, pos, q in placements():
        for lo, hi in rep[m]['aabb'].values():                         # Blender frame of the prefab (x, y, z) -> Unity (-x, z, -y)
            g = np.array([[a, b, c] for a in np.linspace(lo[0], hi[0], 3) for b in np.linspace(lo[1], hi[1], 3)
                          for c in np.linspace(lo[2], hi[2], 3)])
            loc = np.stack([-g[:, 0], g[:, 2], -g[:, 1]], 1)
            w = np.array([_qrot(q, v) for v in loc]) + np.array(pos)
            d = w - p
            z = d @ f
            ok = (z > 0.3) & (np.linalg.norm(d, axis=1) < FOG)
            ok &= (np.abs(d @ r) <= z * th) & (np.abs(d @ u) <= z * tv)
            if ok.any():
                hits.add(m)
                break
    return sorted(hits)


def main(fbx_dir, u4_dir, u3raw_dir, out_dir):
    rep = json.load(open(os.path.join(fbx_dir, 'u5_export_report.json')))
    assert sorted(rep) == sorted(GUIDS), (sorted(rep), sorted(GUIDS))
    u4stage = os.path.join(u4_dir, 'stage')
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
    entries = []

    def folder(path):
        g = u3guid[path]
        meta = open(os.path.join(u3raw_dir, g, 'asset.meta'), encoding='utf-8').read()
        entries.append((path, g, None, meta))

    for f in ('Assets/Locations', ROOT, f'{ROOT}/Models', f'{ROOT}/Textures', f'{ROOT}/Data'):
        folder(f)

    # ---- models (the GUIDs the project has: Update 3's package, or the project's own .meta for six of them)
    src_of = {}
    for name in sorted(rep):
        pn = f'{ROOT}/Models/{name}.fbx'
        g = GUIDS[name]
        if pn in u3guid:
            assert u3guid[pn] == g, f'{pn}: {g} differs from Update 3\'s {u3guid[pn]}'
            src_of[name] = 'Update 3'
        else:
            src_of[name] = 'project'
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

    # ---- materials: Update 4's file + the new ones at the end
    mats_raw = open(os.path.join(u4stage, ROOT, 'Data/Forest_Materials.json'), encoding='utf-8').read()
    M = json.loads(mats_raw)
    assert json.dumps(M, indent=1) == mats_raw
    names = {m['name'] for m in M['materials']}
    for s in NEW_MATS:
        assert s['name'] not in names, s['name']
    used = sorted({m for r in rep.values() for m in r['materials']})
    missing = [m for m in used if m not in names and m not in {s['name'] for s in NEW_MATS}]
    assert not missing, f'materials not defined: {missing}'
    M['materials'].extend(NEW_MATS)
    open(os.path.join(stage, ROOT, 'Data/Forest_Materials.json'), 'w', encoding='utf-8').write(json.dumps(M, indent=1))
    entries.append((f'{ROOT}/Data/Forest_Materials.json', u3guid[f'{ROOT}/Data/Forest_Materials.json'],
                    os.path.join(stage, ROOT, 'Data/Forest_Materials.json'), None))

    # ---- layout: Update 4's + the block u5 (nothing else changes)
    lay_raw = open(os.path.join(u4stage, ROOT, 'Data/Forest_Layout.json'), encoding='utf-8').read()
    L = json.loads(lay_raw)
    assert json.dumps(L, separators=(',', ':')) == lay_raw
    vps = {v['name']: v for v in L['viewpoints']}
    seen = {n: seen_from(v, rep) for n, v in vps.items()}
    changed = [n for n, s in seen.items() if s]
    same = [n for n, s in seen.items() if not s]
    L['u5'] = {'update': 5, 'note': 'Forest Update 5: 25 models of the base and the far points rebuilt in the generator '
                                    'shed\'s look (same names, GUIDs, IX parts, pivots, axes, travel, places, lights and '
                                    'halos); see FOREST_U5_UNITY.md',
               'replaced': sorted(rep), 'changes': []}
    open(os.path.join(stage, ROOT, 'Data/Forest_Layout.json'), 'w', encoding='utf-8').write(
        json.dumps(L, separators=(',', ':')))
    entries.append((f'{ROOT}/Data/Forest_Layout.json', u3guid[f'{ROOT}/Data/Forest_Layout.json'],
                    os.path.join(stage, ROOT, 'Data/Forest_Layout.json'), None))

    # ---- README: Update 4's + the section "Обновление 5"
    u3tris = dict(BS.U3['u3_models'], **FS.U3['u3_models'])
    k = lambda v: f'{v / 1000:.1f}'.replace('.', ',')
    vals = dict(nmodels=len(rep), ntex=len(TEX), nmat=len(NEW_MATS), tris_u5=k(sum(rep[n]['tris'] for n in rep)),
                tris_u3=k(sum(u3tris[n]['tris'] for n in rep)),
                changed_vp=', '.join(f'`{v}`' for v in changed), same_vp=', '.join(f'`{v}`' for v in same))
    section = open(os.path.join(HERE, 'u5_readme_section.md'), encoding='utf-8').read().format(**vals)
    readme = open(os.path.join(u4stage, ROOT, 'README.md'), encoding='utf-8').read().rstrip('\n') + '\n\n' + \
        section.rstrip('\n') + '\n'
    open(os.path.join(out_dir, 'README_u5_section.md'), 'w', encoding='utf-8').write(section)
    open(os.path.join(stage, ROOT, 'README.md'), 'w', encoding='utf-8').write(readme)
    entries.append((f'{ROOT}/README.md', u3guid[f'{ROOT}/README.md'], os.path.join(stage, ROOT, 'README.md'), None))

    # ---- unitypackage (gzip tar: <guid>/asset, <guid>/asset.meta, <guid>/pathname)
    guids = [g for _, g, _, _ in entries]
    assert len(set(guids)) == len(guids), 'duplicate GUID'
    new_guids = {g for p, g, _, _ in entries if p.startswith(f'{ROOT}/Textures/')}
    assert not (new_guids & set(u3guid.values())), 'texture GUID collides with Update 3'
    pkg = os.path.join(out_dir, 'Forest_Update5.unitypackage')
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
                'over': 'Forest_Update4', 'guid_source': src_of,
                'files': [{'path': p, 'guid': g, 'bytes': os.path.getsize(s) if s else None,
                           'md5': hashlib.md5(open(s, 'rb').read()).hexdigest() if s else None} for p, g, s, _ in entries],
                'viewpoints_seeing_new_models': {n: s for n, s in seen.items() if s},
                'viewpoints_unchanged': same, 'changes': []}
    json.dump(manifest, open(os.path.join(out_dir, 'Forest_Update5_manifest.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'[u5] {pkg}: {len(entries)} entries, {os.path.getsize(pkg) / 1e6:.2f} MB')
    print('[u5] viewpoints that see the new models:', {n: s for n, s in seen.items() if s})
    print('[u5] unchanged:', same)


if __name__ == '__main__':
    main(*sys.argv[1:5])
