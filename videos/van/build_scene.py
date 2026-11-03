"""RIVON video #3 "Busik" - build the scene.
Opens the garden scene of video #2 (house, lawn, trees, HDRI), strips the old gazebo animation, and adds:
  * a procedural white cargo van (RIVON decal) that drives in along the driveway and opens its rear doors
  * 3 cartons + beams, posts, rafters, roof slats that fly out of the van and assemble an L-shaped gazebo
  * all metal parts are the ORIGINAL meshes already in the scene (stopa, trojak, mb2 = tessellated RIVON STEP files)
Run:  python3 -I build_scene.py <in.blend> <out.blend>
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, Quaternion, Euler, Matrix

IN, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=IN)
sc = bpy.context.scene

# --- freeze the old film's time-of-day animation at a bright, constant daylight state ---
LIGHT_FRAME = 330
def _freeze(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return
    act = ad.action; fcs = []
    for l_ in act.layers:
        for st_ in l_.strips:
            for cb_ in st_.channelbags: fcs += list(cb_.fcurves)
    for fc in fcs:
        val = fc.evaluate(LIGHT_FRAME)
        opath, _, attr = fc.data_path.rpartition(".")
        try:
            owner = idb.path_resolve(opath) if opath else idb
            cur = getattr(owner, attr)
        except Exception:
            continue
        if hasattr(cur, "__len__"):
            c2 = list(cur); c2[fc.array_index] = val; setattr(owner, attr, c2)
        else:
            setattr(owner, attr, val)
    ad.action = None
_w = sc.world
for _o in (_w, _w.node_tree, bpy.data.objects["sun"], bpy.data.objects["sun"].data, bpy.data.objects["fill"], bpy.data.objects["fill"].data):
    _freeze(_o)
FPS = 30; NF = 900
sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
random.seed(7)

# ------------------------------------------------------------------ cleanup of the old film ---------------------------
OLD = ("g0_", "bbq_", "pile_")
for o in list(bpy.data.objects):
    if o.name.startswith(OLD) or o.name in ("carton", "carton_label_front", "carton_label_top"):
        bpy.data.objects.remove(o, do_unlink=True)
MESH = {n: bpy.data.meshes[n] for n in ("stopa", "trojak", "mb2")}
M = lambda *names: next((bpy.data.materials[n] for n in names if n in bpy.data.materials), None)
MET = M("metal_RAL9005", "metal_RAL9005_fade")
TIMB = [m for m in (M("timber0", "timber0_fade"), M("timber1", "timber1_fade"), M("timber3", "timber3_fade"), M("timber6", "timber6_fade")) if m]
ROOFM = M("roof_RAL7016", "roof_RAL7016_fade")
KRAFT = M("kraft"); LABEL = M("carton_label")
print("materials:", MET and MET.name, [m.name for m in TIMB], ROOFM and ROOFM.name, KRAFT and KRAFT.name, LABEL and LABEL.name)

# ------------------------------------------------------------------ helpers --------------------------------------------
def pmat(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color; b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        if k in b.inputs: b.inputs[k].default_value = v
    return m

def decal_mat(name, path):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    import os; im = bpy.data.images.load(os.path.abspath(path)); im.pack(); tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = im; tex.extension = 'CLIP'
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.35
    nt.links.new(tex.outputs["Alpha"], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bsdf.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0]); return m

PAINT = pmat("van_paint", (0.86, 0.87, 0.88, 1), 0.22, 0.0, **{"Coat Weight": 0.9, "Coat Roughness": 0.04})
TRIM = pmat("van_trim", (0.025, 0.027, 0.03, 1), 0.55)
GLASS = pmat("van_glass", (0.02, 0.03, 0.035, 1), 0.04, 0.0, **{"Coat Weight": 0.5})
TIRE = pmat("van_tire", (0.012, 0.012, 0.013, 1), 0.85)
RIM = pmat("van_rim", (0.62, 0.63, 0.65, 1), 0.28, 1.0)
LINING = pmat("van_lining", (0.36, 0.37, 0.38, 1), 0.7)
FLOORM = pmat("van_floor", (0.12, 0.12, 0.12, 1), 0.8)
LAMP = pmat("van_lamp", (0.9, 0.93, 0.95, 1), 0.08, 0.0, **{"Coat Weight": 0.4})
RACK = pmat("van_rack", (0.18, 0.18, 0.19, 1), 0.5, 0.8)
DEC_DARK = decal_mat("decal_dark", "van_decal_dark.png")
DEC_WHITE = decal_mat("decal_white", "van_decal_white.png")

COLL = sc.collection
def link(o, parent=None):
    COLL.objects.link(o)
    if parent: o.parent = parent
    return o

def bm_obj(name, bm, mats, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    for p in me.polygons: p.use_smooth = False
    return link(o, parent)

def box(name, sx, sy, sz, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    if bevel: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES')
    return bm_obj(name, bm, [mat], parent, loc, rot)

def cyl(name, r, depth, mat, loc, rot=(0, 0, 0), parent=None, seg=40):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    return bm_obj(name, bm, [mat], parent, loc, rot)

def extrude_profile(name, pts, y0, y1, mat, parent=None, bevel=0.0):
    bm = bmesh.new(); vs = [bm.verts.new((x, y0, z)) for x, z in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); vv = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, y1 - y0, 0), verts=vv); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bevel: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES')
    return bm_obj(name, bm, [mat], parent)

def quad(name, p, mat, parent=None):
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in p]; bm.faces.new(vs)
    return bm_obj(name, bm, [mat], parent)

def boolean_cut(target, cutters):
    for c in cutters:
        md = target.modifiers.new("cut", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = c; md.solver = 'EXACT'
    bpy.context.view_layer.update()
    ev = target.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = bpy.data.meshes.new_from_object(ev); old = target.data
    target.modifiers.clear(); target.data = me; bpy.data.meshes.remove(old)
    for c in cutters: bpy.data.objects.remove(c, do_unlink=True)

def ease(u): u = max(0.0, min(1.0, u)); return u * u * u * (u * (u * 6 - 15) + 10)   # smootherstep
def lerp(a, b, t): return a + (b - a) * t

def cr(pts, u):
    """uniform Catmull-Rom through pts, u in 0..1"""
    n = len(pts) - 1; t = u * n; i = min(int(t), n - 1); f = t - i
    p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, n)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)

def key(o, f, loc=None, quat=None, euler=None):
    if loc is not None: o.location = loc; o.keyframe_insert("location", frame=f)
    if quat is not None: o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = quat; o.keyframe_insert("rotation_quaternion", frame=f)
    if euler is not None: o.rotation_mode = 'XYZ'; o.rotation_euler = euler; o.keyframe_insert("rotation_euler", frame=f)

def linear_keys(o):
    ad = o.animation_data
    if not ad or not ad.action: return
    for fc in ad.action.fcurves if hasattr(ad.action, "fcurves") else _fcurves(ad.action):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def _fcurves(action):
    out = []
    for l in action.layers:
        for s in l.strips:
            for cb in s.channelbags: out += list(cb.fcurves)
    return out

# ============================================================== THE VAN ===================================================
# local frame: +X forward, +Y left, +Z up, origin on the ground under the middle of the van.  Length 6.4, width 2.0, height 2.75
VAN = bpy.data.objects.new("van", None); VAN.empty_display_type = 'PLAIN_AXES'; link(VAN)
vp = VAN
CX0, CX1 = -3.2, 1.15      # cargo x range
WZ0, FZ = 0.72, 0.72       # cargo floor height
TOP = 2.75
# lower sill (black plastic cladding), with wheel arches
sill = box("sill", 6.4, 1.98, 0.34, TRIM, (0, 0, 0.57), parent=vp, bevel=0.03)
# cab + hood solid
cab_pts = [(1.15, 0.40), (3.2, 0.40), (3.2, 0.98), (3.10, 1.13), (2.55, 1.25), (1.74, 2.30), (1.64, TOP - 0.02), (1.15, TOP - 0.02)]
cab = extrude_profile("cab", cab_pts, -0.98, 0.98, PAINT, vp, bevel=0.02)
WHEELS = [(2.25, 0.89), (2.25, -0.89), (-1.95, 0.89), (-1.95, -0.89)]
cut1 = [cyl("cut_a%d" % i, 0.47, 0.5, TRIM, (x, y * 1.08, 0.37), (math.pi / 2, 0, 0), parent=None) for i, (x, y) in enumerate(WHEELS)]
for c in cut1: c.parent = vp
for c in cut1: c.matrix_parent_inverse = Matrix.Identity(4)
boolean_cut(sill, [c for c in cut1[2:]]); boolean_cut(cab, [c for c in cut1[:2]])
# cargo box: lining + outside walls + roof + floor + front bulkhead (rear is open)
box("floor", CX1 - CX0, 1.92, 0.06, FLOORM, ((CX0 + CX1) / 2, 0, WZ0 - 0.03), parent=vp)
for s, nm in ((1, "L"), (-1, "R")):
    box("wallout" + nm, CX1 - CX0, 0.03, TOP - WZ0, PAINT, ((CX0 + CX1) / 2, s * 0.985, (TOP + WZ0) / 2), parent=vp, bevel=0.008)
    box("wallin" + nm, CX1 - CX0, 0.02, TOP - WZ0 - 0.08, LINING, ((CX0 + CX1) / 2, s * 0.955, (TOP + WZ0) / 2 - 0.02), parent=vp)
box("roofout", CX1 - CX0, 2.0, 0.04, PAINT, ((CX0 + CX1) / 2, 0, TOP - 0.02), parent=vp, bevel=0.012)
box("roofin", CX1 - CX0, 1.92, 0.02, LINING, ((CX0 + CX1) / 2, 0, TOP - 0.05), parent=vp)
box("bulkhead", 0.04, 1.92, TOP - WZ0 - 0.05, LINING, (CX1 - 0.02, 0, (TOP + WZ0) / 2 - 0.02), parent=vp)
# glass
n = Vector((0.79, 0.62)); n.normalize()
quad("windshield", [(2.55 + n.x * 0.012, -0.84, 1.25 + n.y * 0.012), (2.55 + n.x * 0.012, 0.84, 1.25 + n.y * 0.012),
                    (1.745 + n.x * 0.012, 0.84, 2.27 + n.y * 0.012), (1.745 + n.x * 0.012, -0.84, 2.27 + n.y * 0.012)], GLASS, vp)
for s in (1, -1):
    quad("sidewin%d" % s, [(2.36, s * 0.987, 1.40), (1.80, s * 0.987, 2.24), (1.28, s * 0.987, 2.24), (1.28, s * 0.987, 1.40)], GLASS, vp)
# grille, headlights, bumper, mirrors, lamps
box("grille", 0.03, 1.1, 0.38, TRIM, (3.205, 0, 0.82), parent=vp, bevel=0.01)
for s in (1, -1):
    box("headlight%d" % s, 0.05, 0.34, 0.16, LAMP, (3.17, s * 0.75, 1.02), parent=vp, bevel=0.02)
    box("mirror%d" % s, 0.10, 0.07, 0.26, TRIM, (2.12, s * 1.1, 1.62), parent=vp, bevel=0.02)
    box("mirrorarm%d" % s, 0.05, 0.14, 0.04, TRIM, (2.12, s * 1.02, 1.74), parent=vp)
    box("taillamp%d" % s, 0.04, 0.12, 0.45, pmat("tail%d" % s, (0.5, 0.02, 0.02, 1), 0.2), (-3.2, s * 0.96, 1.0), parent=vp)
box("bumperF", 0.2, 2.0, 0.26, TRIM, (3.12, 0, 0.55), parent=vp, bevel=0.03)
box("bumperR", 0.18, 2.0, 0.22, TRIM, (-3.2, 0, 0.5), parent=vp, bevel=0.03)
box("step", 0.3, 1.5, 0.05, TRIM, (-3.3, 0, 0.45), parent=vp)
# wheels (spin around local Y)
WH = []
for i, (x, y) in enumerate(WHEELS):
    piv = bpy.data.objects.new("wheelpiv%d" % i, None); piv.location = (x, y, 0.37); link(piv, vp)
    cyl("tire%d" % i, 0.37, 0.24, TIRE, (0, 0, 0), (math.pi / 2, 0, 0), piv)
    cyl("rim%d" % i, 0.25, 0.245, RIM, (0, 0.0 if y > 0 else 0.0, 0), (math.pi / 2, 0, 0), piv)
    for k in range(5):  # lug nuts
        a = k * 2 * math.pi / 5; cyl("lug%d_%d" % (i, k), 0.022, 0.26, TRIM, (0.1 * math.cos(a), 0, 0.1 * math.sin(a)), (math.pi / 2, 0, 0), piv, seg=10)
    WH.append(piv)
# RIVON side decals (black wordmark on white paint)
dw, dh = 2.9, 2.9 * 206 / 1078
d_r = quad("decalR", [(-dw / 2, 0, -dh / 2), (dw / 2, 0, -dh / 2), (dw / 2, 0, dh / 2), (-dw / 2, 0, dh / 2)], DEC_DARK, vp)
bm = d_r.data; uv = bm.uv_layers.new(name="UVMap")
for l, (u, v) in zip(bm.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[l.index].uv = (u, v)
d_r.location = (-1.0, -1.006, 1.7); d_r.rotation_euler = (0, 0, 0)
d_l = quad("decalL", [(-dw / 2, 0, -dh / 2), (dw / 2, 0, -dh / 2), (dw / 2, 0, dh / 2), (-dw / 2, 0, dh / 2)], DEC_DARK, vp)
bm = d_l.data; uv = bm.uv_layers.new(name="UVMap")
for l, (u, v) in zip(bm.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[l.index].uv = (u, v)
d_l.location = (-1.0, 1.006, 1.7); d_l.rotation_euler = (0, 0, math.pi)
# rear doors on vertical pivots
DOORS = []
for s, nm in ((1, "L"), (-1, "R")):
    piv = bpy.data.objects.new("doorpiv" + nm, None); piv.location = (-3.22, s * 1.0, 0.0); link(piv, vp)
    box("door" + nm, 0.05, 0.98, 1.95, PAINT, (-0.0, -s * 0.49, 1.74), parent=piv, bevel=0.01)
    box("doorin" + nm, 0.02, 0.9, 1.85, LINING, (0.035, -s * 0.49, 1.74), parent=piv)
    quad("doorwin" + nm, [(-0.027, -s * 0.2, 1.9), (-0.027, -s * 0.78, 1.9), (-0.027, -s * 0.78, 2.5), (-0.027, -s * 0.2, 2.5)], GLASS, piv)
    DOORS.append((piv, s))
# cargo racks
box("rackL", 3.9, 0.5, 0.03, RACK, (-1.05, 0.72, 1.5), parent=vp)
box("rackR", 3.9, 0.5, 0.03, RACK, (-1.05, -0.62, 1.5), parent=vp)
box("rackT", 3.9, 0.85, 0.03, RACK, (-1.05, 0, 2.08), parent=vp)
for xx in (-3.0, -1.0, 0.9):
    for yy in (0.93, -0.93):
        box("rackpost", 0.04, 0.04, 1.4, RACK, (xx, yy, 1.4), parent=vp)

# ------------------------------------------------------------------ extra van detail --------------------------------------
CHROME = RIM
ORANGE = pmat("van_orange", (0.95, 0.38, 0.02, 1), 0.2)
PLATE = pmat("van_plate", (0.92, 0.92, 0.9, 1), 0.4)
RUBBER = pmat("van_rubber", (0.02, 0.02, 0.022, 1), 0.9)
DRL = pmat("van_drl", (1, 1, 1, 1), 0.1, 0.0, **{"Emission Color": (1, 1, 1, 1), "Emission Strength": 9.0})
DOME = pmat("van_dome", (1, 0.92, 0.78, 1), 0.3, 0.0, **{"Emission Color": (1, 0.9, 0.72, 1), "Emission Strength": 7.0})
for s in (1, -1):
    # body belt line + panel seams on the cargo box, cab door outline and handles
    box("belt%d" % s, 4.35, 0.008, 0.016, TRIM, (-1.025, s * 1.003, 1.12), parent=vp)
    box("beltlow%d" % s, 4.35, 0.008, 0.012, TRIM, (-1.025, s * 1.003, 0.9), parent=vp)
    for xx in (-1.75, -0.30):
        box("seam%d" % s, 0.012, 0.008, TOP - WZ0 - 0.05, TRIM, (xx, s * 1.003, (TOP + WZ0) / 2), parent=vp)
    box("cabseamR%d" % s, 0.012, 0.008, 1.85, TRIM, (1.30, s * 0.992, 1.55), parent=vp)
    box("cabseamF%d" % s, 0.012, 0.008, 0.70, TRIM, (2.50, s * 0.992, 1.0), parent=vp)
    box("cabseamB%d" % s, 1.22, 0.008, 0.012, TRIM, (1.90, s * 0.992, 0.66), parent=vp)
    box("cabhandle%d" % s, 0.14, 0.03, 0.03, CHROME, (1.48, s * 1.0, 1.26), parent=vp, bevel=0.008)
    box("fuelcap%d" % s, 0.01, 0.1, 0.1, TRIM, (1.62, s * 0.99, 0.98), parent=vp) if s == 1 else None
    for xx in (-3.12, 1.05):
        box("marker%d" % s, 0.07, 0.012, 0.03, ORANGE, (xx, s * 1.004, 1.5), parent=vp, bevel=0.004)
    # mirror glass, DRL, fog lamps
    box("mirrorglass%d" % s, 0.008, 0.075, 0.22, GLASS, (2.066, s * 1.1, 1.62), parent=vp)
    box("drl%d" % s, 0.012, 0.30, 0.022, DRL, (3.205, s * 0.75, 1.145), parent=vp)
    cyl("fog%d" % s, 0.055, 0.02, LAMP, (3.225, s * 0.72, 0.52), (0, math.pi / 2, 0), vp, seg=20)
    cyl("fogring%d" % s, 0.065, 0.015, TRIM, (3.218, s * 0.72, 0.52), (0, math.pi / 2, 0), vp, seg=20)
    # wipers
    box("wiper%d" % s, 0.012, 0.55, 0.014, TRIM, (2.47, s * 0.35 - 0.0, 1.39), (0, 0, s * 0.14), parent=vp)
    # door hinges (rear) and mud flaps
    for zz in (0.62, 1.4, 2.25):
        box("hinge%d" % s, 0.05, 0.05, 0.14, TRIM, (-3.235, s * 1.012, zz), parent=vp)
    box("mudflap%d" % s, 0.02, 0.3, 0.3, RUBBER, (-2.45, s * 0.88, 0.3), parent=vp)
    box("mudflapF%d" % s, 0.02, 0.28, 0.26, RUBBER, (1.62, s * 0.9, 0.3), parent=vp)
    # wheel-arch flares
    for xx in (2.25, -1.95):
        box("flare%d" % s, 1.0, 0.045, 0.035, RUBBER, (xx, s * 1.0, 0.86), parent=vp)
    # interior cargo rails
    for zz in (1.0, 1.85):
        box("erail%d" % s, 4.25, 0.012, 0.035, RACK, (-1.025, s * 0.941, zz), parent=vp)
# front: grille slats, badge, plate
for k in range(5):
    box("slat%d" % k, 0.012, 1.08, 0.016, CHROME, (3.222, 0, 0.68 + k * 0.075), parent=vp)
cyl("badge", 0.075, 0.012, PLATE, (3.226, 0, 0.99), (0, math.pi / 2, 0), vp, seg=28)
box("platefrontb", 0.012, 0.56, 0.14, TRIM, (3.224, 0, 0.50), parent=vp, bevel=0.004)
box("platefront", 0.014, 0.52, 0.11, PLATE, (3.228, 0, 0.50), parent=vp)
box("plateraer", 0.014, 0.52, 0.11, PLATE, (-3.298, 0, 0.5), parent=vp)
box("platerearb", 0.012, 0.56, 0.14, TRIM, (-3.296, 0, 0.5), parent=vp, bevel=0.004)
box("hood_crease", 0.012, 1.4, 0.012, TRIM, (3.15, 0, 1.12), parent=vp)
box("visor", 0.28, 1.7, 0.04, TRIM, (1.72, 0, 2.30), parent=vp, bevel=0.01)
box("roofvent", 0.55, 0.38, 0.08, PAINT, (-1.9, 0, TOP + 0.04), parent=vp, bevel=0.02)
cyl("antenna", 0.007, 0.35, TRIM, (1.45, 0.4, TOP + 0.17), (0, 0, 0), vp, seg=8)
box("domelight", 3.4, 0.10, 0.025, DOME, (-1.0, 0, TOP - 0.07), parent=vp)
# wheel details: slotted face, hub, tread blocks
for w in WH:
    for sgn in (1, -1):
        cyl("hub", 0.075, 0.03, CHROME, (0, sgn * 0.125, 0), (math.pi / 2, 0, 0), w, seg=24)
        for k in range(8):
            a = k * math.pi / 4
            cyl("slot", 0.032, 0.012, TRIM, (0.165 * math.cos(a), sgn * 0.123, 0.165 * math.sin(a)), (math.pi / 2, 0, 0), w, seg=12)
    for k in range(28):
        a = k * 2 * math.pi / 28
        box("tread", 0.05, 0.236, 0.02, TIRE, (0.375 * math.cos(a), 0, 0.375 * math.sin(a)), (0, -(a + math.pi / 2), 0), w)
# rear door exterior: logos, handles, rubber seal
for piv, s in DOORS:
    c = -s * 0.49
    hw, hh = 0.4, 0.4 * 206 / 1078
    q = quad("doorlogo", [(-0.0275, c + hw, 1.25 - hh), (-0.0275, c - hw, 1.25 - hh), (-0.0275, c - hw, 1.25 + hh), (-0.0275, c + hw, 1.25 + hh)], DEC_DARK, piv)
    uvl = q.data.uv_layers.new(name="UVMap")
    for l, (u, v) in zip(q.data.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): uvl.data[l.index].uv = (u, v)
    box("doorhandle", 0.03, 0.03, 0.34, CHROME, (-0.05, -s * 0.12, 1.0), parent=piv, bevel=0.008)
    box("doorseal", 0.02, 0.02, 1.9, RUBBER, (-0.03, -s * 0.97, 1.74), parent=piv)
    box("doorstrip", 0.012, 0.9, 0.03, TRIM, (-0.03, -s * 0.49, 0.85), parent=piv)

# ------------------------------------------------------------------ van path -------------------------------------------
STOP = Vector((9.25, 11.2, 0.0))          # centre of the parked van, heading -Y  (front bumper at y~8)
R = 6.65; S1 = 12.0; ARC = R * math.pi / 2; S3 = 33.95 - STOP.y
TOTAL = S1 + ARC + S3
def van_pose(s):
    s = max(0.0, min(TOTAL, s))
    if s <= S1: return Vector((9.25 - R - S1 + s, 40.6, 0)), 0.0
    if s <= S1 + ARC:
        ph = (s - S1) / R; cxy = Vector((9.25 - R, 40.6 - R))
        return Vector((cxy.x + R * math.sin(ph), cxy.y + R * math.cos(ph), 0)), -ph
    return Vector((9.25, 33.95 - (s - S1 - ARC), 0)), -math.pi / 2
T_DRIVE = 185
VAN_POS = {}
for f in range(1, T_DRIVE + 1):
    u = (f - 1) / (T_DRIVE - 1); s = TOTAL * (1 - (1 - u) ** 1.8)
    p, h = van_pose(s); key(VAN, f, loc=p, euler=(0, 0, h)); VAN_POS[f] = p
    for w in WH: key(w, f, euler=(0, s / 0.37, 0))
key(VAN, T_DRIVE + 1, loc=van_pose(TOTAL)[0], euler=(0, 0, -math.pi / 2)); key(VAN, NF, loc=van_pose(TOTAL)[0], euler=(0, 0, -math.pi / 2))
for w in WH: key(w, T_DRIVE + 1, euler=(0, TOTAL / 0.37, 0)); key(w, NF, euler=(0, TOTAL / 0.37, 0))
# front wheels steer during the turn is skipped (they are hidden in the arches).  Doors open
T_DOOR = 192
for piv, s in DOORS:
    key(piv, 1, euler=(0, 0, 0)); key(piv, T_DOOR, euler=(0, 0, 0)); key(piv, T_DOOR + 32, euler=(0, 0, -s * math.radians(100)))
    key(piv, NF, euler=(0, 0, -s * math.radians(100)))
VAN_M = Matrix.Translation(STOP) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')   # world matrix of the parked van

def van_to_world(p): return VAN_M @ Vector(p)

# ============================================================== GAZEBO PLAN ==============================================
AX, AY = -5.1, 0.6
LEG, ARMW = 3.8, 2.2
P = {"A": (AX, AY), "B": (AX + LEG, AY), "C": (AX + LEG, AY + ARMW), "D": (AX + ARMW, AY + ARMW), "E": (AX + ARMW, AY + LEG), "F": (AX, AY + LEG)}
TYPE = {"A": "SW", "B": "SE", "C": "NE", "D": "SW", "E": "NE", "F": "NW"}
ORDER = "ABCDEF"
BEAMS = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "F"), ("F", "A")]
Z_POST_TOP, Z_CONN, Z_BEAM = 2.3, 2.303, 2.353
STOPA_OFF = {"SW": (0.05, 0.05, math.pi), "SE": (0.05, 0.05, math.pi), "NE": (-0.05, -0.05, 0.0), "NW": (-0.05, -0.05, 0.0)}
TROJ = {"SW": ((-0.05, 0.05), (math.pi, 0, 0)), "SE": ((-0.05, -0.05), (math.pi, 0, math.pi / 2)),
        "NE": ((0.05, -0.05), (0, math.pi, 0)), "NW": ((0.05, 0.05), (math.pi, 0, -math.pi / 2))}

# ------------------------------------------------------------------ flight machinery ----------------------------------
class Item:
    def __init__(self, obj, start_loc, start_quat, end_loc, end_quat, f0, dur, via=None, hold_inside=None):
        self.o = obj; self.p0 = Vector(start_loc); self.q0 = Quaternion(start_quat); self.p1 = Vector(end_loc); self.q1 = Quaternion(end_quat)
        self.f0 = f0; self.dur = dur; self.via = [Vector(v) for v in (via or [])]
    def pose(self, f):
        u = (f - self.f0) / self.dur
        if u <= 0: return self.p0, self.q0
        if u >= 1: return self.p1, self.q1
        e = ease(u); pts = [self.p0] + self.via + [self.p1]
        pts = [pts[0]] + pts + [pts[-1]] if False else pts
        return cr(pts, e), self.q0.slerp(self.q1, e)
    def bake(self, skip1=False):
        o = self.o; f_first, f_last = self.f0, self.f0 + self.dur
        if not skip1:
            p, q = self.pose(1); key(o, 1, loc=p, quat=q)
        p, q = self.pose(f_first); key(o, f_first, loc=p, quat=q)
        for f in range(f_first + 1, f_last):
            p, q = self.pose(f); key(o, f, loc=p, quat=q)
        key(o, f_last, loc=self.p1, quat=self.q1); key(o, NF, loc=self.p1, quat=self.q1)

def quat(e): return Euler(e, 'XYZ').to_quaternion()

def exit_via(start_w, dest, lift=1.0, up=3.8):
    """world-space waypoints: out of the rear doors (van rear faces +Y), up and over the van, then down to the destination"""
    s = Vector(start_w); d = Vector(dest)
    rear = Vector((STOP.x, STOP.y + 3.2 + 1.6, max(s.z, 1.2) + 0.3))
    top = Vector((STOP.x - 1.2, STOP.y + 2.2, up))
    mid = top.lerp(d + Vector((0, 0, up * 0.55)), 0.55) + Vector((-1.5, -0.5, 0))
    near = d + Vector((0, 0, lift))
    return [Vector((s.x, s.y + 0.0, s.z)).lerp(rear, 0.35), rear, top, mid, near]

ITEMS = []
def add_item(obj, start_loc, start_quat, end_loc, end_quat, f0, dur, via):
    it = Item(obj, start_loc, start_quat, end_loc, end_quat, f0, dur, via); ITEMS.append(it); return it

# ------------------------------------------------------------------ cartons -------------------------------------------
def make_carton(name, dx, dy, dz):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= dx; v.co.y *= dy; v.co.z *= dz
    top = [f for f in bm.faces if f.normal.z > 0.5]; bmesh.ops.delete(bm, geom=top, context='FACES')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.008)
    body = bm_obj(name, bm, [KRAFT])
    flaps = []
    for k, (ax, sgn) in enumerate((("x", 1), ("x", -1), ("y", 1), ("y", -1))):
        if ax == "x": hinge = (0, sgn * dy / 2, dz / 2)
        else:         hinge = (sgn * dx / 2, 0, dz / 2)
        piv = bpy.data.objects.new(name + "_hinge%d" % k, None); piv.location = hinge; link(piv, body)
        if ax == "x": box(name + "_flap%d" % k, dx, dy / 2, 0.006, KRAFT, (0, -sgn * dy / 4, 0), parent=piv)
        else:         box(name + "_flap%d" % k, dx / 2, dy, 0.006, KRAFT, (-sgn * dx / 4, 0, 0.001), parent=piv)
        flaps.append((piv, ax, sgn))
    lab = quad(name + "_label", [(-dx * 0.3, -dy / 2 - 0.002, -dz * 0.3), (dx * 0.3, -dy / 2 - 0.002, -dz * 0.3), (dx * 0.3, -dy / 2 - 0.002, dz * 0.3), (-dx * 0.3, -dy / 2 - 0.002, dz * 0.3)], LABEL, body)
    uv = lab.data.uv_layers.new(name="UV")
    for l, (u, v) in zip(lab.data.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[l.index].uv = (u, v)
    return body, flaps

CARTONS = {}
CARTON_SPEC = {"A": (0.45, 0.55, 0.30), "B": (0.65, 0.95, 0.30), "C": (0.45, 0.40, 0.34)}
CARTON_VAN = {"A": (-2.8, -0.55), "B": (-2.7, 0.35), "C": (-2.0, -0.55)}
CARTON_LAND = {"A": ((-3.55, -1.3), 0.3), "B": ((-2.6, -1.5), -0.15), "C": ((-1.6, -1.0), 0.1)}   # world x,y ; yaw
CARTON_T = {"B": 236, "A": 252, "C": 268}
for k, (dx, dy, dz) in CARTON_SPEC.items():
    body, flaps = make_carton("carton" + k, dx, dy, dz)
    CARTONS[k] = (body, flaps, dz)
    vx, vy = CARTON_VAN[k]; sw = van_to_world((vx, vy, FZ + dz / 2 + 0.01))
    (lx, ly), yaw = CARTON_LAND[k]; dest = Vector((lx, ly, dz / 2 + 0.01))
    it = add_item(body, sw, quat((0, 0, -math.pi / 2)), dest, quat((0, 0, yaw)), CARTON_T[k], 52, exit_via(sw, dest, lift=0.8, up=3.6))
    CARTONS[k] = (body, flaps, dz, it, dest, yaw)

# flaps: open after landing
T_OPEN = 322
for k, (body, flaps, dz, it, dest, yaw) in CARTONS.items():
    for piv, ax, sgn in flaps:
        ang = math.radians(115) if ax == "x" else math.radians(105)
        if ax == "x":   e = (-sgn * ang, 0, 0)
        else:           e = (0, sgn * ang, 0)
        key(piv, 1, euler=(0, 0, 0)); key(piv, T_OPEN + (0 if ax == "x" else 6), euler=(0, 0, 0)); key(piv, T_OPEN + 22 + (0 if ax == "x" else 6), euler=e); key(piv, NF, euler=e)

def carton_pose(k, f):
    body, flaps, dz, it, dest, yaw = CARTONS[k]; p, q = it.pose(f); return p, q

# ------------------------------------------------------------------ gazebo parts --------------------------------------
def tmat(): return random.choice(TIMB)
def stand_items():
    d = {}
    return d

corner_t = {}   # frame at which the corner's trojak has landed
TROJ_OBJ = {}; STOPA_OBJ = {}; POST_OBJ = {}
OFF_A = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
slot_a = lambda i: Vector(((i % 3 - 1) * 0.14, (i // 3 - 0.5) * 0.18, 0.0))     # six stopas in a 3x2 grid in carton A
slot_b = lambda i: Vector(((i // 3 - 0.5) * 0.31 - 0.15, (i % 3 - 1) * 0.31 + 0.05, -0.0))             # six trojaks in a 3x2 grid in carton B
cart_inside = lambda k, loc_off, quat_local: None
def inside_start(k, off, qloc, t):
    """pose (world) of an object riding in carton k at frame t"""
    p, q = carton_pose(k, t); return p + q @ off, q @ qloc

for idx, c in enumerate(ORDER):
    s0 = 344 + 18 * idx
    px, py = P[c]; ty = TYPE[c]
    # stopa
    so = bpy.data.objects.new("stopa_" + c, MESH["stopa"]); so.data.materials.clear() if False else None
    link(so); so.rotation_mode = 'QUATERNION'
    ox, oy, rz = STOPA_OFF[ty]
    endloc = Vector((px + ox, py + oy, 0.0)); endq = quat((0, 0, rz))
    # stopa mesh origin is at its base corner; ride in carton A (its z extent 0..0.152)
    st_off = slot_a(idx) + Vector((-0.05, -0.05, -0.04)); st_q = quat((0, 0, 0))
    sp0, sq0 = inside_start("A", st_off, st_q, s0)
    via = [Vector((px, py, 0)) + Vector((0, 0, 0)) * 0]
    start_w = sp0
    mid = start_w + Vector((0, 0, 1.3)); mid2 = Vector((lerp(start_w.x, endloc.x, 0.5), lerp(start_w.y, endloc.y, 0.5), 2.6)); near = endloc + Vector((0, 0, 0.5))
    it = Item(so, start_w, sq0, endloc, endq, s0, 40, [mid, mid2, near]); ITEMS.append(it); STOPA_OBJ[c] = it
    # post
    pm = tmat()
    po = box("post_" + c, 0.09, 0.09, 2.3, pm, (0, 0, 0)); po.rotation_mode = 'QUATERNION'
    pend = Vector((px, py, 1.15)); pstart = van_to_world((-0.6, 0.82 - (idx % 2) * 0.1, 0.77 + (idx // 2) * 0.09))
    # posts leave the van like the others, ride stacked horizontally
    vq = Quaternion((VAN_M.to_quaternion())) @ quat((0, math.pi / 2, 0))
    pvia = exit_via(pstart, pend + Vector((0, 0, 1.4)), lift=0.0, up=4.2)
    it = Item(po, pstart, vq, pend, quat((0, 0, 0)), s0 + 8, 46, pvia[:-1] + [pend + Vector((0, 0, 0.9))]); ITEMS.append(it); POST_OBJ[c] = it
    # trojak
    to = bpy.data.objects.new("trojak_" + c, MESH["trojak"]); link(to); to.rotation_mode = 'QUATERNION'
    (tx, ty2), er = TROJ[ty]
    tend = Vector((px + tx, py + ty2, Z_CONN)); tq = quat(er)
    tp0, tq0 = inside_start("B", slot_b(idx) + Vector((-0.0, -0.0, 0.0)), quat((0, 0, 0)), s0 + 22)
    tvia = [tp0 + Vector((0, 0, 1.2)), Vector((lerp(tp0.x, tend.x, 0.5), lerp(tp0.y, tend.y, 0.5), 3.4)), tend + Vector((0, 0, 0.6))]
    it = Item(to, tp0, tq0, tend, tq, s0 + 22, 38, tvia); ITEMS.append(it); TROJ_OBJ[c] = it
    corner_t[c] = s0 + 22 + 38

# wooden terrace floor (L-shaped decking laid on the existing paving, already there when the van arrives)
DK_BW, DK_GAP, DK_T = 0.14, 0.006, 0.035
y_lo_d, y_hi_d = AY - 0.18, AY + 3.8 + 0.18
nb = int((y_hi_d - y_lo_d) / (DK_BW + DK_GAP))
for i in range(nb):
    yc = y_lo_d + DK_BW / 2 + i * (DK_BW + DK_GAP)
    x_lo = AX - 0.18; x_hi = AX + (3.8 if yc < AY + 2.2 + 0.02 else 2.2) + 0.18
    mt = TIMB[i % len(TIMB)] if TIMB else None
    box("deck%02d" % i, x_hi - x_lo, DK_BW, DK_T, mt, ((x_lo + x_hi) / 2, yc, DK_T / 2 + 0.001))

# beams between posts
BEAM_OBJ = []
for bi, (a, b) in enumerate(BEAMS):
    pa, pb = Vector(P[a] + (0,)), Vector(P[b] + (0,)); L = (pb - pa).length - 0.1; mid = (pa + pb) / 2
    f0 = max(corner_t[a], corner_t[b]) - 22
    bo = box("beam_%s%s" % (a, b), 0.09, 0.09, L, tmat(), (0, 0, 0)); bo.rotation_mode = 'QUATERNION'
    along_x = abs(pb.x - pa.x) > 1e-6
    endq = quat((0, math.pi / 2, 0)) if along_x else quat((-math.pi / 2, 0, 0))   # box long axis is Z -> turn onto X or Y
    endloc = Vector((mid.x, mid.y, Z_BEAM))
    slot = [(0.84, 1.56), (0.75, 1.56), (0.66, 1.56), (0.84, 1.65), (0.75, 1.65), (0.66, 1.65)][bi]
    sw = van_to_world((-3.0 + L / 2 - 0.0, slot[0], slot[1]))
    sq = VAN_M.to_quaternion() @ quat((0, math.pi / 2, 0))
    via = exit_via(sw, endloc + Vector((0, 0, 0.3)), lift=0.0, up=4.0)
    it = Item(bo, sw, sq, endloc, endq, f0 + bi * 0, 42, via[:-1] + [endloc + Vector((0, 0, 0.5))]); ITEMS.append(it); BEAM_OBJ.append((it, f0 + 42))
beams_done = max(t for _, t in BEAM_OBJ)

mount_slot = lambda n: Vector((((n % 8) % 4 - 1.5) * 0.105 - 0.05, (((n % 8) // 4) - 0.5) * 0.115 - 0.055, -0.17 + (n // 8) * 0.152))
# rafters (along Y) + hanger mounts (mb2)
def mount_obj():
    o = bpy.data.objects.new("mb2", MESH["mb2"]); link(o); o.rotation_mode = 'QUATERNION'; return o
XL = [0.45, 0.9, 1.35, 1.75]; XS = [2.65, 3.05, 3.4]
RAF = [(x, 0.0, LEG, "long") for x in XL] + [(x, 0.0, ARMW, "short") for x in XS]
for ri, (xo, _, span, kind) in enumerate(RAF):
    xr = AX + xo; y_lo = AY + 0.045; y_hi = AY + span - 0.045
    gap = y_hi - y_lo; L = gap - 0.006
    f0 = 470 + ri * 8
    ro = box("rafter_%d" % ri, 0.045, L, 0.098, tmat(), (0, 0, 0)); ro.rotation_mode = 'QUATERNION'
    endloc = Vector((xr, (y_lo + y_hi) / 2, 2.349)); endq = quat((0, 0, 0))
    slot = ri
    sw = van_to_world((-3.0 + L / 2, -0.40 - 0.05 * slot, 1.58)); sq = VAN_M.to_quaternion() @ quat((math.pi / 2, 0, 0)) @ quat((0, 0, 0))
    sq = VAN_M.to_quaternion() @ quat((0, 0, math.pi / 2 * 0))
    # the rafter is a box with its LONG axis along local Y -> starts lying along the van (van X axis == world -Y when parked) : needs a Z yaw of 90deg in van frame
    sq = VAN_M.to_quaternion() @ quat((0, 0, math.pi / 2))
    via = exit_via(sw, endloc + Vector((0, 0, 0.5)), lift=0.0, up=4.0)
    it = Item(ro, sw, sq, endloc, endq, f0, 40, via[:-1] + [endloc + Vector((0, 0, 0.5))]); ITEMS.append(it)
    # two mounts per rafter: near end (low y) and far end (high y)
    for end in (0, 1):
        mo = mount_obj()
        if end == 0:
            mloc = Vector((xr + 0.055, y_lo - 0.0 + 0.0, 2.398)); mq = quat((0, math.pi / 2, math.pi / 2))
        else:
            mloc = Vector((xr - 0.055, y_hi + 0.0, 2.398)); mq = quat((math.pi, math.pi / 2, math.pi / 2))
        slot_m = (ri * 2 + end)
        mstart_c = Vector((0.0, 0.0, 0.0))
        cp, cq = inside_start("C", mount_slot(slot_m), quat((0, 0, 0)), f0 - 18)
        mvia = [cp + Vector((0, 0, 1.2)), Vector((lerp(cp.x, mloc.x, 0.5), lerp(cp.y, mloc.y, 0.5), 3.2)), mloc + Vector((0, 0, 0.5))]
        mit = Item(mo, cp, quat((0, 0, 0)), mloc, mq, f0 - 18 + end * 2, 40, mvia); ITEMS.append(mit)

# roof slats (graphite) along X
SL = []
for k in range(13):
    y = AY + 0.15 + k * 0.304
    if y < AY + ARMW + 0.1: L = LEG + 0.2; xc = AX + LEG / 2
    else: L = ARMW + 0.2; xc = AX + ARMW / 2
    so_ = box("slat_%d" % k, L, 0.30, 0.04, ROOFM or tmat(), (0, 0, 0)); so_.rotation_mode = 'QUATERNION'
    endloc = Vector((xc, y, 2.42)); f0 = 530 + k * 5
    col = k % 2; lvl = k // 2
    sw = van_to_world((-3.0 + L / 2, 0.17 if col == 0 else -0.17, 2.13 + lvl * 0.042)); sq = VAN_M.to_quaternion()
    via = exit_via(sw, endloc + Vector((0, 0, 0.5)), lift=0.0, up=4.3)
    it = Item(so_, sw, sq, endloc, quat((0, 0, 0)), f0, 34, via[:-1] + [endloc + Vector((0, 0, 0.6))]); ITEMS.append(it)

# ------------------------------------------------------------------ bake -------------------------------------------------
def ride(it, off, qloc, k):
    """parts that sit in a carton follow it (in the van and while it flies) until their own flight starts"""
    for f in range(1, it.f0 + 1):
        p, q = inside_start(k, off, qloc, f); key(it.o, f, loc=p, quat=q)
RIDERS = set()
for idx, c in enumerate(ORDER):
    st = STOPA_OBJ[c]; tr = TROJ_OBJ[c]
    ride(st, slot_a(idx) + Vector((-0.05, -0.05, -0.04)), quat((0, 0, 0)), "A"); RIDERS.add(id(st))
    ride(tr, slot_b(idx), quat((0, 0, 0)), "B"); RIDERS.add(id(tr))
mount_items = [it for it in ITEMS if it.o.name.startswith("mb2")]
for n_, it in enumerate(mount_items):
    ride(it, mount_slot(n_), quat((0, 0, 0)), "C"); RIDERS.add(id(it))
for it in ITEMS:
    it.bake(skip1=id(it) in RIDERS)

# ============================================================== CAMERA ====================================================
old = sc.camera
cd_ = bpy.data.cameras.new("cam3"); cd_.lens = 24; cd_.clip_start = 0.05; cd_.clip_end = 3000; cd_.sensor_width = old.data.sensor_width if old else 36
cam = bpy.data.objects.new("cam3", cd_); link(cam)
if old: bpy.data.objects.remove(old, do_unlink=True)
sc.camera = cam
tgt = bpy.data.objects.new("cam_target", None); link(tgt)
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
SHOTS = [  # frame, cam xyz, target xyz   (None target = follow the van)
    (1,   (9.6, 45.6, 1.1),   None),
    (129, (9.6, 45.6, 1.1),   None),
    (130, (13.6, 19.6, 1.7),  None),
    (192, (13.6, 19.6, 1.7),  (9.25, 14.4, 1.6)),
    (231, (13.6, 19.6, 1.8),  (9.0, 15.2, 1.9)),
    (300, (13.6, 19.6, 2.3),  None),
    (301, (4.5, 2.0, 1.9),    (-3.0, 0.8, 1.2)),
    (343, (4.5, 2.0, 1.9),    (-3.5, 0.0, 0.9)),
    (344, (3.4, -3.9, 2.0),   (-3.2, 1.0, 1.2)),
    (420, (-1.2, -6.6, 2.3),  (-3.2, 2.0, 1.6)),
    (500, (-9.0, -3.6, 2.6),  (-3.2, 2.3, 1.6)),
    (580, (-9.0, 6.2, 3.1),   (-3.2, 2.3, 1.7)),
    (650, (-8.5, -6.0, 3.0),  (-3.2, 2.3, 1.6)),
    (720, (-2.0, -7.0, 2.7),  (-3.2, 2.4, 1.7)),
    (780, (6.5, -3.2, 4.3),   (-3.1, 2.6, 1.4)),
    (900, (6.5, -3.2, 4.3),   (-3.1, 2.6, 1.4)),
]
CUTS = (130, 301, 344)     # hard cuts: previous key holds, new shot starts on the frame
for f in range(1, 193):
    if f in VAN_POS: key(tgt, f, loc=VAN_POS[f] + Vector((0, 0, 1.1 if f >= 130 else 2.3)))
# frames 232..300: the camera target rides with the carton that is currently flying out of the van (smoothed)
_CART = [it for it in ITEMS if it.o.name.startswith("carton")]
def _cart_pos(f):
    act = [it for it in _CART if it.f0 <= f <= it.f0 + it.dur]
    it = max(act, key=lambda i: i.f0) if act else _CART[0]
    return it.pose(f)[0]
for f in range(232, 301):
    acc = Vector((0, 0, 0)); n_ = 0
    for k in range(-6, 7):
        acc += _cart_pos(min(max(f + k, 232), 320)); n_ += 1
    key(tgt, f, loc=acc / n_ + Vector((0, 0, 0.2)))
for f, c_, t_ in SHOTS:
    key(cam, f, loc=c_)
    if t_ is not None: key(tgt, f, loc=t_)
for o_ in (cam, tgt):
    for fc in _fcurves(o_.animation_data.action):
        for k_ in fc.keyframe_points:
            if round(k_.co[0]) + 1 in CUTS: k_.interpolation = 'CONSTANT'
import json
EV = [{"name": it.o.name, "f0": it.f0, "f1": it.f0 + it.dur} for it in ITEMS]
EV += [{"name": "VAN_STOP", "f0": T_DRIVE, "f1": T_DRIVE}, {"name": "DOOR", "f0": T_DOOR, "f1": T_DOOR + 32}, {"name": "OPEN", "f0": T_OPEN, "f1": T_OPEN + 20}]
json.dump(EV, open(OUT + ".events.json", "w"))
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT, "items", len(ITEMS))
