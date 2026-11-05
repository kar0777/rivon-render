"""Polish captions, hook headline and RIVON end card for the 'Zestaw' video (PIL, resolution-independent).
overlay(img, frame) -> RGB image.  Text is real typography, never generated."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
POST = os.path.join(HERE, "..", "rivon_film", "post")
FD = os.path.join(POST, "fonts")
_m = Image.open(os.path.join(POST, "rivon_logo.png")).convert("L")
LOGO = _m.crop(_m.point(lambda v: 255 if v > 40 else 0).getbbox())
_ip = os.path.join(POST, "logo_icon.png")
ICON = Image.open(_ip).convert("L") if os.path.exists(_ip) else None

# frame ranges (30 fps) -> (title, subtitle)
CAPS = [
    (64, 118, "Równe, utwardzone podłoże", None),
    (124, 208, "Zestaw na pergolę", "4 słupy · 4 narożniki · 22 mocowania belek"),
    (214, 328, "Podstawa słupa RIVON", "Stopa – kotwiona do podłoża"),
    (334, 418, "Słup wchodzi w gniazdo", "i jest przykręcany przez otwory"),
    (424, 538, "Łącznik narożny RIVON", "Trojak 3D – 3 belki w jednym węźle"),
    (544, 628, "Rama górna", "opuszczana na słupy"),
    (634, 748, "Mocowanie belek RIVON", "krokwie osadzone w uchwytach"),
    (754, 818, "Dowolne pokrycie dachu", "Poliwęglan"),
    (824, 888, "Dowolne pokrycie dachu", "Blacha trapezowa"),
    (894, 958, "Dowolne pokrycie dachu", "Lamele drewniane"),
]
HOOK = (0, 60, ("Pergola z drewna?", "Złóż ją na łącznikach RIVON"))
END0 = 880


def font(name, px):
    return ImageFont.truetype(os.path.join(FD, name), int(px))


def fade(f, a, b, k=6):
    return max(0.0, min(1.0, (f - a) / k, (b - f) / k))


def _pill_text(base, cx, cy, lines, alpha, w):
    """lines: [(text, font, rgb)], drawn centred inside a translucent graphite pill."""
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sizes = [d.textbbox((0, 0), t, font=fn) for t, fn, _ in lines]
    gap = int(w * 0.012)
    tw = max(b[2] - b[0] for b in sizes); th = sum(b[3] - b[1] for b in sizes) + gap * (len(lines) - 1)
    px, py = int(w * 0.045), int(w * 0.03)
    x0, y0 = cx - tw / 2 - px, cy - th / 2 - py
    d.rounded_rectangle((x0, y0, cx + tw / 2 + px, cy + th / 2 + py), radius=int(w * 0.03), fill=(14, 15, 17, int(150 * alpha)))
    y = cy - th / 2
    for (t, fn, rgb), b in zip(lines, sizes):
        d.text((cx - (b[2] - b[0]) / 2 - b[0], y - b[1]), t, font=fn, fill=rgb + (int(255 * alpha),))
        y += (b[3] - b[1]) + gap
    return Image.alpha_composite(base, lay)


def _logo(base, cx, cy, width, alpha, color=(255, 255, 255)):
    lg = LOGO.resize((int(width), int(width * LOGO.height / LOGO.width)), Image.LANCZOS)
    lay = Image.new("RGBA", lg.size, color + (0,)); lay.putalpha(lg.point(lambda v: int(v * alpha)))
    base.alpha_composite(lay, (int(cx - lg.width / 2), int(cy - lg.height / 2)))


def _mask(base, m, cx, cy, width, alpha, color=(255, 255, 255)):
    mm = m.resize((int(width), int(width * m.height / m.width)), Image.LANCZOS)
    lay = Image.new("RGBA", mm.size, color + (0,)); lay.putalpha(mm.point(lambda v: int(v * alpha)))
    base.alpha_composite(lay, (int(cx - mm.width / 2), int(cy - mm.height / 2)))


def _film(base, f):
    """Photographic finish: gentle vignette + fine animated grain (no text)."""
    import numpy as np
    a = np.asarray(base.convert("RGB")).astype(np.float32) / 255.0
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]; r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    a = np.clip(lum + (a - lum) * 1.18, 0, 1)                 # +18 % saturation
    a *= (1 - 0.16 * np.clip(r - 0.35, 0, None) ** 1.6)[..., None]
    g = np.random.default_rng(f).normal(0, 0.006, (h, w, 1)).astype(np.float32)
    a = np.clip(a + g, 0, 1)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8)).convert("RGBA")


TEXT = False          # owner: no on-screen text except the end card


def overlay(img, f):
    base = _film(img, f); w, h = base.size
    if not TEXT and f < END0:
        return base.convert("RGB")
    # small brand mark (top-right), like the reference watermark
    if f < END0:
        _logo(base, w * 0.86, h * 0.055, w * 0.15, 0.85)
    a, b, (t1, t2) = HOOK
    al = fade(f, a - 10, b, 6) if TEXT else 0
    if al > 0:
        base = _pill_text(base, w / 2, h * 0.17,
                          [(t1, font("Jost.ttf", w * 0.078), (255, 255, 255)), (t2, font("Inter-Medium.otf", w * 0.05), (238, 206, 150))],
                          al, w)
    for a, b, t, s in (CAPS if TEXT else []):
        al = fade(f, a, b)
        if al > 0:
            ls = [(t, font("Jost.ttf", w * 0.058), (255, 255, 255))]
            if s:
                ls.append((s, font("Inter-Medium.otf", w * 0.036), (235, 235, 235)))
            base = _pill_text(base, w / 2, h * 0.80, ls, al, w)
    if f >= END0:
        t = f - END0
        e = lambda a, d=14: max(0.0, min(1.0, (t - a) / d))
        k = e(0, 18)
        base = Image.alpha_composite(base, Image.new("RGBA", base.size, (9, 10, 12, int(215 * k))))
        # brand: icon + wordmark, gentle rise-in
        if ICON is not None:
            _mask(base, ICON, w / 2, h * 0.30 + (1 - e(6)) * h * 0.015, w * 0.20, e(6))
        _logo(base, w / 2, h * 0.405 + (1 - e(10)) * h * 0.015, w * 0.64, e(10))
        d = ImageDraw.Draw(base)
        def ctext(txt, fn, col, y, al):
            if al <= 0: return
            bb = d.textbbox((0, 0), txt, font=fn)
            d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], y - (bb[3] - bb[1]) / 2 - bb[1]), txt, font=fn, fill=col + (int(255 * al),))
        ctext("Łączniki do konstrukcji drewnianych", font("Inter-Light.otf", w * 0.042), (225, 225, 225), h * 0.475, e(18))
        ctext("Zbuduj własną pergolę", font("Jost.ttf", w * 0.072), (255, 255, 255), h * 0.585, e(30))
        # call-to-action button
        al = e(40)
        if al > 0:
            fn = font("Jost.ttf", w * 0.056); txt = "Zapytaj o zestaw"
            bb = d.textbbox((0, 0), txt, font=fn); bw, bh = bb[2] - bb[0], bb[3] - bb[1]
            px, py = w * 0.07, w * 0.035; cy = h * 0.675 + (1 - al) * h * 0.01
            lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            dl.rounded_rectangle((w / 2 - bw / 2 - px, cy - bh / 2 - py, w / 2 + bw / 2 + px, cy + bh / 2 + py), radius=int(bh / 2 + py),
                                 fill=(222, 178, 104, int(255 * al)))
            dl.text((w / 2 - bw / 2 - bb[0], cy - bh / 2 - bb[1]), txt, font=fn, fill=(18, 18, 20, int(255 * al)))
            base = Image.alpha_composite(base, lay); d = ImageDraw.Draw(base)
        ctext("Napisz do nas na Facebooku lub Instagramie", font("Inter-Light.otf", w * 0.034), (200, 200, 200), h * 0.745, e(50))
    return base.convert("RGB")
