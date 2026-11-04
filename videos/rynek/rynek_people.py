"""Furniture, table settings, seated guests and walkers for the Rynek scene."""
import math, random
from mathutils import Vector
from rynek_core import *

SKIN = [(0.86, 0.66, 0.54), (0.78, 0.56, 0.43), (0.92, 0.74, 0.62), (0.62, 0.42, 0.31), (0.7, 0.5, 0.38), (0.95, 0.8, 0.7)]
HAIR = [(0.04, 0.03, 0.025), (0.2, 0.11, 0.06), (0.5, 0.33, 0.14), (0.72, 0.58, 0.32), (0.42, 0.42, 0.44), (0.1, 0.06, 0.04), (0.33, 0.14, 0.07)]
CLOTH = [(0.1, 0.16, 0.3), (0.55, 0.1, 0.1), (0.86, 0.83, 0.75), (0.17, 0.34, 0.24), (0.8, 0.58, 0.2), (0.1, 0.1, 0.12), (0.82, 0.48, 0.52),
         (0.22, 0.5, 0.62), (0.9, 0.9, 0.9), (0.3, 0.3, 0.34), (0.62, 0.7, 0.35), (0.35, 0.2, 0.45), (0.9, 0.45, 0.2), (0.7, 0.72, 0.78)]
PANTS = [(0.1, 0.12, 0.2), (0.07, 0.07, 0.08), (0.32, 0.26, 0.2), (0.55, 0.48, 0.38), (0.2, 0.22, 0.3), (0.4, 0.15, 0.15), (0.16, 0.3, 0.22)]


def build_materials_people():
    M['skin'] = [pbr("skin%d" % i, c, rough=0.5, bevel=0.0, sss=0.3, spec=0.45, vary=0.05) for i, c in enumerate(SKIN)]
    M['hair'] = [pbr("hair%d" % i, c, rough=0.45, bevel=0.0, spec=0.6, vary=0.08) for i, c in enumerate(HAIR)]
    M['top'] = [pbr("top%d" % i, c, rough=0.88, bevel=0.0, sheen=0.3, vary=0.08) for i, c in enumerate(CLOTH)]
    M['pants'] = [pbr("pants%d" % i, c, rough=0.85, bevel=0.0, vary=0.08) for i, c in enumerate(PANTS)]
    M['shoe'] = [pbr("shoe%d" % i, c, rough=0.4, bevel=0.0) for i, c in enumerate([(0.05, 0.04, 0.035), (0.28, 0.15, 0.08), (0.8, 0.8, 0.78), (0.35, 0.05, 0.05)])]
    M['chair'] = pbr("bentwood", (0.25, 0.13, 0.07), tex="wood_model_dom_2_1.jpg", tile=0.8, rough=0.38, bevel=0.003, vary=0.12, coat=0.3)
    M['seat'] = pbr("rattan_seat", (0.55, 0.38, 0.2), tex="teak_veneer_diff_2k.jpg", tile=0.5, rough=0.6, bevel=0.002, vary=0.1)
    M['tabletop'] = pbr("tabletop", (0.6, 0.4, 0.25), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                        tex_bump="teak_veneer_disp_2k.png", tile=0.9, bump=0.15, rough=0.5, bevel=0.003, vary=0.06)
    M['cloth_w'] = pbr("tablecloth", (0.93, 0.91, 0.86), rough=0.95, bevel=0.0, sheen=0.5)
    M['cloth_c'] = [pbr("tablecloth_c%d" % i, c, rough=0.95, bevel=0.0, sheen=0.4) for i, c in enumerate([(0.55, 0.12, 0.12), (0.2, 0.3, 0.42), (0.86, 0.8, 0.62)])]
    M['ceramic'] = pbr("ceramic", (0.92, 0.91, 0.88), rough=0.15, bevel=0.0, spec=0.8)
    M['glassware'] = pbr("glassware", (0.9, 0.95, 1.0), rough=0.02, spec=1.0, metal=0.15, bevel=0.0)
    M['drink'] = [pbr("drink%d" % i, c, rough=0.1, bevel=0.0, emit=c, emit_str=0.2) for i, c in enumerate([(0.7, 0.55, 0.1), (0.45, 0.05, 0.08), (0.9, 0.35, 0.05), (0.6, 0.42, 0.1)])]
    M['bottle'] = pbr("bottle", (0.04, 0.12, 0.05), rough=0.1, bevel=0.0, spec=0.9)
    M['food'] = [pbr("food%d" % i, c, rough=0.6, bevel=0.0) for i, c in enumerate([(0.6, 0.35, 0.15), (0.3, 0.45, 0.12), (0.7, 0.2, 0.1), (0.85, 0.7, 0.4)])]
    M['bread'] = pbr("bread", (0.62, 0.42, 0.2), rough=0.8, bevel=0.0)
    M['pedestal'] = pbr("pedestal", (0.03, 0.03, 0.035), rough=0.4, metal=0.6, bevel=0.003)


