"""Assemble the UE deliverable and split it into zips below the 30 MiB transfer limit.
usage: python3 make_package.py <tag> <version>"""
import bpy, os, sys, shutil, zipfile, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'final2'
VER = sys.argv[2] if len(sys.argv) > 2 else 'v3'
UE = os.path.join(HERE, 'export', 'ue')
PKG = os.path.join(HERE, 'deliver', f'UtilityPlane_UE_{VER}')
LIMIT = 29 * 1024 * 1024
if os.path.isdir(PKG):
    shutil.rmtree(PKG)
os.makedirs(os.path.join(PKG, 'Textures'))
os.makedirs(os.path.join(PKG, 'Blender'))
os.makedirs(os.path.join(PKG, 'Renders'))

for f in ('SK_UtilityPlane.fbx', 'SK_UtilityPlane_Cockpit.fbx', 'rig.json', 'ue_import_utility_plane.py',
          'COMPONENTS.md', 'cargo_layout.json', 'interaction_volumes.json'):
    shutil.copy2(os.path.join(UE, f), PKG)
for f in sorted(glob.glob(os.path.join(UE, 'SM_Cargo_*.fbx'))):
    shutil.copy2(f, PKG)
shutil.copy2(os.path.join(HERE, 'ANIM_CONTRACT.md'), PKG)
shutil.copy2(os.path.join(HERE, 'README_UE.md'), os.path.join(PKG, 'README.md'))
for f in sorted(glob.glob(os.path.join(UE, 'Textures', '*.png'))):
    shutil.copy2(f, os.path.join(PKG, 'Textures'))
for f in sorted(glob.glob(os.path.join(HERE, 'renders', f'{VER}_*.jpg'))):
    shutil.copy2(f, os.path.join(PKG, 'Renders'))

# Blender source with textures relinked to the package folder
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_final_{TAG}.blend'))
for im in bpy.data.images:
    if im.source == 'FILE' and im.filepath:
        name = os.path.basename(bpy.path.abspath(im.filepath))
        if os.path.exists(os.path.join(PKG, 'Textures', name)):
            im.filepath = '//../Textures/' + name
for ob in list(bpy.data.objects):
    if ob.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(ob)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PKG, 'Blender', f'UtilityPlane_{VER}.blend'), compress=True,
                            relative_remap=False)

# split into zips: everything except textures first, then textures greedily
files = []
for root, _, fs in os.walk(PKG):
    for f in fs:
        p = os.path.join(root, f)
        files.append((os.path.relpath(p, os.path.dirname(PKG)), p, os.path.getsize(p)))
core = [x for x in files if '/Textures/' not in x[0]]
tex = sorted([x for x in files if '/Textures/' in x[0]], key=lambda x: -x[2])
groups = [core]
bins = []
for item in tex:
    for b in bins:
        if sum(i[2] for i in b) + item[2] < LIMIT:
            b.append(item)
            break
    else:
        bins.append([item])
groups += bins
out = []
for i, g in enumerate(groups, 1):
    kind = 'Meshes_Docs' if i == 1 else f'Textures_{i - 1}'
    zp = os.path.join(HERE, 'deliver', f'UtilityPlane_UE_{VER}_{i}_{kind}.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, p, _ in g:
            z.write(p, rel)
    out.append((zp, os.path.getsize(zp)))
for zp, sz in out:
    print('ZIP', os.path.basename(zp), round(sz / 2 ** 20, 1), 'MiB', 'OK' if sz < 30 * 2 ** 20 else 'TOO BIG')
