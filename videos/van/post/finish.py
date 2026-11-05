"""RIVON post-production: cinematic grade + Polish captions + RIVON end card, then encode MP4 (H.264, 1080x1920, 30 fps).
usage:  python3 finish.py <frames_dir> <out.mp4> [--crf 16] [--audio sound.wav]      (frames named f0000.png ... f0699.png, see remap.py)
        python3 finish.py --test <seconds> <frame.png> <out.png>   (check a single frame)
needs:  pip3 install pillow numpy scipy   and   ffmpeg (brew install ffmpeg)"""
import sys, os, argparse, subprocess, glob, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
class F:
    FPS = 30; NFRAMES = 700
    RAIN = (-9.0, -8.0); SNOW = (-9.0, -8.0)
    TEXT_CUES = [
        {'kind': 'endcard', 't0': 18.53, 't1': 23.34,
         'sub': 'Łączniki do konstrukcji drewnianych',
         'about': ['Stopy, trójaki i mocowania belek', 'do altan, wiat i tarasów'],
         'tag': 'Zbuduj swoją altanę.',
         'cta': 'Kup łączniki RIVON', 'url': ''}]
ap = argparse.ArgumentParser(); ap.add_argument("frames", nargs="?"); ap.add_argument("out", nargs="?")
ap.add_argument("--crf", type=int, default=16); ap.add_argument("--test", nargs=3, default=None); ap.add_argument("--audio", default=None)
a = ap.parse_args()
FD = os.path.join(HERE, "fonts") + os.sep
def font(n, px):
    f = ImageFont.truetype(FD + n, px)
    if n.startswith("Jost"): f.set_variation_by_name("Light")
    return f
def spaced(d, xy, text, fnt, fill, sp=1.5):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill); x += d.textlength(ch, font=fnt) + sp
def spaced_len(d, text, fnt, sp=1.5): return sum(d.textlength(ch, font=fnt) + sp for ch in text) - sp
LOGO_SRC = os.path.join(HERE, "rivon_logo.png")
_m = Image.open(LOGO_SRC).convert("L"); bb = _m.point(lambda v: 255 if v > 40 else 0).getbbox(); LOGO = _m.crop(bb)   # white = ink
def logo(width, alpha=1.0, color=(255, 255, 255)):
    h = int(round(LOGO.height * width / LOGO.width)); m = LOGO.resize((width, h), Image.LANCZOS)
    if alpha < 1: m = m.point(lambda v: int(v * alpha))
    im = Image.new("RGBA", (width, h), (*color, 0)); im.putalpha(m); return im

def env(t, t0, t1, fi=0.35, fo=0.35): return float(np.clip(min((t - t0) / fi, (t1 - t) / fo), 0, 1))
def ease(x): return x * x * (3 - 2 * x)

_rng = np.random.default_rng(3); _VIG = None
def grade(im, i):
    """cinematic grade: lens softness + chromatic aberration, halation/bloom, filmic S-curve, warm/teal split, vignette, luma+chroma grain"""
    global _VIG
    from PIL import ImageFilter
    from scipy.ndimage import map_coordinates
    im = im.filter(ImageFilter.GaussianBlur(0.35))
    a = np.asarray(im, np.float32) / 255.0; h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx = (xx - w / 2) / (w / 2); ry = (yy - h / 2) / (h / 2)
    for ch, k in ((0, 0.0), (2, 0.0)):                                   # lateral chromatic aberration (px at the corners)
        a[..., ch] = map_coordinates(a[..., ch], [yy - ry * k, xx - rx * k], order=1, mode='nearest')
    bl = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)), np.float32) / 255.0
    bl2 = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(26)), np.float32) / 255.0
    hl = np.clip(bl - 0.6, 0, 1) * 2.0; hl2 = np.clip(bl2 - 0.5, 0, 1) * 2.0
    a = 1 - (1 - a) * (1 - 0.10 * hl * np.array([1.0, 0.8, 0.6], np.float32)) * (1 - 0.06 * hl2)     # warm halation + bloom
    a = np.clip(a, 0, 1); a = a + 0.12 * (a - 0.5) * (1 - np.abs(2 * a - 1)) * 2
    lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    a = a + (np.array([1.05, 1.0, 0.92], np.float32) - 1) * lum * 0.6 + (np.array([0.97, 1.0, 1.03], np.float32) - 1) * (1 - lum) * 0.25
    a = lum + (a - lum) * 1.10
    if _VIG is None:
        d = rx ** 2 * 0.7 + ry ** 2 * 0.45
        _VIG = (1 - 0.10 * np.clip(d, 0, 1.4) ** 1.2)[..., None]
    a = a * _VIG
    g = _rng.normal(0, 1, (h, w, 1)).astype(np.float32)
    g = np.asarray(Image.fromarray(((g[..., 0] * 40 + 128).clip(0, 255)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None]; g = (g - 128) / 40.0
    a = a + g * 0.006 * (1 - 0.5 * lum) + _rng.normal(0, 0.004, (h, w, 3)).astype(np.float32)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))

