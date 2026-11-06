"""RIVON "Miniatura" sound (22 s): real recordings only for the beds, no music, no tonal sounds.
  workshop (0-8.5 s, 18.1-22 s): quiet room tone + wall clock ticking (Moodist "clock")
  hidden cuts: low air swell that rises into the logo push-in, a felt thump on the cut, the new place blooms in
  real plot (8.5-18.1 s): birds, wind in trees, distant road (Moodist, Pixabay Content License / CC0 recordings)
  end card: one dull steel latch tap under the logo
The recordings are not stored in this repo; pass the Moodist checkout: python3 sound_mini.py out.wav --sfx /home/claude/sfx"""
import os, sys, wave, subprocess, argparse
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import mini_anim as AN
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--sfx", required=True); A = ap.parse_args()
SR = 44100; DUR = AN.FRAMES / AN.FPS; N = int(SR * DUR); rng = np.random.default_rng(11)
MOO = os.path.join(A.sfx, "moodist", "public", "sounds")
MIX = np.zeros((N, 2))
C1, C2 = AN.CUT1 / AN.FPS, AN.CUT2 / AN.FPS


def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x, axis=0)
def rms(x): return float(np.sqrt((x ** 2).mean()) + 1e-12)
def db(v): return 10 ** (v / 20.0)


def load(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-f", "s16le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float64) / 32768.0
    if len(x) < int(dur * SR): x = np.tile(x, (int(dur * SR) // max(1, len(x)) + 1, 1))
    return x[: int(dur * SR)]


def env(n, fin, fout):
    t = np.arange(n) / SR; d = n / SR
    w = np.clip(t / max(fin, 1e-3), 0, 1) * np.clip((d - t) / max(fout, 1e-3), 0, 1); return (w * w * (3 - 2 * w))[:, None]


def bed(rel, a, b, level, start=5.0, fin=0.25, fout=0.25, lo=None, hi=None):
    x = load(os.path.join(MOO, rel), start, b - a)
    if lo: x = hp(x, lo)
    if hi: x = lp(x, hi)
    x = x / rms(x) * db(level) * env(len(x), fin, fout); i = int(a * SR); MIX[i:i + len(x)] += x[: N - i]


def room(a, b, level):
    n = int((b - a) * SR); y = np.cumsum(rng.normal(size=(n, 2)), 0); y = lp(hp(y, 30, 1), 160, 4)
    y = y / rms(y) * db(level) * env(n, 0.2, 0.2); MIX[int(a * SR):int(a * SR) + n] += y


def swell(t0, t1, level):
    """low air swell, low-pass rising 120 Hz -> 1.2 kHz, never hissy."""
    n = int((t1 - t0) * SR); x = np.cumsum(rng.normal(size=(n, 2)), 0); x = hp(x, 40, 1); out = np.zeros_like(x)
    k = 8; edges = np.linspace(0, n, k + 1).astype(int)
    for j in range(k):
        seg = lp(x, 120 * 10 ** (j / (k - 1)), 2)[edges[j]:edges[j + 1]]; out[edges[j]:edges[j + 1]] = seg
    out = out / rms(out) * db(level) * (np.linspace(0, 1, n) ** 2.2)[:, None]; MIX[int(t0 * SR):int(t0 * SR) + n] += out


def thump(t, level):
    n = int(0.45 * SR); tt = np.arange(n) / SR
    y = np.sin(2 * np.pi * (62 * tt - 20 * tt ** 2)) * np.exp(-tt / 0.09) + lp(rng.normal(size=n), 400) * np.exp(-tt / 0.03) * 0.6
    y = y / np.abs(y).max() * db(level); i = int(t * SR); MIX[i:i + n] += np.stack([y, y], 1)


def latch(t, level):
    """short, dead steel tap: band-limited noise burst with a very fast decay (no ringing pitch)."""
    n = int(0.12 * SR); tt = np.arange(n) / SR; y = rng.normal(size=n)
    y = hp(lp(y, 5200, 4), 900, 2) * (np.exp(-tt / 0.006) + 0.25 * np.exp(-(tt - 0.018).clip(0) / 0.01) * (tt > 0.018))
    y = y / np.abs(y).max() * db(level); i = int(t * SR); MIX[i:i + n] += np.stack([y * 0.95, y], 1)


# workshop
room(0.0, C1 + 0.05, -42); room(C2 - 0.05, DUR, -42)
bed("things/clock.mp3", 0.0, C1, -36, 3.0, 0.15, 0.08, lo=300)
bed("things/clock.mp3", C2, DUR, -37, 12.0, 0.08, 0.6, lo=300)
# push-ins and cuts
swell(C1 - 1.4, C1, -30); thump(C1, -20)
swell(C2 - 1.0, C2, -31); thump(C2, -22)
# real plot
bed("animals/birds.mp3", C1, C2, -31, 20.0, 0.5, 0.12, lo=700)
bed("nature/wind-in-trees.mp3", C1, C2, -37, 8.0, 0.6, 0.12, hi=3500)
bed("urban/road.mp3", C1, C2, -42, 30.0, 0.8, 0.12, hi=3500)
# end card
latch(AN.CTA[0] / AN.FPS + 0.05, -24)

# a touch of room on the workshop parts (short dark reverb), limiter, level
ir_n = int(0.35 * SR); ir = rng.normal(size=ir_n) * np.exp(-np.arange(ir_n) / (0.07 * SR)); ir = lp(ir, 2500); ir /= np.abs(ir).sum() / 8
wet = np.stack([fftconvolve(MIX[:, c], ir)[:N] for c in range(2)], 1) * 0.15
y = MIX + wet
y = y * db(4.0); y = np.tanh(y * 1.6) / 1.6                    # gentle soft limiter (mix already sits around -22 dB RMS)
y = y / np.abs(y).max() * db(-1.0)
with wave.open(A.out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype(np.int16).tobytes())
print("wrote", A.out, round(DUR, 2), "s")
