"""Procedural sound track for the Rynek film (no samples, no music): square ambience, wind and parasol canvas, wood / steel / roofing impacts,
cordless impact driver, cutlery and crowd murmur.  Events follow the same timeline constants as build_rynek.py / rynek_gazebo.py.
usage: python3 sound_rynek.py out.wav"""
import sys, wave
import numpy as np

SR = 48000
NF, FPS = 900, 30
DUR = NF / FPS + 0.5
N = int(SR * DUR)
rng = np.random.default_rng(7)

# ---- timeline constants (mirror build_rynek.py / rynek_gazebo.py) ----
NMOD, UMB_T0, UMB_STEP = 9, 62, 6
ASSEM = (168, 0.8, 8)
PH = {'stopa': (0, 14, 3), 'post': (14, 22, 4), 'con': (44, 22, 4), 'beam': (70, 24, 6), 'moc': (96, 10, 0), 'raft': (104, 16, 2), 'roof': (126, 26, 0)}
LIGHTS_AT = 160
NBAYS = NMOD


def asm_land(a, s, key, i):
    off, dur, stag = PH[key]
    t_in = int(round(a + (off + i * stag) * s)); return t_in + max(5, int(round(dur * s)))


# ---- DSP helpers ----
def tt(n): return np.arange(n) / SR


def fshape(x, lo=None, hi=None, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi: g *= 1 / (1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def lp(x, fc): return fshape(x, None, fc)
def hp(x, fc): return fshape(x, fc, None)
def bp(x, lo, hi): return fshape(x, lo, hi)


def noise(n): return rng.normal(0, 1, n)


def slow_env(n, rate, depth=0.5, seed=0):
    r = np.random.default_rng(seed); k = max(2, int(n / SR * rate) + 2)
    pts = r.uniform(1 - depth, 1, k); return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)


def modal(modes, dur, noise_lp=2200, noise_amp=0.5, noise_tau=0.004, lpf=5000):
    n = int(SR * dur); t = tt(n); x = np.zeros(n)
    for f, a, d in modes: x += a * np.sin(2 * np.pi * f * rng.uniform(0.97, 1.03) * t + rng.uniform(0, 6)) * np.exp(-t / d)
    x += lp(noise(n), noise_lp) * np.exp(-t / noise_tau) * noise_amp
    return lp(x, lpf) * np.minimum(t / 0.0006, 1)


def timber(size=1.0, dur=0.32):
    f0 = 150.0 / size
    return modal([(f0, 1.0, 0.060), (f0 * 2.31, 0.55, 0.040), (f0 * 3.73, 0.35, 0.028), (f0 * 6.2, 0.18, 0.016), (f0 * 0.62, 0.7, 0.09)], dur, 2600, 0.7, 0.006, 4200)


def thud(f=95.0, dur=0.4):
    n = int(SR * dur); t = tt(n); fr = f * (1 + 0.8 * np.exp(-t / 0.03))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return (np.sin(ph) * np.exp(-t / 0.09) + 0.35 * lp(noise(n), 900) * np.exp(-t / 0.02)) * np.minimum(t / 0.0006, 1)


def steel(size=1.0, dur=0.22, damp=1.0):
    f0 = 520.0 / size
    return modal([(f0, 0.6, 0.012 * damp), (f0 * 1.9, 0.5, 0.008 * damp), (f0 * 3.1, 0.4, 0.006 * damp), (f0 * 4.7, 0.25, 0.004 * damp)], dur, 7000, 0.8, 0.002, 9000)


def clank(dur=0.35):
    return steel(0.8, dur, 1.6) + 0.5 * timber(1.3, dur)


def roof_sheet(dur=0.6):
    n = int(SR * dur); t = tt(n)
    return (bp(noise(n), 900, 5500) * np.exp(-t / 0.12) * 0.7 + thud(70, dur) * 0.9)


def driver(dur=0.5, f=620.0, ramp=0.06):
    """cordless impact driver: motor whine with gear rattle and final impact clicks"""
    n = int(SR * dur); t = tt(n)
    fr = f * np.minimum(t / ramp, 1) * (1 - 0.15 * np.clip((t - dur * 0.6) / (dur * 0.4), 0, 1))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    motor = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)
    rattle = (np.sin(2 * np.pi * 38 * t) > 0.6).astype(float) * bp(noise(n), 1500, 6000)
    imp = np.zeros(n); k0 = int(n * 0.62)
    for i, p in enumerate(range(k0, n, int(SR * 0.045))):
        seg = min(int(SR * 0.02), n - p); imp[p:p + seg] += bp(noise(seg), 1200, 7000) * np.exp(-np.arange(seg) / (SR * 0.004)) * 2.2
    env = np.minimum(t / 0.03, 1) * np.minimum((dur - t) / 0.05, 1)
    return (lp(motor, 3200) * 0.5 + rattle * 0.25 + imp * 0.7) * env


