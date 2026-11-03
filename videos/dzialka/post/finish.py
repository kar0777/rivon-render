"""RIVON post-production: cinematic grade + Polish captions + RIVON end card, then encode MP4 (H.264, 1080x1920, 30 fps).
usage:  python3 finish.py <frames_dir> <out.mp4> [--crf 16] [--audio sound.wav]      (frames named f0000.png ... f1679.png)
        python3 finish.py --test <seconds> <frame.png> <out.png>   (check a single frame)
needs:  pip3 install pillow numpy scipy   and   ffmpeg (brew install ffmpeg)"""
import sys, os, argparse, subprocess, glob, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
class F:
    FPS = 30; NFRAMES = 750
    RAIN = (-9.0, -8.0); SNOW = (-9.0, -8.0)
    TEXT_CUES = [{'kind': 'endcard', 't0': 21.0, 't1': 25.0, 'sub': 'Łączniki do konstrukcji drewnianych', 'tag': 'Altana w jeden dzień.', 'y': 0.36, 'cta': 'Zamów łączniki RIVON', 'cta2': 'Link w opisie profilu'}, {'kind': 'hook', 't0': 0.2, 't1': 2.9, 'lines': ['Altany nie postawisz', 'w jeden dzień.'], 't_b': 1.5, 'big': 'To mit.'}, {'kind': 'sub', 't0': 0.3, 't1': 2.9, 'text': 'Podobno się nie da. To mit.'}, {'kind': 'sub', 't0': 3.2, 't1': 5.9, 'text': 'Sobota, ósma rano. Stopy i słupy.'}, {'kind': 'sub', 't0': 6.1, 't1': 9.8, 'text': 'Belki wsuwają się w łączniki RIVON.'}, {'kind': 'sub', 't0': 10.1, 't1': 11.9, 'text': 'Wkręty – i rama trzyma.'}, {'kind': 'sub', 't0': 12.2, 't1': 15.8, 'text': 'Krokwie, potem dach – gotowe.'}, {'kind': 'sub', 't0': 16.3, 't1': 20.8, 'text': 'Niedziela rano – śniadanie w nowej altanie.'}, {'kind': 'sub', 't0': 22.2, 't1': 24.8, 'text': 'Zamów łączniki RIVON i postaw swoją.'}, {'kind': 'clock', 't0': 3.3, 't1': 15.5, 'hold': 0.9, 'h0': 8, 'h1': 17, 'title': 'Sobota · altana w jeden dzień'}, {'kind': 'badge', 't0': 16.3, 't1': 20.6, 'text': 'Zbudowana w jeden dzień'}]
ap = argparse.ArgumentParser(); ap.add_argument("frames", nargs="?"); ap.add_argument("out", nargs="?")
ap.add_argument("--crf", type=int, default=16); ap.add_argument("--test", nargs=3, default=None); ap.add_argument("--audio", default=None)
a = ap.parse_args()
FD = os.path.join(HERE, "fonts") + os.sep
def font(n, px, wt="Light"):
    f = ImageFont.truetype(FD + n, px)
    if n.startswith("Jost"): f.set_variation_by_name(wt)
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