def seated_person(prefix, parent, r):
    """seated guest, faces local +X, origin = centre of the seat on the floor"""
    female = r.random() < 0.5
    mats = {'skin': r.choice(M['skin']), 'hair': r.choice(M['hair']), 'top': r.choice(M['top']), 'bottom': r.choice(M['pants']),
            'shoe': r.choice(M['shoe']), 'glassware': M['glassware'], 'drink': r.choice(M['drink'])}
    mb = MB()
    lean = r.uniform(-0.04, 0.1)
    yaw = r.uniform(-0.65, 0.65)
    for sy in (-1, 1):
        hip = (0.0, sy * 0.09, 0.56); knee = (0.42, sy * (0.10 + r.uniform(0, 0.05)), 0.53); ank = (0.47 + r.uniform(-0.04, 0.08), sy * 0.11, 0.09)
        if female and r.random() < 0.4:
            mb.tube('skin', knee, ank, 0.05, 0.036); mb.tube('bottom', hip, knee, 0.085, 0.07)
        else:
            mb.tube('bottom', hip, knee, 0.085, 0.065); mb.tube('bottom', knee, ank, 0.062, 0.048)
        mb.ellipsoid('shoe', (ank[0] + 0.06, ank[1], 0.045), (0.12, 0.05, 0.04), 1)
    mb.ellipsoid('bottom', (0.0, 0, 0.57), (0.15, 0.19, 0.105), 2)
    if female and r.random() < 0.5:
        mb.ellipsoid('bottom', (0.16, 0, 0.58), (0.26, 0.22, 0.085), 2)          # skirt over the thighs
    mb.ellipsoid('top', (-0.02 - lean * 0.2, 0, 0.88), (0.15, 0.205, 0.27), 2, tilt=lean)
    mb.ellipsoid('top', (-0.02 + lean * 0.5, 0, 1.06), (0.1, 0.25 if not female else 0.22, 0.1), 2)
    neck_top = (0.0 + lean * 0.7, 0, 1.2)
    mb.tube('skin', (0.0 + lean * 0.5, 0, 1.1), neck_top, 0.047, 0.044)
    hc = (0.015 + lean * 0.8, 0, 1.31)
    mb.ellipsoid('skin', hc, (0.1, 0.085, 0.115), 2, pivot=neck_top, rot_z=yaw)
    mb.ellipsoid('skin', (hc[0] + 0.095, 0, hc[2] - 0.02), (0.025, 0.017, 0.03), 1, pivot=neck_top, rot_z=yaw)          # nose
    style = r.choice(('short', 'short', 'long', 'bun', 'cap', 'bald' if not female else 'long'))
    if style != 'bald':
        mb.ellipsoid('hair', (hc[0] - 0.015, 0, hc[2] + 0.03), (0.108, 0.093, 0.1), 2, pivot=neck_top, rot_z=yaw)
    if style == 'long':
        mb.ellipsoid('hair', (hc[0] - 0.06, 0, hc[2] - 0.12), (0.075, 0.105, 0.2), 2, pivot=neck_top, rot_z=yaw)
    if style == 'bun':
        mb.ellipsoid('hair', (hc[0] - 0.08, 0, hc[2] + 0.12), (0.05, 0.05, 0.05), 1, pivot=neck_top, rot_z=yaw)
    for sy in (-1, 1):
        sh = (-0.02 + lean * 0.5, sy * (0.235 if not female else 0.2), 1.04)
        mb.ellipsoid('top', sh, (0.065, 0.065, 0.065), 1)
        pose = r.choice(('rest', 'rest', 'glass', 'gesture', 'rest2'))
        if pose == 'glass' and sy == 1 or (pose == 'glass' and r.random() < 0.3):
            elb = (0.17, sy * 0.25, 0.95); hand = (0.31, sy * 0.13, 1.07)
        elif pose == 'gesture':
            elb = (0.2, sy * 0.3, 0.9); hand = (0.38, sy * 0.24, 1.0)
        elif pose == 'rest2':
            elb = (0.1, sy * 0.3, 0.82); hand = (0.3, sy * 0.1, 0.8)
        else:
            elb = (0.14, sy * 0.27, 0.82); hand = (0.40, sy * 0.17, 0.795)
        long_sleeve = r.random() < 0.55
        mb.tube('top', sh, elb, 0.052, 0.045)
        mb.tube('top' if long_sleeve else 'skin', elb, hand, 0.043, 0.032)
        mb.ellipsoid('skin', (hand[0] + 0.03, hand[1], hand[2]), (0.055, 0.03, 0.026), 1)
        if pose == 'glass' and (sy == 1 or True):
            mb.tube('glassware', (hand[0] + 0.03, hand[1], hand[2] - 0.05), (hand[0] + 0.03, hand[1], hand[2] + 0.07), 0.032, 0.036, 10, caps=False)
            mb.tube('drink', (hand[0] + 0.03, hand[1], hand[2] - 0.03), (hand[0] + 0.03, hand[1], hand[2] + 0.035), 0.028, 0.032, 8, caps=False)
    root = empty(prefix, parent=parent)
    mb.emit(prefix, mats, parent=root, smooth=True)
    return root


