"""Unreal Engine 5.6 editor script: import the Utility Plane package and build its materials.

Run inside the editor (Python Editor Script Plugin enabled):
    Tools -> Execute Python Script... -> pick this file
or in the Output Log console (Cmd = Python):
    py "D:/path/to/UtilityPlane_UE/ue_import_utility_plane.py"

The script expects this layout next to itself:
    SK_UtilityPlane.fbx, SK_UtilityPlane_Cockpit.fbx, Textures/*.png
It creates (DEST = /Game/Vehicles/UtilityPlane):
    Textures/   T_*_BC (sRGB), T_*_N (normal, DirectX), T_*_ORM (masks, linear), T_Gauges_BC, T_CargoNet_BCA
    Materials/  M_PlaneMaster, M_PlaneGlass, M_PlaneNet, M_PlaneLight, M_PlaneGauges + MI_* instances
    Meshes/     SK_UtilityPlane, SK_UtilityPlane_Cockpit (+ skeletons), material slots assigned
Re-running replaces the assets in place."""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = '/Game/Vehicles/UtilityPlane'
TEX_DIR, MAT_DIR, MESH_DIR = DEST + '/Textures', DEST + '/Materials', DEST + '/Meshes'
AT = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
log = unreal.log
warn = unreal.log_warning


def enum(cls_name, value):
    cls = getattr(unreal, cls_name, None)
    return getattr(cls, value, None) if cls else None


def try_set(obj, prop, value):
    if value is None:
        warn(f'[UtilityPlane] skipped {prop}: enum not available in this engine version')
        return False
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as e:  # property names differ slightly between engine versions
        warn(f'[UtilityPlane] could not set {prop} on {obj.get_name()}: {e}')
        return False


# ------------------------------------------------------------------ textures
TEXTURES = {  # file stem: (sRGB, compression)
    'T_Airframe_BC': (True, 'TC_DEFAULT'), 'T_Airframe_N': (False, 'TC_NORMALMAP'),
    'T_Airframe_ORM': (False, 'TC_MASKS'),
    'T_Details_BC': (True, 'TC_DEFAULT'), 'T_Details_N': (False, 'TC_NORMALMAP'),
    'T_Details_ORM': (False, 'TC_MASKS'),
    'T_Cockpit_BC': (True, 'TC_DEFAULT'), 'T_Cockpit_N': (False, 'TC_NORMALMAP'),
    'T_Cockpit_ORM': (False, 'TC_MASKS'),
    'T_Gauges_BC': (True, 'TC_DEFAULT'), 'T_CargoNet_BCA': (True, 'TC_DEFAULT'),
}


def import_files(files, dest):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f)
        t.set_editor_property('destination_path', dest)
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', False)
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    return tasks


import_files([os.path.join(HERE, 'Textures', k + '.png') for k in TEXTURES], TEX_DIR)
TEX = {}
for name, (srgb, comp) in TEXTURES.items():
    tex = unreal.load_asset(f'{TEX_DIR}/{name}')
    if not tex:
        warn(f'[UtilityPlane] texture missing: {name}')
        continue
    try_set(tex, 'srgb', srgb)
    try_set(tex, 'compression_settings', enum('TextureCompressionSettings', comp))
    if comp == 'TC_NORMALMAP':
        try_set(tex, 'flip_green_channel', False)          # already DirectX (G flipped at export)
    try_set(tex, 'lod_group', enum('TextureGroup', 'TEXTUREGROUP_VEHICLE_NORMAL_MAP' if comp == 'TC_NORMALMAP'
                                   else 'TEXTUREGROUP_VEHICLE'))
    EAL.save_loaded_asset(tex)
    TEX[name] = tex
log(f'[UtilityPlane] textures: {len(TEX)}')


# ------------------------------------------------------------------ materials
def new_material(name):
    path = f'{MAT_DIR}/{name}'
    if EAL.does_asset_exist(path):                 # re-run: keep the asset (instances reference it), rebuild graph
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    return AT.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())


