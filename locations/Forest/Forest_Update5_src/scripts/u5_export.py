"""Forest Update 5: one FBX per prefab from the base and far-point packages, in Update 3's FBX convention - the same
exporter as Update 4 (u4_export.py: FBX 7400, Y up, front +Z, UnitScaleFactor 100, the root at the origin without
rotation, children with translations only, normals written).

  base: Hatch (+ IX_HatchLid_94), Crates, LogPile, LightPole, PowerPole, FenceChain, OldFence, OldFence_b, OldFence_c,
        Helipad, RadioMast, Forest_Wires (the world model: its vertices are in the map frame, the root at the origin)
  far:  Dish_1..5 (+ IX_CabinetDoor_2..6), Radome, RelayMast, MeteoStation, LookoutTower, PumpHouse (+ IX_PumpDoor_7),
        Chapel (+ IX_ChapelDoor_8), Cabin (+ IX_CabinDoor_9), Campsite

The lenses, glass, signs and cut-outs are already joined into their objects as extra materials, the lens materials
already carry Update 3's names (M_Light_Red, M_Lamp_SodiumOff, M_Lamp_WarmOff, M_LEDOff, M_GlassDirty, M_Candle,
M_Headlight, M_Cable, M_Galvanized, M_Enamel): nothing to remap.

python3 -I u5_export.py -- <out_dir> [base] [far]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import u4_export as E

E.BATCHES = {
    'base': ('forest_base/base.blend', ['Hatch', 'Crates', 'LogPile', 'LightPole', 'PowerPole', 'FenceChain', 'OldFence',
                                        'OldFence_b', 'OldFence_c', 'Helipad', 'RadioMast', 'Forest_Wires']),
    'far': ('forest_far/far.blend', ['Dish_1', 'Dish_2', 'Dish_3', 'Dish_4', 'Dish_5', 'Radome', 'RelayMast', 'MeteoStation',
                                     'LookoutTower', 'PumpHouse', 'Chapel', 'Cabin', 'Campsite']),
}
E.MAT_REMAP = {}

if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out_dir = a[0]
    os.makedirs(out_dir, exist_ok=True)
    rep = {}
    for b in (a[1:] or list(E.BATCHES)):
        rep.update(E.export(b, out_dir))
    jp = os.path.join(out_dir, 'u5_export_report.json')
    old = json.load(open(jp)) if os.path.exists(jp) else {}
    old.update(rep)
    json.dump(old, open(jp, 'w'), indent=1, ensure_ascii=False)
    print('[u5] exported', len(rep), 'models ->', jp)
