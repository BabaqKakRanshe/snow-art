// Utility Plane v7: condensation / frost veil on the inner glass layers (Glass_Fog, *_Fog), URP only.
// T_GlassFog_Mask: R = clearing order (0 clears first, 1 last), G = density, B = 1 on the windshield (_Fog), 0 on the
// other panes (_FogSide). UtilityPlaneRig drives _Fog / _FogSide 0..1 from windshieldFog / sideWindowFog.
// Fully SRP Batcher compatible: every material property lives in UnityPerMaterial.
Shader "UtilityPlane/GlassFog"
{
    Properties
    {
        [NoScaleOffset] _FogMask ("Fog Mask (R order, G density, B windshield)", 2D) = "white" {}
        _FogColor ("Fog Colour", Color) = (0.86, 0.88, 0.90, 1)
        _Fog ("Windshield Fog", Range(0, 1)) = 0
        _FogSide ("Side Window Fog", Range(0, 1)) = 0
        _Edge ("Clearing Edge Softness", Range(0.01, 0.5)) = 0.12
        _MaxAlpha ("Max Alpha", Range(0, 1)) = 0.85
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent+1" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Pass
        {
            Name "Forward"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_FogMask);
            SAMPLER(sampler_FogMask);

            CBUFFER_START(UnityPerMaterial)
                half4 _FogColor;
                half _Fog;
                half _FogSide;
                half _Edge;
                half _MaxAlpha;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                half3 normalWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = v.uv;
                o.fogFactor = ComputeFogFactor(p.positionCS.z);
                return o;
            }

            half4 frag(Varyings i, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                half4 m = SAMPLE_TEXTURE2D(_FogMask, sampler_FogMask, i.uv);
                half level = lerp(_FogSide, _Fog, m.b);
                // level 1: everything fogged; level 0: clear. Low R clears first (threshold sweeps from 0 to 1 + edge).
                half thr = (1.0h + _Edge) * (1.0h - level);
                half cover = saturate((m.r - thr) / _Edge + 1.0h);
                cover *= step(0.001h, level);
                half alpha = cover * _MaxAlpha * lerp(0.55h, 1.0h, m.g);

                half3 n = normalize(i.normalWS) * IS_FRONT_VFACE(face, 1.0h, -1.0h);
                Light mainLight = GetMainLight();
                half wrap = abs(dot(n, mainLight.direction)) * 0.5h + 0.5h;   // scattering veil: lit from both sides
                half3 lit = SampleSH(n) + mainLight.color * (wrap * 0.35h);
                half3 col = _FogColor.rgb * lit;
                col = MixFog(col, i.fogFactor);
                return half4(col, alpha);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