def chair_mb(mb):
    """bentwood bistro chair at local origin, seat centre; back at -X"""
    mb.box('chair', (0, 0, 0.455), (0.44, 0.42, 0.03), uvm=1.0)
    mb.box('seat', (0, 0, 0.472), (0.38, 0.37, 0.012), uvm=1.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.tube('chair', (sx * 0.17, sy * 0.17, 0.0), (sx * 0.19, sy * 0.19, 0.44), 0.014, 0.018, 8, caps=False)
    for sy in (-1, 1):
        mb.tube('chair', (-0.19, sy * 0.18, 0.44), (-0.22, sy * 0.17, 0.92), 0.016, 0.014, 8, caps=False)
    mb.box('chair', (-0.22, 0, 0.9), (0.025, 0.37, 0.05))
    mb.box('chair', (-0.215, 0, 0.72), (0.02, 0.3, 0.03))
    mb.box('chair', (0.0, 0, 0.18), (0.36, 0.02, 0.02)); mb.box('chair', (0.0, 0, 0.18), (0.02, 0.36, 0.02))


def table_group(g, cx, cy, guests=True, R=0.9, n=8, seed=0):
    """round table with cloth, place settings, chairs and (optionally) seated guests. returns (guest_roots, root)"""
    r = random.Random(900 + g * 13 + seed)
    root = empty("table%d" % g, (cx, cy, 0))
    mb = MB()
    mats = {'tabletop': M['tabletop'], 'cloth': r.choice([M['cloth_w'], M['cloth_w']] + M['cloth_c']), 'pedestal': M['pedestal'],
            'ceramic': M['ceramic'], 'glassware': M['glassware'], 'bottle': M['bottle'], 'bread': M['bread'], 'chair': M['chair'],
            'seat': M['seat'], 'leaf': M['leaf'], 'flower': M['flower_r'], 'flower2': M['flower_w'], 'wine': M['drink'][1], 'water': M['drink'][0],
            'food0': M['food'][0], 'food1': M['food'][1], 'food2': M['food'][2], 'food3': M['food'][3], 'iron': M['iron']}
    mb.tube('pedestal', (0, 0, 0.02), (0, 0, 0.72), 0.05, 0.045, 12, caps=False)
    _cyl(mb, 'pedestal', 0.0, 0.0, 0.0, 0.025, 0.36, 24)
    _cyl(mb, 'tabletop', 0.0, 0.0, 0.715, 0.76, 0.87, 48)
    if r.random() < 0.75:
        _cyl(mb, 'cloth', 0.0, 0.0, 0.759, 0.77, 0.92, 48)                  # cloth top
        _cyl(mb, 'cloth', 0.0, 0.0, 0.52, 0.76, 0.915, 48, r1=0.935)        # drape
    chairs = []
    for k in range(n):
        a = k * 2 * math.pi / n + r.uniform(-0.05, 0.05)
        ca, sa = math.cos(a), math.sin(a)
        px, py = ca * 1.1, sa * 1.1
        cm = MB()
        chair_mb(cm)
        cm.emit("chair%d_%d" % (g, k), mats, parent=root, loc=(px, py, 0), rot=(0, 0, a + math.pi), smooth=False)
        # place setting
        sx, sy = ca * 0.58, sa * 0.58
        _cyl(mb, 'ceramic', sx, sy, 0.764, 0.772, 0.125, 24)
        _cyl(mb, 'ceramic', sx, sy, 0.772, 0.776, 0.07, 20)
        food = r.choice(('food0', 'food1', 'food2', 'food3'))
        if r.random() < 0.8:
            mb.ellipsoid(food, (sx, sy, 0.78), (0.06, 0.05, 0.02), 1)
            mb.ellipsoid(r.choice(('food1', 'food2')), (sx + 0.02, sy - 0.02, 0.79), (0.03, 0.03, 0.015), 1)
        for sd, ln in ((-1, 0.16), (1, 0.16)):                                # fork and knife
            fx = sx + (-sa) * sd * 0.17; fy = sy + ca * sd * 0.17
            mb.box('iron', (fx, fy, 0.763), (0.012, ln, 0.004), rot_z=a + math.pi / 2 + math.pi / 2 * 0)
        gx, gy = ca * 0.62 + (-sa) * 0.15, sa * 0.62 + ca * 0.15
        mb.tube('glassware', (gx, gy, 0.762), (gx, gy, 0.86), 0.03, 0.037, 10, caps=False)
        mb.tube('wine' if r.random() < 0.5 else 'water', (gx, gy, 0.77), (gx, gy, 0.82), 0.027, 0.033, 8, caps=False)
        mb.tube('glassware', (gx, gy, 0.75), (gx, gy, 0.765), 0.012, 0.012, 6, caps=False)
        if guests:
            chairs.append((px, py, a))
    # centre of the table: flowers, bottle, bread basket, candle
    mb.tube('glassware', (0, 0, 0.762), (0, 0, 0.9), 0.045, 0.055, 12, caps=False)
    for i in range(9):
        aa = i * 0.7; rr_ = 0.035 + 0.02 * (i % 3)
        mb.blob('leaf', (math.cos(aa) * rr_, math.sin(aa) * rr_, 0.93 + 0.03 * (i % 3)), 0.04, 1)
        mb.blob(r.choice(('flower', 'flower2', 'flower')), (math.cos(aa + 1) * 0.05, math.sin(aa + 1) * 0.05, 0.99 + 0.02 * (i % 4)), 0.028, 0)
    mb.tube('bottle', (0.22, 0.12, 0.762), (0.22, 0.12, 0.98), 0.04, 0.04, 10, caps=False)
    mb.tube('bottle', (0.22, 0.12, 0.96), (0.22, 0.12, 1.04), 0.016, 0.016, 8)
    mb.ellipsoid('bread', (-0.2, -0.16, 0.8), (0.09, 0.09, 0.04), 1)
    mb.tube('bottle', (-0.22, 0.2, 0.762), (-0.22, 0.2, 0.93), 0.036, 0.036, 10, caps=False)
    mb.emit("tbl%d" % g, mats, parent=root, smooth=False)
    ppl = []
    if guests:
        for k, (px, py, a) in enumerate(chairs):
            holder = empty("seat%d_%d" % (g, k), (px, py, 0), (0, 0, a + math.pi), parent=root)
            p = seated_person("guest%d_%d" % (g, k), holder, r)
            p.location = (-0.03, 0, 0.0)
            ppl.append(holder)
    return ppl, root


def _cyl(mb, key, x, y, z0, z1, r, seg=24, r1=None):
    """vertical cylinder at (x,y) from z0 to absolute z1, top radius r, bottom radius r1"""
    b = mb.bm(key); uv = b.loops.layers.uv.verify()
    rb = r if r1 is None else r1
    lo = [b.verts.new((x + rb * math.cos(2 * math.pi * i / seg), y + rb * math.sin(2 * math.pi * i / seg), z0)) for i in range(seg)]
    hi = [b.verts.new((x + r * math.cos(2 * math.pi * i / seg), y + r * math.sin(2 * math.pi * i / seg), z1)) for i in range(seg)]
    fs = [b.faces.new((lo[i], lo[(i + 1) % seg], hi[(i + 1) % seg], hi[i])) for i in range(seg)]
    fs.append(b.faces.new(lo[::-1])); fs.append(b.faces.new(hi))
    for f in fs:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.y) if abs(f.normal.z) > 0.9 else (math.atan2(l.vert.co.y - y, l.vert.co.x - x) * rb, l.vert.co.z)


