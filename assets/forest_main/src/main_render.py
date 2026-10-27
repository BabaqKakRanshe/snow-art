"""Renders of the baked main building (out/main.blend posed from out/main_contract.json): outside by day, the rooms with
Update 3's lights (the station powered: screens and LEDs on, the fixtures lit) or by a work light, plan cuts.
python3 -I main_render.py <views|all> [spp] [--test] [--work] -> rend/main[_test]/<view>.png"""
import sys, os, math, json, time, subprocess
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P

T0 = time.time()
TEST = '--test' in sys.argv
WORK = '--work' in sys.argv
sfx = '_test' if TEST else ''
OUT = os.path.join(P.HERE, 'rend', 'main' + sfx)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(P.HERE, 'out', f'main{sfx}.blend'))
sc = bpy.context.scene
CON = json.load(open(os.path.join(P.HERE, 'out', f'main_contract{sfx}.json')))
import main_spec as S

for name, p in CON['parts'].items():                                 # the start state: shutters rolled up
    o = bpy.data.objects.get(name)
    if o is not None and p['kind'] == 'scale':
        o.scale.z = p['range'][1] if p.get('open', True) else p['range'][0]       # Update 3: open = rolled up
for m in bpy.data.materials:                                         # point filter everywhere (PSX)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.interpolation = 'Closest'

