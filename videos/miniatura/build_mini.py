"""RIVON video #5 "Miniatura" - a desk model that turns out to be a real carport pergola.

One Blender scene, two places:
  CORE  (plot coordinates, pergola at the origin): exact-STEP pergola, clear polycarbonate roof, Dodge RAM, cobbled drive, lawn patch, thujas.
        Rendered twice: full size (the real plot) and as a 1:MINI_S collection instance standing on a workbench (the "makieta").
  FAR   only around the real plot: a traditional Polish house, neighbours, fences, gate, street, trees, sky.
  SHOP  carpenter's workshop far away (x = SHOP_X): bench, window, tools, a real full-size Trojak 3D lying next to the model.
The camera path is defined once in plot coordinates; on the desk it is mapped through the instance transform, so the hidden cuts
(frame filled by one connector / one beam) are geometrically exact.
"""
import math, sys
from pathlib import Path
import numpy as np
import bpy, mathutils

HERE = Path(__file__).resolve().parent
FILM = HERE.parent / "rivon_film"
sys.path.insert(0, str(FILM)); sys.path.insert(0, str(HERE))
from film_lib import *          # noqa  (materials, STL reader, build_pergola, box/cyl helpers)
import film_sets as FS
import film_scenes as SCN
import film_props as P
from film_stage import mat_matte, _nodes
import build_film as BF          # import_ram()

MINI_S = 1.0 / 25.0                       # model scale
SHOP_X = 320.0                            # workshop lies far outside the plot
BENCH_TOP = 0.90                          # workbench top height (m, shop floor = 0)
BOARD_T = 0.018                           # plywood base of the model
CORE_DEPTH = 0.20                         # core ground slabs are 0.2 m thick (= 8 mm in the model)
# model placement on the bench (world): board centre, rotation about z
MODEL_LOC = (SHOP_X + 0.05, 0.97, BENCH_TOP + BOARD_T + CORE_DEPTH * MINI_S)
REAL_TROJAK_LOC = (SHOP_X - 0.50, 0.56, BENCH_TOP + 0.1)
REAL_TROJAK_ROT = (0.0, 0.0, math.radians(40))
MODEL_ROT = math.radians(0.0)
CORE_X, CORE_Y = 4.6, 6.8                 # half extents of the model base (plot metres)
SUN = dict(el=32.0, az=228.0, energy=7.0, color=(1.0, 0.87, 0.70))


# ------------------------------------------------------------------------------------------------ materials
def mat_polycarb():
    m = bpy.data.materials.new("polycarbonate_clear"); nt = _nodes(m)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
    b.inputs["Base Color"].default_value = (0.86, 0.9, 0.93, 1); b.inputs["Transmission Weight"].default_value = 0.92
    b.inputs["Roughness"].default_value = 0.06; b.inputs["IOR"].default_value = 1.58
    return m


def mat_alu():
    return simple("alu_profile", (0.62, 0.63, 0.64, 1), 0.32, 1.0, 0.5)


def mat_panel_green():
    return simple("panel_fence", (0.035, 0.06, 0.04, 1), 0.45, 0.6, 0.5)


