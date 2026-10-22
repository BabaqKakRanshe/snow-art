import bpy, sys, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
o = bpy.data.objects['Cockpit_Static']
dg = bpy.context.evaluated_depsgraph_get()
me = o.evaluated_get(dg).to_mesh()
mw = np.array(o.matrix_world)
V = np.array([v.co for v in me.vertices]); V = V @ mw[:3,:3].T + mw[:3,3]
U = np.stack([-V[:,0], V[:,2], -V[:,1]], 1)
me.calc_loop_triangles()
T = np.array([t.vertices[:] for t in me.loop_triangles])
C = U[T].mean(1)
N = np.cross(U[T][:,1]-U[T][:,0], U[T][:,2]-U[T][:,0]); A = np.linalg.norm(N,axis=1); N = N/np.maximum(A[:,None],1e-12)
for xs in (-0.3, 0.0, 0.3):
    m = (np.abs(C[:,0]-xs) < 0.03) & (C[:,1] > 1.95) & (C[:,1] < 2.35) & (C[:,2] > 2.6) & (C[:,2] < 3.4)
    print('slice x=%.2f'%xs, m.sum())
    # coarse profile: for z bins, list min/max y of triangle centroids with downward-facing normals (underside of the glareshield)
    for z0 in np.arange(2.70, 3.36, 0.04):
        mm = m & (C[:,2]>=z0) & (C[:,2]<z0+0.04)
        if mm.sum()==0: continue
        down = mm & (N[:,1] < -0.5); up = mm & (N[:,1] > 0.5); aft = mm & (N[:,2] < -0.5)
        f = lambda s: ('%.3f..%.3f'%(C[s,1].min(), C[s,1].max())) if s.sum() else '-'
        print('  z %.2f  down-facing y %s | up-facing y %s | aft-facing y %s'%(z0, f(down), f(up), f(aft)))
