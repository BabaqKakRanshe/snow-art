// Риг ассета BushPlane: вращение винта и колёс, отклонение рулей, створки.
//
// Иерархия модели намеренно плоская — все подвижные части лежат прямым
// потомками корня. Так FBX экспортируется с запечённым преобразованием осей
// и приходит в Unity с единичным трансформом корня; при вложенности глубже
// первого уровня это преобразование портит дочерние объекты. Плата за это —
// колесо не следует за стойкой автоматически, и обжатие подвески двигает их
// обе (см. SetSuspension).
//
// Оси вращения уже в системе Unity, пересчитывать ничего не нужно:
//   винт           local Z
//   колёса         local X
//   руль направления, створки   local Y
//   рули высоты, элероны, закрылки  local X

using UnityEngine;

namespace BushPlaneAsset
{
    [DisallowMultipleComponent]
    public class BushPlaneRig : MonoBehaviour
    {
        [Header("Подвижные части")]
        public Transform propeller;
        public Transform wheelLeft;
        public Transform wheelRight;
        public Transform wheelTail;
        public Transform gearLegLeft;
        public Transform gearLegRight;
        public Transform aileronLeft;
        public Transform aileronRight;
        public Transform flapLeft;
        public Transform flapRight;
        public Transform elevatorLeft;
        public Transform elevatorRight;
        public Transform rudder;
        public Transform cargoDoorLeft;
        public Transform cargoDoorRight;
        public Transform cargoCrates;
        public Transform centerOfMass;

        [Header("Винт")]
        [Tooltip("Обороты в минуту. На холостом ходу около 700, на взлётном — 2200.")]
        public float propellerRpm = 1800f;
        public bool spinPropeller = true;

        [Header("Колёса")]
        [Tooltip("Радиус основного колеса в метрах — из него считается угол качения.")]
        public float mainWheelRadius = 0.52f;
        public float tailWheelRadius = 0.22f;

        [Header("Створки")]
        [Range(0f, 1f)] public float cargoDoorsOpen;
        public float cargoDoorOpenAngle = 104f;   // = CARGO_DOOR_OPEN_DEG в plane_params.py

        float _propAngle;
        float _wheelAngle;
        Vector3 _gearLegLeftHome, _gearLegRightHome, _wheelLeftHome, _wheelRightHome;
        bool _homesCaptured;

        void Awake()
        {
            if (propeller == null) AutoBind();
            CaptureHomes();
            var rb = GetComponent<Rigidbody>();
            if (rb != null && centerOfMass != null)
            {
                rb.centerOfMass = transform.InverseTransformPoint(centerOfMass.position);
            }
        }

        void Reset() { AutoBind(); }

        void CaptureHomes()
        {
            if (_homesCaptured) return;
            if (gearLegLeft != null) _gearLegLeftHome = gearLegLeft.localPosition;
            if (gearLegRight != null) _gearLegRightHome = gearLegRight.localPosition;
            if (wheelLeft != null) _wheelLeftHome = wheelLeft.localPosition;
            if (wheelRight != null) _wheelRightHome = wheelRight.localPosition;
            _homesCaptured = true;
        }

        /// <summary>Находит части по именам из FBX. Безопасно звать повторно.</summary>
        public void AutoBind()
        {
            propeller = Find("Propeller");
            wheelLeft = Find("Wheel_L");
            wheelRight = Find("Wheel_R");
            wheelTail = Find("Wheel_Tail");
            gearLegLeft = Find("GearLeg_L");
            gearLegRight = Find("GearLeg_R");
            aileronLeft = Find("Aileron_L");
            aileronRight = Find("Aileron_R");
            flapLeft = Find("Flap_L");
            flapRight = Find("Flap_R");
            elevatorLeft = Find("Elevator_L");
            elevatorRight = Find("Elevator_R");
            rudder = Find("Rudder");
            cargoDoorLeft = Find("CargoDoor_L");
            cargoDoorRight = Find("CargoDoor_R");
            cargoCrates = Find("Cargo_Crates");
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
            if (spinPropeller && propeller != null)
            {
                _propAngle += propellerRpm * 6f * Time.deltaTime;   // 360°/60с = 6°/с на об/мин
                propeller.localRotation = Quaternion.Euler(0f, 0f, _propAngle);
            }
            ApplyCargoDoors();
        }

        /// <summary>Катит колёса по пройденному за кадр пути (м/с вдоль оси).</summary>
        public void RollWheels(float metresPerSecond)
        {
            if (mainWheelRadius <= 0.0001f) return;
            _wheelAngle += metresPerSecond / mainWheelRadius * Mathf.Rad2Deg * Time.deltaTime;
            SetWheel(wheelLeft, _wheelAngle);
            SetWheel(wheelRight, _wheelAngle);
            // Хвостовое колесо крутится быстрее ровно во столько раз, во сколько
            // оно меньше: длина пути одна, а окружность разная.
            SetWheel(wheelTail, _wheelAngle * SafeRatio(mainWheelRadius, tailWheelRadius));
        }

        static float SafeRatio(float a, float b) => b > 0.0001f ? a / b : 1f;

        static void SetWheel(Transform t, float angle)
        {
            if (t != null) t.localRotation = Quaternion.Euler(angle, 0f, 0f);
        }

        /// <summary>Обжатие подвески, метры вверх. Двигает и стойку, и колесо:
        /// в плоской иерархии колесо стойке не подчинено.</summary>
        public void SetSuspension(float compressionMetres)
        {
            CaptureHomes();
            var d = Vector3.up * compressionMetres;
            if (gearLegLeft != null) gearLegLeft.localPosition = _gearLegLeftHome + d;
            if (gearLegRight != null) gearLegRight.localPosition = _gearLegRightHome + d;
            if (wheelLeft != null) wheelLeft.localPosition = _wheelLeftHome + d;
            if (wheelRight != null) wheelRight.localPosition = _wheelRightHome + d;
        }

        /// <summary>Крен: элероны отклоняются в противоположные стороны.</summary>
        public void SetRoll(float degrees)
        {
            SetHingeX(aileronLeft, -degrees);
            SetHingeX(aileronRight, degrees);
        }

        public void SetPitch(float degrees)
        {
            SetHingeX(elevatorLeft, degrees);
            SetHingeX(elevatorRight, degrees);
        }

        public void SetYaw(float degrees)
        {
            if (rudder != null) rudder.localRotation = Quaternion.Euler(0f, degrees, 0f);
        }

        public void SetFlaps(float degrees)
        {
            SetHingeX(flapLeft, degrees);
            SetHingeX(flapRight, degrees);
        }

        static void SetHingeX(Transform t, float degrees)
        {
            if (t != null) t.localRotation = Quaternion.Euler(degrees, 0f, 0f);
        }

        void ApplyCargoDoors()
        {
            var a = cargoDoorOpenAngle * Mathf.Clamp01(cargoDoorsOpen);
            // Створки распахиваются наружу и НАЗАД: петля на задней кромке
            // проёма, потому что проём стоит вплотную за крылом и створка с
            // передней навеской уходила бы под центроплан.
            if (cargoDoorLeft != null) cargoDoorLeft.localRotation = Quaternion.Euler(0f, a, 0f);
            if (cargoDoorRight != null) cargoDoorRight.localRotation = Quaternion.Euler(0f, -a, 0f);
        }

        /// <summary>Показать или убрать груз в отсеке.</summary>
        public void SetCargoVisible(bool visible)
        {
            if (cargoCrates != null) cargoCrates.gameObject.SetActive(visible);
        }
    }
}
