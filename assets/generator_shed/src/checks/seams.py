import bpy, numpy as np
from PIL import Image
from scipy import ndimage
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
def cover(names, n):
    m = np.zeros((n, n), bool)
    yy, xx = np.mgrid[0:n, 0:n]
    px = (xx + 0.5) / n; py = 1 - (yy + 0.5) / n
    for nm in names:
        o = bpy.data.objects[nm]; me = o.data; me.calc_loop_triangles(); uv = me.uv_layers['PSX'].data
        for t in me.loop_triangles:
            a, b, c = [np.array(uv[l].uv) for l in t.loops]
            x0, x1 = int(max(0, min(a[0], b[0], c[0]) * n - 1)), int(min(n, max(a[0], b[0], c[0]) * n + 2))
            y0, y1 = int(max(0, (1 - max(a[1], b[1], c[1])) * n - 1)), int(min(n, (1 - min(a[1], b[1], c[1])) * n + 2))
            if x1 <= x0 or y1 <= y0: continue
            X, Y = px[y0:y1, x0:x1], py[y0:y1, x0:x1]
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12: continue
            l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
            l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
            l3 = 1 - l1 - l2
            m[y0:y1, x0:x1] |= (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    return m
for atlas, names in (('Snow', ['Snow_Roof', 'Snow_DoorDrift']), ('Genset', ['Genset'])):
    img = np.asarray(Image.open(f'/home/claude/uaz/tex/gen/T_Gen_{atlas}_BaseColor.png').convert('RGB')).astype(float)
    n = img.shape[0]
    cov = cover(names, n)
    lum = img.mean(2)
    inner = ndimage.binary_erosion(cov, iterations=2)
    border = cov & ~ndimage.binary_erosion(cov, iterations=1)
    print(atlas, n, 'covered', cov.sum(), 'border texels mean lum %.1f  interior (2 px in) %.1f' % (lum[border].mean(), lum[inner].mean()))
