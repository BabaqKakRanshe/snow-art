"""KPP v2: the package frames and the game (Forest, Unity world after ForestYardPlan and ForestRelocation).
Booth frame (Checkpoint): x toward the road, y toward the back (the station side), z up; origin = the middle of the pad on
the ground.  Barrier and Gate roots share the booth's axes in the package (yaw 0); in the game the Checkpoint and the Barrier
move together (ForestRelocation, a rigid move), the Gate stays at the yard (ForestYardPlan scales its position only).
Unity prefab-local = (-x, z, -y); a root's yaw turns that about +Y (left-handed)."""
import math
import numpy as np

KPP_U = dict(p=(313.0406, 16.4376, -289.5625), yaw=8.0)                 # Update 3 Checkpoint (Forest_Layout.json)
BARRIER_PLACE = (3.10, -7.00, -0.3867)                                   # booth frame (kpp_kit)
GATE_PLACE = (11.00, 0.00, -0.3772)
REL_OLD = np.array([310.945, 16.0509, -282.1992])                        # ForestRelocation (the barrier's pivot)
REL_NEW = np.array([143.51488, 9.27351, -64.67514])
REL_YAW = -65.3345
GATE_GAME = dict(p=(313.23465, 16.018454, -309.11115), yaw=8.0)          # the Gate root in the game (U7 layout)


def to_unity(v):
    return np.array([-v[0], v[2], -v[1]], float)


def from_unity(u):
    return np.array([-u[0], -u[2], u[1]], float)


def rot_y(u, deg):
    """Unity (left-handed) yaw: x' = x cos + z sin, z' = -x sin + z cos"""
    a = math.radians(deg)
    return np.array([u[0] * math.cos(a) + u[2] * math.sin(a), u[1], -u[0] * math.sin(a) + u[2] * math.cos(a)])


def relocate(p):
    """ForestRelocation.Point (fence_layout.T): Update 3 world -> the game"""
    t = math.radians(REL_YAW)
    d = np.array([p[0] - REL_OLD[0], p[2] - REL_OLD[2]])
    d = np.array([d[0] * math.cos(t) + d[1] * math.sin(t), -d[0] * math.sin(t) + d[1] * math.cos(t)])
    return np.array([REL_NEW[0] + d[0], REL_NEW[1] + (p[1] - REL_OLD[1]), REL_NEW[2] + d[1]])


def unrelocate(g):
    t = math.radians(REL_YAW)
    d = np.array([g[0] - REL_NEW[0], g[2] - REL_NEW[2]])
    d = np.array([d[0] * math.cos(t) - d[1] * math.sin(t), d[0] * math.sin(t) + d[1] * math.cos(t)])
    return np.array([REL_OLD[0] + d[0], REL_OLD[1] + (g[1] - REL_NEW[1]), REL_OLD[2] + d[1]])


def booth_to_u3(p):
    return np.array(KPP_U['p']) + rot_y(to_unity(p), KPP_U['yaw'])


def u3_to_booth(w):
    return from_unity(rot_y(np.asarray(w, float) - np.array(KPP_U['p']), -KPP_U['yaw']))


def booth_to_game(p):
    return relocate(booth_to_u3(p))


def game_to_booth(g):
    return u3_to_booth(unrelocate(g))


BOOTH_YAW_GAME = KPP_U['yaw'] + REL_YAW                                  # -57.3345


def gate_to_game(p):
    return np.array(GATE_GAME['p']) + rot_y(to_unity(p), GATE_GAME['yaw'])


def game_to_gate(g):
    return from_unity(rot_y(np.asarray(g, float) - np.array(GATE_GAME['p']), -GATE_GAME['yaw']))


def barrier_to_booth(p):
    return np.asarray(p, float) + np.array(BARRIER_PLACE)


if __name__ == '__main__':
    print('booth origin in the game', booth_to_game((0, 0, 0)).round(3))
    print('barrier origin in the game', booth_to_game(BARRIER_PLACE).round(3), '(U7: 143.51488, 9.27351, -64.67514)')
    print('rest post', booth_to_game(np.array(BARRIER_PLACE) + (5.6, 0, 0)).round(3))
    print('round trip', game_to_booth(booth_to_game((1.0, 2.0, 3.0))).round(6))
    print('gate west / east ends', gate_to_game((2.93, 0, 0)).round(3), gate_to_game((-7.9, 0, 0)).round(3))
