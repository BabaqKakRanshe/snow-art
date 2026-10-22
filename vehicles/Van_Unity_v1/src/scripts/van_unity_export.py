"""Van v3 -> Unity: Models/Van.fbx, the whole van as one hierarchy in Unity axes, for the Unity package Van_Unity_v1.

out/van3.blend is in the body frame (x forward, y left, z up, ground z = 0). The FBX convention of every Unity model of the
project (Blender exporter: axis_forward -Z, axis_up Y, Apply Transform, the nested-object fix of the plane's export) turns
a Blender point (X, Y, Z) into Unity (-X, Z, -Y). The van is turned by -90 deg about z first (body (x, y, z) -> Blender
(y, -x, z)), so a body point lands in Unity at (-y, z, x): the frame of VAN3_CONTRACT.md (forward +Z, up +Y, right +X).

What changes on the way (nothing is moved or re-shaped):
 - every object keeps its origin = its pivot (hinge, axle, thread, rail) and gets an identity local rotation and scale:
   SpareWheel / SpareWheel_Nut had a rotation (and the nut a 1.7 scale) - baked into their meshes;
 - the glass panes become child objects of the part they sit in (Glass_L1 ... Glass_ZP, Glass_doorL, Glass_Window_doorL;
   the windscreen lob already is one): one renderer per pane, so a pane can fog, frost, take a hand print or break alone;
 - COL_* (box colliders: Data/colliders.json) and LIGHT_* (lamp sockets: Data/lights.json) stay out;
 - unused material slots are dropped (one submesh per material), meshes are triangulated (BEAUTY; custom normals kept;
   the meshes with blend shapes - Wheel_* Flat, Snow_Roof / Snow_Visor / Snow_Bumper Clear - are triangulated in place so
   the FBX keeps their shapes), UV0 = PSX atlas, UV1 = FOG (glass panes, 0..1 per pane) or RT (Radio_Display).

python3 -I van_unity_export.py -- <out_dir>      -> <out_dir>/Models/Van.fbx, <out_dir>/van_export_report.json"""
import bpy, bmesh, os, sys, json, math
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'out', 'van3.blend')
GLASS = ('M_PSX_Glass_Cab', 'M_PSX_Glass_Room')
# pane names by the part they sit in and where they are (body frame x of the pane centre, side)
PANE_NAMES = {
    'Kuzov': [(-1.095, 1, 'Glass_L1'), (-0.131, 1, 'Glass_L2'), (0.605, 1, 'Glass_L3'),
              (-1.095, -1, 'Glass_R1'), (0.605, -1, 'Glass_R3')],
    'doorSalon': [(None, -1, 'Glass_R2')],
    'doorZL': [(None, 1, 'Glass_ZL')],
    'dooZP': [(None, -1, 'Glass_ZP')],
    'doorL': [(None, 1, 'Glass_doorL')],
    'doorP': [(None, -1, 'Glass_doorP')],
    'Window_doorL': [(None, 1, 'Glass_Window_doorL')],
    'Window_doorP': [(None, -1, 'Glass_Window_doorP')],
}
R_BODY = Matrix.Rotation(-math.pi / 2, 4, 'Z')        # body (x, y, z) -> Blender (y, -x, z)


def to_unity(p):
    return [round(-p[1], 5) + 0.0, round(p[2], 5) + 0.0, round(p[0], 5) + 0.0]


def depth(o):
    return 0 if o.parent is None else 1 + depth(o.parent)