def rustle(dur=1.2, ratchet=False):
    n = int(SR * dur); t = tt(n)
    x = bp(noise(n), 1200, 7500) * slow_env(n, 14, 0.8, int(dur * 100)) * np.sin(np.pi * t / dur) ** 0.6
    if ratchet:
        for p in np.arange(0.05, dur - 0.1, 0.07):
            i = int(p * SR); seg = int(SR * 0.012)
            x[i:i + seg] += bp(noise(seg), 1800, 6500) * np.exp(-np.arange(seg) / (SR * 0.003)) * 1.6
    return x


def flap(dur=0.18):
    n = int(SR * dur); t = tt(n)
    return bp(noise(n), 200, 2200) * np.exp(-t / 0.045) * np.minimum(t / 0.004, 1)


def cutlery(dur=0.25):
    return modal([(3100, 0.5, 0.05), (4700, 0.4, 0.035), (6900, 0.25, 0.02)], dur, 9000, 0.6, 0.002, 12000) * 0.5


def glass_clink(dur=0.5):
    f = rng.uniform(2100, 3000)
    return modal([(f, 0.6, 0.18), (f * 2.7, 0.4, 0.1), (f * 4.1, 0.2, 0.06)], dur, 9000, 0.3, 0.002, 12000) * 0.5


def voice(dur, f0, vowel, vib=5.0):
    """voiced sound through formants: murmur / laughter syllable"""
    n = int(SR * dur); t = tt(n)
    fr = f0 * (1 + 0.04 * np.sin(2 * np.pi * vib * t) + 0.12 * np.exp(-t / 0.05))
    ph = np.cumsum(fr) / SR; src = (ph % 1.0) * 2 - 1
    src = src + 0.2 * noise(n)
    forms = {'a': [(730, 1090), (1090, 2000)], 'o': [(450, 800), (800, 1500)], 'e': [(530, 1840), (1800, 2700)], 'u': [(350, 800), (800, 1300)]}[vowel]
    out = np.zeros(n)
    for lo, hi in forms: out += bp(src, lo * 0.8, hi * 1.0)
    env = np.minimum(t / 0.03, 1) * np.minimum((dur - t) / 0.06, 1)
    return out * env


# ---- mixing ----
L = np.zeros(N); R = np.zeros(N)


def add(sig, t_sec, gain=1.0, pan=0.0):
    i = int(t_sec * SR)
    if i < 0 or i >= N: return
    sig = sig[:N - i]; gl = gain * (1 - max(0, pan)); gr = gain * (1 + min(0, pan))
    L[i:i + len(sig)] += sig * gl; R[i:i + len(sig)] += sig * gr


def fr2s(f): return f / FPS


def comb(*pairs):
    m = max(len(x) for x, _ in pairs); out = np.zeros(m)
    for x, g in pairs: out[:len(x)] += x * g
    return out


