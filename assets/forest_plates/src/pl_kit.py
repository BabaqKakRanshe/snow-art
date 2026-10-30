"""Forest first-evening plates (forest_plates 1.0, built locally with tools/snow_style 27.10; docs/gdd/QUESTIONS_7.md §4): four
prefabs, each in its own frame (Blender: z up, the front -y, metres; Unity (x, y, z) -> (-x, z, -y), the front -> +Z).
  PL_Notstrom    the yellow tag NOTSTROM / 12V EMERGENCY on the checkpoint's power cabinet: a 4 mm steel plate, the panel
                 on its front; origin = the middle of its back (the surface it is screwed to)
  PL_GenStart    the start form STARTVORGANG on the generator container's wall by the door: a 6 mm steel plate, the enamel
                 form on its front; origin = the middle of its back
  PL_HangarKey   GESPERRT / LOCKED, SCHLÜSSEL: STATIONSLEITER on the lake hangar's gate: as PL_GenStart
  PL_MapBoard    the overlook's SIE SIND HIER / YOU ARE HERE board: two posts, a framed board, a plank roof, the map on the
                 board's front; origin = the ground between the posts
The panel atlas (pl_tex) carries every face with letters; the steel and the wood go to the PLProps atlas (psxbake)."""
from mathutils import Vector
import gen_kit as K
from gen_kit import kb, part, box6, quad
import pl_tex as PT

uv = PT.uv
ROOTS = ['PL_Notstrom', 'PL_GenStart', 'PL_HangarKey', 'PL_MapBoard']
DISPLAY = {'PL_Notstrom': Vector((-1.6, 0.0, 1.2)), 'PL_GenStart': Vector((-0.9, 0.0, 1.2)),
           'PL_HangarKey': Vector((0.1, 0.0, 1.2)), 'PL_MapBoard': Vector((1.6, 0.0, 0.0))}
ROOT_OF = {}
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot_xyz_deg or None) in the root frame

(Z_PSTEEL, Z_POST, Z_BOARD, Z_ROOF) = range(240, 244)


def reg(name, atlas, root):
    ROOT_OF[name] = root
    return kb(name, atlas)


def build_plate(root, region, thick, rim, note):
    """a steel plate a little larger than its panel, the panel quad 0.2 mm in front of it"""
    w, h = PT.size_m(region)
    k = reg(root, 'PLProps', root)
    box6(k, (-w / 2 - rim, -thick, -h / 2 - rim), (w / 2 + rim, 0.0, h / 2 + rim), Z_PSTEEL, skip=('+y',))
    pn = reg(root + '_Face', 'panel', root)
    quad(pn, Vector((0.0, -thick - 0.0002, 0.0)), (0, -1, 0), w, h, uv(region))
    part(root + '_Face', 'static', (0.0, -thick, 0.0), parent=root, note=note + ' (panel atlas)')
    part(root, 'static', (0, 0, 0), note=f'{note} (root): origin = the middle of the plate\'s back, the face looks -y')
    BOXES.append((root + '_Plate', root, (-w / 2 - rim, w / 2 + rim, -thick, 0.0, -h / 2 - rim, h / 2 + rim), None))


B_W, B_H = PT.size_m('map')                     # 1.00 x 1.10 m of map
B_Z0 = 0.80                                     # the board's lower edge above the ground
POST_X, POST_TOP = 0.60, 2.10


def build_board():
    k = reg('PL_MapBoard', 'PLProps', 'PL_MapBoard')
    for sx in (-1, 1):                                                  # two square posts, sunk 0.40
        box6(k, (sx * POST_X - 0.045, -0.045, -0.40), (sx * POST_X + 0.045, 0.045, POST_TOP), Z_POST)
    fr = 0.05                                                           # the board: a frame round the map, 4 cm deep
    box6(k, (-B_W / 2 - fr, -0.085, B_Z0 - fr), (B_W / 2 + fr, -0.045, B_Z0 + B_H + fr), Z_BOARD)
    for sx in (-1, 1):                                                  # the battens that hold it on the posts
        box6(k, (sx * POST_X - 0.06, -0.045, B_Z0 + 0.15), (sx * POST_X + 0.06, -0.044, B_Z0 + 0.25), Z_BOARD, skip=('+y',))
        box6(k, (sx * POST_X - 0.06, -0.045, B_Z0 + B_H - 0.25), (sx * POST_X + 0.06, -0.044, B_Z0 + B_H - 0.15), Z_BOARD, skip=('+y',))
    box6(k, (-POST_X - 0.12, -0.26, POST_TOP), (POST_X + 0.12, 0.10, POST_TOP + 0.035), Z_ROOF)   # a plank roof over it
    pn = reg('PL_MapBoard_Face', 'panel', 'PL_MapBoard')
    zc = B_Z0 + B_H / 2
    quad(pn, Vector((0.0, -0.0852, zc)), (0, -1, 0), B_W, B_H, uv('map'))
    part('PL_MapBoard_Face', 'static', (0.0, -0.085, zc), parent='PL_MapBoard',
         note='SIE SIND HIER / YOU ARE HERE and the map of the area (panel atlas)')
    part('PL_MapBoard', 'static', (0, 0, 0), note='the overlook\'s map board (root): origin = the ground between the posts '
                                                  '(sunk 0.40); the map faces -y (the reader)')
    BOXES.extend([('Board_PostL', 'PL_MapBoard', (-POST_X - 0.05, -POST_X + 0.05, -0.05, 0.05, 0.0, POST_TOP), None),
                  ('Board_PostR', 'PL_MapBoard', (POST_X - 0.05, POST_X + 0.05, -0.05, 0.05, 0.0, POST_TOP), None),
                  ('Board_Board', 'PL_MapBoard', (-B_W / 2 - fr, B_W / 2 + fr, -0.09, -0.04, B_Z0 - fr, B_Z0 + B_H + fr), None)])


def build_plates():
    build_plate('PL_Notstrom', 'notstrom', 0.004, 0.006, 'NOTSTROM / 12V EMERGENCY tag on the checkpoint\'s power cabinet')
    build_plate('PL_GenStart', 'genstart', 0.006, 0.012, 'STARTVORGANG start form on the generator container\'s wall')
    build_plate('PL_HangarKey', 'hangar', 0.006, 0.012, 'GESPERRT / SCHLÜSSEL: STATIONSLEITER plate on the lake hangar\'s gate')
    build_board()