# 1.2: the Leitstand's gate station is snow_kit instances linked from ../snow_kit/snow_kit.blend: made local (their screen and
# lamp materials switch with the power like the building's own); the kit's lit screen comes in from the kit file
KIT_LIB = [l for l in bpy.data.libraries]
if KIT_LIB:
    with bpy.data.libraries.load(bpy.path.abspath(KIT_LIB[0].filepath), link=True) as (src_, dst_):
        dst_.materials = [m for m in src_.materials if m in ('M_Kit_Screen_On',)]
    for coll_ in (bpy.data.collections, bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for idb in list(coll_):
            if idb.library is not None:
                try:
                    idb.make_local()
                except Exception as ex:
                    print('make_local', idb.name, ex)
    for o in bpy.data.objects:
        if o.name.startswith(('COL_', 'Glow_')):
            o.hide_render = True
    import kit_preview as KP                              # the gate monitor shows the gate camera's stand-in (CAM 2)
    e_gate = bpy.data.objects.get('Leit_Monitor_Gate')
    if e_gate is not None and e_gate.instance_collection is not None:
        KP.screen_variant(e_gate, os.path.join(P.HERE, 'tex', 'snow_kit', 'T_Kit_Screen_On_Gate.png'), 'Gate')
ON = {'M_ScreenOff': 'M_ScreenOn', 'M_LEDOff': 'M_LEDOn', 'M_Kit_Screen_Off': 'M_Kit_Screen_On'}


def u3mat(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        if m.name == 'M_Kit_Screen_On' and m.use_nodes:      # the kit's lit screen: its emission on
            pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if pb is not None:
                pb.inputs['Emission Strength'].default_value = 1.8
        return m
    d = next(x for x in json.load(open(os.path.join(P.HERE, 'main_u3_materials.json'))) if x['name'] == name)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    pb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pb.inputs['Base Color'].default_value = (*d['color'][:3], 1)
    pb.inputs['Emission Color'].default_value = (*d['emission'][:3], 1)
    pb.inputs['Emission Strength'].default_value = float(d.get('emissionIntensity', 0.0))
    return m


def power(on):
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        for s in o.material_slots:
            if s.material is None:
                continue
            n = s.material.name
            if on and n in ON:
                s.material = u3mat(o.get('screen_on', ON[n]) if n == 'M_Kit_Screen_Off' else ON[n])
            elif not on and n in ON.values():
                s.material = u3mat({v: k for k, v in ON.items()}[n])
            elif not on and n == o.get('screen_on'):
                s.material = u3mat('M_Kit_Screen_Off')


# ------------------------------------------------------------------ lights: Update 3's (prefab-local Unity -> building)
LIGHTS = []
for pl in CON['prefabLights']:
    for L in pl['lights']:
        u = L['p']
        pos = Vector((-u[0], -u[2], u[1]))
        d = L.get('d', [0, -1, 0])
        dirb = Vector((-d[0], -d[2], d[1]))
        kind = L['t']
        ld = bpy.data.lights.new('L_' + L.get('fx', 'x'), 'SPOT' if kind == 'spot' else 'POINT')
        col = L['c']
        ld.color = (col[0], col[1], col[2])
        ld.energy = 4 * math.pi ** 2 * float(L['i'])                # URP intensity -> W (the KPP / yard renders)
        ld.shadow_soft_size = 0.05
        if kind == 'spot':
            ld.spot_size = math.radians(float(L.get('a') or 90.0))
            ld.spot_blend = 0.35
        ob = bpy.data.objects.new('L_' + L.get('fx', 'x'), ld)
        ob.location = pos
        ob.rotation_euler = dirb.to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(ob)
        LIGHTS.append(ob)
WORKL = []
for nm, R in S.ROOMS.items():
    zc = R['c'] - 0.35 if nm != 'Treppenhaus' else 1.5
    for zz in ([zc] if nm != 'Treppenhaus' else [-1.5, 1.7, 5.0, 8.0]):
        L = bpy.data.lights.new('W_' + nm, 'POINT')
        L.energy = 90.0 * max(1.0, (R['x1'] - R['x0']) * (R['y1'] - R['y0']) / 20.0)
        L.shadow_soft_size = 0.5
        lo = bpy.data.objects.new('W_' + nm, L)
        lo.location = ((R['x0'] + R['x1']) / 2, (R['y0'] + R['y1']) / 2, zz)
        sc.collection.objects.link(lo)
        WORKL.append(lo)

w = bpy.data.worlds.new('W')
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes['Background']
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.2
sun.data.angle = math.radians(2.0)
sun.rotation_euler = (math.radians(50), math.radians(6), math.radians(25))       # from the south-south-east
sc.collection.objects.link(sun)
gme = bpy.data.meshes.new('Ground')
gme.from_pydata([(-60, -60, S.GROUND - 0.01), (60, -60, S.GROUND - 0.01), (60, 60, S.GROUND - 0.01),
                 (-60, 60, S.GROUND - 0.01)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new('Ground', gme)
gm = bpy.data.materials.new('M_ground')
gm.use_nodes = True
next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.20, 0.19, 0.16, 1)
gme.materials.append(gm)
sc.collection.objects.link(gob)

VIEWS = {
    'axo_se': dict(eye=(22, -24, 18), tgt=(-4, 0, 2), lens=30, day=True),
    'axo_nw': dict(eye=(-30, 22, 18), tgt=(-4, 0, 2), lens=30, day=True),
    'ext_entrance': dict(eye=(-1.0, -13.0, 2.2), tgt=(-5.5, -6.5, 1.0), lens=24, day=True),
    'ext_south': dict(eye=(0.0, -24.0, 2.0), tgt=(0.0, 0.0, 3.0), lens=30, day=True),
    'ext_east': dict(eye=(20.0, 2.0, 2.0), tgt=(0.0, 0.0, 3.0), lens=30, day=True),
    'ext_roof': dict(eye=(12.0, -12.0, 14.0), tgt=(0.0, 0.0, 7.0), lens=24, day=True),
    'ext_garage': dict(eye=(-20.0, -12.0, 3.0), tgt=(-13.0, -5.0, 1.2), lens=24, day=True),
    'ext_wall': dict(eye=(3.0, -8.2, 1.6), tgt=(5.0, -6.0, 1.6), lens=28, day=True),
    'in_windfang': dict(eye=(-5.5, -1.6, 1.7), tgt=(-7.2, -5.2, 1.0), lens=18),
    'in_windfang2': dict(eye=(-6.4, -2.2, 1.6), tgt=(-6.4, -6.0, 1.2), lens=18),
    'in_leitstand': dict(eye=(-4.6, -3.0, 1.6), tgt=(7.0, -4.0, 1.2), lens=18),
    'in_leitstand2': dict(eye=(6.8, -2.0, 1.7), tgt=(-4.0, -3.6, 0.9), lens=18),
    'in_leitstand_kpp': dict(eye=(2.75, -3.05, 1.55), tgt=(2.95, -1.45, 1.0), lens=22),         # 1.2: the KPP gate station
    'in_flur_eg': dict(eye=(-7.2, 0.0, 1.6), tgt=(7.0, 0.0, 1.2), lens=20),
    'in_lager': dict(eye=(-2.62, 1.40, 1.7), tgt=(-7.0, 5.0, 1.0), lens=18),          # (in front of the shelving)
    'in_server': dict(eye=(7.2, 1.5, 1.7), tgt=(3.0, 5.0, 1.0), lens=18),
    'in_garage': dict(eye=(-8.6, 4.0, 1.7), tgt=(-17.0, -4.0, 1.0), lens=18),
    'in_garage2': dict(eye=(-17.2, -4.2, 1.8), tgt=(-9.0, 4.0, 0.8), lens=18),
    'in_tower': dict(eye=(1.3, 1.5, 1.6), tgt=(-1.0, 6.5, 3.0), lens=16),
    'in_kaserne': dict(eye=(-2.3, -1.6, 5.1), tgt=(-7.4, -4.6, 4.0), lens=18),
    'in_kueche': dict(eye=(-1.0, -1.6, 5.0), tgt=(7.0, -5.0, 4.6), lens=18),
    'in_kueche3': dict(eye=(3.0, -2.0, 5.0), tgt=(-1.4, -4.4, 3.9), lens=18),
    'in_flur_og': dict(eye=(7.2, 0.0, 5.0), tgt=(-7.0, 0.0, 4.6), lens=20),
    'in_waschraum': dict(eye=(-2.3, 1.5, 5.1), tgt=(-7.4, 5.0, 4.0), lens=18),
    'in_stationsleiter': dict(eye=(2.3, 1.5, 5.1), tgt=(7.4, 5.0, 4.0), lens=18),
    'in_heizung': dict(eye=(-1.6, -1.6, -1.3), tgt=(7.0, -4.0, -2.4), lens=18),
    'in_heizung2': dict(eye=(7.3, -5.3, -1.3), tgt=(2.0, -1.4, -2.0), lens=18),
    'in_heatctl': dict(eye=(0.9, -2.45, -1.25), tgt=(0.9, -1.34, -1.40), lens=26, fill=((0.6, -2.2, -0.9), 6.0)),
    'in_burner': dict(eye=(5.7, -3.3, -1.5), tgt=(6.17, -2.4, -2.1), lens=28, fill=((5.6, -3.0, -1.2), 6.0)),
    'in_flur_ug': dict(eye=(7.3, 0.6, -1.3), tgt=(-1.8, -0.4, -1.6), lens=20),
    # the cameras of Update 3's game shots (Previews: Forest_*.jpg, U3/Forest_U3_*.jpg), by eye
    'cmp_base': dict(eye=(30.0, -36.0, 1.7), tgt=(-2.0, 0.0, 3.5), lens=32, exp=0.8, moon=True),
    'night_entrance': dict(eye=(-0.5, -14.0, 1.7), tgt=(-5.5, -6.5, 1.5), lens=26, exp=0.6, moon=True),
    'cmp_control': dict(eye=(-4.9, -1.9, 1.7), tgt=(7.0, -4.6, 1.0), lens=20),
    'cmp_corridor': dict(eye=(-6.8, 0.25, 1.65), tgt=(7.6, -0.1, 1.3), lens=22),
    'cmp_kitchen': dict(eye=(-1.25, -1.4, 5.1), tgt=(7.0, -4.8, 4.3), lens=18),
    'cmp_switch': dict(eye=(4.2, 1.5, -1.35), tgt=(5.0, 5.6, -1.9), lens=18),
    'cmp_doorbar': dict(eye=(-6.45, -2.6, 1.55), tgt=(-6.45, -5.9, 1.1), lens=22),
    'cmp_boiler': dict(eye=(6.1, -4.6, -1.4), tgt=(6.25, -1.6, -2.1), lens=20),
    'cmp_barracks': dict(eye=(-1.9, -1.5, 5.2), tgt=(-7.4, -5.0, 3.9), lens=18),
    'cmp_chief': dict(eye=(2.2, 1.35, 5.1), tgt=(7.4, 5.4, 4.0), lens=18),
    'cmp_wash': dict(eye=(-2.2, 1.4, 5.1), tgt=(-7.4, 5.4, 4.2), lens=18),
    'cmp_storage': dict(eye=(-2.62, 1.30, 1.75), tgt=(-7.4, 5.4, 0.8), lens=18),      # (Update 3's eye: in the shelving)
    'in_schaltraum': dict(eye=(2.3, 1.5, -1.3), tgt=(7.4, 5.0, -2.0), lens=18),
}
DETAIL = {                                             # close-ups for checking (not in 'all')
    'det_door6': dict(eye=(-2.2, 0.55, 1.45), tgt=(-3.45, -1.10, 1.05), lens=30),
    'det_door6b': dict(eye=(-4.4, -2.4, 1.5), tgt=(-3.45, -1.12, 1.1), lens=30),
    'det_board': dict(eye=(6.55, 3.05, -1.55), tgt=(7.42, 3.2, -1.55), lens=30),
    'det_mainsw': dict(eye=(4.35, 4.35, -1.75), tgt=(4.75, 5.3, -1.95), lens=28),
    'det_switch': dict(eye=(0.6, 0.45, 1.15), tgt=(0.82, 1.0, 1.05), lens=40),
}
ALL = list(VIEWS)
VIEWS.update(DETAIL)
P.setup_cycles((1100, 700), int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 24)
sc.cycles.max_bounces = 4
FILL = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'POINT'))
FILL.data.shadow_soft_size = 0.25
sc.collection.objects.link(FILL)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
want = ALL if sys.argv[1] == 'all' else sys.argv[1].split(',')
for v in want:
    c = VIEWS[v]
    cam.location = Vector(c['eye'])
    cam.rotation_euler = (Vector(c['tgt']) - Vector(c['eye'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'PERSP'
    cam.data.lens = c['lens']
    cam.data.clip_start, cam.data.clip_end = 0.03, 400
    day = c.get('day', False)
    bg.inputs[0].default_value = (0.56, 0.62, 0.72, 1) if day else (0.02, 0.025, 0.03, 1)
    bg.inputs[1].default_value = 0.9 if day else 0.2
    sun.hide_render = not (day or c.get('moon'))
    sun.data.energy = 3.2 if day else 0.06
    sun.data.color = (1.0, 0.97, 0.92) if day else (0.62, 0.72, 1.0)
    for o in LIGHTS:
        o.hide_render = day or WORK
    for o in WORKL:
        o.hide_render = day or not WORK
    power(not day)
    for m in bpy.data.materials:                      # the kit's lamp lenses: lit with the power (night_emit)
        if m.name.startswith('M_Kit_Lamp_') and not m.name.endswith('_Off') and m.get('night_emit') and m.use_nodes:
            pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if pb is not None:
                pb.inputs['Emission Strength'].default_value = 0.0 if day else float(m['night_emit'])
    for m in bpy.data.materials:                      # by day the fixtures are dark
        if m.name.startswith(('M_FX_', 'M_LEDOn', 'M_Main_Panel')) and m.use_nodes:
            pb = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if pb is not None:
                if 'em0' not in m:
                    m['em0'] = pb.inputs['Emission Strength'].default_value
                pb.inputs['Emission Strength'].default_value = 0.0 if day else m['em0']
    if c.get('fill'):
        FILL.location = Vector(c['fill'][0])
        FILL.data.energy = c['fill'][1]
        FILL.hide_render = False
    else:
        FILL.hide_render = True
    ims = sc.render.image_settings
    if day:
        ims.file_format, ims.color_depth = 'PNG', '8'
        ims.color_management = 'FOLLOW_SCENE'
        sc.render.filepath = os.path.join(OUT, v + '.png')
        bpy.ops.render.render(write_still=True)
    else:
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format, ims.color_depth = 'OPEN_EXR', '32'
        ims.color_management = 'OVERRIDE'
        ims.linear_colorspace_settings.name = 'Linear Rec.709'
        exr = os.path.join(OUT, v + '.exr')
        sc.render.filepath = exr
        bpy.ops.render.render(write_still=True)
        subprocess.run([sys.executable, '-I', os.path.join(P.HERE, 'post_bloom.py'), exr, os.path.join(OUT, v + '.png'),
                        '0.25', str(c.get('exp', 0.0 if c.get('moon') else 0.9))], check=True)
        os.remove(exr)
    print('view', v, f'{time.time() - T0:.1f}s', flush=True)
