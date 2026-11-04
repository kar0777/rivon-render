"""Timeline of the RIVON film (30 s @ 30 fps = 900 frames, 9:16).

   0 -209  lab        pergola assembles piece by piece (stopa -> posts -> trojak -> beams -> mocowanie -> rafters -> screws)
 210 -689  5 x 96     carport, barbecue, summer kitchen, lounge, cafe  (pergola fixed, orbiting camera, hard cuts)
 690 -899  lab        pergola disassembles (reverse, 2x speed), hero Trojak 3D remains, CTA text is added in post (finish.py)

All connector transforms are RIGID (translation + rotation about the part's own axis for screws); nothing is scaled or edited."""
import math
import numpy as np
import bpy, mathutils
from mathutils import Matrix, Vector, Quaternion
from film_lib import load_json

FPS, NF = 30, 900
LAB1 = (0, 209); SCENES = [("carport", 210), ("barbecue", 306), ("kitchen", 402), ("lounge", 498), ("commercial", 594)]; SCENE_LEN = 96
LAB2 = (690, 899)
A_END = 200.0                                    # assembly clock length (frames)
HERO_ID = "TROJAK_C2"


def clamp01(x): return max(0.0, min(1.0, x))
def e_out(u): return 1 - (1 - u) ** 3
def e_io(u): return u * u * (3 - 2 * u)
def e_back(u):                                   # tiny settle: slight overshoot then rest
    c1 = 0.9; c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


# ----------------------------------------------------------------------------------------------- assembly plan
def build_plan():
    L = load_json("layout.json"); objs = {o.name: o for o in bpy.data.collections["PERGOLA"].objects}
    plan = {}                                                      # id -> dict(obj, t0, t1, off, kind)
    def add(pid, obj, t0, t1, off, ease=e_out): plan[pid] = dict(obj=obj, t0=t0, t1=t1, off=Vector(off), ease=ease)
    for k in range(1, 5):
        add(f"STOPA_C{k}", objs[f"INST_STOPA_C{k}"], 14 + 4 * (k - 1), 42 + 4 * (k - 1), (0, 0, 3.2))
        add(f"POST_C{k}", objs[f"POST_C{k}"], 42 + 5 * (k - 1), 78 + 5 * (k - 1), (0, 0, 4.4))
        add(f"TROJAK_C{k}", objs[f"INST_TROJAK_C{k}"], 78 + 4 * (k - 1), 104 + 4 * (k - 1), (0, 0, 1.6))
    add("BEAM_LONG_L", objs["BEAM_LONG_L"], 104, 140, (0, -9.0, 0), e_io); add("BEAM_LONG_R", objs["BEAM_LONG_R"], 110, 146, (0, 9.0, 0), e_io)
    add("BEAM_END_A", objs["BEAM_END_A"], 130, 160, (-8.0, 0, 0), e_io); add("BEAM_END_B", objs["BEAM_END_B"], 136, 166, (8.0, 0, 0), e_io)
    for i in range(11):
        sgn = {"L": 1.0, "R": -1.0}
        for s in ("L", "R"):
            add(f"MOCOW_{s}_{i}", objs[f"INST_MOCOW_{s}_{i}"], 146 + i * 1.1 + (1.5 if s == "R" else 0), 146 + i * 1.1 + 17 + (1.5 if s == "R" else 0), (sgn[s] * 0.9, 0, 0.4))
        add(f"RAFTER_{i}", objs[f"RAFTER_{i}"], 152 + i * 2.0, 152 + i * 2.0 + 20, (0, 0, 1.8))
    # screws follow the part they fasten
    scr = {}
    for i, f in enumerate(L["fasteners"]):
        o = objs[f"SCREW_{i:03d}"]; part = f["part"]; ax = Vector(f["axis_to_timber"]).normalized()
        base_t = plan[part]["t1"] if part in plan else 150
        if part.startswith("STOPA"): base_t = plan["POST_C" + part[-1]]["t1"] - 6
        if part.startswith("MOCOW"): base_t = max(plan[part]["t1"], 190 if False else plan[part]["t1"]) + 6
        t0 = base_t + (i % 7) * 1.3; scr[f"SCREW_{i:03d}"] = dict(obj=o, t0=t0, t1=t0 + 12, off=-ax * 0.10, spin=5.0 * math.pi, ease=e_out)
    plan.update(scr)
    return plan


