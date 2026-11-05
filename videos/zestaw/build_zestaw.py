"""RIVON "Zestaw pergoli" v2 — shot-for-shot remake of the MBD reference (IMG_9038 from 1.0 s), 37.5 s @ 30 fps, 9:16.
Same camera angles, moves and timing; only RIVON parts (exact STEP meshes, layout.json validated: 0 collisions).
Story: kit drops onto the white floor next to the paver pad -> Stopa onto anchor studs of a concrete footing, nuts ->
post tumbles in from the sky into the Stopa, side screws -> top frame: Trojak 3D slide onto the beam ends above the posts,
right unit joins, frame is lowered onto the posts (Trojak sockets are closed tubes, so this is the only honest order) ->
Mocowanie belek 2 on the inner beam faces -> rafters -> roof roll unrolls -> wide shot with roof variants -> end card.
Every metal part moves rigidly only; nothing is scaled or edited.
Usage: python3 build_zestaw.py --frames 0,100,... --out DIR --w 540 --h 960 --spp 32
"""
import sys, math, argparse
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rivon_film"))
import bpy, mathutils
from mathutils import Matrix, Vector, Quaternion
import film_lib as FL

FPS, NF = 30, 1125
END_SRC = 990                       # end card (f >= 1005) re-uses this render, dimmed + blurred in post
LIFT, JOIN = 0.25, 0.8
ROOF_Z = 2.598
ROOF_X, ROOF_Y = 1.86, 3.16
PAD_TOP, FLOOR_Z = -0.10, -0.25
POSTS = {1: (-1.70, -2.95), 2: (1.70, -2.95), 3: (1.70, 2.95), 4: (-1.70, 2.95)}


def clamp01(x): return max(0.0, min(1.0, x))
def e_io(u): u = clamp01(u); return u * u * (3 - 2 * u)
def e_seat(u): u = clamp01(u); return 1 - (1 - u) ** 2.4
def e_out(u): u = clamp01(u); return 1 - (1 - u) ** 3


# ------------------------------------------------------------------------------------------------ shots (camera keys)
# name, f0, f1, [(u, loc, target, lens, fstop|None)]   u in 0..1 inside the shot
SHOTS = [
    ("s01_kit_drop", 0, 66, [(0, (6.6, -5.6, 4.6), (3.7, -0.9, -0.25), 30, None), (1, (5.6, -4.6, 2.6), (3.7, -1.2, -0.25), 30, None)]),
    ("s03_bases_low", 66, 90, [(0, (3.62, -3.95, -0.16), (3.10, -2.85, -0.17), 30, 2.8), (1, (3.50, -4.15, -0.14), (3.10, -2.65, -0.17), 28, 2.8)]),
    ("s03b_kit_wide", 90, 98, [(0, (2.0, -5.6, 1.2), (3.6, -1.8, -0.2), 26, None), (1, (1.8, -5.2, 0.9), (3.4, -1.8, -0.2), 26, None)]),
    ("s04_skim", 98, 132, [(0, (0.9, 0.2, -0.02), (-1.70, -2.95, -0.05), 26, None), (1, (-1.12, -2.28, 0.34), (-1.70, -2.95, 0.02), 30, 5.6)]),
    ("s05_stopa_nuts", 132, 172, [(0, (-1.10, -2.24, 0.36), (-1.70, -2.95, 0.06), 34, 4.0), (1, (-1.02, -2.40, 0.33), (-1.70, -2.95, 0.07), 34, 4.0)]),
    ("s06_post_falls", 172, 206, [(0, (-1.02, -2.40, 0.33), (-1.70, -2.95, 0.12), 34, 4.0), (1, (-1.00, -2.46, 0.30), (-1.70, -2.95, 0.30), 32, 4.0)]),
    ("s07_macro", 206, 244, [(0, (-1.36, -2.60, 0.10), (-1.70, -2.95, 0.10), 40, 2.8), (1, (-1.30, -2.67, 0.14), (-1.70, -2.95, 0.12), 40, 2.8)]),
    ("s08_wide_low", 244, 258, [(0, (-0.9, -4.9, 0.25), (0.4, 0.0, 1.4), 22, None), (1, (-0.7, -4.7, 0.35), (0.4, 0.0, 1.6), 22, None)]),
    ("s09_up_post", 258, 288, [(0, (-1.46, -2.68, 1.85), (-1.70, -2.95, 3.10), 18, None), (1, (-1.48, -2.71, 1.95), (-1.70, -2.95, 3.10), 18, None)]),
    ("s10_corner_orbit", 288, 326, [(0, (-1.20, -3.80, 2.98), (-1.70, -2.95, 2.45), 24, None), (1, (-0.98, -3.78, 2.95), (-1.70, -2.95, 2.45), 24, None)]),
    ("s11_macro_arm", 326, 348, [(0, (-1.12, -3.22, 2.86), (-1.62, -2.95, 2.78), 35, 2.0), (1, (-1.10, -3.16, 2.89), (-1.62, -2.95, 2.78), 35, 2.0)]),
    ("s12_beam_in", 348, 394, [(0, (-0.85, -3.95, 2.98), (-1.65, -2.95, 2.50), 24, None), (1, (-0.95, -4.00, 3.02), (-1.65, -2.95, 2.50), 24, None)]),
    ("s13_corner_close", 394, 432, [(0, (-1.10, -3.62, 2.30), (-1.70, -2.95, 2.75), 30, 3.5), (1, (-1.16, -3.56, 2.42), (-1.70, -2.95, 2.62), 30, 3.5)]),
    ("s15_top_mocow", 432, 560, [(0, (-0.35, -2.75, 4.75), (-1.62, -0.6, 2.55), 30, None), (1, (0.05, -2.35, 4.85), (-1.62, 0.3, 2.55), 30, None)]),
    ("s16_up_inside", 560, 618, [(0, (0.6, -2.1, 0.35), (-0.7, 0.8, 2.9), 18, None), (1, (0.45, -1.6, 0.50), (-0.7, 1.2, 2.9), 18, None)]),
    ("s17_hanger_close", 618, 642, [(0, (-0.95, -3.15, 3.25), (-1.65, -2.42, 2.56), 30, 4.0), (1, (-0.98, -3.05, 3.22), (-1.65, -2.40, 2.56), 30, 4.0)]),
    ("s18_first_rafter", 642, 680, [(0, (-0.45, -4.45, 3.55), (-0.70, -2.30, 2.60), 24, None), (1, (-0.25, -4.25, 3.45), (-0.70, -2.10, 2.60), 24, None)]),
    ("s19_rafters", 680, 746, [(0, (-2.10, -3.55, 2.98), (-0.6, -0.5, 2.45), 24, None), (1, (-1.98, -3.30, 2.95), (-0.6, -0.2, 2.45), 24, None)]),
    ("s20_roll", 746, 810, [(0, (-2.80, -2.75, 3.12), (-1.2, -2.45, 2.72), 24, None), (1, (-2.75, -2.45, 3.10), (-1.2, -2.05, 2.72), 24, None)]),
    ("s22_high_corner", 810, 845, [(0, (-3.3, -5.1, 4.7), (0.0, -0.6, 1.5), 22, None), (1, (-3.6, -5.6, 5.0), (0.0, -0.4, 1.4), 22, None)]),
    ("s23_variants", 845, 1005, [(0, (5.6, -7.4, 5.6), (0.0, 0.0, 1.2), 30, None), (1, (5.0, -6.9, 5.1), (0.0, 0.0, 1.2), 30, None)]),
    ("s24_end", 1005, 1125, [(0, (5.0, -6.9, 5.1), (0.0, 0.0, 1.2), 30, None), (1, (5.0, -6.9, 5.1), (0.0, 0.0, 1.2), 30, None)]),
]
ROOF_TL = [(745, 845, "poly_roll"), (845, 880, "poly"), (880, 915, "blacha"), (915, 950, "lamele"), (950, 1125, "plotno")]


