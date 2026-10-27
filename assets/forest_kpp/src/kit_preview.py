"""Previews only (the Blender renders of the KPP and the main building): a monitor instance of the snow kit shows its own
stand-in picture. The instances share the kit's collection (one screen mesh), so the instance gets a copy of that collection
whose Kit_Monitor_Screen has its own mesh and the property screen_on = M_Kit_Screen_On_<tag> (a copy of M_Kit_Screen_On with
tex/snow_kit/<png>); the power switches of kpp2_game.py and main_render.py put that material on it instead of M_Kit_Screen_On.
screen_variant(empty, png_path, tag) -> the new collection.  (In Unity each monitor shows its camera: render textures.)"""
import os
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))


def screen_on_material():
    m = bpy.data.materials.get('M_Kit_Screen_On')
    if m is None:                                     # not in the file yet: from the kit itself
        with bpy.data.libraries.load(os.path.join(HERE, 'snow_kit', 'snow_kit.blend'), link=False) as (src, dst):
            dst.materials = ['M_Kit_Screen_On']
        m = bpy.data.materials['M_Kit_Screen_On']
    return m


def screen_variant(e, png, tag):
    src = e.instance_collection
    dst = bpy.data.collections.new(f'{src.name}_{tag}')
    dst.instance_offset = src.instance_offset
    m = screen_on_material().copy()
    m.name = f'M_Kit_Screen_On_{tag}'
    img = bpy.data.images.load(png, check_existing=True)
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE':
            n.image = img
            n.interpolation = 'Closest'
    pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if pb is not None:
        pb.inputs['Emission Strength'].default_value = 1.8
    cp = {}
    for o in src.objects:
        c = o.copy()
        if o.type == 'MESH' and o.name.startswith('Kit_Monitor_Screen'):
            c.data = o.data.copy()
            c['screen_on'] = m.name
        dst.objects.link(c)
        cp[o] = c
    for o, c in cp.items():
        if o.parent in cp:
            c.parent = cp[o.parent]
            c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    e.instance_collection = dst
    return dst
