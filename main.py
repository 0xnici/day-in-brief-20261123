#!/usr/bin/env python3
"""Entry program for make.fun news-image-20261123.

Draws a one-page newspaper front page (1024x1024) summing up the world
news of Monday 23 November 2026, and writes it to /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png).

Pillow only, no network, fully deterministic: the same bytes on every run.
Fonts come from Pillow's own bundled default font (ImageFont.load_default),
so the program renders identically in any container that has Pillow.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (247, 243, 232)
INK = (26, 26, 26)
RED = (155, 27, 27)
BLUE = (46, 74, 98)
GREY = (107, 101, 88)
LIGHT_GREY = (200, 194, 178)
SEA = (58, 96, 128)
SAND = (214, 196, 150)

# ---------------------------------------------------------------- stories
# (kicker, headline, place, utc time) — 30 stories, checked against live
# reporting on 23 Nov 2026 (Reuters, AP, CNN, UKMTO, Axios, BBC).
STORIES = [
    ("CLIMATE", "COP31 collapses with no deal", "Antalya, Turkiye", "02:15"),
    ("WAR IN UKRAINE", "Drone hits flats near Kyiv; 2 dead, 14 missing", "Dymer, Ukraine", "04:40"),
    ("COURTS", "ICJ: Myanmar committed genocide of Rohingya", "The Hague, Netherlands", "10:05"),    ("ENERGY", "Russian cargo ship Sparta II still burning", "Gulf of Finland", "06:20"),
    ("MIDDLE EAST", "Settler arson is \u2018Jewish terrorism\u2019, says Eisenkot", "West Bank", "12:30"),
    ("GULF", "Tanker set ablaze in Strait of Hormuz", "Strait of Hormuz", "08:50"),
    ("ASIA", "Factory fire in Indonesia: 24 dead, 50 missing", "Indonesia", "09:15"),
    ("CLIMATE", "EU, UK and Panama reject final COP31 draft", "Antalya, Turkiye", "01:40"),
    ("WAR IN UKRAINE", "Russia hits energy sites overnight", "Ukraine", "03:55"),
    ("ENERGY", "Blast hits Russian corvette in Benghazi port", "Benghazi, Libya", "07:10"),
    ("MIDDLE EAST", "Settlers burn 12 cars in four West Bank villages", "Ramallah, West Bank", "11:45"),
    ("GULF", "Iran attack injures two in Bahrain", "Manama, Bahrain", "13:05"),
    ("ASIA", "Nepal PM in Delhi for talks with Modi", "New Delhi, India", "10:30"),
    ("WAR IN UKRAINE", "Finland: Ukraine likely behind ship drone strike", "Helsinki, Finland", "14:20"),
    ("MIDDLE EAST", "Netanyahu-Eisenkot coalition talks end in deadlock", "Jerusalem", "16:40"),
    ("GULF", "Saudi-led coalition intercepts Houthi missile", "Riyadh, Saudi Arabia", "15:15"),
    ("ASIA", "South Korea minister quits in AI exam scandal", "Seoul, South Korea", "08:05"),
    ("TECH", "Nvidia chips \u2018diverted to China\u2019 in secret network", "Washington, US", "17:30"),
    ("SPORT", "India post record 720/9 in Wellington Test", "Wellington, New Zealand", "06:45"),
    ("WORLD", "UN to keep talking on lethal AI weapons", "Geneva, Switzerland", "12:10"),
    ("AMERICAS", "Brazil Congress to vote on fiscal plan", "Brasilia, Brazil", "18:20"),
    ("AMERICAS", "Bolsonaro \u2018stable\u2019 in intensive care", "Brasilia, Brazil", "09:40"),
    ("AMERICAS", "Trump hits out at Schumer in Senate row", "Washington, US", "19:05"),
    ("TECH", "Waymo pulls driverless taxis off US freeways", "California, US", "20:15"),
    ("EUROPE", "Thousands march in Lisbon over cost of living", "Lisbon, Portugal", "16:00"),
    ("ASIA", "Myanmar calls ASEAN decision \u2018unfair\u2019", "Naypyidaw, Myanmar", "13:45"),
    ("ASIA", "Kim: North Korea seeks security, not supremacy", "Pyongyang, North Korea", "07:50"),
    ("AFRICA", "24 civilians killed in South Sudan; vote delayed", "Juba, South Sudan", "11:00"),
    ("AFRICA", "Drone hits home and UN building in Khartoum", "Khartoum, Sudan", "14:55"),
    ("WORLD", "Trump, Xi and Putin to meet at APEC sidelines", "Shenzhen, China", "21:30"),
]

# ------------------------------------------------------------------- fonts
_cache = {}


def font(size):
    if size not in _cache:
        _cache[size] = ImageFont.load_default(size=size)
    return _cache[size]


def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def wrap(draw, s, f, max_w, max_lines=2):
    """Wrap s to at most max_lines lines of pixel width <= max_w."""
    words = s.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines - 1 and len(words) > 0:
                # last line: keep appending only while it fits
                pass
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    # Trim the last line so it fits, with an ellipsis if text was cut.
    total = " ".join(lines)
    if total != s:
        while lines and draw.textlength(lines[-1] + "\u2026", font=f) > max_w:
            lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
        if lines:
            lines[-1] += "\u2026"
    return lines


def centre(draw, y, s, f, fill=INK, x0=0, x1=W, stroke=0):
    w = draw.textlength(s, font=f)
    draw.text(((x0 + x1 - w) / 2, y), s, font=f, fill=fill,
              stroke_width=stroke, stroke_fill=fill)


def rule(draw, y, x0=24, x1=1000, fill=INK, width=1):
    draw.line([(x0, y), (x1, y)], fill=fill, width=width)


# --------------------------------------------------------------------- map
# Rough continent outlines as (lon, lat) points; projected equirectangular
# into the map strip. Deliberately simplified — a newspaper locator map.
MAP_X0, MAP_Y0, MAP_X1, MAP_Y1 = 24, 132, 1000, 262
LAND = (232, 222, 198)
LAND_EDGE = (120, 110, 88)


def project(lon, lat):
    x = MAP_X0 + (lon + 180.0) / 360.0 * (MAP_X1 - MAP_X0)
    y = MAP_Y0 + (75.0 - lat) / 130.0 * (MAP_Y1 - MAP_Y0)
    return (x, y)


CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
     (-80, 62), (-70, 58), (-65, 50), (-60, 47), (-70, 42), (-75, 35),
     (-80, 32), (-81, 26), (-84, 30), (-90, 21), (-97, 16), (-105, 20),
     (-115, 28), (-125, 40), (-125, 49), (-140, 60), (-158, 58), (-168, 66)],
    # Greenland
    [(-55, 60), (-45, 60), (-40, 65), (-30, 68), (-22, 70), (-30, 76),
     (-55, 76), (-60, 74), (-58, 64)],
    # South America
    [(-80, 10), (-75, 11), (-70, 12), (-62, 10), (-55, 6), (-50, 0),
     (-40, -5), (-35, -8), (-40, -20), (-48, -28), (-55, -35), (-65, -41),
     (-70, -50), (-73, -53), (-70, -45), (-73, -37), (-75, -25), (-80, -15),
     (-81, -5), (-80, 5)],
    # Africa
    [(-17, 15), (-10, 30), (-5, 35), (10, 37), (20, 32), (30, 31),
     (35, 28), (40, 15), (48, 11), (51, 12), (44, 0), (40, -10),
     (35, -20), (30, -30), (20, -35), (15, -30), (12, -18), (9, -1),
     (9, 4), (-8, 4), (-13, 8), (-17, 15)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 58), (28, 60), (30, 62), (40, 68), (50, 69),
     (60, 69), (70, 72), (80, 73), (90, 75), (100, 76), (110, 74),
     (120, 73), (130, 72), (140, 72), (150, 70), (160, 70), (170, 67),
     (178, 65), (178, 62), (170, 60), (162, 56), (158, 52), (150, 59),
     (142, 55), (140, 50), (135, 43), (130, 42), (127, 40), (122, 38),
     (120, 32), (115, 28), (110, 20), (108, 18), (105, 10), (100, 8),
     (98, 12), (95, 16), (92, 21), (88, 22), (85, 20), (80, 15), (77, 8),
     (75, 12), (72, 20), (68, 23), (62, 25), (58, 26), (55, 26), (52, 28),
     (50, 29), (48, 30), (44, 29), (40, 31), (36, 36), (30, 36), (27, 37),
     (23, 36), (19, 40), (15, 44), (12, 45), (8, 44), (3, 43), (-2, 37),
     (-9, 37), (-10, 36)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51), (-3, 50)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (141, 39),
     (141, 42), (143, 44), (141, 45), (139, 41), (137, 38), (133, 36), (130, 33)],
    # Australia
    [(114, -22), (114, -30), (115, -35), (120, -34), (125, -32), (130, -32),
     (135, -35), (140, -38), (145, -38), (150, -37), (153, -32), (153, -27),
     (150, -22), (146, -19), (142, -15), (142, -11), (137, -12), (135, -15),
     (132, -12), (130, -13), (126, -14), (122, -17), (118, -20), (114, -22)],
    # New Zealand
    [(167, -45), (170, -42), (173, -40), (175, -38), (177, -38), (175, -41),
     (173, -42), (170, -44), (167, -46)],
    # Indonesia: Sumatra, Borneo, Java, New Guinea
    [(95, 5), (98, 3), (100, 0), (103, -3), (105, -5), (104, -6), (100, -2), (97, 2)],
    [(109, 1), (111, 3), (114, 4), (117, 6), (119, 0), (117, -3), (114, -4), (110, -3)],
    [(105, -6), (108, -7), (111, -7), (114, -8), (112, -8), (108, -8)],
    [(131, -1), (136, -2), (141, -3), (145, -6), (147, -8), (143, -8),
     (138, -7), (134, -4), (131, -2)],
]

MARKERS = [
    ("ANTALYA", 30.7, 36.9, 1, 8, 4),
    ("KYIV", 30.5, 50.4, 1, -14, -13),
    ("HORMUZ", 56.5, 26.6, 1, 8, 4),
    ("THE HAGUE", 4.3, 52.1, 0, -58, -13),
    ("JAKARTA", 106.8, -6.2, 0, -30, -13),
    ("NEW DELHI", 77.2, 28.6, 0, -38, -13),
    ("BRASILIA", -47.9, -15.8, 0, -32, -13),
    ("LISBON", -9.1, 38.7, 0, -46, -13),
    ("KHARTOUM", 32.5, 15.6, 0, 8, 4),
    ("WELLINGTON", 174.8, -41.3, 0, -80, -4),
]


def draw_map(draw):
    draw.rectangle([MAP_X0, MAP_Y0, MAP_X1, MAP_Y1], fill=(233, 238, 240),
                   outline=INK, width=1)
    # faint latitude lines
    for lat in (60, 30, 0, -30):
        _, y = project(0, lat)
        draw.line([(MAP_X0, y), (MAP_X1, y)], fill=(210, 216, 220), width=1)
    for poly in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly]
        draw.polygon(pts, fill=LAND, outline=LAND_EDGE)
    f_small = font(9)
    for name, lon, lat, big, dx, dy in MARKERS:
        x, y = project(lon, lat)
        r = 4 if big else 3
        draw.ellipse([x - r, y - r, x + r, y + r], fill=RED, outline=(255, 255, 255))
        lw = draw.textlength(name, font=f_small)
        lx = min(max(x + dx, MAP_X0 + 2), MAP_X1 - lw - 2)
        draw.text((lx, y + dy), name, font=f_small, fill=INK)
    # date stamp on the map, bottom-left corner
    draw.rectangle([MAP_X0 + 6, MAP_Y1 - 20, MAP_X0 + 128, MAP_Y1 - 6],
                   fill=INK)
    draw.text((MAP_X0 + 11, MAP_Y1 - 19), "23 NOVEMBER 2026", font=font(10),
              fill=(255, 255, 255))


# ------------------------------------------------------------------ panels
def draw_panel_cop31(draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=(250, 238, 210), outline=INK, width=1)
    # sun
    draw.ellipse([x0 + 118, y0 + 8, x0 + 162, y0 + 52], fill=(232, 120, 40),
                 outline=(180, 80, 20))
    # sea
    for i in range(3):
        yy = y0 + 62 + i * 7
        draw.arc([x0 + 8, yy - 6, x1 - 8, yy + 10], 0, 180, fill=SEA, width=2)
    # conference hall
    draw.rectangle([x0 + 20, y0 + 30, x0 + 100, y0 + 62], fill=(120, 110, 90),
                   outline=INK)
    for i in range(5):
        wx = x0 + 28 + i * 14
        draw.rectangle([wx, y0 + 38, wx + 8, y0 + 54], fill=(240, 230, 200))
    draw.polygon([(x0 + 16, y0 + 30), (x0 + 60, y0 + 14), (x0 + 104, y0 + 30)],
                 fill=(90, 80, 60), outline=INK)
    # empty chairs row (talks ended, hall empty)
    for i in range(6):
        cx = x0 + 130 + i * 28
        draw.rectangle([cx, y0 + 66, cx + 18, y0 + 76], fill=GREY, outline=INK)
    centre(draw, y1 - 22, "COP31 ENDS WITH NO DEAL", font(11), fill=RED, x0=x0, x1=x1, stroke=0)
    centre(draw, y1 - 10, "Antalya, Turkiye", font(9), fill=GREY, x0=x0, x1=x1)


def draw_panel_kyiv(draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=(38, 42, 52), outline=INK, width=1)
    # apartment blocks
    for bx, bw, bh in ((18, 62, 52), (92, 54, 66), (158, 66, 44), (236, 56, 58)):
        draw.rectangle([x0 + bx, y0 + 78 - bh, x0 + bx + bw, y0 + 78],
                       fill=(70, 74, 88), outline=(150, 150, 160))
        for wy in range(y0 + 84 - bh, y0 + 74, 10):
            for wx in range(x0 + bx + 6, x0 + bx + bw - 6, 12):
                draw.rectangle([wx, wy, wx + 6, wy + 6], fill=(232, 200, 90))
    # smoke
    for cx, cy, r in ((x0 + 120, y0 + 18, 12), (x0 + 132, y0 + 10, 15),
                      (x0 + 110, y0 + 8, 9), (x0 + 210, y0 + 22, 10)):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(150, 148, 140))
    # flame at the struck block
    fx = x0 + 118
    draw.polygon([(fx - 14, y0 + 78), (fx, y0 + 48), (fx + 14, y0 + 78)],
                 fill=(232, 90, 30))
    draw.polygon([(fx - 7, y0 + 78), (fx, y0 + 60), (fx + 7, y0 + 78)],
                 fill=(240, 200, 60))
    centre(draw, y1 - 22, "DRONE HITS FLATS NEAR KYIV", font(11), fill=(255, 255, 255), x0=x0, x1=x1)
    centre(draw, y1 - 10, "2 dead, 14 missing - Dymer, Ukraine", font(9), fill=(190, 190, 190), x0=x0, x1=x1)


def draw_panel_hormuz(draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=(214, 232, 240), outline=INK, width=1)
    # sun
    draw.ellipse([x0 + 250, y0 + 6, x0 + 284, y0 + 40], fill=(240, 180, 60),
                 outline=(200, 140, 40))
    # sea
    draw.rectangle([x0 + 1, y0 + 58, x1 - 1, y1 - 26], fill=(58, 110, 145))
    for i in range(3):
        yy = y0 + 64 + i * 8
        draw.arc([x0 + 10, yy - 5, x1 - 10, yy + 8], 0, 180, fill=(200, 225, 240), width=2)
    # tanker
    draw.rectangle([x0 + 40, y0 + 38, x0 + 260, y0 + 62], fill=(40, 40, 44), outline=INK)
    draw.rectangle([x0 + 225, y0 + 18, x0 + 252, y0 + 38], fill=(220, 220, 220), outline=INK)
    draw.rectangle([x0 + 40, y0 + 30, x0 + 90, y0 + 38], fill=(120, 30, 30))
    # flame + smoke from the bow
    draw.polygon([(x0 + 52, y0 + 32), (x0 + 66, y0 + 6), (x0 + 80, y0 + 32)],
                 fill=(232, 90, 30))
    for cx, cy, r in ((x0 + 66, y0 + 8, 8), (x0 + 78, y0 + 6, 9), (x0 + 56, y0 + 10, 6)):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(90, 88, 84))
    draw.rectangle([x0, y0, x1, y1], outline=INK, width=1)
    centre(draw, y1 - 22, "TANKER ABLAZE IN THE HORMUZ STRAIT", font(11), fill=RED, x0=x0, x1=x1)
    centre(draw, y1 - 10, "Gulf tensions flare again", font(9), fill=GREY, x0=x0, x1=x1)


# ------------------------------------------------------------------- build
def build():
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # --- masthead ------------------------------------------------------
    centre(draw, 14, "ONE DAY  \u00b7  ONE PAGE  \u00b7  THE WHOLE WORLD", font(11), fill=GREY)
    centre(draw, 30, "MONDAY 23 NOVEMBER 2026", font(56), fill=INK, stroke=1)
    centre(draw, 92, "The World in One Day", font(20), fill=RED, stroke=0)
    rule(draw, 118, width=3)
    rule(draw, 123, width=1)

    # --- world map ------------------------------------------------------
    draw_map(draw)
    centre(draw, 266, "WHERE THE DAY HAPPENED - EVERY STORY ON THIS PAGE IS MARKED IN RED",
           font(10), fill=GREY)

    # --- three picture panels -------------------------------------------
    px0, pw, gap = 24, 317, 12
    py0, py1 = 278, 388
    draw_panel_cop31(draw, px0, py0, px0 + pw, py1)
    draw_panel_kyiv(draw, px0 + pw + gap, py0, px0 + 2 * pw + gap, py1)
    draw_panel_hormuz(draw, px0 + 2 * (pw + gap), py0, px0 + 3 * pw + 2 * gap, py1)

    # --- story grid ------------------------------------------------------
    rule(draw, 398, width=2)
    centre(draw, 406, "THE DAY IN FULL - 30 STORIES, ALL TIMES UTC", font(12), fill=INK, stroke=0)
    rule(draw, 426, width=1)

    col_w, col_gap = 312, 20
    pitch = 52
    y_top = 436
    f_kick, f_head, f_meta = font(9), font(12), font(9)
    for i, (kicker, headline, place, utc) in enumerate(STORIES):
        col = i % 3
        row = i // 3
        x = 24 + col * (col_w + col_gap)
        y = y_top + row * pitch
        draw.text((x, y), kicker, font=f_kick, fill=RED)
        lines = wrap(draw, headline, f_head, col_w, max_lines=2)
        hy = y + 11
        for ln in lines:
            draw.text((x, hy), ln, font=f_head, fill=INK)
            hy += 15
        draw.text((x, y + 42), f"{place} - {utc} UTC", font=f_meta, fill=GREY)

    # --- footer ----------------------------------------------------------
    fy = 968
    rule(draw, fy, width=3)
    rule(draw, fy + 5, width=1)
    centre(draw, fy + 12, "MONDAY 23 NOVEMBER 2026", font(15), fill=INK, stroke=0)
    centre(draw, fy + 32,
           "Sources: Reuters \u00b7 AP \u00b7 CNN \u00b7 UKMTO \u00b7 Axios \u00b7 BBC - checked 23 November 2026",
           font(10), fill=GREY)
    centre(draw, fy + 46, "23 November 2026 - the world, in one day, on one page.",
           font(10), fill=GREY)
    return img


def main() -> int:
    img = build()
    # Limited palette keeps the file small (tie-break) and stays legible.
    pal = img.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    pal.save(dst, format="PNG", optimize=True)
    size = os.path.getsize(dst)
    if size > 1048576:
        raise SystemExit(f"entry.png is {size} bytes, over the 1 MiB cap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
