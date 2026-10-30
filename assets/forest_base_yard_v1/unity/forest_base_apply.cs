// Snow: the base yard of the Blender concept (source/assets/forest_base_yard_v1) into the open Forest scene: eval body for
// tools/snow_qa ue.run_long, like forest_gorge_apply.cs. Before it: the package's Assets files copied and compiled
// (FOREST_BASE_YARD_UNITY.md, 1-3).
//  1. the new asphalt: T_GR_Asphalt_A.png / _M.png of the package over the project's (old ones to snow_archive/backup);
//     TL_Asphalt keeps its link (same files, same .meta), only the base yard is paved with it;
//  2. ForestBaseYardStep: the package model, project model copies, props, light, smoke, Terrain clearing and paint;
//  3. ForestTreeColliders and ForestWinter: tree colliders after the clearing, the snow cover's layer on the new renderers;
//  4. scene and assets saved.
if (UnityEditor.EditorApplication.isPlaying) return "Play is running - not touching the scene.";
string pkg = @"F:/ClaudeGames/snow/source/assets/forest_base_yard_v1/unity/";
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
foreach (string f in new[] { "Assets/Snow/Editor/ForestBaseYardStep.cs", "Assets/Snow/Levels/Forest/BaseYard/BaseYard.json", "Assets/Snow/Levels/Forest/BaseYard/Forest_BaseYard.fbx" })
    if (!System.IO.File.Exists(f)) return $"{f} missing: copy the package's unity/Assets first.";

// 1. asphalt
string ground = "Assets/Locations/Forest/Terrain/Ground/";
string bak = @"F:/ClaudeGames/snow_archive/backup/forest_base_yard_v1_" + System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
int swapped = 0;
foreach (string n in new[] { "T_GR_Asphalt_A.png", "T_GR_Asphalt_M.png" })
{
    string src = pkg + "asphalt/" + n, dst = ground + n;
    if (!System.IO.File.Exists(src)) return $"{src} missing";
    if (System.IO.File.Exists(dst) && Md5(dst) == Md5(src)) continue;
    System.IO.Directory.CreateDirectory(bak);
    if (System.IO.File.Exists(dst)) System.IO.File.Copy(dst, bak + "/" + n, true);
    System.IO.File.Copy(src, dst, true);
    UnityEditor.AssetDatabase.ImportAsset(dst, UnityEditor.ImportAssetOptions.ForceUpdate);
    swapped++;
}
log.AppendLine(swapped > 0 ? $"asphalt: {swapped} textures replaced (old ones in {bak})" : "asphalt: already the package's");

// 2. the yard
log.AppendLine(Snow.EditorTools.ForestBaseYardStep.Run(root));

// 3. tree colliders, winter
Snow.EditorTools.ForestTreeCollidersStep.Run(root);
log.AppendLine("tree colliders: run");
Snow.EditorTools.ForestWinterStep.Run(root);
log.AppendLine("winter: run");

// 4. save
UnityEditor.AssetDatabase.SaveAssets();
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
log.AppendLine("scene saved: " + UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene));
return log.ToString();
