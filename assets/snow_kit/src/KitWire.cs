// Snow kit, K9: an overhead wire between two points by the kit's rule (SNOW_KIT_CONTRACT.md, «K9: провод между любыми
// точками»). Reference for the Unity agent - not installed by the asset generator. Put it on an empty, set A and B (the
// Wire_ sockets of two kit instances: poles, the roof stand) and the kind; it builds a tube mesh once (and again when
// the ends move in the editor). Parabola: p(t) = A + (B - A) t - up * 4 sag t (1 - t); sag = max(SagMin, SagK * L^2),
// L = horizontal span; segments = max(SegMin, ceil(L / SegLen)).
using UnityEngine;

[ExecuteAlways, RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
public class KitWire : MonoBehaviour
{
    public enum Kind { ServiceDrop, LineBare }

    public Transform A, B;
    public Kind kind = Kind.ServiceDrop;
    public float SagK = 0.0010f, SagMin = 0.05f, SegLen = 1.5f;
    public int SegMin = 6, Sides = 5;
    public float RadiusDrop = 0.007f, RadiusBare = 0.0045f;
    Vector3 _a, _b;

    void OnEnable() { Build(); }

    void Update()
    {
        if (A && B && (A.position != _a || B.position != _b)) Build();
    }

    public static Vector3 Point(Vector3 a, Vector3 b, float sag, float t)
    {
        return Vector3.Lerp(a, b, t) - Vector3.up * (4f * sag * t * (1f - t));
    }

    public static float Sag(Vector3 a, Vector3 b, float k, float min)
    {
        var d = b - a; d.y = 0f;
        float L = d.magnitude;
        return Mathf.Max(min, k * L * L);
    }

    public void Build()
    {
        if (!A || !B) return;
        _a = A.position; _b = B.position;
        Vector3 a = transform.InverseTransformPoint(_a), b = transform.InverseTransformPoint(_b);
        var hd = _b - _a; hd.y = 0f;
        float L = hd.magnitude;
        float sag = Sag(_a, _b, SagK, SagMin);
        int n = Mathf.Max(SegMin, Mathf.CeilToInt(L / SegLen));
        float r = kind == Kind.ServiceDrop ? RadiusDrop : RadiusBare;
        var verts = new Vector3[(n + 1) * Sides];
        var norms = new Vector3[verts.Length];
        var tris = new int[n * Sides * 6];
        Vector3 refUp = Vector3.up;
        for (int i = 0; i <= n; i++)
        {
            float t = i / (float)n;
            Vector3 p = Point(a, b, sag, t);
            Vector3 tan = (Point(a, b, sag, Mathf.Min(1f, t + 0.5f / n)) - Point(a, b, sag, Mathf.Max(0f, t - 0.5f / n))).normalized;
            Vector3 e1 = Vector3.Cross(tan, refUp).normalized;
            if (e1.sqrMagnitude < 1e-6f) e1 = Vector3.Cross(tan, Vector3.right).normalized;
            Vector3 e2 = Vector3.Cross(e1, tan);
            for (int s = 0; s < Sides; s++)
            {
                float ang = s * Mathf.PI * 2f / Sides;
                Vector3 nrm = e1 * Mathf.Cos(ang) + e2 * Mathf.Sin(ang);
                verts[i * Sides + s] = p + nrm * r;
                norms[i * Sides + s] = nrm;
            }
        }
        int k = 0;
        for (int i = 0; i < n; i++)
            for (int s = 0; s < Sides; s++)
            {
                int a0 = i * Sides + s, a1 = i * Sides + (s + 1) % Sides, b0 = a0 + Sides, b1 = a1 + Sides;
                tris[k++] = a0; tris[k++] = b0; tris[k++] = a1;
                tris[k++] = a1; tris[k++] = b0; tris[k++] = b1;
            }
        var mf = GetComponent<MeshFilter>();
        var mesh = mf.sharedMesh;
        if (mesh == null || mesh.name != "KitWire") { mesh = new Mesh { name = "KitWire" }; mf.sharedMesh = mesh; }
        mesh.Clear();
        mesh.vertices = verts; mesh.normals = norms; mesh.triangles = tris;
        mesh.RecalculateBounds();
    }
}
