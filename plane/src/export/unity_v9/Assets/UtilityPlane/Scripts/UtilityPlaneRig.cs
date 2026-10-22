using System.Collections.Generic;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

namespace UtilityPlane
{
    /// <summary>
    /// Presentation layer of the Utility Plane (v9). Reads state that your gameplay / physics code writes into the
    /// public fields and moves every part, needle, lamp and light of the model. It never computes physics.
    ///
    /// Axis rules (all parts rest with identity rotation, except ailerons/flaps which carry the 2 deg dihedral and the
    /// three PropBlade_N which carry their position around the hub):
    ///   rotations are applied as  restRotation * Euler(...)  in the part's local space.
    ///   Needles, dials and knobs turn clockwise as the pilot sees them when the local Z angle is NEGATIVE.
    /// v7: no MaterialPropertyBlock any more (it keeps renderers out of the SRP Batcher). The rig makes its own
    /// material instances on Awake (lamps, lenses, displays, the gauge backlight, glass fog, prop discs) and destroys
    /// them on OnDestroy. See UNITY_CONTRACT.md for the full table.
    /// v9: four folding troop seats in the cargo bay (paxSeatDown), ladder straps (ladderStowed), prints on the
    /// fogged glass (StampFogPrint / StampFogStroke / ClearFogPrints: wiped spots that fog up again, latent prints
    /// that show only through condensation). Every peer applies the same stamps: replicate them as events.
    /// </summary>
    [DisallowMultipleComponent]
    public class UtilityPlaneRig : MonoBehaviour
    {
        // ---------------------------------------------------------------- exterior
        [Header("Flight surfaces: actual actuator positions, degrees")]
        [Tooltip("+ = trailing edge up (nose-up command)")] public float elevatorDeg;
        [Tooltip("+ = right roll: right aileron TE up, left TE down")] public float aileronDeg;
        [Tooltip("+ = trailing edge right (right pedal)")] public float rudderDeg;
        [Tooltip("0..35, trailing edge down")] public float flapDeg;

        [Header("Engine / wheels / gear")]
        public float propRpm;
        [Range(0, 1), Tooltip("Blade pitch: 0 = fine (as modelled), 1 = feathered (+62 deg about each blade's span)")]
        public float propFeather = 1f;
        [Tooltip("Feather follows propRpm: fine pitch from blurStartRpm (250) up, feathered below 120 rpm (start / shutdown, " +
                 "0.5 per second). Off = drive propFeather yourself.")]
        public bool autoFeather = true;
        [Tooltip("Above this rpm the solid blades hide and the smeared-blade disc (PropBlur) takes over")]
        public float bladesHideRpm = 450f;
        [Tooltip("PropBlur fades in from this rpm (blades still visible below bladesHideRpm)")]
        public float blurStartRpm = 250f;
        [Tooltip("From this rpm the even disc (PropDisc) replaces PropBlur, fully at discFullRpm")]
        public float discStartRpm = 800f, discFullRpm = 1200f;
        [Tooltip("Blur disc turns at min(rpm, this) to stay below the stroboscopic range at 60 fps")]
        public float blurVisualRpmMax = 400f;
        [Tooltip("Main wheel rolling speed, m/s (+ = forward)")] public float mainWheelSpeed;
        [Tooltip("Tail wheel rolling speed, m/s")] public float tailWheelSpeed;
        [Range(0, 1), Tooltip("Strut compression as a fraction of the travel below (0 = fully extended)")]
        public float gearCompressionL, gearCompressionR, tailGearCompression;
        [Tooltip("m of wheel-centre lift (model vertical) that compression 1 stands for: set to your suspension travel. " +
                 "The legs swing on their pivots so that the drawn wheel rises exactly this much.")]
        public float mainGearTravel = 0.12f, tailGearTravel = 0.06f;
        [Tooltip("Tail wheel fork angle, + = wheel front to the right")] public float tailWheelSteerDeg;

        [Header("Doors and caps, 0 = closed, 1 = open")]
        [Range(0, 1)] public float pilotDoorL, pilotDoorR, cargoDoorL, cargoDoorR, fuelCapL, fuelCapR;

        // ---------------------------------------------------------------- cockpit controls
        [Header("Cockpit controls")]
        [Range(-1, 1), Tooltip("+ = yoke pushed forward")] public float yokePitch;
        [Range(-1, 1), Tooltip("+ = yoke turned right")] public float yokeRoll;
        [Range(-1, 1), Tooltip("+ = right pedal forward")] public float pedals;
        [Range(-1, 1), Tooltip("-1 aft .. +1 forward")] public float powerLever, propLever, conditionLever;
        [Range(0, 3), Tooltip("detents 0/10/20/35 deg")] public int flapLever;
        [Tooltip("Trim wheel angle, + = nose-up trim")] public float trimWheelDeg;
        [Range(0, 1)] public float visorP, visorC;
        public bool beltP, beltC;
        public bool annunciatorTestPressed;

        [Tooltip("Toggle switches by object name, e.g. SW_Battery, SW_CabinDoor_L. Starter is momentary: keep it true while held.")]
        public List<string> switchesOn = new List<string>();
        [Tooltip("Pull knobs 0..1 (1 = pulled): Pull_CabinHeat, Pull_Defrost, Pull_ParkBrake, Pull_FuelShutoff")]
        public float pullCabinHeat, pullDefrost, pullParkBrake, pullFuelShutoff;
        [Range(0, 1), Tooltip("Rheostats 0..1")] public float panelLight, floodLight;
        [Tooltip("Fuel tank selectors: true = ON (handle down)")] public bool fuelSelL = true, fuelSelR = true;
        [Range(0, 1), Tooltip("Map case lid (Glovebox_Lid): 0 = closed, 1 = open (folds down towards the pilot, 80 deg)")]
        public float mapCase;
        [Range(0, 1), Tooltip("Starter flip guard (Guard_Starter): 0 = closed, 1 = open (95 deg up)")]
        public float starterGuard;
        [Tooltip("The guard follows SW_Starter in switchesOn (opens while the starter is held). Off = drive starterGuard yourself.")]
        public bool autoStarterGuard = true;

        [Header("v7 knobs (degrees, clockwise as the pilot sees them)")]
        [Tooltip("Radio knob angles, index = RadioKnobNames (13 knobs). Your avionics code turns them with the frequency.")]
        public float[] radioKnobDeg = new float[13];
        [Range(0, 4), Tooltip("Transponder mode knob detent: 0 OFF, 1 SBY, 2 ON, 3 ALT, 4 TST")]
        public int xpdrMode;
        [Tooltip("Knob_ALT_Baro, Knob_HDG_Bug, Knob_DG_Set angles (used when autoKnobs is off; Knob_DG_Set always)")]
        public float baroKnobDeg, hdgBugKnobDeg, dgSetKnobDeg;
        [Tooltip("Knob_ALT_Baro turns one revolution per inHg of setting, Knob_HDG_Bug follows the bug 1:1")]
        public bool autoKnobs = true;

        // ---------------------------------------------------------------- instruments (sensor outputs, not truth)
        [Header("Instrument readings (from your sensor models)")]
        public float iasKt, altitudeFt, vsiFpm, pitchDeg, bankDeg, headingDeg, turnRateDegS;
        [Range(-1, 1), Tooltip("slip ball, + = ball right")] public float slip;
        public float torqueFtLb, propRpmGauge, ittC, ngPct, oilPsi, oilC, fuelFlowPph, fuelLGal, fuelRGal, amps, oatC;
        [Tooltip("Voltmeter, volts DC (0..35)")] public float busVolts;
        [Tooltip("Suction gauge, inHg (0..10)")] public float suctionInHg;
        public float clockHours, clockMinutes;
        [Tooltip("v7: altimeter setting shown in the Kollsman window, inHg (28.6..31.0). altitudeFt is already the indicated altitude.")]
        public float altimeterSettingInHg = 29.92f;
        [Tooltip("v7: heading the bug marks on the DG card, degrees")] public float headingBugDeg;
        [Tooltip("v7: magnetic compass card reading, degrees (add your own lag / turning errors)")]
        public float compassHeadingDeg;

        [Header("Needle dynamics")]
        public float needleOmega = 11f;
        public float needleDamping = 0.6f;

        // ---------------------------------------------------------------- glass fog (v7, SYS-01)
        [Header("Glass fog 0..1 (your demist / cabin heat model)")]
        [Range(0, 1), Tooltip("Windshield (both halves); the defroster clears it from the bottom up")]
        public float windshieldFog;
        [Range(0, 1), Tooltip("All other panes incl. the door windows; cabin heat clears them from the bottom up")]
        public float sideWindowFog;
        public Color fogColor = new Color(0.86f, 0.88f, 0.90f, 1f);
        [Range(0, 1)] public float fogMaxAlpha = 0.85f;

