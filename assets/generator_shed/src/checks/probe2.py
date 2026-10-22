import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
def bvh(n):
    o = bpy.data.objects[n]; me = o.data; me.calc_loop_triangles()
    return BVHTree.FromPolygons([o.matrix_world @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
bR = bvh('Door_R'); bS = bvh('Shed'); bE = bvh('Extinguisher'); bLS = bvh('Light_Switch'); bG = bvh('Genset'); bP = bvh('Engine_PrimerLever')
for org, d, b, what in (((-2.4745, -0.15, 1.10), (1, 0, 0), bR, 'hasp plate back face -> Door_R leaf'),
                        ((-2.4745, -0.15, 1.10), (-1, 0, 0), bR, 'hasp plate back face (check it is there)'),
                        ((-2.41, 0.56, 2.302), (1, 0, 0), bS, 'beside key nail -> cladding'),
                        ((-2.175, -1.30, 1.27), (0, 0, -1), bE, 'below extinguisher lever -> valve top'),
                        ((-2.2325, -0.98, 1.40), (-1, 0, 0), bS, 'light switch lever base -> switch box face'),
                        ((0.66, -0.507, 0.50), (0, 1, 0), bG, 'primer lever (y=-0.506) -> lift pump face')):
    loc, n, i, dist = b.ray_cast(Vector(org), Vector(d), 1.0)
    print(what, 'hit', tuple(round(x, 4) for x in loc) if loc else None, 'dist mm', round(dist * 1000, 1) if loc else None)
