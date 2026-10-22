"""v12 Blender files from the v11 ones: same scenes, PSX interior materials (as Unity v12):
 - M_Cockpit, M_Interior, M_Floor, M_Seats, M_Fittings, M_Webbing: normal-map nodes and the *_Normal images removed,
   textures point-sampled (Closest);
 - M_Gauges, M_Annunciator: point-sampled; M_RadioDisplay wired like Unity (base T_Gauges_BC, emission
   T_Displays_Emission; v11 had a plain white emission there);
 - textures stay relative (//../Assets/UtilityPlane/Textures): in UtilityPlane_Unity_v12/Blender they resolve to v12.
python3 make_blend12.py <in.blend> <out.blend> [readme_text_name]"""
import bpy, sys, os

src, dst = sys.argv[-3], sys.argv[-2]
readme = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=src)
PSX = ('M_Cockpit', 'M_Interior', 'M_Floor', 'M_Seats', 'M_Fittings', 'M_Webbing', 'M_Gauges', 'M_Annunciator',
       'M_RadioDisplay')
removed = []
for mn in PSX:
    m = bpy.data.materials.get(mn)
    assert m is not None, mn
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type == 'NORMAL_MAP' or (n.type == 'TEX_IMAGE' and n.image and n.image.name.split('.png')[0].endswith('_Normal')):
            removed.append(f'{mn}:{n.type}:{n.image.name if getattr(n, "image", None) else ""}')
            nt.nodes.remove(n)
    if mn == 'M_RadioDisplay' and not any(n.type == 'TEX_IMAGE' for n in nt.nodes):
        pb = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
        for img, sock in (('T_Gauges_BC.png', 'Base Color'), ('T_Displays_Emission.png', 'Emission Color')):
            t = nt.nodes.new('ShaderNodeTexImage')
            t.image = bpy.data.images[img]
            nt.links.new(t.outputs['Color'], pb.inputs[sock])
        if pb.inputs['Emission Strength'].default_value == 0.0:
            pb.inputs['Emission Strength'].default_value = 1.2
    for n in nt.nodes:
        if n.type == 'TEX_IMAGE':
            n.interpolation = 'Closest'
for im in [im for im in bpy.data.images if im.users == 0 and im.source == 'FILE']:
    removed.append('image:' + im.name)
    bpy.data.images.remove(im)
NOTE = '''v12 (PSX interior): materials M_Cockpit, M_Interior, M_Floor, M_Seats, M_Fittings, M_Webbing without normal maps,
every interior and instrument texture point-sampled (Closest) as in Unity; M_RadioDisplay uses T_Gauges_BC with the
T_Displays_Emission glow (in v11 the radio faces glowed plain white here). Textures: ..\\Assets\\UtilityPlane\\Textures of
the v12 package (PSX interior atlases, pixel-art instrument / placard atlas 1024). The rest of this text describes v11
and is still valid.

'''
t = bpy.data.texts.get(readme) if readme else None
if t is not None:
    body = t.as_string()
    t.clear()
    t.write(NOTE + body)
    t.name = readme.replace('v11', 'v12')
bpy.context.preferences.filepaths.use_relative_paths = True
os.makedirs(os.path.dirname(dst), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True, relative_remap=False)
print('SAVED', dst, 'removed', len(removed), removed)
