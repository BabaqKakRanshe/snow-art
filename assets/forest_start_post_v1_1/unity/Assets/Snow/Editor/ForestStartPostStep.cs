using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using Snow.Levels.Forest;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Snow.EditorTools
{
    /// <summary>
    /// Forest integration: the start post at the SPERRGEBIET gate brought to the Blender concept of 29.10.2026 (package
    /// source/assets/forest_start_post_v1_1, folders of 29.10; targets docs/gdd/locations/start_post/concept_v3 arrive_wache + night_wache,
    /// QUESTIONS_3 all accepted). Two parts:
    ///  - <see cref="BuildWachePrefab"/> (once, from the apply script): StartWache.prefab, a copy of StartBooth.prefab with the
    ///    booth's body, glass and lamp swapped for the guard house of StartWache.fbx (grey rendered brick, flat roof, big window
    ///    to the barrier, door to the road), its sign gone, the booth's door (IX_Door) moved into the house's door, the
    ///    booth's lights moved to the lamp over the door; new: the interior (table, stove, bunk), the warm window glow, the
    ///    stove's glow, the roof snow with cornice and icicles, a warm light inside, the stove pipe's smoke.
    ///    ForestStartDress.json places it (prop at u -8.5, v -3.4, yaw 180) instead of the booth;
    ///  - <see cref="Run"/> (in the build): under <see cref="RootName"/> the package model Forest_StartPost.fbx (world space):
    ///    the ploughed road strip SP_Road_* (6 m lane, two wheel tracks, low windrows, ditch; baked texture), the snow of the
    ///    pad and the post SP_SnowLayer, the SPERRGEBIET plates SP_Plate_*; the snow caps SPC_* hung under their props
    ///    (ForestStartDress props and Structures/ZoneGate, Structures/Sign_Observatory); the RoadNet meshes cut where the
    ///    strip lies (copies saved in the package folder); the pad lamp dead (its lights off); Terrain in the post's zone:
    ///    paint to snow (TL_ForestFloor / TL_ForestFloorDark), no grass, no trees on the road strip.
    /// In the build after ForestPlacesStep (after ForestRoadsStep and ForestSlopeRock, which it overrides) and before
    /// ForestTreeCollidersStep and ForestWinterStep. Idempotent: the root is rebuilt, the cut is made from the current RoadNet.
    /// </summary>
    public static class ForestStartPostStep
    {
        public const string DataPath = SnowPaths.Forest + "/Start/Post/ForestStartPost.json";
        public const string RootName = "ForestStartPost";
        const string Folder = SnowPaths.Forest + "/Start/Post";
        const string SmokeMaterial = SnowPaths.Items + "/Smoke/Materials/M_Smoke.mat";
        // the road strip and the pad snow carry their own snow, as the road models: they sit under ForestRoads, where
        // ForestWinterStep puts no snow decal (it would whiten the lane and the trodden path)
        const string GroundHolder = "StartPostGround";

        [Serializable] class MatDef { public string name, texture, filter; public float[] color, emission; public float smoothness, metallic; }
        [Serializable] class ObjDef { public string name, collider; public string[] materials; public bool ground; }
        [Serializable] class CapDef { public string name, target; public float x, z; }
        [Serializable] class PartDef { public string mesh, target, collider; public string[] materials; }
        [Serializable] class DoorDef { public float[] centre; public float width, height; }
        [Serializable] class LightDef { public string name; public float[] pos, color; public float intensity, range; }
        [Serializable] class PaintDef { public string layer; public float w; }
        [Serializable]
        class WacheDef
        {
            public string fbx, template, prefab;
            public PartDef[] parts;
            public string[] remove;
            public DoorDef door;
            public float[] lamp, smoke, wind;
            public LightDef[] lights;
        }
        [Serializable]
        class Data
        {
            public string model, roadMeshPrefix;
            public MatDef[] materials;
            public ObjDef[] objects;
            public CapDef[] caps;
            public WacheDef wache;
            public float[] roadCut, treeBand, zone, deadLamp;
            public float zoneSoft;
            public PaintDef[] paint;
        }

        [MenuItem("Tools/Snow/Forest/Start Post")]
        static void Menu()
        {
            Transform root = GameObject.Find("Forest")?.transform;
            if (root == null) { Debug.LogError("[Snow] Forest start post: no Forest root in the open scene."); return; }
            Debug.Log(Run(root));
        }

        [MenuItem("Tools/Snow/Forest/Start Post - Build Wache Prefab")]
        static void MenuWache() => Debug.Log(BuildWachePrefab());

        static Data Load() => File.Exists(DataPath) ? JsonUtility.FromJson<Data>(File.ReadAllText(DataPath)) : null;

        public static string Run(Transform root)
        {
            Data d = Load();
            if (d == null) return $"[Snow] Forest start post: {DataPath} not found; nothing done.";
            Transform old = root.Find(RootName);
            if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            Transform roads = root.Find(ForestRoadsStep.RootName);
            Transform oldGround = roads != null ? roads.Find(GroundHolder) : null;
            if (oldGround != null) UnityEngine.Object.DestroyImmediate(oldGround.gameObject);
            var group = new GameObject(RootName).transform;
            group.SetParent(root, false);
            Terrain terrain = root.GetComponentInChildren<Terrain>(true);
            int groundLayer = terrain != null ? terrain.gameObject.layer : 0;
            var mats = Mats(d);
            string model = Model(group, roads, d, mats, groundLayer, out GameObject go);
            string caps = Caps(root, d, go);
            string cut = RoadCut(root, d);
            string lamp = DeadLamp(root, d);
            string ground = Ground(root, d);
            AssetDatabase.SaveAssets();
            string log = $"[Snow] Forest start post ({DataPath}): {model}; {caps}; {cut}; {lamp}; {ground}.";
            Debug.Log(log);
            return log;
        }

        // ------------------------------------------------------------------ materials

        static Dictionary<string, Material> Mats(Data d)
        {
            var mats = new Dictionary<string, Material>();
            foreach (MatDef m in d.materials ?? new MatDef[0]) mats[m.name] = Mat(m);
            return mats;
        }

        /// <summary>URP Lit, a texture (point, or bilinear like the Terrain), a tint, no highlights, an emission where the
        /// data has one (the window, the stove, the bulbs).</summary>
        static Material Mat(MatDef def)
        {
            Texture2D tex = null;
            if (!string.IsNullOrEmpty(def.texture))
            {
                string tp = $"{Folder}/{def.texture}";
                bool point = def.filter != "bilinear";
                if (AssetImporter.GetAtPath(tp) is TextureImporter ti &&
                    (ti.filterMode != (point ? FilterMode.Point : FilterMode.Bilinear) || !ti.mipmapEnabled || ti.wrapMode != TextureWrapMode.Repeat ||
                     ti.textureCompression != TextureImporterCompression.Uncompressed || !ti.sRGBTexture || ti.maxTextureSize < 2048))
                {
                    ti.filterMode = point ? FilterMode.Point : FilterMode.Bilinear; ti.mipmapEnabled = true; ti.wrapMode = TextureWrapMode.Repeat;
                    ti.textureCompression = TextureImporterCompression.Uncompressed; ti.sRGBTexture = true; ti.anisoLevel = point ? 1 : 8;
                    ti.maxTextureSize = Math.Max(ti.maxTextureSize, 2048);
                    ti.SaveAndReimport();
                }
                tex = AssetDatabase.LoadAssetAtPath<Texture2D>(tp);
            }
            string mp = $"{Folder}/{def.name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(mp);
            if (m == null)
            {
                Shader sh = Shader.Find("Universal Render Pipeline/Lit");
                if (sh == null) return null;
                m = new Material(sh);
                AssetDatabase.CreateAsset(m, mp);
            }
            m.SetTexture("_BaseMap", tex);
            Color c = def.color != null && def.color.Length >= 3 ? new Color(def.color[0], def.color[1], def.color[2], 1f) : Color.white;
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Smoothness", def.smoothness);
            m.SetFloat("_Metallic", def.metallic);
            m.SetFloat("_SpecularHighlights", 0f); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            m.SetFloat("_EnvironmentReflections", 0f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            if (def.emission != null && def.emission.Length >= 4 && def.emission[3] > 0f)
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", new Color(def.emission[0], def.emission[1], def.emission[2]) * def.emission[3]);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            else
            {
                m.DisableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", Color.black);
            }
            EditorUtility.SetDirty(m);
            return m;
        }

        static void Static(GameObject o) =>
            GameObjectUtility.SetStaticEditorFlags(o, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

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

        // ------------------------------------------------------------------ the package model

        static string Model(Transform group, Transform roads, Data d, Dictionary<string, Material> mats, int groundLayer, out GameObject go)
        {
            go = null;
            ModelImport(d.model);
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(d.model);
            if (asset == null) return $"MISSING {d.model}";
            var defs = (d.objects ?? new ObjDef[0]).ToDictionary(o => o.name, o => o);
            go = (GameObject)PrefabUtility.InstantiatePrefab(asset, group);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "Forest_StartPost";
            go.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            go.transform.localScale = Vector3.one;
            int objects = 0, tris = 0, colliders = 0, missing = 0;
            foreach (MeshRenderer r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                GameObject o = r.gameObject;
                if (!defs.TryGetValue(o.name, out ObjDef def)) { missing++; continue; }
                Material[] ms = def.materials.Select(n => mats.TryGetValue(n, out Material m) ? m : null).ToArray();
                if (ms.Any(x => x == null)) missing++;
                r.sharedMaterials = ms;
                r.shadowCastingMode = def.ground ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
                r.renderingLayerMask = 2u;                                     // the map's lights, as ForestStartDress's props
                if (def.ground) o.layer = groundLayer;
                Mesh mesh = o.GetComponent<MeshFilter>().sharedMesh;
                if (def.collider == "mesh" && mesh != null) { o.AddComponent<MeshCollider>().sharedMesh = mesh; colliders++; }
                Static(o);
                tris += mesh != null ? mesh.triangles.Length / 3 : 0;
                objects++;
            }
            int underRoads = 0;
            if (roads != null)
            {
                var holder = new GameObject(GroundHolder).transform;
                holder.SetParent(roads, false);
                foreach (ObjDef def in d.objects ?? new ObjDef[0])
                {
                    if (!def.ground) continue;
                    Transform o = go.transform.Find(def.name);
                    if (o == null) continue;
                    o.SetParent(holder, true);
                    underRoads++;
                }
            }
            return $"{objects} package objects ({tris} triangles, {colliders} colliders, {underRoads} ground pieces under {(roads != null ? roads.name : "NO road root")}/{GroundHolder}" +
                   (missing > 0 ? $", {missing} without data or material" : "") + ")";
        }

        /// <summary>The snow caps: each one is made in its prop's own space; it goes under the placed prop nearest to the data's
        /// point (ForestStartDress props by name, or a Structures path).</summary>
        static string Caps(Transform root, Data d, GameObject model)
        {
            if (model == null) return "no caps (no model)";
            Transform dress = root.Find("ForestStartDress");
            int hung = 0, lost = 0;
            foreach (CapDef c in d.caps ?? new CapDef[0])
            {
                Transform cap = model.transform.Find(c.name);
                if (cap == null) { lost++; continue; }
                Transform target = null;
                if (c.target.StartsWith("Structures/", StringComparison.Ordinal)) target = root.Find(c.target);
                else if (dress != null)
                {
                    float best = 2.5f;
                    foreach (Transform t in dress)
                    {
                        if (t.name != c.target) continue;
                        float dist = new Vector2(t.position.x - c.x, t.position.z - c.z).magnitude;
                        if (dist < best) { best = dist; target = t; }
                    }
                }
                if (target == null) { UnityEngine.Object.DestroyImmediate(cap.gameObject); lost++; continue; }
                cap.SetParent(target, false);       // keeps its pose relative to the model root (at the origin): the prop's own space
                hung++;
            }
            return $"{hung} snow caps on their props" + (lost > 0 ? $", {lost} without their prop (removed)" : "");
        }

        // ------------------------------------------------------------------ the RoadNet under the strip

        static string RoadCut(Transform root, Data d)
        {
            if (d.roadCut == null || d.roadCut.Length < 6) return "no road cut";
            string prefix = string.IsNullOrEmpty(d.roadMeshPrefix) ? "ROADNET_" : d.roadMeshPrefix;
            Transform own = root.Find(RootName);
            float bx0 = float.MaxValue, bz0 = float.MaxValue, bx1 = float.MinValue, bz1 = float.MinValue;
            for (int i = 0; i + 1 < d.roadCut.Length; i += 2)
            {
                bx0 = Mathf.Min(bx0, d.roadCut[i]); bx1 = Mathf.Max(bx1, d.roadCut[i]); bz0 = Mathf.Min(bz0, d.roadCut[i + 1]); bz1 = Mathf.Max(bz1, d.roadCut[i + 1]);
            }
            int meshes = 0, removed = 0;
            foreach (MeshFilter mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null || !mf.sharedMesh.name.StartsWith(prefix, StringComparison.Ordinal)) continue;
                if (own != null && mf.transform.IsChildOf(own)) continue;
                Mesh src = mf.sharedMesh;
                if (!src.isReadable && AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(src)) is ModelImporter rmi)
                {
                    rmi.isReadable = true;                                     // the cut reads the road's vertices
                    rmi.SaveAndReimport();
                    src = mf.sharedMesh;
                }
                string baseName = src.name.Replace("_StartCut", "");
                Matrix4x4 l2w = mf.transform.localToWorldMatrix;
                Vector3[] v = src.vertices;
                var cut = new Mesh { name = baseName + "_StartCut", indexFormat = IndexFormat.UInt32 };
                cut.vertices = v;
                if (src.normals.Length == v.Length) cut.normals = src.normals;
                if (src.uv.Length == v.Length) cut.uv = src.uv;
                if (src.uv2.Length == v.Length) cut.uv2 = src.uv2;
                if (src.colors.Length == v.Length) cut.colors = src.colors;
                if (src.tangents.Length == v.Length) cut.tangents = src.tangents;
                cut.subMeshCount = src.subMeshCount;
                int gone = 0;
                for (int s = 0; s < src.subMeshCount; s++)
                {
                    int[] tri = src.GetTriangles(s);
                    var keep = new List<int>(tri.Length);
                    for (int k = 0; k + 2 < tri.Length; k += 3)
                    {
                        Vector3 c = l2w.MultiplyPoint3x4((v[tri[k]] + v[tri[k + 1]] + v[tri[k + 2]]) / 3f);
                        if (c.x >= bx0 && c.x <= bx1 && c.z >= bz0 && c.z <= bz1 && InPoly(new Vector2(c.x, c.z), d.roadCut)) { gone++; continue; }
                        keep.Add(tri[k]); keep.Add(tri[k + 1]); keep.Add(tri[k + 2]);
                    }
                    cut.SetTriangles(keep, s);
                }
                if (gone == 0) continue;
                cut.RecalculateBounds();
                string path = $"{Folder}/{baseName}_StartCut.asset";
                if (AssetDatabase.LoadAssetAtPath<Mesh>(path) != null) AssetDatabase.DeleteAsset(path);
                AssetDatabase.CreateAsset(cut, path);
                mf.sharedMesh = cut;
                foreach (MeshCollider mc in mf.GetComponents<MeshCollider>()) mc.sharedMesh = cut;
                EditorUtility.SetDirty(mf);
                meshes++; removed += gone;
            }
            return meshes > 0 ? $"RoadNet cut under the strip: {meshes} meshes, {removed} triangles out" : "RoadNet NOT cut (no ROADNET_* mesh over the strip)";
        }

        // ------------------------------------------------------------------ the pad lamp: dead

        static string DeadLamp(Transform root, Data d)
        {
            Transform dress = root.Find("ForestStartDress");
            if (dress == null || d.deadLamp == null || d.deadLamp.Length < 2) return "pad lamp as it is";
            Transform pole = null;
            float best = 3f;
            foreach (Transform t in dress)
            {
                if (!t.name.StartsWith("LightPole", StringComparison.Ordinal)) continue;
                float dist = new Vector2(t.position.x - d.deadLamp[0], t.position.z - d.deadLamp[1]).magnitude;
                if (dist < best) { best = dist; pole = t; }
            }
            if (pole == null) return "pad lamp NOT found";
            int n = 0;
            foreach (ForestStartLamp l in pole.GetComponentsInChildren<ForestStartLamp>(true)) { UnityEngine.Object.DestroyImmediate(l); n++; }
            foreach (Light l in pole.GetComponentsInChildren<Light>(true)) { l.enabled = false; EditorUtility.SetDirty(l); n++; }
            foreach (Renderer r in pole.GetComponentsInChildren<Renderer>(true))
                if (r.name.StartsWith("Glow_", StringComparison.Ordinal) || r.name.StartsWith("Beacon_", StringComparison.Ordinal)) { r.enabled = false; n++; }
            return $"pad lamp dead ({n} lights, glows and its battery off)";
        }

        // ------------------------------------------------------------------ the Terrain

        static float SegDist(Vector2 p, Vector2 a, Vector2 b)
        {
            Vector2 ab = b - a;
            float t = ab.sqrMagnitude < 1e-8f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
            return (p - (a + ab * t)).magnitude;
        }

        static float EdgeDist(Vector2 p, float[] pts)
        {
            float d = float.MaxValue;
            int n = pts.Length / 2;
            for (int i = 0, j = n - 1; i < n; j = i++)
                d = Mathf.Min(d, SegDist(p, new Vector2(pts[j * 2], pts[j * 2 + 1]), new Vector2(pts[i * 2], pts[i * 2 + 1])));
            return d;
        }

        static bool InPoly(Vector2 p, float[] pts)
        {
            bool c = false;
            int n = pts.Length / 2;
            for (int i = 0, j = n - 1; i < n; j = i++)
            {
                float xi = pts[i * 2], zi = pts[i * 2 + 1], xj = pts[j * 2], zj = pts[j * 2 + 1];
                if ((zi > p.y) != (zj > p.y) && p.x < (xj - xi) * (p.y - zi) / (zj - zi) + xi) c = !c;
            }
            return c;
        }

        static void Box(float[] pts, out float x0, out float z0, out float x1, out float z1)
        {
            x0 = z0 = float.MaxValue; x1 = z1 = float.MinValue;
            for (int i = 0; i + 1 < pts.Length; i += 2)
            {
                x0 = Mathf.Min(x0, pts[i]); x1 = Mathf.Max(x1, pts[i]); z0 = Mathf.Min(z0, pts[i + 1]); z1 = Mathf.Max(z1, pts[i + 1]);
            }
        }

        /// <summary>The post's zone under snow: paint to the snow layers (soft edge), no grass; no Terrain trees on the
        /// road strip.</summary>
        static string Ground(Transform root, Data d)
        {
            if (d.zone == null || d.zone.Length < 6) return "Terrain as it is";
            Box(d.zone, out float zx0, out float zz0, out float zx1, out float zz1);
            float tx0 = float.MaxValue, tz0 = float.MaxValue, tx1 = float.MinValue, tz1 = float.MinValue;
            if (d.treeBand != null && d.treeBand.Length >= 6) Box(d.treeBand, out tx0, out tz0, out tx1, out tz1);
            float soft = Mathf.Max(0.5f, d.zoneSoft);
            int treesOut = 0, grassOut = 0, texels = 0;
            foreach (Terrain t in Terrain.activeTerrains.Where(t => t != null && t.terrainData != null && t.transform.IsChildOf(root)))
            {
                TerrainData td = t.terrainData;
                Vector3 o = t.transform.position, s = td.size;
                bool zoneHere = !(o.x > zx1 || o.z > zz1 || o.x + s.x < zx0 || o.z + s.z < zz0);
                bool bandHere = !(o.x > tx1 || o.z > tz1 || o.x + s.x < tx0 || o.z + s.z < tz0);
                if (!zoneHere && !bandHere) continue;

                if (bandHere)
                {
                    var keep = new List<TreeInstance>(td.treeInstanceCount);
                    foreach (TreeInstance ti in td.treeInstances)
                    {
                        Vector3 w = o + Vector3.Scale(ti.position, s);
                        if (w.x >= tx0 && w.x <= tx1 && w.z >= tz0 && w.z <= tz1 && InPoly(new Vector2(w.x, w.z), d.treeBand)) { treesOut++; continue; }
                        keep.Add(ti);
                    }
                    if (keep.Count != td.treeInstanceCount) td.SetTreeInstances(keep.ToArray(), false);
                }
                if (zoneHere)
                {
                    int dn = td.detailResolution;
                    for (int l = 0; l < td.detailPrototypes.Length; l++)
                    {
                        int[,] m = td.GetDetailLayer(0, 0, dn, dn, l);
                        bool changed = false;
                        for (int z = 0; z < dn; z++)
                            for (int x = 0; x < dn; x++)
                            {
                                if (m[z, x] == 0) continue;
                                float wx = o.x + (x + 0.5f) * s.x / dn, wz = o.z + (z + 0.5f) * s.z / dn;
                                if (wx < zx0 || wx > zx1 || wz < zz0 || wz > zz1 || !InPoly(new Vector2(wx, wz), d.zone)) continue;
                                m[z, x] = 0; grassOut++; changed = true;
                            }
                        if (changed) td.SetDetailLayer(0, 0, l, m);
                    }

                    int n = td.alphamapResolution, L = td.alphamapLayers;
                    var target = new float[L];
                    float sum = 0f;
                    foreach (PaintDef p in d.paint ?? new PaintDef[0])
                    {
                        int layer = Array.FindIndex(td.terrainLayers, x => x != null && x.name == p.layer);
                        if (layer < 0) continue;
                        target[layer] += p.w; sum += p.w;
                    }
                    if (sum > 0f)
                    {
                        for (int l = 0; l < L; l++) target[l] /= sum;
                        int x0 = Mathf.Max(0, Mathf.FloorToInt((zx0 - o.x) / s.x * n)), x1 = Mathf.Min(n - 1, Mathf.CeilToInt((zx1 - o.x) / s.x * n));
                        int z0 = Mathf.Max(0, Mathf.FloorToInt((zz0 - o.z) / s.z * n)), z1 = Mathf.Min(n - 1, Mathf.CeilToInt((zz1 - o.z) / s.z * n));
                        if (x1 >= x0 && z1 >= z0)
                        {
                            float[,,] map = td.GetAlphamaps(x0, z0, x1 - x0 + 1, z1 - z0 + 1);
                            for (int z = 0; z <= z1 - z0; z++)
                                for (int x = 0; x <= x1 - x0; x++)
                                {
                                    var p = new Vector2(o.x + (x0 + x + 0.5f) * s.x / n, o.z + (z0 + z + 0.5f) * s.z / n);
                                    if (!InPoly(p, d.zone)) continue;
                                    float k = Mathf.SmoothStep(0f, 1f, EdgeDist(p, d.zone) / soft);
                                    if (k <= 0f) continue;
                                    for (int l = 0; l < L; l++) map[z, x, l] = map[z, x, l] * (1f - k) + target[l] * k;
                                    texels++;
                                }
                            td.SetAlphamaps(x0, z0, map);
                        }
                    }
                }
                EditorUtility.SetDirty(td);
            }
            return $"Terrain: {texels} paint texels to snow, {grassOut} grass cells and {treesOut} trees off the post / the road strip";
        }

        // ------------------------------------------------------------------ the guard house prefab

        static Vector3 V(float[] a) => a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero;

        /// <summary>Renderer bounds of a transform's meshes in another transform's space.</summary>
        static Bounds LocalBounds(Transform t, Transform space)
        {
            Bounds b = default(Bounds);
            bool first = true;
            foreach (MeshFilter f in t.GetComponentsInChildren<MeshFilter>(true))
            {
                if (f.sharedMesh == null) continue;
                Matrix4x4 m = space.worldToLocalMatrix * f.transform.localToWorldMatrix;
                Bounds mb = f.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = new Vector3((i & 1) == 0 ? mb.min.x : mb.max.x, (i & 2) == 0 ? mb.min.y : mb.max.y, (i & 4) == 0 ? mb.min.z : mb.max.z);
                    Vector3 w = m.MultiplyPoint3x4(c);
                    if (first) { b = new Bounds(w, Vector3.zero); first = false; } else b.Encapsulate(w);
                }
            }
            return b;
        }

        /// <summary>StartWache.prefab from StartBooth.prefab (its scripts, door, lamp and battery stay): see the class note.
        /// Rebuilt each call; reports what it kept, swapped and could not find.</summary>
        public static string BuildWachePrefab()
        {
            Data d = Load();
            if (d == null || d.wache == null) return $"[Snow] Start post wache: {DataPath} not found or has no wache.";
            WacheDef w = d.wache;
            if (AssetDatabase.LoadAssetAtPath<GameObject>(w.template) == null) return $"[Snow] Start post wache: template {w.template} MISSING.";
            ModelImport(w.fbx);
            var meshes = new Dictionary<string, Mesh>();
            var poses = new Dictionary<string, Matrix4x4>();     // each part's node pose in the FBX
            var fbxRoot = AssetDatabase.LoadAssetAtPath<GameObject>(w.fbx);
            if (fbxRoot != null)
                foreach (MeshFilter f in fbxRoot.GetComponentsInChildren<MeshFilter>(true))
                    if (f.sharedMesh != null)
                    {
                        meshes[f.name] = f.sharedMesh;
                        Matrix4x4 m = fbxRoot.transform.worldToLocalMatrix * f.transform.localToWorldMatrix;
                        poses[f.name] = m;
                    }
            if (meshes.Count == 0) return $"[Snow] Start post wache: no meshes in {w.fbx}.";
            var mats = Mats(d);
            if (AssetDatabase.LoadAssetAtPath<GameObject>(w.prefab) != null) AssetDatabase.DeleteAsset(w.prefab);
            if (!AssetDatabase.CopyAsset(w.template, w.prefab)) return $"[Snow] Start post wache: could not copy {w.template} to {w.prefab}.";
            GameObject root = PrefabUtility.LoadPrefabContents(w.prefab);
            var log = new List<string>();
            Func<string, Transform> Find = n => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == n);

            // where the booth's lamp was (its lights follow the lamp to the door)
            Transform oldLamp = Find("Lamp_Booth") ?? Find("Lens_Booth");
            Vector3 oldLampPos = oldLamp != null ? root.transform.TransformPoint(LocalBounds(oldLamp, root.transform).center) : root.transform.position;

            var lightWas = root.GetComponentsInChildren<Light>(true).ToDictionary(l => l, l => l.transform.position);
            foreach (string r in w.remove ?? new string[0])
            {
                Transform t = Find(r);
                if (t != null) { UnityEngine.Object.DestroyImmediate(t.gameObject); log.Add("removed " + r); }
            }
            foreach (PartDef p in w.parts ?? new PartDef[0])
            {
                if (!meshes.TryGetValue(p.mesh, out Mesh mesh)) { log.Add("MISSING mesh " + p.mesh); continue; }
                Transform t = string.IsNullOrEmpty(p.target) ? null : Find(p.target);
                GameObject go;
                if (t != null) go = t.gameObject;
                else
                {
                    go = new GameObject(p.mesh);
                    go.transform.SetParent(root.transform, false);
                    if (!string.IsNullOrEmpty(p.target)) log.Add($"{p.target} not in the template: {p.mesh} added as a new part");
                }
                // the part's mesh is in the house's own space: the object sits on the prefab root (with the FBX node's own pose)
                Matrix4x4 pose = poses.TryGetValue(p.mesh, out Matrix4x4 pm) ? pm : Matrix4x4.identity;
                go.transform.SetPositionAndRotation(root.transform.TransformPoint((Vector3)pose.GetColumn(3)), root.transform.rotation * pose.rotation);
                go.transform.localScale = pose.lossyScale;
                MeshFilter mf = go.GetComponent<MeshFilter>();
                if (mf == null) mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = mesh;
                MeshRenderer mr = go.GetComponent<MeshRenderer>();
                if (mr == null) mr = go.AddComponent<MeshRenderer>();
                Material[] keep = mr.sharedMaterials;
                var ms = new Material[p.materials.Length];
                for (int i = 0; i < ms.Length; i++)
                {
                    string n = p.materials[i];
                    ms[i] = n.EndsWith("Keep", StringComparison.Ordinal) ? (keep.Length > 0 ? keep[Mathf.Min(i, keep.Length - 1)] : null)
                                                                          : (mats.TryGetValue(n, out Material m) ? m : null);
                    if (ms[i] == null) log.Add($"{p.mesh}: material {n} MISSING");
                }
                mr.sharedMaterials = ms;
                mr.shadowCastingMode = p.mesh.Contains("Glow") ? ShadowCastingMode.Off : ShadowCastingMode.On;
                foreach (Collider c in go.GetComponents<Collider>()) UnityEngine.Object.DestroyImmediate(c);
                if (p.collider == "mesh") go.AddComponent<MeshCollider>().sharedMesh = mesh;
                log.Add(t != null ? $"{p.target} -> {p.mesh}" : $"+{p.mesh}");
            }

            // the booth's door into the house's door: closed leaf in the opening (along local z), bottom on the floor
            Transform door = Find("IX_Door");
            if (door != null && w.door != null)
            {
                Bounds b = LocalBounds(door, root.transform);
                if (b.size.x > b.size.z * 1.5f)
                {
                    door.RotateAround(door.position, root.transform.up, 90f);
                    b = LocalBounds(door, root.transform);
                    log.Add("IX_Door turned 90 deg to lie in the road wall");
                }
                Vector3 c = V(w.door.centre);
                Vector3 off = new Vector3(c.x - b.center.x, c.y - b.min.y, c.z - b.center.z);
                door.position += root.transform.TransformVector(off);
                b = LocalBounds(door, root.transform);
                log.Add($"IX_Door in the opening: local x {b.min.x:0.00}..{b.max.x:0.00}, y {b.min.y:0.00}..{b.max.y:0.00}, z {b.min.z:0.00}..{b.max.z:0.00} " +
                        $"(opening x {c.x:0.00}, y {c.y:0.00}..{c.y + w.door.height:0.00}, z {c.z - w.door.width / 2:0.00}..{c.z + w.door.width / 2:0.00})");
            }
            else log.Add("IX_Door NOT found: the house's door stays open");

            // the booth's lights to the lamp over the door
            Vector3 lampPos = root.transform.TransformPoint(V(w.lamp));
            int moved = 0;
            foreach (var kv in lightWas)
                if (kv.Key != null && (kv.Value - oldLampPos).magnitude < 1.5f) { kv.Key.transform.position = lampPos; moved++; }
            log.Add($"{moved} lamp lights to the door lamp");

            // warm light inside, the stove's glow light
            foreach (LightDef ld in w.lights ?? new LightDef[0])
            {
                var go = new GameObject(ld.name);
                go.transform.SetParent(root.transform, false);
                go.transform.localPosition = V(ld.pos);
                var l = go.AddComponent<Light>();
                l.type = LightType.Point;
                l.color = new Color(ld.color[0], ld.color[1], ld.color[2]);
                l.intensity = ld.intensity;
                l.range = ld.range;
                l.shadows = LightShadows.None;
                l.renderingLayerMask = 2;
            }
            bool smoke = Smoke(root.transform, V(w.smoke), w.wind);
            log.Add(smoke ? "stove smoke" : $"stove smoke OFF (no {SmokeMaterial})");

            // what else the template carries (for a look: triggers sized for the booth, its interior)
            var rest = root.GetComponentsInChildren<Collider>(true).Where(c => !(c is MeshCollider mc && meshes.ContainsValue(mc.sharedMesh)))
                           .Select(c => $"{c.name}:{c.GetType().Name}{(c.isTrigger ? "(trigger)" : "")}").ToArray();
            if (rest.Length > 0) log.Add("template colliders kept: " + string.Join(", ", rest));

            PrefabUtility.SaveAsPrefabAsset(root, w.prefab);
            PrefabUtility.UnloadPrefabContents(root);
            AssetDatabase.SaveAssets();
            string msg = $"[Snow] Start post wache: {w.prefab} from {w.template}: " + string.Join("; ", log) + ".";
            Debug.Log(msg);
            return msg;
        }

        /// <summary>The stove pipe's smoke: the hut's (Particle System with M_Smoke), small, drifting downwind.</summary>
        static bool Smoke(Transform parent, Vector3 local, float[] wind)
        {
            var smokeMat = AssetDatabase.LoadAssetAtPath<Material>(SmokeMaterial);
            if (smokeMat == null) return false;
            var sgo = new GameObject("Smoke_Stove");
            sgo.transform.SetParent(parent, false);
            sgo.transform.localPosition = local;
            sgo.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);
            var ps = sgo.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(6f, 9f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 0.7f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.25f, 0.45f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.startColor = new Color(0.66f, 0.66f, 0.68f, 0.7f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 60;
            var em = ps.emission; em.rateOverTime = 5f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 6f; sh.radius = 0.06f;
            Vector3 wv = wind != null && wind.Length >= 3 ? new Vector3(wind[0], 0f, wind[2]) : new Vector3(0.74f, 0f, 0.67f);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(wv.x * 0.5f, wv.x * 0.9f); vel.y = new ParticleSystem.MinMaxCurve(0.1f, 0.2f);
            vel.z = new ParticleSystem.MinMaxCurve(wv.z * 0.5f, wv.z * 0.9f);
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 0.5f, 1f, 4.5f));
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.75f, 0.1f), new GradientAlphaKey(0.3f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var noise = ps.noise; noise.enabled = true; noise.strength = 0.2f; noise.frequency = 0.3f;
            var pr = sgo.GetComponent<ParticleSystemRenderer>();
            pr.sharedMaterial = smokeMat;
            pr.shadowCastingMode = ShadowCastingMode.Off;
            return true;
        }
    }
}
