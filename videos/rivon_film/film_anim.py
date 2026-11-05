"""Timeline of the RIVON film (30 s @ 30 fps = 900 frames, 9:16).

   0 -269  lab        VORTEX ASSEMBLY, one continuous camera take with three slow-motion close-ups
 270 -689  5 x 84     carport, barbecue, summer kitchen, lounge, cafe  (pergola fixed, orbiting camera, push-through cuts in post)
 690 -899  lab        the assembly runs backwards into the vortex, hero Trojak 3D floats to the centre, logo end card in post

Assembly realism (see plan_assembly.py, every straight move verified with mesh sweeps, 0 overlaps):
  feet -> posts slide down into the feet -> top frame is built in the air ABOVE the posts from rigid sub-assemblies
  (Trojaks slide onto the beam ends, end beams slide into the right unit, right unit slides into the left unit) -> the whole frame
  is lowered onto the posts -> Mocowanie belek 2 from above onto the inner beam faces -> rafters dropped into their channels ->
  screws driven along their own axes into the real holes.
Before a part seats it whirls in a vortex around the lab (rings by part size, so nothing overlaps), flies out on a smooth curve,
turns to its exact final orientation BEFORE the straight insertion move.  All transforms are rigid; nothing is scaled or edited."""
import math
import numpy as np
import bpy, mathutils
from mathutils import Matrix, Vector, Quaternion
from film_lib import load_json

FPS, NF = 30, 900
LAB1 = (0, 269); SCENE_LEN = 84
SCENES = [("carport", 270), ("barbecue", 354), ("kitchen", 438), ("lounge", 522), ("commercial", 606)]
LAB2 = (690, 899)
HERO_ID = "TROJAK_C2"
A_END = 250.0                    # assembly clock length
F_ASM_END = 262                  # film frame where the assembly clock reaches A_END (8 frames of hold before the cut)
LIFT = 1.6                       # the top frame is built this high above its final place
JOIN = 2.0                       # the right unit is built this far out in +x
SLOWMO = [(50.0, 70.0), (130.0, 152.0), (176.0, 194.0)]      # clock windows played at ~0.33x (close-ups)
SLOW_K = 0.33


def clamp01(x): return max(0.0, min(1.0, x))
def e_io(u): return u * u * (3 - 2 * u)
def e_io5(u): return u * u * u * (u * (6 * u - 15) + 10)
def e_out(u): return 1 - (1 - u) ** 3
def e_seat(u):                     # decelerate into the seat, no overshoot (no interpenetration)
    return 1 - (1 - u) ** 2.4


# ----------------------------------------------------------------------------------------------- time warp (slow motion)
def _speed(a):
    s = 1.0
    for a0, a1 in SLOWMO:
        w = 5.0
        k = clamp01((a - (a0 - w)) / w) * clamp01(((a1 + w) - a) / w)
        s = min(s, 1.0 - (1.0 - SLOW_K) * e_io(k))
    return s
_A = np.linspace(0, A_END, 5001); _dF = np.array([1.0 / _speed(x) for x in _A])
_F = np.concatenate([[0.0], np.cumsum((_dF[1:] + _dF[:-1]) / 2 * np.diff(_A))]); _F *= F_ASM_END / _F[-1]
def clock_of_frame(f):  return float(np.interp(f, _F, _A))
def frame_of_clock(a):  return float(np.interp(a, _A, _F))


