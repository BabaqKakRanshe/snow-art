"""forest_trash: build the 6 piles and 6 clumps (trash_kit), bake one PSX atlas (trash_paint), write the contract.
python3 -I trash_build.py [--draft] -> out/trash.blend, trash.json, trash_contract.json, tex/trash/
In the .blend: the piles in a row (y = 0), each clump 2 m in front of its pile, standing on the ground (display_offset)."""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import trash_kit as TK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'trash')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
PB.POS_SCALE = 24.0
MASS = dict(Paper=3.0, Plastic=2.5, Metal=9.0, Wood=6.0, Glass=7.0, Mixed=5.0)
NOTE = dict(Paper='газеты, картон, стаканчики, скомканная бумага', Plastic='ПЭТ-бутылки, пакеты, лоток, стаканчик, канистра',
            Metal='банки целые и смятые, гнутый лист, обрезок трубы, проволока', Wood='доски с гвоздями, планки, ветки, обрубок',
            Glass='бутылки зелёные, коричневые, прозрачные, банка, осколки', Mixed='бытовой: мешок, банка, бутылка, коробка, бумага')


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def U(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
parts, info = TK.build_trash()
colls = {s: bpy.data.collections.new(t) for s, t in (('ground', 'Piles'), ('held', 'Clumps'))}
for c in colls.values():
    bpy.context.scene.collection.children.link(c)
objs, DISPLAY, stats = {}, {}, {}
for i, kind in enumerate(TK.KINDS):
    for state, name in (('ground', f'TrashPile_{kind}'), ('held', f'TrashClump_{kind}')):
        k = parts[name]
        bmesh.ops.remove_doubles(k.bm, verts=list(k.bm.verts), dist=1e-5)
        o = k.to_object(name, coll=colls[state])
        me = o.data
        co = np.array([v.co[:] for v in me.vertices])
        lo, hi = co.min(0), co.max(0)
        if state == 'ground':
            off = Vector((i * 1.7, 0.0, 0.0))
        else:
            off = Vector((i * 1.7, -2.0, -lo[2]))
        o.location = off
        DISPLAY[name] = [round(off.x, 3), round(off.y, 3), round(off.z, 3)]
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        stats[name] = dict(kind=kind, state=state, tris=tris, min=lo.round(4).tolist(), max=hi.round(4).tolist(),
                           area=round(sum(p.area for p in me.polygons), 3))
        objs[name] = o
        log(name, tris, 'tris', 'size', (hi - lo).round(3).tolist(), 'area', stats[name]['area'])
bpy.context.view_layer.update()
log('area piles', round(sum(s['area'] for s in stats.values() if s['state'] == 'ground'), 2), 'clumps',
    round(sum(s['area'] for s in stats.values() if s['state'] == 'held'), 2))
import trash_paint as TP
if DRAFT:
    cache = {}
    for o in objs.values():
        me = o.data
        zl = [int(round(a.value)) for a in me.attributes['zone'].data]
        me.materials.clear()
        idx = {}
        for z in sorted(set(zl)):
            zz = z - TK.CLUMP_DZ if z >= 400 else z
            if zz not in cache:
                m = bpy.data.materials.new(f'draft_{zz}')
                col = PB.lin(*TP.DRAFT_COL.get(zz, (128, 128, 128)))
                m.diffuse_color = (float(col[0]), float(col[1]), float(col[2]), 1)
                cache[zz] = m
            idx[z] = len(me.materials)
            me.materials.append(cache[zz])
        for p, z in zip(me.polygons, zl):
            p.material_index = idx[z]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'trash_draft.blend'))
    log('draft saved')
    sys.exit(0)
INFO = {}
clump_zones = {z + TK.CLUMP_DZ: 2.0 for z in list(range(300, 328)) + list(TK.Z_MOUND.values()) + list(TK.Z_BALE.values())}
PB.make_atlas('Trash', list(objs.values()), TP.painter, TEX, prefix='T_Trash_', mat_prefix='M_Trash_', size=512, ao_min=0.35,
              ao_dist=0.12, rough=0.8, log=log, info=INFO, ppm_cap=64.0, zone_scale=clump_zones,
              prio_zones=(TK.Z_PET_CAP, TK.Z_CANISTER, TK.Z_GL_G, TK.Z_BAG_B, TK.Z_PET_CAP + TK.CLUMP_DZ))
# ------------------------------------------------------------------ contract
C = {'kinds': {}, 'meta': {}}
for kind in TK.KINDS:
    e = {}
    for state, name in (('ground', f'TrashPile_{kind}'), ('held', f'TrashClump_{kind}')):
        s = stats[name]
        lo, hi = np.array(s['min']), np.array(s['max'])
        if state == 'ground':
            bc, bs = (lo + hi) / 2, hi - lo
            bc[2], bs[2] = (hi[2] + 0.0) / 2, hi[2]
            col = dict(type='Box', center=U(bc), size=[round(float(bs[0]), 4), round(float(bs[2]), 4), round(float(bs[1]), 4)])
            e['pile'] = dict(model=name, tris=s['tris'], sizeUnity=[round(float(hi[0] - lo[0]), 3), round(float(hi[2]), 3),
                                                                   round(float(hi[1] - lo[1]), 3)],
                             origin='на земле, посередине кучи', collider=col, display_offset=DISPLAY[name])
        else:
            sx, sy, sz = TK.BALE[kind]
            col = dict(type='Box', center=[0.0, 0.0, 0.0], size=[sx * 0.92, sz * 0.92, sy * 0.92])
            e['clump'] = dict(model=name, tris=s['tris'], sizeUnity=[round(float(hi[0] - lo[0]), 3), round(float(hi[2] - lo[2]), 3),
                                                                    round(float(hi[1] - lo[1]), 3)],
                              baleUnity=[sx, sz, sy], origin='середина кома (точка хвата)', collider=col,
                              sockets={'Hand_Grip': [0.0, 0.0, 0.0]}, lowestPointUnity=round(float(lo[2]), 4),
                              display_offset=DISPLAY[name])
    e['massKg'] = MASS[kind]
    e['note'] = NOTE[kind]
    C['kinds'][kind] = e
C['meta'] = dict(
    version='1.0', units='metres',
    frame='each model in its own frame: z up, front -y. The pile: origin on the ground at its middle; the clump: origin at the '
          'middle of the bale (the grip). In trash.blend the piles stand in a row and each clump 2 m in front of its pile, on '
          'the ground (display_offset)',
    unity='(x, y, z) -> Unity (-x, z, -y); the front (-y) is the prefab\'s +Z',
    states='ground: TrashPile_<Kind> lies on the ground; picked up -> the pile is hidden / removed and TrashClump_<Kind> is in the '
           'hands (Hand_Grip at the hand); put down / dropped -> the clump goes and the pile is placed where it lands (origin on '
           'the ground, any yaw)',
    colliders='BoxCollider per model: the pile - its bounds (low box over the heap), the clump - the bale',
    materials='M_Trash_Trash: one baked PSX atlas, point filter (the piles ~64 px/m, the clumps in the hands twice that)',
    textures='tex', model='trash.blend')
json.dump(C, open(os.path.join(OUT, 'trash_contract.json'), 'w'), indent=1, ensure_ascii=False)
tris = {n: s['tris'] for n, s in stats.items()}
json.dump(dict(atlases=INFO, tris=tris, tris_total=sum(tris.values()), display_offset=DISPLAY),
          open(os.path.join(OUT, 'trash.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'trash.blend'))
log('saved trash.blend; tris', sum(tris.values()))
