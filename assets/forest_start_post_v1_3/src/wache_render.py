"""Views of the guard house with the booth's parts moved in (StartBooth.fbx of the project: IX_Door, Lamp_Booth, Lens_Booth,
Glow_Booth, Booth_Sign by wache_kit.MOVES), snowy ground, a 1.8 m figure. Review recipe of snow_style.json (Cycles 1100 x 700,
day world (0.56, 0.62, 0.72) 0.85 + sun 3.0; night world (0.010, 0.012, 0.020) 0.6 with the lamps lit).
python3.11 -I wache_render.py <blend> <out_dir> <views,...|all> [spp] [--wb] [--open]   (--wb: Workbench draft; --open: door open 80)"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix, Euler
import wache_kit as W
import start_kit as SK

BOOTH_FBX = '/mnt/user-data/uploads/snow/Snow/Assets/Levels/Forest/Start/Models/StartBooth.fbx'
START_TEX = '/mnt/user-data/uploads/snow/Snow/Assets/Levels/Forest/Start/Textures/T_Start_Start_BaseColor.png'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
blend, out_dir, views = args[0], args[1], args[2]
spp = int(args[3]) if len(args) > 3 else 24
WB = '--wb' in sys.argv
OPEN = '--open' in sys.argv
os.makedirs(out_dir, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene


def img_mat(name, path, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pb = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = bpy.data.images.load(path, check_existing=True)
    ti.interpolation = 'Closest'
    nt.links.new(ti.outputs[0], pb.inputs['Base Color'])
    pb.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in pb.inputs:
        pb.inputs['Specular IOR Level'].default_value = 0.25
    return m


# ---- the booth's parts, moved in
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=BOOTH_FBX)
new = [o for o in bpy.data.objects if o not in before]
m_start = img_mat('M_Start_Start_view', START_TEX)
panel = bpy.data.images.get('T_Start_Panel_BaseColor.png')
m_panel = img_mat('M_Start_Panel_view', panel.filepath if panel else START_TEX, 0.6)
lens = bpy.data.materials.get('M_Start_Lamp_Booth')
glow = bpy.data.materials.get('M_Start_Glow')
for o in new:
    if o.name in ('StartBooth', 'Booth_Glass') or o.name.startswith('StartBooth') or o.name.startswith('Booth_Glass'):
        continue
for o in list(new):
    base = o.name.split('.')[0]
    if base in ('StartBooth', 'Booth_Glass', 'IX_Door'):
        continue
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = Matrix.Translation(W.MOVES[base]) @ mw
    mat = {'Lamp_Booth': m_start, 'Booth_Sign': m_panel, 'Lens_Booth': lens, 'Glow_Booth': glow}[base]
    o.data.materials.clear()
    o.data.materials.append(mat)
    if base == 'Glow_Booth':
        o.visible_shadow = False
for o in list(new):
    if o.name.split('.')[0] in ('StartBooth', 'Booth_Glass', 'IX_Door'):
        bpy.data.objects.remove(o, do_unlink=True)
door = bpy.data.objects.get('IX_Door')
if door is not None and OPEN:
    door.rotation_euler.z += math.radians(80)

# ---- ground, figure, world, sun
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0.0))
g = bpy.context.object
gm = bpy.data.materials.new('ground')
gm.use_nodes = True
pbg = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pbg.inputs['Base Color'].default_value = (0.62, 0.66, 0.72, 1)
pbg.inputs['Roughness'].default_value = 0.95
g.data.materials.append(gm)
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.8, location=(W.HX + 1.6, -1.2, 0.9))
fig = bpy.context.object
fm = bpy.data.materials.new('figure')
fm.use_nodes = True
next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.08, 0.09, 0.1, 1)
fig.data.materials.append(fm)
night = False


def setup_world(is_night):
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    if is_night:
        bg.inputs['Color'].default_value = (0.010, 0.012, 0.020, 1)
        bg.inputs['Strength'].default_value = 0.6
    else:
        bg.inputs['Color'].default_value = (0.56, 0.62, 0.72, 1)
        bg.inputs['Strength'].default_value = 0.85


sun_d = bpy.data.lights.new('Sun', 'SUN')
sun_d.energy = 3.0
sun_o = bpy.data.objects.new('Sun', sun_d)
sun_o.rotation_euler = Euler((math.radians(52), 0, math.radians(-35)))
sc.collection.objects.link(sun_o)
lamps = []
for name, pos, energy, colr in (('in', Vector(W.CONTRACT['sockets']['LIGHT_Wache_Inside']['pos']) if 'LIGHT_Wache_Inside' in W.CONTRACT['sockets']
                                  else Vector((0.0, -0.2, W.z_ci(-0.2) - 0.18)), 80, (1.0, 0.70, 0.42)),
                                ('door', SK.BULK + W.MOVES['Lamp_Booth'] + Vector((0.12, 0, -0.02)), 30, (1.0, 0.72, 0.42)),
                                ('stove', Vector((W.STOVE['x1'] + 0.2, (W.STOVE['y0'] + W.STOVE['y1']) / 2, W.FL + 0.45)), 6, (1.0, 0.42, 0.12))):
    ld = bpy.data.lights.new('L_' + name, 'POINT')
    ld.energy = energy
    ld.color = colr
    ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new('L_' + name, ld)
    lo.location = pos
    sc.collection.objects.link(lo)
    lamps.append(lo)

CAMS = {
    'front': ((3.6, -8.6, 1.75), (0.0, 0.0, 1.5), 30),
    'road': ((8.4, 3.6, 1.75), (1.9, 0.5, 1.7), 30),
    'back': ((-6.2, 7.8, 2.2), (0.0, 0.4, 1.5), 30),
    'inside': ((1.55, 1.10, 1.70), (-1.0, -1.2, 1.15), 16),
    'stove': ((1.45, -0.6, 1.65), (-1.3, 1.2, 0.9), 18),
    'night': ((4.6, -8.0, 1.75), (0.3, 0.0, 1.5), 30),
    'top': ((0.0, -0.01, 14.0), (0.0, 0.0, 0.0), 30),
    'pile': ((-0.2, 4.7, 1.25), (-0.6, 2.2, 0.62), 26),
}
if views == 'all':
    views = 'front,road,back,inside,stove,night'
if WB:
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = 'BOTH'
else:
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 1100, 700
for img in bpy.data.images:
    pass
for v in views.split(','):
    loc, tgt, lens_mm = CAMS[v]
    is_night = v == 'night'
    setup_world(is_night)
    sun_o.hide_render = is_night
    for lo in lamps:
        lo.hide_render = not (is_night or v in ('inside', 'stove'))
    for m in bpy.data.materials:
        if m.node_tree is None:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED' and m.get('night_emit') is not None:
                nd.inputs['Emission Strength'].default_value = float(m['night_emit']) if (is_night or v in ('inside', 'stove')) else 0.0
            if nd.type == 'EMISSION' and m.get('night_emit') is not None:
                nd.inputs['Strength'].default_value = float(m['night_emit']) if (is_night or v in ('inside', 'stove')) else 0.0
    cd = bpy.data.cameras.new('cam_' + v)
    cd.lens = lens_mm
    cd.clip_start = 0.05
    co = bpy.data.objects.new('cam_' + v, cd)
    sc.collection.objects.link(co)
    co.location = loc
    d = Vector(tgt) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.filepath = os.path.join(out_dir, f'wache_{v}{"_wb" if WB else ""}.png')
    bpy.ops.render.render(write_still=True)
    print('[render]', sc.render.filepath, flush=True)
