"""Post-bake ORM tweaks without re-baking: raise roughness on the anti-glare glareshield.
usage: python3 patch_orm.py <tag>"""
import bpy, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'final2'
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_final_{TAG}.blend'))
path = os.path.join(HERE, 'export', 'ue', 'Textures', 'T_Cockpit_ORM.png')
orm = np.asarray(Image.open(path).convert('RGB')).copy()
R = orm.shape[0]
PATCH = {'CP_Glareshield': 0.93}          # object: roughness
for on, rough in PATCH.items():
    ob = bpy.data.objects[on]
    me = ob.data
    uv = me.uv_layers[0].data
    mask = Image.new('L', (R, R), 0)
    d = ImageDraw.Draw(mask)
    for p in me.polygons:
        if me.materials[p.material_index].name != 'M_Cockpit':
            continue
        d.polygon([(uv[i].uv[0] * R, (1 - uv[i].uv[1]) * R) for i in p.loop_indices], fill=255)
    mask = np.asarray(mask.filter(ImageFilter.MaxFilter(5))) > 0
    g = orm[..., 1].astype(np.float32)
    g[mask] = np.maximum(g[mask], rough * 255)
    orm[..., 1] = g.astype(np.uint8)
    print(on, 'texels patched', int(mask.sum()))
Image.fromarray(orm, 'RGB').save(path, optimize=True)