# ----------------------------------------------------------------------------------------------- schedule (clock units)
def schedule():
    S = {}                                                   # id -> dict(leave, app, seat, dir, L, groups)
    def put(pid, leave, app, seat, d, L, groups=()):
        S[pid] = dict(leave=leave, app=app, seat=seat, dir=None if d is None else Vector(d), L=L, groups=tuple(groups))
    for k in range(4):
        put(f"STOPA_C{k+1}", 4 + 3 * k, 24 + 3 * k, 38 + 3 * k, (0, 0, -1), 0.8)
        put(f"POST_C{k+1}", 18 + 4 * k, 48 + 5 * k, 64 + 5 * k, (0, 0, -1), 1.0)
    F = ("lift",); R = ("lift", "join")
    put("BEAM_LONG_L", 48, 80, 80, None, 0.0, F); put("BEAM_LONG_R", 52, 84, 84, None, 0.0, R)
    put("TROJAK_C1", 54, 82, 92, (0, 1, 0), 0.6, F); put("TROJAK_C4", 56, 84, 94, (0, -1, 0), 0.6, F)
    put("TROJAK_C2", 58, 86, 96, (0, 1, 0), 0.6, R); put("TROJAK_C3", 60, 88, 98, (0, -1, 0), 0.6, R)
    put("BEAM_END_A", 64, 96, 108, (1, 0, 0), 0.9, R); put("BEAM_END_B", 66, 98, 110, (1, 0, 0), 0.9, R)
    for i in range(11):
        for j, s in enumerate(("L", "R")):
            put(f"MOCOW_{s}_{i}", 118 + 1.6 * i + 0.8 * j, 150 + 1.8 * i + 0.9 * j, 160 + 1.8 * i + 0.9 * j, (0, 0, -1), 0.5)
        put(f"RAFTER_{i}", 148 + 2.2 * i, 176 + 3.0 * i, 190 + 3.0 * i, (0, 0, -1), 0.9)
    return S
GROUP_T = {"join": (110.0, 124.0), "lift": (126.0, 152.0)}


def group_offset(groups, a):
    o = Vector((0, 0, 0))
    if "join" in groups:
        t0, t1 = GROUP_T["join"]; o += Vector((JOIN, 0, 0)) * (1 - e_io(clamp01((a - t0) / (t1 - t0))))
    if "lift" in groups:
        t0, t1 = GROUP_T["lift"]; o += Vector((0, 0, LIFT)) * (1 - e_io5(clamp01((a - t0) / (t1 - t0))))
    return o


# ----------------------------------------------------------------------------------------------- vortex
def _rng(seed): return np.random.default_rng(seed)
class Vortex:
    """The whole vortex turns as ONE rigid body (same angular speed for every slot), so waiting parts never move relative to
    each other.  Slots are packed collision-free (tumble spheres for compact parts, tangential capsules for timbers).
    Radius grows with the departure time: a part flying inward only crosses radii whose parts have already left.
    Each slot's phase is chosen so the part is near its target's bearing when it leaves."""
    OMEGA = 0.02                                       # rad per clock unit
    def __init__(self, parts):
        """parts: dict pid -> dict(leave, target(Vector), size(radius), length(0 for compact), zband(lo,hi))"""
        rng = _rng(7); self.slot = {}; placed = []                 # placed: (pts array, radius)
        for pid in sorted(parts, key=lambda q: (-parts[q]["length"], parts[q]["leave"])):
            P = parts[pid]; th_t = math.atan2(P["target"].y, P["target"].x)
            r = 4.05 + 0.0105 * P["leave"]
            for tries in range(6000):
                spread = 0.5 + tries / 1500.0
                ph = th_t - self.OMEGA * P["leave"] + rng.uniform(-0.75 * spread, 0.35 * spread)
                z = rng.uniform(*P["zband"]); rr = r + rng.uniform(-0.12, 0.12) * (1 + tries / 2000.0)
                pts = self._pts(rr, ph, z, P["length"])
                ok = all(np.min(np.linalg.norm(pts[:, None, :] - q[None, :, :], axis=2)) > P["size"] + rq + 0.06 for q, rq in placed)
                if ok: break
            placed.append((pts, P["size"])); self.slot[pid] = (ph, z, rr, rng.uniform(0, 1e3))
        self.parts = parts
    @staticmethod
    def _pts(r, ph, z, length):
        c = np.array([r * math.cos(ph), r * math.sin(ph), z])
        if length <= 0: return c[None, :]
        t = np.array([-math.sin(ph), math.cos(ph), 0.0]); n = max(2, int(length / 0.15) + 1)
        return c[None, :] + t[None, :] * np.linspace(-length / 2, length / 2, n)[:, None]
    spread = 1.0                                       # > 1 after the disassembly: the vortex opens up and leaves the frame
    def pos(self, pid, s):
        ph, z, r, sd = self.slot[pid]; ang = ph + self.OMEGA * s; spread = self.spread; r = r * spread
        return Vector((r * math.cos(ang), r * math.sin(ang), z + (spread - 1.0) * 1.2)), ang
    def vel(self, pid, s):
        p0, _ = self.pos(pid, s - 0.5); p1, _ = self.pos(pid, s + 0.5); return p1 - p0
    def rot(self, pid, s, q_final, long_axis_local):
        _, ang = self.pos(pid, s); ph, z, r, sd = self.slot[pid]
        if long_axis_local is not None:
            tang = Vector((-math.sin(ang), math.cos(ang), 0.0))
            ax_w = q_final @ long_axis_local
            q_align = ax_w.rotation_difference(tang)
            return Quaternion(tang, 0.025 * s + sd) @ q_align @ q_final
        rng = _rng(int(sd)); axis = Vector(rng.normal(size=3)).normalized(); rate = rng.uniform(0.03, 0.07)
        return Quaternion(axis, rate * s + sd) @ q_final


