"""Read the heightmap of a Unity TerrainData asset (binary) -> heights_1_1.npy (float32, world metres, [z, x])."""
import sys, numpy as np, UnityPy
src, out, originY, sizeY = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
env = UnityPy.load(src)
for obj in env.objects:
    if obj.type.name == 'TerrainData':
        tt = obj.read_typetree()
        hm = tt['m_Heightmap']
        res = hm.get('m_Resolution')
        h = np.array(hm['m_Heights'], dtype=np.float32)
        print('res', res, 'n', h.size, 'scale', hm.get('m_Scale'), 'min', h.min(), 'max', h.max(), 'keys', list(hm.keys()))
        n = int(round(h.size ** 0.5))
        H = h.reshape(n, n) / 32766.0 * sizeY + originY
        np.save(out, H)
        print('saved', out, H.shape, float(H.min()), float(H.max()))
        break
