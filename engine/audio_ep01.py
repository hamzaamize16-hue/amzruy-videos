import os
import numpy as np, random
from scipy.signal import lfilter, butter
from scipy.io import wavfile
SR = 44100
TOT = 61.6
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

# --- melody ---
H = {'D4': 293.66, 'Eb4': 311.13, 'F#4': 369.99, 'G4': 392.0, 'A4': 440.0, 'Bb4': 466.16, 'C5': 523.25, 'D5': 587.33, 'A3': 220.0, 'D3': 146.83}
bpm = 92; beat = 60 / bpm
motifA = [('D4', 0), ('Eb4', .5), ('F#4', 1), ('G4', 1.5), ('A4', 2), ('G4', 3), ('F#4', 3.5), ('Eb4', 4), ('D4', 5)]
motifB = [('A4', 0), ('Bb4', .5), ('A4', 1), ('G4', 1.5), ('F#4', 2), ('G4', 2.5), ('A4', 3), ('F#4', 4), ('Eb4', 4.5), ('D4', 5)]
motifC = [('D5', 0), ('C5', .5), ('Bb4', 1), ('A4', 1.5), ('G4', 2), ('F#4', 3), ('G4', 3.5), ('A4', 4), ('D4', 5.5)]
cache = {}
def note(n):
    if n not in cache: cache[n] = pluck(H[n], 1.8)
    return cache[n]
# intro sparse (0-8.5)
for i, (n, b) in enumerate(motifA[:5]):
    add(mus, note(n), 0.6 + b * beat * 1.4, 0.16, -0.2)
add(mus, note('D3'), 0.6, 0.18)
# after reveal: phrases every 8 beats
start = 7.9
phr = [motifA, motifB, motifA, motifC, motifB, motifA, motifC, motifA]
cur = start
k = 0
while cur < TOT - 4:
    m = phr[k % len(phr)]
    for (n, b) in m:
        add(mus, note(n), cur + b * beat, 0.17, 0.25 if k % 2 else -0.25)
    add(mus, note('D3'), cur, 0.2)
    add(mus, note('A3'), cur + 4 * beat, 0.14)
    cur += 8 * beat; k += 1
add(mus, note('D4'), TOT - 3.6, 0.2); add(mus, note('D3'), TOT - 3.6, 0.22)

# --- frame drum ---
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
cur = start
bar = 0
while cur < TOT - 3:
    pattern = [(0, 'D'), (1, 'T'), (1.5, 'T'), (2, 'D'), (2.5, 'D'), (3, 'T')]
    for b, kd in pattern:
        tm = cur + b * beat
        if kd == 'D': add(mus, D, tm, 0.32)
        else: add(mus, T_, tm, 0.07, 0.3)
    cur += 4 * beat; bar += 1
# light tak intro
for i in range(10):
    add(mus, T_, 0.6 + i * beat * 1.4 * 2, 0.04, 0.3)

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
def verb(x):
    out = x.copy()
    for d, g in ((0.037, .35), (0.071, .28), (0.113, .22), (0.173, .16), (0.251, .1)):
        k = int(d * SR)
        out[k:, 0] += x[:-k, 1] * g; out[k:, 1] += x[:-k, 0] * g
    return out
mus = verb(mus)
import subprocess
v = np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',os.environ.get('AMZ_VOICE','voice.mp3'),'-ac','1','-ar',str(SR),'-f','s16le','-'],capture_output=True).stdout,np.int16).astype(np.float32)/32768
v = hp(v, 70).astype(np.float32)
segs = [(0.0,3.6,0.1),(3.75,7.45,4.05),(7.45,8.6,8.2),(8.75,16.2,11.0),(16.2,23.75,18.35),(23.75,29.95,26.35),(29.95,38.1,32.65),(38.1,54.4,40.85),(54.4,57.81,57.2)]
voice = np.zeros(N, np.float32)
for a,b,at in segs:
    seg = v[int(a*SR):int(b*SR)].copy(); f=int(0.015*SR)
    seg[:f]*=np.linspace(0,1,f); seg[-f:]*=np.linspace(1,0,f)
    i=int(at*SR); seg=seg[:N-i]; voice[i:i+len(seg)]+=seg
voice /= np.abs(voice).max()/0.9
env = np.abs(voice); 
w=int(0.25*SR); env = np.convolve(env, np.ones(w)/w, 'same')
env = np.clip(env/ (env.max()*0.25), 0, 1)
duck = 1 - 0.72*env
musfx = (mus*0.9 + sfx*0.9)
musfx /= np.abs(musfx).max()
mix = musfx*duck[:,None]*0.55 + voice[:,None]*1.0
mix /= max(1e-6, np.abs(mix).max()) / 0.89
wavfile.write('' + os.environ.get('AMZ_OUT','.') + '/mix_voice.wav', SR, (mix * 32767).astype(np.int16))
print('ok', np.abs(mix).max())
