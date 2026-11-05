"""RIVON "Zestaw pergoli" (MBD-style kit video, 36 s @ 30 fps, 9:16).
White infinite studio + soft sky, paver pad, kit laid out, step-by-step assembly with the EXACT STEP meshes
(Stopa x4, Trojak 3D x4, Mocowanie belek 2 x22, layout.json validated: 0 collisions), then three roof coverings.
Assembly order = the verified plan of ../rivon_film (feet -> posts -> top frame built above and lowered -> mocowania -> rafters).
All metal parts only move rigidly; nothing is scaled or edited.
Usage: python3 build_zestaw.py --frames 0,100,... --out DIR --w 540 --h 960 --spp 32
"""
import sys, math, argparse
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rivon_film"))
import bpy, mathutils
from mathutils import Matrix, Vector
import film_lib as FL

FPS, NF = 30, 1080
SHOTS = [  # name, f0, f1
    ("hook", 0, 60), ("pad", 60, 120), ("kit", 120, 210), ("stopa", 210, 330), ("posts", 330, 420),
    ("trojak", 420, 540), ("frame", 540, 630), ("mocow", 630, 750),
    ("roof_poly", 750, 820), ("roof_blacha", 820, 890), ("roof_lamele", 890, 960), ("final", 960, 1080)]
LIFT, JOIN = 1.6, 2.0
ROOF_Z = 2.598
ROOF_X, ROOF_Y = 1.86, 3.16          # half extents of the covering


def clamp01(x): return max(0.0, min(1.0, x))
def e_io(u): u = clamp01(u); return u * u * (3 - 2 * u)
def e_seat(u): u = clamp01(u); return 1 - (1 - u) ** 2.4


def shot_of(f):
    for n, a, b in SHOTS:
        if a <= f < b:
            return n, (f - a) / (b - a)
    return SHOTS[-1][0], 1.0