# ------------------------------------------------------------------ weather overlays (rain streaks / snow flakes, parallax layers)
_wr = np.random.default_rng(11)
RAIN_L = [dict(n=520, ln=64, w=1, al=62, sp=1500.0, sl=0.10), dict(n=240, ln=120, w=1, al=88, sp=2200.0, sl=0.12), dict(n=70, ln=260, w=3, al=48, sp=3100.0, sl=0.14)]
for L in RAIN_L: L["x"] = _wr.uniform(-300, 1400, L["n"]); L["y"] = _wr.uniform(0, 2300, L["n"])
SNOW_L = [dict(n=420, r=1.6, al=150, sp=95.0, sw=14.0, bl=0.0), dict(n=170, r=3.0, al=190, sp=140.0, sw=26.0, bl=0.7), dict(n=34, r=9.0, al=150, sp=230.0, sw=48.0, bl=3.2)]
for L in SNOW_L: L["x"] = _wr.uniform(-40, 1120, L["n"]); L["y"] = _wr.uniform(0, 2000, L["n"]); L["ph"] = _wr.uniform(0, 6.28, L["n"]); L["fr"] = _wr.uniform(0.25, 0.6, L["n"])
def weather(im, t):
    W, H = im.size
    if F.RAIN[0] <= t < F.RAIN[1]:
        lay = Image.new("RGBA", im.size, (214, 224, 236, 0)); d = ImageDraw.Draw(lay); tt = t - F.RAIN[0]
        for L in RAIN_L:
            span = H + L["ln"] + 60
            ys = (L["y"] + L["sp"] * tt) % span - L["ln"]
            for x, y in zip(L["x"], ys):
                xx = x - L["sl"] * y; d.line([(xx, y), (xx + L["sl"] * L["ln"], y + L["ln"])], fill=(214, 224, 236, L["al"]), width=L["w"])
        lay = lay.filter(ImageFilter.GaussianBlur(0.55)); return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")
    if F.SNOW[0] <= t < F.SNOW[1]:
        base = im.convert("RGBA"); tt = t - F.SNOW[0]
        for L in SNOW_L:
            lay = Image.new("RGBA", im.size, (246, 249, 255, 0)); d = ImageDraw.Draw(lay)
            ys = (L["y"] + L["sp"] * tt) % (H + 40) - 20; xs = L["x"] + L["sw"] * np.sin(6.283 * L["fr"] * tt + L["ph"])
            r = L["r"]
            for x, y in zip(xs, ys): d.ellipse([x - r, y - r, x + r, y + r], fill=(246, 249, 255, L["al"]))
            if L["bl"] > 0: lay = lay.filter(ImageFilter.GaussianBlur(L["bl"]))
            base = Image.alpha_composite(base, lay)
        return base.convert("RGB")
    return im

