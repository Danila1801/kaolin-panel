"""Tiny 32x32 renderer: a 3x5 pixel font, hand-drawn icons, card layouts.

Everything is drawn pixel by pixel with Pillow, so the panel shows crisp
pixels instead of a blurry downscaled image.
"""
from PIL import Image

W = H = 32

# 3x5 font. Each glyph is 5 rows of 3 chars, "#" = lit.
FONT = {
    "A": ["###", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "P": ["###", "#.#", "###", "#..", "#.."],
    "Q": ["###", "#.#", "#.#", "###", "..#"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", "..#", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
    " ": ["...", "...", "...", "...", "..."], ":": ["...", ".#.", "...", ".#.", "..."],
    "-": ["...", "...", "###", "...", "..."], "/": ["..#", "..#", ".#.", "#..", "#.."],
    ".": ["...", "...", "...", "...", ".#."], "!": [".#.", ".#.", ".#.", "...", ".#."],
    "?": ["###", "..#", ".##", "...", ".#."], "+": ["...", ".#.", "###", ".#.", "..."],
    "°": ["##.", "##.", "...", "...", "..."], "'": [".#.", ".#.", "...", "...", "..."],
}

# 12x12 icons. Letters map to colours in PALETTE, "." = off.
ICONS = {
    "sun": [
        ".....y......", ".y...y...y..", "..y.....y...", "....yyy.....",
        "...yyyyy....", "yy.yyyyy.yy.", "...yyyyy....", "....yyy.....",
        "..y.....y...", ".y...y...y..", ".....y......", "............",
    ],
    "cloud": [
        "............", "............", "....ww......", "...wwww.....",
        "..wwwwwww...", ".wwwwwwwww..", "wwwwwwwwwww.", "wwwwwwwwwww.",
        ".wwwwwwwww..", "............", "............", "............",
    ],
    "rain": [
        "....ww......", "...wwww.....", "..wwwwwww...", ".wwwwwwwww..",
        "wwwwwwwwwww.", ".wwwwwwwww..", "............", ".b..b..b..b.",
        "b..b..b..b..", "............", ".b..b..b..b.", "b..b..b..b..",
    ],
    "snow": [
        "....ww......", "...wwww.....", "..wwwwwww...", ".wwwwwwwww..",
        "wwwwwwwwwww.", ".wwwwwwwww..", "............", ".w...w...w..",
        "www.www.www.", ".w...w...w..", "............", "............",
    ],
    "shower": [
        "...gggg.....", "..g....g....", "..g.....g...", ".gggggggg...",
        "..........g.", ".b..b..b....", "..b..b..b...", ".b..b..b....",
        "..b..b..b...", ".b..b..b....", "..b..b..b...", "............",
    ],
    "food": [
        "...o..o.....", "..o..o......", "...o..o.....", "............",
        "wwwwwwwwwww.", "wwwwwwwwwww.", ".wwwwwwwww..", ".wwwwwwwww..",
        "..wwwwwww...", "...wwwww....", "............", "............",
    ],
    "coffee": [
        "...w..w.....", "..w..w......", "...w..w.....", "............",
        "oooooooo....", "oooooooooo..", "oooooooo.o..", "oooooooo.o..",
        "oooooooooo..", ".oooooo.....", "wwwwwwwwww..", "............",
    ],
    "run": [
        ".....gg.....", ".....gg.....", "...gggg.....", "..g.ggg.g...",
        "....gg..g...", "...gggg.....", "..g....g....", ".g.....g....",
        "g.......g...", "............", "............", "............",
    ],
    "book": [
        "............", "bbbbb.bbbbb.", "bwwwb.bwwwb.", "bbbbb.bbbbb.",
        "bwwwb.bwwwb.", "bbbbb.bbbbb.", "bwwwb.bwwwb.", "bbbbbbbbbbb.",
        "............", "............", "............", "............",
    ],
    "bag": [
        "....ooo.....", "...o...o....", "..ooooooo...", ".ooooooooo..",
        ".oowwwwwoo..", ".ooooooooo..", ".ooooooooo..", ".ooooooooo..",
        ".ooooooooo..", "............", "............", "............",
    ],
    "tooth": [
        "..wwwwwww...", ".wwwwwwwww..", ".wwwwwwwww..", ".wwwwwwwww..",
        "..wwwwwww...", "..www.www...", "..ww...ww...", "..ww...ww...",
        "...w...w....", "............", "............", "............",
    ],
    "moon": [
        "....yyy.....", "..yyy.......", ".yyy........", ".yy.........",
        "yyy.........", "yyy.........", "yyy.........", ".yy......y..",
        ".yyy....yy..", "..yyyyyyy...", "....yyy.....", "............",
    ],
    "heart": [
        "............", ".rr...rr....", "rrrr.rrrr...", "rrrrrrrrr...",
        "rrrrrrrrr...", ".rrrrrrr....", "..rrrrr.....", "...rrr......",
        "....r.......", "............", "............", "............",
    ],
}

PALETTE = {
    "y": (255, 190, 0), "w": (200, 210, 220), "b": (40, 120, 255),
    "g": (0, 220, 130), "o": (255, 110, 30), "r": (255, 40, 70),
}

GREEN = (0, 230, 140)
WHITE = (220, 225, 230)
DIM = (90, 100, 110)


def text_width(s: str) -> int:
    return max(0, len(s) * 4 - 1)


def draw_text(img: Image.Image, s: str, x: int, y: int, color=WHITE) -> None:
    px = img.load()
    for i, ch in enumerate(s.upper()):
        glyph = FONT.get(ch, FONT["?"])
        for gy, row in enumerate(glyph):
            for gx, c in enumerate(row):
                xx, yy = x + i * 4 + gx, y + gy
                if c == "#" and 0 <= xx < W and 0 <= yy < H:
                    px[xx, yy] = color


def draw_centered(img, s, y, color=WHITE):
    draw_text(img, s, (W - text_width(s)) // 2, y, color)


def draw_icon(img: Image.Image, name: str, x: int, y: int, scale: int = 1) -> None:
    px = img.load()
    for iy, row in enumerate(ICONS[name]):
        for ix, c in enumerate(row):
            if c == ".":
                continue
            for sy in range(scale):
                for sx in range(scale):
                    xx, yy = x + ix * scale + sx, y + iy * scale + sy
                    if 0 <= xx < W and 0 <= yy < H:
                        px[xx, yy] = PALETTE[c]


def wrap(s: str, width: int = 8) -> list[str]:
    """Greedy word wrap to 8 chars per line (32 px / 4 px per char)."""
    lines, cur = [], ""
    for word in s.upper().split():
        cand = f"{cur} {word}".strip()
        if len(cand) <= width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word[:width]
    if cur:
        lines.append(cur)
    return lines


def blank() -> Image.Image:
    return Image.new("RGB", (W, H), (0, 0, 0))


def card_icon_label(icon: str, label: str, accent=GREEN, step: str | None = None) -> Image.Image:
    """Icon on top, up to 2 lines of text under it, optional step counter."""
    img = blank()
    draw_icon(img, icon, 10, 2)
    lines = wrap(label)[:2]
    y = 16 if len(lines) == 2 else 19
    for i, line in enumerate(lines):
        draw_centered(img, line, y + i * 7, accent if i == 0 else WHITE)
    if step:  # "2/5" -> progress bar on the bottom row
        done, total = map(int, step.split("/"))
        seg = W // total
        p = img.load()
        for k in range(total):
            for x in range(k * seg, (k + 1) * seg - 1):
                p[x, H - 1] = accent if k < done else (35, 40, 45)
    return img


def card_text(lines: list[str], colors=None) -> Image.Image:
    img = blank()
    colors = colors or [GREEN] + [WHITE] * 4
    top = (H - (len(lines) * 7 - 2)) // 2
    for i, line in enumerate(lines):
        draw_centered(img, line, top + i * 7, colors[i % len(colors)])
    return img


def card_weather(icon: str, now_c: int, hi: int, lo: int, word: str) -> Image.Image:
    img = blank()
    draw_icon(img, icon, 1, 1)
    t = f"{now_c}°"
    draw_text(img, t, 30 - text_width(t), 4, WHITE)
    draw_centered(img, word, 16, GREEN)
    hl = f"{hi}/{lo}"
    draw_centered(img, hl, 24, DIM)
    return img


def save_gif(frames: list[Image.Image], durations: list[int], path) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=1, optimize=False)


def save_preview(frames: list[Image.Image], durations: list[int], path, scale: int = 10) -> None:
    """Upscaled GIF with an LED-dot look, for the README."""
    out = []
    for f in frames:
        big = Image.new("RGB", (W * scale, H * scale), (12, 12, 14))
        px = f.load()
        for y in range(H):
            for x in range(W):
                c = px[x, y]
                if c == (0, 0, 0):
                    c = (28, 28, 32)
                for yy in range(1, scale - 1):
                    for xx in range(1, scale - 1):
                        big.putpixel((x * scale + xx, y * scale + yy), c)
        out.append(big)
    out[0].save(path, save_all=True, append_images=out[1:], duration=durations, loop=0)