def animate_guests(holders, f0, f1, r):
    """gentle conversation motion: breathing/leaning, keyed every 10 frames"""
    for h in holders:
        base = h.rotation_euler.copy()
        ph = r.uniform(0, 6.28); amp = r.uniform(0.015, 0.05); sp = r.uniform(0.18, 0.3)
        for f in range(f0, f1 + 1, 12):
            h.rotation_euler = (0, 0, base.z + amp * math.sin(ph + f * sp)); h.keyframe_insert('rotation_euler', frame=f)


def hide_until(obs, f):
    for o in obs:
        key_vis(o, 0, False); key_vis(o, f, True)


# ------------------------------------------------------------------ standing / walking people -----------------------
def _body_mats(r):
    return {'skin': r.choice(M['skin']), 'hair': r.choice(M['hair']), 'top': r.choice(M['top']), 'bottom': r.choice(M['pants']),
            'shoe': r.choice(M['shoe'])}


def _upper_body(mb, r, female, lean=0.0):
    """torso/head for a standing figure, origin at the feet, facing +X; returns (hip_z, shoulder_z)"""
    yaw = r.uniform(-0.5, 0.5)
    mb.ellipsoid('bottom', (0, 0, 0.95), (0.14, 0.18, 0.1), 2)
    if female and r.random() < 0.45:
        mb.tube('bottom', (0, 0, 0.98), (0.0, 0, 0.55), 0.2, 0.25, 12, caps=False)        # skirt / dress
    mb.ellipsoid('top', (0, 0, 1.22), (0.15, 0.2 if not female else 0.18, 0.3), 2, tilt=lean)
    mb.ellipsoid('top', (0, 0, 1.45), (0.1, 0.25 if not female else 0.22, 0.1), 2)
    mb.tube('skin', (0, 0, 1.5), (0.01, 0, 1.62), 0.047, 0.044)
    hc = (0.02, 0, 1.74)
    mb.ellipsoid('skin', hc, (0.1, 0.085, 0.115), 2, pivot=(0.01, 0, 1.62), rot_z=yaw)
    mb.ellipsoid('skin', (hc[0] + 0.095, 0, hc[2] - 0.02), (0.025, 0.017, 0.03), 1, pivot=(0.01, 0, 1.62), rot_z=yaw)
    style = r.choice(('short', 'short', 'long', 'bun', 'cap', 'bald' if not female else 'long'))
    if style != 'bald': mb.ellipsoid('hair', (hc[0] - 0.015, 0, hc[2] + 0.03), (0.108, 0.093, 0.1), 2, pivot=(0.01, 0, 1.62), rot_z=yaw)
    if style == 'long': mb.ellipsoid('hair', (hc[0] - 0.06, 0, hc[2] - 0.12), (0.075, 0.105, 0.2), 2, pivot=(0.01, 0, 1.62), rot_z=yaw)
    if style == 'bun': mb.ellipsoid('hair', (hc[0] - 0.08, 0, hc[2] + 0.12), (0.05, 0.05, 0.05), 1, pivot=(0.01, 0, 1.62), rot_z=yaw)