def overlay(im, t):
    W, H = im.size
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for c in F.TEXT_CUES:
        if c["kind"] == "caption":
            al = ease(env(t, c["t0"], c["t1"]))
            if al <= 0: continue
            f1 = font("Jost.ttf", 33); tw = spaced_len(d, c["line1"], f1, 1.2)
            lw = 84; pw = int(max(tw, lw)) + 52; ph = 108; x0 = 28; y0 = H - 170 + int(8 * (1 - al))
            pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=16, fill=(8, 10, 12, int(150 * al)))
            spaced(pd, (26, 14), c["line1"], f1, (255, 255, 255, int(255 * al)), 1.2)
            lg = logo(lw, 0.85 * al); pill.alpha_composite(lg, (26, 14 + 33 + 20))
            lay.alpha_composite(pill, (x0, y0))
        elif c["kind"] == "hook":
            al = ease(env(t, c["t0"], c["t1"], 0.4, 0.4))
            if al <= 0: continue
            f1 = font("Jost.ttf", 74); f2 = font("Jost.ttf", 74)
            w1 = spaced_len(d, c["l1"], f1, 1.5); w2 = spaced_len(d, c["l2"], f2, 1.5)
            pw = int(max(w1, w2)) + 80; ph = 230; px0 = (W - pw) // 2; py0 = 190 + int(14 * (1 - al))
            pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=26, fill=(8, 10, 12, int(165 * al)))
            spaced(pd, ((pw - w1) / 2, 28), c["l1"], f1, (255, 255, 255, int(255 * al)), 1.5)
            spaced(pd, ((pw - w2) / 2, 120), c["l2"], f2, (255, 255, 255, int(255 * al)), 1.5)
            lay.alpha_composite(pill, (px0, py0))
        elif c["kind"] == "clock":
            al = min(ease(env(t, c["t0"], c["t1"] + c.get("hold", 0.0))), 1.0)
            if al <= 0: continue
            u = float(np.clip((t - c["t0"]) / (c["t1"] - c["t0"]), 0, 1)); u = float(u * u * (3 - 2 * u)) * 0.35 + u * 0.65
            hr = c["h0"] + (c["h1"] - c["h0"]) * u; hh, mm = int(hr), int((hr - int(hr)) * 60)
            ft = font("Jost.ttf", 25); fc = font("Jost.ttf", 64); fl = font("Jost.ttf", 22)
            ttl = c["title"].upper(); tw_ = spaced_len(d, ttl, ft, 2.6)
            pw = int(max(tw_ + 70, 560)); ph = 190; px0 = (W - pw) // 2; py0 = 215
            pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=22, fill=(8, 10, 12, int(165 * al)))
            spaced(pd, ((pw - tw_) / 2, 20), ttl, ft, (232, 236, 238, int(255 * al)), 2.6)
            ct = "%02d:%02d" % (hh, mm); cw = pd.textlength(ct, font=fc)
            pd.text(((pw - cw) / 2, 52), ct, font=fc, fill=(255, 255, 255, int(255 * al)))
            bx0, bx1, by = 38, pw - 38, 148
            pd.rounded_rectangle([bx0, by, bx1, by + 6], radius=3, fill=(255, 255, 255, int(70 * al)))
            pd.rounded_rectangle([bx0, by, bx0 + max(6, int((bx1 - bx0) * u)), by + 6], radius=3, fill=(255, 255, 255, int(240 * al)))
            pd.text((bx0, by + 14), "%02d:00" % c["h0"], font=fl, fill=(200, 205, 210, int(230 * al)))
            e_ = "%02d:00" % c["h1"]; pd.text((bx1 - pd.textlength(e_, font=fl), by + 14), e_, font=fl, fill=(200, 205, 210, int(230 * al)))
            lay.alpha_composite(pill, (px0, py0))
        elif c["kind"] == "badge":
            al = ease(env(t, c["t0"], c["t1"]))
            if al <= 0: continue
            ft = font("Jost.ttf", 28); tx = c["text"].upper(); tw_ = spaced_len(d, tx, ft, 3.0)
            pw = int(tw_ + 72); ph = 78; px0 = (W - pw) // 2; py0 = 215
            pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=20, fill=(8, 10, 12, int(165 * al)))
            spaced(pd, (36, 20), tx, ft, (255, 255, 255, int(255 * al)), 3.0)
            lay.alpha_composite(pill, (px0, py0))
        else:
            k = ease(np.clip((t - c["t0"]) / 0.7, 0, 1))
            if k <= 0: continue
            d.rectangle([0, 0, W, H], fill=(6, 7, 8, int(222 * k)))
            y_logo = int(H * 0.33)
            ka = ease(np.clip((t - c["t0"] - 0.3) / 0.6, 0, 1))
            lg = logo(int(W * 0.74), ka); lay.alpha_composite(lg, ((W - lg.width) // 2, y_logo - lg.height // 2))
            kb = ease(np.clip((t - c["t0"] - 0.6) / 0.6, 0, 1))
            y0 = y_logo + lg.height // 2
            fs = font("Jost.ttf", 27); sub = c["sub"].upper(); tw = spaced_len(d, sub, fs, 3.2)
            spaced(d, ((W - tw) / 2, y0 + 44), sub, fs, (232, 236, 238, int(255 * kb)), 3.2)
            d.rectangle([W / 2 - 30, y0 + 26, W / 2 + 30, y0 + 27], fill=(150, 156, 162, int(255 * kb)))
            kc = ease(np.clip((t - c["t0"] - 0.9) / 0.6, 0, 1)); fa = font("Jost.ttf", 40)
            for i_, ln in enumerate(c.get("about", [])):
                twa = d.textlength(ln, font=fa); d.text(((W - twa) / 2, y0 + 140 + i_ * 62), ln, font=fa, fill=(214, 219, 223, int(255 * kc)))
            if c.get("tag"):
                kt = ease(np.clip((t - c["t0"] - 1.2) / 0.6, 0, 1)); ftg = font("Jost.ttf", 58); tg = c["tag"]; twg = d.textlength(tg, font=ftg)
                d.text(((W - twg) / 2, y0 + 300), tg, font=ftg, fill=(255, 255, 255, int(255 * kt)))
            if c.get("cta"):
                kx = ease(np.clip((t - c["t0"] - 1.5) / 0.6, 0, 1)); fb = font("Jost.ttf", 44); bt = c["cta"].upper(); bw = spaced_len(d, bt, fb, 3.0)
                pw = int(bw + 120); ph = 116; px0 = (W - pw) // 2; py0 = y0 + 450 + int(10 * (1 - kx))
                d.rounded_rectangle([px0, py0, px0 + pw, py0 + ph], radius=58, fill=(255, 255, 255, int(255 * kx)))
                spaced(d, (px0 + (pw - bw) / 2, py0 + 29), bt, fb, (12, 14, 16, int(255 * kx)), 3.0)
                if c.get("url"):
                    fu = font("Jost.ttf", 38); twu = d.textlength(c["url"], font=fu)
                    d.text(((W - twu) / 2, py0 + ph + 34), c["url"], font=fu, fill=(214, 219, 223, int(255 * kx)))
    return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")

def load(path):
    im = Image.open(path).convert("RGB")
    return im if im.size == (1080, 1920) else im.resize((1080, 1920), Image.LANCZOS)   # frames rendered at 900x1600 are scaled up here

if a.test:
    t = float(a.test[0]); overlay(weather(grade(load(a.test[1]), 0), t), t).save(a.test[2]); sys.exit(0)
files = sorted(glob.glob(os.path.join(a.frames, "f*.png"))); assert len(files) == F.NFRAMES, (len(files), F.NFRAMES)
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(F.FPS), "-c:v", "png", "-i", "-"] + (["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"] if a.audio else []) + [
       "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart", a.out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i, f in enumerate(files):
    im = overlay(weather(grade(load(f), i), i / F.FPS), i / F.FPS); b = io.BytesIO(); im.save(b, "PNG", compress_level=1); pr.stdin.write(b.getvalue())
pr.stdin.close(); pr.wait(); print("done", a.out)
