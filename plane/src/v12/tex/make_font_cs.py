"""Writes Scripts/UtilityPlanePixelFont.cs (glyph tables generated from pxfont.py, so the game's screen text uses
exactly the glyphs of the v12 instrument atlas) and Textures/T_PixelFont.png (the same glyphs as a sheet, white on
transparent, for sprite / UI use).
python3 make_font_cs.py <package root Assets/UtilityPlane>"""
import os, sys, json
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F

ORDER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,:-+/%°\'()<>=•×?!_→⇆'
SRC_KEY = {'×': 'x'}                     # pxfont.py keeps the cross under 'x' (its "x100" spelling)


def cs_table(font):
    rows = []
    for ch in ORDER:
        g = font['glyphs'][SRC_KEY.get(ch, ch)]
        s = '|'.join(''.join('#' if v else '.' for v in r) for r in g)
        esc = {'\\': '\\\\', '"': '\\"', "'": "\\'"}.get(ch, ch)
        rows.append(f'            {{ \'{esc}\', "{s}" }},')
    return '\n'.join(rows)


CS = r'''using System.Collections.Generic;
using UnityEngine;

namespace UtilityPlane
{
    /// <summary>
    /// v12: the two pixel fonts of the instrument atlas (T_Gauges_BC) for text the game draws itself: radio, GPS and
    /// transponder screens (Display_* quads), the Hobbs counter, any in-cabin readout. Same glyphs as the panel legends,
    /// so screen text matches the PSX cockpit and stays sharp with Point filtering.
    ///   Large57: 5 x 7 px capitals and digits; Small35: 3 x 5 px (M, N, W are wider). 1 px between glyphs.
    /// Legibility from the seat at 1920 x 1080: give one texel about 1 mm on the screen quad (Display_COM1 48 x 17 mm ->
    /// a 48 x 17 texture) and write Large57: characters 7 mm high. Small35 at that scale is fine print (5 mm).
    /// Usage: rig.screensDrivenExternally = true;
    ///        var tex = UtilityPlanePixelFont.CreateTexture(48, 17, new Color32(0, 0, 0, 255));
    ///        UtilityPlanePixelFont.Draw(tex, "118.30", 3, 5, new Color32(120, 255, 140, 255)); tex.Apply(false);
    ///        UtilityPlanePixelFont.SetScreen(displayCom1Renderer.sharedMaterial, tex, Color.white);
    ///        (sharedMaterial after the rig's Awake is the rig's own instance for that screen; the base colour of M_Screen
    ///        stays dark, the text glows through the emission map like a backlit LCD.)
    /// Characters missing from the fonts draw as '?'. Lower case is drawn as capitals; '×' (U+00D7) is the small
    /// multiplication cross ("×100").
    /// </summary>
    public static class UtilityPlanePixelFont
    {
        public enum Size { Small35, Large57 }

        static readonly Dictionary<char, string> F57 = new Dictionary<char, string>
        {
__F57__
        };

        static readonly Dictionary<char, string> F35 = new Dictionary<char, string>
        {
__F35__
        };

        static Dictionary<char, bool[,]> _f57, _f35;

        static Dictionary<char, bool[,]> Glyphs(Size size)
        {
            if (size == Size.Large57) return _f57 ?? (_f57 = Compile(F57));
            return _f35 ?? (_f35 = Compile(F35));
        }

        static Dictionary<char, bool[,]> Compile(Dictionary<char, string> src)
        {
            var d = new Dictionary<char, bool[,]>(src.Count);
            foreach (var kv in src)
            {
                string[] rows = kv.Value.Split('|');
                var g = new bool[rows.Length, rows[0].Length];
                for (int r = 0; r < rows.Length; r++)
                    for (int c = 0; c < rows[r].Length; c++)
                        g[r, c] = rows[r][c] == '#';
                d[kv.Key] = g;
            }
            return d;
        }

        static bool[,] Glyph(Dictionary<char, bool[,]> g, char ch)
        {
            if (g.TryGetValue(ch, out var m)) return m;
            if (g.TryGetValue(char.ToUpperInvariant(ch), out m)) return m;
            return g['?'];
        }

        /// <summary>Glyph height in texels (7 or 5) times scale.</summary>
        public static int Height(Size size = Size.Large57, int scale = 1) => (size == Size.Large57 ? 7 : 5) * Mathf.Max(1, scale);

        /// <summary>Width of a string in texels (1 texel between glyphs, both times scale).</summary>
        public static int Width(string text, Size size = Size.Large57, int scale = 1)
        {
            if (string.IsNullOrEmpty(text)) return 0;
            var g = Glyphs(size);
            int w = 0;
            foreach (char ch in text) w += Glyph(g, ch).GetLength(1) + 1;
            return (w - 1) * Mathf.Max(1, scale);
        }

        /// <summary>A screen texture: RGBA32, Point filter, Clamp, no mipmaps, filled with the background colour
        /// (not yet applied: call Apply after drawing).</summary>
        public static Texture2D CreateTexture(int width, int height, Color32 background)
        {
            var t = new Texture2D(width, height, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                name = "UtilityPlane screen"
            };
            Clear(t, background);
            return t;
        }

        /// <summary>Shows a screen texture on a Display_* material (the rig's instance): the texture becomes the
        /// emission map with the glow colour (URP / Built-in _EmissionMap + _EmissionColor and _EMISSION; HDRP
        /// _EmissiveColorMap + _EmissiveColor, in nits there). Set UtilityPlaneRig.screensDrivenExternally = true first,
        /// otherwise the rig overwrites the emission colour with its idle glow.</summary>
        public static void SetScreen(Material m, Texture2D tex, Color glow)
        {
            if (m == null) return;
            if (m.HasProperty("_EmissiveColorMap"))
            {
                m.SetTexture("_EmissiveColorMap", tex);
                m.SetColor("_EmissiveColor", glow);
            }
            else
            {
                m.SetTexture("_EmissionMap", tex);
                m.SetColor("_EmissionColor", glow);
                m.EnableKeyword("_EMISSION");
            }
        }

        public static void Clear(Texture2D tex, Color32 background)
        {
            var px = new Color32[tex.width * tex.height];
            for (int i = 0; i < px.Length; i++) px[i] = background;
            tex.SetPixels32(px);
        }

        /// <summary>Draws text into a readable texture; (x, yTop) = top-left of the first glyph in texels, y counted
        /// from the TOP edge (as on the screen). Call tex.Apply() afterwards. Returns the width drawn.</summary>
        public static int Draw(Texture2D tex, string text, int x, int yTop, Color32 color, Size size = Size.Large57, int scale = 1)
        {
            var px = tex.GetPixels32();
            int w = Draw(px, tex.width, tex.height, text, x, yTop, color, size, scale);
            tex.SetPixels32(px);
            return w;
        }

        /// <summary>Same on a pixel buffer (row 0 = bottom, as Texture2D.GetPixels32 returns it).</summary>
        public static int Draw(Color32[] pixels, int width, int height, string text, int x, int yTop, Color32 color,
                               Size size = Size.Large57, int scale = 1)
        {
            if (string.IsNullOrEmpty(text)) return 0;
            scale = Mathf.Max(1, scale);
            var g = Glyphs(size);
            int cx = x;
            foreach (char ch in text)
            {
                var m = Glyph(g, ch);
                int gh = m.GetLength(0), gw = m.GetLength(1);
                for (int r = 0; r < gh; r++)
                    for (int c = 0; c < gw; c++)
                    {
                        if (!m[r, c]) continue;
                        for (int sy = 0; sy < scale; sy++)
                            for (int sx = 0; sx < scale; sx++)
                            {
                                int px = cx + c * scale + sx;
                                int py = height - 1 - (yTop + r * scale + sy);
                                if (px < 0 || px >= width || py < 0 || py >= height) continue;
                                pixels[py * width + px] = color;
                            }
                    }
                cx += (gw + 1) * scale;
            }
            return cx - x - scale;
        }
    }
}
'''


