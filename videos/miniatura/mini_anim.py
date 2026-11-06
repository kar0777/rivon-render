"""Timeline of the "Miniatura" video: 22 s x 30 fps = 660 frames (0..659).
Every camera key is in PLOT coordinates (pergola at the origin, metres). Keys marked desk=True were authored in the
workshop (world) and converted through the inverse model transform, so one smooth spline runs through both places.
on_desk(f) decides where the frame is rendered: the model on the work table, or the real plot at full size.
"""
import math
import numpy as np

FPS = 30
FRAMES = 660
CUT1 = 255          # model -> real   (frame filled by the logo face of Trojak C2)
CUT2 = 543          # real -> model   (frame filled by Trojak C1)

SUBS = [              # Polish subtitles, burnt in by post/finish_mini.py: (first, last, text)
    (8, 66, "To tylko makieta…?"),
    (262, 336, "…nie. To RIVON."),
    (388, 470, "Solidna konstrukcja.|Złożysz sam."),
]
CTA = (600, 659)      # logo + "Zamów łączniki RIVON"


def on_desk(f):
    return f < CUT1 or f >= CUT2


def _keys(B):
    """(frame, loc, tgt, lens, fstop). fstop is physical for the place the frame is rendered in."""
    import mathutils
    X, z = B.SHOP_X, B.BENCH_TOP
    Mi = B.model_matrix().inverted()
    d = lambda p: tuple(Mi @ mathutils.Vector(p))
    s = B.MINI_S
    return [
        # --- desk: hook, slow push over the table (tilt-shift look)
        (0,   d((X - 0.07, 0.00, z + 0.22)), d((X + 0.08, 0.86, z + 0.03)), 32, 2.8),
        (66,  d((X - 0.04, 0.16, z + 0.16)), d((X + 0.07, 0.90, z + 0.04)), 32, 2.8),
        # --- desk: dive down to the model, glide along the drive
        (150, (3.4, -9.5, 1.9),  (1.2, -2.6, 2.0), 32, 4.0),
        (215, (2.55, -4.9, 2.25), (1.68, -2.98, 2.48), 40, 5.6),
        # --- desk: push into the logo face of Trojak C2 (hidden cut at CUT1)
        (CUT1 - 1, (1.81, -3.16, 2.49), (1.67, -2.98, 2.50), 50, 8.0),
        # --- real (same pose, equivalent aperture), pull back, the aperture closes -> everything sharp and big
        (CUT1,     (1.81, -3.16, 2.49), (1.67, -2.98, 2.50), 50, 8.0 * s),
        (290, (2.75, -4.45, 2.15), (1.55, -2.85, 2.35), 40, 2.0),
        (330, (3.6, -6.3, 1.25), (0.9, -1.6, 1.95), 26, 8.0),
        # --- real: low hero orbit around the carport (car under the roof, the frame reads heavy and big)
        (400, (3.2, -7.4, 0.55), (-0.1, 0.1, 1.75), 18, 8.0),
        (470, (-1.6, -7.9, 0.70), (0.2, 0.3, 1.65), 18, 8.0),
        # --- real: rise to Trojak C1, push in (hidden cut at CUT2)
        (515, (-2.7, -4.6, 2.05), (-1.74, -2.92, 2.48), 35, 8.0),
        (CUT2 - 1, (-1.84, -3.05, 2.49), (-1.74, -2.92, 2.49), 50, 8.0 * s),
        # --- desk again: pull up and back off the model, the workshop and the coffee mug return
        (CUT2,     (-1.84, -3.05, 2.49), (-1.74, -2.92, 2.49), 50, 8.0),
        (575, (-6.0, -10.5, 4.5), (-0.6, -1.0, 1.7), 40, 5.6),
        (605, d((X - 0.30, 0.10, z + 0.36)), d((X + 0.04, 0.95, z + 0.02)), 32, 2.8),
        (FRAMES - 1, d((X - 0.33, 0.04, z + 0.40)), d((X + 0.04, 0.95, z + 0.02)), 32, 2.8),
    ]


def _ease(t):
    return t * t * (3 - 2 * t)


def _hermite(p0, p1, m0, m1, t):
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1


class Path:
    """Catmull-Rom (non-uniform) through the keys; the two cuts split the spline so each side keeps its own tangents."""
    def __init__(self, B):
        self.K = _keys(B)

    def _segment_keys(self, f):
        K = self.K
        if f < CUT1: return [k for k in K if k[0] < CUT1]
        if f < CUT2: return [k for k in K if CUT1 <= k[0] < CUT2]
        return [k for k in K if k[0] >= CUT2]

    def sample(self, f):
        K = self._segment_keys(f)
        fr = np.array([k[0] for k in K], float)
        if f <= fr[0]: i = 0; t = 0.0
        elif f >= fr[-1]: i = len(K) - 2; t = 1.0
        else:
            i = int(np.searchsorted(fr, f, side="right") - 1); t = (f - fr[i]) / (fr[i + 1] - fr[i])
        def val(j, idx):
            v = K[j][idx]; return np.array(v, float) if not np.isscalar(v) else np.array([math.log(v)] if idx == 4 else [v], float)
        def tang(j, idx):
            if j == 0 or j == len(K) - 1: return np.zeros_like(val(j, idx))
            return (val(j + 1, idx) - val(j - 1, idx)) / (fr[j + 1] - fr[j - 1]) * (fr[i + 1] - fr[i])
        out = []
        for idx in (1, 2, 3, 4):
            p = _hermite(val(i, idx), val(i + 1, idx), tang(i, idx), tang(i + 1, idx), t)
            out.append(p)
        loc, tgt, lens, lf = out
        return tuple(loc), tuple(tgt), float(lens[0]), float(math.exp(lf[0]))
