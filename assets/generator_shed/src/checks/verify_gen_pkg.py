"""open the packaged generator shed from a clean unzip: every image resolves inside the package, the contract and lamps
agree with the blend, the doc and sheets are there"""
import bpy, os, sys, json, zipfile, shutil
ZP = '/home/claude/uaz/out/gen_package.zip'
D = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/pkg_check'
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)
zipfile.ZipFile(ZP).extractall(D)
root = os.path.join(D, 'generator_shed')
files = sorted(os.path.relpath(os.path.join(r, f), root) for r, _, fs in os.walk(root) for f in fs)
print('files', len(files))
bpy.ops.wm.open_mainfile(filepath=os.path.join(root, 'gen.blend'))
bad = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    p = bpy.path.abspath(im.filepath)
    if not os.path.isfile(p) or not os.path.realpath(p).startswith(os.path.realpath(root)):
        bad.append(('image', im.name, im.filepath))
    else:
        im.reload()
        if im.size[0] == 0:
            bad.append(('image not loading', im.name))
C = json.load(open(os.path.join(root, 'gen_contract.json')))
L = json.load(open(os.path.join(root, 'gen_lights.json')))
for k, p in C['parts'].items():
    if p['object'] and p['object'] not in bpy.data.objects:
        bad.append(('part object missing', k))
for c in C['colliders']:
    if c['name'] not in bpy.data.objects:
        bad.append(('collider missing', c['name']))
for l in L['lights']:
    if l['socket'] not in bpy.data.objects or l['lens'] not in bpy.data.objects:
        bad.append(('light', l['socket']))
    for f in (l['ies'], 'Cookies/%s.png' % l.get('cookie', '')):
        if not os.path.isfile(os.path.join(root, 'tex', f)):
            bad.append(('light file missing', f))
for need in ('GEN_CONTRACT.md', 'gen_A.jpg', 'gen_B.jpg', 'gen_C.jpg', 'gen.json', 'src/gen_build.py'):
    if need not in files:
        bad.append(('missing file', need))
mats = sorted({m.name for o in bpy.data.objects if o.type == 'MESH' for m in o.data.materials if m})
print('materials', mats)
print('objects', len([o for o in bpy.data.objects if o.type == 'MESH']), 'empties', len([o for o in bpy.data.objects if o.type == 'EMPTY']))
print('PROBLEMS', bad or 'none')