# ----------------------------------------------------------------------------------------------- animation
def _bezier(p0, p1, p2, p3, u):
    v = 1 - u; return p0 * v ** 3 + p1 * 3 * v * v * u + p2 * 3 * v * u * u + p3 * u ** 3


class Anim:
    def __init__(self):
        bpy.context.view_layer.update()
        L = load_json("layout.json"); coll = bpy.data.collections["PERGOLA"]
        self.objs = {}; self.center = {}; self.vloc = {}; self.long = {}
        for p in L["parts"]: self.objs[p["id"]] = bpy.data.objects[f"INST_{p['id']}"]
        for t in L["timber"]: self.objs[t["id"]] = bpy.data.objects[t["id"]]
        self.S = schedule()
        # screws: follow their part; seat after the part (and its timber) are in place
        self.screw_info = {}; self.screw_part = {}
        for i, fd in enumerate(L["fasteners"]):
            sid = f"SCREW_{i:03d}"; self.objs[sid] = bpy.data.objects[sid]
            part = fd["part"]; ax = Vector(fd["axis_to_timber"]).normalized(); self.screw_part[sid] = part
            if part.startswith("STOPA"):
                base = self.S[part]["seat"] + 3 if fd["kind"] == "anchor" else self.S["POST_C" + part[-1]]["seat"] + 3
            elif part.startswith("TROJAK"): base = GROUP_T["lift"][1] + 2
            elif abs(ax.z) < 0.5: base = self.S[part]["seat"] + 1                      # plate -> beam, before the rafter arrives
            else:
                ri = int(part.split("_")[-1]); base = self.S[f"RAFTER_{ri}"]["seat"] + 2   # from below into the rafter
            seat = base + 4 + (i % 9) * 0.9; app = seat - 7; leave = app - 24
            groups = ()
            self.S[sid] = dict(leave=leave, app=app, seat=seat, dir=ax, L=0.16, groups=groups, spin=6 * math.pi)
        for pid, o in self.objs.items():
            o.rotation_mode = "QUATERNION"
            self.S[pid]["loc0"] = o.matrix_world.translation.copy(); self.S[pid]["q0"] = o.matrix_world.to_quaternion()
            self.center[pid] = self._center(o)
            q0 = self.S[pid]["q0"]; self.vloc[pid] = q0.inverted() @ (self.center[pid] - self.S[pid]["loc0"])
            self.long[pid] = None
            if pid.startswith(("BEAM", "RAFTER", "POST")):
                tb = next(t for t in L["timber"] if t["id"] == pid); ax = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[tb["long_axis"]]
                self.long[pid] = q0.inverted() @ Vector(ax)
        vp = {}
        for pid in self.objs:
            S = self.S[pid]; lo, hi = self._bbox(self.objs[pid]); ext = np.array(hi) - np.array(lo)
            length = float(ext.max()) if self.long[pid] is not None else 0.0
            size = float(np.sort(ext)[1] / 2 * 1.45) if length else float(np.linalg.norm(ext) / 2)
            if pid.startswith("SCREW") and self.screw_part[pid].startswith("MOCOW"): zb = (0.5, 1.9)       # come in under the beams
            elif pid.startswith("BEAM"): zb = (3.3, 3.6)
            else: zb = (0.45, 3.3)
            vp[pid] = dict(leave=S["leave"], target=self.center[pid], size=size, length=length, zband=zb)
        self.V = Vortex(vp)
        self.hero = HERO_ID
        import json, os
        rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assembly_routes.json")
        self.route = {k: tuple(v) for k, v in json.load(open(rp)).items()} if os.path.exists(rp) else {}
        self.hero_center = self.center[HERO_ID]

    @staticmethod
    def _bbox(obj):
        pts = []; stack = [obj]
        while stack:
            o = stack.pop(); stack += list(o.children)
            if o.type == "MESH": pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        a = np.array([list(p) for p in pts]); return a.min(0).tolist(), a.max(0).tolist()

    @staticmethod
    def _center(obj):
        pts = []; stack = [obj]
        while stack:
            o = stack.pop(); stack += list(o.children)
            if o.type == "MESH": pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        a = np.array([list(p) for p in pts]); return Vector(((a.min(0) + a.max(0)) / 2).tolist())

    # ---------------------------------------------------------------- pose of one part (centre position P, rotation Q)
    def pose(self, pid, a, s):
        S = self.S[pid]; q0 = S["q0"]; c0 = self.center[pid]
        base = c0 + group_offset(S["groups"], a)
        d = S["dir"]; L = S["L"]
        if a >= S["seat"]: return base, q0, 0.0
        if d is not None and a >= S["app"]:
            u = (a - S["app"]) / max(1e-6, S["seat"] - S["app"]); k = 1 - e_seat(u)
            return base - d * L * k, q0, k
        A = (c0 + group_offset(S["groups"], S["app"])) - (d * L if d is not None else Vector((0, 0, 0)))
        if a < S["leave"]:
            P, _ = self.V.pos(pid, s); return P, self.V.rot(pid, s, q0, self.long[pid]), 1.0
        # flight: cubic Bezier from the vortex slot to the approach start, tangent-continuous at both ends
        u = (a - S["leave"]) / max(1e-6, S["app"] - S["leave"]); T = S["app"] - S["leave"]
        s_l = s - (a - S["leave"])                          # spin clock at the moment the part left its slot (continuous both ways)
        P0, _ = self.V.pos(pid, s_l); v0 = self.V.vel(pid, s_l)
        k_out, dz, s_end, lat = self.route.get(pid, (0.5, 0.0, 0.85, 0.0))
        side = Vector((-A.y, A.x, 0.0)).normalized() * lat if (A.x or A.y) else Vector((0, 0, 0))
        if pid.startswith("SCREW"):
            P1 = P0 + v0 * (T / 3.0) + Vector((0, 0, dz * 0.6)) + side * 0.6
            if self.screw_part[pid].startswith("MOCOW"): P1.z = min(P1.z, 2.0)
            P2 = A - d * k_out + Vector((0, 0, dz)) + side
        else:
            app_v = (d * L / max(1e-6, S["seat"] - S["app"]) * 2.4) if d is not None else Vector((0, 0, -0.02))
            up = Vector((0, 0, max(0.0, 3.4 - A.z) + 0.6)) if (abs(A.x) < 2.1 and abs(A.y) < 3.3) else Vector((0, 0, 0.3))
            up = up + Vector((0, 0, dz))
            P1 = P0 + v0 * (T / 3.0) + up * 0.6 + side * 0.6
            P2 = A - app_v * (T / 3.0) + up + side
        P = _bezier(P0, P1, P2, A, e_io(u) * 0.35 + u * 0.65)
        Qv = self.V.rot(pid, s_l, q0, self.long[pid])
        Q = Qv.slerp(q0, e_io(clamp01(u / s_end)))
        return P, Q, 1.0

    def place(self, pid, P, Q, spin_k=0.0):
        o = self.objs[pid]; S = self.S[pid]
        if S.get("spin") and spin_k > 0: Q = Q @ Quaternion((0, 0, 1), S["spin"] * spin_k)
        o.rotation_quaternion = Q; o.location = P - Q @ self.vloc[pid]
        o.hide_render = False; o.hide_viewport = False

    def set_clock(self, a, s):
        for pid in self.objs:
            P, Q, k = self.pose(pid, a, s); self.place(pid, P, Q, k if self.S[pid].get("spin") else 0.0)

    # ---------------------------------------------------------------- hero (end): from its vortex slot to the lab centre, slow turn
    def set_hero(self, f, a, s):
        P_v, Q_v, _ = self.pose(HERO_ID, a, s)
        hp = Vector((0.0, 0.0, 1.25)); th = math.radians(hero_theta(f))
        q0 = self.S[HERO_ID]["q0"]; Q_h = Quaternion((0, 0, 1), th) @ q0
        u = e_io(clamp01((f - 758) / 40.0))
        P = P_v.lerp(hp, u); Q = Q_v.slerp(Q_h, u) if u < 1 else Q_h
        self.place(HERO_ID, P, Q)

    def apply(self, f):
        self.V.spread = 1.0
        if f <= LAB1[1]:
            a = clock_of_frame(min(f, F_ASM_END)); self.set_clock(a, a)
        elif f < LAB2[0]:
            self.set_clock(A_END, A_END)
        else:
            # disassembly = the assembly played exactly backwards (so it is just as collision-free), then the vortex opens up
            a = disassembly_clock(f); f_end = LAB2[0] + 4 + 64
            s = a if f <= f_end else -(f - f_end) * 1.6
            if f > f_end: self.V.spread = 1.0 + 0.0009 * (f - f_end) ** 2
            self.set_clock(a, s)
            if f >= 758: self.set_hero(f, a, s)


