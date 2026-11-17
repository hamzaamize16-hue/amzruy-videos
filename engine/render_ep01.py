import math, random, sys, os, subprocess
OUTDIR = os.environ.get('AMZ_OUT', '/home/claude/work/scenes')
BRAND = os.environ.get('AMZ_BRAND', '/home/claude/amzruy-videos/brand/')
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FS = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
RAQM = ImageFont.Layout.RAQM
_fc = {}
def font(size, path=FB):
    k = (size, path)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, layout_engine=RAQM)
    return _fc[k]

GOLD = (233, 189, 92)
GOLD2 = (255, 222, 140)
CREAM = (246, 236, 214)
RED = (193, 39, 45)
GREEN = (0, 98, 51)
NAVY = (8, 18, 40)
INK = (60, 38, 20)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def ease_back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def prog(t, a, b): return clamp((t - a) / (b - a))
def lerp(a, b, x): return a + (b - a) * x

# ---------------- text ----------------
_tc = {}
def text_img(txt, size, fill=CREAM, path=FB, stroke=0, stroke_fill=(0, 0, 0), shadow=True):
    k = (txt, size, fill, path, stroke, stroke_fill, shadow)
    if k in _tc: return _tc[k]
    f = font(size, path)
    l, t, r, b = f.getbbox(txt, stroke_width=stroke)
    pad = 30
    w, h = r - l + pad * 2, b - t + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 4, pad - t + 6), txt, font=f, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        sh = sh.filter(ImageFilter.GaussianBlur(8))
        im.alpha_composite(sh)
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    _tc[k] = im
    return im

