// Snow: the start post of the Blender concept (source/assets/forest_start_post_v1_1: v1 on the folders of 29.10) into the open
// Forest scene: eval body for tools/snow_qa ue.run_long, like forest_base_apply.cs. Before it: the package's Assets files copied
// and compiled, ForestStartPostStep in the build chain (FOREST_START_POST_UNITY.md, 1-2).
//  0. checks: the package's files in Assets; ForestStartDress.json must be the file the package was made on (else stop);
//  1. ground: WorldGroundImport (base check against the 28.10 21:41 map export, backup, trees only follow, no rock paint,
//     hand sculpt captured): the pad's end and the road's embankment sides softened, 12 cm under the road strip. A rerun
//     after a stop further down sees the ground already in and goes on;
//  2. Start/Prefabs/StartWache.prefab from StartBooth.prefab (ForestStartPostStep.BuildWachePrefab);
//  3. ForestStartDress.json -> the package's copy (old one to snow_archive/backup): the house in the booth's place, the
//     barrier turned and moved before the window, props as in the concept, the pad under snow;
//  4. the players' van olive (QUESTIONS_3 11): VanVehicle's body renderers M_Van_Body -> M_VanOld_Body (prefab backed up);
//  5. ForestStartDressStep, ForestStartPostStep, ForestTreeCollidersStep, ForestWinterStep;
//  6. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_start_post_v1_1/unity/";
const string BaseDressMd5 = "5cc3130d6010d0a87b12d12286febb4e";      // ForestStartDress.json of 29.10 (folders of 29.10), the package's base
var log = new System.Text.StringBuilder();
var forest = UnityEngine.GameObject.Find("Forest");
if (forest == null) return "no Forest root";
var root = forest.transform;
System.Func<string, string> Md5 = p =>
{
    using (var h = System.Security.Cryptography.MD5.Create())
        return System.BitConverter.ToString(h.ComputeHash(System.IO.File.ReadAllBytes(p))).Replace("-", "").ToLowerInvariant();
};
string bak = @"F:/ClaudeGames/snow_archive/backup/forest_start_post_v1_1_" + System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");

