"""renders/frames/<Clip>_<view>_<frame>.png (holodny_rig.py --render) -> renders/<Clip>.gif (side | 3/4) + clips_sheet.jpg"""
import glob, os, re, sys
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'renders')
F = os.path.join(R, 'frames')
clips = sorted({re.match(r'(.+)_side_\d+\.png', os.path.basename(p)).group(1) for p in glob.glob(os.path.join(F, '*_side_*.png'))})
sheet = []
for c in clips:
    side = sorted(glob.glob(os.path.join(F, f'{c}_side_*.png')))
    q34 = sorted(glob.glob(os.path.join(F, f'{c}_q34_*.png')))
    frames = []
    for a, b in zip(side, q34):
        im = Image.new('RGB', (1280, 480))
        im.paste(Image.open(a), (0, 0))
        im.paste(Image.open(b), (640, 0))
        frames.append(im.resize((960, 360)))
    nums = [int(re.search(r'_(\d+)\.png$', p).group(1)) for p in side[:2]]
    step = nums[1] - nums[0] if len(nums) > 1 else 1             # the renderer draws every 2nd frame of long clips
    frames[0].save(os.path.join(R, f'{c}.gif'), save_all=True, append_images=frames[1:], duration=int(1000 * step / 24), loop=0)
    sheet.append(frames[len(frames) // 3])
cols = 3
W, H = sheet[0].size
S = Image.new('RGB', (W * cols, H * ((len(sheet) + cols - 1) // cols)), 'white')
for i, im in enumerate(sheet):
    S.paste(im, ((i % cols) * W, (i // cols) * H))
S.resize((S.width // 2, S.height // 2)).save(os.path.join(R, 'clips_sheet.jpg'), quality=88)
print('gifs', clips)