def thuja_mesh():
    """Thuja 'Smaragd': dense narrow cone (2.6 m) with a lumpy noise surface, a short visible trunk."""
    import bmesh
    if "thuja" in bpy.data.meshes: return bpy.data.meshes["thuja"]
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.42, radius2=0.03, depth=2.45)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    rng = np.random.default_rng(3); ph = rng.uniform(0, 6.28, 6)
    for v in bm.verts:
        x, y, z = v.co; t = (z + 1.225) / 2.45
        r = math.hypot(x, y)
        if r > 1e-4:
            bulge = 1.0 + 0.10 * math.sin(z * 9.0 + ph[0]) * math.cos(math.atan2(y, x) * 5 + ph[1]) + 0.06 * math.sin(z * 23 + math.atan2(y, x) * 11 + ph[2])
            bulge *= (1.0 + 0.25 * math.sin(math.pi * min(t * 1.25, 1.0)))
            v.co.x *= bulge; v.co.y *= bulge
        v.co.z += 1.225 + 0.18
    me = bpy.data.meshes.new("thuja"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(FS.foliage_mat("thuja_leaf", (0.008, 0.03, 0.008), (0.035, 0.085, 0.02), 9.0))
    return me


# ------------------------------------------------------------------------------------------------ CORE (rendered full size and as the model)
def build_core():
    core = collection("CORE")
    # pergola: exact STEP meshes, untouched (build_pergola makes its own collection -> nest it in CORE)
    build_pergola("PERGOLA")
    pc = bpy.data.collections["PERGOLA"]; bpy.context.scene.collection.children.unlink(pc); core.children.link(pc)
    # clear polycarbonate roof on top of beams/rafters (top z 2.597), slight fall toward -y, aluminium edge profiles
    g = P.G(core, "roof", bevel=0.002)
    pcm = mat_polycarb(); al = mat_alu()
    W, D, over = 3.494 + 0.30, 5.994 + 0.36, 0.0
    box("roof_sheet", (W, D, 0.016), (0, 0, 2.606), pcm, core, 0, 0.002)
    for x in np.linspace(-W / 2 + 0.01, W / 2 - 0.01, 5): g.box((x, 0, 2.624), (0.05, D, 0.022), al)
    for sy in (-1, 1): g.box((0, sy * D / 2, 2.606), (W, 0.03, 0.05), al)
    g.flush()
    # car under the carport (owner-supplied Dodge RAM)
    ram = BF.import_ram(); ram.location = (0.25, 0.15, 0.0); ram.rotation_euler = (0, 0, math.radians(180))
    cc = bpy.data.collections["CAR_RAM"]; bpy.context.scene.collection.children.unlink(cc); core.children.link(cc)
    # ground slabs (0.2 m thick: their cut edges are the model's base)
    kostka = FS.paving((0.42, 0.40, 0.38), 0.9, "kostka")
    lawn = SCN.lawn_rich()
    drive_x = (-2.3, 2.3)
    box("core_drive", (drive_x[1] - drive_x[0], 2 * CORE_Y, CORE_DEPTH), (0, 0, -CORE_DEPTH / 2), kostka, core, 0, 0.0)
    box("core_lawn_l", (CORE_X + drive_x[0], 2 * CORE_Y, CORE_DEPTH), ((-CORE_X + drive_x[0]) / 2, 0, -CORE_DEPTH / 2), lawn, core, 0, 0.0)
    box("core_lawn_r", (CORE_X - drive_x[1], 2 * CORE_Y, CORE_DEPTH), ((CORE_X + drive_x[1]) / 2, 0, -CORE_DEPTH / 2), lawn, core, 0, 0.0)
    kerb = mat_matte("kerb_grey", (0.55, 0.55, 0.54, 1), 0.85)
    for x in drive_x: box(f"core_kerb_{x}", (0.08, 2 * CORE_Y, 0.06), (x + (0.04 if x < 0 else -0.04), 0, 0.03), kerb, core, 0, 0.01)
    SCN.grass(core, (-CORE_X + drive_x[0]) / 2, 0, (CORE_X + drive_x[0]) / 2 - 0.03, CORE_Y - 0.03, 60000, 5)
    SCN.grass(core, (CORE_X + drive_x[1]) / 2, 0, (CORE_X - drive_x[1]) / 2 - 0.03, CORE_Y - 0.03, 60000, 6)
    # row of thujas along +x, panel fence along +x edge, a few low shrubs on the left
    thu = thuja_mesh()
    for i, y in enumerate(np.arange(-CORE_Y + 0.55, CORE_Y - 0.3, 0.72)):
        ob = bpy.data.objects.new(f"thuja_{i}", thu); ob.location = (CORE_X - 0.5, y, 0); ob.rotation_euler = (0, 0, i * 1.7)
        k = 1.0 + 0.07 * math.sin(i * 2.3); ob.scale = (k, k, k * (1.0 + 0.05 * math.cos(i * 1.1))); link(ob, core)
    pg = P.G(core, "panel_fence", bevel=0.0); pm = mat_panel_green()
    xf = CORE_X - 0.12
    for y in np.arange(-CORE_Y + 0.02, CORE_Y, 0.05): pg.box((xf, y, 0.78), (0.005, 0.005, 1.53), pm)
    for z in (0.08, 0.65, 1.25, 1.52): pg.box((xf, 0, z), (0.006, 2 * CORE_Y - 0.04, 0.006), pm)
    for y in np.arange(-CORE_Y + 0.05, CORE_Y, 2.5): pg.box((xf + 0.03, y, 0.85), (0.06, 0.04, 1.7), pm)
    pg.flush()
    SCN.shrubs(core, [(-CORE_X + 0.7, y) for y in (-5.2, -3.6, 3.9, 5.5)], 41, 0.6, 0.45, "pink")
    return core


# ------------------------------------------------------------------------------------------------ FAR (real plot only)
def build_far():
    far = collection("FAR")
    FS.ground(far, SCN.lawn_rich(), size=(300, 300), z=-0.003)
    SCN.grass(far, -9.5, 0, 4.8, 9.0, 70000, 8)                 # foreground lawn beyond the core, left side
    SCN.grass(far, 0, 11.0, 9.0, 3.6, 50000, 9)
    SCN.grass(far, 6.8, -10.6, 4.5, 3.8, 60000, 10)
    SCN.grass(far, -6.8, -10.6, 4.5, 3.8, 60000, 11)
    # traditional Polish house (light plaster, red clay tiles) to the left, facing the street (-y)
    FS.house_traditional(far, (-13.0, 4.0), 90, plaster_col=(0.90, 0.87, 0.80), roof_col=(0.34, 0.12, 0.07), W=11.0, D=9.0, key="dom")
    _pad = FS._pad
    kostka = bpy.data.materials["kostka"]
    _pad(far, "drive_far", (4.6, 9.0), (0, -CORE_Y - 4.5), kostka, 0.0)
    _pad(far, "path_house", (5.5, 1.4), (-6.8, -2.0), FS.paving((0.5, 0.48, 0.46), 0.7, "path_h"), 0.0)
    _pad(far, "road", (300, 8.0), (0, -21.0), FS.asphalt(), -0.05)
    _pad(far, "sidewalk", (300, 2.2), (0, -15.9), FS.paving((0.6, 0.58, 0.55), 0.6, "chodnik"), 0.0)
    # street fence: panel fence + sliding gate (closed track) at the drive
    pm = bpy.data.materials["panel_fence"]; pg = P.G(far, "street_fence", bevel=0.0)
    for x0, x1 in ((-40, -2.6), (2.6, 40)):
        for x in np.arange(x0, x1, 0.05): pg.box((x, -14.6, 0.8), (0.005, 0.005, 1.55), pm)
        for z in (0.08, 0.7, 1.3, 1.55): pg.box(((x0 + x1) / 2, -14.6, z), (x1 - x0, 0.006, 0.006), pm)
    pg.flush()
    FS.hedge(far, (-40, 13.0), (40, 13.0), 2.2, 1.0)
    FS.slat_fence(far, (-CORE_X - 9.0, -14.4), (-CORE_X - 9.0, 13), 1.8, (0.5, 0.36, 0.24), "fence_w")
    # neighbours across the street and behind
    FS.house_traditional(far, (-6.0, -32.0), -90, plaster_col=(0.86, 0.82, 0.72), roof_col=(0.18, 0.18, 0.2), W=10.0, D=8.6, key="sasiad1")
    FS.house_traditional(far, (12.0, -33.0), -90, plaster_col=(0.92, 0.9, 0.86), roof_col=(0.36, 0.14, 0.08), W=9.5, D=8.0, key="sasiad2")
    FS.house_modern(far, (16.0, 20.0), 180, "sasiad3", cladding=(0.4, 0.3, 0.22), garage=False)
    bases = FS.tree_meshes(far, 52, "broad", 2)
    for p, s in (((-8.5, 11.0), 1.0), ((9.5, 9.0), 0.9), ((-22, -5), 1.15), ((22, -4), 1.1), ((4, 24), 1.2), ((-16, 22), 1.1), ((24, -26), 0.9)):
        FS.place_tree(far, bases, (p[0], p[1], 0), p[0], s)
    SCN._horizon(far, 53)
    cyl("lamp_pole", 0.07, 6.0, (6.0, -16.6, 3.0), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), far, 12)
    return far