class Anim:
    def __init__(self):
        bpy.context.view_layer.update(); self.plan = build_plan()
        for k, p in self.plan.items():
            o = p["obj"]; o.rotation_mode = "QUATERNION"
            p["loc0"] = o.location.copy(); p["q0"] = o.rotation_quaternion.copy()
        self.hero = self.plan[HERO_ID]
        self.hero_center = self._center(self.hero["obj"])

    @staticmethod
    def _center(obj):
        pts = []
        stack = [obj]
        while stack:
            o = stack.pop(); stack += list(o.children)
            if o.type == "MESH": pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        a = np.array([list(p) for p in pts]); return Vector(((a.min(0) + a.max(0)) / 2).tolist())

    # ---------------------------------------------------------------- state of one part at assembly clock a (frames)
    def part_state(self, p, a):
        u = clamp01((a - p["t0"]) / (p["t1"] - p["t0"]))
        vis = a > p["t0"] - 1e-6
        k = 1.0 - p["ease"](u)
        off = p["off"] * k
        loc = p["loc0"] + off; q = p["q0"].copy()
        sp = p.get("spin")
        if sp:                                                      # screw: rotate about its own long axis while travelling in
            ang = sp * k; ax_local = Vector((0, 0, 1)); qs = Quaternion(ax_local, ang); q = q @ qs
        return loc, q, vis

    def set_assembly(self, a):
        for k, p in self.plan.items():
            if k == HERO_ID: continue
            loc, q, vis = self.part_state(p, a)
            o = p["obj"]; o.location = loc; o.rotation_quaternion = q; o.hide_render = not vis; o.hide_viewport = not vis
        loc, q, vis = self.part_state(self.hero, a)
        o = self.hero["obj"]; o.location = loc; o.rotation_quaternion = q; o.hide_render = False

    def set_hero(self, f):
        """hero Trojak 3D leaves its post position, floats to the lab centre and turns slowly (rigid motion only)."""
        o = self.hero["obj"]
        u = e_io(clamp01((f - 758) / 40.0)); hp = Vector((0.0, 0.0, 1.25))
        th = math.radians(18.0 + (f - 758) * 1.6)
        base_loc, base_q = self.hero["loc0"], self.hero["q0"]
        M0 = Matrix.Translation(base_loc) @ base_q.to_matrix().to_4x4()
        c0 = self.hero_center
        # centre of mesh in world at rest: c0 ; move it to hp, spin about vertical axis through hp
        T = Matrix.Translation((hp - c0) * u)
        R = Matrix.Translation(c0 + (hp - c0) * u) @ Matrix.Rotation(th * u, 4, "Z") @ Matrix.Translation(-(c0 + (hp - c0) * u))
        M = R @ T @ M0
        o.location = M.translation; o.rotation_quaternion = M.to_quaternion(); o.hide_render = False; o.hide_viewport = False
        return hp

    # ---------------------------------------------------------------- timeline helpers
    @staticmethod
    def assembly_clock(f):
        if f <= LAB1[1]: return clamp01((f - 4) / A_END) * A_END
        if f < LAB2[0] + 6: return A_END
        return max(0.0, A_END - (f - (LAB2[0] + 6)) * 2.2)

    def apply(self, f):
        a = self.assembly_clock(f)
        self.set_assembly(a)
        if f >= LAB2[0]: self.set_hero(f)


# ----------------------------------------------------------------------------------------------- environments / cameras
def env_for_frame(f):
    if f <= LAB1[1] or f >= LAB2[0]: return "lab"
    for name, s in SCENES:
        if s <= f < s + SCENE_LEN: return name
    return "lab"


def polar(loc):
    return math.atan2(loc[1], loc[0]), math.hypot(loc[0], loc[1]), loc[2]


def orbit(f, f0, f1, loc0, loc1, tgt0, tgt1, lens0, lens1, ease=0.55):
    """camera on an arc around the pergola: polar interpolation of (angle, radius, height), eased; target and lens interpolate too."""
    u = clamp01((f - f0) / max(1, (f1 - f0)))
    u = (1 - ease) * u + ease * e_io(u)
    a0, r0, h0 = polar(loc0); a1, r1, h1 = polar(loc1)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    a = a0 + da * u; r = r0 + (r1 - r0) * u; h = h0 + (h1 - h0) * u
    loc = (r * math.cos(a), r * math.sin(a), h)
    tgt = tuple(np.array(tgt0) * (1 - u) + np.array(tgt1) * u)
    return loc, tgt, lens0 + (lens1 - lens0) * u


# (loc0, loc1, tgt0, tgt1, lens0, lens1) per segment
CAM = {
    "lab1":       ((4.2, -6.8, 0.9), (-5.8, -5.4, 1.3), (0, 0, 1.5), (0, 0, 1.7), 22, 25),
    "carport":    ((6.8, -8.0, 0.9), (6.9, -4.6, 1.0), (-0.6, 0.4, 1.2), (-0.4, 0.2, 1.3), 24, 26),
    "barbecue":   ((-5.6, -7.2, 0.9), (-8.2, -2.4, 1.0), (0.5, 0.4, 1.2), (0.3, 0.5, 1.3), 24, 26),
    "kitchen":    ((-3.2, -7.2, 0.9), (2.2, -7.6, 1.0), (0.8, 1.0, 1.25), (0.2, 1.2, 1.3), 22, 24),
    "lounge":     ((5.4, -6.4, 0.85), (8.0, -2.6, 0.95), (-0.4, 0.9, 1.15), (-0.5, 0.9, 1.3), 22, 24),
    "commercial": ((-5.2, -5.2, 1.1), (-7.6, -6.8, 1.25), (0.4, 1.0, 1.3), (0.5, 1.0, 1.35), 21, 23),
    "lab2":       ((-5.8, -5.4, 1.3), (4.5, -6.8, 1.0), (0, 0, 1.6), (0, 0, 1.4), 25, 22),
}
HERO_CAM = ((0.8, -0.95, 1.45), (-0.75, -1.0, 1.2), (0.0, 0.0, 1.25), (0.0, 0.0, 1.25), 50, 55)


def camera_for_frame(f):
    if f <= LAB1[1]: return orbit(f, LAB1[0], LAB1[1], *CAM["lab1"])
    for name, s in SCENES:
        if s <= f < s + SCENE_LEN: return orbit(f, s, s + SCENE_LEN - 1, *CAM[name])
    if f < 758: return orbit(f, LAB2[0], 757, *CAM["lab2"])
    if f < 790:                                     # blend lab2 end-pose -> hero close-up
        a = orbit(757, LAB2[0], 757, *CAM["lab2"]); b = orbit(790, 790, 899, *HERO_CAM)
        u = e_io((f - 758) / 32.0)
        return tuple(np.array(a[0]) * (1 - u) + np.array(b[0]) * u), tuple(np.array(a[1]) * (1 - u) + np.array(b[1]) * u), a[2] * (1 - u) + b[2] * u
    return orbit(f, 790, 899, *HERO_CAM)
