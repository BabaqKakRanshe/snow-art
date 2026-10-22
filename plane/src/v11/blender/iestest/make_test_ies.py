import sys, numpy as np
sys.path.insert(0, '/home/claude/plane/v11/blender')
from ies_lm63 import write_ies
V = np.arange(0, 181, 5.0); Hh = np.arange(0, 361, 10.0)
cd = np.full((len(Hh), len(V)), 100.0)
for i, h in enumerate(Hh):
    if 20 <= h <= 60: cd[i] = 1000.0
cd[:, V < 20] *= 3.0
cd[:, V > 90] = 0.0
write_ies('/home/claude/plane/v11/blender/iestest/wedge.ies', V, Hh, cd, {'TEST': 'wedge C20-60'})
write_ies('/home/claude/plane/v11/blender/iestest/uniform1000.ies', V, Hh, np.full((len(Hh), len(V)), 1000.0), {'TEST': 'uniform 1000'})
write_ies('/home/claude/plane/v11/blender/iestest/uniform10.ies', V, Hh, np.full((len(Hh), len(V)), 10.0), {'TEST': 'uniform 10'})
print('ok')