# ------------------------------------------------------------------------------------------------ SHOP (carpenter's workshop, model on the work table)
def build_shop():
    """Room 7 x 6 x 3 m. Big window in the -y wall lets the low sun (az 228, el 32) fall across the island work table,
    so the model is lit from the same direction as the real plot (the hidden cuts match)."""
    shop = collection("SHOP")
    X = SHOP_X
    plaster = FS.plaster((0.80, 0.78, 0.74), "shop_wall")
    floor = mat_matte("shop_floor", (0.20, 0.19, 0.17, 1), 0.75)
    rx0, rx1, ry0, ry1, H = X - 3.5, X + 3.5, -1.0, 5.0, 3.0
    box("shop_floor", (rx1 - rx0, ry1 - ry0, 0.1), (X, (ry0 + ry1) / 2, -0.05), floor, shop, 0, 0)
    box("shop_ceiling", (rx1 - rx0, ry1 - ry0, 0.1), (X, (ry0 + ry1) / 2, H + 0.05), plaster, shop, 0, 0)
    box("shop_wall_n", (rx1 - rx0, 0.2, H), (X, ry1 + 0.1, H / 2), plaster, shop, 0, 0)
    box("shop_wall_w", (0.2, ry1 - ry0, H), (rx0 - 0.1, (ry0 + ry1) / 2, H / 2), plaster, shop, 0, 0)
    box("shop_wall_e", (0.2, ry1 - ry0, H), (rx1 + 0.1, (ry0 + ry1) / 2, H / 2), plaster, shop, 0, 0)
    wx0, wx1, wz0, wz1 = X - 2.2, X + 2.2, 0.95, 2.85
    box("shop_wall_s_a", (wx0 - rx0, 0.2, H), ((rx0 + wx0) / 2, ry0 - 0.1, H / 2), plaster, shop, 0, 0)
    box("shop_wall_s_b", (rx1 - wx1, 0.2, H), ((wx1 + rx1) / 2, ry0 - 0.1, H / 2), plaster, shop, 0, 0)
    box("shop_wall_s_c", (wx1 - wx0, 0.2, wz0), ((wx0 + wx1) / 2, ry0 - 0.1, wz0 / 2), plaster, shop, 0, 0)
    box("shop_wall_s_d", (wx1 - wx0, 0.2, H - wz1), ((wx0 + wx1) / 2, ry0 - 0.1, (wz1 + H) / 2), plaster, shop, 0, 0)
    fr = mat_matte("win_frame_dark", (0.03, 0.03, 0.032, 1), 0.5)
    g = P.G(shop, "win", bevel=0.003)
    for x in np.linspace(wx0, wx1, 5): g.box((x, ry0 - 0.1, (wz0 + wz1) / 2), (0.05, 0.08, wz1 - wz0), fr)
    for z in (wz0, wz1, 1.9): g.box(((wx0 + wx1) / 2, ry0 - 0.1, z), (wx1 - wx0, 0.08, 0.05), fr)
    g.flush()
    bases = FS.tree_meshes(shop, 61, "broad", 2)
    for i, (dx, dy) in enumerate(((3, -18), (9, -12), (14, -25), (-14, -8))): FS.place_tree(shop, bases, (X + dx, dy, 0), dx, 0.9, i)
    FS.ground(shop, SCN.lawn_rich(), size=(80, 60), z=-0.003, name="shop_outside").location = (X, -31.5, -0.103)
    # island work table: thick beech top on a sturdy frame
    beech = FS.timber((0.72, 0.60, 0.48), 2.5, "beech_top")
    tx0, tx1, ty0, ty1 = X - 1.1, X + 1.1, 0.40, 1.55
    box("bench_top", (tx1 - tx0, ty1 - ty0, 0.07), (X, (ty0 + ty1) / 2, BENCH_TOP - 0.035), beech, shop, 0, 0.004)
    gb = P.G(shop, "bench", bevel=0.004)
    for lx in (tx0 + 0.08, tx1 - 0.08):
        for ly in (ty0 + 0.08, ty1 - 0.08): gb.box((lx, ly, (BENCH_TOP - 0.07) / 2), (0.09, 0.09, BENCH_TOP - 0.07), "wood_light")
    gb.box((X, (ty0 + ty1) / 2, 0.20), (tx1 - tx0 - 0.1, ty1 - ty0 - 0.1, 0.025), "wood_light")
    gb.flush()
    # plywood model base
    ply = simple("plywood_birch", (0.74, 0.60, 0.42, 1), 0.6, 0.0, 0.3)
    bw, bd = 2 * CORE_X * MINI_S + 0.04, 2 * CORE_Y * MINI_S + 0.04
    box("model_board", (bw, bd, BOARD_T), (MODEL_LOC[0], MODEL_LOC[1], BENCH_TOP + BOARD_T / 2), ply, shop, MODEL_ROT, 0.001)
    inst = bpy.data.objects.new("MODEL", None); inst.instance_type = "COLLECTION"; inst.instance_collection = bpy.data.collections["CORE"]
    inst.location = MODEL_LOC; inst.rotation_euler = (0, 0, MODEL_ROT); inst.scale = (MINI_S,) * 3; shop.objects.link(inst)
    # full-size RIVON Trojak 3D (exact STEP mesh) lying on the table, right foreground
    steel = mat_steel(); troj = bpy.data.objects.new("REAL_TROJAK", None); shop.objects.link(troj)
    for s_ in range(3):
        v, f = read_stl(FILM / "cad" / f"Trojak_3D_s{s_}.stl")
        me = mesh_from_arrays(f"REAL_Trojak_s{s_}", v * MM, f); me.materials.append(steel)
        ob = bpy.data.objects.new(f"REAL_Trojak_s{s_}", me); ob.parent = troj; shop.objects.link(ob)
    troj.location = REAL_TROJAK_LOC; troj.rotation_euler = REAL_TROJAK_ROT
    # props
    gp = P.G(shop, "props", bevel=0.0); z = BENCH_TOP
    mx, my = X - 0.42, 1.30
    gp.cyl((mx, my, z + 0.05), 0.042, 0.10, "white", 40); gp.cyl((mx, my, z + 0.094), 0.038, 0.004, "coffee", 40)
    gp.ell((mx + 0.05, my, z + 0.05), 0.028, "white", (0.35, 1.0, 1.0), 16, 10)
    gp.box((X + 0.02, 0.55, z + 0.0045), (0.18, 0.012, 0.007), "red", rz=math.radians(18))         # flat carpenter pencil
    gp.box((X - 0.36, 0.62, z + 0.03), (0.075, 0.035, 0.06), "mustard")                             # tape measure
    gp.cyl((X - 0.36, 0.62, z + 0.03), 0.028, 0.037, "charcoal", 24, axis="y")
    gp.box((X + 0.50, 1.38, z + 0.002), (0.30, 0.04, 0.003), "steel")                               # steel square
    gp.box((X + 0.64, 1.25, z + 0.002), (0.04, 0.24, 0.003), "steel")
    gp.box((X - 0.75, 1.0, z + 0.03), (0.16, 0.10, 0.06), "lgrey")                                  # screw box
    rng = np.random.default_rng(4)
    for i in range(90):                                                                             # pine shavings
        gp.ell((X + rng.uniform(-0.9, 0.9), rng.uniform(0.5, 1.45), z + 0.003), rng.uniform(0.006, 0.018), "wood_light", (1.0, rng.uniform(0.3, 0.6), 0.25), 10, 6)
    gp.flush()
    # back of the room (blurred): lumber rack with stacked timber, leaning plywood, a sawhorse, hanging clamps
    pine = FS.timber((0.9, 0.7, 0.48), 1.2, "stock_pine")
    gw = P.G(shop, "rack", bevel=0.003)
    for x in (X - 2.4, X - 0.8, X + 0.8, X + 2.4): gw.box((x, ry1 - 0.15, 1.5), (0.06, 0.25, 3.0), "graphite")
    for k, zz in enumerate((0.6, 1.25, 1.9, 2.5)):
        gw.box((X, ry1 - 0.15, zz - 0.03), (5.0, 0.28, 0.03), "graphite")
    gw.flush()
    for k, zz in enumerate((0.6, 1.25, 1.9)):
        for j in range(4 - k % 2):
            box(f"stock_{k}_{j}", (4.6 - 0.4 * j, 0.09, 0.045), (X + 0.1 * j, ry1 - 0.22 + 0.1 * (j % 2), zz + 0.025 + 0.047 * (j // 2)), pine, shop, 0, 0.003)
    for k in range(3): box(f"ply_lean_{k}", (1.25, 0.018, 2.4), (X - 2.6 + 0.04 * k, ry1 - 0.55 - 0.03 * k, 1.18), ply, shop, 0, 0.002).rotation_euler = (math.radians(-8 - 2 * k), 0, 0)
    gc = P.G(shop, "shelf_clutter", bevel=0.003); rng2 = np.random.default_rng(9)
    cols = ("white", "terra", "teal", "mustard", "grey", "olive", "red", "cream")
    for zz in (0.6, 1.25, 1.9, 2.5):
        x = X - 2.3
        while x < X + 2.3:
            kind = rng2.integers(0, 3); y0 = ry1 - 0.12
            if kind == 0:   # paint can
                r = rng2.uniform(0.06, 0.1); hh = rng2.uniform(0.12, 0.22); gc.cyl((x + r, y0, zz + hh / 2), r, hh, cols[rng2.integers(0, len(cols))], 20); x += 2 * r + 0.04
            elif kind == 1: # cardboard box
                w_ = rng2.uniform(0.25, 0.45); hh = rng2.uniform(0.18, 0.35); gc.box((x + w_ / 2, y0, zz + hh / 2), (w_, 0.22, hh), "cream"); x += w_ + 0.05
            else:           # gap / small tool case
                w_ = rng2.uniform(0.2, 0.35); gc.box((x + w_ / 2, y0, zz + 0.06), (w_, 0.2, 0.12), "red" if rng2.random() < 0.3 else "graphite"); x += w_ + 0.12
    gc.flush()
    gs = P.G(shop, "sawhorse", bevel=0.004)
    gs.box((X + 1.9, 3.2, 0.72), (1.0, 0.09, 0.09), "wood_light")
    for sx in (-0.4, 0.4):
        for sy in (-1, 1): gs.box((X + 1.9 + sx, 3.2 + sy * 0.15, 0.35), (0.07, 0.07, 0.75), "wood_light", rx=math.radians(sy * 14))
    gs.flush()
    ld = bpy.data.lights.new("shop_fill", "AREA"); ld.energy = 220.0; ld.size = 5.0; ld.color = (1.0, 0.94, 0.86)
    lo = bpy.data.objects.new("shop_fill", ld); lo.location = (X, 2.2, H - 0.05); shop.objects.link(lo)
    return shop


# ------------------------------------------------------------------------------------------------ scene setup
def model_matrix():
    return mathutils.Matrix.Translation(MODEL_LOC) @ mathutils.Matrix.Rotation(MODEL_ROT, 4, "Z") @ mathutils.Matrix.Scale(MINI_S, 4)


def prepare(w, h, spp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    build_core(); build_far(); build_shop()
    sc.world = SCN.sky_world(1.5, 0.45, 2.0)
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = SUN["energy"]; sun.angle = math.radians(0.6); sun.color = SUN["color"]
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    el, az = math.radians(SUN["el"]), math.radians(SUN["az"])
    d = -mathutils.Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    so.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    cam.clip_start = 0.002; cam.clip_end = 600.0; cam.sensor_width = 36.0
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = spp
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 4; sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 8; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Khronos PBR Neutral"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.3
    sc.render.fps = 30
    return sc


def place_camera(loc_plot, tgt_plot, lens, fstop, on_desk, exposure=None):
    """Camera given in PLOT coordinates. on_desk=True maps it through the model transform (same image, model scale)."""
    cam = bpy.data.objects["cam"]
    L, T = mathutils.Vector(loc_plot), mathutils.Vector(tgt_plot)
    if on_desk:
        M = model_matrix(); L, T = M @ L, M @ T
        fst = fstop                                   # desk aperture as given
    else:
        fst = fstop
    cam.location = L; cam.data.lens = lens
    cam.rotation_euler = (T - L).to_track_quat("-Z", "Y").to_euler()
    d = cam.data.dof; d.use_dof = True; d.focus_distance = (T - L).length; d.aperture_fstop = fst
    _excl("FAR", on_desk)
    if exposure is not None: bpy.context.scene.view_settings.exposure = exposure
    bpy.context.view_layer.update()


def _excl(name, on):
    lc = bpy.context.view_layer.layer_collection.children.get(name)
    if lc is not None: lc.exclude = on


# ------------------------------------------------------------------------------------------------ timeline
import mini_anim as AN
_path = {"p": None}


def _pose(f, desk):
    loc, tgt, lens, fst = _path["p"].sample(f)
    L, T = mathutils.Vector(loc), mathutils.Vector(tgt)
    if desk:
        M = model_matrix(); L, T = M @ L, M @ T
    rot = (T - L).to_track_quat("-Z", "Y").to_euler()
    return L, rot, lens, (T - L).length, fst


def apply_frame(f, motion_blur=False):
    """Camera (and which place is visible) for timeline frame f. With motion_blur the camera is keyed at f and f+0.5
    (both evaluated in the place of frame f) and the shutter opens at the frame, so blur never straddles a hidden cut."""
    if _path["p"] is None: _path["p"] = AN.Path(sys.modules[__name__])
    sc = bpy.context.scene; cam = bpy.data.objects["cam"]
    desk = AN.on_desk(f)
    _excl("FAR", desk)
    sc.view_settings.exposure = 0.4 if desk else 0.3
    cam.animation_data_clear(); cam.data.animation_data_clear()
    for sub in ((0.0, 0.5) if motion_blur else (0.0,)):
        L, rot, lens, fd, fst = _pose(f + sub, desk)
        cam.location = L; cam.rotation_euler = rot; cam.data.lens = lens
        d = cam.data.dof; d.use_dof = True; d.focus_distance = fd; d.aperture_fstop = fst
        if motion_blur:
            fr = f + sub
            for path in ("location", "rotation_euler"): cam.keyframe_insert(path, frame=fr)
            cam.data.keyframe_insert("lens", frame=fr); d.keyframe_insert("focus_distance", frame=fr); d.keyframe_insert("aperture_fstop", frame=fr)
    sc.render.use_motion_blur = motion_blur
    if motion_blur:
        sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = "START"
        sc.frame_set(f)
    bpy.context.view_layer.update()
