using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Snow.EditorTools
{
    /// <summary>
    /// Forest integration: the NW river gorge (28.10.2026, package source/assets/forest_gorge_v1; user: the river under
    /// Bridge30 as a stepped rock gorge like the road canyon frame, along the whole river, no way out but the bridge).
    /// Reads <see cref="DataPath"/> and builds under <see cref="RootName"/>:
    ///  - the rock model <c>Forest_Gorge.fbx</c> (stacked rock slabs in three tiers up to the rim, scree at the wall feet and in
    ///    the water, the stones under Bridge30's two bents), world space, one object per 50 m of the river and material
    ///    (<c>GORGE_S07_RockB</c> ...): URP Lit, point-filtered textures, no highlights, a MeshCollider on each;
    ///  - Terrain trees and grass out of the gorge (mask 1: walls and ledges, 3: the floor), spruces on the wide ledges;
    ///  - paint on mask 1: TL_Rock from 42° (all rock at 52°), TL_ForestFloor (the winter snow) below; the floor keeps
    ///    the creek bed's paint (ForestStreamsStep).
    /// The ground is the package's World Sync ground delta (kept through re-bakes by the hand sculpt layer); the water is the
    /// NW_gorge creek of ForestStreams.json. In the build: after ForestSlopeRock.ClearRock (its rock sets on the walls go).
    /// Idempotent: the root is rebuilt and the mask cleared each run.
    /// </summary>
    public static class ForestGorgeStep
    {
        public const string DataPath = "Assets/Snow/Levels/Forest/Gorge/ForestGorge.json";
        public const string RootName = "ForestGorge";
        const string Folder = "Assets/Snow/Levels/Forest/Gorge";

        [Serializable] class MaskInfo { public string file; public int i0, j0, nx, nz; public float x0, z0, step; }
        [Serializable] class LedgeTree { public string prefab; public float x, z, scale, yaw; }
        [Serializable] class MatDef { public string key, name, texture; public float[] color; }   // key: the object name's suffix
        [Serializable] class Data { public string model; public MaskInfo mask; public MatDef[] materials; public LedgeTree[] ledgeTrees; }

        [MenuItem("Tools/Snow/Forest/Gorge")]
        static void Menu()
        {
            Transform root = GameObject.Find("Forest")?.transform;
            if (root == null) { Debug.LogError("[Snow] Forest gorge: no Forest root in the open scene."); return; }
            Debug.Log(Run(root));
        }

        public static string Run(Transform root)
        {
            if (!File.Exists(DataPath)) return $"[Snow] Forest gorge: {DataPath} not found; nothing done.";
            Data d = JsonUtility.FromJson<Data>(File.ReadAllText(DataPath));
            Transform old = root.Find(RootName);
            if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var group = new GameObject(RootName).transform;
            group.SetParent(root, false);
            Terrain terrain = root.GetComponentInChildren<Terrain>(true);
            int layer = terrain != null ? terrain.gameObject.layer : 0;

            string model = Model(group, d, layer);
            string ground = Ground(root, d);
            AssetDatabase.SaveAssets();
            string log = $"[Snow] Forest gorge ({DataPath}): {model}; {ground}.";
            Debug.Log(log);
            return log;
        }

        // ------------------------------------------------------------------ the rock model

        static string Model(Transform group, Data d, int layer)
        {
            string path = d.model;
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
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (asset == null) return $"MISSING {path}";
            var mats = new Dictionary<string, Material>();
            foreach (MatDef m in d.materials ?? new MatDef[0]) mats[m.key] = Mat(m);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, group);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "Forest_Gorge";
            go.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            go.transform.localScale = Vector3.one;
            int objects = 0, tris = 0, missing = 0;
            foreach (MeshRenderer r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                GameObject o = r.gameObject;
                string key = o.name.Substring(o.name.LastIndexOf('_') + 1);          // GORGE_S07_RockB -> RockB
                if (!mats.TryGetValue(key, out Material m) || m == null) { missing++; continue; }
                r.sharedMaterial = m;
                r.shadowCastingMode = ShadowCastingMode.On;
                r.receiveShadows = true;
                o.layer = layer;
                Mesh mesh = o.GetComponent<MeshFilter>().sharedMesh;
                o.AddComponent<MeshCollider>().sharedMesh = mesh;
                GameObjectUtility.SetStaticEditorFlags(o, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
                tris += mesh != null ? mesh.triangles.Length / 3 : 0;
                objects++;
            }
            return $"{objects} rock objects, {tris} triangles" + (missing > 0 ? $", {missing} without a material" : "");
        }

        /// <summary>URP Lit with a point-filtered pixel texture, a tint, no highlights and no reflections.</summary>
        static Material Mat(MatDef def)
        {
            string tp = $"{Folder}/{def.texture}";
            if (AssetImporter.GetAtPath(tp) is TextureImporter ti &&
                (ti.filterMode != FilterMode.Point || !ti.mipmapEnabled || ti.wrapMode != TextureWrapMode.Repeat || ti.textureCompression != TextureImporterCompression.Uncompressed))
            {
                ti.filterMode = FilterMode.Point; ti.mipmapEnabled = true; ti.wrapMode = TextureWrapMode.Repeat;
                ti.textureCompression = TextureImporterCompression.Uncompressed; ti.sRGBTexture = true;
                ti.SaveAndReimport();
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
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(tp));
            Color c = def.color != null && def.color.Length >= 3 ? new Color(def.color[0], def.color[1], def.color[2], 1f) : Color.white;
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Smoothness", 0.05f);
            m.SetFloat("_Metallic", 0f);
            m.SetFloat("_SpecularHighlights", 0f); m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            m.SetFloat("_EnvironmentReflections", 0f); m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------ the Terrain: trees, grass, paint

        static string Ground(Transform root, Data d)
        {
            MaskInfo mi = d.mask;
            string mp = $"{Folder}/{mi.file}";
            if (!File.Exists(mp)) return $"no mask {mp}";
            byte[] mask = File.ReadAllBytes(mp);
            if (mask.Length != mi.nx * mi.nz) return $"mask {mask.Length} bytes, {mi.nx * mi.nz} expected";
            int M(float x, float z)
            {
                int i = Mathf.RoundToInt((x - mi.x0) / mi.step) - mi.i0, j = Mathf.RoundToInt((z - mi.z0) / mi.step) - mi.j0;
                return i < 0 || j < 0 || i >= mi.nx || j >= mi.nz ? 0 : mask[j * mi.nx + i];
            }
            float bx0 = mi.x0 + mi.i0 * mi.step, bz0 = mi.z0 + mi.j0 * mi.step, bx1 = bx0 + mi.nx * mi.step, bz1 = bz0 + mi.nz * mi.step;
            int treesOut = 0, ledge = 0, grassOut = 0, rockTex = 0, floorTex = 0;
            foreach (Terrain t in Terrain.activeTerrains.Where(t => t != null && t.terrainData != null && t.transform.IsChildOf(root)))
            {
                TerrainData td = t.terrainData;
                Vector3 o = t.transform.position, s = td.size;
                if (o.x > bx1 || o.z > bz1 || o.x + s.x < bx0 || o.z + s.z < bz0) continue;
                TreePrototype[] protos = td.treePrototypes;

                var keep = new List<TreeInstance>(td.treeInstanceCount);
                foreach (TreeInstance ti in td.treeInstances)
                {
                    Vector3 w = o + Vector3.Scale(ti.position, s);
                    int k = M(w.x, w.z);
                    if (k == 1 || k == 3) { treesOut++; continue; }
                    keep.Add(ti);
                }
                foreach (LedgeTree lt in d.ledgeTrees ?? new LedgeTree[0])
                {
                    if (lt.x < o.x || lt.z < o.z || lt.x > o.x + s.x || lt.z > o.z + s.z) continue;
                    int p = Array.FindIndex(protos, q => q.prefab != null && q.prefab.name == lt.prefab);
                    if (p < 0) continue;
                    keep.Add(new TreeInstance
                    {
                        prototypeIndex = p,
                        position = new Vector3((lt.x - o.x) / s.x, t.SampleHeight(new Vector3(lt.x, 0f, lt.z)) / s.y, (lt.z - o.z) / s.z),
                        widthScale = lt.scale, heightScale = lt.scale, rotation = lt.yaw,
                        color = Color.white, lightmapColor = Color.white,
                    });
                    ledge++;
                }
                td.SetTreeInstances(keep.ToArray(), false);

                int dn = td.detailResolution;
                for (int l = 0; l < td.detailPrototypes.Length; l++)
                {
                    int[,] m = td.GetDetailLayer(0, 0, dn, dn, l);
                    bool changed = false;
                    for (int z = 0; z < dn; z++)
                        for (int x = 0; x < dn; x++)
                        {
                            if (m[z, x] == 0) continue;
                            int k = M(o.x + (x + 0.5f) * s.x / dn, o.z + (z + 0.5f) * s.z / dn);
                            if (k != 1 && k != 3) continue;
                            m[z, x] = 0; grassOut++; changed = true;
                        }
                    if (changed) td.SetDetailLayer(0, 0, l, m);
                }

                int rock = Array.FindIndex(td.terrainLayers, x => x != null && x.name == "TL_Rock");
                int floorL = Array.FindIndex(td.terrainLayers, x => x != null && x.name == "TL_ForestFloor");
                if (rock >= 0 && floorL >= 0)
                {
                    int n = td.alphamapResolution, L = td.alphamapLayers;
                    float[,,] map = td.GetAlphamaps(0, 0, n, n);
                    for (int z = 0; z < n; z++)
                        for (int x = 0; x < n; x++)
                        {
                            float u = (x + 0.5f) / n, v = (z + 0.5f) / n;
                            if (M(o.x + u * s.x, o.z + v * s.z) != 1) continue;
                            float k = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(42f, 52f, td.GetSteepness(u, v)));
                            for (int l = 0; l < L; l++) map[z, x, l] = l == rock ? k : l == floorL ? 1f - k : 0f;
                            if (k > 0.5f) rockTex++; else floorTex++;
                        }
                    td.SetAlphamaps(0, 0, map);
                }
                EditorUtility.SetDirty(td);
            }
            return $"{treesOut} Terrain trees and {grassOut} grass cells out of the gorge, {ledge} ledge spruces, {rockTex} rock / {floorTex} snow texels";
        }
    }
}
