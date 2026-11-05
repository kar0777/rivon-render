"""Frames -> MP4: grade + grain (overlay.py), whip-pan blur across every cut (like the reference), end card from END_SRC.
python3 assemble.py FRAMES_DIR OUT.mp4 [--audio wav]"""
import sys, os, subprocess, argparse
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import overlay as O

CUTS = []                      # clean cuts (no whip blur)
NF, END0, END_SRC = 1070, 950, 949


def whip(im, k):
    """directional motion blur, strength k 0..1"""
    if k <= 0:
        return im
    a = np.asarray(im).astype(np.float32); n = max(2, int(k * a.shape[1] * 0.06))
    acc = np.zeros_like(a)
    for i in range(n):
        acc += np.roll(a, i - n // 2, axis=1)
    return Image.fromarray((acc / n).astype(np.uint8))


def frame(src, f):
    p = os.path.join(src, f"f{min(f, END_SRC) if f >= END0 else f:04d}.png")
    im = Image.open(p).convert("RGB")
    if f >= END0:
        im = im.filter(ImageFilter.GaussianBlur(radius=im.width * 0.012 * min(1, (f - END0) / 10)))
    k = max([max(0.0, 1 - abs(f - c + 0.5) / 3.0) for c in CUTS] + [0.0])
    im = whip(im, k)
    return O.overlay(im, f)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--audio", default="")
    ap.add_argument("--nf", type=int, default=NF)
    a = ap.parse_args()
    tmp = a.out + "_frames"; os.makedirs(tmp, exist_ok=True)
    for f in range(a.nf):
        frame(a.src, f).save(os.path.join(tmp, f"{f:04d}.png"))
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(tmp, "%04d.png")]
    if a.audio:
        cmd += ["-i", a.audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "veryfast", "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print("wrote", a.out)
