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
    /// Forest integration: the players' base yard brought up to the Blender concept of 28.10.2026 (package
    /// source/assets/forest_base_yard_v1; user: the yard looked empty - a landmark, closed edges, snow the way a plough leaves it,
    /// zones at the walls, dark masses and a few accents). Reads <see cref="DataPath"/> and builds under <see cref="RootName"/>:
    ///  - the package model <c>Forest_BaseYard.fbx</c> (world space, one object per element, <c>BY_*</c>): the radome on the
    ///    main building, the boiler house with its chimney and oil tank, the workshop and lean-to, eleven containers, drums,
    ///    pallets, gas bottles, skip and bins, bollards, snow poles, grit bin, the plough blade, the station sign, roof kit,
    ///    warm window panes, the kerb along the asphalt, the yard snow (banks, end piles, lee drifts, BY_SnowLayer_*) and the
    ///    snow on the roofs with cornices and icicles. URP Lit, pixel textures, materials M_Base* of the package folder;
    ///    MeshColliders where the data says so; the yard snow, the kerb and the plough lumps on the terrain's layer;
    ///  - copies of project models without their prefabs (no scripts, no network ids, doors shut): two garages, the
    ///    service van at the door, the plough van, a car, the old car snowed in, the gate boom with its beacon; materials of
    ///    the project by name; crates and a cable drum as prefabs;
    ///  - the entry light, the chimney smoke (the hut's way: Particle System with M_Smoke);
    ///  - Terrain: yard saplings, trees and grass off the new buildings, the storage and the lanes; paths, the two driven
    ///    lanes and their ruts painted (TL_TrailTrack, TL_TrailSoil).
    /// In the build after ForestPlacesStep (every step that plants trees or paints the yard is done by then) and before
    /// ForestTreeCollidersStep and ForestWinterStep (the snow cover's layer goes on the new renderers; the glows and glass
    /// keep off it by their names). Idempotent: the root is rebuilt, the Terrain changes are the same each run.
    /// </summary>
    public static class ForestBaseYardStep
    {
        public const string DataPath = "Assets/Snow/Levels/Forest/BaseYard/BaseYard.json";
        public const string RootName = "ForestBaseYard";
        const string Folder = "Assets/Snow/Levels/Forest/BaseYard";
        const string SmokeMaterial = "Assets/Snow/Items/Smoke/Materials/M_Smoke.mat";

        [Serializable] class MatDef { public string name, texture, filter; public float[] color, emission; public float smoothness, metallic; }
        [Serializable] class ObjDef { public string name, collider; public string[] materials; public bool ground; }
        [Serializable] class PartMats { public string mesh; public string[] materials; }
        [Serializable] class ModelDef { public string model, collider; public float[] pos; public float yaw; public PartMats[] parts; }
        [Serializable] class PrefabDef { public string prefab; public float[] pos; public float yaw; }
        [Serializable] class LightDef { public string name; public float[] pos, color; public float intensity, range; }
        [Serializable] class SmokeDef { public float[] pos, wind; }
        [Serializable] class Stroke { public string n, layer; public float w, soft; public float[] p; }
        [Serializable] class Clear { public float w; public float[] p; }      // w > 0: a band w wide along p, else the polygon p
        [Serializable]
        class Data
        {
            public string model;
            public MatDef[] materials;
            public ObjDef[] objects;
            public ModelDef[] models;
            public PrefabDef[] prefabs;
            public LightDef[] lights;
            public SmokeDef smoke;
            public Stroke[] strokes;
            public Clear[] clear;
        }

        [MenuItem("Tools/Snow/Forest/Base Yard")]
        static void Menu()
        {
            Transform root = GameObject.Find("Forest")?.transform;
            if (root == null) { Debug.LogError("[Snow] Forest base yard: no Forest root in the open scene."); return; }
            Debug.Log(Run(root));
        }

        public static string Run(Transform root)
        {
            if (!File.Exists(DataPath)) return $"[Snow] Forest base yard: {DataPath} not found; nothing done.";
            Data d = JsonUtility.FromJson<Data>(File.ReadAllText(DataPath));
            Transform old = root.Find(RootName);
            if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var group = new GameObject(RootName).transform;
            group.SetParent(root, false);
            Terrain terrain = root.GetComponentInChildren<Terrain>(true);
            int groundLayer = terrain != null ? terrain.gameObject.layer : 0;

            var mats = new Dictionary<string, Material>();
            foreach (MatDef m in d.materials ?? new MatDef[0]) mats[m.name] = Mat(m);
            string model = Model(group, d, mats, groundLayer);
            string kit = Kit(group, d);
            string extra = Extras(group, d);
            string ground = Ground(root, d);
            AssetDatabase.SaveAssets();
            string log = $"[Snow] Forest base yard ({DataPath}): {model}; {kit}; {extra}; {ground}.";
            Debug.Log(log);
            return log;
        }

        // ------------------------------------------------------------------ materials

        /// <summary>URP Lit, a pixel texture (point; the yard snow bilinear like the Terrain), a tint, no highlights, an
        /// emission where the data has one.</summary>
        static Material Mat(MatDef def)
        {
            Texture2D tex = null;
            if (!string.IsNullOrEmpty(def.texture))
            {
                string tp = $"{Folder}/{def.texture}";
                bool point = def.filter != "bilinear";
                if (AssetImporter.GetAtPath(tp) is TextureImporter ti &&
                    (ti.filterMode != (point ? FilterMode.Point : FilterMode.Bilinear) || !ti.mipmapEnabled || ti.wrapMode != TextureWrapMode.Repeat ||
                     ti.textureCompression != TextureImporterCompression.Uncompressed || !ti.sRGBTexture))
                {
                    ti.filterMode = point ? FilterMode.Point : FilterMode.Bilinear; ti.mipmapEnabled = true; ti.wrapMode = TextureWrapMode.Repeat;
                    ti.textureCompression = TextureImporterCompression.Uncompressed; ti.sRGBTexture = true; ti.anisoLevel = point ? 1 : 8;
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

        static readonly Dictionary<string, Material> _project = new Dictionary<string, Material>();

        /// <summary>A project material by its name (the kit models keep the look they have in their prefabs).</summary>
        static Material ProjectMat(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            if (_project.TryGetValue(name, out Material m)) return m;
            m = AssetDatabase.FindAssets($"t:Material {name}")
                .Select(g => AssetDatabase.GUIDToAssetPath(g))
                .Where(p => Path.GetFileNameWithoutExtension(p) == name)
                .OrderBy(p => p.StartsWith("Assets/Locations/Forest", StringComparison.Ordinal) ? 0 : p.StartsWith("Assets/Kit", StringComparison.Ordinal) ? 1 : 2)
                .Select(p => AssetDatabase.LoadAssetAtPath<Material>(p)).FirstOrDefault(x => x != null);
            _project[name] = m;
            return m;
        }

        static Material Resolve(Dictionary<string, Material> mats, string name) =>
            mats.TryGetValue(name, out Material m) && m != null ? m : ProjectMat(name);

        static void Static(GameObject o) =>
            GameObjectUtility.SetStaticEditorFlags(o, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);

        // ------------------------------------------------------------------ the package model

        static string Model(Transform group, Data d, Dictionary<string, Material> mats, int groundLayer)
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
            var defs = (d.objects ?? new ObjDef[0]).ToDictionary(o => o.name, o => o);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, group);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "Forest_BaseYard";
            go.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            go.transform.localScale = Vector3.one;
            int objects = 0, tris = 0, colliders = 0, missing = 0;
            foreach (MeshRenderer r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                GameObject o = r.gameObject;
                if (!defs.TryGetValue(o.name, out ObjDef def)) { missing++; continue; }
                Material[] ms = def.materials.Select(n => Resolve(mats, n)).ToArray();
                if (ms.Any(x => x == null)) missing++;
                r.sharedMaterials = ms;
                r.shadowCastingMode = def.ground ? ShadowCastingMode.Off : ShadowCastingMode.On;
                r.receiveShadows = true;
                if (def.ground) o.layer = groundLayer;
                Mesh mesh = o.GetComponent<MeshFilter>().sharedMesh;
                if (def.collider == "mesh" && mesh != null) { o.AddComponent<MeshCollider>().sharedMesh = mesh; colliders++; }
                Static(o);
                tris += mesh != null ? mesh.triangles.Length / 3 : 0;
                objects++;
            }
            return $"{objects} package objects ({tris} triangles, {colliders} colliders" + (missing > 0 ? $", {missing} without data or material" : "") + ")";
        }

        // ------------------------------------------------------------------ project models and props

        static string Kit(Transform group, Data d)
        {
            int models = 0, props = 0, missing = 0;
            var kit = new GameObject("Kit").transform;
            kit.SetParent(group, false);
            foreach (ModelDef md in d.models ?? new ModelDef[0])
            {
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(md.model);
                if (asset == null) { missing++; continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, kit);
                PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                go.transform.SetPositionAndRotation(new Vector3(md.pos[0], md.pos[1], md.pos[2]), Quaternion.Euler(0f, md.yaw, 0f));
                var parts = (md.parts ?? new PartMats[0]).ToDictionary(p => p.mesh, p => p.materials);
                foreach (MeshRenderer r in go.GetComponentsInChildren<MeshRenderer>(true))
                {
                    MeshFilter mf = r.GetComponent<MeshFilter>();
                    Mesh mesh = mf != null ? mf.sharedMesh : null;
                    if (mesh != null && parts.TryGetValue(mesh.name, out string[] names))
                    {
                        Material[] ms = names.Select(n => ProjectMat(n)).ToArray();
                        if (ms.All(x => x != null)) r.sharedMaterials = ms; else missing++;
                    }
                    if (md.collider == "mesh" && mesh != null && r.GetComponent<Collider>() == null) r.gameObject.AddComponent<MeshCollider>().sharedMesh = mesh;
                    Static(r.gameObject);
                }
                models++;
            }
            foreach (PrefabDef pd in d.prefabs ?? new PrefabDef[0])
            {
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(pd.prefab);
                if (asset == null) { missing++; continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, kit);
                go.transform.SetPositionAndRotation(new Vector3(pd.pos[0], pd.pos[1], pd.pos[2]), Quaternion.Euler(0f, pd.yaw, 0f));
                props++;
            }
            return $"{models} project models, {props} props" + (missing > 0 ? $", {missing} MISSING (model, prefab or material)" : "");
        }

        // ------------------------------------------------------------------ light and smoke

        static string Extras(Transform group, Data d)
        {
            int lights = 0;
            foreach (LightDef ld in d.lights ?? new LightDef[0])
            {
                var go = new GameObject(ld.name);
                go.transform.SetParent(group, false);
                go.transform.position = new Vector3(ld.pos[0], ld.pos[1], ld.pos[2]);
                var l = go.AddComponent<Light>();
                l.type = LightType.Point;
                l.color = new Color(ld.color[0], ld.color[1], ld.color[2]);
                l.intensity = ld.intensity;
                l.range = ld.range;
                l.shadows = LightShadows.None;
                lights++;
            }
            bool smoke = Smoke(group, d.smoke);
            return $"{lights} light, chimney smoke {(smoke ? "on" : "OFF (no " + SmokeMaterial + ")")}";
        }

        /// <summary>The boiler house chimney: the hut's smoke (ForestHutDressStep) scaled to a 22 m stack, drifting downwind.</summary>
        static bool Smoke(Transform group, SmokeDef s)
        {
            var smokeMat = AssetDatabase.LoadAssetAtPath<Material>(SmokeMaterial);
            if (s == null || s.pos == null || smokeMat == null) return false;
            var sgo = new GameObject("BoilerSmoke");
            sgo.transform.SetParent(group, false);
            sgo.transform.position = new Vector3(s.pos[0], s.pos[1], s.pos[2]);
            sgo.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);
            var ps = sgo.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.loop = true; main.playOnAwake = true; main.prewarm = true;
            main.startLifetime = new ParticleSystem.MinMaxCurve(10f, 14f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.0f, 1.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(1.0f, 1.6f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.startColor = new Color(0.78f, 0.78f, 0.80f, 0.75f);        // steam, light against the overcast
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = 160;
            var em = ps.emission; em.rateOverTime = 7f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 5f; sh.radius = 0.35f;
            Vector3 w = s.wind != null && s.wind.Length >= 3 ? new Vector3(s.wind[0], 0f, s.wind[2]) : new Vector3(0.8f, 0f, 0.6f);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(w.x * 0.9f, w.x * 1.4f); vel.y = new ParticleSystem.MinMaxCurve(0.15f, 0.3f);
            vel.z = new ParticleSystem.MinMaxCurve(w.z * 0.9f, w.z * 1.4f);
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 0.6f, 1f, 5.5f));
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.8f, 0.08f), new GradientAlphaKey(0.35f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var noise = ps.noise; noise.enabled = true; noise.strength = 0.35f; noise.frequency = 0.25f;
            var pr = sgo.GetComponent<ParticleSystemRenderer>();
            pr.sharedMaterial = smokeMat;
            pr.shadowCastingMode = ShadowCastingMode.Off;
            return true;
        }

        // ------------------------------------------------------------------ the Terrain

        static float SegDist(Vector2 p, Vector2 a, Vector2 b)
        {
            Vector2 ab = b - a;
            float t = ab.sqrMagnitude < 1e-8f ? 0f : Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
            return (p - (a + ab * t)).magnitude;
        }

        static float PolyDist(Vector2 p, float[] pts)
        {
            float d = float.MaxValue;
            for (int i = 0; i + 3 < pts.Length; i += 2)
                d = Mathf.Min(d, SegDist(p, new Vector2(pts[i], pts[i + 1]), new Vector2(pts[i + 2], pts[i + 3])));
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

        static bool Cleared(Data d, Vector2 p) =>
            (d.clear ?? new Clear[0]).Any(c => c.w > 0f ? PolyDist(p, c.p) <= c.w * 0.5f : InPoly(p, c.p));

        static string Ground(Transform root, Data d)
        {
            // the yard's box (Unity x / z), with a margin
            var all = (d.clear ?? new Clear[0]).SelectMany(c => c.p).Concat((d.strokes ?? new Stroke[0]).SelectMany(s => s.p)).ToArray();
            float bx0 = float.MaxValue, bz0 = float.MaxValue, bx1 = float.MinValue, bz1 = float.MinValue;
            for (int i = 0; i + 1 < all.Length; i += 2)
            {
                bx0 = Mathf.Min(bx0, all[i]); bx1 = Mathf.Max(bx1, all[i]); bz0 = Mathf.Min(bz0, all[i + 1]); bz1 = Mathf.Max(bz1, all[i + 1]);
            }
            bx0 -= 5f; bz0 -= 5f; bx1 += 5f; bz1 += 5f;
            int treesOut = 0, grassOut = 0, texels = 0;
            foreach (Terrain t in Terrain.activeTerrains.Where(t => t != null && t.terrainData != null && t.transform.IsChildOf(root)))
            {
                TerrainData td = t.terrainData;
                Vector3 o = t.transform.position, s = td.size;
                if (o.x > bx1 || o.z > bz1 || o.x + s.x < bx0 || o.z + s.z < bz0) continue;

                var keep = new List<TreeInstance>(td.treeInstanceCount);
                foreach (TreeInstance ti in td.treeInstances)
                {
                    Vector3 w = o + Vector3.Scale(ti.position, s);
                    if (w.x >= bx0 && w.x <= bx1 && w.z >= bz0 && w.z <= bz1 && Cleared(d, new Vector2(w.x, w.z))) { treesOut++; continue; }
                    keep.Add(ti);
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
                            float wx = o.x + (x + 0.5f) * s.x / dn, wz = o.z + (z + 0.5f) * s.z / dn;
                            if (wx < bx0 || wx > bx1 || wz < bz0 || wz > bz1 || !Cleared(d, new Vector2(wx, wz))) continue;
                            m[z, x] = 0; grassOut++; changed = true;
                        }
                    if (changed) td.SetDetailLayer(0, 0, l, m);
                }

                int n = td.alphamapResolution, L = td.alphamapLayers;
                float[,,] map = td.GetAlphamaps(0, 0, n, n);
                bool painted = false;
                foreach (Stroke st in d.strokes ?? new Stroke[0])
                {
                    int layer = Array.FindIndex(td.terrainLayers, x => x != null && x.name == st.layer);
                    if (layer < 0 || st.p == null || st.p.Length < 4) continue;
                    float half = st.w * 0.5f, soft = Mathf.Max(0.01f, st.soft);
                    float sx0 = float.MaxValue, sz0 = float.MaxValue, sx1 = float.MinValue, sz1 = float.MinValue;
                    for (int i = 0; i + 1 < st.p.Length; i += 2)
                    {
                        sx0 = Mathf.Min(sx0, st.p[i]); sx1 = Mathf.Max(sx1, st.p[i]); sz0 = Mathf.Min(sz0, st.p[i + 1]); sz1 = Mathf.Max(sz1, st.p[i + 1]);
                    }
                    int x0 = Mathf.Max(0, Mathf.FloorToInt((sx0 - half - o.x) / s.x * n)), x1 = Mathf.Min(n - 1, Mathf.CeilToInt((sx1 + half - o.x) / s.x * n));
                    int z0 = Mathf.Max(0, Mathf.FloorToInt((sz0 - half - o.z) / s.z * n)), z1 = Mathf.Min(n - 1, Mathf.CeilToInt((sz1 + half - o.z) / s.z * n));
                    for (int z = z0; z <= z1; z++)
                        for (int x = x0; x <= x1; x++)
                        {
                            var p = new Vector2(o.x + (x + 0.5f) * s.x / n, o.z + (z + 0.5f) * s.z / n);
                            float dist = PolyDist(p, st.p);
                            float k = 1f - Mathf.SmoothStep(0f, 1f, (dist - (half - soft)) / soft);
                            if (k <= map[z, x, layer]) continue;
                            float rest = 1f - map[z, x, layer], keepRest = 1f - k;
                            for (int l = 0; l < L; l++)
                                map[z, x, l] = l == layer ? k : (rest > 1e-5f ? map[z, x, l] / rest * keepRest : 0f);
                            texels++; painted = true;
                        }
                }
                if (painted) td.SetAlphamaps(0, 0, map);
                EditorUtility.SetDirty(td);
            }
            return $"{treesOut} Terrain trees and {grassOut} grass cells cleared, {texels} paint texels (paths, lanes, ruts)";
        }
    }
}