def standing_person(prefix, r, loc, yaw, parent=None):
    mats = _body_mats(r); female = r.random() < 0.5
    mb = MB(); _upper_body(mb, r, female)
    for sy in (-1, 1):
        mb.tube('bottom', (0, sy * 0.09, 0.92), (0.02, sy * 0.1, 0.48), 0.085, 0.065)
        mb.tube('bottom', (0.02, sy * 0.1, 0.48), (0.0, sy * 0.1, 0.07), 0.062, 0.048)
        mb.ellipsoid('shoe', (0.06, sy * 0.1, 0.04), (0.12, 0.05, 0.04), 1)
        sh = (0, sy * 0.225, 1.43); pose = r.choice(('down', 'down', 'phone', 'gest'))
        if pose == 'phone' and sy == 1: el = (0.14, sy * 0.26, 1.18); hd = (0.26, sy * 0.1, 1.4)
        elif pose == 'gest': el = (0.16, sy * 0.3, 1.2); hd = (0.32, sy * 0.22, 1.32)
        else: el = (0.0, sy * 0.28, 1.15); hd = (0.04, sy * 0.28, 0.9)
        mb.tube('top', sh, el, 0.052, 0.045); mb.tube('top' if r.random() < 0.5 else 'skin', el, hd, 0.043, 0.032)
        mb.ellipsoid('skin', (hd[0] + 0.02, hd[1], hd[2]), (0.05, 0.03, 0.03), 1)
    root = empty(prefix, loc, (0, 0, yaw), parent)
    mb.emit(prefix, mats, parent=root, smooth=True)
    return root


