"""RIVON film post: cinematic grade + white flash on the hard cuts + CTA end card, then H.264 MP4.
usage: python3 finish_film.py <frames_dir> <out.mp4> [--crf 16] [--audio film.wav] [--w 1080 --h 1920] [--fps 30]
       python3 finish_film.py --still <frame.png> <frame_index> <out.png>"""
import sys, os, argparse, subprocess, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "fonts") + os.sep
CUTS = (210, 306, 402, 498, 594, 690)
CTA_LINES = ("Jedno rozwiązanie.", "Wiele możliwości.")           # exact copy: "Jedno rozwiązanie. Wiele możliwości."
CTA_T0, LOGO_T0 = 836, 862
ap = argparse.ArgumentParser(); ap.add_argument("frames", nargs="?"); ap.add_argument("out", nargs="?"); ap.add_argument("--crf", type=int, default=16)
ap.add_argument("--audio", default=None); ap.add_argument("--still", nargs=3, default=None); ap.add_argument("--fps", type=int, default=30); ap.add_argument("--step", type=int, default=1)
a = ap.parse_args()

_m = Image.open(os.path.join(HERE, "rivon_logo.png")).convert("L"); _bb = _m.point(lambda v: 255 if v > 40 else 0).getbbox(); LOGO = _m.crop(_bb)
def logo(width):
    h = int(round(LOGO.height * width / LOGO.width)); m = LOGO.resize((width, h), Image.LANCZOS)
    im = Image.new("RGBA", (width, h), (255, 255, 255, 0)); im.putalpha(m); return im
def ease(x): x = float(np.clip(x, 0, 1)); return x * x * (3 - 2 * x)
def spaced(d, xy, text, fnt, fill, sp=0.0):
    x, y = xy
    for ch in text: d.text((x, y), ch, font=fnt, fill=fill); x += d.textlength(ch, font=fnt) + sp
def spaced_len(d, text, fnt, sp=0.0): return sum(d.textlength(ch, font=fnt) + sp for ch in text) - sp

_rng = np.random.default_rng(3); _VIG = {}
def grade(im):
    from scipy.ndimage import gaussian_filter
    a = np.asarray(im, np.float32) / 255.0; h, w = a.shape[:2]
    s = max(1, w / 1080.0)
    bl = np.stack([gaussian_filter(a[..., c], 9 * s) for c in range(3)], 2); bl2 = np.stack([gaussian_filter(a[..., c], 26 * s) for c in range(3)], 2)
    hl = np.clip(bl - 0.6, 0, 1) * 2.0; hl2 = np.clip(bl2 - 0.5, 0, 1) * 2.0
    a = 1 - (1 - a) * (1 - 0.10 * hl * np.array([1.0, 0.85, 0.7], np.float32)) * (1 - 0.06 * hl2)            # halation + bloom
    a = a + 0.10 * (a - 0.5) * (1 - np.abs(2 * a - 1)) * 2                                                     # gentle S-curve
    lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    a = a + (np.array([1.04, 1.0, 0.94], np.float32) - 1) * lum * 0.5 + (np.array([0.97, 1.0, 1.03], np.float32) - 1) * (1 - lum) * 0.25     # warm highlights / cool shadows
    a = lum + (a - lum) * 1.06
    if (h, w) not in _VIG:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); rx = (xx - w / 2) / (w / 2); ry = (yy - h / 2) / (h / 2)
        _VIG[(h, w)] = (1 - 0.12 * np.clip(rx ** 2 * 0.7 + ry ** 2 * 0.45, 0, 1.4) ** 1.2)[..., None]
    a = a * _VIG[(h, w)]
    a = a + _rng.normal(0, 0.0045, (h, w, 1)).astype(np.float32) * (1 - 0.5 * lum)
    return np.clip(a, 0, 1)

def flash(f):
    """white flash envelope around each hard cut (frame index f)"""
    k = 0.0
    for c in CUTS:
        d = f - c
        if d == -1: k = max(k, 0.30)
        elif d == 0: k = max(k, 0.85)
        elif d == 1: k = max(k, 0.50)
        elif d == 2: k = max(k, 0.18)
    return k

def endcard(img, f):
    W, H = img.size
    t1 = ease((f - CTA_T0) / 14.0)
    if t1 <= 0: return img
    base = np.asarray(img, np.float32) / 255.0
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    base = base * (1 - 0.42 * t1 * np.clip((yy - 0.32) / 0.5, 0, 1))                   # soft dark gradient under the text for legibility
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    fnt = ImageFont.truetype(FD + "Inter-Medium.otf", int(W * 0.056))
    y0 = int(H * 0.775)
    for i, line in enumerate(CTA_LINES):
        tl = ease((f - CTA_T0 - i * 6) / 14.0)
        if tl <= 0: continue
        wd = spaced_len(d, line, fnt, 1.5); x = (W - wd) / 2; y = y0 + i * int(W * 0.082) + (1 - tl) * 18
        spaced(d, (x, y), line, fnt, (255, 255, 255, int(255 * tl)), 1.5)
    tg = ease((f - LOGO_T0) / 16.0)
    if tg > 0:
        lg = logo(int(W * 0.36)); al = lg.split()[3].point(lambda v: int(v * tg)); lg.putalpha(al)
        lay.alpha_composite(lg, ((W - lg.width) // 2, int(H * 0.775 + 2 * W * 0.082 + W * 0.05 + (1 - tg) * 14)))
    return Image.alpha_composite(img, lay).convert("RGB")

def process(path, f):
    im = Image.open(path).convert("RGB")
    a = grade(im); k = flash(f)
    if k: a = a * (1 - k) + k
    out = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
    return endcard(out, f)

if a.still:
    p, f, o = a.still; process(p, int(f)).save(o); sys.exit(0)
fs = sorted(glob.glob(os.path.join(a.frames, "f*.png"))); assert fs, "no frames"
tmp = a.out + ".frames"; os.makedirs(tmp, exist_ok=True)
for i, p in enumerate(fs):
    f = int(os.path.basename(p)[1:5]); process(p, f).save(os.path.join(tmp, f"g{i:05d}.png"))
cmd = ["ffmpeg", "-y", "-framerate", str(a.fps), "-i", os.path.join(tmp, "g%05d.png")] + (["-i", a.audio] if a.audio else []) + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(a.crf), "-preset", "slow"] + (["-c:a", "aac", "-b:a", "192k", "-shortest"] if a.audio else []) + [a.out]
subprocess.run(cmd, check=True)