# ------------------------------------------------------------------------------------------------ world / studio
def setup_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; N = nt.nodes; N.clear()
    out = N.new("ShaderNodeOutputWorld"); bg = N.new("ShaderNodeBackground")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # vertical gradient: hazy white horizon -> soft blue zenith
    ramp = N.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.93, 0.95, 0.98, 1)
    e[1].position = 0.55; e[1].color = (0.36, 0.52, 0.78, 1)
    mid = ramp.color_ramp.elements.new(0.12); mid.color = (0.80, 0.86, 0.94, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    # soft clouds: noise on the view direction, flattened vertically
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.6, 1.6, 5.0)
    nt.links.new(tc.outputs["Generated"], mp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 7.0
    nz.inputs["Roughness"].default_value = 0.62
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.5; cr.color_ramp.elements[1].position = 0.78
    nt.links.new(nz.outputs["Fac"], cr.inputs[0])
    # clouds only above the horizon band
    hz = N.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 0.0; hz.inputs["From Max"].default_value = 0.12
    nt.links.new(sep.outputs["Z"], hz.inputs["Value"])
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
    nt.links.new(cr.outputs["Color"], m1.inputs[0]); nt.links.new(hz.outputs["Result"], m1.inputs[1])
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 0.85
    nt.links.new(m1.outputs[0], m2.inputs[0])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[7].default_value = (0.97, 0.975, 0.985, 1)
    nt.links.new(m2.outputs[0], mix.inputs[0]); nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    nt.links.new(mix.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.15
    nt.links.new(bg.outputs[0], out.inputs[0])
    # sun
    sd = bpy.data.lights.new("sun", "SUN"); sd.energy = 4.2; sd.angle = math.radians(2.5); sd.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new("sun", sd); so.rotation_euler = (math.radians(42), 0, math.radians(-38))
    sc.collection.objects.link(so)


def mat_pavers():
    """Grey concrete paving blocks 20x10 cm (procedural brick pattern, per-block tone, chamfered joints)."""
    m = bpy.data.materials.new("kostka_brukowa"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    br = N.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 2.5; br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Mortar Smooth"].default_value = 0.6; br.inputs["Bias"].default_value = 0.0
    br.inputs["Brick Width"].default_value = 0.5; br.inputs["Row Height"].default_value = 0.25
    br.inputs["Color1"].default_value = (0.30, 0.30, 0.29, 1); br.inputs["Color2"].default_value = (0.43, 0.42, 0.40, 1)
    br.inputs["Mortar"].default_value = (0.16, 0.16, 0.155, 1)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60.0; nz.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "OVERLAY"; mx.inputs[0].default_value = 0.35
    nt.links.new(br.outputs["Color"], mx.inputs[6]); nt.links.new(nz.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.86
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.004
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(br.outputs["Fac"], inv.inputs[1])
    add = N.new("ShaderNodeMath"); add.operation = "ADD"
    sc = N.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 0.08
    nt.links.new(nz.outputs["Fac"], sc.inputs[0]); nt.links.new(inv.outputs[0], add.inputs[0]); nt.links.new(sc.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def setup_studio():
    coll = FL.collection("STUDIO")
    floor = FL.simple("studio_white", (0.80, 0.80, 0.81, 1), rough=0.72, spec=0.25)
    nt = floor.node_tree; N = nt.nodes; outn = N["Material Output"]; bsdf = N["Principled BSDF"]
    cd = N.new("ShaderNodeCameraData"); mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 25.0; mr.inputs["From Max"].default_value = 140.0
    nt.links.new(cd.outputs["View Distance"], mr.inputs["Value"])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.93, 0.95, 0.98, 1); em.inputs["Strength"].default_value = 1.15
    lp = N.new("ShaderNodeLightPath"); mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
    nt.links.new(mr.outputs["Result"], mx.inputs[0]); nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[1])
    ms = N.new("ShaderNodeMixShader")
    nt.links.new(mx.outputs[0], ms.inputs[0]); nt.links.new(bsdf.outputs[0], ms.inputs[1]); nt.links.new(em.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], outn.inputs["Surface"])
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=400, fill_type="NGON", location=(0, 0, -0.15))
    fl = bpy.context.active_object; fl.name = "floor"; fl.data.materials.append(floor); FL.link(fl, coll)
    pav = mat_pavers()
    pad = FL.box("PAD", (4.7, 7.5, 0.15), (0, 0, -0.075), pav, coll, bevel=0.01)
    return pad


# ------------------------------------------------------------------------------------------------ roof coverings
def _sheet_mesh(name, profile, length):
    """profile: list of (x, z); extruded along local +Y from 0 to length; returns mesh (two-sided via solidify)."""
    verts, faces = [], []
    n = len(profile)
    for y in (0.0, length):
        verts += [(x, y, z) for x, z in profile]
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    return FL.mesh_from_arrays(name, np.array(verts), faces, smooth=True)


def build_roofs():
    coll = FL.collection("ROOFS")
    R = {}
    # 1) corrugated polycarbonate (unrolls like the reference)
    poly = bpy.data.materials.new("polycarbonate_bronze"); poly.use_nodes = True
    b = poly.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.55, 0.42, 0.28, 1); b.inputs["Roughness"].default_value = 0.12
    b.inputs["Transmission Weight"].default_value = 0.92; b.inputs["IOR"].default_value = 1.58
    xs = np.linspace(-ROOF_X, ROOF_X, 600)
    prof = [(x, 0.009 * math.sin(2 * math.pi * (x + ROOF_X) / 0.076)) for x in xs]
    me = _sheet_mesh("POLY", prof, 1.0); me.materials.append(poly)
    ob = bpy.data.objects.new("ROOF_POLY", me); FL.link(ob, coll)
    so = ob.modifiers.new("t", "SOLIDIFY"); so.thickness = 0.0016
    R["poly"] = ob
    roll = FL.cyl("ROOF_POLY_ROLL", 1.0, 2 * ROOF_X, (0, 0, 0), poly, coll, seg=48, rot=(0, math.radians(90), 0))
    R["roll"] = roll
    # 2) trapezoidal steel sheet, graphite, 4 sheets
    bl = FL.simple("blacha_grafit", (0.035, 0.038, 0.042, 1), rough=0.38, metal=0.6, spec=0.5)
    w = 2 * ROOF_X / 4; per = w / 5; prof = []
    for k in range(5):
        x0 = -w / 2 + k * per
        prof += [(x0, 0.0), (x0 + per * 0.18, 0.0), (x0 + per * 0.32, 0.035), (x0 + per * 0.68, 0.035), (x0 + per * 0.82, 0.0)]
    prof.append((w / 2, 0.0))
    meb = _sheet_mesh("BLACHA", prof, 2 * ROOF_Y); meb.materials.append(bl)
    R["blacha"] = []
    for i in range(4):
        o = bpy.data.objects.new(f"ROOF_BLACHA_{i}", meb); FL.link(o, coll)
        so = o.modifiers.new("t", "SOLIDIFY"); so.thickness = 0.0006
        o["home"] = (-ROOF_X + w / 2 + i * w, -ROOF_Y, ROOF_Z)
        R["blacha"].append(o)
    # 3) wooden lamellas (deski) across the rafters
    pine = bpy.data.materials.get("pine_planed") or FL.mat_pine()
    R["lamele"] = []
    xs = np.arange(-ROOF_X + 0.07, ROOF_X - 0.06, 0.165)
    for i, x in enumerate(xs):
        o = FL.box(f"ROOF_LAMELA_{i:02d}", (0.12, 2 * ROOF_Y, 0.028), (x, 0, ROOF_Z + 0.014), pine, coll, bevel=0.002)
        o["home"] = (x, 0.0, ROOF_Z + 0.014)
        R["lamele"].append(o)
    return R