def disassembly_clock(f):
    """690..757: the assembly plays backwards (about 3.8x) back into the vortex."""
    return max(0.0, A_END * (1 - e_io(clamp01((f - (LAB2[0] + 4)) / 64.0))))


HERO_T0, HERO_T1, HERO_TH0, HERO_TH_HOLD = 758, 826, 18.0, 149.2     # hero spin eases out so the engraved logo faces the camera and holds
def hero_theta(f):
    u = clamp01((f - HERO_T0) / (HERO_T1 - HERO_T0)); return HERO_TH0 + (HERO_TH_HOLD - HERO_TH0) * e_io(u)


# ----------------------------------------------------------------------------------------------- environments / cameras
def env_for_frame(f):
    if f <= LAB1[1] or f >= LAB2[0]: return "lab"
    for name, s in SCENES:
        if s <= f < s + SCENE_LEN: return name
    return "lab"


def polar(loc): return math.atan2(loc[1], loc[0]), math.hypot(loc[0], loc[1]), loc[2]


def orbit(f, f0, f1, loc0, loc1, tgt0, tgt1, lens0, lens1, ease=0.55):
    u = clamp01((f - f0) / max(1, (f1 - f0))); u = (1 - ease) * u + ease * e_io(u)
    a0, r0, h0 = polar(loc0); a1, r1, h1 = polar(loc1)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    a = a0 + da * u; r = r0 + (r1 - r0) * u; h = h0 + (h1 - h0) * u
    tgt = tuple(np.array(tgt0) * (1 - u) + np.array(tgt1) * u)
    return (r * math.cos(a), r * math.sin(a), h), tgt, lens0 + (lens1 - lens0) * u


