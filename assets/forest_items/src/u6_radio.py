"""Forest Update 6: where the control room's radio set (Item_RadioSet, scare X08) stands - on the writing shelf of the west
control console in the Leitstand, at its west end, the front to the operator's side, the back against the step up to
the instrument slope (the antenna lead goes into the console there).

The console is main_rooms.leitstand()'s: console(k, 0.90, 3.90, yw=-5.65, yf=-4.92) in BaseMain's frame (Blender: x along
the building, y across, z up, ground floor z = 0); the shelf's laminate top is at z 0.745, from y yf - 0.24 (the step) to
yf + 0.02 (the bumper's front yf + 0.025). The radio's model frame (items_kit): the front at -y, the microphone on its
clip at +x, the lead out of the back at +y; it stands turned 180 deg about z, so the front faces +y (the operator).

placement(radio_bounds, basemain) -> dict(building=..., unity=...):
  building: the item origin in BaseMain's Blender frame + yaw (deg about +z)
  unity:    p / q in the map (Unity world), as Forest_Dressing.json writes them
"""
import math
import numpy as np

CONSOLE = dict(x0=0.90, x1=3.90, yw=-5.65, yf=-4.92, shelf=0.745)
GAP_END = 0.03          # from the laminate's west end (x0 + 0.02) to the microphone
GAP_BACK = 0.004        # from the step (yf - 0.24) to the case's back (local y +0.12)
CASE = dict(x=(-0.162, 0.162), y=(-0.122, 0.120), z=(0.0, 0.120))   # the case without the microphone and the leads


def qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, np.float64)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def placement(bounds, basemain):
    """bounds: the radio's model-frame box [[lo], [hi]] (Blender, items.json); basemain: {'p': [...], 'q': [...]} of the
    BaseMain prefab in Forest_Layout.json"""
    lo, hi = bounds
    c = CONSOLE
    # turned 180 deg: model +x -> building -x, model +y -> building -y
    x = c['x0'] + 0.02 + GAP_END + hi[0]
    y = c['yf'] - 0.24 + GAP_BACK + CASE['y'][1]
    z = c['shelf']
    span_x = (x - hi[0], x - lo[0])
    span_y = (y - hi[1], y - lo[1])
    assert span_x[0] >= c['x0'] + 0.02 - 1e-6 and span_x[1] <= c['x1'] - 0.02, span_x
    assert span_y[1] <= c['yf'] + 0.025 + 1e-6, ('the cord hangs over the bumper', span_y)
    local = np.array([-x, z, -y])                                   # Blender (x, y, z) -> Unity prefab-local (-x, z, -y)
    p = qrot(basemain['q'], local) + np.array(basemain['p'])
    q_rel = [0.0, -1.0, 0.0, 0.0]                                   # Blender +180 about z == Unity +180 about -y
    q = qmul(basemain['q'], q_rel)
    if q[3] < 0:
        q = [-v for v in q]
    return dict(building=dict(origin=[round(x, 4), round(y, 4), round(z, 4)], yaw=180.0,
                              span_x=[round(v, 4) for v in span_x], span_y=[round(v, 4) for v in span_y]),
                unity=dict(p=[round(float(v), 4) for v in p], q=[round(float(v), 6) + 0.0 for v in q]))


def collider():
    """the case as a box in the model space of the Unity prefab (as Forest_Items.json writes colliders)"""
    (x0, x1), (y0, y1), (z0, z1) = CASE['x'], CASE['y'], CASE['z']
    lo = np.array([-x1, z0, -y1])
    hi = np.array([-x0, z1, -y0])
    return dict(center=[round(float(v), 4) + 0.0 for v in (lo + hi) / 2], size=[round(float(v), 4) for v in hi - lo])


if __name__ == '__main__':
    import json, sys
    rep = json.load(open(sys.argv[1]))['items']['Item_RadioSet']
    lay = json.load(open(sys.argv[2]))
    bm = next(e for e in lay['prefabs'] if e['m'] == 'BaseMain')
    print(json.dumps(placement(rep['bounds'], bm), indent=1), collider())
