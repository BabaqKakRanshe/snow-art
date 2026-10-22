#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace UtilityPlane.EditorTools
{
    /// <summary>First-import settings for the Utility Plane v6 model and textures (Assets/UtilityPlane/...).</summary>
    public class UtilityPlaneImport : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            if (!assetPath.Replace('\\', '/').Contains("/UtilityPlane/Textures/")) return;
            if (!assetImporter.importSettingsMissing) return;
            UtilityPlaneSetup.ApplyTextureSettings((TextureImporter)assetImporter, assetPath);
        }

        void OnPreprocessModel()
        {
            if (!assetPath.Replace('\\', '/').Contains("/UtilityPlane/Models/")) return;
            if (!assetImporter.importSettingsMissing) return;
            UtilityPlaneSetup.ApplyModelSettings((ModelImporter)assetImporter);
        }
    }

    /// <summary>
    /// Tools / Utility Plane / Build Materials + Prefabs:
    ///  - materials for Built-in, URP or HDRP (auto-detected), remapped onto the FBX by name;
    ///  - Prefabs/UtilityPlane.prefab: COL_* meshes become convex MeshColliders (renderers removed),
    ///    interaction volumes from Data/interaction_volumes.json become trigger BoxColliders on the "Interact" layer
    ///    with UtilityPlaneInteractable, UtilityPlaneRig is added;
    ///  - Prefabs/Cargo_CaseN.prefab for the six cargo cases.
    /// No Rigidbody is added: the vehicle and cargo systems own physics.
    /// </summary>
    public static class UtilityPlaneSetup
    {
        const string Root = "Assets/UtilityPlane";
        const string Fbx = Root + "/Models/UtilityPlane.fbx";

        public static void ApplyTextureSettings(TextureImporter ti, string path)
        {
            string n = Path.GetFileNameWithoutExtension(path);
            ti.maxTextureSize = n.Contains("Details") ? 2048 : (n.Contains("Webbing") || n.Contains("_Detail_")) ? 512 : 4096;
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            ti.textureType = TextureImporterType.Default;
            if (n.EndsWith("_Normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
            }
            else if (n.EndsWith("_MetallicSmoothness") || n.EndsWith("_MaskMap") || n.EndsWith("_AO"))
            {
                ti.sRGBTexture = false;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
            }
            else
            {
                ti.sRGBTexture = true;
                ti.alphaIsTransparency = false;
            }
        }

        public static void ApplyModelSettings(ModelImporter mi)
        {
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.importBlendShapes = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.addCollider = false;
            mi.isReadable = true;              // needed for convex MeshCollider cooking at runtime in builds
        }

        [MenuItem("Tools/Utility Plane/Build Materials + Prefabs")]
        public static void Build()
        {
            if (!(AssetImporter.GetAtPath(Fbx) is ModelImporter mi))
            {
                Debug.LogError($"[UtilityPlane] {Fbx} not found. Keep the folder at {Root}.");
                return;
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (!(AssetImporter.GetAtPath(p) is TextureImporter ti)) continue;
                ApplyTextureSettings(ti, p);
                ti.SaveAndReimport();
            }

            string pipe = DetectPipeline();
            EnsureFolder(Root, "Materials");
            EnsureFolder(Root, "Prefabs");
            if (pipe == "HDRP")
                foreach (var a in Atlases) MakeMaskMap(a);

            var texel = LoadTexel();
            var mats = new (string name, Material mat)[]
            {
                ("M_Airframe", MakeLit("M_Airframe", "T_Airframe", pipe, null)),
                ("M_Details", MakeLit("M_Details", "T_Details", pipe, null)),
                ("M_Cockpit", MakeLit("M_Cockpit", "T_Cockpit", pipe, FindTexel(texel, "Cockpit"))),
                ("M_Interior", MakeLit("M_Interior", "T_Interior", pipe, FindTexel(texel, "Interior"))),
                ("M_Floor", MakeLit("M_Floor", "T_Floor", pipe, FindTexel(texel, "Floor"))),
                ("M_Seats", MakeLit("M_Seats", "T_Seats", pipe, FindTexel(texel, "Seats"))),
                ("M_Gauges", MakeDecal("M_Gauges", pipe, 0.3f, "T_Gauges_Emission", Color.white)),   // matte print
                // v6: the atlas holds the unlit lens look, T_Displays_Emission the lit lamp (per-lamp MPB from the rig)
                ("M_Annunciator", MakeDecal("M_Annunciator", pipe, 0.8f, "T_Displays_Emission", Color.white)),
                ("M_RadioDisplay", MakeDecal("M_RadioDisplay", pipe, 0.7f, "T_Displays_Emission", Color.white)),
                ("M_Screen", MakeLens("M_Screen", pipe, new Color(0.012f, 0.016f, 0.016f), 0.85f)),
                ("M_Webbing", MakeTiled("M_Webbing", "T_Webbing", pipe, new Vector2(10f, 1f), 0.2f)),
                ("M_Glass", MakeGlass("M_Glass", pipe, new Color(0.85f, 0.92f, 0.92f, 0.12f))),
                ("M_GaugeGlass", MakeGlass("M_GaugeGlass", pipe, new Color(1f, 1f, 1f, 0.04f), 0.78f, false)),
                ("M_Light_Red", MakeLens("M_Light_Red", pipe, new Color(0.35f, 0.02f, 0.01f))),
                ("M_Light_Green", MakeLens("M_Light_Green", pipe, new Color(0.02f, 0.3f, 0.05f))),
                ("M_Light_White", MakeLens("M_Light_White", pipe, new Color(0.6f, 0.6f, 0.6f))),
                ("M_Light_Beacon", MakeLens("M_Light_Beacon", pipe, new Color(0.35f, 0.03f, 0.01f))),
                ("M_Light_Landing", MakeLens("M_Light_Landing", pipe, new Color(0.7f, 0.7f, 0.65f))),
                ("M_Light_Cabin", MakeLens("M_Light_Cabin", pipe, new Color(0.7f, 0.65f, 0.55f))),
            };

            ApplyModelSettings(mi);
            foreach (var (name, mat) in mats)
                mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), name), mat);
            mi.SaveAndReimport();
            foreach (var guid in AssetDatabase.FindAssets("SM_Cargo_ t:Model", new[] { Root + "/Models" }))
            {
                var cmi = (ModelImporter)AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(guid));
                ApplyModelSettings(cmi);
                cmi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_Details"),
                             mats.First(m => m.name == "M_Details").mat);
                cmi.SaveAndReimport();
            }

            BuildPlanePrefab();
            BuildCargoPrefabs();
            AssetDatabase.SaveAssets();
            Debug.Log($"[UtilityPlane] Done ({pipe}). Prefabs in {Root}/Prefabs");

            // files a v4 install leaves behind: nothing references them after this build
            var stale = new[] { Root + "/Materials/M_CargoNet.mat", Root + "/Textures/T_CargoNet_BCA.png" }
                .Concat(pipe == "HDRP" ? new string[0] : Atlases.Select(a => $"{Root}/Textures/T_{a}_MaskMap.png"))
                .Where(File.Exists).ToArray();
            if (stale.Length > 0)
                Debug.Log("[UtilityPlane] Unused files from an older version (safe to delete): " + string.Join(", ", stale));
        }

        // ------------------------------------------------------------------ prefabs
