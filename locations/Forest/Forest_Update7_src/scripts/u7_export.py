"""Forest Update 7: the FBX of the fence and road-block kit (out/fences.blend), in Update 3's FBX convention - the same
exporter as Updates 4-6 (u4_export.py: FBX 7400, Y up, front +Z, UnitScaleFactor 100, the root at the origin without
rotation, normals written). Each model is one mesh object (the cut-outs, signs and plates joined in as extra material
slots with the names Forest_Materials.json gives).
python3 -I u7_export.py -- <out_dir>  ->  <out_dir>/*.fbx, u7_export_report.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import u4_export as E
MODELS = ['ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign', 'ConcreteFence_Plain',
          'ConcreteFence_Socket', 'ConcreteFence_Wicket', 'ChainFence', 'ChainFence_Torn', 'WireCoil', 'RoadBlock_FBS',
          'RoadBlock_Jersey', 'RoadBlock_Jersey_Striped', 'RoadBlock_Cube', 'TankTooth', 'TankTooth_b', 'Hedgehog',
          'WireBarricade', 'Abatis', 'Abatis_b', 'Sign_Halt', 'Sign_NoEntry']            # = fence_kit.MODELS

E.BATCHES = {'fences': ('fences.blend', MODELS)}
E.MAT_REMAP = {}

if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_dir = a[0]
    os.makedirs(out_dir, exist_ok=True)
    rep = E.export('fences', out_dir)
    jp = os.path.join(out_dir, 'u7_export_report.json')
    json.dump(rep, open(jp, 'w'), indent=1, ensure_ascii=False)
    print('[u7] exported', len(rep), 'models ->', jp)
