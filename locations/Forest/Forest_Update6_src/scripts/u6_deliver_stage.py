"""Everything of Update 6 in the PC's layout (F:\\ClaudeGames\\snow\\...), as zips of at most ~18 MB with an md5 list:
  source/assets/forest_gencont/, forest_gencont_package.zip, the same for forest_items and forest_figure
  source/locations/Forest/Forest_Update6.unitypackage, Forest_Update6_src/, README_Forest.md (the package's README)
  source/gallery/31_forest-gencont_*, 32_forest-items_*, 33_forest-figure_* (copies of the sheets and renders)
  docs/gdd/FOREST_U6_UNITY.md, GENCONT_FOREST_CONTRACT.md, ITEMS_CONTRACT.md, APPARITION_CONTRACT.md;
  docs/start/START_FOREST_U6.txt
python3 u6_deliver_stage.py <u6_out_dir> <stage_dir>  -> <stage_dir>/snow/..., <stage_dir>/forest_u6_p<N>.zip, md5.txt"""
import os, sys, shutil, hashlib, zipfile, glob

HERE = os.path.dirname(os.path.abspath(__file__))
u6, st = sys.argv[1:3]
root = os.path.join(st, 'snow')
if os.path.exists(root):
    shutil.rmtree(root)
for z in glob.glob(os.path.join(st, 'forest_u6_p*.zip')):
    os.remove(z)


def put(src, rel):
    d = os.path.join(root, rel)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(src, d)


GALLERY = {'gencont': '31_forest-gencont', 'items': '32_forest-items', 'figure': '33_forest-figure'}
for kind, gal in GALLERY.items():
    pk = os.path.join(HERE, 'out', f'forest_{kind}')
    for r, _, fs in os.walk(pk):
        for f in fs:
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(r, f)
            rel = os.path.relpath(p, pk)
            put(p, os.path.join('source', 'assets', f'forest_{kind}', rel))
            # gallery: the sheets (top level jpg) and the renders, flat, <номер>_<что>_<кадр>
            if (os.sep not in rel and f.endswith('.jpg')) or rel.startswith('renders' + os.sep):
                sub = os.path.dirname(rel)[len('renders'):].strip(os.sep).replace(os.sep, '-')
                base = os.path.splitext(f)[0]
                name = f'{gal}_{sub + "_" if sub else ""}{base}{os.path.splitext(f)[1]}'
                put(p, os.path.join('source', 'gallery', name))
    put(os.path.join(HERE, 'out', f'forest_{kind}_package.zip'), os.path.join('source', 'assets', f'forest_{kind}_package.zip'))
put(os.path.join(u6, 'Forest_Update6.unitypackage'), 'source/locations/Forest/Forest_Update6.unitypackage')
put(os.path.join(u6, 'stage', 'Assets', 'Locations', 'Forest', 'README.md'), 'source/locations/Forest/README_Forest.md')
src = os.path.join(u6, 'src')
for r, _, fs in os.walk(src):
    for f in fs:
        p = os.path.join(r, f)
        put(p, os.path.join('source', 'locations', 'Forest', 'Forest_Update6_src', os.path.relpath(p, src)))
for f in ('FOREST_U6_UNITY.md', 'GENCONT_FOREST_CONTRACT.md', 'ITEMS_CONTRACT.md', 'APPARITION_CONTRACT.md'):
    put(os.path.join(HERE, 'docs', f), os.path.join('docs', 'gdd', f))
put(os.path.join(HERE, 'docs', 'START_FOREST_U6.txt'), 'docs/start/START_FOREST_U6.txt')

lines, files, total = [], [], 0
for r, ds, fs in os.walk(root):
    ds.sort()
    for f in sorted(fs):
        p = os.path.join(r, f)
        rel = os.path.relpath(p, root).replace(os.sep, '/')
        lines.append(f'{hashlib.md5(open(p, "rb").read()).hexdigest()}  {rel}')
        files.append((rel, p))
        total += os.path.getsize(p)
open(os.path.join(st, 'md5.txt'), 'w').write('\n'.join(lines) + '\n')
put(os.path.join(st, 'md5.txt'), 'source/locations/Forest/Forest_Update6_src/reports/delivery_md5.txt')   # what was delivered
files.append(('source/locations/Forest/Forest_Update6_src/reports/delivery_md5.txt',
              os.path.join(root, 'source/locations/Forest/Forest_Update6_src/reports/delivery_md5.txt')))
# parts of at most ~28 MB (the bridge fetches about 20 MB a file), stored: mostly png / jpg / zip / blend
LIMIT = 18 * 1024 * 1024
parts, cur, size = [], [], 0
for rel, p in files:
    s = os.path.getsize(p)
    if cur and size + s > LIMIT:
        parts.append(cur)
        cur, size = [], 0
    cur.append((rel, p))
    size += s
if cur:
    parts.append(cur)
for i, part in enumerate(parts, 1):
    zp = os.path.join(st, f'forest_u6_p{i}.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:
        for rel, p in part:
            z.write(p, rel)
    print(f'part {i}: {len(part)} files, {os.path.getsize(zp) / 1e6:.1f} MB')
print(len(lines), 'files,', round(total / 1e6, 1), 'MB in', len(parts), 'parts')
