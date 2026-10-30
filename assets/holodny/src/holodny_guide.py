"""Holodny guide mannequin (29.10.2026): grey A-pose figure with the agreed proportions
(docs/gdd/monsters/01_holodny/QUESTIONS.md, answers 1-3): 2.2 m upright, fingertips at mid-shin.
Renders front / side (left) / back / side_right as image 1 for the Codex model sheets.

Run: blender.exe -b --factory-startup --python holodny_guide.py -- <out dir>
"""
import math
import os
import sys

import bpy

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "."
os.makedirs(OUT, exist_ok=True)

A_POSE = math.radians(20)  # arms out from vertical

# Joints (metres, Z up, the figure faces -Y; its left side is +X). Radii are (x, y) of the skin modifier.
SHOULDER = (0.23, 0.0, 1.76)
ARM = [0.0, 0.56, 1.10, 1.25]           # shoulder -> elbow -> wrist -> knuckles, along the arm
FINGER = 0.23                           # knuckles -> fingertips (fingertips at mid-shin, z ~0.37)


def arm_point(side, d):
    sx = SHOULDER[0] * side
    return (sx + side * d * math.sin(A_POSE), 0.0, SHOULDER[2] - d * math.cos(A_POSE))


def build():
    verts, edges, radii = [], [], []

    def v(p, r):
        verts.append(p)
        radii.append(r)
        return len(verts) - 1

    def chain(a, pts):
        prev = a
        for p, r in pts:
            i = v(p, r)
            edges.append((prev, i))
            prev = i
        return prev

    pelvis = v((0, 0.0, 1.10), (0.12, 0.08))
    # spine, neck, skull
    chest = chain(pelvis, [((0, 0.0, 1.30), (0.085, 0.065)),   # wasted waist
                           ((0, 0.0, 1.50), (0.14, 0.10)),     # ribs
                           ((0, 0.0, 1.70), (0.13, 0.085))])
    chain(chest, [((0, 0.0, 1.84), (0.035, 0.035)),            # long thin neck
                  ((0, 0.0, 1.92), (0.04, 0.04)),
                  ((0, -0.01, 1.98), (0.085, 0.10)),           # jaw / skull base
                  ((0, -0.01, 2.07), (0.095, 0.115)),
                  ((0, 0.0, 2.14), (0.08, 0.10)),
                  ((0, 0.0, 2.20), (0.03, 0.04))])
    for side in (1, -1):
        sh = chain(chest, [((SHOULDER[0] * side, 0.0, SHOULDER[2]), (0.045, 0.045))])
        wrist = chain(sh, [(arm_point(side, ARM[1] * 0.5), (0.032, 0.032)),
                           (arm_point(side, ARM[1]), (0.03, 0.03)),       # bony elbow
                           (arm_point(side, (ARM[1] + ARM[2]) / 2), (0.025, 0.025)),
                           (arm_point(side, ARM[2]), (0.02, 0.018))])
        # big flat palm facing the thigh; fingers fanned front-to-back, thumb in front
        knuckle = chain(wrist, [(arm_point(side, (ARM[2] + ARM[3]) / 2), (0.016, 0.045)),
                                (arm_point(side, ARM[3]), (0.014, 0.055))])
        kx, _, kz = arm_point(side, ARM[3])
        for f in range(4):
            fy = -0.045 + 0.03 * f
            ang = A_POSE + math.radians(4 * f - 6)
            tip = (kx + side * FINGER * math.sin(ang), fy * 1.5, kz - FINGER * math.cos(ang))
            mid = ((kx + tip[0]) / 2, fy * 1.25, (kz + tip[2]) / 2)
            chain(knuckle, [(mid, (0.012, 0.012)), (tip, (0.008, 0.008))])
        wx, _, wz = arm_point(side, ARM[2] + 0.03)
        chain(wrist, [((wx + side * 0.01, -0.06, wz - 0.06), (0.012, 0.012)),       # thumb
                      ((wx + side * 0.02, -0.10, wz - 0.13), (0.009, 0.009))])
        hip = chain(pelvis, [((0.10 * side, 0.0, 1.04), (0.07, 0.07))])
        ankle = chain(hip, [((0.12 * side, 0.0, 0.82), (0.05, 0.05)),
                            ((0.14 * side, 0.0, 0.58), (0.042, 0.045)),     # bony knee
                            ((0.15 * side, 0.01, 0.32), (0.03, 0.03)),
                            ((0.16 * side, 0.02, 0.07), (0.025, 0.025))])
        chain(ankle, [((0.165 * side, -0.08, 0.02), (0.04, 0.02)),
                      ((0.17 * side, -0.16, 0.015), (0.04, 0.012))])

    me = bpy.data.meshes.new("Guide")
    me.from_pydata(verts, edges, [])
    ob = bpy.data.objects.new("Guide", me)
    bpy.context.scene.collection.objects.link(ob)
    skin = ob.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    for i, r in enumerate(radii):
        me.skin_vertices[0].data[i].radius = r
    me.skin_vertices[0].data[pelvis].use_root = True
    sub = ob.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    return ob


def render(name, loc, rot):
    sc = bpy.context.scene
    cam = sc.camera
    cam.location = loc
    cam.rotation_euler = rot
    sc.render.filepath = os.path.join(OUT, f"guide_{name}.png")
    bpy.ops.render.render(write_still=True)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    build()
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = (0.42, 0.42, 0.42)
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.78, 0.78, 0.78)
    sc.render.resolution_x, sc.render.resolution_y = 1024, 1536
    sc.render.film_transparent = False
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "VERTICAL"
    cam_data.ortho_scale = 2.6
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    z = 1.12
    h = math.radians(90)
    render("front", (0, -6, z), (h, 0, 0))
    render("side", (6, 0, z), (h, 0, h))           # figure's left side
    render("back", (0, 6, z), (h, 0, math.pi))
    render("side_right", (-6, 0, z), (h, 0, -h))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Holodny_Guide.blend"))


main()
