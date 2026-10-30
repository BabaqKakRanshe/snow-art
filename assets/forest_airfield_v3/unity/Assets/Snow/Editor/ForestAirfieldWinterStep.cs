using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Snow.EditorTools
{
    /// <summary>
    /// Forest integration: the airfield in winter, from the Blender concept of 29.10.2026 (package
    /// source/assets/forest_airfield_v3, docs/gdd/locations/airfield/concept_v3). Reads <see cref="DataPath"/>:
    ///  - the slabs under a thin ploughed snow: renderers under ForestAirfield with M_AF_Runway get M_AF_RunwayWinter (the
    ///    same material on T_AF_Runway_Winter: the plain and worn slabs' islands with the snow baked in, two wheel tracks a
    ///    lane, more snow to the edges; the other islands as they were), the apron's slabs (more than apronFrom m off the
    ///    axis) M_AF_ApronWinter (nearly white, as the concept's apron);
    ///  - the snow model Forest_AirfieldSnow.fbx (world space): the plough's windrows (about 1 m) along the strip, the banks
    ///    of the apron and the turning pad, drifts at the hangar's facade, caps and drifts on the threshold lights, pale
    ///    stripes at the ends; under ForestRoads/<see cref="Holder"/>, where ForestWinterStep puts no snow decal (the banks
    ///    carry their own snow, as the road models do); banks with mesh colliders;
    ///  - the apron lamps (LightPole under ForestAirfield) dead: no power at the airfield;
    ///  - the Terrain trees: the corridor clear to the forest edge, the approach clearings (205 m south, 165 m north) with
    ///    stumps for a share of the grown trees, nothing on the hangar's front, fences and posts stay; trees taken go into
    ///    ForestWoodsStep's store (a rebuild starts from the same forest); the young growth at the edge, along the clearings
    ///    and on the hangar's hill is planted with <see cref="Added"/> and taken up first on the next run; nothing new within
    ///    roadKeep m of a road;
    ///  - the Terrain paint: the strip, the apron and the pad snow with the plough's packed bands and tyre tracks
    ///    (TL_ForestFloor, TL_TrailTrack, TL_RoadRuts); the dark floor of the trees that went (TL_ForestFloorDark) and the
    ///    rock of the slopes the earthwork flattened (TL_Rock under rockFlat..rockSteep°) back to snow; roads, trails and
    ///    steep rock stay.
    /// The ground comes once, through WorldGroundImport (forest_airfield_v3_apply.cs, which also builds the props with
    /// <see cref="BuildProps"/>). In the build after ForestBaseYardStep (after ForestNetworkStep, ForestRoadsStep,
    /// ForestWoodsStep and ForestSlopeRock, which it overrides) and before ForestTreeCollidersStep and ForestWinterStep;
    /// Tools / Snow / Forest / Airfield Winter runs it alone. A second run gives the same result; only the soft rims of the
    /// paint keep settling a little.
    /// </summary>
    public static class ForestAirfieldWinterStep
    {
        public const string Folder = SnowPaths.Forest + "/Airfield/Winter";
        public const string DataPath = Folder + "/ForestAirfieldWinter.json";
        public const string Holder = "AirfieldSnow";
        const string PropsFolder = SnowPaths.Forest + "/Airfield/Prefabs";
        const string DrumModel = Folder + "/AF_FuelDrum.fbx";
        const string DrumMaterial = SnowPaths.Vehicles + "/Plane/Game/M_FuelDrum.mat";
        const string GeneratorSource = SnowPaths.Items + "/Parts/Prefabs/Item_BackupGenerator.prefab";
        /// <summary>Trees this step plants carry this tint (a step off white; ForestWoodsStep 253,253,254, ForestRockSetsStep
        /// 254,253,253, ForestNetworkStep 254,254,253): a rerun takes them up first.</summary>
        public static readonly Color32 Added = new Color32(253, 254, 254, 255);
        static readonly Color32 NetworkPlanted = new Color32(254, 254, 253, 255);      // ForestNetworkStep.Planted (private there)

        [Serializable] class MatDef { public string name, texture; public float[] color; }
        [Serializable] class ObjDef { public string name; public string[] materials; public bool collider; }
        [Serializable] class RunwayDef { public string material, texture, winter, apronTexture, apronWinter; public float x, z, yaw, apronFrom; }
        [Serializable] class GridDef { public string file; public float x0, z0, step; public int nx, nz; }
        [Serializable] class TreeDef { public string proto; public float x, z, rot, w, h; }
        [Serializable]
        class TreesDef
        {
            public GridDef mask;
            public string stumpProto;
            public float stumpShare, bigHeight, roadKeep;
            public float[] stumpScale;
            public string[] bigKinds, keep;
            public TreeDef[] add;
        }
        [Serializable]
        class PaintDef
        {
            public string file, floor, dark, rock, packed, ruts;
            public float x0, z0, step, packedShare, rockFlat, rockSteep;
            public int nx, nz;
        }
        [Serializable]
        class Data
        {
            public string version, note, model;
            public ObjDef[] objects;
            public MatDef[] materials;
            public RunwayDef runway;
            public TreesDef trees;
            public PaintDef paint;
        }
        [Serializable] class RoadLine { public float[] points; }
        [Serializable] class Roads { public RoadLine[] roads; }

        [MenuItem("Tools/Snow/Forest/Airfield Winter")]
        static void Menu()
        {
            Transform root = GameObject.Find("Forest")?.transform;
            if (root == null) { Debug.LogError("[Snow] Forest airfield winter: no Forest root in the open scene."); return; }
            Run(root);
        }

        public static string Run(Transform root)
        {
            if (!File.Exists(DataPath))
            {
                string none = $"[Snow] Forest airfield winter: {DataPath} not found; nothing done.";
                Debug.LogWarning(none);
                return none;
            }
            Data d = JsonUtility.FromJson<Data>(File.ReadAllText(DataPath));
            string runway = Runway(root, d);
            string model = Model(root, d);
            string lamps = DeadLamps(root);
            string trees = Trees(root, d);
            string paint = Paint(root, d);
            AssetDatabase.SaveAssets();
            string log = $"[Snow] Forest airfield winter ({DataPath}): {runway}; {model}; {lamps}; {trees}; {paint}.";
            Debug.Log(log);
            return log;
        }

        // ------------------------------------------------------------------ the runway's slabs

        /// <summary>A copy of the summer material on a winter atlas (imported as the summer one is), made once, kept in step.</summary>
        static Material WinterMat(Material summer, string texPath, string matPath)
        {
            if (string.IsNullOrEmpty(texPath) || string.IsNullOrEmpty(matPath)) return null;
            Texture summerTex = summer.HasProperty("_BaseMap") ? summer.GetTexture("_BaseMap") : null;
            string summerPath = summerTex != null ? AssetDatabase.GetAssetPath(summerTex) : null;
            if (!string.IsNullOrEmpty(summerPath) && AssetImporter.GetAtPath(summerPath) is TextureImporter from &&
                AssetImporter.GetAtPath(texPath) is TextureImporter to &&
                (to.filterMode != from.filterMode || to.mipmapEnabled != from.mipmapEnabled || to.wrapMode != from.wrapMode ||
                 to.textureCompression != from.textureCompression || to.sRGBTexture != from.sRGBTexture ||
                 to.maxTextureSize != from.maxTextureSize || to.anisoLevel != from.anisoLevel))
            {
                to.filterMode = from.filterMode; to.mipmapEnabled = from.mipmapEnabled; to.wrapMode = from.wrapMode;
                to.textureCompression = from.textureCompression; to.sRGBTexture = from.sRGBTexture;
                to.maxTextureSize = from.maxTextureSize; to.anisoLevel = from.anisoLevel;
                to.SaveAndReimport();
            }
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
            if (tex == null) return null;
            var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (m == null)
            {
                m = new Material(summer) { name = Path.GetFileNameWithoutExtension(matPath) };
                AssetDatabase.CreateAsset(m, matPath);
            }
            else m.CopyPropertiesFromMaterial(summer);
            m.SetTexture("_BaseMap", tex);
            if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", tex);
            EditorUtility.SetDirty(m);
            return m;
        }

        static string Runway(Transform root, Data d)
        {
            RunwayDef rd = d.runway;
            if (rd == null || string.IsNullOrEmpty(rd.material)) return "slabs as they are";
            var summer = AssetDatabase.LoadAssetAtPath<Material>(rd.material);
            if (summer == null) return $"slabs NOT winter ({rd.material} missing)";
            Material winter = WinterMat(summer, rd.texture, rd.winter), apron = WinterMat(summer, rd.apronTexture, rd.apronWinter);
            if (winter == null) return $"slabs NOT winter ({rd.texture} missing)";
            Transform af = root.Find(ForestAirfieldStep.RootName);
            if (af == null) return "slabs NOT winter (no ForestAirfield root)";
            // the apron's slabs (off the axis, across it) are nearly white, the strip's ploughed
            float c = Mathf.Cos(rd.yaw * Mathf.Deg2Rad), sn = Mathf.Sin(rd.yaw * Mathf.Deg2Rad);
            int strip = 0, aprons = 0;
            foreach (Renderer r in af.GetComponentsInChildren<Renderer>(true))
            {
                Material[] ms = r.sharedMaterials;
                if (!ms.Contains(summer)) continue;
                Vector3 p = r.transform.position;
                bool onApron = apron != null && rd.apronFrom > 0f && Mathf.Abs((p.x - rd.x) * c - (p.z - rd.z) * sn) > rd.apronFrom;
                for (int i = 0; i < ms.Length; i++)
                    if (ms[i] == summer) ms[i] = onApron ? apron : winter;
                r.sharedMaterials = ms;
                if (onApron) aprons++; else strip++;
            }
            return $"{strip} renderers of the strip on {winter.name}, {aprons} of the apron on {(apron != null ? apron.name : "-")}";
        }

        // ------------------------------------------------------------------ the snow model

        static Material Mat(MatDef def)
        {
            string mp = $"{Folder}/{def.name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(mp);
            if (m == null)
            {
                Shader sh = Shader.Find("Universal Render Pipeline/Lit");
                if (sh == null) return null;
                m = new Material(sh) { name = def.name };
                AssetDatabase.CreateAsset(m, mp);
            }
            var tex = string.IsNullOrEmpty(def.texture) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(def.texture);
            m.SetTexture("_BaseMap", tex);
            m.SetColor("_BaseColor", def.color != null && def.color.Length >= 3 ? new Color(def.color[0], def.color[1], def.color[2], 1f) : Color.white);
            m.SetFloat("_Smoothness", 0f);
            m.SetFloat("_Metallic", 0f);
            m.SetFloat("_SpecularHighlights", 0f); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            m.SetFloat("_EnvironmentReflections", 0f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        static void ModelImport(string path)
        {
            if (AssetImporter.GetAtPath(path) is ModelImporter mi &&
                (mi.materialImportMode != ModelImporterMaterialImportMode.None || !mi.isReadable || mi.importNormals != ModelImporterNormals.Import ||
                 mi.indexFormat != ModelImporterIndexFormat.UInt32 || mi.importAnimation || mi.globalScale != 1f || mi.addCollider))
            {
                mi.materialImportMode = ModelImporterMaterialImportMode.None;
                mi.isReadable = true;
                mi.importNormals = ModelImporterNormals.Import;
                mi.indexFormat = ModelImporterIndexFormat.UInt32;
                mi.importAnimation = false;
                mi.globalScale = 1f;
                mi.addCollider = false;
                mi.SaveAndReimport();
            }
        }

        static void Static(GameObject o) =>
            GameObjectUtility.SetStaticEditorFlags(o, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

        static string Model(Transform root, Data d)
        {
            Transform roads = root.Find(ForestRoadsStep.RootName);
            foreach (Transform p in new[] { roads, root })
            {
                Transform old = p != null ? p.Find(Holder) : null;
                if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            }
            if (string.IsNullOrEmpty(d.model) || !File.Exists(d.model)) return $"no snow model ({d.model} missing)";
            ModelImport(d.model);
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(d.model);
            if (asset == null) return $"snow model {d.model} did not load";
            var mats = new Dictionary<string, Material>();
            foreach (MatDef md in d.materials ?? new MatDef[0]) mats[md.name] = Mat(md);
            var defs = (d.objects ?? new ObjDef[0]).ToDictionary(o => o.name, o => o);

            var holder = new GameObject(Holder).transform;
            holder.SetParent(roads != null ? roads : root, false);
            holder.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, holder);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = Path.GetFileNameWithoutExtension(d.model);
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);       // the meshes are in world space
            Terrain terrain = root.GetComponentInChildren<Terrain>(true);
            int layer = terrain != null ? terrain.gameObject.layer : go.layer;
            uint lightLayers = terrain != null ? terrain.renderingLayerMask : 2u;            // the map's lights, as the ground

            int objects = 0, tris = 0, colliders = 0, missing = 0;
            foreach (MeshRenderer r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                GameObject o = r.gameObject;
                if (!defs.TryGetValue(o.name, out ObjDef def)) { missing++; continue; }
                Material[] ms = (def.materials ?? new string[0]).Select(n => mats.TryGetValue(n, out Material m) ? m : null).ToArray();
                if (ms.Length == 0 || ms.Any(x => x == null)) missing++;
                r.sharedMaterials = ms;
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
                r.renderingLayerMask = lightLayers;
                o.layer = layer;
                Mesh mesh = o.TryGetComponent(out MeshFilter mf) ? mf.sharedMesh : null;
                if (def.collider && mesh != null) { o.AddComponent<MeshCollider>().sharedMesh = mesh; colliders++; }
                Static(o);
                if (mesh != null) for (int s = 0; s < mesh.subMeshCount; s++) tris += (int)mesh.GetIndexCount(s) / 3;
                objects++;
            }
            return $"snow model: {objects} objects ({tris} triangles, {colliders} colliders) under {holder.parent.name}/{Holder}" +
                   (missing > 0 ? $", {missing} without data or material" : "");
        }

        /// <summary>The apron lamps stand without power: lights and glows off (as the start post's pad lamp).</summary>
        static string DeadLamps(Transform root)
        {
            Transform af = root.Find(ForestAirfieldStep.RootName);
            if (af == null) return "no lamps";
            int poles = 0, n = 0;
            foreach (Transform t in af)
            {
                if (!t.name.StartsWith("LightPole", StringComparison.Ordinal)) continue;
                poles++;
                foreach (Light l in t.GetComponentsInChildren<Light>(true)) { l.enabled = false; EditorUtility.SetDirty(l); n++; }
                foreach (Renderer r in t.GetComponentsInChildren<Renderer>(true))
                    if (r.name.StartsWith("Glow_", StringComparison.Ordinal) || r.name.StartsWith("Beacon_", StringComparison.Ordinal)) { r.enabled = false; n++; }
            }
            return $"{poles} apron lamps dead ({n} lights and glows off)";
        }

        // ------------------------------------------------------------------ the Terrain trees

        static bool Same(Color32 a, Color32 b) => a.r == b.r && a.g == b.g && a.b == b.b;

        static float Hash(float x, float z, float salt)
        {
            float h = Mathf.Sin(x * 12.9898f + z * 78.233f + salt * 37.719f) * 43758.5453f;
            return h - Mathf.Floor(h);
        }

        static List<(Vector2 a, Vector2 b)> RoadSegments()
        {
            var list = new List<(Vector2, Vector2)>();
            if (!File.Exists(ForestRoadsStep.DataPath)) return list;
            Roads r = JsonUtility.FromJson<Roads>(File.ReadAllText(ForestRoadsStep.DataPath));
            foreach (RoadLine l in r.roads ?? new RoadLine[0])
                for (int i = 0; i + 5 < (l.points?.Length ?? 0); i += 3)
                    list.Add((new Vector2(l.points[i], l.points[i + 1]), new Vector2(l.points[i + 3], l.points[i + 4])));
            return list;
        }

        static bool OnRoad(List<(Vector2 a, Vector2 b)> segs, Vector2 q, float keep)
        {
            if (keep <= 0f) return false;
            foreach (var seg in segs)
            {
                Vector2 a = seg.a, b = seg.b;
                if (Mathf.Abs(q.x - a.x) > 40f || Mathf.Abs(q.y - a.y) > 40f) continue;
                Vector2 ab = b - a;
                float k = Mathf.Clamp01(Vector2.Dot(q - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
                if ((q - (a + ab * k)).sqrMagnitude < keep * keep) return true;
            }
            return false;
        }

        /// <summary>Height of a tree prototype's model: the top of its meshes over the prefab's root.</summary>
        static float PrefabHeight(GameObject prefab)
        {
            float top = 0f;
            Matrix4x4 toRoot = prefab.transform.worldToLocalMatrix;
            foreach (MeshFilter f in prefab.GetComponentsInChildren<MeshFilter>(true))
            {
                if (f.sharedMesh == null) continue;
                Matrix4x4 m = toRoot * f.transform.localToWorldMatrix;
                Bounds b = f.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
                    top = Mathf.Max(top, m.MultiplyPoint3x4(c).y);
                }
            }
            return top;
        }

        static int Cell(GridDef g, float x, float z)
        {
            int ix = Mathf.FloorToInt((x - g.x0) / g.step), iz = Mathf.FloorToInt((z - g.z0) / g.step);
            return ix < 0 || iz < 0 || ix >= g.nx || iz >= g.nz ? -1 : iz * g.nx + ix;
        }

        static string Trees(Transform root, Data d)
        {
            TreesDef td = d.trees;
            if (td == null || td.mask == null) return "trees as they are";
            string maskPath = $"{Folder}/{td.mask.file}";
            byte[] mask = File.Exists(maskPath) ? File.ReadAllBytes(maskPath) : null;
            if (mask == null || mask.Length != td.mask.nx * td.mask.nz * 3) return $"trees as they are ({maskPath} missing or not {td.mask.nx} x {td.mask.nz} x 3 bytes)";
            string[] keepKinds = td.keep ?? new string[0], bigKinds = td.bigKinds ?? new string[0];
            float s0 = td.stumpScale != null && td.stumpScale.Length >= 2 ? td.stumpScale[0] : 0.8f, s1 = td.stumpScale != null && td.stumpScale.Length >= 2 ? td.stumpScale[1] : 1.3f;
            var roads = RoadSegments();
            var store = ForestWoodsStep.LoadStore();
            int purged = store.RemoveAll(s => Same(s.color, Added));       // ours never go into the store: they are planted again
            var heights = new Dictionary<GameObject, float>();
            int dropped = 0, removed = 0, stored = 0, stumps = 0, planted = 0, nearRoad = 0, noProto = 0;
            var missingProtos = new HashSet<string>();
            foreach (Terrain t in root.GetComponentsInChildren<Terrain>(true))
            {
                TerrainData data = t.terrainData;
                if (data == null) continue;
                TreePrototype[] protos = data.treePrototypes;
                string[] names = protos.Select(p => p.prefab != null ? p.prefab.name : null).ToArray();
                Vector3 o = t.transform.position, size = data.size;
                int stumpIndex = Array.IndexOf(names, td.stumpProto);
                var keep = new List<TreeInstance>(data.treeInstanceCount + 256);
                bool changed = false;
                foreach (TreeInstance ti in data.treeInstances)
                {
                    if (Same(ti.color, Added)) { dropped++; changed = true; continue; }
                    Vector3 w = o + Vector3.Scale(ti.position, size);
                    int cell = Cell(td.mask, w.x, w.z);
                    if (cell < 0 || mask[cell * 3] < 128) { keep.Add(ti); continue; }
                    string pn = ti.prototypeIndex >= 0 && ti.prototypeIndex < names.Length ? names[ti.prototypeIndex] : null;
                    if (pn != null && keepKinds.Any(k => pn.StartsWith(k, StringComparison.Ordinal))) { keep.Add(ti); continue; }
                    removed++; changed = true;
                    bool theirs = Same(ti.color, ForestWoodsStep.Added) || Same(ti.color, ForestRockSetsStep.Added) || Same(ti.color, NetworkPlanted);
                    if (!theirs && pn != null)
                    {
                        store.Add(new ForestWoodsStep.Stored { proto = pn, w = w, rot = ti.rotation, wScale = ti.widthScale, hScale = ti.heightScale, color = ti.color });
                        stored++;
                    }
                    // the clearings: a share of the grown trees stays as a stump
                    if (mask[cell * 3 + 1] < 128 || stumpIndex < 0 || pn == null || !bigKinds.Any(k => pn.StartsWith(k, StringComparison.Ordinal))) continue;
                    GameObject prefab = protos[ti.prototypeIndex].prefab;
                    if (!heights.TryGetValue(prefab, out float ph)) heights[prefab] = ph = PrefabHeight(prefab);
                    if (ph * ti.heightScale <= td.bigHeight || Hash(w.x, w.z, 7f) >= td.stumpShare) continue;
                    float sc = Mathf.Lerp(s0, s1, Hash(w.x, w.z, 8f));
                    keep.Add(new TreeInstance
                    {
                        prototypeIndex = stumpIndex, position = ti.position, rotation = Hash(w.x, w.z, 9f) * Mathf.PI * 2f,
                        widthScale = sc, heightScale = sc, color = Added, lightmapColor = Color.white,
                    });
                    stumps++;
                }
                var index = new Dictionary<string, int>();
                foreach (TreeDef a in td.add ?? new TreeDef[0])
                {
                    if (a.x < o.x || a.z < o.z || a.x >= o.x + size.x || a.z >= o.z + size.z) continue;
                    if (OnRoad(roads, new Vector2(a.x, a.z), td.roadKeep)) { nearRoad++; continue; }
                    if (!index.TryGetValue(a.proto, out int pi)) index[a.proto] = pi = Array.IndexOf(names, a.proto);
                    if (pi < 0) { noProto++; missingProtos.Add(a.proto); continue; }
                    keep.Add(new TreeInstance
                    {
                        prototypeIndex = pi,
                        position = new Vector3((a.x - o.x) / size.x, t.SampleHeight(new Vector3(a.x, 0f, a.z)) / size.y, (a.z - o.z) / size.z),
                        rotation = a.rot, widthScale = a.w, heightScale = a.h, color = Added, lightmapColor = Color.white,
                    });
                    planted++; changed = true;
                }
                if (!changed) continue;
                data.SetTreeInstances(keep.ToArray(), true);
                EditorUtility.SetDirty(data);
                t.Flush();
            }
            ForestWoodsStep.SaveStore(store);
            return $"trees: {removed} taken from the corridor, the clearings and the hangar's front ({stored} into the woods store), " +
                   $"{stumps} stumps in the clearings, {planted} young trees planted ({nearRoad} by a road left out" +
                   (noProto > 0 ? $", {noProto} without a prototype: {string.Join(", ", missingProtos)}" : "") +
                   $"); {dropped} of the last run's taken up first, {purged} of ours out of the woods store";
        }

        // ------------------------------------------------------------------ the Terrain paint

        static float Smooth(float a, float b, float x)
        {
            float t = Mathf.Clamp01((x - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        const int Channels = 5;      // packed, ruts, strip, cleared, regraded

        /// <summary>The five masks at a world point (bilinear), 0..1; false outside the grid.</summary>
        static bool Sample(byte[] g, PaintDef p, float x, float z, float[] v)
        {
            float fx = (x - p.x0) / p.step, fz = (z - p.z0) / p.step;
            if (fx < 0f || fz < 0f || fx > p.nx - 1 || fz > p.nz - 1) return false;
            int ix = Mathf.Min((int)fx, p.nx - 2), iz = Mathf.Min((int)fz, p.nz - 2);
            float tx = fx - ix, tz = fz - iz;
            int i00 = (iz * p.nx + ix) * Channels, i10 = i00 + Channels, i01 = i00 + p.nx * Channels, i11 = i01 + Channels;
            for (int c = 0; c < Channels; c++)
            {
                float lo = g[i00 + c] + (g[i10 + c] - g[i00 + c]) * tx, hi = g[i01 + c] + (g[i11 + c] - g[i01 + c]) * tx;
                v[c] = (lo + (hi - lo) * tz) / 255f;
            }
            return true;
        }

        static int Layer(TerrainData td, string name) =>
            string.IsNullOrEmpty(name) ? -1 : Array.FindIndex(td.terrainLayers, l => l != null && l.name == name);

        static string Paint(Transform root, Data d)
        {
            PaintDef p = d.paint;
            if (p == null || string.IsNullOrEmpty(p.file)) return "paint as it is";
            string path = $"{Folder}/{p.file}";
            if (!File.Exists(path)) return $"paint as it is ({path} missing)";
            byte[] g = File.ReadAllBytes(path);
            if (p.nx < 2 || p.nz < 2 || g.Length != p.nx * p.nz * Channels) return $"paint as it is ({path}: {g.Length} bytes, {p.nx} x {p.nz} x {Channels} expected)";
            float gx1 = p.x0 + (p.nx - 1) * p.step, gz1 = p.z0 + (p.nz - 1) * p.step;
            int texels = 0, darkOut = 0, rockOut = 0, tiles = 0;
            string noLayers = "";
            var v = new float[Channels];
            foreach (Terrain t in root.GetComponentsInChildren<Terrain>(true))
            {
                TerrainData td = t.terrainData;
                if (td == null) continue;
                Vector3 o = t.transform.position, s = td.size;
                if (o.x > gx1 || o.z > gz1 || o.x + s.x < p.x0 || o.z + s.z < p.z0) continue;
                int floor = Layer(td, p.floor), dark = Layer(td, p.dark), rock = Layer(td, p.rock), packed = Layer(td, p.packed), ruts = Layer(td, p.ruts);
                if (floor < 0 || packed < 0 || ruts < 0) { noLayers += $" {td.name}"; continue; }
                int n = td.alphamapResolution, L = td.alphamapLayers;
                float texel = s.x / n;
                int x0 = Mathf.Clamp(Mathf.FloorToInt((p.x0 - o.x) / texel), 0, n - 1), x1 = Mathf.Clamp(Mathf.CeilToInt((gx1 - o.x) / texel), 0, n - 1);
                int z0 = Mathf.Clamp(Mathf.FloorToInt((p.z0 - o.z) / texel), 0, n - 1), z1 = Mathf.Clamp(Mathf.CeilToInt((gz1 - o.z) / texel), 0, n - 1);
                if (x1 < x0 || z1 < z0) continue;
                int w = x1 - x0 + 1, h = z1 - z0 + 1;
                float[,,] a = td.GetAlphamaps(x0, z0, w, h);
                bool changed = false;
                for (int j = 0; j < h; j++)
                    for (int i = 0; i < w; i++)
                    {
                        if (!Sample(g, p, o.x + (x0 + i + 0.5f) * texel, o.z + (z0 + j + 0.5f) * texel, v)) continue;
                        float pk = v[0], rt = v[1], strip = v[2], cleared = v[3], regraded = v[4];
                        if (strip <= 0f && cleared <= 0f && regraded <= 0f) continue;
                        // the dark floor of the trees that went, the rock of slopes the earthwork flattened: snow again
                        if (cleared > 0f && dark >= 0 && a[j, i, dark] > 0f)
                        {
                            float m = a[j, i, dark] * cleared;
                            a[j, i, dark] -= m; a[j, i, floor] += m; darkOut++;
                        }
                        if (regraded > 0f && rock >= 0 && a[j, i, rock] > 0f)
                        {
                            float k = regraded * (1f - Smooth(p.rockFlat, p.rockSteep, td.GetSteepness((x0 + i + 0.5f) / n, (z0 + j + 0.5f) / n)));
                            if (k > 0f)
                            {
                                float m = a[j, i, rock] * k;
                                a[j, i, rock] -= m; a[j, i, floor] += m; rockOut++;
                            }
                        }
                        // the strip, the apron and the pad: snow, the plough's packed bands, the tyre tracks
                        if (strip > 0f)
                        {
                            float tr = rt, tp = p.packedShare * pk * (1f - rt), tf = 1f - tr - tp;
                            for (int l = 0; l < L; l++)
                            {
                                float target = l == floor ? tf : l == packed ? tp : l == ruts ? tr : 0f;
                                a[j, i, l] += (target - a[j, i, l]) * strip;
                            }
                        }
                        float sum = 0f;
                        for (int l = 0; l < L; l++) sum += a[j, i, l];
                        if (sum <= 1e-5f) { a[j, i, floor] = 1f; sum = 1f; }
                        for (int l = 0; l < L; l++) a[j, i, l] /= sum;
                        texels++;
                        changed = true;
                    }
                if (!changed) continue;
                td.SetAlphamaps(x0, z0, a);
                EditorUtility.SetDirty(td);
                tiles++;
            }
            return $"paint: {texels} texels on {tiles} tiles ({darkOut} dark floor and {rockOut} flattened rock back to snow)" +
                   (noLayers.Length > 0 ? $"; NOT painted (no {p.floor} / {p.packed} / {p.ruts} layer):{noLayers}" : "");
        }

        // ------------------------------------------------------------------ the props (once, from the apply script)

        /// <summary>Renderer bounds of an object in its own space.</summary>
        static Bounds LocalBounds(GameObject go)
        {
            Bounds b = default;
            bool first = true;
            Matrix4x4 toRoot = go.transform.worldToLocalMatrix;
            foreach (MeshFilter f in go.GetComponentsInChildren<MeshFilter>(true))
            {
                if (f.sharedMesh == null) continue;
                Matrix4x4 m = toRoot * f.transform.localToWorldMatrix;
                Bounds mb = f.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = m.MultiplyPoint3x4(new Vector3((i & 1) == 0 ? mb.min.x : mb.max.x, (i & 2) == 0 ? mb.min.y : mb.max.y, (i & 4) == 0 ? mb.min.z : mb.max.z));
                    if (first) { b = new Bounds(c, Vector3.zero); first = false; } else b.Encapsulate(c);
                }
            }
            return b;
        }

        /// <summary>Does another live component on the same object require this one?</summary>
        static bool Required(Component c, Component[] all)
        {
            foreach (Component o in all)
            {
                if (o == null || o == c || o.gameObject != c.gameObject) continue;
                foreach (RequireComponent rc in o.GetType().GetCustomAttributes(typeof(RequireComponent), true))
                    if ((rc.m_Type0 != null && rc.m_Type0.IsInstanceOfType(c)) || (rc.m_Type1 != null && rc.m_Type1.IsInstanceOfType(c)) ||
                        (rc.m_Type2 != null && rc.m_Type2.IsInstanceOfType(c))) return true;
            }
            return false;
        }

        static GameObject PlaceDrum(Transform parent, Material mat)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(DrumModel);
            if (asset == null) return null;
            var m = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent);
            PrefabUtility.UnpackPrefabInstance(m, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            m.name = "Drum";
            foreach (MeshRenderer r in m.GetComponentsInChildren<MeshRenderer>(true))
            {
                r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
            }
            return m;
        }

        /// <summary>AF_FuelDrum (standing), AF_FuelDrum_Lying and AF_Generator (Item_BackupGenerator without its item scripts,
        /// body and sound, its base at the origin) in Airfield/Prefabs: still decor for ForestAirfield.json, colliders on.</summary>
        public static string BuildProps()
        {
            var log = new List<string>();
            ModelImport(DrumModel);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(DrumMaterial);
            if (mat == null) log.Add($"{DrumMaterial} missing: the drums keep no material");
            foreach (bool lying in new[] { false, true })
            {
                string name = lying ? "AF_FuelDrum_Lying" : "AF_FuelDrum";
                var root = new GameObject(name);
                try
                {
                    GameObject drum = PlaceDrum(root.transform, mat);
                    if (drum == null) { log.Add($"{name}: {DrumModel} missing"); continue; }
                    Bounds b = LocalBounds(drum);                               // origin at the foot, the axis up
                    float r = Mathf.Max(b.extents.x, b.extents.z), len = b.size.y;
                    var cap = root.AddComponent<CapsuleCollider>();
                    cap.radius = r;
                    cap.height = len;
                    if (lying)
                    {
                        // on its side along +Z, resting on the ground
                        drum.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                        drum.transform.localPosition = new Vector3(0f, r, -len * 0.5f);
                        cap.direction = 2;
                        cap.center = new Vector3(0f, r, 0f);
                    }
                    else
                    {
                        cap.direction = 1;
                        cap.center = new Vector3(0f, len * 0.5f, 0f);
                    }
                    foreach (Transform x in root.GetComponentsInChildren<Transform>(true)) Static(x.gameObject);
                    PrefabUtility.SaveAsPrefabAsset(root, $"{PropsFolder}/{name}.prefab");
                    log.Add($"{name}.prefab ({r * 2f:0.00} x {len:0.00} m)");
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }

            var gen = AssetDatabase.LoadAssetAtPath<GameObject>(GeneratorSource);
            if (gen == null) log.Add($"AF_Generator: {GeneratorSource} missing");
            else
            {
                var root = new GameObject("AF_Generator");
                try
                {
                    var g = (GameObject)PrefabUtility.InstantiatePrefab(gen, root.transform);
                    PrefabUtility.UnpackPrefabInstance(g, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                    g.name = "Generator";
                    // still decor: no item scripts, body, sound or trigger zones; a component goes once nothing left on its
                    // object needs it (RequireComponent), so no "can't remove" errors
                    foreach (Transform x in g.GetComponentsInChildren<Transform>(true)) GameObjectUtility.RemoveMonoBehavioursWithMissingScript(x.gameObject);
                    int gone = 0;
                    for (int pass = 0; pass < 8; pass++)
                    {
                        Component[] all = g.GetComponentsInChildren<Component>(true);
                        var doomed = all.Where(c => c is MonoBehaviour || c is Rigidbody || c is AudioSource || (c is Collider col && col.isTrigger)).ToList();
                        if (doomed.Count == 0) break;
                        int before = gone;
                        foreach (Component c in doomed)
                        {
                            if (c == null || Required(c, all)) continue;
                            UnityEngine.Object.DestroyImmediate(c);
                            gone++;
                        }
                        if (gone == before) break;
                    }
                    Bounds b = LocalBounds(root);
                    g.transform.localPosition += Vector3.up * -b.min.y;                // its base on the ground
                    foreach (Transform x in root.GetComponentsInChildren<Transform>(true)) Static(x.gameObject);
                    PrefabUtility.SaveAsPrefabAsset(root, $"{PropsFolder}/AF_Generator.prefab");
                    int left = g.GetComponentsInChildren<MonoBehaviour>(true).Length;
                    log.Add($"AF_Generator.prefab ({b.size.x:0.00} x {b.size.y:0.00} x {b.size.z:0.00} m, {gone} components off" +
                            (left > 0 ? $", {left} scripts LEFT" : "") + ")");
                }
                finally { UnityEngine.Object.DestroyImmediate(root); }
            }
            AssetDatabase.SaveAssets();
            return "[Snow] Airfield props: " + string.Join("; ", log);
        }
    }
}
