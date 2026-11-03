"""RIVON gazebo with a FLAT roof, built from exact RIVON STEP meshes (Stopa feet, Trojak corner connectors) + 90x90 timber.
Assembly / quick disassembly / re-assembly are animated with lifecycle() spans. Plus the folding parasols the gazebos replace."""
import math, random
from mathutils import Vector, Matrix
from rynek_core import *

W = 3.0                     # post centre-to-centre
POST = 0.09                 # 90x90 timber
POST_H = 2.40
RH = 0.15                   # joist height
OVER = 0.45                 # roof overhang beyond the beam ring
_stl = {}


def build_materials_gaz():
    M['rivon'] = pbr("rivon_black", (0.012, 0.012, 0.013), rough=0.42, spec=0.55, coat=0.15, bevel=0.0012)     # RAL 9005 powder coat
    M['timber'] = pbr("timber_post", (0.8, 0.6, 0.4), tex="olive_veneer_diff_2k.jpg", tex_rough="olive_veneer_rough_2k.exr",
                      tex_bump="olive_veneer_disp_2k.png", tile=0.8, bump=0.2, rough=0.55, bevel=0.003, vary=0.1, mult=(1.0, 0.88, 0.7))
    M['joist'] = pbr("timber_joist", (0.7, 0.5, 0.3), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                     tex_bump="teak_veneer_disp_2k.png", tile=0.8, bump=0.15, rough=0.55, bevel=0.003, vary=0.12)
    M['lining'] = pbr("deck_lining", (0.7, 0.5, 0.3), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                      tex_bump="teak_veneer_disp_2k.png", tile=0.35, bump=0.15, rough=0.5, bevel=0.0, mult=(0.95, 0.85, 0.72))
    M['membrane'] = procedural("roof_membrane", (0.07, 0.07, 0.075), (0.11, 0.11, 0.115), scale=30, rough=0.75, bump=0.1, spec=0.3)
    M['zinc'] = pbr("zinc", (0.55, 0.57, 0.6), rough=0.35, metal=0.9, bevel=0.002, grime=0.3)
    M['fascia'] = pbr("fascia_anthracite", (0.05, 0.055, 0.06), rough=0.4, bevel=0.003, grime=0.3)
    M['canopy_a'] = parasol_fabric((0.9, 0.84, 0.68), (0.74, 0.34, 0.24))
    M['canopy_b'] = parasol_fabric((0.9, 0.86, 0.78), (0.18, 0.3, 0.42))
    M['pole'] = pbr("pole", (0.03, 0.03, 0.035), rough=0.45, metal=0.7, bevel=0.002)
    M['pweight'] = pbr("weight", (0.35, 0.34, 0.32), rough=0.9, bevel=0.01)


