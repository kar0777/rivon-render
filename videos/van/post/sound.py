"""Synthesised material sounds (no melody) timed from events.json produced by build_scene.py.
usage: python3 sound.py events.json out.wav [seconds=26]"""
import sys, json, numpy as np
from scipy.signal import butter, sosfilt
SR = 44100; FPS = 30
ev = json.load(open(sys.argv[1])); out = sys.argv[2]; DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 26.0
N = int(SR * DUR); rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def noise(n): return rng.normal(0, 1, n)
def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    n = min(len(sig), N - i); g = gain
    L[i:i + n] += sig[:n] * g * (1 - 0.5 * max(pan, 0)); R[i:i + n] += sig[:n] * g * (1 + 0.5 * min(pan, 0) if pan < 0 else 1 - 0.5 * max(-pan, 0))
def tt(d): return np.arange(int(d * SR)) / SR
def tone(freq, d, dec, harm=(1.0,)):
    t = tt(d); y = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harm)); return y * np.exp(-t / dec)
def thud(f=70, d=0.35, dec=0.08, nz=0.6, nf=500):
    t = tt(d); y = np.sin(2 * np.pi * (f + 40 * np.exp(-t / 0.03)) * t) * np.exp(-t / dec) + nz * lp(noise(len(t)), nf) * np.exp(-t / (dec * 0.7)); return y
def wood_tok(f=380, d=0.28, dec=0.05):
    t = tt(d); y = tone(f, d, dec, (1.0, 0.5, 0.25)) + 0.7 * bp(noise(len(t)), 800, 3500) * np.exp(-t / 0.018) + 0.5 * thud(90, d, 0.06, 0.2, 300)[:len(t)]; return y
def steel(fs_, d=0.5, dec=0.11):
    t = tt(d); y = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (dec * (1.0 - 0.15 * i))) for i, (f, a) in enumerate(fs_))
    return y + 0.4 * hp(noise(len(t)), 3000) * np.exp(-t / 0.01)
def whoosh(d, lo=500, hi=2500):
    t = tt(d); env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2; return bp(noise(len(t)), lo, hi) * env
def drill(d=0.38):
    t = tt(d); f = 150 + 120 * np.clip(t / 0.12, 0, 1); ph = 2 * np.cumsum(f) / SR * np.pi
    y = (np.sign(np.sin(ph)) * 0.5 + np.sin(ph)) * 0.5; y += 0.6 * bp(noise(len(t)), 1500, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * t))
    env = np.clip(t / 0.03, 0, 1) * np.clip((d - t) / 0.04, 0, 1); return y * env
def noise_bed(d, f, g): return lp(noise(int(d * SR)), f, 1) * g
# ---- ambience (quiet air + distant garden)
amb = lp(noise(N), 600, 1); amb = 0.05 * amb / np.abs(amb).max(); L += amb; R += amb * 0.9
# ---- van drive 0..6.17 s : engine + tyres, speed profile = derivative of the van path
T0, T1 = 0.0, 185 / FPS; t = np.arange(int((T1 + 0.2) * SR)) / SR; u = np.clip(t / T1, 0, 1)
_vs = [e for e in ev if e["name"] == "VAN_SPEED"]
if _vs:      # v3: real speed profile exported by build_scene.py (one value per frame)
    vv = np.array(_vs[0]["v"], float); spd = np.interp(t * FPS, np.arange(len(vv)) + 0.0, vv / vv.max()); spd = np.where(t < T1, spd, 0)
else:
    spd = 1.8 * (1 - u) ** 0.8; spd /= spd.max(); spd = np.where(t < T1, spd, 0) * np.clip((t) / 0.5, 0, 1)
