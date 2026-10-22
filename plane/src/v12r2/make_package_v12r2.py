"""v12 package, edition 2 (stronger PSX interior + pixel-art text atlas): export/unity_v12r2/Assets/UtilityPlane from
the v11 package (edition 1: v12/make_package_v12.py -> export/unity_v12).
 - textures: interior atlases PSX (Cockpit, Interior, Floor, Seats 512, Fittings 256; BaseColor + MaskMap; edition 1:
   1024 / 512), webbing PSX 32 x 8, instrument / placard atlas pixel art 1024 (T_Gauges_BC, T_Gauges_Emission, T_Displays_Emission),
   pixel font sheet T_PixelFont; the interior normal maps, the webbing normal map and the detail maps are dropped;
 - Scripts/UtilityPlanePixelFont.cs (+ Data/pixel_font.json): the atlas fonts for screen text drawn by the game;
 - Editor/UtilityPlaneSetup.cs: PSX import for the interior, the text atlas and the webbing, sizes, font import,
   webbing without normal map, stale-file list, version strings;
 - Data/atlas_texel.json: interior atlases psx, no detail maps, new densities.
The FBX and every other file are the v11 files unchanged.
python3 make_package_v12r2.py"""
import os, sys, shutil, json, re, subprocess

SRC = '/home/claude/plane/export/unity_v11/Assets/UtilityPlane'
DST = '/home/claude/plane/export/unity_v12r2/Assets/UtilityPlane'
PSX = '/home/claude/plane/v12r2/work/psxF'
GAU = '/home/claude/plane/v12/work/gauges'
DROP = {f'Textures/T_{a}_Normal.png' for a in ('Cockpit', 'Interior', 'Floor', 'Seats', 'Fittings', 'Webbing')} | \
       {f'Textures/T_Detail_{d}_{k}.png' for d in ('Grain', 'Leather') for k in ('Albedo', 'Normal')}

if os.path.exists(DST):
    shutil.rmtree(DST)
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), SRC)
        if rel in DROP:
            continue
        os.makedirs(os.path.join(DST, os.path.dirname(rel)), exist_ok=True)
        shutil.copy2(os.path.join(SRC, rel), os.path.join(DST, rel))
for a in ('Cockpit', 'Interior', 'Floor', 'Seats', 'Fittings'):
    for k in ('BaseColor', 'MaskMap'):
        shutil.copyfile(os.path.join(PSX, f'T_{a}_{k}.png'), os.path.join(DST, 'Textures', f'T_{a}_{k}.png'))
shutil.copyfile(os.path.join(PSX, 'T_Webbing_BaseColor.png'), os.path.join(DST, 'Textures', 'T_Webbing_BaseColor.png'))
for n in ('T_Gauges_BC', 'T_Gauges_Emission', 'T_Displays_Emission'):
    shutil.copyfile(os.path.join(GAU, n + '.png'), os.path.join(DST, 'Textures', n + '.png'))
subprocess.run([sys.executable, '/home/claude/plane/v12/tex/make_font_cs.py', DST], check=True)