        [Header("v9 prints on the fogged glass")]
        [Tooltip("s: a wiped spot fogs up again over this time (only visible while the pane is fogged)")]
        public float printRegrowSeconds = 25f;
        [Range(0, 1), Tooltip("How strongly a latent print (touch without wiping) thins the condensation")]
        public float latentPrintVisibility = 0.6f;
        [Tooltip("Brushes (R channel, readable). Tools/Utility Plane/Build Materials + Prefabs assigns T_FogPrint_*")]
        public Texture2D fogPrintHand, fogPrintFinger;
        [Tooltip("m: StampFogPrint / StampFogStroke look for a fog layer this far from the given point. The cabin colliders " +
                 "(windshield, door panels) lie 5-20 cm in front of the glass: RaycastFog gives the exact point on it.")]
        public float printSearchRadius = 0.25f;

        // ---------------------------------------------------------------- v9 cargo bay
        [Header("v9 cargo bay: folding troop seats, index = PaxSeatNames (L1, R1, L2, R2)")]
        [Tooltip("0 = folded up against the wall (stowed), 1 = down, ready to sit. The model rests in the down pose.")]
        public float[] paxSeatDown = new float[4];
        [Tooltip("Shows the two cargo straps over the step ladder stowed on the bay floor (Stow_LadderStraps)")]
        public bool ladderStowed;

        // ---------------------------------------------------------------- lamps and lights
        [Header("Annunciator (index = Lamp_NN), lit only with bus power")]
        public bool busPowered;
        public bool[] lamps = new bool[12];
        public Color lampGlow = Color.white;
        public float lampIntensity = 3f;

        [Header("Lights (0..1 actual output, already including bus voltage)")]
        [Range(0, 1)] public float navLights, strobeLights, beaconLights, landingLight, cabinLight, cargoLight;
        [Range(0, 1), Tooltip("Avionics bus output 0..1: backlit legends of the radio faces (Display_Radio) and the idle glow " +
                              "of the display quads Display_COM1/NAV1/GPS/XPDR/AP/ADF (their content is drawn by your code).")]
        public float avionicsPower;
        public float radioDisplayIntensity = 1.2f;
        [Tooltip("Your code draws into the display quads (own materials / emission): the rig then leaves them alone.")]
        public bool screensDrivenExternally;
        public Color screenIdleGlow = new Color(0.05f, 0.12f, 0.10f);
        public float screenIdleIntensity = 0.6f;
        [Tooltip("Create missing Light_* objects at the light sockets on Awake. Tools/Utility Plane/Build Materials + Prefabs puts them into " +
                 "the prefab already; their Light.intensity there is the 100 % level (tune it in the prefab).")]
        public bool createLights = true;
        [Tooltip("HDRP only: emission of lamps and lenses is multiplied by this (nits per unit). TEMPORARY, tune to exposure.")]
        public float hdrpEmissionScale = 400f;

        // ---------------------------------------------------------------- internals
        class Part
        {
            public Transform t;
            public Quaternion rot;
            public Vector3 pos, scale;
            public float value, vel;     // smoothed value (needles) and its rate
        }

        readonly Dictionary<string, Part> _parts = new Dictionary<string, Part>();
        readonly Dictionary<string, Material> _emitMats = new Dictionary<string, Material>();
        readonly Dictionary<Material, Vector4> _lastEmission = new Dictionary<Material, Vector4>();
        readonly List<Material> _created = new List<Material>();
        readonly Dictionary<string, Light> _lights = new Dictionary<string, Light>();
        readonly List<string> _switchNames = new List<string>();
        Material _gaugesMat, _fogMat, _blurMat, _discMat;
        Renderer _blurR, _discR;
        readonly List<Renderer> _bladeR = new List<Renderer>();
        readonly List<Renderer> _fogR = new List<Renderer>();      // Glass_Fog (windshield + fixed panes), <Door>_Fog
        int _emissionId, _fogId, _fogSideId, _fogColorId, _fogAlphaId, _baseColorId;
        int _printsId, _printTimeId, _printRegrowId, _latentId;
        float _printClock, _lastRegrow = -1f, _lastLatent = -1f;
        Texture2D _prints;
        bool _printsDirty;
        const int PrintRes = 512;
        bool _hdrp, _fogShader;
        float _propAngle, _blurAngle, _discAngle, _wheelAngle, _tailWheelAngle, _strobeT, _beaconT;
        float _lastFogW = -1f, _lastFogS = -1f, _lastFogKey = -1f, _lastBlurA = -1f, _lastDiscA = -1f;
        const float MainR = 0.484f, TailR = 0.2856f;

        /// <summary>Parked on flat ground, all three tyres touching, struts unloaded: the root is pitched nose-up by this
        /// angle (Unity: negative X rotation). The model frame itself stays level (cabin floor horizontal).</summary>
        public const float ParkedPitchDeg = 9.98f;
        /// <summary>Height of the root above flat ground in that pose, m (negative: the origin is under the ground).</summary>
        public const float ParkedRootHeight = -0.372f;
        /// <summary>Blade pitch from fine (as modelled) to feather, degrees about each blade's span.</summary>
        public const float FeatherDeg = 62f;
        /// <summary>Kollsman disc scale: degrees per inHg (29.92 under the index at rest).</summary>
        public const float BaroDegPerInHg = 120f;

        /// <summary>Root pose for parking on flat ground at <paramref name="groundPoint"/> with heading <paramref name="yawDeg"/>.
        /// The struts settle a few centimetres under weight once physics runs.</summary>
        public static Pose ParkedPose(Vector3 groundPoint, float yawDeg)
        {
            return new Pose(groundPoint + Vector3.up * ParkedRootHeight, Quaternion.Euler(-ParkedPitchDeg, yawDeg, 0f));
        }

        // leg pivot -> axle in the leg's swing plane; the wheel lifts r (sin phi0 - sin(phi0 - a)) at swing angle a
        struct Arm { public float r, phi0; public bool ok; }
        Arm _armL, _armR, _armT;

        static readonly string[] LampNames =
        {
            "Lamp_00", "Lamp_01", "Lamp_02", "Lamp_03", "Lamp_04", "Lamp_05",
            "Lamp_06", "Lamp_07", "Lamp_08", "Lamp_09", "Lamp_10", "Lamp_11"
        };

        /// <summary>Annunciator legends, index = Lamp_NN (same order as the printed atlas).</summary>
        public static readonly string[] LampLegends =
        {
            "OIL PRESS", "ENG HOT", "FUEL LOW L", "FUEL LOW R", "GEN OFF", "BATT LOW",
            "STARTER ON", "IGNITION", "DOOR", "CARGO DOOR", "CARGO LOOSE", "SEAT BELT"
        };

        /// <summary>All needle / dial transforms driven by this component.</summary>
        public static readonly string[] NeedleNames =
        {
            "Needle_ASI", "Needle_ALT100", "Needle_ALT1000", "Needle_VSI", "Needle_TRQ", "Needle_PROP", "Needle_ITT",
            "Needle_NG", "Needle_OILP", "Needle_OILT", "Needle_FF", "Needle_FUELL", "Needle_FUELR", "Needle_AMP",
            "Needle_OAT", "Clock_Hour", "Clock_Min", "ATT_Roll", "ATT_Pitch", "HDG_Card", "TC_Plane", "TC_Ball",
            "Needle_VOLT", "Needle_VAC"
        };

        /// <summary>v6 display quads (UV 0..1 over the visible window, facing the pilot). Sizes: Data/displays.json.
        /// Display_Hobbs follows busPowered, the others avionicsPower.</summary>
        public static readonly string[] DisplayNames =
        {
            "Display_COM1", "Display_NAV1", "Display_GPS", "Display_XPDR", "Display_AP", "Display_ADF", "Display_Hobbs"
        };

        /// <summary>v7 radio knobs, index of radioKnobDeg. Knob_XPDR_Mode is driven by xpdrMode.</summary>
        public static readonly string[] RadioKnobNames =
        {
            "Knob_Audio_Vol", "Knob_Com_Outer", "Knob_Com_Inner", "Knob_Nav_Outer", "Knob_Nav_Inner", "Knob_NavCom_Vol",
            "Knob_GPS_Pwr", "Knob_GPS_Outer", "Knob_GPS_Inner", "Knob_AP_Baro", "Knob_ADF_Vol", "Knob_ADF_Outer",
            "Knob_ADF_Inner"
        };

        /// <summary>Transponder mode detents (clockwise from the modelled OFF position, degrees): OFF, SBY, ON, ALT, TST.</summary>
        public static readonly float[] XpdrDetentDeg = { 0f, 34f, 82f, 116f, 150f };

        static readonly string[] BladeNames = { "PropBlade_1", "PropBlade_2", "PropBlade_3" };

