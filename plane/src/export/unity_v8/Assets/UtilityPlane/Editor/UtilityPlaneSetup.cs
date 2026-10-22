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
    /// <summary>First-import settings for the Utility Plane v8 model and textures (Assets/UtilityPlane/...).</summary>
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
    ///    with UtilityPlaneInteractable, UtilityPlaneRig is added; v7: small parts cast no shadows;
    ///    v8: two LODGroups from Data/lod.json (Exterior on the root, Cockpit on the Cockpit object);
    ///  - Prefabs/Cargo_CaseN.prefab for the six cargo cases; v7: StepLadder.prefab and PlaneKey.prefab.
    /// v8 materials: M_Airframe (fuselage, doors, fin, dorsal, struts) and M_Wing (wing, flaps, ailerons, horizontal
    /// tail), both with the Paint detail map (URP / Built-in).
    /// No Rigidbody is added: the vehicle and cargo systems own physics.
    /// </summary>
    public static class UtilityPlaneSetup
    {
        const string Root = "Assets/UtilityPlane";
        const string Fbx = Root + "/Models/UtilityPlane.fbx";

        public static void ApplyTextureSettings(TextureImporter ti, string path)
        {
            string n = Path.GetFileNameWithoutExtension(path);
            ti.maxTextureSize = (n.Contains("Webbing") || n.Contains("_Detail_") || n.StartsWith("T_Prop")) ? 512 :
                                n.StartsWith("T_GlassFog") ? 1024 : 4096;
            ti.mipmapEnabled = true;
            ti.anisoLevel = 4;
            ti.textureType = TextureImporterType.Default;
            if (n.EndsWith("_Normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
            }
            else if (n.EndsWith("_MaskMap") || n.EndsWith("_MetallicSmoothness") || n.EndsWith("_AO") || n.StartsWith("T_GlassFog") ||
                     n.EndsWith("_DetailMask"))
            {
                ti.sRGBTexture = false;                  // data: metallic / AO / detail / smoothness, fog order + density
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
            }
            else if (n.Contains("_Detail_") && n.EndsWith("_Albedo"))
            {
                // detail albedo x2 (128 = no change). URP Lit samples it raw and needs it linear (as sRGB it would
                // darken the surface to ~0.43x); Built-in Standard expects sRGB (compensated by unity_ColorSpaceDouble).
                ti.sRGBTexture = DetectPipeline() != "URP";
            }
            else
            {
                ti.sRGBTexture = true;
                ti.alphaIsTransparency = n.StartsWith("T_Prop");
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
            foreach (var guid in AssetDatabase.FindAssets("t:Texture", new[] { Root + "/Textures" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (!(AssetImporter.GetAtPath(p) is TextureImporter ti)) continue;
                ApplyTextureSettings(ti, p);
                ti.SaveAndReimport();
            }

            string pipe = DetectPipeline();
            EnsureFolder(Root, "Materials");
            EnsureFolder(Root, "Prefabs");

            var texel = LoadTexel();
            var mats = new (string name, Material mat)[]
            {
                ("M_Airframe", MakeLit("M_Airframe", "T_Airframe", pipe, FindTexel(texel, "Airframe"))),
                ("M_Wing", MakeLit("M_Wing", "T_Wing", pipe, FindTexel(texel, "Wing"))),
                ("M_Details", MakeLit("M_Details", "T_Details", pipe, null)),
                ("M_Cockpit", MakeLit("M_Cockpit", "T_Cockpit", pipe, FindTexel(texel, "Cockpit"))),
                ("M_Interior", MakeLit("M_Interior", "T_Interior", pipe, FindTexel(texel, "Interior"))),
                ("M_Floor", MakeLit("M_Floor", "T_Floor", pipe, FindTexel(texel, "Floor"))),
                ("M_Seats", MakeLit("M_Seats", "T_Seats", pipe, FindTexel(texel, "Seats"))),
                ("M_Gauges", MakeDecal("M_Gauges", pipe, 0.3f, "T_Gauges_Emission", Color.white)),   // matte print
                // v6: the atlas holds the unlit lens look, T_Displays_Emission the lit lamp (per-lamp instance from the rig)
                ("M_Annunciator", MakeDecal("M_Annunciator", pipe, 0.8f, "T_Displays_Emission", Color.white)),
                ("M_RadioDisplay", MakeDecal("M_RadioDisplay", pipe, 0.7f, "T_Displays_Emission", Color.white)),
                ("M_Screen", MakeLens("M_Screen", pipe, new Color(0.012f, 0.016f, 0.016f), 0.85f)),
                ("M_Webbing", MakeTiled("M_Webbing", "T_Webbing", pipe, new Vector2(10f, 1f), 0.2f)),
                ("M_Glass", MakeGlass("M_Glass", pipe, new Color(0.85f, 0.92f, 0.92f, 0.12f))),
                ("M_GaugeGlass", MakeGlass("M_GaugeGlass", pipe, new Color(1f, 1f, 1f, 0.04f), 0.78f, false)),
                ("M_GlassFog", MakeFog("M_GlassFog", pipe)),
                ("M_PropBlur", MakeAlphaTex("M_PropBlur", "T_PropBlur", pipe)),
                ("M_PropDisc", MakeAlphaTex("M_PropDisc", "T_PropDisc", pipe)),
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
            var details = mats.First(m => m.name == "M_Details").mat;
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Root + "/Models" }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                string fn = Path.GetFileNameWithoutExtension(p);
                if (!(fn.StartsWith("SM_Cargo_") || fn == "SM_StepLadder" || fn == "SM_PlaneKey")) continue;
                var cmi = (ModelImporter)AssetImporter.GetAtPath(p);
                ApplyModelSettings(cmi);
                cmi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_Details"), details);
                cmi.SaveAndReimport();
            }

            BuildPlanePrefab(pipe);
            BuildCargoPrefabs();
            BuildPropPrefabs();
            AssetDatabase.SaveAssets();
            Debug.Log($"[UtilityPlane] Done ({pipe}), v8. Prefabs in {Root}/Prefabs");

            // files an older install leaves behind: nothing references them after this build
            var stale = new[] { Root + "/Materials/M_CargoNet.mat", Root + "/Textures/T_CargoNet_BCA.png" }
                .Concat(Atlases.SelectMany(a => new[] { $"{Root}/Textures/T_{a}_MetallicSmoothness.png",
                                                         $"{Root}/Textures/T_{a}_AO.png" }))
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
        [Serializable] class LodLevel { public float screenRelativeHeight; public int triangles; public string[] renderers; }
        [Serializable] class LodGroupData { public string name, root; public LodLevel[] levels; }
        [Serializable] class LodFile { public string note; public LodGroupData[] groups; }
#pragma warning restore 0649

        static readonly string[] Atlases = { "Airframe", "Wing", "Details", "Cockpit", "Interior", "Floor", "Seats" };

        // v7: renderers too small to cast a visible shadow (needles, knobs, switches, lamps, lenses, discs, glass, fog)
        static readonly string[] NoShadowPrefixes =
        {
            "Needle_", "Knob_", "SW_", "Guard_", "Rheo_", "Pull_", "Btn_", "Lamp_", "Lens_", "Display_", "ATT_", "HDG_",
            "TC_", "Clock_", "ALT_", "Compass_", "Belt_", "Lock_", "PropBlur", "PropDisc", "Glass"
        };

        static Texel[] LoadTexel()
        {
            string p = Root + "/Data/atlas_texel.json";
            if (!File.Exists(p)) return new Texel[0];
            var list = JsonUtility.FromJson<TexelList>("{\"items\":" + File.ReadAllText(p) + "}");
            return list != null && list.items != null ? list.items : new Texel[0];
        }

        static Texel FindTexel(Texel[] all, string atlas) => all.FirstOrDefault(t => t.atlas == atlas);

        static void BuildPlanePrefab(string pipe)
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

            // v7: shadows only from parts big enough to matter
            int noShadow = 0;
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                string n = r.name;
                if (NoShadowPrefixes.Any(p => n.StartsWith(p, StringComparison.Ordinal)) || n.EndsWith("_Glass") || n.EndsWith("_Fog"))
                {
                    r.shadowCastingMode = ShadowCastingMode.Off;
                    noShadow++;
                }
            }

            int lights = UtilityPlaneRig.BuildLights(inst.transform, pipe == "HDRP");
            if (inst.GetComponent<UtilityPlaneRig>() == null) inst.AddComponent<UtilityPlaneRig>();
            string lodInfo = BuildLods(inst);
            string path = Root + "/Prefabs/UtilityPlane.prefab";
            PrefabUtility.SaveAsPrefabAsset(inst, path);
            UnityEngine.Object.DestroyImmediate(inst);
            Debug.Log($"[UtilityPlane] {path}: {cols} convex colliders, {vols} interaction volumes, {lights} lights, " +
                      $"{noShadow} renderers without shadows, LOD groups: {lodInfo}");
        }

        // v8: LODGroups from Data/lod.json. Each level lists renderer names (unique in the prefab); <part>_LOD1 / _LOD2
        // are children of <part>, so moving parts carry their LODs. Returns e.g. "Exterior 3, Cockpit 3".
        static string BuildLods(GameObject inst)
        {
            string p = Root + "/Data/lod.json";
            if (!File.Exists(p)) { Debug.LogWarning("[UtilityPlane] Data/lod.json not found: no LODGroup."); return "none"; }
            var file = JsonUtility.FromJson<LodFile>(File.ReadAllText(p));
            if (file == null || file.groups == null) return "none";
            var byName = new System.Collections.Generic.Dictionary<string, Renderer>();
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                if (!byName.ContainsKey(r.name)) byName[r.name] = r;
            var made = new System.Collections.Generic.List<string>();
            foreach (var g in file.groups)
            {
                Transform root = g.root == "UtilityPlane" ? inst.transform :
                    inst.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == g.root);
                if (root == null || g.levels == null) { Debug.LogWarning($"[UtilityPlane] LOD group {g.name}: root {g.root} not found"); continue; }
                var lods = new LOD[g.levels.Length];
                for (int i = 0; i < g.levels.Length; i++)
                {
                    var names = g.levels[i].renderers ?? new string[0];
                    var rs = names.Where(byName.ContainsKey).Select(n => byName[n]).ToArray();
                    if (rs.Length != names.Length)
                        Debug.LogWarning($"[UtilityPlane] LOD group {g.name} level {i}: {names.Length - rs.Length} renderers not found: " +
                                         string.Join(", ", names.Where(n => !byName.ContainsKey(n)).Take(8)));
                    lods[i] = new LOD(g.levels[i].screenRelativeHeight, rs);
                }
                var lg = root.GetComponent<LODGroup>();
                if (lg == null) lg = root.gameObject.AddComponent<LODGroup>();
                lg.fadeMode = LODFadeMode.None;
                lg.SetLODs(lods);
                lg.RecalculateBounds();
                made.Add($"{g.name} {lods.Length}");
            }
            return made.Count > 0 ? string.Join(", ", made) : "none";
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

        // v7: step ladder (COL_* boxes -> BoxColliders, IV_Ladder_Climb -> trigger + UtilityPlaneInteractable "ladder",
        // Ladder_RearLegs = fold hinge about its local X) and the key (convex MeshCollider)
        static void BuildPropPrefabs()
        {
            int layer = LayerMask.NameToLayer("Interact");
            var lad = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SM_StepLadder.fbx");
            if (lad != null)
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(lad);
                PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                foreach (var t in inst.GetComponentsInChildren<Transform>(true)
                             .Where(t => t.name.StartsWith("COL_") || t.name.StartsWith("IV_")).ToArray())
                {
                    var mf = t.GetComponent<MeshFilter>();
                    if (mf == null) continue;
                    var b = mf.sharedMesh.bounds;
                    var bc = t.gameObject.AddComponent<BoxCollider>();
                    bc.center = b.center;
                    bc.size = b.size;
                    if (t.name.StartsWith("IV_"))
                    {
                        bc.isTrigger = true;
                        if (layer >= 0) t.gameObject.layer = layer;
                        var it = t.gameObject.AddComponent<UtilityPlaneInteractable>();
                        it.id = "Ladder_Climb"; it.kind = "ladder"; it.label = "Стремянка";
                    }
                    UnityEngine.Object.DestroyImmediate(t.GetComponent<MeshRenderer>());
                    UnityEngine.Object.DestroyImmediate(mf);
                }
                PrefabUtility.SaveAsPrefabAsset(inst, $"{Root}/Prefabs/StepLadder.prefab");
                UnityEngine.Object.DestroyImmediate(inst);
            }
            var key = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SM_PlaneKey.fbx");
            if (key != null)
            {
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(key);
                PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                var mf = inst.GetComponentInChildren<MeshFilter>();
                if (mf != null)
                {
                    var mc = mf.gameObject.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh;
                    mc.convex = true;
                }
                PrefabUtility.SaveAsPrefabAsset(inst, $"{Root}/Prefabs/PlaneKey.prefab");
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

        static Material GetOrCreate(string name, string pipe, Shader shader = null)
        {
            string path = $"{Root}/Materials/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var sh = shader != null ? shader : LitShader(pipe);
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

        // v7: one packed map per atlas, T_<Atlas>_MaskMap = R metallic, G occlusion, B detail mask (1), A smoothness.
        // URP Lit and Built-in Standard read it as the Metallic map (R, A) and the Occlusion map (G); HDRP as its Mask Map.
        static Material MakeLit(string name, string prefix, string pipe, Texel detail)
        {
            Material mat = GetOrCreate(name, pipe);
            Texture2D bc = Tex(prefix + "_BaseColor"), nrm = Tex(prefix + "_Normal"), mask = Tex(prefix + "_MaskMap");
            SetBase(mat, pipe, bc, Color.white);
            switch (pipe)
            {
                case "URP":
                    mat.SetTexture("_BumpMap", nrm); mat.SetFloat("_BumpScale", 1f); mat.EnableKeyword("_NORMALMAP");
                    mat.SetTexture("_MetallicGlossMap", mask); mat.SetFloat("_Smoothness", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f); mat.EnableKeyword("_METALLICSPECGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", mask); mat.SetFloat("_OcclusionStrength", 1f);
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
                    mat.SetTexture("_MetallicGlossMap", mask); mat.SetFloat("_GlossMapScale", 1f);
                    mat.SetFloat("_SmoothnessTextureChannel", 0f); mat.EnableKeyword("_METALLICGLOSSMAP");
                    mat.SetTexture("_OcclusionMap", mask); mat.SetFloat("_OcclusionStrength", 1f);
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

        // gauge faces / placards / lightplates: printed atlas; emission map = backlit markings only (driven by the rig's
        // material instances). Annunciator lamps and the radio faces (Display_Radio) use T_Displays_Emission.
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
            MakeTransparent(mat, pipe, true);
            Validate(mat, pipe);
            return mat;
        }

        // v7: prop blur / disc: alpha from the texture, two-sided, no shadows (set on the renderers); the rig fades
        // _BaseColor.a on its instances
        static Material MakeAlphaTex(string name, string texName, string pipe)
        {
            Material mat = GetOrCreate(name, pipe);
            SetBase(mat, pipe, Tex(texName), new Color(1f, 1f, 1f, 0f));
            SetSmoothness(mat, pipe, 0.25f);
            if (pipe != "HDRP") mat.SetFloat("_Metallic", 0f);
            MakeTransparent(mat, pipe, true, fade: true);
            Validate(mat, pipe);
            return mat;
        }

        // v7 (SYS-01): fog veil on the inner glass layers. URP: UtilityPlane/GlassFog (clears from the bottom by the
        // mask); HDRP / Built-in: transparent Lit, the rig fades an even veil.
        static Material MakeFog(string name, string pipe)
        {
            var sh = pipe == "URP" ? Shader.Find("UtilityPlane/GlassFog") : null;
            if (sh != null && (ShaderUtil.ShaderHasError(sh) || !sh.isSupported))
            {
                Debug.LogWarning("[UtilityPlane] Shader UtilityPlane/GlassFog has errors or is not supported here: " +
                                 "M_GlassFog falls back to transparent Lit (even veil, no clearing by the mask).");
                sh = null;
            }
            if (sh != null)
            {
                var mat = GetOrCreate(name, pipe, sh);
                mat.renderQueue = -1;                           // the shader's own queue (Transparent+1), also after a fallback
                mat.shaderKeywords = new string[0];
                mat.SetTexture("_FogMask", Tex("T_GlassFog_Mask"));
                mat.SetColor("_FogColor", new Color(0.86f, 0.88f, 0.90f, 1f));
                mat.SetFloat("_Fog", 0f); mat.SetFloat("_FogSide", 0f);
                mat.SetFloat("_Edge", 0.12f); mat.SetFloat("_MaxAlpha", 0.85f);
                EditorUtility.SetDirty(mat);
                return mat;
            }
            var m = GetOrCreate(name, pipe);
            SetBase(m, pipe, null, new Color(0.86f, 0.88f, 0.90f, 0f));
            SetSmoothness(m, pipe, 0.2f);
            MakeTransparent(m, pipe, true, fade: true);
            Validate(m, pipe);
            return m;
        }

        // fade = true (v7: prop discs, fog fallback): straight alpha that also fades the specular, so a fully transparent
        // texel shows no sheen; fade = false (glass): reflections stay on a clear pane.
        static void MakeTransparent(Material mat, string pipe, bool twoSided, bool fade = false)
        {
            switch (pipe)
            {
                case "URP":
                    mat.SetFloat("_Surface", 1f); mat.SetFloat("_Blend", 0f);
                    mat.SetFloat("_BlendModePreserveSpecular", fade ? 0f : 1f);
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                    mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
                    mat.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
                    mat.SetFloat("_ZWrite", 0f); mat.SetFloat("_Cull", twoSided ? 0f : 2f);
                    mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
                case "HDRP":
                    mat.SetFloat("_SurfaceType", 1f); mat.SetFloat("_BlendMode", 0f);
                    mat.SetFloat("_EnableBlendModePreserveSpecularLighting", fade ? 0f : 1f);
                    mat.SetFloat("_DoubleSidedEnable", twoSided ? 1f : 0f);
                    break;
                default:
                    mat.SetFloat("_Mode", fade ? 2f : 3f);              // Standard: Fade / Transparent
                    mat.SetOverrideTag("RenderType", "Transparent");
                    mat.SetInt("_SrcBlend", (int)(fade ? BlendMode.SrcAlpha : BlendMode.One));
                    mat.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                    mat.SetInt("_ZWrite", 0);
                    mat.DisableKeyword("_ALPHATEST_ON");
                    if (fade) { mat.EnableKeyword("_ALPHABLEND_ON"); mat.DisableKeyword("_ALPHAPREMULTIPLY_ON"); }
                    else { mat.DisableKeyword("_ALPHABLEND_ON"); mat.EnableKeyword("_ALPHAPREMULTIPLY_ON"); }
                    mat.renderQueue = (int)RenderQueue.Transparent;
                    break;
            }
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
