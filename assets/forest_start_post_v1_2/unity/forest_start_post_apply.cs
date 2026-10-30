// Snow: the start post's guard house 1.2 (source/assets/forest_start_post_v1_2, on top of v1_1) into the open Forest scene:
// eval body for tools/snow_qa ue.run_long. Before it: the package's Assets files copied and compiled (FOREST_START_POST_UNITY.md, 1).
//  0. checks: the package's files in Assets, ForestStartPostStep of 1.2 compiled, ForestStartPost.json the package's;
//  1. Start/Prefabs/StartWache.prefab again from StartBooth.prefab (ForestStartPostStep.BuildWachePrefab): the house of the style
//     library on the root (the booth's body and boxes off: no house in the house), the booth's door, lamp and plate moved in,
//     its slots on the house's desk, shelf and floor;
//  2. ForestStartDressStep (the house placed again) + WorldSync for its group;
//  3. ForestItemPointsStep (the jerrycan's point under the new Slot_Booth_Jerrycan) + WorldSync for the points; the funnel's
//     point onto the house's shelf (Slot_Shelf): saving the scene keeps it as its hand move (ForestMoves.json);
//  4. ForestWinterStep (the snow decal on the new renderers);
//  5. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_start_post_v1_2/unity/";
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
foreach (string f in new[] { "Assets/Snow/Editor/ForestStartPostStep.cs", "Assets/Levels/Forest/Start/Post/ForestStartPost.json",
                             "Assets/Levels/Forest/Start/Post/StartWache.fbx", "Assets/Levels/Forest/Start/Post/T_Start_Wache_BaseColor.png",
                             "Assets/Levels/Forest/Start/Prefabs/StartBooth.prefab", pkg + "Assets/Levels/Forest/Start/Post/ForestStartPost.json" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: unpack the package and copy its unity/Assets first.";
var ver = typeof(Snow.EditorTools.ForestStartPostStep).GetField("WacheVersion");
if (ver == null || (string)ver.GetValue(null) != "1.2")
    return "ForestStartPostStep is not the package's 1.2 yet (copy unity/Assets/Snow/Editor/ForestStartPostStep.cs and let it compile): nothing done.";
string json = "Assets/Levels/Forest/Start/Post/ForestStartPost.json";
if (Md5(json) != Md5(pkg + "Assets/Levels/Forest/Start/Post/ForestStartPost.json"))
    return "Assets/Levels/Forest/Start/Post/ForestStartPost.json is not the package's (copy unity/Assets of the package): nothing done.";
if (!System.IO.File.ReadAllText("Assets/Snow/Editor/ForestTerrainStep.cs").Contains("ForestStartPostStep.Run(root)"))
    log.AppendLine("WARNING: ForestTerrainStep does not run ForestStartPostStep - the next Forest build would lose the post's model (v1_1 task, step 2).");

// 1. the guard house prefab
string built = Snow.EditorTools.ForestStartPostStep.BuildWachePrefab();
log.AppendLine(built);
if (built.Contains("MISSING") || built.Contains("not found") || built.Contains("could not")) log.AppendLine("WARNING: see MISSING above.");

// 2. the post's things (the house placed again)
Snow.EditorTools.ForestStartDressStep.Run(root);
Snow.EditorTools.WorldSync.FinishGroup(root, Snow.EditorTools.ForestStartDressStep.RootName);
log.AppendLine("start dress: run (counts in the console)");
UnityEngine.Transform dress = root.Find(Snow.EditorTools.ForestStartDressStep.RootName);
UnityEngine.Transform house = null;
if (dress != null)
    foreach (UnityEngine.Transform t in dress)
        if (t.name.StartsWith("StartWache")) { house = t; break; }
if (house == null) log.AppendLine("WARNING: no StartWache under " + Snow.EditorTools.ForestStartDressStep.RootName);
else
{
    int boxes = house.GetComponents<UnityEngine.BoxCollider>().Length;
    bool body = house.GetComponent<UnityEngine.MeshFilter>() != null && house.GetComponent<UnityEngine.MeshFilter>().sharedMesh != null &&
                house.GetComponent<UnityEngine.MeshFilter>().sharedMesh.name == "StartWache";
    log.AppendLine($"house at {house.position}: body {(body ? "StartWache" : "NOT the house's mesh")}, {boxes} boxes on the root");
}

// 3. item points: the jerrycan under the house's slot, the funnel onto the house's shelf
Snow.EditorTools.ForestItemPointsStep.Run(root);
Snow.EditorTools.WorldSync.FinishGroup(root, Snow.EditorTools.ForestItemPointsStep.RootName);
UnityEngine.Transform can = null, funnel = null, shelf = null;
foreach (var t in root.GetComponentsInChildren<UnityEngine.Transform>(true))
{
    if (t.name == "SpawnPoint_Jerrycan_Hut") can = t;
    else if (t.name == "SpawnPoint_Funnel_Hut") funnel = t;
}
if (house != null)
    foreach (var t in house.GetComponentsInChildren<UnityEngine.Transform>(true))
        if (t.name == "Slot_Shelf") { shelf = t; break; }
log.AppendLine(can != null ? $"jerrycan point under {(can.parent != null ? can.parent.name : "-")}" : "WARNING: no SpawnPoint_Jerrycan_Hut");
if (funnel != null && shelf != null)
{
    funnel.position = shelf.position;
    UnityEditor.EditorUtility.SetDirty(funnel);
    log.AppendLine($"funnel point on the house's shelf at {shelf.position} (kept as its hand move when the scene is saved)");
}
else log.AppendLine("WARNING: funnel point or the house's Slot_Shelf not found: the funnel stays where it was");

// 4. snow on the new renderers
Snow.EditorTools.ForestWinterStep.Run(root);
log.AppendLine("winter: run");

// 5. save
UnityEditor.AssetDatabase.SaveAssets();
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
log.AppendLine("scene saved: " + UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene));
return log.ToString();