def paste(base, im, cx, cy, alpha=1.0, scale=1.0, rot=0.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = np.asarray(im.getchannel("A"), dtype=np.float32) * alpha
        im = im.copy(); im.putalpha(Image.fromarray(a.astype(np.uint8)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def put_text(base, txt, cx, cy, size, fill=CREAM, alpha=1, scale=1, path=FB, stroke=0, sf=(0, 0, 0), rot=0):
    paste(base, text_img(txt, size, fill, path, stroke, sf), cx, cy, alpha, scale, rot)

# ---------------- background ----------------
def star_points(cx, cy, r, rot=0.0, k=8, inner=0.62):
    pts = []
    for i in range(2 * k):
        rr = r if i % 2 == 0 else r * inner
        a = rot + i * math.pi / k
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

def make_bg():
    BW, BH = int(W * 1.2), int(H * 1.2)
    y, x = np.mgrid[0:BH, 0:BW].astype(np.float32)
    d = np.sqrt(((x - BW * 0.5) / BW) ** 2 + ((y - BH * 0.38) / BH) ** 2)
    c1 = np.array([22, 40, 78], np.float32); c2 = np.array([4, 8, 20], np.float32)
    m = np.clip(d / 0.75, 0, 1)[..., None]
    arr = c1 * (1 - m) + c2 * m
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    cxg, cyg = BW / 2, BH / 2
    span = max(BW, BH) * 0.9
    for k in range(-9, 10):
        f = k / 9
        pts = [(cxg + f * span * 0.6 * math.cos(t * 0.9), cyg + span * 0.55 * math.sin(t * 0.9)) for t in [i / 59 * math.pi - math.pi / 2 for i in range(60)]]
        dr.line(pts, fill=(233, 189, 92, 24), width=2)
    for k in range(-8, 9):
        y = cyg + k * span * 0.065
        dr.line((0, y, BW, y), fill=(233, 189, 92, 18), width=2)
    img.alpha_composite(lay)
    return img

BG = None
GRAIN = None
def init():
    global BG, GRAIN
    BG = make_bg()
    rng = np.random.default_rng(1)
    GRAIN = [rng.normal(0, 9, (H, W, 1)).astype(np.float32) for _ in range(6)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    global VIG
    VIG = np.clip(1.15 - v * 0.55, 0.35, 1.0)[..., None].astype(np.float32)

rng0 = random.Random(7)
DUST = [(rng0.random(), rng0.random(), rng0.uniform(1.5, 4.5), rng0.uniform(0.01, 0.04), rng0.random() * 6.28) for _ in range(70)]

def background(T):
    # slow drift of pattern
    ox = int((BG.width - W) / 2 + 50 * math.sin(T * 0.11))
    oy = int((BG.height - H) / 2 + 80 * math.cos(T * 0.08))
    fr = BG.crop((ox, oy, ox + W, oy + H)).copy()
    dr = ImageDraw.Draw(fr)
    for (x, y, r, sp, ph) in DUST:
        px = (x * W + 30 * math.sin(T * 0.5 + ph)) % W
        py = (y * H - T * sp * H) % H
        a = int(110 + 90 * math.sin(T * 2 + ph))
        dr.ellipse((px - r, py - r, px + r, py + r), fill=(255, 214, 140, max(0, a)))
    return fr

def finish(img, T, total):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    arr = arr * VIG + GRAIN[int(T * FPS) % len(GRAIN)]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    # progress bar + tag
    d.rectangle((0, 0, W, 10), fill=(20, 20, 30))
    d.rectangle((0, 0, int(W * T / total), 10), fill=GOLD)
    return out

# ---------------- caption ----------------
def caption(base, txt, t_in, t, gold=False, y=1540):
    if not txt: return
    p = ease_back(prog(t, t_in, t_in + 0.35))
    a = prog(t, t_in, t_in + 0.2)
    f = font(62)
    words = txt.split(" ")
    # wrap at ~ 900px
    lines, cur = [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if f.getlength(test) > 900 and cur:
            lines.append(cur); cur = w_
        else:
            cur = test
    lines.append(cur)
    lh = 92
    tot = lh * len(lines)
    box = Image.new("RGBA", (W, tot + 70), (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    maxw = max(f.getlength(l) for l in lines)
    bd.rounded_rectangle(((W - maxw) / 2 - 40, 5, (W + maxw) / 2 + 40, tot + 60), radius=34, fill=(5, 8, 18, 175))
    for i, l in enumerate(lines):
        bd.text((W / 2, 35 + lh * i + lh / 2), l, font=f, anchor="mm", fill=GOLD2 if gold else (255, 255, 255),
                stroke_width=3, stroke_fill=(0, 0, 0))
    paste(base, box, W / 2, y, alpha=a, scale=lerp(0.85, 1.0, p))

# ---------------- flags ----------------
def us_flag(w=520, h=300):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = h / 13
    for i in range(13):
        d.rectangle((0, i * sh, w, (i + 1) * sh), fill=(178, 34, 52) if i % 2 == 0 else (245, 240, 230))
    cw, ch = w * 0.42, sh * 7
    d.rectangle((0, 0, cw, ch), fill=(40, 52, 110))
    cx, cy, R = cw / 2, ch / 2, ch * 0.34
    for i in range(13):
        a = -math.pi / 2 + i * 2 * math.pi / 13
        d.polygon(star_points(cx + R * math.cos(a), cy + R * math.sin(a), ch * 0.06, -math.pi / 2, 5, 0.4), fill=(255, 255, 255))
    return im

def ma_flag(w=520, h=347):
    im = Image.new("RGBA", (w, h), RED + (255,)); d = ImageDraw.Draw(im)
    cx, cy, R = w / 2, h / 2, h * 0.3
    pts = [(cx + R * math.cos(-math.pi / 2 + i * 4 * math.pi / 5), cy + R * math.sin(-math.pi / 2 + i * 4 * math.pi / 5)) for i in range(5)]
    for i in range(5):
        d.line([pts[i], pts[(i + 1) % 5]], fill=GREEN, width=int(h * 0.045))
    return im

def wave(im, T, amp=10, freq=2.2, speed=4):
    a = np.asarray(im)
    h, w = a.shape[:2]
    out = np.zeros((h + 2 * amp, w, 4), np.uint8)
    for x in range(0, w, 2):
        off = int(amp + amp * math.sin(x / w * freq * math.pi - T * speed) * (x / w))
        out[off:off + h, x:x + 2] = a[:, x:x + 2]
        shade = 1 - 0.18 * math.sin(x / w * freq * math.pi - T * speed + 1.2) * (x / w)
        out[off:off + h, x:x + 2, :3] = np.clip(out[off:off + h, x:x + 2, :3] * shade, 0, 255)
    return Image.fromarray(out)

USF = None; MAF = None

# ================= SCENES =================
# each: (duration, draw_fn, captions[(t, text, gold)])

def sc_hook(img, t, T):
    d = ImageDraw.Draw(img)
    # tag pill
    a = prog(t, 0, 0.3)
    put_text(img, "حقيقة تاريخية", W / 2, 230, 44, GOLD, alpha=a)
    fl = wave(USF, T)
    p = ease_back(prog(t, 0.1, 0.7))
    paste(img, fl, W / 2, 560, alpha=prog(t, 0.1, 0.4), scale=lerp(0.6, 1.0, p))
    put_text(img, "1776", W / 2, 800, 46, (200, 200, 210), alpha=prog(t, 0.4, 0.8))
    # big pulsing ?
    s = 1 + 0.06 * math.sin(t * 6)
    put_text(img, "؟", W / 2, 1110, 330, GOLD, alpha=prog(t, 0.6, 1.0), scale=s * ease_back(prog(t, 0.6, 1.1)), path=FS)

def sc_notthem(img, t, T):
    names = ["فرنسا", "إسبانيا", "هولندا"]
    for i, n in enumerate(names):
        t0 = 0.15 + i * 0.75
        y = 480 + i * 270
        p = ease_back(prog(t, t0, t0 + 0.4))
        a = prog(t, t0, t0 + 0.25)
        card = Image.new("RGBA", (640, 200), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, 639, 199), 36, fill=(255, 255, 255, 30), outline=(255, 255, 255, 90), width=3)
        cd.text((320, 100), n, font=font(96), anchor="mm", fill=CREAM)
        # strike
        sp = ease_out(prog(t, t0 + 0.45, t0 + 0.7))
        if sp > 0:
            cd.line((600, 140, 600 - 560 * sp, 140 - 80 * sp), fill=(230, 50, 50), width=16)
        paste(img, card, W / 2 + (1 - p) * 300, y, alpha=a)
        if sp >= 1:
            put_text(img, "✗", W / 2 - 380, y, 90, (230, 60, 60), path=FR, alpha=prog(t, t0 + 0.7, t0 + 0.8))

def sc_reveal(img, t, T):
    # rays
    a = prog(t, 0, 0.15)
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    cx, cy = W / 2, 760
    n = 24
    for i in range(n):
        ang = i * 2 * math.pi / n + T * 0.25
        ang2 = ang + math.pi / n * 0.6
        rd.polygon([(cx, cy), (cx + 2000 * math.cos(ang), cy + 2000 * math.sin(ang)), (cx + 2000 * math.cos(ang2), cy + 2000 * math.sin(ang2))], fill=(255, 200, 100, 34))
    rays = rays.filter(ImageFilter.GaussianBlur(6))
    paste(img, rays, W / 2, H / 2, alpha=a)
    # star
    st = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.polygon(star_points(350, 350, 330, T * 0.3), outline=GOLD + (200,), width=6)
    sd.polygon(star_points(350, 350, 290, -T * 0.3 + 0.2), outline=GOLD + (120,), width=3)
    paste(img, st, cx, cy, alpha=a, scale=ease_back(prog(t, 0, 0.5)))
    fl = wave(MAF, T, amp=8)
    paste(img, fl, cx, cy, scale=0.9 * ease_back(prog(t, 0.05, 0.55)))
    put_text(img, "المغرب", W / 2, 1150, 170, GOLD2, scale=ease_back(prog(t, 0.25, 0.75)), alpha=prog(t, 0.25, 0.4), stroke=4, sf=(60, 30, 0))
    put_text(img, "20 دجنبر 1777", W / 2, 1320, 64, CREAM, alpha=prog(t, 0.8, 1.1))
    # flash
    fa = 1 - prog(t, 0, 0.35)
    if fa > 0:
        fl2 = Image.new("RGBA", (W, H), (255, 245, 220, int(230 * fa)))
        img.alpha_composite(fl2)

def swords_icon(size=420):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for sgn in (1, -1):
        x0, y0 = size / 2 - sgn * size * 0.38, size * 0.88
        x1, y1 = size / 2 + sgn * size * 0.36, size * 0.1
        d.line((x0, y0, x1, y1), fill=(220, 225, 235), width=16)
        # guard
        mx, my = lerp(x0, x1, 0.2), lerp(y0, y1, 0.2)
        dx, dy = (y1 - y0), -(x1 - x0); L = math.hypot(dx, dy); dx, dy = dx / L * 45, dy / L * 45
        d.line((mx - dx, my - dy, mx + dx, my + dy), fill=GOLD, width=16)
        d.line((x0, y0, mx, my), fill=(110, 70, 30), width=20)
    return im
SWORDS = None

def sc_war(img, t, T):
    p = ease_back(prog(t, 0, 0.5))
    paste(img, SWORDS, W / 2, 720, scale=p, rot=3 * math.sin(T * 3))
    # sparks
    rr = random.Random(int(T * 10))
    d = ImageDraw.Draw(img)
    for i in range(14):
        a = rr.random() * 6.28; r = rr.uniform(40, 220) * prog(t, 0.2, 1)
        x, y = W / 2 + r * math.cos(a), 640 + r * math.sin(a)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 190, 80, 200))
    put_text(img, "بريطانيا", 830, 1060, 66, (230, 120, 120), alpha=prog(t, 0.3, 0.6))
    put_text(img, "أمريكا", 250, 1060, 66, (150, 180, 255), alpha=prog(t, 0.3, 0.6))
    put_text(img, "VS", W / 2, 1060, 60, GOLD, alpha=prog(t, 0.5, 0.8), path=FS)
    put_text(img, "1775 – 1783", W / 2, 1180, 52, CREAM, alpha=prog(t, 0.7, 1.0))

# ---------------- map ----------------
NA = [(-110,62),(-64,60.5),(-61.5,56),(-57,52),(-60,50),(-66,49.2),(-64.5,48.8),(-64.4,47),(-61.2,45.6),(-59.8,45.9),(-63.6,44.6),(-65.7,43.5),(-66.2,44.6),(-64.4,45.3),(-67,44.5),(-70.2,43.6),(-70.8,42.6),(-70.9,42.1),(-70.0,42.0),(-69.95,41.67),(-70.6,41.5),(-71.9,41.3),(-73.7,40.9),(-74,40.5),(-74.1,39.8),(-74.9,38.9),(-75.1,38.4),(-75.6,37.4),(-76.0,36.9),(-75.5,35.2),(-76.5,34.7),(-77.9,33.9),(-79.2,33.2),(-80.6,32.2),(-81.4,30.5),(-80.6,28.4),(-80.1,26.5),(-80.4,25.2),(-81.1,25.1),(-81.8,26.6),(-82.7,28),(-82.8,29.2),(-84,30.1),(-85.5,29.7),(-87.5,30.3),(-89.5,30.2),(-89.4,29.0),(-91,29.2),(-94,29.6),(-97.3,27.6),(-97.6,24),(-97.8,22.3),(-96.5,19.5),(-95,18.5),(-91,18.6),(-90.4,21),(-87.1,21.5),(-87.5,19),(-88.3,16),(-110,16)]
NF = [(-59.4,47.6),(-56,47.6),(-53,46.6),(-52.7,47.6),(-53.5,49.5),(-55.5,51.6),(-57,51.4),(-59.4,48.5)]
CUBA = [(-85,21.8),(-81.5,23.1),(-77,22.3),(-74.2,20.2),(-77.5,19.9),(-80,21.7),(-84.5,21.8)]
HISP = [(-74.4,19.9),(-71,19.9),(-68.4,18.6),(-71.5,17.6),(-74.4,18.4)]
AF = [(-5.92,35.79),(-5.4,35.92),(-5.3,35.6),(-4.4,35.2),(-2.9,35.3),(-2.2,35.1),(0,35.9),(3,36.8),(10,37.3),(11,37),(10.2,34),(11.5,33),(15,32.3),(20,30.5),(20,32),(25,31.7),(32,31.3),(40,31),(40,0),(5,5),(-2,4.8),(-7.5,4.4),(-11,7),(-13,9),(-15,10.8),(-16.8,13.2),(-17.5,14.7),(-16.5,16.6),(-16.3,19.5),(-17.1,20.8),(-16.9,21.3),(-15.9,23.7),(-14.5,26.2),(-12.9,27.9),(-11.5,28.3),(-10.5,29.1),(-9.9,29.9),(-9.6,30.4),(-9.8,31.5),(-9.3,32.5),(-8.5,33.2),(-7.6,33.6),(-6.85,34.05),(-6.2,35.2),(-5.92,35.79)]
EU = [(-5.35,36.15),(-6.3,36.5),(-7.4,37.2),(-8.9,37),(-8.8,38.5),(-9.5,38.8),(-8.9,40.2),(-8.7,41.8),(-9.3,42.9),(-8.3,43.5),(-5.8,43.6),(-3.0,43.4),(-1.6,43.4),(-1.2,46),(-2.2,47.2),(-4.5,47.9),(-4.7,48.4),(-3,48.8),(-1.5,48.7),(-1.9,49.7),(0.2,49.5),(1.6,50.9),(2.5,51.1),(4,51.4),(8,53.6),(9,57),(10.5,57.7),(12,55),(15,54),(40,54),(40,41),(28,41),(23,40),(20,39.5),(18.5,40.2),(16,38),(15.6,38),(12.5,41.8),(10,44.1),(8,43.9),(4,43.4),(3.2,41.9),(0.2,40.2),(-0.4,39.4),(0.2,38.7),(-0.8,37.6),(-2.1,36.7),(-4.4,36.7),(-5.35,36.15)]
GB = [(-5.7,50.1),(-3,50.6),(1.4,51.2),(1.7,52.7),(0.2,53.5),(-0.4,54.5),(-1.6,55.6),(-2,57),(-4,57.6),(-3,58.6),(-5,58.6),(-6.2,56.5),(-5,55),(-3.4,54.3),(-3,53.4),(-4.6,53.3),(-4.2,52.3),(-5.2,51.8),(-3.3,51.4),(-4.2,51.2),(-5.7,50.1)]
IE = [(-6,52.2),(-6.2,53.8),(-5.6,54.6),(-7,55.3),(-8.3,55.2),(-10,54.2),(-9.9,53.4),(-10.3,52),(-9.6,51.5),(-8,51.7)]
IS = [(-22,63.9),(-14,64.3),(-13.5,65.5),(-16,66.5),(-22,66.4),(-24,65.5)]
GL = [(-44,59.8),(-50,62),(-53,66),(-55,70),(-30,70),(-22,68),(-35,65.5),(-42,61)]
CAN = [(-15.6,28.0),(-17.9,28.3),(-13.6,29.0),(-14.0,28.4),(-16.6,28.3)]
POLYS = [NA, NF, CUBA, HISP, AF, EU, GB, IE, IS, GL]
PORTS = [("طنجة", -5.81, 35.77, -22), ("العرائش", -6.15, 35.19, 18), ("سلا", -6.80, 34.05, 0), ("الصويرة", -9.77, 31.51, 0)]
K = math.cos(math.radians(35))
MAP_TOP, MAP_BOT = 150, 1380
PAPER = None

def bez(p0, p1, p2, s):
    return ((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0], (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1])

def ship_icon(sz=120):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = sz / 120
    d.polygon([(10*s, 80*s), (110*s, 80*s), (95*s, 102*s), (25*s, 102*s)], fill=(90, 55, 30), outline=(40, 20, 10))
    for mx, top, wdt in ((40, 18, 26), (66, 8, 30), (90, 28, 20)):
        d.line((mx*s, 80*s, mx*s, top*s), fill=(60, 35, 20), width=int(4*s))
        d.polygon([(mx*s, (top+6)*s), ((mx+wdt)*s, (top+20)*s), (mx*s, (top+45)*s)], fill=(250, 244, 228), outline=(120, 100, 80))
        d.polygon([(mx*s, (top+6)*s), ((mx-wdt*0.8)*s, (top+22)*s), (mx*s, (top+42)*s)], fill=(235, 226, 205), outline=(120, 100, 80))
    # tiny flag
    d.rectangle((66*s, 0, 84*s, 10*s), fill=(178, 34, 52)); d.rectangle((66*s, 0, 72*s, 5*s), fill=(40, 52, 110))
    return im
SHIP = None

def sc_map(img, t, T, dur):
    vw, vh = W, MAP_BOT - MAP_TOP
    z = ease_in_out(prog(t, 4.6, 7.2))
    clon = lerp(-40, -7.2, z); clat = lerp(37.5, 33.3, z)
    span = lerp(78, 11, z)  # lon span visible
    sc = vw / (span * K)
    def P(lon, lat): return (vw / 2 + (lon - clon) * K * sc, vh / 2 - (lat - clat) * sc)
    m = PAPER.copy()
    d = ImageDraw.Draw(m)
    # grid
    for lo in range(-100, 41, 10 if span > 30 else 2):
        x = P(lo, 0)[0]; d.line((x, 0, x, vh), fill=(255, 255, 255, 22), width=1)
    for la in range(0, 80, 10 if span > 30 else 2):
        y = P(0, la)[1]; d.line((0, y, vw, y), fill=(255, 255, 255, 22), width=1)
    for poly in POLYS:
        pts = [P(*p) for p in poly]
        d.polygon(pts, fill=(222, 202, 160), outline=(120, 90, 50))
        d.line(pts + [pts[0]], fill=(120, 90, 50), width=3)
    for (lo, la) in CAN:
        x, y = P(lo, la); r = max(3, 0.25 * sc); d.ellipse((x - r, y - r, x + r, y + r), fill=(222, 202, 160), outline=(120, 90, 50))
    # Morocco highlight
    ma_alpha = prog(t, 5.5, 6.5)
    # labels
    ov = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    la1 = 1 - z
    if la1 > 0.05:
        x, y = P(-92, 40); paste(ov, text_img("أمريكا", 54, (70, 45, 20), shadow=False), x, y, la1)
        x, y = P(-42, 30); paste(ov, text_img("المحيط الأطلسي", 50, (220, 235, 245), shadow=False), x, y, la1 * 0.9)
        x, y = P(5, 22); paste(ov, text_img("إفريقيا", 46, (70, 45, 20), shadow=False), x, y, la1 * 0.8)
    # path
    p0, p1, p2 = (-71, 39.5), (-40, 47), (-7.2, 34.6)
    s_end = ease_in_out(prog(t, 0.6, 4.6))
    od = ImageDraw.Draw(ov)
    N = 80
    for i in range(int(N * s_end)):
        if i % 2: continue
        a_ = P(*bez(p0, p1, p2, i / N)); b_ = P(*bez(p0, p1, p2, (i + 1) / N))
        od.line((a_, b_), fill=(193, 39, 45, 230), width=6)
    # origin dot
    x, y = P(*p0); od.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(193, 39, 45))
    # ports
    for i, (nm, lo, la, dy) in enumerate(PORTS):
        t0 = 6.0 + i * 0.45
        pp = ease_back(prog(t, t0, t0 + 0.35))
        if pp <= 0: continue
        x, y = P(lo, la)
        r = 16 * pp
        od.ellipse((x - r - 8, y - r - 8, x + r + 8, y + r + 8), fill=(193, 39, 45, 70))
        od.ellipse((x - r, y - r, x + r, y + r), fill=RED, outline=(255, 255, 255), width=4)
        lbl = text_img(nm, 50, (35, 20, 10), shadow=False)
        paste(ov, lbl, x + lbl.width / 2 + 4, y + dy, pp)
    if ma_alpha > 0:
        x, y = P(-5.2, 32.0); paste(ov, text_img("المغرب", 80, (130, 20, 25), shadow=False), x, y, ma_alpha)
    # ship
    if t < 6.0:
        sp = bez(p0, p1, p2, s_end); sp2 = bez(p0, p1, p2, min(1, s_end + 0.01))
        x, y = P(*sp)
        bob = 5 * math.sin(T * 4)
        flip = sp2[0] >= sp[0]
        sh = SHIP if flip else SHIP.transpose(Image.FLIP_LEFT_RIGHT)
        paste(ov, sh, x, y - 40 + bob, alpha=1 - prog(t, 5.4, 6.0), scale=lerp(1.0, 1.3, z), rot=4 * math.sin(T * 3))
    m.alpha_composite(ov)
    # feather edges
    mask = MAPMASK
    card = Image.new("RGBA", (vw, vh)); card.paste(m, (0, 0)); card.putalpha(mask)
    a = prog(t, 0, 0.3)
    paste(img, card, W / 2, MAP_TOP + vh / 2, alpha=a)

MAPMASK = None
def make_paper():
    global PAPER, MAPMASK
    vw, vh = W, MAP_BOT - MAP_TOP
    rng = np.random.default_rng(3)
    n = rng.normal(0, 1, (vh // 8 + 1, vw // 8 + 1)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n + 3) * 40).clip(0, 255).astype(np.uint8)).resize((vw, vh), Image.BICUBIC), np.float32) / 255
    base = np.array([38, 82, 110], np.float32)
    arr = base[None, None, :] * (0.85 + 0.3 * n[..., None])
    PAPER = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    yy, xx = np.mgrid[0:vh, 0:vw].astype(np.float32)
    e = np.minimum.reduce([xx, vw - xx, yy, vh - yy])
    MAPMASK = Image.fromarray((np.clip(e / 120, 0, 1) ** 1.5 * 255).astype(np.uint8))

# ---------------- treaty ----------------
def sc_treaty(img, t, T):
    pw, ph_full = 820, 1000
    u = ease_out(prog(t, 0.1, 0.9))
    ph = int(120 + (ph_full - 120) * u)
    par = Image.new("RGBA", (pw, ph_full), (0, 0, 0, 0)); d = ImageDraw.Draw(par)
    d.rectangle((0, 0, pw, ph_full), fill=(236, 220, 182))
    # stains
    rr = random.Random(5)
    for _ in range(14):
        x, y, r = rr.uniform(0, pw), rr.uniform(0, ph_full), rr.uniform(40, 160)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(214, 190, 140))
    par = par.filter(ImageFilter.GaussianBlur(25))
    d = ImageDraw.Draw(par)
    d.rectangle((20, 20, pw - 20, ph_full - 20), outline=(150, 110, 60), width=4)
    d.rectangle((34, 34, pw - 34, ph_full - 34), outline=(150, 110, 60), width=2)
    d.text((pw / 2, 120), "معاهدة السلام والصداقة", font=font(64), anchor="mm", fill=INK)
    d.text((pw / 2, 200), "مراكش • 1786", font=font(44, FR), anchor="mm", fill=(120, 80, 40))
    d.line((180, 250, pw - 180, 250), fill=(150, 110, 60), width=3)
    # writing lines RTL
    wp = prog(t, 0.8, 3.6)
    nl = 9
    for i in range(nl):
        lp = clamp(wp * nl - i)
        if lp <= 0: break
        y = 310 + i * 52
        x0 = pw - 90; x1 = 90 if i < nl - 1 else 380
        xe = lerp(x0, x1, lp)
        pts = []
        x = x0
        while x > xe:
            pts.append((x, y + 7 * math.sin(x * 0.11 + i) + 4 * math.sin(x * 0.37 + i * 2)))
            x -= 6
        if len(pts) > 1: d.line(pts, fill=(70, 45, 25), width=4)
    # signatures
    sp = prog(t, 3.6, 4.4)
    if sp > 0:
        for sx, sgn in ((220, 1), (600, -1)):
            pts = [(sx - 120 + k * 4 * sp, 860 + 20 * math.sin(k * 0.35 * sgn) * math.cos(k * 0.08)) for k in range(int(60 * sp) + 1)]
            if len(pts) > 1: d.line(pts, fill=(40, 30, 80), width=4)
    crop = par.crop((0, (ph_full - ph) // 2, pw, (ph_full - ph) // 2 + ph))
    paste(img, crop, W / 2, 780)
    # rollers
    for yy in (780 - ph / 2, 780 + ph / 2):
        r = Image.new("RGBA", (900, 60), (0, 0, 0, 0)); rd = ImageDraw.Draw(r)
        rd.rounded_rectangle((0, 0, 899, 59), 30, fill=(150, 95, 45), outline=(80, 45, 15), width=4)
        rd.rectangle((40, 18, 860, 26), fill=(190, 130, 70))
        paste(img, r, W / 2, yy)
    # seal
    sp2 = prog(t, 4.6, 4.9)
    if sp2 > 0:
        sz = 230
        s = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); sd = ImageDraw.Draw(s)
        sd.ellipse((8, 8, sz - 8, sz - 8), fill=(150, 20, 25))
        sd.ellipse((30, 30, sz - 30, sz - 30), outline=(110, 10, 15), width=6)
        sd.polygon(star_points(sz / 2, sz / 2, 62, math.pi / 8), outline=(215, 120, 110), width=5)
        sc = lerp(2.2, 1.0, ease_out(sp2))
        shake = (1 - prog(t, 4.9, 5.2)) * 10 * math.sin(T * 80) if t > 4.9 else 0
        paste(img, s, W / 2 + 230 + shake, 1130, alpha=sp2, scale=sc, rot=-12)

# ---------------- counter ----------------
def sc_counter(img, t, T):
    t = t - 0.7
    cp = ease_in_out(prog(t, 0.4, 3.4))
    yr = int(round(lerp(1786, 2026, cp)))
    s = 1 + 0.04 * math.sin(t * 20) * (1 - prog(t, 3.3, 3.5)) if cp < 1 else 1
    put_text(img, str(yr), W / 2, 560, 220, GOLD2 if cp >= 1 else CREAM, scale=s, path=FS, alpha=prog(t, -0.7, -0.4))
    # timeline
    d = ImageDraw.Draw(img)
    x0, x1, y = 140, 940, 800
    d.rounded_rectangle((x0, y - 10, x1, y + 10), 10, fill=(255, 255, 255, 40))
    d.rounded_rectangle((x0, y - 10, x0 + (x1 - x0) * cp + 1, y + 10), 10, fill=GOLD)
    put_text(img, "1786", x0, y + 70, 40, CREAM, path=FR)
    put_text(img, "2026", x1, y + 70, 40, CREAM, path=FR, alpha=prog(t, 3.0, 3.4))
    # chain links unbroken
    for i in range(7):
        lx = x0 + 60 + i * 115
        lp = prog(t, 0.4 + i * 0.4, 0.6 + i * 0.4)
        if lp <= 0: continue
        if i % 2 == 0:
            d.rounded_rectangle((lx - 48, 950 - 26, lx + 48, 950 + 26), 26, outline=GOLD + (int(255 * lp),), width=12)
        else:
            d.rounded_rectangle((lx - 48, 950 - 12, lx + 48, 950 + 12), 12, outline=(200, 160, 80, int(255 * lp)), width=12)
    st = prog(t, 3.5, 3.8)
    if st > 0:
        stamp = Image.new("RGBA", (680, 220), (0, 0, 0, 0)); sd = ImageDraw.Draw(stamp)
        sd.rounded_rectangle((6, 6, 674, 214), 24, outline=(230, 70, 60), width=10)
        sd.text((340, 112), "240 عام", font=font(120), anchor="mm", fill=(230, 70, 60))
        paste(img, stamp, W / 2, 1200, alpha=st, scale=lerp(2.0, 1.0, ease_out(st)), rot=-6)

# ---------------- legation ----------------
def building(T):
    bw, bh = 900, 900
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    # main body
    d.rectangle((90, 260, 810, 880), fill=(244, 238, 226), outline=(180, 170, 150), width=3)
    d.rectangle((90, 860, 810, 880), fill=(200, 190, 170))
    # crenellations
    for x in range(90, 810, 60):
        d.rectangle((x, 230, x + 34, 262), fill=(244, 238, 226))
    # tile band
    d.rectangle((90, 262, 810, 300), fill=(20, 110, 80))
    for x in range(90, 810, 30):
        d.polygon([(x, 300), (x + 15, 284), (x + 30, 300)], fill=(14, 80, 58))
    # door: horseshoe arch
    cx = 450
    d.rectangle((cx - 135, 560, cx + 135, 880), fill=(20, 110, 80))
    d.ellipse((cx - 155, 440, cx + 155, 700), fill=(20, 110, 80))
    d.rectangle((cx - 100, 600, cx + 100, 880), fill=(120, 60, 30))
    d.ellipse((cx - 115, 480, cx + 115, 700), fill=(120, 60, 30))
    for k in range(-80, 100, 40):
        d.line((cx + k, 600, cx + k, 880), fill=(90, 45, 20), width=4)
    for yy in range(640, 880, 50):
        for k in range(-80, 100, 40):
            d.ellipse((cx + k - 5, yy - 5, cx + k + 5, yy + 5), fill=(220, 180, 90))
    # windows w/ mashrabiya
    for wx in (210, 690):
        for wy in (380, 620):
            d.rectangle((wx - 60, wy - 70, wx + 60, wy + 70), fill=(110, 70, 40), outline=(20, 110, 80), width=8)
            for g in range(-50, 60, 20):
                d.line((wx + g, wy - 62, wx + g, wy + 62), fill=(70, 40, 20), width=4)
                d.line((wx - 52, wy + g, wx + 52, wy + g), fill=(70, 40, 20), width=4)
    # flagpole + flag
    d.line((780, 230, 780, 60), fill=(200, 200, 200), width=8)
    fl = wave(us_flag(170, 100), T, amp=6)
    im.alpha_composite(fl, (784, 60))
    return im

def palm(h=700):
    im = Image.new("RGBA", (500, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(250 + 30 * math.sin(i / 20), h - i * (h - 120) / 60) for i in range(61)]
    d.line(pts, fill=(25, 18, 30), width=26)
    tx, ty = pts[-1]
    for k in range(9):
        a = math.pi + k * math.pi / 8
        pts2 = [(tx + r * math.cos(a), ty + r * math.sin(a) * 0.7 + (r / 200) ** 2 * 60) for r in range(0, 220, 10)]
        d.line(pts2, fill=(25, 18, 30), width=18)
    return im
PALM = None

def sc_legation(img, t, T):
    # sunset sky panel
    sky_h = 1300
    yy = np.linspace(0, 1, sky_h)[:, None, None]
    c1 = np.array([30, 40, 90]); c2 = np.array([235, 130, 70]); c3 = np.array([250, 200, 120])
    col = np.where(yy < 0.6, c1 * (1 - yy / 0.6) + c2 * (yy / 0.6), c2 * (1 - (yy - 0.6) / 0.4) + c3 * ((yy - 0.6) / 0.4))
    sky = np.broadcast_to(col, (sky_h, W, 3)).astype(np.uint8)
    skyim = Image.fromarray(sky).convert("RGBA")
    sd = ImageDraw.Draw(skyim)
    sd.ellipse((W / 2 + 160 - 110, 820 - 110, W / 2 + 160 + 110, 820 + 110), fill=(255, 225, 160))
    zoom = lerp(1.0, 1.12, ease_in_out(prog(t, 0, 16)))
    b = building(T)
    paste(skyim, b, W / 2, 1300 - 450 * zoom + 10, scale=zoom * ease_out(prog(t, 0, 0.6)) if t < 0.6 else zoom)
    paste(skyim, PALM, 120, 1300 - 330, scale=1.0)
    paste(skyim, PALM.transpose(Image.FLIP_LEFT_RIGHT), 980, 1300 - 300, scale=0.9)
    d = ImageDraw.Draw(skyim); d.rectangle((0, 1270, W, 1300), fill=(30, 22, 30))
    yy2, xx2 = np.mgrid[0:sky_h, 0:W]
    e = np.minimum(np.minimum(yy2, sky_h - yy2), 9999).astype(np.float32)
    mask = (np.clip(e / 140, 0, 1) * 255).astype(np.uint8)
    skyim.putalpha(Image.fromarray(mask))
    img.alpha_composite(skyim, (0, 80))
    # labels
    put_text(img, "طنجة • 1821", W / 2, 260, 70, CREAM, alpha=prog(t, 0.3, 0.7), stroke=3)
    if t > 8.8:
        p = ease_back(prog(t, 8.8, 9.3))
        rib = Image.new("RGBA", (860, 120), (0, 0, 0, 0)); rd = ImageDraw.Draw(rib)
        rd.polygon([(0, 0), (860, 0), (830, 60), (860, 120), (0, 120), (30, 60)], fill=(150, 20, 25))
        rd.text((430, 60), "متحف اليوم", font=font(64), anchor="mm", fill=(255, 240, 220))
        paste(img, rib, W / 2, 380, scale=p, alpha=prog(t, 8.8, 9.0))

# ---------------- outro ----------------
def sc_outro(img, t, T):
    p = ease_back(prog(t, 0, 0.7))
    paste(img, EMB, W / 2, 560, scale=p * (1 + 0.015 * math.sin(T * 2)), rot=(1 - ease_out(prog(t, 0, 0.9))) * 40)
    paste(img, NAMEV, W / 2, 1010, alpha=prog(t, 0.5, 0.9), scale=lerp(0.9, 1.0, ease_out(prog(t, 0.5, 1.0))))
    bp = ease_back(prog(t, 1.2, 1.6))
    btn = Image.new("RGBA", (560, 140), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((0, 0, 559, 139), 70, fill=(204, 0, 0))
    bd.text((280, 70), "تابع  +", font=font(66), anchor="mm", fill=(255, 255, 255))
    paste(img, btn, W / 2, 1335, scale=bp * (1 + 0.04 * math.sin(T * 6)))

# ================= timeline =================
SCENES = [
    (4.0, sc_hook, [(0.0, "واش عرفتي شكون أول دولة فالعالم اعترفات بأمريكا؟", False)]),
    (3.9, sc_notthem, [(0.0, "ماشي فرنسا… ماشي إسبانيا… ماشي هولندا", False)]),
    (3.0, sc_reveal, [(0.3, "هو المغرب!", True)]),
    (7.4, sc_war, [(0.0, "أمريكا كانت باقا كتحارب بريطانيا على الاستقلال ديالها", False),
                   (3.95, "وبزاف ديال الدول كانت خايفة تغامر معاها", False)]),
    (8.0, sc_map, [(0.0, "السلطان سيدي محمد بن عبد الله قرر:", False),
                   (2.8, "أي سفينة هازة العلم الأمريكي…", False),
                   (5.3, "مرحبا بيها فالمراسي ديال المغرب", True)]),
    (6.3, sc_treaty, [(0.0, "وفـ 1786 تسنات فمراكش", False),
                      (2.2, "معاهدة السلام والصداقة بين الجوج", True)]),
    (8.2, sc_counter, [(0.0, "والمفاجأة؟ هاد المعاهدة باقا سارية حتى لليوم", False),
                       (4.3, "أقدم معاهدة عمرها ما تقطعات فتاريخ أمريكا", True)]),
    (16.3, sc_legation, [(0.0, "وفـ 1821 السلطان مولاي سليمان عطا لأمريكا دار فطنجة", False),
                         (5.6, "أول بلاصة كتملكها أمريكا برا أرضها", True),
                         (8.9, "اليوم ولات متحف: المفوضية الأمريكية فطنجة", False),
                         (13.1, "وباقا حتى لدابا شاهدة على هاد الصداقة", False)]),
    (4.5, sc_outro, [(0.1, "تبعنا باش تعرف الجزء الجاي من تاريخ المغرب", False)]),
]
TOTAL = sum(s[0] for s in SCENES)

def render_frame(si, t):
    dur, fn, caps = SCENES[si]
    T = sum(s[0] for s in SCENES[:si]) + t
    img = background(T)
    if fn is sc_map: fn(img, t, T, dur)
    else: fn(img, t, T)
    cur = None
    for c in caps:
        if t >= c[0]: cur = c
    if cur: caption(img, cur[1], cur[0], t, cur[2], y=1600 if fn is not sc_map else 1560)
    if fn is not sc_outro:
        paste(img, WM, 100, 112, alpha=0.9)
    # scene entry: quick zoom-settle + fade from dark
    e = prog(t, 0, 0.25)
    if e < 1:
        dark = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - e) * 0.85)))
        img.alpha_composite(dark)
    return finish(img, T, TOTAL)

def setup():
    global USF, MAF, SWORDS, SHIP, PALM
    init(); make_paper()
    global WM, EMB, NAMEV
    WM = Image.open(BRAND + 'logo_embleme_simple.png').resize((150, 150), Image.LANCZOS)
    EMB = Image.open(BRAND + 'logo_embleme.png').resize((620, 620), Image.LANCZOS)
    lv = Image.open(BRAND + 'logo_vertical_fond_sombre.png')
    top = int(lv.height * 0.535)
    NAMEV = lv.crop((0, top, lv.width, lv.height)); NAMEV = NAMEV.resize((860, int(NAMEV.height * 860 / NAMEV.width)), Image.LANCZOS)
    USF = us_flag(); MAF = ma_flag(); SWORDS = swords_icon(); SHIP = ship_icon(130); PALM = palm()

if __name__ == "__main__":
    setup()
    mode = sys.argv[1]
    if mode == "still":
        for spec in sys.argv[2:]:
            si, t = spec.split(":")
            render_frame(int(si), float(t)).save(f"{OUTDIR}/still_{si}_{t}.jpg", quality=90)
    elif mode == "scene":
        si = int(sys.argv[2])
        dur = SCENES[si][0]
        n = int(round(dur * FPS))
        tmp = f"{OUTDIR}/s{si:02d}.tmp.mp4"
        os.makedirs(OUTDIR, exist_ok=True)
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(render_frame(si, i / FPS).tobytes())
        p.stdin.close()
        if p.wait() == 0:
            os.rename(tmp, f"{OUTDIR}/s{si:02d}.mp4")
    elif mode == "total":
        print(TOTAL, [round(sum(s[0] for s in SCENES[:i]), 2) for i in range(len(SCENES) + 1)])
