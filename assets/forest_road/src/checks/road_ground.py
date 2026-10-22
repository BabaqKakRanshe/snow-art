"""Sample Update 3's terrain (Forest_Terrain.fbx: the terrain tiles + Forest_Road) round the road prefabs, in each prefab's
own frame (the Blender import frame of its FBX: Unity local = (-x, z, -y)), along the prefab's local -z: ground height and
surface (terrain / road / trail). Output: /home/claude/uaz/road_ground.json (the build reads it; the terrain itself is not
part of the project).  python3 -I road_ground.py"""
import bpy, json, math
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree
SCR = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/'
L = json.load(open(SCR + 'u3/Assets/Locations/Forest/Data/Forest_Layout.json'))
bpy.ops.wm.open_mainfile(filepath=SCR + 'trail2/terrain.blend')
dg = bpy.context.evaluated_depsgraph_get()
trees = []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name == 'Forest_Marker':
        continue
    me = o.evaluated_get(dg).to_mesh()
    V = [o.matrix_world @ v.co for v in me.vertices]
    Pl = [list(p.vertices) for p in me.polygons]
    M = [o.data.materials[p.material_index].name.split('.')[0] if o.data.materials else '' for p in me.polygons]
    trees.append((o.name, BVHTree.FromPolygons(V, Pl), M))
    o.evaluated_get(dg).to_mesh_clear()


def W(p):                       # Unity world -> Blender world
    return Vector((-p[0], -p[2], p[1]))


def frame(p, q):
    """local (Blender import frame) -> Blender world matrix"""
    qu = Quaternion((q[3], q[0], q[1], q[2]))
    # local x, y, z axes -> unity local (-x, z, -y) -> unity world (rotate) -> blender world (-X, -Z, Y)
    def bw(u):
        return Vector((-u.x, -u.z, u.y))
    ex = bw(qu @ Vector((-1, 0, 0)))
    ey = bw(qu @ Vector((0, 0, -1)))
    ez = bw(qu @ Vector((0, 1, 0)))
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = ex[i], ey[i], ez[i]
    m.translation = W(p)
    return m


def cast(Mw, x, y, top=40.0):
    """ground along the local z line through (x, y): local z of the hit and the surface (the highest hit)"""
    o = Mw @ Vector((x, y, top))
    d = (Mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    best = None
    for n, t, Ms in trees:
        h = t.ray_cast(o, d, 200.0)
        if h[0] is not None and (best is None or h[3] < best[1]):
            best = (h[0], h[3], Ms[h[2]], n)
    if best is None:
        return None, None
    loc = Mw.inverted() @ best[0]
    surf = 'road' if best[2] in ('M_RoadDirt',) else 'trail' if best[2] == 'M_TrailSoil' else 'asphalt' if best[2] == 'M_Asphalt' else 'terrain'
    return round(loc.z, 4), surf


def grid(Mw, x0, x1, y0, y1, step):
    nx, ny = int(round((x1 - x0) / step)) + 1, int(round((y1 - y0) / step)) + 1
    zs, ss = [], []
    for j in range(ny):
        rz, rs = [], []
        for i in range(nx):
            z, s = cast(Mw, x0 + i * step, y0 + j * step)
            rz.append(z)
            rs.append({'road': 'R', 'trail': 'T', 'terrain': 'G', 'asphalt': 'A'}.get(s, '-'))
        zs.append(rz)
        ss.append(''.join(rs))
    return dict(x0=x0, y0=y0, step=step, nx=nx, ny=ny, z=zs, surf=ss)


OUT = {'_doc': 'ground under the road prefabs from Update 3\'s Forest_Terrain.fbx (tiles + Forest_Road), in each prefab\'s '
               'own frame: grid z[j][i] at (x0 + i*step, y0 + j*step) = the local z where the local z line meets the ground; '
               'surf: R road (M_RoadDirt), T trail (M_TrailSoil), G terrain, A asphalt',
       'prefabs': {}, 'europosts': []}
GRIDS = {'ZoneGate': (-6.0, 6.0, -3.0, 3.0, 0.25), 'Bridge30': (-22.0, 22.0, -4.0, 4.0, 0.25),
         'OverlookDeck': (-4.0, 4.0, -3.0, 6.0, 0.25), 'FallenTree': (-30.0, 30.0, -12.0, 12.0, 0.25),
         'LogCut': (-8.0, 8.0, -5.0, 5.0, 0.25)}
for p in L['prefabs']:
    m = p['m']
    if not (m in GRIDS or m.startswith('Sign_') or m.startswith('Dist_')):
        continue
    Mw = frame(p['p'], p['q'])
    rec = dict(p=p['p'], q=p['q'], world=[list(r) for r in Mw])
    if m in GRIDS:
        rec['grid'] = grid(Mw, *GRIDS[m])
    else:
        rec['grid'] = grid(Mw, -1.6, 1.6, -0.6, 0.6, 0.1)
    rec['at_pivot'] = cast(Mw, 0.0, 0.0)
    OUT['prefabs'][m] = rec
    print(m, 'pivot ground', rec['at_pivot'], flush=True)
for r in L['rocks']:
    if r['m'] != 'EuroPost':
        continue
    Mw = frame(r['p'], r['q'])
    smp = {}
    for dx, dy in ((0, 0), (-0.08, 0), (0.08, 0), (0, -0.08), (0, 0.08)):
        smp[f'{dx},{dy}'] = cast(Mw, dx, dy)[0]
    OUT['europosts'].append(dict(p=r['p'], q=r['q'], ground=smp))
json.dump(OUT, open('/home/claude/uaz/road_ground.json', 'w'))
print('europosts', len(OUT['europosts']), 'min/max ground at pivots', min(e['ground']['0,0'] for e in OUT['europosts']),
      max(e['ground']['0,0'] for e in OUT['europosts']))