def main(out_dir):
    os.makedirs(os.path.join(out_dir, 'Models'), exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=SRC)
    vl = bpy.context.view_layer
    for c in bpy.data.collections:
        c.hide_viewport = False
        c.hide_render = False
    for lc in vl.layer_collection.children:
        lc.exclude = False
        lc.hide_viewport = False
    O = bpy.data.objects
    for o in O:
        o.hide_set(False)
        o.hide_viewport = False
        o.hide_render = False
    log = []

    # 0. blend shapes at 0 (the FBX writes the key value as the default weight: full tyre, full snow cover)
    for me in bpy.data.meshes:
        if me.shape_keys:
            vals = {k.name: round(k.value, 3) for k in me.shape_keys.key_blocks[1:]}
            for k in me.shape_keys.key_blocks[1:]:
                k.value = 0.0
            log.append(f'{me.name}: blend shape weights {vals} -> 0 (Unity default weight 0)')

    # 1. colliders and lamp sockets are data, not geometry
    drop = [o for o in O if o.name.startswith(('COL_', 'LIGHT_'))]
    for o in drop:
        assert not o.children, o.name
    for o in drop:
        bpy.data.objects.remove(o, do_unlink=True)
    log.append(f'left out {len(drop)} COL_ / LIGHT_ objects')

    # 2. one mesh per object, named like it
    for o in O:
        if o.type == 'MESH':
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.name = o.name

    # 3. parent inverse -> identity, world kept: the local transform is the plain transform relative to the parent
    for o in sorted(O, key=depth):
        if o.parent is not None:
            mw = o.matrix_world.copy()
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = o.parent.matrix_world.inverted() @ mw
    vl.update()

    # 4. rotations / scales into the meshes (only leaf objects have them)
    for o in O:
        loc, rot, sca = o.matrix_basis.decompose()
        if rot.angle > 1e-6 or (sca - Vector((1, 1, 1))).length > 1e-6:
            assert o.type == 'MESH' and not o.children, o.name
            M = rot.to_matrix().to_4x4() @ Matrix.Diagonal(sca.to_4d())
            o.data.transform(M, shape_keys=True)
            o.matrix_basis = Matrix.Translation(loc)
            log.append(f'{o.name}: rotation {[round(math.degrees(a), 2) for a in rot.to_euler()]} scale '
                       f'{[round(s, 3) for s in sca]} baked into the mesh')
    vl.update()
    for o in O:
        loc, rot, sca = o.matrix_basis.decompose()
        assert rot.angle < 1e-6 and (sca - Vector((1, 1, 1))).length < 1e-6, o.name

    # 5. glass panes -> child objects
    panes = []
    for host, names in PANE_NAMES.items():
        o = O[host]
        me = o.data
        gidx = {i for i, m in enumerate(me.materials) if m and m.name in GLASS}
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        faces = [f for f in bm.faces if f.material_index in gidx]
        seen, comps = set(), []
        for f in faces:
            if f.index in seen:
                continue
            stack, comp = [f], []
            seen.add(f.index)
            while stack:
                g = stack.pop()
                comp.append(g.index)
                for v in g.verts:
                    for h in v.link_faces:
                        if h.material_index in gidx and h.index not in seen:
                            seen.add(h.index)
                            stack.append(h)
            comps.append(comp)
        mw = o.matrix_world
        cents = [sum((mw @ bm.faces[i].calc_center_median() for i in c), Vector()) / len(c) for c in comps]
        bm.free()
        assert len(comps) == len(names), (host, len(comps))
        used = set()
        for (xc, side, pname) in names:
            best = min((k for k in range(len(comps)) if k not in used and (cents[k].y > 0) == (side > 0)),
                       key=lambda k: abs(cents[k].x - xc) if xc is not None else 0)
            used.add(best)
            keep = set(comps[best])
            # new object: a copy of the host with every face but the pane's removed
            nme = me.copy()
            nme.name = pname
            if nme.shape_keys:
                raise RuntimeError(pname)
            b2 = bmesh.new()
            b2.from_mesh(nme)
            b2.faces.ensure_lookup_table()
            bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context='FACES')
            bmesh.ops.delete(b2, geom=[v for v in b2.verts if not v.link_faces], context='VERTS')
            b2.to_mesh(nme)
            b2.free()
            no = bpy.data.objects.new(pname, nme)
            for col in o.users_collection:
                col.objects.link(no)
            no.parent = o
            no.matrix_parent_inverse = Matrix.Identity(4)
            no.matrix_basis = Matrix.Identity(4)
            panes.append(dict(name=pname, host=host, centre_body=[round(c, 4) for c in cents[best]],
                              faces=len(keep)))
        # host: the panes' faces go away (they are islands: no other face shares their vertices)
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        allg = {i for c in comps for i in c}
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in allg], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me)
        bm.free()
    log.append(f'{len(panes)} glass panes split off: ' + ', '.join(p['name'] for p in panes))
    # the windscreen: its masks run on its PSX UVs (0..1 over the pane); a copy as UV1 'FOG' makes every pane read its
    # masks from UV1
    lme = O['lob'].data
    assert len(lme.uv_layers) == 1
    src = lme.uv_layers[0].name
    fog = lme.uv_layers.new(name='FOG')
    for d, s in zip(fog.data, lme.uv_layers[src].data):
        d.uv = s.uv
    log.append('lob: UV1 FOG = copy of its PSX UVs (masks on UV1 for every pane)')
    pane_names = {p['name'] for p in panes} | {'lob'}
    for o in O:                                   # the hosts keep no glass: their FOG layer goes
        if o.type == 'MESH' and o.name not in pane_names and 'FOG' in o.data.uv_layers:
            o.data.uv_layers.remove(o.data.uv_layers['FOG'])
            log.append(f'{o.name}: FOG UV layer removed (its panes are separate objects now)')
    # each pane: affine map from its local position (Unity axes, metres from the pane's origin) to its mask UVs (UV1),
    # for placing a hand print where a ray hits the glass (the FBX meshes are not readable at run time)
    import numpy as np
    pane_fit = {}
    for pn in sorted(pane_names):
        me = O[pn].data
        uvd = me.uv_layers['FOG'].data
        rows, uvs = [], []
        for li, lp in enumerate(me.loops):
            c = me.vertices[lp.vertex_index].co                    # object local, body axes (rotation is identity)
            rows.append([-c.y, c.z, c.x, 1.0])                     # Unity axes
            uvs.append([uvd[li].uv[0], uvd[li].uv[1]])
        A, Y = np.array(rows), np.array(uvs)
        sol, *_ = np.linalg.lstsq(A, Y, rcond=None)
        err = float(np.abs(A @ sol - Y).max())
        pane_fit[pn] = dict(u=[round(float(x), 6) for x in sol[:, 0]], v=[round(float(x), 6) for x in sol[:, 1]],
                            max_err=round(err, 4))
    for p in panes:
        p['uv_affine'] = pane_fit[p['name']]
    log.append('pane uv fits (max error, uv): ' + ', '.join(f'{k} {v["max_err"]}' for k, v in sorted(pane_fit.items())))
    # the radio display: its RT UVs (0..1 over the glass) become its only UVs, and it gets a material of its own
    rd = O['Radio_Display'].data
    rt = rd.uv_layers['RT']
    psx = rd.uv_layers[0]
    for d, s in zip(psx.data, rt.data):
        d.uv = s.uv
    rd.uv_layers.remove(rd.uv_layers['RT'])
    rmat = bpy.data.materials.new('M_Van_RadioDisplay')
    rd.materials[0] = rmat
    log.append('Radio_Display: UV0 = its RT UVs (0..1 over the glass), material M_Van_RadioDisplay (the rig draws the channel)')
    vl.update()

    # 6. unused material slots out (one submesh per used material)
    for o in O:
        if o.type != 'MESH' or not o.data.materials:
            continue
        me = o.data
        used = sorted(set(p.material_index for p in me.polygons))
        keep = [me.materials[i] for i in used]
        idx = [used.index(p.material_index) for p in me.polygons]
        me.materials.clear()
        for m in keep:
            me.materials.append(m)
        for p, i in zip(me.polygons, idx):
            p.material_index = i
        assert all(m is not None for m in me.materials), o.name

    # 7. body frame -> Blender frame of the Unity convention: every origin and every mesh turned about z by -90 deg
    for o in O:
        t = o.matrix_basis.to_translation()
        o.matrix_basis = Matrix.Translation(R_BODY @ t)
        if o.type == 'MESH':
            o.data.transform(R_BODY, shape_keys=True)
            o.data.update()
    vl.update()

    # 8. triangulate: blend-shape meshes in place (bmesh keeps the shape layers), the rest by modifier (custom normals)
    shapes = {}
    for o in O:
        if o.type != 'MESH':
            continue
        me = o.data
        if me.shape_keys and len(me.shape_keys.key_blocks) > 1:
            assert not me.has_custom_normals, o.name
            n0 = len(me.shape_keys.key_blocks)
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
            bm.to_mesh(me)
            bm.free()
            assert len(me.shape_keys.key_blocks) == n0, o.name
            shapes[o.name] = [k.name for k in me.shape_keys.key_blocks[1:]]
        elif not any(m.type == 'TRIANGULATE' for m in o.modifiers):
            m = o.modifiers.new('tri', 'TRIANGULATE')
            m.quad_method = m.ngon_method = 'BEAUTY'
            m.keep_custom_normals = True
        if me.uv_layers:
            me.uv_layers.active_index = 0
            me.uv_layers[0].active_render = True
        for k in list(o.keys()):
            del o[k]

    # 9. export (the plane's nested-object fix: child local = G L G^-1 for any depth)
    import addon_utils
    addon_utils.enable('io_scene_fbx')
    from io_scene_fbx import fbx_utils
    orig = fbx_utils.ObjectWrapper.fbx_object_matrix

    def patched(self, scene_data, rest=False, local_space=False, global_space=False):
        par = self.parent
        if (not local_space and not global_space and par is not None and self._tag == 'OB' and par._tag == 'OB'
                and not self.parented_to_armature and self.use_bake_space_transform(scene_data)
                and par.use_bake_space_transform(scene_data)):
            L = self.matrix_rest_local if rest else self.matrix_local
            return scene_data.settings.global_matrix @ L @ scene_data.settings.global_matrix_inv
        return orig(self, scene_data, rest, local_space, global_space)

    fbx_utils.ObjectWrapper.fbx_object_matrix = patched
    bpy.ops.object.select_all(action='DESELECT')
    objs = [o for o in O if o.type in ('MESH', 'EMPTY')]
    for o in objs:
        o.select_set(True)
    fp = os.path.join(out_dir, 'Models', 'Van.fbx')
    bpy.ops.export_scene.fbx(
        filepath=fp, use_selection=True, object_types={'EMPTY', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='-Z', axis_up='Y', bake_space_transform=True,
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_subsurf=False, use_mesh_edges=False, use_tspace=False,
        use_triangles=False, use_custom_props=False, colors_type='NONE', add_leaf_bones=False, bake_anim=False,
        path_mode='STRIP', embed_textures=False, batch_mode='OFF')
    fbx_utils.ObjectWrapper.fbx_object_matrix = orig

    # 10. report (body frame and Unity frame of every node)
    dg = bpy.context.evaluated_depsgraph_get()
    rinv = R_BODY.inverted()
    nodes = []
    for o in sorted(objs, key=lambda o: (depth(o), o.name)):
        org_b = rinv @ o.matrix_world.translation                  # back to the body frame
        e = dict(name=o.name, type=o.type, parent=o.parent.name if o.parent else '', depth=depth(o),
                 origin_body=[round(c, 5) + 0.0 for c in org_b], origin_unity=to_unity(org_b))
        if o.type == 'MESH':
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            vs = [rinv @ (o.matrix_world @ v.co) for v in me.vertices]
            lo = [min(v[i] for v in vs) for i in range(3)]
            hi = [max(v[i] for v in vs) for i in range(3)]
            e.update(tris=len(me.polygons), verts=len(me.vertices),
                     bounds_body=[[round(c, 4) for c in lo], [round(c, 4) for c in hi]],
                     materials=[m.name for m in o.data.materials],
                     uv=[u.name for u in o.data.uv_layers], blendshapes=shapes.get(o.name, []))
            ev.to_mesh_clear()
        nodes.append(e)
    rep = dict(file='Models/Van.fbx', bytes=os.path.getsize(fp), nodes=nodes, panes=panes, log=log, lob_fit=pane_fit['lob'],
               tris=sum(n.get('tris', 0) for n in nodes), meshes=sum(1 for n in nodes if n['type'] == 'MESH'),
               empties=[n['name'] for n in nodes if n['type'] == 'EMPTY'])
    json.dump(rep, open(os.path.join(out_dir, 'van_export_report.json'), 'w'), indent=1)
    print('[van] exported', fp, rep['bytes'], 'bytes,', rep['meshes'], 'meshes,', rep['tris'], 'tris,', len(panes), 'panes')
    for l in log:
        print('[van]', l)


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    main(a[0])
