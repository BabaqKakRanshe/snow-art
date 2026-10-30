// Snow: the NW river gorge (source/assets/forest_gorge_v1) into the open Forest scene: eval body for tools/snow_qa
// ue.run_long, like river_nw_unity.cs. Before it: the package's Assets files copied and compiled (FOREST_GORGE_UNITY.md, 1-2).
//  0. ForestStreams.json must be the file the package was made on (else stop: merge the NW_gorge entries by hand);
//  1. ground: WorldGroundImport (base check against the 28.10 20:03 map export, backup, trees follow, new ground gets forest,
//     hand sculpt captured) - this also takes the 28.10 Bridge30 gorge's ground back to the old one outside the new gorge;
//  2. ForestStreams.json -> the package's copy (NW_gorge creek along the whole river, the package water cut), streams rebuilt;
//  3. ForestGorgeStep: rock model + colliders, trees / grass / paint on the gorge mask, ledge spruces;
//  4. ForestWinterStep: the snow cover's rendering layer on the new rocks;
//  5. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_gorge_v1/unity/";
const string BaseStreamsMd5 = "3282727b171c5b835885cdb248082634";      // ForestStreams.json of 28.10 19:50 (the 28.10 Bridge30 gorge)
string newStreams = pkg + "Assets/Snow/Levels/Forest/ForestStreams.json";
var log = new System.Text.StringBuilder();
var forest = UnityEngine.GameObject.Find("Forest");
if (forest == null) return "no Forest root";
var root = forest.transform;
System.Func<string, string> Md5 = p =>
{
    using (var h = System.Security.Cryptography.MD5.Create())
        return System.BitConverter.ToString(h.ComputeHash(System.IO.File.ReadAllBytes(p))).Replace("-", "").ToLowerInvariant();
};

// 0. checks
string streams = "Assets/Snow/Levels/Forest/ForestStreams.json";
foreach (string f in new[] { "Assets/Snow/Editor/ForestGorgeStep.cs", "Assets/Snow/Levels/Forest/Gorge/ForestGorge.json", "Assets/Snow/Levels/Forest/Gorge/Forest_Gorge.fbx", "Assets/Snow/Levels/Forest/Gorge/gorge_mask.bytes" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: copy the package's unity/Assets first.";
string cur = Md5(streams), mine = Md5(newStreams);
if (cur != BaseStreamsMd5 && cur != mine)
    return $"ForestStreams.json changed since the package was made ({cur}): nothing done. Put the package's NW_gorge creek and cut (unity/streams_nw_gorge.json) into it by hand, then run this again.";

// 1. ground
string imp = Snow.EditorTools.WorldGroundImport.Import(pkg + "ground_delta.json", true, 1f, 0f);
log.AppendLine(imp);
if (imp.Contains("differ from the ground") || imp.Contains("is not the tiles") || imp.Contains("no Terrain")) return log.ToString();

// 2. streams
if (cur != mine)
{
    string bak = @"F:/ClaudeGames/snow_archive/backup/forest_gorge_v1_" + System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
    System.IO.Directory.CreateDirectory(bak);
    System.IO.File.Copy(streams, bak + "/ForestStreams.json", true);
    System.IO.File.Copy(newStreams, streams, true);
    UnityEditor.AssetDatabase.ImportAsset(streams);
    log.AppendLine("ForestStreams.json: the package's copy (old one in " + bak + ")");
}
Snow.EditorTools.ForestStreamsStep.Run(root);
log.AppendLine("streams: run (counts in the console)");

// 3. the gorge
log.AppendLine(Snow.EditorTools.ForestGorgeStep.Run(root));

// 4. winter
Snow.EditorTools.ForestWinterStep.Run(root);
log.AppendLine("winter: run");

// 5. save
UnityEditor.AssetDatabase.SaveAssets();
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
log.AppendLine("scene saved: " + UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene));
return log.ToString();