CAM = {   # (loc0, loc1, tgt0, tgt1, lens0, lens1) per outdoor segment; each scene keeps its 96-frame move, the first 12 frames are trimmed
    "carport":    ((6.8, -8.0, 0.9), (6.9, -4.6, 1.0), (-0.6, 0.4, 1.2), (-0.4, 0.2, 1.3), 24, 26),
    "barbecue":   ((-5.6, -7.2, 0.9), (-8.2, -2.4, 1.0), (0.5, 0.4, 1.2), (0.3, 0.5, 1.3), 24, 26),
    "kitchen":    ((-3.2, -7.2, 0.9), (2.2, -7.6, 1.0), (0.8, 1.0, 1.25), (0.2, 1.2, 1.3), 22, 24),
    "lounge":     ((5.4, -6.4, 0.85), (8.0, -2.6, 0.95), (-0.4, 0.9, 1.15), (-0.5, 0.9, 1.3), 22, 24),
    "commercial": ((-5.2, -5.2, 1.1), (-7.6, -6.8, 1.25), (0.4, 1.0, 1.3), (0.5, 1.0, 1.35), 21, 23),
    "lab2":       ((-5.8, -5.4, 1.3), (4.5, -6.8, 1.0), (0, 0, 1.6), (0, 0, 1.4), 25, 22),
}
SCENE_TRIM = 12
HERO_FINAL = ((-0.2137, -0.5596, 1.2999), (0.114, -0.0098, 1.2999), 70.0)


