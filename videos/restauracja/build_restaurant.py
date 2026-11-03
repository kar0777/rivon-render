"""RIVON video #3 - old-town restaurant street: parasols fold away, RIVON gazebos assemble.
Procedural Blender scene (bpy). Metal parts are the exact meshes tessellated from the three RIVON STEP files
(cad/*.stl, 1 unit = 1 mm). Nothing metallic is modelled by hand. Run through render_restaurant.py.
Coordinates: metres, X = along the street (camera looks +X), Y = across (+Y = restaurant side), Z up."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, "..", "dzialka", "textures"))
CAD = os.path.join(HERE, "cad")
FPS, NFR = 30, 720
rng = random.Random(11)

# ------------------------------------------------------------------ timeline (frames) ---------------------------
UMB_T0, UMB_STEP, UMB_FOLD, UMB_SINK = 118, 14, 40, 34        # parasol i folds at UMB_T0+i*STEP
ASM_T0, ASM_STEP = 214, 26                                    # gazebo g starts at ASM_T0+g*ASM_STEP
GAZ_X = [12.0, 17.4, 22.8, 28.2, 33.6]                        # gazebo centres along the street
GAZ_Y = 3.15
W = 3.0                                                       # post centre-to-centre
POST = 0.09                                                   # 90x90 timber (socket inner = 96 mm)
POST_H = 2.40                                                 # timber post length above the Stopa plate

# ------------------------------------------------------------------ helpers -------------------------------------
_mesh_cache = {}
_img_cache = {}


def img(name, nc=False):
    p = os.path.join(TEX, name)
    im = bpy.data.images.load(p, check_existing=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im


def new_obj(name, me, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, coll=None):
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        # materials live on the object, so meshes can be shared between differently coloured objects
        if len(me.materials) == 0: me.materials.append(None)
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = mat
    ob.location = loc; ob.rotation_euler = rot
    if parent is not None: ob.parent = parent
    return ob


def set_smooth(me, flags=None):
    n = len(me.polygons)
    me.polygons.foreach_set("use_smooth", flags if flags is not None else [True] * n)
    me.update()


def box_mesh(sx, sy, sz, grain=True, uvm=1.0):
    """real-size box, origin at centre, per-face planar UV in metres*uvm; grain (u) runs along the longest axis"""
    key = ("box", round(sx, 4), round(sy, 4), round(sz, 4), grain, uvm)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("box")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    uv = bm.loops.layers.uv.new("UVMap")
    dims = (sx, sy, sz); long_ax = max(range(3), key=lambda i: dims[i])
    for f in bm.faces:
        n = f.normal; na = max(range(3), key=lambda i: abs(n[i]))
        axes = [a for a in range(3) if a != na]
        if grain and long_ax in axes:
            ua = long_ax; va = [a for a in axes if a != long_ax][0]
        else:
            ua, va = axes
        for l in f.loops:
            l[uv].uv = (l.vert.co[ua] * uvm, l.vert.co[va] * uvm)
    bm.to_mesh(me); bm.free()
    _mesh_cache[key] = me
    return me


def cyl_mesh(r, h, seg=20, r2=None, cap=True):
    key = ("cyl", round(r, 4), round(h, 4), seg, None if r2 is None else round(r2, 4), cap)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("cyl")
    bm = bmesh.new()
    r2 = r if r2 is None else r2
    top = []; bot = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        bot.append(bm.verts.new((r * math.cos(a), r * math.sin(a), -h / 2)))
        top.append(bm.verts.new((r2 * math.cos(a), r2 * math.sin(a), h / 2)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    flags_side = seg
    if cap:
        tb = [bm.verts.new(v.co) for v in bot]; tt = [bm.verts.new(v.co) for v in top]
        bm.faces.new(tb[::-1]); bm.faces.new(tt)
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (math.atan2(l.vert.co.y, l.vert.co.x) * (r + 0.01) , l.vert.co.z)
    bm.to_mesh(me); bm.free()
    set_smooth(me, [i < flags_side for i in range(len(me.polygons))])
    _mesh_cache[key] = me
    return me


def sphere_mesh(r=0.5, seg=24, rings=16):
    key = ("sph", round(r, 4), seg, rings)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("sph")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bm.to_mesh(me); bm.free(); set_smooth(me)
    _mesh_cache[key] = me
    return me


def box(name, size, loc, mat, rot=(0, 0, 0), parent=None, grain=True, uvm=1.0):
    return new_obj(name, box_mesh(*size, grain=grain, uvm=uvm), mat, loc, rot, parent)


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), parent=None, seg=20, r2=None, cap=True):
    return new_obj(name, cyl_mesh(r, h, seg, r2, cap), mat, loc, rot, parent)


def ball(name, r, loc, mat, scale=(1, 1, 1), parent=None, rot=(0, 0, 0)):
    ob = new_obj(name, sphere_mesh(r), mat, loc, rot, parent)
    ob.scale = scale
    return ob


def between(name, p0, p1, sec, mat, parent=None, roll=0.0):
    """box with its long X axis from p0 to p1, section (w,h)"""
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    me = box_mesh(d.length, sec[0], sec[1])
    ob = new_obj(name, me, mat, (p0 + p1) / 2, (0, 0, 0), parent)
    q = d.to_track_quat('X', 'Z')
    ob.rotation_euler = q.to_euler()
    return ob


# ------------------------------------------------------------------ materials -----------------------------------
def principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED': return n
    return None


def mat_new(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree, principled(m.node_tree)


def pbr(name, color=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tex=None, tex_rough=None, tex_bump=None, bump=0.3,
        tile=1.0, tint=None, mult=None, spec=0.5, emit=None, emit_str=0.0, coat=0.0, mask_lum=False, noise_col=None, sheen=0.0):
    m, nt, bsdf = mat_new(name)
    nodes, links = nt.nodes, nt.links
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Specular IOR Level'].default_value = spec
    if coat: bsdf.inputs['Coat Weight'].default_value = coat
    if emit is not None:
        bsdf.inputs['Emission Color'].default_value = (*emit, 1); bsdf.inputs['Emission Strength'].default_value = emit_str
    uvn = nodes.new('ShaderNodeUVMap'); uvn.uv_map = "UVMap"
    mp = nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
    links.new(uvn.outputs['UV'], mp.inputs['Vector'])
    if tex:
        t = nodes.new('ShaderNodeTexImage'); t.image = img(tex); t.interpolation = 'Cubic'
        links.new(mp.outputs['Vector'], t.inputs['Vector'])
        if tint is not None:               # plaster: use luminance of the texture, colour from tint
            bw = nodes.new('ShaderNodeRGBToBW'); links.new(t.outputs['Color'], bw.inputs['Color'])
            mr = nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.25; mr.inputs['From Max'].default_value = 0.7
            mr.inputs['To Min'].default_value = 0.82; mr.inputs['To Max'].default_value = 1.12
            links.new(bw.outputs['Val'], mr.inputs['Value'])
            mx = nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
            mx.inputs[0].default_value = 1.0
            mx.inputs[6].default_value = (*tint, 1)
            links.new(mr.outputs['Result'], mx.inputs[7])
            links.new(mx.outputs[2], bsdf.inputs['Base Color'])
        elif mult is not None:
            mx = nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
            mx.inputs[7].default_value = (*mult, 1)
            links.new(t.outputs['Color'], mx.inputs[6]); links.new(mx.outputs[2], bsdf.inputs['Base Color'])
        else:
            links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    if tex_rough:
        r = nodes.new('ShaderNodeTexImage'); r.image = img(tex_rough, True); r.interpolation = 'Cubic'
        links.new(mp.outputs['Vector'], r.inputs['Vector'])
        links.new(r.outputs['Color'], bsdf.inputs['Roughness'])
    if tex_bump:
        b = nodes.new('ShaderNodeTexImage'); b.image = img(tex_bump, True); b.interpolation = 'Cubic'
        links.new(mp.outputs['Vector'], b.inputs['Vector'])
        bn = nodes.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = 0.02
        links.new(b.outputs['Color'], bn.inputs['Height'])
        links.new(bn.outputs['Normal'], bsdf.inputs['Normal'])
    return m


def noisy(name, c1, c2, rough=0.8, scale=40.0, bump=0.25):
    m, nt, bsdf = mat_new(name)
    n, l = nt.nodes, nt.links
    tc = n.new('ShaderNodeTexCoord')
    ns = n.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = scale; ns.inputs['Detail'].default_value = 8
    l.new(tc.outputs['Object'], ns.inputs['Vector']) if False else nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*c1, 1); ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(ns.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bn = n.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = 0.02
    nt.links.new(ns.outputs['Fac'], bn.inputs['Height']); nt.links.new(bn.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough
    return m


M = {}


def build_materials():
    M['stone'] = pbr("stone", (0.5, 0.5, 0.5), tex="stone_tiles_02_diff_2k.jpg", tex_rough="stone_tiles_02_rough_2k.exr",
                     tex_bump="stone_tiles_02_disp_2k.png", bump=0.6, tile=2.6, mult=(1.9, 1.45, 1.0))
    cols = {"ochre": (0.9, 0.6, 0.26), "pink": (0.88, 0.5, 0.46), "mint": (0.45, 0.74, 0.58), "cream": (0.95, 0.83, 0.58),
            "terra": (0.8, 0.4, 0.28), "blue": (0.46, 0.62, 0.82), "yellow": (0.96, 0.78, 0.28), "grey": (0.7, 0.7, 0.66),
            "white": (0.92, 0.9, 0.84), "sage": (0.6, 0.72, 0.42)}
    for k, c in cols.items():
        M['wall_' + k] = pbr("wall_" + k, (0.8, 0.8, 0.8), tex="beige_wall_002_diff_2k.jpg", tex_bump="beige_wall_002_disp_2k.png",
                             tint=c, rough=0.9, tile=2.0, bump=0.15)
    M['wall_keys'] = list(cols)
    M['roof'] = pbr("roof_tile", (0.6, 0.3, 0.2), tex="clay_roof_tiles_03_diff_2k.jpg", tex_rough="clay_roof_tiles_03_rough_2k.exr",
                    tex_bump="clay_roof_tiles_03_disp_2k.png", tile=1.6, bump=0.8)
    M['roof_dark'] = pbr("roof_dark", (0.2, 0.17, 0.16), tex="clay_roof_tiles_03_diff_2k.jpg", tint=(0.42, 0.36, 0.34), rough=0.7,
                         tex_bump="clay_roof_tiles_03_disp_2k.png", tile=1.6, bump=0.8)
    M['beam'] = pbr("beam_wood", (0.8, 0.6, 0.4), tex="olive_veneer_diff_2k.jpg", tex_rough="olive_veneer_rough_2k.exr",
                    tex_bump="olive_veneer_disp_2k.png", tile=0.9, bump=0.15, rough=0.6)
    M['teak'] = pbr("teak", (0.7, 0.45, 0.25), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                    tex_bump="teak_veneer_disp_2k.png", tile=0.9, bump=0.12, rough=0.55)
    M['walnut'] = pbr("walnut", (0.3, 0.17, 0.1), tex="wood_model_dom_2_1.jpg", tile=0.8, rough=0.45)
    # RIVON powder coat RAL 9005 (deep black): dielectric, satin
    M['rivon'] = pbr("rivon_black", (0.012, 0.012, 0.013), rough=0.42, metal=0.0, spec=0.55, coat=0.15)
    M['frame'] = pbr("window_frame", (0.93, 0.92, 0.88), rough=0.45)
    M['glass'] = pbr("window_glass", (0.03, 0.045, 0.06), rough=0.04, metal=0.2, spec=0.9)
    M['glass_lit'] = pbr("window_lit", (1.0, 0.7, 0.4), rough=0.3, emit=(1.0, 0.62, 0.28), emit_str=2.2)
    M['white'] = pbr("white_ceramic", (0.9, 0.9, 0.88), rough=0.2)
    M['linen'] = pbr("linen", (0.92, 0.88, 0.8), rough=0.95)
    M['metal_dark'] = pbr("cast_iron", (0.025, 0.027, 0.03), rough=0.5, metal=0.6)
    M['chimney'] = pbr("brick", (0.45, 0.2, 0.15), rough=0.9)
    M['door'] = pbr("door", (0.18, 0.1, 0.07), rough=0.5)
    M['canopy'] = pbr("parasol_fabric", (0.88, 0.8, 0.64), rough=0.9, sheen=0.5)
    M['canopy2'] = pbr("parasol_fabric2", (0.74, 0.38, 0.27), rough=0.9)
    M['skin'] = [pbr("skin%d" % i, c, rough=0.55) for i, c in enumerate([(0.82, 0.62, 0.5), (0.7, 0.5, 0.38), (0.9, 0.72, 0.6), (0.55, 0.38, 0.28)])]
    M['hair'] = [pbr("hair%d" % i, c, rough=0.6) for i, c in enumerate([(0.06, 0.04, 0.03), (0.25, 0.14, 0.07), (0.6, 0.45, 0.22), (0.5, 0.5, 0.5)])]
    M['cloth'] = [pbr("cloth%d" % i, c, rough=0.85) for i, c in enumerate(
        [(0.12, 0.18, 0.32), (0.55, 0.12, 0.12), (0.85, 0.82, 0.74), (0.2, 0.36, 0.25), (0.75, 0.55, 0.2), (0.1, 0.1, 0.12), (0.8, 0.5, 0.55), (0.25, 0.5, 0.62)])]
    M['topiary'] = noisy("topiary", (0.05, 0.16, 0.05), (0.14, 0.36, 0.1), rough=0.8, scale=55)
    M['soil'] = pbr("planter", (0.3, 0.28, 0.25), rough=0.9)
    M['planter'] = pbr("planter_box", (0.2, 0.2, 0.19), rough=0.8)
    M['bulb'] = pbr("bulb", (1, 0.8, 0.5), emit=(1.0, 0.66, 0.3), emit_str=40.0)
    M['lamp'] = pbr("lamp_glass", (1, 0.8, 0.5), emit=(1.0, 0.7, 0.35), emit_str=6.0)
    M['wine'] = pbr("drink", (0.5, 0.35, 0.1), rough=0.1)
    M['glassware'] = pbr("glassware", (0.9, 0.95, 1.0), rough=0.02)


# ------------------------------------------------------------------ animation helpers ---------------------------
def key_loc(ob, f, loc, interp=None):
    ob.location = loc; ob.keyframe_insert('location', frame=f)


def key_rot(ob, f, rot):
    ob.rotation_euler = rot; ob.keyframe_insert('rotation_euler', frame=f)


def key_scale(ob, f, sc):
    ob.scale = sc; ob.keyframe_insert('scale', frame=f)


def show_from(ob, f):
    """hidden in render before frame f"""
    ob.hide_render = True; ob.keyframe_insert('hide_render', frame=max(0, f - 1))
    ob.hide_render = False; ob.keyframe_insert('hide_render', frame=f)


def hide_from(ob, f):
    ob.hide_render = False; ob.keyframe_insert('hide_render', frame=max(0, f - 1))
    ob.hide_render = True; ob.keyframe_insert('hide_render', frame=f)


def fix_constant(ob):
    ad = ob.animation_data
    if not ad or not ad.action: return
    try:
        fcs = ad.action.fcurves
    except Exception:
        fcs = []
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: fcs.extend(cb.fcurves)
    for fc in fcs:
        if fc.data_path in ('hide_render', 'hide_viewport'):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'


def drop_in(ob, f0, f1, rest, offset=(0, 0, 1.5), rot_from=None):
    """appear at f0 displaced by offset, glide to rest by f1"""
    rest = Vector(rest)
    show_from(ob, f0)
    key_loc(ob, f0, rest + Vector(offset)); key_loc(ob, f1, rest)
    if rot_from is not None:
        key_rot(ob, f0, rot_from); key_rot(ob, f1, (0, 0, 0))


# ------------------------------------------------------------------ street, facades -----------------------------
def window(prefix, cx, y, side, z, w=1.05, h=1.55, lit=False, arch=False):
    """flat window on a facade at y=facade plane, side=+1 means facade faces -Y (building on +Y side)"""
    n = -side           # outward normal along Y
    fy = y + n * 0.03
    box(prefix + "_fr", (w + 0.2, 0.08, h + 0.2), (cx, fy, z), M['frame'])
    box(prefix + "_gl", (w, 0.04, h), (cx, fy + n * 0.045, z), M['glass_lit'] if lit else M['glass'])
    box(prefix + "_mv", (0.05, 0.06, h), (cx, fy + n * 0.06, z), M['frame'])
    box(prefix + "_mh", (w, 0.06, 0.05), (cx, fy + n * 0.06, z + 0.1), M['frame'])
    box(prefix + "_sl", (w + 0.45, 0.2, 0.07), (cx, fy + n * 0.1, z - h / 2 - 0.15), M['frame'])
    box(prefix + "_li", (w + 0.4, 0.14, 0.14), (cx, fy + n * 0.07, z + h / 2 + 0.2), M['frame'])


def building(x0, w, side, floors, wall, roof='gable', lit_ground=False, shop=True, seed=0):
    r = random.Random(seed)
    depth = 12.0; fl0 = 4.0; flh = 3.25
    H = fl0 + floors * flh
    yf = 5.0 * side                       # facade plane
    ymid = yf + side * depth / 2
    n = -side
    box("bld", (w, depth, H), (x0 + w / 2, ymid, H / 2), M['wall_' + wall], uvm=1.0)
    # cornice + base plinth
    box("corn", (w + 0.1, 0.5, 0.35), (x0 + w / 2, yf + n * 0.22, H - 0.2), M['wall_white'])
    box("corn2", (w + 0.1, 0.3, 0.18), (x0 + w / 2, yf + n * 0.12, fl0 + 0.15), M['wall_white'])
    box("plinth", (w, 0.1, 0.5), (x0 + w / 2, yf + n * 0.05, 0.25), M['wall_grey'])
    cols = max(2, int(round(w / 2.4)))
    pitch = w / cols
    for f in range(floors):
        z = fl0 + f * flh + flh / 2 + 0.2
        for c in range(cols):
            cx = x0 + pitch * (c + 0.5)
            window("w", cx, yf, side, z, lit=False)
    # ground floor shopfront / arcade
    gz = 1.5
    for c in range(cols):
        cx = x0 + pitch * (c + 0.5)
        if c == cols // 2:
            box("door", (1.3, 0.1, 2.7), (cx, yf + n * 0.07, 1.4), M['door'])
            box("doorf", (1.6, 0.14, 0.18), (cx, yf + n * 0.08, 2.85), M['frame'])
        else:
            window("g", cx, yf, side, gz + 0.35, w=min(1.6, pitch - 0.8), h=1.9, lit=lit_ground)
    # roof
    ry = yf + side * (depth + 0.4) / 2 - side * 0.0
    rh = 3.4 if roof == 'gable' else 0
    if roof == 'gable':
        y0 = yf + n * 0.5; y1 = yf + side * depth
        yc = (y0 + y1) / 2
        me = bpy.data.meshes.new("roof"); bm = bmesh.new()
        xa, xb = x0 - 0.05, x0 + w + 0.05
        a = bm.verts.new((xa, y0, H - 0.05)); b = bm.verts.new((xb, y0, H - 0.05))
        c_ = bm.verts.new((xb, yc, H + rh)); d = bm.verts.new((xa, yc, H + rh))
        e = bm.verts.new((xb, y1, H - 0.05)); f_ = bm.verts.new((xa, y1, H - 0.05))
        s1 = (a, b, c_, d) if side > 0 else (b, a, d, c_)
        s2 = (d, c_, e, f_) if side > 0 else (c_, d, f_, e)
        bm.faces.new(s1); bm.faces.new(s2)
        bm.faces.new((a, d, f_) if side > 0 else (d, a, f_)); bm.faces.new((b, e, c_) if side > 0 else (e, b, c_))
        bm.normal_update()
        uv = bm.loops.layers.uv.new("UVMap")
        for fc in bm.faces:
            for l in fc.loops:
                p = l.vert.co
                l[uv].uv = (p.x, math.hypot(p.y - y0, p.z - H))
        bm.to_mesh(me); bm.free()
        ob = new_obj("roof", me, M['roof'] if r.random() < 0.7 else M['roof_dark'])
        # chimney
        if r.random() < 0.6:
            box("chim", (0.7, 0.7, 2.2), (x0 + w * r.uniform(0.25, 0.75), yc + side * r.uniform(0, 2), H + rh + 0.2), M['chimney'])
        # dormer
        if w > 6 and r.random() < 0.8:
            dx = x0 + w / 2
            box("dorm", (1.5, 1.4, 1.6), (dx, yf + side * 2.2 - side * 0 , H + 1.0), M['wall_' + wall])
            box("dorm_g", (0.9, 0.05, 1.0), (dx, yf + side * 2.2 + n * 0.72, H + 1.05), M['glass'])
    else:
        box("parapet", (w, 0.3, 0.5), (x0 + w / 2, yf + n * 0.05 + side * 0.15, H + 0.25), M['wall_white'])


def end_block(x):
    """closing building at the end of the street (faces -X)"""
    wd = 22.0; H = 19.0
    box("end", (10.0, wd, H), (x + 5.0, 0, H / 2), M['wall_ochre'])
    nx = -1
    for fl in range(4):
        for c in range(-4, 5):
            if c % 2 == 0 and False: continue
            y = c * 2.2; z = 2.6 + fl * 3.6
            box("ew_fr", (0.08, 1.25, 1.75), (x - 0.03, y, z), M['frame'])
            box("ew_gl", (0.04, 1.05, 1.55), (x - 0.075, y, z), M['glass'])
            box("ew_mv", (0.06, 0.05, 1.55), (x - 0.09, y, z), M['frame'])
            box("ew_sl", (0.2, 1.5, 0.07), (x - 0.1, y, z - 0.95), M['frame'])
    box("ec", (0.5, wd + 0.2, 0.4), (x - 0.2, 0, H - 0.2), M['wall_white'])
    # gable roof (ridge along Y)
    me = bpy.data.meshes.new("endroof"); bm = bmesh.new()
    a = bm.verts.new((x - 0.4, -wd / 2 - 0.2, H)); b = bm.verts.new((x - 0.4, wd / 2 + 0.2, H))
    c_ = bm.verts.new((x + 5.0, wd / 2 + 0.2, H + 5.0)); d = bm.verts.new((x + 5.0, -wd / 2 - 0.2, H + 5.0))
    bm.faces.new((a, d, c_, b)); bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for fc in bm.faces:
        for l in fc.loops: l[uv].uv = (l.vert.co.y, math.hypot(l.vert.co.x - (x - 0.4), l.vert.co.z - H))
    bm.to_mesh(me); bm.free()
    new_obj("endroof", me, M['roof'])
    box("endroof2", (0.1, wd, 0.1), (x + 5.0, 0, H + 5.0), M['roof'])


STREET = {}


def build_street():
    # paving
    box("street", (150, 11.0, 0.3), (50, 0, -0.15), M['stone'])
    # buildings, both sides. (x0, w, floors, wall, roof)
    left = [(-14, 8.5, 4, 'cream', 'gable'), (-5.5, 6.5, 3, 'pink', 'gable'), (1.0, 7.0, 4, 'mint', 'gable'),
            (8.0, 8.8, 4, 'cream', 'gable'), (16.8, 9.2, 4, 'ochre', 'gable'), (26.0, 8.0, 3, 'white', 'parapet'),
            (34.0, 9.0, 4, 'terra', 'gable'), (43.0, 7.0, 4, 'blue', 'gable'), (50.0, 8.5, 4, 'yellow', 'gable'),
            (58.5, 7.5, 3, 'sage', 'gable'), (66.0, 9.0, 4, 'pink', 'gable'), (75.0, 8.0, 4, 'cream', 'gable'), (83.0, 9.0, 4, 'grey', 'gable')]
    right = [(-14, 7.0, 4, 'yellow', 'gable'), (-7.0, 8.0, 3, 'blue', 'gable'), (1.0, 6.5, 4, 'sage', 'gable'), (7.5, 8.5, 4, 'pink', 'gable'),
             (16.0, 7.5, 4, 'cream', 'gable'), (23.5, 9.0, 3, 'mint', 'gable'), (32.5, 7.0, 4, 'ochre', 'gable'), (39.5, 8.0, 4, 'white', 'gable'),
             (47.5, 8.0, 4, 'terra', 'gable'), (55.5, 8.5, 3, 'cream', 'gable'), (64.0, 7.5, 4, 'blue', 'gable'), (71.5, 8.5, 4, 'yellow', 'gable'), (80.0, 12.0, 4, 'pink', 'gable')]
    for i, (x0, w, fl, wl, rf) in enumerate(left):
        building(x0, w, +1, fl, wl, rf, lit_ground=(8.0 <= x0 <= 26.0), seed=100 + i)
    for i, (x0, w, fl, wl, rf) in enumerate(right):
        building(x0, w, -1, fl, wl, rf, lit_ground=False, seed=200 + i)
    # closing building at the end of the street
    end_block(100.0)
    # lamp posts
    for i, x in enumerate([6, 20, 34, 48, 62]):
        for sy in (-4.4,):
            cyl("lp", 0.05, 3.6, (x, sy, 1.8), M['metal_dark'], seg=10)
            cyl("lpb", 0.12, 0.5, (x, sy, 0.25), M['metal_dark'], seg=10, r2=0.07)
            box("lpl", (0.28, 0.28, 0.45), (x, sy, 3.8), M['lamp'])
            box("lpt", (0.38, 0.38, 0.06), (x, sy, 4.07), M['metal_dark'])
    # restaurant planters along the terrace edge + topiary
    for i in range(0, 60):
        x = 8.8 + i * 0.5
        if x > 36.8: break
    for k in range(7):
        x = 9.4 + k * 5.4 + 2.7
        box("planter", (0.9, 0.55, 0.5), (x, 1.15, 0.25), M['planter'])
        box("soil", (0.8, 0.45, 0.05), (x, 1.15, 0.52), M['soil'])
        ball("topiary", 0.27, (x, 1.15, 1.02), M['topiary'])
        cyl("trunk", 0.025, 0.4, (x, 1.15, 0.7), M['walnut'], seg=8)


# ------------------------------------------------------------------ furniture / people --------------------------
def chair(prefix, loc, yaw, parent):
    root = bpy.data.objects.new(prefix, None); bpy.context.scene.collection.objects.link(root)
    root.location = loc; root.rotation_euler = (0, 0, yaw)
    # local: facing +X (towards the table centre is -X direction in local? we face +X)
    box(prefix + "s", (0.42, 0.42, 0.035), (0, 0, 0.45), M['teak'], parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(prefix + "l", 0.016, 0.45, (sx * 0.18, sy * 0.18, 0.225), M['walnut'], parent=root, seg=8)
    for sy in (-1, 1):
        box(prefix + "bk", (0.03, 0.03, 0.46), (-0.19, sy * 0.18, 0.7), M['walnut'], parent=root)
    box(prefix + "r1", (0.03, 0.4, 0.05), (-0.19, 0, 0.9), M['teak'], parent=root)
    box(prefix + "r2", (0.03, 0.4, 0.04), (-0.19, 0, 0.78), M['teak'], parent=root)
    box(prefix + "r3", (0.03, 0.4, 0.04), (-0.19, 0, 0.66), M['teak'], parent=root)
    return root


def person(prefix, base, yaw, parent, r):
    """seated figure, stylised mannequin proportions; faces +X in local space; base = seat-centre"""
    root = bpy.data.objects.new(prefix, None); bpy.context.scene.collection.objects.link(root)
    root.location = base; root.rotation_euler = (0, 0, yaw)
    cl = r.choice(M['cloth']); cl2 = r.choice(M['cloth']); sk = r.choice(M['skin']); hr = r.choice(M['hair'])
    trouser = M['cloth'][r.choice([0, 5, 5, 2, 3])]
    # pelvis/torso
    ball(prefix + "t", 0.5, (-0.04, 0, 0.78), cl, scale=(0.22, 0.34, 0.52), parent=root)
    ball(prefix + "p", 0.5, (0, 0, 0.5), trouser, scale=(0.3, 0.36, 0.2), parent=root)
    ball(prefix + "sh", 0.5, (-0.04, 0, 1.0), cl, scale=(0.2, 0.46, 0.18), parent=root)
    ball(prefix + "nk", 0.5, (-0.03, 0, 1.12), sk, scale=(0.1, 0.1, 0.12), parent=root)
    ball(prefix + "hd", 0.5, (0.01, 0, 1.29), sk, scale=(0.235, 0.2, 0.27), parent=root)
    ball(prefix + "hr", 0.5, (-0.025, 0, 1.345), hr, scale=(0.25, 0.215, 0.255), parent=root)
    for sy in (-1, 1):
        # thigh, shin
        ball(prefix + "th", 0.5, (0.22, sy * 0.1, 0.52), trouser, scale=(0.48, 0.15, 0.15), parent=root)
        ball(prefix + "sn", 0.5, (0.44, sy * 0.1, 0.27), trouser, scale=(0.14, 0.13, 0.5), parent=root)
        ball(prefix + "ft", 0.5, (0.5, sy * 0.1, 0.05), M['metal_dark'], scale=(0.28, 0.11, 0.08), parent=root)
        # arm: shoulder -> elbow -> hand on the table
        ball(prefix + "ua", 0.5, (0.04, sy * 0.25, 0.9), cl, scale=(0.13, 0.12, 0.34), parent=root, rot=(0, -0.15, 0))
        ball(prefix + "fa", 0.5, (0.22, sy * 0.24, 0.8), sk, scale=(0.36, 0.1, 0.1), parent=root, rot=(0, 0.18, 0))
        ball(prefix + "hn", 0.5, (0.42, sy * 0.22, 0.77), sk, scale=(0.13, 0.09, 0.05), parent=root)
    return root


def table_set(g, cx, cy, parent=None):
    tops = []
    # round table 1.4 m, pedestal with RIVON-neutral black base
    top = cyl("tbl_top", 0.7, 0.04, (cx, cy, 0.75), M['teak'], seg=40)
    cyl("tbl_ped", 0.05, 0.72, (cx, cy, 0.37), M['metal_dark'], seg=12)
    cyl("tbl_base", 0.34, 0.03, (cx, cy, 0.02), M['metal_dark'], seg=24)
    cyl("linen", 0.5, 0.012, (cx, cy, 0.776), M['linen'], seg=32)
    people = []; chairs = []
    n = 6
    r_ = random.Random(900 + g)
    for k in range(n):
        a = k * 2 * math.pi / n + math.pi / n
        px, py = cx + 0.98 * math.cos(a), cy + 0.98 * math.sin(a)
        yaw = a + math.pi     # facing centre
        chairs.append(chair("chr", (px, py, 0), yaw, None))
        if g != 0 and (k != 4 or g % 2 == 1):      # the first table stays empty: it is the build site that the close-ups film
            people.append(person("ppl", (px + 0.04 * math.cos(a), py + 0.04 * math.sin(a), 0), yaw, None, r_))
        # place setting
        sx, sy = cx + 0.46 * math.cos(a), cy + 0.46 * math.sin(a)
        cyl("plate", 0.12, 0.014, (sx, sy, 0.79), M['white'], seg=20)
        gx, gy = cx + 0.52 * math.cos(a + 0.28), cy + 0.52 * math.sin(a + 0.28)
        cyl("glass", 0.032, 0.11, (gx, gy, 0.835), M['glassware'], seg=10)
    cyl("vase", 0.04, 0.16, (cx, cy, 0.86), M['glassware'], seg=10)
    ball("flowers", 0.09, (cx, cy, 0.99), M['topiary'], scale=(1, 1, 0.8))
    for i in range(3):
        a = i * 2.1
        ball("fl", 0.025, (cx + 0.06 * math.cos(a), cy + 0.06 * math.sin(a), 1.05), pbr("flower%d_%d" % (g, i), (0.9, 0.3 + 0.2 * i, 0.3), rough=0.6))
    return people


# ------------------------------------------------------------------ parasol -------------------------------------
def parasol(g, cx, cy, fabric):
    """round 3.2 m parasol: pole + dome canopy with an 'open' and a 'closed' shape key; returns (root, base)"""
    R = 1.65; ztop = 2.78; zrim = 2.12
    segs = 16; rings = 5
    me = bpy.data.meshes.new("canopy"); bm = bmesh.new()
    apex = bm.verts.new((0, 0, ztop))
    grid = []
    for k in range(1, rings + 1):
        ring = []
        rr = R * k / rings
        zz = zrim + (ztop - zrim) * (1 - (k / rings) ** 2.0)
        for i in range(segs):
            a = 2 * math.pi * i / segs
            # fabric scallop: panel mid (odd i) slightly raised at the rim
            sc = 0.0
            if k == rings and i % 2 == 1: sc = 0.07
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz + sc - 0.03 * (k / rings) * (1 if i % 2 == 1 else 0))))
        grid.append(ring)
    for i in range(segs):
        bm.faces.new((apex, grid[0][(i + 1) % segs], grid[0][i]))
    for k in range(rings - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((grid[k][i], grid[k][j], grid[k + 1][j], grid[k + 1][i]))
    # valance (drop skirt)
    skirt = []
    for i in range(segs):
        v = grid[-1][i]
        skirt.append(bm.verts.new((v.co.x * 1.0, v.co.y * 1.0, v.co.z - 0.14)))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((grid[-1][i], grid[-1][j], skirt[j], skirt[i]))
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.y)
    bm.to_mesh(me); bm.free()
    me.shade_smooth() if hasattr(me, "shade_smooth") else None
    # closed shape key
    basis = me.shape_keys.key_blocks[0] if me.shape_keys else None
    sk0 = None
    ob = new_obj("parasol_canopy", me, fabric, (cx, cy, 0))
    ob.shape_key_add(name="open")
    clo = ob.shape_key_add(name="closed")
    n = len(me.vertices)
    for idx, v in enumerate(me.vertices):
        p = v.co.copy()
        h = (p.z - zrim) / (ztop - zrim)
        rad = math.hypot(p.x, p.y)
        a = math.atan2(p.y, p.x)
        # folded: slim bundle along the pole; rim hangs down
        newr = 0.045 + 0.05 * (rad / R) ** 1.0
        ang_f = 1.0 + 0.1 * math.sin(a * 8)
        newz = ztop - (1 - (rad / R)) * 0.0 - (rad / R) * 1.55 + (0.07 if (abs(math.sin(a * 8 / 2)) < 0.3 and rad > R * 0.95) else 0)
        clo.data[idx].co = (newr * ang_f * math.cos(a), newr * ang_f * math.sin(a), newz)
    clo.value = 0.0
    pole = cyl("pole", 0.026, 2.78, (cx, cy, 1.39), M['metal_dark'], seg=12)
    cap = cyl("pole_cap", 0.02, 0.18, (cx, cy, 2.86), M['metal_dark'], seg=8)
    base = cyl("pbase", 0.38, 0.07, (cx, cy, 0.035), M['metal_dark'], seg=28)
    weight = ball("pweight", 0.2, (cx, cy, 0.1), M['planter'], scale=(1.6, 1.6, 0.3))
    parts = [ob, pole, cap, base, weight]
    for p in parts: p.parent = None
    return ob, parts, clo


def animate_parasol(i, ob, parts, clo):
    f0 = UMB_T0 + i * UMB_STEP
    f1 = f0 + UMB_FOLD
    f2 = f1 + UMB_SINK
    clo.value = 0.0; clo.keyframe_insert('value', frame=f0)
    clo.value = 1.0; clo.keyframe_insert('value', frame=f1)
    # whole parasol sinks into the paving after folding (telescoping base hatch)
    for p in parts:
        z0 = p.location.z
        key_loc(p, f1 + 4, (p.location.x, p.location.y, z0))
        key_loc(p, f2, (p.location.x, p.location.y, z0 - 3.2))
        hide_from(p, f2 + 1)
    # slight rotation twist while folding for life
    key_rot(ob, f0, (0, 0, 0)); key_rot(ob, f1, (0, 0, 0.45))
    for p in parts:
        fix_constant(p)


# ------------------------------------------------------------------ RIVON connectors (exact STEP meshes) -------
_stl = {}


def import_stl(name):
    if name in _stl: return _stl[name]
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(CAD, name + ".stl"))
    new = [o for o in bpy.data.objects if o not in before][0]
    me = new.data
    me.transform(Matrix.Scale(0.001, 4))             # mm -> m, geometry untouched otherwise
    bpy.data.objects.remove(new, do_unlink=True)
    me.name = "RIVON_" + name
    me.materials.append(M['rivon'])
    # shade: flat faces stay crisp, curved logo edges smooth by angle
    for p in me.polygons: p.use_smooth = False
    me.update()
    _stl[name] = me
    return me


def stopa(name, loc):
    me = import_stl("Stopa")
    # Stopa origin: socket corner at (0,0); socket centre is (0.05,0.05); plate bottom z=-0.002
    ob = new_obj(name, me, None, (loc[0] - 0.05, loc[1] - 0.05, loc[2] + 0.002))
    return ob


def trojak(name, post_c, top_z, corner):
    """Trojak (CAD: vertical tube +Z, arms +X and -Y) turned upside down: socket faces down onto the post,
    arms point to +X/+Y; rotated about Z for the four frame corners.
    post_c = post centre; top_z = z of post top."""
    me = import_stl("Trojak")
    ob = new_obj(name, me, None)
    # CAD point (50,50,*) mm is the post axis.  Rotate 180 deg about X: (x,y,z)->(x,-y,-z); arms then go +X,+Y.
    # Place so that CAD z = -98 (socket floor, rotated => +98) sits on the post top.
    yaw = corner * math.pi / 2
    Rz = Matrix.Rotation(yaw, 4, 'Z')
    Rx = Matrix.Rotation(math.pi, 4, 'X')
    # after Rx: axis at (0.05,-0.05); floor of socket at z=+0.098 ; want post top there
    off = Vector((0.05, -0.05, 0.098))
    T0 = Matrix.Translation(-off)
    M_ = Matrix.Translation((post_c[0], post_c[1], top_z)) @ Rz @ T0 @ Rx
    ob.matrix_world = M_
    return ob


# ------------------------------------------------------------------ gazebo --------------------------------------
GAZ = []          # per gazebo: dict of parts, used by lights / camera


def roof_panels(g, cx, cy, z_e, parent_list):
    """hip roof: 4 triangular tile panels + wooden lining, apex over the centre"""
    H0 = W / 2                    # frame half size (post centres)
    Hs = W / 2 + 0.55             # eave overhang
    z_a = z_e + 0.98
    k = (z_a - z_e) / H0
    z_eave = z_e - k * (Hs - H0)
    panels = []
    for s in range(4):
        yaw = s * math.pi / 2
        c, sn = math.cos(yaw), math.sin(yaw)
        def P(px, py, pz): return Vector((cx + px * c - py * sn, cy + px * sn + py * c, pz))
        # panel on the +X side (local), rotate by yaw
        a = P(Hs, -Hs, z_eave); b = P(Hs, Hs, z_eave); ap = P(0.0, 0.0, z_a + 0.02)
        for tag, mat, dz in (("tile", M['roof'], 0.0), ("lining", M['beam'], -0.045)):
            me = bpy.data.meshes.new("roofp"); bm = bmesh.new()
            va = bm.verts.new(a + Vector((0, 0, dz))); vb = bm.verts.new(b + Vector((0, 0, dz))); vc = bm.verts.new(ap + Vector((0, 0, dz)))
            bm.faces.new((va, vc, vb) if tag == "tile" else (va, vb, vc))
            bm.normal_update()
            uv = bm.loops.layers.uv.new("UVMap")
            ed = (b - a).normalized(); sd = (ap - (a + b) / 2).normalized()
            bm.faces.ensure_lookup_table()
            for l in bm.faces[0].loops:
                p = l.vert.co - a
                l[uv].uv = (p.dot(ed), p.dot(sd))
            bm.to_mesh(me); bm.free()
            ob = new_obj("roof_" + tag, me, mat)
            if tag == "tile":
                mod = ob.modifiers.new("th", 'SOLIDIFY'); mod.thickness = 0.04; mod.offset = 1
            panels.append((ob, s, tag))
    return panels


def gazebo(g, cx, cy):
    t0 = ASM_T0 + g * ASM_STEP
    topz = POST_H + 0.002                  # post stands on the Stopa plate (top face at z=0.002)
    corners = [(-W / 2, -W / 2), (W / 2, -W / 2), (W / 2, W / 2), (-W / 2, W / 2)]
    info = dict(t0=t0, cx=cx, cy=cy, topz=topz, bulbs=[])
    # --- Stopa -> post -> Trojak (corner i: arms rotated by i*90 degrees) ---
    for i, (dx, dy) in enumerate(corners):
        px, py = cx + dx, cy + dy
        s = stopa("RIVON_Stopa", (px, py, 0))
        drop_in(s, t0 + i * 3, t0 + i * 3 + 14, s.location, (0, 0, 1.7))
        p = box("post", (POST, POST, POST_H), (px, py, POST_H / 2 + 0.002), M['beam'])
        drop_in(p, t0 + 14 + i * 4, t0 + 14 + i * 4 + 22, p.location, (0, 0, 2.4))
        tj = trojak("RIVON_Trojak", (px, py), topz, i)
        loc = tj.matrix_world.to_translation(); rot = tj.matrix_world.to_euler()
        tj.location = loc; tj.rotation_euler = rot
        drop_in(tj, t0 + 44 + i * 4, t0 + 44 + i * 4 + 22, tj.location, (0, 0, 1.5))
    # --- four beams sliding into the Trojak arms (100 mm engagement in each arm) ---
    arm_z = topz - 0.048
    eng = 0.15
    runs = [((-W / 2, -W / 2), (W / 2, -W / 2)), ((W / 2, -W / 2), (W / 2, W / 2)),
            ((W / 2, W / 2), (-W / 2, W / 2)), ((-W / 2, W / 2), (-W / 2, -W / 2))]
    for j, (a, b) in enumerate(runs):
        va = Vector((cx + a[0], cy + a[1], arm_z)); vb = Vector((cx + b[0], cy + b[1], arm_z))
        d = (vb - va).normalized()
        p0 = va + d * eng; p1 = vb - d * eng
        bm_ = between("beam", p0, p1, (POST, POST), M['beam'])
        f0 = t0 + 74 + j * 6
        rest_loc = bm_.location.copy()
        show_from(bm_, f0)
        # slides in along its own axis from outside, last part is the straight push into the arms
        side = Vector((d.y, -d.x, 0))                 # outward normal (to the right of travel)
        key_loc(bm_, f0, rest_loc + Vector((0, 0, 0.55)) + side * 0.9)
        key_loc(bm_, f0 + 16, rest_loc + Vector((0, 0, 0.0)) + side * 0.9 * 0.0 + d * 0.0 + Vector((0, 0, 0.12)))
        key_loc(bm_, f0 + 24, rest_loc)
    # --- rafters (visible hip/common timber) and roof ---
    z_e = topz + 0.03
    apex = Vector((cx, cy, z_e + 0.98))
    rf = 0
    for i, (dx, dy) in enumerate(corners):
        c0 = Vector((cx + dx, cy + dy, z_e + 0.03))
        far = Vector((cx + dx * 1.37, cy + dy * 1.37, z_e - 0.30))
        ra = between("hip", far, apex + Vector((0, 0, 0.0)), (0.05, 0.10), M['beam'])
        f = t0 + 102 + rf * 3; rf += 1
        rest = ra.location.copy(); show_from(ra, f)
        key_loc(ra, f, rest + Vector((0, 0, 1.2))); key_loc(ra, f + 18, rest)
    for s in range(4):
        yaw = s * math.pi / 2; c, sn = math.cos(yaw), math.sin(yaw)
        for off in (-0.75, 0.75):
            def P(px, py, pz): return Vector((cx + px * c - py * sn, cy + px * sn + py * c, pz))
            k = (0.98) / (W / 2)
            e = P(W / 2 + 0.55, off * 1.37, z_e - 0.55 * k + 0.02)
            top = P(0.0, off * 0.0, z_e + 0.98)
            top = P(0.55 * 0 + abs(off) * 0 + 0.0, off * 0.0, z_e + 0.98)
            ra = between("rafter", e, P(0.1, off * 0.2, z_e + 0.98 - 0.1 * k), (0.045, 0.09), M['beam'])
            f = t0 + 104 + rf * 3; rf += 1
            rest = ra.location.copy(); show_from(ra, f)
            key_loc(ra, f, rest + Vector((0, 0, 1.2))); key_loc(ra, f + 18, rest)
    panels = roof_panels(g, cx, cy, z_e, [])
    for idx, (ob, s, tag) in enumerate(panels):
        f = t0 + 124 + s * 6
        rest = ob.location.copy(); show_from(ob, f)
        key_loc(ob, f, rest + Vector((0, 0, 1.6))); key_loc(ob, f + 22, rest)
    # festoon lights under the eaves (appear when the roof is finished)
    t_on = t0 + 154
    ring = [(-W / 2 + 0.1, -W / 2 + 0.1), (W / 2 - 0.1, -W / 2 + 0.1), (W / 2 - 0.1, W / 2 - 0.1), (-W / 2 + 0.1, W / 2 - 0.1)]
    for i in range(4):
        a = Vector(ring[i]); b = Vector(ring[(i + 1) % 4])
        for t in range(1, 9):
            u = t / 9.0
            p = a.lerp(b, u)
            sag = 0.16 * 4 * u * (1 - u)
            bl = ball("bulb", 0.032, (cx + p.x, cy + p.y, topz - 0.15 - sag), M['bulb'])
            show_from(bl, t_on)
    return t0


def build_furniture_and_parasols():
    umbs = []
    for g, cx in enumerate(GAZ_X):
        table_set(g, cx, GAZ_Y)
        fabric = M['canopy'] if g % 2 == 0 else M['canopy2']
        ob, parts, clo = parasol(g, cx, GAZ_Y, fabric)
        animate_parasol(g, ob, parts, clo)
        umbs.append(ob)
    return umbs


# ------------------------------------------------------------------ world / camera ------------------------------
def build_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(46); sky.sun_rotation = math.radians(235); sky.sun_disc = False
    sky.air_density = 1.0; sky.aerosol_density = 1.0; sky.ozone_density = 1.0
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.35
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sun = bpy.data.lights.new("sun", 'SUN'); sun.energy = 3.0; sun.angle = math.radians(1.2); sun.color = (1.0, 0.92, 0.8)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    d = Vector((-0.32, -0.42, 0.85)).normalized()
    so.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return so


def build_camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam"); cam.lens = 26; cam.sensor_fit = 'AUTO'; cam.clip_start = 0.05; cam.clip_end = 600
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    tgt = bpy.data.objects.new("cam_target", None); sc.collection.objects.link(tgt)
    cam.dof.use_dof = True; cam.dof.focus_object = tgt; cam.dof.aperture_fstop = 3.4
    tc = co.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    return co, tgt


CAM_KEYS = [  # frame, camera location, look-at target, f-stop
    (0,   (3.2, -1.6, 1.55),  (13.0, 3.0, 1.55), 4.0),
    (118, (6.2, -1.3, 1.60),  (16.0, 3.2, 1.45), 4.0),
    (196, (7.6, -0.6, 1.10),  (11.0, 2.2, 0.90), 3.0),
    (226, (9.0, 0.35, 0.62),  (10.45, 1.65, 0.30), 1.8),    # Stopa lands on its plate
    (262, (9.2, 0.55, 1.05),  (10.45, 1.65, 1.35), 1.8),    # post slides into the Stopa
    (300, (9.0, 0.45, 1.75),  (10.55, 1.70, 2.30), 1.8),    # Trojak settles on the post
    (338, (8.5, 0.60, 1.95),  (11.30, 1.75, 2.30), 1.8),    # beam slides into the Trojak arm
    (400, (6.8, -1.9, 2.20),  (14.0, 3.0, 2.00), 3.2),
    (520, (9.5, -4.0, 2.70),  (22.0, 3.2, 1.80), 3.4),
    (620, (15.5, -4.1, 2.20), (27.0, 3.2, 1.80), 3.4),
    (720, (21.5, -3.8, 1.90), (30.0, 3.2, 1.70), 3.4),
]


def animate_camera(co, tgt):
    for f, loc, t, fs in CAM_KEYS:
        co.location = loc; co.keyframe_insert('location', frame=f)
        tgt.location = t; tgt.keyframe_insert('location', frame=f)
        co.data.dof.aperture_fstop = fs; co.data.dof.keyframe_insert('aperture_fstop', frame=f)


def setup_render(w=1080, h=1920, spp=64):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NFR
    sc.cycles.samples = spp; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 3; sc.cycles.sample_clamp_indirect = 8
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'Medium High Contrast'
    except Exception: pass
    sc.view_settings.exposure = -0.45


def finalize_anim():
    for ob in bpy.data.objects:
        fix_constant(ob)


def build(w=1080, h=1920, spp=64, full=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_materials()
    setup_render(w, h, spp)
    build_world()
    build_street()
    co, tgt = build_camera()
    if full:
        build_furniture_and_parasols()
        for g, cx in enumerate(GAZ_X):
            gazebo(g, cx, GAZ_Y)
        animate_camera(co, tgt)
        finalize_anim()
    return co, tgt