def parasol_fabric(c1, c2):
    m, nt, bsdf = mat_new("parasol_fabric")
    from rynek_core import _math, _mix
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    at = _math(nt, 'ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    k = _math(nt, 'FLOOR', _math(nt, 'MULTIPLY', _math(nt, 'ADD', at, math.pi), 16.0 / (2 * math.pi)))
    f = _math(nt, 'MODULO', k, 2.0)
    col = _mix(nt, c1, c2, f)
    nt.links.new(col, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.92; bsdf.inputs['Sheen Weight'].default_value = 0.6
    return m


# ------------------------------------------------------------------ RIVON connectors (exact STEP meshes) -------
def import_stl(name):
    if name in _stl: return _stl[name]
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(CAD, name + ".stl"))
    new = [o for o in bpy.data.objects if o not in before][0]
    me = new.data
    me.transform(Matrix.Scale(0.001, 4))             # mm -> m
    bpy.data.objects.remove(new, do_unlink=True)
    me.name = "RIVON_" + name
    me.materials.append(M['rivon'])
    for p in me.polygons: p.use_smooth = False
    me.update()
    _stl[name] = me
    return me


def stopa(loc):
    ob = new_obj("RIVON_Stopa", import_stl("Stopa"), None, (loc[0] - 0.05, loc[1] - 0.05, loc[2] + 0.002))
    return ob


def trojak(post_c, top_z, corner):
    """Trojak turned upside down (socket over the post top, arms +X/+Y), rotated 90 deg per corner"""
    ob = new_obj("RIVON_Trojak", import_stl("Trojak"), None)
    Rz = Matrix.Rotation(corner * math.pi / 2, 4, 'Z'); Rx = Matrix.Rotation(math.pi, 4, 'X')
    off = Vector((0.05, -0.05, 0.098))
    ob.matrix_world = Matrix.Translation((post_c[0], post_c[1], top_z)) @ Rz @ Matrix.Translation(-off) @ Rx
    loc = ob.matrix_world.to_translation(); rot = ob.matrix_world.to_euler()
    ob.location = loc; ob.rotation_euler = rot
    return ob


# ------------------------------------------------------------------ gazebo module ----------------------------
# One long seating zone = identical RIVON modules side by side. Neighbouring modules have their own posts 0.2 m apart
# (double posts, Trojak sockets side by side) and share one continuous flat roof.
WX = 3.0                    # post centre-to-centre along the zone
WY = 3.7                    # post centre-to-centre across the zone
PITCH = WX + 0.2
PH = {'stopa': (0, 14, 3), 'post': (14, 22, 4), 'tro': (44, 22, 4), 'beam': (70, 24, 6), 'roof': (100, 30, 0)}
LIGHTS_AT = 135


def _asm(a, s, key, i):
    off, dur, stag = PH[key]
    t_in = int(round(a + (off + i * stag) * s)); return t_in, t_in + max(5, int(round(dur * s)))


def _dis(d, key, i):
    base = {'roof': (0, 26, 0), 'beam': (16, 18, 5), 'tro': (40, 18, 4), 'post': (52, 22, 4)}[key]
    t0 = d + base[0] + i * base[2]; return t0, t0 + base[1]


def module(c, cx, cy, n_mod, assemblies, dismantle=None, dis_stag=5):
    """assemblies: list of (start_frame, speed, stagger); the module starts at start + c*stagger.
    dismantle: (start_frame, stagger) for the quick take-down between the first and second assembly."""
    topz = POST_H + 0.002
    arm_z = topz - 0.048
    hx, hy = WX / 2, WY / 2
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    a_list = [(a0 + c * st, s) for (a0, s, st) in assemblies]
    d0 = None if dismantle is None else dismantle[0] + c * dismantle[1]

    def spans_for(key, i, off_in):
        sp = []
        for n, (a, s) in enumerate(a_list):
            t_in, t_land = _asm(a, s, key, i)
            if d0 is not None and n == 0:
                o0, o1 = _dis(d0, key, i)
                sp.append((t_in, t_land, o0, o1, off_in, off_in))
            else:
                sp.append((t_in, t_land, None, None, off_in, off_in))
        return sp
    for i, (dx, dy) in enumerate(corners):
        px, py = cx + dx, cy + dy
        s_ = stopa((px, py, 0))
        a, sp = a_list[0]; t_in, t_land = _asm(a, sp, 'stopa', i)
        lifecycle([s_], s_.location, [(t_in, t_land, None, None, (0, 0, 1.7), (0, 0, 1.7))])
        p = box("post", (POST, POST, POST_H), (px, py, POST_H / 2 + 0.002), M['timber'])
        lifecycle([p], p.location, spans_for('post', i, (0, 0, 2.4)))
        tj = trojak((px, py), topz, i)
        lifecycle([tj], tj.location, spans_for('tro', i, (0, 0, 1.5)))
    eng = 0.15
    runs = [((-hx, -hy), (hx, -hy)), ((hx, -hy), (hx, hy)), ((hx, hy), (-hx, hy)), ((-hx, hy), (-hx, -hy))]
    for j, (a_, b_) in enumerate(runs):
        va = Vector((cx + a_[0], cy + a_[1], arm_z)); vb = Vector((cx + b_[0], cy + b_[1], arm_z))
        d = (vb - va).normalized()
        bm_ = between("beam", va + d * eng, vb - d * eng, (POST, POST), M['timber'])
        side = Vector((d.y, -d.x, 0))
        lifecycle([bm_], bm_.location, spans_for('beam', j, tuple(side * 0.9 + Vector((0, 0, 0.55)))))
    # ---- roof cassette for this module: joists 50x150 across the zone, lining deck, membrane, zinc upstand, fascia
    zr = topz + 0.004
    root = empty("roof%d" % c, (cx, cy, zr))
    ox0 = 0.45 if c == 0 else 0.1; ox1 = 0.45 if c == n_mod - 1 else 0.1
    hyr = hy + 0.45
    xa, xb = -hx - ox0, hx + ox1; xm = (xa + xb) / 2; lx = xb - xa
    kids = []
    nj = int(round(lx / 0.5)) + 1
    for i in range(nj):
        x = xa + 0.025 + (lx - 0.05) * i / (nj - 1)
        kids.append(box("joist", (0.05, 2 * hyr, RH), (x, 0, RH / 2), M['joist'], parent=root))
    kids.append(box("deck", (lx, 2 * hyr, 0.022), (xm, 0, RH + 0.011), M['lining'], parent=root))
    kids.append(box("membrane", (lx + 0.004, 2 * hyr + 0.02, 0.01), (xm, 0, RH + 0.027), M['membrane'], parent=root, grain=False))
    for sgn in (-1, 1):
        kids.append(box("fascia", (lx, 0.025, 0.24), (xm, sgn * (hyr + 0.0125), RH / 2 + 0.02), M['fascia'], parent=root))
        kids.append(box("upstand", (lx, 0.03, 0.05), (xm, sgn * (hyr - 0.015), RH + 0.06), M['zinc'], parent=root))
    if c == 0:
        kids.append(box("fascia", (0.025, 2 * hyr + 0.05, 0.24), (xa - 0.0125, 0, RH / 2 + 0.02), M['fascia'], parent=root))
        kids.append(box("upstand", (0.03, 2 * hyr, 0.05), (xa + 0.015, 0, RH + 0.06), M['zinc'], parent=root))
    if c == n_mod - 1:
        kids.append(box("fascia", (0.025, 2 * hyr + 0.05, 0.24), (xb + 0.0125, 0, RH / 2 + 0.02), M['fascia'], parent=root))
        kids.append(box("upstand", (0.03, 2 * hyr, 0.05), (xb - 0.015, 0, RH + 0.06), M['zinc'], parent=root))
        kids.append(box("spout", (0.06, 0.12, 0.04), (xb - 0.03, -hyr + 0.06, RH + 0.04), M['zinc'], parent=root))
    sp = []
    for n, (a, s) in enumerate(a_list):
        t_in, t_land = _asm(a, s, 'roof', 0)
        if d0 is not None and n == 0:
            o0, o1 = _dis(d0, 'roof', 0); sp.append((t_in, t_land, o0, o1, (0, 0, 1.8), (0, 0, 1.8)))
        else: sp.append((t_in, t_land, None, None, (0, 0, 1.8), (0, 0, 1.8)))
    lifecycle(kids, (cx, cy, zr), sp, root=root)
    # ---- festoon bulbs under the front/back beams + pendant lamp over the table
    lights = []
    for sgn in (-1, 1):
        for t in range(1, 11):
            u = t / 11.0; x = -hx + 0.1 + (WX - 0.2) * u; sag = 0.14 * 4 * u * (1 - u)
            lights.append(ball("bulb", 0.03, (cx + x, cy + sgn * (hy - 0.12), topz - 0.16 - sag), M['bulbmat'], seg=8, rings=6))
    lights.append(cyl("cable", 0.004, 0.5, (cx, cy, topz - 0.25), M['iron'], seg=6))
    sh = cyl("shade", 0.22, 0.14, (cx, cy, topz - 0.55), M['zinc'], seg=20, r2=0.07, cap=False); sh.rotation_euler = (math.pi, 0, 0)
    lights.append(sh)
    lights.append(ball("pendant_bulb", 0.05, (cx, cy, topz - 0.6), M['bulbmat'], seg=10, rings=6))
    for o in lights: key_vis(o, 0, False)
    for n, (a, s) in enumerate(a_list):
        t_on = int(round(a + LIGHTS_AT * s))
        for o in lights: key_vis(o, t_on, True)
        if d0 is not None and n == 0:
            for o in lights: key_vis(o, d0, False)


# ------------------------------------------------------------------ parasols ------------------------------------
def parasol(cx, cy, fabric):
    R = 1.45; ztop = 2.78; zrim = 2.12
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
            sc = 0.07 if (k == rings and i % 2 == 1) else 0.0
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz + sc - 0.03 * (k / rings) * (1 if i % 2 == 1 else 0))))
        grid.append(ring)
    for i in range(segs):
        bm.faces.new((apex, grid[0][(i + 1) % segs], grid[0][i]))
    for k in range(rings - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((grid[k][i], grid[k][j], grid[k + 1][j], grid[k + 1][i]))
    skirt = [bm.verts.new((v.co.x, v.co.y, v.co.z - 0.14)) for v in grid[-1]]
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((grid[-1][i], grid[-1][j], skirt[j], skirt[i]))
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.y)
    bm.to_mesh(me); bm.free()
    set_smooth(me)
    ob = new_obj("parasol_canopy", me, fabric, (cx, cy, 0))
    ob.shape_key_add(name="open"); clo = ob.shape_key_add(name="closed")
    for idx, v in enumerate(me.vertices):
        p = v.co.copy(); rad = math.hypot(p.x, p.y); a = math.atan2(p.y, p.x)
        newr = 0.045 + 0.05 * (rad / R)
        ang_f = 1.0 + 0.1 * math.sin(a * 8)
        newz = ztop - (rad / R) * 1.55 + (0.07 if (abs(math.sin(a * 4)) < 0.3 and rad > R * 0.95) else 0)
        clo.data[idx].co = (newr * ang_f * math.cos(a), newr * ang_f * math.sin(a), newz)
    clo.value = 0.0
    pole = cyl("pole", 0.026, 2.78, (cx, cy, 1.39), M['pole'], seg=12)
    cap = cyl("pole_cap", 0.02, 0.18, (cx, cy, 2.86), M['pole'], seg=8)
    base = cyl("pbase", 0.38, 0.07, (cx, cy, 0.035), M['pole'], seg=28)
    weight = ball("pweight", 0.2, (cx, cy, 0.1), M['pweight'], scale=(1.6, 1.6, 0.3))
    return ob, [ob, pole, cap, base, weight], clo


def animate_parasol(ob, parts, clo, f0, fold=34, sink=28):
    f1 = f0 + fold; f2 = f1 + sink
    clo.value = 0.0; clo.keyframe_insert('value', frame=f0)
    clo.value = 1.0; clo.keyframe_insert('value', frame=f1)
    key_rot(ob, f0, (0, 0, 0)); key_rot(ob, f1, (0, 0, 0.45))
    for p in parts:
        z0 = p.location.z
        key_loc(p, f1 + 4, (p.location.x, p.location.y, z0)); key_loc(p, f2, (p.location.x, p.location.y, z0 - 3.2))
        key_vis(p, 0, True); key_vis(p, f2 + 1, False)