# one-take lab camera: Catmull-Rom through key poses placed on the film frames of the actions (slow-mo close-ups)
def _lab1_keys():
    fa = frame_of_clock
    return [  # (film frame, loc, target, lens, f-stop)
        (0,              (8.4, -9.6, 3.6),   (0.0, 0.0, 2.2),     20, 5.6),
        (fa(30),         (5.2, -7.6, 1.6),   (-0.6, -1.4, 1.2),   24, 4.0),
        (fa(55),         (-2.55, -4.05, 0.45), (-1.70, -2.95, 0.32), 42, 2.8),   # close-up 1: post C1 slides into its Stopa
        (fa(66),         (-2.95, -3.70, 0.70), (-1.70, -2.95, 0.40), 40, 2.8),
        (fa(90),         (-6.2, -4.4, 2.6),  (-0.3, -0.6, 3.6),   22, 4.0),     # wide: the frame is built in the air
        (fa(118),        (-1.8, -7.6, 3.4),  (0.6, -1.8, 3.6),    24, 4.0),
        (fa(140),        (2.75, -3.95, 2.40), (1.70, -2.95, 2.70), 40, 2.8),     # close-up 2: frame lowered, Trojak C2 onto post C2
        (fa(151),        (2.85, -3.85, 2.25), (1.70, -2.95, 2.50), 42, 2.8),
        (fa(168),        (4.8, -3.6, 3.9),   (0.0, -1.0, 2.5),    24, 4.0),
        (fa(182),        (-0.95, -3.45, 2.95), (-1.62, -2.42, 2.62), 38, 2.8),   # close-up 3: first rafter drops into its Mocowanie belek 2
        (fa(192),        (-0.80, -3.30, 2.85), (-1.62, -2.42, 2.57), 40, 2.8),
        (fa(222),        (3.6, -6.4, 2.6),   (0.0, 0.0, 1.8),     22, 4.0),
        (269,            (5.0, -8.6, 0.9),   (0.0, 0.0, 1.9),     22, 4.0),
    ]
def _catmull(keys, f, idx):
    ts = [k[0] for k in keys]
    if f <= ts[0]: return np.array(keys[0][idx], float)
    if f >= ts[-1]: return np.array(keys[-1][idx], float)
    i = max(j for j in range(len(ts) - 1) if ts[j] <= f)
    p = [np.array(keys[max(0, min(len(keys) - 1, i + o))][idx], float) for o in (-1, 0, 1, 2)]
    t = [ts[max(0, min(len(ts) - 1, i + o))] for o in (-1, 0, 1, 2)]
    u = (f - t[1]) / max(1e-6, t[2] - t[1])
    m1 = (p[2] - p[0]) / max(1e-6, t[2] - t[0]) * (t[2] - t[1]); m2 = (p[3] - p[1]) / max(1e-6, t[3] - t[1]) * (t[2] - t[1])
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * p[1] + h10 * m1 + h01 * p[2] + h11 * m2


def camera_for_frame(f):
    """returns loc, target, lens, fstop"""
    if f <= LAB1[1]:
        K = _lab1_keys(); return tuple(_catmull(K, f, 1)), tuple(_catmull(K, f, 2)), float(_catmull(K, f, 3)), float(_catmull(K, f, 4))
    for name, s in SCENES:
        if s <= f < s + SCENE_LEN:
            l, t, ln = orbit(f + SCENE_TRIM, s, s + SCENE_LEN + SCENE_TRIM - 1, *CAM[name]); return l, t, ln, 4.0
    if f < HERO_T0:
        l, t, ln = orbit(f, LAB2[0], 757, *CAM["lab2"]); return l, t, ln, 4.0
    a0 = orbit(757, LAB2[0], 757, *CAM["lab2"]); b0 = HERO_FINAL
    u = e_io(clamp01((f - HERO_T0) / (HERO_T1 - HERO_T0)))
    loc = tuple(np.array(a0[0]) * (1 - u) + np.array(b0[0]) * u); tgt = tuple(np.array(a0[1]) * (1 - u) + np.array(b0[1]) * u)
    return loc, tgt, a0[2] * (1 - u) + b0[2] * u, 4.0 - 1.8 * u