def walker(prefix, r, p0, p1, f0, f1):
    """walking figure from p0 to p1 between frames f0..f1 with swinging legs/arms"""
    mats = _body_mats(r); female = r.random() < 0.5
    p0 = Vector((p0[0], p0[1], 0.0)); p1 = Vector((p1[0], p1[1], 0.0)); d = p1 - p0
    yaw = math.atan2(d.y, d.x)
    root = empty(prefix, (p0.x, p0.y, 0), (0, 0, yaw))
    mb = MB(); _upper_body(mb, r, female, lean=0.05)
    mb.emit(prefix, mats, parent=root, smooth=True)
    legs = []; arms = []
    for sy in (-1, 1):
        hip = empty(prefix + "_h", (0, sy * 0.09, 0.93), parent=root)
        lm = MB()
        lm.tube('bottom', (0, 0, 0), (0.0, 0, -0.45), 0.085, 0.065); lm.tube('bottom', (0, 0, -0.45), (0.0, 0, -0.86), 0.062, 0.048)
        lm.ellipsoid('shoe', (0.05, 0, -0.9), (0.12, 0.05, 0.04), 1)
        lm.emit(prefix + "_l", mats, parent=hip, smooth=True); legs.append((sy, hip))
        sh = empty(prefix + "_s", (0, sy * 0.225, 1.43), parent=root)
        am = MB(); long_s = r.random() < 0.5
        am.tube('top', (0, 0, 0), (0, sy * 0.02, -0.28), 0.052, 0.045)
        am.tube('top' if long_s else 'skin', (0, sy * 0.02, -0.28), (0.02, sy * 0.03, -0.56), 0.043, 0.032)
        am.ellipsoid('skin', (0.03, sy * 0.03, -0.6), (0.04, 0.03, 0.06), 1)
        am.emit(prefix + "_a", mats, parent=sh, smooth=True); arms.append((sy, sh))
    ph = r.uniform(0, 6.28)
    for f in range(f0, f1 + 1, 5):
        t = (f - f0) / (f1 - f0)
        key_loc(root, f, p0.lerp(p1, t))
        w = 2 * math.pi * (f - f0) / 28.0 + ph
        for sy, h in legs: h.rotation_euler = (0, 0.5 * sy * math.sin(w), 0); h.keyframe_insert('rotation_euler', frame=f)
        for sy, s in arms: s.rotation_euler = (0, -0.4 * sy * math.sin(w), 0); s.keyframe_insert('rotation_euler', frame=f)
    return root
