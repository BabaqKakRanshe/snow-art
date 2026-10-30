"""shared by station_quick / station_render: open the built file, put the snow_kit monitors on the rack's slots and the
forest_devices ObjectPC (+ its kit monitor) on the table's Slot_PC as linked collection instances (preview only - the
delivered station.blend holds none), a 1.8 m figure for scale"""
import os
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'source', 'assets'))
KIT = os.path.join(ASSETS, 'snow_kit', 'snow_kit.blend')
DEV = os.path.join(ASSETS, 'forest_devices', 'devices.blend')


def open_built(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    for o in bpy.data.objects:
        if o.name.startswith('COL_'):
            o.hide_render = True
            o.hide_set(True)
    for m in bpy.data.materials:
        if m.node_tree:
            for nd in m.node_tree.nodes:
                if nd.type == 'TEX_IMAGE':
                    nd.interpolation = 'Closest'


def _inst(name, coll, M):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.instance_type = 'COLLECTION'
    e.instance_collection = coll
    e.matrix_world = M
    return e


def furnish(monitors=True, pc=True):
    with bpy.data.libraries.load(KIT, link=True) as (src, dst):
        dst.collections = ['Kit_Monitor_CRT']
    mon = dst.collections[0]
    out = []
    O = bpy.data.objects
    if monitors:
        for i in range(1, 10):
            out.append(_inst(f'prev_Mon_{i}', mon, O[f'Slot_{i}'].matrix_world.copy()))
    if pc and 'Slot_PC' in O:
        with bpy.data.libraries.load(DEV, link=True) as (src, dst):
            dst.collections = ['ObjectPC']
        M = O['Slot_PC'].matrix_world.copy()
        out.append(_inst('prev_PC', dst.collections[0], M))
        out.append(_inst('prev_PC_Mon', mon, M @ Matrix.Translation((0, 0, 0.14))))
    return out


def figure(pos):
    """a 1.8 m grey stand-in (capsule r 0.2) for scale"""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.4, location=(pos[0], pos[1], 0.9), vertices=16)
    a = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(pos[0], pos[1], 1.6), segments=16, ring_count=8)
    b = bpy.context.object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(pos[0], pos[1], 0.2), segments=16, ring_count=8)
    c = bpy.context.object
    m = bpy.data.materials.new('M_prev_figure')
    m.diffuse_color = (0.35, 0.36, 0.38, 1)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (0.35, 0.36, 0.38, 1)
    for o in (a, b, c):
        o.data.materials.append(m)
    return [a, b, c]
