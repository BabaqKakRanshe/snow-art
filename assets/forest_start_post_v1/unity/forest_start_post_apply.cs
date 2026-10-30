// Snow: the start post of the Blender concept (source/assets/forest_start_post_v1) into the open Forest scene: eval body for
// tools/snow_qa ue.run_long, like forest_base_apply.cs. Before it: the package's Assets files copied and compiled
// (FOREST_START_POST_UNITY.md, 1-2).
//  0. checks: the package's files in Assets; ForestStartDress.json must be the file the package was made on (else stop);
//  1. ground: WorldGroundImport (base check against the 28.10 21:41 map export, backup, trees only follow, no rock paint,
//     hand sculpt captured): the pad's end and the road's embankment sides softened, 12 cm under the road strip;
//  2. StartWache.prefab from StartBooth.prefab (ForestStartPostStep.BuildWachePrefab);
//  3. ForestStartDress.json -> the package's copy (old one to snow_archive/backup): the house in the booth's place, the
//     barrier turned and moved before the window, props as in the concept, the pad under snow;
//  4. the players' van olive (QUESTIONS_3 11): VanVehicle's body renderers M_Van_Body -> M_VanOld_Body (prefab backed up);
//  5. ForestStartDressStep, ForestStartPostStep, ForestTreeCollidersStep, ForestWinterStep;
//  6. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_start_post_v1/unity/";
const string BaseDressMd5 = "b808b7e6990fa7b4eaea861cf1809290";      // ForestStartDress.json of 28.10 (10:04 UTC), the package's base
var log = new System.Text.StringBuilder();
var forest = UnityEngine.GameObject.Find("Forest");
if (forest == null) return "no Forest root";
var root = forest.transform;
System.Func<string, string> Md5 = p =>
{
    using (var h = System.Security.Cryptography.MD5.Create())
        return System.BitConverter.ToString(h.ComputeHash(System.IO.File.ReadAllBytes(p))).Replace("-", "").ToLowerInvariant();
};
string bak = @"F:/ClaudeGames/snow_archive/backup/forest_start_post_v1_" + System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");

// 0. checks
foreach (string f in new[] { "Assets/Snow/Editor/ForestStartPostStep.cs", "Assets/Snow/Levels/Forest/StartPost/ForestStartPost.json",
                             "Assets/Snow/Levels/Forest/StartPost/Forest_StartPost.fbx", "Assets/Snow/Levels/Forest/StartPost/StartWache.fbx" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: copy the package's unity/Assets first.";
string dress = "Assets/Snow/Levels/Forest/ForestStartDress.json", newDress = pkg + "ForestStartDress.json";
string cur = Md5(dress), mine = Md5(newDress);
if (cur != BaseDressMd5 && cur != mine)
    return $"ForestStartDress.json changed since the package was made ({cur}): nothing done. Carry the package's props, moves, asphaltShare and pebbles (unity/ForestStartDress.json) into it by hand, then run this again.";

// 1. ground
string imp = Snow.EditorTools.WorldGroundImport.Import(pkg + "ground_delta.json", true, float.MaxValue, 0f);
log.AppendLine(imp);
if (imp.Contains("differ from the ground") || imp.Contains("is not the tiles") || imp.Contains("no Terrain")) return log.ToString();

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
string vanPath = "Assets/Snow/Van/VanVehicle.prefab";
var body = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>("Assets/Van/Materials/M_Van_Body.mat");
var olive = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>("Assets/Van/Materials/M_VanOld_Body.mat");
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