#pragma warning disable 0649 // filled by JsonUtility
        [Serializable] class Vol { public string id, parent, kind, label; public float[] center, halfExtents; }
        [Serializable] class VolList { public Vol[] items; }
        [Serializable] class Texel
        {
            public string atlas, material, detail;
            public float metresPerUV, pxPerMetre, areaM2, detailTiling, detailNormalScale;
        }
        [Serializable] class TexelList { public Texel[] items; }

        static readonly string[] Atlases = { "Airframe", "Details", "Cockpit", "Interior", "Floor", "Seats" };

        static Texel[] LoadTexel()
        {
            string p = Root + "/Data/atlas_texel.json";
            if (!File.Exists(p)) return new Texel[0];
            var list = JsonUtility.FromJson<TexelList>("{\"items\":" + File.ReadAllText(p) + "}");
            return list != null && list.items != null ? list.items : new Texel[0];
        }

        static Texel FindTexel(Texel[] all, string atlas) => all.FirstOrDefault(t => t.atlas == atlas);
#pragma warning restore 0649

        static void BuildPlanePrefab()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            var all = inst.GetComponentsInChildren<Transform>(true);

            // collider proxies
            int cols = 0;
            foreach (var t in all.Where(t => t.name.StartsWith("COL_")))
            {
                var mf = t.GetComponent<MeshFilter>();
                if (mf == null) continue;
                var mc = t.gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = mf.sharedMesh;
                mc.convex = true;
                // the propeller disk proxy must not spin with the blades inside the vehicle body
                if (t.name == "COL_Propeller") t.SetParent(inst.transform, true);
                UnityEngine.Object.DestroyImmediate(t.GetComponent<MeshRenderer>());
                UnityEngine.Object.DestroyImmediate(mf);
                cols++;
            }

            // interaction volumes
            int layer = EnsureLayer("Interact");
            string json = File.ReadAllText(Root + "/Data/interaction_volumes.json");
            var list = JsonUtility.FromJson<VolList>("{\"items\":" + json + "}");
            int vols = 0;
            foreach (var v in list.items)
            {
                var parent = all.FirstOrDefault(t => t.name == v.parent);
                if (parent == null) { Debug.LogWarning($"[UtilityPlane] parent {v.parent} not found for {v.id}"); continue; }
                var go = new GameObject("IV_" + v.id);
                go.transform.SetParent(parent, false);
                if (layer >= 0) go.layer = layer;
                var bc = go.AddComponent<BoxCollider>();
                bc.isTrigger = true;
                bc.center = new Vector3(v.center[0], v.center[1], v.center[2]);
                bc.size = 2f * new Vector3(v.halfExtents[0], v.halfExtents[1], v.halfExtents[2]);
                var it = go.AddComponent<UtilityPlaneInteractable>();
                it.id = v.id; it.kind = v.kind; it.label = v.label;
                vols++;
            }

            int lights = UtilityPlaneRig.BuildLights(inst.transform, DetectPipeline() == "HDRP");
            if (inst.GetComponent<UtilityPlaneRig>() == null) inst.AddComponent<UtilityPlaneRig>();
            string path = Root + "/Prefabs/UtilityPlane.prefab";
            PrefabUtility.SaveAsPrefabAsset(inst, path);
            UnityEngine.Object.DestroyImmediate(inst);
            Debug.Log($"[UtilityPlane] {path}: {cols} convex colliders, {vols} interaction volumes, {lights} lights");
        }

        // Adds a user layer if it is missing (first free slot from 8). Returns -1 if all slots are taken.
        static int EnsureLayer(string name)
        {
            int existing = LayerMask.NameToLayer(name);
            if (existing >= 0) return existing;
            var assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset");
            if (assets == null || assets.Length == 0) return -1;
            var so = new SerializedObject(assets[0]);
            var layers = so.FindProperty("layers");
            for (int i = 8; i < layers.arraySize; i++)
            {
                var sp = layers.GetArrayElementAtIndex(i);
                if (!string.IsNullOrEmpty(sp.stringValue)) continue;
                sp.stringValue = name;
                so.ApplyModifiedProperties();
                Debug.Log($"[UtilityPlane] Added layer \"{name}\" at index {i}. Turn its collisions off in Physics settings.");
                return i;
            }
            Debug.LogWarning($"[UtilityPlane] No free layer for \"{name}\"; volumes stay on Default.");
            return -1;
        }

        static void BuildCargoPrefabs()
        {
            for (int i = 1; i <= 6; i++)
            {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SM_Cargo_Case{i}.fbx");
                if (model == null) continue;
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                var mf = inst.GetComponentInChildren<MeshFilter>();
                if (mf != null)
                {
                    var mc = mf.gameObject.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh;
                    mc.convex = true;
                }
                PrefabUtility.SaveAsPrefabAsset(inst, $"{Root}/Prefabs/Cargo_Case{i}.prefab");
                UnityEngine.Object.DestroyImmediate(inst);
            }
        }

        // ------------------------------------------------------------------ materials
        static string DetectPipeline()
        {
            RenderPipelineAsset rp = GraphicsSettings.currentRenderPipeline;
            if (rp == null) return "BuiltIn";
            return rp.GetType().Name.Contains("HDRenderPipeline") ? "HDRP" : "URP";
        }

        static void EnsureFolder(string parent, string name)
        {
            if (!AssetDatabase.IsValidFolder(parent + "/" + name)) AssetDatabase.CreateFolder(parent, name);
        }

        static Texture2D Tex(string name) => AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/{name}.png");

        static Shader LitShader(string pipe) =>
            pipe == "HDRP" ? Shader.Find("HDRP/Lit") :
            pipe == "URP" ? Shader.Find("Universal Render Pipeline/Lit") : Shader.Find("Standard");

        static Material GetOrCreate(string name, string pipe)
        {
            string path = $"{Root}/Materials/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var sh = LitShader(pipe);
            if (mat == null)
            {
                mat = new Material(sh);
                AssetDatabase.CreateAsset(mat, path);
            }
            else mat.shader = sh;
            return mat;
        }

        static void SetBase(Material m, string pipe, Texture2D tex, Color col)
        {
            string map = pipe == "HDRP" ? "_BaseColorMap" : pipe == "URP" ? "_BaseMap" : "_MainTex";
            string c = pipe == "BuiltIn" ? "_Color" : "_BaseColor";
            if (tex != null) m.SetTexture(map, tex);
            m.SetColor(c, col);
        }

        static void SetEmission(Material m, string pipe, Texture2D map)
        {
            if (pipe == "HDRP")
            {
                if (map != null) m.SetTexture("_EmissiveColorMap", map);
                m.SetColor("_EmissiveColor", Color.black);
            }
            else
            {
                if (map != null) m.SetTexture("_EmissionMap", map);
                m.SetColor("_EmissionColor", Color.black);
                m.EnableKeyword("_EMISSION");
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
        }

        static void SetSmoothness(Material m, string pipe, float s)
        {
            m.SetFloat(pipe == "BuiltIn" ? "_Glossiness" : "_Smoothness", s);
        }

        static Material MakeLit(string name, string prefix, string pipe, Texel detail)
        {
            Material mat = GetOrCreate(name, pipe);
            Texture2D bc = Tex(prefix + "_BaseColor"), nrm = Tex(prefix + "_Normal"),
                ms = Tex(prefix + "_MetallicSmoothness"), ao = Tex(prefix + "_AO"), mask = Tex(prefix + "_MaskMap");
            SetBase(mat, pipe, bc, Color.white);
            switch (pipe)
            {
                case "URP":
                    mat.SetTexture("_BumpMap", nrm); mat.SetFloat("_BumpScale", 1f); mat.EnableKeyword("_NORMALMAP");
                    mat.SetTexture("_MetallicGlossMap", ms); mat.SetFloat("_Smoothness", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f); mat.EnableKeyword("_METALLICSPECGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", ao); mat.SetFloat("_OcclusionStrength", 1f);
                    mat.EnableKeyword("_OCCLUSIONMAP");
                    break;
                case "HDRP":
                    mat.SetTexture("_NormalMap", nrm);
                    mat.SetTexture("_MaskMap", mask);
                    mat.SetFloat("_MetallicRemapMin", 0f); mat.SetFloat("_MetallicRemapMax", 1f);
                    mat.SetFloat("_SmoothnessRemapMin", 0f); mat.SetFloat("_SmoothnessRemapMax", 1f);
                    mat.SetFloat("_AORemapMin", 0f); mat.SetFloat("_AORemapMax", 1f);
                    break;
                default:
                    mat.SetTexture("_BumpMap", nrm); mat.EnableKeyword("_NORMALMAP");
                    mat.SetTexture("_MetallicGlossMap", ms); mat.SetFloat("_GlossMapScale", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f); mat.EnableKeyword("_METALLICGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", ao); mat.SetFloat("_OcclusionStrength", 1f);
                    break;
            }
            if (detail != null && !string.IsNullOrEmpty(detail.detail) && pipe != "HDRP") SetDetail(mat, pipe, detail);
            Validate(mat, pipe);
            return mat;
        }

        // micro grain on top of the baked atlas (URP / Built-in detail maps, x2 albedo + normal, tiled on UV0;
        // the atlases have uniform texel density, Data/atlas_texel.json gives the tiling). HDRP: not set.
        static void SetDetail(Material m, string pipe, Texel d)
        {
            var alb = Tex("T_Detail_" + d.detail + "_Albedo");
            var nrm = Tex("T_Detail_" + d.detail + "_Normal");
            if (alb == null || nrm == null || d.detailTiling <= 0f) return;
            m.SetTexture("_DetailAlbedoMap", alb);
            m.SetTexture("_DetailNormalMap", nrm);
            m.SetFloat("_DetailNormalMapScale", d.detailNormalScale);
            if (pipe == "URP") m.SetFloat("_DetailAlbedoMapScale", 1f);
            m.SetTextureScale("_DetailAlbedoMap", new Vector2(d.detailTiling, d.detailTiling));
            m.EnableKeyword("_DETAIL_MULX2");
        }

        // gauge faces / placards / lightplates: printed atlas; emission map = backlit markings only (driven per renderer
        // by UtilityPlaneRig). Annunciator lamps and the radio faces (Display_Radio) use T_Displays_Emission: the lit
        // lamp picture and the backlit radio legends.
        static Material MakeDecal(string name, string pipe, float smooth, string emissionMap, Color baseTint)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, Tex("T_Gauges_BC"), baseTint);
            SetSmoothness(mat, pipe, smooth);
            SetEmission(mat, pipe, Tex(emissionMap));
            Validate(mat, pipe);
            return mat;
        }

        // tiling material (cargo barrier webbing: UV u runs in metres along the strap)
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
            }
            mat.SetFloat("_Metallic", 0f);
            SetSmoothness(mat, pipe, smooth);
            Validate(mat, pipe);
            return mat;
        }

        static Material MakeLens(string name, string pipe, Color tint, float smooth = 0.9f)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, null, tint);
            SetSmoothness(mat, pipe, smooth);
            SetEmission(mat, pipe, null);
            Validate(mat, pipe);
            return mat;
        }

        // reflections = false (gauge glass, v6): no sun glints and no probe reflections, so the dials stay readable
        // against a bright windshield; switch them back on in the material if you want glare.
        static Material MakeGlass(string name, string pipe, Color col, float smooth = 0.95f, bool reflections = true)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, null, col);
            SetSmoothness(mat, pipe, smooth);
            if (!reflections && pipe != "HDRP")
            {
                mat.SetFloat("_SpecularHighlights", 0f);
                mat.SetFloat(pipe == "URP" ? "_EnvironmentReflections" : "_GlossyReflections", 0f);
                mat.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                mat.EnableKeyword(pipe == "URP" ? "_ENVIRONMENTREFLECTIONS_OFF" : "_GLOSSYREFLECTIONS_OFF");
            }
            else if (!reflections) SetSmoothness(mat, pipe, 0.3f);      // HDRP: no per-material toggle, blur them
            switch (pipe)
            {
                case "URP":
                    mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f);
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                    mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
                    mat.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_ZWrite", 0f); mat.SetFloat("_Cull", 0f);
                    mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
                case "HDRP":
                    mat.SetFloat("_SurfaceType", 1f); mat.SetFloat("_BlendMode", 0f);
                    mat.SetFloat("_DoubleSidedEnable", 1f);
                    break;
                default:
                    mat.SetFloat("_Mode", 3f);
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetInt("_SrcBlend", (int)BlendMode.One);
                    mat.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                    mat.SetInt("_ZWrite", 0);
                    mat.DisableKeyword("_ALPHATEST_ON"); mat.DisableKeyword("_ALPHABLEND_ON");
                    mat.EnableKeyword("_ALPHAPREMULTIPLY_ON");
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
            }
            Validate(mat, pipe);
            return mat;
        }

        // HDRP mask map: R metallic, G AO, B detail (0), A smoothness
        static void MakeMaskMap(string atlas)
        {
            string ms = $"{Root}/Textures/T_{atlas}_MetallicSmoothness.png", ao = $"{Root}/Textures/T_{atlas}_AO.png";
            string outPath = $"{Root}/Textures/T_{atlas}_MaskMap.png";
            if (!File.Exists(ms) || !File.Exists(ao)) return;
            if (File.Exists(outPath) && File.GetLastWriteTimeUtc(outPath) >= File.GetLastWriteTimeUtc(ms) &&
                File.GetLastWriteTimeUtc(outPath) >= File.GetLastWriteTimeUtc(ao)) return;      // up to date (v4 maps get rebuilt)
            var a = new Texture2D(2, 2); a.LoadImage(File.ReadAllBytes(ms));
            var b = new Texture2D(2, 2); b.LoadImage(File.ReadAllBytes(ao));
            if (a.width != b.width || a.height != b.height) { Debug.LogWarning($"[UtilityPlane] size mismatch {atlas}"); return; }
            Color32[] pa = a.GetPixels32(), pb = b.GetPixels32();
            var o = new Color32[pa.Length];
            for (int i = 0; i < pa.Length; i++) o[i] = new Color32(pa[i].r, pb[i].r, 0, pa[i].a);
            var t = new Texture2D(a.width, a.height, TextureFormat.RGBA32, false, true);
            t.SetPixels32(o);
            File.WriteAllBytes(outPath, t.EncodeToPNG());
            AssetDatabase.ImportAsset(outPath);
            if (AssetImporter.GetAtPath(outPath) is TextureImporter ti) { ApplyTextureSettings(ti, outPath); ti.SaveAndReimport(); }
        }

        // URP and HDRP set their shader keywords in their own editor code. Call it through reflection so this file
        // compiles in any pipeline (no package references). Built-in keywords are set above.
        static void Validate(Material m, string pipe)
        {
            if (pipe == "HDRP")
                InvokeStatic("UnityEditor.Rendering.HighDefinition.HDShaderUtils", "ResetMaterialKeywords", m);
            else if (pipe == "URP")
            {
                if (m.shader != null && m.shader.name == "Universal Render Pipeline/Lit")
                    InvokeStatic("UnityEditor.Rendering.Universal.ShaderGUI.LitGUI", "SetMaterialKeywords", m);
                InvokeStatic("UnityEditor.BaseShaderGUI", "SetMaterialKeywords", m);
            }
            EditorUtility.SetDirty(m);
        }

        static void InvokeStatic(string typeName, string method, Material m)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t = asm.GetType(typeName);
                if (t == null) continue;
                foreach (var mi in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static))
                {
                    var ps = mi.GetParameters();
                    if (mi.Name != method || ps.Length == 0 || ps[0].ParameterType != typeof(Material)) continue;
                    if (ps.Skip(1).Any(p => !p.IsOptional && p.ParameterType.IsValueType)) continue;
                    var args = new object[ps.Length];
                    args[0] = m;
                    for (int i = 1; i < ps.Length; i++) args[i] = ps[i].HasDefaultValue ? ps[i].DefaultValue : null;
                    try { mi.Invoke(null, args); }
                    catch (Exception e) { Debug.LogWarning($"[UtilityPlane] {typeName}.{method}: {e.InnerException?.Message ?? e.Message}"); }
                    return;
                }
            }
        }
    }
}
#endif
