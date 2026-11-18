import os
import numpy as np, random
from scipy.signal import lfilter, butter
from scipy.io import wavfile
SR = 44100
TOT = 47.1
STARTS = [0.0, 4.0, 7.55, 11.1, 15.5, 19.85, 22.8, 26.15, 34.15, 38.3, 44.1]
N = int(SR * TOT)
rng = np.random.default_rng(4)
mus = np.zeros((N, 2), np.float32)
sfx = np.zeros((N, 2), np.float32)

def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i]
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l * 1.414
    buf[i:i + len(sig), 1] += sig * gain * r * 1.414

def lp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2)); return lfilter(b, a, x)
def hp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), 'high'); return lfilter(b, a, x)

def pluck(f, dur=1.6, bright=0.5):
    n = int(SR * dur); p = int(SR / f)
    buf = rng.uniform(-1, 1, p) * 0.8
    buf = lp(buf, 2000 + 4000 * bright, 1)
    out = np.zeros(n, np.float32);
    b = list(buf)
    idx = 0
    damp = 0.996
    for k in range(n):
        v = b[idx]; nx = b[(idx + 1) % p]
        b[idx] = damp * 0.5 * (v + nx)
        out[k] = v; idx = (idx + 1) % p
    # body resonance
    out = out + 0.3 * lp(out, 600)
    env = np.minimum(1, np.arange(n) / 80)
    return (out * env).astype(np.float32)

# --- drone pad ---
t = np.arange(N) / SR
pad = np.zeros(N, np.float32)
for f, g in ((73.42, 0.5), (110.0, 0.3), (146.83, 0.25), (220.0, 0.08)):
    for det in (-0.6, 0.6):
        ph = 2 * np.pi * (f + det) * t
        pad += g * (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph))
pad *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t))
pad = lp(pad, 900)
padenv = np.clip(t / 3, 0, 1) * np.clip((TOT - t) / 2.5, 0, 1)
padenv *= np.where((t > 7.0) & (t < 7.9), 1 - (t - 7.0) / 0.9 * 0.7, 1)  # dip before reveal
mus[:, 0] += pad * padenv * 0.10; mus[:, 1] += pad * padenv * 0.10


# --- EP02: mode nahawand sur Do, 84 bpm, ney-like pluck plus grave ---
H = {'C4': 261.63, 'D4': 293.66, 'Eb4': 311.13, 'F4': 349.23, 'G4': 392.0, 'Ab4': 415.3, 'B4': 493.88, 'C5': 523.25, 'G3': 196.0, 'C3': 130.81}
bpm = 84; beat = 60 / bpm
mA = [('C4', 0), ('D4', .5), ('Eb4', 1), ('F4', 1.5), ('G4', 2), ('Eb4', 3), ('D4', 3.5), ('C4', 4)]
mB = [('G4', 0), ('Ab4', .5), ('G4', 1), ('F4', 1.5), ('Eb4', 2), ('F4', 2.5), ('G4', 3), ('D4', 4), ('C4', 5)]
mC = [('C5', 0), ('B4', .5), ('Ab4', 1), ('G4', 1.5), ('F4', 2), ('Eb4', 3), ('D4', 3.5), ('C4', 4.5)]
cache = {}
def note(n):
    if n not in cache: cache[n] = pluck(H[n], 1.8, 0.35)
    return cache[n]
for (n, b) in mA[:4]: add(mus, note(n), 0.3 + b * beat * 1.5, 0.15, -0.2)
add(mus, note('C3'), 0.3, 0.18)
cur = STARTS[3]; k = 0; phr = [mA, mB, mA, mC, mB, mA]
while cur < TOT - 4:
    if STARTS[8] - 0.2 < cur < STARTS[9]: cur += 8 * beat; k += 1; continue
    for (n, b) in phr[k % len(phr)]: add(mus, note(n), cur + b * beat, 0.16, 0.25 if k % 2 else -0.25)
    add(mus, note('C3'), cur, 0.2); add(mus, note('G3'), cur + 4 * beat, 0.13)
    cur += 8 * beat; k += 1
add(mus, note('C4'), TOT - 2.9, 0.2); add(mus, note('C3'), TOT - 2.9, 0.22)