// 0. checks
foreach (string f in new[] { "Assets/Snow/Editor/ForestStartPostStep.cs", "Assets/Levels/Forest/Start/Post/ForestStartPost.json",
                             "Assets/Levels/Forest/Start/Post/Forest_StartPost.fbx", "Assets/Levels/Forest/Start/Post/StartWache.fbx",
                             pkg + "ground_delta.json", pkg + "ground_delta.f32", pkg + "base_ground.r16", pkg + "ForestStartDress.json" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: unpack the package and copy its unity/Assets first.";
string dress = "Assets/Levels/Forest/Start/ForestStartDress.json", newDress = pkg + "ForestStartDress.json";
string cur = Md5(dress), mine = Md5(newDress);
if (cur != BaseDressMd5 && cur != mine)
    return $"ForestStartDress.json changed since the package was made ({cur}): nothing done. Carry the package's props, moves, asphaltShare and pebbles (unity/ForestStartDress.json) into it by hand, then run this again.";

if (!System.IO.File.ReadAllText("Assets/Snow/Editor/ForestTerrainStep.cs").Contains("ForestStartPostStep.Run(root)"))
    log.AppendLine("WARNING: ForestTerrainStep does not run ForestStartPostStep yet - the next Forest build would lose the post's model and paint (task, step 2).");

// 1. ground (already in when every tested changed sample is base + delta: a rerun)
const int N = 3073; const float X0 = -600f, Z0 = -1200f, Step = 0.5859375f, HMin = -58.71427536010742f, HMax = 50.406150817871094f;
byte[] dRaw = System.IO.File.ReadAllBytes(pkg + "ground_delta.f32"), bRaw = System.IO.File.ReadAllBytes(pkg + "base_ground.r16");
if (dRaw.Length != N * N * 4 || bRaw.Length != N * N * 2) return "ground_delta.f32 / base_ground.r16: not the 3073 x 3073 grid of the map export";
int tested = 0, applied = 0;
for (int i = 0; i < N * N; i++)
{
    float d = System.BitConverter.ToSingle(dRaw, i * 4);
    if (System.Math.Abs(d) < 0.05f) continue;
    float x = X0 + (i % N) * Step, z = Z0 + (i / N) * Step;
    UnityEngine.Terrain t = null;
    foreach (var tt in UnityEngine.Terrain.activeTerrains)
    {
        var o = tt.transform.position; var s = tt.terrainData.size;
        if (x >= o.x && z >= o.z && x <= o.x + s.x && z <= o.z + s.z) { t = tt; break; }
    }
    if (t == null) continue;
    var to = t.transform.position;
    float now = to.y + t.terrainData.GetHeight(UnityEngine.Mathf.RoundToInt((x - to.x) / Step), UnityEngine.Mathf.RoundToInt((z - to.z) / Step));
    float baseH = HMin + (bRaw[i * 2] | (bRaw[i * 2 + 1] << 8)) / 65535f * (HMax - HMin);
    tested++;
    if (System.Math.Abs(now - (baseH + d)) < 0.05f) applied++;
}
if (tested > 0 && applied > tested * 99 / 100) log.AppendLine($"ground: already in ({applied} of {tested} tested samples are the edit) - not imported again");
else
{
    string imp = Snow.EditorTools.WorldGroundImport.Import(pkg + "ground_delta.json", true, float.MaxValue, 0f);
    log.AppendLine(imp);
    if (imp.Contains("differ from the ground") || imp.Contains("is not the tiles") || imp.Contains("no Terrain")) return log.ToString();
}

// 2. the guard house prefab
log.AppendLine(Snow.EditorTools.ForestStartPostStep.BuildWachePrefab());

// 3. the dress data
if (cur != mine)
{
    System.IO.Directory.CreateDirectory(bak);
    System.IO.File.Copy(dress, bak + "/ForestStartDress.json", true);
    System.IO.File.Copy(newDress, dress, true);
    UnityEditor.AssetDatabase.ImportAsset(dress);
    log.AppendLine("ForestStartDress.json: the package's copy (old one in " + bak + ")");
}

// 4. the van olive
string vanPath = "Assets/Common/Vehicles/Van/Game/VanVehicle.prefab";
var body = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>("Assets/Common/Vehicles/Van/Materials/M_Van_Body.mat");
var olive = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>("Assets/Common/Vehicles/Van/Materials/M_VanOld_Body.mat");
if (body == null || olive == null || !System.IO.File.Exists(vanPath)) log.AppendLine("van: NOT repainted (M_Van_Body, M_VanOld_Body or VanVehicle.prefab missing)");
else
{
    var van = UnityEditor.PrefabUtility.LoadPrefabContents(vanPath);
    int n = 0;
    foreach (var r in van.GetComponentsInChildren<UnityEngine.Renderer>(true))
    {
        var ms = r.sharedMaterials;
        bool ch = false;
        for (int i = 0; i < ms.Length; i++) if (ms[i] == body) { ms[i] = olive; ch = true; n++; }
        if (ch) r.sharedMaterials = ms;
    }
    if (n > 0)
    {
        System.IO.Directory.CreateDirectory(bak);
        System.IO.File.Copy(vanPath, bak + "/VanVehicle.prefab", true);
        UnityEditor.PrefabUtility.SaveAsPrefabAsset(van, vanPath);
    }
    UnityEditor.PrefabUtility.UnloadPrefabContents(van);
    log.AppendLine(n > 0 ? $"van: {n} body slots M_Van_Body -> M_VanOld_Body (old prefab in {bak})" : "van: already olive");
}

// 5. the post
Snow.EditorTools.ForestStartDressStep.Run(root);
log.AppendLine("start dress: run (counts in the console)");
log.AppendLine(Snow.EditorTools.ForestStartPostStep.Run(root));
Snow.EditorTools.ForestTreeCollidersStep.Run(root);
log.AppendLine("tree colliders: run");
Snow.EditorTools.ForestWinterStep.Run(root);
log.AppendLine("winter: run");

// 6. save
UnityEditor.AssetDatabase.SaveAssets();
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
log.AppendLine("scene saved: " + UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene));
return log.ToString();
