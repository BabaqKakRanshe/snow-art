"""v12 edition 2 preview sheets (v11 / v12 edition 1 / edition 2: stronger PSX interior; same cameras, URP twin)
-> v12r2 deliv previews/"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R = '/home/claude/plane/v12/prev/r/'
R2 = '/home/claude/plane/v12r2/prev/r/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/plane/v12r2/deliv/UtilityPlane_Unity_v12/previews/'
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
BG = (245, 245, 243)


def label(im, text, xy=(10, 8)):
    d = ImageDraw.Draw(im)
    l, t, r, b = d.textbbox(xy, text, font=F)
    d.rectangle((l - 6, t - 4, r + 6, b + 4), fill=(20, 20, 20))
    d.text(xy, text, font=F, fill=(255, 255, 255))


def tile(name, text, crop=None, scale=None):
    im = Image.open((R2 + name[3:] if name.startswith('r2:') else R + name) + '.png').convert('RGB')
    if crop:
        im = im.crop(crop)
    if scale:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS if scale < 1 else Image.NEAREST)
    label(im, text)
    return im


def sheet(title, rows, out, gap=8, note=None):
    W = max(sum(t.width for t in r) + gap * (len(r) - 1) for r in rows)
    top = 60 + (34 if note else 0)
    H = top + sum(max(t.height for t in r) for r in rows) + gap * (len(rows) - 1)
    s = Image.new('RGB', (W + 2 * gap, H + gap), BG)
    d = ImageDraw.Draw(s)
    for size in range(30, 15, -1):
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        if d.textlength(title, font=fb) <= s.width - 2 * (gap + 4):
            break
    d.text((gap + 4, 12 + (30 - size) // 2), title, font=fb, fill=(30, 30, 30))
    if note:
        for size in range(18, 11, -1):
            fn = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
            if d.textlength(note, font=fn) <= s.width - 2 * (gap + 4):
                break
        d.text((gap + 4, 58), note, font=fn, fill=(60, 60, 60))
    y = top
    for r in rows:
        x = gap
        for t in r:
            s.paste(t, (x, y))
            x += t.width + gap
        y += max(t.height for t in r) + gap
    s.save(out, quality=92, optimize=True)
    print(os.path.basename(out), s.size, round(os.path.getsize(out) / 1e6, 2), 'MB')


SIX = (350, 280, 1330, 760)              # 1:1 crop of the main panel in the 1920 x 1080 pilot view
RAD = (1330, 250, 1920, 800)
COP = (940, 380, 1920, 860)
SW = (0, 520, 560, 1080)
LOW = (560, 640, 1480, 1080)             # yoke, pedestal, power levers
WALL = (0, 0, 960, 620)                  # cabin ceiling and left wall

sheet('Utility Plane v11 → v12: кабина из кресла пилота, ночь', [
    [tile('pilot_panel_v11_720_night', 'v11 — реалистичный интерьер'),
     tile('pilot_panel_v12_720_night', 'v12, редакция 1 — 1024², 64 цвета'),
     tile('r2:pilot_panel_F_720_night', 'v12, редакция 2 — 512², 32 цвета, зерно')],
], OUT + 'sheet_A_v12_pilot_night.jpg',
    note='Глаз пилота (Socket_PilotEye), FOV 60°. panelLight 1, floodLight 1 (красная заливка), все плафоны 100 %. Модель света URP, тени Medium. Кадры 1280 × 720.')

sheet('Utility Plane v11 → v12: кабина из кресла пилота, ровный свет', [
    [tile('pilot_panel_v11_flat', 'v11', scale=0.5), tile('pilot_panel_v12_flat', 'v12, редакция 1', scale=0.5),
     tile('r2:pilot_panel_F_flat', 'v12, редакция 2', scale=0.5)],
    [tile('pilot_panel_v12_flat', 'редакция 1 — кроп 1:1', LOW), tile('r2:pilot_panel_F_flat', 'редакция 2 — кроп 1:1', LOW)],
], OUT + 'sheet_B_v12_pilot_day.jpg',
    note='Ровный свет окружения без ламп — чтобы видеть сами текстуры. Кадры 1920 × 1080: сверху уменьшены вдвое, снизу кропы 1:1 (штурвал, пьедестал, РУД).')

sheet('Читаемость при 1920 × 1080: кропы 1:1 из кресла пилота (пиксель кропа = пиксель экрана)', [
    [tile('pilot_panel_v11_flat', 'v11 — приборы', SIX), tile('r2:pilot_panel_F_flat', 'v12 — приборы', SIX)],
    [tile('pilot_panel_v11_flat', 'v11 — табло и радио', RAD), tile('r2:pilot_panel_F_flat', 'v12 — табло и радио', RAD),
     tile('r2:pilot_panel_F_flat', 'v12 — тумблеры', SW)],
], OUT + 'sheet_C_v12_legibility_pilot.jpg',
    note='v12, редакция 2. Читаются: цифры всех приборов, табло, надписи тумблеров, таблички. Подписи кнопок радио и АЗС (в самолёте 2–3 мм) — с 2560 × 1440 или наклонившись.')

sheet('Читаемость при 1920 × 1080: кресло второго пилота', [
    [tile('copilot_panel_v11_flat', 'v11', scale=0.5), tile('r2:copilot_panel_F_flat', 'v12, редакция 2', scale=0.5)],
    [tile('copilot_panel_v11_flat', 'v11 — кроп 1:1', COP), tile('r2:copilot_panel_F_flat', 'v12 — кроп 1:1', COP)],
], OUT + 'sheet_D_v12_legibility_copilot.jpg',
    note='Глаз второго пилота (Socket_CopilotEye). Приборы систем, OPERATING LIMITATIONS, NO SMOKING — читаются.')

sheet('Utility Plane v11 → v12: отсек', [
    [tile('cabin_rear_v11_flat', 'v11 — ровный свет', scale=0.5), tile('cabin_rear_v12_flat', 'v12, ред. 1 — ровный свет', scale=0.5),
     tile('r2:cabin_rear_F_flat', 'v12, ред. 2 — ровный свет', scale=0.5)],
    [tile('cabin_rear_v11_720_night', 'v11 — ночь, плафоны', scale=0.75), tile('cabin_rear_v12_720_night', 'v12, ред. 1 — ночь', scale=0.75),
     tile('r2:cabin_rear_F_720_night', 'v12, ред. 2 — ночь', scale=0.75)],
    [tile('cabin_rear_v12_flat', 'ред. 1 — кроп 1:1: потолок и стена', WALL), tile('r2:cabin_rear_F_flat', 'ред. 2 — кроп 1:1', WALL)],
], OUT + 'sheet_E_v12_cabin.jpg',
    note='Из отсека к кабине. Редакция 2: стены, потолок и пол 85 и 76 px/м (было 171 и 153), 32 цвета, зерно, грязь у пола; металл в маске — ступенями 0, 1/3, 2/3, 1.')

sheet('Вблизи: 0.45 м от доски (наклон к высотомеру)', [
    [tile('pilot_lean_v11_flat', 'v11', scale=0.5), tile('pilot_lean_v12_flat', 'v12, редакция 1', scale=0.5),
     tile('r2:pilot_lean_F_flat', 'v12, редакция 2 — тексель доски 7.5 мм', scale=0.5)],
], OUT + 'sheet_F_v12_closeup.jpg',
    note='Редакция 2: тексели доски вдвое крупнее (133 px/м), зерно и пятна на ровной краске; цифры приборов — пиксели шрифта 5 × 7 из своего атласа, как были.')

# atlas overview: the pixel-art text atlas, upscaled x2 (nearest)
a = Image.open('/home/claude/plane/export/unity_v12r2/Assets/UtilityPlane/Textures/T_Gauges_BC.png').convert('RGB')
e = Image.open('/home/claude/plane/export/unity_v12r2/Assets/UtilityPlane/Textures/T_Displays_Emission.png').convert('RGB')
top = a.crop((0, 0, 1024, 384)).resize((2048, 768), Image.NEAREST)
label(top, 'T_Gauges_BC — шкалы (64 точки на прибор), ×2')
bot = a.crop((0, 512, 1024, 1024)).resize((2048, 1024), Image.NEAREST)
label(bot, 'T_Gauges_BC — радио, лайтплейты, табло, плакарды, ×2')
x, y, w, h = [v // 4 for v in (1605, 2064, 1484, 477)]
ann = Image.fromarray(np.hstack([np.asarray(a.crop((x, y, x + w, y + h))), np.zeros((h, 6, 3), np.uint8),
                                 np.asarray(e.crop((x, y, x + w, y + h)))])).resize(((2 * w + 6) * 3, h * 3), Image.NEAREST)
label(ann, 'Табло: погасшее (T_Gauges_BC) и горящее (T_Displays_Emission), ×3')
sheet('v12: атлас надписей 1024² — пиксельная графика, шрифты 5 × 7 и 3 × 5', [[top], [bot], [ann]],
      OUT + 'sheet_G_v12_text_atlas.jpg', note='Раскладка UV прежняя (как 2048² в v11); каждая буква — на сетке текселей, без сглаживания.')