t = np.arange(N) / SR
pad = np.zeros(N, np.float32)
for f, g in ((65.41, 0.5), (98.0, 0.3), (130.81, 0.25), (196.0, 0.08)):
    for det in (-0.5, 0.5):
        ph = 2 * np.pi * (f + det) * t
        pad += g * (np.sin(ph) + 0.3 * np.sin(2 * ph))
pad *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t))
pad = lp(pad, 800)
padenv = np.clip(t / 2.5, 0, 1) * np.clip((TOT - t) / 2.5, 0, 1)
mus[:, 0] += pad * padenv * 0.10; mus[:, 1] += pad * padenv * 0.10
def doum(dur=0.6):
    n = int(SR * dur); tt = np.arange(n) / SR
    f = 55 + 70 * np.exp(-tt * 25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)
    return s.astype(np.float32)
def tak(dur=0.15):
    n = int(SR * dur); tt = np.arange(n) / SR
    s = hp(rng.normal(0, 1, n), 1800) * np.exp(-tt * 40) + 0.5 * np.sin(2 * np.pi * 420 * tt) * np.exp(-tt * 30)
    return s.astype(np.float32)
D = doum(); T_ = tak()
cur = STARTS[3]
while cur < TOT - 3:
    if STARTS[8] < cur < STARTS[9] - 0.1: cur += 4 * beat; continue
    for b, kd in [(0, 'D'), (1, 'T'), (2, 'D'), (2.75, 'T'), (3.5, 'T')]:
        tm = cur + b * beat
        if kd == 'D': add(mus, D, tm, 0.3)
        else: add(mus, T_, tm, 0.07, 0.3)
    cur += 4 * beat

# --- SFX ---
def whoosh(dur=0.5):
    n = int(SR * dur); tt = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    out = np.zeros(n)
    # sweep bandpass by chunks
    env = np.sin(np.pi * tt / dur) ** 2
    lo = lp(x, 1500); hi = hp(x, 600)
    out = (lo * (1 - tt / dur) + hi * (tt / dur)) * env
    return (out / np.abs(out).max()).astype(np.float32)
def boom(dur=2.5):
    n = int(SR * dur); tt = np.arange(n) / SR
    f = 40 + 60 * np.exp(-tt * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.8)
    s += 0.4 * lp(rng.normal(0, 1, n), 400) * np.exp(-tt * 4)
    return (s / np.abs(s).max()).astype(np.float32)
def riser(dur=2.0):
    n = int(SR * dur); tt = np.arange(n) / SR
    s = hp(rng.normal(0, 1, n), 1200) * (tt / dur) ** 2
    s += 0.3 * np.sin(2 * np.pi * (200 + 600 * (tt / dur) ** 2) * tt) * (tt / dur) ** 2
    return (s / np.abs(s).max()).astype(np.float32)
def pop():
    n = int(SR * 0.12); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (900 - 3000 * tt) * tt) * np.exp(-tt * 45)).astype(np.float32)
def thud():
    n = int(SR * 0.7); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * (60 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9) + 0.5 * lp(rng.normal(0, 1, n), 1200) * np.exp(-tt * 25)
    return (s / np.abs(s).max()).astype(np.float32)
def tick():
    n = int(SR * 0.03); tt = np.arange(n) / SR
    return (hp(rng.normal(0, 1, n), 3000) * np.exp(-tt * 200)).astype(np.float32)
def clang():
    n = int(SR * 1.5); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, d in ((1250, 3), (1873, 4), (2741, 5), (3520, 6)))
    s += hp(rng.normal(0, 1, n), 3000) * np.exp(-tt * 60) * 3
    return (s / np.abs(s).max()).astype(np.float32)
def swipe():
    n = int(SR * 0.22); tt = np.arange(n) / SR
    s = hp(rng.normal(0, 1, n), 2500) * np.sin(np.pi * tt / 0.22)
    return (s / np.abs(s).max()).astype(np.float32)

starts = [0, 4.0, 7.9, 10.9, 18.3, 26.3, 32.6, 40.8, 57.1]
W_ = whoosh()
for s in starts[1:]:
    add(sfx, W_, s - 0.25, 0.22)
