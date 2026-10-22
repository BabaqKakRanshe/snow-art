"""Ready-made UAZ-452 -> PSX like the Utility Plane.
python3 -I uaz_build.py <config.json>
config: {"src": <import blend from inspect_model.py>, "tag": "uaz", "rot_z": 0, "length": 4.36,
         "delete": [object name substrings], "glass": [material name substrings],
         "saloon_x_max": <x below which glass belongs to the saloon (glows at night)>,
         "emit": {material substring: night strength}, "ppm": 50, "details_size": 512}"""
import sys, os, json
sys.path.insert(0, '/home/claude/uaz')
import bpy
import psxlib as P

cfg = json.load(open(sys.argv[1]))
tag = cfg.get('tag', 'uaz')
TEX = os.path.join(P.HERE, 'tex', tag)
log_rows = []


def log(*a):
    print(*a, flush=True)
    log_rows.append(' '.join(str(x) for x in a))


bpy.ops.wm.open_mainfile(filepath=cfg['src'])
for o in list(bpy.data.objects):
    if any(k.lower() in o.name.lower() for k in cfg.get('delete', [])):
        bpy.data.objects.remove(o, do_unlink=True)
s = P.normalise(list(bpy.data.objects), rot_z_deg=cfg.get('rot_z', 0), length=cfg.get('length'))
log('scale', round(s, 5))
objs = P.split_by_material([o for o in bpy.data.objects if o.type == 'MESH'])
lo, hi = P.world_bbox(objs)
log('bbox', lo.round(3).tolist(), hi.round(3).tolist())


def is_glass(m):
    if m is None:
        return False
    n = m.name.lower()
    if any(k.lower() in n for k in cfg.get('glass', ['glass', 'стекл', 'window'])):
        return True
    pb = next((x for x in m.node_tree.nodes if x.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
    return bool(pb and (pb.inputs['Alpha'].default_value < 0.6 and not pb.inputs['Alpha'].is_linked))


g_cab = P.psx_glass('M_PSX_Glass_Cab', glow=0.0)
g_room = P.psx_glass('M_PSX_Glass_Room', glow=0.0)
g_room['glow'] = cfg.get('room_glow', 0.35)
g_cab['glow'] = 0.06
flat, done = [], set()
fbm = P.faces_by_material(objs)
for m, faces in fbm.items():
    users = [o for o in objs if P.main_material(o) == m]
    if is_glass(m):
        for o in users:                                     # cab glass vs saloon glass by position
            cxo = sum((o.matrix_world @ v.co).x for v in o.data.vertices) / max(len(o.data.vertices), 1)
            o.data.materials.clear()
            o.data.materials.append(g_room if cxo < cfg.get('saloon_x_max', 0.6) else g_cab)
        continue
    if m is not None and m.use_nodes and P.find_tex(m, 'Base Color') is not None:
        info = P.psx_from_source(m, faces, TEX, ppm_target=cfg.get('ppm', 50), bake_objs=users, log=log)
        if info:
            done.add(m.name)
            continue
    flat += users
# flat-coloured parts: one Details atlas (AO + seams baked into a texture, like the plane's Details set)
if flat:
    P.psx_atlas(f'{tag}_Details', flat, TEX, ppm=cfg.get('ppm', 50), size=cfg.get('details_size'), log=log)
for m in bpy.data.materials:
    for k, v in cfg.get('emit', {}).items():
        if k.lower() in m.name.lower():
            m['night_emit'] = v
            pb = next((x for x in m.node_tree.nodes if x.type == 'BSDF_PRINCIPLED'), None)
            if pb:
                pb.inputs['Emission Color'].default_value = tuple(cfg.get('emit_color', (1.0, 0.9, 0.7))) + (1,)
tris = sum(P.tri_count(o) for o in bpy.data.objects if o.type == 'MESH')
log('tris', tris, 'objects', len([o for o in bpy.data.objects if o.type == 'MESH']))
os.makedirs(os.path.join(P.HERE, 'out'), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(P.HERE, 'out', f'{tag}_psx.blend'))
open(os.path.join(P.HERE, 'out', f'{tag}_build.log'), 'w').write('\n'.join(log_rows))
