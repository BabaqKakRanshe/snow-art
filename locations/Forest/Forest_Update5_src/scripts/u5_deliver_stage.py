"""Everything of Update 5 in the PC's layout (F:\\ClaudeGames\\snow\\...), as one zip with an md5 list:
  source/assets/forest_base/ (+ renders/), forest_base_package.zip, the same for forest_far
  source/locations/Forest/Forest_Update5.unitypackage, Forest_Update5_src/, README_Forest.md (the package's README)
  docs/gdd/BASE_CONTRACT.md, FAR_CONTRACT.md, FOREST_U5_UNITY.md; docs/start/START_FOREST_U5.txt
python3 u5_deliver_stage.py <u5_out_dir> <stage_dir>  -> <stage_dir>/snow/..., <stage_dir>/forest_u5_delivery.zip, md5.txt"""
import os, sys, shutil, hashlib, zipfile, glob

HERE = os.path.dirname(os.path.abspath(__file__))
u5, st = sys.argv[1:3]
root = os.path.join(st, 'snow')
if os.path.exists(root):
    shutil.rmtree(root)


def put(src, rel):
    d = os.path.join(root, rel)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(src, d)


for kind in ('base', 'far'):
    pk = os.path.join(HERE, 'out', f'forest_{kind}')
    for r, _, fs in os.walk(pk):
        for f in fs:
            if f.endswith(('.blend1', '.pyc')):
                continue
            p = os.path.join(r, f)
            put(p, os.path.join('source', 'assets', f'forest_{kind}', os.path.relpath(p, pk)))
    for f in sorted(glob.glob(os.path.join(HERE, 'rend', kind, '*.png'))):
        put(f, os.path.join('source', 'assets', f'forest_{kind}', 'renders', os.path.basename(f)))
    put(os.path.join(HERE, 'out', f'forest_{kind}_package.zip'), os.path.join('source', 'assets', f'forest_{kind}_package.zip'))
put(os.path.join(u5, 'Forest_Update5.unitypackage'), 'source/locations/Forest/Forest_Update5.unitypackage')
put(os.path.join(u5, 'stage', 'Assets', 'Locations', 'Forest', 'README.md'), 'source/locations/Forest/README_Forest.md')
src = os.path.join(u5, 'src')
for r, _, fs in os.walk(src):
    for f in fs:
        p = os.path.join(r, f)
        put(p, os.path.join('source', 'locations', 'Forest', 'Forest_Update5_src', os.path.relpath(p, src)))
for f in ('BASE_CONTRACT.md', 'FAR_CONTRACT.md', 'FOREST_U5_UNITY.md'):
    put(os.path.join(HERE, 'docs', f), os.path.join('docs', 'gdd', f))
put(os.path.join(HERE, 'docs', 'START_FOREST_U5.txt'), 'docs/start/START_FOREST_U5.txt')

lines, total = [], 0
for r, ds, fs in os.walk(root):
    ds.sort()
    for f in sorted(fs):
        p = os.path.join(r, f)
        rel = os.path.relpath(p, root).replace(os.sep, '/')
        lines.append(f'{hashlib.md5(open(p, "rb").read()).hexdigest()}  {rel}')
        total += os.path.getsize(p)
open(os.path.join(st, 'md5.txt'), 'w').write('\n'.join(lines) + '\n')
put(os.path.join(st, 'md5.txt'), 'source/locations/Forest/Forest_Update5_src/reports/delivery_md5.txt')   # what was delivered
zp = os.path.join(st, 'forest_u5_delivery.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:          # mostly PNG / zip / blend: stored, no recompression
    for r, ds, fs in os.walk(root):
        for f in sorted(fs):
            p = os.path.join(r, f)
            z.write(p, os.path.relpath(p, root).replace(os.sep, '/'))
print(len(lines), 'files,', round(total / 1e6, 1), 'MB ->', zp, round(os.path.getsize(zp) / 1e6, 1), 'MB')
