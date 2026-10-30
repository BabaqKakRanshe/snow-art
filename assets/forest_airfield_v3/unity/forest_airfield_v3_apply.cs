// Snow: the airfield of the Blender concept (source/assets/forest_airfield_v3) into the open Forest scene: eval body for
// tools/snow_qa ue.run_long, like forest_start_post_apply.cs. Before it: the package's Assets files copied and compiled,
// ForestAirfieldWinterStep in the build chain (FOREST_AIRFIELD_V3_UNITY.md, 1-3).
//  0. checks: the package's files in Assets; ForestAirfield.json must be the file the package was made on (else stop);
//  1. ground: WorldGroundImport (base check against the 28.10 21:41 map export, backup, trees only follow, no rock paint,
//     hand sculpt captured): the corridor graded (flat 38 m either side of the axis, a swale, cuts 1:4, fills 1:3), the
//     turning pad, the apron at the hangar's floor, the hill over the hall; the ground under the road D1 kept. A rerun after
//     a stop further down sees the ground already in and goes on;
//  2. AF_FuelDrum, AF_FuelDrum_Lying, AF_Generator prefabs (ForestAirfieldWinterStep.BuildProps);
//  3. ForestAirfield.json -> the package's copy (old one to snow_archive/backup);
//  4. the steps whose things stand on the changed ground: ForestNetworkStep (the L2 pole and the fork stone past the north
//     end), ForestAirfieldStep, ForestAirfieldWinterStep, ForestTreeCollidersStep, ForestWinterStep, ForestCctvStep (K20
//     by the south hut), ForestMergeStep (the network's decor merged again);
//  5. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_airfield_v3/unity/";
const string BaseJsonMd5 = "01941e1864aec37d1099ca70c4c2da4c";      // ForestAirfield.json of 29.10 (layout 27.10), the package's base
var log = new System.Text.StringBuilder();
var forest = UnityEngine.GameObject.Find("Forest");
if (forest == null) return "no Forest root";
var root = forest.transform;
System.Func<string, string> Md5 = p =>
{
    using (var h = System.Security.Cryptography.MD5.Create())
        return System.BitConverter.ToString(h.ComputeHash(System.IO.File.ReadAllBytes(p))).Replace("-", "").ToLowerInvariant();
};
string bak = @"F:/ClaudeGames/snow_archive/backup/forest_airfield_v3_" + System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");

// 0. checks
foreach (string f in new[] { "Assets/Snow/Editor/ForestAirfieldWinterStep.cs", "Assets/Levels/Forest/Airfield/Winter/ForestAirfieldWinter.json",
                             "Assets/Levels/Forest/Airfield/Winter/Forest_AirfieldSnow.fbx", "Assets/Levels/Forest/Airfield/Winter/AF_FuelDrum.fbx",
                             "Assets/Levels/Forest/Airfield/Winter/T_AF_Runway_Winter.png", "Assets/Levels/Forest/Airfield/Winter/AF_Trees.bytes",
                             "Assets/Levels/Forest/Airfield/Winter/AF_Paint.bytes", pkg + "ground_delta.json", pkg + "ground_delta.f32",
                             pkg + "base_ground.r16", pkg + "ForestAirfield.json" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: unpack the package and copy its unity/Assets first.";
string json = "Assets/Levels/Forest/Airfield/ForestAirfield.json", newJson = pkg + "ForestAirfield.json";
string cur = Md5(json), mine = Md5(newJson);
if (cur != BaseJsonMd5 && cur != mine)
    return $"ForestAirfield.json changed since the package was made ({cur}): nothing done. Carry the package's items (unity/ForestAirfield.json: " +
           "Fuel_Depot out, slabs at v +-335, the south hut's and the apron's props, windsock / flood mast / cabinet moved) into it by hand, then run this again.";
if (!System.IO.File.ReadAllText("Assets/Snow/Editor/ForestTerrainStep.cs").Contains("ForestAirfieldWinterStep.Run(root)"))
    log.AppendLine("WARNING: ForestTerrainStep does not run ForestAirfieldWinterStep yet - the next Forest build would lose the winter airfield (task, step 2).");

// 1. ground (already in when every tested changed sample is base + delta: a rerun)
const int N = 3073; const float X0 = -600f, Z0 = -1200f, Step = 0.5859375f, HMin = -58.71427536010742f, HMax = 50.406150817871094f;
byte[] dRaw = System.IO.File.ReadAllBytes(pkg + "ground_delta.f32"), bRaw = System.IO.File.ReadAllBytes(pkg + "base_ground.r16");
if (dRaw.Length != N * N * 4 || bRaw.Length != N * N * 2) return "ground_delta.f32 / base_ground.r16: not the 3073 x 3073 grid of the map export";
int tested = 0, applied = 0;
for (int i = 0; i < N * N; i += 211)
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

// 2. the props
log.AppendLine(Snow.EditorTools.ForestAirfieldWinterStep.BuildProps());

// 3. the airfield's data
if (cur != mine)
{
    System.IO.Directory.CreateDirectory(bak);
    System.IO.File.Copy(json, bak + "/ForestAirfield.json", true);
    System.IO.File.Copy(newJson, json, true);
    UnityEditor.AssetDatabase.ImportAsset(json);
    log.AppendLine("ForestAirfield.json: the package's copy (old one in " + bak + ")");
}
else log.AppendLine("ForestAirfield.json: the package's copy already in");

// 4. what stands on the changed ground
Snow.EditorTools.ForestNetworkStep.Run(root);
log.AppendLine("network: run (counts in the console)");
Snow.EditorTools.ForestAirfieldStep.Run(root);
log.AppendLine("airfield: run (counts in the console)");
log.AppendLine(Snow.EditorTools.ForestAirfieldWinterStep.Run(root));
Snow.EditorTools.ForestTreeCollidersStep.Run(root);
log.AppendLine("tree colliders: run");
Snow.EditorTools.ForestWinterStep.Run(root);
log.AppendLine("winter: run");
Snow.EditorTools.ForestCctvStep.Run(root);
Snow.EditorTools.WorldSync.FinishGroup(root, Snow.EditorTools.ForestCctvStep.RootName);
log.AppendLine("cctv cameras: placed again");
Snow.EditorTools.ForestMergeStep.Run(root);
log.AppendLine("merge: run");

// 5. save
UnityEditor.AssetDatabase.SaveAssets();
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
log.AppendLine("scene saved: " + UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene));
return log.ToString();
