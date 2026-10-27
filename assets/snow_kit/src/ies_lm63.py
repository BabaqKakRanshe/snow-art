"""Minimal IES LM-63-2002 writer (type C photometry, absolute candela, metres)."""
import numpy as np


def write_ies(path, v_angles, h_angles, cd, keywords, width=0.0, length=0.0, height=0.0, watts=0.0):
    """cd: array [len(h_angles), len(v_angles)] in candela (rows = horizontal angles)."""
    v_angles = np.asarray(v_angles, float); h_angles = np.asarray(h_angles, float); cd = np.asarray(cd, float)
    assert cd.shape == (len(h_angles), len(v_angles))
    lines = ['IESNA:LM-63-2002']
    for k, v in keywords.items():
        lines.append('[%s] %s' % (k, v))
    lines.append('TILT=NONE')
    # lamps, lumens per lamp (-1 = absolute photometry), multiplier, nV, nH, type C = 1, units 2 = metres, w, l, h
    lines.append('1 -1 1.0 %d %d 1 2 %.4f %.4f %.4f' % (len(v_angles), len(h_angles), width, length, height))
    lines.append('1.0 1.0 %.1f' % watts)

    def wrap(vals, fmt):
        out, cur = [], []
        for x in vals:
            cur.append(fmt % x)
            if len(cur) == 10:
                out.append(' '.join(cur)); cur = []
        if cur:
            out.append(' '.join(cur))
        return out
    lines += wrap(v_angles, '%g')
    lines += wrap(h_angles, '%g')
    for row in cd:
        lines += wrap(row, '%.4g')
    txt = '\r\n'.join(lines) + '\r\n'
    with open(path, 'w', newline='') as f:
        f.write(txt)
    return txt