def sheet(path):
    """T_PixelFont.png: row 1 = Large57 (cells 6 x 8), row 2 = Small35 (cells 6 x 6), glyphs in ORDER, white on
    transparent; T_PixelFont.json beside the script output lists the cell of every glyph"""
    cols = len(ORDER)
    W = 6 * cols
    W2 = 1
    while W2 < W:
        W2 *= 2
    img = np.zeros((16, W2, 4), np.uint8)
    meta = {'sheet': [W2, 16], 'order': ORDER,
            'note': 'x, y, w, h: glyph rectangle in T_PixelFont.png counted from the TOP-LEFT (image rows go down); '
                    'yBottom = Unity texel row of the rectangle bottom (Texture2D, Sprite and Rect count from the '
                    'bottom): Rect(x, yBottom, w, h). Large57 glyphs are 7 px high, Small35 5 px; 1 px between glyphs. '
                    '\u00d7 is the small multiplication cross (x100).',
            'Large57': {}, 'Small35': {}}
    for k, ch in enumerate(ORDER):
        for font, y0, key in ((F.F57, 0, 'Large57'), (F.F35, 9, 'Small35')):
            g = font['glyphs'][SRC_KEY.get(ch, ch)]
            h, w = g.shape
            x0 = k * 6
            img[y0:y0 + h, x0:x0 + w][g] = (255, 255, 255, 255)
            meta[key][ch] = dict(x=x0, y=y0, w=w, h=h, yBottom=img.shape[0] - y0 - h)
    Image.fromarray(img, 'RGBA').save(path, optimize=True)
    return meta


if __name__ == '__main__':
    root = sys.argv[1]
    cs = CS.replace('__F57__', cs_table(F.F57)).replace('__F35__', cs_table(F.F35))
    open(os.path.join(root, 'Scripts', 'UtilityPlanePixelFont.cs'), 'w', encoding='utf-8').write(cs)
    meta = sheet(os.path.join(root, 'Textures', 'T_PixelFont.png'))
    json.dump(meta, open(os.path.join(root, 'Data', 'pixel_font.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('font: %d glyphs per font' % len(ORDER))