ph = 2 * np.pi * np.cumsum(30 + 38 * spd) / SR
eng = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph) + 0.25 * np.sin(4.02 * ph)) * (0.25 + 0.75 * spd)
eng = lp(eng, 900, 2) * 0.28
tyre = bp(noise(len(t)), 120, 1400) * spd ** 1.2 * 0.45
idle = np.sin(2 * np.pi * np.cumsum(24 + 0 * t) / SR * 1) * 0.05
sig = (eng + tyre) * np.clip((T1 + 0.2 - t) / 0.4, 0, 1)
add(sig, 0, 1.0)
# brake squeal + air hiss + engine off
sq = bp(noise(int(0.5 * SR)), 2200, 3400) * np.sin(np.pi * np.linspace(0, 1, int(0.5 * SR))) ** 2; add(sq, T1 - 0.65, 0.07)
hiss = hp(noise(int(0.9 * SR)), 2500) * np.exp(-tt(0.9) / 0.35); add(hiss, T1 - 0.05, 0.16)
add(thud(55, 0.5, 0.15, 0.2, 200), T1 + 0.05, 0.3)
# ---- events
for e in ev:
    n, f0, f1 = e["name"], e["f0"] / FPS, e["f1"] / FPS
    if n == "DOOR":
        add(steel([(1400, 0.5), (2300, 0.3)], 0.2, 0.05), f0 - 0.05, 0.2)                       # handle
        cr = bp(noise(int(0.9 * SR)), 700, 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * tt(0.9))) * np.sin(np.pi * np.linspace(0, 1, int(0.9 * SR))); add(cr, f0 + 0.1, 0.10)  # hinge creak
        add(thud(85, 0.5, 0.11, 0.7, 700), f1 + 0.05, 0.55); add(steel([(520, 0.4), (910, 0.3), (1630, 0.2)], 0.5, 0.12), f1 + 0.05, 0.18)
    elif n.startswith("carton"):
        add(whoosh(f1 - f0 - 0.1, 400, 1800), f0 + 0.05, 0.13); add(thud(75, 0.4, 0.07, 0.9, 900), f1, 0.5)
        add(bp(noise(int(0.3 * SR)), 1500, 6000) * np.exp(-tt(0.3) / 0.07), f1 + 0.02, 0.10)
    elif n == "OPEN":
        add(bp(noise(int(0.5 * SR)), 1000, 5000) * np.sin(np.pi * np.linspace(0, 1, int(0.5 * SR))) ** 2, f0, 0.14)
    elif n.startswith("stopa"):
        add(whoosh(f1 - f0, 600, 2800), f0, 0.07); add(steel([(1900, 0.6), (2950, 0.35), (4400, 0.2)], 0.5, 0.07), f1, 0.22); add(thud(110, 0.25, 0.04, 0.4, 600), f1, 0.25)
    elif n.startswith("post"):
        add(whoosh(f1 - f0, 300, 1500), f0, 0.06); add(wood_tok(310), f1, 0.42)
    elif n.startswith("trojak"):
        add(whoosh(f1 - f0, 600, 2800), f0, 0.07); add(steel([(1250, 0.6), (1980, 0.4), (3100, 0.25)], 0.55, 0.10), f1, 0.28); add(thud(130, 0.25, 0.04, 0.4, 700), f1, 0.22)
        add(drill(0.4), f1 + 0.08, 0.20, 0.0)
    elif n.startswith("beam"):
        add(whoosh(f1 - f0, 300, 1400), f0, 0.07); add(wood_tok(200, 0.4, 0.09), f1, 0.5); add(drill(0.32), f1 + 0.1, 0.17)
    elif n.startswith("mb2"):
        add(steel([(2200, 0.45), (3500, 0.3)], 0.25, 0.04), f1, 0.14); add(drill(0.26), f1 + 0.03, 0.12)
    elif n.startswith("rafter"):
        add(whoosh(f1 - f0, 400, 1800), f0, 0.05); add(wood_tok(260, 0.3, 0.05), f1, 0.30)
    elif n.startswith("slat"):
        add(wood_tok(560, 0.18, 0.025), f1, 0.17)
# ---- master
pk = max(np.abs(L).max(), np.abs(R).max()); g = 0.8 / pk
fade = np.clip((DUR - np.arange(N) / SR) / 0.8, 0, 1) * np.clip(np.arange(N) / SR / 0.1, 0, 1)
st = np.stack([L * g * fade, R * g * fade], 1)
import wave
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(st, -1, 1) * 32767).astype('<i2').tobytes())
print("wrote", out)