def shot_of(f):
    for n, a, b, keys in SHOTS:
        if a <= f < b:
            return n, (f - a) / (b - a), keys
    n, a, b, keys = SHOTS[-1]; return n, 1.0, keys


def place_camera(cam, keys, u):
    k = e_io(u) * 0.7 + u * 0.3
    (_, l0, t0, z0, s0), (_, l1, t1, z1, s1) = keys[0], keys[-1]
    loc = Vector(l0).lerp(Vector(l1), k); tgt = Vector(t0).lerp(Vector(t1), k)
    cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = z0 + (z1 - z0) * k
    cam.data.dof.use_dof = s0 is not None
    if s0:
        cam.data.dof.aperture_fstop = s0; cam.data.dof.focus_distance = (tgt - loc).length


# ------------------------------------------------------------------------------------------------ materials
def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        n.inputs[k].default_value = v
    return n


def setup_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; N.clear(); L = nt.links.new
    out = N.new("ShaderNodeOutputWorld"); bg = N.new("ShaderNodeBackground")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.80, 0.86, 0.95, 1); e[1].position = 0.5; e[1].color = (0.10, 0.27, 0.66, 1)
    m = ramp.color_ramp.elements.new(0.10); m.color = (0.55, 0.68, 0.88, 1)
    L(sep.outputs["Z"], ramp.inputs[0])
    # cumulus: direction projected onto a cloud deck (x/z, y/z), two noise layers, shaded underside
    dv = N.new("ShaderNodeVectorMath"); dv.operation = "DIVIDE"
    zc = N.new("ShaderNodeMath"); zc.operation = "MAXIMUM"; zc.inputs[1].default_value = 0.06
    L(sep.outputs["Z"], zc.inputs[0])
    cz = N.new("ShaderNodeCombineXYZ"); L(zc.outputs[0], cz.inputs[0]); L(zc.outputs[0], cz.inputs[1]); L(zc.outputs[0], cz.inputs[2])
    L(tc.outputs["Generated"], dv.inputs[0]); L(cz.outputs[0], dv.inputs[1])
    n1 = node(nt, "ShaderNodeTexNoise", Scale=0.55, Detail=12.0, Roughness=0.58); L(dv.outputs[0], n1.inputs["Vector"])
    off = N.new("ShaderNodeVectorMath"); off.operation = "ADD"; off.inputs[1].default_value = (0.05, 0.08, 0.0)
    L(dv.outputs[0], off.inputs[0])
    n2 = node(nt, "ShaderNodeTexNoise", Scale=0.55, Detail=12.0, Roughness=0.58); L(off.outputs[0], n2.inputs["Vector"])
    cov = N.new("ShaderNodeValToRGB"); cov.color_ramp.elements[0].position = 0.50; cov.color_ramp.elements[1].position = 0.64
    L(n1.outputs["Fac"], cov.inputs[0])
    sh = N.new("ShaderNodeValToRGB"); sh.color_ramp.elements[0].position = 0.48; sh.color_ramp.elements[1].position = 0.70
    sh.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1); sh.color_ramp.elements[1].color = (0.52, 0.57, 0.66, 1)
    L(n2.outputs["Fac"], sh.inputs[0])
    hz = node(nt, "ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 0.0; hz.inputs["From Max"].default_value = 0.16
    L(sep.outputs["Z"], hz.inputs["Value"])
    mm = N.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; L(cov.outputs["Color"], mm.inputs[0]); L(hz.outputs["Result"], mm.inputs[1])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    L(mm.outputs[0], mix.inputs[0]); L(ramp.outputs["Color"], mix.inputs[6]); L(sh.outputs["Color"], mix.inputs[7])
    L(mix.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.0
    L(bg.outputs[0], out.inputs[0])
    sd = bpy.data.lights.new("sun", "SUN"); sd.energy = 5.5; sd.angle = math.radians(1.5); sd.color = (1.0, 0.95, 0.86)
    so = bpy.data.objects.new("sun", sd); so.rotation_euler = (math.radians(48), 0, math.radians(-30))
    sc.collection.objects.link(so)


def mat_floor():
    m = FL.simple("studio_white", (0.80, 0.80, 0.81, 1), rough=0.7, spec=0.25)
    nt = m.node_tree; N = nt.nodes; L = nt.links.new; b = N["Principled BSDF"]; out = N["Material Output"]
    tc = N.new("ShaderNodeTexCoord")
    nz = node(nt, "ShaderNodeTexNoise", Scale=0.35, Detail=10.0, Roughness=0.6); L(tc.outputs["Object"], nz.inputs["Vector"])
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (0.76, 0.75, 0.74, 1); rp.color_ramp.elements[1].color = (0.86, 0.86, 0.86, 1)
    L(nz.outputs["Fac"], rp.inputs[0]); L(rp.outputs["Color"], b.inputs["Base Color"])
    cd = N.new("ShaderNodeCameraData"); mr = node(nt, "ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 20.0; mr.inputs["From Max"].default_value = 110.0
    L(cd.outputs["View Distance"], mr.inputs["Value"])
    em = node(nt, "ShaderNodeEmission", Strength=1.0); em.inputs["Color"].default_value = (0.80, 0.86, 0.95, 1)
    lp = N.new("ShaderNodeLightPath"); mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
    L(mr.outputs["Result"], mx.inputs[0]); L(lp.outputs["Is Camera Ray"], mx.inputs[1])
    ms = N.new("ShaderNodeMixShader"); L(mx.outputs[0], ms.inputs[0]); L(b.outputs[0], ms.inputs[1]); L(em.outputs[0], ms.inputs[2])
    L(ms.outputs[0], out.inputs["Surface"])
    return m


def mat_pavers():
    """Warm taupe concrete pavers ~30 cm, staggered, chamfered joints, per-slab tone + dirt."""
    m = bpy.data.materials.new("kostka_brukowa"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links.new; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    br = node(nt, "ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.006, "Mortar Smooth": 0.5, "Bias": 0.0,
                                                      "Brick Width": 0.30, "Row Height": 0.30})
    br.inputs["Color1"].default_value = (0.25, 0.20, 0.16, 1); br.inputs["Color2"].default_value = (0.42, 0.35, 0.29, 1)
    br.inputs["Mortar"].default_value = (0.10, 0.085, 0.07, 1); br.offset = 0.5
    L(tc.outputs["Object"], br.inputs["Vector"])
    nz = node(nt, "ShaderNodeTexNoise", Scale=40.0, Detail=10.0); L(tc.outputs["Object"], nz.inputs["Vector"])
    big = node(nt, "ShaderNodeTexNoise", Scale=1.3, Detail=4.0); L(tc.outputs["Object"], big.inputs["Vector"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "OVERLAY"; mx.inputs[0].default_value = 0.45
    L(br.outputs["Color"], mx.inputs[6]); L(nz.outputs["Color"], mx.inputs[7])
    mx2 = N.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.blend_type = "MULTIPLY"; mx2.inputs[0].default_value = 0.35
    L(mx.outputs[2], mx2.inputs[6]); L(big.outputs["Color"], mx2.inputs[7])
    L(mx2.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.82
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; L(br.outputs["Fac"], inv.inputs[1])
    sc = N.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 0.1; L(nz.outputs["Fac"], sc.inputs[0])
    add = N.new("ShaderNodeMath"); add.operation = "ADD"; L(inv.outputs[0], add.inputs[0]); L(sc.outputs[0], add.inputs[1])
    bump = node(nt, "ShaderNodeBump", Strength=0.8, Distance=0.004); L(add.outputs[0], bump.inputs["Height"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_footing():
    """Exposed-aggregate concrete (granite chips), like the reference footing."""
    m = bpy.data.materials.new("beton_plukany"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links.new; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    vo = node(nt, "ShaderNodeTexVoronoi", Scale=260.0); L(tc.outputs["Object"], vo.inputs["Vector"])
    rp = N.new("ShaderNodeValToRGB"); E = rp.color_ramp.elements
    E[0].position = 0.0; E[0].color = (0.14, 0.11, 0.09, 1); E[1].position = 1.0; E[1].color = (0.58, 0.52, 0.46, 1)
    for p, c in ((0.3, (0.36, 0.27, 0.21, 1)), (0.55, (0.44, 0.40, 0.36, 1)), (0.8, (0.27, 0.24, 0.22, 1))):
        x = rp.color_ramp.elements.new(p); x.color = c
    rp.color_ramp.interpolation = "CONSTANT"
    L(vo.outputs["Color"], rp.inputs[0]); L(rp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    bump = node(nt, "ShaderNodeBump", Strength=0.9, Distance=0.003); L(vo.outputs["Distance"], bump.inputs["Height"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_steel():
    """RAL 9005 powder coat, satin with a clear-ish sheen that picks up the sky like the reference."""
    m = bpy.data.materials["RIVON_black_powder_coat"]; nt = m.node_tree; N = nt.nodes; L = nt.links.new
    b = N["Principled BSDF"]; bump = [n for n in N if n.type == "BUMP"][0]
    b.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1)
    for n in N:
        if n.type == "MAP_RANGE":
            n.inputs["To Min"].default_value = 0.26; n.inputs["To Max"].default_value = 0.36
    b.inputs["Coat Weight"].default_value = 0.6; b.inputs["Coat Roughness"].default_value = 0.12
    bv = N.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.0015; bv.samples = 8
    L(bv.outputs["Normal"], bump.inputs["Normal"])


def mat_wood():
    """Oiled larch / cedar tone like the reference: saturated orange-brown, clear grain, slight oil sheen."""
    pine = bpy.data.materials["pine_planed"]; nt = pine.node_tree; N = nt.nodes; L = nt.links.new; b = N["Principled BSDF"]
    for n in N:
        if n.type == "VALTORGB" and len(n.color_ramp.elements) == 2 and abs(n.color_ramp.elements[0].position - 0.25) < 1e-3:
            n.color_ramp.elements[0].color = (0.46, 0.17, 0.055, 1); n.color_ramp.elements[1].color = (0.22, 0.07, 0.02, 1)
        if n.type == "MIX" and n.data_type == "RGBA":
            c = tuple(n.inputs[7].default_value)
            if c[0] > 0.3:   n.inputs[7].default_value = (0.50, 0.20, 0.07, 1)
            elif c[0] > 0.1: n.inputs[7].default_value = (0.28, 0.09, 0.025, 1)
    bump = [n for n in N if n.type == "BUMP"][0]; bump.inputs["Strength"].default_value = 0.4
    bv = N.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.002; bv.samples = 8; L(bv.outputs["Normal"], bump.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.42; b.inputs["Coat Weight"].default_value = 0.18; b.inputs["Coat Roughness"].default_value = 0.3
    b.inputs["Subsurface Weight"].default_value = 0.05; b.inputs["Subsurface Radius"].default_value = (0.02, 0.008, 0.004)


# ------------------------------------------------------------------------------------------------ studio, footings, anchors
def setup_studio():
    coll = FL.collection("STUDIO")
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=400, fill_type="NGON", location=(0, 0, FLOOR_Z))
    fl = bpy.context.active_object; fl.name = "floor"; fl.data.materials.append(mat_floor()); FL.link(fl, coll)
    pad = FL.box("PAD", (4.7, 7.5, PAD_TOP - FLOOR_Z), (0, 0, (PAD_TOP + FLOOR_Z) / 2), mat_pavers(), coll, bevel=0.008)
    fm = mat_footing(); zinc = FL.simple("anchor_zinc", (0.55, 0.56, 0.58, 1), rough=0.3, metal=1.0)
    for k, (x, y) in POSTS.items():
        FL.box(f"FOOTING_{k}", (0.46, 0.46, -FLOOR_Z), (x, y, FLOOR_Z / 2), fm, coll, bevel=0.012)
    return pad, zinc


def hex_prism(name, r_flat, h, mat, hole=0.0):
    r = r_flat / math.cos(math.pi / 6); v, f = [], []
    for z in (0.0, h):
        v += [(r * math.cos(math.pi / 3 * i + math.pi / 6), r * math.sin(math.pi / 3 * i + math.pi / 6), z) for i in range(6)]
    for i in range(6):
        j = (i + 1) % 6; f.append((i, j, 6 + j, 6 + i))
    f.append(tuple(range(5, -1, -1))); f.append(tuple(range(6, 12)))
    me = FL.mesh_from_arrays(name, np.array(v), f); me.materials.append(mat)
    return me


def build_anchors(items, L, zinc):
    """Threaded studs embedded in each footing through the real O10 anchor holes of the Stopa plate; washer + nut each."""
    coll = FL.collection("ANCHORS")
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.004, radius2=0.004, depth=0.045)
    sme = bpy.data.meshes.new("STUD"); bm.to_mesh(sme); bm.free(); sme.materials.append(zinc)
    for p in sme.polygons: p.use_smooth = True
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.008, radius2=0.008, depth=0.0016)
    wme = bpy.data.meshes.new("WASHER"); bm.to_mesh(wme); bm.free(); wme.materials.append(zinc)
    nme = hex_prism("NUT", 0.0065, 0.0065, zinc)
    for i, fz in enumerate(L["fasteners"]):
        if fz["kind"] != "anchor":
            continue
        sc = bpy.data.objects[f"SCREW_{i:03d}"]; sc.hide_render = sc.hide_viewport = True
        items.pop(f"SCREW_{i:03d}", None)
        x, y, _ = np.array(fz["pos_mm"]) * 0.001
        st = bpy.data.objects.new(f"STUD_{i:03d}", sme); st.location = (x, y, 0.0275 - 0.045 / 2 + 0.0)  # top at +27.5 mm
        coll.objects.link(st)
        for kind, me, z in (("WASH", wme, 0.0028), ("NUT", nme, 0.0036)):
            ob = bpy.data.objects.new(f"{kind}_{i:03d}", me); ob.location = (x, y, z); coll.objects.link(ob)
            it = Item(ob, [ob], ob.matrix_world.copy()); it.part = fz["part"]; it.spin = kind == "NUT"; it.anchor = kind
            items[f"{kind}_{i:03d}"] = it


# ------------------------------------------------------------------------------------------------ roofs
def _sheet_mesh(name, profile, length):
    verts, faces, n = [], [], len(profile)
    for y in (0.0, length):
        verts += [(x, y, z) for x, z in profile]
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    return FL.mesh_from_arrays(name, np.array(verts), faces, smooth=True)


def build_roofs():
    coll = FL.collection("ROOFS"); R = {}
    poly = bpy.data.materials.new("poliweglan_grafit"); poly.use_nodes = True
    b = poly.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.055, 0.06, 1); b.inputs["Roughness"].default_value = 0.22
    b.inputs["Metallic"].default_value = 0.2; b.inputs["Coat Weight"].default_value = 0.5
    xs = np.linspace(-ROOF_X, ROOF_X, 700)
    prof = [(x, 0.012 * math.sin(2 * math.pi * (x + ROOF_X) / 0.076)) for x in xs]
    me = _sheet_mesh("POLY", prof, 1.0); me.materials.append(poly)
    ob = bpy.data.objects.new("ROOF_POLY", me); FL.link(ob, coll); ob.modifiers.new("t", "SOLIDIFY").thickness = 0.0012
    R["poly"] = ob
    # roll: spiral of the same corrugated sheet (reads as a rolled sheet end-on, like the reference)
    turns, r0, gap = 7, 0.07, 0.038
    vs, fs = [], []; nseg = 360
    for k, xx in enumerate((-ROOF_X, ROOF_X)):
        for s in range(turns * nseg):
            a = 2 * math.pi * s / nseg; r = r0 + gap * a / (2 * math.pi) + 0.008 * math.sin(a * 40)
            vs.append((xx, r * math.cos(a), r * math.sin(a)))
    n = turns * nseg
    for s in range(n - 1):
        fs.append((s, s + 1, n + s + 1, n + s))
    rme = FL.mesh_from_arrays("ROLL", np.array(vs), fs, smooth=True); rme.materials.append(poly)
    roll = bpy.data.objects.new("ROOF_ROLL", rme); FL.link(roll, coll); roll.modifiers.new("t", "SOLIDIFY").thickness = 0.0015
    R["roll"] = roll; R["roll_rmax"] = r0 + gap * turns
    bl = FL.simple("blacha_grafit", (0.03, 0.033, 0.037, 1), rough=0.34, metal=0.6, spec=0.5)
    w = 2 * ROOF_X / 4; per = w / 5; prof = []
    for k in range(5):
        x0 = -w / 2 + k * per
        prof += [(x0, 0.0), (x0 + per * 0.18, 0.0), (x0 + per * 0.32, 0.035), (x0 + per * 0.68, 0.035), (x0 + per * 0.82, 0.0)]
    prof.append((w / 2, 0.0))
    meb = _sheet_mesh("BLACHA", prof, 2 * ROOF_Y); meb.materials.append(bl)
    R["blacha"] = []
    for i in range(4):
        o = bpy.data.objects.new(f"ROOF_BLACHA_{i}", meb); FL.link(o, coll); o.modifiers.new("t", "SOLIDIFY").thickness = 0.0006
        o.location = (-ROOF_X + w / 2 + i * w, -ROOF_Y, ROOF_Z); R["blacha"].append(o)
    pine = bpy.data.materials["pine_planed"]; R["lamele"] = []
    for i, x in enumerate(np.arange(-ROOF_X + 0.07, ROOF_X - 0.06, 0.165)):
        R["lamele"].append(FL.box(f"ROOF_LAMELA_{i:02d}", (0.12, 2 * ROOF_Y, 0.028), (x, 0, ROOF_Z + 0.014), pine, coll, bevel=0.002))
    cv = FL.simple("plotno_kremowe", (0.78, 0.72, 0.62, 1), rough=0.85, spec=0.2)
    cv.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.4
    R["plotno"] = [FL.box("ROOF_PLOTNO", (2 * ROOF_X, 2 * ROOF_Y, 0.004), (0, 0, ROOF_Z + 0.003), cv, coll, bevel=0.0)]
    return R


def _show(obs, on):
    for o in obs:
        o.hide_render = not on; o.hide_viewport = not on


def roof_state(R, f):
    kind, p = None, 0.0
    for a, b, k in ROOF_TL:
        if a <= f < b:
            kind = k; p = (f - a) / (b - a)
    _show([R["poly"]], kind in ("poly", "poly_roll")); _show([R["roll"]], kind == "poly_roll")
    _show(R["blacha"], kind == "blacha"); _show(R["lamele"], kind == "lamele"); _show(R["plotno"], kind == "plotno")
    if kind == "poly_roll":
        Ly = 2 * ROOF_Y; q = e_io((f - 750) / 58.0); s = max(1e-4, q * Ly)
        R["poly"].location = (0, -ROOF_Y, ROOF_Z); R["poly"].scale = (1, s, 1)
        rm = R["roll_rmax"]; r = rm * math.sqrt(max(0.15, 1 - q))
        R["roll"].scale = (1, r / rm, r / rm); R["roll"].location = (0, -ROOF_Y + s, ROOF_Z + r)
        R["roll"].rotation_euler = (s / max(r, 0.03), 0, 0)
        _show([R["roll"]], q < 0.995)
    elif kind == "poly":
        R["poly"].location = (0, -ROOF_Y, ROOF_Z); R["poly"].scale = (1, 2 * ROOF_Y, 1)


# ------------------------------------------------------------------------------------------------ pergola items
class Item:
    def __init__(self, ob, meshes, M0):
        self.ob, self.meshes, self.M0 = ob, meshes, M0
        self.kit = None; self.kit_land = -1
        self.leave = self.arrive = self.seat = -1
        self.dir = Vector((0, 0, 0)); self.L = 0.0; self.groups = (); self.spin = False; self.tumble = 0.0; self.arc = 1.5


def build_pergola():
    FL.build_pergola("PERGOLA")
    L = FL.load_json("layout.json"); items = {}
    for p in L["parts"]:
        e = bpy.data.objects[f"INST_{p['id']}"]; items[p["id"]] = Item(e, list(e.children), e.matrix_world.copy())
    for t in L["timber"]:
        o = bpy.data.objects[t["id"]]; items[t["id"]] = Item(o, [o], o.matrix_world.copy())
    for i, f in enumerate(L["fasteners"]):
        o = bpy.data.objects[f"SCREW_{i:03d}"]; it = Item(o, [o], o.matrix_world.copy()); it.f = f; it.spin = True
        items[f"SCREW_{i:03d}"] = it
    bpy.context.view_layer.update()
    return items, L


def kit_layout(items):
    """Flat-pack laid out on the white floor right of the pad (x 2.9..5.8), dropped in one by one at the start."""
    def timber_kit(it, x, y):
        v = np.array([vv.co[:] for vv in it.meshes[0].data.vertices]); d = v.max(0) - v.min(0)
        if d[0] >= d[1]:
            Rk = np.column_stack([(1, 0, 0), (0, 0, -1), (0, 1, 0)]); hz = d[1] / 2
        else:
            Rk = np.column_stack([(0, 0, 1), (1, 0, 0), (0, 1, 0)]); hz = d[0] / 2
        M = np.eye(4); M[:3, :3] = Rk; M[:3, 3] = (x, y, FLOOR_Z + hz); it.kit = Matrix(M.tolist())

    def part_kit(it, x, y, R):
        verts = []
        for m in it.meshes:
            verts += [vv.co[:] for vv in m.data.vertices]
        v = np.array(verts) @ np.array(R).T; c = (v.max(0) + v.min(0)) / 2
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = (x - c[0], y - c[1], FLOOR_Z - v.min(0)[2] + 0.001); it.kit = Matrix(M.tolist())

    order = []
    x = 3.75
    for k in range(4):
        timber_kit(items[f"POST_C{k+1}"], x, -1.9); x += 0.115; order.append(f"POST_C{k+1}")
    for pid in ("BEAM_LONG_L", "BEAM_LONG_R"):
        timber_kit(items[pid], x, 0.0); x += 0.115; order.append(pid)
    for pid in ("BEAM_END_A", "BEAM_END_B"):
        timber_kit(items[pid], x, -1.3); x += 0.115; order.append(pid)
    for i in range(11):
        timber_kit(items[f"RAFTER_{i}"], x + 0.02, -1.25); x += 0.11; order.append(f"RAFTER_{i}")
    I = np.eye(3); flip = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])
    for k in range(4):
        part_kit(items[f"STOPA_C{k+1}"], 3.12, -3.25 + 0.30 * k, I); order.insert(k, f"STOPA_C{k+1}")
    for k in range(4):
        part_kit(items[f"TROJAK_C{k+1}"], 3.12, -1.85 + 0.42 * k, flip); order.insert(4 + k, f"TROJAK_C{k+1}")
    rm = np.array(items["MOCOW_L_0"].M0.to_3x3())
    mo = [f"MOCOW_{s}_{i}" for i in range(11) for s in ("L", "R")]
    for j, pid in enumerate(mo):
        r, c = divmod(j, 2); part_kit(items[pid], 3.0 + 0.27 * c, 0.15 + 0.27 * r, rm); order.append(pid)
    for j, pid in enumerate(order):                       # land times: 0.2 s .. 2.0 s
        items[pid].kit_land = 6 + int(54 * j / len(order))


def schedule(items):
    def go(pid, leave, arrive, seat, d, Ln, groups=(), tumble=0.0, arc=1.5):
        it = items[pid]; it.leave, it.arrive, it.seat = leave, arrive, seat
        it.dir = Vector(d); it.L = Ln; it.groups = groups; it.tumble = tumble; it.arc = arc
    # Stopa C1 seen falling onto the studs (s05); others seated off camera
    go("STOPA_C1", 118, 140, 150, (0, 0, -1), 0.45, arc=2.0)
    for k, t in ((2, 175), (3, 185), (4, 195)):
        go(f"STOPA_C{k}", t - 30, t - 8, t, (0, 0, -1), 0.4)
    # post C1 tumbles in from the sky (s06), others during s07
    go("POST_C1", 158, 200, 212, (0, 0, -1), 0.75, tumble=2.6, arc=5.0)
    for k, t in ((2, 228), (3, 236), (4, 244)):
        go(f"POST_C{k}", t - 40, t - 10, t, (0, 0, -1), 0.7, tumble=1.5, arc=4.0)
    F = ("lift",); RG = ("lift", "join")
    go("BEAM_LONG_L", 232, 256, 256, (0, 0, 0), 0.0, F, arc=3.0)
    go("TROJAK_C1", 250, 272, 286, (0, 1, 0), 0.5, F, arc=3.0)        # s09: seen from below sliding onto the beam end
    go("TROJAK_C4", 262, 284, 298, (0, -1, 0), 0.5, F, arc=3.0)
    go("BEAM_LONG_R", 270, 296, 296, (0, 0, 0), 0.0, RG, arc=3.0)
    go("TROJAK_C2", 284, 304, 316, (0, 1, 0), 0.5, RG, arc=3.0)
    go("TROJAK_C3", 290, 310, 322, (0, -1, 0), 0.5, RG, arc=3.0)
    go("BEAM_END_A", 300, 324, 340, (1, 0, 0), 0.7, RG, arc=3.0)
    go("BEAM_END_B", 306, 330, 346, (1, 0, 0), 0.7, RG, arc=3.0)
    mo = [f"MOCOW_{s}_{i}" for i in range(11) for s in ("L", "R")]
    for j, pid in enumerate(mo):                          # s15: hangers pop onto the beams one after another
        s = 452 + int(4.4 * j); go(pid, s - 26, s - 8, s, (0, 0, -1), 0.35, arc=2.5)
    go("RAFTER_0", 640, 660, 672, (0, 0, -1), 0.8, arc=3.5)
    for i in range(1, 11):
        s = 690 + int(4.8 * (i - 1)); go(f"RAFTER_{i}", s - 30, s - 10, s, (0, 0, -1), 0.8, arc=3.5)
    # fasteners: each along its own axis into its real hole
    win = {"stopaC1": (218, 242), "stopa": (236, 252), "trojak": (412, 432), "mocow_side": (500, 575), "mocow_up": (700, 748)}
    groups = {k: [] for k in win}
    for k, it in items.items():
        if not k.startswith("SCREW"):
            continue
        p = it.f["part"]
        if p.startswith("STOPA"):
            groups["stopaC1" if p == "STOPA_C1" else "stopa"].append(k)
        elif p.startswith("TROJAK"):
            groups["trojak"].append(k)
        elif it.f["axis_to_timber"][2] > 0.5:
            groups["mocow_up"].append(k)
        else:
            groups["mocow_side"].append(k)
    for g, ks in groups.items():
        a, b = win[g]; ks.sort()
        for j, k in enumerate(ks):
            it = items[k]; dur = 12 if g == "stopaC1" else 8
            s = a + dur + (b - a - dur) * (j / max(1, len(ks) - 1))
            it.seat = s; it.arrive = it.leave = s - dur; it.dir = Vector(it.f["axis_to_timber"]).normalized(); it.L = 0.16
    # anchor nuts + washers: C1 in s05 (washers then nuts), others off camera
    for k, it in items.items():
        if getattr(it, "anchor", None):
            c1 = it.part == "STOPA_C1"; idx = int(k.split("_")[1]) % 4
            base = (152 if c1 else {"STOPA_C2": 178, "STOPA_C3": 188, "STOPA_C4": 198}[it.part])
            s = base + idx * 3 + (6 if it.anchor == "NUT" else 0) + (8 if c1 else 0)
            it.seat = s; it.arrive = it.leave = s - (12 if it.anchor == "NUT" else 9)
            it.dir = Vector((0, 0, -1)); it.L = 0.22


GROUP_T = {"join": (352, 386), "lift": (398, 420)}


def group_offset(groups, f):
    o = Vector((0, 0, 0))
    if "join" in groups:
        a, b = GROUP_T["join"]; o += Vector((JOIN, 0, 0)) * (1 - e_io((f - a) / (b - a)))
    if "lift" in groups:
        a, b = GROUP_T["lift"]; o += Vector((0, 0, LIFT)) * (1 - e_io((f - a) / (b - a)))
    return o


def set_item(it, M, vis):
    it.ob.matrix_world = M
    for m in it.meshes:
        m.hide_render = not vis; m.hide_viewport = not vis


def item_pose(it, f):
    """-> (Matrix, visible)"""
    if it.kit is not None and (it.leave < 0 or f < it.leave):
        if f < it.kit_land - 12:
            return it.kit, False
        u = e_seat((f - (it.kit_land - 12)) / 12.0)
        return Matrix.Translation((0, 0, 1.4 * (1 - u))) @ it.kit, True
    if it.seat < 0:
        return it.M0, False
    if f < it.leave:
        return it.M0, False
    appr = Matrix.Translation(-it.dir * it.L + group_offset(it.groups, f)) @ it.M0
    if it.kit is not None and f < it.arrive:            # flight from the kit on a high arc, settling into orientation
        u = (f - it.leave) / max(1, it.arrive - it.leave); k = e_io(u)
        p0, p1 = it.kit.translation, appr.translation
        h = it.arc + 0.25 * (p1 - p0).length
        pos = p0.lerp(p1, k) + Vector((0, 0, h * 4 * k * (1 - k)))
        q0, q1 = it.kit.to_quaternion(), appr.to_quaternion()
        q = q0.slerp(q1, e_io(min(1.0, u * 1.25)))
        if it.tumble:
            ax = Vector((1, 0.4, 0.2)).normalized()
            q = q @ Quaternion(ax, it.tumble * (1 - e_out(u)) * math.pi)
        M = q.to_matrix().to_4x4(); M.translation = pos
        return M, True
    if f < it.arrive:                                   # fasteners: fly in along the axis
        return appr, True
    u = (f - it.arrive) / max(1, it.seat - it.arrive)
    off = -it.dir * it.L * (1 - e_seat(u)) + group_offset(it.groups, f)
    M = Matrix.Translation(off) @ it.M0
    if it.spin and u < 1:
        c = it.M0.translation
        M = Matrix.Translation(off) @ Matrix.Translation(c) @ Matrix.Rotation(-16 * (1 - e_seat(u)), 4, it.dir) @ Matrix.Translation(-c) @ it.M0
    return M, True


def pose_items(items, f):
    for it in items.values():
        M, vis = item_pose(it, f); set_item(it, M, vis)


# ------------------------------------------------------------------------------------------------ frame
def apply_frame(S, f):
    fs = END_SRC if f >= 1005 else f
    name, u, keys = shot_of(f)
    pose_items(S["items"], fs)
    roof_state(S["roofs"], fs)
    place_camera(S["cam"], keys, u)
    bpy.context.scene.frame_set(fs)
    return name


def build(w, h, spp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.fps = FPS
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0.45
    sc.render.image_settings.file_format = "PNG"
    setup_world()
    pad, zinc = setup_studio()
    items, L = build_pergola()
    mat_steel(); mat_wood()
    build_anchors(items, L, zinc)
    kit_layout(items); schedule(items)
    R = build_roofs()
    cd = bpy.data.cameras.new("cam"); cd.sensor_width = 36; cd.clip_start = 0.01
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    return dict(items=items, pad=pad, roofs=R, cam=cam)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="0"); ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--w", type=int, default=540); ap.add_argument("--h", type=int, default=960)
    ap.add_argument("--spp", type=int, default=32); ap.add_argument("--save", default="")
    a = ap.parse_args()
    S = build(a.w, a.h, a.spp)
    if a.save:
        bpy.ops.wm.save_as_mainfile(filepath=a.save)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    for f in [int(x) for x in a.frames.split(",")]:
        p = Path(a.out) / f"f{f:04d}.png"
        if p.exists() or (f >= 1005 and f != END_SRC):
            continue
        n = apply_frame(S, f)
        bpy.context.scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        print("rendered", f, n, flush=True)
