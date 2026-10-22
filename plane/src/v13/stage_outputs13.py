"""Copy the v13 delivery into /mnt/user-data/outputs (for the device commit) and write an md5 manifest.
python3 stage_outputs13.py"""
import os, shutil, hashlib, json

SRC = '/home/claude/plane/v13/deliv/UtilityPlane_Unity_v13'
DOCS = '/home/claude/plane/v13/docs'
OUT = '/mnt/user-data/outputs/v13'
if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(SRC, os.path.join(OUT, 'UtilityPlane_Unity_v13'))
os.makedirs(os.path.join(OUT, 'docs'), exist_ok=True)
for f in ('PLANE_V13_UPGRADE_UNITY.md', 'START_PLANE_V13_UPGRADE.txt'):
    shutil.copyfile(os.path.join(DOCS, f), os.path.join(OUT, 'docs', f))
man = {}
for dp, dn, fn in os.walk(OUT):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        man[os.path.relpath(p, OUT).replace(os.sep, '/')] = hashlib.md5(open(p, 'rb').read()).hexdigest()
json.dump(man, open('/home/claude/plane/v13/manifest13.json', 'w'), indent=1, ensure_ascii=False)
print('files', len(man), 'bytes', sum(os.path.getsize(os.path.join(OUT, k)) for k in man))
