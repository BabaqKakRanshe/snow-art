"""v10 (as v9; as v8, + survival kit FBX): re-import UtilityPlane.fbx (+ SM_StepLadder.fbx, SM_PlaneKey.fbx) and compare every object's world position /
rotation and parent with the export blend; check the blade feather sense and the thrust sense of the blades.
Output lines for the main FBX keep the v6 format (make_docs.py parses them)."""
import bpy, sys, math
from mathutils import Vector, Quaternion, Matrix
RX90 = Quaternion((1, 0, 0), math.radians(90))
tag = sys.argv[-1]
BLEND = f'/home/claude/plane/out/plane_unity_{tag}.blend'
MOD = '/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Models/'


def snapshot(root_name):
    root = bpy.data.objects[root_name]
    names = [root.name] + [o.name for o in root.children_recursive]
    ref = {n: bpy.data.objects[n].matrix_world.copy() for n in names}
    par = {n: (bpy.data.objects[n].parent.name if bpy.data.objects[n].parent else None) for n in names}
    return names, ref, par


def compare(fbx, names, ref, par, label):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=MOD + fbx)
    O = bpy.data.objects
    missing = [n for n in names if n not in O]
    extra = [o.name for o in O if o.name not in ref]
    errs, rerr, pbad = [], [], []
    for n in names:
        if n not in O:
            continue
        a, b = O[n].matrix_world, ref[n]
        errs.append(((a.translation - b.translation).length, n))
        # the importer leaves the Y-up -> Z-up conversion as a right-multiplied Rx(90): imported = reference @ Rx(90)
        q = (b.to_quaternion().inverted() @ a.to_quaternion()).rotation_difference(RX90)
        rerr.append((abs(q.angle), n))
        p = O[n].parent.name if O[n].parent else None
        if p != par[n]:
            pbad.append((n, p, par[n]))
    errs.sort(reverse=True)
    rerr.sort(reverse=True)
    pre = '' if label == 'main' else f'[{label}] '
    print(pre + 'objects', len(names), 'imported', len(O), 'missing', missing[:10], 'extra', extra[:10])
    print(pre + 'max pos err mm', round(errs[0][0] * 1000, 4), errs[0][1], '| max rot err deg',
          round(rerr[0][0] * 57.2958, 4), rerr[0][1])
    print(pre + 'parent mismatches', len(pbad), pbad[:8])
    print(pre + 'meshes', sum(1 for o in O if o.type == 'MESH'), 'empties', sum(1 for o in O if o.type == 'EMPTY'))
    bad = [(round(e * 57.2958, 3), n) for e, n in rerr if e * 57.2958 > 0.01]
    print(pre + 'rot errors > 0.01 deg:', len(bad))
    for e, n in bad[:40]:
        print(f'  {n:28s} {e:8.3f}')
    return len(missing) == 0 and len(extra) == 0 and not pbad and not bad and errs[0][0] < 1e-4


bpy.ops.wm.open_mainfile(filepath=BLEND)
main = snapshot('UtilityPlane')
NOSHADOW_PREFIXES = ("Needle_", "Knob_", "SW_", "Guard_", "Rheo_", "Pull_", "Btn_", "Lamp_", "Lens_", "Display_", "ATT_",
                     "HDG_", "TC_", "Clock_", "ALT_", "Compass_", "Belt_", "Lock_", "PropBlur", "PropDisc", "Glass")
_rend = [o for o in bpy.data.objects['UtilityPlane'].children_recursive
         if o.type == 'MESH' and len(o.data.polygons) and not o.name.startswith('COL_')]
_nos = [o.name for o in _rend if o.name.startswith(NOSHADOW_PREFIXES) or o.name.endswith(('_Glass', '_Fog'))]
print('renderers', len(_rend), 'noshadow', len(_nos))
# v8: LOD meshes - child of their part, identity local transform, same material set, fewer triangles
import json
_lods = [o for o in _rend if '_LOD' in o.name]
_bad = []
for o in _lods:
    src = o.parent
    ok = src is not None and o.name.rsplit('_LOD', 1)[0] == src.name and \
        (o.matrix_world.translation - src.matrix_world.translation).length < 1e-6 and \
        (o.matrix_world.to_quaternion().rotation_difference(src.matrix_world.to_quaternion())).angle < 1e-6
    ms, mo = {m.name for m in src.data.materials if m}, {m.name for m in o.data.materials if m}
    if not ok or not mo <= ms or len(o.data.polygons) >= len(src.data.polygons):
        _bad.append((o.name, ok, sorted(mo - ms), len(o.data.polygons), len(src.data.polygons)))