def _show(obs, on):
    for o in obs:
        o.hide_render = not on; o.hide_viewport = not on


def roof_state(R, kind, p):
    """kind in (None,'poly','blacha','lamele'); p in 0..1 progress of the covering animation."""
    _show([R["poly"], R["roll"]], kind == "poly")
    _show(R["blacha"], kind == "blacha")
    _show(R["lamele"], kind == "lamele")
    if kind == "poly":
        Ly = 2 * ROOF_Y; s = max(1e-4, e_io(p)) * Ly
        R["poly"].location = (0, -ROOF_Y, ROOF_Z); R["poly"].scale = (1, s, 1)
        rem = Ly - s; r = math.sqrt(0.035 ** 2 + rem * 0.0016 * 6 / math.pi)
        R["roll"].scale = (r, r, 1)
        R["roll"].location = (0, -ROOF_Y + s, ROOF_Z + r)
        R["roll"].rotation_euler = (s / r, math.radians(90), 0)
        R["roll"].rotation_mode = "YXZ"
        R["roll"].hide_render = R["roll"].hide_viewport = rem < 0.02
    elif kind == "blacha":
        for i, o in enumerate(R["blacha"]):
            u = e_seat((p - 0.12 * i) / 0.45)
            hx, hy, hz = o["home"]; o.location = (hx, hy, hz + 1.8 * (1 - u))
            o.hide_render = o.hide_viewport = (p - 0.12 * i) < 0
    elif kind == "lamele":
        n = len(R["lamele"])
        for i, o in enumerate(R["lamele"]):
            t0 = 0.55 * i / n; u = e_seat((p - t0) / 0.32)
            hx, hy, hz = o["home"]; o.location = (hx, hy, hz + 1.2 * (1 - u))
            o.hide_render = o.hide_viewport = p < t0


# ------------------------------------------------------------------------------------------------ pergola + events
class Item:
    def __init__(self, ob, meshes, M0):
        self.ob, self.meshes, self.M0 = ob, meshes, M0
        self.appear = -1; self.seat = -1; self.dir = Vector((0, 0, 0)); self.L = 0.0; self.groups = (); self.spin = False
        self.kit = None


def build_pergola():
    FL.build_pergola("PERGOLA")
    L = FL.load_json("layout.json")
    items = {}
    for p in L["parts"]:
        e = bpy.data.objects[f"INST_{p['id']}"]
        items[p["id"]] = Item(e, list(e.children), e.matrix_world.copy())
    for t in L["timber"]:
        o = bpy.data.objects[t["id"]]
        items[t["id"]] = Item(o, [o], o.matrix_world.copy())
    for i, f in enumerate(L["fasteners"]):
        o = bpy.data.objects[f"SCREW_{i:03d}"]
        it = Item(o, [o], o.matrix_world.copy()); it.f = f; it.spin = True
        items[f"SCREW_{i:03d}"] = it
    bpy.context.view_layer.update()
    return items, L


