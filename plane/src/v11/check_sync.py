"""Cross-check the C# LightDefs against spec_v11.LIGHTS (angles, range, intensity, kelvin, offsets, glow / beam numbers)."""
import re, sys, numpy as np
from spec_v11 import LIGHTS, BY_KEY, dirv
cs = open('/home/claude/plane/export/unity_v11/Assets/UtilityPlane/Scripts/UtilityPlaneRig.Lights.cs').read()
body = cs[cs.index('public static readonly LightDef[] LightDefs'):cs.index('};', cs.index('public static readonly LightDef[] LightDefs'))]
ok = True
for L in LIGHTS:
    k = L['key']
    m = re.search(r'Lamp\("%s",.*?(?=(?:WithGlow|WithBeam|Lamp\(|//|$))' % re.escape(k), body, re.S)
    if not m:
        print('MISSING in C#', k); ok = False; continue
    seg = m.group(0)
    nums = [float(x) for x in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?=f?\b)', seg)]
    want = [L['outer'], L['inner'], L['range'], L['intensity'], L['cct']]
    # find the sequence outer, inner, range, intensity, (hdrp), kelvin
    found = False
    for i in range(len(nums) - 5):
        if nums[i] == want[0] and nums[i + 1] == want[1] and abs(nums[i + 2] - want[2]) < 1e-6 and abs(nums[i + 3] - want[3]) < 1e-6 and nums[i + 5] == want[4]:
            found = True
    if not found:
        print('MISMATCH', k, 'spec', want, 'C# numbers', nums[:16]); ok = False
    mn = re.search(r'nearPlane: ([0-9.]+)f', seg)
    near = float(mn.group(1)) if mn else 0.1
    if abs(near - L['near']) > 1e-6:
        print('NEAR', k, 'spec', L['near'], 'C#', near); ok = False
    off = L['offset']
    if any(abs(v) > 0 for v in off):
        mo = re.search(r'offset: new Vector3\(([^)]*)\)', seg)
        got = [float(x.strip().rstrip('f')) for x in mo.group(1).split(',')] if mo else None
        if got is None or np.max(np.abs(np.array(got) - np.array(off))) > 1e-6:
            print('OFFSET', k, off, got); ok = False
print('C# LightDefs in sync with spec' if ok else 'OUT OF SYNC')