def build():
    n = N; t = tt(n)
    # --- square ambience: low rumble of the town + murmur bands + distant traffic of footsteps
    base = lp(noise(n), 400) * 0.35 + bp(noise(n), 400, 2800) * 0.25 * slow_env(n, 0.6, 0.5, 3)
    L[:] += base * 0.5; R[:] += (lp(noise(n), 400) * 0.35 + bp(noise(n), 400, 2800) * 0.25 * slow_env(n, 0.6, 0.5, 4)) * 0.5
    # distant crowd mumble on the square
    for k in range(int(DUR * 2.2)):
        add(voice(rng.uniform(0.25, 0.7), rng.uniform(110, 260), rng.choice(list('aoeu'))) * 0.06, rng.uniform(0, DUR), 1.0, rng.uniform(-0.8, 0.8))
    # footsteps on setts
    for k in range(int(DUR * 5)):
        n_ = int(SR * 0.05); st = bp(noise(n_), 300, 3000) * np.exp(-np.arange(n_) / (SR * 0.012)); add(st * 0.05, rng.uniform(0, DUR), 1.0, rng.uniform(-0.9, 0.9))
    # pigeons: wing claps
    for tp in (1.4, 4.9, 9.7, 13.6, 19.2, 24.8):
        for j in range(6): add(flap(0.12) * 0.12, tp + j * 0.07, 1.0, rng.uniform(-0.6, 0.6))
    # --- wind and canvas, 0..3.2 s (parasols rocking), swelling
    wn = bp(noise(n), 150, 1800) * np.clip(1 - t / 3.4, 0, 1) ** 0.7 * np.minimum(t / 0.3, 1) * slow_env(n, 3.0, 0.7, 11)
    L[:] += wn * 0.35; R[:] += np.roll(wn, 800) * 0.35
    for tp in np.arange(0.2, 3.2, 0.22):
        add(flap(0.2) * rng.uniform(0.08, 0.2) * (0.6 + 0.8 * tp / 3.2), tp + rng.uniform(-0.04, 0.04), 1.0, rng.uniform(-0.7, 0.7))
    # --- parasols folding and sinking
    for c in range(NMOD):
        f0 = UMB_T0 + c * UMB_STEP; pan = -0.7 + 1.4 * c / (NMOD - 1)
        add(rustle(1.1, ratchet=True) * 0.3, fr2s(f0), 1.0, pan)
        add(thud(110, 0.25) * 0.25, fr2s(f0 + 34 + 28 + 2), 1.0, pan)
    # --- assembly waves
    a0, s, st = ASSEM
    for k in range(NMOD + 1):
        a = a0 + k * st; pan = -0.8 + 1.6 * k / NMOD
        for i in (0, 1):
            add(steel(1.0) * 0.3, fr2s(asm_land(a, s, 'stopa', i)), 1.0, pan)
            add(comb((thud(105, 0.3), 0.5), (timber(1.2), 0.25), (steel(0.9, 0.12), 0.12)), fr2s(asm_land(a, s, 'post', i)), 1.0, pan)
            add(clank() * 0.4, fr2s(asm_land(a, s, 'con', i)), 1.0, pan)
        add(timber(1.0) * 0.5, fr2s(asm_land(a, s, 'beam', 2)), 1.0, pan)
        for ri in (3, 4): add(comb((timber(1.15), 0.45), (steel(1.1, 0.1), 0.1)), fr2s(asm_land(a, s, 'beam', ri)), 1.0, pan)
        # impact driver on the connectors of this column
        tcon = fr2s(asm_land(a, s, 'con', 1)) + 0.10
        add(driver(0.55, 600 + 30 * (k % 3)) * 0.33, tcon, 1.0, pan)
        if k >= 1:
            add(driver(0.5, 700) * 0.28, fr2s(asm_land(a + st, s, 'moc', 5)) + 0.15, 1.0, pan)
    for k in range(NBAYS):
        a = a0 + (k + 1) * st; pan = -0.8 + 1.6 * (k + 0.5) / NMOD
        for i in range(6):
            add(steel(1.3, 0.08) * 0.22, fr2s(asm_land(a, s, 'moc', i) + i), 1.0, pan)
            add(comb((thud(120, 0.22), 0.38), (timber(1.1, 0.2), 0.3)), fr2s(asm_land(a, s, 'raft', i)), 1.0, pan)
        add(roof_sheet(0.7) * 0.55, fr2s(asm_land(a, s, 'roof', 0)), 1.0, pan)
    # lights on: soft relay-like tick
    add(steel(0.5, 0.05) * 0.12, fr2s(a0 + (NBAYS) * st + LIGHTS_AT * s), 1.0, 0.0)
    # --- flight over the square: air movement
    fl0, fl1 = fr2s(540), fr2s(680)
    env = np.zeros(n); i0, i1 = int(fl0 * SR), int(fl1 * SR); env[i0:i1] = np.sin(np.linspace(0, np.pi, i1 - i0)) ** 1.5
    wh = bp(noise(n), 200, 1400) * env
    L[:] += wh * 0.3; R[:] += np.roll(wh, 400) * 0.3
    # --- restaurant atmosphere, builds up once the gazebo is complete: cutlery, glasses, laughter, conversation
    t_on = fr2s(a0 + (NBAYS) * st + 120 * s)
    for kk in range(int((DUR - t_on) * 5.5)):
        tp = rng.uniform(t_on, DUR - 0.4); gain = 0.5 + 0.5 * min(1.0, (tp - t_on) / 6.0)
        r_ = rng.random()
        if r_ < 0.35: add(cutlery() * 0.18 * gain, tp, 1.0, rng.uniform(-0.8, 0.8))
        elif r_ < 0.5: add(glass_clink() * 0.16 * gain, tp, 1.0, rng.uniform(-0.8, 0.8))
        elif r_ < 0.7:
            f0 = rng.uniform(200, 420)
            for j in range(int(rng.integers(3, 7))): add(voice(0.14, f0 * (1 + 0.04 * j), 'a', 0) * 0.12 * gain, tp + j * 0.17, 1.0, rng.uniform(-0.7, 0.7))
        else:
            add(voice(rng.uniform(0.3, 0.8), rng.uniform(110, 240), rng.choice(list('aoeu'))) * 0.1 * gain, tp, 1.0, rng.uniform(-0.8, 0.8))
    for kk in range(int((DUR - t_on) * 3)):
        tp = rng.uniform(t_on, DUR - 1.0); pan = rng.uniform(-0.7, 0.7)
        sg = bp(noise(int(SR * 0.9)), 300, 2400) * slow_env(int(SR * 0.9), 6, 0.9, kk) * np.sin(np.linspace(0, np.pi, int(SR * 0.9)))
        add(sg * 0.05, tp, 1.0, pan)
    # master: gentle fade in/out, limiter
    fade = np.minimum(t / 0.15, 1) * np.minimum((DUR - t) / 0.8, 1)
    L[:] *= fade; R[:] *= fade
    # gentle compressor: keep the quiet street/restaurant bed audible next to the loud assembly bursts
    m = (L + R) / 2; w = int(SR * 0.4)
    env = np.sqrt(np.convolve(m * m, np.ones(w) / w, mode='same')) + 1e-4
    gain = np.clip((0.07 / env) ** 0.6, 0.35, 4.0)
    gain = np.convolve(gain, np.ones(int(SR * 0.25)) / int(SR * 0.25), mode='same')
    L[:] *= gain; R[:] *= gain
    peak = max(np.abs(L).max(), np.abs(R).max()); g = 0.8 / peak
    return np.tanh(L * g * 1.3) / np.tanh(1.3), np.tanh(R * g * 1.3) / np.tanh(1.3)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "rynek_sound.wav"
    l, r_ = build()
    st = np.stack([l, r_], 1); pcm = (np.clip(st, -1, 1) * 32000).astype('<i2')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("wrote", out, DUR, "s")
