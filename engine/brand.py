import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

OUT = "/home/claude/vid/brand/"
TIF = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TIFB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"
ARB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
INTER = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
RAQM = ImageFont.Layout.RAQM

NAVY = (11, 22, 48); INK = (5, 10, 24); GOLD = (233, 189, 92); GOLD2 = (255, 222, 140)
SAND = (246, 236, 214); RED = (193, 39, 45); GREEN = (14, 110, 80)
NAME_TIF = "ⴰⵎⵣⵔⵓⵢ ⵏ ⵓⵎⴰⴹⴰⵍ"
NAME_LAT = "AMZRUY N UMADAL"
TAG_AR = "تاريخنا بالدارجة"

def F(p, s): return ImageFont.truetype(p, s, layout_engine=RAQM)

def star(cx, cy, r, rot=0.0, k=8, inner=0.70):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(rot + i * math.pi / k),
             cy + (r if i % 2 == 0 else r * inner) * math.sin(rot + i * math.pi / k)) for i in range(2 * k)]

def gold_gradient(mask):
    """apply vertical gold gradient through an L mask"""
    w, h = mask.size
    y = np.linspace(0, 1, h)[:, None]
    top = np.array(GOLD2, np.float32); bot = np.array((196, 146, 58), np.float32)
    col = top * (1 - y[..., None]) + bot * y[..., None]
    col = np.broadcast_to(col, (h, w, 3)).astype(np.uint8)
    im = Image.fromarray(col).convert("RGBA"); im.putalpha(mask)
    return im