# ------------------------------------------------------------------ Setup
p = os.path.join(DST, 'Editor', 'UtilityPlaneSetup.cs')
s = open(p, encoding='utf-8').read()
R = [
    ('/// <summary>First-import settings for the Utility Plane v11 model and textures (Assets/UtilityPlane/...).</summary>',
     '/// <summary>First-import settings for the Utility Plane v12 model and textures (Assets/UtilityPlane/...).</summary>'),
    ('''    /// makes the glow quads and beam meshes at run time.
    /// No Rigidbody is added: the vehicle and cargo systems own physics.''',
     '''    /// makes the glow quads and beam meshes at run time.
    /// v12 (PSX interior, edition 2): the interior atlases (Cockpit, Interior, Floor, Seats 512 px, Fittings 256) and the
    /// webbing are PSX textures like the exterior (32-colour palette with ordered dither, shading and painted light baked
    /// in, Point, colour uncompressed, no normal or detail maps); the instrument / placard atlas (T_Gauges_*,
    /// T_Displays_Emission, 1024 px) is pixel art with
    /// pixel-font legends, imported the same way; T_PixelFont = the same fonts for screen text (UtilityPlanePixelFont).
    /// No Rigidbody is added: the vehicle and cargo systems own physics.'''),
    ('''        /// <summary>v10: interior atlases (realistic interior, 1024 px since v10).</summary>''',
     '''        /// <summary>v10: interior atlases (1024 px v10-v11; v12: PSX 512 px, Fittings 256).</summary>'''),
    ('''        public static bool IsPsxTexture(string n) =>
            n.StartsWith("T_Airframe_") || n.StartsWith("T_Wing_") || n.StartsWith("T_Details_") ||
            n.StartsWith("T_Survival_") || n.StartsWith("T_KitCovers_") || n.StartsWith("T_KitProps_");''',
     '''        public static bool IsPsxTexture(string n) =>
            n.StartsWith("T_Airframe_") || n.StartsWith("T_Wing_") || n.StartsWith("T_Details_") ||
            n.StartsWith("T_Survival_") || n.StartsWith("T_KitCovers_") || n.StartsWith("T_KitProps_") ||
            IsInteriorAtlas(n) || IsTextAtlas(n) || n.StartsWith("T_Webbing_");                    // v12

        /// <summary>v12: instrument, placard, lightplate and display atlas: pixel art with pixel-font legends, 1024 px.
        /// Point keeps every letter sharp; no compression keeps the colours exact.</summary>
        public static bool IsTextAtlas(string n) => n.StartsWith("T_Gauges_") || n.StartsWith("T_Displays_");'''),
    ('''            ti.maxTextureSize = (n.Contains("Webbing") || n.Contains("_Detail_") || n.StartsWith("T_Prop") || IsPsxTexture(n)) ? 512 :
                                n.StartsWith("T_GlassFog") || IsInteriorAtlas(n) ? 1024 :          // v10: interior 1024
                                n.StartsWith("T_FogPrint_") ? 128 : 2048;                          // gauges, placards, displays''',
     '''            bool keepSprite = n.StartsWith("T_PixelFont") && ti.textureType == TextureImporterType.Sprite;   // v12
            ti.maxTextureSize = n.StartsWith("T_FogPrint_") ? 128 :
                                n.StartsWith("T_GlassFog") || IsTextAtlas(n) ? 1024 :                       // v12: text atlas
                                n.Contains("Webbing") || n.Contains("_Detail_") || n.StartsWith("T_Prop") ||
                                n.StartsWith("T_PixelFont") || IsPsxTexture(n) ? 512 :                      // PSX exterior + interior, props
                                2048;                                                                        // anything else'''),
    ('''            if (n.StartsWith("T_FogPrint_"))
            {''',
     '''            if (n.StartsWith("T_PixelFont"))
            {
                // v12 pixel font sheet (white glyphs on transparent): exact texels, no mips; a sheet the user sliced
                // as Sprite (Multiple) stays a sprite sheet when the menu runs again
                if (keepSprite) ti.textureType = TextureImporterType.Sprite;
                ti.sRGBTexture = true;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.alphaIsTransparency = true;
                ti.filterMode = FilterMode.Point;
                ti.mipmapEnabled = false;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.anisoLevel = 0;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                return;
            }
            if (n.StartsWith("T_FogPrint_"))
            {'''),
    ('''            if (IsPsxTexture(n))
            {
                ti.filterMode = FilterMode.Point;                 // crisp PSX texels (mips stay on: no shimmer far away)
                ti.anisoLevel = 0;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
            }''',
     '''            if (IsPsxTexture(n))
            {
                ti.filterMode = FilterMode.Point;                 // crisp PSX texels (mips stay on: no shimmer far away)
                ti.anisoLevel = 0;
                // colour maps uncompressed: DXT would smear the palette, the dither and the pixel letters. v12: masks
                // (metal and smoothness in at most 4 even steps, G = B = 1) and the emission maps of the text atlas (black
                // + one glyph colour per 4 x 4 block almost everywhere) block-compress practically without loss, at 1/4
                // and 1/8 the memory
                ti.textureCompression = n.EndsWith("_MaskMap") || n.EndsWith("_Emission")
                    ? TextureImporterCompression.Compressed : TextureImporterCompression.Uncompressed;
            }'''),
    ('''            Debug.Log($"[UtilityPlane] Done ({pipe}), v11. Prefabs in {Root}/Prefabs; " +''',
     '''            Debug.Log($"[UtilityPlane] Done ({pipe}), v12. Prefabs in {Root}/Prefabs; " +'''),
    ('''            // (v9: the PSX exterior atlases have no normal maps, and the Paint detail map is no longer used)
            var stale = new[] { Root + "/Materials/M_CargoNet.mat", Root + "/Textures/T_CargoNet_BCA.png",
                                Root + "/Textures/T_Airframe_Normal.png", Root + "/Textures/T_Wing_Normal.png",
                                Root + "/Textures/T_Details_Normal.png", Root + "/Textures/T_Detail_Paint_Albedo.png",
                                Root + "/Textures/T_Detail_Paint_Normal.png" }''',
     '''            // (v9: the PSX exterior atlases have no normal maps, and the Paint detail map is no longer used;
            //  v12: neither have the PSX interior atlases and the webbing, and the Grain / Leather detail maps are gone)
            var stale = new[] { Root + "/Materials/M_CargoNet.mat", Root + "/Textures/T_CargoNet_BCA.png",
                                Root + "/Textures/T_Airframe_Normal.png", Root + "/Textures/T_Wing_Normal.png",
                                Root + "/Textures/T_Details_Normal.png", Root + "/Textures/T_Detail_Paint_Albedo.png",
                                Root + "/Textures/T_Detail_Paint_Normal.png", Root + "/Textures/T_Webbing_Normal.png",
                                Root + "/Textures/T_Detail_Grain_Albedo.png", Root + "/Textures/T_Detail_Grain_Normal.png",
                                Root + "/Textures/T_Detail_Leather_Albedo.png", Root + "/Textures/T_Detail_Leather_Normal.png" }
                .Concat(new[] { "Cockpit", "Interior", "Floor", "Seats", "Fittings" }
                    .Select(a => $"{Root}/Textures/T_{a}_Normal.png"))'''),
    ('''        // tiling material (cargo barrier webbing: UV u runs in metres along the strap)
        static Material MakeTiled(string name, string prefix, string pipe, Vector2 tiling, float smooth)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, Tex(prefix + "_BaseColor"), Color.white);
            var nrm = Tex(prefix + "_Normal");
            switch (pipe)
            {
                case "HDRP":
                    mat.SetTexture("_NormalMap", nrm);
                    mat.SetTextureScale("_BaseColorMap", tiling);
                    break;
                case "URP":
                    mat.SetTexture("_BumpMap", nrm); mat.EnableKeyword("_NORMALMAP");
                    mat.SetTextureScale("_BaseMap", tiling);
                    break;
                default:
                    mat.SetTexture("_BumpMap", nrm); mat.EnableKeyword("_NORMALMAP");
                    mat.SetTextureScale("_MainTex", tiling);
                    break;
            }''',
     '''        // tiling material (cargo barrier webbing: UV u runs in metres along the strap). v12: PSX, no normal map
        static Material MakeTiled(string name, string prefix, string pipe, Vector2 tiling, float smooth)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, Tex(prefix + "_BaseColor"), Color.white);
            var nrm = IsPsxTexture(prefix + "_") ? null : Tex(prefix + "_Normal");
            switch (pipe)
            {
                case "HDRP":
                    mat.SetTexture("_NormalMap", nrm);
                    mat.SetTextureScale("_BaseColorMap", tiling);
                    break;
                case "URP":
                    mat.SetTexture("_BumpMap", nrm);
                    if (nrm != null) mat.EnableKeyword("_NORMALMAP"); else mat.DisableKeyword("_NORMALMAP");
                    mat.SetTextureScale("_BaseMap", tiling);
                    break;
                default:
                    mat.SetTexture("_BumpMap", nrm);
                    if (nrm != null) mat.EnableKeyword("_NORMALMAP"); else mat.DisableKeyword("_NORMALMAP");
                    mat.SetTextureScale("_MainTex", tiling);
                    break;
            }'''),
]
for a, b in R:
    assert s.count(a) == 1, ('not found once', a[:80])
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)

