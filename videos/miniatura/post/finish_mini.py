"""RIVON "Miniatura" post: grade, soft push-through over the two hidden cuts, Polish subtitles, CTA end card, H.264 MP4.
usage: python3 finish_mini.py <frames_dir> <out.mp4> [--crf 16] [--audio mini.wav]
       python3 finish_mini.py --still <frame.png> <frame_index> <out.png>"""
import sys, os, argparse, subprocess, glob
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
FILMPOST = os.path.join(HERE, "..", "..", "rivon_film", "post")
sys.path.insert(0, os.path.join(HERE, ".."))
import mini_anim as AN
FD = os.path.join(FILMPOST, "fonts") + os.sep
TN = 4                                                  # frames on each side of a hidden cut that get the push-through
CTA_TEXT = "Zamów łączniki RIVON"
SUB_Y = 0.78                                            # subtitle baseline (fraction of height), inside the 9:16 safe area

_m = Image.open(os.path.join(FILMPOST, "rivon_logo.png")).convert("L"); WORD = _m.crop(_m.point(lambda v: 255 if v > 40 else 0).getbbox())


def ease(x): x = float(np.clip(x, 0, 1)); return x * x * (3 - 2 * x)


_rng = np.random.default_rng(3); _VIG = {}
def grade(a):
    from scipy.ndimage import gaussian_filter
    h, w = a.shape[:2]; s = max(1, w / 1080.0)
    bl = np.stack([gaussian_filter(a[..., c], 9 * s) for c in range(3)], 2)
    hl = np.clip(bl - 0.6, 0, 1) * 2.0
    a = 1 - (1 - a) * (1 - 0.08 * hl * np.array([1.0, 0.86, 0.72], np.float32))
    a = a + 0.08 * (a - 0.5) * (1 - np.abs(2 * a - 1)) * 2
    lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    a = lum + (a - lum) * 1.04
    if (h, w) not in _VIG:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); rx = (xx - w / 2) / (w / 2); ry = (yy - h / 2) / (h / 2)
        _VIG[(h, w)] = (1 - 0.10 * np.clip(rx ** 2 * 0.7 + ry ** 2 * 0.45, 0, 1.4) ** 1.2)[..., None]
    a = a * _VIG[(h, w)]
    a = a + _rng.normal(0, 0.004, (h, w, 1)).astype(np.float32) * (1 - 0.5 * lum)
    return np.clip(a, 0, 1)


def trans_u(f):
    u = 0.0
    for c in (AN.CUT1, AN.CUT2):
        if c - TN <= f < c: u = max(u, (TN - (c - f) + 1) / TN)
        elif c <= f < c + TN: u = max(u, (TN - (f - c + 1) + 1) / TN)
    return u


def push_through(a, u, n=20):
    h, w = a.shape[:2]; cx, cy = w * 0.5, h * 0.5
    sc = 1.0 + 0.25 * u ** 2; bw = 0.02 + 0.12 * u ** 1.6; acc = np.zeros_like(a)
    for j in range(n):
        s = sc * (1 + bw * (j / (n - 1) - 0.5))
        M = cv2.getRotationMatrix2D((cx, cy), 0.0, s); acc += cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return np.clip(acc / n, 0, 1)


def _font(w, k): return ImageFont.truetype(FD + "Inter-Medium.otf", int(w * k))


def text_layer(size, f):
    w, h = size; lay = Image.new("RGBA", size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for (f0, f1, txt) in AN.SUBS:
        if not (f0 <= f <= f1): continue
        al = min(ease((f - f0) / 8.0), ease((f1 - f) / 8.0))
        fnt = _font(w, 0.054); lines, cur = [], ""
        for part in txt.split("|"):                                    # "|" = forced line break, then wrap to 86 % of the width
            for word in part.split():
                t = (cur + " " + word).strip()
                if d.textlength(t, font=fnt) > w * 0.86 and cur: lines.append(cur); cur = word
                else: cur = t
            lines.append(cur); cur = ""; lh = int(w * 0.078)
        sh = Image.new("RGBA", size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        for i, ln in enumerate(lines):
            x, y = (w - d.textlength(ln, font=fnt)) / 2, h * SUB_Y + i * lh
            ds.text((x, y + w * 0.004), ln, font=fnt, fill=(0, 0, 0, int(160 * al)))
        lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(w * 0.006)))
        for i, ln in enumerate(lines):
            x, y = (w - d.textlength(ln, font=fnt)) / 2, h * SUB_Y + i * lh
            d.text((x, y), ln, font=fnt, fill=(255, 255, 255, int(255 * al)))
    c0, c1 = AN.CTA
    if f >= c0:
        tw_ = ease((f - c0) / 14.0); tc = ease((f - c0 - 8) / 14.0)
        ww = int(w * 0.46); wh = int(round(WORD.height * ww / WORD.width)); wm = WORD.resize((ww, wh), Image.LANCZOS)
        g = Image.new("RGBA", (ww, wh), (255, 255, 255, 0)); g.putalpha(wm.point(lambda v: int(v * tw_)))
        lay.alpha_composite(g, ((w - ww) // 2, int(h * 0.20 + (1 - tw_) * 12)))
        fnt = _font(w, 0.058); tl = d.textlength(CTA_TEXT, font=fnt)
        d.text(((w - tl) / 2, h * 0.20 + wh + h * 0.035 + (1 - tc) * 12), CTA_TEXT, font=fnt, fill=(255, 255, 255, int(255 * tc)))
    return lay


def process(path, f):
    a = grade(np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0)
    u = trans_u(f)
    if u > 0: a = push_through(a, u)
    c0 = AN.CTA[0]
    if f >= c0 - 6: a = a * (1 - 0.62 * ease((f - c0 + 6) / 18.0))          # the workshop dims under the end card
    img = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).convert("RGBA")
    return Image.alpha_composite(img, text_layer(img.size, f)).convert("RGB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("frames", nargs="?"); ap.add_argument("out", nargs="?"); ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--audio", default=None); ap.add_argument("--still", nargs=3, default=None)
    a = ap.parse_args()
    if a.still:
        p, f, o = a.still; process(p, int(f)).save(o); sys.exit(0)
    fs = sorted(glob.glob(os.path.join(a.frames, "f*.png"))); assert fs, "no frames"
    tmp = a.out + ".frames"; os.makedirs(tmp, exist_ok=True)
    for i, p in enumerate(fs): process(p, int(os.path.basename(p)[1:5])).save(os.path.join(tmp, f"g{i:05d}.png"))
    cmd = ["ffmpeg", "-y", "-framerate", str(AN.FPS), "-i", os.path.join(tmp, "g%05d.png")] + (["-i", a.audio] if a.audio else []) + \
          ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(a.crf), "-preset", "slow"] + (["-c:a", "aac", "-b:a", "192k", "-shortest"] if a.audio else []) + [a.out]
    subprocess.run(cmd, check=True)
