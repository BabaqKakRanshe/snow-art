// Настройка импорта, материалов и префаба для ассета BushPlane.
//
// Меню: Tools -> Bush Plane -> Setup Materials + Prefab
//
// Скрипт нужен потому, что настройки импортёра живут в .meta, а FBX и PNG
// приходят извне Unity. Прогонять их руками по десятку галочек — источник
// ошибок, из которых две тихие и дорогие: карта нормалей, импортированная как
// обычная текстура в sRGB, и маска, у которой гладкость умножается на _Smoothness
// материала и потому гаснет.

using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BushPlaneAsset.EditorTools
{
    public static class BushPlaneSetup
    {
        const string Root = "Assets/BushPlane";
        const string TexDir = Root + "/Textures";
        const string ModelPath = Root + "/Models/BushPlane.fbx";
        const string MatDir = Root + "/Materials";
        const string PrefabDir = Root + "/Prefabs";

        const string TexBase = TexDir + "/T_BushPlane_BaseColor.png";
        const string TexMask = TexDir + "/T_BushPlane_Mask.png";
        const string TexNormal = TexDir + "/T_BushPlane_Normal.png";

        // Имена ровно как в Blender: по ним ModelImporter переназначает материалы.
        const string MatBody = "M_BushPlane_Body";
        const string MatGlass = "M_BushPlane_Glass";
        const string MatLights = "M_BushPlane_Lights";

        enum Pipeline { BuiltIn, URP, HDRP }

        [MenuItem("Tools/Bush Plane/Setup Materials + Prefab")]
        public static void Run()
        {
            if (!File.Exists(ModelPath))
            {
                Debug.LogError($"[BushPlane] не найден {ModelPath}. " +
                               "Скопируй папку Assets/BushPlane целиком.");
                return;
            }

            var pipe = DetectPipeline();
            Debug.Log($"[BushPlane] пайплайн: {pipe}");

            EnsureFolder(MatDir);
            EnsureFolder(PrefabDir);

            ConfigureTextures();

            var body = CreateBodyMaterial(pipe);
            var glass = CreateGlassMaterial(pipe);
            var lights = CreateLightsMaterial(pipe);

            ConfigureModel(body, glass, lights);
            BuildPrefab();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[BushPlane] готово: материалы, импорт и префаб настроены.");
        }

        static Pipeline DetectPipeline()
        {
            var rp = GraphicsSettings.currentRenderPipeline;
            if (rp == null) return Pipeline.BuiltIn;
            var n = rp.GetType().Name;
            if (n.Contains("HDRenderPipelineAsset")) return Pipeline.HDRP;
            if (n.Contains("Universal")) return Pipeline.URP;
            return Pipeline.BuiltIn;
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path).Replace('\\', '/');
            var leaf = Path.GetFileName(path);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        // ------------------------------------------------------------------
        // Текстуры
        // ------------------------------------------------------------------

        static void ConfigureTextures()
        {
            SetTexture(TexBase, sRGB: true, normal: false);
            // Маска — данные, а не цвет: R metallic, G occlusion, A smoothness.
            // sRGB на ней исказил бы все три канала.
            SetTexture(TexMask, sRGB: false, normal: false, alphaIsTransparency: false);
            SetTexture(TexNormal, sRGB: false, normal: true);
        }

        static void SetTexture(string path, bool sRGB, bool normal, bool alphaIsTransparency = false)
        {
            var ti = AssetImporter.GetAtPath(path) as TextureImporter;
            if (ti == null)
            {
                Debug.LogWarning($"[BushPlane] нет текстуры {path}");
                return;
            }
            ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = sRGB;
            ti.alphaIsTransparency = alphaIsTransparency;
            ti.alphaSource = TextureImporterAlphaSource.FromInput;
            ti.mipmapEnabled = true;
            ti.wrapMode = TextureWrapMode.Clamp;   // атлас, не тайл
            ti.filterMode = FilterMode.Bilinear;
            ti.anisoLevel = 4;
            // Карты печатаются в 4096: при 2048 импортёр тихо ужал бы их вдвое,
            // и вся заклёпочная мелочь, ради которой атлас и подняли, пропала бы.
            ti.maxTextureSize = 4096;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            if (normal)
            {
                // Blender печёт OpenGL-формат (зелёный вверх) — ровно то, что
                // ждёт Unity. Переворачивать канал не нужно.
                ti.flipGreenChannel = false;
            }
            ti.SaveAndReimport();
        }

        // ------------------------------------------------------------------
        // Материалы
        // ------------------------------------------------------------------

        static Shader LitShader(Pipeline p)
        {
            string name = p switch
            {
                Pipeline.URP => "Universal Render Pipeline/Lit",
                Pipeline.HDRP => "HDRP/Lit",
                _ => "Standard",
            };
            var s = Shader.Find(name);
            if (s == null)
            {
                Debug.LogWarning($"[BushPlane] шейдер '{name}' не найден, беру Standard");
                s = Shader.Find("Standard");
            }
            return s;
        }

        static Material GetOrCreate(string name, Shader shader)
        {
            var path = $"{MatDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(shader);
                AssetDatabase.CreateAsset(m, path);
            }
            else if (m.shader != shader)
            {
                m.shader = shader;
            }
            return m;
        }

        static Material CreateBodyMaterial(Pipeline pipe)
        {
            var m = GetOrCreate(MatBody, LitShader(pipe));
            var baseTex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexBase);
            var maskTex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexMask);
            var nrmTex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexNormal);

            if (pipe == Pipeline.HDRP)
            {
                SetTex(m, "_BaseColorMap", baseTex);
                SetTex(m, "_NormalMap", nrmTex);
                SetTex(m, "_MaskMap", maskTex);
                m.SetFloat("_Smoothness", 1f);
                m.EnableKeyword("_NORMALMAP");
                m.EnableKeyword("_MASKMAP");
                return m;
            }

            SetTex(m, "_BaseMap", baseTex);
            SetTex(m, "_MainTex", baseTex);          // Built-in
            SetTex(m, "_BumpMap", nrmTex);
            // Одна RGBA-текстура работает и как MetallicGloss, и как Occlusion:
            // URP берёт из неё R (metallic), A (smoothness) и G (occlusion).
            SetTex(m, "_MetallicGlossMap", maskTex);
            SetTex(m, "_OcclusionMap", maskTex);

            // Ключевой момент: URP умножает альфу карты на _Smoothness. При
            // значении по умолчанию вся карта гладкости схлопнулась бы в почти
            // матовую поверхность.
            m.SetFloat("_Smoothness", 1f);
            m.SetFloat("_GlossMapScale", 1f);
            m.SetFloat("_Metallic", 1f);
            m.SetFloat("_OcclusionStrength", 1f);
            m.SetFloat("_SmoothnessTextureChannel", 0f);   // 0 = альфа металлической карты
            m.SetFloat("_BumpScale", 1f);

            // Без включённых ключевых слов SetTexture ничего не даёт: ветки
            // шейдера просто не компилируются и карты молча игнорируются.
            m.EnableKeyword("_METALLICSPECGLOSSMAP");
            m.EnableKeyword("_NORMALMAP");
            m.EnableKeyword("_OCCLUSIONMAP");
            return m;
        }

        static Material CreateGlassMaterial(Pipeline pipe)
        {
            var m = GetOrCreate(MatGlass, LitShader(pipe));
            // Альфа 0.86 глушила остекление: салон за ним не читался.
            var c = new Color(0.045f, 0.055f, 0.065f, 0.58f);
            SetColor(m, "_BaseColor", c);
            SetColor(m, "_Color", c);
            m.SetFloat("_Smoothness", 0.92f);
            m.SetFloat("_Metallic", 0.0f);

            if (pipe == Pipeline.URP)
            {
                m.SetFloat("_Surface", 1f);          // Transparent
                m.SetFloat("_Blend", 0f);            // Alpha
                m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f);
                m.SetFloat("_Cull", (float)UnityEngine.Rendering.CullMode.Back);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                m.DisableKeyword("_ALPHATEST_ON");
                m.renderQueue = (int)RenderQueue.Transparent;
            }
            else if (pipe == Pipeline.BuiltIn)
            {
                m.SetFloat("_Mode", 3f);             // Transparent
                m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
                m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                m.SetInt("_ZWrite", 0);
                m.EnableKeyword("_ALPHABLEND_ON");
                m.renderQueue = (int)RenderQueue.Transparent;
            }
            return m;
        }

        static Material CreateLightsMaterial(Pipeline pipe)
        {
            var m = GetOrCreate(MatLights, LitShader(pipe));
            var c = new Color(0.42f, 0.03f, 0.03f, 1f);
            SetColor(m, "_BaseColor", c);
            SetColor(m, "_Color", c);
            m.SetFloat("_Smoothness", 0.7f);
            var emis = new Color(1.0f, 0.06f, 0.05f) * 3.2f;
            SetColor(m, "_EmissionColor", emis);
            m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            return m;
        }

        static void SetTex(Material m, string prop, Texture t)
        {
            if (t != null && m.HasProperty(prop)) m.SetTexture(prop, t);
        }

        static void SetColor(Material m, string prop, Color c)
        {
            if (m.HasProperty(prop)) m.SetColor(prop, c);
        }

        // ------------------------------------------------------------------
        // Модель
        // ------------------------------------------------------------------

        static void ConfigureModel(Material body, Material glass, Material lights)
        {
            var mi = AssetImporter.GetAtPath(ModelPath) as ModelImporter;
            if (mi == null) { Debug.LogError("[BushPlane] FBX не импортирован"); return; }

            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.useFileUnits = true;
            // Экспортёр уже запёк преобразование осей в вершины. Включённая
            // галка повернула бы модель второй раз.
            mi.bakeAxisConversion = false;
            mi.importNormals = ModelImporterNormals.Import;
            // Касательные считает Unity: MikkTSpace — тот же базис, против
            // которого Blender пёк карту нормалей.
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.importBlendShapes = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importAnimation = false;
            mi.generateSecondaryUV = true;
            mi.weldVertices = true;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.isReadable = false;

            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.materialLocation = ModelImporterMaterialLocation.External;
            Remap(mi, body, "M_BushPlane_Body");
            Remap(mi, glass, "M_BushPlane_Glass");
            Remap(mi, lights, "M_BushPlane_Lights");

            mi.SaveAndReimport();
        }

        static void Remap(ModelImporter mi, Material mat, string blenderName)
        {
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), blenderName), mat);
        }

        // ------------------------------------------------------------------
        // Префаб
        // ------------------------------------------------------------------

        static void BuildPrefab()
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (model == null) { Debug.LogError("[BushPlane] модель не загрузилась"); return; }

            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            go.name = "BushPlane";
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);

            var rig = go.GetComponent<BushPlaneAsset.BushPlaneRig>();
            if (rig == null) rig = go.AddComponent<BushPlaneAsset.BushPlaneRig>();
            rig.AutoBind();

            // Коробчатый коллайдер по габаритам — для пропа этого достаточно,
            // а невыпуклый MeshCollider всё равно не работает с Rigidbody.
            var box = go.GetComponent<BoxCollider>();
            if (box == null) box = go.AddComponent<BoxCollider>();
            var bounds = new Bounds(go.transform.position, Vector3.zero);
            bool first = true;
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                if (first) { bounds = r.bounds; first = false; }
                else bounds.Encapsulate(r.bounds);
            }
            box.center = go.transform.InverseTransformPoint(bounds.center);
            box.size = bounds.size;

            var path = $"{PrefabDir}/BushPlane.prefab";
            PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
            Debug.Log($"[BushPlane] префаб: {path}");
        }
    }
}