def schedule(items, L):
    def put(pid, seat, d, Ln, dur=24, groups=()):
        it = items[pid]; it.seat = seat; it.appear = seat - dur; it.dir = Vector(d); it.L = Ln; it.groups = groups
    for k in range(4):
        put(f"STOPA_C{k+1}", [236, 248, 254, 260][k], (0, 0, -1), 0.7, 22)
        put(f"POST_C{k+1}", 352 + 10 * k, (0, 0, -1), 2.6, 24)
    F = ("lift",); Rg = ("lift", "join")
    for pid, g in (("BEAM_LONG_L", F), ("BEAM_LONG_R", Rg)):
        put(pid, 420, (0, 0, 0), 0.0, 1, g)
    put("TROJAK_C1", 448, (0, 1, 0), 0.6, 26, F); put("TROJAK_C4", 458, (0, -1, 0), 0.6, 26, F)
    put("TROJAK_C2", 466, (0, 1, 0), 0.6, 26, Rg); put("TROJAK_C3", 474, (0, -1, 0), 0.6, 26, Rg)
    put("BEAM_END_A", 498, (1, 0, 0), 0.9, 26, Rg); put("BEAM_END_B", 508, (1, 0, 0), 0.9, 26, Rg)
    mo = [f"MOCOW_{s}_{i}" for i in range(11) for s in ("L", "R")]
    for j, pid in enumerate(mo):
        put(pid, 652 + int(1.5 * j), (0, 0, -1), 0.5, 16)
    for i in range(11):
        put(f"RAFTER_{i}", 700 + 3 * i, (0, 0, -1), 1.1, 20)
    # fasteners, each along its own axis into its real hole
    groups = {"anchorC1": [], "anchor": [], "stopa": [], "trojak": [], "mocow_side": [], "mocow_up": []}
    for k, it in items.items():
        if not k.startswith("SCREW"):
            continue
        f = it.f; p = f["part"]
        if f["kind"] == "anchor":
            groups["anchorC1" if p == "STOPA_C1" else "anchor"].append(k)
        elif p.startswith("STOPA"):
            groups["stopa"].append(k)
        elif p.startswith("TROJAK"):
            groups["trojak"].append(k)
        elif f["axis_to_timber"][2] > 0.5:
            groups["mocow_up"].append(k)
        else:
            groups["mocow_side"].append(k)
    win = {"anchorC1": (262, 300), "anchor": (290, 326), "stopa": (390, 418), "trojak": (608, 628),
           "mocow_side": (668, 700), "mocow_up": (734, 748)}
    for g, ks in groups.items():
        a, b = win[g]; ks.sort()
        for j, k in enumerate(ks):
            it = items[k]; ax = Vector(it.f["axis_to_timber"]).normalized()
            dur = 14 if g == "anchorC1" else 10
            s = a + dur + (b - a - dur) * (j / max(1, len(ks) - 1))
            it.seat = s; it.appear = s - dur; it.dir = ax; it.L = 0.14
            it.groups = ("lift", "join") if (g == "trojak" and False) else ()
    return groups


GROUP_T = {"join": (548, 578), "lift": (582, 606)}


def group_offset(groups, f):
    o = Vector((0, 0, 0))
    if "join" in groups:
        a, b = GROUP_T["join"]; o += Vector((JOIN, 0, 0)) * (1 - e_io((f - a) / (b - a)))
    if "lift" in groups:
        a, b = GROUP_T["lift"]; o += Vector((0, 0, LIFT)) * (1 - e_io((f - a) / (b - a)))
    return o