print('lod meshes', len(_lods), 'bad', _bad)
# v10: shadow proxies - child of their part, identity local transform, one material from the part, fewer triangles
_sh = [o for o in _rend if o.name.endswith('_Shadow')]
_sbad = []
for o in _sh:
    src = o.parent
    ok = src is not None and o.name[:-7] == src.name and \
        (o.matrix_world.translation - src.matrix_world.translation).length < 1e-6 and \
        (o.matrix_world.to_quaternion().rotation_difference(src.matrix_world.to_quaternion())).angle < 1e-6
    ms, mo = {m.name for m in src.data.materials if m}, {m.name for m in o.data.materials if m}
    if not ok or not mo <= ms or len(mo) != 1 or len(o.data.polygons) >= len(src.data.polygons):
        _sbad.append((o.name, ok, sorted(mo), len(o.data.polygons), len(src.data.polygons)))
print('shadow proxies', len(_sh), 'bad', _sbad)
_lj = json.load(open('/home/claude/plane/export/unity_v10/Assets/UtilityPlane/Data/lod.json'))
_names = {o.name for o in _rend}
for g in _lj['groups']:
    miss = [n for l in g['levels'] for n in l['renderers'] if n not in _names]
    hs = [l['screenRelativeHeight'] for l in g['levels']]
    print('lod group', g['name'], 'levels', len(hs), 'heights', hs, 'decreasing', all(a > b for a, b in zip(hs, hs[1:])),
          'missing renderers', miss[:5])
body = bpy.data.objects['Body']
print('Body materials', [m.name for m in body.data.materials])
lad = snapshot('SM_StepLadder')
key = snapshot('SM_PlaneKey')
SURV = sorted(o.name for o in bpy.data.objects if o.name.startswith('SM_Surv_') and o.parent is None)
surv = {n: snapshot(n) for n in SURV}

# ---- blade sense checks in the export blend (Blender frame: nose -Y, pilot-left +X, up +Z)
FWD = Vector((0, -1, 0))
prop = bpy.data.objects['Propeller']
PC = prop.matrix_world.translation.copy()


def rot_about_axis(p, ang):          # the rig's propeller turn: Unity Euler(0,0,-a) on local Z = Blender R_y(-a) about PC
    R = Matrix.Rotation(-ang, 4, 'Y')
    return (R @ (p - PC).to_4d()).to_3d() + PC


for bn in ('PropBlade_1', 'PropBlade_2', 'PropBlade_3'):
    ob = bpy.data.objects[bn]
    mw = ob.matrix_world.copy()
    vs = [mw @ v.co for v in ob.data.vertices]
    sec = []
    for i, p in enumerate(vs):
        d = p - PC
        r = (d - FWD * d.dot(FWD)).length
        if 0.74 < r < 0.78:
            sec.append(i)
    best = max(((a, b) for a in sec for b in sec if a < b), key=lambda ab: (vs[ab[0]] - vs[ab[1]]).length)
    ia, ib = best
    mid = (vs[ia] + vs[ib]) / 2
    tv = (rot_about_axis(mid, 1e-3) - mid).normalized()
    c = vs[ia] - vs[ib]
    if c.dot(tv) < 0:
        ia, ib, c = ib, ia, -c
    beta0 = math.degrees(math.atan2(c.dot(FWD), c.dot(tv)))
    # rig feather: Unity localRotation = rest * Euler(0, -62, 0) about local Y = Blender +62 deg about local Z (span)
    mf = mw @ Matrix.Rotation(math.radians(62.0), 4, 'Z')
    va, vb = mf @ ob.data.vertices[ia].co, mf @ ob.data.vertices[ib].co
    c1 = va - vb
    beta1 = math.degrees(math.atan2(c1.dot(FWD), c1.dot(tv)))
    span = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
    radial = ((mid - PC) - FWD * (mid - PC).dot(FWD)).normalized()
    print(f'{bn}: chord {c.length:.3f} m at r 0.76, blade angle {beta0:.1f} deg (thrust forward: {beta0 > 0}), '
          f'after feather {beta1:.1f} deg, span axis . radial {span.dot(radial):.4f}')

ok_main = compare('UtilityPlane.fbx', *main, 'main')
ok_lad = compare('SM_StepLadder.fbx', *lad, 'ladder')
ok_key = compare('SM_PlaneKey.fbx', *key, 'key')
ok_surv = all(compare(n + '.fbx', *surv[n], n[8:]) for n in SURV)
print('survival models', len(SURV))
print('VERIFY', 'OK' if (ok_main and ok_lad and ok_key and ok_surv) else 'FAIL', ok_main, ok_lad, ok_key, ok_surv)
