using UnityEngine;

namespace UtilityPlane
{
    /// <summary>
    /// Drives the moving parts of the Utility Plane model. Every part's pivot sits on its real hinge/axle:
    /// propeller spins on local Z, wheels on local X, control surfaces hinge on local X, rudder/tail wheel/door on local Y.
    /// Feed the public inputs from your own flight/vehicle controller.
    /// </summary>
    [DisallowMultipleComponent]
    public class UtilityPlaneRig : MonoBehaviour
    {
        [Header("Parts (Auto Assign finds them by name)")]
        public Transform propeller;
        public Transform wheelL, wheelR, tailWheel, tailWheelFork;
        public Transform rudder, elevatorL, elevatorR, aileronL, aileronR, flapL, flapR;
        public Transform cargoDoor, centerOfMass;

        [Header("Limits, degrees")]
        public float elevatorMax = 25f;
        public float aileronMax = 20f;
        public float rudderMax = 25f;
        public float flapMax = 35f;
        public float tailWheelSteerMax = 30f;
        [Tooltip("Local Y angle of the fully open cargo door (door closed = 0).")]
        public float doorOpenAngle = -100f;

        [Header("Wheel radii, meters")]
        public float mainWheelRadius = 0.48f;
        public float tailWheelRadius = 0.28f;

        [Header("Inputs")]
        [Range(-1f, 1f)] public float pitch;
        [Range(-1f, 1f)] public float roll;
        [Range(-1f, 1f)] public float yaw;
        [Range(0f, 1f)] public float flaps;
        [Range(0f, 1f)] public float door = 1f;
        public float propellerRpm;
        [Tooltip("Forward ground speed, m/s (used to roll the wheels).")]
        public float groundSpeed;

        Quaternion _elL, _elR, _aiL, _aiR, _flL, _flR, _rud, _fork;

        void Awake()
        {
            if (propeller == null) AutoAssign();
            _elL = Rest(elevatorL); _elR = Rest(elevatorR);
            _aiL = Rest(aileronL); _aiR = Rest(aileronR);
            _flL = Rest(flapL); _flR = Rest(flapR);
            _rud = Rest(rudder); _fork = Rest(tailWheelFork);
            var rb = GetComponent<Rigidbody>();
            if (rb != null && centerOfMass != null)
                rb.centerOfMass = transform.InverseTransformPoint(centerOfMass.position);
        }

        static Quaternion Rest(Transform t) => t != null ? t.localRotation : Quaternion.identity;

        public void AutoAssign()
        {
            propeller = Find("Propeller");
            wheelL = Find("Wheel_L"); wheelR = Find("Wheel_R");
            tailWheel = Find("TailWheel"); tailWheelFork = Find("TailWheel_Fork");
            rudder = Find("Rudder");
            elevatorL = Find("Elevator_L"); elevatorR = Find("Elevator_R");
            aileronL = Find("Aileron_L"); aileronR = Find("Aileron_R");
            flapL = Find("Flap_L"); flapR = Find("Flap_R");
            cargoDoor = Find("CargoDoor");
            centerOfMass = Find("CenterOfMass");
        }

        Transform Find(string n)
        {
            foreach (var t in GetComponentsInChildren<Transform>(true))
                if (t.name == n) return t;
            return null;
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (propeller) propeller.Rotate(0f, 0f, propellerRpm * 6f * dt, Space.Self);

            float main = groundSpeed / (2f * Mathf.PI * mainWheelRadius) * 360f * dt;
            if (wheelL) wheelL.Rotate(main, 0f, 0f, Space.Self);
            if (wheelR) wheelR.Rotate(main, 0f, 0f, Space.Self);
            if (tailWheel)
                tailWheel.Rotate(groundSpeed / (2f * Mathf.PI * tailWheelRadius) * 360f * dt, 0f, 0f, Space.Self);

            // +X rotation lifts a trailing edge. Positive pitch = nose up, positive roll = right wing down,
            // positive yaw = nose right.
            Set(elevatorL, _elL, pitch * elevatorMax);
            Set(elevatorR, _elR, pitch * elevatorMax);
            Set(aileronR, _aiR, roll * aileronMax);
            Set(aileronL, _aiL, -roll * aileronMax);
            Set(flapL, _flL, -flaps * flapMax);
            Set(flapR, _flR, -flaps * flapMax);
            if (rudder) rudder.localRotation = _rud * Quaternion.Euler(0f, -yaw * rudderMax, 0f);
            if (tailWheelFork) tailWheelFork.localRotation = _fork * Quaternion.Euler(0f, yaw * tailWheelSteerMax, 0f);
            if (cargoDoor) cargoDoor.localRotation = Quaternion.Euler(0f, doorOpenAngle * door, 0f);
        }

        static void Set(Transform t, Quaternion rest, float deg)
        {
            if (t) t.localRotation = rest * Quaternion.Euler(deg, 0f, 0f);
        }
    }
}