def analog_clock(hr, h0, h1, u, al, title, D=240, PAD=45, SS=4):
    """round analog clock: dial with ticks + numerals, progress arc (08:00 -> 17:00), hour and minute hands; title under the dial"""
    CW, CH = 600, D + 2 * 8 + 70
    big = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    cx, cy, R = CW * SS / 2, (8 + D / 2) * SS, D / 2 * SS
    A = lambda v: int(v * al)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(8, 10, 12, A(190)))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(255, 255, 255, A(70)), width=2 * SS)
    # progress arc along the rim: from the start hour to the current hour (hour hand sweeps (h-12)*30 deg)
    a0 = (h0 % 12) * 30 - 90; a1 = (hr % 12 if hr % 12 != 0 else 12) * 30 - 90
    if a1 < a0: a1 += 360
    rr = R - 6 * SS
    d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a1, fill=(255, 255, 255, A(235)), width=4 * SS)
    for i in range(60):                                     # tick marks
        ang = np.deg2rad(i * 6); major = i % 5 == 0
        r0 = R - (24 if major else 17) * SS; r1 = R - 12 * SS
        d.line([(cx + r0 * np.sin(ang), cy - r0 * np.cos(ang)), (cx + r1 * np.sin(ang), cy - r1 * np.cos(ang))],
               fill=(255, 255, 255, A(255 if major else 110)), width=(3 if major else 1) * SS)
    fn_ = font("Jost.ttf", 25 * SS, "Medium")
    for n_ in (12, 3, 6, 9):
        ang = np.deg2rad(n_ * 30); rn = R - 46 * SS; tx = cx + rn * np.sin(ang); ty = cy - rn * np.cos(ang)
        w_ = d.textlength(str(n_), font=fn_); d.text((tx - w_ / 2, ty - 17 * SS), str(n_), font=fn_, fill=(255, 255, 255, A(235)))
    def hand(angle_deg, L, w, tail, col):
        ang = np.deg2rad(angle_deg); sx, sy = np.sin(ang), -np.cos(ang)
        p0 = (cx - sx * tail * SS, cy - sy * tail * SS); p1 = (cx + sx * L * SS, cy + sy * L * SS)
        d.line([p0, p1], fill=col, width=int(w * SS))
        for p in (p0, p1): d.ellipse([p[0] - w * SS / 2, p[1] - w * SS / 2, p[0] + w * SS / 2, p[1] + w * SS / 2], fill=col)
    hand((hr % 12) * 30, 0.50 * D / 2, 7, 10, (255, 255, 255, A(255)))             # hour hand: short, thick
    hand((hr - int(hr)) * 360, 0.80 * D / 2, 4, 14, (255, 255, 255, A(255)))       # minute hand: long, thin
    d.ellipse([cx - 7 * SS, cy - 7 * SS, cx + 7 * SS, cy + 7 * SS], fill=(255, 255, 255, A(255)))
    d.ellipse([cx - 3 * SS, cy - 3 * SS, cx + 3 * SS, cy + 3 * SS], fill=(8, 10, 12, A(255)))
    img = big.resize((CW, CH), Image.LANCZOS); d2 = ImageDraw.Draw(img)
    ft = font("Jost.ttf", 24, "Medium"); ttl = title.upper(); tw_ = spaced_len(d2, ttl, ft, 2.4)
    pw = int(tw_ + 44); y0 = 8 + D + 16
    d2.rounded_rectangle([(CW - pw) / 2, y0, (CW + pw) / 2, y0 + 42], radius=21, fill=(8, 10, 12, A(170)))
    spaced(d2, ((CW - tw_) / 2, y0 + 7), ttl, ft, (232, 236, 238, A(255)), 2.4)
    return img

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
        elif c["kind"] == "clock":
            al = min(ease(env(t, c["t0"], c["t1"] + c.get("hold", 0.0))), 1.0)
            if al <= 0: continue
            u = float(np.clip((t - c["t0"]) / (c["t1"] - c["t0"]), 0, 1)); u = float(u * u * (3 - 2 * u)) * 0.35 + u * 0.65
            hr = c["h0"] + (c["h1"] - c["h0"]) * u
            lay.alpha_composite(analog_clock(hr, c["h0"], c["h1"], u, al, c["title"]), ((W - 600) // 2, 170))
        elif c["kind"] == "hook":
            a1 = ease(env(t, c["t0"], c["t1"], 0.45, 0.4))
            if a1 <= 0: continue
            sc_ = d.rectangle  # dark scrim band behind the headline for legibility
            band = Image.new("RGBA", (W, 900), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
            for yy in range(900):
                u = 1 - abs(yy - 450) / 450.0; bd.line([(0, yy), (W, yy)], fill=(6, 8, 10, int(150 * a1 * (u ** 0.8))))
            lay.alpha_composite(band, (0, int(H * 0.36) - 450))
            f1 = font("Jost.ttf", 86, "SemiBold"); y = int(H * 0.36) - 170 + int(14 * (1 - a1))
            for ln in c["lines"]:
                tw_ = d.textlength(ln, font=f1)
                d.text(((W - tw_) / 2 + 3, y + 4), ln, font=f1, fill=(0, 0, 0, int(140 * a1)))
                d.text(((W - tw_) / 2, y), ln, font=f1, fill=(255, 255, 255, int(255 * a1))); y += 104
            a2 = ease(np.clip((t - c["t_b"]) / 0.35, 0, 1)) * min(a1 * 1.0, 1.0)
            if a2 > 0:
                f2 = font("Jost.ttf", 190, "Bold"); tb = c["big"]; tw2 = d.textlength(tb, font=f2); k = 0.94 + 0.06 * a2
                d.text(((W - tw2) / 2 + 4, y + 36 + 5), tb, font=f2, fill=(0, 0, 0, int(150 * a2)))
                d.text(((W - tw2) / 2, y + 36), tb, font=f2, fill=(255, 255, 255, int(255 * a2)))
                d.rectangle([W / 2 - 70, y + 36 + 262, W / 2 + 70, y + 36 + 268], fill=(255, 255, 255, int(235 * a2)))
        elif c["kind"] == "sub":
            al = ease(env(t, c["t0"], c["t1"], 0.18, 0.18))
            if al <= 0: continue
            fs_ = font("Jost.ttf", 46, "Medium"); words = c["text"].split(" "); lines = []; cur = ""
            for w_ in words:
                trial = (cur + " " + w_).strip()
                if d.textlength(trial, font=fs_) > W - 110 and cur: lines.append(cur); cur = w_
                else: cur = trial
            lines.append(cur)
            lh = 62; bh = lh * len(lines) + 30; bw = int(max(d.textlength(l, font=fs_) for l in lines)) + 64
            bx = (W - bw) // 2; by = int(H * 0.775) - bh // 2
            d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=22, fill=(6, 8, 10, int(150 * al)))
            for i_, l in enumerate(lines):
                tw_ = d.textlength(l, font=fs_)
                d.text(((W - tw_) / 2, by + 15 + i_ * lh), l, font=fs_, fill=(255, 255, 255, int(255 * al)))
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
            k = ease(np.clip((t - c["t0"]) / 1.0, 0, 1))
            if k <= 0: continue
            yL = int(H * c.get("y", 0.44))
            d.rectangle([0, 0, W, H], fill=(6, 7, 8, int(215 * k)))
            ka = ease(np.clip((t - c["t0"] - 0.5) / 0.8, 0, 1))
            lg = logo(int(W * 0.74), ka); lay.alpha_composite(lg, ((W - lg.width) // 2, yL - lg.height // 2))
            kb = ease(np.clip((t - c["t0"] - 1.0) / 0.8, 0, 1))
            fs = font("Jost.ttf", 27); sub = c["sub"].upper(); tw = spaced_len(d, sub, fs, 3.2)
            y_sub = yL + lg.height // 2 + 44
            spaced(d, ((W - tw) / 2, y_sub), sub, fs, (232, 236, 238, int(255 * kb)), 3.2)
            if c.get("tag"):
                kt = ease(np.clip((t - c["t0"] - 1.6) / 0.8, 0, 1)); ftg = font("Jost.ttf", 50); tg = c["tag"]; twg = d.textlength(tg, font=ftg)
                d.text(((W - twg) / 2, yL + lg.height // 2 + 150), tg, font=ftg, fill=(255, 255, 255, int(255 * kt)))
            if c.get("cta"):
                kc = ease(np.clip((t - c["t0"] - 2.2) / 0.5, 0, 1))
                if kc > 0:
                    fb = font("Jost.ttf", 46, "SemiBold"); txt = c["cta"].upper(); tbw = spaced_len(d, txt, fb, 3.0)
                    bw_ = int(tbw + 110); bh_ = 112; scl = 0.92 + 0.08 * kc; bw2, bh2 = int(bw_ * scl), int(bh_ * scl)
                    bx_ = (W - bw2) // 2; by_ = int(H * 0.60)
                    d.rounded_rectangle([bx_, by_, bx_ + bw2, by_ + bh2], radius=bh2 // 2, fill=(255, 255, 255, int(250 * kc)))
                    spaced(d, ((W - tbw) / 2, by_ + (bh2 - 46) / 2 - 8), txt, fb, (10, 12, 14, int(255 * kc)), 3.0)
                    if c.get("cta2"):
                        f3 = font("Jost.ttf", 34, "Regular"); t3 = c["cta2"]; w3 = d.textlength(t3, font=f3)
                        d.text(((W - w3) / 2, by_ + bh2 + 28), t3, font=f3, fill=(235, 238, 240, int(235 * kc)))
            d.rectangle([W / 2 - 30, yL + lg.height // 2 + 26, W / 2 + 30, yL + lg.height // 2 + 27], fill=(150, 156, 162, int(255 * kb)))
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