# ------------------------------------------------------------------------------------------------ kit (laid out on the pad)
def kit_layout(items):
    """Neat flat-pack arrangement on the pad. Timber lies along world Y, connectors stand on the pad in rows."""
    def timber_kit(it, x, y, z_extra=0.0):
        me = it.meshes[0].data; v = np.array([vv.co[:] for vv in me.vertices])
        d = v.max(0) - v.min(0)
        if d[0] >= d[1]:
            Rk = np.column_stack([(1, 0, 0), (0, 0, -1), (0, 1, 0)]); hz = d[1] / 2
        else:
            Rk = np.column_stack([(0, 0, 1), (1, 0, 0), (0, 1, 0)]); hz = d[0] / 2
        M = np.eye(4); M[:3, :3] = Rk; M[:3, 3] = (x, y, hz + z_extra)
        it.kit = Matrix(M.tolist())
    xs = -2.12
    for k in range(4):
        timber_kit(items[f"POST_C{k+1}"], xs + 0.11 * k, -0.9)
    timber_kit(items["BEAM_LONG_L"], -1.62, 0.0); timber_kit(items["BEAM_LONG_R"], -1.51, 0.0)
    timber_kit(items["BEAM_END_A"], -1.36, -1.6); timber_kit(items["BEAM_END_B"], -1.25, -1.6)
    for i in range(11):
        timber_kit(items[f"RAFTER_{i}"], -1.02 + 0.112 * i, -1.6)

    def part_kit(it, x, y, R):
        verts = []
        for m in it.meshes:
            verts += [vv.co[:] for vv in m.data.vertices]
        v = np.array(verts) @ np.array(R).T
        c = (v.max(0) + v.min(0)) / 2
        M = np.eye(4); M[:3, :3] = R; M[:3, 3] = (x - c[0], y - c[1], -v.min(0)[2] + 0.001)
        it.kit = Matrix(M.tolist())
    I = np.eye(3)
    flip = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]])      # Trojak: post socket down, as it is mounted
    for k in range(4):
        part_kit(items[f"STOPA_C{k+1}"], 1.0, -2.9 + 0.32 * k, I)
        part_kit(items[f"TROJAK_C{k+1}"], 1.75, -2.75 + 0.62 * k, flip)
    mo = [f"MOCOW_{s}_{i}" for i in range(11) for s in ("L", "R")]
    rm = np.array(items["MOCOW_L_0"].M0.to_3x3())
    for j, pid in enumerate(mo):
        r, c = divmod(j, 4)
        part_kit(items[pid], 0.85 + 0.27 * c, -0.2 + 0.24 * r, rm)
    for k, it in items.items():
        if k.startswith("SCREW"):
            it.kit = None


def set_item(it, M, vis):
    it.ob.matrix_world = M
    for m in it.meshes:
        m.hide_render = not vis; m.hide_viewport = not vis


def pose_items(items, f, mode):
    for k, it in items.items():
        if mode == "hidden":
            set_item(it, it.M0, False)
        elif mode == "final":
            set_item(it, it.M0, True)
        elif mode == "kit":
            if it.kit is None:
                set_item(it, it.M0, False)
            else:
                set_item(it, it.kit, True)
        else:  # assembly clock
            if it.seat < 0 or f < it.appear:
                set_item(it, it.M0, False); continue
            u = (f - it.appear) / max(1, it.seat - it.appear)
            off = -it.dir * it.L * (1 - e_seat(u)) + group_offset(it.groups, f)
            M = Matrix.Translation(off) @ it.M0
            if it.spin and u < 1:
                ax = it.dir
                M = Matrix.Translation(off) @ Matrix.Translation(it.M0.translation) @ Matrix.Rotation(-14 * (1 - e_seat(u)), 4, ax) \
                    @ Matrix.Translation(-it.M0.translation) @ it.M0
            set_item(it, M, True)