def tex_param(mat, name, tex, sampler, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('texture', tex)
    e.set_editor_property('sampler_type', sampler)
    return e


def scalar(mat, name, val, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', val)
    return e


def vector(mat, name, col, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', unreal.LinearColor(*col))
    return e


def mul(mat, a, a_out, b, b_out, x, y):
    e = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, x, y)
    MEL.connect_material_expressions(a, a_out, e, 'A')
    MEL.connect_material_expressions(b, b_out, e, 'B')
    return e


P = unreal.MaterialProperty
ST = unreal.MaterialSamplerType

# opaque PBR master: BaseColor x Tint, ORM (R AO, G roughness x RoughnessMult, B metallic), DirectX normal
m = new_material('M_PlaneMaster')
bc = tex_param(m, 'BaseColor', TEX.get('T_Airframe_BC'), ST.SAMPLERTYPE_COLOR, -900, -300)
orm = tex_param(m, 'ORM', TEX.get('T_Airframe_ORM'), ST.SAMPLERTYPE_MASKS, -900, 0)
nrm = tex_param(m, 'Normal', TEX.get('T_Airframe_N'), ST.SAMPLERTYPE_NORMAL, -900, 300)
tint = vector(m, 'Tint', (1, 1, 1, 1), -600, -420)
rmul = scalar(m, 'RoughnessMult', 1.0, -600, 120)
MEL.connect_material_property(mul(m, bc, 'RGB', tint, '', -350, -300), '', P.MP_BASE_COLOR)
MEL.connect_material_property(orm, 'R', P.MP_AMBIENT_OCCLUSION)
MEL.connect_material_property(mul(m, orm, 'G', rmul, '', -350, 60), '', P.MP_ROUGHNESS)
MEL.connect_material_property(orm, 'B', P.MP_METALLIC)
MEL.connect_material_property(nrm, 'RGB', P.MP_NORMAL)
MEL.recompile_material(m)
M_MASTER = m

# glass: translucent, lit with surface forward shading so it gets reflections
m = new_material('M_PlaneGlass')
try_set(m, 'blend_mode', enum('BlendMode', 'BLEND_TRANSLUCENT'))
try_set(m, 'two_sided', True)
for tlm in ('TLM_SURFACE_PER_PIXEL_LIGHTING', 'TLM_SURFACE_FORWARD_SHADING', 'TLM_SURFACE'):   # 'Surface ForwardShading'
    if hasattr(unreal.TranslucencyLightingMode, tlm):
        try_set(m, 'translucency_lighting_mode', getattr(unreal.TranslucencyLightingMode, tlm))
        break
MEL.connect_material_property(vector(m, 'Tint', (0.02, 0.025, 0.025, 1), -500, -200), '', P.MP_BASE_COLOR)
MEL.connect_material_property(scalar(m, 'Opacity', 0.12, -500, 0), '', P.MP_OPACITY)
MEL.connect_material_property(scalar(m, 'Roughness', 0.04, -500, 100), '', P.MP_ROUGHNESS)
MEL.connect_material_property(scalar(m, 'Specular', 0.6, -500, 200), '', P.MP_SPECULAR)
MEL.recompile_material(m)
M_GLASS = m

# cargo net: masked, two-sided, tiling webbing texture (RGB + alpha)
m = new_material('M_PlaneNet')
try_set(m, 'blend_mode', enum('BlendMode', 'BLEND_MASKED'))
try_set(m, 'two_sided', True)
t = tex_param(m, 'BCA', TEX.get('T_CargoNet_BCA'), ST.SAMPLERTYPE_COLOR, -600, 0)
MEL.connect_material_property(t, 'RGB', P.MP_BASE_COLOR)
MEL.connect_material_property(t, 'A', P.MP_OPACITY_MASK)
MEL.connect_material_property(scalar(m, 'Roughness', 0.85, -600, 250), '', P.MP_ROUGHNESS)
MEL.recompile_material(m)
M_NET = m

# light lenses: emissive = Color x Intensity (drive Intensity from BP for strobes / beacon)
m = new_material('M_PlaneLight')
c = vector(m, 'Color', (1, 1, 1, 1), -700, 0)
i = scalar(m, 'Intensity', 20.0, -700, 200)
MEL.connect_material_property(mul(m, c, '', scalar(m, 'LensTint', 0.25, -700, -150), '', -400, -100), '',
                              P.MP_BASE_COLOR)
MEL.connect_material_property(mul(m, c, '', i, '', -400, 100), '', P.MP_EMISSIVE_COLOR)
MEL.connect_material_property(scalar(m, 'Roughness', 0.1, -700, 350), '', P.MP_ROUGHNESS)
MEL.recompile_material(m)
M_LIGHT = m

# gauge faces: printed dials, optional backlight (Backlight 0..1, drive from the panel rheostat)
m = new_material('M_PlaneGauges')
t = tex_param(m, 'Faces', TEX.get('T_Gauges_BC'), ST.SAMPLERTYPE_COLOR, -800, 0)
MEL.connect_material_property(t, 'RGB', P.MP_BASE_COLOR)
bl = mul(m, t, 'RGB', vector(m, 'BacklightColor', (1.0, 0.55, 0.25, 1), -800, 250), '', -500, 200)
MEL.connect_material_property(mul(m, bl, '', scalar(m, 'Backlight', 0.0, -500, 350), '', -250, 250), '',
                              P.MP_EMISSIVE_COLOR)
MEL.connect_material_property(scalar(m, 'Roughness', 0.55, -800, 450), '', P.MP_ROUGHNESS)
MEL.recompile_material(m)
M_GAUGES = m


def instance(name, parent, textures=None, scalars=None, vectors=None):
    path = f'{MAT_DIR}/{name}'
    if EAL.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = AT.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant,
                             unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (textures or {}).items():
        if v:
            MEL.set_material_instance_texture_parameter_value(mi, k, v)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
    EAL.save_loaded_asset(mi)
    return mi


MI = {}
for atl in ('Airframe', 'Details', 'Cockpit'):
    MI['M_' + atl] = instance('MI_' + atl, M_MASTER, {'BaseColor': TEX.get(f'T_{atl}_BC'),
                                                      'ORM': TEX.get(f'T_{atl}_ORM'),
                                                      'Normal': TEX.get(f'T_{atl}_N')})
MI['M_Glass'] = instance('MI_Glass', M_GLASS, scalars={'Opacity': 0.12})
MI['M_GaugeGlass'] = instance('MI_GaugeGlass', M_GLASS, scalars={'Opacity': 0.05, 'Roughness': 0.02},
                              vectors={'Tint': (0.0, 0.0, 0.0, 1)})
MI['M_CargoNet'] = instance('MI_CargoNet', M_NET)
MI['M_Gauges'] = instance('MI_Gauges', M_GAUGES)
LIGHTS = {'M_Light_Red': ((1.0, 0.02, 0.01, 1), 20), 'M_Light_Green': ((0.02, 1.0, 0.15, 1), 20),
          'M_Light_White': ((1.0, 1.0, 0.95, 1), 15), 'M_Light_Beacon': ((1.0, 0.08, 0.01, 1), 15),
          'M_Light_Landing': ((1.0, 0.97, 0.9, 1), 5)}
for ln, (col, inten) in LIGHTS.items():
    MI[ln] = instance(ln.replace('M_', 'MI_'), M_LIGHT, scalars={'Intensity': inten}, vectors={'Color': col})
for mat in (M_MASTER, M_GLASS, M_NET, M_LIGHT, M_GAUGES):
    EAL.save_loaded_asset(mat)
log(f'[UtilityPlane] material instances: {sorted(MI)}')


# ------------------------------------------------------------------ skeletal meshes
def fbx_options():
    ui = unreal.FbxImportUI()
    try_set(ui, 'import_mesh', True)
    try_set(ui, 'import_as_skeletal', True)
    try_set(ui, 'mesh_type_to_import', enum('FBXImportType', 'FBXIT_SKELETAL_MESH'))
    try_set(ui, 'import_materials', False)
    try_set(ui, 'import_textures', False)
    try_set(ui, 'import_animations', False)
    try_set(ui, 'create_physics_asset', False)
    sk = ui.get_editor_property('skeletal_mesh_import_data')
    try_set(sk, 'convert_scene', True)
    try_set(sk, 'force_front_x_axis', False)          # the nose is already +X
    try_set(sk, 'convert_scene_unit', True)
    try_set(sk, 'import_uniform_scale', 1.0)
    try_set(sk, 'normal_import_method', enum('FBXNormalImportMethod', 'FBXNIM_IMPORT_NORMALS'))
    try_set(sk, 'normal_generation_method', enum('FBXNormalGenerationMethod', 'MIKK_T_SPACE'))
    try_set(sk, 'import_morph_targets', False)
    try_set(sk, 'use_t0_as_ref_pose', False)
    try_set(sk, 'preserve_smoothing_groups', True)
    return ui


def import_sk(fbx):
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', os.path.join(HERE, fbx))
    t.set_editor_property('destination_path', MESH_DIR)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    t.set_editor_property('options', fbx_options())
    AT.import_asset_tasks([t])
    name = os.path.splitext(fbx)[0]
    sk = unreal.load_asset(f'{MESH_DIR}/{name}')
    if not sk:
        warn(f'[UtilityPlane] import failed: {fbx}')
        return None
    mats = sk.get_editor_property('materials')
    out = []
    for sm in mats:
        slot = str(sm.get_editor_property('material_slot_name'))
        key = slot if slot in MI else next((k for k in MI if slot.startswith(k + '_')), None)
        if key:
            sm.set_editor_property('material_interface', MI[key])
        else:
            warn(f'[UtilityPlane] {name}: no instance for slot {slot}')
        out.append(sm)
    sk.set_editor_property('materials', out)
    EAL.save_loaded_asset(sk)
    log(f'[UtilityPlane] {name}: {len(out)} material slots assigned')
    return sk


import_sk('SK_UtilityPlane.fbx')
import_sk('SK_UtilityPlane_Cockpit.fbx')
EAL.save_directory(DEST, only_if_is_dirty=True, recursive=True)
log('[UtilityPlane] done: ' + DEST)
