# EP02 - La khettara : moteur low-poly 3D (rasteriseur PIL, painter's algorithm)
import math, random, sys, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTDIR = os.environ.get('AMZ_OUT', '/home/claude/work/ep02')
BRAND = os.environ.get('AMZ_BRAND', '/home/claude/hamzaamize16-hue/amzruy-videos/brand/')
W, H, FPS = 1080, 1920, 30
SS = 2
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RAQM = ImageFont.Layout.RAQM
_fc = {}
def font(size, path=FB):
    k = (size, path)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, layout_engine=RAQM)
    return _fc[k]

GOLD = (233, 189, 92); GOLD2 = (255, 222, 140); CREAM = (246, 236, 214)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def ease_back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def prog(t, a, b): return clamp((t - a) / (b - a))
def lerp(a, b, x): return a + (b - a) * x
def mix(c1, c2, x): return tuple(int(lerp(a, b, clamp(x))) for a, b in zip(c1, c2))

def paste(base, im, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = np.asarray(im.getchannel("A"), dtype=np.float32) * alpha
        im = im.copy(); im.putalpha(Image.fromarray(a.astype(np.uint8)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ================= background (brand) =================
def make_bg():
    BW, BH = int(W * 1.2), int(H * 1.2)
    y, x = np.mgrid[0:BH, 0:BW].astype(np.float32)
    d = np.sqrt(((x - BW * 0.5) / BW) ** 2 + ((y - BH * 0.36) / BH) ** 2)
    c1 = np.array([26, 46, 86], np.float32); c2 = np.array([4, 8, 20], np.float32)
    m = np.clip(d / 0.75, 0, 1)[..., None]
    img = Image.fromarray((c1 * (1 - m) + c2 * m).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
    cxg, cyg = BW / 2, BH / 2; span = max(BW, BH) * 0.9
    for k in range(-9, 10):
        f = k / 9
        pts = [(cxg + f * span * 0.6 * math.cos(t * 0.9), cyg + span * 0.55 * math.sin(t * 0.9)) for t in [i / 59 * math.pi - math.pi / 2 for i in range(60)]]
        dr.line(pts, fill=(233, 189, 92, 22), width=2)
    for k in range(-8, 9):
        yy = cyg + k * span * 0.065
        dr.line((0, yy, BW, yy), fill=(233, 189, 92, 16), width=2)
    img.alpha_composite(lay)
    return img

BG = GRAIN = VIG = None
def init():
    global BG, GRAIN, VIG
    BG = make_bg()
    rng = np.random.default_rng(2)
    GRAIN = [rng.normal(0, 7, (H, W, 1)).astype(np.float32) for _ in range(6)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    VIG = np.clip(1.15 - v * 0.5, 0.4, 1.0)[..., None].astype(np.float32)

rng0 = random.Random(11)
DUST = [(rng0.random(), rng0.random(), rng0.uniform(1.5, 4), rng0.uniform(0.01, 0.035), rng0.random() * 6.28) for _ in range(60)]
def background(T):
    ox = int((BG.width - W) / 2 + 40 * math.sin(T * 0.1)); oy = int((BG.height - H) / 2 + 60 * math.cos(T * 0.07))
    fr = BG.crop((ox, oy, ox + W, oy + H)).copy(); dr = ImageDraw.Draw(fr)
    for (x, y, r, sp, ph) in DUST:
        px = (x * W + 30 * math.sin(T * 0.5 + ph)) % W; py = (y * H - T * sp * H) % H
        a = int(100 + 80 * math.sin(T * 2 + ph))
        dr.ellipse((px - r, py - r, px + r, py + r), fill=(255, 214, 140, max(0, a)))
    return fr

def finish(img, T, total, tint=None):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    if tint is not None: arr = arr * (1 - tint[1]) + np.array(tint[0], np.float32) * tint[1] * (arr / 255.0) * 1.6
    arr = arr * VIG + GRAIN[int(T * FPS) % len(GRAIN)]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(out)
    d.rectangle((0, 0, W, 10), fill=(20, 20, 30)); d.rectangle((0, 0, int(W * T / total), 10), fill=GOLD)
    return out

def caption(base, txt, t_in, t, gold=False, y=1600):
    if not txt: return
    p = ease_back(prog(t, t_in, t_in + 0.35)); a = prog(t, t_in, t_in + 0.2)
    f = font(62); words = txt.split(" "); lines, cur = [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if f.getlength(test) > 880 and cur: lines.append(cur); cur = w_
        else: cur = test
    lines.append(cur); lh = 92; tot = lh * len(lines)
    box = Image.new("RGBA", (W, tot + 70), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
    maxw = max(f.getlength(l) for l in lines)
    bd.rounded_rectangle(((W - maxw) / 2 - 40, 5, (W + maxw) / 2 + 40, tot + 60), radius=34, fill=(5, 8, 18, 180))
    for i, l in enumerate(lines):
        bd.text((W / 2, 35 + lh * i + lh / 2), l, font=f, anchor="mm", fill=GOLD2 if gold else (255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    paste(base, box, W / 2, y, alpha=a, scale=lerp(0.85, 1.0, p))

# ================= 3D core =================
LIGHT = np.array([-0.45, 1.0, 0.65]); LIGHT = LIGHT / np.linalg.norm(LIGHT)
class Cam:
    def __init__(s, target, az, el, dist, fov=1.25, cy=0.40):
        s.t = np.array(target, float)
        s.pos = s.t + dist * np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])
        f = s.t - s.pos; s.f = f / np.linalg.norm(f)
        r = np.cross(s.f, [0, 1, 0]); s.r = r / np.linalg.norm(r); s.u = np.cross(s.r, s.f)
        s.foc = fov * W * SS; s.cx = W * SS / 2; s.cy = H * SS * cy
    def proj(s, P):
        d = P - s.pos
        x = d @ s.r; y = d @ s.u; z = d @ s.f
        z = np.maximum(z, 1e-3)
        return np.stack([s.cx + s.foc * x / z, s.cy - s.foc * y / z], 1), z

class Scene3D:
    def __init__(s): s.polys = []
    def add(s, pts, col, group=1, lit=True, cull=True, bias=0.0):
        s.polys.append((np.asarray(pts, float), col, group, lit, cull, bias))
    def render(s, cam, layer):
        dr = ImageDraw.Draw(layer)
        items = []
        for i, (P, col, g, lit, cull, bias) in enumerate(s.polys):
            if lit or cull:
                n = np.cross(P[1] - P[0], P[2] - P[0]); nn = np.linalg.norm(n)
                if nn < 1e-9: continue
                n = n / nn
                c = P.mean(0)
                if cull and np.dot(n, cam.pos - c) < 0: continue
                if lit:
                    k = 0.55 + 0.5 * max(0.0, float(np.dot(n, LIGHT)))
                    col = tuple(int(min(255, ch * k)) for ch in col[:3])
            d = P - cam.pos
            C = np.stack([d @ cam.r, d @ cam.u, d @ cam.f], 1)
            NEAR = 0.1
            if C[:, 2].min() < NEAR:
                if C[:, 2].max() < NEAR: continue
                out = []
                for k in range(len(C)):
                    a, b = C[k], C[(k + 1) % len(C)]
                    ina, inb = a[2] >= NEAR, b[2] >= NEAR
                    if ina: out.append(a)
                    if ina != inb:
                        tt = (NEAR - a[2]) / (b[2] - a[2]); out.append(a + (b - a) * tt)
                if len(out) < 3: continue
                C = np.array(out)
            z = C[:, 2]
            scr = np.stack([cam.cx + cam.foc * C[:, 0] / z, cam.cy - cam.foc * C[:, 1] / z], 1)
            items.append((g, -(z.mean() + bias) if g != 2 else i, scr, col))
        items.sort(key=lambda it: (it[0], it[1]))
        for g, _, scr, col in items:
            dr.polygon([tuple(p) for p in scr], fill=tuple(col[:3]) + (255,))

def box(sc, x0, x1, y0, y1, z0, z1, col, group=3):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 4, 7, 3), (1, 2, 6, 5), (3, 7, 6, 2), (0, 1, 5, 4)]:
        sc.add([v[i] for i in f], col, group)

def cone(sc, cx, cy, cz, r, h, col, seg=7, r_top=0.0, top_col=None, group=3, half=False, rot=0.0):
    a0, a1 = (0, math.pi) if half else (0, 2 * math.pi)
    angs = [rot + a0 + (a1 - a0) * i / seg for i in range(seg + 1)]
    for i in range(seg):
        a, b = angs[i], angs[i + 1]
        p0 = (cx + r * math.cos(a), cy, cz - r * math.sin(a)); p1 = (cx + r * math.cos(b), cy, cz - r * math.sin(b))
        if r_top > 0:
            q0 = (cx + r_top * math.cos(a), cy + h, cz - r_top * math.sin(a)); q1 = (cx + r_top * math.cos(b), cy + h, cz - r_top * math.sin(b))
            sc.add([p0, p1, q1, q0], col, group)
        else:
            sc.add([p0, p1, (cx, cy + h, cz)], col, group)
    if r_top > 0 and top_col is not None:
        sc.add([(cx + r_top * math.cos(a), cy + h + 0.004, cz - r_top * math.sin(a)) for a in reversed(angs[:-1] if not half else angs)], top_col, group, lit=False, cull=False, bias=-0.01)

# ================= terrain model =================
X0, X1, ZB, YB = -6.0, 6.5, -3.0, -3.0
XEXIT = 5.0
def surf(x):
    return 2.2 - 0.32 * (min(x, XEXIT) + 6)
def hnoise(x, z):
    if x >= XEXIT - 0.01: return 0.02 * math.sin(x * 7 + z * 5)
    return 0.07 * math.sin(x * 3.1 + z * 2.3) + 0.04 * math.sin(x * 7.7 - z * 5.1)
def top(x, z=0.0): return surf(x) + hnoise(x, z)
def tun(x): return -0.8 + (surf(XEXIT) + 0.8) * (x + 5) / (XEXIT + 5)
WELLS = [-5.0, -3.75, -2.5, -1.25, 0.0, 1.25, 2.5, 3.75]
XS = np.linspace(X0, X1, 26)
ZS = [0.0, -0.75, -1.5, -2.25, -3.0]

SAND = (226, 186, 122); SAND2 = (214, 170, 104); GREEN = (96, 160, 70); GREEN2 = (70, 135, 55)
WATER = (64, 168, 228); WATER2 = (150, 215, 250)

def wt(x, drop=0.0): return -0.35 - 0.06 * (x + 6) - drop
def aq_thick(x): return 0.95 if x < -2.5 else max(0.0, 0.95 * (-1.0 - x) / 1.5)

def build_block(sc, st):
    g = st.get('green', 0.0)
    # top surface
    for i in range(len(XS) - 1):
        for j in range(len(ZS) - 1):
            xa, xb, za, zb = XS[i], XS[i + 1], ZS[j], ZS[j + 1]
            pa = (xa, top(xa, za), za); pb = (xb, top(xb, za), za); pc = (xb, top(xb, zb), zb); pd = (xa, top(xa, zb), zb)
            base = SAND if (i + j) % 2 == 0 else SAND2
            if xa >= XEXIT - 0.01: base = mix(base, GREEN if (i + j) % 2 == 0 else GREEN2, g)
            elif xa >= XEXIT - 1.01 and za < -0.5: base = mix(base, GREEN2, g * 0.6)
            sc.add([pa, pb, pc], base, 1); sc.add([pa, pc, pd], mix(base, (0, 0, 0), 0.04), 1)
    # side faces (right, left, back)
    for (x, sgn) in [(X1, 1), (X0, -1)]:
        pts = [(x, YB, 0), (x, YB, ZB), (x, top(x, ZB), ZB), (x, top(x, 0), 0)]
        if sgn < 0: pts = pts[::-1]
        sc.add(pts, (150, 100, 62), 1)
    back = [(x, top(x, ZB), ZB) for x in XS][::-1] + [(X0, YB, ZB), (X1, YB, ZB)]
    sc.add(back[::-1], (150, 100, 62), 1)
    # front cross-section (group 2, insertion order = painter order)
    xs = np.linspace(X0, X1, 60)
    tops = [top(x, 0) for x in xs]
    def band(u, l, col):
        up = [(x, u(x)) for x in xs]; lo = [(x, min(l(x), u(x))) for x in xs]
        sc.add([(x, y, 0) for x, y in up] + [(x, y, 0) for x, y in lo[::-1]], col, 2, lit=False, cull=False)
    band(lambda x: top(x, 0), lambda x: YB, (112, 74, 50))
    band(lambda x: top(x, 0), lambda x: top(x, 0) - 0.28, (210, 164, 98))
    band(lambda x: top(x, 0) - 0.28, lambda x: max(top(x, 0) - 1.15 + 0.12 * math.sin(x * 1.3), -2.25 + 0.1 * math.sin(x * 2)), (190, 132, 78))
    band(lambda x: max(top(x, 0) - 1.15 + 0.12 * math.sin(x * 1.3), -2.25 + 0.1 * math.sin(x * 2)), lambda x: -2.25 + 0.1 * math.sin(x * 2), (158, 100, 64))
    # aquifer
    drop = st.get('aq_drop', 0.0); aqa = st.get('aq', 1.0)
    if aqa > 0:
        ax = np.linspace(X0, -1.0, 30)
        col = mix((158, 100, 64), (52, 128, 196), aqa)
        tp = [(x, wt(x, drop)) for x in ax]; bt = [(x, wt(x, 0) - aq_thick(x) - 0.0) for x in ax]
        bt = [(x, min(y, wt(x, drop))) for x, y in bt]
        sc.add([(x, y, 0) for x, y in tp] + [(x, y, 0) for x, y in bt[::-1]], col, 2, lit=False, cull=False)
        if st.get('aq_glow', 0) > 0:
            gl = st['aq_glow']
            tp2 = [(x, wt(x, drop)) for x in ax]; tp3 = [(x, wt(x, drop) - 0.08) for x in ax]
            sc.add([(x, y, 0) for x, y in tp2] + [(x, y, 0) for x, y in tp3[::-1]], mix(col, WATER2, gl), 2, lit=False, cull=False)
    # tunnel
    tp_ = st.get('tunnel', 0.0)
    if tp_ > 0:
        xe = -5 + (XEXIT - (-5)) * tp_
        tx = np.linspace(-5, xe, 40)
        sc.add([(x, tun(x) + 0.13, 0) for x in tx] + [(x, tun(x) - 0.13, 0) for x in tx[::-1]], (38, 24, 16), 2, lit=False, cull=False)
        wp = st.get('water', 0.0); lvl = st.get('wlevel', 0.62)
        if wp > 0 and lvl > 0:
            xw = -5 + (min(xe, XEXIT) + 5) * wp
            wx = np.linspace(-5, xw, 40)
            sc.add([(x, tun(x) - 0.13 + 0.26 * lvl, 0) for x in wx] + [(x, tun(x) - 0.13, 0) for x in wx[::-1]], WATER, 2, lit=False, cull=False)
            T = st.get('T', 0.0)
            for k in range(40):
                x = -5 + ((k * 0.42 + T * 1.6) % 10.5)
                if x + 0.25 > xw: continue
                y = tun(x) - 0.13 + 0.26 * lvl * 0.55
                sc.add([(x, y + 0.025, 0), (x + 0.22, tun(x + 0.22) - 0.13 + 0.26 * lvl * 0.55 + 0.025, 0), (x + 0.22, tun(x + 0.22) - 0.13 + 0.26 * lvl * 0.55 - 0.01, 0), (x, y - 0.01, 0)], WATER2, 2, lit=False, cull=False)
    # shafts
    for (x, dp) in st.get('wells', []):
        if dp <= 0: continue
        y0 = top(x, 0) + 0.02; yb = (tun(x) - 0.13) if x > -5 else (tun(x) - 0.13)
        y1 = lerp(y0, yb, dp)
        sc.add([(x - 0.09, y0, 0), (x + 0.09, y0, 0), (x + 0.09, y1, 0), (x - 0.09, y1, 0)], (34, 22, 14), 2, lit=False, cull=False)

def build_mounds(sc, st):
    for (x, dp) in st.get('wells', []):
        ms = st.get('mound', {}).get(x, 1.0 if dp > 0 else 0)
        if ms <= 0: continue
        r = 0.34 * ms; h = 0.2 * ms
        y = top(x, 0) - 0.01
        cone(sc, x, y, 0.0, r, h, (200, 152, 92), seg=6, r_top=0.1 * ms, top_col=(30, 20, 12), half=True)
        sc.add([(x - r, y, 0.002), (x + r, y, 0.002), (x + 0.1 * ms, y + h, 0.002), (x - 0.1 * ms, y + h, 0.002)], (214, 168, 102), 3, lit=False, cull=False, bias=-0.6)
        if dp > 0: sc.add([(x - 0.09, y, 0.004), (x + 0.09, y, 0.004), (x + 0.09, y + h + 0.002, 0.004), (x - 0.09, y + h + 0.002, 0.004)], (34, 22, 14), 3, lit=False, cull=False, bias=-0.7)

def palm(sc, x, z, s, health=1.0, seed=0):
    if s <= 0.02: return
    y = top(x, z); hgt = 1.0 * s
    tr = (128, 92, 58); lf = mix((150, 120, 60), (60, 150, 60), health)
    seg = 5
    for i in range(seg):
        a, b = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        r0, r1 = 0.07 * s, 0.045 * s
        sc.add([(x + r0 * math.cos(a), y, z + r0 * math.sin(a)), (x + r0 * math.cos(b), y, z + r0 * math.sin(b)),
                (x + r1 * math.cos(b), y + hgt, z + r1 * math.sin(b)), (x + r1 * math.cos(a), y + hgt, z + r1 * math.sin(a))][::-1], tr, 3)
    cx, cy = x, y + hgt
    droop = lerp(0.25, 0.55, 1 - health)
    for k in range(7):
        a = seed + 2 * math.pi * k / 7
        L = 0.62 * s; dx, dz = math.cos(a), math.sin(a)
        px, pz = -dz, dx
        tip = (cx + dx * L, cy - droop * s, cz := z + dz * L)
        mid = (cx + dx * L * 0.5, cy + 0.12 * s, z + dz * L * 0.5)
        w = 0.13 * s
        sc.add([(cx, cy, z), (mid[0] + px * w, mid[1], mid[2] + pz * w), tip], lf, 3, cull=False)
        sc.add([(cx, cy, z), tip, (mid[0] - px * w, mid[1] - 0.02, mid[2] - pz * w)], mix(lf, (0, 0, 0), 0.15), 3, cull=False)

PALMS = [(5.35, -0.7), (5.9, -1.3), (6.2, -0.55), (5.5, -2.1), (6.15, -2.5), (5.2, -1.55), (4.6, -2.4)]
def build_oasis(sc, st):
    ps = st.get('palms', 0.0); hl = st.get('health', 1.0)
    for i, (x, z) in enumerate(PALMS):
        palm(sc, x, z, ease_back(prog(ps, i * 0.08, i * 0.08 + 0.5)) * (0.8 + 0.25 * ((i * 37) % 5) / 4) * lerp(0.75, 1.0, hl), hl, seed=i * 0.7)
    sg = st.get('seguia', 0.0)
    if sg > 0:
        xe = XEXIT + (X1 - 0.15 - XEXIT) * sg
        y = top(XEXIT, 0) + 0.025
        sc.add([(XEXIT - 0.05, y, -0.08), (xe, y, -0.08), (xe, y, -0.32), (XEXIT - 0.05, y, -0.32)], WATER, 3, lit=False, cull=False, bias=-0.05)
        if sg > 0.5:
            zz = -0.32 - 2.2 * prog(sg, 0.5, 1.0)
            sc.add([(5.75, y, -0.32), (5.95, y, -0.32), (5.95, y, zz), (5.75, y, zz)], WATER, 3, lit=False, cull=False, bias=-0.05)

def mountains(sc, st):
    for (x, z, r, h) in [(-5.2, -2.3, 0.75, 1.5), (-4.1, -2.55, 0.6, 1.1), (-5.65, -1.35, 0.5, 0.9)]:
        y = top(x, z) - 0.05
        cone(sc, x, y, z, r, h * 0.72, (150, 118, 88), seg=6, r_top=r * 0.28, top_col=None, rot=0.3)
        cone(sc, x, y + h * 0.72, z, r * 0.28, h * 0.28, (240, 240, 245), seg=6, rot=0.3)

def tripod(sc, x, t):
    y = top(x, 0); ap = (x, y + 0.75, -0.02)
    for (dx, dz) in [(-0.3, 0.0), (0.3, 0.0), (0.0, -0.35)]:
        b = (x + dx, top(x + dx, dz), dz)
        sc.add([b, (b[0] + 0.025, b[1], b[2]), (ap[0] + 0.012, ap[1], ap[2]), (ap[0] - 0.012, ap[1], ap[2])], (120, 80, 45), 3, lit=False, cull=False)
    by = lerp(top(x, 0) - 0.3, y + 0.45, 0.5 + 0.5 * math.sin(t * 3))
    sc.add([(x - 0.007, ap[1], 0.01), (x + 0.007, ap[1], 0.01), (x + 0.007, by, 0.01), (x - 0.007, by, 0.01)], (60, 40, 25), 3, lit=False, cull=False, bias=-0.3)
    box(sc, x - 0.06, x + 0.06, by - 0.12, by, -0.05, 0.05, (110, 70, 40))
    # worker
    wx, wz = x + 0.55, -0.35; wy = top(wx, wz); bob = 0.02 * math.sin(t * 6)
    box(sc, wx - 0.08, wx + 0.08, wy, wy + 0.34 + bob, wz - 0.06, wz + 0.06, (236, 228, 210))
    box(sc, wx - 0.06, wx + 0.06, wy + 0.36 + bob, wy + 0.47 + bob, wz - 0.06, wz + 0.06, (196, 146, 108))
    box(sc, wx - 0.07, wx + 0.07, wy + 0.46 + bob, wy + 0.5 + bob, wz - 0.07, wz + 0.07, (250, 250, 250))

def canal(sc, st):
    cp = st.get('canal', 0.0)
    if cp <= 0: return
    z0, z1 = -1.45, -1.75
    xe = -4 + 8.5 * cp
    xs = np.linspace(-4, xe, 20)
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        sc.add([(a, top(a, z0) + 0.03, z0), (b, top(b, z0) + 0.03, z0), (b, top(b, z1) + 0.03, z1), (a, top(a, z1) + 0.03, z1)], WATER, 3, lit=False, cull=False, bias=-0.1)

# ---------- aerial (scene 8) ----------
def aerial(sc, st):
    n = 14
    for i in range(n):
        for j in range(n):
            x0, z0 = -21 + 42 * i / n, -21 + 42 * j / n; x1, z1 = x0 + 3, z0 + 3
            hh = lambda x, z: 0.08 * math.sin(x * 0.9 + z * 0.7)
            c = SAND if (i + j) % 2 == 0 else SAND2
            sc.add([(x0, hh(x0, z0), z0), (x0, hh(x0, z1), z1), (x1, hh(x1, z1), z1)], c, 1)
            sc.add([(x0, hh(x0, z0), z0), (x1, hh(x1, z1), z1), (x1, hh(x1, z0), z0)], mix(c, (0, 0, 0), 0.05), 1)
    # green city
    for k in range(12):
        a = 2 * math.pi * k / 12
        sc.add([(0, 0.1, 0), (2.2 * math.cos(a), 0.1, 2.2 * math.sin(a)), (2.2 * math.cos(a + 0.5236), 0.1, 2.2 * math.sin(a + 0.5236))], GREEN if k % 2 else GREEN2, 3, cull=False, bias=-1.0)
    box(sc, -0.15, 0.15, 0.1, 1.2, -0.15, 0.15, (205, 150, 100))
    box(sc, -0.1, 0.1, 1.2, 1.45, -0.1, 0.1, (220, 170, 115))
    lines = st.get('lines', 0)
    rr = random.Random(5)
    for L in range(14):
        a = 2 * math.pi * L / 14 + rr.uniform(-0.1, 0.1)
        vis = clamp(lines * 14 - L)
        if vis <= 0: continue
        for m in range(9):
            if m / 9 > vis: break
            d = 2.6 + m * 0.75
            x, z = d * math.cos(a), d * math.sin(a)
            cone(sc, x, 0.05, z, 0.22, 0.14, (196, 146, 88), seg=6, r_top=0.07, top_col=(30, 20, 12))

# ================= 2D overlays =================
def sun(img, cx, cy, T, a=1.0, r=95):
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for k in range(12):
        ang = T * 0.4 + k * math.pi / 6
        p = [(cx + (r + 25) * math.cos(ang - 0.08), cy + (r + 25) * math.sin(ang - 0.08)), (cx + (r + 85) * math.cos(ang), cy + (r + 85) * math.sin(ang)), (cx + (r + 25) * math.cos(ang + 0.08), cy + (r + 25) * math.sin(ang + 0.08))]
        d.polygon(p, fill=(255, 196, 70, int(220 * a)))
    pts = [(cx + r * math.cos(k * math.pi / 5), cy + r * math.sin(k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=(255, 205, 80, int(255 * a)))
    pts2 = [(cx + r * 0.7 * math.cos(k * math.pi / 5 + 0.3), cy + r * 0.7 * math.sin(k * math.pi / 5 + 0.3)) for k in range(10)]
    d.polygon(pts2, fill=(255, 232, 140, int(255 * a)))
    gl = lay.filter(ImageFilter.GaussianBlur(28))
    img.alpha_composite(gl); img.alpha_composite(lay)

def vapor(img, cam, T, a):
    if a <= 0: return
    d = ImageDraw.Draw(img)
    for k in range(14):
        x = -3.8 + k * 0.6; z = -1.6
        ph = (T * 0.8 + k * 0.37) % 1.0
        P = np.array([[x, top(x, z) + 0.1 + ph * 1.4, z]])
        s, zz = cam.proj(P); sx, sy = s[0] / SS
        al = int(200 * a * math.sin(ph * math.pi))
        pts = [(sx + 14 * math.sin(i * 0.8 + T * 4 + k), sy - i * 9) for i in range(9)]
        d.line(pts, fill=(255, 255, 255, al), width=5)

def counter(img, val, cx, cy, a=1.0, sc=1.0):
    txt = f"{int(val)}"
    f = font(int(230 * sc))
    lay = Image.new("RGBA", (W, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((W / 2, 200), txt, font=f, anchor="mm", fill=GOLD2, stroke_width=10, stroke_fill=(20, 12, 4))
    paste(img, lay, cx, cy, alpha=a)
    sub = Image.new("RGBA", (W, 140), (0, 0, 0, 0)); d2 = ImageDraw.Draw(sub)
    d2.text((W / 2, 70), "خطارة فالحوز", font=font(70), anchor="mm", fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    paste(img, sub, cx, cy + 190, alpha=a)

def bubble(img, cx, cy, s, a):
    if a <= 0: return
    lay = Image.new("RGBA", (360, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 340, 220), 50, fill=(255, 255, 255))
    d.polygon([(90, 210), (150, 210), (80, 285)], fill=(255, 255, 255))
    for i in range(3): d.ellipse((95 + i * 65 - 20, 100, 95 + i * 65 + 20, 140), fill=(193, 39, 45))
    paste(img, lay, cx, cy, alpha=a, scale=s)

def label(img, txt, cx, cy, a=1.0, col=(255, 255, 255), size=54):
    if a <= 0: return
    lay = Image.new("RGBA", (W, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    tw = font(size).getlength(txt)
    d.rounded_rectangle((W / 2 - tw / 2 - 26, 30, W / 2 + tw / 2 + 26, 130), 30, fill=(8, 14, 30, 200), outline=GOLD, width=3)
    d.text((W / 2, 80), txt, font=font(size), anchor="mm", fill=col)
    paste(img, lay, cx, cy, alpha=a, scale=lerp(0.8, 1, ease_back(a)))

def screen_of(cam, p):
    s, _ = cam.proj(np.array([p])); return s[0] / SS

# ================= scenes =================
FULL = dict(wells=[(x, 1.0) for x in WELLS], tunnel=1.0, water=1.0, seguia=1.0, palms=1.0, green=1.0, aq=1.0)

def cam_k(t, dur, a, b, ease=ease_io):
    x = ease(t / dur)
    return Cam([lerp(a[0][i], b[0][i], x) for i in range(3)], lerp(a[1], b[1], x), lerp(a[2], b[2], x), lerp(a[3], b[3], x))

def draw3d(img, cam, builders, st):
    sc = Scene3D()
    for fn in builders: fn(sc, st)
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    # soft shadow
    sh = cam.proj(np.array([[X0, YB - 0.05, 0.3], [X1, YB - 0.05, 0.3], [X1, YB - 0.05, ZB - 0.3], [X0, YB - 0.05, ZB - 0.3]]))[0]
    sc.render(cam, lay)
    lay = lay.reduce(SS)
    shl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shl).polygon([tuple(p / SS + np.array([0, 40])) for p in sh], fill=(0, 0, 0, 120))
    img.alpha_composite(shl.filter(ImageFilter.GaussianBlur(30)))
    img.alpha_composite(lay)

BLOCK = [build_block, mountains, build_mounds, build_oasis]

def sc_hook(img, t, T, dur):
    st = dict(FULL, T=T)
    cam = cam_k(t, dur, ((-1.0, 0.9, -0.6), 0.2, 0.8, 4.6), ((0.3, -0.2, -1.0), 0.42, 0.42, 13.5))
    draw3d(img, cam, BLOCK, st)

def sc_sun(img, t, T, dur):
    st = dict(wells=[], T=T, canal=lerp(1.0, 0.25, ease_io(prog(t, 0.6, dur))), aq=0.0)
    cam = cam_k(t, dur, ((0, 0, -1.4), 0.55, 0.62, 11.5), ((0, 0, -1.4), 0.4, 0.55, 10.5))
    draw3d(img, cam, [build_block, mountains, canal], st)
    sun(img, 830, 300, T, a=ease_out(prog(t, 0, 0.5)), r=90 + 6 * math.sin(T * 5))
    vapor(img, cam, T, prog(t, 0.3, 0.8))

def sc_dig(img, t, T, dur):
    dp = ease_io(prog(t, 0.2, 2.9))
    st = dict(wells=[(-5.0, dp)], mound={-5.0: ease_back(prog(t, 0.0, 0.6))}, T=T, aq=prog(t, 2.5, 2.9), aq_glow=math.sin(math.pi * prog(t, 2.7, dur)))
    cam = cam_k(t, dur, ((-4.4, 0.3, -0.6), 0.32, 0.3, 7.2), ((-4.2, -0.1, -0.6), 0.22, 0.24, 6.4))
    draw3d(img, cam, [build_block, mountains, build_mounds, lambda sc, s: tripod(sc, -5.0, T)], st)
    if t > 2.7:
        p = screen_of(cam, (-5.0, -0.7, 0.0))
        label(img, "الما!", p[0] + 170, p[1] + 20, a=prog(t, 2.7, 3.0), col=(140, 210, 255))

def sc_wells(img, t, T, dur):
    wl = [(-5.0, 1.0)]; md = {-5.0: 1.0}
    for i, x in enumerate(WELLS[1:]):
        a = 0.25 + i * 0.47
        wl.append((x, ease_io(prog(t, a + 0.1, a + 0.6)))); md[x] = ease_back(prog(t, a, a + 0.3))
    st = dict(wells=wl, mound=md, T=T, aq=1.0)
    cam = cam_k(t, dur, ((-3.2, 0.4, -0.8), 0.3, 0.45, 8.0), ((1.0, -0.6, -0.8), 0.1, 0.4, 9.5))
    draw3d(img, cam, [build_block, mountains, build_mounds], st)

def sc_tunnel(img, t, T, dur):
    st = dict(wells=[(x, 1.0) for x in WELLS], T=T, aq=1.0, tunnel=ease_io(prog(t, 0.3, dur - 0.6)))
    cam = cam_k(t, dur, ((-1.5, -0.4, -0.6), 0.05, 0.22, 11.5), ((0.5, -0.6, -0.6), -0.05, 0.18, 11.0))
    draw3d(img, cam, [build_block, mountains, build_mounds], st)
    # slope arrow
    a = prog(t, 2.2, 2.6)
    if a > 0:
        p0 = screen_of(cam, (-4.5, tun(-4.5) - 0.35, 0)); p1 = screen_of(cam, (4.5, tun(4.5) - 0.35, 0))
        d = ImageDraw.Draw(img); col = GOLD + (int(255 * a),)
        d.line([tuple(p0), tuple(p1)], fill=col, width=7)
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        d.polygon([tuple(p1), (p1[0] - 30 * math.cos(ang - 0.45), p1[1] - 30 * math.sin(ang - 0.45)), (p1[0] - 30 * math.cos(ang + 0.45), p1[1] - 30 * math.sin(ang + 0.45))], fill=col)
        label(img, "ميلان خفيف", (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + 90, a=a, size=48)

def sc_flow(img, t, T, dur):
    st = dict(wells=[(x, 1.0) for x in WELLS], T=T, aq=1.0, tunnel=1.0, water=ease_io(prog(t, 0.0, dur)) * 0.95)
    wf = -5 + 10 * st['water']
    cam = cam_k(t, dur, ((-2.5, -0.5, -0.5), -0.15, 0.3, 7.5), ((2.0, -0.9, -0.5), -0.3, 0.3, 7.5))
    draw3d(img, cam, [build_block, mountains, build_mounds], st)
    sun(img, 860, 260, T, a=1.0, r=80)

def sc_oasis(img, t, T, dur):
    st = dict(FULL, T=T, seguia=ease_io(prog(t, 0.2, 1.6)), palms=prog(t, 1.0, 2.6), green=ease_io(prog(t, 1.0, 2.6)))
    cam = cam_k(t, dur, ((4.5, -1.0, -1.2), -0.55, 0.42, 6.0), ((5.2, -0.9, -1.4), -0.85, 0.36, 5.4))
    draw3d(img, cam, BLOCK, st)

def sc_aerial(img, t, T, dur):
    st = dict(lines=ease_io(prog(t, 0.6, 5.5)))
    cam = Cam((0, 0, 0), 0.4 + t * 0.05, lerp(1.25, 1.05, ease_io(t / dur)), lerp(17, 21, ease_io(t / dur)), cy=0.36)
    draw3d_aerial(img, cam, st)
    if t < 1.6: label(img, "الخطارة", W / 2, 230, a=prog(t, 0.05, 0.4), col=GOLD2, size=90)
    c = ease_out(prog(t, 3.9, 6.6))
    if t > 3.8:
        counter(img, 567 * c, W / 2, 1090, a=prog(t, 3.8, 4.1), sc=1 + 0.06 * (1 - prog(t, 6.6, 7.0)) * (c >= 1))

def draw3d_aerial(img, cam, st):
    sc = Scene3D(); aerial(sc, st)
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); sc.render(cam, lay)
    img.alpha_composite(lay.reduce(SS))

def sc_dry(img, t, T, dur):
    k = ease_io(prog(t, 0.6, dur - 0.6))
    st = dict(FULL, T=T, aq_drop=1.3 * k, wlevel=0.62 * (1 - k), water=1.0, seguia=1.0 - k, green=1 - k, palms=1.0, health=1 - k)
    st['seguia'] = max(0.0, 1 - 1.4 * k)
    cam = cam_k(t, dur, ((0.5, -0.4, -1.0), 0.3, 0.38, 12.0), ((0.0, -0.6, -1.0), 0.15, 0.33, 12.5))
    draw3d(img, cam, BLOCK, st)
    if t > 1.2:
        p = screen_of(cam, (-3.5, wt(-3.5, 1.3 * k) - 0.2, 0))
        label(img, "الفرشة نزلات", p[0] + 60, p[1] + 60, a=prog(t, 1.2, 1.5), col=(255, 140, 120), size=46)

def sc_cta(img, t, T, dur):
    st = dict(FULL, T=T)
    cam = Cam((0.3, -0.3, -1.0), 0.45 + 0.25 * math.sin(t * 0.35), 0.45, 13.0)
    draw3d(img, cam, BLOCK, st)
    bubble(img, 820, 300, ease_back(prog(t, 0.2, 0.6)) * (1 + 0.04 * math.sin(T * 5)), prog(t, 0.2, 0.4))

EMB = WM = NAMEV = None
def sc_outro(img, t, T, dur):
    p = ease_back(prog(t, 0, 0.7))
    paste(img, EMB, W / 2, 560, scale=p * (1 + 0.015 * math.sin(T * 2)), rot=(1 - ease_out(prog(t, 0, 0.9))) * 40)
    paste(img, NAMEV, W / 2, 1010, alpha=prog(t, 0.5, 0.9), scale=lerp(0.9, 1.0, ease_out(prog(t, 0.5, 1.0))))
    bp = ease_back(prog(t, 1.0, 1.4))
    btn = Image.new("RGBA", (560, 140), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((0, 0, 559, 139), 70, fill=(204, 0, 0))
    bd.text((280, 70), "تابع  +", font=font(66), anchor="mm", fill=(255, 255, 255))
    paste(img, btn, W / 2, 1335, scale=bp * (1 + 0.04 * math.sin(T * 6)))

# (durée, fonction, sous-titres [(t, texte, or)]) — calé sur les mots de la voix (ElevenLabs Scribe)
SCENES = [
    (4.0, sc_hook, [(0.0, "كيفاش حفرة صغيرة فالصحرا… كتولي واد كيجري تحت الأرض؟", False)]),
    (3.55, sc_sun, [(0.0, "فالجنوب، الشمس كتشرب الما قبل ما يوصل للفلاحة", False)]),
    (3.55, sc_dig, [(0.0, "جدودنا حفرو بير لتحت… حتى لقاو الما", False)]),
    (4.4, sc_wells, [(0.0, "ومن بعد: بير ورا بير، فخط واحد كينزل شوية بشوية", False)]),
    (4.35, sc_tunnel, [(0.0, "وفلقاع، ربطوهم بنفق… بلا موتور، غير بالميلان", True)]),
    (2.95, sc_flow, [(0.0, "الما كيجري بوحدو، والشمس ما كتوصلوش", False)]),
    (3.35, sc_oasis, [(0.0, "وفالأخير كيخرج للسطح… وكتحيا الواحة", True)]),
    (8.0, sc_aerial, [(0.0, "هادي هي الخطارة!", True), (1.4, "تقنية جات مع المرابطين لمراكش", False), (3.8, "وفالسبعينات، كانت فالحوز…", False)]),
    (4.15, sc_dry, [(0.0, "والمفاجأة؟", True), (1.2, "اليوم فمراكش، تقريبا كاملين نشفو", False)]),
    (5.8, sc_cta, [(0.0, "واش عمرك شفتي خطارة بعينيك؟", True), (2.35, "كتب لينا فين فالكومونتير… وتبعنا", False)]),
    (3.0, sc_outro, [(0.1, "تبعنا باش تكتاشف تاريخ المغرب", False)]),
]
TOTAL = sum(s[0] for s in SCENES)
STARTS = [sum(s[0] for s in SCENES[:i]) for i in range(len(SCENES))]

def render_frame(si, t):
    dur, fn, caps = SCENES[si]
    T = STARTS[si] + t
    img = background(T)
    fn(img, t, T, dur)
    cur = None
    for c in caps:
        if t >= c[0]: cur = c
    if cur and not (fn is sc_aerial and t > 3.8):
        caption(img, cur[1], cur[0], t, cur[2], y=1600)
    if fn is not sc_outro: paste(img, WM, 100, 112, alpha=0.9)
    e = prog(t, 0, 0.22)
    if e < 1 and si > 0: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - e) * 0.8))))
    tint = None
    if fn is sc_dry: tint = ((255, 110, 80), 0.18 * prog(t, 0.6, 2.0))
    return finish(img, T, TOTAL, tint)

def setup():
    global WM, EMB, NAMEV
    init()
    WM = Image.open(BRAND + 'logo_embleme_simple.png').convert("RGBA").resize((150, 150), Image.LANCZOS)
    EMB = Image.open(BRAND + 'logo_embleme.png').convert("RGBA").resize((620, 620), Image.LANCZOS)
    lv = Image.open(BRAND + 'logo_vertical_fond_sombre.png').convert("RGBA")
    topc = int(lv.height * 0.535)
    NAMEV = lv.crop((0, topc, lv.width, lv.height)); NAMEV = NAMEV.resize((860, int(NAMEV.height * 860 / NAMEV.width)), Image.LANCZOS)

if __name__ == "__main__":
    setup(); os.makedirs(OUTDIR, exist_ok=True)
    mode = sys.argv[1]
    if mode == "still":
        for spec in sys.argv[2:]:
            si, t = spec.split(":")
            render_frame(int(si), float(t)).save(f"{OUTDIR}/still_{si}_{t}.jpg", quality=88)
    elif mode == "scene":
        for si in map(int, sys.argv[2:]):
            n = int(round(SCENES[si][0] * FPS)); tmp = f"{OUTDIR}/s{si:02d}.tmp.mp4"
            ff = os.environ.get('FFMPEG', 'ffmpeg')
            p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
            for i in range(n): p.stdin.write(render_frame(si, i / FPS).tobytes())
            p.stdin.close()
            if p.wait() == 0: os.rename(tmp, f"{OUTDIR}/s{si:02d}.mp4")
            print("done", si, flush=True)
    elif mode == "total":
        print(TOTAL, STARTS)