# ------------------------------------------------------------------ atlas_texel.json
p = os.path.join(DST, 'Data', 'atlas_texel.json')
T = json.load(open(p))
SIZE = {'Cockpit': 512, 'Interior': 512, 'Floor': 512, 'Seats': 512, 'Fittings': 256}
for t in T:
    if t['atlas'] in SIZE:
        n = SIZE[t['atlas']]
        t['pxPerMetre'] = round(n / t['metresPerUV'], 1)
        t['detail'] = ''
        t['detailTiling'] = 0.0
        t['detailNormalScale'] = 0.0
        t['psx'] = True
        old = t.get('note', '')
        keep = 'the four seats share their islands (identical copies, the right ones mirrored); ' if t['atlas'] == 'Fittings' else ''
        t['note'] = keep + f'v12 edition 2: PSX {n} px (32 colours, ordered dither, shading and painted light baked in, ' \
                           f'no normal / detail map; edition 1: {2 * n} px); v10: 1024 px realistic; ' \
                           f'v9: {"2048" if t["atlas"] == "Fittings" else "4096"} px'
json.dump(T, open(p, 'w'), ensure_ascii=False, indent=None, separators=(', ', ': '))
subprocess.run([sys.executable, '/home/claude/plane/v12r2/build_docs12r2.py', DST], check=True)
print('package', DST, sum(len(f) for _, _, f in os.walk(DST)), 'files')
