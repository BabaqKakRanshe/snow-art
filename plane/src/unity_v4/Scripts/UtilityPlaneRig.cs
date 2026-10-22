using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace UtilityPlane
{
    /// <summary>
    /// Presentation layer of the Utility Plane (v4). Reads state that your gameplay / physics code writes into the
    /// public fields and moves every part, needle, lamp and light of the model. It never computes physics.
    ///
    /// Axis rules (all parts rest with identity rotation, except ailerons/flaps which carry the 2 deg dihedral):
    ///   rotations are applied as  restRotation * Euler(...)  in the part's local space.
    ///   Needles and dials turn clockwise as the pilot sees them when the local Z angle is NEGATIVE.
    /// See UNITY_CONTRACT.md for the full table.
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
        [Tooltip("Main wheel rolling speed, m/s (+ = forward)")] public float mainWheelSpeed;
        [Tooltip("Tail wheel rolling speed, m/s")] public float tailWheelSpeed;
        [Range(0, 1)] public float gearCompressionL, gearCompressionR, tailGearCompression;
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

        [Tooltip("Toggle switches by object name, e.g. SW_Battery. Starter is momentary: keep it true while held.")]
        public List<string> switchesOn = new List<string>();
        [Tooltip("Pull knobs 0..1 (1 = pulled): Pull_CabinHeat, Pull_Defrost, Pull_ParkBrake, Pull_FuelShutoff")]
        public float pullCabinHeat, pullDefrost, pullParkBrake, pullFuelShutoff;
        [Range(0, 1), Tooltip("Rheostats 0..1")] public float panelLight, floodLight;
        [Tooltip("Fuel tank selectors: true = ON (handle down)")] public bool fuelSelL = true, fuelSelR = true;

        // ---------------------------------------------------------------- instruments (sensor outputs, not truth)
        [Header("Instrument readings (from your sensor models)")]
        public float iasKt, altitudeFt, vsiFpm, pitchDeg, bankDeg, headingDeg, turnRateDegS;
        [Range(-1, 1), Tooltip("slip ball, + = ball right")] public float slip;
        public float torqueFtLb, propRpmGauge, ittC, ngPct, oilPsi, oilC, fuelFlowPph, fuelLGal, fuelRGal, amps, oatC;
        public float clockHours, clockMinutes;

        [Header("Needle dynamics")]
        public float needleOmega = 11f;
        public float needleDamping = 0.6f;

        // ---------------------------------------------------------------- lamps and lights
        [Header("Annunciator (index = Lamp_NN), lit only with bus power")]
        public bool busPowered;
        public bool[] lamps = new bool[12];
        public Color lampGlow = Color.white;
        public float lampIntensity = 3f;

        [Header("Lights (0..1 actual output, already including bus voltage)")]
        [Range(0, 1)] public float navLights, strobeLights, beaconLights, landingLight, cabinLight, cargoLight;
        [Tooltip("Create missing Light_* objects at the light sockets on Awake. Tools/Utility Plane/Build puts them into " +
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
        readonly Dictionary<string, Renderer> _renderers = new Dictionary<string, Renderer>();
        readonly Dictionary<string, Light> _lights = new Dictionary<string, Light>();
        readonly List<string> _switchNames = new List<string>();
        MaterialPropertyBlock _mpb;
        int _emissionId;
        bool _hdrp;
        float _propAngle, _wheelAngle, _tailWheelAngle, _strobeT, _beaconT;
        const float MainR = 0.484f, TailR = 0.285f;

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
            "Needle_OAT", "Clock_Hour", "Clock_Min", "ATT_Roll", "ATT_Pitch", "HDG_Card", "TC_Plane", "TC_Ball"
        };

        void Awake()
        {
            _mpb = new MaterialPropertyBlock();
            var rp = GraphicsSettings.currentRenderPipeline;
            _hdrp = rp != null && rp.GetType().Name.Contains("HDRenderPipeline");
            _emissionId = Shader.PropertyToID(_hdrp ? "_EmissiveColor" : "_EmissionColor");
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (!_parts.ContainsKey(t.name))
                    _parts[t.name] = new Part { t = t, rot = t.localRotation, pos = t.localPosition, scale = t.localScale };
                if (t.name.StartsWith("SW_", System.StringComparison.Ordinal) && !_switchNames.Contains(t.name))
                    _switchNames.Add(t.name);
                var r = t.GetComponent<Renderer>();
                if (r != null && (t.name.StartsWith("Lamp_", System.StringComparison.Ordinal) ||
                                  t.name.StartsWith("Lens_", System.StringComparison.Ordinal) ||
                                  t.name == "Cockpit_Static"))
                    _renderers[t.name] = r;
            }
            if (createLights) BuildLights(transform, _hdrp);
            foreach (var l in GetComponentsInChildren<Light>(true))
            {
                if (!l.name.StartsWith("Light_", System.StringComparison.Ordinal)) continue;
                string key = l.name.Substring(6);
                _lights[key] = l;
                _maxIntensity[key] = l.intensity;
            }
        }

        // ---------------------------------------------------------------- per frame
        void Update()
        {
            float dt = Time.deltaTime;

            // exterior
            _propAngle = Mathf.Repeat(_propAngle + propRpm * 6f * dt, 360f);
            _wheelAngle = Mathf.Repeat(_wheelAngle + mainWheelSpeed / (2f * Mathf.PI * MainR) * 360f * dt, 360f);
            _tailWheelAngle = Mathf.Repeat(_tailWheelAngle + tailWheelSpeed / (2f * Mathf.PI * TailR) * 360f * dt, 360f);
            Rot("Propeller", 0, 0, -_propAngle);                      // clockwise seen from the cockpit
            Rot("Wheel_L", _wheelAngle, 0, 0);
            Rot("Wheel_R", _wheelAngle, 0, 0);
            Rot("TailWheel", _tailWheelAngle, 0, 0);
            Rot("Gear_L", 0, 0, -12f * gearCompressionL);
            Rot("Gear_R", 0, 0, 12f * gearCompressionR);
            Rot("TailGear", 8f * tailGearCompression, 0, 0);
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
            Pos("Pull_CabinHeat", 0, -0.06f * pullCabinHeat);
            Pos("Pull_Defrost", 0, -0.06f * pullDefrost);
            Pos("Pull_ParkBrake", 0, -0.06f * pullParkBrake);
            Pos("Pull_FuelShutoff", 0, -0.06f * pullFuelShutoff);
            Rot("Rheo_Panel", 0, 0, -270f * panelLight);
            Rot("Rheo_Flood", 0, 0, -270f * floodLight);
            Pos("Btn_AnnunTest", 0, annunciatorTestPressed ? 0.003f : 0f);
            Show("Belt_P_On", beltP); Show("Belt_P_Off", !beltP);
            Show("Belt_C_On", beltC); Show("Belt_C_Off", !beltC);
            for (int i = 0; i < _switchNames.Count; i++)
                Rot(_switchNames[i], switchesOn.Contains(_switchNames[i]) ? 40f : 0f, 0, 0);

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
            Needle("Clock_Hour", -30f * Mathf.Repeat(clockHours, 12f), 0, wrap: true);
            Needle("Clock_Min", -6f * Mathf.Repeat(clockMinutes, 60f), 0, wrap: true);
            Needle("ATT_Roll", bankDeg, dt);                                   // card turns against the bank
            NeedlePos("ATT_Pitch", -0.0006f * Mathf.Clamp(pitchDeg, -20, 20), dt);
            Needle("HDG_Card", Mathf.Repeat(headingDeg, 360f), dt, wrap: true);
            Needle("TC_Plane", -(20f / 3f) * Mathf.Clamp(turnRateDegS, -6, 6), dt);
            Needle("TC_Ball", 15f * Mathf.Clamp(slip, -1, 1), dt);

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
            SetLight("Nav_L", navLights); SetLight("Nav_R", navLights); SetLight("Nav_Tail", navLights);
            SetLight("Strobe_L", strobe); SetLight("Strobe_R", strobe);
            SetLight("Beacon_Top", beacon); SetLight("Beacon_Bottom", beacon);
            SetLight("Landing", landingLight);
            SetLight("Light_Dome_L", cabinLight); SetLight("Light_Dome_R", cabinLight);
            SetLight("Light_Cargo", cargoLight);
            SetLight("Light_Flood", busPowered ? floodLight : 0f);
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

        void Emit(string rendererName, Color tint, float k)
        {
            if (!_renderers.TryGetValue(rendererName, out var r)) return;
            r.GetPropertyBlock(_mpb);
            _mpb.SetVector(_emissionId, EmissionValue(tint, k));
            r.SetPropertyBlock(_mpb);
        }

        void Lens(string n, Color c, float intensity) => Emit(n, c, intensity);

        void Backlight(float level)
        {
            if (!_renderers.TryGetValue("Cockpit_Static", out var r)) return;
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null || !mats[i].name.StartsWith("M_Gauges", System.StringComparison.Ordinal)) continue;
                r.GetPropertyBlock(_mpb, i);
                _mpb.SetVector(_emissionId, EmissionValue(new Color(1f, 0.55f, 0.25f), 0.6f * level));
                r.SetPropertyBlock(_mpb, i);
            }
        }

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
            new LightDef("Light_Dome_L", "Socket_Light_Dome_L", LightType.Point, new Color(1f, 0.85f, 0.62f), 1.8f, 0.8f, 2f, 0f, Vector3.zero),
            new LightDef("Light_Dome_R", "Socket_Light_Dome_R", LightType.Point, new Color(1f, 0.85f, 0.62f), 1.8f, 0.8f, 2f, 0f, Vector3.zero),
            new LightDef("Light_Cargo", "Socket_Light_Cargo", LightType.Point, new Color(1f, 0.85f, 0.62f), 3f, 1f, 4f, 0f, Vector3.zero),
            new LightDef("Light_Flood", "Socket_Light_Flood", LightType.Spot, new Color(1f, 0.6f, 0.35f), 1.5f, 0.6f, 3f, 100f, new Vector3(60f, 0f, 0f)),
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