def emblem(S=1200, ring_text=True, bg=True):
    """v2: astrolabe-globe. ring_text=True -> detailed (fine ticks), False -> simplified for small sizes"""
    SS = S * 2; c = SS / 2
    base = Image.new("RGBA", (SS, SS), (0, 0, 0, 0)); d = ImageDraw.Draw(base)
    R = SS * 0.40           # outer ring radius
    cy = c + SS * 0.045     # disc centre (room for suspension ring on top)
    if bg:
        d.ellipse((c - R, cy - R, c + R, cy + R), fill=NAVY + (255,))
        g = Image.new("L", (SS, SS), 0); gd = ImageDraw.Draw(g)
        gd.ellipse((c - R * 0.7, cy - R * 0.95, c + R * 0.7, cy + R * 0.2), fill=60)
        g = g.filter(ImageFilter.GaussianBlur(SS * 0.05))
        circ = Image.new("L", (SS, SS), 0); ImageDraw.Draw(circ).ellipse((c - R, cy - R, c + R, cy + R), fill=255)
        light = Image.new("RGBA", (SS, SS), (60, 95, 170, 0))
        light.putalpha(Image.fromarray(np.minimum(np.asarray(g), np.asarray(circ))))
        base.alpha_composite(light)
    m = Image.new("L", (SS, SS), 0); md = ImageDraw.Draw(m)
    lw = SS * 0.011
    # suspension: throne + shackle ring
    tw = R * 0.22; th = R * 0.16
    md.polygon([(c - tw, cy - R + lw), (c + tw, cy - R + lw), (c + tw * 0.55, cy - R - th), (c - tw * 0.55, cy - R - th)], fill=255)
    rr = R * 0.10
    md.ellipse((c - rr, cy - R - th - rr * 1.7, c + rr, cy - R - th + rr * 0.3), outline=255, width=int(lw * 1.1))
    # limb: outer & inner circles
    md.ellipse((c - R, cy - R, c + R, cy + R), outline=255, width=int(lw * 1.8))
    r_in = R * (0.84 if ring_text else 0.86)
    md.ellipse((c - r_in, cy - r_in, c + r_in, cy + r_in), outline=255, width=int(lw * 0.9))
    # ticks
    n = 72 if ring_text else 24
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        major = (i % (n // 12) == 0)
        L = (R - r_in) * (0.75 if major else 0.38)
        x1, y1 = c + (R - lw * 1.2) * math.cos(a), cy + (R - lw * 1.2) * math.sin(a)
        x2, y2 = c + (R - lw * 1.2 - L) * math.cos(a), cy + (R - lw * 1.2 - L) * math.sin(a)
        md.line((x1, y1, x2, y2), fill=255, width=int(lw * (0.9 if major else 0.55)))
    # four small diamonds at cardinal points just inside the limb
    for k in range(4):
        a = -math.pi / 2 + k * math.pi / 2
        x, y = c + r_in * 0.93 * math.cos(a), cy + r_in * 0.93 * math.sin(a)
        s = SS * 0.014
        md.polygon([(x, y - s), (x + s * 0.6, y), (x, y + s), (x - s * 0.6, y)], fill=255)
    # globe (tilted 23.5 deg) drawn on its own layer then rotated
    gR = r_in * 0.72
    G = Image.new("L", (SS, SS), 0); gd = ImageDraw.Draw(G)
    w1 = int(lw * 1.1); w2 = int(lw * 0.7)
    gd.ellipse((c - gR, cy - gR, c + gR, cy + gR), outline=255, width=w1)
    for f in (0.0, 0.42, 0.78):
        if f == 0: gd.line((c, cy - gR, c, cy + gR), fill=255, width=w2)
        else: gd.ellipse((c - gR * f, cy - gR, c + gR * f, cy + gR), outline=255, width=w2)
    for lat in (-0.5, 0.0, 0.5):
        y = cy + gR * lat
        half = gR * math.sqrt(1 - lat * lat)
        bulge = gR * 0.10 * (1 - abs(lat))
        if lat == 0:
            gd.line((c - gR, y, c + gR, y), fill=255, width=w2)
        else:
            gd.arc((c - half, y - bulge, c + half, y + bulge), 0, 180, fill=255, width=w2)
    G = G.rotate(23.5, center=(c, cy), resample=Image.BICUBIC)
    m = Image.fromarray(np.maximum(np.asarray(m), np.asarray(G)))
    md = ImageDraw.Draw(m)
    # alidade (sighting rule) across the disc
    a = math.radians(-35)
    L = r_in * 0.98
    p1 = (c + L * math.cos(a), cy + L * math.sin(a)); p2 = (c - L * math.cos(a), cy - L * math.sin(a))
    nx, ny = -math.sin(a), math.cos(a); wv = SS * 0.012
    md.polygon([(p1[0] + nx * wv * 0.2, p1[1] + ny * wv * 0.2), (c + nx * wv, cy + ny * wv), (p2[0] + nx * wv * 0.2, p2[1] + ny * wv * 0.2),
                (p2[0] - nx * wv * 0.2, p2[1] - ny * wv * 0.2), (c - nx * wv, cy - ny * wv), (p1[0] - nx * wv * 0.2, p1[1] - ny * wv * 0.2)], fill=255)
    pr = SS * 0.022
    md.ellipse((c - pr, cy - pr, c + pr, cy + pr), fill=255)
    # small star (pole star) pointer near top-right of globe
    gl = gold_gradient(m)
    sh = Image.new("RGBA", (SS, SS), (0, 0, 0, 0)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(SS * 0.006)).point(lambda v: int(v * 0.6)))
    if bg: base.alpha_composite(sh, (0, int(SS * 0.004)))
    base.alpha_composite(gl)
    # punch pivot hole in navy
    if bg:
        ImageDraw.Draw(base).ellipse((c - pr * 0.4, cy - pr * 0.4, c + pr * 0.4, cy + pr * 0.4), fill=NAVY + (255,))
    out = base.resize((S, S), Image.LANCZOS)
    return out.crop(out.getbbox()).resize((S, S), Image.LANCZOS) if False else out

def text_layer(txt, path, size, fill, spacing=0, rtl=False):
    f = F(path, size)
    if spacing:
        widths = [f.getlength(ch) for ch in txt]
        W = int(sum(widths) + spacing * (len(txt) - 1) + 20)
        l, t, r, b = f.getbbox(txt)
        im = Image.new("RGBA", (W, b - t + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        x = 10
        for ch, w in zip(txt, widths):
            d.text((x, 10 - t), ch, font=f, fill=fill); x += w + spacing
        return im
    l, t, r, b = f.getbbox(txt)
    im = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - l, 10 - t), txt, font=f, fill=fill)
    return im

def gold_text(txt, path, size, spacing=0):
    t = text_layer(txt, path, size, (255, 255, 255, 255), spacing)
    return gold_gradient(t.getchannel("A"))

def logo_horizontal(dark_text=False):
    W, H = 3200, 1000
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    em = emblem(900)
    im.alpha_composite(em, (50, 50))
    x0 = 1050
    t1 = gold_text(NAME_TIF, TIF, 210, spacing=10)
    im.alpha_composite(t1, (x0, 160))
    col = INK + (255,) if dark_text else SAND + (255,)
    t2 = text_layer(NAME_LAT, SERIF, 150, col, spacing=26)
    im.alpha_composite(t2, (x0, 470))
    # divider
    d = ImageDraw.Draw(im)
    d.line((x0 + 10, 700, x0 + 330, 700), fill=GOLD + (255,), width=6)
    d.polygon(star(x0 + 380, 700, 18, math.pi / 8, 8, 0.7), fill=GOLD + (255,))
    d.line((x0 + 430, 700, x0 + 750, 700), fill=GOLD + (255,), width=6)
    t3 = text_layer(TAG_AR, ARB, 96, (RED + (255,)) if dark_text else (GOLD + (255,)))
    im.alpha_composite(t3, (x0 + 790, 640))
    return im.crop(im.getbbox())

def logo_vertical(dark_text=False):
    W, H = 2000, 2300
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    em = emblem(1150)
    im.alpha_composite(em, ((W - 1150) // 2, 40))
    t1 = gold_text(NAME_TIF, TIF, 170, spacing=8)
    im.alpha_composite(t1, ((W - t1.width) // 2, 1260))
    col = INK + (255,) if dark_text else SAND + (255,)
    t2 = text_layer(NAME_LAT, SERIF, 118, col, spacing=22)
    im.alpha_composite(t2, ((W - t2.width) // 2, 1530))
    t3 = text_layer(TAG_AR, ARB, 92, (RED + (255,)) if dark_text else (GOLD + (255,)))
    im.alpha_composite(t3, ((W - t3.width) // 2, 1760))
    return im.crop(im.getbbox())

def pattern_bg(W, H):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt(((x - W * 0.5) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    c1 = np.array([22, 40, 78], np.float32); c2 = np.array(INK, np.float32)
    mm = np.clip(dd / 0.7, 0, 1)[..., None]
    img = Image.fromarray((c1 * (1 - mm) + c2 * mm).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # world-map graticule: curved meridians + parallels
    cxg, cyg = W / 2, H / 2
    span = max(W, H) * 0.9
    for k in range(-9, 10):
        f = k / 9
        pts = [(cxg + f * span * math.cos(t * 0.9), cyg + span * 0.5 * math.sin(t * 0.9) * 1.2) for t in np.linspace(-math.pi / 2, math.pi / 2, 60)]
        d.line(pts, fill=GOLD + (22,), width=max(1, W // 900))
    for k in range(-6, 7):
        y = cyg + k * span * 0.09
        d.line((0, y, W, y), fill=GOLD + (16,), width=max(1, W // 900))
    img.alpha_composite(lay)
    return img

if __name__ == "__main__":
    em = emblem(2000); em.save(OUT + "logo_embleme.png")
    emblem(2000, ring_text=False).save(OUT + "logo_embleme_simple.png")
    lh = logo_horizontal(); lh.save(OUT + "logo_horizontal_fond_sombre.png")
    logo_horizontal(True).save(OUT + "logo_horizontal_fond_clair.png")
    lv = logo_vertical(); lv.save(OUT + "logo_vertical_fond_sombre.png")
    logo_vertical(True).save(OUT + "logo_vertical_fond_clair.png")
    # avatar 800 (simplified emblem reads better small)
    av = pattern_bg(800, 800); av.alpha_composite(emblem(780, ring_text=True), (10, 10)); av.convert("RGB").save(OUT + "photo_profil_800.png")
    # watermark 150 + transparent overlay for videos
    wm = emblem(150, ring_text=False); wm.save(OUT + "filigrane_youtube_150.png")
    ov = emblem(300, ring_text=False); a = np.asarray(ov).copy(); a[..., 3] = (a[..., 3] * 0.85).astype(np.uint8); Image.fromarray(a).save(OUT + "filigrane_video_300.png")
    # YouTube banner 2560x1440, safe area 1546x423 centered
    bn = pattern_bg(2560, 1440)
    hh = min(400, int(1500 * lh.height / lh.width)); lhs = lh.resize((int(lh.width * hh / lh.height), hh), Image.LANCZOS)
    bn.alpha_composite(lhs, ((2560 - lhs.width) // 2, (1440 - lhs.height) // 2))
    bn.convert("RGB").save(OUT + "banniere_youtube_2560x1440.png")
    # Instagram/TikTok/FB cover square post
    print("ok")