add(sfx, riser(), 5.9, 0.18)
add(sfx, boom(), 7.9, 0.55)
for i in range(3): add(sfx, swipe(), 4.0 + 0.15 + i * 0.75 + 0.45, 0.25, 0.2)
add(sfx, clang(), 10.9 + 0.15, 0.22)
for i in range(4): add(sfx, pop(), 18.3 + 6.0 + i * 0.45, 0.3)
add(sfx, thud(), 26.3 + 4.85, 0.6)
for i in range(30): add(sfx, tick(), 32.6 + 0.7 + 0.4 + i * 0.1, 0.18)
add(sfx, thud(), 32.6 + 0.7 + 3.75, 0.6)
add(sfx, boom(1.5), 32.6 + 0.7 + 3.75, 0.25)
add(sfx, pop(), 40.8 + 8.8, 0.35)
add(sfx, pop(), 57.1 + 1.2, 0.35)

# reverb-ish on music: simple multi-tap
def bubble(f=600):
    n = int(SR * 0.12); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (f + 2500 * tt) * tt) * np.exp(-tt * 35)).astype(np.float32)
def dig():
    n = int(SR * 0.18); tt = np.arange(n) / SR
    s = lp(rng.normal(0, 1, n), 900) * np.exp(-tt * 25) + 0.6 * np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 30)
    return (s / np.abs(s).max()).astype(np.float32)
W_ = whoosh()
for s in STARTS[1:]: add(sfx, W_, s - 0.25, 0.2)
for i in range(7): add(sfx, dig(), STARTS[2] + 0.3 + i * 0.38, 0.35, -0.2)
add(sfx, boom(1.2), STARTS[2] + 2.75, 0.35)
for i in range(7): add(sfx, pop(), STARTS[3] + 0.25 + i * 0.47, 0.3, -0.5 + i * 0.15)
add(sfx, riser(3.0), STARTS[4] + 0.5, 0.15)
n = int(SR * (STARTS[7] - STARTS[5])); tt = np.arange(n) / SR
flow = lp(rng.normal(0, 1, n), 700) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * tt)) * np.clip(tt / 0.5, 0, 1) * np.clip((n / SR - tt) / 0.5, 0, 1)
add(sfx, flow.astype(np.float32), STARTS[5], 0.08)
rb = random.Random(3)
for i in range(18): add(sfx, bubble(rb.uniform(400, 900)), STARTS[5] + rb.uniform(0, 6), 0.12, rb.uniform(-0.6, 0.6))
add(sfx, riser(), STARTS[7] + 1.9, 0.15)
add(sfx, boom(), STARTS[7], 0.4)
for i in range(26): add(sfx, tick(), STARTS[7] + 3.95 + i * 0.1, 0.16)
add(sfx, thud(), STARTS[7] + 6.6, 0.55)
add(sfx, clang(), STARTS[8] + 0.05, 0.2)
add(sfx, pop(), STARTS[9] + 0.25, 0.35)
add(sfx, pop(), STARTS[10] + 1.0, 0.35)
def verb(x):
    out = x.copy()
    for d, g in ((0.037, .35), (0.071, .28), (0.113, .22), (0.173, .16), (0.251, .1)):
        k = int(d * SR)
        out[k:, 0] += x[:-k, 1] * g; out[k:, 1] += x[:-k, 0] * g
    return out
mus = verb(mus)
import subprocess
FF = os.environ.get('FFMPEG', 'ffmpeg')
v = np.frombuffer(subprocess.run([FF, '-v', 'error', '-i', os.environ.get('AMZ_VOICE', 'voice.mp3'), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout, np.int16).astype(np.float32) / 32768
v = hp(v, 70).astype(np.float32)
voice = np.zeros(N, np.float32); voice[:min(N, len(v))] = v[:N]
voice /= np.abs(voice).max() / 0.9
env = np.abs(voice); w = int(0.25 * SR); env = np.convolve(env, np.ones(w) / w, 'same')
env = np.clip(env / (env.max() * 0.25), 0, 1)
duck = 1 - 0.72 * env
musfx = (mus * 0.9 + sfx * 0.9); musfx /= np.abs(musfx).max()
mix = musfx * duck[:, None] * 0.55 + voice[:, None] * 1.0
mix /= max(1e-6, np.abs(mix).max()) / 0.89
wavfile.write(os.environ.get('AMZ_OUT', '.') + '/mix_voice.wav', SR, (mix * 32767).astype(np.int16))
print('ok', np.abs(mix).max())