# ------------------------------------------------------------------------------------------------ cameras
# (f0, f1, loc0, loc1, target0, target1, lens)
CAM = {
    "hook":   ((-4.2, -6.2, 4.6), (-3.4, -5.6, 4.3), (-0.6, -1.2, 2.2), (-0.5, -0.6, 2.2), 26),
    "pad":    ((0.0, -9.0, 10.5), (6.2, -6.2, 10.0), (0, 0, 0), (0, 0, 0), 30),
    "kit":    ((3.6, -6.4, 4.6), (4.6, -3.0, 4.4), (0.0, -0.9, 0.0), (0.0, 0.0, 0.0), 26),
    "stopa":  ((-1.05, -3.75, 0.42), (-1.25, -3.85, 0.62), (-1.73, -2.98, 0.12), (-1.73, -2.98, 0.18), 45),
    "posts":  ((4.4, -7.4, 1.2), (5.4, -6.0, 1.6), (0.0, -0.6, 1.3), (0.0, -0.3, 1.4), 26),
    "trojak": ((-2.6, -4.3, 4.6), (-2.9, -3.7, 4.7), (-1.7, -2.95, 4.12), (-1.7, -2.6, 4.12), 30),
    "frame":  ((5.4, -7.6, 5.4), (6.6, -4.4, 4.4), (0.6, 0.0, 2.4), (0.3, 0.0, 2.1), 24),
    "mocow":  ((-0.35, -1.55, 3.25), (-0.5, -1.25, 3.05), (-1.62, -0.25, 2.55), (-1.62, 0.25, 2.55), 28),
    "roof_poly":   ((-5.6, -7.6, 5.6), (-3.9, -8.4, 5.0), (0, 0, 1.6), (0, 0.4, 1.6), 24),
    "roof_blacha": ((6.4, -6.8, 6.2), (7.6, -4.2, 5.6), (0, 0, 1.5), (0, 0.4, 1.6), 24),
    "roof_lamele": ((-6.0, 6.6, 3.4), (-7.4, 3.6, 3.2), (0, 0, 1.7), (0, 0, 1.8), 24),
    "final":  ((4.0, -8.6, 1.1), (6.8, -7.4, 2.4), (0, 0, 1.6), (0, 0, 1.4), 24),
}


def place_camera(cam, name, u):
    l0, l1, t0, t1, lens = CAM[name]
    k = e_io(u) * 0.85 + u * 0.15
    loc = Vector(l0).lerp(Vector(l1), k); tgt = Vector(t0).lerp(Vector(t1), k)
    cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    fs = DOF.get(name)
    cam.data.dof.use_dof = fs is not None
    if fs:
        cam.data.dof.aperture_fstop = fs; cam.data.dof.focus_distance = (tgt - loc).length


# ------------------------------------------------------------------------------------------------ frame
def apply_frame(S, f):
    name, u = shot_of(f)
    items, pad, R, cam = S["items"], S["pad"], S["roofs"], S["cam"]
    pad.location = (0, 0, -0.075)
    pad.hide_render = False
    roof = (None, 0.0)
    if name == "hook":
        pose_items(items, f, "final"); roof = ("poly", 0.25 + 0.55 * u)
    elif name == "pad":
        pose_items(items, f, "hidden")
        pad.location = (0, 0, -0.075 - 0.3 * (1 - e_seat(u / 0.6)))
    elif name == "kit":
        pose_items(items, f, "kit")
    elif name in ("stopa", "posts", "trojak", "frame", "mocow"):
        pose_items(items, f, "asm")
    elif name.startswith("roof_"):
        pose_items(items, f, "final"); roof = (name[5:], clamp01(u / 0.85))
    else:
        pose_items(items, f, "final"); roof = ("poly", 1.0)
    roof_state(R, *roof)
    place_camera(cam, name, u)
    bpy.context.scene.frame_set(f)
    return name


