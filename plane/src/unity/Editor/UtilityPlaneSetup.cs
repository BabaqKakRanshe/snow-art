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
    /// <summary>First-import settings for the Utility Plane model and its textures.</summary>
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

    public static class UtilityPlaneSetup
    {
        const string Root = "Assets/UtilityPlane";
        const string Fbx = Root + "/Models/UtilityPlane.fbx";

        public static void ApplyTextureSettings(TextureImporter ti, string path)
        {
            string n = Path.GetFileNameWithoutExtension(path);
            ti.maxTextureSize = n.Contains("Airframe") ? 4096 : 2048;
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            if (n.EndsWith("_Normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
            }
            else if (n.EndsWith("_MetallicSmoothness") || n.EndsWith("_MaskMap") || n.EndsWith("_AO"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
            }
            else
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = true;
            }
        }

        public static void ApplyModelSettings(ModelImporter mi)
        {
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
        }

        [MenuItem("Tools/Utility Plane/Create Materials + Prefab")]
        public static void Setup()
        {
            var mi = AssetImporter.GetAtPath(Fbx) as ModelImporter;
            if (mi == null)
            {
                Debug.LogError($"[UtilityPlane] {Fbx} not found. Keep the folder at Assets/UtilityPlane.");
                return;
            }

            // Make sure texture import settings are right even if textures were imported before this script compiled.
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti == null) continue;
                ApplyTextureSettings(ti, p);
                ti.SaveAndReimport();
            }

            string pipe = DetectPipeline();
            EnsureFolder(Root, "Materials");
            EnsureFolder(Root, "Prefabs");
            Material mA = MakeLit("M_Airframe", "T_Airframe", pipe);
            Material mD = MakeLit("M_Details", "T_Details", pipe);
            Material mL = MakeLights(pipe);

            ApplyModelSettings(mi);
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_Airframe"), mA);
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_Details"), mD);
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_Lights"), mL);
            mi.SaveAndReimport();

            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
            var rig = inst.GetComponent<UtilityPlaneRig>();
            if (rig == null) rig = inst.AddComponent<UtilityPlaneRig>();
            rig.AutoAssign();
            string prefabPath = Root + "/Prefabs/UtilityPlane.prefab";
            PrefabUtility.SaveAsPrefabAsset(inst, prefabPath);
            UnityEngine.Object.DestroyImmediate(inst);
            AssetDatabase.SaveAssets();
            Selection.activeObject = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            Debug.Log($"[UtilityPlane] Done ({pipe}). Prefab: {prefabPath}");
        }

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

        static Texture2D Tex(string name) =>
            AssetDatabase.LoadAssetAtPath<Texture2D>($"{Root}/Textures/{name}.png");

        static Material GetOrCreate(string name, Shader sh)
        {
            string path = $"{Root}/Materials/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(sh);
                AssetDatabase.CreateAsset(mat, path);
            }
            else mat.shader = sh;
            return mat;
        }

        static Shader LitShader(string pipe) =>
            pipe == "HDRP" ? Shader.Find("HDRP/Lit") :
            pipe == "URP" ? Shader.Find("Universal Render Pipeline/Lit") : Shader.Find("Standard");

        static Material MakeLit(string name, string prefix, string pipe)
        {
            Material mat = GetOrCreate(name, LitShader(pipe));
            Texture2D bc = Tex(prefix + "_BaseColor"), nrm = Tex(prefix + "_Normal"),
                ms = Tex(prefix + "_MetallicSmoothness"), ao = Tex(prefix + "_AO"), mask = Tex(prefix + "_MaskMap");
            switch (pipe)
            {
                case "URP":
                    mat.SetTexture("_BaseMap", bc);
                    mat.SetColor("_BaseColor", Color.white);
                    mat.SetTexture("_BumpMap", nrm);
                    mat.SetFloat("_BumpScale", 1f);
                    mat.EnableKeyword("_NORMALMAP");
                    mat.SetTexture("_MetallicGlossMap", ms);
                    mat.SetFloat("_Smoothness", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f);
                    mat.EnableKeyword("_METALLICSPECGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", ao);
                    mat.SetFloat("_OcclusionStrength", 1f);
                    mat.EnableKeyword("_OCCLUSIONMAP");
                    break;
                case "HDRP":
                    mat.SetTexture("_BaseColorMap", bc);
                    mat.SetColor("_BaseColor", Color.white);
                    mat.SetTexture("_NormalMap", nrm);
                    mat.SetTexture("_MaskMap", mask);
                    mat.SetFloat("_MetallicRemapMin", 0f); mat.SetFloat("_MetallicRemapMax", 1f);
                    mat.SetFloat("_SmoothnessRemapMin", 0f); mat.SetFloat("_SmoothnessRemapMax", 1f);
                    mat.SetFloat("_AORemapMin", 0f); mat.SetFloat("_AORemapMax", 1f);
                    HdrpValidate(mat);
                    break;
                default:
                    mat.SetTexture("_MainTex", bc);
                    mat.SetColor("_Color", Color.white);
                    mat.SetTexture("_BumpMap", nrm);
                    mat.EnableKeyword("_NORMALMAP");
                    mat.SetTexture("_MetallicGlossMap", ms);
                    mat.SetFloat("_GlossMapScale", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f);
                    mat.EnableKeyword("_METALLICGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", ao);
                    mat.SetFloat("_OcclusionStrength", 1f);
                    break;
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Material MakeLights(string pipe)
        {
            Material mat = GetOrCreate("M_Lights", LitShader(pipe));
            var red = new Color(0.9f, 0.03f, 0.02f);
            if (pipe == "HDRP")
            {
                mat.SetColor("_BaseColor", red);
                mat.SetColor("_EmissiveColor", new Color(1f, 0.04f, 0.02f) * 300f);
                HdrpValidate(mat);
            }
            else
            {
                mat.SetColor(pipe == "URP" ? "_BaseColor" : "_Color", red);
                mat.SetColor("_EmissionColor", new Color(1f, 0.04f, 0.02f) * 4f);
                mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                mat.SetFloat(pipe == "URP" ? "_Smoothness" : "_Glossiness", 0.85f);
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        // HDRP sets its keywords itself; call it via reflection so this file compiles without the HDRP package.
        static void HdrpValidate(Material m)
        {
            Type t = AppDomain.CurrentDomain.GetAssemblies()
                .Select(a => a.GetType("UnityEditor.Rendering.HighDefinition.HDShaderUtils"))
                .FirstOrDefault(x => x != null);
            MethodInfo reset = t?.GetMethod("ResetMaterialKeywords", BindingFlags.Public | BindingFlags.Static,
                null, new[] { typeof(Material) }, null);
            reset?.Invoke(null, new object[] { m });
        }
    }
}
#endif