        /// <summary>v9 folding seats (pans) in the cargo bay, index of paxSeatDown. Each has a child "&lt;name&gt;_Leg".
        /// L = left wall (pilot side), R = right wall; 1 = ahead of the cargo doors, 2 = behind them.</summary>
        public static readonly string[] PaxSeatNames = { "PaxSeat_L1", "PaxSeat_R1", "PaxSeat_L2", "PaxSeat_R2" };
        static readonly string[] PaxLegNames = { "PaxSeat_L1_Leg", "PaxSeat_R1_Leg", "PaxSeat_L2_Leg", "PaxSeat_R2_Leg" };
        /// <summary>Pan fold angle (deg, about the hinge = local Z); the leg folds by the same angle the other way.</summary>
        public const float PaxSeatFoldDeg = 90f;

        public enum FogBrush { Hand, Finger }

        void Awake()
        {
            var rp = GraphicsSettings.currentRenderPipeline;
            _hdrp = rp != null && rp.GetType().Name.Contains("HDRenderPipeline");
            _emissionId = Shader.PropertyToID(_hdrp ? "_EmissiveColor" : "_EmissionColor");
            _fogId = Shader.PropertyToID("_Fog");
            _fogSideId = Shader.PropertyToID("_FogSide");
            _fogColorId = Shader.PropertyToID("_FogColor");
            _fogAlphaId = Shader.PropertyToID("_MaxAlpha");
            _baseColorId = Shader.PropertyToID(rp == null ? "_Color" : "_BaseColor");
            _printsId = Shader.PropertyToID("_FogPrints");
            _printTimeId = Shader.PropertyToID("_PrintTime");
            _printRegrowId = Shader.PropertyToID("_PrintRegrow");
            _latentId = Shader.PropertyToID("_LatentStrength");
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (!_parts.ContainsKey(t.name))
                    _parts[t.name] = new Part { t = t, rot = t.localRotation, pos = t.localPosition, scale = t.localScale };
                if (t.name.StartsWith("SW_", System.StringComparison.Ordinal) && !_switchNames.Contains(t.name))
                    _switchNames.Add(t.name);
            }
            SetupMaterials();
            _armL = MakeArm("Gear_L", "Wheel_L", true);              // rest pose: nothing has moved the parts yet
            _armR = MakeArm("Gear_R", "Wheel_R", true);
            _armT = MakeArm("TailGear", "TailWheel", false);
            if (createLights) BuildLights(transform, _hdrp);
            foreach (var l in GetComponentsInChildren<Light>(true))
            {
                if (!l.name.StartsWith("Light_", System.StringComparison.Ordinal)) continue;
                string key = l.name.Substring(6);
                _lights[key] = l;
                _maxIntensity[key] = l.intensity;
            }
        }