def realism():
    """Material/light pass. Geometry of RIVON parts untouched: edge highlights come from the Bevel SHADER node only."""
    st = bpy.data.materials["RIVON_black_powder_coat"]; nt = st.node_tree; N = nt.nodes
    b = N["Principled BSDF"]; bump = [n for n in N if n.type == "BUMP"][0]
    bv = N.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.0015; bv.samples = 8
    nt.links.new(bv.outputs["Normal"], bump.inputs["Normal"])
    b.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    b.inputs["Coat Weight"].default_value = 0.25; b.inputs["Coat Roughness"].default_value = 0.35
    b.inputs["Sheen Weight"].default_value = 0.08
    # timber: warmer oiled spruce, stronger pores, edge sheen from bevel shader
    pine = bpy.data.materials["pine_planed"]; nt = pine.node_tree; N = nt.nodes; b = N["Principled BSDF"]
    for n in N:
        if n.type == "VALTORGB" and len(n.color_ramp.elements) == 2 and n.color_ramp.elements[0].position == 0.25:
            n.color_ramp.elements[0].color = (0.62, 0.38, 0.17, 1); n.color_ramp.elements[1].color = (0.40, 0.21, 0.08, 1)
    bump = [n for n in N if n.type == "BUMP"][0]; bump.inputs["Strength"].default_value = 0.35
    bv = N.new("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.002; bv.samples = 8
    nt.links.new(bv.outputs["Normal"], bump.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.55; b.inputs["Sheen Weight"].default_value = 0.15
    b.inputs["Subsurface Weight"].default_value = 0.04; b.inputs["Subsurface Radius"].default_value = (0.02, 0.008, 0.004)
    # pavers: stronger chamfer + dirt
    pv = bpy.data.materials["kostka_brukowa"]; N = pv.node_tree.nodes
    for n in N:
        if n.type == "BUMP": n.inputs["Strength"].default_value = 0.9
        if n.type == "TEX_BRICK":
            n.inputs["Color1"].default_value = (0.27, 0.27, 0.26, 1); n.inputs["Color2"].default_value = (0.47, 0.46, 0.44, 1)
            n.inputs["Mortar"].default_value = (0.10, 0.10, 0.095, 1); n.inputs["Mortar Size"].default_value = 0.016
    # studio floor: slightly warm, not paper-white (keeps contrast), light: stronger low sun, softer fill
    fl = bpy.data.materials["studio_white"].node_tree.nodes["Principled BSDF"]
    fl.inputs["Base Color"].default_value = (0.74, 0.73, 0.72, 1)
    for n in bpy.data.materials["studio_white"].node_tree.nodes:
        if n.type == "EMISSION": n.inputs["Strength"].default_value = 1.0
        if n.type == "MAP_RANGE": n.inputs["From Min"].default_value = 18.0; n.inputs["From Max"].default_value = 90.0
    sun = bpy.data.lights["sun"]; sun.energy = 6.0; sun.angle = math.radians(1.2)
    bpy.data.objects["sun"].rotation_euler = (math.radians(50), 0, math.radians(-32))
    bpy.data.worlds["sky"].node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    sc = bpy.context.scene; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0.65
    fm = bpy.data.materials["studio_white"].node_tree; FN = fm.nodes; fb = FN["Principled BSDF"]
    tc = FN.new("ShaderNodeTexCoord"); nz = FN.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 10.0; nz.inputs["Roughness"].default_value = 0.6
    fm.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = FN.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = (0.66, 0.65, 0.63, 1); rp.color_ramp.elements[1].color = (0.80, 0.79, 0.78, 1)
    fm.links.new(nz.outputs["Fac"], rp.inputs[0]); fm.links.new(rp.outputs["Color"], fb.inputs["Base Color"])
    g = FN.new("ShaderNodeTexNoise"); g.inputs["Scale"].default_value = 400.0; g.inputs["Detail"].default_value = 4.0
    fm.links.new(tc.outputs["Object"], g.inputs["Vector"])
    bp = FN.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15; bp.inputs["Distance"].default_value = 0.001
    fm.links.new(g.outputs["Fac"], bp.inputs["Height"]); fm.links.new(bp.outputs["Normal"], fb.inputs["Normal"])
    wn = bpy.data.worlds["sky"].node_tree.nodes
    for n in wn:
        if n.type == "VALTORGB" and len(n.color_ramp.elements) == 3:
            n.color_ramp.elements[-1].color = (0.20, 0.38, 0.72, 1)


DOF = {"stopa": 2.8, "trojak": 3.5, "mocow": 3.5, "kit": 7.0}


def build(w, h, spp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.fps = FPS
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    setup_world()
    pad = setup_studio()
    items, L = build_pergola()
    schedule(items, L); kit_layout(items)
    R = build_roofs()
    cd = bpy.data.cameras.new("cam"); cd.sensor_width = 36
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    realism()
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
    fr = a.frames.split(",") if "-" not in a.frames else range(*map(int, a.frames.split("-")))
    for f in fr:
        f = int(f); n = apply_frame(S, f)
        p = Path(a.out) / f"f{f:04d}.png"
        if p.exists():
            continue
        bpy.context.scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        print("rendered", f, n, flush=True)