        // One instance per driven material, shared by every renderer of this plane that uses the original: lamps, lenses
        // and displays get their own instance each (independent states), M_Gauges one for the whole backlight.
        void SetupMaterials()
        {
            Material gaugesShared = null;
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                string n = r.name;
                if (n.StartsWith("Lamp_", System.StringComparison.Ordinal) || n.StartsWith("Lens_", System.StringComparison.Ordinal) ||
                    n.StartsWith("Display_", System.StringComparison.Ordinal))
                {
                    if (r.sharedMaterial == null) continue;
                    var inst = Instance(r.sharedMaterial, n);
                    r.sharedMaterial = inst;
                    _emitMats[n] = inst;
                }
                else if (n == "PropBlur" || n == "PropDisc")
                {
                    if (r.sharedMaterial == null) continue;
                    var inst = Instance(r.sharedMaterial, n);
                    r.sharedMaterial = inst;
                    if (n == "PropBlur") { _blurMat = inst; _blurR = r; } else { _discMat = inst; _discR = r; }
                    r.enabled = false;
                }
                else if (n == "Glass_Fog" || n.EndsWith("_Fog", System.StringComparison.Ordinal))
                {
                    if (r.sharedMaterial == null) continue;
                    if (_fogMat == null) _fogMat = Instance(r.sharedMaterial, "fog");
                    r.sharedMaterial = _fogMat;
                    _fogR.Add(r);
                }
                foreach (var m in r.sharedMaterials)
                    if (m != null && gaugesShared == null && m.name.StartsWith("M_Gauges", System.StringComparison.Ordinal))
                        gaugesShared = m;
            }
            if (gaugesShared != null)
            {
                _gaugesMat = Instance(gaugesShared, "backlight");
                foreach (var r in GetComponentsInChildren<Renderer>(true))
                {
                    var mats = r.sharedMaterials;
                    bool hit = false;
                    for (int i = 0; i < mats.Length; i++)
                        if (mats[i] == gaugesShared) { mats[i] = _gaugesMat; hit = true; }
                    if (hit) r.sharedMaterials = mats;
                }
            }
            foreach (var bn in BladeNames)
                if (_parts.TryGetValue(bn, out var bp) && bp.t.TryGetComponent<Renderer>(out var br)) _bladeR.Add(br);
            _fogShader = _fogMat != null && _fogMat.HasProperty(_fogId);
        }

        Material Instance(Material shared, string tag)
        {
            var m = new Material(shared) { name = shared.name + " (" + tag + ")" };
            _created.Add(m);
            return m;
        }

        void OnDestroy()
        {
            foreach (var m in _created)
                if (m != null) Destroy(m);
            _created.Clear();
            if (_prints != null) Destroy(_prints);
        }

        // ---------------------------------------------------------------- v9 prints on the fogged glass
        class FogMesh
        {
            public Transform t;
            public Vector3[] v;
            public Vector2[] uv;
            public int[] tri;
            // per triangle, object space: surface metres per uv unit, area, centroid, cell of the 4 x 3 atlas (-1: degenerate)
            public Vector3[] ju, jv, cen;
            public float[] area;
            public int[] cell;
        }

        static int CellOf(Vector2 uv)                                     // 0..11: column + 4 * row (rows from the top)
        {
            return Mathf.Clamp(Mathf.FloorToInt(uv.x * 4f), 0, 3) + 4 * Mathf.Clamp(Mathf.FloorToInt((1f - uv.y) * 1024f / 341f), 0, 2);
        }

        static FogMesh BuildFogMesh(Transform t, Mesh m)
        {
            var fm = new FogMesh { t = t, v = m.vertices, uv = m.uv, tri = m.triangles };
            int n = fm.tri.Length / 3;
            fm.ju = new Vector3[n]; fm.jv = new Vector3[n]; fm.cen = new Vector3[n]; fm.area = new float[n]; fm.cell = new int[n];
            for (int i = 0; i < n; i++)
            {
                int i0 = fm.tri[3 * i], i1 = fm.tri[3 * i + 1], i2 = fm.tri[3 * i + 2];
                Vector3 e1 = fm.v[i1] - fm.v[i0], e2 = fm.v[i2] - fm.v[i0];
                Vector2 d1 = fm.uv[i1] - fm.uv[i0], d2 = fm.uv[i2] - fm.uv[i0];
                float det = d1.x * d2.y - d2.x * d1.y;
                fm.cen[i] = (fm.v[i0] + fm.v[i1] + fm.v[i2]) / 3f;
                fm.area[i] = 0.5f * Vector3.Cross(e1, e2).magnitude;
                fm.cell[i] = Mathf.Abs(det) < 1e-12f ? -1 : CellOf((fm.uv[i0] + fm.uv[i1] + fm.uv[i2]) / 3f);
                if (fm.cell[i] < 0) continue;
                fm.ju[i] = (e1 * d2.y - e2 * d1.y) / det;
                fm.jv[i] = (e2 * d1.x - e1 * d2.x) / det;
            }
            return fm;
        }

        List<FogMesh> _fogMeshes;

        /// <summary>
        /// Leaves a print on the inner glass layer nearest to <paramref name="worldPoint"/> (within printSearchRadius, 25 cm,
        /// of a fogged pane: windshield, door and cabin windows; RaycastFog gives the exact point on the glass). wipe = true: the condensation is wiped away there and forms again over
        /// printRegrowSeconds; wipe = false: a latent print that shows only while (or when) the glass is fogged.
        /// The brush is oriented with its top towards world up, turned by angleDeg about the glass normal.
        /// Returns false when no pane is near, the fog layer is not the UtilityPlane/GlassFog shader (HDRP / Built-in
        /// fall back to an even veil without prints) or the fog meshes are not readable.
        /// The prints texture is uploaded once per frame (LateUpdate), however many stamps the frame makes.
        /// </summary>
        public bool StampFogPrint(Vector3 worldPoint, FogBrush brush = FogBrush.Hand, float sizeM = 0.18f, float angleDeg = 0f,
                                  bool wipe = true, float strength = 1f)
        {
            if (!EnsurePrints() || !PrintFrameAt(worldPoint, out PrintFrame f)) return false;
            Vector3 up = Vector3.ProjectOnPlane(Vector3.up, f.n);
            if (up.sqrMagnitude < 1e-6f) up = Vector3.ProjectOnPlane(transform.forward, f.n);
            up = Quaternion.AngleAxis(angleDeg, f.n) * up.normalized;
            Vector3 right = Vector3.Cross(up, f.n).normalized;
            float r = Mathf.Max(0.005f, sizeM * 0.5f), k = Mathf.Clamp01(strength), stamp = _printClock + 1f;
            // texel window: the brush square (any rotation) in UV, clipped to the pane's cell of the 4 x 3 fog atlas
            if (!f.Window(f.uv, f.uv, r * 1.5f, out int x0, out int x1, out int y0, out int y1)) return false;
            Texture2D b = brush == FogBrush.Hand ? fogPrintHand : fogPrintFinger;
            NativeArray<Color> px = _prints.GetPixelData<Color>(0);          // the texture's own CPU copy, no extra array
            bool any = false;
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++)
                {
                    float w = 0f;                                            // 2 x 2 samples per texel: no stair steps
                    for (int s = 0; s < 4; s++)
                    {
                        Vector3 p = f.Offset(x + 0.25f + 0.5f * (s & 1), y + 0.25f + 0.5f * (s >> 1));
                        float bx = Vector3.Dot(p, right) / r, by = Vector3.Dot(p, up) / r;
                        if (bx >= -1f && bx <= 1f && by >= -1f && by <= 1f) w += BrushValue(b, brush, bx, by);
                    }
                    w *= 0.25f * k;
                    if (w < 0.01f) continue;
                    Put(px, y * PrintRes + x, w, wipe, stamp);
                    any = true;
                }
            _printsDirty |= any;
            return any;
        }

        /// <summary>
        /// A finger line from a to b (writing in the fog, a dragged hand): an even stroke widthM wide with a soft edge,
        /// laid in pieces of up to 4 cm that follow the curved glass. Returns the number of pieces that landed.
        /// </summary>
        public int StampFogStroke(Vector3 fromWorld, Vector3 toWorld, float widthM = 0.022f, bool wipe = true, float strength = 1f)
        {
            if (!EnsurePrints()) return 0;
            float r = Mathf.Max(0.003f, widthM * 0.5f), k = Mathf.Clamp01(strength), stamp = _printClock + 1f;
            int pieces = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(fromWorld, toWorld) / 0.04f));
            int hits = 0;
            for (int i = 0; i < pieces; i++)
            {
                Vector3 a = Vector3.Lerp(fromWorld, toWorld, i / (float)pieces);
                Vector3 c = Vector3.Lerp(fromWorld, toWorld, (i + 1) / (float)pieces);
                if (!PrintFrameAt(a, out PrintFrame f)) continue;
                Vector3 ab = Vector3.ProjectOnPlane(c - a, f.n);
                float aa = 0.6f * f.texelM;                                  // soft edge: anti-aliased at any width
                if (!f.Window(f.uv, f.uv + f.ToUv(ab), (r + aa) * 1.5f, out int x0, out int x1, out int y0, out int y1)) continue;
                float ab2 = Mathf.Max(ab.sqrMagnitude, 1e-10f);
                NativeArray<Color> px = _prints.GetPixelData<Color>(0);
                bool any = false;
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                    {
                        Vector3 p = f.Offset(x + 0.5f, y + 0.5f);
                        float t = Mathf.Clamp01(Vector3.Dot(p, ab) / ab2);
                        float w = (1f - Smooth(r * 0.55f - aa, r + aa, (p - ab * t).magnitude)) * k;
                        if (w < 0.01f) continue;
                        Put(px, y * PrintRes + x, w, wipe, stamp);
                        any = true;
                    }
                if (!any) continue;
                hits++;
                _printsDirty = true;
            }
            return hits;
        }

        /// <summary>Removes every wiped spot and latent print (the glass is cleaned).</summary>
        public void ClearFogPrints()
        {
            if (_prints == null) return;
            NativeArray<Color> px = _prints.GetPixelData<Color>(0);
            for (int i = 0; i < px.Length; i++) px[i] = default(Color);
            _printsDirty = true;
        }

        // one texel: a wipe keeps what is still clear from earlier wipes (same regrow curve as the shader) and restarts
        // the clock; a latent print only adds
        void Put(NativeArray<Color> px, int k, float w, bool wipe, float stamp)
        {
            Color c = px[k];
            if (wipe)
            {
                float left = 0f;
                if (c.b > 0f)
                {
                    float g = Mathf.Clamp01((_printClock - (c.r / c.b - 1f)) / Mathf.Max(printRegrowSeconds, 0.01f));
                    left = c.b * (1f - g * g * (3f - 2f * g));
                }
                c.b = Mathf.Max(left, w);
                c.r = stamp * c.b;                                       // premultiplied: wipe time x coverage
            }
            else c.g = Mathf.Max(c.g, w);
            px[k] = c;
        }

        static float Smooth(float e0, float e1, float x)                  // HLSL smoothstep (Mathf.SmoothStep differs)
        {
            float t = Mathf.Clamp01((x - e0) / (e1 - e0));
            return t * t * (3f - 2f * t);
        }

        struct PrintFrame
        {
            public Vector2 uv;                                          // uv of the closest point on the fog layer
            public Vector3 dPdu, dPdv, n;                               // world metres per uv unit, glass normal
            public float texelM;                                        // metres per print texel
            public int cx0, cx1, cy0, cy1;                              // texel rect of the pane's cell (4 x 3 atlas)

            public Vector3 Offset(float tx, float ty)                   // surface offset of texel point (tx, ty) from uv
            {
                return dPdu * (tx / PrintRes - uv.x) + dPdv * (ty / PrintRes - uv.y);
            }

            public Vector2 ToUv(Vector3 d)                              // uv step for a surface vector (least squares)
            {
                float g11 = Vector3.Dot(dPdu, dPdu), g12 = Vector3.Dot(dPdu, dPdv), g22 = Vector3.Dot(dPdv, dPdv);
                float det = g11 * g22 - g12 * g12, b1 = Vector3.Dot(d, dPdu), b2 = Vector3.Dot(d, dPdv);
                if (Mathf.Abs(det) < 1e-12f) return Vector2.zero;
                return new Vector2((g22 * b1 - g12 * b2) / det, (g11 * b2 - g12 * b1) / det);
            }

            public bool Window(Vector2 a, Vector2 b, float marginM, out int x0, out int x1, out int y0, out int y1)
            {
                float du = marginM / Mathf.Max(dPdu.magnitude, 1e-6f), dv = marginM / Mathf.Max(dPdv.magnitude, 1e-6f);
                x0 = Mathf.Max(cx0, Mathf.FloorToInt((Mathf.Min(a.x, b.x) - du) * PrintRes));
                x1 = Mathf.Min(cx1, Mathf.CeilToInt((Mathf.Max(a.x, b.x) + du) * PrintRes));
                y0 = Mathf.Max(cy0, Mathf.FloorToInt((Mathf.Min(a.y, b.y) - dv) * PrintRes));
                y1 = Mathf.Min(cy1, Mathf.CeilToInt((Mathf.Max(a.y, b.y) + dv) * PrintRes));
                return x1 >= x0 && y1 >= y0;
            }
        }

        bool PrintFrameAt(Vector3 worldPoint, out PrintFrame f)
        {
            f = default(PrintFrame);
            if (!ClosestOnFog(worldPoint, out FogMesh fm, out int t, out Vector3 bary)) return false;
            int tri = t / 3, cell = fm.cell[tri];
            if (cell < 0) return false;
            int i0 = fm.tri[t], i1 = fm.tri[t + 1], i2 = fm.tri[t + 2];
            Vector3 q = fm.v[i0] * bary.x + fm.v[i1] * bary.y + fm.v[i2] * bary.z;
            // surface metres per uv unit, area-weighted over the pane within 15 cm (the fog UVs are planar projections,
            // so this is near constant over a pane; averaging keeps one thin triangle from skewing the brush)
            Vector3 ju = Vector3.zero, jv = Vector3.zero;
            float wsum = 0f;
            for (int k = 0; k < fm.cell.Length; k++)
            {
                if (fm.cell[k] != cell || (fm.cen[k] - q).sqrMagnitude > 0.15f * 0.15f) continue;
                ju += fm.ju[k] * fm.area[k];
                jv += fm.jv[k] * fm.area[k];
                wsum += fm.area[k];
            }
            if (wsum > 0f) { ju /= wsum; jv /= wsum; }
            else { ju = fm.ju[tri]; jv = fm.jv[tri]; }
            f.uv = fm.uv[i0] * bary.x + fm.uv[i1] * bary.y + fm.uv[i2] * bary.z;
            f.dPdu = fm.t.TransformVector(ju);
            f.dPdv = fm.t.TransformVector(jv);
            Vector3 nt = Vector3.Cross(fm.t.TransformVector(fm.v[i1] - fm.v[i0]), fm.t.TransformVector(fm.v[i2] - fm.v[i0]));
            f.n = Vector3.Cross(f.dPdu, f.dPdv).normalized;
            if (Vector3.Dot(f.n, nt) < 0f) f.n = -f.n;                        // the winding side, as the brush expects
            if (f.n.sqrMagnitude < 0.5f) return false;
            f.texelM = Mathf.Max(f.dPdu.magnitude, f.dPdv.magnitude) / PrintRes;
            int cellX = cell % 4, cellY = cell / 4;
            f.cx0 = cellX * PrintRes / 4;
            f.cx1 = (cellX + 1) * PrintRes / 4 - 1;
            f.cy1 = PrintRes - 1 - Mathf.FloorToInt(cellY * 341f / 1024f * PrintRes);                    // texel rows: v up
            f.cy0 = Mathf.Max(0, PrintRes - Mathf.CeilToInt((cellY + 1) * 341f / 1024f * PrintRes));
            return true;
        }

        /// <summary>
        /// Where a ray meets an inner fog layer (the nearest hit within maxDistance, either side). Use it for "the print
        /// goes where the player looks / reaches": the cabin's physics colliders stand 5-20 cm in front of the glass.
        /// False when nothing is hit or prints are unavailable (see StampFogPrint).
        /// </summary>
        public bool RaycastFog(Ray ray, float maxDistance, out Vector3 point)
        {
            point = default(Vector3);
            if (!EnsurePrints()) return false;
            float best = maxDistance;
            bool hit = false;
            foreach (var fm in _fogMeshes)
            {
                if (fm.t == null) continue;
                // object space with the full inverse (scale included): the ray parameter stays the world distance
                Vector3 o = fm.t.InverseTransformPoint(ray.origin), d = fm.t.InverseTransformVector(ray.direction);
                for (int i = 0; i < fm.tri.Length; i += 3)
                    if (RayTriangle(o, d, fm.v[fm.tri[i]], fm.v[fm.tri[i + 1]], fm.v[fm.tri[i + 2]], out float tt) && tt < best)
                    {
                        best = tt;
                        hit = true;
                    }
            }
            if (hit) point = ray.origin + ray.direction * best;
            return hit;
        }

        static bool RayTriangle(Vector3 o, Vector3 d, Vector3 a, Vector3 b, Vector3 c, out float t)  // Moller-Trumbore
        {
            t = 0f;
            Vector3 e1 = b - a, e2 = c - a, p = Vector3.Cross(d, e2);
            float det = Vector3.Dot(e1, p);
            if (Mathf.Abs(det) < 1e-12f) return false;
            float inv = 1f / det;
            Vector3 s = o - a;
            float u = Vector3.Dot(s, p) * inv;
            if (u < 0f || u > 1f) return false;
            Vector3 q = Vector3.Cross(s, e1);
            float v = Vector3.Dot(d, q) * inv;
            if (v < 0f || u + v > 1f) return false;
            t = Vector3.Dot(e2, q) * inv;
            return t > 0f;
        }

        void LateUpdate()                                                // one upload per frame for all stamps
        {
            if (!_printsDirty || _prints == null) return;
            _prints.Apply(false, false);
            _printsDirty = false;
        }

        bool EnsurePrints()
        {
            if (_fogMat == null || !_fogShader || !_fogMat.HasProperty(_printsId)) return false;
            if (_fogMeshes == null)
            {
                _fogMeshes = new List<FogMesh>();
                foreach (var r in _fogR)
                {
                    if (r == null || !r.TryGetComponent<MeshFilter>(out var mf) || mf.sharedMesh == null) continue;
                    var m = mf.sharedMesh;
                    if (!m.isReadable)
                    {
                        Debug.LogWarning("[UtilityPlane] fog prints need Read/Write on UtilityPlane.fbx (" + m.name + ")");
                        continue;
                    }
                    _fogMeshes.Add(BuildFogMesh(r.transform, m));
                }
            }
            if (_fogMeshes.Count == 0) return false;
            if (_prints == null)
            {
                _prints = new Texture2D(PrintRes, PrintRes, TextureFormat.RGBAFloat, false, true)
                {
                    name = "FogPrints", filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp
                };
                NativeArray<Color> px = _prints.GetPixelData<Color>(0);
                for (int i = 0; i < px.Length; i++) px[i] = default(Color);
                _prints.Apply(false, false);
                _fogMat.SetTexture(_printsId, _prints);
                _lastRegrow = -1f;
            }
            return true;
        }

        bool ClosestOnFog(Vector3 world, out FogMesh best, out int bestTri, out Vector3 bestBary)
        {
            best = null; bestTri = -1; bestBary = Vector3.zero;
            float rad = Mathf.Max(0.01f, printSearchRadius), bestD = rad * rad;
            foreach (var fm in _fogMeshes)
            {
                if (fm.t == null) continue;
                Vector3 p = fm.t.InverseTransformPoint(world);
                for (int t = 0; t < fm.tri.Length; t += 3)
                {
                    Vector3 a = fm.v[fm.tri[t]], b = fm.v[fm.tri[t + 1]], c = fm.v[fm.tri[t + 2]];
                    Vector3 q = ClosestOnTriangle(p, a, b, c, out Vector3 bary);
                    float d = fm.t.TransformVector(q - p).sqrMagnitude;
                    if (d < bestD) { bestD = d; best = fm; bestTri = t; bestBary = bary; }
                }
            }
            return best != null;
        }

        // Ericson, Real-Time Collision Detection 5.1.5, with barycentric output
        static Vector3 ClosestOnTriangle(Vector3 p, Vector3 a, Vector3 b, Vector3 c, out Vector3 bary)
        {
            Vector3 ab = b - a, ac = c - a, ap = p - a;
            float d1 = Vector3.Dot(ab, ap), d2 = Vector3.Dot(ac, ap);
            if (d1 <= 0f && d2 <= 0f) { bary = new Vector3(1, 0, 0); return a; }
            Vector3 bp = p - b;
            float d3 = Vector3.Dot(ab, bp), d4 = Vector3.Dot(ac, bp);
            if (d3 >= 0f && d4 <= d3) { bary = new Vector3(0, 1, 0); return b; }
            float vc = d1 * d4 - d3 * d2;
            if (vc <= 0f && d1 >= 0f && d3 <= 0f) { float v = d1 / (d1 - d3); bary = new Vector3(1 - v, v, 0); return a + v * ab; }
            Vector3 cp = p - c;
            float d5 = Vector3.Dot(ab, cp), d6 = Vector3.Dot(ac, cp);
            if (d6 >= 0f && d5 <= d6) { bary = new Vector3(0, 0, 1); return c; }
            float vb = d5 * d2 - d1 * d6;
            if (vb <= 0f && d2 >= 0f && d6 <= 0f) { float w = d2 / (d2 - d6); bary = new Vector3(1 - w, 0, w); return a + w * ac; }
            float va = d3 * d6 - d5 * d4;
            if (va <= 0f && (d4 - d3) >= 0f && (d5 - d6) >= 0f)
            {
                float w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
                bary = new Vector3(0, 1 - w, w);
                return b + w * (c - b);
            }
            float denom = 1f / (va + vb + vc);
            float vv = vb * denom, ww = vc * denom;
            bary = new Vector3(1 - vv - ww, vv, ww);
            return a + ab * vv + ac * ww;
        }

        static float BrushValue(Texture2D tex, FogBrush brush, float bx, float by)
        {
            if (tex != null && tex.isReadable) return tex.GetPixelBilinear((bx + 1f) * 0.5f, (by + 1f) * 0.5f).r;
            float d = Mathf.Sqrt(bx * bx + by * by);                     // fallback: soft round dab
            return Mathf.Clamp01((1f - d) / (brush == FogBrush.Finger ? 0.35f : 0.5f));
        }

        // ---------------------------------------------------------------- per frame
        void Update()
        {
            float dt = Time.deltaTime;

            // exterior
            UpdatePropeller(dt);
            _wheelAngle = Mathf.Repeat(_wheelAngle + mainWheelSpeed / (2f * Mathf.PI * MainR) * 360f * dt, 360f);
            _tailWheelAngle = Mathf.Repeat(_tailWheelAngle + tailWheelSpeed / (2f * Mathf.PI * TailR) * 360f * dt, 360f);
            Rot("Wheel_L", _wheelAngle, 0, 0);
            Rot("Wheel_R", _wheelAngle, 0, 0);
            Rot("TailWheel", _tailWheelAngle, 0, 0);
            Rot("Gear_L", 0, 0, -SwingDeg(_armL, gearCompressionL * mainGearTravel));
            Rot("Gear_R", 0, 0, SwingDeg(_armR, gearCompressionR * mainGearTravel));
            Rot("TailGear", SwingDeg(_armT, tailGearCompression * tailGearTravel), 0, 0);
            Rot("TailWheel_Fork", 0, tailWheelSteerDeg, 0);
            Rot("Rudder", 0, -rudderDeg, 0);
            Rot("Elevator_L", elevatorDeg, 0, 0);
            Rot("Elevator_R", elevatorDeg, 0, 0);
            Rot("Aileron_R", aileronDeg, 0, 0);
            Rot("Aileron_L", -aileronDeg, 0, 0);
            Rot("Flap_L", -flapDeg, 0, 0);
            Rot("Flap_R", -flapDeg, 0, 0);
            Rot("PilotDoor_L", 0, 70f * pilotDoorL, 0);
            Rot("PilotDoor_R", 0, -70f * pilotDoorR, 0);
            Rot("CargoDoor_L", 0, -100f * cargoDoorL, 0);
            Rot("CargoDoor_R", 0, 100f * cargoDoorR, 0);
            Rot("FuelCap_L", -110f * fuelCapL, 0, 0);
            Rot("FuelCap_R", -110f * fuelCapR, 0, 0);

            // cockpit controls
            Pos("Yoke_P", 0, 0.08f * yokePitch);
            Pos("Yoke_C", 0, 0.08f * yokePitch);
            Rot("Yoke_P_Roll", 0, 0, -50f * yokeRoll);
            Rot("Yoke_C_Roll", 0, 0, -50f * yokeRoll);
            Rot("PedalP_L", -12f * pedals, 0, 0);
            Rot("PedalP_R", 12f * pedals, 0, 0);
            Rot("PedalC_L", -12f * pedals, 0, 0);
            Rot("PedalC_R", 12f * pedals, 0, 0);
            Rot("Lever_Power", 25f * powerLever, 0, 0);
            Rot("Lever_Prop", 25f * propLever, 0, 0);
            Rot("Lever_Condition", 25f * conditionLever, 0, 0);
            Rot("Lever_Flap", -12f * flapLever, 0, 0);
            Rot("TrimWheel", -trimWheelDeg, 0, 0);
            Rot("Visor_P", -80f * visorP, 0, 0);
            Rot("Visor_C", -80f * visorC, 0, 0);
            Rot("FuelSel_L", fuelSelL ? 0f : 60f, 0, 0);
            Rot("FuelSel_R", fuelSelR ? 0f : 60f, 0, 0);
            Rot("Glovebox_Lid", -80f * Mathf.Clamp01(mapCase), 0, 0);
            if (autoStarterGuard)
                starterGuard = Mathf.MoveTowards(starterGuard, switchesOn.Contains("SW_Starter") ? 1f : 0f, 6f * dt);
            Rot("Guard_Starter", 95f * Mathf.Clamp01(starterGuard), 0, 0);
            Pos("Pull_CabinHeat", 0, -0.06f * pullCabinHeat);
            Pos("Pull_Defrost", 0, -0.06f * pullDefrost);
            Pos("Pull_ParkBrake", 0, -0.06f * pullParkBrake);
            Pos("Pull_FuelShutoff", 0, -0.06f * pullFuelShutoff);
            Rot("Rheo_Panel", 0, 0, -270f * panelLight);
            Rot("Rheo_Flood", 0, 0, -270f * floodLight);
            Pos("Btn_AnnunTest", 0, annunciatorTestPressed ? 0.003f : 0f);
            Show("Belt_P_On", beltP); Show("Belt_P_Off", !beltP);
            Show("Belt_C_On", beltC); Show("Belt_C_Off", !beltC);
            for (int i = 0; i < PaxSeatNames.Length; i++)
            {
                float down = paxSeatDown != null && i < paxSeatDown.Length ? Mathf.Clamp01(paxSeatDown[i]) : 0f;
                float s = PaxSeatNames[i][8] == 'L' ? 1f : -1f;             // left pans fold up towards +X model = Unity -X
                float a = PaxSeatFoldDeg * (1f - down);
                Rot(PaxSeatNames[i], 0, 0, s * a);
                Rot(PaxLegNames[i], 0, 0, -s * a);
            }
            Show("Stow_LadderStraps", ladderStowed);
            for (int i = 0; i < _switchNames.Count; i++)
                Rot(_switchNames[i], switchesOn.Contains(_switchNames[i]) ? 40f : 0f, 0, 0);

            // v7 knobs: clockwise = negative local Z
            if (radioKnobDeg != null)
                for (int i = 0; i < RadioKnobNames.Length && i < radioKnobDeg.Length; i++)
                    Rot(RadioKnobNames[i], 0, 0, -radioKnobDeg[i]);
            Rot("Knob_XPDR_Mode", 0, 0, -XpdrDetentDeg[Mathf.Clamp(xpdrMode, 0, XpdrDetentDeg.Length - 1)]);
            float baroSet = Mathf.Clamp(altimeterSettingInHg, 28.6f, 31.0f);
            Rot("Knob_ALT_Baro", 0, 0, -(autoKnobs ? (baroSet - 29.92f) * 360f : baroKnobDeg));
            Rot("Knob_HDG_Bug", 0, 0, -(autoKnobs ? headingBugDeg : hdgBugKnobDeg));
            Rot("Knob_DG_Set", 0, 0, -dgSetKnobDeg);

            // instruments: clockwise = negative local Z
            Needle("Needle_ASI", -1.6f * Mathf.Clamp(iasKt, 0, 200), dt);
            Needle("Needle_ALT100", -0.36f * Mathf.Repeat(altitudeFt, 1000f), dt, wrap: true);
            Needle("Needle_ALT1000", -0.036f * Mathf.Repeat(altitudeFt, 10000f), dt, wrap: true);
            Needle("Needle_VSI", -0.0825f * Mathf.Clamp(vsiFpm, -2000, 2000), dt);
            Needle("Needle_TRQ", -0.1125f * Mathf.Clamp(torqueFtLb, 0, 2400), dt);
            Needle("Needle_PROP", -0.1125f * Mathf.Clamp(propRpmGauge, 0, 2400), dt);
            Needle("Needle_ITT", -0.27f * Mathf.Clamp(ittC - 100f, 0, 1000), dt);
            Needle("Needle_NG", -2.4545f * Mathf.Clamp(ngPct, 0, 110), dt);
            Needle("Needle_OILP", -0.6f * Mathf.Clamp(oilPsi, 0, 200), dt);
            Needle("Needle_OILT", 0.8f * Mathf.Clamp(oilC, 0, 150), dt);   // this pointer runs anticlockwise
            Needle("Needle_FF", -0.675f * Mathf.Clamp(fuelFlowPph, 0, 400), dt);
            Needle("Needle_FUELL", -2f * Mathf.Clamp(fuelLGal, 0, 60), dt);
            Needle("Needle_FUELR", -2f * Mathf.Clamp(fuelRGal, 0, 60), dt);
            Needle("Needle_AMP", -1.5f * Mathf.Clamp(amps, -60, 60), dt);
            Needle("Needle_OAT", -3f * (Mathf.Clamp(oatC, -40, 50) + 20f), dt);
            Needle("Needle_VOLT", -7.714f * Mathf.Clamp(busVolts, 0, 35), dt);
            Needle("Needle_VAC", -27f * Mathf.Clamp(suctionInHg, 0, 10), dt);
            Needle("Clock_Hour", -30f * Mathf.Repeat(clockHours, 12f), 0, wrap: true);
            Needle("Clock_Min", -6f * Mathf.Repeat(clockMinutes, 60f), 0, wrap: true);
            Needle("ATT_Roll", bankDeg, dt);                                   // card turns against the bank
            NeedlePos("ATT_Pitch", -0.0006f * Mathf.Clamp(pitchDeg, -20, 20), dt);
            Needle("HDG_Card", Mathf.Repeat(headingDeg, 360f), dt, wrap: true);
            Needle("TC_Plane", -(20f / 3f) * Mathf.Clamp(turnRateDegS, -6, 6), dt);
            Needle("TC_Ball", 15f * Mathf.Clamp(slip, -1, 1), dt);
            Rot("ALT_Baro", 0, 0, -(baroSet - 29.92f) * BaroDegPerInHg);          // v7 Kollsman disc
            Rot("HDG_Bug", 0, 0, -headingBugDeg);                                // v7, child of HDG_Card
            Rot("Compass_Card", 0, -compassHeadingDeg, 0);                       // v7 drum card, vertical axis

            // lamps, lenses, backlight, lights
            for (int i = 0; i < 12; i++)
            {
                bool on = busPowered && (annunciatorTestPressed || (lamps != null && i < lamps.Length && lamps[i]));
                Emit(LampNames[i], lampGlow, on ? lampIntensity : 0f);
            }
            _strobeT += dt; _beaconT += dt;
            float strobe = strobeLights * StrobePulse(_strobeT);
            float beacon = beaconLights * BeaconPulse(_beaconT);
            Lens("Lens_Nav_L", new Color(1f, 0.02f, 0.01f), navLights * 6f);
            Lens("Lens_Nav_R", new Color(0.02f, 1f, 0.15f), navLights * 6f);
            Lens("Lens_Nav_Tail", Color.white, navLights * 5f);
            Lens("Lens_Strobe_L", Color.white, strobe * 30f);
            Lens("Lens_Strobe_R", Color.white, strobe * 30f);
            Lens("Lens_Beacon_Top", new Color(1f, 0.08f, 0.01f), beacon * 12f);
            Lens("Lens_Beacon_Bottom", new Color(1f, 0.08f, 0.01f), beacon * 12f);
            Lens("Lens_Landing", new Color(1f, 0.97f, 0.9f), landingLight * 8f);
            Lens("Lens_Dome", new Color(1f, 0.85f, 0.62f), cabinLight * 3f);
            Lens("Lens_CargoLight", new Color(1f, 0.85f, 0.62f), cargoLight * 3f);
            Backlight(busPowered ? panelLight : 0f);
            Emit("Display_Radio", Color.white, radioDisplayIntensity * Mathf.Clamp01(avionicsPower));
            if (!screensDrivenExternally)
                for (int i = 0; i < DisplayNames.Length; i++)
                {
                    float p = DisplayNames[i] == "Display_Hobbs" ? (busPowered ? 1f : 0f) : Mathf.Clamp01(avionicsPower);
                    Emit(DisplayNames[i], screenIdleGlow, screenIdleIntensity * p);
                }
            UpdateFog();
            SetLight("Nav_L", navLights); SetLight("Nav_R", navLights); SetLight("Nav_Tail", navLights);
            SetLight("Strobe_L", strobe); SetLight("Strobe_R", strobe);
            SetLight("Beacon_Top", beacon); SetLight("Beacon_Bottom", beacon);
            SetLight("Landing", landingLight);
            SetLight("Dome_L", cabinLight); SetLight("Dome_R", cabinLight);
            SetLight("Cargo", cargoLight); SetLight("Cargo_2", cargoLight);
            SetLight("Flood", busPowered ? floodLight : 0f);
        }

        // v7: solid blades at low rpm, smeared blades (PropBlur) in between, an even disc (PropDisc) at speed.
        // 1900 rpm x 3 blades = 95 blade passes per second: a mesh turning that fast strobes at any frame rate.
        void UpdatePropeller(float dt)
        {
            float rpm = Mathf.Max(0f, propRpm);
            if (autoFeather)
                propFeather = Mathf.MoveTowards(propFeather, rpm >= blurStartRpm ? 0f : (rpm <= 120f ? 1f : propFeather),
                                                0.5f * dt);
            for (int i = 0; i < BladeNames.Length; i++)
                Rot(BladeNames[i], 0, -FeatherDeg * Mathf.Clamp01(propFeather), 0);

            _propAngle = Mathf.Repeat(_propAngle + rpm * 6f * dt, 360f);
            Rot("Propeller", 0, 0, -_propAngle);                      // clockwise seen from the cockpit
            bool blades = rpm < bladesHideRpm;
            for (int i = 0; i < _bladeR.Count; i++) _bladeR[i].enabled = blades;

            float blurA = Mathf.Clamp01(Mathf.InverseLerp(blurStartRpm, bladesHideRpm, rpm)) *
                          (1f - Mathf.Clamp01(Mathf.InverseLerp(discStartRpm, discFullRpm, rpm)));
            float discA = Mathf.Clamp01(Mathf.InverseLerp(discStartRpm, discFullRpm, rpm));
            _blurAngle = Mathf.Repeat(_blurAngle + Mathf.Min(rpm, blurVisualRpmMax) * 6f * dt, 360f);
            _discAngle = Mathf.Repeat(_discAngle + 20f * dt, 360f);
            Rot("PropBlur", 0, 0, -_blurAngle);
            Rot("PropDisc", 0, 0, -_discAngle);
            SetAlpha(_blurMat, _blurR, blurA, ref _lastBlurA);
            SetAlpha(_discMat, _discR, discA, ref _lastDiscA);
        }

        void SetAlpha(Material m, Renderer r, float a, ref float last)
        {
            if (r != null) r.enabled = a > 0.003f;
            if (m == null || Mathf.Abs(a - last) < 0.002f) return;
            last = a;
            if (m.HasProperty(_baseColorId))
            {
                var c = m.GetColor(_baseColorId);
                c.a = a;
                m.SetColor(_baseColorId, c);
            }
        }

        void UpdateFog()
        {
            if (_fogMat == null) return;
            _printClock += Time.deltaTime;
            if (_prints != null && _fogShader)
            {
                _fogMat.SetFloat(_printTimeId, _printClock);
                if (Mathf.Abs(printRegrowSeconds - _lastRegrow) > 1e-3f || Mathf.Abs(latentPrintVisibility - _lastLatent) > 1e-3f)
                {
                    _lastRegrow = printRegrowSeconds; _lastLatent = latentPrintVisibility;
                    _fogMat.SetFloat(_printRegrowId, Mathf.Max(0.01f, printRegrowSeconds));
                    _fogMat.SetFloat(_latentId, latentPrintVisibility);
                }
            }
            float key = fogMaxAlpha + fogColor.r * 3f + fogColor.g * 5f + fogColor.b * 7f;
            if (Mathf.Abs(windshieldFog - _lastFogW) < 0.002f && Mathf.Abs(sideWindowFog - _lastFogS) < 0.002f &&
                Mathf.Abs(key - _lastFogKey) < 1e-4f) return;
            _lastFogW = windshieldFog; _lastFogS = sideWindowFog; _lastFogKey = key;
            // no fog, no draw: an invisible veil would still cost a transparent pass over every pane
            bool ws = windshieldFog > 0.003f, side = sideWindowFog > 0.003f;
            for (int i = 0; i < _fogR.Count; i++)
                if (_fogR[i] != null) _fogR[i].enabled = _fogR[i].name == "Glass_Fog" ? (ws || side) : side;
            if (_fogShader)
            {
                _fogMat.SetFloat(_fogId, Mathf.Clamp01(windshieldFog));
                _fogMat.SetFloat(_fogSideId, Mathf.Clamp01(sideWindowFog));
                _fogMat.SetColor(_fogColorId, fogColor);
                _fogMat.SetFloat(_fogAlphaId, fogMaxAlpha);
            }
            else if (_fogMat.HasProperty(_baseColorId))                      // HDRP / Built-in fallback: even veil
            {
                var c = fogColor;
                c.a = fogMaxAlpha * 0.7f * Mathf.Max(Mathf.Clamp01(windshieldFog), Mathf.Clamp01(sideWindowFog));
                _fogMat.SetColor(_baseColorId, c);
            }
        }

        // double flash ~50 per minute
        static float StrobePulse(float t)
        {
            float p = Mathf.Repeat(t, 1.2f);
            return (p < 0.05f || (p > 0.15f && p < 0.20f)) ? 1f : 0f;
        }

        // ~45 per minute, soft
        static float BeaconPulse(float t)
        {
            float p = Mathf.Repeat(t, 1.33f) / 1.33f;
            return Mathf.Clamp01(1f - Mathf.Abs(p - 0.15f) * 8f);
        }

        // ---------------------------------------------------------------- helpers
        // main legs swing about their local Z (arm in the local XY plane), the tail spring about its local X (YZ plane)
        Arm MakeArm(string leg, string wheel, bool aboutZ)
        {
            if (!_parts.TryGetValue(leg, out var l) || !_parts.TryGetValue(wheel, out var w)) return default(Arm);
            Vector3 p = l.t.InverseTransformPoint(w.t.position);
            float h = aboutZ ? Mathf.Abs(p.x) : Mathf.Abs(p.z), v = -p.y;
            return new Arm { r = Mathf.Sqrt(h * h + v * v), phi0 = Mathf.Atan2(v, h), ok = h > 0.01f && v > 0f };
        }

        // swing angle (deg, >= 0) that lifts the wheel centre by `lift` metres
        static float SwingDeg(Arm a, float lift)
        {
            if (!a.ok || lift <= 0f) return 0f;
            float s = Mathf.Clamp(Mathf.Sin(a.phi0) - lift / a.r, -1f, 1f);
            return (a.phi0 - Mathf.Asin(s)) * Mathf.Rad2Deg;
        }

        void Rot(string n, float x, float y, float z)
        {
            if (_parts.TryGetValue(n, out var p)) p.t.localRotation = p.rot * Quaternion.Euler(x, y, z);
        }

        void Pos(string n, float y, float z)
        {
            if (_parts.TryGetValue(n, out var p)) p.t.localPosition = p.pos + p.rot * new Vector3(0f, y, z);
        }

        void Show(string n, bool on)
        {
            if (_parts.TryGetValue(n, out var p)) p.t.localScale = on ? p.scale : Vector3.zero;
        }

        // Spring step, substepped so that long frames (hitches, low FPS) cannot make the explicit integration explode.
        void Spring(Part p, float target, float dt, bool wrap)
        {
            int steps = Mathf.Clamp(Mathf.CeilToInt(dt / 0.02f), 1, 50);
            float h = dt / steps;
            for (int k = 0; k < steps; k++)
            {
                float err = wrap ? Mathf.DeltaAngle(p.value, target) : target - p.value;
                p.vel += (needleOmega * needleOmega * err - 2f * needleDamping * needleOmega * p.vel) * h;
                p.value += p.vel * h;
            }
        }

        void Needle(string n, float targetDeg, float dt, bool wrap = false)
        {
            if (!_parts.TryGetValue(n, out var p)) return;
            if (dt <= 0f || wrap && Mathf.Abs(Mathf.DeltaAngle(p.value, targetDeg)) > 90f)
            {
                p.value = targetDeg; p.vel = 0f;
            }
            else Spring(p, targetDeg, dt, wrap);
            p.t.localRotation = p.rot * Quaternion.Euler(0f, 0f, p.value);
        }

        void NeedlePos(string n, float targetY, float dt)
        {
            if (!_parts.TryGetValue(n, out var p)) return;
            if (dt > 0f) Spring(p, targetY, dt, false);
            p.t.localPosition = p.pos + p.rot * new Vector3(0f, p.value, 0f);
        }

        // HDR emission: SetColor would treat values above 1 as sRGB and gamma-convert them, so pass a linear vector.
        Vector4 EmissionValue(Color tint, float k)
        {
            Color c = QualitySettings.activeColorSpace == ColorSpace.Linear ? tint.linear : tint;
            float scale = k * (_hdrp ? hdrpEmissionScale : 1f);
            return new Vector4(c.r * scale, c.g * scale, c.b * scale, 1f);
        }

        void SetEmission(Material m, Vector4 v)
        {
            if (m == null) return;
            if (_lastEmission.TryGetValue(m, out var last) && last == v) return;     // no redundant uploads
            _lastEmission[m] = v;
            m.SetVector(_emissionId, v);
        }

        void Emit(string rendererName, Color tint, float k)
        {
            if (_emitMats.TryGetValue(rendererName, out var m)) SetEmission(m, EmissionValue(tint, k));
        }

        void Lens(string n, Color c, float intensity) => Emit(n, c, intensity);

        void Backlight(float level) => SetEmission(_gaugesMat, EmissionValue(new Color(1f, 0.55f, 0.25f), 0.6f * level));

        /// <summary>One light source of the plane. Intensity: Built-in/URP units, and candela for HDRP (TEMPORARY).</summary>
        public struct LightDef
        {
            public string key, socket;
            public LightType type;
            public Color color;
            public float range, intensity, hdrpCandela, spotAngle;
            public Vector3 euler;

            public LightDef(string key, string socket, LightType type, Color color, float range, float intensity,
                            float hdrpCandela, float spotAngle, Vector3 euler)
            {
                this.key = key; this.socket = socket; this.type = type; this.color = color; this.range = range;
                this.intensity = intensity; this.hdrpCandela = hdrpCandela; this.spotAngle = spotAngle; this.euler = euler;
            }
        }

        public static readonly LightDef[] LightDefs =
        {
            new LightDef("Nav_L", "Socket_Nav_L", LightType.Point, new Color(1f, 0.1f, 0.05f), 3f, 2f, 40f, 0f, Vector3.zero),
            new LightDef("Nav_R", "Socket_Nav_R", LightType.Point, new Color(0.1f, 1f, 0.2f), 3f, 2f, 40f, 0f, Vector3.zero),
            new LightDef("Nav_Tail", "Socket_Nav_Tail", LightType.Point, Color.white, 3f, 2f, 20f, 0f, Vector3.zero),
            new LightDef("Strobe_L", "Socket_Strobe_L", LightType.Point, Color.white, 10f, 8f, 800f, 0f, Vector3.zero),
            new LightDef("Strobe_R", "Socket_Strobe_R", LightType.Point, Color.white, 10f, 8f, 800f, 0f, Vector3.zero),
            new LightDef("Beacon_Top", "Socket_Beacon_Top", LightType.Point, new Color(1f, 0.1f, 0.02f), 8f, 4f, 150f, 0f, Vector3.zero),
            new LightDef("Beacon_Bottom", "Socket_Beacon_Bottom", LightType.Point, new Color(1f, 0.1f, 0.02f), 8f, 4f, 150f, 0f, Vector3.zero),
            new LightDef("Landing", "Socket_Landing", LightType.Spot, new Color(1f, 0.97f, 0.9f), 150f, 12f, 50000f, 28f, new Vector3(4f, 0f, 0f)),
            new LightDef("Dome_L", "Socket_Light_Dome_L", LightType.Point, new Color(1f, 0.85f, 0.62f), 1.8f, 0.8f, 2f, 0f, Vector3.zero),
            new LightDef("Dome_R", "Socket_Light_Dome_R", LightType.Point, new Color(1f, 0.85f, 0.62f), 1.8f, 0.8f, 2f, 0f, Vector3.zero),
            new LightDef("Cargo", "Socket_Light_Cargo", LightType.Point, new Color(1f, 0.85f, 0.62f), 2.5f, 0.8f, 3f, 0f, Vector3.zero),
            new LightDef("Cargo_2", "Socket_Light_Cargo_2", LightType.Point, new Color(1f, 0.85f, 0.62f), 2.5f, 0.8f, 3f, 0f, Vector3.zero),
            new LightDef("Flood", "Socket_Light_Flood", LightType.Spot, new Color(1f, 0.6f, 0.35f), 1.5f, 0.6f, 3f, 100f, new Vector3(60f, 0f, 0f)),
        };

        /// <summary>
        /// Creates the missing Light_&lt;key&gt; objects under their sockets. Used by the editor build step and, if the prefab has
        /// no lights, at runtime. HDRP: adds HDAdditionalLightData through reflection (no package reference needed) and writes
        /// Light.intensity in candela, the native unit of punctual lights in Unity 6 HDRP.
        /// </summary>
        public static int BuildLights(Transform root, bool hdrp)
        {
            var all = root.GetComponentsInChildren<Transform>(true);
            System.Type hdType = hdrp ? FindType("UnityEngine.Rendering.HighDefinition.HDAdditionalLightData") : null;
            int made = 0;
            foreach (var d in LightDefs)
            {
                Transform socket = null, found = null;
                foreach (var t in all)
                {
                    if (t.name == d.socket) socket = t;
                    if (t.name == "Light_" + d.key) found = t;
                }
                if (socket == null || found != null) continue;
                var go = new GameObject("Light_" + d.key);
                go.transform.SetParent(socket, false);
                go.transform.localRotation = Quaternion.Euler(d.euler);
                var l = go.AddComponent<Light>();
                l.type = d.type;
                if (hdType != null)
                {
                    // HDRP: same as its AddHDLight helper — add the additional data and apply its defaults, then override.
                    Component hd = go.GetComponent(hdType);          // no ?? on Unity objects (fake null in the editor)
                    if (hd == null) hd = go.AddComponent(hdType);
                    try
                    {
                        hdType.GetMethod("InitDefaultHDAdditionalLightData",
                                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static)
                            ?.Invoke(null, new object[] { hd });
                    }
                    catch (System.Exception e) { Debug.LogWarning("[UtilityPlane] HDRP light defaults: " + e.Message); }
                }
                l.color = d.color;
                l.range = d.range;
                l.shadows = LightShadows.None;
                if (d.type == LightType.Spot) l.spotAngle = d.spotAngle;
                l.intensity = hdrp ? d.hdrpCandela : d.intensity;
                l.enabled = false;
                made++;
            }
            return made;
        }

        static System.Type FindType(string fullName)
        {
            foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(fullName);
                if (t != null) return t;
            }
            return null;
        }

        readonly Dictionary<string, float> _maxIntensity = new Dictionary<string, float>();

        void SetLight(string key, float level)
        {
            if (!_lights.TryGetValue(key, out var l)) return;
            l.intensity = _maxIntensity[key] * Mathf.Clamp01(level);
            l.enabled = level > 0.001f;
        }
    }
}
